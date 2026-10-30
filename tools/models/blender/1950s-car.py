"""Car (50s) - Alene Abdulian.

Her drawing: a long-hooded 1950s sedan. Hooded round headlights at the front corners, an oval grille with vertical bars,
a wraparound bumper, wraparound windshield, two side windows, a flat roof with "IYA" across it, "Cohort 13" in script
along the hood, small tail fins, deep-set wheels with small hubcaps.
Line-only drawing, so colours are a choice: USC cardinal body, cream roof, gold "IYA", cream script, chrome, whitewalls.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

FONTS = '/System/Library/Fonts/Supplemental/'


def interp(keys, v):
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if v <= b:
            t = (v - a) / (b - a) if b > a else 0
            return va + (vb - va) * t
    return keys[-1][1]


def mesh_obj(name, verts, faces, material=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def loft(name, rings, material=None, caps=True):
    n = len(rings[0]); verts = [tuple(p) for r in rings for p in r]; faces = []
    for i in range(len(rings) - 1):
        for j in range(n):
            faces.append((i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j))
    if caps:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return mesh_obj(name, verts, faces, material)


def cut(target, cutter, op='DIFFERENCE'):
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'; md.use_self = True
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    if len(target.data.polygons) < 20:
        print('WARNING: boolean emptied', target.name)
    return target


def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cz + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def rrect_ring(y, hw, zb, zt, rb, rt, crown=0.0, bulge=0.0, tw=None):
    """Closed cross-section at y: rounded slab, bottom radius rb, top radius rt, top half-width tw (tumblehome)."""
    tw = hw if tw is None else tw
    half = [(0.0, zb)]
    half += arc(hw - rb, zb + rb, rb, -math.pi / 2, 0, 4)
    zc = zb + rb + (zt - rt - zb - rb) * 0.62
    half += [(hw + bulge, zc)]
    half += arc(tw - rt, zt - rt, rt, 0, math.pi / 2, 5)
    half += [((tw - rt) * 0.5, zt + crown * 0.75), (0.0, zt + crown)]
    right = [(x, y, z) for x, z in half]
    left = [(-x, y, z) for x, y, z in reversed(right[1:-1])]
    return right + left


def surface(objs):
    trees = [BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get()) for o in objs]

    def top(x, y, z0=5.0):
        best = None
        for t in trees:
            h = t.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)))
            if h[0] is not None and (best is None or h[0].z > best):
                best = h[0].z
        return best
    return top


def text_obj(s, size, font, material, depth=0.004, res=4):
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(font); cu.resolution_u = res
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_line = 0.85
    o = bpy.data.objects.new('txt', cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    return o


def paint_on(o, top, at, zrot, depth=0.004, sink=0.0015):
    """Lay flat text on a curved top surface: rotate about Z, move to `at`, then drape every vertex onto the surface."""
    o.rotation_euler = (0, 0, math.radians(zrot)); o.location = (at[0], at[1], 0)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for v in o.data.vertices:
        z = top(v.co.x, v.co.y)
        v.co.z = (z if z is not None else 0) - sink + (v.co.z + depth / 2)
    o.data.update()
    return o


# ---------------------------------------------------------------- materials
PAINT = kit.mat('cardinal', rough=0.28, metal=0.25, name='paint')       # glossy enamel
CREAM = kit.mat('cream', rough=0.3, metal=0.1, name='roof')
CHROME = kit.mat('chrome', rough=0.18, metal=1.0, name='chrome')
DARK = kit.mat('#141312', rough=0.75, name='dark')
GLASS = kit.mat('#3d5866', rough=0.05, alpha=0.38, name='glass')
TIRE = kit.mat('rubber', rough=0.85, name='tire')
WHITEWALL = kit.mat('white', rough=0.6, name='whitewall')
GOLD = kit.mat('#d9a43a', rough=0.32, metal=0.6, name='gold')
SEAT = kit.mat('#d8c9a8', rough=0.65, name='seat')
TRIM = kit.mat('cardinal', rough=0.6, name='trim')
LENS = kit.mat('#fff1c8', rough=0.1, emit=0.4, name='lens')
TAIL = kit.mat('red', rough=0.15, emit=0.3, alpha=0.9, name='taillamp')

# ---------------------------------------------------------------- body
HW = [(-2.50, 0.74), (-2.48, 0.84), (-2.43, 0.91), (-2.33, 0.95), (-2.0, 0.965), (2.1, 0.965), (2.33, 0.955),
      (2.44, 0.93), (2.50, 0.86)]
ZT = [(-2.50, 0.80), (-2.45, 0.84), (-2.3, 0.87), (-1.6, 0.90), (-0.9, 0.95), (0.0, 0.96), (1.3, 0.97), (2.2, 0.975),
      (2.42, 0.96), (2.50, 0.93)]
ZBK = [(-2.50, 0.42), (-2.46, 0.37), (-2.38, 0.33), (-2.2, 0.30), (2.2, 0.30), (2.38, 0.33), (2.46, 0.37), (2.50, 0.42)]
ys = [-2.50, -2.49, -2.47, -2.44, -2.40, -2.34, -2.25, -2.1, -1.9, -1.55, -1.2, -0.9, -0.6, -0.2, 0.2, 0.6, 1.0, 1.45,
      1.8, 2.1, 2.25, 2.34, 2.40, 2.44, 2.47, 2.49, 2.50]
rings = []
for y in ys:
    hw = interp(HW, y); zt = interp(ZT, y); zb = interp(ZBK, y)
    rings.append(rrect_ring(y, hw, zb, zt, rb=0.11, rt=0.075, crown=0.035, bulge=0.012, tw=hw - 0.015))
body = loft('body', rings, PAINT)

# wheel wells (only the flanks, so the body stays whole), lined dark
WHEELS = [(-1.52, 0.36), (1.48, 0.36)]
for wy, wr in WHEELS:
    for s in (1, -1):
        c = kit.cyl(wr + 0.085, 0.50, at=(s * 0.92, wy, wr - 0.01), rot=(0, 90, 0), material=DARK, verts=48)
        cut(body, c)
# grille opening: an oval cut into the nose
g = kit.cyl(1, 0.30, at=(0, -2.50, 0.58), rot=(90, 0, 0), material=DARK, verts=48)
g.scale = (0.50, 0.12, 1); bpy.context.view_layer.objects.active = g
bpy.ops.object.transform_apply(scale=True)
cut(body, g)
# door shut-lines and trunk / hood shut-lines
for y0 in (-0.86, 0.36):
    for s in (1, -1):
        cut(body, kit.box((0.06, 0.012, 0.58), at=(s * 0.975, y0, 0.66), material=DARK))
for s in (1, -1):
    cut(body, kit.box((0.06, 1.25, 0.012), at=(s * 0.975, -0.25, 0.37), material=DARK))   # rocker line under doors
hood_cut = loft('hoodline', [[(x, y, z) for x, z in [(-0.80, 0.80), (0.80, 0.80), (0.80, 1.2), (-0.80, 1.2)]]
                              for y in (-0.92, -0.905)], DARK)
cut(body, hood_cut)
trunk_cut = loft('trunkline', [[(x, y, z) for x, z in [(-0.82, 0.90), (0.82, 0.90), (0.82, 1.2), (-0.82, 1.2)]]
                               for y in (1.36, 1.375)], DARK)
cut(body, trunk_cut)
kit.finish(body, None, smooth=40)

# tail fins on the rear fenders
for s in (1, -1):
    fin = kit.extrude([(0.55, 0.0), (2.49, 0.0), (2.49, 0.115), (2.38, 0.15), (1.5, 0.07)], 0.09, material=PAINT,
                      bevel=0.03, segments=3, name='fin')
    fin.rotation_euler = (math.radians(90), 0, math.radians(90))
    fin.location = (s * 0.89 - 0.045, 0, 0.915)
    bpy.context.view_layer.objects.active = fin; bpy.ops.object.select_all(action='DESELECT'); fin.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    # tail lamp in the end of each fin
    kit.sphere(0.042, at=(s * 0.89, 2.50, 0.99), scale=(0.9, 0.7, 1.5), material=TAIL, segs=20, rings=10, name='tail')
    # (lamp sits in the fin's tip)
    kit.cyl(0.05, 0.03, at=(s * 0.89, 2.48, 0.99), rot=(90, 0, 0), material=CHROME, verts=24, bevel=0.008, name='tailrim')

# ---------------------------------------------------------------- cabin: cream roof shell, glass, interior
def cabin_rings(grow=0.0):
    out = []
    H = [(-0.95, 0.0), (-0.40, 0.43), (-0.28, 0.47), (0.0, 0.49), (0.62, 0.48), (0.80, 0.44), (1.40, 0.0)]
    for y in [-0.95, -0.85, -0.72, -0.58, -0.46, -0.36, -0.28, -0.15, 0.1, 0.35, 0.55, 0.68, 0.80, 0.92, 1.06, 1.20,
              1.32, 1.40]:
        h = max(interp(H, y), 0.03)
        hw = 0.905 - 0.04 * (h / 0.49)
        tw = hw - 0.20 * (h / 0.49)
        zb = 0.90
        ring = rrect_ring(y, hw + grow, zb - grow, 0.93 + h + grow, rb=0.02, rt=min(0.14, 0.03 + h * 0.25) + grow,
                          crown=0.02 * (h / 0.49), tw=tw + grow)
        out.append(ring)
    return out


frame = loft('roof', cabin_rings(0.012), CREAM)
inner = loft('roofinner', cabin_rings(-0.004), CREAM)
cut(frame, inner)
ZW0, ZW1 = 0.985, 1.345
cut(frame, kit.box((2.4, 0.62, ZW1 - ZW0), at=(0, -0.70, (ZW0 + ZW1) / 2), material=CREAM))      # wraparound windshield
for y0, y1 in ((-0.26, 0.33), (0.43, 0.96)):                                                     # door + quarter windows
    cut(frame, kit.box((2.4, y1 - y0, ZW1 - ZW0 - 0.02), at=(0, (y0 + y1) / 2, (ZW0 + ZW1) / 2 - 0.01), material=CREAM))
cut(frame, kit.box((1.42, 0.6, ZW1 - ZW0 - 0.03), at=(0, 1.30, (ZW0 + ZW1) / 2 - 0.015), material=CREAM))  # rear window
frame.data.validate()
kit.finish(frame, None, smooth=40)
glass = loft('glass', cabin_rings(-0.008), GLASS)
kit.finish(glass, None, smooth=40)

# chrome window reveal along the sills
for s in (1, -1):
    kit.tube([(s * 0.885, -0.70, ZW0 - 0.005), (s * 0.88, 0.2, ZW0 - 0.005), (s * 0.865, 1.0, ZW0 - 0.005)], 0.012,
             material=CHROME, bevel_res=8, name='sill')

# interior: floor tray, dash, bench seats, steering wheel
kit.box((1.66, 2.05, 0.04), at=(0, 0.22, 0.955), material=kit.mat('walnut', rough=0.7, name='floor'), bevel=0.01)
kit.box((1.62, 0.16, 0.12), at=(0, -0.70, 1.02), material=PAINT, bevel=0.03, name='dash')
for yb, hb in ((0.05, 0.30), (0.88, 0.27)):
    kit.box((1.50, 0.42, 0.08), at=(0, yb - 0.10, 1.00), material=SEAT, bevel=0.035, name='cushion')
    kit.box((1.50, 0.12, hb), at=(0, yb + 0.12, 0.96 + hb / 2), rot=(-12, 0, 0), material=SEAT, bevel=0.05, name='seatback')
kit.torus(0.17, 0.014, at=(0.40, -0.48, 1.12), rot=(-62, 0, 0), material=kit.mat('#2a2522', rough=0.4, name='wheelrim'),
          major=40, minor=8, name='steer')
kit.cyl(0.02, 0.32, at=(0.40, -0.58, 1.04), rot=(28, 0, 0), material=CHROME, verts=12, name='column')

# ---------------------------------------------------------------- front end
for s in (1, -1):
    # hooded headlight: a fender brow, chrome bezel, lens
    kit.cyl(0.15, 0.18, at=(s * 0.70, -2.45, 0.72), rot=(90, 0, 0), material=PAINT, verts=40, bevel=0.03, segments=3,
            name='brow')
    kit.torus(0.125, 0.022, at=(s * 0.70, -2.54, 0.72), rot=(90, 0, 0), material=CHROME, major=40, minor=10, name='bezel')
    kit.sphere(0.12, at=(s * 0.70, -2.535, 0.72), scale=(1, 0.32, 1), material=LENS, segs=32, rings=12, name='lens')
# grille: chrome surround and vertical bars
surround = [(0.52 * math.cos(a), -2.505, 0.58 + 0.135 * math.sin(a)) for a in [i / 20 * math.tau for i in range(20)]]
kit.tube(surround, 0.022, material=CHROME, closed=True, bevel_res=5, name='surround')
for i in range(13):
    x = -0.42 + i * 0.07
    hz = 0.115 * math.sqrt(max(0, 1 - (x / 0.50) ** 2))
    kit.box((0.018, 0.04, 2 * hz), at=(x, -2.47, 0.58), material=CHROME, bevel=0.006, name='bar')
kit.box((1.0, 0.03, 0.02), at=(0, -2.47, 0.58), material=CHROME, bevel=0.006, name='grillebar')


def bumper(sign):
    y_end = sign * 2.5; pts = []
    for t in [i / 16 for i in range(17)]:
        a = math.pi * t
        x = -0.98 * math.cos(a)
        y = y_end + sign * (0.11 * math.sin(a) ** 0.35 - 0.16 * (1 - math.sin(a) ** 0.35))
        pts.append((x, y, 0.37))
    kit.tube(pts, 0.065, material=CHROME, bevel_res=5, name='bumper')
    for s in (1, -1):   # overriders
        kit.sphere(0.06, at=(s * 0.38, y_end + sign * 0.15, 0.44), scale=(0.7, 1.0, 1.25), material=CHROME, segs=20,
                   rings=10, name='guard')


bumper(-1); bumper(1)
# side spear trim and door handles
for s in (1, -1):
    kit.tube([(s * 0.985, -2.15, 0.70), (s * 0.99, -0.5, 0.71), (s * 0.99, 1.2, 0.72), (s * 0.975, 2.3, 0.74)], 0.012,
             material=CHROME, bevel_res=8, name='spear')
    kit.box((0.02, 0.16, 0.025), at=(s * 0.985, 0.18, 0.88), material=CHROME, bevel=0.008, name='handle')
# license plate recess at the back, hood ornament at the front
kit.box((0.32, 0.02, 0.16), at=(0, 2.505, 0.62), material=kit.mat('paper', rough=0.5, name='plate'), bevel=0.01,
        name='plate')

# ---------------------------------------------------------------- wheels
for wy, wr in WHEELS:
    for s in (1, -1):
        prof = [(0.17, -0.105), (0.30, -0.108), (0.345, -0.095), (wr, -0.05), (wr, 0.05), (0.345, 0.095), (0.30, 0.108),
                (0.17, 0.105)]
        tire = kit.lathe(prof + [(0.17, -0.105)], material=TIRE, steps=48, name='tire')
        tire.rotation_euler = (0, math.radians(90), 0); tire.location = (s * 0.84, wy, wr)
        ww = kit.lathe([(0.20, 0.0), (0.30, 0.0), (0.30, 0.012), (0.20, 0.012), (0.20, 0.0)], material=WHITEWALL,
                       steps=48, name='whitewall')
        ww.rotation_euler = (0, math.radians(90 * s), 0); ww.location = (s * (0.84 + 0.100), wy, wr)
        cap = kit.lathe([(0.0, 0.0), (0.19, 0.0), (0.19, 0.015), (0.15, 0.035), (0.075, 0.045), (0.06, 0.047),
                         (0.06, 0.058), (0.0, 0.062)], material=CHROME, steps=40, name='hubcap')
        cap.rotation_euler = (0, math.radians(90 * s), 0); cap.location = (s * (0.84 + 0.07), wy, wr)
        kit.cyl(0.18, 0.18, at=(s * 0.84, wy, wr), rot=(0, 90, 0), material=DARK, verts=32, name='rim')

# ---------------------------------------------------------------- lettering
top = surface([body, frame])
# the raised centre panel on the hood that the script sits on
hood_rings = []
for y in [-2.30 + i * (1.32 / 14) for i in range(15)]:
    ey = max(0.0, min(1.0, (y + 2.30) / 0.12, (-0.98 - y) / 0.12)) ** 0.5
    xs = [-0.56 + i * (1.12 / 16) for i in range(17)]
    upper = [(x, y, top(x, y) + 0.034 * ey * max(0.0, min(1.0, (0.56 - abs(x)) / 0.10)) ** 0.5 - 0.002) for x in xs]
    lower = [(x, y, top(x, y) - 0.04) for x in reversed(xs)]
    hood_rings.append(upper + lower)
bulge = loft('hoodpanel', hood_rings, PAINT)
kit.finish(bulge, None, smooth=50)
top = surface([body, frame, bulge])
cohort = text_obj('Cohort\n13', 0.40, FONTS + 'Brush Script.ttf', CREAM, depth=0.004)
paint_on(cohort, top, (0.06, -1.75), 90)
iya = text_obj('IYA', 0.50, FONTS + 'Rockwell.ttc', PAINT, depth=0.004)
paint_on(iya, top, (0, 0.18), 0)

from collections import Counter
dg = bpy.context.evaluated_depsgraph_get(); cnt = Counter()
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles(); cnt[o.name.split('.')[0]] += len(m.loop_triangles)
print('TRIS', sorted(cnt.items(), key=lambda kv: -kv[1]))
kit.export('1950s-car')
