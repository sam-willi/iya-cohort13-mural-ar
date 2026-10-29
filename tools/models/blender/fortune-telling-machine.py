import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion

# ---------------------------------------------------------------- local helpers (kept in this file on purpose)

def _mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return o


def loft(rings, name='loft', cap_start=True, cap_end=True, closed=True, loop=False, material=None, bevel=0.0, smooth=30):
    """Skin a list of rings (each a list of 3D points, same count). loop=True joins the last ring back to the first."""
    bm = bmesh.new()
    vs = [[bm.verts.new(tuple(p)) for p in ring] for ring in rings]
    n = len(rings[0])
    pairs = list(zip(vs, vs[1:])) + ([(vs[-1], vs[0])] if loop else [])
    for a, b in pairs:
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if not loop:
        if cap_start: bm.faces.new(vs[0][::-1])
        if cap_end: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _mesh_obj(name, bm)
    return kit.finish(o, material, bevel, smooth=smooth)


def rrect(w, h, r, seg=6, cx=0.0, cy=0.0):
    """Counter-clockwise rounded rectangle polygon."""
    r = min(r, w / 2 - 1e-5, h / 2 - 1e-5); pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def circle2(r, n=32, cx=0.0, cy=0.0, a0=0.0):
    return [(cx + r * math.cos(a0 + math.tau * i / n), cy + r * math.sin(a0 + math.tau * i / n)) for i in range(n)]


