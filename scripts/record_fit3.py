#!/usr/bin/env python
"""Record fit 3 (U-4): choose the candidate by the validation's own measure on 48 training
seeds (docs/RECORD_FIT_3.md).

U-1 and U-3 chose by the second-largest implausibility (I2) on 12 training seeds, and both
picked a member whose arc did not hold on fresh seeds. On those 12 seeds it was tied with the
final replica (I2 1.91 against 1.93), whose arc holds (46 of 48 fresh runs twice). Here:
- The pool is every ensemble member that M5d, U-1 and U-3 ran on the 12 training seeds
  7000-7011 with M5d's settings. Each is scored on those seeds, with adults counted as Calhoun
  counted them (aged 131 days or more).
- Members already validated on fresh seeds (the final replica, U-1's member and U-1's chain
  member; all below the bar) are not candidates again.
- The best N_CAND by that score run 36 more training seeds, 7012-7047.
- On its 48 training seeds, each is scored by the validation's measure. A candidate must meet
  the bar there before any fresh seed is used (stop rule).

usage:
  python scripts/record_fit3.py --pool [--workers 8]      (score the pool; replays as needed)
  python scripts/record_fit3.py --select [--workers 10]   (36 seeds per candidate; the rule)
  python scripts/record_fit3.py --validate [--workers 10] (fresh seeds, if --select chose one)
--select exits 3 when no candidate meets the bar on its 48 training seeds (the stop rule).
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import history_match as hm  # noqa: E402
import history_match_rep as hmr  # noqa: E402
import record_fit as rf  # noqa: E402
import record_fit2 as r2  # noqa: E402

LABEL = "hm_record3"
OUT = ROOT / "_output" / LABEL
POOL_LABELS = ("hm_m5d", "hm_record", "hm_record2")  # M5d's settings, 12-seed ensembles
TRAIN = tuple(range(7000, 7012))
SELECT = tuple(range(7012, 7048))  # 36 more training seeds (docs/SEEDS.md)
FRESH = tuple(range(9160, 9200)) + tuple(range(9464, 9472))  # 48 (docs/SEEDS.md)
FRESH_ARG = "9160-9199,9464-9471"
N_CAND = 6  # pool members that run the selection seeds
MIN_ARC_12 = 10  # a pool member needs the arc on this many of its 12 seeds
BAR_INSIDE, BAR_ARC = 12, 43  # the bar, on 48 runs (as U-1 and U-3)
CANDIDATE = ROOT / "configs" / "record_fit3_candidate.json"
FINAL = ROOT / "configs" / "replica_v2_final.json"
# members already validated on fresh seeds, all below the bar: not candidates again
VALIDATED = (FINAL, ROOT / "configs" / "record_fit_candidate.json",
             ROOT / "configs" / "record_fit_chain_member.json")
FOURTEEN = rf.MEAN + rf.COND
KEY = r2.KEY


def ukey(u: list[float]) -> tuple:
    return tuple(round(v, 10) for v in u)


def inside(runs: list[dict]) -> tuple[int, list[str]]:
    """The validation's measure (scripts/replica_validate.py): is the record inside the 5-95 %
    range of the runs (its own range where it is contested)? Adults read as Calhoun's."""
    from replica_validate import CONTESTED

    n, miss = 0, []
    for name in FOURTEEN:
        v = np.array([r["outputs"].get(name, np.nan) for r in runs], float)
        v = v[np.isfinite(v)]
        z = hm.OUTPUTS[name][0]
        lo, hi = CONTESTED.get(name, (z, z))
        if v.size and np.quantile(v, 0.05) <= hi and lo <= np.quantile(v, 0.95):
            n += 1
        else:
            miss.append(name)
    return n, miss


def setup() -> None:
    r2.configure()
    rf.setup()  # the 14 targets; adults read from KEY in every loaded run
    hm.PARAMS = hm.param_set(True)
    hm.FIXED = hmr.FIXED
    hm.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)


