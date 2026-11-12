"""Pydantic configuration for Universe 25 (+ playground)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Strict(BaseModel):
    """Unknown keys are errors, so a misspelt key cannot load silently (review 2026-11-09)."""

    model_config = ConfigDict(extra="forbid")


class GeometryConfig(_Strict):
    """Calhoun 1973 pen: 101 x 101 inches, 16 cells, 256 nests."""

    width_in: float = 101.0
    height_in: float = 101.0
    n_cells_x: int = 4
    n_cells_y: int = 4
    nests_per_cell: int = 16
    food_per_cell: int = 1
    water_per_cell: int = 1
    capacity_design: int = 3840
    # Replica v2 (docs/REPLICA_V2.md, M1). "grid": the 4 x 4 grid of the frozen 2m colony.
    # "calhoun": Calhoun's 16 triangular cells (base a 25.25-in wall segment, apex at the
    # centre; 1973 p. 82, Marsden 1972 p. 7), four tunnels of four box levels per cell, a wall
    # hopper and a water platform per cell.
    layout: Literal["grid", "calhoun"] = "grid"
    # Feeding / drinking capacity per cell per day (Calhoun's design limits: food for 9500 and
    # water for 6144 mice, i.e. 593.75 / 384 per cell), split evenly over the decisions; at a
    # hopper, foragers beyond it this decision do not eat (highest rank first). 0 = unlimited.
    hopper_meals_per_day: float = Field(0.0, ge=0.0)
    water_drinks_per_day: float = Field(0.0, ge=0.0)
    # Calhoun's December 1968 reconfiguration (1971 p. 339): until this day each box had its
    # own food and water, so animals eat and drink at their own box. 0 = off.
    box_feeding_until_day: float = Field(0.0, ge=0.0)
    # Cells the founding pairs start in; None = the layout's default (grid: the corners
    # 0 / 3 / 12 / 15; calhoun: the second cell of each wall, 1 / 5 / 9 / 13 - an assumption,
    # the record does not say where the founders were placed).
    founder_cells: list[int] | None = None
    # Replica v2 M3 (docs/REPLICA_V2.md). box_choice: an animal needing a box (homeless, or
    # kicked from an overfull one) takes the fullest box below capacity in its cell (lower level,
    # then lower id, on ties), else its cell's emptiest; off = nearest box / uniform random box.
    box_choice: bool = False
    # hopper_facilitation (calhoun layout): after box_feeding_until_day a forager heads for the
    # hopper, among its cell's and its two wall neighbours', with the most foragers at the
    # previous decision (ties: its own, then the lower id).
    hopper_facilitation: bool = False
    # Replica v2 M4 amendment: an animal reaching maturity leaves its natal box and takes one by
    # the box-choice rule (needs box_choice). Off = boxes are kept for life (the frozen colony).
    disperse_at_maturity: bool = False
    # Replica v2 M4 / M6: only these cells of the calhoun pen are open (a move ending in a
    # closed cell is undone; founders go to open cells). None = all 16.
    open_cells: list[int] | None = None


class PlaygroundConfig(_Strict):
    """Optional playground zone. Geometry only — no play reward."""

    enabled: bool = True
    x0: float = 35.0
    y0: float = 35.0
    x1: float = 66.0
    y1: float = 66.0
    n_balls: int = 8
    n_tunnels: int = 4
    n_ramps: int = 2
    # Ball physics (P4-13, PHASE4_DESIGN.md 1.9): balls are pushed by free-time moves that end
    # in contact (kappa x the approach), roll with friction and bounce at the bounds; object-
    # family curiosity / boredom relief scales with the speed a contact gave a ball. Runs in the
    # free-time sub-step loop (needs free_substeps > 1). False = off (bit-identical).
    ball_physics: bool = False


class ResourceConfig(_Strict):
    mode: Literal["abundant", "scarce"] = "abundant"
    food_refill_per_tick: float = 1e9
    water_refill_per_tick: float = 1e9
    scarce_food_per_day: float = 50.0
    # Scarce mode supply rule. "fixed": scarce_food_per_day in total per day, split equally over
    # the cells (phase 1). "capacity" (SCARCE-PG arm of phase 4): a food-limited carrying
    # capacity - the colony receives enough food per day for scarce_capacity_animals animals
    # eating at hunger_gain_per_day, shared out to the cells in proportion to their weaned
    # occupants, each cell's stock capped at two days of its share. Below the capacity food is
    # effectively free; above it every animal gets capacity / N of a full ration.
    scarce_supply: Literal["fixed", "capacity"] = "fixed"
    scarce_capacity_animals: float = 1000.0
    # Optional famine pulses in capacity mode: every famine_period_days the supply drops to
    # famine_factor of normal for famine_days (0 = no famines).
    scarce_famine_period_days: float = 0.0
    scarce_famine_days: float = 0.0
    scarce_famine_factor: float = 1.0


class BiologyConfig(_Strict):
    """Life-history + density/social mechanisms (no scheduled collapse day)."""

    gestation_days: float = 20.0
    litter_mean: float = 7.0
    litter_sd: float = 1.5
    weaning_days: float = 21.0
    maturity_days: float = 50.0
    max_age_days: float = 800.0
    # Per-individual lifespan: normal around max_age_days with this sd (floor 0.3 x mean),
    # drawn at birth. 0 = one cutoff for all (the 400-600 cohorts then die together, 2e-2k).
    max_age_sd_days: float = 0.0
    base_mortality_per_day: float = 0.0005
    stress_mortality_scale: float = 0.01
    wound_heal_per_day: float = 0.1  # wounds recover; mortality ~ wounds^2 while open
    # Death hazard (per day) while hunger or thirst exceeds 1.2. Unfed newborn mice die within
    # days; at the previous 0.1/day about one never-nursed pup in ten reached weaning, which
    # put a floor under the last-surviving-birth landmark.
    starvation_hazard_per_day: float = 1.0
    first_conception_min_day: float = 95.0
    menopause_density_threshold: float = 0.55
    maternal_neglect_stress: float = 0.7
    # Tunables for principled calibration (priors in calib/priors.py)
    breeding_p_base: float = 0.55
    breeding_stress_coef: float = 0.7
    nest_overcrowd_stress: float = 0.2
    withdrawn_stress_threshold: float = 0.85
    withdrawn_social_threshold: float = 0.2
    pup_hunger_scale: float = 0.35
    young_mortality_scale: float = 0.25
    mate_radius_in: float = 20.0
    stillbirth_neglect_p: float = 0.5
    density_mortality_scale: float = 0.0  # extra death rate ~ dens^2
    social_breakdown_stress_boost: float = 0.0  # added stress gain when dens high
    # Density fraction above which the breakdown stress boost applies (Calhoun's behavioural
    # sink: pathological crowding sets in at a density, not a day). None = use
    # menopause_density_threshold (the conception ramp), as before phase 2e.
    breakdown_density_threshold: float | None = None
    # Which animals the breakdown switch counts: "all" (as before) or "weaned" (the social
    # arena; unweaned pups sit in nest boxes). Weaned numbers fall only through adult mortality,
    # so once the switch is on it stays on long enough for maternal breakdown to be lasting.
    breakdown_density_counts: Literal["all", "weaned"] = "weaned"
    # Width (density fraction) over which the breakdown boost ramps linearly from 0 to its full
    # value, ending at breakdown_density_threshold: social pressure builds as the arena fills
    # (Calhoun phase C: infant mortality rose gradually from Day 315 on), instead of switching
    # on at one density. 0 = step (phase 2e-2g behaviour).
    breakdown_density_ramp: float = 0.0
    beautiful_one_aggression_max: float = 0.15
    # Developmental imprinting (Calhoun 1973: young raised under crowding never acquire
    # normal maternal / courtship / territorial behaviour; the deficit is irreversible).
    # `competence` is a generic social-development trait, not a play term (H2).
    imprint_rate: float = 0.05  # competence loss per day per unit exposure, young only
    imprint_density_threshold: float = 0.15  # local cell density frac where exposure starts
    # Colony-wide developmental exposure: young also lose competence at imprint_rate x this
    # gain x the breakdown factor (the weaned-density ramp), wherever they are. Calhoun /
    # Marsden: mice raised while the colony's social organisation had broken down never
    # acquired reproductive behaviour even in uncrowded cells or after transfer ("death of
    # the spirit"); without it the sparse cells' late cohorts stay competent and the colony
    # can rebound once the old cohorts die (phase 2l). 0 = off.
    imprint_breakdown_exposure: float = 0.0
    withdrawn_competence_threshold: float = 0.3  # adults below this withdraw ("beautiful ones")
    female_fertile_max_age_days: float = 420.0  # reproductive senescence (lab mouse ~12-15 mo)
    # Daily chance that a nursing mother above maternal_neglect_stress abandons her nest box's
    # litter (Calhoun phase C: litters abandoned, young expelled pre-weaning). 0 = off.
    litter_abandon_p: float = 0.0
    # Removal event (ported 2026-11-09 from the unmerged phase 2n branch, commit cd09878, for the
    # posterior predictive check). Calhoun 1973 Fig 2 caption: about 150 mice were removed for
    # other studies after day 1000, so the censuses of 122 at day 1444 and 27 at day 1588 are
    # post-removal counts. Once, on the first day-aligned tick at or after removal_day,
    # removal_n alive adults chosen uniformly at random from the simulation RNG stream are taken
    # out of the universe; they are counted as `removed`, not as deaths. Both 0 = off (no RNG
    # draw, bit-identical). Not part of the calibrated biology (e.g. 1014 / 150).
    removal_day: float = Field(default=0.0, ge=0.0)
    removal_n: int = Field(default=0, ge=0)
    # Replica v2 M2 (docs/REPLICA_V2.md). Founders' age at day 0 (Calhoun 1973: 48 days); None =
    # the frozen colony's uniform 60-90 draw.
    founder_age_days: float | None = Field(default=None, ge=0.0)
    # Territories: one owner (an adult male) per cell, claimed after territory_settle_days daily
    # passes as the cell's top male, contested daily by a present male ranked at least
    # owner - territory_gap; conception needs the female's cell to have an owner, who sires.
    # Off = the frozen rule (any adult male in the cell, cell mean courtship), bit-identical.
    territories: bool = False
    territory_settle_days: int = Field(default=14, ge=1)
    territory_gap: float = Field(default=0.15, gt=0.0)
    # Replica v2 M3. Fidelity: a male who owns or claims the cell he is in does not leave it (a
    # move out is undone); an owner takes his cell's emptiest box; the territorial role means an
    # owner. Tolerance (calhoun layout; Calhoun's basic group: 1 territorial + 3 subordinate
    # males): at each decision an owner in his territory keeps the N lowest-ranked adult males
    # there and displaces the rest to 10 in from the pen centre; territories (and the territory
    # pass) exclude the disc of territory_centre_in around the centre. None = off.
    territory_fidelity: bool = False
    territory_tolerance: int | None = Field(default=None, ge=0)
    territory_centre_in: float = Field(default=12.0, gt=10.0)
    # Replica v2 M4 (docs/REPLICA_V2.md). breakdown_scope "individual" removes the three
    # colony-wide terms (breakdown stress boost, colony-wide developmental exposure, conception
    # suppression by N / design capacity). care_imprint_gain: a pup also loses competence at
    # imprint_rate x gain x its care deficit (max(0, hunger - 0.5) housed, 1 unhoused).
    # exclusion_stress: stress added per displacement by a territory owner. aggression_targets
    # "by_sex": males attack males only, females only while nursing. wound_mortality_scale: the
    # death hazard per wound^2 per day (the frozen hard-coded 0.02).
    breakdown_scope: Literal["colony", "individual"] = "colony"
    care_imprint_gain: float = Field(default=0.0, ge=0.0)
    exclusion_stress: float = Field(default=0.0, ge=0.0)
    aggression_targets: Literal["any", "by_sex"] = "any"
    wound_mortality_scale: float = Field(default=0.02, ge=0.0)
    # Replica v2 M7: intergenerational transmission of maternal care (Francis et al. 1999). Every
    # pup accumulates the nursing weight it receives; at weaning a daughter's maternal capacity
    # becomes (1 - tau) + tau * min(1, care index / care_ref), care index = accumulated weight /
    # weaning_days. Conception does not depend on maternal capacity. 0 = off.
    maternal_transmission: float = Field(default=0.0, ge=0.0, le=1.0)
    care_ref: float = Field(default=0.0, ge=0.0)
    # Replica v2 M8. withdrawn_disengage: adults whose developmental competence is below
    # withdrawn_competence_threshold (withdrawn for life, Calhoun's "beautiful ones") neither
    # fight nor are fought; animals withdrawn by stress alone fight as before.
    # fertility_from_competence False: a female's conception no longer scales with her
    # developmental competence, and a female withdrawn for low competence can still conceive;
    # male courtship and maternal investment still scale with competence.
    withdrawn_disengage: bool = False
    fertility_from_competence: bool = True

    def breakdown_threshold(self) -> float:
        if self.breakdown_density_threshold is not None:
            return float(self.breakdown_density_threshold)
        return float(self.menopause_density_threshold)

    def breakdown_factor(self, density: float) -> float:
        """Fraction of social_breakdown_stress_boost applied at a (weaned) density fraction:
        1 above the threshold, a linear ramp over breakdown_density_ramp below it, else 0."""
        thr = self.breakdown_threshold()
        if density > thr:
            return 1.0
        ramp = float(self.breakdown_density_ramp)
        if ramp <= 0.0:
            return 0.0
        return max(0.0, 1.0 - (thr - density) / ramp)

    # Nursing is relaxation toward satiety: while a lactating mother of its box is in contact,
    # a pup's hunger/thirst deficit decays at nurse_rate_per_day x her maternal investment
    # (composable over sub-steps, so tick resolution cannot change daily milk; no clipping).
    nurse_rate_per_day: float = 6.0
    nurse_max_pups: int = 6  # a mother's milk is shared when more pups than this are in contact
    # Post-weaning maternal breakdown (Calhoun phase C/D: established mothers attacked and
    # expelled their young, stopped nest building, while conceptions continued to ~Day 920).
    # Irreversible loss of maternal capacity per day per unit stress above the threshold, for
    # every weaned female (juveniles exposed to the breakdown never acquire the capacity).
    maternal_erosion_rate: float = 0.0  # 0 = off
    maternal_erosion_stress: float = 0.6
    # Male counterpart (Calhoun phase D: males stopped courting and defending territory, so
    # conceptions ended ~Day 920 although fertile females remained). Irreversible loss of
    # courtship capacity per day per unit stress above the threshold, weaned males; the
    # cell's male competence in the daily breeding pass is competence x courtship capacity.
    courtship_erosion_rate: float = 0.0  # 0 = off
    courtship_erosion_stress: float = 0.6
    # Fertility follows the female's own breakdown state (Calhoun phase D: the incidence of
    # pregnancies declined rapidly after the peak while conceptions went on to ~Day 920): the
    # daily conception probability is scaled by floor + (1 - floor) x maternal_cap. 1.0 = off.
    fertility_cap_floor: float = 1.0
    # Nursing disturbance (Calhoun phase C: nursing females in crowded cells were disturbed,
    # moved litters and dropped young; infant mortality rose with density before the social
    # breakdown): a mother's effective maternal investment while nursing is scaled by
    # exp(-coef x max(0, local cell density - onset)). Reversible, density-graded. coef 0 = off.
    nurse_disturb_coef: float = 0.0
    nurse_disturb_density: float = 0.15
    # Conception suppression in crowded cells (Calhoun's behavioural sink: reproduction in the
    # most crowded cells was disrupted while cells with a territorial male and few females kept
    # breeding). A female's daily conception probability is scaled by
    # clip(1 - (local cell density - onset) / width, 0, 1): untouched below the onset, zero at
    # onset + width. Spatial and graded, unlike the whole-population menopause term. width 0 = off.
    conception_density_onset: float = 0.4
    conception_density_width: float = 0.0


class DriveConfig(_Strict):
    """Homeostatic / social drives. Absolutely no play term."""

    hunger_gain_per_day: float = 1.2
    thirst_gain_per_day: float = 1.5
    fatigue_gain_active: float = 0.4
    fatigue_recovery_rest: float = 0.8
    stress_density_gain: float = 0.35
    stress_decay: float = 0.15
    social_drive_gain: float = 0.2
    curiosity_gain: float = 0.12
    curiosity_decay_on_novel: float = 0.35
    boredom_gain: float = 0.08
    boredom_decay_on_vary: float = 0.25
    # Novelty-based curiosity (P4-14, PHASE4_DESIGN.md 1.10): locomotor curiosity relief scales
    # with the novelty of the bin entered (per-animal last-visit memory on a grid,
    # 1 - exp(-dt / tau)); consequence_gain also scales the ball-push relief (1.9). Needs
    # free_substeps > 1. False = off (bit-identical); consequence_gain 1.0 = P4-13.
    curiosity_novelty: bool = False
    novelty_grid: int = Field(10, ge=1)
    novelty_tau_days: float = Field(1.0, gt=0.0)
    consequence_gain: float = Field(1.0, ge=0.0)
    aggression_baseline: float = 0.1
    aggression_scarce_boost: float = 0.5


class PPOConfig(_Strict):
    # Shared-parameter PPO for policy.kind mlp_ppo (learn/ppo.py; PHASE4_DESIGN.md 1.5). The
    # reward is the homeostatic drive reduction only (learn/reward.py).
    enabled: bool = True  # False = act with the initial network, never update (baseline)
    lr: float = 3e-4
    lr_decay_updates: int = 0  # linear decay to 10 % over this many updates (0 = constant)
    epochs: int = 4
    minibatches: int = 4
    clip: float = 0.2
    gae_lambda: float = 0.95
    gamma_per_decision: float = 0.98  # per decision (4 h); per sub-step gamma ** (1 / K)
    # 0.05, not the design's 0.01: at 0.01 the shared policy learned during the ~3 weeks of
    # gestation before any litter exists that the nest never pays, drove P(NEST), P(NURSE)
    # for mothers from 0.10 to 0.003 / 0.005 and never rediscovered nursing (pups starved);
    # at 0.05 mothers nurse like the heuristic (training seed 7000 nursery, NOTES 2026-11-06).
    entropy_coef: float = 0.05
    # P4-15 (PHASE4_DESIGN.md 4.2) learner-signal options; the defaults reproduce every earlier
    # run. Entropy weight annealed linearly from entropy_coef to entropy_coef_final over the
    # transition count [entropy_anneal_start, entropy_anneal_end] (None = constant).
    entropy_coef_final: float | None = None
    entropy_anneal_start: float = 0.0
    entropy_anneal_end: float = 0.0
    # "pooled": advantages normalised over the minibatch; "per_type": separately for
    # transitions opened at a decision and at a free-time sub-step
    adv_norm: Literal["pooled", "per_type"] = "pooled"
    # True: a transition's GAE lambda factor is gae_lambda ** (duration / K), so lambda applies
    # per decision however the decision is split into sub-steps (False: per transition)
    gae_lambda_per_unit_time: bool = False
    vf_coef: float = 0.5
    huber_delta: float = 1.0
    max_grad_norm: float = 1.0
    rollout_ticks: int = 12  # decisions between updates
    device: Literal["auto", "cpu", "cuda"] = "auto"
    cpu_threads: int = 4


class PolicyConfig(_Strict):
    # Which policy chooses among the eligible actions at each decision (agents/policy.py).
    # "need_driven" is the phase 1/2 utility softmax (bit-identical to the inline version it
    # replaced). "mlp_frozen" is a fixed-weight MLP over agents/observation.py (NumPy
    # inference; weights from `weights` (.npz) or a seeded orthogonal init when null). Learned
    # kinds never receive a play-named observation, reward or goal (H2) and sample from their
    # own RNG stream.
    kind: Literal["need_driven", "mlp_frozen", "mlp_ppo"] = "need_driven"
    weights: str | None = None  # path to an .npz with W1 b1 W2 b2 W3 b3 (mlp kinds)
    hidden: int = 128  # hidden width for a random init (ignored when weights is set)
    # Free-time sub-steps (SimConfig.free_substeps > 1): "continue" repeats the decision action
    # at every sub-step (distributionally the same reach and relief as the decision), "rechoose"
    # lets the policy choose among the free actions at every sub-step. "auto" = continue for
    # need_driven (its motives exist only at the decision grain; re-choosing moved the
    # calibrated curve, NOTES 2026-11-06 P4-8), rechoose for learned kinds.
    substep_mode: Literal["auto", "continue", "rechoose"] = "auto"
    ppo: PPOConfig = Field(default_factory=PPOConfig)


class TraceConfig(_Strict):
    # Per-agent decision traces for the eval-only detectors (metrics/trace.py), recorded in day
    # windows [start, end) and written as trace_<start>_<end>.npz. Empty = off: no recorder,
    # bit-identical tick. The recorder draws no random numbers and writes no simulation state.
    windows: list[tuple[float, float]] = Field(default_factory=list)
    sample_every: int = 1  # keep rows only for individuals whose uid is a multiple of this


class SimConfig(_Strict):
    seed: int = 7000
    ticks_per_day: int = 24
    # Per-decision effect magnitudes (nursing amounts, drive relief, wounds, conception chance
    # per attempt, random-walk steps) are specified at this resolution; the tick loop rescales
    # them by ticks_per_day_ref / ticks_per_day (√ of that for random walks) so daily totals do
    # not depend on ticks_per_day. Movement reaches its target within one decision at any dt.
    ticks_per_day_ref: int = 6
    max_agents: int = 4096
    initial_pairs: int = Field(4, ge=0)  # 0: a pen filled by a harness (replica transfers)
    days: float = 1600.0
    device: Literal["cuda", "cpu", "auto"] = "auto"
    backend: Literal["warp", "torch", "numpy", "auto"] = "auto"
    log_every_ticks: int = 24
    snapshot_every_days: int = 50
    arm_label: str = "TRACK-E-U25-ABUND-PG"
    use_cuda_graph: bool = False
    geometry: GeometryConfig = Field(default_factory=GeometryConfig)
    playground: PlaygroundConfig = Field(default_factory=PlaygroundConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    biology: BiologyConfig = Field(default_factory=BiologyConfig)
    drives: DriveConfig = Field(default_factory=DriveConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    trace: TraceConfig = Field(default_factory=TraceConfig)
    # Free-time sub-steps (P4-8): an agent whose decision action is EXPLORE / SOCIAL /
    # MANIPULATE replays that decision's move and curiosity / boredom / social relief as this
    # many sub-steps, the policy re-choosing among the free actions at each (1/K of the reach
    # and relief per sub-step, its own RNG stream). Feeding, nursing, conception, stress and
    # mortality stay per decision. 1 = off (bit-identical).
    free_substeps: int = Field(1, ge=1)
    # Runtime invariant checks after every tick (universe25/invariants.py); read-only, so the
    # trajectory is the same with them on. Off by default (cost).
    debug_invariants: bool = False
    # Methods fixes (review 2026-11-09; replica v2 M5), off = the frozen numerics:
    # fresh_cell_counts: the per-tick cell-count cache is refreshed after the moves (it was read
    # pre-move by the nursing disturbance on most ticks); synchronous_fights: every fight of a
    # decision picks its target by the ranks at the decision's start, not after earlier fights.
    fresh_cell_counts: bool = False
    synchronous_fights: bool = False

    @model_validator(mode="after")
    def _replica_layout(self) -> SimConfig:
        g = self.geometry
        if g.layout == "calhoun":
            if g.n_cells_x * g.n_cells_y != 16 or g.nests_per_cell != 16:
                raise ValueError("geometry.layout calhoun has 16 cells of 16 boxes")
            if self.backend == "warp":
                raise ValueError("the Warp path implements only geometry.layout grid")
        b = self.biology
        if b.territories and self.backend == "warp":
            raise ValueError("biology.territories is implemented on the NumPy path only")
        if (b.territory_fidelity or b.territory_tolerance is not None) and not b.territories:
            raise ValueError("territory_fidelity / territory_tolerance need biology.territories")
        if b.territory_fidelity and self.free_substeps > 1:
            raise ValueError("territory_fidelity restores moves per decision: no sub-steps")
        if g.layout != "calhoun" and (g.hopper_facilitation or b.territory_tolerance is not None):
            raise ValueError("hopper_facilitation / territory_tolerance need layout calhoun")
        if (g.box_choice or g.hopper_facilitation) and self.backend == "warp":
            raise ValueError("box_choice / hopper_facilitation are NumPy-path only")
        m4 = (b.breakdown_scope != "colony" or b.care_imprint_gain > 0.0
              or b.aggression_targets != "any" or b.wound_mortality_scale != 0.02)
        if m4 and self.backend == "warp":
            raise ValueError("the M4 biology fields are NumPy-path only")
        if b.maternal_transmission > 0.0:
            if b.care_ref <= 0.0:
                raise ValueError("maternal_transmission needs care_ref > 0")
            if self.backend == "warp":
                raise ValueError("maternal_transmission is NumPy-path only")
        if (b.withdrawn_disengage or not b.fertility_from_competence) and self.backend == "warp":
            raise ValueError("withdrawn_disengage / fertility_from_competence are NumPy-path only")
        if g.disperse_at_maturity and not g.box_choice:
            raise ValueError("disperse_at_maturity needs geometry.box_choice")
        if g.open_cells is not None:
            oc = list(g.open_cells)
            if g.layout != "calhoun" or not oc or len(set(oc)) != len(oc) or not all(
                    0 <= c < 16 for c in oc):
                raise ValueError("open_cells: distinct calhoun cells 0-15")
            if not g.box_choice or self.free_substeps > 1:
                raise ValueError("open_cells needs geometry.box_choice and no sub-steps")
            if g.founder_cells is not None and not set(g.founder_cells) <= set(oc):
                raise ValueError("founder_cells must be open cells")
        return self

    @model_validator(mode="after")
    def _ticks_per_day_multiple_of_ref(self) -> SimConfig:
        ref = self.ticks_per_day_ref
        if self.ticks_per_day < ref or self.ticks_per_day % ref != 0:
            raise ValueError(f"ticks_per_day ({self.ticks_per_day}) must be a multiple of "
                             f"ticks_per_day_ref ({ref}): decisions are held over whole ticks")
        return self

    @model_validator(mode="after")
    def _physics_needs_substeps(self) -> SimConfig:
        if self.playground.ball_physics and self.free_substeps < 2:
            raise ValueError("playground.ball_physics needs free_substeps > 1")
        if self.drives.curiosity_novelty and self.free_substeps < 2:
            raise ValueError("drives.curiosity_novelty needs free_substeps > 1")
        return self

    @field_validator("seed")
    @classmethod
    def _seed_range(cls, v: int) -> int:
        if v < 7000 or v >= 10000:
            raise ValueError(f"seed {v} outside allowed seed band [7000,10000)")
        if 5000 <= v < 6000:
            raise ValueError("seed in reserved band")
        return v


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> SimConfig:
    data: dict[str, Any] = {}
    if path is not None:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    if overrides:
        data = _deep_merge(data, overrides)
    return SimConfig.model_validate(data)


def _deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
