#!/usr/bin/env python
"""Benchmark NumPy vs Warp (+ optional CUDA Graph) for a fixed short run."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.config import SimConfig
from universe25.sim import Universe25Sim


def run_once(backend: str, device: str, use_graph: bool, seed: int, days: float, out: Path) -> dict:
    cfg = SimConfig(
        seed=seed,
        days=days,
        backend=backend,  # type: ignore[arg-type]
        device=device,  # type: ignore[arg-type]
        max_agents=4096,
        log_every_ticks=10**9,  # effectively off
        snapshot_every_days=0,
        use_cuda_graph=use_graph,
        arm_label=f"BENCH-{backend}",
    )
    cfg.playground.enabled = True
    t0 = time.perf_counter()
    sim = Universe25Sim(cfg, out)
    # construction may include warp init
    t_init = time.perf_counter()
    summary = sim.run()
    t1 = time.perf_counter()
    summary["wall_total"] = t1 - t0
    summary["wall_init"] = t_init - t0
    summary["use_cuda_graph"] = use_graph
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=7000)
    p.add_argument("--days", type=float, default=50.0)
    p.add_argument("--out", type=str, required=True)
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    results["numpy"] = run_once("numpy", "cpu", False, args.seed, args.days, out / "numpy")
    try:
        results["warp"] = run_once("warp", "cuda", False, args.seed, args.days, out / "warp")
        results["warp_graph"] = run_once("warp", "cuda", True, args.seed, args.days, out / "warp_graph")
    except Exception as e:
        results["warp_error"] = f"{type(e).__name__}: {e}"
    np_w = results["numpy"]["wall_seconds"]
    for k in ("warp", "warp_graph"):
        if k in results and "wall_seconds" in results[k]:
            results[k]["speedup_vs_numpy"] = np_w / max(1e-9, results[k]["wall_seconds"])
    (out / "benchmark.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
