"""Car tire with a speaker in the hole, after Matt Turner's drawing (RV P5a).

As drawn: a wide, chunky tire (width about 0.55 of its diameter) standing on its tread, with a brick-pattern tread of
two staggered rows of blocks. On the face: the sidewall ring, a rim dish split into six segments by radial spokes, and
a speaker in the centre: frame ring, cone, and a big dust cap (the drawing's inner circle).
Invented: bronze rim, the speaker hardware, and the closed back with a bass port and binding posts.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
from mathutils import Vector, Matrix

RC = 0.322          # outer radius (top of the tread blocks)
ZC = RC             # axle height: the tire stands on its tread
HALF = 0.165        # half tread width

M_RUB = kit.mat('#21201f', rough=0.86, name='rubber')
M_RUB_T = kit.mat('#252423', rough=0.82, name='tread')
M_RIM = kit.mat('#c9a05a', rough=0.26, metal=0.95, name='bronze')
M_RIM_DK = kit.mat('#8a6236', rough=0.36, metal=0.9, name='bronze_dark')
M_CHROME = kit.mat('chrome', rough=0.22, metal=1.0, name='chrome')
M_CONE = kit.mat('#2a2826', rough=0.72, name='cone')
M_SURR = kit.mat('#1e1d1c', rough=0.8, name='surround')
M_CAP = kit.mat('gunmetal', rough=0.35, metal=0.85, name='dustcap')
M_FRAME = kit.mat('#2e3034', rough=0.4, metal=0.7, name='frame')
M_RED = kit.mat('red', rough=0.4, name='post_red')
M_BLK = kit.mat('black', rough=0.4, name='post_black')


def place_axis(o):
    """Lathes are built around Z with +z = the tire's front; turn them to face -Y at axle height."""
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (0, 0, ZC)
    return o


def P(r, th, a):
    """Tire-local polar coords -> world. a > 0 is toward the front (-Y)."""
    return Vector((r * math.cos(th), -a, ZC + r * math.sin(th)))


def polar_block(th0, th1, a0, a1, r0, r1, nseg, material, bevel=0.003, name='block'):
    verts, faces = [], []
    for i in range(nseg + 1):
        th = th0 + (th1 - th0) * i / nseg
        verts += [P(r0, th, a0), P(r1, th, a0), P(r1, th, a1), P(r0, th, a1)]
    for i in range(nseg):
        b, c = 4 * i, 4 * (i + 1)
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((b + k, b + k2, c + k2, c + k))
    faces.append((0, 1, 2, 3)); n = 4 * nseg; faces.append((n + 3, n + 2, n + 1, n))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, bevel=bevel, segments=2)


# ---------------------------------------------------------------- tire carcass (lathe, closed)
R_TB = 0.306        # tread base radius
SH = 0.022          # shoulder radius: the face reads as a clean round tire, as drawn
R_BEAD = 0.234
side = []           # front: crown -> shoulder -> sidewall -> bead, as (r, a)
side.append((R_TB, 0.0))
side.append((R_TB, HALF - SH))
for i in range(1, 7):
    t = i / 6 * math.pi / 2
    side.append((R_TB - SH + SH * math.cos(t), HALF - SH + SH * math.sin(t)))
r_sw = R_TB - SH
for i in range(1, 11):
    t = i / 10
    r = r_sw - (r_sw - R_BEAD) * t
    a = HALF + 0.004 * math.sin(math.pi * t) - 0.022 * t ** 1.5
    side.append((r, a))
prof = [(r, -a) for r, a in reversed(side[1:])] + side
prof.append((R_BEAD - 0.004, side[-1][1]))
prof.append((R_BEAD - 0.004, -side[-1][1]))
tire = kit.lathe(prof, material=M_RUB, steps=96, name='tire')
place_axis(tire)


def side_a(r):
    pts = [p for p in side if p[0] <= r_sw + 1e-6]
    best = min(range(len(pts) - 1), key=lambda i: abs((pts[i][0] + pts[i + 1][0]) / 2 - r))
    (r0, a0), (r1, a1) = pts[best], pts[best + 1]
    return a0 + (a1 - a0) * (r - r0) / (r1 - r0)


