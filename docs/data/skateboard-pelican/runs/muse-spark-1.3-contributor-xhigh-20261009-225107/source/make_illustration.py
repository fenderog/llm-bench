#!/usr/bin/env python3
"""Generate pelican-on-skateboard SVG illustration (still + animated frames) v2."""
import math

W, H = 1600, 1200

def svg_string(frame=0, total_frames=48, animated=False):
    phase = 2*math.pi*frame/max(1,total_frames)
    bob = 12*math.sin(phase) if animated else 0
    cx1 = 18*math.sin(phase*0.7) if animated else 0
    cx2 = -22*math.sin(phase*0.5+1) if animated else 0
    cx3 = 14*math.sin(phase*0.6+2) if animated else 0
    wheel_angle = (frame/total_frames)*720 if animated else 24
    scarf_w = 12*math.sin(phase*1.5) if animated else 0
    wing_flap = 3*math.sin(phase) if animated else 0
    dust_s = 1+0.08*math.sin(phase*2) if animated else 1
    speed_op = 0.65+0.25*math.sin(phase*2+0.5) if animated else 0.8

    def wheel_spokes(cx, cy, r, ang_deg):
        s = []
        for k in range(3):
            a = math.radians(ang_deg + k*60)
            x2 = cx + r*math.cos(a)
            y2 = cy + r*math.sin(a)
            x1 = cx - r*math.cos(a)
            y1 = cy - r*math.sin(a)
            s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#B91C2E" stroke-width="7" stroke-linecap="round" opacity="0.9"/>')
        return "".join(s)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#2FA8DE"/><stop offset="0.45" stop-color="#7ED2F5"/><stop offset="0.75" stop-color="#D6F0FF"/><stop offset="1" stop-color="#FFF3C2"/>
</linearGradient>
<linearGradient id="seaGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#2FB3D6"/><stop offset="1" stop-color="#1B7FA8"/>
</linearGradient>
<linearGradient id="sandGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#F9E7AE"/><stop offset="1" stop-color="#EAC07E"/>
</linearGradient>
<linearGradient id="roadGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#D7DEE6"/><stop offset="0.18" stop-color="#C2CAD3"/><stop offset="1" stop-color="#9AA4B0"/>
</linearGradient>
<radialGradient id="sunGlow" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#FFF7B0" stop-opacity="0.95"/><stop offset="0.4" stop-color="#FFE86B" stop-opacity="0.55"/><stop offset="1" stop-color="#FFE86B" stop-opacity="0"/>
</radialGradient>
<radialGradient id="sunCore" cx="0.35" cy="0.35" r="0.9">
<stop offset="0" stop-color="#FFFDE0"/><stop offset="0.55" stop-color="#FFE86B"/><stop offset="1" stop-color="#FFB62E"/>
</radialGradient>
<linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#FFFFFF"/><stop offset="0.65" stop-color="#F1F6FA"/><stop offset="1" stop-color="#D7E3EE"/>
</linearGradient>
<linearGradient id="wingGrad" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#6B7E99"/><stop offset="0.5" stop-color="#46566E"/><stop offset="1" stop-color="#2A3446"/>
</linearGradient>
<linearGradient id="wingFarGrad" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#8A9BB5"/><stop offset="1" stop-color="#5A6B84"/>
</linearGradient>
<linearGradient id="beakGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#FFC14D"/><stop offset="0.5" stop-color="#FF9F1C"/><stop offset="1" stop-color="#E87E00"/>
</linearGradient>
<linearGradient id="pouchGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#FFD9A0"/><stop offset="0.6" stop-color="#FFB26B"/><stop offset="1" stop-color="#F08A3C"/>
</linearGradient>
<linearGradient id="deckGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#3ED6C6"/><stop offset="0.5" stop-color="#14B0A0"/><stop offset="1" stop-color="#0B7E73"/>
</linearGradient>
<linearGradient id="trunkGrad" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#8A5A33"/><stop offset="0.5" stop-color="#A97446"/><stop offset="1" stop-color="#6E4425"/>
</linearGradient>
<linearGradient id="leafGrad" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#4ADE80"/><stop offset="1" stop-color="#15803D"/>
</linearGradient>
<filter id="softBlur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
</defs>

