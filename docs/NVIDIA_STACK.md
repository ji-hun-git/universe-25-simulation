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

## H2 reminder

No play reward in training. Newton contacts and Warp speeds must not introduce a “play” objective.

## Probe

```powershell
$env:PYTHONPATH = "$PWD\src"
python -c "from universe25.nvidia import probe_nvidia_stack; import json; print(json.dumps(probe_nvidia_stack(), indent=2))"
```
