"""Fast landmark evaluation for calibration (minimal I/O)."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from universe25.calib.priors import LANDMARKS, landmark_loss, params_to_overrides
from universe25.config import SimConfig, load_config
from universe25.sim import Universe25Sim


def _extract_landmarks(
    sim: Universe25Sim,
    days_hist: list[float],
    n_hist: list[int],
    births_hist: list[int],
    last_young_hist: list[float],
) -> dict[str, float]:
    days = np.asarray(days_hist, dtype=np.float64)
    ns = np.asarray(n_hist, dtype=np.float64)
    births = np.asarray(births_hist, dtype=np.float64)
    last_young = np.asarray(last_young_hist, dtype=np.float64)
    first_idx = np.flatnonzero(births > 0)
    first_litters = float(days[first_idx[0]]) if len(first_idx) else float("nan")
    n_315 = float(ns[np.argmin(np.abs(days - 315.0))]) if len(days) else float("nan")
    peak_i = int(np.argmax(ns)) if len(ns) else 0
    return {
        "first_litters_day": first_litters,
        "n_at_day_315": n_315,
        "peak_n": float(ns[peak_i]) if len(ns) else 0.0,
        "peak_day": float(days[peak_i]) if len(days) else 0.0,
        "last_young_day": float(np.max(last_young)) if len(last_young) else 0.0,
        "final_n": float(ns[-1]) if len(ns) else 0.0,
    }


def evaluate_params(
    params: dict[str, float],
    *,
    seed: int = 7000,
    days: float = 1600.0,
    ticks_per_day: int = 6,
    max_agents: int = 4096,
    base_config: Path | None = None,
    playground: bool = True,
) -> dict[str, Any]:
    """Run one seeded sim; return landmarks + loss. No parquet/snapshots."""
    overrides = params_to_overrides(params)
    overrides.update(
        {
            "seed": seed,
            "days": days,
            "ticks_per_day": ticks_per_day,
            "max_agents": max_agents,
            "backend": "numpy",
            "device": "cpu",
            "log_every_ticks": 10**9,
            "snapshot_every_days": 0,
            "arm_label": "TRACK-E-U25-CALIB",
            "playground": {"enabled": playground},
            "use_cuda_graph": False,
        }
    )
    if base_config is not None:
        cfg = load_config(base_config, overrides)
    else:
        cfg = SimConfig(
            seed=seed,
            days=days,
            ticks_per_day=ticks_per_day,
            max_agents=max_agents,
            backend="numpy",
            device="cpu",
            log_every_ticks=10**9,
            snapshot_every_days=0,
            arm_label="TRACK-E-U25-CALIB",
            use_cuda_graph=False,
        )
        for k, v in overrides.get("biology", {}).items():
            setattr(cfg.biology, k, v)
        for k, v in overrides.get("drives", {}).items():
            setattr(cfg.drives, k, v)
        cfg.playground.enabled = playground

    td = tempfile.mkdtemp(prefix="u25cal_")
    out = Path(td)
    try:
        sim = Universe25Sim(cfg, out)
        days_hist: list[float] = []
        n_hist: list[int] = []
        births_hist: list[int] = []
        last_young_hist: list[float] = []

        total = int(days * ticks_per_day)
        for _ in range(total):
            sim.step()
            if sim.tick % ticks_per_day == 0:
                days_hist.append(sim.day)
                n_hist.append(sim.agents.n_alive)
                births_hist.append(sim._births)
                last_young_hist.append(sim._last_young_day)
            if sim.agents.n_alive == 0 and sim.day > 50:
                break
        try:
            sim.logger.close()
        except Exception:
            pass
        obs = _extract_landmarks(sim, days_hist, n_hist, births_hist, last_young_hist)
        errors: dict[str, float | None] = {}
        for k, tgt in LANDMARKS.items():
            o = obs.get(k, float("nan"))
            errors[k] = None if o != o else abs(o - tgt) / tgt
        loss = landmark_loss(obs, require_collapse=True)
        return {"observed": obs, "loss": loss, "errors": errors, "seed": seed, "params": params}
    finally:
        shutil.rmtree(td, ignore_errors=True)
