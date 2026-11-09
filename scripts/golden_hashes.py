#!/usr/bin/env python
"""Golden trajectory hashes (src/universe25/golden.py): check or update the table.

usage: python scripts/golden_hashes.py [--tier fast|slow|all] [--update] [--workers 4]
Check mode exits 1 on any mismatch. --update rewrites tests/golden/trajectories.json for the
chosen tiers on this platform and NumPy version; record the reason in NOTES.md when you do.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _run(job: tuple[str, float]) -> tuple[str, dict]:
    from universe25.golden import run_arm

    name, days = job
    return name, run_arm(name, days)


def main() -> int:
    from universe25.golden import (
        ARMS,
        FAST_DAYS,
        SLOW_DAYS,
        TABLE,
        environment,
        load_table,
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tier", choices=("fast", "slow", "all"), default="fast")
    p.add_argument("--update", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    tiers = ("fast", "slow") if a.tier == "all" else (a.tier,)
    table = load_table()
    rc = 0
    for tier in tiers:
        days = FAST_DAYS if tier == "fast" else SLOW_DAYS
        t0 = time.perf_counter()
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            got = dict(ex.map(_run, [(n, days) for n in ARMS]))
        print(f"{tier}: {len(got)} arms, {days:g} days, {time.perf_counter() - t0:.0f} s")
        if got["k12_traced"]["trajectory"] != got["k12_continue"]["trajectory"]:
            print("  FAIL: the trace recorder perturbed the trajectory")
            rc = 1
        if a.update:
            table[tier] = {"environment": environment(), "days": days, "arms": got}
            for n, r in got.items():
                print(f"  {n:18s} {r['trajectory'][:16]} N {r['n_alive']}")
            continue
        entry = table.get(tier)
        if not entry or entry.get("environment") != environment():
            print(f"  skip: table environment {entry and entry.get('environment')} != "
                  f"{environment()}")
            continue
        for n, r in got.items():
            ok = entry["arms"].get(n) == r
            rc |= int(not ok)
            print(f"  {n:18s} {'ok' if ok else 'MISMATCH'} {r['trajectory'][:16]}")
    if a.update:
        TABLE.parent.mkdir(parents=True, exist_ok=True)
        TABLE.write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
        print(f"written {TABLE}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
