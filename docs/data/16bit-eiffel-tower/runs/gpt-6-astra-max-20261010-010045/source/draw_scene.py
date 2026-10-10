#!/usr/bin/env python3
"""A native 256 x 224, tiled, indexed-colour SNES-style Paris background.

Only Python's standard library is used. Geometry is rasterised on the pixel
lattice, without antialiasing. The finished picture is packed into 8x8 4bpp
characters with local palettes, decoded, then written as an indexed PNG.
Run: python3 draw_scene.py
"""
import math
import os
import random
import struct
import zlib
from collections import Counter

W, H = 256, 224
PAL = []
NAMES = {}

def color(name, value):
    # RGB555 DAC values, expanded to eight-bit channels for the PNG.
    rgb5 = [round(v * 31 / 255) for v in bytes.fromhex(value.lstrip('#'))]
    rgb = tuple((v << 3) | (v >> 2) for v in rgb5)
    if rgb not in PAL:
        PAL.append(rgb)
    NAMES[name] = PAL.index(rgb)
    return NAMES[name]

# Colour ramps are deliberately hue-shifted, rather than shaded with black.
sky = [color('sky' + str(i), v) for i, v in enumerate([
    '272d50', '333958', '474263', '604e71', '7e5e7e',
    '9e708b', 'bc8495', 'd5989c', 'e9ad9e', 'f3c19f', 'f7d0a6'])]
star_dim = color('starlight dim', '8f91ae')
star = color('starlight', 'd5cbd1')
moon = color('ivory', 'f9e7bd')
moon_shade = color('moon gold', 'd7bea9')
cloud0 = color('cloud shadow', '605976')
cloud1 = color('cloud violet', '88718a')
cloud2 = color('cloud rose', 'b78898')
cloud3 = color('cloud light', 'e5a7a6')
cloud4 = color('cloud silver', 'f8c7ac')
far0 = color('horizon haze', 'ad8c9b')
far1 = color('horizon silhouettes', '957f95')
far2 = color('horizon shade', '82738d')
city0 = color('city shadow', '59566f')
city1 = color('city blue', '72677e')
city2 = color('city lilac', '907c8b')
city3 = color('city light', 'b4989c')
city4 = color('city peach', 'c7a4a2')
roof0 = color('slate dark', '45475f')
roof1 = color('slate light', '626079')
window = color('window', 'ebc29a')
window_dim = color('window dim', 'c49c94')
park0 = color('park shadow', '404959')
park1 = color('park deep', '51566b')
park2 = color('park light', '6c6b7b')
park3 = color('park mist', '88818a')
t0 = color('iron outline', '3b3044')
t1 = color('iron shadow', '674653')
t2 = color('iron copper', 'a36b56')
t3 = color('iron amber', 'd29666')
t4 = color('iron gold', 'f7c583')
t5 = color('iron lights', 'ffe8ad')
stone0 = color('stone dark', '484559')
stone1 = color('stone shade', '6a5c72')
stone2 = color('stone', '9a7c8c')
stone3 = color('stone lip', 'c39b9d')
stone4 = color('stone gleam', 'e6b8a4')
water = [color('water' + str(i), v) for i, v in enumerate([
    '30394f', '3d415d', '4c4868', '635473', '806581',
    '9c7a90', 'b9929b', 'dbac9f'])]
leaf0 = color('foliage outline', '202c40')
leaf1 = color('foliage deep', '293a4c')
leaf2 = color('foliage blue', '3b4b5c')
leaf3 = color('foliage light', '53616b')
leaf4 = color('foliage rim', '7b7b7d')
lamp0 = color('lamp iron', '242b3d')
lamp1 = color('lamp rim', '827476')
lamp2 = color('lamp glow', 'b48b79')
lamp3 = color('lamp honey', 'e6b77f')
lamp4 = color('lamp core', 'ffedb6')
coat = color('red coat', 'ac6a78')

im = [[sky[0]] * W for _ in range(H)]
rng = random.Random(1889)

def pix(x, y, c):
    x, y = int(x), int(y)
    if 0 <= x < W and 0 <= y < H:
        im[y][x] = c

def rect(x0, y0, x1, y1, c):
    x0, y0, x1, y1 = map(int, (x0, y0, x1, y1))
    if x1 < x0 or y1 < y0:
        return
    for y in range(max(0, y0), min(H - 1, y1) + 1):
        for x in range(max(0, x0), min(W - 1, x1) + 1):
            im[y][x] = c

def line(x0, y0, x1, y1, c, width=1):
    x0, y0, x1, y1 = map(lambda x: int(round(x)), (x0, y0, x1, y1))
    dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if width == 1:
            pix(x0, y0, c)
        else:
            r = width // 2
            rect(x0-r, y0-r, x0 + width-r-1, y0 + width-r-1, c)
        if x0 == x1 and y0 == y1:
            break
        e = 2 * err
        if e >= dy:
            err += dy
            x0 += sx
        if e <= dx:
            err += dx
            y0 += sy

