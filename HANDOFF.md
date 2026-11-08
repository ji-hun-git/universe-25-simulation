# HANDOFF — universe25-play

> **Audience:** collaborators.
> **Repo (private):** https://github.com/ji-hun-git/universe25-play  
> **Local path (lab PC):** `C:\Users\user\Projects\universe25-play`  
> **Owner:** Jason (ji-hun-git) · **Research partner:** gan  
> **Date:** 2026-11-04 (Asia/Seoul) · **Phase:** 1 complete; **phase 2 calibration frozen at 2m (canonical landmark error 0.06 at seed 7000, 0.03–0.10 held-out; 12-seed plateau within 3–4 % of Calhoun; early phase a third low; emergent, irreversible collapse — caveats in `NOTES.md` → "Phase 2m")**; Warp parity partial; phase 3 (visuals) not started; **phase 4 (learning agents + play detectors) designed, preregistered and scaffolded 2026-11-04** (`docs/PHASE4_DESIGN.md`, `PLAN.md` §15, `docs/TASKS.md` P4-0…P4-7; policy hook landed, no learning run yet)

Read this file first. Then read `PLAN.md`, `NOTES.md`, `docs/NVIDIA_STACK.md`, `docs/TASKS.md`; for agents, policies, learning or play metrics also `docs/PHASE4_DESIGN.md` and `docs/RESEARCH_DIGEST.md`. Follow `CONTRIBUTING.md` for day-to-day rules.

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

## 4. Current status (as of phase 2m, 2026-11-03)

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

### Phase 2k — conception brake in crowded cells (neutral), peak-day landmark, recalibration (2026-10-31)

- `conception_density_onset` / `conception_density_width`: a female's daily conception
  probability falls linearly from 1 at the onset local cell density to 0 at onset + width
  (behavioural sink: the sink cells breed less). Off at width 0, bit-identical to 2j. Probed as
  the requested conception-rate brake: it does not delay the plateau (the plateau timing is set by
  when the sink cells fill and maternal erosion starts, not by the conception rate) and costs
  1–2 % of N@736 — a documented neutral result, kept in the search space.
- `peak_day` is now the day of the 31-day running-mean maximum of N (Calhoun's 2200 at Day 560
  is a census maximum); the first-97 %-day used up to 2j marked the start of a ≈100-day plateau
  and sat ≈30 days early by construction (12 seeds: 524 ± 9 vs raw maximum 553 ± 12, smoothed
  555 ± 12). Reported alongside as `peak_day_97pct` / `peak_day_raw_max`; seed spread 0.072 in the
  loss weights; `tests/test_landmarks.py`. Peak-day numbers in the tables above are 97 %-days.
- Multi-seed CMA-ES rerun (112 trials, 60 min) with the brake in the search space: trial 93 beat
  the start on the three training seeds through N@315, but scored out of sample over 12 seeds it
  is worse on every plateau landmark (peak 2148 @ 595, cessation 639, N@736 1964; loss of the mean
  landmarks 0.024 vs 0.012) and its N@315 gain vanishes (496 vs 475). **Parameters unchanged from
  2i**; the 12-seed out-of-sample score is the adjudicator for candidates from now on.

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d):**

| Landmark | Calhoun | Phase 2h | Phase 2i | **Phase 2k** | held-out 8000–8002 |
|----------|--------:|---------:|---------:|-------------:|---:|
| First litters | 104 | 102 | 102 | **102** | 102–105 |
| N @ 315 | 620 | 531 | 528 | **528** | 286–569 |
| Peak N | 2200 | 2115 | 2234 | **2234** | 2231–2309 |
| Peak day (31-d mean max; 2h/2i: first ≥97 %) | 560 | 503 | 518 | **550** (518) | 498–651 |
| Surviving births cease | 600 | 551 | 583 | **583** | 556–717 |
| N @ 736 | 2056 | 1845 | 1949 | **1949** | 1953–2046 |
| Adults @ 315 | 150 | 163 | 163 | **163** | 88–206 |
| Conception cessation | ≈920 | 932 | 915 | **915** | 867–1054 |
| N @ 1200 / 1400 / 1600 | 2056@736, 122@1444, 27@1588 | 1426 / 273 / 0 | 1515 / 480 / 0 | **1515 / 480 / 0** | 1514–1649 @1200 |
| mean rel. error (5) | | 0.077 | 0.057 | **0.046** | 0.07–0.19 |

