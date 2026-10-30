"""CUDA Graph capture for the Warp post-step (stress/mortality/cells).

Phase-2 hybrid: host NumPy owns actions/breeding; Warp owns density stress,
mortality, and cell updates. Capture lives in WarpTickEngine when
use_cuda_graph=True (dens_frac lives in a device buffer so replay stays valid).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CudaGraphTick:
    enabled: bool = False
    backend: str = "numpy"
    device: str = "cpu"
    warmup_ticks: int = 3
    _graph: Any = field(default=None, repr=False)
    _captures: int = 0
    _replays: int = 0
    _engine: Any = field(default=None, repr=False)

    def bind_engine(self, engine: Any) -> None:
        self._engine = engine

    def maybe_capture(self, tick_fn: Callable[[], None]) -> Callable[[], None]:
        """Legacy hook; real capture is inside WarpTickEngine._warp_post_step."""
        return tick_fn

    def status(self) -> dict[str, Any]:
        eng = self._engine
        if eng is not None:
            st = eng.status()
            return {
                "enabled": bool(self.enabled),
                "backend": self.backend,
                "device": self.device,
                "graph_captured": bool(st.get("graph_ready")),
                "captures": 1 if st.get("graph_ready") else 0,
                "replays": int(st.get("n_graph_replays", 0)),
                "n_launches": int(st.get("n_launches", 0)),
                "phase": "warp_hybrid_post_step",
            }
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "device": self.device,
            "graph_captured": self._graph is not None,
            "captures": self._captures,
            "replays": self._replays,
            "phase": "numpy_host",
        }
