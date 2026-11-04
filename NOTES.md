# Universe25 Play — NOTES

## 2026-11-04 — Record review, phase 4 design and scaffold (documentation + code, not empirical)

No empirical result changed in this pass and the calibration stays frozen at phase 2m. What
changed is what the record is known to say, and what the code can now do.

**The record** (`docs/RESEARCH_DIGEST.md` part A: Calhoun 1973 read in full with Fig 2
digitised, Calhoun 1971, Marsden 1972, Kessler 1966, Ramsden & Adams 2009):
- *First litters at day 104 is contested.* Calhoun 1971 gives first surviving litters at 50 d,
  both of his figures imply 60–65 d, and 104 cannot be reconciled with 620 at day 315 and a 55-d
  doubling (five doublings from 20 take 275 d). The simulator reaches 102 and sits a third low
  at 315 (409 ± 45 vs 620) — consistent with phase B starting ≈ 40 d late. This is the best lead
  on the early-phase miss that phase 2j de-weighted. Not applied (frozen); card P0-5 re-anchors
  phase A as a new calibration version with its own 12-seed evaluation.
- *≈ 150 mice were removed after day 1000* (Calhoun 1973 Fig 2 caption). 122 at 1444 and 27 at
  1588 are post-removal counts; the no-removal envelope at 1444 is ≤ 272 and our 155 ± 29 lies
  inside it. The decline is no longer chased toward 122.
- *Irreversibility is n = 1.* Kessler 1966 and Hammock 1971 colonies resumed reproduction when
  density fell; Marsden's transfers (Calhoun's own) did not. The phase 2m colony-wide exposure
  encodes Universe 25's outcome — a model assumption fitted to one colony, listed as such.
- New **reported-only** landmarks in `metrics/calibration.py` (`RECORD_LANDMARKS`, never in the
  loss or the mean errors): 1871 at 811 and ≈ 1650 at 960 (Marsden 1972), 100 at 1471 (Calhoun
  1973), doubling times 55 d (phase B, first litters → 315) and 145 d (phase C, 315 → peak day);
  `landmark_notes` go into every calibration report. Not modelled, now documented: two of four
  founder males dead by ≈ day 60; hoppers and water moved out of the nest compartments ≈ day
  150–175; the 23 May 1973 "extinction" is a projection, no extinction date was observed.
  Read off the existing 2m run (seed 7000, 6 ticks/day, 1600 d): 1833 at 811 (2 % low), 1584
  at 960 (4 % low), 76 at 1471 (24 % low; seed 7000 is a fast decliner), phase B doubling
  47.9 d (Calhoun 55: the simulator starts phase B late and grows faster), phase C doubling
  100 d (1973: 145; the 1971 five-universe mean is 105, Universe 25 digitised 136).

**Code (bit-identical where it touches the tick).**
- Policy hook: `agents/policy.py` (`Policy` protocol, `NeedDrivenPolicy` moved verbatim,
  `sample_masked`, `make_policy`), `policy.kind` in `config.py`, `tests/test_policy.py`. The
  300-d trajectory hash (`966401ea…`, seed 7000, 6 ticks/day) is identical to the commit before
  the change; the full suite is green.
- CUDA-graph bug fixed: the capture tick recorded its launches without running them, so one
  tick's post-step (stress, mortality, cells) was skipped in graph mode; `wp.capture_launch` now
  follows the capture (Warp smoke: 45 replays for 48 ticks, was 44). NumPy-path results are
  unaffected; graph-mode GPU runs made before this fix skipped one tick.
- Found, not fixed (cards): the playground box contains six of the eight hoppers of cells 5, 6,
  9, 10 and 16 nests, so free-choice V counts drinkers (P4-5 adds an excluding variant); the
  Warp path skips three host-only parts of `_density_stress` (homeless adoption, the nest kick,
  the young-female maternal cap) and is not the calibrated model (P0-2); PlayScore F is a
  constant and D a stand-in (P4-5).

**Phase 4** (`docs/PHASE4_DESIGN.md`, `PLAN.md` §15, `docs/TASKS.md` P4-0 … P4-7): learning
agents on the frozen biology — a homeostatic drive-reduction reward (Keramati & Gutkin 2014;
n = 4, m = 2, no drive-independent term, no ICM / RND because conspecifics are a "noisy TV"),
one parameter-shared PPO policy over the same 11 actions with the simulator's eligibility mask,
nursery pre-training, inherited-weight evolution as the reward-free second arm, the heuristic as
a control and never a teacher, a preregistered calibration guard (H-d: every canonical landmark
within 10 % of the control on 12 seeds), Burghardt detectors with synthetic ground truth and
≥ 1,000 surrogates per detector, evaluation seeds 8000–8011 reserved. Hypotheses H-d … H-g are
preregistered before any learning run. The house-mouse literature predicts small, juvenile,
locomotor or object-based effects, so the preregistered tests are about structure (criteria 3
and 4 at matched drive states), not frequency.

**P4-0 done (2026-11-04).** `agents/observation.py` builds the 48-float egocentric vector of
`PHASE4_DESIGN.md` §1.3 (`OBS_NAMES`; no `lifespan`, no `competence`, no PlayScore field);
`MlpFrozenPolicy` (48 → 128 tanh → 128 tanh → 11, orthogonal init with last-layer gain 0.01 from
a seeded stream, or weights from an `.npz`; NumPy float32 inference; the `allowed` mask as −1e8
on the logits; one uniform per deciding agent from the policy stream `seed + 1_000_003`);
`policy.kind: mlp_frozen`, `policy.weights`, `policy.hidden`; CLI `--policy`,
`--policy-weights`. Checks: `need_driven` 300-d hash unchanged (`966401ea…`); `mlp_frozen` is
seed-deterministic and seed-sensitive, respects the mask, round-trips through `.npz`; the
observation names pass the H2 audit. Cost at the plateau (seed 7000, day 560, 2172 alive):
`build_observation` 0.97 ms, `choose` with the MLP 3.45 ms → 1.8 / 6.4 ms per 4,000 agents
(acceptance < 2 ms for the builder). A random-init net is a near-uniform policy over the
eligible actions: the "random policy" baseline of the detector validation. Smoke
(`configs/smoke.yaml`, 30 d, `--policy mlp_frozen`): runs, 0 NaN, no births in 30 d (as with
`need_driven`: first litters come at ≈ 100 d). No learning, no calibration claim: the guard is
P4-1.

## Phase 2m — colony-wide developmental exposure: the collapse cannot rebound (2026-11-03)