<!-- SKY -->
<rect x="0" y="0" width="1600" height="780" fill="url(#skyGrad)"/>
<circle cx="1290" cy="210" r="240" fill="url(#sunGlow)"/>
<g stroke="#D99A00" stroke-width="10" stroke-linecap="round" opacity="0.55">
<line x1="1290" y1="25" x2="1290" y2="60"/>
<line x1="1420" y1="75" x2="1397" y2="100"/>
<line x1="1475" y1="210" x2="1440" y2="210"/>
<line x1="1420" y1="345" x2="1397" y2="320"/>
<line x1="1160" y1="75" x2="1183" y2="100"/>
</g>
<circle cx="1290" cy="210" r="108" fill="url(#sunCore)" stroke="#2F3A4A" stroke-width="7"/>
<ellipse cx="1255" cy="180" rx="38" ry="24" fill="#FFFFFF" opacity="0.65"/>
<!-- clouds -->
<g opacity="0.98">
<g transform="translate({300+cx1},165)">
<ellipse cx="0" cy="20" rx="120" ry="42" fill="#B9D9EE" opacity="0.9"/>
<ellipse cx="-70" cy="0" rx="70" ry="48" fill="#FFFFFF"/><ellipse cx="0" cy="-18" rx="90" ry="58" fill="#FFFFFF"/><ellipse cx="75" cy="0" rx="68" ry="46" fill="#FFFFFF"/><ellipse cx="10" cy="18" rx="110" ry="38" fill="#FFFFFF"/>
</g>
<g transform="translate({800+cx2},125)">
<ellipse cx="0" cy="22" rx="95" ry="34" fill="#B9D9EE" opacity="0.9"/>
<ellipse cx="-55" cy="0" rx="55" ry="38" fill="#FFFFFF"/><ellipse cx="5" cy="-16" rx="70" ry="46" fill="#FFFFFF"/><ellipse cx="60" cy="2" rx="52" ry="36" fill="#FFFFFF"/>
</g>
<g transform="translate({1050+cx3},460)">
<ellipse cx="0" cy="18" rx="80" ry="28" fill="#B9D9EE" opacity="0.9"/>
<ellipse cx="-40" cy="0" rx="44" ry="30" fill="#FFFFFF"/><ellipse cx="10" cy="-12" rx="55" ry="36" fill="#FFFFFF"/><ellipse cx="50" cy="0" rx="40" ry="28" fill="#FFFFFF"/>
</g>
</g>
<g fill="none" stroke="#2F3A4A" stroke-width="6" stroke-linecap="round" opacity="0.75">
<path d="M 500 245 q 18 -18 36 0 q 18 -18 36 0"/>
<path d="M 600 295 q 14 -14 28 0 q 14 -14 28 0"/>
<path d="M 950 235 q 14 -14 28 0 q 14 -14 28 0"/>
</g>

<!-- SEA -->
<rect x="0" y="720" width="1600" height="125" fill="url(#seaGrad)"/>
<rect x="0" y="720" width="1600" height="10" fill="#FFFFFF" opacity="0.7"/>
<g stroke="#FFFFFF" stroke-width="6" stroke-linecap="round" opacity="0.55" fill="none">
<path d="M 150 770 q 25 -14 50 0 t 50 0 t 50 0"/>
<path d="M 550 795 q 25 -14 50 0 t 50 0 t 50 0"/>
<path d="M 950 770 q 25 -14 50 0 t 50 0 t 50 0"/>
<path d="M 1250 795 q 25 -14 50 0 t 50 0"/>
</g>
<!-- SAND -->
<rect x="0" y="845" width="1600" height="115" fill="url(#sandGrad)"/>
<ellipse cx="250" cy="890" rx="90" ry="12" fill="#D9A95F" opacity="0.35"/>
<ellipse cx="1360" cy="895" rx="110" ry="13" fill="#D9A95F" opacity="0.35"/>
<g>
<ellipse cx="330" cy="882" rx="55" ry="12" fill="#000000" opacity="0.12"/>
<rect x="327" y="812" width="6" height="60" fill="#8A5A33"/>
<path d="M 265 817 Q 330 772 395 817 Q 330 837 265 817 Z" fill="#FF5964" stroke="#2F3A4A" stroke-width="5" stroke-linejoin="round"/>
<path d="M 298 808 Q 330 784 362 808" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round"/>
<circle cx="425" cy="877" r="18" fill="#3ED6C6" stroke="#2F3A4A" stroke-width="5"/>
<path d="M 413 865 L 437 889 M 437 865 L 413 889" stroke="#2F3A4A" stroke-width="4" stroke-linecap="round"/>
</g>

