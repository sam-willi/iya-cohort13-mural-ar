"""Vacuum cleaner, after Nina Zhang's drawing (RV P5a).

As drawn: a canister vacuum with a rounded-box body, a lid with a lip and a raised oval panel, a tall squared carry
handle across the top, two oval "eyes" on the front with dark pupils looking up, a knurled hose collar below them like a
nose, and a corrugated hose that runs out along the floor and up into a big loop.
Line-only drawing, so the colours are a retro appliance in the mural palette: red body, cream lid and handle.
Invented: the hose's far end (cuff and a floor tool resting on the ground), casters and bumper, the back vent and cord hook.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
from mathutils import Vector, Matrix


# ---------------------------------------------------------------- helpers
def _catmull(points, subdiv, closed=False):
    P = [Vector(p) for p in points]
    if len(P) < 3 or subdiv <= 1:
        return P
    out = []
    n = len(P)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if closed else P[max(i - 1, 0)]
        p1 = P[i]; p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed else P[min(i + 2, n - 1)]
        for k in range(subdiv):
            t = k / subdiv; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def resample(P, step):
    """Even spacing along a polyline."""
    out = [P[0]]; acc = 0.0
    for a, b in zip(P, P[1:]):
        seg = (b - a).length; d = 0.0
        while acc + seg - d >= step:
            d += step - acc; acc = 0.0
            out.append(a + (b - a) * (d / seg))
        acc += seg - d
    if (out[-1] - P[-1]).length > step * 0.3:
        out.append(P[-1])
    return out


def tube(points, r, material=None, sides=10, subdiv=4, step=None, closed=False, caps=True, name='tube'):
    """Swept circle along a Catmull-Rom path (parallel-transport frames). r: float or callable(t, i)."""
    P = _catmull(points, subdiv, closed)
    if step:
        P = resample(P, step)
    n = len(P)
    rad = (lambda t, i: r) if not callable(r) else r
    T = []
    for i in range(n):
        t = (P[(i + 1) % n] - P[i - 1]) if closed else (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        T.append(t.normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    verts, faces = [], []
    for i in range(n):
        if i:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-8:
                N = Matrix.Rotation(T[i - 1].angle(T[i]), 3, b.normalized()) @ N
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        rr = rad(i / max(n - 1, 1), i)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(P[i] + (N * math.cos(a) + B * math.sin(a)) * rr)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, j * sides + k2, j * sides + k))
    if caps and not closed:
        c0 = len(verts); verts.append(P[0]); c1 = len(verts); verts.append(P[-1])
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k)); faces.append((c1, (n - 1) * sides + k, (n - 1) * sides + k2))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, smooth=50), P


def rrect(w, d, r, n=8):
    """Rounded rectangle polygon, counter-clockwise, centred."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -d / 2 + r, -90), (w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ellipse(a, b, n=48):
    return [(a * math.cos(2 * math.pi * k / n), b * math.sin(2 * math.pi * k / n)) for k in range(n)]


def on_front(o, x, z, y):
    """Stand a flat (xy, +z thickness) piece up on the front face: local +z -> -Y."""
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (x, y, z)
    return o


# ---------------------------------------------------------------- materials
M_BODY = kit.mat('#a92a22', rough=0.36, name='body_red')
M_LID = kit.mat('cream', rough=0.42, name='lid_cream')
M_LID_DK = kit.mat('#d9cbb0', rough=0.45, name='lid_panel')
M_RUBBER = kit.mat('rubber', rough=0.85, name='rubber')
M_DARK = kit.mat('#232325', rough=0.45, name='dark_plastic')
M_PUPIL = kit.mat('#141416', rough=0.12, name='pupil')
M_HOSE = kit.mat('#5a5d62', rough=0.55, name='hose')
M_CHROME = kit.mat('chrome', rough=0.22, metal=1.0, name='chrome')
M_GREY = kit.mat('#8a8d92', rough=0.45, name='grey_plastic')
M_GLINT = kit.mat('#ffffff', rough=0.2, emit=0.6, name='glint')

# ---------------------------------------------------------------- dimensions
W, DP = 0.36, 0.46           # footprint (eye face is the narrow end, as drawn)
RC = 0.085                   # footprint corner radius
Z0, ZL = 0.035, 0.395        # body from bumper to lid
ZT = 0.455                   # top of the lid
YF = -DP / 2

