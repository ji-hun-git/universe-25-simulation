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

**M2 — life history and an emergent phase A.**
- 48-day founders and no calendar gate (`first_conception_min_day` 0). Litter size about 5.5
  (BALB/c 5–6). Phase-B weaning survival high.
- Phase A comes out of the founders establishing themselves: male–male fighting until
  territories settle, and conception needing a settled territorial male.
- *Targets:* first surviving litters at 50–65 d (60 ± 15); 620 at day 315 (150 adults + 470
  young); the doubling time changes from about 55 d to about 145 d at day 315.

**M3 — the social system.**
- *Territories:* each wall sector is held by a territorial male, contested by maturing males,
  and the holder sires. This yields brood groups and role saturation (more young adults than
  roles).
- *Hoppers:* aggregation emerges from social facilitation at feeding.
- *Boxes:* physical box occupancy, with a choice among free boxes and the effort of upper levels.
- *Targets:* about 14 brood groups by day 315 with a skewed young-per-group distribution (Fig 3:
  111 … 13); territories shrinking towards the ring stands in phase C; about 20 % of boxes empty
  at the peak.

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

**M6 — out-of-sample validation.**
- The sibling universes of Calhoun 1971 (1, 2, 4 and 8 cells; Fig 3) were never fitted. They are
  the cleanest out-of-sample test: the same biology in smaller pens.
- Then the guard v2 / predictive-check protocol against the record on fresh seeds.

## Validation standard (fixed now; applied from M2 on)

**Population landmarks.** Calhoun's value must lie inside the replica's 90 % prediction interval
over 48 fresh seeds. The record's own uncertainty widens the interval where the record is
contested: first litters 50–104; phase-C doubling time 105–145.

**Structural phenomena.** Each milestone's targets above, with tolerances written into the
milestone's own preregistration before its test.

Every result is reported in NOTES, including the targets missed.
