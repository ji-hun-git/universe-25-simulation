# HANDOFF — universe25-play

> **Audience:** collaborators.
> **Repo (private):** https://github.com/ji-hun-git/universe25-play  
> **Local path (lab PC):** `C:\Users\user\Projects\universe25-play`  
> **Owner:** Jason (ji-hun-git) · **Research partner:** gan  
> **Date:** 2026-10-30 (Asia/Seoul) · **Phase:** 1 complete; **phase 2 calibration done (2b: mean landmark error 0.14, emergent collapse)**; Warp parity partial; phase 3 (visuals) and phase 4 (play module) not started

Read this file first. Then read `PLAN.md`, `NOTES.md`, `docs/NVIDIA_STACK.md`, `docs/TASKS.md`. Follow `CONTRIBUTING.md` for day-to-day rules.

---

## 0. One-sentence mission

Build a **research-grade Universe 25 (Calhoun 1973) environment** with an optional **playground**, calibrate it to Death Squared landmarks, then ask whether **play-like behavior emerges in learning agents under abundance vs survival** — scored with **Burghardt’s 5 criteria** and a **provisional PlayScore** — with **no LLM agents, no imitation / behavior cloning, and no play reward**.

---

## 1. Research question (locked)

**Core claim (gan + Jason):**  
Play emerges in learning agents (no LLM, no imitation or behavior-cloning data) under **abundance** versus a **survival** world, scored with Burghardt’s 5 criteria. In the **same** setup we compare:

1. **Calhoun-style collapse** (behavioral sink under utopia density), and  
2. The **play bloom** predicted by surplus-resource theory (Auerbach, Kanarek & Burghardt 2015).

**Independent variables (sweep):**  
`abundance × density × toys × unpredictability`

**Play types to score (later module):**  
object · locomotor · social (role reversal, self-handicapping, play invitation) · rule play

**Burghardt’s 5 criteria (detection, not reward):**  
1. Incomplete / exaggerated / modified vs “serious” form  
2. Repeated but varied (not stereotypy alone)  
3. Not immediately functional for survival (task-reward difference near 0)  
4. Voluntary / free-choice  
5. Occurs in a **relaxed field** (high energy, low stress / threat)

---

## 2. Metrics (PROVISIONAL — label everything unvalidated)

Gan’s formalization (**not validated**; agents must never optimize these):

| Symbol | Meaning (provisional) |
|--------|------------------------|
| **F** | Task-reward difference near 0 (play ≠ reward-max) |
| **V** | Free-choice preference for playground under free choice |
| **D** | Divergence (e.g. JS) between play-like and “serious” action distributions |
| **S** | Recurrence × motif entropy (repeated but varied) |
| **G** | Gate: high energy ∧ low stress (relaxed field) |

\[
\mathrm{PlayScore} = G \cdot (1 - |F|) \cdot V \cdot D \cdot S
\]

**Hard protocol:**

- **Optimize with one measure, evaluate with another** (agents cannot game PlayScore).
- Log components as `*_unvalidated` in metrics schema.
- Phase-1 need-driven mice: `F ≈ 0` by construction (no external task reward / no play term).

**Validation plan (later):**

1. PlayScore must separate play from **PPO**, **ICM**, **RND**, and **random** baselines.  
2. Optional: check on real animal pose data **as a ruler only — never for training**.  
3. **Spinka transfer test:** do agents that “played” recover better from pushes / friction / limb perturbations?  
4. **Pre-commit to reporting negative results.**  
5. **Do not overclaim** “fun”, consciousness, or a world model.

---

## 3. Hard rules (non-negotiable)

| ID | Rule |
|----|------|
| **H1** | Synthetic agents only — no animal/human play datasets for training |
| **H2** | **No play reward / observation / goal / utility term** named play, bout, motif, exaggeration, etc. Playground = geometry + manipulable objects. Curiosity / boredom / homeostasis are generic drives; `ACT_MANIPULATE` satisfies those only |
| **H3** | **No LLM in agents** (narrator LLMs later optional and off the critical path) |
| **H4** | Does not import or change L3 ecology; Track E exploratory |
| **Det** | Seeded `numpy.random.Generator`; CPU trajectories must be deterministic for the same seed+config |
| **Honest** | Calibration errors, failed collapses, and negative play results go in `NOTES.md` without spin |

If a PR / commit introduces a play reward, reject it.

---

## 4. Current status (as of HEAD near `9cd9f0a`, 2026-10-30)

### Phase 1 — done

