# Research digest — the Calhoun record, learning agents, play detection (2026-11-04)

Three web-research passes (primary sources read in full where reachable; items the sources did
not give are marked *inference* or *abstract only*) plus a code map of the simulator, made to
answer one question: **how far can this simulator be taken toward a faithful Universe 25 with
learning agents, and what does "faithful" even mean against the record?** Design decisions drawn
from it are in `docs/PHASE4_DESIGN.md`; the preregistration is `PLAN.md` §15.

The short answer: the record is one colony, reported by one author in two partly inconsistent
papers, never replicated; two of the eight landmarks the simulator has been tuned to are
contested or confounded by the record itself; and nothing in the literature operationalises
Burghardt's five criteria computationally, so the play detectors have to be proposed and
validated synthetically. "Perfect" is not definable here. "Every documented number within its
uncertainty, every assumption listed" is.

---

## Part A — The Calhoun record

### A1. What was read

Calhoun 1973 "Death Squared" (*Proc R Soc Med* 66: 80–88) in full with the figures
re-rendered and Fig 2 digitised; Calhoun 1971 "Space and the Strategy of Life" (Esser ed.,
*Behavior and Environment*, pp. 329–387); Calhoun 1962 *Scientific American* (rats); Marsden
1972 "Crowding and Animal Behavior" (Wohlwill & Carson eds.); Kessler 1966 (Rockefeller PhD
thesis); Ramsden & Adams 2009 (*J Social History* 42: 761–792) and the LSE working paper; Day
2025 (*LRB*); Gwern "Does Mouse Utopia Exist?". Not reachable: Southwick 1955, Christian 1956,
Hammock 1971 full texts (abstracts only), Universes 33 / 34 (unpublished; one secondary snippet).

Calendar check: day 0 = 9 Jul 1968; day 600 = 1 Mar 1970 (matches "last born"); day 1444 =
22 Jun 1972; day 1588 = 13 Nov 1972; 23 May 1973 = day 1779 (Calhoun writes 1780).

### A2. Core timeline (primary: Calhoun 1973 unless noted)

| Landmark | Value | Day | Source | Confidence |
|---|---|---|---|---|
| Colonisation | 4 pairs BALB/c, 48 days old | 0 | 1973 p. 82 | high |
| Founder male deaths | 2 of 4 founding males died "within the first two months" (fighting stress) | < ~60 | 1971 p. 337 | high — **not modelled** |
| First litters | 104 (end of phase A) | 104 | 1973 p. 82 | **contested**, see A5 |
| Hoppers and water moved out of the nest compartments (fouling) | environment reconfigured | ≈ 145–175 (Dec 1968) | 1971 p. 339 | high — confound |
| Phase B doubling time | ≈ 55 d (20, 40, 80, 160, 320, 620) | 104–315 | 1973 p. 83 (1971: 56-d five-universe mean) | high |
| End of phase B | 620 weaned mice; 14 social groups; 150 adults + 470 immature | 315 | 1973 p. 84; Marsden Fig 2 | high |
| Births by brood group, days 86–338 | 842 young in 14 groups: 111, 107, 91, 89, 83, 80, 69, 66, 50, 27, 22, 17, 17, 13 | 86–338 | 1973 Fig 3 | high |
| Phase C doubling time | ≈ 145 d for 245 d | 315–560 | 1973 p. 84 (1971: 105-d mean; ≈ 136 d digitised for Universe 25) | medium |
| Mid-phase C | essentially all young prematurely rejected by mothers | ≈ 437 | 1973 p. 85 | medium |
| Peak | 2200; 20 % of the 256 nest boxes usually unoccupied (1971: 30 % empty or with 1–2 mice; some mice suffocated in crowded boxes) | 560 | 1973 Fig 2, p. 82, p. 85 | high |
| Last surviving birth | 1 Mar 1970; between 560 and 600 deaths slightly exceeded births | 600 | 1973 p. 85, Fig 2 | high |
| Reproductive death "predicted by" | | 700 | 1973 p. 85 | high |
| Census | 2056 | 736 | 1973 Fig 2 | high |
| Census | 1871 | 811 | Marsden 1972 Fig 2 | high — **new** |
| "At this writing" | ≈ 1,800 adults, no young | ≈ 870 | Marsden 1972 p. 9 | medium |
| Last conception | ≈ 920 | ≈ 920 | 1973 p. 85 | high |
| Census | ≈ 1,650 | 960–965 | Marsden 1972 fn. 2, Fig 2 | high — **new** |
| Removal for other studies | ≈ 150 mice removed | after 1000 | 1973 Fig 2 caption | high — **confound, not modelled** |
| Mean age of survivors | 776 d (the "776 days" bar in Fig 2 is an age, not a count) | 1331 | 1973 p. 85 | high |
| Census | 122 (22 M, 100 F) | 1444 | 1973 p. 85 | high |
| Census | 100 | 1471 | 1973 Fig 2 caption | high — **new** |
| Final census | 27 (23 F, 4 M); youngest > 987 d old | 1588 | 1973 Fig 2 caption | high |
| Last male death | 23 May 1973 — a **projection** | 1780 | 1973 p. 85 | no observed extinction date exists |
| Female menopause | ≈ 560 d of age | — | 1973 p. 82 | medium |
| Longevity | "large numbers" lived to 800 d | — | 1973 p. 82 | medium (loosely supports 780 ± 150) |
| Sex ratio, phase B | 40 M : 60 F across the five universes | ≤ 315 | 1971 p. 341 | medium |

