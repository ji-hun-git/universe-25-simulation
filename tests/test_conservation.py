"""Alive count conservation: births - deaths = delta N; no play reward in config."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import SimConfig, load_config
from universe25.sim import Universe25Sim


def test_population_accounting() -> None:
    out = ROOT / "_output" / "test_cons"
    cfg = SimConfig(
        seed=7100,
        days=20.0,
        backend="numpy",
        device="cpu",
        max_agents=512,
        log_every_ticks=24,
        snapshot_every_days=0,
        arm_label="TRACK-E-U25-TEST",
    )
    sim = Universe25Sim(cfg, out)
    n0 = sim.agents.n_alive
    sim.run()
    expected = n0 + sim._births - sim._deaths
    assert sim.agents.n_alive == expected, (sim.agents.n_alive, expected, sim._births, sim._deaths)
    assert sim._nan_count == 0


def test_no_play_reward_in_config() -> None:
    cfg = load_config(ROOT / "configs" / "default.yaml")
    dumped = cfg.model_dump_json().lower()
    # Allowed mentions: playground geometry. Forbidden: play_reward / reward_play
    assert "play_reward" not in dumped
    assert "reward_play" not in dumped
    # Source audit: sim.py must not assign a play reward
    sim_src = (ROOT / "src" / "universe25" / "sim.py").read_text(encoding="utf-8")
    assert "play_reward" not in sim_src.lower()
    assert "reward_play" not in sim_src.lower()


if __name__ == "__main__":
    test_no_play_reward_in_config()
    test_population_accounting()
    print("test_conservation: OK")
