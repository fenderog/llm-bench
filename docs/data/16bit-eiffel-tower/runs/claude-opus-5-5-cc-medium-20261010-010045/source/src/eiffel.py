#!/usr/bin/env python3
"""SNES-style pixel art of the Eiffel Tower at sunset.

Renders a 256x224 indexed PNG and enforces SNES-like limits:
  * <= 128 colours total (all colours snapped to 15-bit BGR555)
  * every 8x8 tile uses <= 16 colours
Standard library only.
"""
import math
import random
import struct
import sys
import zlib

W, H = 256, 224
OUT = sys.argv[1] if len(sys.argv) > 1 else "output/eiffel_tower_snes.png"


def C(r, g, b):
    # snap to 5 bits per channel, like SNES CGRAM
    return ((r >> 3) << 3, (g >> 3) << 3, (b >> 3) << 3)


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bay(x, y):
    return (BAYER[y & 3][x & 3] + 0.5) / 16.0


img = [[(0, 0, 0)] * W for _ in range(H)]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H and c is not None:
        img[y][x] = c


# ---------------------------------------------------------------- sky
SKY = [C(16, 16, 56), C(32, 24, 80), C(48, 32, 104), C(88, 40, 128),
       C(120, 56, 144), C(168, 72, 144), C(208, 88, 128), C(232, 112, 112),
       C(248, 144, 104), C(248, 176, 112), C(248, 208, 136), C(248, 232, 176)]
SUN_X, SUN_Y, SUN_R = 100, 168, 15
HORIZON = 196


def sky_index(x, y):
    g = (max(0, y) / HORIZON) ** 1.25 * (len(SKY) - 1.6)
    d = math.hypot((x - SUN_X) * 0.75, (y - SUN_Y) * 1.25)
    g += max(0.0, 3.2 * (1 - d / 95.0))
    g = min(g, len(SKY) - 1.001)
    i = int(g)
    f = g - i
    if f > 0.5 and bay(x, y) < (f - 0.5) / 0.5:
        i += 1
    return i


for y in range(H):
    for x in range(W):
        img[y][x] = SKY[sky_index(x, y)]

rng = random.Random(1994)
STAR = C(248, 248, 248)
STAR2 = C(168, 176, 232)
for _ in range(70):
    x, y = rng.randrange(W), rng.randrange(70)
    if sky_index(x, y) <= 2:
        put(x, y, STAR2 if rng.random() < 0.6 else STAR)
for (x, y) in [(22, 14), (196, 22), (236, 50), (58, 40)]:
    put(x, y, STAR)
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        put(x + dx, y + dy, STAR2)

# sun disc
SUN_CORE, SUN_EDGE = C(248, 248, 216), C(248, 240, 176)
for y in range(SUN_Y - SUN_R, SUN_Y + SUN_R + 1):
    for x in range(SUN_X - SUN_R, SUN_X + SUN_R + 1):
        d = math.hypot(x - SUN_X + 0.5, y - SUN_Y + 0.5)
        if d < SUN_R - 2:
            put(x, y, SUN_CORE)
        elif d < SUN_R:
            put(x, y, SUN_EDGE)

# ---------------------------------------------------------------- clouds
CLOUD_SETS = {
    "high": [C(56, 40, 104), C(88, 56, 128), C(136, 72, 144), C(200, 104, 144), C(240, 152, 152)],
    "mid": [C(104, 56, 136), C(152, 72, 144), C(200, 96, 136), C(240, 136, 128), C(248, 192, 152)],
    "low": [C(176, 80, 128), C(216, 104, 120), C(240, 136, 112), C(248, 176, 128), C(248, 224, 184)],
}


