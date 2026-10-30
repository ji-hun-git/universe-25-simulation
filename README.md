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

## World

- Pen: **101 × 101 inches**, **16 cells**, **256 nests**, food + water per cell (Calhoun design capacity 3840).
- **Playground** (configurable AABB, default center): balls, tunnels, ramps. Toggle `--playground on|off`.

## Calibration targets (Calhoun 1973, Death Squared)

| Landmark | Target | Definition used |
|---|---|---|
| First litters | ~day 104 | first day with a birth |
| N at day 315 | ~620 | |
| Peak | ~2200 at ~day 560 | `peak_day` = first day at ≥ 97 % of max N (plateau-robust) |
| Last surviving young | ~day 600 | latest birth day among pups that reached weaning |
| Decline | thereafter | slow: N = 2056 at day 736, 122 at day ~1444 |

Also reported (not in the canonical mean error): N@736 = 2056, 150 adults (+470 immatures) at
day 315, last conception ≈ day 920.

Collapse is **emergent**: density → stress → neglect / litter abandonment / breeding suppression,
plus a developmental `competence` trait that young lose under crowding and keep for life
(Calhoun's "beautiful ones"; Marsden 1972 showed the deficit persisted after transfer). Conception
is a once-per-day process and nursing is per nest box, so results do not depend on the tick
resolution. No parameter names a collapse day.
`calibration.json` reports honest error; see `NOTES.md` for the current fit and its misses.

Calibration (CMA-ES) runs from the repo-local `.venv` (has optuna; the shared lab venv does not):

```powershell
.venv\Scripts\python.exe scripts\calibrate_optuna.py --seed 7000 --trials 112 --popsize 14 --workers 14 --days 1200 --x0 configs\calibrated_calhoun.yaml --out _output\calib_cma
```

## Metrics (per log window)

Population, role counts, playground occupancy, free-choice preference **V**, action entropy, provisional PlayScore parts **F, V, D, S, G** (labelled `*_unvalidated`).

PlayScore (gan formalization, **not validated**): `G · (1−|F|) · V · D · S`. Agents never optimize it.

## Repo layout

```
configs/          default.yaml, smoke.yaml
src/universe25/   sim, world, agents, metrics, io
tests/            geometry, determinism, conservation, biology guards + Warp parity (__main__ runner)
scripts/          calibrate.py, calibrate_optuna.py, benchmark_backends.py
_output/          runs (gitignored)
PLAN.md           mini-prereg
NOTES.md          dated results
```

## References

- Calhoun JB (1973). Death Squared. *Proc R Soc Med*. [PMC1644264](https://pmc.ncbi.nlm.nih.gov/articles/PMC1644264/)
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
