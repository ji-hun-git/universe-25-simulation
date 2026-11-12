"""H-g rates and phases (metrics/phase_rates.py; PHASE4_DESIGN.md section 4.3): phase boundaries
follow the record's proportions, episode counts match the detectors' own segmentation, the trend
statistics and the exact sign-flip test behave as preregistered, the decision rule reads each
case as written, and the module is eval-only with no play-named identifier (H2)."""
from __future__ import annotations

import io
import itertools
import sys
import tokenize
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.metrics.detectors import (  # noqa: E402
    event_mask,
    gap_criterion,
    prepare,
    segment,
)
from universe25.metrics.phase_rates import (  # noqa: E402
    PHASE_B_FRACTION,
    cell_decision,
    detector_windows,
    label_windows,
    overall,
    phase_b_end,
    phase_of,
    run_taus,
    sign_flip,
    window_rates,
)
from universe25.metrics.synthetic_traces import make_colony  # noqa: E402


def test_phase_boundaries_follow_the_record() -> None:
    assert abs(PHASE_B_FRACTION - 211.0 / 456.0) < 1e-12
    assert abs(phase_b_end(104.0, 560.0) - 315.0) < 1e-9  # the record maps onto itself
    t_fl, t_pk = 100.0, 560.0
    b = phase_b_end(t_fl, t_pk)
    assert phase_of(99.9, t_fl, t_pk) == "A"
    assert phase_of(100.0, t_fl, t_pk) == "B"
    assert phase_of(b - 1e-6, t_fl, t_pk) == "B"
    assert phase_of(b, t_fl, t_pk) == "C"
    assert phase_of(560.0, t_fl, t_pk) == "C"
    assert phase_of(560.1, t_fl, t_pk) == "D"
    assert phase_of(300.0, float("nan"), t_pk) == "A"


def test_window_rates_count_the_detectors_episodes() -> None:
    tr = make_colony("all_criteria_k12", n_individuals=12, days=6, seed=5)
    out = window_rates(tr)
    S = prepare(tr)
    rows_per_day = int(tr["meta"]["decisions_per_day"])
    weaned = S.age >= 21.0
    assert out["n_weaned_individuals"] == 12
    assert abs(out["weaned_individual_days"] - weaned.sum() / rows_per_day) < 1e-9
    for kind in ("object", "locomotor"):
        ev, _ = event_mask(S, kind, fixed=False)
        c, _ = gap_criterion(S, ev, max_gap=rows_per_day)
        s, _, _ = segment(S, ev, c)
        r = out[kind]
        assert r["n_episodes"] == s.size and r["n_events"] == int(ev.sum())
        assert r["n_onsets_weaned"] == int(weaned[s].sum())
        assert abs(r["rate"] - r["n_onsets_weaned"] / out["weaned_individual_days"]) < 1e-12
        assert r["rate_eligible"] >= r["rate"]  # eligible rows are a subset of weaned rows
    for k in ("relaxed_share_weaned", "stressed_share_weaned", "withdrawn_share_weaned",
              "juvenile_share_weaned"):
        assert 0.0 <= out[k] <= 1.0, k
    assert out["withdrawn_share_weaned"] == 0.0  # synthetic rows carry role 4


def _windows(rates: list[float], mids: list[float], t_fl: float, t_pk: float,
             n_weaned: int = 50) -> list[dict]:
    w = [{"mid": m, "n_weaned_individuals": n_weaned, "object": {"rate": r},
          "locomotor": {"rate": r}} for m, r in zip(mids, rates)]
    label_windows(w, t_fl, t_pk)
    return w


def test_run_taus_read_falls_rises_and_undefined_cases() -> None:
    t_fl, t_pk = 100.0, 500.0  # B to 285.1, C to 500, D after
    mids = [155.0, 205.0, 305.0, 405.0, 505.0, 605.0, 705.0, 805.0]
    falling = run_taus(_windows([8, 7, 6, 5, 4, 3, 2, 1], mids, t_fl, t_pk), "object")
    assert falling["tau_bcd"] < 0 and falling["tau_d"] == -1.0
    assert falling["n_windows"] == 8 and falling["n_d_windows"] == 4
    rising_d = run_taus(_windows([8, 7, 6, 5, 1, 2, 3, 4], mids, t_fl, t_pk), "object")
    assert rising_d["tau_d"] == 1.0
    flat = run_taus(_windows([2.0] * 8, mids, t_fl, t_pk), "object")
    assert flat["tau_bcd"] == 0.0 and flat["tau_d"] == 0.0
    one_phase = run_taus(_windows([3, 2, 1], [605.0, 705.0, 805.0], t_fl, t_pk), "object")
    assert np.isnan(one_phase["tau_bcd"]) and one_phase["tau_d"] == -1.0
    short_d = run_taus(_windows([3, 2, 1, 0], [205.0, 305.0, 505.0, 605.0], t_fl, t_pk),
                       "object")
    assert np.isnan(short_d["tau_d"]) and short_d["tau_bcd"] < 0
    few = _windows([8, 7, 6, 5, 4, 3, 2, 1], mids, t_fl, t_pk, n_weaned=9)
    assert not any(x["entered"] for x in few)
    assert np.isnan(run_taus(few, "object")["tau_bcd"])