def poly(points, c):
    # Even/odd fill at pixel centres; vertices are intentionally integral.
    for y in range(max(0, math.floor(min(p[1] for p in points))),
                   min(H-1, math.ceil(max(p[1] for p in points))) + 1):
        sy = y + 0.5
        hits = []
        for i, (x0, y0) in enumerate(points):
            x1, y1 = points[(i+1) % len(points)]
            if (y0 <= sy < y1) or (y1 <= sy < y0):
                hits.append(x0 + (sy-y0) * (x1-x0)/(y1-y0))
        hits.sort()
        for i in range(0, len(hits)-1, 2):
            rect(math.ceil(hits[i]-.5), y, math.floor(hits[i+1]-.5), y, c)

def path(points, c, width=1):
    for a, b in zip(points, points[1:]):
        line(*a, *b, c, width)

def ellipse(cx, cy, rx, ry, c):
    for y in range(max(0, math.ceil(cy-ry)), min(H-1, math.floor(cy+ry))+1):
        for x in range(max(0, math.ceil(cx-rx)), min(W-1, math.floor(cx+rx))+1):
            if ((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 1:
                pix(x, y, c)

def stepped_oval(cx, cy, rx, ry, c):
    # Coarser two-pixel silhouette steps for leafy, tile-era clusters.
    for yy in range(-ry, ry+1, 2):
        width = int(rx * math.sqrt(max(0, 1-(yy/max(ry, 1))**2)))
        width = (width//2)*2
        rect(cx-width, cy+yy, cx+width, cy+yy+1, c)

# --- Painted, banded sky --------------------------------------------------
boundaries = [0, 20, 38, 56, 74, 91, 107, 122, 137, 151, 164]
for y in range(H):
    k = max(i for i, edge in enumerate(boundaries) if edge <= y)
    rect(0, y, W-1, y, sky[k])
    if k and y-boundaries[k] < 3:
        row = y-boundaries[k]
        for x in range(W):
            if ((x + (y % 2)*2) % 4) < (3-row):
                pix(x, y, sky[k-1])

# Tiny constellations: no subpixel edges or blur.
for x, y in [(12,15),(29,26),(78,8),(103,32),(124,9),(170,13),
             (191,25),(223,10),(242,33),(208,44),(87,46),(16,47),
             (65,61),(179,56),(230,64),(115,53),(159,37),(8,64)]:
    pix(x, y, star_dim)
for x, y in [(91,20),(211,16),(26,58)]:
    pix(x, y, moon)
    pix(x-1, y, star_dim)
    pix(x+1, y, star_dim)
    pix(x, y-1, star_dim)
    pix(x, y+1, star_dim)

# Crescent, cut out of the actual banded sky rather than a flat backdrop.
sky_save = [row[:] for row in im]
ellipse(54, 37, 9, 10, moon_shade)
ellipse(53, 36, 8, 9, moon)
for y in range(24, 49):
    for x in range(44, 69):
        if ((x-58)/8)**2 + ((y-32)/9)**2 <= 1:
            pix(x, y, sky_save[y][x])
pix(48, 39, moon_shade)
pix(50, 44, moon_shade)

# Long, hand-stepped clouds, with warm lower edges.
poly([(-4,79),(7,79),(7,76),(17,76),(17,73),(30,73),(30,70),
      (42,70),(42,72),(51,72),(51,76),(64,76),(64,78),(82,78),
      (82,81),(96,81),(96,84),(87,84),(87,86),(61,86),(61,88),
      (26,88),(26,87),(-4,87)], cloud0)
poly([(-2,83),(18,83),(18,81),(31,81),(31,79),(46,79),(46,80),
      (57,80),(57,83),(80,83),(80,84),(90,84),(90,86),(59,86),
      (59,88),(25,88),(25,87),(-2,87)], cloud1)
rect(5,87,27,87,cloud2)
rect(34,88,60,88,cloud2)
rect(63,86,78,86,cloud2)
rect(94,87,110,87,cloud1)
rect(103,90,122,90,cloud1)
rect(113,91,126,91,cloud2)
rect(16,91,43,91,cloud1)

poly([(174,57),(183,57),(183,54),(194,54),(194,51),(207,51),
      (207,48),(217,48),(217,51),(226,51),(226,55),(241,55),
      (241,57),(252,57),(252,59),(266,59),(266,64),(221,64),
      (221,66),(189,66),(189,63),(166,63),(166,60),(174,60)], sky[3])
poly([(183,60),(197,60),(197,57),(219,57),(219,59),(232,59),
      (232,61),(256,61),(256,65),(220,65),(220,66),(188,66),
      (188,64),(178,64),(178,62),(183,62)], cloud0)
rect(199,65,225,65,cloud1)
rect(231,64,250,64,cloud1)
rect(154,66,174,66,sky[3])
rect(163,67,181,67,cloud0)

poly([(-10,112),(4,112),(4,109),(21,109),(21,106),(36,106),
      (36,108),(48,108),(48,110),(62,110),(62,112),(77,112),
      (77,114),(97,114),(97,118),(62,118),(62,120),(25,120),
      (25,121),(-10,121)], cloud2)
poly([(-4,117),(18,117),(18,115),(29,115),(29,116),(46,116),
      (46,117),(76,117),(76,118),(66,118),(66,120),(23,120),
      (23,121),(-4,121)], cloud3)
rect(0,121,19,121,cloud4)
rect(33,120,56,120,cloud4)
rect(71,122,91,122,cloud3)
rect(94,124,116,124,cloud2)
rect(80,130,108,130,cloud3)
rect(90,131,116,131,cloud4)

poly([(175,105),(190,105),(190,101),(204,101),(204,99),(218,99),
      (218,103),(231,103),(231,106),(248,106),(248,109),(262,109),
      (262,115),(224,115),(224,117),(191,117),(191,115),(176,115),
      (176,112),(162,112),(162,109),(175,109)], cloud2)
poly([(182,111),(197,111),(197,108),(214,108),(214,110),(230,110),
      (230,111),(254,111),(254,114),(224,114),(224,116),(190,116),
      (190,114),(177,114),(177,113),(182,113)], cloud3)
rect(197,116,219,116,cloud4)
rect(240,115,255,115,cloud3)
rect(157,117,177,117,cloud2)
rect(181,123,208,123,cloud3)
rect(198,125,219,125,cloud3)
rect(8,135,37,135,cloud3)
rect(2,137,27,137,cloud4)
rect(227,134,255,134,cloud3)
rect(216,137,240,137,cloud4)

# A pair of distant swallows, composed of five-pixel wing silhouettes.
path([(96,103),(98,104),(100,102)],cloud0)
path([(108,98),(110,99),(112,97)],cloud0)

# --- Paris: three planes of roofs and chimneys ---------------------------
rect(0,164,255,182,far1)
x = -5
while x < W:
    bw = rng.randint(5, 13)
    top = rng.randint(151,160)
    rect(x,top,x+bw,169,far0)
    rect(x+1,top-1,x+bw-1,top,far0)
    if rng.random() < .6:
        rect(x+2,top-3,x+3,top,far0)
    x += bw+1
# A very distant church spire and small cupola.
poly([(72,158),(72,151),(75,151),(75,146),(76,141),(77,146),
      (77,151),(80,151),(80,159)],far1)
pix(76,140,far1)
rect(84,154,92,166,far1)
ellipse(88,154,4,5,far1)
rect(87,147,89,150,far1)
pix(88,145,far1)
# Low, hazy central blocks behind the ironwork.
for x, ww, yy in [(98,13,156),(113,9,152),(122,16,156),(142,13,155),
                  (156,14,153),(174,11,158),(189,10,155)]:
    rect(x,yy,x+ww,172,far2)
    rect(x-1,yy,x+ww+1,yy,far1)
    for xx in range(x+3,x+ww-1,4):
        rect(xx,yy+5,xx,yy+6,far0)
        rect(xx,yy+11,xx,yy+12,far0)

# A small domed roof on the eastern skyline.
rect(209,151,224,169,city2)
rect(211,145,222,154,city3)
ellipse(216,145,6,7,city2)
path([(210,145),(211,141),(213,138),(216,137),(219,139),(221,143)],city4)
rect(215,134,217,137,city1)
pix(216,131,city1)
line(216,132,216,134,city1)
rect(210,148,222,149,city1)
for xx in range(212,223,4):
    rect(xx,151,xx+1,155,city1)


def house(x, w, top, bottom, lit, shade, roof_height=5):
    rect(x,top,x+w-1,bottom,lit)
    rect(x+w-4,top,x+w-1,bottom,shade)
    # Slate mansard: a sloped cap, ridge and a lit cornice.
    poly([(x-1,top),(x+2,top-roof_height),(x+w-5,top-roof_height),
          (x+w,top),(x+w,top+1),(x-1,top+1)],roof0)
    line(x+2,top-roof_height,x+w-5,top-roof_height,roof1)
    rect(x-1,top+1,x+w,top+1,city3)
    if w > 13:
        rect(x+3,top-roof_height-3,x+4,top-roof_height,roof0)
        pix(x+3,top-roof_height-3,city2)
    for xx in range(x+3,x+w-4,5):
        rect(xx,top-3,xx+1,top-1,city2)
        pix(xx,top-3,city3)
    for yy in range(top+4,bottom-1,5):
        for xx in range(x+3,x+w-4,4):
            c = window_dim if rng.random() < .31 else city0
            if rng.random() < .16:
                c = window
            rect(xx,yy,xx+1,yy+1,c)
            pix(xx,yy+2,shade)
    rect(x,bottom-3,x+w-1,bottom-3,shade)
    if w > 12:
        rect(x+6,bottom-2,x+8,bottom,city0)

for args in [(-5,19,150,177,city2,city1,5), (14,17,157,177,city3,city1,4),
             (32,21,153,177,city2,city1,6), (54,18,158,177,city3,city1,5),
             (74,19,161,178,city2,city1,4), (94,14,163,178,city3,city1,4),
             (182,19,160,178,city2,city1,4), (202,20,158,178,city3,city1,5),
             (224,18,152,178,city2,city0,6), (243,18,158,178,city3,city1,5)]:
    house(*args)

# Park and tree-lined avenue, a miniature world underneath the tower.
rect(0,174,255,182,park1)
rect(91,173,193,176,park2)
poly([(141,171),(146,171),(161,184),(128,184)],stone3)
line(140,174,132,181,stone4)
line(148,174,157,181,stone2)
for x, y, rx, ry in [(65,173,11,6),(82,171,9,7),(94,174,8,5),
                      (105,170,8,5),(117,172,7,4),(128,171,4,3),
                      (161,171,5,4),(174,173,7,5),(190,170,10,6),
                      (201,174,10,6),(227,175,13,7)]:
    rect(x,y,x+1,181,city0)
    stepped_oval(x,y,rx,ry,park1)
    stepped_oval(x-2,y-2,max(2,rx-3),max(2,ry-2),park2)
    line(x-rx+3,y+ry-1,x+rx-2,y+ry-1,park0)
    pix(x-rx+2,y,park3)
rect(84,181,207,182,park0)
for x in [87,92,99,175,178,182,195,201]:
    pix(x,180,stone3)

# --- Eiffel Tower -------------------------------------------------------
# A true open lattice. Every opening retains the scenery behind it.
C = 144
# Shaft profile; terrace heights follow the real tower's proportions.
profile = [(47,140,148),(56,140,148),(66,139,149),(77,138,150),
           (89,136,152),(101,134,154),(112,131,157),(121,129,159)]
# Rear faces: narrower diagonals, visible through the main iron members.
for i in range(len(profile)-1):
    y0,l0,r0 = profile[i]
    y1,l1,r1 = profile[i+1]
    line(l0+2,y0,r1-3,y1,t1)
    line(r0-2,y0,l1+3,y1,t1)
    line(C+2,y0,C+2,y1,t1)
# Fine X bracing, with alternating warm / shadow-facing edges.
for i in range(len(profile)-1):
    y0,l0,r0 = profile[i]
    y1,l1,r1 = profile[i+1]
    line(l0+1,y0+1,r1-1,y1-1,t0,2)
    line(r0-1,y0+1,l1+1,y1-1,t0,2)
    line(l0+1,y0+1,r1-1,y1-1,t3)
    line(r0-1,y0+1,l1+1,y1-1,t2)
    line(l0,y0,r0,y0,t1)
    line(l0,y0-1,r0-1,y0-1,t3)
    pix(l0+1,y0-1,t4)
# Four flaring uprights and their narrow sunward edges.
left = [(l,y) for y,l,r in profile]
right = [(r,y) for y,l,r in profile]
path(left,t0,3)
path(right,t0,3)
path(left,t3,2)
path([(l-1,y) for y,l,r in profile],t4)
path(right,t2,2)
path([(r-1,y) for y,l,r in profile],t3)
# The far-side stanchion gives the tower a subtly off-centre front face.
path([(147,48),(147,68),(148,83),(150,100),(155,119)],t1)
for y in [64,76,88,100,111]:
    pix(C,y,t4)

# Middle trapezoid, between the first and second observation terraces.
y0,y1=126,149
left_middle=[(130,126),(127,136),(121,149)]
right_middle=[(158,126),(161,136),(167,149)]
# Two bays, broad enough for secondary lattice diamonds.
for ya,yb,la,lb,ra,rb in [(127,138,130,125,158,163),
                         (138,149,125,121,163,167)]:
    line(la+2,ya,rb-2,yb,t0,2)
    line(ra-2,ya,lb+2,yb,t0,2)
    line(la+2,ya,rb-2,yb,t3)
    line(ra-2,ya,lb+2,yb,t2)
    line(la+3,ya,C,yb,t2)
    line(ra-3,ya,C,yb,t1)
    line(la,ya,ra,ya,t0)
    line(la,ya-1,ra,ya-1,t3)
# Front inner rails, curving apart as they approach the lower deck.
path([(137,127),(135,137),(131,149)],t1,2)
path([(151,127),(153,137),(157,149)],t1,2)
path([(137,127),(135,137),(131,149)],t3)
path([(151,127),(153,137),(157,149)],t2)
path(left_middle,t0,3)
path(right_middle,t0,3)
path(left_middle,t3,2)
path([(x-1,y) for x,y in left_middle],t4)
path(right_middle,t2,2)
path([(x-1,y) for x,y in right_middle],t3)

# Four splayed feet; trusses have open sky/park between them.
left_outer=[(122,155),(119,164),(114,173),(107,181)]
left_inner=[(134,155),(130,162),(125,172),(121,181)]
right_outer=[(288-x,y) for x,y in left_outer]
right_inner=[(288-x,y) for x,y in left_inner]
for outer,inner,side in [(left_outer,left_inner,0),(right_outer,right_inner,1)]:
    # Deep rear uprights.
    path([(x+(-2 if side else 2),y) for x,y in inner],t1,2)
    for i in range(3):
        xo,ya=outer[i]; xn,yb=outer[i+1]
        xi,_=inner[i]; xj,_=inner[i+1]
        line(xo,ya,xj,yb,t0,3)
        line(xi,ya,xn,yb,t0,3)
        line(xo,ya,xj,yb,t3 if not side else t2)
        line(xi,ya,xn,yb,t2)
        line(xo,ya,xi,ya,t3)
    path(outer,t0,4)
    path(inner,t0,3)
    path(outer,t2 if side else t3,2)
    path([(x-1,y) for x,y in outer],t4 if not side else t3)
    path(inner,t3,2)
    path([(x-1,y) for x,y in inner],t4 if not side else t2)

# The monumental curved arch is separate from the structural leg trusses.
arch=[(120,179),(122,173),(125,167),(129,162),(134,158),
      (139,156),(144,155),(149,156),(154,158),(159,162),
      (163,167),(166,173),(168,179)]
path(arch,t0,3)
path([(x,y-1) for x,y in arch],t3)
path(arch,t2)
# Tiny radial brackets beneath the first-floor deck.
for xx, yy in [(126,163),(132,158),(138,156),(150,156),(156,158),(162,163)]:
    line(xx,154,xx,yy,t1)
    pix(xx,155,t4)

# Decks: railings, lit cornices, dark undersides and rows of warm windows.
def deck(x0,x1,y,h):
    rect(x0,y,x1,y+h,t0)
    rect(x0+1,y,x1-1,y,t4)
    rect(x0+1,y+1,x1-1,y+1,t2)
    for x in range(x0+2,x1,3):
        pix(x,y+1,t5)
        pix(x,y+2,t1)
    rect(x0-1,y+3,x1+1,y+3,t3)
    rect(x0,y+4,x1,y+4,t0)
    line(x0+2,y+5,x1-2,y+5,t1)
    # Discrete balusters, not a smooth gradient.
    line(x0+1,y-2,x1-1,y-2,t2)
    for x in range(x0+1,x1,4):
        pix(x,y-1,t3)
    pix(x0,y,t5)

deck(127,161,121,4)
deck(118,170,150,5)
# First-floor central enclosed gallery: three amber lit panes.
rect(138,151,151,152,t1)
for xx in [140,144,148]:
    rect(xx,151,xx+1,152,t4)
rect(118,153,170,153,t4)
rect(122,155,166,155,t1)
# Stone foundation blocks, with glinting metal shoes.
for x0,x1 in [(104,122),(166,184)]:
    rect(x0+2,180,x1-2,182,t0)
    rect(x0,183,x1,185,stone1)
    rect(x0+1,182,x1-1,182,stone4)
    rect(x0+2,181,x1-2,181,t3)
    rect(x0,184,x1,184,stone2)

# Summit: antenna, lantern, viewing gallery, and its pointed cap.
line(C,18,C,32,t0)
line(C-1,20,C-1,32,t4)
pix(C,17,t5)
rect(142,30,145,33,t2)
poly([(139,39),(141,34),(146,34),(149,39)],t0)
path([(140,38),(142,34),(145,34)],t4)
rect(141,39,147,44,t2)
rect(140,40,148,40,t4)
for xx in [141,144,147]:
    rect(xx,41,xx,43,t5)
rect(138,44,150,46,t0)
rect(138,44,149,44,t4)
rect(139,45,149,45,t2)
rect(140,47,148,48,t3)
pix(139,44,t5)
# The lit elevator line only peeks through, rather than bisecting every bay.
for yy in [50,51,57,58,65,72,73,80,87,94,95,103,110,116]:
    pix(143,yy,t4)

# --- Embankment ---------------------------------------------------------
rect(0,185,255,187,stone3)
rect(0,188,255,194,stone1)
rect(0,188,255,188,stone4)
rect(0,194,255,195,stone0)
rect(0,191,255,191,stone2)
for x in range(-4,256,17):
    rect(x,189,x,190,stone0)
    rect(x+8,192,x+8,193,stone0)
    rect(x+2,189,x+8,189,stone3)
for x in range(1,256,8):
    pix(x,186,stone2)
# Small railing along the far bank.
line(52,182,236,182,stone0)
for x in range(54,237,6):
    line(x,181,x,185,stone0)
    pix(x,181,stone2)
# A stairway down to the water at the right.
poly([(218,186),(230,186),(242,196),(226,196)],stone0)
for y in range(187,196,2):
    x=218+(y-186)
    rect(x,y,x+11,y,stone2)
    pix(x,y,stone3)

# Miniature lamps and promenading figures provide the sense of game scale.
for xx in [69,94,194,218]:
    line(xx,177,xx,185,lamp0)
    rect(xx-1,176,xx+1,178,lamp2)
    pix(xx,177,lamp4)
    rect(xx-1,175,xx+1,175,lamp0)
    pix(xx,174,lamp0)
    rect(xx-1,185,xx+1,185,lamp0)
for xx, yy, cc in [(81,181,coat),(85,181,city0),(201,182,roof0)]:
    pix(xx,yy-3,stone4)
    rect(xx,yy-2,xx+1,yy,cc)
    pix(xx,yy+1,roof0)
    pix(xx+2,yy+1,roof0)

# --- Seine: clusters of horizontal pixels, never filtered ---------------
for y in range(196,H):
    k=4 if y<201 else 3 if y<208 else 2 if y<217 else 1
    rect(0,y,255,y,water[k])
# Repeating tile-like ripple language, varied by hand-seeded offsets.
for y in range(197,224,3):
    for x in range(-8,260,20):
        xx=x+rng.randint(-5,7)
        length=rng.randint(4,14)
        c=water[4 if y<208 else 3]
        rect(xx,y,xx+length,y,c)
        if rng.random()<.5:
            rect(xx+3,y+1,xx+length-2,y+1,water[2 if y<209 else 1])
for x,y,w in [(2,199,18),(26,202,13),(79,198,12),(101,204,17),
              (184,201,18),(225,199,11),(206,207,16),(75,211,14),
              (89,216,18),(185,216,9),(232,214,17),(111,222,11),
              (37,214,13),(174,207,11),(63,207,8)]:
    rect(x,y,x+w,y,water[5 if y<205 else 4])
    if w>14:
        rect(x+4,y+1,x+w-3,y+1,water[3])
# Tower's broken gold reflection expands toward the viewer.
reflections=[(196,134,18),(197,140,14),(199,128,13),(199,148,13),
             (201,137,17),(203,129,12),(203,149,12),(204,135,21),
             (207,137,16),(208,125,10),(210,147,18),(211,132,19),
             (214,124,13),(214,145,16),(217,139,22),(219,128,14),
             (221,148,15),(222,135,8)]
for y,x,w in reflections:
    rect(x-3,y,x+w+3,y,water[5])
    rect(x,y,x+w,y,water[7] if y<210 else water[6])
    if y<208:
        rect(x+3,y,x+w-3,y,t4 if y%3 else t3)
    if y in (197,201,204):
        rect(x+5,y,x+9,y,t5)
# Small lamp reflections far away.
for xx in [69,94,194,218]:
    rect(xx-2,197,xx+2,197,water[7])
    rect(xx-1,199,xx+3,199,water[6])
    rect(xx-3,203,xx,203,water[5])

# A tiny Seine launch, its windows lit for the evening crossing.
line(207,208,238,208,water[0])
poly([(204,204),(237,204),(232,208),(210,208)],roof0)
rect(208,204,235,204,stone3)
rect(213,199,229,203,city0)
rect(211,198,230,198,roof0)
rect(211,197,228,197,city3)
for xx in [214,218,222,226]:
    rect(xx,200,xx+1,202,window)
line(231,201,231,204,roof0)
pix(231,200,stone4)
rect(211,210,229,210,water[1])
rect(218,211,225,211,water[5])

# --- Foreground terrace, wrought iron, and the close gas lamp ------------
poly([(0,184),(13,188),(79,224),(0,224)],stone0)
poly([(0,189),(64,224),(0,224)],roof0)
poly([(0,184),(9,186),(80,223),(73,224),(0,189)],stone2)
line(0,186,75,223,stone3)
line(0,189,68,224,leaf0)
# Diagonal seams through the cut stone coping.
for xx,yy in [(10,191),(25,199),(42,208),(59,217)]:
    line(xx,yy,xx+4,yy-2,stone0)
    pix(xx+5,yy-2,stone4)
# Pavement receding into the left corner.
for p in [[(0,202),(37,224)],[(0,214),(19,224)],[(13,209),(34,198)],
          [(27,221),(52,208)],[(0,214),(12,207)]]:
    line(*p[0],*p[1],city0)
# Wrought-iron parapet, its posts silhouetted against the river.
line(0,174,69,211,lamp0)
line(0,176,69,213,stone1)
line(0,184,69,221,lamp0)
for xx in range(6,70,9):
    yy=174+round(xx*37/69)
    line(xx,yy-2,xx,yy+10,lamp0,2)
    pix(xx,yy-3,lamp1)
    if xx<61:
        line(xx+2,yy+2,xx+7,yy+9,lamp0)
        line(xx+2,yy+7,xx+7,yy+4,lamp0)

# Tree on the left: designed silhouette, then patches of pixel foliage.
path([(3,217),(7,194),(10,170),(8,149),(2,128)],leaf0,6)
path([(8,170),(21,150),(29,140)],leaf0,4)
path([(9,157),(2,145),(-5,142)],leaf0,4)
path([(8,184),(0,171)],leaf0,3)
# Each canopy group uses coherent, stepped clusters rather than pixel noise.
canopies=[(-5,123,15,13),(7,131,17,14),(22,139,16,12),
          (3,150,22,16),(19,154,16,12),(-4,168,18,13),
          (2,112,10,9),(1,183,11,10)]
for cx,cy,rx,ry in canopies:
    stepped_oval(cx,cy,rx,ry,leaf0)
for cx,cy,rx,ry in canopies:
    stepped_oval(cx-2,cy-4,max(3,rx-4),max(3,ry-5),leaf1)
    stepped_oval(cx+1,cy-6,max(2,rx-8),max(2,ry-8),leaf2)
# Crisp leaf shapes along the sky-facing rim.
for x,y in [(3,103),(8,109),(14,120),(19,126),(26,130),(34,136),
            (36,145),(32,150),(30,157),(19,163),(12,175),(8,183),
            (1,122),(8,138),(17,147),(2,158)]:
    rect(x,y,x+3,y+1,leaf2)
    pix(x+2,y-1,leaf3)
    pix(x+4,y+2,leaf1)
# Tufts of three-to-five pixels, with one dark notch underneath each spray.
# Clipping the tufts to existing leaves keeps the silhouette deliberate.
def leaf_spray(x,y):
    for dx,dy in [(0,0),(1,0),(2,0),(-1,1),(0,1),(1,1),(2,1),(3,1)]:
        xx,yy=x+dx,y+dy
        if 0<=xx<W and 0<=yy<H:
            old=im[yy][xx]
            if old==leaf1:
                pix(xx,yy,leaf2)
            elif old==leaf2:
                pix(xx,yy,leaf3)
    for dx,dy in [(0,2),(1,2),(2,3)]:
        xx,yy=x+dx,y+dy
        if 0<=xx<W and 0<=yy<H and im[yy][xx] in (leaf1,leaf2,leaf3):
            pix(xx,yy,leaf1)

for x,y in [(-2,113),(3,117),(8,124),(15,130),(0,130),(4,137),
            (21,137),(28,142),(10,145),(-2,147),(17,151),(25,155),
            (6,158),(12,164),(-1,166),(4,173),(2,180)]:
    leaf_spray(x,y)
# Select small holes to keep the crown airy.
for x,y in [(27,137),(21,129),(29,151),(18,161),(7,114)]:
    if 0<=y<H and 0<=x<W:
        pix(x,y,sky_save[y][x])
        pix(x+1,y,sky_save[y][x+1])
path([(9,171),(8,190),(4,206)],leaf2)
path([(11,170),(17,157),(24,148)],leaf1)

# Smaller right-bank tree, leaving open space around the tower.
path([(252,188),(250,173),(251,158),(246,146)],leaf0,4)
path([(251,165),(239,154),(235,147)],leaf0,3)
for cx,cy,rx,ry in [(257,146,15,13),(245,146,12,10),(237,154,13,10),
                   (253,163,17,14),(246,175,11,9),(262,179,13,11)]:
    stepped_oval(cx,cy,rx,ry,leaf1)
    stepped_oval(cx-3,cy-3,max(3,rx-4),max(2,ry-4),leaf2)
    stepped_oval(cx-4,cy-5,max(2,rx-8),max(2,ry-7),leaf3)
for x,y in [(232,146),(228,153),(235,140),(243,134),(240,163),(236,171),(249,172)]:
    rect(x,y,x+2,y,leaf4)
    rect(x-1,y+1,x+3,y+1,leaf3)

for x,y in [(247,138),(243,143),(250,148),(235,151),(230,155),
            (241,158),(249,160),(253,165),(242,170),(247,176),(254,178)]:
    leaf_spray(x,y)

# The foreground lantern is a single bright focal accent, not a fuzzy glow.
lx=39
# A sparse, stepped halo; all colours are in the indexed palette.
for xx,yy in [(lx-5,150),(lx+5,150),(lx-6,153),(lx+6,153),
              (lx-5,157),(lx+5,157),(lx-2,145),(lx+2,145)]:
    pix(xx,yy,lamp2)
line(lx,160,lx,211,lamp0,3)
line(lx-1,164,lx-1,205,lamp1)
rect(lx-2,168,lx+2,170,lamp0)
pix(lx-1,168,stone3)
rect(lx-2,198,lx+2,200,lamp0)
rect(lx-3,208,lx+3,213,lamp0)
rect(lx-5,214,lx+5,215,lamp0)
rect(lx-3,212,lx+2,212,lamp1)
# Tapered glazing, dark bonnet and a pinprick finial.
poly([(lx-5,148),(lx+6,148),(lx+4,159),(lx-3,159)],lamp0)
poly([(lx-3,150),(lx+4,150),(lx+2,157),(lx-2,157)],lamp3)
rect(lx-2,150,lx+2,154,lamp4)
rect(lx-1,151,lx+1,156,moon)
line(lx,150,lx,157,lamp2)
rect(lx-4,148,lx+4,148,lamp1)
poly([(lx-6,148),(lx-2,145),(lx-1,143),(lx+1,143),(lx+2,145),(lx+6,148)],lamp0)
pix(lx,141,lamp1)
pix(lx,142,lamp0)
rect(lx-3,158,lx+3,159,lamp0)
rect(lx-1,160,lx+1,161,lamp1)
# A few warm marks on the paving directly beneath it.
line(32,217,38,220,stone2)
line(37,217,43,220,stone1)

# Foreground leaves barely enter the bottom corners.
poly([(0,208),(6,210),(8,216),(15,216),(20,224),(0,224)],leaf0)
for x,y in [(1,209),(7,216),(13,218),(2,220)]:
    line(x,y,x+4,y+2,leaf2)
poly([(236,224),(238,219),(243,220),(244,215),(250,216),(251,211),
      (256,212),(256,224)],leaf0)
for x,y in [(239,220),(246,217),(252,214)]:
    line(x,y,x+3,y+1,leaf2)

# --- Explicit 8x8 / 4bpp tile pipeline ----------------------------------
def distance(a,b):
    # Perceptual-ish weighted RGB; local reductions only affect rare shades.
    a,b=PAL[a],PAL[b]
    return 2*(a[0]-b[0])**2 + 3*(a[1]-b[1])**2 + (a[2]-b[2])**2

adjusted=[]
for ty in range(0,H,8):
    for tx in range(0,W,8):
        count=Counter(im[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8))
        original=len(count)
        # Merge the least consequential pair until the cell is 4bpp-safe.
        while len(count)>16:
            best=None
            for a in count:
                for b in count:
                    if a==b:
                        continue
                    cost=count[a]*distance(a,b)
                    # Preserve bright single-pixel illumination and silhouettes.
                    if a in (t5,lamp4,moon,t0,leaf0):
                        cost*=2
                    if best is None or cost<best[0]:
                        best=(cost,a,b)
            _,a,b=best
            for yy in range(ty,ty+8):
                for xx in range(tx,tx+8):
                    if im[yy][xx]==a:
                        im[yy][xx]=b
            count[b]+=count.pop(a)
        if original>16:
            adjusted.append((tx//8,ty//8,original))

# An actual SNES character consists of four one-bit planes, 32 bytes total.
# Encode and decode those characters so that the published pixels are exactly
# the 8x8 tiled image validated here, not a separate high-resolution render.
tiles=[]
for ty in range(0,H,8):
    for tx in range(0,W,8):
        local=sorted({im[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)})
        assert len(local)<=16
        lookup={c:i for i,c in enumerate(local)}
        pattern=bytearray(32)
        for y in range(8):
            for x in range(8):
                value=lookup[im[ty+y][tx+x]]
                for plane in range(4):
                    offset=(plane//2)*16+y*2+(plane%2)
                    pattern[offset]|=((value>>plane)&1)<<(7-x)
        tiles.append((local,bytes(pattern)))
        for y in range(8):
            for x in range(8):
                value=0
                for plane in range(4):
                    offset=(plane//2)*16+y*2+(plane%2)
                    value|=((pattern[offset]>>(7-x))&1)<<plane
                im[ty+y][tx+x]=local[value]

used=sorted({p for row in im for p in row})
assert len(used)<=128
assert len(tiles)==32*28
remap={old:i for i,old in enumerate(used)}

def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)

def save_png(filename):
    raw=b''.join(b'\0'+bytes(remap[c] for c in row) for row in im)
    png=b'\x89PNG\r\n\x1a\n'
    png+=chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))
    png+=chunk(b'PLTE',b''.join(bytes(PAL[c]) for c in used))
    png+=chunk(b'tEXt',b'Title\0La Tour, heure bleue')
    png+=chunk(b'tEXt',b'Description\0Native 256x224 pixel art. 32x28 eight-pixel tiles; 4bpp per tile. No antialiasing or resampling.')
    png+=chunk(b'IDAT',zlib.compress(raw,9))
    png+=chunk(b'IEND',b'')
    with open(filename,'wb') as f:
        f.write(png)

os.makedirs('output',exist_ok=True)
save_png('output/eiffel_twilight.png')
print('Saved output/eiffel_twilight.png')
print(f'{W} x {H}; {len(used)} total colours; {len(tiles)} 8x8 tiles; maximum {max(len(p) for p,_ in tiles)} colours per tile.')
print(f'{len(adjusted)} tiles had minor palette merges: {adjusted}')
print(f'PNG: {os.path.getsize("output/eiffel_twilight.png")} bytes')