def rod(p0, p1, r, material=None, verts=16, name='rod', bevel=0.0, r2=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    o = kit.cyl(r, d.length, at=(p0 + p1) / 2, material=material, verts=verts, name=name, bevel=bevel, r2=r2)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return o


def fillet(pts, r, seg=6):
    """Round the corners of a polyline."""
    P = [Vector(p) for p in pts]; out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1 = (a - b).normalized(); d2 = (c - b).normalized()
        ang = d1.angle(d2)
        if ang > math.pi - 1e-3:
            out.append(b); continue
        t = min(r / math.tan(ang / 2), (a - b).length * 0.5, (c - b).length * 0.5)
        p1, p2 = b + d1 * t, b + d2 * t
        for k in range(seg + 1):
            s = k / seg; out.append((1 - s) ** 2 * p1 + 2 * (1 - s) * s * b + s * s * p2)
    out.append(P[-1])
    return out


def catmull(pts, n=8, closed=False):
    """Smooth path through points (Catmull-Rom)."""
    P = [Vector(p) for p in pts]; out = []
    m = len(P)
    segs = range(m) if closed else range(m - 1)
    for i in segs:
        p0 = P[(i - 1) % m] if (closed or i > 0) else P[0]
        p1 = P[i]; p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if (closed or i + 2 < m) else P[-1]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def frames(pts, up=(0, 0, 1), loop=False):
    P = [Vector(p) for p in pts]; m = len(P); T = []
    for i in range(m):
        if loop: t = P[(i + 1) % m] - P[(i - 1) % m]
        elif i == 0: t = P[1] - P[0]
        elif i == m - 1: t = P[-1] - P[-2]
        else: t = P[i + 1] - P[i - 1]
        T.append(t.normalized())
    n = Vector(up); n = n - n.dot(T[0]) * T[0]
    if n.length < 1e-6: n = T[0].orthogonal()
    n.normalize(); N = []
    for i in range(m):
        if i > 0:
            n = T[i - 1].rotation_difference(T[i]) @ n
            n = (n - n.dot(T[i]) * T[i]).normalized()
        N.append(n.copy())
    B = [T[i].cross(N[i]) for i in range(m)]
    return P, T, N, B


def sweep(pts, prof, name='sweep', loop=False, up=(0, 0, 1), material=None, bevel=0.0, caps=True, smooth=30, twist=None):
    """Sweep a 2D profile [(u, v), ...] (u along the frame normal, v along the binormal) along a path."""
    P, T, N, B = frames(pts, up, loop)
    rings = []
    for i in range(len(P)):
        n, b = N[i], B[i]
        if twist:
            a = twist(i / max(1, len(P) - 1)); n, b = n * math.cos(a) + b * math.sin(a), b * math.cos(a) - n * math.sin(a)
        rings.append([P[i] + n * u + b * v for u, v in prof])
    return loft(rings, name, cap_start=caps, cap_end=caps, loop=loop, material=material, bevel=bevel, smooth=smooth)


def apply_mods(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if o.type != 'MESH':
        bpy.ops.object.convert(target='MESH')
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)
    return o


def join(objs, name=None):
    for o in objs: apply_mods(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    if name: o.name = name
    return o


def solidify(o, t, offset=-1.0):
    md = o.modifiers.new('solid', 'SOLIDIFY'); md.thickness = t; md.offset = offset; md.use_even_offset = True
    return o


def xform(o, rot=None, loc=None, scale=None, apply=True):
    """Rotate (degrees XYZ) / move / scale an object and bake it into the mesh."""
    if scale: o.scale = scale
    if rot: o.rotation_mode = 'XYZ'; o.rotation_euler = [math.radians(a) for a in rot]
    if loc: o.location = loc
    if apply:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=bool(loc), rotation=bool(rot), scale=bool(scale))
    return o


def lowest_z():
    dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            e = o.evaluated_get(dg); m = e.to_mesh()
            for v in m.vertices:
                z = min(z, (e.matrix_world @ v.co).z)
            e.to_mesh_clear()
    return z


def ground(target=0.0):
    """Shift every root object so the lowest point sits on z=target."""
    dz = target - lowest_z()
    for o in bpy.context.scene.objects:
        if o.parent is None: o.location.z += dz

extrude, tube = kit.extrude, kit.tube

# ---------------------------------------------------------------- model
# Fortune telling machine, after Brendan Giang's drawing: a tall square cabinet on a plinth, corner pilasters with
# inlay lines, a glass case on three sides holding the fortune teller ("DrDre", lettered across the front glass) with
# one hand on a crystal ball in the front corner and the other over a three-digit display, a frieze with square
# corner blocks under a flared cornice, and on the front below: the card slot under an arched sunburst lamp, the coin
# plate with its slot and down arrow, and a push button. The left side has a locked service door; the right side and
# back (louvred service panel) are invented. Pencil drawing: woods, brass and velvet are chosen from the palette.
WALNUT = kit.mat('walnut', rough=0.55, name='walnut')
DARKWOOD = kit.mat('#3b2616', rough=0.55, name='dark_walnut')
OAK = kit.mat('oak', rough=0.55, name='oak_panel')
BRASS = kit.mat('brass', rough=0.32, metal=0.85, name='brass')
VELVET = kit.mat('cardinal', rough=0.9, name='velvet')
DRAPE = kit.mat('#7e1a17', rough=0.85, name='drape')
GLASS = kit.mat('glass', rough=0.08, alpha=0.1, name='glass')
BALL = kit.mat('#cfe6f0', rough=0.03, alpha=0.38, name='crystal')
GLOW = kit.mat('lamp', rough=0.4, emit=3.0, name='glow')
LAMP = kit.mat('amber', rough=0.3, emit=1.6, name='lamp_glass')
DIGIT = kit.mat('#ffb347', rough=0.4, emit=2.2, name='digits')
SLOT = kit.mat('#141210', rough=0.7, name='slot')
ROBE = kit.mat('teal', rough=0.6, name='robe')
SKIN = kit.mat('#6e432a', rough=0.55, name='skin')
BEARD = kit.mat('#1c1714', rough=0.9, name='beard')
SHADES = kit.mat('#101010', rough=0.12, name='shades')
BUTTON = kit.mat('red', rough=0.3, name='button')

W, D = 0.84, 0.78
Z_PL, Z_LOW, Z_CASE, Z_FR, Z_TOP = 0.05, 0.98, 1.78, 1.89, 2.01
POST = 0.056
FY = -D / 2                       # front face


def cut(target, cutter):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)


def plate(w, h, t, at, material, r=0.006, face=(0, -1, 0), bevel=0.0015, name='plate'):
    """Rounded-rectangle plate lying on a face (default the front, facing -y)."""
    o = extrude(rrect(w, h, r, seg=4), t, name=name)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(face))
    if Vector(face).y < -0.5:
        o.rotation_quaternion = Quaternion((1, 0, 0), math.radians(90))
    o.location = at
    return kit.finish(o, material, bevel=bevel, segments=2)

