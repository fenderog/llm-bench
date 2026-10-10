import math, random, struct, zlib, os
random.seed(16)
W,H=256,224
# A hand-picked 16-bit-era palette, from twilight lilacs to warm brass.
colors=[
'#22243e','#33304e','#47395e','#5c446f','#71517d','#8b618c','#a77798','#bf8da5','#dba4ad','#efb9b1','#f5ccc0',
'#f9dcc5','#ffe6be','#ffc98e','#f2a66f','#da805c','#b96151','#91494b','#703d49',
'#191f32','#26334a','#33485a','#476071','#607787','#829298','#acaca3',
'#192f39','#254448','#38605a','#57786b','#85957a',
'#423842','#66504c','#8c6954','#b68c62','#ddb477','#ffda96',
'#374459','#4d586e','#697184','#89909a','#b1b1ad',
'#754d66','#9a667c','#c38791','#e6a499', '#d5bc91','#eee0b8']
pal=[tuple(bytes.fromhex(c[1:])) for c in colors]
pix=[[0]*W for _ in range(H)]
def dot(x,y,c):
 x,y=int(x),int(y)
 if 0<=x<W and 0<=y<H:pix[y][x]=c
def rect(x0,y0,x1,y1,c):
 for y in range(max(0,int(y0)),min(H,int(y1)+1)):
  for x in range(max(0,int(x0)),min(W,int(x1)+1)):pix[y][x]=c
def line(x0,y0,x1,y1,c,w=1):
 x0,y0,x1,y1=map(round,(x0,y0,x1,y1)); dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
 while True:
  rect(x0-(w-1)//2,y0-(w-1)//2,x0+w//2,y0+w//2,c)
  if x0==x1 and y0==y1:break
  e=2*err
  if e>=dy:err+=dy;x0+=sx
  if e<=dx:err+=dx;y0+=sy

def poly(points,c):
 for y in range(max(0,math.ceil(min(p[1] for p in points))),min(H,math.ceil(max(p[1] for p in points))+1)):
  cross=[]
  for a,b in zip(points,points[1:]+points[:1]):
   if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):cross.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
  cross.sort()
  for a,b in zip(cross[::2],cross[1::2]):rect(math.ceil(a),y,math.floor(b),y,c)
def ellipse(cx,cy,rx,ry,c):
 for y in range(int(cy-ry),int(cy+ry)+1):
  v=1-((y-cy)/ry)**2
  if v>=0:
   dx=int(rx*math.sqrt(v));rect(cx-dx,y,cx+dx,y,c)
# Sky: clean bands with restrained ordered-dither transitions.
bands=[(0,19,3),(20,37,4),(38,55,5),(56,73,6),(74,91,7),(92,110,8),(111,130,9),(131,158,10),(159,181,11)]
for a,b,c in bands:rect(0,a,255,b,c)
for a,b,c in bands[1:]:
 for y in range(a,a+4):
  for x in range(W):
   if (x+2*y)%4>y-a:dot(x,y,c-1)
# Broad sculpted clouds with stepped, not antialiased, edges.
def cloud(points,base,light):
 poly(points,base)
 for a,b,y in light:rect(a,y,b,y+1,base+1)
