#!/usr/bin/env python3
"""Raster version of pelican-on-skateboard illustration (stdlib only)."""
import zlib, struct, math

W, H = 1000, 700
img = bytearray(W*H*3)

def hexcol(s):
    s=s.lstrip('#'); return (int(s[0:2],16),int(s[2:4],16),int(s[4:6],16))

def set_px(x,y,c,alpha=1.0):
    if 0<=x<W and 0<=y<H:
        i=(y*W+x)*3
        if alpha>=1.0:
            img[i]=c[0]; img[i+1]=c[1]; img[i+2]=c[2]
        else:
            img[i]=int(img[i]*(1-alpha)+c[0]*alpha)
            img[i+1]=int(img[i+1]*(1-alpha)+c[1]*alpha)
            img[i+2]=int(img[i+2]*(1-alpha)+c[2]*alpha)

def lerp(a,b,t): return (int(a[0]+(b[0]-a[0])*t),int(a[1]+(b[1]-a[1])*t),int(a[2]+(b[2]-a[2])*t))

def vgrad(y0,y1,c0,c1):
    for y in range(max(0,y0),min(H,y1)):
        t=(y-y0)/max(1,(y1-1-y0)); c=lerp(c0,c1,t)
        base=(y*W)*3
        for x in range(W):
            img[base+x*3]=c[0]; img[base+x*3+1]=c[1]; img[base+x*3+2]=c[2]

def fill_rect(x0,y0,x1,y1,c,alpha=1.0):
    x0=max(0,int(x0)); y0=max(0,int(y0)); x1=min(W,int(x1)); y1=min(H,int(y1))
    if alpha>=1:
        for y in range(y0,y1):
            b=(y*W)*3
            for x in range(x0,x1):
                img[b+x*3]=c[0]; img[b+x*3+1]=c[1]; img[b+x*3+2]=c[2]
    else:
        for y in range(y0,y1):
            for x in range(x0,x1): set_px(x,y,c,alpha)

def fill_circle(cx,cy,r,c,alpha=1.0):
    cx=int(cx);cy=int(cy);r=int(r)
    for y in range(max(0,cy-r),min(H,cy+r+1)):
        dy=y-cy; dx=int(math.sqrt(max(0,r*r-dy*dy)))
        for x in range(max(0,cx-dx),min(W,cx+dx+1)): set_px(x,y,c,alpha)

def fill_ellipse(cx,cy,rx,ry,c,alpha=1.0):
    cx=int(cx);cy=int(cy);rx=int(rx);ry=int(ry)
    if rx<=0 or ry<=0: return
    for y in range(max(0,cy-ry),min(H,cy+ry+1)):
        t=(y-cy)/ry; dx=int(rx*math.sqrt(max(0,1-t*t)))
        for x in range(max(0,cx-dx),min(W,cx+dx+1)): set_px(x,y,c,alpha)

def ellipse_outline(cx,cy,rx,ry,c,lw=5):
    for a in range(int(lw)):
        rx2=rx+a//2; ry2=ry+a//2
    # draw ring by angle steps
    steps=max(64,int(2*math.pi*max(rx,ry)))
    for i in range(steps):
        th=2*math.pi*i/steps
        for k in range(lw):
            set_px(int(cx+(rx-k*0.5)*math.cos(th)),int(cy+(ry-k*0.5)*math.sin(th)),c)

def circle_outline(cx,cy,r,c,lw=5):
    ellipse_outline(cx,cy,r,r,c,lw)

def thick_line(x0,y0,x1,y1,c,lw=5,alpha=1.0):
    dx=x1-x0; dy=y1-y0; L=math.hypot(dx,dy)
    steps=max(1,int(L))
    rad=lw/2
    for i in range(steps+1):
        t=i/steps; px=x0+dx*t; py=y0+dy*t
        r=int(math.ceil(rad))
        for yy in range(int(py-r),int(py+r)+1):
            for xx in range(int(px-r),int(px+r)+1):
                if (xx-px)**2+(yy-py)**2<=rad*rad: set_px(xx,yy,c,alpha)