<!-- PALMS (pushed outward to frame, clear of beak) -->
<g>
<path d="M 95 960 Q 110 750 155 510" fill="none" stroke="#2F3A4A" stroke-width="54" stroke-linecap="round"/>
<path d="M 95 960 Q 110 750 155 510" fill="none" stroke="url(#trunkGrad)" stroke-width="38" stroke-linecap="round"/>
<path d="M 108 900 Q 118 800 132 700" fill="none" stroke="#C99A63" stroke-width="10" stroke-linecap="round" opacity="0.8"/>
<g transform="translate(155,510)">
<g fill="url(#leafGrad)" stroke="#1E4D2B" stroke-width="6" stroke-linejoin="round">
<path d="M 0 0 Q -90 -40 -170 -20 Q -90 10 0 0 Z"/>
<path d="M 0 0 Q -70 -90 -140 -110 Q -80 -50 0 0 Z"/>
<path d="M 0 0 Q -10 -100 30 -150 Q 40 -60 0 0 Z"/>
<path d="M 0 0 Q 70 -70 140 -70 Q 70 -20 0 0 Z"/>
<path d="M 0 0 Q 90 -10 160 30 Q 70 30 0 0 Z"/>
</g>
<circle cx="-18" cy="18" r="20" fill="#6E4425" stroke="#2F3A4A" stroke-width="5"/>
<circle cx="18" cy="20" r="18" fill="#7A4E2B" stroke="#2F3A4A" stroke-width="5"/>
</g>
<path d="M 1510 960 Q 1495 760 1452 550" fill="none" stroke="#2F3A4A" stroke-width="54" stroke-linecap="round"/>
<path d="M 1510 960 Q 1495 760 1452 550" fill="none" stroke="url(#trunkGrad)" stroke-width="38" stroke-linecap="round"/>
<g transform="translate(1452,550)">
<g fill="url(#leafGrad)" stroke="#1E4D2B" stroke-width="6" stroke-linejoin="round">
<path d="M 0 0 Q 90 -40 170 -20 Q 90 10 0 0 Z"/>
<path d="M 0 0 Q 70 -90 140 -110 Q 80 -50 0 0 Z"/>
<path d="M 0 0 Q 10 -100 -30 -150 Q -40 -60 0 0 Z"/>
<path d="M 0 0 Q -70 -70 -140 -70 Q -70 -20 0 0 Z"/>
<path d="M 0 0 Q -90 -10 -160 30 Q -70 30 0 0 Z"/>
</g>
<circle cx="18" cy="18" r="20" fill="#6E4425" stroke="#2F3A4A" stroke-width="5"/>
<circle cx="-18" cy="20" r="18" fill="#7A4E2B" stroke="#2F3A4A" stroke-width="5"/>
</g>
</g>

