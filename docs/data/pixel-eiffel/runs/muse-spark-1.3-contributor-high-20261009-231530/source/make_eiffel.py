#!/usr/bin/env python3
"""16-bit color pixel-art Eiffel Tower generator (stdlib only)."""
import random
import math
import subprocess
import os

W, H = 64, 96
SCALE = 8  # final 512x768
CX = W // 2
GROUND_Y = 78

def lerp(a, b, t):
    return int(a + (b - a) * t)

def lerp_color(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))

def to565(r, g, b):
    # quantize to RGB565 (16-bit color = 65536 colors)
    r5 = round((r >> 3) * 255 / 31)
    g6 = round((g >> 2) * 255 / 63)
    b5 = round((b >> 3) * 255 / 31)
    r5 = max(0, min(255, r5)); g6 = max(0, min(255, g6)); b5 = max(0, min(255, b5))
    return (r5, g6, b5)

random.seed(7)

# --- canvas ---
img = [[(0,0,0) for _ in range(W)] for _ in range(H)]

TOP = (26, 36, 92)
MID = (74, 122, 181)
HORIZON = (247, 200, 141)
GROUND1 = (74, 102, 66)
GROUND2 = (46, 62, 44)
STREET = (88, 80, 92)

for y in range(H):
    for x in range(W):
        if y < GROUND_Y:
            if y < int(H*0.45):
                t = y / (H*0.45)
                c = lerp_color(TOP, MID, t)
            else:
                t = (y - H*0.45) / (GROUND_Y - H*0.45)
                t = min(1.0, max(0.0, t))
                # ease
                c = lerp_color(MID, HORIZON, t**1.2)
            img[y][x] = c
        else:
            # ground: grass with street path in middle
            t = (y - GROUND_Y) / (H - GROUND_Y)
            c = lerp_color(GROUND1, GROUND2, t)
            # central walkway under tower
            if abs(x - CX) < 7:
                c = lerp_color((150,138,120), (90,82,74), t)
            img[y][x] = c

