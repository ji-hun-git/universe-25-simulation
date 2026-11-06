"""Homeostatic drive-reduction reward (Keramati & Gutkin 2014) — the only reward in phase 4.

Eight drives (amended 2026-11-06, Jason): the seven preregistered ones plus `maternal_need`, a
nursing female's motivation set by her own litter's hunger (agents/drives.py). With the seven
alone the learner never nursed and its pups starved (NOTES 2026-11-06 → P4-2).

    delta_i = clip(h_i / S, 0, 1)                 setpoint 0 for every drive, S = 1.5 (drive clip)
    D(h)    = (sum_i w_i * delta_i ** N) ** (1/M) N = 4, M = 2, w_i = 1 (K&G need N > M > 1;
                                                   Dulberg et al. 2023 used 4 / 2)
    r       = D(h_t) - D(h_t+1)                   drive reduction between consecutive policy calls
    death   : r = D(h_t) - D_MAX, then the transition is terminal

A function of the drives alone: no drive-independent term (Keramati & Gutkin's "palatability"
term is what produced overeating), no curiosity / novelty / count bonus (prediction-error bonuses
fixate on the least predictable input, which in a colony is other mice), nothing named play (H2).
Rewards are clipped to the physically possible range [-D_MAX, D_MAX].
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from universe25.agents.drives import maternal_need

if TYPE_CHECKING:  # pragma: no cover
    from universe25.agents.state import AgentSoA

DRIVES: tuple[str, ...] = ("hunger", "thirst", "fatigue", "social_drive", "curiosity", "boredom",
                           "stress", "maternal_need")
SCALE = 1.5
N_EXP = 4.0
M_EXP = 2.0
WEIGHTS = np.ones(len(DRIVES))


def deviations(drives: np.ndarray) -> np.ndarray:
    """(m, 8) drive levels -> (m, 8) deviations from the setpoint in [0, 1]."""
    return np.clip(np.asarray(drives, dtype=np.float64) / SCALE, 0.0, 1.0)


def contributions(drives: np.ndarray) -> np.ndarray:
    """Per-drive terms w_i * delta_i ** N (m, 8), logged so reward hacking of one drive shows."""
    return WEIGHTS * deviations(drives) ** N_EXP


def drive(drives: np.ndarray) -> np.ndarray:
    """D per row."""
    return contributions(drives).sum(axis=1) ** (1.0 / M_EXP)


D_MAX = float(drive(np.full((1, len(DRIVES)), SCALE))[0])  # every drive at its maximum


def drive_reduction(d_before: np.ndarray, d_after: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(d_before, float) - np.asarray(d_after, float), -D_MAX, D_MAX)


def terminal_reward(d_before: np.ndarray) -> np.ndarray:
    """Death: the drives jump to their maximum and stay there."""
    return np.asarray(d_before, float) - D_MAX


def read_drives(agents: AgentSoA, idx: np.ndarray) -> np.ndarray:
    """(m, 8) drive levels of the agents `idx`: seven from the SoA, maternal_need derived."""
    cols = [getattr(agents, k)[idx].astype(np.float64) for k in DRIVES[:-1]]
    cols.append(maternal_need(agents, idx))
    return np.stack(cols, axis=1)
