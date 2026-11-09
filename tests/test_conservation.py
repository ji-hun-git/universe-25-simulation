"""Alive count conservation: births - deaths = delta N; no play reward in config."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import SimConfig, load_config
from universe25.sim import Universe25Sim


def test_population_accounting() -> None:
    out = ROOT / "_output" / "test_cons"
    cfg = SimConfig(
        seed=7100,
        days=20.0,
        backend="numpy",
        device="cpu",
        max_agents=512,
        log_every_ticks=24,
        snapshot_every_days=0,
        arm_label="TRACK-E-U25-TEST",
    )
    sim = Universe25Sim(cfg, out)
    n0 = sim.agents.n_alive
    sim.run()
    expected = n0 + sim._births - sim._deaths
    assert sim.agents.n_alive == expected, (sim.agents.n_alive, expected, sim._births, sim._deaths)
    assert sim._nan_count == 0


def test_no_play_reward_in_config() -> None:
    cfg = load_config(ROOT / "configs" / "default.yaml")
    dumped = cfg.model_dump_json().lower()
    # Allowed mentions: playground geometry. Forbidden: play_reward / reward_play
    assert "play_reward" not in dumped
    assert "reward_play" not in dumped
    # Source audit: sim.py must not assign a play reward
    sim_src = (ROOT / "src" / "universe25" / "sim.py").read_text(encoding="utf-8")
    assert "play_reward" not in sim_src.lower()
    assert "reward_play" not in sim_src.lower()


def test_invariants_hold_past_the_first_births() -> None:
    """The calibrated colony (default.yaml) past its first litters with the runtime invariant
    checks on (universe25/invariants.py: population accounting, drive and capacity bounds,
    positions, pup actions, stocks), at K = 1 and with sub-steps, ball physics and novelty.
    The checks only read state, so they cannot hide a perturbation."""
    import tempfile

    for over in ({}, {"free_substeps": 12, "playground": {"ball_physics": True},
                      "drives": {"curiosity_novelty": True, "consequence_gain": 8.0}}):
        cfg = load_config(ROOT / "configs" / "default.yaml", {
            "seed": 7100, "days": 150.0, "ticks_per_day": 6, "backend": "numpy",
            "device": "cpu", "log_every_ticks": 6, "snapshot_every_days": 0,
            "debug_invariants": True, **over})
        sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25inv_")))
        s = sim.run()
        assert s["births"] > 0, "the run must reach the first litters"
        assert s["final_n"] == sim._n_initial + s["births"] - s["deaths"]
        assert s["litters_dropped_at_capacity"] == 0


def test_strict_config_and_reference_backend() -> None:
    """Unknown config keys are errors; ticks_per_day must be a multiple of the reference;
    `auto` is the NumPy reference path (review 2026-11-09)."""
    from universe25.agents.state import pick_backend

    for bad in ({"biology": {"gestaton_days": 19.0}}, {"polcy": {"kind": "need_driven"}},
                {"ticks_per_day": 9}, {"ticks_per_day": 3}):
        try:
            load_config(ROOT / "configs" / "default.yaml", bad)
        except ValueError:
            continue
        raise AssertionError(f"config {bad} must be refused")
    assert pick_backend("auto", "auto") == ("numpy", "cpu")


def test_removal_event_takes_adults_once_and_is_off_by_default() -> None:
    """biology.removal_day / removal_n (ported from the 2n branch for the posterior predictive
    check): once, on the first day-aligned tick at or after the day, that many alive adults
    leave; counted as removed, not deaths; the accounting invariant includes them."""
    import tempfile

    cfg = load_config(ROOT / "configs" / "default.yaml", {
        "seed": 7100, "days": 12.0, "ticks_per_day": 6, "backend": "numpy", "device": "cpu",
        "log_every_ticks": 6, "snapshot_every_days": 0, "debug_invariants": True,
        "biology": {"removal_day": 5.0, "removal_n": 3}})
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25rem_")))
    n0 = sim.agents.n_alive
    s = sim.run()
    assert s["removed"] == 3 and s["final_n"] == n0 + s["births"] - s["deaths"] - 3, s
    off = load_config(ROOT / "configs" / "default.yaml")
    assert off.biology.removal_n == 0 and off.biology.removal_day == 0.0


if __name__ == "__main__":
    test_no_play_reward_in_config()
    test_removal_event_takes_adults_once_and_is_off_by_default()
    test_population_accounting()
    test_invariants_hold_past_the_first_births()
    test_strict_config_and_reference_backend()
    print("test_conservation: OK")
