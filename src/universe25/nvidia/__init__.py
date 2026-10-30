"""NVIDIA tooling hooks: Warp core, optional Newton, CUDA Graphs, NVTX, USD."""

from universe25.nvidia.nvtx_ranges import nvtx_range
from universe25.nvidia.cuda_graphs import CudaGraphTick
from universe25.nvidia.stack_info import probe_nvidia_stack

__all__ = ["nvtx_range", "CudaGraphTick", "probe_nvidia_stack"]
