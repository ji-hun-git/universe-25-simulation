#!/usr/bin/env python
"""Analysis of the norm-matched check of criterion 3 and H-i by the rules fixed in
PHASE4_DESIGN.md 4.5 (2026-11-13, before any code or run).

1. Genome norms per arm against the neutral pools' (the manipulation, by construction).
2. H-i (decisive): s_lambda(c) is the share of colony c's readings (one detector window x kind
   with >= 10 episodes) at size lambda with criterion 3 met (rules v9); d_c = s_1(c) - s_0(c)
   over the colonies with both defined (>= 16, else untested); exact one-sided sign-flip over
   colonies. Supported if mean d > 0 with p < 0.025; falsified if no S1 reading meets
   criterion 3; not supported otherwise.
3. Beside: the dose (S05 = lambda 1/2), colonies with a criterion-3 reading, criteria 4 and 5,
   the form excess and z, the detector vector by window, landmarks, action shares of the trace
   rows, episode rates by phase, and H-h's shares (other seeds: descriptive only).
Also beside (added after the first sweep, before any H-i statistic was read): the colonies that
died out before day 1,600, and H-i's rule with each detector window counted once (H-h's count,
the decisive one, counts a window twice when two labels pick it).
Writes <sweep>/nm_analysis.json.

usage: python scripts/analyse_nm.py [--sweep _output/nm_sweep] [--colonies 1-24]
       python scripts/analyse_nm.py --dev --sweep _output/nm_dev --colonies 1   (harness smoke)
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

from analyse_evo import (  # noqa: E402  (H-h's reading of a run, unchanged)
    C3,
    C4,
    FLAGS,
    KINDS,
    LABELS,
    LANDMARKS,
    PHASES,
    fmean,
    med,
    phase_means,
    readings,
)
from universe25.agents.state import (  # noqa: E402
    ACT_NEST,
    ACT_REST,
    ACT_SOCIAL,
    LOCO_FAMILY,
    OBJECT_FAMILY,
)
from universe25.metrics.phase_rates import sign_flip_low_memory  # noqa: E402

ARMS = ("S0", "S05", "S1")
SHOW = {"S0": "S0", "S05": "S½", "S1": "S1"}
ALPHA = 0.025
MIN_COLONIES = 16
SEED0 = 9904
DEV_SEED = 7000
LAYERS = ("w1", "b1", "w2", "b2")


def readings_once(run: dict) -> list[dict[str, Any]]:
    """Sensitivity only: readings() with each detector window counted once. H-h's readings()
    (the decisive count) takes the four labels; when two pick the same window (D_early and
    D_late both at the last window, say) that window counts twice. Here only the first label
    in B, C, D_early, D_late order is kept."""
    pick = run.get("detector_windows") or {}
    seen: set[float] = set()
    keep: set[str] = set()
    for label in LABELS:
        m = pick.get(label)
        if m is not None and m not in seen:
            seen.add(m)
            keep.add(label)
    return [x for x in readings(run) if x["label"] in keep]


def died_out(run: dict | None) -> bool:
    return bool(run) and int(run["run_summary"].get("final_n", 1)) == 0


def h_i_rule(sf: dict[str, Any], s1_total: int) -> str:
    """H-i's rule (PHASE4_DESIGN.md 4.5)."""
    if sf["n"] < MIN_COLONIES:
        return f"untested (only {sf['n']} colonies with readings at both S0 and S1)"
    if s1_total == 0:
        return "falsified (no S1 reading meets criterion 3)"
    if sf["mean"] > 0 and sf["p_rise"] < ALPHA:
        return "supported"
    return "not supported"


