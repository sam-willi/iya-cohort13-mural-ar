"""Fish aquarium, after Beatrice Madden's drawing (RV P5a).

A tall glass tank (W 0.60 x D 0.38 x H 0.91 m, the drawing's 1 : 0.64 : 1.52) under a dark hood, with a deep gravel bed.
Inside, as drawn: two cartoon fish, bubbles that spell COHORT (front) and 13 (left side), a jellyfish over tall
seaweed, a small grass clump, a spiky anemone and a crab on the gravel. The heater and airline on the back glass
are invented so the back has something to look at.
"""
import sys, os, math, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

random.seed(83)

# ---------------------------------------------------------------- helpers
def _catmull(points, subdiv, closed=False):
    P = [Vector(p) for p in points]
    if len(P) < 3 or subdiv <= 1:
        return P
    out = []
    n = len(P)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if closed else P[max(i - 1, 0)]
        p1 = P[i]; p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed else P[min(i + 2, n - 1)]
        for k in range(subdiv):
            t = k / subdiv; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def tube(points, r, material=None, sides=8, subdiv=4, closed=False, caps=True, name='tube', smooth=True):
    """Swept circle along a Catmull-Rom path (parallel-transport frames). r: float or callable t->radius."""
    P = _catmull(points, subdiv, closed)
    n = len(P)
    rad = (lambda t: r) if not callable(r) else r
    T = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[i - 1]
        else:
            t = P[min(i + 1, n - 1)] - P[max(i - 1, 0)]
        T.append(t.normalized())
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    verts, faces = [], []
    for i in range(n):
        if i:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-8:
                ang = T[i - 1].angle(T[i])
                N = (Matrix.Rotation(ang, 3, b.normalized()) @ N)
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        rr = rad(i / max(n - 1, 1))
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(P[i] + (N * math.cos(a) + B * math.sin(a)) * rr)
    rings = n if not closed else n
    for i in range(rings - (0 if closed else 1)):
        j = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, j * sides + k2, j * sides + k))
    if caps and not closed:
        c0 = len(verts); verts.append(P[0]); c1 = len(verts); verts.append(P[-1])
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k))
            faces.append((c1, (n - 1) * sides + k, (n - 1) * sides + k2))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return kit.finish(o, None, smooth=50 if smooth else 0)


def mesh_obj(name, verts, faces, material=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    for p in me.polygons:
        p.use_smooth = smooth
    return o


def group(objs, loc=(0, 0, 0), rotz=0.0, roty=0.0, rotx=0.0, name='grp', scale=1.0):
    e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e)
    for o in objs:
        o.parent = e
    e.location = loc; e.rotation_euler = (math.radians(rotx), math.radians(roty), math.radians(rotz))
    e.scale = (scale, scale, scale)
    return e


def ribbon(spine, widths, facing, thick, material, name='leaf', crease=0.0):
    """A leaf/blade: strip along `spine` (3D points), half-width per point, flat side facing `facing`."""
    verts, faces = [], []
    n = len(spine)
    for i, p in enumerate(spine):
        p = Vector(p)
        t = (Vector(spine[min(i + 1, n - 1)]) - Vector(spine[max(i - 1, 0)])).normalized()
        side = t.cross(Vector(facing)).normalized()
        nrm = side.cross(t).normalized()
        w = widths[i]
        verts += [p - side * w, p + nrm * crease * w, p + side * w]
    for i in range(n - 1):
        a, b = 3 * i, 3 * (i + 1)
        faces += [(a, b, b + 1, a + 1), (a + 1, b + 1, b + 2, a + 2)]
    o = mesh_obj(name, verts, faces, material)
    sd = o.modifiers.new('solid', 'SOLIDIFY'); sd.thickness = thick; sd.offset = 0
    return o


