import math, random
random.seed(16)
W,H=320,384
# A restricted, RGB565-quantized palette, drawn entirely on a pixel grid.
P={
'ink':'292439','iron':'443047','light':'a66c69','gold':'edaa79','edge':'d38c73',
'sky0':'77768f','sky1':'998298','sky2':'b58c9e','sky3':'d59ca3','sky4':'e5aca5','sky5':'efbda5','sky6':'f4ccaa',
'cloud':'cf9aa5','cloudlight':'f5c6b1','sun':'ffe2ad','sunedge':'f8cfa0',
'cityfar':'ae8595','city':'806e87','roof':'62576f','window':'efbe90',
'water':'737c99','waterlight':'a39bae','waterdark':'5d647e','leaf':'414356','leaflight':'5c5c68','leafdark':'303344',
'ground':'555064','stone':'a38b91','stonehi':'d7b3a0'}
def rgb(h):
    return tuple(int(h[i:i+2],16) for i in (0,2,4))
P={k:tuple(round(round(c*((31,63,31)[i])/255)*255/((31,63,31)[i])) for i,c in enumerate(rgb(v))) for k,v in P.items()}
img=[[P['sky0'] for x in range(W)] for y in range(H)]
def px(x,y,c):
    if 0<=x<W and 0<=y<H: img[y][x]=P[c] if isinstance(c,str) else c
def rect(x0,y0,x1,y1,c):
    for y in range(max(0,int(y0)),min(H,int(y1)+1)):
        for x in range(max(0,int(x0)),min(W,int(x1)+1)): px(x,y,c)
