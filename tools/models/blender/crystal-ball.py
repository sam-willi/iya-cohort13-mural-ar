"""Crystal ball (Madison Harris).

The drawing: a big glass ball resting in the open top of a small square box. Puffy cloud-letter "13" inside
the ball, a wavy band of mist with little stars wrapped around it, curled scroll tips at the box's top corners,
bubble-letter "ASK" on one face and "WHO IS THE BEST COHORT IN IYA?" on the other.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()

FONT_ROUND = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'


# ---------- local helpers ----------
def sweep(pts, prof, ups=(0, 0, 1), closed=False, scales=None, material=None, name='sweep', smooth=60):
    """Sweep a closed 2D profile [(u, v)] along pts. u runs along side = T x up, v along up'."""
    P = [Vector(p) for p in pts]; n = len(P)
    if isinstance(ups, tuple) or isinstance(ups, Vector):
        ups = [Vector(ups)] * n
    else:
        ups = [Vector(u) for u in ups]
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for i in range(n):
        if closed:
            t = (P[(i + 1) % n] - P[i - 1])
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        t.normalize()
        side = t.cross(ups[i]); side.normalize(); up = side.cross(t); up.normalize()
        s = scales[i] if scales else 1.0
        rings.append([bm.verts.new(P[i] + side * (u * s) + up * (v * s)) for u, v in prof])
    m = len(prof)
    for i in range(n if closed else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    if not closed:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, smooth=smooth)


def ellipse(w, h, k=12):
    return [(w * math.cos(a), h * math.sin(a)) for a in (i * math.tau / k for i in range(k))]


def text3d(s, size, depth, font=None, bevel=0.0, bres=2, at=(0, 0, 0), rot=(90, 0, 0), material=None,
           align='CENTER', spacing=1.0, res=3, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font:
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = align; cu.align_y = 'CENTER'; cu.space_character = spacing
    cu.bevel_depth = bevel; cu.bevel_resolution = bres; cu.resolution_u = res
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def star(r_out, r_in, depth, at, normal, material, spin=0.0, name='star'):
    pts = []
    for i in range(10):
        a = math.pi / 2 + spin + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((r * math.cos(a), r * math.sin(a)))
    o = kit.extrude(pts, depth, material=material, bevel=depth * 0.45, segments=2, name=name)
    # extrude builds along +Z from z=0: centre it, then turn +Z to the normal
    for v in o.data.vertices:
        v.co.z -= depth / 2
    q = Vector((0, 0, 1)).rotation_difference(Vector(normal).normalized())
    o.rotation_euler = q.to_euler(); o.location = at
    return o


def apply_all(o):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)
    return o


def resmooth(o, angle=35):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


# ---------- materials ----------
walnut = kit.mat('#4e321e', rough=0.55, name='walnut')
walnut_dark = kit.mat('#3a2415', rough=0.6, name='walnut_dark')
brass = kit.mat('brass', rough=0.28, metal=0.9, name='brass')
gold = kit.mat('#d9a441', rough=0.3, metal=0.85, name='gold_leaf')
glass = kit.mat('#c9dcee', rough=0.03, alpha=0.34, name='glass')
glass.use_backface_culling = True
cloud = kit.mat('#fbf6ea', rough=0.85, emit=0.35, name='cloud')
mist_a = kit.mat('#8fc3dc', rough=0.45, emit=0.15, name='mist_sky')
mist_b = kit.mat('#2f7d86', rough=0.45, name='mist_teal')
mist_c = kit.mat('#efe3c8', rough=0.5, emit=0.1, name='mist_cream')
star_m = kit.mat('#f6c25a', rough=0.3, metal=0.6, emit=0.6, name='star')
felt = kit.mat('#5a1a1a', rough=0.95, name='felt')

# ---------- dimensions (metres) ----------
W = 0.096          # box width/depth
H = 0.052          # box height (above plinth)
PL = 0.006         # plinth height
R = 0.085          # ball radius
TOP = PL + H

# ---------- the box ----------
plinth = kit.box((W + 0.008, W + 0.008, PL), at=(0, 0, PL / 2), material=walnut_dark, bevel=0.0018, segments=3,
                 name='plinth')