def gravel_texture(path, size=512, seed=7):
    """Worley-cell pebbles in warm natural tones, tileable."""
    rng = np.random.default_rng(seed)
    npts = 170
    pts = rng.random((npts, 2)) * size
    cols = np.array([kit.hex_rgb(c)[:3] for c in
                     ('#d4a872', '#a8743f', '#ead6ae', '#8a7258', '#c8913f', '#e0c49a', '#6a4e38', '#b89c7c', '#c8783f', '#f0e2c4')])
    cols = cols ** (1 / 2.2)  # back to display-ish values for the texture
    pid = rng.integers(0, len(cols), npts)
    shade = rng.uniform(0.75, 1.1, npts)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    f1 = np.full((size, size), 1e9, np.float32); f2 = np.full((size, size), 1e9, np.float32)
    idx = np.zeros((size, size), np.int32)
    for k, (px, py) in enumerate(pts):
        dx = np.abs(xx - px); dx = np.minimum(dx, size - dx)
        dy = np.abs(yy - py); dy = np.minimum(dy, size - dy)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < f1
        f2 = np.where(closer, f1, np.minimum(f2, d))
        idx = np.where(closer, k, idx)
        f1 = np.where(closer, d, f1)
    edge = np.clip((f2 - f1) / 5.0, 0, 1)            # 0 in the gaps between pebbles
    dome = np.clip(1.0 - f1 / 34.0, 0.4, 1.0)        # brighter toward pebble centre
    rgb = cols[pid[idx]] * (shade[idx] * (0.55 + 0.45 * dome))[..., None]
    grout = np.array([0.36, 0.27, 0.18])
    rgb = rgb * edge[..., None] + grout * (1 - edge[..., None])
    rgb = np.clip(rgb, 0, 1)
    img = bpy.data.images.new('gravel', size, size)
    px = np.ones((size, size, 4), np.float32); px[..., :3] = rgb[::-1]
    img.pixels = px.ravel()
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


def planar_uv(obj, tile):
    me = obj.data
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            v = obj.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0: u, w = v.y, v.z
            elif ax == 1: u, w = v.x, v.z
            else: u, w = v.x, v.y
            uv.data[li].uv = (u / tile, w / tile)


# ---------------------------------------------------------------- materials
M_HOOD = kit.mat('#2a2522', rough=0.42, name='hood')
M_TRIM = kit.mat('#1b1a19', rough=0.4, name='trim')
M_SEAL = kit.mat('#141414', rough=0.5, name='silicone')
M_GLASS = kit.mat('glass', rough=0.04, alpha=0.09, name='glass')
M_WATER = kit.mat('#5fb0c8', rough=0.05, alpha=0.11, name='water')
tex = gravel_texture(os.path.join(tempfile.gettempdir(), 'fish_aquarium_gravel.png'))
M_GRAVEL = kit.mat('#ffffff', rough=0.85, image=tex, name='gravel')
M_ORANGE = kit.mat('#e0692a', rough=0.4, name='fish_orange')
M_ORANGE_FIN = kit.mat('#f08a3c', rough=0.45, name='fish_fin')
M_GOLD = kit.mat('#f0b23a', rough=0.4, name='fish_gold')
M_GOLD_FIN = kit.mat('#f6c25a', rough=0.45, name='fish_gold_fin')
M_EYE_W = kit.mat('#f7f3ea', rough=0.3, name='eye_white')
M_EYE_B = kit.mat('#121212', rough=0.15, name='eye_black')
M_CRAB = kit.mat('#c8452a', rough=0.45, name='crab')
M_CRAB_LT = kit.mat('#e8834a', rough=0.5, name='crab_spot')
M_WEED = kit.mat('#4f8a3e', rough=0.6, name='weed')
M_WEED_DK = kit.mat('#3a6a34', rough=0.6, name='weed_dark')
M_GRASS = kit.mat('#7aa34a', rough=0.6, name='grass')
M_ANEM = kit.mat('#e07a5a', rough=0.55, name='anemone')
M_JELLY = kit.mat('#f2a483', rough=0.25, alpha=0.72, emit=0.25, name='jelly')
M_JELLY_T = kit.mat('#f6c0a0', rough=0.3, alpha=0.6, emit=0.2, name='jelly_tent')
M_BUBBLE = kit.mat('#f4fbff', rough=0.05, alpha=0.3, name='bubble')
for _m in (M_GLASS, M_WATER, M_BUBBLE):
    _m.use_backface_culling = True
M_LETTER = kit.mat('#16323d', rough=0.4, name='letter')
M_HEATER_GL = kit.mat('#dfe9ee', rough=0.05, alpha=0.3, name='heater_glass')
M_COPPER = kit.mat('copper', rough=0.3, metal=0.9, name='copper')
M_SUCTION = kit.mat('#cfe3e8', rough=0.3, alpha=0.55, name='suction')
M_AIRLINE = kit.mat('#d8e6ea', rough=0.25, alpha=0.6, name='airline')
M_STONE = kit.mat('#8a8f94', rough=0.9, name='airstone')
M_ROCK = kit.mat('#7d7266', rough=0.85, name='rock')
M_ROCK2 = kit.mat('#a8927a', rough=0.85, name='rock2')

