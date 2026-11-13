# TASKS.md — prioritized task list

Each card gives the goal, the files, the acceptance criteria and the task.  
Before starting a card, read `HANDOFF.md`, `PLAN.md`, `NOTES.md` and the card. Obey H2 (no play reward).

Legend: **P0** blocking · **P1** high · **P2** medium · **P3** polish

---

## P0-1 — Biology calibration toward Calhoun landmarks

> **Status 2026-10-30:** pup-mill bug fixed, developmental-imprinting collapse
> mechanism added (2b), daily-only conception + nest-box nursing + litter abandonment (2d),
> post-weaning maternal breakdown + weaned-density breakdown switch + relaxation nursing + lethal
> starvation (2e), exact stress relaxation (2f), male courtship breakdown (2g), graded breakdown
> pressure (2h), nursing-disturbance brake + multi-seed objective (2i), inverse-seed-variance loss
> weights (2j), crowded-cell conception brake (neutral) + smoothed peak-day landmark (2k),
> per-individual lifespan (2l), colony-wide developmental exposure + lifespan 780 ± 150 (2m, no
> rebound in 12 seeds): canonical mean rel. error **0.060** (seed 7000; 0.03–0.10 held-out),
> peak 2199–2285 @ 508–540, surviving births cease 571–621, conceptions
> 905–945, N@736 1920–1955, N@1444 108–111, N@1588 10–16 across four
> seeds (Calhoun 2200 @ 560, 600, ≈920, 2056, 122, 27); 12 seeds (1600 d): N@1444 155 ± 29 (median 119),
> N@1588 31 ± 9 (median 20).
> See `NOTES.md` "Phase 2m" and earlier. Still off: N@315 23–34 % low and seed-dominated (de-weighted to 0.10 of 12 in the loss);
> N@736 3–4 % low; N@1444 27 % high at the mean (two slow realisations; median 119); conceptions
> end ≈20 d late. **Calibration frozen at 2m** — reopen only if phase 3 / 4 needs it (caveats in
> `NOTES.md` → "Phase 2m"). **2026-11-04:** the record review found the first-litter target
> (104) contested — Calhoun 1971 says 50 d, his figures 60–65 — which would explain the N@315
> miss; see P0-5. 122 / 27 are post-removal counts (≈ 150 mice removed after day 1000).

**Goal:** Reduce mean relative landmark error from ~1.08; get first litters nearer day 104, N@315 nearer 620, peak nearer day 560, and either a collapse or an honest negative with mechanism notes.

**Files:** `configs/default.yaml`, `src/universe25/sim.py`, `src/universe25/config.py`, `src/universe25/calib/*`, `scripts/calibrate_optuna.py`, `NOTES.md`

