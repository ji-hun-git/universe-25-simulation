# The deprived generation — a model change so reproduction ends the way Calhoun saw

Jason, 2026-11-19: "Yes, design it", answering "Design a model change so reproduction ends the way
Calhoun saw?" (TASKS U-5). This is the design, fixed before any code. The only runs behind it are
an exploratory diagnostic of the final replica on training seeds.

## What the record says

All from `docs/RESEARCH_DIGEST.md` (Calhoun 1973; Marsden 1972), with its confidence.

- **Mid-phase C, about day 437** (medium): "essentially all young prematurely rejected by
  mothers". Nursing females "wound and expel their own young days before weaning" (A6).
- **Those young survived.**
  - At the end of phase C, 60 % of the population is immature.
  - The last surviving birth is near day 600.
- **They grew up without adult behaviour** (mid-phase D, high).
  - 53 % of the mice entering the adult categories (131–320 days old) had never fought, mated or
    built a nest: the "beautiful ones".
  - They were unwounded, and unstressed by the PNMT assay. Their female counterparts sat in the
    upper boxes and were not aggressive.
- **They rarely reproduced.**
  - In a parallel two-cell universe, 18 % of 148 females born in the last 50 days of phase C had
    ever conceived, at a median age of 334 days.
  - Marsden moved 16 females and 8 males out of the colony on about day 870. With the colony's
    own males there was no sex, pregnancy or pup in 60 days. With competent stock males, 6 of 16
    females conceived, 3 littered, and 5 pups of about 100 reached day 14.
- **Reproduction ended while fertile females remained.**
  - The last conception was near day 920 (high).
  - Females stop at about 560 days of age (medium), so the last of the phase-B females (born by
    about day 315–360) stop near day 875–920.
  - The phase-C females, still fertile, mostly did not conceive.
- **The decline was slow.** The census was 2,056 on day 736, 1,871 on day 811 and about 1,650 on
  day 960. On day 1,331 the survivors' mean age was 776 days. Old age then ended the colony: 122
  on day 1,444, and 27 on day 1,588.

## What the model does

The final replica (`configs/replica_v2_final.json`) on training seeds 7000–7003, read after each
day; the runs are unchanged (`_output/hm_adults/diagnose_end.py`, `diagnose_end.json`;
exploratory).

- **Reproduction does not end.**
  - After day 600 there are about 9,200 conceptions per seed. Days 920–1,100 still have about
    1,200 per seed.
  - The mothers are mostly born in phase C (days 315–560), with competence 0.75–0.80.
  - The sires are the cell owners, born around day 200–280, with competence about 0.9.
  - Conceptions stop only as those females pass 583 days of age and the owners age.
- **There is no deprived generation.**
  - On day 900, no animal of any birth cohort has competence below 0.5, and at most 1 % of any
    cohort is withdrawn.
  - A pup is milk-dependent and nest-bound until weaning on day 21. Expelled or unfed, it
    starves. So the young that survive are the ones that were cared for.
- **Day 800, the 131–320-day-olds:**
  - Every male has fought as an adult, and none has mated (only owners sire).
  - 99 % of the females have conceived.
  - Record: 53 % never fought or mated.
- **Phase-D deaths.** Over days 736–960, the hazard terms on the living give the expected deaths
  (mostly of adults; starving pups are apart):
  - the age-independent base hazard, about half;
  - old age, about a quarter;
  - stress and wounds, the rest.

## Why earlier changes did not get there

- **M4: development from care** (`docs/REPLICA_V2.md`).
  - It costs competence only while a pup is boxless before weaning, and a boxless pup dies.
  - So it removes deprived young instead of making deprived adults.
- **M8: the beautiful ones disengage.** It keyed the phenotype on low competence, and low
  competence needed strong imprinting by crowding.
  - Crowding reaches the phase-B litters too, so the colony stopped growing (peak 1,218).
  - In M5e's 1,488 runs, the categories and the arc never appeared together.
- **What the record points to instead.**
  - The deprived generation was made by mothers, from mid-phase C. That confines it to the
    cohorts born after rejection began.
  - It was survivable, because the young were expelled near weaning, not at birth.

## The change

One switch, `biology.deprivation`, default false. Off, the model is today's: the frozen colony,
the final replica and the golden hashes are unchanged. NumPy path only, as for replica v2, with
per-animal bookkeeping kept off `AgentSoA` like the body and coat genetics. Three values are set
a priori, not fitted.

