import math, random, struct, zlib, os
from collections import Counter
random.seed(19)
W,H=256,224
# Hand-tuned, shared 16-bit-style palette: dusk, patinated iron, stone and foliage.
HEX=['282d4b','343b5d','45466d','5a507c','70608b','8e7099','ad83a5','c398ad','d7a5af','eab6b4','f5c7b3','ffdab0','ffe9bb',
     'fff0cd','f5d38f','e8b469','cc894f','aa603e','82463e','593847','392e46',
     '3d536b','4b687d','608192','80a0a4','a7b9b1','d0c5b4',
     '344a59','426065','58756a','789076','a4a480','c6b58d',
     '514965','6d5a76','89718a','a48a97','bea2a3',
     'bc816b','d59b79','e9b78d','f4cfa4',
     '1f303f','293f49','3c5151','536950','77804e','a19759',
     'bb706b','e69b87','f5c298','b2bec0','6686a0','405777']
PAL=[tuple(bytes.fromhex(x)) for x in HEX]
C={h:i for i,h in enumerate(HEX)}
im=[[0]*W for _ in range(H)]
def px(x,y,c):
    x=int(x); y=int(y)
    if 0<=x<W and 0<=y<H: im[y][x]=c

def rect(x0,y0,x1,y1,c):
    for y in range(max(0,int(y0)),min(H,int(y1)+1)):
        for x in range(max(0,int(x0)),min(W,int(x1)+1)): im[y][x]=c

