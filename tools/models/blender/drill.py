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

# Electric drill, after Julia Chen's isometric drawing (RV P4a).
# Chuck points -X, the "Cohort13" label faces the front (-Y). Metres, real size (~24 cm tall).
ORANGE = kit.mat('orange', rough=0.42, name='housing')
RUBBER = kit.mat('rubber', rough=0.82, name='rubber')
BLACK = kit.mat('black', rough=0.5, name='black_plastic')
GUN = kit.mat('gunmetal', rough=0.32, metal=0.9, name='gunmetal')
CHROME = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
CREAM = kit.mat('cream', rough=0.5, name='label')
INK = kit.mat('black', rough=0.45, name='ink')

LIFT = 0.0012   # rubber feet under the pack
ZC = 0.185 + LIFT  # motor axis height
R = 0.035       # barrel radius
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'


def xlathe(prof, mat, name, steps=64):
    """Lathe around the motor axis (profile given as (radius, x))."""
    return kit.lathe(prof, at=(0, 0, ZC), rot=(0, 90, 0), material=mat, steps=steps, name=name)


# ---- motor housing: barrel with a domed back ----
prof = [(0, -0.040), (0.029, -0.040), (0.0335, -0.038), (R, -0.034), (R, 0.054)]
for i in range(1, 11):
    t = i / 10 * math.pi / 2
    prof.append((R * math.cos(t), 0.054 + 0.034 * math.sin(t)))
barrel = xlathe(prof, ORANGE, 'barrel', 72)

# label pocket on the front (-Y) flank
cut(barrel, kit.extrude(rrect(0.084, 0.028, 0.004, 5), 0.02, at=(0.008, -0.0318, ZC), rot=(90, 0, 0)))
# selector-switch pocket on top
cut(barrel, kit.extrude(rrect(0.030, 0.016, 0.006, 5), 0.02, at=(0.018, 0, ZC + R - 0.0035)))
# motor vents on both flanks of the dome (the drawing doesn't show the back; real drills vent here)
for side in (-1, 1):
    for k in range(5):
        cut(barrel, kit.box((0.016, 0.02, 0.0024), at=(0.068, side * 0.036, ZC - 0.012 + k * 0.006),
                            bevel=0.0011, segments=2))

# ---- label plate, framed, with the lettering ----
kit.extrude(rrect(0.080, 0.024, 0.0032, 5), 0.0012, at=(0.008, -0.0316, ZC), rot=(90, 0, 0),
            material=CREAM, bevel=0.0004, name='plate')
fr = kit.extrude(rrect(0.080, 0.024, 0.0032, 5), 0.0008, at=(0.008, -0.0328, ZC), rot=(90, 0, 0),
                 material=INK, name='frame')
cut(fr, kit.extrude(rrect(0.075, 0.019, 0.0022, 5), 0.004, at=(0.008, -0.0318, ZC), rot=(90, 0, 0)))
txt = text_mesh('Cohort13', 0.0175, 0.0008, font=FONT, at=(0.008, -0.0332, ZC - 0.0003), material=INK,
                name='label_text')
s = min(1.0, 0.066 / txt.dimensions.x); txt.scale = (s, s, 1)

# ---- front collar and the clutch ring with its castellated tabs ----
xlathe([(0, -0.043), (0.0305, -0.043), (0.0315, -0.0415), (0.0315, -0.039), (0, -0.039)], BLACK, 'collar')
xlathe([(0, -0.062), (0.0265, -0.062), (0.0285, -0.0605), (0.0285, -0.0445), (0.0300, -0.0435), (0, -0.0435)],
       BLACK, 'clutch')
for k in range(10):
    a = TAU * k / 10 + 0.31
    tab = kit.box((0.0125, 0.0085, 0.0045), material=BLACK, bevel=0.0009, name='tab')
    tab.location = (-0.0525, 0.0295 * math.cos(a), ZC + 0.0295 * math.sin(a))
    tab.rotation_euler = (a - math.pi / 2, 0, 0)
