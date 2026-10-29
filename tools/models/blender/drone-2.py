"""Drone - Celeste Oder (Cohort 13).

Her drawing: a quadcopter with a pillowy box body (light top shell over a dark lower body), "XIII"
on top beside a round puck, four long swept arms ending in teardrop motor pods with two-blade
props, skid landing gear, and a banner trailing from it that reads "COHORT 13" and ends in flames.
The banner is part of how she drew (and the mural paints) the object, so it hangs from the drone
here: a tapered cloth on a dowel, lettered on both faces, its tail burning in layered flames.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

kit.reset()
random.seed(13)


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
    """Round tube through 3D points with straight segments. res 2 = 8 sides."""
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


def sweep(path, section, scales, material=None, name='sweep'):
    """Sweep a closed 2D section along a 3D path with per-point (su, sv) scales; capped ends."""
    path = [Vector(p) for p in path]; n = len(path)
    tang = [(path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized() for i in range(n)]
    up = Vector((0, 0, 1))
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for i in range(n):
        T = tang[i]; N = (up - T * up.dot(T)).normalized(); B = T.cross(N)
        su, sv = scales[i]
        rings.append([bm.verts.new(path[i] + su * u * B + sv * v * N) for u, v in section])
    m = len(section)
    for i in range(n - 1):
        for j in range(m):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % m], rings[i + 1][(j + 1) % m], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material)


def apply_xform(o):
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


shell = kit.mat('cream', rough=0.38, name='shell_cream')
dark = kit.mat('gunmetal', rough=0.45, name='body_gunmetal')
black = kit.mat('black', rough=0.5, name='black')
copper = kit.mat('copper', rough=0.3, metal=0.85, name='motor_copper')
steel = kit.mat('steel', rough=0.3, metal=0.85, name='steel')
red = kit.mat('cardinal', rough=0.4, name='xiii_red')
prop_tip = kit.mat('orange', rough=0.45, name='prop_tip')
lens = kit.mat('#101418', rough=0.08, name='lens_glass')
led = kit.mat('#7fd0ff', rough=0.3, emit=0.8, name='led')
cloth = kit.mat('paper', rough=0.85, name='banner_cloth')
ink = kit.mat('#2b2420', rough=0.7, name='banner_ink')
dowel = kit.mat('oak', rough=0.55, name='dowel_oak')
brass = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
flame_out = kit.mat('red', rough=0.6, emit=0.3, name='flame_red')
flame_mid = kit.mat('orange', rough=0.6, emit=0.45, name='flame_orange')
flame_core = kit.mat('lamp', rough=0.6, emit=0.6, name='flame_core')

drone_parts = []


def D(o):
    drone_parts.append(o); return o


# ---------------------------------------------------------------- body: light top shell over a dark lower body
LZ0, LZ1 = 0.048, 0.1           # lower body
UZ0, UZ1 = 0.088, 0.136         # top shell
D(kit.box((0.13, 0.168, LZ1 - LZ0), at=(0, 0.004, (LZ0 + LZ1) / 2), material=dark, bevel=0.022, segments=4, name='lower_body'))
D(kit.box((0.152, 0.19, UZ1 - UZ0), at=(0, 0, (UZ0 + UZ1) / 2), material=shell, bevel=0.02, segments=4, name='top_shell'))
# seam groove where the shell meets the body
D(kit.box((0.146, 0.184, 0.004), at=(0, 0, UZ0 + 0.001), material=black, bevel=0.002, name='seam'))
# "XIII" on top, with the round puck beside it (as drawn)
t = kit.text('XIII', 0.05, 0.004, at=(-0.016, 0.006, UZ1 + 0.0005), rot=(0, 0, 0), material=red, name='xiii')
D(kit.finish(t, bevel=0.0006, segments=1))
D(kit.lathe([(0, UZ1 - 0.004), (0.017, UZ1 - 0.004), (0.017, UZ1 + 0.008), (0.015, UZ1 + 0.011),
             (0.006, UZ1 + 0.012), (0.006, UZ1 + 0.015), (0, UZ1 + 0.015)], at=(0.046, 0.05, 0),
            material=dark, steps=32, name='gps_puck'))
D(kit.torus(0.011, 0.0012, at=(0.046, 0.05, UZ1 + 0.0115), material=steel, major=24, minor=6, name='puck_ring'))
# the little round eyes on the lower body corners (drawn as small circles)
for sx in (-1, 1):
    p = Vector((sx * 0.05, -0.08, 0.066))
    D(kit.cyl(0.009, 0.01, at=p, rot=(90, 0, 0), material=steel, verts=24, bevel=0.002, name='eye_ring'))
    D(kit.cyl(0.0065, 0.004, at=p + Vector((0, -0.005, 0)), rot=(90, 0, 0), material=lens, verts=24, name='eye_lens'))
# status LED strip on the back
D(kit.box((0.05, 0.004, 0.006), at=(0, 0.097, 0.072), material=led, bevel=0.002, name='led'))
# battery latch on the back of the top shell
D(kit.box((0.04, 0.008, 0.016), at=(0, 0.096, 0.11), material=dark, bevel=0.003, name='latch'))

# ---------------------------------------------------------------- arms, motor pods and props
MX, MY, MZ = 0.215, 0.2, 0.122
oval = [(math.cos(math.tau * k / 16), math.sin(math.tau * k / 16)) for k in range(16)]
angles = [17, 74, -32, 118]
for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
    root = Vector((sx * 0.05, sy * 0.068, 0.112))
    tip = Vector((sx * MX, sy * MY, MZ))
    path, scl = [], []
    for k in range(17):
        t = k / 16
        p = root.lerp(tip, t) + Vector((0, 0, 0.012 * math.sin(math.pi * t) - 0.004 * t))
        path.append(p)
        w = 0.011 * (1 - t) ** 1.6 + 0.0065       # flares wide where it joins the body
        scl.append((w, w * 0.75))
    D(sweep(path, oval, scl, shell, name='arm'))
    # teardrop motor pod hanging under the arm tip, pointed at the bottom
    D(kit.lathe([(0, MZ - 0.058), (0.003, MZ - 0.054), (0.008, MZ - 0.04), (0.0125, MZ - 0.02), (0.0135, MZ - 0.004),
                 (0.013, MZ + 0.004), (0, MZ + 0.004)], at=(tip.x, tip.y, 0), material=dark, steps=32, name='pod'))
    # motor bell, cooling slots implied by a ring, prop hub
    D(kit.lathe([(0, MZ + 0.003), (0.0125, MZ + 0.003), (0.0125, MZ + 0.014), (0.011, MZ + 0.016), (0, MZ + 0.016)],
                at=(tip.x, tip.y, 0), material=copper, steps=32, name='motor_bell'))
    D(kit.torus(0.0126, 0.0012, at=(tip.x, tip.y, MZ + 0.009), material=black, major=32, minor=6, name='bell_ring'))
    D(kit.lathe([(0, MZ + 0.016), (0.006, MZ + 0.016), (0.006, MZ + 0.022), (0.003, MZ + 0.025), (0, MZ + 0.026)],
                at=(tip.x, tip.y, 0), material=black, steps=24, name='prop_hub'))
    # two-blade prop: tapered, pitched blades with orange tips
    a = math.radians(angles[i])
    for side in (-1, 1):
        blade = [(0.004, -0.006), (0.04, -0.0075), (0.07, -0.006), (0.084, -0.0035), (0.086, 0.0),
                 (0.084, 0.0035), (0.07, 0.0055), (0.04, 0.0065), (0.004, 0.005)]
        b = kit.extrude(blade, 0.0022, material=black, name='blade')
        tipb = kit.extrude([(0.07, -0.0062), (0.084, -0.0036), (0.0865, 0.0), (0.084, 0.0036), (0.07, 0.0056)],
                           0.0028, at=(0, 0, -0.0003), material=prop_tip, name='blade_tip')
        for o in (b, tipb):
            o.matrix_world = (Matrix.Translation((tip.x, tip.y, MZ + 0.02)) @ Matrix.Rotation(a + (math.pi if side < 0 else 0), 4, 'Z')
                              @ Matrix.Rotation(math.radians(10), 4, 'X') @ o.matrix_world)
            D(o)

# ---------------------------------------------------------------- skid landing gear
for sx in (-1, 1):
    x = sx * 0.062
    D(ptube([(x, -0.088, 0.008), (x, 0.088, 0.008)], 0.0055, dark, name='skid'))
    for y in (-0.088, 0.088):
        D(kit.sphere(0.0068, at=(x, y, 0.008), material=black, segs=16, rings=8, name='skid_cap'))
    for y in (-0.045, 0.045):
        D(ptube([(x, y, 0.008), (x * 0.86, y, 0.03), (x * 0.66, y, LZ0 + 0.01)], 0.0042, dark, name='skid_leg'))
    D(ptube([(x * 0.66, -0.045, LZ0 + 0.004), (x * 0.66, 0.045, LZ0 + 0.004)], 0.004, dark, name='skid_brace'))

# ---------------------------------------------------------------- the banner (built hanging in local XZ, then swung back)
L, W0, W1, TH = 0.5, 0.115, 0.25, 0.003
A = 0.02                                    # ripple amplitude along its length


def ripple(s):                              # s = 0 at the hem .. 1 at the tail
    return A * math.sin(math.pi * s) ** 0.7 * math.sin(math.tau * 1.4 * s + 0.5)


def width(s):
    return W0 + (W1 - W0) * s


banner = []
me = bpy.data.meshes.new('banner'); bm = bmesh.new()
NS, NU = 72, 8
front, back = [], []
for i in range(NS + 1):
    s = i / NS; z = -s * L; y = ripple(s); w = width(s)
    front.append([bm.verts.new((w * (u / NU - 0.5), y - TH / 2, z)) for u in range(NU + 1)])
    back.append([bm.verts.new((w * (u / NU - 0.5), y + TH / 2, z)) for u in range(NU + 1)])
for i in range(NS):
    for j in range(NU):
        bm.faces.new((front[i][j], front[i + 1][j], front[i + 1][j + 1], front[i][j + 1]))
        bm.faces.new((back[i][j], back[i][j + 1], back[i + 1][j + 1], back[i + 1][j]))
    for j in (0, NU):
        f = (front[i][j], back[i][j], back[i + 1][j], front[i + 1][j])
        bm.faces.new(f if j == 0 else tuple(reversed(f)))
for j in range(NU):
    bm.faces.new((front[0][j], front[0][j + 1], back[0][j + 1], back[0][j]))
    bm.faces.new((front[-1][j], back[-1][j], back[-1][j + 1], front[-1][j + 1]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
o = bpy.data.objects.new('banner', me); bpy.context.collection.objects.link(o)
banner.append(kit.finish(o, cloth, smooth=40))

# hem: the cloth folds over a dowel at the top
banner.append(kit.cyl(0.0075, W0 + 0.05, at=(0, 0, 0.004), rot=(0, 90, 0), material=dowel, verts=20, name='dowel'))
for sx in (-1, 1):
    banner.append(kit.sphere(0.009, at=(sx * (W0 / 2 + 0.027), 0, 0.004), material=brass, segs=16, rings=8, name='dowel_end'))
banner.append(kit.box((W0 + 0.004, 0.011, 0.022), at=(0, 0, -0.006), material=cloth, bevel=0.004, name='hem'))


def lettering(text, size, s_from, s_to, side):
    """Text running up the banner (reads from the tail toward the drone), wrapped onto the ripple."""
    t = kit.text(text, size, 0.0016, at=(0, 0, 0), rot=(90, -90, 0), material=ink, name='lettering')
    apply_xform(t)
    zs = [v.co.z for v in t.data.vertices]; zmin, zmax = min(zs), max(zs)
    k = (s_to - s_from) * L / (zmax - zmin)
    if k < 1:
        for v in t.data.vertices:
            v.co.z *= k; v.co.x *= k
        zs = [v.co.z for v in t.data.vertices]; zmin, zmax = min(zs), max(zs)
    shift = -s_to * L - zmin
    bm = bmesh.new(); bm.from_mesh(t.data)
    z = zmin + 0.005
    while z < zmax:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
        z += 0.005
    bm.to_mesh(t.data); bm.free()
    for v in t.data.vertices:
        v.co.z += shift
        s = -v.co.z / L
        v.co.y = v.co.y + ripple(s) - TH / 2 - 0.0002
        if side < 0:
            v.co.x, v.co.y = -v.co.x, 2 * ripple(s) - v.co.y
    t.data.update()
    return t


banner.append(lettering('COHORT 13', 0.085, 0.07, 0.93, 1))
banner.append(lettering('COHORT 13', 0.085, 0.07, 0.93, -1))

# flames off the tail: three layers, each thicker than the last so they read from both sides


def flame_poly(width_, n, h_lo, h_hi, overlap, sway):
    """A row of curling flame tongues hanging off the tail, as a 2D outline (x across, z down)."""
    pts = [(width_ / 2, overlap)]
    pitch = width_ / n
    for k in range(n):
        x0 = width_ / 2 - pitch * k            # right edge of this tongue
        h = random.uniform(h_lo, h_hi); lean = random.uniform(-sway, sway)
        for i in range(1, 9):                  # right flank, curving into the tip
            t = i / 8
            pts.append((x0 - pitch * 0.5 * t ** 1.4 + lean * t ** 2, -h * (0.15 + 0.85 * t ** 1.15)))
        for i in range(1, 9):                  # left flank, back up to the notch
            t = 1 - i / 8
            pts.append((x0 - pitch + pitch * 0.5 * t ** 0.7 + lean * t ** 2.2, -h * (0.15 + 0.85 * t ** 2.2)))
        if k < n - 1:
            pts.append((x0 - pitch, -h * 0.1))
    pts.append((-width_ / 2, overlap))
    return pts


for mat_, wd, n, lo, hi, th, ov in ((flame_out, W1 + 0.03, 6, 0.15, 0.23, 0.006, 0.05),
                                     (flame_mid, W1 - 0.02, 5, 0.1, 0.16, 0.011, 0.035),
                                     (flame_core, W1 - 0.08, 4, 0.05, 0.095, 0.016, 0.02)):
    poly = [(x, z) for x, z in flame_poly(wd, n, lo, hi, ov, 0.025)]
    f = kit.extrude(poly, th, at=(0, th / 2, -L), rot=(90, 0, 0), material=mat_, bevel=0.0015, name='flame')
    banner.append(f)

# swing the banner back and down behind the drone, hung from the rear skids by a bridle
hang = Vector((0, 0.115, -0.03))
R = Matrix.Translation(hang) @ Matrix.Rotation(math.radians(24), 4, 'X')
for o in banner:
    o.matrix_world = R @ o.matrix_world
for sx in (-1, 1):
    end = R @ Vector((sx * (W0 / 2 + 0.018), 0, 0.004))
    D(ptube([(sx * 0.062, 0.088, 0.008), tuple(end)], 0.0014, black, res=1, name='bridle'))

# stand the whole thing on z = 0 (the flame tips are the lowest point)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
zmin = min((o.matrix_world @ Vector(c)).z for o in objs for c in o.bound_box)
for o in objs:
    o.matrix_world = Matrix.Translation((0, 0, -zmin)) @ o.matrix_world

kit.export('drone-2')
