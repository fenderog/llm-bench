import subprocess, math
W,H=128,160; cx=64; top=10; base=146
def q565(c):
    r,g,b=[max(0,min(255,int(v))) for v in c]
    r5,g6,b5=r>>3,g>>2,b>>3
    return ((r5<<3)|(r5>>2),(g6<<2)|(g6>>4),(b5<<3)|(b5>>2))
img=[[None]*W for _ in range(H)]
for y in range(H):
    t=y/H
    for x in range(W):
        c=(255*(0.25+0.7*t)+0, 120+110*t, 220+30*t-40*t*t)
        img[y][x]=c
# sun & clouds
for y in range(H):
    for x in range(W):
        d=math.hypot(x-98,y-40)
        if d<9: img[y][x]=(255,235,150)
        elif d<12: img[y][x]=(255,200,170)
for (px,py) in [(20,30),(30,60),(105,75)]:
    for dx in range(-9,10):
        for dy in range(-3,4):
            if (dx/9)**2+(dy/3)**2<1 and (dx+dy*3+px)%7!=0: img[py+dy][px+dx]=(250,245,250)
# ground
for y in range(base,H):
    for x in range(W):
        img[y][x]=(70+((x+y)%3)*6,140-(y-base)*3,60) if y>base else (90,160,70)
# tower
def hw(y):
    t=(y-top)/(base-top); return 0.8+25*t**2.3
plats=[88,112]  # first, second platform rows approx; third near top
plats=[70,104,128]
dark=(70,45,40); mid=(150,100,70); lt=(200,150,100)
for y in range(top,base+1):
    w=hw(y)
    for x in range(cx-int(w)-1,cx+int(w)+2):
        dx=abs(x-cx)
        if dx>w: continue
        t=(y-top)/(base-top)
        # arch cutout
        if y>118:
            ar=hw(base)*0.55; ah=base-118
            if ((dx/ar)**2+((y-base)/ah)**2)<1 and y<base-0: continue
        edge=dx>w-1.6
        lat=((x+y)%5==0) or ((x-y)%5==0)
        if edge: c=dark if x<cx else mid
        elif y>=118 and dx>w*0.0 and False: c=mid
        elif lat or (y%12==0): c=mid
        else: continue
        if y>base-3 : c=dark
        img[y][x]=c
# platforms
for py,ext in [(70,1.5),(104,2.5),(128,3.5)]:
    w=hw(py)+ext
    for y in range(py-1,py+2):
        for x in range(int(cx-w),int(cx+w)+1):
            img[y][x]=lt if y==py-1 else dark
# spire
for y in range(2,top):
    img[y][cx]=dark
img[1][cx]=(255,60,60)
# shading at foot: trees
for x in range(0,W,6):
    for dy in range(4):
        for dx in range(-2,3):
            if 0<=x+dx<W and abs(dx)+dy<4: img[base+2+dy][x+dx]=(40,110,50)
out=bytearray()
for row in img:
    for p in row: out+=bytes(q565(p))
# upscale 5x nearest
S=5
with open('/tmp/e.ppm','wb') as f: f.write(b'P6 %d %d 255\n'%(W,H)); f.write(out)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','/tmp/e.ppm','-vf',f'scale={W*S}:{H*S}:flags=neighbor','-q:v','2','output/eiffel_tower_16bit.jpg'],check=True)
