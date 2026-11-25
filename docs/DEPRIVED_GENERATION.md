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

### Revision 1 looked at (2026-11-19; NOTES 2026-11-19)

- **Checks.** Off and version 1 reproduce exactly:
  - the final replica on seed 9112, and arm A1 on seed 7000, each give 23 of 23 outputs;
  - the golden hashes match.
- **The structure question: no, in every arm** (B0–B3).
- **Lever 1 (B1) does what it was for.**
  - N on day 960 is 1,652, the record's value. The withdrawn share is 0.33, and never fought or
    mated is 0.35.
  - But the last conception stays late (1,296). Females who escaped deprivation keep breeding.
- **Lever 2 (B2) stalls growth, as M8 did.**
  - Mothers above the neglect threshold exist already in phase B, so whole early cohorts are
    deprived.
  - The peak is 1,470, and no seed shows the arc.
- **The common cause.** In this replica, maternal breakdown follows each mother's local stress
  (M4). So it starts too early in places and never reaches every mother.
  - Calhoun's rejection was colony-wide by mid-phase C.
  - The frozen colony, whose breakdown is colony-wide, ends reproduction on time: last surviving
    birth 596, last conception 956.
- **Next, Jason's call:**
  - a revision 2 that triggers rejection colony-wide;
  - or stop. The switch stays off by default.

## Revision 2 (Jason, 2026-11-19: "Try revision 2"; fixed before code)

Rejection near weaning becomes colony-wide, triggered as the frozen colony triggers breakdown.
Revision 1's fertility stays. Lever 2 of revision 1 (expulsion by each mother's own stress) is
not used. Every new field defaults to off, so version 1 and revision 1 reproduce exactly.

- **The trigger** is the frozen colony's breakdown factor, unchanged
  (`biology.breakdown_factor` of the weaned density; the replica config's threshold 0.58 and
  ramp 0.2). In the replica it is otherwise unused, since M4 made breakdown individual.
  - Exploratory, training seeds 7000–7003, the switch off (`_output/hm_adults/trigger_timing.py`):
    the factor first rises above 0 near **day 437, Calhoun's mid-phase C**, with no tuning.
  - It reaches 0.4–0.6 on days 500–600, and falls to about 0.05 by day 800 as the colony thins.
- **The rule** (`biology.colony_rejection`, default false). Once a day, f is the factor.
  - In every box with a nursing mother, the pups at least `independence_days` old are expelled
    with chance f: one draw per box, in box order. `_independence` weans them deprived.
  - Version 1's maternal rules stand beside it: stressed mothers still abandon at random and
    stop nursing.
- **Irreversible** (`biology.rejection_ratchet`, default true when the rule is on). f is the
  running maximum of the factor, so rejection does not relax as the colony thins.
  - Calhoun's rejection did not relax, and the colony never recovered.
  - The frozen colony makes its breakdown irreversible for the same reason: its developmental
    exposure ensures "the collapse cannot rebound".
- **Calhoun's account.** Mid-phase C, essentially all young were prematurely rejected by their
  mothers, days before weaning.
- **Arms**, the same base and seeds (4 × 12 = 48 runs):
  - C0: off;
  - C1: deprivation + `deprived_fertility` 0.01 + colony rejection, with the ratchet;
  - C2: C1 without the ratchet;
  - C3: C1 with the trigger 0.1 earlier (threshold 0.48).
- **Reported beside revision 1's list:** the day the trigger first fires, and its highest
  factor.
- **The structure question and what follows are unchanged.**
- **Risks.**
  - The factor never reaches 1 in the replica, so some litters still escape.
  - A rule keyed on colony density reverses M4's "individual breakdown" for this one behaviour.
  - Surviving young may still run past day 600: rejection near weaning keeps them alive, and only
    maternal erosion ends nursing.

### Revision 2 looked at (2026-11-19; NOTES 2026-11-19)

- **Checks.** Off, version 1 and revision 1 reproduce exactly (23 of 23 outputs each), and the
  golden hashes match.
- **The structure question: no, in every arm** (C0–C3).
- **The timing is right.**
  - The trigger fires on day 430 [409, 443], against Calhoun's mid-phase C near day 437.
  - Rejection reaches 82–90 % of the cohorts born in days 437–700, and the arc holds (8–11 of
    12).
- **The categories overshoot.** Never fought or mated is 0.71–0.75, and withdrawn on day 560 is
  0.44–0.56.
- **Reproduction still ends late** (last conception 1,427). The colony stays too large: deprived
  adults are neither stressed nor wounded.
- **The hole.** The rule acts only on a box with a nursing-role mother. After day 700 most
  near-weaned pups are in boxes without one, where the mother's investment has fallen below
  0.5.
  - On seed 7000, all 139 young who escaped deprivation after day 700 came from such boxes.
  - They breed in phase D.
- **Next, Jason's call:**
  - revision 3: the rule acts on every box with pups of independence age;
  - then a record fit, for the overshoot and the late counts.

