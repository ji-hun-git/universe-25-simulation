# Universe25 Play — NOTES

## Phase 2c — dt-invariance of the tick loop (2026-10-30; TASKS P0-4)

Problem (found at the end of 2b): the calibrated parameters gave peak 2261 at 6 ticks/day but
1088 at 24 ticks/day. Causes: movement was `speed·dt` per tick while the action was re-drawn
every tick (at 24 tpd a mother moved ~6 in toward her nest, then re-rolled, rarely reaching her
pups), and every per-event effect (nursing amounts, drive relief, wounds, nest-stress relief,
conception chance per ACT_MATE attempt, nest-kick chance, random-walk steps) was per tick.

Fix (`SimConfig.ticks_per_day_ref = 6`, `sim.k_ev / sd_k / sqrt_k / reach`):
- per-decision effects × `k = ref/tpd` (so tpd × k is constant → daily totals fixed);
- random walks written as `c·dt·10` × `sqrt(tpd/ref)` (daily variance fixed); per-decision
  nudges without `dt` (object jiggle) × `sqrt(k)`;
- movement reach per decision = `speed · 24/ref` inches, independent of dt (an agent reaches its
  target within one decision at any resolution);
- Warp `density_stress_kernel` takes the same `event_scale` for its social-drive decrement.
At 6 tpd every factor is exactly 1.0, so the calibrated trajectory is **bit-identical** (400-day
SHA-256 of per-tick state unchanged: `32c08242…`). Tests: `test_resolution_scaling` + parity.

Same calibrated params, seed 7000, 1600 d (`_output/run1600_p2b_tpd6`, `run1600_p2c_tpd12`,
`run1600_p2c_tpd24`):

| Landmark | Calhoun | 6 tpd | 12 tpd | 24 tpd | 24 tpd before fix |
|---|---:|---:|---:|---:|---:|
| First litters | 104 | 111 | 110 | 110 | 110 |
| N @ 315 | 620 | 672 | 753 | 928 | 138 |
| Peak N | 2200 | 2261 | 2345 | 2314 | 1088 |
| Peak day (≥97 %) | 560 | 467 | 447 | 439 | 590 |
| Last surviving birth | 600 | 813 | 819 | 797 | 1573 |
| N @ 736 | 2056 | 2106 | 2167 | 2191 | 998 |
| Last conception | ≈920 | 793 | 799 | 777 | 1597 |
| N @ 1200 / 1600 | | 1316 / 93 | 1333 / 127 | 1182 / 85 | 409 / 111 |
| Collapse onset (<50 % peak) | | 1228 | 1225 | 1203 | 1097 |
| mean rel. error (5) | | 0.140 | 0.181 | 0.230 | 0.603 |
| wall (s) | | 50 | 106 | 235 | 173 |

The arc is now resolution-independent (peak ±4 %, N@736 ±4 %, last surviving birth ±3 %,
collapse onset ±2 %, ≈4 800–5 000 births in all three). **Residual:** early exponential growth
is slightly faster at finer ticks (N@315 672 → 753 → 928). Diagnosed with the 320-day
diagnostic at 6 vs 24 tpd: infant mortality is the same (deaths/births 0.23 vs 0.26), but
conceptions are higher (340 vs 245 by day 320; 130 vs 83 births by day 200). Cause: per-tick
action probabilities depend on the drive sawtooth — hunger rises 0.20 per tick at 6 tpd but 0.05
at 24 tpd, so mean hunger/thirst utilities are higher at coarse ticks and the MATE share per tick
is lower; a ~5–8 % conception-rate gap compounds through the 55-day-doubling phase into +38 % at
day 315 (within the seed-to-seed band 404–827, but systematic). Clean fix for later: make
conception purely daily (drop the per-tick ACT_MATE conception side effect; keep the action as
approach/courtship) and re-calibrate — not done here because it changes the 6-tpd reference.

`configs/default.yaml` stays at `ticks_per_day: 6` as the calibrated reference resolution (also
4× cheaper); 12 or 24 are now usable for finer output with the same biology.

## Phase 2b — pup-mill bug, developmental-imprinting collapse, recalibration (2026-10-30)

### What was wrong with the phase-2 calibration (diagnosed, seed 7000, 900 d, 6 ticks/day)
Instrumented the calibrated phase-2 config per day (`n`, cohort counts, conceptions, births,
expected deaths by hazard term). The "N@315 = 594" hit was an artifact:

| day | N | pups | juveniles | adult ♀ | gestating | adult mean age (d) |
|----:|--:|-----:|----------:|--------:|----------:|-------------------:|
| 300 | 630 | 427 | 162 | 13 | 132 | 66 |
| 585 (peak) | ~830 | ~525 | ~160 | ~15 | ~156 | 84 |
| 900 | 670 | 457 | 165 | 21 | 164 | 75 |

