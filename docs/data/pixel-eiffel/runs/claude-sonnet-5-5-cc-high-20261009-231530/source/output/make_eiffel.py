"""Pixel-art Eiffel Tower in 16-bit (RGB565) color. Renders 160x200, upscales 5x, saves JPG via ffmpeg."""
import math, random, zlib, struct, subprocess, os

W, H, S = 160, 200, 5
CX, TOP, BASE = 80, 22, 168
random.seed(7)
img = [[(0, 0, 0)] * W for _ in range(H)]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

def mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

# --- dusk sky: banded gradient with Bayer dithering ---
stops = [(0, (18, 16, 56)), (0.35, (70, 40, 110)), (0.6, (180, 80, 120)), (0.8, (250, 150, 90)), (1.0, (255, 205, 120))]
def sky(y):
    t = y / (BASE - 6)
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(c0, c1, max(0, (t - t0) / (t1 - t0)))
    return stops[-1][1]
for y in range(H):
    c = sky(y)
    for x in range(W):
        d = (BAYER[y % 4][x % 4] / 16 - 0.5) * 22
        img[y][x] = tuple(max(0, min(255, v + d)) for v in c)

# stars
for _ in range(70):
    x, y = random.randrange(W), random.randrange(0, 85)
    b = random.choice([200, 230, 255])
    img[y][x] = (b, b, min(255, b))
# moon
for y in range(-8, 9):
    for x in range(-8, 9):
        if x * x + y * y <= 36:
            px, py = 126 + x, 24 + y
            shade = 1 if (x + 2) ** 2 + (y - 1) ** 2 > 30 else 0
            img[py][px] = (255, 244, 205) if not shade else (225, 210, 165)
        elif x * x + y * y <= 64:
            px, py = 126 + x, 24 + y
            img[py][px] = mix(img[py][px], (255, 220, 170), 0.18)
for (mx, my) in [(124, 22), (128, 27), (122, 27)]:
    img[my][mx] = (205, 190, 150)
# clouds
def cloud(cx, cy, w, col):
    for i in range(w):
        h = int(2 * math.sin(math.pi * i / w) + 0.5)
        for j in range(h):
            x, y = cx + i, cy - j
            if 0 <= x < W: img[y][x] = col
for (cx_, cy_, w_) in [(8, 88, 34), (100, 98, 40), (40, 105, 30), (130, 80, 24)]:
    cloud(cx_, cy_, w_, (150, 80, 120)); cloud(cx_ + 3, cy_ + 2, w_ - 6, (214, 120, 110))

# --- skyline of Paris ---
sil = (52, 34, 78)
sil2 = (74, 44, 90)
x = 0
while x < W:
    w = random.randint(6, 13); h = random.randint(8, 17)
    for xx in range(x, min(W, x + w)):
        for yy in range(BASE - h, BASE):
            img[yy][xx] = sil2
        if (xx - x) % 2 == 0 and h > 11:
            pass
        for yy in range(BASE - h, BASE - h + 2):
            img[yy][xx] = (92, 56, 100)
    # windows
    for wy in range(BASE - h + 3, BASE - 2, 3):
        for wx in range(x + 1, min(W, x + w) - 1, 3):
            if random.random() < 0.45: img[wy][wx] = (255, 215, 120)
    x += w
# dome (Invalides-ish)
for y in range(-9, 0):
    for xx in range(-9, 10):
        if xx * xx / 81 + y * y / 81 <= 1:
            px = 28 + xx; img[BASE - 14 + y][px] = (230, 190, 90) if xx > 1 else (176, 138, 70)
for y in range(BASE - 14, BASE):
    for xx in range(-7, 8): img[y][28 + xx] = sil2
for y in range(BASE - 28, BASE - 22): img[y][28] = (230, 190, 90)

# --- ground: lawn, path, river bank ---
for y in range(BASE, H):
    t = (y - BASE) / (H - BASE)
    for x in range(W):
        d = BAYER[y % 4][x % 4] / 16
        g = mix((40, 110, 70), (20, 70, 50), t)
        if (x + y * 3) % 11 == 0 and d > 0.4: g = mix(g, (70, 150, 80), 0.6)
        img[y][x] = g
# central path (perspective)
for y in range(BASE, H):
    t = (y - BASE) / (H - BASE)
    hw = 7 + 52 * t
    for x in range(W):
        if abs(x - CX) < hw:
            d = BAYER[y % 4][x % 4] / 16
            img[y][x] = mix((196, 160, 120), (150, 110, 96), t) if d < 0.75 else (176, 140, 110)
# reflection glow on path
for y in range(BASE, H):
    for x in range(CX - 3, CX + 4):
        if (y + x) % 2 == 0: img[y][x] = mix(img[y][x], (255, 200, 120), 0.35)

# --- tower ---
def hw(y):
    t = (y - TOP) / (BASE - TOP)
    return 0.8 + 38 * t ** 2.4 + 3.5 * t ** 8