body = kit.box((W, W, H), at=(0, 0, PL + H / 2), material=walnut, bevel=0.0022, segments=3, name='box')
# inset panels on all four faces (a real seam, not a stacked slab)
PW, PH, PD = W - 0.016, H - 0.016, 0.0018
for ax, s in (('y', -1), ('x', 1), ('y', 1), ('x', -1)):
    if ax == 'y':
        c = kit.box((PW, PD * 2, PH), at=(0, s * W / 2, PL + H / 2), name='cut')
    else:
        c = kit.box((PD * 2, PW, PH), at=(s * W / 2, 0, PL + H / 2), name='cut')
    kit.boolean(body, c)
# the seat: a round well in the top that the ball sinks into
well = kit.cyl(0.039, 0.03, at=(0, 0, TOP), verts=64, name='well')
kit.boolean(body, well)
resmooth(body, 35)
# felt lining at the bottom of the well
kit.cyl(0.039, 0.002, at=(0, 0, TOP - 0.015 + 0.001), material=felt, verts=64, name='felt')
# brass top rim around the well
rim = kit.torus(0.0395, 0.0028, at=(0, 0, TOP + 0.0005), material=brass, major=72, minor=12, name='rim')
# brass corner strip along the top edge (thin frame) -> a lip that reads as a separate part
lip_o = kit.box((W + 0.003, W + 0.003, 0.004), at=(0, 0, TOP - 0.002), name='lip')
lip_i = kit.box((W - 0.007, W - 0.007, 0.01), at=(0, 0, TOP - 0.002), name='lip_i')
kit.boolean(lip_o, lip_i)
kit.finish(lip_o, brass, bevel=0.0009, segments=2)

# scroll curls at the four top corners (the drawing's curled tips)
for sx in (-1, 1):
    for sy in (-1, 1):
        d = Vector((sx, sy, 0)).normalized()
        base = Vector((sx * (W / 2 + 0.0005), sy * (W / 2 + 0.0005), TOP))
        pts, sc = [], []
        # rise from the corner, then curl outward and down into a tightening spiral
        pts.append(base + Vector((0, 0, -0.004))); sc.append(1.0)
        pts.append(base + Vector((0, 0, 0.002))); sc.append(1.0)
        cx, cz, r0 = 0.0075, 0.0055, 0.0075
        N = 26
        for i in range(N + 1):
            t = i / N
            a = math.pi - t * math.radians(400)
            r = r0 * (1 - 0.62 * t)
            pts.append(base + d * (cx + r * math.cos(a)) + Vector((0, 0, cz + r * math.sin(a))))
            sc.append(1.0 - 0.45 * t)
        side = Vector((0, 0, 1)).cross(d)
        sweep(pts, ellipse(0.0024, 0.002, 10), ups=tuple(side), scales=sc, material=brass, name='curl')

# "ASK" bubble letters on the front face
ask = text3d('ASK', 0.03, 0.0035, font=FONT_ROUND, bevel=0.0012, bres=2, res=3, material=gold,
             at=(0, -W / 2 + PD - 0.0016, PL + H / 2 - 0.0005), rot=(90, 0, 0), spacing=1.05, name='ask')
# the question on the right-hand face
lines = ['"WHO IS THE', 'BEST COHORT IN', 'IYA?"']
for i, ln in enumerate(lines):
    text3d(ln, 0.0068, 0.0009, font=FONT_ROUND, bevel=0.0, res=1, material=gold,
           at=(W / 2 - PD + 0.0004, 0, PL + H / 2 + 0.0085 - i * 0.0085), rot=(90, 0, 90), name='q')
# back and left faces: brass star inlays (the drawing's stars, carried round)
for (ax, s) in (('y', 1), ('x', -1)):
    for (u, v, r) in ((-0.022, 0.006, 0.0065), (0.004, -0.005, 0.0085), (0.025, 0.008, 0.005)):
        if ax == 'y':
            at = (-u * 1.0, W / 2 - PD + 0.0004, PL + H / 2 + v); nrm = (0, 1, 0)
        else:
            at = (s * (W / 2 - PD + 0.0004), u, PL + H / 2 + v); nrm = (-1, 0, 0)
        star(r, r * 0.45, 0.0012, at, nrm, star_m, spin=u * 9, name='inlay')

# ---------- the ball ----------
# rests on the brass rim: centre height from tube-centre contact
zc = TOP + 0.0005 + math.sqrt((R + 0.0028) ** 2 - 0.0395 ** 2)
ball = kit.sphere(R, at=(0, 0, zc), material=glass, segs=96, rings=48, name='ball')

