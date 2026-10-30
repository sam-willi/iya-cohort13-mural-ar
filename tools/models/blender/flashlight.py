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

# Flashlight, after Makeda West's isometric drawing.
# Built along +X (tail at x=0, lens at +X), then posed as the drawing reads: head tipped down, the lens shining toward
# her block-letter "13" standing below and ahead of it. Turned at the end so, from the front, the lens points
# front-right and the "13" faces front-left, the drawing's three-quarter view. Metres, ~18 cm long.
# Readability: black rubber bezel and tail cap frame the teal body, the switch sits mid-body where she drew it,
# and the lit lens throws a soft beam that fades out before it reaches the numbers.
SHELL = kit.mat('teal', rough=0.42, name='shell')
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')
BLACK = kit.mat('black', rough=0.5, name='black_plastic')
CHROME = kit.mat('#f6d8a0', rough=0.3, metal=0.8, emit=0.7, name='reflector')
GLASS = kit.mat('#fff4dc', rough=0.05, alpha=0.35, emit=0.6, name='lens')
BULB = kit.mat('lamp', rough=0.2, emit=4.0, name='bulb')
CREAM = kit.mat('cream', rough=0.45, name='slider')
STEEL = kit.mat('steel', rough=0.35, metal=0.9, name='steel')

HEAD = 0.0858
ZC = 0.0436   # the knurled ring is the widest part


def ring(x, s, r, n=8, grow=0.0):
    pts = rrect(s + grow, s + grow, r + grow / 2, n)
    return [(x, y, ZC + z) for y, z in pts]


def dense_ring(x, s, r, N, bump=0.0, every=2):
    """Uniformly resampled rounded square; every `every`-th point pushed out by `bump` (knurling)."""
    pts = resample(rrect(s, s, r, 12), N)
    out = []
    for i, (y, z) in enumerate(pts):
        py, pz = pts[i - 1]; ny, nz = pts[(i + 1) % N]
        ty, tz = ny - py, nz - pz; L = math.hypot(ty, tz)
        nyv, nzv = tz / L, -ty / L          # outward for a CCW loop
        b = bump if (i % every == 0) else 0.0
        out.append((x, y + nyv * b, ZC + z + nzv * b))
    return out


# ---- body: tapered rounded square, tail cap is black rubber ----
S_TAIL = 0.045            # the drawing tapers hard: tail about half the head end
TS_ = S_TAIL / 0.0555     # tail-cap rings were drawn for a 55.5 mm tail


def body_s(x):
    return S_TAIL + (0.080 - S_TAIL) * (x - 0.004) / (0.141 - 0.004)


tail = loft([ring(0.0, 0.049 * TS_, 0.0150 * TS_), ring(0.0016, 0.0538 * TS_, 0.0166 * TS_),
             ring(0.0045, 0.0560 * TS_, 0.0174 * TS_),
             ring(0.0098, body_s(0.0098) - 0.0002, 0.31 * body_s(0.0098)),
             ring(0.0106, body_s(0.0106) - 0.0016, 0.31 * body_s(0.0106) - 0.0008)],
            name='tail_cap', material=RUBBER, smooth=50)
xs = [0.0106, 0.0114] + [0.0114 + (0.1425 - 0.0114) * k / 16 for k in range(1, 17)]
body = loft([ring(x, body_s(x) - (0.0016 if i == 0 else 0), 0.31 * body_s(x) - (0.0008 if i == 0 else 0))
             for i, x in enumerate(xs)], name='body', material=SHELL, smooth=50)

# ---- head: square block, knurled grip ring at its back edge, rubber bezel, recessed lens ----
head = loft([ring(0.1405, 0.0846, 0.020), ring(0.1712, 0.0846, 0.020)], name='head', material=SHELL, smooth=50)
knurl = loft([dense_ring(x, 0.0856, 0.0205, 176, b, 2) for x, b in
              ((0.1400, 0.0), (0.1408, 0.0007), (0.1482, 0.0007), (0.1490, 0.0))],
             name='knurl', material=STEEL, smooth=20)
bez = loft([ring(0.1705, 0.0846, 0.020), ring(0.1805, 0.0846, 0.020), ring(0.1832, 0.0826, 0.0192),
            ring(0.1846, 0.0786, 0.0176)], name='bezel', material=RUBBER, smooth=50)
