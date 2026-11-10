#!/usr/bin/env python
"""Pre-train the drive-reduction learner in randomised nursery worlds (P4-3).

usage: python scripts/pretrain_nursery.py [--steps 1e8] [--episode-days 60] [--seed 7000]
       [--label pretrain_v1] [--ckpt-every 5]
       [--resume _output/pretrain/<label>/checkpoints/latest.pt]
Writes _output/pretrain/<label>/: manifest.json (versions, GPU, commit, throughput, VRAM),
episodes.jsonl (one row per episode: the world drawn, colony, births, mean D, throughput),
learn_log.jsonl (one row per PPO update), checkpoints/, policy_final.npz (load it with
`policy.kind: mlp_frozen` and `policy.weights`). Training seeds 7000-7009 only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def show(r: dict) -> None:
    d_end = r["mean_D_end"]
    print(f"ep {r['episode']:4d} {r['kind'][:5]} cells {r['n_cells']:2d} "
          f"seed {r['sim_seed']} {r['resources'][:5]} "
          f"pg={int(r['playground'])} N {r['n_start']:5d}->{r['n_end']:5d} "
          f"surv {r['surviving_births']:5d}/{r['births']:5d} "
          f"D_end {'-' if d_end is None else round(d_end, 3)} "
          f"steps {r['transitions_total']:.3e} ({r['steps_per_s']:.0f}/s)", flush=True)


def main() -> int:
    from universe25.learn.nursery import pretrain

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", type=float, default=1e8)
    p.add_argument("--episode-days", type=float, default=60.0)
    p.add_argument("--seed", type=int, default=7000)
    p.add_argument("--label", type=str, default="pretrain_v1")
    p.add_argument("--ckpt-every", type=int, default=5)
    p.add_argument("--free-substeps", type=int, default=12)
    p.add_argument("--resume", type=str, default=None)
    p.add_argument("--founding-days", type=float, default=300.0)
    p.add_argument("--p-founding", type=float, default=0.4)
    p.add_argument("--ball-physics", action="store_true", help="ball physics on (P4-13)")
    p.add_argument("--novelty", action="store_true", help="novelty-based curiosity (P4-14)")
    p.add_argument("--consequence-gain", type=float, default=1.0, help="P4-14 relief gain g")
    p.add_argument("--entropy-final", type=float, default=None,
                   help="P4-15: final entropy weight (linear annealing)")
    p.add_argument("--entropy-anneal", type=str, default=None,
                   help="P4-15: annealing window in transitions, start:end (e.g. 5e7:1e8)")
    p.add_argument("--adv-norm", choices=("pooled", "per_type"), default="pooled")
    p.add_argument("--lambda-per-time", action="store_true",
                   help="P4-15: GAE lambda per unit of time (lambda ** (duration / K))")
    a = p.parse_args()
    ppo: dict = {}
    if a.entropy_final is not None:
        lo, hi = (float(v) for v in (a.entropy_anneal or "0:0").split(":"))
        ppo.update(entropy_coef_final=a.entropy_final, entropy_anneal_start=lo,
                   entropy_anneal_end=hi)
    if a.adv_norm != "pooled":
        ppo["adv_norm"] = a.adv_norm
    if a.lambda_per_time:
        ppo["gae_lambda_per_unit_time"] = True
    out = ROOT / "_output" / "pretrain" / a.label
    summ = pretrain(out, steps=a.steps, episode_days=a.episode_days, seed=a.seed,
                    free_substeps=a.free_substeps, ckpt_every=a.ckpt_every,
                    resume=Path(a.resume) if a.resume else None, progress=show,
                    founding_days=a.founding_days, p_founding=a.p_founding,
                    ball_physics=a.ball_physics, curiosity_novelty=a.novelty,
                    consequence_gain=a.consequence_gain, ppo=ppo or None)
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