def load(label: str) -> list[dict]:
    path = ROOT / "_output" / label / "runs.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def pool_runs(workers: int) -> dict[tuple, list[dict]]:
    """Every pool member with its runs on TRAIN, each carrying KEY (replayed when missing and
    checked against the stored run; replays cached in OUT/replays.jsonl)."""
    members: dict[tuple, dict[int, dict]] = {}
    for label in POOL_LABELS:
        runs = load(label)
        ens = {ukey(r["u"]) for r in runs if r["wave"] == 99}
        for r in runs:
            k = ukey(r["u"])
            if k in ens and r["seed"] in TRAIN:
                have = members.setdefault(k, {}).get(r["seed"])
                if have is None or (KEY not in have["outputs"] and KEY in r["outputs"]):
                    members[k][r["seed"]] = r
    # U-1's observed members kept their 7000-7005 runs in hm_record; hm_record2 holds the same
    # runs re-measured (record_fit2 --replay)
    measured = {r["key"]: r for r in load("hm_record2") if KEY in r["outputs"]}
    cache_path = OUT / "replays.jsonl"
    cache = {}
    if cache_path.exists():
        cache = {json.loads(x)["key"]: json.loads(x)
                 for x in cache_path.read_text(encoding="utf-8").splitlines() if x}
    todo = []
    for k, by_seed in members.items():
        for s, r in by_seed.items():
            if KEY in r["outputs"]:
                continue
            if r["key"] in measured:
                by_seed[s] = measured[r["key"]]
            elif r["key"] not in cache:
                todo.append(r)
    if todo:
        print(f"replaying {len(todo)} runs to day 316", flush=True)
        with ProcessPoolExecutor(workers) as ex, cache_path.open("a", encoding="utf-8") as fh:
            for r, m in zip(todo, ex.map(r2.replay_one, todo)):
                ok = bool(m["n"] == r["outputs"]["n_at_day_315"]
                          and m["mature"] == r["outputs"]["adults_at_day_315"])
                cache[r["key"]] = {"key": r["key"], "match": ok, **m}
                fh.write(json.dumps(cache[r["key"]]) + "\n")
    bad = 0
    out = {}
    for k, by_seed in members.items():
        rs = []
        for s in sorted(by_seed):
            r = by_seed[s]
            if KEY not in r["outputs"]:
                c = cache[r["key"]]
                bad += not c["match"]
                r["outputs"][KEY] = float(c["age131"]) if c["match"] else float("nan")
            rs.append(r)
        if len(rs) == len(TRAIN):
            out[k] = rf.read_as(rs)
    print(f"pool: {len(out)} members with all {len(TRAIN)} training seeds; "
          f"{bad} replays did not match", flush=True)
    return out


def score_pool(workers: int) -> list[dict]:
    pool = pool_runs(workers)
    va = hmr.v_arc(list(pool.values()))
    final_u = ukey(json.loads(FINAL.read_text(encoding="utf-8"))["members"][0]["u"])
    seen = {ukey(json.loads(p.read_text(encoding="utf-8"))["members"][0]["u"]): p.name
            for p in VALIDATED}
    ens = {lb: {ukey(r["u"]) for r in load(lb) if r["wave"] == 99} for lb in POOL_LABELS}
    rows = []
    for k, rs in pool.items():
        sc = hmr.score(rs, va)
        n_in, miss = inside(rs)
        rows.append({"u": list(k), "params": rs[0]["params"], "inside_12": n_in, "misses_12": miss,
                     "arc_12": len(sc["arc_seeds"]), "i2_12": sc["i2"],
                     "final_replica": k == final_u, "validated_before": seen.get(k),
                     "source": [lb for lb in POOL_LABELS if k in ens[lb]]})
    rows.sort(key=lambda t: (-t["inside_12"], -t["arc_12"], t["i2_12"]))
    return rows