def fill_poly(pts,c,alpha=1.0):
    ys=[p[1] for p in pts]; y0=max(0,int(min(ys))); y1=min(H-1,int(max(ys)))
    n=len(pts)
    for y in range(y0,y1+1):
        xs=[]
        for i in range(n):
            x0,y0p=pts[i]; x1,y1p=pts[(i+1)%n]
            if (y0p<=y<y1p) or (y1p<=y<y0p):
                t=(y-y0p)/(y1p-y0p) if y1p!=y0p else 0
                xs.append(x0+t*(x1-x0))
        xs.sort()
        for k in range(0,len(xs)-1,2):
            for x in range(max(0,int(xs[k])),min(W,int(xs[k+1])+1)): set_px(x,y,c,alpha)

def poly_outline(pts,c,lw=5,close=True):
    n=len(pts)
    for i in range(n if close else n-1):
        thick_line(pts[i][0],pts[i][1],pts[(i+1)%n][0],pts[(i+1)%n][1],c,lw)

INK=hexcol('#2B3A4A')

# --- background ---
vgrad(0,700,hexcol('#4FB6E8'),hexcol('#DFF6FF'))
# sun glow + sun
for r,a in [(110,0.25),(85,0.35),(65,0.5)]:
    fill_circle(830,135,r,hexcol('#FFE66D'),alpha=a)
fill_circle(830,135,52,hexcol('#FFF3A0'))
circle_outline(830,135,52,hexcol('#FFB800'),6)
fill_circle(815,135,5,hexcol('#2B3A4A')); fill_circle(845,135,5,hexcol('#2B3A4A'))
thick_line(810,152,830,160,INK,4); thick_line(830,160,850,152,INK,4)
# clouds
for cx,cy,rx,ry in [(180,130,68,30),(225,112,48,28),(135,112,36,22),(520,85,58,24),(560,70,38,20),(484,70,28,16),(660,190,42,18),(688,180,26,14)]:
    fill_ellipse(cx,cy,rx,ry,hexcol('#FFFFFF'),0.95)
# hills
fill_poly([(0,360),(0,410),(1000,410),(1000,345),(930,375),(830,340),(700,285),(550,335),(420,380),(300,345),(150,300)],hexcol('#7AC74F'))
thick_line(0,360,150,300,hexcol('#4E9440'),5); thick_line(150,300,300,345,hexcol('#4E9440'),5)
thick_line(300,345,420,380,hexcol('#4E9440'),5); thick_line(420,380,550,335,hexcol('#4E9440'),5)
thick_line(550,335,700,285,hexcol('#4E9440'),5); thick_line(700,285,830,340,hexcol('#4E9440'),5)
thick_line(830,340,1000,345,hexcol('#4E9440'),5)
# palms (simplified)
for px,py,s in [(90,335,1.0),(915,330,0.85)]:
    thick_line(px,py,px,py+70,hexcol('#7A4A2B'),12)
    fill_ellipse(px-32*s,py-8,34*s,12,hexcol('#2FA36B')); fill_ellipse(px+32*s,py-8,34*s,12,hexcol('#2FA36B'))
    fill_ellipse(px,py-22,36*s,13,hexcol('#2FA36B'))
    fill_circle(px-10,py,7,hexcol('#6B4226')); fill_circle(px+12,py+2,7,hexcol('#6B4226'))
# sea + sand
fill_rect(0,400,1000,462,hexcol('#1A8FB5'))
fill_rect(0,400,1000,428,hexcol('#2DBFC8'))
for x,y in [(60,425),(300,435),(620,428),(840,438)]:
    thick_line(x,y,x+15,y-5,hexcol('#FFFFFF'),3,0.7); thick_line(x+15,y-5,x+30,y,hexcol('#FFFFFF'),3,0.7); thick_line(x+30,y,x+45,y-5,hexcol('#FFFFFF'),3,0.7); thick_line(x+45,y-5,x+60,y,hexcol('#FFFFFF'),3,0.7)
fill_rect(0,462,1000,510,hexcol('#FFD48A'))
fill_rect(0,462,1000,478,hexcol('#FFE9B8'))
# road
fill_rect(0,510,1000,700,hexcol('#5D6878'))
fill_rect(0,510,1000,524,hexcol('#FFD166'))
for x in [30,150,270,670,790,910]:
    fill_rect(x,600,x+70,612,hexcol('#FFFFFF'))
