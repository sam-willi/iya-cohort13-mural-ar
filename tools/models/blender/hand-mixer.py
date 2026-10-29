"""Hand mixer slot - Jonathan Bakhash (Cohort 13).

His drawing is unlabeled and doesn't show a hand mixer: it is a countertop soft-serve machine.
A bell-shaped body on a wide flared base, a waffle-textured ring on top holding a soft-serve
swirl with a curled tip, three pill-shaped slots down the front, a dark fill-level window on the
left, a two-button strip and an oval lens on the right, a control band around the bottom (round
buttons, a slider, a play button), and an arm off the right side holding a little cone.
Built faithfully to the drawing; materials are a pastel-blue enamel appliance in the mural palette.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()


# ---------------------------------------------------------------- local helpers
def framed_check(obj_id, res=520):
    """kit.check_render frames at 3.2x the bounding radius with a 70 mm lens, which crops tall or long
    objects. Pad the bounds with a vertex-only (invisible) mesh first; the GLB is already written."""
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
    hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
    ctr, half = (lo + hi) / 2, (hi - lo) / 2
    k = max(half) / (0.8 * half.length) * 1.08
    if k > 1:
        me = bpy.data.meshes.new('frame_pad'); me.from_pydata([tuple(ctr - half * k), tuple(ctr + half * k)], [], [])
        bpy.context.collection.objects.link(bpy.data.objects.new('frame_pad', me))
    _kit_check(obj_id, res)


_kit_check = kit.check_render
kit.check_render = framed_check


def boolean(target, cutter, op='DIFFERENCE', keep=False):
    """Like kit.boolean, but the cut faces take the cutter's material (so recesses can be dark)."""
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op; md.object = cutter
    md.solver = 'EXACT'; md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    if not keep:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def sweep(path, section, scales, material=None, name='sweep', cap=True):
    """Sweep a closed 2D section [(u, v), ...] along a 3D path with a per-point scale."""
    path = [Vector(p) for p in path]
    n = len(path)
    tangents = []
    for i in range(n):
        a, b = path[max(i - 1, 0)], path[min(i + 1, n - 1)]
        tangents.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - tangents[0] * up.dot(tangents[0])).normalized()
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for i in range(n):
        T = tangents[i]
        N = (N - T * N.dot(T)).normalized()
        B = T.cross(N)
        s = scales[i]
        rings.append([bm.verts.new(path[i] + s * (u * N + v * B)) for u, v in section])
    m = len(section)
    for i in range(n - 1):
        for j in range(m):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % m], rings[i + 1][(j + 1) % m], rings[i + 1][j]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material)


def stadium(w, h, n=10):
    """Pill outline, w wide, h tall, centred at the origin (2D)."""
    r = min(w, h) / 2; pts = []
    if w >= h:
        for i in range(n + 1):
            a = -math.pi / 2 + math.pi * i / n; pts.append((w / 2 - r + r * math.cos(a), r * math.sin(a)))
        for i in range(n + 1):
            a = math.pi / 2 + math.pi * i / n; pts.append((-w / 2 + r + r * math.cos(a), r * math.sin(a)))
    else:
        for i in range(n + 1):
            a = math.pi * i / n; pts.append((r * math.cos(a), h / 2 - r + r * math.sin(a)))
        for i in range(n + 1):
            a = math.pi + math.pi * i / n; pts.append((r * math.cos(a), -h / 2 + r + r * math.sin(a)))
    return pts


def prism_y(poly, cx, cz, y0, y1, name='prism', material=None):
    """Extrude a 2D outline (in XZ, centred at cx, cz) from y0 to y1 (y0 < y1)."""
    return kit.extrude([(cx + x, cz + z) for x, z in poly], y1 - y0, at=(0, y1, 0), rot=(90, 0, 0),
                       material=material, name=name)


# ---------------------------------------------------------------- body profile (a bell)
Z0 = 0.034                       # top of the base where the body starts
BODY = [(0.123, Z0), (0.122, 0.06), (0.118, 0.11), (0.111, 0.16), (0.1, 0.205), (0.09, 0.235),
        (0.08, 0.252), (0.072, 0.26), (0.06, 0.263)]
ZT = 0.263                       # flat top of the body


