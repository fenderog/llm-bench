import subprocess

W, H = 64, 80
SCALE = 6  # upscale for pixel look
OW, OH = W*SCALE, H*SCALE

def q565(r,g,b):
    return (r & 0xF8, g & 0xFC, b & 0xF8)

def sky(y):
    # day-to-sunset gradient
    t = y/(H-1)
    r = int(135 + 60*t)
    g = int(180 - 20*t)
    b = int(220 - 40*t)
    return q565(r,g,b)

# ground
def ground_color(x,y):
    g = 90 + (x*3+y*2)%20
    return q565(85, g+30, 70)

cx = W//2

# tower params
# returns half-width of tower steel at height y
def half_width(y):
    # y in 0..H; tower from y_top=6 to y_base=70
    yt, yb = 6, 70
    if y < yt or y > yb: return None
    t = (y-yt)/(yb-yt)  # 0 top -> 1 base
    # exponential flare
    return 1 + 13*(t**1.8) + 2*t

platforms = [22, 42, 70]  # y rows of platforms
plat_half = [7, 11, 16]

buf = [[(0,0,0)]*W for _ in range(H)]

for y in range(H):
    for x in range(W):
        if y >= 70:
            c = ground_color(x,y)
        else:
            c = sky(y)
        buf[y][x]=c

# draw tower
for y in range(6,71):
    hw = half_width(y)
    for x in range(W):
        d = abs(x-cx)
        is_steel = d <= hw
        # arch cutout at bottom: parabolic arch
        if y >= 52:
            arch_h = y-52
            arch_hw = 3 + arch_h*0.55  # opening half width grows downward
            # center opening + two side openings
            if d < arch_hw and y > 55:
                # arch top curve: keep steel near top of arch
                top_curve = 55 + (d/arch_hw)*4 if arch_hw>0 else 55
                if y > top_curve:
                    is_steel = False
        # lattice holes: checker pattern to feel like ironwork
        if is_steel:
            # sky peeking through upper part
            if (x+y)%3==0 and y>30 and y<68 and d>1 and d<hw-0.5:
                # keep edges solid
                pass  # keep solid actually for visibility; add shading instead
            # shading: left light, right dark
            if x < cx:
                base=(176,132,84)
            elif x==cx:
                base=(200,155,100)
            else:
                base=(120,88,55)
            # cross-brace darkening
            if (x+y)%4==0:
                base=tuple(max(0,v-25) for v in base)
            buf[y][x]=q565(*base)

# platforms (dark brown bars)
for py,ph in zip(platforms, plat_half):
    for x in range(cx-ph, cx+ph+1):
        for dy in [0,1]:
            yy=py+dy
            if 0<=yy<H and 0<=x<W:
                buf[yy][x]=q565(60,40,25)
    # railing
    if py<70:
        for x in range(cx-ph, cx+ph+1):
            if x%2==0:
                buf[py-1][x]=q565(60,40,25)

# spire + antenna + beacon
for y in range(2,6):
    buf[y][cx]=q565(200,155,100)
buf[1][cx]=q565(255,220,150)

# sun / cloud pixels
for cy,cx2 in [(12,12),(15,50),(28,8)]:
    for dy in range(-2,3):
        for dx in range(-4,5):
            xx,yy=cx2+dx,cy+dy
            if 0<=xx<W and 0<=yy<H and abs(dx)+abs(dy)<5:
                if buf[yy][xx]==sky(yy):
                    buf[yy][xx]=q565(245,245,240)

# upscale nearest neighbor into PPM
with open('/tmp/eiffel.ppm','wb') as f:
    f.write(f'P6\n{OW} {OH}\n255\n'.encode())
    for y in range(H):
        for sy in range(SCALE):
            for x in range(W):
                r,g,b=buf[y][x]
                for sx in range(SCALE):
                    f.write(bytes((r,g,b)))

subprocess.run(['ffmpeg','-y','-f','image2','-i','/tmp/eiffel.ppm','-q:v','2','output/eiffel-16bit.jpg'],check=True)
print("done")
