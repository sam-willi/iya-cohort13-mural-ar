"""Smartphone tripod - Srinija Chukkapalli (Cohort 13).

Her drawing: a phone standing in portrait in a holder (a base tray with two upright side clamps),
on a square post that drops into a cube-shaped hub, with three round-ended rod legs splayed out.
The phone has a thick bezel round its screen and a pill-shaped earpiece near the top.
Line-only, so: black plastic holder and hub, aluminium post and legs, rubber feet, teal phone.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, math
from mathutils import Vector

kit.reset()


# ---------------------------------------------------------------- local helpers
def framed_check(obj_id, res=520):
    """kit.check_render frames at 3.2x the bounding radius with a 70 mm lens, which crops tall or long
    objects. Pad the bounds with a vertex-only (invisible) mesh first; the GLB is already written."""
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
    hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
    ctr, half = (lo + hi) / 2, (hi - lo) / 2
    k = max(half) / (0.8 * half.length) * 1.08
    if k > 1:
        me = bpy.data.meshes.new('frame_pad'); me.from_pydata([tuple(ctr - half * k), tuple(ctr + half * k)], [], [])
        bpy.context.collection.objects.link(bpy.data.objects.new('frame_pad', me))
    _kit_check(obj_id, res)


_kit_check = kit.check_render
kit.check_render = framed_check


def boolean(target, cutter, op='DIFFERENCE'):
    """Like kit.boolean, but cut faces take the cutter's material."""
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op; md.object = cutter
    md.solver = 'EXACT'; md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def rod(p0, p1, r, material, verts=20, name='rod'):
    a, b = Vector(p0), Vector(p1); d = b - a
    o = kit.cyl(r, d.length, at=(a + b) / 2, material=material, verts=verts, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def rbox_xz(w, h, r, n=6):
    """Rounded rectangle outline in the XZ plane (as 2D points)."""
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


black = kit.mat('black', rough=0.45, name='black_plastic')
rubber = kit.mat('rubber', rough=0.85, name='rubber')
alu = kit.mat('#b9bec4', rough=0.32, metal=0.85, name='aluminium')
phone_c = kit.mat('teal', rough=0.38, name='phone_teal')
glass = kit.mat('#1a232b', rough=0.06, name='screen_glass')
grille = kit.mat('steel', rough=0.35, metal=0.8, name='grille')
lensg = kit.mat('#0c0f12', rough=0.05, name='lens_glass')
ring = kit.mat('chrome', rough=0.2, metal=0.85, name='lens_ring')
flash = kit.mat('cream', rough=0.3, emit=0.15, name='flash')

# ---------------------------------------------------------------- legs, hub, post
HUB_Z0, HUB = 0.098, 0.046
kit.box((HUB, HUB, HUB - 0.004), at=(0, 0, HUB_Z0 + HUB / 2), material=black, bevel=0.005, segments=3, name='hub')
kit.cyl(0.019, 0.012, at=(0, 0, HUB_Z0 - 0.004), material=black, verts=32, bevel=0.002, name='leg_mount')
# leg-lock knob on the hub's side
kit.cyl(0.0035, 0.012, at=(HUB / 2 + 0.005, 0, HUB_Z0 + 0.026), rot=(0, 90, 0), material=alu, verts=12, name='knob_stem')
kn = kit.cyl(0.011, 0.008, at=(HUB / 2 + 0.013, 0, HUB_Z0 + 0.026), rot=(0, 90, 0), material=black, verts=12, bevel=0.002, name='knob')
for k in range(12):
    a = math.tau * k / 12
    kit.box((0.008, 0.0025, 0.0025), at=(HUB / 2 + 0.013, 0.011 * math.cos(a), HUB_Z0 + 0.026 + 0.011 * math.sin(a)),
            rot=(math.degrees(a), 0, 0), material=black, name='knurl')

reach, drop = 0.116, HUB_Z0 - 0.012
for k in range(3):
    a = math.radians(-90 + 120 * k)               # first leg points to the front (-Y)
    d = Vector((math.cos(a), math.sin(a), 0))
    top = Vector((0, 0, HUB_Z0 - 0.004)) + d * 0.012
    foot = Vector((0, 0, 0.0)) + d * reach + Vector((0, 0, 0.012))
    rod(top, foot, 0.0055, alu, name='leg')
    # hinge knuckle where the leg pivots
    kit.cyl(0.0075, 0.012, at=top, rot=(90, 0, math.degrees(a)), material=black, verts=16, bevel=0.0015, name='hinge')
    # round rubber foot
    dirv = (foot - top).normalized()
    kit.sphere(0.0085, at=foot + dirv * 0.002, scale=(1, 1, 1), material=rubber, segs=20, rings=10, name='foot')
for o in [o for o in bpy.context.scene.objects if o.name.startswith('foot')]:
    o.location.z = 0.0085

POST_Z0, POST_Z1 = HUB_Z0 + HUB - 0.004, 0.207
kit.box((0.021, 0.021, POST_Z1 - POST_Z0 + 0.004), at=(0, 0, (POST_Z0 + POST_Z1) / 2), material=alu, bevel=0.0025, name='post')
kit.box((0.026, 0.026, 0.008), at=(0, 0, POST_Z0 + 0.004), material=black, bevel=0.002, name='post_collar')

# ---------------------------------------------------------------- holder: tray and two side clamps
TRAY_Z0, TRAY_H = POST_Z1, 0.019
PW, PT, PH = 0.074, 0.0088, 0.152           # phone width, thickness, height
tray = kit.box((0.104, 0.03, TRAY_H), at=(0, 0, TRAY_Z0 + TRAY_H / 2), material=black, bevel=0.003, segments=2, name='tray')
cut = kit.box((PW + 0.002, PT + 0.002, 0.02), at=(0, 0, TRAY_Z0 + TRAY_H + 0.006), name='cut')
boolean(tray, cut)
CL_H = 0.074
for sx in (-1, 1):
    x = sx * (PW / 2 + 0.0075)
    cl = kit.extrude([(-0.0065, 0), (0.0065, 0), (0.0065, CL_H - (0.008 if sx > 0 else 0)), (-0.0065, CL_H - (0 if sx > 0 else 0.008))],
                     0.022, at=(x, 0.011, TRAY_Z0 + TRAY_H - 0.004), rot=(90, 0, 0), material=black, bevel=0.0018, name='clamp')
    # rubber pad on the clamp's inner face
    kit.box((0.0016, 0.016, CL_H - 0.02), at=(sx * (PW / 2 + 0.0003), 0, TRAY_Z0 + TRAY_H + CL_H / 2 - 0.006),
            material=rubber, bevel=0.0005, name='pad')
# spring housing and tilt knob on the back
kit.box((0.05, 0.012, 0.014), at=(0, 0.019, TRAY_Z0 + TRAY_H / 2), material=black, bevel=0.003, name='spring_box')
kit.cyl(0.009, 0.01, at=(0, 0.014, POST_Z1 - 0.012), rot=(90, 0, 0), material=black, verts=24, bevel=0.0015, name='tilt_boss')
kit.cyl(0.0065, 0.008, at=(0, 0.022, POST_Z1 - 0.012), rot=(90, 0, 0), material=alu, verts=24, bevel=0.001, name='tilt_knob')

# ---------------------------------------------------------------- the phone
PZ0 = TRAY_Z0 + TRAY_H - 0.004 + 0.0002
pz = PZ0 + PH / 2
ph = kit.extrude(rbox_xz(PW, PH, 0.009), PT, at=(0, PT / 2, pz), rot=(90, 0, 0), material=phone_c, bevel=0.0025, segments=3, name='phone')
cut = kit.extrude(rbox_xz(PW - 0.009, PH - 0.016, 0.004), 0.004, at=(0, -PT / 2 + 0.0009, pz), rot=(90, 0, 0), material=glass, name='cut')
boolean(ph, cut)
# earpiece: a pill near the top of the screen, as she drew it
kit.extrude(rbox_xz(0.014, 0.0026, 0.0012, 4), 0.0012, at=(0, -PT / 2 + 0.0011, pz + PH / 2 - 0.0135), rot=(90, 0, 0),
            material=grille, name='earpiece')
kit.cyl(0.0014, 0.001, at=(0.012, -PT / 2 + 0.0002, pz + PH / 2 - 0.0135), rot=(90, 0, 0), material=lensg, verts=12, name='selfie_cam')
# side buttons above the clamps
for z, L in ((0.035, 0.012), (0.02, 0.012)):
    kit.box((0.0016, 0.0035, L), at=(-PW / 2 - 0.0006, 0, pz + z), material=phone_c, bevel=0.0007, name='vol_btn')
kit.box((0.0016, 0.0035, 0.018), at=(PW / 2 + 0.0006, 0, pz + 0.028), material=phone_c, bevel=0.0007, name='power_btn')
# camera bump on the back (top left as seen from behind)
bx, bz = PW / 2 - 0.016, pz + PH / 2 - 0.018
kit.extrude(rbox_xz(0.026, 0.026, 0.006), 0.0018, at=(bx, PT / 2 + 0.0018, bz), rot=(90, 0, 0), material=phone_c, bevel=0.0008, name='cam_bump')
for dz in (0.0062, -0.0062):
    kit.cyl(0.0048, 0.0012, at=(bx - 0.004, PT / 2 + 0.0024, bz + dz), rot=(90, 0, 0), material=ring, verts=24, name='lens_ring')
    kit.cyl(0.0036, 0.0008, at=(bx - 0.004, PT / 2 + 0.0029, bz + dz), rot=(90, 0, 0), material=lensg, verts=24, name='lens')
kit.cyl(0.0022, 0.0008, at=(bx + 0.0065, PT / 2 + 0.0024, bz + 0.0062), rot=(90, 0, 0), material=flash, verts=16, name='flash')

kit.export('tripod')
