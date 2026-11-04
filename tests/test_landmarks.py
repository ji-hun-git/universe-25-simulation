"""Landmark extraction: peak day is the smoothed maximum, not the start of the plateau."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from universe25.metrics.calibration import (  # noqa: E402
    EXTRA_LANDMARKS,
    LANDMARKS,
    PEAK_WINDOW_DAYS,
    RECORD_LANDMARKS,
    landmarks_from_series,
    rate_cessation_day,
)


def test_peak_day_is_smoothed_maximum_and_97pct_day_is_reported() -> None:
    days = np.arange(0.0, 900.0)
    # logistic rise to a plateau of 2000 reached by ~day 520 that drifts up by 7.5 to day 650,
    # a one-day spike of +40 at day 500 (2 %), daily jitter, a decline after day 650
    n = 2000.0 / (1.0 + np.exp(-(days - 380.0) / 20.0))
    n = n + 0.05 * np.clip(days - 500.0, 0.0, 150.0)
    n[days > 650] -= 2.0 * (days[days > 650] - 650.0)
    n = n + 10.0 * np.sin(days / 3.0)
    n[500] += 40.0
    births = np.cumsum(np.ones_like(days))
    out = landmarks_from_series(days, n, births, np.zeros_like(days))
    assert out["peak_n"] == float(n.max())
    assert out["peak_day_raw_max"] == 500.0, "the spike is the raw maximum"
    assert out["peak_day_97pct"] < 530.0, "97 % day marks the start of the plateau"
    # the smoothed maximum sits late in the plateau, not at the spike nor at the plateau start
    assert 600.0 <= out["peak_day"] <= 660.0, out["peak_day"]
    assert out["peak_day"] > out["peak_day_97pct"] + PEAK_WINDOW_DAYS / 2
    # the smoothed day does not move when the single-day spike is removed
    n2 = n.copy()
    n2[500] -= 40.0
    out2 = landmarks_from_series(days, n2, births, np.zeros_like(days))
    assert abs(out2["peak_day"] - out["peak_day"]) <= 2.0


def test_rate_cessation_ignores_single_stragglers() -> None:
    hist = np.zeros(1000)
    hist[100:600] = 30  # 30 events a day
    hist[650] = 1  # a straggler
    hist[800] = 1
    assert rate_cessation_day(hist) == 599.0


def test_record_landmarks_are_reported_not_scored() -> None:
    """Record landmarks (2026-11-04 review) stay out of the scored sets; doubling times follow
    the definition (t1 - t0) ln 2 / ln(N1 / N0) and are NaN below the horizon."""
    assert not set(RECORD_LANDMARKS) & (set(LANDMARKS) | set(EXTRA_LANDMARKS))
    days = np.arange(0.0, 700.0)
    # 8 founders, first litters at day 60, then a 55-day doubling from 20 up to a 2200 plateau
    n = np.where(days < 60.0, 8.0, 20.0 * 2.0 ** ((days - 60.0) / 55.0))
    n = np.minimum(n, 2200.0)
    births = np.cumsum(days >= 60.0).astype(np.float64)
    out = landmarks_from_series(days, n, births, np.zeros_like(days))
    assert out["first_litters_day"] == 60.0
    assert abs(out["doubling_time_phase_b_days"] - 55.0) < 0.5, out["doubling_time_phase_b_days"]
    assert 0.0 < out["doubling_time_phase_c_days"] < 200.0  # 315 -> plateau peak day
    assert np.isnan(out["n_at_day_811"]) and np.isnan(out["n_at_day_1471"])  # horizon 700
    assert np.isnan(out["n_at_day_960"])
    # with the horizon extended, the record censuses are read off the series
    days2 = np.arange(0.0, 1500.0)
    n2 = np.full_like(days2, 1000.0)
    out2 = landmarks_from_series(days2, n2, np.cumsum(days2 >= 60.0), np.zeros_like(days2))
    assert out2["n_at_day_811"] == 1000.0 and out2["n_at_day_1471"] == 1000.0
    assert np.isnan(out2["doubling_time_phase_b_days"])  # no growth -> undefined


if __name__ == "__main__":
    test_peak_day_is_smoothed_maximum_and_97pct_day_is_reported()
    test_rate_cessation_ignores_single_stragglers()
    test_record_landmarks_are_reported_not_scored()
    print("test_landmarks: OK")
