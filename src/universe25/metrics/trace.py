"""Per-agent decision traces for the offline detectors (phase 4, eval-only).

Off by default (`trace.windows: []`): no recorder is built and the tick is bit-identical. When
on, the recorder never draws from an RNG, never writes simulation state and never touches the
simulation's per-tick cell-count cache (whose first use in a tick fixes the counts the biology
reads); it keeps its own counts. It runs on decision ticks only.

Every decision tick it tracks identities (a slot whose agent died and was reborn gets a new
`uid`) and each individual's cumulative object contacts since birth (or since recording began).
Inside a window [start, end) it also appends one row per alive agent: the state the agent
decided from (pre-action drives), the action, and the outcome (post-action position, survival
drives, nearest object, distances to its hoppers and nest). Each window is written to
`trace_<start>_<end>.npz` in the run directory when it closes.

Nothing here is read by a policy or learner (tests/test_detectors.py import audit).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from universe25.agents.state import ACT_MANIPULATE

if TYPE_CHECKING:  # pragma: no cover
    from universe25.sim import Universe25Sim

CONTACT_SLACK = 1.0  # inches beyond the object radius that count as contact

PRE_FIELDS = ("uid", "step", "tick", "day", "slot", "action", "age", "sex", "role", "hunger",
              "thirst", "fatigue", "stress", "curiosity", "boredom", "social_drive", "energy",
              "wounds", "cell", "cell_density")
POST_FIELDS = ("x", "y", "hunger_post", "thirst_post", "fatigue_post", "stress_post", "obj_id",
               "obj_dist", "contact", "in_playground", "food_dist", "water_dist", "nest_dist",
               "cum_contacts")
FIELDS = PRE_FIELDS + POST_FIELDS


def nearest_object(x: np.ndarray, y: np.ndarray, ox: np.ndarray, oy: np.ndarray,
                   orad: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Index, distance and radius of the nearest object per point (-1 / inf / 0 if none)."""
    if ox.size == 0:
        n = x.size
        return np.full(n, -1, np.int32), np.full(n, np.inf), np.zeros(n)
    d2 = (x[:, None] - ox[None, :]) ** 2 + (y[:, None] - oy[None, :]) ** 2
    j = np.argmin(d2, axis=1)
    return j.astype(np.int32), np.sqrt(d2[np.arange(x.size), j]), orad[j]


