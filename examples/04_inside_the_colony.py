"""Step the engine yourself and read every mouse: here, each day, the number alive, the mean
stress of the weaned and the share of them withdrawn.

    python examples/04_inside_the_colony.py

Every mouse is a slot in flat arrays (src/universe25/agents/state.py): alive, sex, age_days,
x, y, stress, hunger, role, nest_id, competence, maternal and more.
"""
import tempfile
from pathlib import Path

import numpy as np

import universe25 as u25
from universe25.agents.state import ROLE_WITHDRAWN
from universe25.sim import Universe25Sim

days = 600
cfg = u25.colony_config("universe25", {"seed": 7001, "days": days, "backend": "numpy",
                                       "device": "cpu", "log_every_ticks": 10**9,
                                       "snapshot_every_days": 0})
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    sim = Universe25Sim(cfg, Path(tmp))
    a = sim.agents
    for _ in range(days * cfg.ticks_per_day):
        sim.step()
        if sim.tick % (50 * cfg.ticks_per_day) == 0:  # every 50 days
            weaned = a.alive & (a.age_days >= cfg.biology.weaning_days)
            print(f"day {sim.day:4.0f}: {int(a.alive.sum()):5d} alive, mean stress of the weaned "
                  f"{float(np.mean(a.stress[weaned])):.2f}, withdrawn "
                  f"{float(np.mean(a.role[weaned] == ROLE_WITHDRAWN)):.2f}")
