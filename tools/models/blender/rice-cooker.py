"""Rice cooker - Gabrielle Tiu.

Her drawing: a soft, squarish body on little round feet with a base band; a raised control panel that wraps around
the front of the pot opening, carrying a "C13" display between two round buttons; a full pot of rice; the lid
hinged at the back and standing open, with a big round inner lid and gasket; and steam rising out of the pot as
puffy bubble letters, D-I-S-R-U-P-T, climbing up and to the right past the lid.
Line-only, so: cream body, dark glossy panel, pale LCD, steel inner lid, dark non-stick pot.
Invented: back (cord socket, condensation cup), side grip recesses, lid steam vent.
The little "S" marks on her rice grains are left off (they would be sub-pixel on a phone).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, random, bpy, bmesh

kit.reset()
random.seed(13)

W, D, H = 0.27, 0.30, 0.2
RB = 0.075                      # body corner radius (plan)
PC = (0.0, 0.03)                # pot centre (x, y)
PR = 0.1                        # pot opening radius
FONT = bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf')

body_m = kit.mat('cream', rough=0.38, name='body')
base_m = kit.mat('#b9ab92', rough=0.5, name='base')
panel_m = kit.mat('#2b2e33', rough=0.22, name='panel')
lcd_m = kit.mat('#c9dccf', rough=0.3, name='lcd')
ink_m = kit.mat('#1e2422', rough=0.4, name='ink')
orange_m = kit.mat('orange', rough=0.35, name='btn')
teal_m = kit.mat('teal', rough=0.35, name='btn2')
steel_m = kit.mat('chrome', rough=0.3, metal=0.85, name='steel')
pot_m = kit.mat('#2c2b2a', rough=0.45, name='nonstick')
gasket_m = kit.mat('white', rough=0.7, name='gasket')
rice_m = kit.mat('#fbf6ea', rough=0.75, name='rice')
steam_m = kit.mat('#fffdf8', rough=0.9, name='steam')
rubber_m = kit.mat('rubber', rough=0.85, name='rubber')


def rrect(w, h, r, n=8, cx=0.0, cy=0.0):
    pts = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def sel(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o


def bake(o):
    sel(o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def edge_bevel(o, w, seg=2, angle=60):
    sel(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30), keep_sharp_edges=True)
    md = o.modifiers.new('bevel2', 'BEVEL'); md.width = w; md.segments = seg
    md.limit_method = 'ANGLE'; md.angle_limit = math.radians(angle)
    return o


def letters(s, size, depth, bevel, at, rot, material, res=3):
    """Rounded 3D lettering in Arial Rounded; rot in degrees. Stands facing -Y with rot=(90,0,0)."""
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.font = FONT; cu.size = size
    cu.extrude = depth / 2; cu.bevel_depth = bevel; cu.bevel_resolution = res; cu.resolution_u = 3
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    o = bpy.data.objects.new('txt_' + s, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    sel(o); bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
    return o


def wisp(points, radii, material, name='wisp'):
    """Tapered smooth tube through points (radius per point)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('NURBS'); sp.points.add(len(points) - 1)
    for p, c, r in zip(sp.points, points, radii):
        p.co = (*c, 1); p.radius = r
    sp.use_endpoint_u = True; sp.order_u = 4
    cu.bevel_depth = 1.0; cu.bevel_resolution = 3; cu.resolution_u = 8; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    sel(o); bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    return kit.finish(o, material)


# ---------------------------------------------------------------- body
Z0 = 0.008                                 # body sits on feet
base = kit.extrude(rrect(W - 0.012, D - 0.012, RB - 0.006), 0.03, at=(0, 0, Z0), material=base_m, bevel=0.008,
                   segments=3, name='base')
body = kit.extrude(rrect(W, D, RB), H - 0.03, at=(0, 0, 0.03), material=body_m, bevel=0.012, segments=4,
                   name='body')