Phases: decline (662) → collapse (1300). **Resolution:** 24 ticks/day gives peak 2274 / 501, cessation 581, N@736 1922, conception cessation 905; 12 seeds, 800 d: peak 2269 ± 11 (6 tpd) vs 2281 ± 8 (24 tpd), peak day 555 ± 12 vs 546 ± 12, N@736 1990 ± 15 vs 1992 ± 13, cessation 602 ± 12 vs 604 ± 11.
Cell-density table, scan, landmark note and open gaps in `NOTES.md` → "Phase 2k".

### Phase 2l — per-individual lifespan, late collapse (2026-11-03)

- `max_age_sd_days`: each animal draws its lifespan at birth (normal around `max_age_days`,
  floor 0.3 × mean; SoA `lifespan`, NumPy + Warp `mortality_kernel`); the old-age hazard applies
  past the individual's lifespan. sd 0 = the old single cutoff, bit-identical. Calibrated by a
  1600-d scan on Calhoun's N@1444 = 122 and N@1588 = 27: **850 ± 100** (was 938 for all).
- Late landmarks `n_at_day_1444` / `n_at_day_1588` reported (NaN below that horizon, so 1200-d
  studies skip them; 12-seed spread 1.33 of the target → weight ≈ 0). The inferred decline band
  now applies to N at day 1200, not to the run's final N (a 1600-d run ending near extinction, as
  Calhoun's did, was penalised as collapsed too far). `tests/test_calib_loss.py`.
- **Rebound hazard found**: with shorter lifespans (780 ± 170, 800 ± 150) the old cohorts die
  while fertile, competent females from the sparse cells remain; density falls, nursing recovers
  and surviving births resume in 1–3 of 12 seeds (seed 7007: 1434 animals at day 1588). Calhoun's
  colony never recovered. 850 ± 100 shows no rebound in 12 seeds; the reversibility is an open
  model gap (NOTES "Phase 2l").

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d):**

| Landmark | Calhoun | Phase 2i/2k | **Phase 2l** | held-out 8000–8002 (1600 d) | 12 seeds, 1600 d |
|----------|--------:|---------:|-------------:|---:|---:|
| First litters | 104 | 102 | **102** | 102–103 | 102 ± 0 |
| N @ 315 | 620 | 528 | **502** | 405–643 | 409 ± 45 |
| Peak N | 2200 | 2234 | **2261** | 2255–2286 | 2294 ± 15 |
| Peak day (31-d mean max) | 560 | 550 | **525** | 522–542 | 547 ± 17 |
| Surviving births cease | 600 | 583 | **574** | 567–587 | 600 ± 20 |
| N @ 736 | 2056 | 1949 | **1962** | 1946–1972 | 1999 ± 16 |
| Conception cessation | ≈920 | 915 | **892** | 893–924 | 929 ± 26 |
| N @ 1200 | (0.35–0.85 × peak) | 1515 | **1127** | 1043–1144 | 1212 ± 46 |
| N @ 1444 | 122 | 223 | **120** | 113–140 | 193 ± 47 (median 131) |
| N @ 1588 | 27 | 0 (extinct 1578) | **7** | 4–9 | 24 ± 10 (median 8) |
| mean rel. error (canonical 5) | | 0.046 | **0.069** | 0.04–0.10 | |

Phases: decline (638) → collapse (1198). **Resolution:** 24 ticks/day gives peak 2293 / 561, cessation 594, N@736 1981, N@1444 189, N@1588 15; 12 seeds, 800 d: peak 2294 ± 15 (6 tpd) vs 2275 ± 8 (24 tpd), peak day 547 ± 17 vs 566 ± 14, N@736 1999 ± 16 vs 2018 ± 15.
The seed-7000 realisation differs from 2i/2k before any old-age death (the lifespan draws at birth shift the RNG stream): peak day 525 vs 550, N@315 502 vs 528; the 12-seed means hold (peak day 547 ± 17, N@736 1999 ± 16).
Scan, rebound table and open gaps in `NOTES.md` → "Phase 2l".

