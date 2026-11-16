#!/usr/bin/env python
"""Analysis of late-reflex evo and H-l by the rules fixed in PHASE4_DESIGN.md 4.8 (2026-11-16,
before any code or run).

1. Pre-evolution: per lineage of the two late lines, LF (full meals) and LS (small meals), the
   epochs run, the depth reached against G_l, the colony and weaned count on day 360, the hunger
   and thirst probes, and the eligible decisions' shares over evolution, beside H-h's lineage.
2. The time budget per run: over the eligible rows of each entered window (phase B, C or D, at
   least 10 weaned individuals), M = the FORAGE or DRINK share and T = the free-time share, with
   F and D apart; a run's shares are the means over its entered windows, a lineage's the mean of
   its two runs.
3. Manipulation check (decisive gate): d^M_l = M(LS l) - M(LF l) over the lineages with both
   defined (>= 6, else untested); exact sign-flip, one-sided; passes if the mean > 0 with
   p < 0.025. If it fails, H-l is untested.
4. H-l (decisive): d^T_l = T(LS l) - T(LF l), the same test. Supported if the mean < 0 with
   p(fall) < 0.025; falsified if the mean > 0 with p(rise) < 0.025; not supported otherwise.
5. Beside: F, D, T within relaxed and other eligible rows (LS - LF); LS - NEU and LF - NEU;
   LF - ABUND and LS - ABUND; the whole budget (pooled, and the mean of the lineages'); episode
   rates by phase; the detector vector by window and the criterion-3 readings; landmarks; genome
   norms; the two seeds of each lineage; the garden's d^M against the lines' last-10-epoch M.
Writes <sweep>/late_analysis.json.

usage: python scripts/analyse_late.py [--sweep DIR] [--evo _output/evo] [--late-full DIR]
       [--late-small DIR] [--lineages 1-8] [--dev-seed 7000]
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

from analyse_evo import FLAGS, LANDMARKS, fmean, med, phase_means, readings  # noqa: E402
from analyse_scarce import (  # noqa: E402  (H-j's and H-k's shares and tests, unchanged)
    ACTION_NAMES,
    ALPHA,
    C3,
    KINDS,
    LABELS,
    MIN_LINEAGES,
    PHASES,
    _rows,
    paired,
    pooled_budget,
    run_shares,
)

from universe25.agents.state import ACT_DRINK, ACT_FORAGE  # noqa: E402
from universe25.metrics.phase_rates import FREE_TIME_ACTIONS, label_windows  # noqa: E402

ARMS = ("LS", "LF", "ABUND", "NEU")
LINES = ("LF", "LS")
SEED0 = 9961
SHARES = ("F", "D", "M", "T", "T_relaxed", "T_other")


def seeds_of(lineage: int, seed0: int = SEED0) -> list[int]:
    return [seed0 + 2 * (lineage - 1), seed0 + 2 * (lineage - 1) + 1]


def pre_line(evo_line: Path, evo: Path, lin: int) -> dict[str, Any] | None:
    """One late lineage's epochs: length, depth, colony, probes and eligible shares."""
    rs = _rows(evo_line / f"lineage_{lin}" / "epochs.jsonl")
    if not rs:
        return None
    ra = _rows(evo / f"lineage_{lin}" / "epochs.jsonl")
    sf = evo_line / f"lineage_{lin}" / "summary.json"
    summ = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
    free = list(FREE_TIME_ACTIONS)
    first, last = slice(0, 10), slice(-10, None)

    def m(rows: list[dict], f, sl) -> float:
        return fmean([f(r) for r in rows[sl]])

    def probe(k: str):
        return lambda r: (r.get("probe") or {}).get(k)

    def eshare(idx: list[int]):
        return lambda r: float(np.sum([r["eligible_action_shares"][i] for i in idx]))

    q: dict[str, Any] = {
        "epochs": len(rs), "ended": summ.get("ended"), "stop_depth": summ.get("stop_depth"),
        "depth_reached": summ.get("depth_reached"), "depth_final": summ.get("final_depth_mean"),
        "depth_last": rs[-1].get("adult_depth_mean"),
        "generations_per_epoch": (summ.get("final_depth_mean") or float("nan")) / len(rs),
        "norms_final": summ.get("final_norms"),
        "wall_s": float(sum(r["wall_s"] for r in rs)),
        "abund_n_end_first10": m(ra, lambda r: r["n_end"], first),
        "abund_n_end_last10": m(ra, lambda r: r["n_end"], last),
    }
    for tag, sl in (("first10", first), ("last10", last), ("all", slice(None))):
        q[f"n_end_{tag}"] = m(rs, lambda r: r["n_end"], sl)
        q[f"weaned_end_{tag}"] = m(rs, probe("weaned_end"), sl)
        q[f"hunger_2h_{tag}"] = m(rs, probe("hunger_mean_2h"), sl)
        q[f"hungry_2h_{tag}"] = m(rs, probe("hungry_share_2h"), sl)
        q[f"starving_2h_{tag}"] = m(rs, probe("starving_share_2h"), sl)
        q[f"thirst_starving_2h_{tag}"] = m(rs, probe("thirst_starving_share_2h"), sl)
        q[f"thirst_starving_max_{tag}"] = m(rs, probe("thirst_starving_share_max"), sl)
        q[f"decision_forage_{tag}"] = m(rs, lambda r: r["decision_action_shares"][ACT_FORAGE], sl)
        q[f"eligible_F_{tag}"] = m(rs, eshare([ACT_FORAGE]), sl)
        q[f"eligible_D_{tag}"] = m(rs, eshare([ACT_DRINK]), sl)
        q[f"eligible_M_{tag}"] = m(rs, eshare([ACT_FORAGE, ACT_DRINK]), sl)
        q[f"eligible_T_{tag}"] = m(rs, eshare(free), sl)
    q["eligible_last10"] = (np.mean([r["eligible_action_shares"] for r in rs[last]], axis=0)
                            .round(5).tolist())
    q["eligible_first10"] = (np.mean([r["eligible_action_shares"] for r in rs[first]], axis=0)
                             .round(5).tolist())
    return q


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", default=str(ROOT / "_output" / "late_sweep"))
    p.add_argument("--evo", default=str(ROOT / "_output" / "evo"))
    p.add_argument("--late-full", default=str(ROOT / "_output" / "evo_late_full"))
    p.add_argument("--late-small", default=str(ROOT / "_output" / "evo_late_small"))
    p.add_argument("--lineages", default="1-8")
    p.add_argument("--dev-seed", type=int, default=None,
                   help="harness smoke only: every lineage's runs on this one seed")
    a = p.parse_args()
    sweep, evo = Path(a.sweep), Path(a.evo)
    evo_line = {"LF": Path(a.late_full), "LS": Path(a.late_small)}
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))

    def seeds(lineage: int) -> list[int]:
        return [int(a.dev_seed)] if a.dev_seed is not None else seeds_of(lineage)

    out: dict[str, Any] = {"sweep": str(sweep), "evo": str(evo),
                           "lines": {k: str(v) for k, v in evo_line.items()},
                           "lineages": lineages}

    # --- 1. pre-evolution ---
    print("Pre-evolution (epochs, depth / G, generations per epoch; N and weaned on day 360, "
          "first 10 / last 10 epochs; weaned animals' mean hunger, shares above the reflex and "
          "above thirst 1.2 in the second half, last 10; eligible M and T, first 10 -> last 10)")
    pre: dict[str, dict[str, Any]] = {}
    for line in LINES:
        for lin in lineages:
            q = pre_line(evo_line[line], evo, lin)
            if q is None:
                print(f"  {line} l{lin}: no epochs")
                continue
            pre[f"{line}/{lin}"] = q
            print(f"  {line} l{lin}: {q['epochs']} epochs, depth {q['depth_final']} / "
                  f"{q['stop_depth']} ({q['generations_per_epoch']:.2f}/epoch), ended "
                  f"{q['ended']} | N {q['n_end_first10']:.0f} -> {q['n_end_last10']:.0f}, weaned "
                  f"{q['weaned_end_first10']:.0f} -> {q['weaned_end_last10']:.0f} | hunger "
                  f"{q['hunger_2h_last10']:.3f}, above reflex {q['hungry_2h_last10']:.4f}, thirst "
                  f"> 1.2 {q['thirst_starving_2h_last10']:.4f} | M "
                  f"{q['eligible_M_first10']:.3f} -> "
                  f"{q['eligible_M_last10']:.3f}, T {q['eligible_T_first10']:.3f} -> "
                  f"{q['eligible_T_last10']:.3f}")
    out["pre_evolution"] = pre

    # --- 2. runs and their time budgets ---
    runs: dict[tuple[str, int], list[dict]] = {}
    for arm in ARMS:
        for lin in lineages:
            lst = []
            for s in seeds(lin):
                f = sweep / f"{arm}_l{lin}_{s}" / "scarce_run.json"
                if f.exists():
                    r = json.loads(f.read_text(encoding="utf-8"))
                    label_windows(r["windows"], r["t_fl"], r["t_pk"])
                    r["shares"] = run_shares(r)
                    lst.append(r)
            runs[(arm, lin)] = lst
    per: dict[tuple[str, int], dict[str, float]] = {}
    for lin in lineages:
        for arm in ARMS:
            lst = runs[(arm, lin)]
            per[(arm, lin)] = {k: fmean([r["shares"][k] for r in lst]) for k in SHARES}
            per[(arm, lin)]["n_runs"] = len(lst)
    print("\nTime budget per lineage (M voluntary maintenance = FORAGE or DRINK, T free time; "
          "mean of the two runs)")
    print(f"{'lin':>4s} " + " ".join(f"{arm + ' M':>9s} {arm + ' T':>9s}" for arm in ARMS))
    for lin in lineages:
        print(f"{lin:>4d} " + " ".join(f"{per[(arm, lin)]['M']:>9.4f} {per[(arm, lin)]['T']:>9.4f}"
                                       for arm in ARMS))
    print(f"{'lin':>4s} " + " ".join(f"{arm + ' F':>9s} {arm + ' D':>9s}" for arm in ARMS))
    for lin in lineages:
        print(f"{lin:>4d} " + " ".join(f"{per[(arm, lin)]['F']:>9.4f} {per[(arm, lin)]['D']:>9.4f}"
                                       for arm in ARMS))
    out["per_lineage"] = {f"{arm}/{lin}": per[(arm, lin)] for arm in ARMS for lin in lineages}

    # --- 3. manipulation check ---
    chk = paired(per, "LS", "LF", "M", lineages)
    if chk["n"] < MIN_LINEAGES:
        chk_reading = f"untested (only {chk['n']} lineages with both shares defined)"
    elif chk["mean"] > 0 and chk["p_rise"] < ALPHA:
        chk_reading = "passes"
    else:
        chk_reading = "fails"
    out["manipulation_check"] = {**chk, "reading": chk_reading}
    print(f"\nManipulation check: M(LS) - M(LF) mean {chk['mean']:+.4f} +- {chk['se']:.4f} over "
          f"{chk['n']} lineages, p(rise) {chk['p_rise']:.4f} -> {chk_reading}")

    # --- 4. H-l ---
    hl = paired(per, "LS", "LF", "T", lineages)
    if chk_reading != "passes":
        hl_reading = "untested (the manipulation check did not pass)"
    elif hl["n"] < MIN_LINEAGES:
        hl_reading = f"untested (only {hl['n']} lineages with both shares defined)"
    elif hl["mean"] < 0 and hl["p_fall"] < ALPHA:
        hl_reading = "supported"
    elif hl["mean"] > 0 and hl["p_rise"] < ALPHA:
        hl_reading = "falsified"
    else:
        hl_reading = "not supported"
    out["H_l"] = {**hl, "reading": hl_reading}
    print(f"H-l: T(LS) - T(LF) mean {hl['mean']:+.4f} +- {hl['se']:.4f} over {hl['n']} lineages, "
          f"p(fall) {hl['p_fall']:.4f}, p(rise) {hl['p_rise']:.4f} -> {hl_reading}")
    for k, v in sorted(hl["d"].items(), key=lambda kv: int(kv[0])):
        print(f"   lineage {k}: d^M {chk['d'].get(k, float('nan')):+.4f}, d^T {v:+.4f}")

    # --- 5. beside ---
    print("\nBeside (paired by lineage; mean, n, p(rise), p(fall))")
    bes: dict[str, Any] = {}
    pairs = ([("LS", "LF", k) for k in ("F", "D", "T_relaxed", "T_other")]
             + [(x, "NEU", k) for x in ("LS", "LF", "ABUND") for k in ("M", "F", "D", "T")]
             + [(x, "ABUND", k) for x in ("LF", "LS") for k in ("M", "F", "D", "T")])
    for a1, a2, key in pairs:
        r = paired(per, a1, a2, key, lineages)
        bes[f"{a1}-{a2}/{key}"] = r
        print(f"  {a1:5s} - {a2:5s} {key:9s}: mean {r['mean']:+.4f} over {r['n']}, p(rise) "
              f"{r['p_rise']:.4f}, p(fall) {r['p_fall']:.4f}")
    out["beside"] = bes

    print("\nThe two seeds of a lineage: d^M and d^T on each seed")
    agree = {"M": 0, "T": 0, "pairs": 0}
    seed_d = {}
    for lin in lineages:
        ss = seeds(lin)
        rl = {r["seed"]: r["shares"] for r in runs[("LS", lin)]}
        rf = {r["seed"]: r["shares"] for r in runs[("LF", lin)]}
        if len(ss) < 2 or any(s not in rl or s not in rf for s in ss):
            print(f"  l{lin}: no pair")
            continue
        dm = [rl[s]["M"] - rf[s]["M"] for s in ss]
        dt = [rl[s]["T"] - rf[s]["T"] for s in ss]
        agree["M"] += int(np.sign(dm[0]) == np.sign(dm[1]))
        agree["T"] += int(np.sign(dt[0]) == np.sign(dt[1]))
        agree["pairs"] += 1
        seed_d[str(lin)] = {"dM": dm, "dT": dt}
        print(f"  l{lin}: dM {dm[0]:+.3f} {dm[1]:+.3f}   dT {dt[0]:+.3f} {dt[1]:+.3f}")
    print(f"  seeds agree in sign: M {agree['M']} of {agree['pairs']}, T {agree['T']} of "
          f"{agree['pairs']}")
    out["seed_agreement"] = {"by_lineage": seed_d, **agree}

    print("\nGarden against epochs (exploratory): d^M against LS minus LF eligible M in their "
          "last 10 epochs (each line in its own world)")
    xs, ys = [], []
    for k, v in chk["d"].items():
        qs, qf = pre.get(f"LS/{k}"), pre.get(f"LF/{k}")
        if qs and qf:
            xs.append(qs["eligible_M_last10"] - qf["eligible_M_last10"])
            ys.append(v)
            print(f"  l{k}: epochs {xs[-1]:+.3f} | garden d^M {v:+.3f}")
    r_em = float(np.corrcoef(xs, ys)[0, 1]) if len(xs) > 2 else float("nan")
    print(f"  correlation over {len(xs)} lineages: {r_em:+.2f}")
    out["epochs_vs_garden"] = {"x": xs, "y": ys, "r": r_em}

    print("\nWhole budget: each action's share of the eligible rows (pooled over entered "
          "windows | mean of the lineages')")
    bud = {arm: pooled_budget([r for lin in lineages for r in runs[(arm, lin)]]) for arm in ARMS}
    lin_bud = {}
    for arm in ARMS:
        vals = [pooled_budget(runs[(arm, lin)]) for lin in lineages if runs[(arm, lin)]]
        lin_bud[arm] = np.nanmean(vals, axis=0).tolist() if vals else [float("nan")] * 15
    for i, name in enumerate(ACTION_NAMES):
        print(f"  {name:10s} " + " ".join(f"{arm} {bud[arm][i]:.4f}" for arm in ARMS) + " | "
              + " ".join(f"{arm} {lin_bud[arm][i]:.4f}" for arm in ARMS))
    out["budget_pooled"] = bud
    out["budget_lineage_mean"] = lin_bud

    print("\nEpisode rates by phase (mean over runs of each run's phase mean, entered windows)")
    rates = {}
    for arm in ARMS:
        lst = [r for lin in lineages for r in runs[(arm, lin)]]
        for kind in KINDS:
            pm = [phase_means(r, lambda w, k=kind: (w.get(k) or {}).get("rate")) for r in lst]
            rates[f"{arm}/{kind}"] = {ph: fmean([x[ph] for x in pm]) for ph in PHASES}
            print(f"  {arm:6s} {kind:10s} " + " ".join(
                f"{ph} {rates[f'{arm}/{kind}'][ph]:.3f}" for ph in PHASES))
    out["rates_by_phase"] = rates

    print("\nDetector vector by window (rules v9): flag rates c1..c5 over readings")
    dv = {}
    for arm in ARMS:
        lst = [r for lin in lineages for r in runs[(arm, lin)]]
        for kind in KINDS:
            for label in LABELS:
                rs = [x for r in lst for x in readings(r) if x["label"] == label
                      and x["kind"] == kind]
                if not rs:
                    continue
                fr = [float(np.mean([x["flags"][f] for x in rs])) for f in FLAGS]
                dv[f"{arm}/{kind}/{label}"] = {"n": len(rs), "flag_rates": fr}
                print(f"  {arm:6s} {kind:10s} {label:8s} n {len(rs):3d}  "
                      + " ".join(f"{v:.2f}" for v in fr))
    out["detector_vector"] = dv
    c3 = {}
    for arm in ARMS:
        rs = [(lin, x) for lin in lineages for r in runs[(arm, lin)] for x in readings(r)]
        c3[arm] = {"met": int(sum(x["flags"][C3] for _, x in rs)), "readings": len(rs),
                   "by_lineage": {str(lin): int(sum(x["flags"][C3] for li, x in rs if li == lin))
                                  for lin in lineages}}
        print(f"  criterion 3 {arm}: {c3[arm]['met']} of {c3[arm]['readings']} readings, by "
              f"lineage {c3[arm]['by_lineage']}")
    out["criterion3"] = c3

    print("\nLandmarks (median [range] over runs)")
    lm = {}
    print(f"{'arm':6s} " + " ".join(f"{k[:14]:>20s}" for k in LANDMARKS))
    for arm in ARMS:
        rows = [r["landmarks"] for lin in lineages for r in runs[(arm, lin)]]
        lm[arm] = {k: [float(x.get(k, float("nan"))) for x in rows] for k in LANDMARKS}
        print(f"{arm:6s} " + " ".join(f"{med(lm[arm][k]):>20s}" for k in LANDMARKS))
    out["landmarks"] = lm
    died = {arm: [f"l{lin}_{r['seed']}" for lin in lineages for r in runs[(arm, lin)]
                  if int(r["run_summary"].get("final_n", 1)) == 0] for arm in ARMS}
    out["died_out"] = died
    print(f"died out before day 1,600: {died}")

    f = sweep / "late_analysis.json"
    f.write_text(json.dumps(out, default=float, indent=1), encoding="utf-8")
    print(f"\nwrote {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
