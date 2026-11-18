# Record fit — Calhoun's pen, fitted to the record's numbers

Jason, 2026-11-18: "we need super accurate universe 25 simulation (like anyone can use it)".
Of three aims he chose **the record's numbers in Calhoun's own pen**, as an installable app,
private first. This page is the fit's preregistration: written and committed before any run.

## Why a new fit

- The reference colony (frozen 2m) fits Calhoun's population curve, but in a simplified pen:
  a grid of square cells, nests as floor points, and a playground Calhoun never had (README,
  "How close is it to the original?").
- Replica v2 put the model in Calhoun's own pen and ended on 2026-11-13. It was scored on 20
  targets, 6 of them behaviour categories that never appeared together with the arc.
- Its final replica (M5d's best member) has **9 of the 14 population and timeline targets**
  inside on 48 fresh seeds (NOTES 2026-11-13). It misses:
  - adults on day 315 (297 against 150);
  - the peak (2,519 against 2,200);
  - N on day 960 (1,302 against 1,650);
  - the last surviving birth (day 687 against 600);
  - the last conception (day 1,093 against 920).
- This fit asks only for the record's numbers. The behaviour targets are reported, not fitted.

## What is fitted

- **The pen**: replica v2's (`configs/replica_v2.yaml`).
  - 16 triangular cells and four tunnels of four box levels per cell.
  - Wall hoppers and water platforms with their capacities.
  - Box feeding until day 160, then the food is moved out.
  - About 150 mice removed after day 1,000.
  - No playground.
- **The settings**: M5d's.
  - Hopper facilitation is off.
  - Maternal-care transmission is on (M7).
- **The parameters**: M5d's 22, with M5d's ranges (`scripts/history_match.py`, `PARAMS_M5` and
  `PARAMS_M7`).

## The 14 targets

The record's population and timeline numbers, each with replica v2's observation and
model-discrepancy sd (`scripts/history_match.py`, `OUTPUTS`):

| target | record |
|---|---:|
| first litters (day) | 50–104 (contested) |
| N on day 315 | 620 |
| adults on day 315 | 150 |
| peak N | 2,200 |
| plateau onset (day) | 560 |
| N on day 736 | 2,056 |
| N on day 811 | 1,871 |
| N on day 960 | 1,650 |
| doubling time, phase B (days) | 55 |
| doubling time, phase C (days) | 105–145 (contested) |
| last surviving birth (day), given the arc | 600 |
| last conception (day), given the arc | 920 |
| N on day 1,444, given the arc | 122 |
| N on day 1,588, given the arc | 27 |

**The arc**: growth above 1,800, at least 150 days from the last surviving birth to the last
conception, and fewer than 300 mice on day 1,588.

**Reported, not fitted**: the male share on days 315 and 1,444, empty boxes on day 560, the
withdrawn on day 560, the never-fought-or-mated share on day 800, and the brood groups on day
315.

## Method

This is M5d's history matching (`scripts/history_match_rep.py`), with the implausibility taken
over the 14 targets only. `scripts/record_fit.py` runs it.

- **Waves 1–3** are M5d's runs: the same parameters, settings and seeds (7000–7005).
  `--init` copies them into `_output/hm_record`.
- **What they already show** (`--fit`, before any new run):
  - Over the 14 targets, about a fifth of the parameter box is not ruled out.
  - The arc is the constraint: its emulated frequency there has a median of 0.03.
  - One wave-2 point shows the arc on all 6 of its seeds, with a second-largest implausibility
    of 1.82.
- **Wave 4**: 120 points × seeds 7000–7005. They are drawn from the not-ruled-out space where
  the emulated arc frequency is at least 0.3, because the arc is required.
- **Ensemble**: 24 points × seeds 7000–7011.
  - 6 are the best observed points of waves 1–4: the arc on at least 4 of 6 seeds, then the
    lowest second-largest implausibility.
  - 18 are drawn from the top tenth of emulated arc frequency, as in M5d.
- **The candidate**:
  - A member qualifies if it has the arc on at least 10 of its 12 seeds and a second-largest
    implausibility of at most 3 over the 14 targets.
  - The qualifying member with the lowest second-largest implausibility is the candidate.
  - With none qualifying, it is the lowest among members with the arc on at least 10 seeds;
    with none of those, the lowest overall.

These are training seeds, so nothing here is out-of-sample. A chain
(`scripts/record_fit_chain.cmd`) runs wave 4, the ensemble, the candidate and the validation
without a pause, so no choice is made after seeing the fresh seeds. Its logs go to
`_output/hm_record/`.

## Validation (registered now, before use)

- **Runs**: the candidate alone in Calhoun's pen on 48 fresh seeds, 9416–9463, 1,600 days.
  M5d's best member, the final replica, runs on the same 48 seeds as a paired comparison.
- **Measure**: for each of the 14 targets, is the record inside the 5–95 % range of the 48
  runs (the record's own range where it is contested)?
- **Passes if** both of these hold:
  - at least 12 of the 14 are inside;
  - the arc appears in at least 43 of the 48 runs.
- **Reported either way**:
  - every target, with its median and 5–95 % range;
  - the six behaviour targets;
  - the comparison with the final replica on the same seeds.

## What follows

- **If it passes**: the candidate becomes `configs/universe25_record.json`, the installable
  app's "Universe 25 (Calhoun's pen)".
- **If it fails**: the better of the candidate and the final replica (more of the 14 inside)
  goes into the app with its misses stated, and Jason decides what comes next.
- The frozen 2m colony stays the reference for the play research in either case.

Every result goes into NOTES, including the targets missed.

## Outcome (2026-11-19; NOTES 2026-11-19)

- **The fit fails.** The rule's member has 8 of the 14 inside on seeds 9416–9463, and the arc in
  28 of 48 runs. The final replica has 8 of 14 and the arc in 46 on the same seeds.
- **A deviation, corrected.** The chain scored the six observed ensemble members on 6 of their 12
  seeds (a grouping bug), so it validated a member the rule would not have chosen: 9 of 14, the
  arc in 43 of 48.
  - The fix in `scripts/record_fit.py` re-applies the rule to the same training runs.
  - The rule's member was then validated on the same 48 seeds.
- **What followed.** The candidate and the final replica tie on the 14 targets; the arc decides
  for the final replica.
  - It stays the app's Universe 25, and the app now states its misses.
  - The Windows program was not built (Jason: only if the fit passed).
