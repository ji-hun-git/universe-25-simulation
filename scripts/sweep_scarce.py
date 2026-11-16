#!/usr/bin/env python
"""Evaluation of SCARCE-PG evo and H-j (PHASE4_DESIGN.md 4.6, fixed 2026-11-14 before any code
or run): a common garden, the canonical world, on fresh seeds 9929-9944.

Lineage l uses seeds 9929 + 2(l - 1) and the next, paired across the arms:
  SCARCE  4 F + 4 M drawn from the adults of scarce lineage l's final pool
          (_output/evo_scarce/lineage_l/pool_final.npz)
  ABUND   4 F + 4 M drawn from H-h's final pool of lineage l (_output/evo/.../pool_final.npz)
  NEU     8 founders drawn from H-h's neutral pool of lineage l (pool_neu.npz)
Each run is H-h's pipeline (scripts/sweep_evo.py): Calhoun's 4 pairs, 1,600 d, ABUND-PG, 6
ticks/day, NumPy, 12 sub-steps, 29 ten-day trace windows (every fourth individual), episode
rates in every window and the rules-v9 detector vector (1,000 surrogates, at most 400
individuals, detector seed 0) on the four windows of section 4.3; a window without traced rows
is empty (section 4.5). Added: the time budget of every window (metrics/phase_rates.py
window_budget), computed from the same loaded trace as its rates. Resumable at each stage;
stops on a NaN. Writes _output/scarce_sweep/<arm>_l<l>_<seed>/scarce_run.json.

--regime small evaluates small-meal evo instead (PHASE4_DESIGN.md 4.7): arms SMALL (the
small-meal lineage's final pool, _output/evo_small), ABUND and NEU, on fresh seeds 9945-9960
(lineage l: 9945 + 2(l - 1) and the next); the same pipeline. Writes _output/small_sweep/.

--regime late evaluates late-reflex evo (PHASE4_DESIGN.md 4.8): arms LS and LF (the two late
lines' final pools, _output/evo_late_small and _output/evo_late_full), ABUND and NEU, on fresh
seeds 9961-9976 (lineage l: 9961 + 2(l - 1) and the next), in the late world with full meals
(drives.reflex_need 1.0, starvation hazard 0.05 a day); otherwise the same pipeline. Its traces
record the reflex threshold, and the time budget's eligible rows follow it. Writes
_output/late_sweep/.

usage: python scripts/sweep_scarce.py [--regime scarce|small|late] [--workers 8]
           [--lineages 1-8] [--arms SCARCE ABUND NEU] [--skip-missing]
       python scripts/sweep_scarce.py --dev --lineages 1 --days 300 \
           --evo-scarce _output/evo_scarce_dev --out _output/scarce_dev
       python scripts/sweep_scarce.py --regime late --dev --lineages 1 --days 300 \
           --evolved LS=_output/evo_late_small_dev LF=_output/evo_late_full_dev \
           --out _output/late_dev
--dev runs one seed per lineage, the training seed 7000 (the harness smoke, for timing only; no
statistic of it is read).
then:  python scripts/analyse_scarce.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from sweep_evo import (  # noqa: E402  (H-h's pipeline, unchanged)
    CONFIG,
    DET_SEED,
    MAX_INDIVIDUALS,
    SURROGATES,
    WINDOW_DAYS,
    _series,
    _trace_path,
    windows_for,
)
from sweep_nm import _empty_window, _sim_done  # noqa: E402  (H-i's empty windows)

from evolve_scarce import LATE_WORLD  # noqa: E402  (the late world, PHASE4_DESIGN.md 4.8)

OUT = ROOT / "_output" / "scarce_sweep"
EVO = ROOT / "_output" / "evo"
EVO_SCARCE = ROOT / "_output" / "evo_scarce"
DAYS = 1600.0
SEED0 = 9929
DEV_SEED = 7000
ARMS = ("SCARCE", "ABUND", "NEU")
# regime: (its arms, first seed, the evolved arms' lineage folders, the sweep folder, the
# garden's config options; None is the canonical world)
REGIMES = {
    "scarce": (ARMS, SEED0, {"SCARCE": EVO_SCARCE}, OUT, None),
    "small": (("SMALL", "ABUND", "NEU"), 9945, {"SMALL": ROOT / "_output" / "evo_small"},
              ROOT / "_output" / "small_sweep", None),
    "late": (("LS", "LF", "ABUND", "NEU"), 9961,
             {"LS": ROOT / "_output" / "evo_late_small", "LF": ROOT / "_output" / "evo_late_full"},
             ROOT / "_output" / "late_sweep", LATE_WORLD),
}


def seeds_of(lineage: int, dev: bool = False, seed0: int = SEED0) -> list[int]:
    if dev:
        return [DEV_SEED]
    return [seed0 + 2 * (int(lineage) - 1), seed0 + 2 * (int(lineage) - 1) + 1]


def pool_for(arm: str, lineage: int, evo: Path, evolved: dict[str, Path]) -> Path:
    """An evolved arm's final pool from its lineages' folder, or H-h's final or neutral pool."""
    if arm in evolved:
        return evolved[arm] / f"lineage_{lineage}" / "pool_final.npz"
    if arm == "ABUND":
        return evo / f"lineage_{lineage}" / "pool_final.npz"
    if arm == "NEU":
        return evo / f"lineage_{lineage}" / "pool_neu.npz"
    raise ValueError(arm)


