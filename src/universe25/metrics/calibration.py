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
    # Cessation of surviving births (Calhoun: last surviving birth Day 600). Measured as the
    # last birth day on which the 30-day rate of births that reach weaning is still >= 5 % of
    # its maximum (the strict "latest weaned pup" is also reported; it is set by single lucky
    # survivors among ~10^5 births and is seed noise).
    "last_young_day": 600.0,
}

# Additional quantitative facts from the same paper (reported, not in the canonical mean):
#   N = 2056 at Day 736; 150 adults (+470 immatures) at Day 315; last conception ≈ Day 920.
EXTRA_LANDMARKS = {
    "n_at_day_736": 2056.0,
    "adults_at_day_315": 150.0,
    "last_conception_day": 920.0,  # rate-based cessation (30-day count < 5 % of max for good)
}

# "peak_day" = day of the maximum of the PEAK_WINDOW_DAYS running mean of N: Calhoun's 2200 at
# Day 560 is the census maximum, and the daily maximum of a pulsed birth process is a spike.
# The first day at PEAK_FRACTION x max (used up to phase 2j) marks the *start* of a flat plateau
# and ran ~30 days early by construction; it is still reported as peak_day_97pct.
PEAK_WINDOW_DAYS = 31
PEAK_FRACTION = 0.97


CESSATION_WINDOW_DAYS = 30
CESSATION_FRACTION = 0.05


def rate_cessation_day(
    events_by_day: np.ndarray,
    window: int = CESSATION_WINDOW_DAYS,
    frac: float = CESSATION_FRACTION,
) -> float:
    """Last event day whose trailing `window`-day event count is still >= frac x the maximum
    such count (events: surviving births by birth day, or conceptions by day). 0 if none.

    Single-event "last X day" statistics are set by one straggler among ~10^4-10^5 events and
    swing by +-100 days between seeds or parameter nudges; this is the day the process
    effectively ended.
    """
    hist = np.asarray(events_by_day, dtype=np.float64)
    if hist.size == 0 or hist.sum() <= 0:
        return 0.0
    roll = np.convolve(hist, np.ones(int(window)), mode="full")[: hist.size]
    # anchor on birth days that had a surviving birth themselves (a trailing window that is
    # still above threshold after the last such day would otherwise return the array end)
    above = np.flatnonzero((roll >= frac * roll.max()) & (hist > 0))
    return float(above[-1]) if above.size else 0.0


def surviving_birth_cessation_day(
    surv_births_by_day: np.ndarray,
    window: int = CESSATION_WINDOW_DAYS,
    frac: float = CESSATION_FRACTION,
) -> float:
    return rate_cessation_day(surv_births_by_day, window, frac)


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
    surv_births_by_day: np.ndarray | None = None,
    conceptions_by_day: np.ndarray | None = None,
) -> dict[str, float]:
    """Shared landmark extraction for parquet reports and the fast calibration loop.

    With `surv_births_by_day` (count of pups that reached weaning, by birth day) the
    `last_young_day` landmark is the rate-based cessation day; otherwise it falls back to the
    strict latest-weaned-pup birth day in `last_young`.
    """
    first_birth_idx = np.flatnonzero(births > 0)
    first_litters = float(days[first_birth_idx[0]]) if len(first_birth_idx) else float("nan")
    peak_n = float(ns.max()) if len(ns) else 0.0
    if len(ns):
        peak_day_97 = float(days[int(np.argmax(ns >= PEAK_FRACTION * peak_n))])
        peak_day_raw = float(days[int(np.argmax(ns))])
        w = min(PEAK_WINDOW_DAYS, len(ns))
        sm = np.convolve(ns.astype(np.float64), np.ones(w) / w, mode="valid")
        peak_day = float(days[int(np.argmax(sm)) + w // 2])
    else:
        peak_day = peak_day_97 = peak_day_raw = 0.0
    out = {
        "first_litters_day": first_litters,
        "n_at_day_315": _nearest(days, ns, 315.0),
        "peak_n": peak_n,
        "peak_day": peak_day,
        "peak_day_97pct": peak_day_97,
        "peak_day_raw_max": peak_day_raw,
        "last_young_day": float(np.max(last_young)) if len(last_young) else 0.0,
        "last_surviving_birth_strict_day": float(np.max(last_young)) if len(last_young) else 0.0,
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
        out["last_conception_strict_day"] = float(np.max(last_conception))
    else:
        out["last_conception_day"] = float("nan")
        out["last_conception_strict_day"] = float("nan")
    if conceptions_by_day is not None and np.asarray(conceptions_by_day).sum() > 0:
        out["last_conception_day"] = rate_cessation_day(conceptions_by_day)
    if len(ns):
        peak_i = int(np.argmax(ns))
        out["n_min_after_peak"] = float(ns[peak_i:].min())
        # Plateau level: the daily maximum of a pulsed birth process sits a few percent above
        # the level around it (litters arriving in bursts, doomed pups in the pipeline).
        # Reported, not fitted; Calhoun's 2200 is a single census, not a maximum.
        w = min(31, len(ns))
        out["peak_n_31d_mean"] = float(np.convolve(ns, np.ones(w) / w, mode="valid").max())
    else:
        out["n_min_after_peak"] = 0.0
        out["peak_n_31d_mean"] = 0.0
    if surv_births_by_day is not None:
        out["last_young_day"] = surviving_birth_cessation_day(surv_births_by_day)
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
    ly_source = ly_col
    n_adult = table.column("n_adult").to_numpy() if "n_adult" in cols else None
    last_conc = (
        table.column("last_conception_day").to_numpy() if "last_conception_day" in cols else None
    )

    pred = landmarks_from_series(
        days, ns, births, last_young, n_adult=n_adult, last_conception=last_conc
    )
    if run_summary and run_summary.get("surviving_birth_cessation_day") is not None:
        pred["last_young_day"] = float(run_summary["surviving_birth_cessation_day"])
        ly_source = "surviving_birth_cessation_day (run.json)"
    if run_summary and run_summary.get("conception_cessation_day") is not None:
        pred["last_conception_day"] = float(run_summary["conception_cessation_day"])
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
        "last_young_source": ly_source,
        "peak_day_definition": (
            f"day of the {PEAK_WINDOW_DAYS}-day running-mean maximum of N "
            f"(peak_day_97pct: first day N >= {PEAK_FRACTION:.2f} * max N; peak_day_raw_max)"
        ),
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
