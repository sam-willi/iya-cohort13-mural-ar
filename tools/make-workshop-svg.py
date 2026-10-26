"""Draws images/workshop.svg, the background behind the start and end screens.

Original vector art closely following the mural concept (reference/): a grand staircase climbing to a huge round
window where two silhouettes look out at the sky, with a hanging I-Y-A mobile and two red figures on a balcony;
curving ochre handrails; woodcut browns with heavy black shadows, orange streaks and ragged white gaps; shelves in
perspective with a ladder; lamps on chains throwing yellow light; a round clock; lanterns with glowing halos; an
hourglass on a pillar; a desk of papers with the giant magnifying glass; and, I Spy style, dozens of small
things hidden on every surface (marbles, dice, letter blocks, sneakers, a padlock...). Objects are fully rendered.

Edit this file, not the SVG, then run:  python3 tools/make-workshop-svg.py
The picture is 900 x 1400. Phones show roughly x 130-770 with the badge over y 300-840; wide screens show y 300-1100.
"""
import math
import random
from pathlib import Path

W, H = 900, 1400
OUT = Path(__file__).resolve().parent.parent / "images" / "workshop.svg"
rnd = random.Random(13)

INK = "#140b05"
C = {
    "gap": "#fbf6ec", "wood_dd": "#2a160a", "wood_d": "#4a2812", "wood": "#6e3d18", "wood_l": "#9a5a22",
    "ochre": "#d9862a", "ochre_l": "#f0a830", "amber": "#f6c45a", "sky": "#a9d6ee", "sky_l": "#e2f2fb",
    "stone": "#8fb0c4", "crimson": "#c8173a", "red_glow": "#d9452b", "pink": "#f2a6c4", "violet": "#8f8fd8",
    "sun": "#fbe48a", "cream": "#f6ecd8", "rim": "#8a1a1a", "gold": "#f2c230", "metal": "#b9c3cb",
    "metal_d": "#6e7a84", "black": "#2b2420", "green": "#2f6f4f", "blue": "#2a6f9e", "leather": "#8b4a24",
    "tan": "#c98a4a", "glass": "#3f6c7e",
}
out = []
add = out.append


# ---------------------------------------------------------------- shapes (path data)

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

def wood(d, fill=None, ink=6, streaks=True):
    """Woodcut wood: flat brown, orange streak highlights, heavy rough black edge."""
    add(f'<path d="{d}" fill="{fill or C["wood"]}"/>')
    if streaks:
        add(f'<path d="{d}" fill="url(#streaks)"/>')
    if ink:
        add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{ink}" stroke-linejoin="round"/>')


def part(d, fill, ink=3.5):
    """One part of a rendered object: colour, soft light from the top-left, ink outline."""
    add(f'<path d="{d}" fill="{fill}"/>')
    add(f'<path d="{d}" fill="url(#shade)"/>')
    add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{ink}" stroke-linejoin="round"/>')


def shine(x1, y1, x2, y2, width=4):
    add(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="#fff" stroke-opacity=".75" stroke-width="{width}" stroke-linecap="round"/>')


def line(x1, y1, x2, y2, color=INK, width=3):
    add(f'<path d="M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')


def gap(d):
    """A white unpainted gap with a ragged black brush edge."""
    add(f'<g filter="url(#torn)"><path d="{d}" fill="{C["gap"]}" stroke="{INK}" stroke-width="9" stroke-linejoin="round"/></g>')


def halo(cx, cy, r, red=False):
    """A lamp's glow drawn the concept's way: soft light plus a few painted rings."""
    add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{"redglow" if red else "glow"})"/>')
    for k, op in ((0.45, .35), (0.7, .22), (0.95, .12)):
        add(f'<circle cx="{cx}" cy="{cy}" r="{r * k:.0f}" fill="none" stroke="{C["red_glow"] if red else C["ochre_l"]}" '
            f'stroke-opacity="{op}" stroke-width="5"/>')


def lantern(x, y, s=1.0):
    """A glowing lantern standing at (x, y)."""
    add(f'<g transform="translate({x} {y}) scale({s})">')
    part(rect(-22, -12, 44, 12, 3), C["ochre"], ink=3)
    add(f'<rect x="-17" y="-80" width="34" height="68" rx="4" fill="#ffd96b" stroke="{INK}" stroke-width="4"/>')
    add('<path d="M0 -28 C-9 -38 -5 -52 0 -62 C5 -52 9 -38 0 -28 Z" fill="#fff8dc"/>')
    line(-7, -80, -7, -12, INK, 2)
    line(7, -80, 7, -12, INK, 2)
    part(poly((-24, -80), (-14, -94), (14, -94), (24, -80)), C["ochre"], ink=3)
    add(f'<circle cx="0" cy="-104" r="8" fill="none" stroke="{INK}" stroke-width="4"/>')
    add("</g>")