def pool(workers: int) -> int:
    setup()
    rows = score_pool(workers)
    cand = [t for t in rows
            if t["arc_12"] >= MIN_ARC_12 and not t["validated_before"]][:N_CAND]
    (OUT / "pool.json").write_text(json.dumps({"rows": rows, "candidates": cand}, indent=1,
                                              default=float), encoding="utf-8")
    print(f"{len(rows)} pool members; the arc on >= {MIN_ARC_12} of 12 in "
          f"{sum(t['arc_12'] >= MIN_ARC_12 for t in rows)}; validated before: "
          f"{sum(bool(t['validated_before']) for t in rows)}")
    print("rank  inside/14  arc/12   I2    source        validated before")
    for i, t in enumerate(rows[:20]):
        mark = "  <- candidate" if t in cand else ""
        print(f"{i + 1:3d}   {t['inside_12']:2d}        {t['arc_12']:2d}    {t['i2_12']:5.2f}  "
              f"{','.join(s.replace('hm_', '') for s in t['source']):12s}  "
              f"{t['validated_before'] or '':28s}{mark}")
    return 0


def select(workers: int) -> int:
    setup()
    doc = json.loads((OUT / "pool.json").read_text(encoding="utf-8"))
    cand = doc["candidates"]
    jobs = [(hm.key_of(np.asarray(c["u"]), s), [float(v) for v in c["u"]], s, 1, c["params"])
            for c in cand for s in SELECT]
    hm.run_jobs(jobs, workers)
    runs = hm.load_runs()  # read through READ_AS
    pool = pool_runs(workers)
    rows = []
    for c in cand:
        k = ukey(c["u"])
        rs = pool[k] + sorted([r for r in runs if ukey(r["u"]) == k and r["seed"] in SELECT],
                              key=lambda r: r["seed"])
        assert len(rs) == len(TRAIN) + len(SELECT), (k[:3], len(rs))
        n_in, miss = inside(rs)
        arc = sum(hmr.is_arc(r["outputs"]) for r in rs)
        sc = hmr.score(rs, hmr.v_arc([rs]))
        rows.append({**c, "inside_48": n_in, "misses_48": miss, "arc_48": arc,
                     "i2_48": sc["i2"], "meets_bar": bool(n_in >= BAR_INSIDE and arc >= BAR_ARC)})
    rows.sort(key=lambda t: (-t["inside_48"], -t["arc_48"], t["i2_48"]))
    qual = [t for t in rows if t["meets_bar"]]
    print(f"{len(rows)} candidates on {len(TRAIN) + len(SELECT)} training seeds:")
    for t in rows:
        print(f"  inside {t['inside_48']:2d}/14  arc {t['arc_48']:2d}/48  I2 {t['i2_48']:.2f}  "
              f"{'final replica ' if t['final_replica'] else ''}misses: "
              + ", ".join(t["misses_48"]))
    (OUT / "select.json").write_text(json.dumps(rows, indent=1, default=float), encoding="utf-8")
    if not qual:
        print(f"STOP RULE: no candidate meets the bar ({BAR_INSIDE} of 14 inside and the arc in "
              f"{BAR_ARC} of 48) on its training seeds; no fresh seed is used")
        return 3
    best = qual[0]
    CANDIDATE.write_text(json.dumps({
        "record_fit3_candidate": True, "rule": "the validation's measure on 48 training seeds",
        "n_candidates": len(rows), "n_meet_bar": len(qual), "members": [best]},
        indent=1, default=float), encoding="utf-8")
    print(f"candidate: inside {best['inside_48']}/14, arc {best['arc_48']}/48"
          f"{' (the final replica)' if best['final_replica'] else ''}; wrote {CANDIDATE.name}")
    return 0


def validate(workers: int) -> int:
    for path, label in ((CANDIDATE, "record_fit3"), (FINAL, "record_fit3_final_replica")):
        cmd = [sys.executable, "-X", "utf8", "-u", str(ROOT / "scripts" / "replica_validate.py"),
               "--ensemble", str(path), "--part", "pen", "--pen-seeds", FRESH_ARG, "--label",
               label, "--adults-131", "--workers", str(workers)]
        print(" ".join(cmd[3:]), flush=True)
        subprocess.run(cmd, check=True, cwd=ROOT)
    return 0


def main() -> int:
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 8
    if "--pool" in args:
        return pool(workers)
    if "--select" in args:
        return select(workers)
    if "--validate" in args:
        return validate(workers)
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
