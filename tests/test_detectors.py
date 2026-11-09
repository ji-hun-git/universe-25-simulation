"""Eval-only detectors and decision traces (P4-5): the recorder is off by default and does not
perturb the trajectory when on; traces are well formed; each synthetic class fails exactly the
criterion it was built to violate; the gap criterion finds no structure in memoryless gaps; the
hopper-excluding free-choice measure is logged; no policy or learner module imports a detector,
and detector code carries no play-named identifier (H2 / PHASE4_DESIGN.md section 2)."""
from __future__ import annotations

import ast
import io
import sys
import tempfile
import tokenize
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.state import ACT_MANIPULATE  # noqa: E402
from universe25.config import load_config  # noqa: E402
from universe25.metrics import detectors as D  # noqa: E402
from universe25.metrics.synthetic_traces import make_colony  # noqa: E402
from universe25.metrics.trace import FIELDS, load_trace  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402


def _sim(days: float = 12.0, windows=None, out: str = "u25_det_") -> Universe25Sim:
    over = dict(seed=7100, days=days, ticks_per_day=6, backend="numpy", device="cpu",
                max_agents=512, log_every_ticks=6, snapshot_every_days=0)
    if windows is not None:
        over["trace"] = {"windows": windows}
    cfg = load_config(ROOT / "configs" / "default.yaml", over)
    return Universe25Sim(cfg, Path(tempfile.mkdtemp(prefix=out)))


def test_trace_off_by_default_and_recorder_does_not_perturb() -> None:
    plain = _sim()
    assert plain.trace is None
    traced = _sim(windows=[(2.0, 6.0)])
    assert traced.trace is not None
    for _ in range(72):  # 12 days at 6 ticks/day
        plain.step()
        traced.step()
    a, b = plain.agents, traced.agents
    for k in ("x", "y", "hunger", "stress", "competence", "age_days"):
        assert np.array_equal(getattr(a, k), getattr(b, k)), k
    assert a.n_alive == b.n_alive and plain._births == traced._births
    files = traced.trace.close()
    assert len(files) == 1 and Path(files[0]).name == "trace_2_6.npz"
    tr = load_trace(files[0])
    for k in FIELDS:
        assert k in tr and tr[k].size == tr["uid"].size, k
    # one row per alive agent per decision in [2, 6): 4 days x 6 decisions
    assert np.unique(tr["step"]).size == 24
    key = tr["uid"].astype(np.int64) * 10_000 + tr["step"]
    assert np.unique(key).size == key.size, "one row per (individual, decision)"
    for u in np.unique(tr["uid"]):
        c = tr["cum_contacts"][tr["uid"] == u]
        assert np.all(np.diff(c) >= 0), "cumulative contacts never decrease"
    assert np.all(tr["contact"][tr["action"] != ACT_MANIPULATE] == 0)
    assert int(tr["meta"]["decisions_per_day"]) == 6


def test_each_synthetic_class_fails_the_criterion_it_violates() -> None:
    expect = {  # (kind, flag that must be False)
        "serious": [("object", "c1_not_functional"), ("object", "c3_structurally_different")],
        "rigid_loop": [("object", "c4_repeated_not_rigid"), ("locomotor", "c4_repeated_not_rigid")],
        "novelty": [("object", "c4_repeated_not_rigid")],
        "triggered": [("object", "c2_spontaneous"), ("locomotor", "c2_spontaneous")],
        "stressed": [("object", "c5_relaxed_field"), ("locomotor", "c5_relaxed_field")],
    }
    pos = D.detect_trace(make_colony("all_criteria", seed=31), n_surrogates=200, seed=3)
    for kind in ("object", "locomotor"):
        assert all(pos[kind]["decisions_unvalidated"].values()), (kind, pos[kind])
    for cls, checks in expect.items():
        res = D.detect_trace(make_colony(cls, seed=32), n_surrogates=200, seed=3)
        for kind, flag in checks:
            assert not res[kind]["decisions_unvalidated"][flag], (cls, kind, flag)
    rw = D.detect_trace(make_colony("random_walk", seed=33), n_surrogates=200, seed=3)
    assert rw["object"]["n_episodes"] == 0 and not any(
        rw["object"]["decisions_unvalidated"].values())
    assert not rw["locomotor"]["decisions_unvalidated"]["c5_relaxed_field"]


