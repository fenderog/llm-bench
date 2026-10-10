#!/usr/bin/env python3
"""Draw an original RGB565 / 16-bit-era pixel illustration, then encode a JPG.

No external Python dependencies. All artwork is drawn at 384 x 480, quantized to
RGB565, and enlarged 4x with nearest-neighbor sampling. Requires ffmpeg.
"""
from pathlib import Path
import math
import random
import subprocess

W, H = 384, 480
random.seed(1889)
pixels = [(0, 0, 0)] * (W * H)


def rgb(value):
    if isinstance(value, str):
        value = value.lstrip('#')
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    return value


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(round(x * (1 - t) + y * t) for x, y in zip(a, b))


def pixel(x, y, color):
    x, y = int(x), int(y)
    if 0 <= x < W and 0 <= y < H:
        pixels[y * W + x] = rgb(color)


def get(x, y):
    if 0 <= int(x) < W and 0 <= int(y) < H:
        return pixels[int(y) * W + int(x)]
    return (0, 0, 0)


def rect(x0, y0, x1, y1, color):
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(W - 1, int(x1)), min(H - 1, int(y1))
    c = rgb(color)
    if x1 >= x0:
        for y in range(y0, y1 + 1):
            pixels[y * W + x0:y * W + x1 + 1] = [c] * (x1 - x0 + 1)


