#!/usr/bin/env python3
"""16-bit pixel-art Eiffel Tower generator.
Grid-based pixel art, colors quantized to RGB565 (16-bit), upscaled with
nearest-neighbour so each 'pixel' is a crisp block. Writes PPM, converted to JPG via ffmpeg.
"""
import os

GW, GH = 64, 80     # pixel-art grid
PIX = 8             # block size -> final 512x640
CX = 32
TOP_Y = 6
BASE_Y = 68
ARCH_TOP = 52

def rgb565(r, g, b):
    """Quantize to 16-bit RGB565, return as 8-bit display values."""
    r = max(0, min(255, r)); g = max(0, min(255, g)); b = max(0, min(255, b))
    r5 = (r >> 3) << 3
    g6 = (g >> 2) << 2
    b5 = (b >> 3) << 3
    # expand back slightly for nicer display (optional) - keep masked values
    return (r5, g6, b5)

def lerp(a, b, t):
    return int(a + (b - a) * t)

def sky_color(gy):
    t = gy / BASE_Y  # 0 top -> 1 horizon
    t = max(0.0, min(1.0, t))
    # top deep blue -> mid -> warm horizon
    if t < 0.55:
        k = t / 0.55
        r = lerp(42, 92, k); g = lerp(80, 146, k); b = lerp(168, 214, k)
    else:
        k = (t - 0.55) / 0.45
        r = lerp(92, 172, k); g = lerp(146, 208, k); b = lerp(214, 232, k)
    return (r, g, b)

def half_width(gy):
    if gy < TOP_Y or gy > BASE_Y:
        return 0
    h = (gy - TOP_Y) / (BASE_Y - TOP_Y)
    return 1.2 + 14.5 * (h ** 1.65)

def arch_half(gy):
    if gy < ARCH_TOP or gy > BASE_Y:
        return -1
    f = (gy - ARCH_TOP + 1) / (BASE_Y - ARCH_TOP + 1)
    return 10.5 * (f ** 0.9)

# platforms: (y_start, thickness, extra_half)
PLATFORMS = [
    (13, 2, 2),   # top deck
    (30, 2, 3),   # second floor
    (46, 2, 3),   # first floor
]
def platform_at(gy):
    for y0, th, extra in PLATFORMS:
        if y0 <= gy < y0 + th:
            return (y0, th, extra)
    return None

# clouds: list of (x0,x1,y0,y1)
CLOUDS = [
    (6, 19, 11, 14),
    (42, 58, 17, 21),
    (9, 17, 27, 29),
]
def in_cloud(gx, gy):
    for x0, x1, y0, y1 in CLOUDS:
        if x0 <= gx <= x1 and y0 <= gy <= y1:
            # rounded corners: cut corners
            if (gx == x0 and gy == y0) or (gx == x0 and gy == y1) or (gx == x1 and gy == y0) or (gx == x1 and gy == y1):
                continue
            return True
    return False

def cloud_shadow(gx, gy):
    # bottom row of cloud bounding box -> shadow
    for x0, x1, y0, y1 in CLOUDS:
        if x0 <= gx <= x1 and gy == y1:
            if in_cloud(gx, gy):
                return True
    return False

# trees
TREES = [8, 55]
def tree_pixel(gx, gy):
    for tx in TREES:
        # canopy gy 60..66 triangular
        if 60 <= gy <= 66:
            # half width: wider at bottom
            hw = (gy - 59)  # 1..7? cap
            # make canopy 1..4
            # gy60 hw1, gy61 hw2, gy62 hw3, gy63 hw4, gy64 hw4, gy65 hw5? keep blocky
            table = {60: 1, 61: 2, 62: 3, 63: 3, 64: 4, 65: 4, 66: 5}
            hw = table.get(gy, 3)
            if abs(gx - tx) <= hw:
                return True
        if gy in (67, 68) and abs(gx - tx) <= 0:
            return "trunk"
    return None

