"""Procedurally draws an SNES-style Eiffel Tower at native 256x224 and writes an indexed PNG.

Constraints enforced at the end:
  - 256x224 canvas, no scaling
  - at most 128 colors total
  - every 8x8 tile uses at most 16 colors
"""
import math
import os
import random
import struct
import zlib

W, H = 256, 224


def hx(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


img = [[None] * W for _ in range(H)]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = hx(c)


def rect(x0, x1, y0, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, c)


# ---------- sky: banded gradient with checkerboard dither on each seam ----------
BANDS = [
    (0, '#0a1640'), (18, '#132a6a'), (36, '#1d3c86'), (54, '#2a4fa0'),
    (72, '#3a68b8'), (90, '#5585c8'), (106, '#78a6dc'), (122, '#a4c4e8'),
    (138, '#d8c8e8'), (152, '#f8c8b0'), (166, '#fca888'), (180, '#f88a70'),
    (192, '#e86a6a'),
]


def band_index(y):
    y = max(0, min(H - 1, y))
    idx = 0
    for k, (start, _) in enumerate(BANDS):
        if y >= start:
            idx = k
    return idx


def sky_color(x, y):
    i = band_index(y)
    nxt = band_index(y + 1)
    if nxt != i and (x + y) % 2 == 0:
        i = nxt
    prv = band_index(y - 1)
    if prv != i and (x + y) % 2 == 1:
        i = prv
    return BANDS[i][1]


for y in range(H):
    for x in range(W):
        put(x, y, sky_color(x, y))

# ---------- stars (upper sky only) ----------
rng = random.Random(7)
for _ in range(64):
    x, y = rng.randrange(W), rng.randrange(4, 80)
    put(x, y, rng.choice(['#ffffff', '#cfe0ff', '#fff6c8']))
for _ in range(10):  # a few twinkling sparkles
    x, y = rng.randrange(8, W - 8), rng.randrange(6, 70)
    put(x, y, '#ffffff')
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        put(x + dx, y + dy, '#9fbfff')

# ---------- setting sun, right of the tower ----------
SUN_X, SUN_Y = 190, 100
for y in range(SUN_Y - 26, SUN_Y + 27):
    for x in range(SUN_X - 26, SUN_X + 27):
        d = math.hypot(x - SUN_X, y - SUN_Y)
        if d <= 5:
            c = '#fffbe6'
        elif d <= 9:
            c = '#fff0a0'
        elif d <= 14:
            c = '#ffd45a'
        elif d <= 18:
            c = '#ffb347'
        elif 19 <= d <= 24 and (x + y) % 2 == 0:
            c = '#ffd27a'  # dithered halo
        else:
            continue
        put(x, y, c)

# ---------- clouds: white top, lavender underside ----------


def cloud(cx, cy, blobs):
    for dx, dy, r in blobs:
        for yy in range(-r, r + 1):
            for xx in range(-r, r + 1):
                if xx * xx + yy * yy <= r * r:
                    Y = cy + dy + yy
                    if Y <= cy - 3:
                        c = '#ffffff'
                    elif Y <= cy + 1:
                        c = '#f0eefc'
                    else:
                        c = '#c0b8e0'
                    put(cx + dx + xx, Y, c)


cloud(44, 62, [(0, 0, 9), (-10, 3, 6), (10, 2, 7), (20, 4, 5), (-20, 5, 4)])
cloud(214, 136, [(0, 0, 8), (-9, 2, 6), (9, 1, 6), (-16, 4, 4)])
cloud(96, 30, [(0, 0, 6), (7, 1, 5), (-6, 2, 4)])

# ---------- distant Paris skyline ----------
rng2 = random.Random(11)
x = 0
while x < W:
    w = rng2.randint(4, 9)
    h = rng2.randint(6, 14)
    top = 196 - h
    for xx in range(x, min(W, x + w)):
        for yy in range(top, 200):
            put(xx, yy, '#3d2f63')
        put(xx, top, '#4d3f78')
    for yy in range(top + 2, 198, 3):
        for xx in range(x + 1, x + w - 1, 3):
            if rng2.random() < 0.35:
                put(xx, yy, '#ffd860')
    x += w

# ---------- Champ de Mars lawn ----------
for y in range(198, H):
    for x in range(W):
        if y == 198:
            c = '#1d5c36'
        elif y >= 214:
            c = '#266f3c'
        elif (y // 4) % 2 == 0:
            c = '#2f8a4a'
        else:
            c = '#37994f'
        put(x, y, c)

# ground shadow under the feet
for y in range(197, 206):
    for x in range(W):
        if ((x - 128) / 52) ** 2 + ((y - 201) / 4) ** 2 <= 1:
            put(x, y, '#1d5c36')

# ---------- the tower ----------
OUT = '#24130c'
DARK = '#4a2c1c'
MID = '#7a4f33'
LIGHT = '#b07a4e'
HI = '#d9a06a'


def half(y):
    t = (200 - y) / 176.0
    t = max(0.0, min(1.0, t))
    return int(round(44 * (1 - t) ** 1.5))


def thk(y):
    return 3 + 7 * max(0.0, min(1.0, (y - 40) / 160.0))


for y in range(24, 200):
    h = half(y)
    th = thk(y)
    for dx in range(-h, h + 1):
        ax = abs(dx)
        X = 128 + dx
        if ax == h and h >= 2:
            put(X, y, OUT)
        elif ax == h - th and h >= 10:
            put(X, y, OUT)
        elif ax > h - th or h < 10:
            if dx < 0:
                base = MID
                if (dx + y) % 9 == 0 or (dx - y) % 9 == 0:
                    base = DARK
                if ax == h - 1 and h >= 10:
                    base = HI
            else:
                base = DARK
                if (dx + y) % 9 == 0 or (dx - y) % 9 == 0:
                    base = OUT
            put(X, y, base)

# platforms and beams
h = half(66) + 2
rect(128 - h, 128 + h, 65, 67, MID)
rect(128 - h, 128 + h, 65, 65, LIGHT)
rect(128 - h, 128 + h, 67, 67, OUT)

h = half(118) + 3
rect(128 - h, 128 + h, 116, 119, MID)
rect(128 - h, 128 + h, 116, 116, HI)
rect(128 - h, 128 + h, 119, 119, OUT)

h = half(150) + 2
rect(128 - h, 128 + h, 149, 150, MID)
rect(128 - h, 128 + h, 149, 149, LIGHT)
rect(128 - h, 128 + h, 150, 150, OUT)

# the great arches between the legs
for dx in range(-40, 41):
    yc = round(200 - 34 * (1 - (dx / 40.0) ** 2))
    put(128 + dx, yc - 2, LIGHT)
    put(128 + dx, yc - 1, MID)
    put(128 + dx, yc, MID)
    put(128 + dx, yc + 1, DARK)
    put(128 + dx, yc + 2, OUT)

# spire and beacon
rect(127, 128, 12, 24, DARK)
put(128, 10, OUT)
put(128, 8, '#fff27a')
put(127, 8, '#ffd45a')
put(129, 8, '#ffd45a')
put(128, 7, '#ffffff')

# ---------- write indexed PNG ----------


def write_png(path, pixels, palette):
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for c in row:
            raw.append(palette.index(c))

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 3, 0, 0, 0)
    plte = b''.join(bytes(c) for c in palette)
    out = b'\x89PNG\r\n\x1a\n'
    out += chunk(b'IHDR', ihdr)
    out += chunk(b'PLTE', plte)
    out += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    out += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(out)


def check(pixels):
    colors = set(c for row in pixels for c in row)
    assert None not in colors, 'unpainted pixel'
    worst = 0
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            tile = set(pixels[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8))
            worst = max(worst, len(tile))
    return len(colors), worst


if __name__ == '__main__':
    palette = sorted(set(c for row in img for c in row))
    n_colors, worst_tile = check(img)
    assert n_colors <= 128, n_colors
    assert worst_tile <= 16, worst_tile
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(root, 'output', 'eiffel_tower_snes.png')
    write_png(out_path, img, palette)
    print('size: %dx%d' % (W, H))
    print('total colors: %d (limit 128)' % n_colors)
    print('worst tile colors: %d (limit 16)' % worst_tile)
    print('wrote', out_path, os.path.getsize(out_path), 'bytes')
