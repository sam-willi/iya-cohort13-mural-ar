"""Telescope, after Matthew Carlin's drawing (RV P4a).

The drawing: a straight refractor tube with a stepped collar and eyepiece at the back, a short three-legged
tripod meeting under the middle of the tube, and a cone of light out of the front with big block letters "IYA"
standing in it, cut off by the cone's edges. All of that is here; the light is a translucent cone that fades out
and the letters are clipped to it, like the drawing.
Line-only drawing, so materials are a call: cream enamel tube with brass trim and black fittings on a walnut
tabletop tripod (a vintage refractor, in the mural's palette). Added the bits you'd notice up close: dew shield,
lens, tube rings, focuser knobs, an altitude pivot with a lock knob.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Impact.ttf'


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


def set_faces_material(o, mat, test):
    """Give the faces whose centre passes test(center) a second material."""
    if mat.name not in [m.name for m in o.data.materials]:
        o.data.materials.append(mat)
    idx = [m.name for m in o.data.materials].index(mat.name)
    for p in o.data.polygons:
        if test(p.center):
            p.material_index = idx


# ---------------------------------------------------------------- materials
CREAM = kit.mat('#ece0c4', rough=0.38, name='enamel')
BRASS = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
BLACK = kit.mat('#1c1b1a', rough=0.45, name='black_metal')
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')
WALNUT = kit.mat('walnut', rough=0.6, name='walnut')
GLASS = kit.mat('#9cc4d6', rough=0.05, alpha=0.45, name='lens')
LETTER = kit.mat('#dc8a26', rough=0.38, emit=0.12, name='letters')


def beam_material():
    """Warm light that fades out along the cone (alpha from a small generated gradient texture)."""
    img = bpy.data.images.new('beam_fade', 4, 128, alpha=True)
    px = []
    for j in range(128):
        v = j / 127
        a = 0.30 * (1 - v ** 1.5) * (1 - 0.4 * v)
        px += [1, 1, 1, a] * 4
    img.pixels = px
    img.pack()
    m = bpy.data.materials.new('beam'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = kit.hex_rgb('#ffdf9a')
    b.inputs['Roughness'].default_value = 0.6
    b.inputs['Emission Color'].default_value = kit.hex_rgb('#ffdf9a')
    b.inputs['Emission Strength'].default_value = 0.6
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img; t.extension = 'EXTEND'
    uvn = m.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
    m.node_tree.links.new(uvn.outputs['UV'], t.inputs['Vector'])
    m.node_tree.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    m.surface_render_method = 'BLENDED'
    m.use_backface_culling = False
    return m


# ---------------------------------------------------------------- the optical tube, built along +Z (s), then aimed
TILT = 22.0
D = Vector((math.cos(math.radians(TILT)), 0, math.sin(math.radians(TILT))))   # tube axis
N = Vector((-math.sin(math.radians(TILT)), 0, math.cos(math.radians(TILT))))  # "up" across the tube
Z_HUB = 0.33
PIVOT = Vector((0, 0, Z_HUB + 0.034))
M = PIVOT + N * 0.070
AIM = Matrix.Translation(M) @ Matrix.Rotation(math.radians(90 - TILT), 4, 'Y')
# in the tube's frame, local +X points down (toward the tripod)

ota = []
R_T = 0.040
ota.append(kit.lathe(fillet([(0, -0.27), (R_T, -0.27), (R_T, 0.30), (0, 0.30)], 0), material=CREAM, steps=64, name='tube'))
# back cell / collar (the step in the drawing) and front trim ring
ota.append(kit.lathe(fillet([(0, -0.305), (0.044, -0.305), (0.047, -0.300), (0.047, -0.262), (0.042, -0.258), (0, -0.258)],
                            [0, 0.002, 0.002, 0.002, 0.002, 0], n=3), material=BRASS, steps=64, name='collar'))
ota.append(kit.lathe(fillet([(0.039, -0.25), (0.0418, -0.25), (0.0418, -0.243), (0.039, -0.243)], 0), material=BRASS, steps=64, name='band'))
# focuser body + drawtube + eyepiece + eyecup
ota.append(kit.lathe(fillet([(0, -0.360), (0.024, -0.360), (0.026, -0.355), (0.026, -0.312), (0.030, -0.308), (0.030, -0.300), (0, -0.300)],
                            [0, 0.002, 0.002, 0.002, 0.002, 0.001, 0], n=2), material=BLACK, steps=48, name='focuser'))
ota.append(kit.lathe(fillet([(0, -0.425), (0.0165, -0.425), (0.0165, -0.392), (0.0185, -0.390), (0.0185, -0.378), (0.0150, -0.375),
                             (0.0150, -0.355), (0, -0.355)], [0, 0.002, 0.001, 0.001, 0.001, 0.001, 0, 0], n=2),
                     material=BLACK, steps=48, name='eyepiece'))
ota.append(kit.lathe(fillet([(0, -0.432), (0.0155, -0.432), (0.0155, -0.448), (0.0195, -0.450), (0.0205, -0.444), (0.0200, -0.423),
                             (0, -0.423)], [0, 0, 0.001, 0.002, 0.002, 0.002, 0], n=2), material=RUBBER, steps=48, name='eyecup'))
ota.append(kit.lathe([(0.0168, -0.392), (0.0178, -0.392), (0.0178, -0.385), (0.0168, -0.385)], material=BRASS, steps=48, name='epring'))
for sy in (-1, 1):   # rack-and-pinion focus knobs, under the axis on both sides
    k = kit.cyl(0.0105, 0.012, at=(0.016, sy * 0.034, -0.333), rot=(90, 0, 0), material=BRASS, verts=18, bevel=0.0012, name='knob')
    ota.append(k)
    ota.append(kit.cyl(0.004, 0.010, at=(0.016, sy * 0.025, -0.333), rot=(90, 0, 0), material=BLACK, verts=12, name='shaft'))
ota.append(kit.box((0.012, 0.040, 0.030), at=(0.026, 0, -0.333), material=BLACK, bevel=0.002, name='rack'))
# dew shield: cream outside, black inside, brass lip
dew = kit.lathe(fillet([(0.0395, 0.290), (0.0445, 0.290), (0.0445, 0.394), (0.0465, 0.396), (0.0465, 0.402), (0.0415, 0.402),
                        (0.0415, 0.300), (0.0395, 0.300)], [0, 0.002, 0.0008, 0.0008, 0.0008, 0.0008, 0, 0], n=2),
                material=CREAM, steps=64, name='dew')
set_faces_material(dew, BLACK, lambda c: math.hypot(c.x, c.y) < 0.0425 and c.z > 0.301)
set_faces_material(dew, BRASS, lambda c: c.z > 0.3935 and math.hypot(c.x, c.y) > 0.0425)
ota.append(dew)
# objective: black cell, convex glass, brass retaining ring
ota.append(kit.cyl(0.0416, 0.004, at=(0, 0, 0.302), material=BLACK, verts=48, name='cell'))
ota.append(kit.lathe([(0, 0.3205), (0.020, 0.3195), (0.0405, 0.3165), (0.0405, 0.3045), (0, 0.3045)], material=GLASS, steps=48, name='lens'))
ota.append(kit.lathe(fillet([(0.0335, 0.3165), (0.0414, 0.3165), (0.0414, 0.3215), (0.0335, 0.3215)], 0.0008, n=2, closed=True),
                     material=BRASS, steps=48, name='retainer'))
# tube rings with clamp knobs on top, standing on a dovetail saddle underneath
for s in (-0.075, 0.105):
    ota.append(kit.lathe(fillet([(0.0395, s - 0.009), (0.0455, s - 0.009), (0.0455, s + 0.009), (0.0395, s + 0.009)], 0.0015, n=2, closed=True),
                         material=BLACK, steps=48, name='ring'))
    ota.append(kit.box((0.012, 0.016, 0.018), at=(-0.049, 0, s), material=BLACK, bevel=0.002, name='clamp'))
    ota.append(kit.cyl(0.0075, 0.010, at=(-0.059, 0, s), rot=(0, 90, 0), material=BRASS, verts=16, bevel=0.001, name='ringknob'))
    ota.append(kit.box((0.012, 0.020, 0.020), at=(0.049, 0, s), material=BLACK, bevel=0.002, name='ringfoot'))
ota.append(kit.box((0.012, 0.030, 0.26), at=(0.058, 0, 0.015), material=BLACK, bevel=0.002, name='saddle'))
ota.append(kit.box((0.022, 0.036, 0.050), at=(0.069, 0, 0.0), material=BLACK, bevel=0.003, name='altblock'))
for o in ota:
    o.matrix_world = AIM @ o.matrix_world

# ---------------------------------------------------------------- the light cone, and the IYA letters standing in it
S0, LB = 0.402, 0.58
R0, SLOPE = 0.0415, math.tan(math.radians(11))


def cone_mesh(name, k=1.0, caps=False, uv=False, segs=48, rings=8):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = []
    for j in range(rings + 1):
        t = j / rings; s = S0 + LB * t; r = (R0 + LB * t * SLOPE) * k
        rows.append([bm.verts.new((r * math.cos(a * math.tau / segs), r * math.sin(a * math.tau / segs), s)) for a in range(segs)])
    faces = []
    for j in range(rings):
        for a in range(segs):
            b = (a + 1) % segs
            faces.append((bm.faces.new((rows[j][a], rows[j][b], rows[j + 1][b], rows[j + 1][a])), j, a))
    if caps:
        bm.faces.new(list(reversed(rows[0]))); bm.faces.new(rows[-1])
    if uv:
        lay = bm.loops.layers.uv.new('UVMap')
        for f, j, a in faces:
            for l in f.loops:
                jj = round((l.vert.co.z - S0) / LB * rings)
                l[lay].uv = (0.5, jj / rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.matrix_world = AIM
    return o


beam = cone_mesh('beam', uv=True)
beam.data.materials.append(beam_material())
for p in beam.data.polygons:
    p.use_smooth = True

letters = []
for ch, sp, cap in (('I', 0.125, 0.150), ('Y', 0.258, 0.205), ('A', 0.447, 0.265)):
    c = M + D * (S0 + sp)
    o = ftext(ch, cap / 0.528, 0.040, at=(c.x, 0, c.z), rot=(90, 0, 0), material=LETTER, bevel=0.0025, name='letter_' + ch)
    letters.append(o)
word = bake_join('IYA', letters)
clip = cone_mesh('clip', k=0.965, caps=True, rings=1)
kit.boolean(word, clip, 'INTERSECT')
kit.finish(word, smooth=30)

# ---------------------------------------------------------------- tripod: fork, hub, three walnut legs
kit.cyl(0.034, 0.006, at=(0, 0, Z_HUB + 0.003), material=BLACK, verts=40, bevel=0.0015, name='forkbase')
for sy in (-1, 1):
    kit.extrude(fillet([(-0.026, 0), (0.026, 0), (0.016, 0.040), (-0.016, 0.040)], [0, 0, 0.012, 0.012], n=4, closed=True),
                0.006, at=(0, sy * 0.021 + 0.003, Z_HUB + 0.006), rot=(90, 0, 0), material=BLACK, bevel=0.0012, name='fork')
rod(PIVOT + Vector((0, -0.040, 0)), PIVOT + Vector((0, 0.030, 0)), 0.0065, material=BRASS, verts=20, name='bolt')
kit.cyl(0.016, 0.012, at=PIVOT + Vector((0, -0.044, 0)), rot=(90, 0, 0), material=BRASS, verts=24, bevel=0.002, name='lockknob')
for a in range(8):   # grip flutes on the lock knob
    ang = a * math.tau / 8
    kit.cyl(0.0035, 0.012, at=PIVOT + Vector((0.016 * math.cos(ang), -0.044, 0.016 * math.sin(ang))), rot=(90, 0, 0),
            material=BRASS, verts=10, name='flute')
kit.cyl(0.008, 0.006, at=PIVOT + Vector((0, 0.033, 0)), rot=(90, 0, 0), material=BRASS, verts=16, bevel=0.001, name='nut')
hub = kit.lathe(fillet([(0, Z_HUB - 0.034), (0.030, Z_HUB - 0.034), (0.038, Z_HUB - 0.026), (0.038, Z_HUB), (0, Z_HUB)],
                       [0, 0.003, 0.003, 0.002, 0], n=2), material=BRASS, steps=48, name='hub')

LEG_SPLAY, R_LEG = 26.0, 0.0125
for az in (180, 60, -60):
    a = math.radians(az)
    out = Vector((math.cos(a), math.sin(a), 0))
    top = Vector((0, 0, Z_HUB - 0.016)) + out * 0.040
    dirv = (out * math.sin(math.radians(LEG_SPLAY)) + Vector((0, 0, -math.cos(math.radians(LEG_SPLAY))))).normalized()
    L = (top.z - 0.020) / -dirv.z
    foot = top + dirv * L
    # hinge lug on the hub, and the leg pinned into it
    side = Vector((-math.sin(a), math.cos(a), 0))
    lug = kit.box((0.022, 0.016, 0.026), at=top - Vector((0, 0, 0.002)) - out * 0.004, rot=(0, 0, az), material=BRASS, bevel=0.002, name='lug')
    rod(top - side * 0.0115, top + side * 0.0115, 0.0045, material=BLACK, verts=12, name='pin')
    rod(top + dirv * 0.004, foot - dirv * 0.004, R_LEG, material=WALNUT, verts=20, bevel=0.002, name='leg')
    rod(foot - dirv * 0.026, foot + dirv * 0.002, R_LEG + 0.0012, material=BRASS, verts=20, bevel=0.0012, name='ferrule')
    rod(foot, foot + dirv * 0.020, R_LEG - 0.0015, material=RUBBER, verts=20, bevel=0.003, name='tip')

# ---------------------------------------------------------------- join, settle and export
solid = bake_join('telescope', [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name not in ('beam',)])
both = bake_join('telescope', [solid, beam])
settle(both)
kit.export('telescope')