- Need-driven Universe 25 + playground geometry (Calhoun 101×101 in, 16 cells, 256 nests, design capacity 3840).
- SoA agents (roles, 11 actions, drives). No `ACT_PLAY`.
- Parquet metrics + provisional PlayScore accumulator + calibration script.
- Tests: geometry, determinism, conservation, Warp smoke (`tests/run_tests.py`).
- Private GitHub repo live; MIT license.

### Phase-1 long run (honest)

Command:  
`python main.py --seed 7000 --out _output/run1600_abund_pg --days 1600 --backend numpy --device cpu --max-agents 4096 --playground on`

| Metric | Value |
|--------|-------|
| Wall | **296.6 s** (~4.9 min) |
| Ticks | 38400 |
| Peak N | **1715** at day **~1395** |
| Final N | 1339 |
| Births / deaths / conceptions | 62637 / 61306 / 32122 |
| NaNs | 0 |
| Backend | **numpy/cpu** (Warp available; tick not fully device-resident) |

**Calibration vs Calhoun 1973 (mean relative error ≈ 1.08):**

| Landmark | Target | Observed | Rel err |
|----------|--------|----------|---------|
| First litters | 104 | 221 | 1.13 |
| N @ day 315 | 620 | 48 | 0.92 |
| Peak N | 2200 | ~1708–1715 | ~0.22 |
| Peak day | 560 | ~1392–1395 | ~1.49 |
| Last young | 600 | ~1599.75 | ~1.67 |

Phases detected: adjustment, growth, stagnation. **No collapse by day 1600.**  
Label: **exploratory / negative on timing calibration**; peak magnitude within ~22% is the only near-hit.

### NVIDIA stack

| Piece | Status |
|-------|--------|
| **Warp** 1.18 (sm_120) | Core; hybrid tick + post-step kernels; device-resident action select still TODO |
| **NVTX** via `torch.cuda.nvtx` | Integrated |
| **USD (`pxr`)** pen export | Works → `_output/usd/pen.usda` |
| **CUDA Graphs** | Scaffolding + microbench wins on device-only post-step; hybrid sync-bound |
| **Newton** 1.7.0 | Detected + stub (`newton_playground.py`) — not stepped |
| **RL env spec** | Stub only (`rl_env_spec.py`) — Gymnasium / Isaac Lab style, PlayScore eval-only |
| **GPU on lab PC** | **RTX 5080** (not 5070) — Blackwell **sm_120**. Same family as 5070 |

See `docs/NVIDIA_STACK.md`, `docs/NSIGHT.md`.

### Phase 2 — calibration (2026-10-30) — SUPERSEDED

The phase-2 CMA-ES fit (first litters 115, N@315 594, peak 831 @ 585, no collapse) was an
artifact of a **pup-mill bug**: a zero softmax utility still carried probability, so pre-weaning
pups foraged, fought and *conceived* (median gestating age 15 d), while adults died of runaway
stress at ~80 d. Full diagnosis in `NOTES.md` ("Phase 2b").

### Phase 2b — bug fix + emergent collapse mechanism + recalibration (2026-10-30)

- Eligibility mask in action selection (pups REST/NEST only; MATE needs maturity); age gate in `_try_mate`.
- Births in the nest box; mothers nurse at the nest; wounds heal; stress relaxes toward gain/decay.
- **Developmental imprinting**: SoA trait `competence` lost while young under crowding, frozen at
  maturity; scales conception, maternal investment, withdrawal ("beautiful ones"). Irreversible by
  construction, matching Calhoun/Marsden. Plus female reproductive senescence (~560 d of age).
- Landmarks: `last_young_day` = last *surviving* birth; `peak_day` = first day ≥ 97 % of max;
  extra Calhoun facts (N@736 = 2056, adults@315 = 150, last conception ≈ 920) reported.
- Parallel CMA-ES (`--workers/--popsize`, process pool) from the repo-local `.venv` (has optuna).
- New tests: `tests/test_biology_guards.py` (incl. Warp↔NumPy stress/competence parity).

**Calibrated run (seed 7000, `configs/default.yaml`, 6 ticks/day, 1600 d, 45 s wall):**

| Landmark | Calhoun | Phase 1 | Phase 2b |
|----------|--------:|--------:|---------:|
| First litters | 104 | 221 | **111** |
| N @ 315 | 620 | 48 | **672** |
| Peak N | 2200 | 1715 | **2261** |
| Peak day (first ≥97 %) | 560 | ~1395 | 467 |
| Last surviving birth | 600 | ≥1600 | 813 (mechanism gap, see NOTES) |
| N @ 736 | 2056 | — | **2106** |
| N @ 1200 / 1600 | declining | 1339 @1600, still growing | **1316 / 93** |
| mean rel. error (5) | | 1.08 | **0.14** |