cloud([(0,31),(14,31),(14,28),(34,28),(34,30),(49,30),(49,33),(64,33),(64,37),(79,37),(79,40),(67,40),(67,43),(38,43),(38,41),(16,41),(16,39),(0,39)],6,[(0,35,33),(22,47,32),(44,60,36)])
cloud([(174,20),(193,20),(193,17),(212,17),(212,19),(229,19),(229,22),(246,22),(246,25),(256,25),(256,33),(223,33),(223,30),(198,30),(198,27),(177,27)],5,[(197,221,20),(223,244,24),(179,198,24)])
cloud([(0,79),(20,79),(20,75),(40,75),(40,77),(51,77),(51,81),(76,81),(76,84),(93,84),(93,87),(61,87),(61,89),(32,89),(32,86),(0,86)],9,[(0,25,81),(29,49,79),(50,75,84)])
cloud([(173,64),(188,64),(188,61),(203,61),(203,59),(222,59),(222,62),(239,62),(239,66),(256,66),(256,74),(222,74),(222,77),(191,77),(191,73),(171,73),(171,70),(154,70),(154,67),(173,67)],8,[(192,215,64),(218,237,67),(178,198,70)])
# Sunset disk, a small distant accent to the right of the monument.
ellipse(204,113,16,16,11);ellipse(204,112,14,14,12)
rect(184,117,223,118,9);rect(192,124,219,125,10)
# Slivers of evening cloud.
for x,y,l,c in [(6,109,43,10),(13,111,20,10),(54,116,31,11),(170,99,33,10),(220,102,35,10),(1,132,30,11),(155,128,22,11),(224,136,31,11)]:rect(x,y,x+l,y,c)
# Distant Paris skyline; chimney silhouettes and Mansard roofs.
for x in range(0,256,6):
 h=random.randint(5,17);y=160-h
 rect(x,y,x+6,165,7);rect(x+1,y-2,x+4,y,7)
 if random.random()<.45:rect(x+2,y-5,x+3,y-2,7)
# Dome at the left horizon.
rect(25,143,45,160,6);ellipse(35,143,10,6,6);rect(34,132,36,137,6);line(35,129,35,134,6)
# Neighbourhood on the opposite bank.
for x,width,top in [(0,15,146),(17,18,150),(38,15,143),(56,17,149),(180,16,145),(199,21,149),(222,18,143),(242,14,151)]:
 rect(x,top,x+width,170,39)
 poly([(x-2,top),(x+3,top-5),(x+width-3,top-5),(x+width+2,top)],38)
 line(x,top,x+width,top,41);rect(x+2,top+2,x+width-2,top+3,40)
 for xx in range(x+3,x+width-1,5):
  for yy in range(top+6,168,6):
   rect(xx,yy,xx+1,yy+2,21);dot(xx,yy,34 if random.random()<.45 else 40)
 rect(x+width-1,top+1,x+width,170,37)
# Riverbank grass and trees, placed behind tower.
rect(0,166,255,176,26)
for x in list(range(0,78,9))+list(range(180,256,9)):
 y=random.randint(157,164);ellipse(x,y,7,7,27);ellipse(x-2,y-2,5,4,28);rect(x-1,y+3,x,172,26)
rect(0,174,255,176,34);rect(0,177,255,179,32)
# Seine's stepped blue-purple ripples.
rect(0,180,255,200,38);rect(0,182,255,187,39);rect(0,193,255,200,37)
for y in range(181,201,2):
 for i in range(12):
  x=random.randrange(256);l=random.randrange(3,17);rect(x,y,x+l,y,random.choice([38,39,40,43]))
for y in range(180,198,3):
 spread=int((y-178)*1.5)
 for i in range(3):
  x=204+random.randint(-spread-4,spread+4);rect(x,y,x+random.randint(3,9),y,random.choice([8,9,34]))
# Tower: a constructed lattice, deliberately preserving the sky in its holes.
C=130
# Antenna and summit cabin.
line(C,16,C,33,32);line(C-1,20,C-1,31,36);dot(C,14,36)
rect(127,31,133,33,32);rect(128,29,132,30,35)
poly([(128,34),(132,34),(136,53),(124,53)],32)
line(129,34,125,51,35);line(131,35,135,51,33)
for y in (38,43,48):line(128,y,133,y,34)
rect(122,51,138,53,19);rect(123,50,137,50,36);rect(124,54,136,55,34)
for x in range(124,138,3):dot(x,52,35)
# Main upper taper. Rings and crossing diagonal braces.
levels=[(56,5),(65,6),(76,8),(88,10),(100,14),(110,18)]
for (ya,wa),(yb,wb) in zip(levels,levels[1:]):
 line(C-wa,ya,C+wb,yb,33);line(C+wa,ya,C-wb,yb,34)
 line(C-wa+1,ya,C+wb-1,yb,35)
 line(C-wa,ya,C+wa,ya,32)
 line(C-wa+1,ya-1,C+wa-1,ya-1,35)
 line(C,ya,C,yb,33)
