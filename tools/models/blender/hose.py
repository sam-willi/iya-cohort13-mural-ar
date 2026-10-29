import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

# Garden hose, after Bowden Eley's isometric drawing (RV P5a): a fat hose wound into an upright coil of five
# touching loops, standing on edge. Seen as he drew it, the coil runs left to right with its open front loop
# nearest you on the left; "COHORT 13" is printed up the near side of that front loop, letter tops toward the
# front. The free end leaves over the top of the front loop, swings out to the left, dips to about mid-height and
# rises to a nozzle: a black knurled collar, a tapered brass body and a black tip, spraying a fan of water.
# Guessed (not in the drawing): the spigot end, a brass female coupling with a hex swivel nut riding on the
# outside of the back loop; the hose colour is garden-hose green because the riddle calls it "a long green snake".
# His other sheet (PA5) is a different idea (a flat coil lying on the floor, "Disruption / Innovation" in the
# spray); this follows P5a, the one with COHORT 13 on it.
#
# Built in a local frame (coil axis +X, front loop at -X, near side -Y), then turned -13 degrees so the front
# three-quarter view is the drawing's view. Only views close to the coil's axis show it as a ring of loops.

TAU = math.tau
random.seed(13)

HOSE = kit.mat('#376a32', rough=0.5, name='hose')             # garden green, pulled warm toward the palette
INK = kit.mat('#f2efe8', rough=0.5, name='print')
BRASS = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
GRIP = kit.mat('rubber', rough=0.75, name='grip')
WATER = kit.mat('#a9d5ea', rough=0.05, alpha=0.8, name='water')
FONT = '/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf'


def desel():
    for o in bpy.context.selected_objects:
        o.select_set(False)


def link(name, bm, material=None, smooth=40):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, 0.0, 2, smooth)


def apply_all(o):
    desel(); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.select_set(False)
    return o


# ---------------------------------------------------------------- swept tube with rotation-minimising frames
def resample(pts, step):
    """Resample a polyline to (nearly) uniform spacing, keeping both ends."""
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(2, int(round(L[-1] / step)) + 1)
    out, j = [], 0
    for k in range(n):
        d = L[-1] * k / (n - 1)
        while j < len(L) - 2 and L[j + 1] < d:
            j += 1
        seg = L[j + 1] - L[j]
        t = (d - L[j]) / seg if seg else 0.0
        out.append(pts[j].lerp(pts[j + 1], t))
    return out


def frames(pts):
    """Tangents and rotation-minimising normals (double reflection, Wang et al. 2008)."""
    T = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        T.append((b - a).normalized())
    t0 = T[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    N = [(ref - t0 * ref.dot(t0)).normalized()]
    for i in range(len(pts) - 1):
        v1 = pts[i + 1] - pts[i]; c1 = v1.dot(v1)
        if c1 < 1e-14:
            N.append(N[-1].copy()); continue
        rL = N[i] - (2 / c1) * v1.dot(N[i]) * v1
        tL = T[i] - (2 / c1) * v1.dot(T[i]) * v1
        v2 = T[i + 1] - tL; c2 = v2.dot(v2)
        n = rL - (2 / c2) * v2.dot(rL) * v2 if c2 > 1e-14 else rL
        N.append((n - T[i + 1] * n.dot(T[i + 1])).normalized())
    return T, N


def sweep(pts, radius, sides=16, material=None, name='tube', caps=True, smooth=60):
    """Round tube along pts. radius: float or f(t in 0..1)."""
    T, N = frames(pts)
    bm = bmesh.new(); rings = []
    for i, (p, t, n) in enumerate(zip(pts, T, N)):
        b = t.cross(n)
        rr = radius(i / (len(pts) - 1)) if callable(radius) else radius
        rings.append([bm.verts.new(p + rr * (math.cos(TAU * k / sides) * n + math.sin(TAU * k / sides) * b))
                      for k in range(sides)])
    for a, c in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], c[j], c[k]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return link(name, bm, material, smooth)