# ---- plinth, lower cabinet, corner pilasters
kit.box((W + 0.04, D + 0.04, Z_PL), at=(0, 0, Z_PL / 2), material=DARKWOOD, bevel=0.006, name='plinth')
low = kit.box((W - 0.02, D - 0.02, Z_LOW - Z_PL), at=(0, 0, (Z_PL + Z_LOW) / 2), name='cabinet')
low.data.materials.append(WALNUT); low.data.materials.append(SLOT)
# recessed door panels on both sides, and the louvred service panel on the back
for sx in (-1, 1):
    c = kit.box((0.04, D - 0.24, 0.66), at=(sx * (W / 2 - 0.01), 0.0, 0.5), name='doorcut'); c.data.materials.clear(); c.data.materials.append(WALNUT)
    cut(low, c)
c = kit.box((W - 0.24, 0.04, 0.66), at=(0, D / 2 - 0.01, 0.5), name='backcut'); c.data.materials.clear(); c.data.materials.append(WALNUT)
cut(low, c)
kit.finish(low, None, bevel=0.003)
for sx in (-1, 1):
    kit.box((0.016, D - 0.27, 0.63), at=(sx * (W / 2 - 0.022), 0.0, 0.5), material=OAK, bevel=0.006, segments=2, name='door')
kit.box((W - 0.27, 0.016, 0.63), at=(0, D / 2 - 0.022, 0.5), material=OAK, bevel=0.006, segments=2, name='service_panel')
for k in range(7):
    kit.box((W - 0.38, 0.012, 0.016), at=(0, D / 2 - 0.012, 0.33 + k * 0.045), rot=(-25, 0, 0), material=DARKWOOD, bevel=0.002, name='louvre')
plate(0.07, 0.04, 0.003, (0, D / 2 - 0.0125, 0.74), BRASS, face=(0, 1, 0), name='maker_plate')
# lock on the left door, near its back edge
kit.cyl(0.016, 0.006, at=(-(W / 2 - 0.012), 0.19, 0.58), rot=(0, 90, 0), material=BRASS, verts=24, bevel=0.0015, name='lock')
kit.box((0.004, 0.004, 0.014), at=(-(W / 2 - 0.0085), 0.19, 0.577), material=SLOT, name='keyhole')
kit.cyl(0.0035, 0.004, at=(-(W / 2 - 0.0085), 0.19, 0.584), rot=(0, 90, 0), material=SLOT, verts=12, name='keyhole_top')
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * (W / 2 - POST / 2 + 0.008), sy * (D / 2 - POST / 2 + 0.008)
        kit.box((POST, POST, Z_FR - Z_PL), at=(x, y, (Z_PL + Z_FR) / 2), material=DARKWOOD, bevel=0.004, name='post')
        # brass inlay lines on the two outward faces
        kit.box((0.004, POST * 0.4, Z_FR - Z_PL - 0.12), at=(x + sx * POST / 2, y, (Z_PL + Z_FR) / 2), material=BRASS, name='inlay')
        kit.box((POST * 0.4, 0.004, Z_FR - Z_PL - 0.12), at=(x, y + sy * POST / 2, (Z_PL + Z_FR) / 2), material=BRASS, name='inlay')
# brass deck edge
kit.box((W - 0.01, D - 0.01, 0.028), at=(0, 0, Z_LOW - 0.006), material=BRASS, bevel=0.003, name='deck_edge')

# ---- glass case: velvet deck, draped back wall, three glass panes in thin frames
kit.box((W - 0.03, D - 0.03, 0.012), at=(0, 0, Z_LOW + 0.014), material=VELVET, bevel=0.003, name='deck')
kit.box((W - 0.02, 0.02, Z_CASE - Z_LOW), at=(0, D / 2 - 0.012, (Z_LOW + Z_CASE) / 2), material=WALNUT, name='back_wall')
for k in range(2):
    kit.box((W - 2 * POST - 0.08 - k * 0.04, 0.006, Z_CASE - Z_LOW - 0.1 - k * 0.04), at=(0, D / 2 - 0.0005 + k * 0.004, (Z_LOW + Z_CASE) / 2),
            material=(OAK if k == 0 else WALNUT), bevel=0.003, name='back_panel')
