"""Bicycle, after Sophia Li's drawing.

As drawn: a long, upright cruiser seen from its chain side. Thick tyres on spoked wheels (eight spokes) with a big
rear hub and a barrel front hub; a big bean saddle with "SC" on top and a "13" backrest standing behind it; a very wide
straight handlebar with grips at both ends on a stem; the frame meets at the front in a sideways "IYA" barrel that the
fork hangs from; a solid chainring disc with the crank pointing down to a flat pedal; and a small platform on a post
over the down tube. Line-only drawing, so the colours are USC's: cardinal frame, gold lettering, leather saddle.
Invented or guessed: the far-side crank and pedal (opposite, as on any bike), the chain, and the platform's purpose
(drawn as a little oak shelf).
Length runs along X (front wheel +X) so the turntable opens on the chain side.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
from mathutils import Vector, Matrix


# ---------------------------------------------------------------- helpers
def _catmull(points, subdiv):
    P = [Vector(p) for p in points]
    if len(P) < 3 or subdiv <= 1:
        return P
    out = []
    n = len(P)
    for i in range(n - 1):
        p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, n - 1)]
        for k in range(subdiv):
            t = k / subdiv; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return out


def tube(points, r, material=None, sides=10, subdiv=1, closed=False, name='tube'):
    P = _catmull(points, subdiv) if not closed else [Vector(p) for p in points]
    n = len(P)
    rad = (lambda t, i: r) if not callable(r) else r
    T = [((P[(i + 1) % n] - P[i - 1]) if closed else (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])).normalized() for i in range(n)]
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    verts, faces = [], []
    for i in range(n):
        if i:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-9:
                N = Matrix.Rotation(T[i - 1].angle(T[i]), 3, b.normalized()) @ N
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N); rr = rad(i / max(n - 1, 1), i)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(P[i] + (N * math.cos(a) + B * math.sin(a)) * rr)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, j * sides + k2, j * sides + k))
    if not closed:
        c0 = len(verts); verts.append(P[0]); c1 = len(verts); verts.append(P[-1])
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k)); faces.append((c1, (n - 1) * sides + k, (n - 1) * sides + k2))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, smooth=50)


def rod(p0, p1, r, material, verts=20, bevel=0.0, name='rod', r2=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = kit.cyl(r, d.length, material=material, verts=verts, bevel=bevel, r2=r2, name=name)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.location = (p0 + p1) / 2
    return o


def lat_cyl(r, length, at, material, verts=32, bevel=0.0, name='lat'):
    """Cylinder along Y (the bike's lateral axis)."""
    return kit.cyl(r, length, at=at, rot=(90, 0, 0), material=material, verts=verts, bevel=bevel, name=name)


def lat_lathe(profile, at, material, steps=48, name='lathe'):
    """Lathe with its axis along Y; profile (r, y)."""
    o = kit.lathe([(r, -y) for r, y in profile], material=material, steps=steps, name=name)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = at
    return o


# ---------------------------------------------------------------- materials
M_FRAME = kit.mat('cardinal', rough=0.3, metal=0.35, name='cardinal_paint')
M_GOLD = kit.mat('#d4a640', rough=0.28, metal=0.95, name='gold')
M_TIRE = kit.mat('rubber', rough=0.82, name='tire')
M_CHROME = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
M_STEEL = kit.mat('steel', rough=0.3, metal=0.9, name='spoke_steel')
M_LEATHER = kit.mat('#4a2c1a', rough=0.55, name='leather')
M_GRIP = kit.mat('#3a2418', rough=0.7, name='grip')
M_DARK = kit.mat('gunmetal', rough=0.4, metal=0.8, name='chain')
M_PEDAL = kit.mat('#1e1d1c', rough=0.6, name='pedal_rubber')
M_OAK = kit.mat('oak', rough=0.6, name='oak')

# ---------------------------------------------------------------- key points (metres, X forward, Z up)
RW = 0.31                         # wheel radius to the tyre tread
REAR = Vector((-0.56, 0, RW))
FRONT = Vector((0.56, 0, RW))
BB = Vector((-0.05, 0, 0.225))
SEAT = Vector((-0.22, 0, 0.745))  # top of the seat post
HEAD = Vector((0.47, 0, 0.70))    # the IYA barrel
BAR = Vector((0.39, 0, 0.96))     # handlebar centre
TR = 0.023                        # main tube radius


# ---------------------------------------------------------------- wheels
def wheel(c, hub_big):
    parts = []
    tr = 0.026
    parts.append(kit.torus(RW - tr, tr, at=c, rot=(90, 0, 0), material=M_TIRE, major=72, minor=14, name='tire'))
    # tread band: thin raised ribs round the crown
    for dy in (-0.012, 0.0, 0.012):
        t = kit.torus(RW - 0.0025, 0.0028, at=(c.x, c.y + dy, c.z), rot=(90, 0, 0), material=M_TIRE, major=72, minor=6, name='tread_rib')
    # rim: a chrome channel
    rim = lat_lathe([(RW - 0.05, -0.016), (RW - 0.036, -0.019), (RW - 0.032, -0.012), (RW - 0.034, 0.0), (RW - 0.032, 0.012),
                     (RW - 0.036, 0.019), (RW - 0.05, 0.016), (RW - 0.056, 0.0), (RW - 0.05, -0.016)], c, M_CHROME, steps=72, name='rim')
    # hub
    if hub_big:
        lat_lathe([(0.0, -0.08), (0.03, -0.08), (0.07, -0.05), (0.072, -0.04), (0.045, -0.03), (0.04, 0.0), (0.045, 0.03),
                   (0.072, 0.04), (0.07, 0.05), (0.03, 0.08), (0.0, 0.08)], c, M_CHROME, steps=48, name='rear_hub')
        fl = 0.045
    else:
        lat_cyl(0.04, 0.15, c, M_CHROME, verts=40, bevel=0.006, name='front_hub')
        for s in (-1, 1):
            lat_cyl(0.048, 0.008, (c.x, c.y + s * 0.07, c.z), M_CHROME, verts=40, bevel=0.002, name='hub_flange')
        fl = 0.07
    # eight spokes, alternating flanges
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        s = 1 if k % 2 else -1
        p0 = c + Vector((0.035 * math.cos(a), s * fl, 0.035 * math.sin(a)))
        p1 = c + Vector(((RW - 0.052) * math.cos(a), s * 0.004, (RW - 0.052) * math.sin(a)))
        rod(p0, p1, 0.0028, M_STEEL, verts=8, name='spoke')
    # axle nuts
    for s in (-1, 1):
        lat_cyl(0.012, 0.02, (c.x, c.y + s * (0.09 if hub_big else 0.085), c.z), M_CHROME, verts=6, bevel=0.002, name='axle_nut')


wheel(REAR, True)
wheel(FRONT, False)

# ---------------------------------------------------------------- frame
rod(BB, SEAT + Vector((0, 0, -0.02)), TR, M_FRAME, name='seat_tube')
rod(SEAT + Vector((0.01, 0, -0.08)), HEAD + Vector((-0.04, 0, 0.012)), TR, M_FRAME, name='top_tube')
rod(HEAD + Vector((-0.03, 0, -0.035)), BB, TR * 1.1, M_FRAME, name='down_tube')
for s in (-1, 1):
    rod(REAR + Vector((0, s * 0.07, 0)), SEAT + Vector((0.01, s * 0.022, -0.09)), 0.013, M_FRAME, name='seat_stay')
    rod(REAR + Vector((0, s * 0.07, 0)), BB + Vector((0, s * 0.045, 0)), 0.014, M_FRAME, name='chain_stay')
    # dropouts
    kit.box((0.05, 0.012, 0.05), at=(REAR.x, s * 0.07, REAR.z), material=M_FRAME, bevel=0.006, name='dropout')
kit.sphere(0.032, at=BB, scale=(1, 1.6, 1), material=M_FRAME, segs=24, rings=12, name='bb_shell')
lat_cyl(0.034, 0.12, BB, M_FRAME, verts=32, bevel=0.006, name='bb_barrel')
# seat post + clamp
rod(SEAT + Vector((0.02, 0, -0.11)), SEAT + Vector((0, 0, 0.03)), 0.016, M_CHROME, name='seat_post')
kit.cyl(0.026, 0.03, at=SEAT + Vector((0.015, 0, -0.075)), rot=(0, -18, 0), material=M_FRAME, verts=24, bevel=0.004, name='seat_clamp')

# the IYA barrel at the head: a sideways cylinder the fork hangs from
HL = 0.24
lat_cyl(0.05, HL, HEAD, M_FRAME, verts=48, bevel=0.008, name='iya_barrel')
for s in (-1, 1):
    lat_cyl(0.054, 0.014, (HEAD.x, s * (HL / 2 - 0.005), HEAD.z), M_GOLD, verts=48, bevel=0.003, name='barrel_cap')
txt = kit.text('IYA', 0.06, 0.006, material=M_GOLD, name='iya_text')
# letters on the front (+X) face, reading toward +Y (as drawn)
txt.rotation_euler = (math.radians(90), 0, math.radians(90))
txt.location = (HEAD.x + 0.05, 0, HEAD.z)
# bend the text round the barrel
bpy.context.view_layer.objects.active = txt; txt.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for v in txt.data.vertices:
    dz = v.co.z - HEAD.z
    depth = v.co.x - (HEAD.x + 0.05)
    a = dz / 0.05
    rr = 0.05 + depth + 0.0025
    v.co.x = HEAD.x + rr * math.cos(a)
    v.co.z = HEAD.z + rr * math.sin(a)
txt.data.update()

# fork: two legs from the barrel down to the front hub
for s in (-1, 1):
    tube([(HEAD.x + 0.0, s * 0.075, HEAD.z - 0.02), (HEAD.x + 0.03, s * 0.08, HEAD.z - 0.2), (FRONT.x - 0.005, s * 0.08, FRONT.z + 0.08),
          (FRONT.x, s * 0.08, FRONT.z)], 0.017, M_FRAME, sides=16, subdiv=6, name='fork_leg')
    kit.box((0.04, 0.012, 0.04), at=(FRONT.x, s * 0.08, FRONT.z), material=M_FRAME, bevel=0.006, name='fork_tip')
# stem up to the bar
tube([HEAD + Vector((0, 0, 0.04)), HEAD + Vector((-0.02, 0, 0.16)), BAR + Vector((0.0, 0, -0.03)), BAR], 0.018, M_CHROME,
     sides=16, subdiv=6, name='stem')
kit.box((0.05, 0.06, 0.05), at=BAR, material=M_CHROME, bevel=0.01, name='bar_clamp')
# the very wide straight handlebar with grips at both ends
HW = 0.37
lat_cyl(0.02, 2 * HW, BAR, M_CHROME, verts=28, bevel=0.003, name='handlebar')
for s in (-1, 1):
    g = lat_lathe([(0.0, -0.075), (0.024, -0.075), (0.028, -0.068), (0.026, -0.03), (0.028, 0.0), (0.026, 0.03), (0.028, 0.068),
                   (0.024, 0.075), (0.0, 0.075)], (BAR.x, s * (HW - 0.07), BAR.z), M_GRIP, steps=32, name='grip')
    for k in range(5):
        lat_cyl(0.0285, 0.006, (BAR.x, s * (HW - 0.12 + k * 0.025), BAR.z), M_GRIP, verts=32, name='grip_ring')
    lat_cyl(0.029, 0.008, (BAR.x, s * (HW + 0.004), BAR.z), M_GOLD, verts=32, bevel=0.002, name='bar_end')

# ---------------------------------------------------------------- saddle: big bean with SC, and the 13 backrest
def bean():
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        # wide at the back, a pinched waist, rounded nose toward +X
        x = 0.135 * math.cos(a)
        w = 0.15 * (1 - 0.35 * (0.5 + 0.5 * math.cos(a)) ** 1.5) - 0.03 * math.exp(-((math.cos(a) - 0.25) / 0.25) ** 2)
        y = w * math.sin(a)
        pts.append((x, y))
    return pts


SZ = SEAT.z + 0.03
kit.box((0.09, 0.05, 0.025), at=(SEAT.x, 0, SZ - 0.004), material=M_DARK, bevel=0.006, name='saddle_rails')
sad = kit.extrude(bean(), 0.064, at=(SEAT.x + 0.01, 0, SZ + 0.006), material=M_LEATHER, bevel=0.026, segments=4, name='saddle')
# piping round the saddle's edge
pip = [(SEAT.x + 0.01 + x * 1.01, y * 1.01, SZ + 0.012) for x, y in bean()]
tube(pip, 0.0045, M_LEATHER, sides=8, closed=True, name='saddle_piping')
sc = kit.text('SC', 0.095, 0.004, rot=(0, 0, 0), material=M_GOLD, name='sc_text')
sc.location = (SEAT.x + 0.0, -0.005, SZ + 0.07)
# "13" backrest: thick gold numerals on a short post behind the saddle, facing forward (+X), reading toward +Y
rod((SEAT.x - 0.06, 0, SZ + 0.0), (SEAT.x - 0.135, 0, SZ + 0.085), 0.013, M_CHROME, name='backrest_post')
t13 = kit.text('13', 0.27, 0.04, material=M_GOLD, name='backrest_13')
t13.rotation_euler = (math.radians(90), 0, math.radians(90))
t13.location = (SEAT.x - 0.14, 0, SZ + 0.19)
# a cardinal backing pad under the numerals so the rider has something to lean on
kit.box((0.05, 0.22, 0.024), at=(SEAT.x - 0.14, 0, SZ + 0.088), material=M_LEATHER, bevel=0.009, name='backrest_pad')

# ---------------------------------------------------------------- drivetrain: solid chainring disc, cranks, pedals, chain
CY = -0.085                        # chain line (near side)
lat_cyl(0.105, 0.012, (BB.x, CY, BB.z), M_CHROME, verts=64, bevel=0.003, name='chainring')
for k in range(48):  # teeth
    a = 2 * math.pi * k / 48
    kit.box((0.008, 0.008, 0.01), at=(BB.x + 0.108 * math.cos(a), CY, BB.z + 0.108 * math.sin(a)),
            rot=(0, -math.degrees(a) + 90, 0), material=M_CHROME, bevel=0.0015, name='tooth')
lat_cyl(0.05, 0.016, (BB.x, CY - 0.004, BB.z), M_STEEL, verts=40, bevel=0.003, name='spider')
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.3
    lat_cyl(0.006, 0.008, (BB.x + 0.075 * math.cos(a), CY - 0.008, BB.z + 0.075 * math.sin(a)), M_STEEL, verts=6, name='ring_bolt')
lat_cyl(0.012, 0.22, BB, M_STEEL, verts=16, name='bb_axle')
CL = 0.155
for s, up in ((-1, -1), (1, 1)):
    y = s * 0.11
    rod((BB.x, y, BB.z), (BB.x, y, BB.z + up * CL), 0.014, M_CHROME, verts=16, name='crank')
    kit.box((0.04, 0.02, 0.04), at=(BB.x, y, BB.z), material=M_CHROME, bevel=0.008, name='crank_boss')
    # flat pedal plate, as drawn
    pz = BB.z + up * CL
    lat_cyl(0.007, 0.12, (BB.x, y + s * 0.06, pz), M_STEEL, verts=12, name='pedal_spindle')
    kit.box((0.085, 0.11, 0.022), at=(BB.x, y + s * 0.07, pz), material=M_PEDAL, bevel=0.005, name='pedal')
    kit.box((0.087, 0.112, 0.006), at=(BB.x, y + s * 0.07, pz), material=M_CHROME, bevel=0.002, name='pedal_frame')
# rear sprocket + chain loop
lat_cyl(0.045, 0.008, (REAR.x, CY, REAR.z), M_STEEL, verts=40, bevel=0.002, name='sprocket')


def chain_path():
    """The chain is the convex hull of the two sprockets."""
    pts = []
    for (cx, cz, r, n) in ((BB.x, BB.z, 0.109, 64), (REAR.x, REAR.z, 0.049, 32)):
        pts += [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    pts = sorted(set(pts))
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    hull = lo[:-1] + hi[:-1]
    # resample evenly so the links alternate cleanly
    P = [Vector(p) for p in hull]
    out = []; step = 0.008
    for a, b in zip(P, P[1:] + P[:1]):
        L = (b - a).length; n = max(1, int(L / step))
        out += [a + (b - a) * (i / n) for i in range(n)]
    return out


ch = chain_path()
tube([(p.x, CY, p.y) for p in ch], lambda t, i: 0.0045 if i % 2 else 0.0058, M_DARK, sides=6, closed=True, name='chain')

# ---------------------------------------------------------------- the little platform over the down tube
dt_a, dt_b = HEAD + Vector((-0.03, 0, -0.035)), BB
px = 0.11
tz = dt_b.z + (dt_a.z - dt_b.z) * (px - dt_b.x) / (dt_a.x - dt_b.x)
rod((px, 0, tz), (px, 0, 0.47), 0.011, M_FRAME, name='platform_post')
kit.box((0.17, 0.095, 0.016), at=(px, 0, 0.478), material=M_OAK, bevel=0.004, name='platform')
kit.box((0.05, 0.03, 0.008), at=(px, 0, 0.466), material=M_FRAME, bevel=0.003, name='platform_bracket')

kit.export('bicycle')