# ---------------------------------------------------------------- dimensions
W, D = 0.60, 0.38            # outer glass footprint
G = 0.006                    # glass thickness
Z0, ZG = 0.03, 0.80          # glass from base trim to hood
ZS = 0.23                    # top of the gravel bed (26% of the height, as drawn)
ZH = 0.91                    # top of the hood
XI, YI = W / 2 - G, D / 2 - G  # inner glass faces

# ---------------------------------------------------------------- base trim
FOOT = 0.006
kit.box((W + 0.008, D + 0.008, Z0), at=(0, 0, FOOT + Z0 / 2), material=M_TRIM, bevel=0.004, segments=2, name='base_trim')
# little rubber feet so it doesn't look like it melts into the floor
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.box((0.05, 0.05, FOOT), at=(sx * (W / 2 - 0.04), sy * (D / 2 - 0.04), FOOT / 2), material=M_SEAL,
                bevel=0.002, name='foot')
Z0b = Z0 + FOOT

# ---------------------------------------------------------------- glass panes (butt-jointed, no overlaps)
hgl = ZG - 0.022 - Z0b   # the black rim sits on top of the glass
kit.box((W, G, hgl), at=(0, -D / 2 + G / 2, Z0b + hgl / 2), material=M_GLASS, bevel=0.0015, name='glass_front')
kit.box((W, G, hgl), at=(0, D / 2 - G / 2, Z0b + hgl / 2), material=M_GLASS, bevel=0.0015, name='glass_back')
for sx in (-1, 1):
    kit.box((G, D - 2 * G, hgl), at=(sx * (W / 2 - G / 2), 0, Z0b + hgl / 2), material=M_GLASS, bevel=0.0015, name='glass_side')
# silicone beads in the four inside corners
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.box((0.007, 0.007, ZG - 0.024 - ZS), at=(sx * (XI - 0.0035), sy * (YI - 0.0035), ZS + (ZG - 0.024 - ZS) / 2),
                material=M_SEAL, bevel=0.002, name='seal')

# ---------------------------------------------------------------- top rim frame (under the hood)
rim = kit.box((W + 0.01, D + 0.01, 0.022), at=(0, 0, ZG - 0.011), material=M_TRIM, bevel=0.003, name='rim')
cut = kit.box((W - 0.03, D - 0.03, 0.05), at=(0, 0, ZG - 0.011))
kit.boolean(rim, cut)
# bottom rim frame wraps the glass foot
brim = kit.box((W + 0.01, D + 0.01, 0.022), at=(0, 0, Z0b + 0.011), material=M_TRIM, bevel=0.003, name='brim')
cut = kit.box((W + 0.0006, D + 0.0006, 0.05), at=(0, 0, Z0b + 0.011))
kit.boolean(brim, cut)

# ---------------------------------------------------------------- hood with a hinged feeding flap
hh = ZH - ZG
hood = kit.box((W + 0.014, D + 0.014, hh), at=(0, 0, ZG + hh / 2), material=M_HOOD, bevel=0.006, segments=3, name='hood')
# raised feeding flap with a hinge barrel and a finger lip
kit.box((0.32, 0.14, 0.006), at=(0, -0.055, ZH + 0.003), material=M_HOOD, bevel=0.0025, segments=2, name='flap')
kit.cyl(0.0045, 0.28, at=(0, -0.055 + 0.073, ZH + 0.0035), rot=(0, 90, 0), material=M_TRIM, verts=16, bevel=0.001, name='hinge')
kit.box((0.06, 0.012, 0.004), at=(0, -0.055 - 0.074, ZH + 0.004), material=M_TRIM, bevel=0.0015, name='flap_lip')
# vent slots along the back of the hood
for i in range(9):
    s = kit.box((0.035, 0.03, 0.008), at=(-0.16 + i * 0.04, D / 2 + 0.007, ZG + hh * 0.55))
    kit.boolean(hood, s)
# a seam line where the hood shell meets its lower lip
kit.box((W + 0.016, D + 0.016, 0.004), at=(0, 0, ZG + 0.018), material=M_TRIM, bevel=0.0015, name='hood_seam')

