import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion

# ---------------------------------------------------------------- local helpers (kept in this file on purpose)

def _mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return o


def loft(rings, name='loft', cap_start=True, cap_end=True, closed=True, loop=False, material=None, bevel=0.0, smooth=30):
    """Skin a list of rings (each a list of 3D points, same count). loop=True joins the last ring back to the first."""
    bm = bmesh.new()
    vs = [[bm.verts.new(tuple(p)) for p in ring] for ring in rings]
    n = len(rings[0])
    pairs = list(zip(vs, vs[1:])) + ([(vs[-1], vs[0])] if loop else [])
    for a, b in pairs:
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if not loop:
        if cap_start: bm.faces.new(vs[0][::-1])
        if cap_end: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _mesh_obj(name, bm)
    return kit.finish(o, material, bevel, smooth=smooth)


def rrect(w, h, r, seg=6, cx=0.0, cy=0.0):
    """Counter-clockwise rounded rectangle polygon."""
    r = min(r, w / 2 - 1e-5, h / 2 - 1e-5); pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def circle2(r, n=32, cx=0.0, cy=0.0, a0=0.0):
    return [(cx + r * math.cos(a0 + math.tau * i / n), cy + r * math.sin(a0 + math.tau * i / n)) for i in range(n)]


def rod(p0, p1, r, material=None, verts=16, name='rod', bevel=0.0, r2=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    o = kit.cyl(r, d.length, at=(p0 + p1) / 2, material=material, verts=verts, name=name, bevel=bevel, r2=r2)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return o


def fillet(pts, r, seg=6):
    """Round the corners of a polyline."""
    P = [Vector(p) for p in pts]; out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1 = (a - b).normalized(); d2 = (c - b).normalized()
        ang = d1.angle(d2)
        if ang > math.pi - 1e-3:
            out.append(b); continue
        t = min(r / math.tan(ang / 2), (a - b).length * 0.5, (c - b).length * 0.5)
        p1, p2 = b + d1 * t, b + d2 * t
        for k in range(seg + 1):
            s = k / seg; out.append((1 - s) ** 2 * p1 + 2 * (1 - s) * s * b + s * s * p2)
    out.append(P[-1])
    return out


def catmull(pts, n=8, closed=False):
    """Smooth path through points (Catmull-Rom)."""
    P = [Vector(p) for p in pts]; out = []
    m = len(P)
    segs = range(m) if closed else range(m - 1)
    for i in segs:
        p0 = P[(i - 1) % m] if (closed or i > 0) else P[0]
        p1 = P[i]; p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if (closed or i + 2 < m) else P[-1]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def frames(pts, up=(0, 0, 1), loop=False):
    P = [Vector(p) for p in pts]; m = len(P); T = []
    for i in range(m):
        if loop: t = P[(i + 1) % m] - P[(i - 1) % m]
        elif i == 0: t = P[1] - P[0]
        elif i == m - 1: t = P[-1] - P[-2]
        else: t = P[i + 1] - P[i - 1]
        T.append(t.normalized())
    n = Vector(up); n = n - n.dot(T[0]) * T[0]
    if n.length < 1e-6: n = T[0].orthogonal()
    n.normalize(); N = []
    for i in range(m):
        if i > 0:
            n = T[i - 1].rotation_difference(T[i]) @ n
            n = (n - n.dot(T[i]) * T[i]).normalized()
        N.append(n.copy())
    B = [T[i].cross(N[i]) for i in range(m)]
    return P, T, N, B


def sweep(pts, prof, name='sweep', loop=False, up=(0, 0, 1), material=None, bevel=0.0, caps=True, smooth=30, twist=None):
    """Sweep a 2D profile [(u, v), ...] (u along the frame normal, v along the binormal) along a path."""
    P, T, N, B = frames(pts, up, loop)
    rings = []
    for i in range(len(P)):
        n, b = N[i], B[i]
        if twist:
            a = twist(i / max(1, len(P) - 1)); n, b = n * math.cos(a) + b * math.sin(a), b * math.cos(a) - n * math.sin(a)
        rings.append([P[i] + n * u + b * v for u, v in prof])
    return loft(rings, name, cap_start=caps, cap_end=caps, loop=loop, material=material, bevel=bevel, smooth=smooth)


def apply_mods(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if o.type != 'MESH':
        bpy.ops.object.convert(target='MESH')
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)
    return o


def join(objs, name=None):
    for o in objs: apply_mods(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    if name: o.name = name
    return o


def solidify(o, t, offset=-1.0):
    md = o.modifiers.new('solid', 'SOLIDIFY'); md.thickness = t; md.offset = offset; md.use_even_offset = True
    return o


def xform(o, rot=None, loc=None, scale=None, apply=True):
    """Rotate (degrees XYZ) / move / scale an object and bake it into the mesh."""
    if scale: o.scale = scale
    if rot: o.rotation_mode = 'XYZ'; o.rotation_euler = [math.radians(a) for a in rot]
    if loc: o.location = loc
    if apply:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=bool(loc), rotation=bool(rot), scale=bool(scale))
    return o


def lowest_z():
    dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            e = o.evaluated_get(dg); m = e.to_mesh()
            for v in m.vertices:
                z = min(z, (e.matrix_world @ v.co).z)
            e.to_mesh_clear()
    return z


def ground(target=0.0):
    """Shift every root object so the lowest point sits on z=target."""
    dz = target - lowest_z()
    for o in bpy.context.scene.objects:
        if o.parent is None: o.location.z += dz

extrude, tube = kit.extrude, kit.tube

# ---------------------------------------------------------------- model
# Bicycle helmet, after Daniel Sunoo's drawing: a smooth in-mould shell, longer front-to-back and dropping lower at the
# back, with a centre spine between two long top vents, a big leaf-shaped vent sweeping up from each side of the brow,
# panel lines, a lower rim band, and Y-straps with sliders under the ears meeting at a side-release buckle. The back
# (rear vents, fit dial and cradle) is invented to match. Shell colours are chosen (the drawing is pencil).
SHELL = kit.mat('#ece7dc', rough=0.3, name='shell')
ACCENT = kit.mat('#4a4642', rough=0.4, name='lower_shell')
ORANGE = kit.mat('orange', rough=0.35, name='accent')
EPS = kit.mat('#2b2a29', rough=0.85, name='eps_foam')
WEB = kit.mat('#1f1e1d', rough=0.8, name='webbing')
PLASTIC = kit.mat('#262524', rough=0.45, name='buckle_plastic')
PAD = kit.mat('#3a3937', rough=0.95, name='pad')

A = 0.106                  # half width (x)
CZ = 0.124                 # height of the crown above the equator
def Bf(phi): return 0.141 - 0.012 * math.cos(phi)          # half length: blunter front, longer tail
def z_rim(phi): return -0.024 + 0.03 * math.cos(phi) - 0.006 * math.cos(2 * phi)
def theta_rim(phi): return math.acos(max(-0.99, min(0.99, z_rim(phi) / CZ)))


def surf(phi, s, grow=0.0):
    """Outer shell point. phi: azimuth (0 = front, -y), s: 0 at the crown .. 1 at the rim."""
    th = s * theta_rim(phi)
    return Vector(((A + grow) * math.sin(th) * math.sin(phi), -(Bf(phi) + grow) * math.sin(th) * math.cos(phi),
                   (CZ + grow) * math.cos(th)))


def project(p, grow=0.0):
    """Push a point along the ray from the centre onto the shell surface (approximate inverse of surf)."""
    p = Vector(p); ph = math.atan2(p.x / A, -p.y / 0.141)
    k = 1 / math.sqrt((p.x / (A + grow)) ** 2 + (p.y / (Bf(ph) + grow)) ** 2 + (p.z / (CZ + grow)) ** 2)
    return p * k


def cut(target, cutter):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)