def test_v6_form_test_needs_structure_beyond_chance() -> None:
    """Rules v6: a random walk meets v5 criteria 3 and 4 for locomotion but not the form test
    (its reversal fraction is that of its own order shuffle); all_criteria passes it in both
    kinds; the form test draws from its own stream, so no v5 statistic depends on it."""
    rw = D.detect_trace(make_colony("random_walk", seed=33), n_surrogates=200, seed=3)
    loc = rw["locomotor"]
    assert loc["seq_struct_form_excess_unvalidated"] < D.FORM_MIN_EXCESS, loc
    assert loc["decisions_v5_unvalidated"]["c3_structurally_different"], loc  # what v6 fixes
    assert not loc["decisions_unvalidated"]["c3_structurally_different"]
    assert not loc["decisions_unvalidated"]["c4_repeated_not_rigid"]
    pos = D.detect_trace(make_colony("all_criteria", seed=31), n_surrogates=200, seed=3)
    for kind in ("object", "locomotor"):
        assert pos[kind]["seq_struct_form_excess_unvalidated"] >= D.FORM_MIN_EXCESS, kind
        assert pos[kind]["decisions_unvalidated"] == pos[kind]["decisions_v5_unvalidated"]
    S = D.prepare(make_colony("all_criteria", seed=31))
    a = D.detect_kind(S, "locomotor", n_surrogates=50, seed=3)
    orig = D.form_test
    try:
        D.form_test = lambda *args, **kw: {}
        b = D.detect_kind(S, "locomotor", n_surrogates=50, seed=3)
    finally:
        D.form_test = orig
    assert b["decisions_v5_unvalidated"] == a["decisions_v5_unvalidated"]
    for k, v in b.items():
        if k.endswith("_unvalidated") and not k.startswith("decisions"):
            assert np.array_equal(np.asarray(v), np.asarray(a[k]), equal_nan=True), k


def test_v7_resim_null() -> None:
    """Rules v7: the form test's null is a replay of an even family mix under the simulator's
    mechanics. A random walk stays below the floor and all_criteria above it; a trace without
    object positions cannot replay object episodes (NaN, c3 / c4 not met) while its locomotor
    replay uses the move model; the v6 shuffle statistics and flags are kept; the replay draws
    from its own stream, so no v5 or v6 statistic depends on it."""
    assert D.RULES == "v7"
    rw = D.detect_trace(make_colony("random_walk", seed=33), n_surrogates=200, seed=3)
    loc = rw["locomotor"]
    assert loc["seq_struct_form_excess_unvalidated"] < D.FORM_MIN_EXCESS, loc
    assert "seq_struct_form_shuffle_excess_unvalidated" in loc and "decisions_v6_unvalidated" in loc
    tr = make_colony("all_criteria", seed=31)
    pos = D.detect_trace(tr, n_surrogates=200, seed=3)
    for kind in ("object", "locomotor"):
        assert pos[kind]["seq_struct_form_excess_unvalidated"] >= D.FORM_MIN_EXCESS, kind
    old = {k: v for k, v in tr.items() if k not in ("obj_x", "obj_y")}
    old["meta"] = {k: v for k, v in tr["meta"].items() if not k.startswith(("move_", "world_"))}
    r_old = D.detect_trace(old, n_surrogates=100, seed=3)
    assert np.isnan(r_old["object"]["seq_struct_form_excess_unvalidated"])
    assert not r_old["object"]["decisions_unvalidated"]["c3_structurally_different"]
    assert np.isfinite(r_old["locomotor"]["seq_struct_form_excess_unvalidated"])
    S = D.prepare(tr)
    a = D.detect_kind(S, "object", n_surrogates=50, seed=3)
    orig = D.form_resim
    try:
        D.form_resim = lambda *args, **kw: {}
        b = D.detect_kind(S, "object", n_surrogates=50, seed=3)
    finally:
        D.form_resim = orig
    assert b["decisions_v6_unvalidated"] == a["decisions_v6_unvalidated"]
    for k, v in b.items():
        if k.endswith("_unvalidated") and not k.startswith("decisions"):
            assert np.array_equal(np.asarray(v), np.asarray(a[k]), equal_nan=True), k