<!-- ROAD -->
<rect x="0" y="960" width="1600" height="240" fill="url(#roadGrad)"/>
<rect x="0" y="960" width="1600" height="14" fill="#2F3A4A" opacity="0.9"/>
<rect x="0" y="974" width="1600" height="6" fill="#FFD93D" opacity="0.9"/>
<g stroke="#7A8591" stroke-width="5" opacity="0.55">
<line x1="220" y1="1020" x2="220" y2="1200"/><line x1="1350" y1="1020" x2="1350" y2="1200"/>
</g>
<g fill="#8A94A0" opacity="0.5">
<ellipse cx="180" cy="1100" rx="10" ry="5"/><ellipse cx="520" cy="1130" rx="14" ry="6"/><ellipse cx="1330" cy="1120" rx="12" ry="5"/>
</g>
<g stroke="#2F8A4A" stroke-width="7" stroke-linecap="round" fill="none">
<path d="M 60 1170 Q 70 1130 55 1110 M 80 1170 Q 90 1135 100 1115 M 100 1170 Q 105 1140 120 1125"/>
<path d="M 1520 1175 Q 1530 1135 1515 1115 M 1540 1175 Q 1550 1140 1560 1120"/>
</g>
<g>
<circle cx="95" cy="1115" r="10" fill="#FF5964" stroke="#2F3A4A" stroke-width="4"/><circle cx="122" cy="1128" r="8" fill="#FFD93D" stroke="#2F3A4A" stroke-width="4"/>
<circle cx="1535" cy="1125" r="9" fill="#FFFFFF" stroke="#2F3A4A" stroke-width="4"/><circle cx="1552" cy="1140" r="7" fill="#FF9F1C" stroke="#2F3A4A" stroke-width="4"/>
</g>

<!-- SPEED LINES (kept left, clear of bird) -->
<g stroke="#FFFFFF" stroke-linecap="round" opacity="{speed_op:.2f}">
<line x1="150" y1="560" x2="360" y2="560" stroke-width="14"/>
<line x1="110" y1="650" x2="370" y2="650" stroke-width="18"/>
<line x1="160" y1="745" x2="360" y2="745" stroke-width="12"/>
<line x1="130" y1="830" x2="330" y2="830" stroke-width="10" opacity="0.7"/>
</g>

<!-- SHADOW -->
<ellipse cx="830" cy="1088" rx="370" ry="32" fill="#000000" opacity="0.22" filter="url(#softBlur)"/>

