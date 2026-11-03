"""Landmark loss weights: inverse seed variance with a noise floor, normalised scale."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from universe25.calib.priors import (  # noqa: E402
    EXTRA_LOSS_WEIGHTS,
    LANDMARK_REL_SEED_SD,
    LOSS_WEIGHTS,
    NOISE_FLOOR,
    TOTAL_LOSS_WEIGHT,
    inverse_variance_weights,
    landmark_loss,
)
from universe25.metrics.calibration import EXTRA_LANDMARKS, LANDMARKS  # noqa: E402


def test_weights_are_inverse_variance_and_normalised() -> None:
    w = {**LOSS_WEIGHTS, **EXTRA_LOSS_WEIGHTS}
    assert abs(sum(w.values()) - TOTAL_LOSS_WEIGHT) < 1e-9
    assert set(w) == set(LANDMARK_REL_SEED_SD) == set(LANDMARKS) | set(EXTRA_LANDMARKS)
    # w_k x sigma_k^2 is the same constant for every landmark
    ref = w["peak_n"] * (LANDMARK_REL_SEED_SD["peak_n"] ** 2 + NOISE_FLOOR**2)
    for k, sd in LANDMARK_REL_SEED_SD.items():
        assert abs(w[k] * (sd * sd + NOISE_FLOOR**2) - ref) < 1e-9, k
    # the seed-dominated early phase weighs little against the plateau landmarks
    assert w["n_at_day_315"] < 0.1 * w["peak_n"]
    assert w["adults_at_day_315"] < w["n_at_day_315"]
    # with no spread differences the weights are equal
    eq = inverse_variance_weights({"a": 0.1, "b": 0.1}, floor=0.0, total=2.0)
    assert abs(eq["a"] - 1.0) < 1e-12 and abs(eq["b"] - 1.0) < 1e-12


def test_decline_band_applies_at_day_1200_not_at_the_horizon() -> None:
    base = {**LANDMARKS, **EXTRA_LANDMARKS}
    at_1200 = dict(base, final_n=1500.0, final_day=1200.0)
    assert landmark_loss(at_1200) == 0.0
    collapsed_at_1200 = dict(base, final_n=100.0, final_day=1200.0)
    assert landmark_loss(collapsed_at_1200) > 0.5, "too far down at the 1200-d horizon"
    # a 1600-d run near extinction (Calhoun: 27 at 1588) with N(1200) inside the band: no penalty
    long_run = dict(base, final_n=5.0, final_day=1600.0, n_at_day_1200=1300.0)
    assert landmark_loss(long_run) == 0.0
    long_run_bad = dict(base, final_n=5.0, final_day=1600.0, n_at_day_1200=200.0)
    assert landmark_loss(long_run_bad) > 0.5


def test_peak_miss_costs_more_than_early_phase_noise() -> None:
    perfect = {**LANDMARKS, **EXTRA_LANDMARKS, "final_n": 1500.0, "final_day": 1200.0}
    assert landmark_loss(perfect) == 0.0
    peak_off = dict(perfect)
    peak_off["peak_n"] = 2200.0 * 1.13  # the 2i multi-seed study's best-loss trial
    n315_off = dict(perfect)
    n315_off["n_at_day_315"] = 620.0 * 0.67  # one seed sd below the target
    assert landmark_loss(peak_off) > 3.0 * landmark_loss(n315_off)
    # a 1-sigma miss costs the same on every landmark
    costs = []
    for k, sd in LANDMARK_REL_SEED_SD.items():
        o = dict(perfect)
        target = {**LANDMARKS, **EXTRA_LANDMARKS}[k]
        o[k] = target * (1.0 + (sd * sd + NOISE_FLOOR**2) ** 0.5)
        costs.append(landmark_loss(o))
    assert max(costs) - min(costs) < 1e-9, costs


if __name__ == "__main__":
    test_weights_are_inverse_variance_and_normalised()
    test_decline_band_applies_at_day_1200_not_at_the_horizon()
    test_peak_miss_costs_more_than_early_phase_noise()
    print("test_calib_loss: OK")
