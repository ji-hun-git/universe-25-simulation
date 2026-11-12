# Replica v2 — Calhoun's system, not only his curve

Jason's decision (2026-11-11), after P4-15's stop rule: rebuild the colony as a faithful replica
before any further play hypothesis. This is Tier 3 of `docs/REVIEW_2026-11-09.md`.

It **reopens the frozen calibration**. The frozen 2m colony (`configs/default.yaml`) stays
untouched, bit-identical and the reference for every earlier result. Replica v2 is a scenario of
its own (`configs/replica_v2.yaml`): every new mechanism sits behind a config field whose
default reproduces the 2m colony, and the golden trajectory hashes guard that.

## Sources and what they fix

Calhoun 1973 (*Proc R Soc Med* 66: 80–88; scan decoded page by page), Calhoun 1971 (*Space and
the Strategy of Life*), Marsden 1972. Their numbers are in `docs/RESEARCH_DIGEST.md` part A, and
the apparatus detail comes from the 2026-11-11 extraction (NOTES).

**Pen.**
- 101 × 101 in square, walls 54 in. The top 17 in of the walls is bare metal; the 37 in below is
  climbable mesh.
- **16 cells tile the whole floor as triangles.** Each has a 25¼-in base on the wall and its apex
  at the pen centre, 638 sq in each (the record's "640 sq in"). Four triangles sit on each wall.
- Low partitions mark the cells. Mice step over them, and they serve as territory boundaries.
- The apexes meet at the centre, where the withdrawn mice pooled.

**Per cell.**
- **Tunnels.** Four vertical mesh tunnels, 3 in across and 34 in tall, with their open bottom
  just above the bedding.
- **Boxes.** Each tunnel leads to four 8 × 5 × 4 in boxes at 8-in intervals, so four levels at
  about 8 / 16 / 24 / 32 in. That gives 16 boxes per cell, 256 in all, 15 mice each, 3,840
  shelter capacity.
  - Upper boxes cost more effort per trip; withdrawn females used them.
  - About 20 % of boxes were usually empty at the peak of 2,200.
- **Hopper.** One wire-mesh hopper, 6 × 10 in, halfway up the wall and touching the right-hand
  tunnel; 25 feed at once. Along each wall the sequence is hopper, four tunnels, hopper, four
  tunnels.
  - Food limit 9,500 mice (design).
  - Aggregation was learned: eating side by side made mice converge on some hoppers.
- **Water.** A platform above the tunnels with four bottles, 8 drinking at once; the design
  supports 6,144 mice. The sources conflict (1971: four bottles; Marsden: two spigots), and the
  1973 version is used.
- **Ring stand.** A metal ring stand in the middle of the cell floor: a refuge, with nesting
  material on top. In phase C, territories shrank to within 12 in of the ring-stand bases.

**Protocol.**
- 4 pairs of BALB/c mice, 48 days old, introduced on 9 July 1968 (day 0). Where they were placed
  is not recorded.
- 2 of the 4 founding males died of fighting stress within two months.
- **Reconfiguration in December 1968 (days 145–175).** Before it, each box had its own food and
  water, so eating, drinking and resting happened in the boxes. After it, food and water moved
  to the wall hoppers and platforms.
- About 150 mice were removed after day 1,000.

**What the record does not give,** so the model assumes it and says so:
- founder placement;
- hopper and platform heights;
- ring-stand positions;
- partition heights.

## Milestones

Each milestone lands behind config fields, with unit tests and unchanged golden hashes for the
frozen colony. Each one ends with an uncalibrated run of the replica that shows what it changed.

**M1 — the pen.** Geometry only; the biology parameters stay frozen.
- *Cells:* the 16 triangular cells (`geometry.layout: calhoun`). A point belongs to the
  triangle whose wall segment the ray from the centre crosses.
- *Boxes:* four tunnels per cell along its wall segment, four box levels per tunnel (`Nest.level`
  0–3). A box's floor position is its tunnel base.
- *Food and water:* the hopper at the right-hand end of the segment and the water platform above
  the tunnels. Capacity per day is the record's design limits (9,500 / 16 hopper meals, 6,144 / 16
  drinks, per cell), split over the decisions; neither binds at 2,200 in the frozen biology.
- *Ring stand:* at the triangle's centroid (no mechanism yet).
- *Withdrawal:* withdrawn mice drift to the pen centre, not to (20, 20), a leftover of the grid.
- *Reconfiguration:* until `geometry.box_feeding_until_day` (about 160), animals eat and drink
  at their own box.
- *Founders:* one pair per wall, in the second cell of each wall (assumption, recorded).
- *Plumbing:* one position-to-cell function (`World.cells_of`) serves the simulator, the trace
  and the observation, with the old grid arithmetic kept exactly for `layout: grid`. The Warp
  backend is refused for `layout: calhoun`.
- *Report:* the frozen biology in this pen, with the playground off, against the record.
- **Done 2026-11-11** (24afb76; NOTES):
  - In this pen the frozen biology runs the arc about 190 days early (N@315 1,821, peak day 372,
    doubling time 35 d).
  - Nobody reaches the centre, every box is occupied at the peak, and the sex ratio is 50 : 50.

**M2 — life history and an emergent phase A.**
- 48-day founders and no calendar gate (`first_conception_min_day` 0). Litter size about 5.5
  (BALB/c 5–6). Phase-B weaning survival high.
- Phase A comes out of the founders establishing themselves: male–male fighting until
  territories settle, and conception needing a settled territorial male.
- *Targets:* first surviving litters at 50–65 d (60 ± 15); 620 at day 315 (150 adults + 470
  young); the doubling time changes from about 55 d to about 145 d at day 315.

**M2 specification (fixed 2026-11-11 before code; parameters set a priori, not fitted).**
- *Founders* (`biology.founder_age_days`): 48 days old (Calhoun 1973 p. 82). Unset means the
  frozen colony's uniform 60–90.
- *No calendar gate:* `first_conception_min_day` 0.
- *Litters:* `litter_mean` 5.5 (BALB/c 5–6).
- *Territories* (`biology.territories`, default off).
  - **Owners.** A cell can have one owner, an adult male. Each male owns at most one cell.
  - **Claiming.** In a daily pass, the top-ranked adult, non-withdrawn male present in an
    unowned cell claims it. He becomes its owner after `territory_settle_days` (14) daily
    passes as its top male. A different top male restarts the claim.
  - **Contests.** When the owner is present and another adult male present has a rank within
    `territory_gap` (0.15) of his, they hold one contest a day, drawn from the simulation
    stream. P(the owner wins) = 0.5 + (r_owner − r_challenger) / (2 × gap), clipped to
    [0.05, 0.95].
    - The loser loses 0.10 rank and gains 0.15 wounds and 0.10 stress, as a lost fight in
      `_aggress`.
    - The winner gains 0.05 rank.
    - A winning challenger takes the cell.
  - **Ownership lapses** when the owner dies, withdraws or is defeated. It does not lapse while
    he is away.
  - **Conception** needs the female's cell to have an owner, and uses the owner's competence ×
    courtship capacity: the owner sires. This replaces "any male in the cell, cell mean".
  - **Why:** phase A then comes from the founders settling territories instead of a date. Role
    saturation follows when maturing males outnumber the 16 territories, and brood groups are
    the owners' cells (Calhoun's basic group: one territorial male per territory).
