import zlib, struct, math, random
W,H=256,224
random.seed(7)
pal=[];pidx={}
def C(r,g,b):
    k=(r,g,b)
    if k not in pidx: pidx[k]=len(pal);pal.append(k)
    return pidx[k]
img=[[0]*W for _ in range(H)]
def put(x,y,c):
    if 0<=x<W and 0<=y<H: img[y][x]=c
# sky gradient with Bayer dithering
stops=[(0,(36,48,128)),(60,(84,80,164)),(110,(188,100,160)),(150,(244,140,128)),(190,(255,196,136))]
N=14
def skycol(y):
    for i in range(len(stops)-1):
        y0,c0=stops[i];y1,c1=stops[i+1]
        if y<=y1:
            f=(y-y0)/(y1-y0);return tuple(c0[k]+(c1[k]-c0[k])*f for k in range(3))
    return stops[-1][1]
bayer=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
bands=[tuple(int(round(v/8)*8) if False else int(v) for v in skycol(190*i/(N-1))) for i in range(N)]
bandi=[C(*b) for b in bands]
for y in range(H):
    for x in range(W):
        t=min(y,190)/190*(N-1)
        b=int(t);f=t-b
        if b>=N-1: put(x,y,bandi[-1]);continue
        put(x,y,bandi[b+1] if f>(bayer[y%4][x%4]+.5)/16 else bandi[b])
# sun glow
sun=[C(255,232,160),C(255,214,150)]
for y in range(H):
    for x in range(W):
        d=math.hypot(x-52,(y-168)*1.1)
        if d<14: put(x,y,sun[0])
        elif d<18 and (x+y)%2==0: put(x,y,sun[1])