def run_arm(job: tuple[str, int, int, str, str, float, dict | None]) -> dict:
    """One run: simulate, then rates and time budgets, then detector vectors; each stage is
    skipped when its output exists. The last element of `job` holds the garden's config options
    (None: the canonical world)."""
    arm, lineage, seed, pool, out, days, garden = job
    from universe25.config import load_config
    from universe25.metrics.calibration import calibrate
    from universe25.metrics.detectors import RULES, detect_trace
    from universe25.metrics.phase_rates import (detector_windows, empty_budget, label_windows,
                                                window_budget, window_rates)
    from universe25.metrics.trace import load_trace
    from universe25.sim import Universe25Sim

    d = Path(out) / f"{arm}_l{lineage}_{seed}"
    wins = windows_for(days)
    t0 = time.perf_counter()
    res_f = d / "scarce_run.json"
    timing: dict[str, float] = (json.loads(res_f.read_text(encoding="utf-8")).get("timing", {})
                                if res_f.exists() else {})
    if not _sim_done(d):
        over = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                    log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                    trace={"windows": wins, "sample_every": 4},
                    policy={"kind": "evo", "founders": str(pool), "founder_mode": "sample"})
        if garden:
            over.update(garden)
        sim = Universe25Sim(load_config(CONFIG, over), d)
        sim.run()
        pol = sim.policy
        (d / "evo_policy.json").write_text(json.dumps(
            {"births": pol.n_births, "from_sire": pol.n_from_sire,
             "conceptions": pol.n_conceptions}), encoding="utf-8")
        timing["run_s"] = time.perf_counter() - t0
    summary = json.loads((d / "run.json").read_text(encoding="utf-8"))
    stop = [f"NaN in {d.name}"] if summary.get("nan_count", 0) else []
    obs = calibrate(d / "metrics.parquet", summary)["observed"]
    t_fl, t_pk = float(obs["first_litters_day"]), float(obs["peak_day"])
    written = {Path(x).name for x in summary.get("trace_files") or []}

    rates_f = d / "evo_rates.json"
    windows = (json.loads(rates_f.read_text(encoding="utf-8"))["windows"]
               if rates_f.exists() else None)
    if windows is None or not all("budget" in w for w in windows):
        t1 = time.perf_counter()
        days_s, ns = _series(d / "metrics.parquet")
        windows = []
        for a, b in wins:
            path = _trace_path(d, a, b)
            if path.name in written:
                tr = load_trace(path)
                r = window_rates(tr)
                r["budget"] = window_budget(tr)
            else:
                r = _empty_window()
                r["budget"] = empty_budget()
            mid = 0.5 * (a + b)
            alive = float(ns[int(np.argmin(np.abs(days_s - mid)))]) if mid <= days_s.max() else 0.0
            r.update(start=a, end=b, mid=mid, n_alive=alive)
            windows.append(r)
        rates_f.write_text(json.dumps({"windows": windows}, default=float), encoding="utf-8")
        timing["rates_s"] = time.perf_counter() - t1
    label_windows(windows, t_fl, t_pk)

    pick = detector_windows(windows, t_fl, t_pk)
    det_f = d / "evo_detect.json"
    det = json.loads(det_f.read_text(encoding="utf-8")) if det_f.exists() else {}
    t2 = time.perf_counter()
    detected = False
    for mid in sorted({m for m in pick.values() if m is not None}):
        key = f"{mid:g}"
        if key in det and det[key].get("rules") == RULES:
            continue
        a = mid - 0.5 * WINDOW_DAYS
        tr = load_trace(_trace_path(d, a, a + WINDOW_DAYS))
        det[key] = detect_trace(tr, n_surrogates=SURROGATES, seed=DET_SEED,
                                max_individuals=MAX_INDIVIDUALS, legacy=False)
        det_f.write_text(json.dumps(det, default=float), encoding="utf-8")
        detected = True
    if detected:
        timing["detect_s"] = time.perf_counter() - t2
    pol_f = d / "evo_policy.json"
    res = {"arm": arm, "lineage": lineage, "seed": seed, "days": days, "pool": str(pool),
           "landmarks": obs, "t_fl": t_fl, "t_pk": t_pk, "run_summary": summary,
           "policy": json.loads(pol_f.read_text(encoding="utf-8")) if pol_f.exists() else None,
           "windows": windows, "detector_windows": pick,
           "detectors": {k: det[f"{m:g}"] for k, m in pick.items() if m is not None},
           "rules": RULES, "surrogates": SURROGATES, "max_individuals": MAX_INDIVIDUALS,
           "detector_seed": DET_SEED,
           "empty_windows": sum(1 for a, b in wins if _trace_path(d, a, b).name not in written),
           "stop": stop, "timing": timing}
    if garden:
        res["garden"] = garden
    res_f.write_text(json.dumps(res, default=float, indent=1), encoding="utf-8")
    return {"name": d.name, "stop": stop, "timing": timing, "wall": time.perf_counter() - t0,
            "peak_n": summary.get("peak_n"), "t_pk": t_pk}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--lineages", type=str, default="1-8")
    p.add_argument("--regime", choices=sorted(REGIMES), default="scarce")
    p.add_argument("--arms", nargs="+", default=None, help="default: by regime")
    p.add_argument("--evo", type=str, default=str(EVO))
    p.add_argument("--evo-scarce", type=str, default=None,
                   help="the regime's first evolved arm's lineages (default: by regime)")
    p.add_argument("--evolved", nargs="+", default=None, metavar="ARM=DIR",
                   help="an evolved arm's lineages, e.g. LF=_output/evo_late_full_dev")
    p.add_argument("--out", type=str, default=None, help="default: by regime")
    p.add_argument("--days", type=float, default=DAYS)
    p.add_argument("--dev", action="store_true")
    p.add_argument("--skip-missing", action="store_true",
                   help="skip, and report, the runs whose pool is missing (a lineage that ended)")
    a = p.parse_args()
    arms0, seed0, evolved0, out_x, garden = REGIMES[a.regime]
    arms = a.arms or list(arms0)
    evolved = dict(evolved0)
    if a.evo_scarce:
        evolved[arms0[0]] = Path(a.evo_scarce)
    for kv in a.evolved or []:
        k, _, v = kv.partition("=")
        evolved[k] = Path(v)
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))
    out = Path(a.out) if a.out else out_x
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for lin in lineages:
        for arm in arms:
            pool = pool_for(arm, lin, Path(a.evo), evolved)
            if not pool.exists():
                print(f"missing pool for {arm} lineage {lin}: {pool}"
                      + (" (skipped)" if a.skip_missing else ""), flush=True)
                if a.skip_missing:
                    continue
                return 1
            jobs += [(arm, lin, s, str(pool), str(out), a.days, garden)
                     for s in seeds_of(lin, a.dev, seed0)]
    t0 = time.perf_counter()
    stops: list[str] = []
    failed: list[str] = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_arm, j): j for j in jobs}
        for f in as_completed(futs):
            try:
                r = f.result()
            except Exception as e:  # report every failed run, not only the first
                j = futs[f]
                failed.append(f"{j[0]}_l{j[1]}_{j[2]}")
                print(f"FAILED {failed[-1]}: {type(e).__name__}: {e}", flush=True)
                continue
            tm = " ".join(f"{k} {v:.0f}" for k, v in r.get("timing", {}).items()) or "kept"
            print(f"{r['name']}: peak {r['peak_n']} at {r['t_pk']:.0f}; {tm}; "
                  f"{r['wall']:.0f} s", flush=True)
            if r["stop"]:
                stops.extend(r["stop"])
                print("STOP: " + "; ".join(r["stop"]), flush=True)
                for g in futs:
                    g.cancel()
                break
    state = "stopped" if stops else (f"failed ({len(failed)} runs)" if failed else "done")
    print(f"sweep {state} in {time.perf_counter() - t0:.0f} s", flush=True)
    return 1 if stops or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