# ---------------------------------------------------------------- body, bumper, casters
body = kit.extrude(rrect(W, DP, RC), ZL - Z0, at=(0, 0, Z0), material=M_BODY, bevel=0.022, segments=4, name='body')
kit.extrude(rrect(W + 0.014, DP + 0.014, RC + 0.007), 0.03, at=(0, 0, 0.022), material=M_RUBBER, bevel=0.008, segments=3, name='bumper')
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * (W / 2 - 0.07), sy * (DP / 2 - 0.08)
        kit.cyl(0.024, 0.012, at=(x, y, 0.028), material=M_DARK, verts=24, bevel=0.003, name='caster_mount')
        kit.cyl(0.018, 0.016, at=(x, y + 0.008, 0.018), rot=(0, 90, 0), material=M_RUBBER, verts=24, bevel=0.003, name='caster')

# ---------------------------------------------------------------- lid: lip, rounded dome, raised oval panel
kit.extrude(rrect(W + 0.016, DP + 0.016, RC + 0.008), 0.016, at=(0, 0, ZL - 0.004), material=M_LID, bevel=0.005, segments=2, name='lid_lip')
kit.extrude(rrect(W + 0.004, DP + 0.004, RC + 0.002), ZT - ZL - 0.012, at=(0, 0, ZL + 0.008), material=M_LID, bevel=0.034,
            segments=5, name='lid')
panel = kit.extrude(ellipse(0.135, 0.175, 64), 0.014, at=(0, 0.0, ZT - 0.008), material=M_LID_DK, bevel=0.006, segments=3, name='lid_panel')
# latches on the two long sides where lid meets body
for sx in (-1, 1):
    kit.box((0.016, 0.07, 0.05), at=(sx * (W / 2 + 0.008), 0.0, ZL - 0.01), material=M_DARK, bevel=0.006, segments=2, name='latch')

# ---------------------------------------------------------------- carry handle: tall, squared, across the width (as drawn)
ZP = ZT + 0.006
HH = 0.215                   # handle height above the panel
HX = 0.12                    # legs at +-HX
SQ = 0.036                   # section
for sx in (-1, 1):
    kit.box((SQ, SQ * 1.15, HH), at=(sx * HX, 0, ZP + HH / 2 - 0.004), material=M_LID, bevel=0.012, segments=4, name='handle_leg')
    kit.extrude(ellipse(0.03, 0.034, 32), 0.012, at=(sx * HX, 0, ZP - 0.006), material=M_LID_DK, bevel=0.004, name='handle_boss')
kit.box((2 * HX + SQ, SQ * 1.15, SQ), at=(0, 0, ZP + HH - SQ / 2), material=M_LID, bevel=0.012, segments=4, name='handle_bar')
# rubber grip pad under the bar
kit.box((2 * HX - SQ - 0.02, SQ * 0.95, 0.008), at=(0, 0, ZP + HH - SQ - 0.002), material=M_RUBBER, bevel=0.003, name='grip')

# ---------------------------------------------------------------- the face: two tall oval eyes looking up, the hose collar as a nose
EZ = 0.30
for sx in (-1, 1):
    ex = sx * 0.062
    bez = kit.extrude(ellipse(0.03, 0.056, 48), 0.010, material=M_LID, bevel=0.004, segments=2, name='eye_bezel')
    on_front(bez, ex, EZ, YF + 0.004)
    sock = kit.extrude(ellipse(0.0225, 0.047, 48), 0.004, material=M_DARK, bevel=0.0015, name='eye_socket')
    on_front(sock, ex, EZ, YF - 0.0055)
    pup = kit.extrude(ellipse(0.0185, 0.039, 40), 0.006, material=M_PUPIL, bevel=0.003, segments=3, name='pupil')
    on_front(pup, ex + sx * 0.001, EZ + 0.006, YF - 0.0085)
    kit.sphere(0.0045, at=(ex + sx * 0.002 - 0.006, YF - 0.0145, EZ + 0.032), scale=(1, 0.5, 1.2), material=M_GLINT,
               segs=12, rings=8, name='glint')
# hose collar: knurled ring on a socket
NZ_ = 0.19
sock = kit.cyl(0.046, 0.02, at=(0, YF - 0.004, NZ_), rot=(90, 0, 0), material=M_DARK, verts=48, bevel=0.005, name='inlet')
col = kit.cyl(0.042, 0.05, at=(0, YF - 0.036, NZ_), rot=(90, 0, 0), material=M_DARK, verts=48, bevel=0.004, name='collar')
for k in range(36):
    a = 2 * math.pi * k / 36
    kit.box((0.0045, 0.042, 0.006), at=(0.0425 * math.cos(a), YF - 0.034, NZ_ + 0.0425 * math.sin(a)),
            rot=(0, 90 - math.degrees(a), 0), material=M_DARK, bevel=0.0012, name='knurl')
