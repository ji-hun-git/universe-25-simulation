"""Ball physics (P4-13, PHASE4_DESIGN.md 1.9): a push moves a ball along the approach at
kappa * u, the speed decays by the friction factor per sub-step, a bound reflects it with half
the normal speed, tunnels and ramps never move, the object-family relief follows the speed a
contact gave the ball (none when holding still), physics draws from no random stream, and
observation v4 shows the nearest object's mobility and speed. Bit-identity with physics off is
the trajectory-hash run recorded in NOTES; tests/test_determinism.py keeps guarding it."""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.observation import OBS_DIM, OBS_DIM_V3, ObservationBuilder  # noqa: E402
from universe25.agents.state import (  # noqa: E402
    ACT_BACK_OFF,
    ACT_EXPLORE,
    ACT_MANIPULATE,
)
from universe25.config import load_config  # noqa: E402
from universe25.sim import (  # noqa: E402
    BALL_FRICTION_K12,
    BALL_KAPPA,
    BALL_RESTITUTION,
    Universe25Sim,
)


def _sim(physics: bool = True, days: float = 5.0, K: int = 12) -> Universe25Sim:
    over = dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=K,
                playground={"ball_physics": physics}, policy={"kind": "need_driven"})
    return Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over),
                         Path(tempfile.mkdtemp(prefix="u25_phys_")))


def _ball(sim: Universe25Sim):
    return next(o for o in sim.world.play_objects if o.kind == "ball")


def test_config_needs_substeps() -> None:
    try:
        _sim(physics=True, K=1)
    except ValueError as e:
        assert "free_substeps" in str(e)
    else:
        raise AssertionError("ball physics at K = 1 must be refused")


def test_push_roll_bounce_and_no_draws() -> None:
    sim = _sim()
    a = sim.agents
    b = _ball(sim)
    b.x, b.y, b.vx, b.vy = 50.0, 50.0, 0.0, 0.0
    i = np.flatnonzero(a.alive)[:1]
    # the agent moved from 3 in west of the ball to 1 in west (u = 2): push of kappa * 2 east
    a.x[i], a.y[i] = 49.0, 50.0
    cur0 = float(a.curiosity[i[0]])
    states = (sim.rng.bit_generator.state, sim._sub_rng.bit_generator.state)
    sim._ball_pushes(i, np.array([ACT_MANIPULATE]), np.array([47.0]), np.array([50.0]),
                     0.1, 0.1)
    assert math.isclose(b.vx, BALL_KAPPA * 2.0, rel_tol=1e-9) and abs(b.vy) < 1e-12, (b.vx, b.vy)
    rel = cur0 - float(a.curiosity[i[0]])
    expect = 0.1 * min(1.0, BALL_KAPPA * 2.0 / sim.ball_v_ref)
    assert abs(rel - min(expect, cur0)) < 1e-6, (rel, expect)
    f = BALL_FRICTION_K12 ** (12.0 / sim.free_substeps)
    sim._roll_balls()
    assert math.isclose(b.x, 52.0, rel_tol=1e-9), b.x
    assert math.isclose(b.vx, 2.0 * f, rel_tol=1e-9), b.vx
    # reflection at the east bound of the playground
    x1 = sim.world.playground_bounds[2]
    b.x, b.vx = x1 - 0.5, 2.0
    sim._roll_balls()
    assert b.x == x1 and math.isclose(b.vx, -BALL_RESTITUTION * 2.0 * f, rel_tol=1e-9), b.vx
    assert (sim.rng.bit_generator.state, sim._sub_rng.bit_generator.state) == states, \
        "physics draws from no random stream"


def test_holding_still_and_fixed_objects_give_nothing() -> None:
    sim = _sim()
    a = sim.agents
    b = _ball(sim)
    b.x, b.y, b.vx, b.vy = 50.0, 50.0, 0.0, 0.0
    i = np.flatnonzero(a.alive)[:2]
    a.x[i], a.y[i] = np.array([49.0, 51.5]), np.array([50.0, 50.0])
    a.curiosity[i] = 0.8
    # agent 0 held still in contact; agent 1 backed away (u < 0): no push, no relief
    sim._ball_pushes(i, np.array([ACT_MANIPULATE, ACT_BACK_OFF]), np.array([49.0, 50.5]),
                     np.array([50.0, 50.0]), 0.1, 0.1)
    assert b.vx == 0.0 and b.vy == 0.0
    assert np.allclose(a.curiosity[i], 0.8)
    # a locomotor move pushes the ball but earns no object relief
    a.x[i[0]] = 49.0
    sim._ball_pushes(i[:1], np.array([ACT_EXPLORE]), np.array([46.0]), np.array([50.0]),
                     0.1, 0.1)
    assert b.vx > 0.0 and math.isclose(float(a.curiosity[i[0]]), 0.8, rel_tol=1e-6)
    # over a colony run, tunnels and ramps never move
    sim2 = _sim(days=30.0)
    fixed = [(o.x, o.y) for o in sim2.world.play_objects if o.kind != "ball"]
    balls0 = [(o.x, o.y) for o in sim2.world.play_objects if o.kind == "ball"]
    for _ in range(30 * 6):
        sim2.step()
    assert fixed == [(o.x, o.y) for o in sim2.world.play_objects if o.kind != "ball"]
    assert balls0 != [(o.x, o.y) for o in sim2.world.play_objects if o.kind == "ball"], \
        "some ball should have been pushed in 30 days"


def test_observation_v4_motion_fields() -> None:
    assert OBS_DIM == 57 and OBS_DIM_V3 == 55
    sim = _sim(days=20.0)
    for _ in range(20 * 6):
        sim.step()
    b = _ball(sim)
    b.vx, b.vy = 1.0, 0.0
    idx = np.flatnonzero(sim.agents.alive)
    sim.agents.x[idx[:1]], sim.agents.y[idx[:1]] = b.x + 0.5, b.y
    o4 = ObservationBuilder(sim.world).build(sim, idx)
    o3 = ObservationBuilder(sim.world, version=3).build(sim, idx)
    assert o4.shape == (idx.size, 57) and np.array_equal(o4[:, :55], o3)
    assert o4[0, 55] == 1.0 and abs(o4[0, 56] - min(1.0, 1.0 / sim.ball_v_ref)) < 1e-6
    off = _sim(physics=False, days=1.0)
    for _ in range(6):
        off.step()
    i2 = np.flatnonzero(off.agents.alive)
    o_off = ObservationBuilder(off.world).build(off, i2)
    assert np.all(o_off[:, 55:] == 0.0), "no motion fields without physics"


if __name__ == "__main__":
    test_config_needs_substeps()
    test_push_roll_bounce_and_no_draws()
    test_holding_still_and_fixed_objects_give_nothing()
    test_observation_v4_motion_fields()
    print("test_physics: OK")