- *Bookkeeping:* every pup's brood group is the owner who sired it (a spawn serial number per
  animal).
- *Report* (training seeds 7000–7011, 1,600 d): M1 vs M2.
  - The landmarks.
  - The first-litter day; Calhoun 1971 gives first surviving litters at 50 d, and figures imply
    60–65.
  - Owned cells at day 315.
  - Young per brood group born by day 338 (Calhoun: 842 young in 14 groups, 111 … 13).
  - Founder-male deaths within 60 d (Calhoun: 2 of 4).
- *M2 targets* (reported, not fitted; calibration is M5):
  - first litters 40–80 d with no gate;
  - 10–16 brood groups by day 315 with a skewed distribution;
  - N@315 and the doubling times reported against 620 / 55 d / 145 d.
- *Implementation clarifications* (decided in code, before any multi-seed run; no rule or
  parameter changed after the one-seed sanity run):
  - A challenge needs r_challenger ≥ r_owner − gap, so a higher-ranked male always contests,
    at P(the owner wins) 0.05 when far above. The spec's "within the gap" left that case open.
  - Owners of other cells neither claim nor challenge.
  - The challenger is the top-ranked eligible non-owner present.
  - Cells are visited in id order.
  - With no eligible male present, a claim holds.
  - The owner sires only if he passes the old male filter that day: adult, not withdrawn,
    stress < 0.85.
  - Roles are unchanged: `ROLE_TERRITORIAL_MALE` is still rank > 0.55, and owners' behaviour
    is M3.
  - The M1 comparison arm is `replica_v2.yaml` with the four M2 fields reset. It reproduces the
    M1 golden hash exactly.
- **Done 2026-11-11** (NOTES; 12 training seeds):
  - First litters at day 49 with no gate: target met.
  - N@315 1,559 (record 620) and phase-B doubling 39 d (55): missed.
  - Brood groups by day 315: 22 against 10–16, missed, though skewed as targeted.
  - Only about 7.5 cells are ever owned; 0 of 4 founding males die (record 2 of 4).
  - Phase A is the sum of maturity, settling and gestation, not founder fighting: the founders
    start in separate cells.

**M3 — the social system.**
- *Territories:* M2 added ownership (a holder per cell, contested by maturing males, who sires).
  M3 adds the behaviour:
  - site fidelity and defence by owners (in M2, only about 7.5 cells settle);
  - the owner as the territorial role;
  - role saturation (more young adults than roles).
- *Hoppers:* aggregation emerges from social facilitation at feeding.
- *Boxes:* physical box occupancy, with a choice among free boxes and the effort of upper levels.
- *Targets:* about 14 brood groups by day 315 with a skewed young-per-group distribution (Fig 3:
  111 … 13); territories shrinking towards the ring stands in phase C; about 20 % of boxes empty
  at the peak.

**M3 specification (fixed 2026-11-11 before code; no fitted parameter).** Four mechanisms, each
behind its own field (default off = M2 unchanged).
- **Fidelity** (`biology.territory_fidelity`). A male who owns or claims the cell he is in does
  not leave it: after each decision's moves, his position is restored if he left that cell.
  - On taking ownership, his box becomes the one in his cell with the fewest living occupants
    (ties: lower level, then lower id).
  - `ROLE_TERRITORIAL_MALE` then means an owner, and every other adult, non-withdrawn male is
    subordinate. Roles do not enter the dynamics; this fixes the label.
  - Sub-steps are refused with it.
- **Defence** (`biology.territory_tolerance`: 3, Calhoun's basic group of 1 territorial male +
  3 subordinate males + 6 females; unset = off).
  - Territories exclude the central disc: points within 12 in of the pen centre
    (`territory_centre_in`; 12 in is our centre measure; the record gives no radius). The
    territory pass ignores males inside the disc, so they neither claim nor challenge.
  - At each decision, an owner in his territory tolerates the `territory_tolerance`
    lowest-ranked adult, non-withdrawn males there (ties: lower slot).
  - Every other such male is displaced along his ray from the centre to 10 in from it, into the
    no-man's land where the territories' apexes meet. Calhoun: excluded and withdrawn males
    pooled in the floor centre. Nobody loses his box.
- **Box choice** (`geometry.box_choice`). Two box assignments of the frozen colony change:
  - the homeless rule, which took the nearest box;
  - the destination of the overcrowding kick, which was a uniformly random box anywhere in the
    pen.

  An animal needing a box takes, in its current cell, the box below capacity (15 living
  occupants) with the most occupants: aggregation, as in Calhoun's crowded boxes. Ties go to
  the lower level (the effort of climbing), then the lower id. If every box of its cell is at
  capacity, it takes the one with the fewest occupants. The kick keeps its draw; the
  destination draw is no longer made.
- **Hopper facilitation** (`geometry.hopper_facilitation`, Calhoun layout only). After the
  reconfiguration day, a forager heads for the hopper with the most foragers at the previous
  decision. The choice is among its own cell's hopper and its two neighbours' along the wall
  (ties: its own, then the lower id). An owner or claimant under fidelity uses his own. This is
  social facilitation, which Calhoun's mesh hoppers were designed to permit.
- *Report* (training seeds 7000–7011, 1,600 d), with cumulative arms: M2, + fidelity,
  + defence, + box choice, + facilitation (= M3). Reported:
  - the landmarks;
  - owned cells;
  - brood groups by day 315 and by day 338;
  - subordinate males per owner;
  - the share of weaned, withdrawn and excluded (adult, non-withdrawn, non-owner) males within
    12 in of the centre;
  - empty boxes at days 315 / 560 / 736;
  - the largest hopper's share of the current foragers;
  - owners' mean distance from their ring stand at days 315 and 560.
- *M3 targets* (reported, not fitted; calibration is M5):
  - 10–16 brood groups by day 315, skewed (M2 missed with 22);
  - at least 10 owned cells at day 315 (territories ≈ 1.5 cells, 14 groups);
  - 20–30 % of boxes empty at day 560 (1973: 20 %; 1971: 30 % empty or with 1–2 mice);
  - withdrawn mice within 12 in of the centre at more than twice the disc's area share
    (> 0.09), against 0 in M1 and M2;
  - the largest hopper with at least twice a uniform share of foragers (> 0.125) after day 175.
- *Reported, no target:*
  - territory shrinkage towards the ring stands in phase C (no mechanism is designed for it);
  - N@315 and the doubling times;
  - the sex ratio.
