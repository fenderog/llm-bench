#!/usr/bin/env python3
"""A native-resolution, tile/palette-constrained 16-bit Paris background.
No dependencies. Produces output/eiffel_at_the_golden_hour.png.
All drawing is performed directly on the 256 x 224 integer pixel grid.
"""
import math
import os
import random
import struct
import zlib
from collections import Counter

W, H = 256, 224
PAL = []
NAMES = {}
def color(name, value):
    rgb = tuple(bytes.fromhex(value.lstrip('#')))
    if rgb not in PAL:
        PAL.append(rgb)
    NAMES[name] = PAL.index(rgb)
    return NAMES[name]

# Shared sprite/background colors; no generated RGB blends.
for name, value in [
    ('ink','222b40'), ('night','30354e'), ('sky0','3c3d60'),
    ('sky1','494567'), ('sky2','5c4f74'), ('sky3','735d80'),
    ('sky4','916c8a'), ('sky5','af7b93'), ('sky6','c98b98'),
    ('sky7','dfa19e'), ('sky8','efb89f'), ('sky9','f5cba5'),
    ('cloud0','555075'), ('cloud1','6b5b80'), ('cloud2','826888'),
    ('cloud3','a47c96'), ('cloud4','c798a4'), ('cloud5','e4acaa'),
    ('cream','ffe4ae'), ('sun','ffdaa0'), ('sunlow','f5bd88'),
    ('glow','f1ceae'), ('haze','ba929e'), ('far','967f97'),
    ('farshade','80738c'), ('roof','5e607c'), ('rooflit','858098'),
    ('wall','ae949e'), ('walllit','d1aba6'), ('wallshade','8e8096'),
    ('window','5e6078'), ('brick','9b747f'),
    ('iron0','343344'), ('iron1','574453'), ('iron2','7c5260'),
    ('iron3','a46967'), ('iron4','c18b74'), ('iron5','e0aa7b'),
    ('iron6','f3c68c'), ('iron7','ffe0a5'),
    ('tree0','263e4c'), ('tree1','34525d'), ('tree2','466872'),
    ('tree3','64808a'), ('tree4','849597'),
    ('stone0','6d6379'), ('stone1','96818e'), ('stone2','b69a9a'),
    ('stone3','d4b3a5'), ('stone4','ebc8ab'),
    ('water0','35465f'), ('water1','435573'), ('water2','586681'),
    ('water3','73798e'), ('water4','9892a0'),
    ('ripple0','bb949d'), ('ripple1','dfa8a1'), ('ripple2','f3c297'),
    ('red','c37077'), ('redlit','ec9a8d'), ('leaf','4e6670'),
    ('leaflit','718084'), ('petal','d18b99'), ('petallit','f1b1a7'),
]:
    color(name, value)

pix = [[NAMES['sky0']] * W for _ in range(H)]
rng = random.Random(1648)

def ci(c):
    return NAMES[c] if isinstance(c, str) else c

