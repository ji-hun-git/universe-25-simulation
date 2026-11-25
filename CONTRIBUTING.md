# Contributing

Thank you for looking. This file holds the project's rules and conventions. To use the
simulation, start with [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## What the project is

Two things share one simulator:
- **A Universe 25 simulation anyone can use.** It is fitted to Calhoun's record, and its limits
  are stated (README, "How close is it").
- **A research programme.** Do play-like behaviours emerge in learning agents that are given
  abundance rather than scarcity? The hypotheses and stop rules are preregistered in
  `PLAN.md`.

Read first, as far as your change needs:
1. `HANDOFF.md`: the full state, architecture and roadmap.
2. `PLAN.md`: the hypotheses and stop rules.
3. `NOTES.md`: dated results, negative ones included.
4. `docs/TASKS.md`: open tasks with acceptance criteria.
5. `docs/PHASE4_DESIGN.md` and `docs/RESEARCH_DIGEST.md`, if you touch agents, policies,
   learning, the play metrics or the record's targets.

## Hard rules

- **No reward, utility or observation** named, or acting as, play, bout, motif or exaggeration
  (H2; `tests/test_h2_audit.py` checks it). PlayScore is unvalidated and used only for
  evaluation.
- **No language-model agents**, no imitation or behaviour cloning, and no training on animal or
  human play data.
- **The NumPy path stays deterministic** for a fixed seed. The golden trajectories
  (`tests/test_golden.py`) must not change unless a change is meant to alter the model.
- **New model mechanisms** are preregistered in a design document before code, are off by
  default, and are bit-identical when off.
- **Report results honestly in `NOTES.md`**, including failed calibrations and null results. Do
  not overclaim "fun", play or world models.
- **Seeds** are 7000–9999 and are tracked in `docs/SEEDS.md`. Fresh validation seeds are read
  once.

## Code

- The package is in `src/universe25/`; configs are YAML, validated by pydantic in `config.py`.
- Agents are flat arrays (`agents/state.py`), the world is in `world/geometry.py`, and the tick is
  in `sim.py`.
- Lines are at most 100 characters (ruff), Python 3.11+.
- For hot array loops, prefer Warp kernels, and keep a NumPy reference path for parity.
- Metrics go to Parquet. PlayScore fields end in `_unvalidated`.
- Figures and pages use the palette: paper `#F4F0E6`, ink `#1A1A1A`, stress `#8B1E1E`, nest
  `#2F5D50`.

## Tests

The tests are plain `__main__` scripts, with no pytest:

```bash
python -X utf8 tests/run_tests.py --tier fast   # what CI runs
python -X utf8 tests/run_tests.py               # everything, golden trajectories included
```

## Commits

- Conventional prefixes: `feat:`, `fix:`, `docs:`, `test:`, `perf:`, `chore:`.
- Stage files by path; do not commit `_output/`, secrets or large binaries.
- Rebase on `master` before pushing.

## Definition of done

- The tests pass, and the H2 audit is clean.
- `NOTES.md` is updated if the change is empirical.
- The task's acceptance criteria are met.
- If a headline number or a phase-4 verdict changed:
  - redraw the hero figure (`docs/FIGURES.md`: edit `docs/figures/phase4_ledger.yaml`, then run
    `scripts/hero_figure.py draw`);
  - then remake the booklet (`scripts/booklet.py`).
