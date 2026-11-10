#!/usr/bin/env python
"""P4-15: does the learner's free time depend on object consequences? (PHASE4_DESIGN.md 4.2,
preregistered 2026-11-10.)

  python scripts/p415.py manip [--workers 3]   manipulation check (training data only)
  python scripts/p415.py eval [--workers 6]    evaluation on seeds 9100-9111, primary test,
                                               and the gated secondary if the primary passes

Arms: A0 = _output/pretrain/p415_a0/policy_final.npz, A1 = _output/pretrain/p415_a1/..., R =
MlpFrozenPolicy.random_init(7007). Substrate: configs/default.yaml with ball physics on,
novelty off, K = 12 (sub-step mode auto: rechoose), 6 ticks/day, 1,010 d, traced windows
[400, 410), [700, 710), [1000, 1010), every fourth individual.

Primary statistic per window: over free-time sub-step rows whose previous row (the state the
animal chose from) has its nearest object within 5 in, delta = P(object-family action | nearest
object a ball) - P(object-family action | nearest object a tunnel or ramp); per seed, the mean
over windows. Test: A1 - R paired by seed, exact sign-flip test over the 12 seeds, one-sided;
passes iff the mean difference >= 0.05 and p < 0.025. A0 - R and A1 - A0 are reported.
Manipulation check: A1's surviving-birth fraction over its last 10 nursery episodes >= 0.8 x
A0's, and A1's colony N >= 100 at day 1,010 on training seeds 7000-7002.
Writes _output/p415/.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "_output" / "p415"
PRE = ROOT / "_output" / "pretrain"
WINDOWS = [(400.0, 410.0), (700.0, 710.0), (1000.0, 1010.0)]
EVAL_SEEDS = tuple(range(9100, 9112))
TRAIN_SEEDS = (7000, 7001, 7002)
RANDOM_INIT = 7007
FLOOR = 0.05
ALPHA = 0.025
NEAR_IN = 5.0


def weights(arm: str) -> Path:
    if arm == "R":
        return OUT / f"policy_random_init{RANDOM_INIT}.npz"
    return PRE / f"p415_{arm.lower()}" / "policy_final.npz"


def run_one(job: tuple[str, int, bool]) -> tuple[str, float]:
    arm, seed, traced = job
    d = OUT / ("eval" if traced else "manip") / f"{arm}_{seed}"
    done = (d / "run.json").exists() and (not traced or all(
        (d / f"trace_{a:g}_{b:g}.npz").exists() for a, b in WINDOWS))
    if done:
        return str(d), 0.0
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    over = dict(seed=seed, days=1010.0, ticks_per_day=6, backend="numpy", device="cpu",
                log_every_ticks=6, snapshot_every_days=0, free_substeps=12,
                playground={"ball_physics": True},
                policy={"kind": "mlp_frozen", "weights": str(weights(arm))})
    if traced:
        over["trace"] = {"windows": WINDOWS, "sample_every": 4}
    t0 = time.perf_counter()
    Universe25Sim(load_config(ROOT / "configs" / "default.yaml", over), d).run()
    return str(d), time.perf_counter() - t0


def window_delta(trace_file: Path, n_balls: int) -> dict:
    """Primary statistic of one traced window (see the module docstring)."""
    from universe25.agents.state import (
        ACT_BACK_OFF, ACT_CIRCLE, ACT_EXPLORE, ACT_MANIPULATE, ACT_RUN_ON, ACT_SOCIAL,
        ACT_TURN_BACK, OBJECT_FAMILY)
    from universe25.metrics.trace import load_trace

    free = (ACT_EXPLORE, ACT_SOCIAL, ACT_MANIPULATE, ACT_RUN_ON, ACT_TURN_BACK, ACT_BACK_OFF,
            ACT_CIRCLE)
    t = load_trace(trace_file)
    o = np.lexsort((t["step"], t["uid"]))
    uid, step, act = t["uid"][o], t["step"][o], t["action"][o]
    oid, od = t["obj_id"][o], t["obj_dist"][o]
    prev_ok = np.zeros(uid.size, bool)
    prev_ok[1:] = (uid[1:] == uid[:-1]) & (step[1:] == step[:-1] + 1)
    p_oid = np.r_[-1, oid[:-1]]
    p_od = np.r_[np.inf, od[:-1]]
    sel = prev_ok & np.isin(act, free) & (p_od < NEAR_IN) & (p_oid >= 0)
    is_obj = np.isin(act, OBJECT_FAMILY)
    ball = sel & (p_oid < n_balls)
    fixed = sel & (p_oid >= n_balls)
    out = {"n_ball_rows": int(ball.sum()), "n_fixed_rows": int(fixed.sum())}
    if ball.sum() and fixed.sum():
        out["p_ball"] = float(is_obj[ball].mean())
        out["p_fixed"] = float(is_obj[fixed].mean())
        out["delta"] = out["p_ball"] - out["p_fixed"]
    else:
        out["delta"] = float("nan")
    return out


def seed_delta(d: Path) -> dict:
    cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
    n_balls = int(cfg["playground"]["n_balls"])
    wins = {f.stem: window_delta(f, n_balls) for f in sorted(d.glob("trace_*.npz"))}
    vals = [w["delta"] for w in wins.values() if np.isfinite(w["delta"])]
    return {"windows": wins, "delta": float(np.mean(vals)) if vals else float("nan")}


def sign_flip(diff: np.ndarray) -> float:
    """Exact one-sided sign-flip p: share of the 2^n sign patterns with mean >= observed."""
    diff = diff[np.isfinite(diff)]
    obs = diff.mean()
    pats = np.array(list(itertools.product((1.0, -1.0), repeat=diff.size)))
    return float(np.mean((pats * diff).mean(axis=1) >= obs - 1e-12))


def compare(name: str, a: np.ndarray, b: np.ndarray) -> dict:
    d = a - b
    ok = np.isfinite(d)
    mean = float(d[ok].mean()) if ok.any() else float("nan")
    p = sign_flip(d) if ok.sum() >= 2 else float("nan")
    res = {"n": int(ok.sum()), "mean_diff": mean,
           "se": float(d[ok].std(ddof=1) / np.sqrt(ok.sum())) if ok.sum() > 1 else float("nan"),
           "p_one_sided": p, "passes": bool(np.isfinite(mean) and mean >= FLOOR and p < ALPHA)}
    print(f"{name:8s} mean {mean:+.4f} ± {res['se']:.4f} (n {res['n']}), sign-flip p {p:.4f}"
          f" -> {'PASS' if res['passes'] else 'no'}", flush=True)
    return res


def manip(workers: int) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fr = {}
    for arm in ("A0", "A1"):
        E = [json.loads(line) for line in
             (PRE / f"p415_{arm.lower()}" / "episodes.jsonl").read_text().splitlines()]
        last = E[-10:]
        fr[arm] = float(np.mean([e["surviving_births"] / max(1, e["births"]) for e in last]))
    ok_care = fr["A1"] >= 0.8 * fr["A0"]
    print(f"nursery surviving-birth fraction, last 10 episodes: A0 {fr['A0']:.3f}, A1 "
          f"{fr['A1']:.3f} (needs >= {0.8 * fr['A0']:.3f}) -> {'ok' if ok_care else 'FAIL'}")
    with ProcessPoolExecutor(max_workers=workers) as ex:
        paths = list(ex.map(run_one, [("A1", s, False) for s in TRAIN_SEEDS]))
    n_end = {}
    for p, _ in paths:
        n_end[Path(p).name] = json.loads((Path(p) / "run.json").read_text())["final_n"]
    ok_viable = all(v >= 100 for v in n_end.values())
    print(f"A1 colony N at day 1,010 on training seeds: {n_end} (needs >= 100 each) -> "
          f"{'ok' if ok_viable else 'FAIL'}")
    passed = bool(ok_care and ok_viable)
    print(f"manipulation check: {'PASS' if passed else 'FAIL - stop, read no evaluation seed'}")
    (OUT / "manipulation_check.json").write_text(json.dumps(
        {"surviving_birth_fraction_last10": fr, "care_ok": ok_care, "final_n_train": n_end,
         "viable_ok": ok_viable, "pass": passed}, indent=1), encoding="utf-8")
    return 0


def evaluate(workers: int) -> int:
    mc = OUT / "manipulation_check.json"
    if not mc.exists() or not json.loads(mc.read_text())["pass"]:
        raise SystemExit("the manipulation check has not passed: no evaluation seed is read")
    from universe25.agents.policy import MlpFrozenPolicy

    if not weights("R").exists():
        MlpFrozenPolicy.random_init(RANDOM_INIT).save_npz(str(weights("R")))
    jobs = [(arm, s, True) for arm in ("A0", "A1", "R") for s in EVAL_SEEDS]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        list(ex.map(run_one, jobs))
    print(f"runs done in {time.perf_counter() - t0:.0f} s", flush=True)
    per = {arm: {s: seed_delta(OUT / "eval" / f"{arm}_{s}") for s in EVAL_SEEDS}
           for arm in ("A0", "A1", "R")}
    vec = {arm: np.array([per[arm][s]["delta"] for s in EVAL_SEEDS]) for arm in per}
    for arm in vec:
        print(f"{arm}: per-seed delta mean {np.nanmean(vec[arm]):+.4f} "
              f"[{np.nanmin(vec[arm]):+.4f}, {np.nanmax(vec[arm]):+.4f}]", flush=True)
    res = {"primary_A1_minus_R": compare("A1 - R", vec["A1"], vec["R"]),
           "A0_minus_R": compare("A0 - R", vec["A0"], vec["R"]),
           "A1_minus_A0": compare("A1 - A0", vec["A1"], vec["A0"])}
    summary: dict = {"per_seed": per, "tests": res, "floor": FLOOR, "alpha": ALPHA}
    if res["primary_A1_minus_R"]["passes"]:
        print("\nprimary passed: the gated secondary (amended H-f, rules v9 form excess)")
        from detect import detect_run

        for arm in ("A1", "R"):
            for s in EVAL_SEEDS:
                d = OUT / "eval" / f"{arm}_{s}"
                if not (d / "detectors_unvalidated.json").exists():
                    detect_run(d, 1000, 400, 0)
        sec = {}
        for kind in ("object", "locomotor"):
            fe = {}
            for arm in ("A1", "R"):
                vals = []
                for s in EVAL_SEEDS:
                    det = json.loads((OUT / "eval" / f"{arm}_{s}" /
                                      "detectors_unvalidated.json").read_text())
                    ex = [w[kind].get("seq_struct_form_excess_unvalidated", np.nan)
                          for w in det["windows"].values()]
                    ex = [v for v in ex if v is not None and np.isfinite(v)]
                    vals.append(float(np.mean(ex)) if ex else float("nan"))
                fe[arm] = np.array(vals)
            sec[kind] = compare(f"H-f {kind[:3]}", fe["A1"], fe["R"])
        summary["secondary_form_excess"] = sec
    else:
        print("\nprimary failed: the stop rule applies (no further substrate change for PPO)")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float),
                                      encoding="utf-8")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("manip", "eval"))
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    return manip(a.workers) if a.mode == "manip" else evaluate(a.workers)


if __name__ == "__main__":
    raise SystemExit(main())
