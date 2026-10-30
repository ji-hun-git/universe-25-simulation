"""Same seed => identical trajectory hash (numpy backend)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import SimConfig
from universe25.sim import Universe25Sim


def _traj_digest(seed: int, days: float, out: Path) -> str:
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
    h = hashlib.sha256()
    total = int(days * cfg.ticks_per_day)
    for _ in range(total):
        sim.step()
        a = sim.agents
        alive = a.alive
        payload = np.concatenate(
            [
                a.x[alive],
                a.y[alive],
                a.hunger[alive],
                a.stress[alive],
                a.role[alive].astype(np.float32),
                np.array([a.n_alive], dtype=np.float32),
            ]
        )
        h.update(payload.tobytes())
    return h.hexdigest()


def test_determinism() -> None:
    out = ROOT / "_output" / "test_det"
    a = _traj_digest(7100, 5.0, out / "a")
    b = _traj_digest(7100, 5.0, out / "b")
    assert a == b, (a, b)
    c = _traj_digest(7101, 5.0, out / "c")
    assert a != c, (a, c)


if __name__ == "__main__":
    test_determinism()
    print("test_determinism: OK")
