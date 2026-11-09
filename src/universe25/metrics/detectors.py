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
With action space v2 (PHASE4_DESIGN.md 1.8) the kinds cover the action families: object =
MANIPULATE / BACK_OFF / CIRCLE in contact, locomotor = EXPLORE / RUN_ON / TURN_BACK; identical
on traces without the new actions.
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

Rules v6 (2026-11-09): criteria 3 and 4 also need a form beyond chance - the episodes'
approach-withdraw reversal fraction must beat a within-episode order shuffle of the same
direction labels (excess >= 0.10 and z > 1.645; own random stream, so every v5 statistic is
unchanged). A random walk has the reversal fraction of its own shuffle. The v5 flags stay in the
output as `decisions_v5_unvalidated`.

Rules v9 (2026-11-09): v8 with v7's locomotor threshold restored (v8 failed one synthetic
check: its fixed threshold let random walks meet the form test in 4 of 30 colonies).

Rules v8 (2026-11-09, Tier 1, PHASE4_DESIGN.md section 2; not adopted): criterion 5's
candidate rows are
only rows where a free action was eligible (weaned, no reflex in force: the simulator's mask read
from the row's pre-decision drives); the even-mix re-simulation re-gates object rows on contact
(trace field `obj_r`); an own-action permutation re-simulation is reported as an order
diagnostic (`seq_struct_order_*`, not a flag); locomotor events are locomotor-family rows whose
displacement exceeds the movement model's EXPLORE sigma per row. The v7, v6 and v5 flags come
from a second pass with the v7 definitions (`decisions_v7/v6/v5_unvalidated`).

Rules v7 (2026-11-09, P4-13): the form test's null is a replay of a reference policy. Each
episode is replayed 1,000 times from its start position and heading; its own event rows get an
action drawn uniformly from the kind's family (locomotor EXPLORE / RUN_ON / TURN_BACK, object
MANIPULATE / BACK_OFF / CIRCLE), moved by the simulator's mechanics (move model from the trace
meta, objects held where the trace saw them); other rows keep their observed displacement. The
reversal fraction is computed on each replayed path as on the observed one. Under action space
v2 the heading-relative primitives order the labels of any random mixer, which a label shuffle
removes; the replay keeps it. Own random stream ([seed, 7]). The v6 shuffle statistics are kept
as `seq_struct_form_shuffle_*` and the v6 flags as `decisions_v6_unvalidated`.

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
  3 structurally different seq_struct_reversal: approach-withdraw reversal fraction of the
                          episodes (radial direction to each sequence's own end point), its
                          excess over serious FORAGE / DRINK runs; null = label permutation over
                          sequences. flag: reversal >= 0.25, excess >= 0.2, z > 1.645, and (v6)
                          the form test (JS divergence and amplitude are reported alongside)
  4 repeated, not rigid   rep_rigid_loop_frac: fraction of same-individual episode pairs (length
                          >= 2) with normalised edit distance < 0.2; rep_exposure_slope: slope of
                          log onset rate on log(1 + cumulative exposure). flag: rigid <= 0.2,
                          slope > -0.5 and (v6) the form test (entropy rate and recurrence are
                          reported alongside)
  5 relaxed field         gate_relaxed_log_ratio: log P(onset | relaxed) / P(onset | not relaxed);
                          null = circular shift of the relaxed flag.             flag: z > 1.645
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from universe25.agents.state import (
    ACT_BACK_OFF,
    ACT_CIRCLE,
    ACT_DRINK,
    ACT_EXPLORE,
    ACT_FORAGE,
    ACT_MANIPULATE,
    ACT_NEST,
    ACT_RUN_ON,
    ACT_TURN_BACK,
    LOCO_FAMILY,
    OBJECT_FAMILY,
)

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
FORM_MIN_EXCESS = 0.10  # v6: reversal fraction >= order-shuffle mean + 0.10 (and z > 1.645)
RESIM_CHUNK = 50  # v7: replays computed together (memory: rows x chunk floats per array)
MAX_RIGID_PAIRS = 4000
N_SYM = 9  # movement symbols: 3 displacement bins x 3 radial directions
KINDS = ("object", "locomotor")
RULES = "v9"  # rule-set label written into every detector output
# v8 eligibility: the simulator's reflex mask (sim._select_actions) and the weaning age
REFLEX_DRIVE = 0.85  # thirst or hunger above this forces DRINK / FORAGE
REFLEX_FATIGUE = 1.2  # fatigue above this, with hunger and thirst below REFLEX_CLEAR, forces REST
REFLEX_CLEAR = 0.7
WEANED_AGE = 21.0  # biology.weaning_days of the calibrated colony
CONTACT_SLACK_IN = 1.0  # the trace's contact rule (metrics/trace.py CONTACT_SLACK)
LOCO_CODES = (ACT_EXPLORE, ACT_RUN_ON, ACT_TURN_BACK)
OBJ_CODES = (ACT_MANIPULATE, ACT_BACK_OFF, ACT_CIRCLE)


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
    obj_x: np.ndarray  # v7: nearest object's position at the row (NaN if not recorded)
    obj_y: np.ndarray
    move: dict  # v7: movement model per row (trace meta, else defaults from K)
    obj_r: np.ndarray  # v8: nearest object's radius (NaN if not recorded)
    eligible: np.ndarray  # v8: a free action was eligible at the row's decision
    sim_trace: bool  # v8: a simulator trace (primitive mechanics), not a synthetic one


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
        obj_x=col("obj_x") if "obj_x" in trace else np.full(n, np.nan),
        obj_y=col("obj_y") if "obj_y" in trace else np.full(n, np.nan),
        move=move_model(trace.get("meta", {}), k_sub),
        obj_r=col("obj_r") if "obj_r" in trace else np.full(n, np.nan),
        eligible=_eligible(col("age"), col("hunger"), col("thirst"), col("fatigue"))[
            _decision_start(uid, step, k_sub)],
        sim_trace="synthetic_class" not in trace.get("meta", {}),
    )


