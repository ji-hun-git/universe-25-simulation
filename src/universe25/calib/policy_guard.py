"""Calibration guard for policy arms (phase 4, H-d; docs/PHASE4_DESIGN.md section 4).

Runs the same seeds under the need-driven control and under a policy kind, both on the frozen
biology, and reports the drift of every landmark. The verdict is preregistered (PLAN.md
section 15, H-d): a policy *preserves* the calibration when every canonical landmark mean is
within `TOL` (10 %) of the control mean on the same seeds and the decline band at day 1200
(0.35-0.85 x peak) still holds for the arm. A failed guard is a result to report in NOTES.md,
never a reason to retune the biology.

The guard never reads a PlayScore field and has no play-named term (H2).
"""
from __future__ import annotations

import json
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable

import numpy as np
import yaml

from universe25.metrics.calibration import LANDMARKS

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE = ROOT / "configs" / "default.yaml"
CANONICAL: tuple[str, ...] = tuple(LANDMARKS)
REPORT_KEYS: tuple[str, ...] = CANONICAL + (
    "n_at_day_736", "last_conception_day", "n_at_day_1200", "n_at_day_1444", "n_at_day_1588",
    "final_n",
)
DECLINE_BAND = (0.35, 0.85)  # N@1200 / peak, as in calib/priors.landmark_loss
TOL = 0.10  # H-d: relative drift of each canonical landmark mean vs the control
TICKS_PER_DAY = 6


def arm_config(kind: str, weights: str | None = None, base: Path | None = None,
               extra: dict[str, Any] | None = None) -> Path:
    """Write a temporary config: the base yaml with the policy block set to `kind` and the
    top-level `extra` keys (e.g. free_substeps) set."""
    data = yaml.safe_load((base or DEFAULT_BASE).read_text(encoding="utf-8")) or {}
    data.update(extra or {})
    pol: dict[str, Any] = {"kind": kind}
    if weights:
        pol["weights"] = str(weights)
    data["policy"] = pol
    tmp = Path(tempfile.mkdtemp(prefix="u25guard_")) / f"{kind}.yaml"
    tmp.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp


def _run_one(args: tuple[int, str, float]) -> tuple[int, dict[str, float]]:
    seed, base, days = args
    from universe25.calib.fast_eval import evaluate_params

    res = evaluate_params({}, seed=seed, days=days, ticks_per_day=TICKS_PER_DAY,
                          base_config=Path(base))
    return seed, {k: float(v) for k, v in res["observed"].items()}


