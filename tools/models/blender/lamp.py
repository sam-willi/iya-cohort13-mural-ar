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

# Floor lamp, after Renzo Ogami's isometric drawing: four soft-cornered square blocks stacked with light
# spilling out of the gaps between them, a lettered band round the tall top block ("DEGREE IS" / "IN DISRUPTION"),
# and a big bulb standing in a round socket on top. Built axis-aligned, then turned 45 degrees so a corner faces
# the front like the drawing. ~1.1 m tall.
OAK = image_mat('oak_grain', wood_tex('#bd8a55', '#8a5a33', size=512, rings=14, seed=4), rough=0.6)
BAND = kit.mat('cream', rough=0.55, name='band')
INK = kit.mat('walnut', rough=0.5, name='letters')
GLOW = kit.mat('lamp', rough=0.5, emit=3.0, name='glow')
BRASS = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
BULB = kit.mat('#ffe6b0', rough=0.25, emit=1.8, name='bulb')
DIN = '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf'

S = 0.30          # block side
BEV = 0.034       # soft, pillowy edges
GAP = 0.022
blocks = [(0.0, 0.18), (0.202, 0.382), (0.404, 0.584), (0.606, 0.852)]

for i, (z0, z1) in enumerate(blocks):
    b = kit.box((S, S, z1 - z0), at=(0, 0, (z0 + z1) / 2), name=f'block{i}')
    box_uv(b, grain='x', scale=2.4)
    b.data.materials.append(OAK)
    kit.finish(b, None, bevel=BEV, segments=4)
    if i < 3:   # the glowing core that shows in the gap above this block
        kit.extrude(rrect(S - 0.05, S - 0.05, 0.03, 6), GAP + 0.03, at=(0, 0, z1 - 0.015), material=GLOW,
                    name='glow')

# ---- the lettered band round the top block ----
ztop = blocks[-1][1]
bz0, bz1 = ztop - 0.112, ztop - 0.046
kit.extrude(rrect(S + 0.004, S + 0.004, BEV + 0.002, 10), bz1 - bz0, at=(0, 0, bz0), material=BAND, bevel=0.0008,
            name='band')
zc = (bz0 + bz1) / 2
face = S / 2 + 0.002


def letters(s, rotz, pos, width):
    t = text_mesh(s, 0.06, 0.0016, font=DIN, at=pos, rot=(90, 0, rotz), material=INK, name='letters')
    t.scale = (width / t.dimensions.x, 0.046 / t.dimensions.y, 1)
    return t


letters('DEGREE IS', -90, (-face - 0.0008, 0, zc), 0.215)        # left face in the drawing
letters('IN DISRUPTION', 0, (0, -face - 0.0008, zc), 0.250)      # right face in the drawing
# the band carries on round the back, so the phrase comes round again as the lamp turns
letters('DEGREE IS', 90, (face + 0.0008, 0, zc), 0.215)
letters('IN DISRUPTION', 180, (0, face + 0.0008, zc), 0.250)

# ---- socket and bulb on top ----
cut(bpy.data.objects['block3'], kit.cyl(0.052, 0.03, at=(0, 0, ztop), verts=64))
kit.lathe([(0, ztop - 0.016), (0.0515, ztop - 0.016), (0.0515, ztop - 0.001), (0.049, ztop + 0.003), (0, ztop + 0.003)],
          material=BRASS, steps=64, name='collar')
prof = [(0, ztop), (0.019, ztop)]
for k in range(5):   # screw-thread rings on the bulb base
    zz = ztop + 0.006 + k * 0.0065
    prof += [(0.0195, zz - 0.0025), (0.0212, zz), (0.0195, zz + 0.0025)]
prof += [(0.0185, ztop + 0.040), (0.016, ztop + 0.043), (0, ztop + 0.043)]
kit.lathe(prof, material=BRASS, steps=48, name='base')
bulb = [(0, ztop + 0.041), (0.016, ztop + 0.041), (0.0175, ztop + 0.050)]
for k in range(1, 25):
    t = k / 24
    # A-shape: neck, then a full round crown (max radius 0.058 about 2/3 up)
    z = ztop + 0.050 + 0.150 * t
    if t < 0.55:
        u = t / 0.55
        r = 0.0175 + (0.058 - 0.0175) * (math.sin(u * math.pi / 2) ** 1.6)
    else:
        u = (t - 0.55) / 0.45
        r = 0.058 * math.sqrt(max(0.0, 1 - u ** 2.2))
    bulb.append((r, z))
bulb.append((0, ztop + 0.200))
kit.lathe(bulb, material=BULB, steps=64, name='bulb')

turn_all(45)
merge_by_material()
ground_check()
kit.export('lamp')