def line(x0, y0, x1, y1, color, width=1):
    x0, y0, x1, y1 = map(lambda v: int(round(v)), (x0, y0, x1, y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        if width == 1:
            pixel(x0, y0, color)
        else:
            lo = (width - 1) // 2
            hi = width // 2
            rect(x0 - lo, y0 - lo, x0 + hi, y0 + hi, color)
        if x0 == x1 and y0 == y1:
            break
        twice = 2 * err
        if twice >= dy:
            err += dy
            x0 += sx
        if twice <= dx:
            err += dx
            y0 += sy


def poly(points, color):
    # Scan conversion, deliberately without antialiasing.
    ymin = max(0, math.ceil(min(p[1] for p in points)))
    ymax = min(H - 1, math.floor(max(p[1] for p in points)))
    for y in range(ymin, ymax + 1):
        xs = []
        for i, (x0, y0) in enumerate(points):
            x1, y1 = points[(i + 1) % len(points)]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            rect(math.ceil(xs[i]), y, math.floor(xs[i + 1]), y, color)


def path(points, color, width=1):
    for p, q in zip(points, points[1:]):
        line(*p, *q, color, width)


def ellipse(cx, cy, rx, ry, color):
    for y in range(max(0, int(cy - ry)), min(H - 1, int(cy + ry)) + 1):
        t = (y - cy) / ry
        half = int(rx * math.sqrt(max(0, 1 - t * t)))
        rect(cx - half, y, cx + half, y, color)


# --- A banded, dithered twilight sky -----------------------------------------
sky_stops = [
    (0, '#24263e'), (55, '#39334f'), (110, '#5d4968'),
    (166, '#946079'), (224, '#c98289'), (282, '#eaa08a'),
    (339, '#f2bb94'), (376, '#c59191'), (480, '#413d5a'),
]
sky_bands = []
for y in range(0, H + 8, 8):
    ya, ca = sky_stops[0]
    for yb, cb in sky_stops[1:]:
        if y <= yb:
            color = mix(ca, cb, (y - ya) / (yb - ya))
            break
        ya, ca = yb, cb
    else:
        color = rgb(sky_stops[-1][1])
    sky_bands.append(color)
for y in range(H):
    band = y // 8
    rect(0, y, W - 1, y, sky_bands[band])
    # Two-pixel ordered transition, keeping distinct pixel-art color steps.
    if y % 8 in (0, 1) and band:
        for x in range((y % 2) * 2, W, 4):
            if (x // 4 + y) % 2 == 0 or y % 8 == 0:
                pixel(x, y, sky_bands[band - 1])

# Quiet, individually placed stars: no diffuse digital gradients.
stars = [(25, 34), (53, 67), (87, 24), (124, 51), (154, 17),
         (174, 92), (230, 29), (262, 57), (289, 22), (316, 82),
         (356, 41), (363, 112), (275, 100), (43, 144), (93, 157),
         (20, 94), (331, 132), (239, 120)]
for i, (x, y) in enumerate(stars):
    pixel(x, y, '#c3adba' if i % 3 else '#eac7b5')
    if i % 5 == 0:
        pixel(x + 1, y, '#9a87a6')
for x, y in [(307, 47), (72, 96), (250, 156)]:
    line(x - 2, y, x + 2, y, '#b698ae')
    line(x, y - 2, x, y + 2, '#b698ae')
    pixel(x, y, '#fff0cb')

# The setting sun, with pixel contour and a very restrained ordered halo.
sunx, suny, sunr = 130, 234, 54
for y in range(suny - sunr - 10, suny + sunr + 11):
    for x in range(sunx - sunr - 10, sunx + sunr + 11):
        d = math.hypot(x - sunx, y - suny)
        if sunr < d <= sunr + 8 and (x + 2 * y) % 5 == 0:
            pixel(x, y, mix(get(x, y), '#ffd4a2', 0.13 * (1 - (d - sunr) / 9)))
ellipse(sunx, suny, sunr, sunr, '#ffd29a')
for y in range(suny - sunr, suny + sunr + 1):
    half = int(math.sqrt(max(0, sunr * sunr - (y - suny) ** 2)))
    c = ['#ffe0ac', '#ffdda5', '#ffd59e', '#ffce96', '#fac38f'][min(4, (y - (suny - sunr)) // 23)]
    rect(sunx - half, y, sunx + half, y, c)
# Bands of thin atmospheric cloud cut across the low solar disc.
for x0, y0, x1, y1, c in [
    (77, 250, 119, 251, '#e7a18d'), (139, 250, 181, 251, '#efad90'),
    (91, 268, 174, 270, '#e7a28b'), (105, 278, 175, 280, '#dfa18f'),
]:
    rect(x0, y0, x1, y1, c)

# Long, stepped clouds with faceted undersides.
def cloud(points, shadow, highlight_segments, highlight):
    poly(points, shadow)
    for x0, y, x1, thick in highlight_segments:
        rect(x0, y, x1, y + thick - 1, highlight)

cloud([(-12, 97), (9, 97), (9, 93), (31, 93), (31, 90), (54, 90),
       (54, 93), (75, 93), (75, 99), (101, 99), (101, 103), (117, 103),
       (117, 106), (139, 106), (139, 110), (99, 110), (99, 114),
       (50, 114), (50, 110), (13, 110), (13, 106), (-12, 106)],
      '#72536f', [(3, 108, 39, 2), (39, 111, 92, 2), (101, 107, 135, 1)], '#b8788b')
rect(17, 100, 65, 103, '#805a75')
rect(34, 105, 95, 107, '#93627d')
rect(57, 116, 83, 116, '#a66b85')
rect(116, 116, 154, 117, '#8a5c78')

cloud([(245, 133), (263, 133), (263, 129), (286, 129), (286, 125),
       (305, 125), (305, 128), (325, 128), (325, 134), (350, 134),
       (350, 138), (387, 138), (387, 149), (357, 149), (357, 153),
       (308, 153), (308, 150), (276, 150), (276, 146), (235, 146),
       (235, 141), (245, 141)], '#9d6680',
      [(250, 144, 279, 2), (282, 148, 318, 2), (320, 151, 355, 2),
       (363, 146, 384, 2)], '#d28a95')
rect(276, 135, 324, 137, '#a96e86')
rect(299, 140, 362, 143, '#b5788d')
rect(285, 157, 338, 158, '#c78291')
rect(352, 158, 374, 159, '#ba778b')

cloud([(-8, 186), (7, 186), (7, 183), (29, 183), (29, 181), (56, 181),
       (56, 184), (74, 184), (74, 188), (98, 188), (98, 192),
       (65, 192), (65, 195), (19, 195), (19, 192), (-8, 192)], '#c07d88',
      [(2, 191, 22, 2), (28, 194, 61, 2), (77, 190, 97, 1)], '#e6a08f')
rect(12, 202, 48, 203, '#d28d8d')
rect(67, 201, 91, 201, '#d78e8b')

cloud([(249, 250), (279, 250), (279, 247), (306, 247), (306, 243),
       (334, 243), (334, 247), (349, 247), (349, 250), (390, 250),
       (390, 259), (344, 259), (344, 262), (311, 262), (311, 259),
       (279, 259), (279, 256), (249, 256)], '#d78e8b',
      [(267, 255, 302, 2), (310, 259, 340, 2), (352, 256, 382, 2)], '#f3b296')
rect(241, 268, 280, 269, '#e3a08f')
rect(301, 274, 368, 275, '#edaa91')
rect(1, 275, 59, 276, '#d9978c')
rect(16, 281, 74, 282, '#e1a18e')

# Two little groups of birds, hand-placed and deliberately small.
for x, y, s in [(56, 230, 3), (69, 222, 2), (77, 232, 2),
                (287, 208, 3), (301, 201, 2), (314, 211, 2)]:
    path([(x - s, y - 1), (x - 1, y), (x, y + 1),
          (x + 1, y), (x + s, y - 1)], '#705b75')

# --- Paris recedes into the warm haze --------------------------------------
poly([(0, 326), (0, 316), (16, 316), (16, 311), (38, 309), (56, 302),
      (77, 306), (94, 316), (118, 316), (133, 321), (177, 320),
      (193, 314), (218, 316), (243, 312), (263, 317), (281, 313),
      (302, 310), (324, 313), (347, 319), (384, 315), (384, 353),
      (0, 353)], '#b38c91')
# A distant domed church and its two quiet roof towers.
rect(40, 298, 64, 321, '#b88e91')
ellipse(52, 300, 9, 9, '#b88e91')
rect(50, 287, 54, 294, '#b88e91')
line(52, 282, 52, 288, '#b88e91')
line(50, 285, 54, 285, '#b88e91')
rect(33, 302, 38, 322, '#b88e91')
rect(67, 302, 72, 322, '#b88e91')
poly([(32, 302), (36, 294), (40, 302)], '#b88e91')
poly([(65, 302), (69, 294), (73, 302)], '#b88e91')
# Small distant houses behind the tower, less contrast than the near streets.
for x in range(-4, W, 11):
    top = random.randrange(322, 337)
    col = random.choice(['#b0878a', '#ae858c', '#a78289', '#bb9190'])
    rect(x, top, x + random.randrange(8, 12), 358, col)
    rect(x - 1, top, x + 10, top + 1, '#967b87')
    if x % 3 == 0:
        rect(x + 5, top - 5, x + 6, top, '#aa828b')
    for yy in range(top + 5, 353, 7):
        for xx in range(x + 2, x + 10, 4):
            rect(xx, yy, xx + 1, yy + 2, '#947e88')


def building(x, y, width, height, facade, lit, roof, floors=4):
    base = y + height
    # Deep side wall and sunset-facing front.
    rect(x, y, x + width - 1, base, facade)
    rect(x + width - 5, y + 1, x + width - 1, base, mix(facade, '#483b53', 0.32))
    rect(x + 1, y + 1, x + 2, base, lit)
    # Characteristic zinc mansard roof, dormer windows and chimney pots.
    poly([(x - 2, y), (x + 3, y - 10), (x + width - 8, y - 10),
          (x + width + 1, y), (x + width + 1, y + 3), (x - 2, y + 3)], roof)
    line(x + 3, y - 10, x + width - 8, y - 10, '#b18a90')
    line(x - 2, y + 2, x + width + 1, y + 2, '#dfac96')
    line(x - 2, y + 4, x + width, y + 4, '#745667')
    for dx in range(6, width - 6, 10):
        rect(x + dx, y - 6, x + dx + 4, y - 1, '#ba9290')
        poly([(x + dx - 1, y - 6), (x + dx + 2, y - 9),
              (x + dx + 5, y - 6)], '#4b455d')
        rect(x + dx + 1, y - 5, x + dx + 2, y - 2, '#54435b')
        pixel(x + dx + 1, y - 5, '#d6ae99')
    for dx in [5, width - 10]:
        rect(x + dx, y - 15, x + dx + 2, y - 10, '#6f5367')
        rect(x + dx - 1, y - 16, x + dx + 3, y - 15, '#a17881')
    step = max(8, (height - 8) // floors)
    for floor, yy in enumerate(range(y + 8, base - 3, step)):
        line(x + 3, yy + 5, x + width - 5, yy + 5, mix(lit, facade, .5))
        for xx in range(x + 5, x + width - 6, 7):
            win = '#ffd096' if random.random() < .22 else '#574458'
            rect(xx, yy, xx + 2, yy + 4, '#8a6573')
            rect(xx, yy, xx + 1, yy + 3, win)
            pixel(xx, yy, '#e0ad94' if win == '#ffd096' else '#756479')
            if floor in (0, 2):
                line(xx - 1, yy + 4, xx + 3, yy + 4, '#4f4057')
                pixel(xx - 1, yy + 3, '#5e455c')
                pixel(xx + 3, yy + 3, '#5e455c')
    rect(x - 1, base - 2, x + width, base, '#5f4a5c')
    # Dark ground-floor arcade.
    for xx in range(x + 5, x + width - 5, 9):
        rect(xx, base - 6, xx + 3, base - 3, '#463d52')

building(-11, 319, 34, 42, '#9e7580', '#c18e87', '#51465f')
building(25, 311, 34, 50, '#ba8a88', '#dfab97', '#54485f')
building(61, 325, 30, 36, '#ae7e7c', '#d7a18b', '#615063', 3)
building(94, 333, 30, 28, '#a98081', '#c79788', '#6d596c', 2)
building(275, 324, 29, 39, '#b17f7d', '#d5a28e', '#675169', 3)
building(307, 310, 37, 53, '#bc8886', '#e1a893', '#52455c', 4)
building(347, 322, 39, 41, '#a7797d', '#ca9387', '#51445b', 3)

# Far bank: a line of trees, the gardens, and a warm stone quay.
rect(0, 357, W - 1, 372, '#655463')
for x in range(-6, 391, 9):
    yy = random.randrange(350, 359)
    c = random.choice(['#77666c', '#7d696e', '#8c7475'])
    poly([(x - 5, 358), (x - 5, yy + 2), (x - 2, yy + 2),
          (x - 2, yy - 1), (x + 3, yy - 1), (x + 3, yy + 1),
          (x + 6, yy + 1), (x + 6, 363), (x - 5, 363)], c)
rect(0, 365, W - 1, 367, '#8f7477')
rect(0, 368, W - 1, 369, '#d6a48e')
rect(0, 370, W - 1, 373, '#67505f')
for x in range(4, W, 13):
    line(x, 366, x, 369, '#a4817f')

# --- The Eiffel Tower: open ironwork, not a solid silhouette ----------------
C = 198
INK = '#513749'
DEEP = '#67404b'
IRON = '#94534d'
COPPER = '#c07b58'
GOLD = '#edb572'
LIGHT = '#ffe0a0'

# Widths at structural levels. This nonlinear taper gives the real landmark
# its narrow upper shaft and sweeping, out-turned lower legs.
upper = [(92, 4), (106, 4), (126, 5), (148, 6), (171, 8),
         (195, 11), (219, 15), (244, 21), (253, 24)]

def half_at(y, levels=upper):
    for (ya, wa), (yb, wb) in zip(levels, levels[1:]):
        if ya <= y <= yb:
            return wa + (wb - wa) * (y - ya) / (yb - ya)
    return levels[0][1] if y < levels[0][0] else levels[-1][1]

# Thin ironwork behind the front plane reads as dimensional, copper-lit steel.
back = [(C - w, y) for y, w in upper] + [(C + w, y) for y, w in reversed(upper)]
# Only a faint tint in the upper lattice; the sunset remains visible through it.
for y in range(96, 254):
    hw = int(half_at(y))
    for x in range(C - hw + 2, C + hw - 1):
        pixel(x, y, mix(get(x, y), '#643f55', .13))

# Repeating crossed trusses in the tapering shaft.
levels = [94, 108, 126, 148, 171, 195, 219, 244, 253]
for j, (ya, yb) in enumerate(zip(levels, levels[1:])):
    wa, wb = half_at(ya), half_at(yb)
    line(C - wa + 1, ya, C + wb - 2, yb, INK, 2)
    line(C + wa - 1, ya, C - wb + 2, yb, INK, 2)
    line(C - wa + 1, ya, C + wb - 2, yb, COPPER)
    line(C + wa - 1, ya, C - wb + 2, yb, GOLD)
    # A narrow right-hand face and smaller nested diagonals.
    if j >= 3:
        line(C + wa * .36, ya, C + wb * .4, yb, DEEP, 2)
        line(C + wa * .35, ya, C + wb - 1, yb, COPPER)
        line(C + wa - 1, ya, C + wb * .4, yb, IRON)
    line(C - wb, yb, C + wb, yb, INK, 2)
    line(C - wb, yb - 1, C + wb, yb - 1, COPPER)
    if j >= 2:
        ym = (ya + yb) // 2
        wm = half_at(ym)
        line(C - wm, ym, C + wm, ym, '#a76452')
        # Little fastener highlights at the center of each X.
        pixel(C, ym, LIGHT)
# Four continuous upper posts, edged on their sunward side.
for sign in [-1, 1]:
    p = [(C + sign * w, y) for y, w in upper]
    path(p, INK, 4)
    path([(x - 1, y) for x, y in p], IRON, 2)
    path([(x - 2 if sign < 0 else x - 1, y) for x, y in p], GOLD, 1)
path([(C, 97), (C, 150), (C + 1, 195), (C + 3, 251)], COPPER, 1)

# Observation crown and antenna. The miniature red beacon is one logical pixel.
rect(C - 3, 77, C + 3, 93, INK)
rect(C - 2, 77, C, 91, COPPER)
rect(C - 1, 67, C + 1, 78, INK)
line(C - 1, 67, C - 1, 80, GOLD)
line(C, 47, C, 67, INK)
line(C - 1, 51, C - 1, 66, '#dfad82')
rect(C - 2, 65, C + 2, 67, COPPER)
pixel(C, 45, '#ffcc9c')
pixel(C, 46, '#de7777')
rect(C - 6, 87, C + 6, 91, INK)
rect(C - 6, 86, C + 6, 87, GOLD)
rect(C - 4, 82, C + 4, 84, COPPER)
line(C - 4, 81, C + 4, 81, LIGHT)
for x in range(C - 4, C + 5, 3):
    rect(x, 88, x, 90, '#ffce87')
rect(C - 5, 92, C + 5, 93, IRON)

# The flared middle section between the second and first floors.
mid = [(260, 23), (274, 27), (290, 34), (307, 44)]
# Thin rear-plane wash makes the ironwork distinct from the distant city.
for y in range(260, 308):
    hw = int(half_at(y, mid))
    for x in range(C - hw, C + hw + 1):
        pixel(x, y, mix(get(x, y), '#774749', .12))
# Left/right longitudinal posts with a central open, crossed face.
for sign in [-1, 1]:
    outer_points = [(C + sign * w, y) for y, w in mid]
    inner_points = [(C + sign * w, y) for y, w in [(260, 9), (274, 12), (290, 18), (307, 26)]]
    path(outer_points, INK, 5)
    path([(x - 1, y) for x, y in outer_points], IRON, 3)
    path([(x - 2, y) for x, y in outer_points], GOLD)
    path(inner_points, DEEP, 3)
    path([(x - 1, y) for x, y in inner_points], COPPER)
    for (ya, wa), (yb, wb), ia, ib in zip(mid, mid[1:], [9, 12, 18], [12, 18, 26]):
        line(C + sign * wa, ya, C + sign * ib, yb, INK, 2)
        line(C + sign * ia, ya, C + sign * wb, yb, INK, 2)
        line(C + sign * wa - 1, ya, C + sign * ib - 1, yb, GOLD)
        line(C + sign * ia - 1, ya, C + sign * wb - 1, yb, COPPER)
        line(C + sign * wb, yb, C + sign * ib, yb, COPPER)
# Cross braces running across the open central structure.
for ya, yb, wa, wb in [(261, 283, 9, 15), (283, 306, 15, 26)]:
    line(C - wa, ya, C + wb, yb, INK, 3)
    line(C + wa, ya, C - wb, yb, INK, 3)
    line(C - wa - 1, ya, C + wb - 1, yb, COPPER)
    line(C + wa - 1, ya, C - wb - 1, yb, GOLD)
line(C - 31, 283, C + 31, 283, DEEP, 2)
line(C - 31, 282, C + 31, 282, COPPER)

# Four sweeping legs and the unmistakable great parabolic arch.
arch_top, arch_base, arch_width = 322, 366, 51

def arch_inner(y):
    return arch_width * math.sqrt(max(0, (y - arch_top) / (arch_base - arch_top)))


def leg_outer(y):
    return 45 + (y - 313) * 0.48

# A little rear ironwork is offset within each leg, behind the outer arches.
for side in [-1, 1]:
    poly([(C + side * 39, 312), (C + side * 59, 366),
          (C + side * 68, 366), (C + side * 44, 312)], DEEP)
    line(C + side * 40, 315, C + side * 60, 365, COPPER)
# Intricate open crossed bays in the curved leg panels.
leg_levels = [316, 323, 332, 343, 355, 366]
for side in [-1, 1]:
    for ya, yb in zip(leg_levels, leg_levels[1:]):
        oa, ob = leg_outer(ya), leg_outer(yb)
        ia, ib = arch_inner(ya), arch_inner(yb)
        # Above the arch crown, the two sides meet at the center.
        for q in range(2):
            fa, fb = q / 2, (q + 1) / 2
            xa0, xa1 = C + side * (ia + (oa - ia) * fa), C + side * (ia + (oa - ia) * fb)
            xb0, xb1 = C + side * (ib + (ob - ib) * fa), C + side * (ib + (ob - ib) * fb)
            line(xa0, ya, xb1, yb, INK, 2)
            line(xa1, ya, xb0, yb, INK, 2)
            line(xa0 - 1, ya, xb1 - 1, yb, COPPER)
            line(xa1 - 1, ya, xb0 - 1, yb, GOLD)
        line(C + side * ia, ya, C + side * oa, ya, DEEP, 2)
        line(C + side * ia, ya - 1, C + side * oa, ya - 1, COPPER)
    outer_points = [(C + side * leg_outer(y), y) for y in range(313, 367)]
    path(outer_points, INK, 5)
    path([(x - 1, y) for x, y in outer_points], IRON, 3)
    path([(x - 2, y) for x, y in outer_points], GOLD)
# The curved arch ring is a strong, continuous motif in front of the trusses.
arch_points = [(C + x, arch_top + (x / arch_width) ** 2 * (arch_base - arch_top))
               for x in range(-arch_width, arch_width + 1)]
path(arch_points, INK, 5)
path([(x, y - 1) for x, y in arch_points], IRON, 3)
path([(x, y - 2) for x, y in arch_points], GOLD)
# Riveted semicircular flange catches a few flecks of light.
for x in range(-48, 49, 6):
    y = arch_top + (x / arch_width) ** 2 * (arch_base - arch_top)
    pixel(C + x, y - 1, LIGHT)

# Bold horizontal viewing decks, with railings and luminous little windows.
def deck(y, halfwidth, height):
    rect(C - halfwidth, y, C + halfwidth, y + height, INK)
    rect(C - halfwidth - 1, y, C + halfwidth + 1, y + 1, GOLD)
    line(C - halfwidth + 2, y - 3, C + halfwidth - 2, y - 3, COPPER)
    for xx in range(C - halfwidth + 2, C + halfwidth, 4):
        line(xx, y - 3, xx, y - 1, DEEP)
        pixel(xx - 1, y - 2, GOLD)
    rect(C - halfwidth + 2, y + 2, C + halfwidth - 2, y + height - 2, COPPER)
    for xx in range(C - halfwidth + 3, C + halfwidth - 1, 4):
        rect(xx, y + 2, xx + 1, y + height - 2, '#ffcc88')
        pixel(xx + 2, y + height - 2, INK)
    line(C - halfwidth - 1, y + height, C + halfwidth + 1, y + height, DEEP)
    line(C - halfwidth + 3, y + height + 1, C + halfwidth - 3, y + height + 1, '#9e5a4e')

deck(253, 29, 6)
deck(307, 50, 7)
# Larger floor supports and stone shoes anchor the tower.
for side in [-1, 1]:
    x = C + side * 66
    rect(x - 10, 365, x + 9, 367, INK)
    rect(x - 9, 364, x + 8, 365, COPPER)
    rect(x - 11, 368, x + 10, 370, '#715565')
    line(x - 11, 367, x + 10, 367, '#d7a380')
# Warm points of light, kept smaller than the structural members.
for x, y in [(174, 250), (221, 250), (150, 305), (245, 305),
             (136, 362), (260, 362), (188, 195), (207, 195)]:
    pixel(x, y, LIGHT)

# --- The Seine: layered reflections under the Pont d'Iena ------------------
water_colors = ['#9a7284', '#896c82', '#77637e', '#665b77', '#58516d',
                '#4b4964', '#41455f', '#39435b', '#344158']
for y in range(382, H):
    c = water_colors[min(8, (y - 382) // 11)]
    rect(0, y, W - 1, y, c)
    if (y - 382) % 11 < 2 and y > 393:
        for x in range(y % 4, W, 4):
            pixel(x, y, water_colors[min(8, (y - 382) // 11) - 1])
# Small, broken horizontal reflections are scaled toward the viewer.
for _ in range(420):
    y = random.randrange(395, H)
    x = random.randrange(0, W)
    length = random.randrange(2, 9) + (y - 395) // 25
    c = random.choice(['#8e798d', '#ab8391', '#726c88', '#ba8e98', '#56657c'])
    c = mix(get(x, y), c, random.choice([.3, .5, .65]))
    rect(x, y, x + length, y, c)
# The warm sun is reflected in staggered, unsmoothed bands.
for i, y in enumerate(range(399, 478, 3)):
    spread = 22 + (y - 399) * .43
    center = 130 - (y - 399) * .13
    for j in range(random.randrange(2, 5)):
        x = int(center + random.uniform(-spread, spread))
        length = random.randrange(3, 16)
        c = random.choice(['#dcaa95', '#c9918a', '#efb993', '#a87b89'])
        if y > 449:
            c = mix(c, '#564e69', .25)
        rect(x, y, x + length, y, c)
# Fragmented vertical gold reflection of the tower.
for y in range(399, 459, 4):
    x = C + random.randrange(-11, 11)
    rect(x, y, x + random.randrange(2, 7), y, random.choice(['#dca27f', '#af7e79', '#d4a18b']))

# The bridge's softly rose-colored masonry and four segmented arch openings.
bridge_back = pixels[:]
rect(0, 375, W - 1, 397, '#765566')
rect(0, 376, W - 1, 380, '#b28181')
rect(0, 381, W - 1, 386, '#a57577')
rect(0, 387, W - 1, 397, '#906772')
# Segmental arches, with the river (not flat black) visible through them.
for cx in [48, 144, 240, 336]:
    rx = 37
    for xx in range(cx - rx, cx + rx + 1):
        cap = 395 - 12 * math.sqrt(max(0, 1 - ((xx - cx) / rx) ** 2))
        for yy in range(math.ceil(cap), 399):
            if 0 <= xx < W:
                pixels[yy * W + xx] = bridge_back[yy * W + xx]
    curve = [(cx + xx, 395 - 12 * math.sqrt(max(0, 1 - (xx / rx) ** 2))) for xx in range(-rx, rx + 1)]
    path(curve, '#57475e', 2)
    path([(x, y - 2) for x, y in curve], '#d09a8d', 2)
    for theta in [0.17, .45, .75, 1.03, 1.31, 1.57, 1.83, 2.11, 2.39, 2.69, 2.98]:
        x = cx + math.cos(theta) * 39
        y = 395 - math.sin(theta) * 14
        pixel(x, y, '#8d6570')
    rect(cx - 2, 379, cx + 2, 383, '#e0ad96')
# Stone pier seams and cornice.
for xx in [0, 95, 191, 287, 383]:
    line(xx, 382, xx, 397, '#6c5265')
    line(xx - 5, 392, xx + 4, 392, '#ae7f7c')
    rect(xx - 7, 397, xx + 6, 400, '#635065')
rect(0, 375, W - 1, 376, '#e2ac90')
rect(0, 377, W - 1, 378, '#8e6871')
# Fine pedestrian balustrade on the top of the bridge.
line(0, 371, W - 1, 371, '#624a5e')
line(0, 370, W - 1, 370, '#dca58c')
for xx in range(2, W, 5):
    line(xx, 372, xx, 374, '#5c485b')
for xx in range(0, W, 32):
    rect(xx, 369, xx + 2, 374, '#a47a7b')
    rect(xx - 1, 368, xx + 3, 369, '#e9b792')

# Tiny evening walkers lend scale without distracting from the landmark.
for xx, yy in [(92, 371), (101, 371), (284, 371)]:
    pixel(xx, yy - 6, '#d6aa91')
    rect(xx - 1, yy - 4, xx + 1, yy - 1, '#44394e')
    pixel(xx - 1, yy, '#41384c')
    pixel(xx + 1, yy, '#41384c')

# --- Framing trees: clustered pixels, no soft brushwork ---------------------
def tree(cx, cy, rx, ry, seed, colors):
    r = random.Random(seed)
    # A stepped mass of overlapping small leaf clusters.
    for i in range(85):
        a = r.uniform(0, math.tau)
        d = math.sqrt(r.random())
        x = int(cx + math.cos(a) * rx * d)
        y = int(cy + math.sin(a) * ry * d)
        rw, rh = r.randrange(4, 10), r.randrange(3, 8)
        c = colors[0] if i < 30 else r.choice(colors[:3])
        poly([(x - rw, y - rh + 2), (x - rw + 3, y - rh + 2),
              (x - rw + 3, y - rh), (x + rw - 3, y - rh),
              (x + rw - 3, y - rh + 2), (x + rw, y - rh + 2),
              (x + rw, y + rh - 2), (x + rw - 3, y + rh - 2),
              (x + rw - 3, y + rh), (x - rw + 2, y + rh),
              (x - rw + 2, y + rh - 2), (x - rw, y + rh - 2)], c)
    # Groups of small lit pixels, biased toward the sunset-facing left edge.
    for _ in range(115):
        x = r.randrange(int(cx - rx), int(cx + rx + 1))
        y = r.randrange(int(cy - ry), int(cy + ry + 1))
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < .94:
            if get(x, y) in [rgb(c) for c in colors[:3]]:
                c = r.choice(colors[2:])
                rect(x, y, x + r.randrange(1, 4), y + r.randrange(0, 2), c)

# Left trees on the far side of the water.
path([(10, 390), (11, 352), (3, 331)], '#3b354b', 5)
path([(12, 364), (25, 346), (30, 332)], '#443a50', 3)
tree(4, 340, 26, 31, 22, ['#3d3c50', '#494355', '#5e4d5b', '#856267', '#ab7a70'])
tree(22, 357, 21, 22, 35, ['#414052', '#514655', '#6b5360', '#8c6869'])
# The right edge is closer, cooler and darker.
path([(374, 407), (369, 351), (377, 308)], '#2a3046', 7)
path([(371, 370), (351, 339), (352, 321)], '#333448', 4)
tree(378, 328, 33, 44, 88, ['#30364b', '#3b3c50', '#4b4455', '#68515d', '#89666b'])
tree(377, 367, 31, 31, 55, ['#30364b', '#3b3c50', '#4d4758', '#6b5361'])

# --- A foreground stone promenade, with a lantern and an empty bench -------
poly([(312, 397), (384, 401), (384, 480), (213, 480)], '#544a61')
poly([(319, 401), (384, 407), (384, 480), (225, 480)], '#6d596a')
poly([(313, 397), (320, 401), (225, 480), (213, 480)], '#b48c86')
line(312, 397, 213, 479, '#e2b094', 2)
line(318, 402, 225, 479, '#453d55', 2)
# Perspective paving: less regular and not as contrasty as the tower.
for y in [412, 426, 443, 465]:
    xmin = 319 - (y - 401) * 1.21
    line(xmin, y, 383, y + 6, '#7c6473')
    line(xmin, y + 1, 383, y + 7, '#594c62')
for xb in [251, 278, 314, 359, 410]:
    line(341, 400, xb, 479, '#605165')
for x, y in [(279, 454), (355, 471), (322, 431), (245, 473), (366, 425)]:
    rect(x, y, x + 6, y, '#a78581')
    pixel(x + 8, y + 1, '#896e78')
# Wrought-iron fence along the river edge. Posts increase in size toward us.
posts = [(306, 403, 11), (292, 415, 13), (275, 429, 16), (254, 447, 19), (228, 469, 23)]
for x, y, h in posts:
    rect(x - 1, y - h, x + 1, y, '#343448')
    pixel(x - 1, y - h, '#c49883')
    rect(x - 2, y - h - 2, x + 2, y - h - 1, '#45394d')
    pixel(x, y - h - 3, '#d4a18a')
    rect(x - 2, y, x + 2, y + 1, '#343448')
for a, b in zip(posts, posts[1:]):
    x0, y0, h0 = a
    x1, y1, h1 = b
    line(x0, y0 - h0 + 2, x1, y1 - h1 + 2, '#3b354c', 2)
    line(x0, y0 - h0 + 1, x1, y1 - h1 + 1, '#a47e7d')
    line(x0, y0 - h0 / 2, x1, y1 - h1 / 2, '#3b354c')
    for t in [.25, .5, .75]:
        x, y, h = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, h0 + (h1 - h0) * t
        line(x, y - h + 3, x, y - 2, '#3b354c')

# A well-observed little slatted bench, angled along the walkway.
poly([(283, 447), (312, 450), (323, 448), (295, 445)], '#403849')
for yy in [435, 438, 441]:
    line(289, yy, 320, yy + 3, '#343347', 2)
    line(289, yy - 1, 320, yy + 2, '#b3897a')
    line(290, yy, 319, yy + 3, '#8c666b')
line(290, 432, 287, 451, '#323246', 2)
line(319, 435, 317, 454, '#323246', 2)
for yy in [445, 447]:
    line(284, yy, 314, yy + 3, '#ac7c71', 2)
    line(284, yy - 1, 314, yy + 2, '#d0a087')
line(284, 447, 283, 454, '#2d3044', 2)
line(313, 450, 313, 457, '#2d3044', 2)
path([(282, 444), (282, 441), (286, 440), (289, 442)], '#333246', 2)
path([(314, 447), (314, 444), (318, 443), (321, 445)], '#333246', 2)

# Lamp glow is a hand-dithered aureole, not a blurry filter.
lx, ly = 344, 347
for y in range(ly - 21, ly + 25):
    for x in range(lx - 23, lx + 24):
        d = math.hypot((x - lx) / 1.0, (y - ly) / 1.1)
        if d < 20:
            if (x + y * 2) % (3 if d < 12 else 5) == 0:
                pixel(x, y, mix(get(x, y), '#eeb97c', .2 * (1 - d / 23)))
# The iron standard and flared foot.
rect(lx - 2, 361, lx + 2, 460, '#252c40')
line(lx - 2, 365, lx - 2, 458, '#9c7975')
line(lx + 1, 371, lx + 1, 460, '#3d3a4e')
rect(lx - 3, 453, lx + 3, 460, '#333247')
rect(lx - 5, 460, lx + 5, 463, '#292d41')
rect(lx - 7, 464, lx + 7, 466, '#252a3e')
line(lx - 5, 460, lx + 3, 460, '#76616d')
# Curled support immediately under the lantern.
path([(lx - 1, 375), (lx - 6, 371), (lx - 8, 365), (lx - 7, 362),
      (lx - 4, 362), (lx - 3, 364), (lx - 5, 366)], '#2c3044', 2)
path([(lx + 1, 375), (lx + 6, 371), (lx + 8, 365), (lx + 7, 362),
      (lx + 4, 362), (lx + 3, 364), (lx + 5, 366)], '#2c3044', 2)
rect(lx - 4, 358, lx + 4, 361, '#252c40')
# Tapered glowing glass, dark corner posts, warm left highlights.
poly([(lx - 7, ly - 7), (lx + 7, ly - 7), (lx + 5, ly + 10),
      (lx - 5, ly + 10)], '#272d42')
poly([(lx - 5, ly - 5), (lx + 5, ly - 5), (lx + 3, ly + 8),
      (lx - 3, ly + 8)], '#ffd99a')
rect(lx - 3, ly - 4, lx, ly + 6, '#ffeabb')
line(lx + 1, ly - 5, lx + 1, ly + 8, '#a77d68')
line(lx - 6, ly - 5, lx - 4, ly + 8, '#c89471')
rect(lx - 8, ly - 8, lx + 8, ly - 7, '#252d41')
poly([(lx - 8, ly - 9), (lx - 4, ly - 13), (lx + 4, ly - 13),
      (lx + 8, ly - 9)], '#303146')
line(lx - 6, ly - 10, lx + 4, ly - 10, '#997875')
rect(lx - 2, ly - 16, lx + 2, ly - 13, '#282e42')
pixel(lx, ly - 18, '#e7b78b')

# Dark leaves on the nearest corners make a quiet natural vignette.
tree(-5, 484, 49, 18, 207, ['#252d41', '#2b3347', '#384054', '#4b4a5c'])
tree(382, 487, 34, 22, 302, ['#252d41', '#2c3348', '#3b3f52', '#514859'])
for x, y in [(24, 475), (38, 479), (372, 467), (361, 477)]:
    path([(x, y + 5), (x + 1, y), (x + 4, y - 3)], '#34394c')
    rect(x + 3, y - 3, x + 5, y - 2, '#80636b')

# A one-pixel inner keyline and dark outer edge preserve the postcard finish.
rect(0, 0, W - 1, 2, '#23283d')
rect(0, H - 3, W - 1, H - 1, '#23283d')
rect(0, 0, 2, H - 1, '#23283d')
rect(W - 3, 0, W - 1, H - 1, '#23283d')

# RGB565 uses 5 red bits, 6 green bits, and 5 blue bits: a 16-bit color source.
def to_rgb565(c):
    r, g, b = c
    return (round(round(r * 31 / 255) * 255 / 31),
            round(round(g * 63 / 255) * 255 / 63),
            round(round(b * 31 / 255) * 255 / 31))

root = Path(__file__).resolve().parent
output = root / 'output'
output.mkdir(exist_ok=True)
ppm = root / '_eiffel_pixels.ppm'
try:
    with ppm.open('wb') as f:
        f.write(f'P6\n{W} {H}\n255\n'.encode('ascii'))
        f.write(bytes(channel for c in pixels for channel in to_rgb565(c)))
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-i', str(ppm), '-vf', 'scale=1536:1920:flags=neighbor',
        '-frames:v', '1', '-c:v', 'mjpeg', '-q:v', '1',
        '-pix_fmt', 'yuvj444p', '-update', '1',
        str(output / 'eiffel_twilight.jpg'),
    ], check=True)
finally:
    ppm.unlink(missing_ok=True)
print(f"Created {output / 'eiffel_twilight.jpg'}")
