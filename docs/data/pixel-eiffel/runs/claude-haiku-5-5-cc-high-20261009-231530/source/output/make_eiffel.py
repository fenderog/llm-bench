#!/usr/bin/env python3
"""Draw a 16-bit style pixel-art Eiffel Tower at dusk and save it as a JPG.

The scene is built cell by cell on a small grid. Each cell is coloured in
RGB565 (5-6-5 bits, 65,536 colours) with a 4x4 ordered dither, scaled up with
hard pixel edges, and the raw RGB frame is piped to ffmpeg for JPEG encoding.
Standard library only.
"""
import math
import os
import random
import subprocess

GRID_W, GRID_H = 120, 150          # canvas size in 16-bit "pixels"
SCALE = 5                          # each pixel becomes a 5x5 block
OUT_W, OUT_H = GRID_W * SCALE, GRID_H * SCALE
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eiffel-16bit.jpg")

CX = GRID_W // 2                   # tower centre column
TIP = 6                            # top of the antenna
GROUND = 136                       # ground line
HEIGHT = GROUND - TIP
FLOOR_1 = GROUND - round(0.17 * HEIGHT)   # 57 m of 330 m
FLOOR_2 = GROUND - round(0.35 * HEIGHT)   # 115 m
FLOOR_3 = GROUND - round(0.84 * HEIGHT)   # 276 m
SUN_X, SUN_Y, SUN_R = CX + 30, 92, 8

SKY_STOPS = [
    (0, (14, 22, 60)),
    (40, (40, 50, 120)),
    (70, (110, 70, 140)),
    (100, (210, 110, 140)),
    (125, (250, 160, 110)),
    (GROUND, (255, 200, 130)),
]
CLOUDS = [(20, 30, 15, 3), (100, 50, 13, 3), (28, 72, 11, 2.5)]   # cx, cy, rx, ry
CLOUD_LIT = (226, 140, 170)
CLOUD_SHADE = (150, 80, 130)
STAR = (235, 235, 255)
SUN = (255, 236, 150)
TREE = (28, 61, 44)
GRASS_TOP = (46, 94, 62)
GRASS_BOT = (20, 52, 38)
IRON = (34, 22, 38)
IRON_SHADE = (22, 14, 28)
IRON_LIT = (60, 40, 62)
RIM = (236, 150, 96)

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def sky_at(y):
    for (y0, c0), (y1, c1) in zip(SKY_STOPS, SKY_STOPS[1:]):
        if y0 <= y <= y1:
            return lerp(c0, c1, (y - y0) / (y1 - y0))
    return SKY_STOPS[-1][1]


def tree_top(x):
    return GROUND - int(2 + 3 * abs(math.sin(x * 0.23)) + 2 * abs(math.sin(x * 0.61 + 1)))


def half_width(y):
    """Tower half-width at row y: the four legs splay out towards the ground."""
    s = (y - TIP) / HEIGHT
    return 1.5 + 34 * s * s


def spire_half(y):
    return 0.6 + 2.2 * ((y - TIP) / (FLOOR_3 - TIP)) ** 1.2


def background(x, y, stars):
    if y >= GROUND:
        return lerp(GRASS_TOP, GRASS_BOT, (y - GROUND) / (GRID_H - 1 - GROUND))
    if y >= tree_top(x):
        return TREE
    for cx, cy, rx, ry in CLOUDS:
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
            return CLOUD_LIT if y < cy + ry / 2 else CLOUD_SHADE
    if (x, y) in stars:
        return STAR
    d = math.hypot(x - SUN_X, y - SUN_Y)
    if d <= SUN_R:
        return SUN
    c = sky_at(y)
    if d <= 2 * SUN_R:
        c = lerp(c, SUN, 0.35 * (1 - (d - SUN_R) / SUN_R))
    return c


def tower(x, y):
    """Iron colour for a tower pixel, or None where the background shows through."""
    dx = x - CX
    if y < TIP or y >= GROUND:
        return None
    if y in (FLOOR_1, FLOOR_2, FLOOR_3) and abs(dx) <= half_width(y) + 2.5:
        return IRON_LIT
    if (dx / 13) ** 2 + ((GROUND - y) / 20) ** 2 < 1:
        return None                                  # arch under the first floor
    half = spire_half(y) if y < FLOOR_3 else half_width(y)
    if abs(dx) > half:
        return None
    if abs(dx) >= 3 and ((y + dx) % 8 == 0 or (y - dx) % 8 == 0):
        return None                                  # lattice bracing holes
    if dx < 0 and abs(dx) > half - 1.2:
        return RIM                                   # sunlit left edge
    return IRON if dx < 0 else IRON_SHADE


def render():
    rnd = random.Random(7)
    stars = {(rnd.randrange(GRID_W), rnd.randrange(1, 40)) for _ in range(30)}
    rows = []
    for y in range(GRID_H):
        rows.append([tower(x, y) or background(x, y, stars) for x in range(GRID_W)])
    return rows


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def to_rgb565(c, x, y):
    """Quantise to RGB565 with a 4x4 ordered dither, then expand back to 8 bits."""
    t = (BAYER[y % 4][x % 4] + 0.5) / 16 - 0.5
    r5 = clamp(int(c[0] + t * 8) >> 3, 0, 31)
    g6 = clamp(int(c[1] + t * 4) >> 2, 0, 63)
    b5 = clamp(int(c[2] + t * 8) >> 3, 0, 31)
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def main():
    rows = render()
    raw = bytearray()
    for y, row in enumerate(rows):
        line = bytearray()
        for x, c in enumerate(row):
            line += bytes(to_rgb565(c, x, y)) * SCALE
        raw += line * SCALE
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}", "-i", "-",
         "-frames:v", "1", "-q:v", "2", OUT_PATH],
        input=bytes(raw), check=True)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
