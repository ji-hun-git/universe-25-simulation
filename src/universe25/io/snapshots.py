"""State snapshots for a future WebGPU viewer (JSON lines + compact arrays)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from universe25.agents.state import AgentSoA
from universe25.world.geometry import World


class SnapshotWriter:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._index: list[dict] = []
        # Write world once
        self._world_written = False

    def write(self, day: float, agents: AgentSoA, world: World) -> Path:
        if not self._world_written:
            self._write_world(world)
            self._world_written = True
        alive = agents.alive
        payload = {
            "day": day,
            "n": int(alive.sum()),
            "x": agents.x[alive].astype(np.float32).tolist(),
            "y": agents.y[alive].astype(np.float32).tolist(),
            "role": agents.role[alive].astype(np.int8).tolist(),
            "sex": agents.sex[alive].astype(np.int8).tolist(),
            "stress": agents.stress[alive].astype(np.float32).tolist(),
            "energy": agents.energy[alive].astype(np.float32).tolist(),
            "in_playground": agents.in_playground[alive].astype(bool).tolist(),
            "play_objects": [
                {"id": o.id, "kind": o.kind, "x": o.x, "y": o.y, "r": o.radius}
                for o in world.play_objects
            ],
        }
        name = f"snap_day_{int(day):05d}.json"
        path = self.directory / name
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        self._index.append({"day": day, "file": name, "n": payload["n"]})
        (self.directory / "index.json").write_text(json.dumps(self._index), encoding="utf-8")
        return path

    def _write_world(self, world: World) -> None:
        meta = {
            "width": world.width,
            "height": world.height,
            "n_cells": world.n_cells,
            "n_nests": world.n_nests,
            "playground_enabled": world.playground_enabled,
            "playground_bounds": list(world.playground_bounds),
            "capacity_design": world.capacity_design,
            "cells": [
                {
                    "id": c.id,
                    "x0": c.x0,
                    "y0": c.y0,
                    "x1": c.x1,
                    "y1": c.y1,
                    "food": list(c.food_xy),
                    "water": list(c.water_xy),
                }
                for c in world.cells
            ],
            "nests": [{"id": n.id, "cell_id": n.cell_id, "x": n.x, "y": n.y} for n in world.nests],
        }
        (self.directory / "world.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
