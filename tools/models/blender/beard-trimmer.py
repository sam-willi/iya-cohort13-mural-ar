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
# Beard trimmer, after Sam Williamson's drawing: a long faceted body (flat front with chamfered long edges) that
# widens toward the head, a collar band where the head meets the body, a guard comb with a row of pointed teeth over
# the steel blade, a rounded-rectangle power button in a recess, and a charging port in the base. It stands upright on
# its base so the button faces the viewer (the drawing shows it lying down); the back and side grips are invented.
BODY = kit.mat('#4b5059', rough=0.38, name='body')
GRIP = kit.mat('rubber', rough=0.85, name='grip')
HEAD = kit.mat('#1f1e1d', rough=0.42, name='head')
COPPER = kit.mat('copper', rough=0.3, metal=0.85, name='copper')
STEEL = kit.mat('chrome', rough=0.22, metal=0.9, name='blade')
COMB = kit.mat('#252423', rough=0.4, name='comb')
LED = kit.mat('amber', rough=0.4, emit=2.5, name='led')
PORT = kit.mat('#101010', rough=0.6, name='port')

C = 0.0058  # chamfer on the long edges


def section(w, d, c=C):
    return [(-w / 2 + c, -d / 2), (w / 2 - c, -d / 2), (w / 2, -d / 2 + c), (w / 2, d / 2 - c),
            (w / 2 - c, d / 2), (-w / 2 + c, d / 2), (-w / 2, d / 2 - c), (-w / 2, -d / 2 + c)]


def dims(z):
    """Body width / depth along its length (narrow at the base, widest under the head)."""
    keys = [(0.0, 0.0335, 0.0265), (0.055, 0.0372, 0.0296), (0.095, 0.0418, 0.0328), (0.118, 0.0430, 0.0335)]
    for (z0, w0, d0), (z1, w1, d1) in zip(keys, keys[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0); t = t * t * (3 - 2 * t)
            return w0 + (w1 - w0) * t, d0 + (d1 - d0) * t
    return keys[-1][1], keys[-1][2]


def ring(z, inset=0.0, c=C):
    w, d = dims(min(z, 0.118))
    return [(x, y, z) for x, y in section(w - 2 * inset, d - 2 * inset, c)]


def cut(target, cutter):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)


# main body: bottom chamfer, then sections up to the collar
rings = [ring(0.0, inset=0.0022), ring(0.0022)] + [ring(z) for z in (0.01, 0.025, 0.04, 0.055, 0.07, 0.085, 0.1, 0.11, 0.1175)]
body = loft(rings, name='body', material=BODY, smooth=25)
body.data.materials.append(PORT)
# power button recess on the front face
BZ = 0.086
w_b, d_b = dims(BZ)
tilt = math.degrees(math.atan2((dims(0.1)[1] - dims(0.07)[1]) / 2, 0.03))
rc = extrude(rrect(0.0172, 0.0265, 0.0052, seg=6), 0.01, at=(0, -d_b / 2 + 0.0013, BZ), rot=(90 + tilt, 0, 0), name='recess')
rc.data.materials.append(PORT)
cut(body, rc)
# charging port in the base
pc = extrude(rrect(0.012, 0.0042, 0.0021, seg=6), 0.006, at=(0, 0, -0.001), name='portcut'); pc.data.materials.append(PORT)
cut(body, pc)
kit.finish(body, None, bevel=0.0011, segments=2, smooth=25)
kit.box((0.0105, 0.0016, 0.0006), at=(0, 0, 0.0035), material=STEEL, name='port_pins')

# button: soft rounded slab with a power symbol and an amber status ring
btn = extrude(rrect(0.0136, 0.0228, 0.0042, seg=6), 0.0021, at=(0, -d_b / 2 + 0.0012, BZ), rot=(90 + tilt, 0, 0),
              material=GRIP, bevel=0.0008, segments=2, name='button')
fy = -d_b / 2 - 0.0009 - 0.0002
arc = [Vector((0.0034 * math.sin(a), fy, BZ - 0.0018 + 0.0034 * math.cos(a))) for a in
       [math.radians(35 + (360 - 70) * k / 24) for k in range(25)]]
