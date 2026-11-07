"""Scarcity tools (phase 4 survival condition): capacity supply follows weaned occupancy and is
capped at two days of a cell's share; foragers at a hopper split a short stock equally; famine
pulses scale the supply; the abundant arm is untouched by any of it."""
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


def _sim(resources: dict) -> Universe25Sim:
    over = dict(seed=7100, days=5.0, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=256, log_every_ticks=10**9, snapshot_every_days=0, resources=resources)
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


if __name__ == "__main__":
    test_capacity_supply_follows_occupancy_and_is_capped()
    test_famine_pulses_scale_the_supply()
    test_foragers_split_a_short_stock_equally()
    print("test_scarcity: OK")
