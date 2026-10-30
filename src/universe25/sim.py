"""Universe 25 simulator: need-driven agents, density stress, playground (no play reward)."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from universe25.agents.state import (
    ACT_AGGRESS,
    ACT_DRINK,
    ACT_EXPLORE,
    ACT_FORAGE,
    ACT_MANIPULATE,
    ACT_MATE,
    ACT_NEST,
    ACT_NURSE,
    ACT_REST,
    ACT_SOCIAL,
    ACT_WITHDRAW,
    N_ACTIONS,
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
from universe25.config import SimConfig
from universe25.metrics.logger import MetricsLogger
from universe25.metrics.playscore import PlayScoreAccumulator
from universe25.io.snapshots import SnapshotWriter
from universe25.rng import make_rng
from universe25.world.geometry import World, build_world


class Universe25Sim:
    def __init__(self, cfg: SimConfig, out_dir: Path):
        self.cfg = cfg
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.rng = make_rng(cfg.seed)
        self.backend, self.device = pick_backend(cfg.backend, cfg.device)
        self.world: World = build_world(cfg.geometry, cfg.playground, seed=cfg.seed)
        self.agents = AgentSoA.create(cfg.max_agents)
        self.tick = 0
        self.day = 0.0
        self.dt_days = 1.0 / cfg.ticks_per_day
        self.food = np.full(self.world.n_cells, cfg.resources.food_refill_per_tick, dtype=np.float64)
        self.water = np.full(self.world.n_cells, cfg.resources.water_refill_per_tick, dtype=np.float64)
        self.logger = MetricsLogger(self.out_dir / "metrics.parquet")
        self.playscore = PlayScoreAccumulator()
        self.snapshots = SnapshotWriter(self.out_dir / "snapshots")
        self._action_hist = np.zeros(N_ACTIONS, dtype=np.int64)
        self._conceptions = 0
        self._births = 0
        self._deaths = 0
        self._last_young_day = 0.0
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
        a.in_playground[slot] = self.world.in_playground(a.x[slot], a.y[slot])

    # ------------------------------------------------------------------ step
    def step(self) -> None:
        a = self.agents
        alive = a.alive
        if not alive.any():
            self.tick += 1
            self.day = self.tick * self.dt_days
            return

        self._refill_resources()
        self._update_drives(alive)
        self._assign_roles(alive)
        actions = self._select_actions(alive)
        self._execute_actions(alive, actions)
        self._density_stress(alive)
        self._reproduce(alive)
        self._age_and_die(alive)
        self._check_nan()

        a.n_alive = int(a.alive.sum())
        if a.n_alive > self._peak_n:
            self._peak_n = a.n_alive
            self._peak_day = self.day

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
        else:
            per = self.cfg.resources.scarce_food_per_day / self.cfg.ticks_per_day
            self.food += per / max(1, self.world.n_cells)
            self.water[:] = self.cfg.resources.water_refill_per_tick

    def _update_drives(self, alive: np.ndarray) -> None:
        d = self.cfg.drives
        dt = self.dt_days
        a = self.agents
        idx = alive
        a.hunger[idx] = np.clip(a.hunger[idx] + d.hunger_gain_per_day * dt, 0, 1.5)
        a.thirst[idx] = np.clip(a.thirst[idx] + d.thirst_gain_per_day * dt, 0, 1.5)
        a.curiosity[idx] = np.clip(a.curiosity[idx] + d.curiosity_gain * dt, 0, 1.5)
        a.boredom[idx] = np.clip(a.boredom[idx] + d.boredom_gain * dt, 0, 1.5)
        a.social_drive[idx] = np.clip(a.social_drive[idx] + d.social_drive_gain * dt, 0, 1.5)
        # energy homeostasis: decays with activity proxied by fatigue
        a.energy[idx] = np.clip(a.energy[idx] - 0.15 * dt - 0.1 * a.fatigue[idx] * dt, 0, 1)
        a.age_days[idx] += dt
        if a.gestating[idx].any():
            gest = idx & (a.gestating > 0)
            a.gestating[gest] = np.maximum(0.0, a.gestating[gest] - dt)

    def _assign_roles(self, alive: np.ndarray) -> None:
        a = self.agents
        bio = self.cfg.biology
        idx = np.flatnonzero(alive)
        for i in idx:
            age = a.age_days[i]
            if age < bio.weaning_days:
                a.role[i] = ROLE_PUP
            elif age < bio.maturity_days:
                a.role[i] = ROLE_JUVENILE
            elif a.stress[i] > 0.85 and a.social_drive[i] < 0.2 and a.aggression[i] < 0.15:
                a.role[i] = ROLE_WITHDRAWN  # beautiful ones
            elif a.sex[i] == SEX_F:
                if a.maternal[i] > 0.5 and (a.gestating[i] > 0 or a.role[i] == ROLE_NURSING):
                    a.role[i] = ROLE_NURSING
                else:
                    a.role[i] = ROLE_BREEDING_FEMALE
            else:
                # males: top rank in cell -> territorial
                a.role[i] = ROLE_TERRITORIAL_MALE if a.rank[i] > 0.55 else ROLE_SUBORDINATE_MALE

    def _select_actions(self, alive: np.ndarray) -> np.ndarray:
        """Utility-based action selection. No play utility term."""
        a = self.agents
        n = a.capacity
        actions = np.full(n, ACT_REST, dtype=np.int8)
        d = self.cfg.drives
        scarce = self.cfg.resources.mode == "scarce"
        idx = np.flatnonzero(alive)
        # Precompute utilities for active agents (vectorized where easy)
        for i in idx:
            u = np.zeros(N_ACTIONS, dtype=np.float64)
            u[ACT_FORAGE] = a.hunger[i] * 2.0
            u[ACT_DRINK] = a.thirst[i] * 2.2
            u[ACT_REST] = a.fatigue[i] * 1.5 + (1.0 - a.energy[i])
            u[ACT_NEST] = 0.3 + 0.4 * (a.role[i] == ROLE_NURSING)
            u[ACT_SOCIAL] = a.social_drive[i] * (1.0 - 0.7 * (a.role[i] == ROLE_WITHDRAWN))
            u[ACT_EXPLORE] = a.curiosity[i] * 0.9 + a.boredom[i] * 0.5
            # Manipulate playground objects: curiosity/boredom only — NOT a play reward
            if self.world.playground_enabled:
                u[ACT_MANIPULATE] = (a.curiosity[i] * 0.7 + a.boredom[i] * 0.8) * (
                    1.2 if a.energy[i] > 0.5 and a.stress[i] < 0.4 else 0.3
                )
            else:
                u[ACT_MANIPULATE] = -1.0
            agg = a.aggression[i] + (d.aggression_scarce_boost if scarce else 0.0)
            u[ACT_AGGRESS] = agg * a.stress[i] * (1.5 if scarce else 0.6)
            u[ACT_MATE] = (
                0.9
                * (a.age_days[i] >= self.cfg.biology.maturity_days)
                * (a.stress[i] < 0.75)
                * (a.role[i] != ROLE_WITHDRAWN)
                * (a.energy[i] > 0.4)
            )
            u[ACT_NURSE] = a.maternal[i] * 1.4 * (a.sex[i] == SEX_F)
            u[ACT_WITHDRAW] = a.stress[i] * 1.2 * (1.0 - a.social_drive[i])
            # Softmax sample
            u = u - u.max()
            p = np.exp(np.clip(u, -20, 20))
            p = p / p.sum()
            actions[i] = int(self.rng.choice(N_ACTIONS, p=p))
        return actions

    def _execute_actions(self, alive: np.ndarray, actions: np.ndarray) -> None:
        a = self.agents
        d = self.cfg.drives
        dt = self.dt_days
        idx = np.flatnonzero(alive)
        for i in idx:
            act = int(actions[i])
            a.last_action[i] = act
            self._action_hist[act] += 1
            cell = int(a.cell_id[i])
            if act == ACT_FORAGE:
                take = min(0.35, self.food[cell])
                self.food[cell] -= take
                a.hunger[i] = max(0.0, a.hunger[i] - take)
                a.energy[i] = min(1.0, a.energy[i] + 0.25 * take)
                self._move_toward(i, *self.world.cells[cell].food_xy, speed=8.0)
                a.fatigue[i] = min(1.5, a.fatigue[i] + d.fatigue_gain_active * dt)
            elif act == ACT_DRINK:
                take = min(0.35, self.water[cell])
                self.water[cell] -= take
                a.thirst[i] = max(0.0, a.thirst[i] - take)
                self._move_toward(i, *self.world.cells[cell].water_xy, speed=8.0)
            elif act == ACT_REST:
                a.fatigue[i] = max(0.0, a.fatigue[i] - d.fatigue_recovery_rest * dt)
                a.energy[i] = min(1.0, a.energy[i] + 0.1 * dt)
            elif act == ACT_NEST:
                nid = int(a.nest_id[i])
                if nid >= 0:
                    nest = self.world.nests[nid]
                    self._move_toward(i, nest.x, nest.y, speed=6.0)
                a.stress[i] = max(0.0, a.stress[i] - 0.05)
            elif act == ACT_SOCIAL:
                a.social_drive[i] = max(0.0, a.social_drive[i] - 0.3)
                a.boredom[i] = max(0.0, a.boredom[i] - d.boredom_decay_on_vary)
                self._jitter(i, 3.0)
            elif act == ACT_EXPLORE:
                a.curiosity[i] = max(0.0, a.curiosity[i] - d.curiosity_decay_on_novel)
                a.boredom[i] = max(0.0, a.boredom[i] - d.boredom_decay_on_vary * 0.5)
                self._jitter(i, 10.0)
            elif act == ACT_MANIPULATE:
                # Approach nearest playground object; satisfy curiosity/boredom only
                if self.world.play_objects:
                    obj = min(
                        self.world.play_objects,
                        key=lambda o: (o.x - a.x[i]) ** 2 + (o.y - a.y[i]) ** 2,
                    )
                    self._move_toward(i, obj.x, obj.y, speed=7.0)
                    # nudge object slightly (manipulable)
                    obj.x = float(np.clip(obj.x + self.rng.normal(0, 0.4), self.world.playground_bounds[0], self.world.playground_bounds[2]))
                    obj.y = float(np.clip(obj.y + self.rng.normal(0, 0.4), self.world.playground_bounds[1], self.world.playground_bounds[3]))
                a.curiosity[i] = max(0.0, a.curiosity[i] - d.curiosity_decay_on_novel)
                a.boredom[i] = max(0.0, a.boredom[i] - d.boredom_decay_on_vary)
                a.fatigue[i] = min(1.5, a.fatigue[i] + 0.5 * d.fatigue_gain_active * dt)
            elif act == ACT_AGGRESS:
                a.aggression[i] = min(1.5, a.aggression[i] + 0.05)
                # wound a nearby lower-rank agent
                self._aggress(i)
                self._jitter(i, 4.0)
            elif act == ACT_MATE:
                self._try_mate(i)
            elif act == ACT_NURSE:
                if a.stress[i] > self.cfg.biology.maternal_neglect_stress:
                    a.maternal[i] = max(0.0, a.maternal[i] - 0.05)  # neglect
                else:
                    a.maternal[i] = min(1.0, a.maternal[i] + 0.02)
                    # boost nearby pups' energy
                    self._nurse(i)
            elif act == ACT_WITHDRAW:
                a.social_drive[i] = max(0.0, a.social_drive[i] - 0.1)
                a.aggression[i] = max(0.0, a.aggression[i] - 0.05)
                # move to periphery
                self._move_toward(i, a.x[i] * 0.2 + 2.0, a.y[i] * 0.2 + 2.0, speed=3.0)

            a.cell_id[i] = self.world.cell_index(a.x[i], a.y[i])
            a.in_playground[i] = self.world.in_playground(a.x[i], a.y[i])

        self.playscore.observe_actions(actions[alive])

    def _move_toward(self, i: int, tx: float, ty: float, speed: float) -> None:
        a = self.agents
        dx, dy = tx - a.x[i], ty - a.y[i]
        dist = float(np.hypot(dx, dy)) + 1e-6
        step = min(speed * self.dt_days * 24.0, dist)  # speed inches/day-ish scaled
        a.x[i] = float(np.clip(a.x[i] + dx / dist * step, 0.5, self.world.width - 0.5))
        a.y[i] = float(np.clip(a.y[i] + dy / dist * step, 0.5, self.world.height - 0.5))

    def _jitter(self, i: int, scale: float) -> None:
        a = self.agents
        a.x[i] = float(np.clip(a.x[i] + self.rng.normal(0, scale * self.dt_days * 10), 0.5, self.world.width - 0.5))
        a.y[i] = float(np.clip(a.y[i] + self.rng.normal(0, scale * self.dt_days * 10), 0.5, self.world.height - 0.5))

    def _aggress(self, i: int) -> None:
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
        a = self.agents
        pups = a.alive & (a.role == ROLE_PUP)
        if not pups.any():
            return
        d2 = (a.x - a.x[i]) ** 2 + (a.y - a.y[i]) ** 2
        near = np.flatnonzero(pups & (d2 < 25.0))
        for j in near[:4]:
            a.energy[j] = min(1.0, a.energy[j] + 0.15)
            a.hunger[j] = max(0.0, a.hunger[j] - 0.2)

    def _try_mate(self, i: int) -> None:
        a = self.agents
        bio = self.cfg.biology
        if self.day < bio.first_conception_min_day:
            return
        dens = a.n_alive / max(1, self.world.capacity_design)
        if dens > bio.menopause_density_threshold and a.sex[i] == SEX_F:
            # reproductive collapse under crowding
            return
        if a.role[i] == ROLE_WITHDRAWN:
            return
        partner_sex = SEX_M if a.sex[i] == SEX_F else SEX_F
        cand = a.alive & (a.sex == partner_sex) & (a.age_days >= bio.maturity_days)
        cand &= a.role != ROLE_WITHDRAWN
        cand &= a.gestating == 0
        if not cand.any():
            return
        d2 = (a.x - a.x[i]) ** 2 + (a.y - a.y[i]) ** 2
        near = np.flatnonzero(cand & (d2 < 64.0))
        if len(near) == 0:
            return
        j = int(near[np.argmin(d2[near])])
        female = i if a.sex[i] == SEX_F else j
        if a.gestating[female] > 0:
            return
        if self.rng.random() < 0.25 * (1.0 - a.stress[female]):
            a.gestating[female] = bio.gestation_days
            a.role[female] = ROLE_NURSING
            self._conceptions += 1

    def _density_stress(self, alive: np.ndarray) -> None:
        a = self.agents
        d = self.cfg.drives
        dt = self.dt_days
        idx = np.flatnonzero(alive)
        # Approximate local density via cell occupancy
        cell_counts = np.bincount(a.cell_id[alive].astype(int), minlength=self.world.n_cells)
        for i in idx:
            c = int(a.cell_id[i])
            local = cell_counts[c] / max(1.0, self.world.capacity_design / self.world.n_cells)
            gain = d.stress_density_gain * local
            # nest invasion: overcrowded nests raise stress
            nid = int(a.nest_id[i])
            if nid >= 0:
                nest_occ = int(np.sum(alive & (a.nest_id == nid)))
                if nest_occ > self.world.nests[nid].capacity:
                    gain += 0.2
                    # kick subordinates out
                    if a.rank[i] < 0.4 and self.rng.random() < 0.1:
                        a.nest_id[i] = int(self.rng.integers(0, self.world.n_nests))
            a.stress[i] = np.clip(a.stress[i] + gain * dt - d.stress_decay * dt, 0, 1.5)
            # withdrawal drift
            if a.stress[i] > 0.9 and a.social_drive[i] > 0:
                a.social_drive[i] = max(0.0, a.social_drive[i] - 0.05)

    def _reproduce(self, alive: np.ndarray) -> None:
        a = self.agents
        bio = self.cfg.biology
        births = np.flatnonzero(alive & (a.gestating > 0) & (a.gestating <= self.dt_days))
        for i in births:
            # birth this tick
            a.gestating[i] = 0.0
            if a.stress[i] > bio.maternal_neglect_stress and self.rng.random() < 0.5:
                continue  # stillbirth / neglect
            litter = int(np.clip(self.rng.normal(bio.litter_mean, bio.litter_sd), 1, 12))
            try:
                slots = a.free_slots(litter)
            except RuntimeError:
                break
            for s in slots:
                sex = int(self.rng.integers(0, 2))
                self._spawn(
                    int(s),
                    sex=sex,
                    age=0.0,
                    x=a.x[i] + float(self.rng.normal(0, 0.3)),
                    y=a.y[i] + float(self.rng.normal(0, 0.3)),
                    nest_id=int(a.nest_id[i]),
                    cell_id=int(a.cell_id[i]),
                    role=ROLE_PUP,
                )
                self._births += 1
                self._last_young_day = self.day
            a.role[i] = ROLE_NURSING
            a.maternal[i] = 0.9
        a.n_alive = int(a.alive.sum())

    def _age_and_die(self, alive: np.ndarray) -> None:
        a = self.agents
        bio = self.cfg.biology
        dt = self.dt_days
        idx = np.flatnonzero(alive)
        for i in idx:
            p = bio.base_mortality_per_day * dt
            p += bio.stress_mortality_scale * (a.stress[i] ** 2) * dt
            p += 0.02 * (a.wounds[i] ** 2) * dt
            if a.age_days[i] > bio.max_age_days:
                p += 0.05 * dt
            if a.hunger[i] > 1.2 or a.thirst[i] > 1.2:
                p += 0.1 * dt
            if a.energy[i] < 0.05:
                p += 0.2 * dt
            if self.rng.random() < p:
                a.alive[i] = False
                a.role[i] = ROLE_DEAD
                self._deaths += 1
        a.n_alive = int(a.alive.sum())

    def _check_nan(self) -> None:
        a = self.agents
        fields = [a.hunger, a.thirst, a.stress, a.energy, a.x, a.y]
        for f in fields:
            if np.isnan(f[a.alive]).any():
                self._nan_count += 1
                np.nan_to_num(f, copy=False, nan=0.0)

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
        # Action entropy S over recent hist
        hist = self._action_hist.astype(np.float64)
        if hist.sum() > 0:
            p = hist / hist.sum()
            p = p[p > 0]
            entropy = float(-np.sum(p * np.log(p + 1e-12)))
        else:
            entropy = 0.0
        ps = self.playscore.components(v=v, g=g, action_entropy=entropy)
        row = {
            "tick": self.tick,
            "day": self.day,
            "n_alive": n,
            "n_peak": self._peak_n,
            "conceptions_cum": self._conceptions,
            "births_cum": self._births,
            "deaths_cum": self._deaths,
            "last_young_day": self._last_young_day,
            "playground_occupancy": pg_occ,
            "playground_frac": pg_occ / max(1, n),
            "free_choice_V": v,
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
            "nan_count": self._nan_count,
            "playground_enabled": self.world.playground_enabled,
            "n_nests": self.world.n_nests,
            "n_play_objects": len(self.world.play_objects),
        }
        (self.out_dir / "run.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
