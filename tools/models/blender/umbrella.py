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
# Umbrella, after Bua's drawing: an open eight-rib umbrella with a scalloped hem, straight shaft and a straight
# grip with a wrist strap, resting on the ground the way it is drawn (canopy rim and grip touching the floor,
# underside open to the front so the ribs and stretchers show).
FABRIC = kit.mat('#8f1d18', rough=0.6, name='canopy')
RIB = kit.mat('gunmetal', rough=0.35, metal=0.85, name='rib')
STEEL = kit.mat('#9aa0a8', rough=0.3, metal=0.85, name='shaft')
WOOD = kit.mat('#8a5a2e', rough=0.5, name='grip')
STRAP = kit.mat('#1e1d1c', rough=0.75, name='strap')
CAP = kit.mat('black', rough=0.4, name='cap')

NR = 8                        # ribs
R = 0.50                      # plan radius at the rib tips
ALPHA = math.radians(56)      # canopy arc
RC = R / math.sin(ALPHA)
DEPTH = RC * (1 - math.cos(ALPHA))
S0 = 0.035                    # crown hole under the top cap
SCALLOP = 0.055

def rib_pt(k, s, inset=0.0):
    """Point on rib k at arc fraction s (0 crown, 1 tip); inset moves it under the fabric."""
    a = math.tau * k / NR + math.pi / NR
    t = ALPHA * s; rr = (RC - inset) * math.sin(t); z = (RC - inset) * math.cos(t) - RC * math.cos(ALPHA)
    return Vector((rr * math.cos(a), rr * math.sin(a), z))

# canopy: eight taut panels, straight between the ribs with a slight sag, hem scalloped between the tips
bm = bmesh.new(); NW, NS = 14, 22; grid = {}
for k in range(NR):
    for i in range(NW + 1):
        w = i / NW; se = 1 - SCALLOP * math.sin(math.pi * w)
        for j in range(NS + 1):
            s = S0 + (se - S0) * (j / NS)
            p = rib_pt(k, s).lerp(rib_pt(k + 1, s), w)
            sag = 0.010 * math.sin(math.pi * w) * math.sin(math.pi * min(1, s) * 0.9)
            p.z -= sag; p.xy *= 1 - sag * 0.4
            p.z -= 0.012 * math.sin(math.pi * w) * (j / NS) ** 3   # hem curls down a touch between tips
            grid[k, i, j] = bm.verts.new(p)
for k in range(NR):
    for i in range(NW):
        for j in range(NS):
            bm.faces.new((grid[k, i, j], grid[k, i + 1, j], grid[k, i + 1, j + 1], grid[k, i, j + 1]))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:  # make sure normals face up/out
    if f.normal.z < 0 and f.calc_center_median().z > 0.05: pass
canopy = _mesh_obj('canopy', bm)
if sum(p.normal.z for p in canopy.data.polygons) < 0:
    canopy.data.flip_normals()
solidify(canopy, 0.0016, offset=-1)
kit.finish(canopy, FABRIC, smooth=28)

parts = [canopy]
# ribs under the fabric, tips poking out past the hem
for k in range(NR):
    pts = [rib_pt(k, S0 + (1.0 - S0) * j / 24, inset=0.0035) for j in range(25)]
    parts.append(sweep(pts, circle2(0.0024, 6), name='rib', material=RIB, smooth=60))
    tip_dir = (rib_pt(k, 1.0) - rib_pt(k, 0.97)).normalized()
    t0 = rib_pt(k, 0.985, inset=0.002)
    parts.append(rod(t0, t0 + tip_dir * 0.022, 0.0042, material=CAP, verts=12, name='tip', bevel=0.0015))
# shaft, top notch, runner and stretchers
TOP = Vector((0, 0, DEPTH)); SHAFT_LEN = 0.66
bottom = Vector((0, 0, DEPTH - SHAFT_LEN))
parts.append(rod(bottom, TOP + Vector((0, 0, 0.02)), 0.0055, material=STEEL, verts=16, name='shaft'))
parts.append(kit.lathe([(0, 0), (0.016, 0), (0.017, 0.006), (0.012, 0.011), (0.006, 0.05), (0.002, 0.075), (0, 0.078)],
                       at=(0, 0, DEPTH - 0.004), material=CAP, steps=24, name='ferrule'))
