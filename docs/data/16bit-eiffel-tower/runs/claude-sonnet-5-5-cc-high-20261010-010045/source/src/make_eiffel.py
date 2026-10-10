#!/usr/bin/env python3
"""Eiffel Tower, SNES style: 256x224, <=128 colours, 8x8 tiles with <=16 colours each.

Everything is drawn procedurally into an RGB canvas (colours snapped to the SNES's
5-bit-per-channel space), then the tile/palette limits are enforced and the result is
written as an indexed PNG using only the standard library.
"""
import math, random, struct, sys, zlib
from collections import Counter

W, H = 256, 224
CX = 128          # tower axis (between pixel columns 127 and 128)
GY = 198          # ground row the tower stands on
HORIZON = 190


def C(r, g, b):
    """Snap to 15-bit SNES colour space (5 bits per channel)."""
    return (r & 0xF8, g & 0xF8, b & 0xF8)


img = [[C(0, 0, 0)] * W for _ in range(H)]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bay(x, y):
    return (BAYER[y & 3][x & 3] + 0.5) / 16


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, c)


def blob(cx, cy, rx, ry, tones, base=None, light=(-0.55, -0.83),
         th=(-0.45, 0.1, 0.6), dith=0.25):
    """Ellipse with pseudo-spherical, dithered 3-4 tone shading."""
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        if base is not None and y > base:
            continue
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1:
                n = dx * light[0] + dy * light[1] + (bay(x, y) - 0.5) * dith
                i = sum(1 for t in th if n > t)
                put(x, y, tones[min(i, len(tones) - 1)])


# ----------------------------------------------------------------------------- sky
SKY = [C(40, 80, 168), C(56, 104, 192), C(80, 132, 208), C(112, 160, 224),
       C(152, 188, 232), C(200, 204, 232), C(240, 200, 208), C(248, 184, 152),
       C(248, 168, 112), C(248, 200, 120)]
SUNX, SUNY = 46, 174
SUN_CORE, SUN_RIM = C(255, 252, 216), C(255, 232, 144)

for y in range(H):
    for x in range(W):
        s = 9 * (y / 188.0) ** 1.5
        d = math.hypot(x - SUNX, (y - SUNY) * 1.25)
        s += 6.5 * max(0.0, 1 - d / 100.0) ** 2
        s = min(s, 9.0)
        b = min(int(s), 8)
        f = min(1.0, max(0.0, (s - b - 0.2) / 0.6))
        img[y][x] = SKY[b + 1] if f > bay(x, y) else SKY[b]

# sun
for y in range(H):
    for x in range(W):
        d = math.hypot(x + 0.5 - SUNX, y + 0.5 - SUNY)
        if d < 10:
            put(x, y, SUN_CORE)
        elif d < 13:
            put(x, y, SUN_RIM if d < 12 or bay(x, y) > 0.5 else img[y][x])

# ----------------------------------------------------------------------------- clouds
CLOUD_HI = [C(248, 248, 255), C(208, 224, 248), C(160, 184, 224), C(120, 144, 200)]
CLOUD_LO = [C(255, 240, 216), C(248, 200, 176), C(208, 144, 160), C(152, 104, 136)]


def cloud(cx, base, puffs, tones):
    for dx, dy, rx, ry in puffs:
        blob(cx + dx, base - dy, rx, ry, tones, base=base)


cloud(40, 52, [(-20, 6, 14, 8), (18, 6, 15, 8), (0, 9, 22, 10), (-8, 17, 13, 10),
               (10, 19, 12, 9), (-22, 13, 8, 6)], CLOUD_HI)
