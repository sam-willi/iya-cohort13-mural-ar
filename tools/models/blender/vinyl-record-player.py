"""Vinyl record player // lotus koi pond, after Saissha Jain's drawing.

The drawing: a square wooden plinth on four bun feet; the record is a pond, with two koi, five notched lily pads,
and a lotus on a tall curving stem rising from the spindle; a tonearm on a round base at the right corner with its
needle on the record; a round on/off knob on the left face and "CORHORT13" across the front face (spelled as the
student wrote it, and as the mural concept repeats it).
Line-only drawing, so colours are a call: honey-oak plinth, a deep teal "water vinyl" record with lighter track
gaps so it still reads as a record, Kohaku/Sanke koi, olive lily pads, a pink lotus, chrome tonearm.
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Black.ttf'


# ---------------------------------------------------------------- helpers (local to this script)
def fillet(pts, r, n=4, closed=False):
    m = len(pts); out = []
    for i, p in enumerate(pts):
        ri = r[i] if isinstance(r, (list, tuple)) else r
        if (not closed and i in (0, m - 1)) or not ri:
            out.append(p); continue
        P = Vector(p); A = Vector(pts[i - 1]); B = Vector(pts[(i + 1) % m])
        u = (A - P); v = (B - P); lu, lv = u.length, v.length
        u.normalize(); v.normalize()
        ang = u.angle(v, math.pi)
        if ang > math.pi - 1e-3:
            out.append(p); continue
        d = min(ri / math.tan(ang / 2), 0.48 * lu, 0.48 * lv)
        t1, t2 = P + u * d, P + v * d
        for k in range(n + 1):
            t = k / n
            q = t1 * (1 - t) ** 2 + P * 2 * (1 - t) * t + t2 * t * t
            out.append((q.x, q.y))
    return out


def ftext(s, size, depth, at=(0, 0, 0), rot=(0, 0, 0), material=None, bevel=0.0, align='CENTER', res=5, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.align_x = align; cu.align_y = 'CENTER'; cu.resolution_u = res
    if bevel:
        cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.offset = -bevel
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


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


def rod(a, b, r, material=None, verts=24, bevel=0.0, name='rod'):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=(a + b) / 2, material=material, verts=verts, bevel=bevel, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def mesh_obj(name, verts, faces, uvs=None, material=None, smooth=True, recalc=True):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    if uvs is not None:
        lay = me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li in poly.loop_indices:
                lay.data[li].uv = uvs[me.loops[li].vertex_index]
    if recalc:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = smooth
    return o


def tex_mat(name, img, rough=0.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img; t.interpolation = 'Linear'
    uvn = m.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
    m.node_tree.links.new(uvn.outputs['UV'], t.inputs['Vector'])
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


def wood_image(name, light, dark, seed=3, n=512, lines=70):
    import numpy as np
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, n)[:, None]; u = np.linspace(0, 1, n)[None, :]
    warp = 0.006 * np.sin(u * math.tau * 1.3 + 0.7) + 0.003 * np.sin(u * math.tau * 3.7 + 2.0)
    phase = (v + warp) * lines + 1.5 * np.sin(v * math.tau * 2 + 1.0) + 0.8 * np.sin(v * math.tau * 5 + 0.3)
    g = 0.5 + 0.5 * np.sin(phase * math.tau)
    g = g ** 4
    streak = np.convolve(rng.normal(0, 1, n), np.ones(9) / 9, mode='same')[:, None] * 0.25
    t = np.clip(0.38 * g + 0.22 + streak * 0.8 + rng.normal(0, 0.03, (n, n)), 0, 1)
    L = np.array(srgb_lin(kit_hex(light))); D = np.array(srgb_lin(kit_hex(dark)))
    rgb = L[None, None, :] * (1 - t[..., None]) + D[None, None, :] * t[..., None]
    rgba = np.concatenate([rgb, np.ones((n, n, 1))], axis=2).astype(np.float32)
    img = bpy.data.images.new(name, n, n, alpha=False)
    img.pixels.foreach_set(rgba.ravel()); img.pack()
    return img


def kit_hex(h):
    h = kit.PALETTE.get(h, h).lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def box_uv(o, scale=1.0):
    """Apply modifiers, then project UVs per face along its dominant axis (grain runs along x, or y on the x faces)."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    me = o.data
    lay = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 2:
                uv = (co.x, co.y)
            elif ax == 1:
                uv = (co.x, co.z)
            else:
                uv = (co.y, co.z)
            lay.data[li].uv = (uv[0] * scale + 0.5, uv[1] * scale + 0.5)
    return o


