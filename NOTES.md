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