star = [(0.06 * (1 if i % 2 == 0 else 0.42) * math.cos(math.pi / 2 + math.pi * i / 5), 0.06 * (1 if i % 2 == 0 else 0.42) * math.sin(math.pi / 2 + math.pi * i / 5)) for i in range(10)]
st = extrude(star, 0.006, name='star'); xform(st, rot=(-90, 0, 0), loc=(0, D / 2 + 0.0085, (Z_LOW + Z_CASE) / 2)); kit.finish(st, BRASS, bevel=0.0015)
kit.torus(0.08, 0.004, at=(0, D / 2 + 0.0065, (Z_LOW + Z_CASE) / 2), rot=(90, 0, 0), material=BRASS, major=48, minor=8, name='star_ring')
# drape with soft vertical folds hanging inside the back wall
bm = bmesh.new(); NX, NZ = 48, 8; g = {}
for i in range(NX + 1):
    for j in range(NZ + 1):
        x = -(W / 2 - POST) + (W - 2 * POST) * i / NX; z = Z_LOW + 0.02 + (Z_CASE - Z_LOW - 0.05) * j / NZ
        y = D / 2 - 0.03 - 0.012 * (0.5 + 0.5 * math.sin(i / NX * math.tau * 7)) * (0.6 + 0.4 * (1 - j / NZ))
        g[i, j] = bm.verts.new((x, y, z))
for i in range(NX):
    for j in range(NZ):
        bm.faces.new((g[i, j], g[i + 1, j], g[i + 1, j + 1], g[i, j + 1]))
drape = _mesh_obj('drape', bm); solidify(drape, 0.004); kit.finish(drape, DRAPE, smooth=60)
GT = 0.006
gz0, gz1 = Z_LOW + 0.03, Z_CASE - 0.02
kit.box((W - 2 * POST + 0.004, GT, gz1 - gz0), at=(0, FY + 0.03, (gz0 + gz1) / 2), material=GLASS, name='glass_front')
for sx in (-1, 1):
    kit.box((GT, D - 2 * POST + 0.004, gz1 - gz0), at=(sx * (W / 2 - 0.03), 0, (gz0 + gz1) / 2), material=GLASS, name='glass_side')
for z in (gz0 - 0.006, gz1 + 0.006):
    kit.box((W - 2 * POST + 0.01, 0.024, 0.016), at=(0, FY + 0.03, z), material=WALNUT, bevel=0.002, name='glass_rail')
    for sx in (-1, 1):
        kit.box((0.024, D - 2 * POST + 0.01, 0.016), at=(sx * (W / 2 - 0.03), 0, z), material=WALNUT, bevel=0.002, name='glass_rail')
# warm lamp strip hidden under the frieze, inside the front
kit.box((W - 2 * POST - 0.04, 0.02, 0.012), at=(0, FY + 0.06, Z_CASE - 0.03), material=GLOW, name='case_light')

# ---- frieze with recessed red panels and brass corner blocks, then the flared cornice
kit.box((W + 0.016, D + 0.016, Z_FR - Z_CASE), at=(0, 0, (Z_CASE + Z_FR) / 2), material=WALNUT, bevel=0.003, name='frieze')
FH = Z_FR - Z_CASE
for sx in (-1, 1):
    kit.box((0.006, D - 2 * POST - 0.05, FH * 0.42), at=(sx * (W / 2 + 0.009), 0, (Z_CASE + Z_FR) / 2), material=VELVET, bevel=0.0015, name='frieze_panel')
    for sy in (-1, 1):
        x, y = sx * (W / 2 - POST / 2 + 0.008), sy * (D / 2 - POST / 2 + 0.008)
        for fx, fy in ((sx, 0), (0, sy)):
            at = Vector((x + fx * (POST / 2 + 0.004), y + fy * (POST / 2 + 0.004), (Z_CASE + Z_FR) / 2))
            kit.box((0.008 if fx else 0.046, 0.008 if fy else 0.046, 0.046), at=at, material=BRASS, bevel=0.002, name='rosette')
            kit.box((0.012 if fx else 0.022, 0.012 if fy else 0.022, 0.022), at=at + Vector((fx * 0.003, fy * 0.003, 0)), material=DARKWOOD,
                    bevel=0.002, name='rosette_centre')
for sy in (-1, 1):
    kit.box((W - 2 * POST - 0.05, 0.006, FH * 0.42), at=(0, sy * (D / 2 + 0.009), (Z_CASE + Z_FR) / 2), material=VELVET, bevel=0.0015, name='frieze_panel')
