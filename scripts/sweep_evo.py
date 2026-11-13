#!/usr/bin/env python
"""Evaluation of `evo` and H-h (PHASE4_DESIGN.md 4.4, fixed 2026-11-13 before any code or run).

Arms per lineage l (seeds 9889 + 2(l - 1) and the next, paired across arms):
  SEL   founders drawn from the lineage's final pool (pool_final.npz: 4 adult females, 4 males)
  NEU   founders drawn from its neutral control (pool_neu.npz)
  GEN0  founders drawn from its generation 0 (pool_gen0.npz)
plus the need-driven control without sub-steps on every seed (landmarks only, for the guard).
Evo runs: Calhoun's 4 pairs, 1,600 d, 6 ticks/day, NumPy, 12 sub-steps (re-chosen), 29 ten-day
trace windows (every fourth individual) as in H-g; landmarks, episode rates in every window,
phases, and the rules-v9 detector vector (1,000 surrogates, at most 400 individuals, detector
seed 0) on the four windows of section 4.3. Resumable at each stage; stops on a NaN.
Writes _output/evo_sweep/<arm>_l<l>_<seed>/evo_run.json and control_<seed>/control_run.json.

usage: python scripts/sweep_evo.py [--workers 8] [--lineages 1-8] [--arms SEL NEU GEN0 CTRL]
       [--evo _output/evo] [--out _output/evo_sweep] [--days 1600]
then:  python scripts/analyse_evo.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "_output" / "evo_sweep"
EVO = ROOT / "_output" / "evo"
CONFIG = ROOT / "configs" / "default.yaml"
STARTS = [150.0 + 50.0 * i for i in range(29)]  # 150 ... 1,550
WINDOW_DAYS = 10.0
DAYS = 1600.0
SEED0 = 9889
POOLS = {"SEL": "pool_final.npz", "NEU": "pool_neu.npz", "GEN0": "pool_gen0.npz"}
SURROGATES, MAX_INDIVIDUALS, DET_SEED = 1000, 400, 0


def seeds_of(lineage: int) -> list[int]:
    return [SEED0 + 2 * (lineage - 1), SEED0 + 2 * (lineage - 1) + 1]


def windows_for(days: float) -> list[tuple[float, float]]:
    return [(s, s + WINDOW_DAYS) for s in STARTS if s + WINDOW_DAYS <= days]


def _trace_path(d: Path, a: float, b: float) -> Path:
    return d / f"trace_{a:g}_{b:g}.npz"


def _series(metrics: Path):
    import pyarrow.parquet as pq

    t = pq.read_table(metrics, columns=["day", "n_alive"])
    return t.column("day").to_numpy(), t.column("n_alive").to_numpy()


def run_control(job: tuple[int, str, float]) -> dict:
    """The need-driven control without sub-steps: landmarks only."""
    seed, out, days = job
    from universe25.config import load_config
    from universe25.metrics.calibration import calibrate
    from universe25.sim import Universe25Sim

    d = Path(out) / f"control_{seed}"
    t0 = time.perf_counter()
    timing: dict[str, float] = {}
    if not (d / "run.json").exists():
        over = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                    log_every_ticks=6, snapshot_every_days=0, policy={"kind": "need_driven"})
        Universe25Sim(load_config(CONFIG, over), d).run()
        timing["run_s"] = time.perf_counter() - t0
    summary = json.loads((d / "run.json").read_text(encoding="utf-8"))
    obs = calibrate(d / "metrics.parquet", summary)["observed"]
    stop = [f"NaN in {d.name}"] if summary.get("nan_count", 0) else []
    res = {"arm": "CTRL", "seed": seed, "days": days, "landmarks": obs, "run_summary": summary,
           "stop": stop}
    (d / "control_run.json").write_text(json.dumps(res, default=float, indent=1),
                                        encoding="utf-8")
    return {"name": d.name, "stop": stop, "timing": timing, "wall": time.perf_counter() - t0,
            "peak_n": summary.get("peak_n"), "t_pk": float(obs.get("peak_day", float("nan")))}


def run_evo(job: tuple[str, int, int, str, str, float]) -> dict:
    """One evo run: simulate, then rates, then detector vectors; each stage is skipped when
    its output exists."""
    arm, lineage, seed, evo_dir, out, days = job
    import numpy as np

    from universe25.config import load_config
    from universe25.metrics.calibration import calibrate
    from universe25.metrics.detectors import RULES, detect_trace
    from universe25.metrics.phase_rates import detector_windows, label_windows, window_rates
    from universe25.metrics.trace import load_trace
    from universe25.sim import Universe25Sim

    pool = Path(evo_dir) / f"lineage_{lineage}" / POOLS[arm]
    d = Path(out) / f"{arm}_l{lineage}_{seed}"
    wins = windows_for(days)
    t0 = time.perf_counter()
    timing: dict[str, float] = {}
    if not ((d / "run.json").exists() and all(_trace_path(d, a, b).exists() for a, b in wins)):
        over = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                    log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                    trace={"windows": wins, "sample_every": 4},
                    policy={"kind": "evo", "founders": str(pool), "founder_mode": "sample"})
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

    rates_f = d / "evo_rates.json"
    if rates_f.exists():
        windows = json.loads(rates_f.read_text(encoding="utf-8"))["windows"]
    else:
        t1 = time.perf_counter()
        days_s, ns = _series(d / "metrics.parquet")
        windows = []
        for a, b in wins:
            r = window_rates(load_trace(_trace_path(d, a, b)))
            mid = 0.5 * (a + b)
            r.update(start=a, end=b, mid=mid,
                     n_alive=float(ns[int(np.argmin(np.abs(days_s - mid)))]))
            windows.append(r)
        rates_f.write_text(json.dumps({"windows": windows}, default=float), encoding="utf-8")
        timing["rates_s"] = time.perf_counter() - t1
    label_windows(windows, t_fl, t_pk)

    pick = detector_windows(windows, t_fl, t_pk)
    det_f = d / "evo_detect.json"
    det = json.loads(det_f.read_text(encoding="utf-8")) if det_f.exists() else {}
    t2 = time.perf_counter()
    for mid in sorted({m for m in pick.values() if m is not None}):
        key = f"{mid:g}"
        if key in det and det[key].get("rules") == RULES:
            continue
        a = mid - 0.5 * WINDOW_DAYS
        tr = load_trace(_trace_path(d, a, a + WINDOW_DAYS))
        det[key] = detect_trace(tr, n_surrogates=SURROGATES, seed=DET_SEED,
                                max_individuals=MAX_INDIVIDUALS, legacy=False)
        det_f.write_text(json.dumps(det, default=float), encoding="utf-8")
    if any(m is not None for m in pick.values()):
        timing["detect_s"] = time.perf_counter() - t2
    pol_f = d / "evo_policy.json"
    res = {"arm": arm, "lineage": lineage, "seed": seed, "days": days, "pool": str(pool),
           "landmarks": obs, "t_fl": t_fl, "t_pk": t_pk, "run_summary": summary,
           "policy": json.loads(pol_f.read_text(encoding="utf-8")) if pol_f.exists() else None,
           "windows": windows, "detector_windows": pick,
           "detectors": {k: det[f"{m:g}"] for k, m in pick.items() if m is not None},
           "rules": RULES, "surrogates": SURROGATES, "max_individuals": MAX_INDIVIDUALS,
           "detector_seed": DET_SEED, "stop": stop, "timing": timing}
    (d / "evo_run.json").write_text(json.dumps(res, default=float, indent=1), encoding="utf-8")
    return {"name": d.name, "stop": stop, "timing": timing, "wall": time.perf_counter() - t0,
            "peak_n": summary.get("peak_n"), "t_pk": t_pk}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--lineages", type=str, default="1-8")
    p.add_argument("--arms", nargs="+", default=["SEL", "NEU", "GEN0", "CTRL"])
    p.add_argument("--evo", type=str, default=str(EVO))
    p.add_argument("--out", type=str, default=str(OUT))
    p.add_argument("--days", type=float, default=DAYS)
    p.add_argument("--seeds", type=str, default=None,
                   help="development only: run every arm on these seeds instead")
    a = p.parse_args()
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    def seeds(lin: int) -> list[int]:
        if a.seeds is None:
            return seeds_of(lin)
        s0, _, s1 = a.seeds.partition("-")
        return list(range(int(s0), int(s1 or s0) + 1))

    jobs = []
    for lin in lineages:
        if not (Path(a.evo) / f"lineage_{lin}" / POOLS["SEL"]).exists():
            print(f"lineage {lin}: no final pool (ended or not run); skipped", flush=True)
            continue
        for s in seeds(lin):
            for arm in a.arms:
                if arm in POOLS:
                    jobs.append(("evo", (arm, lin, s, a.evo, str(out), a.days)))
    if "CTRL" in a.arms:
        ctrl = sorted({s for lin in lineages for s in seeds(lin)})
        jobs += [("ctrl", (s, str(out), a.days)) for s in ctrl]
    t0 = time.perf_counter()
    stops: list[str] = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_evo if k == "evo" else run_control, j): j for k, j in jobs}
        for f in as_completed(futs):
            r = f.result()
            tm = " ".join(f"{k} {v:.0f}" for k, v in r.get("timing", {}).items()) or "kept"
            print(f"{r['name']}: peak {r['peak_n']} at {r['t_pk']:.0f}; {tm}; "
                  f"{r['wall']:.0f} s", flush=True)
            if r["stop"]:
                stops.extend(r["stop"])
                print("STOP: " + "; ".join(r["stop"]), flush=True)
                for g in futs:
                    g.cancel()
                break
    print(f"sweep {'stopped' if stops else 'done'} in {time.perf_counter() - t0:.0f} s",
          flush=True)
    return 1 if stops else 0


if __name__ == "__main__":
    raise SystemExit(main())
