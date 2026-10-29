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
# Tea set, after Grace Bishara's drawing: a round, flat drum teapot standing on a flat-cut base, a squared loop handle
# on one side, a straight spout angled up on the other, a curved flap lid set into the top of the rim with a little knob
# and a steam hole beside it; and a square tea cup with flared sides, full of tea. Glazed teal stoneware with a cream
# glaze inside the cup (the drawing is pencil; colours are chosen from the mural palette).
GLAZE = kit.mat('#2b6f77', rough=0.22, name='glaze')
CREAM = kit.mat('cream', rough=0.25, name='cream_glaze')
BISQUE = kit.mat('#d6cab4', rough=0.8, name='unglazed_foot')
TEA = kit.mat('#7a3b10', rough=0.05, name='tea')
WALNUT = kit.mat('walnut', rough=0.5, name='walnut')
HOLE = kit.mat('#141414', rough=0.7, name='hole')

R = 0.086; T = 0.066; E = 0.014; BULGE = 0.0035
CUT = 0.86 * R            # flat base this far below the centre


def cut(target, cutter, transfer=True):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    if transfer: md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)


def rim_point(phi, rad=R, y=0.0):
    """phi measured from the top, toward +x."""
    return Vector((rad * math.sin(phi), y, rad * math.cos(phi)))

# ---- drum body: lathe about z, then turned so the axis runs front-to-back
prof = [(0, -T / 2 - BULGE), (0.03, -T / 2 - BULGE * 0.86), (0.055, -T / 2 - BULGE * 0.5), (R - E, -T / 2)]
for k in range(1, 8):
    a = (math.pi / 2) * k / 8; prof.append((R - E + E * math.sin(a), -T / 2 + E - E * math.cos(a)))
prof.append((R, -T / 2 + E)); prof.append((R, T / 2 - E))
for k in range(1, 8):
    a = (math.pi / 2) * k / 8; prof.append((R - E * (1 - math.cos(a)), T / 2 - E + E * math.sin(a)))
prof += [(R - E, T / 2), (0.055, T / 2 + BULGE * 0.5), (0.03, T / 2 + BULGE * 0.86), (0, T / 2 + BULGE)]
pot = kit.lathe(prof, steps=96, name='teapot')
xform(pot, rot=(90, 0, 0))
pot.data.materials.append(GLAZE); pot.data.materials.append(HOLE); pot.data.materials.append(BISQUE)
# flat base
c = kit.box((0.4, 0.4, 0.1), at=(0, 0, -CUT - 0.05), name='basecut'); c.data.materials.clear(); c.data.materials.append(BISQUE)
cut(pot, c)
# lid seam groove (the dark slot on the drawing) and the steam hole
PHI1, PHI2 = math.radians(6), math.radians(40)
LW = T - 0.016
for phi in (PHI1,):
    g = kit.box((0.003, LW + 0.004, 0.012), at=rim_point(phi, R), rot=(0, math.degrees(phi), 0), name='seamcut')
    g.data.materials.clear(); g.data.materials.append(HOLE); cut(pot, g)
VPHI = math.radians(53)
vh = kit.cyl(0.0027, 0.016, at=rim_point(VPHI, R), rot=(0, math.degrees(VPHI), 0), verts=16, name='vent')
vh.data.materials.clear(); vh.data.materials.append(HOLE); cut(pot, vh)
kit.finish(pot, None, smooth=40)

# ---- curved flap lid on the rim with a walnut knob
def bent_plate(phi0, phi1, width, t0, t1, r_corner=0.005, name='lid'):
    s0, s1 = phi0 * R, phi1 * R
    o = extrude(rrect(s1 - s0, width, r_corner, seg=5, cx=(s0 + s1) / 2), t1 - t0, name=name)
    for v in o.data.vertices:
        s, y, t = v.co.x, v.co.y, v.co.z + t0
        p = rim_point(s / R, R + t, y); v.co = p
    return o