def gear_path(cx, cy, r, teeth=12):
    pts = []
    for i in range(teeth * 4):
        a = i / (teeth * 4) * 2 * math.pi
        rr = r if i % 4 in (0, 1) else r * 0.84
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly(*pts)


# ---------------------------------------------------------------- small hidden things, I Spy style
# Each is drawn about 40 units across around (0, 0); place() positions, turns and sizes it.

def place(draw, x, y, s=1.0, rot=0):
    add(f'<g transform="translate({x:.0f} {y:.0f}) rotate({rot}) scale({s})">')
    draw()
    add("</g>")


def marble(col):
    def d():
        part(ellipse(0, 0, 11), col, ink=2.5)
        add(f'<path d="M-6 3 Q0 -8 6 2" fill="none" stroke="#fff" stroke-opacity=".7" stroke-width="3"/>')
    return d


def die():
    part(rect(-14, -14, 28, 28, 6), "#fbf8f1", ink=2.5)
    for dx, dy in ((-6, -6), (0, 0), (6, 6)):
        add(f'<circle cx="{dx}" cy="{dy}" r="2.6" fill="{INK}"/>')


def block(letter, col):
    def d():
        part(rect(-16, -16, 32, 32, 3), "#e9c48a", ink=2.5)
        add(f'<rect x="-12" y="-12" width="24" height="24" fill="none" stroke="{col}" stroke-width="2.5"/>')
        add(f'<text y="8" text-anchor="middle" font-family="Georgia, serif" font-weight="900" font-size="22" fill="{col}">{letter}</text>')
    return d


def toy_car():
    part("M-24 4 L-20 -6 L-8 -8 L-2 -16 H12 L18 -8 L24 -6 V4 Z", C["crimson"], ink=2.5)
    part(rect(-1, -14, 11, 6, 1), C["glass"], ink=1.5)
    for wx in (-13, 14):
        add(f'<circle cx="{wx}" cy="5" r="6" fill="{C["black"]}" stroke="{INK}" stroke-width="2"/>')
        add(f'<circle cx="{wx}" cy="5" r="2" fill="{C["metal"]}"/>')


def sneaker():
    part("M-22 6 V-6 Q-18 -14 -8 -12 L4 -4 Q16 -2 22 2 V6 Z", C["blue"], ink=2.5)
    add(f'<path d="M-22 6 H22 V10 H-22 Z" fill="#fff" stroke="{INK}" stroke-width="2"/>')
    for k in range(3):
        line(-8 + k * 5, -9 + k * 2, -4 + k * 5, -3 + k * 2, "#fff", 2)


def sunglasses():
    for cx in (-10, 10):
        part(ellipse(cx, 0, 9, 7), C["black"], ink=2.5)
    line(-1, -2, 1, -2, INK, 3)
    line(-19, -2, -24, -5, INK, 3)
    line(19, -2, 24, -5, INK, 3)
    shine(-13, -3, -10, -5, 2)


def umbrella():
    part("M-4 -22 L4 -22 L7 14 L-7 14 Z", C["green"], ink=2.5)
    add(f'<path d="M0 14 V22 Q0 28 -6 26" fill="none" stroke="{INK}" stroke-width="3"/>')
    line(0, -22, 0, -28, INK, 3)


def padlock():
    add(f'<path d="M-9 -2 V-10 A9 9 0 0 1 9 -10 V-2" fill="none" stroke="{C["metal_d"]}" stroke-width="5"/>')
    add(f'<path d="M-9 -2 V-10 A9 9 0 0 1 9 -10 V-2" fill="none" stroke="{INK}" stroke-width="1.5"/>')
    part(rect(-13, -3, 26, 20, 3), C["gold"], ink=2.5)
    add(f'<circle cx="0" cy="6" r="2.5" fill="{INK}"/>')


def key():
    part(ellipse(-12, 0, 7), C["gold"], ink=2.5)
    add(f'<circle cx="-12" cy="0" r="2.5" fill="{C["wood_d"]}"/>')
    part("M-5 -2.5 H18 V2.5 H14 V7 H10 V2.5 H-5 Z", C["gold"], ink=2)


