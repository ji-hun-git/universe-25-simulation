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
    test_gap_criterion_finds_no_structure_in_memoryless_gaps()
    test_free_choice_v_excluding_hoppers_is_logged()
    test_no_policy_or_learner_imports_a_detector()
    test_detector_code_has_no_play_named_identifier()
    print("test_detectors: OK")
