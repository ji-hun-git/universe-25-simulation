# Universe25 Play — NOTES

## 2026-11-11 — Replica v2 M6: out of sample the replica misses the record; the sibling universes contradict the hopper sink

**Design** (`docs/REPLICA_V2.md` M6; `scripts/replica_validate.py`). The seed bands were
registered in `docs/SEEDS.md` before use. The M5 fallback ensemble (12 members, flagged) ran on
fresh seeds:
- Calhoun's pen: 48 runs, member i mod 12 on seed 9200 + i.
- The sibling universes of Calhoun 1971 Fig 3: 1, 2, 4 and 8 open cells, 12 seeds each
  (9248–9295), 900 days, no removal. Time is aligned to the first surviving litter, as in the
  record.
- The Marsden transfer with the best member (9296–9307).

**Calhoun's pen** (48 fresh seeds; the record against the replica's 5–95 % range; * = outside):

| target | record | replica median [5–95 %] |
|---|---|---|
| first litters | 50–104 | 50 [37, 56] |
| N@315 | 620 | 858 [475, 1198] |
| adults @315 | 150 | 402 [220, 827] * |
| peak N | 2200 | 1333 [1109, 1826] * |
| plateau onset | 560 | 516 [340, 1413] |
| N@736 / 811 / 960 | 2056 / 1871 / 1650 | 1090 / 1082 / 988 * (all three) |
| last surviving birth | 600 | 1578 [580, 1578] |
| last conception | 920 | 1599 [552, 1599] |
| N@1444 | 122 | 993 [29, 1592] |
| N@1588 | 27 | 946 [4, 1562] |
| phase-B doubling | 55 | 47 [41, 56] |
| phase-C doubling | 105–145 | 361 [131, 2000] |
| male share @315 | 0.40 | 0.47 [0.39, 0.53] |
| male share @1444 | 0.18 | 0.32 [0.20, 0.41] * |
| empty boxes @560 | 0.25 | 0.42 [0.29, 0.69] * |
| withdrawn @560 | 0.32 | 0.07 [0.00, 0.85] |
| never fought or mated @800 | 0.53 | 0.00 [0.00, 0.36] * |
| brood groups by 315 | 14 | 24.5 [17, 31] * |

The record is inside 11 of 20 ranges. Several of those are inside only because the ensemble is
bistable: the 5–95 % ranges of N@1,444, N@1,588, last conception and withdrawn share span both
the collapsing and the plateauing regime. The median run does not collapse.

**Sibling universes** (N at T days after the first surviving litter; record vs replica median
[5–95 %]):

| cells | end of phase B | end of phase C | later | per cell, later (record) |
|---|---|---|---|---|
| 1 | T142: 60 vs 116 [48, 180] | T293: 181 vs 176 [96, 221] | T498: 185 vs 171 [63, 190] | 171 (180) |
| 2 | T150: 113 vs 223 [106, 292] | T298: 340 vs 219 * | T602: 330 vs 195 * | 98 (175) |
| 4 | T230: 143 vs 407 * | T453: 507 vs 376 * | T573: 490 vs 350 * | 87 (130) |
| 8 | T190: 240 vs 396 * | T378: 1120 vs 573 * | T513: 1100 vs 605 * | 76 (142) |
| 16 (the pen) | T251: 640 vs 780 | T493: 2200 vs 1168 * | T692: 2250 vs 1102 * | 69 (138) |

- The 1-cell universe matches at all three times.
- The replica's plateau per cell falls with pen size (171 → 69); the record's stays at 130–180.
- **Diagnostic, post hoc** (best member, 8 cells, training seeds 7000–7003). The pen holds 81 mice
  per cell with hopper facilitation and 185 without (record 138).
  - So M3's cross-cell hopper aggregation, through pup loss in the aggregated cells, makes the
    plateau depend on pen size.
  - The sibling universes say it should not. The aggregation mechanism as implemented is
    contradicted by data it was never fitted to.

**Marsden transfer, best member** (fresh seeds 9296–9307):

| | conceptions | females conceived | littered | pups to 14 d |
|---|---|---|---|---|
| colony males | 0 [0, 12] | 0 | 0 | 0 |
| fresh stock males | 27 [20, 39] | 10 of 16 | 10 | 32 |
| record | 0; with stock males 6 of 16 conceived | | 3 | 5 |

- Unlike M4, the pattern matches the record. The colony's males are the bottleneck: their
  courtship capacity is eroded to 0.00, while female competence is 0.90.
- Stock males rescue the females, but the rescue is too strong, so the model's females are
  healthier than Calhoun's.

**Reading.**
- **The replica does not meet the validation standard.** Its peak is too low. It plateaus or
  collapses by chance, and its structural numbers miss.
- **The out-of-sample test was informative.** The sibling universes point at a specific
  mechanism: hopper facilitation, coupled to local nursing disturbance. That mechanism also
  capped the colony at about 1,200 in M3 and M4.
- Because M6 found this, removing or revising the mechanism now would use the sibling data in
  fitting. The siblings would then no longer be out of sample.

## Replica v2 — state at the end of M1–M6 (2026-11-11)

**Built.** Every mechanism sits behind a config field whose default reproduces the frozen 2m
colony, which is still the reference and still bit-identical.
- **The pen:** 16 triangular cells, 4 × 4 boxes per cell, hoppers, water, ring stands, box
  feeding until day 160.
- **Life history:** 48-day founders and no calendar gate.
- **Territories:** owners, contests and sires.
- **Owner behaviour:** fidelity and defence, with the centre as no-man's land.
- **Boxes and feeding:** box choice with natal dispersal, and hopper facilitation.
- **Individual breakdown:** care-driven development, exclusion stress, aggression by sex, wound
  mortality.
- **Pens of fewer cells,** with bookkeeping of fought / mated / littered.
- **Tools:** the Marsden transfer, history matching with GP emulators, and fresh-seed validation
  with the sibling universes.
- **Process:** each milestone was preregistered, tested (golden hashes unchanged for every
  frozen arm) and reported, including its misses.

**What the replica reproduces:**
- first litters with no gate;
- territories in all 16 cells;
- hopper aggregation;
- a female-biased late sex ratio;
- the Marsden transfer pattern (best member);
- the 1-cell sibling universe's plateau.

**What it does not:**
- the 2,200 peak followed by the end of reproduction. M5 found no parameter set doing both
  among 488 runs;
- brood groups (about 24 against 14), withdrawn mice at the centre, the share that never fought
  or mated, and box vacancy;
- the sibling universes larger than one cell.

**Open questions, Jason's call:**
1. Hopper facilitation as implemented is contradicted by the siblings. Dropping or revising it
   would need a fresh out-of-sample check, as there is no other unfitted record left.
2. Is the record's collapse a delayed multi-generational mechanism (care across generations),
   or one draw from a bistable system? The record has n = 1, and the model's best region is
   bistable.
3. Whether any replica configuration becomes the reference for new work. I recommend not
   replacing the frozen 2m colony.

## 2026-11-11 — Replica v2 M5: history matching finds no parameter set that grows to 2,200 and then collapses

**Design.** As preregistered in `docs/REPLICA_V2.md` (spec b468f4c, code 11ab904):
- the replica is M4 amended, plus the removal event (150 on day 1,014) and both methods fixes
  from the review;
- 20 parameters on boxes, 20 record targets with observation and discrepancy sds;
- a GP emulator per target, with NROY defined by second-largest implausibility ≤ 3;
- waves of 200 (Latin hypercube), 120 and 120 points, then 24 NROY points × 2 seeds;
- training seeds 7000–7011 throughout.

The run took 488 runs and 10.3 CPU-hours (`_output/hm/`).

**Emulators.** Leave-one-out errors beyond 3 sd were at most 3 % for every target in every wave.
The ones driving most outputs are `imprint_rate`, `maternal_erosion_stress` and
`stress_density_gain`.

**The NROY space shrank wave by wave:**

| fitted on | NROY fraction of the box (2nd-max ≤ 3) | max ≤ 3 |
|---|---|---|
| wave 1 (200 runs) | 0.51 % | 0.006 % |
| waves 1–2 (320) | 0.032 % | 0 |
| waves 1–3 (440) | 0.008 % | — |
| all 488 | 0.003 % | 0 |

**No simulated parameter set passes.**
- The best simulated run has I₂ 3.19 and I_max 4.40. Its N@315 is 742, its peak 1,413 at day
  764, and N@1,444 571.
- None of the 24 ensemble members passes on its two-seed mean. The best scores I₂ 3.95. Its
  worst targets are never fought or mated (4.5), N@736 (3.9) and N@811 (3.3).
- `configs/replica_v2_ensemble.json` holds the 12 best members, marked `fallback: true` because
  none passes.

**The conflict is growth versus collapse.**
- Of 488 runs, 97 peak above 1,800 and 76 end below 300 at day 1,588. **None does both.**
  - The largest peak among collapsing runs is 1,749.
  - Every run that peaks above 1,800 still holds at least 1,265 at day 1,588, and keeps
    conceiving to the end.
- Parameter sets that let the colony grow to the record's size leave reproduction intact at
  that size. Sets whose development and stress end reproduction also cap growth at about
  1,200–1,750.
- "Never fought or mated" at day 800 (record 0.53) is the hardest single target. It can reach
  0.54 on its own (its median over all runs is 0.01). Where the other targets come closest, it
  reaches only about 0.0–0.2.

**The best region is bistable.**
- The best ensemble member's two seeds fall into different regimes. Seed 7001 ends conceptions
  at day 569 and dies out (8 at day 1,588). Seed 7000 conceives to day 1,562 and holds 1,291.
- In the ensemble, 8 of 48 runs end reproduction.
- Near the boundary, the seed decides whether the colony collapses or plateaus.

**Reading.**
- With breakdown driven only by each animal's own experience, the model cannot produce
  Calhoun's arc: growth to 2,200 and then the end of reproduction.
  - The frozen 2m calibration produced it with a colony-wide density switch. M3 showed that
    switch is a fixed density threshold, not a mechanism.
  - The individual mechanisms (local density stress, box overcrowding, care deficits, erosion
    thresholds) act during growth as much as after the peak. So they trade growth against
    collapse.
- Two readings stay open, and this replica cannot separate them:
  - **A missing delayed or cumulative mechanism.** For example, competence lost across
    generations through the care each generation received. This would be Calhoun's "second
    death", which the model has only in one generation.
  - **The record's collapse is one draw from a bistable system** (n = 1). The four sibling
    universes plateaued and were terminated (Calhoun 1971), and the model's best region is
    bistable.
- **This is a negative calibration result, reported as such.** The fallback ensemble does not
  meet the validation standard. Whether any of it becomes the reference for new work is
  Jason's call; I recommend against replacing 2m with it.

## 2026-11-11 — Replica v2 M4: without colony-wide terms the colony collapses only with lifelong natal boxes

**Design.** Jason: "start m4, try to finish the project". The specification was committed before
code (30e5d8d), with a priori values:
- no colony-wide term (`breakdown_scope: individual`);
- pups lose competence with their own care deficit (gain 1.0);
- 0.05 stress per displacement by an owner;
- aggression by sex: males fight males, and females fight only while nursing;
- wound mortality as a field;
- pens of fewer open cells;
- fought / mated / littered bookkeeping;
- the Marsden transfer (`scripts/replica_transfer.py`).

**Amendment, before any multi-seed run** (cc3348c). A one-seed diagnostic found that overfull
boxes gave 92 % of the young's developmental exposure, with up to 160 mice in a box of 15.
Animals kept their natal box for life. Natal dispersal at maturity
(`geometry.disperse_at_maturity`) was added a priori and reported as its own arm.

**Checks.**
- All eight golden arms are unchanged with the flags off. `replica_v2` was refreshed, and the
  report's M3 arm reproduces the M3 hash exactly.
- `test_m4_mechanisms` covers:
  - the guards;
  - the conception term in individual scope;
  - care-driven competence loss (exact);
  - aggression by sex and the fought marks;
  - exclusion stress;
  - open cells;
  - dispersal.
- The fast tier passes, H2 audit included.

**M4 report** (training seeds 7000–7011, 1,600 d; `_output/replica_report_m4.json`). Arms are
cumulative: M3, + individual breakdown and care, + exclusion stress, + aggression by sex (= M4
as specified), + natal dispersal (= M4 amended). Medians, with [5–95 %] where it matters.

| | Calhoun | M3 | + individual | + exclusion | M4 as specified | M4 amended |
|---|---:|---|---|---|---|---|
| N@315 | 620 | 1089 | 1119 | 1100 | 1014 | 1073 |
| peak N | 2200 | 1377 | 1395 | 1373 | 1126 | 1271 |
| N@736 | 2056 | 1214 | 1231 | 1215 | 986 | 1092 |
| last conception | 920 | 1599 | 1599 | 1599 | **814** [735, 1060] | 1599 |
| N@1444 | 122 | 1259 | 1297 | 1252 | **140** [67, 372] | 1080 |
| N@1588 | 27 | 1220 | 1236 | 1226 | **56** [17, 225] | 1066 |
| male share, day 315 | 0.40 | 0.50 | 0.50 | 0.50 | 0.45 | 0.46 |
| male share, day 1444 | 0.18 | 0.53 | 0.53 | 0.52 | 0.03 | 0.23 |
| withdrawn share, day 560 | 0.32 | 0.69 | 0.69 | 0.70 | 0.86 | 0.81 |
| withdrawn within 12 in of the centre | > 0.09 | 0 | 0 | 0 | 0 | 0 |
| never fought or mated, 131–320 d, day 800 | 0.53 | 0 | 0 | 0 | 0.34 | 0.16 |
| empty boxes, day 560 | 0.20–0.30 | 0.60 | 0.60 | 0.60 | 0.81 | 0.64 |
| brood groups by day 315 | 14 | 24 | 25 | 24.5 | 18.5 | 23.5 |

With aggression "any", everyone fights sooner or later, so nobody counts as never having fought
in the first three arms.

**Marsden transfer** (M4 amended, day 870, 12 seeds; `_output/replica_transfer_m4.json`):

| | conceptions | females conceived | littered | pups to 14 d |
|---|---|---|---|---|
| colony males | 0 [0, 3] | 0 | 0 | 0 |
| fresh stock males | 0 [0, 3] | 0 | 0 | 0 [0, 6] |
| record | 0 with colony males; 6 of 16 conceived with stock males | | 3 | 5 |

The transferred females' competence is 0.06, and conception scales with female competence. So
in the model the females are as broken as the males. In the record, the stock males showed the
females were partly intact.

