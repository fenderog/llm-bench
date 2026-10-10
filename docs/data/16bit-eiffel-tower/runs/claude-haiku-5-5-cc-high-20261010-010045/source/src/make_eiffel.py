#!/usr/bin/env python3
"""Render an SNES-style Eiffel Tower at 256x224 and save it as an indexed PNG.

Standard library only. Enforces the SNES limits: at most 128 colors total,
and at most 16 colors in every 8x8 tile.
"""

import math
import os
import random
import struct
import zlib

W, H = 256, 224
TILE = 8
MAX_COLORS = 128
MAX_TILE_COLORS = 16

# Ordered palette: the position of each entry is its PNG index.
COLORS = {
    # sunset sky, deep navy at the top to pale peach at the horizon
    "s0": (11, 20, 56),
    "s1": (24, 34, 96),
    "s2": (52, 52, 128),
    "s3": (100, 70, 160),
    "s4": (170, 90, 166),
    "s5": (226, 112, 150),
    "s6": (255, 150, 122),
    "s7": (255, 192, 138),
    "s8": (255, 230, 168),
    # stars, clouds, sun
    "star": (255, 248, 200),
    "white": (255, 255, 255),
    "cloud": (246, 240, 252),
    "cloud_p": (255, 214, 232),
    "cloud_s": (184, 138, 200),
    "sun": (255, 240, 190),
    "halo": (255, 214, 150),
    # hills, trees, grass
    "hill_f": (74, 58, 126),
    "hill_f_hi": (112, 90, 164),
    "hill_n": (38, 92, 88),
    "hill_n_hi": (66, 134, 110),
    "tree": (22, 66, 44),
    "tree_hi": (38, 96, 60),
    "grass_hi": (120, 200, 90),
    "grass": (64, 160, 80),
    "grass_alt": (76, 172, 88),
    "grass_dk": (34, 110, 56),
    "shade": (26, 70, 40),
    # tower, bronze-brown ironwork
    "t_out": (30, 14, 8),
    "t_dk": (74, 40, 22),
    "t_mid": (122, 72, 38),
    "t_lt": (176, 112, 64),
    "t_hi": (222, 164, 104),
    "t_glint": (255, 226, 160),
}
NAMES = list(COLORS.keys())
INDEX = {name: i for i, name in enumerate(NAMES)}

BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]
SKY = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
SKY_BAND = 20  # rows per solid sky band; the last 4 rows of each band dither

CX = 128  # tower centre column
TOP, BASE = 34, 196  # tower body top and base rows
SPIRE_TOP = 12
F1, F2, F3 = 162, 128, 58  # platform rows: first floor, second floor, top


canvas = [[None] * W for _ in range(H)]


def put(x, y, name):
    if 0 <= x < W and 0 <= y < H:
        canvas[y][x] = name


