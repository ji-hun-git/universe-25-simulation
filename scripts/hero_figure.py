#!/usr/bin/env python
"""The hero figure: the research on one page (top of the README; registry in docs/FIGURES.md).

Panels
  a  the frozen colony on its fullest day in 3D, with a close-up: renders from the viewer
     (viewer/pen3d.js). Every mouse is drawn at real scale. Heights are drawn: the model is
     planar.
  b  population against Calhoun's census: the frozen colony (configs/default.yaml, K = 1,
     NumPy, 1,600 d) on the 48 predictive-check seeds 9000-9047 (NOTES 2026-11-09, Tier 1),
     median and 90 % interval, and how many record values fall inside the interval.
  c  where the colony crowds and who withdraws, on the same 48 runs: each cell's count over
     its design capacity (median), and the share of withdrawn animals.
  d  the play-emergence tests of phase 4 and their verdicts (docs/figures/phase4_ledger.yaml).

usage
  python scripts/hero_figure.py collect [--workers 8]   the 48 runs, cached in _output/hero/
  python scripts/hero_figure.py draw                    docs/figures/hero.png and hero.json

Panel a comes from the viewer. Run scripts/viewer_serve.py and open
http://127.0.0.1:8765/?rec=ref_7000&shot=hero (ref_7000 from scripts/viewer_record.py). That
writes _output/figures/hero_pen.png, hero_close.png and hero_shot.json. `draw` copies them into
docs/figures/src/ when they are newer, and otherwise uses the copies already there.

The runs are the predictive check's own: scripts/calib_reference.py builds them the same way.
`collect` checks every landmark against _output/calib_reference/rows.json when that file exists.
Nothing here changes the simulator or reads a seed for a new decision.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))  # viewer_frames: census and phases

CACHE = ROOT / "_output" / "hero"
SHOTS = ROOT / "_output" / "figures"
FIG = ROOT / "docs" / "figures"
SRC = FIG / "src"
LEDGER = FIG / "phase4_ledger.yaml"
ROWS = ROOT / "_output" / "calib_reference" / "rows.json"
SEEDS = tuple(range(9000, 9048))  # Tier 1 predictive-check seeds (docs/SEEDS.md)
DAYS, TPD = 1600.0, 6
# HANDOFF 8 tokens, as in viewer/viewer.css (light theme)
PAL = {"paper": "#F4F0E6", "paper2": "#EEE8DB", "paper3": "#E3DCCB", "ink": "#1A1A1A",
       "ink2": "#46423B", "ink3": "#7B7569", "stress": "#8B1E1E", "nest": "#2F5D50",
       "ochre": "#A2742A", "slate": "#4E6170", "umber": "#7A5236", "sand": "#B3A88F"}
# panel d: edge colour, fill and line style for each verdict the ledger may give
VERDICT_STYLE = {
    "falsified": (PAL["stress"], "#F1E0DA", "-"),
    "not supported": (PAL["ink2"], PAL["paper2"], "-"),
    "supported": (PAL["nest"], "#DCE7E1", "-"),
    "not specific": (PAL["ochre"], "#F2E8D5", "-"),
    "untested": (PAL["ink3"], PAL["paper"], "--"),
    "not read": (PAL["ink3"], PAL["paper"], ":"),
}


# ------------------------------------------------------------------ collect
def run_one(seed: int) -> tuple[int, dict[str, float]]:
    """One frozen-colony run as scripts/calib_reference.py makes it (evaluate_params with the
    need-driven arm config), recording the daily colony as well as the landmarks."""
    from universe25.calib.policy_guard import arm_config
    from universe25.calib.priors import params_to_overrides
    from universe25.config import load_config
    from universe25.metrics.calibration import landmarks_from_series
    from universe25.sim import Universe25Sim

    base = arm_config("need_driven", None, None, None)
    ov = params_to_overrides({})
    ov.update({"seed": seed, "days": DAYS, "ticks_per_day": TPD, "max_agents": 4096,
               "backend": "numpy", "device": "cpu", "log_every_ticks": 10**9,
               "snapshot_every_days": 0, "arm_label": "TRACK-E-U25-CALIB",
               "playground": {"enabled": True}, "use_cuda_graph": False})
    cfg = load_config(base, ov)
    td = Path(tempfile.mkdtemp(prefix="u25hero_"))
    try:
        sim = Universe25Sim(cfg, td)
        nc = sim.world.n_cells
        mat = cfg.biology.maturity_days
        day, n, births, last_young, adults, last_conc, roles, cells = ([] for _ in range(8))
        for _ in range(int(DAYS * TPD)):
            sim.step()
            if sim.tick % TPD == 0:
                a = sim.agents
                alive = a.alive
                day.append(sim.day)
                n.append(a.n_alive)
                births.append(sim._births)
                last_young.append(sim._last_surviving_young_day)
                adults.append(int(np.sum(alive & (a.age_days >= mat))))
                last_conc.append(sim._last_conception_day)
                roles.append(np.bincount(a.role[alive].astype(np.int64), minlength=8)[:7])
                c = a.cell_id[alive].astype(np.int64)
                cells.append(np.bincount(c[c >= 0], minlength=nc)[:nc])
            if sim.agents.n_alive == 0 and sim.day > 50:
                break
        try:
            sim.logger.close()
        except Exception:
            pass
        obs = landmarks_from_series(
            np.asarray(day, np.float64), np.asarray(n, np.float64),
            np.asarray(births, np.float64), np.asarray(last_young, np.float64),
            n_adult=np.asarray(adults, np.float64),
            last_conception=np.asarray(last_conc, np.float64),
            surv_births_by_day=sim._surv_births_by_day, conceptions_by_day=sim._conc_by_day)
    finally:
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(base.parent, ignore_errors=True)
    obs = {k: float(v) for k, v in obs.items()}
    np.savez_compressed(CACHE / f"frozen_{seed}.npz", day=np.asarray(day, np.float32),
                        n=np.asarray(n, np.int32), roles=np.asarray(roles, np.int32),
                        cells=np.asarray(cells, np.int32))
    (CACHE / f"frozen_{seed}.json").write_text(json.dumps(obs, indent=1), encoding="utf-8")
    return seed, obs


def check_rows() -> str:
    """Do the cached runs give the predictive check's landmarks, seed by seed?"""
    if not ROWS.is_file():
        return "not checked (no _output/calib_reference/rows.json here)"
    rows = json.loads(ROWS.read_text(encoding="utf-8"))["frozen"]
    same, diff = 0, []
    for s in SEEDS:
        mine = json.loads((CACHE / f"frozen_{s}.json").read_text(encoding="utf-8"))
        ref = rows.get(str(s))
        if ref is None:
            diff.append(f"{s}: not in rows.json")
            continue
        bad = [k for k in ref if k in mine and not (
            (np.isnan(ref[k]) and np.isnan(mine[k])) or abs(ref[k] - mine[k]) <= 1e-9)]
        if bad:
            diff.append(f"{s}: {', '.join(bad)}")
        else:
            same += 1
    return f"{same} of {len(SEEDS)} runs match rows.json" + (f"; differ: {diff}" if diff else "")


