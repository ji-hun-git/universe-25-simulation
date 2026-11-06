# NVIDIA stack for universe25-play

Target GPU: RTX 50-series (lab: **RTX 5080**, sm_120; Warp 1.18 + CUDA 13.x). Jason’s brief also names RTX 5070 — same Blackwell family; keep sm_120 kernels.

## Integrated now (phase 1)

| Piece | Role | Status |
|---|---|---|
| **NVIDIA Warp** | Preferred agent SoA / kernel backend (`backend=warp`) | **Core.** Device probe + optional buffer mirror. Tick loop still NumPy host SoA in phase 1 (deterministic CPU path); Warp kernels next. |
| **PyTorch CUDA** | Fallback SoA device + **NVTX** ranges via `torch.cuda.nvtx` | **Integrated.** `universe25.nvidia.nvtx_ranges` wraps step phases for Nsight Systems. |
| **NVTX / Nsight Systems** | `nsys profile --trace=nvtx,cuda` | **Hooks in.** No `nvtx` pip package required. |
| **CUDA Graphs** | Capture Warp tick for replay | **Scaffolding** in `CudaGraphTick` (no-op until device-only kernels). |
| **Newton 1.7.0** | Rigid-body playground (balls/ramps) | **Detected + stub** (`newton_playground.py`). Not stepped in phase 1. |
| **USD (`pxr`)** | Pen export for Omniverse later | **Optional exporter** `usd_export.export_pen_usda`. Omniverse Kit (`omni`) **not** installed. |

## Planned (do not block phase 1)

1. **Warp kernels** for drives, utility select, move, density stress (SoA on `cuda:0`).
2. **CUDA Graph** capture of the Warp tick after warmup (`wp.capture_begin` / `capture_launch` or `torch.cuda.CUDAGraph`).
3. **Newton / warp.sim** playground: balls and ramps as rigid bodies; mice apply contact impulses; kinematic fallback remains.
4. **Nsight** one-pager: example `nsys profile -o _output/nsys/u25 python main.py --backend warp --device cuda --days 5`.
5. **RL vec env** (`rl_env_spec.py`): Gymnasium or Isaac Lab style, PyTorch PPO; rewards = survival + homeostasis (+ generic curiosity); **PlayScore eval-only** (H2).
6. **Omniverse**: live USD stage / Nucleus only if Kit is installed; until then static USDA + JSON snapshots for a WebGPU viewer.

## Learner on the GPU (phase 4, P4-2 / P4-3, 2026-11-06)

| Piece | Role | Measured |
|---|---|---|
| **PyTorch 2.11 + CUDA 12.8** | shared actor-critic (48/49 -> 128 -> 128 -> 11 / 1), PPO updates, inference per policy call (`learn/ppo.py`) | RTX 5080; VRAM peak **246 MB** over 10^8 steps |
| **Nursery pre-training** (`scripts/pretrain_nursery.py`) | single process: host NumPy biology + GPU learner, 60-day randomised episodes | **51,700 agent-steps/s** average (30k-79k per episode); 1.02 x 10^8 steps, 1,891 updates in 33 min |
| **Learning run in one world** (`policy.kind: mlp_ppo`) | same | 20 d, 80 agents, 12 sub-steps: 20 updates, 31,000 transitions in 10 s |

The host-side biology and observation building dominate; the network itself is tiny. Agent-steps
count policy calls (decisions and free-time sub-steps).

Determinism recipe (implemented in `learn/ppo.py`, tested in `tests/test_learn.py` and
`tests/test_nursery.py`): `CUBLAS_WORKSPACE_CONFIG=:4096:8` set before torch loads;
`torch.use_deterministic_algorithms(True)`; cuDNN autotuning off and deterministic; TF32 off;
fixed CPU thread count; initial weights from a seeded `torch.Generator`; action sampling and
minibatch order from seeded NumPy streams; no `torch.compile`. A learning run and a resumed
pre-training run repeat bit for bit on the same GPU and library versions. CPU and GPU runs are not
expected to agree with each other, and the docs never claim they do.

Planned item 5 above is done in a different form: a shared-parameter PPO inside the simulation
(no Gymnasium wrapper), reward = homeostatic drive reduction over eight drives, PlayScore and the
detectors eval-only.

## H2 reminder

No play reward in training. Newton contacts and Warp speeds must not introduce a “play” objective.

## Probe

```powershell
$env:PYTHONPATH = "$PWD\src"
python -c "from universe25.nvidia import probe_nvidia_stack; import json; print(json.dumps(probe_nvidia_stack(), indent=2))"
```