LENS = 0.0640
cut(bez, loft([ring(0.160, LENS, 0.021, 10), ring(0.192, LENS, 0.021, 10)], name='lenscut'))
cut(head, loft([ring(0.160, LENS, 0.021, 10), ring(0.192, LENS, 0.021, 10)], name='lenscut'))
# small inner lip where the glass seats
lip = loft([ring(0.1772, LENS + 0.001, 0.0215, 10), ring(0.1830, LENS + 0.001, 0.0215, 10),
            ring(0.1838, LENS - 0.001, 0.0205, 10)], name='gasket', material=RUBBER, smooth=50)
cut(lip, loft([ring(0.170, LENS - 0.005, 0.019, 10), ring(0.190, LENS - 0.005, 0.019, 10)], name='lipcut'))

# reflector: a chrome funnel from the lens opening down to the bulb
refl = []
for k in range(7):
    t = k / 6
    x = 0.1765 - 0.0145 * (t ** 0.8)
    s = LENS * (1 - t) + 0.016 * t
    r = 0.021 * (1 - t) + 0.008 * t
    refl.append(ring(x, s, r, 10))
loft(refl, name='reflector', material=CHROME, cap0=False, cap1=True, smooth=0)   # faceted, like a cut reflector
kit.sphere(0.0062, at=(0.1645, 0, ZC), scale=(1.15, 1, 1), material=BULB, segs=24, rings=12, name='bulb')
kit.cyl(0.0068, 0.004, at=(0.1615, 0, ZC), rot=(0, 90, 0), material=CHROME, verts=24, name='bulb_base')
# the glass, tinted and faintly lit (the drawing shows it switched on)
loft([ring(0.1773, LENS - 0.0005, 0.0212, 10), ring(0.1781, LENS - 0.0005, 0.0212, 10)], name='glass',
     material=GLASS, smooth=50)

# ---- slide switch on top of the body (tilted to the taper) ----
alpha = math.atan((0.080 - S_TAIL) / 2 / 0.137)
XS = 0.076
ztop = ZC + body_s(XS) / 2
Rt = Matrix.Translation((XS, 0, ztop)) @ Matrix.Rotation(-alpha, 4, 'Y') @ Matrix.Scale(1.2, 4)


def place(o):
    o.matrix_world = Rt @ o.matrix_world
    return o


pocket = place(kit.extrude(rrect(0.030, 0.0185, 0.0065, 6), 0.02, at=(0, 0, -0.0016)))
cut(body, pocket)
fr = place(kit.extrude(rrect(0.032, 0.0205, 0.0072, 6), 0.0026, at=(0, 0, -0.0016), material=BLACK, bevel=0.0007,
                       name='sw_bezel'))
cut(fr, place(kit.extrude(rrect(0.0285, 0.017, 0.0058, 6), 0.02, at=(0, 0, -0.005))))
place(kit.extrude(rrect(0.0285, 0.017, 0.0058, 6), 0.0012, at=(0, 0, -0.0016), material=RUBBER, name='sw_floor'))
place(kit.extrude(rrect(0.020, 0.0105, 0.0052, 8), 0.0016, at=(0.001, 0, -0.0006), material=CREAM, bevel=0.0005,
                  name='sw_plate'))
place(kit.sphere(0.0038, at=(-0.0035, 0, 0.0008), scale=(1, 1, 0.75), material=BLACK, segs=24, rings=12,
                 name='sw_knob'))

