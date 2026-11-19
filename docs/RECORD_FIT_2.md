# Record fit 2 — adults counted as Calhoun counted them

Jason, 2026-11-19: "try a new fit aimed at adults on day 315". This page is the preregistration
of that fit (TASKS U-3). It was written and committed before any new simulation run. The only
runs before it were replays: the first 316 days of existing training runs, re-measured.

## Why a new fit

- **U-1 failed** (`docs/RECORD_FIT.md`; NOTES 2026-11-19). Every member missed adults on day 315,
  with 240–806 against the record's 150. Only 3 of the 236 training runs with the arc had both
  day-315 numbers within 3 sd.
- **The two counts differ.**
  - U-1 counted adults from sexual maturity: age at least `biology.maturity_days`, a fitted
    parameter with a range of 42–70 days.
  - The record's "150 adults + 470 immature" on day 315 uses Calhoun's own age categories
    (`docs/RESEARCH_DIGEST.md` A6): preweaning 1–30 days, juvenile 31–70, subadult 71–130,
    establishing adult 131–210, adult 211–320, declining 321–450, senescent 451+.
  - The same categories set the "beautiful ones" target (131–320 days old, day 800).
- **The record's own arithmetic agrees.** Calhoun gives 620 mice on day 315 after doubling every
  55 days. On that curve:
  - about 120 mice are older than 131 days;
  - 270–330 are past sexual maturity (50–65 days);
  - about 43 are older than 211 days.
  - The record's 150 is about one target sd (34) from the first count, and 3.5–5.5 sd from the
    second. The third is far too few, since mice that old were born before day 104.
- **The miscount pulled on biology.** The rule's member had `maturity_days` 69.5, near the top
  of its range. The fit was making mice mature late to get fewer "adults".
- **How it was found.** It was found after U-1's result, by asking why every member missed this
  one target. The categories it uses have been in the digest since the 2026-11-04 review.
- **An exploratory replay** (training seeds 7000–7011; `_output/hm_adults/replay315.json`)
  counted mice aged 131 days or more on day 315:

  | member | aged ≥ 131 d | past sexual maturity |
  |---|---|---|
  | final replica | 128 [96, 174] | 339 [236, 398] |
  | U-1's candidate (the rule's member) | 118 [77, 144] | 266 [154, 370] |

  Each cell is the median over 12 seeds, with the range in brackets.

## What changes

- **One target's definition.** Adults on day 315 is the number of living mice aged 131 days or
  more (`adults_131_at_day_315` in `scripts/history_match.py`). Its record value (150) and sds
  stay U-1's: observation 15, model discrepancy 30, on a log scale.
- **Still reported:** the count from sexual maturity, as "past sexual maturity".

## What stays (U-1's)

- **The model.**
  - The pen: replica v2's.
  - The settings: M5d's, with hopper facilitation off and maternal-care transmission on.
  - The 22 parameters and their ranges.
- **The targets.**
  - The other 13 targets and their sds.
  - The arc: growth above 1,800, at least 150 days from the last surviving birth to the last
    conception, and fewer than 300 mice on day 1,588.
- **The method.** The sampling (emulated arc frequency at least 0.3), the ensemble design and
  the candidate rule.
- **N on day 315 counts every living mouse, as in U-1.**
  - The digest calls the 620 "weaned mice".
  - Calhoun's own birth count does not fit that reading: 842 young were born in 14 brood groups
    over days 86–338.
  - On a 55-day doubling, about 470 of them were born by day 294, old enough to be weaned on day
    315. With the 8 founders, that is far short of 620. About 620 were born by day 315.
  - The weaned count is reported.

## Method

`scripts/record_fit2.py` runs U-1's fit (`scripts/record_fit.py`) with the adults target read
from the new count.

