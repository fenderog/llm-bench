#!/usr/bin/env python3
"""SNES Eiffel Tower pixel art generator - 256x224, <=128 colors, 8x8 tiles <=16 colors."""
import struct, zlib, math, random

W, H = 256, 224

# ---------- Palette (must stay <=128) ----------
# Define named colors
PAL = []
def add(name, r, g, b):
    PAL.append((name, r, g, b))
    return len(PAL)-1

# outline near-black
C_OUTLINE   = add("outline", 26, 18, 26)
# sky gradient 14 bands top->horizon
SKY = []
sky_defs = [
    (38,38,92),(48,44,108),(60,52,124),(76,60,136),
    (96,68,144),(120,76,148),(144,84,148),(168,92,144),
    (188,100,136),(208,112,128),(224,128,124),(236,148,120),
    (248,168,116),(252,192,128),
]
for i,(r,g,b) in enumerate(sky_defs):
    SKY.append(add(f"sky{i}", r,g,b))

C_SUN_CORE = add("sun_core", 255, 244, 200)
C_SUN_MID  = add("sun_mid", 255, 212, 140)

C_CLOUD_W  = add("cloud_w", 250, 240, 232)
C_CLOUD_L  = add("cloud_l", 240, 200, 192)
C_CLOUD_S  = add("cloud_s", 168, 128, 160)
C_CLOUD_D  = add("cloud_d", 72, 56, 96)

C_CITY_FAR  = add("city_far", 108, 88, 132)
C_CITY_MID  = add("city_mid", 84, 68, 112)
C_CITY_NEAR = add("city_near", 56, 44, 80)
C_CITY_DARK = add("city_dark", 40, 32, 64)
C_ROOF      = add("roof", 72, 52, 88)

C_IRON_D    = add("iron_d", 58, 36, 36)
C_IRON_MD   = add("iron_md", 88, 52, 44)
C_IRON_B    = add("iron_b", 122, 72, 52)
C_IRON_ML   = add("iron_ml", 158, 100, 68)
C_IRON_L    = add("iron_l", 196, 136, 92)
C_IRON_HL   = add("iron_hl", 236, 180, 128)
C_LATTICE   = add("lattice", 46, 28, 32)
C_RIVET     = add("rivet", 255, 220, 170)
C_PLAT      = add("plat", 36, 24, 32)
C_BEACON_R  = add("beacon_r", 255, 64, 64)
C_BEACON_W  = add("beacon_w", 255, 240, 240)

C_GRASS_D  = add("grass_d", 40, 84, 48)
C_GRASS_B  = add("grass_b", 56, 112, 56)
C_GRASS_M  = add("grass_m", 76, 140, 64)
C_GRASS_L  = add("grass_l", 104, 168, 80)
C_GRASS_O  = add("grass_o", 28, 56, 36)
C_FLOWER_R = add("flower_r", 224, 64, 80)
C_FLOWER_Y = add("flower_y", 248, 208, 96)
C_FLOWER_W = add("flower_w", 240, 240, 220)

C_PATH_B = add("path_b", 188, 156, 120)
C_PATH_D = add("path_d", 152, 124, 96)
C_PATH_L = add("path_l", 216, 184, 148)
C_PATH_O = add("path_o", 96, 72, 60)

C_TRUNK_D = add("trunk_d", 64, 40, 32)
C_TRUNK_M = add("trunk_m", 96, 60, 40)
C_LEAF_D  = add("leaf_d", 32, 72, 40)
C_LEAF_B  = add("leaf_b", 48, 100, 52)
C_LEAF_M  = add("leaf_m", 68, 128, 64)
C_LEAF_L  = add("leaf_l", 96, 160, 84)
C_LEAF_HL = add("leaf_hl", 136, 192, 112)

C_POST_B  = add("post_b", 20, 20, 28)
C_POST_M  = add("post_m", 60, 60, 80)
C_STAR    = add("star", 240, 240, 255)
C_BIRD    = add("bird", 40, 32, 64)  # same rgb as city_dark but separate entry? merge to save? keep distinct counts - dedupe later
# Note C_BIRD duplicates C_CITY_DARK rgb; dedupe will merge. Let's keep but count distinct RGB.

print(f"Palette entries: {len(PAL)}")
# dedupe check distinct RGB
rgbs = {}
for i,(n,r,g,b) in enumerate(PAL):
    rgbs.setdefault((r,g,b), []).append(n)
print(f"Distinct RGB: {len(rgbs)}")
for k,v in rgbs.items():
    if len(v)>1:
        print(" duplicate",k,v)

# Build index map: we will use indices as defined, but for duplicate RGB keep first
# For constraint counting, distinct RGB matters. Let's remap duplicates to first occurrence.
remap = {}
seen = {}
for i,(n,r,g,b) in enumerate(PAL):
    if (r,g,b) in seen:
        remap[i]=seen[(r,g,b)]
    else:
        seen[(r,g,b)]=i
print("remap duplicates:",remap)

# Buffer of palette indices
buf = [[0]*W for _ in range(H)]
def set_px(x,y,c):
    if 0<=x<W and 0<=y<H:
        # apply remap
        c = remap.get(c,c)
        buf[y][x]=c

def get_px(x,y):
    if 0<=x<W and 0<=y<H:
        return buf[y][x]
    return -1

# ---------- SKY ----------
# bands: define y ranges for 14 sky colors covering y 0..160
# distribute: first 8 bands 12px each (0..95), next 6 bands ~10-11px
bounds = [0,12,24,36,48,60,72,84,96,106,116,126,136,148,161]
assert len(bounds)==15
def sky_idx_for_y(y):
    for i in range(14):
        if bounds[i]<=y<bounds[i+1]:
            return SKY[i]
    return SKY[13]

