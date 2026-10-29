"""Wireless earbuds - Riya Rajkumar.

Her drawing: a pair of stemmed earbuds standing face to face, speaker grilles turned toward each other, each with an
oval sensor on the cheek of the head and a vent slot on top. Between them, bold slab-serif "IYA" letters hang in a
stream of wavy signal lines running grille to grille, with small cubes and wire-cage spheres strung along the lines.
Colours are a choice: gloss white buds with dark mesh, cardinal letters, amber signal lines, brass cages, honey cubes.
Every letter, cube and sphere sits on a line, and every line runs into a grille, so nothing floats.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Quaternion

FONTS = '/System/Library/Fonts/Supplemental/'
random.seed(13)


def mesh_obj(name, verts, faces, materials=()):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in materials:
        o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def rod(points, r, material, n=6, name='rod'):
    P = [Vector(p) for p in points]; verts = []; faces = []; m = len(P)
    for i, p in enumerate(P):
        t = (P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized(); v = t.cross(u).normalized()
        for k in range(n):
            a = k / n * math.tau
            verts.append(tuple(p + (u * math.cos(a) + v * math.sin(a)) * r))
    for i in range(m - 1):
        for k in range(n):
            faces.append((i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k))
    faces.append(tuple(reversed(range(n)))); faces.append(tuple(range((m - 1) * n, m * n)))
    return kit.finish(mesh_obj(name, verts, faces, [material]), None, smooth=60)


def catmull(ctrl, per=10):
    P = [Vector(c) for c in ctrl]; P = [P[0]] + P + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def cut(target, cutter, op='DIFFERENCE'):
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'; md.use_self = True
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


# ---------------------------------------------------------------- materials
SHELL = kit.mat('white', rough=0.22, name='bud')
MESH = kit.mat('gunmetal', rough=0.45, metal=0.85, name='grille')
SENSOR = kit.mat('#101010', rough=0.12, name='sensor')
LETTER = kit.mat('cardinal', rough=0.35, name='letters')
LINE = kit.mat('amber', rough=0.4, emit=0.35, name='signal')
CAGE = kit.mat('brass', rough=0.3, metal=1.0, name='cage')
CORE = kit.mat('teal', rough=0.2, alpha=0.75, name='core')
CUBE = kit.mat('honey', rough=0.45, name='cube')

HZ = 0.0335                 # head centre height
GAP = 0.094                 # distance between the two buds' axes
from mathutils.bvhtree import BVHTree


def earbud(s):
    """s = -1 for the left bud (grille faces +X), +1 for the right one (grille faces -X)."""
    cx = s * GAP / 2
    g = -s                                   # grille direction along X
    # metaballs can't resolve finer than 5 mm, so the bud is built 10x up and scaled down
    K = 10.0; F = 1 / 0.535                  # metaball radius -> surface radius
    mb = bpy.data.metaballs.new('bud'); mb.resolution = 0.0085; mb.render_resolution = 0.0085; mb.threshold = 0.6
    o = bpy.data.objects.new('bud', mb); bpy.context.collection.objects.link(o)

    def ball(co, r, size=None, kind='BALL', rot=None):
        e = mb.elements.new(); e.co = [c * K for c in co]; e.radius = r * K * F; e.type = kind
        if size:
            e.size_x, e.size_y, e.size_z = size
        if rot:
            e.rotation = rot
        return e
    ball((0, 0, HZ), 0.0108, (1.0, 0.94, 0.97), 'ELLIPSOID')                         # the bulb
    ball((g * 0.0058, -0.0010, HZ - 0.0008), 0.0078, (1.0, 0.9, 0.9), 'ELLIPSOID')    # nozzle swell
    q = Quaternion((0, 1, 0), math.radians(90))                                      # capsule along Z
    ball((-g * 0.0010, 0.0006, HZ - 0.0255), 0.0042, (0.016 * K, 1, 1), 'CAPSULE', q)  # the stem
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.transform(Matrix.Translation((cx, 0, 0)) @ Matrix.Scale(1 / K, 4)); o.data.update()
    o.data.materials.clear(); o.data.materials.append(SHELL)
    # flat stem end, as drawn
    cut(o, kit.box((0.03, 0.03, 0.02), at=(cx, 0, -0.01 + 0.0012), material=SHELL))
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())

    def hit(frm, to):
        frm = Vector(frm); d = (Vector(to) - frm).normalized()
        h = bvh.ray_cast(frm, d)
        return h[0], h[1]
    # speaker grille: a recess with a rim, filled with dark mesh
    hg, ng = hit((cx + g * 0.1, -0.0010, HZ - 0.0008), (cx, -0.0010, HZ - 0.0008))
    c = kit.cyl(0.0056, 0.012, at=(hg.x + g * 0.0052, hg.y, hg.z), rot=(0, 90, 0), material=MESH, verts=40)
    cut(o, c)
    kit.finish(o, None, smooth=80)
    gx = hg.x - g * 0.0009
    kit.cyl(0.0056, 0.0008, at=(gx - g * 0.0002, hg.y, hg.z), rot=(0, 90, 0), material=MESH, verts=40, name='mesh')
    wires = []
    for k in range(-5, 6):
        for rot in (45, -45):
            L = 2 * math.sqrt(max(0.0, 0.0054 ** 2 - (k * 0.00095) ** 2))
            if L < 0.001:
                continue
            w = kit.box((0.0003, 0.00028, L), at=(0, 0, 0), material=MESH, name='wire')
            M = (Matrix.Translation((gx + g * 0.0003, hg.y, hg.z)) @ Matrix.Rotation(math.radians(rot), 4, 'X') @
                 Matrix.Translation((0, k * 0.00095, 0)))
            w.data.transform(M); w.data.update(); wires.append(w)
    bpy.ops.object.select_all(action='DESELECT')
    for w in wires:
        w.select_set(True)
    bpy.context.view_layer.objects.active = wires[0]; bpy.ops.object.join()

    def inset(frm, scale, name, sink=0.0006, spin=0.0):
        p, n = hit(frm, (cx, 0, HZ))
        q = n.to_track_quat('Y', 'Z')            # local Y along the surface normal
        M = (Matrix.Translation(p - n * sink) @ q.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(spin), 4, 'Y'))
        e = kit.sphere(1, at=(0, 0, 0), scale=scale, material=SENSOR, segs=20, rings=10, name=name)
        e.data.transform(M); e.data.update()
    # oval sensor on the cheek toward the viewer, vent slot on top toward the grille, a small one at the back
    inset((cx + g * 0.004, -0.1, HZ + 0.004), (0.0036, 0.0011, 0.0016), 'sensor', spin=12 * g)
    inset((cx + g * 0.006, 0.0, HZ + 0.1), (0.0015, 0.0011, 0.0036), 'vent', spin=0)
    inset((cx - g * 0.004, 0.1, HZ + 0.002), (0.0022, 0.0010, 0.0013), 'backsensor')
    # charging contact at the stem end
    kit.cyl(0.0016, 0.0003, at=(cx - g * 0.0010, 0.0006, 0.0011), material=CAGE, verts=16, name='contact')
    return gx, hg


(gL, hL), (gR, hR) = earbud(-1), earbud(1)
x0, x1 = gL - 0.0004, gR + 0.0004
GY, GZ = hL.y, hL.z

# ---------------------------------------------------------------- IYA in bold slab capitals
cu = bpy.data.curves.new('iya', 'FONT'); cu.body = 'IYA'; cu.size = 0.024; cu.extrude = 0.003
cu.bevel_depth = 0.0003; cu.bevel_resolution = 1
cu.font = bpy.data.fonts.load(FONTS + 'Rockwell.ttc'); cu.resolution_u = 3; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
cu.space_character = 1.05
iya = bpy.data.objects.new('iya', cu); bpy.context.collection.objects.link(iya)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = iya; iya.select_set(True)
bpy.ops.object.convert(target='MESH'); iya = bpy.context.object
iya.data.materials.clear(); iya.data.materials.append(LETTER)
LZ = HZ - 0.004
iya.data.transform(Matrix.Translation((0, 0.0, LZ)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
iya.data.update()
kit.finish(iya, None, smooth=30)
bb = [iya.matrix_world @ Vector(c) for c in iya.bound_box]
lx0 = min(p.x for p in bb); lx1 = max(p.x for p in bb)
w = lx1 - lx0
# letter anchor points the lines thread through: the I's stem, the Y's stem, the A's crossbar
anchors = [Vector((lx0 + w * 0.13, 0.0, LZ - 0.001)), Vector((lx0 + w * 0.50, 0.0, LZ - 0.004)),
           Vector((lx0 + w * 0.84, 0.0, LZ - 0.002))]

# ---------------------------------------------------------------- signal lines, grille to grille
lines = []
NL = 8
for i in range(NL):
    a = (i / NL) * math.tau + 0.3
    gy = GY + 0.0036 * math.cos(a); gz = GZ + 0.0036 * math.sin(a)
    start = Vector((x0, gy, gz)); end = Vector((x1, GY + 0.0036 * math.cos(a + 0.6), GZ + 0.0036 * math.sin(a + 0.6)))
    ctrl = [start, start + Vector((0.004, 0, 0))]
    if i < 3:
        # these three run through the letters, holding them up
        ctrl += [anchors[0] + (Vector() if i == 0 else Vector((-0.002, 0.007, 0.007 * (i - 1.5)))),
                 anchors[1] + (Vector() if i == 1 else Vector((0, 0.006 * (i - 1), -0.007))),
                 anchors[2] + (Vector() if i == 2 else Vector((0.002, 0.006, 0.007 * (1 - i))))]
    else:
        amp_y = random.uniform(0.005, 0.011) * (1 if i % 2 else -1); amp_z = random.uniform(0.004, 0.010)
        ph = random.uniform(0, math.tau)
        for k in range(1, 5):
            t = k / 5
            x = x0 + (x1 - x0) * t
            ctrl.append(Vector((x, gy + amp_y * math.sin(t * math.pi) + 0.004,
                                gz + amp_z * math.sin(t * 2 * math.pi + ph) * math.sin(t * math.pi))))
    ctrl += [end - Vector((0.004, 0, 0)), end]
    pts = catmull(ctrl, 10)
    rod([tuple(p) for p in pts], 0.00028, LINE, n=5, name='signal')
    lines.append(pts)

# ---------------------------------------------------------------- cubes and wire-cage spheres strung on the lines
def cube_on(p, s):
    rot = (random.uniform(-25, 25), random.uniform(-25, 25), random.uniform(0, 90))
    kit.box((s, s, s), at=tuple(p), rot=rot, material=CUBE, bevel=s * 0.08, segments=1, name='cube')


def cage_on(p, r):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=tuple(p))
    o = bpy.context.object; o.name = 'cage'
    md = o.modifiers.new('wire', 'WIREFRAME'); md.thickness = r * 0.12; md.use_replace = True
    o.data.materials.append(CAGE)
    kit.sphere(r * 0.62, at=tuple(p), material=CORE, segs=16, rings=8, name='core')


picks = [(3, 0.28, 'c', 0.0058), (4, 0.62, 'c', 0.0048), (5, 0.40, 's', 0.0036), (6, 0.76, 'c', 0.0054),
         (7, 0.22, 's', 0.0032), (3, 0.70, 's', 0.0038), (5, 0.84, 'c', 0.0042), (7, 0.55, 'c', 0.0036),
         (6, 0.16, 's', 0.0028), (1, 0.18, 'c', 0.0034), (2, 0.86, 's', 0.0030)]
for li, t, kind, size in picks:
    pts = lines[li]; p = pts[int(t * (len(pts) - 1))]
    (cube_on if kind == 'c' else cage_on)(p, size)

kit.export('wireless-earbuds')
