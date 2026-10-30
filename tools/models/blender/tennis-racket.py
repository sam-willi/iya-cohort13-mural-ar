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

# "Racket Guitar", after Alex Tully's isometric drawing: a tennis racket that is also a guitar. Six steel strings
# run from tuning posts on top of the head, over a humbucker pickup and a bridge on the string bed, down the open
# throat and the wrapped grip to a tailpiece on the butt cap. Laminated-wood frame (vintage, like the mural's
# workshop), gut string bed, leather grip. Stands on its butt, string face to the front (-Y). ~0.65 m.
WOOD = image_mat('racket_wood', wood_tex('#b5773f', '#6e4222', size=512, rings=9, seed=7, figure=0.4, contrast=1.15), rough=0.4)
GUT = kit.mat('cream', rough=0.5, name='gut')
STEEL = kit.mat('chrome', rough=0.28, metal=0.85, name='steel_string')
LEATHER = kit.mat('walnut', rough=0.72, name='leather')
TAPE = kit.mat('black', rough=0.6, name='tape')
BRASS = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
PICK = kit.mat('black', rough=0.4, name='pickup')
CHROME = kit.mat('chrome', rough=0.22, metal=0.9, name='chrome')
BONE = kit.mat('paper', rough=0.45, name='bone')

A, B = 0.125, 0.160          # head oval semi-axes (centreline of the frame)
ZH = 0.46                    # head centre height
FW, FD = 0.013, 0.022        # frame width (in the face plane) and depth (front-back)


def oval(phi, grow=0.0):
    return Vector(((A + grow) * math.sin(phi), 0, ZH - (B + grow) * math.cos(phi)))


