"""Electric toothbrush - George Shannon (Cohort 13).

His drawing: a straight cylindrical handle on a thin base ring, an oval button ringed by a bezel on
the front, a seam where the brush head clicks on, a cone tapering into a slim neck, and an oval head
packed with black bristles. His marker shading reads as shadow on a white body, so the body is white;
the bristles stay black as he drew them. The back gets a rubber grip and the base a charging dimple.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, math, random
from mathutils import Vector

kit.reset()
random.seed(7)


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


def oval(w, h, n=40):
    return [(w / 2 * math.cos(math.tau * k / n), h / 2 * math.sin(math.tau * k / n)) for k in range(n)]


white = kit.mat('#f1f1ee', rough=0.3, name='body_white')
head_white = kit.mat('#ecedea', rough=0.4, name='head_white')
bristle = kit.mat('#141414', rough=0.7, name='bristles')
chrome = kit.mat('chrome', rough=0.2, metal=0.85, name='chrome')
button = kit.mat('sky', rough=0.45, name='button_sky')
grip = kit.mat('#c9d6de', rough=0.8, name='grip_rubber')
base_m = kit.mat('steel', rough=0.3, metal=0.85, name='base_ring')
led = kit.mat('#7fd0ff', rough=0.3, emit=0.8, name='led')
dark = kit.mat('#5d6166', rough=0.5, name='seam_dark')

R = 0.0135                 # handle radius
H = 0.152                  # handle height (to the head seam)

# ---------------------------------------------------------------- handle: base ring, straight body, seam
kit.lathe([(0, 0.0), (R - 0.0015, 0.0), (R - 0.0002, 0.0012), (R + 0.0002, 0.003), (R + 0.0002, 0.0048),
           (R - 0.0006, 0.0052), (0, 0.0052)], material=base_m, steps=64, name='base_ring')
handle = kit.lathe([(0, 0.005), (R - 0.0004, 0.005), (R, 0.0065), (R, H - 0.0012), (R - 0.0006, H), (0, H)],
                   material=white, steps=72, name='handle')
# charging dimple under the base
dimple = kit.cyl(0.0055, 0.006, at=(0, 0, 0.0), material=dark, verts=32, name='cut')
base = bpy.data.objects['base_ring']
boolean(base, dimple)

# oval button with a raised bezel ring (the double outline in his drawing)
BZ = 0.118
cut = kit.extrude(oval(0.0125, 0.026), 0.02, at=(0, 0.0, BZ), rot=(90, 0, 0), material=dark, name='cut')
inner = kit.cyl(R - 0.0012, 0.2, at=(0, 0, 0.1), verts=72, name='inner')
boolean(cut, inner)
boolean(handle, cut)
kit.finish(handle, None, bevel=0.0004, segments=2)
btn = kit.extrude(oval(0.0098, 0.0232), 0.02, at=(0, 0.0, BZ), rot=(90, 0, 0), material=button, name='button')
outer = kit.cyl(R + 0.0006, 0.2, at=(0, 0, 0.1), verts=72, name='outer')
boolean(btn, outer, op='INTERSECT')
kit.finish(btn, None, bevel=0.0006, segments=2)
ring_pts = []
for x, z in oval(0.0114, 0.0248, 48):
    a = x / R
    ring_pts.append((R * math.sin(a) * 1.0 + 0.0 * x, -R * math.cos(a) - 0.0003, BZ + z))
cu = bpy.data.curves.new('bezel', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(ring_pts) - 1)
for p, c in zip(sp.points, ring_pts):
    p.co = (*c, 1)
sp.use_cyclic_u = True; cu.bevel_depth = 0.0009; cu.bevel_resolution = 1
ob = bpy.data.objects.new('bezel', cu); bpy.context.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.convert(target='MESH'); kit.finish(bpy.context.object, chrome)
# a small charge light under the button
kit.cyl(0.0011, 0.002, at=(0, -R + 0.0004, BZ - 0.024), rot=(90, 0, 0), material=led, verts=12, name='led')

# rubber grip on the back
cut = kit.extrude(oval(0.011, 0.07), 0.02, at=(0, 0.02, 0.07), rot=(90, 0, 0), material=grip, name='grip')
boolean(cut, kit.cyl(R + 0.0007, 0.2, at=(0, 0, 0.1), verts=72, name='outer'), op='INTERSECT')
kit.finish(cut, None, bevel=0.0006)
for k in range(6):
    z = 0.047 + k * 0.009
    kit.box((0.008, 0.0012, 0.0016), at=(0, R + 0.0009, z), material=grip, bevel=0.0005, name='grip_rib')

# ---------------------------------------------------------------- brush head: seam, cone, neck, oval head
kit.lathe([(0, H - 0.001), (R - 0.0012, H - 0.001), (R - 0.0012, H + 0.0004), (0, H + 0.0004)], material=dark, steps=72, name='seam')
kit.lathe([(0, H + 0.0004), (R - 0.0006, H + 0.0004), (R, H + 0.002), (R - 0.0006, H + 0.008), (R - 0.0026, H + 0.02),
           (0.008, H + 0.031), (0.006, H + 0.04), (0.0053, H + 0.05), (0.0051, H + 0.066), (0.0052, H + 0.072), (0, H + 0.074)],
          material=head_white, steps=56, name='brush_cone')
HZ = H + 0.081
head = kit.sphere(1.0, at=(0, 0.0012, HZ), scale=(0.0079, 0.0043, 0.0145), material=head_white, segs=40, rings=20, name='head')
# a little back hump where the neck meets the head
kit.sphere(1.0, at=(0, 0.0018, HZ - 0.012), scale=(0.005, 0.0038, 0.008), material=head_white, segs=24, rings=12, name='neck_join')

# bristles: a dense oval field of black tufts (hex-packed), slightly uneven like his hatching
TR = 0.00155
for row in range(-4, 5):
    z = HZ + row * TR * 1.75
    half = 0.0068 * math.sqrt(max(0.0, 1 - ((z - HZ) / 0.0138) ** 2))
    x = -half + (TR if row % 2 else TR * 1.9)
    while x <= half - TR * 0.6:
        L = 0.0092 + random.uniform(-0.0007, 0.0007) - 0.0008 * (abs(row) / 4) ** 2
        kit.cyl(TR, L, at=(x, -L / 2, z), rot=(90, 0, 0), material=bristle, verts=8, name='tuft')
        x += TR * 2.0
kit.export('toothbrush')
