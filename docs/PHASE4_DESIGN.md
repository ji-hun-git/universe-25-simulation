# Phase 4 design — learning agents on a frozen biology (2026-11-04)

Status: **design + scaffold**. The policy hook (`src/universe25/agents/policy.py`, `policy.kind`
in `config.py`) is in place and bit-identical to the phase 1/2 behaviour with the default
`need_driven` policy. Nothing in this document is a result. Sources are in
`docs/RESEARCH_DIGEST.md`; the preregistration is `PLAN.md` → "Phase 4 plan".

## 0. The problem this design solves

The mission asks whether play-like behaviour emerges in **learning** agents under abundance vs
survival with **no play reward** (HANDOFF §0, §1). Until today the agents were a fixed utility
softmax over hand-set drives (`NeedDrivenPolicy`): nothing learned, so the question could not be
asked. The biology (feeding, nursing, conception, stress, imprinting, mortality) is calibrated to
Calhoun's curve and **frozen** (phase 2m). Phase 4 therefore has to add a learned action policy
*without* changing a single biology kernel, and has to measure play-likeness without ever
training on it.

Hard rules that bind every choice below: no LLM agents; no imitation / behaviour cloning (the
heuristic is a **control arm**, never a teacher); no reward, utility, observation or goal named
play / bout / motif / exaggeration (H2; the string audit covers `sim.py`, the config, and now
`agents/policy.py`); never train on animal or human play data; `PlayScore*_unvalidated` is
eval-only; the NumPy reference path stays deterministic for a fixed `--seed`.

## 1. Architecture

### 1.1 Separation of concerns (implemented today)

| Layer | Owner | Learned? |
|---|---|---|
| Decision cadence (`ticks_per_decision`), eligibility mask (pups rest/nest only; MATE needs adult, stress < 0.75, not withdrawn, energy > 0.4; NURSE needs a female with maternal > 0; MANIPULATE only with the playground on), reflex overrides (thirst > 0.85 → DRINK, hunger > 0.85 → FORAGE, fatigue > 1.2 → REST) | `sim._select_actions` | no — physiology, identical for every policy |
| Choice among the eligible 11 actions | `Policy.choose(sim, idx, allowed)` | **yes** (phase 4) |
| Action effects, drives, nursing, conception, births, stress, imprinting, mortality | `sim._execute_actions`, `_update_drives`, `_feed_by_nest`, `_daily_breeding_pass`, `_density_stress`, `_age_and_die`, Warp kernels | no — frozen biology |

The policy's only output is an `int8` action per deciding agent. It can change the population
curve only through *where agents go and when they eat, drink, nest and nurse* — which is exactly
the channel through which a real mouse's behaviour shapes a colony. Whether the calibrated curve
survives a learned policy is an **empirical question** (§4), not a tuning target.

### 1.2 Policy kinds (config `policy.kind`)

| kind | What | RNG | Status |
|---|---|---|---|
| `need_driven` | phase 1/2 utility softmax | one draw per deciding agent from the sim stream | done, bit-identical |
| `mlp_frozen` | NumPy float32 MLP inference (48 → 128 → 128 → 11), weights from an `.npz` or a seeded orthogonal init; learning off | own `make_rng(seed + 1_000_003)` stream | done (P4-0, 2026-11-04) |
| `mlp_ppo` | same net, PPO updates every T ticks in torch (CUDA) | torch generator seeded from `seed`; see §5 | to build (P4-2) |
| `evo` | per-agent weights inherited at birth with Gaussian mutation; no reward, no learner | sim stream for mutation draws (biology-ordered) | to build (P4-4) |

Rule for every learned kind: the policy never consumes the biology RNG stream for *sampling*
(so two policy versions see the same biology draws for the same state sequence), and it never
reads a PlayScore field.

### 1.3 Observation vector (v1, ~48 floats, egocentric, all from existing SoA state)

