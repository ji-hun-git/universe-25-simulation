#!/usr/bin/env python
"""Out-of-sample scoring of a parameter fragment over many seeds (the adjudicator for CMA-ES
candidates since phase 2k): every landmark's mean +- se, the inverse-variance loss of the mean
landmarks, the mean of the per-seed losses and the canonical error of the means.

usage: python scripts/seed_eval.py <fragment.yaml|-> <label> [n_seeds=12] [workers=12]
       [first_seed=7000] [days=1200]
'-' scores configs/default.yaml as is; a fragment ({biology: {...}, drives: {...}}) is merged
over it. Writes _output/seed_eval_<label>.json. NumPy CPU path, 6 ticks/day.
"""
from __future__ import annotations

import json
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
KEYS = ("first_litters_day", "n_at_day_315", "adults_at_day_315", "peak_n", "peak_day",
        "peak_day_97pct", "last_young_day", "n_at_day_736", "last_conception_day",
        "n_at_day_1200", "n_at_day_1444", "n_at_day_1588", "final_n")


def _run(args: tuple[int, str, float]) -> tuple[int, float, dict[str, float]]:
    seed, base, days = args
    from universe25.calib.fast_eval import evaluate_params

    res = evaluate_params({}, seed=seed, days=days, ticks_per_day=6, base_config=Path(base))
    return seed, float(res["loss"]), res["observed"]


def main() -> int:
    import numpy as np

    from universe25.calib.priors import landmark_loss
    from universe25.metrics.calibration import EXTRA_LANDMARKS, LANDMARKS

    frag_path, label = sys.argv[1], sys.argv[2]
    n_seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    first = int(sys.argv[5]) if len(sys.argv) > 5 else 7000
    days = float(sys.argv[6]) if len(sys.argv) > 6 else 1200.0
    base = yaml.safe_load((ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))
    if frag_path != "-":
        frag = yaml.safe_load(Path(frag_path).read_text(encoding="utf-8")) or {}
        for g in ("biology", "drives"):
            base.setdefault(g, {}).update(frag.get(g) or {})
    tmp = Path(tempfile.mkdtemp(prefix="u25se_")) / "base.yaml"
    tmp.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")
    seeds = [first + i for i in range(n_seeds)]
    rows: dict[int, dict[str, float]] = {}
    losses: dict[int, float] = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for seed, loss, obs in ex.map(_run, [(s, str(tmp), days) for s in seeds]):
            rows[seed], losses[seed] = obs, loss
            print(f"seed={seed} loss={loss:.4f} "
                  + " ".join(f"{k}={obs[k]:.0f}" for k in KEYS if k in obs), flush=True)
    targets = {**LANDMARKS, **EXTRA_LANDMARKS}
    mean_obs = {k: float(np.mean([rows[s][k] for s in seeds])) for k in KEYS if k in rows[seeds[0]]}
    mean_obs["final_day"] = days
    print(f"\n== {label}: {n_seeds} seeds {seeds[0]}-{seeds[-1]}, {days:.0f} d, 6 ticks/day")
    print(f"{'landmark':22s} {'target':>7s} {'mean':>8s} {'se':>6s} {'rel err':>8s}")
    for k in mean_obs:
        if k == "final_day":
            continue
        v = np.array([rows[s][k] for s in seeds], float)
        t = targets.get(k)
        rel = f"{abs(v.mean() - t) / t:8.3f}" if t else "        "
        se = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
        print(f"{k:22s} {t if t else 0:7.0f} {v.mean():8.1f} {se:6.1f} {rel}")
    mre5 = float(np.mean([abs(mean_obs[k] - t) / t for k, t in LANDMARKS.items()]))
    print(f"loss of the mean landmarks: {landmark_loss(mean_obs):.4f}   mean per-seed loss: "
          f"{np.mean(list(losses.values())):.4f}   canonical error of the means: {mre5:.3f}")
    out = ROOT / "_output" / f"seed_eval_{label}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "losses": losses, "mean": mean_obs}, indent=1),
                   encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
