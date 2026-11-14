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

--regime small reads small-meal evo instead (PHASE4_DESIGN.md 4.7; arm SMALL, seeds 9945-9960,
_output/small_sweep and _output/evo_small): the seeds' agreement and the epochs-against-garden
comparison use the manipulation check's share M (FORAGE or DRINK) in place of F, and the probes
add the thirst-starving share. Writes _output/small_sweep/small_beside.json.

usage: python scripts/scarce_beside.py [--regime scarce|small] [--sweep DIR] [--evo-scarce DIR]
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

from analyse_scarce import ACTION_NAMES, REGIMES, run_shares, seeds_of  # noqa: E402

from universe25.agents.state import ACT_DRINK, N_ACTIONS  # noqa: E402
from universe25.metrics.phase_rates import label_windows  # noqa: E402

LINEAGES = tuple(range(1, 9))
PROBES = ("weaned_end", "weaned_mean_2h", "hunger_mean_2h", "hungry_share_2h",
          "starving_share_2h", "starving_share_max")
THIRST = ("thirst_starving_share_2h", "thirst_starving_share_max")  # small-meal epochs on


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


def epoch_rows(path: Path) -> list[dict]:
    return [json.loads(r) for r in path.read_text(encoding="utf-8").splitlines() if r.strip()]


