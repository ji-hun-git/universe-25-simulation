"""Nursery worlds for pre-training the learner (P4-3; PHASE4_DESIGN.md 1.6).

A nursery is a short episode on the frozen biology, seeded with a mixed colony instead of
Calhoun's four pairs: adults and juveniles spread over all 16 cells, pregnant females, and
nursing mothers with litters of various ages, so maternal situations exist from the first day
(in P4-2 the learner learned to avoid the nest during the weeks before any litter existed).
Every episode draws a new world: colony size and composition, abundant or scarce food, and
whether the playground is open and how many objects it holds. Simulation seeds cycle through the
training band 7000-7009; evaluation seeds (8000-8011) are never used here.

The learner itself is not built here: the caller keeps one `MlpPpoPolicy` across episodes and
installs it in each nursery simulation (`attach`). Nothing here reads a detector, a trace or a
PlayScore field.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from universe25.agents.state import (
    ROLE_BREEDING_FEMALE,
    ROLE_JUVENILE,
    ROLE_NURSING,
    ROLE_PUP,
    ROLE_SUBORDINATE_MALE,
    SEX_F,
    SEX_M,
)
from universe25.config import load_config
from universe25.sim import Universe25Sim

TRAIN_SEEDS = tuple(range(7000, 7010))
DEFAULT_BASE = Path(__file__).resolve().parents[3] / "configs" / "default.yaml"


@dataclass(frozen=True)
class NurseryParams:
    episode: int
    sim_seed: int
    days: float
    n_adults: int
    frac_juvenile: float
    frac_nursing: float  # of adult females, each with a litter
    frac_pregnant: float  # of the remaining adult females
    resources: str  # "abundant" | "scarce"
    food_per_agent_day: float  # scarce mode: daily food relative to the colony's need
    playground: bool
    n_balls: int
    n_tunnels: int
    n_ramps: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sample_params(rng: np.random.Generator, episode: int, days: float = 60.0) -> NurseryParams:
    """One randomised nursery world (domain randomisation)."""
    scarce = bool(rng.random() < 0.3)
    pg = bool(rng.random() < 0.85)
    return NurseryParams(
        episode=episode,
        sim_seed=TRAIN_SEEDS[episode % len(TRAIN_SEEDS)],
        days=float(days),
        n_adults=int(rng.integers(200, 1501)),
        frac_juvenile=float(rng.uniform(0.0, 0.3)),
        frac_nursing=float(rng.uniform(0.05, 0.3)),
        frac_pregnant=float(rng.uniform(0.0, 0.25)),
        resources="scarce" if scarce else "abundant",
        food_per_agent_day=float(rng.uniform(0.6, 1.1)) if scarce else 0.0,
        playground=pg,
        n_balls=int(rng.integers(0, 13)) if pg else 0,
        n_tunnels=int(rng.integers(0, 7)) if pg else 0,
        n_ramps=int(rng.integers(0, 5)) if pg else 0,
    )


def build_nursery(p: NurseryParams, out_dir: Path, rng: np.random.Generator,
                  free_substeps: int = 12, base: Path | None = None) -> Universe25Sim:
    """A nursery simulation with the seeded colony; its own policy is a placeholder (the caller
    attaches the learner). Sub-steps are re-chosen (the learner's mode)."""
    n_expected = int(p.n_adults * (1 + p.frac_juvenile + 0.5 * p.frac_nursing * 5.5))
    res: dict[str, Any] = {"mode": p.resources}
    if p.resources == "scarce":  # daily food relative to the seeded colony's need
        res["scarce_food_per_day"] = float(p.food_per_agent_day * 1.2 * max(n_expected, 1))
    over = dict(seed=p.sim_seed, days=p.days, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=4096, initial_pairs=0, log_every_ticks=10**9, snapshot_every_days=0,
                free_substeps=int(free_substeps), resources=res,
                playground={"enabled": p.playground, "n_balls": p.n_balls,
                            "n_tunnels": p.n_tunnels, "n_ramps": p.n_ramps},
                policy={"kind": "need_driven", "substep_mode": "rechoose"})
    cfg = load_config(base or DEFAULT_BASE, over)
    sim = Universe25Sim(cfg, Path(out_dir))
    seed_population(sim, p, rng)
    return sim


def seed_population(sim: Universe25Sim, p: NurseryParams, rng: np.random.Generator) -> dict:
    """Spawn the mixed colony: adults (ages 70-400 d) and juveniles (21-60 d) in random nest boxes
    of all 16 cells; nursing mothers with a litter (3-8 pups, 0-18 d old, in her box); pregnant
    females (1-19 d of gestation left). Returns the counts."""
    w = sim.world
    a = sim.agents
    n_juv = int(round(p.n_adults * p.frac_juvenile))
    counts = {"adults": 0, "juveniles": 0, "nursing": 0, "pups": 0, "pregnant": 0}

    def place(slot: int, sex: int, age: float, role: int, nest_id: int | None = None) -> int:
        if nest_id is None:
            nest_id = int(rng.integers(0, w.n_nests))
        nest = w.nests[nest_id]
        sim._spawn(slot, sex=sex, age=float(age), x=nest.x + float(rng.normal(0, 1.0)),
                   y=nest.y + float(rng.normal(0, 1.0)), nest_id=nest_id, cell_id=nest.cell_id,
                   role=role)
        a.hunger[slot] = float(rng.uniform(0.0, 0.6))
        a.thirst[slot] = float(rng.uniform(0.0, 0.6))
        a.fatigue[slot] = float(rng.uniform(0.0, 0.6))
        a.social_drive[slot] = float(rng.uniform(0.0, 0.8))
        a.curiosity[slot] = float(rng.uniform(0.0, 0.8))
        a.boredom[slot] = float(rng.uniform(0.0, 0.5))
        return nest_id

    slots = a.free_slots(p.n_adults + n_juv)
    females: list[tuple[int, float]] = []
    for k, s in enumerate(slots[:p.n_adults]):
        sex = SEX_F if k % 2 == 0 else SEX_M
        age = float(rng.uniform(70.0, 400.0))
        place(int(s), sex, age, ROLE_BREEDING_FEMALE if sex == SEX_F else ROLE_SUBORDINATE_MALE)
        if sex == SEX_F:
            females.append((int(s), age))
        counts["adults"] += 1
    for s in slots[p.n_adults:]:
        place(int(s), int(rng.integers(0, 2)), float(rng.uniform(21.0, 60.0)), ROLE_JUVENILE)
        counts["juveniles"] += 1
    fertile = [s for s, age in females if age <= float(sim.cfg.biology.female_fertile_max_age_days)]
    rng.shuffle(fertile)
    n_nurse = int(round(len(fertile) * p.frac_nursing))
    for s in fertile[:n_nurse]:
        litter = int(rng.integers(3, 9))
        try:
            pups = a.free_slots(litter)
        except RuntimeError:
            break
        a.role[s] = ROLE_NURSING
        a.maternal[s] = 0.8
        pup_age = float(rng.uniform(0.0, 18.0))
        nid = int(a.nest_id[s])
        for q in pups:
            place(int(q), int(rng.integers(0, 2)), pup_age, ROLE_PUP, nest_id=nid)
            a.x[q] = a.x[s] + float(rng.normal(0, 0.3))
            a.y[q] = a.y[s] + float(rng.normal(0, 0.3))
            a.hunger[q] = float(rng.uniform(0.1, 0.5))
            counts["pups"] += 1
        a.x[s] = w.nests[nid].x
        a.y[s] = w.nests[nid].y
        counts["nursing"] += 1
    rest = fertile[n_nurse:]
    n_preg = int(round(len(rest) * p.frac_pregnant))
    for s in rest[:n_preg]:
        a.gestating[s] = float(rng.uniform(1.0, 19.0))
        counts["pregnant"] += 1
    a.n_alive = int(a.alive.sum())
    return counts


# ---------------------------------------------------------------- pre-training loop
def manifest(seed: int) -> dict[str, Any]:
    """Library versions, device and commit for a pre-training run."""
    import importlib.metadata as md
    import platform
    import subprocess

    import torch

    def ver(pkg: str) -> str:
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return "absent"

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                cwd=DEFAULT_BASE.parents[1], timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = "unknown"
    return {
        "seed": int(seed), "python": platform.python_version(), "numpy": np.__version__,
        "torch": torch.__version__, "torch_cuda": torch.version.cuda, "warp": ver("warp-lang"),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "platform": platform.platform(), "commit": commit,
    }


def pretrain(out_dir: Path, steps: float = 1e8, max_episodes: int = 10**6,
             episode_days: float = 60.0, seed: int = 7000, free_substeps: int = 12,
             ckpt_every: int = 5, resume: Path | None = None,
             n_adults_range: tuple[int, int] | None = None,
             ppo: dict[str, Any] | None = None, progress: Any = None) -> dict[str, Any]:
    """Pre-train one shared learner over randomised nursery episodes until `steps` transitions
    (agent-steps: one per policy call) or `max_episodes`. Writes episodes.jsonl,
    learn_log.jsonl, checkpoints/ (ckpt_epNNNN.pt and latest.pt), policy_final.npz (the
    mlp_frozen layout) and manifest.json under `out_dir`. A resumed run continues bit for bit."""
    import json
    import shutil
    import tempfile
    import time

    import torch

    from universe25.agents.policy import make_policy
    from universe25.config import PolicyConfig, PPOConfig
    from universe25.learn.reward import drive, read_drives

    if seed not in TRAIN_SEEDS:
        raise ValueError(f"pre-training seed {seed} outside the training band 7000-7009")
    out_dir = Path(out_dir)
    (out_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    pcfg = PolicyConfig(kind="mlp_ppo", substep_mode="rechoose", ppo=PPOConfig(**(ppo or {})))
    policy = make_policy(pcfg, seed)
    policy.log_dir = out_dir
    nrng = np.random.default_rng(int(seed) + 5_000_003)
    episode = 0
    wall_before = 0.0
    if resume is not None:
        ck = torch.load(resume, map_location=policy.learner.device, weights_only=True)
        policy.load_state_dict(ck["policy"])
        nrng.bit_generator.state = ck["nursery_rng"]
        episode = int(ck["episode"])
        wall_before = float(ck.get("wall", 0.0))
    man = manifest(seed)
    man.update({"steps_target": float(steps), "episode_days": float(episode_days),
                "free_substeps": int(free_substeps), "ppo": pcfg.ppo.model_dump(),
                "device": str(policy.learner.device),
                "resumed_from": str(resume) if resume else None})
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t_start = time.perf_counter()

    def save(tag: str) -> None:
        ck = {"episode": episode, "policy": policy.state_dict(),
              "nursery_rng": nrng.bit_generator.state,
              "wall": wall_before + time.perf_counter() - t_start}
        torch.save(ck, out_dir / "checkpoints" / f"{tag}.pt")
        torch.save(ck, out_dir / "checkpoints" / "latest.pt")
        np.savez(out_dir / "checkpoints" / f"{tag}_actor.npz", **policy.learner.actor_params())

    while policy.n_transitions < steps and episode < max_episodes:
        p = sample_params(nrng, episode, episode_days)
        if n_adults_range is not None:  # tests: small colonies
            p = NurseryParams(**{**p.to_dict(), "n_adults": int(nrng.integers(*n_adults_range))})
        tmp = Path(tempfile.mkdtemp(prefix="u25nursery_"))
        sim = build_nursery(p, tmp, nrng, free_substeps)
        policy.attach(sim)
        n0, tr0, t0 = int(sim.agents.n_alive), policy.n_transitions, time.perf_counter()
        for _ in range(int(p.days * 6)):
            sim.step()
            if sim.agents.n_alive == 0:
                break
        policy.end_episode()
        idx = np.flatnonzero(sim.agents.alive)
        dt = time.perf_counter() - t0
        d_end = float(drive(read_drives(sim.agents, idx)).mean()) if idx.size else None
        row = {**p.to_dict(), "n_start": n0, "n_end": int(idx.size), "births": sim._births,
               "surviving_births": sim._surv_births_cum, "mean_D_end": d_end,
               "transitions": policy.n_transitions - tr0, "transitions_total": policy.n_transitions,
               "updates_total": policy.learner.n_updates, "wall": dt,
               "steps_per_s": (policy.n_transitions - tr0) / max(dt, 1e-9)}
        with open(out_dir / "episodes.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        sim.logger.close()
        shutil.rmtree(tmp, ignore_errors=True)
        episode += 1
        if progress:
            progress(row)
        if ckpt_every and episode % ckpt_every == 0:
            save(f"ckpt_ep{episode:04d}")
    save(f"ckpt_ep{episode:04d}")
    np.savez(out_dir / "policy_final.npz", **policy.learner.actor_params())
    np.savez(out_dir / "critic_final.npz", **policy.learner.critic_params())
    wall = wall_before + time.perf_counter() - t_start
    summ = {"episodes": episode, "transitions": policy.n_transitions,
            "updates": policy.learner.n_updates, "wall_s": wall,
            "steps_per_s": policy.n_transitions / max(wall, 1e-9),
            "vram_peak_mb": (torch.cuda.max_memory_allocated() / 2**20
                             if torch.cuda.is_available() else None)}
    man.update({"summary": summ})
    (out_dir / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    return summ
