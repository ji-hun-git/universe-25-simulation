"""Action space v2 (P4-12, PHASE4_DESIGN.md 1.8): the movement primitives move as designed and
draw nothing; the heuristic never chooses them; observation v3 and the v2 layout; a scripted
alternation of the primitives is seen by the v6 form test and a random v3 network is not
(acceptance check 2). Bit-identity of the existing arms (check 1) is the trajectory-hash run
recorded in NOTES; tests/test_determinism.py and tests/test_policy.py keep guarding it."""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.observation import (  # noqa: E402
    OBS_DIM,
    OBS_DIM_V2,
    OBS_DIM_V3,
    OBS_NAMES,
    ObservationBuilder,
)
from universe25.agents.policy import MlpFrozenPolicy, NeedDrivenPolicy  # noqa: E402
from universe25.agents.state import (  # noqa: E402
    ACT_BACK_OFF,
    ACT_CIRCLE,
    ACT_MANIPULATE,
    ACT_RUN_ON,
    ACT_SOCIAL,
    ACT_TURN_BACK,
    LOCO_FAMILY,
    N_ACTIONS,
    N_BASE_ACTIONS,
    OBJECT_FAMILY,
)
from universe25.config import load_config  # noqa: E402
from universe25.metrics.detectors import FORM_MIN_EXCESS, Z95, detect_trace  # noqa: E402
from universe25.metrics.trace import load_trace  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _sim(days: float, policy: dict, trace=None) -> Universe25Sim:
    over = dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=12, policy=policy)
    if trace is not None:
        over["trace"] = trace
    return Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over),
                         Path(tempfile.mkdtemp(prefix="u25_as2_")))


def test_primitives_move_as_designed_without_draws() -> None:
    sim = _sim(5.0, {"kind": "need_driven"})
    a = sim.agents
    ii = np.flatnonzero(a.alive)[:4]
    a.x[ii], a.y[ii] = 50.0, 50.0
    a.heading[ii] = np.float32(0.5)
    state = sim.rng.bit_generator.state
    sim._heading_moves(ii[:2], np.array([ACT_RUN_ON, ACT_TURN_BACK]), 6.0)
    assert np.allclose([a.x[ii[0]] - 50.0, a.y[ii[0]] - 50.0],
                       [6.0 * math.cos(0.5), 6.0 * math.sin(0.5)], atol=1e-4)
    assert np.allclose([a.x[ii[1]] - 50.0, a.y[ii[1]] - 50.0],
                       [-6.0 * math.cos(0.5), -6.0 * math.sin(0.5)], atol=1e-4)
    o = sim.world.play_objects[0]
    a.x[ii[2:]], a.y[ii[2:]] = o.x + 2.0, o.y  # 2 in east of an object, nearest to it
    sim._object_moves(ii[2:], np.array([ACT_BACK_OFF, ACT_CIRCLE]), 1.4)
    r_back = math.hypot(a.x[ii[2]] - o.x, a.y[ii[2]] - o.y)
    r_circ = math.hypot(a.x[ii[3]] - o.x, a.y[ii[3]] - o.y)
    assert abs(r_back - 3.4) < 1e-3, r_back
    assert abs(r_circ - 2.0) < 1e-3 and a.y[ii[3]] > o.y, (r_circ, a.y[ii[3]])  # ccw
    assert sim.rng.bit_generator.state == state, "the primitives draw nothing"


def test_heuristic_never_chooses_a_v2_action() -> None:
    for mode in ("continue", "rechoose"):
        sim = _sim(40.0, {"kind": "need_driven", "substep_mode": mode})
        seen = np.zeros(N_ACTIONS, dtype=bool)
        for _ in range(40 * 6):
            sim.step()
            al = sim.agents.alive
            seen[sim.agents.recent_action[al]] = True
            seen[sim.agents.last_action[al]] = True
        assert not seen[N_BASE_ACTIONS:].any(), (mode, np.flatnonzero(seen))


