#!/usr/bin/env python3
"""
Eiffel Tower at sunset -- SNES-style pixel art rendered natively at 256x224.

Hardware-style limits (checked before saving):
  * 256x224 pixels, no scaling
  * every colour is a 15-bit BGR555 SNES colour, <= 128 colours in total
  * every 8x8 tile uses <= 16 colours
Standard library only. Writes an indexed PNG.

usage: python3 src/eiffel.py [out.png] [--preview DIR]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pngio import write_indexed, write_rgb  # noqa: E402

W, H = 256, 224


# --------------------------------------------------------------------------
# colour helpers
# --------------------------------------------------------------------------
def snes(hexstr):
    """Snap a #rrggbb colour to the nearest 15-bit SNES colour (5 bits/channel)."""
    h = hexstr.lstrip('#')
    out = []
    for i in (0, 2, 4):
        v = round(int(h[i:i + 2], 16) * 31 / 255)
        out.append((v << 3) | (v >> 2))
    return tuple(out)


def pal(*hexes):
    return [snes(h) for h in hexes]


BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bayer(x, y):
    return (BAYER4[y & 3][x & 3] + 0.5) / 16.0


def ramp(v, x, y, n, tw=0.5):
    """Pick a ramp index for continuous value v: solid bands with a short
    ordered-dither transition (width tw) at the top of each band."""
    i = int(math.floor(v))
    f = v - i
    if f > 1.0 - tw and (f - (1.0 - tw)) / tw > bayer(x, y):
        i += 1
    return max(0, min(n - 1, i))


# --------------------------------------------------------------------------
# palettes (all snapped to BGR555)
# --------------------------------------------------------------------------
SKY = pal('#120c34', '#1c1048', '#2a165c', '#3c1c6c', '#52227a', '#6c2a84', '#883288',
          '#a43c88', '#c04a86', '#d85c80', '#ea7478', '#f69070', '#fcb06c', '#fed078',
          '#fff0a8')
SUN_CORE = snes('#fffbe0')
STAR = pal('#9c7cd0', '#e8dcff')
MOON = pal('#fff2d0', '#c8a8d8')
CLOUD = pal('#2a1650', '#3e1e66', '#5a2878', '#7c3282', '#a43e84', '#cc5280', '#ec7076',
            '#fc9a6c', '#ffc878', '#fff0b0')
FAR_A = pal('#a85078', '#d87478')
FAR_B = pal('#5e2c62', '#8a3c6c', '#c05e74')
WIN = pal('#ffd070', '#ff9840')
BLD = pal('#22142e', '#3c2440', '#5a3450', '#784660', '#a0606a', '#d08a70')
ROOF = pal('#1e1838', '#2e2650', '#463c6c', '#6e6094')
TOWER = pal('#1c0e26', '#341834', '#52223c', '#723040', '#964444', '#b85c48', '#d6804e',
            '#f0a85c', '#ffd488')
BEACON = snes('#ff5038')
TREE = pal('#0c1620', '#122228', '#1a3030', '#244034', '#34563a', '#527040', '#869048',
           '#c8b058')
QUAY = pal('#1e1028', '#341a3c', '#4c2a50', '#64395e', '#82506c', '#a8707c')
LAMP = pal('#ffc858', '#fff4c0')
LAMP_GLOW = snes('#b8603c')
BOAT = pal('#141026', '#2a2244', '#54467a', '#9888b4', '#e0d4ec')
FLAG_BLUE = snes('#2c50d8')
WATER = pal('#140c30', '#1e1244', '#2c1a5a', '#40226c', '#5a2c7a', '#843a84', '#c0527e',
            '#f0846e', '#ffc878', '#fff4c8')

# --------------------------------------------------------------------------
# scene layout
# --------------------------------------------------------------------------
SUN_X, SUN_Y, SUN_R = 70, 138, 14
HORIZON = 162
CX, BASE_Y = 144, 188          # tower centre column / ground line
QUAY_Y = 186                   # top of the river wall
WATER_Y = 199                  # first row of water


def sun_dist(x, y):
    return math.hypot((x - SUN_X) / 1.7, y - SUN_Y)


# --------------------------------------------------------------------------
# sky, sun, moon, stars
# --------------------------------------------------------------------------
def sky_value(x, y):
    t = max(0.0, min(1.0, y / HORIZON))
    d = sun_dist(x, y)
    glow = 3.0 * math.exp(-(d / 20.0) ** 2) + 2.0 * math.exp(-(d / 80.0) ** 2)
    return min(13.0, 11.0 * t ** 1.35 + glow)


def draw_sky(img):
    for y in range(H):
        for x in range(W):
            img[y][x] = SKY[ramp(sky_value(x, y), x, y, len(SKY))]


