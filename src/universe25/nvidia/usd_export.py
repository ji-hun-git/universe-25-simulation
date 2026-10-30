"""Optional Omniverse/USD export of the pen (pxr is installed; omni kit is not).

Writes a lightweight USDA of cell floors + playground AABB + nest points.
Full Omniverse live session is out of scope for phase 1.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from universe25.world.geometry import World


def export_pen_usda(world: "World", path: Path) -> dict:
    path = Path(path)
    try:
        from pxr import Usd, UsdGeom, Gf
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage, "/Universe25")
    pen = UsdGeom.Cube.Define(stage, "/Universe25/Pen")
    pen.CreateSizeAttr(1.0)
    # scale to inches
    UsdGeom.XformCommonAPI(pen).SetScale(
        Gf.Vec3f(world.width / 2.0, world.height / 2.0, 0.5)
    )
    UsdGeom.XformCommonAPI(pen).SetTranslate(
        Gf.Vec3f(world.width / 2.0, world.height / 2.0, 0.0)
    )
    if world.playground_enabled:
        x0, y0, x1, y1 = world.playground_bounds
        pg = UsdGeom.Cube.Define(stage, "/Universe25/Playground")
        UsdGeom.XformCommonAPI(pg).SetScale(Gf.Vec3f((x1 - x0) / 2.0, (y1 - y0) / 2.0, 0.25))
        UsdGeom.XformCommonAPI(pg).SetTranslate(Gf.Vec3f((x0 + x1) / 2.0, (y0 + y1) / 2.0, 0.25))
    for n in world.nests:
        nest = UsdGeom.Sphere.Define(stage, f"/Universe25/Nests/nest_{n.id:03d}")
        nest.CreateRadiusAttr(0.4)
        UsdGeom.XformCommonAPI(nest).SetTranslate(Gf.Vec3f(n.x, n.y, 0.4))
    stage.GetRootLayer().Save()
    return {"ok": True, "path": str(path), "nests": world.n_nests}
