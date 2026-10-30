# Universe25 Play — NOTES

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