def headphones():
    add(f'<path d="M-15 4 V-2 A15 15 0 0 1 15 -2 V4" fill="none" stroke="{INK}" stroke-width="6"/>')
    add(f'<path d="M-15 4 V-2 A15 15 0 0 1 15 -2 V4" fill="none" stroke="{C["crimson"]}" stroke-width="3"/>')
    for cx in (-15, 15):
        part(rect(cx - 6, 0, 12, 16, 5), C["black"], ink=2.5)


def trumpet():
    part("M-24 -3 H6 L20 -12 V12 L6 3 H-24 Z", C["gold"], ink=2.5)
    for vx in (-12, -6, 0):
        part(rect(vx - 2, -10, 4, 8, 1), C["gold"], ink=1.5)
    part(rect(-28, -4, 5, 8, 1), C["gold"], ink=1.5)


def frying_pan():
    part(ellipse(-6, 0, 15, 11), C["black"], ink=2.5)
    add(f'<ellipse cx="-6" cy="0" rx="10" ry="7" fill="{C["metal_d"]}"/>')
    part(rect(8, -3, 18, 6, 3), C["wood_l"], ink=2)


def flashlight():
    part(rect(-18, -5, 24, 10, 3), C["blue"], ink=2.5)
    part("M6 -8 H16 V8 H6 Z", C["metal"], ink=2.5)
    add(f'<path d="M16 -6 L34 -14 V14 L16 6 Z" fill="#fff3b0" opacity=".7"/>')


def comb():
    part(rect(-18, -6, 36, 6, 2), C["crimson"], ink=2)
    for k in range(-16, 18, 4):
        line(k, 0, k, 7, C["crimson"], 2)


def toothbrush():
    part(rect(-20, -2.5, 32, 5, 2.5), C["violet"], ink=2)
    part(rect(8, -8, 12, 6, 1.5), "#fff", ink=1.5)


def duck():
    part(ellipse(0, 4, 14, 10), C["gold"], ink=2.5)
    part(ellipse(8, -8, 8), C["gold"], ink=2.5)
    add(f'<path d="M14 -8 L22 -6 L14 -4 Z" fill="{C["ochre"]}" stroke="{INK}" stroke-width="1.5"/>')
    add(f'<circle cx="9" cy="-10" r="1.8" fill="{INK}"/>')


def spool(col):
    def d():
        part(rect(-10, -12, 20, 24, 2), col, ink=2.5)
        part(rect(-13, -15, 26, 5, 2), C["wood_l"], ink=2)
        part(rect(-13, 10, 26, 5, 2), C["wood_l"], ink=2)
    return d


def pencil(col):
    def d():
        part(rect(-20, -3.5, 30, 7, 1), col, ink=2)
        add(f'<path d="M10 -3.5 L20 0 L10 3.5 Z" fill="#f3d9a8" stroke="{INK}" stroke-width="2"/>')
        part(rect(-24, -3.5, 5, 7, 1), C["pink"], ink=1.5)
    return d


def coin():
    part(ellipse(0, 0, 9), C["gold"], ink=2.5)
    add(f'<circle cx="0" cy="0" r="5" fill="none" stroke="{C["ochre"]}" stroke-width="1.5"/>')


# ---------------------------------------------------------------- defs

streaks = " ".join(
    f"M{rnd.randint(0, 200)} {rnd.randint(0, 200)} l{rnd.randint(18, 60)} {rnd.randint(-4, 4)}" for _ in range(26))
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">')
add(f"""<defs>
  <filter id="rough" x="-3%" y="-3%" width="106%" height="106%">
    <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="7"/>
    <feDisplacementMap in="SourceGraphic" scale="7"/>
  </filter>
  <filter id="torn" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.06" numOctaves="3" seed="3"/>
    <feDisplacementMap in="SourceGraphic" scale="16"/>
  </filter>
  <pattern id="streaks" width="200" height="200" patternUnits="userSpaceOnUse">
    <path d="{streaks}" stroke="{C['ochre_l']}" stroke-opacity=".45" stroke-width="4" stroke-linecap="round"/>
  </pattern>
  <linearGradient id="shade" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/>
    <stop offset="1" stop-color="#000" stop-opacity=".35"/>
  </linearGradient>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8fc8e8"/><stop offset=".6" stop-color="{C['sky_l']}"/><stop offset="1" stop-color="#ffffff"/>
  </linearGradient>
  <radialGradient id="glow">
    <stop offset="0" stop-color="#ffe7a3" stop-opacity=".95"/><stop offset=".35" stop-color="{C['ochre_l']}" stop-opacity=".45"/>
    <stop offset="1" stop-color="{C['ochre']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="redglow">
    <stop offset="0" stop-color="#ffd27a" stop-opacity=".95"/><stop offset=".35" stop-color="{C['red_glow']}" stop-opacity=".5"/>
    <stop offset="1" stop-color="{C['red_glow']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe066" stop-opacity=".75"/><stop offset="1" stop-color="#ffe066" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="vignette" cx=".5" cy=".45" r=".75">
    <stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".5"/>
  </radialGradient>
  <clipPath id="round-window"><circle cx="450" cy="500" r="318"/></clipPath>
</defs>""")

