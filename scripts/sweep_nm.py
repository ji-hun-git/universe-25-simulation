#!/usr/bin/env python
"""The norm-matched check of criterion 3 and H-i (PHASE4_DESIGN.md 4.5, fixed 2026-11-13 before
any code or run).

Colony c = 1 ... 24 runs on seed 9904 + c. Its lineage is l = ((c - 1) mod 8) + 1, its base
genome b_c is genome (c - 1) div 8 of lineage l's generation-0 pool, and its jump eps_c is one
standard normal per value from SeedSequence([9904 + c, 7_600_001]). At size lambda the genome is
b_c + lambda * 0.02 * sqrt(G_l) * eps_c, with G_l the generations of lineage l's neutral pool:
S0 (lambda 0, generation 0), S05 (lambda 1/2) and S1 (lambda 1, the neutral drift's size). All 8
founders of a colony carry the one genome; pups copy a parent with N(0, 0.02^2) as in H-h.
Evaluation is H-h's pipeline unchanged (scripts/sweep_evo.py): Calhoun's 4 pairs, 1,600 d, 12
sub-steps, 29 ten-day trace windows (every fourth individual), episode rates in every window, and
the rules-v9 detector vector (1,000 surrogates, at most 400 individuals, detector seed 0) on the
four windows of section 4.3. Each run also counts the trace rows by action. Resumable at each
stage; stops on a NaN. Writes _output/nm_sweep/pools/ and <arm>_c<cc>_<seed>/nm_run.json.

usage: python scripts/sweep_nm.py [--workers 8] [--colonies 1-24] [--arms S0 S05 S1]
       python scripts/sweep_nm.py --dev --colonies 1 --days 300 --out _output/nm_dev
--dev runs every colony on the training seed 7000 (its jump drawn with seed 7000 too); it is the
harness smoke, for timing only, and no statistic of it is read.
then:  python scripts/analyse_nm.py
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

OUT = ROOT / "_output" / "nm_sweep"
EVO = ROOT / "_output" / "evo"
DAYS = 1600.0
SEED0 = 9904  # colony c on seed 9904 + c
COLONIES = 24
LINEAGES = 8
FOUNDERS = 8
DEV_SEED = 7000
LAMBDAS = {"S0": 0.0, "S05": 0.5, "S1": 1.0}


def colony_seed(colony: int, dev: bool = False) -> int:
    return DEV_SEED if dev else SEED0 + int(colony)


def colony_lineage(colony: int) -> int:
    return (int(colony) - 1) % LINEAGES + 1


def colony_base_index(colony: int) -> int:
    return (int(colony) - 1) // LINEAGES


def pool_path(pools: Path, colony: int, arm: str) -> Path:
    return pools / f"c{int(colony):02d}_{arm}.npz"


def build_pools(evo: Path, pools: Path, colonies: list[int], dev: bool) -> dict:
    """One pool per colony and arm: 8 copies of the colony's genome at that size."""
    from universe25.agents.evo import (JUMP_STREAM, N_PARAM, SEX_ANY, genome_norms,
                                       jump_genome, load_pool, save_pool, stream)
    from universe25.learn.evolution import MUTATION_SD

    pools.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for c in colonies:
        lin, k, seed = colony_lineage(c), colony_base_index(c), colony_seed(c, dev)
        d = evo / f"lineage_{lin}"
        g_l = int(json.loads((d / "summary.json").read_text(encoding="utf-8"))
                  ["neutral_generations"])
        base = load_pool(d / "pool_gen0.npz")["genomes"][k]
        eps = stream(seed, JUMP_STREAM).standard_normal(N_PARAM)
        neu = genome_norms(load_pool(d / "pool_neu.npz")["genomes"])
        for arm, lam in LAMBDAS.items():
            g = jump_genome(base, eps, g_l, MUTATION_SD, lam)
            save_pool(pool_path(pools, c, arm), np.repeat(g[None, :], FOUNDERS, axis=0),
                      np.zeros(FOUNDERS, np.int64), np.full(FOUNDERS, SEX_ANY, np.int64),
                      colony=c, lineage=lin, base_index=k, generations=g_l, lam=lam, seed=seed)
            manifest[f"c{c:02d}_{arm}"] = {
                "colony": c, "arm": arm, "lam": lam, "lineage": lin, "base_index": k,
                "generations": g_l, "seed": seed, "mutation_sd": MUTATION_SD,
                "norms": genome_norms(g[None, :]), "neutral_norms": neu}
    (pools / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def _action_counts(d: Path, wins: list[tuple[float, float]]) -> list[int]:
    from universe25.agents.state import N_ACTIONS

    counts = np.zeros(N_ACTIONS, np.int64)
    for a, b in wins:
        with np.load(_trace_path(d, a, b), allow_pickle=False) as z:
            act = z["action"].astype(np.int64)
        counts += np.bincount(act[(act >= 0) & (act < N_ACTIONS)], minlength=N_ACTIONS)
    return counts.tolist()


def run_nm(job: tuple[str, int, int, str, str, float]) -> dict:
    """One run: simulate, then rates, action counts and detector vectors; each stage is skipped
    when its output exists (the stages of sweep_evo.run_evo)."""
    arm, colony, seed, pool, out, days = job
    from universe25.config import load_config
    from universe25.metrics.calibration import calibrate
    from universe25.metrics.detectors import RULES, detect_trace
    from universe25.metrics.phase_rates import detector_windows, label_windows, window_rates
    from universe25.metrics.trace import load_trace
    from universe25.sim import Universe25Sim

    d = Path(out) / f"{arm}_c{colony:02d}_{seed}"
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

    act_f = d / "nm_actions.json"
    if act_f.exists():
        counts = json.loads(act_f.read_text(encoding="utf-8"))["counts"]
    else:
        counts = _action_counts(d, wins)
        act_f.write_text(json.dumps({"counts": counts}), encoding="utf-8")

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
    with np.load(pool, allow_pickle=False) as z:
        meta = {k: z[k].item() for k in ("colony", "lineage", "base_index", "generations",
                                          "lam", "seed") if k in z.files}
    res = {"arm": arm, "colony": colony, "seed": seed, "days": days, "pool": str(pool),
           "pool_meta": meta, "landmarks": obs, "t_fl": t_fl, "t_pk": t_pk,
           "run_summary": summary,
           "policy": json.loads(pol_f.read_text(encoding="utf-8")) if pol_f.exists() else None,
           "windows": windows, "detector_windows": pick,
           "detectors": {k: det[f"{m:g}"] for k, m in pick.items() if m is not None},
           "rules": RULES, "surrogates": SURROGATES, "max_individuals": MAX_INDIVIDUALS,
           "detector_seed": DET_SEED, "action_counts": counts, "stop": stop, "timing": timing}
    (d / "nm_run.json").write_text(json.dumps(res, default=float, indent=1), encoding="utf-8")
    return {"name": d.name, "stop": stop, "timing": timing, "wall": time.perf_counter() - t0,
            "peak_n": summary.get("peak_n"), "t_pk": t_pk}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--colonies", type=str, default=f"1-{COLONIES}")
    p.add_argument("--arms", nargs="+", default=list(LAMBDAS))
    p.add_argument("--evo", type=str, default=str(EVO))
    p.add_argument("--out", type=str, default=str(OUT))
    p.add_argument("--days", type=float, default=DAYS)
    p.add_argument("--dev", action="store_true")
    a = p.parse_args()
    lo, _, hi = a.colonies.partition("-")
    colonies = list(range(int(lo), int(hi or lo) + 1))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    build_pools(Path(a.evo), out / "pools", colonies, a.dev)
    jobs = [(arm, c, colony_seed(c, a.dev), str(pool_path(out / "pools", c, arm)), str(out),
             a.days) for c in colonies for arm in a.arms]
    t0 = time.perf_counter()
    stops: list[str] = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_nm, j): j for j in jobs}
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
