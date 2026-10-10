#!/usr/bin/env python3
"""16-bit style pixel art of the Eiffel Tower at sunset.

Renders a 256x224 (SNES resolution) image, quantizes every color to
RGB555 (16-bit color), and writes a PPM. build.sh upscales it to a JPG.
"""
import math
import random
import sys

W, H = 256, 224
CX = 128
HORIZON = 196
random.seed(1889)

img = [[(0, 0, 0)] * W for _ in range(H)]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dither(x, y, t):
    """True if the pixel should take the 'next' color for fraction t."""
    return t * 16 > BAYER[y % 4][x % 4] + 0.5


# ---------------------------------------------------------------- sky
SKY = [
    (16, 12, 48), (32, 20, 72), (56, 28, 96), (96, 40, 112),
    (144, 52, 116), (192, 72, 104), (228, 104, 88), (244, 140, 72),
    (248, 180, 88), (252, 216, 128),
]


def sky_at(x, y):
    t = (y / HORIZON) ** 1.25 * (len(SKY) - 1)
    i = min(int(t), len(SKY) - 2)
    return SKY[i + 1] if dither(x, y, t - i) else SKY[i]


for y in range(H):
    for x in range(W):
        img[y][x] = sky_at(x, min(y, HORIZON))

# stars
for _ in range(70):
    x, y = random.randrange(W), random.randrange(70)
    if random.random() < y / 80:
        continue
    put(x, y, random.choice([(248, 248, 255), (200, 200, 248), (160, 140, 220)]))
for sx, sy in [(30, 14), (210, 22), (90, 30)]:  # twinkling crosses
    put(sx, sy, (255, 255, 255))
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        put(sx + dx, sy + dy, (168, 160, 232))

# sun with retro stripes in the lower half
SUN_X, SUN_Y, SUN_R = 200, 162, 22
for y in range(SUN_Y - SUN_R - 3, SUN_Y + SUN_R + 1):
    for x in range(SUN_X - SUN_R - 3, SUN_X + SUN_R + 4):
        d = math.hypot(x - SUN_X, y - SUN_Y)
        if d <= SUN_R:
            rel = (y - (SUN_Y - SUN_R)) / (2 * SUN_R)
            k = y - SUN_Y
            if k > 0 and k % 6 < k // 6 + 1:  # gaps widen toward the horizon
                continue
            put(x, y, lerp((255, 248, 184), (252, 152, 64), rel))
        elif d <= SUN_R + 3 and dither(x, y, 0.5 - (d - SUN_R) / 7):
            put(x, y, (252, 200, 120))

