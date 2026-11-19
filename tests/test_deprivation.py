"""U-5, the deprived generation (docs/DEPRIVED_GENERATION.md): refused on Warp and when
independence comes at or after weaning; an expelled or unfed pup old enough is weaned at once and
deprived, a younger one is not; the deprived juvenile forages; the deprived adult is withdrawn,
neither fights nor is fought, is not stressed by crowding, and as a female can still conceive and
be courted. Off, none of this happens."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import (  # noqa: E402
    ACT_AGGRESS,
    ACT_FORAGE,
    ACT_NEST,
    ACT_REST,
    ROLE_JUVENILE,
    ROLE_PUP,
    ROLE_SUBORDINATE_MALE,
    ROLE_WITHDRAWN,
    SEX_F,
    SEX_M,
)
from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


class _FixedDraw:
    """Stands in for the simulation stream where a test needs one outcome."""

    def __init__(self, u: float) -> None:
        self.u = u

    def random(self) -> float:
        return self.u


def _cfg(**over):
    base = {"geometry": {"layout": "calhoun"}, "playground": {"enabled": False}}
    for k, v in over.items():
        base[k] = {**base[k], **v} if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return load_config(ROOT / "configs" / "default.yaml", base)


def _make(on: bool, **bio):
    cfg = _cfg(seed=7100, days=5.0, ticks_per_day=6, backend="numpy", device="cpu",
               log_every_ticks=6, snapshot_every_days=0,
               biology={"aggression_targets": "by_sex", "territories": True,
                        "founder_age_days": 100.0, "first_conception_min_day": 0.0,
                        "breakdown_scope": "individual", "deprivation": on, **bio})
    return Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25dep_"))), cfg


def test_guards() -> None:
    for over in ({"backend": "warp", "geometry": {"layout": "grid"},
                  "biology": {"deprivation": True}},
                 {"biology": {"deprivation": True, "independence_days": 21.0}}):
        try:
            _cfg(**over)
        except ValueError:
            continue
        raise AssertionError(f"{over} must be refused")


def test_independence_and_the_deprived_juvenile() -> None:
    for on in (True, False):
        sim, cfg = _make(on)
        a, bio = sim.agents, cfg.biology
        a.alive[:] = False
        old, young, fed = (int(v) for v in a.free_slots(3))
        for k, age, nest in ((old, 18.0, -1), (young, 10.0, -1), (fed, 19.0, 0)):
            sim._spawn(k, sex=SEX_F, age=age, x=30.0, y=30.0, nest_id=nest, cell_id=0,
                       role=ROLE_PUP)
            a.competence[k] = 0.8
            a.hunger[k] = 0.2
        sim._independence(a.alive.copy())
        if not on:
            assert not sim._deprived.any() and a.role[old] == ROLE_PUP
            continue
        assert sim._deprived[old] and not sim._deprived[young] and not sim._deprived[fed]
        assert np.isclose(a.competence[old], 0.8 * bio.deprived_factor)
        assert a.competence[young] == np.float32(0.8) and a.role[young] == ROLE_PUP
        a.hunger[fed] = bio.independence_hunger + 0.1  # unfed, and old enough: weaned now
        sim._independence(a.alive.copy())
        assert sim._deprived[fed] and a.role[fed] == ROLE_JUVENILE
        sim._assign_roles(a.alive.copy())
        assert a.role[old] == ROLE_JUVENILE and a.role[young] == ROLE_PUP
        # the deprived juvenile forages when hungry; the milk-dependent pup cannot
        a.hunger[[old, young]] = 1.0
        sim.tick = 0
        acts = sim._select_actions(a.alive.copy())
        assert acts[old] == ACT_FORAGE, acts[old]
        assert acts[young] in (ACT_REST, ACT_NEST), acts[young]
        # grown up, it is withdrawn for life
        a.age_days[old] = bio.maturity_days + 1.0
        sim._assign_roles(a.alive.copy())
        assert a.role[old] == ROLE_WITHDRAWN


def test_the_deprived_adult() -> None:
    sim, cfg = _make(True)
    a, bio = sim.agents, cfg.biology
    a.alive[:] = False
    A, B, C = (int(v) for v in a.free_slots(3))
    for k in (A, B, C):
        sim._spawn(k, sex=SEX_M, age=100.0, x=30.0, y=30.0, nest_id=0, cell_id=0, role=0)
    a.rank[[A, B, C]] = (0.9, 0.5, 0.6)
    sim._deprived[B] = True
    a.alive[C] = False
    sim._aggress(A)  # B is the only one near and lower-ranked: no target
    assert not sim._fought[A] and not sim._fought[B]
    sim._aggress(B)
    assert not sim._fought[B]
    a.alive[C] = True
    a.rank[C] = 0.4
    sim._aggress(A)  # an undeprived target is fought
    assert sim._fought[A] and sim._fought[C] and not sim._fought[B]
    # the deprived adult never chooses AGGRESS, however aggressive and stressed
    a.alive[[A, C]] = False
    a.aggression[B], a.stress[B], a.energy[B] = 1.5, 1.5, 0.9
    a.hunger[B] = a.thirst[B] = a.fatigue[B] = 0.0
    picks = set()
    for t in range(200):
        sim.tick = t * sim.ticks_per_decision
        picks.add(int(sim._select_actions(a.alive.copy())[B]))
    assert ACT_AGGRESS not in picks, picks
    # crowding does not stress him: in a packed cell his stress falls, another's rises
    a.alive[:] = False
    crowd = [int(v) for v in a.free_slots(300)]
    for k in crowd:
        sim._spawn(k, sex=SEX_M, age=100.0, x=30.0, y=30.0, nest_id=0, cell_id=0, role=0)
    dep, ctl = crowd[0], crowd[1]
    sim._deprived[dep] = True
    a.stress[[dep, ctl]] = 0.5
    for _ in range(12):
        sim._density_stress(a.alive.copy())
    assert a.stress[dep] < 0.5 < a.stress[ctl], (a.stress[dep], a.stress[ctl])


def test_the_deprived_female_conceives_and_is_courted() -> None:
    got = {}
    for on in (True, False):
        sim, cfg = _make(on)
        a = sim.agents
        f = int(np.flatnonzero(a.alive & (a.sex == SEX_F))[0])
        m = int(np.flatnonzero(a.alive & (a.sex == SEX_M))[0])
        a.cell_id[[f, m]] = 2
        a.stress[[f, m]] = 0.0
        a.energy[f] = 0.9
        sim._deprived[f] = on
        a.competence[f], a.role[f] = 0.3, ROLE_WITHDRAWN
        sim._set_owner(2, m, set())
        sim.rng, real = _FixedDraw(1e-4), sim.rng
        sim._daily_breeding_pass(a.alive.copy())
        sim.rng = real
        got[on] = bool(a.gestating[f] > 0)
        # courtship: a male approaches her only when she is deprived and the switch is on
        a.alive[:] = False
        a.alive[[f, m]] = True
        a.gestating[f] = 0.0
        a.x[f], a.y[f], a.x[m], a.y[m] = 20.0, 20.0, 30.0, 20.0
        a.role[m] = ROLE_SUBORDINATE_MALE
        sim._approach_mate(m)
        assert (a.x[m] < 30.0) == on, (on, a.x[m])
    assert got == {True: True, False: False}, got


if __name__ == "__main__":
    test_guards()
    test_independence_and_the_deprived_juvenile()
    test_the_deprived_adult()
    test_the_deprived_female_conceives_and_is_courted()
    print("test_deprivation: OK")