**Against the M4 targets** (reported, not fitted):
- **Reproduction ends without a colony-wide term** only in M4 as specified (last conception 814;
  N@1,444 and N@1,588 inside the record's range). With dispersal it does not end.
- **Missed:**
  - never fought or mated: 0.16, against 0.53 ± 0.15;
  - withdrawn share: 0.81, against 0.32 ± 0.10;
  - withdrawn at the centre: 0;
  - male share at day 315: 0.46, against 0.40 ± 0.05;
  - transfer with stock males: the females are not partly intact.
- **Met:**
  - female bias late: male share 0.23 at day 1,444, record 0.18;
  - no conceptions after transfer with the colony males.

**Reading.**
- **Removing the colony-wide terms removes the collapse,** as M3 predicted. Individual
  breakdown and exclusion stress leave the plateau of about 1,250 unchanged.
- **Aggression by sex depletes males.** Male–male fights put the wound mortality on males: male
  share 0.25 by day 560, against the record's 0.40 in phase B and 0.18 only at day 1,444.
  - Fewer males means fewer owners: 11 owned cells by day 800, none by day 1,444.
  - With lifelong natal boxes, the overcrowded boxes erode the young's competence. Together with
    male depletion, this ends reproduction near the record's date, and the counts at days
    1,444–1,588 match.
  - **But the collapse rests on an artefact.** With natal dispersal the young keep enough
    competence, and the colony holds at about 1,100 to the end. So the near-match of the late
    landmarks in M4 as specified is not evidence for the mechanism.
- **The colony is regulated at about 1,100–1,400 in every arm.** That is about half the
  record's peak. M3 found the cause: pup loss in the aggregated cells.
- **What this leaves for M5:** whether any parameter set, with all the mechanisms and the
  artefact removed, reproduces the record. Specifically: growth to 2,200, a plateau, the end of
  reproduction near day 920, and the decline. History matching answers that, including "no".

## 2026-11-11 — Replica v2 M3: territories settle and hoppers aggregate; the aggregated colony never collapses

**Design.** Jason: "Start M3". The specification was committed before code (aec8958,
`docs/REPLICA_V2.md`), with no fitted parameter. Four mechanisms, each behind its own field:
- **Fidelity:** owners and claimants keep to their cell. An owner takes his cell's emptiest box,
  and the territorial role means an owner.
- **Defence:** an owner tolerates the 3 lowest-ranked adult males (Calhoun's basic group) and
  displaces the rest to 10 in from the centre. Territories exclude the 12-in centre disc.
- **Box choice:** an animal needing a box takes the fullest box below capacity in its cell
  (lower level on ties), else the emptiest.
- **Hopper facilitation:** after day 160 a forager goes to the busiest of its own and its two
  neighbours' hoppers, counted at the previous decision.

**Checks.**
- With every M3 flag off, all eight golden arms are unchanged, M2's replica arm included. Only
  `replica_v2` was refreshed (now M3), and the report's M2 arm reproduces the M2 hash exactly.
- `test_m3_mechanisms` covers the guards and each mechanism. The fast tier passes, H2 audit
  included.
- After the code was written, a one-seed sanity run and a one-seed turnover count were made.
  No rule or parameter was changed after them.

**M3 report** (training seeds 7000–7011, 1,600 d; `_output/replica_report_m3.json`). The arms
are cumulative: M2, + fidelity, + defence, + box choice, + facilitation (= M3). Medians
[5–95 %]; * = the record lies outside the range.

| landmark | Calhoun | M2 | + fidelity | + defence | + box choice | M3 |
|---|---:|---|---|---|---|---|
| N@315 | 620 | 1559 * | 2348 * | 2355 * | 1826 * | 1089 [1042, 1164] * |
| peak N | 2200 | 2394 * | 2563 * | 2560 * | 2450 * | 1377 [1352, 1433] * |
| peak day | 560 | 393 * | 338 * | 339 * | 372 * | 1129 [514, 1284] |
| N@736 | 2056 | 2050 | 2044 | 2043 | 2037 | 1214 * |
| last conception | 920 | 863 * | 825 * | 831 * | 852 * | 1599 (end of run) * |
| N@1444 | 122 | 30 * | 17 * | 12 * | 24 * | 1259 [1222, 1289] * |
| N@1588 | 27 | 4 * | 1 * | 1 * | 2 * | 1220 * |
| phase-B doubling | 55 d | 39 * | 38 * | 38 * | 40 * | 45 [41, 48] * |

Structure and territories (medians; day 560 unless stated):

| | M2 | + fidelity | + defence | + box choice | M3 | Calhoun / target |
|---|---|---|---|---|---|---|
| owned cells (day 315) | 7.5 | 16 | 16 | 16 | 16 | ≥ 10 |
| brood groups by day 315 | 22 | 35 | 30.5 | 28 | 24 [22, 32] | 10–16 (14) |
| largest group by day 338 | 377 | 368 | 414 | 544 | 673 | 111 |
| takeovers by day 315 | 26 | 40 | 27 | 24 | 26 | — |
| subordinate males per owner | 35 | 13.5 | 14 | 12.8 | 5.4 | 3 |
| empty boxes | 0.00 | 0.00 | 0.00 | 0.36 | 0.60 | 0.20–0.30 |
| withdrawn within 12 in of the centre | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | > 0.09 |
| excluded males within 12 in of the centre | 0.00 | 0.00 | 0.78 | 0.76 | 0.59 | pooled there |
| busiest cell's share of foragers | 0.09 | 0.09 | 0.08 | 0.09 | 0.25 | > 0.125 |
| owners' distance from ring stand (in), day 315 → 560 | 18.4 → 17.9 | 18.8 → 19.0 | 18.9 → 19.0 | 18.9 → 18.7 | 18.4 → 18.9 | < 12 in phase C |
| founding males dead by day 60 | 0 | 0 | 0 | 0 | 0 | 2 of 4 |

**Against the M3 targets** (reported, not fitted):
- **Met:**
  - owned cells (16 from day ~250 on);
  - hopper aggregation (busiest cell 0.25 of the foragers, four times uniform).
- **Missed:**
  - brood groups (24 against 10–16). Owners are defeated after a median 19 days in one seed
    (51 takeovers by day 315). Males are born at rank 0.4–0.8, so many maturing males sit within
    0.15 of the owner, even among the three he tolerates.
  - empty boxes at the peak (0.60 in M3, 0.36 with box choice alone, against 0.20–0.30).
    Aggregating into the fullest box overshoots.
  - the withdrawn at the centre (0.00 everywhere). The excluded, non-withdrawn males pool there
    instead. Withdrawn animals reach the centre only while choosing WITHDRAW; feeding and their
    boxes pull them back to the walls.
- **No shrinkage towards the ring stands.** None was designed in. Owners average about 19 in
  from it in every phase.

**The main finding: the aggregated colony never collapses.** With hopper facilitation, the colony
peaks at about 1,380, sits at about 1,200–1,260 from day 500 to 1,600, and conceives until the
end of the run. The record collapsed to 27.
- **What it is not:** hopper capacity. No meal was refused in three seeds, with or without
  facilitation, and no weaned animal starved (hunger > 1.2, days 300–500).
- **What it is:** pup survival. Between days 300 and 400, conceptions change little (520–561 vs
  590–665). Pups weaned fall by half (453–586 vs 943–1,238).
  - Aggregation puts about 20 % of the weaned in one cell, so mothers feel a higher local
    density (0.70 vs 0.60 of a cell's design capacity).
  - The frozen biology's nursing disturbance is driven by local density.
- **Why that stops the collapse:** the frozen biology's breakdown is switched by colony-wide
  weaned density, at about 2,200 weaned. A colony held near 1,200 by pup loss in the sink never
  reaches it. So it neither breaks down nor dies out; stress is lower, too (0.36 vs 0.47).
- **What it shows about the frozen biology:** its collapse depends on reaching a fixed
  colony-wide density. Calhoun's colony showed the sink and pup loss and still reached 2,200
  and collapsed. M4 (breakdown driven by each animal's own care and experience, not a
  colony-wide count) is where this has to change.
- **Not changed:** M3 changed no biology parameter. Without facilitation (+ box choice) the old
  arc returns, with peak day 372 and N@1444 24.

## 2026-11-11 — Replica v2 M2: no calendar gate, first litters at day 49; territories slow phase B but too few cells settle

**Design.** Jason: "Start M2". The specification and targets were committed before code
(5d25410, `docs/REPLICA_V2.md`), with a priori parameters:
- 48-day founders (`biology.founder_age_days`);
- no calendar gate (`first_conception_min_day` 0);
- litter 5.5;
- territories (`biology.territories`):
  - one owner per cell;
  - a claim settles after 14 daily passes as the cell's top male;
  - daily contests against a present male ranked at least owner − 0.15;
  - ownership lapses only by death, withdrawal or defeat;
  - conception needs an owner in the female's cell, and he sires.

The rule details the spec left open were decided in code before any multi-seed run, and are
recorded in the spec. No rule or parameter changed after the one-seed sanity run.

**Checks.**
- Every frozen golden hash is unchanged on both tiers. Only `replica_v2` was refreshed, because
  its config is now M2.
- The M1 comparison arm (`replica_v2.yaml` with the four M2 fields reset) reproduces the old M1
  hash exactly.
- `test_m2_territories` covers settling, restart, the absent owner, the contest and takeover,
  dropped claims, lapse by death or withdrawal, and conception by the owner. A one-seed sanity
  run printed the pass's state. The fast tier passes, including the H2 audit and a 150-day M2
  colony with invariants on.

**M2 report** (training seeds 7000–7011, 1,600 d; `_output/replica_report_m2.json`). Arms:
- M1;
- M2 without territories (founders, no gate, litter 5.5);
- M2.

Medians [5–95 %]; * = the record lies outside the range.

| landmark | Calhoun | M1 | M2, no territories | M2 |
|---|---:|---|---|---|
| first litters | 50–104 | 102 [102, 102] | 36 [36, 36] * | 49 [49, 52] |
| N@315 | 620 | 1821 [1501, 2042] * | 2459 [2305, 2528] * | 1559 [1109, 1872] * |
| adults @315 | 150 | 654 [599, 742] * | 1314 [1047, 1570] * | 703 [514, 838] * |
| phase-B doubling | 55 d | 35 [32, 36] * | 42 [37, 44] * | 39 [36, 43] * |
| phase-C doubling | 145 d | 124 [91, 196] | 359 [260, 783] * | 156 [109, 190] |
| peak N | 2200 | 2524 [2472, 2583] * | 2535 [2471, 2592] * | 2394 [2321, 2460] * |
| peak day | 560 | 372 [356, 395] * | 323 [305, 347] * | 393 [368, 472] * |
| last young day | 600 | 409 [393, 439] * | 352 [329, 383] * | 439 [407, 503] * |
| N@736 | 2056 | 2060 [2033, 2101] | 2018 [1967, 2048] * | 2050 [2015, 2100] |
| last conception | 920 | 861 [850, 880] * | 809 [793, 827] * | 863 [836, 899] * |
| N@1444 | 122 | 20 [16, 36] * | 11 [8, 21] * | 30 [17, 61] * |

Territories (M2):

| | M2 | Calhoun |
|---|---|---|
| owned cells at day 315 / 560 / 736 | 7.5 / 7.5 / 7 of 16 | 16 territories |
| brood groups by day 315 | 22 [14, 33]; 10–16 in 2 of 12 seeds | ~14 |
| brood groups by day 338 | 25 [17, 34] | 14 |
| young born by day 338 | 2576 [1786, 3120] | 842 |
| largest group by day 338 | 377 [282, 564]; the top 14 hold 90 % | 111 |
| founding males dead by day 60 | 0 of 4 in every seed | 2 of 4 |
| contests / takeovers by day 315 | 79 / 26 | — |

The structural numbers are unchanged from M1:
- nobody within 12 in of the centre;
- no empty boxes at the peak;
- male share 0.50;
- withdrawn share 0.75 at day 560.

**Against the M2 targets** (reported, not fitted):
- **Met:** first litters fall in 40–80 d with no gate (49 d).
- **Missed:** 10–16 brood groups by day 315 (22). The distribution is skewed, as the target
  asked.
- **Missed:** N@315 is 1,559 against 620.
- **Missed:** phase-B doubling is 39 d against 55.
- **Inside the range:** phase-C doubling (156 d against 145).

This is a development report on 12 training seeds. The 48-seed validation standard applies to
the calibrated replica (M5), not to an a priori milestone.

**Reading.**
- **Phase A is now timing, not a social process.** First litters fall at about day 49 in nearly
  every seed. That is the sum of the founders reaching `maturity_days` (age 63.9, so day 16),
  14 days of settling, and gestation (19.5). The founders start in separate cells (an
  assumption), so they never fight: no contests and no founder deaths before other males mature.
  Calhoun's phase A came from founder fighting, which killed 2 of 4 males. Without territories,
  litters come at day 36 and phase B grows faster still.
- **Territories slow phase B but do not hold it.** N@315 falls from 2,459 (no territories) to
  1,559, which is still 2.5 times the record.
  - Only about half the cells ever get an owner. A probable cause, not tested: males have no
    site fidelity yet. A cell's top male changes from day to day as the colony grows, so a
    14-pass claim rarely completes.
  - The owners that exist turn over (26 takeovers by day 315). Each new owner starts a new brood
    group, so there are too many groups (22 against 14). Each holds far too many young, because
    an owner's females conceive at the frozen rate.
- **What follows.**
  - The missing structure (site-faithful owners, centre pooling, box vacancy, the sex ratio,
    founder deaths) is M3–M4 behaviour.
  - The growth rate (N@315, phase-B doubling, the peak about 170 days early) is calibration,
    which is M5.
  - M2 changed nothing else.

## 2026-11-11 — Replica v2 M1: Calhoun's pen built; the frozen biology runs the arc ~190 days early in it

**Decision and design.** Jason chose replica v2 before any further play work. Design:
`docs/REPLICA_V2.md` (9d515bd). The frozen 2m colony stays bit-identical; replica v2 is
`configs/replica_v2.yaml`.

**The pen** (24afb76). Apparatus detail is from the fidelity reviewer's page-by-page reading of
Calhoun 1973, Calhoun 1971 and Marsden 1972.
- *Cells:* 16 triangular cells tiling the floor. Each has a 25¼-in base on the wall and its apex
  at the centre: 638 sq in, the record's 640.
- *Boxes:* four tunnels per cell with four box levels.
- *Food and water:* a wall hopper (food for 9,500) and a water platform (water for 6,144) per
  cell, served highest rank first.
- *Reconfiguration:* box feeding until day 160 (December 1968).
- *Ring stands:* one per cell.
- *Withdrawal:* withdrawn animals drift to the centre.
- *Founders:* one pair per wall; the record does not say where they were placed.
- *Checks:*
  - Every existing golden hash is unchanged, and `World.cells_of` keeps the grid arithmetic
    exactly.
  - The 16 cells have equal area within Monte Carlo noise.
  - The tests pass, including a 150-day replica colony with the invariants on.

**M1 report** (training seeds 7000–7011, 1,600 d; `scripts/replica_report.py`,
`_output/replica_report_m1.json`). Three arms: the frozen grid colony, the grid with the
playground off, and the replica pen. Medians [5–95 %]; * = the record lies outside the range.

| landmark | Calhoun | frozen grid | grid, playground off | replica M1 |
|---|---:|---|---|---|
| N@315 | 620 | 457 [171, 580] * | 889 [723, 1031] * | 1821 [1501, 2042] * |
| peak N | 2200 | 2263 [2185, 2350] | 2378 [2325, 2460] * | 2524 [2472, 2583] * |
| peak day | 560 | 538 [503, 654] | 482 [445, 509] * | 372 [356, 395] * |
| last young day | 600 | 599 [540, 732] | 561 [511, 639] | 409 [393, 439] * |
| N@736 | 2056 | 1951 [1920, 2093] | 2124 [2073, 2143] * | 2060 [2033, 2101] |
| last conception | 920 | 922 [865, 1079] | 924 [908, 954] | 861 [850, 880] * |
| N@1444 | 122 | 119 [83, 351] | 80 [58, 124] | 20 [16, 36] * |
| phase-B doubling | 55 d | 47 [40, 73] | 36 [34, 40] * | 35 [32, 36] * |
| phase-C doubling | 145 d | 95 [71, 111] * | 115 [92, 146] | 124 [91, 196] |

Structural numbers (medians):

| | day 315: replica | day 315: frozen grid | day 560: replica | day 560: frozen grid | Calhoun |
|---|---:|---:|---:|---:|---|
| empty boxes | 0.14 | 0.62 | 0.00 | 0.00 | ~0.20 at the peak |
| weaned within 12 in of the centre | 0.000 | 0.028 | 0.000 | 0.032 | withdrawn mice pooled there |
| withdrawn share | 0.25 | 0.23 | 0.80 | 0.71 | 32 % of a cell at the end of phase C |
| male share | 0.49 | 0.52 | 0.50 | 0.50 | 0.40 in phase B |

**Reading.**
- **The calibrated curve depends on the playground and the layout,** as the review found. With
  the playground off, the frozen biology doubles its early growth. In Calhoun's pen, with food
  at the box until day 160, it grows faster still. Its doubling time is 35 d against the
  record's 55, and it runs the whole arc about 190 days early, then collapses deeper (N@1444 20
  vs 122).
- **The pen alone does not produce Calhoun's structure:**
  - nobody reaches the centre (the withdrawal drift is weaker than the trips to the wall
    hoppers and boxes);
  - every box is occupied at the peak (random box kicks spread the animals);
  - the sex ratio stays 50 : 50;
  - withdrawal is far too common.
- These are the M2–M4 targets (life history and phase A; territories and box choice; breakdown
  and categories). M1 was meant to change only the geometry, so no parameter was touched.

## 2026-11-11 — P4-15: a learner with a stronger free-time signal still ignores object consequences; the stop rule applies

**What was tested** (`docs/PHASE4_DESIGN.md` §4.2, preregistered 507acb4 before any code or
run). Does a PPO learner's free time depend on object consequences once the training signal is
changed?
- *Learner options* (805a6ae; defaults train to the same actor as before):
  - entropy annealed linearly 0.05 → 0.005 over transitions 5e7–1e8;
  - advantages normalised per transition type (decision vs sub-step);
  - GAE λ per unit of time.
- *Substrate:* P4-13 (action space v2, ball physics, novelty off), observation v5.
- *Arms:*
  - **A0**: the `pretrain_v4` recipe after the observation fix. 40 nursery episodes,
    1.0e8 transitions, 2,849 s; entropy 1.46 → 1.72.
  - **A1**: A0 plus the three options. 50 episodes, 3,611 s; entropy 1.58 → 0.96–1.13 as its
    weight fell to 0.005.
  - **R**: `random_init(7007)`.

**Manipulation check** (training data only): **pass.**
- Surviving-birth fraction over the last 10 nursery episodes: A1 0.289 vs A0 0.222 (needs
  ≥ 0.178).
- A1's colony at day 1,010 on training seeds 7000–7002: N 180, 541, 261 (needs ≥ 100 each).

**Primary test** (fresh seeds 9100–9111, 1,010 d, three traced windows each;
`scripts/p415.py`, `_output/p415/summary.json`). Δ = P(object-family action | nearest object a
ball) − P(object-family action | nearest object a tunnel or ramp), on free-time sub-step rows
within 5 in of an object, per seed.

| comparison | mean diff ± se | one-sided sign-flip p | passes (≥ 0.05 and p < 0.025) |
|---|---:|---:|---|
| **A1 − R (primary)** | **+0.011 ± 0.008** | **0.100** | **no** |
| A0 − R | +0.007 ± 0.007 | 0.217 | no |
| A1 − A0 | +0.004 ± 0.003 | 0.111 | no |

- Per-seed Δ: A0 within [−0.011, +0.011], A1 within [−0.016, +0.020], R within [−0.073, +0.017].
- Rows per window: A0 1,300–8,600; A1 130–1,100; R 0–6,000.
- **The falsifier holds.** The learner does not condition its free time on object
  consequences, even with the entropy weight cut tenfold and the advantage and λ fixes.
- **The stop rule applies:** no further substrate change for PPO learners. The gated secondary
  (amended H-f) is not run.

**Reported alongside.**
- *Probe* (training seed 7000, day 300): near an object, A1 chooses object actions rarely
  (P(MANIPULATE) 0.025, BACK_OFF 0.005, CIRCLE 0.013; A0 about 0.31 in total). Flipping
  `object_mobile` changes neither net's choice. Lower entropy made A1 decisive in the direction
  of avoiding objects, not of using balls.
- *A1 development guard* (training seeds, K = 12-continue control): not preserved and not
  equivalent. The colony peaks at about 420 (control 2,255) around day 732, and the phase-B
  doubling time is +20 d. It is viable but far from the Universe 25 arc.

**What it means.**
- Across P4-12 … P4-15, five learners on four substrates show the same thing. Movement form,
  ball consequences and place novelty are expressible, and the detectors (rules v9) would see
  them. But a homeostatic PPO learner neither uses the consequences nor shows a free-time form
  beyond a random mixer's.
- Strengthening the signal moved the policy, but not toward consequence-sensitive free time.
- By the preregistered stop rule, play work with PPO on this substrate ends here. The remaining
  routes are:
  - H-g (state-gating by phase) and the playground-off arm, which need no form;
  - `evo` (inherited weights, no entropy bonus);
  - replica v2 (review Tier 3) before any further play hypothesis.
- No claim of play. No evaluation seed of 8000–8011 was read.

## 2026-11-09 — Tier 1: detector rules v9 frozen; guard v2 checked; the frozen colony's predictive check; H-e re-read

All preregistered in `docs/PHASE4_DESIGN.md` §2 (v8 / v9) and §4.1 before any run (324bbe0;
pre-test amendments 2f509e3, fb1c82f; v9 9d2cda9).

**Detector rules: v8 failed one check, and v9 passes all of them.**
- *v8:*
  - Changes: criterion 5 on eligible rows only, contact re-gating of the object null, an order
    diagnostic, a fixed locomotor threshold.
  - Synthetic result: 19 of 20 checks pass. Locomotor criterion 3 against `random_walk` fails
    with FPR 0.13; v7 had 0.00.
  - Cause: the only change to locomotor events is the fixed threshold.
  - Its simulator negative control passed.
- *v9:* v8 with v7's threshold restored.
  - Synthetic split (90,000+): 20 of 20 checks.
  - The new hard negative `forced_gating` (onsets at one rate whenever eligible, long
    reflex-forced spells) meets criterion 5 in 0.03 / 0.00 of colonies under v9, against 6 of 6
    development colonies under v7. The mechanical criterion-5 artefact the review found is real,
    and v9 removes it.
  - Simulator negative control (random v5 nets, seeds 9500–9504, init 7005 / 7006, both
    substrates): criteria 3, 4 and 5 met in 0 of 30 windows per kind.
  - The scripted alternation still passes.
  - **v9 is the frozen rule set.**
- *Development corrections,* recorded as pre-test amendments: the synthetic generator's movement
  model now describes its own scales (object approach 60 in, withdrawal 2.25 in, per-row steps
  / K for its interpolated sub-steps).

**H-e re-read under v9** (exploratory; evaluation seeds 8000–8011 were already read under v5 /
v6; `_output/he_sweep/he_analysis_v9flags.json`):

| policy | kind | T, v5 (2026-11-08) | T, v9 | p, v9 | reading, v9 |
|---|---|---:|---:|---:|---|
| learned | object | +0.328 | +0.262 | 0.003 | supported |
| learned | locomotor | +0.229 | +0.079 | 0.128 | not supported |
| random | object | +0.099 (v6) | +0.099 | 0.047 | not supported |

- Excluding reflex-forced and pup rows removes the locomotor half of H-e, which already rested
  on two near-empty windows. The object half stands.
- **The continuous gating statistic** (`gate_relaxed_log_ratio`) rises with the relaxed share
  for every policy:
  - learned: +0.33 (object), +0.50 (locomotor);
  - random net: +0.49 / +0.22;
  - heuristic: +0.26 (object).

  The dose association is therefore not specific to learning. The learned net's object flags
  cross the threshold more often, but a random network shows the same relation in its
  continuous statistic.
- As the review recommended, C is no longer read as a response. H-e's object result is
  state-gating that grows with the relaxed share, found in every policy, and is not evidence of
  learned play.

**Guard v2: A/A check passes, but n = 24 is often inconclusive** (frozen K = 1 colony, seeds
9000–9047, 1,000 random 24 + 24 splits; `_output/calib_reference/summary.json`).
- "Not equivalent" in 0.0 % of splits; the bar is ≤ 5 %.
- "Inconclusive" in 60.3 %, because the cessation landmarks' CIs are often wider than their
  margins: last young day in 46 % of splits, last conception in 32 %, peak day in 25 %.
- Resolving ±30–40 d at these seed variances needs about 48 seeds per arm, or wider margins.
  Jason's call; the rule is not changed here.
- On the n = 3 development guards the new rule reads:
  - heuristic at g = 8: inconclusive;
  - `pretrain_v5`: not equivalent (N@736 +225, phase-B doubling −12 d, both outside their
    margins).

**Posterior predictive check of the frozen colony** (48 runs on seeds 9000–9047; 48 with the
removal of 150 adults on day 1014, seeds 9048–9095; 1,600 d):
- *Inside the 90 % prediction interval:* first litters, N@315, peak N, peak day, surviving-birth
  cessation, last conception, adults at 315, N@811, N@960, N@1444, N@1471, N@1588.
- *Misses (the record lies outside the interval):*

| landmark | Calhoun | frozen median [90 % PI] | with removal |
|---|---:|---|---|
| N@736 | 2056 | 1957 [1902, 2025] | 1950 [1898, 2047] |
| phase-B doubling time | 55 d | 44 [37, 55] | 45 [39, 54] |
| phase-C doubling time | 145 d | 97 [80, 137] | 99 [75, 135] |

- The colony grows too fast in both phases. The late gate on first litters compensates, as the
  review predicted.
- The removal event moves the late counts little: N@1444 median 128 without it, 120 with it.

**Morris screening** (`scripts/morris_screen.py`, `_output/morris/summary.json`).
- *Design:* 56 parameters — the 35 searched ones on their prior boxes, plus 21 hand-set biology
  and drive values on ±30 %. r = 10 trajectories, seeds 7003 / 7004, 1,140 runs of 1,600 d.
- *Identifiability.* The landmark × parameter matrix of μ* (rows scaled by each landmark's sd
  over runs) has singular values 11, 3.5, 2.9, 1.9, 1.6, 1.4, 1.2, 1.1, then 0.45 and below.
  - That is an effective rank of **8** at the preregistered 5 % cut, for 12 landmarks and 56
    parameters, with one dominant direction.
  - The calibrated 2m point is one member of a family of about 48 directions the landmarks
    cannot tell apart.
- *Influential parameters:*
  - Searched: `stress_density_gain`, `stress_decay`, `imprint_rate`, `breeding_p_base`,
    `maternal_erosion_rate`, `stress_mortality_scale`.
  - Hand-set, which rank as high as the searched ones: `weaning_days`, `thirst_gain_per_day`,
    `hunger_gain_per_day`, `pup_hunger_scale`, `fatigue_recovery_rest`, and `curiosity_gain` /
    `curiosity_decay_on_novel` for the phase-B doubling time.
  - The intrinsic drives carry weight in the curve, consistent with physics and novelty moving
    it.
- *Caveat.* 31 runs in extreme corners of the boxes reached `max_agents` 4,096 and dropped
  litters (counted by the new Tier 0 counter), so their peak N is capped.
- *Use.* An ensemble or history-matching recalibration (review, Tier 3) should search the
  influential set, hand-set values included, and report results across the not-ruled-out
  family, not one point.

**Not done in Tier 1, recorded:** the stale cell-count cache and slot-order fights (they change
calibrated behaviour and need adjudication).

## 2026-11-09 — P4-14 result: the novelty learner reads neither novelty nor mobility; its colony grows too fast

**What ran.**
- `pretrain_v5` is the `pretrain_v4` recipe with physics, novelty at g = 8 and observation
  v5, after the observation fix (f686968).
- Training: 43 episodes, 1.0e8 transitions, 2,830 s.
- Late surviving-birth fraction 0.22 (v3 0.11, v4 0.30); drive at episode end 0.49.

**Reading** (training seeds 7000–7002, physics and novelty at g = 8, K = 12 rechoose, rules v7 as
preregistered; `scripts/read_p414.py`, `_output/p414_reading/`):

| arm | kind | c1..c5 rates (v7, 9 windows) | form excess median [range] | form test met |
|---|---|---|---|---:|
| learned v5 | object | 0.33 1.00 0.00 0.00 0.44 | −0.096 [−0.196, −0.020] | 0 / 9 |
| learned v5 | locomotor | 1.00 1.00 0.00 0.00 0.67 | −0.017 [−0.024, +0.001] | 0 / 9 |
| random v5 | object | 0.56 1.00 0.00 0.00 0.00 | −0.069 [−0.118, +0.035] | 0 / 9 |
| random v5 | locomotor | 1.00 1.00 0.00 0.00 0.00 | +0.008 [−0.012, +0.034] | 0 / 9 |

Free-time shares, learned v5 (the same on all three seeds):

| explore | run_on | turn_back | social | manipulate | back_off | circle |
|---:|---:|---:|---:|---:|---:|---:|
| 0.14 | 0.11 | 0.11 | 0.28 | 0.09 | 0.16 | 0.13 |

- *Ball use.* 2 % of its object rows touch a ball.
- *The prediction failed.* The preregistered prediction (straight runs preferred) did not
  happen: RUN_ON and TURN_BACK have equal shares.
- *Criterion 5 under v7.* The 0.44 / 0.67 rates carry the mechanical artefact that v9 removes.

**Probe** (counterfactual inputs on 480 weaned animals of a learned-v5 colony, seed 7000, day
300; scratch script):
- *Novelty.* Setting novelty ahead / behind to (1, 0) instead of (0, 1) changes P(RUN_ON) by
  −0.007 and P(TURN_BACK) by −0.018. The net does not read the inputs.
- *Mobility.* Flipping `object_mobile` near an object changes P(MANIPULATE) by 0.002.
- *Weights.* The first-layer weights of these inputs are of ordinary size: they were not
  learned away, just not used.

**Curve guard** (training seeds, against the K = 12-continue heuristic; with guard v2; n = 3 is a
development screen, never decisive): **not preserved / not equivalent.**
- N@315 +414 ± 11.
- N@736 +225, outside its margin.
- Phase-B doubling time −12 d, outside its margin.
- Peak day and the decline band hold.

**What it means.**
- Three substrate changes, each giving free-time choices a consequence, have now left the
  learner's free time at chance: movement primitives, ball physics, place novelty.
- The probe shows why it is not the substrate: the learner does not condition on the
  consequence inputs at all.
- This matches the review's diagnosis. The free-time value differences sit below the entropy
  bonus's temperature, so the best entropy-regularised policy mixes evenly.
- The next lever is the learner's training signal (Tier 2: entropy annealing, advantage
  normalisation per transition type, λ per unit of time), not more substrate.
- H-f stays held. No evaluation seed was read.

## 2026-11-09 — Tier 0 integrity fixes (Jason: "Integrity fixes first")

What `docs/REVIEW_2026-11-09.md` Tier 0 asked for, all without changing any trajectory:

| change | where |
|---|---|
| every run writes `config.json` and `manifest.json` (commit, dirty flag, config sha256, library versions, platform, schema versions incl. detector rules); `run.json` embeds the manifest | `src/universe25/repro.py`, `sim.py` |
| unknown config keys are errors (`extra="forbid"` on every model); `ticks_per_day` must be a multiple of `ticks_per_day_ref` | `config.py` |
| `backend: auto` is the NumPy reference path (it picked Warp whenever CUDA worked, and the Warp path lacks three biology processes); Warp only when requested | `agents/state.py` |
| litters lost at `max_agents` are counted (`litters_dropped_at_capacity` in run.json) with a warning (the loss itself is unchanged) | `sim.py` |
| a spawned slot's `heading` is reset (it inherited the last occupant's) | `sim.py` |
| opt-in runtime invariants (`debug_invariants`): population accounting, drive and capacity bounds, positions, pup actions, stocks; read-only | `src/universe25/invariants.py` |
| golden trajectory hashes over the flag matrix, from committed inputs only (K = 1, K = 12 continue, traced, random-MLP rechoose, physics + novelty g = 8, scarce, 24 ticks/day), fast tier 115 d and slow tier 300 d, tagged with platform and NumPy version | `src/universe25/golden.py`, `scripts/golden_hashes.py`, `tests/golden/trajectories.json`, `tests/test_golden.py` |
| test tiers with per-file timing (`--tier fast` 17–19 s); a conservation test past the first births with the invariants on; strict-config tests; a fast H2 audit file | `tests/run_tests.py`, `tests/test_conservation.py`, `tests/test_h2_audit.py` |
| CI on push: ruff (error classes only) and the fast tier on Linux | `.github/workflows/ci.yml` |
| NumPy pinned to major 2 (trajectories depend on it) | `pyproject.toml` |
| seed ledger, including that 8000–8002 informed calibration and that the 12-seed adjudication block is not out-of-sample; wording corrected in HANDOFF, PHASE4_DESIGN and `seed_eval.py` | `docs/SEEDS.md` |
| guard control caches keyed by the control's config hash (`--control-substeps`); the two existing caches renamed to their hashes (K = 1: `ccfd54bf39`, K = 12 continue: `d3945c79c4`) | `scripts/policy_guard.py` |

