#!/usr/bin/env python
"""Analysis of SCARCE-PG evo and H-j by the rules fixed in PHASE4_DESIGN.md 4.6 (2026-11-14,
before any code or run).

1. Pre-evolution: per scarce lineage, the epochs run, the depth reached against G_l, the colony
   and weaned count on day 360, the hunger probes, and decision shares over evolution, beside
   H-h's lineage.
2. The time budget per run: over the eligible rows of each entered window (phase B, C or D, at
   least 10 weaned individuals), F = the FORAGE share and T = the free-time share; a run's F and
   T are the means over its entered windows, a lineage's the mean of its two runs.
3. Manipulation check (decisive gate): d^F_l = F(SCARCE l) - F(ABUND l) over the lineages with
   both defined (>= 6, else untested); exact sign-flip, one-sided; passes if the mean > 0 with
   p < 0.025. If it fails, H-j is untested.
4. H-j (decisive): d^T_l = T(SCARCE l) - T(ABUND l), the same test. Supported if the mean < 0 with
   p(fall) < 0.025; falsified if the mean > 0 with p(rise) < 0.025; not supported otherwise.
5. Beside: SCARCE - NEU and ABUND - NEU for F and T; the whole budget; T within relaxed and
   other eligible rows; episode rates by phase; the detector vector by window and the criterion-3
   readings; landmarks; genome norms.
Writes <sweep>/scarce_analysis.json.

--regime small analyses small-meal evo and H-k by the rules fixed in PHASE4_DESIGN.md 4.7
(2026-11-15, before any code or run): arms SMALL, ABUND and NEU on seeds 9945-9960
(_output/small_sweep, lineages in _output/evo_small). The manipulation check reads voluntary
maintenance M = the FORAGE or DRINK share of the eligible rows (d^M > 0 at p < 0.025, else H-k
is untested), and H-k reads T as H-j does. F and D (DRINK) are reported beside, with the
epochs' eligible decisions and thirst probes. Writes <sweep>/small_analysis.json. Every regime
reports F, D, M and T; the default regime's other outputs are H-j's.

usage: python scripts/analyse_scarce.py [--regime scarce|small] [--sweep DIR] [--evo _output/evo]
       [--evo-scarce DIR] [--lineages 1-8] [--dev-seed 7000]
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

from universe25.agents.state import ACT_DRINK, ACT_FORAGE, N_ACTIONS  # noqa: E402
from universe25.metrics.phase_rates import (  # noqa: E402
    FREE_TIME_ACTIONS,
    budget_shares,
    label_windows,
    sign_flip,
)

ARMS = ("SCARCE", "ABUND", "NEU")
KINDS = ("object", "locomotor")
LABELS = ("B", "C", "D_early", "D_late")
PHASES = ("B", "C", "D")
ALPHA = 0.025
MIN_LINEAGES = 6
C3 = "c3_structurally_different"
SEED0 = 9929
# regime: (the evolved arm, first seed, its lineages and sweep folders under _output, the
# analysis file, the manipulation check's share, the hypothesis); scarce = H-j (4.6), small =
# H-k (4.7)
REGIMES = {
    "scarce": ("SCARCE", SEED0, "evo_scarce", "scarce_sweep", "scarce_analysis.json", "F", "H_j"),
    "small": ("SMALL", 9945, "evo_small", "small_sweep", "small_analysis.json", "M", "H_k"),
}
ACTION_NAMES = ("REST", "FORAGE", "DRINK", "NEST", "SOCIAL", "EXPLORE", "MANIPULATE", "AGGRESS",
                "MATE", "NURSE", "WITHDRAW", "RUN_ON", "TURN_BACK", "BACK_OFF", "CIRCLE")


def seeds_of(lineage: int, seed0: int = SEED0) -> list[int]:
    return [seed0 + 2 * (lineage - 1), seed0 + 2 * (lineage - 1) + 1]


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(r) for r in path.read_text(encoding="utf-8").splitlines() if r.strip()]


def run_shares(run: dict) -> dict[str, float]:
    """F, D (DRINK), M = F + D and T of one run (means over its entered windows), and T within
    the relaxed and the other eligible rows."""
    F, D, M, T, Tr, To = [], [], [], [], [], []
    for w in run["windows"]:
        if not w.get("entered"):
            continue
        b = w.get("budget") or {}
        el = np.asarray(b.get("eligible", [0] * N_ACTIONS), dtype=np.float64)
        rel = np.asarray(b.get("eligible_relaxed", [0] * N_ACTIONS), dtype=np.float64)
        s = budget_shares(el)
        F.append(s["F"])
        T.append(s["T"])
        n = float(el.sum())
        D.append(float(el[ACT_DRINK] / n) if n > 0 else float("nan"))
        M.append(float((el[ACT_FORAGE] + el[ACT_DRINK]) / n) if n > 0 else float("nan"))
        Tr.append(budget_shares(rel)["T"])
        To.append(budget_shares(el - rel)["T"])
    return {"F": fmean(F), "T": fmean(T), "T_relaxed": fmean(Tr), "T_other": fmean(To),
            "n_windows": int(sum(np.isfinite(x) for x in F)), "D": fmean(D), "M": fmean(M)}


def pooled_budget(runs: list[dict]) -> list[float]:
    """Each action's share of the eligible rows, pooled over the entered windows of `runs`."""
    c = np.zeros(N_ACTIONS)
    for run in runs:
        for w in run["windows"]:
            if w.get("entered"):
                c += np.asarray((w.get("budget") or {}).get("eligible", [0] * N_ACTIONS), float)
    return (c / c.sum()).tolist() if c.sum() > 0 else [float("nan")] * N_ACTIONS