def hermite(P, Tn, samples=24):
    """C1 curve through points P with unit tangents Tn (None = Catmull-Rom)."""
    m = []
    for i, p in enumerate(P):
        if Tn[i] is not None:
            m.append(Tn[i].normalized())
        else:
            m.append((P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized())
    out = []
    for i in range(len(P) - 1):
        p0, p1 = P[i], P[i + 1]; L = (p1 - p0).length
        m0, m1 = m[i] * L, m[i + 1] * L
        for k in range(samples):
            t = k / samples; t2, t3 = t * t, t * t * t
            out.append((2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1)
    out.append(P[-1].copy())
    return out


# ---------------------------------------------------------------- the coil
r = 0.0155                 # hose radius: a fat 1" hose, ~1/12 of the coil's height, as he drew it
R0 = 0.170                 # loop centre-line radius
PITCH = 2 * r + 0.0012     # loops wound side by side, just touching
TH0 = math.radians(-35)                    # spigot end: low on the near side of the back loop
TH_END = math.radians(4 * 360 + 105)       # free end leaves just past the top of the front loop
TURNS = (TH_END - TH0) / TAU
X_BACK = PITCH * TURNS / 2


def loop_r(th):
    """Hand-wound: each loop a touch bigger or smaller than its neighbour, slightly out of round."""
    return R0 * (1.0 + 0.022 * math.sin(th * 0.37 + 1.3) + 0.006 * math.sin(th * 2.0 + 0.4))


def helix(th):
    R = loop_r(th)
    x = X_BACK - PITCH * (th - TH0) / TAU + 0.0005 * math.sin(th * 0.9)
    s = (th - TH0) / math.radians(55)
    if s < 1:                                   # the spigot end lifts out to ride on the outside of the back loop
        x += 1.05 * r * (1 - s) ** 2
    zc = r + R                                  # every loop rests on the floor
    return Vector((x, -R * math.cos(th), zc + R * math.sin(th)))


def helix_d(th, h=1e-4):
    return (helix(th + h) - helix(th - h)) / (2 * h)


NC = int((TH_END - TH0) / math.radians(1.5))
coil = [helix(TH0 + (TH_END - TH0) * i / NC) for i in range(NC + 1)]

# free end: over the top, out of the front of the coil, down to a dip at about mid-height, up to the nozzle
A = coil[-1]; xf = A.x; ZC = r + R0
F = Vector((xf - 1.42 * R0, 0.22 * R0, ZC + 0.56 * R0))         # where the hose enters the nozzle collar
NOZ = Vector((-0.40, -0.06, 0.92)).normalized()                    # nozzle points up and out, like his
P = [A,
     Vector((xf - 0.34 * R0, 0.62 * R0, ZC + 0.80 * R0)),       # turns out of the coil in a loose bend
     Vector((xf - 0.66 * R0, 0.57 * R0, ZC + 0.40 * R0)),
     Vector((xf - 0.97 * R0, 0.45 * R0, ZC + 0.07 * R0)),       # bottom of the dip
     Vector((xf - 1.29 * R0, 0.31 * R0, ZC + 0.21 * R0)),
     F]
free = hermite(P, [helix_d(TH_END), None, None, Vector((-1, -0.3, -0.32)), None, NOZ], samples=30)
path = resample(coil + free[1:], 0.0095)
hose = sweep(path, r, sides=16, material=HOSE, name='hose')


# ---------------------------------------------------------------- nozzle (built along +Z, then aimed)
def aim(o, base, d, s=0.0):
    q = d.to_track_quat('Z', 'Y')
    o.matrix_world = Matrix.Translation(base + d * s) @ q.to_matrix().to_4x4() @ o.matrix_world
    return o


def prof(pts, k=r):
    return [(a * k, b * k) for a, b in pts]


aim(kit.lathe(prof([(0, -1.9), (1.06, -1.9), (1.10, -1.8), (1.10, -1.2), (0, -1.2)]), material=BRASS, steps=40,
              name='ferrule'), F, NOZ)
aim(kit.lathe(prof([(0, -1.3), (1.48, -1.3), (1.62, -1.16), (1.64, -0.9), (1.64, 0.42), (1.58, 0.56), (1.42, 0.60),
                    (1.40, 0.66), (1.40, 0.96), (1.33, 1.04), (0, 1.04)]), material=GRIP, steps=48,
              name='collar'), F, NOZ)
for k in range(20):          # knurled grip ribs round the collar
    a = TAU * (k + 0.5) / 20
    rib = kit.box((0.30 * r, 0.22 * r, 1.30 * r), at=(1.64 * r * math.cos(a), 1.64 * r * math.sin(a), -0.38 * r),
                  material=GRIP, bevel=0.06 * r, name='knurl')
    rib.rotation_euler = (0, 0, a)
    aim(rib, F, NOZ)
aim(kit.lathe(prof([(0, 1.0), (1.20, 1.0), (1.22, 1.08), (1.22, 1.30), (1.13, 1.40), (1.02, 1.42), (1.02, 1.55),
                    (1.08, 1.60), (1.08, 1.72), (0.99, 1.80), (0.86, 4.30), (0, 4.30)]), material=BRASS, steps=48,
              name='nozzle'), F, NOZ)
aim(kit.lathe(prof([(0, 4.22), (0.92, 4.22), (0.98, 4.30), (0.99, 4.95), (0.92, 5.10), (0.50, 5.12),
                    (0.36, 5.02), (0, 5.02)]), material=GRIP, steps=40, name='tip'), F, NOZ)
aim(kit.lathe(prof([(0, 4.96), (0.37, 4.96), (0.37, 5.04), (0.14, 5.06), (0.12, 5.00), (0, 5.00)]),
              material=BRASS, steps=24, name='orifice'), F, NOZ)
TIP = F + NOZ * 5.12 * r

# ---------------------------------------------------------------- spray: a loose fan of water streaks and drops
up = Vector((0, 0, 1))
e1 = up.cross(NOZ).normalized(); e2 = NOZ.cross(e1)
GOLD = math.pi * (3 - math.sqrt(5))
CONE = math.radians(44)                                       # his spray fans out wide, nearly upright
AXIS = (NOZ + Vector((0, 0, 0.6))).normalized()
e1 = up.cross(AXIS).normalized(); e2 = AXIS.cross(e1)
NS = 13
for i in range(NS):
    rad = CONE * math.sqrt((i + 0.5) / NS)                    # sunflower spread inside the cone
    az = i * GOLD
    d = (AXIS * math.cos(rad) + math.sin(rad) * (math.cos(az) * e1 + math.sin(az) * e2)).normalized()
    a0 = random.uniform(0.014, 0.032)
    L = random.uniform(0.075, 0.14) * (1.1 - 0.3 * rad / CONE)
    dashes = [(a0, a0 + L)] if random.random() < 0.6 else [(a0, a0 + 0.5 * L), (a0 + 0.66 * L, a0 + L)]
    w = random.uniform(0.0030, 0.0038)
    for (s0, s1) in dashes:
        pts = []
        for k in range(10):
            s = s0 + (s1 - s0) * k / 9
            pts.append(TIP + d * s - up * 0.8 * s * s)        # a little gravity droop
        sweep(pts, lambda t, w=w: w * (0.3 + 0.7 * math.sin(math.pi * (0.1 + 0.85 * t))), sides=6, material=WATER,
              name='spray')
    if random.random() < 0.2:
        s = a0 + L + random.uniform(0.010, 0.022)
        kit.sphere(random.uniform(0.0028, 0.0040), at=TIP + d * s - up * 0.8 * s * s, material=WATER, segs=10,
                   rings=6, name='drop')

# ---------------------------------------------------------------- spigot end: brass female coupling, hex swivel nut
S0 = path[0]; D0 = (path[0] - path[3]).normalized()
aim(kit.lathe(prof([(0, -1.5), (1.10, -1.5), (1.14, -1.4), (1.14, 0.0), (0, 0.0)]), material=BRASS, steps=40,
              name='ferrule2'), S0, D0)
nut = kit.cyl(1.56 * r, 1.55 * r, at=(0, 0, 0.775 * r), verts=6, material=BRASS, bevel=0.10 * r, name='hexnut')
bore = apply_all(kit.cyl(1.08 * r, 1.4 * r, at=(0, 0, 1.25 * r), verts=40, name='bore'))
kit.boolean(nut, bore)
aim(nut, S0, D0)
aim(kit.cyl(1.09 * r, 0.12 * r, at=(0, 0, 0.62 * r), verts=40, material=GRIP, name='washer'), S0, D0)

# ---------------------------------------------------------------- "COHORT 13" up the near side of the front loop
cu = bpy.data.curves.new('print', 'FONT'); cu.body = 'COHORT 13'; cu.size = 0.0355; cu.resolution_u = 5
cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.space_character = 1.22
if os.path.exists(FONT):
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
t = bpy.data.objects.new('print', cu); bpy.context.collection.objects.link(t)
t = apply_all(t)
bm = bmesh.new(); bm.from_mesh(t.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
for _ in range(4):                          # split long edges so the print can wrap round the hose
    long_e = [e for e in bm.edges if e.calc_length() > 0.0042]
    if not long_e:
        break
    bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
u_mid, w_mid = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
print('PRINT_LEN', round(max(xs) - min(xs), 4), 'CAP', round(max(ys) - min(ys), 4))
TH_TXT = 4 * TAU + math.radians(12)          # sits where he put it: just below the middle of the coil as seen
PHI_C = math.radians(24)                     # turned a little toward the front, so it faces you as drawn
RS = r + 0.0006
for v in bm.verts:
    u, w = v.co.x - u_mid, v.co.y - w_mid
    th = TH_TXT + u / (loop_r(TH_TXT) + r * math.cos(PHI_C))
    c = helix(th); tg = helix_d(th).normalized()
    out = Vector((0, -math.cos(th), math.sin(th))); out = (out - tg * out.dot(tg)).normalized()
    fr = tg.cross(out)
    if fr.x > 0:
        fr = -fr                              # the side of the hose facing the front of the coil (-X)
    ph = PHI_C + w / RS
    v.co = c + RS * (math.cos(ph) * out + math.sin(ph) * fr)
bm.to_mesh(t.data); bm.free()
t.data.materials.clear(); t.data.materials.append(INK)
for f in t.data.polygons:
    f.use_smooth = True
# make sure the print faces outward (majority vote against the hose's own normals)
t.data.update()
votes = 0
for pf in t.data.polygons:
    ok, loc, nrm, _ = hose.closest_point_on_mesh(pf.center)
    votes += 1 if pf.normal.dot(nrm) > 0 else -1
print('PRINT_FACING', votes, len(t.data.polygons))
if votes < 0:
    t.data.flip_normals()

# ---------------------------------------------------------------- finish
dg = bpy.context.evaluated_depsgraph_get(); lo = 1e9
for o in bpy.context.scene.objects:
    if o.type == 'MESH':
        ev = o.evaluated_get(dg)
        for v in ev.to_mesh().vertices:
            lo = min(lo, (o.matrix_world @ v.co).z)
        ev.to_mesh_clear()
print('MIN_Z', round(lo, 5))
for o in bpy.context.scene.objects:          # stand exactly on z=0
    if o.type == 'MESH':
        o.location.z -= lo

Rz = Matrix.Rotation(math.radians(-13), 4, 'Z')
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in objs:
    o.matrix_world = Rz @ o.matrix_world
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
blo = Vector((1e9, 1e9, 1e9)); bhi = -blo
for o in objs:
    ev = o.evaluated_get(dg); m = ev.to_mesh()
    for v in m.vertices:
        w = o.matrix_world @ v.co
        blo = Vector(map(min, blo, w)); bhi = Vector(map(max, bhi, w))
    ev.to_mesh_clear()
c = (blo + bhi) / 2
for o in objs:
    o.location.x -= c.x; o.location.y -= c.y
print('BBOX', [round(v, 4) for v in (bhi - blo)])

# join meshes that share a material (fewer draw calls on the phone)
groups = {}
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        continue
    o = apply_all(o)
    groups.setdefault(o.data.materials[0].name if o.data.materials else '', []).append(o)
for key, g in groups.items():
    if len(g) > 1:
        desel()
        for o in g:
            o.select_set(True)
        bpy.context.view_layer.objects.active = g[0]
        bpy.ops.object.join()
desel()
kit.export('hose')
