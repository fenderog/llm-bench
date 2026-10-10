#!/usr/bin/env python3
"""Eiffel Tower at dusk, drawn as 16-bit era pixel art.

Paints a 320x240 scene (SNES / Mega Drive class resolution) with hard
pixels, banded Bayer-dithered gradients and a small hand-picked palette,
snaps every colour to RGB565 (16-bit "high colour"), then has ffmpeg
upscale 8x with nearest-neighbour sampling and encode a JPEG. At 8x each
art pixel covers exactly one 8x8 JPEG block, so the pixels stay crisp.

    python3 src/eiffel_pixel.py   ->  output/eiffel_tower_16bit.jpg
"""
import math
import os
import random
import shutil
import subprocess

W, H = 320, 240
SCALE = 8
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
OUT_JPG = os.path.join(OUT_DIR, "eiffel_tower_16bit.jpg")
BUILD = os.path.join(ROOT, "build")


def C(s):
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


img = [[(0, 0, 0)] * W for _ in range(H)]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def get(x, y):
    return img[min(max(y, 0), H - 1)][min(max(x, 0), W - 1)]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t + 0.5) for i in range(3))


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def rnd(v):
    return int(math.floor(v + 0.5))


BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def bayer(x, y):
    return (BAYER[y & 3][x & 3] + 0.5) / 16.0


# --------------------------------------------------------------------- sky

SKY = [(0, "090a24"), (26, "10133a"), (50, "1a1b52"), (72, "262466"),
       (92, "352b78"), (110, "4a3284"), (126, "613a8c"), (140, "7c4290"),
       (152, "9a4a90"), (163, "b8568c"), (172, "d66a86"), (180, "ec8a80"),
       (188, "f8b07e"), (H, "f8b07e")]


def paint_sky():
    stops = [(y, C(c)) for y, c in SKY]
    for y in range(H):
        i = 0
        while y >= stops[i + 1][0]:
            i += 1
        (y0, c0), (y1, c1) = stops[i], stops[i + 1]
        # solid bands with a dithered seam between them
        f = clamp(((y + 0.5 - y0) / (y1 - y0) - 0.5) * 2.2 + 0.5)
        for x in range(W):
            img[y][x] = c1 if f > bayer(x, y) else c0


MOON = (56, 40)


def paint_stars(rng):
    bright, mid, dim = C("ffffff"), C("b8c2f4"), C("6a72bc")
    for _ in range(110):
        x, y = rng.randrange(W), int(rng.random() ** 1.6 * 118)
        if math.hypot(x - MOON[0], y - MOON[1]) < 20 or abs(x - 160) < 8:
            continue
        r = rng.random()
        put(x, y, bright if (r < 0.25 and y < 70) else mid if r < 0.6 else dim)
    for x, y, big in ((22, 12, 1), (106, 18, 0), (216, 10, 1), (284, 22, 0),
                      (304, 62, 0), (126, 58, 0), (252, 54, 1), (14, 72, 0)):
        put(x, y, bright)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(x + dx, y + dy, mid)
            if big:
                put(x + 2 * dx, y + 2 * dy, dim)


def paint_moon():
    mx, my = MOON
    glow = C("aaa2ec")
    for y in range(my - 20, my + 21):
        for x in range(mx - 20, mx + 21):
            d = math.hypot(x + 0.5 - mx, y + 0.5 - my)
            if d < 19:
                put(x, y, mix(get(x, y), glow, 0.15 if d < 13 else 0.07))
    lit, mid, shade = C("fff6d6"), C("ffe6a6"), C("e2b878")
    for y in range(my - 9, my + 10):
        for x in range(mx - 9, mx + 10):
            da = math.hypot(x + 0.5 - mx, y + 0.5 - my)
            db = math.hypot(x + 0.5 - (mx - 4.5), y + 0.5 - (my - 3))
            if da <= 8.5 and db > 7.4:
                put(x, y, shade if db < 8.6 else lit if da > 7.3 else mid)


