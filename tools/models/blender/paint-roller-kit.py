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
# Paint roller kit, after Sara Gold's drawing: a framed panel standing on edge, half painted - a band of wet teal paint
# with a wavy lower edge and drips running down - with the roller pressed against it at the bottom of the band, its
# wire frame bending out to a turned wooden handle that rests on the floor, a drip on the floor, and the block letters
# "XIII" lying flat in front. Colours are from the mural palette (the drawing is pencil).
OAK = kit.mat('oak', rough=0.55, name='frame_oak')
PRIMER = kit.mat('paper', rough=0.7, name='primer')
PLY = kit.mat('#a88c68', rough=0.75, name='plywood')
PAINT = kit.mat('#23707a', rough=0.12, name='wet_paint')
NAP = kit.mat('#2a7a84', rough=0.95, name='roller_nap')
CORE = kit.mat('cream', rough=0.5, name='roller_core')
WIRE = kit.mat('#b9bec5', rough=0.28, metal=0.9, name='frame_wire')
CAGE = kit.mat('#2a2826', rough=0.45, name='cage_plastic')
HANDLE = kit.mat('#b4813f', rough=0.45, name='handle_wood')
BRASS = kit.mat('brass', rough=0.32, metal=0.85, name='ferrule')

PW, PH, PT = 0.30, 0.50, 0.04       # panel width / height / thickness
RAIL = 0.018                        # frame rail width
BOARD_Y = -PT / 2 + 0.006           # board face sits 6 mm behind the frame front

# ---- frame: four mitred-looking rails (one solid with the window cut out), board and back
frame = kit.box((PW, PT, PH), at=(0, 0, PH / 2), name='frame')
win = kit.box((PW - 2 * RAIL, PT + 0.01, PH - 2 * RAIL), at=(0, 0, PH / 2), name='win')
kit.boolean(frame, win)
kit.finish(frame, OAK, bevel=0.0025, segments=2)
# inner lip: a small bead round the opening
lip_pts = [(-PW / 2 + RAIL, -PT / 2 + 0.002, RAIL), (PW / 2 - RAIL, -PT / 2 + 0.002, RAIL),
           (PW / 2 - RAIL, -PT / 2 + 0.002, PH - RAIL), (-PW / 2 + RAIL, -PT / 2 + 0.002, PH - RAIL)]
board = kit.box((PW - 2 * RAIL + 0.002, 0.008, PH - 2 * RAIL + 0.002), at=(0, BOARD_Y + 0.004, PH / 2), material=PRIMER, name='board')
back = kit.box((PW - 2 * RAIL + 0.002, 0.006, PH - 2 * RAIL + 0.002), at=(0, PT / 2 - 0.016, PH / 2), material=PLY, name='backboard')
# back of the panel: a cross brace standing proud of the backing board, and a hanging wire between two screw eyes
kit.box((PW - 2 * RAIL, 0.012, 0.024), at=(0, PT / 2 - 0.0075, PH * 0.52), material=OAK, bevel=0.0018, name='brace_h')
kit.box((0.024, 0.0118, PH - 2 * RAIL), at=(0, PT / 2 - 0.0076, PH / 2), material=OAK, bevel=0.0018, name='brace_v')
for x in (-1, 1):
    kit.torus(0.0045, 0.0011, at=(x * (PW / 2 - RAIL - 0.008), PT / 2 + 0.0035, PH * 0.74), rot=(0, 90, 0), material=WIRE,
              major=16, minor=6, name='screw_eye')
tube([(-(PW / 2 - RAIL - 0.008), PT / 2 + 0.0035, PH * 0.74 - 0.004), (-0.05, PT / 2 + 0.006, PH * 0.79),
      (0, PT / 2 + 0.0065, PH * 0.805), (0.05, PT / 2 + 0.006, PH * 0.79), ((PW / 2 - RAIL - 0.008), PT / 2 + 0.0035, PH * 0.74 - 0.004)],
     0.0009, material=WIRE, name='hanging_wire')
for x in (-1, 1):
    for z in (0.12, PH - 0.12):
        kit.box((0.028, 0.004, 0.01), at=(x * (PW / 2 - RAIL + 0.004), PT / 2 - 0.011, z), material=WIRE, bevel=0.001, name='turn_button')

