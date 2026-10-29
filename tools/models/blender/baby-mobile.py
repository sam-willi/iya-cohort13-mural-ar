"""Mobile for babies, after Thomas Du's drawing.

The drawing: a rounded-square hoop with eight spokes across its top, and on strings below it two stars, three
puffy clouds with little curls, a crescent moon, a tiny flying saucer, a big round sun, an airliner, and the
letters I, Y, A at the bottom.
Line-only drawing, so colours are a call, nursery-soft but in the mural's palette: honey-wood hoop with walnut
spokes, lamp-yellow stars and moon, cream clouds, an amber sun, a white-and-red plane, a sky-blue saucer, and
I / Y / A in red, teal and amber. Every piece hangs from a spoke on its own thread; the letters face the front
so IYA reads left to right. A short cord and ring on top to hang it by (my addition).
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Georgia Bold.ttf'


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


def ftext(s, size, depth, material=None, bevel=0.0, res=4, name='text'):
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


def ltube(points, r, material=None, res_u=3, bevel_res=1, name='tube'):
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


def flat(poly, depth, material, bevel, segs=2):
    """A flat ornament from an outline drawn in its own (x, z) plane, centred on y=0, facing -Y."""
    o = kit.extrude(poly, depth, rot=(90, 0, 0), material=material, bevel=bevel, segments=segs, name='ornament')
    o.location = (0, depth / 2, 0)
    return o


def place(objs, at, face_deg):
    """Turn a part list built at the origin (facing -Y) by face_deg about Z and move it to `at`."""
    M = Matrix.Translation(at) @ Matrix.Rotation(math.radians(face_deg), 4, 'Z')
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    return objs


def top_z(objs):
    return max((o.matrix_world @ v.co).z for o in objs for v in o.data.vertices)


# ---------------------------------------------------------------- materials
HONEY = kit.mat('#bf8649', rough=0.5, name='honey_wood')
WALNUT = kit.mat('walnut', rough=0.55, name='walnut')
THREAD = kit.mat('#efe3c8', rough=0.8, name='thread')
STAR = kit.mat('lamp', rough=0.45, name='star')
MOON = kit.mat('#f1e6c6', rough=0.45, name='moon')
CLOUD = kit.mat('#f6f0e2', rough=0.7, name='cloud')
CURL = kit.mat('#d9cdb4', rough=0.7, name='cloud_curl')
SUN = kit.mat('#eba237', rough=0.45, name='sun')
PLANE = kit.mat('white', rough=0.4, name='plane')
RED = kit.mat('red', rough=0.4, name='red')
WINDOW = kit.mat('#2f4a5a', rough=0.2, name='window')
SAUCER = kit.mat('sky', rough=0.35, name='saucer')
DOME = kit.mat('#bfe0ee', rough=0.08, alpha=0.6, name='dome')
LIGHT = kit.mat('amber', rough=0.3, emit=0.8, name='saucer_lights')
L_I, L_Y, L_A = kit.mat('red', rough=0.4, name='letter_i'), kit.mat('teal', rough=0.4, name='letter_y'), kit.mat('amber', rough=0.4, name='letter_a')

# ---------------------------------------------------------------- the hoop: rounded-square band, eight spokes on top, hub, hanging cord
A_, T_ = 0.200, 0.013
RZ0, RZ1 = 0.640, 0.692


def squircle(a, n=4.0, k=96):
    pts = []
    for i in range(k):
        t = math.tau * i / k
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / n), c), a * math.copysign(abs(s) ** (2 / n), s)))
    return pts


outer, inner = squircle(A_), squircle(A_ - T_)
me = bpy.data.meshes.new('hoop'); bm = bmesh.new()
lo_o = [bm.verts.new((x, y, RZ0)) for x, y in outer]; hi_o = [bm.verts.new((x, y, RZ1)) for x, y in outer]
lo_i = [bm.verts.new((x, y, RZ0)) for x, y in inner]; hi_i = [bm.verts.new((x, y, RZ1)) for x, y in inner]
k = len(outer)
for i in range(k):
    j = (i + 1) % k
    bm.faces.new((lo_o[i], lo_o[j], hi_o[j], hi_o[i])); bm.faces.new((hi_i[i], hi_i[j], lo_i[j], lo_i[i]))
    bm.faces.new((hi_o[i], hi_o[j], hi_i[j], hi_i[i])); bm.faces.new((lo_i[i], lo_i[j], lo_o[j], lo_o[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
hoop = bpy.data.objects.new('hoop', me); bpy.context.collection.objects.link(hoop)
kit.finish(hoop, HONEY, bevel=0.0035, segments=2)
SPOKE_Z = RZ1 - 0.006         # spokes sit in the top of the band


def hoop_radius(deg):
    t = math.radians(deg); c, s = math.cos(t), math.sin(t)
    return (A_ - T_ / 2) / ((abs(c) ** 4 + abs(s) ** 4) ** 0.25)


for deg in (0, 45, 90, 135):
    r = hoop_radius(deg)
    sp = kit.box((2 * r, 0.018, 0.010), at=(0, 0, SPOKE_Z), rot=(0, 0, deg), material=WALNUT, bevel=0.002, name='spoke')
kit.lathe(fillet([(0, SPOKE_Z - 0.010), (0.024, SPOKE_Z - 0.010), (0.026, SPOKE_Z), (0.020, SPOKE_Z + 0.012), (0, SPOKE_Z + 0.016)],
                 [0, 0.003, 0.004, 0.004, 0], n=3), material=WALNUT, steps=32, name='hub')
rod((0, 0, SPOKE_Z + 0.014), (0, 0, SPOKE_Z + 0.075), 0.0016, material=THREAD, verts=8, name='cord')
kit.torus(0.016, 0.003, at=(0, 0, SPOKE_Z + 0.090), rot=(90, 0, 0), material=HONEY, major=32, minor=10, name='hangring')
SPOKE_UNDER = SPOKE_Z - 0.005


def hang(parts, deg, r, z_top_target, face, centre=False):
    """Hang a part list below spoke `deg` at radius r, by its highest point (or by its centre line), top at z_top_target,
    with an eyelet and a thread up to the spoke."""
    t = math.radians(deg)
    p = Vector((r * math.cos(t), r * math.sin(t), 0))
    place(parts, (0, 0, 0), face)
    pts = [o.matrix_world @ v.co for o in parts for v in o.data.vertices]
    if centre:
        ext = max(math.hypot(q.x, q.y) for q in pts)
        near = [q for q in pts if math.hypot(q.x, q.y) < max(0.02, 0.3 * ext)]
        top = max(near, key=lambda q: q.z); top = Vector((0, 0, top.z))
    else:
        top = max(pts, key=lambda q: q.z)
    for o in parts:
        o.matrix_world = Matrix.Translation((p.x - top.x, p.y - top.y, z_top_target - top.z)) @ o.matrix_world
    kit.torus(0.0045, 0.0011, at=(p.x, p.y, z_top_target + 0.0035), rot=(90, 0, face), material=THREAD, major=12, minor=4, name='eye')
    rod((p.x, p.y, z_top_target + 0.007), (p.x, p.y, SPOKE_UNDER), 0.0009, material=THREAD, verts=6, name='thread')
    return parts


# ---------------------------------------------------------------- ornaments
def star(R=0.045, r=0.019):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = R if i % 2 == 0 else r
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return [flat(fillet(pts, [0.003 if i % 2 == 0 else 0.002 for i in range(10)], n=2, closed=True), 0.016, STAR, 0.004)]


def moon():
    pts = []
    R1, R2, off = 0.046, 0.043, 0.019
    a0 = math.acos((R1 ** 2 + off ** 2 - R2 ** 2) / (2 * R1 * off))    # where the circles cross
    for i in range(33):
        a = a0 + (math.tau - 2 * a0) * i / 32
        pts.append((R1 * math.cos(a), R1 * math.sin(a)))
    b0 = math.atan2(R1 * math.sin(a0), R1 * math.cos(a0) - off)
    for i in range(1, 32):          # inner arc, without repeating the two horn points
        b = (math.tau - b0) - (math.tau - 2 * b0) * i / 32
        pts.append((off + R2 * math.cos(b), R2 * math.sin(b)))
    m = [(x * math.cos(0.5) - y * math.sin(0.5), x * math.sin(0.5) + y * math.cos(0.5)) for x, y in pts]
    return [flat(m, 0.016, MOON, 0.004)]


def cloud(scale=1.0):
    circles = [(-0.036, -0.004, 0.020), (-0.012, 0.010, 0.027), (0.018, 0.012, 0.024), (0.040, -0.002, 0.018), (0.0, -0.012, 0.020),
               (-0.022, -0.014, 0.016), (0.024, -0.012, 0.016)]
    pts = []
    for i in range(96):
        t = math.tau * i / 96; d = Vector((math.cos(t), math.sin(t)))
        best = 0
        for cx, cy, cr in circles:
            c = Vector((cx, cy)); b = d.dot(c); disc = b * b - (c.length_squared - cr * cr)
            if disc >= 0:
                best = max(best, b + math.sqrt(disc))
        pts.append((d.x * best * scale, d.y * best * scale))
    body = flat(pts, 0.022 * scale, CLOUD, 0.008 * scale, segs=3)
    curls = []
    for (cx, cz, s) in ((-0.016, 0.004, 1), (0.020, 0.002, -1)):
        sp = []
        for k in range(16):
            u = k / 15; rr = 0.008 * (1 - 0.75 * u); th = s * u * 1.6 * math.tau
            sp.append((scale * (cx + rr * math.cos(th)), -0.0115 * scale, scale * (cz + rr * math.sin(th))))
        curls.append(ltube(sp, 0.0011, material=CURL, res_u=2, bevel_res=1, name='curl'))
        mirrored = [(x, -y, z) for x, y, z in sp]
        curls.append(ltube(mirrored, 0.0011, material=CURL, res_u=2, bevel_res=1, name='curl'))
    return [body] + curls


def sun():
    return [kit.sphere(0.060, material=SUN, segs=40, rings=20, name='sun')]


def saucer():
    parts = [kit.lathe(fillet([(0, -0.008), (0.020, -0.006), (0.032, 0.0), (0.020, 0.005), (0, 0.006)], [0, 0.006, 0.003, 0.006, 0], n=4),
                       material=SAUCER, steps=40, name='saucer'),
             kit.sphere(0.013, at=(0, 0, 0.005), scale=(1, 1, 0.85), material=DOME, segs=24, rings=12, name='dome')]
    for i in range(8):
        a = math.tau * i / 8
        parts.append(kit.sphere(0.0028, at=(0.026 * math.cos(a), 0.026 * math.sin(a), -0.002), material=LIGHT, segs=8, rings=4, name='light'))
    return parts


def airplane():
    """Airliner along +X (nose), built small; wings swept back, two engines, tail."""
    parts = []
    fus = kit.lathe(fillet([(0, -0.064), (0.004, -0.062), (0.0085, -0.054), (0.0095, -0.030), (0.0095, 0.030), (0.007, 0.050), (0.003, 0.066),
                            (0, 0.067)], [0, 0.002, 0.004, 0.004, 0.004, 0.004, 0.002, 0], n=3), material=PLANE, steps=24, name='fuselage')
    fus.rotation_euler = (0, math.radians(-90), 0)          # nose to +X
    parts.append(fus)
    wing = kit.extrude(fillet([(0.012, 0.0), (-0.012, 0.0), (-0.034, 0.060), (-0.026, 0.062), (0.002, 0.009)], 0.002, n=2, closed=True),
                       0.0028, at=(0, 0, -0.0045), material=PLANE, bevel=0.0008, name='wing')
    wing2 = kit.extrude(fillet([(0.012, 0.0), (0.002, -0.009), (-0.026, -0.062), (-0.034, -0.060), (-0.012, 0.0)], 0.002, n=2, closed=True),
                        0.0028, at=(0, 0, -0.0045), material=PLANE, bevel=0.0008, name='wing')
    parts += [wing, wing2]
    for s in (-1, 1):
        e = kit.lathe(fillet([(0, -0.012), (0.0045, -0.011), (0.0050, 0.008), (0.0035, 0.012), (0, 0.012)], [0, 0.001, 0.0015, 0.001, 0], n=2),
                      material=RED, steps=16, name='engine')
        e.rotation_euler = (0, math.radians(-90), 0); e.location = (0.004, s * 0.026, -0.008)
        parts.append(e)
        parts.append(kit.box((0.010, 0.002, 0.005), at=(0.002, s * 0.026, -0.0045), material=PLANE, name='pylon'))
    parts.append(kit.extrude(fillet([(-0.040, 0.0), (-0.060, 0.0), (-0.068, 0.030), (-0.058, 0.030)], [0, 0.002, 0.003, 0.003], n=2, closed=True),
                             0.0028, rot=(90, 0, 0), material=RED, bevel=0.0008, name='fin'))
    parts[-1].location = (0, 0.0014, 0.004)
    for s in (-1, 1):
        parts.append(kit.extrude(fillet([(-0.050, 0.0), (-0.062, 0.0), (-0.068, s * 0.022), (-0.062, s * 0.022)], 0.002, n=2, closed=True)
                                 if s > 0 else
                                 fillet([(-0.050, 0.0), (-0.062, -0.022), (-0.068, -0.022), (-0.062, 0.0)], 0.002, n=2, closed=True),
                                 0.0024, at=(0, 0, 0.001), material=PLANE, bevel=0.0007, name='stab'))
    for i in range(7):        # cabin windows on both sides
        for s in (-1, 1):
            parts.append(kit.sphere(0.0016, at=(0.040 - i * 0.010, s * 0.0090, 0.0025), scale=(1.2, 0.5, 1), material=WINDOW, segs=8, rings=4, name='win'))
    parts.append(kit.sphere(0.004, at=(0.058, 0, 0.004), scale=(1.0, 1.4, 0.6), material=WINDOW, segs=12, rings=6, name='cockpit'))
    # tilt it into a gentle bank, nose a little down, as if circling
    for o in parts:
        o.matrix_world = Matrix.Rotation(math.radians(12), 4, 'X') @ Matrix.Rotation(math.radians(6), 4, 'Y') @ o.matrix_world
    return parts


def letter(ch, mat, cap=0.072):
    o = ftext(ch, cap / 0.49, 0.022, material=mat, bevel=0.0025, res=4, name='letter_' + ch)
    o.matrix_world = Matrix.Rotation(math.radians(90), 4, 'X')
    return [o]


# ---------------------------------------------------------------- hang everything (spoke angle, radius, top height, facing)
def scaled(parts, k):
    for o in parts:
        o.matrix_world = Matrix.Diagonal((k, k, k, 1.0)) @ o.matrix_world
    return parts


hang(scaled(star(), 1.30), 180, 0.170, 0.590, -20)
hang(scaled(star(0.040, 0.017), 1.30), 45, 0.190, 0.595, 35)
hang(scaled(saucer(), 1.35), 90, 0.075, 0.605, 0)
hang(scaled(moon(), 1.40), 135, 0.075, 0.548, -45)
hang(cloud(1.45), 225, 0.150, 0.468, -45)
hang(cloud(1.40), 0, 0.165, 0.472, -90)
hang(scaled(sun(), 1.35), 315, 0.075, 0.372, 0)
hang(scaled(airplane(), 1.45), 135, 0.185, 0.335, 50, centre=True)
hang(cloud(1.30), 90, 0.185, 0.272, 10)
hang(letter('I', L_I, 0.100), 180, 0.090, 0.192, 0, centre=True)
hang(letter('Y', L_Y, 0.100), 270, 0.150, 0.118, 0, centre=True)
hang(letter('A', L_A, 0.100), 315, 0.190, 0.172, 0, centre=True)

# ---------------------------------------------------------------- join, settle, export
mob = bake_join('baby_mobile')
settle(mob)
kit.export('baby-mobile')