def sky_background():
    for y in range(H):
        k = min(y // SKY_BAND, len(SKY) - 1)
        r = y % SKY_BAND
        for x in range(W):
            name = SKY[k]
            if r >= SKY_BAND - 4 and k + 1 < len(SKY):
                frac = (r - (SKY_BAND - 4) + 1) / 5
                if frac > (BAYER4[y % 4][x % 4] + 0.5) / 16:
                    name = SKY[k + 1]
            canvas[y][x] = name


def stars():
    rng = random.Random(1986)
    for _ in range(60):
        x = rng.randrange(2, W - 2)
        y = rng.randrange(2, 110)
        put(x, y, "star" if rng.random() < 0.6 else "white")
    # a few four-point sparkles
    for x, y in [(22, 20), (230, 36), (70, 44), (190, 14), (104, 70), (240, 96)]:
        put(x, y, "white")
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            put(x + dx, y + dy, "star")


def sun():
    sx, sy = 204, 158
    for y in range(sy - 14, sy + 15):
        for x in range(sx - 14, sx + 15):
            d = math.hypot(x - sx, y - sy)
            if d <= 8:
                put(x, y, "sun")
            elif d <= 13 and (x + y) % 2 == 0:
                put(x, y, "halo")


def cloud(circles, rects):
    pts = set()
    for cx, cy, r in circles:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    pts.add((x, y))
    for x0, x1, y0, y1 in rects:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                pts.add((x, y))
    for x, y in pts:
        if (x, y - 1) not in pts:
            name = "white"
        elif (x, y + 1) not in pts:
            name = "cloud_s"
        elif (x, y + 2) not in pts:
            name = "cloud_p"
        else:
            name = "cloud"
        put(x, y, name)


def clouds():
    cloud([(40, 96, 7), (56, 88, 11), (72, 96, 8), (56, 100, 7)], [(34, 76, 101, 103)])
    cloud([(192, 128, 6), (206, 122, 9), (220, 128, 7), (212, 132, 6)], [(188, 226, 131, 133)])
    cloud([(218, 52, 4), (226, 49, 5), (234, 53, 3)], [(214, 238, 56, 57)])


def hills():
    for x in range(W):
        top_far = round(172 + 4 * math.sin(x / 19) + 2.5 * math.sin(x / 7.3 + 1.3))
        for y in range(top_far, H):
            put(x, y, "hill_f_hi" if y == top_far else "hill_f")
    for x in range(W):
        top_near = round(186 + 3 * math.sin(x / 13 + 2) + 1.5 * math.sin(x / 5.1))
        for y in range(top_near, H):
            put(x, y, "hill_n_hi" if y == top_near else "hill_n")


def trees():
    for cx, cy, r in [(14, 186, 8), (28, 188, 6), (40, 190, 5), (226, 186, 8), (240, 188, 6), (214, 190, 5)]:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    top_edge = (x - cx) ** 2 + (y - 1 - cy) ** 2 > r * r
                    put(x, y, "tree_hi" if top_edge else "tree")


def grass():
    for y in range(194, H):
        for x in range(W):
            if y == 194:
                name = "grass_hi"
            elif (x * 7 + y * 3) % 11 == 0:
                name = "grass_dk"
            elif (x + y) % 5 == 0 and y % 2 == 1:
                name = "grass_alt"
            else:
                name = "grass"
            put(x, y, name)


def tower_shadow():
    for y in range(194, 200):
        for x in range(CX - 38, CX + 39):
            if ((x - CX) / 38) ** 2 + ((y - 196) / 3.5) ** 2 <= 1:
                put(x, y, "shade")


def tt(y):
    return (y - TOP) / (BASE - TOP)


def outer(y):
    # Half-width of the tower silhouette: narrow at the top, flaring to the base.
    return 2 + 32 * tt(y) ** 1.7


def thick(y):
    # Thickness of the four legs measured horizontally.
    return 3 + 2.5 * tt(y)


def lattice(dx, y):
    return (dx + y) % 4 == 0 or (dx - y) % 4 == 0


def tower_body():
    for y in range(TOP, BASE + 1):
        wo = outer(y)
        wi = wo - thick(y)
        wr = round(wo)
        for dx in range(-wr - 1, wr + 2):
            a = abs(dx)
            x = CX + dx
            if a == wr + 1:
                put(x, y, "t_out")
                continue
            if a > wi:
                # leg: lit from the left, shaded on the right, with a hatch pattern
                if a >= wr - 1 and dx < 0:
                    name = "t_lt"
                elif a >= wr - 1 and dx > 0:
                    name = "t_dk"
                elif (x + 2 * y) % 7 == 0:
                    name = "t_dk"
                else:
                    name = "t_mid"
                put(x, y, name)
            elif y < F1 - 1:
                # open lattice above the first floor
                if lattice(dx, y):
                    put(x, y, "t_mid")
            else:
                # the arch under the first floor
                arch_y = BASE - 30 * (1 - (min(a, 28) / 28) ** 2)
                if abs(y - arch_y) <= 1:
                    put(x, y, "t_mid")
                elif y < arch_y - 1 and lattice(dx, y):
                    put(x, y, "t_mid")


def platform(y, half):
    for dx in range(-half, half + 1):
        x = CX + dx
        put(x, y, "t_mid")
        put(x, y + 1, "t_dk")
        if dx % 2 == 0:
            put(x, y - 1, "t_lt")
    put(CX - half - 1, y, "t_out")
    put(CX + half + 1, y, "t_out")


def top_cabin():
    for y in range(F3 - 6, F3 - 1):
        for dx in range(-2, 3):
            name = "t_dk" if abs(dx) == 2 else "t_mid"
            if y == F3 - 6:
                name = "t_lt"
            put(CX + dx, y, name)


def spire():
    for y in range(SPIRE_TOP, TOP):
        if y < 14:
            put(CX, y, "t_glint")
            continue
        w = 0 if y < 22 else 1
        for dx in range(-w, w + 1):
            name = "t_hi" if dx == 0 else ("t_mid" if dx < 0 else "t_dk")
            put(CX + dx, y, name)


def tower():
    spire()
    tower_body()
    platform(F1, 28)
    platform(F2, 18)
    platform(F3, 6)
    top_cabin()
    for x, y in [(CX - 17, 92), (CX + 12, 150), (CX - 6, 110)]:
        put(x, y, "t_glint")


def tile_check():
    for ty in range(0, H, TILE):
        for tx in range(0, W, TILE):
            used = {canvas[y][x] for y in range(ty, ty + TILE) for x in range(tx, tx + TILE)}
            assert len(used) <= MAX_TILE_COLORS, (tx, ty, len(used))


def write_png(path, width, height, rows, palette_rgb):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0)  # 8-bit indexed
    plte = bytes(c for rgb in palette_rgb for c in rgb)
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"PLTE", plte)
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)


def main():
    sky_background()
    stars()
    sun()
    clouds()
    hills()
    trees()
    grass()
    tower_shadow()
    tower()

    used = {name for row in canvas for name in row}
    assert None not in used, "every pixel must be painted"
    assert len(used) <= MAX_COLORS, len(used)
    tile_check()

    rows = [[INDEX[name] for name in row] for row in canvas]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "eiffel_tower_snes.png")
    write_png(out_path, W, H, rows, [COLORS[n] for n in NAMES])
    print(f"wrote {out_path}: {W}x{H}, {len(used)} colors used")


if __name__ == "__main__":
    main()
