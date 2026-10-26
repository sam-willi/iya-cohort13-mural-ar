"""Draws images/workshop.svg, the background behind the start and end screens.

It's original vector art in the style of the mural concept (reference/): chunky woodcut browns with rough ink edges,
ochre pillars, white unpainted gaps, sketch-style cream objects with brown hatching, a spiral staircase up to an arched
window with two silhouettes, the tall sky window with its hanging I-Y-A mobile and two red figures on a balcony,
an hourglass on a pillar, glowing lanterns, lamps casting light, cubby shelves and the giant magnifying glass.

Edit this file, not the SVG, then run:  python3 tools/make-workshop-svg.py
The picture is 900 x 1400. Phones show roughly x 130-770 (the badge covers the middle), wide screens y 300-1100.
"""
import math
from pathlib import Path

W, H = 900, 1400
OUT = Path(__file__).resolve().parent.parent / "images" / "workshop.svg"

INK = "#1b120b"
C = {
    "gap": "#f6ecda", "wood_dd": "#2a170b", "wood_d": "#4a2a14", "wood": "#7a4a22", "wood_l": "#a8692c",
    "ochre": "#d98f2b", "ochre_l": "#f0b24a", "amber": "#f6c45a", "sky": "#a9d6ee", "sky_l": "#e2f2fb",
    "stone": "#9fb4c2", "crimson": "#c8173a", "pink": "#f2a6c4", "violet": "#8f8fd8", "sun": "#fbe48a",
    "sketch": "#f1e6d0", "sketch_line": "#8a6440", "rim": "#8a2a1e", "gold": "#f2c230",
}
out = []
add = out.append


# ---------------------------------------------------------------- shape helpers (return path data)

def rect(x, y, w, h, r=0):
    if not r:
        return f"M{x} {y}h{w}v{h}h{-w}Z"
    return (f"M{x + r} {y}h{w - 2 * r}a{r} {r} 0 0 1 {r} {r}v{h - 2 * r}a{r} {r} 0 0 1 {-r} {r}"
            f"h{-(w - 2 * r)}a{r} {r} 0 0 1 {-r} {-r}v{-(h - 2 * r)}a{r} {r} 0 0 1 {r} {-r}Z")


def ellipse(cx, cy, rx, ry=None):
    ry = rx if ry is None else ry
    return f"M{cx - rx} {cy}a{rx} {ry} 0 1 0 {2 * rx} 0a{rx} {ry} 0 1 0 {-2 * rx} 0Z"


