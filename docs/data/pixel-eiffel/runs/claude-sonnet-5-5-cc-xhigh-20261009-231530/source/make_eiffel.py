#!/usr/bin/env python3
"""Pixel-art Eiffel Tower at dusk in 16-bit colour (RGB565), saved as a JPG.

The picture is drawn on a 193x256 grid, every colour is snapped to the RGB565
palette (5 bits red, 6 bits green, 5 bits blue = 65,536 possible colours), then
scaled up 4x with nearest-neighbour so the pixels stay crisp. ffmpeg only does
the final JPEG encoding (the python standard library has no JPEG writer).
"""
import math
import os
import random
import subprocess

W, H = 193, 256
SCALE = 4
AX = 96            # axis column of the tower
GROUND = 230       # first ground row
S = 0.6            # pixels per metre (tower is 330 m with its antenna)
random.seed(1889)

OUT_DIR = "output"
OUT = os.path.join(OUT_DIR, "eiffel_tower_pixel_16bit.jpg")
TMP = "eiffel_tmp.ppm"

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bay(x, y):
    return (BAYER[y & 3][x & 3] + 0.5) / 16.0


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))


def shade(c, k):
    return tuple(clamp(v * k) for v in c)


def dlevel(a, x, y, levels):
    """Ordered-dither an alpha in [0,1] down to a few levels."""
    return math.floor(a * levels + bay(x, y)) / levels


img = [[(0, 0, 0)] * W for _ in range(H)]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def blend(x, y, c, a):
    if a > 0 and 0 <= x < W and 0 <= y < H:
        img[y][x] = mix(img[y][x], c, a)


# --------------------------------------------------------------------------
# Sky
# --------------------------------------------------------------------------
SKY = [(0.00, (8, 10, 40)), (0.30, (26, 26, 84)), (0.55, (78, 42, 118)),
       (0.72, (170, 66, 122)), (0.86, (246, 114, 96)), (0.95, (255, 166, 100)),
       (1.00, (255, 214, 132))]


def sky_color(y):
    t = min(1.0, y / GROUND)
    for (t0, c0), (t1, c1) in zip(SKY, SKY[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0))
    return SKY[-1][1]


STEP = 13
for y in range(GROUND):
    c = sky_color(y + 0.5)
    for x in range(W):
        img[y][x] = tuple(min(255, math.floor(v / STEP + bay(x, y)) * STEP) for v in c)

# moon with a dithered halo
MX, MY, MR = 30, 52, 9
for y in range(MY - 30, MY + 31):
    for x in range(MX - 30, MX + 31):
        d = math.hypot(x - MX, y - MY)
        if d < 30:
            a = (1 - d / 30) ** 2 * 0.45
            blend(x, y, (255, 226, 170), dlevel(a, x, y, 6))
for y in range(MY - MR - 2, MY + MR + 3):
    for x in range(MX - MR - 2, MX + MR + 3):
        in1 = math.hypot(x - MX, y - MY) <= MR
        in2 = math.hypot(x - (MX + 4), y - (MY - 3)) <= MR - 1
        if in1 and not in2:
            put(x, y, (255, 246, 206))

# stars
for _ in range(150):
    x = random.randrange(W)
    y = int(random.random() ** 1.7 * 150)
    if math.hypot(x - MX, y - MY) < 16:
        continue
    put(x, y, (255, 255, 236) if random.random() < 0.35 else (176, 176, 232))
for _ in range(9):
    x = random.randrange(8, W - 8)
    y = random.randrange(6, 110)
    if math.hypot(x - MX, y - MY) < 18:
        continue
    put(x, y, (255, 255, 255))
    for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        put(x + ox, y + oy, (186, 186, 240))


