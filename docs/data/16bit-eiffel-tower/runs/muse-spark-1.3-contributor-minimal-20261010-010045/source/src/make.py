import struct, zlib, math, os, random

W,H=256,224
random.seed(7)

# --- Palette: build <=128 colors ---
# Sky gradient dusk: 24 steps top #0a1038 to horizon #ff9a4a etc.
def lerp(c1,c2,t):
    return tuple(int(a+(b-a)*t) for a,b in zip(c1,c2))

top=(16,16,64); mid1=(48,48,128); mid2=(120,80,150); hor=(255,154,74)
sky=[]
for i in range(24):
    t=i/23
    if t<0.5: c=lerp(top,mid1,t*2)
    elif t<0.8: c=lerp(mid1,mid2,(t-0.5)/0.3)
    else: c=lerp(mid2,hor,(t-0.8)/0.2)
    sky.append(c)

pal=list(sky)  # 0..23
# extra colors
extras=[
 (255,230,160), # sun 24
 (255,250,220), # sun hi 25
 (235,200,170), # cloud light 26
 (160,130,170), # cloud shadow 27
 (90,80,130),   # cloud dark 28
 (40,36,80),    # distant bldg 29
 (60,52,100),   # distant bldg2 30
 (30,28,60),    # roof 31
 (20,40,30),    # grass dark 32
 (44,110,52),   # grass 33
 (80,160,70),   # grass light 34
 (120,200,90),  # grass hi 35
 (90,70,50),    # path 36
 (150,120,80),  # path light 37
 (200,170,120), # path hi 38
 (25,20,40),    # tower dark 39
 (55,40,60),    # tower base 40
 (95,70,80),    # tower mid 41
 (150,110,100), # tower light 42
 (220,170,130), # tower highlight 43
 (255,210,160), # tower lamp glow 44
 (250,220,80),  # lamp yellow 45
 (120,90,40),   # trunk 46
 (30,80,40),    # tree dark 47
 (50,130,60),   # tree 48
 (10,10,30),    # bird 49
 (230,230,240), # window lit 50
 (140,140,180), # window dark 51
 (15,15,35),    # night topper 52
 (200,120,90),  # horizon glow 53
 (70,60,110),   # fence 54
 (0,0,0),       # black 55
]
pal.extend(extras)
assert len(pal)<=128, len(pal)
def nearest_idx(c):
    best=0;bd=1e9
    for i,p in enumerate(pal):
        d=(c[0]-p[0])**2+(c[1]-p[1])**2+(c[2]-p[2])**2
        if d<bd: bd=d;best=i
    return best

# pixel buffer of palette indices
idx=[[0]*W for _ in range(H)]

def setp(x,y,pi):
    if 0<=x<W and 0<=y<H: idx[y][x]=pi

# sky gradient by y: horizon at y=150
for y in range(H):
    if y<=150:
        t=y/150
        si=int(t*23)
        pi=si
        for x in range(W): idx[y][x]=pi
    else:
        for x in range(W): idx[y][x]=33

# sun
sx,sy=196,118
for y in range(sy-16,sy+17):
    for x in range(sx-20,sx+21):
        dx=(x-sx)/20; dy=(y-sy)/16
        d=dx*dx+dy*dy
        if d<=1:
            if d<0.35: setp(x,y,25)
            elif d<0.8: setp(x,y,24)
            else: setp(x,y,53)

# clouds: few ellipses with dither
clouds=[(50,40,34,8),(120,60,40,9),(200,45,30,7),(70,90,36,7),(160,85,44,8)]
for cx,cy,rx,ry in clouds:
    for y in range(cy-ry,cy+ry+1):
        for x in range(cx-rx,cx+rx+1):
            dx=(x-cx)/rx; dy=(y-cy)/ry
            if dx*dx+dy*dy<=1:
                if y<cy-1: setp(x,y,26)
                elif y<cy+2:
                    setp(x,y,26 if (x+y)%2==0 else 27)
                else: setp(x,y,27 if (x+y)%2==0 else 28)

# birds
for bx,by in [(90,50),(100,55),(150,40),(155,46)]:
    setp(bx,by,49); setp(bx+1,by-1,49); setp(bx+2,by,49); setp(bx-1,by-1,49)

# distant city silhouette y 130..152
for x in range(W):
    h=8+int(6*math.sin(x*0.11)+4*math.sin(x*0.031+2))
    topy=150-h
    for y in range(topy,152):
        if idx[y][x]<24 or idx[y][x]==53:
            # mansard roofs
            if y==topy: setp(x,y,31)
            elif y<topy+3: setp(x,y,29)
            else: setp(x,y,30 if (x+y)%2==0 else 29)
    # windows
    if x%8==3:
        for wy in [topy+5,topy+8]:
            if 0<=wy<152: setp(x,wy,50 if (x+wy)%3==0 else 51)

# ground: grass with checker dither, path leading to tower
for y in range(152,H):
    for x in range(W):
        base=33
        if (x*3+y*7)%5==0: base=34
        if (x+y)%11==0: base=32
        # central path trapezoid widening
        cxd=abs(x-128)
        half=10+(y-152)*0.55
        if cxd<half:
            if (x+y)%2==0: base=37
            else: base=36
            if cxd<half-3: base=38 if (x+y)%2==0 else 37
            # path edge
            if abs(cxd-half)<1.2: base=32
        setp(x,y,base)

# trees rows
def tree(tx,ty,s):
    for y in range(ty-s,ty+1):
        w=int((y-(ty-s))/s*s*0.7)+1
        for x in range(tx-w,tx+w+1):
            if abs(x-tx)<w*0.7 or random.random()<0.5:
                c=48 if (x+y)%2==0 else 47
                if y<ty-s+3 and (x+y)%2==0: c=35
                setp(x,y,c)
    for y in range(ty+1,ty+4):
        setp(tx,y,46); setp(tx+1,y,46)
