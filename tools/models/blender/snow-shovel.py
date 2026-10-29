"""Snow shovel. No drawing exists, so this is a classic one, standing on its blade: a wide scooped orange blade with
raised side lips, ribs and a steel wear strip riveted along the edge, a moulded socket, an oak shaft with a steel
ferrule, and a black D-grip."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix

blade_m = kit.mat('#c9531f', rough=0.42, name='blade')   # palette orange, a little deeper
steel = kit.mat('steel', rough=0.32, metal=0.9, name='steel')
oak = kit.mat('oak', rough=0.6, name='oak')
grip_m = kit.mat('black', rough=0.5, name='grip')

BW, BL = 0.46, 0.37          # blade width, blade length (edge to back)
NU, NV = 36, 28


def blade_point(u, v, front=0.0):
    """u in [-1, 1] across, v in [0, 1] from the leading edge up to the back. Returns the point on the scoop."""
    t = v
    z = BL * (t - 0.08 * t * t) + 0.004
    y = -0.125 * (1 - t) ** 2 + 0.014 * (u ** 2)
    return Vector((u * BW / 2, y, z))


def sheet(fn, nu, nv, thickness, material, name):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [[bm.verts.new(fn(-1 + 2 * i / (nu - 1), j / (nv - 1))) for i in range(nu)] for j in range(nv)]
    for j in range(nv - 1):
        for i in range(nu - 1):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    kit.finish(o, material, smooth=40)
    s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = thickness; s.offset = 0; s.use_even_offset = True
    b = o.modifiers.new('bevel', 'BEVEL'); b.width = thickness * 0.45; b.segments = 2; b.limit_method = 'ANGLE'
    return o


# ---------- blade ----------
sheet(lambda u, v: blade_point(u, 0.02 + 0.98 * v), NU, NV, 0.006, blade_m, 'blade')
# raised side lips, tall at the back, fading to nothing at the edge
for s in (-1, 1):
    def lip(a, v, s=s):
        p = blade_point(s, 0.02 + 0.98 * v)
        h = 0.055 * min(1.0, v * 1.6) * (0.25 + 0.75 * v)
        return p + Vector((s * 0.0, -h * (a + 1) / 2 * 0.95, h * (a + 1) / 2 * 0.3))
    sheet(lip, 3, 22, 0.006, blade_m, 'side_lip')
# back wall rolling over at the top
kit.tube([tuple(blade_point(u, 1.0) + Vector((0, 0.0, 0.006))) for u in (-1, -0.5, 0, 0.5, 1)], 0.008,
         material=blade_m, bevel_res=12, name='top_roll')
# ribs on the back of the scoop
for u in (-0.62, -0.3, 0.3, 0.62):
    pts = [tuple(blade_point(u, v) + Vector((0, 0.008, 0))) for v in (0.12, 0.4, 0.7, 0.98)]
    kit.tube(pts, 0.006, material=blade_m, bevel_res=10, name='rib')
# low ridges running up the scoop face (they stop snow sticking, and catch the light)
for u in (-0.75, -0.45, -0.15, 0.15, 0.45, 0.75):
    pts = [tuple(blade_point(u, v) + Vector((0, -0.0024, 0.0012))) for v in (0.1, 0.35, 0.6, 0.85)]
    kit.tube(pts, 0.0032, material=blade_m, bevel_res=10, name='ridge')
    for p in (pts[0], pts[-1]):
        kit.sphere(0.0032, at=p, material=blade_m, segs=10, rings=6, name='ridge_end')
# steel wear strip folded over the leading edge, with rivets
sheet(lambda u, v: blade_point(u, 0.0 + 0.075 * v), 24, 4, 0.0095, steel, 'wear_strip')
for i in range(7):
    u = -0.84 + i * 0.28
    p = blade_point(u, 0.04)
    kit.sphere(0.0042, at=tuple(p + Vector((0, -0.0048, 0.0012))), scale=(1, 0.55, 1), material=steel, segs=12, rings=6,
               name='rivet')

# ---------- socket, shaft, ferrule, D-grip ----------
top = blade_point(0, 1.0)
SX, SY = 0.0, top.y + 0.022
kit.lathe([(0, 0.0), (0.028, 0.0), (0.032, 0.03), (0.026, 0.11), (0.0215, 0.13), (0, 0.13)],
          at=(SX, SY, top.z - 0.085), material=blade_m, steps=32, name='socket')
for z in (top.z - 0.05, top.z + 0.01):
    kit.cyl(0.0055, 0.006, at=(SX, SY + 0.0295, z), rot=(-90, 0, 0), material=steel, verts=16, bevel=0.0015, name='screw')
SH0, SH1 = top.z - 0.02, 1.08
kit.cyl(0.0175, SH1 - SH0, at=(SX, SY, (SH0 + SH1) / 2), material=oak, verts=28, name='shaft')
kit.lathe([(0, 0), (0.0192, 0), (0.0198, 0.004), (0.0198, 0.05), (0.019, 0.055), (0, 0.055)],
          at=(SX, SY, SH1 - 0.03), material=steel, steps=28, name='ferrule')
for z in (SH1 - 0.018, SH1 + 0.012):
    kit.cyl(0.003, 0.042, at=(SX, SY, z), rot=(90, 0, 0), material=steel, verts=12, name='ferrule_rivet')
# D-grip: two arms out of a collar, closing on a cross grip
GZ = SH1 + 0.025
kit.lathe([(0, 0), (0.021, 0), (0.024, 0.02), (0.02, 0.05), (0, 0.05)], at=(SX, SY, GZ - 0.01), material=grip_m, steps=28,
          name='grip_collar')
for s in (-1, 1):
    kit.tube([(SX + s * 0.008, SY, GZ + 0.03), (SX + s * 0.04, SY, GZ + 0.07), (SX + s * 0.062, SY, GZ + 0.12),
              (SX + s * 0.06, SY, GZ + 0.16)], 0.0125, material=grip_m, bevel_res=12, name='grip_arm')
kit.lathe([(0, -0.075), (0.012, -0.075), (0.0165, -0.06), (0.0175, 0.0), (0.0165, 0.06), (0.012, 0.075), (0, 0.075)],
          at=(SX, SY, GZ + 0.165), rot=(0, 90, 0), material=grip_m, steps=28, name='grip_bar')


kit.export('snow-shovel')
