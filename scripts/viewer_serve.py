"""Local server for the viewer (`viewer/`): the app, the recordings in `_output/viewer/`, and
live runs started from its control panel (one at a time, stepped in a background thread).

usage: python scripts/viewer_serve.py [--port 8765]   then open http://127.0.0.1:8765/
Binds 127.0.0.1 only. Standard library only.

API
  GET  /api/info                 presets, recordings, live state
  GET  /rec/<name>.u25           a recording (binary; scripts/viewer_frames.py)
  POST /api/live                 start a live run {preset, seed, days, backend, playground,
                                 free_substeps, ball_physics, sample, rate}; returns its world
  GET  /api/live/frames?after=i  the live run's frames after index i (binary, same format),
                                 the run's status in the header
  POST /api/live/control         {"op": "pause" | "resume" | "stop"} or {"rate": days per second}
  POST /api/snapshot?name=n      a PNG the viewer rendered, or a JSON note about one (body),
                                 saved as _output/figures/<n>.png or .json (n: 1-48 of a-z,
                                 0-9, _)

A live run is the run `main.py` makes from the same config, seed and overrides (capture only
reads); it writes its own metrics.parquet and config.json to `_output/viewer_live/<stamp>/`."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import threading
import time
import traceback
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from viewer_frames import ROOT, capture, hook_substeps, pack, world_meta  # noqa: E402

from universe25.config import load_config  # noqa: E402
from universe25.sim import Universe25Sim  # noqa: E402

APP = ROOT / "viewer"
# what the server writes: the repo's _output, or the app's data folder (universe25.app, U25_DATA)
DATA = Path(os.environ.get("U25_DATA") or ROOT / "_output")
REC = DATA / "viewer"
LIVE_OUT = DATA / "viewer_live"
SHOTS = DATA / "figures"  # rendered views (scripts/hero_figure.py reads hero_pen.png)
SHOT_MAX = 40 * 2**20
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# A preset is a config, and optionally a fitted member whose parameters it takes
# ("member": a JSON file with "members", the first of which is used).
PRESETS = {
    "universe25": {"label": "Universe 25: Calhoun's pen (final replica)",
                   "config": "configs/replica_v2.yaml", "member": "configs/replica_v2_final.json",
                   # NOTES 2026-11-19: the record fits (U-1, U-3) failed; this member stays.
                   # Seeds 9112-9159, adults counted as Calhoun did (131 days or older).
                   "about": "Calhoun's pen without the playground, as fitted in replica v2. On 48 "
                            "fresh seeds it grows and collapses in 46 runs, and 11 of the "
                            "record's 14 population and timeline numbers fall inside its 5-95 % "
                            "range (9 on an earlier set of 48 seeds). Misses: the peak (2,490; "
                            "record 2,200), N on day 960 (1,320; 1,650) and the last conception "
                            "(day 1,096; 920). Adults are counted as Calhoun counted them, from "
                            "131 days old. Its behaviour is not Calhoun's: few withdrawn mice "
                            "and no beautiful ones."},
    "reference": {"label": "Reference colony (phase 2m, simplified pen)",
                  "config": "configs/default.yaml",
                  "about": "The research colony: Calhoun's sizes in a simplified pen (a 4 x 4 "
                           "grid, nests as points, and a playground he never had). Its population "
                           "curve was fitted to the record: 11 of 15 values inside on 48 seeds. "
                           "It starts late and then grows too fast, so on day 315 it has few "
                           "adults as Calhoun counted them (131 days or older)."},
    "replica": {"label": "Calhoun's pen, unfitted (replica v2 M1-M4)",
                "config": "configs/replica_v2.yaml",
                "about": "Calhoun's own pen with replica v2's settings before any fit (M1-M4)."},
    "scarce": {"label": "Scarce arm (research)", "config": "configs/scarce.yaml",
               "about": "Phase 4's scarce arm: the research colony with food for 1,000 a day."},
}


def _deep(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _deep(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def preset_config(name: str, overrides: dict | None = None):
    """The config a preset runs: its YAML, its member's parameters, then `overrides`."""
    preset = PRESETS.get(name, PRESETS["reference"])
    over: dict = {}
    if preset.get("member"):
        doc = json.loads((ROOT / preset["member"]).read_text(encoding="utf-8"))
        over = dict(doc["members"][0]["params"])
    return load_config(ROOT / preset["config"], _deep(over, overrides or {}))