bake(body)
hole = kit.cyl(PR + 0.003, 0.2, at=(PC[0], PC[1], H), verts=64)
kit.boolean(body, hole)
for side in (-1, 1):  # finger recesses on the sides
    g = kit.box((0.03, 0.11, 0.02), at=(side * W / 2, 0.0, H - 0.05), material=None, bevel=0.0)
    kit.finish(g, None, bevel=0.009, segments=3); bake(g)
    kit.boolean(body, g)
sock = kit.box((0.034, 0.02, 0.024), at=(-0.06, D / 2, 0.08))
kit.boolean(body, sock)
edge_bevel(body, 0.002)
kit.box((0.032, 0.004, 0.022), at=(-0.06, D / 2 - 0.007, 0.08), material=kit.mat('black', rough=0.5))
for px in (-0.006, 0.006):
    kit.cyl(0.0018, 0.008, at=(-0.06 + px, D / 2 - 0.006, 0.08), rot=(90, 0, 0), material=steel_m, verts=10)
# condensation cup on the back
cup = kit.extrude(rrect(0.05, 0.026, 0.011), 0.045, at=(0.065, D / 2 + 0.008, H - 0.075), material=kit.mat(
    '#bcd9e6', rough=0.15, name='cup'), bevel=0.004, segments=2, name='cup')
kit.box((0.04, 0.012, 0.03), at=(0.065, D / 2 - 0.002, H - 0.055), material=body_m, bevel=0.003)

# feet
for fx in (-0.085, 0.085):
    for fy in (-0.095, 0.095):
        kit.cyl(0.014, Z0 + 0.004, at=(fx, fy, (Z0 + 0.004) / 2), material=rubber_m, bevel=0.003, verts=24)

# ---------------------------------------------------------------- control panel (crescent around the pot, sloped)
PZ = H - 0.004
panel = kit.extrude(rrect(W - 0.016, D - 0.016, RB - 0.008), 0.04, at=(0, 0, PZ), material=panel_m, name='panel')
c = kit.cyl(PR + 0.012, 0.2, at=(PC[0], PC[1], H), verts=64); kit.boolean(panel, c)
c = kit.box((0.4, 0.3, 0.2), at=(0, -0.022 + 0.15, H)); kit.boolean(panel, c)
SLOPE = math.radians(9)
c = kit.box((0.5, 0.5, 0.2), at=(0, 0, 0)); c.rotation_euler = (SLOPE, 0, 0)
# place the cutter so its bottom face is the plane through (y=-D/2, z=H+0.01) rising toward the back
n = (0, -math.sin(SLOPE), math.cos(SLOPE))
p0 = (0, -D / 2 + 0.008, H + 0.011)
c.location = (0, p0[1] + n[1] * 0.1, p0[2] + n[2] * 0.1)
kit.boolean(panel, c)
c = kit.box((0.5, 0.5, 0.2), at=(0, 0, H + 0.023 + 0.1)); kit.boolean(panel, c)   # keep the horns low
kit.finish(panel, None, bevel=0.007, segments=3)


def on_slope(y_front_dist, x, lift=0.0):
    """World point on the sloped panel face, y_front_dist metres up the slope from the front edge."""
    y = -D / 2 + 0.008 + y_front_dist * math.cos(SLOPE)
    z = H + 0.011 + y_front_dist * math.sin(SLOPE)
    return (x, y + n[1] * lift, z + n[2] * lift)


TILT = (math.degrees(SLOPE), 0, 0)
# display: frame, LCD, C13
fx, fd = -0.03, 0.034
frame = kit.extrude(rrect(0.092, 0.042, 0.008), 0.003, material=kit.mat('#3d4148', rough=0.3), bevel=0.0012,
                    segments=2, name='lcd_frame')