def poly(*pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


# ---------------------------------------------------------------- drawing helpers

def wood(d, fill=None, grain="grain-h", ink=4):
    """A woodcut wooden shape: flat fill, a little grain, thick rough ink edge."""
    fill = fill or C["wood"]
    add(f'<path d="{d}" fill="{fill}"/>')
    add(f'<path d="{d}" fill="url(#{grain})"/>')
    add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{ink}" stroke-linejoin="round"/>')


def sketch(*ds, fill=None):
    """A sketch-style object part: cream, hatched, brown pencil outline (like the concept's unrendered objects)."""
    for d in ds:
        add(f'<path d="{d}" fill="{fill or C["sketch"]}"/>')
        add(f'<path d="{d}" fill="url(#hatch)"/>')
        add(f'<path d="{d}" fill="none" stroke="{C["sketch_line"]}" stroke-width="2.5" stroke-linejoin="round"/>')


def line(x1, y1, x2, y2, color=INK, width=3):
    add(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')


def glow(cx, cy, r, strength=1):
    add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#glow)" opacity="{strength}"/>')


def gear_path(cx, cy, r, teeth=12):
    pts = []
    for i in range(teeth * 4):
        a = i / (teeth * 4) * 2 * math.pi
        rr = r if i % 4 in (0, 1) else r * 0.84
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly(*pts)


# ---------------------------------------------------------------- header, filters, patterns, gradients

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">')
add(f"""<defs>
  <!-- wobbles every edge a little, for a hand-cut woodcut look -->
  <filter id="rough" x="-2%" y="-2%" width="104%" height="104%">
    <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7"/>
    <feDisplacementMap in="SourceGraphic" scale="5"/>
  </filter>
  <pattern id="grain-h" width="120" height="22" patternUnits="userSpaceOnUse">
    <path d="M0 6 Q30 2 60 6 T120 6 M0 15 Q40 19 80 15 T120 16" fill="none" stroke="{INK}" stroke-opacity=".18" stroke-width="2"/>
  </pattern>
  <pattern id="grain-v" width="22" height="120" patternUnits="userSpaceOnUse">
    <path d="M6 0 Q2 30 6 60 T6 120 M15 0 Q19 40 15 80 T16 120" fill="none" stroke="{INK}" stroke-opacity=".18" stroke-width="2"/>
  </pattern>
  <pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
    <path d="M0 0V9" stroke="{C['sketch_line']}" stroke-opacity=".35" stroke-width="1.3"/>
  </pattern>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8fc8e8"/><stop offset=".55" stop-color="{C['sky_l']}"/><stop offset="1" stop-color="#ffffff"/>
  </linearGradient>
  <radialGradient id="glow">
    <stop offset="0" stop-color="#ffe7a3" stop-opacity=".95"/>
    <stop offset=".3" stop-color="{C['ochre_l']}" stop-opacity=".45"/>
    <stop offset="1" stop-color="{C['ochre']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe7a3" stop-opacity=".55"/><stop offset="1" stop-color="#ffe7a3" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="vignette" cx=".5" cy=".45" r=".75">
    <stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".45"/>
  </radialGradient>
  <clipPath id="tall-window"><path d="M318 1150 V120 Q450 30 582 120 V1150 Z"/></clipPath>
  <clipPath id="arch-window"><path d="M40 640 V290 A125 125 0 0 1 290 290 V640 Z"/></clipPath>
</defs>""")

# ---------------------------------------------------------------- back wall and white unpainted gaps

add(f'<rect width="{W}" height="{H}" fill="{C["wood_d"]}"/>')
add('<g filter="url(#rough)">')
wood(rect(0, 0, W, H), C["wood_d"], "grain-v", ink=0)
# the white gaps between structures, a big part of the concept's look
for d in [poly((660, 300), (900, 280), (900, 470), (700, 500)), poly((690, 640), (900, 610), (900, 760), (720, 800)),
          poly((0, 700), (60, 690), (40, 860), (0, 880)), poly((610, 1010), (690, 990), (680, 1110), (600, 1130))]:
    add(f'<path d="{d}" fill="{C["gap"]}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
add("</g>")

# light from the hanging lamps
for lx in (215, 780):
    add(f'<path d="{poly((lx - 40, 170), (lx + 40, 170), (lx + 190, 1180), (lx - 190, 1180))}" fill="url(#beam)"/>')
    glow(lx, 190, 230, 0.9)

add('<g filter="url(#rough)">')

# ---------------------------------------------------------------- the tall sky window (centre)

wood("M296 1170 V115 Q450 5 604 115 V1170 Z", C["ochre"], "grain-v", ink=6)
add('<g clip-path="url(#tall-window)">')
add('<rect x="300" y="0" width="300" height="1160" fill="url(#sky)"/>')
# pale towers and beams seen through the glass, like the concept's grey architecture
for d in [rect(330, 300, 46, 860), rect(520, 380, 60, 780), poly((376, 520), (520, 460), (520, 490), (376, 552)),
          rect(400, 820, 120, 24), poly((470, 140), (500, 100), (530, 140), (530, 360), (470, 360))]:
    add(f'<path d="{d}" fill="{C["stone"]}" opacity=".55"/>')
for cx, cy, s in [(360, 210, 1), (540, 330, .8), (420, 600, 1.1)]:
    add(f'<g transform="translate({cx} {cy}) scale({s})" fill="#fff" opacity=".85"><ellipse rx="56" ry="16"/>'
        '<ellipse cx="-20" cy="-10" rx="24" ry="18"/><ellipse cx="14" cy="-14" rx="28" ry="22"/></g>')
# balcony with two red figures leaning on the rail
wood(poly((300, 760), (600, 730), (600, 770), (300, 800)), C["wood_l"], ink=4)
line(300, 712, 600, 688, INK, 5)
for fx in (395, 470):
    add(f'<path d="M{fx - 18} 772 L{fx - 14} 700 Q{fx} 676 {fx + 14} 700 L{fx + 18} 768 Z" fill="{C["crimson"]}"/>')
    add(f'<circle cx="{fx}" cy="682" r="14" fill="{C["crimson"]}"/>')
add("</g>")

# the hanging mobile: strings, sun, moon, stars, I-Y-A letters, a sketched balloon
for x, y in [(395, 175), (450, 228), (500, 196), (412, 300), (462, 340), (512, 302), (360, 395), (548, 250)]:
    line(x, 105, x, y - 16, "#6b4a2c", 1.5)
add(f'<circle cx="450" cy="244" r="30" fill="{C["sun"]}" stroke="{INK}" stroke-width="3"/>')
add(f'<path d="M386 162 A22 22 0 1 0 412 196 A17 17 0 1 1 386 162 Z" fill="{C["amber"]}" stroke="{INK}" stroke-width="3"/>')
for sx, sy in [(500, 196), (548, 250)]:
    pts = [(sx + (12 if i % 2 == 0 else 5) * math.cos(i * math.pi / 5 - math.pi / 2),
            sy + (12 if i % 2 == 0 else 5) * math.sin(i * math.pi / 5 - math.pi / 2)) for i in range(10)]
    add(f'<path d="{poly(*pts)}" fill="{C["amber"]}" stroke="{INK}" stroke-width="2"/>')
for ch, x, y, col, rot in [("I", 412, 318, C["pink"], -8), ("Y", 462, 358, C["violet"], 6), ("A", 512, 320, C["pink"], -4)]:
    add(f'<text x="{x}" y="{y}" transform="rotate({rot} {x} {y - 14})" text-anchor="middle" font-family="Georgia, serif" '
        f'font-weight="900" font-size="40" fill="{col}" stroke="{INK}" stroke-width="2.5" paint-order="stroke">{ch}</text>')
sketch(ellipse(360, 420, 30, 34), "M343 448 L352 470 H368 L377 448 Z")
sketch(rect(352, 470, 16, 12, 2))
add("</g>")

# ---------------------------------------------------------------- left: arched window, silhouettes, spiral stair

add('<g filter="url(#rough)">')
wood("M20 660 V290 A145 145 0 0 1 310 290 V660 Z", C["wood"], "grain-v", ink=6)
add('<g clip-path="url(#arch-window)">')
add('<rect x="40" y="140" width="250" height="520" fill="url(#sky)"/>')
sketch(poly((88, 640), (98, 470), (128, 470), (138, 640)), rect(92, 440, 42, 30, 4), poly((86, 444), (113, 412), (140, 444)))
add(f'<path d="M96 520 H130 L132 545 H94 Z M93 590 H133 L135 615 H91 Z" fill="{C["crimson"]}" opacity=".7"/>')
sketch(poly((180, 238), (240, 232), (262, 240), (240, 247), (180, 246)), poly((206, 238), (216, 216), (226, 218), (222, 238)))
sketch(rect(110, 300, 50, 14, 3), rect(102, 296, 14, 6, 2), rect(154, 296, 14, 6, 2))  # a little drone
add("</g>")
line(165, 160, 165, 640, INK, 5)
line(40, 420, 290, 420, INK, 5)
# two silhouettes looking out
for fx, h in [(150, 150), (205, 160)]:
    add(f'<path d="M{fx - 20} 650 L{fx - 18} {650 - h + 40} Q{fx} {650 - h + 22} {fx + 18} {650 - h + 40} L{fx + 20} 650 Z" fill="{INK}"/>')
    add(f'<circle cx="{fx}" cy="{650 - h + 18}" r="15" fill="{INK}"/>')
wood(rect(0, 648, 320, 26), C["wood_l"], ink=5)  # landing
# spiral staircase curving down from the landing to the bottom-left
N = 12
outer = [(318 - 190 * (i / N) ** 1.4, 676 + 500 * (i / N)) for i in range(N + 1)]
inner = [(x - (130 + 70 * (i / N)), y + 18 * math.sin(i / N * math.pi)) for i, (x, y) in enumerate(outer)]
for i in range(N):
    wood(poly(inner[i], outer[i], outer[i + 1], inner[i + 1]), C["wood_l"] if i % 2 else C["ochre"], ink=4)
    a, b = inner[i], outer[i]  # dark riser along the top of each step
    add(f'<path d="{poly(a, b, (b[0], b[1] + 12), (a[0], a[1] + 12))}" fill="{C["wood_dd"]}"/>')
rail = [(x + 4, y - 64) for x, y in outer]
for (x, y), (rx, ry) in list(zip(outer, rail))[::2]:
    line(rx, ry, x, y, INK, 4)
pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in rail)
add(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>')
add(f'<polyline points="{pts}" fill="none" stroke="{C["ochre"]}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')
# suitcases stacked under the stairs, and a film camera on a tripod (both in the concept's bottom-left)
sketch(rect(10, 1120, 120, 50, 6), rect(20, 1078, 100, 42, 6), rect(34, 1046, 72, 32, 5))
sketch(rect(56, 1112, 28, 8, 3), rect(60, 1070, 20, 8, 3), rect(62, 1040, 16, 6, 2))
sketch(rect(30, 860, 70, 46, 6), ellipse(38, 852, 18), ellipse(86, 852, 18), rect(100, 872, 26, 18, 3))
for x2 in (36, 64, 94):
    line(65, 906, x2, 1000, C["sketch_line"], 4)
add("</g>")

# ---------------------------------------------------------------- right: ochre pillar with the hourglass, cubby shelves

add('<g filter="url(#rough)">')
wood(rect(612, 0, 70, H), C["ochre"], "grain-v", ink=6)
wood(rect(600, 560, 94, 28), C["ochre_l"], ink=5)
wood(rect(600, 820, 94, 28), C["ochre_l"], ink=5)
glow(647, 700, 120, 0.9)
add(f'<path d="M620 588 H674 M620 820 H674" stroke="{INK}" stroke-width="4"/>')
add(f'<path d="M626 594 C626 650 642 680 642 704 C642 728 626 758 626 814 H668 C668 758 652 728 652 704 C652 680 668 650 668 594 Z" '
    f'fill="#eef8fc" fill-opacity=".9" stroke="{INK}" stroke-width="4"/>')
add(f'<path d="M632 640 C636 670 644 690 645 700 H649 C650 690 658 670 662 640 Z M630 812 C636 770 644 752 647 748 C650 752 658 770 664 812 Z" fill="{C["amber"]}"/>')
# cubbies
for y0, y1 in [(150, 300), (500, 640), (800, 1000)]:
    wood(rect(694, y0, 230, y1 - y0), C["wood_dd"], ink=5)
    wood(rect(694, y1 - 16, 230, 18), C["wood_l"], ink=4)
wood(rect(694, 0, 230, 20), C["wood"], ink=5)
# sketch-style objects on the shelves
sketch(rect(712, 214, 70, 54, 6), rect(722, 222, 40, 36, 4), ellipse(770, 236, 5), ellipse(770, 252, 5))          # old TV
sketch(rect(800, 236, 58, 42, 4), ellipse(829, 236, 14, 16))                                                       # camera
sketch(ellipse(829, 238, 8))
sketch(rect(712, 560, 66, 40, 4), ellipse(730, 580, 11), ellipse(760, 580, 11), rect(724, 552, 42, 8, 2))           # boombox
sketch(rect(812, 556, 34, 34, 4), rect(806, 590, 46, 34, 4), rect(812, 624, 12, 0.1), rect(800, 594, 8, 26, 3), rect(850, 594, 8, 26, 3))  # robot
sketch(ellipse(822, 572, 5), ellipse(836, 572, 5))
sketch(poly((718, 984), (730, 930), (830, 930), (842, 984)), rect(724, 900, 112, 14, 7), rect(752, 868, 56, 34, 2))  # typewriter
for kx in range(738, 830, 14):
    add(f'<circle cx="{kx}" cy="958" r="4" fill="{C["sketch"]}" stroke="{C["sketch_line"]}" stroke-width="1.5"/>')
sketch(ellipse(880, 960, 30, 22), "M906 952 Q930 944 924 930", rect(866, 928, 28, 10, 4))                          # teapot
add("</g>")

# ---------------------------------------------------------------- hanging lamps

add('<g filter="url(#rough)">')
for lx in (215, 780):
    line(lx, 0, lx, 120, INK, 4)
    add(f'<path d="M{lx - 56} 178 Q{lx - 52} 126 {lx} 118 Q{lx + 52} 126 {lx + 56} 178 Z" fill="{C["ochre"]}" stroke="{INK}" stroke-width="5"/>')
    add(f'<ellipse cx="{lx}" cy="182" rx="20" ry="11" fill="#fff6cf" stroke="{INK}" stroke-width="3"/>')
    add(f'<rect x="{lx - 60}" y="172" width="120" height="10" rx="5" fill="{C["wood"]}" stroke="{INK}" stroke-width="3"/>')
add(f'<path d="{gear_path(900, 90, 120, 14)}" fill="{C["wood"]}" stroke="{INK}" stroke-width="5"/>')
add(f'<circle cx="900" cy="90" r="40" fill="{C["wood_dd"]}" stroke="{INK}" stroke-width="4"/>')
add("</g>")

# ---------------------------------------------------------------- the desk, lanterns, papers and the giant magnifying glass

add('<g filter="url(#rough)">')
wood(rect(-10, 1170, W + 20, 40), C["ochre"], ink=6)
wood(rect(-10, 1210, W + 20, 200), C["wood_dd"], ink=6)
for dx in (60, 360, 660):
    wood(rect(dx, 1240, 200, 100, 6), C["wood"], ink=4)
    add(f'<circle cx="{dx + 100}" cy="1290" r="9" fill="{C["ochre_l"]}" stroke="{INK}" stroke-width="3"/>')
# papers and blueprints
for d, rot in [(rect(360, 1140, 170, 34, 2), -3), (rect(500, 1146, 150, 30, 2), 4)]:
    add(f'<g transform="rotate({rot} 450 1160)"><path d="{d}" fill="#fffaf0" stroke="{INK}" stroke-width="3"/></g>')
for i in range(5):
    line(372 + i * 30, 1150, 392 + i * 30, 1164, "#8a7a66", 2)
add("</g>")

for lx, ly in [(205, 1170), (330, 960)]:
    glow(lx, ly - 50, 120)
add('<g filter="url(#rough)">')
for lx, ly in [(205, 1170), (330, 960)]:
    add(f'<rect x="{lx - 24}" y="{ly - 14}" width="48" height="14" rx="3" fill="{C["ochre"]}" stroke="{INK}" stroke-width="3"/>')
    add(f'<rect x="{lx - 18}" y="{ly - 86}" width="36" height="72" rx="4" fill="#ffd96b" stroke="{INK}" stroke-width="4"/>')
    add(f'<path d="M{lx} {ly - 30} C{lx - 9} {ly - 40} {lx - 5} {ly - 54} {lx} {ly - 64} C{lx + 5} {ly - 54} {lx + 9} {ly - 40} {lx} {ly - 30} Z" fill="#fff8dc"/>')
    add(f'<path d="M{lx - 26} {ly - 86} L{lx - 16} {ly - 100} H{lx + 16} L{lx + 26} {ly - 86} Z" fill="{C["ochre"]}" stroke="{INK}" stroke-width="3"/>')
    add(f'<circle cx="{lx}" cy="{ly - 110}" r="9" fill="none" stroke="{INK}" stroke-width="4"/>')
wood(rect(260, 960, 150, 22), C["wood_l"], ink=4)  # little table for the second lantern
# the magnifying glass, leaning on the desk
add(f'<path d="M694 1112 L800 1176" stroke="{INK}" stroke-width="28" stroke-linecap="round"/>')
add(f'<path d="M694 1112 L800 1176" stroke="{C["gold"]}" stroke-width="18" stroke-linecap="round"/>')
add(f'<circle cx="636" cy="1062" r="76" fill="{C["sky"]}"/>')
add('<path d="M590 1040 L622 1008 M584 1066 L640 1012" stroke="#fff" stroke-width="7" stroke-opacity=".8" stroke-linecap="round"/>')
add(f'<circle cx="636" cy="1062" r="76" fill="none" stroke="{INK}" stroke-width="20"/>')
add(f'<circle cx="636" cy="1062" r="76" fill="none" stroke="{C["rim"]}" stroke-width="12"/>')
add("</g>")

add(f'<rect width="{W}" height="{H}" fill="url(#vignette)"/>')
add("</svg>")
OUT.write_text("\n".join(out) + "\n")
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
