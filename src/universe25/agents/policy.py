"""Action policies for the tick loop (phase 4 scaffold).

The simulation owns physiology: the decision cadence, the eligibility mask (pre-weaning pups
only rest or nest, mating needs an adult below the stress threshold, nursing needs a female with
maternal investment, ...) and the reflex overrides for critical thirst, hunger and fatigue. A
policy owns the choice among the eligible actions.

`NeedDrivenPolicy` is the phase 1/2 utility softmax moved here verbatim: with it the trajectory is
bit-identical to the inline version it replaces (same utilities, same mask, one `rng.random` draw
per deciding agent from the simulation stream, in the same order).

A learned policy (phase 4) implements the same `choose`. It must draw from its own RNG stream so
policy sampling never perturbs the biology stream, and it must never receive a play-named
observation, reward or goal (H2): only the generic drives (homeostasis, curiosity, boredom), the
local state and the geometry.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import numpy as np

from universe25.agents.state import (
    ACT_AGGRESS,
    ACT_DRINK,
    ACT_EXPLORE,
    ACT_FORAGE,
    ACT_MANIPULATE,
    ACT_MATE,
    ACT_NEST,
    ACT_NURSE,
    ACT_REST,
    ACT_SOCIAL,
    ACT_WITHDRAW,
    N_ACTIONS,
    ROLE_NURSING,
    ROLE_WITHDRAWN,
)

if TYPE_CHECKING:  # pragma: no cover
    from universe25.config import PolicyConfig
    from universe25.sim import Universe25Sim


class Policy(Protocol):
    """One int8 action per row of `idx` (the agents deciding this tick), each with
    `allowed[row, action]` True. `allowed` is (len(idx), N_ACTIONS) and always allows REST."""

    name: str

    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray) -> np.ndarray: ...


def sample_masked(weights: np.ndarray, allowed: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Categorical sample per row from non-negative `weights` restricted to `allowed`, using one
    uniform `r` per row (inverse CDF). Rows must keep at least one allowed action."""
    P = weights * allowed
    P /= P.sum(axis=1, keepdims=True)
    cdf = np.cumsum(P, axis=1)
    return (r[:, None] <= cdf).argmax(axis=1).astype(np.int8)


class NeedDrivenPolicy:
    """Utility softmax over the drives (phase 1/2 behaviour). No play utility term."""

    name = "need_driven"

    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray) -> np.ndarray:
        a = sim.agents
        d = sim.cfg.drives
        scarce = sim.cfg.resources.mode == "scarce"
        m = idx.size
        U = np.zeros((m, N_ACTIONS), dtype=np.float64)
        hung = a.hunger[idx]
        th = a.thirst[idx]
        fat = a.fatigue[idx]
        en = a.energy[idx]
        st = a.stress[idx]
        soc = a.social_drive[idx]
        cur = a.curiosity[idx]
        bor = a.boredom[idx]
        agg = a.aggression[idx] + (d.aggression_scarce_boost if scarce else 0.0)
        role = a.role[idx]
        mat = a.maternal[idx]
        U[:, ACT_FORAGE] = hung * 2.0
        U[:, ACT_DRINK] = th * 2.2
        U[:, ACT_REST] = fat * 1.5 + (1.0 - en)
        U[:, ACT_NEST] = 0.3 + 0.4 * (role == ROLE_NURSING)
        U[:, ACT_SOCIAL] = soc * (1.0 - 0.7 * (role == ROLE_WITHDRAWN))
        U[:, ACT_EXPLORE] = cur * 0.9 + bor * 0.5
        if sim.world.playground_enabled:
            gate = np.where((en > 0.5) & (st < 0.4), 1.2, 0.3)
            U[:, ACT_MANIPULATE] = (cur * 0.7 + bor * 0.8) * gate
        U[:, ACT_AGGRESS] = agg * st * (1.5 if scarce else 0.6)
        U[:, ACT_MATE] = 0.9
        U[:, ACT_NURSE] = mat * 1.4
        U[:, ACT_WITHDRAW] = st * 1.2 * (1.0 - soc)
        U -= U.max(axis=1, keepdims=True)
        # one draw per deciding agent from the simulation stream (bit-identity with phase 1/2)
        return sample_masked(np.exp(np.clip(U, -20, 20)), allowed, sim.rng.random(m))


def make_policy(cfg: PolicyConfig) -> Policy:
    if cfg.kind == "need_driven":
        return NeedDrivenPolicy()
    raise ValueError(f"unknown policy kind {cfg.kind!r}")
