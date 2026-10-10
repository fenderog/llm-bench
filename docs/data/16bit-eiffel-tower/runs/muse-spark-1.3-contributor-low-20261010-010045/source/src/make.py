import struct, zlib, os, math, random

W,H=256,224
random.seed(7)

# --- palette design: build list of RGB ---
pal=[]
def add(c):
    if c not in pal:
        pal.append(c)
    return pal.index(c)

# sky gradient top->horizon (y 0..175)
# interpolate through key stops
stops=[(0,(12,14,52)),(60,(28,36,98)),(110,(86,66,138)),(140,(214,114,110)),(160,(255,166,88)),(175,(255,208,140))]
def sky_color(y):
    for i in range(len(stops)-1):
        y0,c0=stops[i]; y1,c1=stops[i+1]
        if y<=y1:
            t=(y-y0)/max(1,(y1-y0))
            return tuple(int(c0[k]+(c1[k]-c0[k])*t) for k in range(3))
    return stops[-1][1]

sky_idx={}
SKYBANDS=36
sky_band_cols=[]
for b in range(SKYBANDS):
    y=int(b*(175/(SKYBANDS-1)))
    sky_band_cols.append(add(sky_color(y)))
for y in range(176):
    b=int(round(y/175*(SKYBANDS-1)))
    sky_idx[y]=sky_band_cols[b]

# other colors
C_STAR=add((255,255,240))
C_MOON=add((245,238,210)); C_MOON_D=add((210,195,170))
C_CLOUD_L=add((250,200,180)); C_CLOUD_M=add((190,140,170)); C_CLOUD_D=add((120,90,130))
C_CITY=add((22,20,48)); C_CITY2=add((32,30,62)); C_ROOF=add((45,34,70))
C_WIN=add((255,210,110)); C_WIN2=add((255,150,80))
C_GROUND=add((40,36,60)); C_GROUND2=add((58,50,80)); C_ROAD=add((30,28,50))
C_LAMP=add((255,220,130)); C_LAMPPOST=add((20,18,36))
# tower palette (bronze, lit)
TOWER=[(58,32,28),(86,50,40),(122,74,52),(160,104,66),(205,145,90),(240,190,130),(255,230,170),(40,22,24)]
TOW=[add(c) for c in TOWER]
C_SPARK=add((255,242,180))
C_DARKLINE=add((30,16,18))

print("base palette",len(pal))

# buffer of palette indices
buf=[[0]*W for _ in range(H)]

for y in range(H):
    for x in range(W):
        if y<176:
            buf[y][x]=sky_idx[y]
        elif y<196:
            buf[y][x]=C_GROUND
        else:
            buf[y][x]=C_ROAD

def setpx(x,y,c):
    if 0<=x<W and 0<=y<H:
        buf[y][x]=c

# stars (top 90 rows)
for _ in range(120):
    x=random.randrange(W); y=random.randrange(75)
    # fade by y
    if random.random()<0.8:
        setpx(x,y,C_STAR)
        if random.random()<0.3:
            setpx(x+1,y,C_STAR)

# moon at (200,40) r10
mx,my,mr=200,38,11
for y in range(my-mr-2,my+mr+3):
    for x in range(mx-mr-2,mx+mr+3):
        d=math.hypot(x-mx,y-my)
        if d<mr:
            setpx(x,y,C_MOON)
        elif d<mr+1.5:
            setpx(x,y,C_CLOUD_M)
# moon shading craters
for (ox,oy,r) in [(-3,-2,3),(3,2,2),(0,5,2)]:
    for y in range(my+oy-r,my+oy+r+1):
        for x in range(mx+ox-r,mx+ox+r+1):
            if math.hypot(x-(mx+ox),y-(my+oy))<r:
                setpx(x,y,C_MOON_D)

