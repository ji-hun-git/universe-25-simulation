"""Pre-evolution for the inherited-weight policy `evo` (P4-4; docs/PHASE4_DESIGN.md 4.4).

Serial founding epochs on the canonical substrate (`configs/default.yaml`, ABUND-PG, 6 ticks
per day, NumPy, 12 sub-steps): an epoch starts with 8 founder pairs (2 per corner cell) and
runs 360 days under the calibrated conception gate. The next epoch's 8 female and 8 male
founders are drawn uniformly without replacement from the adults alive on day 360, by sex
(with replacement for the rest when fewer than 8 of a sex are alive); their genomes carry over
and everything else restarts. A lineage with no adult female or no adult male on day 360 ends.

Lineage l draws its generation 0 and its founders from `SeedSequence([7000 + l - 1, LINEAGE
stream])`; inside an epoch the policy's streams carry the key (l, epoch); the epochs' simulation
seeds cycle through the training band 7000-7009. Evaluation seeds are never used here.

Outputs per lineage: pool_gen0.npz (generation 0), epochs.jsonl (one row per epoch),
pool_final.npz (the adults alive at the end of the last epoch), pool_neu.npz (the neutral
Wright-Fisher control matched in pedigree depth), summary.json; state.json / state.npz make a
lineage resumable at every epoch. Nothing here reads a detector, a trace or a PlayScore field,
and there is no reward anywhere (H2).

SCARCE-PG evo (PHASE4_DESIGN.md 4.6) uses the same epochs with optional arguments, all off by
default (H-h's lineages are unchanged): config overrides (the scarce food rule), an extra key
element for the policy streams, a lineage stream of its own, generation 0 loaded from a given
pool, a stop once the day-360 adults reach a mean pedigree depth, no neutral pool, and
read-only daily probes of the weaned animals' hunger.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from universe25.agents.evo import (
    LINEAGE_STREAM,
    NEUTRAL_STREAM,
    SEX_ANY,
    genome_norms,
    load_pool,
    neutral_pool,
    random_genomes,
    save_pool,
    stream,
)
from universe25.agents.state import SEX_F, SEX_M
from universe25.config import load_config
from universe25.sim import Universe25Sim

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "configs" / "default.yaml"
TRAIN_SEEDS = tuple(range(7000, 7010))
PAIRS = 8
EPOCH_DAYS = 360.0
EPOCHS = 150
NEUTRAL_SIZE = 64
MUTATION_SD = 0.02
CHECKPOINT_EVERY = 25  # founders kept for inspection every this many epochs
PROBE_HUNGRY = 0.85  # the forced-foraging reflex (sim._select_actions)
PROBE_STARVING = 1.2  # the starvation hazard's threshold (sim mortality)


def lineage_seed(lineage: int) -> int:
    return 7000 + int(lineage) - 1


def epoch_sim_seed(lineage: int, epoch: int) -> int:
    return TRAIN_SEEDS[(int(lineage) - 1 + int(epoch)) % len(TRAIN_SEEDS)]


def generation0(rng: np.random.Generator, pairs: int = PAIRS) -> dict[str, np.ndarray]:
    """Independent generation-0 genomes for one epoch's founders, in slot order (F, M, ...)."""
    sex = np.tile([SEX_F, SEX_M], int(pairs)).astype(np.int64)
    return {"genomes": random_genomes(rng, 2 * int(pairs)),
            "depth": np.zeros(2 * int(pairs), np.int64), "sex": sex}


def sample_founders(rng: np.random.Generator, pool: dict[str, np.ndarray],
                    pairs: int = PAIRS) -> dict[str, np.ndarray] | None:
    """The next epoch's founders from the adults in `pool`, by sex, in slot order (F, M, ...);
    None when a sex has no adult."""
    picks = {}
    for s in (SEX_F, SEX_M):
        cand = np.flatnonzero(pool["sex"] == s)
        if cand.size == 0:
            return None
        k = min(int(pairs), cand.size)
        first = rng.choice(cand, size=k, replace=False)
        rest = (rng.choice(cand, size=int(pairs) - k, replace=True) if k < int(pairs)
                else np.zeros(0, np.int64))
        picks[s] = np.concatenate([first, rest])
    order = np.empty(2 * int(pairs), np.int64)
    order[0::2] = picks[SEX_F]
    order[1::2] = picks[SEX_M]
    return {"genomes": pool["genomes"][order], "depth": pool["depth"][order],
            "sex": pool["sex"][order]}