# clouds lit from below by the horizon glow
def cloud(cx, cy, n, rx_rng, ry_rng, spread):
    cells = set()
    for _ in range(n):
        ex = cx + random.uniform(-spread, spread)
        ey = cy + random.uniform(-2, 2)
        rx = random.uniform(*rx_rng)
        ry = random.uniform(*ry_rng)
        for y in range(int(ey - ry) - 1, int(ey + ry) + 2):
            for x in range(int(ex - rx) - 1, int(ex + rx) + 2):
                if ((x - ex) / rx) ** 2 + ((y - ey) / ry) ** 2 <= 1:
                    cells.add((x, y))
    for (x, y) in cells:
        if not (0 <= x < W and 0 <= y < GROUND):
            continue
        t = y / GROUND
        body = mix((46, 28, 86), (122, 58, 118), t)
        if (x, y + 1) not in cells:
            c = mix((190, 96, 130), (255, 156, 104), t)
        elif (x, y + 2) not in cells:
            c = mix((130, 66, 124), (214, 104, 112), t)
        elif (x, y - 1) not in cells:
            c = shade(body, 1.3)
        else:
            c = body
        if (x + y) % 2 == 0 and (x, y + 1) in cells and (x, y + 2) not in cells:
            c = mix(c, body, 0.5)
        put(x, y, c)


cloud(26, 176, 6, (9, 16), (2, 4), 20)
cloud(168, 158, 6, (9, 16), (2, 4), 18)
cloud(160, 196, 5, (10, 18), (2, 3.5), 18)
cloud(42, 138, 5, (8, 14), (2, 3), 14)
cloud(150, 118, 4, (7, 12), (1.5, 3), 12)
cloud(20, 206, 4, (8, 14), (1.5, 3), 12)

# --------------------------------------------------------------------------
# Paris skyline
# --------------------------------------------------------------------------


