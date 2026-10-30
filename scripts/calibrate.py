#!/usr/bin/env python
"""Recompute calibration from an existing metrics.parquet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.metrics.calibration import write_calibration


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--metrics", type=str, required=True)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--run-json", type=str, default=None)
    args = p.parse_args()
    summary = None
    if args.run_json:
        summary = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    report = write_calibration(Path(args.metrics), Path(args.out), summary)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
