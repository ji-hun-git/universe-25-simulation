# TASKS.md — prioritized task list

Each card gives the goal, the files, the acceptance criteria and the task.  
Before starting a card, read `HANDOFF.md`, `PLAN.md`, `NOTES.md` and the card. Obey H2 (no play reward).

Legend: **P0** blocking · **P1** high · **P2** medium · **P3** polish

---

## P0-1 — Biology calibration toward Calhoun landmarks

> **Status 2026-10-30:** pup-mill bug fixed, developmental-imprinting collapse
> mechanism added, recalibrated — see `NOTES.md` "Phase 2b" for the before/after table. Remaining
> work on this card = whatever landmark is still off in that table.

**Goal:** Reduce mean relative landmark error from ~1.08; get first litters nearer day 104, N@315 nearer 620, peak nearer day 560, and either a collapse or an honest negative with mechanism notes.

**Files:** `configs/default.yaml`, `src/universe25/sim.py`, `src/universe25/config.py`, `src/universe25/calib/*`, `scripts/calibrate_optuna.py`, `NOTES.md`

**Acceptance criteria:**
- Documented parameter change set + seed 7000 1600d (or agreed shorter calib protocol) comparison table in `NOTES.md`
- mean_rel_error improved vs 1.08 **or** clear ablation showing which landmark is infeasible under current mechanisms
- No NaNs; tests still pass
- No play reward terms introduced

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python tests\run_tests.py
python scripts\calibrate.py --metrics _output\<run>\metrics.parquet --out _output\<run>\calibration.json --run-json _output\<run>\run.json
```

**Task:**
```
Read HANDOFF.md + NOTES.md. Phase-1 1600d abundant run peaked at N≈1715 on day~1395 (mean_rel_error≈1.08) with NO collapse. Tune biology/density-stress/mortality/breeding so landmarks move toward Calhoun 1973 (first litters~104, N@315~620, peak~2200@~560, collapse after). Use calib helpers if useful. Keep H2. Write honest before/after table to NOTES.md. Pathspec commits only.
```

---

## P0-2 — Warp ↔ NumPy parity for tick kernels

> **Status 2026-10-30:** `tests/test_biology_guards.py::test_warp_density_stress_parity` covers the
> density-stress + imprinting kernel (max |Δ| ≈ 3e-8). Still open: mortality (different RNG streams —
> compare hazards, not draws) and `update_cells`.

**Goal:** Device Warp path matches NumPy reference on a fixed seed for stress/mortality/cells (and any kernels you own), within agreed float tolerance.

**Files:** `src/universe25/warp_kernels/*`, `src/universe25/sim.py`, `tests/test_warp_smoke.py` (add parity test), `docs/NSIGHT.md`

**Acceptance criteria:**
- Automated parity test seed 7100 (or 7000 short run)
- Document sync vs graph behavior; no silent fallback without logging
- `tests/run_tests.py` green

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python tests\run_tests.py
python main.py --seed 7000 --out _output\warp_parity --backend warp --device cuda --days 5 --max-agents 1024
```

**Task:**
```
Read HANDOFF.md and docs/NVIDIA_STACK.md. Add/extend Warp kernel parity tests vs NumPy host for the post-step (and any tick pieces already on device). RTX 5080 sm_120. Fail loud on mismatch. Update NOTES with parity method. No play reward. Pathspec commits.
```

---

## P0-4 — dt-invariance: action persistence + per-day event effects

> **Status 2026-10-30: DONE for the arc** — per-decision effects × ref/tpd,
> √-scaled random walks, resolution-free movement reach (`SimConfig.ticks_per_day_ref = 6`).
> Peak 2261 / 2345 / 2314 and collapse onset 1228 / 1225 / 1203 at 6 / 12 / 24 tpd; 6-tpd
> trajectory bit-identical to the calibration. **Open residual:** early growth a few % faster per
> day at finer ticks (N@315 672 / 753 / 928) because per-tick MATE probability depends on the
> drive sawtooth amplitude. Follow-up: make conception purely daily (remove the per-tick ACT_MATE
> conception side effect), then re-calibrate. See `NOTES.md` "Phase 2c".

**Goal:** The calibrated biology must give the same trajectory at 6 and 24 ticks/day. Before 2c the
same parameters gave peak 2261 (6 tpd) vs 1088 (24 tpd) — see `NOTES.md` Phase 2b/2c.

**Files:** `src/universe25/sim.py` (`_select_actions`, `_execute_actions`, `_passive_nurse`,
`_nurse`, `_aggress`, `_density_stress`), `configs/default.yaml`, `NOTES.md`

**Acceptance criteria:**
- Agents commit to a movement target (nest / hopper / object) until arrival instead of re-drawing
  every tick, or movement completes within one decision regardless of `ticks_per_day`
- Per-event effects (nurse amounts, wound +0.15, ACT_NEST −0.05 stress, social −0.05) scaled so
  daily totals do not depend on `ticks_per_day`
- 1600-d seed-7000 landmarks at 24 tpd within ~10 % of the 6-tpd run (re-calibrate if needed with
  `scripts/calibrate_optuna.py --workers 14`)
- Determinism test still green; H2 clean

**Task:**
```
Read HANDOFF.md + NOTES.md "Phase 2b" (dt-invariance gap). Make the Universe25 tick dt-invariant:
action/target persistence and per-day scaling of per-event effects. Compare 6 vs 24 ticks/day on
seed 7000 for 1600 d, table in NOTES. Re-run CMA-ES from configs/calibrated_calhoun.yaml if the
landmarks move. No play reward. Pathspec commits.
```

---

## P0-3 — Keep master green while dual-editing

**Goal:** Ensure concurrent phase-2 work does not break determinism/conservation.

**Files:** `tests/*` only if needed; otherwise verify only

**Acceptance criteria:** `python tests\run_tests.py` exit 0 on clean tree after rebase

**Task:**
```
Pull --rebase origin master on universe25-play. Run tests\run_tests.py. If failures, fix minimal regressions without redesign. Report commit HEAD and test output.
```

---

## P1-1 — Scarcity arm config + smoke

**Goal:** Add `TRACK-E-U25-SCARCE-PG` config (seed 7002) with finite food refill; smoke 30–100 days; log aggression proxy vs abundant.

**Files:** `configs/scarce.yaml` (new), `configs/default.yaml` resources, `NOTES.md`

**Acceptance criteria:**
- Scarce run completes; aggression/stress metrics higher than abundant smoke (directionally)
- Playground still has **no** play reward
- Calibration script still runs (landmarks may fail — OK)

**Test command:**
```powershell
$env:PYTHONPATH = "$PWD\src"
python main.py --seed 7002 --out _output\scarce_smoke --config configs\scarce.yaml --days 50
python tests\run_tests.py
```

**Task:**
```
Implement scarcity resource mode + configs/scarce.yaml for arm TRACK-E-U25-SCARCE-PG (seed 7002). Compare aggression/stress vs abundant smoke in NOTES. H2: no play reward. Link to Leibo Gathering as contrast, not as play evidence.
```

---

## P1-2 — Abundance × playground OFF arm

**Goal:** Run `TRACK-E-U25-ABUND-NOPG` seed 7001; compare free-choice V and playground occupancy metrics (should be ~0 / N/A) vs PG ON.

**Files:** run scripts or CLI `--playground off`; `NOTES.md`

**Acceptance criteria:** Side-by-side table of V, G, occupancy, peak N

**Task:**
```
Run abundant playground OFF (seed 7001) vs existing ON (7000) at a comparable day budget. Table V/G/occupancy/peak N in NOTES. Do not change PlayScore formulas except bugfixes labelled unvalidated.
```

---

## P1-3 — Device-resident action select (perf)

> **Profile 2026-10-30 (NumPy, 6 ticks/day, N 340→2140, days 250–400):** 16.4 ms/tick.
> `_passive_nurse` 38 % (Python loop over mothers × pups), `_execute_actions` 50 % (per-agent
> forage/drink loops, `_aggress` O(capacity) per attacker, per-tick `np.array` of food/water xy),
> `_select_actions` 4 %. The host Python loops, not the vectorized math, are the bottleneck —
> vectorize those first (keep the NumPy trajectory hash identical, or re-calibrate), then Warp.

**Goal:** Move utility action selection onto Warp to escape hybrid sync tax; keep NumPy parity.

**Files:** `warp_kernels/kernels.py`, `engine.py`, `sim.py`, `docs/NSIGHT.md`

**Acceptance criteria:**
- Microbench shows improved hybrid or documents remaining host bottlenecks
- Parity test for action histograms / traj hash policy agreed in NOTES
- CUDA Graph optional

**Task:**
```
Phase-3-perf slice: port action utility select to Warp on RTX 5080. Keep NumPy reference. Update NSIGHT.md benches. H2 unchanged. Pathspec commits.
```

---

## P1-4 — Newton playground rigid bodies (stub → step)

**Goal:** Step balls/ramps with Newton or `warp.sim`; mice apply impulses; kinematic fallback remains.

**Files:** `src/universe25/nvidia/newton_playground.py`, world play objects, tests

**Acceptance criteria:**
- Playground objects move under contact in a smoke demo
- Still **no** play reward — manipulate remains curiosity/boredom
- Graceful skip if Newton missing

**Task:**
```
Wire Newton playground stepping behind a feature flag. Document in NVIDIA_STACK.md. Must not introduce play objective. Add smoke test that skips without Newton.
```

---

## P2-1 — Editorial WebGPU / canvas top-down viewer

**Goal:** Top-down 16-cell pen with role-colored dots, playground AABB, stress heatmap; palette from HANDOFF §8.

**Files:** new `viewer/` or `web/` (propose structure), snapshot JSON/bin from `io/snapshots.py`

**Acceptance criteria:**
- Loads a run snapshot; plays scrub timeline
- Colors: paper #F4F0E6, ink #1A1A1A, stress #8B1E1E, nest #2F5D50
- **No** purple/glass/AI-slop aesthetics
- README screenshot section

**Task:**
```
Build a minimal top-down Universe25 viewer consuming existing snapshots. Follow HANDOFF visual tokens strictly. Prefer uPlot for charts later; viewer first. No AI-looking chrome.
```

---

## P2-2 — Dashboard (uPlot + restyled shadcn)

**Goal:** Population curve with 4 phases shaded; conception rate; wounds; nest occupancy; % withdrawn; V and G gates.

**Files:** `viewer/` dashboard route; reads `metrics.parquet` (via pre-exported JSON/CSV if browser)

**Acceptance criteria:** Matches visual tokens; works offline on a static export; documents export script

**Task:**
```
Create scientific editorial dashboard for metrics.parquet exports. uPlot charts, phase shading, PlayScore components clearly labelled UNVALIDATED. Palette from HANDOFF. No default shadcn violet.
```

---

## P2-3 — H2 static audit in CI/tests

**Goal:** Test that fails if reward/utility strings match play/bout/motif/exaggeration in agent code paths.

**Files:** `tests/test_h2_no_play_reward.py`, `agents/drives.py`

**Acceptance criteria:** Audit runs via `tests/run_tests.py`; documents allowlist if any

**Task:**
```
Add a deterministic H2 linter test scanning src/universe25 for forbidden play-reward identifiers in reward/utility contexts. Keep ACT_MANIPULATE allowed. Wire into run_tests.py.
```

---

## P2-4 — PlayScore components: real D and S (still unvalidated)

**Goal:** Replace stand-ins with clearer JS-divergence D and recurrence×entropy S; keep labels `_unvalidated`; agents still do not optimize.

**Files:** `src/universe25/metrics/playscore.py`, logger schema, NOTES

**Acceptance criteria:**
- Formula documented; unit-level smoke on synthetic action streams
- Schema changelog in NOTES
- Optimize-vs-eval reminder in docstring

**Task:**
```
Upgrade PlayScoreAccumulator D and S toward gan’s definitions without validating them. Keep F,V,G. Never feed PlayScore into action selection. Tests for accumulator math.
```

---

## P3-1 — RL vec env skeleton (Isaac Lab / Gymnasium style)

**Goal:** Flesh out `rl_env_spec.py` into a thin Gymnasium-compatible stub with forbidden reward terms enforced.

**Files:** `nvidia/rl_env_spec.py`, optional `env/gym_universe25.py`

**Acceptance criteria:**
- `reward_terms_forbidden` enforced by assert
- Allowed: survival, homeostasis, generic curiosity — **not** play
- No training loop required yet

**Task:**
```
Implement a Gymnasium-shaped Universe25 vec env stub per rl_env_spec.py. Enforce H2 forbidden rewards. Document observation layout. No PPO training in this task.
```

---

## P3-2 — Baseline runners (PPO / ICM / RND / random) — eval PlayScore only

**Goal:** Training entrypoints that optimize allowed rewards; log PlayScore eval-only.

**Files:** new `baselines/`, PLAN.md arms update

**Acceptance criteria:**
- Random + at least one learning baseline runs smoke days
- PlayScore not in loss
- Seeds 7000–7009 respected

**Task:**
```
Add baseline smoke runners (random required; PPO or ICM optional if deps allow). PlayScore eval-only. Update PLAN arms. Do not install into shared venv without approval — use existing torch if present.
```

---

## P3-3 — Spinka transfer test harness (protocol only → minimal impl)

**Goal:** Pre-commit protocol: push/friction/limb perturbation recovery comparison for agents with high vs low prior playground exposure.

**Files:** `docs/SPINKA_PROTOCOL.md` (new), optional stub runner

**Acceptance criteria:** Protocol with seeds, metrics, stop rules, negative-result language; no overclaim

**Task:**
```
Write docs/SPINKA_PROTOCOL.md pre-registering the transfer test. Optional stub that applies kinematic perturbations. Cite Spinka-style prediction without claiming we measured it yet.
```

---

## P3-4 — USD / Omniverse path polish

**Goal:** Export animated agent points to USDA sequence or time samples; document Omniverse open steps.

**Files:** `nvidia/usd_export.py`, `docs/NVIDIA_STACK.md`

**Acceptance criteria:** Static pen + sample agent layer exports; skip without pxr

**Task:**
```
Extend USD export with agent point samples from a short run. Document viewer steps. Optional path only.
```

---

## P3-5 — README research polish (public-facing later)

**Goal:** When Jason is ready to open the repo: abstract, figure, calibration honesty, how to cite.

**Files:** `README.md` only

**Acceptance criteria:** No inflated claims; references complete; quickstart accurate

**Task:**
```
Rewrite README for research clarity: claim, non-goals, phase status, honest calibration table, visuals intent, refs. Keep MIT. Do not claim play emerged.
```

---

## Quick checks

**Status digest**
```
Summarize HEAD commit, NOTES latest run, open P0 tasks, and whether calibration or Warp parity is more blocking. No code changes.
```

**H2 audit now**
```
Grep src/universe25 for play/bout/motif/exaggeration in reward/utility contexts. Report findings only.
```

**Rebase & test**
```
git pull --rebase origin master; python tests\run_tests.py; report.
```