**Bit-identity.** The seven reference trajectories hash exactly as before Tier 0 (after the
observation fix): heuristic K = 1 `bcc13721…`, K = 12 traced `90b68191…`, `pretrain_v2`
`36d412cc…`, random v2 `fb4d16b0…`, `pretrain_v3` `df06b41b…`, random v3 `14776dd6…`,
`pretrain_v4` with physics `25acd497…`. The heading reset changed none of them (a reused slot's
pup moves, and so rewrites its heading, before it ever chooses a free action). The golden table
records the traced arm equal to the untraced one at both tiers. The invariants held through the
first litters at K = 1 and with sub-steps, physics and novelty (seed 7100, 150 d).

Not done in Tier 0 (Tier 1 or later, per the review): the stale cell-count cache and slot-order
fights (change calibrated behaviour; flag plus adjudication), new random streams via
`SeedSequence`, a `uid` field for rebirth detection, checkpoint/restore, the experiment harness.

## 2026-11-09 — Review of environment and methods; an observation bug; a mislabelled control; heuristic guard at g = 8

**Review.** Five independent read-only reviews (fidelity, simulation methods, calibration and
statistics, learning and measurement, engineering) are merged in `docs/REVIEW_2026-11-09.md`,
with a tiered roadmap and three decisions for Jason. Headline points:
- **Fidelity.** The calibrated curve depends on the playground. With it off at seed 7000:
  N@315 890, peak 2431 near day 449. Phase A is a calendar gate, and the pen is a 4 × 4 floor
  grid, not Calhoun's 16 wall cells around an open centre.
