"""Newton / warp.sim playground rigid-body stub.

Installed on this machine: newton 1.7.0 (built on Warp). Phase-1 treats
playground objects as kinematic/point masses updated in NumPy. Phase-2 can
swap to Newton rigid bodies for balls/ramps the mice push.

Do not import newton at module top-level in the hot path until the physics
arm is enabled (kernel compile cost).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PlaygroundPhysicsConfig:
    enabled: bool = False
    engine: str = "newton"  # newton | warp.sim | kinematic
    substeps: int = 4
    gravity: float = -981.0  # inches/s^2-ish; tune in MJCF/USD units later


@dataclass
class PlaygroundPhysics:
    """Lazy Newton world handle."""

    cfg: PlaygroundPhysicsConfig
    _model: Any = None
    _state: Any = None
    status: str = "kinematic"

    def ensure(self) -> None:
        if not self.cfg.enabled:
            self.status = "kinematic"
            return
        if self._model is not None:
            return
        try:
            import newton  # noqa: F401
            import warp as wp

            wp.init()
            # API is pre-1.0 and evolves; construct in a dedicated experiment.
            self.status = "newton_available_not_built"
        except Exception as e:
            self.status = f"fallback_kinematic:{type(e).__name__}"

    def step(self, dt: float) -> None:
        if self._model is None:
            return
        # Future: newton solver substeps; write back object x,y into World.play_objects
        raise NotImplementedError("Newton playground step lands in phase 2")