Motivation: phase 2l found the breakdown reversible — with lifespans short enough to fit the
late tail (780 ± 170, 800 ± 150) the old cohorts die while fertile, competent females from the
sparse cells remain, density falls, nursing recovers and surviving births resume in 1–3 of 12
seeds (seed 7007: 1434 animals at day 1588). Calhoun's colony never recovered; Marsden's transfer
experiment showed the late-born mice could not reproduce even when given space ("death of the
spirit"). The 2l calibration avoided the rebound only by keeping deaths late (850 ± 100).

### Change (NumPy + Warp `density_stress_kernel`, parity 1.9e-9 with the branch exercised)

`imprint_breakdown_exposure`: young lose competence at `imprint_rate` × (local exposure + this
gain × the breakdown factor), where the breakdown factor is the weaned-density ramp that already
drives the colony-wide stress boost. Once the colony is in breakdown the disrupted social
organisation reaches every nest: a female raised in an uncrowded cell during phase C/D no longer
grows up competent, so she withdraws ("beautiful one") instead of breeding when space returns.
Adults are frozen as before. 0 = off, bit-identical (hash `be9f85b6…`, 600 d, 6 ticks/day).
Prior added (log-uniform 0.05–5).

### Scan (seed 7000, 1600 d; Calhoun 2056 / 122 / 27 at 736 / 1444 / 1588)

| exposure gain / lifespan | peak N / day | surviving births cease | conception cessation | N@736 | N@1200 | N@1444 | N@1588 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 / 850 ± 100 (2l) | 2261 / 525 | 574 | 892 | 1962 | 1127 | 120 | 7 |
| 0.5 / 850 ± 100 | 2212 / 503 | 593 | 961 | 1920 | 1092 | 115 | 8 |
| 1.0 / 850 ± 100 | 2214 / 536 | 577 | 950 | 1926 | 1071 | 119 | 7 |
| 2.0 / 850 ± 100 | 2230 / 506 | 589 | 954 | 1907 | 1092 | 122 | 11 |
| 0.5 / 780 ± 170 | 2251 / 507 | 572 | 962 | 1909 | 797 | 141 | 29 |
| 1.0 / 780 ± 170 | 2199 / 528 | 621 | 959 | 1930 | 827 | 153 | 30 |
| 2.0 / 780 ± 170 | 2219 / 546 | 564 | 918 | 1927 | 827 | 142 | 25 |

Seed 7007, which rebounded to 1434 at 1588 with 780 ± 170 in 2l: with gain 1.0 it has 156 at 1444
and 40 at 1588, with gain 2.0 153 / 27 — no rebound. The plateau landmarks move within
realisation noise; N@736 sits 1–3 % lower (fewer late surviving litters) and conceptions end
≈30 days later at the training seed.

### 12-seed check (7000–7011, 1600 d, `scripts/seed_eval.py`, mean ± se)

| gain / lifespan | surviving births cease | conception cessation | N@736 | N@1200 | N@1444 (median) | N@1588 (median) | rebound |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 / 780 ± 170 (2l) | 689 ± 83 | 1003 ± 60 | 1994 ± 19 | — | 242 ± 53 (170) | 159 ± 116 (29) | 7007 full, 7003 / 7009 partial |
| 1.0 / 780 ± 170 | 604 ± 16 | 951 ± 17 | 1970 ± 17 | 882 ± 49 | 194 ± 31 (150) | 46 ± 12 (32) | none |
| 2.0 / 780 ± 170 | 596 ± 17 | 961 ± 19 | 1950 ± 16 | 887 ± 47 | 186 ± 27 | 42 ± 10 | none |
| 1.0 / 850 ± 100 | 602 ± 21 | 926 ± 22 | 1988 ± 14 | 1197 ± 48 | 190 ± 45 (135) | 23 ± 10 (9) | none |
| **1.0 / 780 ± 150** | **608 ± 19** | 939 ± 21 | 1983 ± 20 | 880 ± 49 | **155 ± 29** | **31 ± 9** | none |
| 1.0 / 760 ± 150 | 600 ± 20 | 956 ± 19 | 1967 ± 13 | 808 ± 52 | 122 ± 26 | 19 ± 7 | none |

With the exposure on, the cessation of surviving births has the same spread at every lifespan
(se 16–21 instead of 83): no seed resumes breeding. The lifespan was then re-chosen for the late
tail: 850 ± 100 (2l) holds 1197 at 1200 and 9 at 1588 (median); **780 ± 150** gives N@1444
155 ± 29 and N@1588 31 ± 9 (Calhoun 122 / 27) with the plateau unchanged (peak 2265 ± 18 at
550 ± 15, N@736 1983 ± 20); 760 ± 150 matches N@1444 exactly but leaves 19 at 1588 and ends
conceptions later. The slow realisations (late peak, 7003 / 7009) still carry 300–480 at 1444.
Loss of the mean landmarks 0.020 (2l 0.022), mean per-seed loss 0.073.

### Validation

1600 d, seed 7000, 6 ticks/day (`_output/run1600_p2m_tpd6`, 86 s, 0 NaN; phases decline
675 → collapse 1120) and 24 ticks/day (`_output/run1600_p2m_tpd24`, 155 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 105 |
| N @ 315 | 502 | 307 |
| Peak N / day (31-d mean max; first-97 % day) | 2199 / 528 (506) | 2317 / 543 (529) |
| Surviving births cease (strict latest pup) | 621 (692) | 601 (682) |
| N @ 736 | 1955 | 1982 |
| Conception cessation | 905 | 958 |
| N @ 1444 / 1588 (Calhoun 122 / 27) | 108 / 10 | 158 / 27 |
| Decline onset / collapse onset | 675 / 1120 | 648 / 1138 |
| N @ 1200 / 1400 / 1600 | 811 / 174 / 9 | 923 / 247 / 24 |
| births / conceptions | 16,072 / 2,419 | 15,939 / 2,380 |
| mean rel. error (canonical 5 / extended 10) | 0.060 / 0.143 | 0.120 / 0.118 |

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 93 | 30 | 0 | 0.96 | 166 |
| 300 | 370 | 142 | 72 | 0.47 | 593 |
| 400 | 1401 | 616 | 340 | 0.37 | 2218 |
| 500 | 2097 | 1506 | 1117 | 0.23 | 4280 |
| 600 | 2098 | 1898 | 1529 | 0.17 | 3543 |
| 700 | 1946 | 1919 | 1564 | 0.16 | 2554 |
| 800 | 1849 | 1828 | 1497 | 0.16 | 1623 |
| 900 | 1695 | 1688 | 1389 | 0.16 | 959 |
| 1000 | 1473 | 1473 | 1237 | 0.14 | 136 |
| 1100 | 1180 | 1180 | 1025 | 0.12 | 0 |
| 1200 | 811 | 811 | 716 | 0.10 | 0 |
| 1300 | 444 | 444 | 398 | 0.09 | 0 |
| 1400 | 174 | 174 | 163 | 0.05 | 0 |
| 1500 | 53 | 53 | 51 | 0.04 | 0 |
| 1600 | 9 | 9 | 9 | 0.00 | 0 |

Twelve seeds (7000–7011), 400 d, mean ± se:

| | 6 tpd | 24 tpd |
|---|---:|---:|
| N @ 315 | 409 ± 45 | 402 ± 59 |
| N @ 400 | 1163 ± 122 | 1072 ± 109 |

Twelve seeds, 800 d, mean ± se (`_output/multiseed_peak_p2m.txt`):

| | 6 tpd | 24 tpd | paired 24 − 6 |
|---|---:|---:|---:|
| Peak N (daily max) | 2265 ± 18 | 2262 ± 15 | -3 ± 20 |
| Peak day (31-d mean max) | 550 ± 15 | 562 ± 13 | +13 ± 19 |
| Surviving births cease | 608 ± 19 | 614 ± 17 | +6 ± 24 |
| N @ 736 | 1983 ± 20 | 1987 ± 14 | +4 ± 25 |

Twelve seeds, 1600 d, 6 ticks/day, mean ± se (`scripts/seed_eval.py - p2m_final 12 12 7000 1600`;
`_output/seed_eval_p2m_final.json`):

| landmark | Calhoun | 12 seeds |
|---|---:|---:|
| N @ 315 | 620 | 409 ± 45 |
| Peak N / day | 2200 / 560 | 2265 ± 18 / 550 ± 15 |
| Surviving births cease | 600 | 608 ± 19 |
| N @ 736 | 2056 | 1983 ± 20 |
| Conception cessation | ≈920 | 939 ± 21 |
| N @ 1200 | (0.35–0.85 × peak) | 880 ± 48 |
| N @ 1444 | 122 | 155 ± 29 (median 119) |
| N @ 1588 | 27 | 31 ± 9 (median 20) |
| N @ 1600 | | 27 ± 8 (median 18) |

Mean per-seed loss 0.073; canonical error of the means
0.084. Held-out seeds 8000–8002 at 1600 d: N@1444 109–111, N@1588
14–16, canonical error 0.03–0.10.

**Honest misses / open gaps**
- *N@1444 27 % high* (155 ± 29; 122) — two slow realisations (301, 413); ten of twelve seeds
  lie in 76–149, median 119.
- *Early phase low and seed-dominated* (unchanged): N@315 409 ± 45, adults@315 143 ± 18.
- *N@736 3–4 % low, raw peak 3 % high* (unchanged).
- *Conception cessation ≈20 d later* than 2l (939 ± 21 vs 926; Calhoun ≈920): withdrawn daughters
  do not conceive, so the remaining conceptions are the older competent females' — within noise.
- *The exposure gain is a scan value* (0.5–2 all stop the rebound; 1.0 chosen for the plateau):
  a 1200-d study cannot see what it does (the rebound is a 1300+ phenomenon), so it stays fixed
  unless studies run to 1600 d. `max_age_days` likewise.
- *Realisation shift*: the training seed's plateau numbers move with every change to the RNG
  stream (lifespan draws); the 12-seed means are the reference.
- *Warp*: `density_stress_kernel` parity 1.9e-9 with the colony-wide branch exercised; the
  mortality kernel takes the per-agent lifespan (smoke-tested).

### Calibration frozen at 2m — caveats (read before reopening)

- **The fit is not evidence that the mechanisms are right.** Phases 2b–2m introduced or re-set on
  the order of ten biology parameters (imprinting rate / threshold, breakdown threshold / ramp /
  boost, courtship erosion, nursing-disturbance coefficient / onset, lifespan mean / sd, colony-wide
  exposure) against about ten landmarks taken from a single historical colony. With that ratio a
  close fit is nearly guaranteed: the substrate is plausibility-calibrated, not validated. Do not
  describe it as a model of Universe 25.
- **The optimizer has been decorative.** Every CMA-ES study since 2g (single-seed and multi-seed,
  with and without inverse-variance weights) returned the hand-chosen start point or a candidate
  that lost out of sample. The calibration that stands was done by hand scans adjudicated with
  12-seed out-of-sample scoring (`scripts/seed_eval.py`) and the 6-vs-24 ticks/day check
  (`scripts/multiseed_peak.py`).
- **The early phase was de-weighted, not fixed.** Inverse-variance weighting gives N@315 0.10 and
  adults@315 0.04 of a total weight of 12 because they are seed-dominated (relative seed sd 0.27 /
  0.42). That is statistically defensible, but it means the loss no longer sees a miss of a third
  (409 ± 45 vs 620). The growth of eight founders is a structural miss.
- **Diminishing returns.** Since 2k each phase has moved the plateau landmarks by less than their
  seed standard error (10–20 animals, 10–20 days); the only material change was the irreversible
  collapse (2m). The late-phase knobs (`max_age_days`, `max_age_sd_days`,
  `imprint_breakdown_exposure`) are scan values that a 1200-d study cannot see.
- **Status:** `configs/default.yaml` = `configs/calibrated_calhoun.yaml` = the 2m point. The
  preregistered H-a bar (`PLAN.md`: peak within 30 % of 2200 near day 560, collapse after ~600) is
  met with margin. Reopen calibration only if a phase 3 / 4 experiment needs a landmark the
  substrate cannot show.

## Phase 2l — per-individual lifespan, late collapse, rebound hazard (2026-11-03)

Motivation: with one old-age cutoff (`max_age_days` 938, hazard +0.05 / day past it) the cohorts
born 400–600 died together: 1515 at 1200, 480 at 1400, extinct at 1578 (Calhoun: 2056 at 736,
122 at ≈1444, 27 at 1588).

### Change (NumPy + Warp `mortality_kernel`)

`max_age_sd_days`: every animal draws its lifespan at birth from a normal around `max_age_days`
with this sd (floor 0.3 × mean; SoA `lifespan`, a new kernel buffer); the old-age hazard applies
past the individual's lifespan. sd 0 = the old cutoff, bit-identical (hash `a264ccf2…`, 600 d).
Two late landmarks are now reported: `n_at_day_1444` (122) and `n_at_day_1588` (27), NaN for
runs shorter than that, so 1200-d calibration studies skip them; their 12-seed spread (1.33 of
the target) gives them ≈0 weight in the loss.

### Scan (seed 7000, 1600 d, 6 ticks/day; Calhoun 2056 / 122 / 27 at 736 / 1444 / 1588)

| mean / sd | N@736 | N@1200 | N@1300 | N@1444 | N@1588 | extinct |
|---|---:|---:|---:|---:|---:|---:|
| 938 / 0 (2i–2k) | 1949 | 1515 | 1113 | 223 | 0 | 1578 |
| 938 / 100 | 1966 | 1426 | 1034 | 343 | 46 | — |
| 938 / 150 | 1942 | 1328 | 979 | 450 | 136 | — |
| 900 / 200 | 1961 | 1159 | 854 | 417 | 164 | — |
| 870 / 150 | 1952 | 1116 | 746 | 254 | 59 | — |
| **850 / 100** | 1962 | 1127 | 623 | **120** | 7 | — |
| 850 / 130 | 1967 | 1073 | 666 | 183 | 24 | — |
| 850 / 150 | 1947 | 1046 | 657 | 215 | 44 | — |
| 830 / 150 | 1944 | 960 | 568 | 179 | 32 | — |
| 820 / 130 | 1939 | 952 | 510 | 124 | 11 | — |
| 820 / 150 | 1948 | 916 | 538 | 174 | 32 | — |
| 810 / 170 | 1941 | 918 | 547 | 192 | 49 | — |
| 800 / 100 | 1966 | 881 | 381 | 59 | 1 | — |
| 800 / 130 | 1974 | 892 | 440 | 102 | 7 | — |
| 800 / 150 | 1975 | 884 | 464 | 149 | 21 | — |
| 800 / 170 | 1976 | 888 | 534 | 190 | 38 | — |
| 790 / 180 | 1931 | 832 | 489 | 164 | 35 | — |
| 780 / 150 | 1984 | 801 | 407 | 90 | 13 | — |
| 780 / 170 | 1947 | 832 | 471 | 144 | 24 | — |
| 760 / 120 | 1948 | 706 | 287 | 53 | 2 | — |

The plateau landmarks are untouched (peak 2239–2269, N@736 1931–1984; the first old-age deaths
are the founders'). At the training seed several pairs fit both late numbers — 780 / 170
(144 / 24), 800 / 150 (149 / 21), 850 / 100 (120 / 7) — and the held-out seeds agree
(780 / 170: 160 / 42, 125 / 18, 146 / 22; 800 / 150: 136 / 24, 143 / 19, 136 / 16;
850 / 100: 140 / 9, 113 / 7, 117 / 4).

### The rebound hazard (12 seeds 7000–7011, 1600 d)

| mean / sd | surviving births cease | conception cessation | N@1444 mean ± se (median) | N@1588 mean ± se (median) | seeds with a late rebound |
|---|---:|---:|---:|---:|---|
| 780 / 170 | 689 ± 83 | 1003 ± 60 | 242 ± 53 (170) | 159 ± 116 (29) | 7007 full (1434 at 1588), 7003 / 7009 partial |
| 800 / 150 | 680 ± 83 | 964 ± 63 | 219 ± 45 (157) | 93 ± 58 (25) | 7003 full (725), 7009 partial |
| **850 / 100** | **600 ± 20** | 929 ± 26 | 193 ± 47 (131) | 24 ± 10 (8) | none (7003 / 7009 slow: 411 / 623 at 1444) |

With a shorter mean lifespan the old cohorts die while fertile, competent females remain (the
sparse cells' late cohorts: no imprinting below local density 0.145, no erosion below stress
0.51, fertile to 583 days of age), density falls, nursing recovers and surviving births resume —
in seed 7007 at 780 / 170 the population is back at 1434 by day 1588. Calhoun's colony never
recovered ("death of the spirit": the survivors could not reproduce even when given space). The
hard cutoff at 938 had hidden this: deaths came only after the last fertile females (born ≤ 600)
had aged out at ≈1180. **850 / 100 is the phase-2l calibration**: no rebound in 12 seeds, N@1588
24 ± 10 (Calhoun 27) and N@1444 193 ± 47 with the median at 131 (122) — two slow realisations
(late peak 644 / 681, late last fertile cohort) carry 411 / 623 at 1444. `max_age_days` is a
searched parameter (938 from the 2f study); it is set by hand here and the 1200-d studies cannot
see the late tail, so it should stay fixed in future studies unless they run to 1600 d.

### Validation

1600 d, seed 7000, 6 ticks/day (`_output/run1600_p2l_tpd6`, 90 s, 0 NaN; phases decline
638 → collapse 1198) and 24 ticks/day (`_output/run1600_p2l_tpd24`, 181 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 105 |
| N @ 315 | 502 | 307 |
| Peak N / day (31-d mean max; first-97 % day) | 2261 / 525 (485) | 2293 / 561 (513) |
| Surviving births cease (strict latest pup) | 574 (580) | 594 (619) |
| N @ 736 | 1962 | 1981 |
| Conception cessation | 892 | 901 |
| N @ 1444 / 1588 (Calhoun 122 / 27) | 120 / 7 | 189 / 15 |
| Decline onset / collapse onset | 638 / 1198 | 672 / 1231 |
| N @ 1200 / 1400 / 1600 | 1127 / 218 / 3 | 1272 / 333 / 13 |
| births / conceptions | 14,725 / 2,232 | 15,472 / 2,332 |
| mean rel. error (canonical 5 / extended 10) | 0.069 / 0.149 | 0.114 / 0.183 |

The seed-7000 realisation differs from 2i/2k before any old-age death (the lifespan draws at birth shift the RNG stream): peak day 525 vs 550, N@315 502 vs 528; the 12-seed means hold (peak day 547 ± 17, N@736 1999 ± 16).

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 93 | 30 | 0 | 0.96 | 166 |
| 300 | 370 | 142 | 72 | 0.47 | 593 |
| 400 | 1401 | 616 | 340 | 0.37 | 2218 |
| 500 | 2209 | 1531 | 1107 | 0.24 | 4203 |
| 600 | 2105 | 2001 | 1597 | 0.20 | 3341 |
| 700 | 2013 | 1956 | 1564 | 0.20 | 2330 |
| 800 | 1915 | 1874 | 1500 | 0.20 | 1238 |
| 900 | 1794 | 1794 | 1441 | 0.20 | 535 |
| 1000 | 1721 | 1718 | 1385 | 0.19 | 101 |
| 1100 | 1491 | 1491 | 1250 | 0.17 | 0 |
| 1200 | 1127 | 1127 | 978 | 0.15 | 0 |
| 1300 | 623 | 623 | 559 | 0.13 | 0 |
| 1400 | 218 | 218 | 207 | 0.10 | 0 |
| 1500 | 53 | 53 | 52 | 0.11 | 0 |
| 1600 | 3 | 3 | 3 | 0.07 | 0 |

Twelve seeds (7000–7011), 400 d, mean ± se (unchanged from 2i: no old-age death before day 400):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| N @ 315 | 475 ± 49 | 466 ± 42 |
| N @ 400 | 1176 ± 89 | 1193 ± 81 |

Twelve seeds, 800 d, mean ± se (`_output/multiseed_peak_p2l.txt`):

| | 6 tpd | 24 tpd | paired 24 − 6 |
|---|---:|---:|---:|
| Peak N (daily max) | 2294 ± 15 | 2275 ± 8 | -19 ± 16 |
| Peak day (31-d mean max) | 547 ± 17 | 566 ± 14 | +20 ± 20 |
| Surviving births cease | 600 ± 20 | 615 ± 16 | +14 ± 23 |
| N @ 736 | 1999 ± 16 | 2018 ± 15 | +19 ± 20 |

Twelve seeds, 1600 d, 6 ticks/day, mean ± se (`scripts/seed_eval.py - p2l_final 12 12 7000 1600`;
`_output/seed_eval_p2l_final.json`):

| landmark | Calhoun | 12 seeds |
|---|---:|---:|
| N @ 315 | 620 | 409 ± 45 |
| Peak N / day | 2200 / 560 | 2294 ± 15 / 547 ± 17 |
| Surviving births cease | 600 | 600 ± 20 |
| N @ 736 | 2056 | 1999 ± 16 |
| Conception cessation | ≈920 | 929 ± 26 |
| N @ 1200 | (0.35–0.85 × peak) | 1212 ± 46 |
| N @ 1444 | 122 | 193 ± 47 (median 131) |
| N @ 1588 | 27 | 24 ± 10 (median 8) |
| N @ 1600 | | 18 ± 8 (median 7) |

Loss of the mean landmarks 0.080 (mean per-seed); canonical error of the means
0.085. Held-out seeds 8000–8002 at 1600 d: N@1444 113–140, N@1588
4–9, canonical error 0.04–0.10.

**Honest misses / open gaps**
- *The breakdown is reversible when density falls* (above): a fidelity gap the lifespan spread
  exposes. Calhoun's late-born mice never acquired reproductive behaviour in any cell; here the
  sparse cells' cohorts keep competence and capacity. Candidate: imprinting / erosion driven by
  the colony-wide social state (the arena-wide weaned density that already drives the breakdown
  ramp) rather than the local cell alone, so the "death of the spirit" is colony-wide.
- *Late tail at the median thin*: N@1588 median 8 vs 27 (mean 24 from the two slow seeds);
  N@1444 median 131 vs 122. Slow realisations (late peak) dominate the late means.
- *Early phase low and seed-dominated* (unchanged): N@315 409 ± 45 over 12 seeds at this horizon
  (475 ± 49 at 1200 d in 2k; realisation differences from the lifespan draws), adults@315 143 ± 18.
- *N@736 3 % low, raw peak 3 % high* (unchanged).
- *Late landmarks are reported, not fitted*: spread 1.33 of the target → weight ≈ 0.02 of 12.
- *Warp*: `mortality_kernel` takes the per-agent lifespan (smoke-tested; no hazard-level parity
  test yet).

## Phase 2k — conception brake in crowded cells (neutral), peak-day landmark, recalibration (2026-10-31)

Motivation: after 2i/2j the peak day (first day at ≥97 % of the maximum) was ≈35 days early
(524 ± 9 over 12 seeds; Calhoun 560) with births still running at 1000–1200 per 30 days through
phase C. The pass asked for a brake on the conception rate.

### Where the mice are (phase-2i run, seed 7000, snapshots)

Local cell density (count / 240), the 16 cells sorted:

| day | N | cells |
|---:|---:|---|
| 300 | 488 | 0.41 0.26 0.24 0.20 0.20 0.11 0.10 0.09 0.09 0.08 0.06 0.05 0.05 0.03 0.03 0.03 |
| 400 | 1228 | 0.79 0.74 0.58 0.40 0.35 0.32 0.30 0.29 0.24 0.24 0.18 0.15 0.15 0.13 0.13 0.12 |
| 500 | 2075 | 1.19 1.10 0.93 0.72 0.55 0.50 0.44 0.44 0.41 0.39 0.38 0.38 0.33 0.33 0.28 0.28 |
| 600 | 2094 | 1.23 1.11 1.05 0.99 0.46 0.46 0.42 0.40 0.38 0.36 0.35 0.34 0.31 0.31 0.28 0.27 |

A behavioural sink: by day 400 three cells hold 40 % of the population at 0.6–0.8 of their
design capacity, by 500 they exceed it. Any per-cell brake with an onset above ≈0.4 leaves
phase B alone.

### (A) Conception suppression in crowded cells — neutral at the training seed

`conception_density_onset` / `conception_density_width`: a female's daily conception
probability is scaled by clip(1 − (local cell density − onset) / width, 0, 1) — untouched below
the onset, zero at onset + width (`_conception_density_factor`; Calhoun: reproduction in the sink
cells was disrupted while cells with a territorial male and few females kept breeding). Spatial
and graded, unlike the whole-population `menopause_density_threshold` term. Width 0 = off,
bit-identical to 2j (hash `a264ccf2…`, 600 d, 6 ticks/day). Scan at the 2i parameters, seed 7000,
1200 d (loss on the 2j scale; peak day still the first-97 % day here):

| onset / width | off (2i) | 0.4 / 0.6 | 0.4 / 0.3 | 0.3 / 0.6 | 0.5 / 0.5 | 0.6 / 0.4 |
|---|---:|---:|---:|---:|---:|---:|
| N @ 315 | 528 | 517 | 521 | 500 | 528 | 528 |
| peak N / 97 % day | 2234 / 518 | 2200 / 508 | 2209 / 497 | 2187 / 513 | 2175 / 517 | 2263 / 535 |
| surviving births cease | 583 | 583 | 560 | 643 | 600 | 575 |
| N @ 736 | 1949 | 1922 | 1930 | 1970 | 1930 | 1960 |
| conception cessation | 915 | 920 | 842 | 919 | 927 | 846 |
| loss | 0.019 | 0.026 | 0.045 | 0.024 | 0.021 | 0.025 |

The brake does what it says (fewer conceptions in the sink cells) but does not delay the
plateau: the 97 % day stays at 497–535 and N@736 drops 1–2 %, because the sink cells' litters are
the ones already dying and the plateau timing is set by when maternal erosion starts, i.e. by
when the sink cells fill (day ≈400–450), not by the conception rate. Same lesson as the fertility
floor (2i): removing births in phase C removes some surviving litters too. Kept in the code (off)
and in the search space.

### The peak-day landmark marked the start of the plateau

12 seeds (7000–7011), 800 d, mean ± se:

| | 6 tpd | 24 tpd |
|---|---:|---:|
| first day at ≥97 % of max (the landmark up to 2j) | 524 ± 9 | 521 ± 9 |
| day of the raw maximum | 553 ± 12 | 552 ± 15 |
| day of the 31-day running-mean maximum | 555 ± 12 | 546 ± 12 |

The plateau is flat within 3 % for ≈100 days, so "first day at 97 %" marks where it starts and sits
≈30 days before the maximum by construction; Calhoun's 2200 at Day 560 is a census maximum. The
raw-maximum day is set by litter pulses (spikes of 3–4 %, 2h). `peak_day` is now the day of the
31-day running-mean maximum (`PEAK_WINDOW_DAYS`), with `peak_day_97pct` and `peak_day_raw_max`
reported alongside (`tests/test_landmarks.py`); its seed spread (sd 40 d, 0.072 of the target)
replaces the 97 %-day spread (0.058) in the loss weights. Under this definition the 2i
calibration sits at 550 at seed 7000 and 555 ± 12 over 12 seeds (Calhoun 560) — the "peak day
35 days early" of 2h–2j was mostly the statistic. The earlier phases' peak-day numbers in this
file and in HANDOFF are 97 %-days and are not directly comparable.

### Recalibration (multi-seed CMA-ES under the 2j weights and the new peak day, 112 trials, train seeds 7000 / 7001 / 7002, 60 min)

Start = 2i parameters with the brake nearly off (onset 0.9, width 0.3). The brake and the
fertility floor were in the search space. Trial 93 beat the start on the training seeds (mean
loss 0.026 vs 0.032; per-seed canonical error 0.026 / 0.042 / 0.047 vs 0.044 / 0.102 / 0.113)
through the early phase — N@315 630 / 581 / 534 vs 528 / 401 / 315 — by lowering the young
baseline mortality 42 %, raising nursing 17 %, and compensating with erosion ×3, ramp 0.085, base
mortality +58 %, stillbirth 0.51, fertility floor 0.81 and the brake slightly on (0.78 / 0.25).
Scored out of sample over 12 seeds (7000–7011, 1200 d, 6 ticks/day; `scripts/seed_eval.py`):

| | start (2i parameters) | trial 93 |
|---|---:|---:|
| N @ 315 | 475 ± 49 | 496 ± 52 |
| Adults @ 315 | 172 ± 18 | 191 ± 21 |
| Peak N | 2269 ± 11 | 2148 ± 12 |
| Peak day (31-d mean max) | 555 ± 12 | 595 ± 18 |
| Surviving births cease | 602 ± 12 | 639 ± 20 |
| N @ 736 | 1991 ± 15 | 1964 ± 12 |
| Conception cessation | 923 ± 13 | 944 ± 14 |
| loss of the mean landmarks (2j weights) | **0.012** | 0.024 |
| mean per-seed loss | **0.042** | 0.071 |
| canonical error of the means | **0.058** | 0.075 |

The N@315 gain did not generalise (496 vs 475 over 12 seeds: the three training seeds happened
to respond) while the plateau moved late and low. **The 2i parameters stay**; the brake stays off
(`conception_density_width` 0). Three training seeds still let the early phase lead the search by
realisation luck even at weight 0.1 — the out-of-sample 12-seed score is now the adjudicator for
any candidate. Artifact: `configs/calibration_study_p2k.json`.

### Validation

1600 d, seed 7000, 6 ticks/day (`_output/run1600_p2k_tpd6`, 98 s, 0 NaN; phases decline
662 → collapse 1300) and 24 ticks/day (`_output/run1600_p2k_tpd24`, 184 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 103 |
| N @ 315 | 528 | 514 |
| Peak N / day (31-d mean max; first-97 % day) | 2234 / 550 (518) | 2274 / 501 (486) |
| Surviving births cease (strict latest pup) | 583 (618) | 581 (590) |
| N @ 736 | 1949 | 1922 |
| Conception cessation | 915 | 905 |
| Decline onset / collapse onset | 662 / 1300 | 612 / 1300 |
| N @ 1200 / 1400 / 1600 | 1515 / 480 / 0 | 1560 / 373 / 1 |
| births / conceptions | 15,145 / 2,295 | 14,299 / 2,161 |
| mean rel. error (canonical 5 / extended 8) | 0.046 / 0.047 | 0.070 / 0.087 |

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 73 | 20 | 0 | 0.99 | 140 |
| 300 | 489 | 159 | 67 | 0.52 | 629 |
| 400 | 1228 | 581 | 336 | 0.35 | 1820 |
| 500 | 2077 | 1406 | 987 | 0.25 | 4076 |
| 600 | 2100 | 1940 | 1516 | 0.20 | 3340 |
| 700 | 1963 | 1931 | 1518 | 0.21 | 2501 |
| 800 | 1852 | 1843 | 1445 | 0.21 | 1652 |
| 900 | 1804 | 1782 | 1404 | 0.20 | 773 |
| 1000 | 1723 | 1723 | 1358 | 0.20 | 201 |
| 1100 | 1670 | 1670 | 1318 | 0.20 | 13 |
| 1200 | 1515 | 1515 | 1229 | 0.18 | 0 |
| 1300 | 1113 | 1113 | 973 | 0.14 | 0 |
| 1400 | 480 | 480 | 466 | 0.10 | 0 |
| 1500 | 52 | 52 | 50 | 0.18 | 0 |
| 1600 | 0 | 0 | 0 | 1.00 | 0 |

Twelve seeds (7000–7011), 400 d, mean ± se:

| | 6 tpd | 24 tpd |
|---|---:|---:|
| N @ 200 | 80 ± 8 | 71 ± 6 |
| N @ 315 | 475 ± 49 | 466 ± 42 |
| N @ 400 | 1176 ± 89 | 1193 ± 81 |
| births by day 400 | 2513 ± 223 | 2519 ± 217 |

Twelve seeds (7000–7011), 800 d, mean ± se (`_output/multiseed_peak_p2k.txt`):

| | 6 tpd | 24 tpd | paired 24 − 6 |
|---|---:|---:|---:|
| Peak N (daily max) | 2269 ± 11 | 2281 ± 8 | +12 ± 17 |
| 31-day mean peak | 2214 ± 10 | 2219 ± 7 | +4 ± 15 |
| Peak day (31-d mean max) | 555 ± 12 | 546 ± 12 | -10 ± 15 |
| Peak day (raw max) | 553 ± 12 | 552 ± 15 | -0 ± 19 |
| Peak day (first ≥97 %) | 524 ± 9 | 521 ± 9 | -3 ± 14 |
| Surviving births cease | 602 ± 12 | 604 ± 11 | +2 ± 17 |
| N @ 736 | 1990 ± 15 | 1992 ± 13 | +1 ± 21 |

**Honest misses / open gaps**
- *Early phase low and seed-dominated* (unchanged): N@315 475 ± 49 over 12 seeds (−23 %),
  adults@315 172 ± 18 (+15 %); three training seeds are not enough to fit it, and the one
  candidate that did (trial 93) did not generalise.
- *N@736 3 % low* (1991 ± 15; 1949 at seed 7000), the raw peak 3 % high (2269 ± 11; the
  smoothed plateau 2214 ± 10 is within 1 %): the count at the maximum still carries ≈290 pups that
  will die while births run at ≈1000 per 30 days.
- *Peak day*: 555 ± 12 under the smoothed-maximum definition (Calhoun 560); the 97 %-day is
  524 ± 9 — a flat 100-day plateau has no sharp maximum, and Calhoun's single census day cannot
  tell which statistic it corresponds to.
- *Late collapse steep* (unchanged): 1515 at 1200, 480 at 1400, 0 at 1600 vs Calhoun 122 at ≈1444, 27 at 1588.
- *Pup survival in the uncrowded phase is low* (unchanged, ≈30–45 % to weaning).
- *Calibration method*: the objective (multi-seed mean, inverse-variance weights) is sound but a
  3-seed training set still lets realisation luck in the early phase lead the search; candidates
  must be scored on 12 seeds. CMA-ES in raw units barely moves the day-valued parameters.
- *Warp*: the brake and the nursing terms are host-side; `density_stress_kernel` parity 1.9e-9.

## Phase 2j — inverse-seed-variance loss weights, multi-seed recalibration (2026-10-31)

Motivation: in 2i the multi-seed CMA-ES lowered the loss by fitting N@315 at the training seeds
while the peak went 13 % high and conceptions ended 16 % late, and the N@315 gain did not
generalise. The hand weights (N@315 2.0, peak 2.0, …) priced a 13 % peak miss at 2 × 0.13² ≈ 0.03
against N@315 at 415 (2 × 0.33² ≈ 0.22), while N@315 is set by the first litters' luck at 8
founders.

### Seed spread of the landmarks (phase-2i calibration, 12 seeds 7000–7011, 1200 d, 6 ticks/day)

| landmark | Calhoun | mean | sd | sd / target | weight before | **weight 2j** |
|---|---:|---:|---:|---:|---:|---:|
| First litters (day) | 104 | 102.5 | 1.0 | 0.010 | 1.5 | **2.91** |
| N @ 315 | 620 | 475 | 169 | 0.273 | 2.0 | **0.10** |
| Peak N | 2200 | 2269 | 39 | 0.018 | 2.0 | **2.68** |
| Peak day (first ≥97 %) | 560 | 524 | 32 | 0.058 | 1.5 | **1.29** |
| Surviving births cease | 600 | 602 | 42 | 0.070 | 1.5 | **1.02** |
| N @ 736 | 2056 | 1991 | 54 | 0.026 | 1.5 | **2.38** |
| Adults @ 315 | 150 | 172 | 63 | 0.420 | 1.0 | **0.04** |
| Conception cessation | ≈920 | 923 | 44 | 0.048 | 1.0 | **1.57** |

`calib/priors.py`: w_k ∝ 1 / (rel_sd_k² + 0.05²), normalised to the previous total of 12
(`LANDMARK_REL_SEED_SD`, `NOISE_FLOOR`, `inverse_variance_weights`). Each loss term is then
(rel. error / σ_k)² up to a common factor — how many noise sigmas the model is off — with a 5 %
modelling tolerance in quadrature so the first-litters day (sd 1 %) does not dominate. Under
these weights a one-sigma miss costs the same on every landmark; a 13 % peak miss costs more than
three times a one-sd N@315 miss (`tests/test_calib_loss.py`). Loss values of the studies before
2j (`calibration_study_p2*.json` up to p2i) are on the old scale and not comparable.

### Multi-seed CMA-ES under the new weights (112 trials, popsize 14, train seeds 7000 / 7001 / 7002, `--sigma0 0.1`, 51 min)

No trial beat the start point (the 2i parameters): mean loss 0.0328 (per seed 0.019 / 0.039 /
0.041). The largest terms are now peak day and N@736 at seed 7000, and N@315 at the two slow
training seeds, where it sits 35–50 % below the target and still costs 0.012–0.024 at weight 0.1.
Runner-ups, mean over the training seeds:

| trial | mean loss | peak N / day | surviving births cease | N @ 736 | conception cessation | N @ 315 | first litters | main moves from the start |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **0 (2i, kept)** | **0.033** | 2270 / 527 | 602 | 2008 | 906 | 415 | 103 | — |
| 78 | 0.042 | 2225 / 548 | 611 | 1985 | 994 | 369 | 98 | erosion 0.73, courtship 0.013, ramp 0.10 |
| 86 | 0.051 | 2327 / 535 | 652 | 2108 | 893 | 368 | 101 | disturbance onset 0.31, overcrowd 0.20, ramp 0.10 |
| 57 | 0.058 | 2081 / 539 | 660 | 2003 | 953 | 300 | 103 | erosion 0.70, imprint 0.048, coef 2.4 |
| 32 | 0.062 | 2194 / 552 | 676 | 1985 | 1009 | 408 | 100 | coef 8.6, courtship 0.065 |

Under the old weights the same search drifted to a +13 % peak bought with N@315 (2i); under the
new ones every runner-up is a plateau trade-off — a later peak day paid for with a later
cessation of conceptions or of surviving births, or an early first litter — and N@315 is left
alone. The weights do what they were meant to; they do not by themselves produce a later phase C.
**The 2i point stays the calibration.** Held-out losses on the new scale 0.031 / 0.060 / 0.118
(mean 0.070). Artifact: `configs/calibration_study_p2j.json`.

### Validation

Parameters unchanged from 2i, so the 2i validation applies unchanged (the NumPy path is
deterministic for a fixed seed): seed 7000, 1600 d, 6 ticks/day — peak 2234 @ 518, surviving
births cease 583, N@736 1949, conceptions cease 915, canonical error 0.057; 12 seeds, 800 d —
peak 2269 ± 11 @ 524 ± 9, N@736 1990 ± 15, cessation 602 ± 12, 6 vs 24 ticks/day within noise.
Test suite green with `tests/test_calib_loss.py` added.

**Honest misses / open gaps**
- The model gaps are those of 2i (peak day ≈35 d early, N@736 3 % low, early phase
  seed-dominated, steep late collapse, low uncrowded pup survival): this pass changed the
  objective, not the model.
- *The weights are measured under one calibration.* `LANDMARK_REL_SEED_SD` is the 2i spread; a
  model with a very different plateau variance would need re-measuring (12 seeds × 1200 d ≈ 3 min
  with `scripts/seed_eval.py`; sd = se × √12). The 5 % floor is a judgement: without it the
  first-litters day (sd 1 %) would take ≈60 % of the total weight.
- *Three training seeds still leave N@315 noisy* (se ≈ 100): the term is small now, but a slow
  training seed (7002: N@315 315) still contributes the largest single term at that seed. More
  seeds per trial, or reporting N@315 / adults@315 without fitting them, are the options.
- *CMA-ES step size*: `--sigma0 0.1` in raw units barely moves the day-valued parameters
  (`max_age_days`, `female_fertile_max_age_days`, `first_conception_min_day`); a normalised search
  space is still open.
- *A later phase C needs a new mechanism*, not a re-weighting: the runner-ups buy peak day 548–552
  with conceptions ending at 994–1009 or surviving births at 660–676.

## Phase 2i — nursing-disturbance brake on phase C, fertility floor (negative), multi-seed calibration (2026-10-31)

Motivation: after 2h the 12-seed peak matched Calhoun (2221 vs 2200) but the peak day was ≈85
days early (475 ± 8) and N@736 9 % low (1869 ± 11): days 300–420 still grew ≈3× faster than
Calhoun's phase C, and the count at the peak carried ≈290 pups that would die.

### (A) Fertility tied to the female's breakdown state — negative

`fertility_cap_floor` (1 = off): the daily conception probability is scaled by
floor + (1 − floor) × `maternal_cap`. Calhoun's phase D: the incidence of pregnancies declined
rapidly after the peak. Scan at the 2h parameters, seed 7000, 1200 d:

| floor | 1 (2h) | 0.5 | 0.35 | 0.2 |
|---|---:|---:|---:|---:|
| peak N / day | 2115 / 503 | 2072 / 472 | 2091 / 460 | 2090 / 464 |
| surviving births cease | 551 | 573 | 596 | 567 |
| N @ 736 | 1845 | 1826 | 1792 | 1823 |
| conception cessation | 932 | 934 | 901 | 823 |
| loss | 0.094 | 0.115 | 0.127 | 0.133 |

Why it fails: the doomed pups sit in the *peak* count, not in N@736 (1845 = 1810 adults + 35
pups), so cutting the conceptions of partly-eroded females (capacity 0.3–0.9 during days
400–500) removes litters that still partly survive — the adult plateau falls more than the pup
stock, N@736 drops and the peak day moves earlier. Kept in the code and in the search space
(off at 1.0); the optimiser did not pick it up (the ten best trials of the multi-seed study kept it
at 0.83–0.99).

### (B) Nursing disturbance — a reversible, density-graded brake on phase C

`nurse_disturb_coef`, `nurse_disturb_density`: a mother's effective maternal investment while
nursing (passive and active, `_feed_by_nest`) is scaled by exp(−coef × max(0, local cell
density − onset)). Reversible and graded, unlike the erosion terms — it slows growth without
ending surviving births. Calhoun's phase C: nursing females in crowded cells were disturbed,
moved litters and dropped young; infant mortality rose with density before the social
breakdown. Both new terms off → bit-identical to 2h (hash `0f4ca337…`, 600 d, 6 ticks/day).

Scan at seed 7000, 1200 d (2h parameters unless noted; courtship erosion 0.03):

| coef / onset / ramp | 0 / – / 0.45 (2h) | 1 / 0.15 / 0.45 | 2 / 0.15 / 0.45 | 4 / 0.15 / 0.45 | 2 / 0.25 / 0.45 | 2 / 0.15 / 0.2 | 4 / 0.15 / 0.2 | 4 / 0.15 / 0.3 | **4 / 0.2 / 0.2** | 6 / 0.15 / 0.2 | 6 / 0.2 / 0.3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N @ 315 | 531 | 522 | 473 | 514 | 540 | 473 | 514 | 514 | **528** | 445 | 531 |
| peak N / day | 2115 / 503 | 2248 / 476 | 2133 / 491 | 2032 / 509 | 2140 / 476 | 2309 / 500 | 2265 / 522 | 2215 / 516 | **2209 / 511** | 2122 / 564 | 2129 / 500 |
| surviving births cease | 551 | 546 | 547 | 629 | 579 | 576 | 593 | 606 | **610** | 916 | 627 |
| N @ 736 | 1845 | 1886 | 1786 | 1807 | 1839 | 2006 | 1982 | 1961 | **1997** | 2009 | 1907 |
| conception cessation | 932 | 872 | 984 | 1033 | 962 | 912 | 997 | 984 | **1031** | 1198 | 982 |
| loss | 0.094 | 0.118 | 0.185 | 0.135 | 0.097 | 0.144 | 0.088 | 0.088 | **0.080** | 0.672 | 0.093 |

Reading: the brake alone (coef 4, ramp 0.45) slows phase C — surviving births cease at 629
(Calhoun 600) — but lowers the plateau (2032), because the ramp was tuned to end births for a
faster-growing population. Narrowing the ramp back to 0.2 restores the level while the brake
keeps the timing: peak 2209 at 511, cessation 610, N@736 1997 (N@736 / peak 0.90; 2h 0.87,
Calhoun 0.93). Too strong a brake (coef 6 at onset 0.15) keeps births surviving to 916 and cuts
N@315 (445): mice cluster, so cells pass local density 0.15 already in phase B. Courtship
erosion then pulls the conception cessation back: 0.04 → 915 (peak 2234 / 518, cessation 583,
N@736 1949, loss 0.066), 0.05 → 879 (2200 / 511, 599, 1968, 0.068).

Held-out at coef 4 / onset 0.2 / ramp 0.2 (courtship 0.03), 1200 d: seed 8000 peak 2270 / 533,
cessation 605, N@736 2033, conceptions cease 968; 8001 2298 / 465, 555, 1942, 912; 8002 2207 /
606, 754, 2109, 1099 (the slow seed: N@315 286, everything ≈50 d later).

### Multi-seed objective (`--train-seeds`)

Each CMA-ES trial now runs one simulation per training seed and is scored by the mean loss
(`calib/optimize.py::_combine`; per-seed results kept in the study report). In 2g and 2h the
single-seed optimiser never beat its hand-chosen start point: a parameter nudge is a new random
realisation and loss differences of ≈0.02 are inside that noise. Three training seeds cost 3×
per generation (≈10 min at 14 workers for popsize 14).

### Recalibration (multi-seed CMA-ES, 112 trials, popsize 14, `--sigma0 0.1`, 51 min)

Start = 2h optimum + ramp 0.2 + nursing disturbance 4 / 0.2 + courtship 0.04 (fertility floor
1.0). Mean landmarks over the training seeds 7000 / 7001 / 7002 (1200 d):

| trial | mean loss | mean canonical error | peak N / day | surviving births cease | N @ 736 | conception cessation | N @ 315 | main parameter moves from the start |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **0 (start, kept)** | 0.341 | 0.093 | 2270 / 527 | 602 | 2008 | 906 | 415 | — |
| 99 (best loss) | 0.243 | 0.083 | 2484 / 521 | 602 | 2193 | 1060 | 509 | erosion 0.49, ramp 0.07, imprint 0.012, boost 0.15, coef 2.4 |
| 78 | 0.249 | 0.073 | 2418 / 537 | 613 | 2252 | 809 | 523 | erosion 0.34, boost 0.13, courtship 0.059, ramp 0.12 |
| 47 | 0.250 | 0.098 | 2199 / 484 | 571 | 1974 | 722 | 454 | boost 0.06, coef 1.9, courtship 0.058 |
| 92 | 0.266 | 0.087 | 2211 / 475 | 583 | 1962 | 745 | 508 | boost 0.09, coef 2.3, base mortality 6.3e-5 |

The multi-seed objective does move (the single-seed one never left its start in 2g / 2h), but
where it moves is set by the loss weights: trial 99 buys N@315 at the training seeds (415 → 509)
with the peak (+13 %) and the conception cessation (+16 %), and the N@315 gain does not generalise
— held-out N@315 180 / 240 / 585, canonical error 0.19 / 0.18 / 0.07, mean held-out loss 0.96
(start: 0.10 / 0.08 / 0.17, 0.45). Trial 78 is the best by mean canonical error, but over 12 seeds
(800 d, 6 ticks/day) it sits 9–10 % high on three landmarks: peak 2395 ± 9 at 552 ± 12, N@736
2258 ± 14, cessation 658 ± 17, against the start's 2269 ± 11 at 524 ± 9, 1991 ± 15, 602 ± 12
(Calhoun 2200 / 560 / 2056 / 600). **The start point was kept** as the phase-2i calibration.

*Method finding.* Squared relative error makes a 10–15 % miss on a plateau landmark cheap
(2 × 0.13² ≈ 0.03) next to N@315 at 415 (2 × 0.33² ≈ 0.22), while N@315 has a seed sd of ≈35 % at
8 founders — so the optimiser spends the peak on noise. Next method step: weight landmarks by
the inverse of their seed variance (or report N@315 / adults@315 without fitting them).
Artifacts: `configs/calibrated_calhoun.yaml`, `configs/default.yaml`,
`configs/calibration_study_p2i.json` (per-seed results in every trial record).

Phase C with the brake (seed 7000, 6 ticks/day, 30-day windows; compare the 2g/2h table above):

| day | N | conceptions | births | reached weaning | weaned / born | mean stress | maternal cap (adult F) | weaned density |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 300 | 657 | 65 | 328 | 147 | 0.45 | 0.14 | 1.00 | 0.12 |
| 360 | 1263 | 151 | 815 | 231 | 0.28 | 0.22 | 1.00 | 0.23 |
| 420 | 1799 | 189 | 1196 | 258 | 0.22 | 0.28 | 0.97 | 0.36 |
| 480 | 2115 | 160 | 1186 | 191 | 0.16 | 0.45 | 0.81 | 0.47 |
| 540 | 2148 | 136 | 997 | 87 | 0.09 | 0.55 | 0.27 | 0.52 |
| 600 | 2090 | 127 | 915 | 6 | 0.01 | 0.56 | 0.11 | 0.52 |

The weaned fraction now fades over ≈270 days (0.45 at 300 → 0.01 at 600) instead of collapsing in
90, and the plateau is reached at 510–550 (raw maximum 2234 at 545 with 288 pups and 242
juveniles aboard; 31-day mean maximum 2187 at 550). Growth between 300 and 420 is still ×2.7
(Calhoun ≈×1.7).

### Validation

1600 d, seed 7000, 6 ticks/day (`_output/run1600_p2i_tpd6`, 87 s, 0 NaN; phases decline
662 → collapse 1300) and 24 ticks/day (`_output/run1600_p2i_tpd24`, 147 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 103 |
| N @ 315 | 528 | 514 |
| Peak N / day | 2234 / 518 | 2274 / 486 |
| Surviving births cease (strict latest pup) | 583 (618) | 581 (590) |
| N @ 736 | 1949 | 1922 |
| Conception cessation | 915 | 905 |
| Decline onset / collapse onset | 662 / 1300 | 612 / 1300 |
| N @ 1200 / 1400 / 1600 | 1515 / 480 / 0 | 1560 / 373 / 1 |
| births / conceptions | 15,145 / 2,295 | 14,299 / 2,161 |
| mean rel. error (canonical 5 / extended 8) | 0.057 / 0.054 | 0.076 / 0.091 |

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 73 | 20 | 0 | 0.99 | 140 |
| 300 | 489 | 159 | 67 | 0.52 | 629 |
| 400 | 1228 | 581 | 336 | 0.35 | 1820 |
| 500 | 2077 | 1406 | 987 | 0.25 | 4076 |
| 600 | 2100 | 1940 | 1516 | 0.20 | 3340 |
| 700 | 1963 | 1931 | 1518 | 0.21 | 2501 |
| 800 | 1852 | 1843 | 1445 | 0.21 | 1652 |
| 900 | 1804 | 1782 | 1404 | 0.20 | 773 |
| 1000 | 1723 | 1723 | 1358 | 0.20 | 201 |
| 1100 | 1670 | 1670 | 1318 | 0.20 | 13 |
| 1200 | 1515 | 1515 | 1229 | 0.18 | 0 |
| 1300 | 1113 | 1113 | 973 | 0.14 | 0 |
| 1400 | 480 | 480 | 466 | 0.10 | 0 |
| 1500 | 52 | 52 | 50 | 0.18 | 0 |
| 1600 | 0 | 0 | 0 | 1.00 | 0 |

Twelve seeds (7000–7011), 400 d, mean ± se:

| | 6 tpd | 24 tpd |
|---|---:|---:|
| N @ 200 | 80 ± 8 | 71 ± 6 |
| N @ 315 | 475 ± 49 | 466 ± 42 |
| N @ 400 | 1176 ± 89 | 1193 ± 81 |
| births by day 400 | 2513 ± 223 | 2519 ± 217 |

Twelve seeds (7000–7011), 800 d, mean ± se (`_output/multiseed_peak_p2i.txt`):

| | 6 tpd | 24 tpd | paired 24 − 6 |
|---|---:|---:|---:|
| Peak N (daily max) | 2269 ± 11 | 2281 ± 8 | +12 ± 17 |
| 31-day mean peak | 2214 ± 10 | 2219 ± 7 | +4 ± 15 |
| Peak day (first ≥97 %) | 524 ± 9 | 521 ± 9 | -3 ± 14 |
| Surviving births cease | 602 ± 12 | 604 ± 11 | +2 ± 17 |
| N @ 736 | 1990 ± 15 | 1992 ± 13 | +1 ± 21 |

**Honest misses / open gaps**
- *Peak day ≈35 d early* (518 at seed 7000; 12 seeds 524 ± 9; Calhoun 560; 2h: 85 d early).
  Phase C is still ×2.7 between days 300 and 420 against Calhoun's ≈×1.7; the brake acts on pup
  survival, not on the conception rate, and births run at 1000–1200 per 30 days through day 540.
  On the long flat plateau the first-≥97 % day (518) sits ≈30 d before the maximum (545–550).
- *N@736 3 % low* (1949; 12 seeds 1991 ± 15; 2h: 9 % low). N@736 / peak 0.87–0.88 (Calhoun 0.93):
  the raw maximum still carries ≈290 pups that will die, because births to eroded mothers continue
  at ≈1000 per 30 days while the weaned fraction fades. The fertility floor (A) does not fix this
  (it removes partly-surviving litters first).
- *Early phase seed-dominated* (unchanged): N@315 255–758 over 12 seeds (475 ± 49), adults@315
  88–217 over the four calibration seeds; the training seed is 15 % low on N@315.
- *Late collapse steep* (unchanged): 1515 at 1200, 480 at 1400, 0 at 1600 vs Calhoun 122 at ≈1444, 27 at 1588; collapse
  onset 1300. A per-individual lifespan distribution would spread it.
- *Pup survival in the uncrowded phase is low* (unchanged, ≈30–45 % to weaning).
- *Loss weighting* (above): the multi-seed objective is now limited by the weights, not by noise.
- *Warp*: the nursing brake lives in the host-side `_feed_by_nest` (nursing was host-only before);
  `density_stress_kernel` parity 1.9e-9 unchanged; mortality kernel untested at hazard level.

## Phase 2h — graded social-breakdown pressure, recalibration (2026-10-31)

Motivation: the peak sat 12–18 % above Calhoun's 2200 and ≈60 days early (2482 at 493, held-out
2453–2608 at 434–603) through phases 2e–2g, while the plateau-to-N@736 decline already matched.

### Diagnosis (phase-2g run, seed 7000, 6 ticks/day, 30-day windows)

| day | N | conceptions | births | reached weaning | weaned / born | mean stress | maternal cap (adult F) | weaned density |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 300 | 662 | 80 | 303 | 163 | 0.54 | 0.16 | 1.00 | 0.12 |
| 330 | 852 | 77 | 459 | 150 | 0.33 | 0.18 | 1.00 | 0.16 |
| 360 | 1351 | 130 | 792 | 348 | 0.44 | 0.27 | 1.00 | 0.25 |
| 390 | 1731 | 141 | 848 | 308 | 0.36 | 0.30 | 0.98 | 0.33 |
| 420 | 2176 | 115 | 978 | 475 | 0.49 | 0.37 | 0.91 | 0.45 |
| 450 | 2317 | 112 | 756 | 322 | 0.43 | 0.43 | 0.74 | 0.54 |
| 480 | 2375 | 92 | 650 | 158 | 0.24 | 0.42 | 0.59 | 0.57 |
| 510 | 2368 | 51 | 487 | 91 | 0.19 | 0.68 | 0.25 | 0.59 |
| 540 | 2339 | 53 | 333 | 31 | 0.09 | 0.72 | 0.07 | 0.59 |
| 570 | 2259 | 54 | 233 | 2 | 0.01 | 0.67 | 0.02 | 0.58 |

- *Phase C is too fast and ends too abruptly.* From day 300 to 420 the population triples
  (doubling every ≈36 days; Calhoun's phase C doubled every ≈145 days) with the weaned fraction
  flat at 0.35–0.5; then the weaned-density switch (0.58) trips at ≈480, mean stress jumps
  0.42 → 0.68 in one window, maternal capacity falls 0.59 → 0.07 in 60 days and surviving births
  end. Calhoun's phase C was a gradual rise in infant mortality from Day 315 on, not a switch.
- *The raw peak is a spike on the plateau.* Daily maximum 2482 at 521 with 261 pups and 207
  juveniles aboard; the 31-day running mean peaks at 2404 and N is 2323 at 560 and 2291 at 600.
  Litters arrive in pulses and the pups born to eroded mothers live ≈4 days, so the daily maximum
  of the series sits 3–4 % above the level around it. Calhoun's 2200 is one census, not a maximum.
  `peak_n_31d_mean` is now reported in `calibration.json` (not fitted).
- *The post-peak decline is Calhoun-like once the pup stock is gone.* Adults 2219 at 570 →
  2137 at 720 (−3.7 % in 150 d; Calhoun 2200 → 2056 is −6.5 % in 176 d); the rest of the raw
  drop to N@736 is the doomed pups in the pipeline at the peak dying.

### Change (NumPy path + Warp `density_stress_kernel`, parity 1.9e-9)

**Graded breakdown pressure.** `breakdown_density_ramp` (width in weaned-density units, 0 = the
2e–2g step): the social-breakdown stress boost ramps linearly from 0 at `threshold − ramp` to its
full value at `breakdown_density_threshold` (`BiologyConfig.breakdown_factor`). Social pressure
now builds as the arena fills instead of switching on at one density, so maternal erosion (which
integrates stress above its threshold) starts earlier and surviving births fade over ≈150 days
instead of 90. Width 0 is bit-identical to phase 2g (hash `4bb07c88…`, 600 d, 6 ticks/day). The
ramp has no toggling problem: unlike the 2e thermostat on total N, the factor is monotone in a
density that falls only through adult mortality.

Scan at the 2g parameters (threshold 0.58, boost 0.248), seed 7000, 1200 d:

| ramp width | 0 (2g) | 0.15 | 0.30 | 0.45 |
|---|---:|---:|---:|---:|
| peak N / day (first ≥97 %) | 2482 / 493 | 2345 / 473 | 2235 / 480 | 2115 / 503 |
| surviving births cease | 547 | 546 | 528 | 551 |
| N @ 736 | 2173 | 1999 | 1912 | 1845 |
| conception cessation | 930 | 885 | 864 | 932 |
| loss | 0.120 | 0.109 | 0.113 | **0.094** |
| mean rel. error (5) | 0.100 | 0.095 | 0.088 | 0.077 |

The ramp alone lowers the plateau (and the peak with it) but N@736 follows at a near-constant
ratio of ≈0.87 (Calhoun 0.93): with a lower total density the conception suppression
(`menopause_density_threshold`) bites less, so conceptions stay at 124–139 per 30 days through
day 540 (2g: 51–53) and ≈800–950 pups per 30 days are born to eroded mothers and die within days,
keeping a stock of 140–180 doomed pups in the peak count. The peak day does not move (473–503).

### Recalibration (CMA-ES 168 trials, `--sigma0 0.1`, start = 2g optimum + ramp 0.45)

No trial beat the start point in twelve generations (40 min; next best 0.165), as in 2g, so the
phase-2h parameters are the 2g optimum plus `breakdown_density_ramp` 0.45. Artifacts:
`configs/calibrated_calhoun.yaml`, `configs/default.yaml`, `configs/calibration_study_p2h.json`.
Landmarks at 1200 d (rate-based cessation days):

| Landmark | Calhoun | **7000** (train) | 8000 | 8001 | 8002 |
|---|---:|---:|---:|---:|---:|
| First litters (day) | 104 | **102** | 102 | 105 | 102 |
| N @ day 315 | 620 | 531 | 487 | 564 | 286 |
| Adults @ day 315 | 150 | 163 | 217 | 177 | 88 |
| Peak N / day (first ≥97 %) | 2200 / 560 | **2115 / 503** | 2162 / 482 | 2328 / 421 | 2127 / 565 |
| Surviving births cease | 600 | **551** | 537 | 488 | 615 |
| N @ day 736 | 2056 | **1845** | 1838 | 1894 | 1916 |
| Conception cessation | ≈920 | **932** | 952 | 812 | 1011 |
| N @ 1200 | | 1426 | 1422 | 1473 | 1524 |
| loss | | 0.094 | 0.356 | 0.223 | 0.772 |
| mean rel. error (canonical 5) | | **0.077** | 0.099 | 0.119 | 0.125 |

Against 2g (0.100 / 0.111 / 0.146 / 0.172; peaks 2482 / 2453 / 2608 / 2458; N@736 2173 / 2182 /
2158 / 2285): the peak moves from +12–18 % to −4…+6 % at all four seeds and the canonical error
falls at all four; N@736 moves from +5–11 % to −7…−11 %. Held-out mean loss 0.45 (2g 0.49),
still dominated by the seed spread of N@315 / adults@315.

*Calibration method note.* Each trial is one realisation at seed 7000, and the optimiser could
not improve on its start point in either 2g or 2h: differences of ≈0.02 in loss are within the
realisation noise of the landmarks (a parameter nudge is a new random draw), so CMA-ES at this
budget is confirming hand-chosen 1-D scans rather than finding optima. A multi-seed objective
(mean loss over 2–3 seeds per trial, ≈3× the cost) is the next step for the method.

### Validation

1600 d, seed 7000, 6 ticks/day (`_output/run1600_p2h_tpd6`, 77 s, 0 NaN; phases decline
671 → collapse 1291) and 24 ticks/day (`_output/run1600_p2h_tpd24`, 151 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 103 |
| N @ 315 | 531 | 513 |
| Peak N / day | 2115 / 503 | 2389 / 482 |
| Surviving births cease (strict latest pup) | 551 (648) | 510 (532) |
| N @ 736 | 1845 | 1948 |
| Conception cessation | 932 | 805 |
| Decline onset / collapse onset | 671 / 1291 | 550 / 1284 |
| N @ 1200 / 1400 / 1600 | 1426 / 273 / 0 | 1515 / 181 / 2 |
| births / conceptions | 12,745 / 1,939 | 10,767 / 1,644 |
| mean rel. error (canonical 5 / extended 8) | 0.077 / 0.073 | 0.111 / 0.122 |

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 73 | 20 | 0 | 0.99 | 140 |
| 300 | 503 | 157 | 66 | 0.53 | 631 |
| 400 | 1381 | 608 | 380 | 0.31 | 1828 |
| 500 | 2005 | 1593 | 1295 | 0.18 | 3155 |
| 600 | 2028 | 1877 | 1564 | 0.17 | 2824 |
| 700 | 1879 | 1836 | 1529 | 0.17 | 2206 |
| 800 | 1774 | 1759 | 1463 | 0.17 | 1271 |
| 900 | 1687 | 1680 | 1401 | 0.17 | 513 |
| 1000 | 1627 | 1627 | 1364 | 0.16 | 145 |
| 1100 | 1567 | 1567 | 1326 | 0.16 | 32 |
| 1200 | 1426 | 1426 | 1231 | 0.14 | 0 |
| 1300 | 1020 | 1020 | 940 | 0.11 | 0 |
| 1400 | 273 | 273 | 257 | 0.13 | 0 |
| 1500 | 33 | 33 | 28 | 0.22 | 0 |
| 1600 | 0 | 0 | 0 | 1.00 | 0 |

Twelve seeds (7000–7011), 400 d, mean ± se:

| | 6 tpd | 24 tpd |
|---|---:|---:|
| N @ 200 | 80 ± 8 | 71 ± 6 |
| N @ 315 | 479 ± 49 | 470 ± 46 |
| N @ 400 | 1316 ± 112 | 1399 ± 109 |
| births by day 400 | 2524 ± 232 | 2524 ± 209 |

### Resolution and seed spread (12 seeds 7000–7011, 800 d, `_output/multiseed_peak_p2h.txt`)

| | 6 tpd | 24 tpd | paired 24 − 6 |
|---|---:|---:|---:|
| N @ 400 | 1316 ± 112 | 1399 ± 109 | +83 ± 170 |
| Peak N (daily max) | **2221 ± 21** | 2266 ± 16 | +45 ± 32 |
| 31-day mean peak | 2153 ± 20 | 2209 ± 17 | +56 ± 32 |
| Peak day (first ≥97 %) | 475 ± 8 | 466 ± 8 | −9 ± 13 |
| Surviving births cease | 542 ± 11 | 526 ± 10 | −16 ± 16 |
| N @ 736 | 1869 ± 11 | 1912 ± 11 | +44 ± 16 |

(mean ± se; sd of the peak across seeds 74 / 55.) The 12-seed mean peak is 2221 (Calhoun 2200)
with the 24-tick runs ≈2 % higher; the seed-7000 pair (2115 at 6 tpd vs 2389 at 24 tpd) is
realisation spread, not resolution. Under the ramp the plateau level depends on how fast a
realisation grows (erosion integrates stress over time), so single-seed peaks scatter by ±3 % and
the training seed sits 5 % below the 12-seed mean.

**Honest misses / open gaps**
- *Peak day ≈85 d early* (475 ± 8 across 12 seeds; 503 at the training seed; Calhoun 560): the
  ramp lowered the plateau but did not delay it. Growth between days 300 and 420 is still ≈3×
  faster than Calhoun's phase C, and the plateau day is set by when the ramp (from weaned density
  0.13, ≈ day 300–330) starts eroding maternal capacity. A later, slower phase C needs a brake on
  growth that does not erode capacity — the main open item.
- *N@736 9 % low* (1869 ± 11; 1845 at seed 7000; Calhoun 2056): N@736 / peak is 0.84–0.87 vs
  Calhoun's 0.93. Adults decline at Calhoun's rate (1874 at 570 → 1798 at 720, −4 %); the gap is
  the ≈150 doomed pups in the peak count — conceptions stay at 124–139 per 30 days through day 600
  (2g: 51–53) because the conception suppression acts on total density, which is now lower, and
  800–950 pups per 30 days are born to eroded mothers and die within days. Lowering
  `menopause_density_threshold` to 0.55–0.60 does not help (peak day → 450, N@736 1834–1921, loss
  0.13–0.17). Candidate: a conception probability that declines with the female's own breakdown
  state (`maternal_cap`), which would cut the doomed births without touching pre-peak growth.
- *Surviving births cease ≈60 d early* (542 ± 11; held-out 488–615), coupled to the early peak.
- *Early phase seed-dominated* (unchanged): N@315 286–564 and adults@315 88–217 across the four
  calibration seeds; the training seed sits 14 % low on N@315.
- *Late collapse steep* (unchanged): 1426 at 1200, 273 at 1400, 0 at 1600 vs Calhoun 122 at ≈1444, 27 at 1588; the
  400–600 cohorts die of `max_age_days` (938) together.
- *Pup survival in the uncrowded phase is low* (unchanged, ≈30–40 % to weaning).
- *Calibration method*: the single-seed objective is noise-limited (above). The fast evaluator
  without `base_config` runs the pydantic defaults, which coincide with `configs/default.yaml`
  for the non-searched keys (checked: identical losses) — keep them in step.
- *Warp*: `density_stress_kernel` parity 1.9e-9 with the ramp branch exercised; mortality kernel
  mirrors the hazard form, untested at hazard level; nest kick, erosion and breeding passes are
  host-only.

## Phase 2g — male courtship breakdown, recalibration (2026-10-31)

Motivation: after the maternal breakdown (2e/2f) conceptions continued to 1063–1196 (Calhoun
≈920) because the competent cohort born before ≈300 kept conceiving until it passed
`female_fertile_max_age_days`. Calhoun's phase-D males had stopped courting and defending
territory; the model had no male-side breakdown.

### Change (NumPy path; daily host pass, no kernel change)

**Male courtship capacity** (`courtship_cap`, SoA, 1.0 at birth): once per day every weaned male
above `courtship_erosion_stress` loses `courtship_erosion_rate × excess`, irreversibly (mirror of
`maternal_cap`, `_daily_courtship_erosion`). The daily breeding pass uses, per cell, the mean of
`competence × courtship_cap` over the resident eligible males (was `competence` alone), so the
conception probability of every female in the cell decays with the males' accumulated exposure.
Off by default (rate 0); with it off the 6-tpd trajectory is bit-identical to phase 2f (hash
`d8661863…` for `configs/default.yaml`, 300 d). Logged as `mean_courtship_cap_adult_m`.

**Landmark made rate-based.** The first scan of the new parameter was non-monotone (strict
last-conception day 1148 / 1004 / 1026 / 1130 for rates 0.015 / 0.02 / 0.025 / 0.03 at threshold
0.5) and a CMA-ES study on it sat flat at 0.167 for seven generations: the strict "day of the
last conception" is one event among ~2 000 and swings by ±100 days with any parameter nudge
(each nudge is a new random realisation). `last_conception_day` is now the rate-based
cessation (`rate_cessation_day`: last day on which the 30-day conception count is still ≥ 5 % of
its maximum), the same statistic as for surviving births; the strict day is reported alongside
(`last_conception_strict_day`). Calhoun's "≈920" is itself a single event, so the comparison is
approximate either way.

Scan at the 2f parameters, seed 7000, 1200 d, threshold 0.5 (conception cessation / loss):

| rate | 0 (2f) | 0.015 | 0.02 | 0.025 | 0.03 | 0.04 | 0.05 |
|---|---:|---:|---:|---:|---:|---:|---:|
| conception cessation (day) | 1003 | 970 | 984 | 959 | **930** | 921 | 650 |
| loss | 0.135 | 0.142 | 0.134 | 0.134 | **0.120** | 0.145 | 0.215 |

(Under the rate-based measure the 2f gap was +9 % — 1003 vs 920 — not the +15–30 % the strict
day suggested; the strict 2f values 1063–1196 are in the 2f section.)

Smooth and monotone in the plateau 0.015–0.04, with a cliff at 0.05 where the courtship
capacity is destroyed during the peak excursion and conceptions end with the peak. The other
landmarks are untouched (peak 2447–2494 at 473–495, cessation of surviving births 510–547,
N@736 2150–2193). Threshold 0.6 is a weak lever (strict day 1069–1105 for 0.015–0.03).

### Recalibration results (CMA-ES 84 trials, `--sigma0 0.1`, start = 2f optimum + rate 0.03 / 0.5)

No trial beat the start point in six generations (13.5 min), so the phase-2g parameters are the
2f optimum plus `courtship_erosion_rate` 0.03 / `courtship_erosion_stress` 0.5. Artifacts:
`configs/calibrated_calhoun.yaml`, `configs/default.yaml`, `configs/calibration_study_p2g.json`.
Landmarks at 1200 d (rate-based cessation days; strict single-event days in parentheses):

| Landmark | Calhoun | **7000** (train) | 8000 | 8001 | 8002 |
|---|---:|---:|---:|---:|---:|
| First litters (day) | 104 | **102** | 102 | 105 | 102 |
| N @ day 315 | 620 | 531 | 487 | 564 | 286 |
| Adults @ day 315 | 150 | 163 | 217 | 177 | 88 |
| Peak N / day (first ≥97 %) | 2200 / 560 | 2482 / 493 | 2453 / 492 | 2608 / 434 | 2458 / 603 |
| Surviving births cease (strict) | 600 | **547** (700) | 550 (811) | 467 (502) | 666 (849) |
| N @ day 736 | 2056 | **2173** | 2182 | 2158 | 2285 |
| Conception cessation (strict) | ≈920 | **930** (1130) | 968 (1177) | 885 (994) | 1059 (1177) |
| N @ 1200 | | 1779 | 1767 | 1769 | 1919 |
| loss | | 0.120 | 0.359 | 0.272 | 0.848 |
| mean rel. error (canonical 5) | | 0.100 | 0.111 | 0.146 | 0.172 |

Conception cessation moved from 1003 / 1076–1196 (2f, rate-based / strict) to 930 / 885–1059,
the last of the eight Calhoun numbers to come within ~10 % at the training seed. Everything else
is the 2f fit (the courtship term only acts after the peak). Held-out mean loss 0.49 (2f 0.54).

### Validation

1600 d, seed 7000, 6 ticks/day (`_output/run1600_p2g_tpd6`, 138 s, 0 NaN; phases decline
622 → collapse 1312) and 24 ticks/day (`_output/run1600_p2g_tpd24`, 268 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 103 |
| N @ 315 | 531 | 513 |
| Peak N / day | 2482 / 493 | 2530 / 469 |
| Surviving births cease (strict latest pup) | 547 (700) | 502 (542) |
| N @ 736 | 2173 | 2185 |
| Conception cessation | 930 | 847 |
| Decline onset / collapse onset | 622 / 1312 | 619 / 1315 |
| N @ 1200 / 1400 / 1600 | 1779 / 391 / 6 | 1796 / 336 / 1 |
| births / conceptions | 10,575 / 1,593 | 8,198 / 1,251 |
| mean rel. error (canonical 5) | 0.100 | 0.132 |

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 73 | 20 | 0 | 0.99 | 140 |
| 300 | 503 | 157 | 66 | 0.53 | 631 |
| 400 | 1441 | 605 | 368 | 0.32 | 1806 |
| 500 | 2341 | 1819 | 1523 | 0.15 | 2911 |
| 600 | 2291 | 2218 | 1948 | 0.13 | 1322 |
| 700 | 2189 | 2170 | 1896 | 0.13 | 1341 |
| 800 | 2129 | 2109 | 1838 | 0.13 | 1284 |
| 900 | 2052 | 2044 | 1787 | 0.13 | 788 |
| 1000 | 1991 | 1991 | 1739 | 0.13 | 261 |
| 1100 | 1925 | 1925 | 1693 | 0.12 | 65 |
| 1200 | 1779 | 1779 | 1603 | 0.11 | 26 |
| 1300 | 1320 | 1320 | 1263 | 0.07 | 0 |
| 1400 | 391 | 391 | 384 | 0.07 | 0 |
| 1500 | 26 | 26 | 24 | 0.16 | 0 |
| 1600 | 6 | 6 | 6 | 0.20 | 0 |

Twelve seeds (7000–7011), 400 d, mean ± se:

| | 6 tpd | 24 tpd |
|---|---:|---:|
| N @ 200 | 80 ± 8 | 71 ± 6 |
| N @ 315 | 479 ± 49 | 471 ± 46 |
| N @ 400 | 1314 ± 115 | 1391 ± 111 |
| births by day 400 | 2524 ± 227 | 2522 ± 203 |

**Honest misses / open gaps**
- *Peak 12–18 % high* (2482; held-out 2453–2608) and *≈60 days early* (493; 434–603): unchanged
  from 2f — the optimiser trades the peak for N@736 and the cessation; the weaned-density switch
  caps the plateau, not the peak. Candidate: a density-dependent term in infant survival before
  the switch (Calhoun's phase-C infant mortality rose gradually).
- *Early phase seed-dominated*: N@315 286–564 and adults@315 88–217 across four seeds with 8
  founders; the training seed sits 14 % low on N@315.
- *Late collapse steep*: 1779 at 1200, 391 at 1400, 6 at 1600 vs Calhoun 122 at ≈1444, 27 at 1588; the 400–600 cohorts die
  of `max_age_days` (938) together. A per-individual lifespan distribution would spread it.
- *Pup survival in the uncrowded phase is low* (≈30–40 % to weaning): mothers spend ≈50 % of their
  time at the hoppers; litter 7.2 and conception p 0.79 compensate.
- *Single-event landmarks*: the strict last-conception and latest-weaned-pup days (1130 / 700 at
  the training seed) remain noisy by construction and are reported, not fitted.
- *Warp*: `density_stress_kernel` parity 9e-10; mortality kernel mirrors the hazard form,
  untested at hazard level; nest kick, erosion passes and breeding pass are host-only.

## Phase 2f — exact stress relaxation, per-decision kick/withdrawal, recalibration (2026-10-30)

Motivation: Phase 2e left a monotone early-growth excess at finer ticks (N@400 1065 / 1248 / 1331
at 6 / 12 / 24 ticks/day, 12 seeds) after the per-decision mechanics had been made equivalent by
construction. The remaining resolution-dependent pieces were the continuous processes.

### Changes (NumPy path and Warp `density_stress_kernel`, parity 9e-10)

1. **Exact stress relaxation.** `s += (gain/decay − s)·(1 − exp(−decay·dt))` replaces the Euler
   step `s += (gain − decay·s)·dt`. The Euler factor at dt = 1/6 with decay 0.87 was 0.855 per
   tick against the exact 0.865, i.e. ~1 % extra relaxation per tick at the reference and ~0.3 %
   at 24 tpd; stress hugged its equilibrium more tightly at coarse ticks, which changed how
   often the neglect / erosion / conception thresholds were crossed.
2. **Nest kick and stress-driven social withdrawal are per-decision events** (10 % chance and
   −0.05 on the decision tick) instead of per-tick rates ×k (Bernoulli per tick gave 4 % fewer
   kicks per decision at 24 tpd). The Warp kernel receives the event scale through a device
   buffer (1 on decision ticks, 0 on held ticks), so CUDA-graph replay stays valid.

Both change the 6-tpd reference trajectory (hash `02e9e2e5…` for `configs/default.yaml`,
300 d), so the biology was recalibrated.

### Resolution check before recalibration (phase-2e parameters, 12 seeds, 400 d, mean ± se)

| | 6 tpd | 12 tpd | 24 tpd |
|---|---:|---:|---:|
| N @ 200 | 58 ± 5 | 57 ± 6 | 74 ± 9 |
| N @ 315 | 417 ± 39 | 366 ± 45 | 443 ± 59 |
| N @ 400 | 1122 ± 96 | 1021 ± 103 | 1215 ± 126 |
| births by day 400 | 2234 ± 198 | 2205 ± 214 | 2616 ± 283 |

The monotone trend of phase 2e (+17 % / +25 % at day 400) is gone; the remaining differences
are within about one standard error and change sign between resolutions.

### Recalibration results (CMA-ES 168 trials, `--sigma0 0.1`, start = phase-2e optimum, 39 min)

The start point scores 0.216 under the exact relaxation (was 0.159); the study reached **0.151**
at trial 136. Artifacts: `configs/calibrated_calhoun.yaml`, `configs/default.yaml`,
`configs/calibration_study_p2f.json`. Landmarks at 1200 d:

| Landmark | Calhoun | **7000** (train) | 8000 | 8001 | 8002 |
|---|---:|---:|---:|---:|---:|
| First litters (day) | 104 | **102** | 102 | 105 | 102 |
| N @ day 315 | 620 | 531 | 487 | 564 | 286 |
| Adults @ day 315 | 150 | 163 | 217 | 177 | 88 |
| Peak N / day (first ≥97 %) | 2200 / 560 | 2502 / 502 | 2515 / 504 | 2602 / 429 | 2457 / 604 |
| Surviving births cease (day) | 600 | **533** | 554 | 467 | 654 |
| strict latest weaned pup (day) | (600) | 550 | 554 | 520 | 676 |
| N @ day 736 | 2056 | **2181** | 2223 | 2257 | 2251 |
| Last conception (day) | ≈920 | 1063 | 1076 | 1082 | 1196 |
| N @ 1200 | | 1756 | 1779 | 1804 | 1857 |
| loss | | 0.151 | 0.396 | 0.317 | 0.904 |
| mean rel. error (canonical 5) | | 0.103 | 0.111 | 0.148 | 0.169 |

Against phase 2e (train canonical 0.074; held-out 0.08 / 0.16 / 0.05) the training fit is a
little worse — the peak now overshoots by 12–18 % (2457–2602) — while the held-out spread is
tighter; the strict latest-weaned-pup day no longer drifts into the 1000s at any seed (lethal
starvation + exact relaxation). The 8002 loss is the early-phase seed fluctuation (N@315 286,
adults 88). The one systematic miss is unchanged: last conception 1063–1196 vs ≈920.

### Resolution check at the new parameters

1600 d, seed 7000 (`_output/run1600_p2f_tpd6`, `_output/run1600_p2f_tpd24`):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 102 | 103 |
| N @ 315 | 531 | 513 |
| Peak N / day | 2502 / 502 | 2580 / 477 |
| Surviving births cease (strict latest pup) | 533 (550) | 513 (537) |
| N @ 736 | 2181 | 2235 |
| Last conception | 1063 | 1087 |
| Decline onset / collapse onset | 614 / 1310 | 558 / 1309 |
| N @ 1200 / 1400 / 1600 | 1756 / 370 / 1 | 1775 / 305 / 1 |
| births / conceptions | 14 271 / 2 156 | 16 686 / 2 518 |
| wall | 173 s | 324 s |

Twelve seeds (7000–7011), 400 d, mean ± se:

| | 6 tpd | 12 tpd | 24 tpd |
|---|---:|---:|---:|
| N @ 200 | 80 ± 8 | 66 ± 7 | 71 ± 6 |
| N @ 315 | 479 ± 49 | 383 ± 41 | 471 ± 46 |
| N @ 400 | 1316 ± 115 | 1166 ± 126 | 1384 ± 107 |
| births by day 400 | 2525 ± 228 | 2182 ± 220 | 2520 ± 201 |

6 and 24 ticks/day agree within 5 % on every row; 12 ticks/day sits ~10 % lower (0.9 se), with
no ordering in resolution. Against the pre-2f tables (+20–25 % in 2d, +17 / +25 % monotone in
2e) the tick resolution is now a resolution knob within seed noise. The whole-arc single-seed
agreement (peak +3 %, N@736 +2 %, collapse onset −1 d) is the best of any phase.

**Honest misses / open gaps**
- *Last conception 1063 (held-out 1076–1196) vs ≈920*: unchanged in kind from 2e — the competent
  cohort born before ≈300 conceives until it passes `female_fertile_max_age_days` (583);
  Calhoun's males stopped courting ≈200 days earlier. A male-side / oestrus mechanism under the
  breakdown regime is the next modelling candidate.
- *Peak 12–18 % high* (2502; held-out 2457–2602) and *≈60 days early* (502; 429–604): the
  optimiser accepted the overshoot to hold N@736 (2181 vs 2056) and the cessation (533); the
  weaned-density switch (0.58) caps the plateau rather than the peak.
- *N@315 14 % low at the training seed* (531; held-out 286–564) — the 8-founder exponential phase
  is seed-dominated (adults@315 88–217).
- *Late collapse steep*: 1756 at 1200, 370 at 1400, 1 at 1600 vs Calhoun 122 at ≈1444 and 27 at
  1588 — closer than 2e (729 at 1400) but still a cohort dying of `max_age_days` (938) together.
- *Pup survival in the uncrowded phase is low* (≈30–40 % to weaning) because mothers spend ≈50 %
  of their time at the hoppers; the fit compensates with litter 7.2 and conception p 0.79.
- *Early-phase resolution*: 6 vs 24 ticks/day agree within 5 % on N and births through day 400 (12 seeds); 12 tpd sits ~10 % low (0.9 se) with no ordering in resolution — seed noise, not a trend.
- *Warp*: `density_stress_kernel` parity 9e-10 with the exact relaxation and the event buffer;
  mortality kernel mirrors the hazard form, untested at hazard level; the nest kick is host-only.

## Phase 2e — maternal breakdown, relaxation nursing, held decisions, lethal starvation (2026-10-30)

Motivation (from Phase 2d's open gaps): (a) the last *surviving* birth landed at 762 and coincided
with the last conception (755), whereas Calhoun's conceptions ran to ≈920 with no survivors after
600; (b) early growth was still ≈20–25 % faster per day at 24 than at 6 ticks/day. Both turned out
to have causes other than the ones guessed in 2d, so this pass went through several diagnoses.

### Changes (NumPy reference path; Warp kernels mirrored where they touch the same state)

1. **Relaxation-form nursing** (`_feed_by_nest`). While a lactating mother of a pup's own nest
   box is within reach, the pup's hunger/thirst deficit decays as `exp(-nurse_rate_per_day · w · dt)`
   with `w` = Σ (maternal investment × milk share) over the mothers in contact (share = 1 up to
   `nurse_max_pups`, then divided). Relief is proportional to the remaining deficit and composes
   exactly over sub-steps, so what a pup receives per day depends on contact time only. Only
   parous/gestating females (`ROLE_NURSING`) nurse; the "any female with maternal > 0.4" rule of 2d
   is gone.
2. **Decisions are held for the reference interval; events happen on the decision tick.**
   Agents choose an action every `ticks_per_decision = ticks_per_day / ticks_per_day_ref` ticks
   and continue it in between (`_select_actions`). Per-decision events — the meal or drink (eat
   until satiated), the move to the target (`reach` 4 in per unit speed), a fight, drive relief,
   the random-walk step, the object nudge — happen in full on the decision tick, exactly as at
   the reference resolution; the held ticks integrate only continuous physics with dt (drive
   growth, fatigue, nursing contact, stress, mortality). A first version spread each event over
   the held ticks (×k per tick); that interleaves e.g. eating with hunger growth, so the next
   decision saw hunger 0.05 instead of 0.20, the forage/drink cycle and the fatigue-driven REST
   at the hopper shifted, and a lactating mother's nest contact was 20 % instead of 15 % — which
   lethal starvation (5) turned into +60 % early growth at 24 ticks/day. The micro-simulation
   that found it (one mother, one litter, 40 seeds) now gives the same contact (15.1 vs 15.2 %)
   and action mix at 6 and 24. At 6 ticks/day every tick is a decision tick, so the reference
   trajectory is unchanged by construction (hash-verified after every mechanics change).
3. **Post-weaning maternal breakdown** (`maternal_cap`, `_daily_maternal_erosion`). A new SoA
   trait, 1.0 at birth, eroded irreversibly once per day for every weaned female whose stress
   exceeds `maternal_erosion_stress`, by `maternal_erosion_rate × excess`; maternal investment at
   conception/birth and the ACT_NURSE recovery are capped by it, and a mother's investment is
   clipped to it. Below 0.5 she is no longer `ROLE_NURSING` and nurses nothing.
4. **Social-breakdown switch decoupled from the conception ramp** and driven by the social arena.
   `breakdown_density_threshold` (was tied to `menopause_density_threshold`) gates the
   `social_breakdown_stress_boost`; it counts *weaned* animals (`breakdown_density_counts`), because
   pups sit in nest boxes and, more importantly, because weaned numbers only fall through adult
   mortality: a switch on total N behaved as a thermostat (pups die within days of the switch,
   N drops back under the threshold before adult stress has built, nursing resumes — diagnosed on
   seed 7000, where it capped the peak at exactly the threshold and births went on to 833).
5. **Starvation is lethal** (`starvation_hazard_per_day`, 1.0; was a hard-coded 0.1/day). With the
   old hazard about one never-nursed pup in ten reached weaning; those pups — not any nursing — were
   the "surviving" late litters (diagnosed: every surviving litter after day 600 had a mother with
   `maternal_cap` = 0 and maternal = 0). The old leak also propped up early growth under poor
   nursing, so the 2b/2d calibrations partly depended on it.
6. **Exact per-tick death probability** `1 − exp(−h·dt)` from the per-day hazard `h` (NumPy and
   Warp `mortality_kernel`), so daily survival is `exp(−h)` at any resolution.

New tunables in `calib/priors.py`: `nurse_rate_per_day` [2, 12], `maternal_erosion_rate`
[0.002, 1] (log), `maternal_erosion_stress` [0.3, 0.9], `breakdown_density_threshold` [0.35, 0.8].
`last_conception_day` weight raised 0.5 → 1.0 now that the mechanism can separate it from the last
surviving birth.

### Diagnoses along the way (seed 7000, 6 ticks/day, 2d parameters unless stated)

- Relaxation nursing alone made the resolution gap *worse* (N@400 920 vs 1371 at 6 vs 24 tpd,
  6 seeds): with feeding strictly proportional to contact time, the real cause showed — meals,
  drinks and travel were single-tick events, so mothers at 24 tpd spent a quarter of the time away
  from the nest. Holding decisions (effects spread ×k over the held ticks) brought 24 tpd to
  1084 ± 210 (6 tpd 920 ± 223) at the 2d parameters, but at the 2e parameters (lethal
  starvation) the same scheme gave N@400 1065 ± 102 / 1370 ± 87 / 1725 ± 93 at 6 / 12 / 24 tpd
  (12 seeds) — the interleaving bias described under (2).
- Study 1 (168 trials, old switch, adult-only erosion): loss 0.212, but erosion inactive at the
  optimum (stress gain 0.26 / decay 0.53 keeps adult stress below the 0.64 threshold) and "last
  conception" 736 = fertility horizon of the pre-collapse cohort (born ≤ 284 + 452 d). The
  optimiser parked the breakdown boost above the peak because its threshold also set the
  conception ramp.
- Day-by-day diagnostic with the weaned switch (threshold 0.43): switch on at day 500, adult-female
  stress 0.42 → 0.87, 98 % of adult females below cap 0.5 within 50 days, nursing females 0,
  surviving births per 25 d 121 → 103 → 25 → 2; switch off at 575, conceptions resume at 20–40 per
  25 d to day 858 — but 1–5 "survivors" per 25 d persisted to 792: the unfed-pup leak (5).

### Recalibration results (CMA-ES, 14 workers, 1200 d, 6 ticks/day)

Three studies were needed. Study 1 (168 trials, old switch) reached 0.212 with the erosion
inactive; study 2 (decoupled switch, adult-only erosion) was stopped after the diagnoses above;
study 3 (224 trials, `--sigma0 0.1`, start = hand-probed point with nursing rate 12, softer
imprinting) reached **0.159** at trial 160 in 47 min. Two optimiser facts learnt on the way, now
documented in `calib/optimize.py`: Optuna's CMA-ES returns independent random samples until a
trial has completed, so an asked-ahead first generation is random and `x0`/`sigma0` act from the
second generation on (the start point is now enqueued as trial 0); and the default initial step
(min range / 6 ≈ 0.33) is a third of the range for the unit-range parameters, which made the
first generations of study 3 worse than its start point until `--sigma0 0.1`.

Landmarks of the best parameters (`configs/calibrated_calhoun.yaml`, `configs/default.yaml`,
`configs/calibration_study_p2e.json`) at the training seed and three held-out seeds, 1200 d:

| Landmark | Calhoun | **7000** (train) | 8000 | 8001 | 8002 |
|---|---:|---:|---:|---:|---:|
| First litters (day) | 104 | **104** | 104 | 104 | 104 |
| N @ day 315 | 620 | 542 | 567 | 346 | 630 |
| Adults @ day 315 | 150 | 182 | 188 | 143 | 276 |
| Peak N / day (first ≥97 %) | 2200 / 560 | **2320 / 486** | 2231 / 473 | 2344 / 555 | 2312 / 511 |
| Surviving births cease (day) | 600 | **556** | 551 | 656 | 549 |
| strict latest weaned pup (day) | (600) | 564 | 1111 | 1017 | 606 |
| N @ day 736 | 2056 | **2077** | 2049 | 2146 | 2082 |
| Last conception (day) | ≈920 | 1113 | 1194 | 1170 | 1161 |
| N @ 1200 | | 1699 | 1655 | 1737 | 1701 |
| loss | | 0.162 | 0.214 | 0.491 | 0.802 |
| mean rel. error (canonical 5) | | **0.074** | 0.082 | 0.16 | 0.050 |

The held-out losses are carried by the early phase (N@315 346 at 8001, adults@315 276 at 8002:
with 8 founders the exponential phase is seed-sensitive) and by the late last conception; the
five canonical landmarks are met at every seed. Phase 2d for comparison: canonical error 0.117 at
7000, held-out 0.32 / 0.40 / 1.08. The strict latest-weaned-pup day (1111 / 1017 at 8000 / 8001)
is why the rate-based cessation landmark was introduced: two pups out of ~10⁵ births.

1600-day validation, seed 7000, 6 ticks/day (`_output/run1600_p2e_tpd6`, 249 s, 0 NaN; phases
adjustment → growth → stagnation → decline (733) → collapse (<50 % at 1345); Calhoun: 2056 at
736, 122 at ~1444, 27 at 1588):

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 62 | 15 | 0 | 1.00 | 145 |
| 300 | 477 | 137 | 70 | 0.46 | 713 |
| 400 | 1522 | 626 | 383 | 0.30 | 2247 |
| 500 | 2259 | 1710 | 1373 | 0.14 | 3185 |
| 600 | 2178 | 2123 | 1805 | 0.11 | 1428 |
| 700 | 2100 | 2063 | 1753 | 0.11 | 1912 |
| 800 | 2051 | 1982 | 1685 | 0.11 | 2344 |
| 900 | 1967 | 1912 | 1626 | 0.11 | 2159 |
| 1000 | 1856 | 1843 | 1568 | 0.11 | 1081 |
| 1100 | 1788 | 1788 | 1520 | 0.11 | 37 |
| 1200 | 1699 | 1699 | 1466 | 0.09 | 8 |
| 1300 | 1423 | 1423 | 1282 | 0.06 | 0 |
| 1400 | 729 | 729 | 717 | 0.01 | 0 |
| 1500 | 77 | 77 | 75 | 0.02 | 0 |
| 1600 | 2 | 2 | 2 | 0.00 | 0 |

Births continue at ≈2000 per 100 d through day 900 with no survivors (15 259 pups born, 2 111
conceptions, every pup born after ≈560 starved); the plateau is held by adult survival alone,
then the big cohorts born 400–600 die of age (`max_age_days` 983) between 1300 and 1550 —
steeper and ≈100 d later than Calhoun's 122 at 1444.

### Resolution check at the new parameters

1600 d, seed 7000, same parameters (`_output/run1600_p2e_tpd6`, `_output/run1600_p2e_tpd24`):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 104 | 104 |
| N @ 315 | 542 | 346 |
| Peak N / day | 2320 / 486 | 2296 / 536 |
| Surviving births cease (strict latest pup) | 553 (564) | 582 (846) |
| N @ 736 | 2077 | 2128 |
| Last conception | 1113 | 1263 |
| Decline onset / collapse onset | 733 / 1345 | 792 / 1386 |
| N @ 1200 / 1400 / 1600 | 1699 / 729 / 2 | 1752 / 1047 / 20 |
| births / conceptions | 15 259 / 2 111 | 14 668 / 2 016 |
| wall | 249 s | 509 s |

From the peak on the arc agrees within ≈5 % (peak −1 %, N@736 +2 %, cessation +29 d, collapse
onset +41 d); this seed's early phase happened to run *slower* at 24 tpd. Twelve seeds
(7000–7011), 400 d, N and births (mean ± se):

| | 6 tpd | 12 tpd | 24 tpd |
|---|---:|---:|---:|
| N @ 200 | 57 ± 6 | 65 ± 4 | 67 ± 8 |
| N @ 315 | 403 ± 36 | 436 ± 34 | 490 ± 59 |
| N @ 400 | 1065 ± 102 | 1248 ± 100 | 1331 ± 116 |
| births by day 400 | 2160 ± 194 | 2589 ± 184 | 2769 ± 252 |

So a **residual early-growth excess of ≈ +17 % (12 tpd) / +25 % (24 tpd) at day 400 remains**
(1.3–1.7 standard errors each, but monotone in resolution across all four rows). The
per-decision mechanics are now equivalent by construction (verified on the lone-mother
micro-simulation), so what is left are the continuous processes' discretisations: the Euler
stress relaxation (`s += (gain − decay·s)·dt`, a 1 % per-step over-relaxation at dt = 1/6 that
tightens stress around its equilibrium and so changes how often the neglect / erosion /
conception thresholds are crossed), the per-tick Bernoulli nest kick (`0.1·k` per tick: 4 %
fewer kicks per decision at 24 tpd) and the one-tick timing of births. Making the relaxation
exact (`eq + (s − eq)·exp(−decay·dt)`) changes the 6-tpd reference and needs a recalibration,
so it is left for a later pass. Before this pass the same comparison gave +20–25 % (2d) and,
with relaxation nursing but single-tick meals, +49 %.

**Honest misses / open gaps**
- *Last conception 1113 (held-out 1161–1194) vs ≈920.* After the breakdown, conceptions continue
  among the competent cohort born before ≈300 until it passes `female_fertile_max_age_days`
  (604); Calhoun's conceptions stopped ≈200 days earlier. The optimiser prefers the long fertile
  window because `peak_day` and `N@736` reward late growth; shortening it costs those. A male-side
  or oestrus-suppression mechanism under the breakdown regime (Calhoun: males stopped courting)
  would separate the two; not attempted here.
- *Peak ≈70 days early* (486 vs 560; held-out 473–555) and *N@315 ≈13 % low* at the training seed
  (542; held-out 346–630): growth is fast once it starts and the breakdown switch caps it. The
  early exponential phase is strongly seed-dependent with 8 founders (N@315 346–630, adults@315
  143–276 across four seeds), so these are within the seed band rather than a mechanism gap.
- *Late collapse too steep and ≈100 d late*: 1699 at 1200 and 729 at 1400 vs Calhoun's 122 at
  ≈1444; the cohorts born 400–600 die of `max_age_days` (983) almost together. A wider lifespan
  distribution (per-individual max age) would spread it; not in the model.
- *Pup survival in the uncrowded phase is low* (≈30–40 % of pups reach weaning before day 250, a
  lone mother weans <1 of 8 in the micro-simulation) because mothers spend ≈50 % of their time
  foraging/drinking and the nest contact needed under lethal starvation is high. The calibration
  compensates with litter size 7.9 and conception p 0.74. Calhoun's phase-B infant mortality was
  far lower; a more faithful time budget (nest-bound lactating females, hoppers near boxes) is
  a candidate for a later pass.
- *Early-phase resolution*: ≈ +17 % / +25 % faster growth per day at 12 / 24 ticks/day by day 400 (12 seeds); the arc from the peak on agrees within ≈5 %. See the resolution table above.
- *Warp*: `density_stress_kernel` parity holds (4.7e-10); the mortality kernel mirrors the new
  hazard form but is still untested at hazard level; the breakdown switch value is computed on
  the host and passed in.
- *≈75–85 % of adults withdrawn from day 500*: unchanged in kind from 2b/2d.

## Phase 2d — daily-only conception, nest-box nursing, litter abandonment (2026-10-30)

Motivation: (a) the residual resolution dependence of early growth (Phase 2c) came from the
per-tick ACT_MATE conception channel; (b) the last *surviving* birth landed at ~813 vs Calhoun's
600 because communal nursing within 8 in rescued late litters whose own mothers had failed.

Changes (NumPy path; no kernel change — nursing/breeding are host-side):
1. **Conception is purely daily.** `ACT_MATE` is courtship only (`_approach_mate`: move toward
   the nearest eligible partner, no RNG draw). All conceptions happen in `_daily_breeding_pass`,
   so the conception rate cannot depend on how often the per-tick action softmax is sampled.
   `breeding_p_base` is now the only conception rate (prior widened to 0.1–0.9).
2. **Nursing is per nest box.** Passive and active nursing feed only pups whose `nest_id` equals
   the mother's (and are within reach). A litter whose mothers are dead, displaced by a nest kick,
   incompetent (maternal < 0.4) or above the neglect stress threshold is not rescued by other
   boxes — Calhoun: abandoned litters died.
3. **Litter abandonment** (`litter_abandon_p`, daily): a nursing mother above
   `maternal_neglect_stress` abandons her box's litter with this probability; those pups get
   `nest_id = -1`, are never nursed again and starve within ~1–2 weeks. Weaned survivors without
   a box adopt the nearest one. Emergent from stress, no scheduled day (Calhoun phase C:
   "litters abandoned, young expelled pre-weaning"; Gwizdałła & Duś use an abandonment
   probability above a critical density). Logged as `abandoned_cum` / `abandoned_pups`.
Nest occupancy counts ignore box-less pups (NumPy + Warp host counts).

Start point (phase-2b params, `breeding_p_base` 0.35, `litter_abandon_p` 0.2), untuned, seed 7000,
1200 d: loss 0.75 — first litters 110, N@315 700, peak 2024 @ 494, N@736 2000, last surviving
birth 806, N(1200) 1169.

### Recalibration results (CMA-ES 112 trials, 14 workers, 1200 d, 6 ticks/day)
Wall 21.4 min. Best trial 54, loss **0.236**; held-out 8000 / 8001 / 8002: 0.32 / 0.40 / 1.08
(mean 0.60; the 8002 miss is N@315 = 242 and a late peak at 641 — with 8 founders the early
exponential phase is strongly seed-dependent). Artifacts: `configs/calibrated_calhoun.yaml`,
`configs/default.yaml`, `configs/calibration_study_p2d.json`.

| Landmark | Calhoun | Phase 2b | **Phase 2d** seed 7000 | held-out 8000–8002 |
|---|---:|---:|---:|---:|
| First litters (day) | 104 | 111 | **106** | 106–110 |
| N @ day 315 | 620 | 672 | 494 | 242–571 |
| Peak N | 2200 | 2261 | **2023** | 1846–1991 |
| Peak day (first ≥97 %) | 560 | 467 | **553** | 576–641 |
| Last surviving birth (day) | 600 | 813 | **762** | 764–838 |
| N @ day 736 | 2056 | 2106 | **1924** | 1781–1919 |
| Adults @ day 315 | 150 | 217 | **163** | 124–205 |
| Last conception (day) | ≈920 | 793 | 755 | 745–819 |
| N @ 1200 | | 1316 | 853 (42 % of peak) | 727–1035 |
| mean rel. error (canonical 5) | | 0.140 | **0.117** | |

1600-day validation (`_output/run1600_p2d_tpd6`, wall 56 s, 0 NaN; phases: growth → stagnation →
decline (791) → collapse (<50 % peak at 1167)); Calhoun for comparison: 2056 at 736, 122 at
~1444, 27 at 1588:

| day | N | adults | withdrawn | mean adult competence | births in prior 100 d |
|---:|---:|---:|---:|---:|---:|
| 200 | 82 | 26 | 0 | 0.85 | 85 |
| 300 | 421 | 121 | 41 | 0.57 | 476 |
| 400 | 1383 | 591 | 394 | 0.29 | 1485 |
| 500 | 1806 | 1416 | 1242 | 0.11 | 1364 |
| 600 | 1999 | 1737 | 1604 | 0.08 | 809 |
| 700 | 1982 | 1800 | 1680 | 0.07 | 479 |
| 800 | 1799 | 1768 | 1659 | 0.06 | 167 |
| 900 | 1619 | 1619 | 1517 | 0.06 | 0 |
| 1200 | 853 | 853 | 853 | 0.00 | 0 |
| 1400 | 215 | 215 | 215 | 0.00 | 0 |
| 1600 | 8 | 8 | 8 | 0.00 | 0 |

Resolution check (same params, seed 7000, 1600 d, `_output/run1600_p2d_tpd24`, 285 s):

| | 6 tpd | 24 tpd |
|---|---:|---:|
| First litters | 106 | 110 |
| N @ 315 | 494 | 285 |
| Peak N / day | 2023 / 553 | 2095 / 608 |
| Last surviving birth | 762 | 805 |
| N @ 736 | 1924 | 2052 |
| Last conception | 755 | 786 |
| Decline onset / collapse onset | 791 / 1167 | 854 / 1210 |
| N @ 1200 / 1600 | 853 / 8 | 1086 / 29 |
| births total | 4865 | 4495 |

The arc agrees (peak +4 %, N@736 +7 %, collapse onset +4 %). The early phase differs at this
single seed (N@315 285 vs 494), but a single seed is not informative here. Six seeds
(7000–7005), 400 d, same params:

| | 6 tpd mean ± sd | 24 tpd mean ± sd |
|---|---:|---:|
| N @ 200 | 69 ± 13 | 91 ± 25 |
| N @ 315 | 416 ± 109 | 510 ± 183 |
| N @ 400 | 1124 ± 269 | 1435 ± 304 |
| births by day 400 | 1655 ± 456 | 2010 ± 437 |

So a **residual early-growth excess of ≈ +20–25 % at finer ticks remains** (≈1–2 standard
errors with 6 seeds), same sign as in 2c but smaller; seed 7000 alone happened to go the other
way. Conception is daily now, so the remaining channel is infant survival: per-contact nursing
amounts are clipped (hunger floor 0, energy cap 1), and four quarter-size contacts waste less
than one full-size contact, so pups are fed slightly better at finer ticks and more daughters
reach breeding age. Fix for a later pass: relaxation-form feeding (relief proportional to the
remaining deficit, composed over sub-steps) — changes the 6-tpd reference, so it needs another
recalibration. Everything from the peak onward agrees within ~7 % across resolutions.

**Honest misses / open gaps**
- *Last surviving birth 762 vs 600* (held-out 764–838; across trials min 675 at a 1180 peak,
  median 818). Still a mechanism limit, but of a different kind than in 2b: now the last
  conception (755) and the last surviving birth (762) nearly coincide, i.e. the late litters of
  the remaining competent, fertile females *survive*, whereas Calhoun's conceptions continued to
  ≈920 with no survivors after 600. What is missing is the breakdown of maternal behaviour in
  *already-adult* females under prolonged crowding (Calhoun: nursing females turned aggressive,
  wounded and expelled their own young). Candidate for a phase 2e: an adult-stage erosion of
  `maternal` under sustained stress (irreversible, like competence), which would keep
  conceptions going while infant survival goes to zero.
- *Early phase slightly small* (N@315 494, peak 2023): the optimiser traded it for peak timing
  (553) and the cessation landmark; both within the seed-to-seed band.
- *≈85–90 % of adults withdrawn from day 500*: unchanged from 2b; Calhoun does not quantify it.

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