# stars in upper sky
for _ in range(70):
    x = random.randint(0, W-1)
    y = random.randint(0, int(H*0.35))
    # fade stars near horizon
    b = random.randint(150, 255)
    img[y][x] = (b, b, min(255, b+20))
    if random.random() < 0.3 and x+1 < W:
        img[y][x+1] = (b//2, b//2, b//2)

# moon (pixel circle)
mx, my, mr = 50, 14, 5
for y in range(my-mr-1, my+mr+2):
    for x in range(mx-mr-1, mx+mr+2):
        if 0 <= x < W and 0 <= y < GROUND_Y:
            d = math.hypot(x-mx, y-my)
            if d <= mr:
                img[y][x] = (245, 238, 210)
            elif d <= mr+1:
                img[y][x] = (200, 180, 150)

# blocky clouds (sunset tinted)
def cloud(cx, cy, w):
    for dy in range(3):
        for dx in range(-w, w+1):
            x = cx+dx; y = cy+dy
            if 0 <= x < W and 0 <= y < GROUND_Y:
                # jagged edges
                if abs(dx) == w and dy == 0 and random.random()<0.5:
                    continue
                if dy == 0:
                    img[y][x] = (235, 200, 175)
                elif dy == 1:
                    img[y][x] = (215, 165, 150)
                else:
                    img[y][x] = (120, 110, 150)

cloud(14, 30, 7)
cloud(48, 38, 5)
cloud(12, 55, 4)

# distant Paris rooftops silhouette
for x in range(W):
    h = 3 + int(2*math.sin(x*0.7) + (1 if x % 9 < 4 else 0))
    for y in range(GROUND_Y-h, GROUND_Y):
        # keep tower area clear
        if abs(x-CX) < 20:
            continue
        img[y][x] = (52, 48, 68)
        if y == GROUND_Y-h and random.random()<0.4:
            # chimneys
            if y-1 >= 0:
                img[y-1][x] = (52,48,68)

# --- Eiffel Tower ---
IRON = (106, 74, 48)
IRON_D = (62, 40, 26)
IRON_L = (150, 112, 74)
BEAM_D = (34, 22, 14)
GOLD = (255, 210, 120)

Y_TIP = 5
Y_TOP = 14      # top of shaft
Y_MID_PLAT = 34 # middle platform
Y_LOW_PLAT = 56 # lower platform
Y_BASE = GROUND_Y

def half_width(y):
    if y < Y_TOP:
        return 1.5
    t = (y - Y_TOP) / (Y_BASE - Y_TOP)
    t = min(1.0, max(0.0, t))
    return 2 + (19 - 2) * (t ** 1.55)

def beam_thick(y):
    t = (y - Y_TOP) / (Y_BASE - Y_TOP) if y >= Y_TOP else 0
    return 1 if y < 20 else (2 if y < 40 else 3)

# draw side beams + lattice
for y in range(Y_TOP, Y_BASE+1):
    hw = half_width(y)
    th = beam_thick(y)
    xl0 = int(round(CX - hw)); xl1 = xl0 + th
    xr1 = int(round(CX + hw)); xr0 = xr1 - th
    for x in range(xl0, xl1+1):
        if 0 <= x < W:
            # shading: left dark, small highlight
            img[y][x] = IRON_D if x <= xl0 else IRON
    for x in range(xr0, xr1+1):
        if 0 <= x < W:
            img[y][x] = IRON_L if x >= xr1 else IRON

# horizontal + X cross braces between beams (only above lower platform -> open arch below)
for y in range(Y_TOP+2, Y_LOW_PLAT+2, 5):
    hw = half_width(y)
    xl = int(round(CX - hw)) + beam_thick(y)
    xr = int(round(CX + hw)) - beam_thick(y)
    if xr - xl < 2:
        # solid fill for narrow top
        for x in range(int(round(CX-hw)), int(round(CX+hw))+1):
            if 0 <= x < W:
                img[y][x] = BEAM_D
        continue
    # horizontal bar
    for x in range(xl, xr+1):
        if 0 <= x < W:
            img[y][x] = BEAM_D
    # X brace to next bar (4 rows tall)
    for k in range(1, 5):
        yy = y + k
        if yy > Y_BASE or yy >= H:
            break
        hw2 = half_width(yy)
        xl2 = int(round(CX - hw2)) + beam_thick(yy)
        xr2 = int(round(CX + hw2)) - beam_thick(yy)
        if xr2 - xl2 < 2:
            break
        t = k / 5.0
        xa = int(round(xl + (xr-xl)*t))
        xb = int(round(xr - (xr-xl)*t))
        # only draw inside
        if xl2 <= xa <= xr2 and 0 <= xa < W:
            img[yy][xa] = BEAM_D
        if xl2 <= xb <= xr2 and 0 <= xb < W:
            img[yy][xb] = BEAM_D

# arch between legs (parabolic arch)
for x in range(W):
    hw_at_low = half_width(Y_LOW_PLAT+4)
    xl_arch = CX - hw_at_low
    xr_arch = CX + hw_at_low
    if xl_arch <= x <= xr_arch:
        # arch height: center higher than sides
        u = (x - CX) / hw_at_low  # -1..1
        arch_y = 68 - int(8 * (1 - u*u))  # top of arch ~60 center, ~68 sides
        for y in range(arch_y, arch_y+2):
            if Y_LOW_PLAT < y < Y_BASE and 0 <= y < H:
                img[y][x] = IRON_D

# platforms
def platform(y, extra):
    hw = half_width(y) + extra
    for x in range(int(round(CX-hw)), int(round(CX+hw))+1):
        if 0 <= x < W:
            for dy in range(2):
                yy = y+dy
                if 0 <= yy < H:
                    img[yy][x] = (28, 20, 14) if dy == 1 else (170, 130, 90)
    # railing
    for x in range(int(round(CX-hw)), int(round(CX+hw))+1):
        if 0 <= x < W and y-1 >= 0:
            if (x % 2 == 0):
                img[y-1][x] = (28, 20, 14)

platform(Y_MID_PLAT, 3)
platform(Y_LOW_PLAT, 5)

# top spire / antenna (thin iron with gold tip)
for y in range(Y_TIP, Y_TOP):
    img[y][CX] = IRON
    if y < Y_TIP+2:
        img[y][CX] = GOLD
# small dome under spire
for y in range(Y_TOP-3, Y_TOP+1):
    w = 2 if y < Y_TOP else 3
    for x in range(CX-w, CX+w+1):
        if 0 <= x < W:
            img[y][x] = IRON

# beacon glow (1px)
img[Y_TIP][CX] = (255, 240, 180)
if CX-1 >= 0: img[Y_TIP][CX-1] = (255,200,120)
if CX+1 < W: img[Y_TIP][CX+1] = (255,200,120)

# evening sparkle lights on tower (deterministic)
random.seed(42)
for _ in range(60):
    y = random.randint(Y_TOP, Y_BASE-2)
    hw = half_width(y)
    side = random.choice([-1, 1])
    x = int(round(CX + side*(hw-1)))
    if 0 <= x < W:
        # only on beams
        img[y][x] = GOLD

# (no searchlight — keep sky clean pixel stars)

# --- quantize to 16-bit (RGB565) ---
for y in range(H):
    for x in range(W):
        r, g, b = img[y][x]
        img[y][x] = to565(r, g, b)

# --- upscale nearest neighbor ---
S = SCALE
FW, FH = W*S, H*S
big = [[(0,0,0)]*FW for _ in range(FH)]
for y in range(H):
    for x in range(W):
        c = img[y][x]
        for dy in range(S):
            row = big[y*S+dy]
            for dx in range(S):
                row[x*S+dx] = c

# write PPM (P6)
os.makedirs("output", exist_ok=True)
ppm_path = "tmp_eiffel.ppm"
with open(ppm_path, "wb") as f:
    f.write(f"P6\n{FW} {FH}\n255\n".encode())
    for row in big:
        f.write(bytes([v for px in row for v in px]))

# convert to JPG via ffmpeg
jpg_path = "output/eiffel-16bit.jpg"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", ppm_path, "-q:v", "2", jpg_path], check=True)
os.remove(ppm_path)
print(f"wrote {jpg_path} {FW}x{FH}")