parts.append(kit.cyl(0.013, 0.03, at=(0, 0, DEPTH - 0.03), material=CAP, verts=24, bevel=0.003, name='notch'))
RUN_Z = DEPTH - 0.24
parts.append(kit.cyl(0.0125, 0.065, at=(0, 0, RUN_Z - 0.02), material=CAP, verts=24, bevel=0.003, name='runner'))
parts.append(kit.cyl(0.017, 0.012, at=(0, 0, RUN_Z + 0.012), material=CAP, verts=24, bevel=0.003, name='runner_hub'))
for k in range(NR):
    a = math.tau * k / NR + math.pi / NR
    p0 = Vector((0.016 * math.cos(a), 0.016 * math.sin(a), RUN_Z + 0.012))
    p1 = rib_pt(k, 0.43, inset=0.007)
    parts.append(rod(p0, p1, 0.0019, material=RIB, verts=6, name='stretcher'))
    parts.append(kit.sphere(0.0038, at=p1, material=RIB, segs=10, rings=6, name='joint'))
# straight grip with a metal end cap
gz = bottom.z
# the drawn grip is a squared block: rounded-square section, swelling slightly toward the end
rings = []
for j in range(13):
    t = j / 12; z = gz - 0.142 + 0.15 * t
    wdt = 0.033 + 0.006 * math.sin(math.pi * (1 - t) * 0.8) - 0.012 * max(0, t - 0.88) / 0.12
    rings.append([(x, y, z) for x, y in rrect(wdt, wdt * 0.92, wdt * 0.3, seg=4)])
grip = loft(rings, name='grip', material=WOOD, bevel=0.002)
parts.append(grip)
parts.append(kit.lathe([(0, 0), (0.0135, 0), (0.0165, 0.003), (0.0172, 0.009), (0, 0.009)], at=(0, 0, gz - 0.148),
                       material=STEEL, steps=32, name='endcap'))
parts.append(kit.torus(0.0052, 0.0014, at=(0, 0, gz - 0.150), rot=(90, 0, 0), material=STEEL, major=20, minor=6, name='eyelet'))

# lay it down like the drawing: tilt back until the hem and the grip end both touch the floor
END = Vector((0, 0, gz - 0.146))
def low_points(theta):
    m = Matrix.Rotation(-theta, 4, 'X')
    rim = min((m @ (rib_pt(k, 1.0) + (rib_pt(k, 1.0) - rib_pt(k, 0.97)).normalized() * 0.02)).z for k in range(NR))
    hand = (m @ END).z - 0.019 * math.sin(theta)
    return rim, hand
lo, hi = math.radians(20), math.radians(89)
for _ in range(50):
    mid = (lo + hi) / 2; rim, hand = low_points(mid)
    if hand < rim: lo = mid
    else: hi = mid
theta = (lo + hi) / 2
SPIN = math.radians(-22)   # turned a little so the front view looks into the canopy at an angle, as drawn
M = Matrix.Rotation(SPIN, 4, 'Z') @ Matrix.Rotation(-theta, 4, 'X')
for o in list(bpy.context.scene.objects):
    o.matrix_world = M @ o.matrix_world
bpy.context.view_layer.update()
dz = -lowest_z()
for o in list(bpy.context.scene.objects):
    o.location.z += dz
print('UMBRELLA tilt from vertical', round(math.degrees(theta), 1))

# wrist strap: a flat loop from the eyelet lying out on the floor
eye = M @ Vector((0, 0, gz - 0.150)); eye.z += dz
d = (M @ Vector((0, 0, -1, 0))).to_3d(); d.z = 0; d.normalize(); side = Vector((-d.y, d.x, 0))
h = 0.0016
loop = [eye + d * 0.004, eye + d * 0.03 + side * 0.009 + Vector((0, 0, h - eye.z)) * 0.6,
        Vector((0, 0, 0)) + (eye + d * 0.085 + side * 0.013).to_2d().to_3d() + Vector((0, 0, h)),
        (eye + d * 0.105).to_2d().to_3d() + Vector((0, 0, h)),
        (eye + d * 0.085 - side * 0.013).to_2d().to_3d() + Vector((0, 0, h)),
        eye + d * 0.03 - side * 0.009 + Vector((0, 0, h - eye.z)) * 0.6]
sweep(catmull(loop, 8, closed=True), [(-0.0045, -0.0009), (0.0045, -0.0009), (0.0045, 0.0009), (-0.0045, 0.0009)],
      name='strap', loop=True, up=(0, 0, 1), material=STRAP)

kit.export('umbrella')