### Phase 2m — colony-wide developmental exposure: the collapse cannot rebound (2026-11-03)

- `imprint_breakdown_exposure`: young lose competence at `imprint_rate` × (local exposure +
  gain × the breakdown factor) — the weaned-density ramp that already drives the colony-wide
  stress boost — so a female raised in an uncrowded cell during phase C/D grows up withdrawn
  instead of breeding when space returns (Calhoun / Marsden: the late-born never reproduced even
  after transfer). NumPy + Warp `density_stress_kernel` (parity 1.9e-9, branch exercised); 0 = off,
  bit-identical. Gain 1.0 by scan (0.5–2 all stop the rebound).
- With the rebound gone the lifespan is re-chosen for the late tail: **780 ± 150** (2l: 850 ± 100,
  which held 1197 at day 1200 and a median of 9 at 1588). 12 seeds, 1600 d: surviving births cease
  608 ± 19 at every lifespan tried (2l at 780 ± 170: 689 ± 83 with three rebounding seeds).

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d):**

| Landmark | Calhoun | Phase 2l | **Phase 2m** | held-out 8000–8002 (1600 d) | 12 seeds, 1600 d |
|----------|--------:|---------:|-------------:|---:|---:|
| First litters | 104 | 102 | **102** | 102–103 | 102 ± 0 |
| N @ 315 | 620 | 502 | **502** | 405–643 | 409 ± 45 |
| Peak N | 2200 | 2261 | **2199** | 2247–2285 | 2265 ± 18 |
| Peak day (31-d mean max) | 560 | 525 | **528** | 508–540 | 550 ± 15 |
| Surviving births cease | 600 | 574 | **621** | 571–583 | 608 ± 19 |
| N @ 736 | 2056 | 1962 | **1955** | 1920–1942 | 1983 ± 20 |
| Conception cessation | ≈920 | 892 | **905** | 926–945 | 939 ± 21 |
| N @ 1200 | (0.35–0.85 × peak) | 1127 | **811** | 777–832 | 880 ± 48 |
| N @ 1444 | 122 | 120 | **108** | 109–111 | 155 ± 29 (median 119) |
| N @ 1588 | 27 | 7 | **10** | 14–16 | 31 ± 9 (median 20) |
| mean rel. error (canonical 5) | | 0.069 | **0.060** | 0.03–0.10 | |

Phases: decline (675) → collapse (1120). **Resolution:** 24 ticks/day gives peak 2317 / 543, cessation 601, N@736 1982, N@1444 158, N@1588 27; 12 seeds, 800 d: peak 2265 ± 18 (6 tpd) vs 2262 ± 15 (24 tpd), peak day 550 ± 15 vs 562 ± 13, N@736 1983 ± 20 vs 1987 ± 14.
Scan, 12-seed rebound table and open gaps in `NOTES.md` → "Phase 2m".

**Calibration frozen here.** The fit is a plausibility check, not mechanism validation (about
ten tuned parameters against ten landmarks from one colony); every CMA-ES study since 2g returned
the hand point or lost out of sample, so the method of record is hand scans + 12-seed
out-of-sample scoring; the early phase was de-weighted (0.10 of 12), not fixed; since 2k the
plateau moved by less than its seed se. Caveats in full in `NOTES.md` → "Phase 2m".

### Record review + phase 4 design and scaffold (2026-11-04)

