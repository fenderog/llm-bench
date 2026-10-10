#!/usr/bin/env python3
"""16-bit (SNES-style, RGB555) pixel art of the Eiffel Tower at sunset.
Renders 256x224 native, writes PPM; ffmpeg upscales 4x nearest-neighbour to JPG."""
import math, random, subprocess, os

W, H = 256, 224
random.seed(7)
img = [[(0, 0, 0)] * W for _ in range(H)]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

# --- sky: banded gradient with ordered dithering between bands ---
SKY = [(24, 16, 64), (48, 24, 96), (96, 40, 120), (168, 56, 112),
       (224, 96, 88), (248, 152, 72), (248, 208, 112)]
HORIZON = 176
for y in range(HORIZON):
    f = y / HORIZON * (len(SKY) - 1)
    i = min(int(f), len(SKY) - 2)
    frac = f - i
    for x in range(W):
        img[y][x] = SKY[i + 1] if frac * 16 > BAYER[y % 4][x % 4] + 0.5 else SKY[i]

# stars in the upper sky
for _ in range(45):
    x, y = random.randrange(W), random.randrange(60)
    put(x, y, (248, 240, 200) if random.random() < 0.3 else (176, 160, 208))
for x, y in [(30, 12), (200, 22), (232, 8)]:  # twinkles
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        put(x + dx, y + dy, (176, 160, 208))
    put(x, y, (255, 255, 255))

