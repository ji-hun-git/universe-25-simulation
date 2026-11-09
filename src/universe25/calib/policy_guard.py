"""Calibration guard for policy arms (phase 4, H-d; docs/PHASE4_DESIGN.md section 4).

Runs the same seeds under the need-driven control and under a policy kind, both on the frozen
biology, and reports the drift of every landmark. The verdict is preregistered (PLAN.md
section 15, H-d, amended 2026-11-06): a canonical landmark *fails* only when its mean drifts
more than `TOL` (10 %) from the control mean on the same seeds **and** the paired arm - control
difference exceeds `SE_MULT` (2) paired standard errors; a policy preserves the calibration
when no canonical landmark fails and the decline band at day 1200 (0.35-0.85 x peak) holds.
The original 10 %-only reading is reported alongside (`verdict_10pct_rule`): at 12 seeds the
paired se of N@315 is 12-16 % of its mean, so that rule could not resolve 10 % there. A
failed guard is a result to report in NOTES.md, never a reason to retune the biology.

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
SE_MULT = 2.0  # H-d (amended 2026-11-06): ... and the paired difference beyond 2 paired se
TICKS_PER_DAY = 6


def arm_config(kind: str, weights: str | None = None, base: Path | None = None,
               extra: dict[str, Any] | None = None) -> Path:
    """Write a temporary config: the base yaml with the policy block set to `kind` and the
    `extra` keys (e.g. free_substeps, playground.ball_physics) merged in."""
    from universe25.config import _deep_merge

    data = yaml.safe_load((base or DEFAULT_BASE).read_text(encoding="utf-8")) or {}
    data = _deep_merge(data, extra or {})
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


def _landmark_fails(r: dict[str, float], tol: float, se_mult: float | None) -> bool:
    """Drift beyond tol (NaN = fail) and, when se_mult is set, a paired difference beyond
    se_mult paired se (an undefined se cannot clear a drift)."""
    drift = r["rel_drift"]
    if not (np.isfinite(drift) and drift <= tol):
        if se_mult is None:
            return True
        d, se = r.get("paired_diff", np.nan), r.get("paired_se", np.nan)
        if not (np.isfinite(d) and np.isfinite(se)):
            return True
        return bool(abs(d) > se_mult * se)
    return False


def verdict(table: dict[str, dict[str, float]], band_ok: bool | None, tol: float = TOL,
            se_mult: float | None = SE_MULT) -> dict[str, Any]:
    """H-d (amended 2026-11-06): preserved iff no canonical landmark drifts more than tol with a
    paired difference beyond se_mult paired se, and the decline band holds (when measurable).
    se_mult=None gives the original 10 %-only rule. Lists every failing landmark."""
    failures = [k for k in CANONICAL if _landmark_fails(table[k], tol, se_mult)]
    if band_ok is False:
        failures.append("decline_band_1200")
    return {"preserved": not failures, "failures": failures, "tol": tol, "se_mult": se_mult,
            "decline_band_checked": band_ok is not None}


# ---------------------------------------------------------------- guard v2 (Tier 1, 2026-11-09)
# Equivalence margins (arm - control), preregistered in PHASE4_DESIGN.md 4.1: ("rel", f) is a
# fraction of the control mean, ("abs", v) an absolute difference in the landmark's units.
EQ_MARGINS: dict[str, tuple[str, float]] = {
    "peak_n": ("rel", 0.05),
    "n_at_day_736": ("rel", 0.05),
    "peak_day": ("abs", 30.0),
    "last_young_day": ("abs", 30.0),  # rate-based cessation of surviving births
    "last_conception_day": ("abs", 40.0),  # rate-based cessation of conceptions
    "doubling_time_phase_b_days": ("rel", 0.15),
    "decline_ratio_1200": ("abs", 0.07),  # N@1200 / peak N, per seed
}
EQ_REPORTED = ("first_litters_day", "n_at_day_315", "n_at_day_1444", "n_at_day_1588")
EQ_LEVEL = 0.90
EQ_BOOT = 10_000


def _with_ratio(rows: dict[int, dict[str, float]]) -> dict[int, dict[str, float]]:
    out = {}
    for s, r in rows.items():
        r = dict(r)
        p, n = r.get("peak_n", np.nan), r.get("n_at_day_1200", np.nan)
        r["decline_ratio_1200"] = float(n / p) if np.isfinite(p) and p > 0 and np.isfinite(n) \
            else float("nan")
        out[s] = r
    return out


def equivalence(control: dict[int, dict[str, float]], arm: dict[int, dict[str, float]],
                seed: int = 0, n_boot: int = EQ_BOOT, level: float = EQ_LEVEL) -> dict[str, Any]:
    """Guard v2 (PHASE4_DESIGN.md 4.1): per primary landmark, the difference of the means
    (arm - control) with a percentile bootstrap CI (seeds resampled within each arm on their own
    stream); equivalent iff every CI lies inside its margin, not equivalent iff any CI lies wholly
    outside, else inconclusive. Arms need not share seeds."""
    rng = np.random.default_rng([int(seed), 4_100_001])
    c_rows, a_rows = _with_ratio(control), _with_ratio(arm)
    lo_q, hi_q = (1.0 - level) / 2.0, 1.0 - (1.0 - level) / 2.0
    table: dict[str, dict[str, Any]] = {}
    status = []
    for k in tuple(EQ_MARGINS) + EQ_REPORTED:
        c = np.array([r.get(k, np.nan) for r in c_rows.values()], float)
        a = np.array([r.get(k, np.nan) for r in a_rows.values()], float)
        c, a = c[np.isfinite(c)], a[np.isfinite(a)]
        row: dict[str, Any] = {"n_control": int(c.size), "n_arm": int(a.size)}
        if c.size < 2 or a.size < 2:
            row.update(diff=float("nan"), ci=[float("nan"), float("nan")], status="undefined")
        else:
            diff = float(a.mean() - c.mean())
            bc = c[rng.integers(0, c.size, (n_boot, c.size))].mean(axis=1)
            ba = a[rng.integers(0, a.size, (n_boot, a.size))].mean(axis=1)
            lo, hi = np.quantile(ba - bc, [lo_q, hi_q])
            row.update(diff=diff, ci=[float(lo), float(hi)], control_mean=float(c.mean()),
                       arm_mean=float(a.mean()))
            if k in EQ_MARGINS:
                kind, m = EQ_MARGINS[k]
                margin = m * abs(float(c.mean())) if kind == "rel" else m
                row["margin"] = float(margin)
                if -margin <= lo and hi <= margin:
                    row["status"] = "inside"
                elif hi < -margin or lo > margin:
                    row["status"] = "outside"
                else:
                    row["status"] = "overlaps"
            else:
                row["status"] = "reported"
        table[k] = row
        if k in EQ_MARGINS:
            status.append(row["status"])
    if any(s == "outside" for s in status):
        verdict = "not equivalent"
    elif all(s == "inside" for s in status):
        verdict = "equivalent"
    else:
        verdict = "inconclusive"
    return {"verdict": verdict, "level": level, "n_boot": n_boot, "table": table,
            "margins": {k: list(v) for k, v in EQ_MARGINS.items()}}


def format_equivalence(eq: dict[str, Any]) -> str:
    lines = [f"guard v2 (equivalence, {eq['level']:.0%} bootstrap CI): {eq['verdict'].upper()}",
             f"{'landmark':28s} {'diff':>9s} {'CI':>21s} {'margin':>9s}  status"]
    for k, r in eq["table"].items():
        m = r.get("margin")
        lines.append(f"{k:28s} {r['diff']:+9.3f} [{r['ci'][0]:+9.3f}, {r['ci'][1]:+9.3f}] "
                     f"{'' if m is None else f'±{m:.3f}':>9s}  {r['status']}")
    return "\n".join(lines)


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
        "verdict_10pct_rule": verdict(table, band, se_mult=None),
        "equivalence_v2": equivalence(control, arm, seed=seeds[0]),
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
        flag = ""
        if k in CANONICAL and _landmark_fails(r, report["verdict"]["tol"], None):
            amended = _landmark_fails(r, report["verdict"]["tol"],
                                      report["verdict"].get("se_mult", SE_MULT))
            flag = " **" if amended else " *"  # * drift > 10 %, ** and beyond 2 paired se
        lines.append(f"{k:22s} {r['control_mean']:9.1f} {r['control_se']:6.1f} "
                     f"{r['arm_mean']:9.1f} {r['arm_se']:6.1f} {r['rel_drift']:7.3f} "
                     f"{r['paired_diff']:+8.1f} ± {r['paired_se']:4.1f}{flag}")
    v = report["verdict"]
    band = report["decline_band_arm"]
    lines.append(f"decline band at 1200 (arm): "
                 f"{'not measurable' if band is None else ('ok' if band else 'FAILED')}")
    lines.append(f"H-d verdict (amended: drift > {v['tol']:.0%} and > "
                 f"{v.get('se_mult', SE_MULT):g} paired se): "
                 f"{'PRESERVED' if v['preserved'] else 'NOT PRESERVED'} "
                 f"(failures: {', '.join(v['failures']) or 'none'})")
    v0 = report.get("verdict_10pct_rule")
    if v0 is not None:
        lines.append(f"original 10 % rule: {'PRESERVED' if v0['preserved'] else 'NOT PRESERVED'}"
                     f" (failures: {', '.join(v0['failures']) or 'none'})")
    eq = report.get("equivalence_v2")
    if eq is not None:
        lines.append(format_equivalence(eq))
    return "\n".join(lines)


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