def paired(per: dict, a: str, b: str, key: str, lineages: list[int]) -> dict[str, Any]:
    d = {lin: per[(a, lin)][key] - per[(b, lin)][key] for lin in lineages
         if np.isfinite(per[(a, lin)][key]) and np.isfinite(per[(b, lin)][key])}
    sf = sign_flip(list(d.values()))
    return {"d": {str(k): v for k, v in d.items()}, **sf}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--regime", choices=sorted(REGIMES), default="scarce")
    p.add_argument("--sweep", default=None, help="default: by regime")
    p.add_argument("--evo", default=str(ROOT / "_output" / "evo"))
    p.add_argument("--evo-scarce", default=None,
                   help="the evolved arm's lineages (default: by regime)")
    p.add_argument("--lineages", default="1-8")
    p.add_argument("--dev-seed", type=int, default=None,
                   help="harness smoke only: every lineage's runs on this one seed")
    a = p.parse_args()
    X, seed0, evo_dir, sweep_dir, out_name, chk_key, hyp = REGIMES[a.regime]
    arms = (X, "ABUND", "NEU")
    hyp_label = hyp.replace("_", "-")

    def seeds(lineage: int) -> list[int]:
        return [int(a.dev_seed)] if a.dev_seed is not None else seeds_of(lineage, seed0)

    sweep = Path(a.sweep) if a.sweep else ROOT / "_output" / sweep_dir
    evo_s = Path(a.evo_scarce) if a.evo_scarce else ROOT / "_output" / evo_dir
    evo = Path(a.evo)
    lo, _, hi = a.lineages.partition("-")
    lineages = list(range(int(lo), int(hi or lo) + 1))
    out: dict[str, Any] = {"sweep": str(sweep), "evo": str(evo), "evo_scarce": str(evo_s),
                           "lineages": lineages}
    free = list(FREE_TIME_ACTIONS)

    # --- 1. pre-evolution ---
    print(f"Pre-evolution: {X.lower()} line (epochs, depth / G, gen per epoch, N and weaned on "
          "day 360 first 10 / last 10, hungry and starving shares of weaned animals in the second"
          " half, last 10) | H-h line (N on day 360 first 10 / last 10)")
    pre = {}
    for lin in lineages:
        rs, ra = _rows(evo_s / f"lineage_{lin}" / "epochs.jsonl"), _rows(
            evo / f"lineage_{lin}" / "epochs.jsonl")
        ss = evo_s / f"lineage_{lin}" / "summary.json"
        summ = json.loads(ss.read_text(encoding="utf-8")) if ss.exists() else {}
        sa = json.loads((evo / f"lineage_{lin}" / "summary.json").read_text(encoding="utf-8"))
        if not rs:
            print(f"  lineage {lin}: no {X.lower()} epochs")
            continue

        def m(rows, f, sl):
            return fmean([f(r) for r in rows[sl]])

        def probe(k):
            return lambda r: (r.get("probe") or {}).get(k)

        def dshare(idx):
            return lambda r: float(np.sum([r["decision_action_shares"][i] for i in idx]))

        def eshare(idx):  # eligible decisions (recorded since small-meal evo)
            return lambda r: (float(np.sum([r["eligible_action_shares"][i] for i in idx]))
                              if r.get("eligible_action_shares") else float("nan"))

        first, last = slice(0, 10), slice(-10, None)
        pre[lin] = {
            "epochs": len(rs), "ended": summ.get("ended"), "stop_depth": summ.get("stop_depth"),
            "depth_reached": summ.get("depth_reached"), "depth_final": summ.get("final_depth_mean"),
            "generations_per_epoch": (summ.get("final_depth_mean") or float("nan")) / len(rs),
            "abund_epochs": len(ra), "abund_depth": sa.get("final_depth_mean"),
            "n_end_first10": m(rs, lambda r: r["n_end"], first),
            "n_end_last10": m(rs, lambda r: r["n_end"], last),
            "weaned_end_first10": m(rs, probe("weaned_end"), first),
            "weaned_end_last10": m(rs, probe("weaned_end"), last),
            "hungry_2h_last10": m(rs, probe("hungry_share_2h"), last),
            "starving_2h_last10": m(rs, probe("starving_share_2h"), last),
            "hungry_2h_all": m(rs, probe("hungry_share_2h"), slice(None)),
            "starving_2h_all": m(rs, probe("starving_share_2h"), slice(None)),
            "abund_n_end_first10": m(ra, lambda r: r["n_end"], first),
            "abund_n_end_last10": m(ra, lambda r: r["n_end"], last),
            "forage_decisions_first10": m(rs, dshare([1]), first),
            "forage_decisions_last10": m(rs, dshare([1]), last),
            "free_decisions_first10": m(rs, dshare(free), first),
            "free_decisions_last10": m(rs, dshare(free), last),
            "abund_forage_decisions_last10": m(ra, dshare([1]), last),
            "abund_free_decisions_last10": m(ra, dshare(free), last),
            "norms_final": summ.get("final_norms"), "abund_norms_final": sa.get("final_norms"),
            "neutral_norms": sa.get("neutral_norms"),
            "wall_s": float(sum(r["wall_s"] for r in rs)),
            "thirst_starving_2h_last10": m(rs, probe("thirst_starving_share_2h"), last),
            "thirst_starving_2h_all": m(rs, probe("thirst_starving_share_2h"), slice(None)),
            "eligible_forage_first10": m(rs, eshare([ACT_FORAGE]), first),
            "eligible_forage_last10": m(rs, eshare([ACT_FORAGE]), last),
            "eligible_drink_first10": m(rs, eshare([ACT_DRINK]), first),
            "eligible_drink_last10": m(rs, eshare([ACT_DRINK]), last),
            "eligible_free_first10": m(rs, eshare(free), first),
            "eligible_free_last10": m(rs, eshare(free), last),
        }
        q = pre[lin]
        print(f"  l{lin}: {q['epochs']} epochs, depth {q['depth_final']} / {q['stop_depth']} "
              f"({q['generations_per_epoch']:.2f}/epoch), N {q['n_end_first10']:.0f} -> "
              f"{q['n_end_last10']:.0f}, weaned {q['weaned_end_first10']:.0f} -> "
              f"{q['weaned_end_last10']:.0f}, hungry {q['hungry_2h_last10']:.3f}, starving "
              f"{q['starving_2h_last10']:.4f} | H-h N {q['abund_n_end_first10']:.0f} -> "
              f"{q['abund_n_end_last10']:.0f} | decisions FORAGE "
              f"{q['forage_decisions_first10']:.3f} -> {q['forage_decisions_last10']:.3f} "
              f"(H-h {q['abund_forage_decisions_last10']:.3f}), free "
              f"{q['free_decisions_first10']:.3f} -> {q['free_decisions_last10']:.3f} (H-h "
              f"{q['abund_free_decisions_last10']:.3f})")
        if np.isfinite(q["eligible_forage_last10"]):
            print(f"      eligible decisions FORAGE {q['eligible_forage_first10']:.3f} -> "
                  f"{q['eligible_forage_last10']:.3f}, DRINK {q['eligible_drink_first10']:.3f} -> "
                  f"{q['eligible_drink_last10']:.3f}, free {q['eligible_free_first10']:.3f} -> "
                  f"{q['eligible_free_last10']:.3f}; thirst-starving "
                  f"{q['thirst_starving_2h_last10']:.4f}")
    out["pre_evolution"] = {str(k): v for k, v in pre.items()}

    # --- 2. runs and their time budgets ---
    runs: dict[tuple[str, int], list[dict]] = {}
    for arm in arms:
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
    print("\nTime budget per lineage (F voluntary foraging, T free time; mean of the two runs)")
    print(f"{'lin':>4s} " + " ".join(f"{arm + ' F':>10s} {arm + ' T':>10s}" for arm in arms))
    for lin in lineages:
        for arm in arms:
            lst = runs[(arm, lin)]
            per[(arm, lin)] = {k: fmean([r["shares"][k] for r in lst])
                               for k in ("F", "T", "T_relaxed", "T_other")}
            per[(arm, lin)]["n_runs"] = len(lst)
            per[(arm, lin)].update({k: fmean([r["shares"][k] for r in lst]) for k in ("D", "M")})
        print(f"{lin:>4d} " + " ".join(
            f"{per[(arm, lin)]['F']:>10.4f} {per[(arm, lin)]['T']:>10.4f}" for arm in arms))
    if chk_key != "F":
        print(f"\nVoluntary maintenance per lineage ({chk_key} = FORAGE or DRINK; D = DRINK)")
        print(f"{'lin':>4s} " + " ".join(f"{arm + ' ' + chk_key:>10s} {arm + ' D':>10s}"
                                         for arm in arms))
        for lin in lineages:
            print(f"{lin:>4d} " + " ".join(f"{per[(arm, lin)][chk_key]:>10.4f} "
                                           f"{per[(arm, lin)]['D']:>10.4f}" for arm in arms))
    out["per_lineage"] = {f"{arm}/{lin}": per[(arm, lin)] for arm in arms for lin in lineages}

    # --- 3. manipulation check ---
    chk = paired(per, X, "ABUND", chk_key, lineages)
    if chk["n"] < MIN_LINEAGES:
        chk_reading = f"untested (only {chk['n']} lineages with both shares defined)"
    elif chk["mean"] > 0 and chk["p_rise"] < ALPHA:
        chk_reading = "passes"
    else:
        chk_reading = "fails"
    out["manipulation_check"] = {**chk, "reading": chk_reading}
    print(f"\nManipulation check: {chk_key}({X}) - {chk_key}(ABUND) mean {chk['mean']:+.4f} +- "
          f"{chk['se']:.4f} over {chk['n']} lineages, p(rise) {chk['p_rise']:.4f} -> "
          f"{chk_reading}")

    # --- 4. H-j or H-k ---
    hj = paired(per, X, "ABUND", "T", lineages)
    if chk_reading != "passes":
        hj_reading = "untested (the manipulation check did not pass)"
    elif hj["n"] < MIN_LINEAGES:
        hj_reading = f"untested (only {hj['n']} lineages with both shares defined)"
    elif hj["mean"] < 0 and hj["p_fall"] < ALPHA:
        hj_reading = "supported"
    elif hj["mean"] > 0 and hj["p_rise"] < ALPHA:
        hj_reading = "falsified"
    else:
        hj_reading = "not supported"
    out[hyp] = {**hj, "reading": hj_reading}
    print(f"{hyp_label}: T({X}) - T(ABUND) mean {hj['mean']:+.4f} +- {hj['se']:.4f} over "
          f"{hj['n']} lineages, p(fall) {hj['p_fall']:.4f}, p(rise) {hj['p_rise']:.4f} -> "
          f"{hj_reading}")
    for k, v in sorted(hj["d"].items(), key=lambda kv: int(kv[0])):
        print(f"   lineage {k}: d^T {v:+.4f}, d^{chk_key} {chk['d'].get(k, float('nan')):+.4f}")

    # --- 5. beside ---
    print("\nBeside: against drift (NEU), and T within relaxed / other eligible rows")
    bes = {}
    for a1 in (X, "ABUND"):
        for key in ("F", "T", "T_relaxed", "T_other", "D", "M"):
            r = paired(per, a1, "NEU", key, lineages)
            bes[f"{a1}-NEU/{key}"] = r
            print(f"  {a1} - NEU {key:9s}: mean {r['mean']:+.4f} over {r['n']}, p(rise) "
                  f"{r['p_rise']:.4f}, p(fall) {r['p_fall']:.4f}")
    for key in [k for k in ("T_relaxed", "T_other", "F", "D", "M") if k != chk_key]:
        r = paired(per, X, "ABUND", key, lineages)
        bes[f"{X}-ABUND/{key}"] = r
        print(f"  {X} - ABUND {key:9s}: mean {r['mean']:+.4f} over {r['n']}, p(rise) "
              f"{r['p_rise']:.4f}, p(fall) {r['p_fall']:.4f}")
    out["beside"] = bes

    print("\nWhole budget: each action's share of the eligible rows, pooled over entered windows")
    bud = {arm: pooled_budget([r for lin in lineages for r in runs[(arm, lin)]]) for arm in arms}
    for i, name in enumerate(ACTION_NAMES):
        print(f"  {name:10s} " + " ".join(f"{arm} {bud[arm][i]:.4f}" for arm in arms))
    out["budget_pooled"] = bud

    print("\nEpisode rates by phase (mean over runs of each run's phase mean, entered windows)")
    rates = {}
    for arm in arms:
        lst = [r for lin in lineages for r in runs[(arm, lin)]]
        for kind in KINDS:
            pm = [phase_means(r, lambda w, k=kind: (w.get(k) or {}).get("rate")) for r in lst]
            rates[f"{arm}/{kind}"] = {ph: fmean([x[ph] for x in pm]) for ph in PHASES}
            print(f"  {arm:6s} {kind:10s} " + " ".join(
                f"{ph} {rates[f'{arm}/{kind}'][ph]:.3f}" for ph in PHASES))
        pm = [phase_means(r, lambda w: w.get("relaxed_share_weaned")) for r in lst]
        rates[f"{arm}/relaxed"] = {ph: fmean([x[ph] for x in pm]) for ph in PHASES}
    out["rates_by_phase"] = rates

    print("\nDetector vector by window (rules v9): flag rates c1..c5 over readings")
    dv = {}
    for arm in arms:
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
    for arm in arms:
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
    for arm in arms:
        rows = [r["landmarks"] for lin in lineages for r in runs[(arm, lin)]]
        lm[arm] = {k: [float(x.get(k, float("nan"))) for x in rows] for k in LANDMARKS}
        print(f"{arm:6s} " + " ".join(f"{med(lm[arm][k]):>20s}" for k in LANDMARKS))
    out["landmarks"] = lm
    died = {arm: [f"l{lin}_{r['seed']}" for lin in lineages for r in runs[(arm, lin)]
                  if int(r["run_summary"].get("final_n", 1)) == 0] for arm in arms}
    out["died_out"] = died
    print(f"died out before day 1,600: {died}")

    out["regime"] = a.regime
    f = sweep / out_name
    f.write_text(json.dumps(out, default=float, indent=1), encoding="utf-8")
    print(f"\nwrote {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
