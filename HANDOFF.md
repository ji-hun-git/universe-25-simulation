# HANDOFF — universe25-play

> **Audience:** collaborators.
> **Repo (private):** https://github.com/ji-hun-git/universe25-play  
> **Local path (lab PC):** `C:\Users\user\Projects\universe25-play`  
> **Owner:** Jason (ji-hun-git) · **Research partner:** gan  
> **Date:** 2026-10-30 (Asia/Seoul) · **Phase:** 1 complete; **phase 2 calibration done (2b/2d: mean landmark error 0.117, emergent collapse; 2c: tick loop dt-invariant)**; Warp parity partial; phase 3 (visuals) and phase 4 (play module) not started

Read this file first. Then read `PLAN.md`, `NOTES.md`, `docs/NVIDIA_STACK.md`, `docs/TASKS.md`. Follow `CONTRIBUTING.md` for day-to-day rules.

---

## 0. One-sentence mission

Build a **research-grade Universe 25 (Calhoun 1973) environment** with an optional **playground**, calibrate it to Death Squared landmarks, then ask whether **play-like behavior emerges in learning agents under abundance vs survival** — scored with **Burghardt’s 5 criteria** and a **provisional PlayScore** — with **no LLM agents, no imitation / behavior cloning, and no play reward**.

---

## 1. Research question (locked)

**Core claim (gan + Jason):**  
Play emerges in learning agents (no LLM, no imitation or behavior-cloning data) under **abundance** versus a **survival** world, scored with Burghardt’s 5 criteria. In the **same** setup we compare:

1. **Calhoun-style collapse** (behavioral sink under utopia density), and  
2. The **play bloom** predicted by surplus-resource theory (Auerbach, Kanarek & Burghardt 2015).

**Independent variables (sweep):**  
`abundance × density × toys × unpredictability`

**Play types to score (later module):**  
object · locomotor · social (role reversal, self-handicapping, play invitation) · rule play

**Burghardt’s 5 criteria (detection, not reward):**  
1. Incomplete / exaggerated / modified vs “serious” form  
2. Repeated but varied (not stereotypy alone)  
3. Not immediately functional for survival (task-reward difference near 0)  
4. Voluntary / free-choice  
5. Occurs in a **relaxed field** (high energy, low stress / threat)

---

## 2. Metrics (PROVISIONAL — label everything unvalidated)

Gan’s formalization (**not validated**; agents must never optimize these):

| Symbol | Meaning (provisional) |
|--------|------------------------|
| **F** | Task-reward difference near 0 (play ≠ reward-max) |
| **V** | Free-choice preference for playground under free choice |
| **D** | Divergence (e.g. JS) between play-like and “serious” action distributions |
| **S** | Recurrence × motif entropy (repeated but varied) |
| **G** | Gate: high energy ∧ low stress (relaxed field) |

\[
\mathrm{PlayScore} = G \cdot (1 - |F|) \cdot V \cdot D \cdot S
\]

**Hard protocol:**

- **Optimize with one measure, evaluate with another** (agents cannot game PlayScore).
- Log components as `*_unvalidated` in metrics schema.
- Phase-1 need-driven mice: `F ≈ 0` by construction (no external task reward / no play term).

**Validation plan (later):**

1. PlayScore must separate play from **PPO**, **ICM**, **RND**, and **random** baselines.  
2. Optional: check on real animal pose data **as a ruler only — never for training**.  
3. **Spinka transfer test:** do agents that “played” recover better from pushes / friction / limb perturbations?  
4. **Pre-commit to reporting negative results.**  
5. **Do not overclaim** “fun”, consciousness, or a world model.

---

## 3. Hard rules (non-negotiable)

| ID | Rule |
|----|------|
| **H1** | Synthetic agents only — no animal/human play datasets for training |
| **H2** | **No play reward / observation / goal / utility term** named play, bout, motif, exaggeration, etc. Playground = geometry + manipulable objects. Curiosity / boredom / homeostasis are generic drives; `ACT_MANIPULATE` satisfies those only |
| **H3** | **No LLM in agents** (narrator LLMs later optional and off the critical path) |
| **H4** | Does not import or change L3 ecology; Track E exploratory |
| **Det** | Seeded `numpy.random.Generator`; CPU trajectories must be deterministic for the same seed+config |
| **Honest** | Calibration errors, failed collapses, and negative play results go in `NOTES.md` without spin |

If a PR / commit introduces a play reward, reject it.

---

## 4. Current status (as of phase 2j, 2026-10-31)

### Phase 1 — done

- Need-driven Universe 25 + playground geometry (Calhoun 101×101 in, 16 cells, 256 nests, design capacity 3840).
- SoA agents (roles, 11 actions, drives). No `ACT_PLAY`.
- Parquet metrics + provisional PlayScore accumulator + calibration script.
- Tests: geometry, determinism, conservation, Warp smoke (`tests/run_tests.py`).
- Private GitHub repo live; MIT license.

### Phase-1 long run (honest)

Command:  
`python main.py --seed 7000 --out _output/run1600_abund_pg --days 1600 --backend numpy --device cpu --max-agents 4096 --playground on`

