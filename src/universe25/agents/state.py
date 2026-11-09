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
# Action space v2 (P4-12, PHASE4_DESIGN.md 1.8): generic movement primitives a policy controls.
# Free-time actions with the relief of their family; no new reward, no play semantics.
ACT_RUN_ON = 11  # locomotor: along the agent's own heading
ACT_TURN_BACK = 12  # locomotor: against the agent's own heading
ACT_BACK_OFF = 13  # object: radially away from the nearest object
ACT_CIRCLE = 14  # object: counter-clockwise around the nearest object
N_ACTIONS = 15
N_BASE_ACTIONS = 11  # action space v1: what the heuristic and v2 weight files choose among
LOCO_FAMILY = (ACT_EXPLORE, ACT_RUN_ON, ACT_TURN_BACK)
OBJECT_FAMILY = (ACT_MANIPULATE, ACT_BACK_OFF, ACT_CIRCLE)

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
    heading: np.ndarray  # radians, direction of the agent's last move (action space v2)
    recent_action: np.ndarray  # most recent action, free-time sub-steps included (obs v3)
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
            heading=z(np.float32),
            recent_action=z(np.int8, ACT_REST),
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
    """Choose the compute backend. `auto` is the NumPy reference path: the Warp path lacks three
    biology processes (homeless-nest adoption, the low-rank nest kick, young-female maternal
    competence), so it runs only when requested explicitly (review 2026-11-09; until then
    `auto` picked Warp whenever CUDA worked)."""
    req = requested
    if req == "auto":
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
