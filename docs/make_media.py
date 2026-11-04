"""Render docs/demo.gif: a terminal animation of a real `python -m retail_pipeline.run`.

    python docs/make_media.py        # needs pillow; the pipeline runs for about a minute
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DOCS = Path(__file__).resolve().parent
COMMAND = "python -m retail_pipeline.run"
BG, FG, DIM = "#0d1117", "#c9d1d9", "#8b949e"
CYAN, GREEN, YELLOW = "#79c0ff", "#3fb950", "#e3b341"
FONT = "/System/Library/Fonts/Menlo.ttc"


def run_pipeline() -> list[str]:
    out = subprocess.run([sys.executable, "-m", "retail_pipeline.run"], capture_output=True, text=True, check=True)
    keep = ("rows:", "  ", "quality", "forecast", "tableau")
    return [l for l in out.stdout.rstrip("\n").split("\n") if l.startswith(keep)]


def colour(line: str) -> str:
    if line.startswith("quality"):
        return GREEN
    if line.startswith(("rows:", "forecast")):
        return CYAN
    if line.startswith("tableau"):
        return DIM
    return YELLOW if line.startswith("  removed") else FG


def make_gif(lines: list[str], path: Path) -> None:
    font = ImageFont.truetype(FONT, 15) if Path(FONT).exists() else ImageFont.load_default(15)
    cw, lh, pad, bar = font.getlength("M"), 21, 18, 34
    w = int((max(len(l) for l in lines) + 8) * cw + 2 * pad)
    h = bar + pad + (len(lines) + 2) * lh + pad

    def frame(n: int, typed: str, cursor: bool) -> Image.Image:
        im = Image.new("RGB", (w, h), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w, bar], fill="#161b22")
        for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
            d.ellipse([14 + 20 * i, 11, 26 + 20 * i, 23], fill=c)
        y = bar + pad
        d.text((pad, y), "$ ", font=font, fill=GREEN)
        d.text((pad + 2 * cw, y), typed + ("█" if cursor else ""), font=font, fill=FG)
        for line in lines[:n]:
            y += lh
            d.text((pad, y), line, font=font, fill=colour(line))
        return im

    frames, durations = [], []
    for i in range(0, len(COMMAND) + 1, 2):
        frames.append(frame(0, COMMAND[:i], True)); durations.append(60)
    frames.append(frame(0, COMMAND, True)); durations.append(500)
    for n in range(1, len(lines) + 1):
        frames.append(frame(n, COMMAND, False))
        durations.append(700 if lines[n - 1].startswith(("rows:", "quality", "forecast", "tableau")) else 180)
    durations[-1] = 6000
    ref = frames[-1].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    pal = [f.quantize(palette=ref, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)


if __name__ == "__main__":
    make_gif(run_pipeline(), DOCS / "demo.gif")
    print("docs/demo.gif", f"{(DOCS / 'demo.gif').stat().st_size / 1024:.0f} KB")