def run_arm(
    kind: str,
    seeds: list[int],
    days: float,
    workers: int = 1,
    weights: str | None = None,
    base: Path | None = None,
    progress: Callable[[str], None] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[int, dict[str, float]]:
    """Landmarks per seed for one policy kind on the frozen biology (NumPy path, 6 ticks/day)."""
    cfg = arm_config(kind, weights, base, extra)
    jobs = [(s, str(cfg), float(days)) for s in seeds]
    rows: dict[int, dict[str, float]] = {}
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            it = ex.map(_run_one, jobs)
            for seed, obs in it:
                rows[seed] = obs
                if progress:
                    progress(_row_line(kind, seed, obs))
    else:
        for job in jobs:
            seed, obs = _run_one(job)
            rows[seed] = obs
            if progress:
                progress(_row_line(kind, seed, obs))
    return rows


def _row_line(kind: str, seed: int, obs: dict[str, float]) -> str:
    return f"{kind} seed={seed} " + " ".join(
        f"{k}={obs[k]:.0f}" for k in REPORT_KEYS if k in obs and np.isfinite(obs[k])
    )


def drift_table(
    control: dict[int, dict[str, float]],
    arm: dict[int, dict[str, float]],
    keys: tuple[str, ...] = REPORT_KEYS,
) -> dict[str, dict[str, float]]:
    """Per landmark: control and arm means (+ se), relative drift of the means, and the paired
    arm - control difference over the common seeds (mean +- se). NaN where undefined."""
    seeds = sorted(set(control) & set(arm))
    out: dict[str, dict[str, float]] = {}
    for k in keys:
        c = np.array([control[s].get(k, np.nan) for s in seeds], float)
        a = np.array([arm[s].get(k, np.nan) for s in seeds], float)
        ok = np.isfinite(c) & np.isfinite(a)
        n = int(ok.sum())
        d = a[ok] - c[ok]
        cm = float(np.nanmean(c)) if np.isfinite(c).any() else float("nan")
        am = float(np.nanmean(a)) if np.isfinite(a).any() else float("nan")
        out[k] = {
            "n": n,
            "control_mean": cm,
            "control_se": float(np.nanstd(c, ddof=1) / np.sqrt(np.isfinite(c).sum()))
            if np.isfinite(c).sum() > 1 else float("nan"),
            "arm_mean": am,
            "arm_se": float(np.nanstd(a, ddof=1) / np.sqrt(np.isfinite(a).sum()))
            if np.isfinite(a).sum() > 1 else float("nan"),
            "rel_drift": float(abs(am - cm) / abs(cm)) if cm not in (0.0,) and np.isfinite(cm)
            and np.isfinite(am) else float("nan"),
            "paired_diff": float(d.mean()) if n else float("nan"),
            "paired_se": float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan"),
        }
    return out


def decline_band_ok(rows: dict[int, dict[str, float]]) -> bool | None:
    """Band 0.35-0.85 x peak at day 1200 on the seed means; None below the horizon."""
    n1200 = np.array([r.get("n_at_day_1200", np.nan) for r in rows.values()], float)
    peak = np.array([r.get("peak_n", np.nan) for r in rows.values()], float)
    if not np.isfinite(n1200).any():
        return None
    ratio = float(np.nanmean(n1200)) / float(np.nanmean(peak))
    return bool(DECLINE_BAND[0] <= ratio <= DECLINE_BAND[1])


def verdict(table: dict[str, dict[str, float]], band_ok: bool | None,
            tol: float = TOL) -> dict[str, Any]:
    """H-d: preserved iff every canonical landmark drifts <= tol and the band holds (when
    measurable). Lists every failing landmark."""
    failures = [k for k in CANONICAL
                if not (np.isfinite(table[k]["rel_drift"]) and table[k]["rel_drift"] <= tol)]
    if band_ok is False:
        failures.append("decline_band_1200")
    return {"preserved": not failures, "failures": failures, "tol": tol,
            "decline_band_checked": band_ok is not None}


def guard(
    kind: str,
    seeds: list[int],
    days: float,
    workers: int = 1,
    weights: str | None = None,
    control_rows: dict[int, dict[str, float]] | None = None,
    base: Path | None = None,
    progress: Callable[[str], None] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run (or reuse) the control and run the arm on the same seeds; return the full report."""
    control = control_rows or run_arm("need_driven", seeds, days, workers, None, base, progress)
    arm = run_arm(kind, seeds, days, workers, weights, base, progress, extra)
    table = drift_table(control, arm)
    band = decline_band_ok(arm)
    return {
        "kind": kind, "weights": weights, "extra": extra or {}, "seeds": seeds, "days": days,
        "ticks_per_day": TICKS_PER_DAY, "control": {str(s): control[s] for s in seeds},
        "arm": {str(s): arm[s] for s in seeds}, "table": table,
        "decline_band_arm": band, "decline_band_control": decline_band_ok(control),
        "verdict": verdict(table, band),
    }


def format_table(report: dict[str, Any]) -> str:
    t = report["table"]
    lines = [f"== policy guard: {report['kind']} vs need_driven, {len(report['seeds'])} seeds "
             f"{report['seeds'][0]}-{report['seeds'][-1]}, {report['days']:.0f} d, "
             f"{report['ticks_per_day']} ticks/day",
             f"{'landmark':22s} {'control':>9s} {'se':>6s} {'arm':>9s} {'se':>6s} "
             f"{'drift':>7s} {'paired diff':>14s}"]
    for k in REPORT_KEYS:
        r = t[k]
        flag = " *" if k in CANONICAL and (not np.isfinite(r["rel_drift"])
                                           or r["rel_drift"] > report["verdict"]["tol"]) else ""
        lines.append(f"{k:22s} {r['control_mean']:9.1f} {r['control_se']:6.1f} "
                     f"{r['arm_mean']:9.1f} {r['arm_se']:6.1f} {r['rel_drift']:7.3f} "
                     f"{r['paired_diff']:+8.1f} ± {r['paired_se']:4.1f}{flag}")
    v = report["verdict"]
    band = report["decline_band_arm"]
    lines.append(f"decline band at 1200 (arm): "
                 f"{'not measurable' if band is None else ('ok' if band else 'FAILED')}")
    lines.append(f"H-d verdict: {'PRESERVED' if v['preserved'] else 'NOT PRESERVED'} "
                 f"(tol {v['tol']:.0%}; failures: {', '.join(v['failures']) or 'none'})")
    return "\n".join(lines)


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