def paint_cloud(rng, x0, x1, yc, thick, colors):
    body, top, rim2, rim1 = (C(c) for c in colors)
    blobs = []
    x = x0
    while x < x1:
        t = clamp((x - x0) / float(x1 - x0))
        rx = rng.uniform(7, 16)
        ry = rng.uniform(thick * 0.45, thick) * (0.4 + 0.6 * math.sin(math.pi * t))
        cy = yc + rng.uniform(-1.5, 1.5)
        blobs.append((x, cy, rx, max(ry, 1.3)))
        if rng.random() < 0.55:
            blobs.append((x + rng.uniform(-4, 4), cy - ry * 0.8, rx * 0.55, max(ry, 1.3) * 1.25))
        x += rx * rng.uniform(0.6, 1.1)
    mask = set()
    for bx, by, rx, ry in blobs:
        for y in range(int(by - ry) - 1, int(by + ry) + 2):
            for xx in range(int(bx - rx) - 1, int(bx + rx) + 2):
                if ((xx + 0.5 - bx) / rx) ** 2 + ((y + 0.5 - by) / ry) ** 2 <= 1:
                    mask.add((xx, y))
    # lit from below by the set sun: bright underside, darker crown
    for x, y in mask:
        if (x, y + 1) not in mask:
            c = rim1
        elif (x, y + 2) not in mask:
            c = rim2
        elif (x, y - 1) not in mask:
            c = top
        else:
            c = body
        put(x, y, c)


# -------------------------------------------------------------------- city

HAZE = C("a35887")


def paint_far_city(rng):
    win = C("f0a884")
    base = 201
    x = -3
    while x < W:
        w = rng.randint(6, 15)
        top = base - rng.randint(17, 28)
        for y in range(top, base):
            for xx in range(x, x + w):
                put(xx, y, HAZE)
        r = rng.random()
        if r < 0.35:
            for i in (1, 2):
                for xx in range(x + i, x + w - i):
                    put(xx, top - i, HAZE)
        elif r < 0.5:
            cx = x + rng.randint(1, max(1, w - 3))
            for y in (top - 1, top - 2):
                put(cx, y, HAZE)
                put(cx + 1, y, HAZE)
        for y in range(top + 2, base, 3):
            for xx in range(x + 1, x + w - 1, 2):
                if rng.random() < 0.07:
                    put(xx, y, win)
        x += w


def paint_invalides(cx, base):
    col = C("b4648f")
    gold, gold_l, gold_d = C("eaa65a"), C("ffd88a"), C("b0704a")
    for y in range(base - 29, base):
        for x in range(cx - 15, cx + 16):
            put(x, y, HAZE)
    for x in range(cx - 15, cx + 16):
        put(x, base - 29, col)
    for y in range(base - 36, base - 29):
        for x in range(cx - 7, cx + 8):
            put(x, y, col if (x - cx) % 2 == 0 and y > base - 35 else HAZE)
    for y in range(base - 48, base - 36):
        for x in range(cx - 8, cx + 9):
            dx, dy = (x - cx) / 8.5, (base - 36.5 - y) / 11.5
            if dx * dx + dy * dy <= 1:
                c = gold_l if dx < -0.3 else gold_d if dx > 0.5 else gold
                if (x - cx) % 3 == 0 and c is gold:
                    c = gold_d
                put(x, y, c)
    for y in range(base - 52, base - 48):
        put(cx, y, gold_l)
        if y > base - 51:
            put(cx - 1, y, gold)
            put(cx + 1, y, gold_d)
    for y in range(base - 57, base - 52):
        put(cx, y, gold)


def paint_montparnasse(x0, base, rng):
    col, win = C("8c4a7f"), C("e09482")
    for y in range(base - 44, base):
        for x in range(x0, x0 + 12):
            put(x, y, col)
    for x in (x0 + 3, x0 + 8):
        put(x, base - 45, col)
        put(x, base - 46, col)
    for y in range(base - 42, base, 2):
        for x in range(x0 + 1, x0 + 11):
            if rng.random() < 0.16:
                put(x, y, win)


def paint_mid_city(rng):
    wall, cornice, roof, dark = C("5c3066"), C("6c3a72"), C("3e2152"), C("2b183c")
    lit = (C("ffd27a"), C("f3a65c"), C("ffe7a8"))
    base = 203
    x = -4
    while x < W:
        w = rng.randint(11, 22)
        near = abs(x + w / 2 - 160) < 34
        top = base - (rng.randint(6, 9) if near else rng.randint(13, 21))
        for y in range(top + 3, base):
            for xx in range(x, x + w):
                put(xx, y, wall)
            put(x, y, dark)
        for xx in range(x, x + w):
            put(xx, top + 3, cornice)
        for i in range(3):
            for xx in range(x + 2 - i, x + w - 2 + i):
                put(xx, top + i, roof)
        for _ in range(rng.randint(1, 3)):
            cx = rng.randint(x + 2, x + w - 4)
            for y in (top - 1, top - 2):
                put(cx, y, dark)
                put(cx + 1, y, dark)
        for xx in range(x + 3, x + w - 2, 4):
            if rng.random() < 0.4:
                put(xx, top + 1, lit[0])
        for y in range(top + 5, base - 1, 3):
            for xx in range(x + 2, x + w - 1, 3):
                if rng.random() < 0.3:
                    put(xx, y, rng.choice(lit))
        x += w