kit.cyl(0.036, 0.02, at=(0, YF - 0.069, NZ_), rot=(90, 0, 0), material=M_CHROME, verts=48, bevel=0.003, name='ferrule')

# ---------------------------------------------------------------- corrugated hose: out along the floor, then up into the big loop
HR = 0.028
start = Vector((0, YF - 0.075, NZ_))
path = [start, (0.0, YF - 0.13, NZ_ - 0.015), (-0.03, YF - 0.22, 0.10), (-0.12, YF - 0.27, HR + 0.004),
        (-0.30, YF - 0.25, HR + 0.004), (-0.47, YF - 0.12, 0.09), (-0.55, YF + 0.06, 0.34), (-0.53, 0.0, 0.62),
        (-0.47, 0.20, 0.70), (-0.40, 0.36, 0.55), (-0.38, 0.44, 0.30), (-0.40, 0.47, 0.10)]
hose, HP = tube(path, lambda t, i: HR + (0.0032 if (i // 2) % 2 == 0 else -0.0006), material=M_HOSE, sides=14, subdiv=8,
                step=0.0062, name='hose')
end = HP[-1]; tang = (HP[-1] - HP[-6]).normalized()
# cuff and a small floor tool resting on the ground at the far end
cuff_c = end + tang * 0.03
cuff = kit.cyl(HR + 0.007, 0.07, material=M_GREY, verts=32, bevel=0.004, name='cuff')
cuff.rotation_mode = 'QUATERNION'; cuff.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(tang); cuff.location = cuff_c
tool_top = end + tang * 0.065
neck = kit.cyl(HR - 0.004, 0.05, material=M_GREY, verts=32, bevel=0.003, name='tool_neck')
neck.rotation_mode = 'QUATERNION'; neck.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(tang)
neck.location = end + tang * 0.085
kit.extrude(rrect(0.2, 0.07, 0.03), 0.03, at=(tool_top.x, tool_top.y, 0.004), rot=(0, 0, 15), material=M_DARK,
            bevel=0.01, segments=3, name='floor_tool')
kit.box((0.17, 0.008, 0.006), at=(tool_top.x, tool_top.y, 0.003), rot=(0, 0, 15), material=M_RUBBER, bevel=0.002, name='tool_brush')

# ---------------------------------------------------------------- back: exhaust grille and cord hook with a coiled cord
YB = DP / 2
for k in range(7):
    s = kit.box((0.11, 0.02, 0.007), at=(-0.07, YB + 0.002, 0.15 + k * 0.022), material=M_DARK, bevel=0.0025, name='vent')
kit.extrude(rrect(0.14, 0.18, 0.02), 0.006, rot=(-90, 0, 0), at=(-0.07, YB - 0.001, 0.216), material=M_DARK, bevel=0.002, name='vent_plate')
# cord wound between two hooks on the back-right corner, plug tucked in
CXH = 0.085
kit.box((0.05, 0.03, 0.018), at=(CXH, YB + 0.012, 0.335), material=M_DARK, bevel=0.006, segments=2, name='cord_hook')
kit.box((0.05, 0.03, 0.018), at=(CXH, YB + 0.012, 0.105), material=M_DARK, bevel=0.006, segments=2, name='cord_hook')
for k in range(5):
    pts = []
    hw = 0.022 + 0.0006 * k
    for i in range(24):
        a = 2 * math.pi * i / 24
        z = 0.22 + (0.115 + 0.002 * k) * (1 if math.sin(a) > 0 else -1) * min(1, abs(math.sin(a)) * 3) ** 0.6
        pts.append((CXH + hw * math.cos(a) * 0.9 + (k - 2) * 0.0065, YB + 0.03 + 0.0045 * (k % 2), z))
    tube(pts, 0.0048, material=M_DARK, sides=8, subdiv=2, closed=True, caps=False, name='cord_loop')
kit.box((0.026, 0.02, 0.04), at=(CXH + 0.03, YB + 0.03, 0.06), material=M_DARK, bevel=0.005, name='plug')
for dx in (-0.006, 0.006):
    kit.box((0.003, 0.006, 0.018), at=(CXH + 0.03 + dx, YB + 0.03, 0.033), material=M_CHROME, name='prong')
# on/off button on the lid's back edge
kit.cyl(0.022, 0.012, at=(0.0, 0.16, ZT - 0.006), material=M_BODY, verts=32, bevel=0.004, name='switch')

kit.export('vacuum')
