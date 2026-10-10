#!/usr/bin/env python3
"""Pixel-art Eiffel Tower in 16-bit (RGB565) colour, saved as a JPEG.

The scene is painted on a 160x200 grid. Each pixel is snapped to RGB565
(5 bits red, 6 green, 5 blue: 65,536 colours) and the sky gradient is
ordered-dithered first, as 16-bit hardware did. The grid is then scaled up
4x with nearest-neighbour and piped to ffmpeg, which writes the JPEG.
Only the Python standard library is used.

Usage: python3 make_eiffel_16bit.py OUTPUT.jpg
"""

import math
import random
import subprocess
import sys

W, H = 160, 200          # logical pixel grid
SCALE = 4                # each logical pixel becomes a 4x4 block

CX = W / 2               # centre line of the tower
TOP = 20                 # y of the spire tip
GROUND = 168             # y where the feet meet the lawn
HORIZON = 158            # top of the lawn, below the distant treeline
RIVER = 184              # top edge of the river strip
SUN = (94, 96, 12)       # sun centre x, centre y, radius (sits behind the tower)
GLOW = 14                # width of the sun's glow in the sky

# Tower half-width at height t (0 = feet, 1 = spire tip)
PROFILE = [(0.00, 28.0), (0.06, 23.0), (0.17, 16.0), (0.30, 11.0),
           (0.45, 8.0), (0.60, 6.5), (0.84, 4.2), (0.90, 3.0),
           (0.96, 1.5), (1.00, 0.5)]
ARCH_X, ARCH_Y = 20.0, 28.9                     # arch under the legs: half-width, height
PLATFORMS = [(0.17, 19), (0.35, 12), (0.84, 6)]  # (height t, half-width)

# Palette (8-bit values; every one is snapped to RGB565 when drawn)
SKY = [(0.00, (24, 30, 84)), (0.45, (92, 60, 132)), (0.75, (212, 104, 134)),
       (0.90, (248, 156, 120)), (1.00, (255, 206, 150))]
GLOW_COL = (255, 214, 140)
SUN_CORE = (255, 244, 200)
SUN_RIM = (255, 200, 120)
STAR = (210, 220, 255)
CLOUD_LIT = (170, 140, 200)
CLOUD_SHADE = (118, 96, 168)
TREE = (30, 56, 60)
LAWN_FAR = (76, 116, 82)
LAWN = (46, 88, 58)
LAWN_STRIPE = (56, 100, 66)
WATER = (56, 104, 162)
WATER_GLINT = (132, 178, 222)
IRON = (96, 58, 50)
IRON_HATCH = (124, 76, 62)
IRON_RIM = (250, 160, 110)

CLOUDS = [  # each cloud is a list of ellipses (cx, cy, rx, ry)
    [(26, 60, 13, 3.5), (37, 56, 9, 4), (17, 62, 8, 2.5)],
    [(126, 48, 16, 3.5), (139, 44, 10, 4), (116, 50, 8, 2.5)],
    [(56, 30, 16, 3), (68, 27, 10, 3.5), (46, 33, 8, 2)],
]

BAYER = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]
# One 5/6/5 quantisation step, in 8-bit levels
STEP = (255 / 31, 255 / 63, 255 / 31)


def sample(stops, t):
    """Piecewise-linear lookup of t in a list of (position, value) stops."""
    if t <= stops[0][0]:
        return stops[0][1]
    for (p0, v0), (p1, v1) in zip(stops, stops[1:]):
        if t <= p1:
            k = (t - p0) / (p1 - p0)
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * k for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * k
    return stops[-1][1]


def _level(v, top):
    return min(top, max(0, round(v * top / 255)))


def snap565(rgb, dither=0.0):
    """Quantise an 8-bit colour to RGB565, then expand it back to 8 bits.

    dither is an offset in -0.5..0.5 quantisation steps, used to break up banding.
    """
    r, g, b = rgb
    r5 = _level(r + dither * STEP[0], 31)
    g6 = _level(g + dither * STEP[1], 63)
    b5 = _level(b + dither * STEP[2], 31)
    # Expand by repeating the top bits, as real 16-bit video output does
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def put(img, x, y, colour):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = colour


