"""Pendulum clock, after Christine Wu's drawing (RV P4a).

As drawn: a tall floor clock (about 1.7 m) with a round, drum-shaped head whose face is a spiral dial with a dark hub
and two hands (about 11:20), a body whose sides wave and sway like a slow S, a tall window in the front showing the
pendulum (wide flat rod, ribbed rating nut, round bob caught mid-swing), a cove where the body meets the base, and a
square plinth. The drawing is line-only: oak with real grain for the case, walnut plinth, cream dial, brass spiral,
pendulum and bezel. The head's depth matches the body (the drawing's top is loose there), and the back is invented:
a walnut access panel on the head and a plain back.
"""
import sys, os, math, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

TMP = tempfile.gettempdir()


# ---------------------------------------------------------------- helpers
def save_img(name, arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = arr[::-1]
    img.pixels = px.ravel(); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


def wood_texture(path, light, dark, size=512, seed=3, rings=26.0):
    """Tileable straight-grain wood: gently wandering growth lines along v, fine pores, soft colour drift."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size] / size
    warp = np.zeros_like(u)
    for k in range(7):
        fu, fv = rng.integers(0, 3), rng.integers(1, 4)
        warp += rng.uniform(0.002, 0.008) * np.sin(2 * np.pi * (fu * u + fv * v) + rng.uniform(0, 6.28))
    drift = 0.5 + 0.5 * np.sin(2 * np.pi * (u * 3 + 2 * warp) + 1.0)
    g = (u + warp) * rings
    line = (0.5 + 0.5 * np.sin(2 * np.pi * g)) ** 4
    fine = (0.5 + 0.5 * np.sin(2 * np.pi * (u + warp * 1.7) * rings * 3.3)) ** 2
    pores = np.repeat(rng.random((size, size // 4)), 4, axis=1)
    t = np.clip(0.42 * line + 0.12 * fine + 0.08 * pores + 0.3 * drift, 0, 1)
    lc = np.array(kit.hex_rgb(light)[:3]) ** (1 / 2.2); dc = np.array(kit.hex_rgb(dark)[:3]) ** (1 / 2.2)
    rgb = lc * (1 - t[..., None]) + dc * t[..., None]
    return save_img('wood', np.clip(rgb, 0, 1), path)


def planar_uv(obj, tile, offset=(0.0, 0.0)):
    me = obj.data
    uv = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name='UVMap')
    mw = obj.matrix_world
    for poly in me.polygons:
        n = mw.to_3x3() @ poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            v = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0: a, b = v.y, v.z
            elif ax == 1: a, b = v.x, v.z
            else: a, b = v.x, v.y
            uv.data[li].uv = (a / tile + offset[0], b / tile + offset[1])


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def mesh_obj(name, verts, faces, material=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    return o


def interp(table, z):
    for (z0, a0), (z1, a1) in zip(table, table[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0); t = t * t * (3 - 2 * t)
            return a0 + (a1 - a0) * t
    return table[0][1] if z < table[0][0] else table[-1][1]


# ---------------------------------------------------------------- materials
oak_tex = wood_texture(os.path.join(TMP, 'clock_oak.png'), '#a06a36', '#5c3818', seed=3)
wal_tex = wood_texture(os.path.join(TMP, 'clock_walnut.png'), '#5e3c24', '#2e1d12', seed=8, rings=30)
M_OAK = kit.mat('#ffffff', rough=0.55, image=oak_tex, name='oak')
M_WAL = kit.mat('#ffffff', rough=0.5, image=wal_tex, name='walnut')
M_BACKBOARD = kit.mat('#4a2f1c', rough=0.6, name='backboard')
M_DIAL = kit.mat('cream', rough=0.45, name='dial')
M_BRASS = kit.mat('brass', rough=0.28, metal=0.95, name='brass')
M_HUB = kit.mat('#1a1918', rough=0.3, metal=0.3, name='hub')
M_HAND = kit.mat('#141414', rough=0.35, metal=0.4, name='hand')

# ---------------------------------------------------------------- dimensions (metres)
PLATE = (0.53, 0.46, 0.036)
ZB = PLATE[2]                 # top of the plinth
D = 0.37                      # body depth
YF = -D / 2                   # body front face
ZH, RH = 1.43, 0.27           # head centre height, head radius
# the S-sway of the body: centre offset and half-width by height (from the drawing's two wavy edges)
CX = [(ZB, 0.0), (0.22, 0.008), (0.40, 0.016), (0.70, 0.018), (0.96, 0.012), (1.14, 0.005), (1.32, 0.0)]
HW = [(ZB, 0.232), (0.22, 0.212), (0.40, 0.182), (0.70, 0.224), (0.96, 0.196), (1.14, 0.18), (1.32, 0.166)]
YBK = [(ZB, 0.0), (0.30, 0.026), (0.58, -0.012), (0.90, 0.03), (1.15, 0.004), (1.32, 0.0)]   # wave of the back face


def body_xy(z):
    cx, hw = interp(CX, z), interp(HW, z)
    flare = 0.0
    zc = z - ZB
    if zc < 0.07:                                  # the cove into the plinth
        flare = 0.026 * (1 - math.sin(math.pi / 2 * zc / 0.07))
    return cx, hw + flare, flare


# ---------------------------------------------------------------- plinth
kit.box(PLATE, at=(0, 0, ZB / 2), material=M_WAL, bevel=0.006, segments=3, name='plinth')

# ---------------------------------------------------------------- body: a loft of rounded rectangles
NZ = 46
CORNER = 0.018
ring_n = 6
zs = [ZB - 0.002] + [ZB + (1.32 - ZB) * (i / (NZ - 1)) ** 1.15 for i in range(1, NZ)]
verts, faces = [], []
per = 0
for z in zs:
    cx, hw, fl = body_xy(z)
    yb = D / 2 + interp(YBK, z) + fl
    yf = YF - fl
    pts = []
    corners = [(cx + hw - CORNER, yb - CORNER, 0), (cx - hw + CORNER, yb - CORNER, 90), (cx - hw + CORNER, yf + CORNER, 180),
               (cx + hw - CORNER, yf + CORNER, 270)]
    for (ox, oy, a0) in corners:
        for k in range(ring_n + 1):
            a = math.radians(a0 + 90 * k / ring_n)
            pts.append((ox + CORNER * math.cos(a), oy + CORNER * math.sin(a), z))
    per = len(pts)
    verts += pts
for i in range(NZ - 1):
    for k in range(per):
        k2 = (k + 1) % per
        faces.append((i * per + k, i * per + k2, (i + 1) * per + k2, (i + 1) * per + k))
faces.append(tuple(range(per))[::-1])
faces.append(tuple(range((NZ - 1) * per, NZ * per)))
body = mesh_obj('body', verts, faces, M_OAK)

# the front window: arched top concentric with the head, wavy sides that follow the body, floor at ~0.22 m
STRIP = 0.05
ZW0 = 0.22
RW = RH + 0.036
win = []
zz = [ZW0 + (1.2 - ZW0) * i / 30 for i in range(31)]
left, right = [], []
for z in zz:
    cx, hw, _ = body_xy(z)
    left.append((cx - hw + STRIP, z)); right.append((cx + hw - STRIP, z))


def arch_z(x):
    return ZH - math.sqrt(max(RW * RW - x * x, 0))


# trim the sides where they meet the arch
L = [(x, z) for x, z in left if z <= arch_z(x)]
Rr = [(x, z) for x, z in right if z <= arch_z(x)]
arch = []
xa0, xa1 = L[-1][0], Rr[-1][0]
for i in range(1, 24):
    x = xa0 + (xa1 - xa0) * i / 24
    arch.append((x, arch_z(x)))
outline = L + arch + Rr[::-1]          # counter-clockwise seen from the front? (x right, z up): left up, arch, right down
WDEPTH = 0.17
cut_verts = [(x, YF - 0.05, z) for x, z in outline] + [(x, YF + WDEPTH, z) for x, z in outline]
m = len(outline)
cut_faces = [tuple(range(m)), tuple(range(m, 2 * m))[::-1]]
for k in range(m):
    k2 = (k + 1) % m
    cut_faces.append((k, k2, m + k2, m + k))
cutter = mesh_obj('win_cut', cut_verts, cut_faces)
kit.boolean(body, cutter)
planar_uv(body, 0.55)
kit.finish(body, None, bevel=0.004, segments=2, smooth=35)

# dark backboard at the back of the window
bb_out = [(x, z) for x, z in outline]
bverts = [(x * 0.999, YF + WDEPTH - 0.004, z) for x, z in bb_out] + [(x * 0.999, YF + WDEPTH - 0.001, z) for x, z in bb_out]
bfaces = [tuple(range(m)), tuple(range(m, 2 * m))[::-1]] + [((k), (k + 1) % m, m + (k + 1) % m, m + k) for k in range(m)]
mesh_obj('backboard', bverts, bfaces, M_BACKBOARD)

# ---------------------------------------------------------------- head: a drum the depth of the body
head = kit.cyl(RH, D + 0.012, at=(0, 0.006 - 0.006, ZH), rot=(90, 0, 0), material=M_OAK, verts=96, bevel=0.012, segments=3, name='head')
head.location.y = 0.0
apply_mods(head)
planar_uv(head, 0.55, offset=(0.3, 0.1))
kit.finish(head, None, smooth=35)
YD = -D / 2 - 0.006                      # front face of the head
# brass bezel ring and cream dial
bez = kit.torus(RH - 0.022, 0.014, at=(0, YD - 0.002, ZH), rot=(90, 0, 0), material=M_BRASS, major=96, minor=12, name='bezel')
dial = kit.cyl(RH - 0.03, 0.006, at=(0, YD - 0.001, ZH), rot=(90, 0, 0), material=M_DIAL, verts=96, bevel=0.002, name='dial')
# the spiral, three turns out from the hub (as drawn)
sp = []
turns = 3.0
for i in range(361):
    t = i / 360
    a = math.radians(100) - t * turns * 2 * math.pi
    r = 0.05 + (RH - 0.06 - 0.05) * t
    sp.append((r * math.cos(a), YD - 0.0045, ZH + r * math.sin(a)))
cu = bpy.data.curves.new('spiral', 'CURVE'); cu.dimensions = '3D'
s_ = cu.splines.new('POLY'); s_.points.add(len(sp) - 1)
for p, c in zip(s_.points, sp):
    p.co = (*c, 1)
cu.bevel_depth = 0.0042; cu.bevel_resolution = 2
so = bpy.data.objects.new('spiral', cu); bpy.context.collection.objects.link(so)
bpy.context.view_layer.objects.active = so; so.select_set(True); bpy.ops.object.convert(target='MESH')
so = bpy.context.object; so.data.materials.append(M_BRASS); kit.finish(so, None)
# hub and hands (about 11:20)
kit.sphere(0.034, at=(0, YD - 0.006, ZH), scale=(1, 0.55, 1), material=M_HUB, segs=32, rings=16, name='hub')


def hand(length, w0, w1, ang_deg, y, name):
    a = math.radians(ang_deg)
    poly = [(-w0, -0.025), (w0, -0.025), (w1, length - 0.012), (0, length), (-w1, length - 0.012)]
    o = kit.extrude(poly, 0.003, material=M_HAND, bevel=0.0008, name=name)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.rotation_mode = 'XYZ'
    # rotate within the dial plane: build as matrix
    mat_rot = Matrix.Rotation(a, 4, 'Y') @ Matrix.Rotation(math.radians(90), 4, 'X')
    o.matrix_world = Matrix.Translation((0, y, ZH)) @ mat_rot
    return o


hand(0.205, 0.006, 0.0035, 120, YD - 0.0115, 'minute_hand')     # long hand toward 4
hand(0.115, 0.008, 0.005, -20, YD - 0.0145, 'hour_hand')         # short hand just before 12
kit.cyl(0.008, 0.012, at=(0, YD - 0.024, ZH), rot=(90, 0, 0), material=M_BRASS, verts=24, bevel=0.002, name='hand_nut')

# back of the head: a walnut access panel with brass screws
kit.cyl(RH - 0.06, 0.008, at=(0, D / 2 + 0.009, ZH), rot=(90, 0, 0), material=M_WAL, verts=72, bevel=0.003, name='back_panel')
for k in range(6):
    a = 2 * math.pi * k / 6 + 0.3
    kit.cyl(0.006, 0.004, at=((RH - 0.08) * math.cos(a), D / 2 + 0.014, ZH + (RH - 0.08) * math.sin(a)), rot=(90, 0, 0),
            material=M_BRASS, verts=16, bevel=0.001, name='screw')

# ---------------------------------------------------------------- pendulum, caught mid-swing to the left
PIV = Vector((0, YF + 0.08, arch_z(0) - 0.012))
kit.box((0.09, 0.05, 0.03), at=(PIV.x, PIV.y + 0.02, PIV.z + 0.008), material=M_BRASS, bevel=0.004, name='suspension')
pend = []
SW = math.radians(6)          # swing angle in the plane of the front face
LROD = 0.47
rod_poly = [(-0.028, 0.0), (0.028, 0.0), (0.021, -LROD), (-0.021, -LROD)]
rod = kit.extrude(rod_poly, 0.008, material=M_BRASS, bevel=0.0015, name='rod')
pend.append(rod)
# ribbed rating nut (the hatching above the bob)
for k in range(9):
    pend.append(kit.cyl(0.026 if k % 2 == 0 else 0.022, 0.008, at=(0, 0.004, -LROD + 0.02 + k * 0.008), material=M_BRASS,
                        verts=24, bevel=0.0012, name='nut'))
# lens bob: a disc facing the front with a domed face
bob = kit.lathe([(0.0, -0.012), (0.066, -0.012), (0.07, -0.006), (0.07, 0.006), (0.066, 0.012), (0.045, 0.017), (0.0, 0.019)],
                material=M_BRASS, steps=64, name='bob')
bob.rotation_euler = (math.radians(90), 0, 0)    # dome toward -Y (front)
bob.location = (0, 0.004, -LROD - 0.052)
pend.append(bob)
piv = bpy.data.objects.new('pendulum', None); bpy.context.collection.objects.link(piv)
for o in pend:
    o.parent = piv
# extrude goes +z: rod polygon lies in local xy; stand it up in the xz plane facing the front
rod.rotation_euler = (math.radians(90), 0, 0)
rod.location = (0, 0.004, 0)
piv.location = PIV
piv.rotation_euler = (0, SW, 0)

kit.export('pendulum-clock')
