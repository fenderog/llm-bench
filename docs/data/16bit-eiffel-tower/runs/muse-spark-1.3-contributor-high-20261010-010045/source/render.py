#!/usr/bin/env python3
"""SNES-style Eiffel Tower pixel art, 256x224, <=128 colors, 8x8 tiles <=16 colors."""
import struct, zlib, math, random

W, H = 256, 224
HORIZON = 176

# ---------- palette helpers ----------
# We only ever use colors from this explicit set (no blending creates new ones).
def lerp(a,b,t): return int(round(a+(b-a)*t))

TOP = (16,20,68)
MID = (86,64,148)
BOT = (255,170,110)

SKY = []
for i in range(16):
    t = i/15.0
    if t < 0.55:
        u = t/0.55
        c = (lerp(TOP[0],MID[0],u), lerp(TOP[1],MID[1],u), lerp(TOP[2],MID[2],u))
    else:
        u = (t-0.55)/0.45
        c = (lerp(MID[0],BOT[0],u), lerp(MID[1],BOT[1],u), lerp(MID[2],BOT[2],u))
    SKY.append(c)

WHITE   = (248,248,248)
MOON    = (255,242,176)
MOONSH  = (232,200,106)
DARKBLUE= (32,32,64)
CLOUDPK = (232,180,180)
CLOUDSH = (120,90,120)
CITY    = (42,42,84)
CITYDK  = (28,28,60)
ROOF    = (62,52,92)
LITWIN  = (255,210,110)
GLASS   = (255,240,180)
GRASS1  = (30,90,44)
GRASS2  = (44,122,58)
GRASSDK = (20,62,32)
GRASSLI = (70,150,70)
PATH1   = (138,122,100)
PATH2   = (104,90,74)
PATHLI  = (170,154,132)
PATHDK  = (60,50,50)
OUTL    = (24,12,8)
TSHADOW = (74,42,26)
TBASE   = (122,74,42)
TMID    = (168,106,62)
TLIT    = (216,150,90)
THILITE = (255,216,150)
LATTICE = (46,24,14)
PLATDK  = (36,20,14)
CONC    = (110,110,120)
CONCDK  = (70,70,80)
TRUNK   = (80,50,30)
LEAFDK  = (22,70,36)
LEAF    = (34,110,52)
LEAFLI  = (62,150,72)
LEAFOUT = (12,36,20)
POST    = (20,20,30)
BEACON  = (255,80,80)
BIRD    = (30,30,50)

img = [[(0,0,0) for _ in range(W)] for _ in range(H)]

def put(x,y,c):
    if 0<=x<W and 0<=y<H:
        img[y][x]=c

# ---------- SKY ----------
for y in range(HORIZON):
    f = y/(HORIZON-1)*15.0
    i0 = int(f)
    if i0>=15: i0=14; frac=1.0
    else: frac = f-i0
    for x in range(W):
        # ordered dither on transitions for SNES gradient dither feel
        use_next = 0
        if frac>0.02:
            # 2px tall dither band near boundary
            if frac>0.5 and ((x+y)&1)==0:
                use_next=1
            elif frac>0.75 and ((x+y+1)&1)==0:
                use_next=1
            # also general grain
            if frac>0.9:
                use_next=1
        idx = min(15,i0+use_next)
        put(x,y,SKY[idx])

# stars (top only)
rnd = random.Random(7)
for _ in range(90):
    x = rnd.randrange(0,W); y = rnd.randrange(0,62)
    # twinkle pattern: skip some
    if img[y][x]==SKY[0] or img[y][x]==SKY[1] or img[y][x]==SKY[2]:
        put(x,y,WHITE)
        if rnd.random()<0.25 and x+1<W:
            # tiny cross sparkle uses same white
            pass
# a few 2px stars
for (sx,sy) in [(30,12),(90,28),(150,15),(210,60),(60,40),(180,45)]:
    put(sx,sy,WHITE); put(sx+1,sy,WHITE)

