"""Calhoun pen geometry: 101x101 in, 16 cells, 256 nests, food/water per cell."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from universe25.config import GeometryConfig, PlaygroundConfig


@dataclass(frozen=True)
class Cell:
    id: int
    ix: int
    iy: int
    x0: float
    y0: float
    x1: float
    y1: float
    food_xy: tuple[float, float]
    water_xy: tuple[float, float]
    nest_ids: tuple[int, ...]


@dataclass(frozen=True)
class Nest:
    id: int
    cell_id: int
    x: float
    y: float
    capacity: int = 15  # ~3840/256


@dataclass
class PlayObject:
    id: int
    kind: str  # ball | tunnel | ramp
    x: float
    y: float
    radius: float


@dataclass
class World:
    width: float
    height: float
    cells: list[Cell]
    nests: list[Nest]
    playground_enabled: bool
    playground_bounds: tuple[float, float, float, float]  # x0,y0,x1,y1
    play_objects: list[PlayObject]
    capacity_design: int

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    @property
    def n_nests(self) -> int:
        return len(self.nests)

    def cell_index(self, x: float, y: float) -> int:
        nx = len({c.ix for c in self.cells})
        ny = len({c.iy for c in self.cells})
        cw = self.width / nx
        ch = self.height / ny
        ix = int(np.clip(x / cw, 0, nx - 1))
        iy = int(np.clip(y / ch, 0, ny - 1))
        return iy * nx + ix

    def in_playground(self, x: float, y: float) -> bool:
        if not self.playground_enabled:
            return False
        x0, y0, x1, y1 = self.playground_bounds
        return (x0 <= x <= x1) and (y0 <= y <= y1)

    def local_density(self, x: float, y: float, positions: np.ndarray, alive: np.ndarray, radius: float = 8.0) -> float:
        """Count alive agents within radius (inches), excluding self handled by caller."""
        if positions.size == 0:
            return 0.0
        d2 = (positions[:, 0] - x) ** 2 + (positions[:, 1] - y) ** 2
        return float(np.sum((d2 <= radius * radius) & alive))


def build_world(geo: GeometryConfig, pg: PlaygroundConfig, seed: int = 7100) -> World:
    cw = geo.width_in / geo.n_cells_x
    ch = geo.height_in / geo.n_cells_y
    cells: list[Cell] = []
    nests: list[Nest] = []
    nest_id = 0
    for iy in range(geo.n_cells_y):
        for ix in range(geo.n_cells_x):
            cid = iy * geo.n_cells_x + ix
            x0, y0 = ix * cw, iy * ch
            x1, y1 = x0 + cw, y0 + ch
            # Food/water near cell center toward corridors (inner edge).
            fx = x0 + cw * 0.5
            fy = y0 + ch * 0.35
            wx = x0 + cw * 0.5
            wy = y0 + ch * 0.45
            cell_nests: list[int] = []
            # 4x4 nest grid along outer wall of each cell
            nside = int(np.sqrt(geo.nests_per_cell))
            assert nside * nside == geo.nests_per_cell
            for ny in range(nside):
                for nx in range(nside):
                    # Place nests along the periphery of the cell
                    if nx in (0, nside - 1) or ny in (0, nside - 1):
                        px = x0 + (nx + 0.5) / nside * cw
                        py = y0 + (ny + 0.5) / nside * ch
                    else:
                        px = x0 + (nx + 0.5) / nside * cw
                        py = y0 + (ny + 0.5) / nside * ch
                    nests.append(Nest(id=nest_id, cell_id=cid, x=px, y=py))
                    cell_nests.append(nest_id)
                    nest_id += 1
            # If nests_per_cell > periphery count from loop, we already placed nside^2
            cells.append(
                Cell(
                    id=cid,
                    ix=ix,
                    iy=iy,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    food_xy=(fx, fy),
                    water_xy=(wx, wy),
                    nest_ids=tuple(cell_nests),
                )
            )

    assert len(nests) == geo.n_cells_x * geo.n_cells_y * geo.nests_per_cell == 256

    rng = np.random.default_rng(seed)
    play_objects: list[PlayObject] = []
    if pg.enabled:
        oid = 0
        for _ in range(pg.n_balls):
            play_objects.append(
                PlayObject(
                    id=oid,
                    kind="ball",
                    x=float(rng.uniform(pg.x0 + 1, pg.x1 - 1)),
                    y=float(rng.uniform(pg.y0 + 1, pg.y1 - 1)),
                    radius=1.2,
                )
            )
            oid += 1
        for _ in range(pg.n_tunnels):
            play_objects.append(
                PlayObject(
                    id=oid,
                    kind="tunnel",
                    x=float(rng.uniform(pg.x0 + 2, pg.x1 - 2)),
                    y=float(rng.uniform(pg.y0 + 2, pg.y1 - 2)),
                    radius=2.0,
                )
            )
            oid += 1
        for _ in range(pg.n_ramps):
            play_objects.append(
                PlayObject(
                    id=oid,
                    kind="ramp",
                    x=float(rng.uniform(pg.x0 + 2, pg.x1 - 2)),
                    y=float(rng.uniform(pg.y0 + 2, pg.y1 - 2)),
                    radius=2.5,
                )
            )
            oid += 1

    return World(
        width=geo.width_in,
        height=geo.height_in,
        cells=cells,
        nests=nests,
        playground_enabled=pg.enabled,
        playground_bounds=(pg.x0, pg.y0, pg.x1, pg.y1),
        play_objects=play_objects,
        capacity_design=geo.capacity_design,
    )
