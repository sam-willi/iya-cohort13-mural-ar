"""Treadmill (no student drawing in the folder: a generic home treadmill, modelled at real size).

Length runs along X so the turntable opens on the classic side profile. Belt wrapped round two rollers, aluminium side
rails with ribbed foot strips, a motor hood, raked uprights, a tilted console (amber track display, buttons, cup
holders, the red safety key on its coiled cord) and handrails with sensor grips. Accent stripes in the mural's orange.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
from mathutils import Vector, Matrix

# ---------------------------------------------------------------- helpers
def mesh_obj(name, verts, faces, material=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    return o


def side_extrude(poly_xz, y0, y1, material, bevel=0.0, segments=2, name='ext'):
    """Extrude a polygon drawn in the XZ plane (side view) across Y from y0 to y1."""
    o = kit.extrude([(x, z) for x, z in poly_xz], y1 - y0, material=material, bevel=bevel, segments=segments, name=name)
    o.rotation_euler = (math.radians(90), 0, 0)   # local z (extrude) -> world -y
    o.location = (0, y1, 0)
    return o


def bar(p0, p1, w, h, material, bevel=0.01, up=(0, 0, 1), name='bar'):
    """A rounded rectangular bar from p0 to p1; w across, h in the `up` direction."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = kit.box((d.length, w, h), material=material, bevel=bevel, segments=3, name=name)
    x = d.normalized(); u = Vector(up); z = (u - x * u.dot(x)).normalized(); y = z.cross(x)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Matrix((x, y, z)).transposed().to_quaternion()
    o.location = (p0 + p1) / 2
    return o


def rod(p0, p1, r, material, verts=24, bevel=0.0, name='rod'):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = kit.cyl(r, d.length, material=material, verts=verts, bevel=bevel, name=name)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.location = (p0 + p1) / 2
    return o


def _catmull(points, subdiv, closed=False):
    P = [Vector(p) for p in points]
    if len(P) < 3 or subdiv <= 1:
        return P
    out = []
    n = len(P)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if closed else P[max(i - 1, 0)]
        p1 = P[i]; p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed else P[min(i + 2, n - 1)]
        for k in range(subdiv):
            t = k / subdiv; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def tube(points, r, material=None, sides=8, subdiv=4, closed=False, caps=True, name='tube', smooth=True):
    """Swept circle along a Catmull-Rom path (parallel-transport frames). r: float or callable t->radius."""
    P = _catmull(points, subdiv, closed)
    n = len(P)
    rad = (lambda t: r) if not callable(r) else r
    T = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[i - 1]
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        T.append(t.normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    verts, faces = [], []
    for i in range(n):
        if i:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-8:
                ang = T[i - 1].angle(T[i])
                N = (Matrix.Rotation(ang, 3, b.normalized()) @ N)
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        rr = rad(i / max(n - 1, 1))
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(P[i] + (N * math.cos(a) + B * math.sin(a)) * rr)
    rings = n if not closed else n
    for i in range(rings - (0 if closed else 1)):
        j = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, j * sides + k2, j * sides + k))
    if caps and not closed:
        c0 = len(verts); verts.append(P[0]); c1 = len(verts); verts.append(P[-1])
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k))
            faces.append((c1, (n - 1) * sides + k, (n - 1) * sides + k2))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return kit.finish(o, None, smooth=50 if smooth else 0)


# ---------------------------------------------------------------- materials
M_FRAME = kit.mat('#34373c', rough=0.45, metal=0.2, name='frame_plastic')
M_ALU = kit.mat('#9aa0a8', rough=0.32, metal=0.85, name='aluminium')
M_DARK = kit.mat('#1f2023', rough=0.5, name='dark_plastic')
M_BELT = kit.mat('#1a1a1a', rough=0.82, name='belt')
M_RUBBER = kit.mat('rubber', rough=0.85, name='rubber')
M_ACCENT = kit.mat('orange', rough=0.4, name='accent')
M_SCREEN = kit.mat('#101418', rough=0.12, name='screen')
M_LED = kit.mat('amber', rough=0.3, emit=2.5, name='led')
M_LED_DIM = kit.mat('#7a4a14', rough=0.3, emit=0.6, name='led_dim')
M_BTN = kit.mat('#d9dadc', rough=0.4, name='button')
M_BTN_OR = kit.mat('orange', rough=0.35, name='button_orange')
M_RED = kit.mat('red', rough=0.35, name='safety_red')
M_CHROME = kit.mat('chrome', rough=0.22, metal=1.0, name='chrome')
M_FOAM = kit.mat('#2a2a2b', rough=0.9, name='foam')