- **Done 2026-11-11** (NOTES; 12 training seeds).
  - Targets met: all 16 cells owned; hopper aggregation (busiest cell 0.25 of foragers).
  - Targets missed:
    - brood groups by day 315: 24 against 10–16, with fast owner turnover;
    - empty boxes at the peak: 0.60 against 0.20–0.30;
    - withdrawn mice at the centre: 0.00. The excluded males pool there instead (0.59).
  - **With facilitation the colony never collapses.** It holds at about 1,200 until day 1,600,
    conceiving to the end.
    - The cause is pup loss in the aggregated cells, through the frozen nursing disturbance.
      Hopper capacity is not involved.
    - That loss keeps the colony below the colony-wide density that switches on the frozen
      breakdown.
    - So the frozen collapse needs a fixed colony-wide density, which is M4's to replace.

**M4 — breakdown and the behavioural categories.**
- *Mothers:* maternal aggression and eviction of the young before weaning, mid-phase C (about
  day 437).
- *Males:* withdrawn males (pooled at the centre, wounded by other withdrawn males) are split
  from "beautiful ones" (unwounded, never fought, mated or nest-built).
- *Mortality:* sex-biased through wounding, giving the late female bias (22 M : 100 F at 1,444;
  4 M : 23 F at 1,588).
- *Development:* driven by the care each animal received (nursing deficit, early eviction), not
  by a colony-wide count.
- *Targets:*
  - 53 % of mice entering adulthood in mid-phase D never fought, mated or nest-built;
  - withdrawn mice are 32 % of a cell's 142 at the end of phase C;
  - sex ratio 40 : 60 in phase B.
- *Recovery tests:* the Marsden transfers, and the Kessler and Hammock recoveries, measure what
  the irreversibility assumption costs.

**M4 specification (fixed 2026-11-11 before code; a priori values, not fitted).** M3 showed
that the frozen collapse is switched by colony-wide weaned density: a colony held below it
never collapses. M4 removes every colony-wide term and lets breakdown come from each animal's
experience. Each mechanism sits behind its own field; the default is M3.
- **Individual breakdown** (`biology.breakdown_scope: individual`). This removes the frozen
  biology's three colony-wide terms:
  - the breakdown stress boost (the weaned-density switch);
  - the colony-wide developmental exposure;
  - the conception suppression by colony density (N / design capacity).

  What remains is individual: stress from the animal's cell density, its box, its fights and
  its displacements; development from its local exposure and the care it received (below).
- **Development from care** (`biology.care_imprint_gain`, a priori 1.0, the weight the
  colony-wide exposure had). A pup loses competence at `imprint_rate` × gain × its care deficit
  per day, on top of its local exposure. The deficit is max(0, hunger − 0.5) while it has a
  box, and 1 while it has none (abandoned or evicted). Calhoun: mothers rejected their young
  prematurely in mid-phase C, and young reared so never acquired adult behaviour.
- **Exclusion stress** (`biology.exclusion_stress`, a priori 0.05, half a lost fight). Every
  displacement by a territory owner adds it to the displaced male. Withdrawal can then come from
  role saturation.
- **Aggression by sex** (`biology.aggression_targets: by_sex`; the frozen rule is `any`).
  - A male attacks only lower-ranked males within 6 in.
  - A female attacks only while nursing, and then any lower-ranked animal within 6 in
    (maternal aggression, which in phase C reached her own young).
  - The draw is unchanged. Without a target there is no fight.

  With this, wounds and wound mortality fall mostly on males (record: 22 M : 100 F at day
  1,444).
- **Wound mortality** (`biology.wound_mortality_scale`): the frozen hard-coded 0.02 per wound²
  per day, now a field for M5. M4 keeps 0.02.
- **Pens of fewer cells** (`geometry.open_cells`, calhoun layout). Only the listed cells exist:
  - a move ending in a closed cell is undone;
  - founders go to open cells;
  - facilitation considers open neighbours only.

  It serves the Marsden transfers below and M6's sibling universes.
- **Categories** (bookkeeping only). Per animal: *fought* (either side of a fight or a contest),
  *mated* (conceived or sired) and *littered*. For our purposes a "beautiful one" is an adult who
  never fought or mated. Nest building is read as littering, which implies mating.
