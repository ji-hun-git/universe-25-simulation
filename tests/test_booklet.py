"""The booklet (scripts/booklet.py, docs/FIGURES.md) is generated from the hero figure's data:
the committed page must equal a fresh build from docs/figures/hero.json and
phase4_ledger.yaml, and it must carry every test of the ledger and the predictive check's
count. A stale page means: python scripts/booklet.py."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

import booklet  # noqa: E402


def test_page_is_current() -> None:
    committed = booklet.PAGE.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert committed == booklet.current(), "docs/booklet.html is stale: python scripts/booklet.py"


def test_page_carries_the_ledger_and_the_check() -> None:
    page = booklet.current()
    led = yaml.safe_load(booklet.LEDGER.read_text(encoding="utf-8"))
    for t in led["tests"]:
        assert f">{t['id']}<" in page, t["id"]
    assert "inside the 90 % interval" in page
    assert "How close is it to Universe 25?" in page  # the limits stay in the booklet
    assert booklet.PDF.is_file(), "the printed booklet is missing"


if __name__ == "__main__":
    test_page_is_current()
    test_page_carries_the_ledger_and_the_check()
    print("test_booklet: OK")