# ---------------------------------------------------------------- back wall, shadows, white gaps

add(f'<rect width="{W}" height="{H}" fill="{C["wood_d"]}"/>')
add('<g filter="url(#rough)">')
wood(rect(0, 0, W, H), C["wood_d"], ink=0)
for d in [poly((0, 0), (900, 0), (900, 60), (0, 120)), poly((0, 900), (120, 860), (60, 1400), (0, 1400))]:
    add(f'<path d="{d}" fill="{INK}" opacity=".85"/>')  # heavy black shadows
add("</g>")
for d in [poly((660, 300), (900, 270), (900, 420), (700, 450)), poly((0, 420), (120, 400), (110, 600), (0, 640)),
          poly((700, 650), (900, 620), (900, 700), (720, 730)), poly((690, 1080), (900, 1040), (900, 1110), (700, 1140))]:
    gap(d)

# ---------------------------------------------------------------- ceiling beams and a gear

add('<g filter="url(#rough)">')
for d in [poly((0, 40), (900, -20), (900, 30), (0, 95)), poly((0, 170), (380, 120), (380, 150), (0, 205)),
          poly((520, 115), (900, 150), (900, 185), (520, 145))]:
    wood(d, C["wood"], ink=6)
add(f'<path d="{gear_path(880, 300, 110, 14)}" fill="{C["wood"]}" stroke="{INK}" stroke-width="6"/>')
add(f'<circle cx="880" cy="300" r="38" fill="{C["wood_dd"]}" stroke="{INK}" stroke-width="5"/>')
add("</g>")

# ---------------------------------------------------------------- the round window (behind the badge)

add('<g filter="url(#rough)">')
add(f'<circle cx="450" cy="500" r="346" fill="{C["ochre"]}" stroke="{INK}" stroke-width="9"/>')
add(f'<circle cx="450" cy="500" r="346" fill="url(#streaks)"/>')
add("</g>")
add('<g clip-path="url(#round-window)">')
add('<rect x="120" y="170" width="660" height="660" fill="url(#sky)"/>')
for d in [rect(190, 470, 60, 400), rect(640, 420, 70, 450), poly((250, 640), (640, 560), (640, 590), (250, 672)),
          poly((560, 260), (585, 215), (610, 260), (610, 520), (560, 520))]:
    add(f'<path d="{d}" fill="{C["stone"]}" opacity=".5"/>')
add(f'<path d="M140 520 Q450 380 760 520" fill="none" stroke="{C["stone"]}" stroke-width="10" opacity=".6"/>')
for cx, cy, s in [(250, 300, 1.1), (660, 370, .9), (300, 560, 1)]:
    add(f'<g transform="translate({cx} {cy}) scale({s})" fill="#fff" opacity=".9"><ellipse rx="56" ry="16"/>'
        '<ellipse cx="-20" cy="-10" rx="24" ry="18"/><ellipse cx="14" cy="-14" rx="28" ry="22"/></g>')
# a lighthouse and a little plane far off
part(poly((214, 840), (222, 700), (246, 700), (254, 840)), "#fbf7ee", ink=3)
add(f'<path d="M220 740 H248 L250 762 H218 Z M216 800 H252 L254 822 H214 Z" fill="{C["crimson"]}"/>')
part(rect(218, 678, 32, 24, 3), C["amber"], ink=3)
part(poly((212, 682), (234, 656), (256, 682)), C["crimson"], ink=3)
part(poly((600, 300), (650, 295), (668, 302), (650, 309), (600, 308)), C["cream"], ink=3)
part(poly((622, 300), (630, 282), (640, 284), (636, 300)), C["blue"], ink=2.5)
# the hanging mobile: sun, moon, stars, I-Y-A letters, a little balloon
for x, y in [(395, 205), (450, 250), (505, 215), (412, 290), (462, 318), (512, 292), (340, 352), (560, 268)]:
    line(x, 150, x, y - 16, "#6b4a2c", 1.5)