- **Criterion 5 is partly mechanical:**
  - its candidate rows include reflex-forced and pup rows;
  - on eligible rows the learned net's locomotor gating falls below the threshold (exploratory:
    P4-13 traces);
  - so H-e "supported" (which varied only through criterion 5) is probably an artefact.
- **The learner.** Its free-time value differences sit below the entropy temperature, so
  mixing at chance is forced by the training setup.
- **Guard power.** At n = 3 an identical arm fails about 30 % of the time.
- **A live methods issue in the calibrated model.** The nursing-disturbance term reads a stale
  cell-count cache on 59 % of ticks.
- **A safety issue.** `backend: auto` selects Warp, which lacks three biology processes. Every
  run cited in NOTES since phase 4 forced NumPy.

**Bug (mine, P4-13): observations v4 and v5 showed the decision action.**
- The last-action one-hot read `recent_action` only for version 3. So v4 and v5 showed the
  decision action, not the previous free-time sub-step, against §1.8.
- Fixed in f686968, with a rechoose-mode test that fails without the fix.
- v2, v3 and heuristic trajectories hash identically. The `pretrain_v4` arm changes
  (`e9463fb1…` → `25acd497…`), as it must.
- `pretrain_v4` was trained, and its P4-13 reading made, with the bug. Its "free-time shares as
  v3" and "no form" are readings of a net that could not see its own last move. The
  ball-versus-fixed-object result does not depend on the one-hot, but the net was trained on a
  flawed input.
- The `pretrain_v5` run was stopped at episode 10 (kept as `pretrain_v5_bugged_stopped`) and
  restarted on the fix.

**Mislabelled control (mine, P4-12 onward).**
- `_output/policy_guard_control_7000_3_1600.json` was copied from the v2 development guard. It
  is the heuristic at **K = 12 continue** (physics off), not the K = 1 reference: its N@315 rows
  464 / 256 / 381 equal that arm's.
- Every development guard since P4-12 (learned v3 and v4, heuristic with physics, heuristic at
  g = 8) compared against it. NOTES called it "the need-driven / physics-off control". Read
  those guards as "against the K = 12-continue heuristic, physics off".
- P4-8 found that arm within 2 % of K = 1 on the landmarks it can resolve.
- The file is renamed `policy_guard_control_k12continue_7000_3_1600.json`, so it cannot be
  reused as a K = 1 control.

**Heuristic guard at g = 8** (P4-14, Jason's deviation of 2026-11-09; physics and novelty on,
K = 12 continue, training seeds 7000–7002, 1,600 d, against the K = 12-continue heuristic with
physics off; `_output/dev_guard_heuristic_nov_g8_train7000-7002.json`): **preserved** under the
amended H-d rule and the 10 % rule.

| landmark | control | g = 8 | paired diff |
|---|---:|---:|---:|
| N@315 | 367 | 341 | −26 ± 83 |
| peak N | 2255 | 2240 | −15 ± 25 |
| peak day | 535 | 563 | +29 ± 17 |
| last young day | 606 | 634 | +28 ± 7 |
| last conception day | 923 | 994 | +70 ± 12 |
| N@1588 | 19 | 37 | +18 ± 13 |

- The decline band at day 1200 holds.
- The calibration review's caveat applies: at n = 3 this rule has little power, so read it as
  "not falsified, low power".
- Last young day and last conception day shift later by 3.9 and 5.9 paired se: systematic
  shifts under 10 %.
- Confirming it would need an equivalence test on ≥ 24 fresh seeds (review, Tier 1).

## 2026-11-09 — Novelty-based curiosity (P4-14): built; relief matching misses its 10 % rule, stopped as preregistered

**Context.** Jason chose consequence-based curiosity in every family. Design:
`docs/PHASE4_DESIGN.md` §1.10, commit f0ff667, before the code (dbbfe86).
- *Place memory:* each animal keeps the last visit time of each bin of a 10 × 10 grid.
- *Locomotor relief:* the per-sub-step amount × g × the novelty of the bin entered,
  1 − exp(−Δt / 1 day).
- *Consequence gain:* g also scales the ball-push relief.
- *Observation v5* adds the novelty of the bins ahead and behind.
- *Gate:* g is chosen by matching the heuristic's adult mean curiosity to the frozen substrate.

**Checks.**
1. *Bit-identity with novelty off and g = 1: passes.* Seven trajectories hash identically
   before and after: the six of P4-13 and the `pretrain_v4` net with physics,
   `e9463fb1f65925c4`.
2. *Mechanics: pass* (`tests/test_novelty.py`): full relief on a new bin, none for staying,
   1 − exp(−Δt/τ) on a revisit, a spawned slot forgets, no relief for non-locomotor actions,
   the gain scales pushes, no random draw, observation v5. Every test file passes.

**Relief matching** (`scripts/scan_novelty_gain.py`; heuristic K = 12 continue, training seeds
7000–7002, adult mean curiosity sampled daily over days 100–700): **no g meets the preregistered
10 % rule.**

| g | adult curiosity (target 0.250) | rel. diff | boredom (target 0.064) | N@315 (target 367) | N@700 (target 2029) |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.410 | +464 % | 0.075 | 72 | 831 |
| 2 | 0.938 | +275 % | 0.082 | 85 | 1758 |
| 3 | 0.548 | +119 % | 0.088 | 266 | 2104 |
| 4 | 0.433 | +73 % | 0.091 | 197 | 2120 |
| 6 | 0.326 | +30 % | 0.091 | 390 | 2017 |
| 8 | 0.308 | +23 % | 0.091 | 341 | 2038 |

- The best g, 8, leaves adult curiosity 23 % above the target, so the rule says stop. The
  heuristic guard, `pretrain_v5` and the reading were **not run**.
- Curiosity flattens near 0.3 as g grows. Relief now comes only when an animal enters a bin it
  has not been in recently. The heuristic's continue-mode EXPLORE is a random walk that mostly
  stays in or near bins it has just visited, so larger relief per entry cannot pull the mean
  down much further (curiosity is floored at 0 per entry).
- Seen, not tested: at g = 6 and 8 the colony-size landmarks of the first 700 days are close to
  the target (N@315 390 and 341 vs 367; N@700 2017 and 2038 vs 2029), though curiosity is still
  higher. The proxy may be stricter than the curve. Only the guard would show it, and the guard
  was not run.
- Boredom rises by 0.03 at every g (locomotor boredom relief is unchanged; the heuristic spends
  less time in boredom-relieving actions).

**What this means.** The novelty substrate is implemented and bit-identical when off. Under the
preregistered gate it is not calibration-matched for the heuristic. Two ways on, both
deviations that need Jason:
- Run the heuristic guard at g = 8 anyway: the guard is the real test, and the early
  landmarks look matched.
- Re-preregister the matching: a wider g grid, a shorter τ, or matching on landmarks instead of
  mean curiosity.

No evaluation seed was read.

## 2026-11-09 — Ball physics and rules v7 (P4-13): v7 passes; the learner ignores the balls; physics moves the heuristic's curve

**Context.** Jason held H-f and chose to fix the substrate. Design: `docs/PHASE4_DESIGN.md` §1.9
and §2 v7, commit 9ad08f1, before the code (b8f0db5).
- Balls are pushed by contact (κ·u along the approach), roll with friction and bounce at the
  bounds.
- Object-family curiosity and boredom relief scales with the speed a contact gave a ball.
- Observation v4 (57 floats) adds the nearest object's mobility and speed.
- Rules v7 replace the form test's label shuffle with a re-simulation of an even family mix.

**Checks.**
1. *Bit-identity with physics off: passes.* Six trajectories hash identically before and after:
   - heuristic K = 1: `bcc13721a9144040`
   - heuristic K = 12 traced: `90b681913b578ae7`
   - `pretrain_v2`: `36d412cc465fb164`
   - random v2: `fb4d16b048dd4a8c`
   - `pretrain_v3` traced: `df06b41bee4daf96`
   - random v3: `14776dd64758a9a2`
2. *Mechanics: pass* (`tests/test_physics.py`): push, roll, bounce, fixed tunnels and ramps,
   relief scaling, no random draw, observation v4. Every test file passes.

**Rules v7: every preregistered check passes; v7 is the frozen rule set.**
- *Synthetic split* (seeds 70,000 + …, 30 colonies per class, 1,000 surrogates): 18 of 18,
  every AUC ≥ 0.998 (`_output/detector_validation_v7.json`).
  - Object c3 / c4 TPR is 0.93 (v6: 1.00): 2 of 30 `all_criteria` colonies miss the object
    form floor.
- *Simulator negative control* (`scripts/negcontrol_v7.py`; random v4 nets, init seeds 7003 /
  7004, training seeds 7006–7008, never used): criteria 3 and 4 are met in 0 of 18 windows per
  kind, without and with ball physics.
  - On the same windows v6 meets them in 11–17 % (object without physics 0.17; locomotor 0.11
    in both substrates).
- *Scripted alternation:* passes v7 in both kinds; the random net does not
  (`tests/test_actions_v2.py`).
- *Known property, seen here first.* Random mixers' object excess sits at −0.10 to −0.13. Object
  events are rows in contact, and contact favours approach moves; the even-mix reference is not
  conditioned on contact. The object form test is therefore conservative: a form must beat a
  random mixer by about 0.2.
- *Diagnostic: the action-space-v2 reading re-read with v7.*
  - Locomotor excess: learned v3 +0.015, random v3 +0.014.
  - No window meets the form test (v6: the random net met it in 5 of 18).
  - The object kind reads n/a, because those traces predate `obj_x`.

**Heuristic with ball physics** (K = 12 continue, training seeds 7000–7002, 1,600 d, against the
physics-off control; `_output/dev_guard_heuristic_phys_k12_train7000-7002.json`): **not
preserved.**

| landmark | control | heuristic + physics | paired diff |
|---|---:|---:|---:|
| N@315 | 367 | 183 | −184 ± 62 |
| peak N | 2255 | 2126 | −129 ± 51 |
| peak day | 535 | 694 | +159 ± 42 |
| last young day | 606 | 1011 | +406 ± 301 |
| N@1200 | 897 | 1194 | +297 ± 64 |
| N@1588 | 19 | 223 | +204 ± 126 |

- Seed 7000 resumes surviving births until day 1577 (final N 517). The decline band at day
  1200 holds.
- Mechanism (seed 7000, days 100–320): adult curiosity averages 0.73 with physics and 0.29
  without. In continue mode the heuristic's MANIPULATE approaches and holds, which now earns
  little relief. Curiosity stays high and the colony grows more slowly.
- **The object-relief channel carries weight in the calibrated curve.** The physics substrate
  is not calibration-neutral.

**`pretrain_v4`** (the v3 recipe with physics in every nursery world and observation v4; the
same 40 nursery worlds as v3):
- Run: 1.02e8 transitions, 3,162 s at 32k/s.
- Late surviving-birth fraction 0.30 (v3 0.11, v2 0.50); drive at episode end 0.46 (v3 0.50).
  Entropy 1.4–1.7, as v3.

**Development reading** (training seeds 7000–7002, ball physics, K = 12 rechoose, windows 400 /
700 / 1000 d, rules v7; `scripts/read_p413.py`, `_output/p413_reading/`):

| arm | kind | c1..c5 rates (9 windows) | form excess v7 median [range] | v6 shuffle excess | form test met |
|---|---|---|---|---:|---:|
| learned v4 | object | 0.44 1.00 0.00 0.00 0.00 | −0.104 [−0.178, −0.044] | −0.018 | 0 / 9 |
| learned v4 | locomotor | 1.00 1.00 0.00 0.00 0.56 | −0.006 [−0.008, +0.004] | +0.072 | 0 / 9 |
| random v4 | object | 0.44 0.89 0.00 0.00 0.00 | −0.123 [−0.185, +0.041] | −0.007 | 0 / 9 |
| random v4 | locomotor | 1.00 1.00 0.00 0.00 0.00 | +0.009 [−0.012, +0.074] | +0.083 | 0 / 9 |

- **The learner does not use the balls.**
  - Its free-time shares are v3's: explore 0.13, run_on 0.13, turn_back 0.12, social 0.29,
    manipulate 0.11, back_off 0.10, circle 0.12.
  - Only 3 % of its object-family rows are in contact with a ball (random v4: 3 %).
  - It does not tell balls from fixed objects. Within 5 in of a ball it picks MANIPULATE 17.4 %
    of the time; within 5 in of a tunnel or ramp, 17.6 %. The observation carries
    `object_mobile`.
  - About 8 % of its free-time rows are within 5 in of a ball.
- Colonies: learned v4 peaks at 2,302–2,398 on days 419–523. The random v4 colonies grow
  slowly: peak 263–1,871, still rising at the end of the run.
- Not examined: the object criterion-1 rate is 0.44 in both arms. Without physics it was 0.78
  (random v3) and 1.00 (learned v3).

**Curve guard, `pretrain_v4` with physics** (training seeds;
`_output/dev_guard_pretrain_v4_phys_train7000-7002.json`): **not preserved.**
- Amended-rule failures: last young day (−89 ± 28) and the decline band at 1200.
- It is v2's pattern, an early arc: peak day −55, N@315 +335 ± 171.
- Peak N (+4 %), N@736 and the last conception day hold.

**What this means.**
- Rules v7 work: the form test no longer credits the mechanics of the primitives. On every
  reading so far, no policy has a form beyond an even mix.
- Giving objects a consequence did not give the learner a reason to use them. The most likely
  reason, not yet tested: curiosity and boredom have consequence-free routes. Every locomotor
  move relieves curiosity at a fixed rate anywhere, and SOCIAL relieves boredom. The sparse ball
  relief therefore adds little the learner cannot get without objects.