def _eligible(age: np.ndarray, hunger: np.ndarray, thirst: np.ndarray,
              fatigue: np.ndarray) -> np.ndarray:
    """v8: weaned and no reflex in force (the simulator's mask), from pre-decision drives."""
    forced = ((thirst > REFLEX_DRIVE) | (hunger > REFLEX_DRIVE)
              | ((fatigue > REFLEX_FATIGUE) & (hunger < REFLEX_CLEAR) & (thirst < REFLEX_CLEAR)))
    return (age >= WEANED_AGE) & ~forced


def move_model(meta: dict[str, Any], K: int) -> dict[str, float]:
    """Per-row movement model for the v7 replay: the trace's meta entries, else the
    simulator's defaults at K rows per decision (ticks_per_day_ref 6, 101-in pen)."""
    sd = 10.0 * (1.0 / 6.0) * 10 / np.sqrt(K)

    def g(k: str, v: float) -> float:
        return float(np.asarray(meta.get(k, v)))

    return {"explore_sd": g("move_explore_sd", sd),
            "run_len": g("move_run_len", sd * np.sqrt(np.pi / 2)),
            "manip_step": g("move_manip_step", 7.0 * 4.0 / K),
            "back_off": g("move_back_off", 0.6 * g("move_manip_step", 7.0 * 4.0 / K)),
            "width": g("world_width", 101.0), "height": g("world_height", 101.0)}


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