def cap_ring(z, grow, r=0.012):
    return [(x, y, z) for x, y in rrect(W + 0.016 + 2 * grow, D + 0.016 + 2 * grow, r + grow * 0.2, seg=3)]
cap = loft([cap_ring(Z_FR, 0.0), cap_ring(Z_FR + 0.012, 0.004), cap_ring(Z_FR + 0.03, 0.016), cap_ring(Z_FR + 0.055, 0.042),
            cap_ring(Z_FR + 0.075, 0.058), cap_ring(Z_FR + 0.085, 0.062), cap_ring(Z_TOP, 0.062)], name='cornice', smooth=30)
kit.finish(cap, DARKWOOD, bevel=0.002)
kit.box((W + 0.02, D + 0.02, 0.008), at=(0, 0, Z_FR + 0.004), material=BRASS, name='cornice_trim')
# stepped field on top of the cornice with a brass bead round it
kit.box((W - 0.06, D - 0.06, 0.016), at=(0, 0, Z_TOP + 0.008 - 0.002), material=WALNUT, bevel=0.005, segments=2, name='top_field')
tf = [(x, y, Z_TOP + 0.001) for x, y in rrect(W - 0.03, D - 0.03, 0.02, seg=4)]
sweep(tf, circle2(0.004, 8), name='top_bead', loop=True, material=BRASS, smooth=60)

# ---- front controls: card slot plate with the arched sunburst lamp, coin plate with slot and arrow, push button
CP = Vector((-0.09, FY - 0.0035, 0.62))
cardp = plate(0.31, 0.09, 0.007, CP, BRASS, name='card_plate')
sl = kit.box((0.23, 0.02, 0.014), at=CP + Vector((0.015, -0.006, -0.006)), name='cardslot'); sl.data.materials.clear(); sl.data.materials.append(SLOT)
cut(cardp, sl)
AC = CP + Vector((-0.075, 0, 0.045))
AR = 1.25
arch = extrude([(AR * 0.05 * math.cos(math.pi * k / 20), AR * 0.05 * math.sin(math.pi * k / 20)) for k in range(21)] +
               [(AR * 0.037 * math.cos(math.pi * k / 20), AR * 0.037 * math.sin(math.pi * k / 20)) for k in range(20, -1, -1)],
               0.01, name='arch')
xform(arch, rot=(90, 0, 0), loc=AC + Vector((0, 0.003, 0)))
kit.finish(arch, BRASS, bevel=0.0015)
lampdisc = extrude([(AR * 0.037 * math.cos(math.pi * k / 20), AR * 0.037 * math.sin(math.pi * k / 20)) for k in range(21)], 0.006, name='lamp')
xform(lampdisc, rot=(90, 0, 0), loc=AC + Vector((0, 0.004, 0)))
kit.finish(lampdisc, LAMP)
for k in range(1, 8):
    a = math.pi * k / 8
    rod(AC + Vector((0.01 * math.cos(a), -0.0035, 0.01 * math.sin(a))), AC + Vector((AR * 0.034 * math.cos(a), -0.0035, AR * 0.034 * math.sin(a))),
        0.0016, material=BRASS, verts=6, name='ray')
kit.cyl(0.009, 0.004, at=AC + Vector((0, -0.003, 0.004)), rot=(90, 0, 0), material=BRASS, verts=16, name='ray_hub')
KP = Vector((0.23, FY - 0.0035, 0.8))
coinp = plate(0.09, 0.18, 0.007, KP, BRASS, name='coin_plate')
cs = kit.box((0.009, 0.02, 0.046), at=KP + Vector((0, -0.006, 0.042)), name='coinslot'); cs.data.materials.clear(); cs.data.materials.append(SLOT)
cut(coinp, cs)
kit.torus(0.019, 0.003, at=KP + Vector((0, -0.0075, 0.042)), rot=(90, 0, 0), material=BRASS, major=24, minor=8, name='coin_ring')
arrow = [(-0.004, 0.02), (0.004, 0.02), (0.004, -0.004), (0.013, -0.004), (0.0, -0.024), (-0.013, -0.004), (-0.004, -0.004)]
arw = extrude([(x * 1.2, y * 1.2) for x, y in arrow], 0.003, name='arrow'); xform(arw, rot=(90, 0, 0), loc=KP + Vector((0, -0.0062, -0.035))); kit.finish(arw, SLOT, bevel=0.0008)
BP = Vector((0.23, FY, 0.6))
kit.cyl(0.034, 0.012, at=BP + Vector((0, -0.006, 0)), rot=(90, 0, 0), material=BRASS, verts=32, bevel=0.003, name='button_bezel')
btn = kit.sphere(0.026, at=BP + Vector((0, -0.012, 0)), scale=(1, 0.55, 1), material=BUTTON, segs=24, rings=12, name='button')