def body_r(z):
    for (r0, z0), (r1, z1) in zip(BODY, BODY[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return BODY[-1][0]


def body_slope(z, dz=0.004):
    return math.degrees(math.atan2(body_r(z - dz) - body_r(z + dz), 2 * dz))


def on_body(theta, z, off=0.0):
    """Point on the body surface at angle theta (degrees, 0 = front -Y, + = toward +X) and height z."""
    r = body_r(z) + off; a = math.radians(theta)
    return Vector((r * math.sin(a), -r * math.cos(a), z))


def body_lathe(inset, material=None, name='shell'):
    prof = [(0, Z0 - 0.002)] + [(max(r - inset, 0.001), z) for r, z in BODY] + [(0, ZT - inset)]
    return kit.lathe(prof, material=material, steps=96, name=name)


enamel = kit.mat('#86bcd6', rough=0.32, name='enamel_sky')
cream = kit.mat('cream', rough=0.42, name='base_cream')
chrome = kit.mat('chrome', rough=0.2, metal=0.85, name='chrome')
dark = kit.mat('#1f2326', rough=0.5, name='recess_dark')
panel = kit.mat('gunmetal', rough=0.4, name='panel')
waffle = kit.mat('honey', rough=0.65, name='waffle')
vanilla = kit.mat('#f3e6c6', rough=0.55, name='vanilla')
choc = kit.mat('#4a2a18', rough=0.4, name='chocolate')
smoke = kit.mat('#2a3236', rough=0.08, name='smoked_glass')
red = kit.mat('red', rough=0.35, name='button_red')
amber = kit.mat('amber', rough=0.3, emit=0.6, name='lamp_amber')
white = kit.mat('white', rough=0.4, name='button_white')
rubber = kit.mat('rubber', rough=0.8, name='rubber')

# ---------------------------------------------------------------- base: a wide flared dish
kit.lathe([(0, 0), (0.158, 0), (0.168, 0.003), (0.172, 0.009), (0.172, 0.015), (0.166, 0.02),
           (0.15, 0.024), (0.128, 0.03), (0.124, Z0 + 0.002), (0, Z0 + 0.002)],
          material=cream, steps=96, name='base')
kit.torus(0.1695, 0.0035, at=(0, 0, 0.0125), material=chrome, major=96, minor=8, name='base_trim')

# ---------------------------------------------------------------- body with recesses
body = body_lathe(0, enamel, name='body')
inner = lambda: body_lathe(0.0045, dark, name='inner')

# three pill slots down the front (her drawing: centred, wide, stacked)
for z, w in ((0.205, 0.088), (0.155, 0.098), (0.108, 0.104)):
    cut = prism_y(stadium(w, 0.026), -0.002, z, -0.3, 0.0, material=dark)
    boolean(cut, inner())
    boolean(body, cut)
# tall fill window on the left
def radial_prism(poly, theta, zc, material=None, name='prism'):
    o = prism_y(poly, 0, 0, -0.3, 0.0, material=material, name=name)
    o.rotation_euler = (math.radians(90), 0, math.radians(theta)); o.location.z = zc
    return o


WIN_T, WIN_Z = -42, 0.158
cut = radial_prism(stadium(0.03, 0.13), WIN_T, WIN_Z, smoke)
boolean(cut, inner())
boolean(body, cut)
kit.finish(body, None, bevel=0.0015, segments=2)

# smoked glass, with the chocolate fill showing in the lower part (her drawing shades it dark)
# (the recess floor takes the smoked-glass material; the fill sits just proud of it)
g = radial_prism(stadium(0.025, 0.095), WIN_T, WIN_Z - 0.0155, choc, 'win_fill')
boolean(g, body_lathe(0.0034), op='INTERSECT'); boolean(g, body_lathe(0.008))
# chrome bezel around the window
pts = []
for x, z in stadium(0.036, 0.136, 12):
    zz = 0.158 + z
    a = -42 + math.degrees(x / body_r(zz))
    pts.append(on_body(a, zz, 0.0012))
cu = bpy.data.curves.new('bezel', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
for p, c in zip(sp.points, pts):
    p.co = (*c, 1)
sp.use_cyclic_u = True; cu.bevel_depth = 0.0022; cu.bevel_resolution = 1
ob = bpy.data.objects.new('bezel', cu); bpy.context.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.convert(target='MESH'); kit.finish(bpy.context.object, chrome)

# ---------------------------------------------------------------- right side: two-button strip and oval lens
strip = radial_prism(stadium(0.026, 0.1, 6), 40, 0.165, panel, 'strip')
boolean(strip, body_lathe(-0.004), op='INTERSECT')
kit.finish(strip, None, bevel=0.0012)
for z in (0.192, 0.14):
    p = on_body(40, z, 0.0035)
    kit.cyl(0.0055, 0.006, at=p, rot=(90 - body_slope(z), 0, 40), material=red if z > 0.15 else white, verts=20,
            bevel=0.001, name='strip_button')
# split line across the strip
p = on_body(40, 0.166, 0.004)
kit.box((0.024, 0.002, 0.0018), at=p, rot=(0, 0, 40), material=dark, name='strip_split')
# oval lens above it
lens = kit.sphere(0.012, at=(0, 0, 0), scale=(1.25, 0.45, 0.85), material=smoke, segs=24, rings=12, name='lens')
lens.location = on_body(30, 0.228, -0.001); lens.rotation_euler = (math.radians(-body_slope(0.228)), 0, math.radians(30))
ring = kit.torus(0.0122, 0.0018, at=on_body(30, 0.228, 0.0005), rot=(90 - body_slope(0.228), 0, 30), material=chrome,
                 major=24, minor=6, name='lens_ring')
ring.scale = (1.25, 0.85, 1)

# ---------------------------------------------------------------- control band around the bottom
kit.lathe([(0, 0.044), (0.1235, 0.044), (0.1255, 0.047), (0.1255, 0.072), (0.1215, 0.075), (0, 0.075)],
          material=panel, steps=96, name='control_band')
for z in (0.044, 0.075):
    kit.torus(body_r(z) + 0.002, 0.0016, at=(0, 0, z), material=chrome, major=96, minor=6, name='band_trim')
BR = 0.1255


def on_band(theta, off=0.0, z=0.0595):
    a = math.radians(theta)
    return Vector(((BR + off) * math.sin(a), -(BR + off) * math.cos(a), z))


# left -> right as drawn: two small round buttons, a rocker, a round button, a ring knob,
# a slider, a play button, a pair of switches and a pilot light
for th in (-62, -56):
    kit.cyl(0.0042, 0.006, at=on_band(th, 0.002), rot=(90, 0, th), material=white, verts=16, bevel=0.0008, name='btn')
kit.box((0.016, 0.006, 0.008), at=on_band(-47, 0.0015), rot=(0, 0, -47), material=dark, bevel=0.0015, name='rocker')
kit.box((0.012, 0.004, 0.005), at=on_band(-47, 0.004), rot=(0, 0, -47), material=white, bevel=0.0012, name='rocker_key')
kit.cyl(0.0045, 0.006, at=on_band(-36, 0.002), rot=(90, 0, -36), material=red, verts=16, bevel=0.0008, name='btn')
kit.torus(0.0062, 0.0018, at=on_band(-26, 0.001), rot=(90, 0, -26), material=chrome, major=20, minor=6, name='ring_knob')
kit.cyl(0.0035, 0.004, at=on_band(-26, 0.0015), rot=(90, 0, -26), material=dark, verts=16, name='ring_knob_c')
# slider: a slot with a knob
for k in range(9):
    th = -14 + k * 2.4
    kit.box((0.0055, 0.003, 0.0018), at=on_band(th, 0.0003), rot=(0, 0, th), material=dark, name='slider_slot')
kit.box((0.009, 0.008, 0.011), at=on_band(-2, 0.003), rot=(0, 0, -2), material=chrome, bevel=0.0015, name='slider_knob')
for th in (-14.5, 5.5):
    kit.cyl(0.0022, 0.004, at=on_band(th, 0.001), rot=(90, 0, th), material=chrome, verts=12, name='slider_end')
# play button with a raised triangle
kit.box((0.026, 0.006, 0.013), at=on_band(15, 0.0015), rot=(0, 0, 15), material=white, bevel=0.002, name='play')
tri = kit.extrude([(-0.003, -0.0035), (0.004, 0.0), (-0.003, 0.0035)], 0.0015, material=dark, name='play_tri')
tri.rotation_euler = (math.radians(90), 0, math.radians(15)); tri.location = on_band(15, 0.0045)
for th, wd in ((29, 0.009), (36, 0.014)):
    kit.box((wd, 0.005, 0.009), at=on_band(th, 0.0015), rot=(0, 0, th), material=white, bevel=0.0015, name='switch')
kit.sphere(0.0035, at=on_band(48, 0.001, 0.063), material=amber, segs=12, rings=6, name='pilot')

# ---------------------------------------------------------------- top: waffle ring and the soft-serve swirl
me = bpy.data.meshes.new('waffle_ring'); bm = bmesh.new()
NU, NV, RR, rr = 168, 24, 0.061, 0.0165
grid = []
for i in range(NU):
    u = math.tau * i / NU; row = []
    for j in range(NV):
        v = math.tau * j / NV
        # a waffle: two families of crossing ridges
        g_ = min(abs(math.sin(14 * u + 2 * v)), abs(math.sin(14 * u - 2 * v)))
        d = -0.0022 * max(0.0, 1 - g_ / 0.32) ** 1.5
        r = rr + d
        row.append(bm.verts.new(((RR + r * math.cos(v)) * math.cos(u), (RR + r * math.cos(v)) * math.sin(u),
                                 ZT + 0.006 + r * math.sin(v) * 0.8)))
    grid.append(row)
for i in range(NU):
    for j in range(NV):
        bm.faces.new((grid[i][j], grid[(i + 1) % NU][j], grid[(i + 1) % NU][(j + 1) % NV], grid[i][(j + 1) % NV]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
o = bpy.data.objects.new('waffle_ring', me); bpy.context.collection.objects.link(o); kit.finish(o, waffle)

# soft serve: a star-nozzle section swept up a tightening helix, ending in a curled tip
star = []
for k in range(8 * 3):
    a = math.tau * k / 24
    star.append(((1 + 0.13 * math.cos(8 * a)) * math.cos(a), (1 + 0.13 * math.cos(8 * a)) * math.sin(a)))
path, scl = [], []
turns, N = 2.6, 112
for i in range(N + 1):
    t = i / N
    a = math.tau * turns * t
    R = 0.036 * (1 - t) ** 0.85
    z = ZT + 0.022 + 0.105 * t
    path.append((R * math.cos(a), R * math.sin(a), z))
    scl.append(0.025 * (1 - 0.55 * t))
# the tip: rise and hook over to one side (like the drawing's flame-shaped top)
last = Vector(path[-1])
for i in range(1, 25):
    t = i / 24
    path.append((last.x + 0.03 * t ** 1.6, last.y - 0.008 * t, last.z + 0.05 * math.sin(t * math.pi / 2) - 0.004 * t ** 3))
    scl.append(0.01125 * (1 - t) ** 0.9 + 0.0004)
sweep(path, star, scl, vanilla, name='swirl')
kit.lathe([(0, ZT), (0.05, ZT), (0.052, ZT + 0.02), (0.035, ZT + 0.05), (0.018, ZT + 0.09), (0, ZT + 0.1)],
          material=vanilla, steps=48, name='swirl_core')

# ---------------------------------------------------------------- the arm and the little cone (right side)
root_z = 0.2
root = on_body(90, root_z, -0.002)
kit.cyl(0.016, 0.014, at=on_body(90, root_z, 0.004), rot=(90 - body_slope(root_z), 0, 90), material=chrome, verts=32,
        bevel=0.002, name='arm_boss')
d = Vector((math.cos(math.radians(28)), math.sin(math.radians(28)), 0.16)).normalized()
L = 0.11
a0 = on_body(90, root_z, 0.008)
a1 = a0 + d * L
arm = kit.box((L, 0.012, 0.006), at=(a0 + a1) / 2, material=chrome, bevel=0.0025, name='arm')
arm.rotation_euler = d.to_track_quat('X', 'Z').to_euler()
kit.box((L * 0.7, 0.013, 0.0012), at=(a0 + a1) / 2 + Vector((0, 0, 0.0034)), material=dark, name='arm_inlay').rotation_euler = arm.rotation_euler
# cup ring at the end holding a cone
tip = a1 + d * 0.006
kit.torus(0.0125, 0.0028, at=tip, material=chrome, major=32, minor=8, name='cone_ring')
cone = kit.lathe([(0, -0.052), (0.0016, -0.05), (0.0125, -0.002), (0.0135, 0.002), (0, 0.002)],
                 at=tip, material=waffle, steps=32, name='cone')
for k in range(6):  # waffle score lines
    z = -0.008 - k * 0.007
    rr_ = 0.0125 * (z + 0.052) / 0.05 + 0.0003
    kit.torus(rr_, 0.0007, at=tip + Vector((0, 0, z)), material=kit.mat('#a8702e', rough=0.7, name='waffle_dark'),
              major=24, minor=4, name='cone_line')
kit.sphere(0.0135, at=tip + Vector((0, 0, 0.009)), material=choc, segs=24, rings=12, name='scoop')

# ---------------------------------------------------------------- back: louvred vent and the power inlet
for k in range(7):
    th = 180 - 18 + k * 6
    cut = radial_prism(stadium(0.007, 0.075, 6), th, 0.16, dark)
    boolean(cut, inner())
    boolean(body, cut)
p = on_band(180, 0.004)
kit.box((0.022, 0.008, 0.016), at=p, rot=(0, 0, 180), material=panel, bevel=0.002, name='inlet')
kit.box((0.012, 0.004, 0.006), at=on_band(180, 0.008), rot=(0, 0, 180), material=dark, name='inlet_hole')
kit.box((0.06, 0.003, 0.018), at=on_body(180, 0.225, 0.0005), rot=(-body_slope(0.225), 0, 180), material=chrome,
        bevel=0.0012, name='badge')

kit.export('hand-mixer')