## Revision 3 (Jason, 2026-11-25: "Yes, revision 3"; fixed before code)

It closes revision 2's hole. Everything else is revision 2's.

- **The rule** (`biology.rejection_all_boxes`, default false = revision 2). Colony rejection acts
  on every box holding pups at least `independence_days` old, whoever their mother is. Before,
  it acted only on a box with a nursing-role mother. The chance f, one draw per box in box
  order, and the ratchet are unchanged.
- **Why.** In revision 2, a mother whose maternal investment fell below 0.5 lost the nursing
  role, but her pups could still be fed and reach weaning. After day 700 most near-weaned pups
  were in such boxes. On seed 7000, all 139 young who escaped deprivation came from them, and
  they bred in phase D. Calhoun's "essentially all young" includes theirs.
- **Arms**, the same base and seeds (4 × 12 = 48 runs):
  - D0: off;
  - D1: revision 2's C1 (deprivation + `deprived_fertility` 0.01 + colony rejection with the
    ratchet) + every box;
  - D2: D1 without the ratchet;
  - D3: D1 with the trigger 0.1 later (threshold 0.68). Revision 2's categories overshot, and an
    earlier trigger (C3) raised them, so this brackets the other side.
- **Reported:** revision 2's list, unchanged.
- **The structure question and what follows are unchanged.**
- **Risk.** Closing the hole deprives even more of the late cohorts, so the categories, already
  above range, may rise further. The look reports it, and a record fit would have to bring them
  back.

### Revision 3 looked at (2026-11-25; NOTES 2026-11-25)

- **Checks.** Off and every earlier version reproduce exactly (23 of 23 outputs each), and the
  golden hashes match.
- **The structure question: no, in every arm** (D0–D3).
- **Reproduction ends near the record for the first time.**
  - The last conception is day 969 [911, 1,005] in D2, with 920 inside that range.
  - Conceptions after day 920 fall from 1,152 to about 150 per run.
- **No seed shows the arc.** Growth and collapse hold in all 48 runs. But surviving births run to
  days 922–972 (record 600), so the phase without surviving young lasts 26–46 days (the arc needs
  150; the record has about 320).
- **The categories overshoot** with the trigger as specified (0.83). The later trigger (D3)
  gives withdrawn 0.34, in range.
- **Exploratory: lowering the erosion threshold opens the gap only by stopping growth** (peaks
  1,155 and 468), because erosion is local.
- **Next, Jason's call:**
  - revision 4, a colony-timed end of surviving young (the frozen colony's colony-wide breakdown
    stress is the candidate);
  - or stop.

## Revision 4 (Jason, 2026-11-25: "Yes, revision 4"; fixed before code)

Surviving young end when the colony breaks down, not when each mother's own stress happens to
cross a threshold. Everything else is revision 3's.

- **The rule** (`biology.rejection_stress`, default false = revision 3). With colony rejection on,
  the frozen colony's colony-wide breakdown stress returns. Every animal's stress gain rises by
  `social_breakdown_stress_boost` × f, where f is the day's rejection chance (with the ratchet,
  its running maximum). The deprived adult is not stressed by it, as it is not by crowding.
  - Only the stress term returns. The frozen colony's developmental term
    (`imprint_breakdown_exposure`) does not: the rejected young already carry their deficit, and
    the categories already overshoot.
  - It makes no draw, so off and every earlier version reproduce exactly.
- **Why.** In revision 3 a mother nurses her pups to 17 days unless her own stress, which follows
  her box and cell, is above the neglect threshold (0.785). Many mothers stay below it, so young
  survive to about day 950. In the frozen colony this colony-wide term ends surviving births on
  day 596 (record 600). Raised from day 437 on, it should take mothers across the colony over the
  neglect threshold and erode their maternal capacity (above 0.792). Their litters then die
  before independence.
- **The value, a priori.** The replica config still holds the frozen colony's
  `social_breakdown_stress_boost`, 0.248, unused since M4.
  - It is a gain, and the replica's stress decays faster (0.560 a day against 0.914). So the same
    gain gives more stress: at f = 1, 0.44 against the frozen colony's 0.27.
  - E1 takes the gain as it stands. E2 takes the frozen colony's stress: gain 0.152
    (0.248 × 0.560 / 0.914).
- **Arms**, the same base and seeds (4 × 12 = 48 runs):
  - E0: off;
  - E1: revision 3's D1 + `rejection_stress` (gain 0.248);
  - E2: E1 with gain 0.152;
  - E3: E1 with D3's later trigger (threshold 0.68), which put withdrawn in range.
- **Reported:** revision 2's list, plus the gap (last conception − last surviving birth).
- **The structure question and what follows are unchanged.**
- **What it should do, if this is the missing piece.** Surviving births end near days 600–700
  while conceptions go on to near day 920. The gap opens past 150 days, and the arc returns.
