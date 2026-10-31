#!/usr/bin/env python
"""Calibrate biology with Optuna CMA-ES. Example (16-core lab PC):
  python scripts/calibrate_optuna.py --seed 7000 --trials 112 --popsize 14 --workers 14 \
      --days 1200 --x0 configs/calibrated_calhoun.yaml --out _output/calib_cma_p3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.calib.optimize import load_x0, run_study  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=7000)
    p.add_argument("--trials", type=int, default=40)
    p.add_argument("--days", type=float, default=1200.0)
    p.add_argument("--ticks-per-day", type=int, default=6)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--heldout", type=str, default="8000,8001,8002")
    p.add_argument("--workers", type=int, default=1, help="process pool size (ask/tell batches)")
    p.add_argument("--popsize", type=int, default=None, help="CMA-ES population (= batch size)")
    p.add_argument("--x0", type=str, default=None, help="YAML biology/drives fragment as CMA start")
    p.add_argument("--sigma0", type=float, default=None)
    p.add_argument("--train-seeds", type=str, default=None,
                   help="comma-separated seeds; objective = mean loss over them (default: --seed)")
    args = p.parse_args()
    heldout = [int(x) for x in args.heldout.split(",") if x.strip()]
    train_seeds = (
        [int(x) for x in args.train_seeds.split(",") if x.strip()] if args.train_seeds else None
    )
    x0 = load_x0(Path(args.x0)) if args.x0 else None
    report = run_study(
        out_dir=Path(args.out),
        n_trials=args.trials,
        seed=args.seed,
        heldout_seeds=heldout,
        days=args.days,
        ticks_per_day=args.ticks_per_day,
        n_workers=args.workers,
        popsize=args.popsize,
        x0=x0,
        sigma0=args.sigma0,
        train_seeds=train_seeds,
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
