#!/usr/bin/env python3
"""SNES-style pixel art: the Eiffel Tower at sunset over the Seine.

Pure standard library. Renders a native 256x224 frame, snaps every colour to
the SNES 15-bit (BGR555) gamut, verifies the hardware-style limits
(<=128 colours total, <=16 colours per 8x8 tile) and writes an indexed PNG.

usage: python3 src/eiffel.py [out.png] [--preview N]
"""
import math
import os
import random
import struct
import sys
import zlib

W, H = 256, 224


def c(hexstr):
    """Hex colour -> RGB snapped to 5 bits per channel (SNES CGRAM)."""
    v = int(hexstr.lstrip('#'), 16)

    def q(ch):
        x5 = round(ch * 31 / 255)
        return (x5 << 3) | (x5 >> 2)
    return (q((v >> 16) & 255), q((v >> 8) & 255), q(v & 255))


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dith(x, y, p):
    """Ordered-dither test: True with probability p (0..1)."""
    return BAYER[y & 3][x & 3] < p * 16


# ---------------------------------------------------------------- palette
SKY = [c(h) for h in (
    '#120a34', '#1a0e44', '#261254', '#341864', '#481e74', '#602680',
    '#7c2e8a', '#98368c', '#b4408a', '#cc4e86', '#e0627e', '#ec7a74',
    '#f4966a', '#f8b262', '#f8ca6a', '#f8e08c')]
SKY_EDGES = [16, 30, 42, 54, 65, 76, 86, 95, 104, 112, 120, 127, 134, 141, 148]

STAR = c('#f8f8f0')
STAR_DIM = c('#a490d8')
MOON = c('#f8f0d8')
MOON_SH = c('#c8b0c8')
SUN_CORE = c('#f8f8d8')
SUN = c('#f8e8a0')
SUN_RIM = c('#f8d070')

CLOUD = [c(h) for h in ('#381a60', '#5a2676', '#8a3886', '#c25288',
                        '#f08680', '#f8c890')]

FAR = c('#b05888')
FAR_LIT = c('#d87890')
MID = c('#7a306e')
MID_ROOF = c('#58225e')
WIN = c('#f8c868')
WIN_DIM = c('#c07850')
GOLD = [c('#7a4038'), c('#c88038'), c('#f8c060')]

T = [c(h) for h in ('#140a1c', '#2e1630', '#4a2238', '#6c3240', '#944840',
                    '#c06840', '#e89850', '#f8d088')]
LAMP = c('#f8f0b0')

TREE = [c(h) for h in ('#120e22', '#1c2232', '#283c3c', '#3e5a40',
                       '#6a7a44', '#b89058')]

QUAY = [c(h) for h in ('#2c1840', '#4a2a5c', '#6c4070', '#9a6080',
                       '#d09090')]
POST = c('#1a1226')

WA = [c(h) for h in ('#160c30', '#221246', '#30185a', '#46206a', '#622a76',
                     '#86387c', '#ae4c7c', '#dc7872', '#f8b46e', '#f8e8b0')]

BOAT = {
    'o': c('#24182e'), 'w': c('#e0c8d0'), 'f': c('#f8f0e8'),
    's': c('#987090'), 'r': c('#b83848'), 'g': c('#4a3a78'),
    'y': WIN, 'k': c('#c8a0c0'),
}

img = [[SKY[0]] * W for _ in range(H)]


def put(x, y, col):
    if 0 <= x < W and 0 <= y < H and col is not None:
        img[y][x] = col


# ---------------------------------------------------------------- sky
SUN_X, SUN_Y, SUN_R = 204, 150, 16


def sky_index(x, y):
    idx = sum(1 for e in SKY_EDGES if e <= y)
    for e in SKY_EDGES:                 # 4-row ordered-dither seam
        if e - 2 <= y < e + 2:
            lower = sum(1 for f in SKY_EDGES if f < e)
            p = (y - (e - 2) + 0.5) / 4
            idx = lower + 1 if dith(x, y, p) else lower
            break
    # warm horizon glow around the sun, spread wide like real dusk
    dx = (x - SUN_X) / 1.9
    dy = y - SUN_Y
    d = math.hypot(dx, dy)
    g = (SUN_R + 34 - d) / 11
    if g > 0:
        boost = int(g + BAYER[y & 3][x & 3] / 16)
        idx += min(boost, 3)
    return min(idx, len(SKY) - 1)


