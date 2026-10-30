"""Documented priors for Calhoun 1973 calibration (principled, not hand hacks).

Sources / rationale:
- Mouse gestation ~19–21 d; litter size ~6–8 (lab mouse biology).
- Calhoun first litters ~day 104 ⇒ first_conception ≈ 104 − gestation.
- Design capacity 3840; peak ~2200 ⇒ menopause threshold prior around 0.4–0.7 of capacity.
- Collapse is emergent: density↑ → stress↑ → breeding↓ / neglect↑ / mortality↑ / withdrawal↑.
  No parameter is a "collapse_day".

Search uses Optuna + CMA-ES sampler over these bounds (uniform in transformed space).
"""
from __future__ import annotations

from typing import Any

import numpy as np

LANDMARKS = {
    "first_litters_day": 104.0,
    "n_at_day_315": 620.0,
    "peak_n": 2200.0,
    "peak_day": 560.0,
    "last_young_day": 600.0,
}

# name -> (low, high, log_scale?, path in biology/drives)
PARAM_PRIORS: dict[str, dict[str, Any]] = {
    "first_conception_min_day": {
        "low": 70.0,
        "high": 100.0,
        "log": False,
        "group": "biology",
        "prior": "Uniform; Calhoun first litters 104 minus gestation ~20",
    },
    "gestation_days": {
        "low": 18.0,
        "high": 22.0,
        "log": False,
        "group": "biology",
        "prior": "Uniform around laboratory mouse gestation",
    },
    "litter_mean": {
        "low": 5.0,
        "high": 9.0,
        "log": False,
        "group": "biology",
        "prior": "Uniform around typical litter size 6–8",
    },
    "maturity_days": {
        "low": 35.0,
        "high": 55.0,
        "log": False,
        "group": "biology",
        "prior": "Uniform; earlier maturity → faster early growth",
    },
    "breeding_p_base": {
        "low": 0.25,
        "high": 0.95,
        "log": False,
        "group": "biology",
        "prior": "Uniform; daily conception attempt rate at low density",
    },
    "menopause_density_threshold": {
        "low": 0.25,
        "high": 0.70,
        "log": False,
        "group": "biology",
        "prior": "Uniform; dens/capacity where breeding collapses (peak~2200/3840≈0.57)",
    },
    "stress_mortality_scale": {
        "low": 0.002,
        "high": 0.08,
        "log": True,
        "group": "biology",
        "prior": "LogUniform; stress² mortality drives late die-off",
    },
    "density_mortality_scale": {
        "low": 1e-5,
        "high": 0.02,
        "log": True,
        "group": "biology",
        "prior": "LogUniform; extra mortality ∝ dens² (crowding)",
    },
    "base_mortality_per_day": {
        "low": 1e-4,
        "high": 0.002,
        "log": True,
        "group": "biology",
        "prior": "LogUniform; background adult mortality",
    },
    "maternal_neglect_stress": {
        "low": 0.45,
        "high": 0.90,
        "log": False,
        "group": "biology",
        "prior": "Uniform; stress above which mothers neglect / stillbirth",
    },
    "stillbirth_neglect_p": {
        "low": 0.2,
        "high": 0.9,
        "log": False,
        "group": "biology",
        "prior": "Uniform; P(lose litter | neglect)",
    },
    "stress_density_gain": {
        "low": 0.15,
        "high": 1.2,
        "log": False,
        "group": "drives",
        "prior": "Uniform; how fast local density raises stress",
    },
    "stress_decay": {
        "low": 0.05,
        "high": 0.40,
        "log": False,
        "group": "drives",
        "prior": "Uniform; stress recovery rate",
    },
    "social_breakdown_stress_boost": {
        "low": 0.0,
        "high": 0.8,
        "log": False,
        "group": "biology",
        "prior": "Uniform; extra stress gain when dens > menopause threshold",
    },
    "young_mortality_scale": {
        "low": 0.1,
        "high": 0.6,
        "log": False,
        "group": "biology",
        "prior": "Uniform; pup/juv mortality relative to adult baseline",
    },
}


def suggest_params(trial: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, spec in PARAM_PRIORS.items():
        if spec["log"]:
            out[name] = trial.suggest_float(name, spec["low"], spec["high"], log=True)
        else:
            out[name] = trial.suggest_float(name, spec["low"], spec["high"])
    return out


def params_to_overrides(params: dict[str, float]) -> dict[str, Any]:
    bio: dict[str, float] = {}
    drv: dict[str, float] = {}
    for name, val in params.items():
        group = PARAM_PRIORS[name]["group"]
        if group == "biology":
            bio[name] = float(val)
        else:
            drv[name] = float(val)
    return {"biology": bio, "drives": drv}


def landmark_loss(observed: dict[str, float], require_collapse: bool = True) -> float:
    """Weighted relative L2 on landmarks + collapse penalty.

    Collapse: after peak, N should fall below 0.5 * peak by day 1200, and
    last_young should be near 600 (not still birthing at 1600).
    """
    w = {
        "first_litters_day": 1.5,
        "n_at_day_315": 2.0,
        "peak_n": 2.0,
        "peak_day": 1.5,
        "last_young_day": 1.5,
    }
    acc = 0.0
    for k, target in LANDMARKS.items():
        obs = observed.get(k, float("nan"))
        if obs != obs:
            acc += w[k] * 4.0
            continue
        rel = abs(obs - target) / target
        acc += w[k] * (rel ** 2)
    # collapse emergent check
    if require_collapse:
        peak = observed.get("peak_n", 0.0) or 0.0
        final = observed.get("final_n", peak) or peak
        peak_day = observed.get("peak_day", 0.0) or 0.0
        last_y = observed.get("last_young_day", 1600.0) or 1600.0
        if peak > 0 and final > 0.7 * peak:
            acc += 2.0 * ((final / peak) - 0.5) ** 2
        if last_y > 900:
            acc += 1.5 * ((last_y - 600) / 600) ** 2
        if peak_day > 900:
            acc += 0.5 * ((peak_day - 560) / 560) ** 2
    return float(acc)
