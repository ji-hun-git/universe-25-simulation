#!/usr/bin/env python
"""Calibration guard for a policy arm (phase 4, H-d): the same seeds under the need-driven
control and under <kind>, drift of every landmark, preregistered verdict (every canonical
landmark mean within 10 % of the control, decline band at day 1200 held).

usage: python scripts/policy_guard.py <kind> [--seeds 12] [--first 8000] [--days 1600]
       [--workers 6] [--weights w.npz] [--label name]
Writes _output/policy_guard_<label>.json; the control rows are cached per (first, seeds, days)
in _output/policy_guard_control_<first>_<seeds>_<days>.json and reused. NumPy path, 6 ticks/day.
Evaluation seeds 8000-8011 are reserved for arm comparisons (PLAN.md section 15.3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    from universe25.calib.policy_guard import (
        arm_config,
        format_table,
        guard,
        run_arm,
        write_report,
    )
    from universe25.config import load_config
    from universe25.repro import config_hash

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind")
    p.add_argument("--seeds", type=int, default=12)
    p.add_argument("--first", type=int, default=8000)
    p.add_argument("--days", type=float, default=1600.0)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--weights", type=str, default=None)
    p.add_argument("--label", type=str, default=None)
    p.add_argument("--substeps", type=int, default=1, help="free_substeps for the arm (P4-8)")
    p.add_argument("--ball-physics", action="store_true", help="ball physics for the arm (P4-13)")
    p.add_argument("--novelty", action="store_true", help="novelty-based curiosity (P4-14)")
    p.add_argument("--consequence-gain", type=float, default=1.0, help="P4-14 relief gain g")
    p.add_argument("--control-substeps", type=int, default=1,
                   help="free_substeps of the need-driven control (1 = the frozen reference; "
                        "12 = the K = 12-continue heuristic)")
    a = p.parse_args()
    seeds = [a.first + i for i in range(a.seeds)]
    out_dir = ROOT / "_output"
    # the control's cache is keyed by the hash of its resolved config (review 2026-11-09: a
    # K = 12 control was once reused as the K = 1 reference)
    c_extra = {"free_substeps": a.control_substeps} if a.control_substeps > 1 else None
    c_hash = config_hash(load_config(arm_config("need_driven", None, None, c_extra)))[:10]
    cache = out_dir / f"policy_guard_control_{a.first}_{a.seeds}_{a.days:.0f}_{c_hash}.json"
    print(f"control: need_driven, free_substeps {a.control_substeps}, config {c_hash}",
          flush=True)
    control = None
    if cache.exists():
        raw = json.loads(cache.read_text(encoding="utf-8"))
        control = {int(k): v for k, v in raw.items()}
        print(f"control rows reused from {cache}", flush=True)
    else:
        control = run_arm("need_driven", seeds, a.days, a.workers, progress=print,
                          extra=c_extra)
        out_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({str(k): v for k, v in control.items()}, indent=1),
                         encoding="utf-8")
    extra = {"free_substeps": a.substeps} if a.substeps > 1 else {}
    if a.ball_physics:
        extra["playground"] = {"ball_physics": True}
    if a.novelty or a.consequence_gain != 1.0:
        extra["drives"] = {"curiosity_novelty": bool(a.novelty),
                           "consequence_gain": float(a.consequence_gain)}
    extra = extra or None
    report = guard(a.kind, seeds, a.days, a.workers, a.weights, control_rows=control,
                   progress=print, extra=extra)
    print()
    print(format_table(report))
    out = out_dir / f"policy_guard_{a.label or a.kind}.json"
    write_report(report, out)
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
