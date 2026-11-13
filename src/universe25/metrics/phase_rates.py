"""Per-window episode rates and per-run phases for H-g (PHASE4_DESIGN.md section 4.3, fixed
2026-11-13 before any run).

H-g (PLAN.md section 15.1): breakdown suppresses play-likeness. Detector rates fall in phases C /
D under every policy and decline monotonically after the plateau; falsified if they rise in
phase D. Here:
- the rate of a kind in a trace window is its episodes (rules-v9 events, gap criterion and
  segmentation from metrics/detectors.py) per weaned individual-day, over every traced
  individual (no cap, no surrogates);
- a window's phase comes from its run's own first-litter and peak days (metrics/calibration.py
  landmarks), never from a detector;
- tau_bcd and tau_d are Kendall tau-b of the rate on phase order and, within phase D, on time;
  the decision is an exact sign-flip test over seeds.

Eval-only: nothing here feeds back into a policy, observation or learner (audited in
tests/test_phase_rates.py). The rates measure candidate behaviour, not play.
"""
from __future__ import annotations

import itertools
from typing import Any

import numpy as np

from universe25.agents.state import ROLE_WITHDRAWN
from universe25.metrics.detectors import KINDS, event_mask, gap_criterion, prepare, segment
from universe25.metrics.dose_response import kendall_tau_b

# the record's day 315 between its first litters (day 104) and its peak (day 560)
PHASE_B_FRACTION = (315.0 - 104.0) / (560.0 - 104.0)
PHASE_ORDER = {"B": 0, "C": 1, "D": 2}
MIN_WEANED_INDIVIDUALS = 10  # traced weaned individuals for a window to enter
WEANED_AGE = 21.0  # biology.weaning_days of the calibrated colony
MATURITY_AGE = 64.0  # biology.maturity_days of the calibrated colony (63.9), reported only
STRESSED = 0.4  # the relaxed field's stress bound (detectors.prepare)
D_MIN_WINDOWS = 3
D_EARLY_DAYS = 150.0  # detector-vector windows: days after the peak
D_LATE_DAYS = 600.0
ALPHA = 0.025
N_CELLS = 6  # policy x kind with the playground on (Bonferroni for the falsifier)


def phase_b_end(t_fl: float, t_pk: float) -> float:
    """End of phase B: the record's day 315 in the run's own proportions."""
    return t_fl + PHASE_B_FRACTION * (t_pk - t_fl)


def phase_of(mid: float, t_fl: float, t_pk: float) -> str:
    """Phase of a window by its midpoint: A before the first litters, B to the end of phase B,
    C to the peak day (inclusive), D after it. No first litter or peak: A."""
    if not (np.isfinite(t_fl) and np.isfinite(t_pk)) or mid < t_fl:
        return "A"
    if mid < phase_b_end(t_fl, t_pk):
        return "B"
    return "C" if mid <= t_pk else "D"


def window_rates(trace: dict[str, Any], weaned_age: float = WEANED_AGE,
                 maturity_age: float = MATURITY_AGE) -> dict[str, Any]:
    """Onset rates of both episode kinds in one trace window, per weaned individual-day, with
    the state shares reported beside them. Episodes are those of the detectors under rules v9
    (locomotor threshold: the 90th percentile of the window's serious moves), over every traced
    individual; an onset counts if its row is weaned."""
    meta = trace.get("meta", {})
    rows_per_day = max(1, int(np.asarray(meta.get("decisions_per_day", 6))))
    S = prepare(trace)
    uid = np.asarray(trace["uid"]).astype(np.int64)
    order = np.lexsort((np.asarray(trace["step"]).astype(np.int64), uid))  # as prepare sorts
    weaned = S.age >= weaned_age
    n_w = int(weaned.sum())

    def share(mask: np.ndarray | None) -> float:
        return float(mask[weaned].mean()) if mask is not None and n_w else float("nan")

    def col(k: str) -> np.ndarray | None:
        return np.asarray(trace[k])[order] if k in trace else None

    stress, role = col("stress"), col("role")
    wd = n_w / rows_per_day
    ed = int(S.eligible.sum()) / rows_per_day
    out: dict[str, Any] = {
        "n_rows": int(S.n),
        "n_individuals": int(S.gstart.size),
        "n_weaned_individuals": int(np.unique(S.uid[weaned]).size),
        "weaned_individual_days": wd,
        "eligible_individual_days": ed,
        "relaxed_share_weaned": share(S.relaxed),
        "stressed_share_weaned": share(None if stress is None else stress >= STRESSED),
        "withdrawn_share_weaned": share(None if role is None else role == ROLE_WITHDRAWN),
        "juvenile_share_weaned": share(S.age < maturity_age),
    }
    for kind in KINDS:
        ev, thr = event_mask(S, kind, fixed=False)
        c, has_break = gap_criterion(S, ev, max_gap=rows_per_day)
        s, _, _ = segment(S, ev, c)
        on = s[weaned[s]]
        out[kind] = {
            "n_events": int(ev.sum()),
            "n_events_weaned": int((ev & weaned).sum()),
            "n_episodes": int(s.size),
            "n_onsets_weaned": int(on.size),
            "gap_criterion_steps": int(c),
            "episode_structure": bool(has_break),
            "threshold": thr,
            "rate": on.size / wd if wd > 0 else float("nan"),
            "rate_eligible": on.size / ed if ed > 0 else float("nan"),
            "event_share_weaned": share(ev),
        }
    return out