# ------------------------------------------------------------------- tower

S = 0.58        # pixels per metre (330 m tall -> ~191 px)
GROUND = 200    # first row below the tower's feet
CX = 160        # centre column; the tower is mirrored around it

T_HL, T_G1, T_G2, T_G3, T_G4, T_G5 = (C(c) for c in (
    "fff4b8", "ffd75e", "f5a83a", "d07a26", "8e4620", "55261e"))
BEAM = C("fff0c0")

tower = {}


def tset(d, y, c, c_right=None):
    tower[(CX - d, y)] = c
    tower[(CX + d, y)] = c if c_right is None else c_right


def outer_m(h):
    # half-width of the tower in metres: the famous exponential curve
    return 61.0 * math.exp(-h / 96.0) + 1.5


def inner_m(h):
    # half-width of the opening between the legs
    if h <= 57:
        return outer_m(h) - (25.0 - 6.8 * h / 57.0)
    if h >= 114:
        return 0.0
    return 17.0 * (1 - (h - 57.0) / 57.0) ** 0.6


def h_of(y):
    return (GROUND - y - 0.5) / S


def ro_px(y):
    return int(outer_m(h_of(y)) * S + 0.35)


def lattice(rows, colw=7.0, inner_c=T_G1):
    """Cross-braced girder. rows: [(y, a, b)] bottom-up, a/b = inner/outer d."""
    i = 0
    while i < len(rows):
        _, a, b = rows[i]
        ncols = max(1, rnd((b - a) / colw))
        ph = max(4, rnd((b - a) / ncols * 1.1))
        for j, (y, a, b) in enumerate(rows[i:i + ph]):
            fv = (j + 0.5) / ph
            cw = (b - a) / float(ncols)
            for d in range(a, b + 1):
                tset(d, y, T_G4)
            for k in range(ncols):
                l = a + k * cw
                tset(rnd(l + fv * cw), y, T_G2)
                tset(rnd(l + cw - fv * cw), y, T_G2)
                if k:
                    tset(rnd(l), y, T_G3)
            if j == 0:
                for d in range(a, b + 1):
                    tset(d, y, T_G2)
            tset(a, y, inner_c)
            tset(b, y, T_HL, T_G1)
        i += ph


