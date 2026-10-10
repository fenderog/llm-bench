# SNES-style Eiffel Tower at dusk. 256x224, <=128 colors, <=16 colors per 8x8 tile.
import zlib, struct, math, random
W, H = 256, 224
random.seed(7)
img = [[None]*W for _ in range(H)]
def put(x, y, c):
    if 0 <= x < W and 0 <= y < H: img[y][x] = c
BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]

# --- Sky: banded dusk gradient with ordered dither between bands
sky = [(24,16,56),(40,24,84),(64,32,108),(96,40,124),(136,52,128),(180,68,120),
       (220,92,104),(240,124,88),(250,160,84),(252,196,104)]
HOR = 168
for y in range(HOR):
    t = (y / HOR) ** 1.25 * (len(sky)-1)
    i = int(t); f = t - i
    for x in range(W):
        c = sky[min(i + (f*16 > BAYER[y%4][x%4]), len(sky)-1)]
        img[y][x] = c
# stars
for _ in range(60):
    x, y = random.randrange(W), random.randrange(60)
    put(x, y, (200,200,240) if random.random() < .7 else (255,255,255))
for x, y in [(30,14),(200,22),(150,9),(232,44)]:
    for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]: put(x+dx, y+dy, (255,255,255) if dx==dy==0 else (180,180,230))
