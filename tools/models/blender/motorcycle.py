import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

# ---- local helpers (kept in this file so the script stands alone) ----
TAU = math.tau


def desel():
    for o in bpy.context.selected_objects:
        o.select_set(False)


def tube(points, r, material=None, closed=False, res=12, name='tube'):
    # kit.tube converts *every* selected object to mesh; deselect first so it only touches the new curve.
    desel()
    return kit.tube(points, r, material, closed, res, name)


def catmull(points, n=6, closed=False):
    """Catmull-Rom spline through the points (passes through every point)."""
    P = [Vector(p) for p in points]
    if closed:
        P = P[-1:] + P + P[:2]
    else:
        P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(P[-2])
    return out


def tube_lo(points, r, material=None, sides=10, closed=False, name='tube', smooth=60):
    """Light round tube through a polyline (parallel-transport frames, n-sided), capped unless closed."""
    P = [Vector(p) for p in points]; N = len(P)
    T = []
    for i in range(N):
        a = P[i - 1] if (closed or i > 0) else P[i]
        b = P[(i + 1) % N] if (closed or i < N - 1) else P[i]
        T.append((b - a).normalized())
    n0 = T[0].orthogonal().normalized(); frames = []
    nrm = n0
    for i in range(N):
        nrm = (nrm - T[i] * nrm.dot(T[i])).normalized()
        frames.append((nrm, T[i].cross(nrm)))
    bm = bmesh.new()
    rings = [[bm.verts.new(P[i] + r * (math.cos(TAU * k / sides) * frames[i][0] + math.sin(TAU * k / sides) * frames[i][1]))
              for k in range(sides)] for i in range(N)]
    segs = range(N) if closed else range(N - 1)
    for i in segs:
        j = (i + 1) % N
        for k in range(sides):
            l = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[i][l], rings[j][l], rings[j][k]))
    if not closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    return link(name, bm, material, smooth)


def link(name, bm, material=None, smooth=30, bevel=0.0, segments=2, at=(0, 0, 0), rot=None):
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = at
    if rot:
        o.rotation_euler = [math.radians(a) for a in rot]
    return kit.finish(o, material, bevel, segments, smooth)


