#!/usr/bin/env python
"""What criterion 3's locomotor form test reads on nets (exploratory; NOTES 2026-11-14).

Rebuilds the locomotor episodes of every locomotor reading of the H-i sweep (_output/nm_sweep)
and the H-h sweep (_output/evo_sweep) exactly as the rules-v9 detector builds them: at most 400
individuals drawn with rng seed 17, v7's displacement threshold, the gap criterion and the
segmentation. Each detector window counts once. For each reading it reports:
- the primitive mix of the episodes' own event rows (EXPLORE, RUN_ON, TURN_BACK);
- the reversal fraction (checked against the stored value) and, per direction pair, the
  reversal rate by the move that closes the pair;
- the repeat excess: P(same primitive as the previous own row) minus the sum of squared shares
  (about 0 when the moves are independent of the previous one);
- the TURN_BACK share in relaxed rows minus that in the other rows;
- the stored flags, the form excess against the even mix and the order diagnostic's excess.
Object readings with criterion 3 are listed from the stored fields.

No rule, threshold or stored output changes. Writes _output/form_mix.json.

usage: python scripts/form_mix.py [--workers 6] [--sweeps nm_sweep evo_sweep] [--out F]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SWEEPS = ("nm_sweep", "evo_sweep")
OUT = ROOT / "_output" / "form_mix.json"
MAX_INDIVIDUALS, PREPARE_SEED = 400, 17  # as detect_trace(seed=0, max_individuals=400)
PRIMS = ("EX", "RO", "TB")
STORED = ("seq_struct_reversal_unvalidated", "seq_struct_form_null_mean_unvalidated",
          "seq_struct_form_excess_unvalidated", "seq_struct_form_z_unvalidated",
          "seq_struct_order_excess_unvalidated", "seq_struct_order_z_unvalidated")


def _share(a: np.ndarray, codes: tuple[int, ...]) -> dict[str, float]:
    n = max(int(a.size), 1)
    return {p: float((a == c).sum() / n) for p, c in zip(PRIMS, codes)}


def rebuild(job: tuple[str, str, str]) -> dict:
    """One locomotor reading: the episodes' own rows and their primitive mix."""
    sweep, run, mid = job
    from universe25.agents.state import ACT_EXPLORE, ACT_RUN_ON, ACT_TURN_BACK
    from universe25.metrics import detectors as D
    from universe25.metrics.trace import load_trace

    codes = (ACT_EXPLORE, ACT_RUN_ON, ACT_TURN_BACK)
    a = float(mid) - 5.0
    tr = load_trace(ROOT / "_output" / sweep / run / f"trace_{a:g}_{a + 10.0:g}.npz")
    S = D.prepare(tr, max_individuals=MAX_INDIVIDUALS,
                  rng=np.random.default_rng(PREPARE_SEED))
    ev, thr = D.event_mask(S, "locomotor", fixed=False)
    dpd = int(np.asarray(tr.get("meta", {}).get("decisions_per_day", 6)))
    c, _ = D.gap_criterion(S, ev, max_gap=dpd)
    s, e, _ = D.segment(S, ev, c)
    rows, seq, own, d = D._form_labels(S, ev, s, e)
    link = seq[:-1] == seq[1:]
    act = S.action[rows]
    pair = link & (d[:-1] != 0) & (d[1:] != 0)  # the reversal fraction's direction pairs
    closer, flip = act[1:][pair], (d[:-1] != d[1:])[pair]
    cons = link & own[:-1] & own[1:]  # consecutive own rows of an episode
    mix = _share(act[own], codes)
    repeat = float((act[1:][cons] == act[:-1][cons]).mean()) if cons.any() else float("nan")
    rel = S.relaxed[rows]
    tb = act == ACT_TURN_BACK
    tb_rel = float(tb[own & rel].mean()) if (own & rel).any() else float("nan")
    tb_not = float(tb[own & ~rel].mean()) if (own & ~rel).any() else float("nan")
    return {
        "sweep": sweep, "run": run, "arm": run.split("_")[0], "mid": mid, "threshold": thr,
        "n_episodes": int(s.size), "n_own": int(own.sum()), "n_pairs": int(pair.sum()),
        "reversal": D._reversal_frac(d, link), "mix": mix,
        "closer_share": _share(closer, codes),
        "closer_reversal": {p: float(flip[closer == cc].mean()) if (closer == cc).any()
                            else float("nan") for p, cc in zip(PRIMS, codes)},
        "repeat_excess": repeat - float(sum(v * v for v in mix.values())),
        "tb_relaxed_minus_not": tb_rel - tb_not,
        "own_relaxed_share": float(rel[own].mean()) if own.any() else float("nan"),
    }


def readings(sweeps: tuple[str, ...] = SWEEPS
             ) -> tuple[list[tuple[str, str, str]], dict, list[dict]]:
    """Locomotor jobs (each window once, at least 10 episodes), their stored records, and the
    object readings with criterion 3 met."""
    jobs, stored, obj = [], {}, []
    for sweep in sweeps:
        base = ROOT / "_output" / sweep
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            f = d / "evo_detect.json"
            if not f.exists():
                continue
            det = json.loads(f.read_text(encoding="utf-8"))
            for mid, rec in det.items():
                for kind in ("locomotor", "object"):
                    r = rec.get(kind) or {}
                    if int(r.get("n_episodes", 0)) < 10:
                        continue
                    flags = r["decisions_unvalidated"]
                    keep = {k: float(r.get(k, np.nan)) for k in STORED}
                    keep.update(c3=bool(flags["c3_structurally_different"]),
                                c4=bool(flags["c4_repeated_not_rigid"]))
                    if kind == "locomotor":
                        jobs.append((sweep, d.name, mid))
                        stored[(sweep, d.name, mid)] = keep
                    elif keep["c3"]:
                        obj.append({"sweep": sweep, "run": d.name, "mid": mid, **keep})
    return jobs, stored, obj