| Block | Dims | Content (scaling) |
|---|---|---|
| Interoception | 7 | hunger, thirst, fatigue, social_drive, curiosity, boredom, stress (/1.5) |
| Body | 6 | energy, age / `max_age_days`, sex, gestating, maternal, wounds |
| Role | 7 | one-hot of `role` (pup, juvenile, territorial M, subordinate M, breeding F, nursing, withdrawn) |
| Local | 5 | own-cell density (counts / 240), nest occupancy / capacity, `in_playground`, food in cell (/refill), water in cell (/refill) |
| Targets | 12 | for food, water, own nest, nearest object: capped distance (/50 in) and unit direction |
| Last action | 11 | one-hot |

Excluded on purpose: the agent's own `lifespan` (hidden information), any PlayScore term, any
neighbour-level feature that needs a k-nearest search (v2, host cost). `competence` is excluded
in v1 so that the withdrawn phenotype is expressed through the role flag and the biology, not
read directly by the policy (ablation in v2).

### 1.4 Reward (homeostatic drive reduction; no drive-independent term)

Keramati & Gutkin 2014: with internal variables h_i, setpoints h_i*, scales s_i,

```
delta_i,t = (h_i,t - h_i*) / s_i        i in {hunger, thirst, fatigue, social_drive, curiosity, boredom, stress}
D_t       = ( sum_i w_i |delta_i,t|^n )^(1/m)   n = 4, m = 2 (K&G need n > m > 1; Dulberg et al. 2023 used 4 / 2), w_i = 1
r_t       = D_t - D_{t+1}               from the pre- and post-tick drive state
death     : r_t = D_t - D_max, then absorbing (done = 1, bootstrap 0)
gamma     = 0.98 at 6 ticks/day, 0.99 at 24 ticks/day (about a 50-100-tick horizon)
```

Setpoints are 0 for every drive (the heuristic treats each as a deficit). The reward is a
telescoping function of the drives only: a policy maximising it minimises the discounted sum of
deviations, and there is no term a policy could inflate without reducing a drive. **No** ICM /
RND curiosity bonus: prediction-error bonuses fixate on the least predictable part of the world,
which in a colony is other mice (Burda et al. 2018 "noisy TV"), so they would pull agents into
crowds and corrupt the density-driven calibration. Curiosity and boredom are already drives in
D. Per-drive contributions to r are logged so reward hacking of one drive is visible.

### 1.5 Policy and learner

- Net: obs → 128 tanh → 128 tanh → 11 logits; separate critic 128-128-1; orthogonal init, last
  layer gain 0.01; about 24 k parameters each. Inference on the reference path is pure NumPy
  float32 (`x @ W1`, `tanh`, …), actions by inverse CDF on the masked softmax with one uniform
  per agent from the policy stream (same sampler as `sample_masked`).
- Mask: the sim's `allowed` matrix applied as −1e8 on logits (Huang & Ontañón 2020), so the
  learned policy can never choose an action the heuristic could not.
- Learner: PPO with shared parameters and a local critic (IPPO). Rollout horizon T = 12 ticks
  (6 tpd) / 16 (24 tpd); 4 epochs × 4 minibatches; Adam 3e-4 (eps 1e-5) with linear decay;
  clip 0.2; GAE λ 0.95; entropy 0.01 with a floor; value coef 0.5; Huber value loss; grad clip
  1.0; running value normalisation; per-minibatch advantage normalisation; **fixed** reward scale.
