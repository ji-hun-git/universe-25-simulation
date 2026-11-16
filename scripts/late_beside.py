#!/usr/bin/env python
"""Exploratory readings beside H-l (NOTES 2026-11-16; written after the run, not decisive; no
rule, threshold or stored output changes). From the outputs of evolve_scarce.py (late_full and
late_small), sweep_scarce.py --regime late and analyse_late.py:
- the run's size: epochs, NaN counts, the lineages' wall time and the garden runs' timing;
- the eligible decisions over evolution, for each line: each action's share, the mean of the
  lineages' first 10 and last 10 epochs, and the lineages where it rose;
- the whole budget in the garden: each action's share of the eligible rows per lineage (the mean
  over a run's entered windows, then over the lineage's runs), its mean over the lineages per
  arm, and the lineages with LS above LF;
- per garden run: the entered windows, the peak, the last young, and N on days 1,444 and 1,588.
Writes _output/late_sweep/late_beside.json.

usage: python scripts/late_beside.py [--sweep DIR] [--late-full DIR] [--late-small DIR]
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

from analyse_scarce import ACTION_NAMES  # noqa: E402
from scarce_beside import run_budget  # noqa: E402

ARMS = ("LS", "LF", "ABUND", "NEU")
LINES = {"LF": "evo_late_full", "LS": "evo_late_small"}
LINEAGES = tuple(range(1, 9))
SEED0 = 9961


def epoch_rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sweep", default=str(ROOT / "_output" / "late_sweep"))
    p.add_argument("--late-full", default=str(ROOT / "_output" / LINES["LF"]))
    p.add_argument("--late-small", default=str(ROOT / "_output" / LINES["LS"]))
    a = p.parse_args()
    sweep = Path(a.sweep)
    evo = {"LF": Path(a.late_full), "LS": Path(a.late_small)}
    ana = json.loads((sweep / "late_analysis.json").read_text(encoding="utf-8"))
    out: dict = {"sweep": str(sweep), "evo": {k: str(v) for k, v in evo.items()}}

    # The run's size.
    size = {}
    for line, d in evo.items():
        n_ep = nan = 0
        wall = 0.0
        for lin in LINEAGES:
            rows = epoch_rows(d / f"lineage_{lin}" / "epochs.jsonl")
            n_ep += len(rows)
            nan += sum(int(r.get("nan_count", 0)) for r in rows)
            wall += sum(float(r.get("wall_s", 0.0)) for r in rows)
        size[line] = {"epochs": n_ep, "nan_count": nan, "cpu_h": wall / 3600.0}
        print(f"{line}: {n_ep} epochs over 8 lineages, NaN count {nan}, "
              f"{wall / 3600.0:.1f} CPU-h (sum of the epochs' wall time)")
    runs = {}
    for arm in ARMS:
        for lin in LINEAGES:
            for s in (SEED0 + 2 * (lin - 1), SEED0 + 2 * (lin - 1) + 1):
                f = sweep / f"{arm}_l{lin}_{s}" / "scarce_run.json"
                if f.exists():
                    runs[(arm, lin, s)] = json.loads(f.read_text(encoding="utf-8"))
    garden_s = sum(float(sum(r.get("timing", {}).values())) for r in runs.values())
    size["garden"] = {"runs": len(runs), "cpu_h": garden_s / 3600.0}
    print(f"garden: {len(runs)} runs, {garden_s / 3600.0:.1f} CPU-h (sum of the runs' timing)")
    out["size"] = size

    # The eligible decisions over evolution, per line.
    print("\nEligible decisions over evolution (each action's share; mean of the 8 lineages' "
          "first 10 and last 10 epochs; lineages where it rose)")
    evo_tab = {}
    for line in ("LF", "LS"):
        f10 = np.array([ana["pre_evolution"][f"{line}/{lin}"]["eligible_first10"]
                        for lin in LINEAGES], dtype=np.float64)
        l10 = np.array([ana["pre_evolution"][f"{line}/{lin}"]["eligible_last10"]
                        for lin in LINEAGES], dtype=np.float64)
        tab = {}
        for i, name in enumerate(ACTION_NAMES):
            tab[name] = {"first10": float(f10[:, i].mean()), "last10": float(l10[:, i].mean()),
                         "rose": int((l10[:, i] > f10[:, i]).sum())}
        evo_tab[line] = tab
    print(f"  {'action':<11}" + "".join(f"{h:>12}" for h in
                                         ("LF first10", "LF last10", "LF rose", "LS first10",
                                          "LS last10", "LS rose")))
    order = sorted(ACTION_NAMES, key=lambda n: -evo_tab["LS"][n]["last10"])
    for name in order:
        lf, ls = evo_tab["LF"][name], evo_tab["LS"][name]
        print(f"  {name:<11}{lf['first10']:>12.3f}{lf['last10']:>12.3f}{lf['rose']:>12d}"
              f"{ls['first10']:>12.3f}{ls['last10']:>12.3f}{ls['rose']:>12d}")
    out["eligible_over_evolution"] = evo_tab
    print("  per lineage, last 10 epochs: M, T, the weaned animals' mean hunger (second half), "
          "and the largest rise of an action")
    per_lin_evo = {}
    for line in ("LF", "LS"):
        for lin in LINEAGES:
            r = ana["pre_evolution"][f"{line}/{lin}"]
            d = (np.asarray(r["eligible_last10"]) - np.asarray(r["eligible_first10"]))
            k = int(np.argmax(d))
            per_lin_evo[f"{line}/{lin}"] = {
                "M_last10": r["eligible_M_last10"], "T_last10": r["eligible_T_last10"],
                "hunger_last10": r["hunger_2h_last10"],
                "thirst_starving_last10": r["thirst_starving_2h_last10"],
                "thirst_starving_max_last10": r["thirst_starving_max_last10"],
                "largest_rise": [ACTION_NAMES[k], float(d[k])]}
            print(f"    {line} l{lin}: M {r['eligible_M_last10']:.3f}, T "
                  f"{r['eligible_T_last10']:.3f}, hunger {r['hunger_2h_last10']:.3f}, thirst > "
                  f"1.2 {100 * r['thirst_starving_2h_last10']:.2f} % (worst day "
                  f"{100 * r['thirst_starving_max_last10']:.1f} %), largest rise "
                  f"{ACTION_NAMES[k]} {d[k]:+.3f}")
    out["per_lineage_evolution"] = per_lin_evo

    # The whole budget in the garden.
    per = {}
    for arm in ARMS:
        for lin in LINEAGES:
            bs = [run_budget(r)[0] for (a_, l_, _), r in runs.items() if a_ == arm and l_ == lin]
            bs = [b for b in bs if np.isfinite(b).all()]
            per[(arm, lin)] = np.mean(bs, axis=0) if bs else np.full(len(ACTION_NAMES), np.nan)
    budget = {}
    print("\nWhole budget in the garden (each action's share of the eligible rows; mean over the "
          "lineages; lineages with LS above LF)")
    print(f"  {'action':<11}" + "".join(f"{x:>8}" for x in ARMS) + "  LS > LF")
    mean = {arm: np.nanmean(np.array([per[(arm, lin)] for lin in LINEAGES]), axis=0)
            for arm in ARMS}
    for i in np.argsort(-mean["LS"]):
        name = ACTION_NAMES[i]
        both = [lin for lin in LINEAGES if np.isfinite(per[("LS", lin)][i])
                and np.isfinite(per[("LF", lin)][i])]
        above = sum(per[("LS", lin)][i] > per[("LF", lin)][i] for lin in both)
        budget[name] = {arm: float(mean[arm][i]) for arm in ARMS}
        budget[name]["LS_above_LF"] = [int(above), len(both)]
        print(f"  {name:<11}" + "".join(f"{mean[arm][i]:>8.3f}" for arm in ARMS)
              + f"  {above} of {len(both)}")
    out["budget_lineage_mean"] = budget
    out["budget_per_lineage"] = {f"{arm}/{lin}": [float(x) for x in per[(arm, lin)]]
                                 for arm in ARMS for lin in LINEAGES}

    # Per garden run.
    print("\nPer garden run: entered windows, peak (day), last young, N@1,444, N@1,588")
    per_run = {}
    for (arm, lin, s), r in sorted(runs.items(), key=lambda kv: (ARMS.index(kv[0][0]),
                                                                  kv[0][1], kv[0][2])):
        lm = r["landmarks"]
        ent = sum(bool(w.get("entered")) for w in r["windows"])
        per_run[f"{arm}_l{lin}_{s}"] = {"entered": ent, **{k: lm.get(k) for k in (
            "n_at_day_315", "peak_n", "peak_day", "last_young_day", "last_conception_day",
            "n_at_day_1444", "n_at_day_1588")}}
        print(f"  {arm:<5} l{lin} {s}: entered {ent:2d}, N@315 {lm.get('n_at_day_315')}, peak "
              f"{lm.get('peak_n')} ({lm.get('peak_day')}), last young {lm.get('last_young_day')},"
              f" N@1,444 {lm.get('n_at_day_1444')}, N@1,588 {lm.get('n_at_day_1588')}")
    out["per_run"] = per_run
    dst = sweep / "late_beside.json"
    dst.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
