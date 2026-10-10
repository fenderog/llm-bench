#!/usr/bin/env python3
"""
Pelican riding a skateboard - parametric SVG scene generator.

Usage:
  python3 make_pelican.py --static output/pelican_skateboard.svg
  python3 make_pelican.py --frame t out.svg
  python3 make_pelican.py --frames dir/ fps count

The scene is periodic with a 4 s loop: scenery scrolls left, wheels spin,
the rider bobs and leans, dust puffs trail behind the rear wheel.
t=None -> static master with embedded SMIL animation.
"""

import argparse
import math
import os

# ---------------------------------------------------------------- palette
SKY_TOP = "#a8e6ff"
SKY_BOT = "#54bdf2"
SUN = "#ffd94e"
SUN_EDGE = "#f0b429"
SUN_GLOW = "#fff3ae"
CLOUD = "#ffffff"
HILL_A = "#c6e6b4"
HILL_B = "#b2d9a1"
ROAD_TOP = "#7b8794"
ROAD_BOT = "#5a6570"
ROAD_EDGE = "#4a545e"
DASH = "#ffd95e"
SPECKLE = "#8a94a0"

BODY = "#fdfaf0"
WING = "#f0e8d2"
WING_LINE = "#d9cfb2"
OUTLINE = "#37393f"
BEAK_TOP = "#fcb04b"
BEAK_BOT = "#f97316"
POUCH = "#ffc06a"
POUCH_HI = "#ffe0a3"
LEGS = "#f28c28"
BLUSH = "#ffb1b8"
EYE = "#23262b"

HELMET = "#e5484d"
HELMET_DK = "#c23840"
HELMET_STRIPE = "#ffffff"

DECK = "#ff5964"
DECK_DK = "#e04852"
GRIP = "#31363d"
TRUCK = "#7e8a99"
WHEEL = "#2d2f33"
WHEEL_RIM = "#232529"
HUB = "#ffd95e"
HUB_RIM = "#c08a1e"
WHEEL_DOT = "#4a4f57"

W = H = 1024
SCROLL_SPEED = 128.0     # px / s (leftward scenery)
LOOP = 4.0                # scene loop period, s
BOB_HZ = 1.5              # rider bounce
LEAN_HZ = 0.75            # rider lean
WHEEL_DEG_S = 180.0       # wheel spin
DUST_HZ = 0.75
WHOOSH_HZ = 0.5


def n(v):
    """round nicely for compact svg output"""
    r = round(v, 2)
    if r == int(r):
        return str(int(r))
    return str(r)


# ---------------------------------------------------------------- helpers
def cloud(cx, cy, s):
    e = lambda dx, dy, rx, ry: (
        f'<ellipse cx="{n(cx+dx*s)}" cy="{n(cy+dy*s)}" rx="{n(rx*s)}" ry="{n(ry*s)}"/>'
    )
    return (
        '<g fill="' + CLOUD + '" opacity="0.95">'
        + e(0, 0, 52, 30) + e(44, -13, 45, 27) + e(86, 3, 38, 22) + e(42, 13, 42, 24)
        + "</g>"
    )


def tiled(group_body, period):
    """repeat a scenery fragment so it can scroll seamlessly over 1024 px"""
    out = []
    for shift in (-period, 0, period):
        out.append(f'<g transform="translate({shift} 0)">{group_body}</g>')
    return "".join(out)


# ---------------------------------------------------------------- board
def skateboard():
    """static board; wheel groups are animated by caller-added transforms"""
    p = []
    # deck (side view with kicktails)
    deck = (
        "M316,740 C332,745 344,752 354,760 L714,760 "
        "C724,752 736,745 752,740 L754,758 "
        "C740,763 728,770 718,780 L350,780 "
        "C340,770 328,763 314,758 Z"
    )
    p.append(f'<path d="{deck}" fill="{DECK}" stroke="{OUTLINE}" stroke-width="6" stroke-linejoin="round"/>')
    # grip tape along the top edge
    grip = "M320,743 C335,747.5 347,755 356,762 L714,762 C723,755 735,747.5 750,743"
    p.append(f'<path d="{grip}" fill="none" stroke="{GRIP}" stroke-width="9" stroke-linecap="round"/>')
    # bottom accent stripe
    p.append(f'<path d="M356,775 L714,775" stroke="{DECK_DK}" stroke-width="5" stroke-linecap="round"/>')
    # trucks
    for x in (400, 668):
        p.append(f'<path d="M{x},778 L{x},798" stroke="{TRUCK}" stroke-width="20" stroke-linecap="round"/>')
    # bolts
    for x in (400, 668):
        p.append(f'<circle cx="{x}" cy="763" r="3.5" fill="#1c2025"/>')
    # wheels
    for x in (400, 668):
        dots = []
        for ang in (0, 120, 240):
            a = math.radians(ang)
            dots.append(
                f'<circle cx="{n(x+25*math.cos(a))}" cy="{n(840+25*math.sin(a))}" r="4" fill="{WHEEL_DOT}"/>'
            )
        p.append(
            f'<g id="wheel{x}">'
            f'<circle cx="{x}" cy="840" r="40" fill="{WHEEL}" stroke="{WHEEL_RIM}" stroke-width="5"/>'
            f'<circle cx="{x}" cy="840" r="15" fill="{HUB}" stroke="{HUB_RIM}" stroke-width="4"/>'
            + "".join(dots) + "</g>"
        )
    return "".join(p)


