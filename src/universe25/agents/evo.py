"""Inherited-weight policy `evo` (phase 4, P4-4; docs/PHASE4_DESIGN.md sections 1.7 and 4.4).

Every animal carries its own genome: a net over observation v5 (59 floats) -> 32 tanh -> 15
logits (action space v2), 2,415 float32 values, kept in a capacity-sized buffer indexed by SoA
slot. There is no reward and no learner: the frozen biology's births and deaths are the only
selection. Inheritance is one parent per pup:
- at conception the sire is drawn uniformly among the eligible males of the female's cell (the
  breeding pass's candidates) and his genome is copied into her pregnancy;
- at birth each pup copies the mother's or the sire's genome (probability 1/2 each) and
  N(0, mutation_sd^2) is added to every value.

Streams: action sampling, genetics (sire, parent, mutation) and founder draws each come from
their own `SeedSequence([seed, stream, *genetics_key])`, never from the biology stream. Draws
happen in biology order (conceptions in the breeding pass's order, pups in birth order), so a
run is deterministic for a fixed seed. Nothing here reads a detector, a trace or a PlayScore
field, and no term is named after play (H2).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from universe25.agents.observation import OBS_DIM, ObservationBuilder
from universe25.agents.policy import _orthogonal, sample_masked
from universe25.agents.state import N_ACTIONS, SEX_F, SEX_M

if TYPE_CHECKING:  # pragma: no cover
    from universe25.config import PolicyConfig
    from universe25.sim import Universe25Sim

N_IN = OBS_DIM  # observation v5
N_HID = 32
N_OUT = N_ACTIONS  # action space v2
S_W1 = slice(0, N_IN * N_HID)
S_B1 = slice(S_W1.stop, S_W1.stop + N_HID)
S_W2 = slice(S_B1.stop, S_B1.stop + N_HID * N_OUT)
S_B2 = slice(S_W2.stop, S_W2.stop + N_OUT)
N_PARAM = S_B2.stop
assert N_PARAM == 2415

# stream ids for np.random.SeedSequence([seed, stream, ...]) (docs/SEEDS.md: new streams)
SAMPLING_STREAM = 7_100_001
GENETICS_STREAM = 7_200_001
FOUNDER_STREAM = 7_300_001
LINEAGE_STREAM = 7_400_001
NEUTRAL_STREAM = 7_500_001
JUMP_STREAM = 7_600_001  # the norm-matched check (PHASE4_DESIGN.md 4.5)
SEX_ANY = -1  # a pool entry that may found either sex (neutral pools)


def stream(seed: int, stream_id: int, *key: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(stream_id),
                                                         *(int(k) for k in key)]))


def random_genomes(rng: np.random.Generator, n: int) -> np.ndarray:
    """Generation 0: W1 orthogonal (gain sqrt 2), W2 orthogonal (gain 0.01: near-uniform
    choices), zero biases; one genome after another from `rng`."""
    out = np.zeros((int(n), N_PARAM), dtype=np.float32)
    for i in range(int(n)):
        out[i, S_W1] = _orthogonal(rng, N_IN, N_HID, float(np.sqrt(2.0))).ravel()
        out[i, S_W2] = _orthogonal(rng, N_HID, N_OUT, 0.01).ravel()
    return out


def logits(G: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """Each row's own net: obs (n, N_IN) with genomes G (n, N_PARAM) -> logits (n, N_OUT)."""
    n = G.shape[0]
    W1 = G[:, S_W1].reshape(n, N_IN, N_HID)
    h = np.tanh(np.matmul(obs[:, None, :], W1)[:, 0] + G[:, S_B1])
    W2 = G[:, S_W2].reshape(n, N_HID, N_OUT)
    return np.matmul(h[:, None, :], W2)[:, 0] + G[:, S_B2]


def mutate(rng: np.random.Generator, parent: np.ndarray, sd: float) -> np.ndarray:
    return (parent + (rng.standard_normal(parent.shape) * sd).astype(np.float32)).astype(
        np.float32)