def _q(v) -> str:
    x = np.asarray(v, dtype=float)
    x = x[np.isfinite(x)]
    if not x.size:
        return "-"
    return f"{np.median(x):+.3f} [{x.min():+.3f}, {x.max():+.3f}]"


def report(res: list[dict], obj: list[dict], sweeps: tuple[str, ...] = SWEEPS) -> dict:
    out: dict = {}
    rev = np.array([r["reversal"] for r in res])
    st = np.array([r["seq_struct_reversal_unvalidated"] for r in res])
    ok = np.isfinite(rev) & np.isfinite(st)
    out["rebuilt_vs_stored_max_abs"] = float(np.max(np.abs(rev[ok] - st[ok]))) if ok.any() else None
    print(f"readings: {len(res)} locomotor (each window once); rebuilt vs stored reversal: "
          f"max |diff| {out['rebuilt_vs_stored_max_abs']}")
    groups = {}
    for sweep in sweeps:
        for arm in sorted({r["arm"] for r in res if r["sweep"] == sweep}):
            for flag in (True, False):
                g = [r for r in res if r["sweep"] == sweep and r["arm"] == arm and r["c3"] == flag]
                if not g:
                    continue
                key = f"{sweep}:{arm}:c3={flag}"
                row = {"n": len(g)}
                for p in PRIMS:
                    row[p] = _q([r["mix"][p] for r in g])
                row["reversal"] = _q([r["reversal"] for r in g])
                row["even_null"] = _q([r["seq_struct_form_null_mean_unvalidated"] for r in g])
                row["form_excess"] = _q([r["seq_struct_form_excess_unvalidated"] for r in g])
                row["order_excess"] = _q([r["seq_struct_order_excess_unvalidated"] for r in g])
                row["repeat_excess"] = _q([r["repeat_excess"] for r in g])
                row["tb_relaxed_minus_not"] = _q([r["tb_relaxed_minus_not"] for r in g])
                groups[key] = row
                print(key, json.dumps(row))
    out["groups"] = groups
    clo = {p: _q([r["closer_reversal"][p] for r in res]) for p in PRIMS}
    out["closer_reversal"] = clo
    print("reversal rate of a pair by its closing move:", clo)
    tb = np.array([r["closer_share"]["TB"] for r in res])
    ex = np.array([r["closer_share"]["EX"] for r in res])
    ok = np.isfinite(rev) & np.isfinite(tb) & np.isfinite(ex)
    X = np.column_stack([np.ones(int(ok.sum())), tb[ok], ex[ok]])
    beta = np.linalg.lstsq(X, rev[ok], rcond=None)[0]
    r2 = 1.0 - float(((rev[ok] - X @ beta) ** 2).sum() / ((rev[ok] - rev[ok].mean()) ** 2).sum())
    out["fit"] = {"intercept": float(beta[0]), "tb": float(beta[1]), "ex": float(beta[2]),
                  "r2": r2, "n": int(ok.sum())}
    print("reversal ~ a + b TB + c EX (closing-move shares):", out["fit"])
    c3 = np.array([r["c3"] for r in res])
    tbo = np.array([r["mix"]["TB"] for r in res])
    sep = {}
    for t in (0.45, 0.5):
        sep[f"tb>={t}"] = {"c3": int((c3 & (tbo >= t)).sum()), "c3_of": int(c3.sum()),
                           "other": int((~c3 & (tbo >= t)).sum()), "other_of": int((~c3).sum())}
    low = [r for r in res if r["c3"] and r["mix"]["TB"] < 0.5]
    sep["c3_tb_below_0.5"] = {"n": len(low), "RO": _q([r["mix"]["RO"] for r in low]),
                              "EX": _q([r["mix"]["EX"] for r in low]),
                              "arms": sorted({r["arm"] for r in low})}
    out["separation"] = sep
    print("TURN_BACK share of the own rows:", json.dumps(sep))
    oc3 = [r for r in res if r["c3"]]
    out["c3_order_excess"] = _q([r["seq_struct_order_excess_unvalidated"] for r in oc3])
    out["c3_form_excess"] = _q([r["seq_struct_form_excess_unvalidated"] for r in oc3])
    print(f"locomotor c3 readings: form excess {out['c3_form_excess']}, "
          f"order excess {out['c3_order_excess']}")
    out["object_c3"] = obj
    for r in obj:
        print(f"object c3 {r['sweep']} {r['run']} {r['mid']}: form excess "
              f"{r['seq_struct_form_excess_unvalidated']:+.3f}, order excess "
              f"{r['seq_struct_order_excess_unvalidated']:+.3f} "
              f"(z {r['seq_struct_order_z_unvalidated']:+.2f})")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sweeps", nargs="+", default=list(SWEEPS),
                    help="sweep folders under _output/ (default: H-i and H-h)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    sweeps = tuple(args.sweeps)
    jobs, stored, obj = readings(sweeps)
    if not jobs:
        print(f"no readings found under _output/ {list(sweeps)}")
        return 1
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        res = list(ex.map(rebuild, jobs, chunksize=2))
    for r, j in zip(res, jobs):
        r.update(stored[j])
    out = report(res, obj, sweeps)
    out["readings"] = res
    Path(args.out).write_text(json.dumps(out, default=float, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