# setting sun with horizontal cuts
sx, sy, sr = 196, 150, 26
for y in range(sy-sr, sy+sr):
    for x in range(sx-sr, sx+sr):
        d = math.hypot(x-sx, y-sy)
        if d < sr:
            if y > sy - 6 and (y - sy) % (3 + (sy+sr-y)//6) < 1 + (y-sy)//8: continue
            put(x, y, (255,236,150) if d < sr-4 else (255,208,112))
# clouds: stacked ellipse blobs, lit from below-right
def cloud(cx, cy, w, h):
    blobs = [(cx + random.randint(-w, w), cy + random.randint(-h//2, h//2), random.randint(h, h*2)) for _ in range(9)]
    for y in range(cy - 3*h, cy + 3*h):
        for x in range(cx - w - 3*h, cx + w + 3*h):
            inside = any(((x-bx)/(r*1.8))**2 + ((y-by)/r)**2 < 1 for bx, by, r in blobs)
            if not inside or y > cy + h: continue
            low = any(((x-bx)/(r*1.8))**2 + ((y-by-3)/r)**2 >= 1 for bx, by, r in blobs if ((x-bx)/(r*1.8))**2 + ((y-by)/r)**2 < 1)
            base = (148,72,132) if y < cy - h//2 else (196,92,132)
            if y > cy and ((y + x//2) % 2 == 0 or y > cy + h//2): base = (244,152,128)
            if low and y > cy - 1: base = (255,200,150)
            put(x, y, base)
cloud(60, 52, 30, 5); cloud(170, 74, 26, 4); cloud(236, 34, 16, 3); cloud(24, 100, 18, 3); cloud(120, 30, 14, 3)

# --- Distant city skyline (two layers)
far, near = (112,56,112), (60,32,80)
x = 0
while x < W:
    w = random.randint(6, 16); h = random.randint(4, 14)
    for xx in range(x, x+w):
        for y in range(HOR-h, HOR): put(xx, y, far)
    if random.random() < .25:  # dome / spire
        for y in range(6):
            for xx in range(x+w//2-3+y//2, x+w//2+3-y//2): put(xx, HOR-h-y, far)
    x += w
# Sacré-Cœur-ish dome far left
for y in range(14):
    for xx in range(40-14+y, 40+14-y): pass
x = 0
while x < W:
    w = random.randint(10, 22); h = random.randint(8, 20)
    for xx in range(x, x+w):
        for y in range(HOR+6-h, HOR+8): put(xx, y, near)
        put(xx, HOR+6-h, (88,48,104))
    for y in range(HOR+6-h+3, HOR+4, 4):  # lit windows
        for xx in range(x+2, x+w-2, 3):
            if random.random() < .35: put(xx, y, (255,208,112))
    # mansard roof chimneys
    for xx in range(x+2, x+w-2, 5): put(xx, HOR+5-h, near); put(xx, HOR+4-h, near)
    x += w

# --- Seine river with sky reflection
RIV = HOR + 8
refl = [(252,196,104),(240,124,88),(180,68,120),(96,40,124),(40,24,84)]
for y in range(RIV, 196):
    k = (y - RIV) / (196 - RIV) * (len(refl)-1)
    for x in range(W):
        i = int(k); c = refl[min(i + ((k-i)*16 > BAYER[y%4][x%4]), len(refl)-1)]
        img[y][x] = c
    for _ in range(18):  # shimmer
        x0 = random.randrange(W); l = random.randint(2, 8)
        for xx in range(x0, x0+l): put(xx, y, (255,236,150) if abs(xx-sx) < 26 and random.random() < .8 else (64,32,108))
# embankment + trees + lawn (Champ de Mars) in foreground
for y in range(196, H):
    for x in range(W):
        img[y][x] = (40,56,40) if y > 200 else (88,76,84)
    if y == 196: 
        for x in range(W): img[y][x] = (140,116,112)
for y in range(201, H):
    for x in range(W):
        if (x*7 + y*3) % 11 == 0: put(x, y, (56,80,48))
        if y > 212 and (x + y) % 3 == 0: put(x, y, (24,36,32))
# gravel path to tower
for y in range(201, H):
    hw = 14 + (y-201)*2
    for x in range(128-hw, 128+hw):
        put(x, y, (176,140,112) if (x+y)%5 else (140,108,96))
# path border
# tree rows on each side
def tree(cx, by, r):
    for y in range(by-2*r, by):
        for x in range(cx-r, cx+r+1):
            if ((x-cx)/r)**2 + ((y-(by-r))/r)**2 < 1:
                c = (24,44,40)
                if x - cx < -r*0.2 and y < by - r: c = (48,84,56)
                if x - cx < -r*0.5 and y < by - r*1.3: c = (96,128,64)
                put(x, y, c)
for cx in list(range(4, 88, 11)) + list(range(172, 256, 11)):
    tree(cx, 204 + (cx % 3), 7)

# --- The tower
TOP, P1, P2, BASE = 18, 152, 112, 200
CX = 128
DK, MD, LT, HL, OUT = (36,20,40), (88,44,56), (148,72,64), (232,148,88), (16,8,24)
def halfw(y):
    t = (y - TOP) / (BASE - TOP)
    return 1.5 + 66 * t ** 2.3
def inner(y):
    if y > P1:  # big arch
        t = (y - P1) / (BASE - P1)
        a = halfw(BASE) - 34
        return a * math.sqrt(max(0, 1 - (1-t)**2)) if t > 0 else 0
    if y > P2 + 4:
        t = (y - P2 - 4) / (P1 - P2 - 4)
        return (halfw(y) - 9) * t ** 1.2
    return -1
for y in range(TOP, BASE):
    w = halfw(y); iw = inner(y)
    for x in range(int(CX - w), int(CX + w) + 1):
        d = abs(x - CX + 0.5)
        if d > w: continue
        if iw >= 0 and d < iw: continue
        # position within leg (0 outer..1 inner)
        leg = (w - iw) if iw >= 0 else w * 2
        edge = (w - d < 1) or (iw >= 0 and d - iw < 1)
        left = x < CX
        if edge: c = OUT if not left else MD
        elif leg > 9 and ((x + y) % 4 and (x - y) % 4) and (w - d) > 2 and (iw < 0 or d - iw > 2) and y > 60:
            continue  # lattice holes let sky through
        else:
            c = HL if left and (x+y) % 6 == 0 else (LT if left else DK)
            if not left and (x - y) % 6 == 0: c = MD
        put(x, y, c)
    if w < 4 and y > TOP + 4:  # upper shaft: solid with highlight
        for x in range(int(CX - w), int(CX + w) + 1):
            put(x, y, HL if x < CX - 1 else (LT if x < CX + 1 else DK))
# platforms with lit railings
for py, ext, th in [(P1, 6, 6), (P2, 4, 4), (52, 2, 3)]:
    w = halfw(py) + ext
    for y in range(py - th, py):
        for x in range(int(CX - w), int(CX + w) + 1):
            c = MD if y == py - th else DK
            if y == py - th + 1: c = LT if x < CX else MD
            if th > 3 and y == py - 2 and x % 3 == 0: c = (255,224,120)
            put(x, y, c)
    for x in range(int(CX - w), int(CX + w) + 1, 2): put(x, py - th - 1, OUT)
# antenna + beacon
for y in range(4, TOP + 2): put(CX, y, DK); put(CX-1, y, LT if y > 10 else DK)
for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]: put(CX-1+dx, 6+dy, (255,255,220) if dx==dy==0 else (255,208,112))
# sparkle lights on the tower
for _ in range(40):
    y = random.randint(TOP+6, BASE-2); w = halfw(y)
    x = int(CX + random.uniform(-w, w))
    if img[y][x] in (DK, LT, MD, HL): put(x, y, (255,236,150))

# --- Enforce constraints: <=16 colors per tile
def near(c, pal): return min(pal, key=lambda p: sum((a-b)**2 for a, b in zip(c, p)))
for ty in range(0, H, 8):
    for tx in range(0, W, 8):
        cnt = {}
        for y in range(ty, ty+8):
            for x in range(tx, tx+8): cnt[img[y][x]] = cnt.get(img[y][x], 0) + 1
        if len(cnt) > 16:
            keep = sorted(cnt, key=lambda c: -cnt[c])[:16]
            for y in range(ty, ty+8):
                for x in range(tx, tx+8):
                    if img[y][x] not in keep: img[y][x] = near(img[y][x], keep)
cols = {c for row in img for c in row}
assert len(cols) <= 128, len(cols)
# snap to SNES 15-bit color
img = [[tuple((v >> 3) << 3 | (v >> 5) for v in c) for c in row] for row in img]
print("colors:", len({c for r in img for c in r}))

raw = b"".join(b"\0" + bytes(v for c in row for v in c) for row in img)
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
open("output/eiffel_snes.png", "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