def srgb_lin(c):
    return [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c]


# ---------------------------------------------------------------- materials
WOOD = None   # textured, below
WOOD_DK = kit.mat('walnut', rough=0.6, name='walnut')
VINYL = kit.mat('#173d42', rough=0.18, name='pond_vinyl')
GAP = kit.mat('#2a5a60', rough=0.35, name='track_gap')
CHROME = kit.mat('chrome', rough=0.25, metal=0.85, name='chrome')
BLACK = kit.mat('black', rough=0.45, name='black')
CREAM = kit.mat('cream', rough=0.5, name='label')
INK = kit.mat('#3a2a1e', rough=0.5, name='ink')
BRASS = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
PAD = kit.mat('#62823a', rough=0.5, name='lilypad')
STEM = kit.mat('#4e6d2c', rough=0.55, name='stem')
PETAL = kit.mat('#f0aaa6', rough=0.5, name='petal')
PETAL_IN = kit.mat('#f7d0c6', rough=0.5, name='petal_inner')
POD = kit.mat('#e8b23a', rough=0.5, name='seedpod')
FIN = kit.mat('#f8dccb', rough=0.45, alpha=0.82, name='fin')
EYE = kit.mat('black', rough=0.2, name='eye')

# ---------------------------------------------------------------- plinth, feet, platter, record-pond
W, HP, FOOT = 0.40, 0.085, 0.020
TOP = FOOT + HP
WOOD = tex_mat('oak', wood_image('oak_grain', '#9c6a3b', '#6a4021'), rough=0.5)
plinth = kit.box((W, W, HP), at=(0, 0, FOOT + HP / 2), material=WOOD, bevel=0.009, segments=3, name='plinth')
box_uv(plinth, 1.6)
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.lathe(fillet([(0, 0), (0.020, 0), (0.028, 0.006), (0.029, 0.013), (0.024, FOOT + 0.003), (0, FOOT + 0.003)],
                         [0, 0.004, 0.004, 0.004, 0.003, 0], n=3), at=(sx * 0.160, sy * 0.160, 0), material=WOOD_DK, steps=32, name='bun')
# platter (chrome rim), slightly proud of the plinth
kit.lathe(fillet([(0, TOP - 0.003), (0.171, TOP - 0.003), (0.174, TOP + 0.002), (0.174, TOP + 0.011), (0.169, TOP + 0.014), (0, TOP + 0.014)],
                 [0, 0.002, 0.002, 0.002, 0.002, 0], n=2), material=CHROME, steps=96, name='platter')
WATER = TOP + 0.0175
rec_prof = [(0, TOP + 0.014), (0.166, TOP + 0.014), (0.166, WATER - 0.001), (0.164, WATER)]
gaps = [0.072, 0.096, 0.118, 0.138, 0.156]
r = 0.164
pts = []
for g in sorted(gaps, reverse=True):
    pts += [(g + 0.0018, WATER), (g - 0.0018, WATER)]
rec_prof += pts + [(0.050, WATER), (0, WATER)]
record = kit.lathe(rec_prof, material=VINYL, steps=96, name='record')
record.data.materials.append(GAP)
for p in record.data.polygons:
    c = p.center; rr = math.hypot(c.x, c.y)
    if abs(c.z - WATER) < 1e-4 and any(abs(rr - g) < 0.0018 for g in gaps):
        p.material_index = 1
# label with ring and three radial lines, spindle
kit.cyl(0.049, 0.0012, at=(0, 0, WATER + 0.0006), material=CREAM, verts=64, name='label')
kit.torus(0.041, 0.0011, at=(0, 0, WATER + 0.0012), material=INK, major=64, minor=6, name='labelring')
kit.cyl(0.0034, 0.012, at=(0, 0, WATER + 0.006), material=CHROME, verts=16, name='spindle')
kit.box((0.010, 0.010, 0.006), at=(0, 0, WATER + 0.013), material=CHROME, bevel=0.0012, name='spindlecap')

