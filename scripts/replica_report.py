#!/usr/bin/env python
"""Replica v2 milestone report (docs/REPLICA_V2.md): one or more scenarios on the same seeds,
the record landmarks (median and 90 % range over seeds, and the record's rank), and structural
numbers at days 315 / 560 / 736. Development report: training seeds by default, no pass
condition.

usage: python scripts/replica_report.py --label m1 [--seeds 7000-7011] [--days 1600]
       [--workers 6] [--arms frozen_grid=default.yaml replica=replica_v2.yaml ...]
Each arm is name=config (in configs/) with optional ;key.sub=value overrides, e.g.
"grid_nopg=default.yaml;playground.enabled=false". Writes _output/replica_report_<label>.json.

Structural numbers per snapshot day:
  empty_box_share     share of the 256 boxes with no living occupant (Calhoun: ~20 % at 2200)
  centre_share        share of weaned animals within 12 in of the pen centre
  withdrawn_centre    share of withdrawn animals within 12 in of the centre
  male_share          males among weaned animals (Calhoun: 40 % in phase B)
  max_cell_share      the largest cell's share of the weaned animals (aggregation)
  owned_cells         cells with a territory owner (biology.territories; M2)
  excluded_centre     share of adult, non-withdrawn, non-owner males within 12 in of the centre
  hopper_max_share    the busiest cell's share of the animals foraging this decision
  owner_ring_dist     owners' mean distance (in) from their cell's ring stand
  subs_per_owner      adult, non-withdrawn, non-owner males per owner (Calhoun: 3)
  beautiful_share     share of 131-320-day-olds who never fought or mated (M4; Calhoun: 53 % of
                      those entering adulthood in mid-phase D)
  withdrawn_fought    share of withdrawn adults who ever fought (Calhoun's withdrawn males were
                      wounded; his "beautiful ones" never fought)
Territory numbers per run (M2, biology.territories on):
  brood groups        sires (owners) of the young born by day 338, their count and the young
                      per group (Calhoun 1971: 842 young in 14 groups, 111 ... 13)
  founder_male_deaths founding males dead by day 60 (Calhoun: 2 of 4 within two months)
  contests_315, takeovers_315
An override value of null sets None (e.g. biology.founder_age_days=null).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SNAP_DAYS = (315, 560, 736, 800, 1444)
DEFAULT_ARMS = ("frozen_grid=default.yaml", "grid_nopg=default.yaml;playground.enabled=false",
                "replica=replica_v2.yaml")


def parse_arm(spec: str) -> tuple[str, str, dict]:
    name, rest = spec.split("=", 1)
    parts = rest.split(";")
    over: dict = {}
    for kv in parts[1:]:
        key, val = kv.split("=", 1)
        lit = {"true": True, "false": False, "null": None}
        v: object = lit.get(val.lower(), lit)
        if v is lit:
            try:
                v = float(val)
            except ValueError:
                v = val
        d = over
        keys = key.split(".")
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = v
    return name, parts[0], over


def run_one(job: tuple[str, str, dict, int, float]) -> tuple[str, int, dict]:
    name, conf, over, seed, days = job
    from universe25.config import load_config
    from universe25.metrics.calibration import landmarks_from_series
    from universe25.sim import Universe25Sim
    from universe25.agents.state import ACT_FORAGE, ROLE_WITHDRAWN, SEX_M

    base = dict(seed=seed, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=10**9, snapshot_every_days=0)
    merged = {**base, **over}
    cfg = load_config(ROOT / "configs" / conf, merged)
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25rr_")))
    bio = cfg.biology
    a = sim.agents
    hist = {k: [] for k in ("day", "n", "births", "young", "adult", "conc")}
    struct: dict[str, dict] = {}
    cx, cy = sim.world.width / 2, sim.world.height / 2
    f_m = np.flatnonzero(a.alive & (a.sex == SEX_M))
    f_m_serial = sim._serial[f_m].copy()
    terr: dict = {}
    for _ in range(int(days * 6)):
        sim.step()
        if sim.tick % 6 == 0:
            hist["day"].append(sim.day)
            hist["n"].append(a.n_alive)
            hist["births"].append(sim._births)
            hist["young"].append(sim._last_surviving_young_day)
            hist["adult"].append(int(np.sum(a.alive & (a.age_days >= bio.maturity_days))))
            hist["conc"].append(sim._last_conception_day)
            d = int(round(sim.day))
            if d == 60:
                terr["founder_male_deaths"] = int(np.sum(~a.alive[f_m]
                                                         | (sim._serial[f_m] != f_m_serial)))
            if d == 315:
                terr["contests_315"] = sim._contests
                terr["takeovers_315"] = sim._takeovers
            if d in SNAP_DAYS:
                al = a.alive
                weaned = al & (a.age_days >= bio.weaning_days)
                occ = np.bincount(a.nest_id[al & (a.nest_id >= 0)].astype(int),
                                  minlength=sim.world.n_nests)
                near = np.hypot(a.x - cx, a.y - cy) < 12.0
                wd = al & (a.role == ROLE_WITHDRAWN)
                cells = np.bincount(a.cell_id[weaned].astype(int), minlength=sim.world.n_cells)
                struct[str(d)] = {
                    "n": int(al.sum()),
                    "empty_box_share": float(np.mean(occ == 0)),
                    "centre_share": float(near[weaned].mean()) if weaned.any() else np.nan,
                    "withdrawn_centre": float(near[wd].mean()) if wd.any() else np.nan,
                    "withdrawn_share": float(wd[weaned].mean()) if weaned.any() else np.nan,
                    "male_share": float((a.sex[weaned] == SEX_M).mean()) if weaned.any()
                    else np.nan,
                    "max_cell_share": float(cells.max() / max(1, cells.sum())),
                    "owned_cells": float((sim._owner >= 0).sum()) if bio.territories
                    else np.nan,
                }
                cat = al & (a.age_days >= 131.0) & (a.age_days <= 320.0)
                wad = wd & (a.age_days >= bio.maturity_days)
                struct[str(d)]["beautiful_share"] = (
                    float(np.mean(~sim._fought[cat] & ~sim._mated[cat])) if cat.any() else np.nan)
                struct[str(d)]["withdrawn_fought"] = (float(np.mean(sim._fought[wad]))
                                                      if wad.any() else np.nan)
                fo = al & (a.last_action == ACT_FORAGE)
                fc = np.bincount(a.cell_id[fo].astype(int), minlength=sim.world.n_cells)
                struct[str(d)]["hopper_max_share"] = (float(fc.max() / fc.sum()) if fc.sum()
                                                      else np.nan)
                if bio.territories:
                    own = sim._owner_mask()
                    oi = np.flatnonzero(own)
                    adm = (al & (a.sex == SEX_M) & (a.age_days >= bio.maturity_days)
                           & (a.role != ROLE_WITHDRAWN) & ~own)
                    ring = np.array(sim.world.ring_xy) if sim.world.ring_xy else None
                    struct[str(d)].update({
                        "excluded_centre": float(near[adm].mean()) if adm.any() else np.nan,
                        "subs_per_owner": float(adm.sum() / max(1, oi.size)),
                        "owner_ring_dist": (float(np.mean(np.hypot(
                            a.x[oi] - ring[a.cell_id[oi], 0], a.y[oi] - ring[a.cell_id[oi], 1])))
                            if ring is not None and oi.size else np.nan),
                    })
        if a.n_alive == 0 and sim.day > 50:
            break
    lm = landmarks_from_series(*(np.asarray(hist[k], float) for k in ("day", "n", "births",
                                                                       "young")),
                               n_adult=np.asarray(hist["adult"], float),
                               last_conception=np.asarray(hist["conc"], float),
                               surv_births_by_day=sim._surv_births_by_day,
                               conceptions_by_day=sim._conc_by_day)
    if bio.territories:
        for lim in (315, 338):
            groups: dict[int, int] = {}
            for day, sire, n_pups in sim._litter_log:
                if day <= float(lim):
                    groups[sire] = groups.get(sire, 0) + n_pups
            terr[f"brood_sizes_{lim}"] = sorted(groups.values(), reverse=True)
    return name, seed, {"landmarks": {k: float(v) for k, v in lm.items()}, "struct": struct,
                        "territory": terr, "n_series": [int(v) for v in hist["n"]],
                        "surv_births_by_day": [int(v) for v in sim._surv_births_by_day]}


def main() -> int:
    from universe25.metrics.calibration import EXTRA_LANDMARKS, LANDMARKS, RECORD_LANDMARKS

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--label", required=True)
    p.add_argument("--seeds", default="7000-7011")
    p.add_argument("--days", type=float, default=1600.0)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--arms", nargs="+", default=list(DEFAULT_ARMS))
    a = p.parse_args()
    lo, hi = (int(v) for v in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    arms = [parse_arm(s) for s in a.arms]
    jobs = [(n, c, o, s, a.days) for n, c, o in arms for s in seeds]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(run_one, jobs))
    print(f"{len(rows)} runs in {time.perf_counter() - t0:.0f} s ({len(seeds)} seeds)")
    names = [n for n, _, _ in arms]
    record = {**LANDMARKS, **EXTRA_LANDMARKS, **RECORD_LANDMARKS}
    out: dict = {"seeds": seeds, "days": a.days, "arms": a.arms, "landmarks": {}, "struct": {},
                 "rows": rows}
    print("\n| landmark | Calhoun | " + " | ".join(f"{n} median [5-95 %]" for n in names) + " |")
    print("|---|---:|" + "---|" * len(names))
    for k, tgt in record.items():
        cells = []
        out["landmarks"][k] = {"record": tgt}
        for n in names:
            v = np.array([r["landmarks"].get(k, np.nan) for nn, _, r in rows if nn == n], float)
            v = v[np.isfinite(v)]
            if v.size == 0:
                cells.append("n/a")
                continue
            q = np.quantile(v, [0.05, 0.5, 0.95])
            inside = q[0] <= tgt <= q[2]
            out["landmarks"][k][n] = {"median": float(q[1]), "p05": float(q[0]),
                                      "p95": float(q[2]), "inside": bool(inside)}
            cells.append(f"{q[1]:.1f} [{q[0]:.1f}, {q[2]:.1f}]{'' if inside else ' *'}")
        print(f"| {k} | {tgt:g} | " + " | ".join(cells) + " |")
    print("\n(* = the record lies outside the 5-95 % range over seeds)")
    keys = ("n", "empty_box_share", "centre_share", "withdrawn_share", "withdrawn_centre",
            "male_share", "max_cell_share", "owned_cells", "excluded_centre",
            "hopper_max_share", "owner_ring_dist", "subs_per_owner", "beautiful_share",
            "withdrawn_fought")
    for d in SNAP_DAYS:
        print(f"\nday {d}: " + " | ".join(names))
        out["struct"][str(d)] = {}
        for k in keys:
            vals = []
            for n in names:
                v = np.array([r["struct"].get(str(d), {}).get(k, np.nan) for nn, _, r in rows
                              if nn == n], float)
                m = float(np.nanmedian(v)) if np.isfinite(v).any() else float("nan")
                out["struct"][str(d)].setdefault(k, {})[n] = m
                vals.append(f"{m:.3f}" if k != "n" else f"{m:.0f}")
            print(f"  {k:18s} " + "  ".join(f"{v:>9s}" for v in vals))
    out["territory"] = {}
    for n in names:
        tr = [r.get("territory", {}) for nn, _, r in rows if nn == n]
        if not any("brood_sizes_338" in t for t in tr):
            continue
        ng = np.array([len(t["brood_sizes_338"]) for t in tr], float)
        ng315 = np.array([len(t.get("brood_sizes_315", [])) for t in tr], float)
        young = np.array([sum(t["brood_sizes_338"]) for t in tr], float)
        top = np.array([t["brood_sizes_338"][0] if t["brood_sizes_338"] else 0 for t in tr],
                       float)
        g14 = np.array([sum(t["brood_sizes_338"][:14]) / max(1, sum(t["brood_sizes_338"]))
                        for t in tr], float)
        fd = np.array([t.get("founder_male_deaths", np.nan) for t in tr], float)
        ct = np.array([t.get("contests_315", np.nan) for t in tr], float)
        tk = np.array([t.get("takeovers_315", np.nan) for t in tr], float)
        summ = {"brood_groups_315": ng315, "brood_groups_338": ng, "young_by_338": young,
                "largest_group_338": top,
                "share_in_top14_groups": g14, "founder_male_deaths_60": fd,
                "contests_315": ct, "takeovers_315": tk}
        out["territory"][n] = {k: {"median": float(np.nanmedian(v)),
                                   "p05": float(np.nanquantile(v, 0.05)),
                                   "p95": float(np.nanquantile(v, 0.95))}
                               for k, v in summ.items()}
        print(f"\nterritories ({n}); Calhoun: 14 groups, 842 young by day 338, largest 111, "
              "2 of 4 founding males dead within two months")
        for k, v in out["territory"][n].items():
            print(f"  {k:24s} {v['median']:8.2f} [{v['p05']:.2f}, {v['p95']:.2f}]")
    path = ROOT / "_output" / f"replica_report_{a.label}.json"
    path.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwritten {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
