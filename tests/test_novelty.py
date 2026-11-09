"""Novelty-based curiosity (P4-14, PHASE4_DESIGN.md 1.10): entering a never-visited bin gives
full relief and staying gives none; a bin revisited after dt gives 1 - exp(-dt / tau); a
spawned slot forgets; non-locomotor actions get no novelty relief; the consequence gain scales
the relief; nothing draws from a random stream; observation v5 reads the bins ahead and behind.
Bit-identity with novelty off and gain 1 is the trajectory-hash run recorded in NOTES."""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.observation import OBS_DIM, ObservationBuilder  # noqa: E402
from universe25.agents.state import (  # noqa: E402
    ACT_EXPLORE,
    ACT_MANIPULATE,
    ACT_RUN_ON,
    ACT_SOCIAL,
)
from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _sim(novelty: bool = True, gain: float = 1.0, days: float = 5.0, K: int = 12,
         physics: bool = True) -> Universe25Sim:
    over = dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=K,
                playground={"ball_physics": physics},
                drives={"curiosity_novelty": novelty, "consequence_gain": gain},
                policy={"kind": "need_driven"})
    return Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over),
                         Path(tempfile.mkdtemp(prefix="u25_nov_")))


def test_config_needs_substeps() -> None:
    try:
        _sim(K=1, physics=False)
    except ValueError as e:
        assert "free_substeps" in str(e)
    else:
        raise AssertionError("novelty-based curiosity at K = 1 must be refused")


def test_entry_stay_revisit_and_spawn() -> None:
    sim = _sim(gain=2.0)
    a = sim.agents
    i = np.flatnonzero(a.alive)[:3]
    a.x[i], a.y[i] = np.array([5.0, 5.0, 5.0]), np.array([5.0, 25.0, 45.0])
    sim._visit_t[i] = -np.inf
    a.curiosity[i] = 0.8
    states = (sim.rng.bit_generator.state, sim._sub_rng.bit_generator.state)
    act = np.array([ACT_EXPLORE, ACT_RUN_ON, ACT_SOCIAL])
    sim._place_novelty(i, act, 10.0, 0.01)
    # locomotor actions entering a never-visited bin: full relief x gain; SOCIAL: none
    assert np.allclose(a.curiosity[i], [0.8 - 0.02, 0.8 - 0.02, 0.8], atol=1e-6), a.curiosity[i]
    # staying in the bin at the same time: no relief
    sim._place_novelty(i[:1], act[:1], 10.0, 0.01)
    assert math.isclose(float(a.curiosity[i[0]]), 0.78, abs_tol=1e-6)
    # revisited after half a day: 1 - exp(-0.5 / tau)
    sim._place_novelty(i[:1], act[:1], 10.5, 0.01)
    expect = 0.78 - 2.0 * 0.01 * (1.0 - math.exp(-0.5 / sim.nov_tau))
    assert math.isclose(float(a.curiosity[i[0]]), expect, abs_tol=1e-6)
    assert (sim.rng.bit_generator.state, sim._sub_rng.bit_generator.state) == states, \
        "novelty draws from no random stream"
    # a spawned slot forgets every place
    slot = int(i[0])
    sim._spawn(slot, sex=0, age=30.0, x=5.0, y=5.0, nest_id=0, cell_id=0, role=1)
    assert np.all(np.isneginf(sim._visit_t[slot]))


def test_object_actions_get_no_place_relief_and_gain_scales_pushes() -> None:
    sim = _sim(gain=3.0)
    a = sim.agents
    i = np.flatnonzero(a.alive)[:1]
    a.x[i], a.y[i] = 5.0, 5.0
    a.curiosity[i] = 0.8
    sim._place_novelty(i, np.array([ACT_MANIPULATE]), 1.0, 0.01)
    assert math.isclose(float(a.curiosity[i[0]]), 0.8, abs_tol=1e-6)
    b = next(o for o in sim.world.play_objects if o.kind == "ball")
    b.x, b.y, b.vx, b.vy = 50.0, 50.0, 0.0, 0.0
    a.x[i], a.y[i] = 49.0, 50.0
    sim._ball_pushes(i, np.array([ACT_MANIPULATE]), np.array([47.0]), np.array([50.0]),
                     0.01, 0.01)
    expect = 0.8 - 3.0 * 0.01 * min(1.0, 2.0 / sim.ball_v_ref)
    assert math.isclose(float(a.curiosity[i[0]]), expect, abs_tol=1e-6)


def test_colony_runs_and_observation_v5() -> None:
    assert OBS_DIM == 59
    sim = _sim(days=30.0, gain=2.0)
    for _ in range(30 * 6):
        sim.step()
    seen = np.isfinite(sim._visit_t[sim.agents.alive]).any(axis=1)
    assert seen.all(), "every living animal has visited a place"
    a = sim.agents
    idx = np.flatnonzero(a.alive)[:4]
    a.x[idx], a.y[idx] = 50.0, 50.0
    a.heading[idx] = np.float32(0.0)  # facing east
    sim._visit_t[idx] = -np.inf
    sim._visit_t[idx, sim.nov_bin(np.array([60.0]), np.array([50.0]))[0]] = sim._nov_t
    o5 = ObservationBuilder(sim.world).build(sim, idx)
    o4 = ObservationBuilder(sim.world, version=4).build(sim, idx)
    assert o5.shape == (idx.size, 59) and np.array_equal(o5[:, :57], o4)
    assert np.allclose(o5[:, 57], 0.0) and np.allclose(o5[:, 58], 1.0), o5[:, 57:]
    off = _sim(novelty=False, days=1.0)
    for _ in range(6):
        off.step()
    i2 = np.flatnonzero(off.agents.alive)
    assert np.all(ObservationBuilder(off.world).build(off, i2)[:, 57:] == 0.0)
    assert off._visit_t is None


if __name__ == "__main__":
    test_config_needs_substeps()
    test_entry_stay_revisit_and_spawn()
    test_object_actions_get_no_place_relief_and_gain_scales_pushes()
    test_colony_runs_and_observation_v5()
    print("test_novelty: OK")
