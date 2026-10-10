import math, random, struct, zlib, os
random.seed(16)
W,H=256,224
# One shared 16-entry SNES-style palette: every 8x8 tile is <=16 colors.
P=['171b35','292643','443653','654562','8b5971','b87583','db9291','efb393','f8d6a0','fff0bf','355168','47747b','69918a','a1ae91','9d713e','ca934f']
P=[tuple(bytes.fromhex(c)) for c in P]
im=[[0]*W for _ in range(H)]
def px(x,y,c):
 x,y=int(x),int(y)
 if 0<=x<W and 0<=y<H: im[y][x]=c
def rect(x0,y0,x1,y1,c):
 for y in range(max(0,int(y0)),min(H,int(y1)+1)):
  for x in range(max(0,int(x0)),min(W,int(x1)+1)): im[y][x]=c
def line(x0,y0,x1,y1,c):
 x0,y0,x1,y1=map(int,(x0,y0,x1,y1)); dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
 while True:
  px(x0,y0,c)
  if x0==x1 and y0==y1: break
  e=err*2
  if e>=dy: err+=dy;x0+=sx
  if e<=dx: err+=dx;y0+=sy
def poly(points,c):
 for y in range(max(0,min(p[1] for p in points)),min(H,max(p[1] for p in points)+1)):
  xs=[]
  for (x1,y1),(x2,y2) in zip(points,points[1:]+points[:1]):
   if min(y1,y2)<=y<max(y1,y2): xs.append(x1+(y-y1)*(x2-x1)/(y2-y1))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):rect(math.ceil(a),y,math.floor(b),y,c)
def ellipse(cx,cy,rx,ry,c):
 for y in range(cy-ry,cy+ry+1):
  for x in range(cx-rx,cx+rx+1):
   if (x-cx)**2*ry**2+(y-cy)**2*rx**2<=rx**2*ry**2:px(x,y,c)
# Banded dusk, with sparse ordered dithering at the color joins.
bands=[(0,2),(26,3),(53,4),(81,5),(108,6),(132,7)]
for i,(start,col) in enumerate(bands):
 end=bands[i+1][0] if i+1<len(bands) else 181
 rect(0,start,255,end-1,col)
 if i:
  for y in range(start,start+5):
   for x in range(W):
    if (x+2*y)%4==0 and y<start+3: px(x,y,col-1)
# Pixel-cut cirrus clouds.
for x,y,length in [(5,41,59),(20,46,63),(161,66,82),(179,72,52),(-8,95,76),(11,100,66),(161,115,103)]:
 poly([(x,y+3),(x+8,y+3),(x+8,y+1),(x+23,y+1),(x+23,y),(x+length-15,y),(x+length-15,y+2),(x+length,y+2),(x+length,y+4),(x+length-7,y+4),(x+length-7,y+5),(x,y+5)],5 if y<80 else 6)
 line(x+8,y+5,x+length-14,y+5,6 if y<80 else 7)
# Moon and a few early stars.
ellipse(204,31,10,10,8); ellipse(208,27,9,9,3)
for x,y in [(21,20),(79,16),(160,24),(237,51),(97,40),(181,11)]:
 px(x,y,8)
 if x==21:line(x-1,y,x+1,y,8);line(x,y-1,x,y+1,8)
# Faint skyline silhouettes.
for x in range(0,256,6):
 h=random.randint(6,19);rect(x,165-h,x+5,169,5)
 if x%18==0:line(x+2,162-h,x+2,165-h,5)
# Distant domes and roofs.
ellipse(218,149,9,7,4);rect(208,149,228,168,4);rect(216,137,220,143,4);line(218,133,218,137,4)
for x in range(-5,260,13):
 h=random.randint(10,22);y=174-h
 rect(x,y,x+11,175,3); poly([(x-1,y),(x+3,y-4),(x+8,y-4),(x+12,y)],2)
 line(x,y+1,x+10,y+1,5)
 for yy in range(y+4,172,5):
  for xx in range(x+2,x+10,4):rect(xx,yy,xx+1,yy+1,7 if random.random()<.4 else 4)
# Riverside trees.
for x in list(range(-4,76,9))+list(range(185,263,8)):
 y=random.randint(164,171)
 rect(x-1,y,x+1,183,1)
 for dx,dy,r in [(-4,0,6),(3,-2,6),(0,-6,5)]:
  ellipse(x+dx,y+dy,r,r,10);ellipse(x+dx-1,y+dy-2,r-2,r-2,11)
# Far stone embankment.
rect(0,181,255,187,3);line(0,181,255,181,8);line(0,183,255,183,5)
for x in range(0,256,12):line(x,184,x,186,2)
# Water, long horizontal broken reflections.
rect(0,188,255,218,10)
for y in range(189,219):
 for n in range(7):
  x=random.randrange(256);ln=random.randrange(2,17)
  col=random.choice([11,11,12,3,4])
  if 94<x<164:col=random.choice([7,15,5,11])
  line(x,y,min(255,x+ln),y,col)
