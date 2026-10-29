"""Portable blender (Jewels Freedman). Kept to her drawing: a squat, barrel-sided body, a square-section carry handle
standing over the lid and crossing it on the diagonal, a short open drinking spout at the centre of the lid, and on
the front the three marks she drew - a vertical bar, a ringed button and a pointed U - which read together as a little
face. As controls: a charge-level light, the power button and a raised smile. Opaque, as drawn; colours are ours."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def resmooth(o, angle=35):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    return o


body_m = kit.mat('#86bcd6', rough=0.55, name='soft_touch')   # palette sky, soft-touch plastic
lid_m = kit.mat('cream', rough=0.42, name='lid')
dark = kit.mat('#2a2d31', rough=0.45, name='dark')
led = kit.mat('amber', rough=0.3, emit=3.5, name='led')
rubber = kit.mat('rubber', rough=0.8, name='rubber')

# ---------- body: barrel profile ----------
BODY = [(0.0, 0.003), (0.043, 0.003), (0.0485, 0.0055), (0.0528, 0.016), (0.0558, 0.036), (0.0565, 0.052),
        (0.0556, 0.07), (0.0532, 0.086), (0.0505, 0.0945), (0.0, 0.0945)]


def body_r(z):
    zs = [p[1] for p in BODY[1:-1]]; rs = [p[0] for p in BODY[1:-1]]
    return float(np.interp(z, zs, rs))


body = kit.lathe(BODY, material=body_m, steps=72, name='body')
apply_mods(body)
FY = lambda x, z: -math.sqrt(max(body_r(z) ** 2 - x * x, 0))

# charge-level light: the drawing's vertical bar, a pill slot with a glowing insert
LX, LZ = -0.021, 0.064
slot = kit.box((0.0085, 0.03, 0.028), at=(LX, FY(LX, LZ), LZ), bevel=0.004, segments=3)
kit.boolean(body, slot)
# power button: the ringed circle, in a shallow round pocket
BX, BZ = 0.019, 0.063
pocket = kit.cyl(0.0135, 0.03, at=(BX, FY(BX, BZ), BZ), rot=(90, 0, math.degrees(math.asin(BX / body_r(BZ)))), verts=40)
kit.boolean(body, pocket)
resmooth(body)
kit.box((0.006, 0.01, 0.0235), at=(LX, FY(LX, LZ) + 0.006, LZ), material=led, bevel=0.0028, segments=3, name='led_bar')
btn_axis = Vector((BX, FY(BX, BZ), 0)).normalized()
P = Vector((BX, FY(BX, BZ), BZ))
ring = kit.lathe([(0.0085, 0), (0.0128, 0), (0.0128, 0.0042), (0.0115, 0.0058), (0.0095, 0.0058), (0.0085, 0.004),
                  (0.0085, 0)], material=lid_m, steps=40, name='button_ring')
cap = kit.lathe([(0, 0), (0.0078, 0), (0.0078, 0.0045), (0.006, 0.0068), (0.003, 0.0076), (0, 0.0078)], material=body_m,
                steps=32, name='button')
for o in (ring, cap):
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(btn_axis)
    o.location = P - btn_axis * 0.004
kit.torus(0.0042, 0.0006, at=(0, 0, 0), material=led, major=24, minor=6, name='button_glow')
g = bpy.context.object
g.rotation_mode = 'QUATERNION'; g.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(btn_axis)
g.location = P + btn_axis * 0.0038

# the pointed U, as a raised cream smile following the barrel: straight strokes meeting in a point, as drawn
U = [(-0.0155, 0.045), (-0.0155, 0.029), (0.0, 0.0165), (0.0155, 0.029), (0.0155, 0.045)]
pts = []
for x, z in U:
    r = body_r(z)
    n = Vector((x, -math.sqrt(r * r - x * x), 0)).normalized()
    pts.append(Vector((x, -math.sqrt(r * r - x * x), z)) - n * 0.0011)
for p0, p1 in zip(pts, pts[1:]):
    mids = [p0 + (p1 - p0) * t for t in (0.0, 0.5, 1.0)]
    mids = [Vector((m.x, -math.sqrt(body_r(m.z) ** 2 - m.x * m.x) + 0.0011, m.z)) for m in mids]
    kit.tube([tuple(m) for m in mids], 0.0026, material=lid_m, bevel_res=4, name='smile')
for p in pts:
    kit.sphere(0.0026, at=tuple(p), material=lid_m, segs=12, rings=6, name='smile_joint')

# ---------- lid: cream cap with a seam, spout, and the handle ----------
kit.lathe([(0.0, 0.0935), (0.0503, 0.0935), (0.0508, 0.0965), (0.0496, 0.1015), (0.0465, 0.1055), (0.04, 0.1078),
           (0.0, 0.1085)], material=lid_m, steps=72, name='lid')
kit.torus(0.0505, 0.0011, at=(0, 0, 0.0945), material=dark, major=72, minor=6, name='lid_seam')
# open drinking spout at the centre
kit.lathe([(0.0, 0.107), (0.0125, 0.107), (0.0125, 0.1205), (0.0118, 0.1222), (0.0098, 0.1222), (0.0092, 0.1205),
           (0.0092, 0.112), (0.0, 0.112)], material=lid_m, steps=40, name='spout')
kit.cyl(0.0092, 0.002, at=(0, 0, 0.1125), material=dark, verts=32, name='spout_hole')
# carry handle: square-section inverted U, crossing the lid on the diagonal as drawn
HU, HT, HTH = 0.044, 0.17, 0.0105     # leg position, top of bar, bar thickness
handle = kit.extrude([(-HU - HTH / 2, 0.104), (-HU + HTH / 2, 0.104), (-HU + HTH / 2, HT - HTH),
                      (HU - HTH / 2, HT - HTH), (HU - HTH / 2, 0.104), (HU + HTH / 2, 0.104), (HU + HTH / 2, HT),
                      (-HU - HTH / 2, HT)], HTH, material=lid_m, bevel=0.0028, segments=3, name='handle')
handle.rotation_euler = (math.radians(90), 0, 0); handle.location = (0, HTH / 2, 0)
bpy.context.view_layer.update()
handle.matrix_world = Matrix.Rotation(math.radians(-37), 4, 'Z') @ handle.matrix_world
for s in (-1, 1):   # mounting bosses where the legs meet the lid
    b = kit.box((0.02, 0.018, 0.007), at=(s * HU, 0, 0.1065), material=lid_m, bevel=0.0028, segments=2, name='boss')
    b.matrix_world = Matrix.Rotation(math.radians(-37), 4, 'Z') @ b.matrix_world
    pin = kit.cyl(0.0032, 0.0135, at=(s * HU, 0, 0.1135), rot=(90, 0, 0), material=lid_m, verts=20, bevel=0.0008, name='pin')
    pin.matrix_world = Matrix.Rotation(math.radians(-37), 4, 'Z') @ pin.matrix_world

# ---------- back and bottom: charging port under a rubber flap, feet ring ----------
PZ = 0.03
r = body_r(PZ)
kit.box((0.022, 0.006, 0.014), at=(0, r - 0.0012, PZ), material=rubber, bevel=0.003, segments=2, name='port_flap')
kit.box((0.01, 0.002, 0.003), at=(0, r + 0.0018, PZ - 0.0035), material=dark, bevel=0.0008, name='flap_tab')
for i, x in enumerate((-0.012, -0.006, 0.0, 0.006, 0.012)):
    rz = body_r(0.072)
    kit.cyl(0.0018, 0.004, at=(x, math.sqrt(rz * rz - x * x) - 0.0012, 0.072), rot=(90, 0, 0), material=dark, verts=12,
            name='vent')
kit.lathe([(0.03, 0.0), (0.042, 0.0), (0.043, 0.0035), (0.03, 0.0035), (0.03, 0.0)], material=rubber, steps=60,
          name='foot_ring')

kit.export('portable-blender')
