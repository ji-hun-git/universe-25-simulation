#!/usr/bin/env python
"""Record fit: replica v2's M5d history matching, scored on the record's 14 population and
timeline numbers only (docs/RECORD_FIT.md).

The six behaviour targets of replica v2 are dropped from the implausibility (they are still
computed for every run and reported). Everything else is M5d's: the pen, the settings (hopper
facilitation off, maternal transmission on), the 22 parameters and their ranges, the seeds.
Two changes from M5d, both for the arc the record needs:
- wave 4 samples where the emulated arc frequency is at least P_MIN;
- the ensemble mixes the best observed points with emulated ones, and a member needs the arc
  on MIN_ARC of its 12 seeds.

usage:
  python scripts/record_fit.py --init              (copy M5d's waves 1-3 into _output/hm_record)
  python scripts/record_fit.py --fit               (emulators and the new NROY)
  python scripts/record_fit.py --wave 4 --n 120 --workers 10
  python scripts/record_fit.py --mix-ensemble --workers 10
  python scripts/record_fit.py --write-ensemble configs/record_fit_ensemble.json
  python scripts/record_fit.py --candidate configs/record_fit_ensemble.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import history_match as hm  # noqa: E402
import history_match_rep as hmr  # noqa: E402

LABEL = "hm_record"
SOURCE = "hm_m5d"  # waves 1-3 come from here
BASE = hmr.BASE  # wave 0: M5c's final emulators, as in M5d
OBS_WAVES = {1, 2, 3, 4}  # the ensemble's observed members come from these waves
READ_AS: dict[str, str] = {}  # target -> outputs key it is read from (U-3: record_fit2.py)
MEAN = ["first_litters_day", "n_at_day_315", "adults_at_day_315", "peak_n", "plateau_onset_day",
        "n_at_day_736", "n_at_day_811", "n_at_day_960", "doubling_b", "doubling_c"]
COND = ["last_young_day", "last_conception_day", "n_at_day_1444", "n_at_day_1588"]
P_MIN = 0.3  # wave 4 and the emulated ensemble members: emulated arc frequency at least this
MIN_ARC = 10  # a member needs the arc on this many of its 12 seeds
N_OBS, N_EM = 6, 18  # ensemble: best observed points, and points from the emulators
CANDIDATE = ROOT / "configs" / "record_fit_candidate.json"


def setup() -> None:
    """Score the 14 targets only; keep M5d's settings; aim the sampling at the arc."""
    hm.OUTPUTS = {k: hm.OUTPUTS[k] for k in MEAN + COND}
    hmr.MEAN, hmr.COND, hmr.MIN_ARC = list(MEAN), list(COND), MIN_ARC
    hmr.BASE = BASE
    base_check = hmr.check_label
    if READ_AS:  # every run is read through here, wave 0's included
        base_load_runs, base_load = hm.load_runs, hmr.load
        hm.load_runs = lambda: read_as(base_load_runs())
        hmr.load = lambda label: read_as(base_load(label))

    def check_label(label: str) -> None:  # the label also records its targets
        path = ROOT / "_output" / label / "targets.json"
        cur = {"mean": MEAN, "cond": COND, "source": SOURCE, "p_min": P_MIN,
               "ensemble": [N_OBS, N_EM]}
        if READ_AS:
            cur["read_as"] = READ_AS
        if OBS_WAVES != {1, 2, 3, 4}:
            cur["obs_waves"] = sorted(OBS_WAVES)
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            if old != cur:
                raise SystemExit(f"label {label} holds targets {old}; this script has {cur}")
        else:
            path.write_text(json.dumps(cur, indent=1), encoding="utf-8")
        base_check(label)

    def keep(self, U: np.ndarray) -> np.ndarray:  # not ruled out, and the arc likely
        return self.keep_mean(U) & (self.arc(U)[0] >= P_MIN)

    base_points = hmr.points

    def points(runs: list[dict], waves: set[int], n_seeds: int | None = None) -> list[dict]:
        if waves == {99}:  # the ensemble (write_ensemble, candidate): every member on 12 seeds
            return members(runs, base_points)
        return base_points(runs, waves, n_seeds)

    hmr.check_label = check_label
    hmr.RepEmulators.keep = keep
    hmr.points = points


def read_as(runs: list[dict]) -> list[dict]:
    """Each READ_AS target read from its outputs key, in memory (runs.jsonl keeps both keys).
    A run without the key gets NaN, which the emulators and the scoring leave out."""
    for r in runs:
        o = r["outputs"]
        for name, key in READ_AS.items():
            o[name] = float(o.get(key, float("nan")))
    return runs


def members(runs: list[dict], base_points) -> list[dict]:
    """The ensemble's members (wave 99), each with its runs on all 12 ensemble seeds. An
    observed member's runs on 7000-7005 were cached from its own wave and keep that wave's label,
    so grouping by wave 99 alone scores it on 6 seeds. The chain's first run did that and chose
    its candidate from the wrong pool (NOTES 2026-11-19)."""
    key = lambda u: tuple(round(v, 10) for v in u)  # noqa: E731  (as hmr.points groups)
    mem = {key(p["u"]): p for p in base_points(runs, {99})}
    by_seed: dict[tuple, dict[int, dict]] = {k: {} for k in mem}
    for r in runs:
        k = key(r["u"])
        if k in by_seed and r["seed"] in hmr.ENS_SEEDS:
            by_seed[k].setdefault(r["seed"], r)
    for k, p in mem.items():
        p["runs"] = [by_seed[k][s] for s in sorted(by_seed[k])]
        if len(p["runs"]) != len(hmr.ENS_SEEDS):
            raise SystemExit(f"member {k[:3]}... has {len(p['runs'])} of "
                             f"{len(hmr.ENS_SEEDS)} ensemble seeds")
    return list(mem.values())


