import math, random, subprocess, os
random.seed(19)
W,H=384,480
pix=bytearray(W*H*3)
def rgb(c): return tuple(int(c[i:i+2],16) for i in (0,2,4))
def rect(x,y,w,h,c):
 c=rgb(c) if isinstance(c,str) else c
 for yy in range(max(0,int(y)),min(H,int(y+h))):
  a=(yy*W+max(0,int(x)))*3;b=(yy*W+min(W,int(x+w)))*3
  if b>a: pix[a:b]=bytes(c)*((b-a)//3)
def poly(points,c):
 for y in range(max(0,int(min(p[1] for p in points))),min(H,int(max(p[1] for p in points))+1)):
  xs=[]
  for (x1,y1),(x2,y2) in zip(points,points[1:]+points[:1]):
   if (y1<=y<y2) or (y2<=y<y1):xs.append(x1+(y-y1)*(x2-x1)/(y2-y1))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):rect(math.ceil(a),y,math.floor(b)-math.ceil(a)+1,1,c)
def line(x1,y1,x2,y2,c,t=1):
 n=int(max(abs(x2-x1),abs(y2-y1)))
 for i in range(n+1):
  f=i/max(1,n);rect(round(x1+(x2-x1)*f)-t//2,round(y1+(y2-y1)*f)-t//2,t,t,c)
def ellipse(x,y,rx,ry,c):
 for yy in range(-ry,ry+1):
  span=int(rx*math.sqrt(max(0,1-yy*yy/(ry*ry))))
  rect(x-span,y+yy,span*2+1,1,c)
# Restrained, stepped console-era palette.
sky=['33375d','403e68','514571','655079','805a81','9a6688','b8778c','ce8c95','e7a399','f1b69e','f7c79f','f9d5a7']
for y in range(335):rect(0,y,W,1,sky[min(11,y//28)])
# Sparse ordered dithering at the broad color-band transitions.
for k in range(1,12):
 for y in range(k*28-5,k*28+4):
  for x in range(W):
   if (x%4+(y%2)*2)%4 < (y-(k*28-5))//3:rect(x,y,1,1,sky[k])
# Evening stars.
for x,y in [(37,36),(94,62),(296,39),(346,85),(256,78),(65,116),(319,123),(144,30),(219,21)]:
 rect(x,y,1,1,'ffe1b8')
 if y<65:rect(x-1,y,3,1,'dcb8b5');rect(x,y-1,1,3,'dcb8b5');rect(x,y,1,1,'fff0c6')
# Low sun with sliced pixel silhouette.
ellipse(272,203,37,37,'ffdfac')
for y in [218,225,232]:rect(232,y,80,2,sky[min(11,y//28)])
# Long horizontal clouds.
for x,y,w in [(18,141,107),(248,108,123),(-12,196,105),(295,260,107),(76,92,59)]:
 poly([(x,y+6),(x+10,y+6),(x+10,y+3),(x+24,y+3),(x+24,y),(x+w-22,y),(x+w-22,y+3),(x+w-7,y+3),(x+w-7,y+5),(x+w,y+5),(x+w,y+9),(x,y+9)],'ad798e' if y>120 else '786083')
 rect(x+16,y+9,w-23,2,'d298a0' if y>120 else '966e91')
# Distant roofs and Parisian blocks.
for layer,base,col in [(0,326,'ad8792'),(1,342,'836f85'),(2,355,'605c77')]:
 x=-8
 while x<W:
  w=random.randint(12,29);h=random.randint(14,42)
  rect(x,base-h,w,h,col)
  poly([(x-2,base-h),(x+3,base-h-7),(x+w-4,base-h-7),(x+w+1,base-h)],col)
  rect(x+3,base-h-11,3,7,col)
  if layer>0:
   for yy in range(base-h+5,base-3,7):
    for xx in range(x+3,x+w-2,6):
     rect(xx,yy,2,3,random.choice(['c8a09e','eac098',col,col]))
  x+=w+2
# Small distant dome.
ellipse(69,299,13,11,'826d83');rect(56,299,27,22,'826d83');rect(67,282,3,10,'826d83');rect(62,313,3,9,'c39b99');rect(73,313,3,9,'c39b99')
# River banks and water.
rect(0,350,W,130,'595e7b');rect(0,350,W,6,'363f5d');rect(0,356,W,3,'c99b94')
for y in range(363,451,5):
 for j in range(9):
  x=random.randrange(W);w=random.randint(3,27)
  rect(x,y,w,random.choice([1,1,2]),random.choice(['6e718b','827c94','a28b9c','454e70']))
for y in range(364,445,4):
 span=int((450-y)*.30)
 for j in range(4):
  x=272+random.randint(-span-10,span+10)
  rect(x,y,random.randint(3,14),1,random.choice(['d3a59f','e7b69e','b18e9c']))
# The tower: carefully tapered open ironwork, warm edge lighting.
D='37344f'; M='655066'; L='ba827e'; G='e3ac88'
# Spire and top observatory.
line(192,58,192,86,D,2);rect(191,56,2,3,G);rect(190,77,4,10,D)
poly([(190,83),(194,83),(198,127),(186,127)],D)
line(191,85,189,117,G);line(193,87,195,117,M)
rect(184,117,16,4,D);rect(185,117,14,1,G);rect(183,121,18,3,D)
rect(187,124,10,7,M);rect(189,124,2,5,'f7ce9f');rect(193,124,2,5,'f7ce9f')
# Upper shaft, open sides and crossed girders.
poly([(187,131),(192,131),(178,226),(169,226)],D)
poly([(192,131),(197,131),(215,226),(206,226)],D)
line(187,132,170,226,L,2);line(195,132,212,226,M,2)
for y in range(137,223,11):
 t=(y-131)/95;a=188-16*t;b=196+16*t
 t2=(y+11-131)/95;a2=188-16*t2;b2=196+16*t2
 line(a,y,b2,y+11,M,2);line(b,y,a2,y+11,D,2);line(a,y,b,y,D)
 rect(int(a),y,int(b-a)+1,1,L)
# Second deck.
rect(163,223,58,5,D);rect(166,222,52,1,G);rect(160,228,64,5,D);rect(163,228,58,1,L)
for x in range(165,221,5):rect(x,224,2,3,'a97677')
# Splayed legs from second to first deck.
poly([(170,233),(180,233),(163,281),(143,281)],D)
poly([(204,233),(214,233),(241,281),(221,281)],D)
line(170,234,144,280,G,2);line(179,234,162,280,L,2)
line(205,234,222,280,L,2);line(213,234,239,280,M,2)
for y in range(236,280,9):
 t=(y-233)/48;t2=(y+9-233)/48
 a=170-27*t;b=180-17*t;a2=170-27*t2;b2=180-17*t2
 line(a,y,b2,y+9,L);line(b,y,a2,y+9,L)
 line(384-a,y,384-b2,y+9,L);line(384-b,y,384-a2,y+9,M)
 line(b,y,384-b,y,D,2)
 line(b,y,384-b2,y+9,M);line(384-b,y,b2,y+9,M)
# Broad first-floor promenade.
rect(137,280,110,4,D);rect(138,280,108,1,G)
rect(135,284,114,7,D)
for x in range(139,246,5):rect(x,285,2,3,L)
rect(132,291,120,3,D);rect(134,291,116,1,G)
# Four massive lower supports and the monumental curved arch.
poly([(145,294),(165,294),(151,318),(131,348),(111,348)],D)
poly([(219,294),(239,294),(273,348),(253,348),(233,318)],D)
# Arch as a stepped band following an ellipse; sky is preserved inside.
for x in range(146,239):
 u=(x-192)/47
 arch_y=335-36*math.sqrt(max(0,1-u*u))
 poly([(x,294),(x+1,294),(x+1,int(arch_y)+4),(x,int(arch_y)+4)],D)
 rect(x,int(arch_y)+2,1,2,L)
line(145,296,112,347,G,2);line(164,296,130,347,L,2)
line(221,296,254,347,L,2);line(239,296,272,347,M,2)
for y in range(299,345,10):
 a=145-(y-294)*.64;b=165-(y-294)*.66
 line(a,y,b-7,y+10,L);line(b,y,a-7,y+10,L)
 line(384-a,y,384-b+7,y+10,M);line(384-b,y,384-a+7,y+10,L)
rect(106,346,30,5,D);rect(248,346,30,5,D);rect(108,346,26,1,G);rect(250,346,26,1,G)
# Pinpoint lamps on decks.
for y,a,b in [(282,139,247),(225,165,220)]:
 for x in range(a,b,8):rect(x,y,1,1,'ffe0a3')
# Broken tower reflection.
for y in range(361,431,4):
 spread=int(39-(y-361)*.38)
 for j in range(5):
  x=192+random.randint(-spread,spread)
  rect(x,y,random.randint(3,10),2,random.choice([D,M,'a98288']))
# Foreground embankment on diagonal, cobblestone edging.
poly([(0,420),(384,450),(384,480),(0,480)],'2b304a')
line(0,420,384,450,'c99c99',3);line(0,424,384,454,'6e627a',2)
for x in range(0,384,13):line(x,423+x*.078,x-3,428+x*.078,'373951')
for y in range(442,480,9):
 for x in range((y%2)*8,384,19):rect(x,y,12,1,'3c3c56')
# Wrought iron riverside railing.
line(0,405,384,435,'30344f',3);line(0,411,384,441,'30344f',1)
for x in range(3,384,17):line(x,405+x*.078,x,420+x*.078,'30344f',2)
# Framing chestnut leaves in upper corners.
for side in [0,1]:
 line(-8 if side==0 else 390,15,29 if side==0 else 364,73,'2b304a',4)
 for i in range(92):
  x=random.randrange(0,65);y=random.randrange(0,89)
  if x/65+y/95>1.16:continue
  if side:x=383-x;y-=15
  rect(x,y,random.randrange(3,10),random.randrange(2,7),random.choice(['2b304a','333951','42425c']))
# Two antique lamps.
def lamp(x,y):
 line(x,y+4,x,y+96,'262c43',3);rect(x-5,y+94,11,4,'262c43');rect(x-3,y+88,7,6,'262c43')
 poly([(x-6,y-2),(x+6,y-2),(x+4,y+14),(x-4,y+14)],'292c45')
 poly([(x-4,y),(x+4,y),(x+2,y+11),(x-2,y+11)],'f5c78e')
 rect(x-1,y,2,11,'ffe6af');rect(x-7,y-4,15,3,'292c45')
 poly([(x-7,y-4),(x,y-11),(x+7,y-4)],'292c45');rect(x,y-14,1,4,'e3ac88')
lamp(34,328);lamp(345,351)
# A pair of tiny figures on the promenade.
for x,y in [(292,451),(304,452)]:
 rect(x,y-12,4,4,'252b43');rect(x-1,y-8,6,9,'252b43');line(x,y,x-1,y+8,'252b43',2);line(x+3,y,x+4,y+8,'252b43',2)
line(295,449,303,450,'252b43',1)
# Pixel-aligned framing.
rect(0,0,W,3,'252b43');rect(0,H-3,W,3,'252b43');rect(0,0,3,H,'252b43');rect(W-3,0,3,H,'252b43')
with open('scene.ppm','wb') as f:f.write(('P6\n%d %d\n255\n'%(W,H)).encode()+pix)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','scene.ppm','-vf','scale=1152:1440:flags=neighbor','-q:v','1','-pix_fmt','yuvj444p','output/eiffel-tower.jpg'],check=True)
os.remove('scene.ppm')