**Acceptance criteria:**
- Documented parameter change set + seed 7000 1600d (or agreed shorter calib protocol) comparison table in `NOTES.md`
- mean_rel_error improved vs 1.08 **or** clear ablation showing which landmark is infeasible under current mechanisms
- No NaNs; tests still pass
- No play reward terms introduced

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python tests\run_tests.py
python scripts\calibrate.py --metrics _output\<run>\metrics.parquet --out _output\<run>\calibration.json --run-json _output\<run>\run.json
```

**Task:**
```
Read HANDOFF.md + NOTES.md. Phase-1 1600d abundant run peaked at N≈1715 on day~1395 (mean_rel_error≈1.08) with NO collapse. Tune biology/density-stress/mortality/breeding so landmarks move toward Calhoun 1973 (first litters~104, N@315~620, peak~2200@~560, collapse after). Use calib helpers if useful. Keep H2. Write honest before/after table to NOTES.md. Pathspec commits only.
```

---

## P0-2 — Warp ↔ NumPy parity for tick kernels

> **Status 2026-10-30:** `tests/test_biology_guards.py::test_warp_density_stress_parity` covers the
> density-stress + imprinting kernel (max |Δ| ≈ 3e-8). Still open: mortality (different RNG streams —
> compare hazards, not draws) and `update_cells`.
> **2026-11-04:** the CUDA-graph capture tick skipped its launches (fixed: `wp.capture_launch`
> after capture). Still missing on the Warp path, so it is not the calibrated model: homeless
> nest adoption, the random nest kick and the young-female maternal cap (`sim._density_stress`
> host-only parts); `update_drives_kernel` and `engine.download` are unused; add them or document.

**Goal:** Device Warp path matches NumPy reference on a fixed seed for stress/mortality/cells (and any kernels you own), within agreed float tolerance.

**Files:** `src/universe25/warp_kernels/*`, `src/universe25/sim.py`, `tests/test_warp_smoke.py` (add parity test), `docs/NSIGHT.md`

**Acceptance criteria:**
- Automated parity test seed 7100 (or 7000 short run)
- Document sync vs graph behavior; no silent fallback without logging
- `tests/run_tests.py` green

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python tests\run_tests.py
python main.py --seed 7000 --out _output\warp_parity --backend warp --device cuda --days 5 --max-agents 1024
```

**Task:**
```
Read HANDOFF.md and docs/NVIDIA_STACK.md. Add/extend Warp kernel parity tests vs NumPy host for the post-step (and any tick pieces already on device). RTX 5080 sm_120. Fail loud on mismatch. Update NOTES with parity method. No play reward. Pathspec commits.
```

---

## P0-4 — dt-invariance: action persistence + per-day event effects

> **Status 2026-10-30: DONE** — decisions are held for the reference interval
> (1/6 day); per-decision events (meal, drink, move, fight, relief, walk step) happen in full on
> the decision tick and only continuous physics integrates on the held ticks; relaxation-form
> nursing; exact 1−exp(−h·dt) death draws (phase 2e). The 2d residual (+20–25 % early growth at
> 24 tpd) was not nursing clipping but single-tick meals and travel (mothers away from the nest
> ¼ of the time at 24 tpd); spreading events over held ticks (×k) left an interleaving bias that
> lethal starvation amplified to +60 %. Phase 2f made the stress relaxation exact and the nest
> kick / social withdrawal per-decision events: 6 vs 24 ticks/day now agree within 5 % on N and
> births by day 400 (12 seeds) and over the whole 1600-d arc at seed 7000. See `NOTES.md`
> "Phase 2f" for the tables.

**Goal:** The calibrated biology must give the same trajectory at 6 and 24 ticks/day. Before 2c the
same parameters gave peak 2261 (6 tpd) vs 1088 (24 tpd) — see `NOTES.md` Phase 2b/2c.

**Files:** `src/universe25/sim.py` (`_select_actions`, `_execute_actions`, `_passive_nurse`,
`_nurse`, `_aggress`, `_density_stress`), `configs/default.yaml`, `NOTES.md`

**Acceptance criteria:**
- Agents commit to a movement target (nest / hopper / object) until arrival instead of re-drawing
  every tick, or movement completes within one decision regardless of `ticks_per_day`
- Per-event effects (nurse amounts, wound +0.15, ACT_NEST −0.05 stress, social −0.05) scaled so
  daily totals do not depend on `ticks_per_day`
- 1600-d seed-7000 landmarks at 24 tpd within ~10 % of the 6-tpd run (re-calibrate if needed with
  `scripts/calibrate_optuna.py --workers 14`)
- Determinism test still green; H2 clean

**Task:**
```
Read HANDOFF.md + NOTES.md "Phase 2b" (dt-invariance gap). Make the Universe25 tick dt-invariant:
action/target persistence and per-day scaling of per-event effects. Compare 6 vs 24 ticks/day on
seed 7000 for 1600 d, table in NOTES. Re-run CMA-ES from configs/calibrated_calhoun.yaml if the
landmarks move. No play reward. Pathspec commits.
```

---

## P0-3 — Keep master green while dual-editing

**Goal:** Ensure concurrent phase-2 work does not break determinism/conservation.

**Files:** `tests/*` only if needed; otherwise verify only

**Acceptance criteria:** `python tests\run_tests.py` exit 0 on clean tree after rebase

**Task:**
```
Pull --rebase origin master on universe25-play. Run tests\run_tests.py. If failures, fix minimal regressions without redesign. Report commit HEAD and test output.
```

---

## P0-5 — Re-anchor phase A (first litters 60 ± 15) + optional removal event (calibration version 2n)

> **Status 2026-11-04:** not started. The record review (`docs/RESEARCH_DIGEST.md`
> part A) found that Calhoun 1973's "first litters at 104" is contradicted by Calhoun 1971 (first
> surviving litters at 50 d) and by both of his figures (60–65 d), and cannot fit 620 at 315 with
> a 55-d doubling. The simulator reaches 102 and sits a third low at 315 (409 ± 45 vs 620): phase
> B starts ≈ 40 d late. Also: ≈ 150 mice were removed after day 1000, so 122 / 27 are post-removal.

**Goal:** a new calibration version (2n) that (a) targets first litters at 60 ± 15 instead of 104
(`LANDMARKS["first_litters_day"]` and its seed-sd weight), (b) optionally models the removal as
an event (`biology.removal_day`, `biology.removal_n`, off by default), and (c) is adjudicated the
frozen-method way: 12 seeds, 1600 d, `scripts/seed_eval.py`, `scripts/multiseed_peak.py`; the
expectation is that N@315 rises toward 620 without moving the plateau. If it does not, that is the
result.

**Files:** `src/universe25/metrics/calibration.py`, `src/universe25/calib/priors.py`,
`src/universe25/config.py`, `src/universe25/sim.py` (removal event only), `configs/*.yaml`,
`NOTES.md`, `HANDOFF.md`, `README.md`

**Acceptance criteria:**
- The 2m configs stay in git history as the frozen reference; 2n is a separate NOTES section with
  the 12-seed table before / after
- `landmark_notes` updated; the loss change is documented as a target correction, not a fit
- `tests/run_tests.py` green; hash bit-identical with the new options off

---

## P4-0 — Observation builder + `mlp_frozen` policy (NumPy) + determinism

> **Status 2026-11-04:** scaffold landed — `src/universe25/agents/policy.py`
> (`Policy` protocol, `NeedDrivenPolicy`, `sample_masked`, `make_policy`), `policy.kind` in
> `config.py`, `tests/test_policy.py`; the default is bit-identical to the inline softmax
> (300-d trajectory hash `966401ea…`). Design: `docs/PHASE4_DESIGN.md`; prereg: `PLAN.md` §15.
> **Done 2026-11-04:** `agents/observation.py` (48 floats, `OBS_NAMES`),
> `MlpFrozenPolicy` (NumPy; orthogonal init or `.npz`; own RNG stream), `policy.kind: mlp_frozen`,
> `--policy` / `--policy-weights`; tests in `tests/test_policy.py`; builder 1.8 ms per 4,000
> agents; need-driven hash unchanged; smoke run OK. See `NOTES.md` 2026-11-04 → P4-0.

**Goal:** `agents/observation.py::build_observation(sim, idx) -> float32[m, K]` per
`PHASE4_DESIGN.md` §1.3 (interoception, body, role one-hot, local, targets, last action; no
`lifespan`, no PlayScore field); `MlpFrozenPolicy` (obs → 128 tanh → 128 tanh → 11 logits,
weights from an `.npz`, pure NumPy float32 inference, `allowed` mask as −1e8 on logits, inverse-CDF
sampling from the policy's **own** `make_rng` stream); a random-init weights file for smoke runs.

**Files:** `src/universe25/agents/observation.py`, `src/universe25/agents/policy.py`,
`src/universe25/config.py` (`policy.kind: mlp_frozen`, `policy.weights`), `tests/test_policy.py`,
`tests/test_determinism.py`

**Acceptance criteria:**
- String audit: no play / bout / motif / exaggeration-named field in the observation or policy code
- `test_determinism` passes for `mlp_frozen` (same seed → same hash, different seed → different)
- `need_driven` 300-d hash unchanged (`966401ea…` at 6 ticks/day)
- Observation builder < 2 ms per tick at 4,000 alive agents on the host path
- `tests/run_tests.py` green

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python tests\run_tests.py
python main.py --seed 7000 --out _output\mlp_frozen_smoke --config configs\smoke.yaml --days 30
```

**Task:**
```
Read HANDOFF.md, PLAN.md §15, docs/PHASE4_DESIGN.md §1 and this card. Build the observation
vector and the frozen-MLP policy kind on the policy hook in agents/policy.py. Keep every biology
kernel unchanged; the policy only returns int8 actions among `allowed`. Sample from the policy's
own RNG stream. No play-named signal anywhere (H2). Add tests; keep need_driven bit-identical.
```

---

## P4-1 — Calibration guard for policy arms (H-d)

> **Done 2026-11-04:** `src/universe25/calib/policy_guard.py`,
> `scripts/policy_guard.py`, `tests/test_policy_calibration_guard.py` (3 seeds × 400 d, ≈ 1.5 min).
> First run (seeds 8000–8011, 1600 d): control reproduces the record out of sample; a random
> frozen MLP is NOT PRESERVED (N@315 −61 %, peak −11 % / +240 d, cessation +560 d, late tail
> 5–20×). The curve is not policy-invariant; see `NOTES.md` 2026-11-04 → P4-1.
> **2026-11-06:** H-d amended (adopted by Jason): a landmark fails only beyond 10 % drift and
> 2 paired se; both readings printed. Random MLP still not preserved; heuristic with 12
> sub-steps (continue) preserved.
> **2026-11-07 — first learned arm, preregistered:** `pretrain_v2` at 12 sub-steps, seeds
> 8000–8011: NOT PRESERVED (N@315 +77 %, peak day −69 d, surviving births cease −103 d, decline
> band missed; peak N, N@736, conceptions hold). H-d falsified; NOTES 2026-11-07.

**Goal:** `tests/test_policy_calibration_guard.py` (400 d, 3 seeds, `mlp_frozen` with random
weights vs `need_driven`: landmarks printed, tolerance asserted) and `scripts/policy_guard.py`
(12 seeds 8000–8011, 1600 d, writes `_output/policy_guard_<kind>.json` with the canonical five,
N@1444, N@1588, decline band, relative to the control). Tolerance: every canonical landmark within
10 % of the control at the same seeds (PLAN.md H-d).

**Files:** `tests/test_policy_calibration_guard.py`, `scripts/policy_guard.py`, `NOTES.md`

**Acceptance criteria:**
- Guard test runs in < 5 min on the NumPy path
- Drift is **reported** in `NOTES.md` as a result; the biology is not retuned (frozen at 2m)
- `tests/run_tests.py` green

**Task:**
```
Read docs/PHASE4_DESIGN.md §4 and PLAN.md §15 (H-d). Implement the calibration guard for policy
arms. Never change biology parameters to make a policy pass; write the drift to NOTES.md.
```

---

## P4-2 — Homeostatic reward + PPO learner (torch, CUDA) + GPU determinism

> **Done 2026-11-06, after an amendment.** Maternal drive adopted (eighth drive,
> observation v2) and entropy 0.05: 650-day nursery, learner mean D 0.25 vs 1.04 (no updates)
> vs 0.82 (heuristic), 1.5 × 10^7 transitions, full-size colony; acceptance met. History below.
> **Earlier status (same day): built and tested; one acceptance item not met.**
> `learn/reward.py`, `learn/ppo.py`, `learn/policy_ppo.py` (`policy.kind: mlp_ppo`),
> `PPOConfig`, `scripts/nursery_smoke.py`, `tests/test_learn.py`; reflexes folded into the mask.
> Met: drive-only reward, H2 audit of `learn/*`, bit-identical 20-day GPU run, no bonus,
> learner D below the no-update baseline (0.43 vs 1.04). Not met: 10^7 transitions (2.5 × 10^6)
> because **the learner abandons its young** (NURSE / NEST 0.00 for nursing mothers, 1.5 % pup
> survival vs 13–15 %); the D comparison is confounded by the small colony. Next: decide how the
> learner gets maternal motivation (`docs/PHASE4_DESIGN.md` §1.4 options; NOTES 2026-11-06).

**Goal:** `src/universe25/learn/reward.py` (Keramati–Gutkin drive reduction per
`PHASE4_DESIGN.md` §1.4: n = 4, m = 2, setpoints 0, no drive-independent term, death terminal,
per-drive contributions logged, |r| capped at the one-tick maximum); `learn/ppo.py`
(shared-parameter PPO with a local critic per §1.5; rollout ring buffer; deaths end segments,
births reset the slot's GAE chain; masked losses); `policy.kind: mlp_ppo`; §5 GPU determinism
recipe (`CUBLAS_WORKSPACE_CONFIG`, `use_deterministic_algorithms(True)`, Warp `RUN_TO_RUN`, no
float atomics in obs/reward kernels); weights saved as the `.npz` that `mlp_frozen` loads.

**Files:** `src/universe25/learn/*`, `src/universe25/agents/policy.py`, `src/universe25/config.py`,
`tests/test_learn.py`, `docs/NVIDIA_STACK.md`

**Acceptance criteria:**
- Reward is a function of the drives only (unit test: zero drive change → zero reward; no bonus term)
- H2 string audit covers `learn/*` (P4-7)
- Run-to-run bit-identical on the same GPU for a 20-day nursery run (hash of weights + actions)
- Nursery smoke: mean drive sum below the random-policy baseline after 10^7 agent-steps
- No ICM / RND / count bonus (rejected: noisy-TV on conspecifics, see PHASE4_DESIGN.md §1.4)

**Task:**
```
Read docs/PHASE4_DESIGN.md §1.4–1.5, §5 and docs/RESEARCH_DIGEST.md part B. Implement the
homeostatic reward and the PPO learner on the policy hook. The heuristic is a control arm, never a
teacher: no distillation, no behaviour cloning. No play-named term (H2).
```

---

## P4-3 — Nursery pre-training harness

> **v2 2026-11-07:** founding-colony worlds (40 %) and concentrated mixed worlds
> added; pre-training v2 (10^8 steps, 50 min). The frozen v2 policy spreads the canonical colony
> like the heuristic and reaches peak 2,406, N@736 2,095, conceptions ending at 907 (Calhoun
> 2,200 / 2,056 / 920), on an arc about 100 days early (training seeds 7000–7002). Next: the
> preregistered guard on seeds 8000–8011 with `pretrain_v2/policy_final.npz`.

> **Done 2026-11-06:** `learn/nursery.py`, `scripts/pretrain_nursery.py`,
> `tests/test_nursery.py` (composition, training seeds only, bit-for-bit resume); throughput
> 51,700 agent-steps/s, VRAM 246 MB (`docs/NVIDIA_STACK.md`). Pre-training v1: 1.02 × 10^8 steps.
> On the canonical 4-pair start the frozen policy keeps the colony in the founders' four cells
> (NEST 48 % of adult decisions) and plateaus near 960 — harness mismatch: no nursery episode
> showed a founding colony. Next: decide (a) founding-colony nurseries + re-pretrain,
> (b) preregistered guard now, (c) stress drive amendment (NOTES 2026-11-06 → P4-3).

**Goal:** `scripts/pretrain_nursery.py`: seeded nursery worlds (500–4,000 adults + juveniles,
domain-randomised food / water refill, density and object count), 24 ticks/day, 10^8–10^9
agent-steps, checkpoints, a run manifest (torch / CUDA / Warp / numpy versions, GPU model, seed).

**Files:** `scripts/pretrain_nursery.py`, `src/universe25/learn/nursery.py`, `docs/NVIDIA_STACK.md`

**Acceptance criteria:**
- Throughput (agent-steps/s) and VRAM logged; seeds 7000–7009 only (never 8000–8011)
- Produces weights consumed by P4-1 and P4-6; nursery start stated as a limitation in NOTES

---

## P4-4 — `evo` policy (inherited weights, no reward)

> **Done 2026-11-13:**
> - Pre-evolution: all 8 lineages × 150 epochs (4,247 s on 8 workers), and none ended.
> - Evaluation: 48 evo runs and 16 control runs on 9889–9904 (4,332 s), with no stop.
> - The manipulation check passes (8 of 8 lineages, p 0.0039). **H-h is not supported:**
>   criterion 3 is met in 18 of 125 SEL and 22 of 114 NEU readings (mean d −0.062,
>   p(rise) 0.66).
> - Guard v2 is inconclusive, and the amended H-d table is not preserved (N@315, the decline
>   band).
> - NOTES 2026-11-13.

> **Design fixed 2026-11-13** (`docs/PHASE4_DESIGN.md` §4.4, H-h), before any code or run.
> The earlier sketch (the mother's weights or the parents' mean, pre-evolution in nursery
> worlds) is replaced by one-parent inheritance and serial founding epochs.

**Goal:** a genome per mouse (observation v5 → 32 → 15) in a capacity-sized buffer.
- A pup copies one parent's genome (mother or sire, ½ each) plus N(0, 0.02²), drawn from the
  policy's own genetics stream in biology order. No reward, no learner.
- Pre-evolution: 8 lineages × 150 founding epochs on training seeds.
- Neutral controls matched in pedigree depth.
- Evaluation on fresh seeds 9889–9904: the manipulation check, H-h and the guard.

**Files:** `src/universe25/agents/evo.py`, `src/universe25/agents/policy.py`,
`src/universe25/config.py` (`PolicyConfig`), `src/universe25/sim.py` (founding, conception and
birth hooks), `src/universe25/learn/evolution.py`, `scripts/evolve.py`, `scripts/sweep_evo.py`,
`scripts/analyse_evo.py`, `tests/test_evo.py`, `NOTES.md`, `docs/SEEDS.md`

**Acceptance criteria:**
- `evo` bit-identical run to run for a fixed seed; every other kind bit-identical to before
  (golden hashes)
- H2 clean by construction (no reward code path at all; audit of the new modules)
- pre-evolution, the manipulation check, H-h and the guard reported by the preregistered
  rules, negatives included

---

## P4-5 — Burghardt detectors + synthetic validation + V hopper fix

> **Done 2026-11-06:** `metrics/trace.py`, `metrics/detectors.py` (rules v3),
> `metrics/synthetic_traces.py`, `scripts/validate_detectors.py`, `scripts/detect.py`,
> `tests/test_detectors.py`, `free_choice_V_excl_hopper_unvalidated`. Preregistered validation:
> v1 11 / 12, v2 12 / 12 but falsifier failed, v3 12 / 12 (each on fresh seeds). Simulator:
> single-decision episodes, criteria 3 / 4 not evaluable → P4-8. See `NOTES.md` 2026-11-06.

**Goal:** `src/universe25/metrics/detectors.py` implementing `PHASE4_DESIGN.md` §2: episode
segmentation (bout-criterion interval from the sim's own log-survivorship), criterion 1
`nf_index`, criterion 2 onset / return / preference rates, criterion 3 `seq_struct_*`
(incompleteness, amplitude z, Jensen–Shannon divergence vs serious templates), criterion 4
recurrence / entropy rate / rigid-loop fraction / engagement vs cumulative exposure, criterion 5
`gate_relaxed` dose–response; all logged as `*_unvalidated` vector fields;
`free_choice_V_excl_hopper_unvalidated`; `scripts/validate_detectors.py` with scripted synthetic
agents (sequences written from the criterion text), ≥ 1,000 surrogates per detector, ablations,
preregistered AUC / FPR; neutral identifier names.

**Files:** `src/universe25/metrics/detectors.py`, `src/universe25/metrics/playscore.py`,
`src/universe25/sim.py` (`_log_metrics` only), `scripts/validate_detectors.py`,
`tests/test_detectors.py`, `docs/PHASE4_DESIGN.md` §2 (thresholds), `NOTES.md`

**Acceptance criteria:**
- No policy or learner imports or reads `metrics/detectors.py` or any `*_unvalidated` field (audit)
- Synthetic AUC / FPR per detector reported in NOTES whether pass or fail
- Thresholds written into `PHASE4_DESIGN.md` §2 **before** any evaluation seed (8000–8011) is run
- No animal or human play dataset anywhere (H1)

---

## P4-8 — Finer decision grain for free-time behaviour (prerequisite for H-f)

> **Done 2026-11-06:** `free_substeps` (config / CLI), `policy.substep_mode`
> (continue / rechoose / auto), sub-step rows in the trace, `tests/test_substeps.py`. Guard at
> K = 12: heuristic continue mode within 2 % on every resolvable landmark, fails only the 10 %
> rule on N@315 (+13 %, one paired se — below the rule's resolution; amendment proposed in
> PLAN §15.1); rechoose mode moved the arc (recorded negative). Detectors now have support
> (253–8,309 direction pairs per window); no arm meets all five criteria. See NOTES 2026-11-06.

> **Status 2026-11-06:** not started. P4-5 found that at 6 decisions per day (one
> every 4 hours) every episode in the simulator lasts one decision, for the heuristic and the
> random policy alike, so criteria 3 and 4 have no structure to evaluate (12–21 direction pairs
> per 20-day window). Mouse play bouts last seconds to minutes. Without a finer grain, H-f
> (structure, not frequency) cannot be tested for any policy.

**Goal:** a free-time sub-step layer that leaves the calibrated biology untouched: when an
agent's chosen action is a free one (EXPLORE, MANIPULATE, SOCIAL) it executes K sub-decisions
(e.g. K = 12, 20 min each) inside the decision interval, with movement and object contact per
sub-step and no change to drives, nursing, conception, stress or mortality accounting (those
stay per decision). The policy (heuristic, frozen MLP, learner) chooses the sub-step actions
among the free actions only; the trace recorder logs sub-steps. Off by default and
bit-identical.

**Files:** `src/universe25/sim.py` (execute only), `src/universe25/config.py`,
`src/universe25/agents/policy.py`, `src/universe25/metrics/trace.py`, `tests/`

**Acceptance criteria:**
- K = 1 (off) bit-identical (300-d hash); the calibration guard (P4-1) for the heuristic with
  K = 12 shows every canonical landmark within 10 % (the sub-steps must not move the biology)
- traced runs show multi-step episodes; detectors (v3, unchanged) report criteria 3 / 4 with
  support (≥ 100 direction pairs per window)
- detector rules are not re-tuned on simulator output (they are fixed at v3)

---

## P4-9 — Detector rules v4: phase-preserving trigger null, template minimum support

> **Done 2026-11-08:** v4 (phase-preserving shifts, decision-counted trigger
> window, template support) passes 14 / 14 preregistered checks on seeds 40,000+. On simulator
> traces criterion 2 now reads "locked" in every arm because self-caused cell entries count as
> triggers: rules v5 must separate them (synthetic classes that move between cells, fresh
> split) before any sweep reads criterion 2. NOTES 2026-11-08.

> **Status 2026-11-06:** not started. Found by P4-5 / P4-8 on simulator traces
> (never used to tune): (a) with sub-steps, criterion 2's circular-shift null shifts triggers by
> arbitrary rows, while density and wound triggers update once per decision and continue-mode
> onsets fall on decision boundaries, so criterion 2 reads "locked" by construction; (b) the
> serious template's reversal fraction has no minimum support (one pair at the decision grain).

**Goal:** v4 rules: shift the trigger and relaxed series by whole decisions (multiples of
`free_substeps`, read from the trace meta); treat the serious reversal fraction as 0 below 20
direction pairs. Write v4 into `docs/PHASE4_DESIGN.md` §2 first, then test on a fresh synthetic
split (seeds 40,000 + …), adding a synthetic class whose onsets fall only on decision boundaries
with no trigger dependence (must pass criterion 2).

**Acceptance criteria:**
- v3 record kept; v4 passes the preregistered AUC / TPR / FPR on the fresh split
- no rule tuned on simulator output; `tests/run_tests.py` green

---

## P4-10 — Detector rules v5: exogenous triggers only (criterion 2)

> **Done 2026-11-08:** v5 passes 16 / 16 preregistered checks on seeds 50,000+
> (every AUC 1.000); the v4 trigger set falsely locks the mobile class in 30 / 30 colonies.
> On the P4-8 simulator traces criterion 2 now reads "not locked" in every arm; exogenous
> triggers are rare, so this is weak evidence. NOTES 2026-11-08.

**Goal:** criterion 2's trigger set keeps aggression received and density jumps in a cell the
individual already occupied; self-caused cell entries (and the density jumps that come with
them) no longer count. Rules written into `docs/PHASE4_DESIGN.md` §2 (v5) before the test.
Synthetic mobile classes (2 × 2 cells, objects in their own denser cell) at K = 12; fresh split
on seeds 50,000 + …; then re-read the P4-8 simulator traces.

**Acceptance criteria:**
- the 14 v4 checks and both mobile criterion-2 checks pass the preregistered AUC / TPR / FPR
- v4 reading kept reproducible (diagnostic switch); `tests/run_tests.py` green

---

## P4-11 — Detector rules v6: a form beyond chance (criteria 3 and 4)

> **Done 2026-11-09:** 18 / 18 synthetic checks on seeds 60,000+ (every AUC
> 1.000); simulator negative control: criteria 3 / 4 met in 0 of 18 windows per kind (v5: 18
> of 18). Re-reading the H-e sweep: no policy, the learned net included, meets criterion 3 or
> 4 in any window — the simulator gives policies no control over movement form. NOTES
> 2026-11-09.

**Goal:** under v5 a random-init network meets criteria 1–4 for locomotion everywhere, because
the simulator's EXPLORE moves are isotropic random walks and neither criterion 3 nor criterion 4
asked for structure beyond chance. v6 adds one form test to both: the episodes' approach–withdraw
reversal fraction must beat a within-episode order shuffle of the same labels (excess ≥ 0.10,
z > 1.645). Rules written into `docs/PHASE4_DESIGN.md` §2 (v6) before the test. Fresh synthetic
split on seeds 60,000 + …, plus a simulator negative control (random-init networks, init seeds
7001 / 7002, training seeds 7003–7005).

**Files:** `src/universe25/metrics/detectors.py`, `scripts/validate_detectors.py`,
`scripts/negcontrol_v6.py`, `tests/test_detectors.py`, `NOTES.md`

**Acceptance criteria:**
- the 16 v5 checks (with v6 flags) and both random-walk checks pass the preregistered
  AUC / TPR / FPR
- the simulator negative control meets criterion 3 and criterion 4 in ≤ 10 % of windows per kind
- every v5 statistic unchanged (the form test draws from its own random stream); v5 flags kept in
  the output; `tests/run_tests.py` green

---

## P4-12 — Action space v2: movement form the policy controls

> **Done 2026-11-09:** checks 1 and 2 pass: the four reference hashes are
> identical; a scripted policy meets the v6 form test in both kinds and the random v3 net does
> not. Check 3 reading (training seeds): `pretrain_v3` spreads its free time evenly over each
> family's primitives, and its form excess equals the random v3 net's (locomotor +0.090 vs
> +0.090). Form test met in 0 of 18 windows (random net: 5 of 18). Under v2 the form test has
> a mechanical baseline, so v6's validation does not carry over. Curve guard: not preserved
> (arc 130–340 d late). Pre-training learned less than v2 (pup survival about 0.11 vs 0.50,
> entropy 1.65). NOTES 2026-11-09. The H-f amendment is proposed in PLAN §15.1 and waits for
> Jason.

**Goal:** add four generic free-time movement primitives (`ACT_RUN_ON`, `ACT_TURN_BACK`,
`ACT_BACK_OFF`, `ACT_CIRCLE`) and an agent heading. Policies can then shape how a move unfolds,
not only when it starts; under detector rules v6 no policy can express form today. Observation
v3 (55 floats), with v2 weight files kept bit-identical. Detector event definitions cover the
action families. Retrain the nursery learner as `pretrain_v3`, then read it on training seeds.
Design and checks: `docs/PHASE4_DESIGN.md` §1.8.

**Files:** `agents/state.py`, `agents/policy.py`, `agents/observation.py`, `sim.py`,
`metrics/trace.py`, `metrics/detectors.py`, `metrics/playscore.py`, `tests/test_actions_v2.py`,
`NOTES.md`

**Acceptance criteria:**
- heuristic (K = 1, K = 12 traced) and v2-net trajectories hash identically before and after
- a scripted alternation passes the v6 form test in both kinds; a random v3 net does not
- `pretrain_v3` trained and read on training seeds 7000–7002 next to the random v3 net (no pass
  condition); H-f amendment proposed to Jason before any evaluation seed
- `tests/run_tests.py` green; H2 audit clean (no play-named identifier)

---

## P4-13 — Playground physics and detector rules v7

> **Done 2026-11-09:**
> - Physics off is bit-identical (six hashes); the mechanics tests pass.
> - Rules v7 pass every preregistered check: 18 / 18 synthetic, negative control 0 of 18
>   windows per kind in both substrates (v6 11–17 %), scripted alternation seen. v7 is frozen.
> - Development reading: `pretrain_v4` ignores the balls. Its free-time shares equal v3's, only
>   3 % of its object rows touch a ball, and near a ball it acts as near a fixed object. No
>   window meets the form test in either arm.
> - Physics moves the heuristic's curve (N@315 −50 %, peak day +159; curiosity 0.73 vs 0.29).
>   The v4 guard is not preserved (early arc).
> - Likely reason: curiosity and boredom have consequence-free routes.
> - Next step is Jason's (NOTES 2026-11-09). H-f stays held.

**Goal:** give movement form a consequence (Jason, 2026-11-09: hold H-f, fix the substrate).
- Balls respond to how they are approached: a push of κ·u along the approach, roll with
  friction, bounce at the bounds.
- Object-family relief of curiosity and boredom scales with the speed a contact gave a ball
  (`playground.ball_physics`, default off).
- Observation v4 adds the nearest object's mobility and speed.
- Detector rules v7 replace the form test's label shuffle with a replay of the reference policy
  (an even mix of the family's moves, under the simulator's mechanics).
- Retrain as `pretrain_v4`.

Design and checks: `docs/PHASE4_DESIGN.md` §1.9 and §2 (v7).

**Files:** `config.py`, `world/geometry.py`, `sim.py`, `agents/observation.py`,
`agents/policy.py`, `metrics/trace.py`, `metrics/detectors.py`, `metrics/synthetic_traces.py`,
`scripts/negcontrol_v7.py`, `tests/test_physics.py`, `NOTES.md`

**Acceptance criteria:**
- physics off: six reference trajectories hash identically before and after
- mechanics unit tests pass; physics draws from no random stream
- v7: the v6 battery passes with v7 flags on seeds 70,000+; the simulator negative control
  (random nets, with and without physics) meets c3 / c4 in ≤ 10 % of windows per kind; the
  scripted alternation passes and the random net does not
- `pretrain_v4` trained and read on training seeds 7000–7002 next to the random v4 net, with
  the curve guard and the heuristic-with-physics guard; revised H-f amendment proposed to Jason
  before any evaluation seed
- `tests/run_tests.py` green; H2 audit clean

---

## P4-14 — Novelty-based curiosity (place memory)

> **Stopped at the matching gate 2026-11-09:**
> - Built and bit-identical when off (seven hashes); mechanics tests green.
> - Relief matching: no g within 10 % of the target curiosity. The best is g = 8 at +23 %;
>   curiosity flattens near 0.3.
> - Heuristic guard, `pretrain_v5` and the reading not run, per the preregistered stop.
> - Next: Jason chooses between the guard at g = 8 as a deviation and a re-preregistered
>   matching. NOTES 2026-11-09.
>
> **2026-11-09 later:**
> - Jason chose the guard at g = 8 (deviation recorded in 2eb5e3f). It is preserved, with low
>   power at n = 3.
> - The observation bug (v4 / v5 showed the decision action) is fixed in f686968, and
>   `pretrain_v5` was restarted on the fix.
> - Reading and v5 guard pending.

**Goal:** curiosity is relieved by consequences in every family (Jason, 2026-11-09).
- Locomotor curiosity relief scales with the novelty of the bin entered: 10 × 10 grid,
  1 − exp(−Δt / 1 day), per-animal memory.
- `drives.consequence_gain` g also scales the ball-push relief.
- Observation v5 adds the novelty of the bins ahead and behind.
- g is chosen by matching the heuristic's adult mean curiosity to the frozen substrate, then the
  heuristic guard runs.
- Retrain as `pretrain_v5`, then read it on training seeds.

Design and checks: `docs/PHASE4_DESIGN.md` §1.10.

**Files:** `config.py`, `sim.py`, `agents/observation.py`, `agents/policy.py`,
`learn/nursery.py`, `scripts/pretrain_nursery.py`, `scripts/policy_guard.py`,
`scripts/scan_novelty_gain.py`, `scripts/read_p414.py`, `tests/test_novelty.py`, `NOTES.md`

**Acceptance criteria:**
- novelty off and g = 1: seven reference trajectories hash identically before and after
- mechanics unit tests pass; no random draw
- relief-matching scan reported, g chosen by the preregistered rule (or stop); heuristic guard
  reported
- `pretrain_v5` trained and read next to the random v5 net, with its curve guard; H-f stays
  held
- `tests/run_tests.py` green; H2 audit clean

---

## P4-15 — Consequence sensitivity of the learner (Tier 2)

> **Done 2026-11-11:**
> - The manipulation check passed. The primary test **failed**: A1 − R = +0.011 ± 0.008,
>   one-sided p 0.10, floor 0.05.
> - The stop rule applies: no further substrate change for PPO learners, and the amended H-f
>   is not run.
> - A1 rarely touches objects and ignores ball mobility. Its colony peaks at about 420.
> - NOTES 2026-11-11.

**Goal:** change the learner's signal and ask whether its free time depends on object
consequences beyond its entropy.
- Learner changes: entropy annealing, per-type advantage normalisation, λ per unit of time.
- Arms: A0 (the `pretrain_v4` recipe after the observation fix), A1 (A0 plus the three changes),
  R (`random_init(7007)`).
- Evaluation: fresh seeds 9100–9111. Primary statistic Δ = P(object | near a ball) −
  P(object | near a fixed object). Sign-flip test, floor 0.05.
- Program-level stop rule.

Design: `docs/PHASE4_DESIGN.md` §4.2.

**Files:** `config.py`, `learn/ppo.py`, `learn/policy_ppo.py`, `learn/nursery.py`,
`scripts/pretrain_nursery.py`, `scripts/p415.py`, `tests/test_learn.py`, `NOTES.md`

**Acceptance criteria:**
- learner options default to the existing behaviour (learner determinism tests unchanged)
- manipulation check reported before any evaluation seed
- primary test and, if it passes, the gated secondary reported
- `tests/run_tests.py` green; H2 audit clean

---

## P4-16 — H-g and the playground-off arm

> **Done 2026-11-13:**
> - 72 runs on seeds 9877–9888 (3,696 s on 8 workers), with no stop.
> - **H-g is falsified** by the preregistered rule: four of six cells rise through phase D at
>   p(rise) ≤ 0.002, and no cell is supported.
> - Playground off: the differential prediction passes, the locomotor rate rises through D
>   under all three policies, and every colony grows faster and peaks earlier.
> - NOTES 2026-11-13.

**Goal:** test H-g (breakdown suppresses play-likeness) and run the playground-off arm. Neither
needs a form, as P4-15's stop rule directs. Design: `docs/PHASE4_DESIGN.md` §4.3 (fixed
2026-11-13 before any run).

**Files:** `src/universe25/metrics/phase_rates.py`, `scripts/sweep_hg.py`, `scripts/analyse_hg.py`,
`tests/test_phase_rates.py`, `NOTES.md`, `docs/SEEDS.md`

**Acceptance criteria:**
- 72 runs on seeds 9877–9888; H-g answered by the preregistered rule; the playground-off checks
  reported
- negatives reported; `tests/run_tests.py` green; H2 audit clean

---

## P4-17 — Norm-matched check of criterion 3 (H-i)

> **Done 2026-11-13:**
> - 72 runs on seeds 9905–9928 (about 67 min on 8 workers), with no stop. 10 runs died out
>   before day 1,600, and their empty windows give no reading (a tooling fix made before any
>   H-i statistic was read).
> - **H-i is supported** by the preregistered rule, at the smallest margin the design can
>   detect: 6 of 17 tested colonies are positive, none negative, p(rise) 1/64. The dose and
>   the genome norms are reported.
> - NOTES 2026-11-13.

**Goal:** test whether weight size alone produces criterion 3 on nets (H-i), after H-h found
it in neutral-drift nets as often as in evolved ones. Design: `docs/PHASE4_DESIGN.md` §4.5
(fixed 2026-11-13 before any code or run).

**Files:** `src/universe25/agents/evo.py` (the jump genome),
`src/universe25/metrics/phase_rates.py` (the exact sign-flip without the pattern matrix),
`scripts/sweep_nm.py`, `scripts/analyse_nm.py`, `tests/test_evo.py`,
`tests/test_phase_rates.py`, `NOTES.md`, `docs/SEEDS.md`

**Acceptance criteria:**
- 72 runs on seeds 9905–9928; H-i answered by the preregistered rule; the dose and the genome
  norms reported
- every other kind bit-identical (golden fast tier); `tests/run_tests.py` green; H2 audit
  clean; negatives reported

---

## P4-6 — Phase 4 sweep harness

> **2026-11-08:** survival condition decided (H-e amended to a state-based dose-response, PLAN
> §15.1, ADOPTED); first sweep = the H-e design there. v5 done (P4-10). Harness for H-e:
> `scripts/sweep_he.py` + `scripts/analyse_he.py`.
>
> **H-e answered 2026-11-08:** supported by the preregistered rule (learned net, both kinds).
> The robust part is narrow: object onsets are more strongly gated by the relaxed field where
> more animals are relaxed. The locomotor part rests on two near-empty crisis windows. NOTES
> 2026-11-08. Still open for this card: H-f, H-g, the playground-off arm and the full
> `sweep_phase4.py` grid.
>
> **2026-11-09 (rules v6, P4-11):** H-f is not testable in the current action space — under v6
> no policy meets criterion 3 or 4 anywhere, because no policy controls the path of a move.
> Needs a decision (richer action space under the calibration guard, or structure measured on
> action sequences) before H-f.
>
> **2026-11-09 (action space v2, P4-12):** the richer action space exists. On training seeds the
> learned v3 net mixes the primitives like the random v3 net, so the amended H-f (learned v3 vs
> random v3 at matched V) is predicted null. The form test also needs a null that includes the
> movement mechanics. Both decisions belong to Jason before any evaluation seed (PLAN §15.1).

**Goal:** `scripts/sweep_phase4.py`: policy kind × resources (ABUND / SCARCE) × playground
(ON / OFF) × seeds 8000–8011, 1600 d at 24 ticks/day, parquet + `run.json` + detector vectors;
summary tables per PLAN.md §15.6 (mean ± se, paired differences, surrogate bands); resumable;
manifest per run.

**Files:** `scripts/sweep_phase4.py`, `NOTES.md` ("Phase 4" section), `HANDOFF.md`

**Acceptance criteria:**
- Budget within PLAN.md §15.4; negatives reported; H-d, H-e, H-f, H-g each answered or marked untested

---

## P4-7 — H2 audit extension (policy, observation, learner, detectors)

**Goal:** extend the string audit (`tests/test_conservation.py` or P2-3's CI audit) to
`agents/policy.py`, `agents/observation.py`, `learn/*` and `metrics/detectors.py`: forbidden
identifiers `play_reward`, `reward_play`, `playscore` / `play_score` inside `learn/` and
`agents/`, `motif`, `_bout` / `bout_`, `exaggerat`; plus an import audit (no `learn/` or
`agents/` module imports `metrics.detectors` or `metrics.playscore`).

**Acceptance criteria:**
- A negative test proves the audit fails on an injected forbidden term
- `tests/run_tests.py` green

---

## P1-1 — Scarcity arm config + smoke

> **Status 2026-11-08: tools built, manipulation check failed.**
> `resources.scarce_supply: capacity` (food-limited carrying capacity, shared by weaned
> occupancy, two-day cap), optional famine pulses, scramble sharing at hoppers (abundant arm
> bit-identical), `configs/scarce.yaml`, `tests/test_scarcity.py`. Under every design tried the
> scarce colony is smaller and *more* relaxed than the abundant one (crowding dominates the
> relaxed field). H-e amended to test the animals' state, with SCARCE-PG (capacity 1,000) as
> the food contrast (PLAN §15.1, adopted 2026-11-08).

**Goal:** Add `TRACK-E-U25-SCARCE-PG` config (seed 7002) with finite food refill; smoke 30–100 days; log aggression proxy vs abundant.

**Files:** `configs/scarce.yaml` (new), `configs/default.yaml` resources, `NOTES.md`

**Acceptance criteria:**
- Scarce run completes; aggression/stress metrics higher than abundant smoke (directionally)
- Playground still has **no** play reward
- Calibration script still runs (landmarks may fail — OK)

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python main.py --seed 7002 --out _output\scarce_smoke --config configs\scarce.yaml --days 50
python tests\run_tests.py
```

**Task:**
```
Implement scarcity resource mode + configs/scarce.yaml for arm TRACK-E-U25-SCARCE-PG (seed 7002). Compare aggression/stress vs abundant smoke in NOTES. H2: no play reward. Link to Leibo Gathering as contrast, not as play evidence.
```

---

## P1-2 — Abundance × playground OFF arm

**Goal:** Run `TRACK-E-U25-ABUND-NOPG` seed 7001; compare free-choice V and playground occupancy metrics (should be ~0 / N/A) vs PG ON.

**Files:** run scripts or CLI `--playground off`; `NOTES.md`

**Acceptance criteria:** Side-by-side table of V, G, occupancy, peak N

**Task:**
```
Run abundant playground OFF (seed 7001) vs existing ON (7000) at a comparable day budget. Table V/G/occupancy/peak N in NOTES. Do not change PlayScore formulas except bugfixes labelled unvalidated.
```

---

## P1-3 — Device-resident action select (perf)

> **Profile 2026-10-30 (NumPy, 6 ticks/day, N 340→2140, days 250–400):** 16.4 ms/tick.
> `_passive_nurse` 38 % (Python loop over mothers × pups), `_execute_actions` 50 % (per-agent
> forage/drink loops, `_aggress` O(capacity) per attacker, per-tick `np.array` of food/water xy),
> `_select_actions` 4 %. The host Python loops, not the vectorized math, are the bottleneck —
> vectorize those first (keep the NumPy trajectory hash identical, or re-calibrate), then Warp.

**Goal:** Move utility action selection onto Warp to escape hybrid sync tax; keep NumPy parity.

**Files:** `warp_kernels/kernels.py`, `engine.py`, `sim.py`, `docs/NSIGHT.md`

**Acceptance criteria:**
- Microbench shows improved hybrid or documents remaining host bottlenecks
- Parity test for action histograms / traj hash policy agreed in NOTES
- CUDA Graph optional

**Task:**
```
Phase-3-perf slice: port action utility select to Warp on RTX 5080. Keep NumPy reference. Update NSIGHT.md benches. H2 unchanged. Pathspec commits.
```

---

## P1-4 — Newton playground rigid bodies (stub → step)

**Goal:** Step balls/ramps with Newton or `warp.sim`; mice apply impulses; kinematic fallback remains.

**Files:** `src/universe25/nvidia/newton_playground.py`, world play objects, tests

**Acceptance criteria:**
- Playground objects move under contact in a smoke demo
- Still **no** play reward — manipulate remains curiosity/boredom
- Graceful skip if Newton missing

**Task:**
```
Wire Newton playground stepping behind a feature flag. Document in NVIDIA_STACK.md. Must not introduce play objective. Add smoke test that skips without Newton.
```

---

## P2-1 — Editorial WebGPU / canvas top-down viewer

**Goal:** Top-down 16-cell pen with role-colored dots, playground AABB, stress heatmap; palette from HANDOFF §8.

**Files:** new `viewer/` or `web/` (propose structure), snapshot JSON/bin from `io/snapshots.py`

**Acceptance criteria:**
- Loads a run snapshot; plays scrub timeline
- Colors: paper #F4F0E6, ink #1A1A1A, stress #8B1E1E, nest #2F5D50
- **No** purple/glass/AI-slop aesthetics
- README screenshot section

**Task:**
```
Build a minimal top-down Universe25 viewer consuming existing snapshots. Follow HANDOFF visual tokens strictly. Prefer uPlot for charts later; viewer first. No AI-looking chrome.
```

---

## P2-2 — Dashboard (uPlot + restyled shadcn)

**Goal:** Population curve with 4 phases shaded; conception rate; wounds; nest occupancy; % withdrawn; V and G gates.

**Files:** `viewer/` dashboard route; reads `metrics.parquet` (via pre-exported JSON/CSV if browser)

**Acceptance criteria:** Matches visual tokens; works offline on a static export; documents export script

**Task:**
```
Create scientific editorial dashboard for metrics.parquet exports. uPlot charts, phase shading, PlayScore components clearly labelled UNVALIDATED. Palette from HANDOFF. No default shadcn violet.
```

---

## P2-3 — H2 static audit in CI/tests

**Goal:** Test that fails if reward/utility strings match play/bout/motif/exaggeration in agent code paths.

**Files:** `tests/test_h2_no_play_reward.py`, `agents/drives.py`

**Acceptance criteria:** Audit runs via `tests/run_tests.py`; documents allowlist if any

**Task:**
```
Add a deterministic H2 linter test scanning src/universe25 for forbidden play-reward identifiers in reward/utility contexts. Keep ACT_MANIPULATE allowed. Wire into run_tests.py.
```

---

## P2-4 — PlayScore components: real D and S (still unvalidated)

**Goal:** Replace stand-ins with clearer JS-divergence D and recurrence×entropy S; keep labels `_unvalidated`; agents still do not optimize.

**Files:** `src/universe25/metrics/playscore.py`, logger schema, NOTES

**Acceptance criteria:**
- Formula documented; unit-level smoke on synthetic action streams
- Schema changelog in NOTES
- Optimize-vs-eval reminder in docstring

**Task:**
```
Upgrade PlayScoreAccumulator D and S toward gan’s definitions without validating them. Keep F,V,G. Never feed PlayScore into action selection. Tests for accumulator math.
```

---

## P3-1 — RL vec env skeleton (Isaac Lab / Gymnasium style)

**Goal:** Flesh out `rl_env_spec.py` into a thin Gymnasium-compatible stub with forbidden reward terms enforced.

**Files:** `nvidia/rl_env_spec.py`, optional `env/gym_universe25.py`

**Acceptance criteria:**
- `reward_terms_forbidden` enforced by assert
- Allowed: survival, homeostasis, generic curiosity — **not** play
- No training loop required yet

**Task:**
```
Implement a Gymnasium-shaped Universe25 vec env stub per rl_env_spec.py. Enforce H2 forbidden rewards. Document observation layout. No PPO training in this task.
```

---

## P3-2 — Baseline runners (PPO / ICM / RND / random) — eval PlayScore only

**Goal:** Training entrypoints that optimize allowed rewards; log PlayScore eval-only.

**Files:** new `baselines/`, PLAN.md arms update

**Acceptance criteria:**
- Random + at least one learning baseline runs smoke days
- PlayScore not in loss
- Seeds 7000–7009 respected

**Task:**
```
Add baseline smoke runners (random required; PPO or ICM optional if deps allow). PlayScore eval-only. Update PLAN arms. Do not install into shared venv without approval — use existing torch if present.
```

---

## P3-3 — Spinka transfer test harness (protocol only → minimal impl)

**Goal:** Pre-commit protocol: push/friction/limb perturbation recovery comparison for agents with high vs low prior playground exposure.

**Files:** `docs/SPINKA_PROTOCOL.md` (new), optional stub runner

**Acceptance criteria:** Protocol with seeds, metrics, stop rules, negative-result language; no overclaim

**Task:**
```
Write docs/SPINKA_PROTOCOL.md pre-registering the transfer test. Optional stub that applies kinematic perturbations. Cite Spinka-style prediction without claiming we measured it yet.
```

---

## P3-4 — USD / Omniverse path polish

**Goal:** Export animated agent points to USDA sequence or time samples; document Omniverse open steps.

**Files:** `nvidia/usd_export.py`, `docs/NVIDIA_STACK.md`

**Acceptance criteria:** Static pen + sample agent layer exports; skip without pxr

**Task:**
```
Extend USD export with agent point samples from a short run. Document viewer steps. Optional path only.
```

---

## P3-5 — README research polish (public-facing later)

**Goal:** When Jason is ready to open the repo: abstract, figure, calibration honesty, how to cite.

**Files:** `README.md` only

**Acceptance criteria:** No inflated claims; references complete; quickstart accurate

**Task:**
```
Rewrite README for research clarity: claim, non-goals, phase status, honest calibration table, visuals intent, refs. Keep MIT. Do not claim play emerged.
```

---

## Quick checks

**Status digest**
```
Summarize HEAD commit, NOTES latest run, open P0 tasks, and whether calibration or Warp parity is more blocking. No code changes.
```

**H2 audit now**
```
Grep src/universe25 for play/bout/motif/exaggeration in reward/utility contexts. Report findings only.
```

**Rebase & test**
```
git pull --rebase origin master; python tests\run_tests.py; report.
```
