"""The hero figure's managed inputs (scripts/hero_figure.py, docs/FIGURES.md): the phase-4
ledger is well formed and every verdict has a style; the predictive-check reading marks a
record value outside the 5-95 % range as a miss; the committed figure and its provenance file
agree with the ledger."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

import hero_figure as hf  # noqa: E402


def test_ledger_is_well_formed() -> None:
    led = yaml.safe_load(hf.LEDGER.read_text(encoding="utf-8"))
    assert isinstance(led.get("summary"), str) and led["summary"].strip()
    ids = [t["id"] for t in led["tests"]]
    assert len(ids) == len(set(ids)), ids
    for t in led["tests"]:
        assert re.fullmatch(r"H-[a-z]", t["id"]), t["id"]
        assert t["verdict"] in hf.VERDICT_STYLE, (t["id"], t["verdict"])
        assert 0 < len(t["question"]) <= 60, t["id"]  # fits a chip in three lines
        assert len(t.get("note") or "") <= 70, t["id"]
        assert t.get("notes"), f"{t['id']}: name the NOTES section that records it"
        d = t.get("date")
        assert d is None or re.fullmatch(r"\d\d-\d\d", str(d)), (t["id"], d)


def test_ppc_marks_misses() -> None:
    from universe25.metrics.calibration import LANDMARKS

    obs = [{"peak_n": 2100.0 + 10 * i, "first_litters_day": 200.0 + i} for i in range(21)]
    rows = {r["landmark"]: r for r in hf.ppc(obs)}
    assert LANDMARKS["peak_n"] == 2200.0 and not rows["peak_n"]["miss"]
    assert rows["first_litters_day"]["miss"]  # the record's 104 lies below every run
    assert rows["peak_n"]["n"] == 21


def test_ppc_reads_calhouns_adults() -> None:
    """Adults on day 315 are read from the count 131 days or older, as Calhoun counted them
    (NOTES 2026-11-19); read_as={} gives the check as first run, from sexual maturity."""
    obs = [{"adults_at_day_315": 140.0 + i, "adults_131_at_day_315": 40.0 + i} for i in range(21)]
    row = {r["landmark"]: r for r in hf.ppc(obs)}["adults_at_day_315"]
    assert row["miss"] and row["read_as"] == "adults_131_at_day_315"
    first = {r["landmark"]: r for r in hf.ppc(obs, read_as={})}["adults_at_day_315"]
    assert not first["miss"] and "read_as" not in first


def test_committed_figure_matches_its_ledger() -> None:
    meta = json.loads((hf.FIG / "hero.json").read_text(encoding="utf-8"))
    assert (ROOT / meta["file"]).is_file()
    assert meta["ledger"] == hf.LEDGER.relative_to(ROOT).as_posix()
    assert meta["ppc"]["of"] >= meta["ppc"]["inside"] > 0
    rows = {r["landmark"]: r for r in meta["ppc"]["rows"]}
    assert rows["adults_at_day_315"].get("read_as") == hf.READ_AS["adults_at_day_315"], \
        "the figure counts adults from sexual maturity: run scripts/hero_figure.py draw"
    assert meta.get("ledger_sha256") == hf.ledger_hash(), \
        "the ledger changed after the figure was drawn: run scripts/hero_figure.py draw"


if __name__ == "__main__":
    test_ledger_is_well_formed()
    test_ppc_marks_misses()
    test_ppc_reads_calhouns_adults()
    test_committed_figure_matches_its_ledger()
    print("test_hero_figure: OK")
