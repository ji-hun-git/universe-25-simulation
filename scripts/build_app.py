#!/usr/bin/env python
"""Build the Universe 25 app (U-2; README "App"): a folder with Universe25.exe, the viewer, the
configs its presets use and a sample recording, zipped as dist/Universe25-windows.zip.

It needs PyInstaller in the Python that runs it: a separate build venv, never the shared one.
  python -m venv .venv-app
  .venv-app\\Scripts\\python -m pip install pyinstaller "numpy>=2,<3" pydantic pyyaml pyarrow
  .venv-app\\Scripts\\python scripts\\build_app.py
The built program needs no Python. It serves the viewer on 127.0.0.1 and opens the browser;
recordings and runs go to %LOCALAPPDATA%\\Universe25. Warp (GPU), scipy and matplotlib are
left out: the app runs the NumPy path, the deterministic reference.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

DIST = ROOT / "dist"
WORK = ROOT / "build" / "app"
SAMPLES = ("replica_7000",)  # recordings shipped from _output/viewer/, when present
LEAVE_OUT = ("scipy", "matplotlib", "torch", "warp", "optuna", "IPython", "tkinter")


def preset_files() -> list[str]:
    """The configs and member files the server's presets read."""
    import viewer_serve

    files = set()
    for p in viewer_serve.PRESETS.values():
        files.add(p["config"])
        if p.get("member"):
            files.add(p["member"])
    return sorted(files)


def main() -> int:
    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError:
        print("PyInstaller is not installed in this Python; see this script's docstring.")
        return 2
    sep = ";" if sys.platform == "win32" else ":"
    data = [(ROOT / "viewer", "viewer")]
    data += [(ROOT / f, str(Path(f).parent)) for f in preset_files()]
    for name in SAMPLES:
        for ext in (".u25", ".json"):
            f = ROOT / "_output" / "viewer" / (name + ext)
            if f.is_file():
                data.append((f, "recordings"))
    args = [str(ROOT / "src" / "universe25" / "app.py"), "--name", "Universe25", "--onedir",
            "--console", "--noconfirm", "--distpath", str(DIST), "--workpath", str(WORK),
            "--specpath", str(WORK), "--paths", str(ROOT / "src"), "--paths", str(ROOT / "scripts"),
            "--hidden-import", "viewer_serve", "--hidden-import", "viewer_frames"]
    for mod in LEAVE_OUT:
        args += ["--exclude-module", mod]
    for src, dst in data:
        args += ["--add-data", f"{src}{sep}{dst}"]
    pyinstaller.run(args)
    out = DIST / "Universe25"
    tag = "windows" if sys.platform == "win32" else sys.platform
    zpath = DIST / f"Universe25-{tag}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(out.rglob("*")):
            zf.write(f, f.relative_to(DIST))
    mb = zpath.stat().st_size / 2**20
    print(f"built {out} and {zpath} ({mb:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
