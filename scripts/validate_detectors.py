#!/usr/bin/env python
"""Synthetic validation of the eval-only detectors (P4-5; PHASE4_DESIGN.md section 2).

For every synthetic class (metrics/synthetic_traces.py) it builds M colonies on test seeds
(seed_base + 1000 * class index + colony; development used seeds 100-106, the v1 rules were
tested on seed_base 10_000, v2 on 20_000, v3 on 30_000, v4 on 40_000, v5 on 50_000, v6 on
60_000, v7 on 70_000, the default), runs the detectors for both episode kinds with n
surrogates, and scores each criterion against the class built to violate it:

  criterion                    statistic (higher = more play-like)        target negative
  c1 not fully functional      nf_index_z                                 serious
  c2 spontaneous               onset_trigger_free_z                       triggered
  c3 structurally different    seq_struct_reversal_diff                   serious
  c4 repeated, not rigid       1 - rep_rigid_loop_frac  /  exposure slope rigid_loop / novelty
  c5 relaxed field             gate_relaxed_z                             stressed
  c3 / c4 form beyond chance   seq_struct_form_excess (v6; v7: against   random_walk
                               the even-mix re-simulation), locomotor

Preregistered pass (written before this script was first run on test seeds): AUC >= 0.80 of the
statistic between all_criteria and the target negative, TPR >= 0.80 of the decision flag on
all_criteria colonies, FPR <= 0.10 of the flag on the target negative. NaN statistics count as the
least play-like value; a colony whose kind has too few episodes is flagged False.

usage: python scripts/validate_detectors.py [--colonies 30] [--individuals 30] [--days 20]
       [--surrogates 1000] [--workers 6]
Writes _output/detector_validation.json and prints the tables.
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

AUC_MIN, TPR_MIN, FPR_MAX = 0.80, 0.80, 0.10
SCORES = (  # (criterion flag, statistic key, transform, target negative class)
    ("c1_not_functional", "nf_index_z_unvalidated", 1.0, "serious"),
    ("c2_spontaneous", "onset_trigger_free_z_unvalidated", 1.0, "triggered"),
    ("c3_structurally_different", "seq_struct_reversal_diff_unvalidated", 1.0, "serious"),
    ("c4_repeated_not_rigid", "rep_rigid_loop_frac_unvalidated", -1.0, "rigid_loop"),
    ("c4_repeated_not_rigid", "rep_exposure_slope_unvalidated", 1.0, "novelty"),
    ("c5_relaxed_field", "gate_relaxed_z_unvalidated", 1.0, "stressed"),
    # v4: criterion 2 with 12 sub-steps per decision (onsets on decision boundaries)
    ("c2_spontaneous", "onset_trigger_free_z_unvalidated", 1.0, "triggered_k12",
     "all_criteria_k12"),
    # v5: criterion 2 when individuals move between cells (own entries are not triggers)
    ("c2_spontaneous", "onset_trigger_free_z_unvalidated", 1.0, "triggered_mobile_k12",
     "all_criteria_mobile_k12"),
    # v6: criteria 3 and 4 need a form beyond chance; random_walk has locomotor episodes only
    ("c3_structurally_different", "seq_struct_form_excess_unvalidated", 1.0, "random_walk",
     "all_criteria", ("locomotor",)),
    ("c4_repeated_not_rigid", "seq_struct_form_excess_unvalidated", 1.0, "random_walk",
     "all_criteria", ("locomotor",)),
)
MOBILE = ("all_criteria_mobile_k12", "triggered_mobile_k12")  # also read with v4 (diagnostic)


def _one(args: tuple[str, int, int, int, int, int]) -> dict:
    cls, seed, n_ind, days, n_sur, det_seed = args
    from universe25.metrics.detectors import detect_trace
    from universe25.metrics.synthetic_traces import make_colony

    tr = make_colony(cls, n_individuals=n_ind, days=days, seed=seed)
    res = detect_trace(tr, n_surrogates=n_sur, seed=det_seed)
    v4 = (detect_trace(tr, n_surrogates=n_sur, seed=det_seed, self_entries=True)
          if cls in MOBILE else None)
    return {"class": cls, "seed": seed, "result": res, "v4": v4}


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC; NaN replaced by -inf (least play-like)."""
    pos = np.where(np.isfinite(pos), pos, -np.inf)
    neg = np.where(np.isfinite(neg), neg, -np.inf)
    gt = (pos[:, None] > neg[None, :]).mean()
    eq = (pos[:, None] == neg[None, :]).mean()
    return float(gt + 0.5 * eq)