Digitised Fig 2 points after day 736 (± 10 d, ± 5–8 %): 797 / 1890, 896 / 1810, 957 / 1620,
1014 / 1520, 1031 / 1270 (the drop matches the ≈ 150 removal), 1213 / 690, 1270 / 500,
1340 / 350. Terminal decline rate 0.009–0.0105 per day (half-life 66–74 d) from 1340 to 1588.

### A3. The sibling universes (Calhoun 1971 Fig 3; T = days after the first surviving litter)

| Universe (cells) | end B (T, N) | end C (T, N) | later (T, N) | final mice / cell |
|---|---|---|---|---|
| 1 cell | ≈ 142, 60 | ≈ 293, 181 | ≈ 498, 185 | 180 |
| 2 cells | ≈ 150, 113 | ≈ 298, 340 | ≈ 602, 330 | 175 |
| 4 cells | ≈ 230, 143 | ≈ 453, 507 | ≈ 573, 490 | 130 (pathological founder male) |
| 8 cells | ≈ 190, 240 | ≈ 378, 1120 | ≈ 513, 1100 | 142 |
| 16 cells (U25) | ≈ 251, 640 | ≈ 493, 2200 | ≈ 692, ≈ 2250 | 138 |

Calhoun's own 1968 predictions (terminal totals 250, 230, 205, 168, 110) were falsified. The
four smaller universes plateaued and were terminated; **the collapse to near-extinction is
documented for n = 1**.

### A4. Apparatus constants

Square side 101 in (2.57 m), walls 54 in; 16 cells, each with a 640 sq in floor; 4 mesh
tunnels per cell with 4 nest boxes each → 256 boxes × 15 mice = 3840 shelter capacity; one
6 × 10 in hopper per cell (25 feed at once) → food limit 9500; water for 6144; 20–32 °C;
bedding changed every 4–8 weeks, never sterilised; one negative salmonella culture at peak; no
predators. Calhoun's design units: optimum 10 adults per cell, territories ≈ 1.5 cells, a basic
group of 1 territorial male + 3 subordinate males + 6 females.

### A5. What this does to our landmarks

| Ours | Verdict |
|---|---|
| first litters 104 | 1973 says 104; 1971 says first surviving litters at 50 d, both of Calhoun's figures imply 60–65 d, and his own doubling arithmetic (20 → 620 in "nearly five doublings" of 55 d = 275 d) cannot fit a 211-day window. **The simulator reaches 102 and is a third low at day 315 (409 ± 45 vs 620): consistent with phase B starting ≈ 40 days late.** Target should read 50–104 (60 ± 15 preferred). Calibration follow-up P0-5, not applied now (calibration frozen). |
| 620 at 315, 150 adults | confirmed (+ 470 immature) |
| peak 2200 at 560 | confirmed; add 20–30 % of nest boxes empty at peak |
| last surviving birth 600 | confirmed |
| 2056 at 736 | confirmed; add 1871 at 811, ≈ 1650 at 960 (reported-only record landmarks) |
| last conception ≈ 920 | confirmed |
| 122 at 1444 | confirmed, but **after ≈ 150 mice were removed after day 1000**. A run without removal should sit above 122 and 27; our 155 ± 29 at 1444 is inside the no-removal envelope (≤ 272). Do not chase 122. |
| 27 at 1588 | confirmed (23 F, 4 M); add 100 at 1471; never cite 23 May 1973 as an observed extinction |

