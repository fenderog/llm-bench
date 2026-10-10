#!/usr/bin/env python3
"""Original, procedurally drawn 16-bit-style pixel art. No external assets.

The artwork is drawn on a 512 x 640 pixel canvas, quantized to RGB565,
then enlarged 3x with nearest-neighbour sampling and saved as a 4:4:4 JPEG.
Run: python3 render_eiffel.py
"""
from pathlib import Path
import math
import random
import subprocess

W, H = 512, 640
rng = random.Random(1889)
canvas = bytearray(W * H * 3)


def rgb(c):
    if isinstance(c, str):
        return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
    return c


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(round(x * (1-t) + y * t) for x, y in zip(a, b))


def pixel(x, y, c):
    x, y = int(x), int(y)
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i:i+3] = bytes(rgb(c))


def get(x, y, source=None):
    source = canvas if source is None else source
    x, y = max(0, min(W-1, int(x))), max(0, min(H-1, int(y)))
    i = (y * W + x) * 3
    return tuple(source[i:i+3])


def rect(x0, y0, x1, y1, c):
    x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
    x0, x1 = max(x0, 0), min(x1, W-1)
    y0, y1 = max(y0, 0), min(y1, H-1)
    if x1 < x0 or y1 < y0:
        return
    strip = bytes(rgb(c)) * (x1-x0+1)
    for y in range(y0, y1+1):
        i = (y*W+x0)*3
        canvas[i:i+len(strip)] = strip