def event_mask(S: Steps, kind: str, fixed: bool = True) -> tuple[np.ndarray, float]:
    """Object events: object-family rows in contact. Locomotor events: locomotor-family rows
    above a displacement threshold, v8 the movement model's EXPLORE sigma per row (`fixed`);
    v7 and earlier the 90th percentile of the same trace's serious moves."""
    if kind == "object":
        return np.isin(S.action, OBJECT_FAMILY) & S.contact, float("nan")
    if kind != "locomotor":
        raise ValueError(kind)
    if fixed:
        thr = float(S.move["explore_sd"])
        return np.isin(S.action, LOCO_FAMILY) & np.isfinite(S.disp) & (S.disp > thr), thr
    serious = np.isin(S.action, (ACT_FORAGE, ACT_DRINK, ACT_NEST)) & np.isfinite(S.disp)
    ref = S.disp[serious & (S.disp > 0.5)]
    if ref.size < 20:
        ref = S.disp[np.isfinite(S.disp) & (S.disp > 0.5)]
    thr = float(np.quantile(ref, 0.9)) if ref.size else float("inf")
    ev = np.isin(S.action, LOCO_FAMILY) & np.isfinite(S.disp) & (S.disp > thr)
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


def _form_labels(S: Steps, ev: np.ndarray, s: np.ndarray, e: np.ndarray):
    """Rows, sequence ids, own flags and approach (-1) / withdraw (+1) / neutral (0) labels of
    the episodes' own event rows (radial change relative to each episode's end point)."""
    rows, seq, _, delta = _seq_symbols(S, s, e)
    own = ev[rows] if rows.size else np.zeros(0, dtype=bool)
    d = np.where(own, np.where(delta < -1.0, -1, np.where(delta > 1.0, 1, 0)), 0)
    return rows, seq, own, d


def _reversal_frac(d: np.ndarray, link: np.ndarray) -> float:
    ok = link & (d[:-1] != 0) & (d[1:] != 0)
    n = int(ok.sum())
    return float((ok & (d[:-1] != d[1:])).sum() / n) if n >= 10 else float("nan")


def form_test(S: Steps, ev: np.ndarray, s: np.ndarray, e: np.ndarray, B: int,
              rng: np.random.Generator) -> dict:
    """Rules v6 (kept as `seq_struct_form_shuffle_*`): the episodes' approach-withdraw reversal
    fraction (criterion 3's statistic:
    own event decisions, radial direction to each episode's end point) against a within-episode
    order shuffle of the same direction labels. The own rows keep their positions and their
    labels are permuted, so the pairs that can form are those of the observed episodes. A random
    walk has the reversal fraction of its own shuffle; an alternating form exceeds it."""
    nan = float("nan")
    out = {"seq_struct_form_shuffle_excess_unvalidated": nan,
           "seq_struct_form_shuffle_z_unvalidated": nan,
           "seq_struct_form_shuffle_null_mean_unvalidated": nan}
    rows, seq, own, d = _form_labels(S, ev, s, e)
    if rows.size < 2:
        return out
    link = seq[:-1] == seq[1:]
    obs = _reversal_frac(d, link)
    if not np.isfinite(obs):
        return out
    idx = np.flatnonzero(own)
    null = np.empty(B)
    dd = d.copy()
    for b in range(B):
        dd[idx] = d[idx[np.lexsort((rng.random(idx.size), seq[idx]))]]
        null[b] = _reversal_frac(dd, link)
    fin = null[np.isfinite(null)]
    if fin.size < 2:
        return out
    out["seq_struct_form_shuffle_excess_unvalidated"] = float(obs - fin.mean())
    out["seq_struct_form_shuffle_z_unvalidated"] = _z(obs, fin)
    out["seq_struct_form_shuffle_null_mean_unvalidated"] = float(fin.mean())
    return out


