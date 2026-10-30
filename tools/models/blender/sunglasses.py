"""Sunglasses - Brian Lee.

His drawing: chunky acetate sunglasses, open. Angular, rounded-trapezoid lenses shaded dark, a thick rim, a solid bridge set
high, and thick flat temples that step down in height a third of the way back and hook down at the ear. "CHR13" (coHoRt 13)
is lettered along the outer face of the left temple.
Line drawing, so the material is a choice: tortoiseshell acetate (the mural's walnut / honey / amber), gold letter inlay,
smoked brown lenses, silver hinges.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

FONTS = '/System/Library/Fonts/Supplemental/'


def chaikin(pts, n=2, closed=True):
    for _ in range(n):
        out = []
        m = len(pts) if closed else len(pts) - 1
        for i in range(m):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
            out += [tuple(a.lerp(b, 0.25)), tuple(a.lerp(b, 0.75))]
        pts = out if closed else [pts[0]] + out + [pts[-1]]
    return pts


def offset(pts, d):
    """Offset a closed CCW polygon outward by d (miter by averaged normals)."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e1 = (p1 - p0).normalized(); e2 = (p2 - p1).normalized()
        n1 = Vector((e1.y, -e1.x)); n2 = Vector((e2.y, -e2.x))
        nm = (n1 + n2).normalized()
        k = d / max(0.4, nm.dot(n1))
        out.append(tuple(p1 + nm * k))
    return out


def ccw(pts):
    a = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