1. **Early independence.** A pup at least `independence_days` old (a priori 17) is weaned from
   that day if either:
   - it is expelled from its box (litter abandonment); or
   - it is going unfed: hunger above `independence_hunger` (a priori 1.0; starvation begins at
     1.2).

   It then forages and drinks as a juvenile. Mice eat solid food from about two and a half
   weeks. A younger expelled or unfed pup is unchanged: it dies, as now.
2. **Deprivation.** A pup weaned early is deprived for life. Its competence is multiplied by
   `deprived_factor` (a priori 0.375: Marsden's 6 of 16, the conception rate of colony females
   with competent males).
3. **The deprived adult**, Calhoun's beautiful ones:
   - **Role and fighting.** It is withdrawn. It neither fights nor is fought, as M8's
     disengagement, but keyed on deprivation rather than on a competence threshold.
   - **Stress.** Crowding, its box and displacement do not stress it (the PNMT assay).
   - **A male** never courts or holds a cell. Withdrawn males already cannot.
   - **A female** stays eligible to conceive despite the withdrawn role. Her chance scales with
     her competence, as every female's does (`fertility_from_competence`), so it is about a third
     of an undeprived female's.
     - The record has 6 of 16 with stock males, and 18 % ever in the two-cell universe.
     - With the colony's males, who are mostly deprived or eroded, few conceptions should
       follow.
   - **Maternal investment** already scales with competence × maternal capacity. So a deprived
     mother rears little: Marsden's 5 pups of about 100 reached day 14.
4. **Unchanged, and still fitted.**
   - When rejection starts: the mothers' stress, `maternal_neglect_stress` and
     `litter_abandon_p`.
   - The base hazard: the record's slow decline argues for a low one.
   - The rest of the 22 parameters.

## What it should do, if Calhoun's account is right

- **Growth is unaffected.** Phase-B mothers are calm and nurse to weaning, so the colony still
  grows to the peak. M8 failed here.
- **From mid-phase C:**
  - stressed mothers expel or stop feeding their older pups, who survive deprived;
  - younger litters die, so surviving young end once rejection reaches every litter.
- **On day 800,** most 131–320-day-olds are deprived. They have not fought, and few have mated:
  the categories.
- **Conceptions end as the undeprived females pass their fertile age** (born by about day 437,
  so by about day 1,020 at the latest). The owners age and erode too. So the last conception
  should move from about day 1,100 toward the record's 920.
- **The decline is slower.**
  - Deprived adults are neither wounded nor stressed, so they die of old age, as the survivors'
    mean age of 776 days says.
  - The fit's base hazard can then be low.

## Development look (fixed now, before code; exploratory, training seeds)

- **Base:** the final replica's parameters; seeds 7000–7011; 1,600 days in Calhoun's pen.
- **Arms**, 4 × 12 = 48 runs:
  - A0: deprivation off (today);
  - A1: on, with the a priori values;
  - A2: A1 with `litter_abandon_p` doubled (more expulsion);
  - A3: A1 with `deprived_factor` 0.2 (stronger deprivation).
- **Reported for every arm**, as seed medians:
  - the 14 record targets, with Calhoun's adults;
  - the arc count;
  - never fought as adults or mated (131–320 days old, day 800);
  - the withdrawn share of the weaned on day 560;
  - the deprived share by birth cohort;
  - conceptions after day 920;
  - the last conception and the last surviving birth;
  - the peak and N on day 960.
- **The structure question.** Does any arm show, in seed medians, the arc in at least 8 of 12
  seeds together with these three?
  - a last conception by day 1,000;
  - never fought or mated 0.38–0.68;
  - withdrawn on day 560 0.22–0.42.
- **If yes:** a record fit with deprivation on, preregistered.
  - The three a priori values stay fixed, and the 22 parameters are free.
  - It is validated on fresh seeds that are still unread: 9160–9199 and 9464–9471. Jason's call.
- **If no:** report what is missing. Jason's call.

## Risks

- **More surviving young after day 600.** Survivable expulsion keeps young alive while
  rejection is partial, and the record's last surviving birth is day 600. The fit's
  maternal-erosion parameters have to close it.
- **Too many survivors late.** Unstressed deprived adults may live long enough to keep N on days
  1,444 and 1,588 above the record. Old age (lifespan 780 ± 150 days) should still end the
  colony.
- **Small samples.** The deprived female's fertility rests on 16 transferred females and 148 in
  another universe.