| Metric | Value |
|--------|-------|
| Wall | **296.6 s** (~4.9 min) |
| Ticks | 38400 |
| Peak N | **1715** at day **~1395** |
| Final N | 1339 |
| Births / deaths / conceptions | 62637 / 61306 / 32122 |
| NaNs | 0 |
| Backend | **numpy/cpu** (Warp available; tick not fully device-resident) |

**Calibration vs Calhoun 1973 (mean relative error ≈ 1.08):**

| Landmark | Target | Observed | Rel err |
|----------|--------|----------|---------|
| First litters | 104 | 221 | 1.13 |
| N @ day 315 | 620 | 48 | 0.92 |
| Peak N | 2200 | ~1708–1715 | ~0.22 |
| Peak day | 560 | ~1392–1395 | ~1.49 |
| Last young | 600 | ~1599.75 | ~1.67 |

Phases detected: adjustment, growth, stagnation. **No collapse by day 1600.**  
Label: **exploratory / negative on timing calibration**; peak magnitude within ~22% is the only near-hit.

### NVIDIA stack

| Piece | Status |
|-------|--------|
| **Warp** 1.18 (sm_120) | Core; hybrid tick + post-step kernels; device-resident action select still TODO |
| **NVTX** via `torch.cuda.nvtx` | Integrated |
| **USD (`pxr`)** pen export | Works → `_output/usd/pen.usda` |
| **CUDA Graphs** | Scaffolding + microbench wins on device-only post-step; hybrid sync-bound |
| **Newton** 1.7.0 | Detected + stub (`newton_playground.py`) — not stepped |
| **RL env spec** | Stub only (`rl_env_spec.py`) — Gymnasium / Isaac Lab style, PlayScore eval-only |
| **GPU on lab PC** | **RTX 5080** (not 5070) — Blackwell **sm_120**. Same family as 5070 |

See `docs/NVIDIA_STACK.md`, `docs/NSIGHT.md`.

### Phase 2 — calibration (2026-10-30) — SUPERSEDED

The phase-2 CMA-ES fit (first litters 115, N@315 594, peak 831 @ 585, no collapse) was an
artifact of a **pup-mill bug**: a zero softmax utility still carried probability, so pre-weaning
pups foraged, fought and *conceived* (median gestating age 15 d), while adults died of runaway
stress at ~80 d. Full diagnosis in `NOTES.md` ("Phase 2b").

### Phase 2b — bug fix + emergent collapse mechanism + recalibration (2026-10-30)

- Eligibility mask in action selection (pups REST/NEST only; MATE needs maturity); age gate in `_try_mate`.
- Births in the nest box; mothers nurse at the nest; wounds heal; stress relaxes toward gain/decay.
- **Developmental imprinting**: SoA trait `competence` lost while young under crowding, frozen at
  maturity; scales conception, maternal investment, withdrawal ("beautiful ones"). Irreversible by
  construction, matching Calhoun/Marsden. Plus female reproductive senescence (~560 d of age).
- Landmarks: `last_young_day` = last *surviving* birth; `peak_day` = first day ≥ 97 % of max;
  extra Calhoun facts (N@736 = 2056, adults@315 = 150, last conception ≈ 920) reported.
- Parallel CMA-ES (`--workers/--popsize`, process pool) from the repo-local `.venv` (has optuna).
- New tests: `tests/test_biology_guards.py` (incl. Warp↔NumPy stress/competence parity).

### Phase 2d — daily-only conception, nest-box nursing, litter abandonment (2026-10-30)

- `ACT_MATE` is courtship only; all conception happens in the daily breeding pass (removes the
  per-tick conception channel that made early growth resolution-dependent).
- Nursing feeds only pups of the mother's own nest box; stressed nursing mothers abandon their
  box's litter with daily probability `litter_abandon_p` (pups lose the box and starve).
- Recalibrated (CMA-ES 112 trials, 21 min): loss 0.236.

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d, 56 s wall):**

| Landmark | Calhoun | Phase 1 | Phase 2b | **Phase 2d** |
|----------|--------:|--------:|---------:|-------------:|
| First litters | 104 | 221 | 111 | **106** |
| N @ 315 | 620 | 48 | 672 | 494 |
| Peak N | 2200 | 1715 | 2261 | **2023** |
| Peak day (first ≥97 %) | 560 | ~1395 | 467 | **553** |
| Last surviving birth | 600 | ≥1600 | 813 | 762 (mechanism gap, see NOTES) |
| N @ 736 | 2056 | — | 2106 | **1924** |
| Adults @ 315 | 150 | — | 217 | **163** |
| N @ 1200 / 1600 | declining; 27 @1588 | 1339 @1600, growing | 1316 / 93 | **853 / 8** |
| mean rel. error (5) | | 1.08 | 0.14 | **0.117** |

Phases detected: adjustment → growth → stagnation → decline (791) → collapse (1167). Held-out
seeds 8000–8002: peak 1846–1991, N@736 1781–1919; N@315 varies 242–571 (8 founders ⇒ the
exponential phase is seed-sensitive).
**Resolution:** calibrated at the reference 6 ticks/day (`SimConfig.ticks_per_day_ref`); since
phase 2c the tick loop is dt-invariant (per-decision effects × ref/tpd, random walks √-scaled,
movement reaches its target within one decision), so 12 or 24 ticks/day give the same arc
(peak 2345 / 2314, N@736 2167 / 2191, collapse onset 1225 / 1203). Residual: early growth is a
few % faster per day at finer ticks (N@315 753 / 928) — see NOTES "Phase 2c".
Full tables and the open gaps in `NOTES.md` → "Phase 2b". The worker that owned phase 2
reported it finished; `src/` is no longer dual-edited, but still pull/rebase before pushing.

