"""Record a run for the viewer (`viewer/`): the pen and one frame per day, or every tick (and
every free-time sub-step under the P4-13 physics) inside fine windows, to
`_output/viewer/<name>.u25` in the format of `scripts/viewer_frames.py`, with a summary beside
it (`<name>.json`) and the run's own files (metrics.parquet, config.json) in `<name>_run/`.

usage:
  python scripts/viewer_record.py --name ref_7000
  python scripts/viewer_record.py --name universe25_7001 --colony universe25 --seed 7001
  python scripts/viewer_record.py --name substrate_7000 --days 200 --free-substeps 12 \
      --ball-physics --fine 150:1

The simulator is untouched (scripts/viewer_frames.py only reads), so the run is the run
`main.py` makes from the same config, seed and overrides."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from viewer_frames import ROOT, capture, hook_substeps, pack, world_meta  # noqa: E402

from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402

OUT = ROOT / "_output" / "viewer"


def parse_windows(spec: str | None) -> list[tuple[float, float]]:
    """'450:2,700:1' -> [(450, 452), (700, 701)] (start day, end day)."""
    if not spec:
        return []
    out = []
    for part in spec.split(","):
        start, length = (float(v) for v in part.split(":"))
        out.append((start, start + length))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--name", required=True, help="recording name (file stem)")
    p.add_argument("--config", default=str(ROOT / "configs" / "default.yaml"))
    p.add_argument("--colony", default=None, help="a named colony (universe25.colonies) in "
                                                  "place of --config, with its fitted member")
    p.add_argument("--seed", type=int, default=7000)
    p.add_argument("--days", type=float, default=None, help="default: the config's")
    p.add_argument("--every", type=float, default=1.0, help="days between coarse frames")
    p.add_argument("--fine", default=None, help="windows day:length captured every tick")
    p.add_argument("--backend", default="numpy", choices=["numpy", "warp", "auto"])
    p.add_argument("--playground", default=None, choices=["on", "off"])
    p.add_argument("--free-substeps", type=int, default=None)
    p.add_argument("--ball-physics", action="store_true")
    p.add_argument("--coat", default=None, choices=["balbc", "cb6_cross", "wild_type"],
                   help="coat founders (default: the config's, BALB/c)")
    p.add_argument("--weight-effects", action="store_true",
                   help="let body weight act on fights, conception and survival (uncalibrated)")
    a = p.parse_args(argv)

    overrides: dict = {"seed": a.seed, "backend": a.backend, "snapshot_every_days": 0}
    if a.backend == "numpy":
        overrides["device"] = "cpu"
    if a.days is not None:
        overrides["days"] = a.days
    if a.free_substeps is not None:
        overrides["free_substeps"] = a.free_substeps
    pg: dict = {}
    if a.playground is not None:
        pg["enabled"] = a.playground == "on"
    if a.ball_physics:
        pg["ball_physics"] = True
    if pg:
        overrides["playground"] = pg
    if a.coat is not None:
        overrides["coat"] = {"founders": a.coat}
    if a.weight_effects:
        overrides["body"] = {"weight_effects": True}
    if a.colony:
        from universe25.colonies import colony_overrides, deep_merge

        path, member = colony_overrides(a.colony)
        a.config = str(ROOT / path)
        overrides = deep_merge(member, overrides)
    cfg = load_config(a.config, overrides)

    OUT.mkdir(parents=True, exist_ok=True)
    sim = Universe25Sim(cfg, OUT / f"{a.name}_run")
    windows = parse_windows(a.fine)

    def fine(day: float) -> bool:
        return any(s <= day < e for s, e in windows)

    frames = [capture(sim, 0.0)]
    hook_substeps(sim, lambda s, j, t: frames.append(capture(s, t, sub=j + 1))
                  if fine(s.day) else None)
    per_coarse = max(1, round(a.every * cfg.ticks_per_day))
    total = int(cfg.days * cfg.ticks_per_day)
    t0 = time.perf_counter()
    for _ in range(total):
        start = sim.day
        sim.step()
        if fine(start) or sim.tick % per_coarse == 0:
            frames.append(capture(sim))
        if sim.tick % (100 * cfg.ticks_per_day) == 0:
            print(f"day {sim.day:7.1f}  N {sim.agents.n_alive:5d}  frames {len(frames):6d}  "
                  f"{time.perf_counter() - t0:6.0f} s", flush=True)
        if sim.agents.n_alive == 0 and sim.day > 100:
            frames.append(capture(sim))
            break
    wall = time.perf_counter() - t0
    sim.logger.close()

    summary = {
        "name": a.name, "config": str(Path(a.config).resolve().relative_to(ROOT)),
        "seed": a.seed, "days_simulated": round(sim.day, 4), "frames": len(frames),
        "fine_windows": windows, "wall_seconds": round(wall, 1),
        "peak_n": int(sim._peak_n), "peak_day": round(float(sim._peak_day), 3),
        "final_n": int(sim.agents.n_alive), "births": int(sim._births),
        "deaths": int(sim._deaths), "conceptions": int(sim._conceptions),
        "backend": str(sim.backend), "device": str(sim.device),
        "free_substeps": int(sim.free_substeps), "ball_physics": bool(sim.ball_physics),
        "recorded": time.strftime("%Y-%m-%d %H:%M"),
    }
    blob = pack(frames, {"world": world_meta(sim), "summary": summary})
    (OUT / f"{a.name}.u25").write_bytes(blob)
    (OUT / f"{a.name}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({**summary, "bytes": len(blob)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