Phases detected: adjustment → growth → stagnation → decline (832) → collapse (1228). Held-out
seeds 8000–8002 keep the shape (peak 2238–2305, N@736 2116–2171); N@315 varies 404–827.
**Valid at 6 ticks/day only** (default.yaml is pinned to 6): at 24 ticks/day the same parameters
give peak 1088 because the tick loop is not dt-invariant (movement re-drawn every tick, per-event
effects not dt-scaled) — `docs/TASKS.md` P0-4.
Full tables and the open gaps in `NOTES.md` → "Phase 2b". The worker that owned phase 2
reported it finished; `src/` is no longer dual-edited, but still pull/rebase before pushing.

---

## 5. Architecture map

```
universe25-play/
├── HANDOFF.md              ← you are here
├── PLAN.md                 ← mini-prereg (hypotheses, arms, stop rules)
├── NOTES.md                ← dated honest results
├── README.md
├── pyproject.toml          ← package universe25, py>=3.11
├── main.py                 ← thin entry → universe25.__main__
├── configs/
│   ├── default.yaml        ← Calhoun + playground + biology + drives
│   └── smoke.yaml          ← 30-day smoke overrides
├── docs/
│   ├── TASKS.md            ← prioritized task list
│   ├── NVIDIA_STACK.md
│   └── NSIGHT.md
├── scripts/
│   ├── calibrate.py
│   ├── calibrate_optuna.py
│   ├── benchmark_backends.py
│   ├── microbench_warp_post.py
│   └── probe_nvidia.py
├── src/universe25/
│   ├── __main__.py         ← CLI: --seed --out --config --days --backend --device --playground --max-agents
│   ├── config.py           ← pydantic: Geometry, Playground, Resource, Biology, Drive, SimConfig
│   ├── sim.py              ← Universe25Sim (need-driven tick; density stress; breeding; logging)
│   ├── rng.py
│   ├── agents/
│   │   ├── state.py        ← AgentSoA, ROLE_*, ACT_* (11 actions; no PLAY)
│   │   ├── drives.py       ← H2 documentation
│   │   └── device.py       ← optional Warp mirror buffers
│   ├── world/
│   │   └── geometry.py     ← World, Cell, Nest, PlayObject, build_world
│   ├── metrics/
│   │   ├── logger.py       ← parquet
│   │   ├── playscore.py    ← PlayScoreAccumulator (unvalidated)
│   │   └── calibration.py  ← Calhoun landmarks + phase detect
│   ├── calib/              ← Optuna/CMA-ES helpers (phase 2)
│   ├── warp_kernels/
│   │   ├── engine.py       ← WarpTickEngine + graph capture
│   │   └── kernels.py
│   ├── nvidia/
│   │   ├── nvtx_ranges.py
│   │   ├── cuda_graphs.py
│   │   ├── newton_playground.py  ← stub
│   │   ├── usd_export.py
│   │   ├── rl_env_spec.py        ← stub (forbidden play rewards listed)
│   │   └── stack_info.py
│   └── io/snapshots.py
├── tests/
│   ├── run_tests.py        ← no pytest in shared venv; runs test_*.py as __main__
│   ├── test_geometry.py
│   ├── test_determinism.py
│   ├── test_conservation.py
│   ├── test_biology_guards.py  ← no immature conception, pups nest-bound, competence, Warp parity
│   └── test_warp_smoke.py
├── .venv/                  ← gitignored; repo-local Python with optuna/cmaes for calibration
└── _output/                ← gitignored runs
```

**Action codes** (`state.py`): REST, FORAGE, DRINK, NEST, SOCIAL, EXPLORE, MANIPULATE, AGGRESS, MATE, NURSE, WITHDRAW.  
**Roles:** pup, juvenile, territorial male, subordinate male, breeding female, nursing, withdrawn (“beautiful ones”), dead.

---

## 6. Setup / run / test (lab PC, PowerShell 5.1)

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$proj = 'C:\Users\user\Projects\universe25-play'
$py   = 'C:\Users\user\Desktop\omnilab\.venv\Scripts\python.exe'
$gh   = 'C:\Users\user\tools\gh\gh.exe'
$env:PYTHONPATH = "$proj\src"
Set-Location $proj

# Probe NVIDIA
& $py -X utf8 "$proj\scripts\probe_nvidia.py"

# Smoke
& $py -X utf8 "$proj\main.py" --seed 7000 --out "$proj\_output\smoke" --config "$proj\configs\smoke.yaml" --days 30