- **~150 gestating agents vs ~15 adult females**: of 106 gestating at day 260, **101 were below
  maturity age and 67 were pre-weaning pups** (median gestating age 14.9 d). Cause: the softmax
  gave every action weight exp(0) when its utility was 0, so pups chose FORAGE/DRINK/AGGRESS/MATE
  near-uniformly, and `_try_mate` never checked the initiator's age. Generation time collapsed
  to ≈ gestation (19 d) — a pup mill.
- Adults died at mean age 75–85 d: expected-death attribution over 900 d was stress² 15 638,
  wounds 3 746 (wounds never healed), base 176, age 0, starvation 0. Stress used a *constant*
  decay, i.e. a hard local-density cliff above which stress ran away to the 1.5 clip.
- Births ≈ deaths ≈ 29/day from day 250 on; that steady state (≈830) is what the CMA-ES had
  fitted. It could never reach the menopause threshold, so no collapse was possible.

### Changes (all NumPy path; Warp `density_stress_kernel` updated in parity)
1. **Eligibility mask** in `_select_actions`: ineligible actions get probability exactly 0
   (not exp(0)). Pre-weaning pups: REST/NEST only (milk-dependent, no hopper use, no
   need-override). MATE requires maturity, not withdrawn, stress < 0.75, energy > 0.4. NURSE
   requires female with maternal > 0. MANIPULATE masked when playground is off.
2. `_try_mate`: initiator must be mature and not withdrawn; female must be within fertile age.
3. **Births in the nest**: mother returns to her nest box to give birth; pups stay there until
   weaning; ACT_NURSE first moves the mother to her nest. Nest-box crowding therefore matters.
4. **Stress relaxation**: `stress += (gain − decay·stress)·dt` (equilibrium = gain·local/decay,
   smooth in density) instead of the constant-decay cliff. Wounds heal (`wound_heal_per_day`).
5. **Developmental imprinting (collapse mechanism, H2-safe)**: new SoA trait `competence`
   (1.0 at birth). While age < maturity it decays at `imprint_rate × exposure`, with
   exposure = max(0, local_density − `imprint_density_threshold`) + relative nest overfullness;
   frozen at maturity (irreversible). Effects: conception probability × c_female × c_male;
   maternal investment = 0.9·c (low-c mothers do not nurse → infant mortality); adults with
   c < `withdrawn_competence_threshold` are withdrawn ("beautiful ones"). This is Calhoun's own
   account (young of phase C never acquired adult behaviour; Marsden 1972: the deficit persisted
   after transfer to uncrowded universes). No parameter names a collapse day.
6. **Female reproductive senescence** `female_fertile_max_age_days` (Calhoun: menopause ≈ 560 d
   of age). Without it, early competent cohorts would resume breeding whenever density dipped.
