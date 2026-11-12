#!/usr/bin/env python
"""Replica v2 M6: out-of-sample validation of the M5 ensemble (docs/REPLICA_V2.md).

1. Calhoun's pen: one ensemble member per fresh seed (9200-9247), 1,600 days. For each record
   landmark, is the record inside the 5-95 % range of the 48 runs (the record's own range
   where it is contested)? Structural numbers are reported against the M3/M4 targets.
2. The sibling universes of Calhoun 1971 Fig 3: 1, 2, 4 and 8 open cells (cells 0..n-1), 12
   fresh seeds each (9248-9295), 900 days, no removal event; same members in turn. Time is
   aligned as in the record: T = days after the first surviving litter (the first birth day
   of a pup that reached weaning). N at the record's T values against the record.

usage: python scripts/replica_validate.py --ensemble configs/replica_v2_ensemble.json
       [--workers 6] [--part pen|siblings|all] [--label m6] [--pen-seeds 9200-9247]
       [--sib-seeds 9248-9295]
The sibling seeds are split into four blocks of 12 (1, 2, 4, 8 cells, in that order).
Writes _output/replica_validate[_<label>].json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

PEN_SEEDS = tuple(range(9200, 9248))
SIB_SEEDS = {1: range(9248, 9260), 2: range(9260, 9272), 4: range(9272, 9284),
             8: range(9284, 9296)}
# Calhoun 1971 Fig 3 (docs/RESEARCH_DIGEST.md A3): (T, N) at the end of phase B, the end of
# phase C and later; final mice per cell. T = days after the first surviving litter.
SIBLINGS = {1: ([(142, 60), (293, 181), (498, 185)], 180),
            2: ([(150, 113), (298, 340), (602, 330)], 175),
            4: ([(230, 143), (453, 507), (573, 490)], 130),
            8: ([(190, 240), (378, 1120), (513, 1100)], 142),
            16: ([(251, 640), (493, 2200), (692, 2250)], 138)}
CONTESTED = {"first_litters_day": (50.0, 104.0), "doubling_c": (105.0, 145.0)}


def _deep(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _deep(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def run(job: tuple[str, dict, int, float, int]) -> dict:
    from replica_report import run_one

    part, params, seed, days, cells = job
    over = params
    if cells < 16:
        over = _deep(params, {"geometry": {"open_cells": list(range(cells))},
                              "biology": {"removal_n": 0, "removal_day": 0.0}})
    _, _, r = run_one(("val", "replica_v2.yaml", over, seed, days))
    return {"part": part, "seed": seed, "cells": cells, "r": r}


def t_aligned(r: dict, cells: int) -> dict:
    sb = np.asarray(r["surv_births_by_day"])
    n = np.asarray(r["n_series"], float)
    first = int(np.flatnonzero(sb > 0)[0]) if (sb > 0).any() else -1
    out: dict = {"t0": first}
    for T, _ in SIBLINGS[cells][0]:
        i = first + T - 1
        out[str(T)] = float(n[i]) if first >= 0 and 0 <= i < n.size else float("nan")
    return out


def main() -> int:
    import history_match as hm

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ensemble", required=True)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--part", default="all", choices=("pen", "siblings", "all"))
    p.add_argument("--label", default="")
    p.add_argument("--pen-seeds", default="9200-9247")
    p.add_argument("--sib-seeds", default="9248-9295")
    a = p.parse_args()
    lo, hi = (int(v) for v in a.pen_seeds.split("-"))
    pen_seeds = tuple(range(lo, hi + 1))
    lo, hi = (int(v) for v in a.sib_seeds.split("-"))
    sb = list(range(lo, hi + 1))
    assert len(pen_seeds) == 48 and len(sb) == 48, "48 pen seeds and 48 sibling seeds"
    sib_seeds = {c: sb[12 * k:12 * (k + 1)] for k, c in enumerate((1, 2, 4, 8))}
    members = json.loads(Path(a.ensemble).read_text(encoding="utf-8"))["members"]
    jobs = []
    if a.part in ("pen", "all"):
        jobs += [("pen", members[i % len(members)]["params"], s, 1600.0, 16)
                 for i, s in enumerate(pen_seeds)]
    if a.part in ("siblings", "all"):
        for cells, seeds in sib_seeds.items():
            jobs += [("sib", members[i % len(members)]["params"], s, 900.0, cells)
                     for i, s in enumerate(seeds)]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(run, jobs))
    print(f"{len(rows)} runs in {time.perf_counter() - t0:.0f} s")
    res: dict = {"ensemble": a.ensemble, "n_members": len(members)}
    pen = [r for r in rows if r["part"] == "pen"]
    if pen:
        outs = [hm.outputs(r["r"]) for r in pen]
        res["pen"] = {}
        print("\nCalhoun's pen, 48 fresh seeds: record vs 5-95 % range")
        n_in = 0
        for name, (z, *_rest) in hm.OUTPUTS.items():
            v = np.array([o[name] for o in outs], float)
            v = v[np.isfinite(v)]
            if not v.size:
                continue
            q = np.quantile(v, [0.05, 0.5, 0.95])
            lo, hi = CONTESTED.get(name, (z, z))
            inside = bool(q[0] <= hi and lo <= q[2])
            n_in += inside
            res["pen"][name] = {"record": z, "p05": float(q[0]), "median": float(q[1]),
                                "p95": float(q[2]), "inside": inside, "n": int(v.size)}
            print(f"  {name:22s} record {z:8.3g}  replica {q[1]:9.4g} [{q[0]:.4g}, {q[2]:.4g}]"
                  f"{'' if inside else '  *'}")
        print(f"  inside: {n_in} of {len(res['pen'])}")
        res["pen_t_aligned"] = [t_aligned(r["r"], 16) for r in pen]
        # per run (M5c): do growth, the phase without surviving young and collapse co-occur?
        res["pen_runs"] = [{"seed": r["seed"], "outputs": o,
                            "maternal_cap_f": {d: v.get("maternal_cap_f")
                                               for d, v in r["r"]["struct"].items()}}
                           for r, o in zip(pen, outs)]
        g = np.array([o["peak_n"] > 1800 for o in outs])
        k = np.array([o["n_at_day_1588"] < 300 for o in outs])
        gp = np.array([o["last_conception_day"] - o["last_young_day"] >= 150 for o in outs])
        print(f"  single runs: peak > 1800 {g.sum()}, collapse (N1588 < 300) {k.sum()}, gap >= "
              f"150 d {gp.sum()}; all three {(g & k & gp).sum()} of {len(outs)}")
    sib = [r for r in rows if r["part"] == "sib"]
    if sib:
        res["siblings"] = {}
        print("\nSibling universes (Calhoun 1971 Fig 3): N at T days after the first surviving "
              "litter, record vs replica median [5-95 %]")
        groups = [(c, [x for x in sib if x["cells"] == c]) for c in SIBLINGS if c < 16]
        if pen:
            groups.append((16, pen))
        for cells, rs in groups:
            ta = [t_aligned(x["r"], cells) for x in rs]
            pts, per_cell = SIBLINGS[cells]
            line = []
            res["siblings"][str(cells)] = {}
            for T, N in pts:
                v = np.array([t[str(T)] for t in ta], float)
                v = v[np.isfinite(v)]
                if not v.size:
                    line.append(f"T{T}: n/a")
                    continue
                q = np.quantile(v, [0.05, 0.5, 0.95])
                inside = bool(q[0] <= N <= q[2])
                res["siblings"][str(cells)][str(T)] = {"record": N, "median": float(q[1]),
                                                      "p05": float(q[0]), "p95": float(q[2]),
                                                      "inside": inside}
                line.append(f"T{T}: {N} vs {q[1]:.0f} [{q[0]:.0f}, {q[2]:.0f}]"
                            f"{'' if inside else ' *'}")
            T_last = pts[-1][0]
            v = np.array([t[str(T_last)] for t in ta], float) / cells
            v = v[np.isfinite(v)]
            if v.size:
                res["siblings"][str(cells)]["per_cell_last"] = {
                    "record": per_cell, "median": float(np.median(v))}
                line.append(f"per cell {per_cell} vs {np.median(v):.0f}")
            t0s = [t["t0"] for t in ta]
            line.append(f"first surviving litter day {np.median(t0s):.0f}")
            print(f"  {cells:2d} cells: " + "; ".join(line))
    path = ROOT / "_output" / (f"replica_validate_{a.label}.json" if a.label
                               else "replica_validate.json")
    path.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"\nwritten {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