# ---------------------------------------------------------------- dimensions
X_REAR, X_FRONT = -0.86, 0.60      # belt rollers' outer ends
RR = 0.032                         # roller radius
Z_BELT = 0.19                      # top of belt
BW = 0.25                          # belt half width
RAIL_IN, RAIL_OUT = 0.262, 0.385   # side rails
Z_RAIL = 0.205

# ---------------------------------------------------------------- belt: a stadium loop round two rollers
xr, xf = X_REAR + RR, X_FRONT - RR
zc = Z_BELT - RR
loop = []
for i in range(13):
    a = math.pi / 2 + math.pi * i / 12          # rear: top -> bottom
    loop.append((xr + RR * math.cos(a), zc + RR * math.sin(a)))
for i in range(13):
    a = -math.pi / 2 + math.pi * i / 12         # front: bottom -> top
    loop.append((xf + RR * math.cos(a), zc + RR * math.sin(a)))
inner = [(x + (xr - x) * 0.12 if x < xr else (x + (xf - x) * 0.12 if x > xf else x), z + (zc - z) * 0.12) for x, z in loop]
# belt as a closed band: outer loop + inner loop, extruded across the width
n = len(loop)
verts, faces = [], []
for y in (-BW, BW):
    for x, z in loop:
        verts.append((x, y, z))
    for x, z in inner:
        verts.append((x, y, z))
def vi(side, ring, i): return side * 2 * n + ring * n + (i % n)
for i in range(n):
    faces.append((vi(0, 0, i), vi(0, 0, i + 1), vi(1, 0, i + 1), vi(1, 0, i)))   # outer surface
    faces.append((vi(0, 1, i), vi(1, 1, i), vi(1, 1, i + 1), vi(0, 1, i + 1)))   # inner surface
    faces.append((vi(0, 0, i), vi(0, 1, i), vi(0, 1, i + 1), vi(0, 0, i + 1)))   # edge -y
    faces.append((vi(1, 0, i), vi(1, 0, i + 1), vi(1, 1, i + 1), vi(1, 1, i)))   # edge +y
belt = mesh_obj('belt', verts, faces, M_BELT)
kit.finish(belt, None, smooth=40)
# rollers inside the loop + the deck board between them
for x in (xr, xf):
    kit.cyl(RR * 0.86, 2 * BW + 0.03, at=(x, 0, zc), rot=(90, 0, 0), material=M_ALU, verts=32, name='roller')
kit.box((xf - xr - 0.02, 2 * BW - 0.01, 0.018), at=((xr + xf) / 2, 0, zc + 0.002), material=M_DARK, name='deck_board')

# ---------------------------------------------------------------- side rails: aluminium extrusion, ribbed foot strip, orange accent
L0, L1 = X_REAR - 0.02, 0.62
for s in (-1, 1):
    y0, y1 = sorted((s * RAIL_IN, s * RAIL_OUT))
    yc = (y0 + y1) / 2
    kit.box((L1 - L0, RAIL_OUT - RAIL_IN, Z_RAIL - 0.07), at=((L0 + L1) / 2, yc, (Z_RAIL + 0.07) / 2),
            material=M_ALU, bevel=0.012, segments=3, name='rail')
    # ribbed rubber foot strip on top
    kit.box((L1 - L0 - 0.1, RAIL_OUT - RAIL_IN - 0.03, 0.006), at=((L0 + L1) / 2 - 0.02, yc, Z_RAIL + 0.001),
            material=M_RUBBER, bevel=0.002, name='foot_strip')
    for k in range(5):
        yy = y0 + 0.022 + k * (RAIL_OUT - RAIL_IN - 0.044) / 4
        kit.box((L1 - L0 - 0.12, 0.006, 0.004), at=((L0 + L1) / 2 - 0.02, yy, Z_RAIL + 0.005), material=M_RUBBER,
                bevel=0.0015, name='rib')
    # accent stripe along the outer face
    kit.box((L1 - L0 - 0.16, 0.004, 0.012), at=((L0 + L1) / 2 + 0.02, s * (RAIL_OUT + 0.001), Z_RAIL - 0.045),
            material=M_ACCENT, bevel=0.0015, name='stripe')
    # rear end cap with the roller adjustment bolt
    cap = kit.box((0.09, RAIL_OUT - RAIL_IN + 0.01, Z_RAIL - 0.04), at=(L0 - 0.02, yc, (Z_RAIL + 0.04) / 2),
                  material=M_DARK, bevel=0.025, segments=3, name='end_cap')
    kit.cyl(0.008, 0.012, at=(L0 - 0.066, s * (RAIL_IN + 0.04), zc), rot=(0, 90, 0), material=M_CHROME, verts=6,
            bevel=0.001, name='adjust_bolt')
    # rear leveling foot and a front transport wheel
    kit.cyl(0.03, 0.04, at=(L0 + 0.02, yc, 0.02), material=M_RUBBER, verts=24, bevel=0.006, name='rear_foot')
    kit.cyl(0.035, 0.025, at=(0.93, s * 0.33, 0.035), rot=(90, 0, 0), material=M_RUBBER, verts=32, bevel=0.006, name='wheel')
    kit.cyl(0.012, 0.03, at=(0.93, s * 0.33, 0.035), rot=(90, 0, 0), material=M_ALU, verts=16, name='hub')
