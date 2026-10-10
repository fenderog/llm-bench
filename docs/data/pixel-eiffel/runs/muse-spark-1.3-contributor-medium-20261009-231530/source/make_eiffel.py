#!/usr/bin/env python3
"""16-bit color pixel-art Eiffel Tower -> PPM -> JPG via ffmpeg"""
import random

W, H = 64, 80
SCALE = 10  # upscale for chunky pixels
OUT_W, OUT_H = W*SCALE, H*SCALE

def rgb565_to_rgb8(r,g,b):
    r5 = r >> 3
    g6 = g >> 2
    b5 = b >> 3
    r8 = (r5*255+15)//31
    g8 = (g6*255+31)//63
    b8 = (b5*255+15)//31
    return (r8,g8,b8)

def Q(r,g,b):
    return rgb565_to_rgb8(r,g,b)

# buffers
img = [[(0,0,0) for _ in range(W)] for _ in range(H)]

# sky gradient: top deep blue to pale near horizon
top = (58, 122, 213)    # #3A7AD5
mid = (120, 180, 230)
hor = (200, 230, 244)   # pale
ground_y = 66

for y in range(H):
    if y < ground_y:
        t = y / ground_y
        if t < 0.5:
            k = t/0.5
            r = int(top[0]+(mid[0]-top[0])*k)
            g = int(top[1]+(mid[1]-top[1])*k)
            b = int(top[2]+(mid[2]-top[2])*k)
        else:
            k = (t-0.5)/0.5
            r = int(mid[0]+(hor[0]-mid[0])*k)
            g = int(mid[1]+(hor[1]-mid[1])*k)
            b = int(mid[2]+(hor[2]-mid[2])*k)
        c = Q(r,g,b)
        for x in range(W):
            img[y][x]=c
    else:
        # ground: grass + pavement
        img[y][x]=Q(90,160,90)

# ground detail: pavement strip + grass
for y in range(ground_y, H):
    for x in range(W):
        if y < ground_y+3:
            # pavement gray
            v = 150 + ((x+y)&1)*10
            img[y][x]=Q(v, v-5, v-10)
        else:
            # grass with dither
            base_g = 105 + ((x*7+y*13)&15) - 8
            img[y][x]=Q(86, base_g+55, 72)

# sun (pixel circle top-right)
sun_cx, sun_cy, sun_r = 50, 14, 6
for y in range(H):
    for x in range(W):
        dx=x-sun_cx; dy=y-sun_cy
        d=dx*dx+dy*dy
        if d <= sun_r*sun_r:
            # warm yellow, quantized
            img[y][x]=Q(255, 225, 130)
        elif d <= (sun_r+1)*(sun_r+1):
            img[y][x]=Q(255, 240, 180)

# clouds: blocky pixel clouds
def cloud(cx, cy, s):
    # s scale
    blobs = [(-4,0,3),( -2,-1,3),(0,0,4),(3,0,3),(1,-1,2),(-1,1,2)]
    for bx,by,br in blobs:
        for y in range(cy-br, cy+br+1):
            for x in range(cx+bx*s-br, cx+bx*s+br+1):
                if 0<=x<W and 0<=y<ground_y:
                    dx=x-(cx+bx*s); dy=(y-cy)*1.6
                    if dx*dx+dy*dy <= br*br:
                        # white with slight shade at bottom
                        if y>cy+1:
                            img[y][x]=Q(220,228,238)
                        else:
                            img[y][x]=Q(245,248,252)

cloud(14, 12, 1)
cloud(38, 22, 1)
cloud(12, 32, 1)

random.seed(7)
# birds
for bx,by in [(22,18),(25,19),(44,30)]:
    img[by][bx]=Q(40,40,50)
    img[by][bx+2]=Q(40,40,50)
    img[by-1][bx+1]=Q(40,40,50)

# ---- Eiffel Tower ----
cx = 32
top_y = 8
bot_y = ground_y  # 66
tower_h = bot_y - top_y

# platform Y positions
# first floor (lower, near ground), second floor
y_first = top_y + int(tower_h*0.78)   # ~53
y_second = top_y + int(tower_h*0.55)  # ~39-40
y_third_small = top_y + int(tower_h*0.30) # small collar

def half_width(y):
    t = (y - top_y)/tower_h  # 0 top ->1 bottom
    w = 1 + 15.5*(t**1.75)
    return w

iron_dark = Q(46,32,24)
iron_mid = Q(107,74,48)
iron_light = Q(168,124,84)
iron_hl = Q(200,160,115)
platform_c = Q(42,28,22)
light_dot = Q(255,220,120)

