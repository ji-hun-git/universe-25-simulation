#!/usr/bin/env python
"""Exploratory readings beside H-j (NOTES 2026-11-14; not decisive, no rule or stored output
changes). From the outputs of evolve_scarce.py, sweep_scarce.py and analyse_scarce.py:
- per run: F, T, the entered windows, the colony's peak and N@315, and the share of weaned rows
  that are eligible (no reflex);
- whether the two seeds of a lineage agree in the sign of d^F and d^T;
- the whole budget per lineage (each action's share of the eligible rows, the mean over the
  runs' entered windows), its mean over lineages per arm, and the lineages with SCARCE above
  ABUND and above NEU;
- the epochs' own executed-action shares (all animals and ticks, pups and reflexes included;
  analyse_scarce's pre-evolution) against the garden's d^F and d^T;
- the scarce epochs' hunger probes over evolution (first, middle and last 10 epochs).
Writes _output/scarce_sweep/scarce_beside.json.

usage: python scripts/scarce_beside.py [--sweep _output/scarce_sweep]
       [--evo-scarce _output/evo_scarce]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from analyse_scarce import ACTION_NAMES, ARMS, run_shares, seeds_of  # noqa: E402

from universe25.agents.state import N_ACTIONS  # noqa: E402
from universe25.metrics.phase_rates import label_windows  # noqa: E402

LINEAGES = tuple(range(1, 9))
PROBES = ("weaned_end", "weaned_mean_2h", "hunger_mean_2h", "hungry_share_2h",
          "starving_share_2h", "starving_share_max")


def run_budget(run: dict) -> tuple[np.ndarray, float]:
    """Each action's share of the eligible rows (mean over entered windows), and the eligible
    share of the weaned rows."""
    shares, elig = [], []
    for w in run["windows"]:
        if not w.get("entered"):
            continue
        el = np.asarray(w["budget"]["eligible"], dtype=np.float64)
        we = np.asarray(w["budget"]["weaned"], dtype=np.float64)
        if el.sum() <= 0:
            continue
        shares.append(el / el.sum())
        elig.append(el.sum() / we.sum() if we.sum() > 0 else np.nan)
    if not shares:
        return np.full(N_ACTIONS, np.nan), float("nan")
    return np.mean(shares, axis=0), float(np.nanmean(elig))


def probe_course(evo_scarce: Path, lineage: int) -> dict[str, dict[str, float]]:
    path = evo_scarce / f"lineage_{lineage}" / "epochs.jsonl"
    rows = [json.loads(r) for r in path.read_text(encoding="utf-8").splitlines() if r.strip()]
    mid = len(rows) // 2
    out = {}
    for part, sl in (("first10", rows[:10]), ("middle10", rows[mid - 5:mid + 5]),
                     ("last10", rows[-10:])):
        rec = {}
        for k in PROBES:
            v = [(r.get("probe") or {}).get(k) for r in sl]
            v = [float(x) for x in v if x is not None and np.isfinite(x)]
            rec[k] = float(np.mean(v)) if v else float("nan")
        rec["n_end"] = float(np.mean([r["n_end"] for r in sl]))
        rec["births"] = float(np.mean([r["births"] for r in sl]))
        rec["peak_n"] = float(np.mean([r["peak_n"] for r in sl]))
        out[part] = rec
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", default=str(ROOT / "_output" / "scarce_sweep"))
    p.add_argument("--evo-scarce", default=str(ROOT / "_output" / "evo_scarce"))
    a = p.parse_args()
    sweep, evo_s = Path(a.sweep), Path(a.evo_scarce)
    ana = json.loads((sweep / "scarce_analysis.json").read_text(encoding="utf-8"))
    out: dict = {"runs": {}, "seed_agreement": {}, "budget": {}, "budget_mean": {},
                 "epochs_vs_garden": {}, "probes": {}}

    runs = {}
    print("per run: F, T, entered windows, peak N on day, N@315, eligible share of weaned rows")
    for arm in ARMS:
        for lin in LINEAGES:
            for s in seeds_of(lin):
                d = sweep / f"{arm}_l{lin}_{s}"
                r = json.loads((d / "scarce_run.json").read_text(encoding="utf-8"))
                label_windows(r["windows"], r["t_fl"], r["t_pk"])
                sh = run_shares(r)
                bud, elig = run_budget(r)
                lm = r["landmarks"]
                runs[(arm, lin, s)] = {
                    "F": sh["F"], "T": sh["T"], "n_windows": sh["n_windows"],
                    "budget": bud, "eligible_of_weaned": elig, "peak_n": lm.get("peak_n"),
                    "peak_day": lm.get("peak_day"), "n_at_day_315": lm.get("n_at_day_315")}
    for lin in LINEAGES:
        for s in seeds_of(lin):
            parts = [f"l{lin} {s}"]
            for arm in ARMS:
                q = runs[(arm, lin, s)]
                parts.append(f"{arm[:3]} F {q['F']:.3f} T {q['T']:.3f} w{q['n_windows']:2d} "
                             f"peak {q['peak_n']:.0f} on {q['peak_day']:.0f} "
                             f"N@315 {q['n_at_day_315']:.0f} elig {q['eligible_of_weaned']:.2f}")
            print(" | ".join(parts))
    out["runs"] = {f"{k[0]}_l{k[1]}_{k[2]}": {**v, "budget": v["budget"].tolist()}
                   for k, v in runs.items()}

    print("\nthe two seeds of a lineage: F(SCARCE) - F(ABUND) and T(SCARCE) - T(ABUND)")
    agree = {"F": 0, "T": 0}
    for lin in LINEAGES:
        dF = [runs[("SCARCE", lin, s)]["F"] - runs[("ABUND", lin, s)]["F"] for s in seeds_of(lin)]
        dT = [runs[("SCARCE", lin, s)]["T"] - runs[("ABUND", lin, s)]["T"] for s in seeds_of(lin)]
        agree["F"] += int(np.sign(dF[0]) == np.sign(dF[1]))
        agree["T"] += int(np.sign(dT[0]) == np.sign(dT[1]))
        out["seed_agreement"][str(lin)] = {"dF": dF, "dT": dT}
        print(f"  l{lin}: dF {dF[0]:+.3f} {dF[1]:+.3f}   dT {dT[0]:+.3f} {dT[1]:+.3f}")
    out["seed_agreement"]["lineages_agreeing"] = agree
    print(f"  lineages whose seeds agree in sign: F {agree['F']} of 8, T {agree['T']} of 8")

    lin_bud = {(arm, lin): np.nanmean([runs[(arm, lin, s)]["budget"] for s in seeds_of(lin)],
                                      axis=0) for arm in ARMS for lin in LINEAGES}
    out["budget"] = {f"{arm}/{lin}": lin_bud[(arm, lin)].tolist()
                     for arm in ARMS for lin in LINEAGES}
    print("\nwhole budget: mean over lineages per arm (SCARCE / ABUND / NEU); lineages with SCARCE"
          " above ABUND, above NEU")
    for i, name in enumerate(ACTION_NAMES):
        v = {arm: np.array([lin_bud[(arm, lin)][i] for lin in LINEAGES]) for arm in ARMS}
        above_a = int((v["SCARCE"] > v["ABUND"]).sum())
        above_n = int((v["SCARCE"] > v["NEU"]).sum())
        out["budget_mean"][name] = {**{arm: float(v[arm].mean()) for arm in ARMS},
                                    "scarce_above_abund": above_a, "scarce_above_neu": above_n}
        print(f"  {name:10s} {v['SCARCE'].mean():.3f} / {v['ABUND'].mean():.3f} / "
              f"{v['NEU'].mean():.3f}   above ABUND {above_a}/8, above NEU {above_n}/8")

    print("\nepochs, last 10 (scarce minus H-h, each line in its own world) against the garden")
    pre = ana["pre_evolution"]
    xf, xt, yf, yt = [], [], [], []
    for lin in LINEAGES:
        q = pre[str(lin)]
        ef = q["forage_decisions_last10"] - q["abund_forage_decisions_last10"]
        et = q["free_decisions_last10"] - q["abund_free_decisions_last10"]
        gf = ana["manipulation_check"]["d"][str(lin)]
        gt = ana["H_j"]["d"][str(lin)]
        xf.append(ef)
        xt.append(et)
        yf.append(gf)
        yt.append(gt)
        out["epochs_vs_garden"][str(lin)] = {"epochs_forage": ef, "epochs_free": et,
                                             "garden_dF": gf, "garden_dT": gt}
        print(f"  l{lin}: epochs FORAGE {ef:+.3f} free {et:+.3f} | garden dF {gf:+.3f} "
              f"dT {gt:+.3f}")
    rf, rt = float(np.corrcoef(xf, yf)[0, 1]), float(np.corrcoef(xt, yt)[0, 1])
    out["epochs_vs_garden"]["r_forage"], out["epochs_vs_garden"]["r_free"] = rf, rt
    print(f"  correlation over 8 lineages: FORAGE {rf:+.2f}, free time {rt:+.2f}")

    print("\nscarce epochs over evolution (first / middle / last 10): weaned on day 360, weaned,"
          " hunger, hungry and starving shares (second half), worst day starving, N on day 360")
    for lin in LINEAGES:
        pc = probe_course(evo_s, lin)
        out["probes"][str(lin)] = pc
        for part, rec in pc.items():
            print(f"  l{lin} {part:8s} " + " ".join(f"{rec[k]:8.4f}" for k in PROBES)
                  + f" {rec['n_end']:6.0f}")
    (sweep / "scarce_beside.json").write_text(json.dumps(out, default=float, indent=1),
                                               encoding="utf-8")
    print(f"\nwrote {sweep / 'scarce_beside.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
