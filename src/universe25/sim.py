"""Universe 25 simulator: need-driven agents, density stress, playground (no play reward)."""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from universe25.agents.state import (
    ACT_AGGRESS,
    ACT_BACK_OFF,
    ACT_CIRCLE,
    ACT_DRINK,
    ACT_EXPLORE,
    ACT_FORAGE,
    ACT_MANIPULATE,
    ACT_MATE,
    ACT_NEST,
    ACT_NURSE,
    ACT_REST,
    ACT_RUN_ON,
    ACT_SOCIAL,
    ACT_TURN_BACK,
    ACT_WITHDRAW,
    LOCO_FAMILY,
    N_ACTIONS,
    OBJECT_FAMILY,
    ROLE_BREEDING_FEMALE,
    ROLE_DEAD,
    ROLE_JUVENILE,
    ROLE_NURSING,
    ROLE_PUP,
    ROLE_SUBORDINATE_MALE,
    ROLE_TERRITORIAL_MALE,
    ROLE_WITHDRAWN,
    SEX_F,
    SEX_M,
    AgentSoA,
    pick_backend,
)
from universe25.agents.policy import make_policy
from universe25.config import SimConfig
from universe25.metrics.calibration import rate_cessation_day, surviving_birth_cessation_day
from universe25.metrics.logger import MetricsLogger
from universe25.metrics.playscore import PlayScoreAccumulator
from universe25.metrics.trace import CONTACT_SLACK, TraceRecorder
from universe25.io.snapshots import SnapshotWriter
from universe25.rng import make_rng
from universe25.world.geometry import World, build_world
from universe25.nvidia.nvtx_ranges import nvtx_range
from universe25.nvidia.cuda_graphs import CudaGraphTick
from universe25.warp_kernels.engine import WarpTickEngine


# Ball physics (P4-13, PHASE4_DESIGN.md 1.9), fixed before the first run
BALL_KAPPA = 1.0  # ball speed gained per inch of approach at contact
BALL_FRICTION_K12 = 0.7  # speed kept per sub-step at K = 12 (0.7 ** (12 / K) at other K)
BALL_RESTITUTION = 0.5  # share of the normal speed kept at a playground bound
BALL_STOP = 0.01  # inches per sub-step: slower balls stop


