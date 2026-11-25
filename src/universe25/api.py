"""Run Universe 25 from Python: one run, many seeds, and a check against Calhoun's record.

    import universe25 as u25

    r = u25.run("universe25", seed=7001)     # one 1,600-day run, about a minute on one core
    print(r.table())                          # the run beside Calhoun's record
    r.plot("population.png")

    runs = u25.run_many("universe25", seeds=range(7000, 7012), workers=4)
    print(u25.record_check(runs).table())     # the record against the runs' 5-95 % ranges

Seeds are 7000-9999 (the repo keeps a seed ledger, docs/SEEDS.md). On Windows, call run_many
from under `if __name__ == "__main__":` (it starts worker processes).

Every number is measured as the repo's own validations measure it (scripts/replica_report.py and
scripts/history_match.py), so a check on the published seeds gives the published counts. Runs use
the NumPy path at 6 ticks a day: the same colony, seed, days and overrides give the same run.
The package runs from a clone of the repo (`pip install -e .`).
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np

from universe25.colonies import DEFAULT, colony_overrides, repo_root

# The record's 14 population and timeline numbers (Calhoun 1973, Calhoun 1971, Marsden 1972;
# docs/RECORD_FIT.md). name: (value, the record's own range where it is contested, meaning)
RECORD = {
    "first_litters_day": (77.0, (50.0, 104.0), "first litters (day; the record gives 50-104)"),
    "n_at_day_315": (620.0, None, "population on day 315"),
    "adults_at_day_315": (150.0, None, "adults on day 315 (131 days or older, Calhoun's count)"),
    "peak_n": (2200.0, None, "peak population"),
    "plateau_onset_day": (560.0, None, "plateau onset (day the colony reaches 97 % of its peak)"),
    "n_at_day_736": (2056.0, None, "population on day 736"),
    "n_at_day_811": (1871.0, None, "population on day 811"),
    "n_at_day_960": (1650.0, None, "population on day 960"),
    "doubling_b": (55.0, None, "doubling time, first litters to day 315 (days)"),
    "doubling_c": (125.0, (105.0, 145.0),
                   "doubling time, day 315 to the plateau (days; the record gives 105-145)"),
    "last_young_day": (600.0, None, "last surviving birth (day; rate-based)"),
    "last_conception_day": (920.0, None, "last conception (day; rate-based)"),
    "n_at_day_1444": (122.0, None, "population on day 1,444 (Calhoun had removed about 150)"),
    "n_at_day_1588": (27.0, None, "population on day 1,588"),
}
# Calhoun's behavioural and social numbers. name: (value, meaning, the measurement's name)
BEHAVIOUR = {
    "withdrawn_560": (0.32, "withdrawn share of the weaned, day 560", "withdrawn_560"),
    "never_fought_or_mated_800": (0.53, "never fought as adults or mated, aged 131-320 d, day 800",
                                  "beautiful_800_adult"),
    "male_share_315": (0.40, "male share of the weaned, day 315", "male_share_315"),
    "male_share_1444": (0.18, "male share of the weaned, day 1,444", "male_share_1444"),
    "empty_boxes_560": (0.25, "empty share of the 256 nest boxes, day 560", "empty_boxes_560"),
    "brood_groups_315": (14.0, "brood groups (sires with young) by day 315", "brood_groups_315"),
}
# Calhoun's censuses, for plots: (day, N)
CENSUS = ((315, 620), (560, 2200), (736, 2056), (811, 1871), (960, 1650), (1444, 122),
          (1588, 27))
_READ = {"adults_at_day_315": "adults_131_at_day_315"}  # Calhoun's adults (docs/RECORD_FIT_2.md)


def _scripts():
    """The repo's measurement code (scripts/), the one every published validation used."""
    root = repo_root()
    for p in (root / "scripts", root / "src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import history_match as hm
    import history_match_rep as hmr
    import replica_report as rr

    return hm, hmr, rr


def is_arc(targets: dict) -> bool:
    """Calhoun's arc: growth past 1,800, a phase of at least 150 days with conceptions but no
    surviving young, and fewer than 300 left on day 1,588."""
    _, hmr, _ = _scripts()
    return bool(hmr.is_arc(targets))


@dataclass
class Run:
    """One run of a colony: its population by day and its numbers beside the record."""
    colony: str
    seed: int
    days: float
    overrides: dict
    population: np.ndarray  # N at the end of each day; index 0 is day 1
    targets: dict[str, float]  # the record's 14 numbers (RECORD), measured on this run
    behaviour: dict[str, float]  # Calhoun's behavioural numbers (BEHAVIOUR), on this run
    raw: dict = field(repr=False, default_factory=dict)  # everything measured, by name

    @property
    def arc(self) -> bool:
        return is_arc(self.targets)

    def table(self) -> str:
        rows = [(k, _fmt_record(k), _fmt(self.targets[k])) for k in RECORD]
        rows += [(k, _fmt(v[0]), _fmt(self.behaviour[k])) for k, v in BEHAVIOUR.items()]
        rows.append(("the arc", "yes", "yes" if self.arc else "no"))
        head = f"{self.colony}, seed {self.seed}, {self.days:g} days"
        return head + "\n" + _table(("measure", "record", "this run"), rows)

    def to_dict(self) -> dict:
        return {"colony": self.colony, "seed": self.seed, "days": self.days,
                "overrides": self.overrides, "arc": self.arc, "targets": self.targets,
                "behaviour": self.behaviour, "population": [int(v) for v in self.population]}

    def plot(self, path: str | Path | None = None, ax=None):
        """The population by day with Calhoun's censuses; saved to `path` if given."""
        fig = None
        if ax is None and path is not None:  # no pyplot: a notebook's backend is left alone
            from matplotlib.figure import Figure

            fig = Figure(figsize=(8, 4.5))
            ax = fig.subplots()
        elif ax is None:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 4.5))
        day = np.arange(1, self.population.size + 1)
        ax.plot(day, self.population, color="#1A1A1A", lw=1.4,
                label=f"{self.colony}, seed {self.seed}")
        cd, cn = zip(*CENSUS)
        ax.scatter(cd, cn, color="#8B1E1E", zorder=3, s=28, label="Calhoun's census")
        ax.set_xlabel("day")
        ax.set_ylabel("mice")
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        if path is not None:
            (fig or ax.figure).savefig(path, dpi=150, bbox_inches="tight")
        return ax