# clouds
cl=[C(255,226,214),C(240,172,184),C(160,110,162)]
def cloud(cx,cy,w,h):
    for y in range(cy-h,cy+h//2+1):
        for x in range(cx-w,cx+w+1):
            dx=(x-cx)/w;dy=(y-cy)/h
            bump=0.18*math.sin(x*0.45+cx)
            if dx*dx+dy*dy+bump*0.3<1 and (dy<0.45):
                u=(y-(cy-h))/(h*1.5)
                put(x,y,cl[0] if u<.35 else cl[1] if u<.7 else cl[2])
for a in [(40,34,34,6),(98,60,28,4),(210,40,36,6),(190,92,40,5),(20,100,30,4),(130,120,40,4),(236,130,26,3),(70,140,36,3)]:
    cloud(*a)
# distant paris
hz=[C(176,112,150),C(140,92,140),C(255,206,140)]
x=0
while x<W:
    bw=random.randint(7,16);bh=random.randint(6,17)
    for xx in range(x,min(W,x+bw)):
        for yy in range(188-bh,190):
            put(xx,yy,hz[0] if (xx-x)<bw-2 else hz[1])
    for wy in range(188-bh+3,186,4):
        for wx in range(x+2,x+bw-3,3):
            put(wx,wy,hz[2])
    if bh>12 and random.random()<.6:
        for i in range(5): put(x+bw//2,188-bh-i,hz[1])
    x+=bw
# dome
for y in range(-9,0):
    for xx in range(-int(math.sqrt(max(0,81-y*y))),int(math.sqrt(max(0,81-y*y)))+1):
        put(205+xx,180+y,hz[1])
# ground
g=[C(70,140,70),C(52,116,64),C(92,164,76),C(36,88,64)]
path=[C(236,196,140),C(206,156,116)]
for y in range(188,H):
    for x in range(W):
        band=((y-188)//4)%2
        put(x,y,g[0] if (band+((x//16)%2))%2==0 else g[1])
cx=128
for y in range(188,H):
    t=(y-188)/36
    hw=14+t*70
    for x in range(int(cx-hw),int(cx+hw)+1):
        edge=abs(x-cx)>hw-2
        put(x,y,path[1] if edge or (x+y)%11==0 and t>.2 else path[0])
# tower
iron=[C(255,196,110),C(214,128,72),C(150,80,56),C(92,48,56),C(54,30,56)]
stone=[C(120,100,120),C(80,66,92)]
top,bot=14,190
def w(y):
    t=(y-top)/(bot-top);return 1.5+58.5*t**2.2
P1,P2,P3=160,129,44
def inside(x,y):
    dx=abs(x-cx+0.0+0.5);return dx
for y in range(top,bot):
    ww=w(y)
    for x in range(int(cx-ww-1),int(cx+ww+2)):
        dx=abs(x-cx+0.5)
        if dx>ww: continue
        # gaps
        if y>=P1+4:
            inner=ww*0.63
            at=bot-26*math.sqrt(max(0,1-(dx/(w(bot-1)*0.63))**2)) if dx<w(bot-1)*0.63 else bot
            if dx<inner and y>at: continue
        elif P2+4<y<P1-2 and dx<ww*0.45: continue
        left=(x<cx)
        edge=ww-dx
        if y<P3-4:
            # spire: solid thin
            col=iron[1] if left else iron[3]
            if edge<1: col=iron[0] if left else iron[2]
            put(x,y,col);continue
        horiz=(y%14<2) and y>P3+8
        d=dx
        k=7 if y<P2 else 9
        diag=((d+y)%k<2) or ((d-y)%k<2)
        back=((d+y+3)%k==0)
        if edge<2.2:
            col=iron[0] if left and edge<1.1 else (iron[1] if left else (iron[3] if edge<1.1 else iron[2]))
            put(x,y,col)
        elif horiz or diag:
            put(x,y,iron[1] if left else iron[2])
        elif back:
            put(x,y,iron[4] if not left else iron[3])
# platforms
def plat(y,hw,th,rail):
    for yy in range(y,y+th):
        for x in range(cx-hw,cx+hw):
            c=iron[1] if yy==y else iron[2] if yy<y+th-1 else iron[4]
            if yy==y: c=iron[0] if x<cx else iron[1]
            put(x,yy,c)
    for x in range(cx-hw,cx+hw):
        if x%3==0:
            for r in range(1,rail+1): put(x,y-r,iron[3])
        put(x,y-rail,iron[2])
plat(P1,int(w(P1))+6,5,4)
plat(P2,int(w(P2))+5,4,3)
plat(P3,int(w(P3))+4,4,3)
plat(P3-10,int(w(P3-10))+3,3,0)
# cabin & antenna
for y in range(P3-8,P3):
    for x in range(cx-5,cx+5): put(x,y,iron[2] if x>=cx else iron[1])
for y in range(top-4,top+1): put(cx,y,iron[3]);put(cx-1,y,iron[3])
put(cx,top-6,C(255,90,80)); put(cx,top-5,C(255,90,80))
# feet
for s in (-1,1):
    fx=int(cx+s*w(bot-1)) 
    for y in range(bot-3,bot+2):
        for x in range(fx-8,fx+8) if False else range(min(fx-10*(s==1),fx),max(fx,fx+10*(s==-1))):
            pass
for y in range(bot-3,bot+3):
    for x in list(range(cx-72,cx-30))+list(range(cx+30,cx+72)):
        put(x,y,stone[0] if y<bot else stone[1])
# trees and hedges
tr=[C(30,84,60),C(48,120,64),C(88,160,72),C(110,76,56)]
def tree(tx,ty,r):
    for y in range(ty-r,ty+r):
        for x in range(tx-r,tx+r):
            if (x-tx)**2+(y-ty)**2<r*r:
                d=((x-tx)+(y-ty)*-0.8)/r
                put(x,y,tr[2] if d>.35 else tr[1] if d>-.35 else tr[0])
    for y in range(ty+r-2,ty+r+8):
        for x in (tx-1,tx): put(x,y,tr[3])
for tx,ty,r in [(14,196,13),(40,200,11),(240,196,13),(214,201,11),(66,194,8),(190,194,8)]: tree(tx,ty,r)
for y in range(212,H):
    for x in range(W):
        if x<46 or x>210:
            put(x,y,tr[0] if (x+y)%7 else tr[1])
# birds
for bx,by in [(160,52),(172,46),(150,64)]:
    for i in range(3): put(bx-i-1,by-(i==2)*0-i//2,iron[4]);put(bx+i+1,by-i//2,iron[4])
    put(bx,by,iron[4])
# verify
worst=0
for ty in range(0,H,8):
    for tx in range(0,W,8):
        s={img[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)}
        worst=max(worst,len(s))
print("colors",len(pal),"worst tile",worst)
raw=b''.join(b'\0'+bytes(r) for r in img)
def ch(t,d):
    c=struct.pack('>I',len(d))+t+d
    return c+struct.pack('>I',zlib.crc32(t+d))
out=b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+ch(b'PLTE',b''.join(bytes(c) for c in pal))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b'')
open('output/eiffel_snes.png','wb').write(out)
