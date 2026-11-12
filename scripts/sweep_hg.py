#!/usr/bin/env python
"""H-g and the playground-off arm (PHASE4_DESIGN.md section 4.3, fixed 2026-11-13 before any
run): run, trace, rates per window, detector vectors on four windows per run.

Arms: policy {learned: mlp_frozen with the nursery-trained pretrain_v2 net; need_driven; a random
frozen net of the same architecture, MlpFrozenPolicy.random_init(7000)} x playground {on:
configs/default.yaml (ABUND-PG); off: the same with playground.enabled false (ABUND-NOPG)} x
seeds 9877-9888 (fresh, paired). 1,600 days at 6 ticks/day, 12 free-time sub-steps (sub-step
mode auto); ten-day trace windows starting every 50 days from day 150 to 1,550, every fourth
individual.

Per run: landmarks (metrics/calibration.py) give its phases; every window gets its episode rates
(metrics/phase_rates.py, every traced individual); the four preregistered windows (middle of B,
middle of C, peak + 150, peak + 600) get the rules-v9 detector vector (1,000 surrogates, at most
400 individuals, detector seed 0, no legacy v7 pass). Writes _output/hg_sweep/<policy>_<arm>_<seed>/
hg_run.json. Resumable at each stage. Stops the sweep on a NaN or on an object event with the
playground off (preregistered stop rules).

usage: python scripts/sweep_hg.py [--workers 10] [--seeds 9877-9888] [--policies ...] [--arms ...]
       [--days 1600] [--out _output/hg_sweep]
then:  python scripts/analyse_hg.py
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

OUT = ROOT / "_output" / "hg_sweep"
STARTS = [150.0 + 50.0 * i for i in range(29)]  # 150 ... 1,550
WINDOW_DAYS = 10.0
DAYS = 1600.0
LEARNED = ROOT / "_output" / "pretrain" / "pretrain_v2" / "policy_final.npz"
RANDOM = ROOT / "_output" / "policy_random_v2_7000.npz"
CONFIG = ROOT / "configs" / "default.yaml"
POLICIES = ("learned", "need_driven", "random")
ARMS = ("pg_on", "pg_off")
SURROGATES, MAX_INDIVIDUALS, DET_SEED = 1000, 400, 0


def policy_over(policy: str) -> dict:
    if policy == "need_driven":
        return {"kind": "need_driven"}
    if policy == "learned":
        return {"kind": "mlp_frozen", "weights": str(LEARNED)}
    if policy == "random":
        return {"kind": "mlp_frozen", "weights": str(RANDOM)}
    raise ValueError(policy)


def windows_for(days: float) -> list[tuple[float, float]]:
    return [(s, s + WINDOW_DAYS) for s in STARTS if s + WINDOW_DAYS <= days]


def _trace_path(d: Path, a: float, b: float) -> Path:
    return d / f"trace_{a:g}_{b:g}.npz"


def _series(metrics: Path):
    import pyarrow.parquet as pq

    t = pq.read_table(metrics, columns=["day", "n_alive"])
    return t.column("day").to_numpy(), t.column("n_alive").to_numpy()


def run_job(job: tuple[str, str, int, str, float]) -> dict:
    """One run: simulate, then rates, then detector vectors; each stage is skipped when its
    output exists."""
    policy, arm, seed, out, days = job
    import numpy as np

    from universe25.config import load_config
    from universe25.metrics.calibration import calibrate
    from universe25.metrics.detectors import RULES, detect_trace
    from universe25.metrics.phase_rates import detector_windows, label_windows, window_rates
    from universe25.metrics.trace import load_trace
    from universe25.sim import Universe25Sim

    d = Path(out) / f"{policy}_{arm}_{seed}"
    wins = windows_for(days)
    t0 = time.perf_counter()
    timing: dict[str, float] = {}
    if not ((d / "run.json").exists() and all(_trace_path(d, a, b).exists() for a, b in wins)):
        over = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                    log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                    trace={"windows": wins, "sample_every": 4}, policy=policy_over(policy))
        if arm == "pg_off":
            over["playground"] = {"enabled": False}
            over["arm_label"] = "TRACK-E-U25-ABUND-NOPG"
        Universe25Sim(load_config(CONFIG, over), d).run()
        timing["run_s"] = time.perf_counter() - t0
    summary = json.loads((d / "run.json").read_text(encoding="utf-8"))
    stop = []
    if summary.get("nan_count", 0):
        stop.append(f"NaN in {d.name}")
    obs = calibrate(d / "metrics.parquet", summary)["observed"]
    t_fl, t_pk = float(obs["first_litters_day"]), float(obs["peak_day"])

    rates_f = d / "hg_rates.json"
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
    if arm == "pg_off":
        bad = [w["mid"] for w in windows if w["object"]["n_events"] > 0]
        if bad:
            stop.append(f"object events with the playground off in {d.name} at {bad}")

    pick = detector_windows(windows, t_fl, t_pk)
    det_f = d / "hg_detect.json"
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
    if pick and any(m is not None for m in pick.values()):
        timing["detect_s"] = time.perf_counter() - t2

    res = {"policy": policy, "arm": arm, "seed": seed, "days": days,
           "landmarks": obs, "t_fl": t_fl, "t_pk": t_pk, "run_summary": summary,
           "windows": windows, "detector_windows": pick,
           "detectors": {k: det[f"{m:g}"] for k, m in pick.items() if m is not None},
           "rules": RULES, "surrogates": SURROGATES, "max_individuals": MAX_INDIVIDUALS,
           "detector_seed": DET_SEED, "stop": stop, "timing": timing}
    (d / "hg_run.json").write_text(json.dumps(res, default=float, indent=1), encoding="utf-8")
    return {"name": d.name, "stop": stop, "timing": timing, "wall": time.perf_counter() - t0,
            "peak_n": summary.get("peak_n"), "t_pk": t_pk}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--seeds", type=str, default="9877-9888")
    p.add_argument("--policies", nargs="+", default=list(POLICIES))
    p.add_argument("--arms", nargs="+", default=list(ARMS))
    p.add_argument("--days", type=float, default=DAYS)
    p.add_argument("--out", type=str, default=str(OUT))
    a = p.parse_args()
    lo, _, hi = a.seeds.partition("-")
    seeds = list(range(int(lo), int(hi or lo) + 1))
    if not LEARNED.exists():
        raise SystemExit(f"missing learned weights {LEARNED}")
    if not RANDOM.exists():
        from universe25.agents.policy import MlpFrozenPolicy

        RANDOM.parent.mkdir(parents=True, exist_ok=True)
        MlpFrozenPolicy.random_init(7000).save_npz(str(RANDOM))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(pol, arm, s, str(out), a.days) for s in seeds for pol in a.policies for arm in a.arms]
    t0 = time.perf_counter()
    stops: list[str] = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_job, j): j for j in jobs}
        for f in as_completed(futs):
            r = f.result()
            tm = " ".join(f"{k} {v:.0f}" for k, v in r["timing"].items()) or "kept"
            print(f"{r['name']}: peak {r['peak_n']} at {r['t_pk']:.0f}; {tm}; "
                  f"{r['wall']:.0f} s", flush=True)
            if r["stop"]:
                stops.extend(r["stop"])
                print("STOP: " + "; ".join(r["stop"]), flush=True)
                for g in futs:
                    g.cancel()
                break
    status = "stopped" if stops else "done"
    print(f"sweep {status} in {time.perf_counter() - t0:.0f} s", flush=True)
    return 1 if stops else 0


if __name__ == "__main__":
    raise SystemExit(main())
