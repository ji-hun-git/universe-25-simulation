"""Body weight and coat colour: biology each animal carries, kept apart from the colony's
dynamics unless `body.weight_effects` is on.

Weight (grams)
- A Richards growth curve per sex, fitted to the Jackson Laboratory BALB/cJ body-weight chart
  (stock 000651: weekly means at weeks 3-13 for females and 3-10 for males, 6 % fat diet) from
  an assumed birth weight of 1.3 g. RMSE 0.6 g (females) and 0.4 g (males). Beyond the chart's
  ages the curve is an extrapolation.
- Each animal weighs
      frame x curve(age, sex) x condition x late-life decline + pregnancy + lactation
  where frame is a fixed individual size factor; condition relaxes (body.relax_days) toward a
  value set by energy, hunger and stress, so the young follow the curve while thin or fat
  animals change over days; pregnancy rises with the square of gestation progress, and
  lactation holds a nursing mother a little above her curve. Every term but the curve is a
  stated assumption (config BodyConfig).

Coat colour
- Three loci with Mendelian inheritance: agouti (A > a), brown (Tyrp1, B > b) and albino
  (Tyr, C > c). c/c masks the other two (albino, red eyes).
- Calhoun's founders were BALB/c: A/A b/b c/c, white with hidden agouti and brown alleles.
  `coat.founders` can instead seed a BALB/c x C57BL/6 cross (C57BL/6: a/a B/B C/C, black) or
  wild-type agouti founders. These are variants, not the record.
- At conception the pregnancy takes a sire from the males that could have sired it; each pup
  takes one allele per locus from each parent.

Isolation
- Nothing here draws from the simulator's random stream or writes an AgentSoA field. The body
  has its own stream, SeedSequence([seed, 9_100_001]).
- So with weight_effects off, the colony's trajectory and its golden hashes are unchanged, and
  the coat never acts on anything.
- weight_effects (off by default, uncalibrated) lets weight act on fights, conception, litter
  size and survival; those hooks live in sim.py and use the simulator's stream.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from universe25.agents.state import ROLE_NURSING, SEX_M

if TYPE_CHECKING:  # pragma: no cover
    from universe25.sim import Universe25Sim

BODY_STREAM = 9_100_001
# genotype bits, 1 = the dominant allele: A1 A2 (agouti) B1 B2 (Tyrp1) C1 C2 (Tyr)
LOCI = ((0, 1), (2, 3), (4, 5))
STRAINS = {
    "balbc": 0b000011,  # A/A b/b c/c: albino
    "c57bl6": 0b111100,  # a/a B/B C/C: black
    "wild_type": 0b111111,  # A/A B/B C/C: agouti
}
COATS = ("albino", "agouti", "cinnamon", "black", "chocolate")
NO_SIRE = 255


def richards(age: np.ndarray, m_inf: float, k: float, shape: float, m0: float) -> np.ndarray:
    """Richards growth: m_inf * (1 - b e^{-k t})^{1/(1-shape)}, b set by the birth weight m0."""
    b = 1.0 - (m0 / m_inf) ** (1.0 - shape)
    t = np.maximum(np.asarray(age, dtype=np.float64), 0.0)
    return m_inf * (1.0 - b * np.exp(-k * t)) ** (1.0 / (1.0 - shape))


def phenotype(geno: np.ndarray) -> np.ndarray:
    """0 albino, 1 agouti, 2 cinnamon (agouti on brown), 3 black, 4 chocolate (brown)."""
    g = np.asarray(geno, dtype=np.int64)
    a = (g & 0b000011) != 0
    b = (g & 0b001100) != 0
    c = (g & 0b110000) != 0
    pig = np.where(a, np.where(b, 1, 2), np.where(b, 3, 4))
    return np.where(c, pig, 0).astype(np.uint8)


def genotype_text(geno: int) -> str:
    names = (("A", "a"), ("B", "b"), ("C", "c"))
    parts = []
    for (i, j), (dom, rec) in zip(LOCI, names):
        x, y = (geno >> i) & 1, (geno >> j) & 1
        parts.append(f"{dom if x | y else rec}/{dom if x & y else rec}")  # dominant first
    return " ".join(parts)


def inherit(mother: int, sire: int, draws: np.ndarray) -> int:
    """One pup's genotype: per locus one of the mother's two alleles and one of the sire's,
    chosen by draws (six numbers in [0, 1))."""
    out = 0
    for n, (i, j) in enumerate(LOCI):
        from_m = (mother >> (i if draws[2 * n] < 0.5 else j)) & 1
        from_s = (sire >> (i if draws[2 * n + 1] < 0.5 else j)) & 1
        out |= (from_m << i) | (from_s << j)
    return out


class Body:
    """Per-slot weight, size frame and coat genotype, with the hooks sim.py calls."""

    def __init__(self, sim: Universe25Sim):
        self.sim = sim
        self.cfg = sim.cfg.body
        cap = sim.cfg.max_agents
        self.rng = np.random.default_rng(np.random.SeedSequence([int(sim.cfg.seed), BODY_STREAM]))
        self.mass = np.zeros(cap, dtype=np.float32)
        self.frame = np.ones(cap, dtype=np.float32)
        self.cond = np.ones(cap, dtype=np.float32)  # lean weight over frame x curve
        self.coat = np.full(cap, STRAINS["balbc"], dtype=np.uint8)
        self.preg_coat = np.full(cap, NO_SIRE, dtype=np.uint8)  # the sire's genotype
        self.relax = 1.0 - np.exp(-sim.dt_days / max(1e-6, float(self.cfg.relax_days)))

    # ---------------------------------------------------------------- curves and condition
    def curve(self, age: np.ndarray, male: np.ndarray) -> np.ndarray:
        c = self.cfg
        f = richards(age, *c.female_curve, c.birth_mass_g)
        m = richards(age, *c.male_curve, c.birth_mass_g)
        return np.where(male, m, f)

    def _condition(self, idx: np.ndarray) -> np.ndarray:
        """Nutritional and stress condition, 1 = a fed, unstressed animal (an assumption)."""
        a = self.sim.agents
        c = self.cfg
        energy = a.energy[idx].astype(np.float64)
        cond = (1.0 + c.condition_energy * (energy - c.condition_energy_ref)
                - c.condition_hunger * np.maximum(0.0, a.hunger[idx] - 1.0)
                - c.condition_stress * np.maximum(0.0, a.stress[idx] - 0.6))
        return np.clip(cond, c.condition_min, c.condition_max)

    def _late(self, age: np.ndarray) -> np.ndarray:
        c = self.cfg
        return np.clip(1.0 - c.senescence_per_day * np.maximum(0.0, age - c.senescence_onset_days),
                       c.senescence_floor, 1.0)

    def _extra(self, idx: np.ndarray, curve: np.ndarray) -> np.ndarray:
        """Pregnancy (rising with the square of gestation progress) and lactation, in grams."""
        a = self.sim.agents
        c = self.cfg
        gd = float(self.sim.cfg.biology.gestation_days)
        g = np.where(a.gestating[idx] > 0, 1.0 - a.gestating[idx] / gd, 0.0)
        preg = c.pregnancy_gain * curve * np.clip(g, 0.0, 1.0) ** 2
        lact = np.where((a.role[idx] == ROLE_NURSING) & (a.gestating[idx] <= 0),
                        c.lactation_gain * curve, 0.0)
        return preg + lact

    def _mass(self, idx: np.ndarray) -> np.ndarray:
        """Weight from the current condition: frame x curve x condition x decline + extras."""
        a = self.sim.agents
        age = a.age_days[idx].astype(np.float64)
        curve = self.curve(age, a.sex[idx] == SEX_M)
        lean = self.frame[idx] * curve * self.cond[idx] * self._late(age)
        return lean + self._extra(idx, curve)

    # ---------------------------------------------------------------- per tick
    def update(self) -> None:
        """Condition relaxes toward its target; weight follows (deterministic, no draw)."""
        a = self.sim.agents
        idx = np.flatnonzero(a.alive)
        if idx.size == 0:
            return
        c = self.cond[idx].astype(np.float64)
        c += (self._condition(idx) - c) * self.relax
        self.cond[idx] = c
        self.mass[idx] = self._mass(idx)

    # ---------------------------------------------------------------- life events
    def spawn(self, slot: int, sex: int, age: float) -> None:
        """Defaults for any spawned animal: its curve weight, an average frame, BALB/c coat."""
        male = np.array([sex == SEX_M])
        self.frame[slot] = 1.0
        self.mass[slot] = float(self.curve(np.array([age]), male)[0])
        self.cond[slot] = 1.0
        self.coat[slot] = STRAINS["balbc"]
        self.preg_coat[slot] = NO_SIRE

    def _frame(self) -> float:
        return float(np.clip(self.rng.normal(1.0, self.cfg.frame_sd), 0.85, 1.15))

    def found(self, slots: np.ndarray) -> None:
        """Founders: their own frames, and coats from coat.founders (pairs are female, male)."""
        a = self.sim.agents
        kind = self.sim.cfg.coat.founders
        for k, s in enumerate(slots):
            s = int(s)
            self.frame[s] = self._frame()
            male = np.array([a.sex[s] == SEX_M])
            self.mass[s] = self.frame[s] * float(self.curve(np.array([a.age_days[s]]), male)[0])
            if kind == "cb6_cross":  # BALB/c females x C57BL/6 males (CB6F1 young)
                self.coat[s] = STRAINS["c57bl6" if a.sex[s] == SEX_M else "balbc"]
            else:
                self.coat[s] = STRAINS[kind]

    def conceive(self, female: int, cands: list[int]) -> None:
        """The pregnancy's sire: among the males that could have sired it, on the body stream."""
        if not cands:
            return
        sire = cands[int(self.rng.integers(len(cands)))] if len(cands) > 1 else cands[0]
        self.preg_coat[female] = self.coat[int(sire)]

    def birth(self, mother: int, pup: int) -> None:
        """A pup: birth weight times its own frame, and one allele per locus from each parent."""
        self.frame[pup] = self._frame()
        self.mass[pup] = self.cfg.birth_mass_g * self.frame[pup]
        self.cond[pup] = 1.0
        sire = int(self.preg_coat[mother])
        if sire == NO_SIRE:  # no sire recorded (a harness pregnancy): the mother's own
            sire = int(self.coat[mother])
        self.coat[pup] = inherit(int(self.coat[mother]), sire, self.rng.random(6))

    def delivered(self, mother: int) -> None:
        """After the litter: the mother's pregnancy weight leaves with it."""
        self.mass[mother] = float(self._mass(np.array([mother]))[0])
        self.preg_coat[mother] = NO_SIRE

    # ---------------------------------------------------------------- effects (off by default)
    def fight_reversal(self, attacker: int, target: int) -> float:
        """Chance that the heavier target wins the fight its attacker started."""
        r = float(self.mass[target]) / max(1e-6, float(self.mass[attacker]))
        c = self.cfg
        return float(np.clip(c.fight_mass_slope * (r - 1.0), 0.0, c.fight_reverse_max))

    def fertility(self, female: int) -> float:
        lo, width = self.cfg.fertility_condition_floor, self.cfg.fertility_condition_width
        return float(np.clip((float(self.cond[female]) - lo) / width, 0.0, 1.0))

    def litter_scale(self, mother: int) -> float:
        return float(np.clip(self.cond[mother], 0.7, 1.1))

    def emaciation(self, idx: np.ndarray) -> np.ndarray:
        c = self.cfg
        return c.emaciation_hazard_per_day * np.clip(
            (c.emaciation_condition - self.cond[idx]) / 0.15, 0.0, 1.0)