SAMPLES = ("day", "tick", "sub")
BUFFER_BYTES = 384 * 2**20  # frames kept for clients; the oldest go first
MAX_FRAMES_PER_RESPONSE = 600


class LiveRun:
    """One live run: the simulator stepped in a thread, frames kept in a bounded buffer."""

    def __init__(self, params: dict):
        self.params = params
        self.lock = threading.Lock()
        self.frames: deque[tuple[int, dict, bytes]] = deque()
        self.next_index = 0
        self.bytes = 0
        self.state = "starting"
        self.error: str | None = None
        self.world: dict | None = None
        self.rate = float(params.get("rate", 4.0))  # sim days per wall second; 0 = flat out
        self.resume = threading.Event()
        self.resume.set()
        self.stopping = False
        self.ticks_per_s = 0.0
        self.day = 0.0
        self.n = 0
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # ------------------------------------------------------------------ thread
    def _config(self):
        p = self.params
        backend = p.get("backend", "numpy")
        overrides: dict = {"seed": int(p.get("seed", 7000)), "backend": backend,
                           "snapshot_every_days": 0}
        if backend == "numpy":
            overrides["device"] = "cpu"
        if p.get("days"):
            overrides["days"] = float(p["days"])
        k = int(p.get("free_substeps", 1))
        if k > 1:
            overrides["free_substeps"] = k
        pg: dict = {}
        if p.get("playground") in ("on", "off"):
            pg["enabled"] = p["playground"] == "on"
        if p.get("ball_physics"):
            pg["ball_physics"] = True
        if pg:
            overrides["playground"] = pg
        if p.get("coat") in ("balbc", "cb6_cross", "wild_type"):
            overrides["coat"] = {"founders": p["coat"]}
        if p.get("weight_effects"):
            overrides["body"] = {"weight_effects": True}
        return preset_config(p.get("preset", "reference"), overrides)

    def _push(self, frame: tuple[dict, bytes]) -> None:
        meta, payload = frame
        with self.lock:
            self.frames.append((self.next_index, meta, payload))
            self.next_index += 1
            self.bytes += len(payload)
            while self.bytes > BUFFER_BYTES and len(self.frames) > 1:
                _, _, old = self.frames.popleft()
                self.bytes -= len(old)
            self.day, self.n = meta["t"], meta["n"]

    def _run(self) -> None:
        try:
            cfg = self._config()
            out = LIVE_OUT / time.strftime("%Y%m%d_%H%M%S")
            sim = Universe25Sim(cfg, out)
            self.world = world_meta(sim)
            self.world["run"]["preset"] = self.params.get("preset", "reference")
            sample = self.params.get("sample", "day")
            if sample == "sub":
                hook_substeps(sim, lambda s, j, t: self._push(capture(s, t, sub=j + 1)))
            self._push(capture(sim, 0.0))
            self.state = "running"
            self.ready.set()
            per_day = cfg.ticks_per_day
            total = int(cfg.days * per_day)
            wall0, day0 = time.perf_counter(), 0.0
            rate_seen = self.rate
            win_t, win_k = time.perf_counter(), 0
            for _ in range(total):
                if self.stopping:
                    break
                if not self.resume.is_set():
                    self.state = "paused"
                    self.resume.wait()
                    if self.stopping:
                        break
                    self.state = "running"
                    wall0, day0 = time.perf_counter(), sim.day
                if self.rate != rate_seen:
                    rate_seen = self.rate
                    wall0, day0 = time.perf_counter(), sim.day
                sim.step()
                if sample in ("tick", "sub") or sim.tick % per_day == 0:
                    self._push(capture(sim))
                win_k += 1
                now = time.perf_counter()
                if now - win_t >= 1.0:
                    self.ticks_per_s, win_t, win_k = win_k / (now - win_t), now, 0
                if rate_seen > 0:
                    ahead = (sim.day - day0) / rate_seen - (now - wall0)
                    if ahead > 0:
                        time.sleep(min(ahead, 0.5))
                if sim.agents.n_alive == 0 and sim.day > 100:
                    break
            if sim.tick % per_day != 0 and sample == "day":
                self._push(capture(sim))
            sim.logger.close()
            self.state = "stopped" if self.stopping else "finished"
        except Exception as e:  # reported to the client, which shows it
            self.error = f"{type(e).__name__}: {e}"
            self.state = "error"
            traceback.print_exc()
        finally:
            self.ready.set()

    # ------------------------------------------------------------------ clients
    def status(self) -> dict:
        return {"state": self.state, "error": self.error, "day": self.day, "n": self.n,
                "ticks_per_s": round(self.ticks_per_s, 1), "rate": self.rate,
                "frames": self.next_index, "params": self.params}

    def after(self, i: int) -> bytes:
        with self.lock:
            items = [f for f in self.frames if f[0] > i][:MAX_FRAMES_PER_RESPONSE]
        first = items[0][0] if items else self.next_index
        frames = [(meta, payload) for _, meta, payload in items]
        # indices are consecutive inside the buffer, so pack's first + offset is each index
        return pack(frames, {"status": self.status()}, first=first)

    def control(self, body: dict) -> None:
        op = body.get("op")
        if op == "pause":
            self.resume.clear()
        elif op == "resume":
            self.resume.set()
        elif op == "stop":
            self.stopping = True
            self.resume.set()
        if "rate" in body:
            self.rate = max(0.0, float(body["rate"]))