def cloud_bank(x0, x1, ybase, hmax, seed, style, cut_sun=False):
    r = random.Random(seed)
    ells = []
    x = x0
    while x < x1:
        rx = r.randint(8, 18)
        ry = r.uniform(0.6, 1.0) * hmax * (0.6 + 0.4 * math.sin(math.pi * (x - x0) / max(1, x1 - x0)))
        ry = max(2.0, ry)
        bot = ybase + r.choice([0, 0, 1, -1, 2])
        ells.append((x, bot, rx, ry))
        x += r.randint(6, 12)
    # tails: long thin streaks
    ells.append((x0 - 10, ybase, 22, 1.6))
    ells.append((x1 + 8, ybase - 1, 18, 1.6))
    mask = {}
    for (cx, bot, rx, ry) in ells:
        for y in range(int(bot - ry) - 1, bot + 1):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dy = (y - bot) / ry
                dx = (xx - cx) / rx
                if dx * dx + dy * dy <= 1.0:
                    mask[(xx, y)] = True
    pal = CLOUD_SETS[style]
    for (xx, y) in mask:
        if not (0 <= xx < W and 0 <= y < H):
            continue
        # thickness below this pixel (distance to the lit underside)
        db = 0
        while (xx, y + db + 1) in mask:
            db += 1
        top = (xx, y - 1) not in mask
        if db == 0:
            c = pal[4] if (xx + y) % 7 else pal[3]
        elif db == 1:
            c = pal[3]
        elif db == 2:
            c = pal[3] if bay(xx, y) < 0.5 else pal[2]
        elif db <= 4:
            c = pal[2]
        elif db == 5:
            c = pal[2] if bay(xx, y) < 0.5 else pal[1]
        else:
            c = pal[1]
            if db > 9 and bay(xx, y) < 0.5:
                c = pal[0]
        if top and db > 2:
            c = pal[2] if db < 7 else pal[1]
        put(xx, y, c)


cloud_bank(150, 230, 38, 12, 7, "high")
cloud_bank(8, 72, 62, 13, 11, "high")
cloud_bank(172, 252, 98, 18, 3, "mid")
cloud_bank(-6, 58, 118, 16, 5, "mid")
cloud_bank(62, 104, 136, 9, 21, "mid")
cloud_bank(146, 196, 146, 8, 17, "low")
cloud_bank(66, 128, 162, 2, 9, "low")
cloud_bank(200, 250, 158, 4, 2, "low")

# a few distant birds
BIRD = C(40, 24, 64)
for (bx, by) in [(176, 66), (184, 62), (190, 70), (40, 86)]:
    for p in [(-2, -1), (-1, 0), (0, 0), (1, 0), (2, -1)]:
        put(bx + p[0], by + p[1], BIRD)
    put(bx, by, BIRD)

# ---------------------------------------------------------------- city skyline
FAR, FAR_RIM = C(144, 72, 128), C(208, 112, 128)
NEAR_WALL, NEAR_ROOF, NEAR_RIM = C(88, 48, 104), C(64, 40, 88), C(160, 88, 120)
WIN, WIN2 = C(248, 208, 112), C(232, 152, 88)
GOLD, GOLD_H = C(200, 144, 64), C(248, 216, 120)

r = random.Random(42)
far_h = [0] * W
x = 0
while x < W:
    w = r.randint(3, 10)
    h = r.randint(3, 10)
    for i in range(x, min(W, x + w)):
        far_h[i] = h
    x += w
# Sacre-Coeur-ish domes on a hill, far right
for i in range(W):
    hill = 6 * math.exp(-((i - 214) / 26.0) ** 2)
    far_h[i] = int(far_h[i] * 0.6 + hill)
for (dx, dr, extra) in [(214, 6, 9), (206, 3, 7), (222, 3, 7)]:
    for i in range(dx - dr, dx + dr + 1):
        k = math.sqrt(max(0, dr * dr - (i - dx) ** 2))
        far_h[i] = max(far_h[i], int(extra + k))
far_h[214] += 3
for xx in range(W):
    top = 190 - far_h[xx]
    for y in range(top, 200):
        put(xx, y, FAR_RIM if y == top else FAR)

# nearer Haussmann blocks with mansard roofs and lit windows
x = -2
while x < W:
    w = r.randint(9, 20)
    wall_top = 198 - r.randint(5, 9)
    roof_h = r.randint(2, 4)
    for i in range(x, x + w):
        if not 0 <= i < W:
            continue
        inset = 1 if (i == x or i == x + w - 1) else 0
        rt = wall_top - roof_h + inset
        for y in range(rt, 201):
            if y < wall_top:
                c = NEAR_RIM if y == rt else NEAR_ROOF
            else:
                c = NEAR_WALL
            put(i, y, c)
    # windows
    for wy in range(wall_top + 1, 199, 3):
        for wx in range(x + 2, x + w - 2, 3):
            if r.random() < 0.35:
                put(wx, wy, WIN if r.random() < 0.6 else WIN2)
    # chimneys
    for _ in range(r.randint(0, 2)):
        cxp = r.randint(x + 2, x + w - 3)
        for y in range(wall_top - roof_h - 2, wall_top - roof_h + 1):
            put(cxp, y, NEAR_ROOF)
        put(cxp, wall_top - roof_h - 2, NEAR_RIM)
    x += w

