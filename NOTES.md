# Universe25 Play — NOTES

## Phase 2 (2026-10-30 Asia/Seoul)

### Calibration (Optuna CmaEsSampler, 40 trials, seed 7000, days=700, ticks/day=6)
- Train loss: **0.924**; held-out mean loss (8000–8002): **1.178**
- Wall: ~22.8 min
- Per-landmark relative error (train):
  - first_litters_day: 115 vs 104 → **10.6%**
  - n_at_day_315: 594 vs 620 → **4.2%**
  - peak_n: 831 vs 2200 → **62.2%** (under)
  - peak_day: 585 vs 560 → **4.5%**
  - last_young_day: 699.5 vs 600 → **16.6%** (still birthing at horizon)
- Collapse: final_n 587 / peak 831 ≈ 0.71 — mild decline from density/stress, not a hard-coded schedule; full Calhoun-style die-off not yet matched at 700d.
- Artifacts: `configs/calibrated_calhoun.yaml`, `configs/calibration_study_p2.json`

### Warp + CUDA Graphs (RTX 5080)
- Hybrid full-tick: sync-bound; 200d Warp+Graph **0.75x** vs NumPy (slower).
- Device-only graph replay vs NumPy post @ N=4096: **3.46x**; vs sync path ~48x.
- NVTX/Nsight one-pager: `docs/NSIGHT.md`
- Determinism tests remain NumPy-only (green).

### Gaps
- Peak population still ~831 vs ~2200; need longer CMA budget and/or days≥1200 for collapse.
- Phase-3: keep SoA resident on device to unlock full-tick speedups.

### 1200d collapse check (best params, seed 7000)
- peak still 831 @ day 585; final_n 599; last_young ~1200 (breeding continues)
- loss rose to 3.89 — Calhoun-style cessation of young ~day 600 **not** achieved yet
- Mechanism gap: density_mortality_scale searched to ~1.8e-5 (too weak); menopause thr ~0.57 but peak dens 831/3840≈0.22 never crosses it