# Procedural 16-bit style pixel art of the Eiffel Tower -> PPM (scaled to JPG via ffmpeg)
import math, random
W, H = 96, 128
random.seed(3)
img = [[(0,0,0)]*W for _ in range(H)]
sky = [(28,24,72),(48,36,104),(84,52,128),(140,72,132),(204,104,120),(240,152,112),(252,204,128)]
for y in range(H):
    t = y / 100
    i = min(len(sky)-1, int(t*len(sky)))
    for x in range(W):
        # dithered band edges
        j = i
        if i+1 < len(sky) and (t*len(sky) % 1) > 0.75 and (x+y) % 2 == 0: j = i+1
        img[y][x] = sky[j]
for _ in range(40):
    x, y = random.randrange(W), random.randrange(40)
    img[y][x] = (255,255,220) if random.random() < .3 else (180,170,220)
for y in range(H):  # moon
    for x in range(W):
        if (x-76)**2+(y-18)**2 <= 36 and (x-73)**2+(y-16)**2 > 25: img[y][x] = (255,244,200)
# city silhouette
h = 0
for x in range(W):
    if x % 5 == 0: h = random.randint(4, 14)
    for y in range(110-h, 112):
        c = (60,40,80)
        if (x*7+y*3) % 11 == 0 and y < 108: c = (255,210,110)
        img[y][x] = c
for y in range(112, H):  # ground / park
    for x in range(W):
        img[y][x] = (40,72,56) if (x+y) % 3 else (52,92,64)
for y in range(118, 124):
    for x in range(W): img[y][x] = (196,170,130) if (x//2+y) % 4 else (170,140,104)
# tower
cx, top, base = 48, 6, 114
def half(y):
    t = (y-top)/(base-top)
    return 0.6 + 34*t**2.4
dark, mid, lite, glow = (56,36,32), (112,68,44), (176,108,56), (255,200,96)
for y in range(top, base):
    hw = half(y)
    for x in range(W):
        d = abs(x+0.5-cx)
        if d > hw: continue
        edge = d > hw-1.2
        lat = ((x+y) % 4 == 0) or ((x-y) % 4 == 0)
        c = mid if lat else dark
        if edge: c = lite if x < cx else mid
        # arch between legs
        if y > 88:
            ah = 22*math.sqrt(max(0,1-((y-114)/26)**2))
            if d < ah - 0.5 and d < hw - 6: continue
        # open interior on upper body for see-through lattice
        if not edge and not lat and hw > 3 and y < 88 and (x+y) % 2: continue
        if d < 1 and y < 20: c = lite
        img[y][x] = c
for py in (40, 66, 88):  # platforms
    hw = int(half(py)) + 2
    for x in range(cx-hw, cx+hw):
        img[py][x] = glow if x % 2 else lite
        img[py+1][x] = dark
for y in range(top-4, top):  # antenna + beacon
    img[y][cx] = (200,200,200)
img[top-5][cx] = (255,80,80)
with open('eiffel.ppm', 'w') as f:
    f.write(f'P3 {W} {H} 255\n')
    for row in img: f.write(' '.join(f'{r} {g} {b}' for r,g,b in row) + '\n')