def label_windows(windows: list[dict[str, Any]], t_fl: float, t_pk: float) -> None:
    """Set "phase" and "entered" on window dicts that carry "mid" and "n_weaned_individuals"."""
    for w in windows:
        w["phase"] = phase_of(float(w["mid"]), t_fl, t_pk)
        w["entered"] = bool(w["phase"] in PHASE_ORDER
                            and w["n_weaned_individuals"] >= MIN_WEANED_INDIVIDUALS)


def run_taus(windows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    """tau_bcd (rate on phase order B 0, C 1, D 2; the entered windows must cover two phases) and
    tau_d (rate on window midpoint over at least three entered D windows) of one run; NaN where
    undefined. A constant rate gives tau 0."""
    w = [x for x in windows if x["entered"] and np.isfinite(x[kind]["rate"])]
    order = np.array([PHASE_ORDER[x["phase"]] for x in w], dtype=np.float64)
    rate = np.array([x[kind]["rate"] for x in w], dtype=np.float64)
    tau_bcd = float("nan")
    if np.unique(order).size >= 2:
        tau_bcd = kendall_tau_b(order, rate)
    d = [x for x in w if x["phase"] == "D"]
    tau_d = float("nan")
    if len(d) >= D_MIN_WINDOWS:
        tau_d = kendall_tau_b([x["mid"] for x in d], [x[kind]["rate"] for x in d])
    return {"tau_bcd": tau_bcd, "tau_d": tau_d, "n_windows": len(w), "n_d_windows": len(d)}


def sign_flip(values: Any) -> dict[str, Any]:
    """Exact sign-flip test of the mean (NaN dropped) over all 2^n sign patterns: p_rise is the
    share of patterns with a mean >= the observed one, p_fall the share with a mean <= it."""
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0, "mean": float("nan"), "se": float("nan"),
                "p_rise": float("nan"), "p_fall": float("nan")}
    pats = np.array(list(itertools.product((1.0, -1.0), repeat=v.size)))
    m = (pats * v).mean(axis=1)
    obs = float(v.mean())
    return {"n": int(v.size), "mean": obs,
            "se": float(v.std(ddof=1) / np.sqrt(v.size)) if v.size > 1 else float("nan"),
            "p_rise": float(np.mean(m >= obs - 1e-12)),
            "p_fall": float(np.mean(m <= obs + 1e-12))}


def sign_flip_low_memory(values: Any, block: int = 20) -> dict[str, Any]:
    """The test of `sign_flip` for any n, without its 2^n x n pattern matrix (PHASE4_DESIGN.md
    4.5: 24 colonies would need 3 GB). The sums over the first `block` values' sign patterns are
    built by doubling, and the remaining values' patterns are looped over; every one of the 2^n
    patterns is counted, so the test stays exact."""
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0, "mean": float("nan"), "se": float("nan"),
                "p_rise": float("nan"), "p_fall": float("nan")}
    n = int(v.size)
    obs = float(v.mean())
    head, tail = v[:block], v[block:]
    sums = np.zeros(1)
    for x in head:
        sums = np.concatenate([sums + x, sums - x])
    rise = fall = 0
    for signs in itertools.product((1.0, -1.0), repeat=tail.size):
        m = (sums + float(np.dot(np.asarray(signs, np.float64), tail))) / n
        rise += int(np.count_nonzero(m >= obs - 1e-12))
        fall += int(np.count_nonzero(m <= obs + 1e-12))
    total = 2.0 ** n
    return {"n": n, "mean": obs,
            "se": float(v.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan"),
            "p_rise": rise / total, "p_fall": fall / total}


def cell_decision(tau_bcd: Any, tau_d: Any, n_cells: int = N_CELLS,
                  alpha: float = ALPHA) -> dict[str, Any]:
    """One policy x kind cell: falsified if T_d > 0 with p_rise < alpha / n_cells; supported if
    T_bcd < 0 and T_d < 0, each with p_fall < alpha; otherwise not supported."""
    a, d = sign_flip(tau_bcd), sign_flip(tau_d)
    if a["n"] < 2 and d["n"] < 2:
        reading = "untested"
    elif d["n"] >= 2 and d["mean"] > 0 and d["p_rise"] < alpha / n_cells:
        reading = "falsified"
    elif (a["n"] >= 2 and d["n"] >= 2 and a["mean"] < 0 and a["p_fall"] < alpha
          and d["mean"] < 0 and d["p_fall"] < alpha):
        reading = "supported"
    else:
        reading = "not supported"
    return {"T_bcd": a, "T_d": d, "reading": reading,
            "falsifier_alpha": alpha / n_cells, "alpha": alpha}


def overall(readings: list[str]) -> str:
    """H-g over the cells: falsified if any cell is, supported if every cell is."""
    if any(r == "falsified" for r in readings):
        return "falsified"
    if readings and all(r == "supported" for r in readings):
        return "supported"
    return "not supported"


def detector_windows(windows: list[dict[str, Any]], t_fl: float,
                     t_pk: float) -> dict[str, float | None]:
    """Midpoints of the four detector-vector windows: the entered B window nearest the middle
    of B, the entered C window nearest the middle of C, and the entered D windows nearest
    t_pk + 150 and t_pk + 600 (None where the phase has no entered window; ties go early)."""
    b = phase_b_end(t_fl, t_pk)
    targets = {"B": ("B", 0.5 * (t_fl + b)), "C": ("C", 0.5 * (b + t_pk)),
               "D_early": ("D", t_pk + D_EARLY_DAYS), "D_late": ("D", t_pk + D_LATE_DAYS)}
    out: dict[str, float | None] = {}
    for label, (ph, target) in targets.items():
        cand = [float(x["mid"]) for x in windows if x["entered"] and x["phase"] == ph]
        out[label] = min(cand, key=lambda m: (abs(m - target), m)) if cand else None
    return out
