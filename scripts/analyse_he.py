#!/usr/bin/env python
"""H-e analysis (PLAN.md section 15.1, amendment adopted 2026-11-08) of _output/he_sweep.

Unit: one traced window of one run (policy x food x seed x window). Dose: the relaxed share of
weaned rows. Response: per episode kind, the number of the five v5 decision flags met (C).
Primary (learned net, per kind): Kendall tau-b of C on dose within window strata, mean over the
three strata (T), dose permuted within strata (10,000 permutations, seed 0), one-sided p;
supported if T > 0 and p < 0.025, not supported if T > 0 and p >= 0.025, falsified if T <= 0.
H-e supported if either kind is supported, falsified if both are falsified.
Reported beside it, not decisive: the same test for both control policies; every flag and its
statistic against dose; episodes per weaned individual-decision and the episode count against
dose (a dose-response that only follows episode count reads as a power effect); and the food
contrast abund - scarce in C, paired by seed and window, with the dose difference beside it.

The preregistered test reads the v5 flags (from a v6 detector file, its decisions_v5 copy, whose
statistics are identical); --flags v6 re-reads the same units with the v6 flags (exploratory,
written to he_analysis_v6flags.json).

usage: python scripts/analyse_he.py [--sweep _output/he_sweep] [--perm 10000] [--flags v5|v6]
Writes <sweep>/he_analysis.json and prints the tables.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.metrics.dose_response import paired_mean_se, stratified_tau_test  # noqa: E402

ALPHA = 0.025
K = 12  # free-time sub-steps per decision in the sweep (rows per decision)
POLICIES = ("learned", "need_driven", "random")
KINDS = ("object", "locomotor")
FLAGS = ("c1_not_functional", "c2_spontaneous", "c3_structurally_different",
         "c4_repeated_not_rigid", "c5_relaxed_field")
STATS = ("nf_index_unvalidated", "onset_trigger_free_unvalidated",
         "seq_struct_reversal_unvalidated", "rep_rigid_loop_frac_unvalidated",
         "rep_exposure_slope_unvalidated", "gate_relaxed_log_ratio_unvalidated")


def load_units(sweep: Path, flag_set: str = "v5") -> list[dict]:
    units = []
    key = {"v5": {"v5": "decisions_unvalidated", "v6": "decisions_v5_unvalidated",
                  "v7": "decisions_v5_unvalidated", "v8": "decisions_v5_unvalidated"},
           "v6": {"v6": "decisions_unvalidated", "v7": "decisions_v6_unvalidated",
                  "v8": "decisions_v6_unvalidated"},
           "v7": {"v7": "decisions_unvalidated", "v8": "decisions_v7_unvalidated"},
           "v8": {"v8": "decisions_unvalidated"}}[flag_set]
    for d in sorted(p for p in sweep.iterdir() if p.is_dir()):
        f = d / "detectors_unvalidated.json"
        if not f.exists():
            continue
        det = json.loads(f.read_text(encoding="utf-8"))
        if det.get("rules") not in key:
            raise SystemExit(f"{f}: rules {det.get('rules')!r} carry no {flag_set} flags")
        fkey = key[det["rules"]]
        policy, food, seed = d.name.rsplit("_", 2)
        for wkey, res in det["windows"].items():
            u = {"policy": policy, "food": food, "seed": int(seed),
                 "window": float(wkey.split("_")[1]), "dose": res["relaxed_share_weaned"],
                 "n_rows_weaned": res["n_rows_weaned"]}
            dec = max(1.0, res["n_rows_weaned"] / K)
            for kind in KINDS:
                r = res[kind]
                flags = r[fkey]
                u[f"{kind}:C"] = int(sum(bool(flags[k]) for k in FLAGS))
                u[f"{kind}:n_episodes"] = int(r["n_episodes"])
                u[f"{kind}:rate"] = float(r["n_episodes"]) / dec
                for k in FLAGS:
                    u[f"{kind}:{k}"] = int(bool(flags[k]))
                for k in STATS:
                    u[f"{kind}:{k}"] = float(r.get(k, float("nan")))
            units.append(u)
    return units


def verdict(T: float, p: float) -> str:
    if T <= 0:
        return "falsified"
    return "supported" if p < ALPHA else "not supported"


def test(units: list[dict], key: str, n_perm: int) -> dict:
    ok = [u for u in units if np.isfinite(u[key]) and np.isfinite(u["dose"])]
    if len(ok) < 4:
        return {"T": float("nan"), "p_one_sided": float("nan"), "n_units": len(ok)}
    return stratified_tau_test([u["dose"] for u in ok], [u[key] for u in ok],
                               [u["window"] for u in ok], n_perm=n_perm, seed=0)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", type=str, default=str(ROOT / "_output" / "he_sweep"))
    p.add_argument("--perm", type=int, default=10_000)
    p.add_argument("--flags", choices=("v5", "v6", "v7", "v8"), default="v5")
    a = p.parse_args()
    sweep = Path(a.sweep)
    units = load_units(sweep, a.flags)
    report: dict = {"n_units": len(units), "alpha_one_sided": ALPHA, "flags": a.flags, "doses": {},
                    "primary": {}, "secondary": {}, "food_contrast": {}}
    print(f"{len(units)} window units from {sweep}")

    print("\n## Dose (relaxed share of weaned rows): mean ± se over seeds")
    print("| policy | food | " + " | ".join(f"day {w:g}" for w in (400, 700, 1000)) + " |")
    print("|---|---|---:|---:|---:|")
    for pol in POLICIES:
        for food in ("abund", "scarce"):
            cells = []
            for w in (400.0, 700.0, 1000.0):
                v = np.array([u["dose"] for u in units if u["policy"] == pol
                              and u["food"] == food and u["window"] == w], float)
                se = v.std(ddof=1) / np.sqrt(v.size) if v.size > 1 else float("nan")
                report["doses"][f"{pol}:{food}:{w:g}"] = {"mean": float(np.mean(v)) if v.size
                                                         else float("nan"), "se": float(se),
                                                         "n": int(v.size)}
                cells.append(f"{np.mean(v):.3f} ± {se:.3f} (n={v.size})" if v.size else "–")
            print(f"| {pol} | {food} | " + " | ".join(cells) + " |")

    print("\n## Primary: criteria count C on dose (Kendall tau-b within window strata)")
    print("| policy | kind | T | tau by window (400 / 700 / 1000) | p (one-sided) | reading |")
    print("|---|---|---:|---|---:|---|")
    for pol in POLICIES:
        pu = [u for u in units if u["policy"] == pol]
        for kind in KINDS:
            r = test(pu, f"{kind}:C", a.perm)
            r["verdict"] = verdict(r["T"], r["p_one_sided"]) if np.isfinite(r["T"]) else "n/a"
            report["primary"][f"{pol}:{kind}"] = r
            taus = " / ".join(f"{v:+.2f}" for v in r.get("tau_by_stratum", {}).values())
            role = "primary" if pol == "learned" else "control"
            print(f"| {pol} ({role}) | {kind} | {r['T']:+.3f} | {taus} | "
                  f"{r['p_one_sided']:.4f} | {r['verdict']} |")
    lk = [report["primary"][f"learned:{k}"]["verdict"] for k in KINDS]
    overall = ("supported" if "supported" in lk else
               "falsified" if all(v == "falsified" for v in lk) else
               "untested" if all(v == "n/a" for v in lk) else "not supported")
    report["H_e"] = overall
    print(f"\n**H-e (learned net): {overall}** (object: {lk[0]}, locomotor: {lk[1]})")

    print("\n## Secondary: each flag, statistic, episode rate and count on dose (T, p)")
    keys = [*FLAGS, *STATS, "rate", "n_episodes"]
    print("| policy | kind | " + " | ".join(k.replace("_unvalidated", "") for k in keys) + " |")
    print("|---|---|" + "---:|" * len(keys))
    for pol in POLICIES:
        pu = [u for u in units if u["policy"] == pol]
        for kind in KINDS:
            cells = []
            for k in keys:
                r = test(pu, f"{kind}:{k}", a.perm)
                report["secondary"][f"{pol}:{kind}:{k}"] = r
                cells.append(f"{r['T']:+.2f} ({r['p_one_sided']:.3f})"
                             if np.isfinite(r["T"]) else "–")
            print(f"| {pol} | {kind} | " + " | ".join(cells) + " |")

    print("\n## Food contrast abund − scarce, paired by seed and window (mean ± se)")
    print("| policy | kind | Δ dose | Δ C | Δ episodes per weaned decision | flags met: abund / "
          "scarce (c1..c5 rates) |")
    print("|---|---|---:|---:|---:|---|")
    for pol in POLICIES:
        for kind in KINDS:
            ab = {(u["seed"], u["window"]): u for u in units
                  if u["policy"] == pol and u["food"] == "abund"}
            sc = {(u["seed"], u["window"]): u for u in units
                  if u["policy"] == pol and u["food"] == "scarce"}
            common = sorted(set(ab) & set(sc))
            if not common:
                continue
            dd = paired_mean_se([ab[c]["dose"] for c in common], [sc[c]["dose"] for c in common])
            dc = paired_mean_se([ab[c][f"{kind}:C"] for c in common],
                                [sc[c][f"{kind}:C"] for c in common])
            dr = paired_mean_se([ab[c][f"{kind}:rate"] for c in common],
                                [sc[c][f"{kind}:rate"] for c in common])
            fa = [np.mean([ab[c][f"{kind}:{k}"] for c in common]) for k in FLAGS]
            fs = [np.mean([sc[c][f"{kind}:{k}"] for c in common]) for k in FLAGS]
            report["food_contrast"][f"{pol}:{kind}"] = {
                "d_dose": dd, "d_C": dc, "d_rate": dr, "flags_abund": dict(zip(FLAGS, fa)),
                "flags_scarce": dict(zip(FLAGS, fs))}
            print(f"| {pol} | {kind} | {dd['mean']:+.3f} ± {dd['se']:.3f} | "
                  f"{dc['mean']:+.2f} ± {dc['se']:.2f} | {dr['mean']:+.4f} ± {dr['se']:.4f} | "
                  + " ".join(f"{v:.2f}" for v in fa) + " / " + " ".join(f"{v:.2f}" for v in fs)
                  + " |")
    out = sweep / ("he_analysis.json" if a.flags == "v5" else f"he_analysis_{a.flags}flags.json")
    out.write_text(json.dumps({"report": report, "units": units}, indent=1, default=float),
                   encoding="utf-8")
    print(f"\nwritten {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
