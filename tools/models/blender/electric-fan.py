"""Electric fan - generic (no drawing in the folder yet).

A 1950s-style desk fan to sit in the mural's workshop: teal enamel base, stem and motor housing,
four pitched brass blades, a chrome wire cage (domed front guard with a brass centre badge, rear
guard, clamp ring), a speed knob on the base, a tilt knob at the pivot and an oscillation knob on
top of the motor. Replace with the student's design when the drawing turns up.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, math
from mathutils import Vector, Matrix

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


def ptube(points, r, material=None, res=1, closed=False, name='wire'):
    """Round tube through 3D points with straight segments (res 1 = 6 sides, res 2 = 8)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*c, 1)
    sp.use_cyclic_u = closed
    cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = not closed
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    return kit.finish(bpy.context.object, material)


enamel = kit.mat('teal', rough=0.35, name='teal_enamel')
brass = kit.mat('brass', rough=0.28, metal=0.9, name='brass')
chrome = kit.mat('chrome', rough=0.22, metal=0.85, name='chrome')
black = kit.mat('black', rough=0.45, name='bakelite')
cream = kit.mat('cream', rough=0.4, name='cream')
rubber = kit.mat('rubber', rough=0.85, name='rubber')

# ---------------------------------------------------------------- base and stem (world space)
kit.lathe([(0, 0.0), (0.112, 0.0), (0.116, 0.004), (0.116, 0.012), (0.108, 0.022), (0.09, 0.036), (0.066, 0.048),
           (0.042, 0.056), (0.03, 0.06), (0, 0.06)], material=enamel, steps=72, name='base')
kit.torus(0.114, 0.0028, at=(0, 0, 0.012), material=chrome, major=72, minor=6, name='base_trim')
kit.lathe([(0, -0.0), (0.1, 0.0), (0.1, 0.003), (0, 0.003)], at=(0, 0, -0.0001), material=rubber, steps=48, name='foot_ring')
# speed knob on the front slope of the base, with a little dial plate
n = Vector((0, -math.sin(math.radians(27)), math.cos(math.radians(27))))
kp = Vector((0, -0.079, 0.0415))
kit.cyl(0.024, 0.003, at=kp + n * 0.0008, rot=(27, 0, 0), material=cream, verts=40, bevel=0.0008, name='dial_plate')
kit.cyl(0.0135, 0.015, at=kp + n * 0.009, rot=(27, 0, 0), material=black, verts=24, bevel=0.002, name='speed_knob')
kit.box((0.0045, 0.026, 0.006), at=kp + n * 0.0175, rot=(27, 0, 0), material=black, bevel=0.0015, name='knob_grip')
for k in range(4):          # speed tick marks on the plate
    a = math.radians(200 + k * 47)
    d = Matrix.Rotation(math.radians(27), 3, 'X') @ Vector((0.0195 * math.cos(a), 0.0195 * math.sin(a), 0.0024))
    kit.sphere(0.0017, at=kp + d, material=black, segs=8, rings=4, name='tick')
# stem with a collar at each end
kit.lathe([(0, 0.055), (0.03, 0.055), (0.03, 0.062), (0.019, 0.07), (0.016, 0.08), (0.016, 0.215), (0.02, 0.222),
           (0.02, 0.232), (0, 0.232)], material=enamel, steps=40, name='stem')
kit.torus(0.0165, 0.0018, at=(0, 0, 0.215), material=chrome, major=32, minor=6, name='stem_ring')

# ---------------------------------------------------------------- the head, built along +Z (forward) then swung to face -Y
HEAD = Vector((0, -0.1, 0.29))
head = []


def H(o):
    head.append(o); return o


CR = 0.152                       # cage radius
DF, DR = 0.062, 0.078            # front and rear guard depth


def zf(rho):
    return DF * max(0.0, 1 - (rho / CR) ** 2) ** 0.7


def zr(rho):
    return -DR * max(0.0, 1 - (rho / CR) ** 2) ** 0.7


# clamp ring and guards
H(kit.torus(CR, 0.0045, at=(0, 0, 0), material=chrome, major=96, minor=8, name='cage_rim'))
for rho in (0.128, 0.104, 0.08, 0.056):
    H(kit.torus(rho, 0.0019, at=(0, 0, zf(rho)), material=chrome, major=72, minor=6, name='front_ring'))
for rho in (0.125, 0.095, 0.066):
    H(kit.torus(rho, 0.0019, at=(0, 0, zr(rho)), material=chrome, major=72, minor=6, name='rear_ring'))
for k in range(28):
    a = math.tau * k / 28
    c, s = math.cos(a), math.sin(a)
    H(ptube([(rho * c, rho * s, zf(rho)) for rho in [0.03 + (CR - 0.03) * i / 10 for i in range(11)]], 0.0014, chrome, name='front_wire'))
    H(ptube([(rho * c, rho * s, zr(rho)) for rho in [0.05 + (CR - 0.05) * i / 9 for i in range(10)]], 0.0014, chrome, name='rear_wire'))
# brass centre badge on the front guard
H(kit.lathe([(0, zf(0.03) - 0.004), (0.034, zf(0.03) - 0.004), (0.035, zf(0.03)), (0.03, zf(0.03) + 0.004), (0.012, zf(0.03) + 0.007),
             (0, zf(0.03) + 0.0075)], material=brass, steps=48, name='badge'))
H(kit.torus(0.022, 0.0016, at=(0, 0, zf(0.03) + 0.0055), material=enamel, major=40, minor=6, name='badge_ring'))
# rim clips holding the two guards together
for k in range(6):
    a = math.tau * (k + 0.5) / 6
    H(kit.box((0.012, 0.008, 0.016), at=(CR * math.cos(a), CR * math.sin(a), 0), rot=(0, 0, math.degrees(a)),
              material=chrome, bevel=0.002, name='rim_clip'))

