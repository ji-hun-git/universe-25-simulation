"""Golden trajectory hashes across the feature-flag matrix (Tier 0 of docs/REVIEW_2026-11-09.md).

Every arm is built from committed inputs only (configs and seeded random networks, never
`_output/` weights), so the table in `tests/golden/trajectories.json` can be checked on a fresh
clone. A hash depends on the platform and the NumPy version, so the table records both and the
check skips (with a note) where they differ. Refresh the table only with
`scripts/golden_hashes.py --update`, and record why in NOTES.

Arms (seed 7000, 6 ticks per day unless stated):
  k1                 the calibrated colony, no sub-steps
  k12_continue       12 free-time sub-steps, heuristic repeats its decision (P4-8)
  k12_traced         k12_continue with a trace window: its trajectory must equal k12_continue's
  k12_rechoose_mlp   a seeded random MLP (observation v5) re-choosing at sub-steps
  physics_novelty    ball physics + novelty-based curiosity at g = 8 (P4-13 / P4-14)
  scarce             configs/scarce.yaml (food-limited capacity)
  tpd24              24 ticks per day
  replica_v2         configs/replica_v2.yaml (replica v2: Calhoun's pen, its current milestone)
The fast tier runs each for FAST_DAYS (past the first births), the slow tier for SLOW_DAYS.
"""
from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

import numpy as np

from universe25.repro import ROOT, trajectory_hash

TABLE = ROOT / "tests" / "golden" / "trajectories.json"
FAST_DAYS = 115.0
SLOW_DAYS = 300.0
_BASE = dict(seed=7000, ticks_per_day=6, backend="numpy", device="cpu", log_every_ticks=6,
             snapshot_every_days=0)
_K12 = dict(free_substeps=12)
ARMS: dict[str, tuple[str, dict[str, Any]]] = {
    "k1": ("default.yaml", {}),
    "k12_continue": ("default.yaml", _K12),
    "k12_traced": ("default.yaml", {**_K12, "trace": {"windows": [(100.0, 102.0)],
                                                      "sample_every": 2}}),
    "k12_rechoose_mlp": ("default.yaml", {**_K12, "policy": {"kind": "mlp_frozen"}}),
    "physics_novelty": ("default.yaml", {**_K12, "playground": {"ball_physics": True},
                                         "drives": {"curiosity_novelty": True,
                                                    "consequence_gain": 8.0}}),
    "scarce": ("scarce.yaml", {}),
    "tpd24": ("default.yaml", {"ticks_per_day": 24}),
    "replica_v2": ("replica_v2.yaml", {}),  # Calhoun's pen (docs/REPLICA_V2.md)
}


def environment() -> dict[str, str]:
    return {"numpy": np.__version__, "platform": f"{platform.system()}-{platform.machine()}"}


def run_arm(name: str, days: float) -> dict[str, Any]:
    from universe25.config import load_config

    base, over = ARMS[name]
    cfg = load_config(ROOT / "configs" / base, {**_BASE, **over, "days": days})
    return trajectory_hash(cfg, days)


def load_table() -> dict[str, Any]:
    return json.loads(TABLE.read_text(encoding="utf-8")) if TABLE.exists() else {}


def check(tier: str, names: tuple[str, ...] | None = None) -> tuple[list[str], str | None]:
    """(mismatches, skip reason). The traced arm must also match k12_continue's trajectory."""
    table = load_table()
    entry = table.get(tier)
    if not entry:
        return [], f"no {tier} golden table"
    if entry.get("environment") != environment():
        return [], (f"golden table recorded on {entry.get('environment')}, this is "
                    f"{environment()}: hashes are platform and NumPy dependent")
    days = FAST_DAYS if tier == "fast" else SLOW_DAYS
    bad = []
    got: dict[str, dict[str, Any]] = {}
    for name in names or tuple(ARMS):
        got[name] = run_arm(name, days)
        want = entry["arms"].get(name)
        if want is None or got[name] != want:
            bad.append(f"{name}: got {got[name]}, want {want}")
    if "k12_traced" in got and "k12_continue" in got and \
            got["k12_traced"]["trajectory"] != got["k12_continue"]["trajectory"]:
        bad.append("the trace recorder perturbed the trajectory (k12_traced != k12_continue)")
    return bad, None