def test_v4_substep_rules() -> None:
    """Rules v4: with K = 1 the trigger window is v3's (the onset row or the consecutive row
    before); with 12 sub-steps per decision, onsets independent of triggers read spontaneous and
    onsets after a trigger read locked, in both episode kinds."""
    tr = make_colony("triggered", seed=5)
    S = D.prepare(tr)
    before = np.zeros_like(S.trigger)
    before[1:] = S.trigger[:-1]
    v3 = S.trigger | (S.prev_ok & before)
    cs = np.concatenate([[0], np.cumsum(S.trigger.astype(np.int64))])
    v4 = (cs[np.arange(S.n) + 1] - cs[S.win_lo]) > 0
    assert np.array_equal(v3, v4) and S.K == 1
    pos = D.detect_trace(make_colony("all_criteria_k12", seed=61), n_surrogates=200, seed=3)
    neg = D.detect_trace(make_colony("triggered_k12", seed=62), n_surrogates=200, seed=3)
    for kind in ("object", "locomotor"):
        assert pos[kind]["decisions_unvalidated"]["c2_spontaneous"], (kind, pos[kind])
        assert not neg[kind]["decisions_unvalidated"]["c2_spontaneous"], (kind, neg[kind])


def _hand_trace(cells: list[int], dens: list[float], wounds: list[float], K: int = 1) -> dict:
    n = len(cells)
    tr: dict = {k: np.zeros(n) for k in FIELDS}
    tr["uid"] = np.zeros(n, dtype=np.int64)
    tr["step"] = np.arange(n)
    tr["cell"] = np.asarray(cells)
    tr["cell_density"] = np.asarray(dens, dtype=np.float64)
    tr["wounds"] = np.asarray(wounds, dtype=np.float64)
    tr["age"] = np.full(n, 100.0)
    tr["energy"] = np.ones(n)
    tr["meta"] = {"decisions_per_day": 6 * K, "free_substeps": K}
    return tr


def test_v5_counts_only_exogenous_triggers() -> None:
    """Rules v5: aggression received and density jumps in a cell occupied at the previous
    decision's start are triggers; the individual's own cell entry, and a density jump that
    comes with it, are not (v4 counted both). On the mobile synthetic classes, v4 reads
    onsets that follow the individual's own entry as locked; v5 reads them spontaneous and still
    reads onsets after exogenous triggers as locked."""
    # K = 1: own entry into a denser cell; stays while others arrive; wounded; quiet
    tr = _hand_trace([0, 1, 1, 1, 1], [0.3, 0.8, 1.0, 1.0, 1.0], [0, 0, 0, 0.2, 0.2])
    assert D.prepare(tr).trigger.tolist() == [False, False, True, True, False]
    assert D.prepare(tr, self_entries=True).trigger.tolist() == [False, True, True, True, False]
    # K = 2: the entry happens inside decision 1; decision 2 starts in the new, denser cell
    # (not a trigger in v5); decision 3 stays there while others arrive (a trigger)
    tr = _hand_trace([0, 0, 0, 1, 1, 1, 1, 1], [.3, .3, .3, .3, .9, .9, 1.1, 1.1], [0] * 8, K=2)
    assert D.prepare(tr).trigger.tolist() == [False] * 6 + [True, False]
    assert D.prepare(tr, self_entries=True).trigger.tolist() == \
        [False, False, False, True, True, False, True, False]
    pos = make_colony("all_criteria_mobile_k12", seed=71)
    neg = make_colony("triggered_mobile_k12", seed=72)
    assert np.unique(pos["cell"]).size == 4
    r5 = D.detect_trace(pos, kinds=("object",), n_surrogates=200, seed=3)
    r4 = D.detect_trace(pos, kinds=("object",), n_surrogates=200, seed=3, self_entries=True)
    rn = D.detect_trace(neg, kinds=("object",), n_surrogates=200, seed=3)
    assert r5["rules"] == D.RULES and r4["rules"] == "v4_self_entries"
    assert r5["object"]["decisions_unvalidated"]["c2_spontaneous"], r5["object"]
    assert not r4["object"]["decisions_unvalidated"]["c2_spontaneous"], r4["object"]
    assert not rn["object"]["decisions_unvalidated"]["c2_spontaneous"], rn["object"]
    assert 0.0 <= r5["relaxed_share_weaned"] <= 1.0 and r5["n_rows_weaned"] == r5["n_rows"]