# ---------------------------------------------------------------- lily pads (notched, floating)
def lily(x, y, r, notch_dir):
    n = 28; a0 = math.radians(16)
    poly = [(0.0, 0.0)] + [(r * math.cos(a0 + (math.tau - 2 * a0) * k / n), r * math.sin(a0 + (math.tau - 2 * a0) * k / n)) for k in range(n + 1)]
    o = kit.extrude(poly, 0.0016, at=(x, y, WATER - 0.0004), rot=(0, 0, notch_dir), material=PAD, bevel=0.0006, name='pad')
    rod((x, y, WATER + 0.0012), (x + 0.8 * r * math.cos(math.radians(notch_dir + 180)), y + 0.8 * r * math.sin(math.radians(notch_dir + 180)), WATER + 0.0012),
        0.0007, material=STEM, verts=6, name='vein')
    return o


for x, y, r, d in ((0.000, 0.125, 0.020, 230), (-0.118, 0.055, 0.021, 300), (0.067, 0.117, 0.018, 160),
                   (-0.008, -0.128, 0.021, 60), (0.072, -0.120, 0.016, 110)):
    lily(x, y, r, d)

# ---------------------------------------------------------------- koi (textured bodies, fins, eyes)
def koi_texture(name, seed, red_patches, black_spots):
    W_, H_ = 96, 48
    img = bpy.data.images.new(name, W_, H_, alpha=False)
    white = srgb_lin((0.965, 0.945, 0.915)); red = srgb_lin((0.85, 0.30, 0.13)); blk = srgb_lin((0.11, 0.10, 0.10))
    px = []
    for j in range(H_):
        v = j / (H_ - 1)                       # around the body; 0.25 = top
        for i in range(W_):
            u = i / (W_ - 1)                   # nose -> tail
            c = white
            for (u0, u1, v0, hw) in red_patches:
                if u0 <= u <= u1:
                    edge = hw * (0.75 + 0.25 * math.sin(u * 37 + seed))
                    if abs(v - v0) < edge:
                        c = red
            for (us, vs, rs) in black_spots:
                if (u - us) ** 2 + ((v - vs) * 2.0) ** 2 < rs * rs:
                    c = blk
            px += [*c, 1.0]
    img.pixels = px
    img.pack()
    return img