add(f'<circle cx="450" cy="266" r="30" fill="{C["sun"]}" stroke="{INK}" stroke-width="3"/>')
add(f'<path d="M386 192 A22 22 0 1 0 412 226 A17 17 0 1 1 386 192 Z" fill="{C["amber"]}" stroke="{INK}" stroke-width="3"/>')
for sx, sy in [(505, 215), (560, 268)]:
    pts = [(sx + (12 if i % 2 == 0 else 5) * math.cos(i * math.pi / 5 - math.pi / 2),
            sy + (12 if i % 2 == 0 else 5) * math.sin(i * math.pi / 5 - math.pi / 2)) for i in range(10)]
    add(f'<path d="{poly(*pts)}" fill="{C["amber"]}" stroke="{INK}" stroke-width="2"/>')
for ch, x, y, col, rot in [("I", 412, 308, C["pink"], -8), ("Y", 462, 338, C["violet"], 6), ("A", 512, 310, C["pink"], -4)]:
    add(f'<text x="{x}" y="{y}" transform="rotate({rot} {x} {y - 14})" text-anchor="middle" font-family="Georgia, serif" '
        f'font-weight="900" font-size="40" fill="{col}" stroke="{INK}" stroke-width="2.5" paint-order="stroke">{ch}</text>')
part(ellipse(340, 380, 28, 32), C["crimson"])
add(f'<path d="M333 351 C324 370 326 398 335 410 M347 351 C356 370 354 398 345 410" fill="none" stroke="{C["amber"]}" stroke-width="6"/>')
part(ellipse(340, 380, 28, 32), "none")
part(rect(331, 424, 18, 13, 3), C["tan"], ink=3)
line(333, 408, 335, 424, INK, 2)
line(347, 408, 345, 424, INK, 2)
# balcony with two red figures
add('<g filter="url(#rough)">')
wood(poly((560, 640), (790, 610), (790, 640), (560, 672)), C["wood_l"], ink=5)
line(560, 600, 790, 572, INK, 6)
for fx in (620, 690):
    add(f'<path d="M{fx - 16} 660 L{fx - 12} 598 Q{fx} 578 {fx + 12} 598 L{fx + 16} 656 Z" fill="{C["crimson"]}"/>')
    add(f'<circle cx="{fx}" cy="584" r="13" fill="{C["crimson"]}"/>')
add("</g>")
add("</g>")
add(f'<circle cx="450" cy="500" r="318" fill="none" stroke="{INK}" stroke-width="6"/>')

# ---------------------------------------------------------------- the grand staircase, climbing to the window

add('<g filter="url(#rough)">')
# landing at the foot of the window, with the two silhouettes looking out
wood(poly((250, 800), (650, 800), (680, 836), (220, 836)), C["wood_l"], ink=6)
for fx, h in [(410, 190), (480, 200)]:
    add(f'<path d="M{fx - 26} 806 L{fx - 22} {806 - h + 52} Q{fx} {806 - h + 26} {fx + 22} {806 - h + 52} L{fx + 26} 806 Z" fill="{INK}"/>')
    add(f'<circle cx="{fx}" cy="{806 - h + 22}" r="19" fill="{INK}"/>')
# steps in perspective: narrow at the landing, wide at the bottom
steps = 13
for i in range(steps):
    t0, t1 = i / steps, (i + 1) / steps
    y0, y1 = 836 + 564 * t0 ** 1.25, 836 + 564 * t1 ** 1.25
    w0, w1 = 230 + 380 * t0, 230 + 380 * t1
    wood(poly((450 - w0, y0), (450 + w0, y0), (450 + w1, y1), (450 - w1, y1)), C["wood"], ink=5)
    nose = y0 + (y1 - y0) * 0.22                      # orange lit edge of the tread
    riser = y0 + (y1 - y0) * 0.55                     # dark face of the step below
    ex = lambda y: (w0 + (w1 - w0) * (y - y0) / (y1 - y0))
    add(f'<path d="{poly((450 - w0, y0), (450 + w0, y0), (450 + ex(nose), nose), (450 - ex(nose), nose))}" '
        f'fill="{C["ochre"]}" stroke="{INK}" stroke-width="3"/>')
    add(f'<path d="{poly((450 - ex(riser), riser), (450 + ex(riser), riser), (450 + w1, y1), (450 - w1, y1))}" fill="{C["wood_dd"]}"/>')