def test_gap_criterion_finds_no_structure_in_memoryless_gaps() -> None:
    rng = np.random.default_rng(5)
    n_ind, T = 40, 600
    ev_rows = rng.random(n_ind * T) < 0.15  # Bernoulli events: geometric gaps, no break
    tr = make_colony("all_criteria", n_individuals=1, days=1, seed=1)  # schema donor
    rows = {k: np.zeros(n_ind * T, dtype=np.asarray(tr[k]).dtype) for k in FIELDS}
    rows["uid"] = np.repeat(np.arange(n_ind), T)
    rows["step"] = np.tile(np.arange(T), n_ind)
    rows["action"] = np.where(ev_rows, ACT_MANIPULATE, 0)
    rows["contact"] = ev_rows.astype(np.int8)
    rows["meta"] = {"decisions_per_day": 6}
    S = D.prepare(rows)
    ev, _ = D.event_mask(S, "object")
    c, has_break = D.gap_criterion(S, ev)
    assert not has_break and c == 1, (c, has_break)


def test_free_choice_v_excluding_hoppers_is_logged() -> None:
    import pyarrow.parquet as pq

    sim = _sim(days=40.0, out="u25_vx_")
    sim.run()
    t = pq.read_table(sim.out_dir / "metrics.parquet")
    assert "free_choice_V_excl_hopper_unvalidated" in t.column_names
    vx = t.column("free_choice_V_excl_hopper_unvalidated").to_numpy()
    assert np.all((vx >= 0.0) & (vx <= 1.0))


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out.update(f"{node.module}.{a.name}" for a in node.names)
    return out


def test_no_policy_or_learner_imports_a_detector() -> None:
    banned = ("universe25.metrics.detectors", "universe25.metrics.trace",
              "universe25.metrics.synthetic_traces", "universe25.metrics.playscore")
    pkgs = [ROOT / "src" / "universe25" / "agents", ROOT / "src" / "universe25" / "learn"]
    checked = 0
    for pkg in pkgs:
        for path in sorted(pkg.glob("*.py")) if pkg.exists() else []:
            imps = _imports(path)
            checked += 1
            for b in banned:
                assert not any(i == b or i.startswith(b + ".") for i in imps), (path.name, b)
    assert checked >= 3


def test_detector_code_has_no_play_named_identifier() -> None:
    allowed = {"playground", "play_objects", "PlayObject", "playground_enabled",
               "playground_bounds", "in_playground"}  # world geometry, not a signal
    bad_parts = ("bout", "motif", "exaggerat", "reward")
    for name in ("detectors.py", "trace.py", "synthetic_traces.py"):
        src = (ROOT / "src" / "universe25" / "metrics" / name).read_text(encoding="utf-8")
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type != tokenize.NAME or tok.string in allowed:
                continue
            low = tok.string.lower()
            assert "play" not in low, (name, tok.string)
            assert not any(p in low for p in bad_parts), (name, tok.string)


if __name__ == "__main__":
    test_trace_off_by_default_and_recorder_does_not_perturb()
    test_each_synthetic_class_fails_the_criterion_it_violates()
    test_v6_form_test_needs_structure_beyond_chance()
    test_v7_resim_null()
    test_v4_substep_rules()
    test_v5_counts_only_exogenous_triggers()
    test_gap_criterion_finds_no_structure_in_memoryless_gaps()
    test_free_choice_v_excluding_hoppers_is_logged()
    test_no_policy_or_learner_imports_a_detector()
    test_detector_code_has_no_play_named_identifier()
    print("test_detectors: OK")