# sidewall ridges: two fine rings on each side
for sgn in (1, -1):
    for r, rr in ((0.262, 0.0022), (0.274, 0.0012)):
        to = kit.torus(r, rr, material=M_RUB, major=72, minor=6, name='ridge')
        place_axis(to)
        to.location.y = -sgn * (side_a(r) + rr * 0.2)

# ---------------------------------------------------------------- tread: two staggered rows of blocks (the drawing's brick pattern)
N = 24
pitch = 2 * math.pi / N
groove = 0.016 / RC
A_OUT = HALF - 0.012
for row, (a0, a1) in enumerate(((0.008, A_OUT), (-A_OUT, -0.008))):
    off = 0 if row == 0 else pitch / 2
    for k in range(N):
        th0 = k * pitch + off + groove / 2
        th1 = th0 + pitch - groove
        polar_block(th0, th1, a0, a1, R_TB - 0.004, RC, 4, M_RUB_T, bevel=0.004, name='block')
        # a short sipe on every other block, like the little rectangles in the drawing
        if k % 2 == 0:
            mid = (th0 + th1) / 2
            s0, s1 = (a0 + 0.035, a0 + 0.075) if row == 0 else (a1 - 0.075, a1 - 0.035)
            polar_block(mid - 0.010, mid + 0.010, s0, s1, RC - 0.003, RC + 0.0006, 2, M_RUB, bevel=0.0, name='sipe')

# ---------------------------------------------------------------- rim: dark dish split into six segments by bright spokes, bright lip
A_RIM = 0.134
DISH = [(0.168, A_RIM + 0.002), (0.18, A_RIM + 0.004), (0.21, A_RIM + 0.009), (0.242, A_RIM + 0.016)]


def dish_a(r):
    for (r0, a0), (r1, a1) in zip(DISH, DISH[1:]):
        if r0 <= r <= r1:
            return a0 + (a1 - a0) * (r - r0) / (r1 - r0)
    return DISH[-1][1]


dish_prof = [(0.168, A_RIM - 0.014)] + DISH + [(0.242, A_RIM - 0.004), (0.20, A_RIM - 0.010), (0.168, A_RIM - 0.014)]
lip_prof = [(0.236, A_RIM + 0.012), (0.240, A_RIM + 0.022), (0.246, A_RIM + 0.028), (0.252, A_RIM + 0.027),
            (0.257, A_RIM + 0.020), (0.257, A_RIM + 0.006), (0.236, A_RIM + 0.000), (0.236, A_RIM + 0.012)]
for sgn in (1, -1):
    for pr0, m, nm in ((dish_prof, M_RIM_DK, 'rim_dish'), (lip_prof, M_RIM, 'rim_lip')):
        o = kit.lathe([(r, sgn * a) for r, a in pr0], material=m, steps=96, name=nm)
        place_axis(o)
    for k in range(6):
        th = math.radians(90 + 60 * k)
        mid_r = 0.207
        slope = math.atan2(0.012, 0.062)
        sp = kit.box((0.07, 0.02, 0.009), material=M_RIM, bevel=0.003, segments=2, name='spoke')
        radial = Vector((math.cos(th), 0, math.sin(th)))
        axial = Vector((0, -sgn, 0))           # out of the dish, toward the viewer on that side
        rt = (radial * math.cos(slope) + axial * math.sin(slope)).normalized()
        nrm = (axial - rt * axial.dot(rt)).normalized()
        tg = nrm.cross(rt)
        sp.rotation_mode = 'QUATERNION'
        sp.rotation_quaternion = Matrix((rt, tg, nrm)).transposed().to_quaternion()
        sp.location = P(mid_r, th, sgn * (dish_a(mid_r) + 0.0025))

