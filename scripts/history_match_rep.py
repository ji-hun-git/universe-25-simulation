#!/usr/bin/env python
"""Replica v2 M5d: history matching with replicate seeds per point (docs/REPLICA_V2.md M5d).

In M5c the targets for the phase without surviving young had two outcomes across seeds
(reproduction ends, or it goes on), so as one number per run they carried ~250 days of seed
noise and could not separate parameter sets. Here every design point runs REP_SEEDS, and the
targets split in three:

* MEAN targets: the seed mean is emulated, and so is the log seed variance V_s(x);
  I(x) = |z - m(x)| / sqrt(obs^2 + md^2 + emulator var + V_s(x)) (the record is one run);
* the arc frequency p(x) = P(peak > 1800, last conception - last surviving birth >= 150 d,
  N@1588 < 300), emulated on the share of a point's seeds; x is ruled out where the emulated
  mean + 3 sd is below ALPHA;
* COND targets: the record's late values given the arc, scored in the ensemble on arc seeds.

NROY = M5c's final NROY (wave 0, history_match label hm_m7) and {second-largest MEAN I <= 3}
and {p not ruled out}.

M5e (--m8; docs/REPLICA_V2.md): the same with replica v2 M8 on (withdrawn_disengage, no
fertility from competence) as fixed overrides, and the categories target beautiful_800 read as
the adult share (outputs key beautiful_800_adult). Default label hm_m5e.

usage:
  python scripts/history_match_rep.py --wave 1 --n 120 [--workers 8]
  python scripts/history_match_rep.py --wave 2 --n 80
  python scripts/history_match_rep.py --fit
  python scripts/history_match_rep.py --ensemble 24
  python scripts/history_match_rep.py --write-ensemble configs/replica_v2_ensemble_m5d.json
Runs are cached in _output/<label>/runs.jsonl (history_match.run_job; resumable).
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

import history_match as hm  # noqa: E402

BASE = "hm_m7"  # M5c: wave 0
FIXED = {"geometry": {"hopper_facilitation": False}}
FIXED_M8 = {"geometry": {"hopper_facilitation": False},
            "biology": {"withdrawn_disengage": True, "fertility_from_competence": False}}
ALIAS: dict[str, str] = {}  # target -> outputs key it is read from (M5e: the adult share)
ALIAS_M8 = {"beautiful_800": "beautiful_800_adult"}
REP_SEEDS = tuple(range(7000, 7006))
ENS_SEEDS = tuple(range(7000, 7012))
MEAN = ["first_litters_day", "n_at_day_315", "adults_at_day_315", "peak_n", "plateau_onset_day",
        "n_at_day_736", "n_at_day_811", "n_at_day_960", "doubling_b", "doubling_c",
        "male_share_315", "empty_boxes_560", "withdrawn_560", "beautiful_800",
        "brood_groups_315"]
COND = ["last_young_day", "last_conception_day", "n_at_day_1444", "n_at_day_1588",
        "male_share_1444"]
ALPHA = 0.05  # the arc may not be rarer than 1 in 20 (at the emulator's upper bound)
MIN_ARC = 2  # a member needs the arc in at least 2 of its 12 seeds
assert len(MEAN) + len(COND) == len(hm.OUTPUTS) and set(MEAN + COND) == set(hm.OUTPUTS)


def is_arc(o: dict) -> bool:
    gap = o["last_conception_day"] - o["last_young_day"]
    return bool(o["peak_n"] > 1800.0 and o["n_at_day_1588"] < 300.0 and gap >= 150.0)


def load(label: str) -> list[dict]:
    path = ROOT / "_output" / label / "runs.jsonl"
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def points(runs: list[dict], waves: set[int], n_seeds: int | None = None) -> list[dict]:
    """Group runs by parameter point; keep points with n_seeds runs when given."""
    g: dict[tuple, list[dict]] = {}
    for r in runs:
        if r["wave"] in waves:
            g.setdefault(tuple(round(v, 10) for v in r["u"]), []).append(r)
    out = []
    for rs in g.values():
        rs.sort(key=lambda r: r["seed"])
        if n_seeds is None or len(rs) == n_seeds:
            out.append({"u": rs[0]["u"], "params": rs[0]["params"], "runs": rs,
                        "wave": rs[0]["wave"]})
    return out


def tvals(rs: list[dict], name: str) -> np.ndarray:
    """A target's finite values over runs, on the comparison scale (read through ALIAS)."""
    key = ALIAS.get(name, name)
    y = np.array([r["outputs"].get(key, np.nan) for r in rs], float)
    return hm.transform(name, y[np.isfinite(y)])


