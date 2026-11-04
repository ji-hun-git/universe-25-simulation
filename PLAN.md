# PLAN: universe25-play

- version: 2026-10-30
- Status: draft (phase-1 environment; freeze before learning-agent runs)
- Status note 2026-10-30 (phase 2b): H-a prediction met on magnitude (peak 2261,
  N@736 2106, decline to 58 % of peak by day 1200, 93 mice at 1600) with no scheduled collapse;
  timing partially met (peak day 467 vs 560; last *surviving* birth 813 vs 600 — mechanism gap
  recorded in NOTES.md). The phase-2 calibration before this was invalid (pup-mill bug). Schema
  additions since phase 1: SoA `competence`, biology `imprint_*`, `withdrawn_competence_threshold`,
  `female_fertile_max_age_days`, `wound_heal_per_day`; metrics `last_surviving_young_day`,
  `last_conception_day`, `n_adult`, `mean_competence_adult`. Environment is NOT yet frozen.
- Status note 2026-10-30 (phase 2e): timing now met on the cessation of surviving
  births (549–656 across four seeds vs 600) with conceptions continuing afterwards (to ≈1110–1190,
  Calhoun ≈920 — the remaining miss); peak 2231–2344 at 473–555, N@736 2049–2146, first litters
  104. Schema additions: SoA `maternal_cap`; biology `nurse_rate_per_day`, `nurse_max_pups`,
  `maternal_erosion_*`, `breakdown_density_threshold`, `breakdown_density_counts`,
  `starvation_hazard_per_day`; metrics `surv_births_cum`, `mean_maternal_cap_adult_f`; run.json
  `surviving_birth_cessation_day`. The tick loop holds decisions for 1/6 day at finer resolutions.
- Status note 2026-10-30 (phase 2f): stress relaxation exact, nest kick / social
  withdrawal per-decision; recalibrated — canonical error 0.103 (seed 7000), 0.11–0.17 held-out;
  6 vs 24 ticks/day agree within 5 % (12 seeds, 400 d) and over the full 1600-d arc. Misses:
  last conception 1063–1196 vs ≈920, peak 2457–2602 vs 2200.
- Status note 2026-10-31 (phase 2g): male courtship breakdown (`courtship_cap`,
  `courtship_erosion_*`) ends conceptions at 930 (held-out 885–1059) vs ≈920; the
  conception landmark is rate-based like surviving births. Canonical error 0.100. Remaining:
  peak 2482 vs 2200, steep late collapse.
- Status note 2026-10-31 (phase 2h): the social-breakdown stress boost ramps with
  weaned density (`breakdown_density_ramp`) instead of switching on; recalibrated — peak
  2115 @ 503 (held-out 2127–2328), N@736 1845, canonical error 0.077
  (0.10–0.13 held-out). Remaining: peak day ≈85 d early, N@736 9 % low, steep late collapse.
- Status note 2026-10-31 (phase 2i): density-graded nursing disturbance brakes
  phase C (`nurse_disturb_*`), breakdown ramp narrowed, CMA-ES objective is the mean over three
  training seeds — peak 2234 @ 518 (12 seeds 2269 ± 11 @ 524 ± 9), surviving births cease
  583, N@736 1949, canonical error 0.057 (0.08–0.17 held-out). Fertility tied to
  maternal capacity tested and rejected. Remaining: peak day ≈35 d early, N@736 3 % low, steep late collapse; loss weights for
  the multi-seed objective.
- Status note 2026-10-31 (phase 2j): landmark loss weights ∝ inverse seed variance
  (12-seed spread at 1200 d; N@315 / adults@315 get ≈0.1 / 0.04 of 12, plateau landmarks 1.0–2.7);
  the multi-seed CMA-ES rerun kept the 2i parameters. Remaining: peak day ≈35 d early, N@736 3 %
  low, steep late collapse (unchanged from 2i).