def test_sign_flip_is_exact() -> None:
    v = np.array([0.4, -0.1, 0.3, 0.2, 0.5])
    res = sign_flip(v)
    means = [np.mean(np.array(s) * v) for s in itertools.product((1, -1), repeat=5)]
    assert res["p_rise"] == np.mean(np.array(means) >= v.mean() - 1e-12)
    assert res["p_fall"] == np.mean(np.array(means) <= v.mean() + 1e-12)
    allpos = sign_flip(np.ones(12))
    assert allpos["p_rise"] == 1 / 4096 and allpos["p_fall"] == 1.0
    assert sign_flip([np.nan, 1.0, 2.0])["n"] == 2
    assert sign_flip([])["n"] == 0


def test_decision_rule_reads_each_case() -> None:
    neg = -0.5 * np.ones(12)
    pos = 0.5 * np.ones(12)
    assert cell_decision(neg, neg)["reading"] == "supported"
    assert cell_decision(neg, pos)["reading"] == "falsified"
    assert cell_decision(pos, pos)["reading"] == "falsified"
    assert cell_decision(neg, np.zeros(12))["reading"] == "not supported"
    assert cell_decision(pos, neg)["reading"] == "not supported"
    # a rise at p 0.025 but above the Bonferroni level 0.0042 is not a falsification
    mixed = np.array([0.5] * 9 + [-0.4] * 3)
    d = cell_decision(neg, mixed)
    assert 0.0042 < d["T_d"]["p_rise"] < 0.025 and d["reading"] == "not supported"
    assert cell_decision([np.nan], [np.nan])["reading"] == "untested"
    assert overall(["supported"] * 6) == "supported"
    assert overall(["supported"] * 5 + ["falsified"]) == "falsified"
    assert overall(["supported"] * 5 + ["not supported"]) == "not supported"


def test_detector_windows_pick_the_preregistered_four() -> None:
    t_fl, t_pk = 100.0, 500.0
    mids = [155.0 + 50.0 * i for i in range(29)]
    w = _windows([1.0] * 29, mids, t_fl, t_pk)
    pick = detector_windows(w, t_fl, t_pk)
    b = phase_b_end(t_fl, t_pk)
    assert pick["B"] == 205.0  # middle of B: 192.5
    assert pick["C"] == 405.0  # middle of C: 392.6
    assert pick["D_early"] == 655.0 and pick["D_late"] == 1105.0
    assert phase_of(pick["B"], t_fl, t_pk) == "B" and pick["C"] >= b
    none = detector_windows(_windows([1.0], [605.0], t_fl, t_pk), t_fl, t_pk)
    assert none["B"] is None and none["C"] is None and none["D_late"] == 605.0


def test_phase_rates_is_eval_only_and_has_no_play_named_identifier() -> None:
    allowed = {"playground", "play_objects", "PlayObject", "playground_enabled",
               "playground_bounds", "in_playground"}
    path = ROOT / "src" / "universe25" / "metrics" / "phase_rates.py"
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
        if tok.type != tokenize.NAME or tok.string in allowed:
            continue
        low = tok.string.lower()
        assert "play" not in low, tok.string
        assert not any(p in low for p in ("bout", "motif", "exaggerat", "reward")), tok.string
    for pkg in ("agents", "learn"):
        for f in sorted((ROOT / "src" / "universe25" / pkg).glob("*.py")):
            assert "phase_rates" not in f.read_text(encoding="utf-8"), f.name


if __name__ == "__main__":
    test_phase_boundaries_follow_the_record()
    test_window_rates_count_the_detectors_episodes()
    test_run_taus_read_falls_rises_and_undefined_cases()
    test_sign_flip_is_exact()
    test_decision_rule_reads_each_case()
    test_detector_windows_pick_the_preregistered_four()
    test_phase_rates_is_eval_only_and_has_no_play_named_identifier()
    print("test_phase_rates: OK")