# Tower ironwork. Deliberately open, silhouette-braced lattice panels.
# Coordinates describe the outer and inner edges of each tapered pier.
def beam(a,b,c=15): line(*a,*b,c)
def panel(points,left,right,steps):
 poly(points,2)
 # Decorative panel cross-braces, constrained between tapered edges.
 for i in range(steps):
  t=i/steps;u=(i+1)/steps
  def lerp(a,b,t):return (round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t))
  l0=lerp(*left,t);l1=lerp(*left,u);r0=lerp(*right,t);r1=lerp(*right,u)
  beam(l0,r1,14);beam(r0,l1,15);beam(l1,r1,14)
 beam(*left,8);beam(*right,15)
# Feet and arch piers.
left=[(101,148),(117,150),(113,157),(108,165),(105,174),(103,181),(80,181),(89,165)]
right=[(139,150),(155,148),(167,166),(176,181),(153,181),(151,174),(147,165),(143,157)]
panel(left,((101,148),(81,180)),((115,150),(103,180)),4)
panel(right,((140,150),(153,180)),((155,148),(175,180)),4)
# Curved arch soffit joining the two massive legs.
poly([(101,149),(155,149),(160,159),(149,159),(143,154),(136,152),(121,152),(114,154),(107,159),(96,159)],2)
line(107,159,114,153,15);line(114,153,122,151,8);line(122,151,135,151,15);line(135,151,143,154,14);line(143,154,149,159,14)
# Lower tapered shaft, broad transparent crossed ironwork.
panel([(113,112),(143,112),(154,146),(102,146)],((113,113),(102,146)),((143,113),(154,146)),4)
# Interior main stanchions split the large Xs into finer trusses.
line(122,115,116,146,15);line(134,115,140,146,14)
for y in range(120,146,7):
 half=round(15+(y-112)*.34);line(128-half,y,128+half,y,14)
# Upper taper.
panel([(124,54),(132,54),(142,108),(114,108)],((124,54),(114,108)),((132,54),(142,108)),8)
line(128,57,127,107,14)
# Observation decks and railings.
def deck(x0,x1,y):
 rect(x0,y,x1,y+5,2);line(x0,y,x1,y,8);line(x0-1,y+4,x1+1,y+4,15);line(x0,y+5,x1,y+5,1)
 for x in range(x0+2,x1,3):px(x,y+2,7)
 line(x0+1,y-3,x1-1,y-3,15)
 for x in range(x0+1,x1,4):line(x,y-3,x,y-1,14)
deck(98,158,145);deck(110,146,108);deck(121,135,51)
rect(124,43,132,50,2);rect(125,44,127,49,8);rect(129,44,131,49,14)
poly([(123,43),(126,39),(130,39),(133,43)],15)
line(128,25,128,39,8);line(129,29,129,40,14);px(128,24,9)
for x in [80,94,153,168]:rect(x,181,x+8,183,14);line(x,181,x+8,181,8)
# Warm lamps and tiny strolling figures give the scene game-scale life.
for x in [18,58,195,238]:
 line(x,170,x,181,1);line(x-2,181,x+2,181,1);rect(x-2,166,x+2,169,2);rect(x-1,166,x+1,168,9);px(x,164,1)
for x,y in [(66,180),(71,181),(188,180)]:
 px(x,y-5,8);line(x,y-4,x,y-1,1);px(x-1,y,1);px(x+1,y,1)
# Small river launch.
poly([(187,202),(217,202),(212,207),(192,207)],1);line(188,202,216,202,8)
rect(195,197,208,201,3);rect(196,198,199,200,8);rect(202,198,206,200,8);line(194,196,209,196,15);line(209,199,213,199,7)
line(215,208,230,208,12);line(191,209,210,209,11)
# Near quay: beveled stones and an ornamental iron railing.
rect(0,216,255,223,1);line(0,216,255,216,12);line(0,218,255,218,3)
for x in range(0,256,24):line(x,219,x-3,223,0)
# Small foreground corner foliage, kept clear of the central reflection.
for x,y,r in [(0,211,11),(11,220,9),(247,222,11),(255,213,8)]:
 ellipse(x,y,r,r,0)
 for _ in range(15):
  xx=x+random.randint(-r,r);yy=y+random.randint(-r,r)
  if 0<=xx<W and 0<=yy<H and im[yy][xx]==0:line(xx,yy,xx+2,yy,10)
# Indexed PNG, native 256x224; no scaling or antialiasing.
os.makedirs('output',exist_ok=True)
def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
raw=b''.join(b'\0'+bytes(row) for row in im)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+chunk(b'PLTE',b''.join(bytes(p) for p in P))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
open('output/paris-at-dusk.png','wb').write(png)
assert len(set(c for row in im for c in row))<=128
assert max(len({im[y+dy][x+dx] for dy in range(8) for dx in range(8)}) for y in range(0,H,8) for x in range(0,W,8))<=16
print('Saved output/paris-at-dusk.png: 256x224, 16 total colors, all 8x8 tiles <=16 colors.')
