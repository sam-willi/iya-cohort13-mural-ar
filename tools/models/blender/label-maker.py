"""Label maker - Alana McCareins.

Her page has two machines, both printing "Cohort 13": the main one, a soft-cornered desktop label printer with a thick
rounded lid ("Label Maker" and a power button on top, two indicator dots on the front, a pill-shaped light on the
side) feeding a die-cut label out of a front slot and down onto the table; and behind it, a pistol-grip embossing
label maker with a big character wheel on top and a strip of embossed tape curling out of its nose.
Both are kept, arranged as she drew them (printer in front, embosser behind and to the right).
Line-only, so: warm-white printer with a grey base band, white label on a cream liner, teal embosser, red Dymo tape.
Invented: printer back (cord port, vents), feet; embosser's far side.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy, bmesh

kit.reset()

ARIAL_B = bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
AVENIR = bpy.data.fonts.load('/System/Library/Fonts/Avenir Next.ttc')

shell_m = kit.mat('#ece7dd', rough=0.38, name='shell')
lid_m = kit.mat('white', rough=0.32, name='lid')
band_m = kit.mat('#8b8780', rough=0.45, name='band')
dark_m = kit.mat('#232426', rough=0.5, name='dark')
rubber_m = kit.mat('rubber', rough=0.85, name='rubber')
liner_m = kit.mat('#e6d9bd', rough=0.6, name='liner')
label_m = kit.mat('#fbf8f1', rough=0.45, name='label')
ink_m = kit.mat('#1b1b1b', rough=0.5, name='ink')
grey_ink_m = kit.mat('#6e6961', rough=0.4, name='greyink')
teal_m = kit.mat('teal', rough=0.38, name='teal')
teal_dk_m = kit.mat('#245f66', rough=0.45, name='tealdk')
cream_m = kit.mat('cream', rough=0.4, name='cream')
chrome_m = kit.mat('chrome', rough=0.25, metal=0.9, name='chrome')
tape_m = kit.mat('red', rough=0.35, name='tape')
led_a = kit.mat('amber', rough=0.3, emit=2.0, name='ledA')
led_t = kit.mat('#5fd0c4', rough=0.3, emit=1.5, name='ledT')


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


def words(s, size, depth, at, rot, material, font=ARIAL_B, align='CENTER', bevel=0.0):
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.font = font; cu.size = size
    cu.extrude = depth / 2; cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.resolution_u = 3
    cu.align_x = align; cu.align_y = 'CENTER'
    o = bpy.data.objects.new('txt', cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    sel(o); bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    return o


def soft_slab(w, d, r, h, at, material, top=0.012, bottom=0.002, seg=4, name='slab'):
    """Rounded-rectangle slab whose top rim is rounded by `top` and bottom rim by `bottom` (weighted bevel)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    pts = rrect(w, d, r)
    lo = [bm.verts.new((x, y, 0)) for x, y in pts]; hi = [bm.verts.new((x, y, h)) for x, y in pts]
    bm.faces.new(lo); bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        bm.faces.new((lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bw = bm.edges.layers.float.new('bevel_weight_edge')
    for e in bm.edges:
        zs = [v.co.z for v in e.verts]
        if zs[0] == zs[1]:
            e[bw] = 1.0 if zs[0] > 0 else bottom / top
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.location = at
    kit.finish(o, material)
    md = o.modifiers.new('bevel', 'BEVEL'); md.width = top; md.segments = seg; md.limit_method = 'WEIGHT'
    sel(o); bpy.ops.object.modifier_move_to_index(modifier='bevel', index=0)
    return o


def profile_solid(poly, width, material, name, bevel=0.0, seg=2, y=0.0):
    """Extrude a side profile [(x, z)] across y (centred on y)."""
    o = kit.extrude(poly, width, material=material, bevel=bevel, segments=seg, name=name)
    o.rotation_euler = (math.radians(90), 0, 0); o.location = (o.location.x, y + width / 2, 0)
    return o


# ================================================================ desktop label printer
PW, PD, PH = 0.17, 0.215, 0.118      # x (front width), y (depth), z
PX, PY = -0.05, 0.0                  # printer centre in plan
FEET = 0.004
SEAM = 0.087                         # top of the base shell
base_h = SEAM - FEET
shell = kit.extrude(rrect(PW, PD, 0.026), base_h, at=(PX, PY, FEET), material=shell_m, bevel=0.006, segments=3,
                    name='shell')
bake(shell)
# label exit slot on the front, just under the lid; cord port and vents on the back
slot = kit.box((0.132, 0.03, 0.007), at=(PX, PY - PD / 2, SEAM - 0.007))
kit.boolean(shell, slot)
port = kit.box((0.016, 0.02, 0.012), at=(PX + 0.045, PY + PD / 2, 0.03))
kit.boolean(shell, port)
for k in range(6):
    v = kit.box((0.004, 0.02, 0.03), at=(PX - 0.06 + k * 0.009, PY + PD / 2, 0.045))
    kit.boolean(shell, v)
edge_bevel(shell, 0.0012)
kit.box((0.13, 0.004, 0.006), at=(PX, PY - PD / 2 + 0.013, SEAM - 0.007), material=dark_m)     # slot throat
kit.box((0.014, 0.004, 0.01), at=(PX + 0.045, PY + PD / 2 - 0.008, 0.03), material=dark_m)
kit.box((0.055, 0.004, 0.03), at=(PX - 0.0375, PY + PD / 2 - 0.009, 0.045), material=dark_m)
# grey base band and feet
band = kit.extrude(rrect(PW - 0.004, PD - 0.004, 0.024), 0.012, at=(PX, PY, FEET + 0.001), material=band_m,
                   bevel=0.003, segments=2, name='band')
for fx in (-0.06, 0.06):
    for fy in (-0.08, 0.08):
        kit.cyl(0.009, FEET + 0.002, at=(PX + fx, PY + fy, (FEET + 0.002) / 2), material=rubber_m, bevel=0.0015,
                verts=20)
# pill-shaped status light on the left side, near the back
pill = kit.extrude(rrect(0.026, 0.006, 0.003), 0.002, material=led_t, name='pill')
pill.rotation_euler = (0, math.radians(-90), 0); pill.location = (PX - PW / 2 + 0.0008, PY + 0.07, 0.05)
# lid: thick, soft-topped slab with a reveal above the shell
lid = soft_slab(PW + 0.002, PD + 0.002, 0.027, PH - SEAM - 0.0015, (PX, PY, SEAM + 0.0015), lid_m, top=0.013,
                bottom=0.0025, name='lid')
kit.extrude(rrect(PW - 0.01, PD - 0.01, 0.022), 0.004, at=(PX, PY, SEAM - 0.001), material=dark_m, name='reveal')
# power button and its ring, "Label Maker", two indicator dots on the lid's front edge
BZ = PH
bx, by = PX - PW / 2 + 0.03, PY - PD / 2 + 0.03
kit.cyl(0.0105, 0.002, at=(bx, by, BZ - 0.0002), material=teal_m, verts=40)
kit.cyl(0.0082, 0.004, at=(bx, by, BZ + 0.0005), material=lid_m, bevel=0.0014, verts=40)
ring = kit.torus(0.0042, 0.0007, at=(bx, by, BZ + 0.0025), material=grey_ink_m, major=24, minor=6)
kit.box((0.0014, 0.0045, 0.001), at=(bx, by + 0.0035, BZ + 0.0025), material=grey_ink_m)
words('Label Maker', 0.0135, 0.0004, (bx + 0.016, by - 0.002, BZ + 0.0001), (0, 0, 0), grey_ink_m, font=AVENIR,
      align='LEFT')
for dx, m in ((0.012, led_a), (0.05, led_t)):
    kit.cyl(0.0022, 0.002, at=(PX + dx, PY - PD / 2 - 0.0005, SEAM + 0.012), rot=(90, 0, 0), material=m, verts=16)

# ---------------------------------------------------------------- the printed label coming out of the slot
LW, LT = 0.112, 0.0006
SY = PY - PD / 2                          # front face
lz = SEAM - 0.007                         # slot height
path = [(SY + 0.01, lz), (SY - 0.008, lz)]   # (y, z) centreline: out of the slot, an S-bend down, flat run
for k in range(1, 9):
    a = math.radians(90 * k / 8)
    path.append((SY - 0.008 - 0.036 * math.sin(a), lz - 0.036 + 0.036 * math.cos(a)))
z1 = lz - 0.036
r2 = z1 - LT / 2
for k in range(1, 9):
    b = math.radians(90 * k / 8)
    path.append((SY - 0.044 - r2 + r2 * math.cos(b), LT / 2 + r2 - r2 * math.sin(b)))
for k in range(1, 5):
    path.append((path[-1][0] - 0.022, LT / 2))
me = bpy.data.meshes.new('liner'); bm = bmesh.new()
rows = []
for y, z in path:
    rows.append([bm.verts.new((PX - LW / 2, y, z)), bm.verts.new((PX + LW / 2, y, z))])
for a, b in zip(rows, rows[1:]):
    bm.faces.new((a[0], a[1], b[1], b[0]))
bm.to_mesh(me); bm.free()
liner = bpy.data.objects.new('liner', me); bpy.context.collection.objects.link(liner)
sel(liner)
md = liner.modifiers.new('solid', 'SOLIDIFY'); md.thickness = LT; md.offset = 0
kit.finish(liner, liner_m, smooth=40)
# the sticker on the flat run, with its rounded die-cut corners, and the print
yl0, yl1 = path[-1][0] + 0.006, path[-5][0] - 0.002
sticker = kit.extrude(rrect(LW - 0.01, yl1 - yl0, 0.008), 0.0004, at=(PX, (yl0 + yl1) / 2, LT), material=label_m,
                      name='sticker')
words('Cohort 13', 0.024, 0.0002, (PX + 0.004, (yl0 + yl1) / 2, LT + 0.0004 + 0.0001), (0, 0, -90), ink_m)

# ================================================================ pistol-grip embosser, to the right and behind
# Built with its nose (tape exit) toward +x and its wheel side toward the front, so it sits beside the printer
# with its profile and tape facing the same way as the printer's label.
EX, EY, EYAW = 0.135, 0.055, -12       # position and a slight turn toward the viewer
emb = []
EW = 0.044                             # body width (y)
M = lambda pts: [(-x, z) for x, z in pts]   # profiles below are drawn nose-left, then mirrored nose-right
body_prof = M([(-0.08, 0.082), (0.072, 0.082), (0.08, 0.09), (0.08, 0.112), (0.072, 0.12), (-0.064, 0.12),
               (-0.08, 0.108)])
emb.append(profile_solid(body_prof, EW, teal_m, 'emb_body', bevel=0.007, seg=3))


def curve_pts(p0, p1, p2, n=10):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


# grip: waisted column flaring into a stable foot
front = curve_pts((-0.03, 0.085), (-0.012, 0.04), (-0.052, 0.0), 10)
back = curve_pts((0.044, 0.0), (0.012, 0.04), (0.03, 0.085), 10)
emb.append(profile_solid(M(front + back), EW - 0.008, teal_dk_m, 'emb_grip', bevel=0.006, seg=3))
# squeeze lever: a C-shaped bar behind the grip
lev = curve_pts((0.07, 0.083), (0.075, 0.03), (0.04, 0.012), 12)
inner = [(x - 0.011 * (1 - i / 12) - 0.004, z + 0.004) for i, (x, z) in enumerate(lev)]
emb.append(profile_solid(M(lev + list(reversed(inner))), EW - 0.016, dark_m, 'emb_lever', bevel=0.003, seg=2))
emb.append(kit.box((0.012, EW - 0.02, 0.01), at=(-0.066, 0, 0.082), material=dark_m, bevel=0.002, name='lever_pivot'))
# character wheel on top, overhanging the front: a disc with raised characters round the rim, hub and pointer
WC = (0.022, -0.006, 0.12)
emb.append(kit.cyl(0.036, 0.009, at=(WC[0], WC[1], WC[2] + 0.0035), material=cream_m, bevel=0.002, verts=64,
                   name='wheel'))
for k in range(40):
    a = math.tau * k / 40
    emb.append(kit.box((0.0022, 0.0045, 0.0016), at=(WC[0] + 0.03 * math.cos(a), WC[1] + 0.03 * math.sin(a),
                                                      WC[2] + 0.0083), rot=(0, 0, math.degrees(a)), material=ink_m))
emb.append(kit.cyl(0.011, 0.007, at=(WC[0], WC[1], WC[2] + 0.009), material=teal_dk_m, bevel=0.002, verts=32))
emb.append(kit.cyl(0.0045, 0.004, at=(WC[0], WC[1], WC[2] + 0.0128), material=chrome_m, bevel=0.001, verts=20))
emb.append(kit.box((0.012, 0.008, 0.004), at=(WC[0] - 0.033, WC[1], WC[2] + 0.009), material=chrome_m, bevel=0.0012))
# character window behind the wheel
emb.append(kit.box((0.03, 0.02, 0.006), at=(-0.04, 0.0, 0.121), material=teal_dk_m, bevel=0.002))
emb.append(kit.box((0.022, 0.012, 0.002), at=(-0.04, 0.0, 0.1245), material=kit.mat('#d7e8ee', rough=0.15)))
emb.append(words('M', 0.009, 0.0004, (-0.04, 0.0, 0.1257), (0, 0, 0), ink_m))
# tape nose and the embossed tape running out of it
emb.append(kit.box((0.016, 0.022, 0.016), at=(0.084, 0.0, 0.1), material=teal_dk_m, bevel=0.004, name='nose'))
TW = 0.012
tp = [(0.088, 0.0), (0.12, -0.003), (0.152, -0.006), (0.163, -0.011), (0.17, -0.02), (0.172, -0.03)]
me = bpy.data.meshes.new('tape'); bm = bmesh.new(); rows = []
for x, y in tp:
    rows.append([bm.verts.new((x, y, 0.1 - TW / 2)), bm.verts.new((x, y, 0.1 + TW / 2))])
for a, b in zip(rows, rows[1:]):
    bm.faces.new((a[0], a[1], b[1], b[0]))
bm.to_mesh(me); bm.free()
tape = bpy.data.objects.new('tape', me); bpy.context.collection.objects.link(tape)
md = tape.modifiers.new('solid', 'SOLIDIFY'); md.thickness = 0.0008; md.offset = 0
kit.finish(tape, tape_m, smooth=40)
emb.append(tape)
# embossed white letters on the straight run, reading from the nose outward
(x0, y0), (x1, y1) = tp[0], tp[2]
phi = math.degrees(math.atan2(y1 - y0, x1 - x0))
nx, ny = -(y1 - y0), (x1 - x0)
L = math.hypot(nx, ny); nx, ny = nx / L, ny / L
if ny > 0:
    nx, ny = -nx, -ny
cx, cy = (x0 + x1) / 2 + 0.002, (y0 + y1) / 2
emb.append(words('Cohort 13', 0.0092, 0.0006, (cx + nx * 0.0006, cy + ny * 0.0006, 0.1), (90, 0, phi),
                 kit.mat('white', rough=0.4)))

# stand the embosser in place
root = bpy.data.objects.new('embosser', None); bpy.context.collection.objects.link(root)
for o in emb:
    if o.parent is None:
        o.parent = root
root.location = (EX, EY, 0); root.rotation_euler = (0, 0, math.radians(EYAW))

kit.export('label-maker')