# Tests (shared venv has no pytest)
& $py -X utf8 "$proj\tests\run_tests.py"

# Calibrate a run
& $py -X utf8 "$proj\scripts\calibrate.py" --metrics "$proj\_output\smoke\metrics.parquet" --out "$proj\_output\smoke\calibration.json" --run-json "$proj\_output\smoke\run.json"

# Long abundant+playground, calibrated (default.yaml = phase-2b params, 6 ticks/day; ~50 s on CPU)
# → peak 2262, N@736 2106, 93 left at 1600, calibration_mean_rel_error 0.140
& $py -X utf8 "$proj\main.py" --seed 7000 --out "$proj\_output\run1600_p2b" --days 1600 --backend numpy --device cpu --max-agents 4096 --playground on

# Warp path (when kernels ready)
& $py -X utf8 "$proj\main.py" --seed 7000 --out "$proj\_output\warp_smoke" --backend warp --device cuda --days 5 --max-agents 4096

# Calibration (CMA-ES). optuna lives ONLY in the repo-local .venv (same Python/numpy as omnilab,
# no warp/torch). 16-core box: 14 workers, popsize 14, 1200 d, 6 ticks/day ≈ 25 min / 8 gens.
$pyc = "$proj\.venv\Scripts\python.exe"
& $pyc -X utf8 -u "$proj\scripts\calibrate_optuna.py" --seed 7000 --trials 112 --popsize 14 --workers 14 `
  --days 1200 --ticks-per-day 6 --x0 "$proj\configs\calibrated_calhoun.yaml" --out "$proj\_output\calib_cma"
```

**Git (pathspec discipline — never `git add .` on a shared tree):**

```powershell
git -C $proj --no-optional-locks status --short
git -C $proj pull --rebase origin master
git -C $proj add -- HANDOFF.md docs/TASKS.md
git -C $proj commit -m "docs: handoff menu"
& $gh auth status   # if needed
git -C $proj push origin master
```

Seeds: build/training `7000–7009`; unit tests `7100`; eval worlds later `8000–8009`. Every command takes `--seed`.

---

## 7. Roadmap + acceptance criteria

### Phase 1 — Environment substrate ✅
- [x] Calhoun geometry + playground AABB + objects  
- [x] Need-driven agents, density stress, roles  
- [x] Metrics + unvalidated PlayScore parts  
- [x] Determinism / geometry / conservation tests  
- [x] 1600-day run + honest calibration in NOTES  

### Phase 2 — Calibrate + GPU (calibration DONE 2026-10-30; GPU parity partial)
**Accept when:**
- [x] Mean relative landmark error **≪ 1.0** → **0.14** (peak day 467 = within 17 % of 560; N@315 672; first litters 111)
- [x] Collapse phase appears by ~day 1200 under abundant arm → N(1200) = 58 % of peak, 93 left at 1600; the one documented miss is surviving births lasting to day 813 (Calhoun 600) — mechanism gap, see NOTES
- [~] Warp tick path correct vs NumPy reference: density-stress + imprinting kernel parity test added (3e-8); mortality (hazard-level) and cells parity still open; CUDA Graph speedup documented in NSIGHT
- [x] No NaNs (0 across calibration, held-out and 1600-d runs); `docs/NSIGHT.md` benches unchanged (no kernel perf work this round)

Phase-2c candidates (in priority order): **dt-invariance** (P0-4: action persistence, per-day
event scaling — the calibration is currently tied to 6 ticks/day); stress-dependent litter
abandonment to close the day-600 cessation gap; vectorize `_passive_nurse` / per-agent loops
(profile in `docs/TASKS.md` P1-3).

### Phase 3 — Visuals + dashboard
**Accept when:**
- Top-down 16-cell pen viewer (mice as role-colored dots; stress trail / hopper heatmap)
- Editorial dashboard (population + phases shaded; conception; wounds; nest occupancy; % withdrawn; V and G)
- Look: paper `#F4F0E6`, ink `#1A1A1A`, stress `#8B1E1E`, nest teal `#2F5D50`; IBM Plex / Source Serif; **uPlot** charts; **no purple glows, glassmorphism, or AI-slop chrome**
- shadcn/ui restyled to that palette (not default violet)

### Phase 4 — Play behavior module (after env frozen)
**Accept when:**
- Playground free-choice and object/locomotor/social detectors implement Burghardt gates without rewarding play
- Sweep harness: abundance × density × toys × unpredictability
- Baselines: PPO, ICM, RND, random — **PlayScore eval-only**
- Spinka transfer protocol sketched + seed list frozen in a new PLAN section
- H2 audit still passes (grep for play reward terms)

