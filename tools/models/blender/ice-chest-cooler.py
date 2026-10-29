"""Ice chest cooler - generic (no drawing in the folder yet).

A vintage steel-belted picnic cooler: enamelled blue-teal body and lid, stainless bands round the
base, the body rim and the lid, stainless corner caps with rivets, a chrome draw latch, swing bail
handles on both ends, two hinges at the back, a drain plug and rubber feet.
Replace with the student's design when the drawing turns up.
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


def rrect(w, d, r, n=8):
    """Rounded rectangle in XY (for plan-view extrusions)."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(w, d, r, z0, h, material, bevel=0.004, name='slab'):
    """Rounded-corner block in plan, from z0 up by h."""
    return kit.extrude(rrect(w, d, r), h, at=(0, 0, z0), material=material, bevel=bevel, segments=2, name=name)


paint = kit.mat('#3a7d9c', rough=0.32, metal=0.1, name='enamel_blue')
steel = kit.mat('#c4c8cc', rough=0.28, metal=0.85, name='stainless')
chrome = kit.mat('chrome', rough=0.18, metal=0.9, name='chrome')
rubber = kit.mat('rubber', rough=0.85, name='rubber')
grip = kit.mat('white', rough=0.4, name='grip_white')
dark = kit.mat('#1d2a30', rough=0.6, name='seam')

L, W, R = 0.6, 0.36, 0.035
Z0, ZB = 0.016, 0.338            # body bottom / top
ZL = 0.345                       # lid bottom

# ---------------------------------------------------------------- body and lid
slab(L, W, R, Z0, ZB - Z0, paint, bevel=0.006, name='body')
slab(L - 0.012, W - 0.012, R - 0.006, ZB - 0.004, 0.012, dark, bevel=0.0, name='lid_seam')
slab(L + 0.006, W + 0.006, R + 0.003, ZL, 0.05, paint, bevel=0.008, name='lid')
slab(L - 0.03, W - 0.03, R - 0.012, ZL + 0.048, 0.01, paint, bevel=0.006, name='lid_crown')
# a shallow pressed panel on the lid top
slab(L - 0.1, W - 0.1, 0.025, ZL + 0.055, 0.006, paint, bevel=0.003, name='lid_panel')

# stainless bands: base, body rim, lid edge
slab(L + 0.008, W + 0.008, R + 0.004, Z0 - 0.002, 0.045, steel, bevel=0.004, name='base_band')
slab(L + 0.008, W + 0.008, R + 0.004, ZB - 0.034, 0.034, steel, bevel=0.004, name='rim_band')
slab(L + 0.014, W + 0.014, R + 0.007, ZL - 0.002, 0.028, steel, bevel=0.004, name='lid_band')

# corner caps with rivets, top and bottom of each corner
for sx in (-1, 1):
    for sy in (-1, 1):
        cx, cy = sx * (L / 2 - R), sy * (W / 2 - R)
        for z0, h in ((Z0 - 0.004, 0.06), (ZL - 0.004, 0.034)):
            cap = kit.cyl(R + 0.008, h, at=(cx, cy, z0 + h / 2), material=steel, verts=40, bevel=0.003, name='corner_cap')
            # keep only the outer quarter
            cut = kit.box((2 * R + 0.04, 2 * R + 0.04, h + 0.02), at=(cx - sx * (R + 0.02), cy, z0 + h / 2), name='cut')
            kit.boolean(cap, cut)
            cut = kit.box((2 * R + 0.04, 2 * R + 0.04, h + 0.02), at=(cx, cy - sy * (R + 0.02), z0 + h / 2), name='cut')
            kit.boolean(cap, cut)
            p = Vector((cx + sx * (R + 0.008) * 0.707, cy + sy * (R + 0.008) * 0.707, z0 + h * 0.55))
            kit.sphere(0.0042, at=p, material=chrome, segs=12, rings=6, name='rivet')

