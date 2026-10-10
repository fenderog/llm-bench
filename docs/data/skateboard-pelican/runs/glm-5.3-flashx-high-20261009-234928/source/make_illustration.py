#!/usr/bin/env python3
"""
Pelican riding a skateboard - pure-stdlib renderer.

Renders the same scene as pelican-skateboard.svg into:
  - output/pelican-skateboard.png  (static frame)
  - output/pelican-skateboard.mp4  (5 s @ 20 fps, encoded with ffmpeg)

All drawing is done on a 2x-supersampled RGB bytearray, then box-downsampled
for antialiasing. Run:  python3 make_illustration.py
"""
import math
import os
import shutil
import struct
import subprocess
import zlib

SS = 2                # supersampling factor
W, H = 800, 600       # design / output size
SW, SH = W * SS, H * SS

# ---------------------------------------------------------------- primitives

def fill_rect(img, x0, y0, x1, y1, c):
    x0 = max(0, int(x0)); y0 = max(0, int(y0))
    x1 = min(SW, int(x1)); y1 = min(SH, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for y in range(y0, y1):
        b = (y * SW + x0) * 3
        img[b:b + len(row)] = row


def fill_circle(img, cx, cy, r, c):
    y0 = max(0, int(cy - r)); y1 = min(SH - 1, int(cy + r))
    r2 = r * r
    row = bytes(c) * SW
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        d2 = r2 - dy * dy
        if d2 <= 0:
            continue
        dx = math.sqrt(d2)
        a = max(0, int(cx - dx)); b = min(SW - 1, int(cx + dx))
        if b < a:
            continue
        base = (y * SW + a) * 3
        img[base:base + (b - a + 1) * 3] = row[:(b - a + 1) * 3]


def blend_circle(img, cx, cy, r, c, alpha):
    y0 = max(0, int(cy - r)); y1 = min(SH - 1, int(cy + r))
    x0 = max(0, int(cx - r)); x1 = min(SW - 1, int(cx + r))
    r2 = r * r
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            if dx * dx + dy * dy > r2:
                continue
            b = (y * SW + x) * 3
            img[b] = (img[b] + (c[0] - img[b]) * alpha).__int__()
            img[b + 1] = (img[b + 1] + (c[1] - img[b + 1]) * alpha).__int__()
            img[b + 2] = (img[b + 2] + (c[2] - img[b + 2]) * alpha).__int__()


def fill_ellipse(img, cx, cy, rx, ry, rot_deg, c):
    th = math.radians(rot_deg)
    co, si = math.cos(th), math.sin(th)
    x0 = max(0, int(cx - rx - ry)); x1 = min(SW - 1, int(cx + rx + ry))
    y0 = max(0, int(cy - rx - ry)); y1 = min(SH - 1, int(cy + rx + ry))
    for y in range(y0, y1 + 1):
        dy = y + 0.5 - cy
        base = (y * SW + x0) * 3
        for x in range(x0, x1 + 1):
            dx = x + 0.5 - cx
            u = dx * co + dy * si
            v = -dx * si + dy * co
            if (u * u) / (rx * rx) + (v * v) / (ry * ry) <= 1.0:
                b = base + (x - x0) * 3
                img[b:b + 3] = bytes(c)


def fill_poly(img, pts, c):
    n = len(pts)
    ys = [p[1] for p in pts]
    y0 = max(0, int(math.floor(min(ys)))); y1 = min(SH - 1, int(math.ceil(max(ys))))
    row = bytes(c) * SW
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            xa, ya = pts[i]; xb, yb = pts[(i + 1) % n]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            a = max(0, int(math.ceil(xs[i] - 0.5)))
            b = min(SW - 1, int(math.floor(xs[i + 1] - 0.5)))
            if b < a:
                continue
            base = (y * SW + a) * 3
            img[base:base + (b - a + 1) * 3] = row[:(b - a + 1) * 3]


def thick_seg(img, p0, p1, w, c):
    """Thick line segment as a quad."""
    x0, y0 = p0; x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    fill_poly(img, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                    (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)


def bez(p0, p1, p2, p3, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return x, y

# ------------------------------------------------------------------ scene

SKY_TOP = (110, 168, 232); SKY_BOT = (200, 230, 250)
GRASS = (111, 180, 90); ROAD_TOP = (96, 101, 112); ROAD_BOT = (76, 81, 91)
WHITE = (250, 251, 253); WING = (208, 214, 224); WING2 = (194, 201, 214)
ORANGE = (235, 140, 50); BEAK = (240, 150, 40); BEAK_D = (217, 127, 22)
POUCH = (252, 186, 86); DECK = (125, 70, 170); DECK_D = (109, 58, 146)
DECK_L = (154, 99, 196); TIRE = (60, 62, 70); HUBY = (250, 205, 70)
SPOKE = (168, 129, 31); TRUCK = (70, 75, 85); DARK = (42, 44, 56)


def build_background():
    img = bytearray(SW * SH * 3)
    # sky gradient (per-row fill)
    for y in range(SH):
        if y < 400 * SS:
            f = y / (400 * SS)
            c = tuple(int(a + (b - a) * f) for a, b in zip(SKY_TOP, SKY_BOT))
            fill_rect(img, 0, y, SW, y + 1, c)
        elif y < 430 * SS:
            fill_rect(img, 0, y, SW, y + 1, GRASS)
        else:
            f = (y - 430 * SS) / (SH - 430 * SS)
            c = tuple(int(a + (b - a) * f) for a, b in zip(ROAD_TOP, ROAD_BOT))
            fill_rect(img, 0, y, SW, y + 1, c)
    # sun + glow
    blend_circle(img, 690 * SS, 95 * SS, 85 * SS, (255, 233, 122), 0.45)
    fill_circle(img, 690 * SS, 95 * SS, 42 * SS, (255, 215, 90))
    # clouds (two copies for seamless wrap while drifting)
    for off in (0, 900):
        for cx, cy, rx, ry in [(170, 112, 58, 26), (128, 122, 40, 20),
                               (216, 122, 44, 20), (430, 78, 48, 22),
                               (398, 86, 32, 16), (466, 86, 34, 16),
                               (300, 200, 40, 18), (272, 207, 26, 13),
                               (330, 207, 28, 13)]:
            fill_ellipse(img, (cx + off) * SS, cy * SS, rx * SS, ry * SS, 0, (251, 253, 255))
    return img


def draw_shadow(img):
    fill_ellipse(img, 425 * SS, 512 * SS, 165 * SS, 11 * SS, 0, (72, 76, 86))


def draw_wheel(img, cx, cy, ang):
    cx, cy, r = cx * SS, cy * SS, 19 * SS
    fill_circle(img, cx, cy, r, TIRE)
    fill_circle(img, cx, cy, 14 * SS, HUBY)
    for k in range(3):
        a = ang + k * math.pi / 3
        thick_seg(img, (cx - math.cos(a) * 12 * SS, cy - math.sin(a) * 12 * SS),
                  (cx + math.cos(a) * 12 * SS, cy + math.sin(a) * 12 * SS),
                  3 * SS, SPOKE)
    fill_circle(img, cx, cy, 4 * SS, (90, 93, 102))


def draw_skateboard(img):
    s = SS
    fill_rect(img, 335 * s, 470 * s, 355 * s, 484 * s, TRUCK)
    fill_rect(img, 500 * s, 470 * s, 520 * s, 484 * s, TRUCK)
    fill_poly(img, [(545 * s, 462 * s), (572 * s, 446 * s),
                    (582 * s, 452 * s), (545 * s, 476 * s)], DECK_D)
    fill_poly(img, [(295 * s, 462 * s), (268 * s, 446 * s),
                    (258 * s, 452 * s), (295 * s, 476 * s)], DECK_D)
    fill_rect(img, 295 * s, 462 * s, 545 * s, 476 * s, DECK)
    fill_rect(img, 295 * s, 462 * s, 545 * s, 466 * s, DECK_L)


def draw_pelican(img, by):
    """by = vertical bob offset (design px)."""
    s = SS
    O = lambda x, y: (x * s, (y + by) * s)
    # legs (hips bob, feet stay planted)
    thick_seg(img, O(405, 375 + by), O(400, 425), 7, ORANGE)
    thick_seg(img, O(400, 425), O(412, 461), 7, ORANGE)
    thick_seg(img, O(455, 378 + by), O(452, 425), 7, ORANGE)
    thick_seg(img, O(452, 425), O(464, 461), 7, ORANGE)
    # feet
    fill_poly(img, [O(398, 463), O(434, 463), O(429, 452)], ORANGE)
    fill_poly(img, [O(450, 463), O(486, 463), O(481, 452)], ORANGE)
    # tail
    fill_poly(img, [O(352, 296), O(298, 250), O(322, 320)], WHITE)
    fill_poly(img, [O(352, 296), O(298, 250), O(310, 288)], (221, 227, 234))
    # body
    fill_ellipse(img, 430 * s, (330 + by) * s, 95 * s, 68 * s, 10, WHITE)
    # wing
    fill_poly(img, [O(390, 295), O(462, 318), O(438, 368), O(365, 342)], WING)
    fill_poly(img, [O(402, 306), O(452, 322), O(436, 356)], WING2)
    # neck (tapered bezier stamp)
    p0, p1, p2, p3 = O(488, 295), O(515, 260), O(530, 200), O(556, 185)
    steps = 36
    for i in range(steps + 1):
        t = i / steps
        x, y = bez(p0, p1, p2, p3, t)
        r = (26 - 11 * t) * s
        fill_circle(img, x, y, r, WHITE)
    # head
    fill_circle(img, 560 * s, (185 + by) * s, 25 * s, WHITE)
    # beak: pouch, upper beak, hook
    fill_poly(img, [O(578, 188), O(688, 209), O(648, 238), O(598, 222)], POUCH)
    fill_poly(img, [O(576, 170), O(704, 197), O(700, 207), O(576, 188)], BEAK)
    fill_poly(img, [O(700, 193), O(716, 204), O(702, 215)], BEAK_D)
    # eye
    fill_circle(img, 568 * s, (177 + by) * s, 5.5 * s, DARK)
    fill_circle(img, 570 * s, (175 + by) * s, 2 * s, (255, 255, 255))


def render_frame(bg, t):
    img = bytearray(bg)
    # scrolling lane dashes
    dash_w, gap, period = 70, 60, 130
    off = (t * 220) % period
    x = -off
    while x < W:
        fill_rect(img, x * SS, 536 * SS, (x + dash_w) * SS, 544 * SS, (232, 226, 200))
        x += period
    # speed lines (pulsing)
    for x0, wdt, y, ph in [(70, 95, 300, 0.0), (40, 130, 345, 0.5), (95, 80, 388, 0.25)]:
        a = 0.32 + 0.23 * math.sin(2 * math.pi * (t / 0.6 + ph))
        for yy in range(y * SS, (y + 7) * SS):
            b0 = (yy * SW + x0 * SS) * 3
            n = wdt * SS * 3
            seg = img[b0:b0 + n]
            img[b0:b0 + n] = bytes(int(seg[i] + (255 - seg[i]) * a) for i in range(n))
    draw_shadow(img)
    draw_skateboard(img)
    ang = (t * 220 / 18)  # wheel spin, matches ground speed
    draw_wheel(img, 345, 496, ang)
    draw_wheel(img, 510, 496, ang)
    by = 3.5 * math.sin(2 * math.pi * 1.3 * t)
    draw_pelican(img, by)
    return img


def downsample(img):
    out = bytearray(W * H * 3)
    for y in range(H):
        r0 = (2 * y) * SW * 3
        r1 = (2 * y + 1) * SW * 3
        ob = y * W * 3
        for x in range(W):
            i = r0 + x * 6
            j = r1 + x * 6
            out[ob] = (img[i] + img[i + 3] + img[j] + img[j + 3]) >> 2
            out[ob + 1] = (img[i + 1] + img[i + 4] + img[j + 1] + img[j + 4]) >> 2
            out[ob + 2] = (img[i + 2] + img[i + 5] + img[j + 2] + img[j + 5]) >> 2
            ob += 3
    return out


def write_png(path, rgb):
    raw = b"".join(b"\x00" + bytes(rgb[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)

# -------------------------------------------------------------------- main

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "output")
    os.makedirs(out, exist_ok=True)
    bg = build_background()

    # static PNG
    write_png(os.path.join(out, "pelican-skateboard.png"), downsample(render_frame(bg, 0.25)))
    print("wrote pelican-skateboard.png")

    # video frames
    fps, secs = 20, 5
    frames_dir = os.path.join(here, "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir)
    for i in range(fps * secs):
        f = os.path.join(frames_dir, "f%04d.png" % i)
        write_png(f, downsample(render_frame(bg, i / fps)))
        if i % 20 == 0:
            print("frame", i)
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "f%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
        "-movflags", "+faststart",
        os.path.join(out, "pelican-skateboard.mp4")], check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.rmtree(frames_dir)
    print("wrote pelican-skateboard.mp4")


if __name__ == "__main__":
    main()