# ---------------------------------------------------------------- gravel bed (textured, seen through the glass)
gz = ZS - Z0b - 0.004
gravel = kit.box((2 * XI - 0.002, 2 * YI - 0.002, gz), at=(0, 0, Z0b + 0.004 + gz / 2), name='gravel')
gravel.data.materials.append(M_GRAVEL)
planar_uv(gravel, 0.22)
# gentle mounding on top: scattered pebbles and a few rocks
rock_mats = [M_ROCK, M_ROCK2, kit.mat('#c8a070', rough=0.85, name='peb1'), kit.mat('#5a4a3c', rough=0.85, name='peb2'),
             kit.mat('#e2cfa8', rough=0.85, name='peb3')]
for i in range(70):
    x = random.uniform(-XI + 0.02, XI - 0.02); y = random.uniform(-YI + 0.02, YI - 0.02)
    r = random.uniform(0.006, 0.012)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(x, y, ZS + r * 0.15))
    p = bpy.context.object; p.name = 'pebble'
    p.scale = (random.uniform(0.9, 1.4), random.uniform(0.8, 1.2), random.uniform(0.45, 0.7))
    p.rotation_euler.z = random.uniform(0, math.pi)
    kit.finish(p, random.choice(rock_mats))
for (x, y, r, m) in ((0.18, 0.11, 0.045, M_ROCK), (0.24, 0.05, 0.03, M_ROCK2), (-0.20, 0.12, 0.035, M_ROCK)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, ZS + r * 0.3))
    p = bpy.context.object; p.name = 'rock'
    p.scale = (1.3, 1.0, 0.75)
    bm = bmesh.new(); bm.from_mesh(p.data)
    for v in bm.verts:
        v.co *= 1 + random.uniform(-0.08, 0.08)
    bm.to_mesh(p.data); bm.free()
    kit.finish(p, m)

# ---------------------------------------------------------------- water
wz0, wz1 = ZS + 0.0005, ZG - 0.035
water = kit.box((2 * XI - 0.003, 2 * YI - 0.003, wz1 - wz0), at=(0, 0, (wz0 + wz1) / 2), material=M_WATER, name='water')


# ---------------------------------------------------------------- fish
def fish(body_m, fin_m, L=0.12, name='fish'):
    """A cartoon fish pointing +X, centred at the origin: rounded body, triangle tail, eye and smile as drawn."""
    R = L * 0.33
    prof = [(0, -L * 0.5)]
    for i in range(1, 15):
        t = i / 15
        r = R * (math.sin(math.pi * t ** 0.85) ** 0.8) * (0.25 + 0.75 * min(1, t * 2.2)) + 0.004 * (1 - t)
        prof.append((r, -L * 0.5 + L * t))
    prof.append((0, L * 0.5))
    body = kit.lathe(prof, rot=(0, 90, 0), material=body_m, steps=40, name=name + '_body')
    body.scale = (0.78, 0.48, 1.0)  # local: lathe axis is z -> fish length along world x
    parts = [body]
    # triangle tail with a soft notch, like the drawing
    tail = kit.extrude([(0, 0), (0.07 * L / 0.12, 0.045 * L / 0.12), (0.06 * L / 0.12, 0), (0.07 * L / 0.12, -0.045 * L / 0.12)],
                       0.004, at=(-L * 0.5 + 0.004, 0.002, 0), rot=(90, 0, 180), material=fin_m, bevel=0.0012, name=name + '_tail')
    parts.append(tail)
    dorsal = kit.extrude([(0, 0), (0.035 * L / 0.12, 0), (-0.012 * L / 0.12, 0.022 * L / 0.12)], 0.003,
                         at=(0.0, 0.0015, R * 0.66), rot=(90, 0, 0), material=fin_m, bevel=0.001, name=name + '_dorsal')
    dorsal.location.x = -0.005
    parts.append(dorsal)
    for s in (-1, 1):
        pec = kit.extrude([(0, 0), (0.022, -0.004), (0.018, -0.016)], 0.002, at=(0.01, s * R * 0.42, -0.006),
                          rot=(90 + s * 25, 0, 180), material=fin_m, bevel=0.0008, name=name + '_pec')
        parts.append(pec)
        ex, ez = L * 0.28, R * 0.18
        ey = s * R * 0.42 * 0.95
        parts.append(kit.sphere(0.0075, at=(ex, ey, ez), material=M_EYE_W, segs=16, rings=10, name=name + '_eyew'))
        parts.append(kit.sphere(0.0045, at=(ex + 0.0015, ey + s * 0.0048, ez + 0.0005), material=M_EYE_B, segs=12, rings=8,
                                name=name + '_pupil'))
        # smile
        pts = [(L * 0.37 + 0.008 * math.cos(a), s * R * 0.30, -R * 0.12 + 0.008 * math.sin(a))
               for a in np.linspace(math.radians(200), math.radians(300), 6)]
        parts.append(tube(pts, 0.0011, material=M_EYE_B, sides=5, subdiv=2, name=name + '_smile'))
    return parts


