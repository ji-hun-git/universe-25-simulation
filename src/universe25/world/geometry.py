"""Calhoun pen geometry: 101 x 101 in, 16 cells, 256 nests, food / water per cell.

Two layouts (`geometry.layout`): "grid", the 4 x 4 grid of the frozen 2m colony (bit-identical),
and "calhoun" (replica v2, docs/REPLICA_V2.md M1): 16 triangular cells that tile the floor, each
with its 25.25-in base on a wall and its apex at the centre (Calhoun 1973 p. 82; Marsden 1972
p. 7: "triangular floor space"), four mesh tunnels along its wall segment with four box levels
each, a wall hopper at the segment's right-hand end and a water platform above the tunnels, and
a ring stand at the triangle's centroid. Walls are clipped as before; partitions are only markers
(mice step over them), so movement is unconstrained."""
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
    level: int = 0  # calhoun layout: box level in its tunnel (0 lowest, 8 in above the floor)


@dataclass
class PlayObject:
    id: int
    kind: str  # ball | tunnel | ramp
    x: float
    y: float
    radius: float
    vx: float = 0.0  # ball physics (P4-13): velocity, inches per free-time sub-step
    vy: float = 0.0


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
    layout: str = "grid"
    n_cells_x: int = 4
    n_cells_y: int = 4
    withdraw_xy: tuple[float, float] = (20.0, 20.0)  # where withdrawn animals drift to
    ring_xy: tuple[tuple[float, float], ...] = ()  # calhoun layout: one ring stand per cell

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    def cells_of(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Cell index of positions (vectorised). Grid: the frozen colony's arithmetic, kept
        exactly; calhoun: the triangle whose wall segment the ray from the centre crosses."""
        if self.layout == "grid":
            nx, ny = self.n_cells_x, self.n_cells_y
            cw = self.width / nx
            ch = self.height / ny
            ix = np.clip((x / cw).astype(int), 0, nx - 1)
            iy = np.clip((y / ch).astype(int), 0, ny - 1)
            return iy * nx + ix
        return calhoun_cells_of(np.asarray(x, np.float64), np.asarray(y, np.float64),
                                self.width, self.height)

    @property
    def n_nests(self) -> int:
        return len(self.nests)

    def cell_index(self, x: float, y: float) -> int:
        if self.layout != "grid":
            return int(self.cells_of(np.array([x]), np.array([y]))[0])
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


CALHOUN_TUNNELS = (0.15, 0.31, 0.47, 0.63)  # tunnel positions along a cell's wall segment
CALHOUN_HOPPER = 0.83  # the hopper, touching the right-hand tunnel (1973 p. 82)
CALHOUN_WATER = 0.39  # the water platform above the tunnels
WALL_OFFSET = 0.5  # inches into the pen from the wall (positions stay inside [0.5, W - 0.5])


def _wall_point(wall: int, u: float, W: float, H: float, off: float = 0.0) -> tuple[float, float]:
    """A point u inches along wall `wall` (0 bottom, 1 right, 2 top, 3 left; counter-clockwise
    from the corner (0, 0)), `off` inches into the pen."""
    if wall == 0:
        return (u, off)
    if wall == 1:
        return (W - off, u)
    if wall == 2:
        return (W - u, H - off)
    return (off, H - u)


def calhoun_cells_of(x: np.ndarray, y: np.ndarray, W: float, H: float) -> np.ndarray:
    """Triangular cells: the perimeter coordinate s (counter-clockwise from (0, 0)) of the point
    where the ray from the centre through (x, y) meets the wall, in segments of perimeter / 16."""
    cx, cy = W / 2.0, H / 2.0
    dx, dy = x - cx, y - cy
    ax, ay = np.abs(dx), np.abs(dy)
    horiz = ax * H >= ay * W  # the ray meets the left or right wall
    safe_ax = np.maximum(ax, 1e-12)
    safe_ay = np.maximum(ay, 1e-12)
    px = np.where(horiz, cx + np.sign(dx) * cx, cx + dx * cy / safe_ay)
    py = np.where(horiz, cy + dy * cx / safe_ax, cy + np.sign(dy) * cy)
    s = np.where(horiz & (dx >= 0), W + py,
                 np.where(horiz, 2 * W + H + (H - py),
                          np.where(dy < 0, px, W + H + (W - px))))
    s = np.where((ax < 1e-12) & (ay < 1e-12), 0.0, s)
    seg = 2.0 * (W + H) / 16.0
    return np.clip((s / seg).astype(int), 0, 15)


def build_calhoun(geo: GeometryConfig, pg: PlaygroundConfig, seed: int) -> World:
    W, H = geo.width_in, geo.height_in
    L = W / 4.0  # 25.25 in of wall per cell
    cx, cy = W / 2.0, H / 2.0
    cells: list[Cell] = []
    nests: list[Nest] = []
    rings: list[tuple[float, float]] = []
    for cid in range(16):
        wall, k = divmod(cid, 4)
        u0, u1 = k * L, (k + 1) * L
        p0, p1 = _wall_point(wall, u0, W, H), _wall_point(wall, u1, W, H)
        xs, ys = (p0[0], p1[0], cx), (p0[1], p1[1], cy)
        food = _wall_point(wall, u0 + CALHOUN_HOPPER * L, W, H, WALL_OFFSET)
        water = _wall_point(wall, u0 + CALHOUN_WATER * L, W, H, WALL_OFFSET)
        cell_nests: list[int] = []
        for f in CALHOUN_TUNNELS:
            tx, ty = _wall_point(wall, u0 + f * L, W, H, WALL_OFFSET)
            for level in range(4):
                nests.append(Nest(id=len(nests), cell_id=cid, x=tx, y=ty, level=level))
                cell_nests.append(len(nests) - 1)
        rings.append((sum(xs) / 3.0, sum(ys) / 3.0))
        cells.append(Cell(id=cid, ix=k, iy=wall, x0=min(xs), y0=min(ys), x1=max(xs),
                          y1=max(ys), food_xy=food, water_xy=water,
                          nest_ids=tuple(cell_nests)))
    assert len(nests) == 256
    return World(width=W, height=H, cells=cells, nests=nests, playground_enabled=pg.enabled,
                 playground_bounds=(pg.x0, pg.y0, pg.x1, pg.y1),
                 play_objects=_play_objects(pg, seed), capacity_design=geo.capacity_design,
                 layout="calhoun", n_cells_x=geo.n_cells_x, n_cells_y=geo.n_cells_y,
                 withdraw_xy=(cx, cy), ring_xy=tuple(rings))


def build_world(geo: GeometryConfig, pg: PlaygroundConfig, seed: int = 7100) -> World:
    if geo.layout == "calhoun":
        return build_calhoun(geo, pg, seed)
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

    return World(
        width=geo.width_in,
        height=geo.height_in,
        cells=cells,
        nests=nests,
        playground_enabled=pg.enabled,
        playground_bounds=(pg.x0, pg.y0, pg.x1, pg.y1),
        play_objects=_play_objects(pg, seed),
        capacity_design=geo.capacity_design,
        n_cells_x=geo.n_cells_x,
        n_cells_y=geo.n_cells_y,
    )


def _play_objects(pg: PlaygroundConfig, seed: int) -> list[PlayObject]:
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
    return play_objects