P1, P2, P3 = 128, 92, 54    # platform rows (bottom -> up)
IRON_L = (120, 74, 48); IRON = (176, 118, 62); IRON_H = (236, 176, 84)
def tower_pixel(x, y):
    dx = x - CX; w = hw(y)
    if abs(dx) > w + 0.5: return None
    ax = abs(dx)
    # arch cutout between legs
    if y > P1:
        arch_cy = BASE + 14; rx = w * 0.60; ry = (BASE + 14 - P1 - 6)
        inside_arch = (dx / rx) ** 2 + ((y - arch_cy) / ry) ** 2 < 1
        if inside_arch and ax < w * 0.62:
            # arch rim
            rim = (dx / rx) ** 2 + ((y - arch_cy) / ry) ** 2 > 0.80
            return IRON_L if rim else None
        # inner leg cut (open between legs under lowest part)
        if ax < w * 0.38 and y > P1 + 10 and not inside_arch:
            return None
    # platform bars
    for py, ext, th in ((P1, 3, 3), (P2, 2, 2), (P3, 2, 2)):
        if py <= y < py + th and ax <= w + ext: return IRON_H if y == py else IRON_L
    if y <= TOP + 1 + 0: return IRON
    # edges (girders)
    edge = ax >= w - 1.6
    # lattice
    period = 5 if y > P2 else 4
    lat = ((y + ax) % period == 0) or ((y - ax) % period == 0)
    # horizontal ribs
    rib = (y % 12 == 0)
    if edge:
        return IRON_H if (dx > 0 and ax >= w - 0.8) else IRON
    if y > P2 and ax < w * 0.30 and y < P1: lat = lat and True
    if lat or rib:
        return IRON if dx >= 0 else IRON_L
    # backing haze so lattice reads as tower mass
    return (86, 54, 62) if y > P3 - 6 and ax < w - 1 and (x + y) % 2 == 0 else None
for y in range(TOP - 14, BASE + 1):
    for x in range(W):
        if y < TOP:  # antenna
            if x == CX and y >= TOP - 14: img[y][x] = IRON
            continue
        c = tower_pixel(x, y)
        if c: img[y][x] = c
# beacon
for (bx, by, c) in [(CX, TOP - 15, (255, 250, 200)), (CX - 1, TOP - 15, (255, 190, 90)), (CX + 1, TOP - 15, (255, 190, 90)), (CX, TOP - 16, (255, 190, 90)), (CX, TOP - 14, (255, 190, 90))]:
    img[by][bx] = c
# glow around beacon
for dy in range(-6, 7):
    for dx_ in range(-6, 7):
        d = math.hypot(dx_, dy)
        if 1.5 < d < 6:
            x, y = CX + dx_, TOP - 15 + dy
            if img[y][x][0] < 200 and (x + y) % 2 == 0: img[y][x] = mix(img[y][x], (255, 210, 130), 0.3 * (1 - d / 6))
# string lights along platforms and edges
for y in (P1, P2, P3):
    w = hw(y)
    for x in range(int(CX - w - 2), int(CX + w + 3)):
        if (x % 3 == 0): img[y][x] = (255, 232, 140)
for y in range(TOP + 4, BASE, 7):
    w = hw(y)
    for s in (-1, 1):
        x = int(round(CX + s * w))
        img[y][x] = (255, 240, 170)

# --- trees (dark round) & lamps in foreground ---
def tree(x0, y0, r):
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            if x * x + y * y <= r * r:
                lit = x + y < 0
                img[y0 + y][x0 + x] = (34, 104, 62) if lit else (20, 66, 48)
    for y in range(y0 + r, y0 + r + 4): img[y][x0] = (70, 44, 40)
for (tx, ty, r) in [(12, 178, 7), (34, 184, 8), (126, 180, 7), (148, 186, 8), (58, 190, 4), (102, 190, 4)]:
    tree(tx, ty, r)
for lx in (50, 110, 22, 138):
    for y in range(176, 190): img[y][lx] = (40, 30, 50)
    img[175][lx] = (255, 235, 150)
    for dx_, dy in ((-1, 0), (1, 0), (0, -1)): img[175 + dy][lx + dx_] = (255, 190, 100)

# --- quantize to RGB565 (16-bit color) ---
def q565(c):
    r, g, b = (max(0, min(255, int(round(v)))) for v in c)
    r5, g6, b5 = r >> 3, g >> 2, b >> 3
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))
pix = [[q565(img[y][x]) for x in range(W)] for y in range(H)]

# write upscaled PNG (nearest-neighbour), then convert to JPG
def png(path, pix, s):
    raw = bytearray()
    for row in pix:
        line = bytearray()
        for p in row: line += bytes(p) * s
        raw += (b"\x00" + bytes(line)) * s
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W * s, H * s, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(here, "_tmp.png")
png(tmp, pix, S)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-q:v", "2", "-pix_fmt", "yuvj444p", os.path.join(here, "eiffel_pixel_16bit.jpg")], check=True)
os.remove(tmp)
print("unique colors:", len({c for r in pix for c in r}))