### Phase 5 — Paper-grade release hygiene
README demos, pinned figures, reproducible `_output` cards, negative-result section.

---

## 8. Visual / dashboard direction (do not “AI polish”)

Inspired by Primer / Nicky Case explorables / scientific editorial design:

| Token | Value |
|-------|-------|
| Paper | `#F4F0E6` |
| Ink | `#1A1A1A` |
| Stress / sink | `#8B1E1E` |
| Nest / life | `#2F5D50` |
| Type | Source Serif (body) + IBM Plex Sans/Mono (UI/data) |
| Charts | **uPlot** (fast, tiny) |
| View | Top-down pen, 4×4 cells, nests as small marks, playground AABB dashed |
| Forbidden | Purple gradients, glass blur, neon robots, stock “AI neural” imagery |

---

## 9. Experimental arms (from PLAN.md)

| Arm | Label | Notes |
|-----|-------|-------|
| Abundance + playground | `TRACK-E-U25-ABUND-PG` | Phase-1 delivered (seed 7000) |
| Abundance, no playground | `TRACK-E-U25-ABUND-NOPG` | seed 7001 |
| Scarce + playground | `TRACK-E-U25-SCARCE-PG` | deferred; seed 7002 |

Prediction link to Leibo Gathering: scarcity → more aggression; abundance → peace **and** (our add) a band where Burghardt-positive play appears — or Calhoun withdrawn “beautiful ones” if too easy.

---

## 10. References (keep in README + here)

**Universe 25 / behavioral sink**
- Calhoun JB (1973). Death Squared. *Proc R Soc Med*. [PMC1644264](https://pmc.ncbi.nlm.nih.gov/articles/PMC1644264/)
- Calhoun JB (1962). Population density and social pathology. *Scientific American*.
- RatUtopia — [mantzaris/RatUtopia](https://github.com/mantzaris/RatUtopia), [arXiv:2508.08587](https://arxiv.org/abs/2508.08587)
- Mouse utopia model — [tomgwizd/Mouse-utopia-model](https://github.com/tomgwizd/Mouse-utopia-model), [PMC12939635](https://pmc.ncbi.nlm.nih.gov/articles/PMC12939635/)

**Play / abundance**
- Auerbach, Kanarek & Burghardt (2015). To play or not to play? That’s a resource abundance question. [doi:10.1177/1059712315611188](https://doi.org/10.1177/1059712315611188)
- Learning to Play — [arXiv:1802.07442](https://arxiv.org/abs/1802.07442) (curiosity / exploration; not Burghardt scoring)

**Multi-agent / scarcity aggression**
- Leibo et al. (2017). Gathering. [arXiv:1702.03037](https://arxiv.org/abs/1702.03037)
- Melting Pot — [google-deepmind/meltingpot](https://github.com/google-deepmind/meltingpot)
- Neural MMO — [neuralmmo.github.io](https://neuralmmo.github.io/)

**LLM societies (contrast — imitation; out of scope for agents)**
- Smallville — [arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
- Project Sid — [arXiv:2411.00114](https://arxiv.org/abs/2411.00114)

**Drives / homeostasis**
- Keramati & Gutkin (2014). Homeostatic reinforcement learning.

**NVIDIA / engines**
- [NVIDIA Warp](https://github.com/NVIDIA/warp)
- [NVIDIA Newton](https://github.com/newton-physics/newton) (rigid playground later)
- [FLAME GPU 2](https://github.com/FLAMEGPU/FLAMEGPU2) (alt mass-agent ref)

---

## 11. Collaboration notes

- **gan** owns research framing / PlayScore formalization.
- Jason wants **SOTA engineering**, great visuals, **no AI slop**, private git with continuous commits.
- Lab Python: `C:\Users\user\Desktop\omnilab\.venv\Scripts\python.exe` (do not pip-install into it without asking Jason).
- GPU lease: follow omnilab `gpu-lease-run` before long GPU jobs when the GPU is shared.

---

## 12. Definition of done (any coding task)

1. Matches acceptance criteria in the task card.  
2. `python tests\run_tests.py` passes (or task-local test named in the card).  
3. H2 audit clean (no new play reward terms).  
4. Determinism preserved for NumPy backend when behavior should be unchanged.  
5. `NOTES.md` updated if results changed.  
6. Commit with pathspec; `git pull --rebase` before push; message conventional (`feat|fix|docs|test|perf|chore`).  
7. No secrets, no `_output/` blobs, no force-push to `master`.
