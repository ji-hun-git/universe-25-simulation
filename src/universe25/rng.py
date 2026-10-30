"""Deterministic seeded RNG helpers."""
from __future__ import annotations

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(int(seed))


def spawn_child_seed(rng: np.random.Generator) -> int:
    return int(rng.integers(7000, 7999))