add("</g>")

# ---------------------------------------------------------------- the staircase's curving handrails (furniture drawn later sits in front)

add('<g filter="url(#rough)">')
# curving handrails sweeping out to both sides
for side in (-1, 1):
    pts = [(450 + side * (215 + 250 * t ** 1.3 + 25 * math.sin(t * math.pi)), 790 + 640 * t ** 1.15) for t in [k / 16 for k in range(17)]]
    for x, y in pts[::2]:
        line(x, y, x - side * 10, y + 80, INK, 5)
    d = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    add(f'<polyline points="{d}" fill="none" stroke="{INK}" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>')
    add(f'<polyline points="{d}" fill="none" stroke="{C["ochre"]}" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/>')
add("</g>")

# ---------------------------------------------------------------- left: round clock, shelves in perspective with a ladder

add('<g filter="url(#rough)">')
part(ellipse(70, 300, 46, 56), C["ochre_l"], ink=6)
line(70, 300, 56, 276, INK, 5)
line(70, 300, 92, 312, INK, 5)
wood(poly((0, 600), (210, 640), (210, 1000), (0, 960)), C["wood_dd"], ink=0, streaks=False)
for y0 in (640, 780, 920):  # shelves angling towards the stairs
    wood(poly((0, y0), (200, y0 + 30), (200, y0 + 52), (0, y0 + 22)), C["wood_l"], ink=5)
part(ellipse(60, 618, 30, 26), C["metal"])                                            # astronaut helmet
add(f'<path d="M40 616 Q60 596 82 616 Q60 634 40 616 Z" fill="{C["glass"]}" stroke="{INK}" stroke-width="3"/>')
shine(50, 612, 58, 606, 3)
part(rect(130, 620, 50, 26, 4), C["black"])                                           # binoculars
for bx in (140, 168):
    add(f'<circle cx="{bx}" cy="633" r="9" fill="{C["glass"]}" stroke="{INK}" stroke-width="3"/>')
part(rect(28, 742, 48, 42, 4), C["black"])                                            # top hat
part(ellipse(52, 784, 38, 9), C["black"])
add(f'<rect x="28" y="764" width="48" height="8" fill="{C["crimson"]}"/>')
part(poly((112, 806), (124, 742), (170, 742), (182, 806)), "#c2a27a")                 # drum
part(ellipse(147, 742, 24, 8), C["cream"])
part(ellipse(70, 884, 32, 26), C["crimson"])                                          # teapot
add(f'<path d="M100 878 Q126 868 118 852" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>')
add(f'<path d="M100 878 Q126 868 118 852" fill="none" stroke="{C["crimson"]}" stroke-width="5" stroke-linecap="round"/>')
part(rect(56, 852, 28, 9, 4), C["crimson"], ink=3)
for x0, x1 in ((178, 238), (218, 278)):                                               # ladder leaning on the shelves
    line(x0, 560, x1, 1060, INK, 11)
    line(x0, 560, x1, 1060, C["ochre_l"], 6)
for k in range(1, 10):
    t = k / 10
    line(178 + 60 * t, 560 + 500 * t, 218 + 60 * t, 560 + 500 * t, INK, 7)
    line(178 + 60 * t, 560 + 500 * t, 218 + 60 * t, 560 + 500 * t, C["ochre_l"], 3)
add("</g>")
halo(250, 720, 140, red=True)
lantern(250, 760)

# ---------------------------------------------------------------- right: pillar with the hourglass, cubbies, desk, magnifier

add('<g filter="url(#rough)">')
wood(rect(690, 440, 60, 960), C["ochre"], ink=6)
wood(rect(678, 520, 84, 26), C["ochre_l"], ink=5)
wood(rect(678, 760, 84, 26), C["ochre_l"], ink=5)
add("</g>")
halo(720, 650, 120)
add('<g filter="url(#rough)">')
add(f'<path d="M698 546 C698 600 714 628 714 650 C714 672 698 702 698 756 H742 C742 702 726 672 726 650 C726 628 742 600 742 546 Z" '
    f'fill="#eef8fc" fill-opacity=".9" stroke="{INK}" stroke-width="4"/>')