def draw_sky(img):
    for y in range(HORIZON):
        base = sample(SKY, y / HORIZON)
        for x in range(W):
            d = math.hypot(x + 0.5 - SUN[0], y + 0.5 - SUN[1])
            k = min(1.0, max(0.0, 1 - (d - SUN[2]) / GLOW)) ** 2 * 0.7
            rgb = tuple(c + (g - c) * k for c, g in zip(base, GLOW_COL))
            threshold = (BAYER[y % 4][x % 4] + 0.5) / 16 - 0.5
            img[y][x] = snap565(rgb, threshold)


def draw_stars(img):
    rng = random.Random(1889)  # fixed seed: the same starfield every run
    for _ in range(18):
        put(img, rng.randrange(W), rng.randrange(0, 50), snap565(STAR))


def draw_sun(img):
    sx, sy, r = SUN
    for y in range(int(sy - r) - 1, int(sy + r) + 2):
        for x in range(int(sx - r) - 1, int(sx + r) + 2):
            d = math.hypot(x + 0.5 - sx, y + 0.5 - sy)
            if d < r - 3:
                put(img, x, y, snap565(SUN_CORE))
            elif d < r:
                put(img, x, y, snap565(SUN_RIM))


def draw_clouds(img):
    for y in range(HORIZON):
        for x in range(W):
            for blobs in CLOUDS:
                for cx, cy, rx, ry in blobs:
                    if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                        colour = CLOUD_LIT if y + 0.5 < cy else CLOUD_SHADE
                        put(img, x, y, snap565(colour))


def draw_treeline(img):
    for x in range(W):
        h = 3 + int(2 * (1 + math.sin(x * 0.37))) + int(2 * (1 + math.sin(x * 0.91 + 2)))
        for y in range(HORIZON - h, HORIZON):
            put(img, x, y, snap565(TREE))


def draw_ground(img):
    for y in range(HORIZON, H):
        for x in range(W):
            if y >= RIVER:
                colour = WATER_GLINT if (x * 5 + y * 7) % 19 == 0 else WATER
            elif y < HORIZON + 6:
                colour = LAWN_FAR
            else:
                colour = LAWN_STRIPE if (y // 4) % 2 else LAWN
            put(img, x, y, snap565(colour))


def tower_mask():
    """True where the ironwork covers a pixel (silhouette minus the arch)."""
    mask = [[False] * W for _ in range(H)]
    for y in range(TOP, GROUND + 1):
        t = (GROUND - (y + 0.5)) / (GROUND - TOP)
        half = sample(PROFILE, t)
        dy = GROUND - y
        for x in range(W):
            d = abs(x + 0.5 - CX)
            under_arch = dy >= 0 and (d / ARCH_X) ** 2 + (dy / ARCH_Y) ** 2 < 1
            mask[y][x] = d <= half and not under_arch
    return mask


def draw_tower(img):
    mask = tower_mask()
    for y in range(H):
        for x in range(W):
            if not mask[y][x]:
                continue
            # Pixels on the outline get a warm rim light (the sun is behind the tower)
            edge = any(not (0 <= x + dx < W and 0 <= y + dy < H) or not mask[y + dy][x + dx]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                colour = IRON_RIM
            elif (x + y) % 5 == 0:
                colour = IRON_HATCH
            else:
                colour = IRON
            img[y][x] = snap565(colour)

    for t, half in PLATFORMS:
        deck = round(GROUND - t * (GROUND - TOP))
        for x in range(W):
            if abs(x + 0.5 - CX) <= half:
                put(img, x, deck - 1, snap565(IRON_RIM))
                put(img, x, deck, snap565(IRON_HATCH))
                put(img, x, deck + 1, snap565(IRON))

    for y in range(12, TOP):  # antenna above the spire
        put(img, int(CX), y, snap565(IRON_RIM))


def render():
    img = [[(0, 0, 0)] * W for _ in range(H)]
    draw_sky(img)
    draw_stars(img)
    draw_sun(img)
    draw_clouds(img)
    draw_treeline(img)
    draw_ground(img)
    draw_tower(img)
    return img


def to_rgb24(img):
    """Scale the grid up SCALE times with nearest-neighbour and pack as RGB bytes."""
    out = bytearray()
    for row in img:
        line = b"".join(bytes(px) * SCALE for px in row)
        out += line * SCALE
    return bytes(out)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: make_eiffel_16bit.py OUTPUT.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * SCALE}x{H * SCALE}", "-i", "-",
         "-frames:v", "1", "-pix_fmt", "yuvj444p", "-q:v", "2", sys.argv[1]],
        input=to_rgb24(render()), check=True)


if __name__ == "__main__":
    main()
