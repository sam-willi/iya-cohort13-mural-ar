"""Espresso machine (Sarah Yoo). As drawn: a soft-cornered head with vent slots and two little buttons on top, a
pressure gauge, two buttons and a 0:25 shot timer on the front, a framed IYA badge and a steam knob on the side, a
steam wand swung out to the right, a thick portafilter, a glass latte cup on a flared drip-tray base."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, tempfile
import numpy as np
from mathutils import Vector, Matrix


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def resmooth(o, angle=30):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    return o


def save_tex(name, rgb):
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 4), np.float32); a[..., :3] = rgb[::-1]
    img = bpy.data.images.new(name, w, h)
    img.pixels.foreach_set(a.ravel())
    path = os.path.join(tempfile.gettempdir(), f'{name}.png')
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


def uv_planar(o, r):
    """Planar UVs from local x/y, mapping a disc of radius r onto the unit square."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / (2 * r) + 0.5, l.vert.co.y / (2 * r) + 0.5)
    bm.to_mesh(o.data); bm.free()
    return o


# ---------- materials ----------
enamel = kit.mat('#9c281f', rough=0.28, name='enamel')          # palette red, glossy enamel
cream = kit.mat('cream', rough=0.4, name='cream')
steel = kit.mat('steel', rough=0.3, metal=0.9, name='steel')
chrome = kit.mat('chrome', rough=0.2, metal=0.95, name='chrome')
base_m = kit.mat('#2b2927', rough=0.45, name='base')
rubber = kit.mat('rubber', rough=0.8, name='rubber')
walnut = kit.mat('walnut', rough=0.55, name='walnut')
dark = kit.mat('#141414', rough=0.15, name='display')
led = kit.mat('amber', rough=0.4, emit=3.0, name='led')
glass = kit.mat('#d6e6ee', rough=0.05, alpha=0.25, name='glass')
water = kit.mat('#8fc3dc', rough=0.1, alpha=0.35, name='water')

# ---------- layout (metres) ----------
HW, HD, HH = 0.30, 0.24, 0.16          # head
HY0 = 0.17 - HD                        # head front plane
HZ0 = 0.30                             # head underside
CY0 = 0.05                             # column front plane
TK0 = 0.115                            # water tank front plane (tank runs to the back at y=0.17)
TRAY = 0.078                           # drip-tray top
GX, GY = -0.015, -0.035                # group head centre (under the gauge, a touch left)

# ---------- base: flared skirt, drip tray with grate ----------

