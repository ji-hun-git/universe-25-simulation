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
- Status note 2026-11-06 (P4-5): detectors frozen at rules v3 (12 / 12
  preregistered synthetic checks on fresh seeds, after v1 11 / 12 and a v2 falsifier failure);
  the P4-1 guard was rerun after an observation-builder confound was fixed (verdict unchanged).
  On the simulator, episodes last one decision for every policy, so criteria 3 / 4 — the H-f
  test — are not evaluable at 6 decisions per day; P4-8 (free-time sub-steps) is a
  prerequisite for H-f. No evaluation seed has been used for detector development.
- Status note 2026-11-06 (P4-8): free-time sub-steps added (`free_substeps`; off
  = bit-identical). Heuristic continue mode within 2 % of the control on every resolvable
  landmark but fails the 10 % rule on N@315 at one paired se — H-d amendment proposed in §15.1
  (pending). Learned arms will run at K = 12 against the random policy at the same K.
- Status note 2026-11-06 (P4-2): PPO learner with the preregistered seven-drive
  reward built and deterministic. It abandons its young (nursing mothers never nurse; 1.5 % pup
  survival), so the learned colony cannot reproduce the curve. The reward's drive list must be
  settled (maternal motivation) before any learned arm is judged; no learned arm has been
  evaluated on seeds 8000–8011.
- Amendment 2026-11-06 (Jason; before any learned arm was judged): the learner's reward has
  eight drives — the seven of `PHASE4_DESIGN.md` §1.4 plus `maternal_need`, a nursing female's
  motivation set by her own litter's hunger; entropy coefficient 0.05. P4-2 acceptance met
  (training seed 7000 nursery, 650 d: learner mean D 0.25 vs 1.04 untrained vs 0.82 heuristic,
  1.5 × 10^7 transitions, full-size colony, mothers nurse like the heuristic).
- Status note 2026-11-06 (P4-3): nursery pre-training (10^8 steps) built. A
  development guard on training seeds 7000–7002 (not the preregistered evaluation) shows the
  frozen learner keeping the canonical colony in the founders' four cells and plateauing near
  960 — the nurseries never contained a founding colony. No learned arm has been evaluated on
  seeds 8000–8011.
- Status note 2026-11-07 (nursery v2): with founding-colony worlds in the
  nursery the frozen learner spreads the canonical colony and reaches peak 2,406 / N@736 2,095 /
  conceptions ending 907, about 100 days early (training seeds 7000–7002). The preregistered
  H-d guard on seeds 8000–8011 is the next step.
- Status note 2026-11-07 (H-d): the preregistered guard on seeds 8000–8011 found
  the learned arm not preserved (see §15.1, "H-d result"); H-d is falsified for both the
  random and the learned policy.
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
| H-d | Policy invariance: the calibrated curve is a property of the biology, not of the heuristic policy | 12-seed canonical landmarks of `mlp_frozen`, `mlp_ppo`, `evo` within 10 % of `need_driven` or within 2 paired se of it; decline band met at 1200 | calibration guard (`PHASE4_DESIGN.md` §4) | any canonical landmark > 10 % off the control **and** > 2 paired se (amended 2026-11-06), or the decline band missed at day 1200 |
| H-e | Surplus-resource dependence by state (amended 2026-11-08): the learned policy's play-likeness rises with the share of animals in the relaxed field | per episode kind, the number of criteria met in a window (0–5, detector rules v5) rises with that window's relaxed share at matched phase | stratified permutation test (amendment below) | pooled within-stratum Kendall τ ≤ 0 for both kinds (τ > 0 without one-sided p < 0.025 = not supported) |
| H-f | Structure, not frequency: learned policies' object interactions differ from the heuristic's in sequence statistics (criteria 3 / 4), not only in rate | criterion 3 / 4 detectors differ from `need_driven` at matched free-choice V | time-shuffled and drive-shuffled surrogate bands | no difference beyond the surrogate band |
| H-g | Breakdown suppresses play-likeness: detector rates fall in phases C / D (stress, withdrawal) under every policy | monotone decline after the plateau | detectors by phase | rates rise in phase D |
| H-c (kept) | No play reward: any playground use is drive spillover unless criteria 3 / 4 show structure | code audit; H2 string audit over policy, observation and reward code | | any play-named term |

