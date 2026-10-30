"""Electric scooter (Elizabeth Ahn).

The drawing: a long flat deck with a rounded nose, "IYA '30" written along the top and "COHORT 13" along the
side, a fold latch where the neck meets the tall stem, a straight handlebar with two collars (one labelled
"HONK") and a brake cable looping down the stem, spoked wheels front and back, a curved rear fender with a
tail light, and a kickstand under the deck. Line-only, so: orange frame, black grip tape and tyres, gunmetal
fork and bars, cream lettering.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'
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


def rod(a, b, r, material, verts=16, name='rod', r2=None):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=tuple((a + b) / 2), verts=verts, r2=r2, name=name)
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    return kit.finish(o, material)


def resmooth(o, angle=35):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


def rounded_rect(x0, x1, y0, y1, r_front, r_back, k=10):
    """Plan outline (CCW) with a big radius at the front (y0) and a small one at the back (y1)."""
    pts = []
    def arc(cx, cy, r, a0, a1):
        for i in range(k + 1):
            a = a0 + (a1 - a0) * i / k
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    arc(x1 - r_front, y0 + r_front, r_front, -math.pi / 2, 0)
    arc(x1 - r_back, y1 - r_back, r_back, 0, math.pi / 2)
    arc(x0 + r_back, y1 - r_back, r_back, math.pi / 2, math.pi)
    arc(x0 + r_front, y0 + r_front, r_front, math.pi, 1.5 * math.pi)
    return pts


# ---------- materials ----------
frame = kit.mat('#d9662a', rough=0.35, metal=0.15, name='frame_orange')
gun = kit.mat('gunmetal', rough=0.32, metal=0.85, name='gunmetal')
alu = kit.mat('steel', rough=0.3, metal=0.9, name='alu')
grip = kit.mat('#1e1d1c', rough=0.85, name='griptape')
rubber = kit.mat('rubber', rough=0.8, name='rubber')
cream = kit.mat('cream', rough=0.45, name='cream')
chrome = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
redlens = kit.mat('#c8302a', rough=0.15, emit=0.5, name='taillight')
whitelens = kit.mat('#fff4d6', rough=0.1, emit=0.6, name='headlight')
screen = kit.mat('#1b2a30', rough=0.15, name='display')
screen_txt = kit.mat('#8fc3dc', rough=0.3, emit=0.8, name='display_glow')
amber = kit.mat('amber', rough=0.35, name='amber')

# ---------- dimensions ----------
WR, WW = 0.105, 0.05                 # wheel radius / width
YF, YR = -0.37, 0.39                 # axles
DX = 0.072                           # deck half width
DY0, DY1 = -0.245, 0.30              # deck nose / tail
DZ0, DZ1 = 0.12, 0.162               # deck bottom / top
SY = YF                              # stem line (vertical, above the front axle)
HB = 0.96                            # handlebar height

# ---------- deck ----------
plan = rounded_rect(-DX, DX, DY0, DY1, DX * 0.98, 0.028)
deck = kit.extrude(plan, DZ1 - DZ0, at=(0, 0, DZ0), material=frame, bevel=0.007, segments=3, name='deck')
inset = rounded_rect(-DX + 0.009, DX - 0.009, DY0 + 0.009, DY1 - 0.009, DX * 0.98 - 0.009, 0.02)
kit.extrude(inset, 0.0016, at=(0, 0, DZ1 - 0.0004), material=grip, bevel=0.0006, segments=1, name='griptape')
# battery pan under the deck, a seam away from it
pan = rounded_rect(-DX + 0.012, DX - 0.012, DY0 + 0.05, DY1 - 0.04, 0.045, 0.02)
kit.extrude(pan, 0.03, at=(0, 0, DZ0 - 0.032), material=gun, bevel=0.006, segments=2, name='batterypan')
# the nose curls down into a bumper (the curved skirt drawn under the front of the deck)
nose = kit.extrude(rounded_rect(-DX + 0.004, DX - 0.004, DY0 - 0.002, DY0 + 0.09, DX - 0.0055, 0.01), 0.022,
                   at=(0, 0, DZ0 - 0.02), material=frame, bevel=0.008, segments=3, name='nosecap')
noseclip = kit.box((0.3, 0.3, 0.1), at=(0, DY0 + 0.09 + 0.15 - 0.03, DZ0 - 0.02), name='noseclip')
kit.boolean(nose, noseclip)
kit.box((0.05, 0.006, 0.012), at=(0, DY0 - 0.002, DZ0 - 0.006), material=whitelens, bevel=0.003, name='frontlight')

# lettering: "IYA '30" along the top, "COHORT 13" along both sides
text3d("IYA '30", 0.068, 0.0012, font=FONT, at=(0.0, 0.035, DZ1 + 0.0014), rot=(0, 0, 90), material=cream,
       spacing=1.05, name='top_txt')
for sx in (-1, 1):
    text3d('COHORT 13', 0.031, 0.0012, font=DIN, at=(sx * (DX + 0.0004), 0.03, (DZ0 + DZ1) / 2 - 0.001),
           rot=(90, 0, 90 if sx > 0 else -90), material=cream, spacing=1.1, name='side_txt')

# ---------- wheels ----------
tyre_prof = [(0.078, -WW / 2), (0.092, -WW / 2 - 0.001), (0.101, -WW / 2 + 0.006), (WR, -0.01), (WR, 0.01),
             (0.101, WW / 2 - 0.006), (0.092, WW / 2 + 0.001), (0.078, WW / 2), (0.078, -WW / 2)]


def wheel(y):
    t = kit.lathe(tyre_prof, material=rubber, steps=56, name='tyre')
    t.rotation_euler = (0, math.radians(90), 0); t.location = (0, y, WR)
    rim = kit.lathe([(0.0795, -0.021), (0.0795, 0.021), (0.07, 0.019), (0.07, -0.019), (0.0795, -0.021)],
                    material=alu, steps=48, name='rim')
    rim.rotation_euler = (0, math.radians(90), 0); rim.location = (0, y, WR)
    kit.cyl(0.02, 0.05, at=(0, y, WR), rot=(0, 90, 0), material=gun, bevel=0.004, verts=24, name='hub')
    for k in range(10):
        a = k * math.tau / 10
        for sx in (-1, 1):
            off = 0.3 if sx > 0 else -0.3
            p0 = Vector((sx * 0.016, y + 0.018 * math.cos(a), WR + 0.018 * math.sin(a)))
            p1 = Vector((sx * 0.012, y + 0.071 * math.cos(a + off), WR + 0.071 * math.sin(a + off)))
            rod(p0, p1, 0.0018, chrome, verts=5, name='spoke')


wheel(YF); wheel(YR)

# ---------- rear: fork plates, fender and tail light ----------
for sx in (-1, 1):
    plate = kit.extrude([(DY1 - 0.06, DZ0 + 0.01), (DY1 - 0.005, DZ0 + 0.01), (YR + 0.018, WR + 0.012),
                         (YR + 0.012, WR - 0.016), (YR - 0.02, WR - 0.016), (DY1 - 0.06, DZ0 - 0.012)], 0.008,
                        material=gun, bevel=0.002, name='rearfork')
    for v in plate.data.vertices:
        y, z, x = v.co.x, v.co.y, v.co.z
        v.co = Vector((sx * (WW / 2 + 0.006) + (x - 0.004) * 1.0, y, z))
    plate.data.update()
    kit.cyl(0.009, 0.006, at=(sx * (WW / 2 + 0.013), YR, WR), rot=(0, 90, 0), material=chrome, verts=6,
            name='axlenut')
rod((-WW / 2 - 0.01, YR, WR), (WW / 2 + 0.01, YR, WR), 0.006, alu, name='axle')
# fender: an arc of a channel section over the rear wheel, out past it, ending in the tail light
fp = []
for i in range(25):
    a = math.radians(178 - i * 128 / 24)        # from just behind the deck, over the top, down the back
    fp.append((YR + (WR + 0.016) * math.cos(a), WR + (WR + 0.016) * math.sin(a)))
bm = bmesh.new(); rings = []
prof = [(-0.034, -0.006), (-0.034, 0.0), (-0.028, 0.006), (0.028, 0.006), (0.034, 0.0), (0.034, -0.006),
        (0.028, 0.0), (-0.028, 0.0)]
for i, (y, z) in enumerate(fp):
    nrm = Vector((0, y - YR, z - WR)).normalized()
    rings.append([bm.verts.new((u, y + nrm.y * v, z + nrm.z * v)) for u, v in prof])
for a, b in zip(rings, rings[1:]):
    for j in range(len(prof)):
        bm.faces.new((a[j], a[(j + 1) % len(prof)], b[(j + 1) % len(prof)], b[j]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('fender'); bm.to_mesh(me); bm.free()
fen = bpy.data.objects.new('fender', me); bpy.context.collection.objects.link(fen)
kit.finish(fen, frame, smooth=40)
ty, tz = fp[-1]
tl = kit.box((0.04, 0.02, 0.016), at=(0, ty + 0.012, tz + 0.006), rot=(-40, 0, 0), material=gun, bevel=0.004,
             segments=2, name='taillight_housing')
kit.box((0.032, 0.006, 0.01), at=(0, ty + 0.022, tz + 0.012), rot=(-40, 0, 0), material=redlens, bevel=0.002,
        name='taillight')

# ---------- front: neck, fold latch, head tube, fork ----------
HT0, HT1 = 0.25, 0.375                         # head tube
neck_a = Vector((0, DY0 + 0.045, DZ0 + 0.02)); neck_b = Vector((0, SY + 0.02, HT0 + 0.05))
nd = neck_b - neck_a
neck = kit.box((0.05, nd.length + 0.03, 0.034), material=frame, bevel=0.009, segments=3, name='neck')
neck.location = (neck_a + neck_b) / 2
neck.rotation_euler = Vector((0, 1, 0)).rotation_difference(nd.normalized()).to_euler()
kit.cyl(0.026, HT1 - HT0, at=(0, SY, (HT0 + HT1) / 2), material=frame, bevel=0.004, verts=32, name='headtube')
kit.cyl(0.03, 0.012, at=(0, SY, HT0 + 0.004), material=gun, bevel=0.003, verts=32, name='headset_lo')
kit.cyl(0.03, 0.012, at=(0, SY, HT1 - 0.004), material=gun, bevel=0.003, verts=32, name='headset_hi')
# fold latch: a clamp ring on the stem with a lever lying along the neck
kit.cyl(0.025, 0.034, at=(0, SY, HT1 + 0.017), material=gun, bevel=0.004, verts=32, name='foldclamp')
# the lever lies along the clamp's side, pivoting on a pin at its front end
lev = kit.box((0.008, 0.058, 0.013), at=(0.029, SY + 0.012, HT1 + 0.017), rot=(0, 0, -6), material=amber,
              bevel=0.003, segments=2, name='foldlever')
kit.cyl(0.0065, 0.014, at=(0.028, SY - 0.014, HT1 + 0.017), rot=(0, 90, 0), material=chrome, verts=16,
        name='latchpin')
# fork: crown under the head tube, two legs down to the axle
kit.box((0.09, 0.04, 0.022), at=(0, SY, HT0 - 0.012), material=gun, bevel=0.007, segments=2, name='forkcrown')
for sx in (-1, 1):
    rod((sx * (WW / 2 + 0.008), SY, HT0 - 0.015), (sx * (WW / 2 + 0.008), SY, WR), 0.0085, gun, name='forkleg')
    kit.cyl(0.009, 0.006, at=(sx * (WW / 2 + 0.013), SY, WR), rot=(0, 90, 0), material=chrome, verts=6,
            name='axlenut')
rod((-WW / 2 - 0.01, SY, WR), (WW / 2 + 0.01, SY, WR), 0.006, alu, name='axle')
# small front fender
ffp = []
for i in range(13):
    a = math.radians(40 + i * 100 / 12)
    ffp.append((SY + (WR + 0.012) * math.cos(a) * -1, WR + (WR + 0.012) * math.sin(a)))
prof = [(-0.024, -0.005), (-0.024, 0.0), (-0.019, 0.005), (0.019, 0.005), (0.024, 0.0), (0.024, -0.005),
        (0.019, 0.0), (-0.019, 0.0)]
bm = bmesh.new(); rings = []
for (y, z) in ffp:
    nrm = Vector((0, y - SY, z - WR)).normalized()
    rings.append([bm.verts.new((u, y + nrm.y * v, z + nrm.z * v)) for u, v in prof])
for a, b in zip(rings, rings[1:]):
    for j in range(len(prof)):
        bm.faces.new((a[j], a[(j + 1) % len(prof)], b[(j + 1) % len(prof)], b[j]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('ffender'); bm.to_mesh(me); bm.free()
ff = bpy.data.objects.new('frontfender', me); bpy.context.collection.objects.link(ff)
kit.finish(ff, gun, smooth=40)

# ---------- stem and handlebar ----------
rod((0, SY, HT1 - 0.01), (0, SY, HB - 0.02), 0.017, alu, verts=24, name='stem')
kit.cyl(0.021, 0.012, at=(0, SY, 0.62), material=gun, bevel=0.003, verts=24, name='stemcollar')
kit.box((0.05, 0.034, 0.03), at=(0, SY, HB - 0.012), material=gun, bevel=0.008, segments=2, name='barclamp')
HW = 0.21
rod((-HW, SY, HB), (HW, SY, HB), 0.012, alu, verts=20, name='handlebar')
for sx in (-1, 1):
    g = rod((sx * (HW - 0.105), SY, HB), (sx * (HW + 0.004), SY, HB), 0.0165, rubber, verts=20, name='grip')
    kit.cyl(0.018, 0.006, at=(sx * (HW + 0.004), SY, HB), rot=(0, 90, 0), material=gun, bevel=0.002, verts=20,
            name='barend')
    # the two collars drawn on the bar: brake lever mount (left) and the HONK horn button (right)
    kit.cyl(0.0165, 0.026, at=(sx * 0.09, SY, HB), rot=(0, 90, 0), material=gun if sx < 0 else amber, bevel=0.003,
            verts=20, name='collar')
# brake lever (left)
kit.box((0.09, 0.012, 0.007), at=(-0.135, SY - 0.03, HB - 0.006), rot=(0, 0, 8), material=gun, bevel=0.003,
        segments=2, name='brakelever')
# HONK button + label (right collar)
kit.box((0.022, 0.014, 0.008), at=(0.09, SY - 0.004, HB + 0.017), material=cream, bevel=0.003, segments=2,
        name='honkbutton')
text3d('HONK', 0.0085, 0.0008, font=DIN, at=(0.09, SY - 0.0035, HB + 0.0213), rot=(0, 0, 0), material=frame,
       name='honk_txt')
# thumb throttle (right) and a small display in the middle
kit.box((0.02, 0.03, 0.006), at=(0.12, SY - 0.022, HB + 0.004), rot=(20, 0, 0), material=gun, bevel=0.002,
        name='throttle')
kit.box((0.05, 0.034, 0.012), at=(0, SY - 0.004, HB + 0.022), material=gun, bevel=0.006, segments=2, name='dash')
kit.box((0.036, 0.004, 0.02), at=(0, SY - 0.02, HB + 0.024), rot=(-20, 0, 0), material=screen, bevel=0.002,
        name='display')
text3d('13', 0.012, 0.0006, font=DIN, at=(0, SY - 0.0224, HB + 0.0246), rot=(70, 0, 0), material=screen_txt,
       name='speed')

# brake cable: from the lever, a loose loop down the stem, clipped at the collar, into the fork crown
cable_pts = [(-0.11, SY - 0.01, HB - 0.004), (-0.07, SY - 0.03, HB - 0.03), (-0.04, SY - 0.045, HB - 0.12),
             (-0.035, SY - 0.03, 0.74), (-0.03, SY - 0.022, 0.66), (-0.022, SY - 0.004, 0.62),
             (-0.028, SY - 0.012, 0.5), (-0.03, SY - 0.006, 0.42), (-0.045, SY, HT0 - 0.012)]
kit.tube(cable_pts, 0.0028, material=kit.mat('#2a2826', 0.6, 0, 'cable'), name='cable')

# ---------- kickstand (right side, down to the ground) ----------
ks_top = Vector((DX - 0.004, 0.02, DZ0 - 0.006)); ks_foot = Vector((DX + 0.07, 0.07, 0.006))
kit.cyl(0.008, 0.014, at=tuple(ks_top), rot=(0, 90, 0), material=gun, verts=16, name='kspivot')
rod(ks_top, ks_foot, 0.0055, gun, name='kickstand')
kit.sphere(0.009, at=tuple(ks_foot), scale=(1, 1.4, 0.6), material=rubber, segs=16, rings=8, name='ksfoot')

kit.export('electric-scooter')