# ---- crystal ball on a brass stand in the front-left corner, glowing core
BCN = Vector((-0.2, FY + 0.17, Z_LOW + 0.02))
kit.lathe([(0, 0), (0.07, 0), (0.072, 0.008), (0.05, 0.016), (0.035, 0.03), (0.055, 0.05), (0.05, 0.056), (0, 0.056)],
          at=BCN, material=BRASS, steps=40, name='ball_stand')
BR = 0.105; BC = BCN + Vector((0, 0, 0.05 + BR))
kit.sphere(BR, at=BC, material=BALL, segs=48, rings=24, name='crystal_ball')
kit.sphere(0.035, at=BC + Vector((0, 0, -0.01)), material=GLOW, segs=20, rings=10, name='ball_glow')

# ---- three-digit display on the deck, front right, angled up to the viewer
DP = Vector((0.15, FY + 0.15, Z_LOW + 0.045))
disp = kit.box((0.2, 0.09, 0.04), name='display', material=DARKWOOD, bevel=0.006, segments=2)
xform(disp, rot=(-20, 0, 0), loc=DP)
for k in range(3):
    win = kit.box((0.042, 0.052, 0.006), name='digit', material=DIGIT, bevel=0.002)
    win.matrix_world = Matrix.Translation(DP) @ Matrix.Rotation(math.radians(-20), 4, 'X') @ Matrix.Translation((-0.058 + k * 0.058, 0, 0.019))
for k in range(2):  # the colon between the digits
    kit.sphere(0.004, at=DP + Matrix.Rotation(math.radians(-20), 3, 'X') @ Vector((-0.029 + k * 0.058, 0, 0.021)), material=DIGIT, segs=8, rings=4, name='colon')

# ---- the fortune teller: robed bust behind the deck, shaved head, beard and dark glasses
FC = Vector((-0.04, 0.1, Z_LOW + 0.02))
robe = kit.lathe([(0, 0), (0.2, 0), (0.215, 0.08), (0.22, 0.16), (0.205, 0.25), (0.17, 0.32), (0.12, 0.37), (0.06, 0.4), (0.0, 0.405)],
                 material=ROBE, steps=48, name='robe')
xform(robe, scale=(1, 0.72, 1)); xform(robe, loc=FC)
kit.torus(0.06, 0.012, at=FC + Vector((0, 0, 0.392)), material=BRASS, major=32, minor=10, name='collar')
neck = kit.cyl(0.04, 0.07, at=FC + Vector((0, 0, 0.42)), material=SKIN, verts=24, name='neck')
HC = FC + Vector((0, -0.005, 0.53))
head = kit.sphere(0.085, at=HC, scale=(0.88, 1.0, 1.15), material=SKIN, segs=40, rings=24, name='head')
for sx in (-1, 1):
    kit.sphere(0.022, at=HC + Vector((sx * 0.076, 0.01, 0.0)), scale=(0.45, 0.8, 1.0), material=SKIN, segs=16, rings=10, name='ear')
kit.sphere(0.02, at=HC + Vector((0, -0.085, -0.015)), scale=(0.8, 0.9, 1.1), material=SKIN, segs=16, rings=10, name='nose')
beard = kit.sphere(0.08, at=HC + Vector((0, -0.012, -0.045)), scale=(0.84, 0.93, 0.8), segs=32, rings=16, name='beard')
bc = kit.box((0.3, 0.3, 0.3), at=HC + Vector((0, 0.1, 0.12)), rot=(-28, 0, 0), name='beardcut'); kit.boolean(beard, bc)
kit.finish(beard, BEARD)
kit.sphere(0.03, at=HC + Vector((0, -0.075, -0.052)), scale=(1.2, 0.5, 0.35), material=SKIN, segs=16, rings=8, name='lips')
for sx in (-1, 1):
    kit.sphere(0.026, at=HC + Vector((sx * 0.032, -0.072, 0.018)), scale=(1.1, 0.35, 0.8), material=SHADES, segs=20, rings=10, name='lens')