def line(x0,y0,x1,y1,c,w=1):
    n=max(abs(int(x1-x0)),abs(int(y1-y0)),1)
    for i in range(n+1):
        x=round(x0+(x1-x0)*i/n);y=round(y0+(y1-y0)*i/n)
        rect(x-w//2,y-w//2,x+(w-1)//2,y+(w-1)//2,c)
def poly(points,c):
    for y in range(max(0,math.ceil(min(p[1] for p in points))),min(H,math.ceil(max(p[1] for p in points))+1)):
        xs=[]
        for a,b in zip(points,points[1:]+points[:1]):
            if (a[1]<=y<b[1]) or (b[1]<=y<a[1]): xs.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        xs.sort()
        for i in range(0,len(xs)-1,2): rect(math.ceil(xs[i]),y,math.floor(xs[i+1]),y,c)
def disk(x,y,r,c):
    for yy in range(-r,r+1):
        dx=int(math.sqrt(r*r-yy*yy));rect(x-dx,y+yy,x+dx,y+yy,c)
# Banded dusk with a little ordered pixel dithering at the transitions.
for y in range(0,310):
    band=min(6,y//44)
    rect(0,y,319,y,'sky'+str(band))
    if y%44<5 and band>0:
        for x in range(W):
            if (x+2*y)%4>=y%44: px(x,y,'sky'+str(band-1))
disk(231,121,30,'sunedge');disk(231,120,27,'sun')
# Clouds are deliberately stepped, not antialiased.
for x,y,w in [(8,76,79),(33,83,92),(205,56,72),(239,62,70),(8,162,78),(217,185,93),(191,191,103)]:
    rect(x,y,x+w,y+3,'cloud');rect(x+9,y-3,x+w-15,y,'cloud');rect(x+20,y-5,x+w-29,y-3,'cloud')
    rect(x+5,y+4,x+w-5,y+4,'cloudlight')
for x,y in [(45,41),(93,29),(282,31),(193,24),(27,112)]:
    px(x,y,'sun');px(x+1,y,'sun')
# Distant Paris roofs, chimneys, and a domed landmark.
for x in range(0,W,8):
    ht=random.randrange(5,22); y=281-ht
    rect(x,y,x+7,287,'cityfar')
    if random.random()<.65: rect(x+2,y-3,x+3,y,'cityfar')
for x in range(-4,W,13):
    y=random.randrange(267,280)
    rect(x,y,x+11,300,'city');poly([(x-2,y),(x+4,y-5),(x+12,y)],'roof')
    if random.random()<.65: rect(x+8,y-8,x+9,y-2,'roof')
    for yy in range(y+5,297,6):
        for xx in range(x+2,x+11,4):
            rect(xx,yy,xx+1,yy+1,'window' if random.random()<.38 else 'roof')
rect(263,264,278,292,'city');disk(270,265,7,'roof');rect(261,269,280,272,'stone');line(270,253,270,259,'roof',2)
# Quay and the river.
rect(0,298,319,315,'ground');rect(0,299,319,301,'stone');rect(0,304,319,306,'stonehi')
rect(0,316,319,383,'water')
for y in range(318,384,3):
    for j in range(10):
        x=random.randrange(W);length=random.randrange(3,18)
        rect(x,y,min(319,x+length),y,'waterlight' if random.random()<.45 else 'waterdark')
for y in range(321,378,3):
    spread=7+(y-321)//3
    x=231+random.randrange(-spread,spread)
    rect(x,y,x+random.randrange(4,16),y,'gold' if y%2 else 'stonehi')
# Tower, assembled from individual iron members with open latticework.
# Top taper is a succession of changing-width bays.
levels=[(73,159,161),(91,157,163),(111,155,165),(133,152,168),(154,146,174),(177,139,181),(202,129,191)]
for (y,l,r),(yy,ll,rr) in zip(levels,levels[1:]):
    line(l,y,ll,yy,'iron',3);line(r,y,rr,yy,'iron',3)
    line(l,y,rr,yy,'iron');line(r,y,ll,yy,'iron')
    line(l,y,r,y,'iron',2)
    line(r+1,y,rr+1,yy,'edge')
    line((l+r)//2,y,(ll+rr)//2,yy,'light')
    if yy-y>16: line((l+ll)//2,(y+yy)//2,(r+rr)//2,(y+yy)//2,'iron')
# Needle and lantern.
line(160,48,160,69,'iron');px(160,47,'gold');rect(158,67,162,74,'iron');rect(159,67,160,69,'gold');rect(155,76,165,79,'iron')
# Upper observation floor.
rect(142,154,178,157,'iron');rect(141,158,179,161,'iron');rect(143,155,179,155,'edge')
for x in range(145,179,4): rect(x,157,x,158,'gold')
# Four outward-curving legs with lit outer edges.
legs=[[(129,210),(138,214),(126,247),(116,269),(105,296),(92,296),(106,267),(117,239)],
      [(182,214),(191,210),(203,239),(214,267),(228,296),(215,296),(204,269),(194,247)]]
for pts in legs: poly(pts,'iron')
line(129,215,117,247,'light');line(117,247,95,294,'light')
line(191,215,203,247,'edge');line(203,247,225,294,'edge')
# Lattice on the legs: alternating diagonals and small transverse bars.
for side in [-1,1]:
    def legpos(y): return 160+side*(29+(y-214)*.40+(max(0,y-250))*.19)
    for y in range(217,291,9):
        a=legpos(y);b=legpos(y+9)
        line(a-4,y,b+4,y+9,'light');line(a+4,y,b-4,y+9,'ink')
        line(a-4,y,a+4,y,'edge')
# The large architectural arch beneath the first floor.
arch=[]
for i in range(25):
    t=math.pi+i*math.pi/24
    arch.append((160+37*math.cos(t),298+31*math.sin(t)))
for a,b in zip(arch,arch[1:]): line(*a,*b,'iron',5)
for a,b in zip(arch,arch[1:]): line(a[0],a[1]-2,b[0],b[1]-2,'light')
# Structural ribs between the first and second floors.
line(137,215,145,250,'iron',3);line(183,215,175,250,'iron',3)
line(135,220,183,248,'iron');line(185,220,137,248,'iron')
line(128,235,192,235,'iron',2)
for x in range(131,191,10): line(x,235,x+5,249,'light')
# Two broad terraces, tiny rivets and balustrades.
for l,r,y in [(124,196,203),(108,212,251)]:
    rect(l,y,r,y+3,'iron');rect(l-2,y+4,r+2,y+8,'ink');rect(l-1,y+4,r+1,y+4,'edge')
    rect(l+2,y+9,r-2,y+10,'iron')
    for x in range(l+3,r,4):
        rect(x,y-3,x,y-1,'iron');px(x,y+6,'gold')
    line(l+1,y-3,r-1,y-3,'iron')
# Masonry footings.
for x in [89,211]:
    rect(x,295,x+20,299,'stone');rect(x-3,300,x+23,303,'roof');rect(x,295,x+20,295,'stonehi')
# A few pedestrians and warm lamps along the embankment.
for x in [57,74,245,258]:
    disk(x,298,1,'ink');line(x,300,x,304,'ink');px(x-1,305,'ink');px(x+1,305,'ink')
for x in [34,81,239,286]:
    line(x,286,x,306,'ink');rect(x-2,284,x+2,288,'ink');rect(x-1,285,x+1,287,'sun');rect(x-3,283,x+3,283,'ink')
# Foreground tree masses as clustered, stepped pixels.
for cx,cy,r in [(-3,272,27),(14,290,20),(314,260,27),(306,285,22)]:
    line(cx,cy,cx+3,322,'leafdark',6)
    for i in range(38):
        xx=cx+random.randrange(-r,r+1);yy=cy+random.randrange(-r,r+1)
        if (xx-cx)**2+(yy-cy)**2<r*r:
            size=random.randrange(3,9);rect(xx-size,yy-size,xx+size,yy+size,random.choice(['leaf','leaf','leafdark','leaflight']))
# Lower foreground river wall, leaves and quiet decorative frame.
poly([(0,364),(45,372),(112,384),(0,384)],'ink')
line(0,363,108,383,'stone',3)
for i in range(40):
    x=random.randrange(0,52);y=random.randrange(348,383)
    rect(x,y,x+random.randrange(2,5),y+2,'leafdark')
rect(0,0,319,6,'ink');rect(0,377,319,383,'ink');rect(0,0,6,383,'ink');rect(313,0,319,383,'ink')
line(8,8,311,8,'light');line(8,375,311,375,'light');line(8,8,8,375,'light');line(311,8,311,375,'light')
with open('scene.ppm','wb') as f:
    f.write(('P6\n%d %d\n255\n'%(W,H)).encode())
    f.write(bytes(v for row in img for color in row for v in color))