- Making form matter would need the intrinsic drives to be relieved by consequences in every
  family. For example, locomotor curiosity would be relieved only by moving into places not
  recently visited (spatial novelty), so that the families compete on what they produce.
- That changes the heuristic's drives as well. Physics alone already moved its curve, so either
  path reopens the frozen calibration, or the physics arm stays an uncalibrated variant.
- Nothing here shows play. H-f stays held. The revised amendment (learned v4 vs random v4)
  would read about 0 on the development seeds, so it is not proposed for testing. No
  evaluation seed was read.

## 2026-11-09 — Action space v2 (P4-12): form is now expressible; the learner mixes the new moves like a random net

**What changed** (commit 0514a10, design `docs/PHASE4_DESIGN.md` §1.8, fixed before the code).
Four generic free-time movement primitives were added: `RUN_ON` and `TURN_BACK` along or
against the agent's own heading, and `BACK_OFF` and `CIRCLE` relative to the nearest object.
- Each relieves what its family relieves; no new reward, drive or play-named field (H2).
- Observation v3 has 55 floats.
- `pretrain_v3` is the `pretrain_v2` recipe with 15 actions.

**Acceptance checks (preregistered).**
1. *Bit-identity: passes.* Four reference trajectories hash identically before and after:
   - heuristic K = 1, 300 d: `bcc13721a9144040`
   - heuristic K = 12 traced, 200 d: `90b681913b578ae7`
   - `pretrain_v2` net, 150 d: `36d412cc465fb164`
   - random v2 net, 120 d: `fb4d16b048dd4a8c`
2. *Form is expressible and seen: passes* (`tests/test_actions_v2.py`, seed 7100, 260 d,
   window [250, 260)).
   - A scripted test policy meets the v6 form test in both kinds: excess +0.46, z 24 (object)
     and z 97 (locomotor).
   - The random v3 net does not (locomotor excess +0.080, z 2.6; object too few pairs).
   - Wording deviation: the prereg says the scripted policy alternates RUN_ON / TURN_BACK. The
     test uses TURN_BACK after every locomotor action, a one-step shuttle. The object half is
     MANIPULATE / BACK_OFF as written.
3. *Learned reading* (training seeds 7000–7002, ABUND-PG, K = 12 rechoose, windows 400 / 700 /
   1000 d, rules v6, 1,000 surrogates; `scripts/read_as2.py`, `_output/as2_reading/`). No pass
   condition.

| arm | kind | c1..c5 rates (9 windows) | form excess median [range] | reversal median | form test met |
|---|---|---|---|---:|---:|
| learned v3 | object | 1.00 1.00 0.00 0.00 0.00 | +0.008 [−0.060, +0.084] | 0.206 | 0 / 9 |
| learned v3 | locomotor | 1.00 1.00 0.00 0.00 0.78 | +0.090 [+0.080, +0.097] | 0.561 | 0 / 9 |
| random v3 | object | 0.78 0.89 0.33 0.33 0.00 | +0.032 [−0.026, +0.254] | 0.279 | 3 / 9 |
| random v3 | locomotor | 1.00 1.00 0.22 0.22 0.00 | +0.090 [+0.082, +0.116] | 0.560 | 2 / 9 |

Free-time shares in the traced windows:

| arm | explore | run_on | turn_back | social | manipulate | back_off | circle |
|---|---:|---:|---:|---:|---:|---:|---:|
| learned v3 | 0.15 | 0.11 | 0.13 | 0.29 | 0.10 | 0.11 | 0.11 |
| random v3 | 0.14 | 0.14 | 0.14 | 0.14 | 0.14 | 0.14 | 0.14 |

These are the same on all three seeds to two decimals.

**Reading.**
- **The learner did not learn a form.** Within each family it spreads its free time evenly
  over the primitives. It differs from the random net only in choosing SOCIAL twice as often.
  Its form excess is the random net's: +0.090 vs +0.090 median for locomotion, and nothing
  beyond chance for objects.
  - This is what the design predicts. The reward cannot tell the primitives of a family apart,
    since no relief depends on form (H2). PPO's entropy bonus (0.05) then pushes actions of
    equal value toward equal probability.
  - So with a form-blind reward, an entropy-regularised learner should converge to the random
    net's mixing within a family. Training seeds show exactly that.
- **The v6 form test has a mechanical baseline under action space v2.**
  - The random v3 net chooses near-uniformly and nearly i.i.d. (last-layer gain 0.01). Yet its
    locomotor excess is +0.08 to +0.12, with z 2–17.
  - Reason: the primitives are defined relative to the agent's last move, so random mixing of
    RUN_ON / TURN_BACK already orders the end-point labels. The within-episode label shuffle
    removes that order; it was the right null when every locomotor step was isotropic.
  - Object episodes in small, early random colonies (41–152 episodes) reach +0.15 to +0.25.
    The likely cause is contact gating after BACK_OFF; this is not isolated.
  - Net effect: the random v3 net meets criteria 3 and 4 in 5 of 18 windows (3 of 9 object,
    2 of 9 locomotor). The v6 negative control allowed at most 10 % per kind, and that control
    was run in action space v1. **v6's validation does not carry over to action space v2.**
    Absolute c3 / c4 flags are unreliable there until the null is rebuilt. A comparison of
    learned against random at matched composition is still valid.
- **Colonies on the canonical start.**
  - The learned v3 colony is viable: peak N 2281–2326 at days 601–714.
  - The random v3 colony grows slowly: peak N 736–1329, still at days 974–1005, the end of the
    run.

**Curve guard** (P4-1 style, training seeds 7000–7002, 1,600 d, K = 12, against the need-driven
control; `_output/dev_guard_pretrain_v3_train7000-7002.json`):

| landmark | control | learned v3 | paired diff |
|---|---:|---:|---:|
| first litters day | 103.0 | 103.0 | +0.0 ± 1.5 |
| N@315 | 367 | 486 | +119 ± 54 |
| peak N | 2255 | 2280 | +25 ± 16 |
| peak day | 535 | 669 | +134 ± 55 |
| last young day | 606 | 941 | +336 ± 44 |
| N@736 | 1971 | 2180 | +209 ± 16 |
| N@1200 | 897 | 1158 | +261 ± 75 |
| N@1444 | 139 | 361 | +222 ± 57 |
| N@1588 | 19 | 126 | +107 ± 26 |

- Verdict (amended H-d rule): **not preserved**. Failures: N@315, peak day, last young day.
- The decline band at day 1200 holds.
- The `pretrain_v2` net ran the arc about 80–120 d *early*; the v3 net runs it about 130–340 d
  *late*, with a long tail, a milder version of the random net's (+410 d, N@1588 ×20).

**Pre-training (`pretrain_v3`).**
- Run: 46 nursery episodes, 1.0e8 transitions, 7,398 s at 13.7k transitions/s (v2: 3,008 s at
  34k/s). The slowdown was not isolated, and other jobs shared the CPU.
- On the same 45 nursery episodes (same seeds and worlds), v3 learned less than v2:
  - Drive at episode end: +0.10 above v2 in episodes 0–9, +0.08 in the last ten.
  - Surviving-birth fraction: −0.10 vs v2 early and −0.39 late. v3 stayed near 0.11, while v2
    rose from 0.21 to 0.50.
  - Entropy: 1.3–1.5 through training, up to 1.65 in the last 100 updates (v2 0.85–0.9). Mean
    reward worsened again over the last fifth.
- Probe: on identical colony states (heuristic run, seed 7000, days 120 / 250 / 400), the v3
  net puts 12–17 % of its mass on the new primitives and 8–10 % on WITHDRAW (v2 ≈ 0). The same
  holds for nursing mothers, and WITHDRAW drifts an animal toward the corner, away from the nest.
- The evaluated net is `policy_final`, as fixed; no checkpoint was picked.

**What this means.**
- The substrate now lets a policy shape how a move unfolds, and a scripted policy shows the
  detectors can see it. The H2-clean learner has no reason to use that freedom: nothing it
  feels depends on form, so it mixes the primitives at chance.
- H-f as amended in the design (learned v3 vs random v3 at matched V) is predicted to be null
  by construction. On training seeds it already reads as null.
- Two separate gaps follow:
  - Detectors: the form test's null must include the movement mechanics, for example a
    composition-matched random policy run in the same colony.
  - Substrate: form will only matter to a homeostatic learner if some consequence depends on
    it, for example objects or conspecifics that respond to how they are approached.
- Both are Jason's decisions. No evaluation seed was read.

## 2026-11-09 — Detector rules v6: criteria 3 and 4 need a form beyond chance; no simulator policy has one

**Why.** Under v5 a random-init network met criteria 1–4 for locomotion in every window. The
development look (synthetic seeds 101–103; P4-8 traces of training seeds 7000–7002) found the
cause in the simulator itself. Every EXPLORE sub-step is an isotropic Gaussian step. For the
random net and the heuristic alike, the turn classes of locomotor events come out at
0.25 / 0.25 / 0.25 / 0.25 (straight / left / right / reverse), and the entropy rate equals that
of the order-shuffled sequence. Locomotor "episodes" are random walks, and a random walk meets
v5's criterion 3 (about half its direction pairs reverse relative to the end point; serious
runs have none) and criterion 4 (never rigid, never habituates).

**Rules v6** (preregistered in `docs/PHASE4_DESIGN.md` §2, commit f156624, before any test):
- Criteria 3 and 4 also need a *form test*: the episodes' approach–withdraw reversal fraction
  must beat a within-episode order shuffle of the same labels (excess ≥ 0.10, z > 1.645).
- The form test draws from its own random stream, so every v5 statistic is unchanged.
- The v5 flags stay in the output.

Development values of the excess: `all_criteria` 0.17–0.21, `random_walk` ≤ 0.05, simulator
random net and heuristic ≤ 0.03. Entropy-rate and turn-coding variants were tried in
development and dropped. With end-point coding a random walk reads more predictable than its
own shuffle (end effects). With turn coding the synthetic positive class has no order to
detect.

**Test results (all preregistered checks pass):**
- *Synthetic split* (seeds 60,000 + …, 30 colonies per class, 1,000 surrogates): **18 of 18**,
  every AUC 1.000, TPR 1.00, FPR 0.00. These are the 16 v5 checks scored with v6 flags plus
  both random-walk checks (`_output/detector_validation_v6.json`). `random_walk` now meets
  criteria 1 and 2 only.
- *Simulator negative control* (`scripts/negcontrol_v6.py`; random-init networks with init
  seeds 7001 / 7002 on training seeds 7003–7005, never used before; 18 windows per kind):
  criteria 3 and 4 are met in **0 of 18** windows per kind. Under v5, the same windows met
  locomotor criteria 3 and 4 in 18 of 18 and object criterion 4 in 18 of 18. The random nets'
  form excess is −0.09 to −0.03 for object episodes (approach-and-hold has fewer reversals than
  chance order) and −0.02 to +0.05 for locomotor episodes.

**v6 re-reading of the H-e sweep** (exploratory: 216 windows per kind, evaluation seeds already
read under v5; v5 files kept as `detectors_v5_unvalidated.json`). The v5 analysis reproduces
exactly from the v6 files.

| policy | kind | c1..c5, v5 | c1..c5, v6 | form excess median [range] | reversal median |
|---|---|---|---|---|---:|
| learned | object | 0.99 1.00 0.00 1.00 0.24 | 0.99 1.00 0.00 0.00 0.24 | −0.051 [−0.111, −0.011] | 0.008 |
| learned | locomotor | 1.00 1.00 1.00 1.00 0.96 | 1.00 1.00 0.00 0.00 0.96 | +0.009 [−0.010, +0.030] | 0.445 |
| heuristic | object | 0.96 1.00 0.00 0.00 0.00 | 0.96 1.00 0.00 0.00 0.00 | +0.000 [−0.004, +0.006] | 0.000 |
| heuristic | locomotor | 1.00 1.00 1.00 1.00 0.06 | 1.00 1.00 0.00 0.00 0.06 | +0.019 [+0.004, +0.036] | 0.486 |
| random net | object | 0.94 1.00 0.00 0.99 0.00 | 0.94 1.00 0.00 0.00 0.00 | −0.048 [−0.201, −0.002] | 0.007 |
| random net | locomotor | 1.00 1.00 1.00 1.00 0.00 | 1.00 1.00 0.00 0.00 0.00 | +0.012 [−0.072, +0.049] | 0.448 |

- **No policy meets criterion 3 or 4 in any window, the learned net included.** The learned
  net's object episodes approach and hold (reversal fraction 0.008). Its locomotor episodes are
  the simulator's random walk (excess +0.01). This holds in every food arm and window.
- The H-e test with v6 flags (`he_analysis_v6flags.json`) leaves the learned net unchanged:
  object T +0.328, locomotor T +0.229, because C already varied only through criterion 5. The
  random control's object reading drops from "supported" (p 0.0215, via criteria 1 and 4) to
  not supported (T +0.099, p 0.047, criterion 1 only). v6 removes the control's false positive.

**What this means.**
- The criteria now discriminate random behaviour. What remains play-relevant in the simulator is
  criterion 1 (non-functional), criterion 2 (untriggered) and criterion 5 (relaxed gating). A
  random network meets the first two by nature.
- The deeper limit is the substrate, not the detectors. No policy controls the path of a move:
  EXPLORE is a Gaussian step and MANIPULATE a straight approach to the nearest object. A policy
  can shape only *when* it chooses an action, never *how* the move unfolds. So a learner cannot
  express a play form here, whatever it learns.
