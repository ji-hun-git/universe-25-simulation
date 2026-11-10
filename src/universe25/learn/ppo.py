"""Shared-parameter PPO with a local critic (IPPO) for the colony (P4-2; PHASE4_DESIGN.md 1.5).

One small actor-critic for every mouse. Transitions are the agents' own consecutive policy calls
(decisions and, with free-time sub-steps, sub-steps), so their durations differ: each carries its
own discount gamma_unit ** duration (duration in sub-step units). Deaths end a chain (terminal
reward, bootstrap 0); a reborn slot starts a new chain. Advantages: GAE over each slot's chain,
truncated at the rollout boundary with the bootstrap value. Values are learned on a running
normalisation of the returns; advantages are normalised per minibatch; the reward scale is fixed.

Determinism (PHASE4_DESIGN.md section 5): CUBLAS_WORKSPACE_CONFIG is set before torch loads,
deterministic algorithms are enforced, TF32 and cuDNN autotuning are off, initial weights come
from a seeded torch.Generator, and action sampling and minibatch order use seeded NumPy streams.
Run to run on the same device and library versions the result is bit-identical; CPU and GPU are
not expected to agree with each other.
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

from typing import Any  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402


def setup_determinism(cpu_threads: int = 4) -> None:
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_num_threads(max(1, int(cpu_threads)))


def pick_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def _orth(layer: nn.Linear, gain: float, g: torch.Generator) -> nn.Linear:
    try:
        nn.init.orthogonal_(layer.weight, gain=gain, generator=g)
    except TypeError:  # pragma: no cover - older torch without generator support
        nn.init.orthogonal_(layer.weight, gain=gain)
    nn.init.zeros_(layer.bias)
    return layer


class ActorCritic(nn.Module):
    """obs -> hidden tanh -> hidden tanh -> logits; a separate critic of the same shape -> 1."""

    def __init__(self, obs_dim: int, n_actions: int, hidden: int, g: torch.Generator):
        super().__init__()
        r2 = float(np.sqrt(2.0))
        self.a1 = _orth(nn.Linear(obs_dim, hidden), r2, g)
        self.a2 = _orth(nn.Linear(hidden, hidden), r2, g)
        self.a3 = _orth(nn.Linear(hidden, n_actions), 0.01, g)
        self.c1 = _orth(nn.Linear(obs_dim, hidden), r2, g)
        self.c2 = _orth(nn.Linear(hidden, hidden), r2, g)
        self.c3 = _orth(nn.Linear(hidden, 1), 1.0, g)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = torch.tanh(self.a2(torch.tanh(self.a1(obs))))
        v = torch.tanh(self.c2(torch.tanh(self.c1(obs))))
        return self.a3(h), self.c3(v).squeeze(-1)


class ValueNorm:
    """Debiased exponential running mean / variance of the returns (MAPPO-style)."""

    def __init__(self, beta: float = 0.99, eps: float = 1e-5):
        self.beta, self.eps = beta, eps
        self.m1 = 0.0
        self.m2 = 0.0
        self.debias = 0.0

    @property
    def mean(self) -> float:
        return self.m1 / self.debias if self.debias > 0 else 0.0

    @property
    def std(self) -> float:
        if self.debias <= 0:
            return 1.0
        var = self.m2 / self.debias - self.mean ** 2
        return float(np.sqrt(max(var, self.eps)))

    def update(self, x: np.ndarray) -> None:
        x = np.asarray(x, dtype=np.float64)
        if x.size == 0:
            return
        b = self.beta
        self.m1 = b * self.m1 + (1 - b) * float(x.mean())
        self.m2 = b * self.m2 + (1 - b) * float((x ** 2).mean())
        self.debias = b * self.debias + (1 - b)

    def normalize(self, x: np.ndarray) -> np.ndarray:
        return (np.asarray(x, dtype=np.float64) - self.mean) / self.std

    def denormalize(self, y: np.ndarray) -> np.ndarray:
        return np.asarray(y, dtype=np.float64) * self.std + self.mean


def gae(rew: np.ndarray, val: np.ndarray, val_next: np.ndarray, done: np.ndarray,
        gamma: np.ndarray, lam: float | np.ndarray, slot: np.ndarray,
        time: np.ndarray) -> np.ndarray:
    """Generalised advantage estimates along each slot's chain of transitions (ordered by
    time), with per-transition discounts; truncated at the end of the buffer (the bootstrap is in
    val_next). A terminal transition cuts the chain."""
    n = rew.size
    if n == 0:
        return np.zeros(0)
    order = np.lexsort((time, slot))
    s = slot[order]
    starts = np.flatnonzero(np.concatenate([[True], s[1:] != s[:-1]]))
    lens = np.diff(np.concatenate([starts, [n]]))
    grp = np.repeat(np.arange(starts.size), lens)
    pos = np.arange(n) - np.repeat(starts, lens)
    G, L = starts.size, int(lens.max())
    nd = 1.0 - done[order].astype(np.float64)
    delta = rew[order] + gamma[order] * nd * val_next[order] - val[order]
    lam_o = np.asarray(lam, dtype=np.float64)[order] if np.ndim(lam) else lam  # P4-15
    coef = gamma[order] * lam_o * nd
    D = np.zeros((G, L))
    C = np.zeros((G, L))
    D[grp, pos] = delta
    C[grp, pos] = coef
    A = np.zeros((G, L + 1))
    for j in range(L - 1, -1, -1):
        A[:, j] = D[:, j] + C[:, j] * A[:, j + 1]
    out = np.empty(n)
    out[order] = A[grp, pos]
    return out


def _masked_norm(x: torch.Tensor, m: torch.Tensor) -> torch.Tensor:
    """(x - mean) / std over the rows where m is True (population std), by masked sums."""
    w = m.to(x.dtype)
    n = w.sum().clamp_min(1.0)
    mu = (x * w).sum() / n
    var = (((x - mu) ** 2) * w).sum() / n
    return (x - mu) / (var.sqrt() + 1e-8)


class PPOLearner:
    def __init__(self, obs_dim: int, n_actions: int, hidden: int, cfg: Any, seed: int):
        setup_determinism(int(cfg.cpu_threads))
        self.cfg = cfg
        self.device = pick_device(str(cfg.device))
        g = torch.Generator().manual_seed(int(seed) + 3_000_003)
        self.net = ActorCritic(obs_dim, n_actions, hidden, g).to(self.device)
        self.opt = torch.optim.Adam(self.net.parameters(), lr=float(cfg.lr), eps=1e-5)
        self.vnorm = ValueNorm()
        self.n_updates = 0

    # ---------------------------------------------------------------- acting
    @torch.no_grad()
    def value_raw(self, obs: np.ndarray) -> np.ndarray:
        if obs.shape[0] == 0:
            return np.zeros(0, dtype=np.float32)
        _, v = self.net(torch.from_numpy(obs).to(self.device))
        return self.vnorm.denormalize(v.cpu().numpy()).astype(np.float32)

    @torch.no_grad()
    def act(self, obs: np.ndarray, mask: np.ndarray, u: np.ndarray
            ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Masked categorical sample by inverse CDF on one uniform per row: actions, log-probs
        (float32, as the update computes them) and raw values."""
        o = torch.from_numpy(obs).to(self.device)
        m = torch.from_numpy(np.ascontiguousarray(mask)).to(self.device)
        logits, v = self.net(o)
        logp_all = torch.log_softmax(logits.masked_fill(~m, -1e8), dim=-1)
        p = logp_all.exp().cpu().numpy().astype(np.float64) * mask
        cdf = np.cumsum(p, axis=1)
        cdf /= cdf[:, -1:]
        a = (u[:, None] <= cdf).argmax(axis=1)
        a = np.where(mask[np.arange(a.size), a], a, mask.argmax(axis=1))  # float guard
        lp = logp_all.gather(1, torch.from_numpy(a).to(self.device)[:, None]).squeeze(1)
        return (a.astype(np.int64), lp.cpu().numpy().astype(np.float32),
                self.vnorm.denormalize(v.cpu().numpy()).astype(np.float32))

    # ---------------------------------------------------------------- learning
    def entropy_coef(self, transitions_total: float | None) -> float:
        """P4-15: the entropy weight, linearly annealed over the transition count when
        entropy_coef_final is set; otherwise the constant entropy_coef."""
        cfg = self.cfg
        c0 = float(cfg.entropy_coef)
        c1 = getattr(cfg, "entropy_coef_final", None)
        if c1 is None or transitions_total is None:
            return c0
        a, b = float(cfg.entropy_anneal_start), float(cfg.entropy_anneal_end)
        t = float(transitions_total)
        if t <= a or b <= a:
            return c0 if t <= a else float(c1)
        if t >= b:
            return float(c1)
        return c0 + (float(c1) - c0) * (t - a) / (b - a)

    def update(self, B: dict[str, np.ndarray], rng: np.random.Generator,
               transitions_total: float | None = None, K: int = 1) -> dict[str, float]:
        cfg = self.cfg
        lam: float | np.ndarray = float(cfg.gae_lambda)
        if getattr(cfg, "gae_lambda_per_unit_time", False) and "dt" in B:  # P4-15
            lam = float(cfg.gae_lambda) ** (np.asarray(B["dt"], np.float64) / max(1, int(K)))
        adv = gae(B["reward"], B["value"].astype(np.float64), B["value_next"].astype(np.float64),
                  B["done"], B["gamma"], lam, B["slot"], B["time"])
        ret = adv + B["value"]
        self.vnorm.update(ret)
        ret_n = self.vnorm.normalize(ret)
        dev = self.device
        obs = torch.from_numpy(B["obs"]).to(dev)
        mask = torch.from_numpy(np.ascontiguousarray(B["mask"])).to(dev)
        act = torch.from_numpy(B["action"].astype(np.int64)).to(dev)
        lp_old = torch.from_numpy(B["logp"].astype(np.float32)).to(dev)
        adv_t = torch.from_numpy(adv.astype(np.float32)).to(dev)
        ret_t = torch.from_numpy(ret_n.astype(np.float32)).to(dev)
        per_type = getattr(cfg, "adv_norm", "pooled") == "per_type" and "is_decision" in B
        if per_type:
            dec_t = torch.from_numpy(np.asarray(B["is_decision"], bool)).to(dev)
        ent_c = self.entropy_coef(transitions_total)
        if cfg.lr_decay_updates and cfg.lr_decay_updates > 0:
            frac = max(0.1, 1.0 - self.n_updates / float(cfg.lr_decay_updates))
            for gp in self.opt.param_groups:
                gp["lr"] = float(cfg.lr) * frac
        n = obs.shape[0]
        n_mb = max(1, int(cfg.minibatches))
        stats = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "approx_kl": 0.0,
                 "clip_frac": 0.0}
        steps = 0
        for _ in range(int(cfg.epochs)):
            perm = torch.from_numpy(rng.permutation(n)).to(dev)
            for chunk in torch.tensor_split(perm, n_mb):
                if chunk.numel() == 0:
                    continue
                logits, v_hat = self.net(obs[chunk])
                logp_all = torch.log_softmax(logits.masked_fill(~mask[chunk], -1e8), dim=-1)
                lp = logp_all.gather(1, act[chunk][:, None]).squeeze(1)
                ratio = torch.exp(lp - lp_old[chunk])
                a = adv_t[chunk]
                if per_type:  # P4-15: decisions and sub-steps normalised apart (masked sums)
                    a = torch.where(dec_t[chunk], _masked_norm(a, dec_t[chunk]),
                                    _masked_norm(a, ~dec_t[chunk]))
                else:
                    a = (a - a.mean()) / (a.std(unbiased=False) + 1e-8)
                clipped = torch.clamp(ratio, 1 - cfg.clip, 1 + cfg.clip) * a
                pg = -torch.min(ratio * a, clipped).mean()
                ent = -(logp_all.exp() * logp_all.clamp_min(-1e4)).sum(-1).mean()
                vl = nn.functional.huber_loss(v_hat, ret_t[chunk], delta=float(cfg.huber_delta))
                loss = pg + float(cfg.vf_coef) * vl - ent_c * ent
                self.opt.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), float(cfg.max_grad_norm))
                self.opt.step()
                with torch.no_grad():
                    stats["policy_loss"] += float(pg)
                    stats["value_loss"] += float(vl)
                    stats["entropy"] += float(ent)
                    stats["approx_kl"] += float((lp_old[chunk] - lp).mean())
                    stats["clip_frac"] += float(((ratio - 1).abs() > cfg.clip).float().mean())
                steps += 1
        self.n_updates += 1
        out = {k: v / max(steps, 1) for k, v in stats.items()}
        var_ret = float(np.var(ret))
        out.update({"n": float(n), "mean_reward": float(B["reward"].mean()),
                    "mean_adv": float(adv.mean()), "terminal_frac": float(B["done"].mean()),
                    "explained_var": float(1.0 - np.var(ret - B["value"]) / var_ret)
                    if var_ret > 0 else float("nan"),
                    "value_norm_mean": self.vnorm.mean, "value_norm_std": self.vnorm.std,
                    "entropy_coef": ent_c})
        return out

    # ---------------------------------------------------------------- export
    def actor_params(self) -> dict[str, np.ndarray]:
        """The actor in the MlpFrozenPolicy .npz layout (W as in -> out)."""
        n = self.net
        f = lambda t: t.detach().cpu().numpy().astype(np.float32)  # noqa: E731
        return {"W1": f(n.a1.weight).T.copy(), "b1": f(n.a1.bias), "W2": f(n.a2.weight).T.copy(),
                "b2": f(n.a2.bias), "W3": f(n.a3.weight).T.copy(), "b3": f(n.a3.bias)}

    def critic_params(self) -> dict[str, np.ndarray]:
        n = self.net
        f = lambda t: t.detach().cpu().numpy().astype(np.float32)  # noqa: E731
        return {"W1": f(n.c1.weight).T.copy(), "b1": f(n.c1.bias), "W2": f(n.c2.weight).T.copy(),
                "b2": f(n.c2.bias), "W3": f(n.c3.weight).T.copy(), "b3": f(n.c3.bias),
                "value_norm": np.array([self.vnorm.m1, self.vnorm.m2, self.vnorm.debias])}
