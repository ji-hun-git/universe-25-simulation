"""Calhoun 1973 landmark calibration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

# Death Squared landmarks (Calhoun 1973, PMC1644264)
LANDMARKS = {
    "first_litters_day": 104.0,
    "n_at_day_315": 620.0,
    "peak_n": 2200.0,
    "peak_day": 560.0,
    "last_young_day": 600.0,
}


def calibrate(metrics_path: Path, run_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    table = pq.read_table(metrics_path)
    days = table.column("day").to_numpy()
    ns = table.column("n_alive").to_numpy()
    births = table.column("births_cum").to_numpy()
    last_young = table.column("last_young_day").to_numpy()

    # first litters: first day births_cum > 0
    first_birth_idx = np.flatnonzero(births > 0)
    first_litters = float(days[first_birth_idx[0]]) if len(first_birth_idx) else float("nan")

    n_315 = float(ns[np.argmin(np.abs(days - 315.0))]) if len(days) else float("nan")
    peak_i = int(np.argmax(ns)) if len(ns) else 0
    peak_n = float(ns[peak_i]) if len(ns) else 0.0
    peak_day = float(days[peak_i]) if len(days) else 0.0
    last_y = float(np.max(last_young)) if len(last_young) else 0.0

    pred = {
        "first_litters_day": first_litters,
        "n_at_day_315": n_315,
        "peak_n": peak_n,
        "peak_day": peak_day,
        "last_young_day": last_y,
    }
    errors = {}
    for k, target in LANDMARKS.items():
        p = pred[k]
        errors[k] = {
            "target": target,
            "observed": p,
            "abs_error": float(abs(p - target)) if p == p else float("nan"),
            "rel_error": float(abs(p - target) / target) if p == p and target else float("nan"),
        }

    # Phase detection (heuristic)
    phases = _detect_phases(days, ns)

    report = {
        "landmarks": LANDMARKS,
        "observed": pred,
        "errors": errors,
        "mean_rel_error": float(
            np.nanmean([errors[k]["rel_error"] for k in LANDMARKS])
        ),
        "phases": phases,
        "run_summary": run_summary or {},
        "note": "Phase-1 need-driven model; expect large calibration error until tuned.",
    }
    return report


def _detect_phases(days: np.ndarray, ns: np.ndarray) -> dict[str, Any]:
    if len(days) < 4:
        return {"detected": []}
    peak_i = int(np.argmax(ns))
    # growth: from 10% peak to peak
    growth_start = int(np.argmax(ns >= 0.1 * ns[peak_i]))
    # collapse: after peak, when N < 50% peak
    after = ns[peak_i:]
    collapse_rel = np.flatnonzero(after < 0.5 * ns[peak_i])
    collapse_i = peak_i + int(collapse_rel[0]) if len(collapse_rel) else None
    return {
        "adjustment_end_day": float(days[growth_start]) if growth_start else None,
        "peak_day": float(days[peak_i]),
        "collapse_onset_day": float(days[collapse_i]) if collapse_i is not None else None,
        "detected": ["adjustment", "growth", "stagnation", "collapse"]
        if collapse_i is not None
        else ["adjustment", "growth", "stagnation"],
    }


def write_calibration(metrics_path: Path, out_path: Path, run_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    report = calibrate(metrics_path, run_summary)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