### Phase 2e — maternal breakdown, held decisions, lethal starvation, recalibration (2026-10-30)

- **Post-weaning maternal breakdown**: SoA `maternal_cap` eroded irreversibly (daily) for weaned
  females above `maternal_erosion_stress`; caps maternal investment at conception/birth, so
  conceptions continue while no litter is nursed (Calhoun phase C/D).
- **Social-breakdown switch** decoupled from the conception ramp (`breakdown_density_threshold`)
  and counting weaned animals (`breakdown_density_counts: weaned`) — on total N it was a
  thermostat.
- **Relaxation-form nursing** per nest box (`nurse_rate_per_day`, `nurse_max_pups`), lactating
  (ROLE_NURSING) females only.
- **Lethal starvation** (`starvation_hazard_per_day` 1.0; was a hard-coded 0.1 that let one unfed
  pup in ten reach weaning) and exact `1 − exp(−h·dt)` death draws (NumPy + Warp).
- **Held decisions**: agents decide every 1/6 day; per-decision events happen in full on the
  decision tick, held ticks integrate continuous physics only. 6-tpd trajectory bit-identical.
- **Landmark**: `last_young_day` is now the rate-based cessation of surviving births (30-day
  rate < 5 % of its max for good); the strict latest-weaned-pup day is reported alongside (it is
  single-survivor noise: 1111 / 1017 at held-out seeds 8000 / 8001).
- Recalibrated (three CMA-ES studies, final 224 trials with `--sigma0 0.1`): loss 0.159.

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d, 249 s wall):**

| Landmark | Calhoun | Phase 2b | Phase 2d | **Phase 2e** | held-out 8000–8002 |
|----------|--------:|---------:|---------:|-------------:|---:|
| First litters | 104 | 111 | 106 | **104** | 104 |
| N @ 315 | 620 | 672 | 494 | 542 | 346–630 |
| Peak N | 2200 | 2261 | 2023 | **2320** | 2231–2344 |
| Peak day (first ≥97 %) | 560 | 467 | 553 | 486 | 473–555 |
| Surviving births cease | 600 | 813 | 762 | **553** | 549–656 |
| N @ 736 | 2056 | 2106 | 1924 | **2077** | 2049–2146 |
| Adults @ 315 | 150 | 217 | 163 | 182 | 143–276 |
| Last conception | ≈920 | 793 | 755 | 1113 (miss) | 1161–1194 |
| N @ 1200 / 1600 | declining; 27 @1588 | 1316 / 93 | 853 / 8 | **1699 / 2** | 1655–1737 @1200 |
| mean rel. error (5) | | 0.14 | 0.117 | **0.078** | 0.05–0.16 |

Phases: adjustment → growth → stagnation → decline (733) → collapse (1345). Births go on at
≈2000 per 100 d to day 900 with no survivors; the plateau is adult survival; the 400–600 cohorts
die of age between 1300 and 1550.
**Resolution:** same parameters at 24 ticks/day give the same arc (peak 2296 / 536, cessation 582, N@736 2128, collapse onset 1386 vs 1345) but early growth is still ≈ +17 % / +25 % faster per day at 12 / 24 tpd by day 400 (12 seeds, 1.3–1.7 se, monotone) — continuous-process discretisation, see NOTES.
Full tables, the diagnoses (thermostat switch, unfed-pup leak, interleaving bias) and the open
gaps (last conception ≈200 d late, early peak, steep late collapse, low uncrowded pup survival)
are in `NOTES.md` → "Phase 2e".

### Phase 2f — exact stress relaxation, recalibration (2026-10-30)

- Stress relaxes exactly (`s += (gain/decay − s)·(1 − exp(−decay·dt))`) in NumPy and the Warp
  kernel; nest kick and stress-driven social withdrawal are per-decision events; the Warp
  kernel takes the event scale from a device buffer (CUDA-graph safe).
- Removes the last systematic resolution dependence: at the 2e parameters the 12-seed N@400 went
  from 1065 / 1248 / 1331 (6 / 12 / 24 tpd) to 1122 / 1021 / 1215 — no trend, within ≈1 se.
- Recalibrated from the 2e optimum (168 trials, 39 min): loss 0.151.

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d, 173 s wall):**

| Landmark | Calhoun | Phase 2d | Phase 2e | **Phase 2f** | held-out 8000–8002 |
|----------|--------:|---------:|---------:|-------------:|---:|
| First litters | 104 | 106 | 104 | **102** | 102–105 |
| N @ 315 | 620 | 494 | 542 | 531 | 286–564 |
| Peak N | 2200 | 2023 | 2320 | 2502 | 2457–2602 |
| Peak day (first ≥97 %) | 560 | 553 | 486 | 502 | 429–604 |
| Surviving births cease | 600 | 762 | 553 | **533** | 467–654 |
| N @ 736 | 2056 | 1924 | 2077 | **2181** | 2223–2257 |
| Adults @ 315 | 150 | 163 | 182 | **163** | 88–217 |
| Last conception | ≈920 | 755 | 1113 | 1063 (miss) | 1076–1196 |
| N @ 1200 / 1400 / 1600 | 2056@736, 122@1444, 27@1588 | 853 / — / 8 | 1699 / 729 / 2 | **1756 / 370 / 1** | 1779–1857 @1200 |
| mean rel. error (5) | | 0.117 | 0.078 | 0.103 | 0.11–0.17 |