f1 = fish(M_ORANGE, M_ORANGE_FIN, L=0.12, name='fishA')
group(f1, loc=(-0.19, -0.03, 0.55), rotz=-95, name='fishA', scale=1.45)     # left side, swimming toward the front
f2 = fish(M_GOLD, M_GOLD_FIN, L=0.12, name='fishB')
group(f2, loc=(0.09, 0.0, 0.40), rotz=180 + 12, name='fishB', scale=1.45)     # front, swimming left

# ---------------------------------------------------------------- crab
def crab():
    parts = []
    body = kit.sphere(0.036, at=(0, 0, 0.026), scale=(1.0, 0.8, 0.55), material=M_CRAB, segs=32, rings=16, name='crab_body')
    parts.append(body)
    parts.append(kit.sphere(0.014, at=(0.014, -0.022, 0.024), scale=(1.0, 0.5, 1.0), material=M_CRAB_LT, segs=20, rings=10, name='crab_spot'))
    for s in (-1, 1):
        # eye stalks + eyes
        parts.append(kit.cyl(0.0028, 0.03, at=(s * 0.011, -0.018, 0.052), rot=(-12, s * 10, 0), material=M_CRAB, verts=10, name='stalk'))
        parts.append(kit.sphere(0.0075, at=(s * 0.014, -0.021, 0.069), material=M_EYE_W, segs=14, rings=8, name='crab_eye'))
        parts.append(kit.sphere(0.0038, at=(s * 0.014, -0.0275, 0.070), material=M_EYE_B, segs=10, rings=6, name='crab_pupil'))
        # arms up to raised claws
        arm = [(s * 0.030, -0.012, 0.028), (s * 0.048, -0.022, 0.040), (s * 0.056, -0.026, 0.056)]
        parts.append(tube(arm, 0.0045, material=M_CRAB, sides=8, subdiv=3, name='arm'))
        c = (s * 0.058, -0.027, 0.064)
        parts.append(kit.sphere(0.011, at=c, scale=(0.8, 0.55, 1.0), material=M_CRAB, segs=16, rings=10, name='claw'))
        for k, ang in ((0, 18), (1, -22)):
            pincer = kit.sphere(0.0075, at=(c[0] + s * (0.004 if k else -0.004), c[1], c[2] + 0.012),
                                scale=(0.45, 0.45, 1.25), material=M_CRAB, segs=12, rings=8, name='pincer')
            pincer.rotation_euler.y = math.radians(s * ang)
            parts.append(pincer)
        # three walking legs per side, reaching down to the gravel
        for j, yy in enumerate((-0.002, 0.012, 0.024)):
            leg = [(s * 0.030, yy, 0.022), (s * 0.048, yy + 0.004, 0.026), (s * 0.058, yy + 0.008, 0.002)]
            parts.append(tube(leg, lambda t: 0.0034 - 0.0016 * t, material=M_CRAB, sides=6, subdiv=3, name='leg'))
    # smile
    pts = [(0.012 * math.cos(a), -0.0296, 0.026 + 0.010 * math.sin(a)) for a in np.linspace(math.radians(205), math.radians(335), 7)]
    parts.append(tube(pts, 0.0013, material=M_EYE_B, sides=5, subdiv=2, name='crab_smile'))
    return parts


group(crab(), loc=(-0.04, -0.085, ZS + 0.001), rotz=-8, name='crab', scale=1.4)

