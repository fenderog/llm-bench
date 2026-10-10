"""Render an SNES-style Eiffel Tower scene at native 256x224 and save it as PNG.

Standard library only. Enforces the SNES-style limits: at most 128 colors
overall and at most 16 colors per 8x8 tile.
"""
import math
import os
import random
import struct
import zlib

W, H = 256, 224
GROUND_Y = 196


def hx(s):
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


canvas = [[hx("000000")] * W for _ in range(H)]


def put(x, y, col):
    if 0 <= x < W and 0 <= y < H:
        canvas[y][x] = col


# --- Sky: vertical gradient quantized to 4-px bands (classic SNES banding) ---
SKY_STOPS = [
    (0, "0b0f3a"), (50, "1d2670"), (90, "4a3190"),
    (125, "9a4590"), (150, "d8608a"), (170, "f7906a"), (196, "ffc68a"),
]


def sky_color(y):
    for (a, ca), (b, cb) in zip(SKY_STOPS, SKY_STOPS[1:]):
        if a <= y <= b:
            t = (y - a) / (b - a)
            return tuple(round(p + (q - p) * t) for p, q in zip(hx(ca), hx(cb)))
    return hx(SKY_STOPS[-1][1])


for y in range(GROUND_Y):
    col = sky_color((y // 4) * 4)
    for x in range(W):
        put(x, y, col)

# --- Stars in the upper sky ---
rnd = random.Random(7)
for _ in range(70):
    x, y = rnd.randrange(W), rnd.randrange(0, 80)
    put(x, y, hx("ffffff") if rnd.random() < 0.6 else hx("ffe9a0"))

# --- Setting sun with flat banded rings ---
SUN_CX, SUN_CY = 128, 112
for y in range(SUN_CY - 31, SUN_CY + 32):
    for x in range(SUN_CX - 31, SUN_CX + 32):
        d = math.hypot(x - SUN_CX, y - SUN_CY)
        if d <= 16:
            put(x, y, hx("fff6b0"))
        elif d <= 22:
            put(x, y, hx("ffe070"))
        elif d <= 26:
            put(x, y, hx("ffb050"))
        elif d <= 30:
            put(x, y, hx("f08a50"))

# --- Clouds: unions of circles, outlined, with two-tone shading ---
CLOUD_FILL = hx("ffffff")
CLOUD_SHADE = hx("d8ccf4")
CLOUD_LOW = hx("b8a6e0")
CLOUD_EDGE = hx("7a62b0")

CLOUDS = [
    (44, 64, [(0, 0, 9), (10, -3, 11), (22, 0, 9), (-10, 2, 7), (32, 3, 6)]),
    (196, 52, [(0, 0, 8), (11, -2, 10), (-9, 1, 7), (21, 2, 6)]),
    (34, 152, [(0, 0, 7), (9, -2, 9), (19, 1, 6)]),
    (222, 150, [(0, 0, 7), (-9, -1, 8), (-19, 1, 6)]),
]

for cx, cy, blobs in CLOUDS:
    mask = set()
    for bx, by, r in blobs:
        for y in range(cy + by - r, cy + by + r + 1):
            for x in range(cx + bx - r, cx + bx + r + 1):
                if (x - cx - bx) ** 2 + (y - cy - by) ** 2 <= r * r:
                    mask.add((x, y))
    for x, y in mask:
        edge = any((x + dx, y + dy) not in mask for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        rel = y - cy
        if edge and rel > -4:
            col = CLOUD_EDGE
        elif edge:
            col = CLOUD_EDGE
        elif rel <= 0:
            col = CLOUD_FILL
        elif rel < 5:
            col = CLOUD_SHADE
        else:
            col = CLOUD_LOW
        put(x, y, col)

# --- Round bushes along the lawn edges ---
BUSH_DARK = hx("1e5a2a")
BUSH_MID = hx("2f7a36")
BUSH_LIGHT = hx("58b04a")
for bx in (18, 44, 212, 240):
    for y in range(176, GROUND_Y):
        for x in range(bx - 11, bx + 12):
            if (x - bx) ** 2 + (y - 186) ** 2 <= 100:
                if y < 180:
                    col = BUSH_LIGHT
                elif (x - bx) > 4:
                    col = BUSH_DARK
                else:
                    col = BUSH_MID
                put(x, y, col)

# --- Eiffel Tower ---
TOP_Y = 36
METAL_LIGHT = hx("c8ccd8")
METAL_MID = hx("8f94aa")
METAL_DARK = hx("4a4f6a")
OUTLINE = hx("1c1a2e")


def outer(y):
    # Concave profile: narrow spire, legs flaring sharply toward the base
    t = (y - TOP_Y) / (GROUND_Y - TOP_Y)
    return 2 + 60 * max(t, 0) ** 1.6


for y in range(TOP_Y, GROUND_Y):
    w = outer(y)
    for dx in range(-63, 64):
        ax = abs(dx)
        if ax > w:
            continue
        x = 128 + dx
        if ax >= w - 1:
            put(x, y, OUTLINE)
            continue
        if y >= 120:
            thick = 5 + (y - 120) / 76 * 3
            inner = w - thick
            if ax >= inner:
                if dx < -w * 0.35:
                    col = METAL_LIGHT
                elif dx < w * 0.35:
                    col = METAL_MID
                else:
                    col = METAL_DARK
                put(x, y, col)
            else:
                # Open gap between the legs: inner edge outline, sparse bracing
                if ax >= inner - 1:
                    put(x, y, OUTLINE)
                    continue
                if y >= 168 and ax <= 20:
                    continue
                if (y + ax) % 12 == 0:
                    put(x, y, METAL_DARK)
        else:
            # Solid upper body with horizontal girders
            if dx < -w * 0.35:
                col = METAL_LIGHT
            elif dx < w * 0.35:
                col = METAL_MID
            else:
                col = METAL_DARK
            if y % 6 == 0:
                col = METAL_DARK
            put(x, y, col)

# Platforms (two observation decks)
for dx in range(-27, 28):
    put(128 + dx, 118, METAL_LIGHT)
    put(128 + dx, 119, METAL_MID)
    put(128 + dx, 120, OUTLINE)
for dx in range(-12, 13):
    put(128 + dx, 78, METAL_LIGHT)
    put(128 + dx, 79, OUTLINE)

# --- Champ de Mars ground ---
GRASS_A = hx("3a8c3a")
GRASS_B = hx("58b04a")
GRASS_DEEP = hx("2a6e2e")
GRASS_DEEP2 = hx("1e4a20")
PATH = hx("e8d0a0")
for y in range(GROUND_Y, H):
    for x in range(W):
        if y == GROUND_Y:
            col = PATH
        elif y < 200:
            col = GRASS_B if (x // 4 + y) % 2 == 0 else GRASS_A
        else:
            col = GRASS_DEEP2 if (x // 8 + y // 4) % 3 == 0 else GRASS_DEEP
        put(x, y, col)

# --- Write PNG (8-bit RGB, filter 0 on every row) ---


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


raw = bytearray()
for row in canvas:
    raw.append(0)
    for col in row:
        raw.extend(col)

png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
       + chunk(b"IEND", b""))

# --- SNES limit checks ---
all_colors = set()
for row in canvas:
    all_colors.update(row)
assert len(all_colors) <= 128, f"{len(all_colors)} colors total"
for ty in range(0, H, 8):
    for tx in range(0, W, 8):
        tile = {canvas[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8)}
        assert len(tile) <= 16, f"tile ({tx},{ty}) has {len(tile)} colors"

here = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(here, "..", "output")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "eiffel_tower_snes.png")
with open(out_path, "wb") as f:
    f.write(png)
print(f"wrote {out_path}: {W}x{H}, {len(all_colors)} colors, {len(png)} bytes")
