"""Future RL vectorized env spec (Gymnasium / Isaac Lab style).

Not implemented in phase 1 — agents are need-driven, not policies.
This file freezes the interface so a Torch/Warp training loop can land later
without changing the world schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class VecEnvSpec:
    """Isaac Lab / Gymnasium-shaped contract."""

    id: str = "Universe25-Play-v0"
    num_envs: int = 64
    backend: str = "warp"
    observation_terms: tuple[str, ...] = (
        "proprio",  # hunger, thirst, fatigue, stress, energy, curiosity, boredom
        "local_density",
        "playground_relative",
        "nearest_object",
        "nearest_conspecific",
    )
    action_space: str = "discrete_11"  # matches N_ACTIONS; or continuous later
    reward_terms_allowed: tuple[str, ...] = (
        "survival",  # energy / not-dead
        "homeostasis",
        # H2: NEVER "play", bout, motif, exaggeration, …
    )
    reward_terms_forbidden: tuple[str, ...] = (
        "play",
        "bout",
        "motif",
        "playfulness",
        "explore_bonus_labeled_play",
    )
    train_stack: str = "pytorch"  # PPO via skrl / rsl_rl / cleanrl
    notes: str = (
        "PlayScore is evaluation-only. Train on survival+homeostasis+generic curiosity; "
        "evaluate F,V,D,S,G as unvalidated."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "num_envs": self.num_envs,
            "backend": self.backend,
            "observation_terms": list(self.observation_terms),
            "action_space": self.action_space,
            "reward_terms_allowed": list(self.reward_terms_allowed),
            "reward_terms_forbidden": list(self.reward_terms_forbidden),
            "train_stack": self.train_stack,
            "notes": self.notes,
            "status": "spec_only",
        }
