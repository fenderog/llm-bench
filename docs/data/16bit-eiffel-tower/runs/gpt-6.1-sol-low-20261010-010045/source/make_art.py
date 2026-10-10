import math, random, struct, zlib
random.seed(17)
W,H=256,224
# Shared, deliberately compact 16-bit era palette.
colors=['29243f','39304f','4c395d','614267','794b70','955576','b5637b','d07882','e99189','f4b393','ffd39d','ffe4b1', # sky
'343348','454052','595062','706071','8d7580','ad8b8c', # town
'241f35','3d2c40','593747','75454b','975957','bc7563','dc9977','f4c58c', # iron
'203b46','30505a','43646b','608084','90a29b', # water
'172e37','244442','356054','56806a','b0b58a','eee0b3']
pal=[tuple(bytes.fromhex(c)) for c in colors]
p=[[0]*W for _ in range(H)]
def dot(x,y,c):
 x,y=int(x),int(y)
 if 0<=x<W and 0<=y<H:p[y][x]=c
def rect(x0,y0,x1,y1,c):
 for y in range(max(0,int(y0)),min(H,int(y1)+1)):
  for x in range(max(0,int(x0)),min(W,int(x1)+1)):p[y][x]=c
def line(x0,y0,x1,y1,c,width=1):
 n=max(abs(int(x1-x0)),abs(int(y1-y0)),1)
 for i in range(n+1):
  x=round(x0+(x1-x0)*i/n);y=round(y0+(y1-y0)*i/n)
  rect(x-width//2,y-width//2,x+(width-1)//2,y+(width-1)//2,c)
def poly(pts,c):
 for y in range(max(0,min(v[1] for v in pts)),min(H,max(v[1] for v in pts)+1)):
  xs=[]
  for (x1,y1),(x2,y2) in zip(pts,pts[1:]+pts[:1]):
   if min(y1,y2)<=y<max(y1,y2):xs.append(x1+(y-y1)*(x2-x1)/(y2-y1))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):rect(math.ceil(a),y,math.floor(b),y,c)
