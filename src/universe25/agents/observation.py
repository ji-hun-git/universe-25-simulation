"""Observation vector for learned policies (phase 4; docs/PHASE4_DESIGN.md section 1.3).

Egocentric, float32, built from the SoA state and the world geometry only. It contains no
PlayScore field, no play-named feature (the playground box is geometry, like a cell id), and
not the agent's own `lifespan` (hidden information). Pure NumPy, no RNG, so the reference path
stays deterministic and the builder can be timed and audited on its own.

Blocks (48 floats):
  interoception 7   hunger, thirst, fatigue, social_drive, curiosity, boredom, stress   (/ 1.5)
  body 6            energy, age / max_age_days, sex, gestating, maternal, wounds (/ 1.5)
  role 7            one-hot of ROLE_PUP .. ROLE_WITHDRAWN
  local 5           own-cell density (alive / design capacity per cell), nest occupancy /
                    capacity, in_playground, food and water stock in the cell (/ FOOD_NORM)
  targets 12        for food, water, own nest, nearest object: capped distance (/ DIST_CAP) and
                    unit direction (dx, dy); a missing target reads (1, 0, 0)
  last action 11    one-hot of the previous action
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from universe25.agents.state import N_ACTIONS

if TYPE_CHECKING:  # pragma: no cover
    from universe25.sim import Universe25Sim
    from universe25.world.geometry import World

N_ROLES = 7
DIST_CAP = 50.0  # inches; the pen is 101 x 101
DRIVE_SCALE = 1.5  # drives are clipped to [0, 1.5]
FOOD_NORM = 10.0  # stock covering ten full meals reads as 1.0 (abundant mode is always 1.0)

OBS_NAMES: tuple[str, ...] = (
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
OBS_DIM = len(OBS_NAMES)
assert OBS_DIM == 7 + 6 + N_ROLES + 5 + 12 + N_ACTIONS == 48


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
    """Caches the per-world constants; `build` is vectorised over the deciding agents."""

    def __init__(self, world: World):
        self.world = world
        self.food_xy = np.array([c.food_xy for c in world.cells], dtype=np.float64)
        self.water_xy = np.array([c.water_xy for c in world.cells], dtype=np.float64)
        self.nest_xy = np.array([(n.x, n.y) for n in world.nests], dtype=np.float64)
        self.nest_cap = np.array([float(n.capacity) for n in world.nests], dtype=np.float64)
        objs = [(o.x, o.y) for o in world.play_objects] if world.playground_enabled else []
        self.obj_xy = np.array(objs, dtype=np.float64).reshape(-1, 2)
        self.cap_cell = max(1.0, world.capacity_design / world.n_cells)
        self._role_eye = np.eye(N_ROLES, dtype=np.float32)
        self._act_eye = np.eye(N_ACTIONS, dtype=np.float32)

    def build(self, sim: Universe25Sim, idx: np.ndarray) -> np.ndarray:
        a = sim.agents
        bio = sim.cfg.biology
        m = int(idx.size)
        obs = np.empty((m, OBS_DIM), dtype=np.float32)
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
        if self.obj_xy.shape[0] > 0:
            d2 = (x[:, None] - self.obj_xy[None, :, 0]) ** 2 + (
                y[:, None] - self.obj_xy[None, :, 1]
            ) ** 2
            j = np.argmin(d2, axis=1)
            obs[:, 34:37] = _target_block(x, y, self.obj_xy[j, 0], self.obj_xy[j, 1], present)
        else:
            obs[:, 34:37] = _target_block(x, y, x, y, np.zeros(m, dtype=bool))
        # last action one-hot
        act = np.clip(a.last_action[idx].astype(int), 0, N_ACTIONS - 1)
        obs[:, 37:48] = self._act_eye[act]
        return obs