def _probe_row(sim: Universe25Sim) -> tuple[float, int, float, float, float, float]:
    """Read-only: day, weaned count, the weaned animals' mean hunger, the shares of them above
    the forced-foraging reflex and above starvation, and the share above thirst starvation."""
    a = sim.agents
    w = a.alive & (a.age_days >= sim.cfg.biology.weaning_days)
    n = int(w.sum())
    if n == 0:
        return float(sim.day), 0, float("nan"), float("nan"), float("nan"), float("nan")
    h = a.hunger[w].astype(np.float64)
    th = a.thirst[w].astype(np.float64)
    return (float(sim.day), n, float(h.mean()), float((h > PROBE_HUNGRY).mean()),
            float((h > PROBE_STARVING).mean()), float((th > PROBE_STARVING).mean()))


def _finite_mean(x: np.ndarray) -> float | None:
    x = x[np.isfinite(x)]
    return float(x.mean()) if x.size else None


def _probe_summary(rows: list[tuple[float, int, float, float, float, float]],
                   days: float) -> dict[str, Any]:
    """The probes of one epoch: the weaned count on its last day, and means over its second
    half (days after days / 2) of the weaned count, mean hunger and the three shares, with the
    largest daily starvation shares."""
    if not rows:
        return {"days": 0, "weaned_end": 0}
    P = np.asarray(rows, dtype=np.float64)
    half = P[:, 0] > 0.5 * float(days)
    starving = P[:, 4][np.isfinite(P[:, 4])]
    thirsty = P[:, 5][np.isfinite(P[:, 5])]
    return {"days": int(P.shape[0]), "weaned_end": int(P[-1, 1]),
            "weaned_mean_2h": _finite_mean(P[half, 1]),
            "hunger_mean_2h": _finite_mean(P[half, 2]),
            "hungry_share_2h": _finite_mean(P[half, 3]),
            "starving_share_2h": _finite_mean(P[half, 4]),
            "starving_share_max": float(starving.max()) if starving.size else None,
            "thirst_starving_share_2h": _finite_mean(P[half, 5]),
            "thirst_starving_share_max": float(thirsty.max()) if thirsty.size else None}