def form_resim(S: Steps, kind: str, ev: np.ndarray, s: np.ndarray, e: np.ndarray, B: int,
               rng: np.random.Generator, regate: bool = True, mode: str = "even",
               prefix: str = "seq_struct_form") -> dict:
    """The episodes' reversal fraction against B re-simulations of each episode under the
    simulator's mechanics, starting from the position before the episode's first row with the
    heading of the move into it (uniform if unknown); rows that are not own events keep their
    observed displacement; walls clip; labels and pairs as on the observed path.
    - mode "even" (rules v7 / v8 form test): own event rows get an action drawn uniformly from
      the kind's family (locomotor EXPLORE / RUN_ON / TURN_BACK, object MANIPULATE / BACK_OFF /
      CIRCLE); EXPLORE steps are drawn from the movement model.
    - mode "perm" (v8 order diagnostic): the episode's own actions in a random order, each
      EXPLORE keeping its observed step vector. Needs a simulator trace (`sim_trace`).
    - regate (v8): an object row of the re-simulated path counts as an event only in contact
      (distance to its object <= obj_r + 1 in); needs `obj_r`, else no re-gating (reported).
    Object re-simulations need `obj_x` / `obj_y`; without them the result is NaN."""
    nan = float("nan")
    out = {f"{prefix}_excess_unvalidated": nan, f"{prefix}_z_unvalidated": nan,
           f"{prefix}_null_mean_unvalidated": nan, f"{prefix}_regated_unvalidated": False}
    rows, seq, own, d = _form_labels(S, ev, s, e)
    if rows.size < 2:
        return out
    link = seq[:-1] == seq[1:]
    obs = _reversal_frac(d, link)
    if not np.isfinite(obs):
        return out
    obj = kind == "object"
    if obj and not np.all(np.isfinite(S.obj_x[rows[own]])):
        return out
    if mode == "perm" and not S.sim_trace:
        return out
    regate = bool(regate and obj and np.all(np.isfinite(S.obj_r[rows[own]])))
    out[f"{prefix}_regated_unvalidated"] = regate
    mv = S.move
    W, H = mv["width"], mv["height"]
    n_seq = s.size
    L = e - s + 1
    order = np.argsort(-L, kind="stable")  # longest first: active episodes form a prefix
    Ls = L[order]
    ss = s[order]
    maxL = int(Ls[0])
    # start position (before the first row) and the first row's label availability
    sx, sy = S.xprev[ss], S.yprev[ss]
    no_start = ~np.isfinite(sx)
    sx = np.where(no_start, S.x[ss], sx)
    sy = np.where(no_start, S.y[ss], sy)
    h0 = np.full(n_seq, np.nan)  # heading of the move into the start position
    pm = ~no_start & (ss >= 1)
    if pm.any():
        r1 = ss[pm] - 1
        dx1, dy1 = S.x[r1] - S.xprev[r1], S.y[r1] - S.yprev[r1]
        okh = np.isfinite(dx1) & (np.hypot(dx1, dy1) > 1e-6)
        h0[np.flatnonzero(pm)[okh]] = np.arctan2(dy1[okh], dx1[okh])
    tab_row = np.full((n_seq, maxL), -1, dtype=np.int64)
    for k in range(maxL):
        act = Ls > k
        tab_row[act, k] = ss[act] + k
    valid = tab_row >= 0
    rr = np.where(valid, tab_row, 0)
    own_t = valid & ev[rr]
    lab_ok = valid & np.isfinite(S.xprev[rr])
    lab_ok[:, 0] &= ~no_start
    ddx = np.nan_to_num(S.x[rr] - S.xprev[rr])
    ddy = np.nan_to_num(S.y[rr] - S.yprev[rr])
    odx = np.where(valid & ~own_t, ddx, 0.0)
    ody = np.where(valid & ~own_t, ddy, 0.0)
    if no_start.any():  # the first row has no observed previous position: no move re-simulated
        odx[no_start, 0] = 0.0
        ody[no_start, 0] = 0.0
        own_t[no_start, 0] = False
    ox_t, oy_t = np.nan_to_num(S.obj_x[rr]), np.nan_to_num(S.obj_y[rr])
    r_t = np.nan_to_num(S.obj_r[rr])
    n_act = np.array([int((Ls > k).sum()) for k in range(maxL)])
    codes = np.array(OBJ_CODES if obj else LOCO_CODES)
    if mode == "perm":
        act_t = S.action[rr].astype(np.int64)
        oi = np.flatnonzero(own_t.ravel())  # own slots, ordered by (episode, position)
        seq_of = oi // maxL
    null = []
    done = 0
    while done < B:
        nb = min(RESIM_CHUNK, B - done)
        if mode == "perm":  # the own actions (and EXPLORE step vectors) of each episode, shuffled
            keys = rng.random((oi.size, nb))
            AC = np.zeros((n_seq * maxL, nb), dtype=np.int64)
            AX = np.zeros((n_seq * maxL, nb))
            AY = np.zeros((n_seq * maxL, nb))
            for b in range(nb):
                src = oi[np.lexsort((keys[:, b], seq_of))]
                AC[oi, b] = act_t.ravel()[src]
                AX[oi, b] = ddx.ravel()[src]
                AY[oi, b] = ddy.ravel()[src]
            AC = AC.reshape(n_seq, maxL, nb)
            AX = AX.reshape(n_seq, maxL, nb)
            AY = AY.reshape(n_seq, maxL, nb)
        px = np.repeat(sx[:, None], nb, axis=1)
        py = np.repeat(sy[:, None], nb, axis=1)
        h = np.where(np.isfinite(h0)[:, None], np.nan_to_num(h0)[:, None],
                     rng.uniform(-np.pi, np.pi, (n_seq, nb)))
        PX = np.empty((n_seq, maxL, nb))
        PY = np.empty((n_seq, maxL, nb))
        CT = np.ones((n_seq, maxL, nb), dtype=bool)
        for k in range(maxL):
            m = n_act[k]
            x, y, hh = px[:m], py[:m], h[:m]
            nx = x + odx[:m, k, None]
            ny = y + ody[:m, k, None]
            o = own_t[:m, k]
            if o.any():
                if mode == "perm":
                    c = AC[:m, k]
                    gx, gy = AX[:m, k], AY[:m, k]
                else:
                    c = codes[rng.integers(0, 3, (m, nb))]
                    if obj:
                        gx = gy = 0.0
                    else:
                        g = rng.standard_normal((2, m, nb)) * mv["explore_sd"]
                        gx, gy = g[0], g[1]
                lr = mv["run_len"]
                cx, cy = ox_t[:m, k, None], oy_t[:m, k, None]
                vx, vy = x - cx, y - cy
                r = np.hypot(vx, vy)
                st = mv["manip_step"]
                safe = np.maximum(r, 1e-12)
                ux = np.where(r > 1e-6, vx / safe, 1.0)
                uy = np.where(r > 1e-6, vy / safe, 0.0)
                app = np.minimum(st, r)
                rad = np.maximum(r, 1.0)
                bo = mv["back_off"]  # BACK_OFF length and CIRCLE arc
                ang = np.arctan2(uy, ux) + bo / rad
                mx = np.select(
                    [c == ACT_EXPLORE, c == ACT_RUN_ON, c == ACT_TURN_BACK, c == ACT_MANIPULATE,
                     c == ACT_BACK_OFF, c == ACT_CIRCLE],
                    [gx + 0.0 * x, lr * np.cos(hh), -lr * np.cos(hh), -ux * app,
                     ux * bo, cx + rad * np.cos(ang) - x], 0.0)
                my = np.select(
                    [c == ACT_EXPLORE, c == ACT_RUN_ON, c == ACT_TURN_BACK, c == ACT_MANIPULATE,
                     c == ACT_BACK_OFF, c == ACT_CIRCLE],
                    [gy + 0.0 * y, lr * np.sin(hh), -lr * np.sin(hh), -uy * app,
                     uy * bo, cy + rad * np.sin(ang) - y], 0.0)
                nx = np.where(o[:, None], x + mx, nx)
                ny = np.where(o[:, None], y + my, ny)
            nx = np.clip(nx, 0.5, W - 0.5)
            ny = np.clip(ny, 0.5, H - 0.5)
            if regate:
                CT[:m, k] = (np.hypot(nx - ox_t[:m, k, None], ny - oy_t[:m, k, None])
                             <= r_t[:m, k, None] + CONTACT_SLACK_IN)
            dxm, dym = nx - x, ny - y
            moved = np.hypot(dxm, dym) > 1e-6
            h[:m] = np.where(moved, np.arctan2(dym, dxm), hh)
            px[:m], py[:m] = nx, ny
            PX[:m, k], PY[:m, k] = nx, ny
        ends = Ls - 1
        ex = PX[np.arange(n_seq), ends]
        ey = PY[np.arange(n_seq), ends]
        prevx = np.concatenate([sx[:, None, None].repeat(nb, axis=2), PX[:, :-1]], axis=1)
        prevy = np.concatenate([sy[:, None, None].repeat(nb, axis=2), PY[:, :-1]], axis=1)
        delta = (np.hypot(PX - ex[:, None], PY - ey[:, None])
                 - np.hypot(prevx - ex[:, None], prevy - ey[:, None]))
        lab = np.where(delta < -1.0, -1, np.where(delta > 1.0, 1, 0))
        lab = np.where((own_t & lab_ok)[:, :, None] & CT, lab, 0)
        both = (lab[:, :-1] != 0) & (lab[:, 1:] != 0) & valid[:, 1:, None]
        npair = both.sum(axis=(0, 1))
        nrev = (both & (lab[:, :-1] != lab[:, 1:])).sum(axis=(0, 1))
        null.append(np.where(npair >= 10, nrev / np.maximum(npair, 1), np.nan))
        done += nb
    nullv = np.concatenate(null)
    fin = nullv[np.isfinite(nullv)]
    if fin.size < 2:
        return out
    out[f"{prefix}_excess_unvalidated"] = float(obs - fin.mean())
    out[f"{prefix}_z_unvalidated"] = _z(obs, fin)
    out[f"{prefix}_null_mean_unvalidated"] = float(fin.mean())
    return out


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
def _with_form(r: dict[str, float], prefix: str) -> dict[str, bool]:
    out = decisions_v5(r)
    ex = r.get(f"{prefix}_excess_unvalidated", float("nan"))
    z = r.get(f"{prefix}_z_unvalidated", float("nan"))
    form = bool(np.isfinite(ex) and np.isfinite(z) and ex >= FORM_MIN_EXCESS and z > Z95)
    out["c3_structurally_different"] = out["c3_structurally_different"] and form
    out["c4_repeated_not_rigid"] = out["c4_repeated_not_rigid"] and form
    return out


