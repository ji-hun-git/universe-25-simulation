"""Replica v2, milestone M1 (docs/REPLICA_V2.md): Calhoun's pen. The grid layout's cell mapping is
the frozen colony's arithmetic exactly; the calhoun layout has 16 equal triangular cells that tile
the floor, four tunnels of four box levels per cell, a hopper, a water platform and a ring stand in
each cell; feeding capacity serves the highest-ranked first; animals eat at their own box before
the reconfiguration day; withdrawn animals drift to the pen centre; the Warp path is refused; a
replica colony keeps the runtime invariants past its first litters."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import ACT_FORAGE, ACT_WITHDRAW  # noqa: E402
from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402
from universe25.world.geometry import build_world  # noqa: E402


def _cfg(layout: str = "calhoun", **over):
    base = {"geometry": {"layout": layout}, "playground": {"enabled": False}}
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return load_config(ROOT / "configs" / "default.yaml", base)


def test_grid_cells_of_is_the_old_arithmetic() -> None:
    cfg = load_config(ROOT / "configs" / "default.yaml")
    w = build_world(cfg.geometry, cfg.playground, seed=7000)
    r = np.random.default_rng(7100)
    for dt in (np.float32, np.float64):
        x = r.uniform(0.5, 100.5, 50000).astype(dt)
        y = r.uniform(0.5, 100.5, 50000).astype(dt)
        cw, ch = w.width / 4, w.height / 4
        old = np.clip((y / ch).astype(int), 0, 3) * 4 + np.clip((x / cw).astype(int), 0, 3)
        assert np.array_equal(w.cells_of(x, y), old)


def test_calhoun_pen() -> None:
    cfg = _cfg()
    w = build_world(cfg.geometry, cfg.playground, seed=7000)
    assert w.layout == "calhoun" and w.n_cells == 16 and len(w.nests) == 256
    r = np.random.default_rng(7100)
    x, y = r.uniform(0, 101, 300000), r.uniform(0, 101, 300000)
    area = np.bincount(w.cells_of(x, y), minlength=16) / x.size * 101.0 ** 2
    assert np.all(np.abs(area / (101.0 ** 2 / 16) - 1) < 0.03), area  # 638 sq in each
    for c in w.cells:
        assert len(c.nest_ids) == 16
        levels = sorted(w.nests[n].level for n in c.nest_ids)
        assert levels == [0] * 4 + [1] * 4 + [2] * 4 + [3] * 4
        for px, py in (c.food_xy, c.water_xy, w.ring_xy[c.id]):
            assert w.cells_of(np.array([px]), np.array([py]))[0] == c.id
    # a point just inside each wall segment's middle is in that segment's cell
    L = 101.0 / 4
    for cid in range(16):
        wall, k = divmod(cid, 4)
        u = (k + 0.5) * L
        px, py = [(u, 1.0), (100.0, u), (101.0 - u, 100.0), (1.0, 101.0 - u)][wall]
        assert w.cells_of(np.array([px]), np.array([py]))[0] == cid, cid
    assert w.withdraw_xy == (50.5, 50.5)


def test_capacity_box_feeding_and_withdrawal() -> None:
    cfg = _cfg(seed=7100, days=5.0, ticks_per_day=6, backend="numpy", device="cpu",
               log_every_ticks=6, snapshot_every_days=0,
               geometry={"hopper_meals_per_day": 12.0, "box_feeding_until_day": 2.0})
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25rep_")))
    a = sim.agents
    ii = np.flatnonzero(a.alive)
    a.cell_id[ii] = 3
    a.rank[ii] = np.linspace(0.1, 0.9, ii.size)
    ok = sim._capacity_mask(ii, 12.0)  # 2 per decision at 6 decisions per day
    assert ok.sum() == 2 and set(ii[ok]) == set(ii[np.argsort(-a.rank[ii])[:2]])
    # before the reconfiguration day a forager heads for its own box, not the hopper
    i = int(ii[0])
    nest = sim.world.nests[int(a.nest_id[i])]
    a.x[i], a.y[i] = 50.0, 50.0
    acts = np.full(a.capacity, -1, np.int8)
    acts[a.alive] = 0
    acts[i] = ACT_FORAGE
    sim._execute_actions(a.alive.copy(), acts)
    to_box = np.hypot(a.x[i] - nest.x, a.y[i] - nest.y)
    assert to_box < np.hypot(50.0 - nest.x, 50.0 - nest.y), "moves toward its own box"
    # withdrawn animals drift to the pen centre
    a.x[i], a.y[i] = 10.0, 10.0
    acts[i] = ACT_WITHDRAW
    sim._execute_actions(a.alive.copy(), acts)
    assert np.hypot(a.x[i] - 50.5, a.y[i] - 50.5) < np.hypot(10.0 - 50.5, 10.0 - 50.5)


def test_layout_guards_and_a_replica_colony() -> None:
    for bad in ({"backend": "warp"}, {"geometry": {"n_cells_x": 2}}):
        try:
            _cfg(**bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} must be refused for the calhoun layout")
    cfg = load_config(ROOT / "configs" / "replica_v2.yaml", {
        "seed": 7100, "days": 150.0, "ticks_per_day": 6, "backend": "numpy", "device": "cpu",
        "log_every_ticks": 6, "snapshot_every_days": 0, "debug_invariants": True})
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25rep_")))
    founders = sorted({int(c) for c in sim.agents.cell_id[sim.agents.alive]})
    assert founders == [1, 5, 9, 13], founders
    assert np.all(sim.agents.age_days[sim.agents.alive] == 48.0)  # M2 founders
    s = sim.run()
    assert s["births"] > 0 and s["final_n"] == sim._n_initial + s["births"] - s["deaths"]
    assert s["territories"]["owned_cells"] >= 1, s["territories"]


class _FixedDraw:
    """Stands in for the simulation stream where a test needs one outcome."""

    def __init__(self, u: float) -> None:
        self.u = u

    def random(self) -> float:
        return self.u


def test_m2_territories() -> None:
    """Replica v2 M2: off by default and refused on Warp; claims settle after
    territory_settle_days passes as top male, a new top male restarts the claim, an absent
    owner keeps his cell, a challenger within the gap contests, a winning challenger takes
    the cell and drops his other claims, death and withdrawal end ownership, and only a
    female whose cell has an owner conceives, by him."""
    from universe25.agents.state import ROLE_WITHDRAWN, SEX_F, SEX_M

    d = load_config(ROOT / "configs" / "default.yaml")
    assert d.biology.territories is False and d.biology.founder_age_days is None
    try:
        _cfg("grid", backend="warp", biology={"territories": True})
    except ValueError:
        pass
    else:
        raise AssertionError("territories must be refused on the Warp path")
    cfg = _cfg(seed=7100, days=5.0, ticks_per_day=6, backend="numpy", device="cpu",
               log_every_ticks=6, snapshot_every_days=0,
               biology={"territories": True, "founder_age_days": 48.0,
                        "first_conception_min_day": 0.0})
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25rep_")))
    a = sim.agents
    ff = np.flatnonzero(a.alive)
    assert np.all(a.age_days[ff] == 48.0) and list(sim._serial[ff]) == list(range(8))
    a.age_days[ff] = 100.0
    m0, m1, m2, m3 = (int(i) for i in ff[a.sex[ff] == SEX_M])
    f0, f1 = (int(i) for i in ff[a.sex[ff] == SEX_F][:2])
    a.rank[[m0, m1, m2, m3]] = (0.9, 0.5, 0.3, 0.2)
    a.cell_id[[m0, m1, m2, m3]] = (2, 7, 7, 7)
    a.cell_id[ff[a.sex[ff] == SEX_F]] = 0
    alive = a.alive.copy()
    settle = cfg.biology.territory_settle_days

    def daily(k: int = 1) -> None:
        for _ in range(k):
            sim._daily_territories(alive)

    daily(settle - 1)
    assert sim._owner[2] == -1 and sim._claim[2] == m0 and sim._claim_days[2] == settle - 1
    daily()
    assert sim._owner[2] == m0 and sim._owner[7] == m1 and sim._claim[2] == -1
    daily()  # m2 (0.3) is below m1 (0.5) - gap: no contest
    assert sim._contests == 0
    # a new top male restarts a claim; an owner neither claims nor loses his absent cell
    a.cell_id[m3] = 11
    daily(2)
    assert sim._claim[11] == m3 and sim._claim_days[11] == 2
    a.cell_id[m2] = 11
    daily()
    assert sim._claim[11] == m2 and sim._claim_days[11] == 1
    a.cell_id[m0] = 11
    daily()
    assert sim._owner[2] == m0 and sim._claim[11] == m2 and sim._claim_days[11] == 2
    # a challenger within the gap contests; a winning challenger takes the cell
    a.cell_id[m2] = 7
    a.rank[m2] = 0.45
    sim.rng, real = _FixedDraw(0.99), sim.rng
    daily()
    sim.rng = real
    assert sim._contests == 1 and sim._takeovers == 1 and sim._owner[7] == m2
    assert np.isclose(a.rank[m2], 0.50) and np.isclose(a.rank[m1], 0.40)
    assert np.isclose(a.wounds[m1], 0.15)
    assert sim._claim[11] == m3 and sim._claim_days[11] == 1  # m2's claim went; m3 restarts
    sim._claim[5], sim._claim_serial[5], sim._claim_days[5] = m2, sim._serial[m2], 3
    sim._set_owner(7, m2, set())  # becoming an owner drops every claim he holds
    assert sim._claim[5] == -1 and sim._claim_days[5] == 0
    # death and withdrawal end ownership
    a.alive[m0] = alive[m0] = False
    a.role[m2] = ROLE_WITHDRAWN
    daily()
    assert sim._owner[2] == -1 and sim._owner[7] == -1
    # conception needs an owner, who sires: f0 in an owned cell, f1 in an unowned one
    a.role[m2] = a.role[m1]
    sim._set_owner(7, m2, set())
    a.cell_id[f0], a.cell_id[f1] = 7, 4
    a.stress[[f0, f1, m2]] = 0.0
    a.energy[[f0, f1]] = 0.9
    sim.rng = _FixedDraw(0.0)
    sim._daily_breeding_pass(alive)
    sim.rng = real
    assert a.gestating[f0] > 0 and a.gestating[f1] == 0
    assert sim._preg_sire[f0] == sim._serial[m2]
    a.gestating[f0] = sim.dt_days
    sim._reproduce(a.alive.copy())
    pups = np.flatnonzero(a.alive & (a.age_days == 0.0))
    assert pups.size > 0 and np.all(sim._sire[pups] == sim._serial[m2])
    assert sim._litter_log == [(sim.day, int(sim._serial[m2]), int(pups.size))]


if __name__ == "__main__":
    test_grid_cells_of_is_the_old_arithmetic()
    test_calhoun_pen()
    test_capacity_box_feeding_and_withdrawal()
    test_layout_guards_and_a_replica_colony()
    test_m2_territories()
    print("test_replica: OK")
