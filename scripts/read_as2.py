#!/usr/bin/env python
"""Development reading for action space v2 (PHASE4_DESIGN.md 1.8, acceptance check 3).

The nursery-trained v3 learner (`_output/pretrain/pretrain_v3/policy_final.npz`) and a random v3
network (`MlpFrozenPolicy.random_init(7000)`) on training seeds 7000-7002, ABUND-PG
(configs/default.yaml), 12 free-time sub-steps (sub-step mode auto: rechoose), 1,010 days at
6 ticks/day, traced windows [400, 410), [700, 710), [1000, 1010) days, every fourth individual;
detectors (rules v6) with 1,000 surrogates, at most 400 individuals per window, detector seed 0.
No pass condition: it reports the flag rates, the form test and the action-family shares.

usage: python scripts/read_as2.py [--workers 6]
Writes _output/as2_reading/<arm>_<seed>/ and _output/as2_reading/summary.json.
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

OUT = ROOT / "_output" / "as2_reading"
WINDOWS = [(400.0, 410.0), (700.0, 710.0), (1000.0, 1010.0)]
SEEDS = (7000, 7001, 7002)
LEARNED = ROOT / "_output" / "pretrain" / "pretrain_v3" / "policy_final.npz"
RANDOM = OUT / "policy_random_v3_7000.npz"
ARMS = {"learned_v3": LEARNED, "random_v3": RANDOM}


def run_one(job: tuple[str, int]) -> tuple[str, float]:
    arm, seed = job
    d = OUT / f"{arm}_{seed}"
    if (d / "run.json").exists() and all((d / f"trace_{a:g}_{b:g}.npz").exists()
                                         for a, b in WINDOWS):
        return str(d), 0.0
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    over = dict(seed=seed, days=1010.0, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                trace={"windows": WINDOWS, "sample_every": 4},
                policy={"kind": "mlp_frozen", "weights": str(ARMS[arm])})
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


def family_shares(path: Path) -> dict[str, float]:
    """Shares of the free-time rows by action, over the traced windows."""
    from universe25.agents.state import (
        ACT_BACK_OFF, ACT_CIRCLE, ACT_EXPLORE, ACT_MANIPULATE, ACT_RUN_ON, ACT_SOCIAL,
        ACT_TURN_BACK)
    from universe25.metrics.trace import load_trace

    names = {ACT_EXPLORE: "explore", ACT_RUN_ON: "run_on", ACT_TURN_BACK: "turn_back",
             ACT_SOCIAL: "social", ACT_MANIPULATE: "manipulate", ACT_BACK_OFF: "back_off",
             ACT_CIRCLE: "circle"}
    counts = dict.fromkeys(names.values(), 0)
    for f in sorted(path.glob("trace_*.npz")):
        act = load_trace(f)["action"]
        for code, nm in names.items():
            counts[nm] += int(np.sum(act == code))
    tot = max(1, sum(counts.values()))
    return {k: v / tot for k, v in counts.items()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    from universe25.agents.policy import MlpFrozenPolicy

    if not LEARNED.exists():
        raise SystemExit(f"missing {LEARNED}")
    OUT.mkdir(parents=True, exist_ok=True)
    if not RANDOM.exists():
        MlpFrozenPolicy.random_init(7000).save_npz(str(RANDOM))
    jobs = [(arm, s) for arm in ARMS for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        paths = [path for path, _ in ex.map(run_one, jobs)]
        print(f"runs done in {time.perf_counter() - t0:.0f} s", flush=True)
        for path, wall in ex.map(detect_one, paths):
            print(f"detected {Path(path).name} ({wall:.0f} s)", flush=True)
    rows = []
    for path in paths:
        det = json.loads((Path(path) / "detectors_unvalidated.json").read_text(encoding="utf-8"))
        run = json.loads((Path(path) / "run.json").read_text(encoding="utf-8"))
        shares = family_shares(Path(path))
        for w, res in det["windows"].items():
            for kind in ("object", "locomotor"):
                r = res[kind]
                rows.append({"run": Path(path).name, "window": w, "kind": kind,
                             "n_episodes": r["n_episodes"],
                             "reversal": r.get("seq_struct_reversal_unvalidated"),
                             "form_excess": r.get("seq_struct_form_excess_unvalidated"),
                             "form_z": r.get("seq_struct_form_z_unvalidated"),
                             "rigid": r.get("rep_rigid_loop_frac_unvalidated"),
                             "flags": r["decisions_unvalidated"]})
        print(f"{Path(path).name}: peak N {run.get('peak_n')} day {run.get('peak_day', 0):.0f}, "
              f"final N {run.get('final_n')}; free-time shares "
              + " ".join(f"{k} {v:.2f}" for k, v in shares.items()), flush=True)
    summary: dict = {"rules": det["rules"], "arms": {}, "windows": rows}
    print("\n| arm | kind | windows | c1..c5 rates | form excess median [range] | "
          "reversal median | form test met |")
    print("|---|---|---:|---|---|---:|---:|")
    for arm in ARMS:
        for kind in ("object", "locomotor"):
            kr = [r for r in rows if r["run"].startswith(arm) and r["kind"] == kind]
            names = list(kr[0]["flags"])
            rates = [float(np.mean([r["flags"][f] for r in kr])) for f in names]
            ex = np.array([np.nan if r["form_excess"] is None else r["form_excess"] for r in kr])
            z = np.array([np.nan if r["form_z"] is None else r["form_z"] for r in kr])
            rv = np.array([np.nan if r["reversal"] is None else r["reversal"] for r in kr])
            met = int(np.sum(np.isfinite(ex) & (ex >= 0.10) & (z > 1.645)))
            summary["arms"][f"{arm}:{kind}"] = {"rates": dict(zip(names, rates)),
                                                "form_met": met, "n_windows": len(kr)}
            med = (f"{np.nanmedian(ex):+.3f} [{np.nanmin(ex):+.3f}, {np.nanmax(ex):+.3f}]"
                   if np.isfinite(ex).any() else "n/a")
            rvm = f"{np.nanmedian(rv):.3f}" if np.isfinite(rv).any() else "n/a"
            print(f"| {arm} | {kind} | {len(kr)} | " + " ".join(f"{v:.2f}" for v in rates)
                  + f" | {med} | {rvm} | {met} |")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                      encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
