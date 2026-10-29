"""Air balloon - Garrett McCormick.

His drawing: a round envelope of horizontal bands crossed by vertical gore seams that meet at a crown ring and vent on top,
"IYA" around the middle band; cables converge from the mouth to a burner on a pyramid frame over a square basket. He gave
the basket a steering rig: a flat rudder fin on its left face, a jet thruster on its right face, and a curved tail fin
rising behind. Line-only drawing, so colours are a choice: the bands run cardinal / orange / amber / cream (a warm sunset
against the mural's sky window) with cardinal letters, a wicker basket with leather trim, a lit burner flame.
The basket is turned 45 degrees so its front corner, the fin, the thruster and the IYA face the viewer as in the drawing.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

FONTS = '/System/Library/Fonts/Supplemental/'


def interp(keys, v):
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if v <= b:
            t = (v - a) / (b - a) if b > a else 0
            return va + (vb - va) * t
    return keys[-1][1]


def mesh_obj(name, verts, faces, materials=()):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in materials:
        o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def rod(points, r, material, n=8, name='rod'):
    """Light polyline tube with n sides (kit.tube is far too dense for long cables)."""
    P = [Vector(p) for p in points]; verts = []; faces = []
    ref = Vector((0, 0, 1))
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        if abs(t.dot(ref)) > 0.9:
            ref = Vector((1, 0, 0))
        u = t.cross(ref).normalized(); v = t.cross(u).normalized()
        for k in range(n):
            a = k / n * math.tau
            verts.append(tuple(p + (u * math.cos(a) + v * math.sin(a)) * r))
    for i in range(len(P) - 1):
        for k in range(n):
            faces.append((i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k))
    faces.append(tuple(reversed(range(n)))); faces.append(tuple(range((len(P) - 1) * n, len(P) * n)))
    o = mesh_obj(name, verts, faces, [material])
    return kit.finish(o, None, smooth=60)


def apply_xform(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def tex_mat(name, image, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = image
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


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


def wicker_image(res=256):
    """Basket weave: horizontal weavers passing over and under vertical stakes, shaded so each strand reads round."""
    y, x = np.mgrid[0:res, 0:res] / res
    n = 8                                   # weaver rows / stakes per tile
    row = np.floor(y * n); fy = (y * n) % 1
    stake = np.floor(x * n); fx = (x * n) % 1
    over = ((row + stake) % 2 == 0)
    # the weaver dips where it passes under a stake, rises where it passes over
    rise = np.where(over, np.sin(fx * math.pi), 1 - np.sin(fx * math.pi))
    round_h = np.sin(fy * math.pi) ** 0.5
    shade = round_h * (0.35 + 0.65 * rise)
    gap = (fy < 0.07) | (fy > 0.93)
    stake_show = (~over) & (np.abs(fx - 0.5) < 0.18)           # stake visible between weavers
    rng = np.random.default_rng(3)
    jitter = 0.85 + 0.3 * rng.random(n)[row.astype(int) % n]
    base = np.array([0.66, 0.43, 0.19])
    col = base[None, None, :] * (0.35 + 0.75 * shade)[..., None] * jitter[..., None]
    col[gap] *= 0.3
    col[stake_show & gap] = base * 0.55
    img = np.ones((res, res, 4)); img[..., :3] = np.clip(col, 0, 1)
    im = bpy.data.images.new('wicker', res, res); im.pixels.foreach_set(img.astype(np.float32).ravel()); im.pack()
    return im


# ---------------------------------------------------------------- materials
BAND = {k: kit.mat(c, rough=0.6, name='band_' + k) for k, c in
        (('cardinal', '#8f1d19'), ('orange', '#c9561f'), ('amber', '#dc9128'), ('cream', '#efe3c8'),
         ('walnut', '#4e321e'), ('lamp', '#f6c25a'))}
BAND_ALT = {k: kit.mat(c, rough=0.6, name='band2_' + k) for k, c in
            (('cardinal', '#b8322a'), ('orange', '#e27434'), ('amber', '#efb04c'), ('cream', '#e2d1ad'),
             ('walnut', '#6a4630'), ('lamp', '#f8d27e'))}
ROPE = kit.mat('#3a2a1e', rough=0.8, name='rope')
LEATHER = kit.mat('walnut', rough=0.55, name='leather')
STEEL = kit.mat('steel', rough=0.3, metal=0.9, name='steel')
DARKSTEEL = kit.mat('gunmetal', rough=0.35, metal=0.85, name='darksteel')
FLAME = kit.mat('#ffb347', rough=0.5, emit=3.0, alpha=0.75, name='flame')
WICKER = tex_mat('wicker', wicker_image(), 0.75)
INSIDE = kit.mat('#2a1a10', rough=0.9, name='inside')
LETTER = kit.mat('cardinal', rough=0.5, name='letters')

# ---------------------------------------------------------------- envelope: 12 gores that bulge between load tapes
H = 16.0                                # envelope height
Z0 = 6.4                                # mouth height above the ground
PROF = [(0.00, 1.25), (0.05, 1.55), (0.12, 2.55), (0.22, 3.95), (0.34, 5.25), (0.46, 6.05), (0.58, 6.38), (0.68, 6.32),
        (0.78, 5.85), (0.86, 5.05), (0.92, 4.05), (0.96, 3.0), (0.985, 2.0), (1.0, 1.2)]
NG = 12; SEG = 8
R = lambda f: interp(PROF, f)


def bulge(f):
    return 0.022 * min(1.0, f / 0.15, (1.0 - f) / 0.12)


def surf_r(f, th):
    g = (th / (math.tau / NG)) % 1.0
    return R(f) * (1 + bulge(f) * math.sin(math.pi * g) ** 0.7)


# bands, bottom to top: (top of band as height fraction, colour)
BANDS = [(0.13, 'walnut'), (0.27, 'cardinal'), (0.38, 'orange'), (0.47, 'amber'), (0.61, 'cream'), (0.71, 'amber'),
         (0.80, 'orange'), (0.89, 'cardinal'), (1.01, 'cream')]
edges = sorted(set([0.0, 1.0] + [b for b, _ in BANDS[:-1]] + [i / 44 for i in range(45)]))
fs = []
for f in edges:
    if not fs or f - fs[-1] > 0.004:
        fs.append(f)
NA = NG * SEG
verts, faces, mats = [], [], []
for f in fs:
    for k in range(NA):
        th = k / NA * math.tau
        r = surf_r(f, th)
        verts.append((r * math.sin(th), -r * math.cos(th), Z0 + f * H))
mat_list = []
for k in BAND:
    mat_list += [BAND[k], BAND_ALT[k]]
for i in range(len(fs) - 1):
    fm = (fs[i] + fs[i + 1]) / 2
    band = next(c for top, c in BANDS if fm < top)
    for k in range(NA):
        a = i * NA + k; b = i * NA + (k + 1) % NA
        faces.append((a, b, b + NA, a + NA))
        gore = k // SEG
        mats.append(mat_list.index(BAND[band] if gore % 2 == 0 else BAND_ALT[band]))
env = mesh_obj('envelope', verts, faces, mat_list)
for p, m in zip(env.data.polygons, mats):
    p.material_index = m
# the open mouth: a dark throat cone inside, so you look up into the balloon
throat = kit.lathe([(0.0, Z0 + 1.6), (1.15, Z0 + 0.02), (1.2, Z0 + 0.02)], material=INSIDE, steps=48, name='throat')
kit.finish(env, None, smooth=60)

# load tapes along each gore seam, and the crown ring and vent
for g in range(NG):
    th = g / NG * math.tau
    pts = []
    for f in [i / 30 for i in range(31)]:
        r = surf_r(f, th) + 0.02
        pts.append((r * math.sin(th), -r * math.cos(th), Z0 + f * H))
    rod(pts, 0.05, ROPE, n=6, name='tape')
crown_f = 0.955
kit.torus(R(crown_f) + 0.03, 0.08, at=(0, 0, Z0 + crown_f * H), material=ROPE, major=96, minor=8, name='crownring')
vent_f = 0.99
kit.torus(R(vent_f) + 0.02, 0.07, at=(0, 0, Z0 + vent_f * H + 0.02), material=ROPE, major=64, minor=8, name='ventring')
kit.cyl(R(1.0) + 0.05, 0.12, at=(0, 0, Z0 + H + 0.02), material=BAND['cream'], verts=48, bevel=0.04, name='vent')

# "IYA" wrapped around the cream band, facing the front
for side in (0.0, math.pi):          # on the front, and again on the back so it reads through the spin
    cu = bpy.data.curves.new('iya', 'FONT'); cu.body = 'I Y A'; cu.size = 2.6; cu.extrude = 0.06
    cu.font = bpy.data.fonts.load(FONTS + 'Futura.ttc'); cu.resolution_u = 4; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    iya = bpy.data.objects.new('iya', cu); bpy.context.collection.objects.link(iya)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = iya; iya.select_set(True)
    bpy.ops.object.convert(target='MESH'); iya = bpy.context.object
    iya.data.materials.clear(); iya.data.materials.append(LETTER)
    fc = 0.54
    for v in iya.data.vertices:
        x, y, z = v.co
        f = fc + y / H
        th = x / R(f) + side
        r = surf_r(f, th) + 0.07 + z
        v.co = (r * math.sin(th), -r * math.cos(th), Z0 + f * H)
    iya.data.update()
    kit.finish(iya, None, smooth=30)

# ---------------------------------------------------------------- basket, frame, burner (turned 45 degrees)
B = 3.0; BH = 2.6; BZ = 0.0
ROT = Matrix.Rotation(math.radians(45), 4, 'Z')
parts = []
basket = kit.box((B, B, BH), at=(0, 0, BH / 2), material=WICKER, bevel=0.06, segments=2, name='basket')
box_uv(basket, 0.5)
# hollow it: open top, dark inside walls and floor
inner = kit.box((B - 0.24, B - 0.24, BH), at=(0, 0, BH / 2 + 0.45), material=INSIDE)
md = basket.modifiers.new('cut', 'BOOLEAN'); md.object = inner; md.solver = 'EXACT'; md.material_mode = 'TRANSFER'
bpy.context.view_layer.objects.active = basket
while basket.modifiers.find('cut') > 0:
    bpy.ops.object.modifier_move_up(modifier='cut')
bpy.ops.object.modifier_apply(modifier='cut'); bpy.data.objects.remove(inner, do_unlink=True)
parts.append(basket)
# leather-bound rims top and bottom, corner posts
for z in (BH - 0.06, 0.07):
    rim = kit.box((B + 0.12, B + 0.12, 0.16), at=(0, 0, z), material=LEATHER, bevel=0.06, segments=3, name='rim')
    hole = kit.box((B - 0.2, B - 0.2, 0.5), at=(0, 0, z), material=LEATHER)
    md = rim.modifiers.new('cut', 'BOOLEAN'); md.object = hole; md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = rim
    while rim.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut'); bpy.data.objects.remove(hole, do_unlink=True)
    parts.append(rim)
for sx in (1, -1):
    for sy in (1, -1):
        parts.append(kit.box((0.16, 0.16, BH - 0.1), at=(sx * B / 2, sy * B / 2, BH / 2), material=LEATHER,
                             bevel=0.05, segments=2, name='post'))
# floor visible from above, dark interior
# pyramid frame up to the burner
APEX = BH + 1.35
for sx in (1, -1):
    for sy in (1, -1):
        parts.append(rod([(sx * B / 2, sy * B / 2, BH + 0.02), (sx * 0.42, sy * 0.42, APEX - 0.05)], 0.055, DARKSTEEL,
                         n=12, name='strut'))
parts.append(kit.box((1.0, 1.0, 0.14), at=(0, 0, APEX), material=STEEL, bevel=0.04, segments=2, name='burnerplate'))
for sx in (1, -1):
    parts.append(kit.torus(0.22, 0.07, at=(sx * 0.22, 0, APEX + 0.30), material=STEEL, major=32, minor=10, name='coil'))
    parts.append(kit.cyl(0.14, 0.30, at=(sx * 0.22, 0, APEX + 0.15), material=DARKSTEEL, verts=24, bevel=0.03,
                         name='burner'))
# flame from the burners up into the mouth
flame = kit.lathe([(0.0, 0.0), (0.32, 0.25), (0.42, 0.75), (0.34, 1.6), (0.18, 2.4), (0.0, 3.0)], material=FLAME,
                  steps=32, name='flame')
flame.location = (0, 0, APEX + 0.42)
kit.lathe([(0.0, 0.0), (0.17, 0.2), (0.2, 0.6), (0.12, 1.3), (0.0, 1.8)], at=(0, 0, APEX + 0.42),
          material=kit.mat('#fff2c4', rough=0.5, emit=4.0, name='flamecore'), steps=24, name='flamecore')
# cables from the mouth down to the burner frame
for k in range(8):
    th = (k + 0.5) / 8 * math.tau
    top = (1.15 * math.sin(th), -1.15 * math.cos(th), Z0 + 0.05)
    bot = (0.5 * math.sin(th) * 1.0, -0.5 * math.cos(th) * 1.0, APEX + 0.05)
    rod([bot, top], 0.035, ROPE, n=8, name='cable')
kit.torus(1.2, 0.06, at=(0, 0, Z0 + 0.03), material=STEEL, major=48, minor=8, name='loadring')

# the steering rig, in basket-local coordinates (faces at x = +-B/2, y = +-B/2 before the turn)
# rudder fin: a flat trapezoid standing out of the front-left face
fin = kit.extrude([(0.0, -0.45), (1.75, -0.75), (1.8, 0.62), (0.0, 0.45)], 0.10, material=BAND['cardinal'],
                  bevel=0.03, segments=2, name='fin')
fin.rotation_euler = (math.radians(90), 0, math.radians(180)); fin.location = (-B / 2 - 0.02, 0.045, BH * 0.42)
apply_xform(fin); parts.append(fin)
parts.append(kit.box((0.12, 0.30, 1.15), at=(-B / 2 - 0.04, 0, BH * 0.42), material=DARKSTEEL, bevel=0.03,
                     name='finmount'))
# jet thruster sticking out of the front-right face
thr = kit.lathe([(0.0, 0.0), (0.42, 0.0), (0.46, 0.05), (0.46, 0.95), (0.40, 1.05), (0.30, 1.05), (0.30, 0.85),
                 (0.0, 0.85)], material=STEEL, steps=40, name='thruster')
thr.rotation_euler = (math.radians(90), 0, 0); thr.location = (0, -B / 2 - 0.05, BH * 0.45)
apply_xform(thr); parts.append(thr)
for z in (0.25, 0.65):
    parts.append(kit.torus(0.47, 0.035, at=(0, -B / 2 - 0.05 - z, BH * 0.45), rot=(90, 0, 0), material=DARKSTEEL,
                           major=40, minor=8, name='band'))
jet = kit.lathe([(0.0, 0.0), (0.28, 0.0), (0.22, 0.6), (0.0, 1.3)], material=FLAME, steps=24, name='jet')
jet.rotation_euler = (math.radians(90), 0, 0); jet.location = (0, -B / 2 - 1.08, BH * 0.45)
apply_xform(jet); parts.append(jet)
# curved tail fin rising behind the basket's back corner
tail_pts = []
for i in range(14):
    t = i / 13
    tail_pts.append((0.10 + 1.7 * t ** 1.4, 0.15 + 2.3 * t - 0.8 * t * t))
tail_poly = tail_pts + [(x + 0.62 * (1 - t) + 0.05, y - 0.42 * (1 - t) - 0.05) for (x, y), t in
                        zip(reversed(tail_pts), [1 - i / 13 for i in range(14)])]
tail = kit.extrude(tail_poly, 0.08, material=BAND['cardinal'], bevel=0.025, segments=2, name='tailfin')
tail.rotation_euler = (math.radians(90), 0, math.radians(45)); tail.location = (B / 2 - 0.1, B / 2 - 0.1, BH - 0.35)
apply_xform(tail); parts.append(tail)

for o in parts:
    apply_xform(o)
    o.data.transform(ROT); o.data.update()

kit.export('hot-air-balloon')
