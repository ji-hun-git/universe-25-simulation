"""P4-2 learner: the reward is a function of the drives only; GAE matches a hand recursion; the
actor exports to the frozen-policy format; a learning run is bit-identical run to run on the
same device; `ppo.enabled: false` never updates; learner code passes the H2 audit."""
from __future__ import annotations

import hashlib
import inspect
import io
import sys
import tempfile
import tokenize
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import load_config  # noqa: E402
from universe25.learn import reward as R  # noqa: E402
from universe25.learn.ppo import gae  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def test_reward_is_drive_reduction_only() -> None:
    h = np.array([[0.3, 0.2, 0.1, 0.5, 0.4, 0.2, 0.1, 0.6]])
    d = R.drive(h)
    assert np.allclose(R.drive_reduction(d, d), 0.0), "no drive change, no reward"
    lower = h.copy()
    lower[0, 0] = 0.0  # a meal
    assert R.drive_reduction(d, R.drive(lower))[0] > 0
    assert np.isclose(R.D_MAX, np.sqrt(8.0))
    assert np.allclose(R.terminal_reward(d), d - R.D_MAX)
    assert np.allclose(R.contributions(h).sum(axis=1) ** 0.5, d)
    assert R.drive_reduction(np.array([10.0]), np.array([0.0]))[0] == R.D_MAX, "clipped"
    # the reward functions take drives and nothing else
    for fn in (R.drive, R.drive_reduction, R.terminal_reward, R.contributions, R.deviations):
        params = [p for p in inspect.signature(fn).parameters]
        assert all(p in ("drives", "d_before", "d_after") for p in params), (fn.__name__, params)
    assert R.DRIVES == ("hunger", "thirst", "fatigue", "social_drive", "curiosity", "boredom",
                        "stress", "maternal_need")


def test_maternal_need_is_the_own_litters_hunger() -> None:
    """A nursing female's maternal_need is the mean hunger of the pups in her nest box; it is
    zero without pups, for non-nursing agents and for pups; feeding the pups lowers it."""
    from universe25.agents.drives import maternal_need
    from universe25.agents.state import ROLE_BREEDING_FEMALE, ROLE_NURSING, ROLE_PUP

    sim = Universe25Sim(load_config(ROOT / "configs" / "default.yaml", dict(
        seed=7100, days=1.0, ticks_per_day=6, backend="numpy", device="cpu", max_agents=64,
        log_every_ticks=10**9, snapshot_every_days=0)), Path(tempfile.mkdtemp(prefix="u25mat_")))
    a = sim.agents
    s = np.flatnonzero(a.alive)[:8]
    mom, other, p1, p2, p3 = s[0], s[1], s[2], s[3], s[4]
    a.role[s] = ROLE_BREEDING_FEMALE
    a.nest_id[s] = 200
    a.role[mom] = ROLE_NURSING
    a.nest_id[mom] = 7
    a.role[[p1, p2, p3]] = ROLE_PUP
    a.nest_id[[p1, p2]] = 7
    a.nest_id[p3] = 9  # another box
    a.hunger[[p1, p2, p3]] = [0.4, 0.8, 1.4]
    need = maternal_need(a, np.array([mom, other, p1]))
    assert np.isclose(need[0], 0.6) and need[1] == 0.0 and need[2] == 0.0
    a.hunger[[p1, p2]] = 0.1  # the litter is fed
    assert np.isclose(maternal_need(a, np.array([mom]))[0], 0.1)
    a.nest_id[[p1, p2]] = 9  # no pups left in her box
    assert maternal_need(a, np.array([mom]))[0] == 0.0