lid = bent_plate(PHI1 + 0.035, PHI2, LW, -0.001, 0.0022, name='lid')
kit.finish(lid, GLAZE, bevel=0.0012, segments=2, smooth=40)
KPHI = (PHI1 + 0.035 + PHI2) / 2
kd = rim_point(KPHI, 1.0)
knob = kit.lathe([(0, 0), (0.0068, 0), (0.0072, 0.0015), (0.0068, 0.0055), (0.0058, 0.0075), (0.003, 0.0088), (0, 0.009)],
                 material=WALNUT, steps=28, name='knob')
knob.rotation_mode = 'QUATERNION'; knob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(kd)
knob.location = rim_point(KPHI, R + 0.0015)

# ---- squared loop handle on the -x side
HX = -R - 0.04
path = fillet([rim_point(math.radians(-14), R - 0.006), (-0.03, 0, R + 0.009), (HX, 0, R + 0.009), (HX, 0, -0.022),
               (-R + 0.007, 0, -0.022)], 0.016, seg=8)
handle = sweep(path, rrect(0.0125, 0.012, 0.0035, seg=3), name='handle', up=(0, 1, 0), material=GLAZE, smooth=40)

# ---- straight spout angled up on the +x side, hollow at the tip
SPHI = math.radians(98); SD = Vector((math.cos(math.radians(36)), 0, math.sin(math.radians(36))))
root = rim_point(SPHI, R - 0.01)
SL = 0.066
spout = kit.lathe([(0, 0), (0.0145, 0), (0.0115, 0.012), (0.0099, 0.02), (0.0097, SL - 0.002), (0.0104, SL),
                   (0.0068, SL), (0.0066, SL - 0.014), (0, SL - 0.016)], steps=32, material=GLAZE, name='spout')
spout.rotation_mode = 'QUATERNION'; spout.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(SD)
spout.location = root

# ---- square tea cup with flared sides, cream inside, full of tea
CH = 0.064; CT = 0.0042
def wsz(z):  # outer half-width along the height (narrow foot, flaring to the rim)
    t = z / CH
    return 0.0285 + 0.0075 * t ** 0.9
def csec(z, inset=0.0, rr=None):
    w = 2 * (wsz(z) - inset)
    r = rr if rr is not None else 0.0075 + 0.003 * z / CH
    return rrect(w, w, max(0.002, r - inset), seg=5)
rings = []
foot = [(x, y, 0.0) for x, y in csec(0.0, inset=0.0035)]
rings.append(foot)
rings.append([(x, y, 0.0035) for x, y in csec(0.0, inset=0.0005)])
for z in (0.006, 0.02, 0.035, 0.05, CH - 0.0025):
    rings.append([(x, y, z) for x, y in csec(z)])
rings.append([(x, y, CH) for x, y in csec(CH, inset=CT * 0.25)])
rings.append([(x, y, CH) for x, y in csec(CH, inset=CT * 0.85)])
for z in (CH - 0.003, 0.045, 0.025, 0.012):
    rings.append([(x, y, z) for x, y in csec(z, inset=CT)])
rings.append([(x, y, 0.0085) for x, y in csec(0.0085, inset=CT + 0.004)])
cup = loft(rings, name='cup', smooth=40)
cup.data.materials.append(GLAZE); cup.data.materials.append(CREAM); cup.data.materials.append(BISQUE)
n = len(foot); inner_from = 7
for p in cup.data.polygons:
    ring_i = p.index // n if p.index < n * (len(rings) - 1) else None
    if ring_i is None:
        p.material_index = 2 if p.index == n * (len(rings) - 1) else 1
    elif ring_i >= inner_from: p.material_index = 1
kit.finish(cup, None, bevel=0.0, smooth=40)
TZ = CH - 0.011
tea = extrude(csec(TZ, inset=CT + 0.0002), 0.002, at=(0, 0, TZ - 0.002), material=TEA, name='tea')
# place the cup in front of the spout, turned a touch
CX, CY = 0.125, -0.085
for o in (cup, tea):
    xform(o, rot=(0, 0, 12))
    xform(o, loc=(CX, CY, -CUT + o.location.z))

ground(0.0)

kit.export('tea-set')
