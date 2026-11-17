"""Body weight and coat genetics (src/universe25/agents/body.py), fast tier.

- The growth curves reproduce the Jackson Laboratory BALB/cJ body-weight chart (000651).
- Inheritance is Mendelian: an F1 x F1 cross at the three loci gives 1/4 albino and, among the
  rest, agouti : cinnamon : black : chocolate as 9 : 3 : 3 : 1.
- Isolation: the coat acts on nothing. A BALB/c x C57BL/6 founder set gives the same colony
  as the record's BALB/c founders, bit for bit. Weight acts only with body.weight_effects.
- Weight follows life: late pregnancy is heavier than the curve, and the young follow it.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.agents.body import COATS, STRAINS, inherit, phenotype, richards  # noqa: E402
from universe25.config import BodyConfig, SimConfig  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402

# JAX BALB/cJ chart (stock 000651, 6 % fat diet): weekly means in grams
JAX_F = {3: 11.0, 4: 14.9, 5: 17.5, 6: 18.3, 7: 19.1, 8: 20.0, 9: 20.6, 10: 21.0, 11: 21.5,
         12: 22.6, 13: 23.4}
JAX_M = {3: 11.8, 4: 16.8, 5: 20.8, 6: 22.7, 7: 24.3, 8: 25.6, 9: 26.5, 10: 27.3}
DAYS = 130.0


def test_growth_matches_the_jax_chart() -> None:
    b = BodyConfig()
    for table, curve in ((JAX_F, b.female_curve), (JAX_M, b.male_curve)):
        weeks = np.array(sorted(table), dtype=float)
        got = richards(weeks * 7.0, *curve, b.birth_mass_g)
        want = np.array([table[int(w)] for w in weeks])
        assert np.abs(got - want).max() < 1.2, (got, want)
        assert np.sqrt(np.mean((got - want) ** 2)) < 0.7
    assert abs(float(richards(np.array([0.0]), *b.male_curve, b.birth_mass_g)[0]) - 1.3) < 1e-9


def test_inheritance_is_mendelian() -> None:
    rng = np.random.default_rng(1)
    f1 = 0b010101  # A/a B/b C/c, the CB6F1 hybrid of BALB/c and C57BL/6
    pups = np.array([inherit(f1, f1, rng.random(6)) for _ in range(40_000)])
    share = np.bincount(phenotype(pups), minlength=5) / pups.size
    want = np.array([0.25, 0.75 * 9 / 16, 0.75 * 3 / 16, 0.75 * 3 / 16, 0.75 * 1 / 16])
    assert np.abs(share - want).max() < 0.012, dict(zip(COATS, share.round(3)))
    # the record's founders breed true: BALB/c x BALB/c pups are all albino
    balb = [inherit(STRAINS["balbc"], STRAINS["balbc"], rng.random(6)) for _ in range(200)]
    assert (phenotype(np.array(balb)) == 0).all()


def _cfg(**over) -> SimConfig:
    cfg = SimConfig(seed=7004, days=DAYS, backend="numpy", device="cpu", max_agents=1024,
                    ticks_per_day=6, log_every_ticks=10**9, snapshot_every_days=0,
                    arm_label="TRACK-E-U25-TEST")
    for k, v in over.items():
        section, field = k.split("__")
        setattr(getattr(cfg, section), field, v)
    return cfg


def _run(cfg: SimConfig, out: Path):
    sim = Universe25Sim(cfg, out)
    late: list[float] = []
    for _ in range(int(DAYS * cfg.ticks_per_day)):
        sim.step()
        a, b = sim.agents, sim.body
        g = a.alive & (a.gestating > 0) & (a.gestating < 2.0)  # the last two days of gestation
        if g.any():
            i = np.flatnonzero(g)
            base = b.frame[i] * b.curve(a.age_days[i], a.sex[i] == 1)
            late.extend((b.mass[i] / base).tolist())
    sim.logger.close()
    a = sim.agents
    h = hashlib.sha256()
    for k in ("alive", "x", "y", "stress", "energy", "role", "age_days", "wounds", "rank"):
        h.update(np.ascontiguousarray(getattr(a, k)).tobytes())
    h.update(str(sim.rng.bit_generator.state).encode())
    return sim, h.hexdigest(), late


def test_coat_and_weight_isolation() -> None:
    with tempfile.TemporaryDirectory() as d:
        base, h0, late = _run(_cfg(), Path(d) / "a")
        cross, h1, _ = _run(_cfg(coat__founders="cb6_cross"), Path(d) / "b")
        fx, h2, _ = _run(_cfg(body__weight_effects=True), Path(d) / "c")
    assert base._births > 0 and late, "the window should include births and late pregnancies"
    assert h0 == h1, "the coat must not act on the colony"
    assert h0 != h2, "weight_effects on should change the colony"
    idx = np.flatnonzero(cross.agents.alive)
    ph = phenotype(cross.body.coat[idx])
    assert len(set(ph.tolist())) >= 2, "the cross should show more than one coat"
    assert (phenotype(base.body.coat[base.agents.alive]) == 0).all()
    # late pregnancy: well above the curve (pregnancy_gain 0.55 at term)
    assert np.median(late) > 1.35, np.median(late)
    # the young follow the curve: weaned juveniles near it
    a, b = base.agents, base.body
    juv = a.alive & (a.age_days > 25) & (a.age_days < 45)
    if juv.any():
        i = np.flatnonzero(juv)
        rel = b.mass[i] / (b.frame[i] * b.curve(a.age_days[i], a.sex[i] == 1))
        assert 0.85 < float(np.median(rel)) < 1.1, float(np.median(rel))


if __name__ == "__main__":
    test_growth_matches_the_jax_chart()
    test_inheritance_is_mendelian()
    test_coat_and_weight_isolation()
    print("test_body: OK")