def collect(workers: int) -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = [s for s in SEEDS if not (CACHE / f"frozen_{s}.npz").is_file()]
    print(f"{len(todo)} of {len(SEEDS)} runs to make, {workers} workers", flush=True)
    t0 = datetime.now()
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for seed, obs in ex.map(run_one, todo):
                print(f"seed {seed}: peak {obs.get('peak_n', float('nan')):.0f} on day "
                      f"{obs.get('peak_day', float('nan')):.0f}", flush=True)
    print(f"done in {(datetime.now() - t0).total_seconds():.0f} s; {check_rows()}", flush=True)
    return 0


# ------------------------------------------------------------------ data for the panels
def load_runs():
    """Daily arrays over the 48 runs: N, withdrawn, cells (count), padded after extinction."""
    T = int(DAYS)
    N = np.zeros((len(SEEDS), T))
    W = np.full((len(SEEDS), T), np.nan)
    C = None
    obs = []
    for r, s in enumerate(SEEDS):
        z = np.load(CACHE / f"frozen_{s}.npz")
        k = len(z["n"])
        N[r, :k] = z["n"]
        with np.errstate(invalid="ignore", divide="ignore"):
            W[r, :k] = np.where(z["n"] > 0, z["roles"][:, 6] / np.maximum(z["n"], 1), np.nan)
        if C is None:
            C = np.zeros((len(SEEDS), T, z["cells"].shape[1]))
        C[r, :k] = z["cells"]
        obs.append(json.loads((CACHE / f"frozen_{s}.json").read_text(encoding="utf-8")))
    return np.arange(1, T + 1, dtype=float), N, W, C, obs