def sweep(path, prof, name, material, closed=False, uv=8.0, smooth=50):
    """Sweep a 2D profile [(n, y)] along a path in the XZ plane. n is the in-plane normal."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
    P = [Vector(p) for p in path]; N = len(P)
    rings, us = [], [0.0]
    for i in range(N):
        a = P[i - 1] if (closed or i > 0) else P[i]
        b = P[(i + 1) % N] if (closed or i < N - 1) else P[i]
        t = (b - a).normalized()
        n = Vector((-t.z, 0, t.x))
        rings.append([bm.verts.new(P[i] + n * pn + Vector((0, py, 0))) for pn, py in prof])
        if i:
            us.append(us[-1] + (P[i] - P[i - 1]).length)
    M = len(prof)
    segs = range(N) if closed else range(N - 1)
    for i in segs:
        j = (i + 1) % N
        for k in range(M):
            l = (k + 1) % M
            f = bm.faces.new((rings[i][k], rings[i][l], rings[j][l], rings[j][k]))
            uj = us[j] if j else us[-1] + (P[0] - P[-1]).length
            for lp, (u, v) in zip(f.loops, ((us[i], k), (us[i], k + 1), (uj, k + 1), (uj, k))):
                lp[uvl].uv = (u * uv, v / M * 0.7)   # several laminations round the section
    if not closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    o = link(name, bm, None, smooth)
    o.data.materials.append(material)
    return o


def rprof(w, d, r, n=4):
    return [(x, y) for x, y in rrect(w, d, r, n)]


FRAME = rprof(FW, FD, 0.0045, 4)

# ---- frame: left arm -> round the head -> right arm, then the yoke across the bottom of the string bed ----
J = math.radians(55)                       # where the throat arms meet the head
def bezier(p0, p1, p2, p3, n):
    return [p0 * (1 - t) ** 3 + p1 * 3 * (1 - t) ** 2 * t + p2 * 3 * (1 - t) * t * t + p3 * t ** 3
            for t in (i / n for i in range(n + 1))]


ZS = 0.178                                  # where the arms leave the shaft
pj = oval(-J)
tj = Vector((-A * math.cos(-J), 0, -B * math.sin(-J))).normalized()   # head tangent there, going up the left side
left = bezier(Vector((-0.0045, 0, ZS)), Vector((-0.0045, 0, ZS + 0.07)), pj - tj * 0.075, pj, 18)
head = [oval(-J - (TAU - 2 * J) * i / 90) for i in range(1, 90)]
right = [Vector((-p.x, 0, p.z)) for p in reversed(left)]
sweep(left + head + right, FRAME, 'frame', WOOD)
sweep([oval(-J + 2 * J * i / 30) for i in range(31)], rprof(0.011, FD - 0.002, 0.004, 4), 'yoke', WOOD)

# ---- shaft, grip with its spiral wrap, finishing tape, butt cap ----
def octa(z0, z1, r, name, mat):
    o = kit.cyl(r, z1 - z0, at=(0, 0, (z0 + z1) / 2), verts=8, material=mat, bevel=0.0018, segments=2, name=name)
    o.rotation_euler = (0, 0, math.radians(22.5))
    return o


octa(0.128, 0.190, 0.0125, 'shaft', WOOD)
kit.cyl(0.0140, 0.122, at=(0, 0, 0.012 + 0.061), verts=16, material=LEATHER, name='grip')
helix = [(0.0146 * math.cos(t), 0.0146 * math.sin(t), 0.016 + 0.112 * t / (TAU * 6.5)) for t in
         np.linspace(0, TAU * 6.5, 150)]
tube(helix, 0.0011, LEATHER, res=2, name='wrap')
kit.cyl(0.0152, 0.009, at=(0, 0, 0.1315), verts=24, material=TAPE, bevel=0.0012, name='finish_tape')
kit.lathe([(0, 0), (0.0150, 0), (0.0168, 0.0025), (0.0168, 0.009), (0.0150, 0.0135), (0, 0.0135)], material=WOOD,
          steps=32, name='butt')

# ---- string bed (gut): 16 mains, 19 crosses, inside the inner edge of the frame ----
ai, bi = A - FW / 2, B - FW / 2
def strand(p, q, r, mat, name):
    p, q = Vector(p), Vector(q); d = q - p
    o = kit.cyl(r, d.length, at=(p + q) / 2, verts=6, material=mat, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


for k in range(16):
    x = (k - 7.5) * 0.0128
    h = bi * math.sqrt(max(0, 1 - (x / ai) ** 2)) + 0.003
    strand((x, 0.0006, ZH - h), (x, 0.0006, ZH + h), 0.00075, GUT, 'main')
for k in range(19):
    z = (k - 9) * 0.0152
    w = ai * math.sqrt(max(0, 1 - (z / bi) ** 2)) + 0.003
    strand((-w, -0.0006, ZH + z), (w, -0.0006, ZH + z), 0.00075, GUT, 'cross')

# ---- the guitar: posts on top, nut, six steel strings fanning down to the tailpiece on the butt ----
ZT, YT = 0.0105, -0.0200          # tailpiece string anchor
top_z = lambda x: ZH + (B + FW / 2) * math.sqrt(1 - (x / (A + FW / 2)) ** 2)
strings = []
for i in range(6):
    xt = (i - 2.5) * 0.0112
    xb = (i - 2.5) * 0.0040
    zo = top_z(xt)
    # tuning post standing on top of the frame, with its ivory button
    kit.cyl(0.0024, 0.016, at=(xt, -0.002, zo + 0.006), verts=16, material=CHROME, name='post')
    kit.cyl(0.0042, 0.0032, at=(xt, -0.002, zo + 0.0145), verts=20, material=BONE, bevel=0.0009, name='button')
    nut = Vector((xt, -0.0122, zo + 0.0022))
    strings.append((Vector((xt, -0.002, zo + 0.009)), nut, Vector((xb, YT, ZT))))
# nut: a bone strip along the top-front edge of the head
sweep([oval(-math.pi + d) + Vector((0, 0, 0)) for d in np.linspace(-0.36, 0.36, 15)],
      [(-FW / 2 + 0.0005 + x, -FD / 2 - 0.0002 + y) for x, y in rrect(0.004, 0.0044, 0.0012, 3)], 'nut', BONE)  # n points inward here


def string_y(z, s):
    nut, tail = s[1], s[2]
    t = (z - tail.z) / (nut.z - tail.z)
    return tail.lerp(nut, t)


for i, s in enumerate(strings):
    r = 0.00085 - i * 0.00005
    strand(s[0], s[1], r, STEEL, 'gstring')
    strand(s[1], s[2], r, STEEL, 'gstring')

# pickup on a brass mounting rail across the bed
zp = ZH - 0.050
wp = ai * math.sqrt(1 - ((zp - ZH) / bi) ** 2) + 0.004
kit.box((2 * wp, 0.0055, 0.016), at=(0, -0.0045, zp), material=BRASS, bevel=0.0012, name='rail')
kit.box((0.078, 0.0085, 0.040), at=(0, -0.0083, zp), material=PICK, bevel=0.0025, segments=3, name='pickup')
for row in (-0.0095, 0.0095):
    for i, s in enumerate(strings):
        p = string_y(zp + row, s)
        kit.sphere(0.0021, at=(p.x, -0.0125, zp + row), scale=(1, 0.55, 1), material=CHROME, segs=16, rings=8,
                   name='pole')
for x in (-0.034, 0.034):
    kit.cyl(0.0018, 0.002, at=(x, -0.0126, zp), rot=(90, 0, 0), material=CHROME, verts=12, name='screw')
# bridge: brass rail with six chrome saddles the strings rest on
zb = ZH - 0.100
wb = ai * math.sqrt(1 - ((zb - ZH) / bi) ** 2) + 0.004
kit.box((2 * wb, 0.0055, 0.012), at=(0, -0.0045, zb), material=BRASS, bevel=0.0012, name='bridge_rail')
kit.box((0.074, 0.0060, 0.012), at=(0, -0.0095, zb), material=BRASS, bevel=0.0015, name='bridge')
for s in strings:
    p = string_y(zb, s)
    top = p.y + 0.0008
    kit.box((0.0068, abs(top) - 0.0122, 0.0075), at=(p.x, (top - 0.0122) / 2, zb),
            material=CHROME, bevel=0.0010, name='saddle')
# tailpiece on the front of the butt cap
kit.box((0.026, 0.0125, 0.013), at=(0, -0.01525, 0.0115), material=BRASS, bevel=0.002, segments=3, name='tailpiece')
for s in strings:
    kit.sphere(0.0013, at=(s[2].x, YT - 0.0008, ZT), material=CHROME, segs=12, rings=6, name='ball_end')

# ---- the "13" tennis ball Alex drew flying off beside the head (speed lines are a drawing convention, not modelled) ----
# Optic-yellow felt with the white rubber seam of a real ball (the classic two-dog-bone curve). Each of its four round
# bulbs carries a printed "13", so it reads from every side; the two lobes' numbers are turned 180 degrees to each
# other, as in the drawing (one upright, one upside down across the seam).
BALL_TEX = r"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]; W = int(sys.argv[2]); H = W // 2; SS = 2
b = 0.28; a = 1 - b; c = 2 * np.sqrt(a * b)
t = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
S = np.stack([a * np.cos(t) + b * np.cos(3 * t), a * np.sin(t) - b * np.sin(3 * t), c * np.sin(2 * t)], 1)
S /= np.linalg.norm(S, axis=1, keepdims=True)
T = np.roll(S, -1, 0) - np.roll(S, 1, 0); T /= np.linalg.norm(T, axis=1, keepdims=True)
NS = np.cross(S, T)
w, h = W * SS, H * SS
u = (np.arange(w) + 0.5) / w; v = 1 - (np.arange(h) + 0.5) / h
LON, LAT = np.meshgrid((u - 0.5) * 2 * np.pi, (v - 0.5) * np.pi)
D = np.stack([np.cos(LAT) * np.cos(LON), np.cos(LAT) * np.sin(LON), np.sin(LAT)], -1).reshape(-1, 3)
dist = np.empty(len(D)); side = np.empty(len(D))
for i in range(0, len(D), 20000):
    dd = D[i:i + 20000] @ S.T; k = dd.argmax(1)
    dist[i:i + 20000] = np.arccos(np.clip(dd[np.arange(len(k)), k], -1, 1))
    side[i:i + 20000] = np.sign(np.einsum('ij,ij->i', D[i:i + 20000], NS[k]))
# glyph mask
F = None
for f in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial.ttf'):
    try:
        F = ImageFont.truetype(f, 600); break
    except Exception:
        pass
F = F or ImageFont.load_default()
gi = Image.new('L', (1400, 900), 0); gd = ImageDraw.Draw(gi)
gd.text((700, 450), '13', font=F, fill=255, anchor='mm')
bb = gi.getbbox(); gi = gi.crop(bb); G = np.asarray(gi, np.float32) / 255; gh, gw = G.shape
CAP = 0.50                                  # cap height in tangent-plane units (about 26 degrees)
ink = np.zeros(len(D))
q = 0.5 ** 0.5
BETA = float(sys.argv[3])                     # glyph turn on the first lobe (degrees, CCW seen from outside)
for cx, cy, beta in ((q, -q, BETA), (-q, q, BETA), (q, q, BETA + 180), (-q, -q, BETA + 180)):
    C = np.array([cx, cy, 0.0])
    e1 = np.cross([0, 0, 1.0], C); e1 /= np.linalg.norm(e1); e2 = np.cross(C, e1)
    dc = D @ C; m = dc > 0.5
    P = D[m] / dc[m, None]
    x0 = P @ e1; y0 = P @ e2; cb, sb = np.cos(np.radians(beta)), np.sin(np.radians(beta))
    x = cb * x0 + sb * y0; y = -sb * x0 + cb * y0
    px = (x / CAP * gh + gw / 2).astype(int); py = (gh / 2 - y / CAP * gh).astype(int)
    ok = (px >= 0) & (px < gw) & (py >= 0) & (py < gh)
    vals = np.zeros(len(px)); vals[ok] = G[py[ok], px[ok]]
    ink[np.where(m)[0]] = np.maximum(ink[np.where(m)[0]], vals)
rng = np.random.default_rng(13)
def waves(n, f):          # isotropic noise on the sphere from random plane waves (no pinching at the UV poles)
    dirs = rng.normal(0, 1, (n, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    ph = rng.uniform(0, 2 * np.pi, n); acc = np.zeros(len(D))
    for k in range(n):
        acc += np.sin(f * (D @ dirs[k]) + ph[k])
    return (acc / np.sqrt(n / 2)).reshape(h, w)
def grain(N):             # fine felt speckle: a random value per voxel of a 3D grid
    ijk = np.floor((D + 1) * N).astype(np.int64)
    hsh = (ijk[:, 0] * 73856093) ^ (ijk[:, 1] * 19349663) ^ (ijk[:, 2] * 83492791)
    return ((hsh % 1000) / 500.0 - 1).reshape(h, w)
fuzz = 0.025 * grain(260) + 0.012 * waves(40, 60) + 0.02 * waves(16, 6)
felt = np.array([0.84, 0.86, 0.30])
seamc = np.array([0.95, 0.94, 0.90]); inkc = np.array([0.12, 0.115, 0.11])
d = dist.reshape(h, w); SW = 0.040
col = felt[None, None] * (1 + fuzz[..., None])
edge = np.clip((d - SW) / 0.05, 0, 1)            # felt curls darker into the seam groove
col *= (0.80 + 0.20 * edge)[..., None]
col = np.where((d < SW)[..., None], seamc[None, None] * (1 + 0.3 * fuzz[..., None]), col)
aa = np.clip((SW + 0.006 - d) / 0.012, 0, 1)[..., None] * (d >= SW)[..., None]
col = col * (1 - aa) + seamc * aa
ik = ink.reshape(h, w)[..., None]
col = col * (1 - ik) + inkc * ik
img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
img.save(out, quality=90)
"""


