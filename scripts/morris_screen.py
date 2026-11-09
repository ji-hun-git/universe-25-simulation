#!/usr/bin/env python
"""Morris screening of the calibrated colony (PHASE4_DESIGN.md 4.1, Tier 1, preregistered
2026-11-09). Identifiability: how many directions do the landmarks constrain?

Parameters: the searched parameters of calib/priors.py on their prior boxes (log-uniform where
the prior is), plus every biology and drive value set by hand in configs/default.yaml without a
prior, on +-30 % of its frozen value (booleans and zero values skipped; integers rounded).
Design: r = 10 trajectories, 4 levels (delta = 2/3 of the normalised range), the factor order
random per trajectory; seeds 7003 and 7004 for every point (common random numbers); K = 1,
6 ticks/day, 1,600 d, NumPy. Output per landmark: mu* and sigma of the elementary effects of
each parameter (in landmark units per unit of normalised range); the effective rank of the
landmark x parameter mu* matrix (rows scaled by the landmark's sd over all runs), counting
singular values above 5 % of the largest. No pass condition and no parameter change.

usage: python scripts/morris_screen.py [--workers 6] [--r 10]
Resumable: runs are cached in _output/morris/runs.json. Writes _output/morris/summary.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "_output" / "morris"
SEEDS = (7003, 7004)
LEVELS = 4
DELTA = LEVELS / (2.0 * (LEVELS - 1))  # 2/3
DAYS = 1600.0
HAND_RANGE = 0.30
LANDMARKS = ("first_litters_day", "n_at_day_315", "peak_n", "peak_day", "last_young_day",
             "n_at_day_736", "last_conception_day", "n_at_day_1200", "n_at_day_1444",
             "n_at_day_1588", "doubling_time_phase_b_days", "doubling_time_phase_c_days")


def factors() -> list[dict]:
    """(name, group, low, high, log, integer) for every screened parameter."""
    from universe25.calib.priors import PARAM_PRIORS

    out = [{"name": k, "group": v["group"], "low": float(v["low"]), "high": float(v["high"]),
            "log": bool(v["log"]), "int": False} for k, v in PARAM_PRIORS.items()]
    y = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))
    for group in ("biology", "drives"):
        for k, v in (y.get(group) or {}).items():
            if k in PARAM_PRIORS or isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            if float(v) == 0.0:
                continue
            out.append({"name": k, "group": group, "low": float(v) * (1 - HAND_RANGE),
                        "high": float(v) * (1 + HAND_RANGE), "log": False,
                        "int": isinstance(v, int)})
    return out


def to_value(f: dict, u: float) -> float:
    if f["log"]:
        v = float(np.exp(np.log(f["low"]) + u * (np.log(f["high"]) - np.log(f["low"]))))
    else:
        v = f["low"] + u * (f["high"] - f["low"])
    return float(round(v)) if f["int"] else v


def design(n_f: int, r: int, rng: np.random.Generator) -> list[tuple[np.ndarray, list]]:
    """r trajectories: a start point on the lower levels, then one factor at a time by +-delta
    in a random order. Returns (points (n_f + 1, n_f), [(factor, signed delta), ...])."""
    grid = np.arange(LEVELS) / (LEVELS - 1)
    trajs = []
    for _ in range(r):
        x = rng.choice(grid[grid + DELTA <= 1.0 + 1e-9], size=n_f)
        pts = [x.copy()]
        steps = []
        for i in rng.permutation(n_f):
            d = DELTA if x[i] + DELTA <= 1.0 + 1e-9 else -DELTA
            x = x.copy()
            x[i] += d
            pts.append(x)
            steps.append((int(i), float(d)))
        trajs.append((np.array(pts), steps))
    return trajs


def run_point(job: tuple[str, dict, int]) -> tuple[str, dict]:
    key, over, seed = job
    from universe25.calib.fast_eval import evaluate_params
    from universe25.calib.policy_guard import arm_config

    base = arm_config("need_driven", None, None, over)
    res = evaluate_params({}, seed=seed, days=DAYS, ticks_per_day=6, base_config=base)
    return key, {k: float(res["observed"].get(k, np.nan)) for k in LANDMARKS}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--r", type=int, default=10)
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    fs = factors()
    rng = np.random.default_rng([7003, 4_300_001])
    trajs = design(len(fs), a.r, rng)
    runs_f = OUT / "runs.json"
    runs: dict[str, dict] = json.loads(runs_f.read_text(encoding="utf-8")) if runs_f.exists() \
        else {}
    jobs = []
    for t, (pts, _) in enumerate(trajs):
        for j, u in enumerate(pts):
            over: dict[str, dict] = {"biology": {}, "drives": {}}
            for f, ui in zip(fs, u):
                over[f["group"]][f["name"]] = to_value(f, float(ui))
            for s in SEEDS:
                key = f"{t}_{j}_{s}"
                if key not in runs:
                    jobs.append((key, over, s))
    print(f"{len(fs)} factors, {a.r} trajectories, {len(SEEDS)} seeds: "
          f"{a.r * (len(fs) + 1) * len(SEEDS)} runs, {len(jobs)} to do", flush=True)
    t0 = time.perf_counter()
    if jobs:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for n, (key, obs) in enumerate(ex.map(run_point, jobs), 1):
                runs[key] = obs
                if n % 12 == 0 or n == len(jobs):
                    runs_f.write_text(json.dumps(runs), encoding="utf-8")
                    print(f"  {n}/{len(jobs)} ({time.perf_counter() - t0:.0f} s)", flush=True)
    # elementary effects
    ee = {lm: [[] for _ in fs] for lm in LANDMARKS}
    for t, (pts, steps) in enumerate(trajs):
        for j, (i, d) in enumerate(steps):
            for s in SEEDS:
                y0, y1 = runs[f"{t}_{j}_{s}"], runs[f"{t}_{j + 1}_{s}"]
                for lm in LANDMARKS:
                    if np.isfinite(y0[lm]) and np.isfinite(y1[lm]):
                        ee[lm][i].append((y1[lm] - y0[lm]) / d)
    all_y = {lm: np.array([r[lm] for r in runs.values()], float) for lm in LANDMARKS}
    mu = np.zeros((len(LANDMARKS), len(fs)))
    summary: dict = {"factors": fs, "landmarks": {}, "seeds": SEEDS, "r": a.r}
    for li, lm in enumerate(LANDMARKS):
        sd = float(np.nanstd(all_y[lm]))
        rows = []
        for i, f in enumerate(fs):
            e = np.array(ee[lm][i], float)
            mstar = float(np.mean(np.abs(e))) if e.size else float("nan")
            sig = float(np.std(e, ddof=1)) if e.size > 1 else float("nan")
            mu[li, i] = mstar / sd if sd > 0 and np.isfinite(mstar) else 0.0
            rows.append({"factor": f["name"], "mu_star": mstar, "sigma": sig, "n": int(e.size)})
        rows.sort(key=lambda r: -(r["mu_star"] if np.isfinite(r["mu_star"]) else -1))
        summary["landmarks"][lm] = {"sd_over_runs": sd, "ranking": rows}
        top = ", ".join(f"{r['factor']} {r['mu_star']:.3g}" for r in rows[:5])
        print(f"{lm:28s} sd {sd:9.2f} | top mu*: {top}")
    sv = np.linalg.svd(np.nan_to_num(mu), compute_uv=False)
    rank = int(np.sum(sv > 0.05 * sv[0])) if sv.size and sv[0] > 0 else 0
    summary["singular_values"] = sv.tolist()
    summary["effective_rank"] = rank
    print(f"\neffective rank of the landmark x parameter mu* matrix (rows scaled by sd): {rank} "
          f"of {len(LANDMARKS)} landmarks, {len(fs)} parameters; singular values "
          + " ".join(f"{v:.3g}" for v in sv))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