def rrect(w, h, r, n=6, cx=0.0, cy=0.0):
    """Rounded rectangle, CCW, as [(x, y)]; n segments per corner."""
    r = min(r, w / 2 - 1e-5, h / 2 - 1e-5)
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def resample(poly, n):
    """Resample a closed polyline to n points evenly spaced by arc length."""
    P = [Vector((p[0], p[1], 0)) for p in poly]
    seg = [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    L = [(b - a).length for a, b in seg]; tot = sum(L)
    out = []
    for k in range(n):
        d = tot * k / n; i = 0
        while d > L[i] and i < len(L) - 1:
            d -= L[i]; i += 1
        a, b = seg[i]; t = d / L[i] if L[i] else 0
        q = a.lerp(b, t); out.append((q.x, q.y))
    return out


def loft(rings, name='loft', material=None, cap0=True, cap1=True, smooth=40, bevel=0.0, closed=True):
    """rings: list of rings, each a list of 3D points (same count). Quads between rings, n-gon caps."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap0:
        bm.faces.new(list(reversed(vr[0])))
    if cap1:
        bm.faces.new(vr[-1])
    return link(name, bm, material, smooth, bevel)


def apply_all(o):
    desel(); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.select_set(False)
    return o


def cut(target, cutter, op='DIFFERENCE'):
    """Boolean with modifiers on the cutter applied first."""
    cutter = apply_all(cutter)
    return kit.boolean(target, cutter, op)


def text_mesh(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, align='CENTER', name='text',
              spacing=1.0, res=5):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.resolution_u = res
    cu.align_x = align; cu.align_y = 'CENTER'; cu.space_character = spacing
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    desel(); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.select_set(False)
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def image_mat(name, rgb_array, rough=0.6, metal=0.0):
    """Material with a generated texture. rgb_array: HxWx3 float sRGB 0..1."""
    h, w, _ = rgb_array.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(rgb_array, 0, 1)
    img.pixels.foreach_set(px[::-1].ravel()); img.pack()
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


def wood_tex(base, dark, size=512, rings=14.0, seed=1, figure=1.0, contrast=1.0):
    """Straight-grain wood (grain runs along U): soft latewood lines, fine streaks, slow colour drift.
    Returns HxWx3 sRGB floats."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size] / size          # v across the grain, u along it

    def smooth1d(n, k):
        a = rng.normal(0, 1, n + 2 * k)
        w = np.hanning(2 * k + 1); w /= w.sum()
        return np.convolve(a, w, 'valid')[:n]
    # gentle waviness of the growth rings along the board
    d = np.zeros_like(u)
    for k in range(1, 4):
        d += rng.uniform(0.3, 1.0) / k * np.sin(TAU * (k * u + rng.uniform()) + v * rng.uniform(0, 2))
    p = v * rings + d * 0.25 * figure + smooth1d(size, 12)[:, None] * 0.6
    f = p - np.floor(p)
    late = np.clip((f - 0.62) / 0.3, 0, 1) ** 1.5 * (1 - np.clip((f - 0.95) / 0.05, 0, 1))
    streak = smooth1d(size, 1)[:, None] * np.ones((1, size)) * 0.5 + smooth1d(size * 4, 2).reshape(size, 4).mean(1)[:, None] * 0.3
    drift = smooth1d(size, 60)[:, None] * 0.8 + smooth1d(size, 80)[None, :] * 0.6
    t = 0.55 * late + 0.12 * streak + 0.18 * drift + 0.18
    t = np.clip(0.5 + (t - 0.5) * contrast, 0, 1)[..., None]
    c0 = np.array(kit.hex_rgb(base)[:3]) ** (1 / 2.2); c1 = np.array(kit.hex_rgb(dark)[:3]) ** (1 / 2.2)
    return c0 * (1 - t) + c1 * t


def box_uv(o, grain='z', scale=1.0):
    """Box-project UVs in object space so wood grain runs along `grain` (U runs along it)."""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new()
    uv = me.uv_layers.active.data
    ax = 'xyz'.index(grain); others = [i for i in range(3) if i != ax]
    for p in me.polygons:
        nrm = p.normal; dom = max(range(3), key=lambda i: abs(nrm[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if dom == ax:
                u, v = co[others[0]], co[others[1]]
            else:
                side = [i for i in others if i != dom][0] if dom in others else others[0]
                u, v = co[ax], co[side]
            uv[li].uv = (u * scale, v * scale)
    return o


def merge_by_material():
    """Apply modifiers and join meshes that share a material (fewer draw calls on the phone)."""
    groups = {}
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH':
            continue
        o = apply_all(o)
        key = o.data.materials[0].name if o.data.materials else ''
        groups.setdefault(key, []).append(o)
    for key, objs in groups.items():
        if len(objs) < 2:
            continue
        desel()
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
    desel()


def drop_to_floor():
    """Shift everything so the lowest vertex sits on z=0."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); lo = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            ev = o.evaluated_get(dg)
            for v in ev.to_mesh().vertices:
                lo = min(lo, (o.matrix_world @ v.co).z)
            ev.to_mesh_clear()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.location.z -= lo


def ground_check():
    """Print the lowest z so we know the model stands on z=0."""
    dg = bpy.context.evaluated_depsgraph_get(); lo = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            ev = o.evaluated_get(dg)
            for v in ev.to_mesh().vertices:
                lo = min(lo, (o.matrix_world @ v.co).z)
            ev.to_mesh_clear()
    print('MIN_Z', round(lo, 5))


def turn_all(deg=0.0):
    """Rotate the finished model about world Z, then centre it on x/y (front stays -Y)."""
    Rz = Matrix.Rotation(math.radians(deg), 4, 'Z')
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in objs:
        o.matrix_world = Rz @ o.matrix_world
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        ev = o.evaluated_get(dg); m = ev.to_mesh()
        for v in m.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    c = (lo + hi) / 2
    for o in objs:
        o.location.x -= c.x; o.location.y -= c.y
    print('BBOX', [round(v, 4) for v in (hi - lo)])


# ---- end helpers ----

# Motorcycle (no student drawing in the folder: a generic model). A classic air-cooled parallel-twin standard in
# the mural's palette: red tank and fenders, black tube frame, polished engine with finned cylinders, chrome
# exhausts and spoked wheels, walnut leather seat. Side profile to the front (-Y), front wheel at -X. ~2.1 m long.
RED = kit.mat('red', rough=0.3, name='paint_red')
CREAM = kit.mat('cream', rough=0.35, name='paint_cream')
FRAME = kit.mat('black', rough=0.4, name='frame')
RUBBER = kit.mat('rubber', rough=0.85, name='tyre')
CHROME = kit.mat('chrome', rough=0.18, metal=1.0, name='chrome')
ALLOY = kit.mat('steel', rough=0.38, metal=0.85, name='alloy')
DARK = kit.mat('gunmetal', rough=0.4, metal=0.8, name='dark_metal')
LEATHER = kit.mat('walnut', rough=0.65, name='leather')
GRIPS = kit.mat('rubber', rough=0.75, name='grip')
LENS = kit.mat('#fff3d6', rough=0.1, emit=0.6, name='headlamp')
TAIL = kit.mat('cardinal', rough=0.2, emit=0.8, name='taillamp')
GAUGE = kit.mat('cream', rough=0.4, name='gauge_face')
BRASS = kit.mat('brass', rough=0.3, metal=0.9, name='brass')

XF, XR = -0.71, 0.71          # axle positions
RO = 0.320                    # tyre outer radius
Y = Vector((0, 1, 0))


def seg(p, q, r, mat, name='seg', verts=16):
    p, q = Vector(p), Vector(q); d = q - p
    o = kit.cyl(r, d.length, at=(p + q) / 2, material=mat, verts=verts, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def pipe(pts, r, mat, name='pipe', verts=16):
    """Straight tube runs with ball joints at the bends (frame tubes)."""
    pts = [Vector(p) for p in pts]
    for a, b in zip(pts, pts[1:]):
        seg(a, b, r, mat, name, verts)
    for p in pts[1:-1]:
        kit.sphere(r, at=p, material=mat, segs=10, rings=6, name=name + '_joint')


def mirror_y(fn):
    for s in (-1, 1):
        fn(s)


# ---------------------------------------------------------------- wheels
def wheel(xc, tyre_r, hub_w, rear):
    zc = RO
    kit.torus(RO - tyre_r, tyre_r, at=(xc, 0, zc), rot=(90, 0, 0), material=RUBBER, major=60, minor=12, name='tyre')
    # tread: staggered blocks on the crown
    n = 54
    for k in range(n):
        a = TAU * k / n
        for s in (-1, 1):
            if (k % 2 == 0) != (s > 0):
                continue
            b = kit.box((0.016, tyre_r * 0.7, 0.005), material=RUBBER, name='tread')
            rr = RO - 0.0018
            b.location = (xc + rr * math.cos(a), s * tyre_r * 0.32, zc + rr * math.sin(a))
            b.rotation_euler = (0, -a + math.pi / 2, math.radians(s * 18))
    # rim: a chrome channel
    prof = [(0.218, -0.026), (0.226, -0.028), (0.236, -0.027), (0.240, -0.020), (0.232, -0.012), (0.232, 0.012),
            (0.240, 0.020), (0.236, 0.027), (0.226, 0.028), (0.218, 0.026), (0.218, -0.026)]
    kit.lathe(prof, at=(xc, 0, zc), rot=(90, 0, 0), material=CHROME, steps=56, name='rim')
    # hub with its brake drum and cooling fins
    hp = [(0, -hub_w / 2), (0.040, -hub_w / 2), (0.050, -hub_w / 2 + 0.006), (0.050, -hub_w / 2 + 0.014),
          (0.034, -hub_w / 2 + 0.020), (0.034, hub_w / 2 - 0.045), (0.085, hub_w / 2 - 0.040),
          (0.088, hub_w / 2 - 0.010), (0.080, hub_w / 2), (0, hub_w / 2)]
    kit.lathe(hp, at=(xc, 0, zc), rot=(90, 0, 0), material=ALLOY, steps=48, name='hub')
    for k in range(4):
        kit.cyl(0.091, 0.003, at=(xc, hub_w / 2 - 0.036 + k * 0.008, zc), rot=(90, 0, 0), material=ALLOY, verts=32,
                name='drum_fin')
    kit.cyl(0.012, hub_w + 0.06, at=(xc, 0, zc), rot=(90, 0, 0), material=CHROME, verts=16, name='axle')
    for s in (-1, 1):
        kit.cyl(0.018, 0.012, at=(xc, s * (hub_w / 2 + 0.035), zc), rot=(90, 0, 0), material=CHROME, verts=6,
                name='axle_nut')
    # 36 spokes, cross-laced between the two hub flanges and the rim
    for k in range(36):
        s = 1 if k % 2 else -1
        a = TAU * k / 36
        fl = Vector((xc + 0.044 * math.cos(a), s * (hub_w / 2 - 0.010) * (0.55 if s > 0 else 1.0), zc + 0.044 * math.sin(a)))
        b = a + s * math.radians(24) * (1 if (k // 2) % 2 else -1)
        rm = Vector((xc + 0.221 * math.cos(b), s * 0.006, zc + 0.221 * math.sin(b)))
        seg(fl, rm, 0.0019, CHROME, 'spoke', 6)


wheel(XF, 0.048, 0.10, False)
wheel(XR, 0.056, 0.12, True)

# ---------------------------------------------------------------- front end: fork, clamps, bars, lamp, gauges
RAKE = math.radians(27)
up = Vector((math.sin(RAKE), 0, math.cos(RAKE)))       # along the fork, upward and back
fwd = Vector((-math.cos(RAKE), 0, math.sin(RAKE)))     # perpendicular, forward
axle = Vector((XF, 0, RO))
FORK_Y = 0.088
lower_clamp = axle + up * 0.42
top_clamp = axle + up * 0.56
for s in (-1, 1):
    oy = Vector((0, s * FORK_Y, 0))
    seg(axle + oy + up * 0.02, axle + oy + up * 0.26, 0.022, ALLOY, 'fork_lower', 20)
    seg(axle + oy + up * 0.24, top_clamp + oy + up * 0.02, 0.0175, CHROME, 'stanchion', 20)
    seg(axle + oy + up * 0.25, axle + oy + up * 0.33, 0.026, FRAME, 'gaiter', 20)
    kit.cyl(0.020, 0.012, at=top_clamp + oy + up * 0.026, rot=None, material=CHROME, verts=6, name='fork_cap')
for c in (lower_clamp, top_clamp):
    o = kit.box((0.07, 2 * FORK_Y + 0.05, 0.022), at=c - fwd * 0.012, material=ALLOY, bevel=0.006, segments=2,
                name='triple_clamp')
    o.rotation_euler = (0, RAKE, 0)
head = (lower_clamp + top_clamp) / 2 - fwd * 0.045            # steering head
seg(head - up * 0.09, head + up * 0.08, 0.030, FRAME, 'head_tube', 20)
# handlebars
bar_c = top_clamp + up * 0.035 - fwd * 0.01
for s in (-1, 1):
    seg(bar_c + Vector((0, s * 0.035, 0)), bar_c + Vector((0, s * 0.035, 0.05)), 0.010, CHROME, 'riser', 12)
bar_pts = [(bar_c.x + 0.04, -0.37, bar_c.z + 0.085), (bar_c.x + 0.01, -0.28, bar_c.z + 0.075),
           (bar_c.x - 0.03, -0.14, bar_c.z + 0.055), (bar_c.x - 0.03, 0.0, bar_c.z + 0.052),
           (bar_c.x - 0.03, 0.14, bar_c.z + 0.055), (bar_c.x + 0.01, 0.28, bar_c.z + 0.075),
           (bar_c.x + 0.04, 0.37, bar_c.z + 0.085)]
tube_lo(catmull(bar_pts, 6), 0.011, CHROME, 12, name='handlebar')
for s in (-1, 1):
    g0 = Vector((bar_c.x + 0.025, s * 0.30, bar_c.z + 0.079)); g1 = Vector((bar_c.x + 0.042, s * 0.385, bar_c.z + 0.086))
    seg(g0, g1, 0.0165, GRIPS, 'grip', 16)
    for k in range(4):
        kit.torus(0.0168, 0.0018, at=g0.lerp(g1, 0.2 + k * 0.2), rot=(90, 0, 0), material=GRIPS, major=12, minor=4,
                  name='grip_ring')
    # lever + its perch
    pc = Vector((bar_c.x + 0.012, s * 0.27, bar_c.z + 0.074))
    kit.box((0.03, 0.025, 0.025), at=pc, material=ALLOY, bevel=0.004, name='perch')
    tube_lo(catmull([pc + Vector((-0.02, 0, 0)), pc + Vector((-0.06, s * 0.06, 0.002)),
                     pc + Vector((-0.06, s * 0.13, -0.004))], 4), 0.0045, ALLOY, 8, name='lever')
    # round mirror on a stalk
    m0 = pc + Vector((0.005, s * 0.0, 0.012)); m1 = m0 + Vector((0.04, s * 0.06, 0.16))
    seg(m0, m1, 0.005, CHROME, 'mirror_stalk', 10)
    kit.lathe([(0, -0.008), (0.040, -0.008), (0.045, -0.002), (0.042, 0.006), (0, 0.010)], at=m1 + Vector((0.005, 0, 0.03)),
              rot=(0, 90, 0), material=CHROME, steps=32, name='mirror')
    kit.cyl(0.039, 0.002, at=m1 + Vector((-0.005, 0, 0.03)), rot=(0, 90, 0), material=kit.mat('#9fb4bd', rough=0.05, metal=0.9,
            name='mirror_glass'), verts=32, name='mirror_glass')
# gauges on the top clamp
for s in (-1, 1):
    gc = top_clamp + Vector((0.035, s * 0.055, 0.06))
    kit.lathe([(0, -0.03), (0.036, -0.03), (0.040, 0.0), (0.040, 0.012), (0.036, 0.016), (0, 0.016)], at=gc,
              rot=(0, -20, 0), material=CHROME, steps=40, name='gauge_bezel')
    kit.cyl(0.033, 0.004, at=gc + Vector((-0.0055, 0, 0.015)), rot=(0, -20, 0), material=GAUGE, verts=32,
            name='gauge_face')
    nd = kit.box((0.002, 0.024, 0.002), at=gc + Vector((-0.006, s * 0.006, 0.019)), material=FRAME, name='needle')
    nd.rotation_euler = (0, math.radians(-20), math.radians(35 * s))
# headlamp: chrome bucket, glass, ears to the fork
hl = lower_clamp + fwd * 0.10 - up * 0.02
kit.lathe([(0, 0.06), (0.040, 0.058), (0.075, 0.035), (0.088, 0.005), (0.092, 0.0), (0.090, -0.012), (0, -0.012)],
          at=hl, rot=(0, -90, 0), material=CHROME, steps=48, name='lamp_bucket')
kit.lathe([(0, -0.012), (0.082, -0.012), (0.070, -0.022), (0.040, -0.028), (0, -0.030)], at=hl, rot=(0, -90, 0),
          material=LENS, steps=48, name='lamp_glass')
for s in (-1, 1):
    seg(hl + Vector((0.02, s * 0.06, 0.0)), hl + Vector((0.075, s * FORK_Y, 0.035)), 0.009, FRAME, 'lamp_ear', 12)

# ---------------------------------------------------------------- frame
Hb, Ht = head - up * 0.08, head + up * 0.07
S = Vector((0.13, 0, 0.74))       # seat junction
P = Vector((0.15, 0, 0.42))       # swingarm pivot
R = Vector((0.66, 0, 0.73))       # rear of the seat rails
pipe([Ht, Vector((-0.20, 0, 0.80)), S], 0.019, FRAME, 'top_tube')
for s in (-1, 1):
    w = Vector((0, s * 0.075, 0))
    pipe([Hb, Vector((-0.36, s * 0.06, 0.44)), Vector((-0.30, s * 0.075, 0.20)) , Vector((0.08, s * 0.075, 0.19)),
          P + w + Vector((0, 0, -0.02)), S + w * 0.6], 0.017, FRAME, 'cradle')
    pipe([S + w * 0.6, R + w * 1.2], 0.015, FRAME, 'seat_rail')
    pipe([P + w + Vector((0.02, 0, 0.02)), Vector((0.50, s * 0.09, 0.70))], 0.014, FRAME, 'strut')
# swingarm, both sides, with the axle plates
for s in (-1, 1):
    w = Vector((0, s * 0.105, 0))
    seg(P + w, Vector((XR, s * 0.105, RO)), 0.020, FRAME, 'swingarm', 16)
    kit.box((0.07, 0.012, 0.045), at=(XR - 0.01, s * 0.105, RO), material=FRAME, bevel=0.004, name='axle_plate')
seg(P + Vector((0, -0.13, 0)), P + Vector((0, 0.13, 0)), 0.022, FRAME, 'pivot', 16)
# rear shocks: chrome springs over black bodies
for s in (-1, 1):
    lo, hi = Vector((XR - 0.08, s * 0.118, RO + 0.04)), Vector((0.57, s * 0.105, 0.715))
    d = hi - lo
    seg(lo, hi, 0.016, FRAME, 'damper', 16)
    for e in (lo, hi):
        kit.cyl(0.018, 0.030, at=e, rot=(90, 0, 0), material=CHROME, verts=16, name='shock_eye')
    q = d.to_track_quat('Z', 'Y')
    pts = []
    for t in np.linspace(0, 1, 90):
        a = t * TAU * 9
        v = Vector((0.026 * math.cos(a), 0.026 * math.sin(a), 0.035 + t * (d.length - 0.09)))
        pts.append(tuple(lo + q @ v))
    tube_lo(pts, 0.0045, CHROME, 6, name='spring')

# ---------------------------------------------------------------- engine: parallel twin, finned barrels
EX = -0.10
kit.box((0.36, 0.22, 0.20), at=(EX + 0.02, 0, 0.32), material=ALLOY, bevel=0.035, segments=3, name='crankcase')
# primary cover (left) and timing cover (right)
kit.lathe([(0, 0), (0.090, 0), (0.098, 0.012), (0.095, 0.030), (0, 0.034)], at=(EX + 0.07, -0.110, 0.31),
          rot=(90, 0, 0), material=CHROME, steps=48, name='primary_cover')
kit.lathe([(0, 0), (0.065, 0), (0.070, 0.010), (0.066, 0.024), (0, 0.027)], at=(EX - 0.06, 0.110, 0.33),
          rot=(-90, 0, 0), material=CHROME, steps=40, name='timing_cover')
for s, x, z, n, rr in ((-1, EX + 0.07, 0.31, 8, 0.082), (1, EX - 0.06, 0.33, 6, 0.056)):
    for k in range(n):
        a = TAU * k / n
        kit.cyl(0.006, 0.006, at=(x + rr * math.cos(a), s * (0.110 + 0.031), z + rr * math.sin(a)), rot=(90, 0, 0),
                material=DARK, verts=6, name='cover_screw')
# barrels inclined forward, square fins, then the head and rocker box
tilt = math.radians(14)
ax = Vector((-math.sin(tilt), 0, math.cos(tilt)))
base = Vector((EX - 0.01, 0, 0.41))
for k in range(9):
    c = base + ax * (0.025 + k * 0.016)
    w = 0.150 if k < 7 else 0.165
    kit.box((w - (0.004 if k % 2 else 0), 0.205, 0.0065), at=c, rot=(0, -math.degrees(tilt), 0), material=ALLOY,
            bevel=0.0025, name='fin')
seg(base, base + ax * 0.16, 0.050, DARK, 'barrel_core', 24)
for s in (-1, 1):
    seg(base + Vector((0, s * 0.048, 0)), base + ax * 0.165 + Vector((0, s * 0.048, 0)), 0.046, DARK, 'bore', 24)
hc = base + ax * 0.185
kit.box((0.17, 0.215, 0.05), at=hc, rot=(0, -math.degrees(tilt), 0), material=ALLOY, bevel=0.012, segments=2,
        name='head')
kit.box((0.13, 0.19, 0.035), at=hc + ax * 0.04, rot=(0, -math.degrees(tilt), 0), material=CHROME, bevel=0.012,
        segments=3, name='rocker_cover')
for s in (-1, 1):
    seg(hc + ax * 0.005 + Vector((0, s * 0.108, 0)), hc + ax * 0.005 + Vector((0, s * 0.125, 0)), 0.012, DARK,
        'spark_plug', 12)
    kit.cyl(0.005, 0.03, at=hc + ax * 0.005 + Vector((0, s * 0.14, 0)), rot=(90, 0, 0), material=FRAME, verts=8,
            name='plug_cap')
# carburettors with bell-mouth filters, behind the head
for s in (-1, 1):
    c0 = hc + Vector((0.08, s * 0.048, -0.025))
    seg(c0, c0 + Vector((0.07, 0, -0.01)), 0.022, ALLOY, 'carb', 16)
    kit.lathe([(0, 0), (0.026, 0), (0.034, 0.02), (0.034, 0.045), (0.030, 0.05), (0, 0.05)],
              at=c0 + Vector((0.07, 0, -0.01)), rot=(0, 90, 0), material=FRAME, steps=32, name='air_filter')
# gearbox lid and kickstart lever, footpegs and pedals
seg(Vector((0.05, 0.11, 0.30)), Vector((0.05, 0.16, 0.30)), 0.012, ALLOY, 'kick_shaft', 12)
seg(Vector((0.05, 0.16, 0.30)), Vector((0.18, 0.165, 0.36)), 0.009, CHROME, 'kick_lever', 12)
kit.cyl(0.010, 0.04, at=(0.18, 0.18, 0.36), rot=(90, 0, 0), material=GRIPS, verts=12, name='kick_pad')
for s in (-1, 1):
    seg(Vector((0.13, s * 0.09, 0.27)), Vector((0.13, s * 0.21, 0.27)), 0.017, GRIPS, 'footpeg', 16)
seg(Vector((0.10, -0.12, 0.30)), Vector((-0.03, -0.15, 0.25)), 0.007, CHROME, 'shifter', 10)
seg(Vector((0.10, 0.12, 0.28)), Vector((-0.02, 0.15, 0.22)), 0.007, CHROME, 'brake_pedal', 10)
# side stand, folded up
seg(Vector((0.02, -0.13, 0.20)), Vector((0.30, -0.15, 0.17)), 0.010, FRAME, 'side_stand', 12)

# exhausts: header pipes round the front of the engine into long chrome silencers
for s in (-1, 1):
    port = hc + fwd.normalized() * 0.0 + Vector((-0.075, s * 0.048, -0.01))
    pts = [port, port + Vector((-0.06, s * 0.012, -0.03)), Vector((-0.30, s * 0.10, 0.40)),
           Vector((-0.30, s * 0.135, 0.24)), Vector((-0.18, s * 0.155, 0.17)), Vector((0.10, s * 0.165, 0.185))]
    tube_lo(catmull(pts, 7), 0.020, CHROME, 14, name='header')
    m0, m1 = Vector((0.08, s * 0.165, 0.185)), Vector((0.66, s * 0.17, 0.28))
    d = m1 - m0
    mf = kit.lathe([(0, 0), (0.021, 0), (0.030, 0.05), (0.042, 0.13), (0.044, d.length - 0.08),
                    (0.040, d.length - 0.02), (0.030, d.length), (0, d.length)], material=CHROME, steps=36,
                   name='silencer')
    mf.matrix_world = Matrix.Translation(m0) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    kit.cyl(0.024, 0.006, at=m1 + d.normalized() * 0.002, material=DARK, verts=24,
            name='tailpipe').rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    seg(Vector((0.42, s * 0.10, 0.36)), Vector((0.42, s * 0.16, 0.24)), 0.007, CHROME, 'silencer_hanger', 10)

# chain, sprockets and chain guard (left side)
CY = -0.085
fs, rs = Vector((0.07, CY, 0.30)), Vector((XR, CY, RO))
kit.cyl(0.045, 0.010, at=fs, rot=(90, 0, 0), material=DARK, verts=24, name='front_sprocket')
rsp = kit.cyl(0.105, 0.008, at=rs, rot=(90, 0, 0), material=DARK, verts=48, name='rear_sprocket')
for k in range(42):
    a = TAU * k / 42
    kit.box((0.010, 0.008, 0.012), at=(rs.x + 0.108 * math.cos(a), CY, rs.z + 0.108 * math.sin(a)),
            rot=(0, -math.degrees(a), 0), material=DARK, name='sprocket_tooth')
for k in range(6):
    a = TAU * k / 6
    cut(rsp, kit.cyl(0.022, 0.03, at=(rs.x + 0.062 * math.cos(a), CY, rs.z + 0.062 * math.sin(a)), rot=(90, 0, 0),
                     verts=20))
d = rs - fs; L_ = d.length; ang = math.atan2(d.z, d.x)
chain = []
for k in range(40):   # stadium-shaped loop round both sprockets
    a = math.pi / 2 + math.pi * k / 39
    chain.append(fs + Vector((0.048 * math.cos(a + ang), 0, 0.048 * math.sin(a + ang))))
for k in range(40):
    a = -math.pi / 2 + math.pi * k / 39
    chain.append(rs + Vector((0.111 * math.cos(a + ang), 0, 0.111 * math.sin(a + ang))))
tube_lo(chain, 0.0055, DARK, 6, closed=True, name='chain')
cg = [fs + Vector((0.02, CY - fs.y - 0.008, 0.06)), rs + Vector((-0.10, CY - rs.y - 0.008, 0.125))]
seg(cg[0], cg[1], 0.012, FRAME, 'chain_guard', 12)

# ---------------------------------------------------------------- tank: lofted teardrop, knee pads, filler cap
def tank_ring(x, hw, top, bot, n=28, sq=2.6):
    pts = []
    for i in range(n):
        t = TAU * i / n
        c, s_ = math.cos(t), math.sin(t)
        y = hw * math.copysign(abs(c) ** (2 / sq), c)
        zz = (abs(s_) ** (2 / sq))
        z = (bot + top) / 2 + (top - bot) / 2 * math.copysign(zz, s_)
        if s_ < 0:
            y *= 0.82 + 0.18 * (1 - zz)      # tuck in toward the bottom, over the frame
        pts.append((x, y, z))
    return pts


rows = []
X0t, X1t = -0.40, 0.10
for k in range(18):
    t = k / 17
    x = X0t + (X1t - X0t) * t
    hw = 0.06 + 0.095 * math.sin(math.pi * min(1, t * 1.35) * 0.5 + 0.0) * (1 - 0.35 * t)
    end = min(1.0, t / 0.08, (1 - t) / 0.10)
    endf = math.sqrt(max(0.05, end))
    top = 0.80 + (0.17 - 0.07 * t) * endf
    bot = 0.745 + 0.02 * t
    rows.append(tank_ring(x, hw * endf, top, bot))
tank = loft(rows, name='tank', material=RED, smooth=60)
for o in [tank]:
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
kit.cyl(0.030, 0.012, at=(-0.20, 0, 0.965), rot=(0, -6, 0), material=CHROME, bevel=0.003, verts=32, name='filler_cap')
kit.cyl(0.012, 0.010, at=(-0.20, 0, 0.975), material=CHROME, verts=16, name='filler_knob')
# cream flash and brass emblem on each side, projected onto the tank
bpy.context.view_layer.update()


def decal(cx, cz, w, h, side, mat, off, name, r=0.01):
    bm = bmesh.new()
    pts = rrect(w, h, r, 3)
    ring = [bm.verts.new((cx + x, side * 0.3, cz + z)) for x, z in pts]
    f = bm.faces.new(ring if side < 0 else list(reversed(ring)))
    bmesh.ops.triangulate(bm, faces=[f])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    ev = tank.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for v in bm.verts:
        ok, loc, nrm, _ = ev.closest_point_on_mesh(Vector((v.co.x, side * 0.0, v.co.z)) + Vector((0, side * 0.2, 0)))
        v.co = loc + nrm * off
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    so = o.modifiers.new('solid', 'SOLIDIFY'); so.thickness = 0.0025; so.offset = 1.0
    for p in o.data.polygons:
        p.use_smooth = True
    return o


for s in (-1, 1):
    decal(-0.14, 0.86, 0.30, 0.045, s, CREAM, 0.0004, 'flash', 0.02)
    decal(-0.18, 0.86, 0.075, 0.075, s, BRASS, 0.0028, 'emblem', 0.036)
    decal(0.03, 0.80, 0.09, 0.065, s, GRIPS, 0.0004, 'knee_pad', 0.02)

# ---------------------------------------------------------------- seat
srows = []
X0s, X1s = 0.06, 0.64
for k in range(16):
    t = k / 15
    x = X0s + (X1s - X0s) * t
    end = min(1.0, t / 0.10, (1 - t) / 0.08)
    endf = math.sqrt(max(0.06, end))
    hw = (0.10 + 0.035 * min(1, t * 2.5)) * endf
    top = 0.80 + 0.075 * endf - 0.012 * t
    srows.append([(x, y, z) for (x, y, z) in tank_ring(x, hw, top, 0.755, n=28, sq=3.2)])
seat = loft(srows, name='seat', material=LEATHER, smooth=60)
seat.modifiers.new('sub', 'SUBSURF').levels = 1
# seat strap and piping
strap = []
for i in range(25):
    t = math.pi * i / 24
    strap.append((0.30, -0.142 * math.cos(t), 0.79 + 0.092 * math.sin(t) ** 0.6))
tube_lo(strap, 0.0045, FRAME, 6, name='strap')
# chrome grab rail round the back of the seat
tube_lo(catmull([(0.42, -0.12, 0.79), (0.62, -0.13, 0.80), (0.70, 0.0, 0.81), (0.62, 0.13, 0.80),
                 (0.42, 0.12, 0.79)], 6), 0.009, CHROME, 10, name='grab_rail')

# ---------------------------------------------------------------- oil tank / battery box under the seat
kit.box((0.25, 0.20, 0.17), at=(0.33, 0, 0.615), material=FRAME, bevel=0.03, segments=3, name='oil_tank')
for s in (-1, 1):
    kit.extrude(rrect(0.20, 0.12, 0.05, 8), 0.006, at=(0.33, s * 0.100, 0.615), rot=(-90 * s, 0, 0), material=RED,
                bevel=0.002, name='side_cover')
    kit.extrude(rrect(0.13, 0.016, 0.008, 4), 0.002, at=(0.33, s * 0.106, 0.615), rot=(-90 * s, 0, 0), material=CREAM,
                name='side_stripe')
kit.cyl(0.022, 0.014, at=(0.24, 0.06, 0.705), material=CHROME, bevel=0.003, verts=24, name='oil_cap')

# ---------------------------------------------------------------- fenders, tail lamp
def fender(xc, a0, a1, rad, wid, name, mat):
    path = [Vector((xc + rad * math.cos(a), 0, RO + rad * math.sin(a))) for a in np.linspace(a0, a1, 40)]
    prof = []
    for i in range(9):
        y = -wid / 2 + wid * i / 8
        prof.append((-0.022 * (2 * y / wid) ** 2, y))
    for i in range(8, -1, -1):
        y = -wid / 2 + wid * i / 8
        prof.append((-0.022 * (2 * y / wid) ** 2 - 0.004, y))
    bm = bmesh.new()
    P = path; N = len(P); rings = []
    for i in range(N):
        a = P[max(i - 1, 0)]; b = P[min(i + 1, N - 1)]
        t = (b - a).normalized(); n = Vector((-t.z, 0, t.x))
        if n.dot(P[i] - Vector((xc, 0, RO))) < 0:
            n = -n
        rings.append([bm.verts.new(P[i] - n * pn + Vector((0, py, 0))) for pn, py in prof])
    M = len(prof)
    for i in range(N - 1):
        for k in range(M):
            l = (k + 1) % M
            bm.faces.new((rings[i][k], rings[i][l], rings[i + 1][l], rings[i + 1][k]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    return link(name, bm, mat, 50)


fender(XF, math.radians(28), math.radians(168), RO + 0.035, 0.13, 'front_fender', RED)
for s in (-1, 1):   # fender stays
    seg(Vector((XF - 0.20, s * 0.068, RO + 0.26)), axle + Vector((-0.01, s * FORK_Y, 0.09)), 0.006, CHROME, 'stay', 10)
fender(XR, math.radians(5), math.radians(118), RO + 0.04, 0.15, 'rear_fender', RED)
for s in (-1, 1):
    seg(Vector((XR + 0.05, s * 0.078, RO + 0.355)), Vector((XR - 0.02, s * 0.11, RO + 0.02)), 0.007, CHROME, 'rstay', 10)
tl = Vector((XR + 0.30, 0, RO + 0.17))
kit.box((0.05, 0.10, 0.045), at=tl, material=CHROME, bevel=0.012, segments=3, name='tail_housing')
kit.box((0.012, 0.085, 0.032), at=tl + Vector((0.026, 0, 0)), material=TAIL, bevel=0.006, segments=2, name='tail_lens')

merge_by_material()
drop_to_floor()
ground_check()
kit.export('motorcycle')
