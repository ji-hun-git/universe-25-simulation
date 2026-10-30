"""Warp backend smoke (skip if no CUDA). Determinism remains NumPy-only."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_warp_smoke() -> None:
    try:
        import warp as wp
        import torch
    except Exception:
        print("skip: warp/torch missing")
        return
    wp.init()
    if not any(getattr(d, "is_cuda", False) for d in wp.get_devices()):
        print("skip: no CUDA device")
        return
    from universe25.config import SimConfig
    from universe25.sim import Universe25Sim

    cfg = SimConfig(
        seed=7100,
        days=2.0,
        backend="warp",
        device="cuda",
        max_agents=256,
        log_every_ticks=24,
        snapshot_every_days=0,
        use_cuda_graph=True,
        arm_label="TRACK-E-U25-WARP-SMOKE",
    )
    out = ROOT / "_output" / "test_warp"
    sim = Universe25Sim(cfg, out)
    assert sim.warp_engine is not None
    sim.run()
    assert sim._nan_count == 0
    st = sim.warp_engine.status()
    print("warp status", st)


if __name__ == "__main__":
    test_warp_smoke()
    print("test_warp_smoke: OK")
