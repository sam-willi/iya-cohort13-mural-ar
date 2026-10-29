"""Typewriter, after Daisy Wang's drawing (RV P4a).

As drawn: a portable typewriter with a shell that steps down from a flat rear deck to the keyboard in an S-curve, four
staggered rows of round keys on wire stems, a long space bar, the typebar fan in a curved opening with the little type
guide arch, a carriage that overhangs both sides (flat end plate on the left; big knob, a small block and the carriage
return lever with its handle on the right), a sheet of paper reading "THE PLACE WHERE OUR STORY BEGINS...", and a
"COHORT 13" tape label with zigzag ends stuck on the left side at an angle.
Line-only drawing, so the colours are vintage portable: teal shell, cream keys in chrome rims, black platen, red label.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
from mathutils import Vector, Matrix


# ---------------------------------------------------------------- helpers
def side_extrude(poly_yz, x0, x1, material, bevel=0.0, segments=2, name='ext'):
    """Extrude a polygon drawn in the YZ plane (side view, y forward/back, z up) across X."""
    o = kit.extrude([(y, z) for y, z in poly_yz], x1 - x0, material=material, bevel=bevel, segments=segments, name=name)
    # local x->y, local y->z, local z (extrude)->x
    o.rotation_euler = (math.radians(90), 0, math.radians(90))
    o.location = (x0, 0, 0)
    return o


def rod(p0, p1, r, material, verts=16, bevel=0.0, name='rod'):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = kit.cyl(r, d.length, material=material, verts=verts, bevel=bevel, name=name)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.location = (p0 + p1) / 2
    return o


def xcyl(r, length, at, material, verts=32, bevel=0.0, name='xcyl'):
    return kit.cyl(r, length, at=at, rot=(0, 90, 0), material=material, verts=verts, bevel=bevel, name=name)


def mesh_obj(name, verts, faces, material=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    return o


# ---------------------------------------------------------------- materials
M_SHELL = kit.mat('#3d8c93', rough=0.35, name='teal_enamel')
M_SHELL_DK = kit.mat('#2a6268', rough=0.4, name='teal_dark')
M_CHROME = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
M_STEEL = kit.mat('steel', rough=0.3, metal=0.9, name='steel')
M_KEY = kit.mat('cream', rough=0.35, name='key_cream')
M_BLACK = kit.mat('black', rough=0.45, name='black')
M_PLATEN = kit.mat('#1b1b1c', rough=0.7, name='platen_rubber')
M_PAPER = kit.mat('paper', rough=0.85, name='paper')
M_INK = kit.mat('#1d1d22', rough=0.6, name='ink')
M_LABEL = kit.mat('red', rough=0.35, name='label_tape')
M_LABEL_TXT = kit.mat('#f7f1e3', rough=0.4, name='label_text')
M_RIBBON = kit.mat('#141414', rough=0.6, name='ribbon')
M_RIBBON_R = kit.mat('cardinal', rough=0.6, name='ribbon_red')
M_FELT = kit.mat('#2a2522', rough=0.9, name='felt')

# ---------------------------------------------------------------- shell
W = 0.34
YF, YB = -0.165, 0.125
ZH = 0.085                         # rear deck height
prof = [(YF, 0.0), (YB, 0.0), (YB, ZH - 0.004), (YB - 0.01, ZH)]
prof += [(-0.012, ZH)]
for i in range(1, 11):             # the S-curve down to the keyboard
    t = i / 10
    y = -0.012 - 0.07 * t
    z = ZH - (ZH - 0.05) * (0.5 - 0.5 * math.cos(math.pi * t))
    prof.append((y, z))
prof += [(-0.12, 0.043), (YF + 0.012, 0.034), (YF, 0.026)]
shell = side_extrude(prof, -W / 2, W / 2, M_SHELL, bevel=0.012, segments=4, name='shell')
# rubber feet
for sx in (-1, 1):
    for sy in (YF + 0.03, YB - 0.03):
        kit.cyl(0.012, 0.006, at=(sx * (W / 2 - 0.03), sy, -0.001), material=M_BLACK, verts=16, bevel=0.002, name='foot')

# typebar opening: an annular sector in the rear deck, centred on the type guide
GC = Vector((0, 0.072, ZH))
R0, R1, SPAN = 0.042, 0.088, math.radians(64)
pts = []
for i in range(25):
    a = -math.pi / 2 - SPAN + 2 * SPAN * i / 24
    pts.append((GC.x + R1 * math.cos(a), GC.y + R1 * math.sin(a)))
for i in range(25):
    a = -math.pi / 2 + SPAN - 2 * SPAN * i / 24
    pts.append((GC.x + R0 * math.cos(a), GC.y + R0 * math.sin(a)))
cut = kit.extrude(pts, 0.05, at=(0, 0, ZH - 0.025))
kit.boolean(shell, cut)
# the dark segment floor inside, and the fan of typebars resting on it
floor = kit.extrude(pts, 0.004, at=(0, 0, ZH - 0.024), material=M_FELT, name='basket_floor')
for i in range(32):
    a = -math.pi / 2 - SPAN * 0.97 + 2 * SPAN * 0.97 * i / 31
    p0 = Vector((GC.x + (R0 + 0.002) * math.cos(a), GC.y + (R0 + 0.002) * math.sin(a), ZH - 0.006))
    p1 = Vector((GC.x + (R1 - 0.004) * math.cos(a), GC.y + (R1 - 0.004) * math.sin(a), ZH - 0.017))
    b = kit.box(((p1 - p0).length, 0.0022, 0.0035), material=M_STEEL, name='typebar')
    b.rotation_mode = 'QUATERNION'
    b.rotation_quaternion = Vector((1, 0, 0)).rotation_difference((p1 - p0).normalized())
    b.location = (p0 + p1) / 2
    kit.box((0.003, 0.004, 0.005), at=p0 + Vector((0, 0, 0.002)), material=M_STEEL, name='type_slug').rotation_euler.z = a
# type guide: the little arch where the bars meet, on two legs (as drawn)
tg = kit.torus(0.011, 0.0022, at=(0, GC.y + 0.006, ZH + 0.016), rot=(90, 0, 0), material=M_CHROME, major=24, minor=6, name='type_guide')
bm = bmesh.new(); bm.from_mesh(tg.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -0.0005], context='VERTS')  # local y<0 -> lower half after rot
bm.to_mesh(tg.data); bm.free()
for sx in (-1, 1):
    rod((sx * 0.004, GC.y + 0.002, ZH - 0.004), (sx * 0.011, GC.y + 0.006, ZH + 0.016), 0.0018, M_CHROME, verts=8, name='guide_leg')
# ribbon passing through the guide
kit.box((0.16, 0.003, 0.006), at=(0, GC.y + 0.009, ZH + 0.012), material=M_RIBBON, name='ribbon')
kit.box((0.16, 0.0032, 0.0028), at=(0, GC.y + 0.009, ZH + 0.0075), material=M_RIBBON_R, name='ribbon_red')
for sx in (-1, 1):  # ribbon spool covers
    kit.cyl(0.032, 0.006, at=(sx * 0.115, 0.06, ZH + 0.002), material=M_SHELL_DK, verts=40, bevel=0.002, name='spool_cover')
    kit.cyl(0.006, 0.006, at=(sx * 0.115, 0.06, ZH + 0.006), material=M_CHROME, verts=16, bevel=0.0015, name='spool_hub')

# ---------------------------------------------------------------- keyboard: four staggered rows of round keys on stems
def deck_z(y):
    # height of the keyboard well floor under a key (follows the shell profile)
    pts = [(YF + 0.012, 0.034), (-0.12, 0.043), (-0.082, 0.05), (-0.047, 0.0675), (-0.012, ZH)]
    for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            return z0 + (z1 - z0) * (y - y0) / (y1 - y0)
    return 0.034


rows = [(9, -0.142, 0.059), (10, -0.119, 0.069), (11, -0.096, 0.079), (11, -0.073, 0.089)]   # (count, y, cap z), front to back
PITCH = 0.0205
for r, (n, y, zc) in enumerate(rows):
    off = 0.005 * r - 0.004
    for k in range(n):
        x = (k - (n - 1) / 2) * PITCH + off
        kit.cyl(0.0096, 0.0045, at=(x, y, zc), material=M_CHROME, verts=20, bevel=0.0012, name='key_rim')
        kit.cyl(0.0083, 0.0012, at=(x, y, zc + 0.0026), material=M_KEY, verts=20, name='key_top')
        zb = deck_z(y + 0.01)
        rod((x, y + 0.002, zc - 0.002), (x, y + 0.01, zb - 0.002), 0.0016, M_STEEL, verts=6, name='key_stem')
# space bar on two arms
kit.box((0.17, 0.014, 0.008), at=(0.008, YF + 0.004, 0.05), material=M_KEY, bevel=0.003, segments=2, name='space_bar')
kit.box((0.172, 0.016, 0.003), at=(0.008, YF + 0.004, 0.0455), material=M_CHROME, bevel=0.001, name='space_rim')
for sx in (-1, 1):
    rod((0.008 + sx * 0.07, YF + 0.006, 0.046), (0.008 + sx * 0.075, YF + 0.03, 0.036), 0.0022, M_STEEL, verts=8, name='space_arm')
# shift keys and a margin release at the row ends
for sx in (-1, 1):
    kit.box((0.022, 0.016, 0.006), at=(sx * 0.125, -0.119, 0.07), material=M_KEY, bevel=0.003, name='shift_key')
    rod((sx * 0.125, -0.117, 0.066), (sx * 0.125, -0.109, deck_z(-0.109) - 0.002), 0.002, M_STEEL, verts=6, name='shift_stem')

# ---------------------------------------------------------------- carriage
PY, PZ, PR = YB - 0.012, ZH + 0.034, 0.024
rail = kit.box((0.38, 0.03, 0.012), at=(0.0, PY + 0.004, ZH + 0.006), material=M_SHELL_DK, bevel=0.003, name='carriage_rail')
xcyl(PR, 0.31, (0.0, PY, PZ), M_PLATEN, verts=40, bevel=0.002, name='platen')
xcyl(0.006, 0.42, (0.0, PY, PZ), M_CHROME, verts=12, name='platen_axle')
for sx in (-1, 1):
    side_extrude([(PY - 0.03, ZH + 0.002), (PY + 0.022, ZH + 0.002), (PY + 0.022, PZ + 0.02), (PY - 0.01, PZ + 0.03),
                  (PY - 0.03, PZ + 0.006)], sx * 0.16 - 0.004, sx * 0.16 + 0.004, M_SHELL_DK, bevel=0.003, name='carriage_end')
# paper bail: a chrome rod in front of the platen with two little rollers
xcyl(0.0022, 0.30, (0.0, PY - PR - 0.004, PZ + 0.012), M_CHROME, verts=10, name='paper_bail')
for x in (-0.06, 0.06):
    xcyl(0.005, 0.012, (x, PY - PR - 0.004, PZ + 0.012), M_PLATEN, verts=16, bevel=0.001, name='bail_roller')
# paper table behind the platen: a curved chrome plate rising backward
pt = []
for i in range(9):
    t = i / 8
    pt.append((PY + 0.01 + 0.03 * t, PZ + 0.002 + 0.045 * t + 0.01 * t * t))
pt_poly = [(y, z) for y, z in pt] + [(y + 0.0018, z - 0.002) for y, z in reversed(pt)]
side_extrude(pt_poly, -0.14, 0.14, M_CHROME, name='paper_table')
# left end: a flat rectangular end plate over a small platen knob (as drawn)
xcyl(0.02, 0.025, (-0.18, PY, PZ), M_BLACK, verts=32, bevel=0.003, name='left_knob')
kit.box((0.012, 0.075, 0.06), at=(-0.198, PY - 0.012, PZ - 0.004), material=M_SHELL_DK, bevel=0.006, segments=3, name='left_plate')
# right end: big knob with a groove band, a small block on top, and the return lever with its handle
xcyl(0.03, 0.05, (0.19, PY, PZ), M_PLATEN, verts=40, bevel=0.005, name='right_knob')
xcyl(0.0315, 0.008, (0.178, PY, PZ), M_CHROME, verts=40, bevel=0.002, name='knob_band')
for k in range(24):
    a = 2 * math.pi * k / 24
    kit.box((0.034, 0.0035, 0.0035), at=(0.197, PY + 0.03 * math.cos(a), PZ + 0.03 * math.sin(a)), rot=(math.degrees(a), 0, 0),
            material=M_PLATEN, name='knob_rib')
kit.box((0.05, 0.026, 0.02), at=(0.115, PY + 0.002, PZ + PR + 0.012), material=M_SHELL_DK, bevel=0.004, segments=2, name='release_block')
kit.box((0.046, 0.01, 0.006), at=(0.115, PY - 0.012, PZ + PR + 0.024), material=M_CHROME, bevel=0.002, name='release_lever')
lev = [(0.215, PY, PZ + 0.022), (0.245, PY - 0.005, PZ + 0.03), (0.262, PY - 0.035, PZ + 0.024), (0.275, PY - 0.095, PZ + 0.0)]
for a, b in zip(lev, lev[1:]):
    rod(a, b, 0.0042, M_CHROME, verts=12, name='return_lever')
    kit.sphere(0.0042, at=b, material=M_CHROME, segs=12, rings=8, name='lever_joint')
hd = Vector(lev[-1]); dirv = (Vector(lev[-1]) - Vector(lev[-2])).normalized()
rod(hd, hd + dirv * 0.045, 0.011, M_BLACK, verts=24, bevel=0.003, name='lever_handle')

# ---------------------------------------------------------------- the paper, rising from the platen and leaning back
SW = 0.21
path = []
for i in range(8):                  # around the front-top of the platen
    a = math.radians(-20 + 100 * i / 7)
    path.append((PY - (PR + 0.0012) * math.cos(a), PZ + (PR + 0.0012) * math.sin(a)))
ytop, ztop = path[-1]
LEAN = math.radians(14)
for i in range(1, 13):              # up and leaning back, with a soft curl at the top
    t = i / 12
    h = 0.17 * t
    path.append((ytop + h * math.sin(LEAN) + 0.012 * t ** 3, ztop + h * math.cos(LEAN)))
nx = 12
verts, faces = [], []
for i, (y, z) in enumerate(path):
    for j in range(nx + 1):
        u = j / nx
        x = -SW / 2 + SW * u
        wave = 0.004 * math.sin(u * math.pi * 2 + 0.5) * (0.4 if i < 9 else 1.0) * min(1, i / 6)
        verts.append((x, y - wave, z))
for i in range(len(path) - 1):
    for j in range(nx):
        a = i * (nx + 1) + j
        faces.append((a, a + 1, a + nx + 2, a + nx + 1))
paper = mesh_obj('paper', verts, faces, M_PAPER)
for p in paper.data.polygons:
    p.use_smooth = True
sd = paper.modifiers.new('solid', 'SOLIDIFY'); sd.thickness = 0.0008; sd.offset = 0.0


def paper_point(u, h):
    """Point on the front of the upright part of the sheet: u across (0..1), h up from where it leaves the platen."""
    x = -SW / 2 + SW * u
    wave = 0.004 * math.sin(u * math.pi * 2 + 0.5)
    t = h / 0.17
    y = ytop + h * math.sin(LEAN) + 0.012 * t ** 3 - wave
    z = ztop + h * math.cos(LEAN)
    return Vector((x, y - 0.0012, z))


_FONT_PATH = '/System/Library/Fonts/Supplemental/Courier New Bold.ttf'   # typed with a typewriter face if the system has it
TYPE_FONT = bpy.data.fonts.load(_FONT_PATH) if os.path.exists(_FONT_PATH) else None


def typed(line, h, size=0.0125, margin=0.016):
    cu = bpy.data.curves.new('typed', 'FONT'); cu.body = line; cu.size = size; cu.extrude = 0.0002
    cu.align_x = 'LEFT'; cu.align_y = 'CENTER'; cu.resolution_u = 2
    if TYPE_FONT:
        cu.font = TYPE_FONT
    t = bpy.data.objects.new('typed', cu); bpy.context.collection.objects.link(t)
    bpy.context.view_layer.objects.active = t; t.select_set(True)
    bpy.ops.object.convert(target='MESH')
    t = bpy.context.object
    t.data.materials.append(M_INK)
    for v in t.data.vertices:
        gx, gy, gz = v.co
        p = paper_point(min(max((gx + margin) / SW, 0), 1), h + gy)
        v.co = p + Vector((0, -gz - 0.0002, 0))
    t.data.update()
    return t


# glyphs are built at the origin, then mapped: x across the sheet from the left margin, z up the sheet
typed('THE PLACE WHERE OUR STORY', 0.143, size=0.0225, margin=0.013)
typed('BEGINS...', 0.121, size=0.0225, margin=0.013)

# ---------------------------------------------------------------- COHORT 13 tape label on the left side, at a jaunty angle
LX = -W / 2 - 0.0002
ang = math.radians(-13)
L, Hh = 0.15, 0.022
poly = []
for i in range(7):                  # zigzag right end
    poly.append((L / 2 - (0.005 if i % 2 else 0.0), -Hh / 2 + Hh * i / 6))
for i in range(7):                  # zigzag left end
    poly.append((-L / 2 + (0.005 if i % 2 else 0.0), Hh / 2 - Hh * i / 6))
lab = kit.extrude(poly, 0.0012, material=M_LABEL, bevel=0.0003, name='label')
txt = kit.text('COHORT 13', 0.0155, 0.0008, rot=(0, 0, 0), material=M_LABEL_TXT, name='label_text')
txt.location = (0, -0.001, 0.0012)
for o in (lab, txt):
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # label plane: local x along the side (reading toward the front, -Y), local y up, local z out of the side (-X)
    m = Matrix.Translation((LX, -0.01, 0.042)) @ Matrix(((0, 0, -1, 0), (-math.cos(ang), math.sin(ang), 0, 0),
                                                        (-math.sin(ang) * -1, math.cos(ang), 0, 0), (0, 0, 0, 1)))
    o.matrix_world = m

kit.export('typewriter')
