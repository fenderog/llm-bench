#!/usr/bin/env python3
"""Eiffel Tower at dusk, drawn the way a 1994 SNES artist would.

Hard limits (all verified at the end of the run):
  * 256 x 224 pixels, written 1:1 (no upscaling)
  * <= 128 colours in the whole picture (all snapped to the SNES 15-bit gamut)
  * every 8x8 tile uses <= 16 colours

Pure standard library: the PNG is written by hand as an indexed (paletted) image.
"""
import math
import os
import random
import struct
import sys
import zlib

W, H = 256, 224
HORIZON = 181          # eye-level line where the ground plane meets the sky
GY = 188               # bottom edge of the tower's feet
TIP = 6                # top row of the tower
CX = 128.0             # tower axis (between pixel columns 127 and 128)


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------
def c15(hexstr):
    """'#rrggbb' -> RGB snapped to the SNES 5-bit-per-channel gamut."""
    h = hexstr.lstrip('#')
    out = []
    for i in (0, 2, 4):
        v5 = int(round(int(h[i:i + 2], 16) * 31 / 255.0))
        out.append((v5 << 3) | (v5 >> 2))
    return tuple(out)


def cs(*hexes):
    return [c15(h) for h in hexes]


img = [[(0, 0, 0)] * W for _ in range(H)]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def get(x, y):
    return img[y][x]


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def thr(x, y):
    return (BAYER[y & 3][x & 3] + 0.5) / 16.0


def ramp_pick(ramp, v, x, y, sharp=3.0):
    """Pick from a colour ramp with a narrow ordered-dither zone between bands."""
    top = len(ramp) - 1
    v = min(max(v, 0.0), top - 1e-6)
    i = int(v)
    f = v - i
    f = min(1.0, max(0.0, (f - 0.5) * sharp + 0.5))
    return ramp[i + 1] if f > thr(x, y) else ramp[i]