def draw_tower(rng):
    # legs, ground to first floor, with the big arch between them
    rows_a = [(y, rnd(inner_m(h_of(y)) * S), ro_px(y)) for y in range(GROUND - 1, 168, -1)]
    lattice(rows_a)
    ae, be = 31 * S, 48 * S
    for y, ri, _ in rows_a:
        hp = GROUND - y - 0.5
        for d in range(ri):
            q = math.hypot(d / ae, hp / be)
            if q < 1:
                continue
            if q < 1.045:
                tset(d, y, T_G1)
            elif q < 1.09:
                tset(d, y, T_G2)
            elif (d + y) % 4 == 0 or (d - y) % 4 == 0:
                tset(d, y, T_G3)

    # first floor -> second floor
    rows_b = [(y, rnd(inner_m(h_of(y)) * S), ro_px(y)) for y in range(161, 134, -1)]
    lattice(rows_b)

    # second floor -> top: two columns with a narrowing gap, then one shaft
    rows_c, rows_d = [], []
    for y in range(129, 41, -1):
        ro = ro_px(y)
        t = (h_of(y) - 121.0) / 84.0
        gi = rnd(ro * 0.42 * max(0.0, 1 - t) ** 0.8) if t < 1 else 0
        if gi >= 1 and not rows_d:
            rows_c.append((y, gi, ro))
        else:
            rows_d.append((y, 0, ro))
    lattice(rows_c)
    for y, gi, _ in rows_c:
        for d in range(1, gi):
            if (d + y) % 2 == 0:
                tset(d, y, T_G4)
        tset(0, y, T_G3)   # lift shaft running up the middle
    lattice(rows_d, inner_c=T_G3)

    # first-floor platform with its arcaded frieze
    pw = 22
    for d in range(pw):
        tset(d, 162, T_HL)
        if d % 2 == 0:
            tset(d, 163, T_G2)
    for d in range(pw + 1):
        tset(d, 164, T_G1)
    frieze = {165: (T_G2, T_G2, T_G5, T_G2),
              166: (T_G2, T_G5, T_G5, T_G5),
              167: (T_G2, T_G5, T_G5, T_G5)}
    for y, pat in frieze.items():
        for d in range(pw + 1):
            tset(d, y, T_G1 if d == pw else pat[d % 4])
    for d in range(pw):
        tset(d, 168, T_G3)

    # second-floor platform
    pw = 13
    for d in range(pw):
        tset(d, 130, T_HL)
        if d % 2 == 0:
            tset(d, 131, T_G2)
    for d in range(pw + 1):
        tset(d, 132, T_G1)
        tset(d, 133, T_G1 if d == pw else (T_G2, T_G5)[d % 2])
    for d in range(pw):
        tset(d, 134, T_G3)

    # top deck, Eiffel's cabin, lantern, dome and antenna
    for d in range(6):
        tset(d, 41, T_G3)
        tset(d, 40, T_HL if d == 5 else T_G1)
    for d in range(5):
        tset(d, 39, T_G2 if d % 2 == 0 else T_G4)
    for y in (36, 37, 38):
        for d in range(4):
            tset(d, y, T_G1 if d == 3 else (T_HL, T_G3)[d % 2])
    for d in range(5):
        tset(d, 35, T_G1)
    for y in (31, 32, 33, 34):
        for d in range(3):
            tset(d, y, T_G2 if d == 2 else T_HL)
    tset(0, 32, C("ffffff"))
    tset(0, 33, C("ffffff"))
    for d in range(3):
        tset(d, 30, T_G1)
    for d in range(2):
        tset(d, 29, T_G2)
        tset(d, 28, T_G1)
    tset(0, 27, T_G1)
    for y in range(9, 27):
        tset(0, y, T_G2 if y % 2 == 0 else T_G3)
    for y in (24, 19, 14):
        tset(1, y, T_G3)
    tset(0, 8, C("ff5a4a"))

    for (x, y), c in tower.items():
        put(x, y, c)

    # hourly sparkle
    spots = sorted(p for p in tower if 30 < p[1] < 186)
    for i, (x, y) in enumerate(rng.sample(spots, 30)):
        put(x, y, C("ffffff"))
        if i < 7:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                put(x + dx, y + dy, T_HL)


def paint_beams():
    ox, oy = CX + 0.5, 32.5
    for ang, length, strength in ((-0.12, 175, 0.34),):
        dx, dy = math.cos(ang), math.sin(ang)
        for y in range(H):
            for x in range(W):
                px, py = x + 0.5 - ox, y + 0.5 - oy
                along = px * dx + py * dy
                if along < 3 or along > length:
                    continue
                perp = abs(-px * dy + py * dx)
                spread = 1.0 + along * 0.07
                if perp > spread:
                    continue
                a = strength * (1 - along / length) * (1 - (perp / spread) ** 2) * 12.5
                a = (math.floor(a) + (a % 1 > bayer(x, y))) / 12.5
                if a > 0:
                    put(x, y, mix(get(x, y), BEAM, a))


# ------------------------------------------------------------- foreground

LAMPS = (12, 44, 76, 108, 212, 244, 276, 308)


def paint_trees(rng):
    cool = [C(c) for c in ("0a1620", "10242c", "183630", "22483a")]
    warm = [C(c) for c in ("4e5a2e", "8c8a3c", "d2bc5c")]
    blobs = []
    x = -6.0
    while x < W + 6:
        near = abs(x - CX) < 42
        r = rng.uniform(4, 6) if near else rng.uniform(5, 8.5)
        cy = rng.uniform(197, 200) if near else rng.uniform(192.5, 197)
        blobs.append((x, cy, r))
        x += rng.uniform(4, 8)
    blobs.sort(key=lambda b: b[1])
    for bx, by, r in blobs:
        lx, ly, lz = CX - bx, 172 - by, -14.0
        ln = math.sqrt(lx * lx + ly * ly + lz * lz)
        lx, ly, lz = lx / ln, ly / ln, lz / ln
        reach = clamp(1.6 - math.hypot(CX - bx, 172 - by) / 45.0)
        for y in range(int(by - r) - 1, int(by + r) + 2):
            for x in range(int(bx - r) - 1, int(bx + r) + 2):
                nx, ny = (x + 0.5 - bx) / r, (y + 0.5 - by) * 1.15 / r
                if nx * nx + ny * ny > 1:
                    continue
                nz = math.sqrt(1 - nx * nx - ny * ny)
                n = (rng.random() - 0.5) * 0.3
                w = max(0.0, nx * lx + ny * ly + nz * lz) * reach + n
                k = max(0.0, -ny * 0.75 + nz * 0.35 - 0.1) + n
                if w > 0.62:
                    c = warm[2]
                elif w > 0.45:
                    c = warm[1]
                elif w > 0.3:
                    c = warm[0]
                else:
                    c = cool[3 if k > 0.6 else 2 if k > 0.4 else 1 if k > 0.18 else 0]
                put(x, y, c)