Phases: adjustment → growth → stagnation → decline (614) → collapse (1310). Births continue at
≈2000 per 100 d to day 900 with no survivors.
**Resolution:** the same parameters at 24 ticks/day reproduce the whole arc at seed 7000 (peak 2580 / 477, cessation 513, N@736 2235, collapse onset 1309 vs 1310, 1 mouse at 1600) and 12 seeds show no resolution trend by day 400 (6 vs 24 within 5 %).
Diagnoses, tables and open gaps (last conception ≈150–270 d late, peak 12–18 % high, steep late
collapse, low uncrowded pup survival) in `NOTES.md` → "Phase 2f" / "Phase 2e".

### Phase 2g — male courtship breakdown (2026-10-31)

- SoA `courtship_cap`: weaned males above `courtship_erosion_stress` lose courtship capacity
  irreversibly (`courtship_erosion_rate × excess`, daily); the breeding pass uses the cell's mean
  `competence × courtship_cap` of the eligible males. Calhoun phase D: males stopped courting,
  conceptions ended ≈920 while fertile females remained.
- `last_conception_day` is now the rate-based cessation of conceptions (30-day count < 5 % of its
  maximum for good), like surviving births; the strict single-event day is reported alongside
  (`last_conception_strict_day`). The strict day swings ±100 d between parameter nudges.
- Rate 0.03 / threshold 0.5 chosen by a 1-D scan (plateau 0.015–0.04 → cessation 984–921, cliff
  at 0.05 → 650) and confirmed as the best of an 84-trial CMA-ES study (no trial beat it).

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d):**

| Landmark | Calhoun | Phase 2e | Phase 2f | **Phase 2g** | held-out 8000–8002 |
|----------|--------:|---------:|---------:|-------------:|---:|
| First litters | 104 | 104 | 102 | **102** | 102–105 |
| N @ 315 | 620 | 542 | 531 | 531 | 286–564 |
| Peak N | 2200 | 2320 | 2502 | 2482 | 2453–2608 |
| Peak day (first ≥97 %) | 560 | 486 | 502 | 493 | 434–603 |
| Surviving births cease | 600 | 553 | 533 | **547** | 467–666 |
| N @ 736 | 2056 | 2077 | 2181 | **2173** | 2158–2285 |
| Adults @ 315 | 150 | 182 | 163 | **163** | 88–217 |
| Conception cessation | ≈920 | 1113 (strict) | 1003 | **930** | 885–1059 |
| N @ 1200 / 1400 / 1600 | 2056@736, 122@1444, 27@1588 | 1699 / 729 / 2 | 1756 / 370 / 1 | **1779 / 391 / 6** | 1767–1919 @1200 |
| mean rel. error (5) | | 0.078 | 0.103 | **0.100** | 0.11–0.17 |

Phases: decline (622) → collapse (1312). **Resolution:** 24 ticks/day gives peak 2530 / 469, cessation 502, N@736 2185, conception cessation 847, collapse onset 1315; 12 seeds N@400 1314 ± 115 vs 1391 ± 111 (+6%).
Diagnoses, tables and open gaps (peak 12–18 % high, steep late collapse, low uncrowded pup
survival, early-phase seed spread) in `NOTES.md` → "Phase 2g" / "Phase 2f" / "Phase 2e".

### Phase 2h — graded social-breakdown pressure (2026-10-31)

- `breakdown_density_ramp`: the social-breakdown stress boost ramps linearly over this weaned-
  density width up to `breakdown_density_threshold` instead of switching on there (width 0 =
  the 2e–2g step, bit-identical). Calhoun phase C: infant mortality rose gradually from Day 315;
  the model tripled between days 300 and 420 with a flat weaned fraction and then stopped in one
  window when the switch tripped. NumPy + Warp kernel (parity 1.9e-9).
- Diagnosis in NOTES: the raw peak is a 3–4 % spike on the plateau (pulsed litters, doomed pups in
  the pipeline; `peak_n_31d_mean` now reported, not fitted); adults decline at Calhoun's rate after
  the peak; with a lower plateau the conception suppression bites less, so births to eroded mothers
  keep N@736 at ≈0.87 of the peak (Calhoun 0.93).
- Recalibrated from the 2g optimum + ramp 0.45 (168-trial CMA-ES, popsize 14, `--sigma0 0.1`,
  40 min: no trial beat the start point, next best 0.165 — the single-seed objective is
  noise-limited; a multi-seed objective is the next method step). 12 seeds, 800 d: peak
  2221 ± 21 at 6 ticks/day vs 2266 ± 16 at 24 (Calhoun 2200), N@736 1869 ± 11 vs 1912 ± 11,
  peak day 475 ± 8.

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d):**

