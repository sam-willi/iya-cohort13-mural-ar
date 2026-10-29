"""Gaming mouse - Sarah Tu.

Her drawing: a long, sculpted right-handed mouse. Two button panels split by a treaded scroll wheel, a raised spine running
back from the wheel with "XIII" across it between two rails, a curved fin behind each button, an oval thumb grip on the
left flank, and a base whose front lip juts out past the buttons with rounded knuckles.
Line-only drawing, so colours are a choice: matte gunmetal shell, gloss black buttons, rubber skirt, brass numerals and
amber light in the fins (gaming-mouse RGB, pulled to the mural's lamp amber).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

L = 0.126                      # length (front at -Y)
Y0 = -L / 2


def yu(u):
    return Y0 + L * u


def interp(keys, u):
    for (u0, v0), (u1, v1) in zip(keys, keys[1:]):
        if u <= u1:
            t = (u - u0) / (u1 - u0) if u1 > u0 else 0
            t = t * t * (3 - 2 * t)
            return v0 + (v1 - v0) * t
    return keys[-1][1]


# plan half-width and height along the length
WK = [(0.0, 0.0225), (0.03, 0.0262), (0.15, 0.0282), (0.35, 0.0298), (0.55, 0.0322), (0.70, 0.0334),
      (0.82, 0.0322), (0.91, 0.0280), (0.96, 0.0215), (1.0, 0.0120)]
HK = [(0.0, 0.0165), (0.03, 0.0205), (0.15, 0.0255), (0.35, 0.0318), (0.55, 0.0365), (0.66, 0.0375),
      (0.80, 0.0350), (0.90, 0.0285), (0.96, 0.0205), (1.0, 0.0130)]
ZB = 0.0032                    # shell sits on the base plate
W = lambda u: interp(WK, u)
H = lambda u: interp(HK, u)
# cross-section, right half from bottom centre to top centre, in (W, H) units: pinched waist, strong shoulder
PROF = [(0.0, 0.0), (0.70, 0.0), (0.78, 0.05), (0.74, 0.22), (0.90, 0.45), (1.0, 0.60), (0.97, 0.76),
        (0.83, 0.895), (0.52, 0.975), (0.22, 1.0), (0.0, 1.0)]


def ring(u):
    w, h, y = W(u), H(u), yu(u)
    right = [(fx * w, y, ZB + fz * h) for fx, fz in PROF]
    left = [(-x, y, z) for x, y, z in reversed(right[1:-1])]
    return right + left


def mesh_obj(name, verts, faces, material=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def loft(name, rings, material=None, caps=True, closed=False):
    n = len(rings[0]); verts = [tuple(p) for r in rings for p in r]; faces = []
    m = len(rings) if closed else len(rings) - 1
    for i in range(m):
        i2 = (i + 1) % len(rings)
        for j in range(n):
            faces.append((i * n + j, i * n + (j + 1) % n, i2 * n + (j + 1) % n, i2 * n + j))
    if caps and not closed:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return mesh_obj(name, verts, faces, material)


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def cut(target, cutter, op='DIFFERENCE'):
    """kit.boolean, but the cut faces take the cutter's material (dark seams, lit grooves)."""
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'; md.use_self = True     # the subdivided shell nicks itself at the caps
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    if len(target.data.polygons) < 50:
        print('WARNING: boolean emptied', target.name)
    return target


def wall(pts, zlo, zhi, t, material):
    """Thin vertical blade following a plan polyline (for seams). zlo/zhi: functions of (x, y)."""
    rings = []
    for i, (x, y) in enumerate(pts):
        a = Vector(pts[max(i - 1, 0)]); b = Vector(pts[min(i + 1, len(pts) - 1)])
        d = (b - a).normalized(); n = Vector((-d.y, d.x)) * t / 2
        lo, hi = zlo(x, y), zhi(x, y)
        rings.append([(x - n.x, y - n.y, lo), (x + n.x, y + n.y, lo), (x + n.x, y + n.y, hi), (x - n.x, y - n.y, hi)])
    return loft('wall', rings, material)


def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


# ---------------------------------------------------------------- materials
SHELL = kit.mat('gunmetal', rough=0.5, name='shell')           # soft-touch gunmetal
BTN = kit.mat('#141517', rough=0.3, name='buttons')            # gloss black buttons
GRIP = kit.mat('rubber', rough=0.85, name='grip')
SEAM = kit.mat('#070707', rough=0.8, name='seam')
GLOW = kit.mat('#e8952a', rough=0.4, emit=0.55, name='glow')
BRASS = kit.mat('brass', rough=0.28, metal=0.95, name='brass')
BASE = kit.mat('black', rough=0.6, name='base')