def draw_sky():
    for y in range(H):
        for x in range(W):
            img[y][x] = SKY[sky_index(x, y)]


def draw_stars():
    rnd = random.Random(7)
    for _ in range(70):
        x = rnd.randrange(W)
        y = int(rnd.random() ** 1.7 * 72)
        if y < 40 or rnd.random() < 0.5:
            put(x, y, STAR if rnd.random() < 0.3 else STAR_DIM)
    for (x, y) in ((70, 12), (164, 20), (230, 9), (14, 50), (196, 36)):
        put(x, y, STAR)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(x + dx, y + dy, STAR_DIM)


def draw_moon():
    mx, my, r = 36, 28, 8
    for y in range(my - r - 1, my + r + 2):
        for x in range(mx - r - 1, mx + r + 2):
            if (x - mx) ** 2 + (y - my) ** 2 <= r * r:
                d2 = (x - mx - 5) ** 2 + (y - my + 3) ** 2
                if d2 > (r - 1) ** 2:
                    edge = d2 <= (r + 0.6) ** 2
                    put(x, y, MOON_SH if edge else MOON)
    put(31, 31, MOON_SH)
    put(30, 26, MOON_SH)


def draw_sun():
    for y in range(SUN_Y - SUN_R, SUN_Y + SUN_R + 1):
        for x in range(SUN_X - SUN_R, SUN_X + SUN_R + 1):
            d = math.hypot(x + 0.5 - SUN_X, y + 0.5 - SUN_Y)
            if d <= SUN_R:
                if d > SUN_R - 1.3:
                    col = SUN_RIM
                elif d < SUN_R - 6 and y < SUN_Y + 2:
                    col = SUN_CORE
                else:
                    col = SUN
                put(x, y, col)


# ---------------------------------------------------------------- clouds
def cloud_mask(x0, x1, yb, rmin, rmax, seed):
    """Puffy cloud: a base row of big puffs with smaller puffs stacked on
    top (drawn in front so their sunlit undersides show).
    Returns {(x, y): (puff_id, nx, ny)} for the front-most puff per pixel."""
    rnd = random.Random(seed)
    puffs = []
    for row, (scale, lift) in enumerate(((1.0, 0.45), (0.6, 1.25))):
        x = x0 + row * rmin
        while x < x1:
            t = (x - x0) / (x1 - x0)
            taper = max(0.0, math.sin(math.pi * t)) ** 0.6
            r = (rmin + rnd.random() * (rmax - rmin)) * scale * (0.4 + 0.6 * taper)
            if r >= 2:
                puffs.append((x, yb - r * lift, r))
            x += rnd.uniform(0.9, 1.4) * r + 2
    mask = {}
    for pid, (px, py, r) in enumerate(puffs):
        for y in range(int(py - r) - 1, yb + 1):
            for xx in range(int(px - r * 1.5) - 1, int(px + r * 1.5) + 2):
                nx = (xx + 0.5 - px) / (1.5 * r)
                ny = (y + 0.5 - py) / r
                if nx * nx + ny * ny <= 1:
                    mask[(xx, y)] = (pid, nx, ny)
    return mask


def draw_cloud(mask, tone, warm):
    """Lit from below by the setting sun: bright undersides, dusky tops."""
    for (x, y), (pid, nx, ny) in mask.items():
        if not (0 <= x < W and 0 <= y < H):
            continue
        lum = 0.25 * nx + 0.95 * ny
        if (x, y + 1) not in mask:
            lvl = 5 if warm else 4
        elif (x, y + 2) not in mask:
            lvl = 4 if warm else 3
        elif lum > 0.5:
            lvl = 3
        else:
            lvl = 2
        if (x, y - 1) not in mask or ((x, y - 2) not in mask and dith(x, y, 0.5)):
            lvl = 1
        if (x + 1, y) not in mask and lvl == 2:
            lvl = 3
        put(x, y, CLOUD[max(0, min(5, lvl + tone))])


def draw_streak(x0, x1, y, rows, lvl_top, lvl_bot):
    for r in range(rows):
        inset = 2 * (rows - 1 - r) if r < rows - 1 else 0
        for x in range(x0 + inset + (rows - r), x1 - inset - (rows - r)):
            put(x, y + r, CLOUD[lvl_bot if r == rows - 1 else lvl_top])