### A6. Countable phenomena (future validation targets for role and spatial metrics)

- Phase B: 14 brood groups, > 10 per group, 150 adults vs 470 young; sex ratio 40 : 60.
- End of phase C: withdrawn mice = 32 % of a cell's 142; 60 % of the population immature;
  ≤ 10 mice per cell retained normal adult behaviour; pooled withdrawns in the floor centre,
  wounded by other withdrawns; solitary withdrawns on hopper tops.
- Mid-phase D: 53 % of mice entering the adult categories (131–320 d) had never fought,
  mated or nest-built ("beautiful ones"); unstressed by PNMT assay; female counterparts in
  the upper boxes, not aggressive.
- Phase C: territories shrink to < 12 in around the ring stands; nursing females wound and
  expel their own young days before weaning.
- Calhoun's age categories (days): preweaning 1–30, juvenile 31–70, subadult 71–130,
  establishing adult 131–210, adult 211–320, declining 321–450, senescent 451+.
- Parallel 2-cell universe: of 148 females born in the last 50 d of phase C, 18 % had ever
  conceived at median age 334 d, 2 % pregnant with single embryos.
- Marsden's transfers: 16 F + 8 M left from ≈ 300 → zero sex, pregnancies or pups in 60 d;
  with 8 competent stock males, 6 of 16 females conceived, 3 littered, 5 pups of ≈ 100
  potential survived to day 14; males from each behavioural category in fresh 4-cell universes
  → ≤ 1–2 per group retained effective sexual behaviour.
- Calhoun 1962 (rats; secondary validation only): behavioural sink with up to 60 of 80 rats
  feeding in one pen; infant mortality up to 96 % in the most disordered groups vs 80 % for
  comparable animals in a series without a sink (not pen-level rates; corrected 2026-11-17,
  `docs/PRIOR_WORK.md`).

### A7. Confounds, critiques, replication

- Internal: inbred BALB/c (mutational meltdown never tested); bedding never sterilised, one
  culture; mesh hopper designed to permit the sink; mid-run reconfiguration; ≈ 150 removed;
  observer disturbance caused litter abandonment; n = 1 for the collapse; 1971 and 1973 disagree
  on first-litter day (50 vs 104) and phase C doubling (105 vs 145); the extinction date is a
  projection.
- External: J. Z. Young, who chaired Calhoun's Royal Society of Medicine talk (via Ramsden &
  Adams 2009; listed earlier as "Young 1972", which is not a publication we could find;
  corrected 2026-11-17), Freedman 1975, Fischer / Baldassare / Ofshe 1975 on extrapolation and
  anthropomorphism; Kessler 1966 found **withdrawal and declining interaction**, not rising
  stress, in his crowded mouse populations.
- Replication: **none.** Kessler 1966: two freely growing mouse populations reached ≈ 1000 and
  ≈ 800 in 8–9 months, then **stabilised**, and mice re-paired in cages **resumed
  reproduction** — the opposite of Universe 25's irreversibility. Hammock 1971: crowded groups
  weaned no pups; the one thinned group then weaned 41 % / 30 % / 0 % of successive litters, and
  the uncrowded control also stopped weaning once it filled its apparatus. Petrusewicz: transfer
  renewed growth in 43 of 54 populations (1957); disturbance in 65 % of 264 runs against 32 % of
  controls (1963). Terman 1968 / 1973 (deermice): breeding stopped at the plateau, and removed
  animals recovered. Universes 33 / 34 unpublished. (Hammock, Petrusewicz and Terman corrected or
  added 2026-11-17; the wider literature is in `docs/PRIOR_WORK.md`.)