# ---------------------------------------------------------------- tall seaweed (front right) and small grass (back left)
def plant(base, heights, spread, widths, mats, n_leaves, seed, lean=0.0):
    rnd = random.Random(seed)
    parts = []
    for i in range(n_leaves):
        a = 2 * math.pi * i / n_leaves + rnd.uniform(-0.3, 0.3)
        h = rnd.uniform(*heights)
        out = rnd.uniform(*spread)
        pts, ws = [], []
        for k in range(9):
            t = k / 8
            r = out * (t ** 1.6)
            pts.append((base[0] + r * math.cos(a) + lean * t * t, base[1] + r * math.sin(a), base[2] + h * t))
            ws.append(widths * (0.35 + 1.4 * t * (1 - t) ** 0.9) * (1 if k < 8 else 0.08))
        facing = (math.cos(a), math.sin(a), 0)
        parts.append(ribbon(pts, ws, facing, 0.0025, mats[i % len(mats)], name='leaf', crease=0.25))
    return parts


weed = plant((0.20, 0.08, ZS - 0.002), (0.24, 0.32), (0.04, 0.08), 0.017, [M_WEED, M_WEED_DK], 7, 3)
kit.cyl(0.018, 0.016, at=(0.20, 0.08, ZS + 0.004), material=M_WEED_DK, verts=16, bevel=0.004, name='holdfast')
plant((-0.23, 0.10, ZS - 0.002), (0.09, 0.15), (0.02, 0.05), 0.005, [M_GRASS, M_WEED], 6, 11)

# ---------------------------------------------------------------- spiky anemone (front left)
for i in range(18):
    a = 2 * math.pi * i / 18 + random.uniform(-0.15, 0.15)
    up = random.uniform(0.35, 1.0)
    L = random.uniform(0.06, 0.095)
    pts = []
    for k in range(6):
        t = k / 5
        r = L * t * (1 - up * 0.55)
        z = L * up * math.sin(t * math.pi * 0.75) * 0.9 + 0.006
        pts.append((-0.215 + r * math.cos(a), -0.06 + r * math.sin(a), ZS + z))
    tube(pts, lambda t: 0.0032 - 0.0016 * t, material=M_ANEM, sides=6, subdiv=3, name='tentacle')
kit.sphere(0.017, at=(-0.215, -0.06, ZS + 0.004), scale=(1, 1, 0.6), material=M_ANEM, segs=16, rings=8, name='anem_base')

# ---------------------------------------------------------------- jellyfish over the seaweed
jx, jy, jz = 0.17, -0.01, 0.665
bell = []
Rb, Hb = 0.052, 0.05
for i in range(13):
    t = i / 12
    bell.append((Rb * math.sin(t * math.pi / 2) * (1 + 0.06 * t), jz + Hb * math.cos(t * math.pi / 2) ** 0.9 - 0.004 * t))
for i in range(10, -1, -1):
    t = i / 10
    bell.append((Rb * 0.8 * math.sin(t * math.pi / 2), jz - 0.004 + Hb * 0.7 * math.cos(t * math.pi / 2)))
jb = kit.lathe(bell, at=(jx, jy, 0), material=M_JELLY, steps=40, name='jelly_bell')
# scalloped rim
rim_pts = []
for k in range(97):
    a = 2 * math.pi * k / 96
    rr = Rb * 1.03 + 0.003 * math.cos(16 * a)
    rim_pts.append((jx + rr * math.cos(a), jy + rr * math.sin(a), jz - 0.005 + 0.002 * math.sin(16 * a)))
tube(rim_pts[:-1], 0.0026, material=M_JELLY, sides=6, subdiv=1, closed=True, name='jelly_rim')
# curly tentacles (the drawing's squiggles)
for i in range(7):
    a = 2 * math.pi * i / 7
    r0 = Rb * 0.7
    pts = []
    for k in range(40):
        t = k / 39
        rr = r0 * (1 - 0.35 * t)
        wig = 0.006 * math.sin(t * 22 + i)
        pts.append((jx + (rr + wig) * math.cos(a) + 0.004 * math.cos(t * 22 + i) * math.sin(a),
                    jy + (rr + wig) * math.sin(a) - 0.004 * math.cos(t * 22 + i) * math.cos(a),
                    jz - 0.006 - t * 0.12))
    tube(pts, 0.0016, material=M_JELLY_T, sides=6, subdiv=1, name='jelly_tentacle')
