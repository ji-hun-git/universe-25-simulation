"""Scarcity tools (phase 4 survival condition): capacity supply follows weaned occupancy and is
capped at two days of a cell's share; foragers at a hopper split a short stock equally; famine
pulses scale the supply; small meals cap the relief of one meal; late reflexes fire above their
threshold, and traces record it; the abundant arm is untouched by any of it."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import ACT_FORAGE  # noqa: E402
from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _sim(resources: dict, **extra: dict) -> Universe25Sim:
    over = dict(seed=7100, days=5.0, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=256, log_every_ticks=10**9, snapshot_every_days=0, resources=resources)
    over.update(extra)
    return Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over),
                         Path(tempfile.mkdtemp(prefix="u25scarce_")))


def test_capacity_supply_follows_occupancy_and_is_capped() -> None:
    sim = _sim({"mode": "scarce", "scarce_supply": "capacity", "scarce_capacity_animals": 100.0})
    a = sim.agents
    sim.food[:] = 0.0
    sim._refill_resources()
    weaned = a.alive & (a.age_days >= sim.cfg.biology.weaning_days)
    occ = np.bincount(a.cell_id[weaned].astype(int), minlength=sim.world.n_cells)
    share = 100.0 * sim.cfg.drives.hunger_gain_per_day * occ / occ.sum()
    assert np.allclose(sim.food, share / sim.cfg.ticks_per_day)
    assert np.all(sim.food[occ == 0] == 0.0), "no food delivered to empty cells"
    for _ in range(1000):  # stock never exceeds two days of a cell's share
        sim._refill_resources()
    assert np.allclose(sim.food, 2.0 * share)


def test_famine_pulses_scale_the_supply() -> None:
    sim = _sim({"mode": "scarce", "scarce_supply": "capacity", "scarce_capacity_animals": 100.0,
                "scarce_famine_period_days": 10.0, "scarce_famine_days": 3.0,
                "scarce_famine_factor": 0.25})
    sim.food[:] = 0.0
    sim.day = 1.0  # inside a famine
    sim._refill_resources()
    in_famine = sim.food.copy()
    sim.food[:] = 0.0
    sim.day = 5.0  # outside
    sim._refill_resources()
    assert np.allclose(in_famine, 0.25 * sim.food)


def test_foragers_split_a_short_stock_equally() -> None:
    sim = _sim({"mode": "scarce", "scarce_supply": "capacity", "scarce_capacity_animals": 100.0})
    a = sim.agents
    alive = np.flatnonzero(a.alive)
    i, j = alive[0], alive[1]
    a.age_days[[i, j]] = 120.0
    c = int(a.cell_id[i])
    a.cell_id[j] = c
    a.x[j], a.y[j] = a.x[i], a.y[i]
    a.hunger[[i, j]] = 1.0
    sim.food[:] = 0.0
    sim.food[c] = 0.4
    mask = np.zeros(a.capacity, dtype=bool)
    mask[[i, j]] = True
    actions = np.zeros(a.capacity, dtype=np.int8)
    actions[[i, j]] = ACT_FORAGE
    sim._execute_actions(mask, actions)
    assert np.allclose(a.hunger[[i, j]], [0.8, 0.8]), a.hunger[[i, j]]
    assert abs(sim.food[c]) < 1e-9


def test_small_meals_cap_the_relief_of_one_meal() -> None:
    """Small meals (PHASE4_DESIGN.md 4.7): with meal_cap a meal relieves at most the cap of
    hunger from an unlimited stock; without it the meal relieves all of it."""
    for cap, after in ((0.375, 0.625), (None, 0.0)):
        sim = _sim({} if cap is None else {"meal_cap": cap})
        assert sim.cfg.resources.meal_cap == cap and sim.cfg.resources.mode == "abundant"
        a = sim.agents
        i = int(np.flatnonzero(a.alive)[0])
        a.age_days[i] = 120.0
        a.hunger[i] = 1.0
        sim.food[:] = 1e9
        mask = np.zeros(a.capacity, dtype=bool)
        mask[i] = True
        actions = np.zeros(a.capacity, dtype=np.int8)
        actions[i] = ACT_FORAGE
        sim._execute_actions(mask, actions)
        assert abs(float(a.hunger[i]) - after) < 1e-6, (cap, float(a.hunger[i]))
    try:
        _sim({"meal_cap": 0.0})
        raise AssertionError("a meal cap of 0 must be refused")
    except ValueError:
        pass


def test_late_reflexes_fire_above_their_threshold_and_traces_record_it() -> None:
    """Late reflexes (PHASE4_DESIGN.md 4.8): at the calibrated 0.85 a weaned animal at thirst
    0.95 is forced to DRINK; with drives.reflex_need 1.0 it chooses freely (its decision is
    eligible), and above 1.0 the reflexes force, hunger first. A trace records a threshold only
    when it is not the calibrated one. A threshold of 0 is refused."""
    from universe25.agents.state import ACT_DRINK
    from universe25.metrics.trace import TraceRecorder

    for need, free in ((0.85, False), (1.0, True)):
        sim = _sim({}, drives={"reflex_need": need})
        assert sim.cfg.drives.reflex_need == need
        a = sim.agents
        alive = a.alive.copy()
        idx = np.flatnonzero(alive)
        assert idx.size >= 4 and np.all(a.age_days[idx] >= sim.cfg.biology.weaning_days)
        a.fatigue[idx], a.hunger[idx], a.thirst[idx] = 0.0, 0.0, 0.95
        sim._eligible_hist[:] = 0
        act = sim._select_actions(alive)
        n_el = int(sim._eligible_hist.sum())
        if free:
            assert n_el == idx.size, n_el  # no reflex in force
        else:
            assert n_el == 0 and np.all(act[idx] == ACT_DRINK)
        a.hunger[idx], a.thirst[idx] = 1.1, 1.1
        act = sim._select_actions(alive)
        assert np.all(act[idx] == ACT_FORAGE)  # both above: the hunger reflex wins
        meta = TraceRecorder(sim, [(0.0, 1.0)]).meta
        assert ("reflex_need" in meta) == free and meta.get("reflex_need", need) == need
    try:
        _sim({}, drives={"reflex_need": 0.0})
        raise AssertionError("a reflex threshold of 0 must be refused")
    except ValueError:
        pass


if __name__ == "__main__":
    test_capacity_supply_follows_occupancy_and_is_capped()
    test_famine_pulses_scale_the_supply()
    test_foragers_split_a_short_stock_equally()
    test_small_meals_cap_the_relief_of_one_meal()
    test_late_reflexes_fire_above_their_threshold_and_traces_record_it()
    print("test_scarcity: OK")
