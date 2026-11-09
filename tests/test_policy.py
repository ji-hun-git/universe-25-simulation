"""Policy hook: the need-driven policy is the default, returns eligible actions only, sampling is
seed-deterministic, and the H2 audit covers the policy module."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.observation import OBS_DIM, OBS_NAMES  # noqa: E402
from universe25.agents.policy import (  # noqa: E402
    MlpFrozenPolicy,
    NeedDrivenPolicy,
    make_policy,
)
from universe25.agents.state import ACT_NEST, ACT_REST, N_ACTIONS  # noqa: E402
from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _make_sim(days: float = 5.0, seed: int = 7100, **policy) -> Universe25Sim:
    over = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=512, log_every_ticks=10**9, snapshot_every_days=0)
    if policy:
        over["policy"] = policy
    cfg = load_config(ROOT / "configs" / "default.yaml", over)
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


def test_mlp_frozen_is_deterministic_masked_and_seed_sensitive() -> None:
    sim1 = _make_sim(kind="mlp_frozen")
    sim2 = _make_sim(kind="mlp_frozen")
    assert isinstance(sim1.policy, MlpFrozenPolicy)
    for _ in range(60):
        sim1.step()
        sim2.step()
    assert np.array_equal(sim1.agents.last_action, sim2.agents.last_action)
    assert np.array_equal(sim1.agents.x, sim2.agents.x)
    assert sim1.agents.n_alive == sim2.agents.n_alive
    # another seed gives another trajectory (weights and policy stream both depend on it)
    sim3 = _make_sim(seed=7101, kind="mlp_frozen")
    for _ in range(60):
        sim3.step()
    assert not np.array_equal(sim1.agents.x, sim3.agents.x)
    # the mask is respected and the observation is finite with the documented width
    a = sim1.agents
    idx = np.flatnonzero(a.alive)
    m = idx.size
    allowed = np.zeros((m, N_ACTIONS), dtype=bool)
    allowed[:, ACT_REST] = True
    allowed[::3, ACT_NEST] = True
    chosen = sim1.policy.choose(sim1, idx, allowed)
    assert chosen.dtype == np.int8 and allowed[np.arange(m), chosen].all()
    obs = sim1.policy.observe(sim1, idx)
    assert obs.shape == (m, OBS_DIM) and obs.dtype == np.float32
    assert np.isfinite(obs).all()
    assert obs[:, 37:37 + N_ACTIONS].sum(axis=1).tolist() == [1.0] * m, "last-action one-hot"
    # weights round-trip through npz and load back as the same policy
    path = Path(tempfile.mkdtemp(prefix="u25_w_")) / "w.npz"
    sim1.policy.save_npz(str(path))
    sim4 = _make_sim(kind="mlp_frozen", weights=str(path))
    for _ in range(60):
        sim4.step()
    assert np.array_equal(sim1.agents.x, sim4.agents.x)


def test_observation_names_have_no_forbidden_feature_or_hidden_information() -> None:
    assert len(OBS_NAMES) == OBS_DIM == 59  # observation v5 (place novelty, P4-14)
    assert "lifespan" not in OBS_NAMES and "competence" not in OBS_NAMES
    joined = " ".join(OBS_NAMES).lower().replace("playground", "")
    for bad in ("play", "bout", "motif", "exagger", "score", "reward"):
        assert bad not in joined, bad


def test_h2_no_play_signal_in_policy_module() -> None:
    for name in ("policy.py", "observation.py"):
        src = (ROOT / "src" / "universe25" / "agents" / name).read_text(encoding="utf-8")
        src = src.lower().replace("playground", "").replace("playscore field", "")
        for bad in ("play_reward", "reward_play", "play_score", "motif", "_bout", "bout_"):
            assert bad not in src, (name, bad)


if __name__ == "__main__":
    test_default_policy_is_need_driven_and_respects_the_mask()
    test_policy_sampling_is_deterministic_for_a_seed()
    test_mlp_frozen_is_deterministic_masked_and_seed_sensitive()
    test_observation_names_have_no_forbidden_feature_or_hidden_information()
    test_h2_no_play_signal_in_policy_module()
    print("test_policy: OK")
