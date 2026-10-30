"""Calhoun 1973 landmark calibration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

# Death Squared landmarks (Calhoun 1973, PMC1644264). Canonical five used for mean_rel_error.
LANDMARKS = {
    "first_litters_day": 104.0,
    "n_at_day_315": 620.0,
    "peak_n": 2200.0,
    "peak_day": 560.0,
    "last_young_day": 600.0,  # last *surviving* birth (Calhoun: Day 600)
}

# Additional quantitative facts from the same paper (reported, not in the canonical mean):
#   N = 2056 at Day 736; 150 adults (+470 immatures) at Day 315; last conception ≈ Day 920.
EXTRA_LANDMARKS = {
    "n_at_day_736": 2056.0,
    "adults_at_day_315": 150.0,
    "last_conception_day": 920.0,
}

PEAK_FRACTION = 0.97  # "peak_day" = first day N reaches 97% of the maximum (plateau-robust)


def _nearest(days: np.ndarray, values: np.ndarray, day: float) -> float:
    return float(values[np.argmin(np.abs(days - day))]) if len(days) else float("nan")


def landmarks_from_series(
    days: np.ndarray,
    ns: np.ndarray,
    births: np.ndarray,
    last_young: np.ndarray,
    *,
    n_adult: np.ndarray | None = None,
    last_conception: np.ndarray | None = None,
) -> dict[str, float]:
    """Shared landmark extraction for parquet reports and the fast calibration loop."""
    first_birth_idx = np.flatnonzero(births > 0)
    first_litters = float(days[first_birth_idx[0]]) if len(first_birth_idx) else float("nan")
    peak_n = float(ns.max()) if len(ns) else 0.0
    if len(ns):
        peak_day = float(days[int(np.argmax(ns >= PEAK_FRACTION * peak_n))])
    else:
        peak_day = 0.0
    out = {
        "first_litters_day": first_litters,
        "n_at_day_315": _nearest(days, ns, 315.0),
        "peak_n": peak_n,
        "peak_day": peak_day,
        "last_young_day": float(np.max(last_young)) if len(last_young) else 0.0,
        "n_at_day_736": (
            _nearest(days, ns, 736.0) if len(days) and days[-1] >= 700 else float("nan")
        ),
        "final_n": float(ns[-1]) if len(ns) else 0.0,
        "final_day": float(days[-1]) if len(days) else 0.0,
    }
    if n_adult is not None and len(n_adult):
        out["adults_at_day_315"] = _nearest(days, n_adult, 315.0)
    else:
        out["adults_at_day_315"] = float("nan")
    if last_conception is not None and len(last_conception):
        out["last_conception_day"] = float(np.max(last_conception))
    else:
        out["last_conception_day"] = float("nan")
    if len(ns):
        peak_i = int(np.argmax(ns))
        out["n_min_after_peak"] = float(ns[peak_i:].min())
    else:
        out["n_min_after_peak"] = 0.0
    return out


def _rel_errors(pred: dict[str, float], targets: dict[str, float]) -> dict[str, dict[str, float]]:
    errors: dict[str, dict[str, float]] = {}
    for k, target in targets.items():
        p = pred.get(k, float("nan"))
        ok = p == p
        errors[k] = {
            "target": target,
            "observed": p,
            "abs_error": float(abs(p - target)) if ok else float("nan"),
            "rel_error": float(abs(p - target) / target) if ok and target else float("nan"),
        }
    return errors


def calibrate(metrics_path: Path, run_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    table = pq.read_table(metrics_path)
    cols = set(table.column_names)
    days = table.column("day").to_numpy()
    ns = table.column("n_alive").to_numpy()
    births = table.column("births_cum").to_numpy()
    # Prefer the surviving-birth column (newer runs); fall back to any-birth for old parquet.
    ly_col = "last_surviving_young_day" if "last_surviving_young_day" in cols else "last_young_day"
    last_young = table.column(ly_col).to_numpy()
    n_adult = table.column("n_adult").to_numpy() if "n_adult" in cols else None
    last_conc = (
        table.column("last_conception_day").to_numpy() if "last_conception_day" in cols else None
    )

    pred = landmarks_from_series(
        days, ns, births, last_young, n_adult=n_adult, last_conception=last_conc
    )
    errors = _rel_errors(pred, LANDMARKS)
    extra_errors = _rel_errors(pred, EXTRA_LANDMARKS)
    phases = _detect_phases(days, ns)

    all_rel = [errors[k]["rel_error"] for k in LANDMARKS] + [
        extra_errors[k]["rel_error"] for k in EXTRA_LANDMARKS
    ]
    report = {
        "landmarks": LANDMARKS,
        "extra_landmarks": EXTRA_LANDMARKS,
        "observed": pred,
        "errors": errors,
        "extra_errors": extra_errors,
        "mean_rel_error": float(np.nanmean([errors[k]["rel_error"] for k in LANDMARKS])),
        "mean_rel_error_extended": float(np.nanmean(all_rel)),
        "last_young_source": ly_col,
        "peak_day_definition": f"first day N >= {PEAK_FRACTION:.2f} * max N",
        "phases": phases,
        "run_summary": run_summary or {},
        "note": "Need-driven model; landmark errors reported without adjustment.",
    }
    return report


def _detect_phases(days: np.ndarray, ns: np.ndarray) -> dict[str, Any]:
    if len(days) < 4:
        return {"detected": []}
    peak_i = int(np.argmax(ns))
    # growth: from 10% peak to peak
    growth_start = int(np.argmax(ns >= 0.1 * ns[peak_i]))
    after = ns[peak_i:]
    # decline: first day after the peak below 90% of it; collapse: below 50%
    decline_rel = np.flatnonzero(after < 0.9 * ns[peak_i])
    collapse_rel = np.flatnonzero(after < 0.5 * ns[peak_i])
    decline_i = peak_i + int(decline_rel[0]) if len(decline_rel) else None
    collapse_i = peak_i + int(collapse_rel[0]) if len(collapse_rel) else None
    detected = ["adjustment", "growth", "stagnation"]
    if decline_i is not None:
        detected.append("decline")
    if collapse_i is not None:
        detected.append("collapse")
    return {
        "adjustment_end_day": float(days[growth_start]) if growth_start else None,
        "peak_day": float(days[peak_i]),
        "decline_onset_day": float(days[decline_i]) if decline_i is not None else None,
        "collapse_onset_day": float(days[collapse_i]) if collapse_i is not None else None,
        "detected": detected,
    }


def write_calibration(
    metrics_path: Path, out_path: Path, run_summary: dict[str, Any] | None = None
) -> dict[str, Any]:
    report = calibrate(metrics_path, run_summary)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
