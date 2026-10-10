import random, struct, zlib

W, H = 256, 224
random.seed(7)

fb = [[(0,0,0) for _ in range(W)] for _ in range(H)]

def lerp(a,b,t):
    return int(a+(b-a)*t)

def lerp_c(c1,c2,t):
    return (lerp(c1[0],c2[0],t), lerp(c1[1],c2[1],t), lerp(c1[2],c2[2],t))

# Sky keys: (y, color)
keys = [
    (0,   (18,16,64)),
    (45,  (43,48,128)),
    (85,  (86,86,176)),
    (115, (150,110,170)),
    (135, (232,150,110)),
    (152, (250,208,140)),
    (155, (250,208,140)),
]
def sky_at(y):
    for i in range(len(keys)-1):
        y0,c0 = keys[i]; y1,c1 = keys[i+1]
        if y0 <= y <= y1:
            t = (y-y0)/max(1,(y1-y0))
            return lerp_c(c0,c1,t)
    return keys[-1][1]

for y in range(H):
    for x in range(W):
        if y <= 155:
            fb[y][x] = sky_at(y)
        else:
            fb[y][x] = (0,0,0)

# subtle horizontal band dither (ordered) to fake SNES gradient
bayer4 = [
 [0,8,2,10],
 [12,4,14,6],
 [3,11,1,9],
 [15,7,13,5]
]
# apply tiny noise to sky to give dither feel but keep palette small: quantize tweak
for y in range(156):
    for x in range(W):
        b = bayer4[y%4][x%4]
        r,g,bl = fb[y][x]
        # add -2..2
        d = ((b-7)//4)  # -1..2
        fb[y][x] = (max(0,min(255,r+d)), max(0,min(255,g+d)), max(0,min(255,bl+d)))

# Stars in top area
for _ in range(110):
    x = random.randint(0,W-1)
    y = random.randint(2,72)
    # fade with y
    bright = 255 - y*2 + random.randint(-20,20)
    bright = max(120, min(255, bright))
    c = (bright, bright, min(255,bright+20)) if random.random()<0.2 else (bright,bright,bright)
    # twinkle size
    fb[y][x] = c
    if random.random()<0.15 and x+1<W:
        fb[y][x+1] = (bright//2,bright//2,bright//2)

# Sun glow (low sun to the right, setting)
sun_x, sun_y = 205, 142
for y in range(90,156):
    for x in range(120,W):
        dx = x-sun_x; dy=(y-sun_y)*1.6
        d2 = dx*dx+dy*dy
        if d2 < 55*55:
            t = 1 - (d2**0.5)/55
            base = fb[y][x]
            glow = (255, 220, 160)
            k = t*t*0.55
            fb[y][x] = (lerp(base[0],glow[0],k), lerp(base[1],glow[1],k), lerp(base[2],glow[2],k))
# sun disc
for y in range(sun_y-12, sun_y+8):
    for x in range(sun_x-14, sun_x+14):
        if 0<=x<W and 0<=y<H:
            dx=x-sun_x; dy=(y-sun_y)*1.3
            if dx*dx+dy*dy < 11*11:
                fb[y][x]=(255,244,200)
            elif dx*dx+dy*dy < 13*13:
                fb[y][x]=(255,220,150)

def rect(x0,y0,x1,y1,c):
    for y in range(max(0,y0),min(H,y1+1)):
        for x in range(max(0,x0),min(W,x1+1)):
            fb[y][x]=c

def ellipse(cx,cy,rx,ry,c):
    for y in range(cy-ry,cy+ry+1):
        for x in range(cx-rx,cx+rx+1):
            if 0<=x<W and 0<=y<H:
                if ((x-cx)/max(1,rx))**2+((y-cy)/max(1,ry))**2<=1:
                    fb[y][x]=c

# Clouds - blocky SNES style: clusters of rects
C_HI=(255,248,232); C_MID=(232,178,184); C_SH=(122,96,150); C_SH2=(90,72,130)
def cloud(cx,cy,s):
    # s scale 1..3
    parts=[(-3*s,0,3*s,1),( -2*s,-1,2*s,0),(-1*s,-2,1*s,-1)]
    for dx0,dy0,dx1,dy1 in parts:
        for y in range(cy+dy0,cy+dy1+1):
            for x in range(cx+dx0,cx+dx1+1):
                if 0<=x<W and 0<=y<H and y<156:
                    # shading: top highlight, bottom shadow
                    if y<=cy-1: c=C_HI
                    elif y<=cy: c=C_HI if abs(x-cx)<2*s else C_MID
                    else: c=C_MID if abs(x-cx)<2*s else C_SH
                    # blocky edge cut
                    if abs(x-(cx+dx0))<1 and abs(y-(cy+dy0))<1 and random.random()<0.5:
                        continue
                    fb[y][x]=c
    # dark underside line
    for x in range(cx-3*s,cx+3*s+1):
        y=cy+2
        if 0<=x<W and 0<=y<H:
            if fb[y][x] in (C_MID,C_SH,C_HI):
                fb[y][x]=C_SH
    # pixel notches for style
    for (nx,ny) in [(cx-3*s,cy),(cx+3*s,cy),(cx-2*s,cy-1)]:
        if 0<=nx<W and 0<=ny<H:
            pass

cloud(45,62,4)
cloud(120,38,3)
cloud(190,72,5)
cloud(70,105,3)
cloud(225,105,3)
cloud(20,125,2)
cloud(150,118,2)

# Distant Paris rooftops silhouette y ~150-172
# base haze
for y in range(150,174):
    for x in range(W):
        t=(y-150)/23
        haze=(170,150,170)
        b=fb[y][x]
        fb[y][x]=lerp_c(b,haze,t*0.35)

# buildings row
random.seed(21)
bx=0
bcols_roof=(74,70,110)
bcols_wall=(150,140,170)
bcols_wall2=(130,120,155)
bcols_dark=(60,58,100)
win_lit=(255,224,130)
while bx<W:
    bw=random.randint(18,30)
    bh=random.randint(10,20)
    by1=168; by0=by1-bh
    wall = bcols_wall if random.random()<0.5 else bcols_wall2
    for y in range(by0,by1+1):
        for x in range(bx,bx+bw):
            if 0<=x<W:
                fb[y][x]=wall
    # mansard roof
    for y in range(by0-5,by0):
        for x in range(bx-1,bx+bw+1):
            if 0<=x<W and 0<=y<H:
                # slope
                inset = (y-(by0-5))
                if bx-1+inset//2 <= x <= bx+bw-inset//2:
                    fb[y][x]=bcols_roof
    # chimneys
    for cx_ in [bx+4,bx+bw-5]:
        for y in range(by0-8,by0-4):
            if 0<=cx_<W:
                fb[y][cx_]=bcols_dark
                if cx_+1<W: fb[y][cx_+1]=bcols_dark
    # windows: lit dots
    for wy in range(by0+3,by1-1,4):
        for wx in range(bx+3,bx+bw-2,5):
            if random.random()<0.45:
                if 0<=wx<W:
                    fb[wy][wx]=win_lit
                    fb[wy][wx+1]=win_lit
            else:
                if 0<=wx<W:
                    fb[wy][wx]=bcols_dark
                    fb[wy][wx+1]=bcols_dark
    # dome occasionally
    if random.random()<0.25:
        dxc=bx+bw//2
        ellipse(dxc,by0-5,5,4,bcols_roof)
    bx+=bw+random.randint(0,4)

# Seine? no, Champ de Mars ground
# Ground base
for y in range(168,H):
    t=(y-168)/(H-1-168)
    g1=(64,130,70); g2=(36,84,52)
    for x in range(W):
        fb[y][x]=lerp_c(g1,g2,t)

# central path trapezoid: top narrow at tower, wide at bottom
path_hi=(240,216,160); path_mid=(216,178,120); path_sh=(160,124,80)
for y in range(170,H):
    tt=(y-170)/(H-1-170)  # 0 top 1 bottom
    half = int(18 + tt*62)  # 18 -> 80
    cx=128
    for x in range(cx-half,cx+half+1):
        if 0<=x<W:
            # edge shadow
            if abs(x-cx)>half-3:
                fb[y][x]=path_sh
            elif abs(x-cx)>half-7 and (x+y)%2==0:
                fb[y][x]=path_mid
            else:
                # cobble pattern
                if (x//4+y//3)%2==0:
                    fb[y][x]=path_mid
                else:
                    fb[y][x]=path_hi
                    if (x+y)%4==0:
                        fb[y][x]=path_mid

# grass dither texture
random.seed(99)
for y in range(170,H):
    for x in range(W):
        # skip path
        tt=(y-170)/(55)
        half=int(18+tt*62)
        if abs(x-128)<=half:
            continue
        if (x*7+y*13)%11==0:
            r,g,b=fb[y][x]
            fb[y][x]=(r-14,g-14,b-10)
        if (x+y)%13==0:
            r,g,b=fb[y][x]
            fb[y][x]=(r+12,g+16,b+8)

# trees: function
def tree(cx,base_y,s):
    # trunk
    trunk=(84,58,44); trunk_d=(58,38,30)
    for y in range(base_y-10*s//2,base_y+1):
        for x in range(cx-1,cx+2):
            if 0<=x<W and 0<=y<H:
                fb[y][x]=trunk if x==cx else trunk_d
    # foliage puffs: 3 circles
    greens=[(32,96,56),(48,140,68),(88,190,100),(24,72,44)]
    for (ox,oy,r,c) in [(-4*s//3,-9,6,greens[0]),(4*s//3,-9,6,greens[0]),(0,-13,8,greens[1])]:
        for y in range(base_y+oy-r,base_y+oy+r+1):
            for x in range(cx+ox-r,cx+ox+r+1):
                if 0<=x<W and 0<=y<H:
                    if (x-(cx+ox))**2+(y-(base_y+oy))**2<=r*r:
                        # blocky cut corners
                        if abs(x-(cx+ox))==r and abs(y-(base_y+oy))==r: continue
                        fb[y][x]=c
    # highlights
    for _ in range(14):
        hx=cx+random.randint(-6,6); hy=base_y-13+random.randint(-5,3)
        if 0<=hx<W and 0<=hy<H:
            if fb[hy][hx] in (greens[0],greens[1]):
                fb[hy][hx]=greens[2]
    # shadow dots
    for _ in range(10):
        hx=cx+random.randint(-6,6); hy=base_y-13+random.randint(0,6)
        if 0<=hx<W and 0<=hy<H:
            if fb[hy][hx] in (greens[0],greens[1]):
                fb[hy][hx]=greens[3]

random.seed(5)
tree(28,205,3); tree(228,205,3)
tree(52,190,2); tree(204,190,2)
tree(12,190,2); tree(244,190,2)

# street lamps along path
def lamp(cx,base_y):
    # pole
    for y in range(base_y-22,base_y):
        for x in range(cx-1,cx+1):
            if 0<=x<W and 0<=y<H:
                fb[y][x]=(30,28,44)
    # head
    for y in range(base_y-26,base_y-22):
        for x in range(cx-2,cx+3):
            if 0<=x<W and 0<=y<H:
                fb[y][x]=(30,28,44)
    # glowing light
    for y in range(base_y-24,base_y-21):
        for x in range(cx-1,cx+2):
            fb[y][x]=(255,236,160)
    # glow halo
    for y in range(base_y-29,base_y-18):
        for x in range(cx-5,cx+6):
            if 0<=x<W and 0<=y<H:
                dx=x-cx; dy=(y-(base_y-22))*1.4
                if dx*dx+dy*dy<16:
                    b=fb[y][x]
                    if b!=(255,236,160):
                        fb[y][x]=lerp_c(b,(255,210,130),0.45)

lamp(78,200); lamp(178,200)
lamp(92,186); lamp(164,186)

# ============ EIFFEL TOWER ============
cx=128
y_low=142; y_mid=95; y_top_plat=48; y_tip=14; y_base=208

IRON_D=(28,22,40)
IRON_M=(62,50,78)
IRON_L=(110,90,120)
IRON_LIT=(240,170,110)
EDGE_LIT=(255,220,150)
OUTLINE=(12,10,22)
LIGHT=(255,232,140)

def half_outer_upper(y):
    # y_mid..y_low : 14->28
    t=(y-y_mid)/(y_low-y_mid)
    return 14+(28-14)*(t**1.15)
def half_outer_mid(y):
    # y_top_plat..y_mid : 7->14
    t=(y-y_top_plat)/(y_mid-y_top_plat)
    return 7+(14-7)*(t**1.1)
def half_outer_top(y):
    t=(y-y_tip)/(y_top_plat-y_tip)
    return 2+(7-2)*t

def half_outer_low(y):
    t=(y-y_low)/(y_base-y_low)
    return 28+(55-28)*(t**1.25)
def half_inner_low(y):
    t=(y-y_low)/(y_base-y_low)
    return 4+(33-4)*(t**1.7)

# collect tower pixels set
tower_mask=set()

# upper pylon mid-low
for y in range(y_mid, y_low+1):
    h=int(half_outer_upper(y))
    for x in range(cx-h,cx+h+1):
        tower_mask.add((x,y))
# mid section
for y in range(y_top_plat, y_mid+1):
    h=int(half_outer_mid(y))
    for x in range(cx-h,cx+h+1):
        tower_mask.add((x,y))
# top spire
for y in range(y_tip, y_top_plat+1):
    h=int(half_outer_top(y))
    for x in range(cx-h,cx+h+1):
        tower_mask.add((x,y))
# legs
for y in range(y_low, y_base+1):
    ho=int(half_outer_low(y)); hi=int(half_inner_low(y))
    for x in range(cx-ho,cx-hi+1):
        tower_mask.add((x,y))
    for x in range(cx+hi,cx+ho+1):
        tower_mask.add((x,y))

# fill with shading: left dark, center mid, right lit
for (x,y) in tower_mask:
    # determine half at this y
    if y<y_top_plat: h=half_outer_top(y)
    elif y<y_mid: h=half_outer_mid(y)
    elif y<=y_low:
        if y>=y_mid: h=half_outer_upper(y)
        else: h=10
    else:
        h=half_outer_low(y)
    rel=(x-cx)/max(1,h)  # -1..1
    if rel<-0.55:
        c=IRON_D
    elif rel<-0.15:
        c=IRON_M
    elif rel<0.45:
        c=IRON_M
    else:
        c=IRON_L
        # rightmost edge warm lit
        if rel>0.6:
            c=IRON_LIT
    fb[y][x]=c

# arch underside shadow: darken inner edge
for y in range(y_low, y_base+1):
    hi=int(half_inner_low(y))
    for dx in [ -hi, hi]:
        x=cx+dx
        for k in range(2):
            xx=x+(1 if dx>0 else -1)*k
            if (xx,y) in tower_mask:
                # inner highlight
                fb[y][xx]=IRON_LIT if y>y_low+30 else IRON_L

# lattice X bracing: draw dark lines inside
for y in range(y_tip+4, y_base-2):
    # skip platforms
    if y_low-7<=y<=y_low+1: continue
    if y_mid-6<=y<=y_mid+1: continue
    if y_top_plat-5<=y<=y_top_plat+1: continue
    if y>=y_low:
        ho=int(half_outer_low(y)); hi=int(half_inner_low(y))
        spans=[(cx-ho,cx-hi),(cx+hi,cx+ho)]
    else:
        if y<y_top_plat: h=int(half_outer_top(y))
        elif y<y_mid: h=int(half_outer_mid(y))
        else: h=int(half_outer_upper(y))
        spans=[(cx-h,cx+h)]
    for (xa,xb) in spans:
        w=xb-xa
        if w<4: continue
        # X pattern period 10px
        ph=y%10
        # diagonal 1: x = xa + ph*w/10 etc - draw 1px lines
        for d in [-1,0]:
            xd1=xa+int((ph+d)*w/10)
            xd2=xa+int((9-ph+d)*w/10)
            for xx in [xd1,xd2]:
                if xa+1<=xx<=xb-1 and 0<=xx<W:
                    if (xx,y) in tower_mask:
                        # keep lit edge
                        if fb[y][xx]==IRON_LIT and xx>cx: continue
                        fb[y][xx]=IRON_D
        # horizontal cross bar every 10
        if ph==0 or ph==5:
            for xx in range(xa+1,xb):
                if (xx,y) in tower_mask:
                    if fb[y][xx]==IRON_LIT and xx>cx: continue
                    fb[y][xx]=IRON_D

# outline: any tower pixel adjacent to non-tower -> outline on edge
# do after fill: darken edge pixels
dirs=[(1,0),(-1,0),(0,1),(0,-1)]
for (x,y) in list(tower_mask):
    for dx,dy in dirs:
        nx,ny=x+dx,y+dy
        if not (0<=nx<W and 0<=ny<H) or (nx,ny) not in tower_mask:
            # this is edge; but keep bottom feet not outlined at ground? keep outline
            # don't overwrite lit edge fully? outline outermost
            # only outline outer/inner silhouette, not every lattice hole (lattice already dark)
            # check if neighbor is outside tower shape (not lattice): lattice interior still in mask, so fine
            fb[y][x]=OUTLINE
            break

# platforms
def platform(yc,half_w,thick):
    for y in range(yc-thick,yc+1):
        for x in range(cx-half_w,cx+half_w+1):
            if 0<=x<W and 0<=y<H:
                tower_mask.add((x,y))
                if y==yc-thick:
                    fb[y][x]=EDGE_LIT  # top lit edge
                elif x==cx-half_w or x==cx+half_w:
                    fb[y][x]=OUTLINE
                else:
                    # railing: alternating
                    if y==yc-thick+1 and x%2==0:
                        fb[y][x]=LIGHT
                    else:
                        fb[y][x]=IRON_D if (x-cx)<0 else IRON_M
    # outline bottom
    for x in range(cx-half_w,cx+half_w+1):
        fb[yc+1][x]=OUTLINE if 0<=x<W and yc+1<H else None

platform(y_low,34,6)
platform(y_mid,19,5)
platform(y_top_plat,11,4)

# re-outline platform sides top?
# beacon
fb[y_tip-2][cx]= (255,80,80)
fb[y_tip-1][cx]= (255,240,200)
fb[y_tip][cx]= (255,240,200)
# glow around tip
for (dx,dy) in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1)]:
    xx,yy=cx+dx,y_tip-1+dy
    if 0<=xx<W and 0<=yy<H and (xx,yy) not in tower_mask:
        b=fb[yy][xx]
        fb[yy][xx]=lerp_c(b,(255,220,160),0.6)

# sparkling lights on tower edges (warm)
random.seed(3)
for (x,y) in tower_mask:
    if fb[y][x] in (OUTLINE,): continue
    if random.random()<0.02:
        fb[y][x]=LIGHT

# string lights along arch
for t in [i/20 for i in range(21)]:
    # parabola arch: from left inner base to right inner base apex near y_low+8
    xl=cx-int(half_inner_low(y_base))+2
    xr=cx+int(half_inner_low(y_base))-2
    xa=int(xl+(xr-xl)*t)
    ya=int((y_base-2) - (y_base-(y_low+8))*4*t*(1-t)*1.0)  # arch curve inverted? apex top
    # actually arch apex at y_low+8, ends at y_base-10
    ya = int((y_low+10) + ((y_base-6)-(y_low+10))*( (2*t-1)**2 ))
    if 0<=xa<W and 0<=ya<H:
        fb[ya][xa]=LIGHT
        if xa+1<W: fb[ya][xa+1]=(255,200,110)

# ground shadow under tower
for x in range(cx-60,cx+61):
    y=y_base+1
    if 0<=x<W and y<H:
        if abs(x-cx)<50:
            fb[y][x]=(20,30,30)
            if y+1<H: fb[y+1][x]=(30,50,40)

# foreground vignette bushes
def bush(cx_,cy_,w):
    for y in range(cy_-6,cy_+3):
        for x in range(cx_-w,cx_+w+1):
            if 0<=x<W and 0<=y<H:
                if (x-cx_)**2/ max(1,w*w)+ (y-cy_)**2/36 <=1:
                    fb[y][x]=(24,70,44) if (x+y)%2==0 else (36,100,60)
bush(18,220,16); bush(238,220,16)

# birds
for (bx_,by_) in [(90,55),(96,57),(160,30),(166,32)]:
    if 0<=bx_<W:
        fb[by_][bx_]=OUTLINE
        fb[by_][bx_-2]=OUTLINE
        fb[by_-1][bx_-1]=OUTLINE

# ---- palette enforce: quantize check later ----
# ---- SNES palette enforce: median-cut to 128 ----
from collections import Counter
flat=[fb[y][x] for y in range(H) for x in range(W)]
# first snap to SNES 15-bit (5 bits/channel)
flat15=[(r//8*8+4, g//8*8+4, b//8*8+4) for (r,g,b) in flat]
# median cut
boxes=[flat15]
while len(boxes)<128:
    # find box to split: largest range & >1 distinct
    best=-1; best_range=-1; best_ch=0
    for i,b in enumerate(boxes):
        if len(b)<=1: continue
        rs=[c[0] for c in b]; gs=[c[1] for c in b]; bs=[c[2] for c in b]
        rg=max(rs)-min(rs); gg=max(gs)-min(gs); bg=max(bs)-min(bs)
        r=max(rg,gg,bg)
        if r>best_range:
            # check distinct
            if len(set(b))>1:
                best_range=r; best=i; best_ch=0 if r==rg else (1 if r==gg else 2)
    if best==-1 or best_range==0:
        break
    b=boxes.pop(best)
    b_sorted=sorted(b,key=lambda c:c[best_ch])
    mid=len(b_sorted)//2
    boxes.append(b_sorted[:mid]); boxes.append(b_sorted[mid:])
    if len(boxes)>=256: break
palette=[]
for b in boxes:
    n=len(b)
    ar=sum(c[0] for c in b)//n; ag=sum(c[1] for c in b)//n; ab=sum(c[2] for c in b)//n
    # snap avg to 15-bit too
    palette.append((ar//8*8+4, ag//8*8+4, ab//8*8+4))
# dedupe palette
uniq=[]
seen=set()
for c in palette:
    if c not in seen:
        seen.add(c); uniq.append(c)
palette=uniq
print("palette size:",len(palette))
# map each pixel to nearest palette entry
def nearest(c):
    br=c[0]; bg=c[1]; bb=c[2]
    best=None; bd=1e9
    for p in palette:
        dr=br-p[0]; dg=bg-p[1]; db=bb-p[2]
        d=dr*dr+dg*dg+db*db
        if d<bd:
            bd=d; best=p
            if d==0: break
    return best
# build lookup for all distinct 15-bit colors to speed up
distinct=set(flat15)
print("distinct15:",len(distinct))
lut={c:nearest(c) for c in distinct}
for y in range(H):
    for x in range(W):
        r,g,b=fb[y][x]
        q=(r//8*8+4, g//8*8+4, b//8*8+4)
        fb[y][x]=lut[q]
cols=set()
for y in range(H):
    for x in range(W):
        cols.add(fb[y][x])
print("colors after quant:", len(cols))
# per-tile check
maxpt=0; bad=0
for ty in range(H//8):
    for tx in range(W//8):
        s=set()
        for y in range(ty*8,ty*8+8):
            for x in range(tx*8,tx*8+8):
                s.add(fb[y][x])
        maxpt=max(maxpt,len(s))
        if len(s)>16:
            bad+=1
print("max colors per tile:",maxpt,"tiles over 16:",bad)

# write PNG
def write_png(path, fb):
    import zlib, struct
    h=len(fb); w=len(fb[0])
    raw=bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r,g,b=fb[y][x]
            raw.extend([r,g,b])
    comp=zlib.compress(bytes(raw),9)
    def chunk(typ,data):
        c=struct.pack(">I",len(data))+typ+data
        c+=struct.pack(">I",zlib.crc32(typ+data)&0xffffffff)
        return c
    png=b'\x89PNG\r\n\x1a\n'
    png+=chunk(b'IHDR',struct.pack(">IIBBBBB",w,h,8,2,0,0,0))
    png+=chunk(b'IDAT',comp)
    png+=chunk(b'IEND',b'')
    open(path,'wb').write(png)

write_png("preview.png", fb)