def run_epoch(founders: dict[str, np.ndarray], lineage: int, epoch: int,
              days: float = EPOCH_DAYS, sim_seed: int | None = None,
              mutation_sd: float = MUTATION_SD, *, overrides: dict[str, Any] | None = None,
              key_extra: tuple[int, ...] = (),
              probe: bool = False) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """One founding epoch; returns the adults alive at its end (genomes, depth, sex) and the
    epoch's statistics. `overrides` are merged into the epoch's config (never `policy`),
    `key_extra` is appended to the policy streams' key (lineage, epoch), and `probe` adds the
    read-only daily hunger probes; the defaults are H-h's epoch."""
    tmp = Path(tempfile.mkdtemp(prefix="u25evo_"))
    try:
        fpath = tmp / "founders.npz"
        save_pool(fpath, founders["genomes"], founders["depth"], founders["sex"])
        pairs = founders["genomes"].shape[0] // 2
        seed = epoch_sim_seed(lineage, epoch) if sim_seed is None else int(sim_seed)
        over = dict(seed=seed, days=float(days), ticks_per_day=6, backend="numpy", device="cpu",
                    initial_pairs=int(pairs), log_every_ticks=10**9, snapshot_every_days=0,
                    free_substeps=12,
                    policy={"kind": "evo", "founders": str(fpath), "founder_mode": "ordered",
                            "mutation_sd": float(mutation_sd),
                            "genetics_key": [int(lineage), int(epoch),
                                             *(int(k) for k in key_extra)]})
        if overrides:
            if "policy" in overrides:
                raise ValueError("epoch overrides may not replace the policy")
            over.update(overrides)
        cfg = load_config(BASE, over)
        t0 = time.perf_counter()
        sim = Universe25Sim(cfg, tmp / "run")
        probes: list[tuple[float, int, float, float, float, float]] = []
        for t in range(int(round(float(days) * cfg.ticks_per_day))):
            sim.step()
            if probe and (t + 1) % cfg.ticks_per_day == 0:
                probes.append(_probe_row(sim))
            if sim.agents.n_alive == 0:
                break
        pol = sim.policy
        pool = pol.adults(sim)
        hist = sim._action_hist.astype(np.float64)
        stats = {
            "lineage": int(lineage), "epoch": int(epoch), "sim_seed": int(seed),
            "n_end": int(sim.agents.n_alive), "peak_n": int(sim._peak_n),
            "births": int(sim._births), "surviving_births": int(sim._surv_births_cum),
            "conceptions": int(sim._conceptions), "deaths": int(sim._deaths),
            "litters_dropped": int(sim._litters_dropped), "nan_count": int(sim._nan_count),
            "adults_f": int((pool["sex"] == SEX_F).sum()),
            "adults_m": int((pool["sex"] == SEX_M).sum()),
            "founder_depth_mean": float(np.mean(founders["depth"])),
            "adult_depth_mean": float(pool["depth"].mean()) if pool["depth"].size else None,
            "adult_depth_max": int(pool["depth"].max()) if pool["depth"].size else None,
            "births_from_sire": int(pol.n_from_sire), "policy_births": int(pol.n_births),
            "genome_norms_adults": genome_norms(pool["genomes"]),
            "decision_action_shares": (hist / max(hist.sum(), 1.0)).round(5).tolist(),
            "eligible_action_shares": (sim._eligible_hist / max(sim._eligible_hist.sum(), 1))
            .round(5).tolist(),
            "wall_s": time.perf_counter() - t0,
        }
        if probe:
            stats["probe"] = _probe_summary(probes, days)
        sim.logger.close()
        return {k: pool[k] for k in ("genomes", "depth", "sex")}, stats
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def evolve_lineage(lineage: int, out_dir: Path, epochs: int = EPOCHS, days: float = EPOCH_DAYS,
                   pairs: int = PAIRS, mutation_sd: float = MUTATION_SD,
                   sim_seed: int | None = None,
                   progress: Callable[[dict[str, Any]], None] | None = None, *,
                   overrides: dict[str, Any] | None = None, key_extra: tuple[int, ...] = (),
                   lineage_stream: int = LINEAGE_STREAM, gen0_pool: Path | None = None,
                   stop_depth: float | None = None, neutral: bool = True,
                   probe: bool = False) -> dict[str, Any]:
    """Run (or resume) one lineage to `epochs` epochs, then build its neutral control.

    The keyword arguments are SCARCE-PG evo's (PHASE4_DESIGN.md 4.6) and default to H-h's
    lineage: `overrides` and `key_extra` go to every epoch (run_epoch); founders between epochs
    are drawn from `stream(lineage_seed, lineage_stream)`; `gen0_pool` gives generation 0 (in
    slot order) instead of drawing it; with `stop_depth` the lineage stops after the first epoch
    whose day-360 adults have at least that mean pedigree depth (`epochs` is then the cap);
    `neutral` False skips the neutral pool; `probe` records the daily hunger probes."""
    out = Path(out_dir) / f"lineage_{int(lineage)}"
    out.mkdir(parents=True, exist_ok=True)
    st_json, st_npz, log = out / "state.json", out / "state.npz", out / "epochs.jsonl"
    rng = stream(lineage_seed(lineage), lineage_stream)
    if st_json.exists():
        st = json.loads(st_json.read_text(encoding="utf-8"))
        e0, ended = int(st["next_epoch"]), st.get("ended")
        rng.bit_generator.state = st["rng"]
        founders = load_pool(st_npz)
        if log.exists():  # drop rows of epochs that will run again
            rows = [r for r in log.read_text(encoding="utf-8").splitlines()
                    if r.strip() and json.loads(r)["epoch"] < e0]
            log.write_text("".join(r + "\n" for r in rows), encoding="utf-8")
    else:
        if gen0_pool is None:
            founders = generation0(rng, pairs)
        else:
            g0 = load_pool(gen0_pool)
            founders = {k: g0[k] for k in ("genomes", "depth", "sex")}
            if founders["genomes"].shape[0] != 2 * int(pairs):
                raise ValueError(f"generation 0 {gen0_pool}: {founders['genomes'].shape[0]} "
                                 f"genomes for {pairs} pairs")
        save_pool(out / "pool_gen0.npz", founders["genomes"], founders["depth"],
                  founders["sex"])
        e0, ended = 0, None
    pool = None
    reached = False
    t_start = time.perf_counter()
    for e in range(e0, int(epochs)):
        if ended:
            break
        pool, stats = run_epoch(founders, lineage, e, days, sim_seed, mutation_sd,
                                overrides=overrides, key_extra=key_extra, probe=probe)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(stats) + "\n")
        if progress:
            progress(stats)
        if stats["nan_count"]:
            ended = f"NaN in epoch {e}"
        depth = stats["adult_depth_mean"]
        reached = bool(stop_depth is not None and depth is not None
                       and depth >= float(stop_depth))
        if e == int(epochs) - 1 or ended or reached:
            save_pool(out / "pool_final.npz", pool["genomes"], pool["depth"], pool["sex"],
                      epoch=e)
            break
        nxt = sample_founders(rng, pool, pairs)
        if nxt is None:
            ended = f"no adult of a sex on day {days:g} of epoch {e}"
        else:
            founders = nxt
            if (e + 1) % CHECKPOINT_EVERY == 0:
                save_pool(out / f"founders_e{e + 1:04d}.npz", founders["genomes"],
                          founders["depth"], founders["sex"])
        save_pool(st_npz, founders["genomes"], founders["depth"], founders["sex"])
        st_json.write_text(json.dumps({"next_epoch": e + 1, "rng": rng.bit_generator.state,
                                       "ended": ended}), encoding="utf-8")
        if ended:
            break
    summ: dict[str, Any] = {"lineage": int(lineage), "epochs_target": int(epochs),
                            "ended": ended, "wall_s_this_call": time.perf_counter() - t_start}
    if stop_depth is not None:
        summ.update(stop_depth=float(stop_depth), depth_reached=bool(reached))
    if overrides or key_extra or gen0_pool is not None or lineage_stream != LINEAGE_STREAM:
        summ["setup"] = {"overrides": overrides or {}, "key_extra": [int(k) for k in key_extra],
                         "lineage_stream": int(lineage_stream),
                         "gen0_pool": None if gen0_pool is None else str(gen0_pool)}
    fin = out / "pool_final.npz"
    if fin.exists() and not ended:
        final = load_pool(fin)
        gen0 = load_pool(out / "pool_gen0.npz")
        summ.update(final_adults=int(final["depth"].size),
                    final_depth_mean=float(final["depth"].mean()))
        if neutral:
            g = int(round(float(final["depth"].mean())))
            neu = neutral_pool(gen0["genomes"], g, NEUTRAL_SIZE, mutation_sd,
                               stream(lineage_seed(lineage), NEUTRAL_STREAM))
            save_pool(out / "pool_neu.npz", neu, np.full(NEUTRAL_SIZE, g, np.int64),
                      np.full(NEUTRAL_SIZE, SEX_ANY, np.int64))
            summ.update(neutral_generations=g, final_norms=genome_norms(final["genomes"]),
                        neutral_norms=genome_norms(neu))
        else:
            summ.update(final_norms=genome_norms(final["genomes"]))
        summ.update(gen0_norms=genome_norms(gen0["genomes"]))
    (out / "summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    return summ
