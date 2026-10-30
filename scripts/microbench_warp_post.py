"""Device-only microbench: stress+mortality+cells at fixed N (no host actions)."""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from universe25.config import SimConfig
from universe25.world.geometry import build_world
from universe25.agents.state import AgentSoA
from universe25.warp_kernels.engine import WarpTickEngine

def fill_agents(a: AgentSoA, n_alive: int, rng: np.random.Generator) -> None:
    a.alive[:] = False
    a.alive[:n_alive] = True
    a.role[:n_alive] = 2
    a.hunger[:n_alive] = rng.uniform(0.2, 0.8, n_alive)
    a.thirst[:n_alive] = rng.uniform(0.2, 0.8, n_alive)
    a.energy[:n_alive] = rng.uniform(0.5, 1.0, n_alive)
    a.stress[:n_alive] = rng.uniform(0.0, 0.5, n_alive)
    a.x[:n_alive] = rng.uniform(1, 100, n_alive)
    a.y[:n_alive] = rng.uniform(1, 100, n_alive)
    a.cell_id[:n_alive] = rng.integers(0, 16, n_alive)
    a.nest_id[:n_alive] = rng.integers(0, 256, n_alive)
    a.n_alive = n_alive

def numpy_post(a, world, cfg, dt, rng, steps):
    bio, d = cfg.biology, cfg.drives
    t0 = time.perf_counter()
    for _ in range(steps):
        alive = a.alive
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        dens = a.n_alive / max(1, world.capacity_design)
        cc = np.bincount(a.cell_id[alive].astype(int), minlength=world.n_cells)
        cap = world.capacity_design / max(1, world.n_cells)
        local = cc[a.cell_id[idx]] / max(cap, 1e-9)
        gain = d.stress_density_gain * local
        a.stress[idx] = np.clip(a.stress[idx] + gain * dt - d.stress_decay * dt, 0, 1.5)
        p = np.full(idx.size, bio.base_mortality_per_day * dt)
        p = p + bio.stress_mortality_scale * (a.stress[idx] ** 2) * dt
        p = p + bio.density_mortality_scale * (dens ** 2) * dt
        dead = rng.random(idx.size) < p
        if dead.any():
            a.alive[idx[dead]] = False
            a.n_alive = int(a.alive.sum())
    return time.perf_counter() - t0

def main():
    out = Path(r"C:\Users\user\Projects\universe25-play\_output\bench_p2_micro")
    cfg = SimConfig(seed=7100, max_agents=4096, backend="warp", device="cuda", use_cuda_graph=True)
    world = build_world(cfg.geometry, cfg.playground, seed=cfg.seed)
    rng = np.random.default_rng(7100)
    steps = 500
    results = {}
    for n_alive in (256, 1024, 4096):
        a = AgentSoA.create(4096)
        # numpy
        a2 = AgentSoA.create(4096)
        fill_agents(a2, n_alive, np.random.default_rng(7100))
        tw = numpy_post(a2, world, cfg, 1/24, np.random.default_rng(99), steps)
        # warp full sync
        eng = WarpTickEngine(cfg=cfg, world=world, device="cuda:0", use_graph=False)
        fill_agents(a, n_alive, np.random.default_rng(7100))
        t0 = time.perf_counter()
        for _ in range(steps):
            eng._host_cell_nest_counts(a)
            eng.upload(a, rng)
            eng._launch_kernels(a, 1/24)
            eng._wp.synchronize()
            eng.download(a)
        twarp = time.perf_counter() - t0
        # warp graph replay only (device-resident)
        eng2 = WarpTickEngine(cfg=cfg, world=world, device="cuda:0", use_graph=True)
        fill_agents(a, n_alive, np.random.default_rng(7100))
        eng2.upload(a, rng)
        eng2._host_cell_nest_counts(a)
        for _ in range(5):
            eng2._launch_kernels(a, 1/24)
        eng2._wp.synchronize()
        eng2._wp.capture_begin(device=eng2.device)
        eng2._launch_kernels(a, 1/24)
        eng2._graph = eng2._wp.capture_end(device=eng2.device)
        eng2._wp.synchronize()
        t0 = time.perf_counter()
        for _ in range(steps):
            dens = float(max(1, a.n_alive) / max(1, world.capacity_design))
            eng2._bufs["dens_frac"].assign(np.array([dens], dtype=np.float32))
            eng2._wp.capture_launch(eng2._graph)
        eng2._wp.synchronize()
        tgraph = time.perf_counter() - t0
        results[str(n_alive)] = {
            "numpy_post_s": tw,
            "warp_full_sync_s": twarp,
            "warp_graph_replay_s": tgraph,
            "steps": steps,
            "speedup_graph_vs_numpy": tw / max(1e-9, tgraph),
            "speedup_graph_vs_warp_sync": twarp / max(1e-9, tgraph),
        }
        print(n_alive, results[str(n_alive)])
    (out / "microbench.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
