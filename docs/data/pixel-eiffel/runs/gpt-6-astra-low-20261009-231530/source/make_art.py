import math, random, subprocess, os
random.seed(18)
W,H=320,400
pix=[[(0,0,0) for x in range(W)] for y in range(H)]
def rgb(h):
 c=tuple(int(h[i:i+2],16) for i in (0,2,4))
 # RGB565 palette: classic 16-bit colour
 return (round(round(c[0]*31/255)*255/31),round(round(c[1]*63/255)*255/63),round(round(c[2]*31/255)*255/31))
def put(x,y,c):
 if 0<=x<W and 0<=y<H: pix[y][x]=c
def rect(x,y,w,h,c):
 for yy in range(max(0,y),min(H,y+h)):
  for xx in range(max(0,x),min(W,x+w)):pix[yy][xx]=c
def poly(p,c):
 for y in range(max(0,min(t[1] for t in p)),min(H,max(t[1] for t in p)+1)):
  hits=[]
  for a,b in zip(p,p[1:]+p[:1]):
   if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):hits.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
  hits.sort()
  for i in range(0,len(hits)-1,2):rect(math.ceil(hits[i]),y,int(hits[i+1])-math.ceil(hits[i])+1,1,c)
def line(x,y,xx,yy,c,w=1):
 n=max(abs(xx-x),abs(yy-y),1)
 for i in range(n+1):rect(round(x+(xx-x)*i/n)-w//2,round(y+(yy-y)*i/n)-w//2,w,w,c)
def disc(x,y,r,c):
 for j in range(-r,r+1):
  dx=int(math.sqrt(r*r-j*j));rect(x-dx,y+j,dx*2+1,1,c)
sky=[rgb(c) for c in ['555881','71618e','946e9d','b77eaa','d78fae','efa6ac','ffc1ae','ffd4aa']]
for y in range(H):
 s=min(7,y*8//285)
 for x in range(W):
  z=s
  if s<7 and y%36>28 and (x%2)*2+y%2<(y%36-28)//2:z=s+1
  pix[y][x]=sky[z]
sun=rgb('ffdfad');disc(231,137,37,sun)
# Soft horizontal cloud pixels
for x,y,w in [(12,73,55),(27,69,27),(55,88,39),(218,55,53),(233,51,22),(261,94,45),(9,158,54),(29,154,21),(222,177,80)]:
 rect(x,y,w,3,rgb('e9a2b2'))
 rect(x+7,y+3,max(5,w-19),2,rgb('d991ae'))
# Distant city blocks
far=rgb('a386a0'); roof=rgb('887794')
for x in range(0,W,9):
 h=random.randrange(9,30);rect(x,278-h,8,h,far)
 if random.random()<.5:rect(x+2,276-h,4,2,far)
for x in range(0,W,18):
 h=random.randrange(12,28);rect(x,290-h,17,h,roof)
 poly([(x,290-h),(x+4,284-h),(x+12,284-h),(x+17,290-h)],roof)
 for xx in range(x+3,x+16,5):
  for yy in range(294-h,286,6):rect(xx,yy,2,3,rgb('d6a0a7'))
# River and opposite embankment
rect(0,289,W,9,rgb('665c7e'));rect(0,298,W,53,rgb('7e7b9b'))
rect(0,298,W,2,rgb('f0b5ae'))
for i in range(190):
 x=random.randrange(W);y=random.randrange(302,348)
 rect(x,y,random.randrange(2,15),1,random.choice([rgb('b496af'),rgb('e4acb0'),rgb('676987')]))
# Bridge behind tower
rect(0,310,320,4,rgb('645874'));rect(0,314,320,3,rgb('bc939d'))
for x in range(0,320,43):
 poly([(x,316),(x+5,316),(x+9,333),(x+3,333)],rgb('655974'))
for x in range(0,320,8):rect(x,305,1,5,rgb('665975'))
rect(0,304,320,1,rgb('e7b4ab'))
background=[row[:] for row in pix]
# Eiffel ironwork: silhouettes and bright west-facing riveted girders
ink=rgb('34364f');metal=rgb('65506b');light=rgb('dc987f');mid=rgb('a16e78');dark=rgb('43405b')
# tower legs and narrow upper shaft
poly([(156,91),(164,91),(171,161),(182,220),(196,260),(224,310),(207,312),(176,268),(165,233),(155,233),(143,268),(112,312),(95,310),(124,260),(138,220),(149,161)],ink)
# Open central space below upper platform, then arch between feet
poly([(152,175),(168,175),(176,220),(144,220)],sky[5])
poly([(144,233),(176,233),(183,255),(137,255)],sky[6])
# Open arch; the curved underside is stepped at native pixel resolution.
for y in range(269,314):
 dx=int(39*math.sqrt(max(0,1-((311-y)/43)**2)))
 for x in range(160-dx,161+dx):put(x,y,background[y][x])

# Structural lattice, tier by tier
for ya,yb,la,lb,ra,rb in [(105,124,156,154,164,166),(124,143,154,152,166,168),(143,163,152,149,168,171),(176,197,149,144,171,176),(197,218,144,139,176,181),(233,253,140,133,180,187)]:
 line(la,ya,rb,yb,mid);line(ra,ya,lb,yb,metal)
 line(la,ya,lb,yb,light);line(ra,ya,rb,yb,mid)
 line(lb,yb,rb,yb,ink,2)
# Slanted leg lattice panels
for side in [-1,1]:
 for ya,yb,oa,ob,ia,ib in [(260,276,36,45,22,29),(276,291,45,54,29,39),(291,307,54,64,39,49)]:
  a=160+side*oa;b=160+side*ob;c=160+side*ia;d=160+side*ib
  line(a,ya,d,yb,light);line(c,ya,b,yb,mid)
  line(a,ya,b,yb,light,2);line(c,ya,d,yb,metal,2)
  line(b,yb,d,yb,ink,2)
# Continuous bowed outlines
for p in [[(158,96),(151,160),(139,218),(124,262),(98,307)],[(163,96),(170,160),(181,218),(196,262),(222,307)]]:
 for a,b in zip(p,p[1:]):line(*a,*b,light)
# Antenna, observation capsule, decks
rect(159,65,2,26,ink);rect(158,74,4,2,light)
rect(157,86,6,9,ink);rect(155,94,10,5,ink);rect(156,94,8,1,light)
for x,y,w in [(147,164,26),(134,220,52),(123,257,74)]:
 rect(x,y,w,7,ink);rect(x-2,y,w+4,2,light);rect(x+1,y+4,w-2,1,mid)
 for xx in range(x+3,x+w-2,5):rect(xx,y+2,1,2,rgb('efb08c'))
rect(93,309,21,5,ink);rect(206,309,22,5,ink)
# Foreground park, paths, and clipped trees
poly([(0,350),(320,341),(320,400),(0,400)],rgb('383f5a'))
poly([(126,400),(153,353),(178,351),(218,400)],rgb('a88291'))
poly([(151,400),(161,355),(167,355),(185,400)],rgb('d4a09c'))
rect(0,349,320,3,rgb('e0ac9f'))
rect(0,352,320,3,rgb('554861'))
for x in list(range(-5,87,15))+list(range(248,330,15)):
 y=random.randrange(320,336)
 rect(x-2,y,4,35,ink)
 for dx,dy,r in [(0,0,13),(-9,8,10),(10,8,10),(0,13,14)]:disc(x+dx,y+dy,r,rgb('3d495f'))
 for dx,dy,r in [(-5,-4,7),(-10,5,6),(4,0,7)]:disc(x+dx,y+dy,r,rgb('5b6174'))
 rect(x-9,y-6,6,2,rgb('85798b'))
for x in [33,86,236,288]:
 line(x,339,x,375,ink,2);rect(x-4,334,9,3,ink)
 rect(x-3,337,7,7,rgb('f8c39c'));rect(x-1,338,3,5,rgb('ffe3b5'))
 rect(x-4,344,9,2,ink);rect(x-3,374,7,3,ink)
# Small strolling figures
for x,y in [(140,374),(146,376),(189,382)]:
 rect(x,y,3,3,ink);rect(x-1,y+3,5,6,ink)
 line(x,y+8,x-1,y+12,ink);line(x+2,y+8,x+3,y+12,ink)
# Scattered foliage catching dusk
for i in range(100):
 x=random.randrange(W);y=random.randrange(362,400)
 if x<119 or x>221:rect(x,y,random.randrange(1,4),1,random.choice([rgb('56576b'),rgb('756376')]))
# Fine inset pixel border
border=rgb('ffcfaa')
rect(8,8,304,1,border);rect(8,391,304,1,border)
rect(8,8,1,384,border);rect(311,8,1,384,border)
with open('scene.ppm','wb') as f:
 f.write(f'P6\n{W} {H}\n255\n'.encode());f.write(bytes(v for row in pix for c in row for v in c))
subprocess.run(['ffmpeg','-v','error','-y','-i','scene.ppm','-vf','scale=960:1200:flags=neighbor','-q:v','1','-pix_fmt','yuvj444p','output/eiffel-pixel.jpg'],check=True)
os.remove('scene.ppm')
