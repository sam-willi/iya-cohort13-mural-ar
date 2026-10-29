"""Pet carrier - Ledger A.P.

His drawing: a soft-sided, backpack-style carrier with arched top corners. The front window is unzipped (zipper all round
the arch, the flap rolled up and strapped along the top) and a happy dog leans out of it, mouth open, paw on the sill.
Under the window runs a strap lettered "ABLOH HELLO"; below that, bungee cords criss-cross the front between hooks with a
tag dangling off one. The side has a big pocket, a small patch above it and a D-ring near the top.
Shaded pencil, so colours are a choice: teal canvas, black webbing and piping, the strap as a yellow industrial tape with
black letters (the Virgil Abloh nod), a honey-coloured dog. The back (not drawn) gets padded backpack straps.
Lettering read from the drawing: the second word is clearly HELLO; the first reads as ABLOH (could be misread).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

FONTS = '/System/Library/Fonts/Supplemental/'


def mesh_obj(name, verts, faces, materials=()):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in materials:
        o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def loft(name, rings, materials=(), caps=True):
    n = len(rings[0]); verts = [tuple(p) for r in rings for p in r]; faces = []
    for i in range(len(rings) - 1):
        for j in range(n):
            faces.append((i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j))
    if caps:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return mesh_obj(name, verts, faces, materials)


def rod(points, r, material, n=8, closed=False, name='rod'):
    P = [Vector(p) for p in points]; verts = []; faces = []
    m = len(P)
    for i, p in enumerate(P):
        if closed:
            t = (P[(i + 1) % m] - P[i - 1]).normalized()
        else:
            t = (P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized(); v = t.cross(u).normalized()
        for k in range(n):
            a = k / n * math.tau
            verts.append(tuple(p + (u * math.cos(a) + v * math.sin(a)) * r))
    segs = m if closed else m - 1
    for i in range(segs):
        i2 = (i + 1) % m
        for k in range(n):
            faces.append((i * n + k, i * n + (k + 1) % n, i2 * n + (k + 1) % n, i2 * n + k))
    if not closed:
        faces.append(tuple(reversed(range(n)))); faces.append(tuple(range((m - 1) * n, m * n)))
    return kit.finish(mesh_obj(name, verts, faces, [material]), None, smooth=60)


def cut(target, cutter, op='DIFFERENCE'):
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'; md.use_self = True
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def apply_xform(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def box_uv(o, size):
    me = o.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap'); uv.active = True; uv.active_render = True
    for p in me.polygons:
        ax = max(range(3), key=lambda i: abs(p.normal[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = [c for i, c in enumerate(co) if i != ax]
            uv.data[li].uv = (a / size, b / size)


def canvas_image(rgb, res=256, seed=5):
    """Fine woven canvas: alternating warp/weft ribs with slub noise, tinted to rgb (linear)."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:res, 0:res]
    n = 64
    fx = (x * n / res) % 1; fy = (y * n / res) % 1
    cell = ((np.floor(x * n / res) + np.floor(y * n / res)) % 2 == 0)
    rib = np.where(cell, np.sin(fx * math.pi), np.sin(fy * math.pi)) ** 0.7
    slub = rng.normal(0, 1, (res, 1)) * 0.04 + rng.normal(0, 1, (1, res)) * 0.04
    v = 0.82 + 0.18 * rib + slub
    img = np.ones((res, res, 4))
    for c in range(3):
        img[..., c] = np.clip(rgb[c] * v, 0, 1)
    im = bpy.data.images.new('canvas', res, res); im.pixels.foreach_set(img.astype(np.float32).ravel()); im.pack()
    return im