# clouds: flat-bottomed puffs lit from below by the sun
CLOUDS = [(40, 58, 46), (176, 44, 38), (100, 96, 54), (226, 104, 40), (8, 120, 34), (150, 132, 44)]
for (cx, cy, cw) in CLOUDS:
    puffs = []
    x = cx - cw // 2
    while x < cx + cw // 2:
        r = random.randint(4, 8)
        puffs.append((x, cy - random.randint(0, 4), r))
        x += r
    for y in range(cy - 14, cy + 3):
        for x in range(cx - cw // 2 - 8, cx + cw // 2 + 8):
            if y > cy + 2:
                continue
            inside = any((x - px) ** 2 + ((y - py) * 1.6) ** 2 <= pr * pr for px, py, pr in puffs)
            if not inside:
                continue
            below = not any((x - px) ** 2 + ((y + 2 - py) * 1.6) ** 2 <= pr * pr for px, py, pr in puffs) or y >= cy + 1
            above = not any((x - px) ** 2 + ((y - 2 - py) * 1.6) ** 2 <= pr * pr for px, py, pr in puffs)
            warm = cy / HORIZON
            if below:
                c = lerp((248, 152, 160), (255, 200, 120), warm)
            elif above:
                c = lerp((120, 64, 140), (176, 80, 120), warm)
            else:
                c = lerp((176, 88, 152), (228, 120, 112), warm)
            put(x, y, c)

# ---------------------------------------------------------------- skyline
def building_layer(base, hmin, hmax, color, window_p, seed):
    rnd = random.Random(seed)
    x = 0
    while x < W:
        w = rnd.randint(6, 16)
        h = rnd.randint(hmin, hmax)
        top = base - h
        roof = rnd.random()
        for bx in range(x, min(x + w, W)):
            for by in range(top, base + 1):
                put(bx, by, color)
            if roof < 0.5:  # mansard roof
                inset = min(bx - x, x + w - 1 - bx)
                for r in range(min(inset, 3)):
                    put(bx, top - 1 - r, color)
            if roof > 0.8 and (bx - x) % 4 == 1:  # chimneys
                put(bx, top - 1, color)
                put(bx, top - 2, color)
        for wy in range(top + 2, base - 1, 3):
            for wx in range(x + 1, x + w - 1, 2):
                if rnd.random() < window_p:
                    put(wx, wy, rnd.choice([(255, 216, 112), (248, 176, 88)]))
        x += w + rnd.randint(0, 2)


building_layer(HORIZON, 8, 22, (120, 60, 120), 0.0, 7)
building_layer(HORIZON + 2, 4, 14, (72, 36, 88), 0.12, 11)

# Les Invalides golden dome on the left
DX, DY = 40, 170
for y in range(DY - 2, HORIZON + 2):
    for x in range(DX - 12, DX + 13):
        put(x, y, (64, 32, 80))
for y in range(DY - 14, DY - 1):
    for x in range(DX - 9, DX + 10):
        if (x - DX) ** 2 + ((y - DY + 2) * 0.75) ** 2 <= 81:
            c = (248, 200, 88) if x > DX + 2 else (200, 136, 48) if x > DX - 4 else (136, 80, 40)
            if (x - DX) % 3 == 0:
                c = lerp(c, (64, 32, 40), 0.4)
            put(x, y, c)
for y in range(DY - 22, DY - 13):
    put(DX, y, (248, 216, 112))
    if y > DY - 18:
        put(DX - 1, y, (200, 136, 48))
        put(DX + 1, y, (252, 232, 152))

# ---------------------------------------------------------------- tower
DARK = (40, 20, 40)
MID = (80, 40, 52)
LIGHT = (128, 64, 60)
RIM = (248, 160, 80)
GLOW = (255, 232, 140)


def profile(y):
    """Return list of (left, right) solid spans relative to the center line."""
    if y < 12:
        return []
    if y < 26:
        return [(0, 0)]
    if y < 30:
        return [(-1, 1)]
    if y < 37:
        return [(-3, 3)]
    if y < 44:
        return [(-2, 2)]
    if y < 108:
        t = (y - 44) / 64
        o = round(2 + 7 * t ** 1.7)
        return [(-o, o)]
    if y < 113:
        return [(-13, 13)]
    if y < 146:
        t = (y - 113) / 33
        o = round(10 + 14 * t ** 1.3)
        if y > 121:
            i = round(9 * ((y - 121) / 25) ** 0.7)
            if i >= 1:
                return [(-o, -i), (i, o)]
        return [(-o, o)]
    if y < 154:
        return [(-30, 30)]
    if y <= HORIZON:
        t = (y - 154) / (HORIZON - 154)
        o = round(26 + 32 * t ** 1.6)
        if y > 160:
            i = round(40 * math.sqrt(max(0, 1 - ((HORIZON - y) / 36) ** 2)))
            if i >= 1:
                return [(-o, -i), (i, o)]
        return [(-o, o)]
    return []


for y in range(H):
    for (l, r) in profile(y):
        span = r - l + 1
        for dx in range(l, r + 1):
            x = CX + dx
            el, er = dx - l, r - dx  # distance from span edges
            platform = 108 <= y < 113 or 146 <= y < 154 or 30 <= y < 37
            # see-through lattice inside wide spans
            if not platform and span >= 7 and el >= 2 and er >= 2:
                k = 5 if span < 20 else 6
                if (dx + y) % k and (dx - y) % k and y % 12:
                    continue
            rel = (dx - l) / max(1, span - 1)
            c = DARK if rel < 0.35 else MID if rel < 0.75 else LIGHT
            if dx > 0 and er == 0:
                c = RIM
            elif dx < 0 and el == 0:
                c = DARK
            if not platform and span >= 7 and 2 <= el and 2 <= er:
                c = DARK if dx < 0 else MID
            put(x, y, c)

# platforms: railings, arcade, lamps
for x in range(CX - 13, CX + 14):
    put(x, 108, RIM if x > CX else LIGHT)
    if x % 3 == 0:
        put(x, 110, GLOW)
for x in range(CX - 30, CX + 31):
    put(x, 146, RIM if x > CX else LIGHT)
    if x % 3 == 0:
        put(x, 148, GLOW)
    if x % 4 in (1, 2) and abs(x - CX) < 29:  # arcade openings
        for y in (151, 152):
            put(x, y, sky_at(x, y))
for x in range(CX - 3, CX + 4):
    put(x, 30, RIM if x > CX else LIGHT)
    if x % 2 == 0:
        put(x, 33, GLOW)
# beacon at the top
put(CX, 11, (255, 255, 220))
for dx, dy in [(-1, 11), (1, 11), (0, 10)]:
    put(CX + dx, dy, (255, 200, 120))

# ---------------------------------------------------------------- foreground
# trees on both sides of the tower base
def tree(tx, ty, r, rnd):
    for y in range(ty - r, ty + r + 1):
        for x in range(tx - r - 1, tx + r + 2):
            d = ((x - tx) / (r + 1)) ** 2 + ((y - ty) / r) ** 2
            if d > 1 + rnd.random() * 0.15:
                continue
            if d > 0.6 and (x - tx) > 0 and (y - ty) < 0:
                c = (112, 104, 56)  # warm rim from the sun
            elif (x - tx) + (y - ty) * 0.5 < -r * 0.3:
                c = (24, 40, 48)
            else:
                c = (40, 64, 56) if (x + y) % 5 else (56, 84, 60)
            put(x, y, c)


rnd = random.Random(42)
for tx in list(range(-4, 82, 9)) + list(range(178, 264, 9)):
    tree(tx + rnd.randint(-2, 2), HORIZON - 2 + rnd.randint(-3, 2), rnd.randint(5, 8), rnd)
for tx in range(84, 176, 7):
    tree(tx, HORIZON + 2, rnd.randint(3, 4), rnd)

# stone embankment
for y in range(HORIZON + 3, HORIZON + 9):
    for x in range(W):
        if y == HORIZON + 3:
            c = (168, 112, 96)
        elif (x + (y // 3) * 4) % 8 == 0 or y % 3 == 0:
            c = (56, 32, 56)
        else:
            c = (96, 60, 80)
        put(x, y, c)
for x in range(4, W, 22):  # lamp posts
    for y in range(HORIZON - 4, HORIZON + 3):
        put(x, y, (32, 20, 36))
    put(x, HORIZON - 5, GLOW)
    put(x - 1, HORIZON - 5, (248, 176, 88))
    put(x + 1, HORIZON - 5, (248, 176, 88))

# the Seine: rippling reflection of the scene above the bank
WATER_TOP = HORIZON + 9
for y in range(WATER_TOP, H):
    depth = y - WATER_TOP
    src_y = HORIZON + 2 - depth * 4
    wobble = (1, 0, -1, 0)[(y // 2) % 4]
    for x in range(W):
        sx = min(W - 1, max(0, x + wobble))
        c = lerp(img[max(0, src_y)][sx], (32, 20, 72), 0.4 + depth * 0.015)
        if (x // 5 + y * 7) % 17 == 0:  # ripple highlights
            c = lerp(c, (248, 184, 136), 0.45)
        img[y][x] = c
# sun glitter path on the water: short horizontal dashes
rnd = random.Random(5)
for y in range(WATER_TOP + 1, H, 2):
    spread = 10 + (y - WATER_TOP)
    for _ in range(3):
        x0 = SUN_X + rnd.randint(-spread, spread)
        c = rnd.choice([(255, 236, 168), (252, 184, 96)])
        for x in range(x0, x0 + rnd.randint(2, 6)):
            put(x, y, c)

# ---------------------------------------------------------------- 16-bit quantize
def rgb555(c):
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c)


with open(sys.argv[1] if len(sys.argv) > 1 else "eiffel.ppm", "wb") as f:
    f.write(b"P6 %d %d 255\n" % (W, H))
    f.write(bytes(v for row in img for c in row for v in rgb555(c)))
