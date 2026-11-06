"""Per-agent decision traces for the offline detectors (phase 4, eval-only).

Off by default (`trace.windows: []`): no recorder is built and the tick is bit-identical. When
on, the recorder never draws from an RNG, never writes simulation state and never touches the
simulation's per-tick cell-count cache (whose first use in a tick fixes the counts the biology
reads); it keeps its own counts. It runs on decision ticks only.

Every decision tick it tracks identities (a slot whose agent died and was reborn gets a new
`uid`) and each individual's cumulative object contacts since birth (or since recording began).
Inside a window [start, end) it appends rows on a uniform time base of `free_substeps` (K) rows
per decision and agent: an agent whose decision action is free (EXPLORE / SOCIAL / MANIPULATE)
contributes its K sub-step rows (written by the simulation's sub-step loop through `micro`);
every other agent contributes K rows interpolated along its decision move, with the decision's
survival-drive change on the last row. With K = 1 this is one row per decision, as before.
`step` counts rows (decision index x K + sub-step); `meta.decisions_per_day` is rows per day.
Each window is written to `trace_<start>_<end>.npz` when it closes; `sample_every` keeps only
individuals whose uid is a multiple of it.

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
SURV = ("hunger", "thirst", "fatigue", "stress")


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
    def __init__(self, sim: Universe25Sim, windows: list[tuple[float, float]],
                 sample_every: int = 1):
        self.windows = sorted((float(a), float(b)) for a, b in windows)
        self.sample_every = max(1, int(sample_every))
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
        self.nx, self.ny = int(sim.cfg.geometry.n_cells_x), int(sim.cfg.geometry.n_cells_y)
        self.cw, self.ch = w.width / self.nx, w.height / self.ny
        self.pg_bounds = tuple(float(v) for v in w.playground_bounds)
        self.pg_on = bool(w.playground_enabled)
        self.K = max(1, int(getattr(sim, "free_substeps", 1)))
        dec_per_day = int(sim.cfg.ticks_per_day // sim.ticks_per_decision)
        self.meta: dict[str, Any] = {
            "seed": int(sim.cfg.seed),
            "ticks_per_day": int(sim.cfg.ticks_per_day),
            "ticks_per_decision": int(sim.ticks_per_decision),
            "free_substeps": self.K,
            "decisions_per_day": dec_per_day * self.K,  # rows per day (the detectors' unit)
            "sample_every": self.sample_every,
            "playground_enabled": self.pg_on,
            "playground_bounds": np.array(w.playground_bounds, dtype=np.float64),
            "policy_kind": str(sim.cfg.policy.kind),
        }
        self._buf: dict[str, list[np.ndarray]] = {k: [] for k in FIELDS}
        self._win: int | None = None
        self._cur: dict[str, Any] | None = None  # this decision: idx, pre state, free set

    # ------------------------------------------------------------------ helpers
    def _window_index(self, day: float) -> int | None:
        for i, (a, b) in enumerate(self.windows):
            if a <= day < b:
                return i
        return None

    def _objects(self, sim: Universe25Sim) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        objs = sim.world.play_objects if self.pg_on else []
        return (np.array([o.x for o in objs], dtype=np.float64),
                np.array([o.y for o in objs], dtype=np.float64),
                np.array([o.radius for o in objs], dtype=np.float64))

    def _cell_of(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        ix = np.clip((x / self.cw).astype(int), 0, self.nx - 1)
        iy = np.clip((y / self.ch).astype(int), 0, self.ny - 1)
        return iy * self.nx + ix

    def _in_pg(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        if not self.pg_on:
            return np.zeros(x.size, dtype=np.int8)
        x0, y0, x1, y1 = self.pg_bounds
        return ((x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)).astype(np.int8)

    def _append(self, rows: dict[str, np.ndarray]) -> None:
        keep = (rows["uid"] % self.sample_every) == 0
        if not keep.any():
            return
        for k in FIELDS:
            self._buf[k].append(np.asarray(rows[k])[keep])

    def _place(self, rows: dict[str, Any], sim: Universe25Sim, x: np.ndarray, y: np.ndarray,
               nest_id: np.ndarray, contact: np.ndarray, oid: np.ndarray,
               odist: np.ndarray) -> None:
        """Position-derived post fields for rows at (x, y)."""
        cell_now = self._cell_of(x, y)
        nclip = np.clip(nest_id, 0, len(self.nest_xy) - 1)
        nest_d = np.hypot(x - self.nest_xy[nclip, 0], y - self.nest_xy[nclip, 1])
        rows["x"] = x.astype(np.float32)
        rows["y"] = y.astype(np.float32)
        rows["obj_id"] = oid
        rows["obj_dist"] = np.where(np.isfinite(odist), odist, 1e3).astype(np.float32)
        rows["contact"] = contact.astype(np.int8)
        rows["in_playground"] = self._in_pg(x, y)
        rows["food_dist"] = np.hypot(x - self.food_xy[cell_now, 0],
                                     y - self.food_xy[cell_now, 1]).astype(np.float32)
        rows["water_dist"] = np.hypot(x - self.water_xy[cell_now, 0],
                                      y - self.water_xy[cell_now, 1]).astype(np.float32)
        rows["nest_dist"] = np.where(nest_id >= 0, nest_d, 1e3).astype(np.float32)

    # ------------------------------------------------------------------ hooks
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
        cell = a.cell_id[idx].astype(int)
        counts = np.bincount(a.cell_id[alive].astype(int), minlength=self.n_cells)
        self._cur = {
            "idx": idx, "in_window": w is not None, "free": np.zeros(0, dtype=np.int64),
            "step0": (sim.tick // sim.ticks_per_decision) * self.K, "tick": sim.tick,
            "day": sim.day, "action": actions[idx].astype(np.int16),
            "x": a.x[idx].astype(np.float64), "y": a.y[idx].astype(np.float64),
            "cell": cell, "cell_density": (counts[cell] / self.cap_cell).astype(np.float32),
        }
        for k in ("age", "hunger", "thirst", "fatigue", "stress", "curiosity", "boredom",
                  "social_drive", "energy", "wounds"):
            self._cur[k] = getattr(a, "age_days" if k == "age" else k)[idx].astype(np.float32)
        self._cur["sex"] = a.sex[idx].astype(np.int8)
        self._cur["role"] = a.role[idx].astype(np.int8)

    def micro(self, sim: Universe25Sim, free: np.ndarray, j: int, act: np.ndarray,
              pre: dict[str, np.ndarray]) -> None:
        """Sub-step j of the agents `free` (slots), after the move: `act` is the sub-step
        action, `pre` the curiosity / boredom / social_drive / x / y / cell before it."""
        cur = self._cur
        if cur is None:
            return
        a = sim.agents
        if j == 0:
            cur["free"] = free
        x = a.x[free].astype(np.float64)
        y = a.y[free].astype(np.float64)
        ox, oy, orad = self._objects(sim)
        oid, odist, orr = nearest_object(x, y, ox, oy, orad)
        contact = (act == ACT_MANIPULATE) & (odist <= orr + CONTACT_SLACK)
        self.cum_contacts[free] += contact.astype(np.int32)
        if not cur["in_window"]:
            return
        pos = np.searchsorted(cur["idx"], free)  # rows of `free` in the decision arrays
        rows: dict[str, Any] = {
            "uid": self.slot_uid[free].copy(),
            "step": np.full(free.size, cur["step0"] + j, np.int64),
            "tick": np.full(free.size, cur["tick"], np.int64),
            "day": np.full(free.size, cur["day"], np.float64),
            "slot": free.astype(np.int32), "action": act.astype(np.int16),
            "cell": pre["cell"].astype(np.int16), "cell_density": cur["cell_density"][pos],
            "curiosity": pre["curiosity"].astype(np.float32),
            "boredom": pre["boredom"].astype(np.float32),
            "social_drive": pre["social_drive"].astype(np.float32),
            "cum_contacts": self.cum_contacts[free].copy(),
        }
        for k in ("age", "sex", "role", "energy", "wounds"):
            rows[k] = cur[k][pos]
        for k in SURV:  # first sub-step carries the decision's change; later ones none
            now = getattr(a, k)[free].astype(np.float32)
            rows[k] = cur[k][pos] if j == 0 else now
            rows[f"{k}_post"] = now
        self._place(rows, sim, x, y, a.nest_id[free].astype(int), contact, oid, odist)
        self._append(rows)

    def record_post(self, sim: Universe25Sim) -> None:
        cur = self._cur
        self._cur = None
        if cur is None:
            return
        a = sim.agents
        idx = cur["idx"]
        rest = ~np.isin(idx, cur["free"]) if cur["free"].size else np.ones(idx.size, bool)
        ii = idx[rest]
        if ii.size == 0:
            return
        ox, oy, orad = self._objects(sim)
        x1 = a.x[ii].astype(np.float64)
        y1 = a.y[ii].astype(np.float64)
        if self.K == 1:  # contacts for decision-level manipulation (no sub-steps)
            _, d1, r1 = nearest_object(x1, y1, ox, oy, orad)
            c1 = (a.last_action[ii] == ACT_MANIPULATE) & (d1 <= r1 + CONTACT_SLACK)
            self.cum_contacts[ii] += c1.astype(np.int32)
        if not cur["in_window"]:
            return
        K = self.K
        x0, y0 = cur["x"][rest], cur["y"][rest]
        n = ii.size
        jj = np.tile(np.arange(K), n)
        rep = np.repeat(np.arange(n), K)
        frac = (jj + 1.0) / K
        x = x0[rep] + (x1 - x0)[rep] * frac
        y = y0[rep] + (y1 - y0)[rep] * frac
        prev_x = x0[rep] + (x1 - x0)[rep] * (jj / K)
        prev_y = y0[rep] + (y1 - y0)[rep] * (jj / K)
        oid, odist, orr = nearest_object(x, y, ox, oy, orad)
        act = cur["action"][rest][rep]
        contact = (act == ACT_MANIPULATE) & (odist <= orr + CONTACT_SLACK) & (jj == K - 1)
        last = jj == K - 1
        rows: dict[str, Any] = {
            "uid": self.slot_uid[ii][rep],
            "step": cur["step0"] + jj.astype(np.int64),
            "tick": np.full(n * K, cur["tick"], np.int64),
            "day": np.full(n * K, cur["day"], np.float64),
            "slot": ii[rep].astype(np.int32), "action": act,
            "cell": np.where(jj == 0, cur["cell"][rest][rep],
                             self._cell_of(prev_x, prev_y)).astype(np.int16),
            "cell_density": cur["cell_density"][rest][rep],
            "cum_contacts": self.cum_contacts[ii][rep],
        }
        for k in ("age", "sex", "role", "curiosity", "boredom", "social_drive", "energy",
                  "wounds"):
            rows[k] = cur[k][rest][rep]
        for k in SURV:
            pre_k = cur[k][rest][rep]
            rows[k] = pre_k
            rows[f"{k}_post"] = np.where(last, getattr(a, k)[ii].astype(np.float32)[rep], pre_k)
        self._place(rows, sim, x, y, a.nest_id[ii].astype(int)[rep], contact, oid, odist)
        self._append(rows)

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
