#!/usr/bin/env python3
"""Render a 16-colour pixel-art Eiffel Tower and convert it to JPG via ffmpeg.

The canvas is 128x128 pixels, drawn from the 16-colour PICO-8 style palette
below, then scaled 4x with nearest-neighbour so the pixels stay crisp.
The PPM stream is piped straight into ffmpeg, so no intermediate file is written.
"""
import math
import os
import subprocess

PAL = [
    (0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81),
    (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
    (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54),
    (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170),
]

W, H = 128, 128
SCALE = 4
GROUND_Y = 118
TOP_Y = 12

# 4x4 Bayer matrix for ordered dithering between two palette colours
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# Half-width of the tower silhouette as (y, half-width) control points
HALF_W = [(12, 1), (20, 3), (38, 7), (58, 11), (62, 12), (90, 18), (118, 30)]

CLOUDS = [(20, 30, 10, 4), (106, 56, 12, 4), (30, 74, 8, 3)]


def mix(a, b, t, x, y):
    """Dither between palette index a and b; t in 0..1 is the share of b."""
    thr = (BAYER[y % 4][x % 4] + 0.5) / 16
    return b if min(max(t, 0.0), 1.0) > thr else a


def sky(x, y):
    if y < 50:
        return mix(1, 12, y / 50, x, y)
    if y < 90:
        return mix(12, 6, (y - 50) / 40, x, y)
    return mix(6, 15, (y - 90) / 28, x, y)


def ground(x, y):
    if y == GROUND_Y:
        return 11
    if (x * 3 + y * 5) % 11 == 0:
        return 11
    return 3


def half_width(y):
    for (y0, w0), (y1, w1) in zip(HALF_W, HALF_W[1:]):
        if y0 <= y <= y1:
            return w0 + (w1 - w0) * (y - y0) / (y1 - y0)
    return 0.0


def tower(x, y):
    """Palette index for the tower, or None where the tower is not drawn."""
    if y < TOP_Y:
        return 5 if x == 64 else None  # antenna mast
    if y >= GROUND_Y:
        return None
    d = abs(x - 64)
    w = half_width(y)
    if d > w:
        return None
    # Platforms
    if 56 <= y <= 59 and d <= w + 2:
        return 0 if y == 59 else 5
    if 36 <= y <= 38 and d <= w + 1:
        return 0 if y == 38 else 5
    # Arch under the first level: half-ellipse centred on the ground
    if y >= 92 and (d / 18) ** 2 + ((y - GROUND_Y) / 25) ** 2 < 1:
        return None
    # Dark outline along the silhouette edge
    if d >= w - 0.9:
        return 0
    # Diagonal lattice holes give the open-iron look
    if (x + y) % 5 == 0 or (x - y) % 5 == 0:
        return None
    return 5


def sun(x, y):
    d = math.hypot(x - 100, y - 18)
    if d <= 6:
        return 10
    if d <= 7.5:
        return 9
    return None


def cloud(x, y):
    for cx, cy, rx, ry in CLOUDS:
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
            return 6 if y > cy + ry * 0.3 else 7
    return None


def pixel(x, y):
    if y >= GROUND_Y:
        return ground(x, y)
    t = tower(x, y)
    if t is not None:
        return t
    s = sun(x, y)
    if s is not None:
        return s
    c = cloud(x, y)
    if c is not None:
        return c
    return sky(x, y)


def main():
    rows = [[pixel(x, y) for x in range(W)] for y in range(H)]

    out = bytearray()
    for row in rows:
        line = bytearray()
        for idx in row:
            line += bytes(PAL[idx]) * SCALE
        for _ in range(SCALE):
            out += line

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "eiffel_tower_16color.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W * SCALE}x{H * SCALE}", "-i", "-",
         "-frames:v", "1", "-q:v", "2", out_path],
        input=bytes(out), check=True,
    )
    print(out_path)


if __name__ == "__main__":
    main()
