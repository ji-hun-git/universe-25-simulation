#!/usr/bin/env python
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from universe25.nvidia import probe_nvidia_stack
from universe25.config import load_config
from universe25.world.geometry import build_world
from universe25.nvidia.usd_export import export_pen_usda

def main() -> int:
    info = probe_nvidia_stack()
    print(json.dumps(info, indent=2))
    cfg = load_config(ROOT / "configs" / "default.yaml")
    world = build_world(cfg.geometry, cfg.playground, seed=7100)
    out = ROOT / "_output" / "usd" / "pen.usda"
    res = export_pen_usda(world, out)
    print(json.dumps({"usd_export": res}, indent=2))
    return 0 if "warp" in info and "error" not in info.get("warp", {}) else 1

if __name__ == "__main__":
    raise SystemExit(main())