# ---- shell surface (crown pole + rings down to the rim), accent spine and lower band by face
NP, NS = 96, 34; SPINE = 0.019; BAND = 0.92
bm = bmesh.new()
pole = bm.verts.new(surf(0, 0))
rows = [[bm.verts.new(surf(math.tau * i / NP, j / NS)) for i in range(NP)] for j in range(1, NS + 1)]
faces = []
for i in range(NP):
    faces.append(bm.faces.new((pole, rows[0][i], rows[0][(i + 1) % NP])))
for j in range(NS - 1):
    for i in range(NP):
        faces.append(bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][(i + 1) % NP], rows[j][(i + 1) % NP])))
for f in bm.faces:
    c = f.calc_center_median()
    s_est = None
    f.material_index = 0
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# lower band by row
for j in range(NS - 1):
    if (j + 1.5) / NS > BAND:
        for i in range(NP):
            faces[NP + j * NP + i].material_index = 1
shell = _mesh_obj('shell', bm)
for m in (SHELL, ACCENT, EPS): shell.data.materials.append(m)
if sum((p.center.normalized()).dot(p.normal) for p in shell.data.polygons) < 0:
    shell.data.flip_normals()
md = shell.modifiers.new('solid', 'SOLIDIFY'); md.thickness = 0.021; md.offset = -1; md.use_even_offset = True
md.material_offset = 2; md.material_offset_rim = 2
for p in shell.data.polygons: p.use_smooth = True
apply_mods(shell)