# ---------------------------------------------------------------- shell
us = [0, 0.012, 0.03, 0.06, 0.1, 0.15, 0.2, 0.26, 0.32, 0.38, 0.44, 0.5, 0.56, 0.62, 0.68, 0.74, 0.8, 0.85,
      0.89, 0.925, 0.955, 0.98, 1.0]
shell = loft('shell', [ring(u) for u in us], SHELL)
md = shell.modifiers.new('ss', 'SUBSURF'); md.levels = 2
apply_mods(shell)

bvh = BVHTree.FromObject(shell, bpy.context.evaluated_depsgraph_get())


def top(x, y):
    hit = bvh.ray_cast(Vector((x, y, 0.2)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] else 0.0


def toward(p, target):
    """Surface point hit from outside point p looking at target."""
    d = (Vector(target) - Vector(p)).normalized()
    return bvh.ray_cast(Vector(p), d)


U_FIN = 0.47                   # where the button's back edge leaves the spine
CH = 0.0062                    # spine half-width
FR = lambda u: 0.50 - 0.08 * min(max((u - 0.55) / 0.45, 0), 1)
zloop = lambda u: ZB + FR(min(max(u, 0), 1)) * H(min(max(u, 0), 1))

# ---- scroll-wheel slot
slot = kit.box((0.0094, 0.027, 0.04), at=(0, yu(0.20), 0.0168 + 0.02), material=SEAM)
cut(shell, slot)

# ---- button inner seams (either side of the spine), from the front face back to the fin
for s in (1, -1):
    pts = [(s * CH, yu(u)) for u in [i / 20 * (U_FIN + 0.07) - 0.07 for i in range(21)]]
    cut(shell, wall(pts, lambda x, y: top(x, y) - 0.0045 if y > Y0 + 0.004 else ZB + 0.010, lambda x, y: 0.08,
                    0.0009, SEAM))

# ---- one seam loop all round the flanks and tail: shell above, rubber skirt below
path = []
for i in range(30):
    u = -0.06 + i / 29 * (0.86 + 0.06)
    path.append((1, u))
centre_tail = Vector((0, yu(0.86)))
loop_pts = []
for s, u in path:
    z = zloop(u); y = yu(max(u, 0.004))
    hit = toward((s * 0.2, y, z), (0, y, z))[0]
    hit = Vector((hit.x, yu(u), hit.z))
    loop_pts.append((hit, Vector((1, 0, 0))))
# round the tail
for k in range(1, 12):
    ang = k / 12 * math.pi                    # 0 at +X, pi at -X
    out = Vector((math.cos(ang), math.sin(ang), 0))
    z = zloop(1.0)
    src = Vector((centre_tail.x, centre_tail.y, z)) + out * 0.2
    hit = toward(src, (centre_tail.x, centre_tail.y, z))[0]
    loop_pts.append((hit, out))
for s, u in reversed(path):
    z = zloop(u); y = yu(max(u, 0.004))
    hit = toward((-0.2, y, z), (0, y, z))[0]
    hit = Vector((hit.x, yu(u), hit.z))
    loop_pts.append((hit, Vector((-1, 0, 0))))
rings = []
for p, n in loop_pts:
    n = Vector((n.x, n.y, 0)).normalized()
    a, b = p - n * 0.0035, p + n * 0.008
    t = 0.00045
    rings.append([(a.x, a.y, a.z - t), (b.x, b.y, b.z - t), (b.x, b.y, b.z + t), (a.x, a.y, a.z + t)])
cut(shell, loft('seamloop', rings, SEAM))


# ---- the curved fins: button back edge sweeping from the spine down the flank, a raised rib and a lit intake behind
def fin_curve(s, off=0.0, n=24, reach=0.012):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = CH + (W(0.62) + reach - CH) * (t ** 0.9)
        u = U_FIN + 0.03 * t + 0.13 * t ** 2.2 + off
        pts.append((s * x, yu(u)))
    return pts


for s in (1, -1):
    cut(shell, wall(fin_curve(s), lambda x, y: zloop((y - Y0) / L) - 0.0006, lambda x, y: 0.08, 0.0009, SEAM))
    cut(shell, wall(fin_curve(s, 0.026), lambda x, y: zloop((y - Y0) / L) + 0.0012, lambda x, y: 0.08, 0.0032, GLOW))

# ---- rear palm: the spine carries on to the tail as a centre plate, its grooves converging
for s_ in (1, -1):
    pts = [(s_ * (CH - 0.0022 * ((u - U_FIN) / (0.99 - U_FIN)) ** 1.5), yu(u)) for u in [U_FIN + i * (0.99 - U_FIN) / 18 for i in range(19)]]
    cut(shell, wall(pts, lambda x, y: top(x, y) - 0.0025, lambda x, y: 0.08, 0.0008, SEAM))

# ---- thumb grip: a shallow oval dished into the left flank (+X)
ucut = 0.80
hp = toward((0.2, yu(ucut), ZB + 0.62 * H(ucut)), (0, yu(ucut), ZB + 0.62 * H(ucut)))[0]
thumb = kit.sphere(1, at=(hp.x + 0.0042, yu(ucut), hp.z), scale=(0.0058, 0.0150, 0.0068), material=GRIP)
thumb.rotation_euler = (math.radians(-10), 0, math.radians(-5))
cut(shell, thumb)

# ---- per-face materials: rubber skirt below the loop, gloss buttons above it and ahead of the fins
fin_y = {s: fin_curve(s) for s in (1, -1)}


def fin_limit(x):
    s = 1 if x > 0 else -1
    pts = fin_y[s]; ax = abs(x)
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        if abs(xa) <= ax <= abs(xb):
            t = (ax - abs(xa)) / (abs(xb) - abs(xa) + 1e-9); return ya + (yb - ya) * t
    return pts[-1][1]


slots = {m.name: i for i, m in enumerate(shell.data.materials)}
for m in (BTN, GRIP):
    if m.name not in slots:
        shell.data.materials.append(m); slots[m.name] = len(shell.data.materials) - 1
for p in shell.data.polygons:
    if p.material_index != slots['shell']:
        continue
    c = p.center; u = min(max((c.y - Y0) / L, 0), 1)
    if c.z < zloop(u):
        p.material_index = slots['grip']
    elif abs(c.x) > CH and c.y < fin_limit(c.x):
        p.material_index = slots['buttons']
shell.data.validate()
kit.finish(shell, None, smooth=32)

# ---------------------------------------------------------------- base plate and front chin
pl = [(W(u) * 0.70 + 0.0016, yu(u)) for u in [i / 39 for i in range(40)]]
outline = pl + [(-x, y) for x, y in reversed(pl)]
kit.extrude(outline, ZB + 0.0003, material=BASE, bevel=0.0009, segments=2, name='base')
# the chin: the lip that juts out under the buttons, rounded, split at the spine into two knuckles
for s in (1, -1):
    kit.box((0.0200, 0.011, 0.0060), at=(s * 0.0110, Y0 + 0.0032, 0.0030), material=BASE, bevel=0.0024, segments=3,
            name='chin')

# ---------------------------------------------------------------- scroll wheel with treads
wy, wr, ww = yu(0.20), 0.0105, 0.0066
wz = top(CH + 0.002, wy) + 0.0042 - wr
wheel = kit.cyl(wr - 0.0009, ww, at=(0, wy, wz), rot=(0, 90, 0), material=GRIP, verts=48, bevel=0.0008, segments=2,
                name='wheel')
kit.cyl(wr - 0.0025, ww + 0.0006, at=(0, wy, wz), rot=(0, 90, 0),
        material=kit.mat('#3a3d42', rough=0.35, metal=0.8, name='hub'), verts=32, name='hub')
treads = []
for k in range(36):
    a = k / 36 * math.tau
    treads.append(kit.box((ww * 0.92, 0.0011, 0.0016),
                          at=(0, wy + math.sin(a) * (wr - 0.0011), wz + math.cos(a) * (wr - 0.0011)),
                          rot=(-math.degrees(a), 0, 0), material=GRIP, bevel=0.0003, segments=1, name='tread'))
join([wheel] + treads)
kit.box((0.0062, 0.022, 0.0008), at=(0, wy, 0.0172), material=GLOW, name='slotglow')   # light under the wheel

# ---------------------------------------------------------------- spine rails and the XIII
for s in (1, -1):
    pts = []
    for i in range(9):
        u = 0.335 + i / 8 * 0.21
        y = yu(u); x = s * (CH + 0.0026)
        pts.append((x, y, top(x, y) + 0.0002))
    kit.tube(pts, 0.00135, material=kit.mat('#4a4e55', rough=0.3, metal=0.85, name='rail'), bevel_res=4, name='rail')


def place_text(s, size, y, font, mat_, depth=0.0007):
    cu = bpy.data.curves.new('xiii', 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(font); cu.resolution_u = 3
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    o = bpy.data.objects.new('xiii', cu); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(mat_)
    # flat on the spine, baseline along +Y (reads front to back from the left flank), tilted to the slope
    y0, y1 = y - 0.008, y + 0.008
    slope = math.atan2(top(0, y1) - top(0, y0), y1 - y0)
    o.rotation_mode = 'ZYX'; o.rotation_euler = (slope, 0, math.radians(90))
    o.location = (0, y, top(0, y) + depth * 0.2)
    return o


place_text('XIII', 0.0150, yu(0.445), '/System/Library/Fonts/Supplemental/Bodoni 72.ttc', BRASS)

dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles(); print('TRIS', o.name, len(m.loop_triangles))
kit.export('gaming-mouse')