- **Record** (`docs/RESEARCH_DIGEST.md` part A): first litters at 104 is contested (Calhoun
  1971: 50 d; his figures: 60–65 d; 104 cannot fit 620 at 315 with a 55-d doubling) — the
  simulator's third-low N@315 is consistent with phase B starting ≈ 40 d late (card P0-5, not
  applied: frozen); ≈ 150 mice were removed after day 1000, so 122 / 27 are post-removal and
  our 155 ± 29 at 1444 is inside the no-removal envelope; irreversibility is n = 1 (Kessler
  1966 and Hammock 1971 colonies recovered) — the 2m exposure is a model assumption.
  Reported-only record landmarks added (`RECORD_LANDMARKS`: 1871 @ 811, ≈ 1650 @ 960, 100 @
  1471, doubling 55 d / 145 d) with `landmark_notes` in every report; loss unchanged.
- **Code**: policy hook `agents/policy.py` + `policy.kind` (bit-identical, hash `966401ea…`);
  CUDA-graph capture tick no longer skipped (`wp.capture_launch` after capture); found and
  carded: V counts drinkers (six of eight hoppers inside the playground box), Warp path skips
  three host-only density-stress parts (P0-2), PlayScore F constant / D stand-in.
- **Phase 4**: `docs/PHASE4_DESIGN.md` (architecture, reward, learner, detectors, calibration
  guard, determinism, compute), `PLAN.md` §15 (H-d … H-g, arms, seeds 8000–8011, budget, stop
  rules), `docs/TASKS.md` P4-0 … P4-7. No learning run has been made.
- **P4-0 / P4-1 done (2026-11-04)**: observation builder + frozen-MLP policy kind; calibration
  guard. First guard run (12 evaluation seeds, 1600 d): the frozen calibration reproduces the
  record out of sample; a random policy does **not** preserve the curve (slower, lower, later,
  far more persistent colony) — the heuristic behaviour is load-bearing, H-d is falsified for
  an arbitrary policy and every policy arm must report the guard (`NOTES.md` 2026-11-04 → P4-1).
- **P4-5 done (2026-11-06)**: decision traces (`metrics/trace.py`, off = bit-identical),
  detectors (`metrics/detectors.py`, rules v3), synthetic ground truth, validation 12 / 12 on
  fresh seeds; a confound in the P4-0 observation builder (pre-move cell counts reached the
  biology under learned policies) was fixed and the P4-1 guard rerun (verdict unchanged).
  Simulator reading: no multi-decision structure at 6 decisions per day for any policy → P4-8.
- **P4-8 done (2026-11-06)**: free-time sub-steps (`free_substeps`, off = bit-identical); the
  heuristic continues its decision action across sub-steps (re-choosing moved the arc: recorded
  negative); detectors now measure criteria 3 / 4 with support. Baseline at K = 12: heuristic
  object use is stereotyped approach-and-stay, locomotion and the random policy are random
  walks, and no arm prefers the relaxed field. H-d rule flaw on N@315 found (PLAN §15.1).
- **P4-2 built (2026-11-06)**: drive-reduction reward + shared PPO (`policy.kind: mlp_ppo`),
  deterministic on the GPU. Finding: with the seven preregistered drives the learner lowers its
  drive below the random baseline (0.43 vs 1.04) but never nurses — pups starve (1.5 % survive),
  the colony stays at ~500. Resolved the same day: an eighth, maternal drive (adopted by Jason)
  plus entropy 0.05 — the learner then nurses like the heuristic and keeps a full colony with
  mean D 0.25 (P4-2 acceptance met). Next: nursery pre-training (P4-3), then the guard (H-d).
- **P4-3 done (2026-11-06)**: nursery harness and 10^8-step pre-training (33 min on the RTX
  5080). Development guard on training seeds: the learned colony grows faster than the
  heuristic's early (N@315 624, Calhoun 620) but stays in the founders' four cells (NEST 48 %)
  and plateaus near 960. Decision pending: founding-colony nurseries + re-pretrain
  (recommended), the preregistered guard now, or a stress drive amendment.
- **Nursery v2 (2026-11-07)**: founding-colony and concentrated worlds added; re-pretrained
  (10^8 steps). The frozen v2 policy spreads the canonical colony like the heuristic: peak
  2,406, N@736 2,095, conceptions end 907 (Calhoun 2,200 / 2,056 / ≈920), but about 100 days
  early (peak day 456, last surviving birth 483) because its mothers raise more young early.
  Next: the preregistered guard (seeds 8000–8011) with `_output/pretrain/pretrain_v2`.