def cut(target, cutter, op='DIFFERENCE'):
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.use_self = True
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def apply_xform(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def box_uv(o, size):
    """Box-project UVs by each face's dominant axis (no operator context needed)."""
    me = o.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap'); uv.active = True; uv.active_render = True
    for p in me.polygons:
        ax = max(range(3), key=lambda i: abs(p.normal[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = [c for i, c in enumerate(co) if i != ax]
            uv.data[li].uv = (a / size + 0.37 * ax, b / size + 0.61 * ax)


def rotate_about(o, pivot, rz):
    M = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Translation(-Vector(pivot))
    o.data.transform(M); o.data.update()


FRONT_TILT = Matrix.Rotation(math.radians(4), 4, 'Z') @ Matrix.Rotation(math.radians(7), 4, 'X')


# ---------------------------------------------------------------- tortoiseshell texture, made here (no file on disk)
def tortoise_image(res=512, seed=13):
    rng = np.random.default_rng(seed)

    def up(a, n):   # bilinear upsample a small tiling grid to n x n
        g = a.shape[0]
        xs = np.arange(n) * g / n
        i0 = np.floor(xs).astype(int) % g; i1 = (i0 + 1) % g; t = xs - np.floor(xs)
        rows = a[i0] * (1 - t)[:, None] + a[i1] * t[:, None]
        return rows[:, i0] * (1 - t)[None, :] + rows[:, i1] * t[None, :]

    f = np.zeros((res, res))
    for g, w in ((6, 1.0), (12, 0.7), (24, 0.4), (48, 0.2), (96, 0.1)):
        f += w * up(rng.random((g, g)), res)
    streak = np.zeros((res, res))
    for g, w in ((8, 1.0), (32, 0.4)):
        a = rng.random((g, g)); streak += w * up(np.repeat(a[:, :1], g, axis=1) * 0.3 + a * 0.7, res)
    f = (f - f.min()) / (f.max() - f.min()); streak = (streak - streak.min()) / (streak.max() - streak.min())
    v = np.clip((f * 0.7 + streak * 0.3 - 0.30) * 2.1, 0, 1) ** 1.15
    stops = [(0.0, (0.035, 0.016, 0.008)), (0.40, (0.11, 0.045, 0.016)), (0.60, (0.36, 0.17, 0.05)),
             (0.80, (0.70, 0.40, 0.12)), (1.0, (0.88, 0.60, 0.22))]
    img = np.zeros((res, res, 4)); img[..., 3] = 1
    for c in range(3):
        img[..., c] = np.interp(v, [s for s, _ in stops], [col[c] for _, col in stops])
    im = bpy.data.images.new('tortoiseshell', res, res)
    im.pixels.foreach_set(img.astype(np.float32).ravel())
    im.pack()
    return im


def tex_mat(name, image, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = image
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


TORT = tex_mat('tortoiseshell', tortoise_image(), 0.16)
LENS = kit.mat('#2a201b', rough=0.04, metal=0.2, alpha=0.8, name='lens')
GOLD = kit.mat('#d9a43a', rough=0.25, metal=1.0, name='gold')
SILVER = kit.mat('chrome', rough=0.2, metal=1.0, name='silver')

# ---------------------------------------------------------------- front (right half built, then mirrored)
T = 0.0068          # front thickness (depth along Y)
CX = 0.0355         # lens centre from the bridge centre
lens = [(-0.0245, 0.0185), (0.0055, 0.0205), (0.0265, 0.0195), (0.0285, 0.0060), (0.0225, -0.0140),
        (0.0080, -0.0225), (-0.0105, -0.0215), (-0.0225, -0.0110), (-0.0262, 0.0040)]
lens = ccw(chaikin(ccw(lens), 3))
rim = ccw([(x, y + (0.0012 if y > 0.012 else 0)) for x, y in offset(lens, 0.0058)])
lens_c = [(x + CX, y) for x, y in lens]
rim_c = [(x + CX, y) for x, y in rim]

frame = kit.extrude(rim_c, T, name='front')
bridge = kit.extrude(ccw(chaikin([(-0.0005, 0.0045), (0.016, 0.0040), (0.016, 0.0165), (-0.0005, 0.0170)], 1)), T * 0.92,
                     at=(0, 0, T * 0.04), name='bridge')
cut(frame, bridge, 'UNION')
# end piece: the corner block the hinge sits behind
end = kit.extrude(ccw(chaikin([(CX + 0.020, 0.010), (CX + 0.0345, 0.0085), (CX + 0.0345, 0.0235), (CX + 0.012, 0.0270)], 1)),
                  T, name='endpiece')
cut(frame, end, 'UNION')
hole = kit.extrude(lens_c, T * 3, at=(0, 0, -T), name='hole')
cut(frame, hole)
# a shallow groove the lens sits in, so its edge disappears into the rim
frame.data.materials.clear(); frame.data.materials.append(TORT)
md = frame.modifiers.new('bevel', 'BEVEL'); md.width = 0.0011; md.segments = 3; md.limit_method = 'ANGLE'
apply_mods(frame)
lens_o = kit.extrude(offset(lens_c, 0.0009), 0.0018, at=(0, 0, T * 0.35), material=LENS, name='lens')
# nose pad, moulded on behind the rim's inner lower edge
pad = kit.extrude(ccw(chaikin([(0.0095, -0.004), (0.0135, -0.006), (0.0145, -0.017), (0.0115, -0.0185)], 2)), 0.0075,
                  at=(0, 0, T - 0.001), material=TORT, bevel=0.0012, segments=2, name='pad')

half = [frame, lens_o, pad]
for o in half:
    # stand the front up: polygon XY -> world XZ, extrusion -> +Y (backwards), front face at y=0
    o.rotation_euler = (math.radians(90), 0, 0)
    apply_xform(o)
    for v in o.data.vertices:
        v.co.y = -v.co.y          # front face at y = 0, back at y = T
    o.data.flip_normals()
    # gentle wrap: each half turns back 4 degrees about the bridge, plus 7 degrees pantoscopic tilt
    o.data.transform(FRONT_TILT); o.data.update()
    kit.finish(o, None, smooth=40)
    md = o.modifiers.new('mirror', 'MIRROR'); md.use_axis[0] = True; md.use_bisect_axis[0] = True
    md.use_mirror_merge = True; md.merge_threshold = 0.0004
box_uv(frame, 0.06); box_uv(pad, 0.06)


# ---------------------------------------------------------------- temples
def hinge_point(s):
    p = FRONT_TILT @ Vector((CX + 0.0335, T, 0.0178))
    return Vector((s * p.x, p.y, p.z))


TL = 0.138
side = [(0.0, 0.0055), (0.040, 0.0055), (0.050, 0.0030), (0.122, 0.0022), (0.131, -0.0010), (0.150, -0.0320),
        (0.1505, -0.0360), (0.1465, -0.0378), (0.1430, -0.0350), (0.1255, -0.0075), (0.118, -0.0035), (0.052, -0.0035),
        (0.040, -0.0055), (0.0, -0.0055)]
side = ccw(chaikin(side, 2))
for s in (1, -1):
    tw = 0.0046
    temple = kit.extrude(side, tw, name='temple')
    # polygon XY = (back, up) -> world (Y, Z); extrusion -> X
    temple.rotation_euler = (math.radians(90), 0, math.radians(90)); apply_xform(temple)
    temple.data.materials.append(TORT)
    md = temple.modifiers.new('bevel', 'BEVEL'); md.width = 0.0012; md.segments = 3; md.limit_method = 'ANGLE'
    apply_mods(temple)
    h = hinge_point(s)
    # outer face flush with the end piece; splay outward 3 degrees
    temple.location = (h.x - (tw if s > 0 else 0) + (-0.0005 * s), h.y + 0.0004, h.z - 0.0010)
    apply_xform(temple)
    rotate_about(temple, h, -3 * s)          # temples splay out a little
    kit.finish(temple, None, smooth=40)
    box_uv(temple, 0.06)
    # hinge barrel and the metal core line showing at the hinge
    kit.cyl(0.0017, 0.0085, at=(h.x - s * 0.0021, h.y + 0.0004, h.z - 0.001), material=SILVER, verts=16, bevel=0.0004,
            name='hinge')
    if s > 0:
        # "CHR13" inlaid along the outer face of the left temple, reading front to back
        cu = bpy.data.curves.new('chr13', 'FONT'); cu.body = 'CHR13'; cu.size = 0.0072; cu.extrude = 0.00025
        cu.font = bpy.data.fonts.load(FONTS + 'Futura.ttc'); cu.resolution_u = 4
        cu.align_x = 'LEFT'; cu.align_y = 'CENTER'
        t = bpy.data.objects.new('chr13', cu); bpy.context.collection.objects.link(t)
        bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = t; t.select_set(True)
        bpy.ops.object.convert(target='MESH'); t = bpy.context.object
        t.data.materials.clear(); t.data.materials.append(GOLD)
        # text plane XY -> outer face (+X normal): reading +Y, up +Z
        t.rotation_euler = (math.radians(90), 0, math.radians(90))
        t.location = (h.x - 0.0005, h.y + 0.0095, h.z - 0.0010)
        apply_xform(t)
        rotate_about(t, h, -3)

# stand it on z = 0
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
dg = bpy.context.evaluated_depsgraph_get()
zmin = min((o.matrix_world @ v.co).z for o in objs for v in o.evaluated_get(dg).to_mesh().vertices)
for o in objs:
    o.location.z -= zmin

kit.export('sunglasses')
