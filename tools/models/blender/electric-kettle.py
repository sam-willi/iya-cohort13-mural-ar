"""Electric kettle - Jenny Zhang.

Her drawing: a tall straight cylinder (about 1.65 times as tall as it is wide) with a wide flat rim round a big
lid, a short angular spout jutting from the top on the left, a squared-off handle on the right that comes off the
top and drops down beside the body without rejoining it, the body sitting down in a power base whose rim wraps
up round its foot, and a cord running away from the base.
Line-only, so: teal enamel body and lid, brushed steel rim, walnut handle, black base.
Invented: lid hinge and release button, the plug on the end of the cord.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy, bmesh

kit.reset()

R = 0.076                # body radius
ZB = 0.022               # body bottom (sits down in the base)
H = 0.27                 # top of the body rim
body_m = kit.mat('teal', rough=0.32, name='enamel')
steel_m = kit.mat('chrome', rough=0.3, metal=0.9, name='steel')
walnut_m = kit.mat('walnut', rough=0.55, name='walnut')
base_m = kit.mat('#1f1e1d', rough=0.45, name='base')
rubber_m = kit.mat('rubber', rough=0.8, name='cord')
dark_m = kit.mat('#141414', rough=0.5, name='dark')

# ---------------------------------------------------------------- body, rim and lid
kit.lathe([(0.0, ZB), (R - 0.016, ZB), (R - 0.004, ZB + 0.004), (R, ZB + 0.016), (R, H - 0.012), (R - 0.002, H - 0.01),
           (0.0, H - 0.01)], material=body_m, steps=72, name='body')
# wide steel rim ring round the lid
kit.lathe([(R - 0.022, H - 0.004), (R - 0.022, H - 0.0005), (R - 0.019, H + 0.0015), (R - 0.004, H + 0.0015),
           (R + 0.0008, H - 0.002), (R + 0.0008, H - 0.007), (R - 0.004, H - 0.008), (R - 0.022, H - 0.004)],
          material=steel_m, steps=72, name='rim')
# lid: a gently domed disc sitting just inside the rim, with a seam ring
kit.lathe([(0.0, H + 0.0055), (0.03, H + 0.005), (R - 0.03, H + 0.002), (R - 0.0235, H), (R - 0.0235, H - 0.008),
           (0.0, H - 0.008)], material=body_m, steps=72, name='lid')
kit.torus(R - 0.0225, 0.0012, at=(0, 0, H - 0.0002), material=dark_m, major=72, minor=6)
# lid hinge at the handle side
kit.cyl(0.0045, 0.03, at=(R - 0.026, 0, H + 0.0035), rot=(90, 0, 0), material=steel_m, bevel=0.001, verts=20)

# ---------------------------------------------------------------- spout: an angular wedge out of the top, left
sp = bmesh.new()
pts = [(-R + 0.012, -0.023, H - 0.07), (-R + 0.012, 0.023, H - 0.07), (-R + 0.012, 0.023, H + 0.0035),
       (-R + 0.012, -0.023, H + 0.0035), (-R - 0.03, -0.0095, H - 0.006), (-R - 0.03, 0.0095, H - 0.006),
       (-R - 0.033, 0.0095, H + 0.0065), (-R - 0.033, -0.0095, H + 0.0065)]
vs = [sp.verts.new(p) for p in pts]
bmesh.ops.convex_hull(sp, input=vs)
me = bpy.data.meshes.new('spout'); sp.to_mesh(me); sp.free()
spout = bpy.data.objects.new('spout', me); bpy.context.collection.objects.link(spout)
kit.finish(spout, body_m, bevel=0.003, segments=3)
bpy.ops.object.select_all(action='DESELECT'); spout.select_set(True); bpy.context.view_layer.objects.active = spout
bpy.ops.object.modifier_apply(modifier='bevel')
# pour channel down the top of the spout
ch = kit.box((0.05, 0.011, 0.02), at=(-R - 0.012, 0, H + 0.008))
ch.rotation_euler = (0, math.radians(-8), 0)
kit.boolean(spout, ch)
md = spout.modifiers.new('b2', 'BEVEL'); md.width = 0.0012; md.segments = 2; md.limit_method = 'ANGLE'
md.angle_limit = math.radians(50)

# ---------------------------------------------------------------- handle: off the top, down the side, free end
def bez(p0, p1, p2, n=8):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


X0 = R - 0.012
outer = [(X0, H + 0.008)] + bez((R + 0.03, H + 0.008), (R + 0.064, H + 0.008), (R + 0.064, H - 0.03)) + \
        bez((R + 0.064, H - 0.1), (R + 0.062, H - 0.148), (R + 0.04, H - 0.152), 6)
inner = bez((R + 0.024, H - 0.136), (R + 0.03, H - 0.09), (R + 0.03, H - 0.05), 6) + \
        bez((R + 0.03, H - 0.032), (R + 0.03, H - 0.024), (R + 0.016, H - 0.024), 4) + [(X0, H - 0.024)]
prof = outer + inner
# trace is clockwise in (x, z); kit.extrude recalculates normals either way
handle = kit.extrude(prof, 0.03, material=walnut_m, bevel=0.007, segments=3, name='handle')
handle.rotation_euler = (math.radians(90), 0, 0); handle.location = (0, 0.015, 0)
# steel collar where it meets the body, release button on top, the groove along the grip's outer face
kit.box((0.012, 0.034, 0.036), at=(R - 0.003, 0, H - 0.012), material=steel_m, bevel=0.004, segments=2, name='collar')
kit.box((0.016, 0.014, 0.006), at=(R + 0.03, 0, H + 0.009), material=steel_m, bevel=0.0025, segments=2, name='button')

# ---------------------------------------------------------------- base, cord and plug
kit.lathe([(0.0, 0.0), (0.084, 0.0), (0.088, 0.003), (0.089, 0.03), (0.0875, 0.036), (0.084, 0.038), (0.0795, 0.038),
           (0.0785, 0.03), (0.07, ZB + 0.0005), (0.0, ZB + 0.0005)], material=base_m, steps=72, name='base')
kit.torus(0.0875, 0.0012, at=(0, 0, 0.012), material=steel_m, major=72, minor=6)
cord = [(0.07, 0.05, 0.006), (0.105, 0.068, 0.0045), (0.14, 0.06, 0.0045), (0.17, 0.085, 0.0045),
        (0.195, 0.095, 0.0045)]
kit.tube(cord, 0.0045, material=rubber_m, bevel_res=10, name='cord')
kit.box((0.014, 0.012, 0.009), at=(0.079, 0.055, 0.0065), rot=(0, 0, 27), material=base_m, bevel=0.003)  # strain relief
PA = math.radians(10)
kit.box((0.034, 0.024, 0.016), at=(0.211, 0.098, 0.008), rot=(0, 0, 10), material=base_m, bevel=0.004, segments=2,
        name='plug')
for dy in (-0.006, 0.006):
    px, py = 0.211 + 0.022 * math.cos(PA) - dy * math.sin(PA), 0.098 + 0.022 * math.sin(PA) + dy * math.cos(PA)
    kit.box((0.016, 0.0015, 0.006), at=(px, py, 0.008), rot=(0, 0, 10), material=steel_m)

kit.export('electric-kettle')
