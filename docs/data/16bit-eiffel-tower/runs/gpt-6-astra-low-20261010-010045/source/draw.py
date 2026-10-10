import math, random, struct, zlib, os
random.seed(18)
W,H=256,224
# A shared 16-colour master palette also guarantees <=16 colours per 8x8 tile.
palette=['24243e','393653','574667','805775','ac6c83','d78c92','efafa0','ffcfaa','ffe3b5','bd866a','8d605c','624951','34525e','467477','74a19a','c2c6a4']
pal=[tuple(bytes.fromhex(c)) for c in palette]
pix=[[0]*W for _ in range(H)]
def dot(x,y,c):
 if 0<=x<W and 0<=y<H: pix[y][x]=c
def rect(x,y,w,h,c):
 for yy in range(max(0,y),min(H,y+h)):
  for xx in range(max(0,x),min(W,x+w)):pix[yy][xx]=c
def line(x0,y0,x1,y1,c,width=1):
 x0,y0,x1,y1=map(round,(x0,y0,x1,y1));dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
 while True:
  rect(x0,y0,width,width,c)
  if x0==x1 and y0==y1:break
  e=2*err
  if e>=dy:err+=dy;x0+=sx
  if e<=dx:err+=dx;y0+=sy

def poly(pts,c):
 for y in range(max(0,min(p[1] for p in pts)), min(H,max(p[1] for p in pts)+1)):
  xs=[]
  for (a,b),(d,e) in zip(pts,pts[1:]+pts[:1]):
   if (b<=y<e) or(e<=y<b):xs.append(a+(y-b)*(d-a)/(e-b))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):
   for x in range(max(0,math.ceil(a)),min(W,math.floor(b)+1)):pix[y][x]=c

def ellipse(cx,cy,rx,ry,c):
 for y in range(cy-ry,cy+ry+1):
  k=math.sqrt(max(0,1-((y-cy)/ry)**2));rect(round(cx-rx*k),y,round(2*rx*k)+1,1,c)
# Banded painted sunset, with fine ordered transitions.
bands=[(0,34,2),(34,62,3),(62,88,4),(88,119,5),(119,149,6),(149,177,7)]
for a,b,c in bands:rect(0,a,W,b-a,c)
for a,b,c in bands[:-1]:
 for y in range(b-3,b+3):
  for x in range(W):
   if (x%4,y%2) in ([(0,0)] if y<b else [(0,0),(2,1),(1,0)]):dot(x,y,c+1)
# Sun and elongated pixel clouds.
ellipse(192,91,23,23,7);ellipse(192,91,19,19,8)
rect(167,98,51,2,6);rect(169,104,47,3,5);rect(177,111,31,2,6)
for x,y,w in [(9,42,67),(20,38,34),(0,47,44),(161,33,75),(180,29,28),(199,39,57),(28,77,49),(5,82,48),(213,71,42)]:
 rect(x,y,w,2,4 if y<60 else 6);rect(x+5,y-2,max(5,w-16),2,3 if y<60 else 5)
for x,y in [(22,18),(76,28),(149,15),(230,19),(91,51)]:dot(x,y,7)
# Distant Paris roofline.
rect(0,163,256,19,4)
for x in range(-4,259,9):
 h=random.randrange(7,20);rect(x,166-h,8,h+12,4);rect(x-1,166-h,10,2,3)
 if random.random()<.65:rect(x+2,162-h,2,4,3)
 for yy in range(153,173,5):
  if yy>167-h:
   for xx in [x+2,x+5]:rect(xx,yy,1,2,6)
# Left distant dome.
rect(28,149,20,20,3);ellipse(38,148,10,8,3);rect(36,135,4,6,3);line(38,129,38,138,3)
# Riverbank trees, muted background.
for x in range(-4,262,7):
 y=random.randrange(165,172);ellipse(x,y,9,7,12);ellipse(x-2,y-2,5,4,13)
rect(0,177,256,17,10);rect(0,178,256,2,7)
# Plaza perspective paving.
for y in [183,188,194]:line(0,y,255,y,9)
for x in range(-120,400,32):line(128,176,x,198,11)
# Tower feet and shadow.
ellipse(130,191,66,4,11)
for x in [73,158]:rect(x,187,25,5,9);rect(x,187,25,2,7)
# Main lower legs: open lattice, outward taper.
for pts in [[(108,131),(124,134),(98,188),(77,188)],[(132,134),(148,131),(179,188),(158,188)]]:
 poly(pts,0)
