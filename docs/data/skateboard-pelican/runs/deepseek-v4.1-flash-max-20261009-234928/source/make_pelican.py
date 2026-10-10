#!/usr/bin/env python3
"""
Generate "Pelican on a Skateboard" artwork.

Pipeline:
  * build_svg(t)        -> SVG string for time t (seconds), 1280x720
  * --svg               -> write the static illustration SVG
  * --png               -> render a single high-res PNG (via macOS sips)
  * --frames            -> render every animation frame as PNG (via sips)
  * animated SVG        -> --animated-svg writes an SMIL self-animating SVG

Uses only the Python standard library + the system `sips` SVG renderer.
"""
import math
import os
import subprocess
import sys

W, H = 1280, 720
GROUND = 610.0          # top of the boardwalk
DURATION = 8.0          # seconds, seamless loop
FPS = 30

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def s(x):
    """compact number formatting"""
    if abs(x) < 1e-6:
        return "0"
    return ("%.2f" % x).rstrip("0").rstrip(".")


def wrap(v, period):
    return v - math.floor(v / period) * period


def smoothstep(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def tri(u):
    """0 -> 1 -> 0 over u in [0,1]"""
    u = max(0.0, min(1.0, u))
    return 4 * u * (1 - u)


# ----------------------------------------------------------------------------
# motion: returns a dict describing the pose at time t
# ----------------------------------------------------------------------------

def motion(t):
    m = {}
    # steady rolling bob / lean (period 0.5s, divides 8s)
    m["bob"] = 4.0 * math.sin(2 * math.pi * t / 0.5)
    m["lean"] = 1.1 * math.sin(2 * math.pi * t / 0.5 + 0.9)
    m["wheel"] = (t * 900.0) % 360.0            # 20 full turns in 8s
    m["ground"] = (t * 170.0) % 120.0           # boardwalk plank offset

    # scarf flutter
    m["scarf"] = 16 * math.sin(2 * math.pi * t / 0.5 + 0.4) + \
        7 * math.sin(2 * math.pi * t / 0.25)
    m["wing"] = 5 * math.sin(2 * math.pi * t / 0.5 + 1.7)

    # speed-line pulse
    m["speed"] = 0.55 + 0.45 * math.sin(2 * math.pi * t / 0.5)

    # ---- trick timeline -------------------------------------------------
    rider_y = 0.0
    board_y = 0.0
    flip = 0.0
    wheelie = 0.0
    tuck = 0.0
    crouch = 0.0

    # crouch before the kickflip
    if 2.00 <= t < 2.40:
        crouch = 11.0 * smoothstep((t - 2.00) / 0.40)

    # kickflip: 2.40 -> 3.70
    if 2.40 <= t < 3.70:
        u = (t - 2.40) / 1.30
        arc = math.sin(math.pi * u)
        board_y = -112 * arc
        rider_y = -124 * arc
        flip = 360.0 * smoothstep(u)
        tuck = 26 * arc

    # manual / wheelie: 5.30 -> 6.60
    if 5.30 <= t < 6.60:
        u = (t - 5.30) / 1.30
        wheelie = -15.0 * tri(u)
        tuck = 10 * tri(u)

    m["rider_y"] = rider_y + crouch
    m["board_y"] = board_y + crouch * 0.4
    m["flip"] = flip
    m["wheelie"] = wheelie
    m["tuck"] = tuck
    m["air"] = max(0.0, -board_y) / 128.0

    # shadow
    m["shadow_s"] = 1.0 - 0.55 * m["air"]
    m["shadow_o"] = 0.30 - 0.20 * m["air"]
    return m


# ----------------------------------------------------------------------------
# scene pieces
# ----------------------------------------------------------------------------

def defs():
    return """
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2f7fd6"/>
      <stop offset="0.45" stop-color="#79bdf0"/>
      <stop offset="0.78" stop-color="#cfeafb"/>
      <stop offset="1" stop-color="#f2fbff"/>
    </linearGradient>
    <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2e86c1"/>
      <stop offset="0.5" stop-color="#3f9fd0"/>
      <stop offset="1" stop-color="#6cc0e0"/>
    </linearGradient>
    <linearGradient id="sand" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f3dba6"/>
      <stop offset="1" stop-color="#e3bd77"/>
    </linearGradient>
    <linearGradient id="wood" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#c98f52"/>
      <stop offset="0.12" stop-color="#b77c42"/>
      <stop offset="1" stop-color="#8d5a2b"/>
    </linearGradient>
    <linearGradient id="deck" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f7d9a8"/>
      <stop offset="0.5" stop-color="#e4b878"/>
      <stop offset="1" stop-color="#c08a4c"/>
    </linearGradient>
    <linearGradient id="body" x1="0.2" y1="0" x2="0.8" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="0.62" stop-color="#f4f6f8"/>
      <stop offset="1" stop-color="#d7dee4"/>
    </linearGradient>
    <linearGradient id="beak" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffc14d"/>
      <stop offset="1" stop-color="#ef8b1e"/>
    </linearGradient>
    <linearGradient id="pouch" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffcf70"/>
      <stop offset="1" stop-color="#f0a030"/>
    </linearGradient>
    <radialGradient id="sun" cx="0.5" cy="0.45" r="0.55">
      <stop offset="0" stop-color="#fffbdc"/>
      <stop offset="0.6" stop-color="#ffe473"/>
      <stop offset="1" stop-color="#ffc42e"/>
    </radialGradient>
    <radialGradient id="sunglow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fff6c0" stop-opacity="0.9"/>
      <stop offset="1" stop-color="#fff6c0" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="hill1" cx="0.5" cy="1" r="1">
      <stop offset="0" stop-color="#8fce6a"/>
      <stop offset="1" stop-color="#4e9c46"/>
    </radialGradient>
    <radialGradient id="hill2" cx="0.5" cy="1" r="1">
      <stop offset="0" stop-color="#77bd58"/>
      <stop offset="1" stop-color="#3d8a3a"/>
    </radialGradient>
    <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="7"/>
    </filter>
    <filter id="soft2" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.2"/>
    </filter>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="10"/>
    </filter>
  </defs>"""


def sky():
    return f'  <rect x="0" y="0" width="{W}" height="{H}" fill="url(#sky)"/>'


def sun():
    return """
  <g>
    <circle cx="1082" cy="124" r="150" fill="url(#sunglow)" filter="url(#glow)"/>
    <circle cx="1082" cy="124" r="62" fill="url(#sun)"/>
    <circle cx="1082" cy="124" r="62" fill="none" stroke="#fff3b0" stroke-width="2" opacity="0.7"/>
  </g>"""


def cloud(x, y, sc, op=0.95):
    return f"""
  <g transform="translate({s(x)} {s(y)}) scale({s(sc)})" opacity="{s(op)}">
    <ellipse cx="0" cy="0" rx="78" ry="30" fill="#ffffff"/>
    <ellipse cx="62" cy="8" rx="58" ry="24" fill="#ffffff"/>
    <ellipse cx="-58" cy="10" rx="52" ry="22" fill="#ffffff"/>
    <ellipse cx="14" cy="-20" rx="46" ry="26" fill="#ffffff"/>
    <ellipse cx="0" cy="16" rx="92" ry="16" fill="#dfeaf3" opacity="0.55"/>
  </g>"""


def clouds(t):
    out = []
    specs = [(-120, 120, 1.15), (300, 70, 0.8), (720, 150, 1.0), (1040, 60, 0.7)]
    for i, (bx, y, sc) in enumerate(specs):
        speed = 26 + i * 6
        period = W + 360
        x = wrap(bx - t * speed, period) - 180
        out.append(cloud(x, y, sc, 0.9))
    return "\n".join(out)


def sailboat(x, y, sc=1.0):
    return f"""
  <g transform="translate({s(x)} {s(y)}) scale({s(sc)})" opacity="0.95">
    <path d="M0 0 L0 -46 Q26 -34 0 -4 Z" fill="#ffffff" stroke="#c8d3dc" stroke-width="2"/>
    <path d="M4 0 L4 -40 Q24 -28 4 -6 Z" fill="#f0f4f7"/>
    <path d="M-26 2 L30 2 L22 12 L-18 12 Z" fill="#e05a44" stroke="#b03f2e" stroke-width="2"/>
    <rect x="-2" y="-46" width="3" height="48" fill="#6b7480"/>
  </g>"""


def gulls():
    return """
  <g fill="none" stroke="#4a5b6b" stroke-width="3" stroke-linecap="round" opacity="0.75">
    <path d="M430 190 Q442 178 454 190 Q466 178 478 190"/>
    <path d="M520 232 Q528 224 536 232 Q544 224 552 232"/>
    <path d="M360 250 Q367 243 374 250 Q381 243 388 250"/>
  </g>"""


def sea_and_hills():
    return """
  <g>
    <rect x="0" y="418" width="1280" height="150" fill="url(#sea)"/>
    <g stroke="#bfe6f5" stroke-width="3" stroke-linecap="round" opacity="0.55">
      <line x1="80" y1="452" x2="210" y2="452"/>
      <line x1="330" y1="440" x2="470" y2="440"/>
      <line x1="560" y1="462" x2="690" y2="462"/>
      <line x1="820" y1="446" x2="960" y2="446"/>
      <line x1="1060" y1="460" x2="1190" y2="460"/>
      <line x1="180" y1="486" x2="300" y2="486"/>
      <line x1="640" y1="492" x2="780" y2="492"/>
      <line x1="980" y1="488" x2="1120" y2="488"/>
    </g>
    <path d="M0 520 Q140 448 300 512 Q420 560 560 520 L560 580 L0 580 Z" fill="url(#hill1)" opacity="0.95"/>
    <path d="M430 530 Q600 440 800 522 Q960 588 1280 520 L1280 600 L430 600 Z" fill="url(#hill2)" opacity="0.95"/>
    <path d="M0 560 Q120 524 220 556 L220 600 L0 600 Z" fill="#3d8a3a" opacity="0.5"/>
  </g>"""


def lighthouse():
    return """
  <g transform="translate(196 372)">
    <path d="M-16 70 L16 70 L11 -30 L-11 -30 Z" fill="#f4f1ea" stroke="#c9bfae" stroke-width="2"/>
    <path d="M-14 34 L14 34 L12 12 L-12 12 Z" fill="#e04b3a"/>
    <path d="M-12 -8 L12 -8 L10 -28 L-10 -28 Z" fill="#e04b3a"/>
    <rect x="-15" y="-44" width="30" height="16" rx="3" fill="#5b6470"/>
    <path d="M-19 -44 L19 -44 L0 -66 Z" fill="#e04b3a"/>
    <circle cx="0" cy="-38" r="6" fill="#ffe27a"/>
  </g>"""


def grass(x, y, sc, flip=False):
    f = -1 if flip else 1
    return f"""
  <g transform="translate({s(x)} {s(y)}) scale({s(sc*f)} {s(sc)})" fill="#4b8f3a" opacity="0.9">
    <path d="M0 0 Q-6 -26 -18 -40 Q-4 -28 2 0 Z"/>
    <path d="M4 0 Q6 -30 0 -48 Q10 -28 10 0 Z"/>
    <path d="M8 0 Q16 -24 26 -36 Q16 -20 14 0 Z"/>
  </g>"""


def beach():
    return """
  <g>
    <path d="M0 560 Q320 536 640 566 Q960 596 1280 560 L1280 620 L0 620 Z" fill="url(#sand)"/>
    <path d="M0 560 Q320 536 640 566 Q960 596 1280 560 L1280 572 Q960 608 640 578 Q320 548 0 572 Z" fill="#f7e7be" opacity="0.8"/>
""" + lighthouse() + grass(80, 566, 1.15) + grass(300, 558, 0.9, True) + grass(470, 566, 1.0) + grass(1120, 562, 1.0, True) + """
  </g>"""


def boardwalk(t, offset):
    out = [f'  <g>']
    out.append(f'    <rect x="0" y="{s(GROUND)}" width="{W}" height="{s(H-GROUND)}" fill="url(#wood)"/>')
    # horizontal plank grain lines
    out.append('    <g stroke="#a06a34" stroke-width="2" opacity="0.5">')
    for y in (628, 648, 668, 690, 710):
        out.append(f'      <line x1="0" y1="{y}" x2="{W}" y2="{y}"/>')
    out.append('    </g>')
    # vertical plank seams (move left)
    out.append('    <g stroke="#6f4517" stroke-width="3">')
    period = 120.0
    k = -1
    while True:
        x = offset + k * period
        if x > W + period:
            break
        if x > -period - 5:
            out.append(f'      <line x1="{s(x)}" y1="{s(GROUND)}" x2="{s(x-6)}" y2="{s(H)}"/>')
        k += 1
    out.append('    </g>')
    # bevel highlights next to seams
    out.append('    <g stroke="#e0ad6b" stroke-width="2" opacity="0.7">')
    k = -1
    while True:
        x = offset + k * period
        if x > W + period:
            break
        if x > -period - 5:
            out.append(f'      <line x1="{s(x+5)}" y1="{s(GROUND)}" x2="{s(x-1)}" y2="{s(H)}"/>')
        k += 1
    out.append('    </g>')
    # front edge lip
    out.append(f'    <rect x="0" y="{s(GROUND-8)}" width="{W}" height="10" fill="#d69a58"/>')
    out.append(f'    <rect x="0" y="{s(GROUND-8)}" width="{W}" height="3" fill="#f0c58c" opacity="0.8"/>')
    out.append('  </g>')
    return "\n".join(out)


def boardwalk_railing():
    # simple railing along the far edge of the boardwalk
    return """
  <g opacity="0.9">
    <rect x="0" y="566" width="1280" height="7" rx="3" fill="#a9784a"/>
    <rect x="0" y="566" width="1280" height="2.5" fill="#d3a56e"/>
  </g>"""


def speed_lines(m):
    o = m["speed"]
    out = ['  <g stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity="%.2f">' % (0.75 * o)]
    ys = [470, 500, 520, 480]
    xs = [300, 350, 250, 210]
    for x, y in zip(xs, ys):
        out.append(f'    <line x1="{x}" y1="{y}" x2="{x+86}" y2="{y}"/>')
    out.append('  </g>')
    out.append('  <g stroke="#cfeaff" stroke-width="5" stroke-linecap="round" opacity="%.2f">' % (0.6 * o))
    for x, y in zip([360, 420, 300], [545, 555, 565]):
        out.append(f'    <line x1="{x}" y1="{y}" x2="{x+64}" y2="{y}"/>')
    out.append('  </g>')
    return "\n".join(out)


# geometry of the board
BCX, BCY = 612.0, 566.0     # board centre
REAR_WX, FRONT_WX = 548.0, 678.0
WHEEL_Y = 590.0
WHEEL_R = 20.0


def wheel(cx, angle):
    return f"""
    <g transform="translate({s(cx)} {s(WHEEL_Y)}) rotate({s(angle)})">
      <circle cx="0" cy="0" r="{s(WHEEL_R)}" fill="#3a3f45"/>
      <circle cx="0" cy="0" r="{s(WHEEL_R-3)}" fill="#f2f2f0"/>
      <circle cx="0" cy="0" r="{s(WHEEL_R-8)}" fill="#e2e2de"/>
      <g stroke="#b9b9b3" stroke-width="2.4" stroke-linecap="round">
        <line x1="0" y1="0" x2="0" y2="-11"/>
        <line x1="0" y1="0" x2="9.5" y2="5.5"/>
        <line x1="0" y1="0" x2="-9.5" y2="5.5"/>
      </g>
      <circle cx="0" cy="0" r="4.4" fill="#f39a2b"/>
      <circle cx="0" cy="0" r="2" fill="#7a4a12"/>
    </g>"""


def skateboard(m):
    flip = m["flip"]
    bx, by = BCX, BCY
    return f"""
  <g transform="translate(0 {s(m['board_y'])})">
    <g transform="rotate({s(flip)} {s(bx)} {s(by)})">
      <!-- trucks -->
      <g fill="#8f99a6" stroke="#5c6570" stroke-width="2">
        <path d="M{ s(REAR_WX-14) } 566 L{ s(REAR_WX+14) } 566 L{ s(REAR_WX+8) } 582 L{ s(REAR_WX-8) } 582 Z"/>
        <path d="M{ s(FRONT_WX-14) } 566 L{ s(FRONT_WX+14) } 566 L{ s(FRONT_WX+8) } 582 L{ s(FRONT_WX-8) } 582 Z"/>
      </g>
      <!-- wheels -->
      {wheel(REAR_WX, m['wheel'])}
      {wheel(FRONT_WX, m['wheel'])}
      <!-- deck -->
      <path d="M520 561 Q508 561 506 552 Q506 544 518 544 L702 544 Q714 544 714 552 Q712 561 700 561 Z"
            fill="url(#deck)" stroke="#8f6132" stroke-width="2"/>
      <path d="M518 544 L702 544 Q714 544 714 552 L706 552 Q706 547 700 547 L520 547 Q514 547 514 552 L506 552 Q506 544 518 544 Z"
            fill="#2f3439"/>
      <!-- lightning sticker -->
      <g transform="translate(560 552)">
        <path d="M0 0 L14 0 L6 6 L16 6 L-2 16 L4 8 L-6 8 Z" fill="#ffd23f" stroke="#c99a12" stroke-width="1"/>
      </g>
      <!-- feet contact shadow on the deck -->
      <ellipse cx="616" cy="545" rx="58" ry="5" fill="#5b3a13" opacity="0.25"/>
      <!-- pelican foot grip strip -->
      <rect x="556" y="545" width="112" height="4" rx="2" fill="#3a3f45" opacity="0.35"/>
      <circle cx="700" cy="553" r="2.4" fill="#6d4a24"/>
    </g>
  </g>"""


def shadow(m):
    return f"""
  <ellipse cx="{s(BCX)}" cy="{s(GROUND-4)}" rx="{s(112*m['shadow_s'])}" ry="{s(13*m['shadow_s'])}"
           fill="#2a1a08" opacity="{s(m['shadow_o'])}" filter="url(#soft)"/>"""


def pelican(m):
    wy = m["rider_y"]
    tuck = m["tuck"]
    scarf = m["scarf"]
    wing = m["wing"]
    # leg / foot positions (feet sit on the deck top at y=544, tuck up in flight)
    rear_foot_y = 544 - tuck * 0.55
    front_foot_y = 544 - tuck * 0.55
    rear_foot_x = 584 + tuck * 0.30
    front_foot_x = 646 + tuck * 0.22
    return f"""
  <g transform="translate(0 {s(wy)})">
    <!-- legs -->
    <g>
      <path d="M606 498 Q584 522 584 {s(rear_foot_y-6)} L{ s(rear_foot_x) } {s(rear_foot_y)}"
            fill="none" stroke="#e8891f" stroke-width="10" stroke-linecap="round"/>
      <path d="M{ s(rear_foot_x-16) } {s(rear_foot_y)} L{ s(rear_foot_x+13) } {s(rear_foot_y)}"
            fill="none" stroke="#e8891f" stroke-width="8" stroke-linecap="round"/>
      <path d="M634 502 Q650 522 648 {s(front_foot_y-6)} L{ s(front_foot_x) } {s(front_foot_y)}"
            fill="none" stroke="#d97c16" stroke-width="10" stroke-linecap="round"/>
      <path d="M{ s(front_foot_x-16) } {s(front_foot_y)} L{ s(front_foot_x+13) } {s(front_foot_y)}"
            fill="none" stroke="#d97c16" stroke-width="8" stroke-linecap="round"/>
      <!-- webbed toes -->
      <path d="M{ s(rear_foot_x+13) } {s(rear_foot_y)} L{ s(rear_foot_x+4) } {s(rear_foot_y+7)} L{ s(rear_foot_x-10) } {s(rear_foot_y+6)} Z"
            fill="#e8891f"/>
      <path d="M{ s(front_foot_x+13) } {s(front_foot_y)} L{ s(front_foot_x+4) } {s(front_foot_y+7)} L{ s(front_foot_x-10) } {s(front_foot_y+6)} Z"
            fill="#d97c16"/>
    </g>
    <!-- tail feathers -->
    <path d="M540 452 Q492 430 462 446 Q498 462 490 484 Q520 474 546 494 Z"
          fill="#e7edf2" stroke="#b9c4cd" stroke-width="2.5"/>
    <path d="M544 470 Q508 468 486 486 Q518 488 530 502 Q540 486 552 500 Z"
          fill="#dfe7ee" stroke="#b9c4cd" stroke-width="2"/>
    <!-- far wing (sliver behind body) -->
    <path d="M632 400 Q648 434 630 470 Q616 440 614 408 Z" fill="#d5dee6"/>
    <!-- body -->
    <path d="M668 406
             C 646 372 570 366 532 406
             C 502 438 500 476 522 500
             C 556 534 642 534 682 498
             C 706 474 700 430 668 406 Z"
          fill="url(#body)" stroke="#c3ccd4" stroke-width="2.5"/>
    <!-- chest shading -->
    <path d="M648 508 C 606 520 560 512 534 486 C 566 500 614 502 648 508 Z"
          fill="#dbe3ea" opacity="0.8"/>
    <!-- near wing (folded, tip toward the tail) -->
    <g transform="rotate({s(wing*0.4)} 648 428)">
      <path d="M652 412
               C 704 430 698 492 642 512
               C 592 526 540 512 512 488
               C 556 482 596 470 616 444
               C 628 428 636 416 652 412 Z"
            fill="#eef2f5" stroke="#bcc6cf" stroke-width="2.5"/>
      <g fill="none" stroke="#aeb9c4" stroke-width="2" opacity="0.95">
        <path d="M636 442 Q606 458 566 466"/>
        <path d="M646 462 Q612 480 566 486"/>
        <path d="M648 486 Q620 500 578 506"/>
      </g>
      <path d="M512 488 C 552 486 592 478 616 460" fill="none" stroke="#9fabB7" stroke-width="2"/>
      <path d="M652 412 C 704 430 698 492 642 512 C 592 526 540 512 512 488 C 560 500 610 498 640 476 C 664 458 668 434 652 412 Z"
            fill="#dde6ed" opacity="0.55"/>
    </g>
    <!-- neck -->
    <path d="M652 420
             C 688 398 706 362 708 318
             L 744 322
             C 738 372 716 422 684 456
             C 668 456 656 442 652 420 Z"
          fill="url(#body)" stroke="#c3ccd4" stroke-width="2.5"/>
    <path d="M676 430 C 700 404 712 372 714 336" fill="none" stroke="#dbe3ea" stroke-width="3" opacity="0.8"/>
    <!-- head -->
    <g>
      <circle cx="736" cy="296" r="31" fill="url(#body)" stroke="#c3ccd4" stroke-width="2.5"/>
      <!-- beak upper mandible -->
      <path d="M756 282 Q844 280 906 314 Q852 322 802 312 Q770 304 754 294 Z"
            fill="url(#beak)" stroke="#c96f12" stroke-width="2.5"/>
      <path d="M770 292 Q830 300 892 314" fill="none" stroke="#d9871f" stroke-width="1.6" opacity="0.7"/>
      <!-- pouch -->
      <path d="M756 296 Q786 344 828 356 Q860 360 868 324 Q826 312 788 294 Z"
            fill="url(#pouch)" stroke="#c96f12" stroke-width="2.5"/>
      <path d="M776 304 Q808 336 846 346" fill="none" stroke="#d9871f" stroke-width="1.6" opacity="0.6"/>
      <path d="M800 300 Q828 322 856 330" fill="none" stroke="#c96f12" stroke-width="1.6" opacity="0.5"/>
      <!-- eye -->
      <circle cx="748" cy="280" r="9" fill="#ffffff" stroke="#a9b4bd" stroke-width="1.5"/>
      <circle cx="752" cy="280" r="4.6" fill="#2c2c2c"/>
      <circle cx="754" cy="278" r="1.5" fill="#ffffff"/>
      <!-- helmet -->
      <path d="M702 282 Q706 244 738 240 Q772 238 786 270 Q774 262 760 262 Q730 262 716 284 Z"
            fill="#e8453c" stroke="#b32a24" stroke-width="2.5"/>
      <path d="M704 280 Q748 262 788 270 L790 278 Q750 271 708 290 Z" fill="#f4f6f8"/>
      <path d="M738 240 Q741 252 739 262" fill="none" stroke="#b32a24" stroke-width="2"/>
      <rect x="696" y="280" width="26" height="6" rx="3" fill="#e8453c" stroke="#b32a24" stroke-width="1.5"/>
      <circle cx="722" cy="250" r="3.5" fill="#f4f6f8" opacity="0.6"/>
      <!-- crest feathers under the helmet -->
      <path d="M712 268 Q698 262 692 270 Q702 272 706 278 Z" fill="#eef2f5" stroke="#c3ccd4" stroke-width="1.5"/>
      <path d="M710 276 Q694 274 688 282 Q700 282 704 288 Z" fill="#eef2f5" stroke="#c3ccd4" stroke-width="1.5"/>
    </g>
    <!-- scarf around the neck -->
    <g>
      <path d="M668 346 Q698 334 728 342 Q736 360 724 370 Q698 358 672 374 Z"
            fill="#17a2b8" stroke="#0d7a8a" stroke-width="2.2"/>
      <path d="M672 348 Q700 337 726 345" fill="none" stroke="#7fe0ee" stroke-width="2.2" opacity="0.85"/>
      <g transform="rotate({s(scarf)} 682 366)">
        <path d="M686 358 Q624 344 574 372 Q616 386 606 412 Q654 392 692 392 Z"
              fill="#17a2b8" stroke="#0d7a8a" stroke-width="2.2"/>
        <path d="M682 364 Q632 358 592 380" fill="none" stroke="#7fe0ee" stroke-width="2.2" opacity="0.8"/>
        <path d="M690 384 Q656 388 626 404" fill="none" stroke="#0d7a8a" stroke-width="1.6" opacity="0.5"/>
        <circle cx="686" cy="366" r="8" fill="#17a2b8" stroke="#0d7a8a" stroke-width="2.2"/>
      </g>
    </g>
  </g>"""


def scene(t, static_extra=""):
    m = motion(t)
    off = m["ground"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>A pelican riding a skateboard along a seaside boardwalk</title>
  <desc>Cartoon side view of a white pelican with an orange beak, red helmet and blue scarf,
  balancing on a wooden skateboard on a sunny coastal boardwalk by the sea.</desc>
{defs()}
{sky()}
{sun()}
{clouds(t)}
{gulls()}
{sea_and_hills()}
{sailboat(258, 486, 0.9)}
{beach()}
{boardwalk(t, off)}
{boardwalk_railing()}
{speed_lines(m)}
{shadow(m)}
  <g transform="rotate({s(m['wheelie'])} {s(REAR_WX)} {s(GROUND)})">
{skateboard(m)}
{pelican(m)}
  </g>
{static_extra}
</svg>
"""


# ----------------------------------------------------------------------------
# rendering helpers
# ----------------------------------------------------------------------------

def render_png(svg_text, out_png, width=None):
    tmp = out_png + ".tmp.svg"
    with open(tmp, "w") as f:
        f.write(svg_text)
    cmd = ["sips", "-s", "format", "png", tmp, "--out", out_png]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    os.remove(tmp)
    if r.returncode != 0 or not os.path.exists(out_png):
        sys.stderr.write(r.stderr.decode() + "\n")
        raise SystemExit("sips failed for " + out_png)
    return out_png


def main():
    args = sys.argv[1:]
    mode = args[0] if args else "--png"
    if mode == "--svg":
        out = args[1] if len(args) > 1 else "pelican-skateboard.svg"
        t = float(args[2]) if len(args) > 2 else 0.0
        with open(out, "w") as f:
            f.write(scene(t))
        print("wrote", out)
    elif mode == "--png":
        out = args[1] if len(args) > 1 else "pelican-skateboard.png"
        t = float(args[2]) if len(args) > 2 else 0.0
        scale = float(args[3]) if len(args) > 3 else 1.0
        svg = scene(t)
        if scale != 1.0:
            # upscale intrinsic size for a crisp render
            svg = svg.replace(f'width="{W}" height="{H}"',
                              f'width="{int(W*scale)}" height="{int(H*scale)}"', 1)
        render_png(svg, out)
        print("wrote", out)
    elif mode == "--frames":
        outdir = args[1] if len(args) > 1 else "frames"
        os.makedirs(outdir, exist_ok=True)
        n = int(round(DURATION * FPS))
        for i in range(n):
            t = i / FPS
            render_png(scene(t), os.path.join(outdir, "f_%04d.png" % i))
            if i % 20 == 0:
                print("frame", i)
        print("wrote", n, "frames to", outdir)
    else:
        raise SystemExit("unknown mode " + mode)


if __name__ == "__main__":
    main()
