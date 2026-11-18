"""Viewer capture (scripts/viewer_frames.py) only reads the simulator: a run with a frame taken
at every tick and at every free-time sub-step (P4-13 ball physics, K = 12) ends in the same
state as the same run without capture. The frame codec round-trips (positions to 1/100 in,
stress and wounds to 1.5/255, headings to a 256th of a turn), payloads stay 4-byte aligned,
and the Calhoun layout's 16 triangles tile the pen."""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from universe25.config import SimConfig, load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402
from universe25.world.geometry import build_world  # noqa: E402
from viewer_frames import (  # noqa: E402
    capture,
    cell_polygons,
    hook_substeps,
    pack,
    unpack,
    world_meta,
)

DAYS = 120.0


def _cfg() -> SimConfig:
    cfg = SimConfig(seed=7003, days=DAYS, backend="numpy", device="cpu", max_agents=512,
                    ticks_per_day=6, log_every_ticks=24, snapshot_every_days=0, free_substeps=12,
                    arm_label="TRACK-E-U25-TEST")
    cfg.playground.enabled = True
    cfg.playground.ball_physics = True
    return cfg


def _digest(sim) -> str:
    a = sim.agents
    h = hashlib.sha256()
    for k in ("alive", "x", "y", "stress", "energy", "role", "age_days", "nest_id", "heading",
              "wounds", "cell_id", "in_playground"):
        h.update(np.ascontiguousarray(getattr(a, k)).tobytes())
    for o in sim.world.play_objects:
        h.update(np.array([o.x, o.y, o.vx, o.vy], dtype=np.float64).tobytes())
    h.update(np.array([sim._births, sim._deaths, sim._conceptions], dtype=np.int64).tobytes())
    return h.hexdigest()


def _run(with_capture: bool, out: Path):
    sim = Universe25Sim(_cfg(), out)
    frames: list = []
    if with_capture:
        hook_substeps(sim, lambda s, j, t: frames.append(capture(s, t, sub=j + 1)))
        frames.append(capture(sim, 0.0))
    for _ in range(int(DAYS * sim.cfg.ticks_per_day)):
        sim.step()
        if with_capture:
            frames.append(capture(sim))
    sim.logger.close()
    return sim, frames


def test_capture_is_read_only_and_codec_round_trips() -> None:
    with tempfile.TemporaryDirectory() as d:
        plain, _ = _run(False, Path(d) / "plain")
        seen, frames = _run(True, Path(d) / "seen")
    assert _digest(plain) == _digest(seen), "capture changed the run"
    assert seen._births > 0, "the window should include births"

    K, ticks = seen.free_substeps, int(DAYS * seen.cfg.ticks_per_day)
    assert len(frames) == 1 + ticks * K, len(frames)  # K - 1 sub-step frames + the tick's
    times = [m["t"] for m, _ in frames]
    assert all(b > a for a, b in zip(times, times[1:])), "frame times must increase"
    assert frames[-1][0]["t"] == round(seen.day, 6)

    blob = pack(frames[-3:], {"world": world_meta(seen)}, first=7)
    head, arrs = unpack(blob)
    assert [f["i"] for f in head["frames"]] == [7, 8, 9]
    assert all(f["off"] % 4 == 0 and f["len"] % 4 == 0 for f in head["frames"])
    w = head["world"]
    assert len(w["cells"]) == 16 and len(w["nests"]) == 256
    assert [315.0, 620.0] in w["landmarks"]["census"]

    a, last = seen.agents, arrs[-1]
    idx = np.flatnonzero(a.alive)
    assert head["frames"][-1]["n"] == idx.size
    assert np.array_equal(last["slot"], idx)
    assert np.abs(last["x"] / 100.0 - a.x[idx]).max() <= 0.0051
    assert np.abs(last["y"] / 100.0 - a.y[idx]).max() <= 0.0051
    assert np.abs(last["stress"] * 1.5 / 255 - np.clip(a.stress[idx], 0, 1.5)).max() <= 0.0031
    assert np.array_equal(last["role"], a.role[idx])
    assert np.array_equal(last["flags"] & 1, (a.sex[idx] == 1).astype(np.uint8))
    assert np.array_equal((last["flags"] >> 1) & 1, a.in_playground[idx].astype(np.uint8))
    assert np.array_equal(last["nest"], a.nest_id[idx])
    turn = last["heading"] * (2.0 * np.pi / 256.0) - a.heading[idx].astype(np.float64)
    assert np.abs(np.angle(np.exp(1j * turn))).max() <= np.pi / 256.0 + 1e-6
    assert w["format"] == 3
    b = seen.body
    assert np.abs(last["mass"] / 100.0 - b.mass[idx]).max() <= 0.0051
    assert np.abs(last["cond"] / 100.0 - b.cond[idx]).max() <= 0.0051
    assert np.array_equal(last["coat"], b.coat[idx])
    assert np.array_equal(last["gest"] > 0, a.gestating[idx] > 0)
    assert sum(head["frames"][-1]["roles"]) == idx.size
    assert sum(head["frames"][-1]["cells"]) == idx.size


def test_calhoun_triangles_tile_the_pen() -> None:
    cfg = load_config(ROOT / "configs" / "replica_v2.yaml", {"seed": 7000})
    world = build_world(cfg.geometry, cfg.playground, seed=7000)
    polys = cell_polygons(world)
    assert len(polys) == 16 and all(len(p) == 3 for p in polys)
    area = 0.0
    for p in polys:
        (x0, y0), (x1, y1), (x2, y2) = p
        area += abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0
    assert abs(area - world.width * world.height) < 1e-6, area


def test_app_presets() -> None:
    """Every preset of the viewer server (and the app) builds its config; the Universe 25
    preset is Calhoun's pen without the playground, with its member's fitted parameters."""
    import json

    import viewer_serve as vs

    for name, preset in vs.PRESETS.items():
        cfg = vs.preset_config(name, {"seed": 7001})
        assert cfg.seed == 7001, name
        assert (ROOT / preset["config"]).is_file(), name
    cfg = vs.preset_config("universe25")
    assert cfg.geometry.layout == "calhoun" and not cfg.playground.enabled
    member = json.loads((ROOT / vs.PRESETS["universe25"]["member"]).read_text(encoding="utf-8"))
    for group, values in member["members"][0]["params"].items():
        for key, value in values.items():
            assert getattr(getattr(cfg, group), key) == value, (group, key)
    assert next(iter(vs.PRESETS)) == "universe25"  # the app's first choice


if __name__ == "__main__":
    test_capture_is_read_only_and_codec_round_trips()
    test_calhoun_triangles_tile_the_pen()
    test_app_presets()
    print("test_viewer: OK")