for y in range(top_y, bot_y+1):
    hw = half_width(y)
    x0 = int(round(cx - hw))
    x1 = int(round(cx + hw))
    for x in range(x0, x1+1):
        if 0<=x<W:
            # side shading: left light, middle mid, right dark + lattice
            rel = (x - x0)/max(1,(x1-x0))  # 0..1
            if x==x0 or x==x1:
                c = iron_dark  # outline
            elif rel < 0.35:
                c = iron_light
            elif rel < 0.65:
                c = iron_mid
            else:
                c = iron_dark
            # lattice cross pattern: alternate X
            if (x+y)&1==0 and top_y+4 < y < y_first:
                # darken every other to suggest trusses, but keep outline
                if c==iron_mid:
                    c = iron_dark
                elif c==iron_light:
                    c = iron_mid
            # top spire thin: solid dark
            if y < top_y+6:
                c = iron_dark
            img[y][x]=c
    # outline darker 1px outside
    if 0<=x0-1<W:
        # keep sky unless tower already
        pass

# spire antenna
for y in range(top_y-4, top_y+1):
    img[y][cx]=iron_dark
    if y==top_y-4:
        img[y][cx]=Q(220,80,80)  # red beacon
    elif y==top_y-3:
        img[y][cx]=Q(255,255,255)

# beacon glow
img[top_y-4][cx-1]=Q(255,150,150)
img[top_y-4][cx+1]=Q(255,150,150)

# platforms (horizontal bars)
def platform(y, ext=2):
    hw = half_width(y)
    x0 = int(round(cx-hw))-ext
    x1 = int(round(cx+hw))+ext
    for x in range(x0, x1+1):
        if 0<=x<W:
            img[y][x]=platform_c
            if 0<=y+1<H:
                img[y+1][x]=iron_dark
    # railing
    if 0<=y-1<H:
        for x in range(x0, x1+1):
            if 0<=x<W and (x%2==0):
                img[y-1][x]=platform_c

platform(y_first, ext=3)
platform(y_second, ext=2)
# small collar near top
platform(y_third_small, ext=1)

# arch cutout: parabolic opening between legs from y_first+2 to bot
arch_top = y_first+2
for y in range(arch_top, bot_y+1):
    # arch half-width shrinks toward top
    k = (y - arch_top)/(bot_y - arch_top)  # 0 top 1 bottom
    # opening half width: wide at bottom (~9), narrow at top (~2)
    open_hw = 2 + 8*(k**0.8)
    for x in range(int(cx-open_hw), int(cx+open_hw)+1):
        if 0<=x<W:
            # arch edge highlight
            if abs(x-cx) >= open_hw-1:
                img[y][x]=iron_hl
            else:
                # background behind arch: show pavement/trees? use distant city + sky remnant
                # for lower part show street, for upper show sky/pavement
                if y >= bot_y-4:
                    v=150+((x+y)&1)*8
                    img[y][x]=Q(v,v-5,v-10)
                else:
                    # interior shade sky slightly darker
                    img[y][x]=Q(175,210,230)

# arch outline dark
# lights on tower (evening sparkle dots) – sparse yellow pixels on edges
for y in range(top_y+8, y_first, 4):
    hw = half_width(y)
    x0 = int(round(cx-hw)); x1=int(round(cx+hw))
    if 0<=x0<W: img[y][x0+1]=light_dot
    if 0<=x1<W: img[y][x1-1]=light_dot

# foreground trees (blocky)
def tree(tx, base_y, h=8):
    trunk_c=Q(90,60,35)
    leaf_c=Q(55,120,60)
    leaf_d=Q(40,95,50)
    for y in range(base_y-h, base_y):
        img[y][tx]=trunk_c
    for dy in range(h):
        y=base_y-h+dy-2
        wdt=3-dy//3
        for x in range(tx-wdt, tx+wdt+1):
            if 0<=x<W and 0<=y<H:
                img[y][x]=leaf_c if (x+y)&1 else leaf_d

tree(8, ground_y+6, 10)
tree(13, ground_y+5, 7)
tree(54, ground_y+6, 9)
tree(49, ground_y+5, 6)

# lamp posts
for lx in [20, 44]:
    for y in range(ground_y-6, ground_y+1):
        img[y][lx]=Q(30,30,30)
    img[ground_y-7][lx]=Q(255,230,150)
    img[ground_y-7][lx-1]=Q(255,230,150)
    img[ground_y-6][lx-1]=Q(80,80,60)
    img[ground_y-6][lx+1]=Q(80,80,60)

# upscale nearest neighbor
big = [[None]*OUT_W for _ in range(OUT_H)]
for y in range(H):
    for x in range(W):
        c = img[y][x]
        for dy in range(SCALE):
            for dx in range(SCALE):
                big[y*SCALE+dy][x*SCALE+dx]=c

# write PPM P6
with open("tmp_eiffel.ppm","wb") as f:
    f.write(f"P6\n{OUT_W} {OUT_H}\n255\n".encode())
    for row in big:
        for (r,g,b) in row:
            f.write(bytes((r,g,b)))
print(f"wrote tmp_eiffel.ppm {OUT_W}x{OUT_H}")
