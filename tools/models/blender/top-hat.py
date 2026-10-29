"""Top hat (April Ortiz). A magician's hat set upside down with a plush pony climbing out of it, as drawn: soft
caramel head turned a little to the left, a fuzzy forelock between tall rounded ears, a halter (noseband + cheek and
crown strap), a cream muzzle, and both front hooves hooked over the brim. Hat: black felt, a band just under the
brim, red satin lining inside. The drawing is line-only, so the colours are ours (plush caramel, teal halter)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

random.seed(7)


def xform(objs, M):
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    return objs


def metaball(name, elems, material, res=0.0035, fuzz=0.0):
    """elems: [(centre, (semi_x, semi_y, semi_z), quaternion or None)]. Returns a mesh object."""
    mb = bpy.data.metaballs.new(name); mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    o = bpy.data.objects.new(name, mb); bpy.context.collection.objects.link(o)
    for co, semi, q in elems:
        e = mb.elements.new(); e.type = 'ELLIPSOID'; e.co = co
        R = max(semi) / 0.574; e.radius = R
        e.size_x, e.size_y, e.size_z = (s / (0.574 * R) for s in semi)
        if q is not None:
            e.rotation = q
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.name = name
    kit.finish(o, material, smooth=180)
    if fuzz:
        tex = bpy.data.textures.new(name + '_fuzz', 'CLOUDS'); tex.noise_scale = 0.0028; tex.noise_depth = 1
        d = o.modifiers.new('fuzz', 'DISPLACE'); d.texture = tex; d.strength = fuzz; d.mid_level = 0.5
        d.texture_coords = 'LOCAL'
    return o


def q_from_to(a, b):
    return Vector(a).normalized().rotation_difference(Vector(b).normalized())


def strap(points, normals, w, t, material, closed=False, name='strap'):
    """Flat strap swept along points, lying on the surface with the given outward normals."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    n = len(points); rings = []
    for i in range(n):
        p = points[i]; nn = normals[i]
        a = points[(i - 1) % n] if (closed or i > 0) else points[i]
        b = points[(i + 1) % n] if (closed or i < n - 1) else points[i]
        tg = (b - a).normalized()
        bn = tg.cross(nn).normalized()
        nn = bn.cross(tg).normalized()
        c = p + nn * (t / 2)
        rings.append([bm.verts.new(c + bn * sx * w / 2 + nn * sy * t / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(4):
            bm.faces.new((r0[j], r0[(j + 1) % 4], r1[(j + 1) % 4], r1[j]))
    if not closed:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, bevel=min(w, t) * 0.3, segments=1, smooth=50)


def catmull(pts, k=6, closed=False):
    P = [Vector(p) for p in pts]; out = []
    n = len(P); rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1 = P[i]; p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[(i + 1) % n]
        for s in range(k):
            t = s / k
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(P[-1])
    return out


def snap(points, centre, trees):
    """Project points onto the outermost surface along rays from centre. Returns (points, normals)."""
    C = Vector(centre); ps, ns = [], []
    for p in points:
        d = (Vector(p) - C).normalized(); best = None
        for t in trees:
            hit = t.ray_cast(C, d)
            if hit[0] is not None and (best is None or hit[3] > best[3]):
                best = hit
        if best is None:
            ps.append(Vector(p)); ns.append(d)
        else:
            nn = best[1] if best[1].dot(d) > 0 else -best[1]
            ps.append(best[0]); ns.append(nn.normalized())
    return ps, ns


def tuft(base, direction, material, n=7, length=0.016, r=0.0045, spread=35, name='tuft'):
    """A little clump of plush fibres: tapered cones fanned around a direction."""
    D = Vector(direction).normalized(); objs = []
    for i in range(n):
        a = math.radians(random.uniform(-spread, spread)); b = math.radians(random.uniform(0, 360))
        perp = D.orthogonal().normalized()
        axis = (D * math.cos(a) + (Quaternion(D, b) @ perp) * math.sin(a)).normalized()
        L = length * random.uniform(0.7, 1.15)
        c = Vector(base) + axis * (L / 2 - 0.002)
        o = kit.cyl(r * random.uniform(0.8, 1.1), L, at=tuple(c), r2=0.0006, verts=8, material=material, name=name)
        o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q_from_to((0, 0, 1), axis)
        objs.append(o)
    return objs


# ---------- materials ----------
felt = kit.mat('#232120', rough=0.5, name='felt')
satin_black = kit.mat('#121110', rough=0.3, name='binding')
band_m = kit.mat('cardinal', rough=0.55, name='band')
lining = kit.mat('#7d1a17', rough=0.35, name='lining')
plush = kit.mat('#c98f4e', rough=0.85, name='plush')          # caramel, pulled toward honey
muzzle_m = kit.mat('#efe0c4', rough=0.85, name='muzzle')       # cream
mane_m = kit.mat('#6b4428', rough=0.85, name='mane')           # walnut-brown fluff
hoof_m = kit.mat('walnut', rough=0.6, name='hoof')
sole_m = kit.mat('#3a2617', rough=0.7, name='sole')
eye_m = kit.mat('#0d0c0c', rough=0.08, name='eye')
halter_m = kit.mat('teal', rough=0.5, name='halter')
brass = kit.mat('brass', rough=0.28, metal=0.9, name='brass')

# ---------- the hat, upside down ----------
CRo, CH = 0.1, 0.15            # crown radius, crown height (now pointing down)
ZB = 0.164                     # brim top
crown = kit.lathe([(0, 0), (0.086, 0), (0.095, 0.003), (0.0995, 0.01), (CRo, 0.03), (CRo, 0.152), (0.094, 0.152),
                   (0.094, 0.016), (0, 0.016)], material=felt, steps=72, name='crown')
crown.data.materials.append(lining)
for f in crown.data.polygons:
    c = f.center
    if math.hypot(c.x, c.y) < 0.0965 and c.z > 0.012:
        f.material_index = 1
brim = kit.lathe([(0.094, 0.148), (0.128, 0.1495), (0.137, 0.151), (0.1415, 0.1545), (0.143, 0.1585), (0.1415, 0.1625),
                  (0.137, 0.1652), (0.128, 0.1655), (0.11, ZB), (0.094, ZB - 0.0005), (0.094, 0.148)],
                 material=felt, steps=72, name='brim')
brim.data.materials.append(satin_black)
for f in brim.data.polygons:
    if math.hypot(f.center.x, f.center.y) > 0.1335:
        f.material_index = 1
kit.lathe([(0.0985, 0.118), (0.1022, 0.1185), (0.1025, 0.1465), (0.0985, 0.147), (0.0985, 0.118)], material=band_m,
          steps=72, name='band')

# ---------- pony head, built facing -Y around the hat axis, then turned a little to the left ----------
head = metaball('ponyhead', [
    ((0, 0.022, -0.03), (0.044, 0.042, 0.075), None),           # neck rising out of the hat
    ((0, 0.014, 0.098), (0.05, 0.052, 0.054), None),            # cranium
    ((0, -0.016, 0.07), (0.047, 0.046, 0.046), None),           # cheeks / face
], plush, fuzz=0.0015)
muzzle = metaball('ponymuzzle', [
    ((0, -0.05, 0.048), (0.042, 0.038, 0.034), None),
    ((0, -0.034, 0.05), (0.04, 0.03, 0.036), None),
], muzzle_m, fuzz=0.0009)
dg = bpy.context.evaluated_depsgraph_get()
trees = [BVHTree.FromObject(head, dg), BVHTree.FromObject(muzzle, dg)]
head_parts = [head, muzzle]

# ears: tall teardrops with rounded tips, cupped with a cream inside
for sx in (-1, 1):
    ear = kit.lathe([(0, -0.006), (0.0125, -0.002), (0.0165, 0.012), (0.0158, 0.028), (0.011, 0.042), (0.0045, 0.05),
                     (0, 0.052)], material=plush, steps=24, name='ear')
    ear.scale = (1, 0.42, 1)
    inner = kit.lathe([(0, 0.0), (0.0095, 0.003), (0.0118, 0.014), (0.011, 0.028), (0.0075, 0.04), (0, 0.046)],
                      material=muzzle_m, steps=20, name='ear_inner')
    inner.scale = (1, 0.16, 1); inner.location = (0, -0.0052, 0.0)
    for o in (ear, inner):
        bpy.context.view_layer.update()
        o.matrix_world = (Matrix.Translation((sx * 0.03, 0.024, 0.128)) @ Matrix.Rotation(math.radians(-sx * 14), 4, 'Y')
                          @ Matrix.Rotation(math.radians(sx * 12), 4, 'Z') @ Matrix.Rotation(math.radians(-6), 4, 'X')
                          @ o.matrix_world)
    head_parts += [ear, inner]

# forelock puff between the ears and a mane down the back of the neck
fl = metaball('ponyforelock', [((0.0, 0.006, 0.156), (0.019, 0.017, 0.016), None),
                               ((-0.011, -0.006, 0.152), (0.013, 0.013, 0.012), None),
                               ((0.011, -0.005, 0.153), (0.013, 0.012, 0.012), None),
                               ((0.0, -0.017, 0.146), (0.012, 0.011, 0.011), None),
                               ((-0.003, -0.027, 0.136), (0.008, 0.008, 0.009), None)], mane_m, fuzz=0.0024)
head_parts.append(fl)
mane_pts = [Vector(p) for p in catmull([(0, 0.036, 0.142), (0, 0.054, 0.118), (0, 0.063, 0.085), (0, 0.067, 0.05),
                                         (0, 0.067, 0.015), (0, 0.065, -0.025)], k=3)]
mane = metaball('ponymane', [(tuple(p), (0.0105, 0.012, 0.012), None) for p in mane_pts], mane_m, fuzz=0.0022)
head_parts.append(mane)
for i, p in enumerate(mane_pts[:-2]):
    if i % 2 == 0:
        d = (Vector(p) - Vector((0, 0.0, 0.06))).normalized()
        head_parts += tuft(Vector(p) + d * 0.007, d, mane_m, n=4, length=0.013, r=0.0045, spread=40)
for d in ((0, -0.3, 1), (-0.6, -0.2, 1), (0.6, -0.2, 1), (0, -1, 0.4)):
    D = Vector(d).normalized()
    head_parts += tuft(Vector((0, -0.006, 0.152)) + D * 0.012, D, mane_m, n=4, length=0.015, r=0.0045, spread=30)

# eyes: glossy black beads set into the face
for sx in (-1, 1):
    ps, ns = snap([(sx * 0.04, -0.03, 0.093)], (0, 0.0, 0.085), trees[:1])
    e = kit.sphere(0.0088, at=tuple(ps[0] - ns[0] * 0.003), scale=(1, 1, 1.12), material=eye_m, segs=20, rings=12, name='eye')
    head_parts.append(e)
# nostrils: two small stitched ovals on the front of the muzzle
for sx in (-1, 1):
    ps, ns = snap([(sx * 0.017, -0.09, 0.05)], (0, -0.04, 0.048), trees[1:])
    nos = kit.sphere(0.0058, scale=(0.55, 0.3, 1.0), at=(0, 0, 0), material=sole_m, segs=12, rings=8, name='nostril')
    nos.matrix_world = Matrix.Translation(ps[0] - ns[0] * 0.0008) @ q_from_to((0, -1, 0), ns[0]).to_matrix().to_4x4() \
        @ Matrix.Rotation(math.radians(sx * 25), 4, 'Y')
    head_parts.append(nos)

# halter: noseband round the muzzle, cheek pieces up past the ears and a crownpiece over the poll
SW, ST = 0.011, 0.0028
nb_way = [(0.048, -0.03, 0.05), (0.03, -0.042, 0.082), (0.0, -0.046, 0.088), (-0.03, -0.042, 0.082), (-0.048, -0.03, 0.05),
          (-0.04, -0.03, 0.017), (0.0, -0.03, 0.008), (0.04, -0.03, 0.017)]
pts, nrm = snap(catmull(nb_way, k=6, closed=True), (0, -0.03, 0.05), trees)
head_parts.append(strap(pts, nrm, SW, ST, halter_m, closed=True, name='noseband'))
cp_way = [(0.05, -0.022, 0.052), (0.052, -0.005, 0.078), (0.047, 0.018, 0.108), (0.03, 0.04, 0.138), (0.0, 0.048, 0.148),
          (-0.03, 0.04, 0.138), (-0.047, 0.018, 0.108), (-0.052, -0.005, 0.078), (-0.05, -0.022, 0.052)]
pts, nrm = snap(catmull(cp_way, k=6), (0, 0.0, 0.08), trees)
head_parts.append(strap(pts, nrm, SW, ST, halter_m, name='crownpiece'))
for sx in (-1, 1):
    ps, ns = snap([(sx * 0.05, -0.026, 0.05)], (0, -0.02, 0.05), trees)
    ring = kit.torus(0.0068, 0.0017, at=(0, 0, 0), material=brass, major=24, minor=8, name='halter_ring')
    ring.matrix_world = Matrix.Translation(ps[0] + ns[0] * 0.003) @ q_from_to((0, 0, 1), ns[0]).to_matrix().to_4x4()
    head_parts.append(ring)

xform(head_parts, Matrix.Translation((0, 0.004, ZB)) @ Matrix.Rotation(math.radians(-15), 4, 'Z'))

# ---------- front legs hooked over the brim, hooves resting on it ----------
for sx in (-1, 1):
    path = [(sx * 0.05, -0.018, ZB - 0.05), (sx * 0.055, -0.044, ZB - 0.006), (sx * 0.061, -0.07, ZB + 0.021),
            (sx * 0.067, -0.091, ZB + 0.0215), (sx * 0.071, -0.104, ZB + 0.019)]
    kit.tube(path, 0.021, material=plush, bevel_res=10, name='leg')
    end = Vector(path[-1]); prev = Vector(path[-2]); d = (end - prev).normalized()
    hoof = kit.lathe([(0, 0), (0.0205, 0), (0.0218, 0.004), (0.0214, 0.011), (0.0188, 0.0145), (0, 0.0148)],
                     material=hoof_m, steps=32, name='hoof')
    hoof.rotation_mode = 'QUATERNION'; hoof.rotation_quaternion = q_from_to((0, 0, 1), d)
    hoof.location = end - d * 0.002
    sole = kit.cyl(0.014, 0.002, material=sole_m, verts=24, name='sole')
    sole.rotation_mode = 'QUATERNION'; sole.rotation_quaternion = q_from_to((0, 0, 1), d)
    sole.location = end + d * 0.0128
    # cream fetlock fluff: a soft cuff round the leg just above the hoof
    c = end - d * 0.007
    perp = d.cross(Vector((0, 0, 1))).normalized(); up = perp.cross(d).normalized()
    cuff = []
    for k in range(10):
        a = k * math.tau / 10
        rdir = perp * math.cos(a) + up * math.sin(a)
        cuff.append((tuple(c + rdir * 0.019 - d * (0.002 * (k % 2))), (0.009, 0.009, 0.009), None))
    metaball('fetlock%d' % (sx + 1), cuff, muzzle_m, res=0.003, fuzz=0.0022)

kit.export('top-hat')
