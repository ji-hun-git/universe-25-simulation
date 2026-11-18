"""Universe 25, the app: the viewer and its live runs on this machine (README, "App").

Start it with `universe25-app` (after `pip install -e .` in the repo) or with the built Windows
program (`scripts/build_app.py`). It serves the viewer on 127.0.0.1 only, opens it in the
browser on the live-run panel, and runs until its window is closed (or Ctrl+C).

Where things are:
- resources (the viewer, the configs, the server modules): the repo, or the program's own folder
  when built;
- data (recordings, live runs, saved views): the repo's `_output/`, or, for the built program,
  `%LOCALAPPDATA%\\Universe25` (`~/Universe25` elsewhere). Recordings shipped with the program are
  copied there on first start.
"""
from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import webbrowser
from pathlib import Path

PORT = 8765


def resources() -> Path:
    """The folder holding viewer/, configs/ and scripts/."""
    if getattr(sys, "frozen", False):  # the built program
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for p in Path(__file__).resolve().parents:
        if (p / "viewer" / "index.html").is_file() and (p / "configs").is_dir():
            return p
    raise SystemExit("Universe 25: the viewer files were not found next to the package. Run "
                     "it from the repo (pip install -e .) or use the built program.")


def data_dir(root: Path) -> Path:
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "Universe25"
    return root / "_output"


def free_port(start: int = PORT, tries: int = 20) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"Universe 25: no free port in {start}-{start + tries - 1}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = resources()
    data = data_dir(root)
    os.environ.setdefault("U25_ROOT", str(root))
    os.environ.setdefault("U25_DATA", str(data))
    (data / "viewer").mkdir(parents=True, exist_ok=True)
    shipped = root / "recordings"  # recordings that come with the built program
    if shipped.is_dir():
        for f in shipped.glob("*.u25"):
            for g in (f, f.with_suffix(".json")):
                dst = data / "viewer" / g.name
                if g.is_file() and not dst.exists():
                    shutil.copy2(g, dst)
    for sub in ("scripts", "src"):
        p = str(root / sub)
        if p not in sys.path:
            sys.path.insert(0, p)
    import viewer_serve  # noqa: E402  (scripts/, or bundled with the program)

    port = free_port()
    url = f"http://127.0.0.1:{port}/?start=live"
    print("Universe 25 is running at " + url)
    print(f"Recordings and runs are kept in {data}")
    print("Close this window (or press Ctrl+C) to quit.", flush=True)
    if "--no-browser" not in argv:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    return viewer_serve.main(["--port", str(port)])


if __name__ == "__main__":
    raise SystemExit(main())
