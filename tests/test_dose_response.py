"""Stratified dose-response test for H-e (metrics/dose_response.py): tau-b matches scipy's,
monotone strata give T = 1 and the smallest p, constant strata contribute 0, the permutation
null is deterministic for a fixed seed, and paired differences are summarised correctly."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.metrics.dose_response import (  # noqa: E402
    kendall_tau_b,
    paired_mean_se,
    stratified_tau_test,
)


def test_tau_b_matches_scipy_with_ties() -> None:
    from scipy.stats import kendalltau

    r = np.random.default_rng(3)
    for _ in range(5):
        x = r.random(24)
        y = r.integers(0, 4, 24)  # a 0-5-like count with ties
        assert abs(kendall_tau_b(x, y) - kendalltau(x, y, variant="b").statistic) < 1e-12
    assert kendall_tau_b(np.arange(5), np.ones(5)) == 0.0


def test_stratified_test_monotone_constant_and_null() -> None:
    dose = np.tile(np.linspace(0.0, 1.0, 24), 3)
    strata = np.repeat([400.0, 700.0, 1000.0], 24)
    mono = stratified_tau_test(dose, 3.0 * dose + 1.0, strata, n_perm=2000, seed=0)
    assert abs(mono["T"] - 1.0) < 1e-12 and mono["p_one_sided"] == 1.0 / 2001
    flat = stratified_tau_test(dose, np.zeros(72), strata, n_perm=500, seed=0)
    assert flat["T"] == 0.0 and flat["p_one_sided"] == 1.0
    r = np.random.default_rng(9)
    resp = r.integers(0, 6, 72)
    a = stratified_tau_test(dose, resp, strata, n_perm=3000, seed=0)
    b = stratified_tau_test(dose, resp, strata, n_perm=3000, seed=0)
    assert a == b, "permutation null not deterministic for a fixed seed"
    assert abs(a["null_mean"]) < 0.02 and 0.0 < a["p_one_sided"] <= 1.0
    # one stratum anti-monotone, two monotone: T = 1/3
    resp2 = 3.0 * dose + 1.0
    resp2[:24] = resp2[:24][::-1]
    assert abs(stratified_tau_test(dose, resp2, strata, n_perm=100)["T"] - 1.0 / 3.0) < 1e-12


def test_paired_mean_se() -> None:
    d = paired_mean_se([1.0, 2.0, 3.0, np.nan], [0.0, 0.0, 0.0, 1.0])
    assert d["n"] == 3 and abs(d["mean"] - 2.0) < 1e-12
    assert abs(d["se"] - 1.0 / np.sqrt(3)) < 1e-12


if __name__ == "__main__":
    test_tau_b_matches_scipy_with_ties()
    test_stratified_test_monotone_constant_and_null()
    test_paired_mean_se()
    print("test_dose_response: OK")