def skyline(color, hmin, hmax, wmin, wmax, win_p, win_cols):
    x = -random.randint(0, 6)
    while x < W:
        bw = random.randint(wmin, wmax)
        bh = random.randint(hmin, hmax)
        top = GROUND - bh
        for xx in range(x, x + bw):
            for yy in range(top, GROUND):
                put(xx, yy, color)
        roof = random.choice(["flat", "mansard", "mansard", "gable"])
        if roof == "mansard" and bw >= 6:
            for xx in range(x + 1, x + bw - 1):
                put(xx, top - 1, color)
            for xx in range(x + 2, x + bw - 2):
                put(xx, top - 2, color)
        elif roof == "gable" and bw >= 6:
            for k in range(bw // 2):
                for xx in range(x + k, x + bw - k):
                    put(xx, top - 1 - k, color)
        if bw >= 5 and random.random() < 0.6:
            cx = x + random.randint(1, bw - 2)
            for yy in range(top - 4, top):
                put(cx, yy, color)
        if win_p:
            for xx in range(x + 1, x + bw - 1, 2):
                for yy in range(top + 2, GROUND - 1, 3):
                    if random.random() < win_p:
                        put(xx, yy, random.choice(win_cols))
        x += bw + random.choice([0, 0, 1])


skyline((132, 66, 118), 6, 15, 7, 15, 0, ())
skyline((46, 26, 70), 5, 13, 6, 14, 0.14, ((255, 204, 104), (255, 170, 84), (214, 132, 92)))

# Les Invalides dome (right) and a church spire (left)
DX = 148
for xx in range(DX - 11, DX + 12):
    for yy in range(GROUND - 8, GROUND):
        put(xx, yy, (44, 26, 68))
for xx in range(DX - 5, DX + 6):
    for yy in range(GROUND - 13, GROUND - 8):
        put(xx, yy, (44, 26, 68))
for y in range(GROUND - 22, GROUND - 13):
    for x in range(DX - 6, DX + 7):
        dy = (GROUND - 13) - y
        if (x - DX) ** 2 / 36.0 + dy ** 2 / 81.0 <= 1:
            k = 0.78 + 0.35 * (1 - (x - DX + 6) / 12.0) - 0.1 * dy / 9
            put(x, y, shade((236, 170, 70), k))
for yy in range(GROUND - 30, GROUND - 22):
    put(DX, yy, (240, 190, 80))
put(DX, GROUND - 31, (255, 240, 170))


# --------------------------------------------------------------------------
# Ground (Champ de Mars)
# --------------------------------------------------------------------------
for y in range(GROUND, H):
    t = (y - GROUND) / (H - GROUND)
    lawn = mix((74, 84, 76), (14, 42, 46), t ** 0.6)
    if ((y - GROUND) // 3) % 2:
        lawn = shade(lawn, 0.9)
    half = 9 + (y - GROUND + 1) * 0.95
    for x in range(W):
        c = lawn
        if random.random() < 0.07:
            c = shade(c, 1.22)
        dxp = abs(x - AX)
        if dxp <= half:
            c = mix((176, 134, 126), (78, 62, 92), t ** 0.7)
            if random.random() < 0.12:
                c = shade(c, 0.88)
            if dxp > half - 1.3:
                c = shade(c, 1.28)
        put(x, y, c)

# warm pool of floodlight under the tower
for y in range(GROUND, H):
    for x in range(W):
        d = math.hypot((x - AX) / 62.0, (y - GROUND) / 22.0)
        if d < 1:
            blend(x, y, (255, 176, 76), dlevel((1 - d) ** 1.4 * 0.62, x, y, 6))

# --------------------------------------------------------------------------
# Searchlight beams (drawn behind the tower)
# --------------------------------------------------------------------------
TIP_Y = int(round(GROUND - 330 * S))
for theta in (-66, 52, 81):
    th = math.radians(theta)
    ux, uy = math.sin(th), -math.cos(th)
    for y in range(0, TIP_Y + 1):
        for x in range(W):
            dx, dy = x - AX, y - TIP_Y
            d = dx * ux + dy * uy
            if d <= 3:
                continue
            p = abs(dx * uy - dy * ux)
            hwid = 0.8 + d * 0.045
            if p >= hwid:
                continue
            a = (1 - p / hwid) ** 0.6 * max(0.0, 1 - d / 170.0) * 0.85
            blend(x, y, (255, 234, 178), dlevel(a, x, y, 3))

# --------------------------------------------------------------------------
# The tower
# --------------------------------------------------------------------------
GOLD_HI = (255, 228, 142)
GOLD = (242, 178, 66)
GOLD_MID = (204, 128, 42)
GOLD_LO = (142, 82, 34)
IRON_DARK = (62, 32, 28)
BACK = (44, 24, 30)
LIGHT = (255, 246, 196)

T = [[None] * W for _ in range(H)]
sparks = []


def tput(x, y, c, a=1.0, emissive=False):
    if 0 <= x < W and 0 <= y < H:
        if not emissive and x > AX:
            c = shade(c, 0.8)
        T[y][x] = (c, a)


def tline(x0, y0, x1, y1, c, a=1.0):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        tput(x0, y0, c, a)
        if c == GOLD:
            sparks.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def yh(h):
    return GROUND - h * S


def hw(y):
    h = (GROUND - (y + 0.5)) / S
    return 62.5 * math.exp(-h / 100.0) * S


def rr(y):
    return int(round(hw(y)))


P1_TOP, P1_BOT = int(round(yh(57))) - 3, int(round(yh(57))) + 2      # 6 rows
P2_TOP, P2_BOT = int(round(yh(115))) - 3, int(round(yh(115))) + 1    # 5 rows
P3_TOP, P3_BOT = int(round(yh(276))) - 1, int(round(yh(276))) + 1    # 3 rows


def platform(top, bot, extra):
    r = rr((top + bot) // 2) + extra
    n = bot - top + 1
    for i, y in enumerate(range(top, bot + 1)):
        if i == 0:
            for dx in range(-r - 1, r + 2):
                tput(AX + dx, y, GOLD_HI)
        elif i == n - 1:
            for dx in range(-r, r + 1):
                tput(AX + dx, y, IRON_DARK)
        elif i == 1 or (n == 6 and i == 4):
            for dx in range(-r, r + 1):
                if dx % 2 == 0:
                    tput(AX + dx, y, LIGHT, emissive=True)
                else:
                    tput(AX + dx, y, GOLD_MID)
        else:
            for dx in range(-r, r + 1):
                tput(AX + dx, y, GOLD)


# --- legs, arch and spandrel ------------------------------------------------
yc, ea, eb = yh(10), 38 * S, 37 * S
opening, leg = set(), {}
for y in range(P1_BOT + 1, GROUND):
    r = rr(y)
    yy = y + 0.5
    if yy >= yc:
        inner = ea
    else:
        dyy = yc - yy
        inner = ea * math.sqrt(max(0.0, 1 - (dyy / eb) ** 2)) if dyy < eb else 0
    ir = int(round(inner))
    for dx in range(-r, r + 1):
        if abs(dx) < ir:
            opening.add((AX + dx, y))
        else:
            leg[(AX + dx, y)] = dx

for (x, y), dx in leg.items():
    r = rr(y)
    near = [abs(i) + abs(j) for i in range(-2, 3) for j in range(-2, 3)
            if (x + i, y + j) in opening]
    if near and min(near) <= 1:
        c = GOLD_HI
    elif near and min(near) <= 2:
        c = GOLD
    elif abs(dx) == r:
        c = GOLD_HI
    elif (x + y) % 5 == 0 or (x - y) % 5 == 0:
        c = GOLD
        sparks.append((x, y))
    elif y % 14 == 0:
        c = GOLD_MID
    else:
        c = BACK
    tput(x, y, c)

# stone pedestals
for sgn in (-1, 1):
    r = rr(GROUND - 1)
    ir = int(round(ea))
    for y in range(GROUND - 3, GROUND):
        for dx in range(ir - 1, r + 3):
            tput(AX + sgn * dx, y, (150, 112, 112) if y == GROUND - 3 else (104, 78, 88))

platform(P1_TOP, P1_BOT, 4)

# --- first platform -> second platform -------------------------------------
rows2 = list(range(P2_BOT + 1, P1_TOP))
n2 = len(rows2)


def pillar_w(y):
    t = (P1_TOP - 1 - y) / (n2 - 1)
    return int(round(lerp(7, 4, t)))


for y in rows2:
    r, pw = rr(y), pillar_w(y)
    for k in range(pw):
        d = r - k
        c = GOLD_HI if k == 0 else (GOLD if k == pw - 1 else None)
        if c is None:
            c = GOLD_MID if (d + y) % 4 == 0 or (d - y) % 4 == 0 else BACK
        tput(AX - d, y, c)
        tput(AX + d, y, c)
bounds2 = [P1_TOP - 1, P1_TOP - 1 - n2 // 3, P1_TOP - 1 - 2 * n2 // 3, P2_BOT + 1]
for ya, yb in zip(bounds2, bounds2[1:]):
    xa, xb = rr(ya) - pillar_w(ya), rr(yb) - pillar_w(yb)
    tline(AX - xa, ya, AX + xb, yb, GOLD)
    tline(AX + xa, ya, AX - xb, yb, GOLD)
    tline(AX - xa, ya, AX + xa, ya, GOLD_MID)
tline(AX - rr(bounds2[-1]) + pillar_w(bounds2[-1]), bounds2[-1],
      AX + rr(bounds2[-1]) - pillar_w(bounds2[-1]), bounds2[-1], GOLD_MID)

platform(P2_TOP, P2_BOT, 3)

# --- second platform -> third platform (lattice shaft) ---------------------
top3, bot3 = P3_BOT + 1, P2_TOP - 1
for y in range(top3, bot3 + 1):
    r = rr(y)
    for dx in range(-r + 1, r):
        tput(AX + dx, y, BACK, 0.62)
    for k, c in ((0, GOLD_HI), (1, GOLD)):
        if r - k > 0:
            tput(AX - (r - k), y, c)
            tput(AX + (r - k), y, c)
bnd, y = [bot3], bot3
while y > top3:
    ny = y - max(5, int(round(hw(y) * 1.25)))
    if ny - top3 < 5:
        ny = top3
    bnd.append(ny)
    y = ny
for ya, yb in zip(bnd, bnd[1:]):
    ra, rb = max(1, rr(ya) - 1), max(1, rr(yb) - 1)
    tline(AX - ra, ya, AX + rb, yb, GOLD)
    tline(AX + ra, ya, AX - rb, yb, GOLD)
    tline(AX - rr(ya), ya, AX + rr(ya), ya, GOLD_MID)

# --- third platform, lantern, spire ----------------------------------------
for i, y in enumerate(range(P3_TOP, P3_BOT + 1)):
    r = (5, 6, 5)[i]
    for dx in range(-r, r + 1):
        if i == 0:
            tput(AX + dx, y, GOLD_HI)
        elif i == 1:
            tput(AX + dx, y, LIGHT if dx % 2 == 0 else GOLD_MID, emissive=dx % 2 == 0)
        else:
            tput(AX + dx, y, IRON_DARK)
cabin = [(P3_TOP - 1, 3), (P3_TOP - 2, 3), (P3_TOP - 3, 3), (P3_TOP - 4, 3),
         (P3_TOP - 5, 4), (P3_TOP - 6, 2), (P3_TOP - 7, 2), (P3_TOP - 8, 2),
         (P3_TOP - 9, 1), (P3_TOP - 10, 1), (P3_TOP - 11, 1)]
for i, (y, r) in enumerate(cabin):
    for dx in range(-r, r + 1):
        if i in (1, 2) and dx % 2 == 0:
            tput(AX + dx, y, LIGHT, emissive=True)
        elif i == 4:
            tput(AX + dx, y, GOLD_HI)
        elif abs(dx) == r:
            tput(AX + dx, y, GOLD)
        else:
            tput(AX + dx, y, GOLD_MID if i % 2 else BACK)
spire_top = cabin[-1][0] - 1
for y in range(TIP_Y, spire_top + 1):
    k = y - TIP_Y
    tput(AX, y, GOLD_HI if k % 4 < 2 else GOLD, emissive=True)
    if y in (TIP_Y + 8, TIP_Y + 9, TIP_Y + 15, TIP_Y + 16):
        tput(AX - 1, y, GOLD)
        tput(AX + 1, y, GOLD)

# --------------------------------------------------------------------------
# Glow around the tower (horizontal distance to the nearest tower pixel)
# --------------------------------------------------------------------------
GR = 15
for y in range(H):
    xs = [x for x in range(W) if T[y][x] is not None]
    if not xs:
        continue
    for x in range(W):
        if T[y][x] is not None or y >= GROUND:
            continue
        d = min(abs(x - xx) for xx in xs)
        if d < GR:
            a = (1 - d / GR) ** 2 * 0.6
            blend(x, y, (255, 160, 64), dlevel(a, x, y, 6))
# beacon halo at the very top
for y in range(TIP_Y - 10, TIP_Y + 11):
    for x in range(AX - 10, AX + 11):
        d = math.hypot(x - AX, y - TIP_Y)
        if d < 10 and T[y][x] is None:
            blend(x, y, (255, 240, 190), dlevel((1 - d / 10) ** 2 * 0.8, x, y, 6))

# composite tower
for y in range(H):
    for x in range(W):
        if T[y][x] is not None:
            c, a = T[y][x]
            img[y][x] = mix(img[y][x], c, a)

# twinkling lights on the lattice + beacon star
random.shuffle(sparks)
for (x, y) in sparks[:16]:
    if y < GROUND - 8:
        put(x, y, (255, 252, 226))
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            blend(x + ox, y + oy, (255, 232, 150), 0.55)
put(AX, TIP_Y, (255, 255, 255))
for k in (1, 2):
    for ox, oy in ((k, 0), (-k, 0), (0, k), (0, -k)):
        blend(AX + ox, TIP_Y + oy, (255, 248, 210), 0.9 if k == 1 else 0.55)

# --------------------------------------------------------------------------
# Foreground trees and lamps
# --------------------------------------------------------------------------
LEAF = [(-0.35, (6, 22, 32)), (0.0, (12, 40, 44)), (0.4, (28, 74, 58)),
        (0.75, (70, 108, 60)), (9.0, (154, 140, 72))]


def canopy(cx, cy, r, toward):
    circles = [(cx, cy, r * 0.85)]
    for _ in range(max(3, int(r * 0.9))):
        a = random.uniform(0, math.tau)
        d = random.uniform(0.15, 0.7) * r
        circles.append((cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8, r * random.uniform(0.38, 0.62)))
    circles.sort(key=lambda c: c[1])
    for ccx, ccy, cr in circles:
        for y in range(int(ccy - cr) - 1, int(ccy + cr) + 2):
            for x in range(int(ccx - cr) - 1, int(ccx + cr) + 2):
                nx, ny = (x - ccx) / cr, (y - ccy) / cr
                if nx * nx + ny * ny > 1:
                    continue
                v = nx * toward * 0.6 - ny * 0.8 + (bay(x, y) - 0.5) * 0.35
                for lim, col in LEAF:
                    if v < lim:
                        put(x, y, col)
                        break


def tree(cx, by, r):
    toward = 1 if cx < AX else -1
    trunk = max(2, int(r * 0.7))
    for y in range(by - trunk, by):
        put(cx, y, (34, 22, 30))
        if r > 5:
            put(cx + 1, y, (26, 16, 24))
    canopy(cx, by - trunk - r * 0.8, r, toward)


def lamp(x, by, h):
    for y in range(by - h, by):
        put(x, y, (24, 20, 38))
    ly = by - h - 1
    for y in range(ly - 6, ly + 7):
        for xx in range(x - 6, x + 7):
            d = math.hypot(xx - x, y - ly)
            if d < 6:
                blend(xx, y, (255, 206, 112), dlevel((1 - d / 6) ** 2 * 0.75, xx, y, 5))
    put(x, ly, (255, 244, 190))
    put(x - 1, ly, (255, 214, 130))
    put(x + 1, ly, (255, 214, 130))
    put(x, ly - 1, (255, 214, 130))


# distant tree bumps along the horizon
for lo, hi in ((0, 52), (140, W)):
    for x in range(lo, hi, 3):
        r = random.randint(2, 4)
        canopy(x + 1, GROUND - 1, r, 1 if x < AX else -1)

# tree-lined avenue
for by, r in ((235, 3.0), (241, 4.0), (249, 5.5), (258, 7.5)):
    half = 9 + (by - GROUND + 1) * 0.95
    for sgn in (-1, 1):
        tree(int(AX + sgn * (half + r + 3)), by, r)
for by, h in ((238, 7), (252, 12)):
    half = 9 + (by - GROUND + 1) * 0.95
    for sgn in (-1, 1):
        lamp(int(AX + sgn * (half + 1)), by, h)

# big framing trees in the lower corners
canopy(2, 232, 26, 1)
canopy(W - 3, 236, 28, -1)
for sx_, sy_ in ((14, 222), (176, 224)):
    canopy(sx_, sy_, 13, 1 if sx_ < AX else -1)

# --------------------------------------------------------------------------
# Quantise to RGB565, upscale, encode
# --------------------------------------------------------------------------


def q565(c):
    r, g, b = (clamp(int(round(v))) for v in c)
    r5, g6, b5 = round(r * 31 / 255), round(g * 63 / 255), round(b * 31 / 255)
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


pix = [[q565(c) for c in row] for row in img]
print("distinct RGB565 colours used:", len({c for row in pix for c in row}))

os.makedirs(OUT_DIR, exist_ok=True)
with open(TMP, "wb") as f:
    f.write(b"P6\n%d %d\n255\n" % (W * SCALE, H * SCALE))
    for row in pix:
        line = b"".join(bytes(c) * SCALE for c in row)
        f.write(line * SCALE)

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", TMP, "-frames:v", "1",
                "-q:v", "1", "-pix_fmt", "yuvj444p", OUT], check=True)
os.remove(TMP)
print("wrote", OUT, os.path.getsize(OUT), "bytes")
