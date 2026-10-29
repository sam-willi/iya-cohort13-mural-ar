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

# Skateboard (no student drawing in the folder: a generic model). A popsicle deck in seven-ply maple with
# concave and kicked nose and tail, black grip tape, a sunset graphic underneath in the mural's palette, and
# full trucks and wheels. Shown standing on its tail like a board leaned up in a shop, grip tape to the front,
# so it reads from every side as it turns. Built flat (length along X, grip up), then stood up.
L, W, T = 0.810, 0.206, 0.0115
RE = 0.118                       # length of the rounded nose/tail
U0 = 0.250                       # where the kicks start
CONC = 0.009                     # concave depth


def half_width(u):
    d = abs(u) - (L / 2 - RE)
    if d <= 0:
        return W / 2
    return W / 2 * math.sqrt(max(0.0, 1 - (d / RE) ** 2))


def height(u, v):
    d = max(0.0, abs(u) - U0)
    ang = math.radians(20 if u > 0 else 17)
    kick = math.tan(ang) * d * d / (d + 0.035)
    fade = 1 - min(1.0, d / 0.08) * 0.6
    return kick + CONC * (v / (W / 2)) ** 2 * fade


def normal(u, v, e=1e-4):
    du = (height(u + e, v) - height(u - e, v)) / (2 * e)
    dv = (height(u, v + e) - height(u, v - e)) / (2 * e)
    return Vector((-du, -dv, 1)).normalized()


# ---- textures ----
rng = np.random.default_rng(5)
g = rng.random((256, 256)) * 0.35 + 0.08
grip_img = np.dstack([g * 0.55 + 0.05] * 3) * np.array([1.0, 0.98, 0.95])
GRIP = image_mat('grip_tape', grip_img, rough=0.95)

wood = wood_tex('#e2c08e', '#c49a62', size=512, rings=6, seed=9, figure=0.6, contrast=0.8)
img = np.repeat(np.repeat(wood, 1, 0), 2, 1)[:, :1024][:256 * 2:2]          # 256 x 1024, grain along U
img = np.array(img)
H_, W_ = img.shape[:2]
yy, xx = np.mgrid[0:H_, 0:W_]
u = xx / W_; v = yy / H_
pal = lambda c: np.array(kit.hex_rgb(c)[:3]) ** (1 / 2.2)
# retro sunset: a sun with slits in its lower half, sitting on three bands across the board (nose is u=1)
px_u, px_v = L / W_, W / H_                       # metres per pixel along / across
du_m = (u - 0.60) * L; dv_m = (v - 0.5) * W
sun = du_m ** 2 + dv_m ** 2 < 0.072 ** 2
slit = (du_m < 0.0) & (np.sin(du_m / 0.0105 * math.pi) > 0.35)
grad = np.clip((du_m + 0.072) / 0.144, 0, 1)[..., None]
sun_col = pal('#e8a33a') * (1 - grad) + pal('#f6c25a') * grad
m = sun & ~slit
img[m] = (img * 0.08 + sun_col * 0.92)[m]
for col, u0, u1 in (('#b8322a', 0.330, 0.372), ('#d9662a', 0.384, 0.418), ('#e8a33a', 0.428, 0.454)):
    mm = (u > u0) & (u < u1)
    img[mm] = img[mm] * 0.12 + pal(col) * 0.88
mm = (u > 0.312) & (u < 0.318)
img[mm] = pal('#2f7d86')
GRAPHIC = image_mat('deck_graphic', img, rough=0.45)
plies = ['#e7cc9f', '#dcc08f', '#2f7d86', '#e2c696', '#b8322a', '#dcc08f', '#e7cc9f']
ply_img = np.zeros((70, 8, 3))
for k, c in enumerate(plies):
    ply_img[k * 10:(k + 1) * 10] = pal(c)
    ply_img[k * 10] *= 0.7
PLY = image_mat('plies', ply_img, rough=0.5)

# ---- deck: rows across the board, top (grip) / bottom (graphic) / edge (plies) ----
bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
NC = 14
mid = [-(L / 2 - RE) + 2 * (L / 2 - RE) * i / 48 for i in range(49)]
ends = [(L / 2 - RE) + RE * math.sin(math.radians(a)) for a in [6.4 * k for k in range(1, 14)] + [87.5]]
us = [-u for u in reversed(ends)] + mid + ends      # rows follow the round of the nose and tail
NR = len(us) - 1
rows = []
for u in us:
    hw = max(half_width(u), 0.004)
    top, bot = [], []
    for j in range(NC + 1):
        v = -hw + 2 * hw * j / NC
        p = Vector((u, v, height(u, v)))
        top.append(bm.verts.new(p)); bot.append(bm.verts.new(p - normal(u, v) * T))
    rows.append((top, bot))


def face(vs, mat, uvs):
    f = bm.faces.new(vs); f.material_index = mat
    for lp, uv in zip(f.loops, uvs):
        lp[uvl].uv = uv
    return f


def gu(vert):   # graphic UVs: along the board, and across it by the full width
    return ((vert.co.x + L / 2) / L, (vert.co.y + W / 2) / W)


for i in range(NR):
    (t0, b0), (t1, b1) = rows[i], rows[i + 1]
    for j in range(NC):
        face([t0[j], t1[j], t1[j + 1], t0[j + 1]], 0, [(0, 0)] * 4)
        q = [b0[j], b0[j + 1], b1[j + 1], b1[j]]
        face(q, 1, [gu(x) for x in q])
    ua, ub = us[i] * 6, us[i + 1] * 6
    face([t0[NC], t1[NC], b1[NC], b0[NC]], 2, [(ua, 1), (ub, 1), (ub, 0), (ua, 0)])
    face([t0[0], b0[0], b1[0], t1[0]], 2, [(ua, 1), (ua, 0), (ub, 0), (ub, 1)])