| Landmark | Calhoun | Phase 2f | Phase 2g | **Phase 2h** | held-out 8000–8002 |
|----------|--------:|---------:|---------:|-------------:|---:|
| First litters | 104 | 102 | 102 | **102** | 102–105 |
| N @ 315 | 620 | 531 | 531 | **531** | 286–564 |
| Peak N | 2200 | 2502 | 2482 | **2115** | 2127–2328 |
| Peak day (first ≥97 %) | 560 | 502 | 493 | **503** | 421–565 |
| Surviving births cease | 600 | 533 | 547 | **551** | 488–615 |
| N @ 736 | 2056 | 2181 | 2173 | **1845** | 1838–1916 |
| Adults @ 315 | 150 | 163 | 163 | **163** | 88–217 |
| Conception cessation | ≈920 | 1003 | 930 | **932** | 812–1011 |
| N @ 1200 / 1400 / 1600 | 2056@736, 122@1444, 27@1588 | 1756 / 370 / 1 | 1779 / 391 / 6 | **1426 / 273 / 0** | 1422–1524 @1200 |
| mean rel. error (5) | | 0.103 | 0.100 | **0.077** | 0.10–0.13 |

Phases: decline (671) → collapse (1291). **Resolution:** 24 ticks/day gives peak 2389 / 482, cessation 510, N@736 1948, conception cessation 805, collapse onset 1284; 12 seeds N@400 1316 ± 112 vs 1399 ± 109 (+6%).
Diagnoses, tables and open gaps in `NOTES.md` → "Phase 2h" (and 2g / 2f / 2e).

### Phase 2i — nursing-disturbance brake, multi-seed calibration (2026-10-31)

- `nurse_disturb_coef` / `nurse_disturb_density`: a mother's effective maternal investment while
  nursing is scaled by exp(−coef × max(0, local cell density − onset)) — a reversible,
  density-graded brake on phase-C growth (Calhoun: nursing females disturbed under crowding,
  infant mortality rose before the breakdown). With it the breakdown ramp narrows back to
  0.2 (2h: 0.45) and the plateau keeps its level while the timing moves later.
- `fertility_cap_floor` (conception probability following the female's maternal capacity) is a
  documented negative result: it lowers N@736 and advances the peak. Off (1.0).
- `scripts/calibrate_optuna.py --train-seeds 7000,7001,7002`: the objective is the mean loss over
  the training seeds (one sim per seed per trial); the single-seed objective was noise-limited
  (2g, 2h). The 112-trial study (51 min) reached a lower mean loss (0.243 vs 0.341) only by fitting
  the training seeds' early phase: its best trial has the peak 13 % high and conceptions ending 16 %
  late, held-out mean loss 0.96 vs 0.45 — the hand-chosen start point was kept. Squared relative
  error under-weights 10–15 % misses on the plateau landmarks against N@315 / adults@315, whose
  seed sd is ≈35 %; inverse-variance weights are the next method step.
- Both new terms off → bit-identical to 2h (600-d hash).

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d):**

| Landmark | Calhoun | Phase 2g | Phase 2h | **Phase 2i** | held-out 8000–8002 |
|----------|--------:|---------:|---------:|-------------:|---:|
| First litters | 104 | 102 | 102 | **102** | 102–105 |
| N @ 315 | 620 | 531 | 531 | **528** | 286–569 |
| Peak N | 2200 | 2482 | 2115 | **2234** | 2231–2309 |
| Peak day (first ≥97 %) | 560 | 493 | 503 | **518** | 469–606 |
| Surviving births cease | 600 | 547 | 551 | **583** | 556–717 |
| N @ 736 | 2056 | 2173 | 1845 | **1949** | 1953–2046 |
| Adults @ 315 | 150 | 163 | 163 | **163** | 88–206 |
| Conception cessation | ≈920 | 930 | 932 | **915** | 867–1054 |
| N @ 1200 / 1400 / 1600 | 2056@736, 122@1444, 27@1588 | 1779 / 391 / 6 | 1426 / 273 / 0 | **1515 / 480 / 0** | 1514–1649 @1200 |
| mean rel. error (5) | | 0.100 | 0.077 | **0.057** | 0.08–0.17 |

Phases: decline (662) → collapse (1300). **Resolution:** 24 ticks/day gives peak 2274 / 486, cessation 581, N@736 1922, conception cessation 905; 12 seeds, 800 d: peak 2269 ± 11 (6 tpd) vs 2281 ± 8 (24 tpd), peak day 524 ± 9 vs 521 ± 9, N@736 1990 ± 15 vs 1992 ± 13.
Diagnoses, scan tables and open gaps in `NOTES.md` → "Phase 2i" (and 2h / 2g / 2f / 2e).

### Phase 2j — inverse-seed-variance loss weights, multi-seed recalibration (2026-10-31)

- `calib/priors.py`: landmark loss weights are now ∝ 1 / (seed sd² + 0.05²), normalised to the
  previous total of 12 (`LANDMARK_REL_SEED_SD`, measured over 12 seeds at 1200 d: N@315 sd 27 %,
  adults@315 42 %, plateau landmarks 2–7 %). Each term is (rel. error / σ)², so a one-sigma miss
  costs the same on every landmark and the seed-dominated early phase (weights 0.10 / 0.04) can no
  longer buy the plateau landmarks (peak 2.7, N@736 2.4, conception cessation 1.6, peak day 1.3,
  cessation 1.0). `tests/test_calib_loss.py`. Loss values of earlier studies are on the old scale.
