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
from universe25.rng import make_rng

if TYPE_CHECKING:  # pragma: no cover
    from universe25.config import PolicyConfig
    from universe25.sim import Universe25Sim


class Policy(Protocol):
    """One int8 action per row of `idx` (the agents deciding this tick), each with
    `allowed[row, action]` True. `allowed` is (len(idx), N_ACTIONS) and always allows REST."""

    name: str

    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray,
               rng: np.random.Generator | None = None) -> np.ndarray: ...


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

    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray,
               rng: np.random.Generator | None = None) -> np.ndarray:
        """`rng` None = the simulation stream (decisions, bit-identity); the free-time
        sub-steps pass their own stream so they never perturb the biology draws."""
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
        r = sim.rng if rng is None else rng
        return sample_masked(np.exp(np.clip(U, -20, 20)), allowed, r.random(m))


POLICY_SEED_OFFSET = 1_000_003  # the policy stream is seed + offset: never the biology stream
PARAM_KEYS = ("W1", "b1", "W2", "b2", "W3", "b3")


def _orthogonal(rng: np.random.Generator, n_in: int, n_out: int, gain: float) -> np.ndarray:
    a = rng.standard_normal((max(n_in, n_out), min(n_in, n_out)))
    q, r = np.linalg.qr(a)
    q = q * np.sign(np.diag(r))
    if n_in < n_out:
        q = q.T
    return (gain * q[:n_in, :n_out]).astype(np.float32)


class MlpFrozenPolicy:
    """obs -> hidden tanh -> hidden tanh -> N_ACTIONS logits; weights fixed for the run (no
    learning). Inference is pure NumPy float32 on the reference path; sampling is inverse-CDF
    on the masked softmax with one uniform per deciding agent from the policy's own stream."""

    name = "mlp_frozen"

    def __init__(self, params: dict[str, np.ndarray], seed: int):
        from universe25.agents.observation import OBS_DIM, ObservationBuilder

        self._builder_cls = ObservationBuilder
        self.params = {k: np.asarray(params[k], dtype=np.float32) for k in PARAM_KEYS}
        W1, W2, W3 = self.params["W1"], self.params["W2"], self.params["W3"]
        if W1.shape[0] != OBS_DIM or W3.shape[1] != N_ACTIONS or W1.shape[1] != W2.shape[0]:
            raise ValueError(f"bad MLP shapes {W1.shape} {W2.shape} {W3.shape}")
        self.rng = make_rng(int(seed) + POLICY_SEED_OFFSET)
        self.builder = None

    @classmethod
    def random_init(cls, seed: int, hidden: int = 128) -> MlpFrozenPolicy:
        """Orthogonal init (last layer gain 0.01: near-uniform logits) from a seeded stream."""
        from universe25.agents.observation import OBS_DIM

        rng = make_rng(int(seed) + POLICY_SEED_OFFSET + 1)
        params = {
            "W1": _orthogonal(rng, OBS_DIM, hidden, np.sqrt(2.0)),
            "b1": np.zeros(hidden, np.float32),
            "W2": _orthogonal(rng, hidden, hidden, np.sqrt(2.0)),
            "b2": np.zeros(hidden, np.float32),
            "W3": _orthogonal(rng, hidden, N_ACTIONS, 0.01),
            "b3": np.zeros(N_ACTIONS, np.float32),
        }
        return cls(params, seed)

    @classmethod
    def from_npz(cls, path: str, seed: int) -> MlpFrozenPolicy:
        with np.load(path) as z:
            return cls({k: z[k] for k in PARAM_KEYS}, seed)

    def save_npz(self, path: str) -> None:
        np.savez(path, **self.params)

    def logits(self, obs: np.ndarray) -> np.ndarray:
        p = self.params
        h = np.tanh(obs @ p["W1"] + p["b1"])
        h = np.tanh(h @ p["W2"] + p["b2"])
        return h @ p["W3"] + p["b3"]

    def observe(self, sim: Universe25Sim, idx: np.ndarray) -> np.ndarray:
        if self.builder is None or self.builder.world is not sim.world:
            self.builder = self._builder_cls(sim.world)
        return self.builder.build(sim, idx)

    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray,
               rng: np.random.Generator | None = None) -> np.ndarray:
        z = self.logits(self.observe(sim, idx)).astype(np.float64)
        z = np.where(allowed, z, -1e8)  # invalid-action mask on the logits
        z -= z.max(axis=1, keepdims=True)
        r = self.rng if rng is None else rng
        return sample_masked(np.exp(z), allowed, r.random(idx.size))


def make_policy(cfg: PolicyConfig, seed: int = 7000) -> Policy:
    if cfg.kind == "need_driven":
        return NeedDrivenPolicy()
    if cfg.kind == "mlp_ppo":  # torch is imported only for the learning kind
        from universe25.learn.policy_ppo import MlpPpoPolicy

        return MlpPpoPolicy(cfg, seed)
    if cfg.kind == "mlp_frozen":
        if cfg.weights:
            return MlpFrozenPolicy.from_npz(cfg.weights, seed)
        return MlpFrozenPolicy.random_init(seed, hidden=int(cfg.hidden))
    raise ValueError(f"unknown policy kind {cfg.kind!r}")