def draw_sun(img):
    for y in range(SUN_Y - SUN_R - 2, SUN_Y + SUN_R + 3):
        for x in range(SUN_X - SUN_R - 2, SUN_X + SUN_R + 3):
            d = math.hypot(x - SUN_X, y - SUN_Y)
            if d <= SUN_R - 1.5:
                img[y][x] = SUN_CORE
            elif d <= SUN_R - 0.2:
                img[y][x] = SKY[14]
            elif d <= SUN_R + 0.6:
                img[y][x] = SKY[13]


def draw_moon(img):
    """Thin waxing crescent: a disc minus an offset disc, with a soft inner edge."""
    mx, my, r = 238, 13, 6.7
    for y in range(my - 8, my + 9):
        for x in range(mx - 8, mx + 9):
            d_out = math.hypot(x - mx, y - my)
            d_in = math.hypot(x - (mx + 3.4), y - (my - 2.0))
            if d_out <= r and d_in > r - 0.5:
                img[y][x] = MOON[1] if d_in <= r + 0.5 else MOON[0]


def draw_stars(img):
    rng = random.Random(7)
    placed = 0
    while placed < 34:
        x, y = rng.randrange(2, W - 2), rng.randrange(2, 70)
        if sky_value(x, y) > 2.6:
            continue
        img[y][x] = STAR[1] if rng.random() < 0.35 else STAR[0]
        placed += 1
    for x, y in ((24, 12), (118, 8), (176, 18), (250, 48), (60, 30)):
        img[y][x] = STAR[1]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[y + dy][x + dx] = STAR[0]


# --------------------------------------------------------------------------
# clouds: lobes shaded as lit spheres, light coming from the low sun
# --------------------------------------------------------------------------
CLOUDS = [
    # bias, flat-bottom row, lobes (cx, cy, rx, ry) listed back to front
    (3.0, 71, [(14, 64, 17, 8), (40, 57, 16, 11), (63, 61, 13, 8), (86, 66, 12, 5),
               (26, 67, 15, 5), (52, 67, 17, 6), (74, 68, 13, 4)]),
    (2.2, 41, [(178, 35, 13, 6), (200, 29, 15, 9), (224, 32, 14, 8), (247, 36, 13, 6),
               (212, 37, 24, 5)]),
    (4.2, 100, [(168, 98, 14, 3), (192, 94, 19, 5), (216, 91, 13, 6), (240, 96, 18, 4)]),
    (5.6, 122, [(98, 120, 16, 2), (120, 118, 19, 4), (142, 120, 12, 2)]),
    (5.2, 114, [(6, 112, 16, 3), (28, 108, 14, 5), (48, 112, 12, 3)]),
    (3.4, 142, [(50, 141, 18, 1.6), (78, 137, 24, 2), (104, 140, 10, 1.4)]),
]


def draw_clouds(img):
    for bias, bottom, lobes in CLOUDS:
        ccx = sum(l[0] for l in lobes) / len(lobes)
        ccy = sum(l[1] for l in lobes) / len(lobes)
        lx, ly = SUN_X - ccx, SUN_Y - ccy
        n = math.hypot(lx, ly) or 1.0
        L = (0.8 * lx / n, 0.8 * ly / n, 0.45)
        n = math.sqrt(sum(c * c for c in L))
        L = tuple(c / n for c in L)
        x0 = int(min(l[0] - l[2] for l in lobes)) - 1
        x1 = int(max(l[0] + l[2] for l in lobes)) + 2
        y0 = int(min(l[1] - l[3] for l in lobes)) - 1
        mask = {}
        for y in range(y0, bottom + 1):
            for x in range(max(0, x0), min(W, x1)):
                for k, (cx, cy, rx, ry) in enumerate(lobes):
                    nx, ny = (x - cx) / (rx + 0.35), (y - cy) / (ry + 0.35)
                    if nx * nx + ny * ny <= 1.0:
                        mask[(x, y)] = (k, nx, ny)
        sunboost = 2.0 * math.exp(-(sun_dist(ccx, ccy) / 60.0) ** 2)
        for (x, y), (k, nx, ny) in mask.items():
            nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
            s = nx * L[0] + ny * L[1] + nz * L[2]
            v = bias + sunboost + 2.4 * s
            if (x, y + 1) not in mask:
                v += 1.6
            elif (x, y + 2) not in mask:
                v += 0.6
            if (x, y - 1) not in mask:
                v -= 0.6
            # shadow just outside a lobe that sits in front of this one
            for dx, dy in ((0, -1), (1, 0), (-1, 0)):
                o = mask.get((x + dx, y + dy))
                if o and o[0] > k:
                    v -= 1.0
                    break
            img[y][x] = CLOUD[ramp(v, x, y, len(CLOUD), 0.4)]