def neutral_pool(gen0: np.ndarray, generations: int, size: int, sd: float,
                 rng: np.random.Generator) -> np.ndarray:
    """Wright-Fisher drift with mutation and no selection (PHASE4_DESIGN.md 4.4, NEU): each
    generation samples `size` parents with replacement and adds N(0, sd^2) to every value."""
    pop = np.asarray(gen0, dtype=np.float32)
    for _ in range(int(generations)):
        parents = rng.integers(0, pop.shape[0], int(size))
        pop = mutate(rng, pop[parents], sd)
    return pop


def jump_genome(base: np.ndarray, eps: np.ndarray, generations: int, sd: float,
                lam: float) -> np.ndarray:
    """The norm-matched check (PHASE4_DESIGN.md 4.5): `base` plus `lam` times one random jump
    with the per-value variance of `generations` mutations of sd `sd` (`eps` standard normal).
    At lam = 1 a genome has the size a neutral line reaches by drift, without its genealogy and
    without selection; at lam = 0 it is `base` itself."""
    step = float(lam) * float(sd) * float(np.sqrt(int(generations)))
    out = np.asarray(base, np.float64) + step * np.asarray(eps, np.float64)
    return out.astype(np.float32)


def genome_norms(G: np.ndarray) -> dict[str, float]:
    """Mean Frobenius norms of the layers over the genomes in G."""
    if G.shape[0] == 0:
        return {k: float("nan") for k in ("w1", "b1", "w2", "b2")}
    return {
        "w1": float(np.linalg.norm(G[:, S_W1], axis=1).mean()),
        "b1": float(np.linalg.norm(G[:, S_B1], axis=1).mean()),
        "w2": float(np.linalg.norm(G[:, S_W2], axis=1).mean()),
        "b2": float(np.linalg.norm(G[:, S_B2], axis=1).mean()),
    }


def save_pool(path: Path, genomes: np.ndarray, depth: np.ndarray, sex: np.ndarray,
              **meta: Any) -> None:
    np.savez(path, genomes=np.asarray(genomes, np.float32), depth=np.asarray(depth, np.int64),
             sex=np.asarray(sex, np.int64), **{k: np.asarray(v) for k, v in meta.items()})


def load_pool(path: str | Path) -> dict[str, np.ndarray]:
    with np.load(path) as z:
        out = {k: z[k] for k in z.files}
    if out["genomes"].shape[1:] != (N_PARAM,):
        raise ValueError(f"genome pool {path}: shape {out['genomes'].shape}, want (n, {N_PARAM})")
    return out


