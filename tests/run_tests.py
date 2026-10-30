"""Runner for __main__ tests (shared venv has no pytest)."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    failed = 0
    for path in sorted(HERE.glob("test_*.py")):
        print(f"--- {path.name}")
        try:
            runpy.run_path(str(path), run_name="__main__")
        except Exception as e:
            failed += 1
            print(f"FAIL {path.name}: {type(e).__name__}: {e}")
    print(f"done failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
