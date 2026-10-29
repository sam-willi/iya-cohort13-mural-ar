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
# Basketball + baseball (no student drawing in the folder: a regulation basketball with recessed black channels,
# and a baseball with its figure-eight seam and red double stitching, resting against it).
LEATHER_O = kit.mat('#a3441a', rough=0.62, name='ball_leather')


def pebble_normal_map(path, size=256, cells=18, seed=7):
    """Tileable normal map of round leather pebbles, written to a temp PNG."""
    import numpy as np, random
    rnd = random.Random(seed); cs = size / cells
    cx = np.array([[(i + 0.5 + rnd.uniform(-0.18, 0.18)) * cs for i in range(cells)] for j in range(cells)])
    cy = np.array([[(j + 0.5 + rnd.uniform(-0.18, 0.18)) * cs for i in range(cells)] for j in range(cells)])
    rr = np.array([[cs * rnd.uniform(0.40, 0.5) for i in range(cells)] for j in range(cells)])
    yy, xx = np.mgrid[0:size, 0:size].astype(float) + 0.5
    h = np.zeros((size, size))
    ci, cj = (xx // cs).astype(int), (yy // cs).astype(int)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            i2, j2 = (ci + di) % cells, (cj + dj) % cells
            px = cx[j2, i2] + (ci + di - i2) * cs; py = cy[j2, i2] + (cj + dj - j2) * cs
            d = np.hypot(xx - px, yy - py) / rr[j2, i2]
            h = np.maximum(h, np.sqrt(np.clip(1 - d * d, 0, 1)))
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 1.2; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 1.2
    n = np.dstack([-gx, -gy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    rgba = np.dstack([(n + 1) / 2, np.ones_like(h)])
    img = bpy.data.images.new('pebble', size, size); img.pixels = rgba.astype(np.float32).ravel()
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    return path


import tempfile
_nm = pebble_normal_map(os.path.join(tempfile.gettempdir(), 'basketball_pebble_normal.png'))
_t = LEATHER_O.node_tree; _tex = _t.nodes.new('ShaderNodeTexImage'); _tex.image = bpy.data.images.load(_nm)
_tex.image.colorspace_settings.name = 'Non-Color'
_nmn = _t.nodes.new('ShaderNodeNormalMap'); _nmn.inputs['Strength'].default_value = 0.8
_t.links.new(_tex.outputs['Color'], _nmn.inputs['Color']); _t.links.new(_nmn.outputs['Normal'], _t.nodes['Principled BSDF'].inputs['Normal'])


def cube_sphere(radius, n=30, rep=9, name='cubesphere'):
    """Sphere from a subdivided cube (even quads, per-face UVs repeated `rep` times for the pebble map)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    axes = [((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((-1, 0, 0), (0, 1, 0), (0, 0, -1)), ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
            ((0, -1, 0), (0, 0, 1), (-1, 0, 0)), ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (1, 0, 0), (0, -1, 0))]
    for nrm, ua, va in axes:
        nrm, ua, va = Vector(nrm), Vector(ua), Vector(va)
        g = [[None] * (n + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            for j in range(n + 1):
                u = math.tan((i / n * 2 - 1) * math.pi / 4); v = math.tan((j / n * 2 - 1) * math.pi / 4)
                g[i][j] = bm.verts.new((nrm + ua * u + va * v).normalized() * radius)
        for i in range(n):
            for j in range(n):
                f = bm.faces.new((g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1]))
                for lp, (a_, b_) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    lp[uvl].uv = (a_ / n * rep, b_ / n * rep)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=radius * 1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mesh_obj(name, bm)
CHANNEL = kit.mat('#1c1a19', rough=0.8, name='channel')
HIDE = kit.mat('#ece5d3', rough=0.55, name='hide')
SEAM = kit.mat('#d9d0bb', rough=0.6, name='seam')
THREAD = kit.mat('#a5221b', rough=0.7, name='thread')


def cut(target, cutter):
    """Boolean difference that hands the cutter's material to the new faces (kit.boolean keeps slot indices)."""
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter
    md.solver = 'EXACT'; md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)


def rods_mesh(segs, r, sides=6, name='rods', material=None):
    """Many thin rods [(p0, p1), ...] in one mesh."""
    bm = bmesh.new()
    for p0, p1 in segs:
        p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
        m = Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r, radius2=r, depth=d.length, matrix=m)
    o = _mesh_obj(name, bm)
    return kit.finish(o, material, smooth=60)

# ---- basketball
R = 0.1195
ball = kit.finish(cube_sphere(R, n=34, rep=9, name='basketball'), LEATHER_O)
ball.data.materials.append(CHANNEL)
def great(axis_fn, n=224):
    return [Vector(axis_fn(math.tau * i / n)) for i in range(n)]
paths = [great(lambda t: (math.cos(t), math.sin(t), 0)),          # equator
         great(lambda t: (0, math.cos(t), math.sin(t)))]          # meridian
for sgn in (1, -1):                                                # the two curved channels
    paths.append([Vector((sgn * (0.55 + 0.33 * math.cos(2 * t)), math.cos(t), math.sin(t))).normalized()
                  for t in [math.tau * i / 224 for i in range(224)]])
for p in paths:
    ring = [v.normalized() * (R + 0.0016) for v in p]
    c = sweep(ring, circle2(0.0036, 10), loop=True, name='cutter', smooth=0)
    c.data.materials.append(CHANNEL)
    cut(ball, c)
kit.finish(ball, None, smooth=40)
xform(ball, rot=(18, -12, 32), loc=(0, 0, R))

# ---- baseball
r = 0.0366; b = 0.27; a = 1 - b
def seam_pt(t):
    return Vector((a * math.cos(t) + b * math.cos(3 * t), a * math.sin(t) - b * math.sin(3 * t), 2 * math.sqrt(a * b) * math.sin(2 * t)))
bb = kit.sphere(r, segs=72, rings=36, material=HIDE, name='baseball')
bb.data.materials.append(SEAM)
NS = 216
groove = [seam_pt(math.tau * i / NS).normalized() * (r + 0.0003) for i in range(NS)]
c = sweep(groove, circle2(0.0011, 8), loop=True, name='cutter', smooth=0); c.data.materials.append(SEAM)
cut(bb, c)
kit.finish(bb, None, smooth=40)
# double stitching: 108 V-stitches across the seam
segs = []; NST = 108; w = 0.0034
for i in range(NST):
    t0 = math.tau * i / NST; t1 = t0 + math.tau / NST * 0.55
    p = seam_pt(t0).normalized(); q = seam_pt(t1).normalized()
    tan = (seam_pt(t0 + 1e-3) - seam_pt(t0 - 1e-3)).normalized()
    side = p.cross(tan).normalized()
    L = (p + side * (w / r)).normalized() * (r + 0.0004); Rr = (p - side * (w / r)).normalized() * (r + 0.0004)
    M = q.normalized() * (r + 0.0006)
    segs += [(L, M), (Rr, M)]
st = rods_mesh(segs, 0.00062, sides=5, name='stitches', material=THREAD)
d = 2 * math.sqrt(R * r) + 0.0006; ang = math.radians(-38)
for o in (bb, st):
    xform(o, rot=(25, 10, 60))
    xform(o, loc=(d * math.cos(ang), d * math.sin(ang), r))

kit.export('basketball-baseball')
