import struct, zlib, math, subprocess, os

W,H=960,720
def new_canvas():
    return bytearray(W*H*3)

def set_px(buf,x,y,c):
    if 0<=x<W and 0<=y<H:
        i=(y*W+x)*3
        buf[i]=c[0];buf[i+1]=c[1];buf[i+2]=c[2]

def lerp(a,b,t): return (int(a[0]+(b[0]-a[0])*t),int(a[1]+(b[1]-a[1])*t),int(a[2]+(b[2]-a[2])*t))

def fill_rect(buf,x0,y0,x1,y1,c):
    for y in range(max(0,y0),min(H,y1)):
        for x in range(max(0,x0),min(W,x1)):
            set_px(buf,x,y,c)

def fill_circle(buf,cx,cy,r,c):
    for y in range(int(cy-r-1),int(cy+r+2)):
        for x in range(int(cx-r-1),int(cx+r+2)):
            if (x-cx)**2+(y-cy)**2<=r*r: set_px(buf,x,y,c)

def fill_ellipse(buf,cx,cy,rx,ry,c):
    for y in range(int(cy-ry-1),int(cy+ry+2)):
        for x in range(int(cx-rx-1),int(cx+rx+2)):
            if ((x-cx)/max(1,rx))**2+((y-cy)/max(1,ry))**2<=1: set_px(buf,x,y,c)

def fill_poly(buf,pts,c):
    ys=[p[1] for p in pts]
    for y in range(max(0,int(min(ys))),min(H,int(max(ys))+1)):
        xs=[]
        n=len(pts)
        for i in range(n):
            x1,y1=pts[i];x2,y2=pts[(i+1)%n]
            if (y1<=y<y2) or (y2<=y<y1):
                t=(y-y1)/(y2-y1+1e-9)
                xs.append(x1+t*(x2-x1))
        xs.sort()
        for i in range(0,len(xs)-1,2):
            for x in range(int(xs[i]),int(xs[i+1])+1):
                set_px(buf,x,y,c)

def thick_line(buf,x1,y1,x2,y2,w,c):
    d=math.hypot(x2-x1,y2-y1)
    steps=max(1,int(d))
    for i in range(steps+1):
        t=i/steps
        fill_circle(buf,x1+(x2-x1)*t,y1+(y2-y1)*t,w/2,c)

def save_png(buf,path):
    raw=b''.join(b'\x00'+bytes(buf[y*W*3:(y+1)*W*3]) for y in range(H))
    def chunk(t,d):
        c=t+d; return struct.pack('>I',len(d))+c+struct.pack('>I',zlib.crc32(c)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b'')
    open(path,'wb').write(png)