- **Marsden transfer** (`scripts/replica_transfer.py`).
  - At day 870 (Marsden's "at this writing"), 16 females and 8 males (adults, chosen at random)
    move with their traits (age, rank, wounds, competence, maternal and courtship capacity) into
    a fresh 4-cell pen. Stress starts at the spawn value, and there is no box-feeding period.
  - The pen runs 60 days. The second arm replaces the 8 males with 8 fresh stock males
    (100 days old, full competence).
  - Measured: conceptions, litters, and pups alive at 14 days.
  - Record: no sex, pregnancy or pups with the colony males. With competent stock males, 6 of 16
    females conceived, 3 littered, and 5 pups of about 100 potential survived to day 14.
- *Report* (training seeds 7000–7011, 1,600 d). The arms are cumulative: M3, + individual
  breakdown and development from care, + exclusion stress, + aggression by sex (= M4). The
  transfer runs on the M4 arm.
- *M4 targets* (reported, not fitted; calibration is M5):
  - Whether reproduction still ends without any colony-wide term: last conception, N@1,444 and
    N@1,588. No target; the uncalibrated values will move.
  - Share of 131–320-day-olds at day 800 who never fought or mated: 0.53 (± 0.15).
  - Withdrawn share of the weaned at day 560: 0.32 (± 0.10).
  - Withdrawn within 12 in of the centre: > 0.09.
  - Male share of the weaned: 0.40 at day 315 (± 0.05), and below 0.5 at day 1,444 (record
    0.18).
  - Marsden transfer: 0 conceptions with the colony's males, and more with stock males.
- The Kessler and Hammock recoveries are not modelled: only abstracts were reachable.
- **Amendment (2026-11-11, after a one-seed diagnostic and before any multi-seed run).**
  - *The diagnostic:* in the M4 colony at day 260, overfull boxes give 92 % of the young's
    developmental exposure. One box holds 160 mice (capacity 15), and 81 % of boxes are empty.
  - *The cause is structural:* animals keep their natal box for life. The only way out is the
    overcrowding kick, which needs rank < 0.4, and pups are born at rank 0.4–0.8.
  - *The fix:* `geometry.disperse_at_maturity`. An animal reaching maturity leaves its natal
    box and takes one by the box-choice rule. It is a priori: mice disperse at maturity, and
    Calhoun's boxes held 15.
  - *Effect on that seed:* exposure falls by about 3.7×, and the fullest box holds 50.
  - The report adds dispersal as a fifth cumulative arm (= M4 amended), so both versions are
    visible.
- **Done 2026-11-11** (NOTES; 12 training seeds).
  - **Without colony-wide terms the colony never collapses,** unless natal boxes are kept for
    life.
    - M4 as specified ends reproduction at day 814 (record 920), with N@1,444 140 and N@1,588
      56: inside the record's range. It gets there through overfull natal boxes plus male
      depletion by male–male wounding.
    - With natal dispersal it holds at about 1,100 to day 1,600.
  - **The peak is about 1,100–1,400 in every arm** (record 2,200).
  - **Targets met:** female bias late (male share 0.23 at day 1,444); no conceptions after
    transfer with the colony males.
  - **Targets missed:**
    - never fought or mated (0.16 vs 0.53);
    - withdrawn share (0.81 vs 0.32);
    - withdrawn at the centre (0);
    - male share in phase B (0.46 vs 0.40);
    - the stock-male transfer: the transferred females are as incompetent as the males.

**M5 — landmarks and recalibration.**
- *Expanded landmark set:*
  - plateau onset as the peak day;
  - both doubling times;
  - the counts 1,871 at day 811, 1,650 at 960 and 100 at 1,471;
  - sex ratios;
  - box vacancy;
  - the removal event;
  - the brood-group slope.
- *Methods fixes behind flags:* the post-move cell-count cache and synchronous fights.
- *Recalibration:* history matching. The search set comes from Morris screening (influential
  parameters, hand-set ones included). Gaussian-process emulators, an implausibility cut using
  the record's own uncertainty, and an ensemble of the parameter sets not ruled out, instead of
  one point.
- Jason decides whether the ensemble replaces 2m as the reference for new work.

**M5 specification (fixed 2026-11-11 before any wave).** Calibrate the whole replica (M1–M4
amended) to the record by history matching (`scripts/history_match.py`, emulator
`universe25.calib.emulator`).
- **Configuration** (`configs/replica_v2.yaml`): M4 amended plus
  - the removal event: 150 adults on day 1,014. The record's counts at days 1,444 and 1,588 come
    after about 150 removals.
  - both methods fixes from the review (`fresh_cell_counts`, `synchronous_fights`).
- **Parameters** (20, on boxes; log-uniform where marked):
  - reproduction: `breeding_p_base` 0.2–0.95, `litter_mean` 4.5–7.5, `maturity_days` 42–70;
  - development: `imprint_rate` 0.003–0.1 (log), `imprint_density_threshold` 0.05–0.6,
    `care_imprint_gain` 0–3, `withdrawn_competence_threshold` 0.1–0.6;
  - stress: `stress_density_gain` 0.15–1.2, `stress_decay` 0.5–1.5, `nest_overcrowd_stress`
    0–0.5, `exclusion_stress` 0–0.15;
  - adult breakdown: `maternal_erosion_stress` 0.25–0.8, `courtship_erosion_stress` 0.25–0.8;
  - maternal care: `litter_abandon_p` 0–0.6, `maternal_neglect_stress` 0.3–0.9,
    `nurse_disturb_coef` 0–8;
  - mortality: `wound_mortality_scale` 0.005–0.3 (log), `base_mortality_per_day` 5e-5–1.5e-3
    (log), `young_mortality_scale` 0.1–1, `stress_mortality_scale` 2e-4–0.02 (log).

  The set holds the Morris-influential biology parameters plus the new M2–M4 ones. Everything
  else stays at its M4 value.
- **Targets.** Each is a record value z with an observation sd and a model-discrepancy sd.
  Counts are compared as log(N + 10), and doubling times as logs.

  | target | z | obs sd | discrepancy sd |
  |---|---|---|---|
  | first litters | 77 | 13.5 | — |
  | N@315 | 620 | 5 % | 10 % |
  | adults @315 | 150 | 15 | 30 |
  | peak N | 2,200 | 5 % | 10 % |
  | plateau onset (first day at 97 % of the peak; the review's peak-day fix) | 560 | 20 | 30 |
  | N@736 / N@811 / N@960 | 2,056 / 1,871 / 1,650 | 5 % | 10 % |
  | last surviving birth | 600 | 15 | 30 |
  | last conception | 920 | 20 | 40 |
  | N@1,444 | 122 | 12 | 40 |
  | N@1,588 | 27 | 5 | 15 |
  | phase-B doubling | 55 | 5 | 8 |
  | phase-C doubling (day 315 to plateau onset) | 125 | 10 | 15 |
  | male share @315 | 0.40 | 0.03 | 0.05 |
  | male share @1,444 | 0.18 | 0.03 | 0.06 |
  | empty boxes @560 | 0.25 | 0.05 | 0.05 |
  | withdrawn share @560 | 0.32 | 0.05 | 0.10 |
  | never fought or mated, 131–320 d, @800 | 0.53 | 0.05 | 0.10 |
  | brood groups by day 315 | 14 | 1 | 3 |

  First litters (record 50–104) and phase-C doubling (105–145) are contested, so z is the
  middle of each range. An undefined doubling time (no growth) scores as 2,000 d.
- **Emulators and implausibility.**
  - One GP per target: constant mean, ARD squared-exponential kernel, nugget for seed noise,
    maximum marginal likelihood. It is refitted on every run so far.
  - I_i(x) = |z_i − E f_i(x)| / √(obs² + discrepancy² + emulator variance + seed noise).
  - NROY = {x : the second-largest I_i ≤ 3}, so one target may miss.
- **Waves** (training seeds 7000–7011 in turn, 1,600 d, one seed per point):
  - wave 1: a 200-point Latin hypercube;
  - waves 2 and 3: 120 points each, drawn uniformly from the current NROY.

  Emulator leave-one-out checks are reported each wave.
- **Ensemble.** After wave 3, 24 NROY points × 2 training seeds. The best simulated runs are
  reported with their implausibilities, ranked by I_max.
- **Stop rule.** If no NROY point exists after a wave (none among 1.2 M candidates), the waves
  stop. The result is then that the replica, with these mechanisms and these ranges, cannot
  match the record. The report lists the targets that conflict: the smallest achievable
  implausibility per target, alone and jointly.
- **Validation** is M6, on fresh seeds. Jason decides whether the ensemble becomes the
  reference for new work.
- **Done 2026-11-11** (NOTES; 488 runs, 10.3 CPU-hours).
  - **No simulated parameter set passes.**
    - NROY shrank from 0.51 % of the box to 0.003 % over the waves.
    - The best simulated run has I₂ 3.19. The best ensemble member has I₂ 3.95 on its seed
      mean.
    - `configs/replica_v2_ensemble.json` holds the 12 best members as a fallback, marked as
      such.
  - **The conflict is growth versus collapse.** 97 runs peak above 1,800 and 76 collapse
    (below 300 at day 1,588), but none does both. The largest peak among collapsing runs is
    1,749.
  - **The best region is bistable:** the seed decides whether the colony collapses or
    plateaus.
  - **What it means:** with breakdown driven only by individual experience, the model cannot
    produce Calhoun's arc. Either a delayed or cumulative (multi-generational) mechanism is
    missing, or the record is one draw from a bistable system.

**M6 — out-of-sample validation.**
- The sibling universes of Calhoun 1971 (1, 2, 4 and 8 cells; Fig 3) were never fitted. They are
  the cleanest out-of-sample test: the same biology in smaller pens.
- Then the guard v2 / predictive-check protocol against the record on fresh seeds.
- **Done 2026-11-11** (NOTES; `scripts/replica_validate.py`; fresh seeds 9200–9307).
  - **Calhoun's pen:** the record lies inside the 5–95 % range for 11 of 20 targets, several of
    them only because the ensemble is bistable. Peak N, N@736–960, brood groups, empty boxes,
    never fought or mated, and the late sex ratio are outside.
  - **Sibling universes:** the 1-cell universe matches. The replica's plateau per cell falls
    with pen size (171 → 69), while the record's stays at 130–180.
    - A post-hoc diagnostic traces this to hopper facilitation (M3): an 8-cell pen holds 81 per
      cell with it and 185 without.
  - **Marsden transfer** (best member): the pattern matches the record (colony males sire
    nothing, and stock males rescue the females), but the rescue is too strong.
  - **Not met: the validation standard.** The open questions are in NOTES ("Replica v2 — state
    at the end of M1–M6").

**M5b — recalibration without hopper facilitation (Jason, 2026-11-12: "Yes, recalibrate";
fixed before any run).**
- **Why.** In M6, a post-hoc diagnostic found that hopper facilitation makes the plateau per
  cell fall with pen size: 8 cells hold 81 per cell with it and 185 without. Calhoun's sibling
  universes plateau at 130–180 per cell whatever their size. In M3 and M4 the same mechanism
  capped the colony at about 1,200.
- **The one change.** `geometry.hopper_facilitation: false` is applied to every run as a fixed
  override; `configs/replica_v2.yaml` itself is not changed. Everything else is exactly M5:
  - the configuration, with the removal event and the methods fixes;
  - the 20 parameters and their boxes;
  - the 20 targets with their sds and scales;
  - the emulator, the cut (second-largest implausibility ≤ 3) and the stop rule;
  - waves of 200 / 120 / 120, then 24 NROY points × 2 seeds;
  - the training seeds.

  Wave 1 reuses M5's Latin hypercube and seeds, so the 200 points pair up with M5's: the same
  parameters, with and without facilitation. Runs are cached apart (`_output/hm_nofac/`).
- **Validation.** M6 is repeated on new fresh seeds registered before use:
  - Calhoun's pen: 48 runs, seeds 9308–9355;
  - the sibling universes: 1 / 2 / 4 / 8 cells, 12 each, seeds 9356–9403;
  - the Marsden transfer with the best member: seeds 9404–9415.
- **What the validation can still show.** The sibling universes motivated this change, so for
  the decision to drop facilitation they are no longer out of sample. They were not used to
  fit any parameter. The siblings are therefore reported as a consistency check, not as
  independent validation. The pen landmarks on fresh seeds remain the validation.
- **Reported:** the same tables as M5 and M6, the paired wave-1 comparison, and whether
  growth to 2,200 and a collapse can now co-occur.
- **Done 2026-11-12** (NOTES; 488 runs, 13.1 CPU-hours).
  - **Growth and collapse now co-occur.** 57 runs peak above 1,800 and collapse (M5: 0). NROY
    is 3.6 % of the box (M5: 0.003 %), and single runs pass the cut (best I₂ 2.35).
  - **No ensemble member passes on its seed mean** (best 3.70). The fallback is
    `configs/replica_v2_ensemble_nofac.json`.
  - **On fresh seeds:**
    - 13 of 20 pen targets are inside, including every population count, but within wide,
      bistable ranges (N@1,588: 7–3,313).
    - The sibling universes' plateau per cell is now independent of pen size, as in the record,
      but about 30 % low.
  - **Still missing:**
    - the 320-day phase of conceptions without surviving young (day 600 → 920);
    - the behavioural categories;
    - brood groups, empty boxes, the sex ratios;
    - the female side of the transfer.

**M7 — intergenerational transmission of maternal care (Jason, 2026-11-12: "네, 설계해 줘";
fixed before code).**
- **The gap it addresses.** In the record, the last surviving young was born on day 600, while
  conceptions went on to about day 920: 320 days of pregnancies with no young surviving.
  - Mothers had rejected essentially all young prematurely by mid-phase C, about day 437
    (Calhoun 1973 p. 85).
  - After transfer to fresh pens, colony females mated with competent stock males (6 of 16
    conceived), but only 5 pups of about 100 potential survived to day 14 (Marsden 1972). The
    deficit was in the females' rearing, and it was irreversible.
  - The model couples conceiving and rearing. Both scale with one competence trait and with
    current stress, so young survive almost until conceptions end. The M5b gap has a median of
    6–186 days, and transferred females rear 42 pups.
- **The mechanism** (`biology.maternal_transmission` τ ∈ [0, 1], default 0 = off). Maternal
  behaviour is passed on through the care received, not the genes. In rats, daughters of
  low-licking mothers become low-licking mothers, and cross-fostering shows the effect follows
  the foster mother (Francis, Diorio, Liu & Meaney 1999, *Science* 286: 1155).
  - *Care received.* Every pup accumulates the nursing weight it receives over its life before
    weaning: the w of the nursing relaxation, i.e. maternal investment × milk share ×
    disturbance, summed over its box's mothers in contact, times dt. Its care index is that sum
    divided by `weaning_days`, the mean w. A pup without a box receives none.
  - *Transmission.* At weaning, a daughter's maternal capacity becomes
    `(1 − τ) + τ · min(1, care index / care_ref)`. Stress erosion in adulthood applies as before.
  - Conception does not depend on maternal capacity (the replica's `fertility_cap_floor` is 1).
    A female reared on poor care conceives normally. Her low capacity enters her investment at
    birth, her NURSE choice and her nursing, so her pups starve.
  - Once care declines in phase C, it compounds: poorly reared daughters rear their own
    daughters worse. This is the cumulative, multi-generational mechanism M5 named as a
    candidate.
  - *care_ref* (`biology.care_ref`) is a normalisation, so that a typical phase-B daughter
    reaches full capacity. It is the median care index of daughters weaned on days 100–300 in
    the M5b best member, with transmission off, on training seeds 7000–7002. It is measured once,
    before any run with transmission on, and recorded here.
  - **Measured 2026-11-12: care_ref = 0.888.** That is the median of 773 daughters; the seed
    medians are 0.878, 1.011 and 0.845. The care index exceeds 1 when several mothers of a box
    nurse the same pup.
- *Development report* (the M5b best member as the base; training seeds 7000–7011, 1,600 d).
  - Arms: the base; + transmission τ = 1 (= M7); + τ = 0.5 (sensitivity).
  - Reported:
    - the landmarks;
    - the gap between the last surviving birth and the last conception;
    - adult females' maternal capacity at days 315 / 560 / 736;
    - the Marsden transfer with M7 (training seeds; development, not validation).
- *M7 targets* (reported, not fitted):
  - a gap of at least 150 days (record 320);
  - transfer with stock males: females still conceive (at least 3 of 16), but at most 10 pups
    reach 14 days (record 5);
  - whether growth to the record's size and the collapse survive.
- *Afterwards.* If the phase appears, recalibrate with τ and care_ref among the parameters
  (M5c) and validate on fresh seeds: Jason's call.
- **Done 2026-11-12** (NOTES; training seeds; development).
  - **At the specified values** (τ = 1, care_ref 0.888), maternal capacity declines across
    generations: 0.89 → 0.67 → 0.56 → 0.37 at days 315 / 560 / 736 / 1,444. But no run ends
    reproduction, so the gap does not appear.
  - **Transfer pups with stock males:** 17.5, against 42.5 in M5b and 5 in the record.
  - **Post hoc, care_ref 1.8:** the phase appears (444 days of conceptions after the last
    surviving birth, record 320), but the colony then peaks at about 800.
  - **Next:** a joint recalibration (M5c), Jason's call.

**M5c — joint recalibration with maternal-care transmission (Jason, 2026-11-12: "네, 재보정";
fixed before any run).**
- **Why.** At its a priori values (τ = 1, care_ref 0.888), M7 lowers maternal capacity across
  generations but no run ends reproduction. With a stricter care_ref (1.8, post hoc) the record's
  phase of conceptions without surviving young appears, but the colony peaks at about 800. The
  M5b parameters were fitted without the mechanism. Whether growth to 2,200, the phase and the
  collapse can co-occur needs the mechanism's two parameters fitted jointly with the rest.
- **The change.** M5b exactly (`configs/replica_v2.yaml` with `geometry.hopper_facilitation:
  false` as a fixed override), plus two parameters:
  - `biology.maternal_transmission` τ: 0–1;
  - `biology.care_ref`: 0.5–2.5 (log). The M7 measurement (0.888) and the post-hoc 1.8 are both
    inside.

  Everything else is M5b:
  - the 20 parameters and their boxes;
  - the 20 targets with their sds and scales;
  - the emulator, the cut (second-largest implausibility ≤ 3) and the stop rule;
  - waves of 200 / 120 / 120, then 24 NROY points × 2 seeds;
  - the training seeds 7000–7011.

  Wave 1 pairs with M5b: the same 200 points in the 20 shared parameters and the same seeds,
  with τ and care_ref from a second Latin hypercube (seed 2512). Runs are cached apart
  (`_output/hm_m7/`). The script records a label's parameter names and fixed overrides with its
  first wave and refuses later calls that differ.
- **Validation** on new fresh seeds, registered now before use:
  - Calhoun's pen: 48 runs, seeds 9505–9552;
  - the sibling universes: 1 / 2 / 4 / 8 cells, 12 each, seeds 9553–9600. As in M5b they are a
    consistency check, since they motivated dropping facilitation.
  - the Marsden transfer with the best member: seeds 9601–9612. Its record motivated M7, but
    neither the transfer nor its record enters the fit.
- **Reported:**
  - the M5 and M5b tables: emulator checks, NROY fractions, conflicts, best runs, ensemble;
  - the paired wave-1 comparison with M5b;
  - the NROY ranges of τ and care_ref, and the share of NROY with τ < 0.2 (transmission weak or
    off). If that share is large, the record does not need the mechanism under this model.
  - in single runs and in ensemble members, whether these co-occur: a peak above 1,800, a gap of
    at least 150 days between the last surviving birth and the last conception, and a collapse
    (below 300 at day 1,588);
  - the M6 tables on the fresh seeds, and the M7 transfer targets: at least 3 of 16 females
    conceive with stock males, and at most 10 pups reach 14 days (record 6 and 5).
- Jason decides afterwards whether an ensemble replaces 2m as the reference for new work.
- **Done 2026-11-12** (NOTES; 488 runs, 10.3 CPU-hours; fresh seeds 9505–9612).
  - **Transmission makes the record's whole arc more frequent.** Growth above 1,800, a gap of
    at least 150 days and a collapse co-occur in 33 of 488 runs (M5b: 9). The share rises with
    τ, from 3 % below 0.2 to 14 % above 0.8.
  - **History matching does not constrain τ or care_ref.** The share of NROY with τ < 0.2 is
    0.199, as in the prior. The two targets that define the phase have two outcomes across
    seeds (reproduction ends, or goes on), and the emulators treat the spread as seed noise
    (sd 283 and 227 days).
  - **No ensemble member passes on its seed mean** (best I₂ 4.00; M5b 3.70). The fallback is
    `configs/replica_v2_ensemble_m7.json`.
  - **On fresh seeds:**
    - 13 of 20 pen targets are inside, as in M5b, with narrower ranges.
    - The sibling plateau per cell is closer to the record in the small pens; 10 of 15 record
      points are inside.
  - **The transfer fails on the female side.** With the best member, no transferred female
    conceives, even with stock males (record 6 of 16): imprinting has left the females born
    into crowding without competence. Its colonies match the peak, the last conception and the
    collapse, but because females stop conceiving, not because mothers fail to rear.
  - **Not met: the validation standard.** A proper test of the mechanism needs a method change:
    score the phase as a frequency over replicate seeds per parameter set. Jason's call.

**M5d — history matching with replicate seeds: the phase as a frequency (Jason, 2026-11-12:
"네, 방법 바꿔 보정"; fixed before any run).**
- **Why.** In M5c, the targets for the phase without surviving young have two outcomes across
  seeds: reproduction ends, or it goes on to the end of the run. One run per parameter set
  cannot tell how often each happens. The mean emulators treated the spread as noise (sd 283
  and 227 days), so τ stayed unconstrained.
- **A correction found while designing M5d.** The ensemble scoring of M5–M5c
  (`write_ensemble`) compared each member's seed mean with the record using the seed variance
  divided by the number of seeds, V_s / k. The record is one realization, so one run's variance
  belongs in the denominator as well: V_s (1 + 1/k). Re-scored this way:
  - M5: 2 of 24 members pass (best I₂ 2.94; before, 3.95);
  - M5b: none (best 3.29; before, 3.70);
  - M5c: none (best 3.00; before, 4.00).

  The two M5 members pass only because the record falls between their two seeds. In each, one
  seed holds 1,290–1,470 mice on day 1,588 and the other falls to 8 or 401, and no seed grows
  past 1,600. Once correct, a mean criterion is too lenient for targets with two outcomes. That
  is the problem M5d addresses. The fix applies from now on; the earlier ensemble files stay as
  they were.
- **Configuration and parameters:** M5c exactly. That is `configs/replica_v2.yaml` with
  facilitation off, and the 22 parameters with their boxes.
- **Replicates.** Every design point runs 6 training seeds (7000–7005).
- **Targets,** of three kinds:
  - *Mean targets* (15): first litters, N@315, adults @315, peak N, plateau onset, N@736 / 811
    / 960, both doubling times, male share @315, empty boxes, the withdrawn share, never fought
    or mated, and brood groups. They keep M5's z, sds and scales.
    - Each has two emulators: the seed mean, and the log of the seed variance V_s(x).
    - I(x) = |z − m(x)| / √(obs² + discrepancy² + emulator variance + V_s(x)).
  - *The arc frequency* p(x). This is the probability that one run does all three: grows above
    1,800, has a gap of at least 150 days between the last surviving birth and the last
    conception, and falls below 300 by day 1,588.
    - It is emulated on the share of a point's seeds that do.
    - A point is ruled out where the emulator's mean + 3 sd is below 0.05. The record would then
      be a rarer outcome than 1 in 20, even at the emulator's upper bound.
  - *Conditional targets* (5): the last surviving birth, the last conception, N@1,444, N@1,588
    and the male share @1,444, with M5's values and sds.
    - They are the record's values given the arc.
    - They are scored only in the ensemble, on the seeds where the arc occurs.
- **NROY** is the intersection of three sets:
  - M5c's final NROY (wave 0: its emulators on its 440 wave runs);
  - the points whose second-largest mean-target implausibility is ≤ 3;
  - the points where p is not ruled out.
- **Waves** (6 seeds each, 1,200 runs). Leave-one-out checks for every emulator are reported
  each wave.
  - Wave 1: 120 points drawn uniformly from M5c's final NROY.
  - Wave 2: 80 points drawn uniformly from the M5d NROY.
- **Ensemble.** From the final NROY, 24 points are drawn uniformly among the 10 % of candidates
  with the highest emulated p. Each runs all 12 training seeds (7000–7011); seeds 7006–7011 are
  new to M5d's design.
  - Mean targets use the member's own seed variance: I = |z − ȳ| / √(obs² + discrepancy² +
    V_s (1 + 1/12)).
  - Conditional targets use the member's arc seeds: I = |z − ȳ_arc| / √(obs² + discrepancy² +
    V_arc (1 + 1/k_arc)). V_arc is the within-member variance on arc seeds, pooled over the
    members with at least 2 of them.
  - A member passes if the arc occurs in at least 2 of its 12 seeds, and the second-largest
    implausibility over all 20 targets is ≤ 3. If none passes, the 12 best by that
    implausibility are written with `fallback: true`.
- **Stop rule.** If, after a wave, no candidate in the mean-target NROY has an emulated p above
  0.05, the waves stop: the arc is then rare wherever the other targets fit.
- **Validation** on new fresh seeds, registered now before use:
  - Calhoun's pen: 48 runs, seeds 9613–9660, with the arc's frequency on fresh seeds;
  - the sibling universes: seeds 9661–9708, a consistency check;
  - the Marsden transfer with the best member: seeds 9709–9720.
- **Reported:**
  - the re-scoring of M5–M5c above;
  - emulator checks, and NROY sizes as a share of the box and of M5c's NROY;
  - the emulated p over NROY (its distribution and maximum), and the observed arc counts per
    point;
  - τ and care_ref over NROY and over its high-p part, with the share of τ < 0.2;
  - each member's arc frequency on seeds 7000–7005 against 7006–7011, an internal check;
  - the M6 tables and the transfer.
- **Cost:** about 1,500 runs (about 30 CPU-hours), plus validation.
- Jason decides afterwards whether an ensemble replaces 2m as the reference.
- **Done 2026-11-12** (NOTES; 1,488 runs, 34.0 CPU-hours; fresh seeds 9613–9720).
  - **The arc becomes common where it is selected for.** On fresh seeds 20 of 48 runs show
    growth above 1,800, a gap of at least 150 days and a collapse (M5c: 1). Its frequency is a
    property of the parameter set: the ensemble's seed halves give 45 and 38 of 144 runs
    (Spearman 0.73 over members).
  - **τ is constrained only where the arc is frequent:** a median of 0.81 in the 10 % of NROY
    with the highest emulated p, and 1.2 % below 0.2. Over the whole NROY the share below 0.2 is
    0.208, as in the prior.
  - **No member passes** (best I₂ 3.14). The fallback is `configs/replica_v2_ensemble_m5d.json`.
    Post hoc, the two design points that passed on their six seeds score 3.41 and 3.51 on
    twelve.
  - **On fresh seeds 11 of 20 pen targets are inside** (M5c: 13). The ensemble's arc follows
    faster early growth than the record's and comes late: last surviving birth 1,060, last
    conception 1,482 (record 600 and 920). The siblings have 11 of 15 inside.
  - **The transfer shows the record's route.** The best member's females are competent (0.81)
    and conceive with stock males (10 of 16; record 6), and no pup reaches 14 days (record 5).
    Both M7 transfer targets are met.
  - **Not met: the validation standard.** The remaining misses are mostly the categories.
    - One developmental competence value governs withdrawal, courtship, conception and care.
    - So weak imprinting leaves almost no withdrawn young, and no young that never fought or
      mated. Strong imprinting (M5c) leaves females that cannot conceive.
    - Next: Jason's call.

**M8 — the behavioural categories: the "beautiful ones" disengage, and fertility is apart from
social competence (Jason, 2026-11-12: "Yes, design it"; fixed before code).**
- **The gap.** M5d's best member comes closest to the record's population arc, and its transfer
  takes the record's route. But the categories miss: 0–1 % of young adults never fought or
  mated on day 800 (record 53 %), and 7–12 % of the weaned are withdrawn on day 560 (record
  32 %). Stronger imprinting withdraws more young, but then the females cannot conceive at all
  (M5c's transfer: 0 of 16).
- **Pre-spec diagnostic** (2026-11-12). The M5d best member on development seeds 7000–7001,
  with `imprint_rate` 0.0073 (the member's), 0.03 and 0.09. `_aggress` was replaced by an exact
  copy that also logs attacker and target, so the runs are unchanged (`_output/m8_diag*.json`).
  - **No male can count as never having fought.**
    - By day 800, 94–100 % of the males aged 131–320 days have both attacked and been
      attacked, in every arm. That holds even where 97–98 % of them are withdrawn.
    - At `imprint_rate` 0.09 (seed 7000), 87 % attacked and 97 % were attacked *while
      withdrawn*.
    - Withdrawn animals keep the AGGRESS action (its utility is aggression × stress), and they
      stay targets.
  - **Females.** At 0.09 every young female is withdrawn by day 800, and none conceives:
    withdrawn females are excluded from conception, so a transfer fails as in M5c. A quarter of
    them were attacked as adults by nursing females.
  - **Fights before maturity are a small part.** As adults, 88 % of the young males attacked
    and 98 % were attacked; at any age, 99 % and 99 %.
- **The record separates two groups** (M4).
  - Withdrawn males pooled at the centre, wounded in fights among themselves.
  - The "beautiful ones": unwounded, never fought or mated.

  Transferred colony females conceived with competent stock males (6 of 16), but not with the
  colony's males. The model gives both groups one role and one behaviour, and one competence
  value gates withdrawal, male courtship, female fertility and maternal investment.
- **The change.** Two fields; their defaults are the current model; NumPy path only.
  1. `biology.withdrawn_disengage` (default false). Adults whose developmental competence is
     below `withdrawn_competence_threshold` (withdrawn for life: the beautiful ones) neither
     fight nor are fought:
     - the AGGRESS action is masked for them;
     - they are never the target of an attack.

     Animals withdrawn by stress alone (high stress, low social drive, low aggression) keep
     today's behaviour: they fight and are attacked (Calhoun's centre pool). Territory contests
     already exclude every withdrawn male.
  2. `biology.fertility_from_competence` (default true). When false:
     - a female's conception no longer scales with her developmental competence (her factor
       c_f is 1);
     - a female withdrawn for low competence stays eligible to conceive, and males' courtship
       approaches include her. The other filters stay: age, stress below 0.8, energy, not
       pregnant.

     Two things still scale with competence:
     - Male courtship still scales with competence × courtship capacity. So a colony whose
       males are incompetent stops conceiving (record: no conception with the colony's males).
     - Maternal investment still scales with the mother's competence × maternal capacity. So a
       mother withdrawn for low competence rears almost nothing (record: 5 pups of about 100).
  3. **Bookkeeping, with no effect on the run.** A new flag marks either side of a fight or
     contest from maturity on. The share of 131–320-day-olds who never fought *as adults* or
     mated is reported beside the any-age share. The adult share is Calhoun's definition:
     those entering adulthood who never fought. M5–M5d used the any-age share.
- **Tooling fix.** `replica_transfer.py --members` merged the member's parameters over the
  arm's overrides, so an arm could not change a member parameter. The arm's overrides now win,
  as in `replica_report.py`. Earlier transfers had no overlapping keys, so their results do not
  change.
- **Development report.** The base is the M5d best member; training seeds 7000–7011, 1,600
  days. This is development, not validation.
  - Arms:
    - A0: the base;
    - A1: + disengagement;
    - A2: + disengagement + the fertility split (= M8);
    - A2 at `imprint_rate` 0.03 and 0.06 (stronger imprinting, now possible without sterile
      females);
    - A0 at `imprint_rate` 0.06 (strong imprinting without M8: the bracket).
  - The Marsden transfer for every arm (training seeds).
  - Reported for every arm:
    - never fought or mated (adult and any-age shares);
    - the withdrawn share at day 560, and withdrawn animals at the centre;
    - the arc over 12 seeds: growth above 1,800, a gap of at least 150 days, and a collapse;
    - last surviving birth, last conception, peak N, N@315, adults @315;
    - the male share at day 1,444, and maternal capacity;
    - the transfer numbers.
- **M8 targets** (reported, not fitted; the tolerances are M4's):
  - never fought as adults or mated, 131–320 days old, day 800: 0.53 ± 0.15;
  - withdrawn share of the weaned at day 560: 0.32 ± 0.10;
  - transfer: with the colony's males, at most 1 female conceives (median; record 0). With
    stock males, at least 3 of 16 conceive, and at most 10 pups reach 14 days.
- **The structure question.** Does any A2 arm meet all three at once, in seed medians?
  - If yes: recalibrate with M8 on (M5e), with the adult share as the categories' target, and
    validate on fresh seeds. Jason's call.
  - If not: report what is missing.
  - Reported but not a target: whether the arc survives (its count, landmarks and peak).
- **Done 2026-11-12** (NOTES; 144 runs on training seeds; development).
  - **The structure question: no.** No A2 arm meets the three targets at once.
  - **At the member's weak imprinting, M8 changes almost nothing.** No adult falls below the
    competence threshold, so A1 is identical to A0.
  - **At `imprint_rate` 0.06, M8 gives the categories and the stock-male transfer together.**
    - 41 % of young adults never fought as adults or mated (target 0.38–0.68).
    - With stock males, 6.5 of 16 transferred females conceive, and no pup reaches 14 days.
    - Without M8 at the same imprinting, 1 of 16 conceives.
  - **At that setting the colony stops growing:** peak 1,218, and no run shows the arc.
    - 49 % of the weaned are withdrawn on day 560 (limit 0.42).
    - The colony's own males sire in the transfer (5 of 16; record 0). In the smaller colony
      crowding no longer erodes their courtship (0.75, against 0.03 in A0).
  - **With M8, the any-age share falls to 0.** The young who never fought as adults had
    fought before maturity, and a larger share of the attacks now falls on pups and juveniles.
  - **Next, Jason's call:**
    - recalibrate with M8 on (M5e), with the imprinting rate and its density threshold free;
    - or stop the replica line.

**M5e — history matching with M8 on (Jason, 2026-11-12: "Run M5e"; fixed before any run).**
- **Why.** M8 removed the two structural blocks. But the population parameters were fitted
  without it, and at the strong imprinting that gave the categories, the colony stopped
  growing. Only a recalibration with M8 on can tell whether some parameter set does all of
  this:
  - the colony grows to the record's size;
  - the later cohorts imprint;
  - crowding erodes the males' courtship.
- **The design is M5d exactly, with two changes:**
  - **M8 on,** as fixed overrides beside facilitation off: `biology.withdrawn_disengage: true`
    and `biology.fertility_from_competence: false`.
  - **The categories target** "never fought or mated" (131–320 days old, day 800) is measured
    as the adult share (`beautiful_share_adult`), with M5's z (0.53), sds and scale.

  Everything else is M5d:
  - the 22 parameters and their boxes;
  - the 15 mean targets, the arc frequency (α 0.05) and the 5 targets given the arc;
  - wave 0, M5c's final NROY;
  - waves of 120 and 80 points × 6 seeds (7000–7005);
  - the ensemble of 24 points from the top 10 % of emulated p, run on 12 seeds;
  - the member criterion: the arc in at least 2 of 12 seeds, and I₂ ≤ 3 over all 20 targets;
  - M5d's wave stop rule.
- **Wave 1 pairs with M5d.** It draws the same 120 points (the same candidate stream) and runs
  the same seeds, so the difference is M8 and the adult measure.
- **A caveat on wave 0.** M5c's NROY was built without M8, with the any-age share. Its rule
  (the second-largest implausibility) lets one target fail, and the any-age share was mostly
  that target. So wave 0 should cut little of what M8 makes possible; the paired wave 1 shows
  how much it does.
- **Stop rule for the replica line (new).**
  - If no ensemble member passes, the replica line ends: no further replica milestone. The
    frozen 2m colony stays the reference. The best member of M5d or M5e (whichever does
    better on fresh seeds) is documented with its misses as the final replica.
  - If M5d's wave stop rule ends M5e early, the same applies.
  - If members pass, they are validated on the fresh seeds below. Jason decides afterwards,
    whatever the validation shows.
- **Validation** on new fresh seeds, registered now before use. The categories target counts
  as the adult share.
  - Calhoun's pen: 48 runs, seeds 9721–9768, with the arc's frequency;
  - the sibling universes: seeds 9769–9816, a consistency check;
  - the Marsden transfer with the best member: seeds 9817–9828.
- **Reported:**
  - M5d's list;
  - the paired wave-1 comparison with M5d;
  - the categories (adult and any-age shares) and the withdrawn share;
  - in the transfer, whether the colony's own males sire.
- **Cost:** about 1,500 runs (about 35 CPU-hours), plus validation.

## Validation standard (fixed now; applied from M2 on)

**Population landmarks.** Calhoun's value must lie inside the replica's 90 % prediction interval
over 48 fresh seeds. The record's own uncertainty widens the interval where the record is
contested: first litters 50–104; phase-C doubling time 105–145.

**Structural phenomena.** Each milestone's targets above, with tolerances written into the
milestone's own preregistration before its test.

Every result is reported in NOTES, including the targets missed.