- **Risks.**
  - Males are stressed too. Above 0.732 their courtship erodes, so conceptions may end early and
    close the gap from the other side.
  - Stress from day 437 slows the last of growth. D1's peak is 2,668 against the record's 2,200,
    so some fall is room, but a peak below 1,800 breaks the arc.
  - More stress means more stress deaths and more withdrawal. Withdrawn on day 560 may rise.
  - The replica's stress becomes partly colony-wide again: a second step back from M4, after
    revision 2's trigger.

### Revision 4 looked at (2026-11-25; NOTES 2026-11-25)

- **Checks.** Off and every earlier version reproduce exactly (23 of 23 outputs each, arms A1,
  B3, C1, C2, D1 and D2), and the golden hashes match.
- **The structure question: no, in every arm** (E0–E3).
- **It moves the right way** (E1 against revision 3's D1):
  - the last surviving birth comes forward from 922 to 866;
  - the peak falls from 2,668 to 2,311 (record 2,200);
  - conceptions after day 920 fall from 147 to 54 per run, and the last conception is 956
    [885, 987], with 920 inside.
- **The gap is still short:** a median of 70 days, against the 150 the arc needs. The arc forms
  in 1 of 36 runs with the stress (E3).
- **The categories overshoot further** (0.88). The later trigger (E3) brings withdrawn into
  range (0.41).
- **Why** (exploratory, E1 on seed 7000):
  - The added stress reaches 0.26 by day 600.
  - Mothers still raising pups 10–17 days old sit at a median stress of 0.62–0.65. That is below
    the neglect threshold (0.785) and the erosion threshold (0.792).
  - So the trickle of litters they raise keeps the rate-based landmark near day 866.
  - In the frozen colony the same stress erodes maternal capacity, because its erosion threshold
    is 0.508.
- **Next, Jason's call:**
  - revision 5: from the trigger on, maternal erosion at the frozen colony's threshold (0.508);
  - or stop.

## Revision 5 (Jason, 2026-11-25: "Yes, revision 5"; fixed before code)

The frozen colony's maternal breakdown, taken whole: its colony-wide stress (revision 4) and the
erosion threshold at which that stress wears maternal capacity away. Everything else is revision
4's.

- **The rule** (`biology.rejection_erosion_stress`, default unset = revision 4). From the day the
  colony rejection trigger first fires, maternal erosion uses this threshold in place of
  `maternal_erosion_stress`. Before that day the replica's own threshold stands, so phases A and B
  are untouched.
  - Erosion itself is unchanged: once a day, a weaned female above the threshold loses maternal
    capacity at `maternal_erosion_rate` (0.169, the same in both colonies) × her excess stress,
    and a mother below 0.5 does not nurse.
  - It is irreversible from that day, like the ratchet, and makes no draw. So off and every
    earlier version reproduce exactly.
- **The value, a priori:** the frozen colony's threshold, 0.508. The final replica moved it to
  0.792. An exploratory bracket on 2026-11-25 showed why: lowered for the whole run, erosion
  follows local stress from phase B on and stops growth.
- **Why.** In revision 4, mothers still raising pups sat at a median stress of 0.52 on day 450 and
  0.62–0.65 on days 500–700 (E1, seed 7000), below 0.792. Their maternal capacity never eroded,
  and the trickle of litters they raised kept surviving births going to about day 866. In the
  frozen colony the same stress erodes capacity at 0.508 and ends surviving births on day 596.
  Above 0.508 by about 0.1, capacity falls from 1 to 0.5 in about a month.
- **Arms**, the same base and seeds (4 × 12 = 48 runs):
  - F0: off;
  - F1: revision 4's E1 (deprivation, `deprived_fertility` 0.01, colony rejection with the ratchet
    in every box, `rejection_stress` at gain 0.248) + `rejection_erosion_stress` 0.508;
  - F2: F1 with E2's gain 0.152, which makes both the stress level and the threshold the frozen
    colony's;
  - F3: F1 with the later trigger (threshold 0.68), which put withdrawn in range in revisions 3
    and 4.
- **Reported:** revision 4's list, unchanged.
- **The structure question and what follows are unchanged.**
- **What it should do, if this is the missing piece.**
  - Mothers' capacity erodes in the month or two after the trigger, so surviving births end near
    days 550–650.
  - Conceptions go on to near day 920, since males are untouched, so the gap opens past 150 days.
  - Fewer late cohorts reach independence, so fewer are deprived, and the categories, which
    overshoot (0.88), should fall.
- **Risks.**
  - Erosion from day 430 slows the end of growth. E1's peak is 2,311, and a peak below 1,800
    breaks the arc.
  - Fewer surviving young lower N after the peak. E1's N@960 is already below the record (1,390
    against 1,650).
  - The deprived generation shrinks with the cohorts that reach independence. The categories
    could fall below their ranges.
  - Every weaned female erodes, including young ones who have not yet bred.