- Status note 2026-10-31 (phase 2k): conception brake in crowded cells tested
  (neutral: the plateau timing is set by when the sink cells fill, not by the conception rate; off);
  `peak_day` = day of the 31-day running-mean maximum (the 97 %-day marked the plateau start) —
  12 seeds 555 ± 12 vs Calhoun 560; multi-seed CMA-ES rerun — peak 2234 @ 550, surviving births
  cease 583, N@736 1949, canonical error 0.046 (0.07–0.19 held-out). Remaining: early phase low (N@315 475 ± 49 vs 620), N@736 3 % low, steep
  late collapse.
- Status note 2026-11-03 (phase 2l): per-individual lifespan (`max_age_sd_days`;
  850 ± 100 d) replaces the single old-age cutoff — N@1444 120, N@1588 7 at seed 7000, 12 seeds
  193 ± 47 (median 131) / 24 ± 10 (median 8) (Calhoun 122 / 27), no extinction before 1600. Shorter lifespans
  let the colony rebound in 1–3 of 12 seeds: the breakdown is reversible when density falls (Calhoun's
  was not) — open gap. Remaining: early phase low, N@736 3 % low, late tail thin at
  the median, reversibility of the breakdown.
- Status note 2026-11-03 (phase 2m): colony-wide developmental exposure
  (`imprint_breakdown_exposure` 1.0; young lose competence wherever they are once the colony is in
  breakdown) makes the collapse irreversible — no seed of 12 resumes surviving births — and the
  lifespan is re-chosen at 780 ± 150: N@1444 155 ± 29 (median 119), N@1588 31 ± 9 (median 20)
  (Calhoun 122 / 27), plateau unchanged. Remaining: N@315 409 ± 45 vs 620 (seed-dominated,
  de-weighted); N@736 3–4 % low; N@1444 155 ± 29 vs 122 at the mean (median 119). Calibration
  frozen at this point: the H-a bar (peak within 30 % of 2200 near day 560, collapse after ~600)
  is met with margin, later phases moved landmarks inside the seed se, and a fit of about ten
  parameters to one colony's ten landmarks is a plausibility check, not mechanism validation.
- Status note 2026-11-04 (record review + phase 4 scaffold): the first-litter
  target (104) is contested by Calhoun 1971 (50 d) and his figures (60–65 d) and cannot fit 620
  at 315 with a 55-d doubling — the N@315 miss is consistent with phase B starting ≈ 40 d late
  (`docs/TASKS.md` P0-5, not applied: frozen); 122 / 27 are post-removal counts (≈ 150 removed
  after day 1000); irreversibility is n = 1 (Kessler 1966 colonies recovered) — a model
  assumption. Reported-only record landmarks added; loss unchanged. Policy hook landed
  (bit-identical); phase 4 preregistered in §15; no learning run yet. P4-0 / P4-1 done the same
  day: the first guard run (seeds 8000–8011, 1600 d) shows the control reproducing the record
  out of sample and a random frozen MLP **not** preserving the curve (N@315 −61 %, peak −11 %
  / +240 d, cessation +560 d, late tail 5–20×) — H-d falsified for an arbitrary policy; the
  heuristic behaviour is load-bearing.
- Work package: WP-G12-adjacent / Track E toy world (Universe 25 + playground); not L3 ecology
- Track: **E** (emergent, exploratory)
- Owner: Jason
- Pinned L3 commit: none (does not import L3)

## 1. Question
Can a Calhoun-calibrated need-driven mouse society, given an optional playground with manipulable objects and **no play reward**, produce a population curve matching Death Squared landmarks and a measurable free-choice playground preference under abundance?

## 2. Why it matters
Phase-1 substrate for the play-emergence claim (Burghardt 5 criteria; gan PlayScore provisional). Closest ancestor Auerbach, Kanarek & Burghardt 2015; contrasts Leibo Gathering (aggression under scarcity) and Calhoun behavioral sink. Enables later play-module without contaminating the environment with play terms (H2).

## 3. Hypotheses and predictions

| ID | Hypothesis | Prediction | Measured by | Falsified if |
|---|---|---|---|---|
| H-a | Need-driven agents under Calhoun geometry + unlimited food reproduce the four phases | Peak N within 30% of ~2200 near day 560; collapse after last young ~600 | calibration RMSE vs landmarks | Peak outside [1500, 3000] or no decline by day 1200 |
| H-b | Playground occupancy rises when mean energy high and stress low (relaxed field) | V (free-choice preference) higher in abundance+playground ON vs scarcity or playground OFF | V, G gate | V higher under scarcity than abundance |
| H-c | No play reward → any playground use is drive spillover (curiosity/boredom/homeostasis), not optimized play | Agents never receive a play term; PlayScore components logged as unvalidated | code audit + metrics schema | any reward/utility term named play |