def draw_scene(buf,t):
    # sky gradient
    top=(46,155,214); mid=(126,208,240); bot=(255,208,154)
    for y in range(H):
        if y<360: c=lerp(top,mid,y/360)
        else: c=lerp(mid,bot,(y-360)/360)
        for x in range(W):
            i=(y*W+x)*3; buf[i]=c[0];buf[i+1]=c[1];buf[i+2]=c[2]
    # sun
    fill_circle(buf,700,330,90,(255,200,60))
    fill_circle(buf,700,330,70,(255,245,180))
    # clouds
    for cx,cy,s in [(200+20*math.sin(t*0.3),140,1),(760+t*10%960-100,115,0.8)]:
        cx=cx%960
        for dx,dy,r in [(-60,0,28),(0,-8,34),(60,0,26)]:
            fill_ellipse(buf,int(cx+dx*s),int(cy+dy*s),int(r*s),int(22*s),(255,255,255))
    # sea
    fill_rect(buf,0,400,960,470,(42,150,180))
    fill_rect(buf,0,400,960,408,(120,220,230))
    # boardwalk
    fill_rect(buf,0,470,960,720,(201,168,122))
    fill_rect(buf,0,470,960,484,(169,131,90))
    for y in [540,610,680]:
        thick_line(buf,0,y,960,y,3,(169,131,90))
    off=int(t*300)%120
    for x in range(-120+off,960,120):
        thick_line(buf,x,484,x,720,3,(150,115,75))
    bob=int(10*math.sin(t*6))
    # shadow
    fill_ellipse(buf,480,645,225,20,(90,62,34))
    # wheels
    for wx in [350,625]:
        fill_circle(buf,wx,600+bob,34,(51,55,61))
        fill_circle(buf,wx,600+bob,22,(255,210,63))
        # spokes rotating
        a=t*10
        for k in range(3):
            ang=a+k*2.094
            thick_line(buf,wx,600+bob,wx+18*math.cos(ang),600+bob+18*math.sin(ang),4,(51,55,61))
        fill_circle(buf,wx,600+bob,6,(51,55,61))
        thick_line(buf,wx,560+bob,wx,580+bob,12,(122,127,133))
    # deck
    fill_poly(buf,[(265,545+bob),(710,545+bob),(700,575+bob),(255,575+bob)],(255,140,66))
    fill_poly(buf,[(265,545+bob),(710,545+bob),(708,553+bob),(263,553+bob)],(255,184,77))
    # pelican body
    fill_ellipse(buf,480,420+bob,115,100,(235,240,245))
    fill_ellipse(buf,480,420+bob,115,100,(235,240,245))
    # tail
    fill_poly(buf,[(370,410+bob),(270,390+bob),(290,425+bob),(265,435+bob),(370,445+bob)],(159,179,191))
    # legs
    thick_line(buf,430,500+bob,425,545+bob,16,(255,140,66))
    thick_line(buf,520,500+bob,525,545+bob,16,(255,140,66))
    fill_ellipse(buf,425,548+bob,26,9,(255,140,66))
    fill_ellipse(buf,525,548+bob,26,9,(255,140,66))
    # back wing
    fill_poly(buf,[(400,380+bob),(300,350+bob),(240,365+bob),(380,425+bob)],(215,225,232))
    # front wing flapping
    flap=15*math.sin(t*6)
    fill_poly(buf,[(500,390+bob),(640+flap,340+bob),(710+flap,355+bob),(560,420+bob),(650+flap,425+bob),(540,450+bob)],(255,255,255))
    # neck/head
    fill_poly(buf,[(555,340+bob),(580,220+bob),(630,210+bob),(610,340+bob)],(255,255,255))
    fill_circle(buf,665,200+bob,50,(255,255,255))
    # cap
    fill_poly(buf,[(625,165+bob),(705,172+bob),(700,185+bob),(620,178+bob)],(46,196,182))
    fill_circle(buf,665,158+bob,8,(255,210,63))
    # eye
    fill_circle(buf,678,196+bob,11,(255,255,255))
    fill_circle(buf,680,198+bob,6,(20,20,20))
    fill_circle(buf,682,196+bob,2,(255,255,255))
    # beak upper
    fill_poly(buf,[(705,185+bob),(850,225+bob),(705,245+bob)],(255,182,92))
    # pouch
    fill_poly(buf,[(705,245+bob),(835,250+bob),(760,310+bob),(715,280+bob)],(240,127,46))
    # scarf
    wv=10*math.sin(t*8)
    fill_poly(buf,[(575,300+bob),(500,285+bob+wv),(440,260+bob+wv),(490,305+bob)],(230,62,33))
    fill_circle(buf,575,305+bob,14,(230,62,33))
    # dust puffs
    for i,(dx,dy,r) in enumerate([(-80,0,18),(-110,10,12),(-60,15,10)]):
        fill_ellipse(buf,220+dx+int(20*math.sin(t*5+i)),600+dy, r, int(r*0.6),(255,255,255))

buf=new_canvas()
draw_scene(buf,0.6)
save_png(buf,'output/pelican-skateboard.png')

# video frames
os.makedirs('/tmp/frames',exist_ok=True)
fps=30; dur=5; n=fps*dur
for f in range(n):
    b=new_canvas(); draw_scene(b,f/fps); save_png(b,f'/tmp/frames/f{f:04d}.png')
subprocess.run(['ffmpeg','-y','-framerate','30','-i','/tmp/frames/f%04d.png','-c:v','libx264','-pix_fmt','yuv420p','-crf','20','output/pelican-ride.mp4'],check=True)
print('done')