def decisions(r: dict[str, float]) -> dict[str, bool]:
    """Preregistered per-criterion flags, rules v7 (PHASE4_DESIGN.md section 2): the v5 flags,
    with criteria 3 and 4 also requiring the form test against the replay null; NaN reads as
    False."""
    return _with_form(r, "seq_struct_form")


def decisions_v6(r: dict[str, float]) -> dict[str, bool]:
    """Rules v6 flags: criteria 3 and 4 with the form test against the label shuffle."""
    return _with_form(r, "seq_struct_form_shuffle")


def decisions_v5(r: dict[str, float]) -> dict[str, bool]:
    """Per-criterion flags of rules v5 (kept for continuity); NaN reads as False."""
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
                decisions_per_day: int = 6, rules: str = RULES) -> dict[str, Any]:
    """One episode kind. `rules` "v9" (default), "v8" (v9 with the fixed locomotor threshold;
    not adopted) or "v7" (criterion 5 on every row, the even-mix null without contact
    re-gating, plus the v6 shuffle)."""
    v8 = rules != "v7"  # the v8 / v9 definitions
    rng = np.random.default_rng(seed)
    ev, thr = event_mask(S, kind, fixed=rules == "v8")
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
        if not v8:
            base["decisions_v6_unvalidated"] = dict(base["decisions_unvalidated"])
            base["decisions_v5_unvalidated"] = dict(base["decisions_unvalidated"])
        return base
    base.update(crit1(S, s, e, n_surrogates, rng))
    base.update(crit2(S, s, n_surrogates, rng, horizon=decisions_per_day))
    base.update(crit3(S, ev, s, e, n_surrogates, rng))
    base.update(crit4(S, kind, ev, s, e, cand, onset, n_surrogates, rng))
    # v8: criterion 5 only on rows where a free action was eligible
    base.update(crit5(S, cand & S.eligible if v8 else cand, onset, n_surrogates, rng))
    base["c5_candidate_rows"] = int((cand & S.eligible).sum() if v8 else cand.sum())
    # form nulls on random streams of their own, so no statistic above depends on them
    base.update(form_resim(S, kind, ev, s, e, n_surrogates, np.random.default_rng([seed, 7]),
                           regate=v8))
    if v8:
        base.update(form_resim(S, kind, ev, s, e, n_surrogates,
                               np.random.default_rng([seed, 8]), regate=True, mode="perm",
                               prefix="seq_struct_order"))
        base["decisions_unvalidated"] = decisions(base)
    else:
        base.update(form_test(S, ev, s, e, n_surrogates, np.random.default_rng([seed, 6])))
        base["decisions_unvalidated"] = decisions(base)
        base["decisions_v6_unvalidated"] = decisions_v6(base)
        base["decisions_v5_unvalidated"] = decisions_v5(base)
    return base


