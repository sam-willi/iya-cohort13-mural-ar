"""Bike lock (Tsion Pescasio): a tall square-section shackle on a long brass body,
"LOVE" engraved down the front, hearts scattered over the faces, and a round
T-key emblem on the end, as in her drawing."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()

# ---------- helpers ----------

def sweep(path, profile, name='sweep', material=None, cap=True):
    """Sweep a closed 2D profile [(u, v)] along a 3D polyline. Frames are parallel-transported."""
    P = [Vector(p) for p in path]
    T = []
    for i in range(len(P)):
        a = P[max(i - 1, 0)]; b = P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((0, 1, 0))
    N = [T[0].cross(up).normalized()]
    for i in range(1, len(P)):
        n = N[-1] - T[i] * N[-1].dot(T[i]); N.append(n.normalized())
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for p, t, n in zip(P, T, N):
        b = t.cross(n)
        rings.append([bm.verts.new(p + n * u + b * v) for u, v in profile])
    k = len(profile)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(k):
            bm.faces.new((r0[j], r0[(j + 1) % k], r1[(j + 1) % k], r1[j]))
    if cap:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, smooth=40)


def rounded_rect(w, h, r, n=4, support=0.0):
    """Rounded rectangle, CCW. `support` adds a point that far along each flat side next to every corner,
    so smooth shading stays on the corners and the flat sides read flat."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        a0r, a1r = math.radians(a0), math.radians(a0 + 90)
        if support:
            pts.append((cx + r * math.cos(a0r) + support * math.sin(a0r), cy + r * math.sin(a0r) - support * math.cos(a0r)))
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        if support:
            pts.append((cx + r * math.cos(a1r) - support * math.sin(a1r), cy + r * math.sin(a1r) + support * math.cos(a1r)))
    return pts


def heart(s, n=40):
    pts = []
    for i in range(n):
        t = math.tau * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * s / 32, y * s / 32))
    return pts


def place_on_face(obj, face, u, v, depth_in):
    """Move a flat object built in the XY plane (extruded +Z) onto a body face.
    face: '-Y' front, '+Y' back, '+X', '-X'. (u, v) are face coords, v up. depth_in: how far its base sits inside."""
    if face == '-Y':
        obj.rotation_euler = (math.radians(90), 0, 0); obj.location = (u, -D / 2 + depth_in, v)
    elif face == '+Y':
        obj.rotation_euler = (math.radians(90), 0, math.radians(180)); obj.location = (u, D / 2 - depth_in, v)
    elif face == '+X':
        obj.rotation_euler = (math.radians(90), 0, math.radians(90)); obj.location = (L / 2 - depth_in, u, v)
    elif face == '-X':
        obj.rotation_euler = (math.radians(90), 0, math.radians(-90)); obj.location = (-L / 2 + depth_in, -u, v)
    return obj



# ---------- materials ----------
BRASS = kit.mat('brass', rough=0.28, metal=0.95, name='brass')
STEEL = kit.mat('chrome', rough=0.26, metal=1.0, name='steel')
DARK = kit.mat('#2a2522', rough=0.5, metal=0.3, name='dark_keyway')
ENAMEL = kit.mat('cardinal', rough=0.35, name='red_enamel')

# ---------- body ----------
L, D, H = 0.080, 0.052, 0.040
body = kit.box((L, D, H), at=(0, 0, H / 2), material=BRASS, bevel=0.0028, segments=3, name='body')

# base-plate seam all the way round, 6 mm up
ring_out = kit.box((L + 0.01, D + 0.01, 0.0008), at=(0, 0, 0.006), name='seam')
ring_in = kit.box((L - 0.0012, D - 0.0012, 0.004), at=(0, 0, 0.006), name='seam_in')
kit.boolean(ring_out, ring_in)
kit.boolean(body, ring_out)

# collars where the shackle enters the body
SX, BAR = 0.028, 0.0158
for x in (-SX, SX):
    c = kit.box((BAR + 0.003, BAR + 0.003, 0.003), at=(x, 0, H), name='collar_cut')
    kit.boolean(body, c)

