import subprocess
W,H=160,200
def c565(r,g,b): return ((r>>3)<<3|r>>5,(g>>2)<<2|g>>6,(b>>3)<<3|b>>5)
img=[[None]*W for _ in range(H)]
for y in range(H):
    t=y/H
    for x in range(W):
        img[y][x]=c565(int(40+150*t),int(60+120*t),int(140+90*t))
import random
random.seed(3)
for _ in range(25):
    x,y=random.randrange(W),random.randrange(100); img[y][x]=c565(255,255,220)
# ground
for y in range(185,H):
    for x in range(W): img[y][x]=c565(60,130+(y%2)*10,60)
for y in range(180,185):
    for x in range(W): img[y][x]=c565(90,90,100)
top,base=15,185
def hw(y):
    t=(y-top)/(base-top); return 1+44*t**2.3
iron=c565(90,60,40); light=c565(150,100,60); dark=c565(50,35,30)
for y in range(top,base):
    w=hw(y); cx=80
    t=(y-top)/(base-top)
    for x in range(W):
        d=abs(x-cx+0.5)
        if d>w: continue
        edge=d>w-2.2
        inner=w*0.45 if t>0.5 else 0
        # arch at base
        arch = t>0.82 and d<w*0.6 and (y-(base-14))>-((w*0.6)**2-d*d)**.5*0.5-0+ -4 and d<w*0.62 and y>base-16+ (d/(w*0.6))**2*10
        plat = y in (95,96,140,141) and d<w+2
        if plat: img[y][x]=light if y%2 else dark; continue
        if arch: continue
        if edge: img[y][x]=iron if x<cx else light; continue
        if t<0.12: img[y][x]=iron; continue
        # lattice
        k=int(8-6*t) if False else 6
        if ((x+y)%k==0 or (x-y)%k==0): img[y][x]=dark if (x+y)%2 else iron
for x in range(80-3,80+3):
    for y in range(6,top): img[y][x if y>9 else 80]=iron if y<top else iron
for y in range(3,top): img[y][79]=img[y][80]=dark
# platform extra width
for y in (95,96,140,141):
    for x in range(W):
        if abs(x-79.5)<=hw(y)+2: img[y][x]=light if y%2 else dark
open('o.ppm','wb').write(b'P6 %d %d 255\n'%(W,H)+bytes(v for r in img for p in r for v in p))
subprocess.run('ffmpeg -y -loglevel error -i o.ppm -vf scale=640:800:flags=neighbor -q:v 2 output/eiffel_tower_pixel.jpg && rm o.ppm',shell=True)
