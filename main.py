#!/usr/bin/env python
"""Entry point: python main.py --seed 7000 --out _output/run1"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from universe25.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
