#!/usr/bin/env python
"""Simulator negative control for detector rules v6 (PHASE4_DESIGN.md section 2, card P4-11).

Random-init networks of the learned net's architecture (MlpFrozenPolicy.random_init, init seeds
7001 and 7002, never used before) on training seeds 7003-7005 (never traced before), ABUND-PG
(configs/default.yaml), 12 free-time sub-steps (sub-step mode auto), 1,010 days at 6 ticks/day,
traced windows [400, 410), [700, 710), [1000, 1010) days, every fourth individual; detectors with
1,000 surrogates, at most 400 individuals per window, detector seed 0.

Preregistered pass (fixed before this script first ran): criterion 3 and criterion 4 flags
(rules v6) each met in <= 10 % of the 18 windows per episode kind. Diagnostic, not a pass
condition: the v5 flags on the same windows.

usage: python scripts/negcontrol_v6.py [--workers 6]
Writes _output/negcontrol_v6/<init>_<seed>/ and _output/negcontrol_v6/summary.json.
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
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "_output" / "negcontrol_v6"
WINDOWS = [(400.0, 410.0), (700.0, 710.0), (1000.0, 1010.0)]
INITS = (7001, 7002)
SEEDS = (7003, 7004, 7005)
FPR_MAX = 0.10
FLAGS = ("c3_structurally_different", "c4_repeated_not_rigid")


def weights(init: int) -> Path:
    return OUT / f"policy_random_init{init}.npz"


def run_one(job: tuple[int, int]) -> tuple[str, float]:
    init, seed = job
    d = OUT / f"init{init}_{seed}"
    if (d / "run.json").exists() and all((d / f"trace_{a:g}_{b:g}.npz").exists()
                                         for a, b in WINDOWS):
        return str(d), 0.0
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    over = dict(seed=seed, days=1010.0, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                trace={"windows": WINDOWS, "sample_every": 4},
                policy={"kind": "mlp_frozen", "weights": str(weights(init))})
    t0 = time.perf_counter()
    Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over), d).run()
    return str(d), time.perf_counter() - t0


def detect_one(path: str) -> tuple[str, float]:
    from detect import detect_run
    from universe25.metrics.detectors import RULES

    d = Path(path)
    f = d / "detectors_unvalidated.json"
    if f.exists() and json.loads(f.read_text(encoding="utf-8")).get("rules") == RULES:
        return path, 0.0
    t0 = time.perf_counter()
    detect_run(d, 1000, 400, 0)
    return path, time.perf_counter() - t0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    from universe25.agents.policy import MlpFrozenPolicy

    OUT.mkdir(parents=True, exist_ok=True)
    for init in INITS:
        if not weights(init).exists():
            MlpFrozenPolicy.random_init(init).save_npz(str(weights(init)))
    jobs = [(i, s) for i in INITS for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        paths = [path for path, _ in ex.map(run_one, jobs)]
        print(f"runs done in {time.perf_counter() - t0:.0f} s", flush=True)
        for path, wall in ex.map(detect_one, paths):
            print(f"detected {Path(path).name} ({wall:.0f} s)", flush=True)
    rows = []
    for path in paths:
        det = json.loads((Path(path) / "detectors_unvalidated.json").read_text(encoding="utf-8"))
        for w, res in det["windows"].items():
            for kind in ("object", "locomotor"):
                r = res[kind]
                rows.append({"run": Path(path).name, "window": w, "kind": kind,
                             "n_episodes": r["n_episodes"],
                             "form_excess": r.get("seq_struct_form_excess_unvalidated"),
                             "form_z": r.get("seq_struct_form_z_unvalidated"),
                             "v6": r["decisions_unvalidated"],
                             "v5": r["decisions_v5_unvalidated"]})
    summary: dict = {"rules": det["rules"], "fpr_max": FPR_MAX, "kinds": {}, "windows": rows}
    ok_all = True
    print("\n| kind | windows | c1..c5 rates, v5 | c1..c5 rates, v6 | c3 / c4 (v6) | pass |")
    print("|---|---:|---|---|---|---|")
    for kind in ("object", "locomotor"):
        kr = [r for r in rows if r["kind"] == kind]
        names = list(kr[0]["v6"])
        v5 = [float(np.mean([r["v5"][f] for r in kr])) for f in names]
        v6 = [float(np.mean([r["v6"][f] for r in kr])) for f in names]
        rate = {f: float(np.mean([r["v6"][f] for r in kr])) for f in FLAGS}
        ok = all(v <= FPR_MAX for v in rate.values())
        ok_all &= ok
        summary["kinds"][kind] = {"n_windows": len(kr), "v5_rates": dict(zip(names, v5)),
                                  "v6_rates": dict(zip(names, v6)), "pass": ok}
        print(f"| {kind} | {len(kr)} | " + " ".join(f"{v:.2f}" for v in v5) + " | "
              + " ".join(f"{v:.2f}" for v in v6) + f" | {rate[FLAGS[0]]:.2f} / "
              f"{rate[FLAGS[1]]:.2f} | {'PASS' if ok else 'FAIL'} |")
    summary["all_pass"] = bool(ok_all)
    print(f"\nnegative control: {'PASS' if ok_all else 'FAIL'}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                      encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
