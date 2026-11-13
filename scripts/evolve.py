#!/usr/bin/env python
"""Pre-evolution of the inherited-weight policy `evo` (PHASE4_DESIGN.md 4.4, fixed 2026-11-13
before any code or run): 8 lineages x 150 serial founding epochs (8 pairs, 360 d, ABUND-PG,
training seeds 7000-7009), one lineage per worker, then each lineage's neutral control.
Resumable at every epoch. Writes _output/evo/lineage_<l>/ (see learn/evolution.py).

usage: python scripts/evolve.py [--lineages 1-8] [--epochs 150] [--workers 8] [--out _output/evo]
       python scripts/evolve.py --dev --lineages 1 --epochs 3 --out _output/evo_dev
--dev fixes every epoch's simulation seed to the training seed 7000 (the harness smoke; no
statistic of it is read).
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


def _job(args: tuple[int, str, int, int | None]) -> dict:
    lineage, out, epochs, sim_seed = args
    from universe25.learn.evolution import evolve_lineage

    def progress(st: dict) -> None:
        if st["epoch"] % 10 == 0 or st["epoch"] == epochs - 1:
            print(f"lineage {lineage} epoch {st['epoch']}: N {st['n_end']} (peak "
                  f"{st['peak_n']}), adults {st['adults_f']} F / {st['adults_m']} M, depth "
                  f"{st['adult_depth_mean']:.1f}, {st['wall_s']:.0f} s", flush=True)

    return evolve_lineage(lineage, Path(out), epochs=epochs, sim_seed=sim_seed,
                          progress=progress)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lineages", default="1-8")
    p.add_argument("--epochs", type=int, default=150)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", default=str(ROOT / "_output" / "evo"))
    p.add_argument("--dev", action="store_true")
    a = p.parse_args()
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))
    sim_seed = 7000 if a.dev else None
    t0 = time.perf_counter()
    jobs = [(lin, a.out, a.epochs, sim_seed) for lin in lineages]
    failed = []
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
            print(f"lineage {lin} done: {json.dumps(s)}", flush=True)
    print(f"evolve: {len(jobs) - len(failed)} of {len(jobs)} lineages in "
          f"{time.perf_counter() - t0:.0f} s", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