kit.sphere(0.0018, at=(-0.0375, 0, ZC + 0.0345), scale=(1, 1, 0.5), material=CREAM, segs=16, rings=8, name='index')

# ---- keyless chuck: ribbed sleeve, nose cone, steel tip with the bit hole ----
xlathe([(0, -0.106), (0.0215, -0.106), (0.0235, -0.104), (0.0235, -0.066), (0.0215, -0.0635), (0.017, -0.0625),
        (0, -0.0625)], RUBBER, 'sleeve')
for k in range(20):
    a = TAU * k / 20
    rib = kit.box((0.034, 0.0032, 0.0028), material=RUBBER, bevel=0.0009, name='rib')
    rib.location = (-0.085, 0.0238 * math.cos(a), ZC + 0.0238 * math.sin(a))
    rib.rotation_euler = (a - math.pi / 2, 0, 0)
xlathe([(0, -0.1065), (0.0215, -0.1065), (0.0205, -0.110), (0.0165, -0.118), (0.0105, -0.125), (0, -0.125)],
       GUN, 'nose')
tip = xlathe([(0, -0.1252), (0.0068, -0.1252), (0.0062, -0.1335), (0.0055, -0.1345), (0, -0.1345)], CHROME, 'tip', 48)
cut(tip, kit.cyl(0.0031, 0.02, at=(-0.135, 0, ZC), rot=(0, 90, 0), verts=24))
for k in range(3):   # the three jaws just visible in the bore
    a = TAU * k / 3 + 0.5
    kit.box((0.006, 0.0016, 0.0016), at=(-0.1312, 0.0021 * math.cos(a), ZC + 0.0021 * math.sin(a)),
            material=GUN, name='jaw')

# ---- selector slider on top ----
kit.extrude(rrect(0.009, 0.0125, 0.0045, 6), 0.0055, at=(0.012, 0, ZC + R - 0.0045), material=BLACK,
            bevel=0.0012, segments=3, name='slider')


# ---- handle: lofted, waisted, flaring back into the underside of the barrel ----
def hsec(z, cx, a, b, back=0.0, n=40):
    pts = []
    for i in range(n):
        t = TAU * i / n
        x = cx + a * math.cos(t)
        if math.cos(t) > 0:
            x += back * math.cos(t) ** 2
        pts.append((x, b * math.sin(t), z + LIFT))
    return pts


rings = [hsec(*row) for row in [(0.045, 0.040, 0.0235, 0.0185, 0), (0.060, 0.039, 0.0230, 0.0182, 0),
                                (0.085, 0.037, 0.0212, 0.0170, 0), (0.110, 0.035, 0.0208, 0.0166, 0),
                                (0.130, 0.034, 0.0218, 0.0170, 0.002), (0.145, 0.034, 0.0232, 0.0175, 0.008),
                                (0.158, 0.035, 0.0245, 0.0180, 0.012), (0.170, 0.036, 0.0255, 0.0185, 0.017),
                                (0.185, 0.036, 0.0260, 0.0185, 0.019)]]
loft(rings, name='handle', material=ORANGE, smooth=60)
# rubber overmould on the back of the grip
grings = [hsec(z, cx + 0.0016, a, b + 0.0012) for z, cx, a, b in
          [(0.052, 0.040, 0.0240, 0.0190), (0.070, 0.0385, 0.0226, 0.0180), (0.095, 0.0362, 0.0214, 0.0173),
           (0.120, 0.0346, 0.0218, 0.0175), (0.138, 0.0342, 0.0230, 0.0180)]]
grip = loft(grings, name='grip', material=RUBBER, smooth=60)
cut(grip, kit.box((0.06, 0.08, 0.2), at=(0.006, 0, 0.09)))