def poly(points, c):
    ymin = max(0, math.ceil(min(p[1] for p in points)))
    ymax = min(H-1, math.floor(max(p[1] for p in points)))
    for y in range(ymin, ymax+1):
        scan = y + .5
        xs = []
        for a, b in zip(points, points[1:]+points[:1]):
            if (a[1] <= scan < b[1]) or (b[1] <= scan < a[1]):
                xs.append(a[0]+(scan-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            rect(math.ceil(xs[i]), y, math.floor(xs[i+1]), y, c)


def line(x0, y0, x1, y1, c, width=1):
    x0, y0, x1, y1 = map(round, (x0, y0, x1, y1))
    dx, sx = abs(x1-x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1-y0), 1 if y0 < y1 else -1
    err = dx + dy
    low, high = (width-1)//2, width//2
    while True:
        rect(x0-low, y0-low, x0+high, y0+high, c)
        if x0 == x1 and y0 == y1:
            break
        e = 2 * err
        if e >= dy:
            err += dy
            x0 += sx
        if e <= dx:
            err += dx
            y0 += sy


def path(points, c, width=1):
    for a, b in zip(points, points[1:]):
        line(*a, *b, c, width)


def ellipse(cx, cy, rx, ry, c):
    for y in range(max(0, int(cy-ry)), min(H-1, int(cy+ry))+1):
        q = 1 - ((y-cy)/ry)**2
        if q >= 0:
            span = int(rx * math.sqrt(q))
            rect(cx-span, y, cx+span, y, c)


# SKY: restrained, ordered dithering between a set of flat colour bands.
sky_stops = [(0, '#65658b'), (90, '#a17c9b'), (182, '#d99ba6'),
             (270, '#f4b49f'), (354, '#ffd09f'), (474, '#e9b499')]
bayer = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
for y in range(475):
    for j in range(len(sky_stops)-1):
        ya, ca = sky_stops[j]
        yb, cb = sky_stops[j+1]
        if ya <= y <= yb:
            t = (y-ya)/(yb-ya)
            steps = 6
            lo = math.floor(t*steps)/steps
            hi = min(1, lo+1/steps)
            frac = (t-lo)*steps
            c0, c1 = mix(ca, cb, lo), mix(ca, cb, hi)
            for x in range(W):
                # Dither is restricted to the transitions, leaving broad clear areas.
                threshold = bayer[y % 4][x % 4]/16
                pixel(x, y, c1 if frac > .30 + threshold*.65 else c0)
            break

# Small glimmers in the cooling sky.
for x, y in [(69, 47), (183, 31), (291, 39), (420, 58), (127, 78), (469, 23)]:
    pixel(x, y, '#e4b7be')
line(359, 37, 359, 41, '#edc0bf')
line(357, 39, 361, 39, '#edc0bf')
pixel(359, 39, '#f7d6ca')

# Setting sun; the stepped edge and narrow missing bands are deliberate pixels.
ellipse(347, 228, 61, 61, '#f4bc9b')
for y in range(169, 288):
    span = int(math.sqrt(max(0, 59**2-(y-228)**2)))
    color = '#ffe0a5' if y < 210 else '#ffe8ad' if y < 247 else '#ffdb98'
    if y not in (264, 265, 276, 280, 281, 286):
        rect(347-span, y, 347+span, y, color)


def cloud(x, y, w, h, shadow, main, light, seed):
    r = random.Random(seed)
    # Wide, hand-stepped ribbons, not blurred ellipses.
    pts = [(x, y+h*.65)]
    steps = 13
    for i in range(steps+1):
        xx = x + i*w/steps
        bump = math.sin(math.pi*i/steps)
        yy = y+h*(.58-bump*.50)+r.choice([-2, 0, 0, 2])
        yy = 2*round(yy/2)
        if i:
            pts.append((xx, pts[-1][1]))
        pts.append((xx, yy))
    pts += [(x+w, y+h*.75), (x+w*.87, y+h*.75),
            (x+w*.87, y+h*.89), (x+w*.69, y+h*.89),
            (x+w*.69, y+h), (x+w*.19, y+h),
            (x+w*.19, y+h*.85), (x, y+h*.85)]
    poly(pts, shadow)
    # Quiet broad light planes and thin luminous undersides.
    rect(x+w*.15, y+h*.40, x+w*.72, y+h*.60, main)
    rect(x+w*.29, y+h*.28, x+w*.59, y+h*.42, main)
    rect(x+w*.07, y+h*.62, x+w*.91, y+h*.69, main)
    rect(x+w*.22, y+h*.83, x+w*.73, y+h*.86, light)
    rect(x+w*.51, y+h*.91, x+w*.83, y+h*.94, light)
    rect(x+w*.02, y+h+5, x+w*.22, y+h+6, main)
    rect(x+w*.59, y+h+8, x+w*.92, y+h+9, shadow)

cloud(-34, 104, 227, 35, '#b188a2', '#c496ad', '#e8acb4', 5)
cloud(361, 87, 182, 31, '#b089a3', '#c493ab', '#e0a4b2', 6)
cloud(-29, 203, 204, 31, '#dba0ab', '#ecafaf', '#ffd0b2', 10)
cloud(103, 166, 108, 16, '#c995a6', '#dda3ad', '#efb6b5', 18)
cloud(385, 303, 166, 19, '#e5a6a2', '#f1b4a6', '#ffd0b0', 20)
# Wisps across the edge of the solar disc.
rect(371, 237, 442, 239, '#f1b5a3')
rect(395, 241, 467, 242, '#efb1a3')
rect(317, 269, 354, 270, '#efb29f')
rect(20, 316, 124, 317, '#fbd0ae')
rect(52, 321, 159, 322, '#f6c3a9')
rect(110, 347, 206, 348, '#ffd5ae')

# A handful of tiny swallows, all intentionally drawn as angular sprites.
for x, y, s in [(87, 267, 3), (104, 259, 2), (119, 269, 2), (404, 172, 2), (415, 167, 2)]:
    path([(x-s*2, y-2), (x-s, y-2), (x, y), (x+s, y-2), (x+s*2, y-2)], '#865f7f')

# HAZY DISTANT PARIS: three layers establish depth without competing with ironwork.
rect(0, 412, 511, 454, '#c094a0')
x = -6
while x < W:
    w = rng.randint(10, 27)
    top = rng.randint(385, 411)
    rect(x, top, x+w, 432, '#c397a2')
    rect(x+2, top-2, x+w-3, top, '#c397a2')
    if rng.random() < .35:
        rect(x+w//2, top-6, x+w//2+2, top-1, '#c397a2')
    x += w+2
# A distant domed roof on the eastern skyline.
rect(415, 383, 441, 420, '#b58b9b')
rect(419, 374, 437, 385, '#bd919b')
poly([(418, 374), (420, 365), (424, 360), (431, 360), (436, 365), (438, 374)], '#c39392')
path([(419, 370), (423, 363), (427, 361), (431, 364), (434, 370)], '#e4b290', 2)
rect(426, 354, 429, 360, '#b38b98')
line(427, 350, 427, 356, '#b38b98')
rect(412, 384, 444, 387, '#ad8595')
for xx in range(418, 440, 5):
    rect(xx, 390, xx+1, 397, '#987d94')

# Closer slate mansard roofs and lit limestone facades.
def building(x, top, w, bottom, light, roof, seed):
    r = random.Random(seed)
    rect(x, top+9, x+w, bottom, light)
    rect(x+w-4, top+11, x+w, bottom, mix(light, '#805c79', .3))
    poly([(x-2, top+10), (x+4, top), (x+w-5, top), (x+w+2, top+10)], roof)
    line(x+5, top, x+w-5, top, '#d3a1a0')
    rect(x-1, top+10, x+w+1, top+11, '#e9b69c')
    for xx in range(x+5, x+w-2, 7):
        if xx+2 < x+w-2:
            rect(xx, top+3, xx+3, top+7, '#c49a9d')
            rect(xx+1, top+4, xx+2, top+6, '#675c7c')
            pixel(xx+1, top+2, '#e0ada0')
    for yy in range(top+15, bottom-2, 9):
        for xx in range(x+4, x+w-4, 6):
            color = '#7e6985' if r.random() < .8 else '#ffd39b'
            rect(xx, yy, xx+2, yy+4, color)
            if r.random() < .7:
                line(xx-1, yy+5, xx+3, yy+5, '#97768a')
        line(x+1, yy+7, x+w-4, yy+7, mix(light, '#936d87', .22))
    for xx in [x+6, x+w-9]:
        rect(xx, top-5, xx+2, top+1, '#947284')
        rect(xx-1, top-6, xx+3, top-5, '#bd8e96')

for args in [(0, 409, 26, 452), (26, 401, 36, 454), (66, 411, 28, 454),
             (94, 418, 31, 454), (124, 417, 28, 455),
             (365, 414, 28, 455), (394, 409, 32, 456),
             (428, 411, 34, 455), (466, 396, 44, 456)]:
    building(*args, '#d3a5a1', '#746480', args[0]+90)
# Behind the open arch, the distant city is small and low-contrast.
for args in [(205, 425, 28, 456), (237, 429, 36, 456), (276, 420, 28, 456)]:
    building(*args, '#d6a8a1', '#9c7b91', args[0])

# Warm ground and the far stone quay.
rect(0, 450, 511, 470, '#b68e97')
rect(0, 453, 511, 457, '#d7a39b')
rect(0, 465, 511, 469, '#806b85')
rect(0, 470, 511, 476, '#d5a69b')
rect(0, 470, 511, 471, '#f2c39f')
rect(0, 477, 511, 480, '#645d7c')
for x in range(0, W, 23):
    line(x, 473, x, 476, '#b18c96')
for x in range(0, W, 8):
    line(x, 463, x, 468, '#6f607d')
line(0, 462, 511, 462, '#79667f')

# Plane trees in cool mulberry and petrol hues, with small blocks of copper light.
def tree(cx, base, size, seed):
    r = random.Random(seed)
    trunk = '#4b4b66'
    rect(cx-2, base-size*.7, cx+2, base, trunk)
    line(cx, base-9, cx-size*.37, base-size*.87, trunk, 2)
    line(cx, base-9, cx+size*.36, base-size*.96, trunk, 2)
    clusters = [(cx, base-size*1.4, size*.56, size*.57),
                (cx-size*.45, base-size, size*.5, size*.47),
                (cx+size*.44, base-size*1.07, size*.48, size*.52),
                (cx, base-size*.8, size*.67, size*.51)]
    for a, b, rx, ry in clusters:
        # Quantized contour makes leaves chunky at the intended native resolution.
        points = []
        for i in range(20):
            angle = i*math.tau/20
            px = 2*round((a+rx*math.cos(angle))/2)
            py = 2*round((b+ry*math.sin(angle))/2)
            points.append((px, py))
        poly(points, '#4f596e')
    for i in range(int(size*2.5)):
        x = int(cx+r.uniform(-.84, .84)*size)
        y = int(base-size+r.uniform(-.74, .2)*size)
        if get(x, y) == rgb('#4f596e'):
            c = r.choice(['#596377', '#686a7e', '#786e83', '#966e84'])
            if x < cx and y > base-size:
                c = '#465568'
            rect(x, y, x+r.randint(2, 5), y+r.randint(1, 2), c)
    line(cx+2, base-14, cx+2, base, '#ad8389')

for args in [(12, 459, 29, 10), (46, 459, 25, 20), (82, 460, 21, 30),
             (111, 459, 14, 40), (391, 459, 16, 80),
             (422, 460, 25, 50), (459, 459, 28, 60), (501, 460, 34, 70)]:
    tree(*args)

# THE EIFFEL TOWER. Built from structural members, not a solid icon:
# rear trusses, four piers, perforated legs, curved arch, two galleries, upper pylon.
C = 256
iron = '#493947'
shade = '#63404f'
rust = '#965663'
copper = '#c37c70'
gold = '#ecaf82'
softiron = '#986f7b'


def beam(a, b, width=3, lit=True, color=iron):
    line(*a, *b, color, width)
    if lit:
        line(a[0]+1, a[1], b[0]+1, b[1], copper, 1)


def leg(outer_top, inner_top, outer_bottom, inner_bottom, n, light_side=False):
    # Four columns of cross-braced steel with their own rear webbing.
    ot, it, ob, ib = outer_top, inner_top, outer_bottom, inner_bottom
    def lerp(a, b, t):
        return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
    for i in range(n):
        a, b = lerp(ot, ob, i/n), lerp(it, ib, i/n)
        aa, bb = lerp(ot, ob, (i+1)/n), lerp(it, ib, (i+1)/n)
        line(*a, *bb, rust, 2)
        line(*b, *aa, shade, 2)
        line(a[0]+1, a[1], bb[0]+1, bb[1], copper)
        line(*a, *b, shade, 2)
        line(a[0], a[1]-1, b[0], b[1]-1, copper)
        mid_a, mid_b = lerp(a, b, .52), lerp(aa, bb, .52)
        line(*mid_a, *mid_b, shade)
        for p in (a, b):
            pixel(p[0], p[1], gold)
    beam(ot, ob, 4, True)
    beam(it, ib, 4, True)
    if light_side:
        line(it[0]+2, it[1], ib[0]+2, ib[1], gold)
    for t in (.26, .65):
        a, b = lerp(ot, it, t), lerp(ob, ib, t)
        line(*a, *b, rust)

# Rear supports, deliberately softer so the frontal iron stays readable.
leg((205, 377), (224, 377), (180, 457), (213, 457), 6)
leg((288, 377), (307, 377), (299, 457), (332, 457), 6)
# Main piers and their masonry blocks.
for x, w in [(128, 51), (175, 38), (299, 38), (333, 51)]:
    rect(x, 456, x+w, 466, '#806473')
    rect(x, 456, x+w, 458, '#efb693')
    rect(x+3, 459, x+w-3, 463, '#c08c85')
    rect(x-2, 465, x+w+2, 467, '#735b70')
    line(x+w-4, 459, x+w-4, 463, '#e3a38a')

# Broad curved arch. Segmented radial webbing is visible through its two ribs.
arch_outer, arch_inner = [], []
for i in range(49):
    a = math.pi + math.pi*i/48
    arch_outer.append((256+74*math.cos(a), 452+66*math.sin(a)))
    arch_inner.append((256+66*math.cos(a), 452+58*math.sin(a)))
path(arch_outer, shade, 4)
path(arch_inner, iron, 3)
path([(x+1, y-1) for x, y in arch_outer], copper)
for i in range(0, 49, 2):
    line(*arch_outer[i], *arch_inner[i], copper)
    if i+2 < 49:
        line(*arch_inner[i], *arch_outer[i+2], rust)
# Spandrels below the first gallery.
for sign in (-1, 1):
    for x, yy in [(10, 387), (22, 388), (34, 393), (46, 401), (58, 413)]:
        xx = C+sign*x
        beam((xx, 379), (xx, yy), 2, False, shade)
    line(C, 381, C+sign*64, 415, shade, 2)

leg((183, 379), (214, 379), (139, 455), (183, 455), 6)
leg((298, 379), (329, 379), (329, 455), (373, 455), 6, True)
# Outward foot flares and caps.
poly([(140, 447), (182, 447), (184, 455), (135, 455)], iron)
poly([(330, 447), (371, 447), (377, 455), (328, 455)], iron)
line(137, 454, 183, 454, copper, 2)
line(330, 454, 375, 454, gold, 2)
for x in list(range(141, 181, 6))+list(range(334, 374, 6)):
    rect(x, 449, x+1, 451, copper)

# Middle storey: a great open trapezoid, rear X bracing and two lattice legs.
beam((237, 302), (291, 365), 2, False, softiron)
beam((275, 302), (221, 365), 2, False, softiron)
line(209, 337, 303, 337, softiron, 2)
leg((220, 300), (237, 300), (184, 366), (216, 366), 6)
leg((275, 300), (292, 300), (296, 366), (328, 366), 6, True)
# Structural cross-rail, small maintenance stair on the left.
line(204, 339, 308, 339, shade, 2)
line(205, 338, 307, 338, copper)
for y in range(307, 363, 3):
    t = (y-300)/66
    xx = round(233+(211-233)*t)
    line(xx-2, y, xx+1, y, gold)

# Slender, gradually curving upper pylon.
levels = [(131, 6), (147, 7), (163, 9), (179, 11), (195, 13),
          (211, 16), (227, 19), (243, 23), (259, 28), (275, 33), (289, 38)]
for (y, hw), (yy, hh) in zip(levels, levels[1:]):
    for sign in (-1, 1):
        a, b = (C+sign*hw, y), (C+sign*hh, yy)
        innera, innerb = (C+sign*hw*.15, y), (C+sign*hh*.15, yy)
        line(*a, *innerb, shade, 2)
        line(*innera, *b, rust, 2)
        line(a[0]+1, y, innerb[0]+1, yy, copper)
        line(*a, *b, iron, 3)
        line(a[0]+1, y, b[0]+1, yy, gold if sign == 1 else copper)
        line(C+sign*hw*.53, y, C+sign*hh*.53, yy, shade)
    rect(C-hw, y, C+hw, y+1, shade)
    line(C-hw, y-1, C+hw, y-1, copper)
    line(C, y, C, yy, iron)
    for xx in (C-hw+1, C+hw-1):
        pixel(xx, y, gold)
# Single elevator running up the spine.
rect(254, 235, 258, 245, iron)
rect(255, 236, 257, 239, '#e4a780')
rect(255, 242, 257, 244, copper)


def gallery(y, half, tall):
    left, right = C-half, C+half
    # Rooftop rail.
    rect(left+3, y-5, right-3, y-4, iron)
    line(left+4, y-6, right-4, y-6, copper)
    for x in range(left+4, right-2, 4):
        line(x, y-4, x, y, shade)
        pixel(x, y-4, gold)
    rect(left-2, y, right+2, y+2, iron)
    rect(left-1, y, right+1, y, gold)
    rect(left+1, y+3, right-1, y+tall, shade)
    rect(left+1, y+3, right-1, y+3, copper)
    # Repeating gallery windows, dark on the left, sun-struck on the right.
    for x in range(left+4, right-2, 5):
        rect(x, y+4, x+2, y+tall-2, '#352f41')
        pixel(x+2, y+4, '#eeab79' if x > C else '#b67568')
    rect(left-3, y+tall, right+3, y+tall+2, iron)
    rect(left-2, y+tall, right+2, y+tall, copper)
    rect(left+6, y+tall+3, right-6, y+tall+4, shade)
    line(left+6, y+tall+3, right-6, y+tall+3, rust)

# Two strong horizontal galleries give the monument its unmistakeable rhythm.
gallery(290, 40, 8)
gallery(368, 77, 9)
# Summit cabin and radio aerial.
poly([(250, 131), (249, 119), (251, 112), (261, 112), (263, 119), (262, 131)], iron)
rect(248, 120, 264, 122, shade)
rect(249, 119, 263, 119, gold)
rect(251, 123, 261, 127, copper)
for x in (252, 255, 258, 261):
    rect(x, 123, x, 126, iron)
rect(248, 130, 264, 132, iron)
line(249, 130, 263, 130, gold)
poly([(252, 111), (254, 98), (258, 98), (260, 111)], shade)
line(258, 99, 260, 111, copper)
rect(253, 96, 259, 99, iron)
line(256, 77, 256, 96, iron)
line(257, 87, 257, 96, gold)
line(253, 91, 259, 91, shade)
pixel(256, 76, '#f6c29a')

# Pinprick evening lamps and minuscule pedestrians below the tower.
for x in (95, 117, 202, 310, 395, 416):
    rect(x, 448, x+1, 461, '#5e566d')
    rect(x-1, 447, x+2, 449, '#f9ce92')
    pixel(x, 446, '#fff0b5')
for x, y in [(99, 459), (108, 458), (231, 460), (239, 460), (280, 461), (288, 460), (402, 459)]:
    pixel(x, y-5, '#5e536c')
    rect(x, y-3, x+1, y, '#6d5872')
    pixel(x-1, y+1, '#6d5872')
    pixel(x+2, y+1, '#6d5872')

# THE SEINE. Compressed, wavering reflections preserve the actual ironwork above.
scene = bytes(canvas)
for y in range(481, 583):
    t = (y-481)/102
    base = mix('#948096', '#515b7c', t)
    src_y = 468-int((y-481)*3.8)
    offset = round(3*math.sin(y*.63)+2*math.sin(y*.23))
    for x in range(W):
        reflected = get(x+offset, src_y, scene)
        alpha = .41 if y % 5 < 3 else .22
        c = mix(base, reflected, alpha)
        pixel(x, y, c)
# Alternating long, flat wavelets; perspective length increases down the image.
for i in range(590):
    y = rng.randrange(484, 582)
    x = rng.randrange(-20, W)
    length = rng.randint(2, 14)+int((y-481)/16)
    c = rng.choice(['#77718e', '#a18b9f', '#626781', '#8c839e', '#bb929f'])
    if y > 548:
        c = rng.choice(['#5b6686', '#69728f', '#81829a', '#aa8d9e'])
    rect(x, y, x+length, y, c)
# The sun leaves a broken copper path rather than an airbrushed glow.
for y in range(489, 579, 3):
    t = (y-489)/90
    center = 346+int(6*math.sin(y*.38))
    span = int(13+29*t)
    for j in range(rng.randint(2, 4)):
        xx = center+rng.randint(-span, span)
        length = rng.randint(3, 16)
        color = rng.choice(['#d4a293', '#efb392', '#f9c79b', '#bc9396'])
        rect(xx, y, xx+length, y if j else y+1, color)
# Small dark ripples break up the inverted spire.
for y in range(497, 579, 7):
    x = 246+rng.randint(-12, 5)
    line(x, y, x+rng.randint(15, 39), y, '#7e768e')

# A small riverboat, offset to avoid the main reflected landmark.
line(82, 526, 152, 526, '#c19aa6')
line(71, 529, 164, 529, '#b795a5')
poly([(97, 518), (145, 518), (138, 524), (106, 524)], '#484b68')
line(99, 518, 143, 518, '#f0b593')
rect(106, 510, 134, 516, '#be989b')
rect(105, 509, 135, 510, '#edbe9f')
for x in range(109, 134, 6):
    rect(x, 512, x+3, 515, '#625d7b')
rect(116, 505, 124, 508, '#7e7086')
line(136, 506, 136, 517, '#5c526c')
rect(137, 507, 139, 509, '#cf7378')
line(111, 526, 143, 526, '#4e5978')

# NEAR QUAY: warm stone lip, dark cast-iron railing and a cobbled promenade.
poly([(0, 579), (512, 579), (512, 640), (0, 640)], '#343b57')
rect(0, 580, 511, 583, '#d0a09a')
rect(0, 584, 511, 588, '#997e91')
rect(0, 589, 511, 593, '#55516f')
rect(0, 594, 511, 639, '#43435f')
rect(0, 595, 511, 597, '#6f627d')
for x in range(0, 512, 31):
    line(x, 584, x, 588, '#756980')
# Sparse, perspective-shaped cobblestones; never random single-pixel noise.
for row, y in enumerate((603, 611, 621, 634)):
    width = 20+row*8
    for x in range(-width, 530, width):
        xx = x+(row%2)*(width//2)+rng.randrange(-3, 4)
        line(xx+2, y, xx+width-4, y, '#655872' if rng.random() < .45 else '#514a67')
        line(xx, y+2, xx-3, y+5+row, '#373b56')
        if rng.random() < .2:
            line(xx+5, y+1, xx+width-10, y+1, '#856878')
# Wrought-iron balustrade, geometric and restrained.
line(0, 562, 511, 562, '#353b56', 2)
line(0, 561, 511, 561, '#b28b95')
line(0, 584, 511, 584, '#343950', 2)
for x in range(4, W, 16):
    line(x, 563, x, 584, '#393d57', 2)
    line(x+1, 564, x+1, 579, '#7e7189')
    path([(x+2, 574), (x+8, 567), (x+14, 574), (x+8, 581), (x+2, 574)], '#45455f')
for x in (10, 174, 338, 500):
    rect(x-2, 558, x+2, 587, '#30374f')
    rect(x-3, 557, x+3, 559, '#605972')
    pixel(x, 555, '#b09195')

# Foreground lamp: luminous but still made exclusively of hard-edged pixels.
def lamp(x, base, height):
    top = base-height
    rect(x-5, base-3, x+5, base, '#282f48')
    rect(x-3, base-8, x+3, base-3, '#2e354e')
    rect(x-1, top+18, x+1, base-7, '#2b324a')
    line(x+1, top+23, x+1, base-9, '#9f7d87')
    rect(x-3, top+19, x+3, top+21, '#31344e')
    # Subtle octagonal halo, rather than a smooth glow.
    poly([(x-9, top+2), (x+8, top+2), (x+12, top+7), (x+12, top+15),
          (x+7, top+21), (x-8, top+21), (x-12, top+15), (x-12, top+7)], '#aa8b94')
    poly([(x-7, top+3), (x+7, top+3), (x+5, top+19), (x-5, top+19)], '#34374e')
    poly([(x-5, top+5), (x+5, top+5), (x+3, top+16), (x-3, top+16)], '#ffd18e')
    rect(x-2, top+6, x+2, top+15, '#fff0b3')
    line(x, top+4, x, top+18, '#8d696a')
    path([(x-8, top+3), (x-5, top), (x-2, top-2), (x+2, top-2), (x+5, top), (x+8, top+3)], '#30334b', 2)
    rect(x-5, top+18, x+5, top+20, '#30344c')
    line(x, top-6, x, top-2, '#30334b', 2)
    pixel(x+1, top-5, '#c99a87')

lamp(45, 613, 106)
lamp(465, 602, 88)

# A bicycle resting beside the railing: a tiny human detail, not a second focal point.
def ring(cx, cy, r, col):
    pts = [(round(cx+r*math.cos(i*math.tau/32)), round(cy+r*math.sin(i*math.tau/32))) for i in range(33)]
    path(pts, col)

for xx in (88, 117):
    ring(xx, 603, 9, '#232e46')
    ring(xx, 603, 7, '#837083')
    line(xx-6, 607, xx+6, 599, '#555069')
path([(88, 603), (98, 590), (104, 603), (88, 603), (111, 592), (104, 603)], '#bf877f', 2)
line(111, 590, 117, 603, '#bf877f', 2)
path([(111, 592), (110, 586), (114, 584), (118, 585)], '#292f49', 2)
line(97, 586, 99, 592, '#2b314b', 2)
line(93, 586, 101, 586, '#2b314b', 2)
line(102, 602, 108, 605, '#2b314b')

# Two quiet spectators on the embankment, lit on their sunset-facing edges.
# Ground shadows.
rect(386, 615, 419, 617, '#33374f')
rect(393, 618, 428, 619, '#393a53')
# Person in a copper coat.
ellipse(399, 581, 3, 4, '#d6a094')
rect(396, 576, 402, 578, '#392f48')
rect(396, 579, 397, 583, '#392f48')
poly([(396, 586), (402, 586), (405, 601), (395, 601)], '#b66973')
line(402, 587, 404, 598, '#e29a81')
path([(396, 588), (392, 596), (389, 595)], '#be807d', 2)
line(397, 602, 396, 612, '#292e46', 2)
line(402, 602, 404, 613, '#292e46', 2)
rect(394, 613, 397, 614, '#252c43')
rect(403, 613, 407, 614, '#252c43')
# A dark blue jacket.
ellipse(413, 578, 3, 4, '#c49186')
rect(410, 574, 416, 577, '#2c2c43')
poly([(409, 584), (416, 584), (419, 599), (408, 599)], '#283b53')
line(416, 585, 418, 595, '#827181')
path([(409, 586), (406, 594), (403, 595)], '#34415b', 3)
line(411, 599, 410, 613, '#262e45', 3)
line(416, 599, 418, 612, '#262e45', 3)
rect(407, 613, 411, 614, '#202a41')
rect(417, 612, 422, 614, '#202a41')

# Small plants along the corners anchor the dark foreground.
for x, y, h in [(0, 637, 17), (8, 639, 15), (19, 639, 9), (491, 639, 13), (502, 638, 19), (510, 638, 15)]:
    path([(x-5, y-h+5), (x, y), (x+3, y-h)], '#26364b', 2)
    line(x, y-3, x+8, y-h+4, '#38485d', 2)
    pixel(x+3, y-h, '#8c777f')

# Quantize to a genuine RGB565 palette before encoding. JPEG itself is 8-bit/channel.
for i in range(0, len(canvas), 3):
    r, g, b = canvas[i:i+3]
    canvas[i] = round(round(r*31/255)*255/31)
    canvas[i+1] = round(round(g*63/255)*255/63)
    canvas[i+2] = round(round(b*31/255)*255/31)

root = Path(__file__).resolve().parent
out = root / 'output'
out.mkdir(exist_ok=True)
ppm = root / '.eiffel-native.ppm'
ppm.write_bytes(f'P6\n{W} {H}\n255\n'.encode() + canvas)
try:
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ppm),
                    '-vf', 'scale=1536:1920:flags=neighbor', '-frames:v', '1',
                    '-c:v', 'mjpeg', '-q:v', '1', '-pix_fmt', 'yuvj444p',
                    str(out / 'eiffel-tower-pixel-art.jpg')], check=True)
finally:
    ppm.unlink(missing_ok=True)
print(out / 'eiffel-tower-pixel-art.jpg')
