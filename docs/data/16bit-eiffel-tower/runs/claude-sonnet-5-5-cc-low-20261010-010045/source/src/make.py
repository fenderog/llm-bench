import zlib,struct,math,random
W,H=256,224
random.seed(3)
pal=[];idx={}
def C(c):
    if c not in idx: idx[c]=len(pal);pal.append(c)
    return idx[c]
img=[[0]*W for _ in range(H)]
# sky gradient bands w/ dither
sky=[(40,72,152),(56,96,176),(72,120,200),(96,144,216),(128,172,232),(168,198,240),(224,200,200),(248,214,176)]
for y in range(168):
    f=y/168*(len(sky)-1);i=int(f);fr=f-i
    for x in range(W):
        d=[[0,.5],[.75,.25]][y%2][x%2]
        j=min(i+(1 if fr+ (d-.5)*.9>.5 else 0),len(sky)-1)
        img[y][x]=C(sky[j])
# clouds
cl=[(255,255,255),(226,236,250),(190,210,236)]
def cloud(cx,cy,s):
    for dx in range(-s*3,s*3):
        for dy in range(-s,s):
            for (ox,oy,r) in [(0,0,s),(-s*1.5,s*.3,s*.8),(s*1.5,s*.3,s*.8),(s*.6,-s*.3,s*.9)]:
                if ((dx-ox)/r)**2+((dy-oy)/(r*.6))**2<1:
                    x,y=cx+dx,cy+dy
                    if 0<=x<W and 0<=y<H:
                        k=0 if dy<oy-1 and dy< -s*.1 else (1 if dy<s*.3 else 2)
                        img[y][x]=C(cl[k]);break
for c in [(40,40,5),(205,60,6),(70,110,4),(180,22,4),(230,90,3),(20,80,3)]: cloud(*c)
# distant city
rb=[(120,120,160),(104,104,148)]
x=0
while x<W:
    w=random.randint(6,14);h=random.randint(8,26)
    for xx in range(x,min(W,x+w)):
        for y in range(168-h,168):
            img[y][xx]=C(rb[(x//7)%2] if (xx+y)%7 else (150,150,180)) if (y-168+h)>1 else C((150,150,180))
    x+=w
# trees/ground
g=[(40,120,56),(56,152,64),(32,96,48),(88,176,80)]
for y in range(168,H):
    for x in range(W):
        t=(y-168)
        c=g[(1 if (x//2+y)%4 else 3) if t<8 else (0 if (x+y*2)%5 else 1) if t<30 else (2 if (x+y)%3 else 0)]
        img[y][x]=C(c)
# path
for y in range(176,H):
    t=(y-176)/48
    hw=int(30+t*90)
    for x in range(128-hw,128+hw):
        if 0<=x<W: img[y][x]=C((232,208,152) if (x*3+y)%7 else (212,184,128))
# hedges
for y in range(170,200):
    for x in range(W):
        if abs(x-128)>70+(y-170)*3 and (x*7+y*3)%11<7 and y<190: img[y][x]=C((24,88,40) if (x+y)%2 else (40,120,56))
# tower
base=196;top=18
L=[(255,214,128),(216,150,72)];M=[(184,110,52)];D=[(120,64,40),(88,44,36)]
def hw(y):
    t=(base-y)/(base-top)
    return 1.2+52*math.exp(-3.6*t)+ (2.5*(1-t)**2)
plats=[(124,129),(84,87),(56,58)]
for y in range(top-8,base+1):
    h=hw(y) if y>=top else 1
    if y<top:
        if y>=top-8: 
            if abs(0)<1: img[y][128]=C(D[0]); 
        continue
    for x in range(128-int(h)-1,128+int(h)+2):
        dx=x-128;a=abs(dx)
        if a>h+.5:continue
        inplat=any(p[0]<=y<=p[1] for p in plats)
        t=(base-y)/(base-top)
        arch=False
        if y>150 and y<=base:
            # arch opening
            ry=(base-y)
            if a< h*0.62 and ((a/(h*0.62))**2+((ry-0)/52)**2<1) : arch=True
        if arch and not inplat: 
            continue
        edge=a>=h-1.2
        inner_open=False
        if not inplat and not edge:
            # lattice
            if h>7:
                p=(x+y)%6 if dx>0 else (x-y)%6
                solid=p in(0,1) or a<2 and False
                if h>12 and (y%9)==0: solid=True
                if not solid: continue
            else:
                if y%5 and a>0 and h>3: continue
        side=dx<0
        if edge: c=L[0] if side else M[0]
        else: c=(L[1] if side else D[0])
        if inplat: c=(255,190,100) if y==plats[[p[0]<=y<=p[1] for p in plats].index(True)][0] else (140,80,44)
        if a==0 and h<3: c=M[0]
        img[y][x]=C(c)
# spire & beacon
for y in range(6,top):
    img[y][128]=C(D[0])
img[5][128]=C((255,255,200));img[4][128]=C((255,255,255))
for dx,dy in[(-1,5),(1,5),(0,6),(0,3)]: img[dy][128+dx]=C((255,240,160))
# platform rail highlight
for (a,b) in plats:
    h=hw(a)
    for x in range(128-int(h)-2,128+int(h)+3): img[a-1][x]=C((255,226,150)) if x%2 else C(D[0])
# palette safety: reduce if >128
print(len(pal))
assert len(pal)<=128
for ty in range(0,H,8):
    for tx in range(0,W,8):
        s={img[y][x] for y in range(ty,ty+8) for x in range(tx,tx+8)}
        assert len(s)<=16,(tx,ty,len(s))
raw=b''.join(b'\0'+bytes(r) for r in img)
def ch(t,d):
    c=struct.pack('>I',len(d))+t+d;return c+struct.pack('>I',zlib.crc32(t+d))
open('output/eiffel_snes.png','wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,3,0,0,0))+ch(b'PLTE',bytes(v for c in pal for v in c))+ch(b'IDAT',zlib.compress(raw,9))+ch(b'IEND',b''))
