"""Violin. There's no student drawing for this one in the folder, so it's a classic full-size violin.

Standing upright on its end button, the top plate facing the front, scroll up. Arched top and back over ribs,
pointed corners, black purfling, f-holes, ebony fingerboard, nut, pegs, tailpiece, saddle, chinrest and end button,
a maple bridge, four steel strings, pegbox and scroll. Varnish in the mural's copper-orange.
Built in millimetres (scaled to metres at the end).
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

kit.reset()
MM = 0.001


# ---------------------------------------------------------------- helpers (local to this script)
def bake_join(name, objs=None):
    objs = objs or [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o


def settle(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    o.data.transform(Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
    return o


def mesh_obj(name, verts, faces, material=None, smooth=40):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(c * MM for c in v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    return kit.finish(o, material, smooth=smooth)


def loft(name, rings, material, cap=True, smooth=40):
    """Faces between equal-length rings of 3D points (mm); optional fan caps at both ends."""
    n = len(rings[0]); verts = [p for r in rings for p in r]; faces = []
    for i in range(len(rings) - 1):
        for j in range(n):
            a = i * n + j; b = i * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap:
        for r, base in ((rings[0], 0), (rings[-1], (len(rings) - 1) * n)):
            c = len(verts); verts.append(tuple(sum(p[k] for p in r) / n for k in range(3)))
            for j in range(n):
                faces.append((base + j, base + (j + 1) % n, c))
    return mesh_obj(name, verts, faces, material, smooth)


def ltube(points, r, material=None, res_u=3, bevel_res=1, name='tube'):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('NURBS'); sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*(v * MM for v in c), 1)
    sp.use_endpoint_u = True; sp.order_u = min(4, len(points))
    cu.bevel_depth = r * MM; cu.bevel_resolution = bevel_res; cu.resolution_u = res_u; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def rod(a, b, r, material=None, verts=12, name='rod'):
    a, b = Vector(a) * MM, Vector(b) * MM; d = b - a
    o = kit.cyl(r * MM, d.length, at=(a + b) / 2, material=material, verts=verts, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def interp(table, y):
    """Monotone cubic (PCHIP) through the table, so the outline is smooth without overshooting the corners."""
    xs = [p[0] for p in table]; ys_ = [p[1] for p in table]; n = len(xs)
    if y <= xs[0]:
        return ys_[0]
    if y >= xs[-1]:
        return ys_[-1]
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]; dl = [(ys_[i + 1] - ys_[i]) / h[i] for i in range(n - 1)]
    m = [dl[0]] + [0.0] * (n - 2) + [dl[-1]]
    for i in range(1, n - 1):
        if dl[i - 1] * dl[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])
    for i in range(n - 1):
        if xs[i] <= y <= xs[i + 1]:
            t = (y - xs[i]) / h[i]
            h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
            return h00 * ys_[i] + h10 * h[i] * m[i] + h01 * ys_[i + 1] + h11 * h[i] * m[i + 1]


# ---------------------------------------------------------------- materials
VARNISH = kit.mat('#953f18', rough=0.28, name='varnish')
NECKV = kit.mat('#a34b1e', rough=0.32, name='neck_varnish')
EBONY = kit.mat('#161412', rough=0.35, name='ebony')
MAPLE = kit.mat('#e3c391', rough=0.6, name='bridge_maple')
STEEL = kit.mat('chrome', rough=0.3, metal=0.9, name='string')
GUT = kit.mat('#d8c6a0', rough=0.6, name='tailgut')

# ---------------------------------------------------------------- body: half-width along the length (mm), corners as quick steps
L = 356.0
HALF = [(0, 10), (3, 38), (9, 58), (20, 76), (35, 90), (55, 99), (80, 103), (100, 102), (120, 97), (134, 93), (141, 91.5),
        (145, 71), (152, 61), (166, 56.5), (185, 55), (204, 58), (215, 64), (221, 73), (226, 82), (232, 80), (245, 82),
        (265, 84), (285, 82), (304, 76), (321, 66), (335, 52), (345, 36), (351, 22), (L, 8)]
RIB = 30.0


def arch_top(y):
    return 15.5 * max(0.0, math.sin(math.pi * y / L)) ** 0.55


def arch_back(y):
    return 13.0 * max(0.0, math.sin(math.pi * y / L)) ** 0.55


def top_z(x, y):
    w = interp(HALF, y); u = min(1.0, abs(x) / max(w, 1e-6))
    return RIB / 2 + arch_top(y) * (1 - u * u) ** 1.4


ys = sorted(set([y for y, _ in HALF] + [y + d for y, _ in HALF for d in (3.0,) if y + d < L] + [i * L / 60 for i in range(61)]))
rings = []
for y in ys:
    w = interp(HALF, y)
    inset = min(2.5, w * 0.25)
    ring = []
    for k in range(15):                                  # top plate, +x edge to -x edge
        x = w * math.cos(math.pi * k / 14)
        ring.append((x, y, top_z(x, y)))
    ring += [(-w, y, RIB / 2 - 2.8), (-(w - inset), y, RIB / 2 - 3.4), (-(w - inset), y, -RIB / 2 + 3.4), (-w, y, -RIB / 2 + 2.8)]
    for k in range(15):                                  # back plate, -x edge to +x edge
        x = -w * math.cos(math.pi * k / 14)
        u = min(1.0, abs(x) / max(w, 1e-6))
        ring.append((x, y, -RIB / 2 - arch_back(y) * (1 - u * u) ** 1.4))
    ring += [(w, y, -RIB / 2 + 2.8), (w - inset, y, -RIB / 2 + 3.4), (w - inset, y, RIB / 2 - 3.4), (w, y, RIB / 2 - 2.8)]
    rings.append(ring)
body = loft('body', rings, VARNISH, smooth=50)

# purfling: a black line 4 mm in from the edge, on the top and the back
for side in (1, -1):
    path = []
    for y in [i * L / 90 for i in range(1, 90)]:
        w = interp(HALF, y) - 4.0
        if w > 3:
            z = top_z(w, y) + 0.25 if side > 0 else -(RIB / 2 + arch_back(y) * (1 - (w / (w + 4)) ** 2) ** 1.4) - 0.25
            path.append((w, y, z))
    loop = path + [(-x, y, z) for x, y, z in reversed(path)] + [path[0]]
    ltube(loop, 0.6, EBONY, res_u=1, bevel_res=0, name='purfling')

# f-holes: an S-shaped slot with an eye at each end and the two nicks, laid on the arching
for s in (1, -1):
    pts = []
    for k in range(13):
        t = k / 12
        y = 156 + 70 * t
        x = s * (47 - 15 * t + 4.5 * math.sin(math.tau * t))
        pts.append((x, y, top_z(x, y) + 0.35))
    ltube(pts, 1.5, EBONY, res_u=2, bevel_res=1, name='fhole')
    for (x, y, r) in ((s * 47.5, 155, 3.6), (s * 31.5, 227, 3.2)):
        kit.cyl(r * MM, 0.6 * MM, at=(x * MM, y * MM, (top_z(x, y) + 0.2) * MM), material=EBONY, verts=14, name='feye')
    for dy in (-1, 1):                                   # nicks
        x = s * (40 + 2.0); y = 191
        rod((x, y, top_z(x, y) + 0.3), (x + s * 4.5, y + dy * 0.3, top_z(x + s * 4.5, y) + 0.3), 0.7, EBONY, 6, 'nick')

# ---------------------------------------------------------------- neck, fingerboard, nut, pegbox, pegs, scroll
NUT_Y, FB_END = 486.0, 216.0
fb_top = lambda y: 13.5 + (NUT_Y - y) * (40.5 / (NUT_Y - FB_END))
fb_w = lambda y: 24 + (NUT_Y - y) / (NUT_Y - FB_END) * 18
fb_rings = []
for y in (FB_END, 300, 400, NUT_Y):
    w = fb_w(y) / 2; zt = fb_top(y)
    ring = [(w * math.cos(math.pi * k / 10), y, zt - 2.5 + 2.5 * math.sin(math.pi * k / 10) * 1.0) for k in range(11)]
    ring += [(-w, y, zt - 8.5), (w, y, zt - 8.5)]
    fb_rings.append(ring)
loft('fingerboard', fb_rings, EBONY, smooth=35)
neck_rings = []
for y in (346, 370, 420, 470, NUT_Y + 2):
    w = fb_w(min(y, NUT_Y)) / 2 - 0.6; zt = fb_top(min(y, NUT_Y)) - 8.5
    depth = 19 + (1 - (y - 346) / 140) * 6
    ring = [(w, y, zt + 0.2), (-w, y, zt + 0.2)] + [(-w * math.cos(math.pi * k / 10), y, zt - depth * math.sin(math.pi * k / 10)) for k in range(1, 10)]
    neck_rings.append(ring)
loft('neck', neck_rings, NECKV, smooth=50)
# heel: a block from the neck root down onto the back's button
heel = kit.box((26 * MM, 22 * MM, 44 * MM), at=(0, 352 * MM, 2 * MM), material=NECKV, bevel=6 * MM, segments=3, name='heel')
kit.box((26 * MM, 6 * MM, 5 * MM), at=(0, (NUT_Y - 1) * MM, (fb_top(NUT_Y) + 0.8) * MM), material=EBONY, bevel=1.2 * MM, name='nut')
# pegbox: cheeks with a dark well between them
PB0, PB1 = NUT_Y + 1, 560.0
for s in (1, -1):
    kit.box((4.5 * MM, (PB1 - PB0) * MM, 26 * MM), at=(s * 10.5 * MM, (PB0 + PB1) / 2 * MM, (fb_top(NUT_Y) - 14) * MM), material=NECKV,
            bevel=1.5 * MM, name='cheek')
kit.box((17 * MM, (PB1 - PB0) * MM, 6 * MM), at=(0, (PB0 + PB1) / 2 * MM, (fb_top(NUT_Y) - 24) * MM), material=NECKV, bevel=1.5 * MM, name='pbfloor')
kit.box((16.6 * MM, (PB1 - PB0 - 2) * MM, 1 * MM), at=(0, (PB0 + PB1) / 2 * MM, (fb_top(NUT_Y) - 20.5) * MM), material=EBONY, name='well')
for i, y in enumerate((497, 512, 527, 542)):
    s = 1 if i % 2 == 0 else -1
    z = fb_top(NUT_Y) - 12
    rod((-s * 14, y, z), (s * 18, y, z), 3.2, EBONY, 12, 'pegshaft')
    head = kit.sphere(11 * MM, at=(s * 30 * MM, y * MM, z * MM), scale=(1.0, 0.95, 0.38), material=EBONY, segs=20, rings=10, name='peghead')
    head.rotation_euler = (math.radians(90), 0, 0)
    kit.sphere(4 * MM, at=(s * 19.5 * MM, y * MM, z * MM), scale=(0.7, 1, 1), material=EBONY, segs=12, rings=6, name='pegcollar')
# scroll: a core with spiral volutes on both cheeks
SC = Vector((0, 578, fb_top(NUT_Y) - 12))
kit.cyl(17 * MM, 30 * MM, at=SC * MM, rot=(0, 90, 0), material=NECKV, verts=40, bevel=2.5 * MM, segments=2, name='scrollcore')
kit.box((24 * MM, 20 * MM, 22 * MM), at=(0, 563 * MM, (SC.z - 4) * MM), material=NECKV, bevel=3 * MM, name='throat')
for s in (1, -1):
    pts = []
    for k in range(40):
        t = k / 39; th = math.radians(-60) + t * 2.4 * math.tau; r = 16.5 * (1 - 0.78 * t)
        pts.append((s * (15.4 + 1.6 * t), SC.y + r * math.cos(th), SC.z + r * math.sin(th)))
    ltube(pts, 2.1, NECKV, res_u=3, bevel_res=1, name='volute')
    kit.cyl(4.2 * MM, 3 * MM, at=(s * 16.5 * MM, SC.y * MM, SC.z * MM), rot=(0, 90, 0), material=NECKV, verts=18, bevel=1.2 * MM, name='eye')

# ---------------------------------------------------------------- bridge, tailpiece, saddle, chinrest, end button, strings
BY = 192.0
bz = top_z(0, BY)
bridge_o = [(-21, -1.5), (-12, -1.5), (-9, 5), (-12, 14), (12, 14), (9, 5), (12, -1.5), (21, -1.5), (20, 6), (19.5, 18), (19, 28), (12, 33.5), (0, 35),
            (-12, 33.5), (-19, 28), (-19.5, 18), (-20, 6)]
br = kit.extrude([(x * MM, z * MM) for x, z in bridge_o], 3.6 * MM, rot=(90, 0, 0), material=MAPLE, bevel=0.6 * MM, name='bridge')
br.location = (0, (BY + 1.8) * MM, (bz - 0.5) * MM)
br.rotation_euler = (math.radians(90), 0, 0)
heart = kit.extrude([(x * MM, z * MM) for x, z in ((0, 19), (3.5, 23), (2.5, 26), (0, 25), (-2.5, 26), (-3.5, 23))], 10 * MM, rot=(90, 0, 0), name='heartcut')
heart.location = (0, (BY + 5) * MM, (bz - 0.5) * MM)
kit.boolean(br, heart)
BTOP = bz - 0.5 + 34.0
# tailpiece, tilted to follow the arch
tp = kit.extrude([(x * MM, y * MM) for x, y in ((-10, 0), (10, 0), (19.5, 92), (17, 108), (-17, 108), (-19.5, 92))], 6 * MM,
                 material=EBONY, bevel=1.8 * MM, segments=2, name='tailpiece')
tp.location = (0, 12 * MM, (RIB / 2 + 6.5) * MM)
tp.rotation_euler = (math.radians(5.6), 0, 0)
TP_TOP = Vector((0, 118, RIB / 2 + 6.5 + 6 + 108 * math.tan(math.radians(5.6)) + 0.5))
kit.box((30 * MM, 4 * MM, 4 * MM), at=(0, 118.5 * MM, (TP_TOP.z - 0.5) * MM), material=EBONY, bevel=1 * MM, name='tpfret')
ltube([(-6, 13, RIB / 2 + 7), (-6, 2, RIB / 2 + 4), (0, -2, RIB / 2 - 1), (6, 2, RIB / 2 + 4), (6, 13, RIB / 2 + 7)], 1.3, GUT, 3, 1, 'tailgut')
kit.box((32 * MM, 6 * MM, 4 * MM), at=(0, 1.0 * MM, (RIB / 2 + 0.8) * MM), material=EBONY, bevel=1.2 * MM, name='saddle')
rod((0, 2, 0), (0, -6, 0), 3.5, EBONY, 16, 'endpin')
kit.sphere(6 * MM, at=(0, -7 * MM, 0), material=EBONY, segs=16, rings=8, name='endbutton')
cr = kit.sphere(25 * MM, at=(-46 * MM, 28 * MM, (RIB / 2 + 11) * MM), scale=(1.0, 0.72, 0.22), material=EBONY, segs=24, rings=12, name='chinrest')
rod((-46, 28, RIB / 2 + 3), (-46, 28, RIB / 2 + 10), 8, EBONY, 16, 'chinfoot')
for dx in (-12, 12):
    rod((-46 + dx, 28, RIB / 2 + 6), (-46 + dx, 28, RIB / 2 + 2), 2.2, STEEL, 8, 'chinpost')
# strings
for i, x_b in enumerate((-15.5, -5.2, 5.2, 15.5)):
    x_t = (-13.5, -4.5, 4.5, 13.5)[i]; x_n = (-8.4, -2.8, 2.8, 8.4)[i]
    r = (0.55, 0.45, 0.4, 0.3)[i]
    edge = [(0, 35.0), (12, 33.5), (19, 28.0)]
    zb = bz - 0.5 + interp(edge, abs(x_b)) + r * 0.6
    rod((x_t, TP_TOP.y, TP_TOP.z), (x_b, BY, zb), r, STEEL, 6, 'string')
    rod((x_b, BY, zb), (x_n, NUT_Y, fb_top(NUT_Y) + 1.6), r, STEEL, 6, 'string')
    rod((x_n, NUT_Y, fb_top(NUT_Y) + 1.6), (x_n * 0.6, 500 + i * 13, fb_top(NUT_Y) - 12), r, STEEL, 6, 'string')
    kit.cyl(1.4 * MM, 3 * MM, at=(x_t * MM, (TP_TOP.y - 2) * MM, (TP_TOP.z - 0.5) * MM), material=STEEL, verts=10, name='ball')

# ---------------------------------------------------------------- stand it up: length along Z, top plate facing the front (-Y)
v = bake_join('violin')
v.matrix_world = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ v.matrix_world
settle(v)
kit.export('violin')
