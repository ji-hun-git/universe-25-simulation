"""Optional Warp/Torch device buffers (phase-1 kernels land here)."""
from __future__ import annotations

from typing import Any

import numpy as np

from universe25.agents.state import AgentSoA, BackendName


def try_warp_mirror(agents: AgentSoA, device: str) -> dict[str, Any] | None:
    """Allocate Warp arrays mirroring SoA floats. Returns None if Warp unavailable."""
    try:
        import warp as wp
    except Exception:
        return None
    wp.init()
    n = agents.capacity
    return {
        "x": wp.array(agents.x, dtype=wp.float32, device=device),
        "y": wp.array(agents.y, dtype=wp.float32, device=device),
        "hunger": wp.array(agents.hunger, dtype=wp.float32, device=device),
        "thirst": wp.array(agents.thirst, dtype=wp.float32, device=device),
        "stress": wp.array(agents.stress, dtype=wp.float32, device=device),
        "energy": wp.array(agents.energy, dtype=wp.float32, device=device),
        "alive": wp.array(agents.alive.astype(np.int32), dtype=wp.int32, device=device),
        "backend": "warp",
        "device": device,
    }
