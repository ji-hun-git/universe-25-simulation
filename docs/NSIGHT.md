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