# --------------------------------------------------------------------------
# distant city
# --------------------------------------------------------------------------
def skyline_tops(seed, lo, hi):
    rng = random.Random(seed)
    top = [HORIZON + 10] * W
    segs = []
    x = -rng.randint(0, 8)
    while x < W:
        w = rng.randint(7, 16)
        h = rng.randint(lo, hi)
        segs.append((x, w, h))
        for i in range(w):
            xx = x + i
            if 0 <= xx < W:
                inset = min(i, w - 1 - i)
                top[xx] = h + max(0, 2 - inset)       # mansard shoulders
        for _ in range(rng.randint(0, 2)):          # chimney stacks
            cxp = x + rng.randint(2, max(2, w - 3))
            ch = rng.randint(2, 3)
            for xx in (cxp, cxp + 1):
                if 0 <= xx < W:
                    top[xx] = h - ch
        x += w
    return top, segs


def draw_far_city(img):
    # far layer: hazy silhouettes with landmarks
    top, _ = skyline_tops(11, 147, 153)
    for x in range(W):          # Montmartre hill
        top[x] = min(top[x], int(158 - 9 * math.exp(-((x - 198) / 22.0) ** 2)))
    shapes = set()

    def rect(x0, y0, x1, y1):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                shapes.add((xx, yy))

    def dome(cx, cy, rx, ry):
        for yy in range(int(cy - ry), cy + 1):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((xx - cx) / (rx + 0.5)) ** 2 + ((yy - cy) / (ry + 0.5)) ** 2 <= 1:
                    shapes.add((xx, yy))

    # Les Invalides
    rect(92, 150, 108, 160)
    rect(95, 145, 105, 150)
    dome(100, 145, 5, 6)
    rect(99, 136, 101, 139)
    rect(100, 131, 100, 136)
    # Sacre-Coeur
    rect(191, 143, 201, 152)
    dome(196, 143, 4, 6)
    rect(196, 133, 196, 137)
    for sx in (186, 206):
        rect(sx - 1, 146, sx + 1, 151)
        dome(sx, 146, 1, 2)
    rect(209, 139, 211, 151)
    dome(210, 139, 1, 2)
    rect(210, 135, 210, 137)

    for y in range(128, HORIZON + 12):
        for x in range(W):
            if y >= top[x] or (x, y) in shapes:
                above = (y - 1 >= top[x]) or ((x, y - 1) in shapes)
                left = (x - 1 >= 0) and ((y >= top[x - 1]) or ((x - 1, y) in shapes))
                img[y][x] = FAR_A[0] if (above and left) else FAR_A[1]

    # Invalides gilding catches the sun
    for (x, y) in ((96, 141), (95, 142), (95, 143), (99, 139), (97, 140)):
        img[y][x] = WIN[0]

    # nearer layer: darker rooftops with lit windows
    top, segs = skyline_tops(23, 154, 160)
    rng = random.Random(5)
    for y in range(146, H):
        for x in range(W):
            if y >= top[x]:
                if y == top[x] or (x > 0 and y < top[x - 1]):
                    c = FAR_B[2] if x < 150 else FAR_B[1]
                elif y < top[x] + 3:
                    c = FAR_B[1]
                else:
                    c = FAR_B[0]
                img[y][x] = c
    for sx, w, h in segs:
        for wy in range(h + 5, 184, 4):
            for wx in range(sx + 2, sx + w - 2, 3):
                if 0 <= wx < W and wy > top[wx] + 3 and rng.random() < 0.16:
                    img[wy][wx] = WIN[1] if rng.random() < 0.7 else WIN[0]


