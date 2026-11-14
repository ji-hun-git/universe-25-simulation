#!/usr/bin/env python
"""Pre-evolution of SCARCE-PG evo (PHASE4_DESIGN.md 4.6, fixed 2026-11-14 before any code or
run): 8 scarce lineages, one per worker.

Scarce lineage l starts from the 16 generation-0 genomes of H-h's lineage l
(_output/evo/lineage_l/pool_gen0.npz, in slot order) and runs H-h's founding epochs (8 pairs,
360 d, 6 ticks/day, NumPy, 12 sub-steps, sim seeds cycling over 7000-7009) with food for 100
animals: the capacity rule of configs/scarce.yaml at scarce_capacity_animals 100. Its founder
draws come from SeedSequence([7000 + l - 1, 7_700_001]) and its policy streams carry the key
(l, epoch, 2). It stops after the first epoch whose day-360 adults reach a mean pedigree depth of
G_l, the depth H-h's lineage l reached (its neutral generations), at most 400 epochs. No neutral
pool is built: H-h's controls drift for both lines. Every epoch records the read-only hunger
probes. Resumable at every epoch; a lineage with a summary.json is done and skipped.
Writes _output/evo_scarce/lineage_<l>/ (see learn/evolution.py).

--regime small runs small-meal evo instead (PHASE4_DESIGN.md 4.7, fixed 2026-11-15 before any
code or run): unlimited food, but a meal relieves at most 0.375 of hunger (resources.meal_cap);
founder draws from SeedSequence([7000 + l - 1, 7_800_001]) and policy streams keyed (l, epoch,
3); everything else as above. Writes _output/evo_small/lineage_<l>/.

usage: python scripts/evolve_scarce.py [--regime scarce|small] [--lineages 1-8] [--epochs 400]
           [--workers 8]
       python scripts/evolve_scarce.py --dev --lineages 1 --epochs 3 --out _output/evo_scarce_dev
--dev fixes every epoch's simulation seed to the training seed 7000 (the harness smoke, for
timing only; no statistic of it is read).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.evo import (  # noqa: E402
    SCARCE_KEY,
    SCARCE_LINEAGE_STREAM,
    SMALL_KEY,
    SMALL_LINEAGE_STREAM,
)

EVO = ROOT / "_output" / "evo"
OUT = ROOT / "_output" / "evo_scarce"
CAPACITY = 100.0  # animals' worth of food per day (PHASE4_DESIGN.md 4.6)
MEAL_CAP = 0.375  # the most hunger one meal relieves (PHASE4_DESIGN.md 4.7)
MAX_EPOCHS = 400
MAX_ENDED = 2  # stop rule: more lineages ending than this
SCARCE_FOOD = {"resources": {"mode": "scarce", "scarce_supply": "capacity",
                             "scarce_capacity_animals": CAPACITY}}
SMALL_MEALS = {"resources": {"meal_cap": MEAL_CAP}}
# regime: (epoch overrides, extra policy key, lineage stream, default output folder)
REGIMES = {
    "scarce": (SCARCE_FOOD, SCARCE_KEY, SCARCE_LINEAGE_STREAM, OUT),
    "small": (SMALL_MEALS, SMALL_KEY, SMALL_LINEAGE_STREAM, ROOT / "_output" / "evo_small"),
}


def target_depth(evo: Path, lineage: int) -> int:
    """G_l: the depth H-h's lineage l reached (the generations of its neutral pool)."""
    s = json.loads((evo / f"lineage_{lineage}" / "summary.json").read_text(encoding="utf-8"))
    return int(s["neutral_generations"])


def _job(args: tuple[int, str, str, int, int | None, str]) -> dict:
    lineage, out, evo, epochs, sim_seed, regime = args
    from universe25.learn.evolution import evolve_lineage

    overrides, key, lineage_stream, _ = REGIMES[regime]

    summ_f = Path(out) / f"lineage_{lineage}" / "summary.json"
    if summ_f.exists():
        return {**json.loads(summ_f.read_text(encoding="utf-8")), "kept": True}
    g = target_depth(Path(evo), lineage)

    def progress(st: dict) -> None:
        if st["epoch"] % 10 == 0:
            p = st.get("probe", {})
            print(f"lineage {lineage} epoch {st['epoch']}: N {st['n_end']}, weaned "
                  f"{p.get('weaned_end')}, adults {st['adults_f']} F / {st['adults_m']} M, depth "
                  f"{st['adult_depth_mean']:.1f} of {g}, hungry {p.get('hungry_share_2h')}, "
                  f"starving {p.get('starving_share_2h')}, thirst-starving "
                  f"{p.get('thirst_starving_share_2h')}, {st['wall_s']:.0f} s", flush=True)

    return evolve_lineage(lineage, Path(out), epochs=epochs, sim_seed=sim_seed,
                          progress=progress, overrides=overrides, key_extra=(key,),
                          lineage_stream=lineage_stream,
                          gen0_pool=Path(evo) / f"lineage_{lineage}" / "pool_gen0.npz",
                          stop_depth=float(g), neutral=False, probe=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lineages", default="1-8")
    p.add_argument("--epochs", type=int, default=MAX_EPOCHS)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--evo", default=str(EVO))
    p.add_argument("--out", default=None, help="default: by regime")
    p.add_argument("--regime", choices=sorted(REGIMES), default="scarce")
    p.add_argument("--dev", action="store_true")
    a = p.parse_args()
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))
    sim_seed = 7000 if a.dev else None
    out = a.out or str(REGIMES[a.regime][3])
    t0 = time.perf_counter()
    jobs = [(lin, out, a.evo, a.epochs, sim_seed, a.regime) for lin in lineages]
    failed, ended, short = [], [], []
    with ProcessPoolExecutor(max_workers=min(a.workers, len(jobs))) as ex:
        futs = {ex.submit(_job, j): j[0] for j in jobs}
        for f in as_completed(futs):
            lin = futs[f]
            try:
                s = f.result()
            except Exception as e:  # report and keep the other lineages running
                failed.append(lin)
                print(f"lineage {lin} FAILED: {type(e).__name__}: {e}", flush=True)
                continue
            if s.get("ended"):
                ended.append(lin)
            elif not s.get("depth_reached"):
                short.append(lin)
            print(f"lineage {lin} done: {json.dumps(s)}", flush=True)
    stops = []
    if len(ended) > MAX_ENDED:
        stops.append(f"{len(ended)} lineages ended ({ended})")
    if short and not a.dev:
        stops.append(f"lineages {short} reached {a.epochs} epochs short of their depth")
    for s in stops:
        print(f"STOP: {s}", flush=True)
    state = "stopped" if stops else (f"failed ({failed})" if failed else "done")
    print(f"evolve_scarce ({a.regime}) {state}: {len(jobs) - len(failed)} of {len(jobs)} "
          f"lineages in {time.perf_counter() - t0:.0f} s", flush=True)
    return 1 if failed or stops else 0


if __name__ == "__main__":
    raise SystemExit(main())
