"""Optuna + CMA-ES calibration to Calhoun 1973 landmarks."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import optuna
from optuna.samplers import CmaEsSampler

from universe25.calib.fast_eval import evaluate_params
from universe25.calib.priors import LANDMARKS, PARAM_PRIORS, suggest_params


def run_study(
    *,
    out_dir: Path,
    n_trials: int = 40,
    seed: int = 7000,
    heldout_seeds: list[int] | None = None,
    days: float = 700.0,
    ticks_per_day: int = 6,
    n_jobs: int = 1,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    heldout_seeds = heldout_seeds or [8000, 8001, 8002]
    sampler = CmaEsSampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler, study_name="u25_calhoun")

    t0 = time.perf_counter()

    def objective(trial: optuna.Trial) -> float:
        params = suggest_params(trial)
        # early cheap probe: if first litters wildly late, still run full (CMA needs smooth)
        result = evaluate_params(
            params, seed=seed, days=days, ticks_per_day=ticks_per_day
        )
        trial.set_user_attr("observed", result["observed"])
        return float(result["loss"])

    study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs, show_progress_bar=False)
    wall = time.perf_counter() - t0

    best_params = dict(study.best_params)
    train_eval = evaluate_params(best_params, seed=seed, days=days, ticks_per_day=ticks_per_day)
    heldout = []
    for hs in heldout_seeds:
        heldout.append(evaluate_params(best_params, seed=hs, days=days, ticks_per_day=ticks_per_day))

    report = {
        "method": "optuna.CmaEsSampler",
        "n_trials": n_trials,
        "train_seed": seed,
        "heldout_seeds": heldout_seeds,
        "days": days,
        "ticks_per_day": ticks_per_day,
        "wall_seconds": wall,
        "best_loss_train_optuna": study.best_value,
        "best_params": best_params,
        "priors": {k: {kk: vv for kk, vv in v.items() if kk != "group"} for k, v in PARAM_PRIORS.items()},
        "landmarks_target": LANDMARKS,
        "train_eval": train_eval,
        "heldout_evals": heldout,
        "heldout_mean_loss": float(sum(h["loss"] for h in heldout) / max(1, len(heldout))),
        "note": "Collapse must emerge from density/social params; no collapse_day in search space.",
    }
    (out_dir / "calibration_study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # write best yaml fragment
    bio = {k: v for k, v in best_params.items() if PARAM_PRIORS[k]["group"] == "biology"}
    drv = {k: v for k, v in best_params.items() if PARAM_PRIORS[k]["group"] == "drives"}
    best_cfg = {"biology": bio, "drives": drv}
    import yaml

    (out_dir / "best_params.yaml").write_text(yaml.safe_dump(best_cfg, sort_keys=False), encoding="utf-8")
    return report

