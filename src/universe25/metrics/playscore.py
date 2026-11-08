"""Provisional PlayScore components (gan formalization) — UNVALIDATED.

PlayScore = G * (1 - |F|) * V * D * S

Agents must NOT optimize this. Logged for later validation only.
No play reward is applied in the simulator.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from universe25.agents.state import N_BASE_ACTIONS


class PlayScoreAccumulator:
    def __init__(self) -> None:
        self._actions: list[np.ndarray] = []
        self._baseline_entropy = np.log(N_BASE_ACTIONS)  # action space v1 (comparability)

    def observe_actions(self, actions: np.ndarray) -> None:
        self._actions.append(np.asarray(actions, dtype=np.int8).copy())

    def reset_window(self) -> None:
        self._actions.clear()

    def components(self, *, v: float, g: float, action_entropy: float) -> dict[str, float]:
        # F: task-reward difference proxy — in need-driven phase-1 we have no external
        # task reward, so F≈0 by construction (agents are not reward-maxing a play term).
        F = 0.0
        V = float(v)
        # D: divergence from "serious" action mix (forage/drink/rest/nest/aggress/mate/nurse)
        # vs exploratory/manipulate. Use share of explore+manipulate as stand-in; full JS
        # divergence needs a serious baseline policy — marked unvalidated.
        if self._actions:
            acts = np.concatenate(self._actions)
            serious = {0, 1, 2, 3, 7, 8, 9, 10}  # rest,forage,drink,nest,aggress,mate,nurse,withdraw
            playful_like = {5, 6, 11, 12, 13, 14}  # explore, manipulate and their v2 families
            p_play = float(np.mean(np.isin(acts, list(playful_like)))) if len(acts) else 0.0
            D = p_play  # provisional, not true JS divergence
        else:
            D = 0.0
        S = float(action_entropy / max(1e-9, self._baseline_entropy))
        G = float(g)
        score = G * (1.0 - abs(F)) * V * D * S
        return {"F": F, "V": V, "D": D, "S": S, "G": G, "PlayScore": float(score)}
