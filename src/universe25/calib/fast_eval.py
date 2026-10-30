"""Fast landmark evaluation for calibration (minimal I/O)."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from universe25.calib.priors import EXTRA_LANDMARKS, LANDMARKS, landmark_loss, params_to_overrides
from universe25.config import SimConfig, load_config
from universe25.metrics.calibration import landmarks_from_series
from universe25.sim import Universe25Sim


def evaluate_params(
    params: dict[str, float],
    *,
    seed: int = 7000,
    days: float = 1200.0,
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
        bio = cfg.biology
        days_hist: list[float] = []
        n_hist: list[int] = []
        births_hist: list[int] = []
        last_young_hist: list[float] = []
        n_adult_hist: list[int] = []
        last_conc_hist: list[float] = []

        total = int(days * ticks_per_day)
        for _ in range(total):
            sim.step()
            if sim.tick % ticks_per_day == 0:
                a = sim.agents
                days_hist.append(sim.day)
                n_hist.append(a.n_alive)
                births_hist.append(sim._births)
                last_young_hist.append(sim._last_surviving_young_day)
                n_adult_hist.append(int(np.sum(a.alive & (a.age_days >= bio.maturity_days))))
                last_conc_hist.append(sim._last_conception_day)
            if sim.agents.n_alive == 0 and sim.day > 50:
                break
        try:
            sim.logger.close()
        except Exception:
            pass
        obs = landmarks_from_series(
            np.asarray(days_hist, dtype=np.float64),
            np.asarray(n_hist, dtype=np.float64),
            np.asarray(births_hist, dtype=np.float64),
            np.asarray(last_young_hist, dtype=np.float64),
            n_adult=np.asarray(n_adult_hist, dtype=np.float64),
            last_conception=np.asarray(last_conc_hist, dtype=np.float64),
            surv_births_by_day=sim._surv_births_by_day,
        )
        obs["last_birth_any_day"] = float(sim._last_young_day)
        obs["nan_count"] = int(sim._nan_count)
        errors: dict[str, float | None] = {}
        for k, tgt in {**LANDMARKS, **EXTRA_LANDMARKS}.items():
            o = obs.get(k, float("nan"))
            errors[k] = None if o != o else abs(o - tgt) / tgt
        loss = landmark_loss(obs, require_collapse=True)
        return {"observed": obs, "loss": loss, "errors": errors, "seed": seed, "params": params}
    finally:
        shutil.rmtree(td, ignore_errors=True)
