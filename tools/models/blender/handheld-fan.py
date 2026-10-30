"""Handheld fan - Edie Murawski.

Her drawing: a folding fan opened to about 120 degrees, its pleated paper leaf printed with a night sky (Saturn,
a swirly Earth, a banded planet with a little moon, scattered stars) above a band of scalloped clouds; bare sticks
fanning down to a rivet with a spiral on it; the front guard stick inlaid with a row of stars.
The leaf art is a PIL-painted texture (palette colours, ink outlines like the mural), mapped onto real pleats.
Unsure: whether her scallops are the leaf's lower edge or clouds painted on it. Built as a real fan would be:
a leaf with a plain inner edge whose lower band is painted as clouds, scalloped tops where she drew them.
The back shows the same print through (a single double-sided leaf); the back guard is plain.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy, bmesh, subprocess, tempfile, json

kit.reset()

R = 0.23                    # stick length (pivot to leaf top)
RIN = 0.44 * R              # leaf inner edge
SPREAD = 124.0              # opening angle, degrees
N = 24                      # pleat panels
DEP = 0.0055                # pleat half-depth at the top edge
PZ = 0.0062                 # pivot height: the rivet caps touch the ground
A0 = -SPREAD / 2            # angle of the left edge from vertical (degrees)

# ---------------------------------------------------------------- leaf texture (painted with PIL in system python)
TEX = os.path.join(tempfile.gettempdir(), 'handheld-fan-leaf.jpg')
PAINT = r'''
import sys, json, math, random
from PIL import Image, ImageDraw, ImageFilter
a = json.loads(sys.argv[1]); out = sys.argv[2]
W, H = 2048, 1024; R = a['R']; A0 = a['A0']; SP = a['SP']; RIN = a['RIN']
random.seed(7)
def px(rn, tn):          # (radius fraction, angle fraction 0=left..1=right) -> pixel
    ang = math.radians(A0 + tn * SP)
    return ((rn * math.sin(ang) + 1) / 2 * W, (1 - rn * math.cos(ang)) * H)
def hexc(h, k=1.0):
    h = h.lstrip('#'); return tuple(min(255, int(int(h[i:i + 2], 16) * k)) for i in (0, 2, 4))
INK = hexc('#2a1d14')
def scallop(tn):         # cloud tops: 12 arcs, one per pair of pleats
    f = (tn * 12) % 1.0
    return 0.605 + 0.062 * math.sqrt(max(0.0, 1 - (2 * f - 1) ** 2))
img = Image.new('RGB', (W, H)); P = img.load()
sky0, sky1 = hexc('#1b4152'), hexc('#10283a')
c0, c1 = hexc('#f6eedb'), hexc('#d9c7a2')
for y in range(H):
    for x in range(W):
        X = x / W * 2 - 1; Z = 1 - y / H
        rn = math.hypot(X, Z); tn = (math.degrees(math.atan2(X, Z)) - A0) / SP
        tn = min(1, max(0, tn))
        s = scallop(tn)
        if rn >= s:
            t = min(1, (rn - s) / (1 - s))
            P[x, y] = tuple(int(sky0[i] + (sky1[i] - sky0[i]) * t) for i in range(3))
        else:
            t = max(0, min(1, (s - rn) / (s - RIN / R + 1e-6)))
            f = (tn * 12) % 1.0
            cusp = math.exp(-((min(f, 1 - f)) / 0.12) ** 2)       # soft shadow under each cusp between puffs
            # lit cloud tops fading to a warmer shadow toward the sticks
            k = max(0, 1 - 0.45 * t ** 0.9 - 0.3 * cusp * math.exp(-t / 0.25))
            P[x, y] = tuple(int(c1[i] + (c0[i] - c1[i]) * k) for i in range(3))
d = ImageDraw.Draw(img)
# cloud top outline
d.line([px(scallop(i / 1200), i / 1200) for i in range(1201)], fill=INK, width=5)
# dust stars
for i in range(260):
    tn = random.random(); rn = random.uniform(0.69, 0.985)
    x, y = px(rn, tn); r = random.choice((1.5, 2, 2, 3))
    d.ellipse((x - r, y - r, x + r, y + r), fill=hexc('#efe3c8', random.uniform(0.7, 1.0)))
def star(cx, cy, ro, rot=0, fill='#f6c25a'):
    pts = []
    for k in range(10):
        rr = ro if k % 2 == 0 else ro * 0.45
        a = math.radians(rot - 90 + k * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=hexc(fill), outline=INK, width=5)
for tn, rn, s, rot in ((0.25, 0.88, 46, 8), (0.22, 0.73, 40, -12), (0.46, 0.905, 46, 5), (0.57, 0.79, 50, -6),
                       (0.86, 0.75, 44, 10), (0.9, 0.925, 42, -14), (0.07, 0.95, 26, 0), (0.64, 0.95, 26, 20),
                       (0.36, 0.95, 24, 30)):
    star(*px(rn, tn), s, rot)
# Saturn
cx, cy = px(0.80, 0.105); pr = 0.082 * W / 2
d.ellipse((cx - pr * 2.1, cy - pr * 0.62, cx + pr * 2.1, cy + pr * 0.62), outline=INK, width=16)
d.ellipse((cx - pr * 2.1, cy - pr * 0.62, cx + pr * 2.1, cy + pr * 0.62), outline=hexc('#efe3c8'), width=9)
d.ellipse((cx - pr, cy - pr, cx + pr, cy + pr), fill=hexc('#c8893d'), outline=INK, width=6)
for b, col in ((-0.45, '#e8a33a'), (0.05, '#9a6a3c'), (0.45, '#e8a33a')):
    hw = pr * math.sqrt(max(0, 1 - b * b)) * 0.95
    d.line((cx - hw, cy + b * pr, cx + hw, cy + b * pr), fill=hexc(col), width=10)
d.arc((cx - pr * 2.1, cy - pr * 0.62, cx + pr * 2.1, cy + pr * 0.62), 0, 180, fill=INK, width=16)
d.arc((cx - pr * 2.1, cy - pr * 0.62, cx + pr * 2.1, cy + pr * 0.62), 0, 180, fill=hexc('#efe3c8'), width=9)
# swirly Earth
cx, cy = px(0.76, 0.37); pr = 0.08 * W / 2
d.ellipse((cx - pr, cy - pr, cx + pr, cy + pr), fill=hexc('#8fc3dc'), outline=INK, width=6)
random.seed(3)
for k in range(7):
    a0 = random.uniform(0, 6.28); rr = random.uniform(0.15, 0.75) * pr
    pts = [(cx + (rr + 0.2 * pr * math.sin(4 * t + k)) * math.cos(a0 + t), cy + (rr + 0.2 * pr * math.sin(4 * t + k)) * math.sin(a0 + t))
           for t in [i * 0.06 for i in range(40)]]
    pts = [p for p in pts if math.hypot(p[0] - cx, p[1] - cy) < pr * 0.88]
    if len(pts) > 2:
        d.line(pts, fill=hexc('#2f7d86'), width=9, joint='curve')
# banded planet with a moon
cx, cy = px(0.86, 0.71); pr = 0.085 * W / 2
d.ellipse((cx - pr, cy - pr, cx + pr, cy + pr), fill=hexc('#d9662a'), outline=INK, width=6)
for b, col, w in ((-0.62, '#efe3c8', 12), (-0.25, '#e8a33a', 16), (0.15, '#efe3c8', 12), (0.5, '#b0663c', 16)):
    hw = pr * math.sqrt(max(0, 1 - b * b)) * 0.93
    d.line((cx - hw, cy + b * pr, cx + hw, cy + b * pr), fill=hexc(col), width=w)
d.ellipse((cx - pr, cy - pr, cx + pr, cy + pr), outline=INK, width=6)
mx, my = cx + pr * 0.85, cy + pr * 0.85; mr = pr * 0.3
d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=hexc('#f4ecd8'), outline=INK, width=5)
# thin ink binding along the top edge
pts = [px(0.992, i / 400) for i in range(401)]
d.line(pts, fill=hexc('#c8893d'), width=6)
img = img.filter(ImageFilter.SMOOTH)
img.resize((1024, 512), Image.LANCZOS).save(out, quality=90)
'''
subprocess.run(['/usr/bin/env', 'python3', '-c', PAINT, json.dumps({'R': R, 'A0': A0, 'SP': SPREAD, 'RIN': RIN}), TEX],
               check=True)

leaf_m = kit.mat('#ffffff', rough=0.62, name='leaf', image=TEX)
walnut_m = kit.mat('walnut', rough=0.5, name='walnut')
stick_m = kit.mat('honey', rough=0.55, name='stick')
brass_m = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
star_m = kit.mat('lamp', rough=0.35, metal=0.8, name='staronlay')


def ang(k):
    return math.radians(A0 + SPREAD * k / N)


def fold_y(k, r):
    """Pleat offset of fold line k at radius r (alternating, growing toward the top)."""
    return (DEP if k % 2 else -DEP) * r / R


def pt(a, r, y):
    return (r * math.sin(a), y, PZ + r * math.cos(a))


# ---------------------------------------------------------------- pleated leaf with flat-fan UVs
me = bpy.data.meshes.new('leaf'); bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
RS = 4                     # radial rows per panel (keeps texture interpolation true)
grid = {}
for k in range(N + 1):
    for j in range(RS + 1):
        r = RIN + (R - RIN) * j / RS
        grid[k, j] = bm.verts.new(pt(ang(k), r, fold_y(k, r)))
for k in range(N):
    for j in range(RS):
        f = bm.faces.new((grid[k, j], grid[k + 1, j], grid[k + 1, j + 1], grid[k, j + 1]))
        for l in f.loops:
            x, _, z = l.vert.co
            l[uv].uv = (0.5 + x / (2 * R), (z - PZ) / R)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me); bm.free()
leaf = bpy.data.objects.new('leaf', me); bpy.context.collection.objects.link(leaf)
kit.finish(leaf, leaf_m, smooth=0)
leaf_m.use_backface_culling = False

# ---------------------------------------------------------------- sticks: one per fold, stacked at the rivet


def slab(a, r0, r1, w0, w1, t, y0, y1, material, name, tip=False):
    """Tapered flat stick along angle a from radius r0 to r1, thickness t (in y), y offsets at each end."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ux, uz = math.sin(a), math.cos(a)      # along the stick
    vx, vz = math.cos(a), -math.sin(a)     # across the stick
    ring = []
    n = 6 if tip else 1
    outline = [(r0, -w0 / 2), (r1, -w1 / 2)]
    if tip:   # rounded tip
        outline = [(r0, -w0 / 2), (r1 - w1 / 2, -w1 / 2)] + [
            (r1 - w1 / 2 + w1 / 2 * math.sin(math.pi * i / n), -w1 / 2 * math.cos(math.pi * i / n)) for i in range(1, n)]
        outline += [(r1 - w1 / 2, w1 / 2), (r0, w0 / 2)]
    else:
        outline += [(r1, w1 / 2), (r0, w0 / 2)]
    # rounded butt around the rivet
    m = 5
    butt = [(r0 - w0 / 2 * math.sin(math.pi * i / m), w0 / 2 * math.cos(math.pi * i / m)) for i in range(1, m)]
    outline = outline + butt
    for s, yy in ((-1, 0), (1, 1)):
        layer = []
        for rr, ww in outline:
            f = (rr - r0) / (r1 - r0) if r1 != r0 else 0
            y = y0 + (y1 - y0) * max(0, min(1, f)) + s * t / 2
            layer.append(bm.verts.new((rr * ux + ww * vx, y, PZ + rr * uz + ww * vz)))
        ring.append(layer)
    bm.faces.new(ring[0]); bm.faces.new(list(reversed(ring[1])))
    L = len(outline)
    for i in range(L):
        bm.faces.new((ring[0][i], ring[0][(i + 1) % L], ring[1][(i + 1) % L], ring[1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, bevel=min(t, w0) * 0.3, segments=2)


TS = 0.0008
for k in range(N + 1):
    if k in (0, N):
        continue
    a = ang(k)
    y_root = (N / 2 - k) * TS * 0.95          # left sticks at the back of the stack, right at the front
    y_leaf = fold_y(k, RIN + 0.02) + (0.0022 if k % 2 == 0 else 0.001)
    slab(a, 0.0, RIN + 0.02, 0.0042, 0.0058, TS, y_root, y_leaf, stick_m, f'stick{k}')

# guards: back (left) plain, front (right) with star inlays
GW, GT = 0.0105, 0.0026
yb = (N / 2) * TS * 0.95 + GT / 2 + 0.0002
slab(ang(0), 0.0, R + 0.004, 0.0085, GW, GT, yb, fold_y(0, R) + 0.0025, walnut_m, 'guard_back', tip=True)
yf = (N - N / 2) * TS * 0.95 + GT / 2 + 0.0002
yf_top = fold_y(N, R) - 0.0025
slab(ang(N), 0.0, R + 0.004, 0.0085, GW, GT, -yf, yf_top, walnut_m, 'guard_front', tip=True)


def star_poly(ro, ri=0.45):
    return [(ro * (ri if i % 2 else 1) * math.cos(math.radians(90 + i * 36)),
             ro * (ri if i % 2 else 1) * math.sin(math.radians(90 + i * 36))) for i in range(10)]


a = ang(N)
for i in range(17):
    r = 0.022 + i * (R - 0.03) / 16
    f = r / (R + 0.004)
    yfront = (-yf + (yf_top - (-yf)) * f) - GT / 2      # front face of the front guard at r
    s = kit.extrude(star_poly(0.0034), 0.0005, material=star_m, name='inlay')
    s.rotation_euler = (math.radians(90), a, 0)
    s.location = (r * math.sin(a), yfront + 0.0002, PZ + r * math.cos(a))

# ---------------------------------------------------------------- rivet with the spiral
stack = yf * 2 + 0.002
kit.cyl(0.0032, stack, at=(0, 0, PZ), rot=(90, 0, 0), material=brass_m, verts=24, name='pin')
for s in (-1, 1):
    y = s * (yf + GT / 2 + 0.0004) if s > 0 else -(yf + GT / 2 + 0.0004)
    cap = kit.sphere(0.0062, scale=(1, 0.32, 1), material=brass_m, segs=32, rings=12, name='rivet_cap')
    cap.location = (0, y if s > 0 else y, PZ)
# front cap is on -Y; spiral relief on it
cy = -(yf + GT / 2 + 0.0004) - 0.0062 * 0.32 + 0.0004
sp = []
for i in range(46):
    t = i / 45
    a = t * math.tau * 2.4
    rr = 0.0006 + 0.0043 * t
    yy = cy + 0.0062 * 0.32 * (1 - math.sqrt(max(0, 1 - (rr / 0.0062) ** 2))) - 0.0003
    sp.append((rr * math.cos(a), yy, PZ + rr * math.sin(a)))
kit.tube(sp, 0.00045, material=kit.mat('#7a5a26', rough=0.35, metal=0.85), bevel_res=6, name='spiral')

kit.export('handheld-fan')