# lower frame under the deck
kit.box((L1 - L0 - 0.06, 2 * RAIL_OUT - 0.08, 0.05), at=((L0 + L1) / 2, 0, 0.065), material=M_DARK, bevel=0.01, name='frame')
for x in (-0.55, 0.0, 0.4):
    kit.box((0.06, 2 * RAIL_OUT - 0.1, 0.03), at=(x, 0, 0.025), material=M_DARK, bevel=0.008, name='crossmember')
    for s in (-1, 1):
        kit.cyl(0.022, 0.012, at=(x, s * (RAIL_OUT - 0.07), 0.006), material=M_RUBBER, verts=16, bevel=0.003, name='pad')

# ---------------------------------------------------------------- motor hood
hood_prof = [(0.56, 0.06), (0.98, 0.06), (0.99, 0.18), (0.95, 0.27), (0.84, 0.31), (0.66, 0.285), (0.58, 0.24), (0.56, 0.20)]
side_extrude(hood_prof, -RAIL_OUT - 0.005, RAIL_OUT + 0.005, M_FRAME, bevel=0.025, segments=4, name='hood')
for s in (-1, 1):
    kit.box((0.34, 0.004, 0.012), at=(0.80, s * (RAIL_OUT + 0.007), 0.22), rot=(0, -8, 0), material=M_ACCENT,
            bevel=0.0015, name='hood_stripe')
