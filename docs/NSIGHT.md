# Nsight Systems one-pager (Universe25 Warp tick)

## Goal
See NVTX ranges (`Universe25_step`, `warp_stress_mortality_cells`, `cuda_graph_capture` / `cuda_graph_replay`) and CUDA kernel time on RTX 50-series.

## Prerequisites
- Nsight Systems CLI (`nsys`) on PATH
- Omnilab venv with Warp + Torch CUDA
- Repo at `C:\Users\user\Projects\universe25-play`

## Profile command (PowerShell)

```powershell
$proj = 'C:\Users\user\Projects\universe25-play'
$py = 'C:\Users\user\Desktop\omnilab\.venv\Scripts\python.exe'
$env:PYTHONPATH = "$proj\src"
New-Item -ItemType Directory -Force -Path "$proj\_output\nsys" | Out-Null
nsys profile -o "$proj\_output\nsys\u25_warp" --trace=cuda,nvtx,osrt --force-overwrite true `
  $py -X utf8 -u "$proj\main.py" --seed 7000 --out "$proj\_output\nsys_run" `
  --backend warp --device cuda --days 5 --max-agents 4096
```

Open `u25_warp.nsys-rep` in Nsight Systems GUI.

## What to look for
1. **NVTX** lanes: host `Universe25_step` vs device `warp_*`.
2. After warmup (~3 ticks), **`cuda_graph_replay`** should replace repeated capture.
3. GPU gaps between graphs ⇒ host action/breeding still serial (phase-2 hybrid). Phase-3 moves action select to Warp.

## Note
CUDA Graph captures kernel launches with **device buffer** inputs (`dens_frac[0]` updated each tick). Do not bake Python floats into the graph.

## Phase-2 benchmark notes (RTX 5080, Asia/Seoul 2026-10-30)

### Full hybrid tick (host actions + Warp post-step)
- 50d / N~8: NumPy 3.08s, Warp 2.55s (1.21x), Warp+Graph 2.26s (1.37x)
- 200d / N~30–50: NumPy 6.78s, Warp 11.3s (0.60x), Warp+Graph 9.05s (0.75x)
- Hybrid is **sync-bound**: upload/download each tick dominates until more of the step stays on device.

### Device-only microbench (500 steps stress+mortality+cells)
| N alive | NumPy post | Warp full sync | CUDA Graph replay | Graph vs NumPy |
|--------:|-----------:|---------------:|------------------:|---------------:|
| 256 | 0.024s | 3.15s | 0.025s | 0.96x |
| 1024 | 0.032s | 1.10s | 0.021s | 1.54x |
| 4096 | 0.075s | 1.03s | 0.022s | **3.46x** |

Graph replay vs sync path: ~48–124x. Phase-3 target: keep agents resident on device.