- **H-d preregistered (2026-11-07)**: the learned arm is not preserved on seeds 8000–8011
  (N@315 +77 %, peak day −69 d, surviving births cease −103 d, decline band missed; peak N,
  N@736, conceptions hold). H-d is falsified: the curve is biology plus behaviour. The play
  hypotheses compare conditions within a policy and can run on the learned colony.
- **P4-9 + survival condition (2026-11-08)**: detector rules v4 pass 14 / 14 synthetic checks,
  but on simulator traces criterion 2 reads locked everywhere (self-caused cell entries count
  as triggers; v5 needed). Scarcity tools built; food scarcity makes the colony smaller and
  more relaxed, so abundance vs survival must be redefined for H-e (pending, PLAN §15.1).
- **H-e amended + rules v5 (2026-11-08)**: H-e is now a state-based dose-response (adopted).
  Detector rules v5 count only exogenous triggers for criterion 2 (16 / 16 synthetic checks).
  H-e harness: `scripts/sweep_he.py`, `scripts/analyse_he.py`.
- **H-e tested (2026-11-08)**: supported by the preregistered rule (learned net, object
  T +0.33, locomotor T +0.23; heuristic falsified; random net object also positive, via
  criteria 1/4). All of the variation in C comes from criterion 5, so the result is
  state-gating that scales with relaxed share, not play. Object robust; locomotor rests on two
  near-empty crisis windows (T +0.10, p 0.043 without them). NOTES 2026-11-08.