<!-- ===== RIDER ===== -->
<g transform="translate(0,{bob:.1f})">
<!-- dust -->
<g transform="translate(520,1030) scale({dust_s:.3f})" opacity="0.95">
<g fill="#F8ECD0" stroke="#2F3A4A" stroke-width="6">
<circle cx="-70" cy="-10" r="34"/><circle cx="-25" cy="-28" r="42"/><circle cx="25" cy="-12" r="30"/><circle cx="-45" cy="22" r="26"/>
</g>
<circle cx="-30" cy="-32" r="12" fill="#FFFFFF" opacity="0.9"/>
<circle cx="-130" cy="10" r="10" fill="#F8ECD0" stroke="#2F3A4A" stroke-width="5"/>
<circle cx="-160" cy="-20" r="7" fill="#F8ECD0" stroke="#2F3A4A" stroke-width="4"/>
</g>
<!-- far wheels -->
<g opacity="0.95">
<circle cx="710" cy="1028" r="38" fill="#8E1E28" stroke="#2F3A4A" stroke-width="7"/>
<circle cx="1020" cy="1028" r="38" fill="#8E1E28" stroke="#2F3A4A" stroke-width="7"/>
</g>
<!-- FAR WING (soft, behind) -->
<g transform="rotate({-6+wing_flap:.1f} 780 620)">
<path d="M 780 640 Q 700 520 640 400 Q 615 345 580 315 Q 560 298 547 313 Q 534 328 550 350 L 620 470 Q 640 500 670 520 L 760 620 Z" fill="url(#wingFarGrad)" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
</g>
<!-- TAIL (white with dark tips, lower) -->
<path d="M 630 680 L 500 660 Q 478 658 478 676 Q 478 694 500 696 L 545 700 L 505 725 Q 486 738 498 753 Q 510 768 528 758 L 640 720 Z" fill="#FFFFFF" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<path d="M 505 665 L 478 663 Q 478 676 500 678 Z M 510 730 L 490 740 Q 498 753 515 745 Z" fill="#46566E"/>
<!-- NECK chunky -->
<path d="M 880 690 Q 950 570 1005 420" fill="none" stroke="#2F3A4A" stroke-width="132" stroke-linecap="round"/>
<path d="M 880 690 Q 950 570 1005 420" fill="none" stroke="#FFFFFF" stroke-width="108" stroke-linecap="round"/>
<path d="M 915 680 Q 975 570 1025 440" fill="none" stroke="#D7E3EE" stroke-width="24" stroke-linecap="round" opacity="0.9"/>
<!-- BODY -->
<ellipse cx="775" cy="675" rx="200" ry="160" fill="url(#bodyGrad)" stroke="#2F3A4A" stroke-width="8" transform="rotate(-8 775 675)"/>
<ellipse cx="795" cy="730" rx="128" ry="80" fill="#D9E6F2" opacity="0.95"/>
<ellipse cx="705" cy="610" rx="70" ry="50" fill="#FFFFFF" opacity="0.95"/>
<g stroke="#CBD8E4" stroke-width="5" stroke-linecap="round" opacity="0.9" fill="none">
<path d="M 660 690 Q 700 710 750 705"/><path d="M 650 720 Q 700 740 760 735"/>
</g>
<!-- MAIN WING smoother, less finger-like -->
<g transform="rotate({wing_flap:.1f} 770 640)">
<path d="M 790 660 Q 660 600 540 470 Q 470 395 410 310 Q 392 287 370 296 Q 348 305 360 328 L 410 410 Q 430 445 465 465 L 620 625 Q 700 675 790 660 Z" fill="url(#wingGrad)" stroke="#2F3A4A" stroke-width="8" stroke-linejoin="round"/>
<path d="M 620 620 Q 540 550 470 460" stroke="#1D2735" stroke-width="7" stroke-linecap="round" opacity="0.65" fill="none"/>
<path d="M 650 650 Q 580 590 520 520" stroke="#1D2735" stroke-width="6" stroke-linecap="round" opacity="0.5" fill="none"/>
<path d="M 560 480 Q 510 420 470 360" stroke="#FFFFFF" stroke-width="9" stroke-linecap="round" opacity="0.28" fill="none"/>
<path d="M 410 410 Q 395 415 390 430 Q 405 445 425 445" fill="none" stroke="#2F3A4A" stroke-width="6" stroke-linecap="round"/>
</g>
<!-- SCARF in front of wing, around neck -->
<path d="M 975 480 Q 860 435 {745+scarf_w:.0f} 470 Q 640 500 {545+scarf_w:.0f} 455 Q 522 445 518 467 Q 514 489 542 499 Q 645 540 760 508 Q 865 482 975 515 Z" fill="#FF4757" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<g stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" opacity="0.9">
<line x1="815" y1="472" x2="800" y2="500"/>
<line x1="695" y1="487" x2="680" y2="515"/>
</g>
<circle cx="975" cy="497" r="30" fill="#E63946" stroke="#2F3A4A" stroke-width="7"/>
<path d="M 958 484 Q 975 498 992 484" stroke="#2F3A4A" stroke-width="5" fill="none" stroke-linecap="round"/>
<!-- LEGS (behind board) -->
<path d="M 750 800 L 705 930" stroke="#2F3A4A" stroke-width="42" stroke-linecap="round"/>
<path d="M 750 800 L 705 930" stroke="#FF9F1C" stroke-width="26" stroke-linecap="round"/>
<path d="M 890 800 L 960 930" stroke="#2F3A4A" stroke-width="42" stroke-linecap="round"/>
<path d="M 890 800 L 960 930" stroke="#FF9F1C" stroke-width="26" stroke-linecap="round"/>

