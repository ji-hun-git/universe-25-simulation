#!/usr/bin/env python
"""Relief matching for novelty-based curiosity (PHASE4_DESIGN.md 1.10, card P4-14).

The heuristic (need_driven, K = 12, sub-step mode continue) on training seeds 7000-7002,
configs/default.yaml, 6 ticks/day, 700 days. Statistic: adult (age >= maturity) mean curiosity,
sampled once a day over days 100-700, averaged per seed; boredom is reported beside it.
- target: the frozen substrate (ball physics and novelty off);
- scan: ball physics and novelty on, consequence gain g in {1, 2, 3, 4, 6, 8}.
Preregistered rule (fixed before this script first ran): choose the g whose seed-mean curiosity
is closest to the target; if none is within 10 % of the target, report that and stop.

usage: python scripts/scan_novelty_gain.py [--workers 6]
Writes _output/novelty_gain_scan/summary.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "_output" / "novelty_gain_scan"
SEEDS = (7000, 7001, 7002)
GAINS = (1.0, 2.0, 3.0, 4.0, 6.0, 8.0)
DAYS = 700
FIRST_DAY = 100
TOL = 0.10


def run_one(job: tuple[str, float, int]) -> dict:
    arm, g, seed = job
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    on = arm == "scan"
    over = dict(seed=seed, days=float(DAYS), ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=10**9, snapshot_every_days=0, free_substeps=12,
                playground={"ball_physics": on},
                drives={"curiosity_novelty": on, "consequence_gain": g},
                policy={"kind": "need_driven"})
    t0 = time.perf_counter()
    sim = Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over),
                        Path(tempfile.mkdtemp(prefix="u25scan_")))
    mat = float(sim.cfg.biology.maturity_days)
    cur, bor, n = [], [], []
    for d in range(DAYS):
        for _ in range(6):
            sim.step()
        if d + 1 >= FIRST_DAY:
            a = sim.agents
            ad = a.alive & (a.age_days >= mat)
            if ad.any():
                cur.append(float(a.curiosity[ad].mean()))
                bor.append(float(a.boredom[ad].mean()))
            n.append(int(a.alive.sum()))
    return {"arm": arm, "g": g, "seed": seed, "curiosity": float(np.mean(cur)),
            "boredom": float(np.mean(bor)), "n_at_315": n[315 - FIRST_DAY],
            "n_at_700": n[-1], "wall_s": time.perf_counter() - t0}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [("target", 1.0, s) for s in SEEDS] + [("scan", g, s) for g in GAINS for s in SEEDS]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(run_one, jobs))
    tgt = [r for r in rows if r["arm"] == "target"]
    T = float(np.mean([r["curiosity"] for r in tgt]))
    Tb = float(np.mean([r["boredom"] for r in tgt]))
    print(f"target (frozen substrate): adult curiosity {T:.3f}, boredom {Tb:.3f}, "
          f"N@315 {np.mean([r['n_at_315'] for r in tgt]):.0f}, "
          f"N@700 {np.mean([r['n_at_700'] for r in tgt]):.0f}")
    print("| g | adult curiosity | rel. diff | boredom | N@315 | N@700 |")
    print("|---:|---:|---:|---:|---:|---:|")
    table = []
    for g in GAINS:
        rg = [r for r in rows if r["arm"] == "scan" and r["g"] == g]
        c = float(np.mean([r["curiosity"] for r in rg]))
        b = float(np.mean([r["boredom"] for r in rg]))
        table.append({"g": g, "curiosity": c, "rel_diff": (c - T) / T, "boredom": b,
                      "n_at_315": float(np.mean([r["n_at_315"] for r in rg])),
                      "n_at_700": float(np.mean([r["n_at_700"] for r in rg]))})
        t = table[-1]
        print(f"| {g:g} | {c:.3f} | {t['rel_diff']:+.1%} | {b:.3f} | {t['n_at_315']:.0f} | "
              f"{t['n_at_700']:.0f} |")
    best = min(table, key=lambda t: abs(t["rel_diff"]))
    ok = abs(best["rel_diff"]) <= TOL
    print(f"\nchosen g = {best['g']:g} (rel. diff {best['rel_diff']:+.1%}); "
          f"within {TOL:.0%}: {'yes' if ok else 'NO - stop'}")
    (OUT / "summary.json").write_text(json.dumps(
        {"target": {"curiosity": T, "boredom": Tb}, "table": table, "chosen_g": best["g"],
         "within_tolerance": ok, "rows": rows}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