- **The training runs are re-measured.**
  - They are U-1's waves 1, 2 and 4 (1,920 runs, seeds 7000–7005) and M5c's waves (440 runs;
    wave 0's emulators).
  - Each run is replayed to day 316 (`--replay`). A run is deterministic for a fixed seed.
  - A replay must give the cached run's N and its count past sexual maturity on day 315 exactly.
    A run that does not is left out.
  - U-1's ensemble runs are not used: they never trained the emulators.
- **What they already show** (`--look`, before any new run; `_output/hm_record2/look.json`).
  Each line compares U-1's reading with Calhoun's.
  - Every replay matched: 1,920 of 1,920 of U-1's runs and 440 of 440 of M5c's.
  - The not-ruled-out space over the 14 targets: 17 % of the parameter box, then 33 %.
    - Where the emulated arc frequency is also at least 0.3 (where wave 5 samples): 0.65 %,
      then 1.4 %.
    - `maturity_days` there, median [5–95 %]: 62.8 [52.3, 69.4], then 61.4 [47.8, 69.3].
  - Single runs: 143 of the 1,920 show the arc. Of these:

    | | U-1's reading | Calhoun's |
    |---|---:|---:|
    | adults on day 315 within 3 sd | 5 | 88 |
    | both day-315 numbers within 3 sd | 5 | 21 |
    | within 3 sd on at least 12 of the 14 | 7 | 12 |

  - The best observed point is the same under both: the wave-2 point that became U-1's
    candidate, with the arc on 6 of 6 seeds and I₂ 1.82. Its adults on day 315 are 283 under
    U-1's reading and 122 under Calhoun's.
  - The arc stays the constraint. Over the not-ruled-out space, its emulated frequency has a
    median of 0.02.
- **Wave 5**: 120 points × seeds 7000–7005, drawn from the not-ruled-out space where the emulated
  arc frequency is at least 0.3, as U-1's wave 4 was.
- **Ensemble**: 24 points × seeds 7000–7011.
  - 6 are the best observed points of waves 1, 2, 4 and 5: the arc on at least 4 of 6 seeds,
    then the lowest second-largest implausibility.
  - 18 are drawn from the top tenth of the emulated arc frequency.
- **The candidate** is chosen by U-1's rule.
  - A member qualifies if it has the arc on at least 10 of its 12 seeds and a second-largest
    implausibility of at most 3 over the 14 targets.
  - The qualifying member with the lowest second-largest implausibility is the candidate.
  - With none qualifying, it is the lowest among members with the arc on at least 10 seeds;
    with none of those, the lowest overall.

These are training seeds, so nothing here is out-of-sample. A chain
(`scripts/record_fit2_chain.cmd`) runs wave 5, the ensemble, the candidate and the validation
without a pause, so no choice is made after seeing the fresh seeds. Its logs go to
`_output/hm_record2/`.

## Validation (registered now, before use)

- **Runs**: the candidate alone in Calhoun's pen on 48 fresh seeds, 9112–9159, 1,600 days. The
  final replica runs on the same 48 seeds as a paired comparison.
- **Measure**: for each of the 14 targets, with adults read as above: is the record inside the
  5–95 % range of the 48 runs? Where the record is contested, its own range is used.
- **Passes if** both of these hold:
  - at least 12 of the 14 are inside;
  - the arc appears in at least 43 of the 48 runs.
- **Reported either way**:
  - every target, with its median and 5–95 % range;
  - adults past sexual maturity, and the weaned N on day 315;
  - the six behaviour targets;
  - the comparison with the final replica on the same seeds.
- **Also reported, exploratory**: U-1's three validation sets (seeds 9416–9463) re-measured
  with adults read as above. These seeds are spent, so this decides nothing.

## What follows

- **If it passes**:
  - The candidate becomes `configs/universe25_record.json`, the app's Universe 25.
  - Jason asked for the Windows program only if the fit passed, and later said "Not now" to
    building it anyway. He is asked before it is built.
- **If it fails**: the better of the candidate and the final replica stays in the app, with its
  misses stated. "Better" means more of the 14 inside; the arc breaks a tie, as in U-1.
- **In both cases**:
  - The app's Universe 25 line reports adults as Calhoun counted them.
  - The frozen 2m colony stays the reference for the play research.

Every result goes into NOTES, including the targets missed.

## Outcome (2026-11-19; NOTES 2026-11-19)

- **The fit fails.** Its rule picked U-1's member again: the wave-2 point with I₂ 1.91 and the
  arc on 10 of 12 training seeds.
  - Its I₂ is set by N on days 960 and 736, not by adults.
  - On seeds 9112–9159 it has 9 of the 14 inside and the arc in 28 of 48 runs (12 and 43 needed).
- **Adults are no longer the shared miss.** Counted from 131 days, they are inside for both
  members: the candidate 110 [77, 150], the final replica 112 [69, 174].
- **The final replica is the better of the two.** On the same seeds it has 11 of 14 and the arc
  in 46 of 48.
  - It misses the peak (2,490), N on day 960 (1,320) and the last conception (day 1,096).
  - It stays the app's Universe 25, and its line in the app reports adults as Calhoun counted them.
- **Exploratory, and reported:**
  - U-1's validation sets re-measured: the final replica goes from 8 to 9 of 14 on those seeds.
  - The frozen reference colony's predictive check has the same miscount: its adults on day 315
    are 40 [22, 61] counted from 131 days. Its "12 of 15" would read 11 of 15. Whether to
    restate it is Jason's call.
