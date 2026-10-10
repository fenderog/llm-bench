import math, random, os, subprocess
random.seed(1879)
W,H=384,448
pixels=bytearray(W*H*3)
def rgb(c):
    if isinstance(c,str): return tuple(int(c[i:i+2],16) for i in (1,3,5))
    return c
def dot(x,y,c):
    x,y=int(x),int(y)
    if 0<=x<W and 0<=y<H:
        i=(y*W+x)*3; pixels[i:i+3]=bytes(rgb(c))
def rect(x0,y0,x1,y1,c):
    c=bytes(rgb(c)); x0=max(0,int(x0));x1=min(W-1,int(x1));y0=max(0,int(y0));y1=min(H-1,int(y1))
    if x1<x0 or y1<y0:return
    row=c*(x1-x0+1)
    for y in range(y0,y1+1):
        i=(y*W+x0)*3;pixels[i:i+len(row)]=row
def line(x0,y0,x1,y1,c,w=1):
    x0,y0,x1,y1=map(round,(x0,y0,x1,y1));dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    while True:
        rect(x0-w//2,y0-w//2,x0+(w-1)//2,y0+(w-1)//2,c)
        if x0==x1 and y0==y1:break
        e=2*err
        if e>=dy:err+=dy;x0+=sx
        if e<=dx:err+=dx;y0+=sy

def poly(points,c):
    for y in range(max(0,math.ceil(min(p[1] for p in points))),min(H-1,math.floor(max(p[1] for p in points)))+1):
        xs=[]
        for i in range(len(points)):
            x1,y1=points[i];x2,y2=points[(i+1)%len(points)]
            if (y1<=y<y2) or (y2<=y<y1):xs.append(x1+(y-y1)*(x2-x1)/(y2-y1))
        xs.sort()
        for i in range(0,len(xs)-1,2):rect(math.ceil(xs[i]),y,math.floor(xs[i+1]),y,c)
def ellipse(cx,cy,rx,ry,c):
    for y in range(int(cy-ry),int(cy+ry)+1):
        v=1-((y-cy)/ry)**2
        if v>=0:
            a=int(rx*math.sqrt(v));rect(cx-a,y,cx+a,y,c)

# Deliberately restricted, banded twilight palette with sparse ordered dithering.
sky=['#292c57','#34325f','#403666','#4d3c70','#5e437b','#754c84','#8c568b','#a56290','#bd7194','#d68199','#e9959f','#efa8a6','#f5bbaa','#f8cbaa','#f9d6b1']
for y in range(331):
    z=y/330*(len(sky)-1);a=int(z);frac=z-a
    rect(0,y,W-1,y,sky[a])
    if a<len(sky)-1:
        for x in range(W):
            if ((x%4)*4+(y%4)*5)%16<frac*16:dot(x,y,sky[a+1])
# Celestial points, upper sky.
for i in range(74):
    x=random.randrange(9,376);y=random.randrange(9,172)
    if random.random()<(.95-y/210):
        dot(x,y,random.choice(['#d8b9c4','#b092b3','#e8cfce']))
for x,y in [(53,47),(326,80),(119,29),(284,28),(29,132)]:
    line(x-2,y,x+2,y,'#b995b5');line(x,y-2,x,y+2,'#b995b5');dot(x,y,'#ffe6cd')
# Sunset disk rendered as stair-stepped rings.
ellipse(279,174,36,36,'#e8939c');ellipse(279,174,32,32,'#f6b6a5');ellipse(279,174,28,28,'#ffddaa')
for y in range(176,203,5):
    a=int(28*math.sqrt(max(0,1-((y-174)/28)**2)))
    rect(279-a,y,279+a,y+1,'#fac6a2')
# Long pixel-cloud islands, made of irregular, tiered runs.
def cloud(x,y,scale,colors):
    # dimensions deliberately snapped to two-pixel blocks
    spans=[(8,-7,31),(25,-11,46),(41,-8,69),(3,-4,79),(-8,0,94),(1,4,81),(18,7,64)]
    for k,(a,b,c) in enumerate(spans):
        rect(x+a*scale,y+b*scale,x+c*scale,y+(b+3)*scale,colors[min(k//2,len(colors)-1)])
    for _ in range(12):
        xx=x+random.randrange(5,79)*scale; yy=y+random.randrange(-3,8)*scale
        rect(xx,yy,xx+random.randrange(3,12)*scale,yy,colors[-1])
cloud(-29,97,1,['#634773','#80547f','#9c628c','#b87697'])
cloud(57,137,1,['#94628b','#b17397','#cf869d','#eca7a7'])
cloud(265,116,1,['#85557f','#a96c8c','#c88197','#e39aa2'])
cloud(307,57,1,['#493c69','#584372','#705080','#90618b'])
cloud(-36,206,1,['#cb8198','#dd929f','#efa9a5','#f5bdaa'])
cloud(234,226,1,['#dd939f','#eaa7a6','#f5b9a9','#f8c8af'])
# Narrow wisps around sunset.
for x,y,l in [(247,184,66),(292,192,64),(208,209,41),(20,235,71),(101,249,37),(316,261,52)]:
    rect(x,y,x+l,y+1,'#e9a1a2');rect(x+8,y+2,x+l-7,y+2,'#f4b7a6')
# Atmospheric skyline.
for x in range(0,W,5):
    h=random.randrange(7,24)
    rect(x,306-h,x+random.randrange(4,9),321,'#b28b9e')
    if random.random()<.3:line(x+2,306-h,x+2,300-h,'#b28b9e')
# The domed Paris skyline at left.
rect(41,281,67,306,'#9d8096');ellipse(54,281,12,13,'#9d8096');rect(51,263,57,272,'#9d8096');line(54,257,54,263,'#9d8096')
line(45,279,49,271,'#c69da4');line(57,270,63,279,'#b691a1')
# Mansard roofs and warmly lit facades.
for x in range(-7,W,21):
    top=random.randrange(297,309);bw=random.randrange(18,25)
    rect(x,top,x+bw,332,random.choice(['#8e798e','#927689','#a0808f','#aa8894']))
    poly([(x-2,top),(x+3,top-8),(x+bw-4,top-8),(x+bw+2,top)],'#6e657f')
    line(x+2,top-8,x+bw-4,top-8,'#b39aa5')
    rect(x+4,top-12,x+6,top-6,'#736880')
    line(x,top+2,x+bw,top+2,'#c19aa0')
    for xx in range(x+3,x+bw-1,6):
        for yy in range(top+6,330,7):
            rect(xx,yy,xx+1,yy+2,random.choice(['#eabc9b','#686780','#b2959c','#f8cc9e']))
# Back bank and layered park trees.
rect(0,328,383,347,'#6d6574')
for x in range(-8,397,7):
    y=random.randrange(319,331)
    ellipse(x,y,random.randrange(7,13),random.randrange(6,12),'#5c6071')
    ellipse(x-2,y-2,random.randrange(4,8),random.randrange(4,7),'#767783')
    if random.random()<.6:rect(x-5,y-5,x-1,y-4,'#909080')
rect(0,339,383,346,'#b29391');line(0,339,383,339,'#d7b29d');rect(0,347,383,351,'#5a5269')
for x in range(0,384,11):rect(x,342,x+7,344,'#967f85')
# Water in stepped color bands.
water=['#b78b9c','#a17f97','#89748f','#756b89','#646480','#555b79','#474f70','#3b4666']
for y in range(352,432):rect(0,y,383,y,water[min(7,(y-352)//10)])
for i in range(1150):
    y=random.randrange(353,430);x=random.randrange(W);length=random.choice([2,3,4,6,9,14])
    c=random.choice(['#9d8298','#84798f','#b492a0','#686b88','#545e7c'])
    line(x,y,x+length,y,c)
# Warm broken reflections below the sun and the tower.
for i in range(230):
    y=random.randrange(354,424);center=273-(y-353)*.16
    x=int(random.gauss(center,9+(y-352)*.22));length=random.randrange(2,12)
    c=random.choice(['#e8af9d','#d49d98','#bf8996','#f4c19f'])
    line(x,y,x+length,y,c)
for i in range(120):
    y=random.randrange(353,420);x=int(random.gauss(191,5+(y-350)*.18))
    line(x,y,x+random.randrange(2,8),y,random.choice(['#bf9191','#dfa78e','#eec29c','#806878']))
# Right-hand stone bridge, arches open onto water.
poly([(285,365),(319,354),(384,354),(384,378),(285,378)],'#776579')
for cx in [312,348,385]:
    ellipse(cx,378,13,14,'#c39a97');ellipse(cx,379,10,12,'#716c87');rect(cx-10,379,cx+10,384,'#716c87')
line(283,365,320,353,'#f1c3a3',2);line(320,353,384,353,'#f1c3a3',2)
line(284,369,320,357,'#a17b85');line(320,357,384,357,'#a17b85')
for x in range(322,384,6):line(x,348,x,352,'#5a5369')
line(322,348,384,348,'#7d697c')
# Tower foundations.
for x in [104,247]:
    rect(x-6,338,x+32,342,'#514654');rect(x-3,333,x+28,338,'#e3b398');rect(x,330,x+25,333,'#bb8b7b')
# Ironwork palette: aubergine shadows, copper faces, lit ochre edges.
dark='#483a50'; deep='#392f47';rust='#93615e'; copper='#c78a6d';gold='#f8cc8c';light='#ffe0a4'
# Upper taper: open cross-braced structure with a dark frame.
levels=[(83,189,195),(107,186,198),(132,183,201),(156,177,207),(179,170,214),(196,164,220)]
for i in range(len(levels)-1):
    y,l,r=levels[i];yy,ll,rr=levels[i+1]
    line(l,y,ll,yy,dark,4);line(r,y,rr,yy,dark,4)
    line(l+1,y,ll+1,yy,copper);line(r-1,y,rr-1,yy,gold)
    line(l+2,y,rr-2,yy,rust,2);line(r-2,y,ll+2,yy,rust,2)
    line(l+2,y,rr-2,yy,gold);line(l,y,r,y,dark,2)
    mid=(y+yy)//2
    ml=(l+ll)//2;mr=(r+rr)//2
    line(ml,mid,mr,mid,copper)
    line(192,y,192,yy,rust)
# Long antenna and tiny summit lantern.
line(192,39,192,65,dark);line(193,44,193,64,gold)
rect(189,64,195,67,dark);rect(187,68,197,71,copper);rect(188,72,196,81,dark)
rect(190,72,191,78,gold);rect(194,72,194,78,'#e3a877')
rect(185,81,199,84,deep);rect(185,81,199,81,gold);rect(188,85,196,89,rust)
# Platform and balcony helper.
def deck(x0,x1,y,h):
    rect(x0,y,x1,y+h,deep);rect(x0,y,x1,y,copper);rect(x0-2,y+2,x1+2,y+3,gold)
    rect(x0+1,y+5,x1-1,y+h-1,rust)
    for x in range(x0+3,x1-1,5):rect(x,y+5,x+1,y+h-2,light)
    line(x0-2,y-4,x1+2,y-4,copper)
    for x in range(x0,x1+1,4):line(x,y-4,x,y,deep)
    line(x0-2,y+h+1,x1+2,y+h+1,deep)
# Four openwork splayed supports between decks.
# Each leg is a series of thick-edged trapezoids, interior visible sky.
def truss_leg(nodes,mirror=False):
    if mirror:nodes=[(y,384-r,384-l) for y,l,r in nodes]
    for i in range(len(nodes)-1):
        y,l,r=nodes[i];yy,ll,rr=nodes[i+1]
        poly([(l,y),(r,y),(rr,yy),(ll,yy)],rust)
        # Open triangular voids pick up the dusk behind this ironwork.
        bg=sky[min(len(sky)-1,int(((y+yy)/2)/330*(len(sky)-1)))] if yy<313 else '#74717c'
        poly([(l+3,y+3),(r-3,y+3),((ll+rr)/2,yy-4)],bg)
        poly([(ll+3,yy-3),(rr-3,yy-3),((l+r)/2,y+4)],bg)
        line(l,y,ll,yy,deep,3);line(r,y,rr,yy,dark,3)
        line(l-1,y,ll-1,yy,copper);line(r,y,rr,yy,gold)
        line(l+1,y,rr-1,yy,copper);line(r-1,y,ll+1,yy,gold)
        line(l,y,r,y,deep,2);line(l,y-1,r,y-1,copper)
        dot(l,y,light);dot(r,y,light)
upperlegs=[(206,163,179),(226,156,174),(246,146,168),(263,135,160)]
truss_leg(upperlegs);truss_leg(upperlegs,True)
# Interior horizontal tie and lower diagonal girders.
line(167,243,217,243,dark,3);line(168,242,216,242,copper)
line(171,228,211,260,rust,2);line(213,228,173,260,copper,2)
# Great arch, built from angular segments in the two lower legs.
lowerlegs=[(276,129,155),(294,122,146),(316,112,135),(332,104,128)]
truss_leg(lowerlegs);truss_leg(lowerlegs,True)
# Broad curved arch lintel between the legs: characteristic Eiffel profile.
outer=[(130,319),(140,294),(153,279),(169,272),(192,269),(215,272),(231,279),(244,294),(254,319)]
inner=[(246,319),(236,300),(224,288),(209,283),(192,281),(175,283),(160,288),(148,300),(138,319)]
poly(outer+inner, dark)
for a,b in zip(inner,inner[1:]):line(*a,*b,copper,2)
for a,b in zip(outer,outer[1:]):line(*a,*b,rust)
for x in range(154,235,7):
    y=276+int(((x-192)/15)**2)
    line(x,y,x,y+4,gold)
# Upper and main observation terraces overlay the leg joints.
deck(161,223,196,9)
deck(127,257,263,12)
rect(140,260,244,261,copper)
# Deck center restaurant windows.
rect(171,265,213,273,deep)
for x in range(173,212,5):rect(x,266,x+2,270,'#ffdc98');dot(x,272,copper)
# Golden lamps embedded along the terraces and feet.
for y,x0,x1 in [(199,161,223),(266,128,256)]:
    for x in range(x0,x1+1,8):dot(x,y,light);dot(x,y+1,gold)
for x,y in [(112,327),(126,307),(145,284),(240,284),(259,307),(271,327),(177,179),(207,179),(184,141),(200,141)]:
    dot(x,y,light);dot(x,y-1,gold)
# Small trees at the plaza flank (never obscure the tower's arch).
for x in [3,17,33,53,72,88,297,313,335,358,377]:
    y=random.randrange(327,337)
    line(x,y-4,x,y+9,'#413d51',2)
    ellipse(x,y-4,9,10,'#454b60');ellipse(x-3,y-8,6,6,'#696e73')
    rect(x-5,y-11,x-1,y-10,'#899083')
# Tiny figures and lights establish monumental scale.
for x in [77,91,148,158,228,238,292]:
    dot(x,337,'#393b51');line(x,339,x,342,'#393b51');dot(x+1,343,'#393b51')
for x in range(12,383,38):
    line(x,340,x,347,'#484251');rect(x-1,338,x+1,339,'#fbd49b')
    line(x-2,351,x+2,351,'#d4a595')
# A distant little river boat.
poly([(51,384),(92,384),(86,390),(58,390)],'#303c57');line(52,384,91,384,'#efbe9f')
rect(61,378,82,383,'#dcc0b0');rect(64,379,79,381,'#596078');rect(67,375,75,377,'#514d63')
line(47,393,99,393,'#b897a2');line(58,396,88,396,'#8f8198')
# Foreground embankment: cut stone, rail, and period lamps.
poly([(0,429),(384,421),(384,448),(0,448)],'#292f49')
line(0,429,384,421,'#c69d9c',2);line(0,432,384,424,'#705d78',2)
for x in range(-20,384,29):line(x,435,x+12,448,'#44425d')
# Delicate riverside railing.
line(0,413,384,408,'#302f49',2);line(0,416,384,411,'#917887')
for x in range(7,384,12):
    y=round(413-x*5/384);line(x,y,x,y+14,'#35354f',2);dot(x-1,y,'#b79293')
# Foreground lamps with pixel halo and warm panes.
def lamp(x,y,bottom):
    # Transparent-looking glow via sparse stippling rather than antialiasing.
    for yy in range(y-17,y+18):
        for xx in range(x-17,x+18):
            d=(xx-x)**2+(yy-y)**2
            if d<260 and (xx+yy*3)%7==0:
                i=(yy*W+xx)*3
                if 0<=xx<W and 0<=yy<H:
                    old=tuple(pixels[i:i+3]);a=.12 if d>100 else .24
                    dot(xx,yy,tuple(round(v*(1-a)+t*a) for v,t in zip(old,(255,191,132))))
    line(x,y+11,x,bottom,'#252b43',3);line(x-1,y+14,x-1,bottom-3,'#987981')
    rect(x-4,bottom-3,x+4,bottom,'#252b43');rect(x-2,bottom-9,x+2,bottom-4,'#34354c')
    poly([(x-6,y-7),(x+6,y-7),(x+4,y+8),(x-4,y+8)],'#292d45')
    poly([(x-4,y-5),(x+4,y-5),(x+2,y+5),(x-2,y+5)],'#ffd394')
    rect(x-2,y-3,x+1,y+3,'#fff0bd');line(x,y-5,x,y+6,'#9a746f')
    line(x-5,y+8,x+5,y+8,'#bd8e7c');rect(x-2,y+9,x+2,y+11,'#292d45')
    poly([(x-8,y-8),(x,y-14),(x+8,y-8)],'#292d45');line(x-7,y-8,x+7,y-8,'#b89085');line(x,y-18,x,y-14,'#292d45')
lamp(30,331,438);lamp(352,342,433)
# Two quiet silhouetted spectators at the near-bank railing.
def person(x,y,h,coat):
    ellipse(x,y-h,2,3,'#242b42');rect(x-3,y-h+4,x+3,y-7,coat)
    line(x-2,y-7,x-2,y,'#222940',2);line(x+2,y-7,x+3,y,'#222940',2)
    line(x-3,y-h+6,x-5,y-10,coat,2);line(x+3,y-h+6,x+5,y-10,coat,2)
person(264,431,21,'#363248');person(274,431,18,'#594155');line(269,422,270,422,'#242b42')
# Pixel foliage in lower corners.
for i in range(110):
    x=random.choice([random.randrange(0,66),random.randrange(329,384)]);y=random.randrange(435,448)
    rect(x,y,x+random.randrange(2,7),y+2,random.choice(['#232d43','#303c50','#475064','#5b596b']))
# Export nearest-neighbor, high-quality JPEG with full chroma resolution.
os.makedirs('output',exist_ok=True)
with open('art.ppm','wb') as f:f.write(('P6\n%d %d\n255\n'%(W,H)).encode()+pixels)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','art.ppm','-vf','scale=1152:1344:flags=neighbor','-q:v','1','-pix_fmt','yuvj444p','output/eiffel_twilight.jpg'],check=True)
os.remove('art.ppm')