def rng_str(v: list[float], fmt: str = ".2f") -> str:
    v = [x for x in v if x is not None and np.isfinite(x)]
    if not v:
        return "—"
    return f"{np.mean(v):{fmt}} [{min(v):{fmt}}, {max(v):{fmt}}]"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", default=str(ROOT / "_output" / "nm_sweep"))
    p.add_argument("--colonies", default="1-24")
    p.add_argument("--dev", action="store_true", help="harness smoke: every colony on seed 7000")
    p.add_argument("--hh", default=str(ROOT / "_output" / "evo_sweep" / "evo_analysis.json"))
    a = p.parse_args()
    sweep = Path(a.sweep)
    lo, _, hi = a.colonies.partition("-")
    colonies = list(range(int(lo), int(hi or lo) + 1))
    manifest = json.loads((sweep / "pools" / "manifest.json").read_text(encoding="utf-8"))
    out: dict[str, Any] = {"sweep": str(sweep), "colonies": colonies, "dev": a.dev}

    runs: dict[tuple[str, int], dict | None] = {}
    missing = []
    for c in colonies:
        seed = DEV_SEED if a.dev else SEED0 + c
        for arm in ARMS:
            f = sweep / f"{arm}_c{c:02d}_{seed}" / "nm_run.json"
            if f.exists():
                runs[(arm, c)] = json.loads(f.read_text(encoding="utf-8"))
            else:
                runs[(arm, c)] = None
                missing.append(f.parent.name)
    out["missing"] = missing
    out["stops"] = [x for r in runs.values() if r for x in r.get("stop", [])]
    if missing:
        print(f"missing runs: {len(missing)} ({', '.join(missing[:6])} ...)")
    if out["stops"]:
        print("STOP (preregistered): " + "; ".join(out["stops"]))

    print("Colonies that died out before day 1,600 (no trace rows after; those windows are empty)")
    died: dict[str, Any] = {}
    for arm in ARMS:
        have = [c for c in colonies if runs[(arm, c)]]
        gone = [c for c in have if died_out(runs[(arm, c)])]
        days = [float(runs[(arm, c)]["run_summary"]["days_simulated"]) for c in gone]
        died[arm] = {"colonies": gone, "days": days, "of": len(have),
                     "empty_windows": [int(runs[(arm, c)].get("empty_windows", 0)) for c in gone]}
        print(f"  {SHOW[arm]:3s} {len(gone)}/{len(have)}"
              + (f": colonies {', '.join(str(c) for c in gone)}; last day {med(days)}"
                 if gone else ""))
    out["died_out"] = died

    # --- 1. genome norms (the manipulation, by construction) ---
    print("Genome norms per arm, mean [min, max] over colonies; neutral pools (NEU l) beside")
    norms: dict[str, Any] = {}
    for arm in ARMS:
        rows = [manifest[f"c{c:02d}_{arm}"]["norms"] for c in colonies]
        norms[arm] = {k: [r[k] for r in rows] for k in LAYERS}
        print(f"  {SHOW[arm]:3s} " + "  ".join(f"|{k}| {rng_str(norms[arm][k])}" for k in LAYERS))
    neu = [manifest[f"c{c:02d}_S1"]["neutral_norms"] for c in colonies]
    norms["NEU"] = {k: [r[k] for r in neu] for k in LAYERS}
    print("  NEU " + "  ".join(f"|{k}| {rng_str(norms['NEU'][k])}" for k in LAYERS))
    out["norms"] = norms

    # --- 2. H-i ---
    print("\nH-i: criterion-3 share of readings (>= 10 episodes) per colony and size")
    rows_h: dict[int, Any] = {}
    d_main, d_half, d_top = [], [], []
    for c in colonies:
        m = manifest[f"c{c:02d}_S1"]
        row: dict[str, Any] = {"lineage": m["lineage"], "base_index": m["base_index"],
                               "generations": m["generations"]}
        for arm in ARMS:
            rs = readings(runs[(arm, c)]) if runs[(arm, c)] else []
            k3 = sum(x["flags"][C3] for x in rs)
            k4 = sum(x["flags"][C4] for x in rs)
            k5 = sum(all(x["flags"][f] for f in FLAGS) for x in rs)
            row[arm] = {"readings": len(rs), "c3_met": k3, "c4_met": k4, "all_five": k5,
                        "c3_share": (k3 / len(rs)) if rs else None}
        s0, sh, s1 = (row[x]["c3_share"] for x in ARMS)
        if s1 is not None and s0 is not None:
            row["d"] = s1 - s0
            d_main.append(row["d"])
        if sh is not None and s0 is not None:
            d_half.append(sh - s0)
        if s1 is not None and sh is not None:
            d_top.append(s1 - sh)
        rows_h[c] = row
        for arm in ARMS:
            row[arm]["died_out"] = died_out(runs[(arm, c)])

        def fmt(arm: str, r: dict = row) -> str:
            return f"{r[arm]['c3_met']}/{r[arm]['readings']}" + ("†" if r[arm]["died_out"] else "")

        print(f"  colony {c:2d} (l{row['lineage']}, base {row['base_index']}, G "
              f"{row['generations']}): S0 {fmt('S0'):>6s}  S½ {fmt('S05'):>6s}  "
              f"S1 {fmt('S1'):>6s}  d {row.get('d', float('nan')):+.3f}")
    print("  († the colony died out before day 1,600)")
    sf = sign_flip_low_memory(d_main)
    s1_total = sum(rows_h[c]["S1"]["c3_met"] for c in colonies)
    reading = h_i_rule(sf, s1_total)
    print(f"  mean d {sf['mean']:+.4f} ± {sf['se']:.4f} (n {sf['n']}), p(rise) "
          f"{sf['p_rise']:.6f}; S1 readings with criterion 3: {s1_total}")
    print(f"H-i (preregistered rule): {reading.upper()}")

    # sensitivity (not decisive): each detector window once
    d_once, s1_once = [], 0
    for c in colonies:
        s = {}
        for arm in ("S0", "S1"):
            rs = readings_once(runs[(arm, c)]) if runs[(arm, c)] else []
            s[arm] = (sum(x["flags"][C3] for x in rs) / len(rs)) if rs else None
            if arm == "S1":
                s1_once += sum(x["flags"][C3] for x in rs)
        if s["S0"] is not None and s["S1"] is not None:
            d_once.append(s["S1"] - s["S0"])
    sf_once = sign_flip_low_memory(d_once)
    reading_once = h_i_rule(sf_once, s1_once)
    n_dup = sum(1 for r in runs.values() if r and len(readings_once(r)) < len(readings(r)))
    print(f"  sensitivity, each window once ({n_dup} runs with two labels on one window): "
          f"mean d {sf_once['mean']:+.4f} (n {sf_once['n']}), p(rise) "
          f"{sf_once['p_rise']:.6f}; S1 readings with criterion 3: {s1_once} -> {reading_once}")
    out["H_i"] = {"per_colony": rows_h, "sign_flip": sf, "s1_c3_total": s1_total,
                  "reading": reading,
                  "sensitivity_each_window_once": {"sign_flip": sf_once, "s1_c3_total": s1_once,
                                                   "reading": reading_once,
                                                   "runs_with_shared_window": n_dup}}

    # --- 3. beside ---
    print("\nThe dose (beside)")
    tot = {arm: {k: sum(rows_h[c][arm][k] for c in colonies)
                 for k in ("c3_met", "c4_met", "all_five", "readings")} for arm in ARMS}
    with_c3 = {arm: sum(rows_h[c][arm]["c3_met"] > 0 for c in colonies) for arm in ARMS}
    for arm in ARMS:
        t = tot[arm]
        print(f"  {SHOW[arm]:3s} criterion 3 in {t['c3_met']}/{t['readings']} readings, "
              f"{with_c3[arm]}/{len(colonies)} colonies with one; criterion 4 {t['c4_met']}; "
              f"all five {t['all_five']}")
    sh_, st_ = sign_flip_low_memory(d_half), sign_flip_low_memory(d_top)
    print(f"  S½ - S0: mean {sh_['mean']:+.4f} (n {sh_['n']}), p(rise) {sh_['p_rise']:.6f}")
    print(f"  S1 - S½: mean {st_['mean']:+.4f} (n {st_['n']}), p(rise) {st_['p_rise']:.6f}, "
          f"p(fall) {st_['p_fall']:.6f}")
    mono = sum(1 for c in colonies if all(rows_h[c][x]["c3_share"] is not None for x in ARMS)
               and rows_h[c]["S0"]["c3_share"] <= rows_h[c]["S05"]["c3_share"]
               <= rows_h[c]["S1"]["c3_share"])
    print(f"  colonies with s0 <= s½ <= s1: {mono}")
    agree = sum(x["flags"][C3] == x["flags"][C4] for r in runs.values() if r
                for x in readings(r))
    n_all = sum(len(readings(r)) for r in runs.values() if r)
    print(f"  criterion 4 agrees with criterion 3 in {agree} of {n_all} readings")
    out["dose"] = {"totals": tot, "colonies_with_c3": with_c3, "half_minus_zero": sh_,
                   "one_minus_half": st_, "monotone_colonies": mono,
                   "c3_c4_agree": agree, "readings": n_all}

    print("\nCriterion-3 readings (arm colony window kind episodes form-excess z reversal)")
    met = []
    for arm in ARMS:
        for c in colonies:
            r = runs[(arm, c)]
            if not r:
                continue
            for lab, det in (r.get("detectors") or {}).items():
                for kind in KINDS:
                    x = det.get(kind) or {}
                    if int(x.get("n_episodes", 0)) < 10:
                        continue
                    if not (x.get("decisions_unvalidated") or {}).get(C3):
                        continue
                    met.append({"arm": arm, "colony": c, "label": lab, "kind": kind,
                                "n_episodes": int(x["n_episodes"]),
                                "form_excess": x.get("seq_struct_form_excess_unvalidated"),
                                "form_z": x.get("seq_struct_form_z_unvalidated"),
                                "reversal": x.get("seq_struct_reversal_unvalidated"),
                                "all_five": all((x.get("decisions_unvalidated") or {})
                                                .get(f) for f in FLAGS)})
    for m in met:
        print(f"  {SHOW[m['arm']]:3s} c{m['colony']:02d} {m['label']:8s} {m['kind']:10s} "
              f"{m['n_episodes']:5d} {m['form_excess']:+.3f} {m['form_z']:6.2f} "
              f"{m['reversal']:.3f}{'  all five' if m['all_five'] else ''}")
    out["c3_readings"] = met

    print("\nDetector vector by window (rules v9): flag rates c1..c5 over readings; "
          "form excess median")
    dv: dict[str, Any] = {}
    for arm in ARMS:
        for kind in KINDS:
            for label in LABELS:
                rs = [x for c in colonies if runs[(arm, c)] for x in readings(runs[(arm, c)])
                      if x["kind"] == kind and x["label"] == label]
                if not rs:
                    continue
                fr = [float(np.mean([x["flags"][f] for x in rs])) for f in FLAGS]
                fe = [x["form_excess"] for x in rs if x["form_excess"] is not None
                      and np.isfinite(x["form_excess"])]
                dv[f"{arm}/{kind}/{label}"] = {"n": len(rs), "flag_rates": fr,
                                               "form_excess_median": float(np.median(fe))
                                               if fe else None}
                print(f"  {SHOW[arm]:3s} {kind:10s} {label:8s} n {len(rs):3d}  flags "
                      + " ".join(f"{v:.2f}" for v in fr)
                      + f"  form excess {np.median(fe) if fe else float('nan'):+.3f}")
    out["detector_vector"] = dv

    print("\nLandmarks, median [min, max] over colonies")
    lm: dict[str, Any] = {}
    print(f"{'arm':4s} " + " ".join(f"{k[:14]:>20s}" for k in LANDMARKS))
    for arm in ARMS:
        rows = [runs[(arm, c)]["landmarks"] for c in colonies if runs[(arm, c)]]
        lm[arm] = {k: [float(r.get(k, float("nan"))) for r in rows] for k in LANDMARKS}
        print(f"{SHOW[arm]:4s} " + " ".join(f"{med(lm[arm][k]):>20s}" for k in LANDMARKS))
    out["landmarks"] = lm

    print("\nAction shares of the trace rows, median [min, max] over colonies")
    fam = {"free": [ACT_SOCIAL, *LOCO_FAMILY, *OBJECT_FAMILY], "locomotor": list(LOCO_FAMILY),
           "object": list(OBJECT_FAMILY), "social": [ACT_SOCIAL], "nest": [ACT_NEST],
           "rest": [ACT_REST]}
    sh: dict[str, Any] = {}
    for arm in ARMS:
        cs = [np.asarray(runs[(arm, c)]["action_counts"], float) for c in colonies
              if runs[(arm, c)]]
        sh[arm] = {k: [float(x[idx].sum() / max(1.0, x.sum())) for x in cs]
                   for k, idx in fam.items()}
        print(f"  {SHOW[arm]:3s} " + "  ".join(
            f"{k} {np.median(v):.3f} [{min(v):.3f}, {max(v):.3f}]" for k, v in sh[arm].items()))
    out["action_shares"] = sh

    print("\nEpisode rates by phase (mean over colonies of each run's phase mean, entered windows)")
    bp: dict[str, Any] = {}
    for arm in ARMS:
        lst = [runs[(arm, c)] for c in colonies if runs[(arm, c)]]
        for kind in KINDS:
            pm = [phase_means(r, lambda w, k=kind: (w.get(k) or {}).get("rate")) for r in lst]
            v = {ph: fmean([m[ph] for m in pm]) for ph in PHASES}
            bp[f"{arm}/{kind}"] = v
            print(f"  {SHOW[arm]:3s} {kind:10s} " + "  ".join(f"{ph} {v[ph]:.3f}"
                                                            for ph in PHASES))
    out["by_phase"] = bp

    hh = Path(a.hh)
    if hh.exists():
        h = json.loads(hh.read_text(encoding="utf-8"))["H_h"]["per_lineage"]
        ref = {arm: [sum(r[arm]["c3_met"] for r in h.values()),
                     sum(r[arm]["readings"] for r in h.values())] for arm in ("SEL", "NEU",
                                                                             "GEN0")}
        print("\nH-h beside (other seeds and population structure; descriptive only): "
              + "  ".join(f"{k} {v[0]}/{v[1]}" for k, v in ref.items()))
        out["H_h_reference"] = ref

    f = sweep / "nm_analysis.json"
    f.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwritten {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