# clouds: a few puffy ellipses
def cloud(cx,cy,s):
    for y in range(cy-8*s//4,cy+6):
        for x in range(cx-30*s//4,cx+30*s//4):
            ex=(x-cx)/(22*s/4); ey=(y-cy)/(6*s/4)
            n=math.sin(x*0.7)*0.15+math.sin(x*0.23+y*0.5)*0.15
            if ex*ex+ey*ey+n<1:
                # top highlight
                if y<cy-1: c=C_CLOUD_L
                elif y<cy+2: c=C_CLOUD_M
                else: c=C_CLOUD_D
                setpx(x,y,c)
cloud(55,70,4); cloud(150,95,3); cloud(215,110,4); cloud(70,120,3); cloud(30,55,2)

# distant city silhouette y 150..190
for x in range(W):
    h=8+int(6*math.sin(x*0.11)+4*math.sin(x*0.031+2)+3*math.sin(x*0.21))
    # mansard roofs occasional
    roof = (x%37)<10
    top=168-h
    for y in range(top,192):
        if y<top+3 and roof:
            # slanted roof
            setpx(x,y,C_ROOF)
        elif y<top+4:
            setpx(x,y,C_CITY2)
        else:
            setpx(x,y,C_CITY)
    # chimney
    if x%29==0:
        for y in range(top-6,top):
            setpx(x,y,C_CITY); setpx(x+1,y,C_CITY)
# windows lit
for _ in range(140):
    x=random.randrange(W); y=random.randrange(160,188)
    if buf[y][x]==C_CITY:
        setpx(x,y, C_WIN if random.random()<0.6 else C_WIN2)

# Haussmann foreground row darker y188..196
for x in range(W):
    for y in range(188,197):
        buf[y][x]=C_GROUND if (x+y)%2==0 else C_GROUND2
# street lamps foreground
for lx in [18,238]:
    for y in range(170,210):
        setpx(lx,y,C_LAMPPOST)
    setpx(lx-2,166,C_LAMPPOST);setpx(lx+2,166,C_LAMPPOST)
    for dx in range(-3,4):
        for dy in range(-2,3):
            if abs(dx)+abs(dy)<4:
                setpx(lx+dx,165+dy,C_LAMP)
    # glow
    for dx in range(-6,7):
        for dy in range(-5,6):
            if abs(dx)+abs(dy) in (5,6) and 0<=lx+dx<W:
                if buf[165+dy][lx+dx] not in (C_LAMP,):
                    pass

# ---- Eiffel tower ----
cx=128
def half_width(y):
    # y from 30..208
    if y<45: return 2
    if y<75: return 5+(y-45)*(7/30)   # 5..12
    if y<82: return 15
    if y<130: return 15+(y-82)*(17/48) #15..32
    if y<139: return 36
    if y<208: return 36+(y-139)*(14/69) #36..50
    return 50

for y in range(28,210):
    hw=half_width(y)
    for x in range(int(cx-hw),int(cx+hw)+1):
        # arch cutout for lower part
        if y>155:
            # parabolic arch: opening half width
            t=(y-155)/55.0  #0..1
            arch_hw= 8+ t*28  # widens downward? actually narrows upward
            # arch top curve
            arch_top=158+ (abs(x-cx)/34.0)**1.6*45
            if abs(x-cx)<arch_hw and y>arch_top:
                continue  # sky/city shows through
        # platforms: solid bars
        dx=x-cx
        # shading across width: left highlight, right shadow
        f=dx/hw if hw>0 else 0  # -1..1
        if abs(dx)>hw-1.5:
            c=TOW[0]  # edge dark
        elif f<-0.5: c=TOW[5]
        elif f<-0.15: c=TOW[4]
        elif f<0.3: c=TOW[3]
        elif f<0.65: c=TOW[2]
        else: c=TOW[1]
        # horizontal girder bands every 8px darker
        if y%8==6 or y%8==7:
            # darken one step
            c=TOW[max(0,TOW.index(c)-1)]
        setpx(x,y,c)
    # platform slabs
    if y in (78,79,80,81,82,133,134,135,136,137,138):
        for x in range(int(cx-hw-4),int(cx+hw+5)):
            if 0<=x<W:
                setpx(x,y, TOW[0] if y%2==0 else TOW[1])
        # platform lights row
        if y==78 or y==133:
            for x in range(int(cx-hw-4),int(cx+hw+5),3):
                setpx(x,y-1,C_SPARK)

# lattice cross-hatch
for y in range(46,208):
    hw=half_width(y)
    if 76<=y<=82 or 130<=y<=139: continue
    for x in range(int(cx-hw)+1,int(cx+hw)):
        if abs(x-cx)<2: continue
        # skip arch hole (already sky)
        # diagonal pattern
        if (x+y)%7==0 or (x-y)%7==0:
            # only on tower pixels
            if buf[y][x] in TOW[1:]:
                setpx(x,y,C_DARKLINE)
        # vertical struts
        if (x-cx)%9==0:
            if buf[y][x] in TOW[1:]:
                setpx(x,y,TOW[0])

# arch outline highlight
for y in range(155,209):
    hw=half_width(y)
    t=(y-155)/55.0
    arch_hw=8+t*28
    arch_top=158+(arch_hw/34.0)**1.6*45
    for sx in (-1,1):
        ax=int(cx+sx*arch_hw)
        ay=int(158+(abs(ax-cx)/34.0)**1.6*45 + (y-ay if False else 0))
        # draw edge along arch curve: for each y find edge x? simpler: highlight pixels adjacent to hole
        pass

# beacon + sparkles on tower
setpx(cx,27,C_SPARK); setpx(cx,26,C_STAR)
for _ in range(90):
    y=random.randrange(45,205)
    hw=half_width(y)
    x=int(cx+random.uniform(-hw+1,hw-1))
    if buf[y][x] in (TOW+[C_DARKLINE]+[TOW[0]]):
        if random.random()<0.5:
            setpx(x,y,C_SPARK)

# ground shadow under tower
for x in range(int(cx-55),int(cx+56)):
    d=abs(x-cx)/55.0
    for y in range(208,216):
        if random.random()>d:
            if buf[y][x] in (C_ROAD,C_GROUND,C_GROUND2):
                setpx(x,y,C_LAMPPOST)

# scanline-ish? no.

# --- verify constraints ---
colors=set()
for row in buf:
    colors.update(row)
print("total colors:",len(colors))
maxt=0
bad=[]
for ty in range(H//8):
    for tx in range(W//8):
        s=set()
        for y in range(ty*8,ty*8+8):
            for x in range(tx*8,tx*8+8):
                s.add(buf[y][x])
        maxt=max(maxt,len(s))
        if len(s)>16:
            bad.append((tx,ty,len(s)))
print("max per tile:",maxt,"bad tiles:",len(bad),bad[:10])

# --- write PNG (8-bit colormap) ---
pal_rgb=[(0,0,0)]*len(pal)
for i,c in enumerate(pal):
    pal_rgb[i]=c
# pad to 256? not needed; use PLTE with len
raw=bytearray()
for y in range(H):
    raw.append(0)
    raw.extend(buf[y])
# remap indices <256 fine (len<128)
def chunk(t,d):
    c=t+d; return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(c)&0xffffffff)
plte=bytearray()
for (r,g,b) in pal_rgb: plte.extend([r,g,b])
ihdr=struct.pack(">IIBBBBB",W,H,8,3,0,0,0)
png=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",ihdr)+chunk(b"PLTE",bytes(plte))+chunk(b"IDAT",zlib.compress(bytes(raw),9))+chunk(b"IEND",b"")
os.makedirs("output",exist_ok=True)
open("output/eiffel-snes.png","wb").write(png)
print("wrote",len(png),"bytes")