def tex_mat(name, image, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = image
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


# ---------------------------------------------------------------- materials
CANVAS = tex_mat('canvas', canvas_image(kit.hex_rgb('#2a6f78')[:3]), 0.85)
WEB = kit.mat('#1c1c1c', rough=0.75, name='webbing')
INSIDE = kit.mat('#141414', rough=0.9, name='inside')
YELLOW = kit.mat('lamp', rough=0.6, name='tape')
INK = kit.mat('black', rough=0.6, name='ink')
METAL = kit.mat('steel', rough=0.3, metal=0.9, name='metal')
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')
TAG = kit.mat('red', rough=0.45, name='tag')
FUR = kit.mat('#c8893d', rough=0.85, name='fur')
FUR_DARK = kit.mat('#8a5a2c', rough=0.85, name='ears')
NOSE = kit.mat('#141210', rough=0.25, name='nose')
EYE = kit.mat('#0e0c0b', rough=0.08, name='eye')
TONGUE = kit.mat('#d86a6a', rough=0.35, name='tongue')
MOUTH = kit.mat('#3a1612', rough=0.6, name='mouth')
PATCH = kit.mat('cream', rough=0.7, name='patch')

# ---------------------------------------------------------------- body: arch-topped, soft-edged box
W, D, HT = 0.34, 0.30, 0.48
YF, YB = -D / 2, D / 2


def outline(inset=0.0, n_arc=10):
    """Front-view outline (x, z), CCW from bottom centre: small bottom radius, big arched top corners."""
    w = W / 2 - inset; rt = 0.125 - inset * 0.5; rb = 0.03 - inset * 0.5
    z0 = inset * 0.6; z1 = HT - inset
    pts = [(0.0, z0)]
    for i in range(n_arc // 2 + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / (n_arc // 2)
        pts.append((w - rb + rb * math.cos(a), z0 + rb + rb * math.sin(a)))
    for i in range(n_arc + 1):
        a = (math.pi / 2) * i / n_arc
        pts.append((w - rt + rt * math.cos(a), z1 - rt + rt * math.sin(a)))
    pts.append((0.0, z1))
    right = pts
    left = [(-x, z) for x, z in reversed(right[1:-1])]
    return right + left


ends = [(0.0, 0.022), (0.002, 0.012), (0.007, 0.005), (0.014, 0.0015), (0.022, 0.0)]
ys = [YF + a for a, _ in ends] + [YB - a for a, _ in reversed(ends)]
insets = [b for _, b in ends] + [b for _, b in reversed(ends)]
rings = [[(x, y, z) for x, z in outline(ins)] for y, ins in zip(ys, insets)]
body = loft('body', rings, [CANVAS])

# the window: an arched opening into the dark inside
win = [(-0.118, 0.215), (0.118, 0.215), (0.118, 0.335)] + [(0.118 * math.cos(a), 0.335 + 0.10 * math.sin(a))
                                                             for a in [i / 12 * math.pi for i in range(1, 12)]] + [(-0.118, 0.335)]
cutter = kit.extrude(win, 0.16, material=INSIDE, name='wincut')
cutter.rotation_euler = (math.radians(90), 0, 0); cutter.location = (0, YF + 0.13, 0)
apply_xform(cutter)
cut(body, cutter)
box_uv(body, 0.12)
kit.finish(body, None, smooth=40)

# piping round the front and back faces
for y, s in ((YF + 0.004, 1), (YB - 0.004, 1)):
    pts = [(x * 0.985, y, 0.004 + z * 0.985) for x, z in outline(0.004, 16)][1:]
    rod(pts, 0.0045, WEB, n=8, closed=True, name='piping')

# zipper round the window arch: tape + teeth + pull
zw = [(-0.131, 0.205), (-0.131, 0.335)] + [(-0.131 * math.cos(a), 0.335 + 0.113 * math.sin(a))
                                           for a in [i / 24 * math.pi for i in range(1, 24)]] + [(0.131, 0.335), (0.131, 0.205)]
dense = []
for (x0, z0), (x1, z1) in zip(zw, zw[1:]):
    L = math.hypot(x1 - x0, z1 - z0); k = max(1, int(L / 0.006))
    for i in range(k):
        dense.append((x0 + (x1 - x0) * i / k, z0 + (z1 - z0) * i / k))
dense.append(zw[-1])
rod([(x, YF - 0.001, z) for x, z in zw], 0.0042, WEB, n=6, name='zipper tape')
teeth = []
for i, (x, z) in enumerate(dense):
    if True:
        a, b = Vector(dense[max(i - 1, 0)]), Vector(dense[min(i + 1, len(dense) - 1)])
        ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        teeth.append(kit.box((0.0028, 0.0035, 0.0085), at=(x, YF - 0.0045, z), rot=(0, -ang, 0), material=METAL,
                             name='tooth'))
bpy.ops.object.select_all(action='DESELECT')
for t in teeth:
    t.select_set(True)
bpy.context.view_layer.objects.active = teeth[0]; bpy.ops.object.join()
kit.box((0.012, 0.004, 0.026), at=(0.131, YF - 0.007, 0.19), material=METAL, bevel=0.002, name='pull')
kit.box((0.010, 0.003, 0.018), at=(0.131, YF - 0.009, 0.172), material=WEB, bevel=0.002, name='pulltab')

# rolled-up window flap strapped along the top front edge
roll = kit.cyl(0.03, W - 0.07, at=(0, YF + 0.045, HT - 0.005), rot=(0, 90, 0), material=CANVAS, verts=32, bevel=0.012,
               segments=3, name='roll')
box_uv(roll, 0.12)
kit.cyl(0.021, W - 0.069, at=(0, YF + 0.045, HT - 0.005), rot=(0, 90, 0), material=WEB, verts=24, name='rollcore')
for sx in (-0.09, 0.09):
    strap = [(sx, YF + 0.045 + 0.033 * math.cos(a), HT - 0.005 + 0.033 * math.sin(a)) for a in
             [i / 16 * math.tau for i in range(16)]]
    rod(strap, 0.0035, WEB, n=6, closed=True, name='rollstrap')
    kit.box((0.016, 0.004, 0.012), at=(sx, YF + 0.0125, HT - 0.012), material=METAL, bevel=0.0015, name='buckle')

# the lettered strap under the window
band = kit.box((W - 0.012, 0.006, 0.036), at=(0, YF - 0.001, 0.188), material=YELLOW, bevel=0.002, name='band')
cu = bpy.data.curves.new('lbl', 'FONT'); cu.body = 'ABLOH  HELLO'; cu.size = 0.026; cu.extrude = 0.0006
cu.font = bpy.data.fonts.load(FONTS + 'Impact.ttf'); cu.resolution_u = 3; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
lbl = bpy.data.objects.new('lbl', cu); bpy.context.collection.objects.link(lbl)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = lbl; lbl.select_set(True)
bpy.ops.object.convert(target='MESH'); lbl = bpy.context.object
lbl.data.materials.clear(); lbl.data.materials.append(INK)
lbl.rotation_euler = (math.radians(90), 0, 0); lbl.location = (0, YF - 0.0043, 0.188)
apply_xform(lbl)

# bungee cords criss-crossing the lower front, on hooks
top_a = [(-0.13, 0.163), (-0.01, 0.163), (0.12, 0.163)]
bot_a = [(-0.14, 0.035), (-0.03, 0.035), (0.085, 0.035)]
for (x0, z0), (x1, z1) in [(top_a[0], bot_a[1]), (top_a[1], bot_a[0]), (top_a[1], bot_a[2]), (top_a[2], bot_a[1]),
                           (top_a[2], bot_a[2]), (top_a[0], bot_a[0])]:
    mid = ((x0 + x1) / 2, YF - 0.009, (z0 + z1) / 2)
    rod([(x0, YF - 0.006, z0), mid, (x1, YF - 0.006, z1)], 0.0032, WEB, n=6, name='bungee')
for x, z in top_a + bot_a:
    kit.cyl(0.0075, 0.006, at=(x, YF - 0.003, z), rot=(90, 0, 0), material=METAL, verts=16, bevel=0.0015, name='eyelet')
# the dangling tag (a zip-tie tag off the right bottom hook)
kit.box((0.012, 0.003, 0.05), at=(0.092, YF - 0.009, 0.006), rot=(0, -12, 0), material=TAG, bevel=0.0015, name='tag')
rod([(0.085, YF - 0.008, 0.035), (0.089, YF - 0.009, 0.03)], 0.0018, TAG, n=6, name='tagloop')

# side pockets (both sides), a patch above the right one, D-rings near the top
for s in (1, -1):
    px = s * (W / 2 + 0.006)
    pk = kit.box((0.016, D - 0.07, 0.19), at=(px, 0.0, 0.115), material=CANVAS, bevel=0.007, segments=3, name='pocket')
    box_uv(pk, 0.12)
    kit.box((0.019, D - 0.072, 0.012), at=(px + s * 0.0005, 0.0, 0.205), material=WEB, bevel=0.003, name='pockettrim')
    kit.torus(0.013, 0.0025, at=(s * (W / 2 + 0.008), 0.06, HT - 0.07), rot=(0, 90, 0), material=METAL, major=20,
              minor=6, name='dring')
    kit.box((0.006, 0.022, 0.012), at=(s * (W / 2 + 0.002), 0.06, HT - 0.055), material=WEB, bevel=0.002, name='tab')
kit.box((0.003, 0.034, 0.05), at=(W / 2 + 0.002, -0.045, 0.27), rot=(8, 0, 0), material=PATCH, bevel=0.002, name='patch')
for dx, dz in ((-0.008, 0.008), (0.008, 0.008)):          # the patch's X-eyed face
    for a in (45, -45):
        kit.box((0.002, 0.009, 0.0016), at=(W / 2 + 0.0038, -0.045 + dx, 0.27 + dz), rot=(a, 0, 0), material=INK,
                name='x')
kit.box((0.002, 0.014, 0.0016), at=(W / 2 + 0.0038, -0.045, 0.257), material=INK, name='mouthline')

# back: padded backpack straps
for sx in (-0.075, 0.075):
    pts = [(sx, YB + 0.004, 0.43), (sx * 1.05, YB + 0.03, 0.38), (sx * 1.15, YB + 0.035, 0.22),
           (sx * 1.3, YB + 0.02, 0.07), (sx * 1.35, YB + 0.004, 0.05)]
    rod(pts, 0.016, WEB, n=10, name='shoulderstrap')
kit.box((W - 0.12, 0.012, 0.05), at=(0, YB + 0.006, 0.42), material=WEB, bevel=0.004, name='topstrapbar')
# base: rubber bumper
kit.box((W + 0.006, D + 0.006, 0.018), at=(0, 0, 0.009), material=RUBBER, bevel=0.007, segments=3, name='base')

# ---------------------------------------------------------------- the dog
from mathutils.bvhtree import BVHTree


def meta_blob(elements, name, material, res=0.005):
    mb = bpy.data.metaballs.new(name); mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    o = bpy.data.objects.new(name, mb); bpy.context.collection.objects.link(o)
    for (x, y, z), r, scale in elements:
        e = mb.elements.new(); e.co = (x, y, z); e.radius = r
        if scale:
            e.type = 'ELLIPSOID'; e.size_x, e.size_y, e.size_z = scale
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    return o


def ellipsoid(scale, M_, material, name, segs=20, rings=12):
    o = kit.sphere(1, at=(0, 0, 0), scale=scale, material=material, segs=segs, rings=rings, name=name)
    o.data.transform(M_); o.data.update()
    return o


HEAD = Vector((-0.012, YF + 0.004, 0.338))
YAW = math.radians(-22)           # looking out toward its right (the viewer's left)
M = Matrix.Translation(HEAD) @ Matrix.Rotation(YAW, 4, 'Z') @ Matrix.Rotation(math.radians(6), 4, 'X') @ Matrix.Scale(1.12, 4)
R_ = Matrix.Rotation(YAW, 4, 'Z') @ Matrix.Rotation(math.radians(6), 4, 'X')

# local frame: -Y is forward (out of the window), +Z up. Skull, stop, tapering muzzle, cheeks, neck back inside.
head = meta_blob([((0, 0.025, 0.012), 0.085, (1.0, 1.05, 0.95)),
                  ((0, -0.035, -0.012), 0.055, (0.85, 1.25, 0.78)),
                  ((0, -0.075, -0.018), 0.040, (0.78, 1.1, 0.70)),
                  ((0.034, -0.005, -0.022), 0.045, None), ((-0.034, -0.005, -0.022), 0.045, None),
                  ((0, 0.10, -0.06), 0.075, (1.0, 1.5, 1.0))], 'doghead', FUR)
head.data.transform(M); head.data.update()
kit.finish(head, None, smooth=80)
bvh = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())


def on_head(local_from, local_dir, sink=0.0):
    o = M @ Vector(local_from); d = (R_ @ Vector(local_dir).to_4d()).to_3d().normalized()
    hit = bvh.ray_cast(o, d)
    if hit[0] is None:
        return o
    return hit[0] + d * sink


# nose on the muzzle tip
tip = on_head((0, -0.25, -0.012), (0, 1, 0.0))
ellipsoid((0.017, 0.012, 0.012), Matrix.Translation(tip + (R_ @ Vector((0, 0.004, 0.003, 0))).to_3d()) @ R_, NOSE, 'nose')
# eyes and glints
for s in (1, -1):
    e = on_head((s * 0.03, -0.06, 0.026), (0, 1, 0), sink=0.004)
    kit.sphere(0.0085, at=tuple(e), material=EYE, segs=20, rings=10, name='eye')
    g = e + (R_ @ Vector((s * -0.002, -0.0075, 0.004, 0))).to_3d()
    kit.sphere(0.0022, at=tuple(g), material=kit.mat('white', rough=0.2, emit=0.3, name='glint'), segs=8, rings=6,
               name='glint')
    # floppy ears: hang from the top sides of the skull and lie against the cheeks
    root = on_head((s * 0.2, 0.02, 0.05), (-s, 0, -0.15), sink=0.004)
    ear_M = (Matrix.Translation(root + (R_ @ Vector((s * 0.008, 0.0, -0.035, 0))).to_3d()) @ R_ @
             Matrix.Rotation(math.radians(-s * 14), 4, 'Y') @ Matrix.Rotation(math.radians(-8), 4, 'X'))
    ellipsoid((0.011, 0.032, 0.048), ear_M, FUR_DARK, 'ear')
# open mouth: dark mouth, lower jaw, tongue lolling out over the lip
under = on_head((0, -0.06, -0.15), (0, 0, 1))
mouth_M = Matrix.Translation(under + (R_ @ Vector((0, 0.004, 0.006, 0))).to_3d()) @ R_ @ Matrix.Rotation(math.radians(-6), 4, 'X')
ellipsoid((0.024, 0.040, 0.010), mouth_M, MOUTH, 'mouth')
jaw_M = Matrix.Translation(under + (R_ @ Vector((0, 0.010, -0.006, 0))).to_3d()) @ R_ @ Matrix.Rotation(math.radians(-14), 4, 'X')
ellipsoid((0.026, 0.040, 0.011), jaw_M, FUR, 'jaw')
tg_M = Matrix.Translation(under + (R_ @ Vector((0.002, -0.022, -0.020, 0))).to_3d()) @ R_ @ Matrix.Rotation(math.radians(-68), 4, 'X')
ellipsoid((0.016, 0.027, 0.0055), tg_M, TONGUE, 'tongue')

# a paw on the sill, bottom left of the window
paw = meta_blob([((0, 0, 0), 0.032, (1.0, 1.4, 0.65)), ((0, 0.055, 0.012), 0.03, (1.0, 1.6, 1.0))], 'paw', FUR)
paw.data.transform(Matrix.Translation(Vector((-0.08, YF - 0.006, 0.228))) @ Matrix.Rotation(math.radians(-8), 4, 'Z'))
kit.finish(paw, None, smooth=80)
pb = BVHTree.FromObject(paw, bpy.context.evaluated_depsgraph_get())
for dx in (-0.013, -0.0045, 0.0045, 0.013):
    h = pb.ray_cast(Vector((-0.08 + dx, YF - 0.1, 0.226)), Vector((0, 1, 0)))[0]
    if h is not None:
        kit.sphere(0.0068, at=(h.x, h.y + 0.003, h.z - 0.001), material=FUR, segs=12, rings=8, name='toe')

kit.export('pet-carrier')
