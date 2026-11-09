#!/usr/bin/env python
"""Development reading for ball physics (PHASE4_DESIGN.md 1.9, acceptance check 3).

The nursery-trained v4 learner (`_output/pretrain/pretrain_v4/policy_final.npz`, observation v4,
trained with ball physics) and a random v4 network (`MlpFrozenPolicy.random_init(7000)`) on
training seeds 7000-7002, ABUND-PG (configs/default.yaml) with ball physics on, 12 free-time
sub-steps (sub-step mode auto: rechoose), 1,010 days at 6 ticks/day, traced windows
[400, 410), [700, 710), [1000, 1010) days, every fourth individual; detectors (rules v7) with
1,000 surrogates, at most 400 individuals per window, detector seed 0. No pass condition: it
reports the flag rates, the v7 form test (and the v6 shuffle beside it), the action-family
shares, ball contacts and the ball activity counters.

usage: python scripts/read_p413.py [--workers 6]
Writes _output/p413_reading/<arm>_<seed>/ and _output/p413_reading/summary.json.
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

OUT = ROOT / "_output" / "p413_reading"
WINDOWS = [(400.0, 410.0), (700.0, 710.0), (1000.0, 1010.0)]
SEEDS = (7000, 7001, 7002)
LEARNED = ROOT / "_output" / "pretrain" / "pretrain_v4" / "policy_final.npz"
RANDOM = OUT / "policy_random_v4_7000.npz"
ARMS = {"learned_v4": LEARNED, "random_v4": RANDOM}


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
                playground={"ball_physics": True},
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


def shares_and_contacts(path: Path) -> tuple[dict[str, float], dict[str, float]]:
    """Free-time shares by action, and object-family rows in contact with a ball / other object."""
    from universe25.agents.state import (
        ACT_BACK_OFF, ACT_CIRCLE, ACT_EXPLORE, ACT_MANIPULATE, ACT_RUN_ON, ACT_SOCIAL,
        ACT_TURN_BACK, OBJECT_FAMILY)
    from universe25.metrics.trace import load_trace

    names = {ACT_EXPLORE: "explore", ACT_RUN_ON: "run_on", ACT_TURN_BACK: "turn_back",
             ACT_SOCIAL: "social", ACT_MANIPULATE: "manipulate", ACT_BACK_OFF: "back_off",
             ACT_CIRCLE: "circle"}
    run = json.loads((path / "run.json").read_text(encoding="utf-8"))
    n_balls = int(run.get("config", {}).get("playground", {}).get("n_balls", 8))
    counts = dict.fromkeys(names.values(), 0)
    obj_rows = ball_contact = other_contact = 0
    for f in sorted(path.glob("trace_*.npz")):
        t = load_trace(f)
        act = t["action"]
        for code, nm in names.items():
            counts[nm] += int(np.sum(act == code))
        fam = np.isin(act, OBJECT_FAMILY)
        c = t["contact"] > 0
        obj_rows += int(fam.sum())
        ball_contact += int(np.sum(fam & c & (t["obj_id"] < n_balls)))
        other_contact += int(np.sum(fam & c & (t["obj_id"] >= n_balls)))
    tot = max(1, sum(counts.values()))
    shares = {k: v / tot for k, v in counts.items()}
    contacts = {"object_family_rows": obj_rows,
                "ball_contact_share": ball_contact / max(1, obj_rows),
                "other_contact_share": other_contact / max(1, obj_rows)}
    return shares, contacts


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
    runs: dict[str, dict] = {}
    for path in paths:
        det = json.loads((Path(path) / "detectors_unvalidated.json").read_text(encoding="utf-8"))
        run = json.loads((Path(path) / "run.json").read_text(encoding="utf-8"))
        shares, contacts = shares_and_contacts(Path(path))
        runs[Path(path).name] = {"peak_n": run.get("peak_n"), "peak_day": run.get("peak_day"),
                                 "final_n": run.get("final_n"), "shares": shares,
                                 "contacts": contacts, "ball_stats": run.get("ball_stats")}
        for w, res in det["windows"].items():
            for kind in ("object", "locomotor"):
                r = res[kind]
                rows.append({"run": Path(path).name, "window": w, "kind": kind,
                             "n_episodes": r["n_episodes"],
                             "reversal": r.get("seq_struct_reversal_unvalidated"),
                             "form_excess": r.get("seq_struct_form_excess_unvalidated"),
                             "form_z": r.get("seq_struct_form_z_unvalidated"),
                             "shuffle_excess": r.get("seq_struct_form_shuffle_excess_unvalidated"),
                             "flags": r["decisions_unvalidated"],
                             "flags_v6": r["decisions_v6_unvalidated"]})
        bs = run.get("ball_stats") or {}
        print(f"{Path(path).name}: peak N {run.get('peak_n')} day {run.get('peak_day', 0):.0f}, "
              f"final N {run.get('final_n')}; pushes {bs.get('pushes')} (object family "
              f"{bs.get('object_family_pushes')}), rolled {bs.get('rolled_in', 0):.0f} in; "
              f"ball contact share {contacts['ball_contact_share']:.2f}; shares "
              + " ".join(f"{k} {v:.2f}" for k, v in shares.items()), flush=True)
    summary: dict = {"rules": det["rules"], "arms": {}, "runs": runs, "windows": rows}
    print("\n| arm | kind | windows | c1..c5 rates (v7) | form excess v7 median [range] | "
          "v6 shuffle excess median | reversal median | form test met (v7) |")
    print("|---|---|---:|---|---|---:|---:|---:|")
    for arm in ARMS:
        for kind in ("object", "locomotor"):
            kr = [r for r in rows if r["run"].startswith(arm) and r["kind"] == kind]
            names = list(kr[0]["flags"])
            rates = [float(np.mean([r["flags"][f] for r in kr])) for f in names]

            def arr(key: str) -> np.ndarray:
                return np.array([np.nan if r[key] is None else r[key] for r in kr], float)

            ex, z = arr("form_excess"), arr("form_z")
            sh, rv = arr("shuffle_excess"), arr("reversal")
            met = int(np.sum(np.isfinite(ex) & (ex >= 0.10) & (z > 1.645)))
            summary["arms"][f"{arm}:{kind}"] = {"rates": dict(zip(names, rates)),
                                                "form_met": met, "n_windows": len(kr)}

            def med(v: np.ndarray, rng: bool = False) -> str:
                if not np.isfinite(v).any():
                    return "n/a"
                m = f"{np.nanmedian(v):+.3f}"
                return m + (f" [{np.nanmin(v):+.3f}, {np.nanmax(v):+.3f}]" if rng else "")

            print(f"| {arm} | {kind} | {len(kr)} | " + " ".join(f"{v:.2f}" for v in rates)
                  + f" | {med(ex, True)} | {med(sh)} | {med(rv)} | {met} |")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                      encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
