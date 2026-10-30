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
    ROLE_PUP,
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
    sim = _make_sim(days=150.0, out="test_bio_ly")
    sim.run()
    bio = sim.cfg.biology
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
    assert s6.k_ev == 1.0 and s6.sqrt_k == 1.0 and s6.sd_k == 1.0
    assert abs(s24.k_ev - 0.25) < 1e-12 and abs(s24.sqrt_k - 0.5) < 1e-12
    assert abs(s24.sd_k - 2.0) < 1e-12
    assert s6.reach == s24.reach == 4.0
    # per-day random-walk variance is resolution independent: tpd * (c*dt*10*sd_k)^2
    v6 = 6 * (3.0 * s6.dt_days * 10 * s6.sd_k) ** 2
    v24 = 24 * (3.0 * s24.dt_days * 10 * s24.sd_k) ** 2
    assert abs(v6 - v24) < 1e-9, (v6, v24)
    # per-day variance of a per-decision nudge written without dt: tpd * (c*sqrt_k)^2
    j6 = 6 * (0.4 * s6.sqrt_k) ** 2
    j24 = 24 * (0.4 * s24.sqrt_k) ** 2
    assert abs(j6 - j24) < 1e-9, (j6, j24)
    # per-decision effects: tpd * k is constant → daily totals resolution independent
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
    dens_frac = float(a.n_alive / max(1, sim.world.capacity_design))
    b["dens_frac"].assign(np.array([dens_frac], dtype=np.float32))
    cap_cell = float(sim.world.capacity_design / max(1, sim.world.n_cells))
    wp.launch(
        density_stress_kernel,
        dim=a.capacity,
        inputs=[
            b["alive"], b["cell_id"], b["nest_id"], b["rank"], b["stress"], b["social_drive"],
            b["cell_counts"], b["nest_occ"], b["nest_cap"], b["age_days"], b["competence"],
            float(sim.dt_days), float(d.stress_density_gain), float(d.stress_decay),
            float(bio.nest_overcrowd_stress), cap_cell, b["dens_frac"],
            float(bio.menopause_density_threshold), float(bio.social_breakdown_stress_boost),
            float(bio.maturity_days), float(bio.imprint_rate), float(bio.imprint_density_threshold),
            float(sim.k_ev),
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


if __name__ == "__main__":
    test_no_immature_conception_and_pup_actions()
    test_last_surviving_young_tracks_weaned_cohorts()
    test_resolution_scaling()
    test_warp_density_stress_parity()
    print("test_biology_guards: OK")