def line_pts(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return pts


def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            put(x, y, c)


# --------------------------------------------------------------------------
# palette (names -> colours); everything is quantised to 15-bit
# --------------------------------------------------------------------------
SKY = cs('#0e0e38', '#18164e', '#221e64', '#2e287a', '#403490', '#5c409e', '#7c4ca4',
         '#a05a9e', '#c46c96', '#e0878a', '#f2a67e', '#f9c88c', '#fde6ae')
CLOUD_HI = cs('#4a3478', '#74428e', '#a85488', '#d8707c', '#f49a70', '#fecb86')
CLOUD_LO = cs('#1c1a58', '#2a2a74', '#40408e', '#5c56a4', '#8466b0')
TOWER = cs('#1a0e2c', '#3a1e3e', '#6a3448', '#a0503e', '#cc7c3a', '#f0aa44', '#ffd470', '#fff2b8')
STONE = cs('#2c2448', '#52466a', '#7a6a88', '#a496a8', '#cfc0c4')

STAR_W, STAR_B = c15('#ffffff'), c15('#aab4ee')
MOON_L, MOON_M, MOON_D = cs('#fff4c8', '#e8d090', '#b89c78')
SUN_CORE, SUN_EDGE = cs('#fff8d0', '#ffe48c')


# --------------------------------------------------------------------------
# 1. sky, sun, moon, stars, clouds
# --------------------------------------------------------------------------
SUN = (80, 173)
MOON = (216, 33)


def sky_v(x, y):
    base = 0.2 + 8.2 * ((min(y, 184) / 184.0) ** 1.25)
    dx = (x - SUN[0]) / 80.0
    dy = (y - SUN[1]) / 46.0
    g = 4.6 * math.exp(-(dx * dx + dy * dy) * 1.5)
    dm = math.hypot(x - MOON[0], y - MOON[1])
    g += 1.0 * math.exp(-(dm / 20.0) ** 2)
    return base + g


def draw_sky():
    for y in range(H):
        for x in range(W):
            put(x, y, ramp_pick(SKY, sky_v(x, y), x, y, 3.2))


def draw_sun():
    cx, cy = SUN
    for y in range(cy - 16, cy + 12):
        for x in range(cx - 16, cx + 17):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d < 7:
                put(x, y, SUN_CORE)
            elif d < 10:
                put(x, y, SUN_EDGE)
            elif d < 13 and (x + y) & 1 == 0:
                put(x, y, SKY[12])


def draw_moon():
    cx, cy, r = MOON[0], MOON[1], 9.0
    for y in range(cy - 11, cy + 12):
        for x in range(cx - 11, cx + 12):
            d1 = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            d2 = math.hypot(x + 0.5 - (cx + 5.0), y + 0.5 - (cy - 2.0))
            if d1 < r and d2 >= 8.2:
                if d2 < 9.4:
                    put(x, y, MOON_M)
                else:
                    put(x, y, MOON_L if d1 < r - 1.5 else MOON_M)
    # a few craters on the lit limb
    put(cx - 6, cy + 1, MOON_D)
    put(cx - 5, cy + 4, MOON_D)
    put(cx - 4, cy - 3, MOON_D)


def draw_stars():
    rng = random.Random(11)
    n = 0
    while n < 62:
        x = rng.randrange(2, W - 2)
        y = rng.randrange(1, 112)
        if sky_v(x, y) > 3.3 + (0.4 if y < 40 else 0):
            continue
        if math.hypot(x - MOON[0], y - MOON[1]) < 17:
            continue
        put(x, y, STAR_W if rng.random() < 0.42 else STAR_B)
        n += 1
    for (x, y) in [(36, 22), (92, 12), (170, 26), (24, 70)]:
        put(x, y, STAR_W)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            put(x + dx, y + dy, STAR_B)


def puff_cloud(x, base, puffs, ramp, ambient=0.0, light=(-0.55, 0.6, 0.55), sharp=2.3):
    """Cumulus made of overlapping shaded spheres with a flat base.

    The sun is below the horizon at the left, so every puff is lit from underneath."""
    for dx, r in puffs:
        cx, cy = x + dx, base - r * 0.72
        sphere(cx, cy, r, ramp, light=light, ambient=ambient, sharp=sharp,
               clip=lambda xx, yy, b=base: yy <= b)


def draw_clouds():
    # high, cool clouds
    puff_cloud(6, 58, [(4, 6), (13, 9), (25, 12), (38, 9), (48, 7), (55, 5)], CLOUD_LO, 0.0)
    puff_cloud(168, 86, [(4, 6), (13, 9), (25, 12), (38, 9), (48, 7), (58, 5)], CLOUD_LO, 0.3)
    # low, warm clouds near the horizon glow
    puff_cloud(0, 136, [(6, 7), (17, 10), (30, 13), (44, 10), (55, 8), (64, 5)], CLOUD_HI, 0.2)
    puff_cloud(186, 130, [(5, 6), (16, 9), (28, 12), (41, 10), (52, 8), (64, 5)], CLOUD_HI, -0.3)


# --------------------------------------------------------------------------
# 2. Paris skyline
# --------------------------------------------------------------------------
FAR_WALL, FAR_ROOF, FAR_RIM = cs('#7a4a86', '#5e3c7c', '#b0689a')
NEAR_WALL, NEAR_ROOF, NEAR_RIM, NEAR_SHADE = cs('#48306c', '#30204e', '#7a4a88', '#3a2860')
WIN_ON, WIN_OFF = cs('#ffd070', '#3a2860')
DOME_L, DOME_M = cs('#f4c070', '#c88460')


def buildings(base, hmin, hmax, wmin, wmax, wall, roof, rim, shade, seed, windows=None, x0=-6, cap=None):
    rng = random.Random(seed)
    x = x0
    while x < W:
        w = rng.randint(wmin, wmax)
        h = rng.randint(hmin, hmax)
        if cap:
            h = min(h, cap(x + w // 2))
        top = base - h
        roof_h = 4 if h >= 10 else 3
        for yy in range(top + roof_h, base):
            for xx in range(x, x + w):
                put(xx, yy, wall)
            put(x, yy, rim)
            put(x + w - 1, yy, shade)
        for r in range(roof_h):
            inset = roof_h - 1 - r
            for xx in range(x + inset, x + w - inset):
                put(xx, top + r, roof)
            put(x + inset, top + r, rim if r > 0 else roof)
        for _ in range(rng.choice([1, 2, 2])):
            cxm = rng.randint(x + 3, max(x + 3, x + w - 5))
            for yy in range(top - 2, top + 2):
                put(cxm, yy, roof)
                put(cxm + 1, yy, shade)
        if windows:
            for wy in range(top + roof_h + 2, base - 2, 4):
                for wx in range(x + 2, x + w - 2, 3):
                    put(wx, wy, WIN_ON if rng.random() < 0.26 else WIN_OFF)
        x += w


def draw_invalides(x0, base):
    """Dome des Invalides: the golden dome that anchors the right-hand skyline."""
    cx = x0 + 13
    # drum
    rect(x0 + 5, base - 12, x0 + 21, base - 1, FAR_WALL)
    for xx in range(x0 + 5, x0 + 22):
        put(xx, base - 12, FAR_ROOF)
    for xx in range(x0 + 7, x0 + 20, 3):
        rect(xx, base - 10, xx, base - 4, FAR_ROOF)
    rect(x0 + 5, base - 12, x0 + 5, base - 1, FAR_RIM)
    # golden dome
    for y in range(base - 27, base - 12):
        t = (base - 12 - y) / 15.0
        half = 9 * math.sqrt(max(0.0, 1 - (t * 0.98) ** 2)) + 0.6
        for x in range(int(cx - half), int(cx + half) + 1):
            s = (x + 0.5 - cx) / 9.0
            if s < -0.35 and (y + x) % 6 != 0:
                c = DOME_L
            elif s < 0.2:
                c = DOME_M
            else:
                c = FAR_ROOF
            put(x, y, c)
    # ribs
    for k in (-5, 0, 5):
        for y in range(base - 25, base - 13):
            t = (base - 12 - y) / 15.0
            half = 9 * math.sqrt(max(0.0, 1 - (t * 0.98) ** 2))
            xx = int(cx + k * (half / 9.0))
            put(xx, y, FAR_ROOF if k >= 0 else DOME_M)
    # lantern + spire
    rect(cx - 1, base - 33, cx, base - 28, DOME_M)
    put(cx - 1, base - 33, DOME_L)
    rect(cx - 1, base - 39, cx - 1, base - 34, DOME_L)
    put(cx, base - 38, DOME_M)
    put(cx - 1, base - 40, DOME_L)


def draw_arc(x0, base):
    """Arc de Triomphe with the sunset showing through the opening."""
    w, h = 30, 28
    for y in range(base - h, base):
        for x in range(x0, x0 + w):
            put(x, y, FAR_WALL)
        put(x0, y, FAR_RIM)
        put(x0 + w - 1, y, FAR_ROOF)
    for x in range(x0 - 1, x0 + w + 1):
        put(x, base - h, FAR_RIM)
        put(x, base - h + 1, FAR_RIM)
        put(x, base - h + 2, FAR_ROOF)
    # attic with relief panels
    for x in range(x0 + 1, x0 + w - 1):
        if x % 3 != 0:
            put(x, base - h + 4, FAR_ROOF)
            put(x, base - h + 5, FAR_ROOF)
    for x in range(x0, x0 + w):
        put(x, base - h + 7, FAR_ROOF)
    # central opening: round-topped, sky visible through it
    cxm = x0 + w / 2.0
    ox0, ox1, top, r = x0 + 9, x0 + w - 10, base - 19, 6.0
    for y in range(top, base):
        for x in range(ox0, ox1 + 1):
            ry = y - top
            if ry < r:
                half = math.sqrt(max(0.0, r * r - (r - ry - 0.5) ** 2))
                if abs(x + 0.5 - cxm) > half:
                    continue
            put(x, y, ramp_pick(SKY, sky_v(x, y), x, y, 3.2))
    # pier shading beside the opening
    for y in range(top + 3, base):
        put(ox0 - 1, y, FAR_ROOF)
        put(ox1 + 1, y, FAR_RIM)


def draw_skyline():
    base = 185
    far_cap = lambda x: 7 if 64 <= x <= 98 else 99
    near_cap = lambda x: 4 if 62 <= x <= 96 else 99
    buildings(base, 13, 20, 9, 16, FAR_WALL, FAR_ROOF, FAR_RIM, FAR_ROOF, seed=5, cap=far_cap)
    draw_arc(38, base)
    draw_invalides(200, base)
    buildings(base + 1, 7, 12, 8, 14, NEAR_WALL, NEAR_ROOF, NEAR_RIM, NEAR_SHADE, seed=9, windows=True, x0=-3, cap=near_cap)


# --------------------------------------------------------------------------
# 3. spheres / foliage helper
# --------------------------------------------------------------------------
TREE = cs('#080e20', '#101c32', '#1a3040', '#264a4c', '#38685a', '#6a9a68')


def sphere(cx, cy, r, ramp, light=(-0.55, -0.6, 0.58), ambient=0.0, sharp=2.6, clip=None):
    lx, ly, lz = light
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            nx = (x + 0.5 - cx) / r
            ny = (y + 0.5 - cy) / r
            d2 = nx * nx + ny * ny
            if d2 > 1.0:
                continue
            if clip and not clip(x, y):
                continue
            nz = math.sqrt(1 - d2)
            lam = max(0.0, nx * lx + ny * ly + nz * lz)
            v = (lam * (len(ramp) - 1.0)) + ambient
            put(x, y, ramp_pick(ramp, v, x, y, sharp))


def foliage(cx, cy, rx, ry, seed, ramp, count=14, rmin=5, rmax=9, light=(-0.8, -0.1, 0.5)):
    rng = random.Random(seed)
    clumps = []
    for _ in range(count):
        a = rng.random() * math.tau
        d = math.sqrt(rng.random())
        clumps.append((cx + math.cos(a) * rx * d, cy + math.sin(a) * ry * d, rng.uniform(rmin, rmax)))
    clumps.sort(key=lambda c: c[1] - c[2] * 0.3)       # paint back-to-front, top first
    for (x, y, r) in clumps:
        sphere(x, y, r, ramp, light=light)


# --------------------------------------------------------------------------
# 4. ground: tree line, lawn, path
# --------------------------------------------------------------------------
LAWN = cs('#17343a', '#1f4840', '#2a5c44', '#3a7248', '#528a50')
PATH = cs('#5a4062', '#7a5a76', '#9a7488', '#b8909c', '#dcb6ac')
FLOWER = cs('#e85c7c', '#ffa0b4', '#f0d060')
LAMP = cs('#ffe8a0', '#ffc860', '#fff8d8')
LAWN_TOP = 186


def path_hw(y):
    return max(0.0, 0.84 * (y + 0.5 - 176) + 2.0)


def draw_treeline():
    rng = random.Random(3)
    rows = [(184, 4.0, 6.5, -0.8), (LAWN_TOP, 4.5, 8.0, -0.35)]
    for ybase, rmin, rmax, amb in rows:
        x = -6.0
        while x < W + 8:
            r = rng.uniform(rmin, rmax)
            if rng.random() < 0.2:
                r *= 1.3
            cy = ybase - r * 0.62 - rng.uniform(0, 3)
            lean = 1.0 - min(1.0, max(0.0, (x - 30) / 210.0)) * 0.95
            sphere(x + r, cy, r, TREE, ambient=amb + 1.1 * lean + rng.uniform(-0.3, 0.3), sharp=2.2,
                   clip=lambda xx, yy, b=ybase: yy < b)
            x += r * rng.uniform(1.15, 1.8)


def draw_ground():
    y = LAWN_TOP
    widths = [2, 2, 3, 3, 4, 4, 5, 6, 7, 8, 9, 10]
    k = 0
    while y < H:
        wd = widths[min(k, len(widths) - 1)]
        t = (y - LAWN_TOP) / float(H - LAWN_TOP)
        for yy in range(y, min(y + wd, H)):
            for xx in range(W):
                side = xx / float(W - 1)
                v = 3.3 - 1.8 * t - 1.0 * side + (0.55 if k % 2 == 0 else -0.15)
                put(xx, yy, ramp_pick(LAWN, v, xx, yy, 2.4))
        y += wd
        k += 1


def draw_lawn_detail():
    rng = random.Random(77)
    for _ in range(420):
        y = rng.randrange(LAWN_TOP + 1, H)
        x = rng.randrange(W)
        if abs(x + 0.5 - CX) < path_hw(y) + 8:
            continue
        t = (y - LAWN_TOP) / float(H - LAWN_TOP)
        v = rng.random()
        if v < 0.82:
            put(x, y, LAWN[1] if rng.random() < 0.5 else LAWN[3])
            if t > 0.3:
                put(x, y - 1, LAWN[3])
        elif v < 0.93:
            put(x, y, FLOWER[1])
        else:
            put(x, y, FLOWER[2])


def draw_path():
    # paving: seams follow the same perspective as the mown stripes
    seam_rows = set()
    y, gap = LAWN_TOP + 3, 3
    while y < H:
        seam_rows.add(y)
        y += gap
        gap += 1
    for y in range(LAWN_TOP - 3, H):
        hw = path_hw(y)
        x_lo = int(math.ceil(CX - hw - 0.5))
        x_hi = 255 - x_lo
        for x in range(x_lo, x_hi + 1):
            dx = x + 0.5 - CX
            v = 2.9 - 0.8 * abs(dx) / max(hw, 1.0) + 0.5 * max(0.0, 1 - (y - 184) / 14.0) - 0.45 * (dx > 0)
            if y in seam_rows:
                v -= 1.0
            elif (x * 7 + y * 13) % 31 == 0:
                v -= 0.8
            put(x, y, ramp_pick(PATH, v, x, y, 2.5))
        put(x_lo, y, PATH[4])
        put(x_lo - 1, y, LAWN[0])
        put(x_hi, y, PATH[1])
        put(x_hi + 1, y, LAWN[0])
    # low box hedges along both sides of the avenue, with a few flowers on top
    rng = random.Random(21)
    for y in range(LAWN_TOP, H):
        hw = path_hw(y)
        t = (y - LAWN_TOP) / float(H - LAWN_TOP)
        wd = 2 + int(round(t * 5))
        for sgn in (-1, 1):
            for k in range(wd):
                x = int(math.ceil(CX + sgn * (hw + 2.0) - 0.5)) + sgn * k if sgn > 0 else int(math.ceil(CX - (hw + 2.0) - 0.5)) - k
                if k == wd - 1:
                    c = TREE[1]
                elif k == 0:
                    c = TREE[0]
                else:
                    c = TREE[3] if (sgn < 0 or (x + y) & 1) else TREE[2]
                put(x, y, c)
            xe = int(math.ceil(CX + sgn * (hw + 2.0) - 0.5)) + sgn * (wd // 2) if sgn > 0 else int(math.ceil(CX - (hw + 2.0) - 0.5)) - wd // 2
            if rng.random() < 0.16:
                put(xe, y, rng.choice(FLOWER))


# --------------------------------------------------------------------------
# 5. the tower
# --------------------------------------------------------------------------
def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(j for j in range(n - 1) if xs[j] <= x)
        t = (x - xs[i]) / h[i]
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h[i] * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h[i] * m[i + 1])
    return f


_hw = pchip([22, 40, 70, 97, 124, 150, 170, 189],
            [3.6, 4.6, 6.4, 8.6, 12.8, 22.5, 31.5, 45.0])


def half_w(y):
    """Outer half-width of the tower at pixel row y (continuous profile)."""
    return _hw(y + 0.5)


def edge(y):
    """Leftmost tower pixel of row y."""
    return int(math.ceil(CX - half_w(y) - 0.5))


def tone(s, bias=0.0, base=4.3, k=2.3):
    """Tower shading: light from the left, so s=-1 is bright and s=+1 is plum shade."""
    i = int(round(base - k * max(-1.2, min(1.2, s)) + bias))
    return TOWER[max(0, min(7, i))]


def tw(x, y, bias=0.0, color=None):
    """Plot one tower pixel, shaded by where it sits across the tower."""
    if color is None:
        hw = max(half_w(y), 2.5)
        color = tone((x + 0.5 - CX) / hw, bias)
    put(x, y, color)


def tw2(x, y, bias=0.0, color=None):
    tw(x, y, bias, color)
    tw(255 - x, y, bias, color)


SOLID = set()          # pixels that get a dark outline later


def deck(top, face, ext, win_every=4, win_h=2, wins=True):
    """Platform: rail, balusters, deck lip, lit facade, cornice, shadowed underside."""
    y = top
    e = lambda yy: edge(yy) - ext
    # rail
    for x in range(e(y + 3), 128):
        tw2(x, y, 1.6)
    y += 1
    for x in range(e(y + 2), 128):
        if (x - e(y + 2)) % 2 == 0:
            tw2(x, y, 0.2)
    y += 1
    for x in range(e(y + 1), 128):
        tw2(x, y, 1.2)
        SOLID.add((x, y)); SOLID.add((255 - x, y))
    y += 1
    f0 = y
    for yy in range(f0, f0 + face):
        for x in range(e(yy) + 1, 128):
            tw2(x, yy, -0.4 - 0.5 * ((yy - f0) / float(face)))
            SOLID.add((x, yy)); SOLID.add((255 - x, yy))
    if wins:
        wy0 = f0 + (face - win_h) // 2
        x = 128 - 2 - win_every
        k = 0
        xs = []
        px = 2
        while 128 - px - 1 > e(wy0) + 3:
            xs.append(px)
            px += win_every
        for px in xs:
            for ww in range(2):
                for hh in range(win_h):
                    xl = 128 - px - 1 - ww
                    xr = 128 + px + ww
                    put(xl, wy0 + hh, TOWER[7])
                    put(xr, wy0 + hh, TOWER[6])
    y = f0 + face
    for x in range(e(y) - 1, 128):
        tw2(x, y, 0.9)
        SOLID.add((x, y)); SOLID.add((255 - x, y))
    y += 1
    for yy in (y, y + 1):
        for x in range(e(yy) + 1, 128):
            tw2(x, yy, color=TOWER[1] if yy == y else TOWER[0])
            SOLID.add((x, yy)); SOLID.add((255 - x, yy))
    return y + 1            # first free row below the deck


def chord(y0, y1, width=2, outer=1.6, inner=0.4):
    for y in range(y0, y1 + 1):
        xo = edge(y)
        for k in range(width):
            b = outer if k == 0 else inner
            tw2(xo + k, y, b)


def lattice(bounds, chord_w=2, bars=True, brace_bias=-1.0, inner_edge=None):
    """X-braced panels between consecutive y bounds (top -> bottom)."""
    for ya, yb in zip(bounds[:-1], bounds[1:]):
        xla = edge(ya) + chord_w
        xlb = edge(yb) + chord_w
        xra, xrb = 255 - xla, 255 - xlb
        for (x, y) in line_pts(xla, ya, xrb, yb):
            tw(x, y, brace_bias)
        for (x, y) in line_pts(xra, ya, xlb, yb):
            tw(x, y, brace_bias)
        if bars:
            for x in range(edge(yb), 128):
                tw2(x, yb, -0.2)


def tower_sparkle(x, y):
    put(x, y, TOWER[7])
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        put(x + dx, y + dy, TOWER[6])


P1_TOP, P2_TOP, P3_TOP = 142, 112, 33
ARX, ARY = 25.0, 22.0


def in_arch(x, y):
    dx = (x + 0.5 - CX) / ARX
    dy = (GY - (y + 0.5)) / ARY
    return dx * dx + dy * dy < 1.0


def in_ring(x, y):
    dx = (x + 0.5 - CX) / (ARX + 2.4)
    dy = (GY - (y + 0.5)) / (ARY + 2.4)
    return dx * dx + dy * dy < 1.0


def ring_edge(y):
    """First pixel (from the left) of the arch ring on row y, or 127 if none."""
    for x in range(edge(y), 128):
        if in_ring(x, y) or in_arch(x, y):
            return x
    return 127


def solid2(x, y, cl, cr):
    put(x, y, cl)
    put(255 - x, y, cr)
    SOLID.add((x, y))
    SOLID.add((255 - x, y))


def draw_tower():
    # ---- upper shaft: platform 3 -> platform 2 (open lattice, sky shows through)
    chord(43, P2_TOP - 1)
    lattice([43, 50, 58, 67, 77, 88, 100, P2_TOP - 1])
    # ---- section between platforms 2 and 1: denser, dark-backed
    for y in range(P2_TOP + 11, P1_TOP):
        for x in range(edge(y) + 2, 128):
            solid2(x, y, TOWER[2], TOWER[1])
    chord(P2_TOP + 11, P1_TOP - 1, width=3, outer=1.7, inner=0.3)
    lattice([P2_TOP + 11, P2_TOP + 20, P1_TOP], chord_w=3, brace_bias=-0.5)
    # ---- platforms
    deck(P3_TOP, 3, 3, win_every=3, win_h=2)
    deck(P2_TOP, 4, 4, win_every=4, win_h=2)
    y_under = deck(P1_TOP, 6, 5, win_every=4, win_h=3)
    # ---- legs + spandrel (everything below platform 1)
    y_top = y_under
    for y in range(y_top, GY):
        for x in range(edge(y), 128):
            if in_arch(x, y):
                continue
            solid2(x, y, TOWER[2], TOWER[1])
    # spandrel band above the arch: posts and X cells
    band_a, band_b = y_top, 163
    for x in range(edge(band_a), 128):
        tw2(x, band_a, 0.6)
        tw2(x, band_b, 0.6)
    posts = [112, 120]
    for ya_, yb_ in ((band_a, band_b),):
        for px in posts:
            for y in range(ya_, yb_ + 1):
                tw2(px, y, -0.3)
        for y in range(ya_, yb_ + 1):
            put(127, y, tone(-0.05, -0.3))
            put(128, y, tone(0.05, -0.3))
        cell_x = [None, 112, 120, 127]
        for k in range(3):
            xa = (edge(ya_) + 1) if k == 0 else cell_x[k]
            xb = cell_x[k + 1]
            xa2 = (edge(yb_) + 1) if k == 0 else cell_x[k]
            for (x, y) in line_pts(xa, ya_ + 1, xb, yb_ - 1):
                tw2(x, y, -0.7)
            for (x, y) in line_pts(xb, ya_ + 1, xa2, yb_ - 1):
                tw2(x, y, -0.7)
    # X braces inside each leg
    legb = [164, 171, 178, 183]
    for ya_, yb_ in zip(legb[:-1], legb[1:]):
        xa0, xb0 = edge(ya_) + 2, edge(yb_) + 2
        xa1, xb1 = ring_edge(ya_) - 1, ring_edge(yb_) - 1
        xa1, xb1 = max(xa1, xa0 + 3), max(xb1, xb0 + 3)
        for (x, y) in line_pts(xa0, ya_, xb1, yb_):
            tw2(x, y, -0.5)
        for (x, y) in line_pts(xa1, ya_, xb0, yb_):
            tw2(x, y, -0.5)
        for x in range(xb0, xb1 + 1):
            tw2(x, yb_, -0.1)
    # arch ring: bright inner lip, slightly darker body
    for y in range(y_top, GY):
        for x in range(edge(y), 128):
            if in_arch(x, y) or not in_ring(x, y):
                continue
            lip = (in_arch(x + 1, y) or in_arch(x, y + 1) or in_arch(x - 1, y) or in_arch(x, y - 1)
                   or in_arch(x + 1, y + 1) and False)
            tw2(x, y, 2.1 if lip else 1.0)
    # outer chords of the legs
    chord(y_top, GY - 1, width=2, outer=1.8, inner=0.6)
    # ---- stone piers
    for y in range(183, GY):
        for x in range(edge(y) - 1, 128):
            if in_arch(x, y) or in_arch(x + 1, y):
                continue
            if y == 183:
                cl, cr = STONE[4], STONE[2]
            elif y == 185:
                cl, cr = STONE[2], STONE[0]
            elif y == GY - 1:
                cl, cr = STONE[1], STONE[0]
            else:
                cl, cr = STONE[3], STONE[1]
            if x == edge(y) - 1:
                cl = STONE[4] if y != 185 else STONE[3]
            solid2(x, y, cl, cr)
    # ---- cupola + spire
    for y in range(24, 33):
        hw = 3 if y >= 26 else 2
        for x in range(128 - hw - 1, 128):
            tw2(x, y, 0.3)
            SOLID.add((x, y)); SOLID.add((255 - x, y))
    for y in range(26, 31):
        put(127, y, TOWER[7]); put(128, y, TOWER[6])
    for y in range(8, 24):
        put(127, y, TOWER[6]); put(128, y, TOWER[3])
    for y in (11, 16, 20):
        put(126, y, TOWER[5]); put(129, y, TOWER[2])
    for (x, y) in ((127, 6), (128, 6), (127, 7), (128, 7)):
        put(x, y, TOWER[7])
    for sx, sy in ((126, 6), (129, 6), (126, 7), (129, 7), (127, 5), (128, 5)):
        put(sx, sy, TOWER[6])
    tower_sparkle(127, 10)
    tower_sparkle(edge(P1_TOP + 3) - 5, P1_TOP + 1)
    tower_sparkle(255 - edge(P2_TOP + 3) + 4, P2_TOP)
    for y in range(0, 14):
        for x in range(118, 138):
            d = math.hypot(x + 0.5 - 128.0, y - 6.5)
            if (x, y) in SOLID or not (get(x, y) in SKY or get(x, y) in CLOUD_LO):
                continue
            if 2.8 < d < 4.8 and (x + y) & 1 == 0:
                put(x, y, HALO_B)
            elif 4.8 <= d < 6.8 and x % 2 == 0 and y % 2 == 0:
                put(x, y, HALO_B)


def outline_tower(minimum_y=100):
    """1px dark-plum outline around the solid masonry/deck parts, on the sky side only."""
    add = set()
    for (x, y) in SOLID:
        if y < minimum_y:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in SOLID and 0 <= n[0] < W and 0 <= n[1] < H and in_open(n[0], n[1]):
                add.add(n)
    for (x, y) in add:
        put(x, y, TOWER[0])


def in_open(x, y):
    """True where the pixel is background (not part of the tower's own artwork)."""
    return not in_arch(x, y) or y >= GY


# --------------------------------------------------------------------------
# 5b. foreground props: lamps, people, framing trees, birds
# --------------------------------------------------------------------------
HAIR, SKIN = cs('#2a1c3c', '#e8b890')
COATS = {
    'blue': cs('#2848a0', '#4a70d0'),
    'red': cs('#b02848', '#e05070'),
    'gold': cs('#c89030', '#f0c860'),
    'teal': cs('#207068', '#38a098'),
}
TROUSERS = cs('#1c1838', '#2c2850')
POST = c15('#1a1030')
HALO_A, HALO_B = cs('#f4c868', '#b88848')
FG = cs('#060a18', '#0e1830', '#16283e', '#223c4a', '#33584e', '#4c7858')


def lamp(x, yf, h):
    thick = 2 if h >= 16 else 1
    # glow first, so the post sits on top of it
    hy = yf - h
    rad = 3.5 + h * 0.2
    for y in range(int(hy - rad), int(hy + rad) + 1):
        for xx in range(int(x - rad), int(x + rad) + 2):
            d = math.hypot(xx + 0.5 - (x + thick / 2.0), y + 0.5 - hy)
            if d < rad * 0.5 and (xx + y) & 1 == 0:
                put(xx, y, HALO_A)
            elif d < rad and xx % 2 == 0 and y % 2 == 0:
                put(xx, y, HALO_B)
    for y in range(hy, yf + 1):
        for k in range(thick):
            put(x + k, y, POST)
    # lantern head
    hw = 3 if h >= 16 else 2
    for yy in range(hy - 2, hy + 1):
        for xx in range(x - hw // 2, x - hw // 2 + hw + (thick - 1)):
            put(xx, yy, LAMP[2] if yy == hy - 1 else LAMP[0])
    put(x + (thick - 1) // 2, hy - 3, POST)


def person(x, yf, h, coat, trousers=TROUSERS[0], dress=False):
    cl, cd = COATS[coat][1], COATS[coat][0]
    bw = 3 if h >= 11 else 2
    x0 = x - bw // 2
    head = 3 if h >= 13 else 2
    legs_h = max(2, h // 3)
    y = yf - h + 1
    # head
    for yy in range(y, y + head):
        for xx in range(x0, x0 + head):
            put(xx, yy, SKIN)
    for xx in range(x0, x0 + head):
        put(xx, y, HAIR)
    put(x0 + head - 1, y + 1, HAIR) if head == 3 else None
    # torso
    ty = y + head
    for yy in range(ty, yf - legs_h + 1):
        for k in range(bw):
            put(x0 + k, yy, cl if k == 0 else cd)
    # legs
    for yy in range(yf - legs_h + 1, yf + 1):
        if dress:
            for k in range(bw):
                put(x0 + k, yy, cl if k == 0 else cd)
        else:
            put(x0, yy, trousers)
            put(x0 + bw - 1, yy, trousers)


def draw_people():
    person(113, 205, 13, 'blue')
    person(117, 205, 11, 'gold', dress=True)
    person(146, 198, 9, 'red')
    person(143, 199, 8, 'teal')
    person(126, 193, 6, 'gold')


def draw_lamps():
    for (yf, h) in ((200, 10), (211, 16), (223, 24)):
        hw = path_hw(yf)
        wd = 2 + int(round((yf - LAWN_TOP) / float(H - LAWN_TOP) * 5))
        lamp(int(CX - hw - wd - 5), yf, h)
        lamp(int(CX + hw + wd + 4), yf, h)


def draw_framing_trees():
    # left tree
    for y in range(160, 216):
        for k in range(5):
            put(8 + k, y, FG[1] if k < 3 else FG[0])
        put(8, y, FG[2])
    foliage(2, 140, 20, 28, 31, FG, count=22, rmin=7, rmax=12)
    # right tree
    for y in range(168, 214):
        for k in range(5):
            put(246 + k, y, FG[1] if k < 3 else FG[0])
        put(246, y, FG[2])
    foliage(250, 150, 20, 26, 47, FG, count=20, rmin=7, rmax=12)
    # low shrubs in the corners
    foliage(14, 214, 16, 6, 5, FG, count=8, rmin=6, rmax=9)
    foliage(240, 216, 16, 5, 6, FG, count=8, rmin=6, rmax=9)


def bird(x, y, big=True):
    c = TOWER[0]
    if big:
        for dx, dy in ((0, 0), (4, 0), (1, 1), (3, 1), (2, 2)):
            put(x + dx, y + dy, c)
    else:
        for dx, dy in ((0, 0), (2, 0), (1, 1)):
            put(x + dx, y + dy, c)


def draw_birds():
    for (x, y, big) in ((168, 58, True), (178, 52, True), (184, 62, False), (156, 66, False), (196, 48, False)):
        bird(x, y, big)


# --------------------------------------------------------------------------
# 6. verification + output
# --------------------------------------------------------------------------
def analyse():
    colors = {}
    for row in img:
        for c in row:
            colors[c] = colors.get(c, 0) + 1
    bad = []
    worst = 0
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            cs_ = set()
            for y in range(ty, ty + 8):
                for x in range(tx, tx + 8):
                    cs_.add(img[y][x])
            worst = max(worst, len(cs_))
            if len(cs_) > 16:
                bad.append((tx // 8, ty // 8, len(cs_)))
    return colors, bad, worst


def write_indexed_png(path, colors_sorted):
    index = {c: i for i, c in enumerate(colors_sorted)}
    raw = bytearray()
    for row in img:
        raw.append(0)
        raw.extend(index[c] for c in row)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)

    plte = bytes(v for c in colors_sorted for v in c)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 3, 0, 0, 0))
           + chunk(b'PLTE', plte)
           + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


def write_preview(path, scale=4, box=(0, 0, W, H)):
    bx0, by0, bx1, by1 = box
    raw = bytearray()
    for row in img[by0:by1]:
        line = bytearray([0])
        for c in row[bx0:bx1]:
            line.extend(bytes(c) * scale)
        for _ in range(scale):
            raw.extend(line)

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', (bx1 - bx0) * scale, (by1 - by0) * scale, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(raw), 6))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


def render():
    draw_sky()
    draw_stars()
    draw_moon()
    draw_clouds()
    draw_sun()
    draw_skyline()
    draw_treeline()
    draw_ground()
    draw_path()
    draw_lawn_detail()
    draw_tower()
    outline_tower()
    draw_lamps()
    draw_people()
    draw_framing_trees()
    draw_birds()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'output/eiffel_tower_snes.png'
    preview = sys.argv[2] if len(sys.argv) > 2 else None
    render()
    colors, bad, worst = analyse()
    print('colours:', len(colors), ' worst tile:', worst, ' tiles over 16:', len(bad))
    if bad:
        print('  over-limit tiles (tx,ty,n):', bad[:20])
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    pal = sorted(colors, key=lum)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    write_indexed_png(out, pal)
    if preview:
        write_preview(preview)
    if len(sys.argv) > 8:
        x0, y0, x1, y1, sc = (int(v) for v in sys.argv[3:8])
        write_preview(sys.argv[8], sc, (x0, y0, x1, y1))


if __name__ == '__main__':
    main()