7. Landmarks: `last_young_day` now means the last *surviving* birth (latest birth day among
   weaned young — Calhoun's "last surviving birth Day 600"); `peak_day` is the first day at
   ≥97% of the maximum (plateau-robust). Extra Calhoun facts reported alongside the canonical
   five (not in `mean_rel_error`): N@736 = 2056, adults@315 = 150, last conception ≈ 920.
8. Calibration: `scripts/calibrate_optuna.py --workers N --popsize N` runs CMA-ES generations
   in a process pool (ask/tell); `--x0` seeds the search from a YAML fragment. Priors widened /
   re-justified in `calib/priors.py` (adult lifespan 750–1100 d, weak stress mortality, etc.).
   The loss no longer demands a 30% drop by the horizon: between N=2056 (Day 736) and N=122
   (Day 1444) we only require N(1200)/peak ∈ [0.35, 0.85] (inferred band, flagged as such).
9. Tests: `tests/test_biology_guards.py` — no immature gestation, pups only REST/NEST,
   competence ∈ [0,1] and frozen for adults, surviving-young bookkeeping, Warp↔NumPy parity of
   stress + competence (max |Δ| ≈ 3e-8). Full suite green; NumPy determinism test unchanged.

Environment note: the phase-2 Optuna study was run from a repo-local `.venv` (Python 3.12.10,
numpy 2.5.4, optuna 5.0 + cmaes, no warp/torch); the shared omnilab venv has no optuna. The
NumPy sim path is identical in both (same interpreter + numpy build).

### Recalibration results (seed 7000, 1200 d, 6 ticks/day, CMA-ES 14×8 generations)
Optuna `CmaEsSampler`, popsize 14, 112 trials in 14 processes (ask/tell), start point = a
hand-picked fragment (loss 2.74). Wall **19.8 min**. Best trial 108, loss **0.463**; held-out
seeds 8000 / 8001 / 8002: 1.03 / 0.40 / 0.50 (mean 0.64; the 8000 miss is N@315 = 827 — early
exponential-phase stochasticity with 8 founders). Artifacts: `configs/calibrated_calhoun.yaml`
(fragment), `configs/default.yaml` (same values), `configs/calibration_study_p2b.json` (all trials).

| Landmark | Calhoun | Phase 1 (1600 d) | Phase 2 (pup-mill) | **Phase 2b** seed 7000 | held-out 8000–8002 |
|---|---:|---:|---:|---:|---:|
| First litters (day) | 104 | 221 | 115 | **111** | 110–111 |
| N @ day 315 | 620 | 48 | 594 | **672** | 404–827 |
| Peak N | 2200 | 1715 | 831 | **2261** | 2238–2305 |
| Peak day (first ≥97 % of max) | 560 | ~1395 | 585 (argmax) | **467** | 440–497 |
| Last surviving birth (day) | 600 | ≥1600 | 700 (horizon) | **813** | 814–835 |
| N @ day 736 | 2056 | — | — | **2106** | 2116–2171 |
| Adults @ day 315 | 150 | — | — | 217 | 153–258 |
| Last conception (day) | ≈920 | — | — | 793 | 794–831 |
| mean rel. error (canonical 5) | | 1.08 | 0.20 (artifact) | **0.14** | |
| Decline by day 1200 | yes | no | no | **1316 = 58 % of peak** | 1283–1428 |

1600-day validation run (`_output/run1600_p2b_tpd6`, identical trajectory through day 1200,
wall 45 s, 0 NaN; phases detected: adjustment → growth → stagnation → decline (onset 832) →
collapse (<50 % peak at 1228)):

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 97 | 29 | 0 | 0.97 | 96 |
| 300 | 461 | 159 | 55 | 0.60 | 477 |
| 400 | 1980 | 859 | 664 | 0.21 | 2234 |
| 500 | 2114 | 1958 | 1891 | 0.08 | 847 |
| 600 | 2156 | 2018 | 1977 | 0.07 | 492 |
| 700 | 2099 | 1999 | 1888 | 0.06 | 290 |
| 800 | 2061 | 1965 | 1864 | 0.06 | 342 |
| 900 | 1924 | 1924 | 1814 | 0.06 | 19 |
| 1000 | 1790 | 1790 | 1683 | 0.06 | 0 |
| 1200 | 1316 | 1316 | 1314 | 0.00 | 0 |
| 1300 | 589 | 589 | 589 | 0.00 | 0 |
| 1600 | 93 | 93 | 93 | 0.00 | 0 |

Calhoun: 2056 at 736, 122 at ~1444, 27 at 1588 (≈150 removed after day 1000). The decline is
now driven by the mechanism intended: cohorts born after ~day 330 mature with competence ≈ 0.1,
withdraw, and never breed; the competent founders' lineage ages past fertility (510 d) and dies
out at ~880 d. Nothing schedules it.

**Honest misses / open gaps**
- *Last surviving birth 813 vs 600 (all seeds 814–835).* Across the 112 trials the minimum was
  673 (trial 12, at the cost of peak 1412) and the landmark is uncorrelated with peak size
  (r = 0.01), so this is a **mechanism limit, not a tuning trade-off**. Conceptions actually
  stop *earlier* than Calhoun's (793 vs ≈920); the difference is that his late litters all died
  (mothers abandoned / attacked young) whereas ours are partly kept alive by communal passive
  nursing (any competent nursing female within 8 in feeds up to 6 pups per tick). Candidate
  fix for a phase-2c pass: stress-dependent litter abandonment / pup expulsion after birth
  (Gwizdałła & Duś use an abandonment probability above critical density) and restricting
  passive nursing to the mother's own nest box.
- *Peak ~90 days early* (467 vs 560): phase C is compressed — growth is Calhoun-like to ~day 300
  then jumps to the plateau within 100 days. Phase B doubling time is right; phase C's
  145-day doubling is not reproduced.
- *Adults @ 315 = 217 vs 150* (with maturity fitted at 64 d). Within ~1.5×; Calhoun's "adult"
  definition is not ours.
- *≈90 % of adults withdrawn from day 500.* Calhoun does not quantify this; it may be too
  extreme and is a side effect of competence collapsing to ≈0.06.
- **Not dt-invariant at the time of 2b — fixed in Phase 2c above** (kept for the record). Same parameters at 24 ticks/day
  (`_output/run1600_p2b_tpd24`, 173 s): first litters 110, N@315 **138**, peak **1088** @ 590,
  N@736 998, breeding never ceases (last surviving birth 1573), mean rel. error 0.60. Cause is
  the agent loop, not biology: movement is `speed·dt` per tick but the action is re-drawn every
  tick, so at 24 ticks/day a mother moves ~6 in toward her nest and then re-rolls, rarely
  reaching her pups (at 6 ticks/day she arrives in one tick); per-event effects (nursing
  amounts, wounds, ACT_NEST stress relief, social-drive decrements) are also per tick, not per
  day. `configs/default.yaml` and `smoke.yaml` are therefore pinned to `ticks_per_day: 6`
  (`SimConfig()` keeps 24 for the unit tests). Fix = action persistence (commit to a target
  until arrival) + dt-scaled event effects, then re-calibrate — logged as `docs/TASKS.md` P0-4.

## Phase 2 (2026-10-30 Asia/Seoul) — superseded by Phase 2b (pup-mill bug, see above)

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