sweep(arc, circle2(0.00045, 6), name='power_arc', up=(0, -1, 0), material=LED, smooth=60)
rod((0, fy, BZ - 0.0012), (0, fy, BZ + 0.0026), 0.00045, material=LED, verts=6, name='power_bar')

# collar band and the head housing
collar = loft([ring(z, inset=0.0007) for z in (0.1178, 0.1215, 0.1262)], name='collar', material=COPPER, smooth=25)
kit.finish(collar, None, bevel=0.0004)
def head_ring(z, grow):
    w, d = dims(0.118)
    return [(x, y, z) for x, y in section(w + grow, d + grow * 0.3, C * 0.8)]
head = loft([head_ring(0.1265, 0.0), head_ring(0.134, 0.0012), head_ring(0.146, 0.0024), head_ring(0.1515, 0.0026),
             head_ring(0.1525, 0.0004)], name='head', material=BODY, smooth=25)
kit.finish(head, None, bevel=0.0009)
HW, HD = dims(0.118)[0] + 0.0026, dims(0.118)[1] + 0.0008
HTOP = 0.1525

# steel blade with fine teeth peeking out at the front, under the comb
kit.box((HW - 0.006, 0.0075, 0.0032), at=(0, -HD / 2 + 0.0058, HTOP + 0.0014), material=STEEL, bevel=0.0006, name='blade')
for k in range(31):
    x = -(HW - 0.008) / 2 + k * (HW - 0.008) / 30
    kit.box((0.0007, 0.0026, 0.0024), at=(x, -HD / 2 + 0.0022, HTOP + 0.0028), material=STEEL, name='blade_tooth')

# guard comb: two side arms clipped over the head, a front bar, a back spine and eleven pointed teeth
CW = HW + 0.0052
for sx in (-1, 1):
    arm = rrect(HD + 0.002, 0.034, 0.004, seg=4, cy=HTOP + 0.003)
    extrude(arm, 0.0024, at=(sx * (CW / 2) - 0.0012, 0, 0), rot=(90, 0, 90), material=COMB, bevel=0.0007, name='comb_arm')
kit.box((CW, 0.0026, 0.0036), at=(0, -HD / 2 - 0.0002, HTOP + 0.0055), material=COMB, bevel=0.0008, name='comb_front')
kit.box((CW, 0.004, 0.0165), at=(0, HD / 2 - 0.0012, HTOP + 0.0106), material=COMB, bevel=0.0012, name='comb_spine')
NT = 11
for k in range(NT):
    x = -CW / 2 + 0.0035 + k * (CW - 0.007) / (NT - 1)
    tooth = [(-HD / 2 + 0.0005, HTOP + 0.003), (HD / 2 - 0.002, HTOP + 0.003), (HD / 2 - 0.002, HTOP + 0.0185),
             (-HD / 2 + 0.0065, HTOP + 0.0185), (-HD / 2 + 0.0005, HTOP + 0.0115)]
    extrude(tooth, 0.0013, at=(x - 0.00065, 0, 0), rot=(90, 0, 90), material=COMB, bevel=0.0003, segments=1, name='comb_tooth')

# side grips: rubber inserts with fine ribs, following the taper of the sides
for sx in (-1, 1):
    pts = []
    for z in (0.024, 0.04, 0.056, 0.072, 0.088):
        w, d = dims(z); pts.append((sx * (w / 2 + 0.0004), z))
    z0, z1 = 0.022, 0.09
    for k in range(13):
        z = z0 + (z1 - z0) * k / 12; w, d = dims(z)
        x = sx * (w / 2 + 0.00025)
        rod((x, -d / 2 + C + 0.0018, z), (x, d / 2 - C - 0.0018, z), 0.00085, material=GRIP, verts=8, name='grip_rib')
# back: a long rubber pad with ribs
for k in range(14):
    z = 0.022 + 0.07 * k / 13; w, d = dims(z)
    rod((-w / 2 + C + 0.0016, d / 2 + 0.0001, z), (w / 2 - C - 0.0016, d / 2 + 0.0001, z), 0.00085, material=GRIP, verts=8,
        name='back_rib')


kit.export('beard-trimmer')