# ---- vents: radial prisms through the shell from outlines drawn on the surface
def vent_cutter(outline, name='vent'):
    outer = [p * 1.25 for p in outline]; inner = [p * 0.45 for p in outline]
    c = loft([inner, outer], name=name, smooth=0)
    c.data.materials.append(EPS)
    return c

def smooth_outline(pts, n=5):
    return catmull(pts, n, closed=True)

def leaf(sx):
    # (phi deg, s) round the leaf: lower front tip near the brow, upper back tip toward the crown
    up = [(18, 0.80), (28, 0.70), (42, 0.59), (58, 0.5), (76, 0.43), (96, 0.375)]
    lo = [(90, 0.48), (74, 0.6), (58, 0.69), (42, 0.765), (30, 0.82), (22, 0.835)]
    pts = smooth_outline([surf(sx * math.radians(a), s) for a, s in up + lo])
    return [project(p) for p in pts]

def top_slot(sx):
    xy = [(0.026, -0.098), (0.036, -0.104), (0.048, -0.075), (0.056, -0.03), (0.058, 0.02), (0.054, 0.062), (0.045, 0.088),
          (0.036, 0.082), (0.031, 0.045), (0.028, 0.0), (0.026, -0.05)]
    pts = smooth_outline([Vector((sx * x, y, 0.12)) for x, y in xy])
    pts = [project(p) for p in pts]
    return pts if sx > 0 else pts[::-1]

def rear_slot(sx):
    pts = [(150, 0.5), (158, 0.47), (163, 0.53), (163, 0.68), (158, 0.74), (151, 0.7), (149, 0.6)]
    out = [project(p) for p in smooth_outline([surf(sx * math.radians(a), s) for a, s in pts])]
    return out if sx > 0 else out[::-1]

for sx in (1, -1):
    lf = leaf(sx); lf = lf if sx > 0 else lf[::-1]
    for outline in (lf, top_slot(sx), rear_slot(sx)):
        cut(shell, vent_cutter(outline))

# ---- panel lines: shallow grooves along curves on the surface
def groove(points, r=0.0012, loop=False):
    pts = [project(p, grow=0.0004) for p in points]
    c = sweep(pts, circle2(r, 6), name='groove', loop=loop, smooth=0)
    c.data.materials.append(EPS)
    cut(shell, c)

for sx in (1, -1):
    # spine edges, front brow over the crown to the tail
    line = []
    for k in range(31):
        t = -1 + 2 * k / 30; th = t * 1.62
        line.append(Vector((sx * SPINE, -0.14 * math.sin(th) if t < 0 else -0.155 * math.sin(th), CZ * math.cos(th))))
    groove(line[2:-2])
    # sweeping side panel line: from the brow under the leaf vent back along the side to the tail
    side = [surf(sx * math.radians(a), s) for a, s in [(14, 0.885), (36, 0.85), (64, 0.75), (96, 0.62), (126, 0.56), (150, 0.6), (168, 0.72)]]
    groove(catmull(side, 6))
    # outline around the leaf vent (the raised frame in the drawing)
    rim_l = [surf(sx * math.radians(a), s) for a, s in [(14, 0.84), (26, 0.7), (44, 0.58), (64, 0.49), (88, 0.405), (108, 0.34), (118, 0.33)]]
    groove(catmull(rim_l, 6))
# the lower band seam all round
groove([surf(math.tau * i / 120, BAND - 0.012) for i in range(120)], loop=True)
kit.finish(shell, None, bevel=0.0012, segments=1, smooth=34)

# ---- inside: comfort pads on the foam
for (a, s, w, h) in [(0, 0.55, 0.05, 0.03), (90, 0.55, 0.04, 0.05), (-90, 0.55, 0.04, 0.05), (0, 0.15, 0.06, 0.05)]:
    c = surf(math.radians(a), s, grow=-0.0215)
    n = c.normalized()
    pad = kit.box((w, 0.006, h), name='pad', material=PAD, bevel=0.0025, segments=3)
    pad.rotation_mode = 'QUATERNION'; pad.rotation_quaternion = Vector((0, -1, 0)).rotation_difference(-n)
    pad.location = c - n * 0.003

