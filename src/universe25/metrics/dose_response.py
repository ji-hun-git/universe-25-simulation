"""Stratified dose-response test for H-e (PLAN.md section 15.1, amendment adopted 2026-11-08).

Kendall's tau-b between a dose and a response within each stratum, averaged over the strata
(T); the null permutes the dose within every stratum. A stratum where the dose or the response
is constant has tau 0 and contributes 0 to T and to every permutation. Eval-only and generic:
nothing here reads a detector, a policy or the simulation.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _signs(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return np.sign(v[:, None] - v[None, :])


def kendall_tau_b(x: Any, y: Any) -> float:
    """Kendall's tau-b; 0 when either variable is constant."""
    sx, sy = _signs(np.asarray(x)), _signs(np.asarray(y))
    iu = np.triu_indices(sx.shape[0], 1)
    a, b = sx[iu], sy[iu]
    den = np.sqrt(float(np.count_nonzero(a)) * float(np.count_nonzero(b)))
    return float((a * b).sum() / den) if den > 0 else 0.0


def stratified_tau_test(dose: Any, response: Any, strata: Any, n_perm: int = 10_000,
                        seed: int = 0, chunk: int = 1000) -> dict[str, Any]:
    """T = mean over strata of tau-b(dose, response); one-sided p of T against the dose permuted
    within strata: p = (1 + #{T* >= T}) / (1 + n_perm)."""
    dose = np.asarray(dose, dtype=np.float64)
    resp = np.asarray(response, dtype=np.float64)
    strata = np.asarray(strata)
    if not (dose.shape == resp.shape == strata.shape):
        raise ValueError("dose, response and strata must have the same shape")
    rng = np.random.default_rng(seed)
    labels = list(dict.fromkeys(strata.tolist()))
    taus: list[float] = []
    null = np.zeros(n_perm)
    for lab in labels:
        m = strata == lab
        sd, sr = _signs(dose[m]), _signs(resp[m])
        n = sd.shape[0]
        iu = np.triu_indices(n, 1)
        den = np.sqrt(float(np.count_nonzero(sd[iu])) * float(np.count_nonzero(sr[iu])))
        if den == 0:
            taus.append(0.0)
            continue
        taus.append(float((sd[iu] * sr[iu]).sum() / den))
        # tau(dose[p], resp) = sum_{i<j} sd[p_i, p_j] sr[i, j] / den; both sign matrices are
        # antisymmetric, so the full-matrix sum counts every pair twice
        for lo in range(0, n_perm, chunk):
            b = min(chunk, n_perm - lo)
            P = np.argsort(rng.random((b, n)), axis=1)
            sdp = sd[P[:, :, None], P[:, None, :]]
            null[lo:lo + b] += 0.5 * (sdp * sr[None]).sum(axis=(1, 2)) / den
    k = max(1, len(labels))
    T = float(np.mean(taus)) if taus else 0.0
    null /= k
    p = (1.0 + float(np.count_nonzero(null >= T - 1e-12))) / (1.0 + n_perm)
    return {"T": T, "p_one_sided": p, "tau_by_stratum": dict(zip(map(str, labels), taus)),
            "null_mean": float(null.mean()), "null_q975": float(np.quantile(null, 0.975)),
            "n_units": int(dose.size), "n_strata": len(labels), "n_perm": int(n_perm)}


def paired_mean_se(a: Any, b: Any) -> dict[str, float]:
    """Mean and standard error of the paired difference a - b (NaN pairs dropped)."""
    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    d = d[np.isfinite(d)]
    if d.size == 0:
        return {"mean": float("nan"), "se": float("nan"), "n": 0}
    se = float(d.std(ddof=1) / np.sqrt(d.size)) if d.size > 1 else float("nan")
    return {"mean": float(d.mean()), "se": se, "n": int(d.size)}
