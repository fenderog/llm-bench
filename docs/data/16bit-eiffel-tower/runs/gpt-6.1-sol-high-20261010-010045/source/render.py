"""A small, dependency-free SNES-style Paris postcard renderer.
Native indexed pixels only: 256x224, <=128 global colors, <=16 per 8x8 tile.
Run with python3 render.py. The only deliverable is output/eiffel_at_sunset.png.
"""
import math
import random
import struct
import zlib
from pathlib import Path
from collections import Counter

W, H = 256, 224
palette = []
names = {}
def color(name, hexcode):
    rgb = tuple(bytes.fromhex(hexcode))
    if rgb not in palette:
        palette.append(rgb)
    names[name] = palette.index(rgb)
    return names[name]

# Carefully grouped, shared ramp colors: no interpolation or antialiasing.
SKY = [color('sky'+str(i), h) for i,h in enumerate([
    '303d68','3e4b78','515886','666391','7d6c98','95779d',
    'b086a4','c999ac','dcacb3','edbdb5','f3c9b9','f7d4ba'])]
ink = color('ink','292a46')
cloud_dark = color('cloud shadow','8b7297')
cloud_mid = color('cloud body','b38ba5')
cloud_light = color('cloud light','e7b1b2')
cloud_rim = color('cloud rim','f7cebc')
sun = color('sun','ffe6ad')
sun_rim = color('sun rim','ffda9f')
sun_core = color('sun core','fff0c2')
far = color('distant city','9b849c')
far_light = color('distant city light','b59caa')
roof = color('roofs','625a7b')
roof_light = color('roof light','82738e')
wall = color('walls','b39d9c')
wall_light = color('wall light','d6b6a8')
wall_shade = color('wall shade','958697')
win = color('window shade','736b86')
win_light = color('window amber','efc69c')
leaf_dark = color('leaf dark','34344f')
leaf_mid = color('leaf middle','414459')
leaf_light = color('leaf light','565467')
leaf_warm = color('leaf sunward','7e6973')
leaf_gold = color('leaf gold','ad847b')
trunk = color('trunk','4d4054')
steel_dark = color('steel outline','393044')
steel_shade = color('steel shade','604150')
steel = color('steel','8b5856')
steel_mid = color('steel lit','b07764')
steel_light = color('steel highlight','d39a72')
steel_gold = color('steel gold','f0ba80')
steel_glow = color('steel glint','ffe0a0')
stone_dark = color('stone dark','55495f')
stone = color('stone','8f7b86')
stone_light = color('stone light','c2a091')
stone_rim = color('stone rim','e3ba99')
water = [color('water'+str(i), h) for i,h in enumerate([
    '414865','505571','64647e','7d778b','9b8998','c59da3'])]
reflection = color('water gold','edbd9d')
flower = color('flower','c27f8a')
pixels = [[SKY[0] for x in range(W)] for y in range(H)]
rng = random.Random(1632)

def put(x,y,c):
    if 0 <= x < W and 0 <= y < H:
        pixels[y][x] = c

def rect(x0,y0,x1,y1,c):
    for y in range(max(0,y0), min(H,y1+1)):
        for x in range(max(0,x0), min(W,x1+1)):
            pixels[y][x] = c