<!-- SKATEBOARD chunky -->
<g>
<path d="M 555 930 L 1105 930 Q 1150 930 1152 953 Q 1154 976 1110 979 L 570 979 Q 528 979 526 955 Q 524 930 555 930 Z" fill="url(#deckGrad)" stroke="#2F3A4A" stroke-width="8" stroke-linejoin="round"/>
<rect x="526" y="945" width="626" height="18" fill="#C98A5B" stroke="#2F3A4A" stroke-width="5"/>
<rect x="555" y="930" width="550" height="11" fill="#2F3A4A" opacity="0.92"/>
<g>
<path d="M 815 983 L 858 983 L 837 999 L 875 999 L 822 1020 L 833 1003 L 808 1003 Z" fill="#FFD93D" stroke="#2F3A4A" stroke-width="4" stroke-linejoin="round"/>
</g>
<rect x="685" y="979" width="64" height="18" rx="4" fill="#9AA4B0" stroke="#2F3A4A" stroke-width="5"/>
<path d="M 695 997 L 739 997 L 730 1022 L 704 1022 Z" fill="#CBD3DB" stroke="#2F3A4A" stroke-width="5" stroke-linejoin="round"/>
<line x1="665" y1="1017" x2="769" y2="1017" stroke="#2F3A4A" stroke-width="10" stroke-linecap="round"/>
<rect x="995" y="979" width="64" height="18" rx="4" fill="#9AA4B0" stroke="#2F3A4A" stroke-width="5"/>
<path d="M 1005 997 L 1049 997 L 1040 1022 L 1014 1022 Z" fill="#CBD3DB" stroke="#2F3A4A" stroke-width="5" stroke-linejoin="round"/>
<line x1="975" y1="1017" x2="1079" y2="1017" stroke="#2F3A4A" stroke-width="10" stroke-linecap="round"/>
<g>
<circle cx="700" cy="1045" r="52" fill="#FF5964" stroke="#2F3A4A" stroke-width="8"/>
{wheel_spokes(700,1045,30,wheel_angle)}
<circle cx="700" cy="1045" r="20" fill="#FFFFFF" stroke="#2F3A4A" stroke-width="6"/>
<circle cx="700" cy="1045" r="7" fill="#2F3A4A"/>
<ellipse cx="681" cy="1026" rx="15" ry="10" fill="#FFFFFF" opacity="0.75"/>
<circle cx="1030" cy="1045" r="52" fill="#FF5964" stroke="#2F3A4A" stroke-width="8"/>
{wheel_spokes(1030,1045,30,wheel_angle+30)}
<circle cx="1030" cy="1045" r="20" fill="#FFFFFF" stroke="#2F3A4A" stroke-width="6"/>
<circle cx="1030" cy="1045" r="7" fill="#2F3A4A"/>
<ellipse cx="1011" cy="1026" rx="15" ry="10" fill="#FFFFFF" opacity="0.75"/>
</g>
<g fill="none" stroke="#2F3A4A" stroke-width="6" stroke-linecap="round" opacity="0.32">
<path d="M 636 1080 Q 700 1100 764 1080"/><path d="M 966 1080 Q 1030 1100 1094 1080"/>
</g>
</g>
<!-- FEET on top of deck -->
<g>
<path d="M 630 912 Q 705 892 780 912 L 790 948 Q 710 966 625 948 Z" fill="#FF9F1C" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<path d="M 670 916 L 670 944 M 708 914 L 708 946 M 744 916 L 744 944" stroke="#2F3A4A" stroke-width="5" stroke-linecap="round"/>
<path d="M 885 912 Q 960 892 1035 912 L 1045 948 Q 965 966 880 948 Z" fill="#FF9F1C" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<path d="M 925 916 L 925 944 M 963 914 L 963 946 M 999 916 L 999 944" stroke="#2F3A4A" stroke-width="5" stroke-linecap="round"/>
</g>

