#!/usr/bin/env python3
"""Pelican riding a skateboard - SVG + PNG + MP4 renderer (stdlib only + ffmpeg).

The scene is described once as vector ops (Canvas) and exported to:
  - output/pelican_skateboard.svg  (vector)
  - output/pelican_skateboard.png  (rasterized at 2x supersampling)
  - output/pelican_skateboard.mp4  (3s looping animation, piped to ffmpeg)
"""
import math, zlib, struct, subprocess, sys

W, H = 960, 640
S = 2  # supersampling factor (must be 2)

# ----------------------------------------------------------------------------- Canvas

class Canvas:
    def __init__(self):
        self.ops = []
    def grad(self, x, y, w, h, c1, c2):
        self.ops.append(("grad", x, y, w, h, c1, c2))
    def poly(self, pts, color):
        self.ops.append(("poly", pts, color))
    def rect(self, x, y, w, h, color):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color)
    def circle(self, cx, cy, r, color):
        self.ops.append(("circle", cx, cy, r, color))
    def ellipse(self, cx, cy, rx, ry, rot_deg, color):
        self.ops.append(("ellipse", cx, cy, rx, ry, rot_deg, color))
    def stroke(self, pts, width, color):
        self.ops.append(("stroke", pts, width, color))

def rgba(c):
    return (c[0], c[1], c[2], c[3] if len(c) > 3 else 255)

def ellipse_pts(cx, cy, rx, ry, rot_deg=0, n=72):
    a = math.radians(rot_deg)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        x, y = rx * math.cos(th), ry * math.sin(th)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts

# ----------------------------------------------------------------------------- Rasterizer

