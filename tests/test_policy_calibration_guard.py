"""Calibration guard for policy arms (P4-1, H-d): the verdict rule on synthetic rows, a
control-vs-control run with zero drift, and a frozen-MLP arm that runs end to end. The random
net is a near-uniform policy and makes no calibration claim, so its drift is printed, not
asserted (the guard's job is to measure it)."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.calib.policy_guard import (  # noqa: E402
    CANONICAL,
    REPORT_KEYS,
    decline_band_ok,
    drift_table,
    format_table,
    guard,
    run_arm,
    verdict,
    write_report,
)

SEEDS = [7100, 7101, 7102]
DAYS = 400.0


def _rows(peak: float, n1200: float = float("nan"), first: float = 100.0) -> dict:
    return {s: {"first_litters_day": first, "n_at_day_315": 600.0, "peak_n": peak,
                "peak_day": 550.0, "last_young_day": 600.0, "n_at_day_736": 2000.0,
                "last_conception_day": 920.0, "n_at_day_1200": n1200,
                "n_at_day_1444": float("nan"), "n_at_day_1588": float("nan"),
                "final_n": 500.0} for s in SEEDS}


def test_verdict_rule_on_synthetic_rows() -> None:
    control = _rows(2200.0, 1100.0)
    same = drift_table(control, _rows(2200.0, 1100.0))
    assert all(same[k]["rel_drift"] == 0.0 for k in CANONICAL)
    assert verdict(same, decline_band_ok(_rows(2200.0, 1100.0)))["preserved"]
    # a 15 % peak miss fails H-d, a 5 % one passes
    v = verdict(drift_table(control, _rows(2530.0, 1100.0)), True)
    assert not v["preserved"] and v["failures"] == ["peak_n"]
    assert verdict(drift_table(control, _rows(2310.0, 1100.0)), True)["preserved"]
    # the decline band: N@1200 at 90 % of the peak fails, below the horizon it is not checked
    assert decline_band_ok(_rows(2200.0, 1980.0)) is False
    assert decline_band_ok(_rows(2200.0)) is None
    low = _rows(2200.0, 1980.0)
    v2 = verdict(drift_table(control, low), decline_band_ok(low))
    assert v2["failures"] == ["decline_band_1200"]
    v3 = verdict(drift_table(control, _rows(2200.0)), decline_band_ok(_rows(2200.0)))
    assert v3["preserved"] and not v3["decline_band_checked"]


def test_control_vs_control_has_zero_drift_and_mlp_arm_runs() -> None:
    control = run_arm("need_driven", SEEDS, DAYS, workers=1)
    assert set(control) == set(SEEDS)
    rep = guard("need_driven", SEEDS, DAYS, workers=1, control_rows=control)
    for k in CANONICAL:
        assert rep["table"][k]["rel_drift"] == 0.0, k
        assert rep["table"][k]["paired_diff"] == 0.0, k
    assert rep["verdict"]["preserved"] and not rep["verdict"]["decline_band_checked"]
    # frozen MLP with one fixed random net across the seeds
    from universe25.agents.policy import MlpFrozenPolicy

    w = Path(tempfile.mkdtemp(prefix="u25guard_w_")) / "random_7100.npz"
    MlpFrozenPolicy.random_init(7100).save_npz(str(w))
    rep2 = guard("mlp_frozen", SEEDS, DAYS, workers=1, weights=str(w), control_rows=control)
    print(format_table(rep2))
    for k in REPORT_KEYS:
        assert k in rep2["table"]
    for k in ("peak_n", "n_at_day_315", "final_n"):
        assert np.isfinite(rep2["table"][k]["arm_mean"]), k
    assert isinstance(rep2["verdict"]["preserved"], bool)
    out = Path(tempfile.mkdtemp(prefix="u25guard_o_")) / "guard.json"
    write_report(rep2, out)
    assert out.exists() and out.stat().st_size > 100


if __name__ == "__main__":
    test_verdict_rule_on_synthetic_rows()
    test_control_vs_control_has_zero_drift_and_mlp_arm_runs()
    print("test_policy_calibration_guard: OK")