def paint_quay():
    walk, cope_t, cope_f = C("221a30"), C("a07888"), C("6a4a66")
    stone, joint = C("4e3858"), C("3a2846")
    glow = C("ffc070")
    for x in range(W):
        put(x, 203, walk)
        put(x, 204, cope_t)
        put(x, 205, cope_f)
        for y in range(206, 212):
            course = 0 if y < 209 else 1
            c = joint if y in (208, 211) or (x + 4 * course) % 9 == 0 else stone
            put(x, y, c)
    for lx in LAMPS:
        for y in (204, 205, 206):
            for x in range(lx - 5, lx + 6):
                a = 0.32 * (1 - abs(x - lx) / 6.0) * (1 - (y - 204) / 3.0)
                put(x, y, mix(get(x, y), glow, a))
    for y in range(204, 212):
        for x in range(CX - 34, CX + 35):
            put(x, y, mix(get(x, y), T_G2, 0.14 * (1 - abs(x - CX) / 35.0)))


def paint_lamps():
    post, cap = C("1a1428"), C("2e2440")
    glow = C("ffcf70")
    for lx in LAMPS:
        for y in range(186, 200):
            for x in range(lx - 6, lx + 7):
                d = math.hypot(x - lx, y - 192)
                if d < 6:
                    put(x, y, mix(get(x, y), glow, 0.3 if d < 3.5 else 0.14))
        for y in range(194, 203):
            put(lx, y, post)
        put(lx - 1, 202, post)
        put(lx + 1, 202, post)
        for x in (lx - 1, lx, lx + 1):
            put(x, 190, cap)
            put(x, 193, T_G2)
        put(lx - 1, 191, T_G1)
        put(lx + 1, 191, T_G1)
        put(lx - 1, 192, T_G1)
        put(lx + 1, 192, T_G1)
        put(lx, 191, C("fffbe0"))
        put(lx, 192, C("fffbe0"))
        put(lx, 189, cap)


