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
    s = sim.run()
    assert s["births"] > 0 and s["final_n"] == sim._n_initial + s["births"] - s["deaths"]


if __name__ == "__main__":
    test_grid_cells_of_is_the_old_arithmetic()
    test_calhoun_pen()
    test_capacity_box_feeding_and_withdrawal()
    test_layout_guards_and_a_replica_colony()
    print("test_replica: OK")