- **Detector rules v6 (2026-11-09)**: criteria 3 / 4 need a form beyond chance (order-shuffle
  test); 18 / 18 synthetic checks, simulator negative control 0 / 18 windows. No simulator
  policy, the learned net included, meets criterion 3 or 4 anywhere: EXPLORE is a Gaussian
  step and MANIPULATE a straight approach, so no policy controls movement form. H-f untested;
  next decision: richer action space (under the calibration guard) or action-sequence form.

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
│   ├── PHASE4_DESIGN.md    ← learning agents on the frozen biology: reward, learner, detectors, guard
│   ├── RESEARCH_DIGEST.md  ← the Calhoun record (re-read 2026-11-04), learning-agent and play literature
│   ├── NVIDIA_STACK.md
│   └── NSIGHT.md
├── scripts/
│   ├── calibrate.py
│   ├── calibrate_optuna.py
│   ├── seed_eval.py        ← out-of-sample scoring of a fragment over N seeds (adjudicator, 2k)
│   ├── policy_guard.py     ← H-d calibration guard: a policy kind vs the need-driven control on the same seeds
│   ├── nursery_smoke.py    ← learner vs no-update network vs heuristic in one nursery (P4-2)
│   ├── pretrain_nursery.py ← nursery pre-training with checkpoints and a manifest (P4-3)
│   ├── validate_detectors.py ← preregistered synthetic validation of the detectors (AUC / TPR / FPR)
│   ├── detect.py           ← run the detectors on a traced run (writes detectors_unvalidated.json)
│   ├── multiseed_peak.py   ← 12-seed plateau / 6-vs-24 ticks check (peak, peak day, N@736, cessation)
│   ├── benchmark_backends.py
│   ├── microbench_warp_post.py
│   └── probe_nvidia.py
├── src/universe25/
│   ├── __main__.py         ← CLI: --seed --out --config --days --backend --device --playground --max-agents
│   ├── config.py           ← pydantic: Geometry, Playground, Resource, Biology, Drive, Policy, SimConfig
│   ├── sim.py              ← Universe25Sim (need-driven tick; density stress; breeding; logging)
│   ├── rng.py
│   ├── agents/
│   │   ├── state.py        ← AgentSoA, ROLE_*, ACT_* (11 actions; no PLAY)
│   │   ├── policy.py       ← Policy protocol; NeedDrivenPolicy (bit-identical); MlpFrozenPolicy (NumPy, seeded stream)
│   │   ├── drives.py       ← drive documentation; maternal_need (the learner's eighth drive)
│   │   ├── observation.py  ← 48-float egocentric observation (OBS_NAMES; no lifespan / PlayScore field)
│   │   └── device.py       ← optional Warp mirror buffers
│   ├── learn/
│   │   ├── reward.py       ← homeostatic drive-reduction reward (the only training signal)
│   │   ├── ppo.py          ← shared actor-critic, PPO, per-transition-discount GAE, determinism
│   │   ├── policy_ppo.py   ← policy.kind mlp_ppo (transitions per slot, updates, .npz export)
│   │   └── nursery.py      ← randomised nursery worlds and the pre-training loop (P4-3)
│   ├── world/
│   │   └── geometry.py     ← World, Cell, Nest, PlayObject, build_world
│   ├── metrics/
│   │   ├── logger.py       ← parquet
│   │   ├── trace.py        ← per-agent decision traces in day windows (eval-only; off = bit-identical)
│   │   ├── detectors.py    ← Burghardt criterion detectors (rules v3; *_unvalidated; never read by policies)
│   │   ├── synthetic_traces.py ← scripted ground-truth classes for detector validation (no dataset)
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
- [x] Mean relative landmark error **≪ 1.0** → **0.060** at seed 7000, 0.03–0.10 held-out (phase 2m: first litters 102, peak 2199 @ 528, surviving births cease 621, N@736 1955, conceptions cease 905, N@1444 108; 2b was 0.14)
- [x] Collapse phase appears under abundant arm → decline from 675, N(1200) = 37 % of peak, 174 at 1400, 108 at 1444, 10 at 1588 (Calhoun 122 at ~1444, 27 at 1588); surviving births cease at 621, conceptions at 905 (2e–2m); no rebound in 12 seeds; documented misses: early phase 23–34 % low (N@315 409 ± 45 over 12 seeds vs 620, de-weighted to 0.10 of 12 in the loss), N@736 3–4 % low, N@1444 27 % high at the mean (two slow realisations; median 119), conceptions end ≈20 d late (939 ± 21) — see NOTES
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
trade-offs, not N@315 fits). Phase 2k (done): conception brake in crowded cells (neutral, off),
`peak_day` = day of the 31-day running-mean maximum (the 97 %-day marked the plateau start; 12
seeds 555 ± 12 vs Calhoun 560), multi-seed CMA-ES rerun — peak 2234 @ 550, surviving
births cease 583, N@736 1949 (12 seeds 1990 ± 15), conceptions cease 915; canonical
error 0.046 (held-out 0.07–0.19). Phase 2l (done): per-individual lifespan 850 ± 100 d — N@1444 120, N@1588 7 at seed 7000
(Calhoun 122 / 27; 12 seeds 193 ± 47 (median 131) / 24 ± 10 (median 8)); shorter lifespans let the colony
rebound in 1–3 of 12 seeds (the breakdown is reversible when density falls — open gap).
Phase 2m (done): colony-wide developmental exposure (`imprint_breakdown_exposure` 1.0: young lose
competence wherever they are once the colony is in breakdown) ends the rebound — no seed of 12 resumes
surviving births — and lets the lifespan be 780 ± 150: N@1444 155 ± 29 (median 119), N@1588
31 ± 9 (median 20) (Calhoun 122 / 27) with the plateau unchanged. **Calibration is frozen at the 2m point** (`configs/default.yaml` =
`configs/calibrated_calhoun.yaml`): since 2k each phase has moved the plateau landmarks by less
than their seed se, and on the order of ten tuned biology parameters against ten landmarks from
one colony is a plausibility fit, not evidence for the mechanisms (caveats in `NOTES.md` →
"Phase 2m"). Reopen only if a phase 3 / 4 experiment needs a landmark the substrate cannot
show; the open misses, in priority order, are the early phase (N@315 409 ± 45 over 12 seeds vs
620 — seed-dominated and de-weighted, so the optimizer no longer sees it), the doomed-pup stock
in the peak count (N@736 3–4 % low) and the slow realisations' late tail (N@1444 155 ± 29 vs
122, median 119). Engineering candidates: vectorize
`_passive_nurse` / per-agent loops (`docs/TASKS.md` P1-3); Warp mortality-kernel parity at hazard level.