def probe_course(evo_scarce: Path, lineage: int,
                 keys: tuple[str, ...] = PROBES) -> dict[str, dict[str, float]]:
    path = evo_scarce / f"lineage_{lineage}" / "epochs.jsonl"
    rows = [json.loads(r) for r in path.read_text(encoding="utf-8").splitlines() if r.strip()]
    mid = len(rows) // 2
    out = {}
    for part, sl in (("first10", rows[:10]), ("middle10", rows[mid - 5:mid + 5]),
                     ("last10", rows[-10:])):
        rec = {}
        for k in keys:
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
    p.add_argument("--regime", choices=sorted(REGIMES), default="scarce")
    p.add_argument("--sweep", default=None, help="default: by regime")
    p.add_argument("--evo-scarce", default=None, help="default: by regime")
    a = p.parse_args()
    X, seed0, evo_dir, sweep_dir, ana_name, chk, hyp = REGIMES[a.regime]
    arms = (X, "ABUND", "NEU")
    sweep = Path(a.sweep) if a.sweep else ROOT / "_output" / sweep_dir
    evo_s = Path(a.evo_scarce) if a.evo_scarce else ROOT / "_output" / evo_dir
    ana = json.loads((sweep / ana_name).read_text(encoding="utf-8"))
    out: dict = {"runs": {}, "seed_agreement": {}, "budget": {}, "budget_mean": {},
                 "epochs_vs_garden": {}, "probes": {}}

    runs = {}
    print("per run: F, T, entered windows, peak N on day, N@315, eligible share of weaned rows")
    for arm in arms:
        for lin in LINEAGES:
            for s in seeds_of(lin, seed0):
                d = sweep / f"{arm}_l{lin}_{s}"
                if not (d / "scarce_run.json").exists():  # e.g. a lineage that ended
                    continue
                r = json.loads((d / "scarce_run.json").read_text(encoding="utf-8"))
                label_windows(r["windows"], r["t_fl"], r["t_pk"])
                sh = run_shares(r)
                bud, elig = run_budget(r)
                lm = r["landmarks"]
                runs[(arm, lin, s)] = {
                    "F": sh["F"], "T": sh["T"], "n_windows": sh["n_windows"],
                    "D": sh["D"], "M": sh["M"],
                    "budget": bud, "eligible_of_weaned": elig, "peak_n": lm.get("peak_n"),
                    "peak_day": lm.get("peak_day"), "n_at_day_315": lm.get("n_at_day_315")}
    for lin in LINEAGES:
        for s in seeds_of(lin, seed0):
            parts = [f"l{lin} {s}"]
            for arm in arms:
                q = runs.get((arm, lin, s))
                if q is None:
                    parts.append(f"{arm[:3]} no run")
                    continue
                parts.append(f"{arm[:3]} F {q['F']:.3f} T {q['T']:.3f} w{q['n_windows']:2d} "
                             f"peak {q['peak_n']:.0f} on {q['peak_day']:.0f} "
                             f"N@315 {q['n_at_day_315']:.0f} elig {q['eligible_of_weaned']:.2f}")
            print(" | ".join(parts))
    out["runs"] = {f"{k[0]}_l{k[1]}_{k[2]}": {**v, "budget": v["budget"].tolist()}
                   for k, v in runs.items()}

    print(f"\nthe two seeds of a lineage: {chk}({X}) - {chk}(ABUND) and T({X}) - T(ABUND)")
    agree = {chk: 0, "T": 0}
    n_pairs = 0
    for lin in LINEAGES:
        sl = seeds_of(lin, seed0)
        if any((arm, lin, s) not in runs for arm in (X, "ABUND") for s in sl):
            print(f"  l{lin}: no pair")
            continue
        dF = [runs[(X, lin, s)][chk] - runs[("ABUND", lin, s)][chk] for s in sl]
        dT = [runs[(X, lin, s)]["T"] - runs[("ABUND", lin, s)]["T"] for s in sl]
        agree[chk] += int(np.sign(dF[0]) == np.sign(dF[1]))
        agree["T"] += int(np.sign(dT[0]) == np.sign(dT[1]))
        n_pairs += 1
        out["seed_agreement"][str(lin)] = {f"d{chk}": dF, "dT": dT}
        print(f"  l{lin}: d{chk} {dF[0]:+.3f} {dF[1]:+.3f}   dT {dT[0]:+.3f} {dT[1]:+.3f}")
    out["seed_agreement"]["lineages_agreeing"] = agree
    print(f"  lineages whose seeds agree in sign: {chk} {agree[chk]} of {n_pairs}, T "
          f"{agree['T']} of {n_pairs}")

    lin_bud = {(arm, lin): (np.nanmean([runs[(arm, lin, s)]["budget"] for s in seeds_of(lin, seed0)
                                        if (arm, lin, s) in runs], axis=0)
                            if any((arm, lin, s) in runs for s in seeds_of(lin, seed0))
                            else np.full(N_ACTIONS, np.nan))
               for arm in arms for lin in LINEAGES}
    out["budget"] = {f"{arm}/{lin}": lin_bud[(arm, lin)].tolist()
                     for arm in arms for lin in LINEAGES}
    print(f"\nwhole budget: mean over lineages per arm ({X} / ABUND / NEU); lineages with {X}"
          " above ABUND, above NEU")
    for i, name in enumerate(ACTION_NAMES):
        v = {arm: np.array([lin_bud[(arm, lin)][i] for lin in LINEAGES]) for arm in arms}
        above_a = int((v[X] > v["ABUND"]).sum())  # NaN compares False
        above_n = int((v[X] > v["NEU"]).sum())
        out["budget_mean"][name] = {**{arm: float(np.nanmean(v[arm])) for arm in arms},
                                    f"{X.lower()}_above_abund": above_a,
                                    f"{X.lower()}_above_neu": above_n}
        n_x = int(np.isfinite(v[X]).sum())
        print(f"  {name:10s} {np.nanmean(v[X]):.3f} / {np.nanmean(v['ABUND']):.3f} / "
              f"{np.nanmean(v['NEU']):.3f}   above ABUND {above_a}/{n_x}, "
              f"above NEU {above_n}/{n_x}")

    print(f"\nepochs, last 10 ({X.lower()} minus H-h, each line in its own world) against the "
          "garden")
    pre = ana["pre_evolution"]
    evo = Path(ana["evo"])
    xf, xt, yf, yt = [], [], [], []
    for lin in LINEAGES:
        q = pre[str(lin)]
        ef = q["forage_decisions_last10"] - q["abund_forage_decisions_last10"]
        if chk == "M":  # the check's share: FORAGE and DRINK of the executed decisions
            def drink(path: Path) -> float:
                return float(np.mean([r["decision_action_shares"][ACT_DRINK]
                                      for r in epoch_rows(path)[-10:]]))
            ef += (drink(evo_s / f"lineage_{lin}" / "epochs.jsonl")
                   - drink(evo / f"lineage_{lin}" / "epochs.jsonl"))
        et = q["free_decisions_last10"] - q["abund_free_decisions_last10"]
        gf = ana["manipulation_check"]["d"].get(str(lin))
        gt = ana[hyp]["d"].get(str(lin))
        if gf is None or gt is None:
            print(f"  l{lin}: no garden pair")
            continue
        xf.append(ef)
        xt.append(et)
        yf.append(gf)
        yt.append(gt)
        out["epochs_vs_garden"][str(lin)] = {"epochs_forage": ef, "epochs_free": et,
                                             "garden_dF": gf, "garden_dT": gt}
        name = "FORAGE" if chk == "F" else "FORAGE+DRINK"
        print(f"  l{lin}: epochs {name} {ef:+.3f} free {et:+.3f} | garden d{chk} {gf:+.3f} "
              f"dT {gt:+.3f}")
    rf, rt = float(np.corrcoef(xf, yf)[0, 1]), float(np.corrcoef(xt, yt)[0, 1])
    out["epochs_vs_garden"]["r_forage"], out["epochs_vs_garden"]["r_free"] = rf, rt
    print(f"  correlation over {len(xf)} lineages: {name} {rf:+.2f}, free time {rt:+.2f}")

    keys = PROBES + (THIRST if chk == "M" else ())
    print(f"\n{X.lower()} epochs over evolution (first / middle / last 10): weaned on day 360, "
          "weaned, hunger, hungry and starving shares (second half), worst day starving"
          + (", thirst-starving (second half, worst day)" if chk == "M" else "")
          + ", N on day 360")
    for lin in LINEAGES:
        pc = probe_course(evo_s, lin, keys)
        out["probes"][str(lin)] = pc
        for part, rec in pc.items():
            print(f"  l{lin} {part:8s} " + " ".join(f"{rec[k]:8.4f}" for k in keys)
                  + f" {rec['n_end']:6.0f}")
    name = "scarce_beside.json" if a.regime == "scarce" else f"{a.regime}_beside.json"
    (sweep / name).write_text(json.dumps(out, default=float, indent=1), encoding="utf-8")
    print(f"\nwrote {sweep / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
