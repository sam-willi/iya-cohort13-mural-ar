"""Office desk - Zachary Lehr.

His drawing: one thick slab top carried by two end units. Seen from the long side, each end unit is an E: a web
standing under the top, with a middle shelf and a floor shelf cantilevered out to the end, every inside corner
filleted; the two Es face away from each other and leave a wide knee space between the webs. On the left end
the shelves hold big serif letters, I Y A on the middle shelf and C 1 3 on the floor shelf. A raised rounded pad
sits on the top over the knee space.
So it is one filleted profile extruded through the depth. Line-only, so: oak (PIL-painted grain texture),
brass letters (Times bold: his are lining serif capitals and numerals), a dark green leather pad. Ends made symmetric (his right unit is drawn a little wider).
Invented: felt glides, a brass cable grommet at the back of the top.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy, bmesh, subprocess, tempfile

kit.reset()

L, D, H = 1.7, 0.7, 0.74       # length (x), depth (y), height (z)
T = 0.065                      # slab / shelf / web thickness
U = 0.44                       # end unit width (outer end to the knee-side face of its web)
RF = 0.07                      # inside fillet radius
ZM = T + (H - 3 * T) / 2       # underside of the middle shelf
LIFT = 0.005                   # felt glides
TEX = os.path.join(tempfile.gettempdir(), 'office-desk-oak.jpg')

PAINT = r'''
import sys, math, random
import numpy as np
from PIL import Image, ImageFilter
out = sys.argv[1]
W, H = 1024, 512                       # covers 2.0 m (grain direction, u) x 1.0 m (v)
rng = np.random.default_rng(13)
x = np.linspace(0, 1, W)[None, :]; y = np.linspace(0, 1, H)[:, None]
warp = np.zeros((H, W))
for k in range(1, 6):
    a, fx, fy, ph = rng.uniform(0.002, 0.008) / k, rng.integers(1, 3) * k, rng.integers(1, 3), rng.uniform(0, 6.28)
    warp += a * np.sin(2 * np.pi * (fx * x + fy * y) + ph)
rings = (y + warp + 0.004 * rng.normal(0, 1, (H, 1))) * 46.0
g = 0.5 + 0.5 * np.sin(2 * np.pi * rings)
g = g ** 8                             # thin dark latewood lines
streak = rng.normal(0, 1, (H, 1)) * np.ones((1, W))
streak = np.array(Image.fromarray(((streak - streak.min()) / (np.ptp(streak) + 1e-9) * 255).astype('uint8'))
                  .filter(ImageFilter.GaussianBlur(1.2))) / 255.0
fine = rng.normal(0, 1, (H, W)) * 0.035
base = np.array([0x8c, 0x5c, 0x32], float) / 255.0
dark = np.array([0x63, 0x3f, 0x22], float) / 255.0
light = np.array([0xa8, 0x76, 0x44], float) / 255.0
t = np.clip(0.38 * g + 0.35 * (streak - 0.5) + fine, -0.3, 1.0)[..., None]
img = np.where(t > 0, base + (dark - base) * t, base + (light - base) * (-t) * 2.5)
img = np.clip(img, 0, 1)
Image.fromarray((img * 255).astype('uint8')).save(out, quality=90)
'''
subprocess.run(['/usr/bin/env', 'python3', '-c', PAINT, TEX], check=True)

oak_m = kit.mat('#ffffff', rough=0.55, name='oak', image=TEX)
brass_m = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
pad_m = kit.mat('#2e5249', rough=0.65, name='leather')
stitch_m = kit.mat('#c9b48c', rough=0.7, name='stitch')
felt_m = kit.mat('#2a2522', rough=0.9, name='felt')
dark_m = kit.mat('#141312', rough=0.6, name='hole')


def arc(cx, cz, a0, a1, n=8):
    return [(cx + RF * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cz + RF * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def profile():
    """The desk seen from the front: top slab, two outward-facing E units, filleted inside corners. CCW."""
    x0, x1 = -L / 2, L / 2
    wl0, wl1 = x0 + U - T, x0 + U          # left web
    wr0, wr1 = x1 - U, x1 - U + T          # right web
    zt = H - T                             # slab underside
    p = [(x0, 0), (wl1, 0)]
    p += arc(wl1 + RF, zt - RF, 180, 90)                       # knee side, under the slab (left)
    p += arc(wr0 - RF, zt - RF, 90, 0)                         # knee side, under the slab (right)
    p += [(wr0, 0), (x1, 0), (x1, T)]
    p += arc(wr1 + RF, T + RF, 270, 180)                       # right floor shelf into the web
    p += arc(wr1 + RF, ZM - RF, 180, 90)                       # web up into the middle shelf underside
    p += [(x1, ZM), (x1, ZM + T)]
    p += arc(wr1 + RF, ZM + T + RF, 270, 180)                  # middle shelf top into the web
    p += arc(wr1 + RF, zt - RF, 180, 90)                       # web into the slab underside
    p += [(x1, zt), (x1, H), (x0, H), (x0, zt)]
    p += arc(wl0 - RF, zt - RF, 90, 0)
    p += arc(wl0 - RF, ZM + T + RF, 0, -90)
    p += [(x0, ZM + T), (x0, ZM)]
    p += arc(wl0 - RF, ZM - RF, 90, 0)
    p += arc(wl0 - RF, T + RF, 0, -90)
    p += [(x0, T)]
    return p


desk = kit.extrude(profile(), D, rot=(90, 0, 0), material=oak_m, bevel=0.005, segments=3, name='desk')
desk.location = (0, D / 2, LIFT)
desk.modifiers['bevel'].angle_limit = math.radians(40)    # fillet segments (11 deg) stay smooth, corners bevel
bpy.ops.object.select_all(action='DESELECT'); desk.select_set(True); bpy.context.view_layer.objects.active = desk
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
# box-projected UVs so the grain runs along the length on the top, shelves and the long faces
bm = bmesh.new(); bm.from_mesh(desk.data); uv = bm.loops.layers.uv.new('UVMap')
for f in bm.faces:
    n = f.normal
    ax = max(range(3), key=lambda i: abs(n[i]))
    for l in f.loops:
        x, y, z = l.vert.co
        l[uv].uv = {2: (x / 2.0 + 0.5, y + 0.5), 1: (x / 2.0 + 0.5, z + 0.13), 0: (y / 2.0 + 0.3, z + 0.61)}[ax]
bm.to_mesh(desk.data); bm.free()

# ---------------------------------------------------------------- leather pad with a stitched edge
PW, PD = 0.76, 0.5
PY = 0.03


def rrect(w, h, r, n=8, cx=0.0, cy=0.0):
    out = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            out.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return out


kit.extrude(rrect(PW, PD, 0.04), 0.006, at=(0, PY, LIFT + H), material=pad_m, bevel=0.0025, segments=2, name='pad')
stitch = rrect(PW - 0.024, PD - 0.024, 0.028, n=6, cy=PY)
stitches = []
for (ax_, ay), (bx, by) in zip(stitch, stitch[1:] + stitch[:1]):
    seg = math.dist((ax_, ay), (bx, by)); n = max(1, int(seg / 0.016))
    for k in range(n):
        t0 = (k + 0.2) / n; t1 = (k + 0.7) / n
        p0 = (ax_ + (bx - ax_) * t0, ay + (by - ay) * t0); p1 = (ax_ + (bx - ax_) * t1, ay + (by - ay) * t1)
        cx, cy = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        stitches.append(kit.box((math.dist(p0, p1), 0.0022, 0.0012), at=(cx, cy, LIFT + H + 0.0061),
                                rot=(0, 0, ang), material=stitch_m, name='stitch'))
bpy.ops.object.select_all(action='DESELECT')
for o in stitches:
    o.select_set(True)
bpy.context.view_layer.objects.active = stitches[0]
bpy.ops.object.join()

# ---------------------------------------------------------------- letters on the left shelves, facing the end
FONT = bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf')


def letter(ch, y, z_floor, size=0.25, depth=0.035):
    cu = bpy.data.curves.new('L', 'FONT'); cu.body = ch; cu.font = FONT; cu.size = size
    cu.extrude = depth / 2; cu.bevel_depth = 0.0025; cu.bevel_resolution = 2; cu.resolution_u = 4
    cu.align_x = 'CENTER'; cu.align_y = 'BOTTOM_BASELINE'
    o = bpy.data.objects.new('L_' + ch, cu); bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.radians(90), 0, math.radians(-90))
    o.location = (-L / 2 + 0.11, y, z_floor)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    kit.finish(o, brass_m, smooth=35)
    return o


for ch, y in zip('IYA', (0.22, 0.0, -0.22)):
    letter(ch, y, LIFT + ZM + T)
for ch, y in zip('C13', (0.22, 0.0, -0.22)):
    letter(ch, y, LIFT + T)

# ---------------------------------------------------------------- grommet and glides
gx, gy = 0.55, D / 2 - 0.09
kit.cyl(0.029, 0.002, at=(gx, gy, LIFT + H + 0.0002), material=dark_m, verts=40)
kit.torus(0.031, 0.0035, at=(gx, gy, LIFT + H + 0.0012), material=brass_m, major=40, minor=10)
kit.box((0.034, 0.004, 0.002), at=(gx, gy + 0.008, LIFT + H + 0.0014), material=dark_m, bevel=0.0008)
for ux in (-L / 2 + 0.06, -L / 2 + U - 0.06, L / 2 - U + 0.06, L / 2 - 0.06):
    for y in (-D / 2 + 0.06, D / 2 - 0.06):
        kit.cyl(0.022, LIFT + 0.002, at=(ux, y, (LIFT + 0.002) / 2), material=felt_m, bevel=0.0015, verts=24)

kit.export('office-desk')