cloud(208, 70, [(-14, 4, 12, 6), (12, 4, 13, 6), (0, 8, 15, 8), (-3, 13, 9, 7)], CLOUD_HI)
cloud(96, 28, [(-8, 3, 10, 4), (8, 3, 11, 4), (0, 6, 9, 5)], CLOUD_HI)
cloud(236, 26, [(-6, 3, 10, 4), (6, 3, 9, 4), (0, 6, 8, 5)], CLOUD_HI)
cloud(28, 118, [(-14, 3, 16, 5), (14, 3, 18, 5), (0, 6, 20, 6), (-6, 10, 10, 6)], CLOUD_LO)
cloud(226, 126, [(-14, 3, 16, 5), (12, 3, 20, 5), (0, 6, 18, 6), (8, 10, 9, 6)], CLOUD_LO)
cloud(150, 150, [(-30, 2, 28, 4), (10, 2, 34, 4), (-10, 5, 22, 5)], CLOUD_LO)
cloud(30, 160, [(-16, 2, 24, 4), (14, 2, 28, 4), (0, 5, 20, 5)], CLOUD_LO)
cloud(236, 168, [(-20, 2, 24, 4), (12, 2, 22, 4), (0, 5, 18, 5)], CLOUD_LO)

BIRD = C(72, 56, 104)
for bx, by in [(70, 70), (80, 64), (60, 78), (186, 40), (194, 46)]:
    for k in range(1, 4):
        put(bx - k, by - (k // 2 + (1 if k == 3 else 0)) + 1, BIRD)
        put(bx + k, by - (k // 2 + (1 if k == 3 else 0)) + 1, BIRD)
    put(bx, by + 1, BIRD)

# ----------------------------------------------------------------------------- skyline
rnd = random.Random(11)


def row_of_buildings(base, hmin, hmax, wall, wall_l, wall_d, roof, roof_hi, win,
                     tall_win, chim):
    x = -4
    while x < W:
        w = rnd.randint(9, 17)
        h = rnd.randint(hmin, hmax)
        top = base - h
        rect(x, top + 3, x + w - 1, base, wall)
        rect(x, top + 3, x, base, wall_l)
        rect(x + w - 1, top + 3, x + w - 1, base, wall_d)
        for r in range(4):
            inset = max(0, 2 - r)
            rect(x + inset - (0 if r else -0), top + r, x + w - 1 - inset, top + r,
                 roof_hi if r == 0 else roof)
        if rnd.random() < 0.6:
            cx0 = x + rnd.randint(2, max(2, w - 5))
            rect(cx0, top - 3, cx0 + 1, top, chim)
            put(cx0, top - 3, roof_hi)
        for wy in range(top + 5, base - 1, 4):
            for wx in range(x + 2, x + w - 2, 3):
                put(wx, wy, win)
                if tall_win:
                    put(wx, wy + 1, win)
        x += w


# far, hazy layer
row_of_buildings(HORIZON, 9, 16, C(184, 160, 192), C(200, 176, 200), C(160, 136, 176),
                 C(144, 128, 176), C(168, 152, 192), C(160, 136, 176), False, C(152, 128, 168))

# Les Invalides dome (gold) behind the near row
DX = 212
GOLD = [C(255, 240, 150), C(248, 208, 88), C(216, 160, 56), C(160, 104, 48)]
rect(DX - 17, HORIZON - 9, DX + 17, HORIZON, C(216, 184, 168))
rect(DX - 17, HORIZON - 9, DX - 17, HORIZON, C(232, 204, 184))
rect(DX + 17, HORIZON - 9, DX + 17, HORIZON, C(176, 144, 152))
rect(DX - 17, HORIZON - 10, DX + 17, HORIZON - 10, C(240, 216, 192))
for px in range(DX - 15, DX + 16, 4):
    rect(px, HORIZON - 7, px, HORIZON - 1, C(176, 144, 152))
rect(DX - 8, HORIZON - 16, DX + 8, HORIZON - 10, C(224, 192, 176))
rect(DX + 8, HORIZON - 16, DX + 8, HORIZON - 10, C(176, 144, 152))
for px in range(DX - 6, DX + 7, 3):
    rect(px, HORIZON - 15, px, HORIZON - 12, C(120, 96, 128))
blob(DX, HORIZON - 16, 9, 12, GOLD, base=HORIZON - 16, light=(-0.6, -0.7),
     th=(-0.5, 0.0, 0.55))
for k in (-4, 0, 4):
    for y in range(HORIZON - 26, HORIZON - 16):
        c = img[y][DX + k]
        if c in GOLD[:3]:
            put(DX + k, y, GOLD[GOLD.index(c) + 1])
rect(DX - 1, HORIZON - 31, DX, HORIZON - 26, GOLD[1])
rect(DX, HORIZON - 31, DX, HORIZON - 26, GOLD[2])
rect(DX, HORIZON - 36, DX, HORIZON - 31, GOLD[1])
put(DX - 1, HORIZON - 34, GOLD[1]); put(DX + 1, HORIZON - 34, GOLD[2])

# near row, sunlit cream stone with slate mansard roofs
row_of_buildings(HORIZON + 1, 9, 18, C(232, 196, 168), C(248, 224, 184), C(184, 144, 152),
                 C(88, 88, 136), C(136, 136, 176), C(120, 88, 120), True, C(160, 112, 120))

# row of horizon trees
TREE = [C(176, 208, 96), C(120, 176, 72), C(64, 128, 64), C(32, 80, 56)]
xx = -3
while xx < W + 4:
    r = rnd.randint(4, 6)
    blob(xx, HORIZON + 1, r, r - 0.5, TREE, base=HORIZON + 3)
    xx += rnd.randint(5, 8)

# ----------------------------------------------------------------------------- ground
LAWN = [C(144, 192, 72), C(96, 152, 64)]
LAWN_SH = [C(80, 128, 72), C(48, 96, 72)]
PLAZA, PLAZA_L = C(216, 184, 152), C(192, 160, 136)
PLAZA_SH, PLAZA_LSH = C(152, 128, 128), C(136, 112, 120)
GRAVEL, GRAVEL_S = C(240, 216, 176), C(216, 184, 144)
GRAVEL_SH, GRAVEL_SSH = C(168, 144, 136), C(152, 128, 128)
EDGE_C = C(248, 240, 208)
SHADOWMAP = {LAWN[0]: LAWN_SH[0], LAWN[1]: LAWN_SH[1], PLAZA: PLAZA_SH,
             PLAZA_L: PLAZA_LSH, GRAVEL: GRAVEL_SH, GRAVEL_S: GRAVEL_SSH,
             EDGE_C: GRAVEL_SH}

for y in range(HORIZON, H):
    z = 1.0 / (y - 180.0)
    stripe = int(z * 70)
    for x in range(W):
        put(x, y, LAWN[stripe & 1])

# plaza under the tower
for y in range(HORIZON, 209):
    for x in range(W):
        dx = (x + 0.5 - CX) / 78.0
        dy = (y + 0.5 - 199) / 10.0
        if dx * dx + dy * dy <= 1:
            c = PLAZA
            if (y + (x // 6)) % 4 == 0 or x % 12 == 5:
                c = PLAZA_L
            put(x, y, c)

# central avenue (perspective trapezoid)
def path_hw(y):
    return 12 + (y - HORIZON) * 1.95


for y in range(HORIZON + 3, H):
    hw_ = path_hw(y)
    for x in range(W):
        ax = abs(x + 0.5 - CX)
        if ax <= hw_:
            c = GRAVEL
            if (x * 7 + y * 13) % 11 == 0 or (x * 3 + y * 5) % 17 == 0:
                c = GRAVEL_S
            if ax > hw_ - 1.5:
                c = EDGE_C
            put(x, y, c)

# tower shadow, thrown toward the viewer (sun is low, behind-left)
for y in range(GY + 1, H):
    xl = 86 + (y - 199) * 5.2
    xr = 172 + (y - 199) * 3.2
    for x in range(W):
        if xl <= x <= xr:
            edge = (x - xl < 2) or (xr - x < 2)
            if edge and (x + y) & 1:
                continue
            c = img[y][x]
            if c in SHADOWMAP:
                put(x, y, SHADOWMAP[c])


# ----------------------------------------------------------------------------- trees
TRUNK, TRUNK_D = C(120, 80, 56), C(72, 48, 48)


def tree(xb, yb, s):
    # ground shadow
    for dx in range(-int(7 * s), int(9 * s) + 1):
        for dy in (0, 1):
            if dy == 0 or abs(dx) < 5 * s:
                c = img[yb + dy][xb + dx] if 0 <= xb + dx < W and yb + dy < H else None
                if c in SHADOWMAP:
                    put(xb + dx, yb + dy, SHADOWMAP[c])
    tw = max(2, int(round(2.5 * s)))
    th_ = int(round(8 * s))
    rect(xb - tw // 2, yb - th_, xb - tw // 2 + tw - 1, yb, TRUNK)
    rect(xb - tw // 2 + tw - 1, yb - th_, xb - tw // 2 + tw - 1, yb, TRUNK_D)
    cy = yb - th_ - 5 * s
    for dx, dy, r in [(-5, 2, 6), (5, 2, 6), (0, -1, 8), (-3, -6, 6), (4, -5, 6)]:
        blob(xb + dx * s, cy + dy * s, r * s, r * s * 0.95, TREE)


def trees_at(yb_list, side_gap):
    for yb in yb_list:
        s = 0.55 + (yb - 194) / 30.0
        off = path_hw(yb) + side_gap * s + 5
        for sgn in (-1, 1):
            tree(int(CX + sgn * off), yb, s)


BACK = [193, 197]
FRONT = [208, 222]
trees_at(BACK, 6)

# ----------------------------------------------------------------------------- the tower
IH, IL, IM, ID = C(248, 208, 128), C(184, 112, 64), C(104, 60, 48), C(48, 28, 44)
FAR = C(128, 88, 112)
WINDOW = C(255, 232, 136)
STONE, STONE_D = C(200, 168, 144), C(136, 104, 112)


def hw(h):
    return 46 * math.exp(-0.0135 * h) - 2.6 * (h / 186.0) ** 4


def lattice(s, h, S0, S1, h0, h1, nx, thick=0.65, edge=1.7, gird=0.85,
            vshift=0.0, edges=True):
    wd = S1 - S0
    if wd <= 0:
        return 0
    if edges:
        if s - S0 < edge:
            return 1
        if S1 - s < edge:
            return 2
        if h - h0 < gird:
            return 5
        if h1 - h < gird:
            return 6
    ph = h1 - h0
    u = (s - S0) / wd * nx
    i = min(int(u), nx - 1)
    uu = u - i
    cw = wd / nx
    v = ((h - h0) / ph + vshift) % 1.0
    if nx > 1 and i > 0 and uu * cw < 0.6:
        return 7
    k = ph / math.hypot(ph, cw)
    if abs(uu - v) * cw * k < thick:
        return 3
    if abs(uu - (1 - v)) * cw * k < thick:
        return 4
    return 0


def lat_color(kind, dx, s, S0, S1):
    left = dx < 0
    if kind == 1:
        return IH if s - S0 < 1.0 else IL
    if kind == 2:
        return ID if S1 - s < 1.0 else IM
    if kind == 3:
        return IL if left else IM
    if kind == 4:
        return IM if left else ID
    if kind == 5:
        return ID
    if kind == 6:
        return IH if left else IL
    return IM


def deck(dx, xi, r, wb, ext):
    """Platform: 0 underside, 1-3 body, 4-5 railing posts, 6 top rail."""
    ax = abs(dx)
    left = dx < 0
    if r == 0:
        return ID if ax <= wb + ext - 1 else None
    if r in (1, 2, 3):
        if ax > wb + ext:
            return None
        if r == 1:
            return IL if left else IM
        if r == 2:
            return ID if xi % 3 == 0 else (IH if left else IL)
        return IH if left else IL
    if r in (4, 5):
        if ax > wb + ext - 1:
            return None
        return (IL if left else IM) if xi % 2 == 0 else None
    if r == 6:
        return (IH if left else IL) if ax <= wb + ext - 1 else None
    return None


P1, P2, P3 = 36, 76, 146
ARCH_RX, ARCH_RY = 25.0, 31.0
SECTION_C = [(83, 99), (99, 115), (115, 131), (131, 146)]


def tower_pixel(x, y):
    h = GY - y - 0.5
    if h < 0:
        return None
    xc = x + 0.5
    dx = xc - CX
    ax = abs(dx)
    r = int(h)
    w = hw(h)
    left = dx < 0
    # ---------------- legs & arch
    if r < P1:
        if ax > w + (2 if r < 2 else 0):
            return None
        if r < 2 and ax > w:
            return STONE
        e = (dx / ARCH_RX) ** 2 + (h / ARCH_RY) ** 2
        if e < 1.0:
            return None
        if e < 1.24:
            t = (e - 1.0) / 0.24
            if t < 0.3:
                return ID
            if t < 0.8:
                return IL if left else IM
            return IH if left else IL
        a1 = ARCH_RX * math.sqrt(max(0.0, 1.24 - (h / ARCH_RY) ** 2))
        S0, S1 = (-w, -a1) if left else (a1, w)
        hlo, hhi = (0, 18) if h < 18 else (18, P1)
        if S1 - S0 < 3:
            return IM
        k = lattice(xc - CX, h, S0, S1, hlo, hhi, 1, thick=0.9, edge=2.3)
        if k:
            return lat_color(k, dx, xc - CX, S0, S1)
        k = lattice(xc - CX, h, S0, S1, hlo, hhi, 1, thick=0.5, vshift=0.5, edges=False)
        return FAR if k else None
    # ---------------- decks
    for p, ext in ((P1, 5), (P2, 3), (P3, 3)):
        if p <= r < p + 7:
            return deck(dx, x, r - p, hw(p), ext)
    # ---------------- lattice shafts
    if ax <= w:
        if P1 + 7 <= r < P2:
            panels = [(P1 + 7, 56), (56, P2)]
        elif P2 + 7 <= r < P3:
            panels = SECTION_C
        else:
            panels = None
        if panels:
            for h0, h1 in panels:
                if h0 <= h < h1 or (h0, h1) == panels[-1]:
                    wd = 2 * w
                    nx = max(1, round(wd / (h1 - h0)))
                    k = lattice(dx, h, -w, w, h0, h1, nx, thick=0.75, edge=2.0 if h < P2 else 1.7)
                    if k:
                        return lat_color(k, dx, dx, -w, w)
                    k = lattice(dx, h, -w, w, h0, h1, nx, thick=0.5, vshift=0.5,
                                edges=False)
                    return FAR if k else None
    # ---------------- cabin, dome, spire
    if P3 + 7 <= r < P3 + 14:       # cabin
        if ax > 7:
            return None
        if r == P3 + 13:
            return ID
        if ax >= 6:
            return IH if left else ID
        if r in (P3 + 9, P3 + 10) and int(xc + 20) % 3 != 0:
            return WINDOW
        return IL if left else IM
    if P3 + 14 <= r < P3 + 18:      # dome
        lim = (5.5, 4.5, 3.5, 2.5)[r - (P3 + 14)]
        if ax > lim:
            return None
        return IH if (left and ax > lim - 1.2) else (IL if left else IM)
    if P3 + 18 <= r < 181:          # spire
        lim = 2.0 if r < P3 + 24 else 1.0
        if r == P3 + 26 or r == P3 + 33:
            lim = 3.0 if r == P3 + 26 else 2.0
        if ax > lim:
            return None
        return IH if left else IM
    if 181 <= r < 190:              # antenna
        if int(x) == 127:
            return IH
        return None
    return None


for y in range(2, GY):
    for x in range(CX - 70, CX + 70):
        c = tower_pixel(x, y)
        if c is not None:
            put(x, y, c)

# tricolour on top
for c in range(7):
    fy = 8 + int(round(math.sin(c * 0.95)))
    col = C(40, 72, 200) if c < 2 else (C(248, 248, 248) if c < 5 else C(224, 40, 48))
    rect(128 + c, fy, 128 + c, fy + 3, col)
rect(127, 6, 127, 12, IH)

# ----------------------------------------------------------------------------- foreground
trees_at(FRONT, 6)


def person(x, yf, hgt, shirt, legs=C(64, 48, 88), hair=C(72, 40, 40)):
    hb = max(2, hgt // 3)
    rect(x, yf - hb + 1, x + 1, yf, legs)
    put(x + 1, yf, ID)
    rect(x - 1, yf - hb - hgt // 3 + 1, x + 2, yf - hb, shirt)
    put(x + 2, yf - hb, ID)
    rect(x, yf - hb - hgt // 3 - 1, x + 1, yf - hb - hgt // 3, C(240, 192, 152))
    rect(x, yf - hb - hgt // 3 - 2, x + 1, yf - hb - hgt // 3 - 2, hair)
    put(x + 2, yf + 1, GRAVEL_SH)
    put(x + 3, yf + 1, GRAVEL_SH)


person(112, 206, 9, C(208, 48, 56))
person(116, 207, 9, C(56, 96, 200))
person(150, 214, 11, C(248, 224, 96))
person(160, 216, 11, C(240, 240, 248))
person(96, 221, 12, C(88, 184, 112))

# lamp posts
for yb, s in ((213, 1.3),):
    for sgn in (-1, 1):
        lx = int(CX + sgn * (path_hw(yb) + 3))
        ph_ = int(14 * s)
        rect(lx, yb - ph_, lx, yb, ID)
        rect(lx - 1, yb - ph_ - 3, lx + 1, yb - ph_ - 1, WINDOW)
        put(lx, yb - ph_ - 4, ID)
        put(lx - 1, yb - ph_ - 3, C(255, 255, 216))

# foreground hedges and flower beds in the bottom corners
FLOW = [C(240, 64, 80), C(248, 160, 200), C(248, 224, 96), C(248, 248, 248)]
for side in (-1, 1):
    for i in range(7):
        bx = (6 + i * 9) if side < 0 else (W - 7 - i * 9)
        blob(bx, 222 - (i % 2), 6, 5, TREE, base=223)
    fr = random.Random(5 + side)
    for _ in range(26):
        fx = fr.randint(0, 62) if side < 0 else W - 1 - fr.randint(0, 62)
        fy = fr.randint(212, 223)
        if img[fy][fx] in TREE:
            put(fx, fy, FLOW[fr.randint(0, 3)])

# ----------------------------------------------------------------------------- limits
def tile_fix():
    fixed = 0
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            cnt = Counter(img[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8))
            while len(cnt) > 16:
                fixed += 1
                rare = min(cnt, key=lambda c: cnt[c])
                others = [c for c in cnt if c != rare]
                near = min(others, key=lambda c: sum((a - b) ** 2 for a, b in zip(c, rare)))
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        if img[y][x] == rare:
                            img[y][x] = near
                cnt[near] += cnt.pop(rare)
    return fixed


def write_png(path, scale=1):
    pal = sorted({c for row in img for c in row})
    idx = {c: i for i, c in enumerate(pal)}
    raw = bytearray()
    for row in img:
        line = bytearray([0])
        for c in row:
            line += bytes([idx[c]]) * scale
        raw += (line) * scale
    def chunk(t, d):
        b = struct.pack(">I", len(d)) + t + d
        return b + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W * scale, H * scale, 8, 3, 0, 0, 0))
    png += chunk(b"PLTE", b"".join(bytes(c) for c in pal))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)
    return len(pal)


if __name__ == "__main__":
    fixed = tile_fix()
    n = write_png("output/eiffel_snes.png")
    worst = max(len({img[y][x] for y in range(ty, ty + 8) for x in range(tx, tx + 8)})
                for ty in range(0, H, 8) for tx in range(0, W, 8))
    print("colours:", n, "| tiles repaired:", fixed, "| max colours/tile:", worst)
    if len(sys.argv) > 1:
        write_png(sys.argv[1], 4)
