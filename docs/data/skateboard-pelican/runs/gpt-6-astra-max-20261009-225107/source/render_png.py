#!/usr/bin/env python3
"""Render the original SVG to a PNG using Quick Look and ffmpeg.

Quick Look gives SVGs a square viewport. A temporary square copy followed by
an exact top-left crop preserves the illustration's intended aspect ratio.
No packages, external images, or network access are used.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SVG = ROOT / "output" / "pelican-cruiser.svg"
PNG = SVG.with_suffix(".png")
SCALE = 1.5


def main():
    source = SVG.read_text(encoding="utf-8")
    element = ET.fromstring(source)
    _, _, width, height = map(float, element.attrib["viewBox"].split())
    side = int(max(width, height))
    opening, rest = source.split(">", 1)
    opening = re.sub(r'\bwidth="[^"]+"', 'width="%s"' % side, opening)
    opening = re.sub(r'\bheight="[^"]+"', 'height="%s"' % side, opening)
    opening = re.sub(r'\bviewBox="[^"]+"',
                     'viewBox="0 0 %s %s"' % (side, side), opening)
    with tempfile.TemporaryDirectory(prefix=".render-", dir=ROOT) as temp:
        directory = Path(temp)
        square = directory / "square.svg"
        square.write_text(opening + ">" + rest, encoding="utf-8")
        subprocess.run([
            "qlmanage", "-t", "-s", str(round(side * SCALE)),
            "-o", str(directory), str(square)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(directory / "square.svg.png"), "-vf",
            "crop=%s:%s:0:0" % (round(width * SCALE), round(height * SCALE)),
            "-frames:v", "1", "-update", "1", "-compression_level", "9",
            str(PNG)
        ], check=True)
    if PNG.stat().st_size >= 2_000_000:
        raise RuntimeError("PNG exceeds the delivery size limit")
    print("Created %s (%s bytes)" % (PNG.relative_to(ROOT), PNG.stat().st_size))


if __name__ == "__main__":
    main()