# ---- roller placement
ZC = 0.212                    # roller axis height
RR = 0.025; RL = 0.23         # cover radius / length
RX0, RX1 = -0.07, -0.07 + RL  # cover ends (overhangs the right edge like the drawing)
PAINT_Y = BOARD_Y - 0.0012    # paint surface
RY = PAINT_Y - RR             # roller axis y (touching the paint)

# ---- paint band: straight top, wavy bottom wrapping the roller, drips
TOPZ = PH * 0.77
xl, xr = -PW / 2 + RAIL, PW / 2 - RAIL
drips = [(-0.09, 0.03, 0.008), (-0.03, 0.085, 0.0105), (0.04, 0.045, 0.0075), (0.1, 0.028, 0.0065)]
def wave(x):
    return ZC - 0.004 + 0.02 * math.sin(x * 21 + 2.2) + 0.006 * math.sin(x * 57)
bottom = []
N = 90
for i in range(N + 1):
    x = xr - (xr - xl) * i / N
    z = wave(x)
    if RX0 - 0.012 < x < RX1:  # the roller squeezes a bead of paint out under it
        z = min(z, ZC - 0.016 - 0.004 * math.sin((x - RX0) * 40))
    bottom.append((x, z))
poly = [(xl, TOPZ), (xr, TOPZ)] + bottom[0:]   # counter-clockwise when seen from the front (x right, z up)
# insert drips as fingers hanging from the bottom edge
out = []
for (x, z) in poly:
    out.append((x, z))
fingers = []
for dx, dl, dw in drips:
    pts = []
    zt = wave(dx) if not (RX0 - 0.012 < dx < RX1) else ZC - 0.016 - 0.004 * math.sin((dx - RX0) * 40)
    for k in range(13):
        a = math.pi * k / 12
        pts.append((dx + dw * 0.5 * math.cos(a), zt - dl + dw * 0.55 * math.sin(-a) if False else 0))
    fingers.append((dx, dl, dw, zt))
def drip_outline(dx, dl, dw, zt):
    pts = [(dx + dw * 0.45, zt + 0.004)]
    for k in range(6):
        t = k / 5; pts.append((dx + dw * (0.38 - 0.08 * t), zt - dl * 0.7 * t))
    for k in range(13):
        a = -math.pi * k / 12
        pts.append((dx + dw * 0.62 * math.cos(a), zt - dl + dw * 0.62 * math.sin(a)))
    for k in range(6):
        t = 1 - k / 5; pts.append((dx - dw * (0.38 - 0.08 * t), zt - dl * 0.7 * t))
    pts.append((dx - dw * 0.45, zt + 0.004))
    return pts[::-1]
paint = extrude([(x, z) for x, z in poly], 0.0012, at=(0, BOARD_Y, 0), rot=(90, 0, 0), name='paint')
kit.finish(paint, PAINT, bevel=0.0005, segments=1)
for dx, dl, dw, zt in fingers:
    d = extrude(drip_outline(dx, dl, dw, zt), 0.0014, at=(0, BOARD_Y + 0.0001, 0), rot=(90, 0, 0), name='drip')
    kit.finish(d, PAINT, bevel=0.0006, segments=2)
# a loose drop lower down on the left, and a puddle on the floor
drop = drip_outline(-0.118, 0.03, 0.0065, ZC - 0.075)
extrude(drop, 0.0013, at=(0, BOARD_Y + 0.0001, 0), rot=(90, 0, 0), material=PAINT, name='drop')
puddle = kit.sphere(1.0, segs=32, rings=12, name='puddle')
for v in puddle.data.vertices:
    v.co.x *= 0.022 * (1 + 0.15 * math.sin(3 * math.atan2(v.co.y, v.co.x))); v.co.y *= 0.014; v.co.z = max(0.0, v.co.z) * 0.0025
xform(puddle, loc=(0.02, -PT / 2 - 0.03, 0.0))
kit.finish(puddle, PAINT)

