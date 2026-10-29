"""Baby stroller (Oli Reyes).

The drawing is a stroller built like a little car: a tub body whose sides dip down around the seat, a tall
curved front panel filled with mesh, an "IYA" licence plate and a round headlight below it, flared bumpers at
the corners, a raised rear box with "13" on its side, four chunky wheels, a bucket seat with a curved back,
and a tall push handle (two flat bars leaning back to a D-shaped top bar with a pivot bolt). Line-only, so:
red lacquered body, cream trim, black tyres, chrome hubs, honey seat fabric.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, subprocess, tempfile
from mathutils import Vector, Matrix

kit.reset()
FUTURA = '/System/Library/Fonts/Supplemental/Futura.ttc'
DIN = '/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf'


def text3d(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, bevel=0.0, res=3,
           spacing=1.0, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res; cu.space_character = spacing
    cu.bevel_depth = bevel; cu.bevel_resolution = 1
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def resmooth(o, angle=35):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


def rod(a, b, r, material, verts=12, name='rod'):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=tuple((a + b) / 2), verts=verts, name=name)
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    return kit.finish(o, material)


# ---------- materials ----------
lacquer = kit.mat('#b02f27', rough=0.3, name='lacquer')
cream = kit.mat('cream', rough=0.4, name='cream')
chrome = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
tyre = kit.mat('rubber', rough=0.82, name='tyre')
foam = kit.mat('#2a2826', rough=0.9, name='foam')
alu = kit.mat('#9aa0a8', rough=0.32, metal=0.85, name='alu')
fabric = kit.mat('#c8893d', rough=0.9, name='fabric')
fabric_dk = kit.mat('#a46a2a', rough=0.9, name='fabric_dark')
lens = kit.mat('#fff4d6', rough=0.08, emit=0.4, name='headlight')
tail = kit.mat('#d0402e', rough=0.15, emit=0.25, name='taillight')
ink = kit.mat('black', rough=0.5, name='ink')
mesh_tex = os.path.join(tempfile.mkdtemp(), 'mesh.png')
subprocess.run(['/usr/bin/env', 'python3', '-c', r"""
import sys
from PIL import Image, ImageDraw, ImageFilter
N = 256; im = Image.new('RGB', (N, N), (38, 36, 34)); d = ImageDraw.Draw(im)
s = 16
for k in range(-N, 2 * N, s):
    d.line([(k, 0), (k + N, N)], fill=(92, 88, 82), width=3)
    d.line([(k, N), (k + N, 0)], fill=(92, 88, 82), width=3)