add(f'<path d="M704 590 C708 620 716 640 718 648 H722 C724 640 732 620 736 590 Z M702 752 C708 712 716 694 720 690 C724 694 732 712 738 752 Z" fill="{C["amber"]}"/>')
for y0, y1 in [(450, 560), (720, 860)]:
    wood(rect(750, y0, 160, y1 - y0), C["wood_dd"], ink=6, streaks=False)
    wood(rect(750, y1 - 16, 160, 18), C["wood_l"], ink=5)
part(rect(766, 494, 66, 50, 6), C["wood_l"])                                          # old TV
part(rect(774, 502, 40, 34, 6), C["glass"])
shine(780, 510, 792, 502, 3)
add(f'<circle cx="822" cy="512" r="5" fill="{C["gold"]}" stroke="{INK}" stroke-width="2"/>')
part(rect(846, 504, 52, 36, 5), C["black"])                                           # camera
part(ellipse(872, 522, 12), C["metal_d"])
add(f'<circle cx="872" cy="522" r="6" fill="{C["glass"]}" stroke="{INK}" stroke-width="2"/>')
part(rect(766, 806, 64, 38, 5), C["metal"])                                           # boombox
for cx in (782, 814):
    add(f'<circle cx="{cx}" cy="825" r="12" fill="{C["black"]}" stroke="{INK}" stroke-width="3"/>')
part(rect(846, 812, 42, 34, 5), "#7f9fb5")                                            # robot
part(rect(852, 778, 30, 32, 5), "#7f9fb5")
for ex in (861, 873):
    add(f'<circle cx="{ex}" cy="792" r="4" fill="{C["sun"]}" stroke="{INK}" stroke-width="2"/>')
# desk with papers
wood(poly((560, 1130), (900, 1080), (900, 1400), (600, 1400)), C["wood"], ink=7)
for d in [poly((600, 1150), (760, 1124), (790, 1190), (630, 1222)), poly((700, 1200), (880, 1170), (900, 1240), (720, 1276))]:
    add(f'<path d="{d}" fill="{C["gap"]}" stroke="{INK}" stroke-width="4"/>')
for k in range(5):
    line(616 + k * 30, 1162 - k * 4, 640 + k * 30, 1200 - k * 4, "#8a7a66", 2.5)
part(poly((800, 1110), (840, 1104), (846, 1140), (806, 1146)), C["green"])           # typewriter
add("</g>")
# the giant magnifying glass: thin red rim, yellow handle
add('<g filter="url(#rough)">')
add(f'<path d="M760 1130 L880 1250" stroke="{INK}" stroke-width="26" stroke-linecap="round"/>')
add(f'<path d="M760 1130 L880 1250" stroke="{C["gold"]}" stroke-width="16" stroke-linecap="round"/>')
add(f'<circle cx="700" cy="1072" r="84" fill="{C["sky"]}"/>')
add('<path d="M650 1050 L686 1014 M644 1078 L706 1018 M700 1120 L744 1076" stroke="#fff" stroke-width="8" stroke-opacity=".8" stroke-linecap="round"/>')
add(f'<circle cx="700" cy="1072" r="84" fill="none" stroke="{INK}" stroke-width="14"/>')
add(f'<circle cx="700" cy="1072" r="84" fill="none" stroke="{C["rim"]}" stroke-width="7"/>')
add("</g>")

# ---------------------------------------------------------------- bottom-left: suitcases and a film camera on a tripod

add('<g filter="url(#rough)">')
for (x, y, w, h), col in [((20, 1290, 150, 60), C["leather"]), ((32, 1236, 126, 54), C["tan"]), ((48, 1196, 94, 40), C["green"])]:
    part(rect(x, y, w, h, 7), col)
    add(f'<path d="M{x + w * .25} {y} V{y + h} M{x + w * .75} {y} V{y + h}" stroke="{C["wood_d"]}" stroke-width="6"/>')
    part(rect(x + w / 2 - 12, y - 8, 24, 10, 3), C["wood_d"], ink=2.5)
for x2 in (230, 262, 296):
    line(262, 1110, x2, 1240, INK, 8)
    line(262, 1110, x2, 1240, C["wood_l"], 4)
part(ellipse(236, 1050, 22), C["black"])
part(ellipse(290, 1050, 22), C["black"])
for cx in (236, 290):
    add(f'<circle cx="{cx}" cy="1050" r="8" fill="{C["metal"]}" stroke="{INK}" stroke-width="2"/>')
