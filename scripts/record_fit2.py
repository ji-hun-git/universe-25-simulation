#!/usr/bin/env python
"""Record fit 2 (U-3): the record fit with adults on day 315 read as Calhoun counted them, the
mice aged 131 days or more (docs/RECORD_FIT_2.md).

U-1 (scripts/record_fit.py) counted adults from sexual maturity (age >= biology.maturity_days,
a fitted parameter of 42-70 days). Calhoun's "150 adults + 470 immature" on day 315 uses his age
categories, whose adult categories begin at 131 days (docs/RESEARCH_DIGEST.md A6). Everything
else is U-1's: the pen, the settings, the 22 parameters and their ranges, the other 13 targets,
the arc, the sampling and the candidate rule.

The training runs are U-1's waves 1, 2 and 4 (seeds 7000-7005) and M5c's waves (wave 0),
re-measured: each is replayed to day 316 (a run is deterministic for a fixed seed), and the
replay must give the cached run's N and sexually mature count on day 315 exactly, or the run
gets no new value. New runs compute the count themselves (history_match.outputs).

usage:
  python scripts/record_fit2.py --replay [--workers 8]   (U-1's and M5c's runs, re-measured)
  python scripts/record_fit2.py --look                   (what the re-measured runs show)
  python scripts/record_fit2.py --wave 5 --n 120 --workers 10
  python scripts/record_fit2.py --mix-ensemble --workers 10
  python scripts/record_fit2.py --write-ensemble configs/record_fit2_ensemble.json
  python scripts/record_fit2.py --candidate configs/record_fit2_ensemble.json
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import history_match as hm  # noqa: E402
import history_match_rep as hmr  # noqa: E402
import record_fit as rf  # noqa: E402

KEY = "adults_131_at_day_315"
ADULT_AGE = 131.0  # Calhoun's "establishing adult" category begins here
LABEL = "hm_record2"
BASE = "hm_m7_a131"
# (source label, re-measured label, waves): U-1's waves (not its ensemble) and M5c's waves
REPLAYS = (("hm_record", LABEL, (1, 2, 4)), ("hm_m7", BASE, (1, 2, 3)))
DAY = 315


def configure() -> None:
    """U-1's fit with the adults target read from KEY."""
    rf.LABEL = LABEL
    rf.SOURCE = "hm_record waves 1, 2, 4, re-measured (record_fit2.py --replay)"
    rf.BASE = BASE
    rf.OBS_WAVES = {1, 2, 3, 4, 5}
    rf.READ_AS = {"adults_at_day_315": KEY}
    rf.CANDIDATE = ROOT / "configs" / "record_fit2_candidate.json"


def replay_one(run: dict) -> dict:
    """The run's first 316 days: counts by age on day DAY (as replica_report.run_one takes
    them: at the day's last tick)."""
    from universe25.config import load_config
    from universe25.sim import Universe25Sim

    base = dict(seed=run["seed"], days=hm.DAYS, ticks_per_day=6, backend="numpy",
                device="cpu", log_every_ticks=10**9, snapshot_every_days=0)
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="u25rp_", ignore_cleanup_errors=True) as tmp:
        cfg = load_config(ROOT / "configs" / hm.CONF, {**base, **run["params"]})
        sim = Universe25Sim(cfg, Path(tmp))
        a, bio = sim.agents, cfg.biology
        out: dict = {}
        for _ in range((DAY + 1) * 6):
            sim.step()
            if sim.tick % 6 == 0 and int(round(sim.day)) == DAY:
                al = a.alive
                out = {"n": int(al.sum()),
                       "mature": int(np.sum(al & (a.age_days >= bio.maturity_days))),
                       "age131": int(np.sum(al & (a.age_days >= ADULT_AGE))),
                       "weaned": int(np.sum(al & (a.age_days >= bio.weaning_days)))}
                break
        close = getattr(getattr(sim, "logger", None), "close", None)
        if callable(close):
            close()
    if not out:
        raise RuntimeError(f"run {run['key']} did not reach day {DAY}")
    out["secs"] = time.perf_counter() - t0
    return out