class EvoPolicy:
    """Per-animal genomes with one-parent inheritance and Gaussian mutation; no reward."""

    name = "evo"

    def __init__(self, cfg: PolicyConfig, seed: int):
        self.seed = int(seed)
        self.sd = float(cfg.mutation_sd)
        self.mode = cfg.founder_mode
        key = tuple(int(k) for k in cfg.genetics_key)
        self.rng = stream(self.seed, SAMPLING_STREAM, *key)
        self.gen = stream(self.seed, GENETICS_STREAM, *key)
        self.founder_rng = stream(self.seed, FOUNDER_STREAM, *key)
        self.pool = load_pool(cfg.founders) if cfg.founders else None
        self.G: np.ndarray | None = None
        self.builder: ObservationBuilder | None = None
        self.n_conceptions = 0
        self.n_births = 0
        self.n_from_sire = 0

    # ------------------------------------------------------------ buffers
    def _ensure(self, sim: Universe25Sim) -> None:
        cap = int(sim.agents.capacity)
        if self.G is not None and self.G.shape[0] == cap:
            return
        self.G = np.zeros((cap, N_PARAM), dtype=np.float32)
        self.depth = np.zeros(cap, dtype=np.int64)
        self.preg = np.zeros((cap, N_PARAM), dtype=np.float32)
        self.preg_depth = np.zeros(cap, dtype=np.int64)
        self.preg_ok = np.zeros(cap, dtype=bool)

    # ------------------------------------------------------------ genetics hooks (sim.py)
    def found(self, sim: Universe25Sim, slots: np.ndarray) -> None:
        """Genomes of the founders spawned in `slots` (in slot order): from the pool in order
        ("ordered"), drawn from it by sex without replacement ("sample"; entries of SEX_ANY
        found either sex, and a pool with no sex labels is drawn as one), or, without a pool,
        independent generation-0 genomes."""
        self._ensure(sim)
        slots = np.asarray(slots, dtype=np.int64)
        n = slots.size
        if self.pool is None:
            g, d = random_genomes(self.founder_rng, n), np.zeros(n, np.int64)
        elif self.mode == "ordered":
            g, d = self.pool["genomes"], self.pool["depth"]
            if g.shape[0] != n:
                raise ValueError(f"ordered founders: pool has {g.shape[0]}, slots {n}")
            ps = self.pool["sex"]
            bad = (ps != SEX_ANY) & (ps != sim.agents.sex[slots])
            if bad.any():
                raise ValueError("ordered founders: pool sexes do not match the founders")
        else:
            g, d = self._sample(sim.agents.sex[slots])
        self.G[slots] = g
        self.depth[slots] = d
        self.preg_ok[slots] = False

    def _sample(self, sexes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        ps = self.pool["sex"]
        pick = np.empty(sexes.size, dtype=np.int64)
        if np.all(ps == SEX_ANY):
            n_pool = ps.size
            pick[:] = self.founder_rng.choice(n_pool, size=sexes.size,
                                              replace=sexes.size > n_pool)
        else:
            for s in (SEX_F, SEX_M):
                rows = np.flatnonzero(sexes == s)
                if rows.size == 0:
                    continue
                cand = np.flatnonzero((ps == s) | (ps == SEX_ANY))
                if cand.size == 0:
                    raise ValueError(f"founder pool has no genome for sex {s}")
                k = min(rows.size, cand.size)
                first = self.founder_rng.choice(cand, size=k, replace=False)
                rest = (self.founder_rng.choice(cand, size=rows.size - k, replace=True)
                        if rows.size > k else np.zeros(0, np.int64))
                pick[rows] = np.concatenate([first, rest])
        return self.pool["genomes"][pick], self.pool["depth"][pick]

    def conceive(self, sim: Universe25Sim, female: int, cands: list[int]) -> None:
        """The sire: one of the breeding pass's eligible males of her cell, drawn uniformly; his
        genome goes into her pregnancy."""
        sire = int(cands[int(self.gen.integers(len(cands)))])
        self.preg[female] = self.G[sire]
        self.preg_depth[female] = self.depth[sire]
        self.preg_ok[female] = True
        self.n_conceptions += 1

    def birth(self, sim: Universe25Sim, mother: int, pup: int) -> None:
        """One parent per pup (mother or sire, 1/2 each), copied with mutation."""
        from_sire = bool(self.gen.random() < 0.5) and bool(self.preg_ok[mother])
        if from_sire:
            parent, d = self.preg[mother], int(self.preg_depth[mother])
            self.n_from_sire += 1
        else:
            parent, d = self.G[mother], int(self.depth[mother])
        self.G[pup] = mutate(self.gen, parent, self.sd)
        self.depth[pup] = d + 1
        self.preg_ok[pup] = False
        self.n_births += 1

    # ------------------------------------------------------------ choice
    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray,
               rng: np.random.Generator | None = None) -> np.ndarray:
        if self.G is None:
            self._ensure(sim)
        if self.builder is None or self.builder.world is not sim.world:
            self.builder = ObservationBuilder(sim.world, version=5)
        obs = self.builder.build(sim, idx)
        z = logits(self.G[idx], obs).astype(np.float64)
        z = np.where(allowed, z, -1e8)  # invalid-action mask on the logits
        z -= z.max(axis=1, keepdims=True)
        r = self.rng if rng is None else rng
        return sample_masked(np.exp(z), allowed, r.random(idx.size))

    # ------------------------------------------------------------ export
    def adults(self, sim: Universe25Sim) -> dict[str, np.ndarray]:
        """Genomes, pedigree depths and sexes of the adults alive now (age >= maturity)."""
        a = sim.agents
        idx = np.flatnonzero(a.alive & (a.age_days >= sim.cfg.biology.maturity_days))
        return {"slots": idx, "genomes": self.G[idx].copy(), "depth": self.depth[idx].copy(),
                "sex": a.sex[idx].astype(np.int64)}
