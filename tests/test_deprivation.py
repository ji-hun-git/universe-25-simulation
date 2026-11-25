"""U-5, the deprived generation (docs/DEPRIVED_GENERATION.md): refused on Warp and when
independence comes at or after weaning; an expelled or unfed pup old enough is weaned at once and
deprived, a younger one is not; the deprived juvenile forages; the deprived adult is withdrawn,
neither fights nor is fought, is not stressed by crowding, and as a female can still conceive and
be courted. Off, none of this happens."""
from __future__ import annotations

import math
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
    ROLE_BREEDING_FEMALE,
    ROLE_JUVENILE,
    ROLE_NURSING,
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
                 {"biology": {"deprivation": True, "independence_days": 21.0}},
                 {"biology": {"deprived_fertility": 0.01}},
                 {"biology": {"expel_at_independence": True}},
                 {"biology": {"colony_rejection": True}},
                 {"biology": {"deprivation": True, "rejection_all_boxes": True}},
                 {"biology": {"deprivation": True, "rejection_stress": True}},
                 {"biology": {"deprivation": True, "rejection_erosion_stress": 0.5}}):
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


def test_revision_1_fertility() -> None:
    """Revision 1, lever 1: with deprived_fertility her daily chance is that fraction of an
    undeprived female's (here p_base x 0.01), not her competence (0.3)."""
    for fert, draw, conceives in ((None, 0.02, True), (0.01, 0.02, False),
                                  (0.01, 0.002, True)):
        sim, cfg = _make(True, deprived_fertility=fert)
        a, bio = sim.agents, cfg.biology
        f = int(np.flatnonzero(a.alive & (a.sex == SEX_F))[0])
        m = int(np.flatnonzero(a.alive & (a.sex == SEX_M))[0])
        a.cell_id[[f, m]] = 2
        a.stress[[f, m]] = 0.0
        a.energy[f] = 0.9
        a.competence[m] = a.courtship_cap[m] = a.maternal_cap[f] = 1.0
        sim._deprived[f] = True
        a.competence[f], a.role[f] = 0.3, ROLE_WITHDRAWN
        sim._set_owner(2, m, set())
        sim.rng, real = _FixedDraw(draw), sim.rng
        sim._daily_breeding_pass(a.alive.copy())
        sim.rng = real
        assert bool(a.gestating[f] > 0) == conceives, (fert, draw, bio.breeding_p_base)


def test_revision_1_expulsion() -> None:
    """Revision 1, lever 2: a stressed nursing mother expels the pups of her box that are old
    enough and keeps nursing the younger ones; without the lever she nurses none of them."""
    for expel in (True, False):
        sim, cfg = _make(True, expel_at_independence=expel, litter_abandon_p=0.0)
        a, bio = sim.agents, cfg.biology
        a.alive[:] = False
        mom, old, young = (int(v) for v in a.free_slots(3))
        sim._spawn(mom, sex=SEX_F, age=120.0, x=30.0, y=30.0, nest_id=0, cell_id=0, role=0)
        for k, age in ((old, 18.0), (young, 10.0)):
            sim._spawn(k, sex=SEX_M, age=age, x=30.0, y=30.0, nest_id=0, cell_id=0,
                       role=ROLE_PUP)
            a.hunger[k] = 0.9
        a.role[mom], a.maternal[mom] = ROLE_NURSING, 0.9
        a.stress[mom] = bio.maternal_neglect_stress + 0.1
        sim.tick = 0
        sim._daily_litter_abandonment(a.alive.copy())
        assert (a.nest_id[old] < 0) == expel and a.nest_id[young] == 0
        sim._passive_nurse(a.alive.copy())
        assert (a.hunger[young] < 0.9) == expel, (expel, a.hunger[young])


class _Draws:
    """A vectorized stand-in for the simulation stream; raises when it should not be drawn."""

    def __init__(self, u: float | None) -> None:
        self.u = u

    def random(self, size=None):
        if self.u is None:
            raise AssertionError("no draw expected")
        return self.u if size is None else np.full(size, self.u)


def test_revision_2_colony_rejection() -> None:
    """Revision 2: from the colony's breakdown on, a box's pups of independence age are expelled
    with chance f; below the trigger there is no draw; with the ratchet f does not relax."""
    for ratchet in (True, False):
        sim, cfg = _make(True, colony_rejection=True, rejection_ratchet=ratchet,
                         litter_abandon_p=0.0)
        a = sim.agents
        a.alive[:] = False
        mom, old, young = (int(v) for v in a.free_slots(3))
        sim._spawn(mom, sex=SEX_F, age=120.0, x=30.0, y=30.0, nest_id=0, cell_id=0, role=0)
        for k, age in ((old, 18.0), (young, 10.0)):
            sim._spawn(k, sex=SEX_M, age=age, x=30.0, y=30.0, nest_id=0, cell_id=0,
                       role=ROLE_PUP)
        a.role[mom], a.maternal[mom], a.stress[mom] = ROLE_NURSING, 0.9, 0.0
        sim.tick = 0
        real = sim.rng
        sim._breakdown_density = lambda alive: 0.0  # below the trigger: no draw
        sim.rng = _Draws(None)
        sim._colony_rejection(a.alive.copy())
        assert a.nest_id[old] == 0 and sim._rejection_onset is None
        sim._breakdown_density = lambda alive: 10.0  # far above it: f = 1
        sim.rng = _Draws(0.99)
        sim._colony_rejection(a.alive.copy())
        assert a.nest_id[old] < 0 and a.nest_id[young] == 0
        assert sim._rejection_onset == sim.day and sim._rejection_f_max == 1.0
        a.nest_id[old] = 0  # the next day the colony has thinned: f falls to 0
        sim._breakdown_density = lambda alive: 0.0
        sim.rng = _Draws(0.99 if ratchet else None)
        sim._colony_rejection(a.alive.copy())
        assert (a.nest_id[old] < 0) == ratchet, ratchet
        sim.rng = real