class TraceRecorder:
    def __init__(self, sim: Universe25Sim, windows: list[tuple[float, float]]):
        self.windows = sorted((float(a), float(b)) for a, b in windows)
        cap = sim.agents.capacity
        self.slot_uid = np.full(cap, -1, np.int64)
        self.prev_age = np.full(cap, np.inf)
        self.cum_contacts = np.zeros(cap, np.int32)
        self.next_uid = 0
        self.out_dir = Path(sim.out_dir)
        self.files: list[str] = []
        w = sim.world
        self.food_xy = np.array([c.food_xy for c in w.cells], dtype=np.float64)
        self.water_xy = np.array([c.water_xy for c in w.cells], dtype=np.float64)
        self.nest_xy = np.array([(n.x, n.y) for n in w.nests], dtype=np.float64)
        self.cap_cell = max(1.0, w.capacity_design / w.n_cells)
        self.n_cells = w.n_cells
        self.meta: dict[str, Any] = {
            "seed": int(sim.cfg.seed),
            "ticks_per_day": int(sim.cfg.ticks_per_day),
            "ticks_per_decision": int(sim.ticks_per_decision),
            "decisions_per_day": int(sim.cfg.ticks_per_day // sim.ticks_per_decision),
            "playground_enabled": bool(w.playground_enabled),
            "playground_bounds": np.array(w.playground_bounds, dtype=np.float64),
            "policy_kind": str(sim.cfg.policy.kind),
        }
        self._buf: dict[str, list[np.ndarray]] = {k: [] for k in FIELDS}
        self._win: int | None = None
        self._pending: tuple[np.ndarray, dict[str, np.ndarray] | None] | None = None

    def _window_index(self, day: float) -> int | None:
        for i, (a, b) in enumerate(self.windows):
            if a <= day < b:
                return i
        return None

    def capture_pre(self, sim: Universe25Sim, alive: np.ndarray, actions: np.ndarray) -> None:
        a = sim.agents
        idx = np.flatnonzero(alive)
        self.slot_uid[~alive] = -1
        age = a.age_days[idx].astype(np.float64)
        new = (self.slot_uid[idx] < 0) | (age < self.prev_age[idx] - 1e-9)
        if new.any():
            n_new = int(new.sum())
            self.slot_uid[idx[new]] = np.arange(self.next_uid, self.next_uid + n_new)
            self.next_uid += n_new
            self.cum_contacts[idx[new]] = 0
        self.prev_age[idx] = age
        self.prev_age[~alive] = np.inf
        w = self._window_index(sim.day)
        if self._win is not None and w != self._win:
            self._flush()
        self._win = w
        if w is None:
            self._pending = (idx, None)
            return
        cell = a.cell_id[idx].astype(int)
        counts = np.bincount(a.cell_id[alive].astype(int), minlength=self.n_cells)
        rec = {
            "uid": self.slot_uid[idx].copy(),
            "step": np.full(idx.size, sim.tick // sim.ticks_per_decision, np.int64),
            "tick": np.full(idx.size, sim.tick, np.int64),
            "day": np.full(idx.size, sim.day, np.float64),
            "slot": idx.astype(np.int32),
            "action": actions[idx].astype(np.int16),
            "age": a.age_days[idx].astype(np.float32),
            "sex": a.sex[idx].astype(np.int8),
            "role": a.role[idx].astype(np.int8),
            "hunger": a.hunger[idx].astype(np.float32),
            "thirst": a.thirst[idx].astype(np.float32),
            "fatigue": a.fatigue[idx].astype(np.float32),
            "stress": a.stress[idx].astype(np.float32),
            "curiosity": a.curiosity[idx].astype(np.float32),
            "boredom": a.boredom[idx].astype(np.float32),
            "social_drive": a.social_drive[idx].astype(np.float32),
            "energy": a.energy[idx].astype(np.float32),
            "wounds": a.wounds[idx].astype(np.float32),
            "cell": cell.astype(np.int16),
            "cell_density": (counts[cell] / self.cap_cell).astype(np.float32),
        }
        self._pending = (idx, rec)

    def record_post(self, sim: Universe25Sim) -> None:
        if self._pending is None:
            return
        idx, rec = self._pending
        self._pending = None
        a = sim.agents
        objs = sim.world.play_objects if sim.world.playground_enabled else []
        ox = np.array([o.x for o in objs], dtype=np.float64)
        oy = np.array([o.y for o in objs], dtype=np.float64)
        orad = np.array([o.radius for o in objs], dtype=np.float64)
        x = a.x[idx].astype(np.float64)
        y = a.y[idx].astype(np.float64)
        oid, odist, orr = nearest_object(x, y, ox, oy, orad)
        contact = (a.last_action[idx] == ACT_MANIPULATE) & (odist <= orr + CONTACT_SLACK)
        self.cum_contacts[idx] += contact.astype(np.int32)
        if rec is None:
            return
        cell = rec["cell"].astype(int)
        cell_now = a.cell_id[idx].astype(int)  # hoppers of the cell the agent ended in
        nid = a.nest_id[idx].astype(int)
        nclip = np.clip(nid, 0, len(self.nest_xy) - 1)
        nest_d = np.hypot(x - self.nest_xy[nclip, 0], y - self.nest_xy[nclip, 1])
        rec.update({
            "x": x.astype(np.float32),
            "y": y.astype(np.float32),
            "hunger_post": a.hunger[idx].astype(np.float32),
            "thirst_post": a.thirst[idx].astype(np.float32),
            "fatigue_post": a.fatigue[idx].astype(np.float32),
            "stress_post": a.stress[idx].astype(np.float32),
            "obj_id": oid,
            "obj_dist": np.where(np.isfinite(odist), odist, 1e3).astype(np.float32),
            "contact": contact.astype(np.int8),
            "in_playground": a.in_playground[idx].astype(np.int8),
            "food_dist": np.hypot(x - self.food_xy[cell_now, 0],
                                  y - self.food_xy[cell_now, 1]).astype(np.float32),
            "water_dist": np.hypot(x - self.water_xy[cell_now, 0],
                                   y - self.water_xy[cell_now, 1]).astype(np.float32),
            "nest_dist": np.where(nid >= 0, nest_d, 1e3).astype(np.float32),
            "cum_contacts": self.cum_contacts[idx].copy(),
        })
        del cell
        for k in FIELDS:
            self._buf[k].append(rec[k])

    def _flush(self) -> None:
        if self._win is None or not self._buf["uid"]:
            for k in FIELDS:
                self._buf[k].clear()
            return
        start, end = self.windows[self._win]
        arrays = {k: np.concatenate(self._buf[k]) for k in FIELDS}
        meta = {f"meta_{k}": np.asarray(v) for k, v in self.meta.items()}
        path = self.out_dir / f"trace_{start:g}_{end:g}.npz"
        np.savez_compressed(path, **arrays, **meta, meta_window=np.array([start, end]))
        self.files.append(str(path))
        for k in FIELDS:
            self._buf[k].clear()

    def close(self) -> list[str]:
        self._flush()
        self._win = None
        return self.files


def load_trace(path: str | Path) -> dict[str, Any]:
    """Arrays by field name plus `meta` (dict) from a trace_*.npz."""
    with np.load(path, allow_pickle=False) as z:
        out: dict[str, Any] = {k: z[k] for k in z.files if not k.startswith("meta_")}
        meta = {k[5:]: z[k] for k in z.files if k.startswith("meta_")}
    out["meta"] = {k: (v.item() if v.ndim == 0 else v) for k, v in meta.items()}
    return out