def ball_texture(beta, size=1024):
    import subprocess, tempfile
    path = os.path.join(tempfile.mkdtemp(), 'tennis_ball.jpg')   # JPEG: the felt noise bloats a PNG
    subprocess.run(['/usr/bin/env', 'python3', '-c', BALL_TEX, path, str(size), str(beta)], check=True)
    im = bpy.data.images.load(path); im.pack(); im.name = 'tennis_ball'
    return im


def tennis_ball(center, r, rot, beta):
    img = ball_texture(beta)
    m = bpy.data.materials.new('ball_felt'); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Roughness'].default_value = 0.95
    tx = m.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    m.node_tree.links.new(tx.outputs['Color'], bs.inputs['Base Color'])
    o = kit.sphere(1.0, segs=64, rings=32, name='tennis_ball')
    me = o.data
    uvl = me.uv_layers[0] if me.uv_layers else me.uv_layers.new()
    for p in me.polygons:
        us, vs, poles = [], [], []
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            us.append(math.atan2(co.y, co.x) / TAU + 0.5)
            vs.append(math.asin(max(-1, min(1, co.z))) / math.pi + 0.5)
            poles.append(abs(co.z) > 0.9999)
        real = [x for x, pl in zip(us, poles) if not pl]
        if max(real) - min(real) > 0.5:
            us = [x + 1 if x < 0.5 else x for x in us]; real = [x + 1 if x < 0.5 else x for x in real]
        for li, x, y, pl in zip(p.loop_indices, us, vs, poles):
            uvl.data[li].uv = (sum(real) / len(real) if pl else x, y)
    o.scale = (r, r, r); o.location = center
    o.rotation_euler = [math.radians(a) for a in rot]
    o.data.materials.clear(); o.data.materials.append(m)
    return o


# Seen from the front the seam runs diagonally between two bulbs: an upright "13" lower left and one upside down
# upper right, as drawn. The ball is turned 135 deg about Y to put the bulbs there; beta pre-turns the print to match.
# A touch bigger than regulation (33.5 mm), toward the drawing's proportion.
BALL_R = 0.037
tennis_ball((0.25, -0.03, ZH + 0.035), BALL_R, (0, 135, 0), beta=110)

merge_by_material()
ground_check()
kit.export('tennis-racket')