# Banded sunset, with sparse ordered transition pixels.
for y in range(170):
 c=min(10,y//16)
 rect(0,y,255,y,c)
 if y%16 in (0,1):
  for x in range((y%2)*2,256,4):dot(x,y,max(0,c-1))
# Small sunset disc, hidden behind the ironwork.
for y in range(87,126):
 for x in range(159,198):
  if (x-178)**2+(y-106)**2<19**2:dot(x,y,11 if y<112 else 10)
# Long broken cloud banks, shaded underneath.
for x,y,w in [(4,44,69),(173,33,70),(12,79,54),(190,71,65),(48,103,37)]:
 rect(x,y+3,x+w,y+5,5 if y<60 else 8)
 rect(x+9,y,x+w-12,y+2,6 if y<60 else 9)
 rect(x+22,y-2,x+w-25,y,6 if y<60 else 9)
 for k in range(5):rect(x+k*13,y+6,x+k*13+7,y+6,4 if y<60 else 7)
# Distant roofs / Paris city, with limited warm window motifs.
rect(0,155,255,177,15)
for x in range(0,256,7):
 h=random.randrange(8,23);rect(x,157-h,x+6,168,14)
 if random.random()<.5:poly([(x-1,157-h),(x+3,152-h),(x+7,157-h)],13)
 for y in range(160-h,166,5):
  for xx in (x+1,x+4):
   if random.random()<.48:rect(xx,y,xx+1,y+1,17)
# Distant domed silhouette on right.
rect(219,135,241,161,13);rect(224,129,237,136,13)
poly([(223,130),(225,124),(230,120),(236,124),(239,130)],13)
line(230,116,230,121,13)
# Seine and embankment.
rect(0,174,255,214,26)
rect(0,172,255,174,12)
for y in range(178,213):
 for k in range(9):
  x=random.randrange(256);w=random.randrange(2,16)
  rect(x,y,x+w,y,random.choice([27,28,29]))
for y in range(179,211,3):
 for k in range(3):
  x=178+random.randrange(-22,23);rect(x,y,x+random.randrange(3,15),y,24 if y<190 else 30)
# Main tower: broad concave silhouette legs and narrowing spire.
left=[(124,45),(121,66),(116,87),(111,108),(103,131),(92,157),(76,181),(66,191),(84,191),(97,172),(110,148),(120,120),(124,89),(127,56)]
right=[(256-x,y) for x,y in left]
poly(left,19);poly(right,18)
# Bronze lit faces.
poly([(124,49),(122,77),(117,104),(109,133),(97,158),(79,187),(73,187),(91,158),(103,130),(113,101),(120,72)],22)
poly([(132,49),(136,81),(143,110),(153,139),(166,167),(181,187),(172,187),(158,160),(148,137),(139,105)],21)
# Cross-braced panels along both legs, with tiny highlight joints.
for side in [-1,1]:
 def coord(y):
  # outside and inside edge widths at landmark levels
  levels=[(50,4,0),(76,10,3),(103,16,7),(128,24,12),(153,35,20),(177,50,34),(190,60,44)]
  for (a,o,i),(b,oo,ii) in zip(levels,levels[1:]):
   if a<=y<=b:
    t=(y-a)/(b-a);return 128+side*(o+(oo-o)*t),128+side*(i+(ii-i)*t)
  return 128+side*4,128
 for a,b in [(57,67),(68,80),(81,94),(95,108),(109,122),(123,137),(138,152),(153,168),(169,181),(182,188)]:
  oa,ia=coord(a);ob,ib=coord(b)
  line(oa,a,ib,b,24 if side<0 else 22)
  line(ia,a,ob,b,20)
  line(oa,a,ia,a,23)
  dot(oa,a,25 if side<0 else 23)
 for a in range(58,190,3):
  o,i=coord(a);dot(o,a,24 if side<0 else 22)
# Lower arch: curved load-bearing truss above negative space.
poly([(93,157),(101,147),(155,147),(163,157),(157,169),(148,156),(139,150),(117,150),(108,156),(99,169)],20)
line(103,155,114,148,23);line(114,148,142,148,23);line(142,148,153,155,22)
for x in range(109,151,5):line(x,143,x+3,150,23)
# Observation decks: sharply stepped platforms.
for x0,x1,y in [(98,158,137),(110,146,104),(119,137,72)]:
 rect(x0,y,x1,y+5,18);rect(x0-2,y-1,x1+2,y,24)
 rect(x0+1,y+2,x1-1,y+2,22)
 for x in range(x0+2,x1,4):dot(x,y+4,25)
 line(x0,y-5,x1,y-5,21)
 for x in range(x0,x1+1,4):line(x,y-5,x,y-1,23)
# Top cabin and needle.
rect(124,41,132,55,20);rect(123,47,133,49,24)
rect(125,43,126,45,25);rect(129,43,130,45,23)
line(128,23,128,40,23);line(127,30,129,30,25)
rect(125,38,131,40,22);dot(128,22,11)
# Stone footings.
for x in [67,175]:
 rect(x-3,190,x+13,193,18);rect(x-1,188,x+11,190,16);line(x-1,188,x+11,188,25)
# Foreground promenade, paved in repeating isometric stones.
rect(0,212,255,223,12);rect(0,209,255,211,17);line(0,209,255,209,36)
for y in (215,221):
 line(0,y,255,y,13)
 for x in range(-8,256,16):line(x+(8 if y==221 else 0),y-3,x+3+(8 if y==221 else 0),y,15)
# Cast-iron railing along the river.
line(0,201,255,201,18);line(0,207,255,207,18)
for x in range(0,256,8):line(x,201,x,208,18);dot(x,200,17)
# Rich foliage framing the scene, pixel cluster shading.
for side in (0,1):
 for k in range(45):
  x=random.randrange(-12,42) if side==0 else random.randrange(225,271)
  y=random.randrange(153,194);r=random.randrange(4,11)
  poly([(x-r,y),(x-r+2,y-4),(x-3,y-r),(x+4,y-r+2),(x+r,y-3),(x+r,y+4),(x+3,y+r),(x-r+2,y+r-2)],31)
  rect(x-4,y-4,x+3,y-2,32)
  if k%3==0:rect(x-3,y-5,x,y-4,33)
# Two glowing lamps, with no blur or antialiasing.
for x in [25,230]:
 rect(x-3,207,x+3,209,18);line(x,177,x,207,18,2)
 rect(x-4,168,x+4,175,18);rect(x-2,169,x+2,174,25);rect(x-1,169,x+1,172,11)
 poly([(x-5,167),(x,163),(x+5,167)],18);dot(x,162,24)
 line(x-3,176,x+3,176,23)
# Enforce the 8x8 tile budget by nearest palette mapping if needed.
max_tile=0
for ty in range(0,H,8):
 for tx in range(0,W,8):
  counts={}
  for y in range(ty,ty+8):
   for x in range(tx,tx+8):counts[p[y][x]]=counts.get(p[y][x],0)+1
  keep=sorted(counts,key=lambda c:-counts[c])[:16]
  for y in range(ty,ty+8):
   for x in range(tx,tx+8):
    c=p[y][x]
    if c not in keep:p[y][x]=min(keep,key=lambda k:sum((pal[c][i]-pal[k][i])**2 for i in range(3)))
  max_tile=max(max_tile,len(set(p[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8))))
def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
raw=b''.join(b'\0'+bytes(row) for row in p)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+chunk(b'PLTE',b''.join(bytes(c) for c in pal))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
open('output/eiffel_snes.png','wb').write(png)
print('256x224;',len(set(sum(p,[]))),'colors; maximum colors per 8x8 tile:',max_tile)
