#!/usr/bin/env python
"""Calibration reference runs: A/A check of guard v2 and the posterior predictive check
(PHASE4_DESIGN.md 4.1, Tier 1, preregistered 2026-11-09).

Runs the frozen colony (configs/default.yaml, K = 1, 6 ticks/day, NumPy, 1,600 d) on seeds
9000-9047, and again with the removal event (150 adults on day 1014) on seeds 9048-9095.
- A/A: 1,000 random splits of the 48 frozen runs into two arms of 24; the guard v2 verdict on
  each split. Pass (preregistered): "not equivalent" in <= 5 % of splits; the inconclusive rate
  is reported as the rule's cost at n = 24.
- PPC: for every landmark and record value, the median, the 90 % prediction interval and the
  percentile rank of Calhoun's value, without and with the removal event. A record value
  outside the 90 % interval is a miss.

usage: python scripts/calib_reference.py [--workers 6]
Writes _output/calib_reference/rows.json and _output/calib_reference/summary.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "_output" / "calib_reference"
FROZEN = tuple(range(9000, 9048))
REMOVAL = tuple(range(9048, 9096))
DAYS = 1600.0
REMOVAL_EXTRA = {"biology": {"removal_day": 1014.0, "removal_n": 150}}
N_SPLITS = 1000
NE_MAX = 0.05


def run_one(job: tuple[str, int]) -> tuple[str, int, dict]:
    arm, seed = job
    from universe25.calib.fast_eval import evaluate_params
    from universe25.calib.policy_guard import arm_config

    base = arm_config("need_driven", None, None, REMOVAL_EXTRA if arm == "removal" else None)
    res = evaluate_params({}, seed=seed, days=DAYS, ticks_per_day=6, base_config=base)
    return arm, seed, {k: float(v) for k, v in res["observed"].items()}


def main() -> int:
    from universe25.calib.policy_guard import EQ_MARGINS, equivalence
    from universe25.metrics.calibration import EXTRA_LANDMARKS, LANDMARKS, RECORD_LANDMARKS

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows_f = OUT / "rows.json"
    rows: dict[str, dict[str, dict]] = (json.loads(rows_f.read_text(encoding="utf-8"))
                                        if rows_f.exists() else {"frozen": {}, "removal": {}})
    jobs = [(arm, s) for arm, seeds in (("frozen", FROZEN), ("removal", REMOVAL))
            for s in seeds if str(s) not in rows[arm]]
    t0 = time.perf_counter()
    if jobs:
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for arm, seed, obs in ex.map(run_one, jobs):
                rows[arm][str(seed)] = obs
                rows_f.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"{len(jobs)} runs in {time.perf_counter() - t0:.0f} s", flush=True)

    # A/A check of guard v2
    frozen = {int(s): r for s, r in rows["frozen"].items()}
    seeds = np.array(sorted(frozen))
    rng = np.random.default_rng([9000, 4_200_001])
    verdicts: dict[str, int] = {"equivalent": 0, "inconclusive": 0, "not equivalent": 0}
    margins_hit: dict[str, int] = dict.fromkeys(EQ_MARGINS, 0)
    for i in range(N_SPLITS):
        perm = rng.permutation(seeds)
        c = {int(s): frozen[int(s)] for s in perm[:24]}
        t = {int(s): frozen[int(s)] for s in perm[24:]}
        eq = equivalence(c, t, seed=i)
        verdicts[eq["verdict"]] += 1
        for k in EQ_MARGINS:
            if eq["table"][k]["status"] != "inside":
                margins_hit[k] += 1
    ne = verdicts["not equivalent"] / N_SPLITS
    print(f"\nA/A (1,000 splits of 48 frozen runs into 24 + 24): "
          + ", ".join(f"{k} {v / N_SPLITS:.1%}" for k, v in verdicts.items())
          + f" -> {'PASS' if ne <= NE_MAX else 'FAIL'} (not equivalent <= {NE_MAX:.0%})")
    print("share of splits where the landmark's CI is not inside its margin: "
          + ", ".join(f"{k} {v / N_SPLITS:.1%}" for k, v in margins_hit.items()))

    # posterior predictive check
    record = {**LANDMARKS, **EXTRA_LANDMARKS, **RECORD_LANDMARKS}
    ppc: dict[str, dict] = {}
    print("\n| landmark | Calhoun | frozen median [90 % PI] | rank | removal median [90 % PI] "
          "| rank |")
    print("|---|---:|---|---:|---|---:|")
    for k, tgt in record.items():
        line = f"| {k} | {tgt:g} |"
        ppc[k] = {"record": tgt}
        for arm in ("frozen", "removal"):
            v = np.array([r.get(k, np.nan) for r in rows[arm].values()], float)
            v = v[np.isfinite(v)]
            if v.size == 0:
                line += " n/a | |"
                continue
            lo, med, hi = np.quantile(v, [0.05, 0.5, 0.95])
            rank = float(np.mean(v < tgt) + 0.5 * np.mean(v == tgt))
            miss = not (lo <= tgt <= hi)
            ppc[k][arm] = {"median": float(med), "pi90": [float(lo), float(hi)],
                           "rank": rank, "miss": bool(miss), "n": int(v.size)}
            line += f" {med:.1f} [{lo:.1f}, {hi:.1f}]{' **miss**' if miss else ''} | {rank:.2f} |"
        print(line)
    (OUT / "summary.json").write_text(json.dumps(
        {"aa": {"splits": N_SPLITS, "verdicts": verdicts, "not_equivalent_rate": ne,
                "pass": ne <= NE_MAX, "margins_not_inside": margins_hit},
         "ppc": ppc}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
