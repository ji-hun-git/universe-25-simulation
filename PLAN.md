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