- H-f ("learned object interactions differ from the heuristic's in sequence statistics,
  criteria 3 / 4") would compare zeros. It is not tested; it needs either a richer action space
  (movement relative to objects and conspecifics, under the calibration guard) or structure
  measured at the level of action sequences. That is Jason's decision.
- Nothing here shows play, and nothing rules it out in a substrate that allows form.

## 2026-11-08 — H-e result: supported by the preregistered rule; the object part is robust, the locomotor part is not

**Design** (PLAN §15.1 amendment, fixed before the run): 3 policies × 2 food arms × evaluation
seeds 8000–8011, 1,010 days, 12 sub-steps, traced windows at days 400 / 700 / 1000, detector
rules v5 (1,000 surrogates). 72 runs, 216 window units, 6,760 s at 6 workers.
`scripts/sweep_he.py`, then `scripts/analyse_he.py`; outputs in `_output/he_sweep/`
(`he_analysis.json`), log in `_output/he_analysis_log.txt`.

**Dose** (relaxed share of weaned rows, mean ± se over 12 seeds):

| policy | food | day 400 | day 700 | day 1000 |
|---|---|---:|---:|---:|
| learned | abund | 0.172 ± 0.022 | 0.012 ± 0.002 | 0.246 ± 0.009 |
| learned | scarce | 0.229 ± 0.013 | 0.188 ± 0.020 | 0.229 ± 0.013 |
| heuristic | abund | 0.110 ± 0.004 | 0.031 ± 0.001 | 0.087 ± 0.004 |
| heuristic | scarce | 0.111 ± 0.005 | 0.062 ± 0.009 | 0.084 ± 0.011 |
| random net | abund | 0.135 ± 0.002 | 0.062 ± 0.009 | 0.060 ± 0.003 |
| random net | scarce | 0.136 ± 0.002 | 0.083 ± 0.008 | 0.086 ± 0.011 |

The learned colony runs its arc early (H-d). At day 700 the abundant colony is in its crowding
crisis and almost no weaned animal is relaxed (0.012). The scarce colony stays small and
relaxed (0.19–0.23). The dose therefore varies most at day 700, and there it mostly separates
the two food arms.

**Primary test** (criteria count C on dose, Kendall τ-b within window strata, 10,000
permutations):

| policy | kind | T | τ at 400 / 700 / 1000 | p (one-sided) | preregistered reading |
|---|---|---:|---|---:|---|
| learned (primary) | object | +0.328 | +0.40 / +0.40 / +0.18 | 0.0004 | supported |
| learned (primary) | locomotor | +0.229 | +0.40 / +0.29 / +0.00 | 0.0002 | supported |
| heuristic (control) | object | −0.182 | +0.00 / −0.31 / −0.24 | 0.990 | falsified |
| heuristic (control) | locomotor | −0.024 | +0.00 / −0.13 / +0.05 | 0.629 | falsified |
| random net (control) | object | +0.118 | +0.35 / +0.00 / +0.00 | 0.0215 | supported |
| random net (control) | locomotor | +0.000 | constant C | 1.000 | falsified |

**H-e, by the preregistered rule: supported** (object supported, locomotor supported).

**What the result rests on.** For the learned net, criteria 1, 2 and 4 are met in every window
but one (one object window misses criterion 1). Criterion 3 is never met for object episodes
and always met for locomotor episodes. So C varies only through criterion 5, onsets gated by
the relaxed field: object C is 3 or 4 (17 of 72 windows meet criterion 5), and locomotor C
is 4 or 5 (69 of 72 meet it). The finding is
therefore narrower than "more play-like where animals are relaxed". In windows where more of
the colony is relaxed, the learned net's onsets concentrate more strongly in the relaxed state,
enough to cross the 2× gating threshold. The dose and criterion 5 are both defined by the
relaxed field, so the test sits close to its own definition. Read it as state-gating that
scales with the state's prevalence, not as evidence of play.

**Reported beside it** (preregistered, not decisive):
- Not an episode-count power effect: episode counts *fall* with dose (learned T = −0.11
  object, −0.23 locomotor).
- Gating statistic against dose (learned): log ratio T = +0.36 (object) and +0.53 (locomotor),
  both p < 0.001. Criterion 2's trigger-free share rises too (+0.21, +0.31), but its flag does
  not change.
- Controls: the heuristic shows no dose-response in C (both kinds T ≤ 0). The random net's
  object C reads "supported" (p 0.0215) through criteria 1 and 4, not 5. So a positive reading
  of this test does not by itself point to learning.
- Food contrast, abundant − scarce (learned): Δ dose −0.072 ± 0.018, Δ C object −0.33 ± 0.09,
  locomotor −0.08 ± 0.05. Scarcity made the learned colony *more* relaxed and its object
  episodes *more* gated. Surplus-resource theory read by food runs backwards here, as the
  manipulation check predicted. Read by state, it agrees.

**Exploratory checks** (not preregistered; scratchpad scripts `he_c5_diag.py`,
`he_robust.py`, `he_floor.py`):
- *Criterion 5 is limited by effect size, not power.* No window failed criterion 5 with a
  ratio ≥ 2 and a low z. Relaxed rows number in the thousands and z values are large.
- *The gating–dose coupling is partly structural.* The random net's log ratio also rises with
  dose (object T = +0.51, locomotor +0.17; heuristic object z +0.33). Its onsets are not gated
  above 2× anywhere. What sets the learned net apart is the *level* of gating (locomotor log
  ratio 1.0–1.8, that is 3–6× more onsets when relaxed). Some of its *dependence on dose* is
  shared by policies that do not learn.
- *Object result is robust.* T = +0.199, p 0.0096 with strata split by food arm too, so it is
  positive within a food arm. Leave-one-window-out T ranges over [+0.30, +0.36], max p 0.002.
  It holds unchanged when near-empty windows are dropped.
- *Locomotor result is not robust.* It rests on the 3 windows that fail criterion 5, all in
  the abundant colony's crisis: doses 0.0002, 0.0014 and 0.045. Two of them have only 60 and 372
  relaxed rows, so criterion 5 can barely be measured there (a floor). Without those two
  windows, locomotor T = +0.098, p 0.043, which would read *not supported*. Leave-one-out alone
  does not show this (T ≥ +0.13, max p 0.003), because the floor takes two windows.
- *A duplicate unit.* `random_abund_8002` and `random_scarce_8002` give identical day-400
  windows. That random colony stayed below the carrying capacity up to day 400, so the two food
  arms had not diverged yet. It is one of 72 random-net units and does not change any reading.

**Honest summary.** The preregistered test supports H-e. The robust part is narrow: the learned
net's object onsets are more strongly gated by the relaxed field in windows where more animals
are relaxed. This holds across seeds, within food arms and in every window stratum. The
locomotor part depends on two crisis windows where the criterion can hardly be measured.
Nothing here shows play. Criteria 1–4 do not discriminate on simulator movement (the random net
meets 1–4 for locomotion everywhere). The response is criterion 5 and the dose is the relaxed
share, so the test is near-definitional. PlayScore stays unvalidated.

## 2026-11-08 — Detector rules v5 (exogenous triggers only); H-e amended; sweep harness

**H-e amended — ADOPTED by Jason (state-based dose-response).** Written into PLAN §15.1 and
committed (dd33dbe) before any code for it ran: per episode kind, the number of criteria met
in a window should rise with that window's relaxed share; Kendall τ-b within window strata
(policy × window, 24 units each: 2 food arms × 12 evaluation seeds), mean over the three strata,
dose permuted within strata; learned net primary (one-sided α 0.025 per kind), heuristic and a
random net of the same architecture as controls; food contrast and episode-count checks reported
beside it.

**Rules v5** (written into `docs/PHASE4_DESIGN.md` §2 and committed before the test): criterion
2 counts exogenous triggers only — aggression received, or a density jump in the cell the
individual occupied at its previous decision's start. Its own cell entries no longer count
(`self_entries=True` keeps the v4 set for diagnostics). New synthetic classes
`all_criteria_mobile_k12` / `triggered_mobile_k12`: 2 × 2 cells, objects in a denser cell of
their own, each row recording the cell of its start position as the recorder does. Development
look on seeds 101–103 only. **Test on a fresh split (seeds 50,000 + …, 30 colonies per class,
1,000 surrogates): 16 of 16 checks pass, every AUC 1.000, TPR 1.00, FPR 0.00.** Diagnostic:
under the v4 trigger set, `all_criteria_mobile_k12` object onsets read locked in 30 of 30
colonies. The mobile world reproduces the simulator's false locking, and v5 removes it.

**v5 on the P4-8 simulator traces** (training seeds 7000–7002, windows at days 400 / 700 / 1000,
flag rate over 9 window-seeds, c1…c5):

| arm | kind | v4 | v5 |
|---|---|---|---|
| heuristic, continue | object | 1.00 0.00 0.00 0.00 0.00 | 1.00 **1.00** 0.00 0.00 0.00 |
| heuristic, continue | locomotor | 1.00 0.00 1.00 1.00 0.11 | 1.00 **1.00** 1.00 1.00 0.11 |
| heuristic, rechoose | object | 1.00 0.00 0.00 1.00 0.00 | 1.00 **1.00** 0.00 1.00 0.00 |
| heuristic, rechoose | locomotor | 1.00 0.22 1.00 1.00 0.11 | 1.00 **1.00** 1.00 1.00 0.11 |
| random network | object | 1.00 0.00 0.00 1.00 0.00 | 1.00 **1.00** 0.00 1.00 0.00 |
| random network | locomotor | 1.00 0.00 1.00 1.00 0.00 | 1.00 **1.00** 1.00 1.00 0.00 |

Criterion 2 now reads "not locked" everywhere, but this is weak evidence. Exogenous triggers
are rare in the simulator: 0.86–0.97 of onsets are trigger-free, the same as under the shifted
null. So criterion 2 says only that onsets are not time-locked to aggression or crowding.

Read honestly, the full table shows that the criteria discriminate little on simulator
locomotion. The random network and the heuristic, neither of which learns or has any reason to
play, meet criteria 1–4 in every locomotor window. Only criterion 5 (onsets gated by the relaxed
field) separates them, and it is rarely met (0.11 and 0.00). The synthetic `random_walk` class
also meets 1–3 (P4-5). So a locomotor criteria count near 4 means "random-like movement outside
serious tasks", not play. For the H-e test, the count can only vary through criteria 3–5 for
object episodes and through criterion 5 for locomotor episodes, and the controls show what that
variation looks like without learning. No hypothesis has been tested yet.

**Harness** (P4-6 for H-e): `scripts/sweep_he.py` (runs, traces and v5 detection; resumable),
`scripts/analyse_he.py` (preregistered test and reported-beside tables),
`metrics/dose_response.py` (stratified τ-b permutation test; tests against scipy). The detector
output now carries the dose (`relaxed_share_weaned`) and the rule version. Smoke-tested on 68-day
runs of training seed 7000.

## 2026-11-08 — P4-9 detector rules v4; the survival condition fails its manipulation check

**Detector rules v4** (written into `docs/PHASE4_DESIGN.md` §2 before the test). With K
free-time sub-steps per decision: surrogate shifts for criteria 1, 2 and 5 move by whole
decisions; the criterion-2 trigger window runs from the start of the previous decision to the
onset row (added after a development look at seed 101, before the test); the serious template's
reversal fraction counts as 0 below 20 direction pairs. With K = 1 the shifts, their random draws
and the window are exactly v3's (tested). Fresh split (seeds 40,000 + …, 30 colonies per class,
1,000 surrogates): **14 of 14 checks pass** — the 12 v3 checks (AUC 0.983–1.000, TPR ≥ 0.97,
FPR 0.00) and two new sub-step checks for criterion 2 (`all_criteria_k12` vs `triggered_k12`,
object and locomotor: AUC 1.00, TPR 1.00, FPR 0.00). Recorded limit: stretched decision-level
alternation loses criterion 3 at the sub-step grain.

**v4 on the simulator** (the P4-8 traces, training seeds 7000–7002, windows at days 400, 700 and
1000, flag rate over 9 window-seeds): criteria 1, 3, 4 and 5 are unchanged from v3; **criterion
2 now reads "locked" in every arm** (object episodes: heuristic continue 1.00 → 0.00, heuristic
rechoose 1.00 → 0.00, random network 0.78 → 0.00). Cause: entering a new cell counts as an
exogenous trigger, and with the window now spanning the previous decision, an agent's own approach
to an object — which usually crosses into a playground cell — counts as the trigger of its own
episode. The synthetic worlds never tested this (their individuals stay in one cell). Criterion 2
is not interpretable on simulator traces until the trigger set separates self-caused cell entries
from exogenous events (rules v5, needs synthetic classes that move between cells and a fresh
split). No hypothesis has been tested with simulator detector readings.

**Survival condition: three designs fail the manipulation check.** The preregistered SCARCE-PG arm
had no quantitative definition. Tools added (`resources.scarce_supply: capacity`,
`scarce_capacity_animals`, optional famine pulses; foragers at a hopper split a short stock
equally — scramble competition, bit-identical for the abundant arm; `configs/scarce.yaml`;
`tests/test_scarcity.py`). A first per-capita rule (85 % of need, split equally over the cells)
starved the colony before day 100 and is a death spiral by construction (supply shrinks with the
colony). The manipulation check that matters for H-e is the share of weaned animals in the
relaxed field (fed, watered, energetic, unstressed, unwounded), heuristic policy, training seeds
7001–7002, 900 d:

| condition | colony, days 450–900 | relaxed share, day 600 | relaxed share, day 900 |
|---|---:|---:|---:|
| abundant (calibrated) | 1,750–2,170 | 0.05–0.08 | 0.13–0.16 |
| carrying capacity 1,000 animals | 1,190–1,330 | 0.19–0.30 | 0.33–0.34 |
| carrying capacity 400 animals | 480–620 | 0.14–0.28 | 0.33–0.35 |
| capacity 1,000 + famines (15 of every 60 d at 25 %) | 450–800 | 0.33–0.38 | 0.34–0.38 (0.33 in famines, 0.37 between) |

In this demographic world food scarcity acts through mortality: the colony shrinks until its
survivors are fed, and the smaller colony escapes the crowding stress that dominates the relaxed
field under abundance. So unlimited food produces the *least* relaxed animals in the later phases
— Calhoun's paradox — and a food-regime contrast points opposite to Burghardt's surplus-resource
prediction that H-e assumes. H-e as preregistered (detector rates higher in ABUND-PG than in
SCARCE-PG) cannot be read as a test of surplus-resource theory here. Decision pending (PLAN §15.1):
define abundance vs survival by the animals' state (relaxed-field share, pooled across arms,
windows and seeds, as a dose-response) with the food arms as a secondary contrast, or keep the
food arms as preregistered and report the reversed manipulation.

## 2026-11-07 — H-d, preregistered test of a learned arm: not preserved; the learned colony runs the Universe 25 arc about 70–100 days early

**Test as preregistered** (`PLAN.md` §15.1, H-d amended 2026-11-06): the frozen pre-trained
learner (`_output/pretrain/pretrain_v2/policy_final.npz`, eight-drive reward, `mlp_frozen` with
12 re-chosen sub-steps) against the calibrated need-driven control (no sub-steps; the cached
control every arm has been judged against) on the 12 evaluation seeds 8000–8011, 1,600 days, the
canonical 4-pair start. First use of the evaluation seeds by a learned arm.
`_output/policy_guard_mlp_pretrain_v2.json`; mean ± se, paired = learner − control:

| landmark | Calhoun | control | heuristic, 12 sub-steps (continue) | **learner v2** | drift | paired |
|---|---:|---:|---:|---:|---:|---:|
| first litters | 104 | 102 ± 0 | 102 ± 0 | 102 ± 0 | 0.001 | +0.1 ± 0.3 |
| N @ 315 | 620 | 470 ± 43 | 531 ± 49 | **832 ± 52** | 0.771 | +362 ± 70 |
| peak N | 2,200 | 2,252 ± 13 | 2,241 ± 15 | 2,364 ± 18 | 0.049 | +111 ± 23 |
| peak day | 560 | 534 ± 7 | 541 ± 13 | **465 ± 7** | 0.129 | −69 ± 8 |
| surviving births cease | 600 | 593 ± 8 | 597 ± 15 | **490 ± 7** | 0.174 | −103 ± 7 |
| N @ 736 | 2,056 | 1,956 ± 11 | 1,951 ± 13 | 2,089 ± 11 | 0.068 | +133 ± 18 |
| conception cessation | ≈ 920 | 935 ± 8 | 947 ± 11 | 910 ± 6 | 0.027 | −25 ± 12 |
| N @ 1200 (band 0.35–0.85 × peak) | | 839 ± 20 | 822 ± 32 | 692 ± 26 (**0.29**) | 0.175 | −147 ± 35 |
| N @ 1444 | 122 | 127 ± 8 | 128 ± 14 | 63 ± 6 | 0.503 | −64 ± 10 |
| N @ 1588 | 27 | 19 ± 2 | 23 ± 3 | 6 ± 1 | 0.670 | −13 ± 2 |

**Verdict: NOT PRESERVED** under the amended rule and under the original 10 % rule (failures:
N@315 at 5.2 paired se, peak day at 9.1, cessation of surviving births at 14.5, decline band
missed). Peak N (+4.9 %), N@736 (+6.8 %) and conception cessation (−2.7 %) pass. The three
training seeds (development guard) gave the same picture.

**What H-d now says.** The calibrated Calhoun curve is a property of the biology *and* the
behaviour, not of the biology alone: a random policy breaks it entirely (P4-1), and a learned
drive-reduction policy with maternal motivation reproduces its shape and size but shifts it
forward. The mechanism (NOTES 2026-11-07, nursery v2): learned mothers raise more young early, so
crowding and the developmental breakdown arrive sooner; the biology was calibrated against the
heuristic's slow early growth.

**Against the record** (canonical error of the means over the five canonical landmarks): control
0.068, heuristic with 12 sub-steps 0.043, learner 0.157. The learner is closer to Calhoun than the
control on peak size relative to N@736 (2,089 vs 2,056) and on conception cessation (910 vs ≈ 920),
further on N@315 (832 vs 620), peak day (465 vs 560), cessation of surviving births (490 vs 600)
and the late tail (63 / 6 vs 122 / 27; Calhoun's late counts are post-removal, so the record sits
above a no-removal run, not below).

