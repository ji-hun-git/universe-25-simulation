"""Frames for the viewer (`viewer/`, TASKS P2-1 / P2-2): the pen as drawn, and each captured
moment of a run as compact arrays. Used by `scripts/viewer_record.py` (files) and
`scripts/viewer_serve.py` (live runs).

Read-only on the simulator: nothing here draws a random number or writes simulator state, so a
recorded or live run is the run `main.py` makes from the same config and seed
(`tests/test_viewer.py` checks that the NumPy path stays bit-identical with capture on).

A frame is a JSON header and a payload. The payload holds the n animals alive in slot order,
little-endian, array after array:
  uint16 slot, x and y (1/100 in), age (whole days); int16 nest (-1 none);
  uint8 role, flags (1 male, 2 in the playground, 4 gestating), stress and wounds (0-1.5 to
  0-255), energy (0-1 to 0-255), action (the last decision), cell (255 none), and (format 2)
  heading, the direction of the animal's last move (`AgentSoA.heading`, 0-2 pi to 0-255);
  format 3 adds the body (agents/body.py): uint16 mass (1/100 g); uint8 condition (x 100),
  coat genotype (six allele bits) and pregnancy (0 none, else 1 + 254 x gestation progress);
then zero bytes to a multiple of 4. The header carries the time, the colony counters, colony
summaries (by role and by cell, means, and V and G as `Universe25Sim._log_metrics` defines
them) and the object positions (balls roll under the P4-13 physics; without it a MANIPULATE
decision nudges its object).

A blob (a recording file or one live response) is a uint32 header length, the header JSON,
zero bytes to a multiple of 4, then the payloads; each frame's header has `off` and `len` into
the payload region."""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

