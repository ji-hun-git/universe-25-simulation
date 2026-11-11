"""Replica v2 M5: the GP emulator recovers a known function (the relevant inputs get short
lengthscales, the others long ones, the nugget the noise level) with calibrated uncertainty, and
the history-matching transforms map record values and model outputs to the same scale."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from universe25.calib.emulator import GP, implausibility  # noqa: E402


def test_gp_recovers_a_known_function() -> None:
    rng = np.random.default_rng(7100)
    d, n = 6, 120
    X = rng.random((n, d))

    def f(X: np.ndarray) -> np.ndarray:
        return 2.0 * np.sin(3.0 * X[:, 0]) + X[:, 1] ** 2

    y = f(X) + rng.normal(0.0, 0.05, n)
    gp = GP(X, y, restarts=3, seed=11)
    assert gp.ls[:2].max() < 3.0 and gp.ls[2:].min() > 5.0, gp.ls
    assert 0.02 < np.sqrt(gp.n2) * gp.sd < 0.12
    Xs = rng.random((2000, d))
    m, ve, vn = gp.predict(Xs)
    err = m - f(Xs)
    assert np.sqrt(np.mean(err ** 2)) < 0.1
    assert np.mean(np.abs(err) > 3.0 * np.sqrt(ve + vn)) < 0.01
    lm, lv = gp.loo()
    assert np.mean(np.abs(y - lm) / np.sqrt(lv) > 3.0) < 0.02
    assert np.allclose(implausibility(1.0, 0.0, np.array([1.0, 3.0]), np.array([1.0, 1.0]),
                                      3.0), [0.0, 1.0])


def test_history_match_scales() -> None:
    import history_match as hm

    for name in hm.OUTPUTS:
        z, var = hm.target(name)
        assert np.isclose(hm.transform(name, np.array([hm.OUTPUTS[name][0]]))[0], z)
        assert var > 0.0
    u = np.full(len(hm.PARAMS), 0.5)
    over = hm.to_params(u)
    for g, k, lo, hi, lg in hm.PARAMS:
        v = over[g][k]
        assert lo <= v <= hi
        assert np.isclose(v, np.sqrt(lo * hi) if lg else 0.5 * (lo + hi))


if __name__ == "__main__":
    test_gp_recovers_a_known_function()
    test_history_match_scales()
    print("test_emulator: OK")