frame.location = on_slope(fd, fx, -0.0005); frame.rotation_euler = [math.radians(a) for a in TILT]
lcd = kit.extrude(rrect(0.08, 0.031, 0.005), 0.0008, material=lcd_m, name='lcd')
lcd.location = on_slope(fd, fx, 0.0024); lcd.rotation_euler = [math.radians(a) for a in TILT]
txt = letters('C13', 0.028, 0.0012, 0.0, on_slope(fd, fx, 0.0035), TILT, ink_m, res=0)
# buttons
for bx, m in ((-0.103, teal_m), (0.045, orange_m)):
    r = kit.cyl(0.0125, 0.003, material=kit.mat('#3d4148', rough=0.3), bevel=0.001, verts=32)
    r.location = on_slope(fd, bx, 0.0005); r.rotation_euler = [math.radians(a) for a in TILT]
    b = kit.cyl(0.0098, 0.007, material=m, bevel=0.0025, segments=3, verts=32)
    b.location = on_slope(fd, bx, 0.003); b.rotation_euler = [math.radians(a) for a in TILT]

# ---------------------------------------------------------------- pot and rice
PT = H + 0.002
pot = kit.lathe([(0.0, PT - 0.13), (PR - 0.006, PT - 0.13), (PR - 0.001, PT - 0.124), (PR - 0.001, PT - 0.004),
                 (PR - 0.005, PT - 0.003), (PR - 0.005, PT - 0.12), (0.0, PT - 0.125)], at=(PC[0], PC[1], 0),
                material=pot_m, steps=64, name='pot')
kit.torus(PR + 0.003, 0.0045, at=(PC[0], PC[1], PT), material=steel_m, major=64, minor=10, name='pot_rim')
RZ = PT - 0.03
mound = lambda r: RZ + 0.012 * (1 - (r / (PR - 0.005)) ** 2)
kit.lathe([(0.0, mound(0) - 0.003)] + [(r, mound(r) - 0.003) for r in (0.03, 0.06, 0.085, PR - 0.0045)] +
          [(PR - 0.0045, RZ - 0.02), (0.0, RZ - 0.02)], at=(PC[0], PC[1], 0), material=rice_m, steps=48, name='rice')
# grains: one mesh of small ellipsoids lying on the mound
me = bpy.data.meshes.new('grains'); bm = bmesh.new()
golden = math.pi * (3 - math.sqrt(5))
N = 230
for i in range(N):
    rr = (PR - 0.011) * math.sqrt((i + 0.5) / N)
    a = i * golden
    x, y = PC[0] + rr * math.cos(a), PC[1] + rr * math.sin(a)
    g = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=1.0)
    vs = g['verts']
    yaw = random.uniform(0, math.pi); pitch = random.uniform(-0.35, 0.35)
    sx, sy, sz = 0.0048, 0.0021, 0.0019
    for v in vs:
        px, py, pz = v.co.x * sx, v.co.y * sy, v.co.z * sz
        py, pz = py * math.cos(pitch) - pz * math.sin(pitch), py * math.sin(pitch) + pz * math.cos(pitch)
        px, py = px * math.cos(yaw) - py * math.sin(yaw), px * math.sin(yaw) + py * math.cos(yaw)
        v.co = (x + px, y + py, mound(rr) + 0.0002 + pz)
bm.to_mesh(me); bm.free()
grains = bpy.data.objects.new('grains', me); bpy.context.collection.objects.link(grains)
kit.finish(grains, rice_m)

# ---------------------------------------------------------------- lid (hinged at the back, open ~100 deg)
HY, HZ = 0.13, H + 0.016
LL, LT = 0.255, 0.042
hinge = bpy.data.objects.new('lid_hinge', None); bpy.context.collection.objects.link(hinge)
hinge.location = (0, HY, HZ)


def lid_part(o):
    o.parent = hinge
    return o