# vent slots on the hood top
def hood_top(x):
    pts = [(0.58, 0.24), (0.66, 0.285), (0.84, 0.31), (0.95, 0.27)]
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return z0 + (z1 - z0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


for k in range(6):
    x = 0.71 + k * 0.022
    ang = math.degrees(math.atan2(0.025, 0.18))
    kit.box((0.010, 0.34, 0.004), at=(x, 0, hood_top(x) - 0.0005), rot=(0, -ang, 0), material=M_DARK, bevel=0.0015, name='vent')
# power switch and cord at the front
kit.box((0.02, 0.05, 0.035), at=(0.99, -0.22, 0.12), material=M_DARK, bevel=0.004, name='switch_box')
kit.box((0.012, 0.022, 0.016), at=(1.0, -0.22, 0.125), material=M_RED, bevel=0.002, name='switch')

# ---------------------------------------------------------------- uprights, raked back toward the runner
TOP = Vector((0.66, 0, 1.06))
for s in (-1, 1):
    bar((0.88, s * 0.37, 0.22), (0.68, s * 0.37, 1.06), 0.05, 0.075, M_FRAME, bevel=0.018, up=(1, 0, 0.3), name='upright')
    kit.box((0.12, 0.07, 0.06), at=(0.88, s * 0.37, 0.24), material=M_DARK, bevel=0.015, name='upright_foot')

# ---------------------------------------------------------------- console: tilted housing with display and buttons
con = bpy.data.objects.new('console_pivot', None); bpy.context.collection.objects.link(con)
parts = []
parts.append(kit.box((0.20, 0.86, 0.09), material=M_FRAME, bevel=0.03, segments=4, name='console'))
parts.append(kit.box((0.15, 0.62, 0.012), at=(-0.005, 0, 0.046), material=M_DARK, bevel=0.004, name='console_face'))
parts.append(kit.box((0.085, 0.30, 0.006), at=(0.02, 0, 0.054), material=M_SCREEN, bevel=0.002, name='screen'))
# amber LED track (the 400 m oval) and a small bar graph, no lettering
for i in range(40):
    a = 2 * math.pi * i / 40
    parts.append(kit.box((0.004, 0.007, 0.002), at=(0.02 + 0.026 * math.sin(a), 0.075 * math.cos(a), 0.0575),
                         rot=(0, 0, math.degrees(math.atan2(0.026 * math.cos(a), -0.075 * math.sin(a)))),
                         material=M_LED, name='led'))
parts.append(kit.box((0.006, 0.006, 0.002), at=(0.02 + 0.026, 0.0, 0.0578), material=M_RED, name='runner_dot'))
for k in range(9):
    h = 0.008 + 0.004 * ((k * 7) % 5)
    parts.append(kit.box((h, 0.008, 0.002), at=(0.0 + h / 2 - 0.004, 0.10 + k * 0.012, 0.0575), material=M_LED if k < 6 else M_LED_DIM, name='bar'))
    parts.append(kit.box((h, 0.008, 0.002), at=(0.0 + h / 2 - 0.004, -0.10 - k * 0.012, 0.0575), material=M_LED_DIM if k % 3 else M_LED, name='bar'))
# buttons: speed (left) and incline (right) clusters, start/stop in the middle
for sgn in (-1, 1):
    for r in range(2):
        for c in range(3):
            parts.append(kit.cyl(0.0085, 0.006, at=(-0.045 + r * 0.022, sgn * (0.20 + c * 0.024), 0.054),
                                 material=M_BTN, verts=20, bevel=0.002, name='btn'))
    parts.append(kit.box((0.03, 0.05, 0.008), at=(-0.034, sgn * 0.27, 0.055), material=M_BTN_OR, bevel=0.003, name='key'))
parts.append(kit.cyl(0.014, 0.008, at=(-0.045, -0.035, 0.055), material=M_BTN_OR, verts=24, bevel=0.003, name='start'))
parts.append(kit.cyl(0.014, 0.008, at=(-0.045, 0.035, 0.055), material=M_RED, verts=24, bevel=0.003, name='stop'))
# cup holders at both ends
for sgn in (-1, 1):
    cup = kit.cyl(0.045, 0.06, at=(-0.01, sgn * 0.37, 0.005), material=M_FRAME, verts=40, bevel=0.006, name='cupholder')
    kit.boolean(cup, kit.cyl(0.036, 0.06, at=(-0.01, sgn * 0.37, 0.03), verts=40))
    parts.append(cup)
# safety key slot, red key, coiled cord, clip
parts.append(kit.box((0.03, 0.05, 0.02), at=(-0.095, 0, -0.005), material=M_DARK, bevel=0.005, name='key_slot'))
parts.append(kit.cyl(0.016, 0.012, at=(-0.106, 0, -0.005), rot=(0, 90, 0), material=M_RED, verts=24, bevel=0.003, name='safety_key'))
for k in range(8):
    parts.append(kit.box((0.012, 0.30, 0.004), at=(-0.05 + k * 0.014, 0, -0.045), material=M_DARK, bevel=0.0015, name='console_vent'))
for o in parts:
    o.parent = con
con.location = (0.72, 0, 1.12)
con.rotation_euler = (0, math.radians(-38), 0)   # face tilted up toward the runner (-X)

# coiled cord hanging from the key (in world space)
bpy.context.view_layer.update()
start = con.matrix_world @ Vector((-0.112, 0, -0.005))
coil = []
for i in range(150):
    t = i / 149
    a = t * 2 * math.pi * 12
    coil.append((start.x - 0.01 * t + 0.008 * math.cos(a), 0.008 * math.sin(a), start.z - 0.02 - 0.22 * t))
cu = bpy.data.curves.new('cord', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(coil) - 1)
for p, c in zip(sp.points, coil):
    p.co = (*c, 1)
cu.bevel_depth = 0.0018; cu.bevel_resolution = 1
co = bpy.data.objects.new('cord', cu); bpy.context.collection.objects.link(co)
bpy.context.view_layer.objects.active = co; co.select_set(True); bpy.ops.object.convert(target='MESH')
co = bpy.context.object; co.data.materials.append(M_RED)
end = Vector(coil[-1])
kit.box((0.012, 0.03, 0.04), at=(end.x, 0, end.z - 0.022), material=M_RED, bevel=0.004, name='clip')

# ---------------------------------------------------------------- handrails with sensor grips
for s in (-1, 1):
    path = [(0.735, s * 0.375, 0.84), (0.72, s * 0.40, 0.97), (0.64, s * 0.41, 1.035), (0.50, s * 0.41, 1.03),
            (0.36, s * 0.41, 1.0), (0.31, s * 0.41, 0.985)]
    tube(path, 0.019, material=M_FRAME, sides=20, subdiv=6, name='handrail')
    kit.sphere(0.019, at=path[-1], material=M_FRAME, segs=20, rings=10, name='rail_end')
    # foam grip at the back, steel heart-rate sleeves at the front
    tube([(0.47, s * 0.41, 1.026), (0.40, s * 0.41, 1.013), (0.33, s * 0.41, 0.989)], 0.0225, material=M_FOAM, sides=20,
         subdiv=3, name='grip')
    tube([(0.61, s * 0.41, 1.036), (0.57, s * 0.41, 1.035), (0.53, s * 0.41, 1.033)], 0.0215, material=M_CHROME, sides=20,
         subdiv=3, name='hr_sleeve')

kit.export('treadmill')