im.filter(ImageFilter.GaussianBlur(0.6)).save(sys.argv[1])
""", mesh_tex], check=True)
mesh_m = kit.mat('#ffffff', rough=0.85, name='mesh', image=mesh_tex)

# ---------- dimensions ----------
BW = 0.46                      # body width (x)
Y0, Y1 = -0.40, 0.40           # front / rear
ZB, ZT = 0.10, 0.44            # body bottom / top of front wall and rear box
WR = 0.105                     # wheel radius
YF, YR = -0.255, 0.265         # axle positions
FRONT_T = 0.075                # front wall thickness
REAR_Y = 0.17                  # front of the rear box

# ---------- body tub ----------
body = kit.box((BW, Y1 - Y0, ZT - ZB), at=(0, (Y0 + Y1) / 2, (ZB + ZT) / 2), bevel=0.03, segments=4, name='body')
# cockpit hollow
cock = kit.box((BW - 0.05, REAR_Y - (Y0 + FRONT_T), 0.5), at=(0, (Y0 + FRONT_T + REAR_Y) / 2, 0.21 + 0.25),
               bevel=0.02, segments=3, name='cockpit')
kit.boolean(body, cock)
# the sides dip down around the seat: elliptical cut through both side walls
dip = kit.cyl(1.0, BW + 0.1, rot=(0, 90, 0), verts=96, name='dip')
dip.scale = (0.20, 0.235, 1.0)
dip.location = (0, -0.075, 0.48)
kit.boolean(body, dip)
# mesh-panel recess in the upper front, plate + light recess in the lower front
rec = kit.box((BW - 0.07, 0.03, 0.17), at=(0, Y0, 0.335), bevel=0.014, segments=3, name='rec')
kit.boolean(body, rec)
# the rear box is an open-top bin behind the seat
binc = kit.box((BW - 0.05, Y1 - REAR_Y - 0.045, 0.24), at=(0, (REAR_Y + Y1) / 2 - 0.0, ZT), bevel=0.012, segments=2,
               name='bin')
kit.boolean(body, binc)
kit.finish(body, lacquer)
resmooth(body, 32)

# the curved mesh panel in the front recess (bows outward like a windscreen)
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
NX, NZ = 16, 6
pw, ph = BW - 0.08, 0.16
rows = []
for j in range(NZ + 1):
    row = []
    for i in range(NX + 1):
        u, v = i / NX, j / NZ
        x = -pw / 2 + pw * u
        y = Y0 + 0.012 - 0.008 * (1 - (2 * u - 1) ** 2)
        row.append(bm.verts.new((x, y, 0.335 - ph / 2 + ph * v)))
    rows.append(row)
for j in range(NZ):
    for i in range(NX):
        f = bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][i + 1], rows[j][i + 1]))
        for l in f.loops:
            l[uvl].uv = ((l.vert.co.x + pw / 2) / pw * 2.6, (l.vert.co.z - 0.255) / ph * 0.9)
me = bpy.data.meshes.new('mesh'); bm.to_mesh(me); bm.free()
mp = bpy.data.objects.new('meshpanel', me); bpy.context.collection.objects.link(mp)
kit.finish(mp, mesh_m, smooth=80)
mp.data.polygons.foreach_set('use_smooth', [True] * len(mp.data.polygons))
# cream frame around the mesh (a raised rounded ring)
fr = kit.box((BW - 0.05, 0.008, 0.19), at=(0, Y0 - 0.001, 0.335), bevel=0.02, segments=4, name='frame')
frc = kit.box((BW - 0.075, 0.05, 0.165), at=(0, Y0, 0.335), bevel=0.014, segments=3, name='framecut')
kit.boolean(fr, frc)
kit.finish(fr, cream); resmooth(fr, 40)
# cream frame rail along the top of the front wall
kit.tube([(-BW / 2 + 0.02, Y0 + 0.03, ZT + 0.004), (0, Y0 + 0.024, ZT + 0.006), (BW / 2 - 0.02, Y0 + 0.03, ZT + 0.004)],
         0.008, material=cream, name='frontrail')

# licence plate "IYA" and the headlights
kit.box((0.20, 0.008, 0.068), at=(0, Y0 - 0.001, 0.19), material=chrome, bevel=0.004, segments=2, name='plate')
kit.box((0.186, 0.004, 0.054), at=(0, Y0 - 0.004, 0.19), material=kit.mat('#f4ecd8', 0.4, 0, 'platefield'),
        bevel=0.002, name='platefield')
text3d('I Y A', 0.05, 0.0024, font=DIN, at=(0, Y0 - 0.0062, 0.189), material=ink, name='plate_txt')
for sx in (-1, 1):
    hx = sx * (BW / 2 - 0.05)
    kit.cyl(0.03, 0.016, at=(hx, Y0 - 0.002, 0.2), rot=(90, 0, 0), material=chrome, bevel=0.003, verts=32,
            name='lamp_bezel')
    kit.sphere(0.024, at=(hx, Y0 - 0.008, 0.2), scale=(1, 0.45, 1), material=lens, segs=24, rings=12, name='lamp')

# bumpers: stepped flares at the four bottom corners, joined by a cream bar front and back
for sy, yb in ((-1, Y0), (1, Y1)):
    kit.box((BW + 0.04, 0.035, 0.035), at=(0, yb + sy * 0.008, ZB + 0.025), material=cream, bevel=0.012, segments=3,
            name='bumper')
    for sx in (-1, 1):
        kit.box((0.05, 0.045, 0.03), at=(sx * (BW / 2 + 0.0), yb - sy * 0.012, ZB + 0.014), material=lacquer,
                bevel=0.01, segments=3, name='flare')

# rear: "13" on both sides of the rear box, tail lights and a basket pocket on the back
for sx in (-1, 1):
    text3d('13', 0.12, 0.004, font=FUTURA, at=(sx * (BW / 2 + 0.0015), (REAR_Y + Y1) / 2 + 0.005, 0.33),
           rot=(90, 0, 90 if sx > 0 else -90), material=cream, bevel=0.0008, spacing=0.9, name='thirteen')
for sx in (-1, 1):
    kit.cyl(0.018, 0.01, at=(sx * (BW / 2 - 0.045), Y1 + 0.002, 0.36), rot=(90, 0, 0), material=tail, bevel=0.002,
            verts=24, name='tail')
kit.box((0.25, 0.012, 0.13), at=(0, Y1 + 0.003, 0.27), material=kit.mat('#3a2a20', 0.85, 0, 'pocket'),
        bevel=0.008, segments=2, name='pocket')
kit.box((0.25, 0.016, 0.012), at=(0, Y1 + 0.005, 0.335), material=cream, bevel=0.004, name='pocketlip')

# ---------- seat ----------
SY0, SY1 = Y0 + FRONT_T + 0.01, REAR_Y - 0.01
kit.box((BW - 0.07, SY1 - SY0 - 0.06, 0.05), at=(0, (SY0 + SY1) / 2 - 0.03, 0.235), material=fabric, bevel=0.018,
        segments=3, name='cushion')
# piping seam on the cushion
kit.box((BW - 0.08, 0.006, 0.004), at=(0, (SY0 + SY1) / 2 - 0.03, 0.261), material=fabric_dk, bevel=0.002,
        name='seam')
# curved backrest shell, leaning back against the rear box
back = kit.cyl(0.19, 0.23, at=(0, 0, 0), verts=40, name='back')
bkc = kit.cyl(0.165, 0.3, at=(0, 0, 0), verts=40, name='bkc')
kit.boolean(back, bkc)
cutb = kit.box((0.5, 0.5, 0.5), at=(0, -0.25 - 0.0, 0), name='cutb')
kit.boolean(back, cutb)   # keep the back half: a U-shaped shell
back.rotation_euler = (math.radians(-14), 0, 0)
back.location = (0, REAR_Y - 0.198, 0.355)
kit.finish(back, fabric, bevel=0.006, segments=2)
resmooth(back, 40)
# harness straps
for sx in (-1, 1):
    kit.box((0.022, 0.004, 0.14), at=(sx * 0.055, REAR_Y - 0.198 + 0.165 + 0.0, 0.37), rot=(-14, 0, 0), material=foam,
            name='strap')
kit.box((0.03, 0.012, 0.03), at=(0, SY0 + 0.09, 0.275), material=alu, bevel=0.004, name='buckle')
kit.box((0.022, 0.004, 0.06), at=(0, SY0 + 0.09, 0.255), material=foam, name='crotchstrap')

# ---------- wheels ----------
tyre_prof = [(0.07, -0.03), (0.088, -0.031), (0.1, -0.026), (0.105, -0.012), (0.105, 0.012), (0.1, 0.026),
             (0.088, 0.031), (0.07, 0.03)]
for y in (YF, YR):
    for sx in (-1, 1):
        cx = sx * (BW / 2 + 0.036)
        t = kit.lathe(tyre_prof + [(0.07, -0.03)], material=tyre, steps=48, name='tyre')
        t.rotation_euler = (0, math.radians(90), 0); t.location = (cx, y, WR)
        kit.cyl(0.071, 0.05, at=(cx, y, WR), rot=(0, 90, 0), material=cream, verts=40, name='rim')
        kit.cyl(0.046, 0.012, at=(cx + sx * 0.026, y, WR), rot=(0, 90, 0), material=chrome, bevel=0.004, verts=40,
                name='hubcap')
        kit.cyl(0.014, 0.008, at=(cx + sx * 0.034, y, WR), rot=(0, 90, 0), material=lacquer, bevel=0.002, verts=20,
                name='hubdot')
# axles hidden behind the rims
for y in (YF, YR):
    rod((-BW / 2 - 0.03, y, WR), (BW / 2 + 0.03, y, WR), 0.009, alu, name='axle')

# ---------- push handle ----------
HY0, HZ0 = -0.1, 0.235         # where the bars meet the body sides
HY1, HZ1 = 0.37, 1.0           # top
for sx in (-1, 1):
    x = sx * (BW / 2 + 0.018)
    a, b = Vector((x, HY0, HZ0)), Vector((x, HY1, HZ1))
    d = b - a
    bar = kit.box((0.015, 0.044, d.length), material=alu, bevel=0.005, segments=2, name='bar')
    bar.location = (a + b) / 2
    bar.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    # pivot hub where the bar bolts to the body
    kit.cyl(0.03, 0.016, at=(sx * (BW / 2 + 0.008), HY0, HZ0), rot=(0, 90, 0), material=foam, bevel=0.004, verts=32,
            name='pivot')
    kit.cyl(0.011, 0.02, at=(sx * (BW / 2 + 0.019), HY0, HZ0), rot=(0, 90, 0), material=chrome, bevel=0.002,
            verts=20, name='bolt')
# D-section foam top bar with pivot-bolt caps
tw = BW + 0.036 + 0.03
prof = [(0.03 * math.cos(a), 0.024 * math.sin(a)) for a in (math.pi * i / 10 for i in range(11))]
prof = [(-0.03, -0.006)] + [(p[0], p[1]) for p in reversed(prof)] + [(0.03, -0.006)]
top = kit.extrude([(p[0], p[1]) for p in prof], tw, material=foam, bevel=0.003, name='topbar')
top.rotation_euler = (math.radians(-90 + 34), 0, math.radians(90))
top.rotation_euler = (0, 0, 0)
# build it explicitly: profile in the YZ plane, extruded along X
for v in top.data.vertices:
    px, py, pz = v.co.x, v.co.y, v.co.z
    v.co = Vector((pz - tw / 2, px, py))
top.data.update()
top.rotation_euler = (math.radians(34), 0, 0)
top.location = (0, HY1 + 0.004, HZ1 + 0.006)
kit.finish(top, foam)
for sx in (-1, 1):
    kit.cyl(0.026, 0.01, at=(sx * (tw / 2 + 0.004), HY1 + 0.004, HZ1 + 0.012), rot=(0, 90, 0), material=alu,
            bevel=0.002, verts=24, name='endcap')
    kit.cyl(0.008, 0.006, at=(sx * (tw / 2 + 0.01), HY1 + 0.004, HZ1 + 0.012), rot=(0, 90, 0), material=chrome,
            verts=16, name='capbolt')

kit.export('baby-stroller')