shell = kit.extrude(rrect(W - 0.014, LL, RB - 0.008), LT, material=body_m, bevel=0.016, segments=4, name='lid')
shell.location = (0, -LL / 2 + 0.012, 0.0); lid_part(shell)
# inner side (faces forward when open): steel inner lid, silicone gasket, valve cap
ic = (0, -LL / 2 + 0.012 - 0.01)
inner = kit.cyl(0.098, 0.006, at=(ic[0], ic[1], -0.001), material=steel_m, bevel=0.002, verts=64, name='inner_lid')
lid_part(inner)
lid_part(kit.torus(0.1, 0.0045, at=(ic[0], ic[1], -0.003), material=gasket_m, major=64, minor=10, name='gasket'))
lid_part(kit.cyl(0.08, 0.0012, at=(ic[0], ic[1], -0.0045), material=kit.mat('#a8adb4', rough=0.4, metal=0.8),
                 verts=64, name='inner_disc'))
lid_part(kit.cyl(0.016, 0.006, at=(ic[0], ic[1], -0.006), material=steel_m, bevel=0.002, verts=32, name='valve'))
for k in range(4):
    a = math.radians(45 + 90 * k)
    lid_part(kit.cyl(0.0035, 0.003, at=(ic[0] + 0.088 * math.cos(a), ic[1] + 0.088 * math.sin(a), -0.004),
                     material=steel_m, verts=12))
# outer side: steam vent cap near the front edge
vent = kit.extrude(rrect(0.05, 0.03, 0.014), 0.008, material=kit.mat('#d8ccb2', rough=0.4), bevel=0.003,
                   segments=2, name='vent')
vent.location = (0, -LL + 0.06, LT - 0.003); lid_part(vent)
for k in range(3):
    lid_part(kit.box((0.026, 0.0025, 0.004), at=(0, -LL + 0.052 + k * 0.007, LT + 0.0045), material=ink_m,
                     bevel=0.0008))
# hinge barrel and the body's hinge housing
lid_part(kit.cyl(0.012, 0.11, at=(0, 0.0, 0.006), rot=(0, 90, 0), material=body_m, bevel=0.003, verts=32, name='barrel'))
kit.box((0.13, 0.026, 0.02), at=(0, HY + 0.004, H + 0.004), material=body_m, bevel=0.007, segments=3, name='hinge_block')
hinge.rotation_euler = (math.radians(-100), 0, 0)

# ---------------------------------------------------------------- steam: wisps and DISRUPT
wisp([(PC[0] + 0.005, PC[1] - 0.005, RZ + 0.008), (PC[0] - 0.02, PC[1] - 0.02, RZ + 0.04), (0.0, -0.02, 0.25),
      (-0.04, -0.03, 0.27), (-0.07, -0.015, 0.29)], [0.0025, 0.006, 0.008, 0.009, 0.008], steam_m)
wisp([(PC[0] + 0.03, PC[1] + 0.01, RZ + 0.008), (0.045, 0.03, RZ + 0.05), (0.01, 0.02, 0.27), (0.03, 0.015, 0.33),
      (-0.01, 0.01, 0.37), (-0.03, 0.008, 0.4)], [0.0025, 0.005, 0.006, 0.006, 0.006, 0.005], steam_m)
SIZE = 0.085
for ch, (x, y, z, tilt, yaw) in zip('DISRUPT', [(-0.078, -0.016, 0.318, 8, -10), (-0.084, -0.004, 0.398, -7, -6),
                                                (-0.03, 0.008, 0.412, 7, 0), (0.033, 0.02, 0.43, -8, 6),
                                                (0.047, 0.034, 0.505, 5, 10), (0.11, 0.045, 0.535, -6, 14),
                                                (0.172, 0.055, 0.515, 9, 18)]):
    letters(ch, SIZE, 0.02, 0.0085, (x, y, z), (90 + random.uniform(-6, 6), tilt, yaw), steam_m, res=2)
# a curl of steam leaving the T
wisp([(0.19, 0.055, 0.54), (0.222, 0.06, 0.57), (0.236, 0.064, 0.6), (0.22, 0.066, 0.618), (0.205, 0.064, 0.602),
      (0.215, 0.062, 0.592)], [0.007, 0.006, 0.005, 0.004, 0.003, 0.002], steam_m)

kit.export('rice-cooker')
