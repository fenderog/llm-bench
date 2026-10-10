#!/usr/bin/env python3
"""Generate the pelican-on-skateboard SVG (still + animation frames)."""
import math, os

W, H = 800, 600

def svg_frame(t=0.0):
    """Render one frame at time t (seconds)."""
    # motion parameters
    bob = 6 * math.sin(2 * math.pi * 2 * t)          # pelican body bob
    tilt = 3 * math.sin(2 * math.pi * 1 * t + 1.0)   # board tilt (degrees)
    wheel_rot = (t * 720) % 360                       # wheels spin fast
    cloud_x = -(t * 60) % 900                         # clouds drift left
    leg_bend = 4 * math.sin(2 * math.pi * 2 * t + math.pi)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#7ec8f7"/>
      <stop offset="0.7" stop-color="#bfe6ff"/>
      <stop offset="1" stop-color="#e8f7ff"/>
    </linearGradient>
    <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#9aa3ad"/>
      <stop offset="1" stop-color="#6f7883"/>
    </linearGradient>
    <radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fff7c0"/>
      <stop offset="0.7" stop-color="#ffd94d"/>
      <stop offset="1" stop-color="#ffcf2e"/>
    </radialGradient>
    <linearGradient id="deck" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e2574c"/>
      <stop offset="1" stop-color="#b23a30"/>
    </linearGradient>
    <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#dde4ea"/>
    </linearGradient>
  </defs>

  <!-- sky -->
  <rect width="{W}" height="{H}" fill="url(#sky)"/>
  <circle cx="660" cy="95" r="52" fill="url(#sun)"/>

  <!-- clouds (drifting) -->
  <g opacity="0.9" transform="translate({cloud_x:.1f} 0)">
    <g fill="#ffffff">
      <ellipse cx="{140+900}" cy="110" rx="55" ry="22"/>
      <ellipse cx="{180+900}" cy="98" rx="40" ry="20"/>
      <ellipse cx="140" cy="110" rx="55" ry="22"/>
      <ellipse cx="180" cy="98" rx="40" ry="20"/>
      <ellipse cx="{420+900}" cy="170" rx="65" ry="24"/>
      <ellipse cx="{470+900}" cy="158" rx="42" ry="20"/>
      <ellipse cx="420" cy="170" rx="65" ry="24"/>
      <ellipse cx="470" cy="158" rx="42" ry="20"/>
    </g>
  </g>

  <!-- distant hills -->
  <path d="M0 430 Q 120 360 260 425 T 520 420 T 800 428 V 460 H 0 Z" fill="#a8d8b9"/>
  <path d="M0 445 Q 180 400 380 445 T 800 440 V 470 H 0 Z" fill="#8cc7a1"/>

  <!-- ground / street -->
  <rect x="0" y="460" width="{W}" height="140" fill="url(#ground)"/>
  <rect x="0" y="460" width="{W}" height="6" fill="#565f69"/>
  <g stroke="#f2e8c9" stroke-width="6" stroke-dasharray="46 34" transform="translate({(-t*240)%80:.1f} 0)">
    <line x1="-80" y1="545" x2="900" y2="545"/>
  </g>

  <!-- speed lines -->
  <g stroke="#ffffff" stroke-linecap="round" opacity="0.85">
    <line x1="{60 - (t*300)%50:.0f}" y1="330" x2="{170 - (t*300)%50:.0f}" y2="330" stroke-width="7"/>
    <line x1="{30 - (t*260)%60:.0f}" y1="368" x2="{130 - (t*260)%60:.0f}" y2="368" stroke-width="6"/>
    <line x1="{70 - (t*340)%45:.0f}" y1="404" x2="{190 - (t*340)%45:.0f}" y2="404" stroke-width="7"/>
  </g>

  <!-- shadow under board -->
  <ellipse cx="400" cy="498" rx="185" ry="16" fill="#000000" opacity="0.22"/>

  <!-- ================= SKATEBOARD + PELICAN ================= -->
  <g transform="translate(0 {bob:.2f})">
    <g transform="rotate({tilt:.2f} 400 470)">

      <!-- board deck -->
      <path d="M225 468 Q 205 468 205 460 Q 205 452 228 452 L 572 452 Q 595 452 595 460 Q 595 468 575 468 Z"
            fill="url(#deck)"/>
      <rect x="228" y="452" width="344" height="4" fill="#ffffff" opacity="0.35"/>
      <!-- grip tape stripe -->
      <rect x="250" y="452" width="300" height="3" fill="#3a3f45" opacity="0.5"/>

      <!-- trucks -->
      <rect x="255" y="468" width="16" height="10" rx="3" fill="#c9ced4"/>
      <rect x="529" y="468" width="16" height="10" rx="3" fill="#c9ced4"/>

      <!-- wheels (spinning) -->
      <g transform="translate(263 486)">
        <circle r="15" fill="#2f343a"/>
        <circle r="7" fill="#f4b942"/>
        <g transform="rotate({wheel_rot:.1f})">
          <line x1="-7" y1="0" x2="7" y2="0" stroke="#2f343a" stroke-width="3"/>
          <line x1="0" y1="-7" x2="0" y2="7" stroke="#2f343a" stroke-width="3"/>
        </g>
      </g>
      <g transform="translate(537 486)">
        <circle r="15" fill="#2f343a"/>
        <circle r="7" fill="#f4b942"/>
        <g transform="rotate({wheel_rot:.1f})">
          <line x1="-7" y1="0" x2="7" y2="0" stroke="#2f343a" stroke-width="3"/>
          <line x1="0" y1="-7" x2="0" y2="7" stroke="#2f343a" stroke-width="3"/>
        </g>
      </g>

      <!-- ===== pelican ===== -->
      <g>
        <!-- tail feathers -->
        <path d="M282 372 Q 240 358 226 386 Q 250 384 262 396 Q 244 400 240 414 Q 268 410 292 398 Z"
              fill="#c7d0d8" stroke="#9aa5b1" stroke-width="3"/>

        <!-- legs -->
        <g stroke="#f49e28" stroke-width="12" stroke-linecap="round" fill="none">
          <path d="M352 400 L {346+leg_bend:.1f} 434 L 344 450"/>
          <path d="M406 402 L {402+leg_bend:.1f} 436 L 402 450"/>
        </g>
        <!-- webbed feet -->
        <path d="M330 450 h34 l-6 8 h-30 z" fill="#f49e28"/>
        <path d="M388 450 h34 l-6 8 h-30 z" fill="#f49e28"/>

        <!-- body -->
        <ellipse cx="382" cy="352" rx="105" ry="72" fill="url(#body)" stroke="#9aa5b1" stroke-width="3.5"/>
        <!-- belly shading -->
        <path d="M290 372 Q 380 430 476 378 Q 460 420 382 424 Q 310 424 290 372 Z" fill="#e7ecf1"/>

        <!-- wing (outstretched for balance) -->
        <path d="M368 330 Q 300 268 214 262 Q 258 296 252 322 Q 288 312 316 336 Q 342 356 372 352 Z"
              fill="#eef2f6" stroke="#9aa5b1" stroke-width="3.5" stroke-linejoin="round"/>
        <g stroke="#b7c0ca" stroke-width="3" fill="none" stroke-linecap="round">
          <path d="M250 288 Q 292 300 322 326"/>
          <path d="M240 302 Q 286 314 312 340"/>
        </g>

        <!-- neck -->
        <path d="M440 306 Q 458 262 492 246 Q 512 238 522 250 L 506 292 Q 486 322 458 332 Z"
              fill="url(#body)" stroke="#9aa5b1" stroke-width="3.5"/>

        <!-- head -->
        <g>
          <circle cx="516" cy="248" r="34" fill="url(#body)" stroke="#9aa5b1" stroke-width="3.5"/>
        <!-- helmet (safety first!) : dome over top of head -->
        <path d="M486 238 A 30 30 0 0 1 546 238 L 546 244 Q 516 236 486 244 Z"
              fill="#4f8ef7" stroke="#2f66c4" stroke-width="3" stroke-linejoin="round"/>
        <path d="M486 238 Q 516 230 546 238 L 546 244 Q 516 236 486 244 Z" fill="#2f66c4"/>
        <!-- chin strap -->
        <path d="M492 244 Q 504 268 514 274" stroke="#2f66c4" stroke-width="3" fill="none" stroke-linecap="round"/>
        <g>
          <!-- eye -->
          <circle cx="530" cy="246" r="6.5" fill="#22262b"/>
          <circle cx="532" cy="244" r="2.2" fill="#ffffff"/>
          <!-- blush of excitement -->
          <circle cx="512" cy="260" r="6" fill="#f7a6a0" opacity="0.7"/>

          <!-- big beak + pouch -->
          <path d="M544 240 L 640 262 Q 650 266 640 272 L 552 264 Z"
                fill="#f9b53f" stroke="#d98f22" stroke-width="3" stroke-linejoin="round"/>
          <path d="M548 258 Q 596 316 640 272 L 552 264 Z"
                fill="#fcc967" stroke="#d98f22" stroke-width="3" stroke-linejoin="round"/>
          <!-- beak line -->
          <path d="M546 254 Q 596 266 641 266" stroke="#d98f22" stroke-width="2.5" fill="none"/>
          <!-- tiny fish tail poking out of pouch tip -->
          <path d="M634 274 q 10 8 6 20 q 8 -6 10 -16 q -9 4 -16 -4 z" fill="#5aa9e6" stroke="#3d7cb3" stroke-width="2"/>
        </g>

        </g>
      </g>
    </g>
  </g>

  <!-- little pebbles / sparks behind wheels -->
  <g fill="#4a525b" opacity="0.6">
    <circle cx="{150 - (t*420)%120:.0f}" cy="492" r="4"/>
    <circle cx="{110 - (t*380)%140:.0f}" cy="500" r="3"/>
  </g>

  <!-- title -->
  <text x="400" y="570" text-anchor="middle" font-family="Helvetica, Arial, sans-serif"
        font-size="24" font-weight="bold" fill="#ffffff" opacity="0.9">Pelican Skate Co.</text>
</svg>
'''

if __name__ == "__main__":
    os.makedirs("build", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    # still (t = nice pose)
    with open("output/pelican_skateboard.svg", "w") as f:
        f.write(svg_frame(t=0.06))
    print("wrote output/pelican_skateboard.svg")
