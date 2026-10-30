"""Warp kernels for Universe25 SoA tick (no play reward)."""
from __future__ import annotations

import warp as wp


@wp.kernel
def update_drives_kernel(
    alive: wp.array(dtype=wp.int32),
    role: wp.array(dtype=wp.int32),
    hunger: wp.array(dtype=wp.float32),
    thirst: wp.array(dtype=wp.float32),
    curiosity: wp.array(dtype=wp.float32),
    boredom: wp.array(dtype=wp.float32),
    social_drive: wp.array(dtype=wp.float32),
    energy: wp.array(dtype=wp.float32),
    fatigue: wp.array(dtype=wp.float32),
    age_days: wp.array(dtype=wp.float32),
    gestating: wp.array(dtype=wp.float32),
    dt: float,
    hunger_gain: float,
    thirst_gain: float,
    curiosity_gain: float,
    boredom_gain: float,
    social_gain: float,
    pup_hunger_scale: float,
):
    i = wp.tid()
    if alive[i] == 0:
        return
    scale = float(1.0)
    if role[i] == 0:  # ROLE_PUP
        scale = pup_hunger_scale
    hunger[i] = wp.clamp(hunger[i] + hunger_gain * scale * dt, 0.0, 1.5)
    thirst[i] = wp.clamp(thirst[i] + thirst_gain * scale * dt, 0.0, 1.5)
    curiosity[i] = wp.clamp(curiosity[i] + curiosity_gain * dt, 0.0, 1.5)
    boredom[i] = wp.clamp(boredom[i] + boredom_gain * dt, 0.0, 1.5)
    social_drive[i] = wp.clamp(social_drive[i] + social_gain * dt, 0.0, 1.5)
    energy[i] = wp.clamp(energy[i] - 0.15 * dt - 0.1 * fatigue[i] * dt, 0.0, 1.0)
    age_days[i] = age_days[i] + dt
    if gestating[i] > 0.0:
        gestating[i] = wp.max(0.0, gestating[i] - dt)


@wp.kernel
def density_stress_kernel(
    alive: wp.array(dtype=wp.int32),
    cell_id: wp.array(dtype=wp.int32),
    nest_id: wp.array(dtype=wp.int32),
    rank: wp.array(dtype=wp.float32),
    stress: wp.array(dtype=wp.float32),
    social_drive: wp.array(dtype=wp.float32),
    cell_counts: wp.array(dtype=wp.int32),
    nest_occ: wp.array(dtype=wp.int32),
    nest_cap: wp.array(dtype=wp.int32),
    age_days: wp.array(dtype=wp.float32),
    competence: wp.array(dtype=wp.float32),
    dt: float,
    stress_density_gain: float,
    stress_decay: float,
    nest_overcrowd_stress: float,
    capacity_per_cell: float,
    dens_frac_arr: wp.array(dtype=wp.float32),
    menopause_thr: float,
    social_breakdown_boost: float,
    maturity_days: float,
    imprint_rate: float,
    imprint_thr: float,
):
    i = wp.tid()
    if alive[i] == 0:
        return
    dens_frac = dens_frac_arr[0]
    c = cell_id[i]
    local = float(cell_counts[c]) / capacity_per_cell
    gain = stress_density_gain * local
    over = float(0.0)
    nid = nest_id[i]
    if nid >= 0:
        if nest_occ[nid] > nest_cap[nid]:
            gain = gain + nest_overcrowd_stress
            over = float(nest_occ[nid]) / float(nest_cap[nid]) - 1.0
    if dens_frac > menopause_thr:
        gain = gain + social_breakdown_boost
    # Relaxation toward gain/decay (smooth in density; mirrors sim._density_stress).
    stress[i] = wp.clamp(stress[i] + (gain - stress_decay * stress[i]) * dt, 0.0, 1.5)
    if stress[i] > 0.9 and social_drive[i] > 0.0:
        social_drive[i] = wp.max(0.0, social_drive[i] - 0.05)
    # Developmental imprinting: young lose social competence under crowding; frozen at maturity.
    if age_days[i] < maturity_days:
        exposure = wp.max(0.0, local - imprint_thr) + over
        competence[i] = wp.clamp(competence[i] - imprint_rate * exposure * dt, 0.0, 1.0)


@wp.kernel
def mortality_kernel(
    alive: wp.array(dtype=wp.int32),
    role: wp.array(dtype=wp.int32),
    stress: wp.array(dtype=wp.float32),
    wounds: wp.array(dtype=wp.float32),
    age_days: wp.array(dtype=wp.float32),
    hunger: wp.array(dtype=wp.float32),
    thirst: wp.array(dtype=wp.float32),
    energy: wp.array(dtype=wp.float32),
    rng_states: wp.array(dtype=wp.uint32),
    dt: float,
    base_mort: float,
    stress_mort: float,
    max_age: float,
    young_scale: float,
    dens_mort: float,
    dens_frac_arr: wp.array(dtype=wp.float32),
):
    i = wp.tid()
    if alive[i] == 0:
        return
    dens_frac = dens_frac_arr[0]
    p = base_mort * dt
    if role[i] == 0 or role[i] == 1:
        p = p * young_scale
    p = p + dens_mort * dens_frac * dens_frac * dt
    p = p + stress_mort * stress[i] * stress[i] * dt
    p = p + 0.02 * wounds[i] * wounds[i] * dt
    if age_days[i] > max_age:
        p = p + 0.05 * dt
    if hunger[i] > 1.2 or thirst[i] > 1.2:
        p = p + 0.1 * dt
    if energy[i] < 0.05:
        p = p + 0.2 * dt
    # xorshift
    s = rng_states[i]
    s = s ^ (s << wp.uint32(13))
    s = s ^ (s >> wp.uint32(17))
    s = s ^ (s << wp.uint32(5))
    rng_states[i] = s
    u = float(s) / 4294967295.0
    if u < p:
        alive[i] = 0
        role[i] = 7  # DEAD


@wp.kernel
def update_cells_kernel(
    alive: wp.array(dtype=wp.int32),
    x: wp.array(dtype=wp.float32),
    y: wp.array(dtype=wp.float32),
    cell_id: wp.array(dtype=wp.int32),
    in_playground: wp.array(dtype=wp.int32),
    width: float,
    height: float,
    n_cells_x: int,
    n_cells_y: int,
    pg_enabled: int,
    pg_x0: float,
    pg_y0: float,
    pg_x1: float,
    pg_y1: float,
):
    i = wp.tid()
    if alive[i] == 0:
        return
    cw = width / float(n_cells_x)
    ch = height / float(n_cells_y)
    ix = wp.clamp(int(x[i] / cw), 0, n_cells_x - 1)
    iy = wp.clamp(int(y[i] / ch), 0, n_cells_y - 1)
    cell_id[i] = iy * n_cells_x + ix
    if pg_enabled == 1:
        if x[i] >= pg_x0 and x[i] <= pg_x1 and y[i] >= pg_y0 and y[i] <= pg_y1:
            in_playground[i] = 1
        else:
            in_playground[i] = 0
    else:
        in_playground[i] = 0