# ---- roller cover (fuzzy nap, cream core showing at the ends) and its cage end caps
cover = kit.lathe([(0.0165, 0), (0.0228, 0), (0.0248, 0.0025), (RR, 0.006), (RR, RL - 0.006), (0.0248, RL - 0.0025),
                   (0.0228, RL), (0.0165, RL), (0.0165, 0)], steps=48, material=NAP, name='cover')
core = kit.lathe([(0.0148, -0.0005), (0.0168, -0.0005), (0.0168, RL + 0.0005), (0.0148, RL + 0.0005), (0.0148, -0.0005)],
                 steps=48, material=CORE, name='core')
caps = []
for zc, sgn in ((0.004, 1), (RL - 0.004, -1)):
    caps.append(kit.lathe([(0, 0), (0.0149, 0), (0.0149, 0.004), (0.005, 0.004), (0.005, 0.0025), (0, 0.0025)],
                          at=(0, 0, zc - (0.004 if sgn < 0 else 0) + (0 if sgn > 0 else 0)), material=CAGE, steps=32, name='cage_cap'))
for o in [cover, core] + caps:
    xform(o, rot=(0, 90, 0))
    xform(o, loc=(RX0, RY, ZC))

# ---- wire frame: axle out of the right end, down and away from the panel, back under the roller, into the handle
A0 = Vector((RX1 - 0.01, RY, ZC)); A1 = Vector((RX1 + 0.022, RY, ZC))
B = Vector((RX1 + 0.022, RY - 0.035, ZC - 0.05))
HX = (RX0 + RX1) / 2 + 0.045
Cc = Vector((HX, RY - 0.05, ZC - 0.058))
HANG = math.radians(33)                     # handle tilt from vertical, toward the viewer
HD = Vector((0, -math.sin(HANG), -math.cos(HANG)))
F0 = Cc + HD * 0.01                         # into the ferrule
wire = sweep(fillet([A0, A1, B, Cc, F0], 0.012, seg=8), circle2(0.0032, 10), name='wire', material=WIRE, smooth=60)
# handle: brass ferrule then a turned wooden grip; length chosen so the end rests on the floor
FER = 0.022
GL = (Cc.z - 0.0165 * math.sin(HANG)) / math.cos(HANG) - FER
fer = kit.lathe([(0, 0), (0.0105, 0), (0.0112, 0.002), (0.0112, FER - 0.002), (0.0105, FER), (0, FER)], material=BRASS,
                steps=32, name='ferrule')
grip = kit.lathe([(0, 0), (0.0118, 0), (0.0135, 0.01), (0.0155, GL * 0.35), (0.0165, GL * 0.75), (0.016, GL - 0.012),
                  (0.0135, GL - 0.003), (0.008, GL), (0, GL)], at=(0, 0, FER), material=HANDLE, steps=32, name='grip')
q = Vector((0, 0, 1)).rotation_difference(HD)
for o in (fer, grip):
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q; o.location = Cc
print('PAINTROLLER grip length', round(GL, 3))

# ---- "XIII" block letters lying flat on the floor in front of the panel
FONT = '/System/Library/Fonts/Supplemental/Arial Black.ttf'
cu = bpy.data.curves.new('xiii', 'FONT'); cu.body = 'XIII'; cu.size = 0.105; cu.extrude = 0.007; cu.space_character = 1.15
if os.path.exists(FONT): cu.font = bpy.data.fonts.load(FONT)
cu.align_x = 'CENTER'
letters = bpy.data.objects.new('xiii', cu); bpy.context.collection.objects.link(letters)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = letters; letters.select_set(True)
bpy.ops.object.convert(target='MESH'); letters = bpy.context.object
xs = [v.co.x for v in letters.data.vertices]; ys = [v.co.y for v in letters.data.vertices]
for v in letters.data.vertices:
    v.co.x -= (min(xs) + max(xs)) / 2; v.co.y -= (min(ys) + max(ys)) / 2; v.co.z += 0.007
letters.location = (-0.04, -PT / 2 - 0.105, 0.0); letters.rotation_euler = (0, 0, math.radians(-4))
kit.finish(letters, PAINT, bevel=0.0012, segments=2)


kit.export('paint-roller-kit')