class Server(ThreadingHTTPServer):
    daemon_threads = True
    live: LiveRun | None = None


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, fmt: str, *args) -> None:  # quiet: API polls many times a second
        if not self.path.startswith("/api/live/frames"):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def _file(self, path: Path, root: Path) -> None:
        try:
            path = path.resolve()
            path.relative_to(root.resolve())
        except (ValueError, OSError):
            return self._json({"error": "not found"}, 404)
        if not path.is_file():
            return self._json({"error": "not found"}, 404)
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            ctype = "text/javascript"
        self._send(200, path.read_bytes(), ctype)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        live = self.server.live
        if url.path == "/api/info":
            recs = []
            for f in sorted(REC.glob("*.u25")):
                side = f.with_suffix(".json")
                summary = json.loads(side.read_text(encoding="utf-8")) if side.is_file() else {}
                recs.append({"name": f.stem, "bytes": f.stat().st_size, "summary": summary})
            return self._json({"presets": PRESETS, "samples": SAMPLES, "recordings": recs,
                               "live": live.status() if live else None})
        if url.path == "/api/live/frames":
            if live is None:
                return self._json({"error": "no live run"}, 404)
            after = int(parse_qs(url.query).get("after", ["-1"])[0])
            return self._send(200, live.after(after), "application/octet-stream")
        if url.path.startswith("/rec/"):
            return self._file(REC / url.path[len("/rec/"):], REC)
        rel = url.path.lstrip("/") or "index.html"
        return self._file(APP / rel, APP)

    def _snapshot(self, url) -> None:
        """Save a PNG the viewer rendered, or a JSON note about it, to _output/figures/."""
        name = parse_qs(url.query).get("name", [""])[0]
        if not re.fullmatch(r"[a-z0-9_]{1,48}", name):
            return self._json({"error": "name: 1 to 48 of a-z, 0-9 and _"}, 400)
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 < n <= SHOT_MAX:
            return self._json({"error": "empty or too large"}, 413)
        data = self.rfile.read(n)
        ext = "png"
        if not data.startswith(PNG_MAGIC):
            try:
                json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self._json({"error": "not a PNG or JSON"}, 400)
            ext = "json"
        SHOTS.mkdir(parents=True, exist_ok=True)
        out = SHOTS / f"{name}.{ext}"
        out.write_bytes(data)
        shown = out.relative_to(ROOT).as_posix() if out.is_relative_to(ROOT) else str(out)
        return self._json({"path": shown, "bytes": n})

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path == "/api/snapshot":
            return self._snapshot(url)
        try:
            body = self._body()
        except json.JSONDecodeError:
            return self._json({"error": "bad JSON"}, 400)
        if url.path == "/api/live":
            old = self.server.live
            if old is not None:
                old.control({"op": "stop"})
                old.thread.join(timeout=10)
            run = LiveRun(body)
            self.server.live = run
            run.ready.wait(timeout=120)
            if run.state == "error":
                return self._json({"error": run.error}, 500)
            return self._json({"world": run.world, "status": run.status()})
        if url.path == "/api/live/control":
            if self.server.live is None:
                return self._json({"error": "no live run"}, 404)
            self.server.live.control(body)
            return self._json({"status": self.server.live.status()})
        return self._json({"error": "not found"}, 404)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args(argv)
    REC.mkdir(parents=True, exist_ok=True)
    srv = Server(("127.0.0.1", a.port), Handler)
    print(f"viewer on http://127.0.0.1:{a.port}/  (recordings: {REC})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
