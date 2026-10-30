"""Same seed => identical population trajectory (numpy backend)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import SimConfig
from universe25.sim import Universe25Sim


def _curve(seed: int, days: float, out: Path) -> list[int]:
    cfg = SimConfig(
        seed=seed,
        days=days,
        backend="numpy",
        device="cpu",
        max_agents=256,
        log_every_ticks=24,
        snapshot_every_days=0,
        arm_label="TRACK-E-U25-TEST",
    )
    cfg.playground.enabled = True
    sim = Universe25Sim(cfg, out)
    ns = []
    total = int(days * cfg.ticks_per_day)
    for _ in range(total):
        sim.step()
        if sim.tick % cfg.ticks_per_day == 0:
            ns.append(sim.agents.n_alive)
    return ns


def test_determinism() -> None:
    out = ROOT / "_output" / "test_det"
    a = _curve(7100, 5.0, out / "a")
    b = _curve(7100, 5.0, out / "b")
    assert a == b, (a, b)
    c = _curve(7101, 5.0, out / "c")
    assert a != c


if __name__ == "__main__":
    test_determinism()
    print("test_determinism: OK")