def replay(workers: int) -> int:
    """Re-measure the training runs into the new labels (resumable)."""
    for src, dst, waves in REPLAYS:
        runs = [r for r in hmr.load(src) if r["wave"] in waves]
        out = ROOT / "_output" / dst
        out.mkdir(parents=True, exist_ok=True)
        path = out / "runs.jsonl"
        done = set()
        if path.exists():
            done = {json.loads(x)["key"] for x in path.read_text(encoding="utf-8").splitlines()
                    if x}
        todo = [r for r in runs if r["key"] not in done]
        print(f"{src} waves {waves}: {len(runs)} runs, {len(todo)} to replay into {dst}",
              flush=True)
        t0 = time.perf_counter()
        bad = 0
        with ProcessPoolExecutor(max_workers=workers) as ex, \
                path.open("a", encoding="utf-8") as fh:
            futs = {ex.submit(replay_one, r): r for r in todo}
            for k, f in enumerate(as_completed(futs), 1):
                r, m = futs[f], f.result()
                o = r["outputs"]
                ok = bool(m["n"] == o["n_at_day_315"] and m["mature"] == o["adults_at_day_315"])
                o[KEY] = float(m["age131"]) if ok else float("nan")
                o["n_weaned_at_day_315"] = float(m["weaned"]) if ok else float("nan")
                r["replay"] = {"source": src, "match": ok, **m}
                fh.write(json.dumps(r, default=float) + "\n")
                fh.flush()
                bad += not ok
                if k % 50 == 0 or k == len(todo):
                    print(f"  {k}/{len(todo)} replayed, {bad} not matching, "
                          f"{time.perf_counter() - t0:.0f} s", flush=True)
        all_runs = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]
        n_ok = sum(r["replay"]["match"] for r in all_runs)
        print(f"{dst}: {len(all_runs)} runs, {n_ok} match the cached run on day {DAY}, "
              f"{len(all_runs) - n_ok} do not", flush=True)
    return 0


def raw_load(label: str) -> list[dict]:
    path = ROOT / "_output" / label / "runs.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def single_run_close(o: dict, names: list[str]) -> np.ndarray:
    """Per target: is a single run within 3 sd of the record (observation and discrepancy sd,
    on the comparison scale)?"""
    out = []
    for name in names:
        y = o.get(name, np.nan)
        z, var = hm.target(name)
        out.append(bool(np.isfinite(y)
                        and abs(hm.transform(name, np.array([y]))[0] - z) <= 3 * np.sqrt(var)))
    return np.array(out)


def look_one(runs: list[dict], em0: hm.Emulators, tag: str) -> dict:
    """The NROY and the best observed points of waves 1, 2 and 4 under one reading."""
    pts = hmr.points(runs, {1, 2, 4}, len(hmr.REP_SEEDS))
    rep = hmr.RepEmulators(pts)
    C, st = hmr.sample(em0, rep, 10 ** 9, seed=4242, rounds=4, mean_only=True)
    m = rep.arc(C)[0] if len(C) else np.empty(0)
    names = [k for _, k, *_ in hm.PARAMS]
    jm = names.index("maturity_days")
    region = C[m >= rf.P_MIN] if len(C) else C
    res = {"reading": tag, "n_points": len(pts), "tried": st["tried"],
           "mean_nroy": int(len(C)), "mean_nroy_frac_box": len(C) / st["tried"],
           "sampling_region": int(len(region)),
           "sampling_region_frac_box": len(region) / st["tried"]}
    if len(C):
        res["p_quantiles"] = np.quantile(m, [0.05, 0.5, 0.95]).tolist()
    for nm, X in (("mean_nroy", C), ("sampling_region", region)):
        if len(X):
            res[f"maturity_days[{nm}]"] = np.quantile(hmr.raw(X, jm), [0.05, 0.5, 0.95]).tolist()
    va = hmr.v_arc([p["runs"] for p in pts])
    rows = []
    for p in pts:
        sc = hmr.score(p["runs"], va)
        if len(sc["arc_seeds"]) >= 4:
            ad = [r["outputs"]["adults_at_day_315"] for r in p["runs"]]
            rows.append({"wave": p["wave"], "arc": len(sc["arc_seeds"]), "i2": sc["i2"],
                         "adults_315_mean": float(np.nanmean(ad)),
                         "maturity_days": p["params"]["biology"]["maturity_days"],
                         "worst": sorted(sc["implausibility"].items(), key=lambda t: -t[1])[:3]})
    rows.sort(key=lambda t: t["i2"])
    res["n_points_arc4"] = len(rows)
    res["best_observed"] = rows[:6]
    print(f"\n[{tag}] {len(pts)} points of waves 1, 2, 4. Mean-target NROY "
          f"{res['mean_nroy_frac_box']:.4g} of the box; with emulated arc frequency >= "
          f"{rf.P_MIN} {res['sampling_region_frac_box']:.4g} ({len(region)} of {st['tried']})")
    if "p_quantiles" in res:
        print("  emulated arc frequency over the mean NROY, 5/50/95 %: "
              + " / ".join(f"{v:.3f}" for v in res["p_quantiles"]))
    for nm in ("mean_nroy", "sampling_region"):
        if f"maturity_days[{nm}]" in res:
            print(f"  maturity_days in the {nm.replace('_', ' ')}, 5/50/95 %: "
                  + " / ".join(f"{v:.1f}" for v in res[f"maturity_days[{nm}]"]))
    print(f"  points with the arc on >= 4 of 6 seeds: {len(rows)}; the best by I2:")
    for t in rows[:6]:
        print(f"    wave {t['wave']} arc {t['arc']}/6 I2 {t['i2']:.2f} adults@315 "
              f"{t['adults_315_mean']:.0f} maturity {t['maturity_days']:.1f}; worst: "
              + ", ".join(f"{n} {v:.1f}" for n, v in t["worst"]))
    return res