for i in range(3):
    a = 2 * math.pi * i / 3 + 0.5
    pts = [(jx + 0.008 * math.cos(a) + 0.004 * math.sin(t * 9), jy + 0.008 * math.sin(a), jz - 0.004 - t * 0.06)
           for t in np.linspace(0, 1, 14)]
    tube(pts, lambda t: 0.0045 - 0.002 * t, material=M_JELLY, sides=8, subdiv=2, name='oral_arm')

# ---------------------------------------------------------------- bubbles: COHORT on the front, 13 on the left side
def bubble(c, r, letter=None, face='front'):
    kit.sphere(r, at=c, material=M_BUBBLE, segs=20 if letter else 12, rings=10 if letter else 6, name='bubble')
    if letter:
        rot = (90, 0, 0) if face == 'front' else (90, 0, -90)
        kit.text(letter, r * 1.45, 0.004, at=c, rot=rot, material=M_LETTER, name='bubble_letter')


col = [('C', 0.715, -0.04), ('O', 0.655, -0.075), ('H', 0.597, -0.06), ('O', 0.540, -0.035), ('R', 0.483, -0.07),
       ('T', 0.428, -0.045)]
for i, (ch, z, x) in enumerate(col):
    bubble((x, -0.085, z), 0.019, ch, 'front')
for (x, z, r) in ((-0.012, 0.70, 0.006), (-0.095, 0.705, 0.008), (0.0, 0.62, 0.007), (-0.10, 0.60, 0.005),
                  (-0.02, 0.52, 0.006), (-0.09, 0.47, 0.007)):
    bubble((x, -0.07, z), r)
bubble((-0.235, -0.07, 0.715), 0.019, '1', 'left')
bubble((-0.235, -0.04, 0.655), 0.019, '3', 'left')
for (y, z, r) in ((-0.02, 0.73, 0.007), (-0.09, 0.685, 0.006), (-0.01, 0.69, 0.006), (-0.06, 0.625, 0.005)):
    bubble((-0.24, y, z), r)

# ---------------------------------------------------------------- back glass: heater and airline with an airstone
hx, hy = 0.215, YI - 0.020
kit.cyl(0.011, 0.22, at=(hx, hy, 0.53), material=M_HEATER_GL, verts=24, name='heater_glass')
coil = [(hx + 0.006 * math.cos(t), hy + 0.006 * math.sin(t), 0.44 + t * 0.0045) for t in np.linspace(0, 36, 160)]
tube(coil, 0.0012, material=M_COPPER, sides=5, subdiv=1, name='heater_coil')
kit.cyl(0.0125, 0.04, at=(hx, hy, 0.66), material=M_TRIM, bevel=0.003, verts=24, name='heater_cap')
kit.cyl(0.0125, 0.012, at=(hx, hy, 0.414), material=M_TRIM, bevel=0.003, verts=24, name='heater_foot')
tube([(hx, hy, 0.68), (hx, hy + 0.004, 0.72), (hx - 0.01, YI - 0.006, ZG - 0.03)], 0.0025, material=M_TRIM, sides=8, name='heater_cord')
for z in (0.47, 0.60):
    kit.cyl(0.002, 0.012, at=(hx, hy + 0.012, z), rot=(90, 0, 0), material=M_SUCTION, verts=10, name='cup_stem')
    kit.cyl(0.009, 0.004, at=(hx, YI - 0.002, z), rot=(90, 0, 0), r2=0.004, material=M_SUCTION, verts=20, name='cup')
ax_ = -0.05
air = [(ax_ - 0.02, YI - 0.006, ZG - 0.02), (ax_ - 0.02, YI - 0.006, 0.50), (ax_ - 0.01, YI - 0.008, 0.30),
       (ax_, YI - 0.03, ZS + 0.02), (ax_, YI - 0.045, ZS + 0.012)]
tube(air, 0.0025, material=M_AIRLINE, sides=8, name='airline')
kit.cyl(0.012, 0.022, at=(ax_ + 0.012, YI - 0.05, ZS + 0.011), rot=(0, 90, 0), material=M_STONE, bevel=0.003, verts=20, name='airstone')
for i, z in enumerate(np.linspace(ZS + 0.04, ZG - 0.06, 11)):
    bubble((ax_ + 0.012 + 0.006 * math.sin(i * 1.7), YI - 0.05 + 0.004 * math.cos(i * 2.3), z), 0.003 + 0.0015 * (i % 3))

kit.export('fish-aquarium')
