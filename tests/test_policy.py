"""Policy hook: the need-driven policy is the default, returns eligible actions only, sampling is
seed-deterministic, and the H2 audit covers the policy module."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.policy import NeedDrivenPolicy, make_policy  # noqa: E402
from universe25.agents.state import ACT_NEST, ACT_REST, N_ACTIONS  # noqa: E402
from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _make_sim(days: float = 5.0) -> Universe25Sim:
    cfg = load_config(
        ROOT / "configs" / "default.yaml",
        dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
             max_agents=512, log_every_ticks=10**9, snapshot_every_days=0),
    )
    return Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25_policy_")))


def test_default_policy_is_need_driven_and_respects_the_mask() -> None:
    sim = _make_sim()
    assert isinstance(sim.policy, NeedDrivenPolicy)
    assert make_policy(sim.cfg.policy).name == "need_driven"
    for _ in range(30):
        sim.step()
    a = sim.agents
    idx = np.flatnonzero(a.alive)
    m = idx.size
    assert m > 0
    allowed = np.zeros((m, N_ACTIONS), dtype=bool)
    allowed[:, ACT_REST] = True
    allowed[::2, ACT_NEST] = True
    chosen = sim.policy.choose(sim, idx, allowed)
    assert chosen.dtype == np.int8 and chosen.shape == (m,)
    assert allowed[np.arange(m), chosen].all(), "ineligible action chosen"


def test_policy_sampling_is_deterministic_for_a_seed() -> None:
    sim1, sim2 = _make_sim(), _make_sim()
    for _ in range(60):
        sim1.step()
        sim2.step()
    assert np.array_equal(sim1.agents.last_action, sim2.agents.last_action)
    assert np.array_equal(sim1.agents.x, sim2.agents.x)
    assert sim1.agents.n_alive == sim2.agents.n_alive


def test_h2_no_play_signal_in_policy_module() -> None:
    src = (ROOT / "src" / "universe25" / "agents" / "policy.py").read_text(encoding="utf-8")
    src = src.lower().replace("playground", "")
    for bad in ("play_reward", "reward_play", "playscore", "play_score", "motif", "_bout", "bout_"):
        assert bad not in src, bad


if __name__ == "__main__":
    test_default_policy_is_need_driven_and_respects_the_mask()
    test_policy_sampling_is_deterministic_for_a_seed()
    test_h2_no_play_signal_in_policy_module()
    print("test_policy: OK")
