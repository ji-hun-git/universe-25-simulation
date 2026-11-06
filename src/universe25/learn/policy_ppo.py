"""`policy.kind: mlp_ppo` — the learning policy (P4-2).

Each call of `choose` (a decision, or a free-time sub-step in rechoose mode) is one action per
agent. The policy keeps one open transition per slot: the observation, action, log-probability,
value, mask and homeostatic drive D at the call. The agent's next call closes it with the reward
D_before - D_now, the discount gamma_unit ** (time between the calls, in sub-step units) and the
value of the new state as bootstrap. At a decision call, slots whose agent died or was replaced
by a newborn since the last decision close as terminal (reward D_before - D_MAX). Every
`rollout_ticks` decisions the closed transitions are used for one PPO update (learn/ppo.py) and
cleared; new actions are then drawn with the updated network.

Training signal: the drive-reduction reward only. No detector, trace or PlayScore field is read
(audited); the heuristic is never a teacher. Sampling draws from the policy's own stream (or the
simulation's sub-step stream at sub-steps), never from the biology stream.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from universe25.agents.observation import OBS_DIM, ObservationBuilder
from universe25.agents.state import N_ACTIONS
from universe25.learn.ppo import PPOLearner
from universe25.learn.reward import (
    D_MAX,
    contributions,
    drive,
    drive_reduction,
    read_drives,
    terminal_reward,
)
from universe25.rng import make_rng

if TYPE_CHECKING:  # pragma: no cover
    from universe25.config import PolicyConfig
    from universe25.sim import Universe25Sim

BUFFER_KEYS = ("obs", "action", "logp", "value", "mask", "reward", "done", "value_next",
               "gamma", "slot", "time", "contrib")


class MlpPpoPolicy:
    name = "mlp_ppo"

    def __init__(self, cfg: PolicyConfig, seed: int):
        self.cfg = cfg
        self.ppo = cfg.ppo
        self.learner = PPOLearner(OBS_DIM, N_ACTIONS, int(cfg.hidden), cfg.ppo, seed)
        self.rng = make_rng(int(seed) + 1_000_003)  # action sampling at decisions
        self.mb_rng = make_rng(int(seed) + 4_000_003)  # minibatch order
        self.builder: ObservationBuilder | None = None
        self.cap = 0
        self._tick = -1
        self._call = 0
        self._decisions_since_update = 0
        self.n_transitions = 0
        self.n_calls = 0
        self.log_path: Path | None = None
        self.history: list[dict[str, float]] = []
        self._buf: dict[str, list[np.ndarray]] = {k: [] for k in BUFFER_KEYS}

    # ---------------------------------------------------------------- state
    def _init(self, sim: Universe25Sim) -> None:
        cap = sim.agents.capacity
        self.cap = cap
        self.has = np.zeros(cap, dtype=bool)
        self.p_obs = np.zeros((cap, OBS_DIM), dtype=np.float32)
        self.p_act = np.zeros(cap, dtype=np.int64)
        self.p_logp = np.zeros(cap, dtype=np.float32)
        self.p_val = np.zeros(cap, dtype=np.float32)
        self.p_mask = np.zeros((cap, N_ACTIONS), dtype=bool)
        self.p_D = np.zeros(cap, dtype=np.float64)
        self.p_time = np.zeros(cap, dtype=np.int64)
        self.p_contrib = np.zeros((cap, 7), dtype=np.float32)
        self.prev_age = np.full(cap, np.inf)
        self.K = max(1, int(getattr(sim, "free_substeps", 1)))
        self.gamma_unit = float(self.ppo.gamma_per_decision) ** (1.0 / self.K)
        self.log_path = Path(sim.out_dir) / "learn_log.jsonl"
        self.builder = ObservationBuilder(sim.world)

    def _close(self, slots: np.ndarray, reward: np.ndarray, done: np.ndarray,
               value_next: np.ndarray, now: int | np.ndarray) -> None:
        if slots.size == 0:
            return
        dt = np.asarray(now) - self.p_time[slots]
        self._buf["obs"].append(self.p_obs[slots].copy())
        self._buf["action"].append(self.p_act[slots].copy())
        self._buf["logp"].append(self.p_logp[slots].copy())
        self._buf["value"].append(self.p_val[slots].copy())
        self._buf["mask"].append(self.p_mask[slots].copy())
        self._buf["reward"].append(reward.astype(np.float64))
        self._buf["done"].append(done.astype(np.float64))
        self._buf["value_next"].append(value_next.astype(np.float32))
        self._buf["gamma"].append(self.gamma_unit ** np.maximum(dt, 0).astype(np.float64))
        self._buf["slot"].append(slots.astype(np.int64))
        self._buf["time"].append(self.p_time[slots].copy())
        self._buf["contrib"].append(self.p_contrib[slots].copy())
        self.has[slots] = False
        self.n_transitions += int(slots.size)

    def _buffer(self) -> dict[str, np.ndarray]:
        return {k: np.concatenate(v) for k, v in self._buf.items()}

    def _update(self) -> None:
        B = self._buffer()
        for k in BUFFER_KEYS:
            self._buf[k].clear()
        if B["reward"].size == 0 or not self.ppo.enabled:
            return
        st = self.learner.update(B, self.mb_rng)
        st["update"] = float(self.learner.n_updates)
        st["transitions_total"] = float(self.n_transitions)
        st["mean_D_at_call"] = float(np.mean(B["contrib"].sum(axis=1) ** 0.5))
        for i, k in enumerate(("hunger", "thirst", "fatigue", "social_drive", "curiosity",
                               "boredom", "stress")):
            st[f"contrib_{k}"] = float(B["contrib"][:, i].mean())
        self.history.append(st)
        if self.log_path is not None:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(st) + "\n")

    # ---------------------------------------------------------------- policy
    def choose(self, sim: Universe25Sim, idx: np.ndarray, allowed: np.ndarray,
               rng: np.random.Generator | None = None) -> np.ndarray:
        if self.cap == 0:
            self._init(sim)
        if sim.tick != self._tick:
            self._tick = sim.tick
            self._call = 0
        else:
            self._call += 1
        decision = self._call == 0
        now = (sim.tick // sim.ticks_per_decision) * self.K + (0 if decision else self._call - 1)
        obs = self.builder.build(sim, idx)
        drives = read_drives(sim.agents, idx)
        contrib = contributions(drives)
        D = contrib.sum(axis=1) ** 0.5
        if decision:
            a = sim.agents
            alive = a.alive
            reborn = alive & (a.age_days < self.prev_age - 1e-9)
            gone = np.flatnonzero(self.has & (~alive | reborn))
            self._close(gone, terminal_reward(self.p_D[gone]), np.ones(gone.size),
                        np.zeros(gone.size, np.float32), now)
            self.prev_age[alive] = a.age_days[alive]
            self.prev_age[~alive] = np.inf
        hp = self.has[idx]
        if hp.any():
            v_now = self.learner.value_raw(obs[hp])
            s = idx[hp]
            self._close(s, drive_reduction(self.p_D[s], D[hp]), np.zeros(s.size), v_now, now)
        if decision:
            self._decisions_since_update += 1
            if self._decisions_since_update >= int(self.ppo.rollout_ticks):
                self._update()
                self._decisions_since_update = 0
        u = (self.rng if rng is None else rng).random(idx.size)
        act, logp, val = self.learner.act(obs, allowed, u)
        self.has[idx] = True
        self.p_obs[idx] = obs
        self.p_act[idx] = act
        self.p_logp[idx] = logp
        self.p_val[idx] = val
        self.p_mask[idx] = allowed
        self.p_D[idx] = D
        self.p_time[idx] = now
        self.p_contrib[idx] = contrib.astype(np.float32)
        self.n_calls += int(idx.size)
        return act.astype(np.int8)

    def finish(self, sim: Universe25Sim) -> dict[str, Any]:
        out = Path(sim.out_dir)
        np.savez(out / "policy_final.npz", **self.learner.actor_params())
        np.savez(out / "critic_final.npz", **self.learner.critic_params())
        summ = {"updates": self.learner.n_updates, "transitions": self.n_transitions,
                "calls": self.n_calls, "device": str(self.learner.device),
                "gamma_unit": getattr(self, "gamma_unit", None), "d_max": D_MAX,
                "free_substeps": getattr(self, "K", None)}
        (out / "learn_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
        return summ


def mean_drive(sim: Universe25Sim) -> float:
    """Mean homeostatic D over the alive agents (the smoke metric)."""
    idx = np.flatnonzero(sim.agents.alive)
    return float(drive(read_drives(sim.agents, idx)).mean()) if idx.size else float("nan")
