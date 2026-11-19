# Record fit 3 — choosing the candidate by the bar's own measure

Jason, 2026-11-19: "KEEP GOING?", after record fit 2 (U-3) failed. This page is the
preregistration of record fit 3 (TASKS U-4). It was written and committed before any new
simulation run. The only runs before it were replays: the first 316 days of stored training runs,
re-measured.

## Why a third fit

- **The same member was chosen twice.** U-1 and U-3 both chose by the second-largest
  implausibility (I₂) on 12 training seeds, and both picked the member with I₂ 1.91 and the arc
  on 10 of 12 seeds.
  - On fresh seeds its arc held in 28 of 48 runs, twice.
  - It had 8 and 9 of the 14 record values inside.
- **On those 12 seeds the final replica ties with it.**
  - Its I₂ is 1.93, with the arc on 11 of 12 seeds.
  - On fresh seeds its arc held in 46 of 48 runs, twice, with 9 and 11 of 14 inside.
  - It was never a candidate: it belongs to M5d's ensemble, not U-1's or U-3's.
- **Twelve seeds are too few.** They cannot separate an arc in 58 % of runs from one in 96 %, and
  I₂ is not the measure the bar uses.
- **So this fit changes the choice, not the model.**
  - It chooses among members already run, by the validation's own measure, on 48 training seeds.
  - It spends fresh seeds only on a member that meets the bar there.

## The pool

- **Who is in it.** Every member that M5d, U-1 and U-3 ran on the 12 training seeds 7000–7011
  with M5d's settings: 68 distinct members.
- **How they are measured.** Adults on day 315 are counted as Calhoun counted them, aged 131 days
  or more (`docs/RECORD_FIT_2.md`).
  - Runs without that count were replayed to day 316: 516 replays, each checked against its
    stored run. All matched.
- **Members already validated on fresh seeds are not candidates.** All three fell below the bar,
  and testing them again until one passes would be cherry-picking.
  - the final replica: 9 and 11 of 14;
  - U-1's member: 8 and 9;
  - U-1's chain member: 9.
- **What the pool shows** (`scripts/record_fit3.py --pool`, before any new run;
  `_output/hm_record3/pool.json`). Scores are on each member's 12 seeds.
  - 17 members have the arc on at least 10 of 12 seeds.
  - The most record values inside: 9 of 14, U-1's chain member. Then 8, the final replica.
  - Among members not validated before, at most 7.
  - Misses shared across the pool:
    - N on day 960, in 58 of the 68 members;
    - the peak, in 50;
    - the last conception, in all six candidates.

## The candidates

The six members not validated before that have the arc on at least 10 of 12 seeds. They are
ranked by the record values inside the 5–95 % range of their 12 runs, then by the arc count, then
by I₂.

| rank in the pool | inside, of 14 | arc, of 12 | I₂ | from |
|---:|---:|---:|---:|---|
| 8 | 7 | 12 | 2.55 | U-1 and U-3 |
| 9 | 7 | 11 | 4.54 | M5d |
| 11 | 7 | 10 | 2.18 | U-3 |
| 17 | 6 | 11 | 2.87 | U-1 and U-3 |
| 18 | 6 | 10 | 3.59 | U-1 |
| 30 | 5 | 11 | 3.65 | U-3 |

## Selection, on training seeds

- **More seeds.** Each candidate runs 36 more training seeds, 7012–7047: 1,600 days in Calhoun's
  pen with M5d's settings.
- **The measure.** On its 48 training seeds (7000–7047), each candidate is scored by the
  validation's measure, as U-1 and U-3 were:
  - how many of the 14 record values fall inside the 5–95 % range of its runs, the record's own
    range where it is contested;
  - in how many runs the arc appears.
- **The rule.** A candidate qualifies if it meets the bar there: at least 12 of 14 inside and the
  arc in at least 43 of 48. The candidate is the qualifier with the most inside, then the most
  arcs, then the lowest I₂ on its 48 seeds.
- **Stop rule.** If no candidate qualifies, the fit fails and no fresh seed is used.

A chain (`scripts/record_fit3_chain.cmd`) runs the selection and, when a candidate qualifies, the
validation, without a pause. Its logs go to `_output/hm_record3/`.

## Validation (registered now, before use)

- **Runs**: the candidate alone in Calhoun's pen on 48 fresh seeds, 9160–9199 and 9464–9471,
  1,600 days. The final replica runs on the same seeds as a paired comparison.
- **Measure**: for each of the 14 targets, with adults counted as Calhoun counted them: is the
  record inside the 5–95 % range of the 48 runs? Where it is contested, its own range is used.
- **Passes if** both of these hold:
  - at least 12 of the 14 are inside;
  - the arc appears in at least 43 of the 48 runs.
- **Reported either way**:
  - every target, with its median and 5–95 % range;
  - adults past sexual maturity, and the weaned N on day 315;
  - the six behaviour targets;
  - the comparison with the final replica on the same seeds.

## What follows

- **If it passes**:
  - The candidate becomes `configs/universe25_record.json`, the app's Universe 25.
  - Jason is asked before the Windows program is built.
- **If it fails**, at the stop rule or the validation:
  - The final replica stays in the app, with its misses stated.
  - The fits so far point to limits in the model rather than in the choice. Whether to change the
    model is Jason's call.

Every result goes into NOTES.