def look() -> int:
    """Before any new run: what the re-measured training runs show, under U-1's reading and
    under Calhoun's (as U-1's preregistration reported its --fit)."""
    configure()
    rf.setup()
    hm.PARAMS = hm.param_set(True)
    hm.FIXED = hmr.FIXED
    hm.OUT = ROOT / "_output" / LABEL
    new = hm.load_runs()  # read through READ_AS
    n_ok = sum(r.get("replay", {}).get("match", False) for r in new)
    base_new = hmr.load(BASE)
    b_ok = sum(r.get("replay", {}).get("match", False) for r in base_new)
    print(f"{LABEL}: {len(new)} runs, {n_ok} re-measured; {BASE}: {len(base_new)} runs, "
          f"{b_ok} re-measured")
    old = raw_load(LABEL)  # the same runs, adults read from sexual maturity as in U-1
    res: dict = {"runs": len(new), "re_measured": n_ok, "base_runs": len(base_new),
                 "base_re_measured": b_ok}
    em0_new = hmr.base_emulators()
    em0_old = hm.Emulators([r for r in raw_load(BASE) if r["wave"] != 99])
    res["u1_reading"] = look_one(old, em0_old, "U-1: adults from sexual maturity")
    res["calhoun_reading"] = look_one(new, em0_new, "U-3: adults aged 131 days or more")
    # single runs (exploratory, as NOTES 2026-11-19): how close can one run come?
    names = rf.MEAN + rf.COND
    i315 = [names.index("n_at_day_315"), names.index("adults_at_day_315")]
    for tag, runs in (("u1_reading", old), ("calhoun_reading", new)):
        arc = [r for r in runs if hmr.is_arc(r["outputs"])]
        close = np.array([single_run_close(r["outputs"], names) for r in arc]) if arc else \
            np.zeros((0, len(names)), bool)
        res[tag]["single_runs"] = {
            "runs": len(runs), "arc_runs": len(arc),
            "within_3sd_on_12_of_14": int(np.sum(close.sum(axis=1) >= 12)),
            "both_day315_within_3sd": int(np.sum(close[:, i315].all(axis=1))),
            "adults_315_within_3sd": int(np.sum(close[:, i315[1]]))}
        s = res[tag]["single_runs"]
        print(f"\n[{tag}] single runs: {s['arc_runs']} of {s['runs']} show the arc; "
              f"{s['within_3sd_on_12_of_14']} within 3 sd on >= 12 of 14; adults@315 within "
              f"3 sd in {s['adults_315_within_3sd']}, both day-315 numbers in "
              f"{s['both_day315_within_3sd']}")
    (ROOT / "_output" / LABEL / "look.json").write_text(json.dumps(res, indent=1, default=float),
                                                       encoding="utf-8")
    print(f"\nwritten _output/{LABEL}/look.json")
    return 0


def main() -> int:
    args = sys.argv[1:]
    workers = int(args[args.index("--workers") + 1]) if "--workers" in args else 8
    if "--replay" in args:
        return replay(workers)
    if "--look" in args:
        return look()
    if "--init" in args:
        print("U-3 starts from --replay, not --init")
        return 1
    configure()
    return rf.main()


if __name__ == "__main__":
    raise SystemExit(main())
