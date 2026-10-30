"""Nsight Systems NVTX ranges (no extra package required).

Uses torch.cuda.nvtx when CUDA is available; otherwise a no-op context manager.
Mark tick phases so `nsys profile` shows Universe25_step / drives / actions / metrics.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def nvtx_range(name: str, color: str = "blue") -> Iterator[None]:
    pushed = False
    try:
        import torch

        if torch.cuda.is_available() and hasattr(torch.cuda, "nvtx"):
            torch.cuda.nvtx.range_push(name)
            pushed = True
    except Exception:
        pushed = False
    try:
        yield
    finally:
        if pushed:
            try:
                import torch

                torch.cuda.nvtx.range_pop()
            except Exception:
                pass