def main() -> int:
    from universe25.metrics.synthetic_traces import CLASSES, SUBSTEP_CLASSES

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--colonies", type=int, default=30)
    p.add_argument("--individuals", type=int, default=30)
    p.add_argument("--days", type=int, default=20)
    p.add_argument("--surrogates", type=int, default=1000)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--seed-base", type=int, default=70_000)
    p.add_argument("--out", type=str, default=str(ROOT / "_output" / "detector_validation.json"))
    a = p.parse_args()
    all_classes = tuple(CLASSES) + tuple(SUBSTEP_CLASSES)
    jobs = [(c, a.seed_base + 1000 * i + m, a.individuals, a.days, a.surrogates, 7 + m)
            for i, c in enumerate(all_classes) for m in range(a.colonies)]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(_one, jobs, chunksize=4))
    print(f"{len(results)} colonies in {time.perf_counter() - t0:.0f} s "
          f"({a.surrogates} surrogates per statistic)")
    by: dict[str, list[dict]] = {c: [r["result"] for r in results if r["class"] == c]
                                 for c in all_classes}
    report: dict = {"config": vars(a), "criteria": {}, "flag_rates": {},
                    "thresholds": {"auc_min": AUC_MIN, "tpr_min": TPR_MIN, "fpr_max": FPR_MAX}}
    all_pass = True
    for kind in ("object", "locomotor"):
        print(f"\n== {kind} episodes: preregistered scoring (all_criteria vs target negative)")
        print(f"{'criterion':28s} {'statistic':38s} {'negative':11s} {'AUC':>6s} {'TPR':>6s} "
              f"{'FPR':>6s}  pass")
        rows = []
        for flag, key, sign, neg, *extra in SCORES:
            pc = extra[0] if extra else "all_criteria"
            if len(extra) > 1 and kind not in extra[1]:
                continue
            pos_v = np.array([r[kind].get(key, np.nan) for r in by[pc]], float) * sign
            neg_v = np.array([r[kind].get(key, np.nan) for r in by[neg]], float) * sign
            pos_r = by[pc]
            tpr = float(np.mean([r[kind]["decisions_unvalidated"][flag] for r in pos_r]))
            fpr = float(np.mean([r[kind]["decisions_unvalidated"][flag] for r in by[neg]]))
            au = auc(pos_v, neg_v)
            ok = au >= AUC_MIN and tpr >= TPR_MIN and fpr <= FPR_MAX
            all_pass &= ok
            rows.append({"criterion": flag, "statistic": key, "negative": neg,
                         "positive": pc, "auc": au,
                         "tpr": tpr, "fpr": fpr, "pass": ok})
            print(f"{flag:28s} {key:38s} {neg:11s} {au:6.3f} {tpr:6.2f} {fpr:6.2f}  "
                  f"{'PASS' if ok else 'FAIL'}")
        report["criteria"][kind] = rows
        flags = list(by["all_criteria"][0][kind]["decisions_unvalidated"])
        print(f"\nflag rate per class ({kind}): " + " ".join(f"{f[:3]:>5s}" for f in flags)
              + "   all five")
        rates = {}
        for c in all_classes:
            fr = [float(np.mean([r[kind]["decisions_unvalidated"][f] for r in by[c]]))
                  for f in flags]
            five = float(np.mean([all(r[kind]["decisions_unvalidated"].values()) for r in by[c]]))
            eps = float(np.mean([r[kind]["n_episodes"] for r in by[c]]))
            rates[c] = {"flags": dict(zip(flags, fr)), "all_five": five, "mean_episodes": eps}
            print(f"  {c:12s} " + " ".join(f"{v:5.2f}" for v in fr) + f"   {five:5.2f}"
                  f"   (episodes {eps:.0f})")
        report["flag_rates"][kind] = rates
    print("\ndiagnostic (not a pass criterion): criterion 2 with the v4 trigger set (own cell"
          " entries count) on the mobile classes")
    report["v4_diagnostic"] = {}
    for kind in ("object", "locomotor"):
        v4p = [r["v4"][kind] for r in results if r["class"] == MOBILE[0]]
        v4n = [r["v4"][kind] for r in results if r["class"] == MOBILE[1]]
        key = "onset_trigger_free_z_unvalidated"
        tpr = float(np.mean([r["decisions_unvalidated"]["c2_spontaneous"] for r in v4p]))
        fpr = float(np.mean([r["decisions_unvalidated"]["c2_spontaneous"] for r in v4n]))
        au = auc(np.array([r.get(key, np.nan) for r in v4p], float),
                 np.array([r.get(key, np.nan) for r in v4n], float))
        report["v4_diagnostic"][kind] = {"auc": au, "tpr": tpr, "fpr": fpr}
        print(f"  {kind:9s} v4: AUC {au:.3f}  spontaneous on {MOBILE[0]} {tpr:.2f}, "
              f"on {MOBILE[1]} {fpr:.2f}")
    report["all_pass"] = bool(all_pass)
    print(f"\npreregistered validation: {'ALL PASS' if all_pass else 'NOT ALL PASS'}")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=float), encoding="utf-8")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