# ---------------------------------------------------------------- pelican
def pelican():
    p = []
    # ---- legs and webbed feet (behind the body, in front of the deck)
    for x0, x1 in ((592, 600), (470, 494)):
        p.append(f'<path d="M{x0},732 L{x1},658" stroke="{OUTLINE}" stroke-width="23" stroke-linecap="round" fill="none"/>')
    for x0, x1 in ((592, 600), (470, 494)):
        p.append(f'<path d="M{x0},732 L{x1},658" stroke="{LEGS}" stroke-width="13" stroke-linecap="round" fill="none"/>')
    for ax in (590, 468):
        foot = f"M{ax},724 L{ax+42},757 L{ax-30},757 Z"
        p.append(f'<path d="{foot}" fill="{LEGS}" stroke="{OUTLINE}" stroke-width="5" stroke-linejoin="round"/>')
    # ---- tail feathers
    for d in (
        "M404,506 L314,478 L400,528 Z",
        "M406,518 L304,510 L402,540 Z",
        "M404,532 L312,552 L398,544 Z",
    ):
        p.append(f'<path d="{d}" fill="{BODY}" stroke="{OUTLINE}" stroke-width="6" stroke-linejoin="round"/>')
    # ---- body + neck + head as one silhouette
    silhouette = (
        "M409,502 "
        "A150,110 0 0 1 626,465 "          # back arc over the body
        "C652,430 660,360 631,293 "        # back of the neck
        "A58,58 0 1 1 706,296 "            # head (clockwise over the top)
        "C692,340 678,410 652,482 "        # front of the neck
        "A150,110 0 1 1 391,545 "          # chest, belly, rear
        "Z"
    )
    p.append(f'<path d="{silhouette}" fill="{BODY}" stroke="{OUTLINE}" stroke-width="6" stroke-linejoin="round"/>')
    # ---- folded wing
    p.append(
        f'<ellipse cx="525" cy="550" rx="112" ry="76" transform="rotate(-18 525 550)" '
        f'fill="{WING}" stroke="{OUTLINE}" stroke-width="6"/>'
    )
    for d in ("M480,605 Q525,588 562,550", "M500,622 Q545,606 580,572"):
        p.append(f'<path d="{d}" fill="none" stroke="{WING_LINE}" stroke-width="8" stroke-linecap="round"/>')
    # ---- pouch (drawn under the upper mandible)
    pouch = (
        "M722,264 "
        "C744,330 800,362 862,360 "
        "C912,358 940,330 950,306 "
        "C868,290 790,274 722,264 Z"
    )
    p.append(f'<path d="{pouch}" fill="{POUCH}" stroke="{OUTLINE}" stroke-width="6" stroke-linejoin="round"/>')
    p.append(f'<path d="M752,296 C792,326 842,336 892,322" fill="none" stroke="{POUCH_HI}" stroke-width="6" stroke-linecap="round" opacity="0.85"/>')
    # ---- upper mandible
    beak = (
        "M706,226 "
        "C790,232 880,258 948,290 "
        "C958,294 960,302 950,306 "
        "C866,286 788,272 726,262 Z"
    )
    p.append(f'<path d="{beak}" fill="url(#beakGrad)" stroke="{OUTLINE}" stroke-width="6" stroke-linejoin="round"/>')
    p.append(f'<path d="M754,243 L780,250" stroke="{OUTLINE}" stroke-width="5" stroke-linecap="round"/>')
    # ---- helmet
    helmet = "M620,231 C623,172 641,149 671,146 C705,143 727,170 724,227 C694,238 652,239 620,231 Z"
    p.append(f'<path d="{helmet}" fill="{HELMET}" stroke="{OUTLINE}" stroke-width="6" stroke-linejoin="round"/>')
    p.append(f'<path d="M640,183 Q672,165 708,179" fill="none" stroke="{HELMET_STRIPE}" stroke-width="9" stroke-linecap="round"/>')
    for cx, cy in ((654, 167), (676, 160)):
        p.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{HELMET_DK}"/>')
    # ---- face
    p.append(f'<circle cx="692" cy="252" r="10.5" fill="{EYE}"/>')
    p.append('<circle cx="695" cy="248" r="3.5" fill="#ffffff"/>')
    p.append(f'<ellipse cx="682" cy="290" rx="11" ry="7" fill="{BLUSH}" opacity="0.55"/>')
    return "".join(p)