# setting sun
SX, SY, SR = 196, 158, 26
for y in range(SY - SR, SY + SR):
    for x in range(SX - SR, SX + SR):
        d = math.hypot(x - SX, y - SY)
        if d < SR and y < HORIZON:
            if (y - SY + SR) > 30 and (y // 3) % 2 == 0 and y > SY:  # retro stripes
                continue
            put(x, y, (255, 232, 152) if d < SR - 4 else (255, 192, 104))

# pixel clouds
def cloud(cx, cy, w, col, hi):
    for k in range(w):
        h = int(3 + 3 * math.sin(k / w * math.pi) + 2 * math.sin(k * 0.7))
        for j in range(h):
            put(cx + k, cy - j, hi if j == h - 1 else col)
    for k in range(w + 8):
        put(cx - 4 + k, cy + 1, col)
cloud(20, 70, 40, (200, 88, 120), (240, 144, 136))
cloud(150, 52, 52, (136, 56, 128), (200, 96, 136))
cloud(60, 118, 34, (232, 128, 96), (248, 184, 120))
cloud(180, 100, 44, (232, 120, 96), (248, 176, 120))

# --- distant Paris skyline ---
FAR = (88, 40, 88)
x = 0
while x < W:
    bw, bh = random.randint(6, 16), random.randint(8, 22)
    for xx in range(x, min(W, x + bw)):
        for y in range(HORIZON - bh, HORIZON):
            put(xx, y, FAR)
    if random.random() < 0.4:  # mansard roof chimneys
        put(x + 2, HORIZON - bh - 1, FAR); put(x + 2, HORIZON - bh - 2, FAR)
    x += bw
NEAR = (56, 24, 64)
x = 0
while x < W:
    bw, bh = random.randint(10, 22), random.randint(4, 14)
    for xx in range(x, min(W, x + bw)):
        rh = bh + min(xx - x, x + bw - 1 - xx, 3)  # sloped roofs
        for y in range(HORIZON - rh, HORIZON + 2):
            put(xx, y, NEAR)
    for wy in range(HORIZON - bh + 3, HORIZON, 3):
        for wx in range(x + 2, x + bw - 2, 3):
            if random.random() < 0.35:
                put(wx, wy, (248, 200, 96))
    x += bw

# --- ground: Seine + Champ de Mars ---
for y in range(HORIZON, H):
    t = (y - HORIZON) / (H - HORIZON)
    for x in range(W):
        if y < 186:  # river reflecting the sky
            c = (64, 48, 120) if (x + y * 3) % 11 else (232, 120, 96)
            if abs(x - SX) < 20 - (y - HORIZON) and (x + y) % 3 == 0:
                c = (255, 208, 120)
        elif y < 188:
            c = (120, 96, 88)
        else:
            c = lerp((48, 88, 48), (24, 48, 32), t)
            if BAYER[y % 4][x % 4] < 3:
                c = (64, 112, 56)
        img[y][x] = c
# central gravel path in perspective
for y in range(188, H):
    hw = 6 + (y - 188) * 1.4
    for x in range(int(128 - hw), int(128 + hw) + 1):
        c = (200, 168, 120) if BAYER[y % 4][x % 4] > 4 else (168, 136, 96)
        put(x, y, c)

# --- Eiffel Tower ---
CX = 128
TOP, BASE = 18, 188
DARK, MID, LIT, HL = (64, 32, 32), (128, 64, 48), (184, 104, 64), (240, 168, 96)

def outer_hw(y):
    """outer half-width of tower silhouette at row y (concave curve)."""
    t = (y - 30) / (BASE - 30)
    return 1.5 + 50 * t ** 2.3 + 6 * t

def inner_hw(y):
    """half-width of the leg arch cutout (0 above the arch)."""
    ARCH_TOP = 150
    if y < ARCH_TOP:
        return -1
    t = (y - ARCH_TOP) / (BASE - ARCH_TOP)
    return 30 * math.sqrt(1 - (1 - t) ** 2)

tower = {}
for y in range(30, BASE):
    ohw, ihw = outer_hw(y), inner_hw(y)
    for x in range(int(CX - ohw), int(CX + ohw) + 1):
        dx = abs(x - CX)
        if dx < ihw:
            continue
        edge = dx >= ohw - 1.2 or (ihw >= 0 and dx < ihw + 1.2)
        # gap between the four legs (lower half)
        if y > 105 and dx < ihw + 1.2 + (y - 105) * 0.05 and ihw < 0 and False:
            pass
        lattice = (x + y) % 4 == 0 or (x - y) % 4 == 0 or y % 8 == 0
        if ohw < 4 or edge or lattice:
            tower[(x, y)] = 'edge' if edge else 'lat'
for (x, y), kind in tower.items():
    side = x - CX
    if kind == 'edge':
        c = HL if side < 0 else DARK
    else:
        c = LIT if side < -2 else (MID if side < 3 else DARK)
    put(x, y, c)
# spine/shadow lines down each leg
for y in range(105, BASE):
    ohw = outer_hw(y)
    for s in (-1, 1):
        put(int(CX + s * (ohw * 0.62)), y, MID if s < 0 else DARK)

# summit: cap + antenna
for y in range(22, 31):
    for x in range(CX - 2, CX + 3):
        put(x, y, LIT if x <= CX else MID)
for x in range(CX - 3, CX + 4):
    put(x, 30, DARK); put(x, 26, DARK)
for y in range(TOP - 8, 22):
    put(CX, y, (200, 200, 216))
put(CX, TOP - 9, (255, 64, 64))  # aviation beacon
for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
    put(CX + dx, TOP - 9 + dy, (200, 64, 96))

def platform(y, hw, h, arches=False):
    for yy in range(y, y + h):
        for x in range(int(CX - hw), int(CX + hw) + 1):
            if yy == y:
                c = HL if x < CX else LIT
            elif yy == y + h - 1:
                c = DARK
            else:
                c = (MID if (x - CX) % 3 else DARK) if not arches else MID
            put(x, yy, c)
    # little lights along the deck
    for x in range(int(CX - hw) + 2, int(CX + hw), 4):
        put(x, y + 1, (255, 232, 128))

platform(76, outer_hw(76) + 2, 3)    # top of second stage
platform(104, outer_hw(104) + 3, 5)  # second platform
platform(146, outer_hw(146) + 3, 7)  # first platform
# decorative arch fringe under first platform
for x in range(int(CX - 30), int(CX + 31)):
    d = abs(x - CX) / 30
    ay = 153 + int(6 * (1 - math.sqrt(max(0, 1 - d * d))))
    put(x, ay, LIT if x < CX else MID)
    put(x, ay - 1, DARK)

# leg feet / pedestals
for s in (-1, 1):
    fx = int(CX + s * (outer_hw(BASE - 1) - 10))
    for y in range(BASE - 3, BASE + 1):
        for x in range(fx - 11, fx + 12):
            put(x, y, (152, 136, 128) if y == BASE - 3 else (104, 88, 96))

# trees along the Champ de Mars
for tx in list(range(4, 70, 9)) + list(range(190, 256, 9)):
    ty = 196 + (abs(tx - 128) // 30)
    for y in range(ty - 6, ty + 3):
        for x in range(tx - 4, tx + 5):
            if (x - tx) ** 2 + (y - ty + 2) ** 2 * 1.4 < 18:
                c = (40, 96, 48) if x - tx < 1 and y < ty else (24, 64, 40)
                if (x + y) % 5 == 0 and x < tx:
                    c = (88, 144, 64)
                put(x, y, c)
    for y in range(ty + 2, ty + 6):
        put(tx, y, (72, 48, 40))

# --- quantise to 16-bit era colour depth (RGB555, as on the SNES) ---
def q(c):
    return tuple(((v >> 3) * 255 + 15) // 31 for v in c)

os.makedirs('output', exist_ok=True)
with open('eiffel_tmp.ppm', 'wb') as f:
    f.write(b'P6 %d %d 255\n' % (W, H))
    f.write(bytes(v for row in img for c in row for v in q(c)))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', 'eiffel_tmp.ppm',
                '-vf', 'scale=iw*4:ih*4:flags=neighbor', '-pix_fmt', 'yuvj444p',
                '-q:v', '1', 'output/eiffel_tower_16bit.jpg'], check=True)
os.remove('eiffel_tmp.ppm')
print('wrote output/eiffel_tower_16bit.jpg')