- Multi-seed CMA-ES rerun under the new weights (112 trials, train seeds 7000/7001/7002, 51 min):
  no trial beat the 2i point (mean loss 0.033; runner-up 0.042 trades a later peak day for a later
  conception cessation); the drift to N@315 of the 2i study is gone. Held-out losses on the new
  scale 0.031 / 0.060 / 0.118.
- **Calibrated parameters unchanged from 2i** (`configs/default.yaml`, `calibrated_calhoun.yaml`);
  the 2i table and validation apply. Study artifact: `configs/calibration_study_p2j.json`.

---

## 5. Architecture map

```
universe25-play/
├── HANDOFF.md              ← you are here
├── PLAN.md                 ← mini-prereg (hypotheses, arms, stop rules)
├── NOTES.md                ← dated honest results
├── README.md
├── pyproject.toml          ← package universe25, py>=3.11
├── main.py                 ← thin entry → universe25.__main__
├── configs/
│   ├── default.yaml        ← Calhoun + playground + biology + drives
│   └── smoke.yaml          ← 30-day smoke overrides
├── docs/
│   ├── TASKS.md            ← prioritized task list
│   ├── NVIDIA_STACK.md
│   └── NSIGHT.md
├── scripts/
│   ├── calibrate.py
│   ├── calibrate_optuna.py
│   ├── benchmark_backends.py
│   ├── microbench_warp_post.py
│   └── probe_nvidia.py
├── src/universe25/
│   ├── __main__.py         ← CLI: --seed --out --config --days --backend --device --playground --max-agents
│   ├── config.py           ← pydantic: Geometry, Playground, Resource, Biology, Drive, SimConfig
│   ├── sim.py              ← Universe25Sim (need-driven tick; density stress; breeding; logging)
│   ├── rng.py
│   ├── agents/
│   │   ├── state.py        ← AgentSoA, ROLE_*, ACT_* (11 actions; no PLAY)
│   │   ├── drives.py       ← H2 documentation
│   │   └── device.py       ← optional Warp mirror buffers
│   ├── world/
│   │   └── geometry.py     ← World, Cell, Nest, PlayObject, build_world
│   ├── metrics/
│   │   ├── logger.py       ← parquet
│   │   ├── playscore.py    ← PlayScoreAccumulator (unvalidated)
│   │   └── calibration.py  ← Calhoun landmarks + phase detect
│   ├── calib/              ← Optuna/CMA-ES helpers (phase 2)
│   ├── warp_kernels/
│   │   ├── engine.py       ← WarpTickEngine + graph capture
│   │   └── kernels.py
│   ├── nvidia/
│   │   ├── nvtx_ranges.py
│   │   ├── cuda_graphs.py
│   │   ├── newton_playground.py  ← stub
│   │   ├── usd_export.py
│   │   ├── rl_env_spec.py        ← stub (forbidden play rewards listed)
│   │   └── stack_info.py
│   └── io/snapshots.py
├── tests/
│   ├── run_tests.py        ← no pytest in shared venv; runs test_*.py as __main__
│   ├── test_geometry.py
│   ├── test_determinism.py
│   ├── test_conservation.py
│   ├── test_biology_guards.py  ← no immature conception, pups nest-bound, competence, Warp parity
│   └── test_warp_smoke.py
├── .venv/                  ← gitignored; repo-local Python with optuna/cmaes for calibration
└── _output/                ← gitignored runs
```

**Action codes** (`state.py`): REST, FORAGE, DRINK, NEST, SOCIAL, EXPLORE, MANIPULATE, AGGRESS, MATE, NURSE, WITHDRAW.  
**Roles:** pup, juvenile, territorial male, subordinate male, breeding female, nursing, withdrawn (“beautiful ones”), dead.

---

## 6. Setup / run / test (lab PC, PowerShell 5.1)

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$proj = 'C:\Users\user\Projects\universe25-play'
$py   = 'C:\Users\user\Desktop\omnilab\.venv\Scripts\python.exe'
$gh   = 'C:\Users\user\tools\gh\gh.exe'
$env:PYTHONPATH = "$proj\src"
Set-Location $proj

# Probe NVIDIA
& $py -X utf8 "$proj\scripts\probe_nvidia.py"

# Smoke
& $py -X utf8 "$proj\main.py" --seed 7000 --out "$proj\_output\smoke" --config "$proj\configs\smoke.yaml" --days 30

# Tests (shared venv has no pytest)
& $py -X utf8 "$proj\tests\run_tests.py"

# Calibrate a run
& $py -X utf8 "$proj\scripts\calibrate.py" --metrics "$proj\_output\smoke\metrics.parquet" --out "$proj\_output\smoke\calibration.json" --run-json "$proj\_output\smoke\run.json"

# Long abundant+playground, calibrated (default.yaml = phase-2d params, 6 ticks/day; ~55 s on CPU)
# → peak 2028, N@736 1924, 8 left at 1600, calibration_mean_rel_error 0.117
& $py -X utf8 "$proj\main.py" --seed 7000 --out "$proj\_output\run1600_p2b" --days 1600 --backend numpy --device cpu --max-agents 4096 --playground on

# Warp path (when kernels ready)
& $py -X utf8 "$proj\main.py" --seed 7000 --out "$proj\_output\warp_smoke" --backend warp --device cuda --days 5 --max-agents 4096

