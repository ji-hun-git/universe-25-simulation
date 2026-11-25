"""The README's moving picture and the repository's preview image, from viewer frames.

1. Record a colony and capture its frames in the viewer (scripts/viewer_serve.py):
     python scripts/viewer_record.py --name universe25_7001 --colony universe25 --seed 7001
     open http://localhost:8765/?rec=universe25_7001&shot=video
   The page saves 480 frames (_output/figures/v_0000.png ...), an orbit over 1,600 days, and the
   population by day (_output/figures/video_series.json).
2. python scripts/readme_media.py
   Writes docs/media/universe25.mp4 (720p, 30 fps), docs/media/universe25.webp (animated, for
   the README),
   docs/media/universe25_day560.jpg (a still at the peak) and docs/media/social_preview.png
   (1280 x 640, for the repository's social preview).

Needs Pillow and an ffmpeg binary (on PATH, or the one imageio-ffmpeg ships).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "_output" / "figures"
OUT = ROOT / "docs" / "media"
PAPER, INK, INK2, STRESS, NEST = "#F4F0E6", "#1A1A1A", "#8A8478", "#8B1E1E", "#2F5D50"
W, H_RENDER, H_STRIP = 1280, 608, 112
CENSUS = ((315, 620), (560, 2200), (736, 2056), (811, 1871), (960, 1650), (1444, 122),
          (1588, 27))
# Calhoun 1973's four phases: (first day, name)
PHASES = ((0, "Phase A · strive"), (105, "Phase B · exploit"), (316, "Phase C · equilibrium"),
          (561, "Phase D · die"))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"])
    for n in names:
        for d in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"),
                  Path("/Library/Fonts")):
            if (d / n).is_file():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size)


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def strip(day: int, n: int, days: list[int], ns: list[int], f_big, f_mid, f_small) -> Image.Image:
    img = Image.new("RGB", (W, H_STRIP), PAPER)
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (W, 0)], fill="#DDD6C8", width=1)
    phase = [p for start, p in PHASES if day >= start][-1]
    d.text((28, 14), f"Day {day:,}", font=f_big, fill=INK)
    d.text((28, 62), f"{n:,} mice", font=f_mid, fill=INK)
    d.text((190, 66), phase, font=f_small, fill=INK2)
    # the population so far, against Calhoun's censuses
    x0, x1, y0, y1 = 470, W - 28, 16, H_STRIP - 22
    top = 2700.0
    sx = lambda t: x0 + (x1 - x0) * t / 1600.0  # noqa: E731
    sy = lambda v: y1 - (y1 - y0) * v / top  # noqa: E731
    d.line([(x0, y1), (x1, y1)], fill="#CFC7B6", width=1)
    for t in (0, 400, 800, 1200, 1600):
        d.text((sx(t) - 8, y1 + 4), f"{t}", font=f_small, fill=INK2)
    pts = [(sx(t), sy(v)) for t, v in zip(days, ns) if t <= day]
    if len(pts) > 1:
        d.line(pts, fill=INK, width=2)
    for t, v in CENSUS:
        r = 4
        filled = t <= day
        d.ellipse([sx(t) - r, sy(v) - r, sx(t) + r, sy(v) + r],
                  fill=STRESS if filled else PAPER, outline=STRESS, width=2)
    d.text((x1 - 236, y0 - 6), "simulated", font=f_small, fill=INK)
    d.line([(x1 - 258, y0 + 3), (x1 - 242, y0 + 3)], fill=INK, width=2)
    d.ellipse([x1 - 150 - 4, y0 + 3 - 4, x1 - 150 + 4, y0 + 3 + 4], fill=STRESS)
    d.text((x1 - 140, y0 - 6), "Calhoun's census", font=f_small, fill=INK)
    return img


def main() -> int:
    series = json.loads((SRC / "video_series.json").read_text(encoding="utf-8"))
    days, ns = series["days"], series["ns"]
    n_of = dict(zip(days, ns))
    frames = sorted(SRC.glob("v_[0-9][0-9][0-9][0-9].png"))
    if not frames:
        print("no frames: capture them first (see the docstring)")
        return 1
    f_big, f_mid, f_small = font(34, True), font(19), font(14)
    OUT.mkdir(parents=True, exist_ok=True)
    last = days[-1]
    tmp = Path(tempfile.mkdtemp(prefix="u25media_"))
    for k, fp in enumerate(frames):
        day = round(k / (len(frames) - 1) * last)
        render = Image.open(fp).convert("RGB").resize((W, H_RENDER), Image.LANCZOS)
        frame = Image.new("RGB", (W, H_RENDER + H_STRIP), PAPER)
        frame.paste(render, (0, 0))
        frame.paste(strip(day, n_of.get(day, 0), days, ns, f_big, f_mid, f_small), (0, H_RENDER))
        frame.save(tmp / f"f_{k:04d}.png")
    ff = ffmpeg()
    mp4 = OUT / "universe25.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", "30", "-i",
                    str(tmp / "f_%04d.png"), "-c:v", "libx264", "-preset", "slow", "-crf", "27",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
    # the README's moving picture: an animated WebP (an orbiting camera changes every pixel, so a
    # GIF of the same length is three times the size), every 4th frame at 10 fps, 720 px wide
    webp = OUT / "universe25.webp"
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(mp4), "-vf",
                    "select='not(mod(n\\,4))',setpts=N/10/TB,scale=720:-1:flags=lanczos",
                    "-r", "10", "-c:v", "libwebp_anim", "-quality", "60",
                    "-compression_level", "6", "-loop", "0", str(webp)], check=True)
    peak = SRC / "vtest_560.png"  # the hero angle at day 560, 1600 x 900
    if peak.is_file():
        Image.open(peak).convert("RGB").save(OUT / "universe25_day560.jpg", quality=86,
                                             optimize=True, progressive=True)
        social(Image.open(peak).convert("RGB"))
    shutil.rmtree(tmp, ignore_errors=True)
    for p in sorted(OUT.iterdir()):
        print(f"{p.relative_to(ROOT)}  {p.stat().st_size / 1e6:.1f} MB")
    return 0


def social(still: Image.Image) -> None:
    """1280 x 640: the pen at its peak, with the name and one line, on paper."""
    img = Image.new("RGB", (1280, 640), PAPER)
    pic = still.resize((1067, 600), Image.LANCZOS).crop((180, 0, 1067, 600))
    img.paste(pic, (1280 - pic.width, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 420, 640], fill=PAPER)
    d.text((44, 170), "Universe 25", font=font(54, True), fill=INK)
    d.text((46, 244), "Calhoun's mouse colony,", font=font(26), fill=INK)
    d.text((46, 278), "simulated mouse by mouse", font=font(26), fill=INK)
    d.line([(46, 336), (120, 336)], fill=STRESS, width=3)
    d.text((46, 356), "agent-based model · Python", font=font(19), fill=INK2)
    d.text((46, 384), "fitted to the 1968–1973 record", font=font(19), fill=INK2)
    img.save(OUT / "social_preview.png", optimize=True)


if __name__ == "__main__":
    sys.exit(main())
