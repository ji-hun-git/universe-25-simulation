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
    from universe25.calib.policy_guard import format_table, guard, run_arm, write_report

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind")
    p.add_argument("--seeds", type=int, default=12)
    p.add_argument("--first", type=int, default=8000)
    p.add_argument("--days", type=float, default=1600.0)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--weights", type=str, default=None)
    p.add_argument("--label", type=str, default=None)
    p.add_argument("--substeps", type=int, default=1, help="free_substeps for the arm (P4-8)")
    a = p.parse_args()
    seeds = [a.first + i for i in range(a.seeds)]
    out_dir = ROOT / "_output"
    cache = out_dir / f"policy_guard_control_{a.first}_{a.seeds}_{a.days:.0f}.json"
    control = None
    if cache.exists():
        raw = json.loads(cache.read_text(encoding="utf-8"))
        control = {int(k): v for k, v in raw.items()}
        print(f"control rows reused from {cache}", flush=True)
    else:
        control = run_arm("need_driven", seeds, a.days, a.workers, progress=print)
        out_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({str(k): v for k, v in control.items()}, indent=1),
                         encoding="utf-8")
    extra = {"free_substeps": a.substeps} if a.substeps > 1 else None
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
