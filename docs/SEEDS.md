# Seed ledger

Which seeds exist for what, and which have already been read. Created 2026-11-09 (Tier 0 of
`docs/REVIEW_2026-11-09.md`); add a line whenever a seed range is used for something new. A seed
read once for a decision is no longer "fresh" for that kind of decision.

The config refuses seeds outside [7000, 10000) and the reserved band 5000–5999
(`SimConfig._seed_range`). Detector validation seeds (synthetic colonies) are separate numbers
passed to the generator, not simulation seeds.

## Simulation seeds

| range | role | used so far |
|---|---|---|
| 7000–7002 | training / development | calibration objective (phases 2i–2m, CMA-ES `--train-seeds`); every phase-4 development reading and development guard (P4-8, P4-12 … P4-14); relief-matching scan (P4-14); golden hashes (7000) |
| 7003–7005 | training / development | v6 simulator negative control (P4-11) |
| 7006–7008 | training / development | v7 simulator negative control (P4-13) |
| 7009 | training / development | nursery pre-training worlds only |
| 7000–7009 | nursery worlds | every `pretrain_v*` run cycles nursery episodes over these sim seeds |
| 7000–7011 | calibration adjudication | `scripts/seed_eval.py` 12-seed scoring since phase 2k. **7010 and 7011 lie outside the 7000–7009 training band**, and the block includes the training seeds 7000–7002, so this scoring is not out-of-sample |
| 7100 | unit tests | `tests/` |
| 8000–8002 | evaluation, **used for calibration** | `scripts/calibrate_optuna.py --heldout` default; held-out losses informed calibration choices (phases 2b–2h, e.g. NOTES "held-out 8000–8002"). Not fresh for any claim about fit to the record |
| 8000–8011 | evaluation (arm comparisons only, PLAN §15.3) | P4-1 guard (random MLP, 2026-11-04); H-d guard of `pretrain_v2` (2026-11-07); heuristic K = 12 guards (P4-8); H-e sweep (2026-11-08, rules v5, re-read under v6) |
| 9000–9047 | calibration reference (Tier 1, preregistered 2026-11-09) | A/A check of guard v2 and the posterior predictive check, frozen K = 1 colony |
| 9048–9095 | calibration reference (Tier 1) | posterior predictive check with the removal event |
| 9500–9504 | detector negative control (Tier 1) | rules v8 simulator negative control (random v5 nets, init 7005 / 7006) |
| 9100–9111 | evaluation, P4-15 (preregistered 2026-11-10) | the consequence-sensitivity test (A1 vs random net); the first decisive use of the band |
| 7000–7011 | replica v2 development (M1–M8, M5b–M5e) | every replica milestone report (M1–M4, M7, M8; the M8 pre-spec diagnostic on 7000–7001) and the M5, M5b, M5c, M5d and M5e history-matching waves and ensembles (training seeds; not out-of-sample) |
| 9200–9247 | replica v2 M6 validation (registered 2026-11-11, before use) | the M5 ensemble in Calhoun's pen, one member per seed: 90 % prediction intervals against the record |
| 9248–9295 | replica v2 M6 sibling universes (registered 2026-11-11, before use) | 1, 2, 4 and 8 open cells, 12 seeds each in that order (Calhoun 1971 Fig 3) |
| 9296–9307 | replica v2 M6 Marsden transfer (registered 2026-11-11, before use) | the best M5 member: transfer at day 870 into a fresh 4-cell pen |
| 9308–9355 | replica v2 M5b validation (registered 2026-11-12, before use) | the M5b ensemble (no hopper facilitation) in Calhoun's pen, one member per seed |
| 9356–9403 | replica v2 M5b sibling universes (registered 2026-11-12, before use) | 1, 2, 4 and 8 open cells, 12 seeds each in that order; a consistency check (the siblings motivated M5b) |
| 9404–9415 | replica v2 M5b Marsden transfer (registered 2026-11-12, before use) | the best M5b member |
| 9505–9552 | replica v2 M5c validation (registered 2026-11-12, before use) | the M5c ensemble (M5b plus maternal-care transmission) in Calhoun's pen, one member per seed |
| 9553–9600 | replica v2 M5c sibling universes (registered 2026-11-12, before use) | 1, 2, 4 and 8 open cells, 12 seeds each in that order; a consistency check |
| 9601–9612 | replica v2 M5c Marsden transfer (registered 2026-11-12, before use) | the best M5c member |
| 9613–9660 | replica v2 M5d validation (registered 2026-11-12, before use) | the M5d ensemble (replicate-seed history matching) in Calhoun's pen, one member per seed |
| 9661–9708 | replica v2 M5d sibling universes (registered 2026-11-12, before use) | 1, 2, 4 and 8 open cells, 12 seeds each in that order; a consistency check |
| 9709–9720 | replica v2 M5d Marsden transfer (registered 2026-11-12, before use) | the best M5d member |
| 9721–9768 | replica v2 M5e validation (registered 2026-11-12, before use) | the M5e ensemble (M5d with M8 on) in Calhoun's pen, one member per seed |
| 9769–9816 | replica v2 M5e sibling universes (registered 2026-11-12, before use) | 1, 2, 4 and 8 open cells, 12 seeds each in that order; a consistency check |
| 9817–9828 | replica v2 M5e Marsden transfer (registered 2026-11-12, before use) | the best M5e member |
| 9829–9876 | replica v2 final-replica comparison (registered 2026-11-13, before use) | M5d's best member and M5e's member A, each alone in Calhoun's pen on all 48 seeds (paired) |
| 9877–9888 | evaluation, H-g and the playground-off arm (registered 2026-11-13, before use) | three policies × playground on / off, 1,600 d, the same seeds in every arm (`PHASE4_DESIGN.md` §4.3) |
| 7000–7009 | `evo` pre-evolution (P4-4, registered 2026-11-13) | the founding epochs of the 8 lineages cycle over these sim seeds; lineage ℓ's own streams come from `SeedSequence([7000 + ℓ − 1, stream])` |
| 9889–9904 | evaluation, `evo` and H-h (registered 2026-11-13, before use) | 2 seeds per lineage (9889 + 2(ℓ − 1) and the next), paired across SEL, NEU and GEN0; the need-driven control on all 16 (`PHASE4_DESIGN.md` §4.4) |
| 9905–9928 | evaluation, the norm-matched check of criterion 3 and H-i (registered 2026-11-13, before use) | colony c on seed 9904 + c, the same seed in S0, S½ and S1; the jump from `SeedSequence([seed, 7_600_001])` (`PHASE4_DESIGN.md` §4.5) |
| 7000–7009 | `evo` scarce pre-evolution (P4-19, registered 2026-11-14) | the scarce lineages' founding epochs cycle over these sim seeds as H-h's do; founder draws from `SeedSequence([7000 + ℓ − 1, 7_700_001])`, policy streams keyed (ℓ, e, 2) |
| 9929–9944 | evaluation, SCARCE-PG `evo` and H-j (registered 2026-11-14, before use) | 2 seeds per lineage (9929 + 2(ℓ − 1) and the next), paired across SCARCE, ABUND and NEU (`PHASE4_DESIGN.md` §4.6) |
| 7000–7009 | `evo` small-meal pre-evolution (P4-20, registered 2026-11-15) | the small-meal lineages' founding epochs cycle over these sim seeds as H-h's do; founder draws from `SeedSequence([7000 + ℓ − 1, 7_800_001])`, policy streams keyed (ℓ, e, 3). The design's pilot used the dev-only streams 7_799_001 and (ℓ, e, 99) |
| 9945–9960 | evaluation, small-meal `evo` and H-k (registered 2026-11-15, before use) | 2 seeds per lineage (9945 + 2(ℓ − 1) and the next), paired across SMALL, ABUND and NEU (`PHASE4_DESIGN.md` §4.7) |
| 7000–7009 | `evo` late-reflex pre-evolution (P4-21, registered 2026-11-16) | the two late lines' founding epochs cycle over these sim seeds as H-h's do; founder draws from `SeedSequence([7000 + ℓ − 1, 7_900_001])` (LF) and `SeedSequence([7000 + ℓ − 1, 8_000_001])` (LS), policy streams keyed (ℓ, e, 4) and (ℓ, e, 5). The design's development look used the dev-only key (ℓ, 0, 99) on seed 7000, and its pilot the dev-only streams 7_899_001 and (ℓ, e, 98) |
| 9961–9976 | evaluation, late-reflex `evo` and H-l (registered 2026-11-16, before use) | 2 seeds per lineage (9961 + 2(ℓ − 1) and the next), paired across LS, LF, NEU and ABUND (`PHASE4_DESIGN.md` §4.8) |
| 9416–9463 | record fit validation (registered 2026-11-18, before use) | the record fit's candidate and the final replica, each alone in Calhoun's pen on all 48 seeds (paired; `docs/RECORD_FIT.md`); the chain's member (a bug); all three replayed to day 316 for Calhoun's adults (U-3, exploratory, 2026-11-19) |
| 9112–9159 | record fit 2 validation (registered 2026-11-19, before use) | the record fit 2 candidate (U-1's member again) and the final replica, each alone in Calhoun's pen on all 48 seeds (paired; `docs/RECORD_FIT_2.md`; read 2026-11-19) |
| 9096–9099, 9160–9199, 9464–9499, 9977–9999 | **reserved, fresh** | substrate-variant confirmation (24 seeds per variant) and future references |

## Random-network init seeds (`MlpFrozenPolicy.random_init(s)`)

| seed | used for |
|---|---|
| 7000 | the random comparison nets of every reading (v2 … v5) |
| 7001, 7002 | v6 negative control |
| 7003, 7004 | v7 negative control |
| 7005, 7006 | v8 / v9 negative control (Tier 1) |
| 7007 | P4-15 random comparison net R |
| 7100 | unit tests |

Known stream collision, kept for bit-identity: `random_init(s)` draws its weights from
`make_rng(s + 1_000_003 + 1)`, which is also the action-sampling stream of a frozen policy on
simulation seed s + 1. So `random_init(7000)` run on seed 7001 samples actions with the stream
that made its weights. With near-uniform random logits (last-layer gain 0.01) the effect should
be negligible, but new streams should come from `np.random.SeedSequence([seed, stream_id])`.

## Detector validation splits (synthetic colonies)

| range | rule set |
|---|---|
| 100–106 | development (every version) |
| 10,000+ | v1 |
| 20,000+ | v2 |
| 30,000+ | v3 |
| 40,000+ | v4 |
| 50,000+ | v5 |
| 60,000+ | v6 |
| 70,000+ | v7 |
| 80,000+ | next (v8) |

## Random streams of one run

| stream | made from | used for |
|---|---|---|
| simulator | `make_rng(seed)` | all of the colony's biology and movement |
| free-time sub-steps | `make_rng(seed + 2_000_003)` | P4-8 sub-steps, only when K > 1 |
| body | `SeedSequence([seed, 9_100_001])` | body size frames, coat inheritance and the sire of each pregnancy for the coat (agents/body.py, 2026-11-17). Never the simulator's stream, so the frozen colony is bit-identical with it. |