for y in range(0,161):
    c = sky_idx_for_y(y)
    for x in range(W):
        set_px(x,y,c)
    # dither boundary row: checker mix with next band for SNES gradient smoothness
    # if y is last row of band (except last), dither it
    for i in range(14):
        if y==bounds[i+1]-1 and i<13:
            nxt = SKY[i+1]
            for x in range(W):
                if (x+y)&1==0:
                    set_px(x,y,nxt)
            break

# ---------- STARS (top area only) ----------
random.seed(7)
for _ in range(55):
    x = random.randint(0,W-1)
    y = random.randint(0,62)
    # avoid sun area? sun is lower, fine
    # only on darker sky (y<60)
    # sparse: 1px star, some brighter with cross
    b = random.random()
    if b<0.6:
        set_px(x,y,C_STAR)
    elif b<0.8:
        set_px(x,y,C_STAR)
        # dim via dither? keep single px
        pass
    else:
        set_px(x,y,C_STAR)
        if x+1<W: set_px(x+1,y,C_STAR)
        # tiny cross
        # keep minimal

# ---------- SUN ----------
SUN_X, SUN_Y, R_CORE, R_MID, R_GLOW = 196, 126, 12, 18, 30
for y in range(SUN_Y-R_GLOW, SUN_Y+R_GLOW+1):
    for x in range(SUN_X-R_GLOW, SUN_X+R_GLOW+1):
        if not (0<=x<W and 0<=y<H and y<161):
            continue
        dx, dy = x-SUN_X, y-SUN_Y
        d = math.hypot(dx,dy)
        if d<=R_CORE:
            set_px(x,y,C_SUN_CORE)
        elif d<=R_MID:
            # dither edge between core and mid
            if d<R_CORE+1.5 and ((x+y)&1==0):
                set_px(x,y,C_SUN_CORE)
            else:
                set_px(x,y,C_SUN_MID)
        elif d<=R_GLOW:
            # translucent glow: checker with sky
            if ((x+y)&1)==0:
                # alternate mid / sky dither -> glow feel
                # closer = denser
                if d<R_MID+4 or ((x*2+y)&1)==0:
                    set_px(x,y,C_SUN_MID)
                # else leave sky
            # horizontal flare line
            pass
# sun horizontal flare (anamorphic SNES sparkle)
for x in range(SUN_X-34, SUN_X+35):
    if 0<=x<W:
        if abs(x-SUN_X)>R_MID:
            # 1px flare with dither
            if (x&1)==0:
                set_px(x,SUN_Y,C_SUN_MID)
                set_px(x,SUN_Y-1,C_SUN_MID) if (x&3)==0 else None
# vertical flare shorter
for y in range(SUN_Y-22, SUN_Y+23):
    if 0<=y<H:
        if abs(y-SUN_Y)>R_MID and (y&1)==0:
            set_px(SUN_X,y,C_SUN_MID)

