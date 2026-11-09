"""Golden trajectory hashes, fast tier (src/universe25/golden.py; table in
tests/golden/trajectories.json). Every arm of the feature-flag matrix must reproduce its
recorded hash, and the traced arm must equal the untraced one. Skipped with a note when the table
was recorded on another platform or NumPy version (hashes are not portable across them)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from universe25.golden import check  # noqa: E402


def test_golden_fast() -> None:
    bad, skip = check("fast")
    if skip:
        print(f"test_golden: skipped ({skip})")
        return
    assert not bad, "\n".join(bad)


if __name__ == "__main__":
    test_golden_fast()
    print("test_golden: OK")