# buildings skyline (behind tower), left and right blocks
def building_color(gx, gy):
    # buildings occupy gy 62..67, but only outside central tower zone? draw everywhere, tower overdraws
    if not (62 <= gy <= 67):
        return None
    # vary roofline: left block 0..14 top 62, mid block 48..63 top 63, plus small centre blocks?
    # define building segments
    # segment: (x0,x1,top)
    segs = [(0, 14, 62), (48, 63, 62), (15, 20, 64), (44, 47, 64)]
    for x0, x1, top in segs:
        if x0 <= gx <= x1 and top <= gy <= 67:
            if gy == top:
                # roof dark
                return (88, 76, 70)
            else:
                # wall
                # windows: dark dots every 3x2
                if (gx % 3 == 1) and (gy % 2 == 0):
                    return (70, 72, 92)  # windows
                return (198, 186, 166)
    return None

def ground_color(gx, gy):
    if gy < BASE_Y:
        return None
    if gy <= 70:
        # pavement
        base = (172, 168, 152)
        # central path under tower
        if abs(gx - CX) <= 6:
            base = (186, 180, 164)
        # checker subtle
        if (gx + gy) % 5 == 0:
            base = (base[0]-12, base[1]-12, base[2]-12)
        return base
    else:
        # grass
        if abs(gx - CX) <= 6 and gy <= 73:
            # path continues a bit into grass
            return (186, 180, 164)
        if (gx + gy) % 2 == 0:
            return (86, 148, 78)
        else:
            return (76, 134, 68)

grid = [[(0,0,0) for _ in range(GW)] for _ in range(GH)]