**Consequence for phase 2m.** The colony-wide developmental exposure that makes our collapse
irreversible encodes Universe 25's outcome (and Marsden's transfers); Kessler's and Hammock's
colonies recovered. Irreversibility is therefore a **model assumption fitted to one colony**,
listed as such in NOTES.md and HANDOFF.md.

---

## Part B — Learning agents inside a fixed biology

### B1. Homeostatic reinforcement learning

Keramati & Gutkin 2014 (*eLife* 3: e04811): internal state H, setpoint H*, drive
D(H) = (Σ_i |h_i* − h_i|^n)^(1/m), reward r_t = D(H_t) − D(H_{t+1}); with γ < 1 any policy
maximising discounted reward also minimises the discounted sum of deviations; the phenomena
need n > m > 1 (their Fig 6: n = 4; Dulberg et al. 2023 used n = 4, m = 2). The model
reproduces anticipatory responding, deprivation-scaled reward, inhibition of one need by
another's drive, risk aversion, satiation — and **overeating only when a drive-independent
"palatability" term is added** (the reward-hacking warning). Continuous-time variants
(Laurençon et al. 2021; CTCS-HRRL 2024) note that HRL struggles as the number of internal
variables grows. Dulberg et al. 2023 (*PNAS*): a **modular** agent (one learner per internal
variable, action = argmax of summed Q) reaches homeostasis faster, does not overshoot and
needs no exploration schedule, whereas a monolithic DQN overshoots. Yoshida et al. 2021 / 2024 /
2025: the drive-difference reward performs best in deep RL; integrated multi-need behaviour and
"autonomous exploration" without extra bonuses (*abstracts only* for 2024 / 2025).

### B2. Intrinsic motivation that is not a play reward