for (tt, bb), sgn in ((rows[0], 1), (rows[-1], -1)):
    for j in range(NC):
        vs = [tt[j], tt[j + 1], bb[j + 1], bb[j]]
        face(vs if sgn < 0 else list(reversed(vs)), 2, [(j / NC, 1), ((j + 1) / NC, 1), ((j + 1) / NC, 0), (j / NC, 0)])
deck = link('deck', bm, None, 35)
for m in (GRIP, GRAPHIC, PLY):
    deck.data.materials.append(m)

# ---- trucks and wheels ----
ALU = kit.mat('steel', rough=0.35, metal=0.85, name='truck_alloy')
STEEL = kit.mat('chrome', rough=0.25, metal=1.0, name='steel')
BUSH = kit.mat('amber', rough=0.5, name='bushing')
WHEEL = kit.mat('cream', rough=0.42, name='urethane')
RISER = kit.mat('black', rough=0.6, name='riser')
BOLT = kit.mat('gunmetal', rough=0.35, metal=0.9, name='bolt')
for ut, sgn in ((0.192, 1), (-0.192, -1)):
    zb = height(ut, 0) - T            # underside of the deck at the truck
    kit.box((0.072, 0.064, 0.004), at=(ut, 0, zb - 0.002), material=RISER, bevel=0.0012, name='riser')
    kit.box((0.066, 0.058, 0.007), at=(ut, 0, zb - 0.0075), material=ALU, bevel=0.002, segments=2, name='baseplate')
    # kingpin boss angled toward the middle of the board, bushings, kingpin nut
    kp = Vector((ut - sgn * 0.010, 0, zb - 0.026))
    seg_ax = Vector((sgn * 0.6, 0, 0.8)).normalized()
    kit.cyl(0.010, 0.020, at=kp + seg_ax * 0.010, material=ALU, verts=20, name='kp_boss').rotation_euler = \
        seg_ax.to_track_quat('Z', 'Y').to_euler()
    for k, off in enumerate((-0.006, 0.010)):
        kit.cyl(0.0125, 0.010, at=kp + seg_ax * off, material=BUSH, bevel=0.002, verts=20,
                name='bushing').rotation_euler = seg_ax.to_track_quat('Z', 'Y').to_euler()
    kit.cyl(0.0042, 0.034, at=kp + seg_ax * 0.0, material=STEEL, verts=12, name='kingpin').rotation_euler = \
        seg_ax.to_track_quat('Z', 'Y').to_euler()
    kit.cyl(0.0065, 0.006, at=kp - seg_ax * 0.016, material=STEEL, verts=6, name='kp_nut').rotation_euler = \
        seg_ax.to_track_quat('Z', 'Y').to_euler()
    # hanger: a tapered body round the bushings carrying the axle housing
    za = zb - 0.040
    hang = kit.extrude([(-0.030, -0.010), (0.030, -0.010), (0.016, 0.014), (-0.016, 0.014)], 0.034,
                       at=(ut, 0.017, za + 0.002), rot=(90, 0, 0), material=ALU, bevel=0.004, segments=2, name='hanger')
    kit.cyl(0.0105, 0.150, at=(ut, 0, za), rot=(90, 0, 0), material=ALU, bevel=0.002, verts=24, name='axle_housing')
    kit.cyl(0.0040, 0.226, at=(ut, 0, za), rot=(90, 0, 0), material=STEEL, verts=12, name='axle')
    for s in (-1, 1):
        wy = s * 0.091
        kit.lathe([(0.0055, -0.016), (0.022, -0.016), (0.0265, -0.013), (0.0272, -0.004), (0.0272, 0.006),
                   (0.026, 0.013), (0.021, 0.016), (0.0055, 0.016), (0.0055, -0.016)],
                  at=(ut, wy, za), rot=(90, 0, 0), material=WHEEL, steps=48, name='wheel')
        for e in (-1, 1):
            kit.cyl(0.0110, 0.0035, at=(ut, wy + e * 0.0148, za), rot=(90, 0, 0), material=STEEL, verts=24,
                    name='bearing')
            kit.cyl(0.0050, 0.0040, at=(ut, wy + e * 0.0160, za), rot=(90, 0, 0), material=BOLT, verts=16, name='shield')
        kit.cyl(0.0068, 0.006, at=(ut, s * 0.1110, za), rot=(90, 0, 0), material=STEEL, verts=6, name='axle_nut')
        kit.cyl(0.0060, 0.0015, at=(ut, s * 0.1078, za), rot=(90, 0, 0), material=STEEL, verts=16, name='washer')
    # mounting bolts: heads on the grip, nuts under the baseplate
    for bx in (-0.027, 0.027):
        for by in (-0.0205, 0.0205):
            x = ut + bx
            kit.cyl(0.0042, 0.0012, at=(x, by, height(x, by) + 0.0003), material=BOLT, verts=16, name='bolt_head')
            kit.cyl(0.0050, 0.005, at=(x, by, zb - 0.0125), material=BOLT, verts=6, name='bolt_nut')

# ---- stand it on its tail, grip tape to the front ----
M = Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Rotation(math.radians(-90), 4, 'Y')
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        o.matrix_world = M @ o.matrix_world
turn_all(0)
merge_by_material()
drop_to_floor()
ground_check()
kit.export('skateboard')
