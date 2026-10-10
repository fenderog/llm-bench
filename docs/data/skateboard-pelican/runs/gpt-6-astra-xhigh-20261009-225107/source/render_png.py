#!/usr/bin/env python3
"""Export the hand-drawn SVG as a PNG using macOS Quick Look and ffmpeg.

Quick Look uses a square SVG viewport. Render into a temporary square canvas,
then crop only the extra bottom margin. No artwork is cropped or stretched.
All temporary files are created beside this script and removed automatically.
"""
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SVG = ROOT / "output" / "coast-and-roll.svg"
PNG = ROOT / "output" / "coast-and-roll.png"
SIZE = 1800


def main():
    artwork = SVG.read_text(encoding="utf-8")
    ET.fromstring(artwork)  # Check that the source is well-formed XML.
    original = 'width="1400" height="1120" viewBox="0 0 1400 1120"'
    square = 'width="1400" height="1400" viewBox="0 0 1400 1400"'
    assert artwork.count(original) == 1
    with tempfile.TemporaryDirectory(prefix=".render-", dir=ROOT) as work:
        work = Path(work)
        source = work / "square.svg"
        source.write_text(artwork.replace(original, square), encoding="utf-8")
        subprocess.run(
            ["qlmanage", "-t", "-s", str(SIZE), "-o", str(work), str(source)],
            check=True, stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(work / "square.svg.png"),
             "-vf", f"crop={SIZE}:{SIZE * 1120 // 1400}:0:0,format=rgb24",
             "-frames:v", "1", "-update", "1", str(PNG)],
            check=True,
        )
    assert PNG.stat().st_size < 2_000_000
    print(f"Created {PNG.relative_to(ROOT)} ({SIZE} × {SIZE * 1120 // 1400})")


if __name__ == "__main__":
    main()