def test_observation_v3_and_the_v2_layout() -> None:
    assert OBS_DIM == 59 and OBS_DIM_V3 == 55 and OBS_DIM_V2 == 49
    joined = " ".join(OBS_NAMES).lower().replace("playground", "")
    for bad in ("play", "bout", "motif", "exagger", "score", "reward"):
        assert bad not in joined, bad
    sim = _sim(20.0, {"kind": "need_driven"})
    for _ in range(20 * 6):
        sim.step()
    idx = np.flatnonzero(sim.agents.alive)
    o3 = ObservationBuilder(sim.world, version=3).build(sim, idx)
    o2 = ObservationBuilder(sim.world, version=2).build(sim, idx)
    assert o3.shape == (idx.size, 55) and o2.shape == (idx.size, 49)
    assert np.array_equal(o3[:, :34], o2[:, :34])  # shared blocks up to the object block
    h = sim.agents.heading[idx].astype(np.float64)
    assert np.allclose(o3[:, 53], np.cos(h), atol=1e-6)
    assert np.allclose(o3[:, 54], np.sin(h), atol=1e-6)
    p5 = MlpFrozenPolicy.random_init(7100)  # observation v5 since P4-14
    assert p5.obs_version == 5 and p5.n_out == N_ACTIONS
    w3 = ROOT / "_output" / "as2_reading" / "policy_random_v3_7000.npz"
    if w3.exists():  # a v3 weight file keeps the v3 layout
        assert MlpFrozenPolicy.from_npz(str(w3), 7100).obs_version == 3
    w2 = ROOT / "_output" / "policy_random_v2_7000.npz"
    if w2.exists():  # a v2 weight file keeps the v2 layout and the base actions
        p2 = MlpFrozenPolicy.from_npz(str(w2), 7100)
        assert p2.obs_version == 2 and p2.n_out == N_BASE_ACTIONS


class _Alternator(NeedDrivenPolicy):
    """Test only (never a teacher): the heuristic's decisions; in free-time sub-steps TURN_BACK
    after a locomotor action (a shuttle) and MANIPULATE / BACK_OFF alternation after an object
    action."""

    name = "test_alternator"

    def choose(self, sim, idx, allowed, rng=None):
        if rng is None:
            return super().choose(sim, idx, allowed)
        last = sim.agents.recent_action[idx]
        out = np.full(idx.size, ACT_SOCIAL, np.int8)
        loco = np.isin(last, LOCO_FAMILY)
        obj = np.isin(last, OBJECT_FAMILY)
        out[loco] = ACT_TURN_BACK
        out[obj] = np.where(last[obj] == ACT_MANIPULATE, ACT_BACK_OFF, ACT_MANIPULATE)
        return out


def _form(policy) -> dict:
    sim = _sim(260.0, {"kind": "need_driven", "substep_mode": "rechoose"},
               trace={"windows": [(250.0, 260.0)], "sample_every": 1})
    sim.policy = policy
    for _ in range(260 * 6):
        sim.step()
    return detect_trace(load_trace(sim.trace.close()[0]), n_surrogates=200, seed=3)


def _met(r: dict) -> bool:
    ex = r.get("seq_struct_form_excess_unvalidated", float("nan"))
    z = r.get("seq_struct_form_z_unvalidated", float("nan"))
    return bool(np.isfinite(ex) and np.isfinite(z) and ex >= FORM_MIN_EXCESS and z > Z95)


def test_scripted_alternation_is_seen_and_random_mixing_is_not() -> None:
    alt = _form(_Alternator())
    for kind in ("object", "locomotor"):
        assert _met(alt[kind]), (kind, alt[kind])
        assert alt[kind]["decisions_unvalidated"]["c3_structurally_different"], kind
    rnd = _form(MlpFrozenPolicy.random_init(7100))
    for kind in ("object", "locomotor"):
        assert not _met(rnd[kind]), (kind, rnd[kind])


if __name__ == "__main__":
    test_primitives_move_as_designed_without_draws()
    test_heuristic_never_chooses_a_v2_action()
    test_observation_v3_and_the_v2_layout()
    test_scripted_alternation_is_seen_and_random_mixing_is_not()
    print("test_actions_v2: OK")
