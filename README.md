# universe25-play

Research-grade **Universe 25** (Calhoun 1973) simulation with an optional **playground** zone.

Track E / exploratory. Agents are need-driven (hunger, thirst, fatigue, stress, social, aggression, maternal, curiosity, boredom, homeostasis). **There is no play reward.** The playground is geometry + manipulable objects only; any playground use is drive spillover.

## Why

Closest scientific recreations (RatUtopia, mouse-utopia-model) match population curves but have bare visuals and no play instrumentation. DeepMind Gathering shows aggression under scarcity / peace under abundance, but agents cannot play. This repo builds the environment substrate for asking whether **play-like behavior emerges under abundance** and can be scored with Burghardt’s criteria / a provisional PlayScore (unvalidated).

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Lab standard; uv/pip friendly |
| Agent store | Structure-of-arrays (NumPy host; Warp/Torch device select) | Scales to thousands of mice; Warp confirmed on RTX 5080 sm_120 |
| Config | pydantic + YAML | Typed, hydra-free (shared env has no hydra) |
| Metrics | Parquet (pyarrow, zstd) | Columnar, WebGPU-streamable snapshots alongside |
| RNG | `numpy.random.Generator` seeded | Deterministic CPU trajectories |

## Quick start

```powershell
# from repo root; uses a Python with numpy/pydantic/pyyaml/pyarrow
$env:PYTHONPATH = "$PWD\src"
python main.py --seed 7000 --out _output\smoke --config configs\smoke.yaml --days 30
python tests\run_tests.py
python scripts\calibrate.py --metrics _output\smoke\metrics.parquet --out _output\smoke\calibration.json --run-json _output\smoke\run.json
```

## Viewer

A local colony viewer (phase 3, TASKS P2-1 / P2-2) has these parts:
- **Pen view:** the pen from above (cells, nest boxes, food and water, the playground and its
  objects, every mouse).
- **Control panel:** recordings, live runs, layers, colours and roles.
- **Transport:** with Calhoun's phases on the timeline.
- **Inspector:** follows one mouse.
- **Dashboard:** population against Calhoun's census, roles, births and deaths, stress,
  playground share, and cell density over time.

It has light ("paper") and dark themes.

```powershell
$env:PYTHONPATH = "$PWD\src"
# the reference colony: a frame a day for 1,600 days, every tick in four one-day windows
python scripts\viewer_record.py --name ref_7000 --fine 150:1,450:1,750:1,1100:1
# the phase-4 substrate with ball physics: every free-time sub-step in two one-day windows
python scripts\viewer_record.py --name substrate_7000 --days 420 --free-substeps 12 --ball-physics --fine 300:1,400:1
# serve it on 127.0.0.1 only, then open http://127.0.0.1:8765/
python scripts\viewer_serve.py
```

- **Recording** plays a `.u25` file from `_output/viewer/`, or one dropped on the window.
- **Live run** steps the simulator on this machine and streams frames as they are made. You
  choose:
  - preset: reference, scarce, or replica v2 pen;
  - seed and days;
  - backend: NumPy, or Warp on the GPU;
  - playground, sub-steps K and ball physics;
  - one frame per day, tick or sub-step.
- **Capture only reads the simulator.** A recorded or live run is the run `main.py` makes from
  the same config and seed (`tests/test_viewer.py`).
- **The Warp path is not the calibrated colony**: its mortality and cell kernels are not at
  parity with NumPy.
- Phases A–D are Calhoun's, shaded on the record's days. V and G are unvalidated and eval-only.
- Keys:
  - Space: run or pause
  - ← / →: previous or next frame
  - Home / End: start or latest frame
  - `[` / `]`: slower or faster
  - F: follow the selected mouse
  - Esc: clear the selection
- The charts load uPlot from cdn.jsdelivr.net, and the fonts come from Google Fonts. Without
  them the page still runs, and the charts say so.

## World

- Pen: **101 × 101 inches**, **16 cells**, **256 nests**, food + water per cell (Calhoun design capacity 3840).
- **Playground** (configurable AABB, default center): balls, tunnels, ramps. Toggle `--playground on|off`.

## Calibration targets (Calhoun 1973, Death Squared)

| Landmark | Target | Definition used |
|---|---|---|
| First litters | ~day 104 (contested: Calhoun 1971 and his figures give 50–65; see `docs/RESEARCH_DIGEST.md`) | first day with a birth |
| N at day 315 | ~620 | |
| Peak | ~2200 at ~day 560 | `peak_day` = day of the 31-day running-mean maximum of N (the census maximum, plateau-robust; the first day at ≥ 97 % of max marks the start of the plateau and is reported as `peak_day_97pct`) |
| Last surviving young | ~day 600 | cessation of surviving births: last birth day on which the 30-day rate of births that reach weaning is still ≥ 5 % of its maximum (the strict latest-weaned-pup day is also reported; it is set by single lucky survivors) |
| Decline | thereafter | slow: N = 2056 at day 736, 122 at day ~1444, 27 at day 1588 (N@1444 and N@1588 reported from 1600-day runs; old-age deaths follow a per-individual lifespan, 780 ± 150 d; both counts were taken after ≈ 150 mice had been removed after day 1000, so a run without removal sits above them). Reported-only record points: 1871 at 811, ≈ 1650 at 960, 100 at 1471, doubling times 55 d (phase B) / 145 d (phase C) |

Also reported (not in the canonical mean error): N@736 = 2056, 150 adults (+470 immatures) at
day 315, last conception ≈ day 920 (measured as the rate-based cessation of conceptions, like
surviving births; the strict last-conception day is reported alongside).

