#!/usr/bin/env python
"""U-5 development look (docs/DEPRIVED_GENERATION.md, "Development look", fixed before code).

The final replica's parameters (configs/replica_v2_final.json) in Calhoun's pen, training seeds
7000-7011, 1,600 days, four arms:
  A0  deprivation off (today)
  A1  on, with the a priori values
  A2  A1 with litter_abandon_p doubled (more expulsion)
  A3  A1 with deprived_factor 0.2 (stronger deprivation)
Reported per arm as seed medians [5-95 %]: the 14 record targets (adults counted as Calhoun did),
the arc count, never fought as adults or mated (131-320 days old, day 800), the withdrawn share on
day 560, the deprived shares, conceptions after day 920, and the structure question:
  the arc in at least 8 of 12 seeds, with a last conception by day 1,000, never fought or mated
  0.38-0.68 and withdrawn on day 560 0.22-0.42 (seed medians).
This is development on training seeds, not validation.

Revision 1 (--set r1): B0 off, B1 + deprived_fertility 0.01, B2 + expel_at_independence, B3 both.
Revision 2 (--set r2): C0 off; C1 deprivation + deprived_fertility 0.01 + colony_rejection (with
the ratchet); C2 C1 without the ratchet; C3 C1 with breakdown_density_threshold 0.48. The same
base, seeds and question in every set.
Revision 3 (--set r3): D0 off; D1 C1 + rejection_all_boxes; D2 D1 without the ratchet; D3 D1 with
breakdown_density_threshold 0.68.
Revision 4 (--set r4): E0 off; E1 D1 + rejection_stress (social_breakdown_stress_boost 0.248, the
config's); E2 E1 with the boost 0.152 (the frozen colony's stress level); E3 E1 with
breakdown_density_threshold 0.68. Every set also reports the gap (last conception - last
surviving birth).

usage: python scripts/deprivation_look.py [--workers 10] [--set v1|r1|r2|r3|r4]
Writes _output/deprivation_look.json (v1) or _output/deprivation_look_<set>.json.
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
sys.path.insert(0, str(ROOT / "scripts"))

import history_match as hm  # noqa: E402
import history_match_rep as hmr  # noqa: E402

SEEDS = tuple(range(7000, 7012))
FINAL = ROOT / "configs" / "replica_v2_final.json"
FOURTEEN = ["first_litters_day", "n_at_day_315", "adults_at_day_315", "peak_n",
            "plateau_onset_day", "n_at_day_736", "n_at_day_811", "n_at_day_960", "doubling_b",
            "doubling_c", "last_young_day", "last_conception_day", "n_at_day_1444",
            "n_at_day_1588"]
READ = {"adults_at_day_315": "adults_131_at_day_315"}  # Calhoun's adults (U-3)
CONTESTED = {"first_litters_day": (50.0, 104.0), "doubling_c": (105.0, 145.0)}


SET = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "v1"


def arms() -> dict[str, dict]:
    """v1: the first look (A0-A3); revisions 1-4: B0-B3, C0-C3, D0-D3, E0-E3
    (docs/DEPRIVED_GENERATION.md)."""
    params = json.loads(FINAL.read_text(encoding="utf-8"))["members"][0]["params"]
    bio = params["biology"]

    def with_bio(**kw):
        return {**params, "biology": {**bio, **kw}}

    if SET == "r4":
        rev4 = dict(deprivation=True, deprived_fertility=0.01, colony_rejection=True,
                    rejection_all_boxes=True, rejection_stress=True)
        frozen = 0.24829430244099573 * 0.5604105404723718 / 0.9135074926585873  # 0.152
        return {"E0": params,
                "E1": with_bio(**rev4),
                "E2": with_bio(**rev4, social_breakdown_stress_boost=frozen),
                "E3": with_bio(**rev4, breakdown_density_threshold=0.68)}
    if SET == "r3":
        rev3 = dict(deprivation=True, deprived_fertility=0.01, colony_rejection=True,
                    rejection_all_boxes=True)
        return {"D0": params,
                "D1": with_bio(**rev3),
                "D2": with_bio(**rev3, rejection_ratchet=False),
                "D3": with_bio(**rev3, breakdown_density_threshold=0.68)}
    if SET == "r2":
        rev2 = dict(deprivation=True, deprived_fertility=0.01, colony_rejection=True)
        return {"C0": params,
                "C1": with_bio(**rev2),
                "C2": with_bio(**rev2, rejection_ratchet=False),
                "C3": with_bio(**rev2, breakdown_density_threshold=0.48)}
    if SET == "r1":
        return {"B0": params,
                "B1": with_bio(deprivation=True, deprived_fertility=0.01),
                "B2": with_bio(deprivation=True, expel_at_independence=True),
                "B3": with_bio(deprivation=True, deprived_fertility=0.01,
                               expel_at_independence=True)}
    return {"A0": params,
            "A1": with_bio(deprivation=True),
            "A2": with_bio(deprivation=True, litter_abandon_p=2.0 * bio["litter_abandon_p"]),
            "A3": with_bio(deprivation=True, deprived_factor=0.2)}


def run(job: tuple[str, dict, int]) -> dict:
    from replica_report import run_one

    arm, over, seed = job
    _, _, r = run_one(("look", "replica_v2.yaml", over, seed, 1600.0))
    o = hm.outputs(r)
    s560, s800 = r["struct"].get("560", {}), r["struct"].get("800", {})
    return {"arm": arm, "seed": seed, "outputs": o,
            "deprived_share_560": s560.get("deprived_share", np.nan),
            "deprived_131_320_800": s800.get("deprived_131_320", np.nan),
            "conceptions_after_920": r["conceptions_after_920"],
            "rejection_onset": r.get("rejection_onset"),
            "rejection_f_max": r.get("rejection_f_max", 0.0)}


def q(v: list[float]) -> list[float]:
    x = np.asarray(v, float)
    x = x[np.isfinite(x)]
    return np.quantile(x, [0.05, 0.5, 0.95]).tolist() if x.size else [np.nan] * 3


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--set", choices=("v1", "r1", "r2", "r3", "r4"), default="v1",
                   help="v1: the first look (A0-A3); r1-r4: revisions 1-4 (B, C, D, E arms)")
    a = p.parse_args()
    jobs = [(arm, over, s) for arm, over in arms().items() for s in SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(run, jobs))
    print(f"{len(rows)} runs in {time.perf_counter() - t0:.0f} s")
    summary = {}
    for arm in arms():
        rs = [r for r in rows if r["arm"] == arm]
        outs = [r["outputs"] for r in rs]
        t = {}
        inside = 0
        for name in FOURTEEN:
            qq = q([o.get(READ.get(name, name), np.nan) for o in outs])
            z = hm.OUTPUTS[name][0]
            lo, hi = CONTESTED.get(name, (z, z))
            ok = bool(qq[0] <= hi and lo <= qq[2])
            inside += ok
            t[name] = {"q": qq, "inside_12": ok}
        arc = sum(hmr.is_arc(o) for o in outs)
        extra = {
            "beautiful_800_adult": q([o.get("beautiful_800_adult", np.nan) for o in outs]),
            "withdrawn_560": q([o.get("withdrawn_560", np.nan) for o in outs]),
            "deprived_share_560": q([r["deprived_share_560"] for r in rs]),
            "deprived_131_320_800": q([r["deprived_131_320_800"] for r in rs]),
            "conceptions_after_920": q([r["conceptions_after_920"] for r in rs]),
            "rejection_onset": q([r["rejection_onset"] if r.get("rejection_onset") is not None
                                  else np.nan for r in rs]),
            "rejection_f_max": q([r.get("rejection_f_max", 0.0) for r in rs]),
            "gap": q([o.get("last_conception_day", np.nan) - o.get("last_young_day", np.nan)
                      for o in outs]),
        }
        lc = t["last_conception_day"]["q"][1]
        bf = extra["beautiful_800_adult"][1]
        wd = extra["withdrawn_560"][1]
        answer = bool(arc >= 8 and lc <= 1000.0 and 0.38 <= bf <= 0.68 and 0.22 <= wd <= 0.42)
        summary[arm] = {"targets": t, "inside_of_14_on_12_seeds": inside, "arc": arc, **extra,
                        "structure": {"arc_ge_8": arc >= 8, "last_conception_le_1000": lc <= 1000,
                                      "beautiful_038_068": 0.38 <= bf <= 0.68,
                                      "withdrawn_022_042": 0.22 <= wd <= 0.42, "yes": answer}}
    names = list(summary)
    def f(x: float) -> str:
        return f"{x:.2f}"

    print("\n| measure | record | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    for name in FOURTEEN:
        cells = []
        for arm in names:
            qq = summary[arm]["targets"][name]["q"]
            fmt = f if abs(qq[1]) < 2 else (lambda x: f"{x:,.0f}")
            cells.append(f"{fmt(qq[1])} [{fmt(qq[0])}, {fmt(qq[2])}]"
                         + ("" if summary[arm]["targets"][name]["inside_12"] else " *"))
        print(f"| {name} | {hm.OUTPUTS[name][0]:g} | " + " | ".join(cells) + " |")
    print("| inside, of 14 (12 seeds) | | " + " | ".join(
        str(summary[arm]["inside_of_14_on_12_seeds"]) for arm in names) + " |")
    print("| the arc, of 12 | | " + " | ".join(str(summary[arm]["arc"]) for arm in names) + " |")
    for key, rec in (("beautiful_800_adult", "0.53"), ("withdrawn_560", "0.32"),
                     ("deprived_share_560", "-"), ("deprived_131_320_800", "-"),
                     ("conceptions_after_920", "0"), ("rejection_onset", "437"),
                     ("rejection_f_max", "-"), ("gap", "320")):
        cells = []
        for arm in names:
            qq = summary[arm][key]
            fmt = (f if key not in ("conceptions_after_920", "rejection_onset", "gap")
                   else (lambda x: f"{x:,.0f}"))
            cells.append(f"{fmt(qq[1])} [{fmt(qq[0])}, {fmt(qq[2])}]")
        print(f"| {key} | {rec} | " + " | ".join(cells) + " |")
    print("\nstructure question (seed medians): the arc >= 8 of 12, last conception <= 1,000, "
          "never fought or mated 0.38-0.68, withdrawn on day 560 0.22-0.42")
    for arm in names:
        s = summary[arm]["structure"]
        print(f"  {arm}: " + ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in s.items()))
    name = "deprivation_look.json" if SET == "v1" else f"deprivation_look_{SET}.json"
    (ROOT / "_output" / name).write_text(json.dumps(
        {"set": SET, "seeds": list(SEEDS), "summary": summary, "rows": rows}, indent=1,
        default=float), encoding="utf-8")
    print(f"\nwritten _output/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