# blades: four pitched, cupped brass paddles on a domed spinner
HUBZ = -0.004
blade = [(0.022, -0.02), (0.06, -0.032), (0.1, -0.044), (0.118, -0.04), (0.126, -0.025), (0.128, 0.0), (0.124, 0.024),
         (0.112, 0.038), (0.085, 0.042), (0.05, 0.03), (0.022, 0.018)]
for k in range(4):
    b = kit.extrude(blade, 0.0022, at=(0, 0, 0), material=brass, bevel=0.0008, segments=1, name='blade')
    for v in b.data.vertices:          # cup the blade across its width
        v.co.z += 0.006 * (v.co.y / 0.045) ** 2 * min(1.0, v.co.x / 0.06)
    b.data.update()
    b.matrix_world = Matrix.Translation((0, 0, HUBZ)) @ Matrix.Rotation(math.tau * k / 4, 4, 'Z') @ Matrix.Rotation(math.radians(24), 4, 'X')
    H(b)
H(kit.lathe([(0, HUBZ - 0.012), (0.03, HUBZ - 0.012), (0.03, HUBZ + 0.004), (0.024, HUBZ + 0.012), (0.012, HUBZ + 0.018),
             (0, HUBZ + 0.02)], material=brass, steps=40, name='spinner'))
H(kit.cyl(0.006, 0.05, at=(0, 0, HUBZ - 0.03), material=chrome, verts=16, name='shaft'))

# motor housing: a teardrop behind the rear guard, with a vented band and a chrome nose ring
H(kit.lathe([(0, -0.05), (0.03, -0.05), (0.05, -0.058), (0.063, -0.075), (0.068, -0.1), (0.066, -0.125), (0.058, -0.148),
             (0.042, -0.168), (0.022, -0.18), (0, -0.184)], material=enamel, steps=64, name='motor'))
H(kit.torus(0.032, 0.0035, at=(0, 0, -0.051), material=chrome, major=40, minor=8, name='motor_nose'))
for k in range(20):
    a = math.tau * k / 20
    H(kit.box((0.0035, 0.0012, 0.018), at=(0.0675 * math.cos(a), 0.0675 * math.sin(a), -0.105), rot=(0, 0, math.degrees(a) + 90),
              material=black, name='vent'))
# oscillation knob on top of the motor (local +Y is up)
H(kit.cyl(0.004, 0.022, at=(0, 0.064, -0.14), rot=(90, 0, 0), material=chrome, verts=12, name='osc_stem'))
H(kit.lathe([(0, 0), (0.011, 0), (0.012, 0.004), (0.011, 0.012), (0.006, 0.016), (0, 0.017)], material=black, steps=24,
            name='osc_knob'))
head[-1].matrix_world = Matrix.Translation((0, 0.074, -0.14)) @ Matrix.Rotation(math.radians(-90), 4, 'X')

# swing the head so +Z (forward) faces -Y, and lift it into place
M = Matrix.Translation(HEAD) @ Matrix.Rotation(math.radians(90), 4, 'X')
for o in head:
    o.matrix_world = M @ o.matrix_world

# pivot yoke under the motor, with the tilt knob
mz = HEAD.z - 0.064
my = HEAD.y + 0.11
kit.box((0.034, 0.05, 0.03), at=(0, my, mz - 0.006), material=enamel, bevel=0.006, name='pivot_block')
kit.lathe([(0, 0.228), (0.02, 0.228), (0.02, 0.235), (0, 0.235)], material=enamel, steps=24, name='stem_cap')
for sx in (-1, 1):
    kit.cyl(0.012, 0.006, at=(sx * 0.02, my, mz - 0.006), rot=(0, 90, 0), material=chrome, verts=24, name='pivot_washer')
kit.cyl(0.004, 0.02, at=(0.03, my, mz - 0.006), rot=(0, 90, 0), material=chrome, verts=12, name='tilt_screw')
kit.lathe([(0, 0), (0.012, 0), (0.013, 0.004), (0.012, 0.012), (0, 0.013)], material=black, steps=24, name='tilt_knob')
bpy.data.objects['tilt_knob'].matrix_world = Matrix.Translation((0.038, my, mz - 0.006)) @ Matrix.Rotation(math.radians(90), 4, 'Y')
# the cord leaves the back of the base through a grommet, drops to the table and ends in a plug
kit.cyl(0.006, 0.012, at=(0, 0.113, 0.009), rot=(90, 0, 0), material=black, verts=16, bevel=0.0015, name='grommet')
pts = []
for i in range(25):
    t = i / 24
    # a lazy S on the table
    y = 0.118 + 0.085 * t
    x = 0.07 * math.sin(t * math.pi * 0.85)
    z = 0.0035 + 0.0055 * max(0.0, 1 - t * 5) ** 2
    pts.append((x, y, z))
ptube(pts, 0.0035, black, res=1, name='cord')
end = Vector(pts[-1]); d = (end - Vector(pts[-2])).normalized()
plug = kit.box((0.018, 0.03, 0.012), at=end + d * 0.014 + Vector((0, 0, 0.0025)), material=black, bevel=0.003, name='plug')
plug.rotation_euler = (0, 0, math.atan2(d.y, d.x) - math.pi / 2)
for sx in (-1, 1):
    p = kit.box((0.002, 0.016, 0.006), at=end + d * 0.036 + Vector((sx * 0.005, 0, 0.0025)), material=brass, name='prong')
    p.rotation_euler = plug.rotation_euler

kit.export('electric-fan')