def frustum(w0, d0, w1, d1, z0, z1, mat, bevel, name):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    b = [bm.verts.new((sx * w0 / 2, sy * d0 / 2, z0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    t = [bm.verts.new((sx * w1 / 2, sy * d1 / 2, z1)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(b[::-1]); bm.faces.new(t)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((b[i], b[j], t[j], t[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, mat, bevel, 3)


skirt = frustum(0.36, 0.39, 0.31, 0.34, 0.012, TRAY - 0.008, base_m, 0.012, 'skirt')
kit.box((0.34, 0.37, 0.012), at=(0, 0, 0.006 + 0.0005), material=rubber, bevel=0.004, name='foot_plate')
# tray rim + removable drip tray (steel) with a slotted grate under the cup
kit.box((0.305, 0.335, 0.01), at=(0, 0, TRAY - 0.005), material=base_m, bevel=0.004, name='tray_rim')
tray = kit.box((0.2, 0.17, 0.006), at=(GX, -0.07, TRAY + 0.001), material=steel, bevel=0.002, name='tray')
apply_mods(tray)
for i in range(9):
    s = kit.box((0.16, 0.007, 0.02), at=(GX, -0.135 + i * 0.016, TRAY + 0.002))
    kit.boolean(tray, s)
resmooth(tray)
kit.box((0.19, 0.16, 0.003), at=(GX, -0.07, TRAY - 0.0005), material=dark, name='tray_well')
kit.box((0.08, 0.012, 0.014), at=(GX, -0.163, TRAY - 0.012), material=steel, bevel=0.004, name='tray_pull')

# ---------- column and head ----------
col = kit.box((0.26, TK0 - CY0 + 0.01, HZ0 - TRAY + 0.02), at=(0, (TK0 + 0.01 + CY0) / 2, (HZ0 + TRAY) / 2 + 0.005),
              material=enamel, bevel=0.02, segments=4, name='column')
head = kit.box((HW, HD, HH), at=(0, HY0 + HD / 2, HZ0 + HH / 2), material=enamel, bevel=0.032, segments=5, name='head')
apply_mods(head)
for i in range(9):   # vent slots across the top, back two thirds
    s = kit.box((0.2, 0.007, 0.03), at=(0.015, HY0 + 0.08 + i * 0.015, HZ0 + HH), bevel=0.0)
    kit.boolean(head, s)
resmooth(head)
kit.box((0.205, 0.135, 0.004), at=(0.015, HY0 + 0.14, HZ0 + HH - 0.012), material=dark, name='vent_shadow')
# two square buttons on top, front left (drawn as little squares)
for k, x in enumerate((-0.105, -0.07)):
    kit.box((0.022, 0.022, 0.01), at=(x, HY0 + 0.035, HZ0 + HH + 0.001), material=cream, bevel=0.003, name='top_button')

FY = HY0   # front face plane of the head
# power light, top left
kit.cyl(0.012, 0.006, at=(-0.104, FY - 0.002, HZ0 + 0.112), rot=(90, 0, 0), material=chrome, verts=32, bevel=0.0015,
        name='power_ring')
kit.cyl(0.0085, 0.004, at=(-0.104, FY - 0.005, HZ0 + 0.112), rot=(90, 0, 0), material=led, verts=24, name='power_led')

# pressure gauge with its face texture
gr = 0.038
gx, gz = GX - 0.01, HZ0 + 0.082
n = 512
yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n * 2 - 1
rr = np.hypot(xx, yy); ang = np.degrees(np.arctan2(xx, yy))  # 0 = up, clockwise positive
face = np.ones((n, n, 3)) * np.array([0.96, 0.92, 0.82])
on_arc = np.abs(ang) <= 135
for k in range(28):
    a = -135 + k * 10
    major = k % 3 == 0
    m = (np.abs(ang - a) < (1.3 if major else 0.8)) & (rr > (0.62 if major else 0.7)) & (rr < 0.82)
    face[m] = (0.12, 0.11, 0.1)
red_zone = (ang > 75) & (ang <= 135) & (rr > 0.84) & (rr < 0.9)
face[red_zone] = (0.72, 0.18, 0.15)
green_zone = (ang > 15) & (ang <= 60) & (rr > 0.84) & (rr < 0.9)
face[green_zone] = (0.25, 0.5, 0.3)
face[rr > 0.97] = (0.2, 0.2, 0.2)
gauge_m = kit.mat('#ffffff', rough=0.35, name='gauge_face', image=save_tex('esp_gauge', face))
gface = kit.cyl(gr - 0.004, 0.002, at=(0, 0, 0), verts=48, name='gauge_face')
gface.data.materials.clear(); gface.data.materials.append(gauge_m)
uv_planar(gface, gr - 0.004)
gface.location = (gx, FY - 0.004, gz); gface.rotation_euler = (math.radians(90), 0, 0)
kit.lathe([(gr - 0.006, 0.0), (gr + 0.004, 0.0), (gr + 0.006, 0.006), (gr + 0.002, 0.012), (gr - 0.004, 0.011),
           (gr - 0.006, 0.004), (gr - 0.006, 0.0)], at=(gx, FY + 0.001, gz), rot=(90, 0, 0), material=chrome, steps=64,
          name='gauge_bezel')
kit.lathe([(0, 0.0), (gr - 0.004, 0.0), (gr - 0.0045, 0.006), (gr - 0.006, 0.0085), (0, 0.009)],
          at=(gx, FY - 0.002, gz), rot=(90, 0, 0), material=glass, steps=48, name='gauge_glass')
# the two needles of the drawing, meeting at the hub
for a, L in ((-25, 0.028), (20, 0.022)):
    nd = kit.box((0.0022, L, 0.0012), material=dark, name='needle')
    c = L / 2 - 0.004
    nd.location = (gx + c * math.sin(math.radians(a)), FY - 0.0062, gz + c * math.cos(math.radians(a)))
    nd.rotation_euler = (math.radians(90), math.radians(a), 0)
kit.cyl(0.004, 0.003, at=(gx, FY - 0.0068, gz), rot=(90, 0, 0), material=dark, verts=16, name='needle_hub')

# two round buttons and the shot timer to the right
for x in (0.068, 0.103):
    kit.cyl(0.0105, 0.004, at=(x, FY - 0.001, HZ0 + 0.068), rot=(90, 0, 0), material=chrome, verts=32, name='btn_ring')
    kit.cyl(0.0078, 0.009, at=(x, FY - 0.004, HZ0 + 0.068), rot=(90, 0, 0), material=cream, bevel=0.002, verts=28,
            name='button')
kit.box((0.075, 0.003, 0.022), at=(0.078, FY - 0.0005, HZ0 + 0.03), material=dark, bevel=0.001, name='timer_window')
t = kit.text('0:25', 0.016, 0.001, at=(0.087, FY - 0.0022, HZ0 + 0.029), material=led, name='timer_digits')
kit.box((0.01, 0.002, 0.0035), at=(0.053, FY - 0.0022, HZ0 + 0.03), material=led, bevel=0.001, name='timer_pill')

# ---------- group head, portafilter ----------
gh = frustum(0.075, 0.07, 0.095, 0.09, HZ0 - 0.034, HZ0 + 0.01, steel, 0.008, 'group_housing')
gh.location = (GX, GY + 0.005, 0)
# padlock mark on the housing front (drawn small under the head)
kit.box((0.008, 0.002, 0.007), at=(GX - 0.03, GY - 0.036, HZ0 - 0.012), material=dark, bevel=0.0008, name='lock_body')
kit.torus(0.0028, 0.0008, at=(GX - 0.03, GY - 0.036, HZ0 - 0.0075), rot=(90, 0, 0), material=dark, major=16, minor=6,
          name='lock_shackle')
kit.lathe([(0, -0.012), (0.03, -0.012), (0.034, -0.008), (0.034, 0.0), (0.0, 0.0)], at=(GX, GY, HZ0 - 0.034),
          material=chrome, steps=48, name='shower_ring')
PFZ = HZ0 - 0.046 - 0.016
pf = kit.lathe([(0, -0.022), (0.03, -0.022), (0.036, -0.016), (0.038, 0.0), (0.038, 0.012), (0.042, 0.014),
                (0.042, 0.018), (0.0, 0.018)], at=(GX, GY, PFZ), material=steel, steps=48, name='basket')
for sx in (-1, 1):
    kit.box((0.012, 0.012, 0.006), at=(GX + sx * 0.046, GY, PFZ + 0.015), material=steel, bevel=0.002, name='ear')
for sx in (-1, 1):
    kit.cyl(0.0055, 0.014, at=(GX + sx * 0.011, GY, PFZ - 0.028), material=steel, verts=16, r2=0.004, name='spout')
kit.box((0.03, 0.02, 0.012), at=(GX, GY, PFZ - 0.024), material=steel, bevel=0.004, name='spout_block')
# handle: steel neck, collar, thick walnut grip with a steel end cap
HYb = GY - 0.04
kit.cyl(0.011, 0.03, at=(GX, HYb + 0.006, PFZ + 0.004), rot=(90, 0, 0), material=steel, verts=24, name='neck')
kit.cyl(0.02, 0.012, at=(GX, HYb - 0.012, PFZ + 0.004), rot=(90, 0, 0), material=chrome, bevel=0.003, verts=32,
        name='collar')
kit.lathe([(0, 0), (0.019, 0), (0.021, 0.01), (0.022, 0.06), (0.0215, 0.13), (0.019, 0.142), (0, 0.142)],
          at=(GX, HYb - 0.018, PFZ + 0.004), rot=(90, 0, 0), material=walnut, steps=32, name='grip')
kit.cyl(0.0165, 0.006, at=(GX, HYb - 0.162, PFZ + 0.004), rot=(90, 0, 0), material=chrome, bevel=0.002, verts=32,
        name='end_cap')

# ---------- side: IYA badge (both sides), steam knob and wand on the right ----------
for sx in (1, -1):
    SX = sx * HW / 2
    kit.box((0.004, 0.13, 0.068), at=(SX, HY0 + 0.1, HZ0 + 0.09), material=cream, bevel=0.0018, name='badge')
    kit.box((0.003, 0.136, 0.074), at=(SX - sx * 0.0005, HY0 + 0.1, HZ0 + 0.09), material=chrome, bevel=0.001,
            name='badge_frame')
    kit.text('IYA', 0.058, 0.003, at=(SX + sx * 0.002, HY0 + 0.1, HZ0 + 0.09), rot=(90, 0, 90 * sx),
             material=enamel, name='badge_text')
# steam knob (right side, low and toward the back) with its pointer tab
KX, KY, KZ, KR = HW / 2, HY0 + 0.19, HZ0 + 0.05, 0.02
kit.cyl(KR - 0.003, 0.008, at=(KX + 0.004, KY, KZ), rot=(0, 90, 0), material=chrome, verts=32, name='knob_boss')
kit.lathe([(0, 0), (KR, 0), (KR + 0.002, 0.006), (KR + 0.002, 0.02), (KR - 0.001, 0.026), (0, 0.027)],
          at=(KX + 0.008, KY, KZ), rot=(0, 90, 0), material=walnut, steps=36, name='steam_knob')
for i in range(12):
    a = i * math.tau / 12
    kit.box((0.014, 0.004, 0.004), at=(KX + 0.021, KY + (KR + 0.0015) * math.cos(a), KZ + (KR + 0.0015) * math.sin(a)),
            rot=(math.degrees(a), 0, 0), material=walnut, name='knurl')
kit.box((0.01, 0.03, 0.007), at=(KX + 0.013, KY - 0.026, KZ), material=chrome, bevel=0.0025, name='knob_tab')
# steam wand: ball joint under the head at the front right, angled out to the right, then level with a grip
J = Vector((HW / 2 - 0.03, HY0 + 0.03, HZ0 - 0.004))
kit.sphere(0.013, at=tuple(J), material=chrome, segs=24, rings=12, name='wand_joint')
kit.cyl(0.016, 0.01, at=(J.x, J.y, HZ0 + 0.001), material=chrome, verts=24, bevel=0.002, name='wand_mount')
P1 = J + Vector((0.075, 0, -0.035))
P2 = P1 + Vector((0.11, 0, 0))
kit.tube([tuple(J), tuple(J + (P1 - J) * 0.5), tuple(P1 - Vector((0.012, 0, -0.004))), tuple(P1 + Vector((0.012, 0, 0))),
          tuple(P2)], 0.0068, material=chrome, bevel_res=24, name='wand')
kit.cyl(0.009, 0.014, at=tuple(P1 + Vector((0.004, 0, 0))), rot=(0, 90, 0), material=chrome, verts=24, bevel=0.002,
        name='wand_collar')
kit.lathe([(0, 0), (0.0098, 0), (0.0108, 0.006), (0.0108, 0.06), (0.0094, 0.066), (0, 0.067)],
          at=tuple(P2 - Vector((0.062, 0, 0))), rot=(0, 90, 0), material=rubber, steps=24, name='wand_grip')

# ---------- back: slide-out water tank under the head ----------
tank_h = HZ0 - TRAY - 0.012
kit.box((0.22, 0.17 - TK0, tank_h), at=(0, (TK0 + 0.17) / 2, TRAY + tank_h / 2), material=glass, bevel=0.01, segments=3,
        name='tank')
kit.box((0.206, 0.17 - TK0 - 0.012, tank_h * 0.55), at=(0, (TK0 + 0.17) / 2, TRAY + 0.006 + tank_h * 0.275),
        material=water, bevel=0.006, name='tank_water')
kit.box((0.22, 0.17 - TK0, 0.016), at=(0, (TK0 + 0.17) / 2, TRAY + tank_h - 0.008 + 0.0005), material=base_m,
        bevel=0.005, name='tank_lid')
kit.box((0.09, 0.012, 0.016), at=(0, 0.17 + 0.004, TRAY + tank_h - 0.03), material=base_m, bevel=0.005, name='tank_grip')

# ---------- glass latte cup ----------
CZ = TRAY + 0.004
S = 1.12
cup_prof = [(0, 0), (0.026, 0), (0.03, 0.004), (0.045, 0.03), (0.053, 0.058), (0.056, 0.07), (0.052, 0.07),
            (0.049, 0.058), (0.041, 0.031), (0.028, 0.009), (0, 0.009)]
kit.lathe([(r * S, z * S) for r, z in cup_prof], at=(GX, GY, CZ), material=glass, steps=56, name='cup')
# coffee with a latte swirl
n = 256
yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n * 2 - 1
rr = np.hypot(xx, yy); th = np.arctan2(yy, xx)
swirl = np.sin(th * 1 + rr * 15.0)
heart = (rr < 0.62) & (swirl > 0.15)
crema = np.ones((n, n, 3)) * np.array([0.36, 0.2, 0.1])
crema[rr < 0.8] = (0.62, 0.42, 0.25)
crema[heart] = (0.94, 0.88, 0.76)
crema[rr < 0.12] = (0.94, 0.88, 0.76)
coffee_top = kit.mat('#ffffff', rough=0.3, name='crema', image=save_tex('esp_crema', crema))
liq = kit.lathe([(r * S, z * S) for r, z in [(0, 0.009), (0.028, 0.009), (0.041, 0.031), (0.0478, 0.055), (0, 0.055)]], at=(GX, GY, CZ),
                material=kit.mat('#3a2213', rough=0.25, name='coffee'), steps=48, name='coffee')
cap = kit.cyl(0.0476 * S, 0.0015, at=(0, 0, 0), verts=48, name='crema')
cap.data.materials.clear(); cap.data.materials.append(coffee_top); uv_planar(cap, 0.0476 * S)
cap.location = (GX, GY, CZ + 0.055 * S + 0.0005)
kit.tube([(GX + 0.048 * S, GY, CZ + 0.054 * S), (GX + 0.072 * S, GY, CZ + 0.056 * S), (GX + 0.078 * S, GY, CZ + 0.036 * S),
          (GX + 0.062 * S, GY, CZ + 0.02 * S), (GX + 0.04 * S, GY, CZ + 0.022 * S)], 0.0045, material=glass, bevel_res=16,
         name='cup_handle')

kit.export('espresso-machine')