# Calibration (CMA-ES). optuna lives ONLY in the repo-local .venv (same Python/numpy as omnilab,
# no warp/torch). 16-core box: 14 workers, popsize 14, 1200 d, 6 ticks/day ≈ 3 min / generation
# (224 trials = 16 generations ≈ 47 min). --sigma0 0.1: the default initial step (min range / 6)
# is a third of the range for the unit-range parameters. The start point itself is trial 0.
$pyc = "$proj\.venv\Scripts\python.exe"
& $pyc -X utf8 -u "$proj\scripts\calibrate_optuna.py" --seed 7000 --train-seeds 7000,7001,7002 --trials 112 `
  --popsize 14 --workers 14 --sigma0 0.1 --days 1200 --ticks-per-day 6 `
  --x0 "$proj\configs\calibrated_calhoun.yaml" --out "$proj\_output\calib_cma"
# --train-seeds: objective = mean loss over the seeds (one sim per seed per trial, 2i); with three
# seeds a generation of 14 takes ~10 min (112 trials = 8 generations ~ 50 min). Loss weights are
# inverse seed variance (2j, calib/priors.py); losses of studies before 2j are on another scale.
```

**Git (pathspec discipline — never `git add .` on a shared tree):**

```powershell
git -C $proj --no-optional-locks status --short
git -C $proj pull --rebase origin master
git -C $proj add -- HANDOFF.md docs/TASKS.md
git -C $proj commit -m "docs: handoff menu"
& $gh auth status   # if needed
git -C $proj push origin master
```

Seeds: build/training `7000–7009`; unit tests `7100`; eval worlds later `8000–8009`. Every command takes `--seed`.

---

## 7. Roadmap + acceptance criteria

### Phase 1 — Environment substrate ✅
- [x] Calhoun geometry + playground AABB + objects  
- [x] Need-driven agents, density stress, roles  
- [x] Metrics + unvalidated PlayScore parts  
- [x] Determinism / geometry / conservation tests  
- [x] 1600-day run + honest calibration in NOTES  

### Phase 2 — Calibrate + GPU (calibration DONE 2026-10-30; GPU parity partial)
**Accept when:**
- [x] Mean relative landmark error **≪ 1.0** → **0.057** at seed 7000, 0.08–0.17 held-out (phase 2i: first litters 102, peak 2234 @ 518, surviving births cease 583, N@736 1949, conceptions cease 915; 2b was 0.14)
- [x] Collapse phase appears under abundant arm → decline from 662, N(1200) = 68 % of peak, 480 at 1400, 0 left at 1600 (Calhoun 122 at ~1444, 27 at 1588); surviving births cease at 583, conceptions at 915 (2e–2j); documented misses: peak day ≈35 d early, N@736 3 % low, late collapse steep — see NOTES
- [~] Warp tick path correct vs NumPy reference: density-stress + imprinting kernel parity test added (3e-8); mortality (hazard-level) and cells parity still open; CUDA Graph speedup documented in NSIGHT
- [x] No NaNs (0 across calibration, held-out and 1600-d runs); `docs/NSIGHT.md` benches unchanged (no kernel perf work this round)

Phase 2c (done): dt-invariance of the tick loop. Phase 2d (done): daily-only conception,
nest-box nursing, litter abandonment. Phase 2e (done): post-weaning maternal breakdown, weaned-
density breakdown switch, relaxation nursing, lethal starvation, held decisions. Phase 2f
(done): exact stress relaxation, per-decision kick/withdrawal, recalibrated (canonical mean
landmark error 0.103 at seed 7000, 0.11–0.17 held-out; surviving births cease 467–654 while
conceptions continue; 6 vs 24 ticks/day agree within 5 %). Phase 2g (done): male courtship
breakdown ends conceptions at 930 (held-out 885–1059; Calhoun ≈920), rate-based
conception landmark. Phase 2h (done): graded breakdown pressure (ramp in weaned density
instead of a step) brings the peak to 2115 @ 503 (held-out 2127–2328) with
N@736 1845 (held-out 1838–1916); canonical error 0.077. Phase 2i (done): nursing-disturbance
brake on phase C + narrower ramp, multi-seed CMA-ES objective — peak 2234 @ 518
(12 seeds 2269 ± 11 @ 524 ± 9), surviving births cease 583, N@736 1949
(12 seeds 1990 ± 15); canonical error 0.057 (held-out 0.08–0.17). Phase 2j (done): landmark loss
weights ∝ inverse seed variance (N@315 / adults@315 no longer buy the plateau); the multi-seed
CMA-ES rerun under them kept the 2i point (no trial beat it; runner-ups are plateau-faithful
trade-offs, not N@315 fits). Remaining candidates (priority order): a later phase C (peak day
524 ± 9 over 12 seeds vs 560: the nursing brake acts on pup survival while births run at 1000–1200
per 30 days; a conception-rate brake is untested); a lifespan distribution (late collapse too steep); vectorize
`_passive_nurse` / per-agent loops (`docs/TASKS.md` P1-3); Warp mortality-kernel parity at hazard level.

### Phase 3 — Visuals + dashboard
**Accept when:**
- Top-down 16-cell pen viewer (mice as role-colored dots; stress trail / hopper heatmap)
- Editorial dashboard (population + phases shaded; conception; wounds; nest occupancy; % withdrawn; V and G)
- Look: paper `#F4F0E6`, ink `#1A1A1A`, stress `#8B1E1E`, nest teal `#2F5D50`; IBM Plex / Source Serif; **uPlot** charts; **no purple glows, glassmorphism, or AI-slop chrome**
- shadcn/ui restyled to that palette (not default violet)

