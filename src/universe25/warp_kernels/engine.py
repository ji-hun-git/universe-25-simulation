"""Warp tick engine with optional CUDA Graph capture."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from universe25.agents.state import AgentSoA
from universe25.config import SimConfig
from universe25.nvidia.nvtx_ranges import nvtx_range
from universe25.world.geometry import World


@dataclass
class WarpTickEngine:
    cfg: SimConfig
    world: World
    device: str = "cuda:0"
    use_graph: bool = False
    _wp: Any = field(default=None, repr=False)
    _bufs: dict[str, Any] = field(default_factory=dict, repr=False)
    _graph: Any = field(default=None, repr=False)
    _graph_ready: bool = False
    _warmup_left: int = 3
    n_launches: int = 0
    n_graph_replays: int = 0

    def __post_init__(self) -> None:
        import warp as wp

        wp.init()
        self._wp = wp
        self._ensure_buffers_capacity(self.cfg.max_agents)

    def _ensure_buffers_capacity(self, n: int) -> None:
        wp = self._wp
        if self._bufs.get("n") == n:
            return
        self._bufs = {
            "n": n,
            "alive": wp.zeros(n, dtype=wp.int32, device=self.device),
            "role": wp.zeros(n, dtype=wp.int32, device=self.device),
            "hunger": wp.zeros(n, dtype=wp.float32, device=self.device),
            "thirst": wp.zeros(n, dtype=wp.float32, device=self.device),
            "curiosity": wp.zeros(n, dtype=wp.float32, device=self.device),
            "boredom": wp.zeros(n, dtype=wp.float32, device=self.device),
            "social_drive": wp.zeros(n, dtype=wp.float32, device=self.device),
            "energy": wp.zeros(n, dtype=wp.float32, device=self.device),
            "fatigue": wp.zeros(n, dtype=wp.float32, device=self.device),
            "age_days": wp.zeros(n, dtype=wp.float32, device=self.device),
            "gestating": wp.zeros(n, dtype=wp.float32, device=self.device),
            "stress": wp.zeros(n, dtype=wp.float32, device=self.device),
            "wounds": wp.zeros(n, dtype=wp.float32, device=self.device),
            "rank": wp.zeros(n, dtype=wp.float32, device=self.device),
            "x": wp.zeros(n, dtype=wp.float32, device=self.device),
            "y": wp.zeros(n, dtype=wp.float32, device=self.device),
            "cell_id": wp.zeros(n, dtype=wp.int32, device=self.device),
            "nest_id": wp.zeros(n, dtype=wp.int32, device=self.device),
            "in_playground": wp.zeros(n, dtype=wp.int32, device=self.device),
            "competence": wp.zeros(n, dtype=wp.float32, device=self.device),
            "rng_states": wp.zeros(n, dtype=wp.uint32, device=self.device),
            "cell_counts": wp.zeros(self.world.n_cells, dtype=wp.int32, device=self.device),
            "nest_occ": wp.zeros(self.world.n_nests, dtype=wp.int32, device=self.device),
            "nest_cap": wp.array(
                np.array([n.capacity for n in self.world.nests], dtype=np.int32),
                dtype=wp.int32,
                device=self.device,
            ),
            "dens_frac": wp.zeros(1, dtype=wp.float32, device=self.device),
            "dens_social": wp.zeros(1, dtype=wp.float32, device=self.device),
        }
        self._graph = None
        self._graph_ready = False
        self._warmup_left = 3

    def upload(self, agents: AgentSoA, rng: np.random.Generator) -> None:
        wp = self._wp
        n = agents.capacity
        self._ensure_buffers_capacity(n)
        b = self._bufs
        b["alive"].assign(agents.alive.astype(np.int32))
        b["role"].assign(agents.role.astype(np.int32))
        b["hunger"].assign(agents.hunger)
        b["thirst"].assign(agents.thirst)
        b["curiosity"].assign(agents.curiosity)
        b["boredom"].assign(agents.boredom)
        b["social_drive"].assign(agents.social_drive)
        b["energy"].assign(agents.energy)
        b["fatigue"].assign(agents.fatigue)
        b["age_days"].assign(agents.age_days)
        b["gestating"].assign(agents.gestating)
        b["stress"].assign(agents.stress)
        b["wounds"].assign(agents.wounds)
        b["rank"].assign(agents.rank)
        b["x"].assign(agents.x)
        b["y"].assign(agents.y)
        b["cell_id"].assign(agents.cell_id.astype(np.int32))
        b["nest_id"].assign(agents.nest_id.astype(np.int32))
        b["in_playground"].assign(agents.in_playground.astype(np.int32))
        b["competence"].assign(agents.competence)
        # seed rng states once
        if not hasattr(self, "_rng_seeded"):
            seeds = rng.integers(1, 2**31 - 1, size=n, dtype=np.uint32)
            b["rng_states"].assign(seeds)
            self._rng_seeded = True

    def download(self, agents: AgentSoA) -> None:
        b = self._bufs
        agents.alive[:] = np.array(b["alive"].numpy(), dtype=bool)
        agents.role[:] = np.array(b["role"].numpy(), dtype=np.int8)
        agents.hunger[:] = b["hunger"].numpy()
        agents.thirst[:] = b["thirst"].numpy()
        agents.curiosity[:] = b["curiosity"].numpy()
        agents.boredom[:] = b["boredom"].numpy()
        agents.social_drive[:] = b["social_drive"].numpy()
        agents.energy[:] = b["energy"].numpy()
        agents.fatigue[:] = b["fatigue"].numpy()
        agents.age_days[:] = b["age_days"].numpy()
        agents.gestating[:] = b["gestating"].numpy()
        agents.stress[:] = b["stress"].numpy()
        agents.wounds[:] = b["wounds"].numpy()
        agents.x[:] = b["x"].numpy()
        agents.y[:] = b["y"].numpy()
        agents.cell_id[:] = np.array(b["cell_id"].numpy(), dtype=np.int16)
        agents.nest_id[:] = np.array(b["nest_id"].numpy(), dtype=np.int16)
        agents.in_playground[:] = np.array(b["in_playground"].numpy(), dtype=bool)
        agents.competence[:] = b["competence"].numpy()
        agents.n_alive = int(agents.alive.sum())

    def _host_cell_nest_counts(self, agents: AgentSoA) -> None:
        alive = agents.alive
        cc = np.bincount(agents.cell_id[alive].astype(int), minlength=self.world.n_cells).astype(np.int32)
        housed = alive & (agents.nest_id >= 0)  # abandoned pups (nest_id -1) occupy no box
        no = np.bincount(agents.nest_id[housed].astype(int), minlength=self.world.n_nests)
        no = no.astype(np.int32)
        self._bufs["cell_counts"].assign(cc)
        self._bufs["nest_occ"].assign(no)

    def _launch_kernels(self, agents: AgentSoA, dt: float) -> None:
        from universe25.warp_kernels.kernels import (
            density_stress_kernel,
            mortality_kernel,
            update_cells_kernel,
            update_drives_kernel,
        )

        wp = self._wp
        b = self._bufs
        n = agents.capacity
        bio = self.cfg.biology
        d = self.cfg.drives
        dens_frac = float(agents.n_alive / max(1, self.world.capacity_design))
        b["dens_frac"].assign(np.array([dens_frac], dtype=np.float32))
        if bio.breakdown_density_counts == "weaned":
            n_soc = int(np.count_nonzero(agents.alive & (agents.age_days >= bio.weaning_days)))
        else:
            n_soc = int(agents.n_alive)
        b["dens_social"].assign(
            np.array([n_soc / max(1, self.world.capacity_design)], dtype=np.float32)
        )
        capacity_per_cell = float(self.world.capacity_design / max(1, self.world.n_cells))
        pg = self.world.playground_bounds

        with nvtx_range("warp_drives"):
            wp.launch(
                update_drives_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["role"], b["hunger"], b["thirst"], b["curiosity"], b["boredom"],
                    b["social_drive"], b["energy"], b["fatigue"], b["age_days"], b["gestating"],
                    float(dt), float(d.hunger_gain_per_day), float(d.thirst_gain_per_day),
                    float(d.curiosity_gain), float(d.boredom_gain), float(d.social_drive_gain),
                    float(bio.pup_hunger_scale),
                ],
                device=self.device,
            )
        with nvtx_range("warp_stress"):
            wp.launch(
                density_stress_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["cell_id"], b["nest_id"], b["rank"], b["stress"], b["social_drive"],
                    b["cell_counts"], b["nest_occ"], b["nest_cap"], b["age_days"], b["competence"],
                    float(dt), float(d.stress_density_gain), float(d.stress_decay),
                    float(bio.nest_overcrowd_stress), capacity_per_cell, b["dens_social"],
                    float(bio.breakdown_threshold()), float(bio.social_breakdown_stress_boost),
                    float(bio.maturity_days), float(bio.imprint_rate),
                    float(bio.imprint_density_threshold),
                    float(self.cfg.ticks_per_day_ref / self.cfg.ticks_per_day),
                ],
                device=self.device,
            )
        with nvtx_range("warp_mortality"):
            wp.launch(
                mortality_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["role"], b["stress"], b["wounds"], b["age_days"],
                    b["hunger"], b["thirst"], b["energy"], b["rng_states"],
                    float(dt), float(bio.base_mortality_per_day), float(bio.stress_mortality_scale),
                    float(bio.max_age_days), float(bio.young_mortality_scale),
                    float(bio.density_mortality_scale), b["dens_frac"],
                    float(bio.starvation_hazard_per_day),
                ],
                device=self.device,
            )
        with nvtx_range("warp_cells"):
            wp.launch(
                update_cells_kernel,
                dim=n,
                inputs=[
                    b["alive"], b["x"], b["y"], b["cell_id"], b["in_playground"],
                    float(self.world.width), float(self.world.height),
                    int(self.cfg.geometry.n_cells_x), int(self.cfg.geometry.n_cells_y),
                    1 if self.world.playground_enabled else 0,
                    float(pg[0]), float(pg[1]), float(pg[2]), float(pg[3]),
                ],
                device=self.device,
            )
        self.n_launches += 1

    def device_physics_step(self, agents: AgentSoA, dt: float, rng: np.random.Generator) -> None:
        """Upload → Warp kernels (or graph replay) → download. Host still owns actions/births."""
        self._host_cell_nest_counts(agents)
        self.upload(agents, rng)
        wp = self._wp

        if self.use_graph and str(self.device).startswith("cuda"):
            if not self._graph_ready:
                if self._warmup_left > 0:
                    self._launch_kernels(agents, dt)
                    wp.synchronize()
                    self._warmup_left -= 1
                else:
                    with nvtx_range("cuda_graph_capture"):
                        wp.capture_begin(device=self.device)
                        self._launch_kernels(agents, dt)
                        self._graph = wp.capture_end(device=self.device)
                    self._graph_ready = True
            else:
                with nvtx_range("cuda_graph_replay"):
                    wp.capture_launch(self._graph)
                    self.n_graph_replays += 1
        else:
            self._launch_kernels(agents, dt)

        wp.synchronize()
        self.download(agents)

    def status(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "use_graph": self.use_graph,
            "graph_ready": self._graph_ready,
            "n_launches": self.n_launches,
            "n_graph_replays": self.n_graph_replays,
        }