# ---------- MOON ----------
mx,my,mr = 202,34,14
for dy in range(-mr-2,mr+3):
    for dx in range(-mr-2,mr+3):
        d2 = dx*dx+dy*dy
        x,y = mx+dx,my+dy
        if d2<=mr*mr:
            if dx<-2: put(x,y,MOONSH)
            elif dx>4 and dy<-2: put(x,y,WHITE)
            else: put(x,y,MOON)
        elif d2<=(mr+1)*(mr+1):
            put(x,y,DARKBLUE)
# craters
for (cx,cy,cr) in [(-4,-2,3),(3,3,2),(5,-5,2)]:
    for dy in range(-cr,cr+1):
        for dx in range(-cr,cr+1):
            if dx*dx+dy*dy<=cr*cr:
                put(mx+cx+dx,my+cy+dy,MOONSH)
# halo: 1px dotted ring using pink cloud color (checker)
for a in range(0,360,4):
    rr=mr+4
    x=int(mx+rr*math.cos(math.radians(a))); y=int(my+rr*math.sin(math.radians(a))*0.9)
    if (x+y)&1==0:
        if 0<=x<W and 0<=y<H and img[y][x] in SKY:
            put(x,y,CLOUDPK)

# ---------- CLOUDS (SNES blocky) ----------
def cloud(cx,cy,scale):
    w=int(30*scale); h=int(9*scale)
    for dy in range(-h-4,h+4):
        for dx in range(-w-4,w+5):
            nx=dx/(w+0.5); ny=dy/(h+0.5)
            m=nx*nx+ny*ny*1.6
            x=cx+dx; y=cy+dy
            if m<=1.0:
                if dy>=h-2: put(x,y,CLOUDSH)
                elif dy>=h-4: put(x,y,CLOUDPK)
                elif dy<=-2: put(x,y,WHITE)
                else: put(x,y,CLOUDPK)
            elif m<=1.3 and dy>=-1:
                put(x,y,DARKBLUE)
    for dx in range(-w,w+1):
        put(cx+dx,cy+h+1, DARKBLUE)
    # puff tops merged: bright caps
    for (px,py,pw,ph) in [(-w//2,-h-3,10,4),(0,-h-5,12,5),(w//2,-h-3,9,4)]:
        for dy in range(ph):
            for dx in range(pw):
                x=cx+px+dx; y=cy+py+dy
                if dy==ph-1 and (dx in (0,pw-1)): continue
                put(x,y,WHITE)
        # outline top of puff
        for dx in range(pw):
            if (cx+px+dx+cy+py)&1==0: pass
    # underside dither between pink and shadow
    for dx in range(-w+2,w-1):
        if (dx&1)==0:
            put(cx+dx,cy+h-2,CLOUDSH)

cloud(52,52,1.0)
cloud(150,72,0.8)
cloud(84,98,0.6)
cloud(215,86,0.55)

# birds
for (bx,by,s) in [(120,40,1),(128,43,1),(70,70,1),(170,50,1)]:
    put(bx-s,by-1,BIRD); put(bx,by,BIRD); put(bx+s,by-1,BIRD)

# ---------- DISTANT PARIS SKYLINE ----------
# base fill behind
for y in range(146,HORIZON):
    for x in range(W):
        put(x,y,CITYDK)
# buildings
brnd = random.Random(21)
x=0
while x<W:
    bw = brnd.choice([18,22,26,30,16,24])
    bh = brnd.choice([16,20,24,28,18,22])
    top = HORIZON-bh
    # facade
    for y in range(top,HORIZON):
        for xx in range(x,min(W,x+bw)):
            put(xx,y,CITY)
    # mansard roof
    for ry in range(5):
        y=top-5+ry
        inset=ry//2
        for xx in range(x+inset,min(W,x+bw-inset)):
            put(xx,y,ROOF)
    # chimneys
    for chx in [x+3,x+bw-4]:
        for yy in range(top-9,top-4):
            put(chx,yy,CITY); put(chx+1,yy,CITY)
    # lit windows grid
    for wy in range(top+3,HORIZON-3,5):
        for wx in range(x+3,x+bw-2,5):
            if brnd.random()<0.45:
                put(wx,wy,LITWIN); put(wx+1,wy,LITWIN)
            else:
                put(wx,wy,CITYDK)
    # roof outline
    for xx in range(x,min(W,x+bw)):
        put(xx,top-5,DARKBLUE)
    x+=bw+brnd.choice([2,4,6])
# distant Sacre-Coeur-ish dome left
for dx in range(-16,17):
    for dy in range(-12,1):
        if dx*dx+dy*dy*2<=140:
            put(28+dx,158+dy,CITY)
put(28,144,CITY); put(28,145,CITY)
# horizon glow line
for x in range(W):
    put(x,HORIZON-1, CLOUDPK)
    put(x,HORIZON-2, CLOUDPK if (x&1)==0 else CITY)

# ---------- GROUND ----------
for y in range(HORIZON,H):
    for x in range(W):
        # checker dither grass
        if ((x+y)&1)==0: put(x,y,GRASS1)
        else: put(x,y,GRASS2)
        # darker at very horizon (shadow)
        if y<HORIZON+3: put(x,y,GRASSDK)
# grass texture speckles
grnd = random.Random(99)
for _ in range(500):
    x=grnd.randrange(0,W); y=grnd.randrange(HORIZON+4,H)
    put(x,y,GRASSDK if (x+y)&1 else GRASSLI)

# path trapezoid to tower
for y in range(HORIZON, H):
    t=(y-HORIZON)/(H-HORIZON)  # 0..1
    hw=int(38+52*t)  # 38 -> 90
    cx=128
    for x in range(cx-hw,cx+hw+1):
        if 0<=x<W:
            # cobble base with checker
            if ((x//4+y//3)&1)==0: put(x,y,PATH1)
            else: put(x,y,PATH2)
            # center lighter
            if abs(x-cx)<hw*0.5 and ((x+y)&1)==0:
                put(x,y,PATHLI)
# cobble lines
for y in range(HORIZON+2,H,5):
    t=(y-HORIZON)/(H-HORIZON); hw=int(38+52*t)
    for x in range(128-hw,128+hw+1):
        if ((x+y)&3)==0:
            put(x,y,PATHDK)
for yy in range(HORIZON,H):
    t=(yy-HORIZON)/(H-HORIZON); hw=int(38+52*t)
    # side borders
    for x in [128-hw,128+hw]:
        for dy in range(2):
            put(x,yy,PATHDK)
# path edge grass shadow
for y in range(HORIZON,H):
    t=(y-HORIZON)/(H-HORIZON); hw=int(38+52*t)
    put(128-hw-1,y,GRASSDK); put(128+hw+1,y,GRASSDK)

# ---------- TREES (behind tower, in front of city) ----------
def tree(tx, base_y, s):
    # trunk
    for y in range(base_y-int(26*s), base_y+1):
        for dx in range(-1,2):
            put(tx+dx,y,TRUNK)
        put(tx-2,y,OUTL if (y&1)==0 else TRUNK)
        put(tx+2,y,OUTL if (y&1)==0 else TRUNK)
    # canopy: 3 stacked blobs
    blobs=[(0,-30,16),( -10,-20,12),(10,-20,12),(0,-12,14)]
    for (ox,oy,r) in blobs:
        r=int(r*s)
        cxp=tx+int(ox*s); cyp=base_y+int(oy*s)
        for dy in range(-r,r+1):
            for dx in range(-r,r+1):
                if dx*dx+dy*dy<=r*r:
                    x=cxp+dx; y=cyp+dy
                    # outline
                    if dx*dx+dy*dy>=r*r-4:
                        put(x,y,LEAFOUT)
                    elif dx< -r//3 or dy> r//3:
                        put(x,y,LEAFDK)
                    elif dx> r//4 and dy<0:
                        put(x,y,LEAFLI)
                    else:
                        # dither leaf
                        put(x,y,LEAF if ((x+y)&1)==0 else LEAFDK)
    # highlight dots
    put(tx-6,base_y-int(28*s),LEAFLI); put(tx+5,base_y-int(32*s),LEAFLI)

tree(28,196,1.1)
tree(228,196,1.1)
tree(52,188,0.7)
tree(204,188,0.7)

# ---------- EIFFEL TOWER ----------
CX=128
BASE_Y=194

def half_w(y):
    if y>=148:
        t=(y-148)/(194-148)
        return int(44+12*t+4*t*t)
    elif y>=101:
        t=(y-101)/(148-101)
        return int(26+18*t)
    elif y>=53:
        t=(y-53)/(101-53)
        return int(12+14*t)
    else:
        t=max(0,(y-18)/(53-18))
        return int(3+9*t)

def in_arch(x,y):
    if 156<=y<=194:
        aw=int(44*math.sqrt(max(0,(y-156)/38.0)))
        if abs(x-CX)<=aw:
            return True, abs(abs(x-CX)-aw)<=1
    return False, False

# draw body rows bottom-up
for y in range(24, BASE_Y+1):
    w=half_w(y)
    for x in range(CX-w-1, CX+w+2):
        inside = abs(x-CX)<=w
        edge = abs(abs(x-CX)-w)<=0  # exact edge
        outer = abs(x-CX)==w+1
        arch_void, arch_edge = in_arch(x,y)
        if arch_void and not arch_edge:
            continue  # leave background (path/sky)
        if outer or arch_edge:
            put(x,y,OUTL)
            continue
        if not inside:
            continue
        # shading across width
        nx=(x-(CX-w))/(max(1,2*w))  # 0..1
        if nx<0.22: base=TSHADOW
        elif nx<0.55: base=TBASE
        elif nx<0.78: base=TMID
        elif nx<0.93: base=TLIT
        else: base=THILITE
        # right-edge 1px highlight line
        if x==CX+w: base=THILITE
        if x==CX-w: base=TSHADOW
        # horizontal shadow under platforms
        if y in (139,140,141,95,96,49,50):
            base=TSHADOW
        # lattice X pattern (skip on platforms zone & spire)
        if 55<=y<=192 and y not in range(138,150) and y not in range(94,103) and y not in range(48,56):
            a=(x+y)%8; b=(x-y)%8
            if a<2 or b<2:
                # darken one step
                if base==THILITE: base=TLIT
                elif base==TLIT: base=TMID
                elif base==TMID: base=TBASE
                elif base==TBASE: base=TSHADOW
                else: base=LATTICE
            elif a==7 or b==7:
                # rivet highlight dots occasionally
                if ((x*3+y*5)&7)==0:
                    base=THILITE
        # floodlight warm glow on lower front: dither toward lit
        if y>150 and nx>0.4 and nx<0.8 and ((x+y)&3)==0:
            if base==TBASE: base=TMID
            elif base==TSHADOW: base=TBASE
        # arch inner glow
        if 156<=y<=194 and abs(abs(x-CX)- (int(44*math.sqrt(max(0,(y-156)/38.0)))+2))<=0:
            base=THILITE
        # horizontal girder bands every 14px for structural feel
        if (y%14)==4 and 55<=y<=192:
            if base in (TBASE,TMID): base=TSHADOW
            elif base==TLIT: base=TMID
        put(x,y,base)

# feet concrete blocks
for fx in [CX-half_w(192), CX+half_w(192)]:
    for dy in range(0,7):
        for dx in range(-8,9):
            y=188+dy; x=fx+dx if fx<CX else fx+dx
            # for right foot fx is right side; block centered on leg center
            # leg center approx CX-w+8 / CX+w-8 ; adjust
            pass
# simpler: two concrete pads under legs
for pad_cx in [CX-46, CX+46]:
    for dy in range(0,6):
        y=188+dy
        for dx in range(-10,11):
            x=pad_cx+dx
            if dx in (-10,10) or dy==5: put(x,y,CONCDK)
            elif dy==0: put(x,y,WHITE)
            else: put(x,y,CONC)

# platforms
def platform(y_top,h,hw):
    # railing above
    for y in range(y_top-7,y_top):
        for x in range(CX-hw,CX+hw+1):
            if y==y_top-7: put(x,y,OUTL)  # top rail
            elif y in (y_top-4,):
                # mid rail line
                put(x,y,PLATDK)
            # posts
            if (x-(CX-hw))%5==0:
                put(x,y,OUTL)
            # lights on railing (warm dots) denser
            if y==y_top-6 and (x-(CX-hw))%10==5:
                put(x,y,LITWIN); put(x,y+1,GLASS)
    # deck
    for y in range(y_top,y_top+h):
        for x in range(CX-hw-4,CX+hw+5):
            if x in (CX-hw-4,CX+hw+4) or y==y_top+h-1:
                put(x,y,OUTL)
            elif y==y_top:
                put(x,y,THILITE)
            elif y==y_top+1:
                put(x,y,TLIT)
            else:
                # fascia with arched windows
                rx=(x-(CX-hw))%14
                if 4<=rx<=8 and y>=y_top+3:
                    put(x,y,LITWIN if ((x+y)&1)==0 else GLASS)
                else:
                    put(x,y,PLATDK if ((x+y)&1)==0 else OUTL)
    # under-deck shadow + small arch supports
    for x in range(CX-hw-4,CX+hw+5):
        put(x,y_top+h,OUTL)

platform(138,6,50)
platform(94,6,31)
platform(48,5,16)

# spire / antenna
for y in range(18,50):
    w2=2 if y>28 else 1
    for x in range(CX-w2,CX+w2+1):
        put(x,y,OUTL)
    put(CX,y,TMID if (y&1)==0 else THILITE)
# beacon
put(CX,16,BEACON); put(CX-1,17,BEACON); put(CX+1,17,BEACON); put(CX,17,WHITE)
# beacon glow cross (dithered, reuse lit colors)
for dx in range(-6,7):
    if dx!=0 and (dx&1)==0:
        # keep sky intact? overwrite with glow checker
        if 0<=CX+dx<W: put(CX+dx,17,LITWIN)
for dy in range(-4,5):
    if dy!=0 and (dy&1)==0:
        put(CX,17+dy,LITWIN)
# top searchlight beams (dithered white checker triangles)
for y in range(18,60):
    spread=int((y-18)*1.6)
    for x in range(CX-spread,CX+spread+1):
        # beam edges: left and right beams diagonal
        # create two thin beams going up-left and up-right
        # left beam: x approx CX-(y-18)*2 .. +3
        lx=CX-int((y-16)*2.2)
        rx=CX+int((y-16)*2.2)
        if abs(x-lx)<=1 or abs(x-rx)<=1:
            if ((x+y)&1)==0 and img[y][x] in SKY:
                put(x,y,WHITE)

# tower base floodlight glow dots on ground
for gx,gy in [(CX-36,196),(CX+36,196),(CX-22,192),(CX+22,192)]:
    put(gx,gy,LITWIN); put(gx+1,gy,GLASS); put(gx-1,gy,GLASS)

# ---------- LAMPS (foreground) ----------
def lamp(lx,base_y):
    # post
    for y in range(base_y-28,base_y+1):
        put(lx,y,POST); put(lx+1,y,POST)
    # cross base
    for dx in range(-3,5):
        put(lx+dx,base_y,POST)
    # lantern head
    hx,hy=lx,base_y-34
    for dy in range(-5,4):
        for dx in range(-4,5):
            x=hx+dx; y=hy+dy
            if abs(dx)==4 or abs(dy)==5 or dy==-5:
                put(x,y,POST)
            else:
                put(x,y,GLASS if ((x+y)&1)==0 else LITWIN)
    put(hx,hy-6,POST); put(hx-2,hy-6,POST); put(hx+2,hy-6,POST)
    # halo checker
    for dy in range(-8,8):
        for dx in range(-8,8):
            if dx*dx+dy*dy<=56 and dx*dx+dy*dy>=24:
                if ((dx+dy)&1)==0:
                    x=hx+dx; y=hy+dy
                    if 0<=x<W and 0<=y<H and img[y][x] in (GRASS1,GRASS2,CITY,CITYDK, *SKY):
                        # use lit color sparingly (checker)
                        if (dx*dx+dy*dy)<40:
                            put(x,y,LITWIN)

lamp(70,208)
lamp(186,208)

# ---------- BUSHES + FENCE ----------
for bx in [96,160,112,144]:
    by=198
    for dy in range(-5,2):
        for dx in range(-7,8):
            if dx*dx+dy*dy*2<=36:
                x=bx+dx; y=by+dy
                if dx*dx+dy*dy*2>=28: put(x,y,LEAFOUT)
                else: put(x,y,LEAF if ((x+y)&1)==0 else LEAFDK)
# fence posts along path front
for fx in range(48,210,12):
    fy=212+((fx*7)&3)
    # skip if inside path? place at path edges
    # just draw two rows front
    pass
# tiny tourists (2 sprites) for life/scale
def person(px,py,shirt,pants):
    put(px,py-6, (255,220,180))  # head (extra color? use GLASS-ish -> replace)
    # use GLASS for skin to avoid new color
    put(px,py-6,GLASS)
    put(px-1,py-5,GLASS); put(px+1,py-5,GLASS)
    put(px,py-4,shirt); put(px,py-3,shirt)
    put(px-1,py-2,pants); put(px+1,py-2,pants)
    put(px-1,py-1,POST); put(px+1,py-1,POST)

# shirt colors reuse existing: BEACON red, DARKBLUE, LEAF
person(110,216,BEACON,DARKBLUE)
person(118,218,DARKBLUE,POST)
person(148,217,LEAF,POST)

# grass tufts + flowers for SNES polish
trnd=random.Random(5)
for _ in range(70):
    x=trnd.randrange(0,W); y=trnd.randrange(HORIZON+6,H)
    if img[y][x] in (GRASS1,GRASS2):
        # tuft: 3px vertical
        put(x,y,GRASSDK); put(x,y-1,LEAF); put(x-1,y,LEAFDK)
        if trnd.random()<0.18:
            put(x,y-2,LITWIN)  # tiny flower (reuse lit color)
            put(x+1,y-2,WHITE)
# soft checker shadow ellipse
for dy in range(0,8):
    y=196+dy
    hw2=int(60-dy*3)
    for dx in range(-hw2,hw2+1):
        if (dx*dx)//40+dy*dy<60:
            x=CX+dx
            if ((x+y)&1)==0:
                # darken: map grass/path to darker existing colors
                cur=img[y][x]
                if cur in (GRASS1,GRASS2,GRASSLI): put(x,y,GRASSDK)
                elif cur in (PATH1,PATHLI): put(x,y,PATH2)
                elif cur==PATH2: put(x,y,PATHDK)

# ---------- verify constraints ----------
uniq=set()
for row in img:
    uniq.update(row)
print(f"total colors: {len(uniq)}")
# tile check
from collections import Counter
maxc=0; bad=[]
for ty in range(H//8):
    for tx in range(W//8):
        s=set()
        for dy in range(8):
            for dx in range(8):
                s.add(img[ty*8+dy][tx*8+dx])
        if len(s)>maxc: maxc=len(s)
        if len(s)>16: bad.append((tx,ty,len(s)))
print(f"max per-tile colors: {maxc}")
print(f"bad tiles: {bad[:10]} (count {len(bad)})")

# ---------- write PNG (truecolor, no new colors) ----------
def write_png(path):
    raw=bytearray()
    for y in range(H):
        raw.append(0)
        for x in range(W):
            r,g,b=img[y][x]
            raw.extend((r,g,b))
    comp=zlib.compress(bytes(raw),9)
    def chunk(typ,data):
        c=struct.pack(">I",len(data))+typ+data
        c+=struct.pack(">I",zlib.crc32(typ+data)&0xffffffff)
        return c
    png=b"\x89PNG\r\n\x1a\n"
    png+=chunk(b"IHDR",struct.pack(">IIBBBBB",W,H,8,2,0,0,0))
    png+=chunk(b"IDAT",comp)
    png+=chunk(b"IEND",b"")
    open(path,"wb").write(png)
    print("wrote",path)

write_png("output/eiffel-snes.png")