def init() -> int:
    """Copy M5d's waves 1-3 (not its ensemble) into the record label."""
    src = ROOT / "_output" / SOURCE / "runs.jsonl"
    dst_dir = ROOT / "_output" / LABEL
    dst = dst_dir / "runs.jsonl"
    if dst.exists():
        print(f"{dst} exists; not copying")
        return 1
    dst_dir.mkdir(parents=True, exist_ok=True)
    keep = [x for x in src.read_text(encoding="utf-8").splitlines()
            if x and json.loads(x)["wave"] in (1, 2, 3)]
    dst.write_text("\n".join(keep) + "\n", encoding="utf-8")
    print(f"copied {len(keep)} runs of waves 1-3 from {SOURCE}")
    return 0


def mix_ensemble(workers: int, dry: bool = False) -> int:
    """Wave 99: the N_OBS best observed points of OBS_WAVES and N_EM from the top tenth of the
    emulated arc frequency, each on the 12 ensemble seeds."""
    runs = hm.load_runs()
    pts = hmr.points(runs, OBS_WAVES, len(hmr.REP_SEEDS))
    rep = hmr.RepEmulators(pts)
    va = hmr.v_arc([p["runs"] for p in pts])
    scored = [(hmr.score(p["runs"], va), p) for p in pts]
    obs = [p for sc, p in sorted(scored, key=lambda t: t[0]["i2"])
           if len(sc["arc_seeds"]) >= 4][:N_OBS]
    print(f"{len(pts)} points; {len(obs)} observed members:")
    for p in obs:
        sc = hmr.score(p["runs"], va)
        print(f"  wave {p['wave']} arc {len(sc['arc_seeds'])}/{sc['n_seeds']} I2 {sc['i2']:.2f}")
    em0 = hmr.base_emulators()
    C, st = hmr.sample(em0, rep, 10 * 5 * N_EM, seed=2699)
    print(f"emulated candidates: {st}")
    if not len(C):
        print("no emulated candidates")
        return 2
    m, _ = rep.arc(C)
    top = C[m >= np.quantile(m, 0.9)]
    rng = np.random.default_rng(2799)
    em = top[rng.choice(len(top), size=min(N_EM, len(top)), replace=False)]
    U = [np.asarray(p["u"]) for p in obs] + list(em)
    jobs = [hm.job_of(u, s, 99) for u in U for s in hmr.ENS_SEEDS]
    if dry:
        print(f"dry run: {len(jobs)} jobs ({len(U)} members), none run")
        return 0
    (hm.OUT / "ensemble_design.json").write_text(
        json.dumps({"observed": [p["u"] for p in obs], "sampling": st, "jobs": jobs}),
        encoding="utf-8")
    hm.run_jobs(jobs, workers)
    return 0


def candidate(path: Path) -> int:
    """The candidate among the ensemble's members (wave 99; the rule in docs/RECORD_FIT.md),
    written as a one-member file for scripts/replica_validate.py. `path` is the ensemble file
    written just before, named in the output."""
    runs = hm.load_runs()
    mem = hmr.points(runs, {99})
    va = hmr.v_arc([p["runs"] for p in mem])
    scored = []
    for p in mem:
        sc = hmr.score(p["runs"], va)
        sc.update({"u": p["u"], "params": p["params"]})
        scored.append(sc)
    arc_ok = [m for m in scored if len(m["arc_seeds"]) >= MIN_ARC]
    qual = [m for m in arc_ok if m["i2"] <= hm.CUT]
    pool, rule = ((qual, "qualifies") if qual else (arc_ok, "arc on >= 10 seeds") if arc_ok
                  else (scored, "lowest overall"))
    best = min(pool, key=lambda m: m["i2"])
    CANDIDATE.write_text(json.dumps({
        "record_fit_candidate": True, "rule": rule, "ensemble": str(path.name),
        "n_members": len(scored), "n_qualify": len(qual), "members": [best]},
        indent=1, default=float), encoding="utf-8")
    print(f"candidate ({rule}): I2 {best['i2']:.2f}, "
          f"arc {len(best['arc_seeds'])}/{best['n_seeds']}; "
          f"{len(qual)} of {len(scored)} members qualify; wrote {CANDIDATE.name}")
    return 0


def main() -> int:
    if "--init" in sys.argv:
        return init()
    setup()
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 8
    if "--mix-ensemble" in args or "--candidate" in args:
        hm.PARAMS = hm.param_set(True)
        hm.FIXED = hmr.FIXED
        hm.OUT = ROOT / "_output" / LABEL
        hmr.check_label(LABEL)
        if "--mix-ensemble" in args:
            return mix_ensemble(workers, dry="--dry" in args)
        return candidate(Path(args[args.index("--candidate") + 1]))
    sys.argv = [sys.argv[0], "--label", LABEL] + args
    return hmr.main()


if __name__ == "__main__":
    raise SystemExit(main())