# the repo, or the folder the app keeps the viewer and configs in (universe25.app sets U25_ROOT)
ROOT = Path(os.environ.get("U25_ROOT") or Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.body import COATS  # noqa: E402
from universe25.agents.state import SEX_M  # noqa: E402
from universe25.metrics.calibration import (  # noqa: E402
    EXTRA_LANDMARKS,
    LANDMARKS,
    RECORD_LANDMARKS,
)
from universe25.world.geometry import _wall_point  # noqa: E402

FORMAT = 3  # 2: a heading byte after the cell; 3: the body (mass, condition, coat, pregnancy)
FIELDS = (("slot", "<u2"), ("x", "<u2"), ("y", "<u2"), ("age", "<u2"), ("nest", "<i2"),
          ("role", "<u1"), ("flags", "<u1"), ("stress", "<u1"), ("wounds", "<u1"),
          ("energy", "<u1"), ("action", "<u1"), ("cell", "<u1"), ("heading", "<u1"),
          ("mass", "<u2"), ("cond", "<u1"), ("coat", "<u1"), ("gest", "<u1"))
N_FIELDS = {1: 12, 2: 13, 3: 17}  # fields per format
ROLE_NAMES = ("pup", "juvenile", "territorial male", "subordinate male", "breeding female",
              "nursing", "withdrawn")
ACTION_NAMES = ("rest", "forage", "drink", "nest", "social", "explore", "manipulate",
                "aggress", "mate", "nurse", "withdraw", "run on", "turn back", "back off",
                "circle")
CLIP_MAX = 1.5  # stress and wounds are clipped to [0, 1.5] in sim.py
# Calhoun 1973's phases on the record's days: A to the first litters, B to day 315, C to the
# peak, D after it (metrics/calibration.py: phase B doubling "first litters -> day 315",
# phase C "day 315 -> peak_day").
PHASES = (("A", 0.0, LANDMARKS["first_litters_day"]),
          ("B", LANDMARKS["first_litters_day"], 315.0),
          ("C", 315.0, LANDMARKS["peak_day"]),
          ("D", LANDMARKS["peak_day"], None))


def landmarks() -> dict[str, Any]:
    """Calhoun's census points and event days, as the calibration module holds them."""
    census = [[315.0, LANDMARKS["n_at_day_315"]], [LANDMARKS["peak_day"], LANDMARKS["peak_n"]]]
    for table in (EXTRA_LANDMARKS, RECORD_LANDMARKS):
        for key, val in table.items():
            m = re.fullmatch(r"n_at_day_(\d+)", key)
            if m:
                census.append([float(m.group(1)), float(val)])
    census.sort()
    events = [["first litters", LANDMARKS["first_litters_day"]],
              ["last surviving birth", LANDMARKS["last_young_day"]],
              ["last conception", EXTRA_LANDMARKS["last_conception_day"]]]
    return {"census": census, "events": events,
            "phases": [{"name": n, "from": a, "to": b} for n, a, b in PHASES],
            "source": "Calhoun 1973, Marsden 1972 (src/universe25/metrics/calibration.py)"}


def cell_polygons(world) -> list[list[list[float]]]:
    """Grid: the 4 x 4 squares. Calhoun layout: each triangle, wall segment to the centre."""
    W, H = float(world.width), float(world.height)
    if world.layout != "calhoun":
        return [[[c.x0, c.y0], [c.x1, c.y0], [c.x1, c.y1], [c.x0, c.y1]] for c in world.cells]
    L = W / 4.0
    polys = []
    for c in world.cells:
        wall, k = divmod(c.id, 4)
        p0, p1 = _wall_point(wall, k * L, W, H), _wall_point(wall, (k + 1) * L, W, H)
        polys.append([[p0[0], p0[1]], [p1[0], p1[1]], [W / 2.0, H / 2.0]])
    return polys


def world_meta(sim) -> dict[str, Any]:
    """The pen, the objects at the start, the run's settings and Calhoun's landmarks."""
    w, cfg = sim.world, sim.cfg
    polys = cell_polygons(w)
    return {
        "format": FORMAT,
        "width": float(w.width),
        "height": float(w.height),
        "layout": w.layout,
        "cells": [{"id": c.id, "poly": p, "food": list(c.food_xy), "water": list(c.water_xy)}
                  for c, p in zip(w.cells, polys)],
        "nests": [{"x": n.x, "y": n.y, "cell": n.cell_id, "level": n.level, "cap": n.capacity}
                  for n in w.nests],
        "rings": [list(r) for r in w.ring_xy],
        "withdraw_xy": list(w.withdraw_xy),
        "playground": {"enabled": bool(w.playground_enabled),
                       "bounds": list(w.playground_bounds)},
        "objects": [{"id": o.id, "kind": o.kind, "x": o.x, "y": o.y, "r": o.radius}
                    for o in w.play_objects],
        "capacity_design": int(w.capacity_design),
        "cell_capacity": float(w.capacity_design) / float(len(w.cells)),
        "roles": list(ROLE_NAMES),
        "actions": list(ACTION_NAMES),
        "coats": list(COATS),
        "body": {"coat_founders": str(cfg.coat.founders),
                 "weight_effects": bool(cfg.body.weight_effects),
                 "gestation_days": float(cfg.biology.gestation_days)},
        "run": {"seed": int(cfg.seed), "days": float(cfg.days),
                "ticks_per_day": int(cfg.ticks_per_day), "free_substeps": int(sim.free_substeps),
                "ball_physics": bool(sim.ball_physics), "backend": str(sim.backend),
                "device": str(sim.device), "arm_label": str(cfg.arm_label),
                "max_agents": int(cfg.max_agents), "policy": str(cfg.policy.kind),
                "resources": str(cfg.resources.mode)},
        "landmarks": landmarks(),
    }


def _q8(v: np.ndarray, hi: float) -> np.ndarray:
    return np.rint(np.clip(v, 0.0, hi) * (255.0 / hi)).astype("<u1")


def cfg_gest(sim) -> float:
    return float(sim.cfg.biology.gestation_days)


def _gest8(left: np.ndarray, days: float) -> np.ndarray:
    """Pregnancy: 0 none, else 1 + 254 x the share of gestation done."""
    done = np.clip(1.0 - left.astype(np.float64) / max(1e-9, days), 0.0, 1.0)
    return np.where(left > 0, 1 + np.rint(done * 254.0), 0).astype("<u1")


def _heading8(h: np.ndarray) -> np.ndarray:
    """Radians to 256 steps of the full turn (0 = +x, counter-clockwise, y up)."""
    turn = np.mod(h.astype(np.float64), 2.0 * np.pi) / (2.0 * np.pi)
    return (np.rint(turn * 256.0).astype(np.int64) % 256).astype("<u1")


def capture(sim, t: float | None = None, sub: int = 0) -> tuple[dict[str, Any], bytes]:
    """The colony now: header and payload (module docstring). `t` defaults to `sim.day`;
    `sub` > 0 marks a free-time sub-step frame inside a tick."""
    a, w = sim.agents, sim.world
    idx = np.flatnonzero(a.alive)
    n = int(idx.size)
    W, H = float(w.width), float(w.height)
    sex_m = a.sex[idx] == SEX_M
    in_pg = a.in_playground[idx].astype(bool)
    cell = a.cell_id[idx]
    flags = (sex_m.astype(np.uint8) | (in_pg.astype(np.uint8) << 1)
             | ((a.gestating[idx] > 0).astype(np.uint8) << 2))
    parts = [
        idx.astype("<u2"),
        np.rint(np.clip(a.x[idx], 0.0, W) * 100.0).astype("<u2"),
        np.rint(np.clip(a.y[idx], 0.0, H) * 100.0).astype("<u2"),
        np.minimum(np.floor(np.maximum(a.age_days[idx], 0.0)), 65535).astype("<u2"),
        a.nest_id[idx].astype("<i2"),
        a.role[idx].astype("<u1"),
        flags.astype("<u1"),
        _q8(a.stress[idx], CLIP_MAX),
        _q8(a.wounds[idx], CLIP_MAX),
        _q8(a.energy[idx], 1.0),
        a.last_action[idx].astype("<u1"),
        np.where(cell < 0, 255, cell).astype("<u1"),
        _heading8(a.heading[idx]),
        np.rint(np.clip(sim.body.mass[idx], 0.0, 655.0) * 100.0).astype("<u2"),
        np.rint(np.clip(sim.body.cond[idx], 0.0, 2.55) * 100.0).astype("<u1"),
        sim.body.coat[idx].astype("<u1"),
        _gest8(a.gestating[idx], float(cfg_gest(sim))),
    ]
    payload = b"".join(p.tobytes() for p in parts)
    payload += b"\0" * ((-len(payload)) % 4)

    n_cells = len(w.cells)
    stress, energy = a.stress[idx], a.energy[idx]
    eligible = (energy > 0.5) & (stress < 0.4)  # as _log_metrics: V and G (unvalidated)
    ne = int(eligible.sum())
    nests = a.nest_id[idx]
    meta = {
        "t": round(float(sim.day if t is None else t), 6),
        "k": int(sim.tick),
        "s": int(sub),
        "n": n,
        "b": int(sim._births),
        "d": int(sim._deaths),
        "c": int(sim._conceptions),
        "roles": np.bincount(a.role[idx].astype(np.int64), minlength=8)[:7].tolist(),
        "cells": np.bincount(cell[cell >= 0].astype(np.int64),
                             minlength=n_cells)[:n_cells].tolist(),
        "pg": int(in_pg.sum()),
        "ms": round(float(stress.mean()), 4) if n else 0.0,
        "mw": round(float(a.wounds[idx].mean()), 4) if n else 0.0,
        "me": round(float(energy.mean()), 4) if n else 0.0,
        "V": round(float((eligible & in_pg).sum()) / ne, 4) if ne else 0.0,
        "G": round(ne / n, 4) if n else 0.0,
        "nests": int(np.unique(nests[nests >= 0]).size),
        "obj": [[round(float(o.x), 3), round(float(o.y), 3)] for o in w.play_objects],
    }
    return meta, payload


def pack(frames: list[tuple[dict[str, Any], bytes]], extra: dict[str, Any] | None = None,
         first: int = 0) -> bytes:
    """A blob of frames (module docstring); `first` is the index of frames[0] in its run."""
    heads, off = [], 0
    for i, (meta, payload) in enumerate(frames):
        heads.append({**meta, "i": first + i, "off": off, "len": len(payload)})
        off += len(payload)
    head = json.dumps({**(extra or {}), "frames": heads}, separators=(",", ":")).encode("utf-8")
    pad = (-(4 + len(head))) % 4
    return b"".join([struct.pack("<I", len(head)), head, b"\0" * pad]
                    + [payload for _, payload in frames])


def unpack(blob: bytes) -> tuple[dict[str, Any], list[dict[str, np.ndarray]]]:
    """Inverse of pack, for tests and analysis: the header and each frame's arrays."""
    (hlen,) = struct.unpack_from("<I", blob, 0)
    head = json.loads(blob[4:4 + hlen].decode("utf-8"))
    base = 4 + hlen + ((-(4 + hlen)) % 4)
    fmt = int((head.get("world") or {}).get("format", FORMAT))
    out = []
    for fr in head["frames"]:
        n, p = fr["n"], base + fr["off"]
        arrs: dict[str, np.ndarray] = {}
        for name, dt in FIELDS[:N_FIELDS.get(fmt, len(FIELDS))]:
            arr = np.frombuffer(blob, dtype=dt, count=n, offset=p)
            arrs[name] = arr
            p += arr.nbytes
        out.append(arrs)
    return head, out


def substep_times_ok(sim) -> bool:
    """Sub-step frames need the P4-13 physics (its roll runs once per sub-step) and decisions
    at every tick, so that each sub-step falls inside its own tick."""
    return (bool(sim.ball_physics) and sim.free_substeps > 1
            and sim.cfg.ticks_per_day == sim.cfg.ticks_per_day_ref)


def hook_substeps(sim, on_substep: Callable[[Any, int, float], None]) -> None:
    """Call on_substep(sim, j, t) after free-time sub-step j = 0 .. K-2 of each decision, at the
    sub-step's end time t (sub-step K-1 ends with the tick, whose frame the caller takes).
    `_roll_balls` runs once at the end of every sub-step under the P4-13 physics, so wrapping
    it on the instance sees each one; the wrapper only reads."""
    if not substep_times_ok(sim):
        return
    roll = sim._roll_balls
    K = sim.free_substeps
    state = {"tick": -1, "j": 0}

    def rolled() -> None:
        roll()
        if sim.tick != state["tick"]:
            state["tick"], state["j"] = sim.tick, 0
        j = state["j"]
        state["j"] = j + 1
        if j < K - 1:
            on_substep(sim, j, sim.day + (j + 1) * sim.dt_ref / K)

    sim._roll_balls = rolled
