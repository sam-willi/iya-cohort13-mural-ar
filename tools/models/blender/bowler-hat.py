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

# ---------------------------------------------------------------- model
# Bowler hat (no student drawing in the folder: a classic brown felt bowler).
# Oval crown with a domed top, brim curled up at the sides, grosgrain band with a flat bow on the wearer's left,
# bound brim edge, satin lining and a leather sweatband inside.
FELT = kit.mat('#2e1d15', rough=0.82, name='felt')
RIBBON = kit.mat('#1e1b19', rough=0.5, name='grosgrain')
SATIN = kit.mat('cardinal', rough=0.35, name='satin')
LEATHER = kit.mat('#8a5a32', rough=0.55, name='leather')

OVAL = 1.12            # head shape: longer front-to-back (y)
R_IN = 0.083           # crown base radius (x)
R_OUT = 0.135          # brim edge radius at the sides (x)
BRIM_T = 0.003
CURL = 0.03           # brim lift at the sides
DIP = 0.004            # brim drop at front and back

def brim_lift(x, y):
    """Height offset of the brim at (x, y) before oval scaling."""
    r = math.hypot(x, y)
    if r <= R_IN: return 0.0
    s = min(1.0, (r - R_IN) / (R_OUT - R_IN))
    c2 = (x / r) ** 2
    return CURL * s ** 2.2 * c2 ** 1.3 - DIP * s ** 2 * (1 - c2)

# crown: felt outside, satin inside (solidify material offset)
H = 0.128; Z0 = 0.042; RB = R_IN + 0.0022; NSUP = 2.15
crown_prof = [(R_IN, 0.0006), (R_IN + 0.0008, 0.014), (R_IN + 0.0016, 0.028), (RB, Z0)]
for i in range(1, 19):
    t = (math.pi / 2) * i / 18
    crown_prof.append((RB * math.cos(t) ** (2 / NSUP) if i < 18 else 0.0, Z0 + (H - Z0) * math.sin(t) ** (2 / NSUP)))
crown = kit.lathe(crown_prof, steps=96, name='crown')
crown.data.materials.append(FELT); crown.data.materials.append(SATIN)
md = crown.modifiers.new('solid', 'SOLIDIFY'); md.thickness = 0.003; md.offset = -1; md.use_even_offset = True
md.material_offset = 1; md.use_rim = True

# brim: flat annulus (two rings of verts per radius step) bent by brim_lift
bm = bmesh.new(); NA = 128; radii = [R_IN - 0.0025 + (R_OUT - R_IN + 0.0025) * (i / 12) ** 1.0 for i in range(13)]
top, bot = [], []
for r in radii:
    rt, rb = [], []
    for k in range(NA):
        a = math.tau * k / NA; x, y = r * math.cos(a), r * math.sin(a); z = brim_lift(x, y)
        rt.append(bm.verts.new((x, y, z + BRIM_T))); rb.append(bm.verts.new((x, y, z)))
    top.append(rt); bot.append(rb)
for ring in (top, bot):
    for i in range(len(radii) - 1):
        for k in range(NA):
            j = (k + 1) % NA
            bm.faces.new((ring[i][k], ring[i][j], ring[i + 1][j], ring[i + 1][k]))
for k in range(NA):  # inner wall (hidden by the crown)
    j = (k + 1) % NA
    bm.faces.new((top[0][k], top[0][j], bot[0][j], bot[0][k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
brim = _mesh_obj('brim', bm); kit.finish(brim, FELT)

# bound edge: a rolled grosgrain binding following the curled brim edge
edge = []
for k in range(NA):
    a = math.tau * k / NA; x, y = R_OUT * math.cos(a), R_OUT * math.sin(a)
    edge.append((x, y, brim_lift(x, y) + BRIM_T / 2))
binding = sweep(edge, circle2(0.0032, 12), name='binding', loop=True, material=RIBBON)

# grosgrain band around the crown base, hugging the crown profile
band_prof = [(R_IN + 0.0012, BRIM_T - 0.0005), (R_IN + 0.0026, 0.012), (R_IN + 0.0032, 0.024), (R_IN + 0.0034, 0.033),
             (R_IN + 0.0017, 0.0335), (R_IN + 0.0016, 0.024), (R_IN + 0.001, 0.012), (R_IN - 0.0004, BRIM_T - 0.0005)]
band = kit.lathe(band_prof + [band_prof[0]], steps=96, name='band', material=RIBBON)

# flat bow on the wearer's left (+x when the hat faces -y): two pinched ribbon loops, a knot and two tails
bx = R_IN + 0.0042; bz = 0.0185
for s_ in (-1, 1):
    lp = kit.box((0.0042, 0.02, 0.022), at=(bx, s_ * 0.0125, bz), material=RIBBON, bevel=0.0018, segments=3, name='bowloop')
    for v in lp.data.vertices:  # pinch toward the knot
        u = (s_ * v.co.y + 0.01) / 0.02
        v.co.z *= 0.42 + 0.58 * math.sin(min(1.0, u * 1.5) * math.pi / 2)
        v.co.x -= 0.0012 * (1 - u)  # loops lie flatter against the band at the knot
kit.box((0.0056, 0.0075, 0.0135), at=(bx + 0.0008, 0, bz), material=RIBBON, bevel=0.002, segments=3, name='knot')

# leather sweatband inside the crown
sweat_prof = [(R_IN - 0.0042, 0.0), (R_IN - 0.0042, 0.04), (R_IN - 0.0058, 0.04), (R_IN - 0.0058, 0.0)]
kit.lathe(sweat_prof + [sweat_prof[0]], steps=96, name='sweatband', material=LEATHER)

# oval everything, then stand it on its brim
for o in list(bpy.context.scene.objects):
    xform(o, scale=(1.0, OVAL, 1.0))
ground(0.0)

kit.export('bowler-hat')