## 4. Arms

| Arm | Label | What | Expected fail | Seeds |
|---|---|---|---|---|
| U25-ABUND-PG | TRACK-E-U25-ABUND-PG | Calhoun pen, unlimited resources, playground ON | n/a (exploratory env) | 7000 |
| U25-ABUND-NOPG | TRACK-E-U25-ABUND-NOPG | same, playground OFF | n/a | 7001 |
| U25-SCARCE-PG | TRACK-E-U25-SCARCE-PG | scarce food (later phase) | n/a | 7002 |

Phase 1 delivers ABUND-PG smoke + long run. Scarcity arm deferred.

## 5. Seeds
- Training/build: 7000–7009
- Eval worlds: 8000–8009 (later)
- Confirmed by PI (BOARD D1, 2026-10-20)
- Unit tests: 7100
- Every command passes `--seed`

## 6. Budget

| Resource | Planned | Stop at |
|---|---|---|
| CPU wall-clock | 1 h smoke + tests | 2 h |
| Peak RAM | < 4 GB | 8 GB |
| GPU minutes | 30 (smoke + ~1600-day run) | 60 |
| Disk | < 2 GB parquet/snapshots | 5 GB |
| API spend | 0 | 0 |

## 7. Metrics
- Primary: population curve vs Calhoun landmarks (calibration script)
- Secondary: role counts, playground occupancy, free-choice V, action entropy, provisional PlayScore parts F,V,D,S,G (**unvalidated**, gan formalization)
- Output: `_output/<run>/metrics.parquet`, `calibration.json`, `run.json`, snapshots/

## 8. Stop rules
- Success: smoke deterministic; long run completes; calibration report written
- Futility: Warp CUDA fails and torch fallback also fails
- Safety: NaN; GPU busy without lease; write outside the project folder; H2 play-reward appears

## 9. Negative result
Population never peaks above 500, or never collapses, or playground preference is higher under scarcity — all reported honestly in NOTES.md.

## 10. Analysis plan
Unit: one seeded run. Report landmark errors, phase detection (adj/growth/stag/collapse), wall time, peak VRAM. No confirmatory stats in phase 1.

## 11. H1–H4 checklist
- [x] H1: no animal/human play data; synthetic agents only
- [x] H2: no play reward/observation/goal; playground is geometry + objects only; curiosity/boredom/homeostasis are generic drives
- [x] H3: no LLM in agents
- [x] H4: exploratory; does not change L3
- [x] No peeking at L3 drive-arm telemetry

## 12. Deliverables (phase 1)
- Sim core: Warp SoA (+ torch CUDA fallback), pydantic YAML config, fixed timestep, seeded RNG
- Calhoun geometry + configurable playground
- Need-driven agents with density-stress mechanisms
- Metrics logger + calibration script
- pytest-style `__main__` tests (shared venv has no pytest): geometry, determinism, conservation
- README + references
- Headless smoke + ~1600-day abundant run

## 13. Non-goals (phase 1)
- Visual dashboard (phase 2)
- RL / learning agents
- Validated PlayScore
- LLM narrator mice

## 14. Freeze
Environment schema frozen after first successful long run + NOTES entry; learning arms require a new PLAN.

## 15. Phase 4 plan — learning arms (v2026-11-04; the "new PLAN" that §14 requires)

- Status: preregistered design, **no runs yet**. Design: `docs/PHASE4_DESIGN.md`. Sources:
  `docs/RESEARCH_DIGEST.md`. Scaffold landed 2026-11-04: `agents/policy.py` (policy hook,
  bit-identical with `policy.kind: need_driven`).
