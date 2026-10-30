"""Geometry invariants for Calhoun pen + playground."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import GeometryConfig, PlaygroundConfig
from universe25.world.geometry import build_world


def test_calhoun_counts() -> None:
    world = build_world(GeometryConfig(), PlaygroundConfig(enabled=True), seed=7100)
    assert world.width == 101.0 and world.height == 101.0
    assert world.n_cells == 16
    assert world.n_nests == 256
    assert world.capacity_design == 3840
    assert world.playground_enabled
    assert len(world.play_objects) == 8 + 4 + 2
    for o in world.play_objects:
        assert world.in_playground(o.x, o.y)


def test_playground_toggle() -> None:
    off = build_world(GeometryConfig(), PlaygroundConfig(enabled=False), seed=7100)
    assert not off.playground_enabled
    assert len(off.play_objects) == 0
    assert not off.in_playground(50.0, 50.0)


def test_cell_index_bounds() -> None:
    world = build_world(GeometryConfig(), PlaygroundConfig(enabled=False), seed=7100)
    assert world.cell_index(0.0, 0.0) == 0
    assert world.cell_index(100.9, 100.9) == 15


if __name__ == "__main__":
    test_calhoun_counts()
    test_playground_toggle()
    test_cell_index_bounds()
    print("test_geometry: OK")
