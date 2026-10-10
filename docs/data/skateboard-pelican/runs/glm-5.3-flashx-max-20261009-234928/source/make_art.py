#!/usr/bin/env python3
"""
Pelican riding a skateboard — generated art pack.

Outputs (all written into ./output/):
  * pelican_skateboard.svg : animated SVG illustration (SMIL, plays in any browser)
  * pelican_skateboard.png : 800x600 poster frame
  * pelican_ride.mp4       : 1.5 s seamless 20 fps loop (800x600)

The scene is described once as a small scene-graph; one emitter turns it into
SVG, another rasterises it (pure Python, 2x supersampled) into PNG frames
that are then muxed with ffmpeg. Run:  python3 make_art.py
"""
import math
import os
import shutil
import struct
import subprocess
import zlib

W, H = 800, 600
SS = 2                      # supersampling factor for the rasteriser
SW, SH = W * SS, H * SS     # supersampled canvas
FPS = 20
DUR = 1.5                   # loop length in seconds (all periods divide it)
NF = int(FPS * DUR)         # 30 frames
OUT = "output"
FRAMES = "frames"

# ----------------------------------------------------------------------------
# tiny vector helpers
# ----------------------------------------------------------------------------

def lerp(a, b, t):
    return a + (b - a) * t


def mix(c0, c1, t):
    return tuple(max(0, min(255, int(round(lerp(c0[i], c1[i], t))))) for i in range(3))


def rot_about(p, c, deg):
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)


def cubic(p0, p1, p2, p3, n=20):
    """Flatten a cubic bezier; returns points AFTER p0 up to and incl p3."""
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
        y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
        out.append((x, y))
    return out