### Phase 4 — Play behavior module (after env frozen)
**Accept when:**
- Playground free-choice and object/locomotor/social detectors implement Burghardt gates without rewarding play
- Sweep harness: abundance × density × toys × unpredictability
- Baselines: PPO, ICM, RND, random — **PlayScore eval-only**
- Spinka transfer protocol sketched + seed list frozen in a new PLAN section
- H2 audit still passes (grep for play reward terms)

### Phase 5 — Paper-grade release hygiene
README demos, pinned figures, reproducible `_output` cards, negative-result section.

---

## 8. Visual / dashboard direction (do not “AI polish”)

Inspired by Primer / Nicky Case explorables / scientific editorial design:

| Token | Value |
|-------|-------|
| Paper | `#F4F0E6` |
| Ink | `#1A1A1A` |
| Stress / sink | `#8B1E1E` |
| Nest / life | `#2F5D50` |
| Type | Source Serif (body) + IBM Plex Sans/Mono (UI/data) |
| Charts | **uPlot** (fast, tiny) |
| View | Top-down pen, 4×4 cells, nests as small marks, playground AABB dashed |
| Forbidden | Purple gradients, glass blur, neon robots, stock “AI neural” imagery |

---

## 9. Experimental arms (from PLAN.md)

| Arm | Label | Notes |
|-----|-------|-------|
| Abundance + playground | `TRACK-E-U25-ABUND-PG` | Phase-1 delivered (seed 7000) |
| Abundance, no playground | `TRACK-E-U25-ABUND-NOPG` | seed 7001 |
| Scarce + playground | `TRACK-E-U25-SCARCE-PG` | deferred; seed 7002 |

Prediction link to Leibo Gathering: scarcity → more aggression; abundance → peace **and** (our add) a band where Burghardt-positive play appears — or Calhoun withdrawn “beautiful ones” if too easy.

---

## 10. References (keep in README + here)

**Universe 25 / behavioral sink**
- Calhoun JB (1973). Death Squared. *Proc R Soc Med*. [PMC1644264](https://pmc.ncbi.nlm.nih.gov/articles/PMC1644264/)
- Calhoun JB (1962). Population density and social pathology. *Scientific American*.
- RatUtopia — [mantzaris/RatUtopia](https://github.com/mantzaris/RatUtopia), [arXiv:2508.08587](https://arxiv.org/abs/2508.08587)
- Mouse utopia model — [tomgwizd/Mouse-utopia-model](https://github.com/tomgwizd/Mouse-utopia-model), [PMC12939635](https://pmc.ncbi.nlm.nih.gov/articles/PMC12939635/)

**Play / abundance**
- Auerbach, Kanarek & Burghardt (2015). To play or not to play? That’s a resource abundance question. [doi:10.1177/1059712315611188](https://doi.org/10.1177/1059712315611188)
- Learning to Play — [arXiv:1802.07442](https://arxiv.org/abs/1802.07442) (curiosity / exploration; not Burghardt scoring)

**Multi-agent / scarcity aggression**
- Leibo et al. (2017). Gathering. [arXiv:1702.03037](https://arxiv.org/abs/1702.03037)
- Melting Pot — [google-deepmind/meltingpot](https://github.com/google-deepmind/meltingpot)
- Neural MMO — [neuralmmo.github.io](https://neuralmmo.github.io/)

**LLM societies (contrast — imitation; out of scope for agents)**
- Smallville — [arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
- Project Sid — [arXiv:2411.00114](https://arxiv.org/abs/2411.00114)

**Drives / homeostasis**
- Keramati & Gutkin (2014). Homeostatic reinforcement learning.

**NVIDIA / engines**
- [NVIDIA Warp](https://github.com/NVIDIA/warp)
- [NVIDIA Newton](https://github.com/newton-physics/newton) (rigid playground later)
- [FLAME GPU 2](https://github.com/FLAMEGPU/FLAMEGPU2) (alt mass-agent ref)

---

## 11. Collaboration notes

- **gan** owns research framing / PlayScore formalization.
- Jason wants **SOTA engineering**, great visuals, **no AI slop**, private git with continuous commits.
- Lab Python: `C:\Users\user\Desktop\omnilab\.venv\Scripts\python.exe` (do not pip-install into it without asking Jason).
- GPU lease: follow omnilab `gpu-lease-run` before long GPU jobs when the GPU is shared.

---

## 12. Definition of done (any coding task)

1. Matches acceptance criteria in the task card.  
2. `python tests\run_tests.py` passes (or task-local test named in the card).  
3. H2 audit clean (no new play reward terms).  
4. Determinism preserved for NumPy backend when behavior should be unchanged.  
5. `NOTES.md` updated if results changed.  
6. Commit with pathspec; `git pull --rebase` before push; message conventional (`feat|fix|docs|test|perf|chore`).  
7. No secrets, no `_output/` blobs, no force-push to `master`.