**Amendment to H-d — ADOPTED 2026-11-06 (Jason; proposed the same day, before
any learned arm was judged).**
The 10 % rule cannot resolve N@315 at 12 seeds: its paired se is 12–16 % of the mean, and the
heuristic with 12 sub-steps in continue mode — the control's distribution by construction —
failed it at one paired se (+13 %). Proposed: a canonical landmark fails only if its drift
exceeds 10 % **and** the paired difference exceeds 2 paired se (equivalence where resolvable);
the decline band unchanged. Effect on the arms run so far: continue mode would be preserved;
the random frozen MLP stays not preserved (peak −11.5 % at 10 paired se, peak day +238 d,
cessation +508 d); the re-choosing heuristic stays not preserved (decline band).
Re-verdict of the stored guard runs under the adopted rule (`_output/policy_guard_*.json`, both
readings kept as `verdict` and `verdict_10pct_rule`): random frozen MLP NOT PRESERVED (N@315
7.1 se, peak 10.7 se, peak day 8.0 se, cessation 5.4 se); heuristic K = 12 rechoose NOT
PRESERVED (decline band only; N@315 +17 % at 1.1 se now passes); heuristic K = 12 continue
PRESERVED (N@315 +13 % at 1.1 se). Every guard report prints both readings.

**H-d result (2026-11-07, seeds 8000–8011, 1,600 d): falsified.** Random frozen MLP: not
preserved (P4-1). Pre-trained drive-reduction learner (`pretrain_v2`, eight drives, 12
sub-steps): not preserved — N@315 +77 % (5.2 paired se), peak day −69 d (9.1 se), surviving
births cease −103 d (14.5 se), decline band 0.29 < 0.35 — while peak N (+4.9 %), N@736 (+6.8 %)
and conception cessation (−2.7 %) hold. The heuristic with 12 sub-steps (continue) is preserved.
The calibrated curve is biology plus behaviour; the learner runs the same arc about 70–100 days
early. H-e … H-g compare conditions within a policy and are unaffected (NOTES 2026-11-07).

**Manipulation check for H-e (2026-11-08): failed for every food-scarcity design tried.**
Food scarcity shrinks the colony until its survivors are fed; the smaller colony escapes the
crowding stress that dominates the relaxed field, so the scarce arm is *more* relaxed than the
abundant one in the later phases (day 900: 0.33–0.38 vs 0.13–0.16). H-e as written cannot test
surplus-resource theory in this world.

**Amendment to H-e — ADOPTED 2026-11-08 (Jason; proposed the same day, before
any evaluation-seed detector reading).** Original wording: object / locomotor detector rates
are higher under abundance than under scarcity for learned policies — criteria 1, 3, 4, 5
higher in ABUND-PG than SCARCE-PG at matched phase; falsified if equal or higher under
scarcity. Reason: the manipulation check above. The amended test, fixed before the sweep:

- *Arms.* Policy: the learned net (`mlp_frozen`, `_output/pretrain/pretrain_v2/policy_final.npz`;
  primary), `need_driven` (control), and a random frozen net of the same architecture
  (`MlpFrozenPolicy.random_init(7000)`, control) × food: ABUND-PG (`configs/default.yaml`) and
  SCARCE-PG (`configs/scarce.yaml`, carrying capacity 1,000 animals) × evaluation seeds
  8000–8011. 12 free-time sub-steps (sub-step mode `auto`), 1,010 days, traced windows
  [400, 410), [700, 710) and [1000, 1010) days, every fourth individual; detector rules v5,
  1,000 surrogates, at most 400 individuals per window, detector seed 0.
- *Unit.* One window of one run: 2 food arms × 12 seeds × 3 windows = 72 per policy.
- *Dose.* Relaxed share: the fraction of traced rows of weaned individuals (age ≥ 21 d) inside
  the detectors' relaxed field, in that window.
- *Response.* Per episode kind (object, locomotor): the criteria count C, the number of the five
  v5 decision flags met (a kind with fewer than 10 episodes scores 0, as the detectors flag it).