<!-- HEAD bigger -->
<g>
<circle cx="1045" cy="375" r="108" fill="url(#bodyGrad)" stroke="#2F3A4A" stroke-width="8"/>
<ellipse cx="1010" cy="340" rx="30" ry="22" fill="#FFFFFF" opacity="0.9"/>
<!-- upper beak thicker, shorter -->
<path d="M 1100 345 Q 1215 370 1305 455 Q 1315 465 1307 476 Q 1299 487 1287 480 Q 1200 435 1088 392 Z" fill="url(#beakGrad)" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<!-- pouch fuller -->
<path d="M 1095 390 Q 1170 480 1235 575 Q 1265 595 1298 573 Q 1320 550 1312 478 Q 1210 438 1095 390 Z" fill="url(#pouchGrad)" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<g stroke="#C96A1E" stroke-width="4" opacity="0.55" fill="none" stroke-linecap="round">
<path d="M 1155 475 Q 1182 508 1205 535"/><path d="M 1188 460 Q 1210 492 1228 518"/>
</g>
<path d="M 1280 448 Q 1298 460 1307 476 Q 1295 484 1282 477 Q 1273 466 1280 448 Z" fill="#C25700" stroke="#2F3A4A" stroke-width="5" stroke-linejoin="round"/>
<line x1="1112" y1="360" x2="1265" y2="430" stroke="#E87E00" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
<!-- helmet bigger -->
<path d="M 945 355 Q 938 245 1045 240 Q 1152 245 1142 355 Q 1092 328 1045 328 Q 995 328 945 355 Z" fill="#00B5B8" stroke="#2F3A4A" stroke-width="7" stroke-linejoin="round"/>
<path d="M 972 295 Q 995 265 1035 260" stroke="#FFFFFF" stroke-width="11" stroke-linecap="round" opacity="0.7" fill="none"/>
<g fill="#0B7E73" stroke="#2F3A4A" stroke-width="5">
<ellipse cx="1002" cy="302" rx="13" ry="9"/><ellipse cx="1045" cy="294" rx="13" ry="9"/><ellipse cx="1088" cy="302" rx="13" ry="9"/>
</g>
<path d="M 945 355 L 958 392 M 1142 355 L 1132 390" stroke="#2F3A4A" stroke-width="7" stroke-linecap="round"/>
<path d="M 958 392 Q 1010 415 1088 392" fill="none" stroke="#2F3A4A" stroke-width="6" stroke-linecap="round"/>
<!-- sunglasses -->
<g transform="rotate(-6 1050 358)">
<rect x="986" y="326" width="135" height="68" rx="28" fill="#1A1A2E" stroke="#2F3A4A" stroke-width="6"/>
<line x1="1012" y1="336" x2="996" y2="382" stroke="#7ED2F5" stroke-width="11" stroke-linecap="round" opacity="0.9"/>
<line x1="1036" y1="336" x2="1020" y2="382" stroke="#7ED2F5" stroke-width="6" stroke-linecap="round" opacity="0.7"/>
<line x1="986" y1="348" x2="956" y2="342" stroke="#2F3A4A" stroke-width="8" stroke-linecap="round"/>
</g>
<ellipse cx="998" cy="415" rx="20" ry="11" fill="#FF9AAE" opacity="0.7"/>
<!-- fluffy nape under helmet -->
<path d="M 955 360 Q 935 375 940 395 Q 955 390 965 375 Z" fill="#FFFFFF" stroke="#2F3A4A" stroke-width="5" stroke-linejoin="round"/>
</g>
</g>

<!-- sparkles -->
<g fill="#FFFFFF" opacity="0.9">
<circle cx="1365" cy="630" r="8"/><circle cx="1392" cy="660" r="5"/>
<path d="M 1445 695 l 6 14 14 6 -14 6 -6 14 -6 -14 -14 -6 14 -6 Z"/>
<path d="M 200 720 l 5 11 11 5 -11 5 -5 11 -5 -11 -11 -5 11 -5 Z"/>
</g>
<rect x="0" y="0" width="1600" height="1200" fill="none" stroke="#2F3A4A" stroke-width="18" opacity="0.12"/>
</svg>'''
    return svg

if __name__ == "__main__":
    import pathlib
    pathlib.Path("output").mkdir(exist_ok=True)
    pathlib.Path("output/pelican-skateboard.svg").write_text(svg_string(), encoding="utf-8")
    print("wrote v2", len(svg_string()))
