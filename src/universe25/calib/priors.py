"""Documented priors for Calhoun 1973 calibration (principled, not hand hacks).

Sources / rationale:
- Mouse gestation ~19–21 d; litter size ~5–8; maturity ~6–8 weeks (lab mouse biology).
- Calhoun first litters ~day 104 ⇒ first_conception ≈ 104 − gestation.
- Design capacity 3840; peak ~2200 ⇒ menopause threshold prior around 0.35–0.8 of capacity.
- Calhoun: female menopause ≈ 560 d of age; survivors at Day 1588 were > 987 d old and
  N was still 2056 at Day 736 ⇒ adults live out ~800–1100 d; adult mortality is NOT the
  collapse driver. Collapse = young raised under crowding never breed (Marsden 1972: the
  deficit persisted after transfer to uncrowded universes) ⇒ developmental imprinting.
- No parameter is a "collapse_day". Collapse must emerge from density → stress →
  neglect / breeding suppression / imprinting.

Search uses Optuna + CMA-ES sampler over these bounds (uniform in transformed space).
"""
from __future__ import annotations

from typing import Any

from universe25.metrics.calibration import EXTRA_LANDMARKS, LANDMARKS  # noqa: F401 (re-export)

# name -> (low, high, log_scale?, path in biology/drives)
PARAM_PRIORS: dict[str, dict[str, Any]] = {
    "first_conception_min_day": {
        "low": 70.0, "high": 100.0, "log": False, "group": "biology",
        "prior": "Uniform; Calhoun first litters 104 minus gestation ~20",
    },
    "gestation_days": {
        "low": 19.0, "high": 21.0, "log": False, "group": "biology",
        "prior": "Uniform around laboratory mouse gestation",
    },
    "litter_mean": {
        "low": 4.5, "high": 9.0, "log": False, "group": "biology",
        "prior": "Uniform around typical litter size 5–8",
    },
    "maturity_days": {
        "low": 42.0, "high": 70.0, "log": False, "group": "biology",
        "prior": "Uniform; 6–10 weeks to sexual maturity",
    },
    "breeding_p_base": {
        "low": 0.10, "high": 0.90, "log": False, "group": "biology",
        "prior": "Uniform; daily conception probability, cohabiting eligible pair, low density "
                 "(the only conception channel since phase 2d)",
    },
    "litter_abandon_p": {
        "low": 0.0, "high": 0.6, "log": False, "group": "biology",
        "prior": "Uniform; daily P(stressed nursing mother abandons her box's litter)",
    },
    "breeding_stress_coef": {
        "low": 0.2, "high": 1.0, "log": False, "group": "biology",
        "prior": "Uniform; conception suppression per unit stress",
    },
    "menopause_density_threshold": {
        "low": 0.35, "high": 0.80, "log": False, "group": "biology",
        "prior": "Uniform; dens/capacity where conception is fully suppressed (2200/3840≈0.57)",
    },
    "breakdown_density_threshold": {
        "low": 0.35, "high": 0.80, "log": False, "group": "biology",
        "prior": "Uniform; dens/capacity above which the social-breakdown stress boost applies "
                 "(behavioural sink), decoupled from the conception ramp",
    },
    "stress_mortality_scale": {
        "low": 2e-4, "high": 0.02, "log": True, "group": "biology",
        "prior": "LogUniform; stress² mortality — weak: Calhoun adults lived out their lifespans",
    },
    "base_mortality_per_day": {
        "low": 5e-5, "high": 1.5e-3, "log": True, "group": "biology",
        "prior": "LogUniform; background adult mortality",
    },
    "max_age_days": {
        "low": 750.0, "high": 1100.0, "log": False, "group": "biology",
        "prior": "Uniform; survivors > 987 d at Day 1588; T_max 1000–1143 d (Gwizdałła & Duś)",
    },
    "young_mortality_scale": {
        "low": 0.1, "high": 1.0, "log": False, "group": "biology",
        "prior": "Uniform; pup/juvenile baseline mortality relative to adult",
    },
    "maternal_neglect_stress": {
        "low": 0.30, "high": 0.90, "log": False, "group": "biology",
        "prior": "Uniform; stress above which mothers stop nursing / abandon litters",
    },
    "stillbirth_neglect_p": {
        "low": 0.2, "high": 0.9, "log": False, "group": "biology",
        "prior": "Uniform; P(lose litter | neglect)",
    },
    "nest_overcrowd_stress": {
        "low": 0.0, "high": 0.6, "log": False, "group": "biology",
        "prior": "Uniform; extra stress gain in an overfull nest box",
    },
    "social_breakdown_stress_boost": {
        "low": 0.0, "high": 0.8, "log": False, "group": "biology",
        "prior": "Uniform; extra stress gain when dens > menopause threshold",
    },
    "imprint_rate": {
        "low": 0.01, "high": 0.5, "log": True, "group": "biology",
        "prior": "LogUniform; competence loss per day per unit exposure while young",
    },
    "imprint_density_threshold": {
        "low": 0.05, "high": 0.40, "log": False, "group": "biology",
        "prior": "Uniform; local density fraction where developmental exposure begins",
    },
    "withdrawn_competence_threshold": {
        "low": 0.1, "high": 0.7, "log": False, "group": "biology",
        "prior": "Uniform; adults below this competence withdraw ('beautiful ones')",
    },
    "female_fertile_max_age_days": {
        "low": 450.0, "high": 620.0, "log": False, "group": "biology",
        "prior": "Uniform; Calhoun: female menopause ≈ 560 d of age",
    },
    "nurse_rate_per_day": {
        "low": 2.0, "high": 12.0, "log": False, "group": "biology",
        "prior": "Uniform; relaxation rate of a pup's deficit per day in contact with a "
                 "lactating mother (x her maternal investment); sets pup starvation risk",
    },
    "maternal_erosion_rate": {
        "low": 0.002, "high": 1.0, "log": True, "group": "biology",
        "prior": "LogUniform; irreversible adult maternal-capacity loss per day per unit "
                 "stress above threshold (Calhoun C/D: mothers expelled their young); the "
                 "upper range lets a brief excursion above the threshold do lasting damage",
    },
    "maternal_erosion_stress": {
        "low": 0.3, "high": 0.9, "log": False, "group": "biology",
        "prior": "Uniform; stress above which adult maternal capacity erodes",
    },
    "courtship_erosion_rate": {
        "low": 0.002, "high": 1.0, "log": True, "group": "biology",
        "prior": "LogUniform; irreversible male courtship-capacity loss per day per unit stress "
                 "above threshold (Calhoun D: males ceased courting; last conception ~920)",
    },
    "courtship_erosion_stress": {
        "low": 0.3, "high": 0.9, "log": False, "group": "biology",
        "prior": "Uniform; stress above which male courtship capacity erodes",
    },
    "stress_density_gain": {
        "low": 0.1, "high": 1.5, "log": False, "group": "drives",
        "prior": "Uniform; how fast local density raises stress",
    },
    "stress_decay": {
        "low": 0.1, "high": 1.5, "log": False, "group": "drives",
        "prior": "Uniform; stress relaxation rate (equilibrium = gain·local/decay)",
    },
}