def rasterize(cv, W, H, S):
    BW, BH = W * S, H * S
    buf = bytearray(BW * BH * 3)

    def fill_poly(pts, color):
        r, g, b, a = rgba(color)
        xs = [p[0] * S for p in pts]; ys = [p[1] * S for p in pts]
        y0 = max(0, int(min(ys))); y1 = min(BH - 1, int(max(ys)))
        x0 = max(0, int(min(xs))); x1 = min(BW - 1, int(max(xs)))
        if x1 < x0 or y1 < y0: return
        sp = [(x * S, y * S) for x, y in pts]
        n = len(sp)
        opaque = a >= 255
        seg_color = bytes((r, g, b))
        af = a / 255.0; ia = 1 - af
        for sy in range(y0, y1 + 1):
            yc = sy + 0.5
            xints = []
            for i in range(n):
                ax, ay = sp[i]; bx, by = sp[(i + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    xints.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            if len(xints) < 2: continue
            xints.sort()
            rowbase = sy * BW * 3
            for j in range(0, len(xints) - 1, 2):
                sx0 = max(x0, math.ceil(xints[j] - 0.5))
                sx1 = min(x1, math.floor(xints[j + 1] - 0.5))
                if sx1 < sx0: continue
                st = rowbase + sx0 * 3
                cnt = sx1 - sx0 + 1
                if opaque:
                    buf[st:st + cnt * 3] = seg_color * cnt
                else:
                    for sx in range(sx0, sx1 + 1):
                        idx = rowbase + sx * 3
                        buf[idx] = int(r * af + buf[idx] * ia)
                        buf[idx + 1] = int(g * af + buf[idx + 1] * ia)
                        buf[idx + 2] = int(b * af + buf[idx + 2] * ia)

    for op in cv.ops:
        kind = op[0]
        if kind == "grad":
            _, x, y, w, h, c1, c2 = op
            sy0 = max(0, int(y * S)); sy1 = min(BH - 1, int((y + h) * S) - 1)
            for sy in range(sy0, sy1 + 1):
                t = ((sy + 0.5) / S - y) / h
                t = min(1.0, max(0.0, t))
                col = bytes((int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
                xa = max(0, int(x * S)); xb = min(BW, int((x + w) * S))
                st = sy * BW * 3 + xa * 3
                buf[st:st + (xb - xa) * 3] = col * (xb - xa)
        elif kind == "poly":
            fill_poly(op[1], op[2])
        elif kind == "circle":
            _, cx, cy, r, color = op
            fill_poly(ellipse_pts(cx, cy, r, r), color)
        elif kind == "ellipse":
            _, cx, cy, rx, ry, rot, color = op
            fill_poly(ellipse_pts(cx, cy, rx, ry, rot), color)
        elif kind == "stroke":
            _, pts, width, color = op
            r = width / 2.0
            seg = ellipse_pts(0, 0, r, r, 0, 24)
            # walk the polyline, stamping circles
            for i in range(len(pts) - 1):
                ax, ay = pts[i]; bx, by = pts[i + 1]
                L = math.hypot(bx - ax, by - ay)
                steps = max(1, int(L / max(0.5, r / 2)))
                for k in range(steps + 1):
                    t = k / steps
                    cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
                    fill_poly([(cx + px, cy + py) for px, py in seg], color)
    return buf

def downsample(buf, W, H, S):
    BW = W * S
    out = bytearray(W * H * 3)
    for ty in range(H):
        r0 = buf[(ty * S) * BW * 3:(ty * S + 1) * BW * 3]
        r1 = buf[(ty * S + 1) * BW * 3:(ty * S + 2) * BW * 3]
        orow = bytearray(W * 3)
        for c in range(3):
            a = r0[c::3]; b = r1[c::3]
            vals = bytes(((a[0::2][i] + a[1::2][i] + b[0::2][i] + b[1::2][i]) >> 2) for i in range(W))
            orow[c::3] = vals
        out[ty * W * 3:(ty + 1) * W * 3] = orow
    return bytes(out)

def render_rgb(cv, W, H, S):
    return downsample(rasterize(cv, W, H, S), W, H, S)

# ----------------------------------------------------------------------------- PNG

def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + rgb[i * w * 3:(i + 1) * w * 3] for i in range(h))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)

# ----------------------------------------------------------------------------- SVG

def css(c):
    return "rgb(%d,%d,%d)" % (c[0], c[1], c[2])

def opacity_attr(c):
    a = c[3] if len(c) > 3 else 255
    return "" if a >= 255 else ' opacity="%.3f"' % (a / 255)

def to_svg(cv, W, H):
    defs = []
    body = []
    gid = 0
    for op in cv.ops:
        kind = op[0]
        if kind == "grad":
            _, x, y, w, h, c1, c2 = op
            gid += 1
            defs.append(
                '<linearGradient id="g%d" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
                % (gid, css(c1), css(c2)))
            body.append('<rect x="%g" y="%g" width="%g" height="%g" fill="url(#g%d)"/>' % (x, y, w, h, gid))
        elif kind == "poly":
            _, pts, color = op
            d = "M" + "L".join("%.2f %.2f" % p for p in pts) + "Z"
            body.append('<path d="%s" fill="%s"%s/>' % (d, css(color), opacity_attr(color)))
        elif kind == "circle":
            _, cx, cy, r, color = op
            body.append('<circle cx="%g" cy="%g" r="%g" fill="%s"%s/>' % (cx, cy, r, css(color), opacity_attr(color)))
        elif kind == "ellipse":
            _, cx, cy, rx, ry, rot, color = op
            body.append('<ellipse cx="%g" cy="%g" rx="%g" ry="%g" transform="rotate(%g %g %g)" fill="%s"%s/>'
                        % (cx, cy, rx, ry, rot, cx, cy, css(color), opacity_attr(color)))
        elif kind == "stroke":
            _, pts, width, color = op
            d = "M" + "L".join("%.2f %.2f" % p for p in pts)
            body.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g" stroke-linecap="round" stroke-linejoin="round"%s/>'
                        % (d, css(color), width, opacity_attr(color)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
            '<defs>%s</defs>\n%s\n</svg>\n' % (W, H, W, H, "".join(defs), "\n".join(body)))

# ----------------------------------------------------------------------------- Scene

FPS = 30
DUR = 3.0  # seamless loop

def cloud(cv, x, y, s):
    c = (255, 255, 255, 235)
    cv.ellipse(x, y, 46 * s, 20 * s, 0, c)
    cv.ellipse(x - 32 * s, y + 7 * s, 28 * s, 14 * s, 0, c)
    cv.ellipse(x + 34 * s, y + 7 * s, 30 * s, 15 * s, 0, c)
    cv.ellipse(x + 6 * s, y - 10 * s, 26 * s, 15 * s, 0, c)

def scene(cv, t):
    horizon = 472
    # sky
    cv.grad(0, 0, W, horizon, (116, 192, 235), (223, 244, 250))
    # sun
    cv.circle(806, 92, 60, (255, 220, 110, 80))
    cv.circle(806, 92, 44, (255, 209, 74))
    # clouds
    cloud(cv, 150, 92, 1.0)
    cloud(cv, 455, 62, 0.75)
    cloud(cv, 640, 150, 1.05)
    # hills
    cv.ellipse(240, horizon + 46, 360, 94, 0, (128, 190, 120))
    cv.ellipse(740, horizon + 58, 440, 106, 0, (104, 172, 106))
    # curb + road
    cv.rect(0, horizon, W, 10, (163, 167, 171))
    cv.rect(0, horizon + 10, W, H - horizon - 10, (72, 76, 86))
    # moving road dashes (period 160px, 2 cycles per loop)
    phase = (t * 320) % 160
    for k in range(-1, 8):
        x = k * 160 - phase
        cv.rect(x, 556, 80, 8, (226, 226, 216, 220))
    # speed lines (period 300px, 6 cycles per loop)
    ys = [388, 434, 480, 522]
    for i, yy in enumerate(ys):
        ph = (t * 600 + i * 150) % 300
        x = 350 - ph
        cv.stroke([(x, yy), (x + 62 + i * 14, yy)], 5, (255, 255, 255, 105))

    # ----- board + pelican group
    bob = 2.5 * math.sin(2 * math.pi * t)
    tilt = math.radians(1.8 * math.sin(2 * math.pi * t / DUR))
    ox, oy = 480.0, 543.0 + bob
    ca, sa = math.cos(tilt), math.sin(tilt)
    def P(x, y):
        return (ox + x * ca - y * sa, oy + x * sa + y * ca)
    def B(*pts):
        return [P(x, y) for x, y in pts]

    # shadow
    cv.ellipse(ox, 582, 178, 13, 0, (0, 0, 0, 70))

    # deck
    cv.poly(B((-172,-26),(-150,-11),(150,-11),(172,-26),(172,-15),(150,-1),(-150,-1),(-172,-15)), (206, 160, 105))
    cv.poly(B((-172,-26),(-150,-11),(150,-11),(172,-26),(172,-21),(150,-7),(-150,-7),(-172,-21)), (52, 52, 58))
    # red deck stripe
    cv.poly(B((-90,-4),(90,-4),(90,-1.5),(-90,-1.5)), (200, 70, 60))
    # trucks
    cv.poly(B((-104,-1),(-72,-1),(-77,11),(-99,11)), (130, 134, 140))
    cv.poly(B((72,-1),(104,-1),(99,11),(77,11)), (130, 134, 140))
    # wheels (4 rotations per loop)
    theta = 2 * math.pi * 4 * t / DUR
    for wx in (-88, 88):
        c = P(wx, 16)
        cv.circle(c[0], c[1], 16, (246, 199, 74))
        cv.circle(c[0], c[1], 5.5, (85, 88, 94))
        for k in (0, math.pi / 2):
            ang = theta + k
            dx, dy = 11 * math.cos(ang), 11 * math.sin(ang)
            cv.stroke([(c[0] - dx, c[1] - dy), (c[0] + dx, c[1] + dy)], 3, (85, 88, 94))

    # ----- pelican (local coords, feet on deck top y=-11)
    orange = (244, 153, 64)
    white = (250, 247, 238)
    # far wing (raised for balance)
    cv.poly(B((-15,-152),(-60,-190),(-105,-216),(-150,-228),(-162,-216),(-135,-200),
              (-100,-178),(-62,-152),(-28,-126)), (224, 220, 208))
    cv.stroke([P(-142,-224), P(-102,-198)], 2.5, (196, 192, 180))
    cv.stroke([P(-120,-213), P(-82,-188)], 2.5, (196, 192, 180))
    cv.stroke([P(-98,-201), P(-62,-176)], 2.5, (196, 192, 180))
    # tail
    cv.poly(B((-52,-138),(-104,-152),(-98,-128),(-56,-112)), (236, 232, 220))
    cv.stroke([P(-62,-134), P(-96,-146)], 2.5, (205, 200, 188))
    # legs + webbed feet
    cv.stroke([P(-26,-80), P(-30,-48), P(-29,-16)], 13, orange)
    cv.stroke([P(20,-82), P(26,-48), P(21,-16)], 13, orange)
    cv.poly(B((-50,-15),(-10,-15),(-4,-4),(-46,-3)), orange)
    cv.poly(B((0,-15),(40,-15),(46,-4),(4,-3)), orange)
    cv.stroke([P(-36,-12), P(-30,-5)], 2, (214, 122, 40))
    cv.stroke([P(-24,-12), P(-18,-5)], 2, (214, 122, 40))
    cv.stroke([P(14,-12), P(20,-5)], 2, (214, 122, 40))
    cv.stroke([P(26,-12), P(32,-5)], 2, (214, 122, 40))
    # body
    bc = P(-5, -125)
    cv.ellipse(bc[0], bc[1], 66, 52, -12 + math.degrees(tilt), white)
    # near wing (folded)
    wc = P(-12, -122)
    cv.ellipse(wc[0], wc[1], 44, 23, -8 + math.degrees(tilt), (238, 234, 224))
    cv.stroke([P(-48,-121), P(-12,-111), P(22,-119)], 2.5, (205, 200, 188))
    cv.stroke([P(-40,-130), P(-8,-122), P(16,-128)], 2.5, (212, 208, 196))
    # neck + head
    cv.stroke([P(34,-152), P(60,-180), P(82,-200)], 30, white)
    hc = P(100, -218)
    cv.circle(hc[0], hc[1], 33, white)
    # crest feathers
    cv.stroke([P(76,-242), P(56,-257)], 4, (233, 229, 218))
    cv.stroke([P(80,-234), P(58,-245)], 4, (233, 229, 218))
    # pouch + beak (local, drawn then rotated by group transform)
    cv.poly(B((118,-212),(238,-206),(214,-176),(158,-160),(124,-184)), (255, 168, 78))
    cv.poly(B((118,-234),(238,-214),(238,-206),(118,-212)), (255, 190, 90))
    cv.poly(B((238,-214),(250,-208),(238,-206)), (238, 166, 66))
    cv.stroke([P(122,-212), P(234,-207)], 2, (230, 150, 60, 160))
    # eye
    ec = P(108, -226)
    cv.circle(ec[0], ec[1], 5, (35, 35, 40))
    cv.circle(ec[0] + 1.6, ec[1] - 1.8, 1.8, (255, 255, 255))

# ----------------------------------------------------------------------------- Main

def main():
    t0 = 0.5
    cv = Canvas()
    scene(cv, t0)
    with open("output/pelican_skateboard.svg", "w") as f:
        f.write(to_svg(cv, W, H))
    print("wrote SVG")

    rgb = render_rgb(cv, W, H, S)
    write_png("output/pelican_skateboard.png", W, H, rgb)
    print("wrote PNG")

    # video: pipe raw frames to ffmpeg
    nframes = int(FPS * DUR)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
         "output/pelican_skateboard.mp4"],
        stdin=subprocess.PIPE)
    for i in range(nframes):
        cv = Canvas()
        scene(cv, i / FPS)
        ff.stdin.write(render_rgb(cv, W, H, S))
        if i % 15 == 0:
            print("frame %d/%d" % (i, nframes)); sys.stdout.flush()
    ff.stdin.close()
    ff.wait()
    print("wrote MP4, rc=%d" % ff.returncode)

if __name__ == "__main__":
    main()
