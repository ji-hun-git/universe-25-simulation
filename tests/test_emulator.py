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
    # M5c: the two transmission parameters append to the M5 set; a point of the wrong
    # dimension is refused instead of silently truncated
    ps = hm.param_set(True)
    assert ps[:len(hm.PARAMS_M5)] == hm.PARAMS_M5 and len(ps) == len(hm.PARAMS_M5) + 2
    over = hm.to_params(np.full(len(ps), 0.5), ps)
    assert np.isclose(over["biology"]["maternal_transmission"], 0.5)
    assert np.isclose(over["biology"]["care_ref"], np.sqrt(0.5 * 2.5))
    try:
        hm.to_params(np.full(len(ps), 0.5))
    except ValueError:
        pass
    else:
        raise AssertionError("a 22-dimensional point for the 20 M5 parameters must be refused")


def test_history_match_rep_scoring() -> None:
    """M5d: the arc test, the pooled arc variance, member scoring from its own seeds, and the
    replicate emulators on a synthetic design."""
    import history_match as hm
    import history_match_rep as rp

    def out(peak, n1588, young, conc, **kw):
        o = {name: hm.OUTPUTS[name][0] for name in hm.OUTPUTS}  # every target at the record
        o.update(peak_n=peak, n_at_day_1588=n1588, last_young_day=young,
                 last_conception_day=conc, **kw)
        return o

    assert rp.is_arc(out(2200, 27, 600, 920))
    assert not rp.is_arc(out(1700, 27, 600, 920))  # no growth
    assert not rp.is_arc(out(2200, 400, 600, 920))  # no collapse
    assert not rp.is_arc(out(2200, 27, 600, 700))  # gap of 100 d
    arc_runs = [{"seed": 7000 + i, "outputs": out(2200, 27, 600 + 10 * i, 920)} for i in range(3)]
    flat = [{"seed": 7003 + i, "outputs": out(2200, 1500, 1578, 1599)} for i in range(9)]
    va = rp.v_arc([arc_runs + flat])
    assert np.isclose(va["last_young_day"], np.var([600, 610, 620], ddof=1))
    sc = rp.score(arc_runs + flat, va)
    assert sc["arc_seeds"] == [7000, 7001, 7002] and np.isclose(sc["arc_freq"], 0.25)
    assert sc["arc_wave_seeds"] == 3 and sc["arc_new_seeds"] == 0
    assert sc["implausibility"]["n_at_day_1588"] < 1e-9  # given the arc: exactly the record
    assert np.isfinite(sc["i2"])
    sc0 = rp.score(flat, va)  # no arc: the conditional targets cannot be scored
    assert sc0["arc_freq"] == 0.0 and np.isinf(sc0["implausibility"]["last_young_day"])
    # replicate emulators on a synthetic design (22 parameters, 6 seeds per point)
    hm.PARAMS = hm.param_set(True)
    rng = np.random.default_rng(3)
    pts = []
    for _ in range(40):
        u = rng.random(len(hm.PARAMS))
        runs = []
        for k in range(6):
            o = out(1500 + 1000 * u[0] + 50 * rng.normal(), 27 + 600 * u[1], 600, 920)
            o["n_at_day_315"] = 620 * np.exp(0.5 * (u[2] - 0.5) + 0.05 * rng.normal())
            runs.append({"seed": 7000 + k, "u": list(u), "outputs": o})
        pts.append({"u": list(u), "runs": runs})
    em = rp.RepEmulators(pts)
    U = rng.random((50, len(hm.PARAMS)))
    assert em.impl(U).shape == (50, len(rp.MEAN))
    m, sd = em.arc(U)
    assert m.shape == (50,) and np.all(sd >= 0) and em.keep(U).dtype == bool
    hm.PARAMS = hm.param_set(False)


if __name__ == "__main__":
    test_gp_recovers_a_known_function()
    test_history_match_scales()
    test_history_match_rep_scoring()
    print("test_emulator: OK")
