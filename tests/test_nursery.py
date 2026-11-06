"""P4-3 nursery pre-training: the seeded colony has the drawn composition spread over all cells,
with litters in their mothers' boxes; worlds are deterministic for a seed and use training seeds
only; a pre-training run resumed from a checkpoint continues bit for bit."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import ROLE_JUVENILE, ROLE_NURSING, ROLE_PUP  # noqa: E402
from universe25.learn.nursery import (  # noqa: E402
    TRAIN_SEEDS,
    NurseryParams,
    build_nursery,
    pretrain,
    sample_params,
)


def _params(**kw) -> NurseryParams:
    base = dict(episode=0, sim_seed=7003, days=5.0, kind="mixed", n_cells=16, n_pairs=0,
                n_adults=300, frac_juvenile=0.2,
                frac_nursing=0.2, frac_pregnant=0.2, resources="abundant", food_per_agent_day=0.0,
                playground=True, n_balls=4, n_tunnels=2, n_ramps=1)
    base.update(kw)
    return NurseryParams(**base)


def test_seeded_colony_has_the_drawn_composition() -> None:
    p = _params()
    sim = build_nursery(p, Path(tempfile.mkdtemp(prefix="u25n_")), np.random.default_rng(3))
    a = sim.agents
    al = a.alive
    assert int((al & (a.age_days >= 70)).sum()) >= p.n_adults - 1
    assert int((al & (a.role == ROLE_JUVENILE)).sum()) == round(p.n_adults * p.frac_juvenile)
    moms = np.flatnonzero(al & (a.role == ROLE_NURSING))
    pups = np.flatnonzero(al & (a.role == ROLE_PUP))
    assert moms.size >= 10 and pups.size >= 3 * moms.size
    assert set(a.nest_id[pups]) <= set(a.nest_id[moms]), "litters sit in their mothers' boxes"
    assert np.unique(a.cell_id[al]).size == 16, "the colony spans all cells"
    assert int((al & (a.gestating > 0)).sum()) >= 5
    assert sim.cfg.policy.substep_mode == "rechoose" and sim.free_substeps == 12
    # the same draw gives the same world
    sim2 = build_nursery(p, Path(tempfile.mkdtemp(prefix="u25n_")), np.random.default_rng(3))
    for k in ("x", "y", "age_days", "nest_id", "role", "hunger", "gestating"):
        assert np.array_equal(getattr(a, k), getattr(sim2.agents, k)), k


def test_founding_and_concentrated_worlds() -> None:
    """Founding worlds: young adult pairs in at most n_cells cells, no litters, the calibrated
    conception gate kept. Concentrated mixed worlds stay within their cells; mixed worlds lift the
    gate."""
    from universe25.config import load_config

    gate = load_config(ROOT / "configs" / "default.yaml").biology.first_conception_min_day
    f = _params(kind="founding", n_cells=2, n_pairs=12, n_adults=24, frac_juvenile=0.0,
                frac_nursing=0.0, frac_pregnant=0.0, days=300.0)
    sim = build_nursery(f, Path(tempfile.mkdtemp(prefix="u25f_")), np.random.default_rng(5))
    a = sim.agents
    al = a.alive
    assert int(al.sum()) == 24 and int((al & (a.sex == 0)).sum()) == 12
    assert np.unique(a.cell_id[al]).size <= 2
    assert np.all((a.age_days[al] >= 48) & (a.age_days[al] <= 90))
    assert not np.any(al & (a.role == ROLE_PUP)) and not np.any(al & (a.gestating > 0))
    assert sim.cfg.biology.first_conception_min_day == gate
    c = _params(n_cells=3)
    sim2 = build_nursery(c, Path(tempfile.mkdtemp(prefix="u25c_")), np.random.default_rng(6))
    al2 = sim2.agents.alive
    assert np.unique(sim2.agents.cell_id[al2]).size <= 3
    assert sim2.cfg.biology.first_conception_min_day == 0.0
    rng = np.random.default_rng(1)
    kinds = [sample_params(rng, ep).kind for ep in range(200)]
    assert 0.3 < kinds.count("founding") / 200 < 0.5


def test_worlds_use_training_seeds_only() -> None:
    rng = np.random.default_rng(0)
    for ep in range(25):
        p = sample_params(rng, ep)
        assert p.sim_seed in TRAIN_SEEDS and not 8000 <= p.sim_seed <= 8011
        assert p.resources in ("abundant", "scarce") and 1 <= p.n_cells <= 16
        if p.kind == "mixed":
            assert 200 <= p.n_adults <= 1500
        else:
            assert 4 <= p.n_pairs <= 30 and p.n_cells <= 4 and p.days == 300.0
    try:
        pretrain(Path(tempfile.mkdtemp()), seed=8000, max_episodes=1)
    except ValueError:
        pass
    else:
        raise AssertionError("an evaluation seed was accepted for pre-training")


def _small(out: Path, max_episodes: int, resume: Path | None = None) -> dict:
    return pretrain(out, steps=1e12, max_episodes=max_episodes, episode_days=3.0, seed=7000,
                    ckpt_every=1, resume=resume, n_adults_range=(40, 80),
                    founding_days=3.0, p_founding=0.5, ppo={"rollout_ticks": 6})


def test_resumed_pretraining_continues_bit_for_bit() -> None:
    a = Path(tempfile.mkdtemp(prefix="u25preA_"))
    b = Path(tempfile.mkdtemp(prefix="u25preB_"))
    sa = _small(a, 2)
    _small(b, 1)
    sb = _small(b, 2, resume=b / "checkpoints" / "latest.pt")
    assert sa["episodes"] == sb["episodes"] == 2
    assert sa["transitions"] == sb["transitions"] and sa["updates"] == sb["updates"] >= 4
    with np.load(a / "policy_final.npz") as za, np.load(b / "policy_final.npz") as zb:
        for k in za.files:
            assert np.array_equal(za[k], zb[k]), k
    rows_a = [json.loads(x) for x in (a / "episodes.jsonl").read_text().splitlines()]
    rows_b = [json.loads(x) for x in (b / "episodes.jsonl").read_text().splitlines()]
    for ra, rb in zip(rows_a, rows_b):
        for k in ("n_start", "n_end", "births", "transitions", "mean_D_end"):
            assert ra[k] == rb[k], (k, ra[k], rb[k])
    man = json.loads((a / "manifest.json").read_text())
    assert man["summary"]["transitions"] == sa["transitions"] and man["torch"]


if __name__ == "__main__":
    test_seeded_colony_has_the_drawn_composition()
    test_founding_and_concentrated_worlds()
    test_worlds_use_training_seeds_only()
    test_resumed_pretraining_continues_bit_for_bit()
    print("test_nursery: OK")
