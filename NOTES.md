# NOTES: universe25-play

## 2026-10-30 — Phase 1 scaffold

- Created Track E Universe 25 + playground environment (no L3 import).
- Stack: Python 3.12 shared omnilab `.venv`, NVIDIA Warp 1.18 (sm_120 / RTX 5080), pydantic+YAML config, pyarrow metrics.
- No play reward. Drives: hunger, thirst, fatigue, stress, social, aggression, maternal, curiosity, boredom, homeostasis.
- PlayScore F,V,D,S,G logged as **unvalidated** (gan formalization).
- Pending: smoke run, ~1600-day abundant run, calibration errors.


## 2026-10-30 — tests + smoke

- Private repo: https://github.com/ji-hun-git/universe25-play
- Tests: geometry, determinism (traj hash), conservation — all OK
- Smoke seed 7000, 30 days, numpy/cpu: wall ~0.36 s, N peak 8 (pre-conception window), births 0, nan 0
- Vectorized SoA host path; Warp device mirror stubbed for phase-2 kernels
- Calibration no longer imports pandas


## 2026-10-30 — NVIDIA stack hooks

- Added `src/universe25/nvidia/`: NVTX ranges (torch.cuda.nvtx), CudaGraphTick scaffolding, Newton playground stub, USD pen export, RL vec-env spec, stack probe.
- Lab venv has warp 1.18, torch 2.11+cu128, newton 1.7.0, pxr; no gymnasium/isaaclab/omni/nvtx package.
- Docs: docs/NVIDIA_STACK.md


## 2026-10-30 — 1600-day abundant+playground run (seed 7000)

Command: `python main.py --seed 7000 --out _output/run1600_abund_pg --days 1600 --backend numpy --device cpu --max-agents 4096 --playground on`

| Metric | Value |
|---|---|
| Wall | 296.6 s (~4.9 min) |
| Ticks | 38400 |
| Peak N | 1715 at day ~1395 |
| Final N | 1339 |
| Births / deaths / conceptions | 62637 / 61306 / 32122 |
| NaNs | 0 |
| Backend | numpy/cpu (Warp available; kernels not yet driving tick) |

### Calibration vs Calhoun 1973 (honest)

| Landmark | Target | Observed | Rel error |
|---|---|---|---|
| First litters | 104 | 221 | 1.13 |
| N @ day 315 | 620 | 48 | 0.92 |
| Peak N | 2200 | ~1708 | 0.22 |
| Peak day | 560 | 1392 | 1.49 |
| Last young | 600 | 1599.75 | 1.67 |
| mean_rel_error | | | **1.08** |

Phases detected: adjustment, growth, stagnation. **No collapse** by day 1600 (last_young still near end; density suppression too weak / mortality too low for Death Squared crash).

Label: **exploratory / negative on timing calibration**; peak magnitude within ~22% is the only near-hit.

Outputs: `_output/run1600_abund_pg/{run,calibration,metrics.parquet,snapshots/}`
