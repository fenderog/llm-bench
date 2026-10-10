import random

# Low-res pixel art grid
W, H = 60, 75
SCALE = 8
random.seed(7)

def lerp(a,b,t): return int(a+(b-a)*t)
def lerp3(c1,c2,t): return (lerp(c1[0],c2[0],t), lerp(c1[1],c2[1],t), lerp(c1[2],c2[2],t))

top_sky = (26, 32, 86)
mid_sky = (94, 70, 140)
horizon = (255, 150, 80)
ground_c = (24, 24, 38)
ground_c2 = (40, 36, 52)

cx = W//2
tower_top = 6
tower_bottom = 60
mid_plat_y = 34
top_plat_y = 18

def half_width(y):
    if y < tower_top or y > tower_bottom: return 0
    if y < top_plat_y-1:
        # spire + upper
        t = (y-tower_top)/(top_plat_y-1-tower_top)
        return 1 + t*2.2
    if y <= top_plat_y+1:
        return 6  # top platform
    if y < mid_plat_y:
        t=(y-top_plat_y-1)/(mid_plat_y-top_plat_y-2)
        return 3.2 + t*3.0
    if y <= mid_plat_y+2:
        return 10  # middle platform
    # lower section flares
    t=(y-mid_plat_y-2)/(tower_bottom-mid_plat_y-2)
    return 6.5 + t*t*11.5

def in_tower(x,y):
    hw = half_width(y)
    if hw==0: return False
    # platform wider bars
    if y in (top_plat_y, top_plat_y+1, mid_plat_y+1, mid_plat_y+2):
        return abs(x-cx) <= hw
    # antenna tip thin
    if y < 9:
        return abs(x-cx) <= 0.6
    return abs(x-cx) <= hw

def in_arch(x,y):
    # arch cutout: ellipse centered at (cx, tower_bottom)
    if y < 60: return False
    dx = abs(x-cx)
    dy = tower_bottom - y
    # arch shape: width shrinks near top
    # ellipse radii
    rx, ry = 8.5, 11
    v = (dx/rx)**2 + (dy/ry)**2
    if v < 1.0:
        # keep legs thickness: exclude if too close to tower edge? legs are thick
        # legs inner edge: ensure arch doesn't eat legs: legs occupy outer 3 px
        hw = half_width(y)
        if hw - dx >= 2.5:
            return True
    return False

# small side arch windows? skip

pixels = []
for y in range(H):
    row=[]
    for x in range(W):
        # sky / ground
        if y < 60:
            t = y/60
            if t < 0.55:
                c = lerp3(top_sky, mid_sky, t/0.55)
            else:
                c = lerp3(mid_sky, horizon, (t-0.55)/0.45)
            # dither checker for 16-bit vibe
            if (x+y)%2==0:
                c = (c[0]+4, c[1]+4, c[2]+4)
            # stars
            if y < 28 and random.random()<0.035:
                c = (255,255,220)
            # moon
            mx,my,mr = 47,12,4
            d=((x-mx)**2+(y-my)**2)**0.5
            if d<mr:
                c=(250,240,200)
            elif d<mr+1:
                c=(200,180,160)
            # distant city silhouette
            if y>=54 and y<60:
                bld = int(3*abs(__import__('math').sin(x*1.7))+2*abs(__import__('math').sin(x*0.53+2)))
                if y >= 60-bld:
                    c = (30,26,50)
                    if random.random()<0.12:
                        c=(255,200,100)
            # sun glow near horizon
            if y>50:
                glow = max(0,1-abs(x-30)/25)
                c=(min(255,int(c[0]+glow*30)),min(255,int(c[1]+glow*10)),c[2])
        else:
            # ground: dark with cobble dither + reflection
            c = lerp3(ground_c2, ground_c, (y-60)/(H-60))
            if (x*3+y*5)%7==0:
                c=(c[0]+8,c[1]+8,c[2]+10)
            # light reflection under tower
            if abs(x-cx)<8:
                c=(c[0]+20,c[1]+14,c[2]+6)
        row.append(c)
    pixels.append(row)

# draw tower
for y in range(H):
    for x in range(W):
        if not in_tower(x,y):
            continue
        if in_arch(x,y):
            continue
        hw = half_width(y)
        dx = abs(x-cx)
        edge = dx/hw if hw>0 else 0
        # base tower color: dark iron with warm lit side
        # left darker, right lit by sunset
        if x < cx:
            base=(58,44,40)
        else:
            base=(110,80,58)
        # outline dark
        if edge>0.82:
            base=(28,20,26)
        # horizontal girders
        if y%3==0:
            base=(max(0,base[0]-18),max(0,base[1]-14),max(0,base[2]-8))
        # cross bracing sparkle
        if (x+y)%4==0 and 20<y<60 and edge<0.8:
            base=(200,150,90)
        # beacon lights
        if (y%6==1 and edge<0.9) or (x==cx and y%2==0):
            base=(255,210,120)
        # platforms bright
        if y in (top_plat_y,top_plat_y+1,mid_plat_y+1,mid_plat_y+2):
            base=(255,190,110) if (x%2==0) else (180,110,60)
        # spire beacon
        if y==tower_top:
            base=(255,80,80)
        # legs shading
        if y>50 and not in_arch(x,y):
            # inner leg highlight
            pass
        pixels[y][x]=base

# searchlight beams from top
for y in range(tower_top, 30):
    pass # skip (keep clean)

# quantize to RGB565 (16-bit color)
def q565(c):
    r,g,b=c
    r=(r>>3)<<3 | (r>>3>>2)  # approx 5-bit: values 0..31 scaled
    # proper: 5bit then expand to 8bit
    r5=r>>3; g6=g>>2; b5=b>>3
    return ((r5*255)//31, (g6*255)//63, ((b5*255)//31))

for y in range(H):
    for x in range(W):
        pixels[y][x]=q565(pixels[y][x])

# upscale nearest
OW, OH = W*SCALE, H*SCALE
with open('/tmp/eiffel.ppm','wb') as f:
    f.write(f'P6\n{OW} {OH}\n255\n'.encode())
    for y in range(OH):
        sy=y//SCALE
        for x in range(OW):
            sx=x//SCALE
            f.write(bytes(pixels[sy][sx]))
print(f"wrote {OW}x{OH}")