class RepEmulators:
    """Mean and log-variance emulators for the MEAN targets, and the arc frequency."""

    def __init__(self, pts: list[dict]) -> None:
        from universe25.calib.emulator import GP

        U = np.array([p["u"] for p in pts])
        self.gm: dict = {}
        self.gv: dict = {}
        self.loo: dict = {}
        for name in MEAN:
            M = np.full(len(pts), np.nan)
            V = np.full(len(pts), np.nan)
            for i, p in enumerate(pts):
                y = tvals(p["runs"], name)
                if y.size >= 2:
                    M[i], V[i] = y.mean(), y.var(ddof=1)
            ok = np.isfinite(M) & np.isfinite(V)
            floor = 1e-6 * max(float(np.var(M[ok])), 1e-12)
            gm = GP(U[ok], M[ok], restarts=3, seed=11)
            gv = GP(U[ok], np.log(V[ok] + floor), restarts=3, seed=12)
            self.gm[name], self.gv[name] = gm, gv
            for tag, gp, y in (("mean", gm, M[ok]), ("logvar", gv, np.log(V[ok] + floor))):
                m, v = gp.loo()
                self.loo[f"{name}/{tag}"] = float(np.mean(np.abs(y - m) / np.sqrt(v) > 3.0))
        self.k = np.array([sum(is_arc(r["outputs"]) for r in p["runs"]) for p in pts])
        self.share = self.k / np.array([len(p["runs"]) for p in pts])
        self.ga = GP(U, self.share, restarts=3, seed=13)
        m, v = self.ga.loo()
        self.loo["arc/share"] = float(np.mean(np.abs(self.share - m) / np.sqrt(v) > 3.0))

    def impl(self, U: np.ndarray) -> np.ndarray:
        cols = []
        for name in MEAN:
            z, var = hm.target(name)
            m, ve, _ = self.gm[name].predict(U)
            lv, _, _ = self.gv[name].predict(U)
            cols.append(np.abs(z - m) / np.sqrt(var + ve + np.exp(lv)))
        return np.stack(cols, axis=1)

    def arc(self, U: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        m, ve, _ = self.ga.predict(U)
        return m, np.sqrt(ve)

    def keep_mean(self, U: np.ndarray) -> np.ndarray:
        return hm.kth_max(self.impl(U), 2) <= hm.CUT

    def keep(self, U: np.ndarray) -> np.ndarray:
        m, s = self.arc(U)
        return self.keep_mean(U) & (m + 3.0 * s >= ALPHA)


def base_emulators() -> hm.Emulators:
    """M5c's final emulators (its 440 wave runs): wave 0 of M5d."""
    return hm.Emulators([r for r in load(BASE) if r["wave"] != 99])


def sample(em0: hm.Emulators, rep: RepEmulators | None, want: int, seed: int,
           rounds: int = 40, mean_only: bool = False) -> tuple[np.ndarray, dict]:
    """Candidates from M5c's NROY, filtered by the M5d criteria when rep is given."""
    rng = np.random.default_rng(seed)
    d = len(hm.PARAMS)
    keep: list = []
    tried = n0 = 0
    for _ in range(rounds):
        C = rng.random((100_000, d))
        tried += len(C)
        C = C[hm.kth_max(em0.impl(C), 2) <= hm.CUT]
        n0 += len(C)
        if rep is not None and len(C):
            C = C[rep.keep_mean(C) if mean_only else rep.keep(C)]
        keep.extend(C)
        if len(keep) >= want:
            break
    cands = np.array(keep) if keep else np.empty((0, d))
    return cands, {"tried": tried, "in_m5c_nroy": n0, "kept": len(cands),
                   "frac_box": len(cands) / tried, "frac_of_m5c_nroy": len(cands) / max(n0, 1)}


def raw(U: np.ndarray, j: int) -> np.ndarray:
    """Column j of unit-cube points in parameter units."""
    _, _, lo, hi, lg = hm.PARAMS[j]
    if lg:
        return np.exp(np.log(lo) + U[:, j] * (np.log(hi) - np.log(lo)))
    return lo + U[:, j] * (hi - lo)


def check_label(label: str) -> None:
    cur = {"params": [k for _, k, *_ in hm.PARAMS], "fixed": FIXED, "rep_seeds": list(REP_SEEDS),
           "ens_seeds": list(ENS_SEEDS), "base": BASE, "alpha": ALPHA, "min_arc": MIN_ARC}
    if ALIAS:  # M5e (labels from before the alias keep their record)
        cur["alias"] = ALIAS
    path = ROOT / "_output" / label / "label.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old != cur:
            raise SystemExit(f"label {label} holds {old}; this script has {cur}")
    else:
        path.write_text(json.dumps(cur, indent=1), encoding="utf-8")


def v_arc(members: list[list[dict]]) -> dict[str, float]:
    """Within-member variance of each COND target on arc seeds, pooled over members with at
    least 2 arc seeds (all arc seeds together if no member has 2)."""
    out = {}
    for name in COND:
        ss = dof = 0.0
        allv = []
        for rs in members:
            y = tvals([r for r in rs if is_arc(r["outputs"])], name)
            allv.extend(y.tolist())
            if y.size >= 2:
                ss += float(np.sum((y - y.mean()) ** 2))
                dof += y.size - 1
        out[name] = ss / dof if dof > 0 else (float(np.var(allv, ddof=1)) if len(allv) > 1
                                              else 0.0)
    return out


def score(rs: list[dict], va: dict[str, float]) -> dict:
    """A member's implausibilities from its own seeds (docs/REPLICA_V2.md M5d ensemble)."""
    Ii = {}
    for name in MEAN:
        y = tvals(rs, name)
        z, var = hm.target(name)
        if not y.size:
            Ii[name] = np.inf
            continue
        s2 = float(y.var(ddof=1)) if y.size > 1 else 0.0
        Ii[name] = abs(z - y.mean()) / np.sqrt(var + s2 * (1.0 + 1.0 / y.size))
    arc = [r for r in rs if is_arc(r["outputs"])]
    for name in COND:
        y = tvals(arc, name)
        z, var = hm.target(name)
        Ii[name] = (abs(z - y.mean()) / np.sqrt(var + va[name] * (1.0 + 1.0 / y.size))
                    if y.size else np.inf)
    vals = np.array([Ii[n] for n in hm.OUTPUTS])
    seeds = [r["seed"] for r in rs]
    arc_seeds = [r["seed"] for r in arc]
    return {"seeds": seeds, "n_seeds": len(rs), "arc_seeds": arc_seeds,
            "arc_freq": len(arc) / len(rs),
            "arc_wave_seeds": sum(s in REP_SEEDS for s in arc_seeds),
            "arc_new_seeds": sum(s not in REP_SEEDS for s in arc_seeds),
            "i2": float(np.sort(vals)[-2]), "imax": float(vals.max()),
            "implausibility": {n: float(v) for n, v in Ii.items()}}


def fit_report(label: str) -> None:
    runs = hm.load_runs()
    pts = points(runs, {1, 2, 3}, len(REP_SEEDS))
    print(f"{len(runs)} runs, {len(pts)} complete design points")
    rep = RepEmulators(pts)
    print("leave-one-out share |e| > 3 sd:")
    for k, v in rep.loo.items():
        if v > 0.05 or k.endswith("arc/share"):
            print(f"  {k:28s} {v:.3f}")
    print(f"  (others <= 0.05; {sum(v <= 0.05 for v in rep.loo.values())} of {len(rep.loo)})")
    hist = np.bincount(rep.k, minlength=len(REP_SEEDS) + 1)
    print(f"arc seeds per point (0..{len(REP_SEEDS)}): {hist.tolist()}")
    em0 = base_emulators()
    C, st = sample(em0, rep, 10 ** 9, seed=4242, rounds=4, mean_only=True)
    mean_nroy = len(C)
    m, s = rep.arc(C) if len(C) else (np.empty(0), np.empty(0))
    keep = m + 3.0 * s >= ALPHA
    print(f"of {st['tried']} box points: {st['in_m5c_nroy']} in M5c's NROY, {mean_nroy} also "
          f"pass the mean targets, {int(keep.sum())} also the arc frequency; M5d NROY "
          f"{keep.sum() / st['tried']:.4g} of the box, {keep.sum() / max(st['in_m5c_nroy'], 1):.3f}"
          " of M5c's NROY")
    res: dict = {"n_runs": len(runs), "n_points": len(pts), "loo": rep.loo,
                 "arc_hist": hist.tolist(), "sampling": st, "mean_nroy": mean_nroy,
                 "nroy": int(keep.sum())}
    if len(C):
        q = np.quantile(m, [0.05, 0.5, 0.95])
        print(f"emulated p over the mean-target NROY: 5/50/95 % {q[0]:.3f} / {q[1]:.3f} / "
              f"{q[2]:.3f}, max {m.max():.3f}; share with p >= 0.1 {np.mean(m >= 0.1):.3f}, "
              f">= 0.2 {np.mean(m >= 0.2):.3f}")
        res["p_quantiles"] = q.tolist()
        res["p_max"] = float(m.max())
        N = C[keep]
        if len(N):
            top = N[m[keep] >= np.quantile(m[keep], 0.9)]
            names = [k for _, k, *_ in hm.PARAMS]
            for tag, X in (("NROY", N), ("NROY, top 10 % of p", top)):
                print(f"{tag} ({len(X)} candidates), parameters 5 / 50 / 95 %:")
                for j, nm in enumerate(names):
                    v = np.quantile(raw(X, j), [0.05, 0.5, 0.95])
                    print(f"    {nm:32s} {v[0]:.4g} / {v[1]:.4g} / {v[2]:.4g}")
                tj = names.index("maternal_transmission")
                print(f"  share with tau < 0.2: {np.mean(X[:, tj] < 0.2):.3f}")
                res[f"tau_lt_0.2[{tag}]"] = float(np.mean(X[:, tj] < 0.2))
    # observed, emulator-free: each point scored on its own seeds
    va = v_arc([p["runs"] for p in pts])
    rows = sorted(((score(p["runs"], va), p) for p in pts),
                  key=lambda t: (-t[0]["arc_freq"], t[0]["i2"]))
    print("design points with the most arc seeds (observed; I2 over the 20 targets):")
    for sc, p in rows[:12]:
        b = p["params"]["biology"]
        print(f"  wave {p['wave']} arc {len(sc['arc_seeds'])}/{sc['n_seeds']}  I2 {sc['i2']:.2f}"
              f"  tau {b['maternal_transmission']:.2f} cref {b['care_ref']:.2f}")
    res["best_observed"] = [{"arc": len(sc["arc_seeds"]), "i2": sc["i2"], "u": p["u"]}
                            for sc, p in rows[:20]]
    (ROOT / "_output" / label / "fit_summary.json").write_text(
        json.dumps(res, indent=1, default=float), encoding="utf-8")


def write_ensemble(path: Path) -> None:
    runs = hm.load_runs()
    mem = points(runs, {99})
    va = v_arc([p["runs"] for p in mem])
    scored = []
    for p in mem:
        sc = score(p["runs"], va)
        sc.update({"u": p["u"], "params": p["params"]})
        sc["passes"] = bool(len(sc["arc_seeds"]) >= MIN_ARC and sc["i2"] <= hm.CUT)
        scored.append(sc)
    scored.sort(key=lambda m: m["i2"])
    passing = [m for m in scored if m["passes"]]
    members = passing or scored[:12]
    path.write_text(json.dumps({
        "criterion": (f"arc in at least {MIN_ARC} of the member's seeds, and second-largest "
                      f"implausibility <= {hm.CUT} over 15 mean targets (own seed variance, "
                      "V_s (1 + 1/k)) and 5 targets given the arc (pooled arc variance)"
                      + (f"; targets read as {ALIAS}" if ALIAS else "")),
        "n_sampled": len(scored), "n_pass": len(passing), "fallback": not passing,
        "v_arc": va, "members": members}, indent=1, default=float), encoding="utf-8")
    print(f"{len(scored)} members scored, {len(passing)} pass; wrote {len(members)} to {path}")
    for m in scored[:12]:
        worst = sorted(m["implausibility"].items(), key=lambda t: -t[1])[:3]
        b = m["params"]["biology"]
        print(f"  I2 {m['i2']:.2f} arc {len(m['arc_seeds'])}/{m['n_seeds']} (wave seeds "
              f"{m['arc_wave_seeds']}, new {m['arc_new_seeds']}) tau "
              f"{b['maternal_transmission']:.2f} cref {b['care_ref']:.2f}; worst: "
              + ", ".join(f"{n} {v:.1f}" for n, v in worst))
    a = np.array([m["arc_wave_seeds"] for m in scored])
    b = np.array([m["arc_new_seeds"] for m in scored])
    print(f"arc seeds over all members: {a.sum()} of {6 * len(scored)} on 7000-7005, {b.sum()} "
          f"of {6 * len(scored)} on 7006-7011")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wave", type=int)
    p.add_argument("--n", type=int, default=120)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--fit", action="store_true")
    p.add_argument("--ensemble", type=int)
    p.add_argument("--write-ensemble")
    p.add_argument("--label")
    p.add_argument("--m8", action="store_true",
                   help="M5e: replica v2 M8 on, categories target as the adult share")
    a = p.parse_args()
    global FIXED, ALIAS
    if a.m8:
        FIXED, ALIAS = FIXED_M8, dict(ALIAS_M8)
    a.label = a.label or ("hm_m5e" if a.m8 else "hm_m5d")
    hm.PARAMS = hm.param_set(True)
    hm.FIXED = FIXED
    hm.OUT = ROOT / "_output" / a.label
    hm.OUT.mkdir(parents=True, exist_ok=True)
    check_label(a.label)
    if a.fit:
        fit_report(a.label)
        return 0
    if a.write_ensemble:
        write_ensemble(Path(a.write_ensemble))
        return 0
    em0 = base_emulators()
    if a.wave or a.ensemble:
        wave = a.wave or 99
        rep = None
        if wave > 1:
            pts = points(hm.load_runs(), set(range(1, min(wave, 99))), len(REP_SEEDS))
            rep = RepEmulators(pts)
            # stop rule: the arc must be possible somewhere the mean targets fit
            Cm, _ = sample(em0, rep, 5000, seed=5150 + wave, rounds=10, mean_only=True)
            pm = rep.arc(Cm)[0] if len(Cm) else np.empty(0)
            print(f"mean-target NROY: {len(Cm)} candidates; emulated p max "
                  f"{pm.max() if pm.size else float('nan'):.3f}")
            if not pm.size or pm.max() <= ALPHA:
                print("STOP RULE: no candidate in the mean-target NROY has an emulated p above "
                      f"{ALPHA}")
                return 2
        want = 5 * (a.n if wave != 99 else 10 * a.ensemble)
        C, st = sample(em0, rep, want, seed=2600 + wave)
        print(f"wave {wave}: {st}")
        if not len(C):
            print("no candidates")
            return 2
        rng = np.random.default_rng(2700 + wave)
        if wave == 99:
            m, _ = rep.arc(C)
            top = C[m >= np.quantile(m, 0.9)]
            U = top[rng.choice(len(top), size=min(a.ensemble, len(top)), replace=False)]
            print(f"ensemble: {len(U)} points from the {len(top)} candidates in the top 10 % of "
                  f"emulated p (p >= {np.quantile(m, 0.9):.3f})")
            seeds = ENS_SEEDS
        else:
            U = C[rng.choice(len(C), size=min(a.n, len(C)), replace=False)]
            seeds = REP_SEEDS
        jobs = [hm.job_of(u, s, wave) for u in U for s in seeds]
        name = "ensemble_design.json" if wave == 99 else f"wave{wave}_design.json"
        (hm.OUT / name).write_text(json.dumps({"sampling": st, "jobs": jobs}), encoding="utf-8")
        hm.run_jobs(jobs, a.workers)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
