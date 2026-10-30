"""Pydantic configuration for Universe 25 (+ playground)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class GeometryConfig(BaseModel):
    """Calhoun 1973 pen: 101 x 101 inches, 16 cells, 256 nests."""

    width_in: float = 101.0
    height_in: float = 101.0
    n_cells_x: int = 4
    n_cells_y: int = 4
    nests_per_cell: int = 16
    food_per_cell: int = 1
    water_per_cell: int = 1
    capacity_design: int = 3840


class PlaygroundConfig(BaseModel):
    """Optional playground zone. Geometry only — no play reward."""

    enabled: bool = True
    x0: float = 35.0
    y0: float = 35.0
    x1: float = 66.0
    y1: float = 66.0
    n_balls: int = 8
    n_tunnels: int = 4
    n_ramps: int = 2


class ResourceConfig(BaseModel):
    mode: Literal["abundant", "scarce"] = "abundant"
    food_refill_per_tick: float = 1e9
    water_refill_per_tick: float = 1e9
    scarce_food_per_day: float = 50.0


class BiologyConfig(BaseModel):
    """Life-history + density/social mechanisms (no scheduled collapse day)."""

    gestation_days: float = 20.0
    litter_mean: float = 7.0
    litter_sd: float = 1.5
    weaning_days: float = 21.0
    maturity_days: float = 50.0
    max_age_days: float = 800.0
    base_mortality_per_day: float = 0.0005
    stress_mortality_scale: float = 0.01
    first_conception_min_day: float = 95.0
    menopause_density_threshold: float = 0.55
    maternal_neglect_stress: float = 0.7
    # Tunables for principled calibration (priors in calib/priors.py)
    breeding_p_base: float = 0.55
    breeding_stress_coef: float = 0.7
    nest_overcrowd_stress: float = 0.2
    withdrawn_stress_threshold: float = 0.85
    withdrawn_social_threshold: float = 0.2
    pup_hunger_scale: float = 0.35
    young_mortality_scale: float = 0.25
    mate_radius_in: float = 20.0
    stillbirth_neglect_p: float = 0.5
    density_mortality_scale: float = 0.0  # extra death rate ~ dens^2
    social_breakdown_stress_boost: float = 0.0  # added stress gain when dens high
    beautiful_one_aggression_max: float = 0.15


class DriveConfig(BaseModel):
    """Homeostatic / social drives. Absolutely no play term."""

    hunger_gain_per_day: float = 1.2
    thirst_gain_per_day: float = 1.5
    fatigue_gain_active: float = 0.4
    fatigue_recovery_rest: float = 0.8
    stress_density_gain: float = 0.35
    stress_decay: float = 0.15
    social_drive_gain: float = 0.2
    curiosity_gain: float = 0.12
    curiosity_decay_on_novel: float = 0.35
    boredom_gain: float = 0.08
    boredom_decay_on_vary: float = 0.25
    aggression_baseline: float = 0.1
    aggression_scarce_boost: float = 0.5


class SimConfig(BaseModel):
    seed: int = 7000
    ticks_per_day: int = 24
    max_agents: int = 4096
    initial_pairs: int = 4
    days: float = 1600.0
    device: Literal["cuda", "cpu", "auto"] = "auto"
    backend: Literal["warp", "torch", "numpy", "auto"] = "auto"
    log_every_ticks: int = 24
    snapshot_every_days: int = 50
    arm_label: str = "TRACK-E-U25-ABUND-PG"
    use_cuda_graph: bool = False
    geometry: GeometryConfig = Field(default_factory=GeometryConfig)
    playground: PlaygroundConfig = Field(default_factory=PlaygroundConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    biology: BiologyConfig = Field(default_factory=BiologyConfig)
    drives: DriveConfig = Field(default_factory=DriveConfig)

    @field_validator("seed")
    @classmethod
    def _seed_range(cls, v: int) -> int:
        if v < 7000 or v >= 10000:
            raise ValueError(f"seed {v} outside allowed seed band [7000,10000)")
        if 5000 <= v < 6000:
            raise ValueError("seed in reserved band")
        return v


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> SimConfig:
    data: dict[str, Any] = {}
    if path is not None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    if overrides:
        data = _deep_merge(data, overrides)
    return SimConfig.model_validate(data)


def _deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