# seagulls
for gx,gy,s in [(340,165,1.4),(430,200,1.0),(700,110,1.0)]:
    thick_line(gx-28*s,gy,gx-14*s,gy-10*s,INK,4); thick_line(gx-14*s,gy-10*s,gx,gy,INK,4)
    thick_line(gx,gy,gx+14*s,gy-10*s,INK,4); thick_line(gx+14*s,gy-10*s,gx+28*s,gy,INK,4)
# speed lines
thick_line(55,500,185,500,hexcol('#FFFFFF'),9,0.85); thick_line(30,535,155,535,hexcol('#FFFFFF'),7,0.85); thick_line(70,568,180,568,hexcol('#FFFFFF'),6,0.6)
# shadow
fill_ellipse(510,638,240,22,hexcol('#1A2A3A'),0.28)

# --- skateboard ---
# wheels
for wx in [350,670]:
    fill_circle(wx,605,34,INK); fill_circle(wx,605,26,hexcol('#FF5A7A'))
    circle_outline(wx,605,26,hexcol('#FFFFFF'),5); fill_circle(wx,605,8,hexcol('#FFFFFF')); fill_circle(wx-8,605-8,4,hexcol('#FFC2D1'))
# trucks
fill_poly([(330,575),(370,575),(360,595),(340,595)],hexcol('#CBD5E1')); poly_outline([(330,575),(370,575),(360,595),(340,595)],INK,4)
fill_poly([(650,575),(690,575),(680,595),(660,595)],hexcol('#CBD5E1')); poly_outline([(650,575),(690,575),(680,595),(660,595)],INK,4)
# deck
fill_poly([(210,555),(210,543),(230,532),(790,532),(810,543),(810,567),(790,578),(230,578),(210,567)],hexcol('#FF5A7A'))
fill_rect(230,532,790,578,hexcol('#FF6B6B'))
fill_rect(470,532,550,578,hexcol('#FFF200'))  # bolt bg area simplified
fill_poly([(500,532),(470,558),(490,558),(475,578),(515,550),(495,550)],hexcol('#FFF200'))
poly_outline([(500,532),(470,558),(490,558),(475,578),(515,550),(495,550)],INK,3)
poly_outline([(210,555),(210,543),(230,532),(790,532),(810,543),(810,567),(790,578),(230,578),(210,567)],INK,6)
for dx in [300,340,680,720]:
    fill_circle(dx,555,5,hexcol('#FFFFFF'))
thick_line(240,620,340,620,hexcol('#FFFFFF'),5,0.5); thick_line(680,620,780,620,hexcol('#FFFFFF'),5,0.5)

