"""Structure-of-arrays agent store (NumPy host mirror; optional Warp/Torch device)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

# Role codes
ROLE_PUP = 0
ROLE_JUVENILE = 1
ROLE_TERRITORIAL_MALE = 2
ROLE_SUBORDINATE_MALE = 3
ROLE_BREEDING_FEMALE = 4
ROLE_NURSING = 5
ROLE_WITHDRAWN = 6  # "beautiful ones"
ROLE_DEAD = 7

# Action codes (no PLAY action — manipulate/explore are generic)
ACT_REST = 0
ACT_FORAGE = 1
ACT_DRINK = 2
ACT_NEST = 3
ACT_SOCIAL = 4
ACT_EXPLORE = 5
ACT_MANIPULATE = 6  # interact with playground object (curiosity/boredom, NOT play reward)
ACT_AGGRESS = 7
ACT_MATE = 8
ACT_NURSE = 9
ACT_WITHDRAW = 10
N_ACTIONS = 11

SEX_F = 0
SEX_M = 1


@dataclass
class AgentSoA:
    """Fixed-capacity SoA. alive mask tracks occupancy."""

    capacity: int
    alive: np.ndarray
    sex: np.ndarray
    age_days: np.ndarray
    hunger: np.ndarray
    thirst: np.ndarray
    fatigue: np.ndarray
    stress: np.ndarray
    social_drive: np.ndarray
    aggression: np.ndarray
    maternal: np.ndarray  # 0..1 nursing investment
    rank: np.ndarray
    role: np.ndarray
    wounds: np.ndarray
    x: np.ndarray
    y: np.ndarray
    cell_id: np.ndarray
    nest_id: np.ndarray
    gestating: np.ndarray  # days left; 0 = not
    energy: np.ndarray  # homeostasis 0..1
    curiosity: np.ndarray
    boredom: np.ndarray
    last_action: np.ndarray
    in_playground: np.ndarray
    competence: np.ndarray  # social development 0..1; shaped while young, frozen at maturity
    maternal_cap: np.ndarray  # adult maternal capacity 0..1; eroded irreversibly under stress
    courtship_cap: np.ndarray  # male courtship capacity 0..1; eroded irreversibly under stress
    lifespan: np.ndarray  # age (days) past which the old-age hazard applies; per individual
    # bookkeeping
    n_alive: int = 0

    @staticmethod
    def create(capacity: int) -> "AgentSoA":
        z = lambda dtype, fill=0: np.full(capacity, fill, dtype=dtype)  # noqa: E731
        return AgentSoA(
            capacity=capacity,
            alive=z(np.bool_, False),
            sex=z(np.int8),
            age_days=z(np.float32),
            hunger=z(np.float32),
            thirst=z(np.float32),
            fatigue=z(np.float32),
            stress=z(np.float32),
            social_drive=z(np.float32),
            aggression=z(np.float32),
            maternal=z(np.float32),
            rank=z(np.float32),
            role=z(np.int8, ROLE_DEAD),
            wounds=z(np.float32),
            x=z(np.float32),
            y=z(np.float32),
            cell_id=z(np.int16, -1),
            nest_id=z(np.int16, -1),
            gestating=z(np.float32),
            energy=z(np.float32, 1.0),
            curiosity=z(np.float32, 0.3),
            boredom=z(np.float32, 0.1),
            last_action=z(np.int8, ACT_REST),
            in_playground=z(np.bool_, False),
            competence=z(np.float32, 1.0),
            maternal_cap=z(np.float32, 1.0),
            courtship_cap=z(np.float32, 1.0),
            lifespan=z(np.float32, 1.0e9),
            n_alive=0,
        )

    def free_slots(self, n: int) -> np.ndarray:
        idx = np.flatnonzero(~self.alive)
        if len(idx) < n:
            raise RuntimeError(f"capacity exhausted: need {n}, free {len(idx)}")
        return idx[:n]

    def positions(self) -> np.ndarray:
        return np.stack([self.x, self.y], axis=1)


BackendName = Literal["numpy", "torch", "warp"]


def pick_backend(requested: str, device: str) -> tuple[BackendName, str]:
    """Choose compute backend. Prefer Warp on CUDA; fall back to torch then numpy."""
    req = requested
    if req == "auto":
        # try warp cuda
        try:
            import warp as wp

            wp.init()
            if device in ("auto", "cuda"):
                try:
                    _ = wp.zeros(4, dtype=wp.float32, device="cuda:0")
                    return "warp", "cuda:0"
                except Exception:
                    pass
            return "numpy", "cpu"
        except Exception:
            pass
        try:
            import torch

            if torch.cuda.is_available() and device in ("auto", "cuda"):
                return "torch", "cuda"
        except Exception:
            pass
        return "numpy", "cpu"
    if req == "warp":
        import warp as wp

        wp.init()
        dev = "cuda:0" if device in ("auto", "cuda") else "cpu"
        return "warp", dev
    if req == "torch":
        import torch

        dev = "cuda" if (device in ("auto", "cuda") and torch.cuda.is_available()) else "cpu"
        return "torch", dev
    return "numpy", "cpu"