def koi(name, at, heading, length, bend, img):
    """A koi lying at the water line, nose at +X before rotation. bend curves the tail sideways."""
    rings, segs = 18, 18
    prof = [(0.0, 0.0), (0.03, 0.42), (0.10, 0.78), (0.22, 0.98), (0.34, 1.0), (0.50, 0.86), (0.66, 0.60),
            (0.80, 0.36), (0.92, 0.20), (1.0, 0.14)]

    def width(t):
        for (a, wa), (b, wb) in zip(prof, prof[1:]):
            if a <= t <= b:
                k = (t - a) / (b - a); k = k * k * (3 - 2 * k)
                return wa + (wb - wa) * k
        return prof[-1][1]

    def centre(t):           # spine: nose at x=0 heading -X toward the tail
        return Vector((-t * length, bend * length * t * t, 0))

    WY, WZ = 0.125 * length, 0.105 * length
    verts, uvs, faces = [], [], []
    for i in range(rings + 1):
        t = i / rings
        t_ = 0.004 + 0.996 * t
        w = max(width(t_), 0.02)
        c = centre(t_)
        for j in range(segs):
            th = math.tau * j / segs
            y = math.cos(th) * WY * w
            z = math.sin(th) * WZ * w
            if z < 0:
                z *= 0.75            # flatter belly
            verts.append((c.x, c.y + y, c.z + z)); uvs.append((t, (j / segs + 0.0) % 1.0))
    for i in range(rings):
        for j in range(segs):
            a = i * segs + j; b = i * segs + (j + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    # caps at nose and tail
    nose = len(verts); verts.append((0.004 * length, 0, 0)); uvs.append((0, 0.25))
    for j in range(segs):
        faces.append((nose, (j + 1) % segs, j))
    tail = len(verts); c = centre(1.0); verts.append((c.x - 0.002, c.y, c.z)); uvs.append((1, 0.25))
    base = rings * segs
    for j in range(segs):
        faces.append((tail, base + j, base + (j + 1) % segs))
    body = mesh_obj(name, verts, faces, uvs, tex_mat(name + '_skin', img))
    parts = [body]
    # tail fan (horizontal, spread like the drawing's top-down koi), split into two lobes
    ct = centre(1.0); tang = (centre(1.0) - centre(0.95)).normalized()
    ang = math.degrees(math.atan2(tang.y, tang.x))
    k_ = length / 0.1
    tail_poly = fillet([(x * k_, y * k_) for x, y in ((0, -0.009), (0.016, -0.021), (0.034, -0.031), (0.042, -0.020), (0.031, 0),
                                                      (0.042, 0.020), (0.034, 0.031), (0.016, 0.021), (0, 0.009))],
                       [0, 0.006, 0.006, 0.006, 0.004, 0.006, 0.006, 0.006, 0], n=4, closed=True)
    tf = kit.extrude(tail_poly, 0.0012, at=(ct.x + tang.x * -0.002, ct.y + tang.y * -0.002, -0.0006), rot=(0, 0, ang), material=FIN, name='tail')
    parts.append(tf)
    # pectoral fins, spread out to the sides and lying on the water
    for s in (-1, 1):
        c = centre(0.24)
        poly = fillet([(x * length / 0.1, s * y * length / 0.1) for x, y in ((0, 0), (-0.002, 0.014), (-0.009, 0.024), (-0.019, 0.025), (-0.025, 0.015), (-0.017, 0))],
                      [0, 0.005, 0.005, 0.005, 0.005, 0], n=4, closed=True)
        if s < 0:
            poly = list(reversed(poly))
        parts.append(kit.extrude(poly, 0.0012, at=(c.x, c.y + s * WY * 0.6, -0.0006), material=FIN, name='pfin'))
        # pelvic fins, smaller, further back
        c2 = centre(0.55)
        poly2 = fillet([(x * length / 0.1, s * y * length / 0.1) for x, y in ((0, 0), (-0.002, 0.009), (-0.008, 0.015), (-0.015, 0.012), (-0.012, 0))],
                       [0, 0.003, 0.003, 0.003, 0], n=3, closed=True)
        if s < 0:
            poly2 = list(reversed(poly2))
        parts.append(kit.extrude(poly2, 0.0011, at=(c2.x, c2.y + s * WY * 0.4, -0.0008), material=FIN, name='vfin'))
        # eyes
        e = centre(0.08); we = width(0.08)
        parts.append(kit.sphere(0.0030 * length / 0.1, at=(e.x, e.y + s * WY * we * math.cos(0.6) * 0.93, WZ * we * math.sin(0.6) * 0.93),
                                material=EYE, segs=10, rings=6, name='eye'))
    # dorsal fin along the back
    dv, dfc = [], []
    for k in range(13):      # a thin fin strip that follows the bent spine
        t = 0.28 + 0.42 * k / 12
        c = centre(t); top = WZ * width(t)
        h = 0.0095 * length / 0.1 * math.sin(math.pi * k / 12) ** 0.6 * (1.15 - 0.5 * k / 12)
        dv += [(c.x, c.y, top - 0.0025), (c.x, c.y, top + h)]
    for k in range(12):
        dfc.append((2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1))
    parts.append(mesh_obj('dorsal', dv, dfc, material=FIN))
    k = bake_join(name, parts)
    k.matrix_world = Matrix.Translation(at) @ Matrix.Rotation(math.radians(heading), 4, 'Z') @ k.matrix_world
    return k


img1 = koi_texture('kohaku', 1.0, [(0.02, 0.16, 0.25, 0.16), (0.30, 0.52, 0.27, 0.17), (0.62, 0.80, 0.22, 0.13)],
                   [(0.45, 0.32, 0.035), (0.70, 0.30, 0.03)])
img2 = koi_texture('sanke', 2.3, [(0.20, 0.42, 0.24, 0.16), (0.55, 0.70, 0.29, 0.12)],
                   [(0.12, 0.27, 0.035), (0.33, 0.20, 0.03), (0.48, 0.30, 0.04), (0.62, 0.21, 0.03), (0.80, 0.26, 0.035), (0.90, 0.24, 0.025)])
LK = 0.095
for name, mid, head, ln, bend, img in (('koi_a', (-0.086, -0.060), 125, LK, 0.20, img1), ('koi_b', (0.106, 0.016), -80, LK * 0.95, -0.15, img2)):
    hd = Vector((math.cos(math.radians(head)), math.sin(math.radians(head)), 0))
    nose = Vector((*mid, WATER + 0.0015)) + hd * (ln * 1.33 / 2)
    koi(name, nose, head, ln, bend, img)

# ---------------------------------------------------------------- lotus: stem from the spindle, flower tilted toward the front
FC = Vector((-0.075, 0.058, WATER + 0.285))
FN = Vector((-0.25, -0.55, 0.80)).normalized()      # flower faces up and toward the viewer
stem_pts = [(0, 0, WATER + 0.015), (0.0, 0.0, WATER + 0.09), (-0.022, 0.016, WATER + 0.17), (-0.060, 0.070, WATER + 0.235),
            tuple(FC - FN * 0.035), tuple(FC)]
kit.tube(stem_pts, 0.0042, material=STEM, bevel_res=10, name='stem')


def petal(L, w, cup, curl, material):
    n, m = 9, 4
    verts, faces = [], []
    for i in range(n + 1):
        t = i / n
        wt = w * (math.sin(math.pi * min(t * 1.08, 1.0)) ** 0.75) * (1 - 0.15 * t)
        for j in range(-m, m + 1):
            s = j / m
            verts.append((t * L, s * wt, cup * s * s * wt + curl * t * t * L))
    row = 2 * m + 1
    for i in range(n):
        for j in range(row - 1):
            a = i * row + j
            faces.append((a, a + 1, a + 1 + row, a + row))
    return mesh_obj('petal', verts, faces, material=material)


flower = []
for layer, (count, L, w, pitch, mat, r0, off) in enumerate(((16, 0.060, 0.0105, 18, PETAL, 0.010, 0),
                                                           (12, 0.046, 0.0095, 42, PETAL, 0.008, 15),
                                                           (9, 0.032, 0.0085, 64, PETAL_IN, 0.006, 7))):
    for k in range(count):
        a = math.tau * k / count + math.radians(off)
        p = petal(L, w, 0.35, 0.18, mat)
        p.matrix_world = Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((r0, 0, 0.002 * layer)) @ Matrix.Rotation(math.radians(-pitch), 4, 'Y')
        flower.append(p)
pod = kit.lathe(fillet([(0, 0.0), (0.010, 0.0), (0.013, 0.010), (0.011, 0.014), (0, 0.0145)], [0, 0.003, 0.002, 0.002, 0], n=3),
                material=POD, steps=24, name='pod')
flower.append(pod)
for k in range(7):
    a = math.tau * k / 7
    flower.append(kit.sphere(0.0016, at=(0.0065 * math.cos(a), 0.0065 * math.sin(a), 0.0143), material=kit.mat('#a3752a', rough=0.5), segs=8, rings=5, name='seed'))
flower.append(kit.sphere(0.0016, at=(0, 0, 0.0147), material=kit.mat('#a3752a', rough=0.5), segs=8, rings=5, name='seed'))
flower.append(kit.cyl(0.0055, 0.008, at=(0, 0, -0.003), r2=0.004, material=STEM, verts=16, name='receptacle'))
fl = bake_join('lotus', flower)
q = Vector((0, 0, 1)).rotation_difference(FN)
fl.matrix_world = Matrix.Translation(FC + FN * 0.004) @ q.to_matrix().to_4x4() @ fl.matrix_world

# ---------------------------------------------------------------- tonearm on a round base at the right-front corner
P = Vector((0.152, -0.152, TOP))
kit.lathe(fillet([(0, 0), (0.033, 0), (0.033, 0.020), (0.030, 0.024), (0, 0.024)], [0, 0, 0.003, 0.003, 0], n=2),
          at=P, material=CHROME, steps=48, name='armbase')
kit.lathe(fillet([(0, 0.024), (0.012, 0.024), (0.010, 0.040), (0, 0.040)], [0, 0.002, 0.002, 0], n=2), at=P, material=BLACK, steps=24, name='post')
kit.torus(0.011, 0.0022, at=P + Vector((0, 0, 0.040)), rot=(90, 0, 45), material=CHROME, major=24, minor=8, name='gimbal')
to_c = Vector((-1, 1, 0)).normalized()
A0 = P + Vector((0, 0, 0.040))
A1 = A0 + to_c * 0.125
rod(A0 - to_c * 0.010, A1, 0.0042, material=CHROME, verts=16, name='arm')
rod(A0 - to_c * 0.012, A0 - to_c * 0.040, 0.0125, material=BLACK, verts=24, bevel=0.002, name='counterweight')
rod(A0 - to_c * 0.040, A0 - to_c * 0.043, 0.0095, material=CHROME, verts=24, name='cwcap')
hs = kit.box((0.030, 0.017, 0.004), at=A1 + to_c * 0.010, rot=(0, 0, 135), material=BLACK, bevel=0.0012, name='headshell')
kit.box((0.010, 0.004, 0.010), at=A1 + to_c * 0.020 + Vector((0, 0, 0.002)), rot=(0, 0, 135), material=BLACK, bevel=0.001, name='fingerlift')
kit.box((0.016, 0.011, 0.016), at=A1 + to_c * 0.012 + Vector((0, 0, -0.010)), rot=(0, 0, 135), material=kit.mat('red', rough=0.4), bevel=0.0012, name='cartridge')
rod(A1 + to_c * 0.016 + Vector((0, 0, -0.018)), Vector((A1.x + to_c.x * 0.018, A1.y + to_c.y * 0.018, WATER + 0.0004)), 0.0008,
    material=CHROME, verts=6, name='stylus')
# arm rest post
REST = P + Vector((0.004, 0.052, 0))
rod(REST, REST + Vector((0, 0, 0.034)), 0.004, material=CHROME, verts=12, name='rest')
kit.box((0.010, 0.010, 0.005), at=REST + Vector((0, 0, 0.034)), material=BLACK, bevel=0.0012, name='restcup')

# ---------------------------------------------------------------- on/off knob on the left face, CORHORT13 across the front
KZ = FOOT + HP / 2
KY = -0.105
kit.cyl(0.031, 0.004, at=(-W / 2 - 0.0015, KY, KZ), rot=(0, 90, 0), material=BLACK, verts=40, bevel=0.0012, name='bezel')
kn = kit.lathe(fillet([(0, 0), (0.025, 0), (0.026, 0.006), (0.024, 0.014), (0, 0.014)], [0, 0.002, 0.002, 0.003, 0], n=2),
               at=(-W / 2 - 0.003, KY, KZ), rot=(0, -90, 0), material=CHROME, steps=40, name='knob')
for k in range(20):   # knurl ridges round the knob
    a = math.tau * k / 20
    kit.box((0.010, 0.0024, 0.0022), at=(-W / 2 - 0.0095, KY + 0.0255 * math.cos(a), KZ + 0.0255 * math.sin(a)),
            rot=(math.degrees(a), 0, 0), material=CHROME, name='knurl')
kit.box((0.002, 0.0035, 0.018), at=(-W / 2 - 0.0172, KY, KZ + 0.008), material=BLACK, name='pointer')
for dz, dy in ((0.0336, -0.023), (0.0336, 0.023)):     # ON / OFF index dots
    kit.cyl(0.0035, 0.002, at=(-W / 2 - 0.0005, KY + dy, KZ + dz - 0.006), rot=(0, 90, 0), material=CREAM, verts=12, name='dot')
ftext('CORHORT13', 0.030 / 0.515, 0.003, at=(0.015, -W / 2, KZ - 0.002), rot=(90, 0, 0), material=BRASS, bevel=0.0005, name='label_text')

# ---------------------------------------------------------------- join, settle and export
both = bake_join('vinyl_record_player')
settle(both)
kit.export('vinyl-record-player')