Collapse is **emergent**: density → stress → neglect / litter abandonment / breeding suppression,
plus a developmental `competence` trait that young lose under crowding — or anywhere in the
colony once its social organisation has broken down — and keep for life
(Calhoun's "beautiful ones"; Marsden 1972 showed the deficit persisted after transfer), an
irreversible post-weaning loss of maternal capacity under sustained stress (Calhoun's phase C/D
mothers that attacked and expelled their young while conceptions went on) and its male
counterpart, a loss of courtship capacity that ends conceptions (phase D). A social-breakdown
stress boost builds up with the weaned-population density (a ramp up to a threshold: the
behavioural sink), nursing is a relaxation toward satiety per nest box that crowding disturbs (a
reversible, density-graded loss of nursing effectiveness: Calhoun's phase-C infant mortality), and
starvation is lethal within days. Conception is a once-per-day process and agents hold each
decision for 1/6 day, so results do not depend on the tick resolution. No parameter names a
collapse day.
`calibration.json` reports honest error; see `NOTES.md` for the current fit and its misses.

Calibration (CMA-ES) runs from the repo-local `.venv` (has optuna; the shared lab venv does not):

```powershell
.venv\Scripts\python.exe scripts\calibrate_optuna.py --seed 7000 --trials 224 --popsize 14 --workers 14 --sigma0 0.1 --days 1200 --x0 configs\calibrated_calhoun.yaml --out _output\calib_cma
```

## Metrics (per log window)

Population, role counts, playground occupancy, free-choice preference **V**, action entropy, provisional PlayScore parts **F, V, D, S, G** (labelled `*_unvalidated`).

PlayScore (gan formalization, **not validated**): `G · (1−|F|) · V · D · S`. Agents never optimize it.

## Repo layout

```
configs/          default.yaml, smoke.yaml
src/universe25/   sim, world, agents (state, policy hook), metrics, io
tests/            geometry, determinism, conservation, biology guards + Warp parity (__main__ runner)
scripts/          calibrate.py, calibrate_optuna.py, benchmark_backends.py, viewer_*.py
viewer/           colony viewer (static HTML / JS; scripts/viewer_serve.py serves it)
_output/          runs (gitignored)
PLAN.md           mini-prereg (§15: phase 4 learning arms)
NOTES.md          dated results
docs/             TASKS.md, PHASE4_DESIGN.md (learning agents, detectors), RESEARCH_DIGEST.md (record + literature), NVIDIA_STACK.md
```

## References

- Calhoun JB (1973). Death Squared. *Proc R Soc Med*. [PMC1644264](https://pmc.ncbi.nlm.nih.gov/articles/PMC1644264/)
- Calhoun JB (1971). Space and the Strategy of Life. In Esser (ed.), *Behavior and Environment*, 329–387 — first surviving litters at 50 d; five-universe series
- Marsden HM (1972). Crowding and Animal Behavior. In Wohlwill & Carson (eds.) — censuses 1871 @ 811, ≈ 1650 @ 960; transfer experiments
- Kessler A (1966). Rockefeller PhD thesis — crowded mouse populations stabilised and resumed reproduction when re-paired (the non-replication)
- Keramati M & Gutkin B (2014). Homeostatic reinforcement learning. *eLife* 3:e04811 — the drive-reduction reward used in phase 4
- Burghardt GM (2005). *The Genesis of Animal Play*; Burghardt (2014) *Anim Behav Cogn* 1(2):90–98 — the five criteria, surplus resource theory
- Full list with URLs: `docs/RESEARCH_DIGEST.md` part E
- RatUtopia — [mantzaris/RatUtopia](https://github.com/mantzaris/RatUtopia), [arXiv:2508.08587](https://arxiv.org/abs/2508.08587)
- Mouse utopia model — [tomgwizd/Mouse-utopia-model](https://github.com/tomgwizd/Mouse-utopia-model), [PMC12939635](https://pmc.ncbi.nlm.nih.gov/articles/PMC12939635/)
- Leibo et al. 2017. Multi-agent Cooperation and the Emergence of (natural) Selection. [arXiv:1702.03037](https://arxiv.org/abs/1702.03037) (Gathering)
- Auerbach, Kanarek & Burghardt 2015. To play or not to play? [doi:10.1177/1059712315611188](https://doi.org/10.1177/1059712315611188)
- Learning to Play — [arXiv:1802.07442](https://arxiv.org/abs/1802.07442)
- Smallville — [arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
- Project Sid — [arXiv:2411.00114](https://arxiv.org/abs/2411.00114)
- Melting Pot — [google-deepmind/meltingpot](https://github.com/google-deepmind/meltingpot)
- Neural MMO — [neuralmmo.github.io](https://neuralmmo.github.io/)

## License

MIT. Not affiliated with Calhoun’s estate or NIMH.


## NVIDIA stack

Warp is the core. See [docs/NVIDIA_STACK.md](docs/NVIDIA_STACK.md).

```powershell
python scripts\probe_nvidia.py
# Nsight (when using --backend warp --device cuda):
# nsys profile -o _output/nsys/u25 python main.py --seed 7000 --out _output\nsys_run --backend warp --device cuda --days 5
```

Integrated: Warp, PyTorch CUDA NVTX hooks, CUDA Graph scaffolding, Newton stub, USD (`pxr`) pen export.  
Planned: Warp tick kernels + CUDA Graph capture, Newton rigid playground, Isaac Lab / Gymnasium vec env, Omniverse live session.
