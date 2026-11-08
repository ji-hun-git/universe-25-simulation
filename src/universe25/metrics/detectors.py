"""Eval-only detectors for Burghardt's five criteria (phase 4; docs/PHASE4_DESIGN.md section 2).

Computed after the fact from decision traces (`metrics/trace.py` for simulator runs,
`metrics/synthetic_traces.py` for the synthetic ground truth). No policy, observation builder
or learner may import this module (audited in tests/test_detectors.py), and nothing here feeds
back into the simulation. Every output key ends in `_unvalidated`; the result is a vector of
per-criterion statistics with surrogate z-scores and preregistered decision flags, never a
single score.

Episodes ("kinds"):
  object     MANIPULATE decisions that end in contact with an object
  locomotor  EXPLORE decisions whose displacement exceeds the 90th percentile of the
             displacement of serious moves (FORAGE / DRINK / NEST) in the same trace
Events of a kind are grouped into episodes with a gap criterion from the inter-event gaps: a
maximum-likelihood mixture of two geometric processes that beats one process by BIC (Sibly,
Nott & Fletcher 1990) gives the criterion minimising misassigned gaps (Slater & Lester 1982);
otherwise episodes are runs of consecutive events and `episode_structure_unvalidated` is
False (the falsifier).

Rules v4 (2026-11-07): surrogate shifts move series by whole decisions when the trace has
free-time sub-steps (K rows per decision); the serious template's reversal fraction needs 20
direction pairs, else counts as 0. With K = 1 the shifts and their draws are v3's.

Rules v5 (2026-11-08): criterion 2 counts exogenous triggers only - aggression received, or a
local density jump in the cell the individual occupied at the start of its previous decision
(others arrived). Its own cell entries, and density jumps that come with them, no longer
count; `self_entries=True` restores the v4 trigger set (diagnostics only).

Criteria (decision rules v3, preregistered in PHASE4_DESIGN.md section 2; form
statistics use only the episode's own event decisions; the gap criterion is a
maximum-likelihood one- vs two-process fit, Sibly et al. 1990):
  1 not fully functional  nf_index: fraction of episodes with no survival-drive relief (hunger,
                          thirst, fatigue, stress; curiosity / boredom excluded) that do not end
                          at a hopper or the own nest; null = circular shift of the per-step
                          relief / at-target series within individual.          flag: z > 1.645
  2 spontaneous           onset_trigger_free: fraction of onsets with no exogenous trigger (v5:
                          wound received, or a density jump in an already occupied cell) from
                          the start of the previous decision to the onset (v4 window);
                          null = circular shift of the trigger series. A spontaneous behaviour is
                          not time-locked below chance.                          flag: z >= -1.645
  3 structurally different seq_struct_js: Jensen-Shannon divergence between the movement-symbol
                          transitions inside episodes and inside serious approaches (FORAGE /
                          DRINK runs); null = label permutation over sequences.  flag: z > 1.645
                          (approach-withdraw reversals and amplitude are reported alongside)
  4 repeated, not rigid   rep_rigid_loop_frac: fraction of same-individual episode pairs (length
                          >= 2) with normalised edit distance < 0.2; rep_exposure_slope: slope of
                          log onset rate on log(1 + cumulative exposure). flag: rigid <= 0.2 and
                          slope > -0.5 (entropy rate and recurrence are reported alongside)
  5 relaxed field         gate_relaxed_log_ratio: log P(onset | relaxed) / P(onset | not relaxed);
                          null = circular shift of the relaxed flag.             flag: z > 1.645
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from universe25.agents.state import ACT_DRINK, ACT_EXPLORE, ACT_FORAGE, ACT_MANIPULATE, ACT_NEST

Z95 = 1.6448536269514722
SURVIVAL = ("hunger", "thirst", "fatigue", "stress")
TARGET_RADIUS = 4.0  # inches: ended at a hopper
NEST_RADIUS = 3.0  # inches: ended at the own nest
RELIEF_TOL = 0.02  # summed survival-drive relief below which an episode counts as no relief
DENSITY_JUMP = 0.1  # increase of own-cell density (fraction of design capacity) = trigger
WOUND_HIT = 0.01  # increase of wounds between decisions = aggression received
RECENT_HIT_STEPS = 6
NF_MIN = 0.5  # criterion 1: a majority of episodes without function
TF_RATIO_MIN = 0.8  # criterion 2: locked = trigger-free fraction < 0.8 x chance (and z < -1.645)
REV_MIN = 0.25  # criterion 3: approach-withdraw reversals in >= a quarter of direction pairs
REV_DIFF_MIN = 0.2  # criterion 3: ... and >= 0.2 above the serious sequences (direct move: 0)
GATE_MIN = float(np.log(2.0))  # criterion 5: onsets at least twice as likely when relaxed
RIGID_EPS = 0.2
RIGID_MAX_FRAC = 0.2
EXPOSURE_SLOPE_MIN = -0.5
MIN_EPISODES = 10
GAP_BIC_MARGIN = 10.0  # v3: two-process model must beat one process by this much
REV_TEMPLATE_MIN_PAIRS = 20  # v4: serious reversal fraction below this support counts as 0
MAX_RIGID_PAIRS = 4000
N_SYM = 9  # movement symbols: 3 displacement bins x 3 radial directions
KINDS = ("object", "locomotor")


@dataclass
class Steps:
    """A trace sorted by (uid, step) with per-row derived quantities."""

    n: int
    K: int  # rows per decision (free-time sub-steps); surrogate shifts keep this phase (v4)
    uid: np.ndarray
    step: np.ndarray
    gid: np.ndarray
    gstart: np.ndarray
    glen: np.ndarray
    prev_ok: np.ndarray
    next_ok: np.ndarray
    action: np.ndarray
    contact: np.ndarray
    disp: np.ndarray
    relief: np.ndarray
    at_target: np.ndarray
    trigger: np.ndarray
    relaxed: np.ndarray
    relax_score: np.ndarray
    in_pg: np.ndarray
    obj_id: np.ndarray
    cum_contacts: np.ndarray
    day: np.ndarray
    x: np.ndarray
    y: np.ndarray
    xprev: np.ndarray  # post position of the previous decision (NaN if none)
    yprev: np.ndarray
    ddobj: np.ndarray  # change of the nearest-object distance since the previous decision
    win_lo: np.ndarray  # v4: first row of the trigger window (start of the previous decision)
    age: np.ndarray  # days


def _prev(v: np.ndarray, ok: np.ndarray, fill: float = np.nan) -> np.ndarray:
    out = np.empty_like(v, dtype=np.float64)
    out[0] = fill
    out[1:] = v[:-1]
    return np.where(ok, out, fill)


def prepare(trace: dict[str, Any], max_individuals: int | None = None,
            rng: np.random.Generator | None = None, self_entries: bool = False) -> Steps:
    uid_all = np.asarray(trace["uid"]).astype(np.int64)
    keep = np.ones(uid_all.size, dtype=bool)
    if max_individuals is not None:
        uniq = np.unique(uid_all)
        if uniq.size > max_individuals:
            r = rng if rng is not None else np.random.default_rng(0)
            chosen = np.sort(r.choice(uniq, size=max_individuals, replace=False))
            keep = np.isin(uid_all, chosen)
    idx = np.flatnonzero(keep)
    step_all = np.asarray(trace["step"]).astype(np.int64)
    order = idx[np.lexsort((step_all[idx], uid_all[idx]))]

    def col(k: str, dt: Any = np.float64) -> np.ndarray:
        return np.asarray(trace[k])[order].astype(dt)

    uid = uid_all[order]
    step = step_all[order]
    n = uid.size
    _, gstart, glen = np.unique(uid, return_index=True, return_counts=True)
    gid = np.repeat(np.arange(gstart.size), glen)
    same_prev = np.zeros(n, dtype=bool)
    if n > 1:
        same_prev[1:] = (uid[1:] == uid[:-1]) & (step[1:] == step[:-1] + 1)
    next_ok = np.zeros(n, dtype=bool)
    next_ok[:-1] = same_prev[1:]
    x, y = col("x"), col("y")
    disp = np.hypot(x - _prev(x, same_prev), y - _prev(y, same_prev))
    relief = np.zeros(n)
    for k in SURVIVAL:
        relief += col(f"{k}_post") - col(k)
    relief = np.maximum(0.0, -relief)
    at_target = ((col("food_dist") <= TARGET_RADIUS) | (col("water_dist") <= TARGET_RADIUS)
                 | (col("nest_dist") <= NEST_RADIUS))
    cell = col("cell", np.int64)
    dens = col("cell_density")
    wounds = col("wounds")
    dpd = int(np.asarray(trace.get("meta", {}).get("decisions_per_day", 6)))
    k_sub = max(1, int(np.asarray(trace.get("meta", {}).get("free_substeps", 1))))
    hit = same_prev & ((wounds - _prev(wounds, same_prev, 0.0)) > WOUND_HIT)
    jump = (dens - _prev(dens, same_prev, 0.0)) > DENSITY_JUMP
    if self_entries:  # v4 trigger set (diagnostics): the individual's own cell entries count
        entry = cell != _prev(cell.astype(np.float64), same_prev, -1).astype(np.int64)
        trigger = same_prev & (entry | jump | hit)
    else:  # v5: a density jump counts only in the cell occupied at the previous decision start
        cell_dec = cell[_decision_start(uid, step, k_sub)]
        stayed = cell_dec == _prev(cell_dec.astype(np.float64), same_prev, -1).astype(np.int64)
        trigger = same_prev & ((jump & stayed) | hit)
    recent_hit = _rolling_any(hit, gid, gstart, RECENT_HIT_STEPS)
    conds = np.stack([
        col("hunger") < 0.5, col("thirst") < 0.5, col("energy") > 0.5, col("stress") < 0.4,
        wounds < 0.3, ~recent_hit, dens < 1.0,
    ])
    relaxed = conds.all(axis=0)
    return Steps(
        n=n, K=k_sub,
        uid=uid, step=step, gid=gid, gstart=gstart, glen=glen, prev_ok=same_prev,
        next_ok=next_ok, action=col("action", np.int64), contact=col("contact", np.int64) > 0,
        disp=disp, relief=relief, at_target=at_target, trigger=trigger, relaxed=relaxed,
        relax_score=conds.sum(axis=0), in_pg=col("in_playground", np.int64) > 0,
        obj_id=col("obj_id", np.int64), cum_contacts=col("cum_contacts"),
        day=step // max(1, dpd), x=x, y=y, xprev=_prev(x, same_prev), yprev=_prev(y, same_prev),
        win_lo=_window_start(uid, step, same_prev, k_sub),
        ddobj=col("obj_dist") - _prev(col("obj_dist"), same_prev),
        age=col("age"),
    )


def _rolling_any(flag: np.ndarray, gid: np.ndarray, gstart: np.ndarray, w: int) -> np.ndarray:
    """True where `flag` was True at this row or within the previous w-1 rows of the group."""
    cs = np.concatenate([[0], np.cumsum(flag.astype(np.int64))])
    i = np.arange(flag.size)
    lo = np.maximum(i - (w - 1), gstart[gid])
    return (cs[i + 1] - cs[lo]) > 0


def _shift_index(S: Steps, rng: np.random.Generator) -> np.ndarray:
    """Row index of a circular shift within each individual by a random non-zero number of whole
    decisions (v4: K rows each; with K = 1 exactly v3's arbitrary-row shift and draws)."""
    n_dec = S.glen // S.K
    k = np.where(n_dec > 1, rng.integers(1, np.maximum(n_dec, 2)), 0) * S.K
    o = S.gstart[S.gid]
    return o + (np.arange(S.n) - o + k[S.gid]) % S.glen[S.gid]


def event_mask(S: Steps, kind: str) -> tuple[np.ndarray, float]:
    if kind == "object":
        return (S.action == ACT_MANIPULATE) & S.contact, float("nan")
    if kind != "locomotor":
        raise ValueError(kind)
    serious = np.isin(S.action, (ACT_FORAGE, ACT_DRINK, ACT_NEST)) & np.isfinite(S.disp)
    ref = S.disp[serious & (S.disp > 0.5)]
    if ref.size < 20:
        ref = S.disp[np.isfinite(S.disp) & (S.disp > 0.5)]
    thr = float(np.quantile(ref, 0.9)) if ref.size else float("inf")
    ev = (S.action == ACT_EXPLORE) & np.isfinite(S.disp) & (S.disp > thr)
    return ev, thr


def _geom_mix_fit(g: np.ndarray, iters: int = 300) -> tuple[float, float, float, float]:
    """EM fit of a two-component geometric mixture on gaps >= 1: (log-likelihood, w_fast,
    p_fast, p_slow) with p_fast >= p_slow."""
    g = g.astype(np.float64)
    lo = g <= np.median(g)
    p1 = float(np.clip(1.0 / max(g[lo].mean(), 1.0 + 1e-6), 1e-6, 1 - 1e-9))
    p2 = float(np.clip(1.0 / max(g[~lo].mean() if (~lo).any() else g.mean() * 2, 1.0 + 1e-6),
                       1e-6, 1 - 1e-9))
    w = 0.5
    for _ in range(iters):
        l1 = np.log(w) + np.log(p1) + (g - 1.0) * np.log1p(-p1)
        l2 = np.log(1.0 - w) + np.log(p2) + (g - 1.0) * np.log1p(-p2)
        m = np.maximum(l1, l2)
        r = np.exp(l1 - m) / (np.exp(l1 - m) + np.exp(l2 - m))
        w = float(np.clip(r.mean(), 1e-6, 1 - 1e-6))
        p1 = float(np.clip(r.sum() / max((r * g).sum(), 1e-12), 1e-6, 1 - 1e-9))
        p2 = float(np.clip((1 - r).sum() / max(((1 - r) * g).sum(), 1e-12), 1e-6, 1 - 1e-9))
    l1 = np.log(w) + np.log(p1) + (g - 1.0) * np.log1p(-p1)
    l2 = np.log(1.0 - w) + np.log(p2) + (g - 1.0) * np.log1p(-p2)
    ll = float(np.logaddexp(l1, l2).sum())
    if p2 > p1:
        w, p1, p2 = 1.0 - w, p2, p1
    return ll, w, p1, p2


def gap_criterion(S: Steps, ev: np.ndarray, max_gap: int = 6) -> tuple[int, bool]:
    """Bout-style gap criterion in decision steps (v3). Maximum-likelihood comparison of one
    geometric process against a mixture of two on the inter-event gaps within individuals
    (Sibly, Nott & Fletcher 1990), BIC margin 10 and distinct rates (ratio > 2); the criterion
    minimises the expected misassigned gaps (Slater & Lester 1982), capped at max_gap. A single
    process means no episode structure: (1, False), episodes are runs of consecutive events."""
    e = np.flatnonzero(ev)
    if e.size < 3:
        return 1, False
    same = S.uid[e[1:]] == S.uid[e[:-1]]
    g = (S.step[e[1:]] - S.step[e[:-1]])[same].astype(np.float64)
    if g.size < 30:
        return 1, False
    n = g.size
    p = 1.0 / g.mean()
    if p >= 1.0:  # every gap is 1: one run per individual
        return 1, False
    ll1 = float(np.sum(np.log(p) + (g - 1.0) * np.log1p(-p)))
    ll2, w, pf, ps = _geom_mix_fit(g)
    bic1 = -2.0 * ll1 + 1.0 * np.log(n)
    bic2 = -2.0 * ll2 + 3.0 * np.log(n)
    has_break = bool(bic2 < bic1 - GAP_BIC_MARGIN and pf > 2.0 * ps and 0.02 < w < 0.98)
    if not has_break:
        return 1, False
    cs = np.arange(1, max_gap + 1, dtype=np.float64)
    mis = w * (1.0 - pf) ** cs + (1.0 - w) * (1.0 - (1.0 - ps) ** cs)
    return int(cs[int(np.argmin(mis))]), True


def segment(S: Steps, ev: np.ndarray, c: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Episode start / end row (inclusive) and event count; events of an individual separated
    by at most c decision steps belong to one episode."""
    e = np.flatnonzero(ev)
    if e.size == 0:
        z = np.zeros(0, dtype=np.int64)
        return z, z, z
    new = np.ones(e.size, dtype=bool)
    new[1:] = (S.uid[e[1:]] != S.uid[e[:-1]]) | ((S.step[e[1:]] - S.step[e[:-1]]) > c)
    ep = np.cumsum(new) - 1
    last = np.ones(e.size, dtype=bool)
    last[:-1] = new[1:]
    return e[new], e[last], np.bincount(ep)


def _range_sums(v: np.ndarray, s: np.ndarray, e: np.ndarray) -> np.ndarray:
    cs = np.concatenate([[0.0], np.cumsum(v, dtype=np.float64)])
    return cs[e + 1] - cs[s]


def _z(obs: float, null: np.ndarray) -> float:
    null = null[np.isfinite(null)]
    if not np.isfinite(obs) or null.size < 2:
        return float("nan")
    sd = float(null.std(ddof=1))
    return float((obs - null.mean()) / max(sd, 1e-9))


# ---------------------------------------------------------------- criterion 1
def _nf(relief: np.ndarray, at_target: np.ndarray, s: np.ndarray, e: np.ndarray) -> float:
    r = _range_sums(relief, s, e)
    return float(np.mean((r <= RELIEF_TOL) & ~at_target[e]))


def crit1(S: Steps, s: np.ndarray, e: np.ndarray, B: int, rng: np.random.Generator) -> dict:
    obs = _nf(S.relief, S.at_target, s, e)
    null = np.empty(B)
    for b in range(B):
        j = _shift_index(S, rng)
        null[b] = _nf(S.relief[j], S.at_target[j], s, e)
    return {"nf_index_unvalidated": obs, "nf_index_z_unvalidated": _z(obs, null),
            "nf_index_null_mean_unvalidated": float(null.mean())}


# ---------------------------------------------------------------- criterion 2
def _decision_start(uid: np.ndarray, step: np.ndarray, K: int) -> np.ndarray:
    """Per row (sorted by uid, step), the first row of its own decision (K rows each)."""
    n = uid.size
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    blk = step // K
    new = np.ones(n, dtype=bool)
    new[1:] = (uid[1:] != uid[:-1]) | (blk[1:] != blk[:-1])
    return np.maximum.accumulate(np.where(new, np.arange(n), 0))


def _window_start(uid: np.ndarray, step: np.ndarray, prev_ok: np.ndarray, K: int) -> np.ndarray:
    """v4 trigger window: per row, the first row of the previous decision of the same individual
    when it directly precedes (else the first row of the row's own decision). With K = 1 this is
    the previous row when it is consecutive, else the row itself (v3's window)."""
    n = uid.size
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    blk = step // K
    start = _decision_start(uid, step, K)
    before = start - 1
    ok = before >= 0
    bb = np.where(ok, before, 0)
    prev_start = start[bb]
    linked = ok & (uid[bb] == uid) & (blk[bb] == blk - 1) & prev_ok[start]
    return np.where(linked, prev_start, start)


def _trigger_free(trig: np.ndarray, win_lo: np.ndarray, s: np.ndarray) -> float:
    """Fraction of onsets with no trigger from the window start to the onset row, inclusive."""
    cs = np.concatenate([[0], np.cumsum(trig.astype(np.int64))])
    return float(np.mean((cs[s + 1] - cs[win_lo[s]]) == 0))


def _return_hazard(S: Steps, horizon: int) -> float:
    prev_in = np.zeros(S.n, dtype=bool)
    prev_in[1:] = S.in_pg[:-1]
    exits = np.flatnonzero(S.prev_ok & prev_in & ~S.in_pg)
    if exits.size == 0:
        return float("nan")
    ret = np.zeros(exits.size, dtype=bool)
    for r in range(1, horizon + 1):
        j = exits + r
        ok = j < S.n
        jj = np.where(ok, j, 0)
        hit = ok & (S.uid[jj] == S.uid[exits]) & ((S.step[jj] - S.step[exits]) == r) & S.in_pg[jj]
        ret |= hit
    return float(ret.mean())


def crit2(S: Steps, s: np.ndarray, B: int, rng: np.random.Generator, horizon: int) -> dict:
    obs = _trigger_free(S.trigger, S.win_lo, s)
    null = np.empty(B)
    for b in range(B):
        j = _shift_index(S, rng)
        null[b] = _trigger_free(S.trigger[j], S.win_lo, s)
    return {"onset_trigger_free_unvalidated": obs,
            "onset_trigger_free_z_unvalidated": _z(obs, null),
            "onset_trigger_free_null_mean_unvalidated": float(null.mean()),
            "return_hazard_unvalidated": _return_hazard(S, horizon)}


# ---------------------------------------------------------------- symbols and sequences
def _seq_rows(s: np.ndarray, e: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Expanded row indices and sequence ids for inclusive row ranges [s, e]."""
    lens = e - s + 1
    seq = np.repeat(np.arange(s.size), lens)
    base = np.repeat(s - np.concatenate([[0], np.cumsum(lens)[:-1]]), lens)
    return base + np.arange(lens.sum()), seq


def _seq_symbols(S: Steps, s: np.ndarray, e: np.ndarray
                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Movement symbols per expanded row of the sequences [s, e]: 3 x displacement bin (< 2,
    2-10, > 10 in) + radial direction relative to the sequence's own end point (approach
    < -1 in, withdraw > +1 in, neutral). The end-point reference makes the code
    target-agnostic: a goal-directed approach reads as steady approach whatever the goal, an
    approach-withdraw alternation as alternation. Returns rows, seq, symbol (-1 undefined) and
    the radial change."""
    rows, seq = _seq_rows(s, e)
    if rows.size == 0:
        z = np.zeros(0, dtype=np.int64)
        return z, z, z, np.zeros(0)
    xf, yf = S.x[e][seq], S.y[e][seq]
    d_now = np.hypot(S.x[rows] - xf, S.y[rows] - yf)
    d_prev = np.hypot(S.xprev[rows] - xf, S.yprev[rows] - yf)
    delta = d_now - d_prev
    disp = S.disp[rows]
    dbin = np.where(disp < 2.0, 0, np.where(disp < 10.0, 1, 2))
    dirb = np.where(delta < -1.0, 0, np.where(delta > 1.0, 1, 2))
    ok = np.isfinite(disp) & np.isfinite(delta)
    return rows, seq, np.where(ok, 3 * dbin + dirb, -1), delta


def _pair_counts(sym: np.ndarray, seq: np.ndarray, n_seq: int, n_sym: int) -> np.ndarray:
    """Transition counts per sequence from symbols aligned with expanded rows."""
    if sym.size < 2:
        return np.zeros((n_seq, n_sym * n_sym))
    a, b = sym[:-1], sym[1:]
    ok = (seq[:-1] == seq[1:]) & (a >= 0) & (b >= 0)
    code = seq[:-1][ok] * (n_sym * n_sym) + a[ok] * n_sym + b[ok]
    return np.bincount(code, minlength=n_seq * n_sym * n_sym).reshape(n_seq, n_sym * n_sym)


def _serious_runs(S: Steps, context: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Maximal FORAGE and DRINK runs (optionally with the move into the run)."""
    st_all, en_all = [], []
    for act in (ACT_FORAGE, ACT_DRINK):
        m = S.action == act
        if not m.any():
            continue
        r = np.flatnonzero(m)
        new = np.ones(r.size, dtype=bool)
        new[1:] = ~(S.prev_ok[r[1:]] & (r[1:] == r[:-1] + 1))
        last = np.ones(r.size, dtype=bool)
        last[:-1] = new[1:]
        st, en = r[new], r[last]
        st_all.append(np.where(S.prev_ok[st] & context, st - 1, st))
        en_all.append(en)
    if not st_all:
        z = np.zeros(0, dtype=np.int64)
        return z, z
    return np.concatenate(st_all), np.concatenate(en_all)


def _js_bits(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    m = 0.5 * (p + q)
    with np.errstate(divide="ignore", invalid="ignore"):
        kp = np.where(p > 0, p * np.log2(p / m), 0.0).sum(axis=-1)
        kq = np.where(q > 0, q * np.log2(q / m), 0.0).sum(axis=-1)
    return 0.5 * (kp + kq)


def _seq_stats(S: Steps, s: np.ndarray, e: np.ndarray,
               ev: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Per sequence: transition counts (n x 81) and [reversals, direction pairs, disp sum,
    disp sum of squares, disp n]."""
    n_seq = s.size
    rows, seq, sym, delta = _seq_symbols(S, s, e)
    if ev is not None:  # v2: only the episode's own decisions carry form
        own = ev[rows]
        sym = np.where(own, sym, -1)
        delta = np.where(own, delta, 0.0)
    counts = _pair_counts(sym, seq, n_seq, N_SYM)
    extra = np.zeros((n_seq, 5))
    if rows.size:
        d = np.where(delta < -1.0, -1, np.where(delta > 1.0, 1, 0))
        if rows.size > 1:
            ok = (seq[:-1] == seq[1:]) & (d[:-1] != 0) & (d[1:] != 0)
            rev = ok & (d[:-1] != d[1:])
            extra[:, 0] = np.bincount(seq[:-1][rev], minlength=n_seq)
            extra[:, 1] = np.bincount(seq[:-1][ok], minlength=n_seq)
        dv = S.disp[rows] if ev is None else np.where(ev[rows], S.disp[rows], np.nan)
        fin = np.isfinite(dv)
        extra[:, 2] = np.bincount(seq[fin], weights=dv[fin], minlength=n_seq)
        extra[:, 3] = np.bincount(seq[fin], weights=dv[fin] ** 2, minlength=n_seq)
        extra[:, 4] = np.bincount(seq[fin], minlength=n_seq)
    return counts, extra


def crit3(S: Steps, ev: np.ndarray, s: np.ndarray, e: np.ndarray, B: int,
          rng: np.random.Generator) -> dict:
    """Within-sequence form against serious FORAGE / DRINK runs, both without context steps,
    radial direction relative to each sequence's own end point. Decision statistic: the
    approach-withdraw reversal fraction of episodes and its excess over serious sequences (a
    direct move has no reversal pair and counts as 0); null = label permutation over
    sequences. Movement-transition JS divergence and amplitude are reported alongside."""
    nan = float("nan")
    res = {k: nan for k in ("seq_struct_js_unvalidated", "seq_struct_js_z_unvalidated",
                            "seq_struct_reversal_unvalidated",
                            "seq_struct_reversal_diff_unvalidated",
                            "seq_struct_reversal_z_unvalidated", "seq_struct_amp_unvalidated",
                            "seq_struct_amp_z_unvalidated")}
    res["seq_struct_reversal_pairs_unvalidated"] = 0.0
    ss, se = _serious_runs(S, context=False)
    c1, x1 = _seq_stats(S, s, e, ev)
    if ss.size:
        c0, x0 = _seq_stats(S, ss, se)
    else:
        c0, x0 = np.zeros((0, c1.shape[1])), np.zeros((0, 5))
    C = np.vstack([c1, c0]).astype(np.float64)
    X = np.vstack([x1, x0])
    lab = np.concatenate([np.ones(s.size, bool), np.zeros(ss.size, bool)])
    pairs_ep = float(x1[:, 1].sum())
    res["seq_struct_reversal_pairs_unvalidated"] = pairs_ep
    if pairs_ep < 10:
        return res

    def stats(mask: np.ndarray) -> tuple[np.ndarray, ...]:
        """mask: (b, n_seq) boolean group-1 membership -> js, rev1, rev diff, amp effect."""
        m = mask.astype(np.float64)
        g1 = m @ C
        g0 = C.sum(axis=0)[None, :] - g1
        with np.errstate(divide="ignore", invalid="ignore"):
            p = (g1 + 0.5) / (g1.sum(axis=1, keepdims=True) + 0.5 * C.shape[1])
            q = (g0 + 0.5) / (g0.sum(axis=1, keepdims=True) + 0.5 * C.shape[1])
            js = np.where((g1.sum(axis=1) >= 5) & (g0.sum(axis=1) >= 5), _js_bits(p, q), np.nan)
            y1 = m @ X
            y0 = X.sum(axis=0)[None, :] - y1
            rev1 = y1[:, 0] / y1[:, 1]
            rev0 = np.where(y0[:, 1] >= REV_TEMPLATE_MIN_PAIRS,
                            y0[:, 0] / np.maximum(y0[:, 1], 1e-12), 0.0)
            m1, m0 = y1[:, 2] / y1[:, 4], y0[:, 2] / y0[:, 4]
            tot_n = y1[:, 4] + y0[:, 4]
            var = (y1[:, 3] + y0[:, 3]) / tot_n - ((y1[:, 2] + y0[:, 2]) / tot_n) ** 2
            amp = (m1 - m0) / np.sqrt(np.maximum(var, 1e-9))
        return js, rev1, rev1 - rev0, amp

    js, rev1, rdiff, amp = (float(v[0]) for v in stats(lab[None, :]))
    nulls: tuple[list, list, list, list] = ([], [], [], [])
    done = 0
    if ss.size:
        while done < B:
            nb = min(100, B - done)
            perm = np.stack([rng.permutation(lab) for _ in range(nb)])
            for acc, v in zip(nulls, stats(perm)):
                acc.append(v)
            done += nb
    nj, _, nd, na = (np.concatenate(v) if v else np.zeros(0) for v in nulls)
    res.update({
        "seq_struct_js_unvalidated": js, "seq_struct_js_z_unvalidated": _z(js, nj),
        "seq_struct_reversal_unvalidated": rev1, "seq_struct_reversal_diff_unvalidated": rdiff,
        "seq_struct_reversal_z_unvalidated": _z(rdiff, nd) if ss.size else float("inf"),
        "seq_struct_amp_unvalidated": amp, "seq_struct_amp_z_unvalidated": _z(amp, na),
    })
    return res


# ---------------------------------------------------------------- criterion 4
def _levenshtein(a: list[int], b: list[int]) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _entropy_rate(pairs_a: np.ndarray, pairs_b: np.ndarray, n_sym: int) -> float:
    if pairs_a.size < 2:
        return float("nan")
    joint = np.bincount(pairs_a * n_sym + pairs_b, minlength=n_sym * n_sym).astype(np.float64)
    joint = joint.reshape(n_sym, n_sym)
    tot = joint.sum()
    row = joint.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -np.where(joint > 0, joint / tot * np.log2(joint / row), 0.0).sum()
    return float(h)


def _pairs_within(sym: np.ndarray, seq: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if sym.size < 2:
        z = np.zeros(0, dtype=np.int64)
        return z, z
    ok = (seq[:-1] == seq[1:]) & (sym[:-1] >= 0) & (sym[1:] >= 0)
    return sym[:-1][ok], sym[1:][ok]


def crit4(S: Steps, kind: str, ev: np.ndarray, s: np.ndarray, e: np.ndarray, cand: np.ndarray,
          onset: np.ndarray, B: int, rng: np.random.Generator) -> dict:
    rows, seq, sym9, _ = _seq_symbols(S, s, e)
    if kind == "object":  # object-centred: the object is the fixed point of the form
        disp = S.disp[rows]
        dbin = np.where(disp < 2.0, 0, np.where(disp < 10.0, 1, 2))
        dd = S.ddobj[rows]
        dirb = np.where(dd < -1.0, 0, np.where(dd > 1.0, 1, 2))
        sym9 = np.where(np.isfinite(disp) & np.isfinite(dd), 3 * dbin + dirb, -1)
        prev_obj = np.zeros_like(S.obj_id)
        prev_obj[1:] = S.obj_id[:-1]
        switch = (S.prev_ok & (S.obj_id != prev_obj)).astype(np.int64)[rows]
    else:
        switch = np.zeros(rows.size, dtype=np.int64)
    sym = np.where((sym9 >= 0) & ev[rows], sym9 + N_SYM * switch, -1)  # v2: own decisions
    out: dict[str, float] = {}
    # rigid loops: same-individual pairs of episodes with >= 2 defined symbols
    strings: dict[int, list[list[int]]] = {}
    bounds = np.concatenate([[0], np.cumsum(e - s + 1)])
    for q in range(s.size):
        st = [int(v) for v in sym[bounds[q]:bounds[q + 1]] if v >= 0]
        if len(st) >= 2:
            strings.setdefault(int(S.uid[s[q]]), []).append(st)
    pairs = [(u, i, j) for u, lst in strings.items() for i in range(len(lst))
             for j in range(i + 1, len(lst))]
    if len(pairs) > MAX_RIGID_PAIRS:
        pick = rng.choice(len(pairs), size=MAX_RIGID_PAIRS, replace=False)
        pairs = [pairs[k] for k in pick]
    if len(pairs) >= 10:
        close = [(_levenshtein(strings[u][i], strings[u][j])
                  / max(len(strings[u][i]), len(strings[u][j]))) < RIGID_EPS
                 for u, i, j in pairs]
        out["rep_rigid_loop_frac_unvalidated"] = float(np.mean(close))
    else:
        out["rep_rigid_loop_frac_unvalidated"] = float("nan")
    out["rep_rigid_pairs_unvalidated"] = float(len(pairs))
    # entropy rate of within-episode transitions, null = within-episode shuffle
    n18 = 2 * N_SYM
    pa, pb = _pairs_within(sym, seq)
    h = _entropy_rate(pa, pb, n18)
    null = np.empty(B)
    for b in range(B):
        order = np.lexsort((rng.random(sym.size), seq))
        qa, qb = _pairs_within(sym[order], seq[order])
        null[b] = _entropy_rate(qa, qb, n18)
    out["rep_entropy_rate_unvalidated"] = h
    out["rep_entropy_rate_z_unvalidated"] = _z(h, null)
    # recurrence across days, null = the individual's episodes at random steps of its record
    ep_uid = S.uid[s]
    uids, inv = np.unique(ep_uid, return_inverse=True)
    big, small = np.iinfo(np.int64).max, np.iinfo(np.int64).min
    if uids.size:
        dmin = np.full(uids.size, big)
        dmax = np.full(uids.size, small)
        np.minimum.at(dmin, inv, S.day[s])
        np.maximum.at(dmax, inv, S.day[s])
        g = np.searchsorted(S.uid[S.gstart], uids)
        lo, n_rows = S.gstart[g], S.glen[g]
        span_ok = (S.day[lo + n_rows - 1] - S.day[lo]) >= 1
        rec = float(np.mean((dmax > dmin)[span_ok])) if span_ok.any() else float("nan")
        rnull = np.empty(min(B, 200))
        for b in range(rnull.size):
            pos = lo[inv] + (rng.random(inv.size) * n_rows[inv]).astype(np.int64)
            a1 = np.full(uids.size, big)
            a2 = np.full(uids.size, small)
            np.minimum.at(a1, inv, S.day[pos])
            np.maximum.at(a2, inv, S.day[pos])
            rnull[b] = np.mean((a2 > a1)[span_ok]) if span_ok.any() else np.nan
        out["rep_recurrence_unvalidated"] = rec
        out["rep_recurrence_z_unvalidated"] = _z(rec, rnull)
    else:
        out["rep_recurrence_unvalidated"] = float("nan")
        out["rep_recurrence_z_unvalidated"] = float("nan")
    # engagement vs cumulative exposure (object contacts, or the kind's own events)
    if kind == "object":
        expo = S.cum_contacts - S.contact.astype(np.float64)
    else:
        cs = np.cumsum(ev.astype(np.float64))
        base = np.concatenate([[0.0], cs])[S.gstart[S.gid]]
        expo = cs - ev - base
    xx = np.log1p(np.maximum(expo[cand], 0.0))
    yy = onset[cand].astype(np.float64)
    slope = float("nan")
    if xx.size >= 60:
        edges = np.unique(np.quantile(xx, np.linspace(0, 1, 7)))
        if edges.size >= 3:
            b_id = np.clip(np.searchsorted(edges, xx, side="right") - 1, 0, edges.size - 2)
            cnt = np.bincount(b_id, minlength=edges.size - 1).astype(np.float64)
            on = np.bincount(b_id, weights=yy, minlength=edges.size - 1)
            mx = np.bincount(b_id, weights=xx, minlength=edges.size - 1)
            use = cnt >= 20
            if use.sum() >= 3:
                rate = on[use] / cnt[use]
                xm = mx[use] / cnt[use]
                w = cnt[use]
                lr = np.log(rate + 1e-3)
                xb = np.average(xm, weights=w)
                yb = np.average(lr, weights=w)
                den = np.sum(w * (xm - xb) ** 2)
                if den > 0:
                    slope = float(np.sum(w * (xm - xb) * (lr - yb)) / den)
    out["rep_exposure_slope_unvalidated"] = slope
    return out


# ---------------------------------------------------------------- criterion 5
def _log_ratio(relaxed: np.ndarray, cand: np.ndarray, onset: np.ndarray) -> float:
    r = relaxed[cand]
    o = onset[cand]
    on_r, n_r = float(o[r].sum()), float(r.sum())
    on_n, n_n = float(o[~r].sum()), float((~r).sum())
    return float(np.log((on_r + 0.5) / (n_r + 1.0)) - np.log((on_n + 0.5) / (n_n + 1.0)))


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 3 or np.all(a == a[0]) or np.all(b == b[0]):
        return float("nan")
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    return float(np.corrcoef(ra, rb)[0, 1])


def crit5(S: Steps, cand: np.ndarray, onset: np.ndarray, B: int,
          rng: np.random.Generator) -> dict:
    obs = _log_ratio(S.relaxed, cand, onset)
    null = np.empty(B)
    for b in range(B):
        j = _shift_index(S, rng)
        null[b] = _log_ratio(S.relaxed[j], cand, onset)
    sc = S.relax_score[cand]
    on = onset[cand]
    vals, rates = [], []
    for v in np.unique(sc):
        m = sc == v
        if m.sum() >= 20:
            vals.append(v)
            rates.append(on[m].mean())
    return {"gate_relaxed_log_ratio_unvalidated": obs,
            "gate_relaxed_z_unvalidated": _z(obs, null),
            "gate_dose_spearman_unvalidated": _spearman(np.array(vals, float),
                                                        np.array(rates, float))}


# ---------------------------------------------------------------- driver
def decisions(r: dict[str, float]) -> dict[str, bool]:
    """Preregistered per-criterion flags (PHASE4_DESIGN.md section 2); NaN reads as False."""
    def gt(k: str, v: float) -> bool:
        x = r.get(k, float("nan"))
        return bool(np.isfinite(x) and x > v)

    def ge(k: str, v: float) -> bool:
        x = r.get(k, float("nan"))
        return bool(np.isfinite(x) and x >= v)

    def le(k: str, v: float) -> bool:
        x = r.get(k, float("nan"))
        return bool(np.isfinite(x) and x <= v)

    tf = r.get("onset_trigger_free_unvalidated", float("nan"))
    tf0 = r.get("onset_trigger_free_null_mean_unvalidated", float("nan"))
    tfz = r.get("onset_trigger_free_z_unvalidated", float("nan"))
    locked = bool(np.isfinite(tf) and np.isfinite(tf0) and np.isfinite(tfz) and tf0 > 0
                  and tf / tf0 < TF_RATIO_MIN and tfz < -Z95)
    return {
        "c1_not_functional": gt("nf_index_z_unvalidated", Z95)
        and ge("nf_index_unvalidated", NF_MIN),
        "c2_spontaneous": bool(np.isfinite(tf)) and not locked,
        "c3_structurally_different": ge("seq_struct_reversal_unvalidated", REV_MIN)
        and ge("seq_struct_reversal_diff_unvalidated", REV_DIFF_MIN)
        and gt("seq_struct_reversal_z_unvalidated", Z95),
        "c4_repeated_not_rigid": le("rep_rigid_loop_frac_unvalidated", RIGID_MAX_FRAC)
        and gt("rep_exposure_slope_unvalidated", EXPOSURE_SLOPE_MIN),
        "c5_relaxed_field": gt("gate_relaxed_z_unvalidated", Z95)
        and ge("gate_relaxed_log_ratio_unvalidated", GATE_MIN),
    }


def detect_kind(S: Steps, kind: str, n_surrogates: int = 1000, seed: int = 0,
                decisions_per_day: int = 6) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    ev, thr = event_mask(S, kind)
    c, has_break = gap_criterion(S, ev, max_gap=decisions_per_day)
    s, e, n_ev = segment(S, ev, c)
    in_ep = np.zeros(S.n + 1, dtype=np.int64)
    np.add.at(in_ep, s, 1)
    np.add.at(in_ep, e + 1, -1)
    inside = np.cumsum(in_ep)[:-1] > 0
    onset = np.zeros(S.n, dtype=bool)
    onset[s] = True
    cand = ~inside | onset
    base: dict[str, Any] = {
        "kind": kind,
        "n_individuals": int(S.gstart.size),
        "n_steps": int(S.n),
        "n_events": int(ev.sum()),
        "n_episodes": int(s.size),
        "mean_episode_events": float(n_ev.mean()) if n_ev.size else 0.0,
        "gap_criterion_steps": int(c),
        "episode_structure_unvalidated": bool(has_break),
        "locomotor_disp_threshold": thr,
        "n_surrogates": int(n_surrogates),
    }
    if s.size < MIN_EPISODES:
        base["note"] = f"fewer than {MIN_EPISODES} episodes: criteria not evaluated"
        base["decisions_unvalidated"] = {k: False for k in decisions({})}
        return base
    base.update(crit1(S, s, e, n_surrogates, rng))
    base.update(crit2(S, s, n_surrogates, rng, horizon=decisions_per_day))
    base.update(crit3(S, ev, s, e, n_surrogates, rng))
    base.update(crit4(S, kind, ev, s, e, cand, onset, n_surrogates, rng))
    base.update(crit5(S, cand, onset, n_surrogates, rng))
    base["decisions_unvalidated"] = decisions(base)
    return base


def detect_trace(trace: dict[str, Any], kinds: tuple[str, ...] = KINDS, n_surrogates: int = 1000,
                 seed: int = 0, max_individuals: int | None = None, self_entries: bool = False,
                 weaned_age: float = 21.0) -> dict[str, Any]:
    """Both episode kinds of one trace window, plus the relaxed share of weaned rows (age >=
    `weaned_age`, the config's biology.weaning_days) of the individuals read: the dose of H-e."""
    meta = trace.get("meta", {})
    dpd = int(np.asarray(meta.get("decisions_per_day", 6)))
    S = prepare(trace, max_individuals=max_individuals, rng=np.random.default_rng(seed + 17),
                self_entries=self_entries)
    weaned = S.age >= weaned_age
    out: dict[str, Any] = {
        "n_rows": int(S.n), "n_individuals": int(S.gstart.size),
        "rules": "v4_self_entries" if self_entries else "v5",
        "n_rows_weaned": int(weaned.sum()),
        "relaxed_share_weaned": float(S.relaxed[weaned].mean()) if weaned.any() else float("nan"),
    }
    for k in kinds:
        out[k] = detect_kind(S, k, n_surrogates=n_surrogates, seed=seed, decisions_per_day=dpd)
    return out