# Les Invalides golden dome, left side
IX, IY = 64, 187
for y in range(IY - 9, IY + 1):
    for i in range(IX - 7, IX + 8):
        d = math.hypot((i - IX) / 7.0, (y - IY) / 9.0)
        if d <= 1 and y <= IY:
            c = GOLD_H if (i - IX) < -2 and y < IY - 3 else GOLD
            if (i - IX) % 3 == 0 and y > IY - 7:
                c = C(152, 96, 56)
            put(i, y, c)
for y in range(IY + 1, 196):
    for i in range(IX - 9, IX + 10):
        put(i, y, NEAR_WALL if (i % 3) else NEAR_ROOF)
for y in range(IY - 15, IY - 8):
    put(IX, y, GOLD_H if y < IY - 12 else GOLD)
put(IX - 1, IY - 10, GOLD)
put(IX + 1, IY - 10, C(152, 96, 56))

# ---------------------------------------------------------------- the tower
T_OUT = C(32, 16, 40)
T_D = C(72, 32, 56)
T_M = C(120, 56, 64)
T_L = C(176, 88, 64)
T_H = C(232, 136, 80)
T_S = C(248, 200, 128)

CX = 127.5
BASE_Y = 200
TOP_Y = 10
SCALE = (BASE_Y - TOP_Y) / 312.0  # px per metre (300 m + antenna)
WX = 1.25                          # width exaggeration for chunkiness

OUTER = [(0, 62), (15, 55), (30, 48), (45, 42), (57, 37), (80, 30), (100, 24),
         (115, 20.5), (140, 17), (170, 14), (200, 11.5), (235, 9), (265, 7), (276, 6.2)]
INNER = [(0, 44), (20, 35), (40, 27), (57, 22), (80, 15), (100, 11), (115, 8.4),
         (140, 4.5), (165, 1.6), (175, 0)]


def interp(tab, h):
    if h <= tab[0][0]:
        return tab[0][1]
    for (h0, v0), (h1, v1) in zip(tab, tab[1:]):
        if h <= h1:
            return v0 + (v1 - v0) * (h - h0) / (h1 - h0)
    return tab[-1][1]


def hpx(m):
    return m * SCALE


P1, P2, P3 = 57, 115, 276
P1_T, P2_T, P3_T = 9, 6, 5   # platform thickness in metres
ARCH_H = 39


def tower_pixel(x, y):
    h = (BASE_Y - y) / SCALE + 0.5 / SCALE
    dx = x + 0.5 - 128
    ax = abs(dx)
    left = dx < 0
    O = interp(OUTER, h) * SCALE * WX
    I = interp(INNER, h) * SCALE * WX if h < 175 else -1

    # platforms
    for (ph, pt, ext) in [(P1, P1_T, 2.5), (P2, P2_T, 2.0), (P3, P3_T, 1.5)]:
        if ph <= h < ph + pt:
            Ow = interp(OUTER, ph) * SCALE * WX + ext
            if ax > Ow:
                return None
            row = int((BASE_Y - y) - hpx(ph))  # 0 = bottom row of platform
            nrows = max(2, int(round(hpx(pt))))
            if row >= nrows - 1:
                return T_S if left and ax > 2 else T_L
            if row == 0:
                return T_OUT
            if ax > Ow - 1:
                return T_H if left else T_D
            # little arcade/railing windows
            if (x % 3 == 0) and 0 < row < nrows - 1:
                return T_D if ph != P3 else T_OUT
            return T_L if left else T_M

    # top cabin + lantern + antenna
    if h >= P3 + P3_T:
        top_px = (BASE_Y - y) - hpx(P3 + P3_T)
        if top_px < 5:
            w = 3.5 if top_px < 3 else 2.5
            if ax > w:
                return None
            if top_px == 4:
                return T_L
            if ax > w - 1:
                return T_H if left else T_D
            return T_S if (y % 2 == 0 and ax < 1.5) else T_M
        if y < TOP_Y:
            return None
        if y <= TOP_Y + 1:
            return T_S if ax < 0.6 else None
        if top_px < 9:
            if ax < 1.5:
                return T_L if left else T_D
            return None
        if ax < 0.6:
            return T_H if y % 3 else T_M
        return None

    if ax > O:
        return None

    edge_out = ax > O - 1.0
    # open center between the legs
    if ax < I:
        if h < P1:
            a = I_BASE
            b = hpx(ARCH_H)
            hp = (BASE_Y - y) + 0.5
            e = math.hypot(ax / a, hp / b)
            if e < 1.0:
                return None                       # under the arch: open sky
            if e < 1.0 + 2.4 / b:
                if e < 1.0 + 1.0 / b:
                    return T_D                    # arch soffit
                return T_L if left else T_M       # arch face
            # spandrel lattice
            if (x + y) % 4 == 0 or (x - y) % 4 == 0:
                return T_M if left else T_D
            return None
        # horizontal girders crossing the gap between legs
        rowm = int((BASE_Y - y) - hpx(P2))
        if h > P2 and rowm % 9 == 3:
            return T_D
        return None

    if ax < I + 1.0:
        # inner edges: left leg's inner side faces away from the sun
        return T_M if left else T_L
    if edge_out:
        return T_H if left else T_OUT

    # leg / shaft interior lattice
    period = 4 if h < P2 else 3
    k = 1 if left else 0
    on_x = (x + y) % period == 0 or (x - y) % period == 0
    on_h = (y % 6 == 0) if h < P2 else (y % 4 == 0)
    if on_h:
        return T_L if left else T_D
    if on_x:
        return T_L if left else T_M
    if h >= 170 or (O - I) < 3:
        return T_M if left else T_D
    if (x + y) % 2 == k or y % 2 == 0:
        return T_D if left else T_OUT
    return None


