"""Gaussian-process emulator for history matching (replica v2 M5, docs/REPLICA_V2.md).

Constant mean, ARD squared-exponential kernel plus a nugget, on inputs scaled to [0, 1]^d.
Hyperparameters are found by maximum marginal likelihood (L-BFGS-B with the analytic gradient,
a few restarts from fixed seeds), so a fit is deterministic for a given data set. The nugget
absorbs the seed-to-seed noise of the simulator; `predict` returns the latent mean, its
variance (emulator uncertainty) and the nugget (seed noise), all in the output's units.

No dependency beyond NumPy and SciPy.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

LOG2PI = float(np.log(2.0 * np.pi))


class GP:
    def __init__(self, X: np.ndarray, y: np.ndarray, restarts: int = 4, seed: int = 0,
                 ls_bounds: tuple[float, float] = (0.03, 20.0)) -> None:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        self.X = X
        self.n, self.d = X.shape
        self.mu = float(y.mean())
        self.sd = float(y.std()) or 1.0
        self.y = (y - self.mu) / self.sd
        self._D = (X[:, None, :] - X[None, :, :]) ** 2  # (n, n, d) squared differences
        d = self.d
        lo = np.r_[np.full(d, np.log(ls_bounds[0])), np.log(0.05), np.log(1e-4)]
        hi = np.r_[np.full(d, np.log(ls_bounds[1])), np.log(20.0), np.log(2.0)]
        rng = np.random.default_rng(seed)
        best = None
        for _ in range(restarts):
            th0 = np.r_[np.log(rng.uniform(0.3, 2.0, d)), 0.0, np.log(rng.uniform(0.02, 0.4))]
            res = minimize(self._nlml, th0, jac=True, method="L-BFGS-B",
                           bounds=list(zip(lo, hi)), options={"maxiter": 300})
            if best is None or res.fun < best.fun:
                best = res
        self.theta = best.x
        self.nlml = float(best.fun)
        self._set(best.x)
        del self._D

    def _parts(self, th: np.ndarray):
        d = self.d
        ls2 = np.exp(2.0 * th[:d])
        s2, n2 = float(np.exp(th[d])), float(np.exp(th[d + 1]))
        Dk = self._D / ls2  # (n, n, d)
        kse = s2 * np.exp(-0.5 * Dk.sum(axis=2))
        K = kse + (n2 + 1e-8) * np.eye(self.n)
        return Dk, kse, K, s2, n2

    def _nlml(self, th: np.ndarray) -> tuple[float, np.ndarray]:
        Dk, kse, K, s2, n2 = self._parts(th)
        try:
            c = cho_factor(K, lower=True)
        except np.linalg.LinAlgError:
            return 1e25, np.zeros_like(th)
        alpha = cho_solve(c, self.y)
        nl = (0.5 * float(self.y @ alpha) + float(np.sum(np.log(np.diag(c[0]))))
              + 0.5 * self.n * LOG2PI)
        Kinv = cho_solve(c, np.eye(self.n))
        W = np.outer(alpha, alpha) - Kinv
        WK = W * kse
        g = np.empty_like(th)
        g[: self.d] = -0.5 * np.einsum("ij,ijk->k", WK, Dk)
        g[self.d] = -0.5 * float(WK.sum())
        g[self.d + 1] = -0.5 * n2 * float(np.trace(W))
        return nl, g

    def _set(self, th: np.ndarray) -> None:
        d = self.d
        self.ls = np.exp(th[:d])
        self.s2, self.n2 = float(np.exp(th[d])), float(np.exp(th[d + 1]))
        _, _, K, _, _ = self._parts(th)
        self._c = cho_factor(K, lower=True)
        self._alpha = cho_solve(self._c, self.y)
        self._Kinv = cho_solve(self._c, np.eye(self.n))

    def predict(self, Xs: np.ndarray, chunk: int = 4000) -> tuple[np.ndarray, np.ndarray, float]:
        """(mean, emulator variance, nugget variance) in the output's units."""
        Xs = np.asarray(Xs, dtype=np.float64)
        Xl = self.X / self.ls
        sq_l = np.sum(Xl ** 2, axis=1)
        mean = np.empty(len(Xs))
        var = np.empty(len(Xs))
        for a in range(0, len(Xs), chunk):
            Z = Xs[a:a + chunk] / self.ls
            d2 = np.sum(Z ** 2, axis=1)[:, None] + sq_l[None, :] - 2.0 * Z @ Xl.T
            Ks = self.s2 * np.exp(-0.5 * np.maximum(d2, 0.0))
            mean[a:a + chunk] = Ks @ self._alpha
            var[a:a + chunk] = self.s2 - np.sum((Ks @ self._Kinv) * Ks, axis=1)
        var = np.maximum(var, 1e-12)
        return (self.mu + self.sd * mean, var * self.sd ** 2, self.n2 * self.sd ** 2)

    def loo(self) -> tuple[np.ndarray, np.ndarray]:
        """Leave-one-out predictive mean and variance (closed form), output units, for the
        emulator diagnostic (standardised errors should be about N(0, 1))."""
        diag = np.diag(self._Kinv)
        m = self.y - self._alpha / diag
        v = 1.0 / diag
        return self.mu + self.sd * m, v * self.sd ** 2


def implausibility(z: float, var_obs: float, mean: np.ndarray, var_em: np.ndarray,
                   var_noise: float) -> np.ndarray:
    """|z - E f(x)| / sqrt(observation + discrepancy + emulator + seed-noise variance)."""
    return np.abs(z - mean) / np.sqrt(var_obs + var_em + var_noise)