# puffy cloud "13" floating in the upper half of the ball: a rounded letter body with a scalloped,
# cloud-like outline (the drawing draws the digits with a wavy edge)
SZ = 0.060
body13 = text3d('13', SZ, 0.007, font=FONT_ROUND, bevel=0.0032, bres=3, res=4, at=(0, 0, 0), rot=(0, 0, 0),
                spacing=1.08, name='thirteen')
flat = text3d('13', SZ, 0.0, font=FONT_ROUND, res=4, at=(0, 0, 0), rot=(0, 0, 0), spacing=1.08, name='outline')
bm = bmesh.new(); bm.from_mesh(flat.data)
bnd = [e for e in bm.edges if len(e.link_faces) == 1]
puffs, acc, k = [], 0.0, 0
for e in bnd:
    a, b = e.verts[0].co.copy(), e.verts[1].co.copy(); L = (b - a).length
    while acc < L:
        p = a + (b - a) * (acc / L)
        r = 0.0033 + 0.0011 * math.sin(k * 1.9)
        puffs.append(kit.sphere(r, at=tuple(p), segs=12, rings=8, name='puff')); k += 1
        acc += 0.0034
    acc -= L
bm.free(); bpy.data.objects.remove(flat, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for o in puffs + [body13]:
    o.select_set(True)
bpy.context.view_layer.objects.active = body13
bpy.ops.object.join()
t13 = bpy.context.object
for md in list(t13.modifiers):
    t13.modifiers.remove(md)
rm = t13.modifiers.new('remesh', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.0006
sm = t13.modifiers.new('smooth', 'SMOOTH'); sm.iterations = 2; sm.factor = 0.5
dc = t13.modifiers.new('dec', 'DECIMATE'); dc.ratio = 0.10
apply_all(t13)
# centre it, then stand it up facing the front inside the ball
bb = [t13.matrix_world @ Vector(c) for c in t13.bound_box]
cx = sum(v.x for v in bb) / 8; cy = sum(v.y for v in bb) / 8
for v in t13.data.vertices:
    v.co.x -= cx; v.co.y -= cy
t13.location = (0, 0, zc + 0.028); t13.rotation_euler = (math.radians(90), 0, 0)
kit.finish(t13, cloud, smooth=80)

# the mist band: parallel wavy strands circling the ball like a ring, tilted as in the drawing
tilt = Matrix.Rotation(math.radians(-13), 4, 'X') @ Matrix.Rotation(math.radians(-9), 4, 'Y')
ctr = Vector((0, 0, zc - 0.012))
strand_specs = [  # (radius scale, height offset, phase lag, ribbon half-height, material)
    (1.085, 0.0085, 0.00, 0.0016, mist_c),
    (1.100, 0.0030, 0.10, 0.0020, mist_a),
    (1.115, -0.0025, 0.20, 0.0016, mist_b),
    (1.100, -0.0078, 0.30, 0.0013, mist_a),
]
K = 120
strand_paths = []
for (rs, zo, lag, hh, m) in strand_specs:
    pts, ups = [], []
    for i in range(K):
        a = i * math.tau / K
        b = a - lag
        rad = R * rs * (1 + 0.035 * math.sin(2 * b + 0.6) + 0.02 * math.sin(5 * b))
        z = zo * (1 + 0.25 * math.sin(3 * a)) + 0.0065 * math.sin(3 * b) + 0.0025 * math.sin(7 * b + 1)
        p = Vector((rad * math.cos(a), rad * math.sin(a), z))
        pts.append(ctr + (tilt @ p))
        ups.append(tuple(tilt.to_3x3() @ Vector((math.cos(a), math.sin(a), 0))))
    sweep(pts, ellipse(hh, 0.0008, 8), ups=ups, closed=True, material=m, name='mist')
    strand_paths.append(pts)

# stars riding the band
for k, (si, i) in enumerate(((0, 6), (2, 22), (1, 37), (3, 52), (0, 66), (2, 81), (1, 96), (3, 110))):
    p = strand_paths[si][i]
    outward = (p - ctr); outward.z *= 0.3
    star(0.0055, 0.0023, 0.0016, p + outward.normalized() * 0.0012, outward, star_m, spin=k * 0.7, name='star')

kit.export('crystal-ball')
