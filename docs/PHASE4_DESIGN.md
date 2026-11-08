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
| `mlp_frozen` | NumPy float32 MLP inference (48 → 128 → 128 → 11), weights from an `.npz` or a seeded orthogonal init; learning off | own `make_rng(seed + 1_000_003)` stream; keeps its own cell counts (never the simulation's per-tick cache; fixed 2026-11-06) | done (P4-0, 2026-11-04) |
| `mlp_ppo` | same net, PPO updates every `rollout_ticks` decisions in torch (CUDA); sub-steps re-chosen; eight-drive reward | init from a seeded torch.Generator; sampling from `seed + 1_000_003` (decisions) or the sub-step stream; minibatches `seed + 4_000_003` | done (P4-2, 2026-11-06) |
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

**Amended 2026-11-06 (Jason): eight drives.** `maternal_need` (agents/drives.py) — for a
female in the nursing role, the mean hunger of the pre-weaning pups in her nest box — joins
the seven below in D (D_MAX = √8) and is the 49th observation value (observation v2). The
biology does not read it. Entropy coefficient 0.05 (§1.5). With both, the learner nurses like
the heuristic and keeps a full-size colony (NOTES 2026-11-06, maternal drive).

**P4-2 finding (2026-11-06): the seven-drive reward produces no maternal care.** In a 450-day
nursery the learner never chose NURSE or NEST for nursing mothers, mothers sat a median 48 in
from their nest, and 1.5 % of pups survived (no-update network 13 %, heuristic 15 %). Nursing
relieves none of the seven drives. Options, decision pending (NOTES 2026-11-06 → P4-2):
(1, recommended) an eighth, maternal-motivation drive for lactating females set by their own
pre-weaning pups' hunger — physiology unchanged, only the learner's motivation, still
drive-only; (2) a maternal reflex in physiology for every policy; (3) no change, report the
collapse as the H-d result. Any change amends this section before a learned arm is judged.
Decision: option 1 adopted the same day.

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
  Entropy coefficient changed to **0.05** (2026-11-06, training seed 7000): at 0.01 the shared
  policy learned during gestation, before any litter exists, that the nest never pays and
  never rediscovered nursing (P(NEST), P(NURSE) for mothers 0.003 / 0.005 vs 0.10 at init).
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

**P4-3 result (2026-11-06).** The harness is built (`learn/nursery.py`; 6 decisions per day
with 12 sub-steps rather than 24 ticks per day). Pre-training v1 (10^8 steps) learned maternal
care, but its nurseries always started spread over all 16 cells: on the canonical 4-pair start
the frozen policy keeps the colony in the founders' four cells and it plateaus near 960. The
nursery distribution must include founding colonies (few founders, one to four cells) before
its weights stand for the canonical start (NOTES 2026-11-06 → P4-3). Done in v2 (2026-11-07):
founding worlds in 40 % of episodes; the v2 policy spreads the canonical colony and runs the
Universe 25 arc at full size, about 100 days early (NOTES 2026-11-07).

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

**Preregistered decision rules (v1, fixed 2026-11-06 before the synthetic test run and before
any evaluation seed; implemented in `src/universe25/metrics/detectors.py`).** Every rule pairs
a surrogate test with an effect-size floor, so a large window cannot pass on significance alone.
z is (observed − surrogate mean) / surrogate sd with ≥ 1,000 surrogates; NaN reads as not met;
fewer than 10 episodes of a kind = criteria not evaluated (all False).

| Criterion | Flag is True when |
|---|---|
| 1 not fully functional | `nf_index` ≥ 0.5 **and** z > 1.645 against a circular shift of the per-step relief / at-target series within individual |
| 2 spontaneous | **not** time-locked: it fails only if the trigger-free onset fraction is < 0.8 × its circular-shift null mean **and** z < −1.645 (triggers = cell entry, own-cell density rise > 0.1 of design capacity, wound increase > 0.01, at or one decision before onset) |
| 3 structurally different | within-episode approach–withdraw reversal fraction (radial direction to the sequence's own end point, moves of > 1 in) ≥ 0.25, **and** ≥ 0.2 above that of serious FORAGE / DRINK runs (a direct move has no reversal pair and counts as 0), **and** z > 1.645 under label permutation over sequences |
| 4 repeated, not rigid | fraction of same-individual episode pairs (≥ 2 symbols) with normalised edit distance < 0.2 is ≤ 0.2, **and** the slope of log onset rate on log(1 + cumulative exposure) is > −0.5 |
| 5 relaxed field | log P(onset relaxed) / P(onset not relaxed) ≥ ln 2 **and** z > 1.645 against a circular shift of the relaxed flag (relaxed = hunger < 0.5, thirst < 0.5, energy > 0.5, stress < 0.4, wounds < 0.3, no wound in the last 6 decisions, own-cell density < 1) |

Episodes: gap criterion from the broken-stick fit of the log-survivorship of inter-event gaps
(BIC margin 2, capped at one day of decisions); no break → runs of consecutive events and
`episode_structure_unvalidated = False`. Locomotor events: EXPLORE moves above the 90th
percentile of serious (FORAGE / DRINK / NEST) displacement in the same trace.

Development and test split. The rules above were shaped on one synthetic colony per class
(seeds 100–106, `metrics/synthetic_traces.py`); three changes were made there and are recorded
here: (a) each criterion got an effect-size floor (significance alone flagged every class once
hundreds of sequences were pooled); (b) criterion 3 moved from a movement-transition JS
divergence (still reported) to the approach–withdraw reversal fraction, because the JS compared
sequence-length compositions rather than form and because at 6 decisions per day serious moves
reach their target in one step, so there is no multi-step serious form to compare transitions
against; (c) criterion 4's strings are object-centred for object episodes. The test run uses
fresh seeds (10,000 + 1,000 × class + colony). **Preregistered pass per criterion and episode
kind:** AUC ≥ 0.80 of the statistic between `all_criteria` (the class built to meet all five) and the class built to violate that
criterion (c1 / c3: `serious`; c2: `triggered`; c4: `rigid_loop` for rigidity, `novelty` for the
exposure slope; c5: `stressed`), flag rate ≥ 0.80 on `all_criteria` colonies (TPR) and ≤ 0.10 on
the violating class (FPR). `random_walk` (a matched-speed random policy) is read against every
criterion and has no pass condition: it shows what a policy without structure scores.

**v1 test result (2026-11-06, seeds 10,000 + …, 30 colonies per class, 1,000 surrogates):
11 of 12 checks pass** (AUC 0.98–1.00, TPR 1.00, FPR 0.00–0.07); **criterion 3 on object
episodes fails** (AUC 0.58, FPR 0.77 on `serious`). Mechanism: the gap criterion found a break
on the functional class and merged single consumption acts up to a day apart into one episode;
the form statistic then read the trips home and back between them as approach–withdraw cycles.

**v2 (fixed 2026-11-06 after the v1 test, before the v2 test).** One change: the form
statistics (criterion 3 reversals, JS and amplitude; criterion 4 strings and entropy rate) use
only the episode's own event decisions, and a transition or direction pair exists only between
two consecutive event decisions; the other actions inside an episode's gap no longer count.
All thresholds unchanged. v2 is tested on a new fresh split (seeds 20,000 + 1,000 × class +
colony), never used before; the v1 result above stays the record of v1.

**v2 test result (seeds 20,000 + …): 12 of 12 checks pass.** But the episode falsifier failed
in the unit test written afterwards: on purely memoryless (Bernoulli) events the broken-stick
least-squares fit on the log-survivorship still reported a break (capped at 6 decisions),
because unweighted least squares on log S(t) treats a sparse tail point like a dense one. The
same defect produced the v1 merges.

**v3 (fixed 2026-11-06 after the falsifier failure, before the v3 test).** One change: the gap
criterion is a maximum-likelihood comparison of one geometric process against a two-component
geometric mixture on the inter-event gaps within individuals (Sibly, Nott & Fletcher 1990;
EM fit), BIC margin 10, distinct rates (fast > 2 × slow) and both components > 2 %; the
criterion is the gap that minimises the expected misassigned gaps (Slater & Lester 1982),
capped at one day of decisions. On memoryless events at rates 0.05–0.5 it reports no structure;
on planted runs separated by long pauses it reports a criterion of 2. Everything else as v2. v3
is tested on a new fresh split (seeds 30,000 + 1,000 × class + colony).

**v3 test result (2026-11-06): 12 of 12 checks pass** (AUC 0.993–1.000, TPR 1.00, FPR 0.00 on
every check, both episode kinds; `_output/detector_validation.json`). v3 is the frozen rule
set for phase 4; any later change is v4 and needs its own fresh split. Limit: the synthetic
classes and the detectors come from the same hand, so this shows the detectors compute what
the criteria say, not that they would recognise real play.

**v4 (fixed 2026-11-07 before the v4 test; card P4-9).** Two changes, motivated by simulator
traces with free-time sub-steps (never used to tune a threshold):
1. *Phase-preserving surrogate shifts.* With K sub-steps per decision (`free_substeps`, from the
   trace meta), the circular shifts behind criteria 1, 2 and 5 move each series by a whole number
   of decisions (a random multiple of K rows), not an arbitrary number of rows. Density and wound
   triggers, relief and the relaxed flag update once per decision, so an arbitrary shift moved
   them off the decision-boundary rows and made any behaviour whose onsets fall on decision
   boundaries read as trigger-locked. With K = 1 the shift and its random draws are exactly v3's.
2. *Minimum support for the serious template.* The serious runs' reversal fraction counts as 0
   below 20 direction pairs (in the observed statistic and in every permutation), instead of
   resting on a handful of pairs.
3. *Trigger window counted in decisions* (added after a development look at one colony per
   sub-step class, seed 101, before the test): a trigger counts for an onset if it falls between
   the start of the previous decision and the onset row, inclusive. An object episode's first
   contact comes several sub-steps into its decision, after the approach, while triggers sit on
   the decision's first row, so the v3 window (the onset row or the one before) missed them. With
   K = 1 the window is exactly v3's.
All thresholds and every other rule unchanged. Test on a fresh split (seeds 40,000 + 1,000 ×
class + colony), with the 12 v3 checks plus two sub-step checks (criterion 2, episodes of K = 12
rows, onsets only on decision boundaries): `all_criteria_k12` (onsets independent of triggers)
must be flagged spontaneous in ≥ 80 % of colonies and `triggered_k12` (onsets after a trigger) in
≤ 10 %, with AUC ≥ 0.80 between them. Sub-step classes are the K = 1 classes expanded to 12 rows
per decision the way the trace recorder writes non-free decisions (positions interpolated,
drive change on the last row, triggers on the first).

**v4 test result (2026-11-08, seeds 40,000 + …, 30 colonies per class, 1,000 surrogates):
14 of 14 checks pass** — the 12 v3 checks (AUC 0.983–1.000, TPR ≥ 0.97, FPR 0.00) and both
sub-step checks for criterion 2 (object and locomotor: AUC 1.00, TPR 1.00, FPR 0.00;
`_output/detector_validation_v4.json`). v4 is the frozen rule set. Recorded limit: the
expanded classes lose criterion 3 (decision-level approach / withdrawal stretched over 12
interpolated rows becomes 12-row runs in one direction), so at the sub-step grain criterion 3
detects alternation only when it happens between sub-steps — which a learner at that grain
can produce and stretched decision-level behaviour cannot.

**v5 (fixed 2026-11-08 after the v4 simulator reading, before the v5 test; card P4-10).** One
change, to criterion 2's trigger set: a trigger is an exogenous event only — aggression
received (wounds rise between decisions), or a local density jump in the cell the individual
occupied at the start of its previous decision (others arrived). Entering a new cell, and a
density jump that comes with it, is the individual's own doing — in the simulator every cell
change is the agent's own movement, the WITHDRAW drift, or a mother's return to her nest at a
birth — and no longer counts. Under v4, an object episode's approach crosses into a playground
cell a few sub-steps before first contact, inside the trigger window, so every arm read
"locked" (NOTES 2026-11-08). The synthetic classes never change cell, so their trigger series
and every v4 check are unchanged. Test on a fresh split (seeds 50,000 + 1,000 × class +
colony): the 14 v4 checks plus two mobile checks for criterion 2 at K = 12 —
`all_criteria_mobile_k12` (onsets independent of exogenous triggers, in an arena split into
2 × 2 cells with the objects in a denser cell of their own, so most object onsets follow the
individual's own entry into that cell inside the trigger window) must be flagged spontaneous
in ≥ 80 % of colonies and `triggered_mobile_k12` (same world, onsets after an exogenous
trigger) in ≤ 10 %, with AUC ≥ 0.80 between them. Mobile classes record the cell of each
row's start position the way the trace recorder does. Diagnostic, not a pass criterion: the
v4 trigger set on `all_criteria_mobile_k12`, which should reproduce the simulator's false
locking. Everything else is v4.

**v5 test result (2026-11-08, seeds 50,000 + …, 30 colonies per class, 1,000 surrogates):
16 of 16 checks pass**, every AUC 1.000, TPR 1.00, FPR 0.00 — the 14 v4 checks and both mobile
criterion-2 checks (`_output/detector_validation_v5.json`). Development look before the test:
seeds 101–103 only, which confirmed that the old classes' trigger series are identical under v4
and v5. Diagnostic: with the v4 trigger set, `all_criteria_mobile_k12` object onsets read
locked in 30 of 30 colonies (AUC 0.71 against `triggered_mobile_k12`); locomotor onsets were
not affected (a run starts where the individual stands). So the synthetic mobile world
reproduces the simulator's false locking, and v5 removes it without losing true locking. v5 is
the frozen rule set.

**v6 (fixed 2026-11-09 after the H-e reading, before the v6 test; card P4-11).** One change:
criteria 3 and 4 both require a form beyond chance. Under v5 the random-init network and the
heuristic met criteria 1–4 for locomotion in every window (NOTES 2026-11-08). The development
look (synthetic seeds 101–103 and the P4-8 traces of training seeds 7000–7002, never an
evaluation seed) found why. In the simulator every EXPLORE sub-step is an isotropic Gaussian
step, so turn classes come out at 0.25 / 0.25 / 0.25 / 0.25 with no sequential structure, for
every policy. Locomotor "episodes" are therefore random walks. A random walk meets v5's
criterion 3 (about half of its direction pairs reverse relative to the end point, against none
for direct serious runs) and criterion 4 (never rigid, no habituation). Neither criterion asked
for structure beyond chance, although item 2 of the validation plan below says a
within-individual time shuffle should collapse both.
- *Form test.* The episodes' approach–withdraw reversal fraction (criterion 3's statistic)
  against a within-episode order shuffle of the same direction labels. Each episode's own event
  decisions keep their positions, and their approach / withdraw / neutral labels are permuted,
  1,000 shuffles on a random stream of their own, so every v5 statistic is unchanged. Excess =
  observed − shuffle mean, and z is taken against the shuffles. The form test is met when the
  excess is ≥ 0.10 and z > 1.645 (floor: a tenth of the direction pairs more reversals than the
  same moves in chance order).
- *Criterion 3* = v5 criterion 3 and the form test. *Criterion 4* = v5 criterion 4 and the
  form test: a behaviour repeated "in a similar form" must have a form, and an order-shuffled
  copy of a random walk is the same random walk.
- Criteria 1, 2 and 5 are unchanged. They are absence or gating criteria, which random
  behaviour meets or fails on its own merits (it is non-functional and untriggered). This is
  recorded, not changed. The output keeps the v5 flags (`decisions_v5_unvalidated`) for
  continuity.

Development values of the excess:
- `all_criteria`: 0.17–0.21 (both kinds, z 5–8).
- `random_walk`: −0.03 to +0.05.
- Simulator random network and heuristic, both kinds: ≤ 0.03, with z up to 4.8 at thousands of
  pairs (hence the floor).

Test on a fresh split (seeds 60,000 + 1,000 × class + colony, 30 colonies per class, 1,000
surrogates). Pass conditions:
- The 16 v5 checks, scored with v6 flags.
- Two random-walk checks, locomotor episodes only (`random_walk` has no object episodes). AUC
  ≥ 0.80 of the form excess between `all_criteria` and `random_walk`, and criterion 3 and
  criterion 4 flags each met in ≥ 80 % of `all_criteria` colonies and ≤ 10 % of `random_walk`
  colonies.
- A simulator negative control (`scripts/negcontrol_v6.py`): random-init networks of the learned
  net's architecture (`MlpFrozenPolicy.random_init`, init seeds 7001 and 7002, never used) on
  training seeds 7003–7005 (never traced). K = 12, 1,010 days, windows at days
  400 / 700 / 1000, every fourth individual, ≤ 400 individuals, 1,000 surrogates. Criterion 3
  and criterion 4 flags must each be met in ≤ 10 % of the 18 windows per kind.

Diagnostic, not a pass condition: v5 flags on the same traces.

Known limits, recorded before the test:
- The form test detects one kind of form, approach–withdraw alternation. A play form without
  alternation (a stereotyped circuit, repeated straight dashes) fails it.
- In this simulator no policy controls the path of a move: EXPLORE is a Gaussian step and
  MANIPULATE a straight approach to the nearest object. Path-form criteria can therefore reflect
  a policy only through the order in which it chooses actions.

**First simulator reading (training seeds 7000–7002, 4 windows).** Need-driven and random
policies: object and locomotor episodes are non-functional (c1) and spontaneous (c2) but last
one decision (mean 1.00–1.04 events), so c3 / c4 are not evaluable (≤ 21 direction pairs, ≤ 2
comparable episode pairs per window) and c5 is not met (log ratio below ln 2). Playground off:
object episodes vanish, locomotor persist. At 6 decisions per day no policy can show
within-episode form; card P4-8 adds a free-time sub-step layer (biology untouched) before any
H-f test. Known v3 limitation to fix in v4 if needed: the serious template's reversal fraction
has no minimum support (in the simulator it rests on one pair).

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

## 2b. Free-time sub-steps (P4-8, 2026-11-06)

At 6 decisions per day every episode in the simulator lasted one decision, so criteria 3 and 4
had nothing to measure for any policy. `free_substeps: K` replays a free decision (EXPLORE /
SOCIAL / MANIPULATE) as K sub-steps, each moving 1/K of a decision's reach with 1/K of the
relief, after the decision itself has executed (so the biology's random stream is unchanged;
sub-steps draw from their own). Feeding, nursing, conception, stress and mortality stay per
decision. `policy.substep_mode`: `continue` (the decision action at every sub-step; the
heuristic's default, because its motives exist only at the decision grain and re-choosing moved
the calibrated arc) or `rechoose` (the policy chooses among the free actions at every sub-step;
the default for learned kinds, which is what lets a learner show within-episode form). Learned
arms run at K = 12 (20-minute sub-steps) and are compared with the random frozen MLP at the
same K. Guard and baseline readings: `NOTES.md` 2026-11-06 → P4-8.

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
with the `need_driven` control at the same seeds. **Preserved** means no canonical landmark
drifts more than 10 % (relative) with a paired arm − control difference beyond 2 paired se
(H-d as amended 2026-11-06: at 12 seeds the paired se of N@315 is 12–16 % of its mean, so a
10 %-only rule could not resolve it), and the decline band still met at day 1200. The original
10 %-only reading is reported alongside. A policy that breaks the
curve is a **result** ("the Calhoun curve is not policy-invariant under drive-reduction
learning"), reported in NOTES.md; the biology is not retuned to rescue it (the calibration is
frozen, phase 2m). A test (`tests/test_policy_calibration_guard.py`, P4-1) runs a 400-day
3-seed version of this check so that drift is caught before a sweep.

**First measurement (2026-11-04, `scripts/policy_guard.py mlp_frozen --weights
_output/policy_random_7000.npz`, seeds 8000–8011, 1600 d).** The need-driven control
reproduces the record on seeds it had never seen (peak 2252 ± 13 at 534 ± 7, cessation 593 ± 8,
N@1444 127 ± 8, N@1588 19 ± 2). A fixed random MLP (near-uniform over the eligible actions) is
**not preserved**: N@315 −61 %, peak −11 % and +240 d, surviving births +560 d, conceptions
+410 d, N@1444 ×5, N@1588 ×20. The behavioural sink needs the heuristic's attraction to
hoppers, nests and partners; spread uniformly the colony never concentrates enough for the
breakdown to complete. So the calibration is "biology + heuristic behaviour", H-d is
falsified for an arbitrary policy, and the random arm is the baseline bounding what a learned
policy may do (`NOTES.md` 2026-11-04 → P4-1).

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