- **One account.** This follows Calhoun's own reading of one colony. A fit that reproduces it
  shows the account is sufficient, not that it is right.

## Cost

- **Code:** `sim.py` (early independence, the deprived flag, its exclusions), config fields,
  and tests:
  - off is bit-identical (golden hashes);
  - on, an expelled 18-day pup lives and is deprived, and an expelled 10-day pup dies.
- **The development look:** 48 runs, about 15 minutes.
- **If it goes on:** a record fit of about 1,000 runs, plus its validation, about 3–4 hours.

## Built and looked at (2026-11-19; NOTES 2026-11-19)

- **Built as designed.** Off, it is bit-identical: the final replica on seed 9112 reproduces all
  23 stored outputs, and the golden hashes match. `tests/test_deprivation.py` checks each rule.
- **The structure question: no.**
  - **The categories, partly.** The withdrawn share on day 560 reaches the record's 0.32 (from
    0.09). The never-fought-or-mated share rises from 0.00 to 0.23–0.37 (range 0.38–0.68).
  - **The decline slows.** N on day 960 goes from 1,264 to 1,401–1,620 (record 1,650).
  - **Reproduction ends later, not earlier.** The last conception moves to days 1,292–1,599
    (from 1,092), the last surviving birth to 1,003–1,227 (from 692). Too many mice are left on
    days 1,444 and 1,588.
- **Why, from a trace of A1:**
  - **Deprived females still conceive.** 98 % of the young females have mated by day 800, though
    38 % are deprived. Marsden's 60-day rate, applied for months, reaches nearly all of them;
    the two-cell universe's 18 % ever is the stricter figure.
  - **Rejection is partial.** It reaches about 38 % of the cohort born in days 437–560, not
    "essentially all".
  - **A phase-D generation forms.** Young that survive late become a breeding generation of
    their own.
- **Next, Jason's call.** The switch stays off by default.

## Revision 1 (Jason, 2026-11-19: "Yes, revise it"; fixed before code)

The first look missed for two reasons. Each gets a lever, set a priori. Both default to version 1,
so version 1 and its look reproduce exactly.

- **Lever 1: the deprived female's fertility** (`biology.deprived_fertility`, a priori 0.01;
  unset = version 1).
  - **The rule.** A deprived female's daily chance of conceiving is this fraction of an
    undeprived female's in the same cell. It replaces the competence scaling for her.
  - **Why version 1 was wrong.** It used Marsden's 6 of 16 as a daily multiplier. That figure is
    a 60-day share, so version 1 was about 30 times too fertile. Two hazard ratios, with the
    model's own daily rates (training seeds 7000–7003, the switch off;
    `_output/hm_adults/conception_rate.py`):
    - Marsden, 6 of 16 in 60 days with stock males (0.0078 a day), against the uncrowded
      phase-B rate of 0.61 a day: 0.013.
    - The two-cell universe, 18 % ever by 334 days of age (7.4 × 10⁻⁴ a day over about 270
      fertile days), against the phase-D rate of 0.10 a day: 0.007.
    - Their middle is 0.01.
- **Lever 2: rejection near weaning** (`biology.expel_at_independence`, default false =
  version 1).
  - **The rule.** A nursing mother whose stress is above `maternal_neglect_stress` keeps nursing
    the pups of her box until they are `independence_days` old, then expels them. She no longer
    abandons whole litters at random (`litter_abandon_p` no longer applies).
  - **Why.** Calhoun's mothers expelled their young "days before weaning", and in mid-phase C
    essentially all young were rejected. In version 1 a stressed mother abandoned her litter
    with chance 0.137 a day, so about 92 % of her litters were abandoned before day 17 and died.
  - **What still ends surviving young.** A mother whose maternal investment is below 0.5 does
    not nurse at all, so her litter dies. That happens when stress has eroded her maternal
    capacity, or when she is deprived. The record has no surviving young after day 600.
- **Arms**, the same base and seeds (4 × 12 = 48 runs):
  - B0: off;
  - B1: version 1 + lever 1;
  - B2: version 1 + lever 2;
  - B3: both.
- **The structure question and what follows are unchanged.**
- **Risks.**
  - Lever 2 lets far more young survive in phase C; the record has 60 % of the population
    immature at its end.
  - That may raise the peak, already too high at 2,551.
  - It may also keep surviving young past day 600, unless maternal erosion ends nursing in time.