# --- pelican ---
ORANGE=hexcol('#FF9F1C'); DORANGE=hexcol('#E67E00')
# tail
fill_poly([(310,480),(230,460),(245,490),(220,495),(250,515),(235,535),(310,515)],hexcol('#D8E4EC'))
poly_outline([(310,480),(230,460),(245,490),(220,495),(250,515),(235,535),(310,515)],INK,5)
# body
fill_ellipse(440,460,135,105,hexcol('#FFFFFF'))
fill_ellipse(440,490,100,60,hexcol('#D8E4EC'),0.7)
ellipse_outline(440,460,135,105,INK,7)
# legs
thick_line(430,550,425,595,DORANGE,14); fill_ellipse(425,600,28,12,ORANGE); ellipse_outline(425,600,28,12,INK,4)
thick_line(550,550,560,595,DORANGE,16); fill_ellipse(570,597,32,13,ORANGE); ellipse_outline(570,597,32,13,INK,4)
# raised wing
fill_poly([(380,430),(300,340),(250,220),(265,195),(295,210),(430,380)],hexcol('#EAF2F8'))
poly_outline([(380,430),(300,340),(250,220),(265,195),(295,210),(430,380)],INK,6)
thick_line(285,250,350,350,hexcol('#7A9BB5'),4); thick_line(310,235,375,335,hexcol('#7A9BB5'),4)
fill_poly([(250,220),(230,180),(235,150),(265,180)],hexcol('#FFFFFF')); poly_outline([(250,220),(230,180),(235,150),(265,180)],INK,4)
# scarf back
fill_poly([(540,330),(460,320),(380,350),(280,360),(360,385),(545,355)],hexcol('#E63946'))
poly_outline([(540,330),(460,320),(380,350),(280,360),(360,385),(545,355)],INK,5)
# neck
thick_line(520,450,560,400,hexcol('#EFF4F8'),70); thick_line(560,400,545,340,hexcol('#EFF4F8'),70); thick_line(545,340,570,285,hexcol('#EFF4F8'),70)
# head
fill_circle(595,260,72,hexcol('#FFFFFF')); circle_outline(595,260,72,INK,6)
# crest
fill_poly([(545,205),(500,170),(545,180),(590,170),(555,205)],INK)
# helmet
fill_ellipse(600,215,65,62,hexcol('#2EC4B6')); fill_rect(535,215,665,245,hexcol('#2EC4B6'))
poly_outline([(535,235),(535,200),(560,160),(640,160),(665,200),(665,245),(535,245)],INK,5)
fill_rect(592,150,610,172,hexcol('#FFD166')); fill_circle(601,148,8,hexcol('#FF5A7A')); circle_outline(601,148,8,INK,3)
fill_circle(560,195,7,hexcol('#FFD166')); fill_circle(640,195,7,hexcol('#FFD166'))
# eye
fill_circle(612,260,20,hexcol('#FFFFFF')); circle_outline(612,260,20,INK,4)
fill_circle(616,262,11,INK); fill_circle(620,258,4,hexcol('#FFFFFF'))
fill_ellipse(575,285,12,8,hexcol('#FF9AA2'))
# beak upper
fill_poly([(650,245),(880,270),(875,296),(650,275)],hexcol('#FF9F1C'))
poly_outline([(650,245),(880,270),(875,296),(650,275)],INK,5)
fill_poly([(860,272),(893,272),(891,295),(860,294)],DORANGE)
# pouch
fill_poly([(650,275),(875,296),(760,375),(630,310)],hexcol('#F4846B'))
poly_outline([(650,275),(875,296),(760,375),(630,310)],INK,5)
fill_poly([(675,295),(830,305),(740,355),(665,315)],hexcol('#E96A5A'))
# fish
fill_ellipse(722,300,14,10,hexcol('#4FB6E8')); fill_poly([(736,286),(764,300),(736,314)],hexcol('#4FB6E8'))
poly_outline([(736,286),(764,300),(736,314)],INK,3); ellipse_outline(722,300,14,10,INK,3)
# front wing
fill_ellipse(480,475,42,55,hexcol('#FFFFFF')); ellipse_outline(480,475,42,55,INK,5)
thick_line(470,445,495,485,hexcol('#7A9BB5'),3)
# scarf knot
fill_circle(548,342,20,hexcol('#E63946')); circle_outline(548,342,20,INK,5)
fill_poly([(555,360),(560,435),(540,448),(530,425),(542,362)],hexcol('#FF5A5A'))
poly_outline([(555,360),(560,435),(540,448),(530,425),(542,362)],INK,4)

# dust
for cx,cy,r in [(210,600,18),(228,592,13),(194,592,11),(800,605,15),(815,598,10),(787,597,9)]:
    fill_circle(cx,cy,r,hexcol('#FFFFFF')); circle_outline(cx,cy,r,hexcol('#E6DCC8'),3)
# badge (moved below deck so it doesn't read as a wheel) + star
fill_circle(95,645,40,hexcol('#FFFDF0')); circle_outline(95,645,40,INK,5); circle_outline(95,645,32,hexcol('#FF5A7A'),3)
fill_poly([(95,622),(101,637),(117,637),(104,646),(109,661),(95,652),(81,661),(86,646),(73,637),(89,637)],hexcol('#E63946'))
# bottom banner with yellow trim (no text in raster)
fill_rect(330,648,670,680,INK)
fill_rect(330,648,670,654,hexcol('#FFD166'))

def save_png(path):
    def chunk(t,d):
        h=struct.pack('>I',len(d))+t+d
        return h+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    raw=bytearray()
    for y in range(H):
        raw.append(0)
        raw.extend(img[y*W*3:(y+1)*W*3])
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),6))+chunk(b'IEND',b'')
    open(path,'wb').write(png)
    print('wrote',path,len(png))

save_png('output/pelican-skateboard.png')
