"""Observation vector for learned policies (phase 4; docs/PHASE4_DESIGN.md section 1.3).

Egocentric, float32, built from the SoA state and the world geometry only. It contains no
PlayScore field, no play-named feature (the playground box is geometry, like a cell id), and
not the agent's own `lifespan` (hidden information). Pure NumPy, no RNG, so the reference path
stays deterministic and the builder can be timed and audited on its own.

Blocks (v5, 59 floats, novelty-based curiosity 2026-11-09: v4 plus the novelty of the place
bins ahead of and behind the animal along its heading. v4, 57 floats, ball physics 2026-11-09:
v3 plus the nearest object's mobility and speed; kept exactly for v4 weight files. v3, 55
floats, action space v2 2026-11-09: the last-action one-hot covers 15 actions,
the heading is appended, and the object block reads the objects' current positions; kept
exactly for v3 weight files. v2, 49 floats, 2026-11-06, is kept exactly for v2 weight files:
11-action one-hot, the object positions at world creation. v1 weight files with 48 inputs no
longer load):
  interoception 7   hunger, thirst, fatigue, social_drive, curiosity, boredom, stress   (/ 1.5)
  body 6            energy, age / max_age_days, sex, gestating, maternal, wounds (/ 1.5)
  role 7            one-hot of ROLE_PUP .. ROLE_WITHDRAWN
  local 5           own-cell density (alive / design capacity per cell), nest occupancy /
                    capacity, in_playground, food and water stock in the cell (/ FOOD_NORM)
  targets 12        for food, water, own nest, nearest object: capped distance (/ DIST_CAP) and
                    unit direction (dx, dy); a missing target reads (1, 0, 0)
  last action 15    one-hot of the most recent action, free-time sub-steps included (v2: 11,
                    the decision action)
  maternal 1        maternal_need / 1.5 (agents/drives.py; a drive of the learner's reward)
  heading 2         cos, sin of the direction of the agent's last move (v3, v4)
  object motion 2   nearest object: mobile (1 for a ball under ball physics, else 0) and its
                    speed / a full-speed push (capped at 1) (v4, v5)
  place novelty 2   novelty (1 - exp(-dt / tau) since the last visit) of the grid bin one bin
                    width ahead of / behind the animal along its heading; 0 without
                    novelty-based curiosity (v5 only)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from universe25.agents.drives import maternal_need
from universe25.agents.state import N_ACTIONS, N_BASE_ACTIONS

if TYPE_CHECKING:  # pragma: no cover
    from universe25.sim import Universe25Sim
    from universe25.world.geometry import World

N_ROLES = 7
DIST_CAP = 50.0  # inches; the pen is 101 x 101
DRIVE_SCALE = 1.5  # drives are clipped to [0, 1.5]
FOOD_NORM = 10.0  # stock covering ten full meals reads as 1.0 (abundant mode is always 1.0)

_BASE_NAMES: tuple[str, ...] = (
    "hunger", "thirst", "fatigue", "social_drive", "curiosity", "boredom", "stress",
    "energy", "age_frac", "sex", "gestating", "maternal", "wounds",
    "role_pup", "role_juvenile", "role_territorial_m", "role_subordinate_m",
    "role_breeding_f", "role_nursing", "role_withdrawn",
    "cell_density", "nest_occupancy", "in_playground", "food_avail", "water_avail",
    "food_dist", "food_dx", "food_dy", "water_dist", "water_dx", "water_dy",
    "nest_dist", "nest_dx", "nest_dy", "object_dist", "object_dx", "object_dy",
    "last_rest", "last_forage", "last_drink", "last_nest", "last_social", "last_explore",
    "last_manipulate", "last_aggress", "last_mate", "last_nurse", "last_withdraw",
)
OBS_NAMES_V2: tuple[str, ...] = _BASE_NAMES + ("maternal_need",)
OBS_NAMES_V3: tuple[str, ...] = _BASE_NAMES + (
    "last_run_on", "last_turn_back", "last_back_off", "last_circle",
    "maternal_need", "heading_cos", "heading_sin",
)
OBS_NAMES_V4: tuple[str, ...] = OBS_NAMES_V3 + ("object_mobile", "object_speed")
OBS_NAMES: tuple[str, ...] = OBS_NAMES_V4 + ("novelty_ahead", "novelty_behind")
OBS_DIM_V2 = len(OBS_NAMES_V2)
OBS_DIM_V3 = len(OBS_NAMES_V3)
OBS_DIM_V4 = len(OBS_NAMES_V4)
OBS_DIM = len(OBS_NAMES)
assert OBS_DIM_V2 == 7 + 6 + N_ROLES + 5 + 12 + N_BASE_ACTIONS + 1 == 49
assert OBS_DIM_V3 == 7 + 6 + N_ROLES + 5 + 12 + N_ACTIONS + 1 + 2 == 55
assert OBS_DIM_V4 == OBS_DIM_V3 + 2 == 57
assert OBS_DIM == OBS_DIM_V4 + 2 == 59
_DIMS = {2: OBS_DIM_V2, 3: OBS_DIM_V3, 4: OBS_DIM_V4, 5: OBS_DIM}


def _target_block(x: np.ndarray, y: np.ndarray, tx: np.ndarray, ty: np.ndarray,
                  present: np.ndarray) -> np.ndarray:
    """(m, 3): capped distance / DIST_CAP, unit dx, unit dy; (1, 0, 0) where not present."""
    dx = tx - x
    dy = ty - y
    dist = np.hypot(dx, dy)
    safe = np.maximum(dist, 1e-6)
    out = np.empty((x.size, 3), dtype=np.float32)
    out[:, 0] = np.where(present, np.minimum(dist, DIST_CAP) / DIST_CAP, 1.0)
    out[:, 1] = np.where(present, dx / safe, 0.0)
    out[:, 2] = np.where(present, dy / safe, 0.0)
    return out


class ObservationBuilder:
    """Caches the per-world constants; `build` is vectorised over the deciding agents.
    `version` 5 (default), 4, 3 or 2 (the layouts of older weight files, kept exactly)."""

    def __init__(self, world: World, version: int = 5):
        if version not in _DIMS:
            raise ValueError(f"observation version {version}")
        self.version = version
        self.dim = _DIMS[version]
        self.n_act = N_BASE_ACTIONS if version == 2 else N_ACTIONS
        self.ball = np.array([o.kind == "ball" for o in world.play_objects], dtype=bool)
        self.world = world
        self.food_xy = np.array([c.food_xy for c in world.cells], dtype=np.float64)
        self.water_xy = np.array([c.water_xy for c in world.cells], dtype=np.float64)
        self.nest_xy = np.array([(n.x, n.y) for n in world.nests], dtype=np.float64)
        self.nest_cap = np.array([float(n.capacity) for n in world.nests], dtype=np.float64)
        objs = [(o.x, o.y) for o in world.play_objects] if world.playground_enabled else []
        self.obj_xy = np.array(objs, dtype=np.float64).reshape(-1, 2)
        self.cap_cell = max(1.0, world.capacity_design / world.n_cells)
        self._role_eye = np.eye(N_ROLES, dtype=np.float32)
        self._act_eye = np.eye(self.n_act, dtype=np.float32)

    def build(self, sim: Universe25Sim, idx: np.ndarray) -> np.ndarray:
        a = sim.agents
        bio = sim.cfg.biology
        m = int(idx.size)
        obs = np.empty((m, self.dim), dtype=np.float32)
        if m == 0:
            return obs
        # interoception
        obs[:, 0] = a.hunger[idx] / DRIVE_SCALE
        obs[:, 1] = a.thirst[idx] / DRIVE_SCALE
        obs[:, 2] = a.fatigue[idx] / DRIVE_SCALE
        obs[:, 3] = a.social_drive[idx] / DRIVE_SCALE
        obs[:, 4] = a.curiosity[idx] / DRIVE_SCALE
        obs[:, 5] = a.boredom[idx] / DRIVE_SCALE
        obs[:, 6] = a.stress[idx] / DRIVE_SCALE
        # body
        obs[:, 7] = a.energy[idx]
        obs[:, 8] = np.minimum(a.age_days[idx] / float(bio.max_age_days), 2.0)
        obs[:, 9] = a.sex[idx]
        obs[:, 10] = a.gestating[idx] > 0
        obs[:, 11] = a.maternal[idx]
        obs[:, 12] = a.wounds[idx] / DRIVE_SCALE
        # role one-hot
        role = np.clip(a.role[idx].astype(int), 0, N_ROLES - 1)
        obs[:, 13:20] = self._role_eye[role]
        # local
        cell = a.cell_id[idx].astype(int)
        # Own count, never sim._tick_cell_counts(): that cache is filled on first use in a tick
        # and the biology (nursing disturbance, conception density) reads it after the actions
        # have moved agents. Filling it here, before the actions, gave the biology pre-move
        # counts under learned policies only (fixed 2026-11-06; the P4-1 guard was rerun).
        counts = np.bincount(a.cell_id[a.alive].astype(int), minlength=self.world.n_cells)
        obs[:, 20] = counts[cell] / self.cap_cell
        nid = a.nest_id[idx].astype(int)
        housed = a.alive & (a.nest_id >= 0)
        nest_occ = np.bincount(a.nest_id[housed].astype(int), minlength=self.world.n_nests)
        nclip = np.clip(nid, 0, self.world.n_nests - 1)
        obs[:, 21] = np.where(nid >= 0, nest_occ[nclip] / self.nest_cap[nclip], 0.0)
        obs[:, 22] = a.in_playground[idx]
        obs[:, 23] = np.clip(sim.food[cell] / FOOD_NORM, 0.0, 1.0)
        obs[:, 24] = np.clip(sim.water[cell] / FOOD_NORM, 0.0, 1.0)
        # targets
        x = a.x[idx].astype(np.float64)
        y = a.y[idx].astype(np.float64)
        present = np.ones(m, dtype=bool)
        obs[:, 25:28] = _target_block(x, y, self.food_xy[cell, 0], self.food_xy[cell, 1], present)
        obs[:, 28:31] = _target_block(
            x, y, self.water_xy[cell, 0], self.water_xy[cell, 1], present
        )
        obs[:, 31:34] = _target_block(
            x, y, self.nest_xy[nclip, 0], self.nest_xy[nclip, 1], nid >= 0
        )
        obj_xy = self.obj_xy
        if self.version >= 3 and obj_xy.shape[0] > 0:  # v3, v4: where the objects are now
            obj_xy = np.array([(o.x, o.y) for o in self.world.play_objects], dtype=np.float64)
        j = None
        if obj_xy.shape[0] > 0:
            d2 = (x[:, None] - obj_xy[None, :, 0]) ** 2 + (
                y[:, None] - obj_xy[None, :, 1]
            ) ** 2
            j = np.argmin(d2, axis=1)
            obs[:, 34:37] = _target_block(x, y, obj_xy[j, 0], obj_xy[j, 1], present)
        else:
            obs[:, 34:37] = _target_block(x, y, x, y, np.zeros(m, dtype=bool))
        # last action one-hot
        n = self.n_act
        # v3+: the most recent action, free-time sub-steps included (fixed 2026-11-09: v4 and v5
        # read the decision action until then); v2: the decision action
        last = a.recent_action if self.version >= 3 else a.last_action
        act = np.clip(last[idx].astype(int), 0, n - 1)
        obs[:, 37:37 + n] = self._act_eye[act]
        obs[:, 37 + n] = np.clip(maternal_need(a, idx) / DRIVE_SCALE, 0.0, 1.0)
        if self.version >= 3:
            h = a.heading[idx].astype(np.float64)
            obs[:, 38 + n] = np.cos(h)
            obs[:, 39 + n] = np.sin(h)
        if self.version >= 4:
            mob = np.zeros(m, dtype=np.float32)
            spd = np.zeros(m, dtype=np.float32)
            if j is not None and getattr(sim, "ball_physics", False):
                objs = self.world.play_objects
                v = np.array([np.hypot(o.vx, o.vy) for o in objs], dtype=np.float64)
                mob = self.ball[j].astype(np.float32)
                spd = np.where(self.ball[j], np.minimum(v[j] / sim.ball_v_ref, 1.0), 0.0)
            obs[:, 40 + n] = mob
            obs[:, 41 + n] = spd
        if self.version == 5:
            ahead = np.zeros(m, dtype=np.float32)
            behind = np.zeros(m, dtype=np.float32)
            if getattr(sim, "novelty", False):
                h = a.heading[idx].astype(np.float64)
                step = self.world.width / sim.nov_G
                W, H = self.world.width, self.world.height
                for sign, out in ((1.0, ahead), (-1.0, behind)):
                    px = np.clip(x + sign * step * np.cos(h), 0.5, W - 0.5)
                    py = np.clip(y + sign * step * np.sin(h), 0.5, H - 0.5)
                    out[:] = sim.place_novelty(idx, sim.nov_bin(px, py), sim._nov_t)
            obs[:, 42 + n] = ahead
            obs[:, 43 + n] = behind
        return obs