for gy in range(GH):
    hw = half_width(gy)
    ah = arch_half(gy)
    plat = platform_at(gy)
    plat_half = None
    if plat is not None:
        y0, th, extra = plat
        plat_half = round(half_width(y0)) + extra
    for gx in range(GW):
        dx = gx - CX
        # start with sky
        r, g, b = sky_color(gy)

        # sun: small block top-right
        if 53 <= gx <= 56 and 6 <= gy <= 9:
            r, g, b = (252, 220, 100)
            if gx == 53 or gx == 56 or gy == 6 or gy == 9:
                r, g, b = (248, 200, 80)  # edge

        # clouds (over sky, behind tower)
        if in_cloud(gx, gy):
            if cloud_shadow(gx, gy):
                r, g, b = (196, 204, 216)
            else:
                r, g, b = (244, 244, 248)

        # birds: two tiny gull "v" shapes, kept clear of tower/clouds/sun
        # bird1 left of tower, bird2 upper-middle-right
        if (gx == 19 and gy == 19) or (gx == 21 and gy == 19) or (gx == 20 and gy == 20):
            r, g, b = (40, 44, 60)
        if (gx == 40 and gy == 9) or (gx == 42 and gy == 9) or (gx == 41 and gy == 10):
            r, g, b = (40, 44, 60)

        # buildings behind
        bc = building_color(gx, gy)
        if bc is not None:
            r, g, b = bc

        # ground
        gc = ground_color(gx, gy)
        if gc is not None:
            r, g, b = gc

        # trees (in front of buildings/ground, behind tower? trees to sides so no overlap)
        tp = tree_pixel(gx, gy)
        if tp == True:
            # canopy shading left dark / right light
            if dx < -20 or (gx < TREES[0]+1 and gx in [TREES[0]-1, TREES[0]-2] if False else False):
                pass
            # per-tree local dx
            for tx in TREES:
                if abs(gx - tx) <= 5 and 60 <= gy <= 66:
                    ldx = gx - tx
                    if ldx < 0:
                        r, g, b = (44, 96, 50)
                    elif ldx == 0:
                        r, g, b = (58, 118, 60)
                    else:
                        r, g, b = (74, 142, 72)
                    # dither top highlight
                    if gy == 60 and ldx == 0:
                        r, g, b = (90, 160, 86)
                    break
        elif tp == "trunk":
            r, g, b = (96, 72, 48)

        # tower shadow on ground (ellipse under base)
        if gy >= BASE_Y and gy <= 71:
            # shadow extends left/right
            sh_hw = 18 - (gy - BASE_Y)  # 18..15
            if abs(dx) <= sh_hw:
                # darken ground
                r = int(r * 0.82); g = int(g * 0.82); b = int(b * 0.82)

        # ---- TOWER (foreground) ----
        is_tower = False
        is_platform = False
        if TOP_Y <= gy <= BASE_Y:
            # spire narrow handling: for gy 6..12 force narrow
            if gy <= 12:
                # antenna tip: gy6 single, then 3-wide
                if gy == 6:
                    if dx == 0:
                        is_tower = True
                elif gy <= 12:
                    if abs(dx) <= 1:
                        is_tower = True
            else:
                if abs(dx) <= round(hw) + 0.001:
                    # arch hole?
                    if gy >= ARCH_TOP and abs(dx) < ah:
                        is_tower = False
                        # arch interior: keep background, but add inner glow? no
                        pass
                    else:
                        is_tower = True
            # platform overrides / extends
            if plat is not None and abs(dx) <= plat_half:
                is_tower = True
                is_platform = True

        if is_tower:
            if gy == 6 and dx == 0:
                # red beacon
                r, g, b = (252, 60, 60)
            elif is_platform:
                # platform: top row light, bottom dark
                y0, th, extra = plat
                if gy == y0:
                    r, g, b = (150, 118, 88)  # railing highlight
                    # railing posts
                    if (gx % 2 == 0):
                        r, g, b = (52, 40, 32)
                else:
                    r, g, b = (52, 40, 32)
                    # under-platform shadow line
                    if abs(dx) <= plat_half - 1:
                        r, g, b = (40, 30, 24)
            else:
                # body
                # outline edges
                edge = round(hw) if gy > 12 else 1
                # arch inner edge outline
                is_arch_edge = (gy >= ARCH_TOP and abs(abs(dx) - ah) < 1.0)
                if abs(abs(dx) - edge) < 0.6 or is_arch_edge:
                    r, g, b = (36, 28, 22)  # dark outline
                elif dx < 0:
                    # shadow side (left)
                    r, g, b = (74, 56, 44)
                    # lattice horizontal beams
                    if gy % 3 == 0:
                        r, g, b = (60, 44, 34)
                    # diagonal lattice hint
                    if (gx * 2 + gy) % 9 == 0:
                        r, g, b = (52, 38, 30)
                elif dx == 0:
                    r, g, b = (48, 36, 28)
                else:
                    # lit side (right)
                    r, g, b = (128, 94, 64)
                    if gy % 3 == 0:
                        r, g, b = (108, 78, 54)
                    if (gx * 2 + gy) % 9 == 0:
                        r, g, b = (96, 68, 48)
                # centre vertical highlight line just right of centre?
                if dx == 1 and gy % 2 == 0:
                    # subtle highlight
                    pass
                # second floor / first floor beacon lights? small yellow dots on platforms
                # add lights under platforms (evening lamps)
                # keep daytime so skip

        # quantize to 16-bit
        r, g, b = rgb565(r, g, b)
        grid[gy][gx] = (r, g, b)

# upscale to final image
W, H = GW * PIX, GH * PIX
# build bytes
import io
os.makedirs("output", exist_ok=True)
ppm_path = "tmp_eiffel.ppm"
with open(ppm_path, "wb") as f:
    f.write(f"P6\n{W} {H}\n255\n".encode("ascii"))
    for gy in range(GH):
        for py in range(PIX):
            for gx in range(GW):
                r, g, b = grid[gy][gx]
                f.write(bytes((r, g, b)) * PIX)

print(f"Wrote {ppm_path} {W}x{H}")
# count unique colors (should be <=65536)
uniq = set()
for row in grid:
    for c in row:
        uniq.add(c)
print(f"Unique grid colors: {len(uniq)} (16-bit max 65536)")