# ---------------------------------------------------------------- scene
def scene(t=None, smil=False):
    """t=None and smil=True -> animated master file; t in seconds -> video frame."""
    p = []

    # ---- sky
    p.append(f'<rect width="{W}" height="{H}" fill="url(#skyGrad)"/>')

    # ---- sun
    p.append(
        f'<circle cx="152" cy="128" r="104" fill="{SUN_GLOW}" opacity="0.18"/>'
        f'<circle cx="152" cy="128" r="80" fill="{SUN_GLOW}" opacity="0.35"/>'
        f'<circle cx="152" cy="128" r="56" fill="{SUN}" stroke="{SUN_EDGE}" stroke-width="6"/>'
    )

    # ---- clouds, hills, speckles: scroll with 512 px tiling
    clouds = tiled(cloud(392, 138, 1.0) + cloud(778, 206, 0.72) + cloud(64, 304, 0.55), 512)
    hills = tiled(
        f'<ellipse cx="240" cy="935" rx="260" ry="115" fill="{HILL_A}"/>'
        f'<ellipse cx="790" cy="945" rx="300" ry="135" fill="{HILL_B}"/>',
        512,
    )
    speckles = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SPECKLE}" opacity="0.8"/>'
        for cx, cy, r in ((150, 1000, 3), (330, 1012, 2.5), (470, 986, 2),
                          (700, 1004, 3), (860, 990, 2), (980, 1014, 2.5))
    )
    speckles = tiled(speckles, 512)

    # ---- road
    road = (
        f'<rect x="0" y="880" width="{W}" height="144" fill="url(#roadGrad)"/>'
        f'<path d="M0,880 L1024,880" stroke="{ROAD_EDGE}" stroke-width="6"/>'
    )

    # ---- lane dashes: 128 px tiling
    dashes = "".join(
        f'<rect x="{k*128}" y="946" width="72" height="13" rx="6.5" fill="{DASH}" opacity="0.85"/>'
        for k in range(-1, 10)
    )

    # ---- speed lines behind the rider: 256 px tiling
    lines = "".join(
        f'<path d="M{x0},{y} L{x1},{y}" stroke="#ffffff" stroke-width="{w}" stroke-linecap="round" opacity="0.7"/>'
        for y, x0, x1, w in ((468, 120, 300, 11), (540, 84, 236, 9), (612, 130, 296, 10))
        for x0, x1 in ((x0, x1), (x0 - 256, x1 - 256), (x0 + 256, x1 + 256))
    )

    # ---- dust puffs behind the rear wheel
    dust = []
    for i in range(3):
        if smil:
            begin = f'begin="{-i / 3.0 * 4 / 3:.4f}s"'
            dust.append(
                '<g>'
                '<circle r="7" fill="#ffffff">'
                '<animate attributeName="r" values="7;20" dur="1.3333s" ' + begin + ' repeatCount="indefinite"/>'
                '<animate attributeName="opacity" values="0.5;0" dur="1.3333s" ' + begin + ' repeatCount="indefinite"/>'
                '</circle>'
                '<animateTransform attributeName="transform" type="translate" '
                'values="310 856;240 832" dur="1.3333s" ' + begin + ' repeatCount="indefinite"/>'
                '</g>'
            )
        else:
            ph = (t * DUST_HZ + i / 3.0) % 1.0 if t is not None else i / 3.0
            x = 310 - 70 * ph
            y = 856 - 24 * ph
            r = 7 + 13 * ph
            op = 0.5 * (1 - ph)
            dust.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" fill="#ffffff" opacity="{n(op)}"/>')

    # ---- assemble scrolling groups
    def scroll_group(body, period, dur):
        if smil:
            return (
                f'<g><animateTransform attributeName="transform" type="translate" '
                f'from="0 0" to="{-period} 0" dur="{n(dur)}s" repeatCount="indefinite"/>{body}</g>'
            )
        off = -(SCROLL_SPEED * t) % period if t is not None else 0.0
        return f'<g transform="translate({n(off)} 0)">{body}</g>'

    p.append(scroll_group(clouds, 512, 512 / SCROLL_SPEED))
    p.append(scroll_group(hills, 512, 512 / SCROLL_SPEED))
    p.append(road)
    p.append(scroll_group(dashes, 128, 128 / SCROLL_SPEED))
    p.append(scroll_group(speckles, 512, 512 / SCROLL_SPEED))
    p.append('<ellipse cx="534" cy="892" rx="238" ry="11" fill="#16202b" opacity="0.22"/>')
    p.append(scroll_group(lines, 256, 256 / SCROLL_SPEED))
    p.extend(dust)

    # ---- rider bob / lean / wheels
    bob = 0.0
    lean = 0.0
    wheel_rot = 0.0
    whoosh_op = 0.45
    if t is not None:
        bob = 4.0 * math.sin(2 * math.pi * BOB_HZ * t)
        lean = 1.8 * math.sin(2 * math.pi * LEAN_HZ * t)
        wheel_rot = (WHEEL_DEG_S * t) % 360
        whoosh_op = 0.42 + 0.15 * math.sin(2 * math.pi * WHOOSH_HZ * t)

    board = skateboard()
    bird = pelican()

    if smil:
        board_g = (
            '<g><animateTransform attributeName="transform" type="translate" '
            'values="0 0;0 5;0 0" keyTimes="0;0.5;1" dur="0.6667s" repeatCount="indefinite"/>'
            + board + '</g>'
        )
        bird_g = (
            '<g><animateTransform attributeName="transform" type="rotate" '
            'values="0 560 700;1.8 560 700;0 560 700" keyTimes="0;0.5;1" dur="1.3333s" repeatCount="indefinite"/>'
            + bird + '</g>'
        )
        for x in (400, 668):
            board_g = board_g.replace(
                f'<g id="wheel{x}">',
                f'<g id="wheel{x}"><animateTransform attributeName="transform" type="rotate" '
                f'from="0 {x} 840" to="360 {x} 840" dur="2s" repeatCount="indefinite"/>',
            )
        whoosh = (
            '<g stroke="#ffffff" stroke-linecap="round" fill="none" opacity="0.45">'
            '<path d="M846,170 L960,158" stroke-width="8"/>'
            '<path d="M876,204 L985,195" stroke-width="7"/>'
            '<animate attributeName="opacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite"/>'
            '</g>'
        )
    else:
        board_g = f'<g transform="translate(0 {n(bob)})">{board}</g>'
        bird_g = (
            f'<g transform="translate(0 {n(bob)}) rotate({n(lean)} 560 700)">{bird}</g>'
        )
        # rotate wheel dots around their hubs
        for x in (400, 668):
            board_g = board_g.replace(
                f'<g id="wheel{x}">',
                f'<g id="wheel{x}" transform="rotate({n(wheel_rot)} {x} 840)">',
            )
        whoosh = (
            f'<g stroke="#ffffff" stroke-linecap="round" fill="none" opacity="{n(whoosh_op)}">'
            '<path d="M846,170 L960,158" stroke-width="8"/>'
            '<path d="M876,204 L985,195" stroke-width="7"/>'
            '</g>'
        )

    p.append(board_g)
    p.append(bird_g)
    p.append(whoosh)

    defs = (
        '<defs>'
        f'<linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{SKY_TOP}"/><stop offset="1" stop-color="{SKY_BOT}"/></linearGradient>'
        f'<linearGradient id="roadGrad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{ROAD_TOP}"/><stop offset="1" stop-color="{ROAD_BOT}"/></linearGradient>'
        f'<linearGradient id="beakGrad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BEAK_TOP}"/><stop offset="1" stop-color="{BEAK_BOT}"/></linearGradient>'
        '</defs>'
    )

    title = (
        "<title>Pelican riding a skateboard</title>"
        "<desc>A cartoon pelican in a red helmet cruises on a skateboard, "
        "big beak forward, dust trailing behind its rear wheel.</desc>"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">{title}{defs}' + "".join(p) + '</svg>\n'
    )


# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", metavar="OUT")
    ap.add_argument("--frame", nargs=2, metavar=("T", "OUT"))
    ap.add_argument("--frames", nargs=3, metavar=("DIR", "FPS", "COUNT"))
    ap.add_argument("--indent", action="store_true")
    args = ap.parse_args()

    if args.static:
        svg = scene(None, smil=True)
        os.makedirs(os.path.dirname(args.static) or ".", exist_ok=True)
        with open(args.static, "w") as f:
            f.write(svg)
        print(f"wrote {args.static} ({len(svg)} bytes)")
    if args.frame:
        t, out = float(args.frame[0]), args.frame[1]
        with open(out, "w") as f:
            f.write(scene(t))
        print(f"wrote {out}")
    if args.frames:
        d, fps, count = args.frames[0], float(args.frames[1]), int(args.frames[2])
        os.makedirs(d, exist_ok=True)
        for i in range(count):
            t = i / fps
            with open(os.path.join(d, f"frame_{i:04d}.svg"), "w") as f:
                f.write(scene(t))
        print(f"wrote {count} frames to {d} at {fps} fps")


if __name__ == "__main__":
    main()