def ppc(obs: list[dict]) -> list[dict]:
    """scripts/calib_reference.py's predictive check: 5 / 50 / 95 % and a miss when the record
    value falls outside the 90 % interval."""
    from universe25.metrics.calibration import EXTRA_LANDMARKS, LANDMARKS, RECORD_LANDMARKS

    out = []
    for k, tgt in {**LANDMARKS, **EXTRA_LANDMARKS, **RECORD_LANDMARKS}.items():
        v = np.array([o.get(k, np.nan) for o in obs], float)
        v = v[np.isfinite(v)]
        if not v.size:
            continue
        lo, med, hi = np.quantile(v, [0.05, 0.5, 0.95])
        out.append({"landmark": k, "record": tgt, "median": float(med),
                    "pi90": [float(lo), float(hi)],
                    "miss": bool(not lo <= tgt <= hi), "n": int(v.size)})
    return out


def census() -> list[tuple[float, float]]:
    from viewer_frames import landmarks

    return [tuple(c) for c in landmarks()["census"]]


def phases() -> list[tuple[str, float, float | None]]:
    from viewer_frames import PHASES

    return list(PHASES)


def git_head() -> tuple[str, bool]:
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "configs",
                                     "scripts"],
                                    cwd=ROOT, capture_output=True, text=True).stdout.strip())
        return h, dirty
    except (OSError, subprocess.CalledProcessError):
        return "unknown", False


def renders() -> dict:
    """Panel a's images: fresh viewer renders in _output/figures/ are copied into
    docs/figures/src/ (JPEG); otherwise the copies there are used."""
    from PIL import Image

    SRC.mkdir(parents=True, exist_ok=True)
    meta_new = SHOTS / "hero_shot.json"
    meta_old = SRC / "hero_shot.json"
    shots = [SHOTS / "hero_pen.png", SHOTS / "hero_close.png"]
    fresh = meta_new.is_file() and all(p.is_file() for p in shots) and (not meta_old.is_file()
                                    or meta_new.stat().st_mtime > meta_old.stat().st_mtime)
    if fresh:  # kept at about 1.5x the size the figure draws them
        for name, width in (("hero_pen", 1800), ("hero_close", 1200)):
            im = Image.open(SHOTS / f"{name}.png").convert("RGB")
            im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
            im.save(SRC / f"{name}.jpg", quality=88, optimize=True, progressive=True)
        shutil.copyfile(meta_new, meta_old)
    if not meta_old.is_file():
        raise SystemExit("no panel-a renders: run the viewer with ?rec=ref_7000&shot=hero first")
    meta = json.loads(meta_old.read_text(encoding="utf-8"))
    meta["fresh"] = fresh
    return meta