# ---------------------------------------------------------------- draw latch on the front
yf = -W / 2 - 0.004
kit.box((0.07, 0.008, 0.03), at=(0, yf - 0.002, ZB - 0.03), material=chrome, bevel=0.002, name='latch_base')
kit.cyl(0.005, 0.07, at=(0, yf - 0.008, ZB - 0.016), rot=(0, 90, 0), material=chrome, verts=16, name='latch_pin')
lever = kit.extrude([(-0.03, 0), (0.03, 0), (0.026, 0.052), (0.014, 0.062), (-0.014, 0.062), (-0.026, 0.052)], 0.006,
                    at=(0, yf - 0.009 - 0.004, ZB - 0.02), rot=(90, 0, 0), material=chrome, bevel=0.0015, name='latch_lever')
kit.box((0.05, 0.008, 0.008), at=(0, yf - 0.008, ZL + 0.024), material=chrome, bevel=0.002, name='latch_keeper')
for x in (-0.024, 0.024):
    kit.sphere(0.0032, at=(x, yf - 0.006, ZB - 0.038), material=steel, segs=10, rings=5, name='rivet')
# a blank maker's plate under the latch (no lettering)
kit.box((0.1, 0.004, 0.032), at=(0, -W / 2 - 0.001, 0.2), material=steel, bevel=0.002, name='plate')
for x in (-0.044, 0.044):
    kit.sphere(0.0026, at=(x, -W / 2 - 0.003, 0.2), material=chrome, segs=10, rings=5, name='rivet')

# ---------------------------------------------------------------- swing bail handles on both ends
for sx in (-1, 1):
    xe = sx * (L / 2 + 0.004)
    for sy in (-1, 1):
        kit.box((0.012, 0.032, 0.03), at=(xe + sx * 0.005, sy * 0.085, ZB - 0.05), material=chrome, bevel=0.003, name='handle_bracket')
        kit.cyl(0.006, 0.014, at=(xe + sx * 0.012, sy * 0.085, ZB - 0.05), rot=(0, 90, 0), material=chrome, verts=16, name='handle_boss')
    bail = [(xe + sx * 0.016, -0.085, ZB - 0.05), (xe + sx * 0.02, -0.085, ZB - 0.1), (xe + sx * 0.022, -0.075, ZB - 0.118),
            (xe + sx * 0.022, 0.075, ZB - 0.118), (xe + sx * 0.02, 0.085, ZB - 0.1), (xe + sx * 0.016, 0.085, ZB - 0.05)]
    ptube(bail, 0.0042, chrome, name='bail')
    g = kit.lathe([(0, -0.06), (0.011, -0.06), (0.013, -0.055), (0.013, 0.055), (0.011, 0.06), (0, 0.06)],
                  at=(0, 0, 0), material=grip, steps=24, name='grip')
    g.rotation_euler = (math.radians(90), 0, 0); g.location = (xe + sx * 0.022, 0, ZB - 0.118)

# ---------------------------------------------------------------- hinges at the back, drain plug, feet
yb = W / 2 + 0.004
for x in (-0.17, 0.17):
    kit.box((0.06, 0.006, 0.03), at=(x, yb + 0.003, ZB - 0.012), material=steel, bevel=0.0015, name='hinge_leaf')
    kit.box((0.06, 0.006, 0.026), at=(x, yb + 0.006, ZL + 0.014), material=steel, bevel=0.0015, name='hinge_leaf')
    kit.cyl(0.006, 0.064, at=(x, yb + 0.009, ZB + 0.004), rot=(0, 90, 0), material=chrome, verts=16, name='hinge_knuckle')
dp = Vector((L / 2 - 0.08, -W / 2 - 0.006, Z0 + 0.06))
kit.cyl(0.016, 0.01, at=dp, rot=(90, 0, 0), material=steel, verts=32, bevel=0.002, name='drain_boss')
kit.cyl(0.011, 0.012, at=dp + Vector((0, -0.008, 0)), rot=(90, 0, 0), material=chrome, verts=12, bevel=0.0015, name='drain_cap')
kit.box((0.016, 0.004, 0.003), at=dp + Vector((0, -0.0145, 0)), material=chrome, bevel=0.001, name='drain_tab')
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cyl(0.018, 0.016, at=(sx * (L / 2 - 0.05), sy * (W / 2 - 0.05), 0.008), material=rubber, verts=24, bevel=0.003, name='foot')

kit.export('ice-chest-cooler')
