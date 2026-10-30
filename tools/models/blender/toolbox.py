"""Toolbox - generic (no drawing in the folder yet).

A classic red steel hip-roof toolbox: pressed-steel body with a rolled rim, a hip-roof lid with a
lip and stamped stiffening beads, a folding carry handle with a black grip, two chrome draw latches,
a padlock hasp, a piano hinge along the back and rubber feet.
Replace with the student's design when the drawing turns up.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
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


def ptube(points, r, material=None, res=2, name='tube'):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*c, 1)
    cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    return kit.finish(bpy.context.object, material)


def frustum(w0, d0, w1, d1, z0, h, material, bevel=0.003, name='roof'):
    """A box whose top (w1 x d1) is smaller than its base (w0 x d0): the hip roof."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    b = [bm.verts.new((sx * w0 / 2, sy * d0 / 2, z0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    t = [bm.verts.new((sx * w1 / 2, sy * d1 / 2, z0 + h)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(b[::-1]); bm.faces.new(t)
    for i in range(4):
        bm.faces.new((b[i], b[(i + 1) % 4], t[(i + 1) % 4], t[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, bevel=bevel, segments=3)


paint = kit.mat('red', rough=0.36, metal=0.15, name='red_paint')
chrome = kit.mat('chrome', rough=0.18, metal=0.9, name='chrome')
steel = kit.mat('steel', rough=0.32, metal=0.85, name='steel')
black = kit.mat('black', rough=0.5, name='grip_black')
rubber = kit.mat('rubber', rough=0.85, name='rubber')
dark = kit.mat('#2a0f0c', rough=0.7, name='gap')

L, W = 0.5, 0.22
ZB = 0.168            # top of the body
ZL = 0.172            # bottom of the lid

# ---------------------------------------------------------------- body: pressed steel with a rolled rim and a foot bead
kit.box((L, W, ZB - 0.008), at=(0, 0, 0.008 + (ZB - 0.008) / 2), material=paint, bevel=0.006, segments=3, name='body')
kit.box((L + 0.006, W + 0.006, 0.012), at=(0, 0, ZB - 0.008), material=paint, bevel=0.005, segments=3, name='rim_roll')
kit.box((L + 0.004, W + 0.004, 0.012), at=(0, 0, 0.014), material=paint, bevel=0.005, segments=3, name='foot_bead')
kit.box((L - 0.01, W - 0.01, 0.006), at=(0, 0, ZB + 0.001), material=dark, name='gap')
# stamped stiffening panel on the front and back
for sy in (-1, 1):
    kit.box((L - 0.07, 0.004, 0.075), at=(0, sy * (W / 2 + 0.0005), 0.085), material=paint, bevel=0.0018, name='front_panel')
# stamped dimples on the ends
for sx in (-1, 1):
    for y in (-0.05, 0.05):
        kit.sphere(0.014, at=(sx * (L / 2 - 0.003), y, 0.09), scale=(0.35, 1, 1), material=paint, segs=20, rings=10, name='dimple')

# ---------------------------------------------------------------- hip-roof lid with a lip and beads along the top
kit.box((L + 0.01, W + 0.01, 0.016), at=(0, 0, ZL + 0.008), material=paint, bevel=0.005, segments=3, name='lid_lip')
frustum(L + 0.002, W + 0.002, L - 0.1, W - 0.1, ZL + 0.012, 0.06, paint, bevel=0.006, name='lid_roof')
ZT = ZL + 0.072
for y in (-0.03, 0.03):
    kit.box((L - 0.16, 0.012, 0.006), at=(0, y, ZT + 0.001), material=paint, bevel=0.003, name='lid_bead')

# ---------------------------------------------------------------- folding carry handle on top
for sx in (-1, 1):
    x = sx * 0.12
    kit.box((0.028, 0.03, 0.012), at=(x, 0, ZT + 0.004), material=steel, bevel=0.003, name='handle_bracket')
    kit.cyl(0.006, 0.034, at=(x, 0, ZT + 0.012), rot=(0, 90, 0), material=chrome, verts=16, name='pivot')
bail = [(-0.12, 0, ZT + 0.012), (-0.12, 0, ZT + 0.04), (-0.112, 0, ZT + 0.058), (-0.095, 0, ZT + 0.064),
        (0.095, 0, ZT + 0.064), (0.112, 0, ZT + 0.058), (0.12, 0, ZT + 0.04), (0.12, 0, ZT + 0.012)]
ptube(bail, 0.0055, chrome, name='bail')
g = kit.lathe([(0, -0.07), (0.011, -0.07), (0.014, -0.066)] +
              [(0.014 - 0.0015 * (k % 2), -0.06 + k * 0.01) for k in range(13)] +
              [(0.014, 0.066), (0.011, 0.07), (0, 0.07)], material=black, steps=24, name='grip')
g.rotation_euler = (0, math.radians(90), 0); g.location = (0, 0, ZT + 0.064)

# ---------------------------------------------------------------- draw latches, hasp, hinge, feet
yf = -W / 2 - 0.004
for x in (-0.17, 0.17):
    kit.box((0.05, 0.006, 0.028), at=(x, yf, ZB - 0.03), material=chrome, bevel=0.002, name='latch_base')
    kit.cyl(0.0045, 0.05, at=(x, yf - 0.004, ZB - 0.018), rot=(0, 90, 0), material=chrome, verts=12, name='latch_pin')
    lever = kit.extrude([(-0.022, 0), (0.022, 0), (0.018, 0.04), (0.008, 0.046), (-0.008, 0.046), (-0.018, 0.04)], 0.005,
                        at=(x, yf - 0.005, ZB - 0.022), rot=(90, 0, 0), material=chrome, bevel=0.0012, name='latch_lever')
    kit.box((0.034, 0.006, 0.007), at=(x, yf - 0.002, ZL + 0.018), material=chrome, bevel=0.0015, name='latch_keeper')
# padlock hasp in the middle
kit.box((0.028, 0.006, 0.05), at=(0, yf - 0.002, ZB - 0.008), material=steel, bevel=0.002, name='hasp_plate')
hasp = kit.torus(0.009, 0.0028, at=(0, yf - 0.011, ZB - 0.02), rot=(0, 0, 0), material=chrome, major=24, minor=8, name='hasp_loop')
kit.box((0.006, 0.012, 0.012), at=(0, yf - 0.006, ZB - 0.02), material=steel, bevel=0.0015, name='hasp_staple')
# piano hinge along the back
yb = W / 2 + 0.004
kit.cyl(0.0045, L - 0.06, at=(0, yb + 0.002, ZL + 0.002), rot=(0, 90, 0), material=steel, verts=16, name='hinge_barrel')
for k in range(12):
    x = -(L - 0.06) / 2 + (k + 0.5) * (L - 0.06) / 12
    kit.cyl(0.0052, 0.003, at=(x, yb + 0.002, ZL + 0.002), rot=(0, 90, 0), material=steel, verts=16, name='hinge_knuckle')
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cyl(0.012, 0.008, at=(sx * (L / 2 - 0.035), sy * (W / 2 - 0.03), 0.004), material=rubber, verts=20, bevel=0.002, name='foot')

kit.export('toolbox')
