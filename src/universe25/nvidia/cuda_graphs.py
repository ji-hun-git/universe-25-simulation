"""CUDA Graph capture scaffolding for the Warp tick loop.

Phase-1 host SoA still runs on NumPy; when Warp kernels own the step, capture
the graph once after warmup and replay with wp.capture_launch / torch.cuda.CUDAGraph.

This module is safe on CPU: capture() is a no-op unless device is CUDA and
backend is warp.
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

    def maybe_capture(self, tick_fn: Callable[[], None]) -> Callable[[], None]:
        """Return a callable that either runs tick_fn or replays a captured graph.

        For phase 1 we only record intent and always call tick_fn. When Warp
        kernels are the sole mutators of device buffers, replace the body with
        wp.capture_begin/end + capture_launch (or torch.cuda.CUDAGraph).
        """
        if not self.enabled or self.backend != "warp" or not str(self.device).startswith("cuda"):
            return tick_fn

        def wrapped() -> None:
            # Placeholder: real capture requires device-only side effects.
            # Documented in docs/NVIDIA_STACK.md.
            self._captures = max(self._captures, 1)
            tick_fn()
            self._replays += 1

        return wrapped

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "backend": self.backend,
            "device": self.device,
            "graph_captured": self._graph is not None,
            "captures": self._captures,
            "replays": self._replays,
            "phase": "scaffolding",
        }
