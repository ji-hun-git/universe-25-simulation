"""Runner for __main__ tests (shared venv has no pytest).

usage: python tests/run_tests.py [--tier fast|slow|gpu|all]   (default all)
  fast  everything except the slow and GPU files below (the CI tier)
  slow  long simulations and learner tests
  gpu   Warp / CUDA smoke tests (print "skip" without a GPU)
Prints each file's wall time.
"""
from __future__ import annotations

import argparse
import runpy
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SLOW = {"test_policy_calibration_guard.py", "test_actions_v2.py", "test_learn.py",
        "test_golden.py", "test_nursery.py", "test_detectors.py"}
GPU = {"test_warp_smoke.py"}


def tier_of(name: str) -> str:
    return "gpu" if name in GPU else "slow" if name in SLOW else "fast"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tier", choices=("fast", "slow", "gpu", "all"), default="all")
    a = p.parse_args()
    failed = 0
    t_all = time.perf_counter()
    for path in sorted(HERE.glob("test_*.py")):
        if a.tier != "all" and tier_of(path.name) != a.tier:
            continue
        print(f"--- {path.name} [{tier_of(path.name)}]")
        t0 = time.perf_counter()
        try:
            runpy.run_path(str(path), run_name="__main__")
        except Exception as e:
            failed += 1
            print(f"FAIL {path.name}: {type(e).__name__}: {e}")
        print(f"    {time.perf_counter() - t0:.1f} s")
    print(f"done failed={failed} ({time.perf_counter() - t_all:.0f} s, tier {a.tier})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
