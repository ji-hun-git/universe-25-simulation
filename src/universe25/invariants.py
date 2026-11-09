"""Runtime invariants of the simulation state (Tier 0 of docs/REVIEW_2026-11-09.md).

`check(sim)` returns the violated invariants after a tick (empty list = all hold). With
`debug_invariants: true` in the config the tick loop calls it and raises `InvariantError`. It
only reads state: no random draw and no write, so a run with the checks on follows the same
trajectory as one without.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from universe25.agents.state import ACT_NEST, ACT_REST, ROLE_DEAD

if TYPE_CHECKING:  # pragma: no cover
    from universe25.sim import Universe25Sim

DRIVES = ("hunger", "thirst", "fatigue", "stress", "social_drive", "curiosity", "boredom",
          "wounds")
UNIT = ("energy", "competence", "maternal_cap", "courtship_cap")
TOL = 1e-5


class InvariantError(AssertionError):
    pass


def check(sim: Universe25Sim) -> list[str]:
    a = sim.agents
    w = sim.world
    bad: list[str] = []
    al = a.alive
    idx = np.flatnonzero(al)
    if a.n_alive != idx.size:
        bad.append(f"n_alive {a.n_alive} != alive count {idx.size}")
    n0 = getattr(sim, "_n_initial", None)
    if n0 is not None and idx.size != n0 + sim._births - sim._deaths:
        bad.append(f"population accounting: alive {idx.size} != initial {n0} + births "
                   f"{sim._births} - deaths {sim._deaths}")
    if np.any(a.role[idx] == ROLE_DEAD):
        bad.append("a living animal has the dead role")
    if idx.size == 0:
        return bad
    x, y = a.x[idx].astype(np.float64), a.y[idx].astype(np.float64)
    if np.any((x < 0.5 - TOL) | (x > w.width - 0.5 + TOL) | (y < 0.5 - TOL)
              | (y > w.height - 0.5 + TOL)):
        bad.append("position outside the pen")
    for k in DRIVES:
        v = getattr(a, k)[idx]
        if np.any(~np.isfinite(v)) or np.any(v < -TOL) or np.any(v > 1.5 + TOL):
            bad.append(f"{k} outside [0, 1.5] or not finite")
    for k in UNIT:
        v = getattr(a, k)[idx]
        if np.any(~np.isfinite(v)) or np.any(v < -TOL) or np.any(v > 1.0 + TOL):
            bad.append(f"{k} outside [0, 1] or not finite")
    m = a.maternal[idx]
    if np.any(~np.isfinite(m)) or np.any(m < -TOL) or np.any(m > 1.0 + TOL):
        bad.append("maternal outside [0, 1] or not finite")
    pup =a.age_days[idx] < sim.cfg.biology.weaning_days
    if np.any(pup & ~np.isin(a.last_action[idx], (ACT_REST, ACT_NEST))
              & (a.age_days[idx] > sim.dt_days + TOL)):
        bad.append("a pre-weaning pup chose an action other than REST / NEST")
    if np.any(a.gestating[idx] < -TOL):
        bad.append("negative gestation")
    if np.any(~np.isfinite(sim.food)) or np.any(sim.food < -TOL) or \
            np.any(~np.isfinite(sim.water)) or np.any(sim.water < -TOL):
        bad.append("negative or non-finite resource stock")
    return bad


def enforce(sim: Universe25Sim) -> None:
    bad = check(sim)
    if bad:
        raise InvariantError(f"tick {sim.tick} (day {sim.day:.3f}): " + "; ".join(bad))
