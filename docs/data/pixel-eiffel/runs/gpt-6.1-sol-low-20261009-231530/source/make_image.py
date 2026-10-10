import math, random, subprocess, os
random.seed(23)
W,H=320,400
pix=[[(0,0,0) for x in range(W)] for y in range(H)]
def color(h):return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rect(x,y,w,h,c):
 c=color(c) if isinstance(c,str) else c
 for yy in range(max(0,int(y)),min(H,int(y+h))):
  for xx in range(max(0,int(x)),min(W,int(x+w))):pix[yy][xx]=c
def poly(points,c):
 for y in range(max(0,int(min(p[1] for p in points))),min(H,int(max(p[1] for p in points))+1)):
  xs=[]
  for a,b in zip(points,points[1:]+points[:1]):
   if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):xs.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):rect(math.ceil(a),y,int(b)-math.ceil(a)+1,1,c)
def line(x1,y1,x2,y2,c,width=1):
 n=max(abs(x2-x1),abs(y2-y1))
 for i in range(int(n)+1):
  t=i/max(1,n);rect(round(x1+(x2-x1)*t)-width//2,round(y1+(y2-y1)*t)-width//2,width,width,c)
def disk(x,y,r,c):
 for yy in range(y-r,y+r+1):
  dx=int(math.sqrt(max(0,r*r-(yy-y)**2)));rect(x-dx,yy,2*dx+1,1,c)
# Deliberately stepped palette: the aesthetic of a 16-bit console background.
sky=['292d59','35365f','48406b','614a74','855773','a96376','cb7779','e58d83','f0a28a','f5b98e','f8cc9c']
for y in range(302):rect(0,y,W,1,sky[min(10,y//28)])
# A huge, pixel-stepped sun.
disk(236,181,39,'ffd69a');disk(236,181,31,'ffdda7')
for y in (157,178,201,212):rect(193,y,88,2,'f5b98e')
for x,y,w in [(15,72,49),(38,80,62),(234,51,50),(218,58,73),(5,139,65),(260,119,55)]:
 rect(x,y,w,3,'ad7186');rect(x+8,y-3,w-16,3,'ad7186');rect(x+14,y+3,w-20,2,'c98389')
for x,y in [(28,31),(79,48),(121,22),(202,34),(283,29),(301,85)]:rect(x,y,1,1,'e7b99f')
# Distant Paris roofline.
rect(0,286,320,37,'9b777f')
for x in range(0,320,13):
 h=random.randint(9,30);rect(x,290-h,12,h+20,'8b707e');poly([(x-1,290-h),(x+6,284-h),(x+13,290-h)],'75677b')
 for yy in range(294-h,291,7):
  for xx in range(x+3,x+11,5):rect(xx,yy,2,3,'dc9c88')
rect(0,311,320,8,'ba8c87')
rect(0,319,320,81,'48475b')
# Riverside quay and foreground promenade.
rect(0,328,320,24,'645366')
for y in range(332,352,4):
 for i in range(12):rect(random.randrange(320),y,random.randrange(3,18),1,random.choice(['956f78','c98f81','48475b']))
rect(0,353,320,5,'dfab91');rect(0,358,320,42,'665362')
for y in [367,382,397]:line(0,y,319,y,'79616a')
for x in range(-30,350,35):line(x,358,x+40,399,'79616a')
# Tower. All structure is constructed as pixels, not a vector resampling.
dark='353345'; edge='6c4954';gold='e9ac79';light='ffd096'
# Antenna, lantern, upper tapered shaft.
line(160,39,160,65,dark,2);rect(159,39,2,5,light)
rect(156,62,9,8,dark);rect(158,64,5,4,gold)
poly([(157,70),(163,70),(169,154),(151,154)],dark)
line(158,73,152,151,gold);line(162,73,168,151,edge)
for y in range(79,149,9):
 half=2+(y-70)*.08;line(int(160-half),y,int(160+half),y+8,gold)
rect(148,150,25,5,dark);rect(150,150,21,1,light)
# Second tier, open iron truss.
poly([(151,155),(169,155),(186,229),(174,229),(163,162),(157,162),(146,229),(134,229)],dark)
line(152,157,137,226,gold,2);line(167,157,182,226,edge,2)
for y in range(164,225,12):
 left=int(151-(y-155)*.23);right=320-left
 line(left,y,right,y,gold)
 line(left,y,right+3,y+12,edge)
 line(right,y,left-3,y+12,gold)
rect(130,225,61,8,dark);rect(131,225,58,2,light);rect(133,230,54,1,edge)
# Broad legs and first observation deck.
poly([(135,233),(148,233),(134,275),(117,275),(94,326),(73,326),(112,273)],dark)
poly([(172,233),(185,233),(208,273),(247,326),(226,326),(203,275),(186,275)],dark)
line(136,235,115,276,gold,2);line(184,235,205,276,gold,2)
line(115,278,79,322,gold,2);line(204,278,240,322,edge,2)
# Diagonal girders on each leg.
for a,b,c,d in [(132,242,142,252),(126,253,138,266),(119,265,130,273),(107,284,119,296),(99,296,111,306),(89,309,100,320)]:
 line(a,b,c,d,gold);line(c,b,a,d,edge)
 line(320-a,b,320-c,d,gold);line(320-c,b,320-a,d,edge)
rect(108,271,104,9,dark);rect(106,271,108,2,light);rect(110,276,100,2,edge)
for x in range(111,210,5):rect(x,273,2,3,gold)
# The signature curved arch between the four feet.
outer=[];inner=[]
for x in range(98,223):
 t=(x-160)/62
 yy=322-36*math.sqrt(max(0,1-t*t))
 outer.append((x,yy));inner.append((x,yy+5))
poly(outer+inner[::-1],dark)
for x,y in outer[::2]:rect(x,int(y),2,1,gold)
rect(72,324,27,4,dark);rect(221,324,28,4,dark)
# Ground shadows and trees framing the architecture.
for x,y,w in [(65,330,46),(209,330,50)]:rect(x,y,w,2,'343747')
for x,y,r in [(7,285,25),(27,302,22),(304,286,24),(283,304,19)]:
 rect(x-2,y,4,38,'353345');disk(x,y,r,'353e50');disk(x-5,y-7,r-6,'465264')
 for i in range(20):
  xx=x+random.randrange(-r,r);yy=y+random.randrange(-r,r)
  if (xx-x)**2+(yy-y)**2<r*r:rect(xx,yy,3,2,'62606b')
# Ornamental lamps on the quay.
for x in [35,285]:
 line(x,313,x,355,dark,2);rect(x-4,354,9,2,dark);rect(x-4,312,9,3,dark)
 rect(x-3,304,7,8,'f4bf8b');rect(x-2,305,4,5,'ffdda7');poly([(x-5,304),(x,299),(x+5,304)],dark)
# A few tiny pedestrians anchor the immense scale.
for x,y in [(132,342),(142,345),(194,345),(201,344)]:
 rect(x,y-7,3,3,'edb697');rect(x-1,y-4,5,6,'353345');line(x,y+2,x-1,y+7,dark);line(x+2,y+2,x+3,y+7,dark)
# Foreground flowers, pixel highlights.
for x in range(0,320):
 if random.random()<.25:rect(x,random.randint(391,399),2,2,random.choice(['b47a7a','dfad89','363c50']))
with open('render.ppm','wb') as f:
 f.write(('P6\n%d %d\n255\n'%(W,H)).encode());f.write(bytes(v for row in pix for p in row for v in p))
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','render.ppm','-vf','scale=960:1200:flags=neighbor','-q:v','1','output/eiffel_16bit.jpg'],check=True)
os.remove('render.ppm')