# ---------------------------------------------------------------- speaker (front)
A_SP = A_RIM - 0.006
frame = kit.lathe([(0.150, A_SP - 0.006), (0.170, A_SP - 0.006), (0.172, A_SP + 0.004), (0.166, A_SP + 0.008),
                   (0.152, A_SP + 0.008), (0.150, A_SP - 0.006)], material=M_FRAME, steps=96, name='frame')
place_axis(frame)
for k in range(6):
    th = math.radians(90 + 60 * k)
    sc = kit.cyl(0.0055, 0.004, verts=16, material=M_CHROME, bevel=0.0012, name='screw')
    sc.rotation_euler = (math.radians(90), 0, 0)
    sc.location = P(0.161, th, A_SP + 0.009)
surround = kit.torus(0.1415, 0.0095, material=M_SURR, major=96, minor=12, name='surround')
place_axis(surround); surround.location.y = -(A_SP + 0.0005)
cone = []
for i in range(17):
    t = i / 16
    r = 0.134 - (0.134 - 0.074) * t
    a = A_SP - 0.002 - 0.048 * (t ** 0.85) + 0.0012 * math.sin(t * math.pi * 7)
    cone.append((r, a))
cone_back = [(r - 0.0, a - 0.003) for r, a in reversed(cone)]
cone_m = kit.lathe(cone + cone_back + [cone[0]], material=M_CONE, steps=72, name='cone')
place_axis(cone_m)
a_cap = cone[-1][1]
dome = [(0.077 * math.cos(i / 12 * math.pi / 2), a_cap - 0.001 + 0.03 * math.sin(i / 12 * math.pi / 2)) for i in range(13)]
capo = kit.lathe([(0.0, a_cap - 0.004), (0.077, a_cap - 0.004)] + dome, material=M_CAP, steps=64, name='dustcap')
place_axis(capo)
# a back plate deep inside so the cone never looks into the void
bp = kit.cyl(0.165, 0.004, material=M_FRAME, verts=64, name='inner_plate')
place_axis(bp); bp.location.y = -(a_cap - 0.01)

# ---------------------------------------------------------------- the back: closed plate with a bass port and binding posts
A_B = -(A_RIM - 0.006)
plate = kit.lathe([(0.0, A_B - 0.004), (0.168, A_B - 0.004), (0.171, A_B + 0.002), (0.0, A_B + 0.002)],
                  material=M_FRAME, steps=96, name='back_plate')
place_axis(plate)
# bass port: flared tube
port = kit.lathe([(0.034, A_B - 0.012), (0.046, A_B - 0.008), (0.040, A_B - 0.004), (0.034, A_B + 0.08),
                  (0.030, A_B + 0.08), (0.030, A_B - 0.012), (0.034, A_B - 0.012)], material=M_SURR, steps=48, name='port')
port.rotation_euler = (math.radians(90), 0, 0)
port.location = (-0.06, 0, ZC + 0.04)
hole = kit.cyl(0.031, 0.05, rot=(90, 0, 0), at=(-0.06, -A_B, ZC + 0.04), verts=48)
kit.boolean(plate, hole)
# terminal cup with two posts
kit.box((0.07, 0.008, 0.045), at=(0.07, -A_B + 0.006, ZC - 0.06), material=M_BLK, bevel=0.004, name='terminal')
for x, m in ((0.055, M_RED), (0.085, M_BLK)):
    kit.cyl(0.0075, 0.016, at=(x, -A_B + 0.016, ZC - 0.06), rot=(90, 0, 0), material=m, verts=24, bevel=0.002, name='post')
    kit.cyl(0.003, 0.01, at=(x, -A_B + 0.026, ZC - 0.06), rot=(90, 0, 0), material=M_CHROME, verts=12, name='post_tip')
# bolts around the back plate
for k in range(8):
    th = math.radians(22.5 + 45 * k)
    b = kit.cyl(0.006, 0.006, verts=6, material=M_CHROME, bevel=0.001, name='bolt')
    b.rotation_euler = (math.radians(90), 0, 0)
    b.location = P(0.158, th, A_B - 0.007)

kit.export('car-tire')