I_BASE = interp(INNER, 0) * SCALE * WX + 0.5
for y in range(TOP_Y - 1, BASE_Y + 1):
    for x in range(W):
        c = tower_pixel(x, y)
        if c is not None:
            put(x, y, c)
# sunset glint on top lantern
put(127, TOP_Y, C(248, 248, 216))
put(128, TOP_Y, C(248, 248, 216))

# ---------------------------------------------------------------- ground
GRASS_D, GRASS_M, GRASS_L = C(32, 64, 48), C(48, 88, 56), C(72, 112, 64)
PATH_D, PATH_M, PATH_L = C(136, 96, 88), C(184, 136, 104), C(224, 176, 128)
HEDGE = C(24, 48, 40)
VX, VY = 127.5, 192
for y in range(201, H):
    for x in range(W):
        t = (y - 200) / 24.0
        half = 18 + t * 56
        dx = x + 0.5 - VX
        if abs(dx) < half:
            # gravel path: lit toward the sunset, streaky dither
            c = PATH_M
            if abs(dx) > half - 2:
                c = PATH_D
            elif bay(x, y) < 0.7 * (1 - (dx + half) / (2 * half)) - 0.1:
                c = PATH_L
            elif (x * 7 + y * 13) % 23 == 0:
                c = PATH_D
            put(x, y, c)
        elif abs(dx) < half + 3:
            put(x, y, HEDGE)
        else:
            ang = math.atan2(dx, (y - VY))
            stripe = int(ang * 14) % 2
            c = GRASS_M if stripe else GRASS_D
            if y < 204:
                c = GRASS_D
            elif stripe and bay(x, y) < 0.15:
                c = GRASS_L
            put(x, y, c)

# tower feet: stone piers
PIER, PIER_L = C(96, 72, 88), C(168, 128, 120)
for sgn in (-1, 1):
    O0 = interp(OUTER, 0) * SCALE * WX
    I0 = interp(INNER, 0) * SCALE * WX
    for y in range(199, 203):
        for x in range(int(CX + sgn * I0) - 1, int(CX + sgn * O0) + 2) if sgn > 0 else \
                range(int(CX - O0) - 1, int(CX - I0) + 2):
            put(x, y, PIER_L if y == 199 else PIER)

# little people on the path
PPL = C(40, 24, 56)
for (px, py, hh) in [(112, 206, 4), (115, 206, 4), (150, 210, 5), (96, 214, 6), (170, 218, 6)]:
    for yy in range(py - hh, py):
        put(px, yy, PPL)
        put(px + 1, yy, PPL if yy > py - hh else None)
    put(px, py - hh - 1, C(184, 136, 104) if px < 128 else PPL)

# ---------------------------------------------------------------- trees
LEAF = [C(16, 24, 40), C(24, 48, 56), C(40, 72, 64), C(80, 96, 64), C(176, 120, 72)]
TRUNK, TRUNK_L = C(40, 24, 32), C(88, 56, 56)


