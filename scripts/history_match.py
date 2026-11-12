#!/usr/bin/env python
"""Replica v2 M5: history matching of the replica to the record (docs/REPLICA_V2.md).

Each run is configs/replica_v2.yaml with the PARAMS overrides, one training seed (7000-7011 in
turn), 1,600 days. Each OUTPUT has a record value z, an observation sd (the record's own
uncertainty) and a model-discrepancy sd, and some are compared on a log scale. A GP emulator
(universe25.calib.emulator) per output, refitted on every run so far, gives the implausibility

    I_i(x) = |z_i - E f_i(x)| / sqrt(obs_i^2 + md_i^2 + emulator var + seed-noise var)

and the not-ruled-out-yet (NROY) space is {x : the second-largest I_i(x) <= 3}. Wave 1 is a
Latin hypercube over the parameter box. Wave k > 1 samples the current NROY space uniformly
(rejection from the box, then local perturbation if it is small).

usage:
  python scripts/history_match.py --wave 1 --n 200 [--workers 8]
  python scripts/history_match.py --wave 2 --n 200       (fits on waves < 2, samples NROY, runs)
  python scripts/history_match.py --fit                  (emulator diagnostics, NROY size, best)
  python scripts/history_match.py --ensemble 12 --seeds 7000-7003   (NROY members x seeds)
Runs are cached in _output/<label>/runs.jsonl (resumable; --label, default hm); designs there.
--fixed group.key=value ... applies the same overrides to every run of the label (M5b:
--label hm_nofac --fixed geometry.hopper_facilitation=false); they are stored in each run's
params, so the ensemble members carry them. --transmission adds the two M7 parameters
(biology.maternal_transmission, biology.care_ref); M5c is --label hm_m7 --transmission --fixed
geometry.hopper_facilitation=false. A label keeps the parameter names and fixed overrides of
its first wave (_output/<label>/label.json) and refuses calls that differ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "_output" / "hm"  # main process only; set from --label
FIXED: dict = {}  # main process only; set from --fixed (jobs carry it to the workers)
CONF = "replica_v2.yaml"
DAYS = 1600.0
TRAIN_SEEDS = tuple(range(7000, 7012))
CUT = 3.0

# (group, name, low, high, log)
PARAMS_M5 = [
    ("biology", "breeding_p_base", 0.2, 0.95, False),
    ("biology", "litter_mean", 4.5, 7.5, False),
    ("biology", "maturity_days", 42.0, 70.0, False),
    ("biology", "imprint_rate", 0.003, 0.1, True),
    ("biology", "imprint_density_threshold", 0.05, 0.6, False),
    ("drives", "stress_density_gain", 0.15, 1.2, False),
    ("drives", "stress_decay", 0.5, 1.5, False),
    ("biology", "nest_overcrowd_stress", 0.0, 0.5, False),
    ("biology", "maternal_erosion_stress", 0.25, 0.8, False),
    ("biology", "courtship_erosion_stress", 0.25, 0.8, False),
    ("biology", "withdrawn_competence_threshold", 0.1, 0.6, False),
    ("biology", "care_imprint_gain", 0.0, 3.0, False),
    ("biology", "exclusion_stress", 0.0, 0.15, False),
    ("biology", "wound_mortality_scale", 0.005, 0.3, True),
    ("biology", "base_mortality_per_day", 5e-5, 1.5e-3, True),
    ("biology", "young_mortality_scale", 0.1, 1.0, False),
    ("biology", "nurse_disturb_coef", 0.0, 8.0, False),
    ("biology", "stress_mortality_scale", 2e-4, 0.02, True),
    ("biology", "litter_abandon_p", 0.0, 0.6, False),
    ("biology", "maternal_neglect_stress", 0.3, 0.9, False),
]
PARAMS_M7 = [  # M5c: maternal-care transmission (replica v2 M7)
    ("biology", "maternal_transmission", 0.0, 1.0, False),
    ("biology", "care_ref", 0.5, 2.5, True),
]
PARAMS = PARAMS_M5  # main process only; set from --transmission (jobs carry the overrides)


def param_set(transmission: bool) -> list:
    return PARAMS_M5 + (PARAMS_M7 if transmission else [])

# name: (z, obs sd, discrepancy sd, log offset or None)
OUTPUTS = {
    "first_litters_day": (77.0, 13.5, 0.0, None),  # record 50-104 (contested)
    "n_at_day_315": (620.0, 31.0, 62.0, 10.0),
    "adults_at_day_315": (150.0, 15.0, 30.0, 10.0),
    "peak_n": (2200.0, 110.0, 220.0, 10.0),
    "plateau_onset_day": (560.0, 20.0, 30.0, None),
    "n_at_day_736": (2056.0, 103.0, 206.0, 10.0),
    "n_at_day_811": (1871.0, 94.0, 187.0, 10.0),
    "n_at_day_960": (1650.0, 83.0, 165.0, 10.0),
    "last_young_day": (600.0, 15.0, 30.0, None),
    "last_conception_day": (920.0, 20.0, 40.0, None),
    "n_at_day_1444": (122.0, 12.0, 40.0, 10.0),  # after ~150 removed (removal event on)
    "n_at_day_1588": (27.0, 5.0, 15.0, 10.0),
    "doubling_b": (55.0, 5.0, 8.0, 0.0),
    "doubling_c": (125.0, 10.0, 15.0, 0.0),  # record 105-145 (contested); 315 -> plateau onset
    "male_share_315": (0.40, 0.03, 0.05, None),
    "male_share_1444": (0.18, 0.03, 0.06, None),
    "empty_boxes_560": (0.25, 0.05, 0.05, None),
    "withdrawn_560": (0.32, 0.05, 0.10, None),
    "beautiful_800": (0.53, 0.05, 0.10, None),
    "brood_groups_315": (14.0, 1.0, 3.0, None),
}
DOUBLING_CAP = 2000.0  # a doubling time that is undefined (no growth) is scored as this


def to_params(u: np.ndarray, params: list | None = None) -> dict:
    """Unit-cube point -> nested config overrides."""
    params = PARAMS if params is None else params
    if len(u) != len(params):
        raise ValueError(f"{len(u)}-dimensional point for {len(params)} parameters")
    over: dict = {}
    for (g, k, lo, hi, lg), v in zip(params, u):
        val = float(np.exp(np.log(lo) + v * (np.log(hi) - np.log(lo))) if lg
                    else lo + v * (hi - lo))
        over.setdefault(g, {})[k] = val
    return over


def key_of(u: np.ndarray, seed: int) -> str:
    return hashlib.sha1((",".join(f"{v:.10f}" for v in u) + f"|{seed}").encode()).hexdigest()


def outputs(r: dict) -> dict[str, float]:
    lm, st, tr = r["landmarks"], r["struct"], r.get("territory", {})
    n = np.asarray(r["n_series"], float)  # N at day i + 1

    def at(day: float) -> float:
        i = int(round(day)) - 1
        return float(n[i]) if 0 <= i < n.size else float("nan")

    t97 = lm.get("peak_day_97pct", float("nan"))
    n315, n97 = at(315.0), at(t97)
    dc = ((t97 - 315.0) * np.log(2.0) / np.log(n97 / n315)
          if np.isfinite(t97) and t97 > 315.0 and n315 > 0 and n97 > n315 else DOUBLING_CAP)
    db = lm.get("doubling_time_phase_b_days", float("nan"))
    db = db if np.isfinite(db) else DOUBLING_CAP

    def s(day: str, k: str) -> float:
        return float(st.get(day, {}).get(k, float("nan")))

    return {
        "first_litters_day": lm.get("first_litters_day", float("nan")),
        "n_at_day_315": n315,
        "adults_at_day_315": lm.get("adults_at_day_315", float("nan")),
        "peak_n": lm.get("peak_n", float("nan")),
        "plateau_onset_day": t97,
        "n_at_day_736": at(736.0) if n.size >= 736 else 0.0,
        "n_at_day_811": at(811.0) if n.size >= 811 else 0.0,
        "n_at_day_960": at(960.0) if n.size >= 960 else 0.0,
        "last_young_day": lm.get("last_young_day", float("nan")),
        "last_conception_day": lm.get("last_conception_day", float("nan")),
        "n_at_day_1444": at(1444.0) if n.size >= 1444 else 0.0,
        "n_at_day_1588": at(1588.0) if n.size >= 1588 else 0.0,
        "doubling_b": min(db, DOUBLING_CAP),
        "doubling_c": min(dc, DOUBLING_CAP),
        "male_share_315": s("315", "male_share"),
        "male_share_1444": s("1444", "male_share"),
        "empty_boxes_560": s("560", "empty_box_share"),
        "withdrawn_560": s("560", "withdrawn_share"),
        "beautiful_800": s("800", "beautiful_share"),
        "brood_groups_315": float(len(tr.get("brood_sizes_315", []))),
    }


def transform(name: str, y: np.ndarray) -> np.ndarray:
    off = OUTPUTS[name][3]
    return np.log(np.maximum(y, 0.0) + off) if off is not None else y


def target(name: str) -> tuple[float, float]:
    """(z, total observation + discrepancy variance) on the comparison scale."""
    z, so, sm, off = OUTPUTS[name]
    var = so ** 2 + sm ** 2
    if off is not None:
        return float(np.log(z + off)), var / (z + off) ** 2
    return z, var


def _deep(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _deep(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def parse_fixed(items: list[str]) -> dict:
    """["geometry.hopper_facilitation=false", ...] -> nested overrides."""
    out: dict = {}
    for it in items:
        key, val = it.split("=", 1)
        lit = {"true": True, "false": False, "null": None}
        v: object = lit.get(val.lower(), lit)
        if v is lit:
            try:
                v = float(val)
            except ValueError:
                v = val
        d = out
        ks = key.split(".")
        for k in ks[:-1]:
            d = d.setdefault(k, {})
        d[ks[-1]] = v
    return out


def run_job(job: tuple) -> dict:
    from replica_report import run_one

    key, u, seed, wave, over = job  # over: the run's full overrides, made in the main process
    t0 = time.perf_counter()
    _, _, r = run_one(("hm", CONF, over, seed, DAYS))
    return {"key": key, "wave": wave, "u": u, "seed": seed, "params": over,
            "outputs": outputs(r), "secs": time.perf_counter() - t0,
            "n_series": r["n_series"]}


def load_runs() -> list[dict]:
    path = OUT / "runs.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def check_label(fixed: dict) -> None:
    """A label keeps the parameter names and fixed overrides of its first wave."""
    cur = {"params": [k for _, k, *_ in PARAMS], "fixed": fixed}
    path = OUT / "label.json"
    runs = load_runs()
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old != cur:
            raise SystemExit(f"label {OUT.name} holds {old}; this call has {cur}")
    elif runs:  # labels from before the record (M5, M5b): at least the dimension must agree
        if len(runs[0]["u"]) != len(PARAMS):
            raise SystemExit(f"label {OUT.name} holds {len(runs[0]['u'])}-parameter runs; "
                             f"this call has {len(PARAMS)} parameters")
    else:
        path.write_text(json.dumps(cur, indent=1), encoding="utf-8")


def job_of(u: np.ndarray, seed: int, wave: int) -> tuple:
    uu = [float(v) for v in u]
    return (key_of(u, seed), uu, seed, wave, _deep(to_params(np.asarray(uu)), FIXED))


def run_jobs(jobs: list[tuple], workers: int) -> None:
    done = {r["key"] for r in load_runs()}
    todo = [j for j in jobs if j[0] not in done]
    print(f"{len(jobs)} jobs, {len(todo)} to run ({len(jobs) - len(todo)} cached)", flush=True)
    if not todo:
        return
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex, \
            (OUT / "runs.jsonl").open("a", encoding="utf-8") as fh:
        futs = [ex.submit(run_job, j) for j in todo]
        for k, f in enumerate(as_completed(futs), 1):
            fh.write(json.dumps(f.result(), default=float) + "\n")
            fh.flush()
            if k % 10 == 0 or k == len(todo):
                print(f"  {k}/{len(todo)} done, {time.perf_counter() - t0:.0f} s", flush=True)


class Emulators:
    def __init__(self, runs: list[dict]) -> None:
        from universe25.calib.emulator import GP

        self.gp: dict = {}
        self.loo: dict = {}
        U = np.array([r["u"] for r in runs])
        for name in OUTPUTS:
            y = np.array([r["outputs"].get(name, np.nan) for r in runs], float)
            ok = np.isfinite(y)
            if ok.sum() < 20:
                continue
            yt = transform(name, y[ok])
            gp = GP(U[ok], yt, restarts=3, seed=11)
            self.gp[name] = gp
            m, v = gp.loo()
            self.loo[name] = float(np.mean(np.abs(yt - m) / np.sqrt(v) > 3.0))

    def impl(self, U: np.ndarray) -> np.ndarray:
        """(points, outputs) implausibility; NaN where an output has no emulator."""
        cols = []
        for name in OUTPUTS:
            if name not in self.gp:
                cols.append(np.full(len(U), np.nan))
                continue
            z, var = target(name)
            m, ve, vn = self.gp[name].predict(U)
            cols.append(np.abs(z - m) / np.sqrt(var + ve + vn))
        return np.stack(cols, axis=1)


def kth_max(I: np.ndarray, k: int) -> np.ndarray:
    J = np.where(np.isfinite(I), I, -np.inf)
    return -np.sort(-J, axis=1)[:, k - 1]


def sample_nroy(em: Emulators, n: int, seed: int, max_rounds: int = 12) -> tuple[np.ndarray, float]:
    rng = np.random.default_rng(seed)
    d = len(PARAMS)
    keep, tried = [], 0
    for _ in range(max_rounds):
        C = rng.random((100_000, d))
        tried += len(C)
        ok = kth_max(em.impl(C), 2) <= CUT
        keep.extend(C[ok])
        if len(keep) >= 5 * n:
            break
    frac = len(keep) / tried
    pts = np.array(keep) if keep else np.empty((0, d))
    while 0 < len(pts) < 5 * n:  # small NROY: perturb found points
        P = np.clip(pts[rng.integers(0, len(pts), 20_000)]
                    + rng.normal(0, 0.03, (20_000, d)), 0.0, 1.0)
        ok = kth_max(em.impl(P), 2) <= CUT
        pts = np.vstack([pts, P[ok]])
        if not ok.any():
            break
    if len(pts) == 0:
        return pts, frac
    sel = rng.choice(len(pts), size=min(n, len(pts)), replace=False)
    return pts[sel], frac


def write_ensemble(runs: list[dict], path: Path) -> None:
    """Score each ensemble member (wave 99) on the mean of its seeds' outputs, on the
    comparison scale. The record is one realization, so the variance is one run's seed noise
    plus that of the k-seed mean, V_s (1 + 1/k), with V_s from the final emulators' nuggets.
    (Until M5d this used V_s / k only, which leaves out the record's own realization and is
    too strict; docs/REPLICA_V2.md M5d.) Members pass if the second-largest implausibility is
    <= CUT. If none pass, the 12 best are written with fallback = true."""
    em = Emulators([r for r in runs if r["wave"] != 99])
    groups: dict[str, list[dict]] = {}
    for r in runs:
        if r["wave"] == 99:
            groups.setdefault(json.dumps([round(v, 10) for v in r["u"]]), []).append(r)
    scored = []
    for rs in groups.values():
        k = len(rs)
        Ii, means = [], {}
        for name in OUTPUTS:
            ys = np.array([r["outputs"].get(name, np.nan) for r in rs], float)
            ys = ys[np.isfinite(ys)]
            if not ys.size:
                Ii.append(np.inf)
                continue
            yt = float(np.mean(transform(name, ys)))
            means[name] = yt
            z, var = target(name)
            vs = em.gp[name].n2 * em.gp[name].sd ** 2 if name in em.gp else 0.0
            vn = vs * (1.0 + 1.0 / ys.size)
            Ii.append(abs(z - yt) / np.sqrt(var + vn))
        Ii = np.array(Ii)
        scored.append({"u": rs[0]["u"], "params": rs[0]["params"],
                       "seeds": [r["seed"] for r in rs], "n_seeds": k,
                       "i2": float(np.sort(Ii)[-2]), "imax": float(Ii.max()),
                       "implausibility": dict(zip(OUTPUTS, map(float, Ii)))})
    scored.sort(key=lambda m: m["i2"])
    passing = [m for m in scored if m["i2"] <= CUT]
    members = passing or scored[:12]
    path.write_text(json.dumps({
        "criterion": f"second-largest implausibility <= {CUT} on the mean of the member's seeds"
                     " (variance V_s (1 + 1/k))",
        "n_sampled": len(scored), "n_pass": len(passing), "fallback": not passing,
        "members": members}, indent=1, default=float), encoding="utf-8")
    print(f"{len(scored)} members scored, {len(passing)} pass; wrote {len(members)} to {path}")
    for m in scored[:10]:
        worst = sorted(m["implausibility"].items(), key=lambda t: -t[1])[:3]
        print(f"  I2 {m['i2']:.2f} Imax {m['imax']:.2f}; worst: "
              + ", ".join(f"{n} {v:.1f}" for n, v in worst))


def main() -> int:
    from scipy.stats import qmc

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wave", type=int)
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--fit", action="store_true")
    p.add_argument("--ensemble", type=int)
    p.add_argument("--seeds", default="7000-7003")
    p.add_argument("--write-ensemble", help="path: score the ensemble runs, write members")
    p.add_argument("--label", default="hm", help="run cache: _output/<label>/")
    p.add_argument("--fixed", nargs="*", default=[], help="group.key=value for every run")
    p.add_argument("--transmission", action="store_true",
                   help="add maternal_transmission and care_ref to the parameters (M5c)")
    a = p.parse_args()
    global OUT, FIXED, PARAMS
    OUT = ROOT / "_output" / a.label
    FIXED = parse_fixed(a.fixed)
    PARAMS = param_set(a.transmission)
    OUT.mkdir(parents=True, exist_ok=True)
    check_label(FIXED)
    if FIXED:
        print(f"label {a.label}: fixed overrides {FIXED}")
    if a.wave:
        if a.wave == 1:
            U = qmc.LatinHypercube(d=len(PARAMS_M5), seed=2511).random(a.n)
            if len(PARAMS) > len(PARAMS_M5):  # M5c: M5b's points, new parameters appended
                U = np.hstack([U, qmc.LatinHypercube(d=len(PARAMS) - len(PARAMS_M5),
                                                     seed=2512).random(a.n)])
            frac = 1.0
        else:
            runs = [r for r in load_runs() if r["wave"] < a.wave]
            em = Emulators(runs)
            U, frac = sample_nroy(em, a.n, seed=2511 + a.wave)
            print(f"wave {a.wave}: NROY fraction of the box {frac:.4g} "
                  f"(emulators on {len(runs)} runs); {len(U)} points")
        jobs = [job_of(u, TRAIN_SEEDS[i % 12], a.wave) for i, u in enumerate(U)]
        (OUT / f"wave{a.wave}_design.json").write_text(
            json.dumps({"nroy_fraction": frac, "jobs": jobs}), encoding="utf-8")
        run_jobs(jobs, a.workers)
        return 0
    runs = load_runs()
    if a.fit:
        em = Emulators(runs)
        print(f"{len(runs)} runs; emulators for {len(em.gp)} of {len(OUTPUTS)} outputs")
        for name, gp in em.gp.items():
            print(f"  {name:22s} LOO |e|>3sd {em.loo[name]:.3f}  nugget sd "
                  f"{np.sqrt(gp.n2) * gp.sd:.3g}  shortest lengthscales "
                  + ", ".join(f"{PARAMS[i][1]} {gp.ls[i]:.2f}" for i in np.argsort(gp.ls)[:3]))
        C = np.random.default_rng(1).random((100_000, len(PARAMS)))
        I = em.impl(C)
        for k in (1, 2, 3):
            print(f"  NROY fraction (k-th max <= {CUT}): k={k} {np.mean(kth_max(I, k) <= CUT):.4g}")
        nroy = C[kth_max(I, 2) <= CUT]
        if len(nroy):
            print(f"  NROY ranges in parameter units (5 / 50 / 95 %, {len(nroy)} candidates):")
            for j, (g, k, lo, hi, lg) in enumerate(PARAMS):
                q = np.quantile(nroy[:, j], [0.05, 0.5, 0.95])
                v = np.exp(np.log(lo) + q * (np.log(hi) - np.log(lo))) if lg else lo + q * (hi - lo)
                print(f"    {k:32s} {v[0]:.4g} / {v[1]:.4g} / {v[2]:.4g}")
            names_p = [k for _, k, *_ in PARAMS]
            if "maternal_transmission" in names_p:
                tau = nroy[:, names_p.index("maternal_transmission")]  # unit = raw on 0-1
                print(f"  NROY share with tau < 0.2: {np.mean(tau < 0.2):.3f}")
        # co-occurrence in the simulated runs: growth, the phase without surviving young, collapse
        grow = np.array([r["outputs"]["peak_n"] > 1800 for r in runs])
        coll = np.array([r["outputs"]["n_at_day_1588"] < 300 for r in runs])
        gap = np.array([r["outputs"]["last_conception_day"] - r["outputs"]["last_young_day"]
                        >= 150 for r in runs])
        print(f"  runs: peak > 1800 {grow.sum()}, collapse (N1588 < 300) {coll.sum()}, gap >= 150 "
              f"d {gap.sum()}; grow & collapse {(grow & coll).sum()}, grow & gap "
              f"{(grow & gap).sum()}, all three {(grow & coll & gap).sum()} of {len(runs)}")
        # conflicts: the smallest implausibility each target can reach alone, and what the
        # others are where the joint (2nd-max) implausibility is smallest
        i2 = kth_max(I, 2)
        best = int(np.argmin(i2))
        print(f"  smallest joint 2nd-max implausibility {i2[best]:.2f}; per target there "
              "(alone-minimum in brackets):")
        for j, name in enumerate(OUTPUTS):
            if np.isfinite(I[:, j]).any():
                print(f"    {name:22s} {I[best, j]:6.2f}  [{np.nanmin(I[:, j]):.2f}]")
        names = list(OUTPUTS)
        print("  pairwise conflicts: min over candidates of max(I_a, I_b), emulated; and the "
              "simulated runs' best")
        for pa, pb in (("peak_n", "n_at_day_1588"), ("peak_n", "last_conception_day"),
                       ("peak_n", "n_at_day_1444"), ("n_at_day_736", "n_at_day_1444"),
                       ("peak_n", "n_at_day_315"), ("peak_n", "beautiful_800")):
            ja, jb = names.index(pa), names.index(pb)
            em_min = float(np.nanmin(np.maximum(I[:, ja], I[:, jb])))
            sim_min = np.inf
            for r in runs:
                ii = []
                for nm in (pa, pb):
                    y = r["outputs"].get(nm, np.nan)
                    z, var = target(nm)
                    vn = em.gp[nm].n2 * em.gp[nm].sd ** 2
                    ii.append(abs(z - transform(nm, np.array([y]))[0]) / np.sqrt(var + vn)
                              if np.isfinite(y) else np.inf)
                sim_min = min(sim_min, max(ii))
            print(f"    {pa} & {pb}: emulated {em_min:.2f}, simulated {sim_min:.2f}")
        # the simulated runs, scored on their own outputs (seed noise from the emulators)
        rows = []
        for r in runs:
            Ii = []
            for name in OUTPUTS:
                y = r["outputs"].get(name, np.nan)
                if not np.isfinite(y):
                    Ii.append(np.inf)
                    continue
                z, var = target(name)
                vn = em.gp[name].n2 * em.gp[name].sd ** 2 if name in em.gp else 0.0
                Ii.append(abs(z - transform(name, np.array([y]))[0]) / np.sqrt(var + vn))
            Ii = np.array(Ii)
            rows.append((np.sort(Ii)[-2], np.max(Ii), r))
        rows.sort(key=lambda t: t[0])
        print("best simulated runs (2nd-max / max implausibility):")
        for i2, im, r in rows[:8]:
            o = r["outputs"]
            print(f"  wave {r['wave']} seed {r['seed']}: I2 {i2:.2f} Imax {im:.2f} | N315 "
                  f"{o['n_at_day_315']:.0f} peak {o['peak_n']:.0f}@{o['plateau_onset_day']:.0f} "
                  f"N736 {o['n_at_day_736']:.0f} N1444 {o['n_at_day_1444']:.0f} N1588 "
                  f"{o['n_at_day_1588']:.0f} lastconc {o['last_conception_day']:.0f}")
        (OUT / "fit_summary.json").write_text(json.dumps({
            "n_runs": len(runs), "loo_out_3sd": em.loo,
            "best": [{"i2": float(i2), "imax": float(im), "key": r["key"], "u": r["u"],
                      "params": r["params"], "outputs": r["outputs"]} for i2, im, r in rows[:20]],
        }, indent=1, default=float), encoding="utf-8")
        return 0
    if a.write_ensemble:
        write_ensemble(runs, Path(a.write_ensemble))
        return 0
    if a.ensemble:
        em = Emulators(runs)
        U, frac = sample_nroy(em, a.ensemble, seed=9901)
        lo, hi = (int(v) for v in a.seeds.split("-"))
        jobs = [job_of(u, s, 99) for u in U for s in range(lo, hi + 1)]
        (OUT / "ensemble_design.json").write_text(
            json.dumps({"nroy_fraction": frac, "jobs": jobs}), encoding="utf-8")
        run_jobs(jobs, a.workers)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
