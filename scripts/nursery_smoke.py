#!/usr/bin/env python
"""P4-2 nursery smoke: does the drive-reduction learner lower the homeostatic drive D below the
random policy it starts from?

Arms (same seed, same nursery, 12 free-time sub-steps):
  ppo_learn      policy mlp_ppo, learning on
  ppo_no_update  policy mlp_ppo with ppo.enabled false: the identical initial network, never
                 updated (the random-policy baseline: near-uniform over the eligible actions)
  need_driven    the heuristic (continue mode), for reference
Records mean D over the alive agents and the per-drive means every day; the acceptance test is
the mean D over the last quarter of the run, learner below the no-update baseline, with at least
10^7 learner transitions. Nursery = `initial_pairs` founders (default 100) on the frozen biology;
this is not the canonical 4-pair world and is a training seed (never 8000-8011).

usage: python scripts/nursery_smoke.py [--days 450] [--pairs 100] [--seed 7000]
Writes _output/nursery_smoke/<arm>/ (run files, daily.json) and _output/nursery_smoke.json.
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

ARMS = {
    "ppo_learn": {"policy": {"kind": "mlp_ppo"}},
    "ppo_no_update": {"policy": {"kind": "mlp_ppo", "ppo": {"enabled": False}}},
    "need_driven": {"policy": {"kind": "need_driven"}},
}


def run_arm(job: tuple[str, int, int, float]) -> dict:
    arm, seed, pairs, days = job
    import numpy as np

    from universe25.config import load_config
    from universe25.learn.reward import DRIVES, drive, read_drives
    from universe25.sim import Universe25Sim

    out = ROOT / "_output" / "nursery_smoke" / arm
    over = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=4096, initial_pairs=pairs, log_every_ticks=6, snapshot_every_days=0,
                free_substeps=12, **ARMS[arm])
    sim = Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over), out)
    daily = []
    t0 = time.perf_counter()
    for d in range(int(days)):
        for _ in range(6):
            sim.step()
        idx = np.flatnonzero(sim.agents.alive)
        if idx.size == 0:
            break
        dr = read_drives(sim.agents, idx)
        row = {"day": d + 1, "n": int(idx.size), "mean_D": float(drive(dr).mean())}
        row.update({f"mean_{k}": float(dr[:, i].mean()) for i, k in enumerate(DRIVES)})
        if hasattr(sim.policy, "n_transitions"):
            row["transitions"] = int(sim.policy.n_transitions)
        daily.append(row)
    learn = sim.policy.finish(sim) if hasattr(sim.policy, "finish") else None
    sim.logger.close()
    (out / "daily.json").write_text(json.dumps(daily), encoding="utf-8")
    return {"arm": arm, "wall": time.perf_counter() - t0, "daily": daily, "learn": learn}


def main() -> int:
    import numpy as np

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=float, default=450.0)
    p.add_argument("--pairs", type=int, default=100)
    p.add_argument("--seed", type=int, default=7000)
    a = p.parse_args()
    jobs = [(arm, a.seed, a.pairs, a.days) for arm in ARMS]
    with ProcessPoolExecutor(max_workers=len(jobs)) as ex:
        res = {r["arm"]: r for r in ex.map(run_arm, jobs)}
    summary: dict = {"config": vars(a), "arms": {}}
    print(f"{'arm':14s} {'wall s':>7s} {'days':>5s} {'N end':>6s} {'D last quarter':>15s} "
          f"{'D first quarter':>16s} {'transitions':>12s}")
    for arm, r in res.items():
        dl = r["daily"]
        n = len(dl)
        q = max(1, n // 4)
        last = float(np.mean([x["mean_D"] for x in dl[-q:]]))
        first = float(np.mean([x["mean_D"] for x in dl[:q]]))
        per = {k: float(np.mean([x[k] for x in dl[-q:]])) for k in dl[0] if k.startswith("mean_")
               and k != "mean_D"}
        tr = dl[-1].get("transitions")
        summary["arms"][arm] = {"wall": r["wall"], "days": n, "n_end": dl[-1]["n"],
                                "mean_D_last_quarter": last, "mean_D_first_quarter": first,
                                "per_drive_last_quarter": per, "transitions": tr,
                                "learn": r["learn"]}
        print(f"{arm:14s} {r['wall']:7.0f} {n:5d} {dl[-1]['n']:6d} {last:15.4f} {first:16.4f} "
              f"{tr if tr is not None else '-':>12}")
    L = summary["arms"]["ppo_learn"]
    B = summary["arms"]["ppo_no_update"]
    ok = L["mean_D_last_quarter"] < B["mean_D_last_quarter"] and (L["transitions"] or 0) >= 1e7
    summary["acceptance"] = {"learner_below_no_update_baseline": bool(
        L["mean_D_last_quarter"] < B["mean_D_last_quarter"]),
        "transitions_ge_1e7": bool((L["transitions"] or 0) >= 1e7), "pass": bool(ok)}
    print("\nper-drive means, last quarter:")
    keys = list(L["per_drive_last_quarter"])
    print(f"{'arm':14s} " + " ".join(f"{k[5:]:>12s}" for k in keys))
    for arm in ARMS:
        pd = summary["arms"][arm]["per_drive_last_quarter"]
        print(f"{arm:14s} " + " ".join(f"{pd[k]:12.4f}" for k in keys))
    print(f"\nacceptance: {summary['acceptance']}")
    out = ROOT / "_output" / "nursery_smoke.json"
    out.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