def test_revision_3_every_box() -> None:
    """Revision 3: colony rejection also reaches a box whose mother has lost the nursing role."""
    for every in (True, False):
        sim, cfg = _make(True, colony_rejection=True, rejection_all_boxes=every,
                         litter_abandon_p=0.0)
        a = sim.agents
        a.alive[:] = False
        mom, old = (int(v) for v in a.free_slots(2))
        sim._spawn(mom, sex=SEX_F, age=120.0, x=30.0, y=30.0, nest_id=0, cell_id=0, role=0)
        sim._spawn(old, sex=SEX_M, age=18.0, x=30.0, y=30.0, nest_id=0, cell_id=0,
                   role=ROLE_PUP)
        a.role[mom], a.maternal[mom] = ROLE_BREEDING_FEMALE, 0.3  # not the nursing role
        sim.tick = 0
        sim._breakdown_density = lambda alive: 10.0
        sim.rng, real = _Draws(0.5 if every else None), sim.rng
        sim._colony_rejection(a.alive.copy())
        sim.rng = real
        assert (a.nest_id[old] < 0) == every, every


def test_revision_4_colony_stress() -> None:
    """Revision 4: with rejection_stress, an undeprived animal's stress gain rises by
    social_breakdown_stress_boost x f, the day's rejection chance; the deprived adult's does not,
    and a pup's competence (the developmental term) is untouched."""
    out = {}
    for on in (False, True):
        sim, cfg = _make(True, colony_rejection=True, rejection_stress=on,
                         social_breakdown_stress_boost=0.25)
        a = sim.agents
        a.alive[:] = False
        adult, dep, pup = (int(v) for v in a.free_slots(3))
        for k, sex, age, role in ((adult, SEX_F, 120.0, 0), (dep, SEX_M, 120.0, 0),
                                  (pup, SEX_M, 10.0, ROLE_PUP)):
            sim._spawn(k, sex=sex, age=age, x=30.0, y=30.0, nest_id=0, cell_id=0, role=role)
        sim._deprived[dep] = True
        a.stress[[adult, dep, pup]] = 0.0
        a.competence[pup] = 0.8
        sim._rejection_f = 0.5
        sim._density_stress(a.alive.copy())
        out[on] = (a.stress[[adult, dep, pup]].astype(float), float(a.competence[pup]))
    relax = -math.expm1(-cfg.drives.stress_decay * sim.dt_days)
    want = 0.25 * 0.5 / cfg.drives.stress_decay * relax
    d = out[True][0] - out[False][0]
    assert abs(d[0] - want) < 1e-5 and abs(d[2] - want) < 1e-5 and d[1] == 0.0, (d, want)
    assert out[True][1] == out[False][1]



def test_revision_5_erosion_from_the_trigger() -> None:
    """Revision 5: from the day the rejection trigger first fires, maternal erosion uses
    rejection_erosion_stress; before it, and with it unset, maternal_erosion_stress stands."""
    for thr in (None, 0.5):
        sim, cfg = _make(True, colony_rejection=True, rejection_erosion_stress=thr,
                         maternal_erosion_rate=0.2, maternal_erosion_stress=0.8)
        a = sim.agents
        a.alive[:] = False
        f = int(a.free_slots(1)[0])
        sim._spawn(f, sex=SEX_F, age=120.0, x=30.0, y=30.0, nest_id=0, cell_id=0, role=0)
        a.stress[f], a.maternal_cap[f], a.maternal[f] = 0.6, 1.0, 0.9
        sim.tick = 0
        sim._daily_maternal_erosion(a.alive.copy())  # before the trigger: 0.6 < 0.8
        assert a.maternal_cap[f] == 1.0
        sim._rejection_onset = 430.0
        sim._daily_maternal_erosion(a.alive.copy())
        want = 1.0 - 0.2 * (0.6 - 0.5) if thr is not None else 1.0
        assert abs(float(a.maternal_cap[f]) - want) < 1e-5, (thr, a.maternal_cap[f])
        assert float(a.maternal[f]) <= float(a.maternal_cap[f]) + 1e-7


if __name__ == "__main__":
    test_guards()
    test_independence_and_the_deprived_juvenile()
    test_the_deprived_adult()
    test_the_deprived_female_conceives_and_is_courted()
    test_revision_1_fertility()
    test_revision_1_expulsion()
    test_revision_2_colony_rejection()
    test_revision_3_every_box()
    test_revision_4_colony_stress()
    test_revision_5_erosion_from_the_trigger()
    print("test_deprivation: OK")