line(125,55,112,110,19,3);line(125,55,112,110,35)
line(135,55,148,110,19,3);line(134,55,147,110,34)
# Second observation gallery.
rect(108,108,152,110,19);rect(109,107,151,107,36)
rect(110,111,150,114,32);line(111,114,149,114,35)
for x in range(112,150,4):rect(x,110,x+1,112,35)
# Between the two decks: two broad tapering truss walls, cross-braced.
for side in [-1,1]:
 def sx(d):return C+side*d
 poly([(sx(16),115),(sx(21),115),(sx(33),141),(sx(24),141)],32)
 line(sx(17),115,sx(25),140,35,2)
 line(sx(21),115,sx(33),140,19,2)
 line(sx(20),115,sx(31),140,34)
 # Three clear X panels per side.
 for ya,yb,ia,ib,oa,ob in [(116,123,17,19,21,25),(124,132,20,22,25,29),(133,139,23,25,29,32)]:
  line(sx(ia),ya,sx(ob),yb,36);line(sx(oa),ya,sx(ib),yb,19)
  line(sx(ia),ya,sx(oa),ya,34)
# Inner cross members of the central open storey.
line(114,115,151,138,33);line(146,115,109,138,33)
line(115,115,151,137,35);line(145,115,109,137,34)
line(110,130,150,130,32);line(111,129,149,129,34)
# Arch legs: dark iron wedges with recessed openings and gold outer edges.
background=[row[:] for row in pix]
for side in [-1,1]:
 def sx(d):return C+side*d
 points=[(sx(25),144),(sx(34),144),(sx(47),174),(sx(51),179),(sx(33),179),(sx(30),166),(sx(20),151)]
 poly(points,19)
 poly([(sx(27),146),(sx(32),146),(sx(45),177),(sx(36),177),(sx(32),163)],33)
 # A thin triangular glimpse of the sky through each leg.
 hole=[(sx(31),152),(sx(35),163),(sx(39),173),(sx(35),170)]
 mask=[[False]*W for _ in range(H)]
 # Punch the triangular lattice opening from the saved background.
 for yy in range(153,174):
  d0=31+(yy-152)*.30;d1=31+(yy-152)*.40
  for dd in range(math.ceil(d0),math.floor(d1)+1):
   xx=sx(dd)
   if 0<=xx<W:pix[yy][xx]=background[yy][xx]
 line(sx(34),145,sx(48),177,35,2);line(sx(33),145,sx(47),176,36)
 line(sx(25),147,sx(33),177,34)
 for yy,d in [(153,32),(161,36),(170,40)]:
  line(sx(d-3),yy-2,sx(d+3),yy+3,19)
  line(sx(d-3),yy-3,sx(d+3),yy+2,35)
 # Stone footings.
 rect(min(sx(52),sx(32)),178,max(sx(52),sx(32)),180,32)
 rect(min(sx(53),sx(31)),181,max(sx(53),sx(31)),182,25)
# The iconic curved arch follows a segmented pixel arc.
arch=[(105,172),(108,163),(112,156),(117,152),(123,149),(130,148),(137,149),(143,152),(148,156),(152,163),(155,172)]
for a,b in zip(arch,arch[1:]):line(*a,*b,32,3);line(a[0],a[1]-1,b[0],b[1]-1,35)
# First gallery with bright cornice, railings and repeating dark windows.
rect(95,139,165,140,19);rect(96,138,164,138,36)
rect(98,141,162,145,32)
for x in range(99,162,4):rect(x,141,x+1,143,35);dot(x,144,19)
rect(96,146,164,147,19);rect(99,145,161,145,36)
# Far bank lamps & tiny figures establish the scale.
for x in [64,188]:
 line(x,164,x,175,19);rect(x-2,162,x+2,164,32);dot(x,163,12)