def paint_water(rng):
    src = [row[:] for row in img]
    top, bottom = C("2a2258"), C("110d2c")
    ripple = C("443e86")
    wy = 212
    for y in range(wy, H):
        base = mix(top, bottom, (y - wy) / float(H - 1 - wy))
        sy = 2 * wy - 1 - y
        for x in range(W):
            ox = rnd(1.3 * math.sin(y * 0.9 + x * 0.05) + 0.9 * math.sin(y * 2.3 + 1.0))
            s = src[sy][min(max(x + ox, 0), W - 1)]
            lum = (s[0] * 3 + s[1] * 6 + s[2]) / 10.0
            c = mix(base, s, 0.62 if lum > 170 else 0.4)
            if (y - wy) % 3 == 2:
                c = mix(c, bottom, 0.3)
            img[y][x] = c
    for y in range(wy + 1, H, 2):
        x = rng.randrange(-12, 0)
        while x < W:
            ln = rng.randint(2, 7)
            if rng.random() < 0.5:
                for k in range(ln):
                    if get(x + k, y)[0] < 120:
                        put(x + k, y, ripple)
            x += ln + rng.randint(4, 14)
    # light trails on the water: the tower and the quay lamps
    for y in range(wy + 1, H):
        rel = (y - wy) / float(H - wy)
        for _ in range(6):
            if rng.random() < 0.8:
                x = CX + rnd(rng.gauss(0, 7 + rel * 9))
                ln = rng.randint(1, 3) + (rel > 0.4) + (rel > 0.7)
                c = rng.choice((T_HL, T_G1, T_G2, T_G2, T_G3) if rel < 0.5 else (T_G1, T_G2, T_G3, T_G3))
                for k in range(ln):
                    put(x + k - ln // 2, y, c)
        for lx in LAMPS:
            if rng.random() < 0.55:
                ln = rng.choice((1, 2, 2, 3))
                c = mix(C("ffd070"), C("b0603a"), rel)
                x = lx + rng.randint(-1, 1)
                for k in range(ln):
                    put(x + k - ln // 2, y, c)


def paint_boat(rng, x0=24, y0=219):
    roof, frame = C("c9cde4"), C("4c4a72")
    glass = (C("ffe08a"), C("f6b45a"))
    rail, hull, hull_d = C("eceaf6"), C("46427a"), C("17152f")
    foam = C("aab2dc")
    n = 62
    for x in range(x0 + 5, x0 + n - 5):
        put(x, y0, roof)
    for row, g in ((1, glass[0]), (2, glass[1])):
        for x in range(x0 + 3, x0 + n - 3):
            put(x, y0 + row, frame if (x - x0) % 4 == 0 or x in (x0 + 3, x0 + n - 4) else g)
    for x in range(x0 + 1, x0 + n):
        put(x, y0 + 3, rail)
    put(x0 + n, y0 + 3, rail)
    put(x0 + n + 1, y0 + 2, rail)
    for x in range(x0, x0 + n + 1):
        put(x, y0 + 4, hull)
    for x in range(x0 + 2, x0 + n - 1):
        put(x, y0 + 5, hull_d)
    for y, x_from, x_to in ((y0 + 4, x0 - 6, x0), (y0 + 5, x0 - 13, x0 + 2), (y0 + 6, x0 - 19, x0 - 5)):
        x = x_from
        while x < x_to:
            ln = rng.randint(2, 4)
            for k in range(min(ln, x_to - x)):
                put(x + k, y, foam)
            x += ln + rng.randint(1, 3)
    for y in range(y0 + 6, y0 + 11):
        for x in range(x0 + 3, x0 + n - 3):
            if (x - x0) % 4 and rng.random() < 0.45 - (y - y0 - 6) * 0.08:
                put(x, y, mix(glass[1], C("2a2258"), 0.35 + (y - y0 - 6) * 0.1))


# ------------------------------------------------------------------ output

def to565(c):
    r5 = (c[0] * 31 + 127) // 255
    g6 = (c[1] * 63 + 127) // 255
    b5 = (c[2] * 31 + 127) // 255
    return ((r5 * 255 + 15) // 31, (g6 * 255 + 31) // 63, (b5 * 255 + 15) // 31)


def save():
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    ppm = os.path.join(BUILD, "eiffel_%dx%d.ppm" % (W, H))
    colours = set()
    buf = bytearray()
    for row in img:
        for c in row:
            q = to565(c)
            colours.add(q)
            buf += bytes(q)
    with open(ppm, "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (W, H))
        f.write(buf)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ppm,
                    "-vf", "scale=iw*%d:ih*%d:flags=neighbor,format=yuvj444p" % (SCALE, SCALE),
                    "-q:v", "1", "-qmin", "1", OUT_JPG], check=True)
    if os.environ.get("KEEP_BUILD") != "1":
        shutil.rmtree(BUILD)
    print("%s  (%dx%d, %d RGB565 colours)" % (OUT_JPG, W * SCALE, H * SCALE, len(colours)))


def main():
    rng = random.Random(1889)   # the year the tower opened
    paint_sky()
    paint_stars(rng)
    paint_moon()
    paint_cloud(rng, 196, 330, 88, 6.0, ("261f5e", "33296f", "7a4596", "c7709f"))
    paint_cloud(rng, -12, 112, 120, 7.0, ("3b2872", "4a3282", "a65597", "ec92a4"))
    paint_cloud(rng, 200, 334, 140, 6.0, ("573180", "673a8a", "c8618e", "ffab96"))
    paint_cloud(rng, -8, 96, 152, 3.5, ("75398a", "84418f", "e07a8c", "ffc49a"))
    paint_far_city(rng)
    paint_invalides(62, 201)
    paint_montparnasse(258, 201, rng)
    paint_mid_city(rng)
    paint_beams()
    draw_tower(rng)
    paint_trees(rng)
    paint_quay()
    paint_lamps()
    paint_water(rng)
    paint_boat(rng)
    save()


if __name__ == "__main__":
    main()
