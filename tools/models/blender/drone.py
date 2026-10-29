"""Drone, after Hudsen Brodt's drawing (RV P5a), objects.json "drone".

The drawing: a blocky body sitting on crossed square beams, with a dark panel on top, a sloped nose face with a big
"13" and a round camera lens below it; four motor pods at the beam ends, each a box over a tapered bottom with two
vent slots, a square post on top and a long two-blade propeller with a kinked root and a stripe near each tip.
Line-only drawing, so colours are a call: cream-white body, gunmetal beams, orange pods and "13" (mural palette),
black props with orange tips. The far beam ends are hidden in the drawing; I read the frame as a plus with the body
along one arm, and turned the whole drone 45 degrees so the front view matches her three-quarter view. Four slim
landing legs under the body are my addition (the two short strokes under the body in the drawing).
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Black.ttf'


# ---------------------------------------------------------------- helpers (local to this script)
def fillet(pts, r, n=4, closed=False):
    m = len(pts); out = []
    for i, p in enumerate(pts):
        ri = r[i] if isinstance(r, (list, tuple)) else r
        if (not closed and i in (0, m - 1)) or not ri:
            out.append(p); continue
        P = Vector(p); A = Vector(pts[i - 1]); B = Vector(pts[(i + 1) % m])
        u = (A - P); v = (B - P); lu, lv = u.length, v.length
        u.normalize(); v.normalize()
        ang = u.angle(v, math.pi)
        if ang > math.pi - 1e-3:
            out.append(p); continue
        d = min(ri / math.tan(ang / 2), 0.48 * lu, 0.48 * lv)
        t1, t2 = P + u * d, P + v * d
        for k in range(n + 1):
            t = k / n
            q = t1 * (1 - t) ** 2 + P * 2 * (1 - t) * t + t2 * t * t
            out.append((q.x, q.y))
    return out


def ftext(s, size, depth, material=None, bevel=0.0, res=4, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res
    if bevel:
        cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.offset = -bevel
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def bake_join(name, objs=None):
    objs = objs or [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o


def settle(o, rot_z=0.0):
    o.matrix_world = Matrix.Rotation(math.radians(rot_z), 4, 'Z') @ o.matrix_world
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    o.data.transform(Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
    return o


def rod(a, b, r, material=None, verts=24, bevel=0.0, name='rod'):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=(a + b) / 2, material=material, verts=verts, bevel=bevel, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


# ---------------------------------------------------------------- materials
SHELL = kit.mat('#ece6da', rough=0.4, name='shell')
BEAM = kit.mat('gunmetal', rough=0.45, name='carbon')
POD = kit.mat('orange', rough=0.42, name='pod')
PROP = kit.mat('#1c1b1a', rough=0.4, name='prop')
MOTOR = kit.mat('gunmetal', rough=0.32, metal=0.85, name='motor')
CHROME = kit.mat('chrome', rough=0.22, metal=0.9, name='chrome')
LENS = kit.mat('#0d1418', rough=0.05, name='lens')
SMOKE = kit.mat('#23323a', rough=0.12, name='smoked_panel')
VENT = kit.mat('#141312', rough=0.6, name='vent')
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')

# Built with the body's nose along +X; turned 45 degrees at the end so the front view is her three-quarter view.
ARM = 0.255                     # pod centre distance from the middle
BZ0, BZ1 = 0.040, 0.064         # beams
POD_TOP = 0.076

# ---------------------------------------------------------------- crossed beams with end caps
for a, b in (((-ARM, 0, (BZ0 + BZ1) / 2), (ARM, 0, (BZ0 + BZ1) / 2)), ((0, -ARM, (BZ0 + BZ1) / 2), (0, ARM, (BZ0 + BZ1) / 2))):
    d = Vector(b) - Vector(a)
    size = (abs(d.x) + 0.0, abs(d.y) + 0.0, BZ1 - BZ0)
    size = (size[0] or 0.024, size[1] or 0.024, size[2])
    kit.box(size, at=(0, 0, (BZ0 + BZ1) / 2), material=BEAM, bevel=0.003, name='beam')
    for s in (-1, 1):            # a seam band where each beam meets the body
        p = (Vector(a) if s < 0 else Vector(b)) * ((ARM - 0.036) / ARM)
        kit.box((0.012 if d.x else 0.028, 0.012 if d.y else 0.028, BZ1 - BZ0 + 0.004), at=(p.x, p.y, (BZ0 + BZ1) / 2), material=MOTOR,
                bevel=0.0015, name='clamp')

# ---------------------------------------------------------------- body: sloped nose, top panel, "13", camera, side vents, legs
prof = [(-0.125, 0.062), (0.115, 0.062), (0.115, 0.110), (0.056, 0.164), (-0.112, 0.164), (-0.125, 0.150)]
prof = fillet(prof, [0.006, 0.006, 0.006, 0.006, 0.006, 0.004], n=2, closed=True)
body = kit.extrude(prof, 0.112, rot=(90, 0, 0), material=SHELL, bevel=0.006, segments=2, name='body')
body.location = (0, 0.056, 0)
# dark panel on top (the shaded slot in the drawing)
kit.box((0.120, 0.052, 0.006), at=(-0.034, 0, 0.1635), material=SMOKE, bevel=0.002, name='toppanel')
kit.box((0.125, 0.057, 0.004), at=(-0.034, 0, 0.1628), material=BEAM, bevel=0.0015, name='panelframe')
# 13 on the sloped nose face
up = Vector((-0.059, 0, 0.054)).normalized(); read = Vector((0, 1, 0)); face = read.cross(up)
t13 = ftext('13', 0.040 / 0.515, 0.003, material=POD, bevel=0.0006, name='13')
mid = Vector(((0.115 + 0.056) / 2, 0, (0.110 + 0.164) / 2))
t13.matrix_world = Matrix.Translation(mid + face * 0.0005) @ Matrix((read, up, face)).transposed().to_4x4()
# camera on the front face: housing, chrome ring, glass, inner ring
cx = 0.115
CZ = 0.086
kit.cyl(0.021, 0.010, at=(cx + 0.003, 0, CZ), rot=(0, 90, 0), material=BEAM, verts=32, bevel=0.002, name='camhousing')
kit.torus(0.016, 0.0025, at=(cx + 0.0085, 0, CZ), rot=(0, 90, 0), material=CHROME, major=32, minor=8, name='camring')
kit.sphere(0.0145, at=(cx + 0.004, 0, CZ), scale=(0.55, 1, 1), material=LENS, segs=24, rings=12, name='camglass')
kit.torus(0.007, 0.001, at=(cx + 0.0117, 0, CZ), rot=(0, 90, 0), material=CHROME, major=24, minor=6, name='caminner')
# side vents
for sy in (-1, 1):
    for k in range(4):
        kit.box((0.022, 0.003, 0.004), at=(-0.080 + k * 0.030, sy * 0.0555, 0.136), material=VENT, bevel=0.0008, name='vent')
    kit.cyl(0.004, 0.003, at=(0.072, sy * 0.0555, 0.136), rot=(90, 0, 0), material=kit.mat('#7ad06a', rough=0.3, emit=0.6), verts=12,
            name='led')
# landing legs
for sx in (-1, 1):
    for sy in (-1, 1):
        top = Vector((sx * 0.075, sy * 0.040, 0.064)); foot = Vector((sx * 0.080, sy * 0.050, 0.006))
        rod(top, foot, 0.0045, material=BEAM, verts=10, name='leg')
        kit.sphere(0.0065, at=foot, scale=(1, 1, 0.8), material=RUBBER, segs=12, rings=6, name='foot')

# ---------------------------------------------------------------- motor pods, posts, motors and props
def blade(sign, angle, length=0.118):
    """A blade along +X from the hub: kinked root, straight paddle, rounded tip in orange."""
    w = 0.024
    body_o = fillet([(0.004, -0.005), (0.020, -0.006), (0.030, -w / 2), (length - 0.026, -w / 2), (length - 0.026, w / 2), (0.032, w / 2),
                     (0.024, 0.004), (0.004, 0.005)], [0, 0.003, 0.004, 0, 0, 0.004, 0.003, 0], n=3, closed=True)
    tip_o = fillet([(length - 0.026, -w / 2), (length - 0.006, -w / 2), (length, -w / 2 + 0.006), (length, w / 2 - 0.006),
                    (length - 0.006, w / 2), (length - 0.026, w / 2)], [0, 0.004, 0.004, 0.004, 0.004, 0], n=3, closed=True)
    parts = [kit.extrude(body_o, 0.0035, at=(0, 0, -0.00175), material=PROP, bevel=0.0008, name='blade'),
             kit.extrude(tip_o, 0.0035, at=(0, 0, -0.00175), material=POD, bevel=0.0008, name='tip')]
    b = bake_join('blade', parts)
    b.matrix_world = Matrix.Rotation(math.radians(angle), 4, 'Z') @ Matrix.Rotation(math.radians(sign * 9), 4, 'X') @ b.matrix_world
    return b


for (px, py, pa) in ((ARM, 0, 82), (-ARM, 0, 98), (0, ARM, 76), (0, -ARM, 104)):
    # tapered lower half with two vent slots on each outward face
    kit.cyl(0.024, 0.032, r2=0.040, at=(px, py, 0.016), rot=(0, 0, 45), material=POD, verts=4, bevel=0.002, name='podbottom')
    kit.box((0.057, 0.057, POD_TOP - 0.031), at=(px, py, (POD_TOP + 0.031) / 2), material=POD, bevel=0.003, name='podtop')
    for fx, fy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for k in (-1, 1):
            tan_ = Vector((-fy, fx, 0))
            c = Vector((px, py, 0.016)) + Vector((fx, fy, 0)) * 0.0232 + tan_ * k * 0.008
            v = kit.box((0.0025, 0.0035, 0.016), at=c, material=VENT, name='podvent')
            v.rotation_euler = (math.radians(-19.5 * fy), math.radians(19.5 * fx), 0)
    kit.box((0.032, 0.032, 0.026), at=(px, py, POD_TOP + 0.012), material=POD, bevel=0.0025, name='post')
    kit.lathe(fillet([(0, 0), (0.017, 0), (0.018, 0.004), (0.018, 0.012), (0.015, 0.015), (0, 0.015)], [0, 0.001, 0.001, 0.002, 0.002, 0], n=2),
              at=(px, py, POD_TOP + 0.024), material=MOTOR, steps=28, name='motor')
    for k in range(6):          # cooling slots round the motor bell
        a = k * math.tau / 6
        kit.box((0.002, 0.008, 0.007), at=(px + 0.0178 * math.cos(a), py + 0.0178 * math.sin(a), POD_TOP + 0.032), rot=(0, 0, math.degrees(a)),
                material=VENT, name='motorslot')
    hz = POD_TOP + 0.043
    hub = kit.lathe(fillet([(0, -0.004), (0.009, -0.004), (0.009, 0.004), (0.004, 0.009), (0, 0.010)], [0, 0.001, 0.002, 0.002, 0], n=2),
                    at=(px, py, hz), material=PROP, steps=20, name='hub')
    for side in (0, 180):
        b = blade(1 if side == 0 else -1, pa + side)
        b.matrix_world = Matrix.Translation((px, py, hz)) @ b.matrix_world

# ---------------------------------------------------------------- join, turn, settle, export
drone = bake_join('drone')
settle(drone, rot_z=-45)
kit.export('drone')