def draw_clouds():
    draw_cloud(cloud_mask(-14, 84, 60, 6, 10, 3), -1, False)
    draw_cloud(cloud_mask(150, 270, 44, 5, 9, 11), -1, False)
    draw_cloud(cloud_mask(96, 186, 86, 6, 10, 5), 0, False)
    draw_cloud(cloud_mask(-20, 64, 104, 6, 11, 21), 0, False)
    draw_cloud(cloud_mask(168, 272, 112, 6, 11, 9), 0, True)
    draw_streak(56, 112, 126, 2, 2, 3)
    draw_streak(132, 206, 120, 2, 2, 4)
    draw_streak(176, 246, 138, 2, 3, 4)
    draw_streak(62, 116, 139, 1, 3, 3)


BIRDS = (
    (["#...#", ".#.#.", "..#.."], 166, 94),
    (["##.##", "..#.."], 176, 100),
    (["#...#", ".#.#.", "..#.."], 158, 103),
    (["##.##", "..#.."], 184, 92),
)


def draw_birds():
    for rows, bx, by in BIRDS:
        for j, line in enumerate(rows):
            for i, ch in enumerate(line):
                if ch == '#':
                    put(bx + i, by + j, CLOUD[0])


# ---------------------------------------------------------------- skyline
SACRE_COEUR = [
    "...............#................",
    "...............#................",
    "..............###...............",
    "..............###...............",
    ".............#####..............",
    "............#######.............",
    "...........#########............",
    "..........###########.......#...",
    "..........###########......###..",
    "..........###########......###..",
    "...........#########.......###..",
    "...........#.#.#.#.#.......###..",
    "....#......#.#.#.#.#...#...###..",
    "...###.....#########..###..###..",
    "..#####...###########.###..###..",
    "..#####..#############.#########",
    "..##.##..#############.#########",
    "..##.##.##############.##.##.###",
    ".############################.##",
    "################################",
    "################################",
    "################################",
]