def dot(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        pix[y][x] = ci(c)

def rect(x0, y0, x1, y1, c):
    c = ci(c)
    for y in range(max(0, int(y0)), min(H, int(y1)+1)):
        for x in range(max(0, int(x0)), min(W, int(x1)+1)):
            pix[y][x] = c

def line(x0, y0, x1, y1, c, width=1):
    x0,y0,x1,y1 = map(lambda n: int(round(n)), (x0,y0,x1,y1))
    dx, sx = abs(x1-x0), 1 if x0<x1 else -1
    dy, sy = -abs(y1-y0), 1 if y0<y1 else -1
    err = dx+dy
    while True:
        if width == 1:
            dot(x0,y0,c)
        else:
            rect(x0-(width-1)//2,y0-(width-1)//2,x0+width//2,y0+width//2,c)
        if x0 == x1 and y0 == y1:
            break
        e = 2*err
        if e >= dy:
            err += dy; x0 += sx
        if e <= dx:
            err += dx; y0 += sy

def poly(points, c):
    # Integer spans, no antialiasing, deterministic even at shared edges.
    ymin = max(0, math.floor(min(y for x,y in points)))
    ymax = min(H-1, math.ceil(max(y for x,y in points)))
    for y in range(ymin, ymax+1):
        xs = []
        for i,(x0,y0) in enumerate(points):
            x1,y1 = points[(i+1)%len(points)]
            if (y0 <= y+0.5 < y1) or (y1 <= y+0.5 < y0):
                xs.append(x0+(y+0.5-y0)*(x1-x0)/(y1-y0))
        xs.sort()
        for a,b in zip(xs[::2], xs[1::2]):
            rect(math.ceil(a-0.5),y,math.floor(b-0.5),y,c)

def path(points, c, width=1):
    for a,b in zip(points,points[1:]):
        line(*a,*b,c,width)

def ellipse(cx,cy,rx,ry,c):
    for y in range(max(0,cy-ry),min(H,cy+ry+1)):
        t = 1 - ((y-cy)/ry)**2
        dx = int(rx*math.sqrt(max(0,t)))
        rect(cx-dx,y,cx+dx,y,c)

# ---------------------------------------------------------------------------
# Dusk. Broad, clean color bands with short, ordered-dither transition zones.
sky_stops = [(0,'sky0'),(22,'sky1'),(42,'sky2'),(61,'sky3'),
             (79,'sky4'),(96,'sky5'),(112,'sky6'),(129,'sky7'),
             (143,'sky8'),(157,'sky9')]
bayer = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
for y in range(179):
    idx = max(i for i,(sy,c) in enumerate(sky_stops) if sy <= y)
    base = sky_stops[idx][1]
    rect(0,y,W-1,y,base)
    if idx > 0 and y-sky_stops[idx][0] < 5:
        k = (y-sky_stops[idx][0]+1)*3
        for x in range(W):
            if bayer[y%4][x%4] >= k:
                dot(x,y,sky_stops[idx-1][1])

# The sun is an intentionally stepped pixel disc, not a resampled vector.
ellipse(70,96,25,25,'sunlow')
ellipse(70,94,23,23,'sun')
rect(49,107,91,108,'sunlow')
rect(53,112,87,113,'sky8')
rect(58,117,82,118,'sky7')

# Hand-shaped clouds with terraces and warm lower edges.
poly([(0,32),(12,32),(12,29),(24,29),(24,27),(38,27),(38,28),
      (48,28),(48,31),(59,31),(59,33),(70,33),(70,36),(83,36),
      (83,38),(62,38),(62,40),(32,40),(32,39),(12,39),(12,37),(0,37)],'cloud0')
rect(9,36,62,37,'cloud1'); rect(27,38,51,38,'cloud2')
rect(49,32,65,33,'cloud1'); rect(79,40,94,40,'cloud1')
rect(3,43,33,43,'cloud1'); rect(15,44,27,44,'cloud2')

poly([(171,38),(184,38),(184,35),(194,35),(194,32),(210,32),
      (210,34),(220,34),(220,39),(234,39),(234,41),(244,41),
      (244,44),(255,44),(255,63),(241,63),(241,66),(214,66),
      (214,64),(195,64),(195,61),(179,61),(179,58),(168,58),
      (168,54),(163,54),(163,49),(171,49)],'cloud0')
poly([(178,44),(190,44),(190,40),(208,40),(208,43),(220,43),
      (220,48),(238,48),(238,51),(255,51),(255,62),(235,62),
      (235,64),(216,64),(216,62),(194,62),(194,59),(177,59),
      (177,55),(168,55),(168,51),(178,51)],'cloud1')
poly([(183,53),(203,53),(203,51),(217,51),(217,54),(239,54),
      (239,57),(255,57),(255,62),(235,62),(235,64),(216,64),
      (216,62),(194,62),(194,59),(177,59),(177,57),(183,57)],'cloud2')
rect(194,60,232,61,'cloud3'); rect(210,62,238,63,'cloud4')
rect(239,60,255,60,'cloud4'); rect(221,64,232,64,'cloud5')
rect(162,64,190,65,'cloud2'); rect(174,66,200,67,'cloud3')
rect(187,68,211,68,'cloud4'); rect(238,70,255,71,'cloud3')

# Slim cirrus, deliberately asymmetrical to leave air around the tower.
poly([(0,84),(17,84),(17,82),(30,82),(30,83),(38,83),(38,86),
      (50,86),(50,88),(40,88),(40,90),(12,90),(12,88),(0,88)],'cloud3')
rect(4,88,37,89,'cloud4'); rect(20,90,45,90,'cloud5')
rect(0,97,31,98,'cloud4'); rect(13,99,43,99,'cloud5')
rect(42,104,64,105,'sky7'); rect(59,106,100,107,'sky7')
rect(93,109,119,110,'cloud4'); rect(105,111,132,111,'cloud5')
rect(178,103,216,104,'cloud3'); rect(191,105,225,106,'cloud4')
rect(204,108,246,108,'cloud5')
rect(179,122,194,123,'cloud5'); rect(189,125,219,125,'sky8')
rect(4,128,31,128,'sky8'); rect(35,135,76,136,'sky9')

# A few distant birds: small, low-contrast, unmistakably pixel-edged.
def bird(x,y,c):
    path([(x-3,y-1),(x-2,y-1),(x,y+1),(x+2,y-1),(x+3,y-1)],c)
bird(113,82,'cloud0'); bird(122,87,'cloud1'); bird(197,91,'cloud2')

# ---------------------------------------------------------------------------
# Paris: two parallax skyline layers, slate mansard roofs, chimneys, a dome.
rect(0,162,255,178,'haze')
for x in range(-3,260,9):
    top = rng.choice([153,155,157,158,160])
    ww = rng.randint(6,12)
    rect(x,top,x+ww,169,'far')
    if rng.random() < .6:
        rect(x+2,top-3,x+3,top,'far')
    rect(x+1,top+1,x+ww-1,top+1,'haze')
# Far church spire, almost lost in the warm atmospheric haze.
poly([(217,151),(220,136),(223,151)],'far')
rect(218,149,222,161,'far'); dot(220,134,'far')

# The distant gilded dome of Les Invalides.
rect(46,150,65,169,'wallshade')
rect(48,143,63,151,'walllit')
ellipse(55,144,9,10,'farshade')
ellipse(54,144,7,9,'walllit')
rect(46,145,64,147,'rooflit')
rect(45,149,66,151,'walllit')
rect(53,133,57,136,'roof'); rect(54,130,56,133,'iron5')
line(55,127,55,131,'roof'); dot(54,129,'roof'); dot(56,129,'roof')
for x in [49,54,59]:
    rect(x,153,x+1,158,'roof')
rect(44,159,68,161,'walllit')

# Rooftops have actual pixel silhouettes rather than random skyline bars.
def building(x,y,w,h,lit=False):
    face = 'walllit' if lit else 'wall'
    shade = 'wall' if lit else 'wallshade'
    rect(x,y,x+w-1,y+h,face)
    rect(x+w-4,y+1,x+w-1,y+h,shade)
    poly([(x-1,y),(x+3,y-6),(x+w-5,y-6),(x+w,y)],'roof')
    line(x+3,y-6,x+w-5,y-6,'rooflit')
    line(x,y,x+w-1,y,'stone3')
    rect(x+4,y-10,x+5,y-6,'roof')
    dot(x+4,y-10,'walllit')
    if w > 15:
        rect(x+w-7,y-8,x+w-5,y-6,'brick')
    for xx in range(x+3,x+w-4,5):
        for yy in range(y+4,y+h-1,6):
            rect(xx,yy,xx+1,yy+2,'window')
            if rng.random()<.35:
                dot(xx,yy+1,'sunlow')
        if w>12:
            rect(xx,y-4,xx+1,y-2,'wallshade')
            dot(xx,y-5,'rooflit')
    line(x,y+h-1,x+w-1,y+h-1,shade)

for spec in [(-5,157,20,19,False),(13,160,18,16,True),(30,161,17,15,False),
             (66,158,23,18,True),(88,162,17,14,False),
             (201,158,20,18,False),(221,154,22,22,True),(241,157,20,19,False)]:
    building(*spec)

# A textured, clustered tree belt at the far bank. No white-noise spray.
def tree(cx,base,r,seed):
    rr = random.Random(seed)
    rect(cx-1,base-r,cx+1,base+2,'tree0')
    clusters = [(cx-r//2,base-r,r*3//5), (cx+r//2,base-r+1,r*3//5),
                (cx,base-r-r//2,r*2//3), (cx,base-r//2,r*4//5)]
    for xx,yy,rad in clusters:
        ellipse(xx,yy,rad,rad*3//4,'tree0')
    for xx,yy,rad in clusters:
        ellipse(xx-1,yy-2,max(2,rad-1),max(2,rad//2),'tree1')
        rect(xx-rad//2,yy-rad//2-1,xx+1,yy-rad//2,'tree2')
        if rr.random()<.7:
            rect(xx-rad//2,yy-rad//2-1,xx-rad//2+2,yy-rad//2-1,'tree3')
    for _ in range(r//2):
        xx = cx+rr.randint(-r+2,r-2); yy=base-rr.randint(3,r)
        rect(xx,yy,xx+2,yy,'tree1')

for i,(cx,base,r) in enumerate([(3,180,13),(18,179,10),(37,180,9),(72,179,8),
                               (88,180,10),(102,180,8),(213,180,10),
                               (231,180,12),(250,181,15)]):
    tree(cx,base,r,700+i)

# Warm park/promenade plane behind the tower.
rect(0,180,255,183,'stone2')
rect(0,180,255,180,'stone3')
rect(101,178,209,180,'stone3')
line(108,181,198,181,'stone4')
for a,b,y in [(38,54,181),(60,77,183),(211,233,182),(127,146,183)]:
    line(a,y,b,y,'stone1')

# ---------------------------------------------------------------------------
# The Eiffel Tower. Curved outer legs, three galleries, riveted open ironwork.
# Its bays are drawn over untouched background, preserving the actual sky holes.
CX = 155
# Receding pair of legs, visibly less golden than the front pair.
poly([(143,149),(149,150),(137,181),(126,183),(122,181)],'iron1')
poly([(164,149),(170,150),(186,181),(182,183),(175,181)],'iron1')
path([(146,151),(141,164),(130,181)],'iron3',2)
path([(168,152),(172,166),(182,181)],'iron2',2)
line(130,181,181,181,'iron2')

# Small taper segments reproduce the tower's concave silhouette.
ys = [48,58,69,81,94,107,122]
ls = [152,151,150,148,146,143,140]
ms = [156,156,157,158,159,161,163]
rs = [158,159,160,162,164,167,170]
for i in range(len(ys)-1):
    y0,y1 = ys[i],ys[i+1]
    l0,l1,m0,m1,r0,r1 = ls[i],ls[i+1],ms[i],ms[i+1],rs[i],rs[i+1]
    # The narrow right-hand face remains darker; both faces have open bays.
    line(m0,y0,r1,y1,'iron1',2)
    line(r0,y0,m1,y1,'iron2')
    line(m0,y0,r0,y0,'iron2')
    # Large front X trusses, a gold side and a shadow side.
    line(l0+1,y0,m1,y1,'iron1',2)
    line(m0,y0,l1+1,y1,'iron1',2)
    line(l0+1,y0,m1-1,y1,'iron4')
    line(m0-1,y0,l1+1,y1,'iron5')
    line(l1,y1,r1,y1,'iron0',2)
    line(l1,y1-1,m1,y1-1,'iron5')
    if i >= 3:
        line(l1+2,y1+1,m1-1,y1+1,'iron2')
# Vertical corner members, each with its own shaded edge.
path(list(zip(rs,ys)),'iron0',2)
path(list(zip(ms,ys)),'iron2',2)
path([(x-1,y) for x,y in zip(ms,ys)],'iron5')
path(list(zip(ls,ys)),'iron0',2)
path([(x+1,y) for x,y in zip(ls,ys)],'iron6')
for y,l,m in zip(ys[1:],ls[1:],ms[1:]):
    dot(l+1,y-1,'iron7'); dot(m-1,y-1,'iron6')

# Summit observation cabin, roof, beacon and antenna.
rect(151,34,158,40,'iron0')
rect(152,35,157,39,'iron4')
rect(153,35,154,37,'iron7'); rect(156,35,157,37,'iron1')
poly([(148,41),(151,39),(159,39),(162,41),(162,44),(148,44)],'iron0')
line(148,41,161,41,'iron6')
rect(150,42,160,43,'iron3')
for x in [151,154,157,160]:
    dot(x,42,'iron7')
rect(149,45,161,46,'iron0'); rect(150,45,160,45,'iron5')
line(152,47,158,47,'iron2')
poly([(152,34),(153,28),(155,25),(157,28),(158,34)],'iron1')
line(154,28,154,33,'iron6')
line(155,18,155,28,'iron0')
line(154,20,154,26,'iron5'); dot(155,17,'iron6')
rect(152,30,158,31,'iron0'); line(153,30,157,30,'iron4')

# Second-floor to first-floor body. Two broad front lattice bays and side plane.
left = [(140,126),(137,136),(132,146),(126,154)]
right = [(170,126),(174,136),(179,146),(184,154)]
mid = [(163,126),(165,136),(169,146),(172,154)]
for i in range(3):
    (l0,y0),(l1,y1)=left[i:i+2]
    (m0,_),(m1,_)=mid[i:i+2]
    (r0,_),(r1,_)=right[i:i+2]
    # Split the front into two slender panels.
    c0,c1=(l0+m0)//2,(l1+m1)//2
    for a0,a1,b0,b1 in [(l0,l1,c0,c1),(c0,c1,m0,m1)]:
        line(a0+1,y0,b1,y1,'iron0',2)
        line(b0,y0,a1+1,y1,'iron1',2)
        line(a0+1,y0,b1-1,y1,'iron4')
        line(b0-1,y0,a1+1,y1,'iron6')
    line(c0,y0,c1,y1,'iron3')
    line(m0,y0,r1,y1,'iron1',2)
    line(r0,y0,m1,y1,'iron2',2)
    line(r0-1,y0,m1,y1,'iron4')
    line(l1,y1,r1,y1,'iron1',2)
    line(l1,y1-1,m1,y1-1,'iron5')
path(left,'iron0',3); path([(x+1,y) for x,y in left],'iron6')
path(right,'iron0',3); path([(x-1,y) for x,y in right],'iron3')
path(mid,'iron1',2); path([(x-1,y) for x,y in mid],'iron5')

# The large characteristic arch and the flaring front legs.
legL = [(126,156),(139,157),(133,166),(126,176),(120,185),(102,185),
        (112,174),(120,164)]
legR = [(184,156),(190,164),(198,174),(208,185),(190,185),
        (184,176),(177,166),(171,157)]
poly(legL,'iron0'); poly(legR,'iron0')
poly([(128,157),(135,158),(129,168),(117,183),(106,183),(116,173)],'iron3')
poly([(176,158),(182,157),(190,173),(202,183),(192,183),(181,168)],'iron2')
# Lattice apertures through both front legs, copied from saved scenic colors
# are not needed here: dark inset triangles read as the occluded rear framework.
for pts in [[(124,163),(130,161),(125,169)],[(119,170),(124,170),(117,178)],
            [(110,180),(119,176),(116,182)]]:
    poly(pts,'iron0')
    poly([(310-x,y) for x,y in pts],'iron0')
path([(126,157),(120,166),(112,176),(104,184)],'iron6',2)
path([(137,158),(130,169),(120,183)],'iron5',2)
path([(183,158),(189,169),(203,184)],'iron4',2)
path([(173,158),(180,170),(190,183)],'iron5')
for pts in [[(124,161),(131,166),(117,171),(123,176),(107,181),(117,183)],
            [(182,161),(177,166),(192,172),(185,176),(202,181),(192,183)]]:
    path(pts,'iron0',2)
    path([(x,y-1) for x,y in pts],'iron5' if pts[0][0]<155 else 'iron3')
# The decorative shallow arch is separate from the angled load-bearing legs.
arch = [(119,183),(123,174),(128,167),(135,161),(145,157),(155,156),
        (165,157),(175,161),(182,167),(187,174),(191,183)]
path(arch,'iron0',3)
path([(x,y-1) for x,y in arch],'iron4')
path([(x,y+1) for x,y in arch[1:-1]],'iron2')
# Arch spandrel braces.
for x,yy in [(134,162),(141,159),(148,157),(162,157),(169,159),(176,162)]:
    line(x,158,x,yy,'iron1')
    dot(x,yy,'iron6')

# Galleries use dark undersides, continuous highlights, and tiny balustrades.
def gallery(x0,x1,y,lower=False):
    rect(x0+2,y-3,x1-2,y-1,'iron1')
    line(x0+2,y-3,x1-2,y-3,'iron5')
    for x in range(x0+3,x1-2,3):
        line(x,y-3,x,y-1,'iron6')
    rect(x0,y,x1,y+3,'iron0')
    line(x0,y,x1,y,'iron7')
    line(x0+1,y+1,x1-1,y+1,'iron4')
    line(x0+2,y+3,x1-2,y+3,'iron2')
    for x in range(x0+4,x1-2,4):
        dot(x,y+2,'iron5')
    if lower:
        line(x0+4,y+4,x1-4,y+4,'iron0')
        for x in range(x0+6,x1-4,6):
            dot(x,y+4,'iron4')

gallery(135,175,123)
gallery(121,189,154,True)
# Foundation stones and tiny illuminated footlights.
for x0,x1 in [(101,121),(189,209)]:
    rect(x0,185,x1,187,'stone0')
    rect(x0,185,x1-1,185,'stone4')
    rect(x0+1,186,x1-2,186,'stone2')
    dot(x0+3,184,'cream'); dot(x1-3,184,'sun')
# Lamp-size points and visitors on the distant promenade emphasize scale.
for x in [63,83,222,243]:
    line(x,177,x,182,'iron0'); dot(x,176,'cream')
for x,y in [(143,181),(149,182),(169,182)]:
    dot(x,y-3,'iron1'); rect(x,y-2,x+1,y,'roof')
    dot(x,y+1,'ink'); dot(x+2,y+1,'ink')

# ---------------------------------------------------------------------------
# Limestone embankment and the Seine, with short clustered pixel reflections.
rect(0,188,255,192,'stone0')
rect(0,188,255,188,'stone4')
rect(0,189,255,189,'stone2')
rect(0,192,255,193,'ink')
for x in range(-2,256,13):
    line(x,190,x,191,'stone1')
    line(x+2,190,x+8,190,'stone3')
for y in range(194,219):
    rect(0,y,255,y,'water2' if y<199 else ('water1' if y<212 else 'water0'))
# Horizontal ripples, grouped rather than evenly scattered.
for _ in range(140):
    x=rng.randrange(256); y=rng.randrange(195,219)
    ww=rng.choice([2,3,4,5,8,11])
    c=rng.choice(['water0','water2','water3'])
    if y>212 and c=='water3': c='water2'
    line(x,y,x+ww,y,c)
# Sun's broken peach reflection.
for y in [195,197,200,203,205,209,212,215,218]:
    spread = 11+(y-194)
    for j in range(rng.randint(2,4)):
        x=70+rng.randint(-spread,spread)
        ww=rng.randint(2,10)
        line(x,y,x+ww,y,rng.choice(['ripple0','ripple1','ripple2']))
# Tower reflection, subtly displaced by the current.
for y in range(195,217,3):
    for x0,x1 in [(113,130),(178,197)]:
        shift = rng.randint(-3,3)
        line(x0+shift,y,x1+shift,y,'water0')
        line(x0+shift+3,y,x0+shift+8,y,'iron3')
    if y<204:
        line(139,y,168,y,'water1')
        line(145,y,151,y,'ripple0')
line(1,195,36,195,'water3'); line(222,195,254,195,'water3')

# A low, moored riverboat, a tiny scenic prop (not an interface element).
poly([(46,200),(72,200),(68,204),(50,204)],'ink')
line(47,200,71,200,'stone3')
rect(53,197,65,199,'roof'); rect(55,196,64,196,'stone3')
rect(55,198,58,199,'sunlow'); rect(61,198,64,199,'sunlow')
line(54,205,67,205,'water0'); line(59,207,65,207,'ripple0')

# Foreground promenade: cool stone, ironwork, and one ornate Paris streetlight.
rect(0,218,255,223,'night')
rect(0,218,255,218,'stone1')
rect(0,219,255,219,'stone0')
for x in range(-12,256,26):
    line(x,220,x+6,223,'ink')
    line(x+10,222,x+24,222,'roof')
# Railing silhouette: repetitive 8-pixel iron rhythm grounded by stone piers.
line(0,206,255,206,'ink',2)
line(0,205,255,205,'rooflit')
line(0,215,255,215,'ink',2)
for x in range(4,256,8):
    line(x,207,x,216,'ink')
    dot(x-1,209,'ink'); dot(x+1,209,'ink')
    dot(x,208,'stone1')
for x in [8,56,104,152,200,248]:
    rect(x-2,205,x+2,217,'night')
    rect(x-3,204,x+3,205,'ink')
    line(x-2,204,x+2,204,'stone1')
    rect(x-3,217,x+3,218,'ink')

# Tall foreground lamp. Its five-tone glass has a crisp, unblurred glow.
# Behind the actual lantern, a restrained stepped halo reuses sky colors.
poly([(22,128),(29,128),(33,132),(33,141),(30,145),(22,145),
      (18,141),(18,133)],'cloud4')
poly([(22,130),(29,130),(31,133),(31,141),(28,144),(23,144),
      (20,141),(20,133)],'iron5')
# Pole and ornamental scrollwork.
rect(25,145,27,216,'ink')
line(25,148,25,211,'iron3'); line(26,152,26,212,'iron1')
rect(23,213,29,217,'ink'); rect(21,217,31,219,'ink')
line(23,216,28,216,'iron2'); dot(24,217,'iron4')
rect(24,167,28,169,'ink'); dot(24,167,'iron4')
path([(25,159),(20,156),(19,152),(21,150),(23,151),(22,153)],'ink')
path([(27,159),(32,156),(33,152),(31,150),(29,151),(30,153)],'ink')
# Glass and metal case.
poly([(20,132),(32,132),(30,144),(22,144)],'ink')
poly([(22,134),(30,134),(28,142),(24,142)],'sunlow')
rect(23,134,28,138,'sun'); rect(24,134,26,140,'cream')
line(26,133,26,143,'iron3')
line(21,133,23,142,'iron4')
rect(22,143,30,145,'ink'); line(23,143,29,143,'iron5')
poly([(18,132),(21,130),(23,128),(29,128),(31,130),(34,132)],'ink')
line(21,130,30,130,'iron3'); line(20,132,32,132,'iron5')
rect(25,125,27,128,'ink'); dot(25,125,'iron5')
rect(24,146,28,147,'iron0'); dot(25,146,'iron5')

# A foreground plane-tree bough frames the open sky. These small, interlocking
# leaf clusters are drawn as pixel terraces, with light only on the lower edge.
poly([(0,0),(59,0),(59,3),(54,3),(54,7),(47,7),(47,12),
      (40,12),(40,16),(35,16),(35,22),(29,22),(29,28),(23,28),
      (23,35),(16,35),(16,41),(10,41),(10,47),(4,47),(4,51),(0,51)],'ink')
path([(0,33),(9,23),(22,17),(36,4),(43,0)],'iron1',3)
path([(1,31),(10,22),(23,16),(37,3)],'tree2')
path([(10,23),(8,9),(1,3)],'iron1',2)
path([(22,17),(35,18),(44,13)],'iron1',2)
# Hand-placed clusters, not a uniform noise texture.
for x,y,w in [(2,2,11),(18,1,10),(35,1,11),(48,1,9),
              (9,9,9),(26,7,10),(39,8,9),(1,18,10),
              (15,17,10),(27,17,8),(2,28,9),(13,27,8),(2,38,7)]:
    poly([(x-w,y-1),(x-w+2,y-4),(x-3,y-4),(x-3,y-6),
          (x+3,y-6),(x+3,y-3),(x+w-1,y-3),(x+w-1,y+1),
          (x+w-4,y+1),(x+w-4,y+4),(x+1,y+4),(x+1,y+6),
          (x-4,y+6),(x-4,y+3),(x-w,y+3)],'tree0')
    poly([(x-4,y),(x+1,y),(x+1,y-2),(x+w-2,y-2),
          (x+w-2,y),(x+4,y),(x+4,y+3),(x,y+3),
          (x,y+5),(x-4,y+5)],'tree1')
    line(x+1,y+3,x+3,y+3,'tree2')
    line(x-4,y+5,x-2,y+5,'tree2')
# A few loose leaf tips keep the silhouette from reading as a geometric wedge.
rect(8,47,10,48,'tree0'); dot(9,49,'tree1')
rect(24,32,26,33,'tree0'); dot(25,34,'tree2')
rect(42,15,44,16,'tree1'); dot(44,17,'tree2')
rect(54,7,56,8,'tree0'); dot(56,9,'tree1')

# Flower boxes are tiny foreground clusters, not smooth painted foliage.
for cx in [0,239,252]:
    ellipse(cx,219,11,5,'tree0')
    ellipse(cx-3,217,6,3,'tree1')
    for dx,dy in [(-7,-1),(-3,-4),(1,-2),(6,-3),(8,0),(-1,1)]:
        xx,yy=cx+dx,218+dy
        line(xx,yy+2,xx-1,yy+5,'leaf')
        rect(xx-1,yy,xx+1,yy+1,'petal')
        dot(xx-1,yy,'petallit')
    rect(cx-10,222,cx+10,223,'iron1')
    line(cx-10,222,cx+10,222,'iron3')

# ---------------------------------------------------------------------------
# Hardware constraint pass. The image is exactly 32 x 28 native 8 x 8 tiles.
# Usually no reduction is needed. If mixed sprite/background intersections
# exceed sixteen colors, merge the least-cost pair locally, never resampling.
def distance(a,b):
    ca,cb=PAL[a],PAL[b]
    return 2*(ca[0]-cb[0])**2+3*(ca[1]-cb[1])**2+(ca[2]-cb[2])**2

changed_tiles = 0
changed_pixels = 0
for ty in range(0,H,8):
    for tx in range(0,W,8):
        count=Counter(pix[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8))
        if len(count)>16:
            changed_tiles += 1
        while len(count)>16:
            # A merge minimizing weighted perceptual error, preserving the more
            # common color; edges retain their exact pixel positions.
            options=[]
            for a in count:
                for b in count:
                    if a!=b and count[a]<=count[b]:
                        options.append((count[a]*distance(a,b),a,b))
            _,a,b=min(options)
            for y in range(ty,ty+8):
                for x in range(tx,tx+8):
                    if pix[y][x]==a:
                        pix[y][x]=b; changed_pixels+=1
            count[b]+=count[a]; del count[a]

used=set(c for row in pix for c in row)
max_tile=max(len({pix[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)})
             for ty in range(0,H,8) for tx in range(0,W,8))
assert (W,H)==(256,224)
assert len(used)<=128
assert max_tile<=16
assert W%8==0 and H%8==0

# Indexed PNG: the PLTE itself is also below 128 entries.
def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)

def save_png(filename):
    raw=b''.join(b'\x00'+bytes(row) for row in pix)
    data=b'\x89PNG\r\n\x1a\n'
    data+=chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))
    data+=chunk(b'PLTE',b''.join(bytes(rgb) for rgb in PAL))
    data+=chunk(b'tEXt',b'Title\x00Paris, the golden hour')
    data+=chunk(b'tEXt',b'Description\x00Native 256x224 pixel art; 32x28 tiles of 8x8 pixels; <=16 colors per tile; <=128 colors total. No antialiasing or upscaling.')
    data+=chunk(b'IDAT',zlib.compress(raw,9))
    data+=chunk(b'IEND',b'')
    with open(filename,'wb') as f:
        f.write(data)

if __name__=='__main__':
    os.makedirs('output',exist_ok=True)
    target='output/eiffel_at_the_golden_hour.png'
    save_png(target)
    print(f'{target}: {W}x{H}, {len(used)} colors, {max_tile} colors/tile maximum')
    print(f'{changed_tiles} tiles locally palette-fitted, {changed_pixels} pixels remapped; no resizing')
