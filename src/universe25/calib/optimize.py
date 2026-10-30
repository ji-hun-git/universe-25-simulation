"""Optuna + CMA-ES calibration to Calhoun 1973 landmarks (serial or process-parallel)."""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import optuna
import yaml
from optuna.samplers import CmaEsSampler

from universe25.calib.fast_eval import evaluate_params
from universe25.calib.priors import (
    EXTRA_LANDMARKS,
    LANDMARKS,
    PARAM_PRIORS,
    overrides_to_params,
    suggest_params,
)


def _trial_record(
    trial: optuna.trial.FrozenTrial | optuna.Trial, loss: float, result: dict[str, Any]
) -> dict[str, Any]:
    return {
        "number": trial.number,
        "loss": float(loss),
        "observed": result["observed"],
        "params": result["params"],
    }


def _write_report(out_dir: Path, report: dict[str, Any]) -> None:
    (out_dir / "calibration_study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    bp = report.get("best_params") or {}
    bio = {k: v for k, v in bp.items() if PARAM_PRIORS[k]["group"] == "biology"}
    drv = {k: v for k, v in bp.items() if PARAM_PRIORS[k]["group"] == "drives"}
    (out_dir / "best_params.yaml").write_text(
        yaml.safe_dump({"biology": bio, "drives": drv}, sort_keys=False), encoding="utf-8"
    )


def run_study(
    *,
    out_dir: Path,
    n_trials: int = 40,
    seed: int = 7000,
    heldout_seeds: list[int] | None = None,
    days: float = 1200.0,
    ticks_per_day: int = 6,
    n_jobs: int = 1,
    n_workers: int = 1,
    popsize: int | None = None,
    x0: dict[str, float] | None = None,
    sigma0: float | None = None,
) -> dict[str, Any]:
    """CMA-ES over PARAM_PRIORS.

    n_workers > 1 evaluates each CMA generation (popsize candidates) in a process pool via
    Optuna's ask/tell interface; evaluation is the NumPy CPU path so results are
    deterministic per (seed, params) regardless of scheduling.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    heldout_seeds = heldout_seeds or [8000, 8001, 8002]
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = CmaEsSampler(seed=seed, popsize=popsize, x0=x0, sigma0=sigma0)
    study = optuna.create_study(direction="minimize", sampler=sampler, study_name="u25_calhoun")
    eval_kw = dict(seed=seed, days=days, ticks_per_day=ticks_per_day)
    trials_log: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    if n_workers <= 1:

        def objective(trial: optuna.Trial) -> float:
            params = suggest_params(trial)
            result = evaluate_params(params, **eval_kw)
            trial.set_user_attr("observed", result["observed"])
            trials_log.append(_trial_record(trial, result["loss"], result))
            return float(result["loss"])

        study.optimize(objective, n_trials=n_trials, n_jobs=n_jobs, show_progress_bar=False)
    else:
        batch = popsize or n_workers
        done = 0
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            while done < n_trials:
                k = min(batch, n_trials - done)
                trials = [study.ask() for _ in range(k)]
                params_list = [suggest_params(t) for t in trials]
                futs = [ex.submit(evaluate_params, p, **eval_kw) for p in params_list]
                for t, f in zip(trials, futs):
                    res = f.result()
                    t.set_user_attr("observed", res["observed"])
                    study.tell(t, float(res["loss"]))
                    trials_log.append(_trial_record(t, res["loss"], res))
                done += k
                best = study.best_trial
                print(
                    f"[calib] trials={done}/{n_trials} best_loss={best.value:.4f} "
                    f"(trial {best.number}) obs={_fmt_obs(best.user_attrs.get('observed', {}))} "
                    f"wall={time.perf_counter() - t0:.0f}s",
                    flush=True,
                )
                _write_report(
                    out_dir,
                    {
                        "status": "running",
                        "trials_done": done,
                        "best_loss_train_optuna": best.value,
                        "best_params": dict(best.params),
                        "trials": trials_log,
                    },
                )
    wall = time.perf_counter() - t0

    best_params = dict(study.best_params)
    train_eval = evaluate_params(best_params, **eval_kw)
    heldout = []
    if heldout_seeds:
        if n_workers > 1:
            with ProcessPoolExecutor(max_workers=min(n_workers, len(heldout_seeds))) as ex:
                futs = [
                    ex.submit(evaluate_params, best_params, seed=hs, days=days,
                              ticks_per_day=ticks_per_day)
                    for hs in heldout_seeds
                ]
                heldout = [f.result() for f in futs]
        else:
            for hs in heldout_seeds:
                heldout.append(
                    evaluate_params(best_params, seed=hs, days=days, ticks_per_day=ticks_per_day)
                )

    report = {
        "status": "done",
        "method": "optuna.CmaEsSampler" + (" (ask/tell, process pool)" if n_workers > 1 else ""),
        "n_trials": n_trials,
        "n_workers": n_workers,
        "popsize": popsize,
        "x0": x0,
        "train_seed": seed,
        "heldout_seeds": heldout_seeds,
        "days": days,
        "ticks_per_day": ticks_per_day,
        "wall_seconds": wall,
        "best_loss_train_optuna": study.best_value,
        "best_params": best_params,
        "priors": {
            k: {kk: vv for kk, vv in v.items() if kk != "group"} for k, v in PARAM_PRIORS.items()
        },
        "landmarks_target": LANDMARKS,
        "extra_landmarks_target": EXTRA_LANDMARKS,
        "train_eval": train_eval,
        "heldout_evals": heldout,
        "heldout_mean_loss": float(sum(h["loss"] for h in heldout) / max(1, len(heldout))),
        "trials": trials_log,
        "note": (
            "Collapse must emerge from density/social/developmental params; "
            "no collapse_day in search space."
        ),
    }
    _write_report(out_dir, report)
    return report


def load_x0(path: Path) -> dict[str, float]:
    """Read a biology/drives YAML fragment into a CMA-ES starting point (searched keys only)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    x0 = overrides_to_params(data)
    for k, spec in PARAM_PRIORS.items():
        if k in x0:
            x0[k] = float(min(max(x0[k], spec["low"]), spec["high"]))
    return x0


def _fmt_obs(obs: dict[str, Any]) -> str:
    keys = [
        "first_litters_day", "n_at_day_315", "peak_n", "peak_day", "last_young_day",
        "n_at_day_736", "final_n",
    ]
    parts = []
    for k in keys:
        v = obs.get(k)
        if v is None or v != v:
            parts.append(f"{k}=nan")
        else:
            parts.append(f"{k}={v:.0f}")
    return " ".join(parts)


if __name__ == "__main__":  # pragma: no cover
    print("use scripts/calibrate_optuna.py", file=sys.stderr)