rod(HC + Vector((-0.012, -0.08, 0.022)), HC + Vector((0.012, -0.08, 0.022)), 0.0025, material=BRASS, verts=8, name='bridge')
for sx in (-1, 1):
    rod(HC + Vector((sx * 0.056, -0.07, 0.02)), HC + Vector((sx * 0.076, 0.0, 0.02)), 0.0025, material=SHADES, verts=8, name='temple')

def arm(shoulder, elbow, wrist, name):
    pts = catmull([shoulder, elbow, wrist], 8)
    sweep(pts, circle2(0.045, 16), name=name, material=ROBE, smooth=50)
    d = (Vector(wrist) - Vector(elbow)).normalized()
    cuff = kit.torus(0.044, 0.01, material=BRASS, major=24, minor=8, name='cuff')
    cuff.rotation_mode = 'QUATERNION'; cuff.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d); cuff.location = Vector(wrist) - d * 0.004
    return d

def hand(wrist, d, palm_down=True, spread=1.0, curl=0.0, name='hand'):
    side = d.cross(Vector((0, 0, 1))).normalized(); up = side.cross(d).normalized()
    pc = Vector(wrist) + d * 0.045
    palm = kit.sphere(0.04, scale=(1.0, 1.0, 0.45), segs=20, rings=12, material=SKIN, name=name)
    palm.rotation_mode = 'QUATERNION'; palm.rotation_quaternion = Matrix((side, d, up)).transposed().to_quaternion(); palm.location = pc
    for k in range(4):
        off = (k - 1.5) * 0.019 * spread
        base = pc + d * 0.032 + side * off
        tip = base + (d * math.cos(curl) - up * math.sin(curl)) * (0.05 - abs(k - 1.5) * 0.006) + side * off * 0.35
        rod(base, tip, 0.0075, material=SKIN, verts=10, name='finger')
        kit.sphere(0.0075, at=tip, material=SKIN, segs=10, rings=6, name='fingertip')
    tb = pc + side * 0.03 - d * 0.005
    tt = tb + side * 0.03 + d * 0.025 - up * 0.005
    rod(tb, tt, 0.009, material=SKIN, verts=10, name='thumb'); kit.sphere(0.009, at=tt, material=SKIN, segs=10, rings=6, name='thumbtip')

# right arm (viewer's left) down to the crystal ball, left arm forward over the display
S_R = FC + Vector((-0.16, -0.01, 0.33)); S_L = FC + Vector((0.16, -0.01, 0.33))
w_r = BC + Vector((0.04, 0.07, 0.11))
d_r = arm(S_R, FC + Vector((-0.24, -0.08, 0.2)), w_r, 'arm_r')
hand(w_r, (BC + Vector((0, 0, BR + 0.02)) - w_r).normalized(), spread=1.15, curl=0.5, name='hand_r')
w_l = DP + Vector((-0.02, 0.1, 0.13))
d_l = arm(S_L, FC + Vector((0.25, -0.06, 0.2)), w_l, 'arm_l')
hand(w_l, (DP + Vector((0.0, -0.01, 0.07)) - w_l).normalized(), spread=1.35, curl=0.25, name='hand_l')

# ---- "DrDre" across the top of the front glass: tall D's, small r's and e, gold leaf
FONT = '/System/Library/Fonts/Supplemental/Arial Black.ttf'
x = -0.27
for ch, size in (('D', 0.2), ('R', 0.1), ('D', 0.2), ('R', 0.1), ('E', 0.1)):
    cu = bpy.data.curves.new('lt', 'FONT'); cu.body = ch; cu.size = size; cu.extrude = 0.0015
    if os.path.exists(FONT): cu.font = bpy.data.fonts.load(FONT)
    o = bpy.data.objects.new('lettering', cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    xs = [v.co.x for v in o.data.vertices]; w = max(xs) - min(xs)
    for v in o.data.vertices: v.co.x -= min(xs)
    o.rotation_euler = (math.radians(90), 0, 0); o.location = (x, FY + 0.03 - GT / 2 - 0.0016, Z_CASE - 0.25)
    o.data.materials.clear(); o.data.materials.append(BRASS)
    x += w + 0.01

kit.export('fortune-telling-machine')