def draw_far():
    rnd = random.Random(42)
    top = [0] * W
    x = 0
    while x < W:
        bw = rnd.randint(5, 14)
        h = rnd.randint(152, 158)
        for i in range(bw):
            if x + i < W:
                top[x + i] = h
        x += bw
    x = 0                                    # Montmartre: roofs up the hill
    while x < 76:
        bw = rnd.randint(3, 6)
        hill = min(140 + 18 * (1 - math.exp(-((xx - 33) / 24) ** 2))
                   for xx in range(x, x + bw))
        h = int(hill) + rnd.randint(-1, 1)
        for i in range(bw):
            top[x + i] = min(top[x + i], h)
        x += bw
    for sx in (92, 140, 170, 248):           # church steeples
        for k in range(10):
            for dx in range(-(k // 4), k // 4 + 1):
                if 0 <= sx + dx < W:
                    top[sx + dx] = min(top[sx + dx], 146 + k)
    shapes = []
    # Sacre-Coeur on the hilltop
    for j, line in enumerate(SACRE_COEUR):
        for i, ch in enumerate(line):
            if ch == '#':
                shapes.append((16 + i, 120 + j))
    for (x, y) in shapes:
        put(x, y, FAR)
    for x in range(W):
        for y in range(top[x], 190):
            put(x, y, FAR)
    # rim light on edges that face the setting sun
    for y in range(118, 190):
        for x in range(W - 1):
            if img[y][x] == FAR and img[y][x + 1] != FAR and img[y][x + 1] != FAR_LIT:
                put(x, y, FAR_LIT)
            elif img[y][x] == FAR and abs(x - SUN_X) < 60 and img[y - 1][x] not in (FAR, FAR_LIT):
                put(x, y, FAR_LIT)


def draw_mid():
    rnd = random.Random(1889)
    x = -4
    while x < W:
        bw = rnd.randint(16, 30)
        face = rnd.randint(165, 170)
        roof_h = rnd.choice((3, 4, 4, 5))
        for y in range(face - roof_h, 192):
            for i in range(bw):
                px = x + i
                if y < face:
                    k = y - (face - roof_h)
                    inset = roof_h - k
                    if i < inset or i >= bw - inset:
                        continue
                    put(px, y, MID_ROOF)
                else:
                    put(px, y, MID)
        for i in range(2, bw - 2, rnd.randint(5, 8)):    # chimneys
            put(x + i, face - roof_h - 1, MID_ROOF)
            put(x + i + 1, face - roof_h - 1, MID_ROOF)
        for y in range(face - roof_h + 1, face, 2):      # dormer lights
            for i in range(3, bw - 3, 4):
                if rnd.random() < 0.18:
                    put(x + i, y, WIN)
        for y in range(face + 2, 190, 3):                # windows
            for i in range(2, bw - 2, 3):
                r = rnd.random()
                if r < 0.16:
                    put(x + i, y, WIN)
                elif r < 0.24:
                    put(x + i, y, WIN_DIM)
        x += bw
    # Les Invalides golden dome
    dx0, top = 236, 140
    for y in range(top - 10, 166):
        for x in range(dx0 - 10, dx0 + 11):
            fx = x + 0.5 - dx0
            col = None
            if y >= 154 and abs(fx) <= 9:
                col = MID if (x % 3) else MID_ROOF
                if y % 4 == 2 and x % 3 == 1:
                    col = WIN if (x * 7 + y) % 5 == 0 else MID_ROOF
            elif y >= 149 and abs(fx) <= 7:
                col = MID_ROOF if x % 2 else MID
            elif y < 149 and (fx / 7) ** 2 + ((y + 0.5 - 149) / 9) ** 2 <= 1:
                s = fx / 7
                col = GOLD[2] if s > 0.35 else GOLD[1] if s > -0.4 else GOLD[0]
                if y % 3 == 0 and abs(fx) < 6 and x % 2 == 0:
                    col = GOLD[0] if s < 0.35 else GOLD[1]
            elif abs(fx) <= 1 and top - 2 <= y < 141 and (fx > 0 or y >= top + 1):
                col = GOLD[2] if fx > 0 else GOLD[1]
            elif fx > 0 and fx < 1 and top - 9 <= y < top - 2:
                col = GOLD[2]
            if col is not None:
                put(x, y, col)


# ---------------------------------------------------------------- tower
CX = 120.0
YG = 182
HT = 174
W0 = 44.0


def tw(y):
    h = (YG - (y + 0.5)) / HT
    return W0 * math.exp(-3.2 * h)


def lattice(x, y, sp):
    a = (x + y) % sp
    b = (x - y) % sp
    if a == 0 or b == 0:
        return 'm'
    if a == sp // 2 and b == sp // 2:
        return 'h'
    return 'd'


def leg_px(x, y, fx, w, inner):
    d = abs(fx)
    right = fx > 0
    u = w - d
    v = d - inner
    if u < 1:
        return T[6] if right else T[1]
    if u < 2:
        return T[5] if right else T[2]
    if inner > 0:
        if v < 1:
            return T[1] if right else T[5]
        if v < 2:
            return T[2] if right else T[4]
    if w - inner < 6:
        xl = math.ceil(CX - w - 0.5) + 2
        xr = math.floor(CX + w - 0.5) - 2
        n = xr - xl + 1
        if inner > 0 or n < 2:
            return T[4] if right else T[3]
        per = 2 * (n - 1)
        t = y % per
        p = t if t < n else per - t
        if x - xl in (p, n - 1 - p) or y % 6 == 0:
            return T[4] if right else T[3]
        return T[1] if fx < 0 else T[2]
    if y % 8 == 0:
        return T[4] if right else T[3]
    k = lattice(x, y, 4)
    if k == 'm':
        return T[4] if right else T[3]
    if k == 'h':
        return None
    return T[1]


def tower_px(x, y):
    fx = x + 0.5 - CX
    d = abs(fx)
    right = fx > 0
    w = tw(y)
    if y >= 151:                                   # legs + grand arch
        if d > w:
            return None
        inner = 0.6 * w
        if d >= inner:
            return leg_px(x, y, fx, w, inner)
        a = 0.6 * tw(YG - 1)
        b = YG - 156
        r = math.hypot(fx / a, (YG - (y + 0.5)) / b)
        if r < 1.0:
            return None
        if r < 1.045:
            return T[5] if right else T[3]
        if r < 1.09:
            return T[1]
        k = lattice(x, y, 4)
        if k == 'm':
            return T[4] if right else T[3]
        if k == 'h':
            return None
        return T[1]
    if 120 <= y <= 142:                            # between 1st and 2nd
        if d > w:
            return None
        inner = 0.58 * w
        if d < inner:
            return None
        return leg_px(x, y, fx, w, inner)
    if 36 <= y <= 112:                             # upper shaft
        if d > w:
            return None
        if y >= 86:
            inner = 0.58 * w * (y - 86) / (112 - 86)
            if d < inner - 0.5:
                return None
        else:
            inner = 0
        if y in (84, 85):
            return (T[6] if right else T[4]) if y == 84 else T[1]
        if w < 3.2:
            u = w - d
            if u < 1:
                return T[6] if right else T[1]
            return T[4] if right else T[2] if fx < -1 else T[3]
        return leg_px(x, y, fx, w, inner)
    return None


def platform(y0, kinds, pw, lit_seed):
    rnd = random.Random(lit_seed)
    for i, kind in enumerate(kinds):
        y = y0 + i
        for x in range(int(CX - pw) - 1, int(CX + pw) + 2):
            fx = x + 0.5 - CX
            if abs(fx) > pw:
                continue
            s = fx / pw
            edge_r = fx > pw - 1
            edge_l = fx < -pw + 1
            mem = T[5] if s > 0.3 else T[3] if s < -0.3 else T[4]
            col = None
            if kind == 'rail':
                col = (T[5] if s > 0.3 else T[3]) if x % 2 == 0 else None
            elif kind == 'top':
                col = T[7] if edge_r else T[6] if s > 0 else T[5] if s > -0.6 else T[4]
            elif kind == 'beam':
                col = T[2] if s > 0.3 else T[1]
            elif kind == 'under':
                col = T[0]
            elif kind in ('arch', 'archlit'):
                p = x % 4
                if p in (1, 2):
                    col = T[0]
                    if kind == 'archlit' and rnd.random() < 0.45:
                        col = WIN
                else:
                    col = mem
            elif kind == 'win':
                col = mem if x % 2 == 0 else (WIN if rnd.random() < 0.6 else T[0])
            if edge_r and kind not in ('rail', 'top'):
                col = T[6]
            if edge_l and kind not in ('rail',):
                col = T[1]
            put(x, y, col)


def draw_tower():
    for y in range(36, YG):
        for x in range(int(CX - W0) - 2, int(CX + W0) + 3):
            put(x, y, tower_px(x, y))
    platform(143, ['rail', 'top', 'beam', 'arch', 'archlit', 'beam', 'under', 'under'],
             tw(150) + 3, 1)
    platform(113, ['rail', 'top', 'beam', 'win', 'beam', 'under', 'under'],
             tw(119) + 2.5, 2)
    platform(30, ['rail', 'top', 'win', 'win', 'beam', 'under'], tw(35) + 2.5, 3)
    # cupola, beacon and antenna
    cup = {29: 4, 28: 3, 27: 3, 26: 3, 25: 2, 24: 2, 23: 2, 22: 1}
    for y, hw in cup.items():
        for x in range(120 - hw, 120 + hw):
            fx = x + 0.5 - CX
            col = T[1] if x == 120 - hw else T[6] if x == 119 + hw else (T[4] if fx > 0 else T[3])
            put(x, y, col)
    put(119, 21, LAMP)
    put(120, 21, LAMP)
    for (x, y) in ((118, 21), (121, 21), (119, 20), (120, 20)):
        put(x, y, WA[8])
    for y in range(8, 20):
        put(120, y, T[5])
        if y >= 14:
            put(119, y, T[2])


# ---------------------------------------------------------------- foreground
def draw_trees():
    rnd = random.Random(99)
    circles = []
    for (x0, x1, yc) in ((-8, 86, 177), (156, 266, 177)):
        x = x0
        while x < x1:
            r = rnd.uniform(6, 9.5)
            circles.append((x, yc + rnd.uniform(-3, 2), r))
            x += rnd.uniform(6, 9)
        x = x0 + 4
        while x < x1:
            r = rnd.uniform(5, 7)
            circles.append((x, yc + 6 + rnd.uniform(-1, 1), r))
            x += rnd.uniform(7, 10)
    for x in range(84, 160, 5):                      # low hedge under the arch
        circles.append((x + rnd.uniform(-1, 1), 184, rnd.uniform(3, 4.2)))
    for (cx, cy, r) in circles:
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                if dx * dx + dy * dy > r * r or y >= 186:
                    continue
                lum = (dx * 0.75 - dy * 0.65) / r      # lit from upper right
                lum = lum * 2.1 + 1.6
                if r < 4.5:
                    lum -= 1.0
                lvl = int(lum + BAYER[y & 3][x & 3] / 16)
                lvl = max(0, min(4, lvl))
                rim = dx * dx + dy * dy > (r - 1.2) ** 2 and dx > 0 and dy < 0
                put(x, y, TREE[5] if rim and r > 4.5 and lvl >= 3 else TREE[lvl])


def draw_quay():
    for y in range(186, 194):
        for x in range(W):
            if y == 186:
                col = QUAY[4] if x % 2 or x > 140 else QUAY[3]
            elif y == 187:
                col = QUAY[2]
            elif y == 193:
                col = QUAY[0]
            else:
                row = (y - 188) // 3
                joint = (y - 188) % 3 == 2 or (x + row * 5) % 10 == 0
                col = QUAY[1] if joint else QUAY[2]
                if not joint and (x + y) % 7 == 0:
                    col = QUAY[3] if x > 128 else QUAY[1]
            put(x, y, col)
    for lx in (10, 46, 82, 158, 194, 230):            # lamp posts
        for y in range(175, 186):
            put(lx, y, POST)
        put(lx - 1, 185, POST)
        put(lx + 1, 185, POST)
        put(lx - 1, 174, LAMP)
        put(lx, 174, LAMP)
        put(lx - 1, 173, WA[9])
        put(lx, 173, WA[8])
        put(lx - 1, 175, POST)
        put(lx, 172, POST)


def draw_river():
    rnd = random.Random(5)
    for y in range(194, H):
        t = (y - 194) / (H - 194)
        base = 6.2 - t * 4.2
        for x in range(W):
            lvl = int(base + BAYER[y & 3][x & 3] / 16 - 0.5)
            if y < 196:
                lvl = 1 if y == 194 else 2
            img[y][x] = WA[max(0, min(9, lvl))]
        if y >= 196:                                  # horizontal ripples
            x = rnd.randint(-10, 0)
            while x < W:
                ln = rnd.randint(3, 14)
                lvl = int(base + 0.5) + rnd.choice((1, 1, -1, -1, 2))
                if y % 2 == 0:
                    for i in range(ln):
                        put(x + i, y, WA[max(0, min(8, lvl))])
                x += ln + rnd.randint(4, 18)
    # tower reflection
    for y in range(198, H):
        if y % 4 == 3:
            continue
        yt = YG - 1 - (y - 198) * 1.6
        if yt < 40:
            break
        w = tw(int(yt))
        wob = round(math.sin(y * 1.3) * 1.5)
        inner = 0.6 * w if yt > 151 else 0.58 * w if yt > 120 else 0
        if 143 <= yt <= 150 or 113 <= yt <= 119:
            w += 2
            inner = 0
        for x in range(int(CX - w), int(CX + w) + 1):
            d = abs(x + 0.5 - CX)
            if d <= w and d >= inner:
                put(x + wob, y, WA[1] if d < w - 1 else WA[2])
    # sun glitter
    for y in range(195, H):
        hw = 7 + (y - 195) * 0.45
        wob = rnd.randint(-2, 2)
        if y % 2:
            continue
        x = int(SUN_X - hw) + wob
        while x < SUN_X + hw:
            ln = rnd.randint(2, 7)
            for i in range(ln):
                px = x + i
                if px >= SUN_X + hw:
                    break
                dc = abs(px - SUN_X) / hw
                put(px, y, WA[9] if dc < 0.35 else WA[8] if dc < 0.75 else WA[7])
            x += ln + rnd.randint(1, 4)
    # lamp reflections
    for lx in (10, 46, 82, 158, 194, 230):
        for y in range(196, 212):
            if y % 2 == 0 and rnd.random() < 0.8:
                ln = 1 if y < 202 else 2
                o = rnd.randint(-1, 0)
                for i in range(ln):
                    put(lx + o + i, y, WA[9] if y < 202 else WA[8])


def draw_boat():
    bx, wl = 14, 210
    L = 58
    o, w_, f, s, r, g, yw, k = (BOAT[ch] for ch in 'owfsrgyk')
    rnd = random.Random(3)
    # hull: bow at the left rises above the waterline
    hull = {205: (0, L), 206: (1, L), 207: (2, L), 208: (3, L - 1), 209: (5, L - 2)}
    for y, (a, b) in hull.items():
        for i in range(a, b):
            x = bx + i
            col = f if y == 205 else w_ if y in (206, 207) else r if y == 208 else o
            if y in (206, 207) and i > L - 12:
                col = s
            if i == a and y < 209:
                col = o
            if i == b - 1:
                col = s if y < 208 else o
            put(x, y, col)
    # glass cabin with lit windows
    for y in range(199, 205):
        for i in range(10, L - 5):
            x = bx + i
            if y == 199:
                if 11 < i < L - 7:
                    put(x, y, k)
                continue
            if y == 200:
                put(x, y, k if i > 10 else o)
                continue
            if y == 204:
                put(x, y, o)
                continue
            if i == 10 or i == L - 6 or (i - 10) % 4 == 0:
                put(x, y, o)
            else:
                put(x, y, yw if (y in (201, 202) and rnd.random() < 0.55) else g)
    # bow rail + flag
    for i in range(3, 10, 2):
        put(bx + i, 204, o)
    put(bx + L - 2, 201, o)
    put(bx + L - 2, 202, o)
    put(bx + L - 2, 203, o)
    put(bx + L - 1, 201, r)
    # wake and reflection
    for i in range(0, 34):
        y = wl + (i // 9)
        if (i * 7) % 5 < 3:
            put(bx + L - 1 + i, y, WA[9] if i < 12 else WA[8])
    for i in range(-3, 4):
        put(bx + 2 + i, wl, WA[9] if i % 2 else WA[8])
    for y in range(wl + 1, wl + 5):
        for i in range(8, L - 4):
            if (i + y) % 3 and y % 2:
                put(bx + i, y, WA[1])


# ---------------------------------------------------------------- SNES limits
def enforce_limits():
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
                rare = min(counts, key=counts.get)
                near = min((q for q in counts if q != rare),
                           key=lambda q: sum((a - b) ** 2 for a, b in zip(q, rare)))
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        if img[y][x] == rare:
                            img[y][x] = near
                fixes += 1
    return fixes


def report():
    colours = {p for row in img for p in row}
    worst = 0
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            n = len({img[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8)})
            worst = max(worst, n)
    return len(colours), worst


def write_png(path, pixels, scale=1):
    pal = sorted({p for row in pixels for p in row})
    assert len(pal) <= 256
    idx = {p: i for i, p in enumerate(pal)}
    rows = []
    for row in pixels:
        line = bytes(idx[p] for p in row for _ in range(scale))
        rows.extend([b'\x00' + line] * scale)
    raw = b''.join(rows)

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
    png = (b'\x89PNG\r\n\x1a\n' +
           chunk(b'IHDR', struct.pack('>IIBBBBB', len(pixels[0]) * scale,
                                      len(pixels) * scale, 8, 3, 0, 0, 0)) +
           chunk(b'PLTE', b''.join(bytes(p) for p in pal)) +
           chunk(b'IDAT', zlib.compress(raw, 9)) +
           chunk(b'IEND', b''))
    with open(path, 'wb') as fh:
        fh.write(png)


def main():
    args = sys.argv[1:]
    out = 'output/eiffel_tower_snes.png'
    preview = None
    if '--preview' in args:
        i = args.index('--preview')
        preview = args[i + 1]
        del args[i:i + 2]
    if args:
        out = args[0]

    draw_sky()
    draw_stars()
    draw_moon()
    draw_sun()
    draw_clouds()
    draw_birds()
    draw_far()
    draw_mid()
    draw_tower()
    draw_trees()
    draw_quay()
    draw_river()
    draw_boat()

    fixes = enforce_limits()
    total, worst = report()
    assert total <= 128 and worst <= 16
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    write_png(out, img)
    print(f'{out}: {W}x{H}, {total} colours, max {worst}/tile, {fixes} tile fixes')
    if preview:
        write_png(preview, img, 4)


if __name__ == '__main__':
    main()