- Question: does play-like behaviour (Burghardt's five criteria, eval-only detectors) emerge more
  under abundance than under survival in agents that **learn** a homeostatic drive-reduction
  policy with **no play reward**, on the frozen Calhoun-calibrated biology — and does the Calhoun
  population curve survive a learned policy at all?

### 15.1 Hypotheses

| ID | Hypothesis | Prediction | Measured by | Falsified if |
|---|---|---|---|---|
| H-d | Policy invariance: the calibrated curve is a property of the biology, not of the heuristic policy | 12-seed canonical landmarks of `mlp_frozen`, `mlp_ppo`, `evo` within 10 % of `need_driven`; decline band met at 1200 | calibration guard (`PHASE4_DESIGN.md` §4) | any canonical landmark > 10 % off the control, or no decline by day 1200 |
| H-e | Relaxed-field dependence: object / locomotor detector rates are higher under abundance than under scarcity for learned policies | criterion 1, 3, 4, 5 detector rates higher in ABUND-PG than SCARCE-PG at matched phase | per-criterion detectors (`PHASE4_DESIGN.md` §2) with surrogate controls | rates equal or higher under scarcity |
| H-f | Structure, not frequency: learned policies' object interactions differ from the heuristic's in sequence statistics (criteria 3 / 4), not only in rate | criterion 3 / 4 detectors differ from `need_driven` at matched free-choice V | time-shuffled and drive-shuffled surrogate bands | no difference beyond the surrogate band |
| H-g | Breakdown suppresses play-likeness: detector rates fall in phases C / D (stress, withdrawal) under every policy | monotone decline after the plateau | detectors by phase | rates rise in phase D |
| H-c (kept) | No play reward: any playground use is drive spillover unless criteria 3 / 4 show structure | code audit; H2 string audit over policy, observation and reward code | | any play-named term |

### 15.2 Arms

Policy kind × resources × playground: `need_driven` (control), `mlp_frozen`, `mlp_ppo`, `evo`;
each in ABUND-PG, ABUND-NOPG, SCARCE-PG (arms of §4). The heuristic is a control, never a teacher
(no distillation, no behaviour cloning).

### 15.3 Seeds

- Nursery pre-training and tuning: 7000–7009 only.
- Canonical evaluation: **8000–8011** (12 seeds), never used for pre-training, tuning or detector
  threshold choice. Arms are compared only on these.
- Unit tests: 7100.

### 15.4 Budget

| Resource | Planned | Stop at |
|---|---|---|
| Nursery pre-training | 10^9 agent-steps per policy kind (≤ 2 GPU-hours each) | 4 GPU-hours each |
| Canonical runs | 12 seeds × 3 resource arms × 4 kinds × 1600 d at 24 ticks/day ≈ 144 runs ≈ 8 h | 16 h |
| Peak RAM / VRAM | < 8 GB / < 8 GB | 16 GB / 14 GB |
| Disk | < 10 GB parquet + weights | 20 GB |
| API spend | 0 | 0 |

### 15.5 Stop rules

- Success: H-d evaluated on 12 seeds for at least `mlp_frozen` and `evo`; detectors validated on
  synthetic ground truth with the controls of `PHASE4_DESIGN.md` §2; H-e and H-f tested.
- Futility: no policy kind beats the random-policy drive baseline after 10^9 nursery agent-steps
  (reported as a negative result, not retried with a play term).
- Safety: NaN; an H2 term appears; PlayScore used in any loss, reward or stopping criterion; any
  training on animal or human play data.

### 15.6 Analysis plan

Unit = one seeded run. Per arm: mean ± se over the 12 evaluation seeds. H-e and H-f: paired
differences across seeds against surrogate bands (time-shuffled action sequences within agent;
drive-shuffled relaxed-field gate). Effect sizes reported. The detector set and thresholds are
fixed in `docs/PHASE4_DESIGN.md` §2 **before** the first evaluation run; no detector is added or
re-thresholded after seeing evaluation seeds. Negative results go to `NOTES.md`.

### 15.7 Non-goals and freeze

- Non-goals: a validated PlayScore (it stays `_unvalidated` unless the preregistered synthetic
  validation passes); LLM narrators; visuals (phase 3, in parallel).
- Freeze: biology frozen at phase 2m. The observation vector, the reward and the detector set
  freeze when P4-0 and P4-5 land with tests; any later change is a new version of this section.
