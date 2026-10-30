#!/usr/bin/env python
"""Calibrate biology with Optuna CMA-ES. Example:
  python scripts/calibrate_optuna.py --seed 7000 --trials 40 --out _output/calib_cma
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.calib.optimize import run_study


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=7000)
    p.add_argument("--trials", type=int, default=40)
    p.add_argument("--days", type=float, default=1600.0)
    p.add_argument("--ticks-per-day", type=int, default=6)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--heldout", type=str, default="8000,8001,8002")
    args = p.parse_args()
    heldout = [int(x) for x in args.heldout.split(",") if x.strip()]
    report = run_study(
        out_dir=Path(args.out),
        n_trials=args.trials,
        seed=args.seed,
        heldout_seeds=heldout,
        days=args.days,
        ticks_per_day=args.ticks_per_day,
    )
    print(json.dumps({
        "best_loss": report["train_eval"]["loss"],
        "heldout_mean_loss": report["heldout_mean_loss"],
        "train_observed": report["train_eval"]["observed"],
        "wall_seconds": report["wall_seconds"],
        "best_params": report["best_params"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