**Consequences for the play experiments.** H-e, H-f and H-g compare conditions *within* a policy
(abundance vs scarcity, playground on vs off, phase of the arc), so they can run on the learned
colony as it is, with its arc reported alongside. Any statement that ties a learned colony to the
Calhoun record must use the learned colony's own phases (its peak near day 465, not 560).
Recalibrating the biology for the learner would reopen the frozen calibration (Jason's call).

## 2026-11-07 — Nursery v2 (founding colonies): the learned colony now spreads and runs the Universe 25 arc, faster

**Change** (Jason chose "widen and retrain"): founding worlds in 40 % of episodes — 4 to 30
pairs of 48- to 90-day-old founders in one to four cells, 300 days, the calibrated conception
gate — and mixed worlds concentrated into one to eight cells half the time (conception gate
lifted for their mature adults). Pre-training v2 from scratch (`_output/pretrain/pretrain_v2/`):
45 episodes (14 founding), 1.02 × 10^8 agent-steps, 3,075 updates, 50 min, 34,000 steps/s, VRAM
262 MB; founding colonies grew from 12–60 animals to 950–1,800 in 300 days; policy entropy
1.13 → 1.04 (v1 ended at 0.60).

**Development guard** (frozen v2 policy, canonical 4-pair start, training seeds 7000–7002,
1,600 d, 12 sub-steps, against the heuristic at the same grain; not the preregistered evaluation):

| landmark | Calhoun | heuristic | learner v1 | **learner v2** |
|---|---:|---:|---:|---:|
| first litters | 104 | 103 | 102 | 102 |
| N @ 315 | 620 | 367 ± 61 | 624 ± 56 | 852 ± 106 |
| peak N | 2,200 | 2,255 ± 28 | 958 ± 90 | **2,406 ± 44** |
| peak day | 560 | 535 ± 17 | 709 ± 40 | 456 ± 24 |
| surviving births cease | 600 | 606 ± 18 | 882 ± 147 | 483 ± 28 |
| N @ 736 | 2,056 | 1,971 ± 35 | 918 ± 82 | **2,095 ± 21** |
| conception cessation | ≈ 920 | 923 ± 26 | 863 ± 147 | **907 ± 23** |
| N @ 1200 / peak | 0.35–0.85 | 0.40 | 0.41 | 0.29 (band missed) |
| N @ 1444 / 1588 | 122 / 27 | 139 / 19 | 160 / 77 | 65 / 7 |

Amended H-d on these three training seeds: not preserved (N@315 +132 %, surviving births cease
−20 %, decline band); peak N, N@736 and conception cessation are within 10 % of the control.

**Why it spreads now** (seed 7000, 800 d): from day 300 only 34–42 % of the learned colony sits
in its four most crowded cells (heuristic 40–55 %, v1 95–99 %); NEST is 3 % of adult decisions
(v1 48 %); the adult action mix — FORAGE 0.28, DRINK 0.28, REST 0.15, SOCIAL 0.09, EXPLORE 0.09,
MANIPULATE 0.04 — resembles the heuristic's. The v1 crowding was the harness defect diagnosed in
P4-3, and it is gone.

**Why the arc is faster:** the learned mothers raise more young early (N@315 852 vs 367), so the
colony reaches crowding sooner; competence collapses earlier (0.57 at day 250 vs 0.97), the
withdrawn majority forms earlier, surviving births stop near day 480 and the late decline is
steeper. The biology was calibrated against the heuristic's slow early growth (its N@315 is the
known third-low miss), so better maternal care moves the whole arc forward. That is the content of
H-d: the calibrated curve depends on the behaviour policy, here through maternal care.

**Reading against the record:** the learned colony now has Universe 25's shape and size — a peak
of 2,406 (2,200), N@736 2,095 (2,056), conceptions ending at day 907 (≈ 920), an irreversible
collapse — on a timeline about 100 days early (peak day 456 vs 560, last surviving birth 483 vs
600) with faster early growth (852 vs 620 at day 315). Three training seeds only; the
preregistered test is the guard on seeds 8000–8011.

## 2026-11-06 — P4-3: nursery pre-training; on the canonical start the learned colony crowds into four cells

**Built.** `learn/nursery.py` + `scripts/pretrain_nursery.py`: one persistent learner over
60-day randomised nursery episodes (training seeds 7000–7009 only): 200–1,500 adults and
juveniles in random nest boxes of all 16 cells, nursing mothers with litters, pregnant females,
abundant or scarce food, playground open or closed with random object counts, 12 re-chosen
sub-steps; checkpoints with bit-for-bit resume (tested), episodes and update logs, manifest
(versions, GPU, commit, throughput, VRAM). Decisions stay at 6 per day (the card's 24 ticks per
day would only hold actions over more ticks); the learner sees 20-minute sub-steps.

**Pre-training v1** (`_output/pretrain/pretrain_v1/`): 61 episodes, 1.02 × 10^8 agent-steps,
1,891 updates, 33 min, 51,700 steps/s, VRAM peak 246 MB. Young surviving to weaning: 410 in the
first ten episodes, 7,420 in the last ten; colonies that shrank in early episodes (2,381 → 1,820)
grow in late ones (1,205 → 1,819); mean D at episode end 0.157 → 0.124; policy entropy
1.16 → 0.60.

**Development guard — the pretrained policy frozen on the canonical 4-pair start** (training
seeds 7000–7002, 1,600 d, 12 sub-steps, against the heuristic at the same grain; these are not
the preregistered evaluation seeds):

| landmark | Calhoun | heuristic | pretrained learner |
|---|---:|---:|---:|
| N @ 315 | 620 | 367 ± 61 | **624 ± 56** |
| peak N | 2,200 | 2,255 ± 28 | **958 ± 90** |
| peak day | 560 | 535 ± 17 | 709 ± 40 |
| surviving births cease | 600 | 606 ± 18 | 882 ± 147 |
| N @ 736 | 2,056 | 1,971 ± 35 | 918 ± 82 |
| conception cessation | ≈ 920 | 923 ± 26 | 863 ± 147 |
| N @ 1444 / 1588 | 122 / 27 | 139 / 19 | 160 / 77 |

Not preserved under the amended H-d rule (N@315, peak N, peak day). Early growth now matches
Calhoun better than the heuristic does (good maternal care); the colony then stops near 960.

**Why (seed 7000, 800 d, per 50 days; `plateau_diag` in a scratch folder):** from day 300
the learned adults spend **48 %** of their decisions going home (NEST; heuristic 5 %) and almost
none on SOCIAL, EXPLORE, MANIPULATE or MATE; **95–99 %** of the colony sits in its four most
crowded cells (heuristic 40–55 %). The founders' nests are in the four corner cells and pups
inherit their mother's nest, so a stay-home policy keeps the whole colony in those cells; the
nest-capacity spill-over that scatters the heuristic colony never fires (four cells hold 960
animals in their boxes). Local crowding then runs the breakdown early: adult competence 0.51 at
day 250 and 0.05 by day 400 (heuristic 0.97 and 0.48), withdrawn adults 486 of 642 at day 400,
about 30 conceptions per 50 days, and a plateau between 650 and 1,100.

Two causes, both fixable and both worth recording:
1. *Train-test mismatch in the nursery.* Nursery colonies start spread over all 16 cells, so
   going home never meant crowding; no episode showed a colony founded in a few cells. A defect
   of the v1 harness.
2. *The reward barely sees chronic stress.* With N = 4, a stress of 0.3 (δ = 0.2) contributes
   δ⁴ ≈ 0.002 to D, so moderate crowding is almost free to the learner, while the biology turns
   it into developmental damage and withdrawal that no drive registers.

Options (decision pending): (a) widen the nursery to include founding colonies (few founders in
one to four cells, as in the canonical start) and re-pretrain, then repeat this guard; (b) run
the preregistered guard on seeds 8000–8011 now and record "not preserved" as the H-d result for
the drive-reduction learner; (c) revisit the drive function for stress (an amendment to the
preregistered reward). (a) first is recommended: it removes a harness defect without touching the
reward, and (b) stays available afterwards.

## 2026-11-06 — Maternal drive adopted; P4-2 acceptance met (Jason's decision)

**Change (reward amended before any learned arm was judged).** An eighth drive,
`maternal_need` (`agents/drives.py`): for a female in the nursing role with a nest box, the mean
hunger of the pre-weaning pups in her box (nursing in the simulation is per box), zero
otherwise. It enters the drive-reduction reward like the other seven (D over eight drives,
D_MAX = √8) and is the 49th observation value (observation v2; 48-input weight files no longer
load). The biology does not read it: the heuristic stays bit-identical (300-d hash `966401ea…`).

**First run: necessary but not sufficient** (entropy 0.01, 450 d, same nursery as before):
colony 984 (seven drives: 496; heuristic 2,072), 5.3 % pup survival, and the frozen final policy
still chose NEST / NURSE 0.00 for nursing mothers. For mothers whose litter was hungry
(maternal_need median 0.45 of its range) the learned policy gave P(NEST) 0.003 and P(NURSE)
0.005, where its untrained start gave 0.10 each: PPO had driven them down. Cause: females enter
the nursing role at conception, about three weeks before any pup exists; in that stretch the
nest only costs time that relieves the social drive elsewhere, so the shared policy learns
"nursing role: go elsewhere" and, with entropy 0.01, never samples the nest often enough after
the litters arrive to see the payoff. An exploration failure, not a missing incentive.

**Fix: entropy coefficient 0.05** (development choice on training seed 7000; the design said
0.01). Same nursery, 450 d: colony 2,377, pup survival 31 % between days 350 and 450; frozen
weights: mothers within 8 in of the nest 0.30 of the time (heuristic 0.25), NURSE 0.10 / NEST
0.04 (heuristic 0.09 / 0.04), 838 of 2,013 pups survived (heuristic 520 of 1,966).

**Acceptance run** (entropy 0.05 default, 100 founding pairs, 12 sub-steps, 650 d, training seed
7000; `_output/nursery_smoke.json`):

| arm | mean D, last quarter | first quarter | colony at day 650 | births | surviving births | learner transitions |
|---|---:|---:|---:|---:|---:|---:|
| learner (`mlp_ppo`, eight drives) | **0.251** | 0.417 | **2,165** | 14,617 | 2,224 | **1.51 × 10^7** |
| same network, no updates | 1.035 | 1.014 | 1,751 | 23,320 | 1,864 | — |
| heuristic (continue) | 0.822 | 0.791 | 1,781 | 15,898 | 2,007 | — |

**P4-2 acceptance: met** — the learner's mean D is below the no-update baseline (0.25 vs 1.04,
and below the heuristic's 0.82) with 1.5 × 10^7 transitions, and the comparison is no longer
confounded by a small colony. All three colonies pass through a plateau and stop producing
surviving young after about day 450. Per-drive means in the last quarter: the learner keeps
fatigue (0.23 vs 1.03 / 0.71), social drive (0.46 vs 1.36 / 1.23), curiosity (0.07 vs 0.12 /
0.21) and boredom (0.04 vs 0.07 / 0.07) low; its stress is the highest (0.57 vs 0.45 / 0.48),
because its colony is the largest. Frozen 650-day weights (days 110–160 of a fresh nursery):
mothers within 8 in of the nest 0.38 of the time, NURSE 0.15 / NEST 0.07, 905 of 1,975 pups
survived.

**What this does not show yet.** This is one training seed in a nursery world (100 founding
pairs in the four corner cells), not the canonical 4-pair colony; whether a learned arm
preserves the calibrated curve is the calibration guard's question (H-d, 12 evaluation seeds),
which needs the nursery pre-training harness (P4-3) to produce weights for the 4-pair start.
The learner was never trained on, or shown, any detector output.

## 2026-11-06 — P4-2: homeostatic reward + PPO learner; a drive-reduction learner abandons its young

**Built.** `learn/reward.py` (Keramati & Gutkin drive reduction over the seven drives hunger,
thirst, fatigue, social_drive, curiosity, boredom, stress; N = 4, M = 2, setpoints 0; death
terminal at D − D_MAX; clipped to ±D_MAX; no drive-independent term, no bonus), `learn/ppo.py`
(shared actor-critic 48 → 128 → 128 → 11 and 48 → 128 → 128 → 1, PPO with clipping, GAE along each
slot's chain with per-transition discounts — decisions and sub-steps have different durations —
value normalisation, masked logits, determinism recipe), `learn/policy_ppo.py`
(`policy.kind: mlp_ppo`: one open transition per slot, closed at the agent's next call or as
terminal on death / rebirth; update every `rollout_ticks` decisions; exports the actor in the
`mlp_frozen` .npz layout), `PPOConfig`, `scripts/nursery_smoke.py`, `tests/test_learn.py`.
The reflex overrides (critical thirst, hunger, fatigue) are now also the only action the mask
allows on those rows, so a learner is never credited for an action physiology overrode
(bit-identical for the heuristic: hash `966401ea…`).

**Checks.** The reward is a function of the drives only (signature and values tested); GAE
matches a hand recursion with a terminal and a truncated chain; a 20-day learning run on the GPU
repeats bit for bit (actions, positions and final weights hashed); the exported actor gives the
same logits as `mlp_frozen`; `ppo.enabled: false` never updates; learner code passes the H2
identifier and import audits. Speed: 20 days with 80 agents and 12 sub-steps, 20 updates,
31,000 transitions in 10 s on the RTX 5080.

**Nursery smoke** (training seed 7000, 100 founding pairs, 12 sub-steps, 450 days;
`_output/nursery_smoke.json`):

| arm | mean D, last quarter | first quarter | N at day 450 | births | surviving births | learner transitions |
|---|---:|---:|---:|---:|---:|---:|
| learner (`mlp_ppo`) | **0.430** | 0.318 | **496** | 11,207 | **166** | 2.5 × 10^6 |
| same network, no updates | 1.036 | 0.969 | 2,060 | 14,905 | 1,903 | — |
| heuristic (continue) | 0.802 | 0.722 | 2,072 | 13,028 | 2,007 | — |

Per-drive means in the last quarter: the learner rests more (fatigue 0.30 vs 0.94 / 0.68) and
socialises more (social drive 0.64 vs 1.34 / 1.17), explores less (curiosity 0.45 vs 0.20 /
0.23), and its stress is low (0.15 vs 0.49 / 0.56) because its colony is small.

Acceptance as written: the learner's mean D is below the no-update baseline (**met**, by more
than half) but it reached 2.5 × 10^6 transitions, not 10^7 (**not met**), because its colony never
grew; and the D comparison is confounded by that demography.

**Why the colony stayed small: the learner abandons its young.** Conceptions and births are
normal (1,764 conceptions, 11,207 births); 1.5 % of pups survive to weaning against 13 % (no
updates) and 15 % (heuristic); abandonment is zero, so the pups starve. Measured directly with
the final weights frozen (days 110–160, same nursery):

| policy | nursing mothers within 8 in of their nest | median distance | NURSE / NEST share of their decisions | mean pup hunger | surviving births |
|---|---:|---:|---:|---:|---:|
| learned | **0.05** | 48 in | **0.00 / 0.00** | 0.71 | 31 of 2,008 |
| untrained network | 0.24 | 15 in | 0.05 / 0.05 | 0.39 | 330 of 1,955 |
| heuristic | 0.25 | 13 in | 0.09 / 0.04 | 0.42 | 520 of 1,966 |

None of the seven drives is relieved by nursing, so a pure drive-reduction learner has no reason
to stay at the nest and learns not to. The heuristic encodes maternal motivation in its
utilities (NURSE ∝ maternal investment, NEST raised for nursing females); the preregistered
reward does not. This is a result about the reward, not a bug: homeostatic self-maintenance
alone does not produce maternal care, and without it the calibrated colony cannot exist. It
must be fixed before any learned arm can be compared with the control (H-d would fail on
recruitment alone) and before the play question can be asked of a learner.