def detect_trace(trace: dict[str, Any], kinds: tuple[str, ...] = KINDS, n_surrogates: int = 1000,
                 seed: int = 0, max_individuals: int | None = None, self_entries: bool = False,
                 weaned_age: float = 21.0, legacy: bool = True) -> dict[str, Any]:
    """Both episode kinds of one trace window, plus the relaxed share of weaned rows (age >=
    `weaned_age`, the config's biology.weaning_days) of the individuals read: the dose of H-e."""
    meta = trace.get("meta", {})
    dpd = int(np.asarray(meta.get("decisions_per_day", 6)))
    S = prepare(trace, max_individuals=max_individuals, rng=np.random.default_rng(seed + 17),
                self_entries=self_entries)
    weaned = S.age >= weaned_age
    out: dict[str, Any] = {
        "n_rows": int(S.n), "n_individuals": int(S.gstart.size),
        "rules": "v4_self_entries" if self_entries else RULES,
        "n_rows_weaned": int(weaned.sum()),
        "relaxed_share_weaned": float(S.relaxed[weaned].mean()) if weaned.any() else float("nan"),
    }
    for k in kinds:
        r8 = detect_kind(S, k, n_surrogates=n_surrogates, seed=seed, decisions_per_day=dpd)
        if legacy:  # the v7 / v6 / v5 flags from a pass with the v7 definitions
            r7 = detect_kind(S, k, n_surrogates=n_surrogates, seed=seed,
                             decisions_per_day=dpd, rules="v7")
            r8["decisions_v7_unvalidated"] = r7["decisions_unvalidated"]
            for key in ("decisions_v6_unvalidated", "decisions_v5_unvalidated"):
                if key in r7:
                    r8[key] = r7[key]
            r8["legacy_v7"] = {key: r7[key] for key in (
                "n_episodes", "locomotor_disp_threshold", "c5_candidate_rows",
                "gate_relaxed_log_ratio_unvalidated", "gate_relaxed_z_unvalidated",
                "seq_struct_form_excess_unvalidated", "seq_struct_form_z_unvalidated",
                "seq_struct_form_shuffle_excess_unvalidated") if key in r7}
        out[k] = r8
    return out
