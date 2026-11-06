"""Free-time sub-steps (P4-8): off is identical; sub-steps never draw from the biology stream;
they move only agents whose decision action is free; with every sub-step on the decision's own
action the decision's reach and relief are preserved; the trace has K rows per decision."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import ACT_EXPLORE, ACT_MANIPULATE, ACT_SOCIAL  # noqa: E402
from universe25.config import load_config  # noqa: E402
from universe25.metrics.trace import load_trace  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402

FREE = (ACT_EXPLORE, ACT_SOCIAL, ACT_MANIPULATE)


def _sim(K: int, days: float = 30.0, **extra) -> Universe25Sim:
    over = dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=512, log_every_ticks=10**9, snapshot_every_days=0, **extra)
    if K != 1 or "free_substeps" in extra:
        over["free_substeps"] = K
    cfg = load_config(ROOT / "configs" / "default.yaml", over)
    return Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix=f"u25sub{K}_")))


def _warm(sims: list[Universe25Sim], ticks: int) -> None:
    for _ in range(ticks):
        for s in sims:
            s.step()


def test_off_is_identical_to_default() -> None:
    a, b = _sim(1), _sim(1, free_substeps=1)
    assert a.free_substeps == b.free_substeps == 1 and b._sub_rng is None
    _warm([a, b], 90)
    for k in ("x", "y", "hunger", "curiosity", "stress", "age_days"):
        assert np.array_equal(getattr(a.agents, k), getattr(b.agents, k)), k


def _one_decision(sim: Universe25Sim, use_sub: bool) -> dict:
    alive = sim.agents.alive.copy()
    actions = sim._select_actions(alive)
    pre = sim._free_pre(alive, actions) if use_sub else None
    sim._execute_actions(alive, actions)
    if pre is not None:
        sim._run_free_substeps(pre)
    return {"actions": actions, "alive": alive, "pre": pre}


def test_substeps_use_their_own_stream_and_move_only_free_agents() -> None:
    for mode in ("continue", "rechoose"):
        _stream_check(mode)


def _stream_check(mode: str) -> None:
    off = _sim(1)
    on = _sim(12, policy={"kind": "need_driven", "substep_mode": mode})
    _warm([off], 60)
    # bring `on` to the identical state: same seed, run with sub-steps off for the warm-up
    on.free_substeps = 1
    _warm([on], 60)
    on.free_substeps = 12
    for k in ("x", "y", "curiosity"):
        assert np.array_equal(getattr(off.agents, k), getattr(on.agents, k)), k
    r_off = _one_decision(off, use_sub=False)
    r_on = _one_decision(on, use_sub=True)
    assert np.array_equal(r_off["actions"], r_on["actions"])
    assert off.rng.bit_generator.state == on.rng.bit_generator.state, \
        "sub-steps drew from the biology stream"
    alive = r_on["alive"]
    F = r_on["pre"]["F"]
    assert F.size > 0
    not_free = alive.copy()
    not_free[F] = False
    for k in ("x", "y", "hunger", "thirst", "fatigue", "stress", "curiosity", "boredom"):
        assert np.array_equal(getattr(off.agents, k)[not_free], getattr(on.agents, k)[not_free]), k
    assert np.all(np.isin(r_on["actions"][F], FREE))
    # relief of free agents is between none and the full decision relief
    d = on.cfg.drives
    pre_c = r_on["pre"]["curiosity"]
    assert np.all(on.agents.curiosity[F] <= pre_c + 1e-6)
    assert np.all(on.agents.curiosity[F] >= pre_c - d.curiosity_decay_on_novel - 1e-6)
    assert np.array_equal(on.agents.last_action[F], r_on["actions"][F]), "decision action kept"
    if mode == "continue":  # same relief as the decision, exactly
        assert np.allclose(on.agents.curiosity[F], off.agents.curiosity[F], atol=1e-5)
        assert np.allclose(on.agents.social_drive[F], off.agents.social_drive[F], atol=1e-5)


def test_reach_is_preserved_when_every_substep_explores() -> None:
    sim = _sim(12)
    _warm([sim], 60)
    a = sim.agents
    alive = a.alive.copy()
    idx = np.flatnonzero(alive)
    # every alive adult explores, and every sub-step explores too
    actions = np.zeros(a.capacity, dtype=np.int8)
    actions[idx] = ACT_EXPLORE
    pups = a.age_days[idx] < sim.cfg.biology.weaning_days
    actions[idx[pups]] = 0
    real = sim.policy.choose
    sim.policy.choose = lambda s, i, al, rng=None: np.full(i.size, ACT_EXPLORE, np.int8)
    full = sim.cfg.drives.curiosity_decay_on_novel
    dxs, rels = [], []
    try:
        for _ in range(20):  # repeat the decision for enough samples (8 founders at day 10)
            a.x[idx] = 50.5  # centre: the walls do not clip the walk
            a.y[idx] = 50.5
            a.curiosity[idx] = 1.0  # relief not clipped at zero
            pre = sim._free_pre(alive, actions)
            x0 = a.x[pre["F"]].copy()
            sim._execute_actions(alive, actions)
            sim._run_free_substeps(pre)
            dxs.append(a.x[pre["F"]] - x0)
            rels.append(pre["curiosity"] - a.curiosity[pre["F"]])
    finally:
        sim.policy.choose = real
    dx = np.concatenate(dxs)
    sd_decision = 10.0 * sim.dt_ref * 10  # the decision-level EXPLORE walk
    assert dx.size >= 100
    assert 0.8 < float(dx.std()) / sd_decision < 1.2, (dx.std(), sd_decision)
    msg = "12 explore sub-steps relieve curiosity like one explore decision"
    assert np.allclose(np.concatenate(rels), full, atol=1e-4), msg


def test_trace_has_k_rows_per_decision() -> None:
    sim = _sim(12, days=8.0, trace={"windows": [(2.0, 4.0)]})
    s = sim.run()
    tr = load_trace(s["trace_files"][0])
    assert int(tr["meta"]["decisions_per_day"]) == 72 and int(tr["meta"]["free_substeps"]) == 12
    key = tr["uid"].astype(np.int64) * 100_000 + tr["step"]
    assert np.unique(key).size == key.size, "one row per (individual, sub-step)"
    for u in np.unique(tr["uid"])[:20]:
        st = np.sort(tr["step"][tr["uid"] == u])
        if st.size > 1:
            assert np.all(np.diff(st) == 1), "rows are consecutive sub-steps"
    per = np.bincount(np.unique(tr["uid"], return_inverse=True)[1])
    assert np.all(per % 12 == 0), "K rows per decision for every individual"


if __name__ == "__main__":
    test_off_is_identical_to_default()
    test_substeps_use_their_own_stream_and_move_only_free_agents()
    test_reach_is_preserved_when_every_substep_explores()
    test_trace_has_k_rows_per_decision()
    print("test_substeps: OK")
