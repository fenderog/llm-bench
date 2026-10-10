#!/usr/bin/env python3
"""Render pelican_skateboard.svg to pelican_skateboard.png.

Pipeline:
1. Build a temporary square (900x900) version of the SVG by padding the
   sky/sand background rects, because qlmanage fill-crops non-square art.
2. Render it with macOS Quick Look (qlmanage), which draws a white document
   border around the artwork.
3. Find the artwork bounding box from raw pixels (via ffmpeg -> rawvideo)
   and crop the border away.
4. Crop the square artwork back down to the original 900x650 scene area.
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).parent / "output"
SRC = OUT / "pelican_skateboard.svg"
DST = OUT / "pelican_skateboard.png"
TMP = OUT / "_padded_square.svg"
SIZE = "1800"

svg = SRC.read_text()
svg = svg.replace('viewBox="0 0 900 650"', 'viewBox="0 -125 900 900"', 1)
svg = svg.replace(
    '<rect width="900" height="462" fill="url(#sky)"/>',
    '<rect y="-125" width="900" height="587" fill="url(#sky)"/>',
    1,
)
svg = svg.replace(
    '<rect y="460" width="900" height="190" fill="url(#sand)"/>',
    '<rect y="460" width="900" height="315" fill="url(#sand)"/>',
    1,
)
TMP.write_text(svg)

try:
    subprocess.run(
        ["qlmanage", "-t", "-s", SIZE, "-o", str(OUT), str(TMP)],
        check=True, capture_output=True, text=True,
    )
    thumb = OUT / (TMP.name + ".png")

    # Read raw RGBA pixels through ffmpeg.
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(thumb)],
        check=True, capture_output=True, text=True,
    )
    w, h = (int(v) for v in probe.stdout.strip().split(","))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(thumb),
         "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        check=True, capture_output=True,
    ).stdout

    # Bounding box of pixels that are not near-white.
    min_x, min_y, max_x, max_y = w, h, -1, -1
    row_len = w * 4
    for y in range(h):
        row = raw[y * row_len:(y + 1) * row_len]
        for x in range(w):
            i = x * 4
            r, g, b = row[i], row[i + 1], row[i + 2]
            if r < 245 or g < 245 or b < 245:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
    if max_x < 0:
        raise RuntimeError("no artwork found in thumbnail")

    # Nudge inward a couple of px to avoid any anti-aliased border fringe.
    pad = 3
    bx, by = min_x + pad, min_y + pad
    bw, bh = (max_x - min_x + 1) - 2 * pad, (max_y - min_y + 1) - 2 * pad

    # The square artwork maps to viewBox 900x900; the original scene is the
    # band y in [125, 775) of that square.
    sy = by + round(bh * 125 / 900)
    sh = round(bh * 650 / 900)

    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(thumb),
         "-vf", f"crop={bw}:{sh}:{bx}:{sy}", str(DST)],
        check=True,
    )
    thumb.unlink()
finally:
    TMP.unlink(missing_ok=True)

print(f"wrote {DST}")