# Snapshot-free open windows use plaza / sky colour approximations only inside girders.
# Build each leg as narrow open quadrilateral panels with cross ties.
for side in [-1,1]:
 def point(y,outer):
  t=(y-134)/54
  return round(128+side*((20+31*t) if outer else (5+25*t)))
 for ya,yb in [(137,149),(151,165),(167,185)]:
  a=point(ya,True);b=point(ya,False);c=point(yb,False);d=point(yb,True)
  pts=[(a-side*3,ya),(b+side*2,ya),(c+side*2,yb),(d-side*3,yb)]
  poly(pts,5 if ya<150 else (4 if ya<166 else 12))
  line(a,ya,c,yb,9);line(b,ya,d,yb,10)
  line(a,ya,d,yb,7);line(b,ya,c,yb,10)
  line(a,yb,d,yb,0)
 line(point(134,True),134,point(188,True),188,9,2)
 line(point(136,True)-side*2,136,point(187,True)-side*2,187,7)
# Monument's curving arch, stepped wrought iron rim.
for side in [-1,1]:
 pts=[(128+side*5,145),(128+side*13,147),(128+side*21,154),(128+side*27,164),(128+side*32,180)]
 for p,q in zip(pts,pts[1:]):line(*p,*q,0,3);line(p[0],p[1],q[0],q[1],9)
# Tapered upper framework.
levels=[(55,3),(69,4),(82,6),(95,9),(108,13),(122,18),(133,22)]
for (ya,wa),(yb,wb) in zip(levels,levels[1:]):
 for side in [-1,1]:
  line(128+side*wa,ya,128+side*wb,yb,0,3)
  line(128+side*wa,ya,128+side*wb,yb,9)
 line(128-wa,ya,128+wa,ya,0,2)
 line(128-wa+2,ya+2,128+wb-1,yb,10)
 line(128+wa-1,ya+2,128-wb+2,yb,9)
 line(128,ya,128,yb,0)
# Warm left edge / shadow right edge.
for (ya,wa),(yb,wb) in zip(levels,levels[1:]):line(127-wa,ya,127-wb,yb,7)
# Observation decks with cornices, rails and repeating golden windows.
def deck(x,y,w):
 rect(x,y,w,2,9);rect(x,y,w,1,8);rect(x+2,y+2,w-4,5,0)
 for xx in range(x+3,x+w-3,4):rect(xx,y+3,2,2,7)
 rect(x-1,y+7,w+2,2,0);rect(x-1,y+7,w+2,1,9)
 for xx in range(x+2,x+w,4):line(xx,y-3,xx,y-1,0)
 line(x+1,y-3,x+w-2,y-3,9)
deck(103,132,51);deck(115,99,27)
# Summit lantern, antenna and delicate spire.
rect(124,48,9,10,0);rect(125,49,6,5,9);rect(126,49,2,5,8)
rect(122,55,13,2,0);rect(123,55,11,1,7)
poly([(123,47),(127,40),(130,40),(134,47)],0);line(126,43,128,40,9)
line(128,28,128,41,0);line(127,32,127,39,7);dot(128,27,8)
# Foreground promenade and river, decorative masonry.
rect(0,197,256,27,12);rect(0,197,256,2,0);rect(0,199,256,2,9)
for y in range(203,224,3):
 for i in range(17):
  x=random.randrange(256);w=random.randrange(2,17);rect(x,y,w,1,13)
for y in range(204,224,3):
 for i in range(5):
  x=184+random.randrange(-21,22);rect(x,y,random.randrange(3,12),1,6 if y<214 else 9)
# Stone river balustrade.
rect(0,191,256,2,7);rect(0,193,256,2,11)
for x in range(0,256,8):rect(x,194,2,4,10)
# Framing foliage and gas lanterns.
for side in [0,255]:
 for i in range(40):
  x=side+random.randrange(-23,24);y=random.randrange(169,198)
  ellipse(x,y,random.randrange(3,9),4,0)
  if i%3==0:rect(x-3,y-2,4,1,12)
for x in [33,222]:
 rect(x-1,177,3,15,0);rect(x-3,190,7,2,0)
 rect(x-3,170,7,7,0);rect(x-2,171,5,4,8);rect(x,171,1,5,9)
 poly([(x-5,170),(x,166),(x+5,170)],0);dot(x,165,9)
# Indexed PNG, native resolution, no resampling.
os.makedirs('output',exist_ok=True)
def chunk(t,data):return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data)&0xffffffff)
raw=b''.join(b'\0'+bytes(row) for row in pix)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+chunk(b'PLTE',b''.join(bytes(c) for c in pal))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
open('output/eiffel-twilight.png','wb').write(png)
assert len(set(sum(pix,[])))<=128
assert all(len({pix[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)})<=16 for ty in range(0,H,8) for tx in range(0,W,8))
print('256x224; 16-colour indexed PNG; every 8x8 tile uses <=16 colours.')