# --------------------------------------------------------------------------
# Haussmann buildings framing the view
# --------------------------------------------------------------------------
def draw_haussmann(img, x0, x1, roof_top, seed, lit_left):
    rng = random.Random(seed)
    cornice = roof_top + 10
    # chimneys
    for cxp in range(x0 + 4, x1 - 3, 11):
        cxp += rng.randint(-1, 1)
        for y in range(roof_top - 5, roof_top + 2):
            for x in range(cxp, cxp + 4):
                if 0 <= x < W:
                    c = BLD[4] if x == cxp else (BLD[1] if x == cxp + 3 else BLD[2])
                    if y == roof_top - 5:
                        c = BLD[5] if x == cxp else BLD[3]
                    img[y][x] = c
        for x in (cxp, cxp + 2):
            if 0 <= x < W:
                img[roof_top - 6][x] = BLD[3]
    # mansard roof with dormers
    for y in range(roof_top, cornice):
        slope = (cornice - y) // 3
        for x in range(x0, x1):
            if not (0 <= x < W):
                continue
            if (lit_left and x < x0 + slope) or (not lit_left and x >= x1 - slope):
                continue
            if y == roof_top:
                c = ROOF[3]
            elif (lit_left and x == x0 + slope) or (not lit_left and x == x1 - slope - 1):
                c = ROOF[3] if lit_left else ROOF[0]
            else:
                c = ROOF[1] if (x % 3) else ROOF[2]
            img[y][x] = c
    for dx in range(x0 + 5, x1 - 4, 7):
        for y in range(roof_top + 3, cornice):
            for x in range(dx - 1, dx + 2):
                if 0 <= x < W:
                    if y == roof_top + 3:
                        c = BLD[4] if x == dx else ROOF[0]
                    elif x == dx and y > roof_top + 4:
                        c = WIN[0] if (dx // 7 + seed) % 3 == 0 else BLD[0]
                    else:
                        c = BLD[3] if x == dx - 1 else BLD[1]
                    img[y][x] = c
    # cornice
    for x in range(x0, x1):
        if 0 <= x < W:
            img[cornice][x] = BLD[5]
            img[cornice + 1][x] = BLD[1]
    # facade
    for y in range(cornice + 2, QUAY_Y):
        for x in range(x0, x1):
            if 0 <= x < W:
                edge = (x == x0) if lit_left else (x == x1 - 1)
                img[y][x] = BLD[4] if edge else BLD[2]
    floor_h = 9
    for f, fy in enumerate(range(cornice + 3, QUAY_Y, floor_h)):
        for wx in range(x0 + 3, x1 - 2, 6):
            lit = rng.random() < 0.28
            for y in range(fy + 1, min(fy + 7, QUAY_Y)):
                for x in (wx, wx + 1):
                    if 0 <= x < W:
                        if y == fy + 1:
                            c = BLD[1]
                        elif lit:
                            c = WIN[1] if y == fy + 6 else WIN[0]
                        else:
                            c = BLD[0]
                        img[y][x] = c
            for x in range(wx - 1, wx + 3):      # sill / lintel highlight
                if 0 <= x < W and fy + 7 < QUAY_Y:
                    img[fy + 7][x] = BLD[3]
        if f in (1, 4):                          # wrought-iron balconies
            by = fy + 6
            for x in range(x0 + 1, x1 - 1):
                if 0 <= x < W and by < QUAY_Y:
                    img[by][x] = BLD[0] if x % 2 == 0 else img[by][x]
                    if by + 1 < QUAY_Y:
                        img[by + 1][x] = BLD[0]
                    if by + 2 < QUAY_Y:
                        img[by + 2][x] = BLD[4]


# --------------------------------------------------------------------------
# the tower
# --------------------------------------------------------------------------
HOLE, AA_LIT, AA_DARK = -1, -2, -3


def wo(hp):
    """Outer half-width at height hp above the ground (concave, exponential)."""
    return 32.0 * math.exp(-hp / 48.0) + 1.5


def draw_tower(img):
    T = {}

    def put(x, y, t):
        T[(x, y)] = t

    def panel(y, struts):
        for ya, yb in zip(struts, struts[1:]):
            if yb <= y <= ya:
                return ya - y, ya - yb
        return 0, 1

    def on_x(p, n, k, K):
        """Is interior pixel p (of n) on either diagonal of an X-braced panel?"""
        if n <= 0:
            return False
        lo = round((k - 0.5) / K * (n - 1))
        hi = max(lo, round((k + 0.5) / K * (n - 1)) - 1)
        lo, hi = max(0, lo), min(n - 1, hi)
        return lo <= p <= hi or lo <= n - 1 - p <= hi

    def leg_row(y, o, i, struts, open_holes):
        """One row of the lattice: two legs (or one merged column if i is None)."""
        xo = int(round(o))
        k, K = panel(y, struts)
        strut = k == 0 or k == K
        if o - xo > 0.15:                       # soften the stair-steps of the curve
            put(CX - xo - 1, y, AA_LIT)
            put(CX + xo + 1, y, AA_DARK)
        if i is None or i < 0.5:
            n = 2 * xo - 3
            for dx in range(-xo, xo + 1):
                do, left = xo - abs(dx), dx < 0
                if do == 0:
                    t = 6 if left else 0
                elif do == 1:
                    t = 4 if left else 2
                elif strut or on_x(dx + xo - 2, n, k, K):
                    t = 3 if dx <= 0 else 2
                else:
                    t = HOLE
                put(CX + dx, y, t)
            return
        xi = int(round(i))
        iw = 2 if xo - xi + 1 >= 8 else 1
        n = xo - xi + 1 - 2 - iw
        for side in (-1, 1):
            lit_outer = side < 0
            for a in range(xi, xo + 1):
                do, di = xo - a, a - xi
                p = do - 2
                if do == 0:
                    t = 6 if lit_outer else 0
                elif do == 1:
                    t = 4 if lit_outer else 2
                elif di == 0:
                    t = 1 if lit_outer else 5
                elif di == 1 and iw == 2:
                    t = 2 if lit_outer else 3
                elif strut or on_x(p, n, k, K):
                    t = 3
                elif open_holes or not (0 < p < n - 1 and 1 < k < K - 1 and
                                        not on_x(p - 1, n, k, K) and
                                        not on_x(p + 1, n, k, K)):
                    t = HOLE if open_holes else 1
                else:
                    t = HOLE
                put(CX + side * a, y, t)

    def band(y, half, fn):
        for dx in range(-half, half + 1):
            put(CX + dx, y, fn(dx))

    def lit(base, dx, k=12.0):
        return int(round(base - dx / k))

    # ---- legs, ground to first floor
    struts = [BASE_Y, 181, 175, 169, 164, 159]
    for y in range(BASE_Y, 158, -1):
        hp = BASE_Y - y
        leg_row(y, wo(hp), 20.0 - 8.0 * hp / 30.0, struts, False)

    # ---- the great arch between the legs, with hangers up to the deck
    ay = 181
    for y in range(159, ay + 1):
        for dx in range(-19, 20):
            if (CX + dx, y) in T:
                continue
            e_out = (dx / 18.5) ** 2 + ((y - ay) / 21.5) ** 2
            e_in = (dx / 16.0) ** 2 + ((y - ay) / 19.0) ** 2
            if e_out <= 1.0 < e_in:
                e_mid = (dx / 17.2) ** 2 + ((y - ay) / 20.2) ** 2
                t = (4 if dx < 0 else 3) if e_mid > 1.0 else 2
                put(CX + dx, y, t)
            elif e_out > 1.0 and dx % 4 == 0:
                put(CX + dx, y, 2)

    # ---- first floor
    band(158, 19, lambda dx: 1)
    band(157, 19, lambda dx: 0 if dx % 4 in (1, 2) else 3)
    band(156, 19, lambda dx: 2 if dx % 4 in (1, 2) else lit(4, dx))
    band(155, 20, lambda dx: lit(6, dx, 10))
    band(154, 20, lambda dx: lit(3.5, dx))
    band(153, 20, lambda dx: lit(5, dx) if dx % 2 == 0 else HOLE)
    band(152, 20, lambda dx: lit(6.5, dx, 10))

    # ---- legs, first to second floor
    struts = [151, 146, 141, 136, 131, 127]
    for y in range(151, 126, -1):
        hp = BASE_Y - y
        leg_row(y, wo(hp), 9.5 - 6.0 * (hp - 37) / 24.0, struts, True)

    # ---- second floor
    band(126, 11, lambda dx: 1)
    band(125, 12, lambda dx: 1 if dx % 3 == 0 else lit(3.5, dx, 8))
    band(124, 12, lambda dx: lit(5.5, dx, 8))
    band(123, 12, lambda dx: lit(4.5, dx, 8) if dx % 2 == 0 else HOLE)
    band(122, 12, lambda dx: lit(6.5, dx, 8))

    # ---- upper shaft: the four pillars converge, then one braced column
    struts = [121, 114, 107, 100, 93, 86, 79, 72, 65, 58, 51, 43]
    for y in range(121, 42, -1):
        hp = BASE_Y - y
        leg_row(y, wo(hp), 2.6 * (1.0 - (hp - 67) / 30.0), struts, True)

    # ---- third floor and top
    band(42, 5, lambda dx: 1)
    band(41, 5, lambda dx: lit(4, dx, 4))
    band(40, 5, lambda dx: 8 if dx % 2 == 0 and dx < 3 else 3)
    band(39, 5, lambda dx: lit(6, dx, 4))
    band(38, 4, lambda dx: lit(7, dx, 4))
    for y in range(37, 32, -1):
        band(y, 2, lambda dx: 7 if dx < 0 else (5 if dx == 0 else 2))
    for y in range(32, 29, -1):
        band(y, 1, lambda dx: 7 if dx < 0 else (5 if dx == 0 else 2))
    band(29, 1, lambda dx: 6)
    band(28, 0, lambda dx: 7)
    for y in range(27, 12, -1):
        put(CX, y, 5)
    band(21, 1, lambda dx: 4)
    band(25, 1, lambda dx: 4)

    def boost(y, t):
        """The low sun only reaches the upper tower; the base sits in the city's shadow."""
        hp = BASE_Y - y
        lit_face = t >= 4
        if hp < 37:
            return 0
        if hp < 100:
            return 1 if lit_face else 0
        return 2 if lit_face else 1

    for (x, y), t in T.items():
        if t == AA_LIT:
            t = 5
        elif t == AA_DARK:
            t = 1
        if t != HOLE:
            img[y][x] = TOWER[max(0, min(8, t + boost(y, t)))]
    img[12][CX] = BEACON


# --------------------------------------------------------------------------
# trees and hedges
# --------------------------------------------------------------------------
def draw_canopy(img, cx, cy, rx, ry, rng, blob=(2.2, 3.4)):
    blobs = []
    for row, by in enumerate(range(int(cy - ry), int(cy + ry) + 1, 3)):
        for bx in range(int(cx - rx) - 2, int(cx + rx) + 3, 4):
            jx = bx + (2 if row % 2 else 0) + rng.uniform(-1.0, 1.0)
            jy = by + rng.uniform(-0.8, 0.8)
            nx, ny = (jx - cx) / rx, (jy - cy) / ry
            if nx * nx + ny * ny <= 0.86:
                blobs.append((jx, jy, rng.uniform(*blob)))
    blobs.sort(key=lambda b: b[1])
    sun = 1.4 * math.exp(-(sun_dist(cx, cy) / 70.0) ** 2)
    mine = {}
    for bx, by, r in blobs:
        nx, ny = (bx - cx) / rx, (by - cy) / ry
        cv = -0.6 * nx - 0.8 * ny
        for y in range(int(by - r) - 1, int(by + r) + 2):
            for x in range(int(bx - r) - 1, int(bx + r) + 2):
                ux, uy = (x - bx) / r, (y - by) / r
                d2 = ux * ux + uy * uy
                if d2 > 1.0 or not (0 <= x < W and 0 <= y < H):
                    continue
                lv = -0.6 * ux - 0.8 * uy
                v = 2.0 + 1.7 * cv + 1.3 * lv + sun
                if d2 > 0.55 and lv < -0.3:
                    v = min(v, 1.0)
                mine[(x, y)] = ramp(v, x, y, len(TREE), 0.35)
                img[y][x] = TREE[mine[(x, y)]]
    for (x, y), i in mine.items():
        if (x - 1, y) in mine and (x, y - 1) in mine:
            continue
        facing = -0.6 * (x - cx) / rx - 0.8 * (y - cy) / ry
        if facing > 0.2:
            img[y][x] = TREE[min(len(TREE) - 1, i + (3 if facing > 0.6 else 2))]


def draw_trees(img):
    rng = random.Random(3)
    trunks = [12, 36, 60, 86, 106, 202, 226, 250]
    for tx in trunks:
        for y in range(170, QUAY_Y):
            for x in (tx - 1, tx, tx + 1):
                img[y][x] = TREE[2] if x == tx - 1 else TREE[0]
    for cx, cy, rx, ry in ((12, 170, 15, 12), (36, 166, 14, 13), (60, 164, 15, 14),
                           (86, 167, 14, 12), (106, 174, 11, 9), (250, 168, 14, 12),
                           (226, 164, 15, 14), (202, 167, 14, 12), (183, 175, 10, 8)):
        draw_canopy(img, cx, cy, rx, ry, rng)
    for cx in range(110, 182, 9):       # hedge in front of the tower's feet
        draw_canopy(img, cx, 184, 6, 3, rng, blob=(1.6, 2.4))


# --------------------------------------------------------------------------
# river wall, lamps, water, boat, birds
# --------------------------------------------------------------------------
def draw_quay(img):
    rng = random.Random(4)
    for x in range(W):
        img[QUAY_Y][x] = QUAY[5]
        img[QUAY_Y + 1][x] = QUAY[4]
        img[QUAY_Y + 2][x] = QUAY[1]
    worn = {}
    for y in range(QUAY_Y + 3, WATER_Y):
        r = y - (QUAY_Y + 3)
        course, ry = r // 4, r % 4
        for x in range(W):
            if y >= WATER_Y - 2:                 # wet, darkened foot of the wall
                img[y][x] = QUAY[1] if (y == WATER_Y - 2 and x % 5 in (0, 2)) else QUAY[0]
                continue
            off = 7 if course % 2 else 0
            bx, block = (x + off) % 14, (course, (x + off) // 14)
            if block not in worn:
                worn[block] = rng.random() < 0.35
            if ry == 3 or bx == 13:
                c = QUAY[1]
            elif (ry == 0 or bx == 0) and not worn[block]:
                c = QUAY[3]
            else:
                c = QUAY[2]
            img[y][x] = c
    for _ in range(26):                          # rain streaks under the coping
        x = rng.randrange(W)
        for y in range(QUAY_Y + 3, QUAY_Y + 3 + rng.randint(2, 6)):
            if img[y][x] != QUAY[1]:
                img[y][x] = QUAY[1]
    for rx in (52, 132, 244):                    # mooring rings
        ry = QUAY_Y + 7
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            img[ry + dy][rx + dx] = QUAY[0]
        img[ry - 1][rx] = QUAY[4]
    # arched outfall
    ax, ay = 92, WATER_Y - 1
    for y in range(ay - 7, ay + 1):
        for x in range(ax - 6, ax + 7):
            d = math.hypot((x - ax) / 1.0, (y - (ay - 1)) / 1.15)
            if y >= ay - 1:
                d = abs(x - ax)
            if d <= 3.6:
                img[y][x] = QUAY[0]
            elif d <= 5.2:
                img[y][x] = QUAY[4] if (y < ay - 3 and x <= ax) else QUAY[3]


LAMPS = [22, 62, 100, 190, 230]


def draw_lamps(img):
    for lx in LAMPS:
        top = QUAY_Y - 14                       # lantern cap row
        for y in range(top - 3, top + 8):
            for x in range(lx - 4, lx + 5):
                if 2.2 < math.hypot(x - lx, (y - top - 2) * 1.15) <= 3.7 and (x + y) % 2 == 0:
                    img[y][x] = LAMP_GLOW
        for y in range(top + 4, QUAY_Y):
            img[y][lx] = QUAY[0]
        for y, half in ((top - 1, 0), (top, 1), (top + 7, 1), (QUAY_Y - 2, 1), (QUAY_Y - 1, 1)):
            for dx in range(-half, half + 1):
                img[y][lx + dx] = QUAY[0]
        for y in (top + 1, top + 2, top + 3):
            img[y][lx - 1] = LAMP[0]
            img[y][lx] = LAMP[1]
            img[y][lx + 1] = LAMP[0]


def draw_water(img):
    rng = random.Random(9)
    rows = H - WATER_Y
    depth = [3 + (1 if rng.random() < 0.4 else 0) for _ in range(W)]
    for y in range(WATER_Y, H):
        r = y - WATER_Y
        offs = [0.0] * W
        x = -rng.randint(0, 8)
        while x < W:
            ln = rng.randint(3, 12)
            o = rng.choice((-0.9, -0.4, 0.4, 0.9) if r % 2 == 0 else (-0.35, 0.0, 0.35))
            for xx in range(max(0, x), min(W, x + ln)):
                offs[xx] = o
            x += ln
        for x in range(W):
            if r < depth[x]:                     # the wall's dark reflection
                img[y][x] = WATER[0] if r < depth[x] - 1 else WATER[1]
                continue
            q = r / rows
            sun = math.exp(-((x - SUN_X) / 28.0) ** 2) * (1.0 - 0.55 * q)
            v = 5.0 - 2.9 * q + 2.8 * sun + offs[x]
            img[y][x] = WATER[max(0, min(len(WATER) - 2, int(v)))]
        if r % 2 == 0 and r > 3:                 # sun glitter
            for _ in range(4):
                gx = int(rng.gauss(SUN_X, 9))
                for xx in range(gx, gx + rng.randint(1, 4)):
                    if 0 <= xx < W:
                        img[y][xx] = WATER[9] if rng.random() < 0.5 else WATER[8]
    for lx in LAMPS:                             # lamp reflections
        for y in range(WATER_Y + 1, H - 3, 2):
            w = rng.randint(0, 2)
            off = rng.randint(-1, 1)
            for xx in range(lx + off - w // 2, lx + off + w // 2 + 1):
                img[y][xx] = WATER[8] if y < WATER_Y + 9 else WATER[7]


BOAT_X0, BOAT_X1, BOAT_WL = 150, 228, 214      # stern, bow, waterline


def draw_boat(img):
    """A bateau-mouche gliding right, its glazed cabin lit for the evening cruise."""
    x0, x1, wl = BOAT_X0, BOAT_X1, BOAT_WL
    rng = random.Random(12)
    mine = {}

    def put(x, y, c):
        img[y][x] = c
        mine[(x, y)] = c

    # hull: raked bow on the right, rounded stern on the left
    for k, (si, bi) in enumerate(((0, 0), (0, 1), (1, 3), (3, 6))):
        for x in range(x0 + si, x1 - bi + 1):
            c = BOAT[4] if k == 0 else (BOAT[2] if k == 1 and x > x1 - 30 else BOAT[1] if k == 1 else BOAT[0])
            put(x, wl - 4 + k, c)
    # glazed cabin
    c0, c1 = x0 + 9, x1 - 22
    for x in range(c0, c1 + 1):
        if c0 < x < c1:
            put(x, wl - 10, BOAT[4])
        put(x, wl - 9, BOAT[3])
        put(x, wl - 5, BOAT[2])
        for y in (wl - 8, wl - 7, wl - 6):
            if (x - c0) % 4 == 0:
                c = BOAT[1]
            else:
                c = WIN[0] if y < wl - 6 else WIN[1]
            put(x, y, c)
    for x in range(c0 + 2, c1 - 1, 4):           # passengers against the light
        if rng.random() < 0.55:
            put(x, wl - 7, BOAT[1])
            put(x, wl - 6, BOAT[1])
            put(x + 1, wl - 6, BOAT[1])
    # pilot house on the roof
    for x in range(c1 - 9, c1 - 2):
        put(x, wl - 12, BOAT[4] if x < c1 - 3 else BOAT[3])
        put(x, wl - 11, BOAT[1] if x in (c1 - 9, c1 - 3) else WIN[0])
    # open decks with railings, fore and aft
    for xa, xb in ((x0 + 1, c0 - 1), (c1 + 1, x1 - 5)):
        for x in range(xa, xb + 1):
            put(x, wl - 6, BOAT[3])
            if x % 2 == 0:
                put(x, wl - 5, BOAT[2])
    # stern flag (tricolore) and bow light
    for y in range(wl - 14, wl - 5):
        put(x0 + 2, y, BOAT[3])
    for i, c in enumerate((FLAG_BLUE, LAMP[1], BEACON)):
        put(x0 + 3 + i, wl - 14, c)
        put(x0 + 3 + i, wl - 13, c)
    put(x1 - 5, wl - 7, LAMP[1])

    # reflection, broken up by ripples
    refl = {BOAT[4]: WATER[4], BOAT[3]: WATER[3], BOAT[2]: WATER[2], BOAT[1]: WATER[0],
            BOAT[0]: WATER[0], WIN[0]: WATER[8], WIN[1]: WATER[7], LAMP[1]: WATER[9],
            FLAG_BLUE: WATER[2], BEACON: WATER[6]}
    for r in range(0, 10):
        ys, yd = wl - 1 - r, wl + r
        if yd >= H:
            break
        shift = (1, 0, -1, 0)[r % 4]
        x = x0 - 1
        while x < x1 + 2:                       # ripples cut the reflection into dashes
            run = rng.randint(4, 10)
            gap = rng.randint(1, 3) if r > 2 else 0
            for xx in range(x, min(x + run, x1 + 2)):
                c = mine.get((xx - shift, ys))
                if c is None:
                    continue
                if wl - 8 <= ys <= wl - 6 and c0 <= xx - shift <= c1:
                    c = WIN[0] if ys < wl - 6 else WIN[1]
                img[yd][xx] = refl[c]
            x += run + gap
    # wake trailing from the stern, bow wave
    for k in range(6):
        xs = x0 - 3 - k * 7
        for xx in range(xs - (4 - k // 2), xs):
            if xx >= 0:
                img[wl - 1 + (k % 2) * 2][xx] = WATER[7] if k < 2 else WATER[6]
    for xx in range(x1 - 6, x1 + 2):
        img[wl - 1][xx] = WATER[9] if xx > x1 - 3 else WATER[8]


def draw_birds(img):
    for bx, by, flap in ((96, 104, 0), (104, 99, 1), (88, 98, 1), (112, 106, 0)):
        pts = ([(-2, 0), (-1, -1), (0, 0), (1, -1), (2, 0)] if flap else
               [(-2, -1), (-1, 0), (0, 0), (1, 0), (2, -1)])
        for dx, dy in pts:
            img[by + dy][bx + dx] = TOWER[1]


# --------------------------------------------------------------------------
# constraint enforcement + output
# --------------------------------------------------------------------------
def dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def enforce_tile_limit(img, limit=16):
    """Merge the rarest colour of any over-full 8x8 tile into its nearest neighbour."""
    fixed = 0
    for ty in range(0, H, 8):
        for tx in range(0, W, 8):
            while True:
                count = {}
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        count[img[y][x]] = count.get(img[y][x], 0) + 1
                if len(count) <= limit:
                    break
                fixed += 1
                rare = min(count, key=lambda c: count[c])
                near = min((c for c in count if c != rare), key=lambda c: dist2(c, rare))
                for y in range(ty, ty + 8):
                    for x in range(tx, tx + 8):
                        if img[y][x] == rare:
                            img[y][x] = near
    return fixed


def render():
    img = [[None] * W for _ in range(H)]
    draw_sky(img)
    draw_stars(img)
    draw_moon(img)
    draw_sun(img)
    draw_clouds(img)
    draw_birds(img)
    draw_far_city(img)
    draw_haussmann(img, 0, 40, 114, 1, False)
    draw_haussmann(img, 214, 256, 110, 2, True)
    draw_tower(img)
    draw_trees(img)
    draw_quay(img)
    draw_lamps(img)
    draw_water(img)
    draw_boat(img)
    merges = enforce_tile_limit(img)
    return img, merges


def main():
    args = sys.argv[1:]
    preview = None
    if '--preview' in args:
        i = args.index('--preview')
        preview = args[i + 1]
        del args[i:i + 2]
    out = args[0] if args else os.path.join('output', 'eiffel_tower_snes.png')

    img, merges = render()
    palette = sorted({px for row in img for px in row})
    assert len(palette) <= 128, f'{len(palette)} colours'
    index = {c: i for i, c in enumerate(palette)}
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    write_indexed(out, [[index[px] for px in row] for row in img], palette)
    print(f'wrote {out}: {len(palette)} colours, {merges} tile merges')

    if preview:
        os.makedirs(preview, exist_ok=True)
        s = 4
        big = [[px for px in row for _ in range(s)] for row in img for _ in range(s)]
        write_rgb(os.path.join(preview, 'preview_x4.png'), big)


if __name__ == '__main__':
    main()
