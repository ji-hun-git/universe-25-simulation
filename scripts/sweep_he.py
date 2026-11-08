#!/usr/bin/env python
"""H-e sweep (PLAN.md section 15.1, amendment adopted 2026-11-08): run, trace and detect.

Arms: policy {learned: mlp_frozen with the nursery-trained pretrain_v2 net; need_driven; a random
frozen net of the same architecture, MlpFrozenPolicy.random_init(7000)} x food {abund:
configs/default.yaml (ABUND-PG), scarce: configs/scarce.yaml (SCARCE-PG, capacity 1,000)} x
evaluation seeds 8000-8011. 12 free-time sub-steps (sub-step mode auto), 1,010 days at the
reference 6 ticks/day; traced windows [400, 410), [700, 710), [1000, 1010) days, every fourth
individual; then the detectors (preregistered with rules v5; the current rule set is read too,
1,000 surrogates, at most 400 individuals per window, seed 0).

Resumable: a run whose run.json and three traces exist is not rerun; a run whose detector file
is present with the current rules is not re-detected (a file of an older rule set is kept as
detectors_<rules>_unvalidated.json). Writes _output/he_sweep/<policy>_<food>_<seed>/.

usage: python scripts/sweep_he.py [--workers 6] [--seeds 8000-8011] [--policies ...] [--foods ...]
then:  python scripts/analyse_he.py
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
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "_output" / "he_sweep"
WINDOWS = [(400.0, 410.0), (700.0, 710.0), (1000.0, 1010.0)]
DAYS = 1010.0
LEARNED = ROOT / "_output" / "pretrain" / "pretrain_v2" / "policy_final.npz"
RANDOM = ROOT / "_output" / "policy_random_v2_7000.npz"
FOODS = {"abund": ROOT / "configs" / "default.yaml", "scarce": ROOT / "configs" / "scarce.yaml"}
POLICIES = ("learned", "need_driven", "random")
SURROGATES, MAX_INDIVIDUALS, DET_SEED = 1000, 400, 0


def policy_over(policy: str) -> dict:
    if policy == "need_driven":
        return {"kind": "need_driven"}
    if policy == "learned":
        return {"kind": "mlp_frozen", "weights": str(LEARNED)}
    if policy == "random":
        return {"kind": "mlp_frozen", "weights": str(RANDOM)}
    raise ValueError(policy)


def run_dir(policy: str, food: str, seed: int) -> Path:
    return OUT / f"{policy}_{food}_{seed}"


def _done(d: Path) -> bool:
    return (d / "run.json").exists() and all(
        (d / f"trace_{a:g}_{b:g}.npz").exists() for a, b in WINDOWS)


def run_one(job: tuple[str, str, int]) -> tuple[str, float, int]:
    policy, food, seed = job
    d = run_dir(policy, food, seed)
    if _done(d):
        return str(d), 0.0, -1
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    over = dict(seed=seed, days=DAYS, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                trace={"windows": WINDOWS, "sample_every": 4}, policy=policy_over(policy))
    t0 = time.perf_counter()
    summ = Universe25Sim(load_config(FOODS[food], over), d).run()
    return str(d), time.perf_counter() - t0, int(summ.get("peak_n", -1))


def detect_one(path: str) -> tuple[str, float]:
    d = Path(path)
    f = d / "detectors_unvalidated.json"
    if f.exists():
        try:
            from universe25.metrics.detectors import RULES

            if json.loads(f.read_text(encoding="utf-8")).get("rules") == RULES:
                return path, 0.0
        except json.JSONDecodeError:
            pass
    from detect import detect_run

    t0 = time.perf_counter()
    detect_run(d, SURROGATES, MAX_INDIVIDUALS, DET_SEED)
    return path, time.perf_counter() - t0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--seeds", type=str, default="8000-8011")
    p.add_argument("--policies", nargs="+", default=list(POLICIES))
    p.add_argument("--foods", nargs="+", default=list(FOODS))
    a = p.parse_args()
    lo, _, hi = a.seeds.partition("-")
    seeds = list(range(int(lo), int(hi or lo) + 1))
    if not LEARNED.exists():
        raise SystemExit(f"missing learned weights {LEARNED}")
    if not RANDOM.exists():
        from universe25.agents.policy import MlpFrozenPolicy

        RANDOM.parent.mkdir(parents=True, exist_ok=True)
        MlpFrozenPolicy.random_init(7000).save_npz(str(RANDOM))
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(pol, food, s) for pol in a.policies for food in a.foods for s in seeds]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for path, wall, peak in ex.map(run_one, jobs):
            tag = "kept" if peak < 0 else f"wall {wall:.0f} s, peak {peak}"
            print(f"run {Path(path).name}: {tag}", flush=True)
    print(f"runs done in {time.perf_counter() - t0:.0f} s", flush=True)
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for path, wall in ex.map(detect_one, [str(run_dir(*j)) for j in jobs]):
            print(f"detected {Path(path).name} ({wall:.0f} s)", flush=True)
    print(f"sweep done in {time.perf_counter() - t0:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
