#!/usr/bin/env python3
"""Generate pelican riding skateboard SVG (animated with SMIL) + frames for video."""
import math, os

W, H = 1000, 700
OUT_SVG = "output/pelican-skateboard.svg"

def svg_header():
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Pelican riding a skateboard at sunset">
<title>Pelican riding a skateboard</title>
<desc>A cheerful white pelican wearing a teal helmet and red scarf rides a skateboard along a beach boardwalk at sunset.</desc>
'''

def defs():
    return '''
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#2f8fd0"/>
    <stop offset="45%" stop-color="#7cc4ea"/>
    <stop offset="72%" stop-color="#ffd9a0"/>
    <stop offset="100%" stop-color="#ff9d76"/>
  </linearGradient>
  <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="#fff7c9" stop-opacity="0.95"/>
    <stop offset="40%" stop-color="#ffe27a" stop-opacity="0.9"/>
    <stop offset="100%" stop-color="#ffb347" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#2aa5b8"/>
    <stop offset="100%" stop-color="#1a7f95"/>
  </linearGradient>
  <linearGradient id="sand" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#ffe3a3"/>
    <stop offset="100%" stop-color="#f7c46d"/>
  </linearGradient>
  <linearGradient id="road" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#6b7280"/>
    <stop offset="12%" stop-color="#7d8590"/>
    <stop offset="100%" stop-color="#4b5563"/>
  </linearGradient>
  <linearGradient id="bodyG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#ffffff"/>
    <stop offset="70%" stop-color="#f6f0e3"/>
    <stop offset="100%" stop-color="#e8dcc3"/>
  </linearGradient>
  <linearGradient id="wingG" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#ffffff"/>
    <stop offset="100%" stop-color="#d9cdb2"/>
  </linearGradient>
  <linearGradient id="beakG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#ffb02e"/>
    <stop offset="100%" stop-color="#f67f1b"/>
  </linearGradient>
  <linearGradient id="pouchG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#ff9e5e"/>
    <stop offset="100%" stop-color="#e85d2a"/>
  </linearGradient>
  <linearGradient id="deckTop" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#14b8a6"/>
    <stop offset="50%" stop-color="#0bd5c0"/>
    <stop offset="100%" stop-color="#0e9b8d"/>
  </linearGradient>
  <linearGradient id="helmetG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#2dd4bf"/>
    <stop offset="100%" stop-color="#0f766e"/>
  </linearGradient>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="8"/>
  </filter>
  <filter id="outline" x="-20%" y="-20%" width="140%" height="140%">
  </filter>
