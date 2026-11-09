"""Run provenance and trajectory hashes (Tier 0 of docs/REVIEW_2026-11-09.md).

- `manifest(cfg)`: commit, dirty flag, config hash, library versions, platform and schema
  versions. Every `Universe25Sim` writes it (`manifest.json`, and inside `run.json`) together
  with the resolved config (`config.json`).
- `config_hash(cfg)`: sha256 of the canonical JSON of the resolved config.
- `trajectory_hash(cfg, days)`: sha256 over every agent field, the resource stocks and the play
  objects after every tick, then the state of every random stream. It is the golden-hash
  primitive (`scripts/golden_hashes.py`, `tests/golden/trajectories.json`).

Nothing here draws from a random stream or writes simulation state.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.metadata as md
import json
import platform
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from universe25.config import SimConfig
    from universe25.sim import Universe25Sim

ROOT = Path(__file__).resolve().parents[2]

# Versions of the data layouts a run produces or reads. Bump the entry whenever its layout
# changes; readers check them instead of guessing from shapes.
SCHEMAS: dict[str, Any] = {
    "run_json": 2,  # 2: manifest embedded (2026-11-09)
    "metrics_parquet": 2,  # 2: removed_cum column (2026-11-09)
    "trace": 2,  # 2: obj_x / obj_y and the movement model in meta (rules v7)
    "observation": 5,  # builder default; v2-v4 weight files keep their layouts
    "action_space": 2,  # 15 actions (P4-12)
}
_PACKAGES = ("numpy", "pyarrow", "pydantic", "PyYAML", "torch", "warp-lang", "optuna")


def config_hash(cfg: SimConfig) -> str:
    """sha256 of the canonical JSON (sorted keys) of the resolved config."""
    blob = json.dumps(cfg.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def git_state() -> dict[str, Any]:
    """Commit and whether src/, configs/ or scripts/ have uncommitted changes (cached per
    process)."""
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT,
                              timeout=10).stdout.strip()

    try:
        commit = git("rev-parse", "HEAD") or "unknown"
        dirty = bool(git("status", "--porcelain", "--", "src", "configs", "scripts"))
    except (OSError, subprocess.SubprocessError):
        commit, dirty = "unknown", None
    return {"commit": commit, "dirty": dirty}


@lru_cache(maxsize=1)
def versions() -> dict[str, str]:
    """Python, platform and installed package versions (metadata only, no imports)."""
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for pkg in _PACKAGES:
        try:
            out[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            out[pkg] = "absent"
    return out


def manifest(cfg: SimConfig, **extra: Any) -> dict[str, Any]:
    from universe25.metrics.detectors import RULES  # numpy only; never read by a policy

    return {**git_state(), "config_sha256": config_hash(cfg), "versions": versions(),
            "schemas": {**SCHEMAS, "detector_rules": RULES}, **extra}


# ---------------------------------------------------------------- trajectory hashes
def _agent_fields(sim: Universe25Sim) -> list[np.ndarray]:
    a = sim.agents
    return [np.ascontiguousarray(getattr(a, f.name)) for f in dataclasses.fields(a)
            if isinstance(getattr(a, f.name), np.ndarray)]


def _stream_states(sim: Universe25Sim) -> str:
    """The states of every random stream the run uses, as canonical JSON."""
    st: dict[str, Any] = {"sim": sim.rng.bit_generator.state}
    if getattr(sim, "_sub_rng", None) is not None:
        st["substeps"] = sim._sub_rng.bit_generator.state
    pol = getattr(sim.policy, "rng", None)
    if pol is not None:
        st["policy"] = pol.bit_generator.state
    return json.dumps(st, sort_keys=True, default=str)


def trajectory_hash(cfg: SimConfig, days: float | None = None,
                    out_dir: Path | None = None) -> dict[str, Any]:
    """Run `cfg` for `days` (default cfg.days) and hash the trajectory: after every tick all
    agent arrays, n_alive, the food and water stocks and every play object's position and
    velocity; at the end the random streams. Trace files, when the config writes them, get a
    separate hash (fields in sorted order, meta excluded), so trace on and trace off can be
    compared on the trajectory alone."""
    from universe25.sim import Universe25Sim

    days = float(cfg.days if days is None else days)
    out = Path(out_dir) if out_dir is not None else Path(tempfile.mkdtemp(prefix="u25hash_"))
    sim = Universe25Sim(cfg, out)
    h = hashlib.sha256()
    for _ in range(int(round(days * cfg.ticks_per_day))):
        sim.step()
        for arr in _agent_fields(sim):
            h.update(arr.tobytes())
        h.update(np.int64(sim.agents.n_alive).tobytes())
        h.update(np.ascontiguousarray(sim.food).tobytes())
        h.update(np.ascontiguousarray(sim.water).tobytes())
        objs = sim.world.play_objects
        if objs:
            h.update(np.array([(o.x, o.y, o.vx, o.vy) for o in objs], np.float64).tobytes())
    h.update(_stream_states(sim).encode("utf-8"))
    res: dict[str, Any] = {"trajectory": h.hexdigest(), "n_alive": int(sim.agents.n_alive),
                           "births": int(sim._births), "deaths": int(sim._deaths)}
    if sim.trace is not None:
        th = hashlib.sha256()
        for f in sim.trace.close():
            with np.load(f) as z:
                for k in sorted(z.files):
                    if not k.startswith("meta_"):
                        th.update(np.ascontiguousarray(z[k]).tobytes())
        res["trace"] = th.hexdigest()
    return res
