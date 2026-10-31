"""Landmark extraction: peak day is the smoothed maximum, not the start of the plateau."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from universe25.metrics.calibration import (  # noqa: E402
    PEAK_WINDOW_DAYS,
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


if __name__ == "__main__":
    test_peak_day_is_smoothed_maximum_and_97pct_day_is_reported()
    test_rate_cessation_ignores_single_stragglers()
    print("test_landmarks: OK")