</defs>
<style>
  .ol { stroke:#3b2f2f; stroke-width:6; stroke-linejoin:round; stroke-linecap:round; }
  .ol-thin { stroke:#3b2f2f; stroke-width:4; stroke-linejoin:round; stroke-linecap:round; }
  .title { font-family: 'Trebuchet MS', Verdana, sans-serif; font-weight:900; }
</style>
'''

def background(cloud_shift=0):
    # cloud_shift for video frames; SMIL adds extra animation on top
    s = ''
    s += f'<rect width="{W}" height="{H}" fill="url(#sky)"/>\n'
    # sun glow + sun
    s += '<circle cx="800" cy="150" r="150" fill="url(#sunGlow)"/>\n'
    s += '<circle cx="800" cy="150" r="68" fill="#fff3a6" stroke="#ff9d3c" stroke-width="5"/>\n'
    s += '<circle cx="782" cy="136" r="13" fill="#ffffff" opacity="0.7"/>\n'
    # clouds
    clouds = [(190,125,1.0),(480,95,0.75),(880,320,0.6),(320,220,0.5)]
    for i,(cx,cy,sc) in enumerate(clouds):
        x = cx + cloud_shift * (1 if i%2==0 else -1) * (10+i*5)
        s += f'''<g transform="translate({x},{cy}) scale({sc})" opacity="0.95">
          <ellipse cx="0" cy="0" rx="70" ry="26" fill="white"/>
          <ellipse cx="-38" cy="8" rx="36" ry="20" fill="white"/>
          <ellipse cx="38" cy="8" rx="40" ry="22" fill="white"/>
          <ellipse cx="0" cy="-14" rx="38" ry="22" fill="white"/>
        </g>\n'''
    # distant birds
    s += '''<g stroke="#3b2f2f" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.7">
      <path d="M210,200 q10,-10 20,0 q10,-10 20,0"/>
      <path d="M270,170 q8,-8 16,0 q8,-8 16,0"/>
      <path d="M620,90 q8,-8 16,0 q8,-8 16,0"/>
    </g>\n'''
    # sea
    s += '<rect x="0" y="360" width="1000" height="70" fill="url(#sea)"/>\n'
    s += '''<g fill="white" opacity="0.55">
      <ellipse cx="150" cy="385" rx="60" ry="6"/><ellipse cx="420" cy="400" rx="80" ry="6"/>
      <ellipse cx="700" cy="385" rx="55" ry="6"/><ellipse cx="880" cy="405" rx="70" ry="6"/>
      <ellipse cx="300" cy="415" rx="40" ry="5"/>
    </g>\n'''
    # sand
    s += '<rect x="0" y="430" width="1000" height="70" fill="url(#sand)"/>\n'
    s += '''<g fill="#e0a44f" opacity="0.6">
      <ellipse cx="120" cy="460" rx="8" ry="4"/><ellipse cx="250" cy="475" rx="6" ry="3"/>
      <ellipse cx="800" cy="465" rx="9" ry="4"/><ellipse cx="920" cy="478" rx="6" ry="3"/>
      <ellipse cx="550" cy="470" rx="7" ry="3"/>
    </g>\n'''
    # palm silhouettes left/right
    s += '''<g>
      <rect x="52" y="280" width="14" height="160" rx="7" fill="#5b3a29" stroke="#3b2f2f" stroke-width="4"/>
      <g fill="#2f9e44" stroke="#1f6b2e" stroke-width="4">
        <ellipse cx="60" cy="260" rx="58" ry="20" transform="rotate(-20 60 260)"/>
        <ellipse cx="60" cy="250" rx="58" ry="20" transform="rotate(15 60 250)"/>
        <ellipse cx="60" cy="245" rx="50" ry="18" transform="rotate(45 60 245)"/>
      </g>
      <circle cx="48" cy="275" r="12" fill="#6b4423" stroke="#3b2f2f" stroke-width="3"/>
      <circle cx="72" cy="275" r="12" fill="#6b4423" stroke="#3b2f2f" stroke-width="3"/>
    </g>\n'''
    # road / boardwalk
    s += '<rect x="0" y="500" width="1000" height="200" fill="url(#road)"/>\n'
    s += '<rect x="0" y="500" width="1000" height="14" fill="#9aa0aa"/>\n'
    s += '<rect x="0" y="514" width="1000" height="6" fill="#3b2f2f" opacity="0.3"/>\n'
    # moving dashes (road)
    for i in range(6):
        x = 40 + i*180 + cloud_shift*3
        # wrap
        x = x % 1100 - 50
        s += f'<rect x="{x}" y="600" width="90" height="14" rx="7" fill="#fde68a" opacity="0.9"/>\n'
    return s

def skateboard(wheel_angle=0, animated=False):
    s = '<g id="skateboard">\n'
    # shadow
    s += '<ellipse cx="500" cy="630" rx="200" ry="22" fill="black" opacity="0.25" filter="url(#soft)"/>\n'
    # wheels back/front
    for wx in [395, 605]:
        spin = '<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="0.6s" repeatCount="indefinite"/>' if animated else ''
        s += f'''<g transform="translate({wx},590)">
          <circle r="34" fill="#3b2f2f"/>
          <circle r="28" fill="#ff6b35" stroke="#3b2f2f" stroke-width="3"/>
          <g transform="rotate({wheel_angle})">
            {spin}
            <rect x="-3" y="-18" width="6" height="36" rx="3" fill="#ffe8cc"/>
            <rect x="-18" y="-3" width="36" height="6" rx="3" fill="#ffe8cc"/>
          </g>
          <circle r="8" fill="#f8fafc" stroke="#3b2f2f" stroke-width="3"/>
        </g>\n'''
    # trucks
    for wx in [395,605]:
        s += f'<path d="M{wx-22},562 L{wx+22},562 L{wx+12},540 L{wx-12},540 Z" fill="#cbd5e1" stroke="#3b2f2f" stroke-width="4" stroke-linejoin="round"/>\n'
    # deck: wood side + top
    s += '''<g>
      <path d="M300,530 Q300,515 325,515 L675,515 Q700,515 700,530 L695,542 Q690,555 670,555 L330,555 Q310,555 305,542 Z"
        fill="#eab308" stroke="#3b2f2f" stroke-width="6" stroke-linejoin="round"/>
      <path d="M300,530 Q300,515 325,515 L675,515 Q700,515 700,530 L698,536 Q695,542 680,542 L320,542 Q305,542 302,536 Z"
        fill="url(#deckTop)" stroke="#3b2f2f" stroke-width="5" stroke-linejoin="round"/>
      <path d="M350,515 L360,542 M420,515 L430,542 M570,515 L580,542 M640,515 L650,542" stroke="#3b2f2f" stroke-width="3" opacity="0.25" stroke-linecap="round"/>
      <g transform="translate(500,528)">
        <path d="M-18,-8 L6,-8 L-2,0 L10,0 L-12,14 L-6,2 L-18,2 Z" fill="#fef08a" stroke="#3b2f2f" stroke-width="3" stroke-linejoin="round"/>
      </g>
      <text x="605" y="533" font-size="16" class="title" fill="#fefce8" stroke="#3b2f2f" stroke-width="0.6" transform="rotate(-2 605 533)" letter-spacing="1">PELI</text>
    </g>\n'''
    # speed dust puffs
    s += '''<g fill="#e5e7eb" stroke="#3b2f2f" stroke-width="3" opacity="0.9">
      <circle cx="285" cy="585" r="12"/><circle cx="260" cy="595" r="9"/><circle cx="310" cy="598" r="8"/>
    </g>\n'''
    s += '</g>\n'
    return s

def pelican(bob=0, wing_flap=0, scarf_wave=0):
    # bob: vertical offset, wing_flap: rotation deg for raised wing, scarf_wave: control offset
    s = f'<g id="pelican" transform="translate(0,{bob})">\n'
    # ---- motion speed lines behind ----
    s += '''<g stroke="#ffffff" stroke-linecap="round" opacity="0.8">
      <line x1="120" y1="320" x2="300" y2="320" stroke-width="8"/>
      <line x1="90" y1="360" x2="270" y2="360" stroke-width="10"/>
      <line x1="130" y1="400" x2="310" y2="400" stroke-width="7"/>
    </g>\n'''
    # ---- tail ----
    s += '''<g transform="translate(385,390)">
      <path d="M0,0 L-70,-15 L-65,5 L-72,20 L-10,25 Z" fill="#e8dcc3" stroke="#3b2f2f" stroke-width="5" stroke-linejoin="round"/>
      <line x1="-10" y1="8" x2="-60" y2="2" stroke="#3b2f2f" stroke-width="3"/>
    </g>\n'''
    # ---- far leg (darker, behind body) ----
    s += '''<g>
      <path d="M545,460 L550,505 L580,505" fill="none" stroke="#3b2f2f" stroke-width="15" stroke-linecap="round"/>
      <path d="M545,460 L550,505 L580,505" fill="none" stroke="#d97706" stroke-width="9" stroke-linecap="round"/>
      <g transform="translate(598,505)">
        <ellipse cx="0" cy="0" rx="30" ry="12" fill="#f59e0b" stroke="#3b2f2f" stroke-width="4"/>
        <path d="M-8,-3 L18,-8 M-8,0 L20,0 M-8,3 L18,8" stroke="#3b2f2f" stroke-width="2.5" stroke-linecap="round"/>
      </g>
    </g>\n'''
    # ---- body (raised to show legs) ----
    s += '''<ellipse cx="500" cy="380" rx="130" ry="112" fill="url(#bodyG)" class="ol"/>
    <ellipse cx="520" cy="415" rx="75" ry="52" fill="#fef9e7" opacity="0.9"/>
    <ellipse cx="455" cy="330" rx="28" ry="18" fill="white" opacity="0.6"/>\n'''
    # ---- raised wing (balancing, broad and feathery) ----
    s += f'''<g transform="translate(435,315) rotate({-32+wing_flap})">
      <path d="M0,0 C-15,-10 -35,-35 -50,-70 C-65,-105 -75,-145 -60,-175 C-55,-188 -40,-186 -35,-172 C-25,-135 -5,-80 35,-30 C25,-10 10,8 0,0 Z"
        fill="url(#wingG)" class="ol"/>
      <path d="M-38,-60 C-50,-95 -58,-125 -52,-155" fill="none" stroke="#3b2f2f" stroke-width="3" opacity="0.45" stroke-linecap="round"/>
      <path d="M-20,-55 C-28,-85 -32,-115 -28,-140" fill="none" stroke="#3b2f2f" stroke-width="3" opacity="0.35" stroke-linecap="round"/>
    </g>\n'''
    # ---- side wing (tucked, showing feathers) ----
    s += '''<g transform="translate(500,370)">
      <path d="M-20,-50 C-90,-40 -150,-10 -170,40 C-175,55 -165,65 -150,60 C-100,40 -50,20 0,10 Z"
        fill="url(#wingG)" class="ol"/>
      <path d="M-40,-35 C-80,-25 -120,-5 -145,25" fill="none" stroke="#3b2f2f" stroke-width="3.5" stroke-linecap="round"/>
      <path d="M-35,-15 C-75,-5 -110,10 -135,30" fill="none" stroke="#3b2f2f" stroke-width="3.5" stroke-linecap="round"/>
      <path d="M-120,15 q15,12 30,5 q15,10 28,2" fill="none" stroke="#3b2f2f" stroke-width="3" stroke-linecap="round"/>
    </g>\n'''
    # ---- scarf flowing behind ----
    w = scarf_wave
    s += f'''<g>
      <path d="M548,282 C480,270 {380+w},250 315,275 C300,280 298,295 312,304 L330,312 L318,322 C310,330 318,342 332,340 C400,330 {470+w},325 542,318 Z"
        fill="#ef4444" class="ol"/>
      <path d="M548,282 C480,270 {380+w},250 315,275" fill="none" stroke="#fca5a5" stroke-width="4" opacity="0.6" stroke-linecap="round"/>
      <g stroke="#7f1d1d" stroke-width="3" stroke-linecap="round" opacity="0.7">
        <line x1="335" y1="285" x2="330" y2="308"/>
        <line x1="352" y1="283" x2="348" y2="308"/>
      </g>
      <ellipse cx="548" cy="300" rx="30" ry="24" fill="#dc2626" class="ol"/>
      <path d="M535,290 q13,10 0,20" fill="none" stroke="#7f1d1d" stroke-width="3" stroke-linecap="round"/>
    </g>\n'''
    # ---- neck ----
    s += '''<path d="M540,300 C570,260 590,235 600,195 L660,195 C655,245 630,285 590,320 L540,320 Z"
      fill="url(#bodyG)" class="ol"/>\n'''
    # ---- near leg (in front) ----
    s += '''<g>
      <path d="M485,465 L490,505 L520,505" fill="none" stroke="#3b2f2f" stroke-width="17" stroke-linecap="round"/>
      <path d="M485,465 L490,505 L520,505" fill="none" stroke="#fbbf24" stroke-width="10" stroke-linecap="round"/>
      <g transform="translate(538,505)">
        <ellipse cx="0" cy="0" rx="34" ry="14" fill="#fcd34d" stroke="#3b2f2f" stroke-width="4"/>
        <path d="M-10,-4 L20,-9 M-10,0 L22,0 M-10,4 L20,9" stroke="#3b2f2f" stroke-width="2.5" stroke-linecap="round"/>
      </g>
    </g>\n'''
    # ---- head ----
    s += '''<g transform="translate(625,175)">
      <circle r="58" fill="url(#bodyG)" class="ol"/>
      <!-- crest feathers -->
      <g transform="translate(-45,-20) rotate(-25)">
        <ellipse cx="0" cy="0" rx="22" ry="10" fill="white" class="ol-thin"/>
        <ellipse cx="-8" cy="-14" rx="20" ry="9" fill="white" class="ol-thin"/>
      </g>
      <!-- helmet -->
      <g transform="translate(0,-18)">
        <path d="M-58,-5 A58,58 0 0 1 58,-5 L58,5 L-58,5 Z" fill="url(#helmetG)" class="ol"/>
        <rect x="-10" y="-63" width="20" height="58" fill="#fde047" stroke="#3b2f2f" stroke-width="4"/>
        <circle cx="0" cy="-62" r="10" fill="#fde047" stroke="#3b2f2f" stroke-width="4"/>
        <circle cx="-32" cy="-28" r="6" fill="white" opacity="0.5"/>
      </g>
      <path d="M48,18 L58,28 L48,32" fill="none" stroke="#3b2f2f" stroke-width="3" opacity="0.3"/>
      <!-- eye -->
      <ellipse cx="10" cy="-5" rx="16" ry="18" fill="white" stroke="#3b2f2f" stroke-width="4"/>
      <circle cx="13" cy="-4" r="8" fill="#1f2937"/>
      <circle cx="16" cy="-7" r="3" fill="white"/>
      <path d="M-8,-22 Q10,-28 26,-18" fill="none" stroke="#3b2f2f" stroke-width="4" stroke-linecap="round"/>
      <!-- blush -->
      <ellipse cx="-18" cy="12" rx="12" ry="8" fill="#fda4af" opacity="0.8"/>
      <!-- smile -->
      <path d="M-5,22 Q10,26 22,20" fill="none" stroke="#3b2f2f" stroke-width="3.5" stroke-linecap="round"/>
    </g>\n'''
    # ---- beak + pouch (facing right) ----
    s += '''<g transform="translate(670,165)">
      <!-- lower pouch sagging -->
      <path d="M0,20 C60,25 120,40 165,75 C175,83 170,95 158,95 C110,95 50,70 5,55 Z"
        fill="url(#pouchG)" class="ol"/>
      <path d="M20,35 C70,45 120,60 150,80" fill="none" stroke="#7c2d12" stroke-width="3" opacity="0.4" stroke-linecap="round"/>
      <!-- upper beak -->
      <path d="M0,0 C70,5 140,20 195,45 C205,50 205,60 195,60 C130,55 60,35 0,30 Z"
        fill="url(#beakG)" class="ol"/>
      <path d="M0,8 C70,13 135,25 185,45" fill="none" stroke="#fff" stroke-width="4" opacity="0.5" stroke-linecap="round"/>
      <!-- nail tip -->
      <path d="M195,45 C205,50 205,60 195,60 L175,58 C185,55 188,50 185,44 Z" fill="#c2410c" stroke="#3b2f2f" stroke-width="3"/>
    </g>\n'''
    s += '</g>\n'
    return s

def foreground():
    return '''<!-- title badge -->
<g transform="translate(28,28)">
  <rect x="0" y="0" width="300" height="64" rx="16" fill="#ffffff" opacity="0.92" stroke="#3b2f2f" stroke-width="5"/>
  <text x="18" y="28" font-size="22" class="title" fill="#0f766e">PELICAN</text>
  <text x="18" y="50" font-size="18" class="title" fill="#f97316" letter-spacing="2">★ SKATE CLUB ★</text>
  <g transform="translate(265,18)">
    <circle r="14" fill="#fbbf24" stroke="#3b2f2f" stroke-width="3"/>
    <path d="M0,-8 L2,-2 L8,-2 L3,2 L5,8 L0,4 L-5,8 L-3,2 L-8,-2 L-2,-2 Z" fill="#fff"/>
  </g>
</g>
<!-- vignette -->
<rect width="1000" height="700" fill="none" stroke="#3b2f2f" stroke-width="12" opacity="0.15" rx="8"/>
'''

def full_svg_animated():
    return (svg_header() + defs()
        + '<g id="scene">\n'
        + background()
        # animated clouds drift + road dashes? add SMIL on top group for subtle life
        + '</g>\n'
        # shadow + board + pelican with SMIL bob
        + '''<g>
          <animateTransform attributeName="transform" type="translate" values="0 0; 0 -10; 0 0" keyTimes="0;0.5;1" dur="1.2s" repeatCount="indefinite"/>
        '''
        + skateboard(animated=True) + pelican()
        + '</g>\n'
        # overlay SMIL for wheels spin: we wrap wheels? simpler: CSS rotation
        + '''<style>
          #skateboard { animation: none; }
        </style>\n'''
        + foreground()
        + animated_extras()
        + '</svg>\n')

def animated_extras():
    return '''
<g stroke="white" stroke-linecap="round" opacity="0.8">
  <animate attributeName="opacity" values="0.8;0.2;0.8" dur="1.2s" repeatCount="indefinite"/>
  <line x1="120" y1="320" x2="300" y2="320" stroke-width="8"/>
  <line x1="90" y1="360" x2="270" y2="360" stroke-width="10"/>
</g>
'''

def full_svg_frame(t):
    # t in [0,1): bob = sin, wing = sin, wheel angle, cloud shift, scarf
    bob = -10 * math.sin(t*2*math.pi)
    wing = 10 * math.sin(t*2*math.pi)
    wheel = t*360*2  # 2 rotations per loop
    cloud = (t*60) % 60 - 30
    scarf = 20*math.sin(t*2*math.pi)
    return (svg_header() + defs() + background(cloud_shift=cloud)
        + skateboard(wheel_angle=wheel)
        + pelican(bob=bob, wing_flap=wing, scarf_wave=scarf)
        + foreground() + '</svg>\n')

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    open(OUT_SVG, "w").write(full_svg_animated())
    print(f"wrote {OUT_SVG} ({os.path.getsize(OUT_SVG)} bytes)")
