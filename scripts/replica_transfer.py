#!/usr/bin/env python
"""Replica v2 M4: the Marsden transfer (docs/REPLICA_V2.md). Development report, no pass
condition.

For each seed the arm's colony runs to --day. Then 16 females and 8 males are chosen at random
(adults, alive, the females not pregnant) and moved into a fresh 4-cell pen (cells 0-3), with
their traits: age, rank, wounds, lifespan, competence, maternal and courtship capacity. Stress,
drives and boxes start fresh, and there is no box-feeding period. The pen runs --pen-days.

Arm "colony": the 16 females with the colony's 8 males. Arm "stock": the same 16 females with 8
fresh stock males, 100 days old with full competence. Measured: conceptions, litters, and pups
that reached 14 days.

Record (Marsden 1972): with the colony's males, no sex, pregnancy or pups in 60 days. With 8
competent stock males, 6 of 16 females conceived, 3 littered, and 5 pups of about 100 potential
survived to day 14.

usage: python scripts/replica_transfer.py --label m4 [--seeds 7000-7011] [--day 870]
       [--pen-days 60] [--workers 6] [--arm "m4=replica_v2.yaml;key.sub=value"]
Writes _output/replica_transfer_<label>.json.
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
sys.path.insert(0, str(ROOT / "scripts"))

PEN_CELLS = [0, 1, 2, 3]
TRAITS = ("age_days", "rank", "wounds", "lifespan", "competence", "maternal_cap",
          "courtship_cap")


def _deep(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _deep(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _pen(conf: str, over: dict, seed: int, days: float):
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    pen = _deep(over, {"seed": seed, "days": days, "ticks_per_day": 6, "backend": "numpy",
                       "device": "cpu", "log_every_ticks": 10**9, "snapshot_every_days": 0,
                       "initial_pairs": 0,
                       "geometry": {"open_cells": PEN_CELLS, "founder_cells": None,
                                    "box_feeding_until_day": 0.0},
                       "biology": {"removal_n": 0, "removal_day": 0.0}})
    cfg = load_config(ROOT / "configs" / conf, pen)
    return Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25tr_"))), cfg


def _place(sim, k: int, sex: int, role: int) -> int:
    """Spawn one animal in the pen (cells 0-3 in turn) near its cell's ring stand, without a
    box (box choice gives it one at its first stress pass)."""
    slot = int(sim.agents.free_slots(1)[0])
    c = PEN_CELLS[k % len(PEN_CELLS)]
    rx, ry = sim.world.ring_xy[c]
    sim._spawn(slot, sex=sex, age=100.0, x=rx, y=ry, nest_id=-1, cell_id=c, role=role)
    return slot


def run_one(job: tuple[str, str, dict, int, float, float]) -> dict:
    name, conf, over, seed, day, pen_days = job
    from universe25.agents.state import (
        ROLE_BREEDING_FEMALE,
        ROLE_SUBORDINATE_MALE,
        SEX_F,
        SEX_M,
    )
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    base = _deep(over, {"seed": seed, "days": day + 1.0, "ticks_per_day": 6,
                        "backend": "numpy", "device": "cpu", "log_every_ticks": 10**9,
                        "snapshot_every_days": 0})
    cfg = load_config(ROOT / "configs" / conf, base)
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25tr_")))
    a = sim.agents
    for _ in range(int(round(day * 6))):
        sim.step()
    bio = cfg.biology
    adult = a.alive & (a.age_days >= bio.maturity_days)
    fem = np.flatnonzero(adult & (a.sex == SEX_F) & (a.gestating == 0))
    mal = np.flatnonzero(adult & (a.sex == SEX_M))
    rng = np.random.default_rng(np.random.SeedSequence([seed, int(day), 25]))
    out: dict = {"seed": seed, "colony_n": int(a.n_alive), "females_available": int(fem.size),
                 "males_available": int(mal.size)}
    if fem.size < 16 or mal.size < 8:
        out["skipped"] = "too few adults"
        return out
    fsel = rng.choice(fem, 16, replace=False)
    msel = rng.choice(mal, 8, replace=False)
    out["mean_competence_f"] = float(a.competence[fsel].mean())
    out["mean_competence_m"] = float(a.competence[msel].mean())
    out["mean_courtship_m"] = float(a.courtship_cap[msel].mean())
    for arm in ("colony", "stock"):
        pen, pcfg = _pen(conf, over, seed, pen_days)
        pa = pen.agents
        k = 0
        for src in fsel:
            s = _place(pen, k, SEX_F, ROLE_BREEDING_FEMALE)
            for t in TRAITS:
                getattr(pa, t)[s] = getattr(a, t)[src]
            pa.maternal[s] = min(0.8 * float(pa.competence[s]), float(pa.maternal_cap[s]))
            k += 1
        for src in msel:
            s = _place(pen, k, SEX_M, ROLE_SUBORDINATE_MALE)
            if arm == "colony":
                for t in TRAITS:
                    getattr(pa, t)[s] = getattr(a, t)[src]
            k += 1
        pa.n_alive = int(pa.alive.sum())
        n0 = int(pen._next_serial)
        reached14: set[int] = set()
        for _ in range(int(round(pen_days * 6))):
            pen.step()
            pup = pa.alive & (pen._serial >= n0) & (pa.age_days >= 14.0)
            reached14.update(int(v) for v in pen._serial[pup])
        out[arm] = {"conceptions": int(pen._conceptions),
                    "litters": int(np.sum(pen._littered)),
                    "births": int(pen._births), "pups_to_14d": len(reached14),
                    "females_conceived": int(np.sum(pen._mated[pa.sex == SEX_F]))}
    return out


def main() -> int:
    from replica_report import parse_arm

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--label", required=True)
    p.add_argument("--seeds", default="7000-7011")
    p.add_argument("--day", type=float, default=870.0)
    p.add_argument("--pen-days", type=float, default=60.0)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--arm", default="m4=replica_v2.yaml")
    p.add_argument("--members", help="M5 ensemble file: use its first (best) member's params")
    a = p.parse_args()
    lo, hi = (int(v) for v in a.seeds.split("-"))
    name, conf, over = parse_arm(a.arm)
    if a.members:  # the arm's own overrides win (as in replica_report.py; fixed in M8)
        best = json.loads(Path(a.members).read_text(encoding="utf-8"))["members"][0]
        over = _deep(best["params"], over)
    jobs = [(name, conf, over, s, a.day, a.pen_days) for s in range(lo, hi + 1)]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(run_one, jobs))
    print(f"{len(rows)} transfers in {time.perf_counter() - t0:.0f} s (day {a.day:g})")
    done = [r for r in rows if "skipped" not in r]
    print(f"skipped (too few adults): {len(rows) - len(done)}")
    summ: dict = {}
    for arm in ("colony", "stock"):
        summ[arm] = {}
        for k in ("conceptions", "females_conceived", "litters", "pups_to_14d"):
            v = np.array([r[arm][k] for r in done], float)
            if v.size:
                summ[arm][k] = {"median": float(np.median(v)), "min": float(v.min()),
                                "max": float(v.max())}
        print(f"  {arm:7s} " + "  ".join(
            f"{k} {d['median']:.1f} [{d['min']:.0f}, {d['max']:.0f}]"
            for k, d in summ[arm].items()))
    for k in ("mean_competence_f", "mean_competence_m", "mean_courtship_m"):
        v = np.array([r[k] for r in done], float)
        if v.size:
            print(f"  {k}: median {np.median(v):.3f}")
    print("Record: colony males 0 conceptions; stock males 6 of 16 conceived, 3 littered, "
          "5 pups to day 14")
    path = ROOT / "_output" / f"replica_transfer_{a.label}.json"
    path.write_text(json.dumps({"args": vars(a), "rows": rows, "summary": summ}, indent=1,
                               default=float), encoding="utf-8")
    print(f"written {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
