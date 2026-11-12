#!/usr/bin/env python
"""H-g and the playground-off arm: the preregistered decision and the tables reported beside it
(PHASE4_DESIGN.md section 4.3, fixed 2026-11-13 before any run).

Reads <sweep>/<policy>_<arm>_<seed>/hg_run.json (scripts/sweep_hg.py); writes
<sweep>/hg_analysis.json and prints the tables. Decisive: the six playground-on cells (policy x
kind) and H-g over them. Preregistered, not decisive: the playground-off checks (object events
vanish, locomotor episodes persist), H-g's rule for locomotion with the playground off, the
colony's landmarks. Reported beside: detector vectors by phase, state shares by phase, rates by
days since the peak, late minus early phase D, and the playground contrast.

usage: python scripts/analyse_hg.py [--sweep _output/hg_sweep] [--seeds 9877-9888]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.metrics.phase_rates import (  # noqa: E402
    N_CELLS,
    cell_decision,
    overall,
    run_taus,
    sign_flip,
)

POLICIES = ("learned", "need_driven", "random")
ARMS = ("pg_on", "pg_off")
KINDS = ("object", "locomotor")
PHASES = ("B", "C", "D")
LABELS = ("B", "C", "D_early", "D_late")
LANDMARKS = ("first_litters_day", "n_at_day_315", "peak_n", "peak_day", "last_young_day",
             "last_conception_day", "n_at_day_1444", "n_at_day_1588")
BESIDE = ("n_alive", "n_weaned_individuals", "relaxed_share_weaned", "stressed_share_weaned",
          "withdrawn_share_weaned", "juvenile_share_weaned")
KIND_BESIDE = ("rate", "rate_eligible", "event_share_weaned", "threshold")
FLAGS = ("c1_not_functional", "c2_spontaneous", "c3_structurally_different",
         "c4_repeated_not_rigid", "c5_relaxed_field")
SHAPE_BINS = np.arange(-400.0, 1101.0, 100.0)


def mse(v: Any) -> dict[str, float]:
    a = np.asarray(v, dtype=np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0, "mean": float("nan"), "se": float("nan")}
    se = float(a.std(ddof=1) / np.sqrt(a.size)) if a.size > 1 else float("nan")
    return {"n": int(a.size), "mean": float(a.mean()), "se": se}


def two_sided(v: Any) -> dict[str, Any]:
    r = sign_flip(v)
    r["p_two_sided"] = float(min(1.0, 2.0 * min(r["p_rise"], r["p_fall"]))) if r["n"] else \
        float("nan")
    return r


def load(sweep: Path, seeds: list[int]) -> tuple[dict, list[str]]:
    runs: dict[tuple[str, str], list[dict]] = {}
    missing: list[str] = []
    for pol in POLICIES:
        for arm in ARMS:
            lst = []
            for s in seeds:
                f = sweep / f"{pol}_{arm}_{s}" / "hg_run.json"
                if f.exists():
                    lst.append(json.loads(f.read_text(encoding="utf-8")))
                else:
                    missing.append(f.parent.name)
            runs[(pol, arm)] = lst
    return runs, missing


def cells_for(runs: list[dict], kind: str) -> dict[str, Any]:
    taus = [run_taus(r["windows"], kind) for r in runs]
    dec = cell_decision([t["tau_bcd"] for t in taus], [t["tau_d"] for t in taus],
                        n_cells=N_CELLS)
    dec["per_seed"] = {str(r["seed"]): t for r, t in zip(runs, taus)}
    return dec


def phase_means(run: dict, get) -> dict[str, float]:
    out = {}
    for ph in PHASES:
        v = [get(w) for w in run["windows"] if w["entered"] and w["phase"] == ph]
        v = [x for x in v if x is not None and np.isfinite(x)]
        out[ph] = float(np.mean(v)) if v else float("nan")
    return out


def rate_at(run: dict, mid: float | None, kind: str) -> float:
    if mid is None:
        return float("nan")
    for w in run["windows"]:
        if abs(float(w["mid"]) - float(mid)) < 1e-9:
            return float(w[kind]["rate"])
    return float("nan")


def fmt_t(c: dict) -> str:
    return f"{c['mean']:+.3f} ± {c['se']:.3f}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", type=str, default=str(ROOT / "_output" / "hg_sweep"))
    p.add_argument("--seeds", type=str, default="9877-9888")
    a = p.parse_args()
    lo, _, hi = a.seeds.partition("-")
    seeds = list(range(int(lo), int(hi or lo) + 1))
    sweep = Path(a.sweep)
    runs, missing = load(sweep, seeds)
    out: dict[str, Any] = {"sweep": str(sweep), "seeds": seeds, "missing": missing}
    if missing:
        print(f"missing runs ({len(missing)}): {', '.join(missing[:12])} ...")
    stops = [s for lst in runs.values() for r in lst for s in r.get("stop", [])]
    out["stops"] = stops
    if stops:
        print("STOP conditions: " + "; ".join(stops))

    # --- the decision (playground on) ---
    print("\nH-g, playground on (decisive): T = mean over seeds of Kendall tau-b; exact "
          "sign-flip p")
    print(f"{'policy':12s} {'kind':10s} {'T_BCD':>16s} {'p fall':>7s} {'T_D':>16s} "
          f"{'p fall':>7s} {'p rise':>7s} {'n':>3s}  reading")
    cells: dict[str, Any] = {}
    for pol in POLICIES:
        for kind in KINDS:
            c = cells_for(runs[(pol, "pg_on")], kind)
            cells[f"{pol}/{kind}"] = c
            print(f"{pol:12s} {kind:10s} {fmt_t(c['T_bcd']):>16s} {c['T_bcd']['p_fall']:7.4f} "
                  f"{fmt_t(c['T_d']):>16s} {c['T_d']['p_fall']:7.4f} {c['T_d']['p_rise']:7.4f} "
                  f"{c['T_d']['n']:3d}  {c['reading']}")
    hg = overall([c["reading"] for c in cells.values()])
    out["cells_pg_on"] = cells
    out["H_g"] = hg
    print(f"H-g (preregistered rule): {hg.upper()}")

    # --- playground off: secondary H-g reading for locomotion ---
    print("\nPlayground off, locomotor (preregistered, not decisive; same thresholds)")
    off_cells: dict[str, Any] = {}
    for pol in POLICIES:
        c = cells_for(runs[(pol, "pg_off")], "locomotor")
        off_cells[pol] = c
        print(f"{pol:12s} T_BCD {fmt_t(c['T_bcd'])} (p fall {c['T_bcd']['p_fall']:.4f})  "
              f"T_D {fmt_t(c['T_d'])} (p fall {c['T_d']['p_fall']:.4f}, "
              f"p rise {c['T_d']['p_rise']:.4f})  {c['reading']}")
    out["cells_pg_off_locomotor"] = off_cells

    # --- playground off: differential prediction ---
    obj_bad, loco_bad, n_det = [], [], 0
    for pol in POLICIES:
        for r in runs[(pol, "pg_off")]:
            for w in r["windows"]:
                if w["object"]["n_events"] > 0:
                    obj_bad.append(f"{pol}_{r['seed']}@{w['mid']:g}")
            for lab, det in r["detectors"].items():
                n_det += 1
                if det["locomotor"]["n_episodes"] < 10:
                    loco_bad.append(f"{pol}_{r['seed']}:{lab}")
    diff = {"object_event_windows": obj_bad, "locomotor_below_10": loco_bad,
            "detector_windows": n_det, "passes": not obj_bad and not loco_bad}
    out["differential_prediction"] = diff
    print(f"\nDifferential prediction, playground off: object events in {len(obj_bad)} windows; "
          f"locomotor < 10 episodes in {len(loco_bad)} of {n_det} detector windows -> "
          f"{'PASS' if diff['passes'] else 'FAIL'}")
    if loco_bad:
        print("  locomotor below 10: " + ", ".join(loco_bad))

    # --- the colony per arm ---
    print("\nColony landmarks, median [min, max] over seeds")
    lm: dict[str, Any] = {}
    print(f"{'arm':22s} " + " ".join(f"{k[:14]:>20s}" for k in LANDMARKS))
    for pol in POLICIES:
        for arm in ARMS:
            row = {}
            for k in LANDMARKS:
                v = np.array([r["landmarks"].get(k, np.nan) for r in runs[(pol, arm)]], float)
                v = v[np.isfinite(v)]
                row[k] = ({"median": float(np.median(v)), "min": float(v.min()),
                           "max": float(v.max()), "n": int(v.size)} if v.size else {"n": 0})
            lm[f"{pol}/{arm}"] = row
            cells_txt = " ".join(
                f"{row[k]['median']:7.0f} [{row[k]['min']:5.0f},{row[k]['max']:5.0f}]"
                if row[k]["n"] else f"{'-':>20s}" for k in LANDMARKS)
            print(f"{pol + '/' + arm:22s} {cells_txt}")
    out["landmarks"] = lm

    # --- detector vector by phase ---
    print("\nDetector vector by phase (rules v9): mean criteria count C and flag rates "
          "c1..c5 over seeds")
    dv: dict[str, Any] = {}
    for pol in POLICIES:
        for arm in ARMS:
            for kind in KINDS:
                for lab in LABELS:
                    dets = [r["detectors"][lab][kind] for r in runs[(pol, arm)]
                            if lab in r["detectors"]]
                    if not dets:
                        continue
                    fl = np.array([[bool(d["decisions_unvalidated"][f]) for f in FLAGS]
                                   for d in dets], float)
                    eps = [d["n_episodes"] for d in dets]
                    gate = [d.get("gate_relaxed_log_ratio_unvalidated", np.nan) for d in dets]
                    row = {"n": len(dets), "C": mse(fl.sum(axis=1)),
                           "flag_rates": dict(zip(FLAGS, fl.mean(axis=0).tolist())),
                           "episodes": mse(eps), "gate_log_ratio": mse(gate)}
                    dv[f"{pol}/{arm}/{kind}/{lab}"] = row
                    fr = " ".join(f"{x:.2f}" for x in fl.mean(axis=0))
                    gm = row["gate_log_ratio"]["mean"]
                    print(f"{pol:12s} {arm:7s} {kind:10s} {lab:8s} n {len(dets):2d}  "
                          f"C {row['C']['mean']:.2f}  flags {fr}  episodes "
                          f"{row['episodes']['mean']:7.0f}  gate {gm:+.2f}")
    out["detector_vector_by_phase"] = dv

    # --- beside: state shares and rates by phase ---
    print("\nBy phase, mean ± se over seeds of each run's phase mean (entered windows)")
    bp: dict[str, Any] = {}
    for pol in POLICIES:
        for arm in ARMS:
            lst = runs[(pol, arm)]
            if not lst:
                continue
            for key in BESIDE:
                pm = [phase_means(r, lambda w, k=key: w.get(k)) for r in lst]
                bp[f"{pol}/{arm}/{key}"] = {ph: mse([m[ph] for m in pm]) for ph in PHASES}
            for kind in KINDS:
                for key in KIND_BESIDE:
                    pm = [phase_means(r, lambda w, k=key, kd=kind: w[kd].get(k)) for r in lst]
                    bp[f"{pol}/{arm}/{kind}/{key}"] = {ph: mse([m[ph] for m in pm])
                                                       for ph in PHASES}
            for key in ("object/rate", "locomotor/rate", "relaxed_share_weaned",
                        "stressed_share_weaned", "withdrawn_share_weaned",
                        "juvenile_share_weaned", "n_alive"):
                v = bp[f"{pol}/{arm}/{key}"]
                txt = "  ".join(f"{ph} {v[ph]['mean']:.3g} ± {v[ph]['se']:.2g}" for ph in PHASES)
                print(f"{pol:12s} {arm:7s} {key:22s} {txt}")
    out["by_phase"] = bp

    # --- shape: rate by days since the peak ---
    print("\nRate by days since the peak (bins of 100 d; mean over seeds of each run's bin "
          "mean)")
    shape: dict[str, Any] = {}
    for pol in POLICIES:
        for arm in ARMS:
            for kind in KINDS:
                rows = []
                for lo_b in SHAPE_BINS[:-1]:
                    per = []
                    for r in runs[(pol, arm)]:
                        v = [w[kind]["rate"] for w in r["windows"]
                             if w["entered"] and lo_b <= w["mid"] - r["t_pk"] < lo_b + 100.0]
                        if v:
                            per.append(float(np.mean(v)))
                    rows.append({"from": float(lo_b), **mse(per)})
                shape[f"{pol}/{arm}/{kind}"] = rows
                if arm == "pg_off" and kind == "object":
                    continue
                txt = " ".join(f"{x['mean']:.3g}" if x["n"] else "-" for x in rows)
                print(f"{pol:12s} {arm:7s} {kind:10s} {txt}")
    out["shape_bins_from"] = SHAPE_BINS[:-1].tolist()
    out["shape"] = shape

    # --- late minus early phase D ---
    print("\nLate D (peak + 600) minus early D (peak + 150), rate, paired; two-sided sign-flip")
    le: dict[str, Any] = {}
    for pol in POLICIES:
        for arm in ARMS:
            for kind in KINDS:
                if arm == "pg_off" and kind == "object":
                    continue
                dlt = [rate_at(r, r["detector_windows"].get("D_late"), kind)
                       - rate_at(r, r["detector_windows"].get("D_early"), kind)
                       for r in runs[(pol, arm)]]
                res = two_sided(dlt)
                le[f"{pol}/{arm}/{kind}"] = res
                print(f"{pol:12s} {arm:7s} {kind:10s} {res['mean']:+.4f} ± {res['se']:.4f} "
                      f"(n {res['n']}, p {res['p_two_sided']:.4f})")
    out["late_minus_early_D"] = le

    # --- playground contrast, locomotion by phase ---
    print("\nLocomotor rate, playground on - off, by phase (paired by seed; two-sided "
          "sign-flip)")
    pc: dict[str, Any] = {}
    for pol in POLICIES:
        on = {r["seed"]: phase_means(r, lambda w: w["locomotor"]["rate"])
              for r in runs[(pol, "pg_on")]}
        off = {r["seed"]: phase_means(r, lambda w: w["locomotor"]["rate"])
               for r in runs[(pol, "pg_off")]}
        both = sorted(set(on) & set(off))
        for ph in PHASES:
            res = two_sided([on[s][ph] - off[s][ph] for s in both])
            pc[f"{pol}/{ph}"] = res
            print(f"{pol:12s} {ph}  {res['mean']:+.4f} ± {res['se']:.4f} "
                  f"(n {res['n']}, p {res['p_two_sided']:.4f})")
    out["pg_contrast_locomotor"] = pc

    f = sweep / "hg_analysis.json"
    f.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwritten {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