for tx in [20,45,70,185,210,235]:
    tree(tx,170+int(5*math.sin(tx)),10)
for tx in [12,60,195,244]:
    tree(tx,190,12)

# ---- Eiffel tower ----
# tower spans y 40..200 base width profile
def half_width(y):
    # y 40 top .. 200 bottom
    t=(y-40)/160  # 0 top 1 bottom
    if t<0.08: return 3+t*30  # spire flare
    elif t<0.55: return 5.4+ (t-0.08)*38  # shaft widening
    else: return 23.2+ (t-0.55)*110  # arch flare to ~72
    # tuned

spire_top=38
tower_dark=39; tower_base=40; tower_mid=41; tower_light=42; tower_hi=43
for y in range(spire_top,202):
    hw=half_width(y)
    # floors
    is_floor = y in (72,118,158)
    fh=4 if y in (72,118) else 5
    for x in range(int(128-hw-3), int(128+hw+4)):
        dx=abs(x-128)
        if dx>hw: continue
        # arch cutouts at bottom
        if y>158:
            # big arch
            arch_hw=(y-158)*1.55
            arch_top=158+ (dx*0.35)
            if dx<arch_hw and y>arch_top+6:
                continue  # see through
        elif y>118:
            # smaller arch openings lattice: two side cutouts
            if y>140:
                # two arches
                for cx in [128-16,128+16]:
                    if abs(x-cx)<9 and y>150-(9-abs(x-cx))*0.8:
                        # leave pillar
                        if not (abs(x-(128-23))<3 or abs(x-(128+23))<3 or abs(x-128)<3):
                            pass
                pass
        # base color by side shading: left dark, center mid, right light
        if dx>hw-2: c=tower_dark
        elif x<124: c=tower_base
        elif x<128: c=tower_mid
        elif x<132: c=tower_light
        else: c=tower_mid
        # cross-brace dither lattice
        if not is_floor and (x+y)%3==0 and y>72: c=tower_dark
        if (x-y)%5==0 and y>50 and y<155: 
            # highlight strut
            if x>=128: c=tower_hi if c in (tower_light,tower_mid) else c
        # beacon
        setp(x,y,c)
    if is_floor:
        for x in range(int(128-hw-4),int(128+hw+5)):
            if abs(x-128)<=hw+4:
                setp(x,y,tower_dark)
                setp(x,y+1,45 if (x%4<2) else tower_hi)  # lit railing
                if fh>4: setp(x,y+2,tower_dark)

# spire antenna + beacon
for y in range(30,spire_top+1):
    setp(128,y,tower_dark)
    setp(129,y,tower_mid)
setp(128,28,44); setp(127,29,45); setp(129,29,45)
# glow around beacon
for dx,dy in [(-2,0),(2,0),(0,2),(0,-2)]: setp(128+dx,28+dy,24)

# tower searchlight beams (subtle)
for i in range(40):
    x1=128-i; y1=28-i//2
    setp(x1,y1,26 if i%2==0 else idx[y1][x1])
    x2=128+i; y2=28-i//2
    if 0<=x2<W and y2>=0: setp(x2,y2,26 if i%2==0 else idx[y2][x2])

# lamps along path
for lx,ly in [(100,175),(156,175),(90,195),(166,195)]:
    setp(lx,ly,45); setp(lx,ly-3,54); setp(lx,ly-2,54); setp(lx,ly-1,44)

# fence
for x in range(0,W):
    if 158<=152+0: pass
for y in [160,162]:
    for x in range(W):
        cxd=abs(x-128); half=10+(160-152)*0.55
        if cxd>half+2 and x%4!=0:
            if 158<=y<=163: setp(x,y,54)

# --- enforce per-tile 16 colors ---
for ty in range(0,H,8):
    for tx in range(0,W,8):
        cols={}
        for y in range(ty,min(ty+8,H)):
            for x in range(tx,min(tx+8,W)):
                cols[idx[y][x]]=cols.get(idx[y][x],0)+1
        if len(cols)>16:
            top16=sorted(cols,key=cols.get,reverse=True)[:16]
            topRGB=[pal[i] for i in top16]
            for y in range(ty,min(ty+8,H)):
                for x in range(tx,min(tx+8,W)):
                    v=idx[y][x]
                    if v not in top16:
                        c=pal[v]
                        bi=min(range(16),key=lambda i:(c[0]-topRGB[i][0])**2+(c[1]-topRGB[i][1])**2+(c[2]-topRGB[i][2])**2)
                        idx[y][x]=top16[bi]

# count colors
used=sorted({v for row in idx for v in row})
print("colors used:",len(used))
# remap to 0..n for PNG? keep full palette but fine (PLTE len = len(pal))
# write PNG indexed
raw=bytearray()
for y in range(H):
    raw.append(0)
    raw.extend(idx[y][x] for x in range(W))
comp=zlib.compress(bytes(raw),9)
def chunk(t,d):
    c=t+d; return struct.pack(">I",len(d))+t+ d+struct.pack(">I",zlib.crc32(c)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'
png+=chunk(b'IHDR',struct.pack(">IIBBBBB",W,H,8,3,0,0,0))
plte=b''.join(bytes(p) for p in pal)
png+=chunk(b'PLTE',plte)
png+=chunk(b'IDAT',comp)
os.makedirs("output",exist_ok=True)
open("output/eiffel-snes.png","wb").write(png)
print("wrote output/eiffel-snes.png",len(png))