# trigger housing (the bracket behind the trigger in the drawing) and the trigger
kit.extrude([(0.002, 0.124), (0.040, 0.124), (0.044, 0.170), (0.000, 0.170)], 0.034,
            at=(0, 0.017, LIFT), rot=(90, 0, 0), material=ORANGE, bevel=0.003, segments=3, name='trig_housing')
kit.extrude([(-0.010, -0.012), (0.010, -0.012), (0.010, 0.012), (-0.005, 0.012), (-0.0095, 0.007),
             (-0.011, -0.004)], 0.0145, at=(-0.002, 0.00725, 0.137 + LIFT), rot=(90, 0, 0), material=BLACK,
            bevel=0.0018, segments=3, name='trigger')
# forward/reverse button: a pill through the trigger housing, proud on both sides
kit.extrude(rrect(0.013, 0.0065, 0.00325, 6), 0.038, at=(0.022, 0.019, 0.1505 + LIFT), rot=(90, 0, 0),
            material=BLACK, bevel=0.0009, segments=2, name='fr_button')
# housing screws on the far (+Y) side
for x, dz in [(-0.024, 0.017), (-0.024, -0.019), (0.035, 0.022), (0.035, -0.022), (0.056, 0.0)]:
    beta = math.asin(dz / R)
    kit.cyl(0.0026, 0.0016, at=(x, (R + 0.0002) * math.cos(beta), ZC + (R + 0.0002) * math.sin(beta)),
            rot=(math.degrees(beta) - 90, 0, 0), material=GUN, verts=20, bevel=0.0005, name='screw')

# ---- battery pack ----
bat = kit.extrude([(-0.047, 0.0), (0.080, 0.0), (0.080, 0.052), (-0.026, 0.052), (-0.047, 0.026)], 0.084,
                  at=(0, 0.042, LIFT), rot=(90, 0, 0), material=BLACK, bevel=0.0035, segments=3, name='battery')
for side in (-1, 1):   # the long rounded grip slot in the drawing, both sides
    cut(bat, kit.extrude(rrect(0.074, 0.0075, 0.00375, 6), 0.012, at=(0.026, side * 0.0395, 0.020 + LIFT),
                         rot=(90 if side < 0 else -90, 0, 0)))
# orange foot where the handle meets the pack
kit.box((0.066, 0.052, 0.006), at=(0.040, 0, 0.0525 + LIFT), material=ORANGE, bevel=0.0025, segments=3, name='foot')
# release button on the sloped front face, with its two ridges
ang = math.atan2(0.026, 0.021)
n = Vector((-math.sin(ang), 0, math.cos(ang)))   # outward normal of the slope
d = Vector((math.cos(ang), 0, math.sin(ang)))    # up the slope
c = Vector((-0.0365, 0, 0.039 + LIFT))
kit.box((0.019, 0.024, 0.006), at=c + n * 0.001, rot=(0, -math.degrees(ang), 0), material=ORANGE,
        bevel=0.0018, segments=3, name='release')
for dd in (-0.0035, 0.0035):
    kit.box((0.0022, 0.014, 0.0014), at=c + n * 0.0044 + d * dd, rot=(0, -math.degrees(ang), 0), material=BLACK,
            bevel=0.0005, name='ridge')
# charge-level window on the back of the pack
kit.box((0.0012, 0.026, 0.006), at=(0.0802, 0, 0.030 + LIFT), material=GUN, bevel=0.0004, name='gauge')
for k in range(3):
    kit.box((0.0012, 0.0055, 0.0032), at=(0.0806, -0.008 + k * 0.008, 0.030 + LIFT),
            material=kit.mat('lamp', rough=0.3, emit=0.6, name='led'), name='led')
# rubber feet
for x in (-0.035, 0.068):
    for y in (-0.030, 0.030):
        kit.cyl(0.004, LIFT, at=(x, y, LIFT / 2), material=RUBBER, verts=16, name='foot_pad')

merge_by_material()
ground_check()
kit.export('drill')
