"""Noise-canceling headphones (Hartley Scales).

The drawing: Beats-style over-ears seen from above and to one side. A wide, flat headband that runs nearly
straight across and turns down at both ends into short sliders, two big oval cups hanging from them, thick
cushions (the near-side cup shows its cushion and oval ear opening), and the "b" roundel on the outer face.
Line-only, so the iconic colourway: gloss red shells, black leather cushions and band padding, chrome sliders.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'


# ---------- local helpers ----------
def link(o):
    bpy.context.collection.objects.link(o); return o


def sweep(P, ups, prof, material, closed=False, name='sweep', smooth=60):
    """Sweep a closed profile [(u, v)] along points P; u runs along T x up, v along up."""
    bm = bmesh.new(); rings = []; n = len(P)
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        side = t.cross(ups[i]).normalized(); up = side.cross(t).normalized()
        rings.append([bm.verts.new(P[i] + side * u + up * v) for u, v in prof])
    m = len(prof)
    for a, b in zip(rings, rings[1:]):
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return kit.finish(link(bpy.data.objects.new(name, me)), material, smooth=smooth)


def rounded_rect_prof(hw, hh, r, k=4):
    """Closed rounded-rectangle profile, half width hw (u) and half height hh (v)."""
    pts = []
    for cx, cy, a0 in ((hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180), (hw - r, -hh + r, 270)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def resample(P, step):
    out = [P[0]]; acc = 0.0
    for a, b in zip(P, P[1:]):
        L = (b - a).length; d = step - acc
        while d <= L:
            out.append(a.lerp(b, d / L)); d += step
        acc = L - (d - step)
    if (out[-1] - P[-1]).length > step * 0.3:
        out.append(P[-1])
    else:
        out[-1] = P[-1]
    return out


def text3d(s, size, depth, font=None, rot=(90, 0, 90), at=(0, 0, 0), material=None, res=4, name='t'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res
    o = link(bpy.data.objects.new(name, cu))
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


# ---------- materials ----------
shell = kit.mat('#a8231e', rough=0.22, name='gloss_red')
seam_red = kit.mat('#6e1714', rough=0.4, name='seam_red')
leather = kit.mat('#1f1d1c', rough=0.6, name='leather')
padding = kit.mat('#262422', rough=0.75, name='soft_touch')
cloth = kit.mat('#3a3836', rough=0.95, name='speaker_cloth')
chrome = kit.mat('chrome', rough=0.18, metal=1.0, name='chrome')
gun = kit.mat('gunmetal', rough=0.35, metal=0.8, name='gunmetal')
white = kit.mat('#f4f1ea', rough=0.3, name='logo_white')
led = kit.mat('#f2efe8', rough=0.2, emit=0.8, name='led')

# ---------- dimensions ----------
CX_IN = 0.064                 # cushion face distance from the centre line
SH = 1.12                     # cups are ovals, taller than wide
RC = 0.052                    # cup radius (before the oval stretch)
CZ = RC * SH + 0.0005         # cup centre height: cups stand on their bottom edges
CUP_TOP = CZ + RC * SH
XH = CX_IN + 0.031            # x of the hinge / slider line

# ---------- ear cups ----------
k_ = RC / 0.047
shell_prof = [(0.0, 0.053), (0.02 * k_, 0.0525), (0.032 * k_, 0.051), (0.0405 * k_, 0.048), (0.0455 * k_, 0.0425),
              (RC, 0.0355), (RC, 0.027), (0.0455 * k_, 0.0235), (0.0, 0.0235)]
cushion_prof = [(r * k_, z) for r, z in [(0.021, 0.021), (0.0205, 0.006), (0.0235, 0.0015), (0.03, 0.0), (0.0385, 0.0),
                (0.0438, 0.0025), (0.0462, 0.0085), (0.0465, 0.0155), (0.0452, 0.0205), (0.042, 0.0222),
                (0.021, 0.0222), (0.021, 0.021)]]
for sx in (-1, 1):
    rot = (0, 90 * sx, 0)
    at = (sx * CX_IN, 0, CZ)
    o = kit.lathe(shell_prof, material=shell, steps=64, name='cup_shell')
    o.rotation_euler = [math.radians(a) for a in rot]; o.location = at; o.scale = (SH, 1, 1)
    kit.finish(o, shell, smooth=50)
    o = kit.lathe(cushion_prof, material=leather, steps=64, name='cushion')
    o.rotation_euler = [math.radians(a) for a in rot]; o.location = at; o.scale = (SH, 1, 1)
    kit.finish(o, leather, smooth=55)
    # seam ring between shell and cushion
    o = kit.torus(RC - 0.0012, 0.0016, material=gun, major=64, minor=8, name='seam')
    o.rotation_euler = [math.radians(a) for a in rot]; o.location = (sx * (CX_IN + 0.0232), 0, CZ); o.scale = (SH, 1, 1)
    # speaker cloth at the bottom of the ear opening
    o = kit.cyl(0.0212 * k_, 0.002, verts=40, material=cloth, name='cloth')
    o.rotation_euler = [math.radians(a) for a in rot]; o.location = (sx * (CX_IN + 0.012), 0, CZ); o.scale = (SH, 1, 1)
    # the "b" roundel on the outer face
    face_x = sx * (CX_IN + 0.0531)
    # the outer cap is a separate plate: a seam ring round it (drawn as the cup's inner circle)
    o = kit.torus(0.0345 * k_, 0.0009, material=seam_red, major=64, minor=6, name='cap_seam')
    o.rotation_euler = [math.radians(a) for a in rot]; o.location = (sx * (CX_IN + 0.0506), 0, CZ); o.scale = (SH, 1, 1)
    o = kit.torus(0.0175, 0.0016, material=white, major=48, minor=8, name='logo_ring')
    o.rotation_euler = [math.radians(a) for a in rot]; o.location = (face_x + sx * 0.0004, 0, CZ)
    b = text3d('b', 0.03, 0.0014, font=FONT, rot=(90, 0, 90 * sx), material=white, name='logo_b',
               at=(face_x + sx * 0.0006, 0, CZ + 0.0005))
    # hinge yoke on top of the cup
    kit.box((0.016, 0.03, 0.012), at=(sx * XH, 0, CUP_TOP + 0.004), material=gun, bevel=0.004, segments=2,
            name='hinge')
    kit.cyl(0.0042, 0.034, at=(sx * XH, 0, CUP_TOP + 0.004), rot=(90, 0, 0), material=chrome, verts=16,
            name='hingepin')

# fuel-gauge LEDs under the right cup, a 3.5 mm jack under the left one
for k in range(5):
    kit.sphere(0.0013, at=(CX_IN + 0.035, -0.008 + k * 0.004, CZ - RC * SH * 0.86), material=led, segs=10,
               rings=6, name='led')
kit.cyl(0.0042, 0.006, at=(-(CX_IN + 0.035), 0, CZ - RC * SH * 0.93), material=gun, verts=20, name='jack')
kit.cyl(0.0019, 0.0062, at=(-(CX_IN + 0.035), 0, CZ - RC * SH * 0.93), material=leather, verts=16, name='jackhole')

# ---------- headband: wide and flat, nearly straight across, turning down at the ends ----------
Z_END = CUP_TOP + 0.034       # where the band ends and the sliders come out
B = 0.072                     # rise of the band above its ends
A = XH                        # half span
pexp = 0.5                    # < 1 squares the arc off: flat top, tight shoulders
raw = []
for i in range(801):
    t = math.pi * i / 800
    c, s = math.cos(t), math.sin(t)
    raw.append(Vector((A * math.copysign(abs(c) ** pexp, c), 0, Z_END + B * abs(s) ** pexp)))
P = resample(raw, 0.004)
ups = []
for i in range(len(P)):
    t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
    ups.append(Vector((t.z, 0, -t.x)))          # outward normal of a counter-clockwise curve in x-z
BW_, BT = 0.019, 0.0048                         # half width, half thickness
sweep(P, ups, rounded_rect_prof(BW_, BT, 0.0035), shell, name='headband')
# padding on the underside of the top run, with a stitched centre groove
top_idx = [i for i, p in enumerate(P) if p.z > Z_END + B * 0.86]
PP = [P[i] - ups[i] * (BT + 0.0034) for i in top_idx]
UU = [ups[i] for i in top_idx]
sweep(PP, UU, rounded_rect_prof(BW_ - 0.003, 0.0038, 0.0032), padding, name='padding')
sweep([p - u * 0.0036 for p, u in zip(PP, UU)], UU, rounded_rect_prof(0.0009, 0.0007, 0.0006, 2), leather,
      name='stitch')
# end collars where the sliders leave the band
for sx in (-1, 1):
    kit.box((0.012, 2 * BW_ - 0.004, 0.012), at=(sx * A, 0, Z_END + 0.002), material=gun, bevel=0.003, segments=2,
            name='collar')
    # the slider: a flat chrome bar from the collar down into the hinge, with size ticks
    z0, z1 = CUP_TOP + 0.008, Z_END
    kit.box((0.0035, 0.014, z1 - z0), at=(sx * A, 0, (z0 + z1) / 2), material=chrome, bevel=0.001, name='slider')
    for k in range(4):
        kit.box((0.0006, 0.006, 0.0008), at=(sx * (A + 0.0019), 0, z0 + 0.007 + k * 0.0045), material=gun,
                name='tick')

kit.export('headphones')