**Options (decision pending, `PHASE4_DESIGN.md` §1.4):**
1. *Maternal-motivation drive in the reward (recommended).* For a lactating female, a drive set
   by her own pre-weaning pups' hunger (dams respond to pup cues), relieved when the pups are fed.
   Physiology stays identical for every policy; only the learner's motivation changes, mirroring
   what the heuristic already encodes. Still drive-only and H2-clean. Amends the preregistered
   reward (seven → eight drives) before any learned arm is judged.
2. *Maternal reflex in physiology.* Lactating mothers whose pups are hungry are forced to nurse,
   like the thirst and hunger reflexes, for every policy. Maternal care is then not learned; the
   heuristic's calibrated infant mortality must be re-guarded.
3. *No change.* Report demographic collapse as the H-d result for drive-reduction learners and
   study play only in nursery worlds without reproduction.

## 2026-11-06 — H-d amendment adopted (Jason)

A canonical landmark now fails the calibration guard only if it drifts more than 10 % from the
control **and** the paired difference exceeds 2 paired se; the decline band is unchanged
(`calib/policy_guard.py` `SE_MULT`; the 10 %-only reading is kept as `verdict_10pct_rule` and
printed with every guard). Reason: the 12-seed paired se of N@315 is 12–16 % of its mean, so
the 10 % rule failed a distributionally identical arm at one se. Decided before any learned
arm was judged. Re-verdict of the stored runs (seeds 8000–8011, 1600 d):

| arm | amended rule | 10 % rule | deciding landmarks |
|---|---|---|---|
| random frozen MLP | NOT PRESERVED | NOT PRESERVED | N@315 7.1 se, peak 10.7 se, peak day 8.0 se, cessation 5.4 se |
| heuristic, 12 sub-steps, rechoose | NOT PRESERVED | NOT PRESERVED | decline band (0.342 < 0.35); N@315 +17 % at 1.1 se |
| heuristic, 12 sub-steps, continue | **PRESERVED** | NOT PRESERVED | N@315 +13 % at 1.1 se |

So the sub-step layer in continue mode leaves the calibrated curve intact; the random policy's
departure (the P4-1 result) is unaffected by the amendment.

## 2026-11-06 — P4-8: free-time sub-steps

**What it is.** `free_substeps: K` (config, CLI `--free-substeps`; 1 = off, bit-identical, 300-d
hash `966401ea…`). An agent whose decision action is EXPLORE / SOCIAL / MANIPULATE replays that
decision as K sub-steps: the decision-level move and curiosity / boredom / social relief are
undone, then each sub-step moves 1/K of a decision's reach (random walks with sd / √K) with 1/K of
the relief. The decision itself still executes in full first, so the biology's random stream is
consumed exactly as without sub-steps (tested); sub-step draws come from their own stream.
Feeding, nursing, conception, stress and mortality stay per decision, from wherever agents end.
`policy.substep_mode`: `continue` repeats the decision action at every sub-step (the same reach
and relief as the decision, in distribution — tested for EXPLORE: sd ratio within 0.8–1.2,
relief exact), `rechoose` lets the policy choose among the free actions at every sub-step;
`auto` = continue for `need_driven`, rechoose for learned kinds. The trace uses a uniform time
base of K rows per decision (non-free decisions interpolated along their move).

**Guard (12 evaluation seeds 8000–8011, 1600 d, vs the need-driven control without sub-steps):**

| arm (K = 12) | first litters | N @ 315 | peak N / day | cessation | N @ 736 | conceptions | N @ 1200 / band | N @ 1444 | N @ 1588 | H-d (10 % rule) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| control (no sub-steps) | 102.2 | 470 ± 43 | 2252 / 534 | 593 | 1956 | 935 | 839 / ok | 127 | 19 | — |
| heuristic, rechoose | 103.0 | 551 ± 42 (+17 %) | 2318 / 512 | 572 | 2000 | 900 | 793 / **0.342 < 0.35** | 108 | 15 | not preserved (N@315, band) |
| heuristic, **continue** | 102.4 | 531 ± 49 (+13 %) | 2241 / 541 | 597 | 1951 | 947 | 822 / ok | 128 | 23 | not preserved (N@315 only) |

- Re-choosing at every sub-step moved the arc earlier and steeper (peak day −22, cessation −21,
  conceptions −35 d; band missed by 0.008): mixing explore / social / manipulate inside a decision
  leaves manipulating agents short of their object and puts relief on other drives, so the colony
  spreads differently from the calibration. Recorded as a negative; the heuristic's motives exist
  only at the decision grain (its drives barely move within a decision), so `continue` is its
  faithful sub-step policy.
- Continue mode is within 2 % of the control on every landmark the guard can resolve. It still
  fails the preregistered 10 % rule on N@315 (+61 ± 57 paired, one se). That arm is the control's
  distribution by construction (only the random draws differ), and the 12-seed paired se of N@315
  is 12 % of its mean, so two equivalent realisations miss the 10 % rule about 40 % of the time:
  **the H-d rule cannot resolve 10 % on the early phase.** Verdict recorded as written; an
  amendment is proposed in `PLAN.md` §15.1 (pending Jason's approval, not applied).

**Detectors (v3, unchanged) on traced runs, K = 12, training seeds 7000–7002, 10-day windows at
days 150 / 400 / 700 / 1000, one individual in four, 1,000 surrogates
(`_output/p48_trace_summary.txt`):**
- Support now exists: from day 400 on, 253–8,309 direction pairs and 394–4,000 comparable
  episode pairs per window (at the decision grain: at most 21 and 2). Episodes last 2.3–11.3
  sub-steps; the gap criterion finds structure (3–10 sub-steps).
- Heuristic (continue), object episodes: stereotyped approach-and-stay — criterion 3 rejected
  (reversal 0.00), criterion 4 rejected (rigid 0.29–0.36 > 0.2). Locomotor episodes: a random walk
  (reversal 0.48, rigid 0.00), so criteria 3 and 4 pass from randomness, as for `random_walk` in
  the synthetic validation.
- Heuristic (rechoose) and the random frozen MLP: object episodes not rigid (0.04–0.06) but with
  no approach–withdraw (reversal ≤ 0.01: re-choosing ends an episode rather than withdrawing within
  it); locomotor as above.
- No arm prefers the relaxed field (criterion 5 met in 1 of 3 seeds in one window at most), so
  **no arm meets all five criteria in any window.** This is the profile a learned policy has to
  beat: approach–withdraw structure in object episodes (criterion 3) and relaxed-field dependence
  (criterion 5), against the random policy at the same sub-step grain.
- Known v3 limitation exposed by sub-steps: in continue mode criterion 2 reads "locked" for
  locomotor episodes. Density and wound triggers update once per decision, so they fall on
  decision-boundary rows, where continue-mode onsets also fall; the v3 circular-shift null shifts
  by arbitrary rows, not whole decisions. A phase-preserving null (shift by multiples of K) and a
  minimum support for the serious template are the v4 changes (card P4-9; fresh synthetic split
  required, never tuned on simulator output).

## 2026-11-06 — P4-5: Burghardt detectors, synthetic validation, decision traces

**Confound found and fixed first (affects P4-1).** The observation builder (P4-0) filled the
simulator's per-tick cell-count cache before the actions ran. The biology reads that cache after
the actions (nursing disturbance, conception density), so under learned policies it got
pre-move counts while the heuristic did not: the biology rules were not identical across guard
arms. The builder now keeps its own count. The 12-seed 1600-d guard was rerun: every landmark
moved by less than its se (peak 1995 → 1993, peak day 776 → 772, cessation 1154 → 1101, N@1588
383 → 357) and the verdict is unchanged — NOT PRESERVED, same four failures. Both versions are in
`_output/` (`policy_guard_mlp_random*.json`).

**What was built** (all eval-only; nothing here is imported by a policy, observation builder or
learner — audited):
- `metrics/trace.py`: per-agent decision traces in day windows (`trace.windows`, CLI
  `--trace-windows 150:170,400:420`). Off by default: no recorder, bit-identical tick (300-d
  hash `966401ea…` unchanged). When on it draws no random numbers, writes no simulation state,
  keeps its own cell counts, and a traced run is identical to an untraced one (tested).
- `metrics/detectors.py`: episode segmentation and the five criterion detectors with surrogate
  nulls and effect-size floors (rules in `docs/PHASE4_DESIGN.md` §2). Output is a vector of
  `*_unvalidated` statistics and per-criterion flags, never a single score.
- `metrics/synthetic_traces.py`: seven scripted classes written from the criterion text (no
  dataset, H1): `all_criteria` (built to meet all five) and one class built to violate each
  criterion (`serious`, `triggered`, `rigid_loop`, `novelty`, `stressed`), plus a matched-speed
  `random_walk`.
- `scripts/validate_detectors.py`, `scripts/detect.py`; `tests/test_detectors.py`.
- `free_choice_V_excl_hopper_unvalidated` in the metrics parquet.

**Validation history (each version tested on seeds never used before; rules fixed before each
test run, all recorded in the design doc).**

| Rules | Test seeds | Checks passed | What failed and why |
|---|---|---:|---|
| v1 | 10,000 + … | 11 / 12 | criterion 3 on object episodes (AUC 0.58, FPR 0.77 on `serious`): the gap criterion merged single consumption acts a day apart, and the trips between them read as approach–withdraw cycles |
| v2: form statistics use only the episode's own decisions | 20,000 + … | 12 / 12 | the episode falsifier failed afterwards in a unit test: least squares on the log-survivorship found a "break" in purely memoryless events (sparse tail points weighted like dense ones) |
| **v3**: gap criterion = maximum-likelihood one- vs two-process fit (Sibly, Nott & Fletcher 1990), criterion minimising misassigned gaps (Slater & Lester 1982) | 30,000 + … | **12 / 12** | — (memoryless events at rates 0.05–0.5: no structure; planted bouts: criterion 2) |

v3, 30 colonies per class, 1,000 surrogates per statistic, both episode kinds: AUC 0.993–1.000,
TPR 1.00, FPR 0.00 on every check. Every violating class fails exactly its criterion; the
`random_walk` passes criteria 1–3 and fails 5 (and 4 in 57 % of colonies), which is why every
reading must be set against the random baseline. **Limit, stated plainly:** the synthetic classes
and the detectors come from the same hand, so this shows the detectors compute what the
criteria say on behaviour built to the criteria; it does not show they would recognise real
play, and the thresholds are conventions, not estimates.

**First reading on the simulator** (training seeds 7000–7002, 1020 d, windows at days 150, 400,
700, 1000 of 20 d, 400 individuals per window, 1,000 surrogates; `_output/p45_trace_summary.txt`):

| arm | episodes per window | c1 not functional | c2 spontaneous | c3 / c4 | c5 relaxed field |
|---|---:|---|---|---|---|
| need-driven, playground on | object 63–1104, locomotor 78–1489 | met (nf 0.69–0.91) | met (not trigger-locked) | **not evaluable** | not met (log ratio −1.1 to +0.5 < ln 2) |
| random frozen MLP | object 42–930, locomotor 41–1227 | met | met | **not evaluable** | not met (−1.2 to +0.1) |
| need-driven, playground off | object 0, locomotor 216–2006 | locomotor met | locomotor met | not evaluable | not met |

- Episodes last one decision (mean 1.00–1.04 events; the gap criterion finds no structure), so a
  20-day window has only 12–21 direction pairs for criterion 3 and at most 2 comparable episode
  pairs for criterion 4. Those flags read False for lack of structure, not because a structure
  was found and rejected; the serious template's reversal fraction rests on a single pair.
- Drive spillover is not called play: the heuristic's object use is non-functional and
  spontaneous but unstructured and not relaxed-field gated beyond chance-level ratios.
- The differential prediction holds: with the playground off, object episodes vanish and
  locomotor episodes persist (more of them).
- The old free-choice V counted hopper users: day 150 V 0.132 → 0.048 without them, day 400
  0.234 → 0.116 (about half of the "free choice" was eating or drinking inside the box).

**Consequence for phase 4.** At 6 decisions per day (one every 4 hours) no policy, learned or
not, can show within-episode form: mouse play bouts last seconds to minutes. Criteria 3 and 4 —
the preregistered non-trivial tests (H-f) — need a finer decision grain for free-time behaviour.
New card P4-8. The detectors are ready; the substrate's time grain is now the binding constraint.

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

**P4-1 done (2026-11-04) — first phase 4 measurement: the curve is not policy-invariant.**
`calib/policy_guard.py`, `scripts/policy_guard.py`, `tests/test_policy_calibration_guard.py`
(verdict rule, control-vs-control zero drift, a random arm end to end). Guard run: the 12
evaluation seeds 8000–8011 (first use), 1600 d, 6 ticks/day, need-driven control vs one fixed
random frozen MLP (`_output/policy_random_7000.npz`: orthogonal init, last-layer gain 0.01, i.e.
near-uniform over the eligible actions, with the same masks and reflexes as the heuristic).
`_output/policy_guard_mlp_random.json`; mean ± se, paired = arm − control on the same seed:

| landmark | Calhoun | need_driven (control) | random MLP | drift | paired diff |
|---|---:|---:|---:|---:|---:|
| First litters | 104 | 102.2 ± 0.2 | 102.8 ± 0.3 | 0.006 | +0.6 ± 0.4 |
| N @ 315 | 620 | 470 ± 43 | 181 ± 36 | **0.61** | −289 ± 41 |
| Peak N | 2200 | 2252 ± 13 | 1995 ± 23 | **0.11** | −257 ± 27 |
| Peak day | 560 | 534 ± 7 | 776 ± 27 | **0.45** | +242 ± 31 |
| Surviving births cease | 600 | 593 ± 8 | 1154 ± 107 | **0.95** | +561 ± 108 |
| N @ 736 | 2056 | 1956 ± 11 | 1791 ± 74 | 0.08 | −165 ± 71 |
| Conception cessation | ≈920 | 935 ± 8 | 1349 ± 59 | 0.44 | +414 ± 62 |
| N @ 1200 | (0.35–0.85 × peak) | 839 ± 20 | 1272 ± 54 | 0.52 | +433 ± 56 |
| N @ 1444 | 122 | 127 ± 8 | 608 ± 74 | 3.8 | +481 ± 77 |
| N @ 1588 | 27 | 19 ± 2 | 383 ± 93 | 19 | +364 ± 93 |

H-d verdict for the random policy: **NOT PRESERVED** (N@315, peak N, peak day, cessation fail
the 10 % rule; the decline band at 1200 holds). Reading:
- The frozen 2m calibration, on evaluation seeds it had never seen, reproduces the record:
  peak 2252 ± 13 at 534 ± 7, cessation 593 ± 8, N@736 1956 ± 11, conceptions 935 ± 8, N@1444
  127 ± 8 (122), N@1588 19 ± 2 (27). The early phase stays low (470 ± 43 vs 620; see P0-5).
- A policy that chooses uniformly among the eligible actions gives a slower, weaker and far
  more persistent colony: phase B at half the rate (random mothers leave the nest, pups starve
  more), a peak 11 % lower and 240 d later, surviving births for ≈ 560 d longer, conceptions
  ≈ 410 d longer, and five to twenty times the control's late tail. The behavioural sink needs
  the heuristic's attraction to hoppers, nests and partners; spread uniformly, the colony never
  concentrates enough for the breakdown to run its course.
- Consequence: "calibrated biology" is really calibrated biology **plus heuristic behaviour**.
  H-d is falsified for an arbitrary policy, which is the baseline that bounds what a learned
  drive-reduction policy may do; whether such a policy lands near the heuristic or near random
  is the open question P4-2 / P4-3 answer, and every policy arm reports this guard before any
  abundance-vs-scarcity comparison is read. The biology is not retuned (frozen at 2m).

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