class Universe25Sim:
    def __init__(self, cfg: SimConfig, out_dir: Path):
        self.cfg = cfg
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.rng = make_rng(cfg.seed)
        self.backend, self.device = pick_backend(cfg.backend, cfg.device)
        self.world: World = build_world(cfg.geometry, cfg.playground, seed=cfg.seed)
        self._nest_x = np.array([n.x for n in self.world.nests], dtype=np.float64)
        self._nest_y = np.array([n.y for n in self.world.nests], dtype=np.float64)
        self.agents = AgentSoA.create(cfg.max_agents)
        self.policy = make_policy(cfg.policy, cfg.seed)  # chooses among eligible actions
        self.tick = 0
        self.day = 0.0
        self.dt_days = 1.0 / cfg.ticks_per_day
        # Resolution scaling (see SimConfig.ticks_per_day_ref). Agents decide once per
        # reference interval (1/ticks_per_day_ref day) and hold the action over the finer
        # ticks in between. Per-decision events (a meal, a drink, the move to a target, a
        # fight, drive relief, a random-walk step) happen in full on the decision tick, exactly
        # as at the reference resolution; the held ticks integrate only continuous physics
        # (drive growth, fatigue, nursing contact, stress, mortality) with dt, the stress
        # relaxation in exact form. k_ev = ref/tpd is kept for diagnostics only.
        self.k_ev = cfg.ticks_per_day_ref / cfg.ticks_per_day
        self.ticks_per_decision = max(1, cfg.ticks_per_day // cfg.ticks_per_day_ref)
        self.dt_ref = 1.0 / cfg.ticks_per_day_ref  # length of a decision, days
        self.reach = 24.0 / cfg.ticks_per_day_ref  # inches per decision per unit speed
        self.food = np.full(self.world.n_cells, cfg.resources.food_refill_per_tick, dtype=np.float64)
        self.water = np.full(self.world.n_cells, cfg.resources.water_refill_per_tick, dtype=np.float64)
        self.logger = MetricsLogger(self.out_dir / "metrics.parquet")
        self.playscore = PlayScoreAccumulator()
        self.snapshots = SnapshotWriter(self.out_dir / "snapshots")
        self.cuda_graph = CudaGraphTick(
            enabled=bool(getattr(cfg, "use_cuda_graph", False)),
            backend=self.backend,
            device=self.device,
        )
        self.warp_engine = None
        if self.backend == "warp":
            dev = self.device if str(self.device).startswith("cuda") else "cuda:0"
            if self.device == "cpu":
                dev = "cpu"
            self.warp_engine = WarpTickEngine(
                cfg=cfg,
                world=self.world,
                device=dev,
                use_graph=bool(getattr(cfg, "use_cuda_graph", False)) and str(dev).startswith("cuda"),
            )
            self.cuda_graph.bind_engine(self.warp_engine)
        self._action_hist = np.zeros(N_ACTIONS, dtype=np.int64)
        self._cell_food = np.array([c.food_xy for c in self.world.cells], dtype=np.float64)
        self._cell_water = np.array([c.water_xy for c in self.world.cells], dtype=np.float64)
        # free-time sub-steps (P4-8): 1 = off; their own stream, never the biology stream
        self.free_substeps = max(1, int(cfg.free_substeps))
        self._sub_rng = make_rng(cfg.seed + 2_000_003) if self.free_substeps > 1 else None
        # ball physics (P4-13, PHASE4_DESIGN.md 1.9): pushes and rolling in the free-time
        # sub-steps, deterministic (no random draw); off = bit-identical
        self.ball_physics = bool(cfg.playground.ball_physics and self.world.playground_enabled)
        self.ball_friction = BALL_FRICTION_K12 ** (12.0 / self.free_substeps)
        self.ball_v_ref = BALL_KAPPA * 7.0 * self.reach / self.free_substeps  # full MANIPULATE
        self._ball_stats = {"pushes": 0, "object_family_pushes": 0, "rolled_in": 0.0}
        # novelty-based curiosity (P4-14, PHASE4_DESIGN.md 1.10): per-animal last visit time of
        # each grid bin (days, -inf = never); deterministic; off = bit-identical
        dcfg = cfg.drives
        self.novelty = bool(dcfg.curiosity_novelty)
        self.consequence_gain = float(dcfg.consequence_gain)
        self.nov_G = int(dcfg.novelty_grid)
        self.nov_tau = float(dcfg.novelty_tau_days)
        self._visit_t = (np.full((cfg.max_agents, self.nov_G * self.nov_G), -np.inf)
                         if self.novelty else None)
        self._nov_t = 0.0  # time the policy observes novelty at (decision or sub-step start)
        # eval-only decision traces (off when no windows: no recorder, bit-identical tick)
        self.trace = (TraceRecorder(self, cfg.trace.windows, cfg.trace.sample_every)
                      if cfg.trace.windows else None)
        self._conceptions = 0
        self._births = 0
        self._deaths = 0
        self._last_young_day = 0.0
        self._last_surviving_young_day = 0.0  # birth day of the latest pup that reached weaning
        # pups that reached weaning, by birth day (for the rate-based cessation landmark)
        self._surv_births_by_day = np.zeros(int(math.ceil(cfg.days)) + 2, dtype=np.int64)
        self._surv_births_cum = 0
        self._conc_by_day = np.zeros(int(math.ceil(cfg.days)) + 2, dtype=np.int64)
        self._cell_counts_tick = -1
        self._cell_counts = np.zeros(self.world.n_cells, dtype=np.int64)
        self._last_conception_day = 0.0
        self._abandoned = 0  # pups expelled from their nest box by a stressed mother
        self._peak_n = 0
        self._peak_day = 0.0
        self._nan_count = 0
        self._seed_initial()

    # ------------------------------------------------------------------ setup
    def _seed_initial(self) -> None:
        """Calhoun start: 4 pairs of young adults."""
        n = self.cfg.initial_pairs * 2
        slots = self.agents.free_slots(n)
        # Place pairs in four corner cells
        corner_cells = [0, 3, 12, 15]
        for i, slot in enumerate(slots):
            pair = i // 2
            cell = self.world.cells[corner_cells[pair % 4]]
            nest = self.world.nests[cell.nest_ids[i % len(cell.nest_ids)]]
            sex = SEX_F if (i % 2 == 0) else SEX_M
            self._spawn(
                slot,
                sex=sex,
                age=float(self.rng.uniform(60, 90)),
                x=nest.x + float(self.rng.normal(0, 0.5)),
                y=nest.y + float(self.rng.normal(0, 0.5)),
                nest_id=nest.id,
                cell_id=cell.id,
                role=ROLE_BREEDING_FEMALE if sex == SEX_F else ROLE_TERRITORIAL_MALE,
            )
        self.agents.n_alive = int(self.agents.alive.sum())

    def _spawn(
        self,
        slot: int,
        *,
        sex: int,
        age: float,
        x: float,
        y: float,
        nest_id: int,
        cell_id: int,
        role: int,
    ) -> None:
        a = self.agents
        a.alive[slot] = True
        a.sex[slot] = sex
        if self._visit_t is not None:  # a new animal knows no place yet
            self._visit_t[slot] = -np.inf
        a.age_days[slot] = age
        a.hunger[slot] = float(self.rng.uniform(0.1, 0.3))
        a.thirst[slot] = float(self.rng.uniform(0.1, 0.3))
        a.fatigue[slot] = 0.1
        a.stress[slot] = 0.05
        a.social_drive[slot] = 0.3
        a.aggression[slot] = self.cfg.drives.aggression_baseline
        a.maternal[slot] = 0.8 if sex == SEX_F else 0.0
        a.rank[slot] = float(self.rng.uniform(0.4, 0.8))
        a.role[slot] = role
        a.wounds[slot] = 0.0
        a.x[slot] = np.clip(x, 0.5, self.world.width - 0.5)
        a.y[slot] = np.clip(y, 0.5, self.world.height - 0.5)
        a.cell_id[slot] = cell_id
        a.nest_id[slot] = nest_id
        a.gestating[slot] = 0.0
        a.energy[slot] = 0.9
        a.curiosity[slot] = 0.35
        a.boredom[slot] = 0.1
        a.last_action[slot] = ACT_REST
        a.recent_action[slot] = ACT_REST
        a.in_playground[slot] = self.world.in_playground(a.x[slot], a.y[slot])
        a.competence[slot] = 1.0  # shaped during development (see _density_stress)
        a.maternal_cap[slot] = 1.0  # eroded in adulthood (see _daily_maternal_erosion)
        a.courtship_cap[slot] = 1.0  # males; eroded in adulthood (see _daily_maternal_erosion)
        bio = self.cfg.biology
        if bio.max_age_sd_days > 0.0:  # per-individual lifespan (old-age hazard onset)
            a.lifespan[slot] = max(
                0.3 * bio.max_age_days,
                float(self.rng.normal(bio.max_age_days, bio.max_age_sd_days)),
            )
        else:
            a.lifespan[slot] = bio.max_age_days

    # ------------------------------------------------------------------ step
    def step(self) -> None:
        a = self.agents
        alive = a.alive
        if not alive.any():
            self.tick += 1
            self.day = self.tick * self.dt_days
            return

        with nvtx_range("Universe25_step"):
            self._refill_resources()
            use_warp = self.warp_engine is not None
            if use_warp:
                with nvtx_range("drives"):
                    self._update_drives(alive)  # host drives (bit-stable with numpy path for shared logic)
            else:
                with nvtx_range("drives"):
                    self._update_drives(alive)
            with nvtx_range("roles"):
                self._assign_roles(alive)
            with nvtx_range("actions"):
                self._nov_t = self.day
                actions = self._select_actions(alive)
                decision = self._decision_tick()
                record = self.trace is not None and decision
                if record:
                    self.trace.capture_pre(self, alive, actions)
                free = (self._free_pre(alive, actions)
                        if self.free_substeps > 1 and decision else None)
                self._execute_actions(alive, actions)
                if free is not None:
                    self._run_free_substeps(free)
                if self.novelty and decision:  # every animal marks where it ends the decision
                    idx = np.flatnonzero(a.alive)
                    self._visit_t[idx, self.nov_bin(a.x[idx], a.y[idx])] = self.day + self.dt_ref
                if record:
                    self.trace.record_post(self)
            with nvtx_range("life"):
                self._passive_nurse(alive)
                self._daily_breeding_pass(alive)
                self._daily_maternal_erosion(alive)
                self._daily_courtship_erosion(alive)
                self._daily_litter_abandonment(alive)
                self._reproduce(alive)
            if use_warp:
                with nvtx_range("warp_stress_mortality_cells"):
                    # Device: density stress + mortality + cell/playground flags (CUDA Graph capable)
                    self._warp_post_step()
            else:
                with nvtx_range("density_stress"):
                    self._density_stress(alive)
                with nvtx_range("mortality"):
                    self._age_and_die(alive)
            self._check_nan()

        a.n_alive = int(a.alive.sum())
        if a.n_alive > self._peak_n:
            self._peak_n = a.n_alive
            self._peak_day = self.day
        # Calhoun's landmark is the last *surviving* birth: latest birth day among weaned young.
        wean = self.cfg.biology.weaning_days
        weaned = alive & (a.age_days >= wean)
        if weaned.any():
            born = self.day - float(a.age_days[weaned].min())
            if born > self._last_surviving_young_day:
                self._last_surviving_young_day = born
            crossed = weaned & (a.age_days - self.dt_days < wean)  # weaned this tick
            if crossed.any():
                bd = np.floor(self.day - a.age_days[crossed]).astype(int)
                bd = np.clip(bd, 0, self._surv_births_by_day.size - 1)
                np.add.at(self._surv_births_by_day, bd, 1)
                self._surv_births_cum += int(crossed.sum())

        self.tick += 1
        self.day = self.tick * self.dt_days

        if self.tick % self.cfg.log_every_ticks == 0:
            self._log_metrics()
        if (
            self.cfg.snapshot_every_days > 0
            and abs(self.day % self.cfg.snapshot_every_days) < self.dt_days
        ):
            self.snapshots.write(self.day, self.agents, self.world)

    def _refill_resources(self) -> None:
        if self.cfg.resources.mode == "abundant":
            self.food[:] = self.cfg.resources.food_refill_per_tick
            self.water[:] = self.cfg.resources.water_refill_per_tick
        elif self.cfg.resources.scarce_supply == "capacity":
            a = self.agents
            weaned = a.alive & (a.age_days >= self.cfg.biology.weaning_days)
            occ = np.bincount(a.cell_id[weaned].astype(int), minlength=self.world.n_cells)
            n_w = max(1, int(occ.sum()))
            r = self.cfg.resources
            supply = r.scarce_capacity_animals * self.cfg.drives.hunger_gain_per_day
            period = r.scarce_famine_period_days
            if period > 0 and (self.day % period) < r.scarce_famine_days:
                supply *= r.scarce_famine_factor
            share = supply * occ / n_w  # per cell per day, by weaned occupancy
            self.food = np.minimum(self.food + share / self.cfg.ticks_per_day, 2.0 * share)
            self.water[:] = self.cfg.resources.water_refill_per_tick
        else:
            per = self.cfg.resources.scarce_food_per_day / self.cfg.ticks_per_day
            self.food += per / max(1, self.world.n_cells)
            self.water[:] = self.cfg.resources.water_refill_per_tick

    def _update_drives(self, alive: np.ndarray) -> None:
        d = self.cfg.drives
        dt = self.dt_days
        a = self.agents
        idx = alive
        pup = a.role[idx] == ROLE_PUP
        phs = float(self.cfg.biology.pup_hunger_scale)
        hunger_gain = np.where(pup, d.hunger_gain_per_day * phs, d.hunger_gain_per_day)
        thirst_gain = np.where(pup, d.thirst_gain_per_day * phs, d.thirst_gain_per_day)
        a.hunger[idx] = np.clip(a.hunger[idx] + hunger_gain * dt, 0, 1.5)
        a.thirst[idx] = np.clip(a.thirst[idx] + thirst_gain * dt, 0, 1.5)
        a.curiosity[idx] = np.clip(a.curiosity[idx] + d.curiosity_gain * dt, 0, 1.5)
        a.boredom[idx] = np.clip(a.boredom[idx] + d.boredom_gain * dt, 0, 1.5)
        a.social_drive[idx] = np.clip(a.social_drive[idx] + d.social_drive_gain * dt, 0, 1.5)
        # energy homeostasis: decays with activity proxied by fatigue
        a.energy[idx] = np.clip(a.energy[idx] - 0.15 * dt - 0.1 * a.fatigue[idx] * dt, 0, 1)
        a.wounds[idx] = np.maximum(0.0, a.wounds[idx] - self.cfg.biology.wound_heal_per_day * dt)
        a.age_days[idx] += dt
        if a.gestating[idx].any():
            gest = idx & (a.gestating > 0)
            a.gestating[gest] = np.maximum(0.0, a.gestating[gest] - dt)

    def _assign_roles(self, alive: np.ndarray) -> None:
        a = self.agents
        bio = self.cfg.biology
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            return
        age = a.age_days[idx]
        role = np.empty(idx.size, dtype=np.int8)
        role[:] = ROLE_BREEDING_FEMALE
        pup = age < bio.weaning_days
        juv = (~pup) & (age < bio.maturity_days)
        bio = self.cfg.biology
        withdrawn = (
            (~pup)
            & (~juv)
            & (a.stress[idx] > bio.withdrawn_stress_threshold)
            & (a.social_drive[idx] < bio.withdrawn_social_threshold)
            & (a.aggression[idx] < bio.beautiful_one_aggression_max)
        )
        # "Beautiful ones": adults whose development under crowding left them socially
        # incompetent withdraw permanently (competence is frozen at maturity).
        withdrawn |= (~pup) & (~juv) & (a.competence[idx] < bio.withdrawn_competence_threshold)
        female = a.sex[idx] == SEX_F
        nursing = female & ((a.maternal[idx] > 0.5) & ((a.gestating[idx] > 0) | (a.role[idx] == ROLE_NURSING)))
        male = ~female
        terr = male & (a.rank[idx] > 0.55)
        role[pup] = ROLE_PUP
        role[juv] = ROLE_JUVENILE
        role[withdrawn] = ROLE_WITHDRAWN
        role[(~pup) & (~juv) & (~withdrawn) & nursing] = ROLE_NURSING
        role[(~pup) & (~juv) & (~withdrawn) & female & (~nursing)] = ROLE_BREEDING_FEMALE
        role[(~pup) & (~juv) & (~withdrawn) & terr] = ROLE_TERRITORIAL_MALE
        role[(~pup) & (~juv) & (~withdrawn) & male & (~terr)] = ROLE_SUBORDINATE_MALE
        a.role[idx] = role


    def _select_actions(self, alive: np.ndarray) -> np.ndarray:
        """Physiology around the policy: decision cadence, eligibility mask, reflex overrides.
        The choice among eligible actions is `self.policy.choose` (agents/policy.py; the default
        need-driven utility softmax has no play utility term).

        Decisions are made every ticks_per_decision ticks (once per reference interval);
        on the ticks in between every agent continues its last action.
        """
        a = self.agents
        n = a.capacity
        actions = np.full(n, ACT_REST, dtype=np.int8)
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            return actions
        if self.ticks_per_decision > 1 and (self.tick % self.ticks_per_decision) != 0:
            actions[idx] = a.last_action[idx]
            return actions
        bio = self.cfg.biology
        m = idx.size
        hung = a.hunger[idx]
        th = a.thirst[idx]
        fat = a.fatigue[idx]
        en = a.energy[idx]
        st = a.stress[idx]
        role = a.role[idx]
        sex = a.sex[idx]
        age = a.age_days[idx]
        mat = a.maternal[idx]

        # Eligibility mask: ineligible actions get exactly zero probability. (Previously a
        # zero utility still carried softmax weight, so pups foraged, fought and conceived.)
        pup = age < bio.weaning_days
        adult = age >= bio.maturity_days
        allowed = np.ones((m, N_ACTIONS), dtype=bool)
        # Pre-weaning pups are milk-dependent and stay at the nest.
        allowed[pup, :] = False
        allowed[pup, ACT_REST] = True
        allowed[pup, ACT_NEST] = True
        allowed[:, ACT_MATE] &= adult & (st < 0.75) & (role != ROLE_WITHDRAWN) & (en > 0.4)
        allowed[:, ACT_NURSE] &= (sex == SEX_F) & (mat > 0.0)
        if not self.world.playground_enabled:
            allowed[:, ACT_MANIPULATE] = False
        # Action space v2: the movement primitives are allowed wherever their family is (the
        # heuristic and v2 networks never choose them; their columns are not read).
        allowed[:, ACT_RUN_ON] = allowed[:, ACT_EXPLORE]
        allowed[:, ACT_TURN_BACK] = allowed[:, ACT_EXPLORE]
        allowed[:, ACT_BACK_OFF] = allowed[:, ACT_MANIPULATE]
        allowed[:, ACT_CIRCLE] = allowed[:, ACT_MANIPULATE]

        # Critical physiological needs override the policy (dt-invariant need drive); pups
        # cannot use hoppers, their hunger/thirst are relieved only by nursing. The forced
        # action is also the only one the mask allows, so a learning policy is never credited
        # for an action physiology overrode (same outcome, same draws: bit-identical).
        forced = np.full(m, -1, dtype=np.int64)
        forced = np.where((th > 0.85) & ~pup, ACT_DRINK, forced)
        forced = np.where((hung > 0.85) & ~pup, ACT_FORAGE, forced)
        forced = np.where((fat > 1.2) & (hung < 0.7) & (th < 0.7), ACT_REST, forced)
        fr = forced >= 0
        if fr.any():
            allowed[fr, :] = False
            allowed[np.flatnonzero(fr), forced[fr]] = True
        chosen = self.policy.choose(self, idx, allowed)  # every row allows one action
        chosen = np.where(fr, forced, chosen).astype(np.int8)
        actions[idx] = chosen
        return actions

    def _decision_tick(self) -> bool:
        return (self.tick % self.ticks_per_decision) == 0

    def _execute_actions(self, alive: np.ndarray, actions: np.ndarray) -> None:
        """Batched action effects (still host-side NumPy).

        `decision` ticks carry the per-decision events (k = 1); on held ticks k = 0 and only
        the continuous terms written with dt apply.
        """
        a = self.agents
        d = self.cfg.drives
        dt = self.dt_days
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            return
        act = actions[idx].astype(np.int16)
        a.last_action[idx] = act.astype(np.int8)
        a.recent_action[idx] = act.astype(np.int8)
        x_before, y_before = a.x[idx].copy(), a.y[idx].copy()  # for the heading (no draws)
        for code in range(N_ACTIONS):
            self._action_hist[code] += int(np.sum(act == code))
        decision = self._decision_tick()
        k = 1.0 if decision else 0.0  # per-decision event scale
        dtr = self.dt_ref  # random-walk steps are per decision: sd = c * dt_ref * 10
        xmax = self.world.width - 0.5
        ymax = self.world.height - 0.5

        # Movement helpers via masks
        cells = a.cell_id[idx].astype(int)
        food_xy = np.array([self.world.cells[c].food_xy for c in cells], dtype=np.float64)
        water_xy = np.array([self.world.cells[c].water_xy for c in cells], dtype=np.float64)

        def move_mask(mask, tx, ty, speed):
            ii = idx[mask]
            if ii.size == 0 or not decision:
                return
            dx = tx[mask] - a.x[ii]
            dy = ty[mask] - a.y[ii]
            dist = np.hypot(dx, dy) + 1e-6
            step = np.minimum(speed * self.reach, dist)
            a.x[ii] = np.clip(a.x[ii] + dx / dist * step, 0.5, self.world.width - 0.5)
            a.y[ii] = np.clip(a.y[ii] + dy / dist * step, 0.5, self.world.height - 0.5)

        m_forage = act == ACT_FORAGE
        if m_forage.any():
            ii = idx[m_forage]
            # The meal is a per-decision event (eat until satiated, stock-limited) on the
            # decision tick; the held ticks are spent at the hopper (fatigue, a little rest).
            if decision:
                # Scramble competition: the foragers at a hopper this decision split its stock
                # equally (each takes at most stock / foragers). With abundant food the share
                # always exceeds hunger, so the abundant arm is unchanged (bit-identical).
                n_c = np.bincount(a.cell_id[ii].astype(int), minlength=self.world.n_cells)
                share = self.food / np.maximum(n_c, 1)
                for i in ii:
                    c = int(a.cell_id[i])
                    take = min(float(a.hunger[i]), self.food[c], float(share[c]))
                    self.food[c] -= take
                    a.hunger[i] = max(0.0, a.hunger[i] - take)
                    a.energy[i] = min(1.0, a.energy[i] + 0.25 * take + 0.1 * dt)
            else:
                a.energy[ii] = np.minimum(1.0, a.energy[ii] + 0.1 * dt)
            move_mask(m_forage, food_xy[:, 0], food_xy[:, 1], 8.0)
            a.fatigue[ii] = np.minimum(1.5, a.fatigue[ii] + d.fatigue_gain_active * dt)

        m_drink = act == ACT_DRINK
        if m_drink.any():
            ii = idx[m_drink]
            if decision:  # a drink is a per-decision event, like a meal
                for i in ii:
                    c = int(a.cell_id[i])
                    take = min(float(a.thirst[i]), self.water[c])
                    self.water[c] -= take
                    a.thirst[i] = max(0.0, a.thirst[i] - take)
            move_mask(m_drink, water_xy[:, 0], water_xy[:, 1], 8.0)

        m_rest = act == ACT_REST
        if m_rest.any():
            ii = idx[m_rest]
            a.fatigue[ii] = np.maximum(0.0, a.fatigue[ii] - d.fatigue_recovery_rest * dt)
            a.energy[ii] = np.minimum(1.0, a.energy[ii] + 0.1 * dt)

        m_nest = act == ACT_NEST
        if m_nest.any():
            ii = idx[m_nest]
            nids = a.nest_id[ii].astype(int)
            tx = np.array([self.world.nests[n].x if n >= 0 else a.x[i] for i, n in zip(ii, nids)])
            ty = np.array([self.world.nests[n].y if n >= 0 else a.y[i] for i, n in zip(ii, nids)])
            # build full-length tx/ty aligned to idx mask
            txx = np.zeros(idx.size); tyy = np.zeros(idx.size)
            txx[m_nest] = tx; tyy[m_nest] = ty
            move_mask(m_nest, txx, tyy, 6.0)
            a.stress[ii] = np.maximum(0.0, a.stress[ii] - 0.05 * k)

        m_social = act == ACT_SOCIAL
        if m_social.any():
            ii = idx[m_social]
            a.social_drive[ii] = np.maximum(0.0, a.social_drive[ii] - 0.3 * k)
            a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - d.boredom_decay_on_vary * k)
            if decision:
                sd = 3.0 * dtr * 10
                a.x[ii] = np.clip(a.x[ii] + self.rng.normal(0, sd, ii.size), 0.5, xmax)
                a.y[ii] = np.clip(a.y[ii] + self.rng.normal(0, sd, ii.size), 0.5, ymax)

        m_explore = act == ACT_EXPLORE
        if m_explore.any():
            ii = idx[m_explore]
            a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - d.curiosity_decay_on_novel * k)
            a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - d.boredom_decay_on_vary * 0.5 * k)
            if decision:
                sd = 10.0 * dtr * 10
                a.x[ii] = np.clip(a.x[ii] + self.rng.normal(0, sd, ii.size), 0.5, xmax)
                a.y[ii] = np.clip(a.y[ii] + self.rng.normal(0, sd, ii.size), 0.5, ymax)

        m_manip = act == ACT_MANIPULATE
        if m_manip.any() and self.world.play_objects:
            ii = idx[m_manip]
            # nearest object (broadcast)
            ox = np.array([o.x for o in self.world.play_objects])
            oy = np.array([o.y for o in self.world.play_objects])
            for i in ii:
                if not decision:
                    break
                d2 = (ox - a.x[i]) ** 2 + (oy - a.y[i]) ** 2
                j = int(np.argmin(d2))
                self._move_toward(int(i), float(ox[j]), float(oy[j]), 7.0)
                if self.ball_physics:  # balls move only by physics (P4-13)
                    continue
                obj = self.world.play_objects[j]
                pgb = self.world.playground_bounds
                jig = 0.4  # per-decision nudge of the object
                obj.x = float(np.clip(obj.x + self.rng.normal(0, jig), pgb[0], pgb[2]))
                obj.y = float(np.clip(obj.y + self.rng.normal(0, jig), pgb[1], pgb[3]))
            a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - d.curiosity_decay_on_novel * k)
            a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - d.boredom_decay_on_vary * k)
            a.fatigue[ii] = np.minimum(1.5, a.fatigue[ii] + 0.5 * d.fatigue_gain_active * dt)

        # Action space v2 (PHASE4_DESIGN.md 1.8): the relief of the family, deterministic moves
        m_run = (act == ACT_RUN_ON) | (act == ACT_TURN_BACK)
        if m_run.any():
            ii = idx[m_run]
            a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - d.curiosity_decay_on_novel * k)
            a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - d.boredom_decay_on_vary * 0.5 * k)
            if decision:
                self._heading_moves(ii, act[m_run], 10.0 * dtr * 10 * math.sqrt(math.pi / 2))
        m_obj = (act == ACT_BACK_OFF) | (act == ACT_CIRCLE)
        if m_obj.any() and self.world.play_objects:
            ii = idx[m_obj]
            if decision:
                self._object_moves(ii, act[m_obj], 0.6 * 7.0 * self.reach)
            a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - d.curiosity_decay_on_novel * k)
            a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - d.boredom_decay_on_vary * k)
            a.fatigue[ii] = np.minimum(1.5, a.fatigue[ii] + 0.5 * d.fatigue_gain_active * dt)

        m_agg = act == ACT_AGGRESS
        if m_agg.any():
            ii = idx[m_agg]
            a.aggression[ii] = np.minimum(1.5, a.aggression[ii] + 0.05 * k)
            if decision:  # one fight per decision
                for i in ii:
                    self._aggress(int(i))
                sd = 4.0 * dtr * 10
                a.x[ii] = np.clip(a.x[ii] + self.rng.normal(0, sd, ii.size), 0.5, xmax)
                a.y[ii] = np.clip(a.y[ii] + self.rng.normal(0, sd, ii.size), 0.5, ymax)

        m_mate = act == ACT_MATE
        if m_mate.any() and decision:
            for i in idx[m_mate]:
                self._approach_mate(int(i))

        m_nurse = act == ACT_NURSE
        if m_nurse.any():
            # Mothers return to their nest to nurse (pups stay at the nest until weaning).
            ii = idx[m_nurse]
            nids = a.nest_id[ii].astype(int)
            txx = np.zeros(idx.size); tyy = np.zeros(idx.size)
            txx[m_nurse] = [self.world.nests[n].x if n >= 0 else a.x[i] for i, n in zip(ii, nids)]
            tyy[m_nurse] = [self.world.nests[n].y if n >= 0 else a.y[i] for i, n in zip(ii, nids)]
            move_mask(m_nurse, txx, tyy, 6.0)
            for i in ii:
                if a.stress[i] > self.cfg.biology.maternal_neglect_stress:
                    a.maternal[i] = max(0.0, a.maternal[i] - 0.05 * k)
                else:
                    a.maternal[i] = min(float(a.maternal_cap[i]), a.maternal[i] + 0.02 * k)
                    self._nurse(int(i))

        m_with = act == ACT_WITHDRAW
        if m_with.any():
            ii = idx[m_with]
            a.social_drive[ii] = np.maximum(0.0, a.social_drive[ii] - 0.1 * k)
            a.aggression[ii] = np.maximum(0.0, a.aggression[ii] - 0.05 * k)
            # drift toward (20, 20) at 5 % per decision (x*0.95 + 1.0 at the reference resolution)
            a.x[ii] = np.clip(a.x[ii] * (1.0 - 0.05 * k) + 20.0 * 0.05 * k, 0.5, xmax)
            a.y[ii] = np.clip(a.y[ii] * (1.0 - 0.05 * k) + 20.0 * 0.05 * k, 0.5, ymax)

        # update cell + playground flags (vectorized)
        nx, ny = self.cfg.geometry.n_cells_x, self.cfg.geometry.n_cells_y
        cw = self.world.width / nx
        ch = self.world.height / ny
        ix = np.clip((a.x[idx] / cw).astype(int), 0, nx - 1)
        iy = np.clip((a.y[idx] / ch).astype(int), 0, ny - 1)
        a.cell_id[idx] = (iy * nx + ix).astype(np.int16)
        if self.world.playground_enabled:
            x0, y0, x1, y1 = self.world.playground_bounds
            a.in_playground[idx] = (a.x[idx] >= x0) & (a.x[idx] <= x1) & (a.y[idx] >= y0) & (a.y[idx] <= y1)
        else:
            a.in_playground[idx] = False
        self._update_heading(idx, x_before, y_before)

        self.playscore.observe_actions(actions[alive])

    def _update_heading(self, idx: np.ndarray, x0: np.ndarray, y0: np.ndarray) -> None:
        """Heading = direction of the last move of more than 1e-6 in (no random draw)."""
        a = self.agents
        dx = a.x[idx].astype(np.float64) - x0
        dy = a.y[idx].astype(np.float64) - y0
        moved = np.hypot(dx, dy) > 1e-6
        if moved.any():
            a.heading[idx[moved]] = np.arctan2(dy[moved], dx[moved]).astype(np.float32)

    def _heading_moves(self, ii: np.ndarray, act: np.ndarray, length: float) -> None:
        """RUN_ON along the agent's heading, TURN_BACK against it, `length` inches."""
        a = self.agents
        h = a.heading[ii].astype(np.float64) + np.where(act == ACT_TURN_BACK, math.pi, 0.0)
        a.x[ii] = np.clip(a.x[ii] + length * np.cos(h), 0.5, self.world.width - 0.5)
        a.y[ii] = np.clip(a.y[ii] + length * np.sin(h), 0.5, self.world.height - 0.5)

    def _object_moves(self, ii: np.ndarray, act: np.ndarray, length: float) -> None:
        """BACK_OFF: radially away from the nearest object; CIRCLE: counter-clockwise around it
        at the current radius (at least 1 in), `length` inches of path."""
        a = self.agents
        objs = self.world.play_objects
        ox = np.array([o.x for o in objs], dtype=np.float64)
        oy = np.array([o.y for o in objs], dtype=np.float64)
        x = a.x[ii].astype(np.float64)
        y = a.y[ii].astype(np.float64)
        j = np.argmin((x[:, None] - ox[None, :]) ** 2 + (y[:, None] - oy[None, :]) ** 2, axis=1)
        vx, vy = x - ox[j], y - oy[j]
        r = np.hypot(vx, vy)
        ang = np.where(r > 1e-6, np.arctan2(vy, vx), 0.0)
        rad = np.maximum(r, 1.0)
        back = act == ACT_BACK_OFF
        nx = np.where(back, x + length * np.cos(ang), ox[j] + rad * np.cos(ang + length / rad))
        ny = np.where(back, y + length * np.sin(ang), oy[j] + rad * np.sin(ang + length / rad))
        a.x[ii] = np.clip(nx, 0.5, self.world.width - 0.5).astype(np.float32)
        a.y[ii] = np.clip(ny, 0.5, self.world.height - 0.5).astype(np.float32)


    def _free_pre(self, alive: np.ndarray, actions: np.ndarray) -> dict[str, np.ndarray]:
        """Agents whose decision action is free, and their state before the action."""
        a = self.agents
        idx = np.flatnonzero(alive)
        act = actions[idx]
        free = np.isin(act, (ACT_EXPLORE, ACT_SOCIAL, ACT_RUN_ON, ACT_TURN_BACK))
        if self.world.playground_enabled and self.world.play_objects:
            free |= np.isin(act, OBJECT_FAMILY)
        F = idx[free]
        return {"F": F, "act": act[free].copy(), "x": a.x[F].copy(), "y": a.y[F].copy(),
                "curiosity": a.curiosity[F].copy(), "boredom": a.boredom[F].copy(),
                "social_drive": a.social_drive[F].copy(), "heading": a.heading[F].copy()}

    def _run_free_substeps(self, pre: dict[str, np.ndarray]) -> None:
        """Replay the free agents' decision as K sub-steps (P4-8). The decision-level move and
        curiosity / boredom / social relief are undone; each sub-step either repeats the
        decision action (`policy.substep_mode` continue) or lets the policy re-choose among
        EXPLORE / SOCIAL / MANIPULATE (rechoose; own RNG stream), and the agent moves 1/K of a
        decision's reach (random walks with sd / sqrt(K)) with 1/K of the relief. Everything
        else the decision did (fatigue, object nudges, biology draws) stands; feeding,
        nursing, conception, stress and mortality run per decision from where agents end."""
        F = pre["F"]
        K = self.free_substeps
        if F.size == 0:
            if self.ball_physics:  # balls keep rolling through the sub-steps
                for _ in range(K):
                    self._roll_balls()
            return
        a = self.agents
        d = self.cfg.drives
        phys = self.ball_physics
        r = self._sub_rng
        for k in ("x", "y", "curiosity", "boredom", "social_drive", "heading"):
            getattr(a, k)[F] = pre[k]
        allowed = np.zeros((F.size, N_ACTIONS), dtype=bool)
        allowed[:, ACT_EXPLORE] = True
        allowed[:, ACT_SOCIAL] = True
        allowed[:, ACT_RUN_ON] = True  # action space v2 (never read by the heuristic)
        allowed[:, ACT_TURN_BACK] = True
        objs = self.world.play_objects if self.world.playground_enabled else []
        if objs:
            allowed[:, ACT_MANIPULATE] = True
            allowed[:, ACT_BACK_OFF] = True
            allowed[:, ACT_CIRCLE] = True
        ox = np.array([o.x for o in objs], dtype=np.float64)
        oy = np.array([o.y for o in objs], dtype=np.float64)
        sq = math.sqrt(K)
        sd_e = 10.0 * self.dt_ref * 10 / sq  # EXPLORE walk, as in _execute_actions
        sd_s = 3.0 * self.dt_ref * 10 / sq  # SOCIAL walk
        step_m = 7.0 * self.reach / K  # MANIPULATE approach speed
        cur_rel = d.curiosity_decay_on_novel / K
        bor_rel = d.boredom_decay_on_vary / K
        xmax, ymax = self.world.width - 0.5, self.world.height - 0.5
        nx, ny = self.cfg.geometry.n_cells_x, self.cfg.geometry.n_cells_y
        cw, ch = self.world.width / nx, self.world.height / ny
        tracing = self.trace is not None
        mode = self.cfg.policy.substep_mode
        if mode == "auto":
            mode = "continue" if self.cfg.policy.kind == "need_driven" else "rechoose"
        nov = self.novelty
        for j in range(K):
            self._nov_t = self.day + j * self.dt_ref / K  # what the policy observes now
            if phys:  # balls moved in the previous sub-step
                ox = np.array([o.x for o in objs], dtype=np.float64)
                oy = np.array([o.y for o in objs], dtype=np.float64)
            pre_j = None
            if tracing:
                pre_j = {"curiosity": a.curiosity[F].copy(), "boredom": a.boredom[F].copy(),
                         "social_drive": a.social_drive[F].copy(),
                         "cell": a.cell_id[F].astype(int)}
            if mode == "continue":  # the decision action at every sub-step
                act = pre["act"].astype(np.int8)
            else:  # the policy re-chooses among the free actions
                act = self.policy.choose(self, F, allowed, rng=r)
            xs, ys = a.x[F].copy(), a.y[F].copy()  # for the heading (no draws)
            a.recent_action[F] = act  # what observation v3 shows at the next call
            ii = F[act == ACT_EXPLORE]
            if ii.size:
                a.x[ii] = np.clip(a.x[ii] + r.normal(0, sd_e, ii.size), 0.5, xmax)
                a.y[ii] = np.clip(a.y[ii] + r.normal(0, sd_e, ii.size), 0.5, ymax)
                if not nov:  # with novelty the relief follows the place (below)
                    a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - cur_rel)
                a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - 0.5 * bor_rel)
            ii = F[act == ACT_SOCIAL]
            if ii.size:
                a.x[ii] = np.clip(a.x[ii] + r.normal(0, sd_s, ii.size), 0.5, xmax)
                a.y[ii] = np.clip(a.y[ii] + r.normal(0, sd_s, ii.size), 0.5, ymax)
                a.social_drive[ii] = np.maximum(0.0, a.social_drive[ii] - 0.3 / K)
                a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - bor_rel)
            ii = F[act == ACT_MANIPULATE]
            if ii.size:
                d2 = (a.x[ii, None] - ox[None, :]) ** 2 + (a.y[ii, None] - oy[None, :]) ** 2
                jo = np.argmin(d2, axis=1)
                dx, dy = ox[jo] - a.x[ii], oy[jo] - a.y[ii]
                dist = np.hypot(dx, dy) + 1e-6
                stp = np.minimum(step_m, dist)
                a.x[ii] = np.clip(a.x[ii] + dx / dist * stp, 0.5, xmax)
                a.y[ii] = np.clip(a.y[ii] + dy / dist * stp, 0.5, ymax)
                if not phys:  # with physics the relief follows the ball (_ball_pushes)
                    a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - cur_rel)
                    a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - bor_rel)
            run = (act == ACT_RUN_ON) | (act == ACT_TURN_BACK)  # action space v2
            if run.any():
                ii = F[run]
                self._heading_moves(ii, act[run], sd_e * math.sqrt(math.pi / 2))
                if not nov:
                    a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - cur_rel)
                a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - 0.5 * bor_rel)
            obj = (act == ACT_BACK_OFF) | (act == ACT_CIRCLE)
            if obj.any():
                ii = F[obj]
                self._object_moves(ii, act[obj], 0.6 * step_m)
                if not phys:
                    a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - cur_rel)
                    a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - bor_rel)
            if phys:
                self._ball_pushes(F, act, xs, ys, cur_rel, bor_rel)
            if nov:
                self._place_novelty(F, act, self.day + (j + 1) * self.dt_ref / K, cur_rel)
            self._update_heading(F, xs, ys)
            ix = np.clip((a.x[F] / cw).astype(int), 0, nx - 1)
            iy = np.clip((a.y[F] / ch).astype(int), 0, ny - 1)
            a.cell_id[F] = (iy * nx + ix).astype(np.int16)
            if self.world.playground_enabled:
                x0, y0, x1, y1 = self.world.playground_bounds
                a.in_playground[F] = ((a.x[F] >= x0) & (a.x[F] <= x1)
                                      & (a.y[F] >= y0) & (a.y[F] <= y1))
            if tracing:
                self.trace.micro(self, F, j, act, pre_j)
            if phys:  # after the trace, which saw the contacts against these positions
                self._roll_balls()

    def _ball_pushes(self, F: np.ndarray, act: np.ndarray, x0: np.ndarray, y0: np.ndarray,
                     cur_rel: float, bor_rel: float) -> None:
        """Ball physics (P4-13): every free agent whose move ended in contact with its nearest
        ball and brought it closer to the ball's centre by u > 0 pushes it by kappa * u along the
        agent-to-ball direction. Object-family actions relieve curiosity / boredom in proportion
        to the speed their contact gave the ball (full relief at a full-speed MANIPULATE contact,
        none when holding still, at a tunnel or ramp, or without contact). No random draw."""
        a = self.agents
        balls = [o for o in self.world.play_objects if o.kind == "ball"]
        scale = np.zeros(F.size)
        if balls:
            bx = np.array([o.x for o in balls], dtype=np.float64)
            by = np.array([o.y for o in balls], dtype=np.float64)
            br = np.array([o.radius for o in balls], dtype=np.float64)
            x1 = a.x[F].astype(np.float64)
            y1 = a.y[F].astype(np.float64)
            d1 = np.hypot(x1[:, None] - bx[None, :], y1[:, None] - by[None, :])
            j = np.argmin(d1, axis=1)
            dj = d1[np.arange(F.size), j]
            u = np.hypot(x0 - bx[j], y0 - by[j]) - dj
            push = (dj <= br[j] + CONTACT_SLACK) & (u > 0.0)
            if push.any():
                k = np.flatnonzero(push)
                jk = j[k]
                ex, ey = bx[jk] - x1[k], by[jk] - y1[k]
                n = np.hypot(ex, ey)
                mx, my = x1[k] - x0[k], y1[k] - y0[k]  # at the centre: along the own move
                mn = np.maximum(np.hypot(mx, my), 1e-12)
                at_c = n < 1e-6
                n = np.maximum(n, 1e-12)
                ex = np.where(at_c, mx / mn, ex / n)
                ey = np.where(at_c, my / mn, ey / n)
                dv = BALL_KAPPA * u[k]
                dvx = np.zeros(len(balls))
                dvy = np.zeros(len(balls))
                np.add.at(dvx, jk, dv * ex)
                np.add.at(dvy, jk, dv * ey)
                for b, o in enumerate(balls):
                    if dvx[b] != 0.0 or dvy[b] != 0.0:
                        o.vx = float(o.vx + dvx[b])
                        o.vy = float(o.vy + dvy[b])
                scale[k] = np.minimum(1.0, dv / self.ball_v_ref) * self.consequence_gain
                self._ball_stats["pushes"] += int(k.size)
                self._ball_stats["object_family_pushes"] += int(
                    np.isin(act[k], OBJECT_FAMILY).sum())
        obj = np.isin(act, OBJECT_FAMILY)
        ii = F[obj]
        if ii.size:
            sc = scale[obj]
            a.curiosity[ii] = np.maximum(0.0, a.curiosity[ii] - cur_rel * sc)
            a.boredom[ii] = np.maximum(0.0, a.boredom[ii] - bor_rel * sc)

    def nov_bin(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Grid bin index of positions (novelty-based curiosity, P4-14)."""
        G = self.nov_G
        ix = np.clip((np.asarray(x, dtype=np.float64) / (self.world.width / G)).astype(int),
                     0, G - 1)
        iy = np.clip((np.asarray(y, dtype=np.float64) / (self.world.height / G)).astype(int),
                     0, G - 1)
        return iy * G + ix

    def place_novelty(self, idx: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
        """1 - exp(-(t - last visit) / tau) of bins `b` for animals `idx` (1 if never)."""
        return 1.0 - np.exp(-(t - self._visit_t[idx, b]) / self.nov_tau)

    def _place_novelty(self, F: np.ndarray, act: np.ndarray, t: float, cur_rel: float) -> None:
        """Novelty-based curiosity (P4-14): each free animal reads the novelty of the bin it
        ended this sub-step in and marks it visited at `t`; locomotor-family actions relieve
        curiosity by consequence_gain x the per-sub-step amount x that novelty. No draw."""
        a = self.agents
        b = self.nov_bin(a.x[F], a.y[F])
        n = self.place_novelty(F, b, t)
        self._visit_t[F, b] = t
        loco = np.isin(act, LOCO_FAMILY)
        ii = F[loco]
        if ii.size:
            a.curiosity[ii] = np.maximum(
                0.0, a.curiosity[ii] - self.consequence_gain * cur_rel * n[loco])

    def _roll_balls(self) -> None:
        """One sub-step of rolling: move by the velocity, reflect at the playground bounds with
        half the normal speed, decay by the friction factor, stop below BALL_STOP."""
        x0, y0, x1, y1 = self.world.playground_bounds
        f = self.ball_friction
        for o in self.world.play_objects:
            if o.kind != "ball" or (o.vx == 0.0 and o.vy == 0.0):
                continue
            nx, ny = o.x + o.vx, o.y + o.vy
            if nx < x0 or nx > x1:
                nx = min(max(nx, x0), x1)
                o.vx = -BALL_RESTITUTION * o.vx
            if ny < y0 or ny > y1:
                ny = min(max(ny, y0), y1)
                o.vy = -BALL_RESTITUTION * o.vy
            self._ball_stats["rolled_in"] += math.hypot(nx - o.x, ny - o.y)
            o.x, o.y = float(nx), float(ny)
            o.vx, o.vy = o.vx * f, o.vy * f
            if math.hypot(o.vx, o.vy) < BALL_STOP:
                o.vx = o.vy = 0.0

    def _move_toward(self, i: int, tx: float, ty: float, speed: float) -> None:
        """Per-decision move (callers only move on decision ticks)."""
        a = self.agents
        dx, dy = tx - a.x[i], ty - a.y[i]
        dist = float(np.hypot(dx, dy)) + 1e-6
        step = min(speed * self.reach, dist)  # reach per decision
        a.x[i] = float(np.clip(a.x[i] + dx / dist * step, 0.5, self.world.width - 0.5))
        a.y[i] = float(np.clip(a.y[i] + dy / dist * step, 0.5, self.world.height - 0.5))

    def _jitter(self, i: int, scale: float) -> None:
        a = self.agents
        a.x[i] = float(np.clip(a.x[i] + self.rng.normal(0, scale * self.dt_days * 10), 0.5, self.world.width - 0.5))
        a.y[i] = float(np.clip(a.y[i] + self.rng.normal(0, scale * self.dt_days * 10), 0.5, self.world.height - 0.5))

    def _aggress(self, i: int) -> None:
        """One fight per AGGRESS decision (called on decision ticks only)."""
        a = self.agents
        alive = a.alive & (np.arange(a.capacity) != i)
        if not alive.any():
            return
        d2 = (a.x - a.x[i]) ** 2 + (a.y - a.y[i]) ** 2
        near = np.flatnonzero(alive & (d2 < 36.0) & (a.rank < a.rank[i]))
        if len(near) == 0:
            return
        j = int(self.rng.choice(near))
        a.wounds[j] = min(1.5, a.wounds[j] + 0.15)
        a.stress[j] = min(1.5, a.stress[j] + 0.1)
        a.rank[j] = max(0.0, a.rank[j] - 0.05)
        a.rank[i] = min(1.0, a.rank[i] + 0.02)

    def _nurse(self, i: int) -> None:
        """Active nursing: feed pups of the mother's own nest box that are within close reach."""
        a = self.agents
        nid = int(a.nest_id[i])
        if nid < 0:
            return
        pups = np.flatnonzero(a.alive & (a.role == ROLE_PUP) & (a.nest_id == nid))
        if pups.size:
            self._feed_by_nest(np.array([i]), pups, radius2=25.0, dt=self.dt_days)

    def _tick_cell_counts(self) -> np.ndarray:
        """Alive agents per cell, computed once per tick on first use (cached)."""
        if self._cell_counts_tick != self.tick:
            a = self.agents
            self._cell_counts = np.bincount(
                a.cell_id[a.alive].astype(int), minlength=self.world.n_cells
            )
            self._cell_counts_tick = self.tick
        return self._cell_counts

    def _feed_by_nest(
        self, moms: np.ndarray, pups: np.ndarray, *, radius2: float, dt: float
    ) -> None:
        """Relaxation-form nursing: each pup's deficit decays by exp(-rate * w * dt).

        w sums, over the lactating mothers of the pup's own nest box within sqrt(radius2)
        inches, maternal investment x milk share (1 up to nurse_max_pups pups in contact,
        then divided). Relief is proportional to the remaining deficit and composes exactly
        over sub-steps, so the daily amount a pup receives depends on contact time, not on
        how many ticks that time is cut into (the clipped per-contact amounts of phase 2d
        under-fed pups at coarse resolution). Deterministic; no RNG.
        """
        a = self.agents
        bio = self.cfg.biology
        rate = float(bio.nurse_rate_per_day)
        cap = float(bio.nurse_max_pups)
        mom_nest = a.nest_id[moms]
        pup_nest = a.nest_id[pups]
        # Nursing disturbance: a mother in a crowded cell nurses less effectively (reversible,
        # graded in local density; Calhoun phase C infant mortality). Off when coef == 0.
        coef = float(bio.nurse_disturb_coef)
        if coef > 0.0:
            counts = self._tick_cell_counts()
            cap_cell = max(1.0, self.world.capacity_design / self.world.n_cells)
            local_m = counts[a.cell_id[moms].astype(int)] / cap_cell
            disturb = np.exp(-coef * np.maximum(0.0, local_m - float(bio.nurse_disturb_density)))
        for nid in np.intersect1d(mom_nest, pup_nest):
            m_sel = mom_nest == nid
            mi = moms[m_sel]
            pj = pups[pup_nest == nid]
            d2 = (a.x[mi][:, None] - a.x[pj][None, :]) ** 2
            d2 += (a.y[mi][:, None] - a.y[pj][None, :]) ** 2
            contact = d2 < radius2  # (mothers, pups)
            n_contact = contact.sum(axis=1)
            if not n_contact.any():
                continue
            share = np.minimum(1.0, cap / np.maximum(1, n_contact))
            invest = a.maternal[mi].astype(np.float64)
            if coef > 0.0:
                invest = invest * disturb[m_sel]
            w = (contact * (invest * share)[:, None]).sum(axis=0)
            f = np.exp(-rate * w * dt)
            a.hunger[pj] = a.hunger[pj] * f
            a.thirst[pj] = a.thirst[pj] * f
            a.energy[pj] = 1.0 - (1.0 - a.energy[pj]) * f

    def _approach_mate(self, i: int) -> None:
        """ACT_MATE is courtship: approach the nearest eligible partner.

        Conception itself happens only in the once-per-day breeding pass, so the conception
        rate cannot depend on how often the per-tick action softmax is sampled.
        """
        a = self.agents
        bio = self.cfg.biology
        if a.age_days[i] < bio.maturity_days or a.role[i] == ROLE_WITHDRAWN:
            return
        partner_sex = SEX_M if a.sex[i] == SEX_F else SEX_F
        cand = a.alive & (a.sex == partner_sex) & (a.age_days >= bio.maturity_days)
        cand &= a.role != ROLE_WITHDRAWN
        cand &= a.gestating == 0
        if partner_sex == SEX_F:
            cand &= a.age_days <= bio.female_fertile_max_age_days
        if not cand.any():
            return
        d2 = (a.x - a.x[i]) ** 2 + (a.y - a.y[i]) ** 2
        near = np.flatnonzero(cand & (d2 < float(bio.mate_radius_in) ** 2))
        if len(near) == 0:
            return
        j = int(near[np.argmin(d2[near])])
        self._move_toward(i, float(a.x[j]), float(a.y[j]), 7.0)

    def _density_stress(self, alive: np.ndarray) -> None:
        a = self.agents
        d = self.cfg.drives
        dt = self.dt_days
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            return
        cell_counts = np.bincount(a.cell_id[alive].astype(int), minlength=self.world.n_cells)
        cells = a.cell_id[idx].astype(int)
        local = cell_counts[cells] / max(1.0, self.world.capacity_design / self.world.n_cells)
        gain = d.stress_density_gain * local
        # Weaned agents without a nest box (abandoned as pups) adopt the nearest box.
        homeless = (a.nest_id[idx] < 0) & (a.age_days[idx] >= self.cfg.biology.weaning_days)
        if homeless.any():
            hi = idx[homeless]
            d2n = (a.x[hi, None] - self._nest_x[None, :]) ** 2
            d2n += (a.y[hi, None] - self._nest_y[None, :]) ** 2
            a.nest_id[hi] = d2n.argmin(axis=1).astype(np.int16)
        nids = a.nest_id[idx].astype(int)
        # nest occupancy (abandoned pups with nest_id -1 occupy no box)
        housed = alive & (a.nest_id >= 0)
        nest_occ = np.bincount(a.nest_id[housed].astype(int), minlength=self.world.n_nests)
        cap = np.array([n.capacity for n in self.world.nests], dtype=np.float64)
        nclip = np.clip(nids, 0, self.world.n_nests - 1)
        over = (nids >= 0) & (nest_occ[nclip] > cap[nclip])
        # graded overfullness (occupants beyond capacity, relative) for developmental exposure
        over_frac = np.where(nids >= 0, np.maximum(0.0, nest_occ[nclip] / cap[nclip] - 1.0), 0.0)
        gain = gain + float(self.cfg.biology.nest_overcrowd_stress) * over
        # Social-breakdown pressure: full boost above the weaned-density threshold, a linear ramp
        # below it (breakdown_density_ramp; 0 = step). Mirrors warp density_stress_kernel.
        f_bd = self.cfg.biology.breakdown_factor(self._breakdown_density(alive))
        if f_bd > 0.0:
            gain = gain + float(self.cfg.biology.social_breakdown_stress_boost) * f_bd
        decision = self._decision_tick()
        # random nest kick for low-rank overcrowded agents: one 10 % chance per decision
        if decision:
            kick = over & (a.rank[idx] < 0.4) & (self.rng.random(idx.size) < 0.1)
            if kick.any():
                a.nest_id[idx[kick]] = self.rng.integers(
                    0, self.world.n_nests, size=int(kick.sum())
                )
        # Exact relaxation toward gain/decay over dt: equilibrium stress is smooth in local
        # density (a constant decay gave a hard density cliff) and the daily trajectory does
        # not depend on the tick resolution (the Euler step over-relaxed by ~1 % per tick at
        # 6 ticks/day). Mirrors warp density_stress_kernel.
        relax = -math.expm1(-d.stress_decay * dt)
        a.stress[idx] = np.clip(
            a.stress[idx] + (gain / d.stress_decay - a.stress[idx]) * relax, 0, 1.5
        )
        if decision:  # social withdrawal under high stress: a per-decision step
            with_mask = (a.stress[idx] > 0.9) & (a.social_drive[idx] > 0)
            a.social_drive[idx[with_mask]] = np.maximum(
                0.0, a.social_drive[idx[with_mask]] - 0.05
            )
        # Developmental imprinting (Calhoun): young exposed to crowded cells / overfull nests
        # lose social competence; the trait is frozen once mature. Mirrors Warp kernel.
        bio = self.cfg.biology
        young = a.age_days[idx] < bio.maturity_days
        if young.any():
            exposure = np.maximum(0.0, local - bio.imprint_density_threshold) + over_frac
            if bio.imprint_breakdown_exposure > 0.0 and f_bd > 0.0:
                # colony-wide: the social breakdown reaches every nest (mirrors Warp kernel)
                exposure = exposure + float(bio.imprint_breakdown_exposure) * f_bd
            yi = idx[young]
            a.competence[yi] = np.clip(
                a.competence[yi] - bio.imprint_rate * exposure[young] * dt, 0.0, 1.0
            )
            # Nulliparous maternal investment develops with competence (set at conception/birth
            # later); otherwise incompetent daughters would still seek out and nurse pups.
            yf = yi[a.sex[yi] == SEX_F]
            a.maternal[yf] = 0.8 * a.competence[yf]



    def _breakdown_density(self, alive: np.ndarray) -> float:
        """Density fraction that drives the social-breakdown stress switch."""
        bio = self.cfg.biology
        if bio.breakdown_density_counts == "weaned":
            n = int(np.count_nonzero(alive & (self.agents.age_days >= bio.weaning_days)))
        else:
            n = self.agents.n_alive
        return n / max(1, self.world.capacity_design)

    def _passive_nurse(self, alive: np.ndarray) -> None:
        """Lactating mothers at their nest box feed the pups of that box (not optional softmax).

        Nursing is per nest box: a litter whose mothers are dead, displaced, incompetent or
        too stressed is not rescued by mothers of other boxes (Calhoun: abandoned litters died).
        Only parous / gestating females (ROLE_NURSING, i.e. maternal investment > 0.5) nurse;
        a mother above the neglect stress threshold does not.
        """
        a = self.agents
        bio = self.cfg.biology
        moms = np.flatnonzero(
            alive
            & (a.sex == SEX_F)
            & (a.role == ROLE_NURSING)
            & (a.nest_id >= 0)
            & (a.stress <= bio.maternal_neglect_stress)
        )
        pups = np.flatnonzero(alive & (a.role == ROLE_PUP) & (a.nest_id >= 0))
        if moms.size == 0 or pups.size == 0:
            return
        self._feed_by_nest(moms, pups, radius2=64.0, dt=self.dt_days)

    def _daily_maternal_erosion(self, alive: np.ndarray) -> None:
        """Once per day: weaned females above maternal_erosion_stress lose maternal capacity
        irreversibly (rate x excess stress per day) and their current maternal investment is
        capped by it. Calhoun phase C/D: established mothers attacked and expelled their
        young and stopped nest building while conceptions went on to ~Day 920; juveniles
        exposed to the same conditions never acquired the capacity. Stress-driven only, no
        scheduled day; daily pass, so tick resolution cannot change it."""
        if (self.tick % self.cfg.ticks_per_day) != 0:
            return
        bio = self.cfg.biology
        if bio.maternal_erosion_rate <= 0.0:
            return
        a = self.agents
        af = np.flatnonzero(
            alive
            & (a.sex == SEX_F)
            & (a.age_days >= bio.weaning_days)
            & (a.stress > bio.maternal_erosion_stress)
        )
        if af.size == 0:
            return
        excess = a.stress[af].astype(np.float64) - float(bio.maternal_erosion_stress)
        a.maternal_cap[af] = np.maximum(
            0.0, a.maternal_cap[af] - float(bio.maternal_erosion_rate) * excess
        )
        a.maternal[af] = np.minimum(a.maternal[af], a.maternal_cap[af])

    def _daily_courtship_erosion(self, alive: np.ndarray) -> None:
        """Once per day: weaned males above courtship_erosion_stress lose courtship capacity
        irreversibly (rate x excess stress per day). Calhoun phase D: males ceased courting and
        territorial defence, so conceptions ended (~Day 920) while fertile females remained."""
        if (self.tick % self.cfg.ticks_per_day) != 0:
            return
        bio = self.cfg.biology
        if bio.courtship_erosion_rate <= 0.0:
            return
        a = self.agents
        am = np.flatnonzero(
            alive
            & (a.sex == SEX_M)
            & (a.age_days >= bio.weaning_days)
            & (a.stress > bio.courtship_erosion_stress)
        )
        if am.size == 0:
            return
        excess = a.stress[am].astype(np.float64) - float(bio.courtship_erosion_stress)
        a.courtship_cap[am] = np.maximum(
            0.0, a.courtship_cap[am] - float(bio.courtship_erosion_rate) * excess
        )

    def _daily_litter_abandonment(self, alive: np.ndarray) -> None:
        """Once per day: a nursing mother above the neglect stress threshold abandons her box's
        litter with probability litter_abandon_p; those pups lose their nest box (nest_id = -1)
        and are no longer nursed. Emergent from stress; no scheduled day."""
        if (self.tick % self.cfg.ticks_per_day) != 0:
            return
        bio = self.cfg.biology
        if bio.litter_abandon_p <= 0.0:
            return
        a = self.agents
        moms = np.flatnonzero(
            alive
            & (a.sex == SEX_F)
            & (a.role == ROLE_NURSING)
            & (a.nest_id >= 0)
            & (a.stress > bio.maternal_neglect_stress)
        )
        if moms.size == 0:
            return
        pups_mask = alive & (a.role == ROLE_PUP) & (a.nest_id >= 0)
        if not pups_mask.any():
            return
        draws = self.rng.random(moms.size)
        nests = np.unique(a.nest_id[moms[draws < bio.litter_abandon_p]])
        if nests.size == 0:
            return
        victims = np.flatnonzero(pups_mask & np.isin(a.nest_id, nests))
        if victims.size:
            a.nest_id[victims] = -1
            self._abandoned += int(victims.size)

    def _daily_breeding_pass(self, alive: np.ndarray) -> None:
        """Once per day: conceive eligible females that share a cell with a male."""
        if (self.tick % self.cfg.ticks_per_day) != 0:
            return
        a = self.agents
        bio = self.cfg.biology
        if self.day < bio.first_conception_min_day:
            return
        dens = a.n_alive / max(1, self.world.capacity_design)
        # suppression with density (behavioral-sink precursor) — no scheduled collapse day
        p_base = float(bio.breeding_p_base) * max(0.02, 1.0 - dens / max(1e-6, bio.menopause_density_threshold))
        females = np.flatnonzero(
            alive
            & (a.sex == SEX_F)
            & (a.age_days >= bio.maturity_days)
            & (a.age_days <= bio.female_fertile_max_age_days)
            & (a.gestating == 0)
            & (a.role != ROLE_WITHDRAWN)
            & (a.stress < 0.8)
            & (a.energy > 0.35)
        )
        males = np.flatnonzero(
            alive
            & (a.sex == SEX_M)
            & (a.age_days >= bio.maturity_days)
            & (a.role != ROLE_WITHDRAWN)
            & (a.stress < 0.85)
        )
        if females.size == 0 or males.size == 0:
            return
        floor = float(bio.fertility_cap_floor)
        width = float(bio.conception_density_width)
        if width > 0.0:  # behavioural sink: crowded cells conceive less
            dens_factor = self._conception_density_factor(females)
        # Per-cell mean male courtship capability: developmental competence x what adult-stage
        # stress has left of the courtship capacity.
        male_cells: dict[int, list[int]] = {}
        for m in males:
            male_cells.setdefault(int(a.cell_id[m]), []).append(int(m))
        male_comp = {
            c: float(np.mean(a.competence[ms] * a.courtship_cap[ms]))
            for c, ms in male_cells.items()
        }
        for j, f in enumerate(females):
            cands = male_cells.get(int(a.cell_id[f]), [])
            if not cands:
                continue
            c_f = float(a.competence[f])
            p = p_base * (1.0 - float(bio.breeding_stress_coef) * float(a.stress[f]))
            p *= c_f * male_comp[int(a.cell_id[f])]
            if floor < 1.0:  # fertility follows her own breakdown state
                p *= floor + (1.0 - floor) * float(a.maternal_cap[f])
            if width > 0.0:
                p *= float(dens_factor[j])
            if self.rng.random() < p:
                a.gestating[f] = bio.gestation_days
                a.role[f] = ROLE_NURSING
                a.maternal[f] = max(
                    float(a.maternal[f]), 0.85 * c_f * float(a.maternal_cap[f])
                )
                self._conceptions += 1
                self._last_conception_day = self.day
                self._conc_by_day[min(int(self.day), self._conc_by_day.size - 1)] += 1

    def _conception_density_factor(self, females: np.ndarray) -> np.ndarray:
        """Per-female conception factor from her cell's density: 1 below
        conception_density_onset, linear to 0 at onset + conception_density_width."""
        bio = self.cfg.biology
        counts = self._tick_cell_counts()
        cap_cell = max(1.0, self.world.capacity_design / self.world.n_cells)
        local = counts[self.agents.cell_id[females].astype(int)] / cap_cell
        excess = local - float(bio.conception_density_onset)
        return np.clip(1.0 - excess / float(bio.conception_density_width), 0.0, 1.0)

    def _reproduce(self, alive: np.ndarray) -> None:
        a = self.agents
        bio = self.cfg.biology
        births = np.flatnonzero(alive & (a.gestating > 0) & (a.gestating <= self.dt_days))
        for i in births:
            # birth this tick
            a.gestating[i] = 0.0
            if a.stress[i] > bio.maternal_neglect_stress and self.rng.random() < float(bio.stillbirth_neglect_p):
                continue  # stillbirth / neglect
            litter = int(np.clip(self.rng.normal(bio.litter_mean, bio.litter_sd), 1, 12))
            try:
                slots = a.free_slots(litter)
            except RuntimeError:
                break
            # Birth happens in the mother's nest; she returns there and pups stay until weaning.
            nid = int(a.nest_id[i])
            if nid >= 0:
                nest = self.world.nests[nid]
                a.x[i] = float(np.clip(nest.x, 0.5, self.world.width - 0.5))
                a.y[i] = float(np.clip(nest.y, 0.5, self.world.height - 0.5))
                a.cell_id[i] = nest.cell_id
            for s in slots:
                sex = int(self.rng.integers(0, 2))
                self._spawn(
                    int(s),
                    sex=sex,
                    age=0.0,
                    x=a.x[i] + float(self.rng.normal(0, 0.3)),
                    y=a.y[i] + float(self.rng.normal(0, 0.3)),
                    nest_id=nid,
                    cell_id=int(a.cell_id[i]),
                    role=ROLE_PUP,
                )
                self._births += 1
                self._last_young_day = self.day
            a.role[i] = ROLE_NURSING
            # Maternal investment reflects the mother's own social development and what
            # adult-stage stress has left of her maternal capacity.
            a.maternal[i] = 0.9 * float(a.competence[i]) * float(a.maternal_cap[i])
        a.n_alive = int(a.alive.sum())

    def _age_and_die(self, alive: np.ndarray) -> None:
        a = self.agents
        bio = self.cfg.biology
        dt = self.dt_days
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            return
        # Hazard per day, then the exact per-tick death probability 1 - exp(-h*dt): survival
        # over a day is exp(-h) at any tick resolution. Mirrors warp mortality_kernel.
        h = np.full(idx.size, bio.base_mortality_per_day, dtype=np.float64)
        # pups/juveniles: lower baseline, rely on neglect/hunger instead
        young = (a.role[idx] == ROLE_PUP) | (a.role[idx] == ROLE_JUVENILE)
        h = np.where(young, h * float(bio.young_mortality_scale), h)
        dens = a.n_alive / max(1, self.world.capacity_design)
        h = h + float(bio.density_mortality_scale) * (dens ** 2)
        h += bio.stress_mortality_scale * (a.stress[idx] ** 2)
        h += 0.02 * (a.wounds[idx] ** 2)
        h += np.where(a.age_days[idx] > a.lifespan[idx], 0.05, 0.0)  # old age, per individual
        starving = (a.hunger[idx] > 1.2) | (a.thirst[idx] > 1.2)
        h += np.where(starving, float(bio.starvation_hazard_per_day), 0.0)
        h += np.where(a.energy[idx] < 0.05, 0.2, 0.0)
        p = -np.expm1(-h * dt)
        dead = self.rng.random(idx.size) < p
        if dead.any():
            di = idx[dead]
            a.alive[di] = False
            a.role[di] = ROLE_DEAD
            self._deaths += int(dead.sum())
        a.n_alive = int(a.alive.sum())


    def _check_nan(self) -> None:
        a = self.agents
        fields = [a.hunger, a.thirst, a.stress, a.energy, a.x, a.y]
        for f in fields:
            if np.isnan(f[a.alive]).any():
                self._nan_count += 1
                np.nan_to_num(f, copy=False, nan=0.0)


    def _warp_post_step(self) -> None:
        """GPU stress + mortality + cell update via Warp (+ optional CUDA Graph)."""
        assert self.warp_engine is not None
        eng = self.warp_engine
        a = self.agents
        wp = eng._wp
        from universe25.warp_kernels.kernels import (
            density_stress_kernel,
            mortality_kernel,
            update_cells_kernel,
        )
        eng._host_cell_nest_counts(a)
        eng.upload(a, self.rng)
        b = eng._bufs
        n = a.capacity
        bio = self.cfg.biology
        d = self.cfg.drives
        dt = float(self.dt_days)
        dens_frac = float(a.n_alive / max(1, self.world.capacity_design))
        capacity_per_cell = float(self.world.capacity_design / max(1, self.world.n_cells))
        pg = self.world.playground_bounds
        b["dens_frac"].assign(np.array([dens_frac], dtype=np.float32))
        b["dens_social"].assign(np.array([self._breakdown_density(a.alive)], dtype=np.float32))
        b["event_scale"].assign(
            np.array([1.0 if self._decision_tick() else 0.0], dtype=np.float32)
        )

        def launches():
            wp.launch(
                density_stress_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["cell_id"], b["nest_id"], b["rank"], b["stress"], b["social_drive"],
                    b["cell_counts"], b["nest_occ"], b["nest_cap"], b["age_days"], b["competence"],
                    dt, float(d.stress_density_gain), float(d.stress_decay),
                    float(bio.nest_overcrowd_stress), capacity_per_cell, b["dens_social"],
                    float(bio.breakdown_threshold()), float(bio.breakdown_density_ramp),
                    float(bio.social_breakdown_stress_boost),
                    float(bio.maturity_days), float(bio.imprint_rate),
                    float(bio.imprint_density_threshold), float(bio.imprint_breakdown_exposure),
                    b["event_scale"],
                ],
                device=eng.device,
            )
            wp.launch(
                mortality_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["role"], b["stress"], b["wounds"], b["age_days"],
                    b["hunger"], b["thirst"], b["energy"], b["rng_states"],
                    dt, float(bio.base_mortality_per_day), float(bio.stress_mortality_scale),
                    b["lifespan"], float(bio.young_mortality_scale),
                    float(bio.density_mortality_scale), b["dens_frac"],
                    float(bio.starvation_hazard_per_day),
                ],
                device=eng.device,
            )
            wp.launch(
                update_cells_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["x"], b["y"], b["cell_id"], b["in_playground"],
                    float(self.world.width), float(self.world.height),
                    int(self.cfg.geometry.n_cells_x), int(self.cfg.geometry.n_cells_y),
                    1 if self.world.playground_enabled else 0,
                    float(pg[0]), float(pg[1]), float(pg[2]), float(pg[3]),
                ],
                device=eng.device,
            )
            eng.n_launches += 1

        if eng.use_graph and str(eng.device).startswith("cuda"):
            if not eng._graph_ready:
                if eng._warmup_left > 0:
                    launches()
                    wp.synchronize()
                    eng._warmup_left -= 1
                else:
                    wp.capture_begin(device=eng.device)
                    launches()
                    eng._graph = wp.capture_end(device=eng.device)
                    eng._graph_ready = True
                    # Stream capture records the launches without running them: replay now so
                    # the capture tick's post-step (stress, mortality, cells) is not skipped.
                    wp.capture_launch(eng._graph)
                    eng.n_graph_replays += 1
            else:
                wp.capture_launch(eng._graph)
                eng.n_graph_replays += 1
        else:
            launches()
        wp.synchronize()
        # download mutated fields
        prev_alive = int(a.n_alive)
        a.alive[:] = np.array(b["alive"].numpy(), dtype=bool)
        a.role[:] = np.array(b["role"].numpy(), dtype=np.int8)
        a.stress[:] = b["stress"].numpy()
        a.social_drive[:] = b["social_drive"].numpy()
        a.cell_id[:] = np.array(b["cell_id"].numpy(), dtype=np.int16)
        a.in_playground[:] = np.array(b["in_playground"].numpy(), dtype=bool)
        a.competence[:] = b["competence"].numpy()
        a.n_alive = int(a.alive.sum())
        if a.n_alive < prev_alive:
            self._deaths += prev_alive - a.n_alive

    def _log_metrics(self) -> None:
        a = self.agents
        alive = a.alive
        n = int(alive.sum())
        roles = {f"role_{r}": int(np.sum(alive & (a.role == r))) for r in range(7)}
        pg_occ = int(np.sum(alive & a.in_playground)) if n else 0
        # Free-choice preference V: among agents with energy>0.5 & stress<0.4, fraction in playground
        eligible = alive & (a.energy > 0.5) & (a.stress < 0.4)
        ne = int(eligible.sum())
        v = float(np.sum(eligible & a.in_playground) / ne) if ne > 0 else 0.0
        g = float(np.mean((a.energy[alive] > 0.5) & (a.stress[alive] < 0.4))) if n else 0.0
        # V without hopper users: six of the eight hoppers of cells 5, 6, 9, 10 and 16 nests lie
        # inside the playground box, so eating or drinking there counted as free choice.
        # Excludes agents whose last action was FORAGE / DRINK or that sit within 4 in of their
        # cell's food or water point (P4-5; the box and hoppers are calibrated geometry).
        hop = np.zeros(a.capacity, dtype=bool)
        ia = np.flatnonzero(alive)
        if ia.size:
            ca = a.cell_id[ia].astype(int)
            near = (np.hypot(a.x[ia] - self._cell_food[ca, 0], a.y[ia] - self._cell_food[ca, 1])
                    <= 4.0) | (np.hypot(a.x[ia] - self._cell_water[ca, 0],
                                        a.y[ia] - self._cell_water[ca, 1]) <= 4.0)
            used = (a.last_action[ia] == ACT_FORAGE) | (a.last_action[ia] == ACT_DRINK)
            hop[ia] = near | used
        elig_x = eligible & ~hop
        ne_x = int(elig_x.sum())
        v_x = float(np.sum(elig_x & a.in_playground) / ne_x) if ne_x > 0 else 0.0
        # Action entropy S over recent hist
        hist = self._action_hist.astype(np.float64)
        if hist.sum() > 0:
            p = hist / hist.sum()
            p = p[p > 0]
            entropy = float(-np.sum(p * np.log(p + 1e-12)))
        else:
            entropy = 0.0
        ps = self.playscore.components(v=v, g=g, action_entropy=entropy)
        adult_f = alive & (a.sex == SEX_F) & (a.age_days >= self.cfg.biology.maturity_days)
        adult_m = alive & (a.sex == SEX_M) & (a.age_days >= self.cfg.biology.maturity_days)
        row = {
            "tick": self.tick,
            "day": self.day,
            "n_alive": n,
            "n_peak": self._peak_n,
            "conceptions_cum": self._conceptions,
            "births_cum": self._births,
            "deaths_cum": self._deaths,
            "last_young_day": self._last_young_day,
            "last_surviving_young_day": self._last_surviving_young_day,
            "surv_births_cum": self._surv_births_cum,
            "last_conception_day": self._last_conception_day,
            "abandoned_cum": self._abandoned,
            "n_adult": int(np.sum(alive & (a.age_days >= self.cfg.biology.maturity_days))),
            "mean_competence_adult": float(
                a.competence[alive & (a.age_days >= self.cfg.biology.maturity_days)].mean()
            ) if np.any(alive & (a.age_days >= self.cfg.biology.maturity_days)) else 1.0,
            "mean_maternal_cap_adult_f": (
                float(a.maternal_cap[adult_f].mean()) if adult_f.any() else 1.0
            ),
            "mean_courtship_cap_adult_m": (
                float(a.courtship_cap[adult_m].mean()) if adult_m.any() else 1.0
            ),
            "playground_occupancy": pg_occ,
            "playground_frac": pg_occ / max(1, n),
            "free_choice_V": v,
            "free_choice_V_excl_hopper_unvalidated": v_x,
            "gate_G": g,
            "action_entropy_S": entropy,
            "playscore_F_unvalidated": ps["F"],
            "playscore_V_unvalidated": ps["V"],
            "playscore_D_unvalidated": ps["D"],
            "playscore_S_unvalidated": ps["S"],
            "playscore_G_unvalidated": ps["G"],
            "playscore_unvalidated": ps["PlayScore"],
            "mean_stress": float(a.stress[alive].mean()) if n else 0.0,
            "mean_energy": float(a.energy[alive].mean()) if n else 0.0,
            "mean_hunger": float(a.hunger[alive].mean()) if n else 0.0,
            "withdrawn": roles.get("role_6", 0),
            "nan_count": self._nan_count,
            "backend": self.backend,
            "device": self.device,
            **roles,
        }
        self.logger.log(row)
        # reset short action hist window
        self._action_hist[:] = 0
        self.playscore.reset_window()

    # ------------------------------------------------------------------ run
    def run(self) -> dict[str, Any]:
        t0 = time.perf_counter()
        total_ticks = int(self.cfg.days * self.cfg.ticks_per_day)
        for _ in range(total_ticks):
            self.step()
            if self.agents.n_alive == 0 and self.day > 100:
                break
        wall = time.perf_counter() - t0
        self.logger.close()
        learn_summary = self.policy.finish(self) if hasattr(self.policy, "finish") else None
        trace_files = self.trace.close() if self.trace is not None else []
        # final snapshot
        self.snapshots.write(self.day, self.agents, self.world)
        summary = {
            "seed": self.cfg.seed,
            "arm_label": self.cfg.arm_label,
            "backend": self.backend,
            "device": self.device,
            "days_simulated": self.day,
            "ticks": self.tick,
            "wall_seconds": wall,
            "peak_n": self._peak_n,
            "peak_day": self._peak_day,
            "final_n": self.agents.n_alive,
            "births": self._births,
            "deaths": self._deaths,
            "conceptions": self._conceptions,
            "last_young_day": self._last_young_day,
            "last_surviving_young_day": self._last_surviving_young_day,
            "surviving_birth_cessation_day": surviving_birth_cessation_day(
                self._surv_births_by_day
            ),
            "surviving_births": self._surv_births_cum,
            "last_conception_day": self._last_conception_day,
            "conception_cessation_day": rate_cessation_day(self._conc_by_day),
            "abandoned_pups": self._abandoned,
            "nan_count": self._nan_count,
            "playground_enabled": self.world.playground_enabled,
            "n_nests": self.world.n_nests,
            "n_play_objects": len(self.world.play_objects),
            "ball_physics": self.ball_physics,
            "ball_stats": dict(self._ball_stats) if self.ball_physics else None,
            "cuda_graph": self.cuda_graph.status(),
            "warp": None if self.warp_engine is None else self.warp_engine.status(),
            "trace_files": trace_files,
            "policy_kind": self.cfg.policy.kind,
            "learn": learn_summary,
        }
        (self.out_dir / "run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
