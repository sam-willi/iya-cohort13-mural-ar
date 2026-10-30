"""Office chair, after Sophie Ogawa's drawing (RV P5a).

The drawing: a grand, throne-like armchair on casters. Tall upholstered back with two studded trim bands and a
seam across the middle, its frame wrapped in a carved vine and topped by a crest of big sweeping leaves; a plush
seat with a rolled front; hoop-shaped arms with "C13" and rib grooves carved along them, each ending in a cat's
head at the front; square fluted legs on twin-wheel casters, with a stretcher between the legs.
Line-only drawing, so materials are a call for a boss's chair in the mural's palette: carved walnut, cardinal
velvet, gilt C13 letters and brass nailheads, honey-wood cat heads with black eyes. The back of the chair isn't
drawn: it's the walnut frame and a plain velvet back with the same trim.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

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


def ftext(s, size, depth, material=None, bevel=0.0, res=5, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res
    if bevel:
        cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.offset = -bevel
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
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


def ltube(points, r, material=None, res_u=3, bevel_res=1, name='tube'):
    """A lighter tube than kit.tube: fewer sides and samples, for small carved details."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('NURBS'); sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*c, 1)
    sp.use_endpoint_u = True; sp.order_u = min(4, len(points))
    cu.bevel_depth = r; cu.bevel_resolution = bevel_res; cu.resolution_u = res_u; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def mesh_obj(name, verts, faces, material=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = smooth
    return o


def apply_mods(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    return o


def tex_mat(name, img, rough=0.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img
    uvn = m.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
    m.node_tree.links.new(uvn.outputs['UV'], t.inputs['Vector'])
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


def srgb_lin(c):
    return [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c]


def kit_hex(h):
    h = kit.PALETTE.get(h, h).lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def wood_image(name, light, dark, seed=3, n=512, lines=70):
    import numpy as np
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, n)[:, None]; u = np.linspace(0, 1, n)[None, :]
    warp = 0.006 * np.sin(u * math.tau * 1.3 + 0.7) + 0.003 * np.sin(u * math.tau * 3.7 + 2.0)
    phase = (v + warp) * lines + 1.5 * np.sin(v * math.tau * 2 + 1.0) + 0.8 * np.sin(v * math.tau * 5 + 0.3)
    g = (0.5 + 0.5 * np.sin(phase * math.tau)) ** 4
    streak = np.convolve(rng.normal(0, 1, n), np.ones(9) / 9, mode='same')[:, None] * 0.25
    t = np.clip(0.38 * g + 0.22 + streak * 0.8 + rng.normal(0, 0.03, (n, n)), 0, 1)
    L = np.array(srgb_lin(kit_hex(light))); D = np.array(srgb_lin(kit_hex(dark)))
    rgb = L[None, None, :] * (1 - t[..., None]) + D[None, None, :] * t[..., None]
    rgba = np.concatenate([rgb, np.ones((n, n, 1))], axis=2).astype(np.float32)
    img = bpy.data.images.new(name, n, n, alpha=False)
    img.pixels.foreach_set(rgba.ravel()); img.pack()
    return img


def wood_uv(o, scale=2.0, along='z'):
    """Apply modifiers and project UVs per face so the grain runs along `along` (world axis)."""
    apply_mods(o)
    me = o.data; mw = o.matrix_world
    lay = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = (mw.to_3x3() @ p.normal); ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            other = [i for i in range(3) if i != ax]
            a, b = co[other[0]], co[other[1]]
            # grain (the texture's u direction) follows `along` when it lies in this face
            gi = 'xyz'.index(along)
            if gi == other[0]:
                uv = (a, b)
            elif gi == other[1]:
                uv = (b, a)
            else:
                uv = (a, b)
            lay.data[li].uv = (uv[0] * scale, uv[1] * scale)
    return o


# ---------------------------------------------------------------- materials
WOOD = tex_mat('walnut', wood_image('walnut_grain', '#6e4427', '#3c2312', lines=60), rough=0.45)
WOOD_PLAIN = kit.mat('#5a3a22', rough=0.5, name='walnut_plain')
VELVET = kit.mat('#8c1f1b', rough=0.8, name='velvet')
VELVET_DK = kit.mat('#621512', rough=0.85, name='velvet_seam')
TRIM = kit.mat('#d6a24a', rough=0.6, name='gimp_trim')
BRASS = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
GILT = kit.mat('#d4a64a', rough=0.3, metal=0.85, name='gilt')
HONEY = kit.mat('#c8893d', rough=0.5, name='honey_wood')
EYE = kit.mat('#141210', rough=0.2, name='eye')
NOSE = kit.mat('#5a2a20', rough=0.4, name='nose')
WHEEL = kit.mat('#2a2522', rough=0.55, name='wheel')

# ---------------------------------------------------------------- legs on casters, stretchers, seat frame
LX, LY, LEG = 0.300, 0.240, 0.056
Z_FRAME0, Z_FRAME1 = 0.360, 0.440
Z_LEG0 = 0.090
wood_parts = []
for sx in (-1, 1):
    for sy in (-1, 1):
        leg = kit.box((LEG, LEG, Z_FRAME0 + 0.02 - Z_LEG0), at=(sx * LX, sy * LY, (Z_FRAME0 + 0.02 + Z_LEG0) / 2), material=WOOD, name='leg')
        for v in leg.data.vertices:          # taper toward the foot
            if v.co.z < 0:
                v.co.x *= 0.80; v.co.y *= 0.80
        # flutes down the two outward faces
        cut = []
        for k in (-1, 1):
            cut.append(kit.box((0.006, 0.02, 0.22), at=(sx * LX + k * 0.011, sy * LY + sy * 0.026, 0.245), rot=(sy * -1.0, 0, 0), name='flute'))
            cut.append(kit.box((0.02, 0.006, 0.22), at=(sx * LX + sx * 0.026, sy * LY + k * 0.011, 0.245), rot=(0, sx * 1.0, 0), name='flute'))
        cutter = bake_join('flutes', cut)
        kit.boolean(leg, cutter)
        kit.finish(leg, bevel=0.006, segments=2)
        wood_parts.append(leg)
        # caster: brass socket and yoke, twin wheels
        x, y = sx * LX, sy * LY
        kit.cyl(0.023, 0.024, at=(x, y, Z_LEG0 - 0.008), material=BRASS, verts=16, bevel=0.003, name='socket')
        kit.cyl(0.010, 0.016, at=(x, y, Z_LEG0 - 0.026), material=BRASS, verts=16, name='stem')
        kit.box((0.016, 0.040, 0.010), at=(x, y, 0.055), material=BRASS, bevel=0.003, name='yoke')
        rod((x - 0.030, y, 0.027), (x + 0.030, y, 0.027), 0.0045, material=BRASS, verts=12, name='axle')
        for k in (-1, 1):
            w = kit.lathe(fillet([(0.004, -0.0065), (0.022, -0.0065), (0.027, -0.002), (0.027, 0.002), (0.022, 0.0065), (0.004, 0.0065)],
                                 [0, 0.002, 0.002, 0.002, 0.002, 0], n=1), material=WHEEL, steps=20, name='wheel')
            w.location = (x + k * 0.020, y, 0.027); w.rotation_euler = (0, math.radians(90), 0)
            kit.cyl(0.009, 0.0142, at=(x + k * 0.020, y, 0.027), rot=(0, 90, 0), material=BRASS, verts=10, name='hubcap')
# H-stretcher: gently arched side rails, a turned cross rail
for sx in (-1, 1):
    pts = [(sx * LX * 0.94, -LY, 0.170), (sx * LX * 0.95, -LY * 0.5, 0.185), (sx * LX * 0.96, 0, 0.190), (sx * LX * 0.95, LY * 0.5, 0.185),
           (sx * LX * 0.94, LY, 0.170)]
    wood_parts.append(ltube(pts, 0.012, material=WOOD, res_u=6, bevel_res=2, name='stretcher'))
rail = kit.lathe(fillet([(0, -LX * 0.94), (0.010, -LX * 0.94), (0.010, -0.18), (0.016, -0.15), (0.012, -0.12), (0.012, 0.12), (0.016, 0.15),
                         (0.010, 0.18), (0.010, LX * 0.94), (0, LX * 0.94)], [0, 0, 0.004, 0.006, 0.004, 0.004, 0.006, 0.004, 0, 0], n=3),
                 material=WOOD, steps=20, name='crossrail')
rail.location = (0, 0, 0.190); rail.rotation_euler = (0, math.radians(90), 0)
wood_parts.append(rail)
# seat frame (apron) with a carved bead along its bottom edge
frame = kit.box((0.70, 0.57, Z_FRAME1 - Z_FRAME0), at=(0, 0, (Z_FRAME0 + Z_FRAME1) / 2), material=WOOD, bevel=0.010, segments=3, name='apron')
wood_parts.append(frame)
for sy in (-1, 1):
    wood_parts.append(rod((-0.345, sy * 0.287, Z_FRAME0 + 0.012), (0.345, sy * 0.287, Z_FRAME0 + 0.012), 0.006, material=WOOD, verts=12, name='bead'))
for sx in (-1, 1):
    wood_parts.append(rod((sx * 0.352, -0.28, Z_FRAME0 + 0.012), (sx * 0.352, 0.28, Z_FRAME0 + 0.012), 0.006, material=WOOD, verts=12, name='bead'))

# ---------------------------------------------------------------- seat cushion: domed, rolled front, three channel seams
SEAT_T = 0.528
cush = kit.box((0.600, 0.560, 0.090), at=(0, -0.010, Z_FRAME1 + 0.040), material=VELVET, name='cushion')
md = cush.modifiers.new('bevel', 'BEVEL'); md.width = 0.035; md.segments = 5; md.limit_method = 'NONE'
apply_mods(cush)
md = cush.modifiers.new('sub', 'SUBSURF'); md.levels = 1
apply_mods(cush)
for v in cush.data.vertices:             # dome the top and roll the front edge forward
    x, y, z = v.co
    if z > Z_FRAME1 + 0.040:
        k = (z - (Z_FRAME1 + 0.040)) / 0.045
        v.co.z += 0.022 * k * (1 - (x / 0.30) ** 2) * (1 - ((y + 0.01) / 0.29) ** 2)
    if y < -0.20:
        v.co.y -= 0.012 * max(0, 1 - abs(z - (Z_FRAME1 + 0.055)) / 0.05)
for x in (-0.098, 0.0, 0.098):
    g = kit.box((0.012, 0.50, 0.03), at=(x, 0.0, SEAT_T + 0.026), rot=(0, 45, 0), name='seam')
    kit.boolean(cush, g)
kit.finish(cush, smooth=60)
for x in (-0.098, 0.0, 0.098):          # piping laid in each seam
    pts = [(x, y, Z_FRAME1 + 0.085 - 0.011 + 0.022 * (1 - (x / 0.30) ** 2) * (1 - ((y + 0.01) / 0.29) ** 2)) for y in
           [(-0.22 + 0.44 * k / 10) for k in range(11)]]
    ltube(pts, 0.0045, material=VELVET_DK, res_u=3, bevel_res=1, name='piping')

# ---------------------------------------------------------------- back: tilted frame, padded panel, studded trim, carved vine and crest
TILT = 7.0
PIV = Vector((0, LY, Z_FRAME1))
BACK = Matrix.Translation(PIV) @ Matrix.Rotation(math.radians(-TILT), 4, 'X') @ Matrix.Translation(-PIV)
back = []
for sx in (-1, 1):
    st = kit.box((0.052, 0.052, 0.80), at=(sx * LX, LY, Z_FRAME0 + 0.40), material=WOOD, bevel=0.008, segments=2, name='stile')
    back.append(st)
top_rail = kit.box((0.64, 0.050, 0.060), at=(0, LY, 1.135), material=WOOD, bevel=0.010, segments=2, name='toprail')
back.append(top_rail)
panel = kit.box((0.55, 0.070, 0.64), at=(0, LY - 0.012, 0.815), material=VELVET, name='panel')
md = panel.modifiers.new('bevel', 'BEVEL'); md.width = 0.028; md.segments = 4; md.limit_method = 'NONE'
apply_mods(panel)
for v in panel.data.vertices:             # pad the front of the panel
    if v.co.y < LY - 0.03:
        v.co.y -= 0.018 * (1 - (v.co.x / 0.28) ** 2) * (1 - ((v.co.z - 0.815) / 0.33) ** 2)
seam = kit.box((0.60, 0.03, 0.012), at=(0, LY - 0.064, 0.795), rot=(45, 0, 0), name='seam')
kit.boolean(panel, seam)
kit.finish(panel, smooth=60)
back.append(panel)
# two trim bands with nailheads (the dotted bands in the drawing)
for bx in (-0.092, 0.092):
    pts = []
    for k in range(13):
        z = 0.53 + 0.57 * k / 12
        y = LY - 0.047 - 0.018 * (1 - (bx / 0.28) ** 2) * (1 - ((z - 0.815) / 0.33) ** 2) - 0.0035
        pts.append((bx, y, z))
    strip = ltube(pts, 0.006, material=TRIM, res_u=2, bevel_res=1, name='trim')
    cy_ = pts[6][1]
    strip.data.transform(Matrix.Translation((bx, cy_, 0)) @ Matrix.Diagonal((2.1, 0.55, 1.0, 1.0)) @ Matrix.Translation((-bx, -cy_, 0)))
    back.append(strip)
    for k in range(16):
        z = 0.545 + 0.54 * k / 15
        y = LY - 0.047 - 0.018 * (1 - (bx / 0.28) ** 2) * (1 - ((z - 0.815) / 0.33) ** 2) - 0.007
        back.append(kit.sphere(0.0050, at=(bx, y, z), material=BRASS, segs=8, rings=4, name='nail'))
# the same bands on the back of the panel, so the back isn't bare
for bx in (-0.092, 0.092):
    for k in range(12):
        z = 0.56 + 0.52 * k / 11
        back.append(kit.sphere(0.0045, at=(bx, LY + 0.0245, z), material=BRASS, segs=8, rings=4, name='nail'))
# carved vine twisting up the front of each stile, with small leaves and curls
for sx in (-1, 1):
    pts = [(sx * LX + 0.013 * math.sin(k * 0.9), LY - 0.029, 0.47 + 0.64 * k / 20) for k in range(21)]
    back.append(ltube(pts, 0.0055, material=WOOD_PLAIN, res_u=3, bevel_res=1, name='vine'))
    for k in range(2, 20, 3):
        x0 = sx * LX + 0.013 * math.sin(k * 0.9); z0 = 0.47 + 0.64 * k / 20
        side = 1 if math.cos(k * 0.9) > 0 else -1
        back.append(kit.sphere(0.010, at=(x0 + side * 0.008, LY - 0.0275, z0 + 0.010), scale=(0.95, 0.30, 0.45), material=WOOD_PLAIN,
                               segs=8, rings=4, name='vineleaf'))
        back[-1].rotation_euler = (0, math.radians(side * -35), 0)


def leaf(path, width, thick, material, cup=0.25, twist=0.0):
    """A carved leaf: a ribbon along `path` (list of Vectors), lens-shaped width, cupped, with thickness."""
    n = len(path) - 1; m = 4
    verts, faces = [], []
    for i, p in enumerate(path):
        t = i / n
        tang = (path[min(i + 1, n)] - path[max(i - 1, 0)]).normalized()
        side = tang.cross(Vector((0, 1, 0))).normalized()
        w = width * (math.sin(math.pi * min(t * 1.05 + 0.04, 1.0)) ** 0.8)
        for j in range(-m, m + 1):
            s = j / m
            off = side * (s * w) + Vector((0, -1, 0)) * (cup * w * s * s) + Vector((0, twist * s * w * t, 0))
            verts.append(tuple(p + off))
    row = 2 * m + 1
    for i in range(n):
        for j in range(row - 1):
            a = i * row + j
            faces.append((a, a + 1, a + 1 + row, a + row))
    o = mesh_obj('leaf', verts, faces, material=material)
    md = o.modifiers.new('solid', 'SOLIDIFY'); md.thickness = thick; md.offset = 0
    rib = ltube([tuple(p + Vector((0, -thick * 0.5, 0))) for p in path[:-1]], thick * 0.4, material=material, res_u=2, bevel_res=1, name='midrib')
    return [o, rib]


CY = LY - 0.004
def arc_path(x0, z0, x1, z1, lift, curl, n=14):
    pts = []
    for k in range(n + 1):
        t = k / n
        x = x0 + (x1 - x0) * t
        z = z0 + (z1 - z0) * t + lift * math.sin(math.pi * t) - curl * max(0, t - 0.75) ** 2 * 16
        pts.append(Vector((x, CY, z)))
    return pts


for sx in (-1, 1):
    back += leaf(arc_path(sx * 0.01, 1.165, sx * 0.36, 1.150, 0.065, 0.020), 0.052, 0.012, WOOD_PLAIN)     # long sweep to the corner
    back += leaf(arc_path(sx * 0.02, 1.175, sx * 0.22, 1.215, 0.055, -0.012), 0.036, 0.010, WOOD_PLAIN)   # shorter leaf over it, tip curling up
back += leaf([Vector((0.0, CY, 1.150 + 0.11 * k / 10)) + Vector((0.012 * math.sin(k * 0.6), 0, 0)) for k in range(11)], 0.030, 0.011, WOOD_PLAIN)
for o in back:
    o.matrix_world = BACK @ o.matrix_world

# ---------------------------------------------------------------- hoop arms with rib grooves, gilt C13, cat heads
AX, AW = 0.332, 0.054           # arm centre x and width
RC = Vector((0, -0.012, Z_FRAME1 - 0.003))
RO, RI = 0.262, 0.204


def hoop(sx):
    def band_poly(ro, ri, th0, th1, n=48):
        n = 36
        prof = [(ro * math.cos(th0 + (th1 - th0) * k / n), ro * math.sin(th0 + (th1 - th0) * k / n)) for k in range(n + 1)]
        prof += [(ri * math.cos(th0 + (th1 - th0) * k / n), ri * math.sin(th0 + (th1 - th0) * k / n)) for k in range(n, -1, -1)]
        return prof
    yz_to_world = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # polygon (y, z), extruded along x
    band = kit.extrude(band_poly(RO, RI, 0.0, math.pi), AW, material=WOOD, name='arm')
    band.matrix_world = Matrix.Translation((sx * AX - AW / 2, RC.y, RC.z)) @ yz_to_world
    cut = []
    for deg in list(range(14, 64, 9)) + list(range(118, 172, 9)):    # rib grooves, the top left clear for C13
        t = math.radians(deg)
        c = RC + Vector((0, (RO + RI) / 2 * math.cos(t), (RO + RI) / 2 * math.sin(t)))
        g = kit.box((AW + 0.03, 0.0055, RO - RI + 0.03), at=(sx * AX, c.y, c.z), name='groove')
        g.rotation_euler = (t - math.pi / 2, 0, 0)
        cut.append(g)
    kit.boolean(band, bake_join('grooves', cut))
    kit.finish(band, bevel=0.0065, segments=2)
    # a slimmer core inside, so the grooves read as carved rings a few millimetres deep
    rm, half = (RO + RI) / 2, (RO - RI) / 2 * 0.74
    core = kit.extrude(band_poly(rm + half, rm - half, math.radians(3), math.radians(177)), AW - 0.011, material=WOOD, name='armcore')
    core.matrix_world = Matrix.Translation((sx * AX - (AW - 0.011) / 2, RC.y, RC.z)) @ yz_to_world
    kit.finish(core, bevel=0.003)
    return [band, core]


arms = []
for sx in (-1, 1):
    arms += hoop(sx)
    # C13 along the top of the hoop, on the outward face, gilt
    order = ('C', '1', '3') if sx < 0 else ('3', '1', 'C')
    for ch, dth in zip(order, (-0.20, 0.0, 0.20)):
        t = math.pi / 2 + dth
        rm = (RO + RI) / 2
        up = Vector((0, math.cos(t), math.sin(t)))
        tang = Vector((0, -math.sin(t), math.cos(t))) if sx < 0 else Vector((0, math.sin(t), -math.cos(t)))
        face = tang.cross(up)
        o = ftext(ch, 0.034 / 0.515, 0.004, material=GILT, bevel=0.0007, res=3, name='c13')
        rotm = Matrix((tang, up, face)).transposed().to_4x4()
        pos = RC + up * rm + Vector((sx * (AX + AW / 2), 0, 0)) + up * 0.0015
        o.matrix_world = Matrix.Translation(pos) @ rotm
        arms.append(o)


def cat_head(sx):
    parts = []
    c = Vector((sx * AX, RC.y - (RO + RI) / 2 - 0.012, Z_FRAME1 + 0.040))
    head = kit.sphere(0.050, at=c + Vector((0, 0, 0.004)), scale=(1.0, 0.86, 0.88), material=HONEY, segs=28, rings=14, name='cathead')
    parts.append(head)
    for ex in (-1, 1):
        # ears
        ear = kit.cyl(0.020, 0.032, r2=0.002, at=c + Vector((ex * 0.026, 0.004, 0.040)), material=HONEY, verts=12, name='ear')
        ear.rotation_euler = (math.radians(-8), math.radians(ex * 22), 0)
        parts.append(ear)
        inner = kit.cyl(0.011, 0.020, r2=0.001, at=c + Vector((ex * 0.026, -0.006, 0.039)), material=NOSE, verts=10, name='earin')
        inner.rotation_euler = (math.radians(-8), math.radians(ex * 22), 0)
        parts.append(inner)
        # eyes
        parts.append(kit.sphere(0.0085, at=c + Vector((ex * 0.018, -0.034, 0.008)), scale=(0.8, 0.6, 1.0), material=EYE, segs=12, rings=8, name='eye'))
        # muzzle pads and whiskers
        parts.append(kit.sphere(0.012, at=c + Vector((ex * 0.010, -0.037, -0.012)), material=HONEY, segs=12, rings=8, name='muzzle'))
        for wz in (-0.004, 0.003):
            parts.append(rod(c + Vector((ex * 0.020, -0.036, -0.012 + wz)), c + Vector((ex * 0.058, -0.030, -0.010 + wz * 3)), 0.0011,
                             material=EYE, verts=6, name='whisker'))
    parts.append(kit.sphere(0.0065, at=c + Vector((0, -0.045, -0.003)), scale=(1.2, 0.7, 0.8), material=NOSE, segs=12, rings=8, name='nose'))
    return parts


for sx in (-1, 1):
    arms += cat_head(sx)

# ---------------------------------------------------------------- grain UVs on the walnut parts, join, settle, export
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    if any(m and m.name == 'walnut' for m in o.data.materials):
        wood_uv(o, 2.0, along='z' if o.name.startswith(('leg', 'stile')) else 'x')
chair = bake_join('office_chair')
settle(chair)
kit.export('office-chair')