LOSS_WEIGHTS = {
    "first_litters_day": 1.5,
    "n_at_day_315": 2.0,
    "peak_n": 2.0,
    "peak_day": 1.5,
    "last_young_day": 1.5,
}
EXTRA_LOSS_WEIGHTS = {
    "n_at_day_736": 1.5,
    "adults_at_day_315": 1.0,
    "last_conception_day": 1.0,
}
# Inferred (not a Calhoun number): between N=2056 at Day 736 and N=122 at Day 1444 the
# population at Day 1200 should sit well below the peak but not be extinct.
DECLINE_BAND_AT_HORIZON = (0.35, 0.85)


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


def overrides_to_params(overrides: dict[str, Any]) -> dict[str, float]:
    """Inverse of params_to_overrides for the keys in PARAM_PRIORS (others ignored)."""
    out: dict[str, float] = {}
    for group in ("biology", "drives"):
        for k, v in (overrides.get(group) or {}).items():
            if k in PARAM_PRIORS:
                out[k] = float(v)
    return out


def landmark_loss(observed: dict[str, float], require_collapse: bool = True) -> float:
    """Weighted relative L2 on landmarks + emergent-collapse shape penalties.

    Canonical landmarks weigh most; extra Calhoun facts (N@736, adults@315, last conception)
    add shape information. Collapse terms: no surviving births long after Day 600 and a
    population at the horizon inside DECLINE_BAND_AT_HORIZON of the peak (only when the
    horizon is >= 1000 days).
    """
    acc = 0.0
    for k, w in LOSS_WEIGHTS.items():
        target = LANDMARKS[k]
        obs = observed.get(k, float("nan"))
        if obs != obs:
            acc += w * 4.0
            continue
        rel = abs(obs - target) / target
        acc += w * min(rel, 2.0) ** 2
    for k, w in EXTRA_LOSS_WEIGHTS.items():
        target = EXTRA_LANDMARKS[k]
        obs = observed.get(k, float("nan"))
        if obs != obs:
            continue  # horizon too short / column absent: no penalty
        rel = abs(obs - target) / target
        acc += w * min(rel, 2.0) ** 2
    if require_collapse:
        peak = observed.get("peak_n", 0.0) or 0.0
        final = observed.get("final_n", peak) or 0.0
        horizon = observed.get("final_day", 0.0) or 0.0
        if peak > 0 and horizon >= 1000.0:
            frac = final / peak
            lo, hi = DECLINE_BAND_AT_HORIZON
            if frac > hi:
                acc += 1.5 * ((frac - hi) / (1.0 - hi)) ** 2
            elif frac < lo:
                acc += 1.5 * ((lo - frac) / lo) ** 2
    return float(acc)