def bump(cx, cy, rad):
    for y in range(int(cy - rad) - 1, int(cy + rad) + 2):
        for x in range(int(cx - rad) - 1, int(cx + rad) + 2):
            ddx, ddy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(ddx, ddy)
            if d > rad:
                continue
            # light comes from the low sun on the left
            lit = (-ddx * 0.85 - ddy * 0.5) / rad - 0.12
            if d > rad - 1.2 and lit < -0.1:
                c = LEAF[0]
            elif lit > 0.62 and d > rad - 2.0:
                c = LEAF[4]
            elif lit > 0.3:
                c = LEAF[3] if bay(x, y) < (lit - 0.3) * 3 else LEAF[2]
            elif lit > -0.2:
                c = LEAF[2] if lit > 0.05 else LEAF[1]
            else:
                c = LEAF[1] if bay(x, y) < 0.5 + lit else LEAF[0]
            put(x, y, c)


def tree(cx, top, bottom, width, seed):
    tr = random.Random(seed)
    # trunk
    for y in range(bottom - 12, 206):
        for x in range(cx - 1, cx + 2):
            put(x, y, TRUNK_L if x == cx - 1 else TRUNK)
    # canopy: back-to-front bumps
    bumps = []
    for _ in range(int(width * (bottom - top) / 18)):
        bx = cx + tr.uniform(-width / 2, width / 2)
        span = (bottom - top)
        by = tr.uniform(top + 4, bottom - 3)
        # taper towards the top
        f = (by - top) / span
        bx = cx + (bx - cx) * min(1.0, 0.45 + f)
        bumps.append((bx, by, tr.uniform(3.5, 6.5)))
    bumps.sort(key=lambda b: (b[1] + b[0] * 0.2))
    for b in bumps:
        bump(*b)


# tree rows framing the Champ de Mars (back rows first)
tree(186, 184, 203, 12, 32)
tree(194, 168, 205, 20, 34)
tree(36, 150, 208, 26, 35)
tree(222, 148, 208, 26, 36)
tree(8, 118, 216, 34, 37)
tree(250, 116, 216, 34, 38)

# ---------------------------------------------------------------- lampposts
POLE, POLE_L = C(24, 24, 40), C(80, 72, 96)
LAMP, LAMP_H = C(248, 184, 88), C(248, 240, 176)


def lamppost(x0, base, top):
    for y in range(top + 6, base):
        put(x0, y, POLE_L)
        put(x0 + 1, y, POLE)
    for y in (base - 1, base - 2, base - 3):
        for x in range(x0 - 1, x0 + 3):
            put(x, y, POLE if x > x0 else POLE_L)
    put(x0 - 1, top + 12, POLE)
    put(x0 + 2, top + 12, POLE)
    # lantern
    for y in range(top, top + 7):
        hw = 1 if y in (top, top + 6) else 2
        for x in range(x0 - hw, x0 + 2 + hw):
            if y in (top, top + 6) or x in (x0 - hw, x0 + 1 + hw):
                put(x, y, POLE)
            else:
                put(x, y, LAMP_H if (x <= x0 and y < top + 4) else LAMP)
    put(x0, top - 1, POLE)
    put(x0 + 1, top - 1, POLE)
    put(x0, top - 2, POLE_L)


lamppost(30, 224, 150)
lamppost(224, 224, 150)

# ---------------------------------------------------------------- SNES limits
def enforce_limits():
    def dist(a, b):
        return (a[0] - b[0]) ** 2 * 3 + (a[1] - b[1]) ** 2 * 4 + (a[2] - b[2]) ** 2 * 2

    fixes = 0
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            while True:
                counts = {}
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        counts[img[y][x]] = counts.get(img[y][x], 0) + 1
                if len(counts) <= 16:
                    break
                rare = min(counts, key=lambda c: counts[c])
                keep = [c for c in counts if c != rare]
                best = min(keep, key=lambda c: dist(c, rare))
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        if img[y][x] == rare:
                            img[y][x] = best
                fixes += 1
    return fixes


fixes = enforce_limits()
palette = sorted({c for row in img for c in row})
assert len(palette) <= 128, len(palette)
worst = 0
for ty in range(0, H, 8):
    for tx in range(0, W, 8):
        n = len({img[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8)})
        worst = max(worst, n)
assert worst <= 16
print(f"colours: {len(palette)}  max colours per 8x8 tile: {worst}  tile merges: {fixes}")


# ---------------------------------------------------------------- PNG (indexed)
def write_png(path):
    index = {c: i for i, c in enumerate(palette)}
    raw = bytearray()
    for row in img:
        raw.append(0)
        raw.extend(index[c] for c in row)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 3, 0, 0, 0))
    png += chunk(b"PLTE", b"".join(bytes(c) for c in palette))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


write_png(OUT)
print("wrote", OUT)
