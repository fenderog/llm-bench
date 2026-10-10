#!/usr/bin/env python3
"""Draw an original, limited-palette 16-bit-style Paris scene without dependencies.
Render at 400 x 500, then nearest-neighbour enlarge and encode as a 4:4:4 JPG.
"""
import math
import random
import subprocess
from pathlib import Path

W, H = 400, 500
random.seed(1889)
pixels = bytearray(W * H * 3)

def rgb(c):
    if isinstance(c, str):
        return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
    return c

def dot(x, y, c):
    x, y = int(x), int(y)
    if 0 <= x < W and 0 <= y < H:
        k = (y * W + x) * 3
        pixels[k:k+3] = bytes(rgb(c))

def rect(x0, y0, x1, y1, c):
    x0, x1 = max(0, int(x0)), min(W - 1, int(x1))
    y0, y1 = max(0, int(y0)), min(H - 1, int(y1))
    if x0 > x1 or y0 > y1:
        return
    row = bytes(rgb(c)) * (x1 - x0 + 1)
    for y in range(y0, y1 + 1):
        k = (y * W + x0) * 3
        pixels[k:k+len(row)] = row

def poly(points, c):
    for y in range(max(0, math.ceil(min(p[1] for p in points))), min(H-1, math.floor(max(p[1] for p in points)))+1):
        xs = []
        for a, b in zip(points, points[1:] + points[:1]):
            if (a[1] <= y < b[1]) or (b[1] <= y < a[1]):
                xs.append(a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            rect(math.ceil(xs[i]), y, math.floor(xs[i+1]), y, c)

def line(x0, y0, x1, y1, c, width=1):
    x0,y0,x1,y1 = map(round, (x0,y0,x1,y1))
    dx, dy = abs(x1-x0), -abs(y1-y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx+dy
    while True:
        rect(x0-(width-1)//2, y0-(width-1)//2, x0+width//2, y0+width//2, c)
        if x0 == x1 and y0 == y1:
            break
        e = 2*err
        if e >= dy:
            err += dy; x0 += sx
        if e <= dx:
            err += dx; y0 += sy

def circle(cx, cy, r, c):
    for y in range(cy-r, cy+r+1):
        span = int(math.sqrt(max(0, r*r-(y-cy)**2)))
        rect(cx-span, y, cx+span, y, c)

# Restrained, stepped and dithered sunset palette: no anti-aliased pixels.
sky = ['#222744','#2b2c50','#35325d','#433a6b','#544273','#674b7b',
       '#7d5681','#956286','#af708a','#c8808f','#df9498','#eda89f',
       '#f3b9a5','#f8c9af','#f9d4b5']
threshold = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
for y in range(H):
    t = min(14, y/24.0)
    lo = int(t)
    fraction = t-lo
    for x in range(W):
        # Most of each band is flat; small ordered transitions preserve pixel texture.
        idx = min(14, lo + (fraction > (threshold[y%4][x%4]+0.5)/16))
        dot(x,y,sky[idx])

# Distant stars, each a deliberate pixel cluster.
for x,y in [(34,34),(74,82),(126,42),(159,19),(239,34),(272,121),(367,46),
            (353,151),(43,135),(114,119),(230,150),(315,26),(20,91),(375,110)]:
    dot(x,y,'#ddd3c8')
    if y < 90:
        dot(x+1,y,'#ddd3c8')
for x,y in [(92,29),(262,69),(347,101)]:
    line(x-2,y,x+2,y,'#f9e5c0')
    line(x,y-2,x,y+2,'#f9e5c0')
    dot(x,y,'#fff0d4')

# A thin, pixel-stepped crescent, carved from the untouched sky.
old = bytes(pixels)
circle(325,65,15,'#f8deb5')
circle(324,65,12,'#fff0c9')
for y in range(47,83):
    for x in range(309,347):
        if (x-332)**2+(y-60)**2 <= 15**2:
            k = (y*W+x)*3
            pixels[k:k+3] = old[k:k+3]

# Long stratified clouds with angular, hand-built silhouettes.
def cloud(x, y, w, h, main, light):
    pts = [(x,y+h),(x,y+h//2),(x+w*.12,y+h//2),(x+w*.12,y+h*.25),
           (x+w*.3,y+h*.25),(x+w*.3,y),(x+w*.50,y),(x+w*.50,y+h*.18),
           (x+w*.69,y+h*.18),(x+w*.69,y+h*.4),(x+w*.88,y+h*.4),
           (x+w*.88,y+h*.65),(x+w,y+h*.65),(x+w,y+h)]
    poly(pts, main)
    rect(x+w*.14,y+h-2,x+w*.85,y+h,light)
    rect(x+w*.33,y+h-4,x+w*.70,y+h-3,light)
cloud(-18,102,157,17,'#574166','#8b5b7d')
cloud(241,153,183,15,'#805478','#b7768b')
cloud(34,178,121,13,'#a96c87','#d28b93')
cloud(-26,212,120,13,'#bd778a','#e39b99')
cloud(263,235,167,11,'#d68b91','#f1b1a3')
rect(22,126,71,127,'#745177')
rect(263,180,346,181,'#aa6c85')
rect(114,196,148,197,'#d28b93')
rect(5,242,46,243,'#efa99e')

# Low sun, broken into warm horizontal pixel bands.
circle(86,281,34,'#ffc791')
circle(86,281,30,'#ffdda5')
for yy in range(273,311):
    span = int(math.sqrt(max(0,30**2-(yy-281)**2)))
    if abs(yy-281) <= 30:
        rect(86-span,yy,86+span,yy,'#ffe4af' if yy < 288 else '#ffd49c')
rect(44,293,130,295,'#e9a396')
rect(59,302,121,304,'#e9a396')
rect(72,310,104,311,'#edaca0')

# Far Paris roofs, softened in the warm haze.
for x in range(-4,405,9):
    top = random.randint(315,331)
    bw = random.randint(7,13)
    rect(x,top,x+bw,350,'#ad8092')
    poly([(x-1,top),(x+3,top-4),(x+bw-3,top-4),(x+bw+2,top)],'#ad8092')
    if random.random()<.5:
        rect(x+3,top-7,x+4,top-3,'#ad8092')
# Tiny distant basilica domes on the right hillside.
poly([(281,326),(301,318),(325,319),(348,330)],'#ad8092')
for x,r in [(306,5),(321,8),(338,4)]:
    circle(x,314,r,'#ad8092')
    rect(x-r,314,x+r,326,'#ad8092')
    rect(x,303 if r==8 else 307,x,309,'#ad8092')
rect(0,347,399,358,'#9a778e')

# Haussmann blocks: slate mansards, chimneys and tiny illuminated windows.
for start,end in [(-8,160),(244,410)]:
    x=start
    while x < end:
        bw=random.randint(17,28)
        y=random.randint(325,340)
        face=random.choice(['#715d7c','#79627f','#806881'])
        rect(x,y,x+bw-2,366,face)
        poly([(x-2,y),(x+3,y-7),(x+bw-7,y-7),(x+bw,y)],'#514866')
        line(x,y,x+bw-2,y,'#a07e93')
        rect(x+4,y-10,x+6,y-6,'#514866')
        for wy in range(y+5,363,7):
            for wx in range(x+4,x+bw-3,6):
                rect(wx,wy,wx+1,wy+2,random.choice(['#b6929b','#e6b29e','#4c4863','#a38193']))
        rect(x,362,x+bw-2,364,'#514866')
        x+=bw

# Seine and its long horizontal reflections.
rect(0,366,399,389,'#716b8d')
rect(0,366,399,368,'#b990a0')
for _ in range(170):
    x=random.randrange(W); y=random.randrange(370,388)
    rect(x,y,x+random.randint(2,13),y,random.choice(['#9a849f','#c09ba5','#655e81','#cba9ac']))
# A distant arched stone bridge to the right.
rect(269,373,399,378,'#655d7a')
rect(267,372,399,373,'#ce9c9f')
for x in range(278,400,25):
    poly([(x,379),(x+3,375),(x+10,375),(x+14,379),(x+14,385),(x,385)],'#716b8d')
    rect(x+15,377,x+21,390,'#655d7a')
for x in range(273,400,11):
    rect(x,369,x,372,'#655d7a')
rect(0,390,399,394,'#454c65')
rect(0,389,399,389,'#b493a0')

# Champ de Mars lawns and central promenade.
rect(0,395,399,499,'#303f51')
poly([(165,414),(235,414),(288,499),(111,499)],'#aa8d8b')
poly([(176,414),(225,414),(268,499),(133,499)],'#c6a19a')
line(163,417,108,499,'#e3b8a0',2)
line(237,417,291,499,'#e3b8a0',2)
poly([(0,411),(147,417),(108,467),(0,453)],'#3b5157')
poly([(253,417),(400,409),(400,453),(292,467)],'#3b5157')
poly([(0,461),(104,471),(87,499),(0,499)],'#293d47')
poly([(298,471),(400,461),(400,499),(315,499)],'#293d47')
for y in [453,469,492]:
    half=(y-414)*.78+25
    line(200-half,y,200+half,y,'#b49390')
# Terrace behind the tower's feet.
rect(87,422,313,433,'#8d7b83')
rect(84,421,316,423,'#d6aa96')
rect(83,433,317,435,'#524e61')
line(86,435,315,435,'#ba9691')

# Tower metal palette: dark plum iron, copper, gold, and warm glints.
D='#483446'; S='#78505a'; M='#b57765'; G='#d99a70'; L='#f8c48a'; B='#e8ac77'

def beam(a,b,width=3,lit=True):
    line(*a,*b,D,width+2)
    line(*a,*b,M if lit else S,width)
    if lit and width >= 2:
        line(a[0]-1,a[1],b[0]-1,b[1],L,1)

# Sparse open lattice from summit down to the second observation deck.
levels=[(111,196,204),(137,194,206),(163,191,209),(190,187,213),
        (216,181,219),(243,174,226),(272,164,236)]
for (y0,l0,r0),(y1,l1,r1) in zip(levels,levels[1:]):
    beam((l0,y0),(r1,y1),2,False)
    beam((r0,y0),(l1,y1),2,True)
    beam((l1,y1),(r1,y1),2,True)
    ym=(y0+y1)//2
    lm=(l0+l1)//2; rm=(r0+r1)//2
    line(lm,ym,rm,ym,S)
    # Inner vertical rails give the tapered shaft depth.
    line(l0+3,y0,l1+4,y1,G,1)
    line(r0-3,y0,r1-4,y1,S,1)
for (y0,l0,r0),(y1,l1,r1) in zip(levels,levels[1:]):
    beam((l0,y0),(l1,y1),3,True)
    beam((r0,y0),(r1,y1),3,False)
    line(r0-1,y0,r1-1,y1,G)

# Upper lantern, roof and antenna.
rect(196,84,204,108,D)
rect(197,87,202,105,G)
rect(198,89,200,104,L)
rect(191,106,209,110,D)
rect(190,107,210,108,L)
rect(193,111,207,114,S)
rect(194,111,206,111,B)
poly([(195,84),(198,79),(202,79),(205,84)],D)
line(200,62,200,80,L,2)
line(201,62,201,79,S)
rect(199,60,201,62,L)
rect(196,83,204,84,L)
for x in range(194,208,3):
    dot(x,107,'#ffe1a3')

# Open middle section. Four sloping piers, rather than a filled silhouette.
for a,b in [((165,279),(137,339)),((179,279),(164,339)),
            ((235,279),(263,339)),((221,279),(236,339))]:
    beam(a,b,5,a[0]<200)
# Structural cross-bracing inside each pylon.
for side in [-1,1]:
    ys=[281,300,320,338]
    outer=[35,43,53,63]; inner=[21,26,31,36]
    for i in range(3):
        a=(200+side*outer[i],ys[i]); b=(200+side*inner[i+1],ys[i+1])
        c=(200+side*inner[i],ys[i]); d=(200+side*outer[i+1],ys[i+1])
        beam(a,b,2,side<0); beam(c,d,2,False)
        beam((200+side*outer[i+1],ys[i+1]),(200+side*inner[i+1],ys[i+1]),2,True)
# Horizontal girders and the internal diagonal web.
beam((157,298),(243,298),2,False)
beam((146,323),(254,323),3,True)
beam((181,283),(230,334),2,False)
beam((219,283),(170,334),2,True)
line(200,283,200,335,S,2)

# Lower sweeping legs, with a true open arch beneath the first floor.
left=[(136,342),(164,342),(174,352),(159,371),(150,391),(136,420),
      (103,420),(117,390),(126,364)]
right=[(400-x,y) for x,y in left]
poly(left,D); poly(right,D)
poly([(139,345),(162,345),(169,352),(155,374),(147,394),(133,417),
      (110,417),(122,389),(131,364)],M)
poly([(261,345),(238,345),(231,352),(245,374),(253,394),(267,417),
      (290,417),(278,389),(269,364)],S)
# Arch spandrel, narrow enough to keep the sky visible.
poly([(163,343),(237,343),(242,356),(231,363),(218,356),(205,353),
      (195,353),(182,356),(169,363),(158,356)],D)
poly([(167,346),(233,346),(236,353),(226,354),(213,349),(188,349),(174,354),(164,353)],M)
# Crossed lattice in the spreading feet: dark openings bounded by lit struts.
for side in [-1,1]:
    rows=[(352,59,37),(374,70,47),(397,80,58),(419,94,65)]
    for (y0,o0,i0),(y1,o1,i1) in zip(rows,rows[1:]):
        # Little sky/land-coloured triangular openings enhance the wrought iron.
        col='#867182' if y0<374 else '#4d5366'
        poly([(200+side*(o0-4),y0+5),(200+side*(i0+4),y0+5),
              (200+side*((o1+i1)//2),y1-5)],col)
        poly([(200+side*(o1-4),y1-3),(200+side*(i1+4),y1-3),
              (200+side*((o0+i0)//2),y0+7)],col)
        beam((200+side*o0,y0),(200+side*i1,y1),3,side<0)
        beam((200+side*i0,y0),(200+side*o1,y1),3,side<0)
        beam((200+side*o1,y1),(200+side*i1,y1),3,True)
    # Outer and inner continuous curves.
    out=[(200+side*63,343),(200+side*72,375),(200+side*82,398),(200+side*97,421)]
    ins=[(200+side*29,358),(200+side*46,375),(200+side*56,397),(200+side*65,421)]
    for p,q in zip(out,out[1:]): beam(p,q,4,side<0)
    for p,q in zip(ins,ins[1:]): beam(p,q,3,side<0)
# Graceful inner arch with discrete highlighted joints.
arch=[(143,389),(151,373),(161,362),(176,354),(190,350),(200,349),
      (210,350),(224,354),(239,362),(249,373),(257,389)]
for p,q in zip(arch,arch[1:]):
    line(*p,*q,D,4)
    line(p[0],p[1]-1,q[0],q[1]-1,B,2)

# Platforms overlap all of the support members.
def platform(x0,x1,y,height):
    poly([(x0+3,y-3),(x1-3,y-3),(x1+2,y),(x0-2,y)],D)
    rect(x0-2,y,x1+2,y+2,L)
    rect(x0,y+3,x1,y+height,D)
    rect(x0+1,y+3,x1-1,y+4,G)
    for x in range(x0+3,x1-2,4):
        rect(x,y+5,x+1,y+height-1,S)
        dot(x,y+5,B)
    line(x0+2,y+height,x1-2,y+height,M)
    for x in range(x0+2,x1,5):
        line(x,y-5,x,y-1,D)
        dot(x,y-5,B)
    line(x0,y-5,x1,y-5,G)
platform(159,241,273,9)
platform(130,270,337,11)
# Footings and the small shaded entrance under the arch.
for a,b in [(101,137),(263,299)]:
    rect(a,420,b,424,D)
    rect(a-2,424,b+2,427,'#d1aa94')
    rect(a-3,428,b+3,431,'#675769')
    rect(a,420,b,421,L)
rect(180,412,220,419,'#565366')
rect(184,407,216,411,'#716575')
for x in range(185,218,7):
    rect(x,414,x+2,418,'#dfad88')
# Pinpoint rivets and festive incandescent bulbs, spaced rather than noisy.
for y,l,r in levels[2:]:
    dot(l,y,L); dot(r,y,B)
for x in range(133,270,6):
    dot(x,339,'#ffe0a1')
for x in range(163,240,6):
    dot(x,274,'#ffe0a1')

# Framing trees, rendered in blocky clusters, keep the monument unobstructed.
def tree(cx,cy,r,base,mid,top):
    rect(cx-2,cy+5,cx+3,cy+r+31,'#252e40')
    line(cx,cy+18,cx-r//2,cy+4,'#252e40',2)
    line(cx+1,cy+12,cx+r//2,cy-3,'#252e40',2)
    for _ in range(15):
        xx=cx+random.randint(-r,r); yy=cy+random.randint(-r//2,r//2)
        rr=random.randint(r//3,r//2+2)
        # Rectangular cluster edges, with round canopy silhouettes underneath.
        circle(xx,yy,rr,base)
        rect(xx-rr+2,yy-rr,xx+rr-3,yy-rr+3,base)
    for _ in range(17):
        xx=cx+random.randint(-r+3,r-3); yy=cy+random.randint(-r//2,r//2)
        rect(xx,yy,xx+random.randint(3,9),yy+random.randint(2,5),mid)
    for _ in range(9):
        xx=cx+random.randint(-r+3,r-3); yy=cy+random.randint(-r//2,0)
        rect(xx,yy,xx+random.randint(2,6),yy+1,top)
tree(19,375,28,'#30394f','#41485c','#62596d')
tree(65,388,20,'#30394f','#41495c','#6c5c6d')
tree(373,374,29,'#30394f','#41485c','#65596c')
tree(335,392,19,'#30394f','#41495c','#6c5c6d')
# Lower hedges and flowerbeds.
for side in [0,1]:
    for j in range(45):
        x=random.randint(0,103) if side==0 else random.randint(297,399)
        y=random.randint(459,485)
        rect(x,y,x+random.randint(2,6),y+2,random.choice(['#405459','#4b6060','#263b46']))
        if j%5==0:
            dot(x+1,y-1,'#cf8b88'); dot(x+2,y-1,'#e5a395')
line(0,454,109,467,'#817777',2)
line(293,467,399,454,'#817777',2)

# Parisian park lamps with stepped pools of warm light.
def lamp(x,base,height):
    y=base-height
    line(x,base,x,y+8,'#242c40',2)
    rect(x-3,base-1,x+3,base,'#242c40')
    rect(x-4,y+1,x+4,y+8,'#b27e6a')
    rect(x-2,y+2,x+2,y+7,'#ffe0a0')
    rect(x-1,y+2,x+1,y+6,'#fff0bb')
    poly([(x-5,y+1),(x-2,y-2),(x+2,y-2),(x+5,y+1)],'#242c40')
    rect(x-4,y+9,x+4,y+10,'#242c40')
    dot(x,y-3,'#d3a27e')
    rect(x-5,base+2,x+5,base+2,'#b29183')
lamp(82,431,31); lamp(318,431,31)
lamp(52,486,46); lamp(348,486,46)

# Benches on the terrace, a few walkers for a sense of scale.
def bench(x,y):
    rect(x,y,x+15,y+3,'#493747')
    line(x,y,x+15,y,'#b48a7c')
    rect(x-1,y+5,x+16,y+6,'#493747')
    rect(x+2,y+6,x+3,y+9,'#302f43')
    rect(x+12,y+6,x+13,y+9,'#302f43')
bench(69,444); bench(315,444)

def person(x,y,scale,coat):
    rect(x,y,x+scale,y+scale,'#e0ae95')
    rect(x,y-1,x+scale,y,'#332e42')
    rect(x-1,y+scale+1,x+scale+1,y+scale*4,coat)
    line(x,y+scale*4,x-1,y+scale*6,'#303043',scale)
    line(x+scale,y+scale*4,x+scale+1,y+scale*6,'#303043',scale)
    line(x-1,y+scale+2,x-2,y+scale*4,coat)
    line(x+scale+1,y+scale+2,x+scale+2,y+scale*4,coat)
person(191,448,2,'#58415b')
person(203,450,2,'#b96869')
person(230,477,2,'#344558')
person(162,428,1,'#3e374e')
person(242,432,1,'#574054')
person(181,478,2,'#dfb185')
# Fine foreground cobblestone marks, kept sparse and aligned to perspective.
for x,y in [(155,467),(211,469),(190,462),(244,491),(171,495),(142,489),(213,495),(188,488),(229,459)]:
    rect(x,y,x+3,y,'#ae8e8a')

# Export an integer-scaled, high quality JPEG with no chroma subsampling.
out = Path('output')
out.mkdir(exist_ok=True)
tmp = Path('.eiffel_render.ppm')
tmp.write_bytes(f'P6\n{W} {H}\n255\n'.encode() + pixels)
try:
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp),
                    '-vf','scale=1200:1500:flags=neighbor','-frames:v','1',
                    '-q:v','2','-pix_fmt','yuvj444p',str(out/'eiffel_tower_16bit.jpg')],check=True)
finally:
    tmp.unlink(missing_ok=True)
print(out/'eiffel_tower_16bit.jpg')