# ---- the beam: a soft warm cone from the lens, fading to nothing (alpha ramp in a tiny texture) ----
def beam_mat():
    n = 128
    img = bpy.data.images.new('beam_ramp', 4, n, alpha=True)
    px = np.zeros((n, 4, 4), np.float32)
    t = np.linspace(0, 1, n)[:, None]
    px[..., 0], px[..., 1], px[..., 2] = 1.0, 0.86, 0.55
    px[..., 3] = 0.30 * (1 - t) ** 1.8 * np.clip(t / 0.06, 0, 1) ** 0.5   # row 0 = lens end
    img.pixels.foreach_set(px.ravel()); img.pack()
    m = bpy.data.materials.new('beam'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 1.0
    b.inputs['Emission Color'].default_value = kit.hex_rgb('#ffe2a8')
    b.inputs['Emission Strength'].default_value = 1.2
    tx = m.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    m.node_tree.links.new(tx.outputs['Color'], b.inputs['Base Color'])
    m.node_tree.links.new(tx.outputs['Alpha'], b.inputs['Alpha'])
    m.surface_render_method = 'BLENDED'
    return m


BEAM_L = 0.09
bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
K, NR = 48, 10
rows = []
for i in range(NR + 1):
    t = i / NR
    x = 0.1782 + BEAM_L * t
    s_ = (LENS - 0.002) + 2 * math.tan(math.radians(17)) * BEAM_L * t      # widens ~17 deg each side
    r_ = 0.021 + (s_ / 2 - 0.021) * min(1, t * 1.6)                        # rounded square -> round
    pts = resample(rrect(s_, s_, r_, 12), K)
    rows.append([bm.verts.new((x, y, ZC + z)) for y, z in pts])
for i in range(NR):
    for k in range(K):
        f = bm.faces.new((rows[i][k], rows[i][(k + 1) % K], rows[i + 1][(k + 1) % K], rows[i + 1][k]))
        for lp, (uu, vv) in zip(f.loops, ((k / K, 1 - i / NR), ((k + 1) / K, 1 - i / NR),
                                          ((k + 1) / K, 1 - (i + 1) / NR), (k / K, 1 - (i + 1) / NR))):
            lp[uvl].uv = (uu, min(max(vv, 0.004), 0.996))
link('beam', bm, beam_mat(), smooth=180)

# ---- pose: tip the head down, as the drawing reads ----
TILT = 24
P0 = Vector((0.092, 0, ZC))
M = Matrix.Translation(P0) @ Matrix.Rotation(math.radians(TILT), 4, 'Y') @ Matrix.Translation(-P0)
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    o.matrix_world = M @ o.matrix_world
bpy.context.view_layer.update()
LENS_C = M @ Vector((0.1781, 0, ZC))
AXIS = (M.to_3x3() @ Vector((1, 0, 0))).normalized()

# ---- Makeda's "13": square-cut block numerals standing upright, reading along the flashlight's line,
# faces turned to the side (front-left once turned). A "1" with a short flag, a "3" of three bars on a stem,
# the middle bar set in from the left. Proportions measured off her drawing (stroke ~1/8 of the height). ----
NUM = kit.mat('orange', rough=0.45, name='numerals')   # pencil in the drawing; the teal's complement from the palette
H13 = 0.084; T13 = H13 / 8
one = [(T13, 0), (2.05 * T13, 0), (2.05 * T13, H13), (0, H13), (0, H13 - 1.25 * T13), (T13, H13 - 1.25 * T13)]
W3, TB, TS, IN = 4.2 * T13, 1.15 * T13, 1.1 * T13, 1.0 * T13
HM = H13 / 2
three = [(0, 0), (W3, 0), (W3, H13), (0, H13), (0, H13 - TB), (W3 - TS, H13 - TB), (W3 - TS, HM + TB / 2),
         (IN, HM + TB / 2), (IN, HM - TB / 2), (W3 - TS, HM - TB / 2), (W3 - TS, TB), (0, TB)]
D13 = 1.1 * T13
X13 = LENS_C.x + 0.050                       # the "1"'s flag starts just ahead of the lens
Z13 = LENS_C.z - 0.078 - H13 / 2             # numerals' foot, below the beam's line
for poly, dx, nm in ((one, 0.0, 'num_1'), (three, 2.05 * T13 + 2.25 * T13, 'num_3')):
    kit.extrude(poly, D13, at=(X13 + dx, D13 / 2, Z13), rot=(90, 0, 0), material=NUM, bevel=0.0012, segments=2, name=nm)

# stand the lowest point on z=0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); zlo = 1e9
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    ev = o.evaluated_get(dg)
    for v in ev.to_mesh().vertices:
        zlo = min(zlo, (o.matrix_world @ v.co).z)
    ev.to_mesh_clear()
print('ZLO', zlo)
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    o.matrix_world = Matrix.Translation((0, 0, -zlo)) @ o.matrix_world
bpy.context.view_layer.update()

turn_all(-45)
merge_by_material()
ground_check()
kit.export('flashlight')