### Phase 3 — Visuals + dashboard
**Accept when:**
- Top-down 16-cell pen viewer (mice as role-colored dots; stress trail / hopper heatmap)
- Editorial dashboard (population + phases shaded; conception; wounds; nest occupancy; % withdrawn; V and G)
- Look: paper `#F4F0E6`, ink `#1A1A1A`, stress `#8B1E1E`, nest teal `#2F5D50`; IBM Plex / Source Serif; **uPlot** charts; **no purple glows, glassmorphism, or AI-slop chrome**
- shadcn/ui restyled to that palette (not default violet)

### Phase 4 — Learning agents + play detectors (design + scaffold done 2026-11-04; `docs/PHASE4_DESIGN.md`, `PLAN.md` §15)
**Accept when:**
- [x] Policy hook: `agents/policy.py`, `policy.kind`, need-driven default bit-identical (hash `966401ea…`), H2 audit on the policy module
- [x] Preregistration: H-d (policy invariance of the curve, 10 %), H-e / H-f / H-g, arms, seeds 8000–8011 reserved, budget, stop rules (`PLAN.md` §15)
- [x] Observation builder + `mlp_frozen` (P4-0, 2026-11-04: 48-float obs, NumPy MLP, seeded policy stream, CLI `--policy`; builder 1.8 ms per 4,000 agents; need-driven hash unchanged)
- [x] Calibration guard (P4-1, 2026-11-04: `calib/policy_guard.py`, `scripts/policy_guard.py`; first run on seeds 8000–8011 at 1600 d — the control reproduces the record (peak 2252 ± 13 @ 534 ± 7, N@1444 127 ± 8, N@1588 19 ± 2), a random frozen MLP is **not preserved**: N@315 −61 %, peak −11 % and +240 d, surviving births +560 d, late tail 5–20×; the curve is not policy-invariant, see NOTES)
- [x] Homeostatic reward + PPO (P4-2, 2026-11-06: bit-identical on the GPU; the seven-drive learner abandoned its young, so the reward gained an eighth drive, `maternal_need` (adopted by Jason), and entropy 0.05; 650-day nursery: learner mean D 0.25 vs 1.04 untrained vs 0.82 heuristic, 1.5 × 10^7 transitions, full-size colony)
- [x] Nursery pre-training (P4-3, 2026-11-06: harness + 10^8-step pre-training; the frozen policy on the canonical start crowds the colony into the founders' four cells and plateaus near 960 — no nursery episode showed a founding colony; next step pending)
- [ ] `evo` (P4-4)
- [x] Burghardt detectors per criterion with synthetic ground truth, ≥ 1,000 surrogates, thresholds fixed before any evaluation seed; V hopper fix (P4-5, 2026-11-06: rules v3 pass 12 / 12 preregistered checks on fresh seeds after v1 (11 / 12) and a falsifier failure in v2, all recorded; on the simulator both policies are non-functional and spontaneous but single-decision, so criteria 3 / 4 are not evaluable at 6 decisions per day) — **PlayScore eval-only, unvalidated**
- [x] Finer decision grain for free-time behaviour (P4-8, 2026-11-06: `free_substeps`, `policy.substep_mode`; heuristic continue mode within 2 % of the control on every resolvable landmark, N@315 +13 % at one paired se; detectors have support; no arm meets all five criteria)
- [x] H-d amendment adopted 2026-11-06 (drift > 10 % and > 2 paired se; heuristic with 12 sub-steps in continue mode preserved, random MLP not)
- [ ] Detector rules v4 (P4-9: phase-preserving trigger null, template minimum support)
- [ ] Sweep: policy kind × abundance / scarcity × playground on / off × 12 seeds (P4-6); H-d … H-g answered or marked untested in NOTES
- [ ] H2 audit extended to observation, learner and detector code with a negative test (P4-7); no ICM / RND bonus; the heuristic is never distilled

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