- Births and deaths: a death ends a segment (`done`, bootstrap 0 after the terminal reward); a
  birth starts a fresh segment in that SoA slot (GAE chain and last value reset so a reused
  slot never inherits its previous occupant's trajectory); losses are masked by
  `alive_during_step` and divided by the number of valid samples.
- Interleaving per tick: build obs (host NumPy in v1; a Warp kernel once P1-3 moves action
  selection on device) → policy forward → `allowed` mask → sample → existing
  `_execute_actions` and biology → reward from the drive deltas → ring buffer; every T ticks one
  synchronous PPO update on the same CUDA stream. No asynchronous learner.

### 1.6 Pre-training ("nursery" worlds) and the canonical run

One 1600-day run gives only 800–2,400 PPO updates and starts from 8 mice: too little to learn
from scratch. Pre-train in nursery worlds seeded with 500–4,000 adults and juveniles, 24
ticks/day, domain-randomised over abundance (food / water refill), density and object count,
for 10^8–10^9 agent-steps; then run the canonical 4-pair world (a) with the frozen net
(`mlp_frozen`) and (b) with learning on at lr 1e-4 (`mlp_ppo`), both against (c) the
`need_driven` control with identical seeds. The nursery start is not Calhoun's start — a stated
limitation. The heuristic is never distilled into the net.

### 1.7 Alternative learner: inherited weights (`evo`)

Each mouse carries its own small net (obs → 32 → 11, about 2 k params; 4,096 slots × 2 k × 4 B
= 32 MB). At birth the child's weights are the mother's (or the parents' mean) plus N(0, 0.02);
no reward, no learner: selection is the existing biology (Hamon, Nisioti & Moulin-Frier 2023;
JaxLife 2024; Polyworld). Pros: H2-clean by construction (there is no reward at all), no PPO
non-stationarity, trivially deterministic (per-agent mat-vec, no atomics). Cons: about 15 mouse
generations in 1600 days is two orders of magnitude fewer than Hamon's about 1,500, so it also
needs pre-evolution in nursery worlds; selection acts through births and deaths, i.e. it is
coupled to the calibrated demography (fecundity-related behaviour can drift; monitor per
generation). This is the arm closest to Auerbach, Kanarek & Burghardt 2015, who evolved rather
than trained.

## 2. Measurement: detectors per Burghardt criterion (eval-only, unvalidated)

Principles. Every detector is computed after the fact from logs (position, action, drives, cell,
object contact) and is never read by a policy or learner (P4-7 audit). Code names avoid
play / bout / motif / exaggeration (`episode_*`, `nf_index`, `seq_struct_*`, `gate_*`). The
output stays a **vector** of five criterion detectors plus their surrogate z-scores; it is not
collapsed into a scalar until the preregistered synthetic validation passes. Thresholds are
fixed here before the first evaluation seed is run. No computational operationalisation of all
five criteria exists in the literature (the closest work either uses a single criterion or a
supervised ethogram classifier, which H1 forbids), so these are proposals, labelled as such.

Episode segmentation. Object-contact episodes (MANIPULATE within an object radius) and
high-speed locomotion episodes (EXPLORE displacement above the 90th percentile of the serious
distribution) are split with a bout-criterion interval from the log-survivorship of the sim's
own inter-event intervals (Slater & Lester 1982; Sibly et al. 1990). Falsifier: no break in the
survivorship curve means no episode structure to score.

| Criterion (Burghardt 2005) | Detector (eval-only) | Falsifier | Main confound |
|---|---|---|---|
| 1 not fully functional | `nf_index`: change in the survival drives (hunger, thirst, fatigue, stress) over the episode plus a short horizon, minus matched non-episode windows of the same agent and drive state; play-like if within the surrogate band and the episode does not end at food, water, nest or a mate. Curiosity and boredom are **excluded** from the functional set, otherwise every episode "functions" to relieve curiosity (the tautology). | episodes reliably reduce a survival drive | delayed function; a learner's value estimate making the episode instrumental — reported, not hidden |
| 2 spontaneous / autotelic | trigger-free onset rate (no neighbour approach, object spawn or drive-threshold crossing within k ticks) vs non-episode actions; voluntary return hazard to the playground with unchanged drives; revealed preference at path-equivalent choice points in sated states. Baseline: a random policy with matched action entropy (the Oudeyer normalisation). Pleasure is not inferable: an autotelic *proxy*. | onsets time-locked to triggers; return hazard at baseline | policy stochasticity looks spontaneous |
| 3 structurally / temporally different from the serious form | serious templates from the sim's own functional sequences (forage → consume, aggress → wound, approach → mate): incompleteness fraction (terminal act available but dropped), amplitude z-scores (speed, turn rate, approach–withdraw cycles), Jensen–Shannon divergence between candidate and serious first-order transition matrices, targeting of non-consumable object parts | divergence within the surrogate band; episodes complete | interruption or failure mimics incompleteness; early-training incompetence mimics precocity — match training stage, classify blocked serious episodes separately |
| 4 repeated but not rigidly stereotyped | recurrence of episodes in a feature space across days above a preset rate; conditional entropy rate and Lempel–Ziv compressibility of within-episode action sequences; rigid-loop fraction (pairs with normalised edit distance below ε); engagement as a function of **cumulative object exposure** (curiosity decays with exposure, play recurs after novelty is exhausted) | episodes not repeated, or compressibility that of a fixed loop | a deterministic policy in a static world loops by construction — report against matched-entropy random policies and over training time |
| 5 relaxed field | `gate_relaxed`: survival drives below their action thresholds, no aggression received in the last m ticks, local density below the crowding threshold, wounds low. Used as a gate **and** a dose–response variable, P(episode | relaxed) vs P(episode | not), never as evidence on its own. | episodes equally frequent under stress | this gate is what manufactures spillover; post-deprivation rebound (Held & Špinka 2011) inflates rates right after stress ends |

Free-choice V hopper fix (measurement bug found 2026-11-04). The playground box (35, 35)–(66, 66)
covers cells 5, 6, 9 and 10 and contains six of their eight hoppers (all four water points, the
food points of 9 and 10) and 16 of the 256 nests, so an agent drinking there counts toward V.
Report `free_choice_V_excl_hopper_unvalidated`, which excludes agents whose current action is
FORAGE or DRINK or who are within the hopper radius; keep the old V for continuity. Moving the
box or the hoppers would change the calibrated redistribution, so the fix is in the metric.

Validation plan (no animal or human play data, ever).
1. **Synthetic ground truth**: scripted non-learning agents inject sequences written from the
   criterion text (incomplete approach sequences, varied object pushes, rigid loops,
   matched-speed random walks, decaying novel-object inspection) and serious completions;
   preregistered minimum ROC-AUC and false-positive rate per detector.
2. **Surrogates**: within-agent time shuffle of actions (should collapse criteria 3 / 4),
   circular shift of drive traces against actions (should collapse 1 / 5 gating), first-order
   Markov surrogates preserving transition frequencies (tests higher-order structure); every
   detector reported as z against at least 1,000 surrogates.
3. **Ablations**: playground off (object detectors → 0, locomotor detectors persist: a
   differential prediction); abundance → scarcity ramp with preregistered monotone direction;
   gate removed (quantifies the gate-driven share); curiosity / boredom drive removed (if all
   episodes vanish the phenomenon is pure drive spillover: a negative result); crowding ramp;
   juvenile vs adult bands.
4. **Non-triviality**: match episodes on drive state (curiosity level, gate status, age). If
   abundance changes criteria 3 / 4 at matched drive states the effect is not spillover by
   construction; if it only changes time spent in the relaxed field, it is.
5. **Thresholds** from surrogate percentiles; literature numbers (rat role reversal ≈ 30 %,
   play ≈ 2–3 % of the daily energy budget) only as orientation, never tuned on sim output.
6. **Agreement**: Cohen's kappa between criterion detectors on episode labels; held-out seeds.

Rodent grounding for the predictions. House mice show only a faint version of play fighting
(attack–defence ≈ 2 % of social play in C57 mice, most social play non-contact locomotion:
Pellis & Pasztor 1999; Wolff 1981), so predicted effects are small and locomotor or
object-based. Rats lose play under 24 h food deprivation (a three-fold drop in pinning, reversed
by a meal: Siviy & Panksepp 1985), under acute restraint stress (Klein, Padow & Romeo 2010) and
under predator cues; social isolation increases it on return (a rebound confound for any
"abundance after scarcity" design). No study scores play under crowding in rodents, and Calhoun
did not score play, so H-g (breakdown suppresses play-likeness) is a prediction, not a
replication.

## 3. Fidelity: landmarks and the record

What the 2026-11-04 review of the record (`RESEARCH_DIGEST.md` part A) changes:

- **The canonical five and the loss are unchanged** (calibration frozen at 2m). Five record
  landmarks were added as **reported-only** values in `metrics/calibration.py`
  (`RECORD_LANDMARKS`, `landmark_notes` in every report): 1871 at day 811 and ≈ 1650 at day 960
  (Marsden 1972), 100 at day 1471 (Calhoun 1973), and the doubling times 55 d (phase B, first
  litters → 315) and 145 d (phase C, 315 → peak day).
- **First litters at 104 is contested.** Calhoun 1971 gives first surviving litters at 50 d,
  both of his figures imply 60–65 d, and 104 cannot be reconciled with 620 at 315 and a 55-d
  doubling. The simulator reaches 102 and sits a third low at day 315: consistent with phase B
  starting ≈ 40 days late. This is the strongest lead on the early-phase miss that phase 2j
  de-weighted. It is **not** applied now; card P0-5 re-anchors phase A at 60 ± 15 as a new
  calibration version (2n) with its own 12-seed evaluation and NOTES entry.
- **≈ 150 mice were removed after day 1000.** The 122 at 1444 and 27 at 1588 are after that
  removal, which the simulator does not model; the no-removal envelope at 1444 is ≤ 272, and
  our 155 ± 29 is inside it. The decline is no longer chased toward 122. An optional
  `removal` event (day, count) for fidelity runs is part of P0-5.
- **Irreversibility is an assumption fitted to one colony.** Kessler 1966's crowded mouse
  populations stabilised and resumed reproduction when re-paired; Hammock 1971's weaned pups
  again after density reduction; Marsden's transfers (Calhoun's own) did not. The phase 2m
  colony-wide exposure encodes Universe 25's outcome and is listed as a model assumption.
- **Not modelled, now documented:** two of four founder males died in the first two months;
  the hoppers and water were moved out of the nest compartments around day 150–175; the
  phase B sex ratio was 40 : 60; 20–30 % of nest boxes were empty at peak; withdrawn mice were
  32 % of a cell at the end of phase C; 53 % of mice entering the adult categories by mid-phase D
  had never fought, mated or nest-built. The last four are candidate validation targets for the
  role and spatial metrics (phase 4 sweeps report them; no fitting).
- **Fidelity ceiling.** The collapse to near-extinction is documented for one colony, never
  replicated, with unresolved disease and genetic confounds and an internally inconsistent
  record. "Perfect" is not definable against it. The operational target is: every documented
  number reproduced within its stated uncertainty, every departure and assumption listed.

## 4. Calibration guard (preregistered, PLAN.md)

For every policy arm, the 12-seed means of the canonical five landmarks (first litters, N@315,
peak N, peak day, cessation of surviving births) and the late tail (N@1444, N@1588) are compared
with the `need_driven` control at the same seeds. **Preserved** means every canonical landmark
within 10 % (relative) and the decline band still met at day 1200. A policy that breaks the
curve is a **result** ("the Calhoun curve is not policy-invariant under drive-reduction
learning"), reported in NOTES.md; the biology is not retuned to rescue it (the calibration is
frozen, phase 2m). A test (`tests/test_policy_calibration_guard.py`, P4-1) runs a 400-day
3-seed version of this check so that drift is caught before a sweep.

## 5. Determinism (two tiers, never cross-tier identity)

- **Reference tier (NumPy, CPU):** `need_driven`, `mlp_frozen` and `evo` are bit-identical run
  to run for a fixed seed (existing `test_determinism`; extend to each kind). BLAS threads
  pinned to 1 for the mat-vecs. Sampling by `searchsorted` on a cumulative softmax with uniforms
  from the policy stream — never `np.random.choice`.
- **GPU tier (torch + Warp):** run-to-run bit-identical on the same GPU / driver / library
  versions: `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `torch.use_deterministic_algorithms(True)` (not
  `warn_only`), cuDNN benchmark off / deterministic on, TF32 off, no `torch.compile`,
  `wp.config.deterministic = wp.DeterministicMode.RUN_TO_RUN` set before any kernel module is
  created, obs / reward kernels written with per-agent writes only (no float atomics; the
  deterministic atomic path costs 10–24× on sparse atomics), GAE as a vectorised backward scan
  over T with per-slot masks (no scatter), minibatch shuffles from a seeded generator. PyTorch
  documents that CPU and GPU results need not match for the same seed, so the docs never claim
  cross-tier identity; a parity test compares argmax agreement under a tolerance.
- Versions (torch 2.11.0+cu128, CUDA 12.8, Warp 1.18.0, numpy 2.5.4 in the omnilab venv) and
  the GPU model go into every run manifest.

## 6. Compute (RTX 5080, one card)

Agent-steps per 1600-day run: about 19–38 M at 6 ticks/day (mean population 2,000–4,000),
about 150 M at 24. Policy forward about 50 kFLOP per agent-step → compute negligible,
latency-bound (30–100 µs per tick); obs + reward build 0.1–0.3 ms per tick; a PPO update
20–50 ms. Learning adds about 1–3 min to a 1600-day run; the run time stays set by the biology
and the host loop (today about 86 s per 1600 d at 6 tpd on the NumPy path). Pre-training at
0.3–1 M agent-steps/s: 10^9 agent-steps in 20–60 min; 10^10 overnight. Budget in PLAN.md.

## 7. Known pitfalls and the mitigation each gets

| Pitfall | Mitigation |
|---|---|
| Reward hacking of one drive; setpoint overshoot | pure drive-reduction reward, per-drive scales, per-drive contribution logged, abs(r) capped at the one-tick physical maximum; modular critic heads as an ablation |
| Entropy collapse / stereotypy | entropy floor, KL early stop, action-entropy and per-agent switch-rate monitors; PlayScore never a training or stopping signal |
| Calibration drift | §4 guard; masks identical to the heuristic; drift reported, biology not retuned; heuristic control at identical seeds |
| Non-stationarity (8 → 4,000 → 30 agents; drifting density) | per-sample loss normalisation, value normalisation, age and density in obs, lr decay, fixed tick horizon with variable N, nursery warm start |
| Built-in result (under abundance only social / stimulation drives carry gradient) | test structure (criteria 3 and 4), not only frequency; compare learned vs heuristic with identical drive definitions; scarcity arm |
| Nursery mismatch | domain randomisation; evaluate on the canonical 4-pair start; state as limitation |
| Evolution-driven demographic drift (`evo`) | per-generation fecundity monitor; §4 guard |
| Seed variance | at least 5 seeds per condition before any abundance-vs-survival comparison; 12 for the calibration guard |

## 8. Task breakdown (cards in `docs/TASKS.md`)

P4-0 observation builder + `mlp_frozen` (NumPy) + determinism test · P4-1 calibration guard ·
P4-2 homeostatic reward + PPO learner (torch) + GPU determinism recipe · P4-3 nursery
pre-training harness · P4-4 `evo` policy · P4-5 Burghardt detectors + synthetic-ground-truth
validation + V hopper fix · P4-6 sweep harness (abundance × playground × policy kind × seeds)
· P4-7 H2 audit extension (obs / reward kernels). Order: P4-0 → P4-1 → P4-5 → P4-2 → P4-3 →
P4-6, with P4-4 in parallel after P4-1.