def catmull(ctrl, per=10):
    """Smooth polyline through control points (Catmull-Rom)."""
    if len(ctrl) < 3:
        return list(ctrl)
    P = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = [ctrl[0]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(1, per + 1):
            t = j / per
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2*p1[0] + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5 * (2*p1[1] + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            out.append((x, y))
    return out


def chain(*segs):
    """Concatenate bezier segments given as (p0, c1, c2, p3); p0 shared."""
    pts = [segs[0][0]]
    for s in segs:
        pts += cubic(s[0], s[1], s[2], s[3])
    return pts


def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=72):
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        x, y = rx * math.cos(th), ry * math.sin(th)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def rrect_pts(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def hexc(c):
    return "#%02x%02x%02x" % c


def fmt(v):
    s = ("%.2f" % v).rstrip("0").rstrip(".")
    return s if s else "0"

# ----------------------------------------------------------------------------
# palette
# ----------------------------------------------------------------------------
SKY_TOP  = (140, 202, 240)
SKY_BOT  = (233, 247, 252)
ROAD_TOP = (154, 160, 170)
ROAD_BOT = (105, 111, 122)
CURB     = (178, 184, 192)
DASH     = (238, 240, 244)
SUN      = (255, 211, 74)
SUN_GLOW = (255, 233, 158)
RAY      = (255, 199, 64)
CLOUD    = (255, 255, 255)
BIRD     = (90, 105, 120)
SHADOW   = (50, 56, 68)
DECK     = (224, 83, 59)
DECK_E   = (168, 54, 36)
GRIP     = (58, 52, 66)
SHEEN    = (244, 138, 100)
TRUCK    = (186, 195, 205)
TRUCK_D  = (141, 150, 161)
TIRE     = (255, 198, 58)
SPOKE    = (216, 142, 10)
HUB      = (252, 251, 248)
AXLE     = (95, 100, 108)
LEG_O    = (243, 146, 35)
LEG_E    = (212, 118, 18)
BODY     = (255, 255, 255)
EDGE     = (216, 209, 196)
SHADE    = (244, 239, 228)
FEATHER  = (224, 216, 200)
BEAK     = (255, 157, 46)
BEAK_E   = (221, 126, 24)
POUCH    = (241, 126, 12)
POUCH_E  = (210, 104, 6)
EYE      = (45, 41, 37)
SPEED    = (158, 190, 216)

# animation constants (shared by SVG + raster so both stay in sync)
T_BOB    = 0.5   # rider bob + wheel rev + dash scroll + speed-line flicker period
T_CLOUD  = 3.0   # cloud sway period
T_GLOW   = 1.5   # sun glow pulse period

# ----------------------------------------------------------------------------
# scene graph
#   node kinds: vgrad / g / poly / line / ell / rrect
#   dynamic hooks: move(t), rot(t)+rotc, op_func(t), r_func(t)
#   svg extra child elements via 'anims'
# ----------------------------------------------------------------------------

def line_node(pts, col, w, op=1.0, op_func=None, anims=None):
    return {"k": "line", "pts": pts, "col": col, "w": w, "op": op,
            "op_func": op_func, "anims": anims or []}


def poly_node(pts, fill, op=1.0, op_func=None, stroke=None, sw=0, anims=None):
    return {"k": "poly", "pts": pts, "fill": fill, "op": op, "op_func": op_func,
            "stroke": stroke, "sw": sw, "anims": anims or []}


def ell_node(cx, cy, rx, ry, fill, rot=0.0, op=1.0, op_func=None, r_func=None,
             stroke=None, sw=0, anims=None):
    return {"k": "ell", "cx": cx, "cy": cy, "rx": rx, "ry": ry, "rot": rot,
            "fill": fill, "op": op, "op_func": op_func, "r_func": r_func,
            "stroke": stroke, "sw": sw, "anims": anims or []}


def group(children, move=None, rot=None, rotc=None, anims=None):
    return {"k": "g", "ch": children, "move": move, "rot": rot, "rotc": rotc,
            "anims": anims or []}


def build_scene():
    scene = []

    # --- sky -----------------------------------------------------------------
    scene.append({"k": "vgrad", "y0": 0, "y1": 505, "c0": SKY_TOP, "c1": SKY_BOT,
                  "id": "sky"})

    # --- sun -----------------------------------------------------------------
    scene.append(ell_node(668, 102, 95, 95, SUN_GLOW, op=0.35,
                          r_func=lambda t: 95 + 7 * math.sin(math.pi * ((t / T_GLOW) % 1)),
                          anims=['<animate attributeName="rx" values="95;102;95" dur="%gs" repeatCount="indefinite"/>' % T_GLOW]))
    scene.append(ell_node(668, 102, 46, 46, SUN))
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        x0, y0 = 668 + 56 * math.cos(a), 102 + 56 * math.sin(a)
        x1, y1 = 668 + 72 * math.cos(a), 102 + 72 * math.sin(a)
        scene.append(line_node([(x0, y0), (x1, y1)], RAY, 5, op=0.8))

    # --- clouds (gentle sway) --------------------------------------------------
    def cloud(cx, cy, op):
        return [
            ell_node(cx, cy, 54, 20, CLOUD, op=op),
            ell_node(cx - 38, cy + 8, 34, 14, CLOUD, op=op),
            ell_node(cx + 42, cy + 8, 38, 15, CLOUD, op=op),
        ]

    for i, (cx, cy, op) in enumerate([(150, 112, 0.95), (398, 72, 0.92), (258, 168, 0.8)]):
        off = i / 3.0
        scene.append(group(
            cloud(cx, cy, op),
            move=lambda t, o=off: (15 * math.sin(math.pi * ((t / T_CLOUD + o) % 1)),
                                   5 * math.sin(math.pi * ((t / T_CLOUD + o) % 1))),
            anims=['<animateTransform attributeName="transform" type="translate" values="0 0;15 5;0 0" dur="%gs" begin="-%gs" repeatCount="indefinite"/>' % (T_CLOUD, T_CLOUD * off)],
        ))

    # --- birds -----------------------------------------------------------------
    def bird(cx, cy, s):
        return line_node([(cx - 13*s, cy), (cx - 6*s, cy - 9*s), (cx, cy),
                          (cx + 6*s, cy - 9*s), (cx + 13*s, cy)], BIRD, 2.5)
    scene.append(group([bird(235, 96, 1.0), bird(298, 118, 0.8)],
                       move=lambda t: (12 * math.sin(math.pi * ((t / T_CLOUD) % 1)),
                                       -7 * math.sin(math.pi * ((t / T_CLOUD) % 1))),
                       anims=['<animateTransform attributeName="transform" type="translate" values="0 0;12 -7;0 0" dur="%gs" repeatCount="indefinite"/>' % T_CLOUD]))

    # --- road ------------------------------------------------------------------
    scene.append({"k": "vgrad", "y0": 505, "y1": 600, "c0": ROAD_TOP, "c1": ROAD_BOT,
                  "id": "road"})
    scene.append(poly_node(rrect_pts(0, 505, 800, 10), CURB))

    dashes = [poly_node(rrect_pts(-60 + 100 * k, 550, 62, 9), DASH, op=0.9)
              for k in range(10)]
    scene.append(group(dashes,
                       move=lambda t: (-((t / T_BOB) * 100) % 100, 0),
                       anims=['<animateTransform attributeName="transform" type="translate" values="0 0;-100 0" dur="%gs" repeatCount="indefinite"/>' % T_BOB]))

    # --- shadow (breathes opposite to the bob) ----------------------------------
    scene.append(ell_node(410, 509, 176, 10, SHADOW, op=0.30,
                          op_func=lambda t: 0.30 - 0.06 * math.sin(math.pi * ((t / T_BOB) % 1)),
                          r_func=lambda t: 176 - 6 * math.sin(math.pi * ((t / T_BOB) % 1)),
                          anims=['<animate attributeName="rx" values="176;170;176" dur="%gs" repeatCount="indefinite"/>' % T_BOB,
                                 '<animate attributeName="opacity" values="0.3;0.24;0.3" dur="%gs" repeatCount="indefinite"/>' % T_BOB]))

    # --- speed lines -------------------------------------------------------------
    speeds = [(66, 430, 206, 430, 7), (36, 464, 176, 464, 6),
              (76, 497, 226, 497, 7), (30, 398, 112, 398, 5)]
    for i, (x0, y0, x1, y1, w) in enumerate(speeds):
        off = i * 0.25
        op_f = lambda t, o=off: 0.25 + 0.65 * math.sin(math.pi * ((t / T_BOB + o) % 1))
        scene.append(line_node([(x0, y0), (x1, y1)], SPEED, w, op_func=op_f,
                               anims=['<animate attributeName="opacity" values="0.25;0.9;0.25" dur="%gs" begin="-%gs" repeatCount="indefinite"/>' % (T_BOB, T_BOB * off),
                                      '<animateTransform attributeName="transform" type="translate" values="0 0;-16 0;0 0" dur="%gs" begin="-%gs" repeatCount="indefinite" additive="sum"/>' % (T_BOB, T_BOB * off)]))

    # =========================================================================
    # RIDER  (pelican + skateboard bob as one unit)
    # =========================================================================
    rider = []

    def wheel(wx, wy):
        r = []
        # truck (drawn first, behind the wheel)
        r.append(poly_node([(wx - 6, 464), (wx + 6, 464), (wx + 11, 487), (wx - 11, 487)], TRUCK))
        r.append(line_node([(wx - 12, wy), (wx + 12, wy)], TRUCK_D, 4))
        # wheel
        r.append(ell_node(wx, wy, 16, 16, TIRE))
        spokes = group([
            line_node([(wx - 11, wy), (wx + 11, wy)], SPOKE, 3),
            line_node([(wx, wy - 11), (wx, wy + 11)], SPOKE, 3),
        ], rot=lambda t: ((t / T_BOB) * 360) % 360, rotc=(wx, wy),
           anims=['<animateTransform attributeName="transform" type="rotate" from="0 %d %d" to="360 %d %d" dur="%gs" repeatCount="indefinite"/>' % (wx, wy, wx, wy, T_BOB)])
        r.append(spokes)
        r.append(ell_node(wx, wy, 6.5, 6.5, HUB))
        r.append(ell_node(wx, wy, 2.5, 2.5, AXLE))
        return r

    rider += wheel(312, 489)
    rider += wheel(500, 489)

    # --- deck -------------------------------------------------------------------
    deck = chain(
        ((246, 436), (252, 452), (262, 454), (276, 454)),
        ((276, 454), (546, 454), (546, 454), (546, 454)),   # straight top
        ((546, 454), (562, 454), (572, 450), (582, 438)),
        ((582, 438), (582, 450), (582, 450), (582, 450)),   # nose tip
        ((582, 450), (572, 462), (562, 466), (546, 466)),
        ((546, 466), (276, 466), (276, 466), (276, 466)),   # straight bottom
        ((276, 466), (262, 466), (252, 464), (246, 448)),
    )
    rider.append(poly_node(deck, DECK, stroke=DECK_E, sw=2))
    rider.append(line_node(catmull([(251, 441), (258, 451), (278, 453), (545, 453),
                                    (564, 450), (576, 441)], per=6), GRIP, 3))
    rider.append(line_node([(282, 460), (540, 460)], SHEEN, 2.5, op=0.9))

    # --- legs & feet (bent riding stance) -----------------------------------------
    rider.append(line_node(catmull([(366, 328), (350, 376), (354, 420), (358, 448)], per=8), LEG_O, 12))
    rider.append(line_node(catmull([(442, 332), (466, 380), (452, 424), (456, 448)], per=8), LEG_O, 12))
    rider.append(poly_node([(342, 455), (384, 455), (377, 449), (369, 445), (351, 445), (346, 449)],
                           LEG_O, stroke=LEG_E, sw=1.5))
    rider.append(poly_node([(446, 455), (488, 455), (481, 449), (473, 445), (455, 445), (450, 449)],
                           LEG_O, stroke=LEG_E, sw=1.5))

    # --- tail --------------------------------------------------------------------
    rider.append(poly_node([(322, 262), (246, 230), (260, 258), (232, 272), (262, 288),
                            (246, 312), (304, 298), (334, 304)],
                           (247, 243, 234), stroke=EDGE, sw=2))

    # --- body ----------------------------------------------------------------------
    rider.append(ell_node(408, 292, 104, 70, BODY, rot=-10, stroke=EDGE, sw=3))
    rider.append(ell_node(398, 318, 82, 34, SHADE, rot=-10, op=0.85))
    rider.append(line_node(catmull([(340, 300), (386, 320), (436, 326)], per=8), FEATHER, 2.5))
    rider.append(line_node(catmull([(368, 336), (420, 344)], per=4), FEATHER, 2))

    # --- raised wing (clearly sweeping above the body) ---------------------------
    wing = chain(
        ((395, 260), (324, 244), (280, 198), (266, 142)),
        ((266, 142), (306, 164), (342, 184), (368, 212)),
        ((368, 212), (392, 238), (402, 252), (400, 268)),
        ((400, 268), (390, 272), (378, 268), (395, 260)),
    )
    rider.append(poly_node(wing, (250, 247, 240), stroke=EDGE, sw=2.5))
    rider.append(line_node([(360, 244), (306, 180)], FEATHER, 2))
    rider.append(line_node([(374, 252), (322, 194)], FEATHER, 2))
    rider.append(line_node([(386, 260), (338, 208)], FEATHER, 2))

    # --- neck (S-curve, under-stroke gives the outline) ---------------------------------
    neck = catmull([(436, 268), (458, 242), (474, 210), (490, 180), (506, 160), (528, 148)], per=8)
    rider.append(line_node(neck, EDGE, 36))
    rider.append(line_node(neck, BODY, 31))

    # --- head ------------------------------------------------------------------------------
    rider.append(ell_node(548, 140, 27, 27, BODY, stroke=EDGE, sw=3))
    rider.append(poly_node([(531, 121), (517, 103), (528, 110), (527, 99), (538, 117)],
                           BODY, stroke=EDGE, sw=1.5))          # little crest tuft
    rider.append(ell_node(557, 131, 5.2, 5.2, EYE))
    rider.append(ell_node(559, 129, 1.7, 1.7, (255, 255, 255)))

    # --- beak: pouch first, upper mandible over it -------------------------------------------
    pouch = chain(
        ((572, 148), (604, 152), (640, 168), (666, 192)),   # top edge (under beak)
        ((666, 192), (640, 218), (600, 224), (578, 202)),   # sagging bottom
        ((578, 202), (568, 192), (566, 166), (572, 148)),
    )
    rider.append(poly_node(pouch, POUCH, stroke=POUCH_E, sw=2))
    upper = chain(
        ((572, 126), (608, 128), (646, 148), (678, 184)),
        ((678, 184), (678, 184), (668, 196), (668, 196)),
        ((668, 196), (640, 168), (604, 152), (572, 148)),
    )
    rider.append(poly_node(upper, BEAK, stroke=BEAK_E, sw=2))
    rider.append(line_node([(576, 133), (632, 152), (660, 176)], BEAK_E, 2, op=0.9))
    rider.append(line_node([(588, 139), (599, 142)], BEAK_E, 2))
    rider.append(line_node([(586, 170), (600, 196), (630, 206)], POUCH_E, 2, op=0.6))

    scene.append(group(rider,
                       move=lambda t: (0, -4 * math.sin(math.pi * ((t / T_BOB) % 1))),
                       anims=['<animateTransform attributeName="transform" type="translate" values="0 0;0 -4;0 0" dur="%gs" repeatCount="indefinite"/>' % T_BOB]))
    return scene

# ----------------------------------------------------------------------------
# rasteriser
# ----------------------------------------------------------------------------

class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.R = bytearray(w * h)
        self.G = bytearray(w * h)
        self.B = bytearray(w * h)

    def blit(self, y, x0, x1, col, op):
        if x1 <= x0:
            return
        x0 = max(0, x0)
        x1 = min(self.w, x1)
        if x1 <= x0 or y < 0 or y >= self.h:
            return
        s, e = y * self.w + x0, y * self.w + x1
        if op >= 0.999:
            n = e - s
            self.R[s:e] = bytes([col[0]]) * n
            self.G[s:e] = bytes([col[1]]) * n
            self.B[s:e] = bytes([col[2]]) * n
        else:
            a, ia = op, 1 - op
            self.R[s:e] = bytes(min(255, int(col[0] * a + v * ia)) for v in self.R[s:e])
            self.G[s:e] = bytes(min(255, int(col[1] * a + v * ia)) for v in self.G[s:e])
            self.B[s:e] = bytes(min(255, int(col[2] * a + v * ia)) for v in self.B[s:e])


def fill_poly(cv, pts, col, op=1.0):
    ys = [p[1] for p in pts]
    j0 = max(0, int(math.ceil(min(ys) - 0.5)))
    j1 = min(cv.h - 1, int(math.floor(max(ys) - 0.5)))
    n = len(pts)
    for j in range(j0, j1 + 1):
        yc = j + 0.5
        xs = []
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if y1 == y2:
                continue
            if (y1 <= yc < y2) or (y2 <= yc < y1):
                t = (yc - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            i0 = max(0, int(math.ceil(xs[k] - 0.5)))
            i1 = min(cv.w - 1, int(math.floor(xs[k + 1] - 0.5)))
            cv.blit(j, i0, i1 + 1, col, op)


def draw_line(cv, pts, col, w, op=1.0, closed=False):
    h = w / 2.0
    segs = list(zip(pts, pts[1:]))
    if closed and len(pts) > 2:
        segs.append((pts[-1], pts[0]))
    for (a, b) in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        nx, ny = -dy / L * h, dx / L * h
        fill_poly(cv, [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                       (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], col, op)
    for p in pts:  # round caps + joints
        fill_poly(cv, ellipse_pts(p[0], p[1], h, h, n=20), col, op)


def apply_tr(tr, p):
    for op_ in reversed(tr):
        if op_[0] == "t":
            p = (p[0] + op_[1], p[1] + op_[2])
        else:
            p = rot_about(p, (op_[1], op_[2]), op_[3])
    return p


def draw_tree(nodes, cv, t, tr=()):
    for nd in nodes:
        k = nd["k"]
        if k == "vgrad":
            for y in range(nd["y0"], nd["y1"]):
                c = mix(nd["c0"], nd["c1"], (y - nd["y0"]) / max(1, nd["y1"] - nd["y0"]))
                cv.blit(y, 0, cv.w, c, 1.0)
        elif k == "g":
            tr2 = tr
            if nd["move"]:
                dx, dy = nd["move"](t)
                tr2 = tr2 + (("t", dx, dy),)
            if nd["rot"]:
                tr2 = tr2 + (("r", nd["rotc"][0], nd["rotc"][1], nd["rot"](t)),)
            draw_tree(nd["ch"], cv, t, tr2)
        elif k == "poly":
            pts = [apply_tr(tr, p) for p in nd["pts"]]
            op = nd["op_func"](t) if nd["op_func"] else nd["op"]
            fill_poly(cv, pts, nd["fill"], op)
            if nd["stroke"]:
                draw_line(cv, pts + [pts[0]], nd["stroke"], nd["sw"], op)
        elif k == "line":
            pts = [apply_tr(tr, p) for p in nd["pts"]]
            op = nd["op_func"](t) if nd["op_func"] else nd["op"]
            draw_line(cv, pts, nd["col"], nd["w"], op)
        elif k == "ell":
            rx = nd["r_func"](t) if nd["r_func"] else nd["rx"]
            op = nd["op_func"](t) if nd["op_func"] else nd["op"]
            pts = [apply_tr(tr, p) for p in ellipse_pts(nd["cx"], nd["cy"], rx, nd["ry"], nd["rot"])]
            fill_poly(cv, pts, nd["fill"], op)
            if nd["stroke"]:
                draw_line(cv, pts + [pts[0]], nd["stroke"], nd["sw"], op)
        elif k == "rrect":
            pts = [apply_tr(tr, p) for p in rrect_pts(nd["x"], nd["y"], nd["w"], nd["h"])]
            fill_poly(cv, pts, nd["fill"], nd["op"])


def render_frame(scene, t, ss=SS):
    cv = Canvas(int(W * ss), int(H * ss))
    scaled = scale_tree(scene, ss)
    draw_tree(scaled, cv, t)
    return cv


def scale_tree(nodes, s):
    """Scale every coordinate by s (for supersampling)."""
    out = []
    for nd in nodes:
        k = nd["k"]
        if k == "vgrad":
            out.append({"k": k, "y0": int(nd["y0"]*s), "y1": int(nd["y1"]*s),
                        "c0": nd["c0"], "c1": nd["c1"], "id": nd["id"]})
        elif k == "g":
            g = {"k": k, "ch": scale_tree(nd["ch"], s), "move": nd["move"],
                 "rot": nd["rot"], "rotc": nd["rotc"], "anims": nd["anims"]}
            if nd["rotc"]:
                g["rotc"] = (nd["rotc"][0]*s, nd["rotc"][1]*s)
            if nd["move"]:
                g["move"] = (lambda f, s=s: (lambda t: tuple(v*s for v in f(t))))(nd["move"])
            out.append(g)
        elif k == "poly":
            out.append({"k": k, "pts": [(p[0]*s, p[1]*s) for p in nd["pts"]],
                        "fill": nd["fill"], "op": nd["op"], "op_func": nd["op_func"],
                        "stroke": nd["stroke"], "sw": nd["sw"]*s, "anims": nd["anims"]})
        elif k == "line":
            out.append({"k": k, "pts": [(p[0]*s, p[1]*s) for p in nd["pts"]],
                        "col": nd["col"], "w": nd["w"]*s, "op": nd["op"],
                        "op_func": nd["op_func"], "anims": nd["anims"]})
        elif k == "ell":
            out.append({"k": k, "cx": nd["cx"]*s, "cy": nd["cy"]*s, "rx": nd["rx"]*s,
                        "ry": nd["ry"]*s, "rot": nd["rot"], "fill": nd["fill"],
                        "op": nd["op"], "op_func": nd["op_func"],
                        "r_func": (lambda f, s=s: (lambda t: f(t)*s))(nd["r_func"]) if nd["r_func"] else None,
                        "stroke": nd["stroke"], "sw": nd["sw"]*s, "anims": nd["anims"]})
        elif k == "rrect":
            out.append({"k": "poly", "pts": [(p[0]*s, p[1]*s) for p in rrect_pts(nd["x"], nd["y"], nd["w"], nd["h"])],
                        "fill": nd["fill"], "op": nd["op"], "op_func": None,
                        "stroke": None, "sw": 0, "anims": []})
    return out

# ----------------------------------------------------------------------------
# PNG output + 2x box downsample
# ----------------------------------------------------------------------------

def downsample2(cv):
    w2, h2 = cv.w // 2, cv.h // 2
    chans = []
    for buf in (cv.R, cv.G, cv.B):
        rows = []
        for oy in range(h2):
            a = buf[(2*oy)*cv.w:(2*oy)*cv.w + cv.w]
            b = buf[(2*oy+1)*cv.w:(2*oy+1)*cv.w + cv.w]
            row = bytes(((x + y) >> 1) for x, y in zip(a, b))
            rows.append(bytes(((x + y) >> 1) for x, y in zip(row[0::2], row[1::2])))
        chans.append(rows)
    return w2, h2, chans


def write_png(path, w, h, chans):
    raw = bytearray()
    R, G, B = chans
    row = bytearray(3 * w)
    for y in range(h):
        row[0::3] = R[y]
        row[1::3] = G[y]
        row[2::3] = B[y]
        raw.append(0)
        raw += row

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)

# ----------------------------------------------------------------------------
# SVG emitter
# ----------------------------------------------------------------------------

def emit_svg(nodes, defs):
    parts = []
    for nd in nodes:
        k = nd["k"]
        if k == "vgrad":
            defs.append(
                '<linearGradient id="%s" x1="0" y1="%s" x2="0" y2="%s" gradientUnits="userSpaceOnUse">'
                '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
                % (nd["id"], fmt(nd["y0"]), fmt(nd["y1"]), hexc(nd["c0"]), hexc(nd["c1"])))
            parts.append('<rect x="0" y="%s" width="%d" height="%s" fill="url(#%s)"/>'
                         % (fmt(nd["y0"]), W, fmt(nd["y1"] - nd["y0"]), nd["id"]))
        elif k == "g":
            inner = emit_svg(nd["ch"], defs) + "".join(nd["anims"])
            parts.append("<g>%s</g>" % inner)
        elif k == "poly":
            pts = " ".join("%s,%s" % (fmt(p[0]), fmt(p[1])) for p in nd["pts"])
            attrs = 'points="%s" fill="%s"' % (pts, hexc(nd["fill"]))
            if nd["op"] != 1 or nd["op_func"]:
                attrs += ' opacity="%s"' % fmt(nd["op"])
            if nd["stroke"]:
                attrs += ' stroke="%s" stroke-width="%s" stroke-linejoin="round"' % (hexc(nd["stroke"]), fmt(nd["sw"]))
            parts.append("<polygon %s>%s</polygon>" % (attrs, "".join(nd["anims"])))
        elif k == "line":
            pts = " ".join("%s,%s" % (fmt(p[0]), fmt(p[1])) for p in nd["pts"])
            attrs = ('points="%s" fill="none" stroke="%s" stroke-width="%s" '
                     'stroke-linecap="round" stroke-linejoin="round" opacity="%s"'
                     % (pts, hexc(nd["col"]), fmt(nd["w"]), fmt(nd["op"])))
            parts.append("<polyline %s>%s</polyline>" % (attrs, "".join(nd["anims"])))
        elif k == "ell":
            attrs = 'cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"' % (
                fmt(nd["cx"]), fmt(nd["cy"]), fmt(nd["rx"]), fmt(nd["ry"]), hexc(nd["fill"]))
            if nd["rot"]:
                attrs += ' transform="rotate(%s %s %s)"' % (fmt(nd["rot"]), fmt(nd["cx"]), fmt(nd["cy"]))
            if nd["op"] != 1 or nd["op_func"]:
                attrs += ' opacity="%s"' % fmt(nd["op"])
            if nd["stroke"]:
                attrs += ' stroke="%s" stroke-width="%s"' % (hexc(nd["stroke"]), fmt(nd["sw"]))
            parts.append("<ellipse %s>%s</ellipse>" % (attrs, "".join(nd["anims"])))
    return "".join(parts)

# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    os.makedirs(OUT, exist_ok=True)
    scene = build_scene()

    # ---- animated SVG ----
    defs = []
    body = emit_svg(scene, defs)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
           'role="img" aria-labelledby="t d">\n'
           '<title id="t">Pelican riding a skateboard</title>\n'
           '<desc id="d">A cheerful white pelican with a big orange beak rides a red skateboard '
           'along a road, with spinning wheels, drifting clouds and speed lines.</desc>\n'
           '<defs>%s</defs>\n%s\n</svg>\n' % (W, H, W, H, "".join(defs), body))
    svg_path = os.path.join(OUT, "pelican_skateboard.svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print("wrote %s (%.1f KB)" % (svg_path, len(svg) / 1024.0))

    # ---- poster PNG ----
    cv = render_frame(scene, 0.125)
    w2, h2, chans = downsample2(cv)
    png_path = os.path.join(OUT, "pelican_skateboard.png")
    write_png(png_path, w2, h2, chans)
    print("wrote %s (%dx%d)" % (png_path, w2, h2))

    # ---- video frames ----
    os.makedirs(FRAMES, exist_ok=True)
    try:
        for i in range(NF):
            t = i / FPS
            cv = render_frame(scene, t)
            w2, h2, chans = downsample2(cv)
            write_png(os.path.join(FRAMES, "f%03d.png" % i), w2, h2, chans)
        mp4 = os.path.join(OUT, "pelican_ride.mp4")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f%03d.png"),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
               "-movflags", "+faststart", mp4]
        subprocess.run(cmd, check=True)
        print("wrote %s (%.1f KB, %d frames @ %d fps = %.2fs loop)"
              % (mp4, os.path.getsize(mp4) / 1024.0, NF, FPS, NF / FPS))
    finally:
        shutil.rmtree(FRAMES, ignore_errors=True)


if __name__ == "__main__":
    main()
