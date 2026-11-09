"""Synthetic ground truth for the eval-only detectors (phase 4, P4-5).

Scripted, non-learning individuals written from the wording of Burghardt's criteria (never from
an animal or human dataset, H1). Each class shares a serious routine (forage, drink, rest at a
hopper or the nest when a drive is high) and differs only in its free-time episodes:

  all_criteria onset only in the relaxed field, independent of triggers; object episodes that
               approach an object and then alternate small withdrawals and re-approaches,
               switching objects, varying in length; fast zig-zag locomotor runs away from any
               target; no survival relief; recur on most days with variation
  serious      onset when a drive is rising; straight approach to the hopper (via an object
               placed at the food) ending in consumption: functional (criterion 1 negative,
               criterion 3 negative: same form as the serious approach)
  rigid_loop   the same episode at the same time every day: identical object and path
               (criterion 4 negative)
  novelty      inspection that decays with cumulative exposure: approach and stay
               (criterion 4 exposure-slope negative)
  triggered    all_criteria episodes whose onsets follow an exogenous trigger (density jump or
               wound) at or one step before onset (criterion 2 negative)
  stressed     all_criteria episodes that start only outside the relaxed field (criterion 5
               negative)
  random_walk  fast random displacement at random times in any state, no objects: the
               matched-speed random policy every detector is also read against

Traces use the schema of `metrics/trace.py`; cell is constant (the only exogenous triggers are
density jumps and wounds).

Mobile sub-step classes (rules v5): the same individuals in an arena split into 2 x 2 cells
(nest, hoppers and objects in different cells; the object cell denser), each row recording the
cell of its start position as the trace recorder does, so an object onset usually follows the
individual's own entry into the object cell a few sub-steps earlier. Exogenous density jumps
add to the occupied cell's base density.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from universe25.agents.state import (
    ACT_DRINK,
    ACT_EXPLORE,
    ACT_FORAGE,
    ACT_MANIPULATE,
    ACT_NEST,
    ACT_REST,
)
from universe25.metrics.trace import FIELDS, nearest_object

CLASSES = ("all_criteria", "serious", "rigid_loop", "novelty", "triggered", "stressed",
           "random_walk", "forced_gating")
# forced_gating (rules v8 hard negative for criterion 5): free-time onsets at one constant rate
# whenever a free action is eligible, relaxed or not; long reflex-forced foraging and drinking
# spells (hunger or thirst above 0.85, slow trips) that are never relaxed. Without the
# eligibility restriction those forced rows make onsets look gated by the relaxed field.
FORCED = 0.85
FORCED_SPEED = 3.0
# Sub-step classes: a base class expanded to K rows per decision (rules v4), optionally in the
# 2 x 2-cell arena (rules v5): name -> (base class, K, mobile)
SUBSTEP_CLASSES = {"all_criteria_k12": ("all_criteria", 12, False),
                   "triggered_k12": ("triggered", 12, False),
                   "all_criteria_mobile_k12": ("all_criteria", 12, True),
                   "triggered_mobile_k12": ("triggered", 12, True)}
FOOD = np.array([8.0, 8.0])
WATER = np.array([8.0, 12.0])
OBJECTS = np.array([[32.0, 32.0], [36.0, 28.0], [28.0, 36.0], [8.0, 8.0]])  # last: at the food
OBJ_RADIUS = 1.5
PG_BOX = (24.0, 24.0, 40.0, 40.0)
W = 40.0
# rules v7 replay null: movement model per decision in this arena (the random walk's sigma, its
# mean step, the serious approach speed); per sub-step as the simulator scales it
MOVE_EXPLORE_SD = 14.0
# v8 (amended before the v8 test): the generator's own object scales - approach at its "at"
# speed (60 in per decision) and withdraw 2.25 in (v7 used the serious approach speed, 30 in,
# for both, which made every re-simulated BACK_OFF leave contact)
MOVE_MANIP_STEP = 60.0
MOVE_BACK_OFF = 2.25
CELL_BASE = np.array([0.3, 0.3, 0.3, 0.6])  # mobile arena: hoppers 0, nest 2, objects 3


def _cells(x: Any, y: Any) -> np.ndarray:
    """Cell of points in the mobile arena's 2 x 2 grid (row-major, like the simulator's)."""
    return ((np.asarray(x) >= W / 2).astype(np.int64)
            + 2 * (np.asarray(y) >= W / 2).astype(np.int64))


def _relaxed(st: dict[str, float]) -> bool:
    return (st["hunger"] < 0.5 and st["thirst"] < 0.5 and st["energy"] > 0.5
            and st["stress"] < 0.4 and st["wounds"] < 0.3 and st["since_hit"] >= 6
            and st["density"] < 1.0)


def _toward(pos: np.ndarray, target: np.ndarray, speed: float) -> np.ndarray:
    d = target - pos
    dist = float(np.hypot(*d))
    if dist <= speed or dist < 1e-9:
        return target.copy()
    return pos + d / dist * speed


def _free_object_plan(r: np.random.Generator, n_obj: int = 3) -> list[tuple[int, Any]]:
    """Approach an object, then alternate withdraw / re-approach (small, varied), sometimes
    switching object; 3-6 steps."""
    plan: list[tuple[int, Any]] = []
    obj = int(r.integers(0, n_obj))
    plan.append((ACT_MANIPULATE, ("at", obj, 0.0)))
    for _ in range(int(r.integers(2, 6))):
        if r.random() < 0.35:
            obj = int(r.choice([o for o in range(n_obj) if o != obj]))
            plan.append((ACT_MANIPULATE, ("at", obj, 0.0)))
        elif plan[-1][1][2] == 0.0:
            plan.append((ACT_MANIPULATE, ("at", obj, float(r.uniform(2.05, 2.45)))))
        else:
            plan.append((ACT_MANIPULATE, ("at", obj, 0.0)))
    return plan


def _free_loco_plan(r: np.random.Generator) -> list[tuple[int, Any]]:
    """Fast zig-zag run with varied headings, 3-6 steps of 20-28 in."""
    plan = []
    heading = float(r.uniform(0, 2 * np.pi))
    for _ in range(int(r.integers(3, 7))):
        heading += float(r.uniform(np.pi / 2, 3 * np.pi / 2))
        L = float(r.uniform(20.0, 28.0))
        plan.append((ACT_EXPLORE, ("vec", L * np.cos(heading), L * np.sin(heading))))
    return plan


def _simulate_individual(cls: str, uid: int, days: int, dpd: int,
                         r: np.random.Generator, mobile: bool = False) -> dict[str, list]:
    rows: dict[str, list] = {k: [] for k in FIELDS}
    nest = np.array([4.0 + r.uniform(-1, 1), 36.0 + r.uniform(-1, 1)])
    pos = nest.copy()
    st = {"hunger": float(r.uniform(0, 0.4)), "thirst": float(r.uniform(0, 0.4)),
          "fatigue": float(r.uniform(0, 0.4)), "stress": 0.1, "energy": 0.8, "wounds": 0.0,
          "density": 0.3, "since_hit": 10.0}
    cum_contacts = 0
    cum_loco = 0
    excess = 0.0  # mobile arena: density above the occupied cell's base
    plan: list[tuple[int, Any]] = []
    plan_kind = ""
    trig_prev = False
    rigid_obj = [(ACT_MANIPULATE, ("at", 0, 0.0 if i % 2 == 0 else 2.25)) for i in range(6)]
    # fixed waypoints: one goto (variable start) then five identical 24-in legs every day
    rigid_loco = [(ACT_EXPLORE, ("goto", np.array([28.0, 36.0]), 60.0, ""))] + [
        (ACT_EXPLORE, ("vec", dx, dy))
        for dx, dy in ((0.0, -24.0), (-24.0, 0.0), (0.0, 24.0), (24.0, 0.0), (0.0, -24.0))]
    rigid_slot = int(r.integers(1, dpd))
    rigid_done_day = -1
    stress_day_phase = int(r.integers(0, 2))
    for t in range(days * dpd):
        day = t // dpd
        # environment: density jumps and wounds are the exogenous triggers
        trig = False
        if mobile:
            excess *= 0.7
            if r.random() < 0.12:
                excess += 0.2
                trig = True
            st["density"] = float(CELL_BASE[_cells(pos[0], pos[1])]) + excess
        else:
            st["density"] = 0.3 + (st["density"] - 0.3) * 0.7
            if r.random() < 0.12:
                st["density"] += 0.2
                trig = True
        st["since_hit"] += 1.0
        st["wounds"] = max(0.0, st["wounds"] - 0.01)
        if r.random() < 0.02:
            st["wounds"] += 0.15
            st["since_hit"] = 0.0
            trig = True
        st["hunger"] = min(1.5, st["hunger"] + 0.08)
        st["thirst"] = min(1.5, st["thirst"] + 0.10)
        st["fatigue"] = min(1.5, st["fatigue"] + 0.03)
        if cls == "stressed":
            st["stress"] = 0.7 if (day + stress_day_phase) % 2 == 0 else 0.1
        pre = dict(st)
        relaxed = _relaxed(st)
        triggered_now = trig or trig_prev
        trig_prev = trig
        # choose
        act = ACT_REST
        target = None
        if not plan:
            if cls == "forced_gating":  # eligible = no reflex in force (the simulator's mask)
                free = not (st["thirst"] > FORCED or st["hunger"] > FORCED)
            else:
                free = not (st["thirst"] > 0.6 or st["hunger"] > 0.6 or st["fatigue"] > 0.8)
            if free:
                at_nest = bool(np.hypot(*(pos - nest)) < 1.0)
                plan, plan_kind = _onset(cls, r, relaxed, triggered_now, st, cum_contacts,
                                         cum_loco, day, t % dpd, rigid_slot, rigid_done_day,
                                         rigid_obj, rigid_loco, pos, at_nest)
                if plan and cls == "rigid_loop":
                    rigid_done_day = day
        if plan:
            act, target = plan.pop(0)
        elif cls == "forced_gating" and st["thirst"] > FORCED:
            act = ACT_DRINK
        elif cls == "forced_gating" and st["hunger"] > FORCED:
            act = ACT_FORAGE
        elif cls == "forced_gating":
            act = ACT_REST if st["fatigue"] > 0.8 or r.random() < 0.5 else ACT_NEST
        elif st["thirst"] > 0.6:
            act = ACT_DRINK
        elif st["hunger"] > 0.6:
            act = ACT_FORAGE
        elif st["fatigue"] > 0.8:
            act = ACT_REST
        else:
            act = ACT_NEST if r.random() < 0.5 else ACT_REST
        cell_pre = int(_cells(pos[0], pos[1])) if mobile else 0
        # execute
        speed = FORCED_SPEED if cls == "forced_gating" else 15.0
        if act == ACT_DRINK:
            pos = _toward(pos, WATER, speed)
            if np.hypot(*(pos - WATER)) < 0.5:
                st["thirst"] = 0.0
        elif act == ACT_FORAGE:
            pos = _toward(pos, FOOD, speed)
            if np.hypot(*(pos - FOOD)) < 0.5:
                st["hunger"] = 0.0
        elif act == ACT_REST:
            st["fatigue"] = max(0.0, st["fatigue"] - 0.5)
        elif act == ACT_NEST:
            pos = _toward(pos, nest, 12.0)
        elif target is not None and target[0] == "at":
            obj = OBJECTS[target[1]]
            off = target[2]
            if off > 0.0:
                ang = float(r.uniform(0, 2 * np.pi))
                pos = obj + off * np.array([np.cos(ang), np.sin(ang)])
            else:
                pos = _toward(pos, obj, 60.0)
            st["fatigue"] = min(1.5, st["fatigue"] + 0.03)
        elif target is not None and target[0] == "vec":
            pos = np.clip(pos + np.array([target[1], target[2]]), 0.5, W - 0.5)
            st["fatigue"] = min(1.5, st["fatigue"] + 0.03)
        elif target is not None and target[0] == "goto":
            goal = target[1]
            pos = _toward(pos, goal, target[2])
            if target[3] and np.hypot(*(pos - goal)) < 0.5:  # consumption at arrival
                if target[3] == "food":
                    st["hunger"] = 0.0
                else:
                    st["thirst"] = 0.0
        oid, odist, orad = nearest_object(pos[:1].astype(float), pos[1:].astype(float),
                                          OBJECTS[:, 0], OBJECTS[:, 1],
                                          np.full(len(OBJECTS), OBJ_RADIUS))
        contact = bool(act == ACT_MANIPULATE and odist[0] <= orad[0] + 1.0)
        cum_contacts += int(contact)
        if plan_kind == "locomotor" and act == ACT_EXPLORE:
            cum_loco += 1
        if not plan:
            plan_kind = ""
        x0, y0, x1, y1 = PG_BOX
        vals = {
            "uid": uid, "step": t, "tick": t, "day": t / dpd, "slot": uid, "action": act,
            "age": 100.0 + t / dpd, "sex": uid % 2, "role": 4,
            "hunger": pre["hunger"], "thirst": pre["thirst"], "fatigue": pre["fatigue"],
            "stress": pre["stress"], "curiosity": 0.3, "boredom": 0.3, "social_drive": 0.3,
            "energy": pre["energy"], "wounds": pre["wounds"], "cell": cell_pre,
            "cell_density": pre["density"],
            "x": pos[0], "y": pos[1], "hunger_post": st["hunger"], "thirst_post": st["thirst"],
            "fatigue_post": st["fatigue"], "stress_post": st["stress"], "obj_id": int(oid[0]),
            "obj_dist": float(odist[0]), "contact": int(contact),
            "in_playground": int(x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1),
            "food_dist": float(np.hypot(*(pos - FOOD))),
            "water_dist": float(np.hypot(*(pos - WATER))),
            "nest_dist": float(np.hypot(*(pos - nest))), "cum_contacts": cum_contacts,
            "obj_x": float(OBJECTS[int(oid[0]), 0]), "obj_y": float(OBJECTS[int(oid[0]), 1]),
            "obj_r": OBJ_RADIUS,
        }
        for k in FIELDS:
            rows[k].append(vals[k])
    return rows


def _onset(cls: str, r: np.random.Generator, relaxed: bool, triggered: bool,
           st: dict[str, float], cum_contacts: int, cum_loco: int, day: int, slot: int,
           rigid_slot: int, rigid_done_day: int, rigid_obj: list, rigid_loco: list,
           pos: np.ndarray, at_nest: bool) -> tuple[list[tuple[int, Any]], str]:
    kind = "object" if r.random() < 0.5 else "locomotor"
    if cls == "all_criteria":
        go = relaxed and r.random() < 0.12
    elif cls == "triggered":
        go = relaxed and triggered and r.random() < 0.8
    elif cls == "stressed":
        go = (not relaxed) and r.random() < 0.3
    elif cls == "forced_gating":
        go = r.random() < 0.12  # one rate whenever eligible, relaxed or not
    elif cls == "random_walk":
        if r.random() < 0.12:
            plan = []
            for _ in range(int(r.integers(2, 6))):
                v = r.normal(0.0, 14.0, size=2)
                plan.append((ACT_EXPLORE, ("vec", float(v[0]), float(v[1]))))
            return plan, "locomotor"
        return [], ""
    elif cls == "rigid_loop":
        k = "object" if day % 2 == 0 else "locomotor"
        if relaxed and day != rigid_done_day and slot >= rigid_slot:
            return [tuple(p) for p in (rigid_obj if k == "object" else rigid_loco)], k
        return [], ""
    elif cls == "novelty":
        expo = cum_contacts if kind == "object" else cum_loco
        if relaxed and r.random() < 0.6 * np.exp(-expo / 4.0):
            n = int(r.integers(2, 5))
            if kind == "object":
                obj = int(r.integers(0, 3))
                return [(ACT_MANIPULATE, ("at", obj, 0.0)) for _ in range(n)], kind
            spot = np.array([r.uniform(14, 26), r.uniform(4, 16)])
            return [(ACT_EXPLORE, ("goto", spot, 24.0, ""))] + \
                [(ACT_EXPLORE, ("goto", spot, 24.0, "")) for _ in range(n - 1)], kind
        return [], ""
    elif cls == "serious":
        rising = (0.3 < st["hunger"] <= 0.6) or (0.3 < st["thirst"] <= 0.6)
        if not rising or r.random() > 0.35:
            return [], ""
        if kind == "object":
            # straight approach to the object at the food, then consume there
            far = float(np.hypot(*(pos - OBJECTS[3])))
            n = max(1, int(np.ceil(far / 30.0)))
            return [(ACT_MANIPULATE, ("goto", OBJECTS[3], 30.0, ""))
                    for _ in range(n - 1)] + [(ACT_MANIPULATE, ("goto", FOOD, 30.0, "food"))], kind
        far = float(np.hypot(*(pos - WATER)))
        if far < 22.0:
            return [], ""
        n = max(1, int(np.floor(far / 22.0)))
        L = far / n
        return [(ACT_EXPLORE, ("goto", WATER, L, "")) for _ in range(n - 1)] + \
            [(ACT_EXPLORE, ("goto", WATER, L, "water"))], kind
    else:
        raise ValueError(cls)
    if not go:
        return [], ""
    return (_free_object_plan(r) if kind == "object" else _free_loco_plan(r)), kind


def expand_substeps(trace: dict[str, Any], K: int) -> dict[str, Any]:
    """K rows per decision, written the way the trace recorder writes a non-free decision:
    positions interpolated from the previous decision's end, drives and triggers constant within
    the decision (so density jumps and wounds appear on its first row), the survival-drive change
    on its last row; object contact and distances recomputed per row."""
    order = np.lexsort((trace["step"], trace["uid"]))
    t = {k: np.asarray(trace[k])[order] for k in FIELDS}
    n = t["uid"].size
    first = np.ones(n, dtype=bool)
    first[1:] = t["uid"][1:] != t["uid"][:-1]
    xp = np.where(first, t["x"], np.roll(t["x"], 1))
    yp = np.where(first, t["y"], np.roll(t["y"], 1))
    ndp = np.where(first, t["nest_dist"], np.roll(t["nest_dist"], 1))
    rep = np.repeat(np.arange(n), K)
    j = np.tile(np.arange(K), n)
    f = (j + 1.0) / K
    out: dict[str, Any] = {k: t[k][rep] for k in FIELDS}
    out["step"] = t["step"][rep] * K + j
    out["x"] = xp[rep] + (t["x"] - xp)[rep] * f
    out["y"] = yp[rep] + (t["y"] - yp)[rep] * f
    out["nest_dist"] = ndp[rep] + (t["nest_dist"] - ndp)[rep] * f
    if trace.get("meta", {}).get("cell_grid"):  # mobile arena: cell of each row's start
        g = j / K
        out["cell"] = np.where(j == 0, t["cell"][rep],
                               _cells(xp[rep] + (t["x"] - xp)[rep] * g,
                                      yp[rep] + (t["y"] - yp)[rep] * g))
    last = j == K - 1
    for k in ("hunger", "thirst", "fatigue", "stress"):
        out[f"{k}_post"] = np.where(last, t[f"{k}_post"][rep], t[k][rep])
    oid, od, orr = nearest_object(out["x"], out["y"], OBJECTS[:, 0], OBJECTS[:, 1],
                                  np.full(len(OBJECTS), OBJ_RADIUS))
    out["obj_id"], out["obj_dist"] = oid, od
    out["obj_x"], out["obj_y"] = OBJECTS[oid, 0], OBJECTS[oid, 1]
    out["obj_r"] = np.full(out["obj_x"].shape, OBJ_RADIUS)
    out["contact"] = ((out["action"] == ACT_MANIPULATE) & (od <= orr + 1.0)).astype(np.int8)
    x0, y0, x1, y1 = PG_BOX
    out["in_playground"] = ((out["x"] >= x0) & (out["x"] <= x1) & (out["y"] >= y0)
                            & (out["y"] <= y1)).astype(np.int8)
    out["food_dist"] = np.hypot(out["x"] - FOOD[0], out["y"] - FOOD[1])
    out["water_dist"] = np.hypot(out["x"] - WATER[0], out["y"] - WATER[1])
    cum = np.cumsum(out["contact"].astype(np.int64))
    starts = np.flatnonzero(first)  # first original row of each individual
    lens = np.diff(np.r_[starts, n]) * K  # its expanded rows
    base = np.concatenate([[0], cum])[np.repeat(starts * K, lens)]  # cum before its first row
    out["cum_contacts"] = cum - base
    meta = dict(trace.get("meta", {}))
    meta["decisions_per_day"] = int(meta.get("decisions_per_day", 6)) * K
    meta["free_substeps"] = K
    meta.update(_move_meta(K))
    out["meta"] = meta
    return out


def _move_meta(K: int) -> dict[str, float]:
    """Trace meta of the movement model per row at K rows per decision (rules v7). The K rows
    of a synthetic decision are a linear interpolation of it (expand_substeps), so every step
    scales with 1/K (v8, amended before the test; v7 used 1/sqrt(K) for EXPLORE, which is the
    simulator's independent sub-steps, not this generator's interpolation)."""
    sd = MOVE_EXPLORE_SD / K
    return {"move_explore_sd": float(sd), "move_run_len": float(sd * np.sqrt(np.pi / 2)),
            "move_manip_step": MOVE_MANIP_STEP / K, "move_back_off": MOVE_BACK_OFF / K,
            "world_width": W, "world_height": W}


def make_colony(cls: str, n_individuals: int = 30, days: int = 20, dpd: int = 6,
                seed: int = 0, mobile: bool = False) -> dict[str, Any]:
    """One synthetic colony of a class, as a trace dict (schema of metrics/trace.py)."""
    if cls in SUBSTEP_CLASSES:
        base, K, mob = SUBSTEP_CLASSES[cls]
        out = expand_substeps(make_colony(base, n_individuals, days, dpd, seed, mobile=mob), K)
        out["meta"]["synthetic_class"] = cls
        return out
    if cls not in CLASSES:
        raise ValueError(cls)
    r = np.random.default_rng(seed)
    cols: dict[str, list] = {k: [] for k in FIELDS}
    for u in range(n_individuals):
        rows = _simulate_individual(cls, u, days, dpd, r, mobile)
        for k in FIELDS:
            cols[k].extend(rows[k])
    out: dict[str, Any] = {k: np.asarray(v) for k, v in cols.items()}
    out["meta"] = {"decisions_per_day": dpd, "synthetic_class": cls, "seed": seed,
                   **_move_meta(1)}
    if mobile:
        out["meta"]["cell_grid"] = 2
    return out