def line(x0,y0,x1,y1,c,width=1):
    x0,y0,x1,y1=map(int,(x0,y0,x1,y1)); dx=abs(x1-x0);dy=-abs(y1-y0)
    sx=1 if x0<x1 else -1;sy=1 if y0<y1 else -1;e=dx+dy
    while True:
        rect(x0-(width-1)//2,y0-(width-1)//2,x0+width//2,y0+width//2,c)
        if x0==x1 and y0==y1: break
        e2=e*2
        if e2>=dy: e+=dy;x0+=sx
        if e2<=dx: e+=dx;y0+=sy

def poly(points,c):
    lo=max(0,min(y for x,y in points));hi=min(H-1,max(y for x,y in points))
    for y in range(lo,hi+1):
        cuts=[]
        for (x1,y1),(x2,y2) in zip(points,points[1:]+points[:1]):
            if y1!=y2 and min(y1,y2)<=y<max(y1,y2): cuts.append(x1+(y-y1)*(x2-x1)/(y2-y1))
        cuts.sort()
        for a,b in zip(cuts[::2],cuts[1::2]): rect(math.ceil(a),y,math.floor(b),y,c)
    for a,b in zip(points,points[1:]+points[:1]): line(*a,*b,c)

def ellipse(cx,cy,rx,ry,c):
    for y in range(cy-ry,cy+ry+1):
        for x in range(cx-rx,cx+rx+1):
            if ((x-cx)/rx)**2+((y-cy)/ry)**2<=1: px(x,y,c)

# Slow stepped gradient, with sparse ordered dithering only at band boundaries.
bands=[(0,3),(23,4),(43,5),(65,6),(85,7),(104,8),(122,9),(143,10),(167,11)]
for i,(start,col) in enumerate(bands):
    stop=bands[i+1][0] if i+1<len(bands) else H
    rect(0,start,255,stop-1,col)
    if i:
        for y in range(start,start+4):
            for x in range(W):
                if (x%4,y%4) in ([(0,0),(2,2),(1,3),(3,1)] if y<start+2 else [(0,0),(2,2)]): px(x,y,bands[i-1][1])

# Pixel cloud banks with intentionally stepped contours and warm rim light.
def cloud(x,y,scale=1):
    pts=[(0,9),(8,9),(8,6),(19,6),(19,3),(31,3),(31,0),(46,0),(46,3),(54,3),(54,6),(67,6),(67,9),(82,9),(82,12),(65,12),(65,14),(15,14),(15,12),(0,12)]
    poly([(x+a*scale,y+b*scale) for a,b in pts],8)
    for a,b,l in [(20,5,25),(9,8,47),(3,10,68)]: rect(x+a*scale,y+b*scale,x+(a+l)*scale,y+b*scale,10)
    rect(x+24*scale,y+12*scale,x+59*scale,y+13*scale,6)
cloud(-16,47)
cloud(165,31)
# Low wisps.
for x,y,length in [(4,99,48),(21,103,43),(169,101,62),(183,105,76),(2,125,24),(200,122,54),(62,78,26)]:
    rect(x,y,x+length,y+1,9);rect(x+6,y-1,x+length-10,y-1,10)
# The setting sun is a small, stepped disk, rather than a smooth vector circle.
ellipse(199,84,14,14,11);ellipse(199,83,12,12,12)
rect(179,88,207,89,8);rect(190,94,222,95,9)
# Distant birds.
for x,y in [(72,44),(83,49),(172,67)]:
    line(x-3,y-1,x,y+1,3);line(x,y+1,x+3,y-1,3)

# Paris skyline: far layer, slate roofs, chimneys, and a little domed pavilion.
for x in range(-3,260,9):
    ht=random.choice([8,10,13,16,19]);rect(x,157-ht,x+7,164,35)
    rect(x+1,156-ht,x+6,156-ht,34)
    if random.random()<.5: rect(x+4,152-ht,x+5,156-ht,34)
    for wy in range(160-ht,159,5):
        for wx in range(x+2,x+7,4): rect(wx,wy,wx,wy+1,37)
ellipse(42,136,9,8,34);rect(32,137,52,140,34);rect(35,141,49,158,36)
rect(41,123,43,128,34);line(42,121,42,125,34)
for x in range(37,50,4):rect(x,143,x+1,155,34)
# Middle-distance Haussmann terraces.
for x,w,top in [(-4,23,151),(20,22,148),(43,20,153),(63,17,150),(185,24,150),(210,24,145),(235,23,151)]:
    rect(x,top,x+w,175,38);rect(x+2,top+3,x+w-2,174,40)
    poly([(x-1,top),(x+3,top-7),(x+w-3,top-7),(x+w+1,top)],33)
    line(x+3,top-7,x+w-3,top-7,35)
    rect(x+5,top-11,x+7,top-6,33)
    for yy in [top+4,top+10,top+16]:
        if yy>173: continue
        for xx in range(x+4,x+w-2,5):
            rect(xx,yy,xx+1,yy+2,33);px(xx,yy,14)
        line(x+1,yy+3,x+w-1,yy+3,39)
    line(x,top,x+w,top,41)
# Tree-lined distant esplanade.
rect(0,173,255,186,29)
for x in list(range(0,77,7))+list(range(184,256,7)):
    y=random.randint(161,170)
    rect(x, y+3,x+1,179,27)
    ellipse(x,y,7,6,27);ellipse(x-2,y-2,5,4,28)
    rect(x-4,y-4,x,y-3,29)
rect(0,182,255,188,32);line(0,182,255,182,41)
rect(0,189,255,193,33);line(0,189,255,189,18)
for x in range(0,256,12):line(x,190,x,192,35)
line(0,194,255,194,25)

# Tower, built as tapered iron sections with outlined beams and cross bracing.
DARK=20;SHADE=18;MID=17;IRON=16;GOLD=15;LIT=14
cx=132
# Spire and lantern.
line(cx,18,cx,34,DARK);line(cx,20,cx,30,LIT)
rect(131,29,133,33,IRON);rect(129,33,135,43,DARK)
rect(130,33,133,35,LIT);rect(130,37,134,41,IRON);line(132,36,132,42,DARK)
poly([(127,43),(137,43),(139,47),(125,47)],DARK)
line(127,44,136,44,LIT);rect(125,47,139,49,SHADE);line(125,47,139,47,GOLD)
# Lattice tapered upper shaft. Dark inset is punctured by glints and rhythmic X braces.
levels=[(50,129,135),(60,128,136),(71,126,138),(82,124,140),(93,121,143),(106,117,147),(110,116,148)]
poly([(l,y) for y,l,r in levels]+[(r,y) for y,l,r in levels[::-1]],DARK)
for j in range(len(levels)-1):
    y,l,r=levels[j]; yy,ll,rr=levels[j+1]
    # Alternating warm faces make every brace readable at native resolution.
    line(l+2,y,rr-2,yy,MID);line(r-2,y,ll+2,yy,IRON)
    line(l+2,y-1,rr-2,yy-1,GOLD)
    line(l,y,ll,yy,GOLD,2);line(l+2,y,ll+2,yy,IRON)
    line(r,y,rr,yy,SHADE,2);line(r-1,y,rr-1,yy,IRON)
    line(l,y,r,y,MID);px(l,y,LIT)
line(132,51,132,106,IRON)
# Upper observation deck.
rect(112,108,152,110,DARK);line(113,108,151,108,LIT)
rect(114,111,150,114,SHADE);line(114,111,150,111,GOLD)
for x in range(117,150,4):px(x,112,LIT)
line(112,115,152,115,DARK)
# Open middle bay: the sunset is visible between the iron members.
left=[(117,116),(112,129),(106,143)];right=[(147,116),(152,129),(158,143)]
for path in [left,right]:
    for a,b in zip(path,path[1:]):line(*a,*b,DARK,5)
    for a,b in zip(path,path[1:]):line(a[0]-1,a[1],b[0]-1,b[1],GOLD,2);line(a[0]+1,a[1],b[0]+1,b[1],MID)
# Fine double cross-braced web between the second and first floors.
for a,b in [((119,116),(154,142)),((145,116),(110,142)),((119,116),(133,142)),((145,116),(131,142))]:
    line(*a,*b,DARK,3);line(a[0]-1,a[1],b[0]-1,b[1],IRON);line(*a,*b,GOLD)
line(113,128,151,128,DARK,2);line(114,127,150,127,IRON)
# First floor: projecting cornice, tiny balcony rails and illuminated rivets.
rect(100,141,164,143,DARK);line(101,141,163,141,LIT)
for x in range(103,164,3):line(x,138,x,141,MID)
line(103,138,161,138,IRON)
rect(99,144,165,148,DARK);rect(101,144,163,145,IRON)
line(100,144,164,144,LIT)
for x in range(103,162,4):rect(x,146,x+1,147,GOLD)
line(98,149,166,149,DARK);line(99,148,165,148,MID)
# Sweeping splayed feet. The curved negative space is the signature Eiffel arch.
lleg=[(103,150),(119,150),(116,154),(111,159),(107,165),(102,175),(100,182),(81,182),(89,171),(97,157)]
rleg=[(264-x,y) for x,y in lleg]
poly(lleg,DARK);poly(rleg,DARK)
# Metal faces and rails follow the curving legs.
for flip in [False,True]:
    def q(x):return 264-x if flip else x
    outer=[(104,151),(98,162),(91,174),(85,180)]
    inner=[(115,152),(108,162),(103,174),(101,180)]
    for path,col,width in [(outer,GOLD,3),(inner,IRON,2)]:
        for a,b in zip(path,path[1:]):line(q(a[0]),a[1],q(b[0]),b[1],col,width)
    for (y,l,r),(yy,ll,rr) in zip([(152,104,114),(160,100,109),(169,95,104)],[(160,100,109),(169,95,104),(179,87,100)]):
        line(q(l),y,q(rr),yy,IRON);line(q(r),y,q(ll),yy,GOLD)
        line(q(l),y,q(r),y,MID)
    line(q(84),181,q(99),181,LIT)
# Arch edging, graceful segmented arc.
arch=[(101,178),(105,167),(110,158),(117,152),(124,150),(140,150),(147,152),(154,158),(159,167),(163,178)]
for a,b in zip(arch,arch[1:]):line(*a,*b,MID);line(a[0],a[1]-1,b[0],b[1]-1,IRON)
# Small stone footings and pools of warm illumination.
for x in [80,162]:
    rect(x,183,x+22,185,18);rect(x+1,182,x+21,183,41)
    line(x-3,187,x+26,187,40)
# Distant park rail and diminutive pedestrians.
for x in [63,72,191,201]:
    line(x,178,x,184,20);px(x,176,20);line(x-1,180,x+1,180,20)
for x in [29,59,199,225]:
    line(x,174,x,182,33);rect(x-1,172,x+1,174,14);px(x,171,33)

# Seine: controlled horizontal clusters, reflected gold beneath the tower.
rect(0,195,255,223,22)
rect(0,197,255,199,23)
for y in range(196,224):
    for k in range(9):
        x=random.randrange(256);length=random.randint(3,17)
        if y%3==0:rect(x,y,x+length,y,random.choice([21,23,24]))
for y in range(196,222,3):
    half=18+(y-196)//3
    for k in range(3):
        x=random.randint(130-half,132+half)
        rect(x,y,x+random.randint(2,10),y,random.choice([38,39,40]))
# Tiny river launch with a lit cabin, left of the reflection.
line(43,204,77,204,20);poly([(46,205),(75,205),(70,208),(52,208)],20)
rect(52,200,66,203,41);rect(53,199,64,199,20)
for x in [54,59,64]:rect(x,201,x+2,202,22)
line(49,203,72,203,14);line(56,209,72,209,24)
# Near quays angle in from both corners, with stone paving.
poly([(0,208),(17,210),(72,223),(0,223)],42)
poly([(256,205),(237,209),(196,223),(255,223)],42)
line(0,208,17,210,32);line(17,210,72,223,32)
line(256,205,237,209,32);line(237,209,196,223,32)
for y in range(216,224,4):
    line(0,y,(y-208)*3,y,27)
    for x in range((y%8)-5,40,12):line(x,y,x-3,y+3,27)
# Ornamental foreground lamp, crisp silhouette and warm glass.
line(22,179,22,212,42,3);rect(18,213,26,215,42);rect(20,209,24,213,42)
rect(20,190,24,191,32);line(22,179,18,177,42);line(22,179,26,177,42)
poly([(17,166),(27,166),(26,176),(24,178),(20,178),(18,175)],42)
rect(19,168,25,174,15);rect(20,168,24,172,12);line(22,167,22,176,42)
poly([(16,166),(19,163),(21,162),(23,162),(25,163),(28,166)],42)
line(22,160,22,162,42);line(19,176,25,176,32)
# Foreground plane tree and ivy: sculpted pixel clusters, not soft circles.
poly([(245,215),(242,194),(245,177),(243,159),(247,155),(248,178),(246,197),(251,214)],42)
line(246,183,236,168,42,3);line(246,188,256,171,42,3)
def leafcluster(x,y,r,col):
    pts=[(x-r,y-2),(x-r+2,y-2),(x-r+2,y-r+2),(x-3,y-r+2),(x-3,y-r),(x+3,y-r),(x+3,y-r+2),(x+r-1,y-r+2),(x+r-1,y+1),(x+r,y+1),(x+r,y+4),(x+3,y+4),(x+3,y+r),(x-3,y+r),(x-3,y+r-2),(x-r,y+r-2)]
    poly(pts,col)
for x,y,r in [(249,151,12),(240,157,10),(255,163,14),(238,171,9),(251,175,11),(259,144,13)]:
    leafcluster(x,y,r,42);leafcluster(x-2,y-3,r-3,43);leafcluster(x-4,y-5,max(3,r-6),44)
    for k in range(3):
        xx=x+random.randint(-r+3,3);yy=y+random.randint(-r+2,-2)
        rect(xx,yy,xx+2,yy,45)
for x in range(218,258,6):
    leafcluster(x,220+random.randint(-2,3),5,43)
    rect(x-2,217,x,218,45)
for x,y in [(228,216),(237,220),(251,214)]:
    px(x,y,49);px(x+1,y,50);px(x,y+1,48)

# Enforce hardware tile constraints, using only the existing shared palette.
# Rare overfull tiles retain their most representative colors, weighted by use.
def dist(a,b):return sum((PAL[a][i]-PAL[b][i])**2 for i in range(3))
changed=0
for ty in range(0,H,8):
    for tx in range(0,W,8):
        counts=Counter(im[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8))
        if len(counts)<=16:continue
        chosen=[counts.most_common(1)[0][0]]
        while len(chosen)<16:
            candidates=[c for c in counts if c not in chosen]
            chosen.append(max(candidates,key=lambda c:min(dist(c,k) for k in chosen)*counts[c]**.65))
        mapping={c:min(chosen,key=lambda k:dist(c,k)) for c in counts}
        for y in range(ty,ty+8):
            for x in range(tx,tx+8):
                new=mapping[im[y][x]];changed+=new!=im[y][x];im[y][x]=new
# Indexed PNG, native resolution. No scaling, filters, antialiasing or external libraries.
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
raw=b''.join(b'\0'+bytes(row) for row in im)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+chunk(b'PLTE',b''.join(bytes(c) for c in PAL))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
os.makedirs('output',exist_ok=True)
with open('output/paris_at_the_golden_hour.png','wb') as f:f.write(png)
used=len(set(c for row in im for c in row))
max_tile=max(len({im[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)}) for ty in range(0,H,8) for tx in range(0,W,8))
assert used<=128 and max_tile<=16
print(f'256×224 indexed PNG; {used} total colors; maximum {max_tile} colors per 8×8 tile; {len(png)} bytes; {changed} pixels tile-remapped.')
