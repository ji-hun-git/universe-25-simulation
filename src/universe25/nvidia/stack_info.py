"""Probe which NVIDIA pieces are importable on this machine."""
from __future__ import annotations

from typing import Any


def probe_nvidia_stack() -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        import warp as wp

        wp.init()
        out["warp"] = {
            "version": getattr(wp, "__version__", "?"),
            "devices": [str(d) for d in wp.get_devices()],
            "capture_begin": hasattr(wp, "capture_begin"),
        }
    except Exception as e:
        out["warp"] = {"error": type(e).__name__}
    try:
        import torch

        out["torch"] = {
            "version": torch.__version__,
            "cuda": torch.cuda.is_available(),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "nvtx": hasattr(torch.cuda, "nvtx"),
        }
    except Exception as e:
        out["torch"] = {"error": type(e).__name__}
    try:
        import newton

        out["newton"] = {"version": getattr(newton, "__version__", "ok")}
    except Exception as e:
        out["newton"] = {"error": type(e).__name__}
    try:
        from pxr import Usd  # noqa: F401

        out["usd_pxr"] = {"ok": True}
    except Exception as e:
        out["usd_pxr"] = {"error": type(e).__name__}
    for name in ("gymnasium", "isaaclab", "omni", "nvtx"):
        try:
            __import__(name)
            out[name] = {"ok": True}
        except Exception as e:
            out[name] = {"error": type(e).__name__}
    return out