Prediction-error curiosity (Pathak 2017 ICM; Burda 2018 RND) is cheap but fixates on
unpredictable input ("noisy TV"; Burda et al. report a random-noise source "does ruin the
performance of the curious agents"). In a colony the least predictable input is *other mice*,
so ICM / RND would pull agents into crowds and corrupt the density-driven calibration
(*inference*). Count / novelty bonuses (Bellemare 2016; Tang 2017) are O(1) per step and can be
per-agent (habituation). Learning progress (Oudeyer & Kaplan 2007; Schmidhuber) fixes the
noise problem at the cost of per-region bookkeeping. Empowerment (Klyubin 2005; Salge 2014)
costs exponentially in the horizon (11^n action sequences) — too expensive per tick at 4,000
agents. Boredom fits cleanly as a homeostatic variable. **Decision:** no separate bonus;
curiosity and boredom stay inside the drive vector.

### B3. Scaling to thousands of agents

MAPPO (Yu et al. 2022): parameter sharing is decisive for homogeneous agents (SMAC 6h_vs_8z:
88 % shared vs 11 % separate); value normalisation, ≤ 10 epochs, clip ≤ 0.2, large batch; nets
2 × 64 + GRU-64; death masking for dead agents. IPPO (de Witt 2020) is competitive with local
critics. Throughput reference points: Neural MMO 2.0 ≈ 3 k agent-steps per core per second;
PufferLib 13 k (Neural MMO) to 460 k (CartPole) on a 24-core i9 + 4090, "1–4 M sps" headlines;
Isaac Gym 540 k sps (Ant, A100, 4,096 envs); JaxMARL 4 × 10^7 random-action sps at 10 k envs;
WarpDrive millions sps with all data GPU-resident. Common pattern for one population in one
world: flatten all alive agents into one batch, one shared policy, observations and rewards as
GPU tensors, variable agent counts by padding + validity masks.

### B4. Evolution across generations

Auerbach, Kanarek & Burghardt 2015: asexual semelparous agents, rest vs forage, resources
decline within a generation; "play" is a heritable costly state entered when satiated; frivolous
play fixes at a low rate under abundance; functional play spreads then collapses the population.
Hamon, Nisioti & Moulin-Frier 2023: reward-free neuroevolution with 1,000 agents, child =
parent weights + N(0, 0.02), 10^6 steps in ≈ 20 min on one GPU, Lotka–Volterra cycles and two
foraging strategies emerged, 3 of 5 seeds collapsed before tuning. JaxLife 2024: the same design
with attention + LSTM nets. Salimans 2017 (ES), Such 2017 (deep GA): black-box optimisation
scales but needs thousands of evaluations. Singh, Lewis, Barto & Sorg 2010: optimal-reward
framework, intrinsic vs extrinsic reward as a continuum. Ackley & Littman 1991: evolved
evaluation network + within-life learning in a world with food, predators, birth and death —
the closest precedent for "fixed biology + evolved valuation + learned policy". A 1600-day
colony has ≈ 15 generations: two orders of magnitude fewer than Hamon's, so inherited-weight
evolution also needs nursery pre-evolution.

### B5. Determinism

PyTorch: `torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, cuDNN
benchmark off / deterministic on; under the flag `scatter_add_`, `index_add`, `cumsum`, `gather`
backward become deterministic on CUDA, while `histc`, weighted `bincount`, `put_(accumulate)`
raise. PyTorch states results are not reproducible between CPU and GPU even with identical
seeds. Warp 1.18: `wp.config.deterministic = wp.DeterministicMode.RUN_TO_RUN` (set before module
creation) gives bit-exact run-to-run on the same architecture; float atomics are transformed,
`atomic_cas / exch` are not; measured 10–24× slower on sparse-output atomics. Intel oneMKL CNR
only matches across machines with a fixed thread count.

### B6. Prior art separating a fixed biology from a learned policy

Polyworld (evolved Hebbian nets, fixed metabolism); Yang et al. 2018 (million-agent predator–prey,
shared DQN, Lotka–Volterra cycles); Hamon 2023 / JaxLife (reward-free, energy-gated birth /
death fixed); Neural MMO (fixed survival mechanics, shared PPO, variable agent count); AI
Economist (fixed economy, learned agents); Baker et al. 2020 (fixed physics, PPO self-play);
Co-Reyes et al. 2020 ("ecological RL": reset-free RL is hard, dynamism helps). None is a
demographically calibrated colony; all keep the world rules out of the learner.

### B7. Recommendation (adopted in `PHASE4_DESIGN.md`)

Formalise what the heuristic already optimises as the Keramati–Gutkin drive-reduction reward
over the existing drives (n = 4, m = 2, no drive-independent term), one parameter-shared PPO
policy over the same 11 actions with the sim's eligibility mask, every biology kernel
unchanged; nursery pre-training because a single run gives only 800–2,400 updates from 8 mice;
inherited-weight evolution as the reward-free second arm; the heuristic as a control, never a
teacher; two determinism tiers, never cross-tier identity.

---

## Part C — Play: criteria, ancestors, rodent facts, validation

### C1. Burghardt's five criteria (Burghardt 2005, quoted verbatim in Miller 2017)

1. Not fully functional "in the form or context in which it is expressed".
2. "Spontaneous, voluntary, intentional, pleasurable, rewarding, reinforcing, or autotelic".
3. Differs from the serious version "structurally or temporally": incomplete, exaggerated,
   awkward, precocious, or with modified sequencing or targeting.
4. "Performed repeatedly in a similar, but not rigidly stereotyped, form".
5. Initiated when the animal is "adequately fed, healthy, and free from stress" — the
   "relaxed field".

Surplus Resource Theory (Burghardt 2005, 2014): play first arises as a by-product of excess
metabolic energy, lack of stimulation and motivational conflict ("primary process"); species
with more time and energy, reduced locomotor cost, prolonged ontogeny and parental care play
more; secondary and tertiary processes can then evolve. Reviewers: surplus is necessary, not
sufficient. **No computational operationalisation of all five criteria exists**; Cloos et al.
2026 use one criterion plus an LLM judge (off-limits here); livestock classifiers are
supervised on human ethograms (forbidden by H1).

### C2. Auerbach, Kanarek & Burghardt 2015 (*Adaptive Behavior* 23: 354–361; full text read)

Non-spatial, individual-based, asexual, semelparous population (N = 50 / 100); resources R0 per
generation decline as consumed; agents rest or forage below a hunger threshold; foraging
success a·(R_t / R0); zero energy = death; weak selection at generation end. Two heritable loci:
play on / off and play probability; players play *when satiated*, at higher energy cost and
double resting mortality; a variant lets play raise foraging ability. Results: "frivolous play
evolves … when there are ample resources", fixes at a low rate (≈ 10 % of satiated time);
initial resource abundance is the most important parameter; functional play rises faster, then
the player population collapses and the cycle repeats. The authors' own caveat: "our labeling
this behavior as play may seem a sleight of hand". **For us:** the relaxed-field gate is built in
(play only when satiated), so "more abundance → more play opportunity" is by construction; the
non-trivial result there was evolutionary persistence despite cost. Nothing in that model
touches criteria 3 or 4 — which is where our non-trivial test has to live.

### C3. Other computational models (what each counted as play, and whether it was rewarded)

| Work | Agent | Play defined as | Reward for play? | Result |
|---|---|---|---|---|
| Haber et al. 2018 (NeurIPS) | world-model + self-model curiosity agent | object in view within 2 m ("play state") | no (world-model loss) | stages ego-motion → object attention → two-object interaction; noisy-TV problem acknowledged |
| Oudeyer, Kaplan & Hafner 2005 / 2007 | AIBO with learning-progress drive | never defined; descriptive | no (learning progress) | self-organised phases; action rates **normalised against a random-policy baseline** |
| Bell, Bell, Schank & Pellis 2015 | ABM of rat keep-away | rat ethogram tactics | none | tactics reproduced without programs |
| Durand & Schank 2015 | ABM juveniles | interactions that train cooperation | indirect fitness | social play evolves |
| Lehman & Stanley 2011 | evolved controllers | not play; novelty objective | novelty replaces objective | beats objective search on deceptive tasks |
| Cloos et al. 2026 | LLM agents | four LLM-judged signatures | no | no human-agreement or null-model check; LLM agents excluded here |

### C4. Rodent play facts

- Rats: onset ≈ PND 18, peak PND 30–40, decline by PND 50–60; ≈ 30 % of juvenile play fights end
  in role reversal (self-handicapping); play costs 2–3 % of the daily energy budget.
- Suppressors: 24 h food deprivation → three-fold drop in pinning, reversed by a meal (Siviy &
  Panksepp 1985); acute restraint stress nearly eliminates play (Klein, Padow & Romeo 2010);
  predator cues and bright light suppress it. Enhancers: short social isolation increases play
  on return (a rebound confound). Welfare framing: play can also rise under stress or as a
  rebound, so presence alone is not a clean indicator (Held & Špinka 2011).
- **House mice play little**: attack–defence play ≈ 2 % of social play in C57 mice, most social
  play non-contact locomotion (Pellis & Pasztor 1999); solitary locomotor play ("jerk-run",
  vertical bouncing: Wolff 1981) is the documented form; no quantitative source on mouse
  object play; no rodent study of crowding vs play; Calhoun did not score play.
- Implication: predicted effects in a mouse colony are **small, juvenile, locomotor or
  object-based**; near-total loss under hunger, stress and crowding analogues is expected.

### C5. Validation principles adopted (no animal or human play data)

Synthetic ground truth scripted from the criterion text; ≥ 1,000 surrogates per detector
(within-agent time shuffle, circular drive shift, first-order Markov surrogates; permutation
logic of Wampold & Margolin 1982); ablations (playground off, abundance ramp, gate removed,
curiosity / boredom drive removed, crowding ramp, age bands); non-triviality by matching on
drive state; thresholds from surrogate percentiles fixed before any evaluation seed;
inter-detector agreement (kappa); reporting per Datta et al. 2019 ("human-imposed design
decisions suffuse any quantification"). Detectors in `PHASE4_DESIGN.md` §2.

---

## Part D — What the code map found (2026-11-04)

- No policy abstraction existed: action selection was an inline utility softmax in
  `sim._select_actions`. **Fixed today**: `agents/policy.py` with a `Policy` protocol, the
  heuristic moved verbatim (bit-identical, 300-d hash `966401ea…`), `policy.kind` in the config.
- The vital links to the calibrated biology run mostly through **position and state**, not
  through the action label: conception needs a female and an eligible male in the same cell
  (ACT_MATE only moves agents); pup feeding needs the mother within 8 in of the nest; stress is
  cell density. A learned policy therefore changes the curve through redistribution, which is
  the right channel and the reason for the calibration guard.
- The playground box (35, 35)–(66, 66) contains six of the eight hoppers of cells 5, 6, 9, 10
  and 16 nests: an agent drinking there counts toward free-choice V. Metric fix in P4-5.
- `PlayScoreAccumulator`: F is a constant 0, D is the share of EXPLORE / MANIPULATE actions, the
  object / locomotor / social detectors named in HANDOFF do not exist in code.
- The Warp path skips three host-only parts of `_density_stress` (homeless nest adoption, the
  random nest kick, `maternal = 0.8 × competence` for young females) and draws mortality from
  per-slot xorshift streams: it is not the calibrated model (P0-2 remains open). The CUDA-graph
  capture tick recorded its launches without running them, so one tick's post-step was skipped
  in graph mode — **fixed today** (`wp.capture_launch` right after capture; the smoke test now
  shows 45 replays for 48 ticks instead of 44).
- torch 2.11.0+cu128 with CUDA 12.8, Warp 1.18.0 and numpy 2.5.4 are in the omnilab venv; the
  repo-local `.venv` has only optuna / cmaes.

---

## Part E — References

Calhoun record (DOIs added 2026-11-17): Calhoun 1973 doi:10.1177/00359157730661P202,
https://pmc.ncbi.nlm.nih.gov/articles/PMC1644264/ (OCR scan
https://physicsoflife.pl/dict/pic/calhoun/calhoun's-experiment.pdf) · Calhoun 1971
doi:10.1007/978-1-4684-1893-4_25, https://www.gwern.net/doc/sociology/1971-calhoun.pdf · Calhoun 1962
https://gwern.net/doc/sociology/1962-calhoun.pdf · Marsden 1972 (in *Environment and the Social
Sciences*, APA, pp. 5–14) doi:10.1037/10045-001, https://gwern.net/doc/sociology/1972-marsden.pdf ·
Kessler 1966 ("Interplay between social ecology and physiology, genetics and population dynamics
of mice")
https://www.gwern.net/doc/biology/1966-kessler.pdf · Hammock 1971 ("Behavioral changes due to
overpopulation in mice") doi:10.15760/etd.1428,
https://pdxscholar.library.pdx.edu/open_access_etds/1429/ · Ramsden & Adams 2009
doi:10.1353/jsh.0.0156, http://eprints.lse.ac.uk/59888/ · Gwern https://gwern.net/mouse-utopia ·
Day 2025
https://www.lrb.co.uk/the-paper/v47/n13/jon-day/the-beautiful-ones · Petrusewicz 1963
https://rcin.org.pl/publication/85975 · Dugatkin 2024 *Dr. Calhoun's Mousery* (University of
Chicago Press; not read) · Adams & Ramsden 2024 *Rat City* (not read). Everything else about
earlier Universe 25 research, with its references: `docs/PRIOR_WORK.md` (2026-11-17).

Learning agents: Keramati & Gutkin 2014 https://elifesciences.org/articles/04811 · Hulme,
Morville & Gutkin 2019 https://hal.archives-ouvertes.fr/hal-02355206 · Dulberg et al. 2023
https://doi.org/10.1073/pnas.2221180120 · Yoshida et al. 2025 https://arxiv.org/abs/2507.04998 ·
Laurençon et al. 2021 https://arxiv.org/abs/2109.06580 · Pathak et al. 2017
https://arxiv.org/abs/1705.05363 · Burda et al. 2018 https://arxiv.org/abs/1810.12894 ,
https://arxiv.org/abs/1808.04355 · Oudeyer & Kaplan 2007
https://www.frontiersin.org/articles/10.3389/neuro.12.006.2007/full · Bellemare et al. 2016
https://arxiv.org/abs/1606.01868 · Salge, Glackin & Polani 2014 https://arxiv.org/abs/1310.1863 ·
Yu et al. 2022 (MAPPO) https://arxiv.org/abs/2103.01955 · de Witt et al. 2020
https://arxiv.org/abs/2011.09533 · Huang & Ontañón 2020 https://arxiv.org/abs/2006.14171 ·
PufferLib https://arxiv.org/abs/2406.12905 · Neural MMO 2.0 https://arxiv.org/abs/2311.03736 ·
JaxMARL https://arxiv.org/abs/2311.10090 · Isaac Gym https://arxiv.org/abs/2108.10470 ·
WarpDrive https://arxiv.org/abs/2108.13976 · Hamon, Nisioti & Moulin-Frier 2023
https://arxiv.org/abs/2302.09334 · JaxLife 2024 https://arxiv.org/abs/2409.00853 · Salimans et
al. 2017 https://arxiv.org/abs/1703.03864 · Such et al. 2017 https://arxiv.org/abs/1712.06567 ·
Singh, Lewis, Barto & Sorg 2010 https://ieeexplore.ieee.org/document/5471106 · Ackley &
Littman 1991 https://www2.hawaii.edu/~nreed/ics606/papers/Ackley91learningEvolution.pdf ·
Yang et al. 2018 https://arxiv.org/abs/1709.04511 · Baker et al. 2020
https://arxiv.org/abs/1909.07528 · Co-Reyes et al. 2020 https://arxiv.org/abs/2006.12478 ·
PyTorch reproducibility https://docs.pytorch.org/docs/stable/notes/randomness.html · Warp
deterministic execution
https://nvidia.github.io/warp/v1.18/user_guide/execution_and_performance/deterministic_execution.html

Play: Burghardt 2014 https://www.animalbehaviorandcognition.org/uploads/journals/2/01.Burghart_Final_2.pdf ·
Miller 2017 https://link.springer.com/article/10.3758/s13420-017-0286-x · Burghardt et al. 2024
https://pubmed.ncbi.nlm.nih.gov/38458553/ · Auerbach, Kanarek & Burghardt 2015
https://doi.org/10.1177/1059712315611188 (full text
https://trace.tennessee.edu/server/api/core/bitstreams/12e445af-b702-4fd5-ae49-82ac95540103/content) ·
Pellis, Burghardt, Palagi & Mangel 2015 doi:10.1177/1059712315596053 · Haber et al. 2018
https://ar5iv.arxiv.org/html/1802.07442 · Oudeyer, Kaplan & Hafner 2007
https://adapt.informatik.hu-berlin.de/pub/papers/ims.pdf · Lehman & Stanley 2011
https://www.cs.swarthmore.edu/~meeden/cs81/f17/papers/lehman_ecj11.pdf · Gopnik 2020
https://pmc.ncbi.nlm.nih.gov/articles/PMC7293160 · Andersen et al. 2023 *Psychol Rev* 130: 462 ·
Cloos et al. 2026 https://arxiv.org/html/2610.07130v1 · Held & Špinka 2011
https://www.wellbeingintlstudiesrepository.org/plabeh/2 · Vanderschuren, Achterberg & Trezza
2016 https://pmc.ncbi.nlm.nih.gov/articles/PMC5074863 · Bell 2018
https://academic.oup.com/endo/article/159/7/2596/4995288 · Pellis et al. 2022
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9623181/ · Siviy & Panksepp 1985
https://pubmed.ncbi.nlm.nih.gov/2999842/ · Siviy & Atrens 1992 https://cupola.gettysburg.edu/psyfac/24 ·
Klein, Padow & Romeo 2010 doi:10.1002/dev.20413 · Pellis & Pasztor 1999
https://nifplay.org/the-developmental-onset-of-a-rudimentary-form-of-play-fighting-in-c57-mice/ ·
Meijer & Robbers 2014 https://pmc.ncbi.nlm.nih.gov/articles/PMC4046404 · Slater & Lester 1982
*Behaviour* 79: 153 · Wampold & Margolin 1982 *Psychol Bull* 92: 755 · Berman et al. 2014
https://pmc.ncbi.nlm.nih.gov/articles/PMC4233753 · Datta et al. 2019
https://pmc.ncbi.nlm.nih.gov/articles/PMC6981239 · Vonk & Krause 2018 (preregistration)
https://www.animalbehaviorandcognition.org/uploads/journals/19/AB_C_2018_Vol5(2)_Vonk_Krause.pdf