for x in [77,174,181]:
 dot(x,173,19);line(x,174,x,177,19)
# Small boat on the river.
poly([(35,190),(62,190),(57,194),(40,194)],19);line(38,190,60,190,34)
rect(43,185,55,189,40);rect(45,184,52,184,46);rect(45,186,48,188,21);rect(50,186,53,188,21)
line(31,195,59,195,40)
# Foreground embankment and stone promenade.
poly([(0,201),(256,196),(256,224),(0,224)],20)
line(0,201,255,196,41,2);line(0,204,255,199,32,2)
poly([(0,209),(256,203),(256,224),(0,224)],37)
# Perspective paving joints.
for a,b in [(211,207),(219,214)]:line(0,a,255,b,38)
for x in range(-40,290,27):line(x,224,128+(x-128)*.72,207,20)
for x in range(8,256,29):line(x,213,x+13,213,39)
# Wrought iron river railing, behind foreground plants.
line(0,195,255,190,19,2);line(0,202,255,197,19)
for x in range(0,256,8):
 y=195-round(x*5/255);line(x,y,x,y+8,19);dot(x,y-1,34)
# Foreground ornate streetlight, balanced against the tower.
def lamp(x,y):
 rect(x-3,y+46,x+3,y+48,19);rect(x-2,y+43,x+2,y+46,19)
 line(x,y+13,x,y+44,19,3);line(x-1,y+16,x-1,y+40,34)
 rect(x-4,y+4,x+4,y+12,19)
 rect(x-2,y+5,x+2,y+10,13);rect(x-1,y+5,x+1,y+9,12)
 line(x,y+4,x,y+12,34);rect(x-5,y+3,x+5,y+4,19)
 poly([(x-5,y+3),(x,y-1),(x+5,y+3)],19);dot(x,y-3,19)
 rect(x-3,y+13,x+3,y+14,19)
lamp(25,161);lamp(234,153)
# Dark corner foliage with small controlled highlight clusters.
for x,y,rx,ry in [(0,213,18,13),(12,224,23,13),(251,219,21,14),(241,228,26,13)]:
 ellipse(x,y,rx,ry,19)
 for i in range(18):
  xx=x+random.randint(-rx,rx);yy=y+random.randint(-ry,0)
  if 0<=xx<W and 0<=yy<H and pix[yy][xx]==19:
   rect(xx,yy,xx+2,yy+1,26);dot(xx,yy,27)
# Guarantee the SNES 4bpp tile rule by merging least-used excess shades
# only inside tiles that need it (typically overlapping foreground details).
changed=0
for ty in range(0,H,8):
 for tx in range(0,W,8):
  counts={}
  for yy in range(ty,ty+8):
   for xx in range(tx,tx+8):counts[pix[yy][xx]]=counts.get(pix[yy][xx],0)+1
  while len(counts)>16:
   src=min(counts,key=lambda c:counts[c]);dst=min((c for c in counts if c!=src),key=lambda c:sum((pal[c][i]-pal[src][i])**2 for i in range(3)))
   for yy in range(ty,ty+8):
    for xx in range(tx,tx+8):
     if pix[yy][xx]==src:pix[yy][xx]=dst;changed+=1
   counts[dst]+=counts.pop(src)
os.makedirs('output',exist_ok=True)
def chunk(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
raw=b''.join(b'\0'+bytes(row) for row in pix)
data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+chunk(b'PLTE',b''.join(bytes(c) for c in pal))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
with open('output/eiffel_twilight.png','wb') as f:f.write(data)
used=set(v for row in pix for v in row)
max_tile=max(len({pix[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)}) for ty in range(0,H,8) for tx in range(0,W,8))
print('256 x 224 |',len(used),'colors | max',max_tile,'colors / 8x8 tile |',changed,'pixels palette-consolidated |',len(data),'bytes')