def line(x0,y0,x1,y1,c,width=1):
    dx,dy=abs(x1-x0),abs(y1-y0)
    sx=1 if x0<x1 else -1
    sy=1 if y0<y1 else -1
    err=dx-dy
    while True:
        rect(x0-(width-1)//2,y0-(width-1)//2,x0+width//2,y0+width//2,c)
        if x0==x1 and y0==y1: break
        e=2*err
        if e>-dy: err-=dy; x0+=sx
        if e<dx: err+=dx; y0+=sy

def poly(points,c,restore=None):
    # Pixel-centre scan conversion, including the outline endpoints.
    ys=[p[1] for p in points]
    for y in range(max(0,min(ys)),min(H-1,max(ys))+1):
        xs=[]
        for (ax,ay),(bx,by) in zip(points,points[1:]+points[:1]):
            if ay==by: continue
            if min(ay,by)<=y<max(ay,by):
                xs.append(ax+(y-ay)*(bx-ax)/(by-ay))
        xs.sort()
        for i in range(0,len(xs)-1,2):
            for x in range(max(0,math.ceil(xs[i])),min(W-1,math.floor(xs[i+1]))+1):
                pixels[y][x] = restore[y][x] if restore else c

def ellipse(cx,cy,rx,ry,c):
    for y in range(max(0,cy-ry), min(H,cy+ry+1)):
        span=int(rx*math.sqrt(max(0,1-((y-cy)/ry)**2))) if ry else rx
        rect(cx-span,y,cx+span,y,c)

# Sky: long solid bands with restrained ordered-dither joins.
boundaries=[0,17,33,48,63,77,91,105,119,135,153,173]
for y in range(185):
    k=max(i for i,b in enumerate(boundaries) if y>=b)
    for x in range(W):
        c=SKY[k]
        if k<11:
            d=boundaries[k+1]-y
            if d<=3 and ((x&3)+2*(y&1))%4 >= d:
                c=SKY[k+1]
        put(x,y,c)
# Discreet evening stars, not a noisy starfield.
for x,y in [(20,18),(49,10),(78,28),(108,12),(155,19),(212,15),(238,32)]:
    put(x,y,SKY[7])
    if x==49 or x==212:
        put(x-1,y,SKY[3]);put(x+1,y,SKY[3]);put(x,y-1,SKY[3])

# Low golden disk. The rim and horizontal obscuration are all hard pixel edges.
ellipse(182,105,26,26,sun_rim)
ellipse(182,104,24,24,sun)
ellipse(179,100,19,19,sun_core)
for yy,x0,x1 in [(116,157,163),(120,159,170),(125,165,194)]:
    rect(x0,yy,x1,yy,SKY[8])

# Pixel-cloud banks: sculpted contours, layered warm edges, no soft brushes.
def cloud(x,y,scale=1):
    pts=[(0,10),(8,10),(8,7),(16,7),(16,4),(24,4),(24,0),(35,0),
         (35,2),(43,2),(43,6),(55,6),(55,8),(69,8),(69,11),(80,11),
         (80,14),(65,14),(65,16),(20,16),(20,14),(0,14)]
    p=[(x+int(a*scale),y+int(b*scale)) for a,b in pts]
    poly(p,cloud_dark)
    poly([(x+int(a*scale),y+int(b*scale)-2) for a,b in pts],cloud_mid)
    line(x+int(16*scale),y+int(4*scale)-2,x+int(24*scale),y+int(4*scale)-2,cloud_light)
    line(x+int(24*scale),y-2,x+int(34*scale),y-2,cloud_light)
    line(x+int(35*scale),y,x+int(43*scale),y,cloud_light)
    line(x+int(43*scale),y+int(6*scale)-2,x+int(54*scale),y+int(6*scale)-2,cloud_rim)
    rect(x+int(20*scale),y+int(12*scale),x+int(47*scale),y+int(13*scale),cloud_light)
    rect(x+int(33*scale),y+int(14*scale),x+int(69*scale),y+int(14*scale),cloud_mid)
cloud(-18,55,1.0)
cloud(176,41,1.12)
cloud(39,91,.66)
# Long, broken lower cloud streaks.
for x0,x1,y,c in [(0,33,114,cloud_light),(4,44,116,cloud_mid),(212,255,101,cloud_light),
                   (220,255,103,cloud_mid),(47,72,123,cloud_rim),(55,89,125,cloud_light),
                   (144,177,137,cloud_light),(147,193,139,cloud_mid)]:
    rect(x0,y,x1,y+1,c)

# Far Paris silhouette: chimneys and a distant copper dome.
for x in range(0,256,5):
    h=rng.randrange(5,16)
    rect(x,160-h,x+4,174,far)
    if rng.random()<.55:rect(x+1,157-h,x+2,161-h,far)
rect(193,142,207,165,far)
ellipse(200,143,7,8,far)
rect(198,132,202,139,far)
line(200,128,200,133,far)
line(195,143,205,143,far_light)
# Mansard roofs, narrow buildings and hand-placed lit windows.
for x,bw,top in [(-6,21,155),(15,16,151),(31,22,157),(53,17,153),(70,20,160),
                 (89,16,156),(158,16,158),(174,18,151),(192,23,157),(215,19,153),(234,23,157)]:
    rect(x,top+5,x+bw-1,181,wall)
    rect(x+bw-5,top+5,x+bw-1,181,wall_shade)
    poly([(x-1,top+5),(x+3,top-1),(x+bw-5,top-1),(x+bw,top+5)],roof)
    line(x+3,top-1,x+bw-5,top-1,roof_light)
    rect(x+4,top-6,x+6,top-1,roof)
    rect(x+3,top-6,x+7,top-6,roof_light)
    line(x,top+6,x+bw-1,top+6,wall_light)
    for yy in range(top+10,180,6):
        for xx in range(x+3,x+bw-3,5):
            rect(xx,yy,xx+1,yy+2,win)
            if rng.random()<.30: put(xx,yy+1,win_light)
        if yy+4<179:line(x,yy+4,x+bw-5,yy+4,wall_shade)
    for xx in range(x+5,x+bw-3,7):
        rect(xx,top+1,xx+1,top+3,wall_light)
        put(xx,top+1,win)

# Embankment and water ground planes.
rect(0,181,255,190,stone)
rect(0,182,255,182,stone_light)
rect(0,189,255,192,stone_dark)
rect(0,192,255,194,stone_light)
rect(0,195,255,196,stone_dark)
for y in range(197,224):
    base=water[max(0,3-(y-197)//7)]
    rect(0,y,255,y,base)
    # Long horizontal pixel-clusters, weighted toward the sunset.
    for n in range(7):
        x=rng.randrange(256);length=rng.randrange(4,24)
        c=water[min(5,max(0,4-(y-197)//9))]
        rect(x,y,x+length,y,c)
for y in range(198,224,2):
    spread=6+(y-198)//2
    for n in range(3):
        x=182+rng.randint(-spread,spread)
        rect(x,y,x+rng.randint(2,9),y,reflection if n==0 else water[5])
# Reflection of the tower is fractured, rather than a perfect mirror.
for y in range(198,223,3):
    x=128+rng.randrange(-5,4)
    rect(x-3,y,x+4,y,steel_shade)
    rect(x-9,y+1,x+8,y+1,water[0])
    if y<213:rect(x,y,x+2,y,steel_mid)
# Masonry courses and railing.
for y in (185,188):
    for x in range((y%2)*6,256,15):line(x,y,x,y+2,stone_dark)
line(0,178,255,178,stone_dark)
line(0,181,255,181,stone_dark)
for x in range(2,256,6):line(x,178,x,181,stone_dark)
for x in range(0,256,24):rect(x,177,x+1,184,stone_dark);put(x,177,stone_rim)

# Dense chestnut trees. Clumps use shared three-shade ramps, with clustered
# highlight pixels instead of uniformly scattered noise.
def tree(cx,cy,rx,ry):
    line(cx,cy,cx-1,185,trunk,3)
    line(cx,cy+8,cx-10,cy-2,trunk,2)
    ellipse(cx,cy,rx,ry,leaf_dark)
    for i in range(14):
        a=rng.random()*math.tau
        r=rng.random()**.5
        xx=int(cx+math.cos(a)*rx*r*.8)
        yy=int(cy+math.sin(a)*ry*r*.8)
        rr=rng.randint(4,8)
        ellipse(xx,yy,rr,rr-1,leaf_mid)
        if i%3!=0:
            ellipse(xx-1,yy-2,max(2,rr-2),max(2,rr-3),leaf_light)
        if xx>cx+rx//4:
            line(xx,yy-3,xx+2,yy-3,leaf_warm)
    for i in range(10):
        xx=rng.randint(cx-rx+3,cx+rx-3); yy=rng.randint(cy-ry+3,cy+ry-3)
        if 0<=xx<W and 0<=yy<H and pixels[yy][xx] in (leaf_light,leaf_mid):
            put(xx,yy,leaf_warm)
            if i%4==0:put(xx+1,yy,leaf_gold)
for args in [(0,156,17,24),(19,160,18,22),(40,165,15,19),(58,173,11,13),
             (256,153,20,27),(234,160,17,23),(215,171,13,16),(203,176,9,10)]:tree(*args)
# A few shrubs beside the paving.
for x in (3,10,18,229,238,247):
    ellipse(x,186,6,3,leaf_dark)
    put(x-2,184,leaf_warm);put(x+1,185,flower)

# Save the background to cut actual openings through the ironwork.
bg=[row[:] for row in pixels]
# Top antenna and beacon.
line(128,17,128,32,steel_dark)
line(127,25,127,33,steel_light)
put(128,16,steel_gold)
rect(126,32,130,36,steel_shade)
line(126,33,128,33,steel_gold)
poly([(126,35),(130,35),(133,49),(123,49)],steel_dark)
poly([(126,36),(128,36),(130,48),(124,48)],steel_mid)
line(126,36,124,47,steel_gold)
# Summit gallery: tiny enclosed room, cornice and guard rails.
rect(121,46,135,47,steel_dark)
rect(122,45,134,45,steel_light)
rect(123,48,133,52,steel_shade)
for x in (124,127,130):rect(x,48,x+1,50,steel_dark)
line(123,52,133,52,steel_gold)
line(123,43,133,43,steel_dark)
for x in (123,126,130,133):put(x,44,steel_mid)

# Long taper, with see-through triangles and alternating diagonal bracing.
shaft=[(124,53),(132,53),(141,94),(115,94)]
poly(shaft,steel_dark)
poly([(125,53),(128,53),(120,93),(117,93)],steel_mid)
poly([(128,53),(131,53),(139,93),(132,93)],steel_shade)
for y0,y1 in [(54,61),(62,70),(71,80),(81,91)]:
    l0=round(124-(y0-53)*9/41);r0=256-l0
    l1=round(124-(y1-53)*9/41);r1=256-l1
    poly([(l0+2,y0+1),(r0-2,y0+1),(128,y1-2)],0,restore=bg)
    poly([(l1+2,y1-1),(128,y0+3),(r1-2,y1-1)],0,restore=bg)
    line(l0,y0,r1,y1,steel_mid)
    line(r0,y0,l1,y1,steel_light)
    line(l1,y1,r1,y1,steel_shade)
    line(l1,y1,l1+4,y1,steel_gold)
line(124,53,115,93,steel_gold)
line(132,53,141,93,steel_shade)
# Second observation floor.
rect(111,92,145,96,steel_dark)
rect(113,91,143,91,steel_mid)
line(112,93,143,93,steel_gold)
line(113,96,143,96,steel_mid)
for x in range(114,144,3):put(x,94,steel_mid)
# Rail above deck.
line(114,89,142,89,steel_shade)
for x in range(115,143,3):put(x,90,steel_light)

# Middle frame, its large open diamonds and broad crossed girders.
poly([(116,97),(140,97),(151,138),(105,138)],steel_dark)
poly([(117,98),(121,98),(112,137),(107,137)],steel_mid)
poly([(135,98),(139,98),(149,137),(143,137)],steel_shade)
poly([(123,99),(133,99),(128,111)],0,restore=bg)
poly([(121,102),(124,113),(115,126)],0,restore=bg)
poly([(135,102),(132,113),(141,126)],0,restore=bg)
poly([(126,118),(114,135),(142,135),(130,118)],0,restore=bg)
line(119,99,144,136,steel_mid,2)
line(137,99,112,136,steel_light,2)
line(119,99,144,136,steel_shade)
line(137,99,112,136,steel_gold)
line(116,98,106,138,steel_gold)
line(140,98,150,138,steel_mid)
# Small cross panels in the curved side girders.
for y in range(103,136,6):
    left=116-round((y-97)*10/41)
    right=256-left
    line(left,y,left+5,y+5,steel_shade)
    line(left+5,y,left,y+5,steel_light)
    line(right-5,y,right,y+5,steel_mid)
    line(right,y,right-5,y+5,steel_dark)
line(113,113,143,113,steel_mid)
line(112,114,144,114,steel_dark)

# Lower arch and splayed feet. Curving boundary follows a pixel staircase.
arch=[(106,146),(150,146),(153,158),(158,171),(166,181),(171,185),
      (153,185),(146,173),(142,164),(137,159),(132,157),(124,157),
      (119,159),(114,164),(110,173),(103,185),(85,185),(90,181),
      (98,171),(103,158)]
poly(arch,steel_dark)
poly([(107,147),(117,147),(111,162),(106,174),(100,183),(89,183),
      (99,168),(104,155)],steel_mid)
poly([(139,147),(149,147),(152,160),(158,174),(167,183),(155,183),
      (147,169),(143,157)],steel_shade)
# Arch rim, warm on the left and shaded on its underside.
arc=[(102,182),(108,170),(113,161),(119,156),(126,153),(130,153),
     (137,156),(143,161),(148,170),(154,182)]
for a,b in zip(arc,arc[1:]):line(*a,*b,steel_light,2)
for a,b in zip(arc[1:],arc[2:]):line(a[0]+1,a[1]+2,b[0]+1,b[1]+2,steel_shade)
# Each foot has its own open, crisscrossed panels.
for ltop,rtop,lbot,rbot,y0,y1 in [
    (106,113,102,109,150,159),(103,110,98,105,161,170),
    (98,105,89,100,172,182),(143,150,147,154,150,159),
    (146,153,151,158,161,170),(151,158,156,166,172,182)]:
    poly([(ltop+2,y0+1),(rtop-1,y0+1),((lbot+rbot)//2,y1-2)],0,restore=bg)
    poly([(lbot+2,y1-1),((ltop+rtop)//2,y0+2),(rbot-2,y1-1)],0,restore=bg)
    line(ltop,y0,rbot,y1,steel_light)
    line(rtop,y0,lbot,y1,steel_shade)
    line(lbot,y1,rbot,y1,steel_mid)
# Main outer edges catch the low sunlight.
for a,b in zip([(106,148),(102,161),(97,174),(88,183)],[(102,161),(97,174),(88,183)]):
    line(*a,*b,steel_gold)
line(149,148,154,167,steel_mid)
line(154,167,168,184,steel_mid)
# The first floor's projecting cornice and enclosed observation gallery.
rect(99,137,157,145,steel_dark)
rect(100,137,156,138,steel_light)
rect(102,140,154,143,steel_shade)
for x in range(103,154,4):
    rect(x,140,x+1,142,steel_dark)
    put(x+2,140,steel_mid)
line(99,139,157,139,steel_gold)
line(101,144,155,144,steel_mid)
line(103,146,153,146,steel_dark)
# Exposed balcony railing with glints, separate from its floor.
line(103,134,153,134,steel_shade)
for x in range(104,154,3):line(x,135,x,136,steel_mid)
line(103,134,124,134,steel_light)
for x,y in [(112,93),(118,81),(124,52),(101,139),(109,139),(117,139),(137,139),(95,177)]:
    put(x,y,steel_glow)
# Masonry shoes anchor the tower to its plaza.
for x0,x1 in [(84,102),(154,172)]:
    rect(x0,184,x1,187,stone_dark)
    rect(x0,184,x1,184,stone_rim)
    rect(x0+1,185,x1-1,186,stone)
    line(x0+2,185,x0+8,185,stone_light)
# Plaza contact shadows and small paving highlights.
line(81,188,111,188,stone_dark)
line(148,188,176,188,stone_dark)
line(111,185,145,185,stone_light)
line(116,187,139,187,stone_rim)

# Elegant park lamps framing the landmark (unobtrusive, 1px ironwork).
def lamp(x,y):
    line(x,y+5,x,188,ink)
    rect(x-1,187,x+1,188,ink)
    poly([(x-3,y),(x+3,y),(x+2,y+6),(x-2,y+6)],ink)
    rect(x-1,y+1,x+1,y+4,sun)
    put(x,y+1,sun_core)
    line(x-3,y-1,x+3,y-1,ink)
    put(x,y-3,ink)
    put(x-3,y+2,stone_light);put(x+3,y+2,stone_light)
lamp(72,164)
lamp(185,164)
# A couple on the promenade gives a tiny human scale.
for x,y,c in [(119,182,steel_shade),(123,183,ink)]:
    rect(x,y-3,x+1,y-2,c)
    rect(x-1,y-1,x+2,y+1,c)
    put(x,y+2,c);put(x+2,y+2,c)
put(119,178,steel_gold)

# Enforce the requested tile color budget. Eliminate least-used shades first,
# always replacing with a nearby existing tile shade, keeping the global ramp.
def distance(a,b):
    r,g,b0=palette[a];s,t,u=palette[b]
    return 2*(r-s)**2+3*(g-t)**2+2*(b0-u)**2
changed=0
for ty in range(0,H,8):
    for tx in range(0,W,8):
        counts=Counter(pixels[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8))
        while len(counts)>16:
            # Favor merging low-frequency near-identical colors, not hard outlines.
            candidates=[]
            for a,n in counts.items():
                b=min((b for b in counts if b!=a),key=lambda b:distance(a,b))
                candidates.append((distance(a,b)*n,a,b))
            _,a,b=min(candidates)
            for y in range(ty,ty+8):
                for x in range(tx,tx+8):
                    if pixels[y][x]==a: pixels[y][x]=b;changed+=1
            counts[b]+=counts.pop(a)

used=set(v for row in pixels for v in row)
max_tile=max(len({pixels[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)})
             for ty in range(0,H,8) for tx in range(0,W,8))
assert len(used)<=128 and max_tile<=16

def chunk(t,data):
    return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data)&0xffffffff)
raw=b''.join(b'\x00'+bytes(row) for row in pixels)
plte=b''.join(bytes(rgb) for rgb in palette)
png=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))
     +chunk(b'PLTE',plte)+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))
Path('output').mkdir(exist_ok=True)
Path('output/eiffel_at_sunset.png').write_bytes(png)
print(f'256x224 indexed PNG; {len(used)} used colors; maximum {max_tile} colors per 8x8 tile; {changed} pixels reconciled; {len(png)} bytes.')