def test_gae_matches_hand_recursion() -> None:
    # slot 0: three transitions, the last terminal; slot 1: two transitions, open at the end
    rew = np.array([0.1, -0.2, -1.0, 0.3, 0.05])
    val = np.array([0.5, 0.4, 0.2, 0.1, 0.3])
    nxt = np.array([0.4, 0.2, 0.0, 0.3, 0.6])
    done = np.array([0, 0, 1, 0, 0], float)
    gam = np.array([0.9, 1.0, 0.95, 0.9, 0.8])
    slot = np.array([0, 0, 0, 1, 1])
    time = np.array([0, 1, 2, 0, 5])
    lam = 0.95
    perm = np.array([4, 1, 3, 0, 2])  # order must not matter
    got = gae(rew[perm], val[perm], nxt[perm], done[perm], gam[perm], lam, slot[perm],
              time[perm])
    exp = np.zeros(5)
    for chain in ([0, 1, 2], [3, 4]):
        a_next = 0.0
        for t in reversed(chain):
            nd = 1.0 - done[t]
            delta = rew[t] + gam[t] * nd * nxt[t] - val[t]
            a_next = delta + gam[t] * lam * nd * a_next
            exp[t] = a_next
    assert np.allclose(got, exp[perm]), (got, exp[perm])


def _run(days: float = 20.0, enabled: bool = True, out: str = "u25learn_") -> tuple[str, Path,
                                                                                    Universe25Sim]:
    over = dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=1024, initial_pairs=40, log_every_ticks=10**9, snapshot_every_days=0,
                free_substeps=12,
                policy={"kind": "mlp_ppo", "ppo": {"rollout_ticks": 6, "enabled": enabled}})
    sim = Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over),
                        Path(tempfile.mkdtemp(prefix=out)))
    h = hashlib.sha256()
    for _ in range(int(days * 6)):
        sim.step()
        al = sim.agents.alive
        h.update(sim.agents.last_action[al].tobytes())
        h.update(sim.agents.x[al].tobytes())
    sim.policy.finish(sim)
    with np.load(sim.out_dir / "policy_final.npz") as z:
        for k in sorted(z.files):
            h.update(z[k].tobytes())
    return h.hexdigest(), sim.out_dir, sim


def test_learning_run_is_bit_identical_and_exports_to_mlp_frozen() -> None:
    h1, out1, sim1 = _run()
    h2, _, _ = _run()
    assert h1 == h2, "a learning run must repeat bit for bit on the same device"
    assert sim1.policy.learner.n_updates >= 15
    # the exported actor is the frozen policy: identical logits on the same observations
    import torch

    from universe25.agents.policy import MlpFrozenPolicy

    frozen = MlpFrozenPolicy.from_npz(str(out1 / "policy_final.npz"), seed=7100)
    idx = np.flatnonzero(sim1.agents.alive)
    obs = sim1.policy.builder.build(sim1, idx)
    with torch.no_grad():
        logits, _ = sim1.policy.learner.net(torch.from_numpy(obs).to(sim1.policy.learner.device))
    assert np.allclose(frozen.logits(obs), logits.cpu().numpy(), atol=1e-4)


def test_disabled_learner_never_updates() -> None:
    _, out, sim = _run(days=4.0, enabled=False, out="u25noupd_")
    assert sim.policy.learner.n_updates == 0
    assert not (out / "learn_log.jsonl").exists()
    from universe25.agents.observation import OBS_DIM
    from universe25.agents.state import N_ACTIONS
    from universe25.learn.ppo import PPOLearner

    fresh = PPOLearner(OBS_DIM, N_ACTIONS, 128, sim.cfg.policy.ppo, seed=7100).actor_params()
    with np.load(out / "policy_final.npz") as z:
        for k, v in fresh.items():
            assert np.array_equal(z[k], v), k


def test_h2_learner_code_has_no_play_signal() -> None:
    bad = ("play", "bout", "motif", "exaggerat", "playscore", "detector", "trace")
    geometry = {"playground", "playground_enabled", "playground_bounds", "in_playground",
                "play_objects", "PlayObject"}  # world geometry, allowed by H2
    for path in sorted((ROOT / "src" / "universe25" / "learn").glob("*.py")):
        src = path.read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.NAME and tok.string not in geometry:
                low = tok.string.lower()
                assert not any(b in low for b in bad), (path.name, tok.string)


if __name__ == "__main__":
    test_reward_is_drive_reduction_only()
    test_maternal_need_is_the_own_litters_hunger()
    test_gae_matches_hand_recursion()
    test_learning_run_is_bit_identical_and_exports_to_mlp_frozen()
    test_disabled_learner_never_updates()
    test_h2_learner_code_has_no_play_signal()
    print("test_learn: OK")
