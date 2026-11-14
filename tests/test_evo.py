"""The inherited-weight policy `evo` (P4-4; docs/PHASE4_DESIGN.md 4.4): genome layout and
generation 0, the per-animal forward pass, one-parent inheritance with mutation, founders,
the neutral control, the norm-matched jump genome (4.5), epoch founder sampling, a short
deterministic run whose hooks cover every conception and birth, the scarce epochs of SCARCE-PG
evo (4.6: their streams, read-only probes and the generation-matched stop), and the H2 audit of
the new modules (no reward, no play-named identifier)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import tokenize
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.evo import (  # noqa: E402
    FOUNDER_STREAM,
    GENETICS_STREAM,
    JUMP_STREAM,
    LINEAGE_STREAM,
    N_HID,
    N_IN,
    N_OUT,
    N_PARAM,
    NEUTRAL_STREAM,
    S_B1,
    S_B2,
    S_W1,
    S_W2,
    SAMPLING_STREAM,
    SCARCE_KEY,
    SCARCE_LINEAGE_STREAM,
    SEX_ANY,
    SMALL_KEY,
    SMALL_LINEAGE_STREAM,
    EvoPolicy,
    jump_genome,
    logits,
    neutral_pool,
    random_genomes,
    save_pool,
    stream,
)
from universe25.agents.state import ACT_FORAGE, N_ACTIONS, SEX_F, SEX_M  # noqa: E402
from universe25.config import PolicyConfig, load_config  # noqa: E402
from universe25.learn.evolution import (  # noqa: E402
    evolve_lineage,
    generation0,
    run_epoch,
    sample_founders,
)
from universe25.sim import Universe25Sim  # noqa: E402


def _stub(cap: int = 16, sexes: list[int] | None = None) -> SimpleNamespace:
    sex = np.array(sexes if sexes is not None else [SEX_F, SEX_M] * (cap // 2), np.int8)
    return SimpleNamespace(agents=SimpleNamespace(capacity=cap, sex=sex))


def test_genome_layout_and_generation0() -> None:
    assert N_PARAM == N_IN * N_HID + N_HID + N_HID * N_OUT + N_OUT == 2415
    a = random_genomes(np.random.default_rng(1), 3)
    b = random_genomes(np.random.default_rng(1), 3)
    assert a.dtype == np.float32 and np.array_equal(a, b)
    assert not np.array_equal(a[0], a[1])  # independent genomes
    assert np.all(a[:, S_B1] == 0) and np.all(a[:, S_B2] == 0)
    w2 = np.linalg.norm(a[:, S_W2], axis=1)
    assert np.allclose(w2, 0.01 * np.sqrt(N_OUT), rtol=1e-4)  # near-uniform choices
    w1 = np.linalg.norm(a[:, S_W1], axis=1)
    assert np.allclose(w1, np.sqrt(2.0) * np.sqrt(N_HID), rtol=1e-4)


def test_logits_match_a_per_animal_loop() -> None:
    rng = np.random.default_rng(2)
    G = rng.standard_normal((5, N_PARAM)).astype(np.float32)
    x = rng.standard_normal((5, N_IN)).astype(np.float32)
    z = logits(G, x)
    for i in range(5):
        W1 = G[i, S_W1].reshape(N_IN, N_HID)
        W2 = G[i, S_W2].reshape(N_HID, N_OUT)
        ref = np.tanh(x[i] @ W1 + G[i, S_B1]) @ W2 + G[i, S_B2]
        assert np.allclose(z[i], ref, atol=1e-4)


def test_one_parent_inheritance_with_mutation() -> None:
    def replay(seed: int) -> tuple[np.ndarray, np.ndarray, int]:
        pol = EvoPolicy(PolicyConfig(kind="evo"), seed)
        sim = _stub(16)
        pol._ensure(sim)
        rng = np.random.default_rng(3)
        pol.G[0] = rng.standard_normal(N_PARAM)  # mother
        pol.G[1] = rng.standard_normal(N_PARAM)  # male 1
        pol.G[3] = rng.standard_normal(N_PARAM)  # male 2
        pol.depth[[0, 1, 3]] = [4, 7, 9]
        pol.conceive(sim, 0, [1, 3])
        for pup in range(4, 16):
            pol.birth(sim, 0, pup)
        return pol.G.copy(), pol.depth.copy(), pol.n_from_sire

    G, depth, n_sire = replay(11)
    G2, depth2, n_sire2 = replay(11)
    assert np.array_equal(G, G2) and np.array_equal(depth, depth2) and n_sire == n_sire2
    sires = [s for s in (1, 3) if np.isclose(np.linalg.norm(G[4:] - G[s], axis=1).min(),
                                             0.02 * np.sqrt(N_PARAM), rtol=0.2)]
    assert len(sires) == 1  # one sire per pregnancy
    sire = sires[0]
    for pup in range(4, 16):
        dm = np.linalg.norm(G[pup] - G[0])
        ds = np.linalg.norm(G[pup] - G[sire])
        d = min(dm, ds)
        assert abs(d - 0.02 * np.sqrt(N_PARAM)) < 0.2 * 0.02 * np.sqrt(N_PARAM), d
        assert depth[pup] == (depth[0] if dm < ds else depth[sire]) + 1
    assert 0 < n_sire < 12  # both parents occur (fixed seed)


def test_founders_ordered_and_sampled() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        g = np.arange(6 * N_PARAM, dtype=np.float32).reshape(6, N_PARAM)
        p = Path(tmp) / "pool.npz"
        save_pool(p, g[:4], np.array([0, 1, 2, 3]), np.array([SEX_F, SEX_M, SEX_F, SEX_M]))
        pol = EvoPolicy(PolicyConfig(kind="evo", founders=str(p), founder_mode="ordered"), 1)
        sim = _stub(8, [SEX_F, SEX_M] * 4)
        pol.found(sim, np.array([0, 1, 2, 3]))
        assert np.array_equal(pol.G[:4], g[:4]) and list(pol.depth[:4]) == [0, 1, 2, 3]
        save_pool(p, g, np.zeros(6), np.array([SEX_F, SEX_F, SEX_F, SEX_M, SEX_M, SEX_M]))
        pol = EvoPolicy(PolicyConfig(kind="evo", founders=str(p)), 5)
        pol.found(sim, np.array([0, 1, 2, 3]))
        rows = [int(pol.G[i, 0] // N_PARAM) for i in range(4)]
        assert rows[0] in (0, 1, 2) and rows[2] in (0, 1, 2) and rows[0] != rows[2]
        assert rows[1] in (3, 4, 5) and rows[3] in (3, 4, 5) and rows[1] != rows[3]
        save_pool(p, g, np.zeros(6), np.full(6, SEX_ANY))
        pol = EvoPolicy(PolicyConfig(kind="evo", founders=str(p)), 5)
        pol.found(sim, np.array([0, 1, 2, 3]))
        rows = [int(pol.G[i, 0] // N_PARAM) for i in range(4)]
        assert len(set(rows)) == 4  # a pool without sexes is drawn as one, no repeats


def test_neutral_pool_is_drift_without_selection() -> None:
    z = np.zeros((16, N_PARAM), np.float32)
    a = neutral_pool(z, 50, 64, 0.02, np.random.default_rng(4))
    b = neutral_pool(z, 50, 64, 0.02, np.random.default_rng(4))
    assert a.shape == (64, N_PARAM) and np.array_equal(a, b)
    assert abs(float(a.std()) - 0.02 * np.sqrt(50)) < 0.1 * 0.02 * np.sqrt(50)
    assert np.array_equal(neutral_pool(z, 0, 64, 0.02, np.random.default_rng(4)), z)


def test_jump_genome_scales_one_random_jump() -> None:
    base = random_genomes(np.random.default_rng(8), 1)[0]
    eps = stream(9905, JUMP_STREAM).standard_normal(N_PARAM)
    assert np.array_equal(eps, stream(9905, JUMP_STREAM).standard_normal(N_PARAM))
    g0 = jump_genome(base, eps, 245, 0.02, 0.0)
    assert g0.dtype == np.float32 and np.array_equal(g0, base)  # lambda 0 is generation 0
    step = 0.02 * np.sqrt(245)
    g1 = jump_genome(base, eps, 245, 0.02, 1.0)
    gh = jump_genome(base, eps, 245, 0.02, 0.5)
    assert np.allclose(g1 - base, step * eps, atol=1e-5)
    assert np.allclose(gh - base, 0.5 * step * eps, atol=1e-5)  # same direction, half the size
    expect = step * np.sqrt(N_HID * N_OUT)  # |W2| of a neutral line after 245 generations
    assert abs(float(np.linalg.norm(g1[S_W2])) - expect) < 0.1 * expect
    ids = {SAMPLING_STREAM, GENETICS_STREAM, FOUNDER_STREAM, LINEAGE_STREAM, NEUTRAL_STREAM,
           JUMP_STREAM, SCARCE_LINEAGE_STREAM, SMALL_LINEAGE_STREAM}
    assert len(ids) == 8  # its own stream, and the scarce (4.6) and small-meal (4.7) lineages'


def test_epoch_founders_by_sex_in_slot_order() -> None:
    rng = np.random.default_rng(6)
    g0 = generation0(rng, 8)
    assert g0["genomes"].shape == (16, N_PARAM) and list(g0["sex"][:4]) == [SEX_F, SEX_M] * 2
    pool = {"genomes": np.arange(5)[:, None].repeat(N_PARAM, 1).astype(np.float32),
            "depth": np.arange(5), "sex": np.array([SEX_F, SEX_M, SEX_F, SEX_F, SEX_M])}
    f = sample_founders(np.random.default_rng(7), pool, pairs=3)
    assert list(f["sex"]) == [SEX_F, SEX_M] * 3
    fem = set(f["depth"][0::2].tolist())
    assert fem == {0, 2, 3}  # three females, without replacement
    assert set(f["depth"][1::2].tolist()) <= {1, 4}  # two males, the third drawn again
    none = sample_founders(rng, {**pool, "sex": np.full(5, SEX_F)}, pairs=3)
    assert none is None


def _short_run(seed: int, out: Path) -> Universe25Sim:
    cfg = load_config(ROOT / "configs" / "default.yaml",
                      dict(seed=seed, days=125.0, ticks_per_day=6, backend="numpy", device="cpu",
                           log_every_ticks=10**9, snapshot_every_days=0, free_substeps=12,
                           policy={"kind": "evo"}))
    sim = Universe25Sim(cfg, out)
    for _ in range(int(125 * 6)):
        sim.step()
    return sim


def test_short_run_is_deterministic_and_hooks_cover_every_birth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        s1 = _short_run(7100, Path(tmp) / "a")
        s2 = _short_run(7100, Path(tmp) / "b")
        p1, p2 = s1.policy, s2.policy
        assert np.array_equal(p1.G, p2.G) and np.array_equal(s1.agents.x, s2.agents.x)
        assert s1._births > 0 and p1.n_births == s1._births
        assert p1.n_conceptions == s1._conceptions
        assert 0 < p1.n_from_sire < p1.n_births
        alive = np.flatnonzero(s1.agents.alive)
        allowed = np.zeros((alive.size, N_OUT), dtype=bool)
        allowed[:, 0] = True
        allowed[::2, 5] = True
        act = p1.choose(s1, alive, allowed)
        assert np.all(allowed[np.arange(alive.size), act])  # the mask holds
        s1.logger.close()
        s2.logger.close()


SCARCE_FOOD = {"resources": {"mode": "scarce", "scarce_supply": "capacity",
                             "scarce_capacity_animals": 100.0}}


def _strip(stats: dict) -> dict:
    return {k: v for k, v in stats.items() if k not in ("wall_s", "probe")}


def test_scarce_epochs_keep_their_streams_and_probes_read_only() -> None:
    """SCARCE-PG evo (PHASE4_DESIGN.md 4.6): a scarce epoch is deterministic, its probes change
    nothing, its extra key gives other streams, and the default call is H-h's epoch."""
    founders = generation0(np.random.default_rng(12), 8)
    kw = dict(days=30.0, sim_seed=7100)
    p1, s1 = run_epoch(founders, 1, 0, overrides=SCARCE_FOOD, key_extra=(SCARCE_KEY,),
                       probe=True, **kw)
    p2, s2 = run_epoch(founders, 1, 0, overrides=SCARCE_FOOD, key_extra=(SCARCE_KEY,),
                       probe=True, **kw)
    p3, s3 = run_epoch(founders, 1, 0, overrides=SCARCE_FOOD, key_extra=(SCARCE_KEY,),
                       probe=False, **kw)
    assert np.array_equal(p1["genomes"], p2["genomes"]) and _strip(s1) == _strip(s2)
    assert s1["probe"] == s2["probe"] and s1["probe"]["days"] == 30
    assert np.array_equal(p1["genomes"], p3["genomes"]) and _strip(s1) == _strip(s3)
    assert "probe" not in s3  # read-only: the probes change no draw and no state
    _, s4 = run_epoch(founders, 1, 0, overrides=SCARCE_FOOD, **kw)
    assert s4["decision_action_shares"] != s1["decision_action_shares"]  # other streams
    d1, h1 = run_epoch(founders, 1, 0, **kw)
    d2, h2 = run_epoch(founders, 1, 0, overrides={}, key_extra=(), probe=False, **kw)
    assert np.array_equal(d1["genomes"], d2["genomes"]) and _strip(h1) == _strip(h2)
    try:
        run_epoch(founders, 1, 0, overrides={"policy": {"kind": "evo"}}, **kw)
        raise AssertionError("an override of the policy must be refused")
    except ValueError:
        pass


