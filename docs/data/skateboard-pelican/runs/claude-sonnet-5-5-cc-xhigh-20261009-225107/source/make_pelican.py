#!/usr/bin/env python3
"""Generates output/pelican_skateboard.svg (a pelican riding a skateboard).

Everything is hand-placed vector shapes; the script only computes the leaf-shaped
feather fans for the wings and stitches them into the SVG template.
"""
import math
import os

W, H = 800, 600


def feather(p0, tip, w, tipfrac, fill, tipfill, stroke, sw=1.5):
    """A leaf-shaped feather from p0 to tip with a dark tip section."""
    dx, dy = tip[0] - p0[0], tip[1] - p0[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    mx, my = (p0[0] + tip[0]) / 2, (p0[1] + tip[1]) / 2
    c1 = (mx + nx * w, my + ny * w)
    c2 = (mx - nx * w, my - ny * w)
    body = (f"M{p0[0]:.0f} {p0[1]:.0f} Q{c1[0]:.0f} {c1[1]:.0f} {tip[0]:.0f} {tip[1]:.0f} "
            f"Q{c2[0]:.0f} {c2[1]:.0f} {p0[0]:.0f} {p0[1]:.0f}Z")

    def q(t, c):
        return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * tip[0],
                (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * tip[1])

    n = 8
    a = [q(tipfrac + (1 - tipfrac) * i / n, c1) for i in range(n + 1)]
    b = [q(tipfrac + (1 - tipfrac) * i / n, c2) for i in range(n + 1)]
    pts = a + b[::-1][1:]
    tip_d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    return (f'<path d="{body}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            f'<path d="{tip_d}" fill="{tipfill}"/>')


def fan(p0, tips, w, tipfrac, fill, tipfill, stroke, sw=1.5):
    return "\n    ".join(feather(p0, t, w, tipfrac, fill, tipfill, stroke, sw) for t in tips)


FAR_WING = fan((376, 296),
               [(252, 146), (222, 180), (210, 220), (218, 260), (244, 290)],
               30, 0.55, "#7d8da3", "#2c3645", "#5a6a80", 2)
NEAR_PRIMARIES = fan((396, 372),
                     [(262, 364), (270, 380), (288, 392), (314, 399)],
                     12, 0.5, "#8a9bb1", "#2c3645", "#2c3645", 1.5)

SVG = r'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
  <title>Pelican riding a skateboard</title>
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5fb7e8"/>
      <stop offset="0.65" stop-color="#bfe6f5"/>
      <stop offset="1" stop-color="#ffe9c4"/>
    </linearGradient>
    <radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fffbe0" stop-opacity="1"/>
      <stop offset="0.45" stop-color="#ffe98a" stop-opacity="0.9"/>
      <stop offset="1" stop-color="#ffe98a" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="road" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#6c7480"/>
      <stop offset="1" stop-color="#4b525c"/>
    </linearGradient>
    <linearGradient id="pouch" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f7cf7a"/>
      <stop offset="1" stop-color="#eba24a"/>
    </linearGradient>
    <linearGradient id="bill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffc94d"/>
      <stop offset="1" stop-color="#f29a2e"/>
    </linearGradient>
    <linearGradient id="deck" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#1fb5a8"/>
      <stop offset="1" stop-color="#2a8fd1"/>
    </linearGradient>
    <filter id="soft" x="-20%" y="-100%" width="140%" height="300%">
      <feGaussianBlur stdDeviation="5"/>
    </filter>
    <g id="cloud">
      <ellipse cx="0" cy="20" rx="70" ry="20"/>
      <ellipse cx="-25" cy="5" rx="32" ry="24"/>
      <ellipse cx="22" cy="0" rx="38" ry="28"/>
    </g>
  </defs>

  <!-- sky -->
  <rect width="800" height="600" fill="url(#sky)"/>
  <circle cx="150" cy="120" r="120" fill="url(#sun)"/>
  <circle cx="150" cy="120" r="46" fill="#fff6c2"/>

  <!-- clouds -->
  <g fill="#ffffff">
    <use href="#cloud" transform="translate(540 92)" opacity="0.95"/>
    <use href="#cloud" transform="translate(705 195) scale(0.7)" opacity="0.92"/>
    <use href="#cloud" transform="translate(312 178) scale(0.5)" opacity="0.8"/>
  </g>

  <!-- distant hills -->
  <path d="M0 400 C80 340 170 330 260 380 C340 420 420 340 520 335 C620 330 700 380 800 350 L800 470 L0 470 Z" fill="#8fc7a0"/>
  <path d="M0 430 C100 390 200 400 300 420 C420 440 520 385 640 395 C720 402 770 420 800 415 L800 480 L0 480 Z" fill="#6fb184"/>

  <!-- road -->
  <rect x="0" y="470" width="800" height="130" fill="url(#road)"/>
  <rect x="0" y="470" width="800" height="8" fill="#9aa2ad"/>
  <g fill="#f4efe0" opacity="0.85">
    <polygon points="30,560 130,560 140,572 20,572"/>
    <polygon points="250,560 350,560 360,572 240,572"/>
    <polygon points="470,560 570,560 580,572 460,572"/>
    <polygon points="690,560 790,560 800,572 680,572"/>
  </g>

  <!-- ground shadow -->
  <ellipse cx="400" cy="512" rx="185" ry="9" fill="#1d2229" opacity="0.5" filter="url(#soft)"/>

  <!-- speed lines -->
  <g stroke="#ffffff" stroke-width="5" stroke-linecap="round" opacity="0.85">
    <line x1="40" y1="300" x2="150" y2="300"/>
    <line x1="80" y1="340" x2="200" y2="340"/>
    <line x1="20" y1="385" x2="130" y2="385"/>
    <line x1="110" y1="425" x2="215" y2="425"/>
  </g>

  <!-- dust puffs -->
  <g fill="#e9e2d3" opacity="0.85">
    <circle cx="262" cy="504" r="9"/>
    <circle cx="240" cy="508" r="7"/>
    <circle cx="220" cy="511" r="4.5"/>
  </g>

  <!-- ============ SKATEBOARD ============ -->
  <g id="skateboard">
    <!-- trucks -->
    <rect x="306" y="466" width="30" height="12" rx="3" fill="#8a929c"/>
    <rect x="464" y="466" width="30" height="12" rx="3" fill="#8a929c"/>
    <!-- wheels -->
    <g>
      <circle cx="321" cy="490" r="19" fill="#ff8a3d" stroke="#c9601d" stroke-width="3"/>
      <circle cx="321" cy="490" r="7" fill="#f4efe0"/>
      <circle cx="321" cy="490" r="2.5" fill="#8a929c"/>
      <circle cx="479" cy="490" r="19" fill="#ff8a3d" stroke="#c9601d" stroke-width="3"/>
      <circle cx="479" cy="490" r="7" fill="#f4efe0"/>
      <circle cx="479" cy="490" r="2.5" fill="#8a929c"/>
    </g>
    <!-- deck -->
    <path d="M238 432 C246 454 268 460 296 460 L504 460 C532 460 554 454 562 432 L570 430 C562 468 538 474 504 474 L296 474 C262 474 238 468 230 430 Z" fill="url(#deck)"/>
    <!-- grip tape -->
    <path d="M238 432 C246 454 268 460 296 460 L504 460 C532 460 554 454 562 432 L566 431 C556 452 536 456 504 456 L296 456 C264 456 244 452 234 431 Z" fill="#2b2f36"/>
    <!-- deck stripe -->
    <path d="M262 468 L538 468" stroke="#ffe27a" stroke-width="3" stroke-linecap="round" opacity="0.9"/>
  </g>

  <!-- ============ PELICAN ============ -->
  <g id="pelican" stroke-linejoin="round" stroke-linecap="round">

    <!-- far wing (raised for balance) -->
    <path d="M340 312 C326 276 346 244 392 256 C412 268 408 296 394 312 Z" fill="#7d8da3" stroke="#5a6a80" stroke-width="2"/>
    <g>
    __FAR_WING__
    </g>

    <!-- far leg -->
    <path d="M372 384 L372 392 L354 430 L352 450" fill="none" stroke="#d8761f" stroke-width="11"/>
    <path d="M338 449 L378 452 Q392 456 386 458 L380 458 L340 458 Q334 456 338 449 Z" fill="#d8761f" stroke="#d8761f" stroke-width="2"/>

    <!-- near leg -->
    <path d="M422 384 L424 396 L448 432 L448 450" fill="none" stroke="#f08c2e" stroke-width="11"/>
    <path d="M434 449 L484 452 Q500 457 492 459 L486 459 L436 458 Q430 456 434 449 Z" fill="#f08c2e" stroke="#f08c2e" stroke-width="2"/>
    <path d="M456 453 L480 457 M446 454 L462 458" stroke="#b8601a" stroke-width="1.8" fill="none"/>

    <!-- tail -->
    <path d="M300 352 L244 374 L260 354 L240 346 L282 322 Z" fill="#dfe6ee" stroke="#aebccc" stroke-width="2.5"/>

    <!-- neck outline (behind body) -->
    <path d="M432 322 C420 262 488 250 488 190" fill="none" stroke="#aebccc" stroke-width="50"/>

    <!-- body -->
    <path d="M478 300 C505 340 478 408 400 410 C345 412 305 392 262 374 C292 352 292 316 322 292 C362 262 440 258 478 300 Z" fill="#ffffff" stroke="#aebccc" stroke-width="2.5"/>
    <!-- chest tint -->
    <path d="M470 312 C488 350 460 396 405 402 C440 380 452 340 470 312 Z" fill="#fff3d4" opacity="0.9"/>

    <!-- neck -->
    <path d="M432 322 C420 262 488 250 488 190" fill="none" stroke="#ffffff" stroke-width="46"/>
    <path d="M466 268 C474 246 470 230 468 214" fill="none" stroke="#e8eef5" stroke-width="3" opacity="0.8"/>

    <!-- head -->
    <circle cx="496" cy="178" r="32" fill="#ffffff" stroke="#aebccc" stroke-width="2.5"/>
    <circle cx="496" cy="178" r="30" fill="#ffffff"/>

    <!-- pouch -->
    <path d="M512 204 C536 284 648 274 690 226 Z" fill="url(#pouch)" stroke="#c7772a" stroke-width="2.5"/>
    <path d="M532 224 C558 266 622 262 652 234" fill="none" stroke="#c7772a" stroke-width="2" opacity="0.5"/>

    <!-- bill (upper) -->
    <path d="M512 166 L690 210 C703 214 702 228 688 228 L512 204 Z" fill="url(#bill)" stroke="#c7772a" stroke-width="2.5"/>
    <path d="M520 176 L676 214" stroke="#ffe39a" stroke-width="4" opacity="0.8" fill="none"/>
    <path d="M512 204 L688 227" stroke="#b9661f" stroke-width="2.5" fill="none"/>
    <path d="M688 210 C700 212 703 222 694 226" fill="none" stroke="#9a4d12" stroke-width="3"/>
    <circle cx="536" cy="178" r="2" fill="#9a4d12"/>

    <!-- eye -->
    <circle cx="507" cy="172" r="8" fill="#fff8e1" stroke="#e0a63a" stroke-width="2"/>
    <circle cx="509" cy="172" r="4.5" fill="#1b1b1f"/>
    <circle cx="510.5" cy="170.5" r="1.6" fill="#ffffff"/>

    <!-- helmet -->
    <path d="M462 166 C460 136 484 122 506 127 C524 132 532 150 530 164 C510 157 484 158 462 166 Z" fill="#e8413c" stroke="#a82723" stroke-width="2.5"/>
    <path d="M480 131 C492 146 494 154 492 160" fill="none" stroke="#ffffff" stroke-width="5" opacity="0.85"/>
    <path d="M462 166 C484 158 510 157 530 164" fill="none" stroke="#a82723" stroke-width="3"/>

    <!-- near wing (folded) -->
    <g>
    __NEAR_PRIMARIES__
    </g>
    <path d="M440 300 C470 330 452 374 384 386 C346 392 322 378 292 372 C318 358 336 322 362 302 C390 284 420 284 440 300 Z" fill="#a9b9cc" stroke="#6c7e95" stroke-width="2.5"/>
    <!-- wing coverts -->
    <path d="M427 308 C442 328 430 354 398 362" fill="none" stroke="#8597ad" stroke-width="2.5"/>
    <path d="M394 300 C414 320 406 348 374 360" fill="none" stroke="#8597ad" stroke-width="2.5"/>
    <path d="M364 312 C380 328 370 350 344 360" fill="none" stroke="#8597ad" stroke-width="2.5"/>

  </g>
</svg>
'''

svg = SVG.replace("__FAR_WING__", FAR_WING).replace("__NEAR_PRIMARIES__", NEAR_PRIMARIES)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "pelican_skateboard.svg")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    f.write(svg)
print("wrote", out)
