"""The interface for everyone (src/universe25/api.py, cli.py, colonies.py; docs/USER_GUIDE.md):
every colony's config validates; a run is the same for the same inputs and takes overrides;
record_check counts "inside" as the repo's validations do; the command line parses its values.
(That a run reproduces the published validation exactly was checked on seed 9112: NOTES
2026-11-25, "For everyone".)"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import universe25 as u25  # noqa: E402
from universe25.api import BEHAVIOUR, RECORD, Run  # noqa: E402
from universe25.cli import main as cli_main  # noqa: E402
from universe25.cli import parse_seeds, parse_set  # noqa: E402


def test_colonies() -> None:
    assert next(iter(u25.COLONIES)) == "universe25"
    for name in u25.COLONIES:
        cfg = u25.colony_config(name, {"seed": 7001})
        assert cfg.seed == 7001, name
    cfg = u25.colony_config("universe25", {"biology": {"litter_mean": 4.0}})
    assert cfg.biology.litter_mean == 4.0
    try:
        u25.colony_config("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown colony must be refused")


def test_run_is_repeatable_and_takes_overrides() -> None:
    a = u25.run("universe25", seed=7001, days=40.0)
    b = u25.run("universe25", seed=7001, days=40.0)
    assert np.array_equal(a.population, b.population) and a.population.size == 40
    assert set(a.targets) == set(RECORD) and set(a.behaviour) == set(BEHAVIOUR)
    c = u25.run("universe25", seed=7001, days=40.0, overrides={"initial_pairs": 8})
    assert c.population[0] == 16 and a.population[0] == 8, (c.population[0], a.population[0])
    assert "the arc" in a.table() and a.to_dict()["population"][:1] == [8]
    try:
        u25.run("universe25", seed=7001, days=10.0, overrides={"seed": 7002})
    except ValueError:
        pass
    else:
        raise AssertionError("seed in overrides must be refused")


def _fake(seed: int, **t) -> Run:
    targets = {k: v[0] for k, v in RECORD.items()}
    targets.update(t)
    return Run("universe25", seed, 1600.0, {}, np.zeros(1, np.int64), targets,
               {k: v[0] for k, v in BEHAVIOUR.items()})


def test_record_check_rule() -> None:
    runs = [_fake(7000 + i, peak_n=2500.0 + i, first_litters_day=100.0 + i) for i in range(20)]
    c = u25.record_check(runs)
    assert not c.rows["peak_n"]["inside"]  # 2,200 below every run
    assert c.rows["first_litters_day"]["inside"]  # 100-119 meets the record's 50-104
    assert c.inside == len(RECORD) - 1 and c.n == 20
    assert c.arc == 20  # the record's own numbers show the arc (gap 320)
    assert "13 of 14" in c.table()


def test_command_line() -> None:
    assert parse_set(["biology.litter_mean=5", "playground.enabled=false", "arm_label=x",
                      "biology.deprived_fertility=null", "biology.weaning_days=21.5"]) == {
        "biology": {"litter_mean": 5, "deprived_fertility": None, "weaning_days": 21.5},
        "playground": {"enabled": False}, "arm_label": "x"}
    assert parse_seeds("7000-7002,7010") == [7000, 7001, 7002, 7010]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert cli_main(["colonies"]) == 0
    assert "universe25  (default)" in buf.getvalue() and "reference" in buf.getvalue()


if __name__ == "__main__":
    test_colonies()
    test_run_is_repeatable_and_takes_overrides()
    test_record_check_rule()
    test_command_line()
    print("test_api: OK")
