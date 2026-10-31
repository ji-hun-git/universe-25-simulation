#!/usr/bin/env python
"""Plateau / resolution check: peak N, 31-day-mean peak and its day, raw-maximum day, first-97 %
day, N@736 and the surviving-birth cessation for several seeds at 6 vs 24 ticks/day.

usage: python scripts/multiseed_peak.py <n_seeds> <tpds> <workers> [days=800] [fragment.yaml]
e.g.   python scripts/multiseed_peak.py 12 6,24 12 800
Fragment ({biology: {...}, drives: {...}}) is merged over configs/default.yaml. NumPy CPU path.
"""
from __future__ import annotations

import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _run(args: tuple[int, int, float, str]) -> tuple[int, int, dict[str, float]]:
    seed, tpd, days, frag = args
    import numpy as np
    import yaml

    from universe25.config import load_config
    from universe25.metrics.calibration import (
        PEAK_FRACTION,
        PEAK_WINDOW_DAYS,
        surviving_birth_cessation_day,
    )
    from universe25.sim import Universe25Sim

    ov = dict(yaml.safe_load(Path(frag).read_text(encoding="utf-8")) or {}) if frag else {}
    ov.update(dict(seed=seed, days=days, ticks_per_day=tpd, backend="numpy", device="cpu",
                   log_every_ticks=10**9, snapshot_every_days=0))
    cfg = load_config(ROOT / "configs" / "default.yaml", ov)
    sim = Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix="u25mp_")))
    ns, days_l = [], []
    for _ in range(int(days * tpd)):
        sim.step()
        if sim.tick % tpd == 0:
            ns.append(sim.agents.n_alive)
            days_l.append(sim.day)
    n = np.array(ns, float)
    d = np.array(days_l)
    w = PEAK_WINDOW_DAYS
    sm = np.convolve(n, np.ones(w) / w, mode="valid")
    return seed, tpd, dict(
        n400=float(n[int(np.argmin(np.abs(d - 400)))]),
        peak=float(n.max()),
        peak_day_97=float(d[int(np.argmax(n >= PEAK_FRACTION * n.max()))]),
        p31=float(sm.max()),
        p31_day=float(d[int(np.argmax(sm)) + w // 2]),
        raw_day=float(d[int(np.argmax(n))]),
        n736=float(n[int(np.argmin(np.abs(d - 736)))]),
        cess=float(surviving_birth_cessation_day(sim._surv_births_by_day)),
    )


def main() -> int:
    import numpy as np

    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    tpds = [int(t) for t in sys.argv[2].split(",")] if len(sys.argv) > 2 else [6, 24]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    days = float(sys.argv[4]) if len(sys.argv) > 4 else 800.0
    frag = sys.argv[5] if len(sys.argv) > 5 else ""
    seeds = [7000 + i for i in range(n_seeds)]
    jobs = [(s, t, days, frag) for t in sorted(tpds, reverse=True) for s in seeds]
    res: dict[tuple[int, int], dict[str, float]] = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for seed, tpd, out in ex.map(_run, jobs):
            res[(seed, tpd)] = out
            print(f"seed={seed} tpd={tpd:2d} N400={out['n400']:.0f} peak={out['peak']:.0f} "
                  f"p31={out['p31']:.0f} @ {out['p31_day']:.0f} rawday={out['raw_day']:.0f} "
                  f"day97={out['peak_day_97']:.0f} N736={out['n736']:.0f} cess={out['cess']:.0f}",
                  flush=True)
    labels = (("n400", "N@400"), ("peak", "peak N"), ("p31", "31-d mean peak"),
              ("peak_day_97", "peak day (97 %)"), ("p31_day", "31-d mean peak day"),
              ("raw_day", "raw max day"), ("n736", "N@736"), ("cess", "surviving births cease"))
    for key, lab in labels:
        parts = []
        for tpd in sorted(tpds):
            v = np.array([res[(s, tpd)][key] for s in seeds], float)
            se = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
            parts.append(f"tpd={tpd:2d}: {v.mean():7.1f} ± {se:5.1f} (sd {v.std(ddof=1):6.1f})")
        if len(tpds) == 2:
            lo, hi = sorted(tpds)
            diff = np.array([res[(s, hi)][key] - res[(s, lo)][key] for s in seeds], float)
            se = diff.std(ddof=1) / np.sqrt(len(diff)) if len(diff) > 1 else 0.0
            parts.append(f"paired diff (hi-lo): {diff.mean():+7.1f} ± {se:5.1f}")
        print(f"{lab:24s} " + " | ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