def _job(job: tuple[str, int, float, dict]) -> Run:
    colony, seed, days, overrides = job
    for k in ("seed", "days"):
        if k in overrides:
            raise ValueError(f"pass {k} as an argument, not in overrides")
    hm, _, rr = _scripts()
    path, over = colony_overrides(colony, overrides)
    _, _, r = rr.run_one((colony, Path(path).name, over, int(seed), float(days)))
    o = hm.outputs(r)
    targets = {k: float(o.get(_READ.get(k, k), np.nan)) for k in RECORD}
    behaviour = {k: float(o.get(v[2], np.nan)) for k, v in BEHAVIOUR.items()}
    return Run(colony, int(seed), float(days), dict(overrides),
               np.asarray(r["n_series"], dtype=np.int64), targets, behaviour,
               {"outputs": o, **r})


def run(colony: str = DEFAULT, seed: int = 7000, days: float = 1600.0,
        overrides: dict | None = None) -> Run:
    """One run. `overrides` are nested config values over the colony's, e.g.
    {"biology": {"litter_mean": 5.0}} (the fields: src/universe25/config.py)."""
    return _job((colony, int(seed), float(days), dict(overrides or {})))


def run_many(colony: str = DEFAULT, seeds: Iterable[int] = range(7000, 7012),
             days: float = 1600.0,
             overrides: dict | None = None, workers: int | None = None) -> list[Run]:
    """One run per seed, `workers` at a time (default: all cores but one), in seed order."""
    jobs = [(colony, int(s), float(days), dict(overrides or {})) for s in seeds]
    if workers is None:
        workers = max(1, min(len(jobs), (os.cpu_count() or 2) - 1))
    if workers <= 1 or len(jobs) <= 1:
        return [_job(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_job, jobs))