# ------------------------------------------------------------------ draw
def draw() -> int:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import yaml
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import FancyBboxPatch, Polygon
    from PIL import Image

    days, N, W, C, obs = load_runs()
    checks = ppc(obs)
    inside = sum(not c["miss"] for c in checks)
    misses = [c for c in checks if c["miss"]]
    shot = renders()
    ledger = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    head, dirty = git_head()
    rows_check = check_rows()

    sans, serif, mono = "Segoe UI", "Georgia", "Consolas"
    plt.rcParams.update({
        "font.family": [sans, "DejaVu Sans"], "font.size": 7.5, "text.color": PAL["ink"],
        "axes.edgecolor": PAL["ink3"], "axes.linewidth": 0.6, "axes.labelcolor": PAL["ink2"],
        "xtick.color": PAL["ink3"], "ytick.color": PAL["ink3"], "xtick.labelcolor": PAL["ink2"],
        "ytick.labelcolor": PAL["ink2"], "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.labelsize": 6.6,
        "ytick.labelsize": 6.6, "axes.facecolor": PAL["paper"], "figure.facecolor": PAL["paper"],
        "savefig.facecolor": PAL["paper"],
    })
    Wf, Hf = 12.0, 7.85
    fig = plt.figure(figsize=(Wf, Hf), dpi=200)

    def ax_at(l_in, b_in, w_in, h_in):
        return fig.add_axes((l_in / Wf, b_in / Hf, w_in / Wf, h_in / Hf))

    def header(l_in, top_in, letter, title, sub=None):
        """A panel's letter and title above its axes, and a small line or two under them."""
        fig.text(l_in / Wf, (top_in + 0.36) / Hf, letter, fontsize=10.5, fontweight="bold",
                 va="bottom", ha="left")
        fig.text((l_in + 0.2) / Wf, (top_in + 0.36) / Hf, title, family=serif, fontsize=9.6,
                 va="bottom", ha="left")
        if sub:
            fig.text(l_in / Wf, (top_in + 0.32) / Hf, sub, fontsize=6.5, va="top", ha="left",
                     color=PAL["ink2"], linespacing=1.35)

    def clean(ax):
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    # ---- title
    fig.text(0.24 / Wf, (Hf - 0.18) / Hf, "Universe 25, simulated", family=serif, fontsize=17,
             va="top")
    fig.text(0.24 / Wf, (Hf - 0.55) / Hf,
             "A Calhoun-calibrated mouse colony (the frozen phase-2m biology) as the substrate "
             "for one question: does play-like behaviour appear without any play reward, under "
             "abundance and under scarcity?", fontsize=8.8, va="top", color=PAL["ink2"])
    row_top = Hf - 1.42

    # ---- a: the render, with the close-up in the empty corner
    img = np.asarray(Image.open(SRC / "hero_pen.jpg"))
    ih, iw = img.shape[:2]
    aw = 6.6
    ah = aw * ih / iw
    ax = ax_at(0.24, row_top - ah, aw, ah)
    ax.imshow(img, interpolation="lanczos")
    ax.set_axis_off()
    header(0.24, row_top, "a", "The frozen colony on its fullest day, in 3D",
           f"{shot['recording']} (seed {shot['seed']}), day {shot['day']:.0f}, {shot['n']:,} mice. "
           "Every mouse is drawn at real scale (BALB/c, albino).\n"
           "Heights are drawn: the model is planar. The grid layout is the frozen colony's "
           "abstract pen; its nest sites are floor points, drawn as pads.")
    poly = shot.get("close_poly")
    cimg = np.asarray(Image.open(SRC / "hero_close.jpg"))
    ch_, cw_ = cimg.shape[:2]
    inset_w = 0.31
    inset_h = inset_w * (aw / ah) * ch_ / cw_
    cax = ax.inset_axes((0.006, 0.006, inset_w, inset_h))
    cax.imshow(cimg, interpolation="lanczos")
    cax.set_xticks([]); cax.set_yticks([])
    for s in cax.spines.values():
        s.set_edgecolor(PAL["stress"]); s.set_linewidth(1.0)
    cax.text(0.012, 0.025, "close-up: the playground, crowds at food and water; pups are pink",
             transform=cax.transAxes, fontsize=6.0, va="bottom", color=PAL["ink"],
             bbox={"boxstyle": "square,pad=0.25", "fc": PAL["paper"], "ec": "none", "alpha": 0.9})
    if poly and len(poly) == 4:
        pts = np.array([[x * iw, y * ih] for x, y in poly])
        ax.add_patch(Polygon(pts, closed=True, fill=False, ec=PAL["stress"], lw=1.0))
        corner = pts[np.argmin(pts[:, 0] - pts[:, 1])]  # the polygon's lower-left corner
        x1, y1 = inset_w * iw + 0.006 * iw, (1 - 0.006 - inset_h) * ih
        ax.plot([x1, corner[0]], [y1, corner[1]], color=PAL["stress"], lw=0.7)

    # ---- b: population against the record
    rx = 0.24 + aw + 0.62
    rw = Wf - rx - 0.28
    bh = 1.62
    bx = ax_at(rx, row_top - bh, rw, bh)
    for i, (name, a0, a1) in enumerate(phases()):
        a1 = DAYS if a1 is None else a1
        bx.axvspan(a0, a1, color=PAL["paper3"] if i % 2 == 0 else PAL["paper2"], lw=0, zorder=0)
        bx.text((a0 + a1) / 2, 2560, name, ha="center", va="top", fontsize=6.8, color=PAL["ink3"])
    q05, q50, q95 = np.quantile(N, [0.05, 0.5, 0.95], axis=0)
    bx.fill_between(days, q05, q95, color=PAL["ink"], alpha=0.14, lw=0, zorder=2)
    bx.plot(days, q50, color=PAL["ink"], lw=1.3, zorder=3)
    cs = census()
    bx.plot([c[0] for c in cs], [c[1] for c in cs], ls="none", marker="+", ms=7, mew=1.5,
            color=PAL["stress"], zorder=4)
    bx.set_xlim(0, DAYS); bx.set_ylim(0, 2600)
    bx.set_yticks([0, 1000, 2000]); bx.set_yticklabels(["0", "1,000", "2,000"])
    bx.set_xticks([0, 400, 800, 1200, 1600]); bx.set_xticklabels([])
    bx.set_ylabel("mice", fontsize=7)
    clean(bx)
    names = {"n_at_day_736": "N on day 736", "doubling_time_phase_b_days": "doubling in phase B",
             "doubling_time_phase_c_days": "doubling in phase C"}
    header(rx, row_top, "b", "Population against Calhoun's census",
           f"Frozen colony on {len(SEEDS)} seeds ({SEEDS[0]}-{SEEDS[-1]}): median and 90 % "
           "interval. + census: Calhoun 1973, Marsden 1972.\n"
           f"{inside} of {len(checks)} record values fall inside the interval; outside: "
           + ", ".join(names.get(m["landmark"], m["landmark"]) for m in misses) + ".")

    # ---- c: crowding and withdrawal
    c_top = row_top - bh - 0.66
    chh = 1.18
    cxa = ax_at(rx, c_top - chh, rw, chh)
    cap = 3840.0 / C.shape[2]
    heat = np.median(C, axis=0).T / cap  # cells x days
    cmap = LinearSegmentedColormap.from_list("u25", [PAL["paper3"], PAL["ochre"], PAL["stress"]])
    im = cxa.imshow(heat, aspect="auto", cmap=cmap, vmin=0, vmax=1.5, interpolation="nearest",
                    extent=(0.5, DAYS + 0.5, heat.shape[0] - 0.5, -0.5))
    cxa.set_xlim(0, DAYS)
    cxa.set_yticks([0, 5, 10, 15]); cxa.set_ylabel("cell", fontsize=7)
    cxa.set_xticks([0, 400, 800, 1200, 1600]); cxa.set_xticklabels([])
    clean(cxa)
    header(rx, c_top, "c", "Where the colony crowds, and who withdraws",
           "Each cell's count over its design capacity of 240, median of the runs.\n"
           "Cells 5, 6, 9, 10 are central. Below: the share of withdrawn animals.")
    cb = fig.add_axes(((rx + rw - 1.05) / Wf, (c_top + 0.05) / Hf, 1.0 / Wf, 0.06 / Hf))
    cbar = fig.colorbar(im, cax=cb, orientation="horizontal", ticks=[0, 1, 1.5])
    cbar.ax.set_xticklabels(["0", "capacity", "1.5x"], fontsize=5.8)
    cbar.ax.tick_params(length=1.5, pad=1)
    cbar.outline.set_linewidth(0.4)
    wh = 0.5
    wx = ax_at(rx, c_top - chh - 0.08 - wh, rw, wh)
    w05, w50, w95 = np.nanquantile(W, [0.05, 0.5, 0.95], axis=0)
    wx.fill_between(days, w05 * 100, w95 * 100, color=PAL["umber"], alpha=0.16, lw=0)
    wx.plot(days, w50 * 100, color=PAL["umber"], lw=1.1)
    wx.set_xlim(0, DAYS); wx.set_ylim(0, 100)
    wx.set_yticks([0, 50, 100]); wx.set_yticklabels(["0", "50", "100 %"])
    wx.set_xticks([0, 400, 800, 1200, 1600])
    wx.set_xticklabels(["0", "400", "800", "1,200", "1,600 days"])
    clean(wx)
    wx.text(0.012, 0.95, "withdrawn share, median and 90 % interval", transform=wx.transAxes,
            fontsize=6.2, va="top", color=PAL["umber"])

    # ---- d: the ledger of phase-4 tests
    dh = 1.22
    d_top = 1.56
    dx = ax_at(0.24, d_top - dh, Wf - 0.52, dh)
    dx.set_xlim(0, 1); dx.set_ylim(0, 1); dx.set_axis_off()
    header(0.24, d_top, "d", "Play-emergence tests so far",
           "Phase 4, each preregistered (PLAN §15.1) before its run; verdicts as NOTES "
           "records them. " + ledger["summary"])
    style = VERDICT_STYLE
    items = ledger["tests"]
    k = len(items)
    gap = 0.008
    wbox = (1 - gap * (k - 1)) / k
    ln = 0.105 / dh  # one line of 6.2 pt text, in axes units
    for i, t in enumerate(items):
        x0 = i * (wbox + gap)
        ec, fc, ls = style[t["verdict"]]
        dx.add_patch(FancyBboxPatch((x0, 0.02), wbox, 0.96,
                                    boxstyle="round,pad=0,rounding_size=0.01",
                                    fc=fc, ec=ec, lw=0.8, ls=ls))
        dx.text(x0 + 0.007, 0.93, t["id"], fontsize=8.4, fontweight="bold", va="top")
        dx.text(x0 + wbox - 0.006, 0.925, t.get("date") or "", fontsize=5.8, family=mono,
                va="top", ha="right", color=PAL["ink3"])
        q = textwrap.wrap(t["question"], 25)
        y = 0.74
        dx.text(x0 + 0.007, y, "\n".join(q), fontsize=6.2, va="top", color=PAL["ink"],
                linespacing=1.3)
        y -= len(q) * ln + 0.05
        if t.get("note"):
            dx.text(x0 + 0.007, y, "\n".join(textwrap.wrap(t["note"], 29)), fontsize=5.6,
                    va="top", color=PAL["ink3"], linespacing=1.25)
        dx.text(x0 + 0.007, 0.07, t["verdict"], fontsize=7.4, fontweight="bold", va="bottom",
                color=ec)

    # ---- footer
    stamp = datetime.now().strftime("%Y-%m-%d")
    fig.text(0.24 / Wf, 0.1 / Hf,
             f"scripts/hero_figure.py · drawn {stamp} at commit {head}"
             f"{' with uncommitted changes' if dirty else ''} · b, c: frozen colony, "
             f"configs/default.yaml, the Tier 1 predictive-check seeds · a: viewer render · "
             "record: docs/RESEARCH_DIGEST.md · registry: docs/FIGURES.md",
             fontsize=5.8, color=PAL["ink3"], va="bottom")

    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / "hero.png"
    master = CACHE / "hero_rgb.png"  # full colour, not committed
    fig.savefig(master, dpi=170)
    plt.close(fig)
    encode(master, out)
    meta = {"generated": stamp, "commit": head, "uncommitted_changes": dirty,
            "seeds": [SEEDS[0], SEEDS[-1]], "runs_check": rows_check,
            "ppc": {"inside": inside, "of": len(checks), "rows": checks},
            "panel_a": {k: v for k, v in shot.items() if k != "fresh"},
            "ledger": LEDGER.relative_to(ROOT).as_posix(), "ledger_sha256": ledger_hash(),
            "file": out.relative_to(ROOT).as_posix(), "bytes": out.stat().st_size}
    (FIG / "hero.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.2f} MB); {inside} of "
          f"{len(checks)} inside; {rows_check}")
    return 0


def ledger_hash() -> str:
    """The ledger as drawn; tests/test_hero_figure.py compares it with the file now."""
    import hashlib

    return hashlib.sha256(LEDGER.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def encode(master: Path, out: Path) -> None:
    """The committed PNG, kept small: the figure's colours fit a palette once the render's
    gradients are left to dithering."""
    from PIL import Image

    Image.open(master).convert("RGB").quantize(
        colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG,
    ).save(out, optimize=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("stage", choices=["collect", "draw"])
    p.add_argument("--workers", type=int, default=8)
    a = p.parse_args(argv)
    return collect(a.workers) if a.stage == "collect" else draw()


if __name__ == "__main__":
    raise SystemExit(main())