def test_scarce_lineage_loads_generation0_and_stops_at_its_depth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        g0 = generation0(np.random.default_rng(13), 8)
        src = Path(tmp) / "gen0.npz"
        save_pool(src, g0["genomes"], g0["depth"], g0["sex"])
        summ = evolve_lineage(1, Path(tmp) / "out", epochs=3, days=30.0, sim_seed=7100,
                              overrides=SCARCE_FOOD, key_extra=(SCARCE_KEY,),
                              lineage_stream=SCARCE_LINEAGE_STREAM, gen0_pool=src,
                              stop_depth=0.0, neutral=False, probe=True)
        d = Path(tmp) / "out" / "lineage_1"
        rows = (d / "epochs.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(rows) == 1  # the founders are adults of depth 0 on day 30: stop at once
        assert summ["depth_reached"] and summ["stop_depth"] == 0.0 and summ["ended"] is None
        assert (d / "pool_final.npz").exists() and not (d / "pool_neu.npz").exists()
        with np.load(d / "pool_gen0.npz") as z:
            assert np.array_equal(z["genomes"], g0["genomes"])  # generation 0 as given
        assert summ["setup"]["lineage_stream"] == SCARCE_LINEAGE_STREAM
        assert summ["setup"]["key_extra"] == [SCARCE_KEY]
        assert "probe" in json.loads(rows[0])


SMALL_MEALS = {"resources": {"meal_cap": 0.375}}


def test_small_meal_epochs_keep_their_streams_and_records() -> None:
    """Small-meal evo (PHASE4_DESIGN.md 4.7): a small-meal epoch is deterministic, its key gives
    other streams, its record carries the thirst probe and the eligible decisions' shares, and
    the small meals change the epoch."""
    founders = generation0(np.random.default_rng(12), 8)
    kw = dict(days=30.0, sim_seed=7100)
    p1, s1 = run_epoch(founders, 1, 0, overrides=SMALL_MEALS, key_extra=(SMALL_KEY,),
                       probe=True, **kw)
    p2, s2 = run_epoch(founders, 1, 0, overrides=SMALL_MEALS, key_extra=(SMALL_KEY,),
                       probe=True, **kw)
    assert np.array_equal(p1["genomes"], p2["genomes"]) and _strip(s1) == _strip(s2)
    assert s1["probe"] == s2["probe"]
    assert {"thirst_starving_share_2h", "thirst_starving_share_max"} <= set(s1["probe"])
    el = np.asarray(s1["eligible_action_shares"])
    assert el.size == N_ACTIONS and abs(float(el.sum()) - 1.0) < 1e-3
    _, s3 = run_epoch(founders, 1, 0, overrides=SMALL_MEALS, key_extra=(SCARCE_KEY,), **kw)
    assert s3["decision_action_shares"] != s1["decision_action_shares"]  # other streams
    _, s4 = run_epoch(founders, 1, 0, key_extra=(SMALL_KEY,), **kw)  # the same, full meals
    assert s4["decision_action_shares"][ACT_FORAGE] < s1["decision_action_shares"][ACT_FORAGE]


def test_evo_modules_have_no_play_named_identifier_and_no_reward() -> None:
    allowed = {"playground", "play_objects", "PlayObject", "playground_enabled",
               "playground_bounds", "in_playground"}
    for rel in ("agents/evo.py", "learn/evolution.py"):
        src = (ROOT / "src" / "universe25" / rel).read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type != tokenize.NAME or tok.string in allowed:
                continue
            low = tok.string.lower()
            assert "play" not in low, (rel, tok.string)
            assert not any(p in low for p in ("bout", "motif", "exaggerat", "reward")), \
                (rel, tok.string)
        assert "import torch" not in src  # no learner, no gradient


if __name__ == "__main__":
    test_genome_layout_and_generation0()
    test_logits_match_a_per_animal_loop()
    test_one_parent_inheritance_with_mutation()
    test_founders_ordered_and_sampled()
    test_neutral_pool_is_drift_without_selection()
    test_jump_genome_scales_one_random_jump()
    test_epoch_founders_by_sex_in_slot_order()
    test_short_run_is_deterministic_and_hooks_cover_every_birth()
    test_scarce_epochs_keep_their_streams_and_probes_read_only()
    test_scarce_lineage_loads_generation0_and_stops_at_its_depth()
    test_small_meal_epochs_keep_their_streams_and_records()
    test_evo_modules_have_no_play_named_identifier_and_no_reward()
    print("test_evo: OK")