part(rect(224, 1064, 82, 50, 6), C["black"])
part(rect(304, 1076, 30, 24, 4), C["metal_d"])
add(f'<circle cx="334" cy="1088" r="10" fill="{C["glass"]}" stroke="{INK}" stroke-width="3"/>')
add("</g>")


# ---------------------------------------------------------------- hidden things everywhere (the I Spy part)

MARBLES = [marble(c) for c in (C["crimson"], C["blue"], C["green"], C["gold"], C["violet"])]
things = [die, toy_car, sneaker, sunglasses, padlock, key, headphones, trumpet, frying_pan, flashlight, comb,
          toothbrush, duck, coin, block("I", C["crimson"]), block("S", C["blue"]), block("P", C["green"]),
          block("Y", C["crimson"]), spool(C["crimson"]), spool(C["blue"]), pencil(C["gold"]), pencil(C["green"])]
# on the stairs: a few things on every step, kept clear of the middle (where the Start button sits),
# the desk and magnifier, and the suitcases; cycling through the list so nothing repeats too often
pool = (things + MARBLES) * 3
rnd.shuffle(pool)
for i in range(13):
    t = (i + 0.4) / 13
    y = 836 + 564 * t ** 1.25 + 4
    half = 230 + 380 * t
    for side in (-1, 1):
        for k in range(rnd.randint(1, 2)):
            x = 450 + side * rnd.uniform(140, half - 30)
            hidden = (x > 560 and y > 1000) or (x < 190 and y > 1170)
            if 0 < x < W and not hidden:
                place(pool.pop(), x, y, 0.75 + t * 0.6, rnd.randint(-25, 25))
# on the beams, the window sill, the shelves and the desk
for draw, x, y, s, r in [
    (umbrella, 300, 120, 1, 70), (MARBLES[0], 420, 112, 1, 0), (MARBLES[1], 446, 110, 1, 0), (die, 600, 128, 1, 12),
    (block("A", C["blue"]), 120, 160, 1, -8), (key, 760, 150, 1, 15), (coin, 520, 125, .9, 0), (duck, 360, 112, 1, 0),
    (sneaker, 300, 790, 1, 0), (toy_car, 590, 790, 1, 0), (sunglasses, 540, 800, .9, 0),
    (spool(C["green"]), 170, 900, 1, 0), (block("C", C["crimson"]), 30, 1050, 1.1, 8), (padlock, 120, 1040, 1, 0),
    (headphones, 800, 690, 1, 0), (trumpet, 820, 560, .9, 0), (frying_pan, 820, 1010, 1, -10),
    (flashlight, 760, 1180, 1, -12), (pencil(C["crimson"]), 640, 1290, 1.1, -20), (comb, 820, 1300, 1, 10),
    (toothbrush, 600, 1350, 1, 15), (MARBLES[2], 700, 1300, 1.2, 0), (MARBLES[3], 730, 1320, 1.2, 0), (die, 860, 1340, 1.2, -15),
]:
    place(draw, x, y, s, r)

# ---------------------------------------------------------------- lamps on chains, throwing light (drawn last)

for lx in (190, 720):
    add(f'<path d="{poly((lx - 36, 250), (lx + 36, 250), (lx + 170, 1100), (lx - 170, 1100))}" fill="url(#beam)" opacity=".7"/>')
    halo(lx, 262, 130)
add('<g filter="url(#rough)">')
for lx in (190, 720):
    for k in range(9):  # chain links
        add(f'<ellipse cx="{lx}" cy="{12 + k * 22}" rx="6" ry="11" fill="none" stroke="{INK}" stroke-width="4"/>')
    add(f'<path d="M{lx - 58} 256 Q{lx - 54} 202 {lx} 194 Q{lx + 54} 202 {lx + 58} 256 Z" fill="{C["ochre"]}" stroke="{INK}" stroke-width="6"/>')
    add(f'<ellipse cx="{lx}" cy="260" rx="22" ry="12" fill="#fff6cf" stroke="{INK}" stroke-width="3"/>')
    add(f'<rect x="{lx - 62}" y="250" width="124" height="11" rx="5" fill="{C["wood"]}" stroke="{INK}" stroke-width="3"/>')
add("</g>")

add(f'<rect width="{W}" height="{H}" fill="url(#vignette)"/>')
add("</svg>")
OUT.write_text("\n".join(out) + "\n")
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
