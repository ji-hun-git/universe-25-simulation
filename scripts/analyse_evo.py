#!/usr/bin/env python
"""Analysis of `evo` and H-h by the rules fixed in PHASE4_DESIGN.md 4.4 (2026-11-13, before any
code or run).

1. Pre-evolution: per lineage, the colony on day 360 over the epochs, founder depth, genome
   norms, and the neutral control's generations.
2. Manipulation check: d_l = SEL - GEN0 in N@315 (mean of the lineage's 2 seeds); exact
   sign-flip over lineages, one-sided; passes if mean d > 0 with p < 0.025. If it fails, H-h is
   untested.
3. H-h (decisive): a reading is one detector window x kind of a run with >= 10 episodes of that
   kind; s_A(l) = the share of arm A's readings of lineage l with criterion 3 met (rules v9);
   d_l = s_SEL - s_NEU over lineages with both defined (>= 6, else untested); exact sign-flip,
   one-sided. Supported if mean d > 0 with p < 0.025; falsified if no SEL reading meets
   criterion 3; not supported otherwise.
4. Guard v2 for SEL (16 seeds, lineages pooled) against the need-driven control, with the
   amended H-d table (reported, not decisive here).
5. Beside: criterion 4, GEN0, the form excess and z, the detector vector by window, episode
   rates by phase, landmarks per arm.
Writes <sweep>/evo_analysis.json.

usage: python scripts/analyse_evo.py [--sweep _output/evo_sweep] [--evo _output/evo]
       [--lineages 1-8]
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
sys.path.insert(0, str(ROOT / "scripts"))

from universe25.calib.policy_guard import (  # noqa: E402
    decline_band_ok,
    drift_table,
    equivalence,
    format_equivalence,
    verdict,
)
from universe25.metrics.phase_rates import sign_flip  # noqa: E402

ARMS = ("SEL", "NEU", "GEN0")
KINDS = ("object", "locomotor")
LABELS = ("B", "C", "D_early", "D_late")
PHASES = ("B", "C", "D")
MIN_EPISODES = 10
ALPHA = 0.025
MIN_LINEAGES = 6
C3, C4 = "c3_structurally_different", "c4_repeated_not_rigid"
FLAGS = ("c1_not_functional", "c2_spontaneous", C3, C4, "c5_relaxed_field")
LANDMARKS = ("first_litters_day", "n_at_day_315", "peak_n", "peak_day", "last_young_day",
             "last_conception_day", "n_at_day_1444", "n_at_day_1588")
SEED0 = 9889


def seeds_of(lineage: int) -> list[int]:
    return [SEED0 + 2 * (lineage - 1), SEED0 + 2 * (lineage - 1) + 1]


def readings(run: dict) -> list[dict[str, Any]]:
    out = []
    for label, det in (run.get("detectors") or {}).items():
        for kind in KINDS:
            r = det.get(kind) or {}
            if int(r.get("n_episodes", 0)) < MIN_EPISODES:
                continue
            dec = r.get("decisions_unvalidated", {})
            out.append({"label": label, "kind": kind, "flags": {f: bool(dec.get(f)) for f in FLAGS},
                        "form_excess": r.get("seq_struct_form_excess_unvalidated"),
                        "form_z": r.get("seq_struct_form_z_unvalidated"),
                        "n_episodes": int(r["n_episodes"])})
    return out


def share(runs: list[dict], flag: str) -> tuple[int, int, float | None]:
    rs = [x for run in runs for x in readings(run)]
    k = sum(x["flags"][flag] for x in rs)
    return k, len(rs), (k / len(rs) if rs else None)


def med(v: list[float]) -> str:
    v = [x for x in v if x is not None and np.isfinite(x)]
    if not v:
        return "—"
    return f"{np.median(v):.0f} [{min(v):.0f}, {max(v):.0f}]"


def fmean(v: list[float]) -> float:
    """Mean of the finite values; NaN (without a warning) when there are none."""
    v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def phase_means(run: dict, get) -> dict[str, float]:
    out = {}
    for ph in PHASES:
        v = [get(w) for w in run["windows"] if w.get("entered") and w.get("phase") == ph]
        v = [x for x in v if x is not None and np.isfinite(x)]
        out[ph] = float(np.mean(v)) if v else float("nan")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", default=str(ROOT / "_output" / "evo_sweep"))
    p.add_argument("--evo", default=str(ROOT / "_output" / "evo"))
    p.add_argument("--lineages", default="1-8")
    p.add_argument("--dev-seed", type=int, default=None,
                   help="harness smoke only: every lineage's runs on this one seed")
    a = p.parse_args()
    if a.dev_seed is not None:
        global seeds_of

        def seeds_of(lineage: int) -> list[int]:  # noqa: F811
            return [int(a.dev_seed)]
    sweep, evo = Path(a.sweep), Path(a.evo)
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))
    out: dict[str, Any] = {"sweep": str(sweep), "evo": str(evo), "lineages": lineages}

    # --- 1. pre-evolution ---
    print("Pre-evolution (per lineage): N on day 360, epochs 0-9 / last 10; adult depth at the "
          "end; |W2| gen0 -> final / neutral")
    pre = {}
    for lin in lineages:
        d = evo / f"lineage_{lin}"
        rows = [json.loads(r) for r in (d / "epochs.jsonl").read_text(encoding="utf-8")
                .splitlines() if r.strip()] if (d / "epochs.jsonl").exists() else []
        summ = json.loads((d / "summary.json").read_text(encoding="utf-8")) \
            if (d / "summary.json").exists() else {}
        if not rows:
            print(f"  lineage {lin}: no epochs")
            continue
        n = [r["n_end"] for r in rows]
        pre[lin] = {"epochs": len(rows), "ended": summ.get("ended"),
                    "n_end_first10": float(np.mean(n[:10])),
                    "n_end_last10": float(np.mean(n[-10:])),
                    "births_first10": float(np.mean([r["births"] for r in rows[:10]])),
                    "births_last10": float(np.mean([r["births"] for r in rows[-10:]])),
                    "depth_final": summ.get("final_depth_mean"),
                    "neutral_generations": summ.get("neutral_generations"),
                    "norms_gen0": summ.get("gen0_norms"), "norms_final": summ.get("final_norms"),
                    "norms_neutral": summ.get("neutral_norms"),
                    "wall_s": float(sum(r["wall_s"] for r in rows)),
                    "n_end_by_epoch": n,
                    "action_shares_last10": np.mean([r["decision_action_shares"]
                                                     for r in rows[-10:]], axis=0).tolist()}
        q = pre[lin]
        w2 = lambda k: (q[k] or {}).get("w2", float("nan"))  # noqa: E731
        end = ' ENDED ' + q['ended'] if q['ended'] else ''
        print(f"  lineage {lin}: {q['epochs']} epochs{end};"
              f" N {q['n_end_first10']:.0f} -> {q['n_end_last10']:.0f}; depth "
              f"{q['depth_final'] if q['depth_final'] is None else round(q['depth_final'], 1)}; "
              f"|W2| {w2('norms_gen0'):.2f} -> {w2('norms_final'):.2f} / {w2('norms_neutral'):.2f};"
              f" {q['wall_s'] / 3600:.2f} CPU-h")
    out["pre_evolution"] = pre

    # --- load the evaluation ---
    runs: dict[tuple[str, int], list[dict]] = {}
    missing = []
    for lin in lineages:
        for arm in ARMS:
            lst = []
            for s in seeds_of(lin):
                f = sweep / f"{arm}_l{lin}_{s}" / "evo_run.json"
                if f.exists():
                    lst.append(json.loads(f.read_text(encoding="utf-8")))
                else:
                    missing.append(f.parent.name)
            runs[(arm, lin)] = lst
    ctrl = {}
    for lin in lineages:
        for s in seeds_of(lin):
            f = sweep / f"control_{s}" / "control_run.json"
            if f.exists():
                ctrl[s] = json.loads(f.read_text(encoding="utf-8"))["landmarks"]
            else:
                missing.append(f.parent.name)
    out["missing"] = missing
    stops = [x for lst in runs.values() for r in lst for x in r.get("stop", [])]
    out["stops"] = stops
    if missing:
        print(f"\nmissing runs: {len(missing)} ({', '.join(missing[:6])}...)")

    # --- 2. manipulation check ---
    print("\nManipulation check: SEL - GEN0 in N@315 (mean of each lineage's 2 seeds)")
    dm, mrows = [], {}
    for lin in lineages:
        sel = [r["landmarks"].get("n_at_day_315") for r in runs[("SEL", lin)]]
        g0 = [r["landmarks"].get("n_at_day_315") for r in runs[("GEN0", lin)]]
        if len(sel) == 2 and len(g0) == 2:
            d = float(np.mean(sel) - np.mean(g0))
            dm.append(d)
            mrows[lin] = {"sel": sel, "gen0": g0, "d": d}
            print(f"  lineage {lin}: SEL {np.mean(sel):7.0f}  GEN0 {np.mean(g0):7.0f}  d {d:+7.0f}")
    sf = sign_flip(dm)
    passed = bool(sf["n"] >= MIN_LINEAGES and sf["mean"] > 0 and sf["p_rise"] < ALPHA)
    print(f"  mean d {sf['mean']:+.0f} ± {sf['se']:.0f} (n {sf['n']}), p(rise) "
          f"{sf['p_rise']:.4f} -> {'PASS' if passed else 'FAIL'}")
    out["manipulation_check"] = {"per_lineage": mrows, "sign_flip": sf, "passes": passed}

    # --- 3. H-h ---
    print("\nH-h: criterion-3 share of readings (>= 10 episodes), per lineage and arm")
    hrows, dh = {}, []
    sel_c3_total = 0
    for lin in lineages:
        row = {}
        for arm in ARMS:
            k, n, s = share(runs[(arm, lin)], C3)
            k4, _, s4 = share(runs[(arm, lin)], C4)
            row[arm] = {"c3_met": k, "readings": n, "c3_share": s, "c4_met": k4, "c4_share": s4}
        sel_c3_total += row["SEL"]["c3_met"]
        if row["SEL"]["c3_share"] is not None and row["NEU"]["c3_share"] is not None:
            row["d"] = row["SEL"]["c3_share"] - row["NEU"]["c3_share"]
            dh.append(row["d"])
        hrows[lin] = row
        fmt = lambda r: f"{r['c3_met']:2d}/{r['readings']:2d}"  # noqa: E731
        print(f"  lineage {lin}: SEL {fmt(row['SEL'])}  NEU {fmt(row['NEU'])}  GEN0 "
              f"{fmt(row['GEN0'])}  d {row.get('d', float('nan')):+.3f}")
    sh = sign_flip(dh)
    if not passed:
        reading = "untested (the manipulation check failed: selection did not adapt the colony)"
    elif sh["n"] < MIN_LINEAGES:
        reading = f"untested (only {sh['n']} lineages with both shares defined)"
    elif sel_c3_total == 0:
        reading = "falsified (no SEL reading meets criterion 3)"
    elif sh["mean"] > 0 and sh["p_rise"] < ALPHA:
        reading = "supported"
    else:
        reading = "not supported"
    print(f"  mean d {sh['mean']:+.4f} ± {sh['se']:.4f} (n {sh['n']}), p(rise) "
          f"{sh['p_rise']:.4f}; SEL readings with criterion 3: {sel_c3_total}")
    print(f"H-h (preregistered rule): {reading.upper()}")
    out["H_h"] = {"per_lineage": hrows, "sign_flip": sh, "sel_c3_total": sel_c3_total,
                  "reading": reading}

    # --- 4. guard v2 ---
    sel_rows = {r["seed"]: r["landmarks"] for lin in lineages for r in runs[("SEL", lin)]}
    common = sorted(set(sel_rows) & set(ctrl))
    if len(common) >= 2:
        c_rows = {s: ctrl[s] for s in common}
        a_rows = {s: sel_rows[s] for s in common}
        eq = equivalence(c_rows, a_rows, seed=common[0])
        table = drift_table(c_rows, a_rows)
        ver = verdict(table, decline_band_ok(a_rows))
        print("\nGuard for evo (SEL, lineages pooled) against the need-driven control, "
              f"{len(common)} seeds")
        print(format_equivalence(eq))
        print(f"amended H-d: {'PRESERVED' if ver['preserved'] else 'NOT PRESERVED'} "
              f"(failures: {', '.join(ver['failures']) or 'none'})")
        out["guard"] = {"seeds": common, "equivalence_v2": eq, "drift_table": table,
                        "verdict_amended": ver}

    # --- 5. beside ---
    print("\nLandmarks, median [min, max] over runs")
    lm: dict[str, Any] = {}
    print(f"{'arm':6s} " + " ".join(f"{k[:14]:>20s}" for k in LANDMARKS))
    groups = {arm: [r["landmarks"] for lin in lineages for r in runs[(arm, lin)]]
              for arm in ARMS}
    groups["CTRL"] = list(ctrl.values())
    for arm, rows in groups.items():
        lm[arm] = {k: [float(r.get(k, float("nan"))) for r in rows] for k in LANDMARKS}
        print(f"{arm:6s} " + " ".join(f"{med(lm[arm][k]):>20s}" for k in LANDMARKS))
    out["landmarks"] = lm

    print("\nDetector vector by window (rules v9): flag rates c1..c5 over readings; "
          "form excess median")
    dv: dict[str, Any] = {}
    for arm in ARMS:
        for kind in KINDS:
            for label in LABELS:
                rs = [x for lin in lineages for run in runs[(arm, lin)] for x in readings(run)
                      if x["kind"] == kind and x["label"] == label]
                if not rs:
                    continue
                fr = [float(np.mean([x["flags"][f] for x in rs])) for f in FLAGS]
                fe = [x["form_excess"] for x in rs if x["form_excess"] is not None
                      and np.isfinite(x["form_excess"])]
                dv[f"{arm}/{kind}/{label}"] = {"n": len(rs), "flag_rates": fr,
                                               "form_excess_median": float(np.median(fe))
                                               if fe else None}
                print(f"{arm:5s} {kind:10s} {label:8s} n {len(rs):3d}  flags "
                      + " ".join(f"{v:.2f}" for v in fr)
                      + f"  form excess {np.median(fe) if fe else float('nan'):+.3f}")
    out["detector_vector"] = dv

    print("\nEpisode rates by phase (mean over runs of each run's phase mean, entered windows)")
    bp: dict[str, Any] = {}
    for arm in ARMS:
        lst = [r for lin in lineages for r in runs[(arm, lin)]]
        for kind in KINDS:
            pm = [phase_means(r, lambda w, k=kind: (w.get(k) or {}).get("rate")) for r in lst]
            v = {ph: fmean([m[ph] for m in pm]) for ph in PHASES}
            bp[f"{arm}/{kind}"] = v
            print(f"{arm:5s} {kind:10s} " + "  ".join(f"{ph} {v[ph]:.3f}" for ph in PHASES))
        pm = [phase_means(r, lambda w: w.get("relaxed_share_weaned")) for r in lst]
        bp[f"{arm}/relaxed"] = {ph: fmean([m[ph] for m in pm]) for ph in PHASES}
    out["by_phase"] = bp

    f = sweep / "evo_analysis.json"
    f.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwritten {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