# ---------- engraving: LOVE + hearts on the front, hearts + emblem elsewhere ----------
CUT = 0.0009



def text_obj(s, size, depth, offset=0.0, name='txt'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = offset; cu.space_character = 1.12
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for ob in bpy.context.selected_objects:
        ob.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    # put the extrusion between z=0 and z=depth
    o.data.transform(Matrix.Translation((0, 0, depth / 2)))
    return o


def flat(poly, depth, name):
    return kit.extrude(poly, depth, name=name)



# LOVE: groove CUT deep, enamel fill sitting 0.25 mm below the surface
lt = text_obj('LOVE', 0.0225, CUT * 2, offset=0.0003, name='love_cut')
place_on_face(lt, '-Y', 0.0, 0.0175, CUT)
kit.boolean(body, lt)
lf = text_obj('LOVE', 0.0225, CUT * 0.7, offset=0.00017, name='love_fill')
place_on_face(lf, '-Y', 0.0, 0.0175, CUT * 0.95)
lf.data.materials.append(ENAMEL)

hearts = [('-Y', -0.0315, 0.0315, 0.0075), ('-Y', 0.0255, 0.0062, 0.0068), ('+X', -0.0155, 0.0315, 0.0068),
          ('+X', 0.0175, 0.0105, 0.0062), ('+Y', 0.026, 0.028, 0.0075), ('+Y', -0.024, 0.011, 0.0065),
          ('-X', 0.0, 0.020, 0.009)]
for i, (face, u, v, s) in enumerate(hearts):
    hc = flat(heart(s), CUT * 2, f'heart_cut{i}')
    place_on_face(hc, face, u, v, CUT)
    kit.boolean(body, hc)
    hf = flat(heart(s * 0.93), CUT * 0.7, f'heart{i}')
    place_on_face(hf, face, u, v, CUT * 0.95)
    hf.data.materials.append(ENAMEL)

# ---------- end emblem: a raised brass ring round a T-shaped keyway ----------
EX, EZ = 0.004, 0.019
ring = kit.lathe([(0.0098, 0), (0.0098, 0.0006), (0.0094, 0.0011), (0.0080, 0.0011), (0.0076, 0.0006), (0.0076, 0)],
                 material=BRASS, steps=64, name='emblem_ring')
ring.rotation_euler = (0, math.radians(90), 0); ring.location = (L / 2 - 0.0002, EX, EZ)
# T-key keyway: a T head over a notched key blade, cut into the face
key = [(-0.0042, 0.0050), (0.0042, 0.0050), (0.0042, 0.0028), (0.0011, 0.0028), (0.0011, 0.0010),
       (0.0024, 0.0010), (0.0024, -0.0004), (0.0011, -0.0004), (0.0011, -0.0018), (0.0021, -0.0018),
       (0.0021, -0.0032), (0.0011, -0.0032), (0.0011, -0.0058), (-0.0011, -0.0058), (-0.0011, 0.0028),
       (-0.0042, 0.0028)]
kc = flat(key, 0.004, 'key_cut')
place_on_face(kc, '+X', EX, EZ, 0.002)
kit.boolean(body, kc)
kf = flat([(x * 0.94, y * 0.96) for x, y in key], 0.0004, 'keyway_floor')
place_on_face(kf, '+X', EX, EZ, 0.0019)
kf.data.materials.append(DARK)

# ---------- shackle: rounded-square bar, legs into the body, semicircular crown ----------
TOP = H + 0.115
R = SX
path = []
for i in range(8):
    path.append((-SX, 0, H - 0.012 + (TOP - BAR / 2 - R - (H - 0.012)) * i / 7))
for i in range(1, 32):
    a = math.pi - math.pi * i / 32
    path.append((R * math.cos(a), 0, TOP - BAR / 2 - R + R * math.sin(a)))
for i in range(8):
    path.append((SX, 0, TOP - BAR / 2 - R - (TOP - BAR / 2 - R - (H - 0.012)) * i / 7))
sh = sweep(path, rounded_rect(BAR, BAR, 0.0025, n=4, support=0.0006), name='shackle', material=STEEL)


wn = body.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.weight = 100

kit.export('lock')
