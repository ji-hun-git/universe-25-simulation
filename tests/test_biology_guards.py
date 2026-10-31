"""Life-history guards: no immature conceptions, milk-dependent pups, bounded competence.

Regression for the phase-2 "pup mill": a zero softmax utility still carried probability, so
pups foraged, fought and conceived (median gestating age was 15 days). These tests pin the
fixes. Also checks Warp density-stress/imprinting parity against the NumPy reference.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import (  # noqa: E402
    ACT_NEST,
    ACT_REST,
    ROLE_NURSING,
    ROLE_PUP,
    SEX_F,
)
from universe25.config import SimConfig  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _make_sim(seed: int = 7100, days: float = 200.0, out: str = "test_bio") -> Universe25Sim:
    cfg = SimConfig(
        seed=seed,
        days=days,
        ticks_per_day=6,
        backend="numpy",
        device="cpu",
        max_agents=1024,
        log_every_ticks=10**9,
        snapshot_every_days=0,
        arm_label="TRACK-E-U25-TEST",
    )
    # fast growth so the checks see many pups / juveniles
    cfg.biology.first_conception_min_day = 60.0
    cfg.biology.breeding_p_base = 0.5
    return Universe25Sim(cfg, ROOT / "_output" / out)


def test_no_immature_conception_and_pup_actions() -> None:
    sim = _make_sim()
    a = sim.agents
    bio = sim.cfg.biology
    total = int(sim.cfg.days * sim.cfg.ticks_per_day)
    n_pup_ticks = 0
    n_gest_checks = 0
    comp_prev = None
    for _ in range(total):
        sim.step()
        alive = a.alive
        gest = alive & (a.gestating > 0)
        # no female conceives before maturity (gestation shorter than maturity, so any
        # gestating individual must be at least maturity_days old)
        assert not np.any(a.age_days[gest] < bio.maturity_days), (
            "immature gestation", a.age_days[gest].min()
        )
        # gestating individuals are female
        assert np.all(a.sex[gest] == 0)
        n_gest_checks += int(gest.sum())
        # pre-weaning pups only rest / stay at the nest
        pup = alive & (a.role == ROLE_PUP)
        if pup.any():
            acts = a.last_action[pup]
            assert np.all((acts == ACT_REST) | (acts == ACT_NEST)), np.unique(acts)
            n_pup_ticks += int(pup.sum())
        # competence stays in [0, 1] and is frozen for adults
        comp = a.competence
        assert np.all(comp[alive] >= 0.0) and np.all(comp[alive] <= 1.0)
        adult = alive & (a.age_days >= bio.maturity_days + 1.0)
        if comp_prev is not None:
            # adults alive at both ticks keep their competence
            both = adult & comp_prev[1]
            assert np.allclose(comp[both], comp_prev[0][both]), "adult competence changed"
        comp_prev = (comp.copy(), adult.copy())
    assert sim._births > 50, sim._births
    assert n_pup_ticks > 0 and n_gest_checks > 0
    assert sim._nan_count == 0


def test_last_surviving_young_tracks_weaned_cohorts() -> None:
    from universe25.metrics.calibration import surviving_birth_cessation_day

    sim = _make_sim(days=150.0, out="test_bio_ly")
    summary = sim.run()
    bio = sim.cfg.biology
    # rate-based cessation: never after the strict latest weaned pup, counts every weaning
    assert sim._surv_births_cum == int(sim._surv_births_by_day.sum()) > 0
    cess = summary["surviving_birth_cessation_day"]
    assert 0.0 < cess <= sim._last_surviving_young_day + 1e-6, (cess, sim._last_surviving_young_day)
    assert int(sim._conc_by_day.sum()) == sim._conceptions > 0
    assert 0.0 < summary["conception_cessation_day"] <= sim._last_conception_day + 1e-6
    # synthetic: a steady rate then a single late straggler -> cessation ignores the straggler
    hist = np.zeros(400, dtype=np.int64)
    hist[100:300] = 20
    hist[390] = 1
    assert surviving_birth_cessation_day(hist) == 299.0
    assert surviving_birth_cessation_day(np.zeros(10)) == 0.0
    # a surviving birth is at most (day - weaning) and never after the last birth of any kind
    assert sim._last_surviving_young_day <= sim.day - bio.weaning_days + 1e-6
    assert sim._last_surviving_young_day <= sim._last_young_day + 1e-6
    assert sim._last_surviving_young_day > 0.0


def test_resolution_scaling() -> None:
    """Per-decision scale is exactly 1 at the reference resolution and movement reach is fixed."""
    s6 = _make_sim(days=1.0, out="test_bio_res6")
    cfg24 = SimConfig(seed=7100, days=1.0, ticks_per_day=24, backend="numpy", device="cpu",
                      max_agents=64, log_every_ticks=10**9, snapshot_every_days=0,
                      arm_label="TRACK-E-U25-TEST")
    s24 = Universe25Sim(cfg24, ROOT / "_output" / "test_bio_res24")
    assert s6.k_ev == 1.0 and abs(s24.k_ev - 0.25) < 1e-12
    # a decision lasts 1/6 day at both resolutions; per-decision reach is the same
    assert s6.ticks_per_decision == 1 and s24.ticks_per_decision == 4
    assert s6.dt_ref == s24.dt_ref == 1.0 / 6.0
    assert s6.reach == s24.reach == 4.0
    # per-tick rates written per decision (nest kick, social decrement): tpd * k constant
    assert abs(6 * s6.k_ev - 24 * s24.k_ev) < 1e-12


def test_warp_density_stress_parity() -> None:
    """Warp density_stress_kernel == NumPy _density_stress on identical state (stress, competence)."""
    try:
        import warp as wp
    except Exception:
        print("skip: warp missing")
        return
    wp.init()
    if not any(getattr(d, "is_cuda", False) for d in wp.get_devices()):
        print("skip: no CUDA device")
        return
    from universe25.warp_kernels.engine import WarpTickEngine
    from universe25.warp_kernels.kernels import density_stress_kernel

    sim = _make_sim(days=180.0, out="test_bio_parity")
    a = sim.agents
    for _ in range(int(180 * sim.cfg.ticks_per_day)):
        sim.step()
    assert a.n_alive > 40, a.n_alive
    # crank up imprinting so the competence path is exercised
    bio = sim.cfg.biology
    bio.imprint_rate = 0.5
    bio.imprint_density_threshold = 0.0
    # put the weaned density inside the breakdown ramp so the graded-boost branch is exercised
    bio.breakdown_density_threshold = 1.0
    bio.breakdown_density_ramp = 1.0
    bio.social_breakdown_stress_boost = 0.5
    f_bd = bio.breakdown_factor(sim._breakdown_density(a.alive))
    assert 0.0 < f_bd < 1.0, f_bd
    d = sim.cfg.drives

    # NumPy reference on a copy (disable the random nest kick by fixing rank high)
    a.rank[:] = 0.9
    ref_stress = a.stress.copy()
    ref_comp = a.competence.copy()
    snapshot = {k: getattr(a, k).copy() for k in ("stress", "competence", "social_drive", "nest_id")}
    sim._density_stress(a.alive)
    ref_stress[:] = a.stress
    ref_comp[:] = a.competence
    ref_social = a.social_drive.copy()
    for k, v in snapshot.items():
        getattr(a, k)[:] = v

    eng = WarpTickEngine(cfg=sim.cfg, world=sim.world, device="cuda:0", use_graph=False)
    eng._host_cell_nest_counts(a)
    eng.upload(a, sim.rng)
    b = eng._bufs
    b["dens_social"].assign(np.array([sim._breakdown_density(a.alive)], dtype=np.float32))
    b["event_scale"].assign(np.array([1.0], dtype=np.float32))  # a decision tick
    cap_cell = float(sim.world.capacity_design / max(1, sim.world.n_cells))
    wp.launch(
        density_stress_kernel,
        dim=a.capacity,
        inputs=[
            b["alive"], b["cell_id"], b["nest_id"], b["rank"], b["stress"], b["social_drive"],
            b["cell_counts"], b["nest_occ"], b["nest_cap"], b["age_days"], b["competence"],
            float(sim.dt_days), float(d.stress_density_gain), float(d.stress_decay),
            float(bio.nest_overcrowd_stress), cap_cell, b["dens_social"],
            float(bio.breakdown_threshold()), float(bio.breakdown_density_ramp),
            float(bio.social_breakdown_stress_boost),
            float(bio.maturity_days), float(bio.imprint_rate), float(bio.imprint_density_threshold),
            b["event_scale"],
        ],
        device=eng.device,
    )
    wp.synchronize()
    alive = a.alive
    w_stress = b["stress"].numpy()[alive]
    w_comp = b["competence"].numpy()[alive]
    w_social = b["social_drive"].numpy()[alive]
    ds = np.max(np.abs(w_stress - ref_stress[alive]))
    dc = np.max(np.abs(w_comp - ref_comp[alive]))
    dso = np.max(np.abs(w_social - ref_social[alive]))
    assert ds < 1e-5, f"stress parity {ds}"
    assert dc < 1e-5, f"competence parity {dc}"
    assert dso < 1e-5, f"social parity {dso}"
    assert np.any(ref_comp[alive] < 1.0), "imprinting path not exercised"
    print(f"warp parity max|dstress|={ds:.2e} max|dcomp|={dc:.2e} n={int(alive.sum())}")


def test_decisions_are_held_between_decision_ticks() -> None:
    """At 24 ticks/day an agent re-decides every 4 ticks and keeps its action in between."""
    cfg = SimConfig(seed=7100, days=30.0, ticks_per_day=24, backend="numpy", device="cpu",
                    max_agents=512, log_every_ticks=10**9, snapshot_every_days=0,
                    arm_label="TRACK-E-U25-TEST")
    cfg.biology.first_conception_min_day = 10.0
    sim = Universe25Sim(cfg, ROOT / "_output" / "test_bio_hold")
    a = sim.agents
    changes_between = 0
    changes_at = 0
    prev = None
    for _ in range(int(30 * 24)):
        decision_tick = (sim.tick % sim.ticks_per_decision) == 0
        sim.step()
        cur = (a.last_action.copy(), a.alive.copy())
        if prev is not None:
            both = prev[1] & cur[1]
            diff = int(np.sum(cur[0][both] != prev[0][both]))
            if decision_tick:
                changes_at += diff
            else:
                changes_between += diff
        prev = cur
    assert changes_between == 0, changes_between
    assert changes_at > 0


def test_relaxation_feeding_composes_over_substeps() -> None:
    """Nursing relief is exp(-rate*w*dt): four 1/24-day contacts equal one 1/6-day contact."""
    sim = _make_sim(days=1.0, out="test_bio_feed")
    a = sim.agents
    bio = sim.cfg.biology
    nest = sim.world.nests[0]
    slots = np.asarray(a.free_slots(9), dtype=int)
    for s_ in slots:
        sim._spawn(int(s_), sex=SEX_F, age=200.0, x=nest.x, y=nest.y, nest_id=0,
                   cell_id=nest.cell_id, role=ROLE_NURSING)
    mom = slots[:2]
    pups = slots[2:9]  # 6 pups of box 0 (= nurse_max_pups, full share) + 1 pup of box 1
    a.sex[mom] = SEX_F
    a.role[mom] = ROLE_NURSING
    a.age_days[mom] = 200.0
    a.nest_id[mom] = 0
    a.maternal[mom] = [0.9, 0.6]
    a.x[mom] = nest.x
    a.y[mom] = nest.y
    a.role[pups] = ROLE_PUP
    a.age_days[pups] = 5.0
    a.nest_id[pups] = 0
    a.x[pups] = nest.x + 1.0
    a.y[pups] = nest.y
    a.hunger[pups] = 0.9
    a.thirst[pups] = 0.8
    a.energy[pups] = 0.3
    # one pup belongs to another box: untouched
    a.nest_id[pups[-1]] = 1
    snap = {k: getattr(a, k).copy() for k in ("hunger", "thirst", "energy")}

    sim._feed_by_nest(mom, pups, radius2=64.0, dt=1.0 / 6.0)
    once = {k: getattr(a, k).copy() for k in snap}
    for k, v in snap.items():
        getattr(a, k)[:] = v
    for _ in range(4):
        sim._feed_by_nest(mom, pups, radius2=64.0, dt=1.0 / 24.0)
    for k in snap:
        assert np.allclose(getattr(a, k)[pups], once[k][pups], atol=1e-6), k
    fed = pups[:-1]
    share = 6.0 / 6.0  # 6 pups of box 0 in contact -> full share
    w = (0.9 + 0.6) * share
    f = np.exp(-bio.nurse_rate_per_day * w / 6.0)
    assert np.allclose(once["hunger"][fed], 0.9 * f, atol=1e-6)
    assert np.allclose(once["thirst"][fed], 0.8 * f, atol=1e-6)
    assert np.allclose(once["energy"][fed], 1.0 - 0.7 * f, atol=1e-6)
    assert once["hunger"][pups[-1]] == np.float32(0.9), "pup of another box was fed"
    assert np.all(once["hunger"][fed] > 0.0), "relief must not clip to zero"


def test_maternal_erosion_is_weaned_only_and_irreversible() -> None:
    sim = _make_sim(days=1.0, out="test_bio_erode")
    a = sim.agents
    bio = sim.cfg.biology
    bio.maternal_erosion_rate = 0.1
    bio.maternal_erosion_stress = 0.5
    alive = np.flatnonzero(a.alive)
    adult_f, young_f, calm_f = alive[0], alive[1], alive[2]
    a.sex[[adult_f, young_f, calm_f]] = SEX_F
    a.age_days[adult_f] = 300.0
    a.age_days[young_f] = bio.weaning_days - 5.0  # unweaned pup: not exposed
    a.age_days[calm_f] = 300.0
    a.stress[[adult_f, young_f]] = 0.9
    a.stress[calm_f] = 0.4
    a.maternal[[adult_f, young_f, calm_f]] = 0.9
    a.maternal_cap[:] = 1.0
    sim.tick = sim.cfg.ticks_per_day  # day boundary
    sim._daily_maternal_erosion(a.alive)
    expect = 1.0 - 0.1 * (0.9 - 0.5)
    assert abs(float(a.maternal_cap[adult_f]) - expect) < 1e-6, a.maternal_cap[adult_f]
    assert a.maternal_cap[young_f] == 1.0 and a.maternal_cap[calm_f] == 1.0
    assert abs(float(a.maternal[adult_f]) - 0.9) < 1e-6  # still below the cap
    # cap binds the investment once it falls below it
    for _ in range(12):
        sim._daily_maternal_erosion(a.alive)
    assert float(a.maternal[adult_f]) <= float(a.maternal_cap[adult_f]) + 1e-7
    assert float(a.maternal_cap[adult_f]) < 0.6
    # not at a day boundary: nothing happens; low stress later: no recovery
    cap_before = float(a.maternal_cap[adult_f])
    sim.tick += 1
    sim._daily_maternal_erosion(a.alive)
    assert float(a.maternal_cap[adult_f]) == cap_before
    sim.tick = 2 * sim.cfg.ticks_per_day
    a.stress[adult_f] = 0.1
    sim._daily_maternal_erosion(a.alive)
    assert float(a.maternal_cap[adult_f]) == cap_before, "maternal capacity must not recover"
    # births and conceptions respect the cap
    a.competence[adult_f] = 1.0
    a.gestating[adult_f] = sim.dt_days / 2
    a.nest_id[adult_f] = 0
    sim._reproduce(a.alive)
    assert float(a.maternal[adult_f]) <= 0.9 * cap_before + 1e-6


def test_breakdown_pressure_ramp_is_graded_and_step_at_zero_width() -> None:
    from universe25.config import BiologyConfig

    bio = BiologyConfig(breakdown_density_threshold=0.6, breakdown_density_ramp=0.0)
    assert bio.breakdown_factor(0.59) == 0.0 and bio.breakdown_factor(0.61) == 1.0, "step"
    bio = BiologyConfig(breakdown_density_threshold=0.6, breakdown_density_ramp=0.3)
    assert bio.breakdown_factor(0.2) == 0.0, "below the ramp"
    assert abs(bio.breakdown_factor(0.45) - 0.5) < 1e-12, "half way up the ramp"
    assert bio.breakdown_factor(0.6) == 1.0 and bio.breakdown_factor(0.9) == 1.0
    f = [bio.breakdown_factor(x) for x in np.linspace(0.3, 0.6, 7)]
    assert all(b >= a for a, b in zip(f, f[1:])), "monotone in density"
    # In the sim: with the ramp the stress gain already rises below the threshold.
    sim = _make_sim(days=1.0, out="test_bio_ramp")
    a = sim.agents
    b2 = sim.cfg.biology
    b2.breakdown_density_threshold = 1.0  # never reached by 8 founders ...
    b2.social_breakdown_stress_boost = 0.5
    b2.breakdown_density_ramp = 0.0
    a.rank[:] = 0.9  # no nest kick
    s0 = a.stress.copy()
    sim._density_stress(a.alive)
    step_stress = a.stress.copy()
    a.stress[:] = s0
    b2.breakdown_density_ramp = 1.0  # ... but the ramp spans the whole density range
    sim._density_stress(a.alive)
    assert np.all(a.stress[a.alive] > step_stress[a.alive] + 1e-7), "ramp adds pressure early"


def test_fertility_floor_scales_conception_with_maternal_cap() -> None:
    """fertility_cap_floor 0 + maternal_cap 0 -> no conceptions; floor 1 -> the usual rate."""
    from universe25.agents.state import SEX_M

    def run(floor: float, cap: float) -> int:
        sim = _make_sim(days=1.0, out="test_bio_fert")
        a = sim.agents
        bio = sim.cfg.biology
        bio.first_conception_min_day = 0.0
        bio.fertility_cap_floor = floor
        for s in a.free_slots(40):
            sim._spawn(int(s), sex=0, age=200.0, x=10.0, y=10.0, nest_id=0, cell_id=0, role=0)
        alive = np.flatnonzero(a.alive)
        a.age_days[alive] = 200.0
        a.sex[alive] = SEX_F
        a.sex[alive[:8]] = SEX_M
        a.x[alive] = 10.0
        a.y[alive] = 10.0
        a.cell_id[alive] = 0
        a.stress[alive] = 0.1
        a.energy[alive] = 1.0
        a.gestating[alive] = 0.0
        a.competence[alive] = 1.0
        a.courtship_cap[alive] = 1.0
        a.maternal_cap[alive] = cap
        a.role[alive] = 0
        sim._assign_roles(a.alive)
        before = sim._conceptions
        for day in range(1, 11):
            sim.tick = day * sim.cfg.ticks_per_day
            sim.day = float(day)
            sim._daily_breeding_pass(a.alive)
        return sim._conceptions - before

    assert run(0.0, 0.0) == 0, "eroded females with floor 0 never conceive"
    assert run(1.0, 0.0) > 5, "floor 1 = off: capacity does not matter"
    assert run(0.0, 1.0) > 5, "intact females conceive at floor 0"


def test_conception_density_suppression_is_graded_per_cell() -> None:
    """Conception factor: 1 below the onset, linear to 0 at onset + width; off at width 0."""
    from universe25.agents.state import SEX_M

    sim = _make_sim(days=1.0, out="test_bio_concdens")
    a = sim.agents
    bio = sim.cfg.biology
    bio.first_conception_min_day = 0.0
    for s in a.free_slots(80):  # crowd cell 0: 88 mice -> local density 88 / 240 = 0.367
        sim._spawn(int(s), sex=0, age=200.0, x=10.0, y=10.0, nest_id=0, cell_id=0, role=0)
    alive = np.flatnonzero(a.alive)
    a.sex[alive] = SEX_F
    a.sex[alive[:8]] = SEX_M
    a.age_days[alive] = 200.0
    a.x[alive] = 10.0
    a.y[alive] = 10.0
    a.cell_id[alive] = 0
    a.stress[alive] = 0.1
    a.energy[alive] = 1.0
    a.competence[alive] = 1.0
    a.courtship_cap[alive] = 1.0
    a.maternal_cap[alive] = 1.0
    a.gestating[alive] = 0.0
    a.role[alive] = 0
    sim._assign_roles(a.alive)
    sim.tick += 1
    females = alive[8:]
    local = alive.size / (sim.world.capacity_design / sim.world.n_cells)
    bio.conception_density_width = 0.2
    bio.conception_density_onset = local + 0.1
    assert np.all(sim._conception_density_factor(females) == 1.0), "below the onset"
    bio.conception_density_onset = local - 0.1
    f = sim._conception_density_factor(females)
    assert np.allclose(f, 0.5), f[:3]
    bio.conception_density_onset = local - 0.3
    assert np.all(sim._conception_density_factor(females) == 0.0), "beyond onset + width"
    # in the breeding pass: fully suppressed cell conceives nothing; width 0 is off
    before = sim._conceptions
    for day in range(1, 11):
        sim.tick = day * sim.cfg.ticks_per_day
        sim.day = float(day)
        sim._daily_breeding_pass(a.alive)
    assert sim._conceptions == before, "no conceptions in a fully suppressed cell"
    bio.conception_density_width = 0.0
    for day in range(11, 21):
        sim.tick = day * sim.cfg.ticks_per_day
        sim.day = float(day)
        sim._daily_breeding_pass(a.alive)
    assert sim._conceptions > before + 5, "width 0 = off"


def test_nursing_disturbance_is_graded_in_cell_density() -> None:
    """A mother in a crowded cell nurses less with nurse_disturb_coef > 0; off at 0."""
    sim = _make_sim(days=1.0, out="test_bio_disturb")
    a = sim.agents
    bio = sim.cfg.biology
    # crowd cell 0 with weaned bystanders
    for s in a.free_slots(60):
        sim._spawn(int(s), sex=0, age=100.0, x=5.0, y=5.0, nest_id=3, cell_id=0, role=0)
    alive = np.flatnonzero(a.alive)
    mom, pup = alive[0], alive[1]
    a.sex[mom] = SEX_F
    a.age_days[mom] = 200.0
    a.maternal[mom] = 0.9
    a.nest_id[[mom, pup]] = 7
    a.age_days[pup] = 5.0
    a.role[pup] = ROLE_PUP
    a.x[[mom, pup]] = 5.0
    a.y[[mom, pup]] = 5.0
    a.cell_id[[mom, pup]] = 0
    sim.tick += 1

    def relief(coef: float, onset: float) -> float:
        bio.nurse_disturb_coef = coef
        bio.nurse_disturb_density = onset
        a.hunger[pup] = 1.0
        sim._feed_by_nest(np.array([mom]), np.array([pup]), radius2=25.0, dt=sim.dt_days)
        return 1.0 - float(a.hunger[pup])

    base = relief(0.0, 0.15)
    assert base > 0.1
    assert abs(relief(2.0, 5.0) - base) < 1e-12, "onset above the density: no effect"
    crowded = relief(2.0, 0.0)
    assert crowded < base * 0.9, (crowded, base)
    assert relief(6.0, 0.0) < crowded, "stronger coefficient, less milk"


def test_courtship_erosion_is_weaned_males_only_and_irreversible() -> None:
    from universe25.agents.state import SEX_M

    sim = _make_sim(days=1.0, out="test_bio_court")
    a = sim.agents
    bio = sim.cfg.biology
    bio.courtship_erosion_rate = 0.2
    bio.courtship_erosion_stress = 0.5
    alive = np.flatnonzero(a.alive)
    male, pup_m, calm_m, female = alive[0], alive[1], alive[2], alive[3]
    a.sex[[male, pup_m, calm_m]] = SEX_M
    a.sex[female] = SEX_F
    a.age_days[[male, calm_m, female]] = 300.0
    a.age_days[pup_m] = bio.weaning_days - 5.0
    a.stress[[male, pup_m, female]] = 0.9
    a.stress[calm_m] = 0.3
    a.courtship_cap[:] = 1.0
    sim.tick = sim.cfg.ticks_per_day
    sim._daily_courtship_erosion(a.alive)
    assert abs(float(a.courtship_cap[male]) - (1.0 - 0.2 * 0.4)) < 1e-6
    assert a.courtship_cap[pup_m] == 1.0 and a.courtship_cap[calm_m] == 1.0
    assert a.courtship_cap[female] == 1.0, "females keep courtship_cap untouched"
    sim.tick += 1
    sim._daily_courtship_erosion(a.alive)
    assert abs(float(a.courtship_cap[male]) - (1.0 - 0.2 * 0.4)) < 1e-6, "not a day boundary"
    sim.tick = 2 * sim.cfg.ticks_per_day
    a.stress[male] = 0.1
    sim._daily_courtship_erosion(a.alive)
    assert abs(float(a.courtship_cap[male]) - (1.0 - 0.2 * 0.4)) < 1e-6, "must not recover"


if __name__ == "__main__":
    test_no_immature_conception_and_pup_actions()
    test_last_surviving_young_tracks_weaned_cohorts()
    test_resolution_scaling()
    test_decisions_are_held_between_decision_ticks()
    test_relaxation_feeding_composes_over_substeps()
    test_maternal_erosion_is_weaned_only_and_irreversible()
    test_courtship_erosion_is_weaned_males_only_and_irreversible()
    test_breakdown_pressure_ramp_is_graded_and_step_at_zero_width()
    test_fertility_floor_scales_conception_with_maternal_cap()
    test_nursing_disturbance_is_graded_in_cell_density()
    test_conception_density_suppression_is_graded_per_cell()
    test_warp_density_stress_parity()
    print("test_biology_guards: OK")