- *Statistic.* Kendall τ-b between dose and C within each stratum (policy × window, 24 units);
  T = the mean τ over the policy's three strata (a stratum where C or the dose is constant
  contributes 0). Null: dose permuted within strata, 10,000 permutations (seed 0); one-sided
  p = (1 + #{T* ≥ T}) / 10,001. Strata by window because the relaxed share also changes with
  phase (H-g): pooling windows would read phase as dose. Within a window the dose varies with
  the food regime and the seed.
- *Decision (learned net).* Per kind: supported if T > 0 and p < 0.025 (Bonferroni over the two
  kinds); not supported if T > 0 and p ≥ 0.025; falsified if T ≤ 0. H-e is supported if either
  kind is supported and falsified if both kinds are falsified.
- *Reported beside it, not decisive.* The same test for both control policies (a dose-response
  the heuristic and the random net show as well is free-time spillover, not something learned);
  each flag and its statistic against dose; episodes per weaned individual-decision against
  dose; Kendall τ between dose and episode count (z-based flags gain power with episodes, so a
  dose-response that only follows episode count is read as a power effect); and the food
  contrast ABUND-PG − SCARCE-PG in C, paired by seed and window, with the relaxed-share
  difference (the manipulation check) beside it.
- *Before the sweep.* Criterion 2 needs detector rules v5 (`PHASE4_DESIGN.md` §2, card P4-10).

**H-e result (2026-11-08, evaluation seeds 8000–8011, 216 window units): supported by the
preregistered rule.** Learned net: object T = +0.328 (p 0.0004), locomotor T = +0.229
(p 0.0002). Controls: heuristic falsified for both kinds; random net object T = +0.118
(p 0.0215, via criteria 1 and 4), locomotor constant. C varies only through criterion 5
(relaxed-field gating), so the finding is that onsets are more strongly gated by the relaxed
field in windows where more animals are relaxed. This is close to definitional, and it is not
evidence of play. Exploratory checks: the object part is robust (positive within food arms,
and to leave-one-out). The locomotor part rests on two crisis windows with 60 and 372 relaxed
rows; without them T = +0.098, p 0.043. Food contrast: scarcity made the learned colony more
relaxed (Δ dose −0.072) and its object onsets more gated (Δ C −0.33). NOTES 2026-11-08.

**Detector rules v6 (2026-11-09, card P4-11; not an amendment of any hypothesis).** Criteria 3
and 4 now need a form beyond chance (all preregistered checks pass). Re-read with v6 flags,
the H-e numbers for the learned net are unchanged; the random control's object reading falls
to not supported (p 0.047). Under v6 no policy meets criterion 3 or 4 in any window, so H-f as
written would compare zeros: no policy controls the path of a move (EXPLORE is a Gaussian
step, MANIPULATE a straight approach). H-f is untested pending a decision on the action space
or on measuring structure in action sequences. NOTES 2026-11-09.

**Action space v2 and a proposed H-f amendment (2026-11-09, card P4-12; PROPOSED, NOT
ADOPTED).** The heuristic cannot use the new movement primitives, so the comparison for H-f
moves to the random v3 net, which uses the same action space and has the same mechanical
baseline.

*Proposed H-f:* learned v3 object and locomotor episodes have more form than the random v3
net's at matched free-choice V.
- *Statistic:* per evaluation seed and window (the same days in both arms), the difference in
  v6 form excess, learned v3 minus random v3, in windows where both arms have at least 10
  reversal pairs. The form excess is a per-pair fraction against its own shuffle, so it does
  not scale with the event rate. Each arm's free-choice V is reported beside it.
- *Test:* sign-flip permutation over the 12 seeds (window means per seed), one-sided p < 0.025
  per kind.
- *Falsifier:* mean difference ≤ 0, or p ≥ 0.025, in both kinds.
- The absolute c3 / c4 flags are not used: under action space v2 the random net meets them in
  5 of 18 development windows.

*Development reading* (training seeds 7000–7002, NOTES 2026-11-09): the difference is about 0
for locomotion (+0.090 vs +0.090) and negative for objects (+0.008 vs +0.032). The learner
spreads its free time evenly over each family's primitives, as a form-blind reward predicts.
So the amended H-f is expected to be null. Jason may instead hold H-f until the substrate gives
form a consequence (objects or conspecifics that respond to how they are approached), or until
the form test's null includes the movement mechanics.

**Decision (Jason, 2026-11-09): H-f held; fix the substrate.** Card P4-13 (`PHASE4_DESIGN.md`
§1.9 and §2 v7):
- Balls respond to how they are approached.
- Object-family relief scales with the speed a contact gives a ball.
- Rules v7 replay an even mix of the family's moves as the form test's null.

A revised H-f amendment (learned v4 vs random v4, rules v7) goes to Jason after the
development reading, before any evaluation seed.

**P4-13 result (2026-11-09).**
- Rules v7 pass every preregistered check and are frozen.
- The v4 learner ignores the balls: free-time shares as v3, 3 % of object rows touch a ball.
  No window meets the form test in either arm.
- Ball physics moves the heuristic's curve: N@315 −50 %, peak day +159.
- The revised amendment would read about 0, so it is not proposed. H-f stays held.
- Open (Jason): whether to make the intrinsic drives consequence-based in every family, for
  example spatial novelty for locomotion. That reopens the frozen calibration. The alternative
  is to turn to H-g and the playground-off arm, which need no form. NOTES 2026-11-09.

**P4-14 and Tier 1 (2026-11-09).**
- Jason chose novelty-based curiosity, then a guard at g = 8 as a deviation.
- The v5 learner reads neither novelty nor mobility inputs. Free time stays at chance, and its
  colony grows too fast.
- Detector rules v9 are frozen. Criterion 5 now counts only rows where a free action was
  eligible.
- **H-e re-read under v9** (exploratory; the evaluation seeds were already read):
  - The learned net's object part stands: T +0.262, p 0.003.
  - Its locomotor part does not: T +0.079, p 0.13.
  - The continuous gating statistic rises with the relaxed share for every policy, the random
    net included. H-e's preregistered "supported" is now read as state-gating found in every
    policy, not as learned play.
- H-f stays held; the next lever is the learner's signal (review Tier 2). NOTES 2026-11-09.

**P4-15 and a program-level stop rule (preregistered 2026-11-10; `PHASE4_DESIGN.md` §4.2).**
- *Question:* does a learner whose training signal is changed condition its free time on object
  consequences?
- *Learner changes:* entropy annealed 0.05 → 0.005, advantages normalised per transition type,
  λ per unit of time.
- *Test:* A1 vs a random net on fresh seeds 9100–9111. Statistic: P(object action | near a
  ball) − P(object action | near a fixed object). Sign-flip test, floor 0.05, α 0.025.
- *Stop rule:* no further substrate change for PPO until a learner passes. If it fails, the
  programme moves to H-g, the playground-off arm and `evo`.
- *If it passes,* the amended H-f (form excess, A1 vs R) is read on the same traces.
- **Result (2026-11-11): fails.** A1 − R = +0.011 ± 0.008, p 0.10. The stop rule applies, and
  H-f is not read. Next (Jason): H-g / the playground-off arm, `evo`, or replica v2 first.
  NOTES 2026-11-11.
- **Replica v2 ran first (2026-11-11 to 2026-11-13) and ended** without meeting its validation
  standard (`docs/REPLICA_V2.md`; NOTES 2026-11-13). The frozen 2m colony stays the reference.
  Open next (Jason): H-g / the playground-off arm, or `evo`.
- **H-g and the playground-off arm (Jason chose them 2026-11-13; fixed the same day before any
  run; `PHASE4_DESIGN.md` §4.3).**
  - *Arms:* the heuristic, the learned `pretrain_v2` net and a random net × playground on / off ×
    fresh seeds 9877–9888; 1,600 d, 12 sub-steps.
  - *Phases* per run, from its own first-litter and peak days in the record's proportions.
  - *Response:* episodes per weaned individual-day, per kind, in 29 ten-day windows.
  - *Decision* (playground on, per policy × kind):
    - falsified if the rate rises through phase D (Kendall τ, sign-flip p < 0.0042);
    - supported if it is lower in C / D than in B and falls through D (both p < 0.025);
    - H-g needs every cell.
  - *Playground off:* object events must vanish and locomotor episodes persist. H-g's rule for
    locomotion and the colony's landmarks are reported beside.

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