# ---- rear fit system: a cradle band round the back and a ribbed dial
cradle = []
for k in range(15):
    a = math.radians(105 + 150 * k / 14)
    p = surf(a, 0.97, grow=-0.024); p.z -= 0.022 + 0.01 * math.sin(math.pi * k / 14)
    cradle.append(p)
sweep(cradle, [(-0.0015, -0.007), (0.0015, -0.007), (0.0015, 0.007), (-0.0015, 0.007)], name='cradle', up=(0, 1, 0),
      material=PLASTIC, smooth=40)
back = surf(math.pi, 0.97, grow=-0.024); back.z -= 0.032
dial = kit.cyl(0.016, 0.011, at=back + Vector((0, 0.004, 0)), rot=(90, 0, 0), material=PLASTIC, verts=32, bevel=0.002, name='dial')
for k in range(16):
    a = math.tau * k / 16
    kit.box((0.002, 0.011, 0.003), at=back + Vector((0.0165 * math.cos(a), 0.004, 0.0165 * math.sin(a))), rot=(0, -math.degrees(a), 0),
            material=PLASTIC, name='dial_rib')
kit.cyl(0.006, 0.003, at=back + Vector((0, 0.011, 0)), rot=(90, 0, 0), material=ORANGE, verts=20, name='dial_cap')

# ---- Y-straps, sliders under the ears and the buckle under the chin
WEB_PROF = [(-0.0008, -0.0075), (0.0008, -0.0075), (0.0008, 0.0075), (-0.0008, 0.0075)]
BUCKLE = Vector((0.0, -0.07, -0.165))
for sx in (1, -1):
    front_anchor = surf(sx * math.radians(52), 0.985, grow=-0.012)
    rear_anchor = surf(sx * math.radians(128), 0.985, grow=-0.012)
    slider = Vector((sx * 0.08, -0.015, -0.078))
    sweep(catmull([front_anchor + Vector((0, 0, 0.004)), front_anchor + Vector((sx * 0.006, 0.004, -0.02)),
                   slider + Vector((0, -0.006, 0.012)), slider], 6), WEB_PROF, name='strap_front', up=(sx, 0, 0), material=WEB)
    sweep(catmull([rear_anchor + Vector((0, 0, 0.004)), rear_anchor + Vector((sx * 0.004, -0.008, -0.025)),
                   slider + Vector((0, 0.008, 0.014)), slider], 6), WEB_PROF, name='strap_rear', up=(sx, 0, 0), material=WEB)
    end = BUCKLE + Vector((sx * 0.021, 0, 0.002))
    sweep(catmull([slider, slider + Vector((-sx * 0.006, -0.012, -0.03)), end + Vector((sx * 0.02, 0.008, 0.022)), end], 8),
          WEB_PROF, name='strap_chin', up=(sx, 0, 0), material=WEB)
    # slider: a frame with a window, the webbing threading through it
    d = (slider + Vector((-sx * 0.006, -0.012, -0.03)) - slider).normalized()
    sl = kit.box((0.006, 0.022, 0.026), name='slider', material=PLASTIC, bevel=0.0018, segments=2)
    win = kit.box((0.012, 0.011, 0.007), name='slwin'); kit.boolean(sl, win)
    sl.rotation_mode = 'QUATERNION'; sl.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(d); sl.location = slider + d * 0.004
# side-release buckle: female receiver and male tongue
fem = kit.box((0.03, 0.012, 0.024), at=BUCKLE + Vector((0.012, 0, 0)), material=PLASTIC, bevel=0.003, segments=2, name='buckle_f')
male = kit.box((0.022, 0.008, 0.018), at=BUCKLE + Vector((-0.012, 0, 0)), material=PLASTIC, bevel=0.0025, segments=2, name='buckle_m')
for sz in (-1, 1):
    kit.box((0.011, 0.0035, 0.004), at=BUCKLE + Vector((0.014, -0.0062, sz * 0.008)), material=PLASTIC, bevel=0.001, name='buckle_tab')
for o in (fem, male):
    o.rotation_euler = (math.radians(-12), 0, 0)

ground(0.0)
kit.export('bicycle-helmet')