# ---------- CLOUDS ----------
def draw_cloud(cx, cy, w, h):
    # w,h bounding; shape via ellipses: 3-4 bumps
    # bumps: (dx, dy, rx, ry)
    bumps = [(-w//3, 2, w//4, h//3),(0, -2, w//3, h//2),(w//3, 2, w//4, h//3)]
    # collect mask
    xs0, xs1 = cx-w//2-4, cx+w//2+4
    ys0, ys1 = cy-h//2-4, cy+h//2+4
    mask=set()
    for y in range(ys0, ys1+1):
        for x in range(xs0, xs1+1):
            inside=False
            for (dx,dy,rx,ry) in bumps:
                bx, by = cx+dx, cy+dy
                if ((x-bx)/max(1,rx))**2 + ((y-by)/max(1,ry))**2 <=1:
                    inside=True
                    break
            # also base rect
            if not inside:
                if abs(x-cx)<=w//2 and abs(y-(cy+2))<=h//4:
                    inside=True
            if inside:
                mask.add((x,y))
    # fill shading by relative height
    for (x,y) in mask:
        if not (0<=x<W and 0<=y<H):
            continue
        rel = (y - (cy - h//2)) / max(1,h)  # 0 top 1 bottom
        if rel<0.45:
            set_px(x,y,C_CLOUD_W)
        elif rel<0.75:
            # dither transition white->light
            if rel<0.52 and ((x+y)&1==0):
                set_px(x,y,C_CLOUD_W)
            else:
                set_px(x,y,C_CLOUD_L)
        else:
            # bottom shadow
            if rel>0.88:
                set_px(x,y,C_CLOUD_S)
            else:
                if ((x+y)&1)==0:
                    set_px(x,y,C_CLOUD_L)
                else:
                    set_px(x,y,C_CLOUD_S)
    # outline: pixels in mask touching outside -> dark bottom, else keep? SNES: dark outline bottom, mid outline sides
    for (x,y) in list(mask):
        # check 4-neighbors outside mask
        for nx,ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if (nx,ny) not in mask:
                if 0<=nx<W and 0<=ny<H:
                    # only outline bottom and sides, top stays light (no outline or light outline)
                    # if neighbor is below -> dark shadow outline
                    if ny==y+1:
                        set_px(x,y,C_CLOUD_D)
                    elif ny==y-1:
                        # top edge: keep white (no dark outline)
                        pass
                    else:
                        # sides: mid dark only if lower half
                        rel2 = (y - (cy - h//2))/max(1,h)
                        if rel2>0.5:
                            set_px(x,y,C_CLOUD_D)
                # also draw outer outline pixel? For crispness, set neighbor if sky to dark? No, keep 1px inner outline only.
                break
    # highlight: top white sparkle line
    for x in range(cx-w//3, cx+w//3):
        y = cy - h//2 + 1
        if (x,y) in mask:
            set_px(x,y,C_CLOUD_W)

# clouds: place before skyline, after sun
draw_cloud(42, 36, 66, 18)
draw_cloud(208, 32, 72, 20)
draw_cloud(32, 88, 54, 14)
draw_cloud(172, 92, 60, 16)  # partially behind tower later? tower drawn after so tower covers
draw_cloud(120, 58, 46, 12)
# small wisp
draw_cloud(90, 108, 36, 10)

# ---------- DISTANT PARIS SKYLINE ----------
# far layer
def draw_far_city():
    y_base = 156
    x=0
    random.seed(21)
    while x<W:
        bw = random.randint(18,30)
        bh = random.randint(10,20)
        top = y_base - bh
        # body
        for yy in range(top, y_base):
            for xx in range(x, min(W,x+bw)):
                set_px(xx,yy,C_CITY_FAR)
        # mansard roof: trapezoid 4px
        for r in range(4):
            yy = top -4 + r
            inset = r  # narrower at top? actually mansard slopes inward upward? top narrower
            # invert: bottom wider
            # r=0 top, r=3 bottom (widest)
            x0 = x+2+ (3-r)
            x1 = x+bw-2-(3-r)
            for xx in range(max(0,x0), min(W,x1+1)):
                set_px(xx,yy,C_CITY_MID if r<2 else C_CITY_FAR)
        # roof top line
        for xx in range(x+5, min(W,x+bw-5)):
            set_px(xx, top-4, C_CITY_MID)
        x+=bw+random.randint(1,4)

def draw_near_city():
    y_base = 161
    x=-4
    random.seed(42)
    # add a dome (Sacré-Cœur-ish) on left? draw small dome at x~18
    while x<W:
        bw = random.randint(22,34)
        bh = random.randint(14,24)
        # vary height, center taller?
        if 100<x<160:
            bh = random.randint(8,12)  # lower behind tower/hill so tower stands out
        top = y_base - bh
        for yy in range(top, y_base):
            for xx in range(x, min(W,x+bw)):
                if 0<=xx<W:
                    set_px(xx,yy,C_CITY_NEAR)
        # mansard roof dark
        for r in range(5):
            yy = top-5+r
            inset = (4-r)
            # shape: bottom wide, top narrow
            x0 = x+3+inset
            x1 = x+bw-3-inset
            for xx in range(max(0,x0), min(W,x1+1)):
                set_px(xx,yy,C_ROOF if r>=2 else C_CITY_DARK)
        # chimneys
        for _ in range(random.randint(1,3)):
            chx = random.randint(x+4, x+bw-6)
            chh = random.randint(4,7)
            for yy in range(top-5-chh, top-4):
                for xx in range(chx, chx+2):
                    if 0<=xx<W and yy>=0:
                        set_px(xx,yy,C_CITY_DARK)
            set_px(chx, top-5-chh, C_CITY_DARK)
        # lit windows: small 2x2 yellow dots grid, sparse
        for wy in range(top+4, y_base-2, 5):
            for wx in range(x+4, x+bw-4, 6):
                if random.random()<0.45:
                    if 0<=wx<W:
                        set_px(wx,wy,C_SUN_MID)
                        set_px(wx+1,wy,C_SUN_MID)
                        # dark frame below?
                        # set_px(wx,wy+1,C_CITY_DARK)  # keep lit
        # roof edge highlight (sunset rim)
        for xx in range(max(0,x), min(W,x+bw)):
            # top of body highlight 1px warm
            if random.random()<0.9:
                # use rivet warm? reuse sun_mid dithered
                if (xx&1)==0:
                    set_px(xx,top,C_SUN_MID)
        x+=bw+random.randint(2,6)

draw_far_city()
draw_near_city()

# dome silhouette left (Montmartre hill + Sacre Coeur) - draw over near city at x~22
def draw_dome():
    cx, base = 24, 161
    # hill
    for y in range(base-14, base):
        half = int(22*math.sqrt(max(0,1-((y-(base-14))/14)**2))*0.9+6)
        for x in range(cx-half, cx+half+1):
            if 0<=x<W:
                # hill color city_near but slightly darker bottom?
                set_px(x,y,C_CITY_NEAR)
    # church on hill
    bx, by = cx, base-14
    # nave rect
    for y in range(by-10, by):
        for x in range(bx-8, bx+9):
            set_px(x,y,C_CITY_NEAR)
    # central dome
    for y in range(by-18, by-9):
        dy = y-(by-9)
        half = int(6*math.sqrt(max(0,1-(dy/9)**2))+1)
        for x in range(bx-half, bx+half+1):
            set_px(x,y,C_CITY_NEAR)
    # side domes
    for sx in (bx-7, bx+7):
        for y in range(by-13, by-9):
            dy=y-(by-9)
            half=int(3*math.sqrt(max(0,1-(dy/4)**2))+1)
            for x in range(sx-half, sx+half+1):
                set_px(x,y,C_CITY_NEAR)
    # tiny highlight windows
    set_px(bx,by-5,C_SUN_MID)
    set_px(bx+1,by-5,C_SUN_MID)
draw_dome()

# ---------- GROUND ----------
# base grass
for y in range(160, H):
    for x in range(W):
        set_px(x,y,C_GRASS_B)
# horizon rim light (sunset on grass top edge)
for x in range(W):
    set_px(x,160,C_GRASS_L)
    if (x&1)==0:
        set_px(x,161,C_GRASS_M)
# grass vertical shading: darker toward bottom with dither
for y in range(162, H):
    # blend factor to dark
    t = (y-162)/(H-1-162)  # 0..1
    for x in range(W):
        # checker dither between base and dark/mid
        if t>0.6:
            if ((x+y)&1)==0:
                # keep base, else dark?
                pass
            else:
                # darker toward bottom
                if t>0.85:
                    set_px(x,y,C_GRASS_D)
                else:
                    # mix base/dark via checker already? set dark on checker
                    if ((x*2+y)&1)==0:
                        set_px(x,y,C_GRASS_D)
        elif t>0.3:
            if ((x+y)&1)==0 and ((x*3+y*2)&3)==0:
                set_px(x,y,C_GRASS_M if (x&1)==0 else C_GRASS_B)

# path trapezoid: top (110,160)-(146,160) bottom (75,224)-(181,224)
def in_path(x,y):
    if y<160: return False
    t=(y-160)/(223-160)
    xl = 110 + (75-110)*t
    xr = 146 + (181-146)*t
    return xl<=x<=xr

for y in range(160,H):
    t=(y-160)/(223-160)
    xl = int(110 + (75-110)*t)
    xr = int(146 + (181-146)*t)
    for x in range(max(0,xl-1), min(W,xr+2)):
        if x==xl-1 or x==xr+1:
            # edge outline (skip top row)
            if y>162:
                set_px(x,y,C_PATH_O)
        elif xl<=x<=xr:
            set_px(x,y,C_PATH_B)
# path shading: left shadow, right highlight + speckles
random.seed(99)
for y in range(160,H):
    t=(y-160)/(63)
    xl = int(110 + (75-110)*t)
    xr = int(146 + (181-146)*t)
    for x in range(xl,xr+1):
        # left 3px shadow
        if x<xl+3 and y>165:
            if ((x+y)&1)==0:
                set_px(x,y,C_PATH_D)
        # right highlight
        if x>xr-3:
            if ((x+y)&1)==0:
                set_px(x,y,C_PATH_L)
        # speckles
        r=random.random()
        if r<0.06:
            set_px(x,y,C_PATH_D)
        elif r<0.10:
            set_px(x,y,C_PATH_L)
        # center stones: horizontal lines every 12px (perspective)
        if y%12==0 and (x&1)==0:
            set_px(x,y,C_PATH_D)
# path center highlight line? no

# hedge row at y 164-168 across, with gap for path
for x in range(0,W):
    y0=164
    # gap where path (path top width)
    if 108<=x<=148:
        continue
    for y in range(y0, y0+5):
        # hedge leaf dark base with highlights
        if y==y0:
            set_px(x,y,C_LEAF_L if (x&1)==0 else C_LEAF_M)
        elif y==y0+4:
            set_px(x,y,C_LEAF_D)
        else:
            set_px(x,y,C_LEAF_B if (x&1)==0 else C_LEAF_M)
        # top sparkle
# hedge outline bottom
for x in range(0,W):
    if 108<=x<=148: continue
    set_px(x,168+1,C_GRASS_D)

# grass tufts + flowers (deterministic)
random.seed(1234)
for _ in range(90):
    x=random.randint(0,W-1)
    y=random.randint(170,H-4)
    if in_path(x,y):
        continue
    # tuft: 3px
    set_px(x,y,C_GRASS_L)
    set_px(x-1,y+1,C_GRASS_M)
    set_px(x+1,y+1,C_GRASS_M)
    if random.random()<0.25:
        # flower
        fx, fy = x, y-2
        if not in_path(fx,fy):
            fc = random.choice([C_FLOWER_R, C_FLOWER_Y, C_FLOWER_W])
            set_px(fx,fy,fc)
            set_px(fx,fy+1,C_GRASS_D)

# ---------- TREES ----------
def draw_tree(cx, base_y, scale=1.0):
    # trunk
    trunk_w = int(4*scale)
    trunk_h = int(18*scale)
    top_y = base_y - trunk_h
    for y in range(top_y, base_y+1):
        for x in range(cx-trunk_w//2, cx+trunk_w//2+1):
            # shading: left dark, right mid
            if x<=cx-1:
                set_px(x,y,C_TRUNK_D)
            else:
                set_px(x,y,C_TRUNK_M)
            # outline sides
            if x==cx-trunk_w//2 or x==cx+trunk_w//2:
                # keep dark outline? use post_b? use trunk_d darker? use outline for outer?
                pass
    # outline trunk sides
    for y in range(top_y, base_y+1):
        set_px(cx-trunk_w//2-1,y,C_OUTLINE)
        set_px(cx+trunk_w//2+1,y,C_OUTLINE)
    # canopy: cluster of circles
    # center above trunk top
    can_cy = top_y - int(10*scale)
    # radii
    blobs = [ (0,0,int(14*scale)), (-10*scale,4*scale,int(9*scale)), (10*scale,4*scale,int(9*scale)), (0,-8*scale,int(10*scale)) ]
    # mask
    mask=set()
    for (dx,dy,r) in blobs:
        bx, by = cx+int(dx), can_cy+int(dy)
        for y in range(by-r-1, by+r+2):
            for x in range(bx-r-1, bx+r+2):
                if (x-bx)**2+(y-by)**2 <= r*r:
                    mask.add((x,y))
    for (x,y) in mask:
        if not (0<=x<W and 0<=y<H):
            continue
        # shading by height + x: top-left light, bottom-right dark
        # normalized: ny 0 top 1 bottom, nx 0 left 1 right
        # compute bounds roughly
        rel_y = (y - (can_cy-14*scale)) / max(1,28*scale)
        rel_x = (x - (cx-14*scale)) / max(1,28*scale)
        light = (1-rel_y)*0.6 + (1-rel_x)*0.4  # 0..1 top-left bright
        if light>0.75:
            c=C_LEAF_HL
        elif light>0.6:
            c=C_LEAF_L
        elif light>0.45:
            c=C_LEAF_M
        elif light>0.3:
            c=C_LEAF_B
        else:
            c=C_LEAF_D
        # dither transitions: checker
        # add texture speckle
        if ((x*3+y*5)&7)==0:
            # darker speckle
            if c==C_LEAF_M: c=C_LEAF_B
            elif c==C_LEAF_L: c=C_LEAF_M
        set_px(x,y,c)
    # outline canopy: edge pixels touching outside -> outline (but only darker side? use outline for bottom, leaf_d for top? SNES uses dark outline all around)
    for (x,y) in list(mask):
        for nx,ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if (nx,ny) not in mask:
                # keep outline only if neighbor not trunk? always outline
                # top highlight edge: keep leaf dark? Use outline for crispness but softer top? Use outline.
                set_px(x,y,C_OUTLINE)
                break
    # highlight sparkles on top-left
    for _ in range(int(12*scale)):
        hx = cx + random.randint(-10,2)*scale
        hy = can_cy + random.randint(-12,-2)*scale
        hx, hy = int(hx), int(hy)
        if (hx,hy) in mask:
            set_px(hx,hy,C_LEAF_HL)
    # shadow under tree on grass
    for x in range(cx-int(14*scale), cx+int(14*scale)+1):
        if 0<=x<W:
            if abs(x-cx)<10*scale and (x&1)==0:
                set_px(x,base_y+1,C_GRASS_D)

random.seed(5)
draw_tree(30, 198, 1.15)
draw_tree(226, 198, 1.15)
draw_tree(58, 182, 0.7)
draw_tree(198, 182, 0.7)

# ---------- LAMPPOSTS ----------
def draw_lamppost(cx, base_y):
    h=38
    top_y=base_y-h
    # pole
    for y in range(top_y+8, base_y):
        set_px(cx,y,C_POST_B)
        set_px(cx-1,y,C_POST_M if (y&1)==0 else C_POST_B)
        # outline sides
        set_px(cx-2,y,C_OUTLINE)
        set_px(cx+1,y,C_OUTLINE)
    # base
    for y in range(base_y-4, base_y+1):
        for x in range(cx-3, cx+2):
            set_px(x,y,C_POST_B)
    for x in range(cx-4,cx+3):
        set_px(x,base_y+1,C_OUTLINE)
    # crossarm? lantern head
    # lantern glass 6x8
    lx0, lx1 = cx-3, cx+3
    ly0, ly1 = top_y, top_y+8
    # cap
    for x in range(lx0-2, lx1+3):
        set_px(x,ly0-2,C_OUTLINE)
        set_px(x,ly0-1,C_POST_B)
    set_px(cx,ly0-4,C_OUTLINE)
    set_px(cx,ly0-3,C_POST_B)
    # glass
    for y in range(ly0, ly1+1):
        for x in range(lx0, lx1+1):
            # glowing center
            if x==cx and y in (ly0+2,ly0+3,ly0+4):
                set_px(x,y,C_SUN_MID)
            elif abs(x-cx)<=1 and ly0+1<=y<=ly0+5:
                set_px(x,y,C_SUN_MID)
            else:
                set_px(x,y,C_SUN_CORE if (x==cx-1 or x==cx+1) and y==ly0+3 else C_POST_B)
            # frame edges
            if x==lx0 or x==lx1:
                set_px(x,y,C_OUTLINE)
    for x in range(lx0, lx1+1):
        set_px(x,ly1+1,C_OUTLINE)
    # halo: dithered glow around lantern (3px radius checker)
    for y in range(ly0-5, ly1+6):
        for x in range(lx0-5, lx1+6):
            if not (0<=x<W and 0<=y<H):
                continue
            dx,dy=x-cx,y-(ly0+4)
            d=math.hypot(dx,dy)
            if 5<=d<=10:
                if ((x+y)&1)==0 and ((x*2+y)&3)!=0:
                    # only on sky/grass? overwrite with warm glow dither (preserve tower? lampposts away from tower, fine)
                    # don't overwrite tree/outline? keep simple: only if current is sky or grass
                    cur=get_px(x,y)
                    # sky indices + grass: allow halo
                    # check if cur is sky or grass base/mid
                    if cur in SKY or cur in (C_GRASS_B,C_GRASS_M,C_GRASS_D,C_GRASS_L):
                        set_px(x,y,C_SUN_MID)
    # bright core halo denser
    for y in range(ly0-2, ly1+3):
        for x in range(lx0-2, lx1+3):
            dx,dy=x-cx,y-(ly0+4)
            if math.hypot(dx,dy)<6 and ((x+y)&1)==0:
                cur=get_px(x,y)
                if cur in SKY or cur in (C_GRASS_B,C_GRASS_M):
                    set_px(x,y,C_SUN_MID)

draw_lamppost(66, 196)
draw_lamppost(190, 196)

# ---------- EIFFEL TOWER ----------
CX=128
Y_TOP=12; Y_TIPB=18; Y_P3=48; Y_P2=82; Y_P1=128; Y_FEET=176
# platform rows
P1_ROWS=set(range(126,131))
P2_ROWS=set(range(80,85))
P3_ROWS=set(range(46,51))

def outer_half(y):
    if y<Y_TOP or y>Y_FEET: return 0
    if y<=Y_TIPB: # 12-18 tip
        t=(y-Y_TOP)/(Y_TIPB-Y_TOP)
        return 2 + t*2  # 2->4
    elif y<=Y_P3: # 18-48
        t=(y-Y_TIPB)/(Y_P3-Y_TIPB)
        return 4 + t*4  # 4->8
    elif y<=Y_P2: # 48-82
        t=(y-Y_P3)/(Y_P2-Y_P3)
        # slight curve: pow 0.9
        return 8 + (19-8)*(t**0.9)
    elif y<=Y_P1: # 82-128
        t=(y-Y_P2)/(Y_P1-Y_P2)
        return 19 + (37-19)*(t**0.9)
    else: # 128-176
        t=(y-Y_P1)/(Y_FEET-Y_P1)
        return 37 + (56-37)*(t**0.85)

def thick(y):
    return 3 + (y-Y_TOP)/(Y_FEET-Y_TOP)*7

def inner_half(y):
    if y in P1_ROWS or y in P2_ROWS or y in P3_ROWS:
        return None  # solid platform
    if 131<=y<=Y_FEET:
        apex=130; base=Y_FEET; max_inner=46
        t=(y-apex)/(base-apex)
        if t<0: return 0
        return max_inner*(t**0.65)
    elif 85<=y<=125:
        apex=84; base=125; max_inner=29
        # outer at base ~? but use fixed
        t=(y-apex)/(base-apex)
        return max_inner*(t**0.7)
    elif 51<=y<=79:
        apex=50; base=79; max_inner=14
        t=(y-apex)/(base-apex)
        return max_inner*(t**0.7)
    else:
        return None  # solid spire

# first pass: determine tower mask (including platforms overhang)
tower_mask=set()
for y in range(Y_TOP, Y_FEET+1):
    oh=outer_half(y)
    ih=inner_half(y)
    # platform overhang
    is_plat = y in P1_ROWS or y in P2_ROWS or y in P3_ROWS
    if is_plat:
        oh+=4
        x0=int(round(CX-oh)); x1=int(round(CX+oh))
        for x in range(x0,x1+1):
            tower_mask.add((x,y))
    else:
        if ih is None:
            x0=int(round(CX-oh)); x1=int(round(CX+oh))
            for x in range(x0,x1+1):
                tower_mask.add((x,y))
        else:
            if ih<1.0:
                x0=int(round(CX-oh)); x1=int(round(CX+oh))
                for x in range(x0,x1+1):
                    tower_mask.add((x,y))
            else:
                xl0=int(round(CX-oh)); xl1=int(round(CX-ih))
                xr0=int(round(CX+ih)); xr1=int(round(CX+oh))
                for x in range(xl0,xl1+1):
                    tower_mask.add((x,y))
                for x in range(xr0,xr1+1):
                    tower_mask.add((x,y))
    # antenna tip extra? beacon handled later

# base feet: small concrete pedestals 6x4 at bottom
feet_boxes=[(CX-52, Y_FEET-2),(CX+52-6, Y_FEET-2)]  # approx outer feet positions? outer 56 so feet at ±52?
# Actually feet at outer edges: left foot center CX-50, right CX+50
for (fx,fy) in [(CX-50,Y_FEET-4),(CX+50,Y_FEET-4)]:
    for y in range(fy, fy+6):
        for x in range(fx-5, fx+6):
            tower_mask.add((x,y))

# fill base shading per pixel
# gradient west->east dark->light, plus vertical darker at bottom
for (x,y) in tower_mask:
    # platform rows handled separately later (override)
    if y in P1_ROWS or y in P2_ROWS or y in P3_ROWS:
        continue
    # concrete feet?
    if y>=Y_FEET-4 and (abs(x-(CX-50))<=5 or abs(x-(CX+50))<=5):
        # concrete gray? reuse city_far/mid? Use path colors for concrete
        # alternate
        if ((x+y)&1)==0:
            set_px(x,y,C_PATH_L)
        else:
            set_px(x,y,C_PATH_D)
        continue
    oh=outer_half(y)
    # normalized u 0..1 across outer width
    left=CX-oh; right=CX+oh
    span=max(1,right-left)
    u=(x-left)/span
    # vertical adjust
    # bottom darker: shift u down by 0.15 if y>150, top lighter shift up 0.1 if y<40
    if y>150:
        u-=0.15
    elif y>130:
        u-=0.07
    if y<40:
        u+=0.08
    if u<0.18:
        c=C_IRON_D
    elif u<0.36:
        c=C_IRON_MD
    elif u<0.55:
        c=C_IRON_B
    elif u<0.73:
        c=C_IRON_ML
    elif u<0.88:
        c=C_IRON_L
    else:
        c=C_IRON_HL
    set_px(x,y,c)

# lattice overlay (only non-platform, non-feet, where leg width >=6)
for (x,y) in list(tower_mask):
    if y in P1_ROWS or y in P2_ROWS or y in P3_ROWS:
        continue
    if y>=Y_FEET-4:
        continue
    oh=outer_half(y); ih=inner_half(y)
    # determine leg width
    if ih is None:
        leg_w = oh*2
        if leg_w<6:
            continue
    else:
        if ih<1: 
            leg_w=oh*2
            if leg_w<6: continue
        else:
            leg_w = oh - ih
            if leg_w<5: continue
    # lattice: diagonals every 8px (sparser for cleaner ironwork)
    # use two patterns: (x + y*2) %8==0 and (x - y*2)%8==0
    d1=(x + y*2)%8
    d2=(x - y*2)%8
    # horizontal beam every 12px
    hb = (y%12==0)
    if d1==0 or d2==0 or hb:
        # don't overwrite highlight edge? keep lattice dark but preserve outermost highlight? allow
        # checker to keep some base visible? lattice lines 1px
        # intersections -> rivet?
        if d1==0 and d2==0:
            set_px(x,y,C_RIVET)
        else:
            set_px(x,y,C_LATTICE)
    # rivets along edges: every 6px small light dot just inside outer? 
    # handle separately below

# rivet dots along leg edges every 8px (inner and outer)
for y in range(Y_TOP, Y_FEET):
    if y%8!=0: continue
    if y in P1_ROWS or y in P2_ROWS or y in P3_ROWS: continue
    oh=int(round(outer_half(y))); ih=inner_half(y)
    # outer edges
    for x in (CX-oh+1, CX+oh-1):
        if (x,y) in tower_mask:
            # only if not lattice already?
            set_px(x,y,C_RIVET)
    if ih is not None and ih>=1:
        ihi=int(round(ih))
        for x in (CX-ihi-1, CX+ihi+1):
            if (x,y) in tower_mask:
                set_px(x,y,C_RIVET)

# platforms: fill deck + railing
for prow, label in [(P1_ROWS,"P1"),(P2_ROWS,"P2"),(P3_ROWS,"P3")]:
    for y in prow:
        oh=int(round(outer_half(y)))+4
        x0=CX-oh; x1=CX+oh
        for x in range(x0,x1+1):
            if y==min(prow):
                # top rail highlight
                set_px(x,y,C_IRON_L if (x&1)==0 else C_IRON_ML)
            elif y==min(prow)+1:
                # railing posts alternating
                if (x%4)==0:
                    set_px(x,y,C_PLAT)
                else:
                    # glass / gap showing sky? Actually railing gap shows sky behind? For simplicity fill with warm lit? Use sun_mid dither for lit interior?
                    # keep platform dark with light dots (crowd/lights)
                    if (x%6)==0:
                        set_px(x,y,C_SUN_MID)
                    else:
                        set_px(x,y,C_PLAT)
                # top rail shadow?
            elif y==max(prow):
                set_px(x,y,C_IRON_D)  # underside shadow
            else:
                set_px(x,y,C_PLAT)
                # under-deck lights: small yellow dots
                if (x%8)==0 and y==max(prow)-1:
                    set_px(x,y,C_SUN_MID)
    # railing top outline? will be handled by outer outline pass
    # add support struts under platform (triangles)
    y_under=max(prow)+1
    # small brackets every 8px
    oh=int(round(outer_half(max(prow))))+4
    for x in range(CX-oh, CX+oh+1, 8):
        if (x,y_under) not in tower_mask:
            # bracket pixel below deck
            set_px(x,y_under,C_LATTICE)
            # tower_mask.add((x,y_under)) # don't add to mask to avoid outline confusion? add?
            tower_mask.add((x,y_under))

# arch trim: inner edge highlight (rim light on east side)
for y in range(Y_TOP, Y_FEET+1):
    ih=inner_half(y)
    if ih is None or ih<1: continue
    ihi=int(round(ih))
    # east inner edges (left leg inner = CX-ihi, right leg inner=CX+ihi)
    # left leg inner faces east (lit) -> highlight
    x=CX-ihi-1
    if (x,y) in tower_mask:
        # only highlight if on east side? set to light?
        cur=get_px(x,y)
        # override with highlight if currently mid/base?
        if y<150:  # not too dark bottom
            set_px(x,y,C_IRON_L)
    # right leg inner faces west (shadow) -> keep dark, ensure dark
    x2=CX+ihi+1
    if (x2,y) in tower_mask:
        set_px(x2,y,C_IRON_D)
    # outer rim: right outer highlight, left outer shadow (already via gradient, enforce)
    oh=int(round(outer_half(y)))
    xo_left=CX-oh
    xo_right=CX+oh
    if (xo_left,y) in tower_mask:
        set_px(xo_left,y,C_IRON_D)
    if (xo_right,y) in tower_mask:
        set_px(xo_right,y,C_IRON_HL)

# outline pass: expand 1px around tower_mask (including platforms, brackets, feet)
# Need background snapshot? Just set neighbors to outline if not in mask
neighbors=[(1,0),(-1,0),(0,1),(0,-1)]
# also diagonals for corners? use 4-dir only for crisp
to_outline=set()
for (x,y) in tower_mask:
    for dx,dy in neighbors:
        nx,ny=x+dx,y+dy
        if not (0<=nx<W and 0<=ny<H): continue
        if (nx,ny) not in tower_mask:
            to_outline.add((nx,ny))
for (x,y) in to_outline:
    set_px(x,y,C_OUTLINE)
# inner outline? For arch openings, the edge pixels of legs touching opening (empty) already got outer outline via above (opening empty pixels set to outline). But that would fill arch opening border with outline, narrowing opening by 1px outward? Actually we set empty neighbor to outline, so outline sits in the opening (background), preserving leg width. Good.
# However legs edge pixels themselves remain shaded, outline is outside. For solid sections, outline outside too. Good.

# floodlights / sparkle lights up tower (Eiffel sparkles): small warm dots along outer edges every 8px
for y in range(Y_TOP+4, Y_FEET, 8):
    if y in P1_ROWS or y in P2_ROWS or y in P3_ROWS: continue
    oh=int(round(outer_half(y)))
    for x in (CX-oh, CX+oh):
        # place just inside outline? outline is outside, so x is edge shaded pixel -> add sparkle on top? offset inside 1?
        # use rivet already there; add glow above?
        # place sparkle 1px inside
        xi = x+1 if x<CX else x-1
        if (xi,y) in tower_mask:
            set_px(xi,y,C_SUN_MID)
# horizontal sparkle line on platforms
for prow in [P1_ROWS,P2_ROWS,P3_ROWS]:
    y=min(prow)
    oh=int(round(outer_half(y)))+4
    for x in range(CX-oh, CX+oh+1, 6):
        set_px(x,y,C_BEACON_W if (x&1)==0 else C_SUN_MID)

# beacon on tip
# antenna: 2px wide from Y_TOP-6 to Y_TOP
for y in range(Y_TOP-6, Y_TOP+1):
    set_px(CX,y,C_OUTLINE)
    # tower_mask.add((CX,y)) # not needed
# beacon light 3x3
bx,by=CX,Y_TOP-8
for dy in range(-1,2):
    for dx in range(-1,2):
        if abs(dx)+abs(dy)<=1:
            set_px(bx+dx,by+dy,C_BEACON_R)
        elif abs(dx)<=1 and abs(dy)<=1:
            set_px(bx+dx,by+dy,C_BEACON_W)
# beacon halo dither
for dy in range(-3,4):
    for dx in range(-3,4):
        if max(abs(dx),abs(dy))==3 and ((bx+dx+by+dy)&1)==0:
            # only on sky
            cur=get_px(bx+dx,by+dy)
            if cur in SKY:
                set_px(bx+dx,by+dy,C_BEACON_R)

# searchlight beams from top? subtle SNES sparkle beams (two diagonal translucent beams)
# left beam
for t in range(1,40):
    x=CX - t
    y=by - t//3
    if 0<=x<W and 0<=y<H:
        if ((x+y)&1)==0:
            cur=get_px(x,y)
            if cur in SKY or cur==C_STAR:
                set_px(x,y,C_CLOUD_L)
for t in range(1,40):
    x=CX + t
    y=by - t//3
    if 0<=x<W and 0<=y<H:
        if ((x+y)&1)==0:
            cur=get_px(x,y)
            if cur in SKY or cur==C_STAR:
                set_px(x,y,C_CLOUD_L)

# ---------- BIRDS ----------
def draw_bird(cx,cy,s=1):
    # simple "m" shape 5x2
    set_px(cx-2*s,cy,C_BIRD)
    set_px(cx-1*s,cy-1,C_BIRD)
    set_px(cx,cy,C_BIRD)
    set_px(cx+1*s,cy-1,C_BIRD)
    set_px(cx+2*s,cy,C_BIRD)
    # outline? keep single color, will be counted. Ensure not too many colors in tile - single color fine
draw_bird(78,52,1)
draw_bird(90,60,1)
draw_bird(70,68,1)

# ---------- FOREGROUND BUSHES / FLOWERS FRONT ----------
random.seed(777)
for _ in range(6):
    x=random.randint(10,W-10)
    y=random.randint(205,220)
    if in_path(x,y):
        continue
    # small bush 8x5
    for dy in range(-3,2):
        for dx in range(-5,6):
            if dx*dx/25+dy*dy/9<=1:
                xx,yy=x+dx,y+dy
                if 0<=xx<W and 0<=yy<H and not in_path(xx,yy):
                    # shade
                    if dy<-1:
                        set_px(xx,yy,C_LEAF_L if (xx+yy)&1==0 else C_LEAF_M)
                    elif dy>0:
                        set_px(xx,yy,C_LEAF_D if (xx+yy)&1==0 else C_LEAF_B)
                    else:
                        set_px(xx,yy,C_LEAF_M)

# bench? small SNES bench left of path
def draw_bench(cx,by):
    # legs
    for x in (cx-8,cx+8):
        for y in range(by-6,by+1):
            set_px(x,y,C_TRUNK_D)
            set_px(x+1,y,C_TRUNK_D)
    # seat
    for x in range(cx-10,cx+11):
        set_px(x,by-6,C_TRUNK_M)
        set_px(x,by-7,C_TRUNK_M)
        if (x&1)==0:
            set_px(x,by-7,C_PATH_L)  # highlight
    # backrest
    for x in range(cx-10,cx+11):
        set_px(x,by-12,C_TRUNK_M)
        set_px(x,by-13,C_TRUNK_D)
    for x in (cx-10,cx+10):
        for y in range(by-12,by-6):
            set_px(x,y,C_TRUNK_D)
draw_bench(48,214)
draw_bench(208,214)

# ---------- HUD? No, keep pure scene. Add subtle bottom vignette? No.

# ---------- VERIFY CONSTRAINTS ----------
# count distinct RGB actually used
used=set()
for y in range(H):
    for x in range(W):
        c=buf[y][x]
        # resolve remap already? buf already remapped? set_px remapped, good
        # palette RGB
        _,r,g,b=PAL[c]
        used.add((r,g,b))
print(f"Used distinct colors: {len(used)} (limit 128)")
# tile check
def tile_colors(tx,ty):
    s=set()
    for y in range(ty*8, ty*8+8):
        for x in range(tx*8, tx*8+8):
            s.add(buf[y][x])
    return s

violations=[]
for ty in range(H//8):
    for tx in range(W//8):
        s=tile_colors(tx,ty)
        # count distinct RGB (since duplicates remapped, same)
        # need distinct RGB, but buf indices already deduped, so len(s) is distinct RGB
        if len(s)>16:
            violations.append((tx,ty,len(s),s))
print(f"Tiles violating >16 colors: {len(violations)}")
for tx,ty,n,s in violations[:10]:
    print(f" tile {tx},{ty} n={n}")

# Fix violations by merging to 16 most frequent
if violations:
    from collections import Counter
    for tx,ty,n,s in violations:
        # count freq
        cnt=Counter()
        for y in range(ty*8,ty*8+8):
            for x in range(tx*8,tx*8+8):
                cnt[buf[y][x]]+=1
        most=cnt.most_common(16)
        keep=set(k for k,_ in most)
        # for others, map to nearest kept by RGB distance
        # precompute palette RGB
        def rgb(idx):
            _,r,g,b=PAL[idx]
            return (r,g,b)
        keep_rgbs={k:rgb(k) for k in keep}
        for y in range(ty*8,ty*8+8):
            for x in range(tx*8,tx*8+8):
                c=buf[y][x]
                if c not in keep:
                    r,g,b=rgb(c)
                    best=None; bestd=1e9
                    for k,(kr,kg,kb) in keep_rgbs.items():
                        d=(r-kr)**2+(g-kg)**2+(b-kb)**2
                        if d<bestd:
                            bestd=d; best=k
                    buf[y][x]=best
    # recheck
    violations2=[]
    for ty in range(H//8):
        for tx in range(W//8):
            if len(tile_colors(tx,ty))>16:
                violations2.append((tx,ty))
    print(f"After fix violations: {len(violations2)}")
    # recount used
    used2=set()
    for y in range(H):
        for x in range(W):
            _,r,g,b=PAL[buf[y][x]]
            used2.add((r,g,b))
    print(f"Used after fix: {len(used2)}")

# ---------- WRITE PNG (truecolor, no palette chunk to keep simple, but colors still limited) ----------
# Build RGB bytes
raw=bytearray()
for y in range(H):
    raw.append(0)  # filter 0
    for x in range(W):
        _,r,g,b=PAL[buf[y][x]]
        raw.extend([r,g,b])

def chunk(typ,data):
    l=struct.pack(">I",len(data))
    c=typ+data
    crc=struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    return l+c+crc

sig=b'\x89PNG\r\n\x1a\n'
ihdr=struct.pack(">IIBBBBB",W,H,8,2,0,0,0)
idat=zlib.compress(bytes(raw),9)
png=sig+chunk(b'IHDR',ihdr)+chunk(b'IDAT',idat)+chunk(b'IEND',b'')
open("output/eiffel_snes.png","wb").write(png)
print(f"Wrote output/eiffel_snes.png {len(png)} bytes, {W}x{H}")

# also write report
used_final=set()
for y in range(H):
    for x in range(W):
        _,r,g,b=PAL[buf[y][x]]
        used_final.add((r,g,b))
print("FINAL distinct:",len(used_final))
# max per tile
mx=max(len(tile_colors(tx,ty)) for ty in range(H//8) for tx in range(W//8))
print("FINAL max per tile:",mx)