@dataclass
class RecordCheck:
    """The record against the 5-95 % range of many runs: "inside" when the record (or, where it
    is contested, its range) meets that range. The repo's validations use this rule."""
    colony: str
    seeds: list[int]
    rows: dict[str, dict]  # name -> record, range, p05, median, p95, inside
    behaviour: dict[str, dict]  # name -> record, p05, median, p95, inside
    inside: int  # of the 14
    arc: int  # runs with Calhoun's arc
    n: int  # runs

    def table(self) -> str:
        rows = [(k, _fmt_record(k), _fmt_q(v), "yes" if v["inside"] else "no")
                for k, v in self.rows.items()]
        rows += [(k, _fmt(v["record"]), _fmt_q(v), "yes" if v["inside"] else "no")
                 for k, v in self.behaviour.items()]
        head = (f"{self.colony}, {self.n} runs: {self.inside} of {len(self.rows)} record numbers "
                f"inside; the arc in {self.arc} of {self.n}")
        return head + "\n" + _table(("measure", "record", "median [5-95 %]", "inside"), rows)

    def to_dict(self) -> dict:
        return {"colony": self.colony, "seeds": self.seeds, "n": self.n, "inside": self.inside,
                "arc": self.arc, "rows": self.rows, "behaviour": self.behaviour}


def _range(values: list[float]) -> list[float] | None:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    return np.quantile(v, [0.05, 0.5, 0.95]).tolist() if v.size else None


def record_check(runs: list[Run]) -> RecordCheck:
    """How many of the record's 14 numbers fall inside the runs' 5-95 % ranges, and how many
    runs show the arc. Use 48 seeds for a check comparable to the repo's validations."""
    if not runs:
        raise ValueError("no runs")
    colonies = {r.colony for r in runs}
    if len(colonies) > 1:
        raise ValueError(f"runs of several colonies: {sorted(colonies)}")
    rows: dict[str, dict] = {}
    for k, (z, rng, _) in RECORD.items():
        q = _range([r.targets[k] for r in runs])
        lo, hi = rng or (z, z)
        ok = bool(q is not None and q[0] <= hi and lo <= q[2])
        rows[k] = {"record": z, "range": list(rng) if rng else None,
                   "p05": q[0] if q else None, "median": q[1] if q else None,
                   "p95": q[2] if q else None, "inside": ok}
    beh: dict[str, dict] = {}
    for k, (z, *_rest) in BEHAVIOUR.items():
        q = _range([r.behaviour[k] for r in runs])
        beh[k] = {"record": z, "p05": q[0] if q else None, "median": q[1] if q else None,
                  "p95": q[2] if q else None,
                  "inside": bool(q is not None and q[0] <= z <= q[2])}
    return RecordCheck(runs[0].colony, [r.seed for r in runs], rows, beh,
                       sum(v["inside"] for v in rows.values()), sum(r.arc for r in runs),
                       len(runs))


def _fmt(x) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    return f"{x:.2f}" if abs(x) < 2 else f"{x:,.0f}"


def _fmt_record(k: str) -> str:
    z, rng, _ = RECORD[k]
    return f"{rng[0]:g}-{rng[1]:g}" if rng else _fmt(z)


def _fmt_q(v: dict) -> str:
    if v["median"] is None:
        return "n/a"
    return f"{_fmt(v['median'])} [{_fmt(v['p05'])}, {_fmt(v['p95'])}]"


def _table(head: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    w = [max(len(str(r[i])) for r in [head, *rows]) for i in range(len(head))]
    line = "  ".join(h.ljust(w[i]) for i, h in enumerate(head))
    out = [line, "  ".join("-" * x for x in w)]
    out += ["  ".join(str(c).ljust(w[i]) if i == 0 else str(c).rjust(w[i])
                      for i, c in enumerate(r)) for r in rows]
    return "\n".join(out)
