"""'Coffee grinder' (Lauren Young). Her drawing is not a grinder: it's an EXPLODED octagonal stovetop moka pot with
coffee pouring out of it, and the stream spells "C13". Modelled as drawn, every part free-floating in her layout:

- top: the upper chamber, tipped back so its threaded mouth (gasket and perforated filter plate inside) faces the
  viewer the way she drew it from below; beak spout up and to the right, black tube handle down and to the left,
  hinged lid and knob on top for the back view. A few coffee grounds fall from its mouth.
- middle-left: the funnel basket, tilted with its stem pointing down-right, heaped with grounds.
- bottom: the boiler upright, octagonal frustum, threaded round collar on top, brass safety valve on the front facet.
- right: a stream of glossy coffee from the spout down to the boiler: a splash and drips, a long S ribbon, then the
  liquid letters "C13", then more drips. Traced from her drawing in its own pixel coordinates (metaballs, so the
  strokes and drops swell and pinch like liquid), letters facing the front.

Unsure: the upper chamber's pose (she draws it from below; read as tipped back toward the viewer and slightly toward the
spout, as if pouring). The parts and the stream sit in one plane, as in the drawing; the sides are invented."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, random, tempfile
from mathutils import Vector, Matrix, Euler, noise

random.seed(13)

alu = kit.mat('#c4c7cb', rough=0.34, metal=0.85, name='aluminium')
alu_dark = kit.mat('#8d9096', rough=0.45, metal=0.8, name='aluminium_shadow')
inside = kit.mat('#46484c', rough=0.55, metal=0.6, name='aluminium_inside')
bakelite = kit.mat('#1c1a19', rough=0.4, name='bakelite')
brass = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
rubber = kit.mat('#2a2826', rough=0.75, name='gasket')
coffee = kit.mat('#2c160a', rough=0.07, name='coffee')
grounds = kit.mat('#3b2818', rough=0.95, name='grounds')

OCT = 22.5                            # turn the octagon so flat facets face front/back/left/right
FLAT = math.cos(math.radians(22.5))   # facet-centre radius / corner radius

# Her drawing's pixel coordinates -> metres in the front (XZ) plane. The boiler's foot (430 px) is 10 cm.
S = 0.10 / 430


def D(u, v):
    return ((u - 540) * S, (1455 - v) * S)   # v=1455: the boiler foot's centre (its front corner is drawn at 1495)


def octa(profile, name, material=alu, bevel=0.0012):
    o = kit.lathe(profile, rot=(0, 0, OCT), material=material, steps=8, name=name)
    md = o.modifiers.new('bevel', 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(20)
    return o


def ring(r_in, r_out, z0, z1, material, steps=48, name='ring'):
    """A solid washer (closed profile not touching the axis)."""
    return kit.lathe([(r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1), (r_in, z0)], material=material, steps=steps,
                     name=name)


def helix(R, r, z0, z1, turns, material, steps_per_turn=40, sides=6, name='thread'):
    """A screw thread: a small circle swept round Z while climbing from z0 to z1."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((R + r * math.cos(a), 0, z0 + r * math.sin(a)))
          for a in [i * math.tau / sides for i in range(sides)]]
    es = [bm.edges.new((vs[i], vs[(i + 1) % sides])) for i in range(sides)]
    steps = int(turns * steps_per_turn)
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), dvec=(0, 0, (z1 - z0) / steps),
                   angle=turns * math.tau, steps=steps, use_duplicate=False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material)


def new_since(before):
    return [o for o in bpy.context.scene.objects if o not in before]


def group(name, objs, rot):
    """Parent the parts to an empty so the whole piece can be posed as one."""
    e = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(e)
    for o in objs:
        if o.parent is None:
            o.parent = e
    e.rotation_euler = Euler([math.radians(a) for a in rot], 'XYZ')
    return e


def pose(e, local_pt, world_pt):
    """Move empty e so that its local point lands on world_pt."""
    rot = e.rotation_euler.to_matrix()
    e.location = Vector(world_pt) - rot @ Vector(local_pt)
    bpy.context.view_layer.update()


def perforated_plate_texture():
    """Steel disc with a grid of holes (UVs map the disc's diameter to the image)."""
    import numpy as np
    n = 512
    img = bpy.data.images.new('filter_plate', n, n)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    cx = (xx + 0.5) / n * 2 - 1; cy = (yy + 0.5) / n * 2 - 1          # -1..1 across the disc
    pitch = 2 / 13.0
    gx = (cx / pitch) - np.round(cx / pitch); gy = (cy / pitch) - np.round(cy / pitch)
    hole = (np.hypot(gx, gy) < 0.26) & (np.hypot(cx, cy) < 0.80)
    rim = (np.hypot(cx, cy) > 0.86) & (np.hypot(cx, cy) < 0.9)
    base = np.array([0.72, 0.73, 0.75])
    rgb = np.where(hole[..., None], np.array([0.12, 0.11, 0.10]), base)
    rgb = np.where(rim[..., None], base * 0.78, rgb)
    px = np.concatenate([rgb, np.ones((n, n, 1))], axis=2).astype(np.float32)
    img.pixels.foreach_set(px.ravel())
    path = os.path.join(tempfile.gettempdir(), 'coffee-grinder-filter-plate.png')
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


def disc(r, z, material, verts=48, name='disc'):
    """A flat disc facing down (-Z) with planar UVs."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=verts, radius=r)
    for f in bm.faces:
        f.normal_flip()
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / (2 * r) + 0.5, l.vert.co.y / (2 * r) + 0.5)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, z))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o


# =====================================================================================================
# BOILER (bottom, upright): octagonal frustum, round threaded collar, brass safety valve
# =====================================================================================================
before = set(bpy.context.scene.objects)
B_TOP = 0.0606
octa([(0, 0.0015), (0.0455, 0.0015), (0.049, 0.0035), (0.0502, 0.007), (0.0372, 0.0565), (0.0356, 0.0592),
      (0.0332, B_TOP), (0.0262, B_TOP)], 'boiler')
octa([(0, 0.0), (0.0445, 0.0), (0.0455, 0.0015), (0, 0.0015)], 'boiler_foot', alu_dark, bevel=0.0004)
# collar: round, open, with a dark floor inside so it reads hollow
kit.lathe([(0.0235, 0.044), (0.0235, 0.0748), (0.0241, 0.0757), (0.0262, 0.0757), (0.0268, 0.0749),
           (0.0268, 0.0590)], material=alu, steps=48, name='collar')
disc(0.0237, 0.045, inside, name='boiler_inside')
helix(0.0270, 0.00075, 0.0625, 0.0715, 2.2, alu, name='collar_thread')
# safety valve on the front facet (her concentric circles)
vz = 0.029
r_face = (0.0502 + (0.0372 - 0.0502) * (vz - 0.007) / (0.0565 - 0.007)) * FLAT
tilt = math.degrees(math.atan2((0.0502 - 0.0372) * FLAT, 0.0565 - 0.007))
V = kit.lathe([(0, 0), (0.0085, 0), (0.0085, 0.0025), (0.0068, 0.0032), (0.0062, 0.0042), (0.0042, 0.0046),
               (0.0036, 0.0058), (0.002, 0.0072), (0, 0.0074)], material=brass, steps=32, name='valve')
V.rotation_euler = (math.radians(90 - tilt), 0, 0)
V.location = (0, -r_face + 0.0006, vz)
vr = kit.torus(0.0058, 0.0007, material=brass, major=24, minor=6, name='valve_ring')
vr.rotation_euler = (math.radians(90 - tilt), 0, 0); vr.location = (0, -r_face - 0.0035, vz + 0.0008)
boiler = group('boiler_part', new_since(before), (0, 0, 0))
boiler.location = (D(585, 0)[0], 0, 0)

# =====================================================================================================
# FUNNEL BASKET (middle): cup with a flange, heaped with grounds, long stem
# =====================================================================================================
before = set(bpy.context.scene.objects)
kit.lathe([(0.0066, 0.0), (0.022, 0.0), (0.0252, 0.0012), (0.0262, 0.004), (0.0262, 0.0185), (0.0300, 0.0190),
           (0.0306, 0.0198), (0.0300, 0.0206), (0.0250, 0.0206), (0.0246, 0.0198), (0.0246, 0.0040), (0, 0.0040)],
          material=alu, steps=48, name='funnel_cup')
kit.lathe([(0, 0.002), (0.0068, 0.002), (0.0068, -0.047), (0.0064, -0.0485), (0.0050, -0.0485), (0.0047, -0.0472),
           (0.0047, -0.040), (0, -0.040)], material=alu, steps=32, name='funnel_stem')
# heaped grounds: a dome, roughened with noise, sprinkled with loose granules
HEAP = 0.0125
prof = [(0.0247 * math.cos(t * math.pi / 2), 0.0165 + HEAP * math.sin(t * math.pi / 2) ** 0.8)
        for t in [i / 12 for i in range(13)]]
prof[-1] = (0, prof[-1][1])
g = kit.lathe(prof, material=grounds, steps=48, name='grounds_heap')
for vtx in g.data.vertices:
    rr = math.hypot(vtx.co.x, vtx.co.y)
    w = min(1.0, (0.0247 - rr) / 0.004)
    vtx.co.z += w * (0.0014 * noise.noise(vtx.co * 240) + 0.0007 * noise.noise(vtx.co * 700 + Vector((3, 1, 2))))
for i in range(36):
    a = random.uniform(0, math.tau); rr = 0.022 * math.sqrt(random.random())
    t = 1 - rr / 0.0247
    z = 0.0165 + HEAP * max(0.0, math.sin(t * math.pi / 2)) ** 0.8
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.0006, 0.0010),
                                          location=(rr * math.cos(a), rr * math.sin(a), z + 0.0003))
    kit.finish(bpy.context.object, grounds, smooth=0).name = 'granule'
funnel = group('funnel_part', new_since(before), (20, -30, 0))
fx, fz = D(355, 792)
pose(funnel, (0, 0, 0.012), (fx, 0, fz))

# =====================================================================================================
# UPPER CHAMBER (top, tipped): threaded skirt with gasket and filter plate, flared octagon, lid, spout, handle
# =====================================================================================================
before = set(bpy.context.scene.objects)
plate_mat = kit.mat('#ffffff', rough=0.4, metal=0.7, name='filter_plate', image=perforated_plate_texture())
# skirt: round, female-threaded inside (two ridges), open at the bottom
kit.lathe([(0.0274, 0.0125), (0.0274, 0.0012), (0.0280, 0.0), (0.0293, 0.0), (0.0299, 0.0008), (0.0299, 0.0130)],
          material=alu, steps=48, name='skirt')
for k, z in enumerate((0.0035, 0.0065)):
    kit.torus(0.0273, 0.00055, at=(0, 0, z), material=alu_dark, major=48, minor=6, name='skirt_thread')
ring(0.0203, 0.0275, 0.0097, 0.0113, rubber, name='gasket')
disc(0.0206, 0.0101, plate_mat, name='filter_plate')
# body: octagon flaring from the waist to the rim, a little taller than the boiler (as she drew it)
octa([(0, 0.0118), (0.0335, 0.0118), (0.0355, 0.0133), (0.0362, 0.016), (0.0462, 0.086), (0.0477, 0.0886),
      (0.0469, 0.0905), (0, 0.0905)], 'top_chamber')
# lid: faceted, sloping in to a flat top (seam line under it)
octa([(0, 0.0902), (0.0472, 0.0902), (0.0479, 0.0915), (0.0452, 0.0945), (0.0295, 0.1038), (0.0152, 0.1068),
      (0, 0.107)], 'lid')
kit.lathe([(0, 0), (0.0075, 0), (0.0068, 0.004), (0.0058, 0.0065), (0.0085, 0.0098), (0.0088, 0.0122),
           (0.0072, 0.0142), (0, 0.0146)], at=(0.012, 0, 0.1053), material=bakelite, steps=28, name='knob')
kit.cyl(0.0035, 0.024, at=(-0.0492, 0, 0.0928), rot=(90, 0, 0), material=alu, verts=16, bevel=0.0006, name='hinge')
for y in (-0.008, 0.008):
    kit.box((0.008, 0.006, 0.006), at=(-0.0457, y, 0.0918), material=alu, bevel=0.001, name='hinge_leaf')
# beak spout on the right (+X), as drawn: a big triangular beak rising off the rim
RX = 0.0477 * FLAT
SPOUT_TIP = (RX + 0.027, 0.0, 0.0975)
me = bpy.data.meshes.new('spout'); bm = bmesh.new()
vL = bm.verts.new((RX - 0.004, -0.0165, 0.0902)); vR = bm.verts.new((RX - 0.004, 0.0165, 0.0902))
vB = bm.verts.new((RX - 0.0075, 0.0, 0.054)); tip = bm.verts.new(SPOUT_TIP)
ch = bm.verts.new((RX + 0.003, 0.0, 0.0848))
for f in ((vL, ch, tip), (ch, vR, tip), (vL, tip, vB), (tip, vR, vB), (vR, ch, vL), (vL, vB, vR)):
    bm.faces.new(f)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me); bm.free()
sp = bpy.data.objects.new('spout', me); bpy.context.collection.objects.link(sp)
sp.data.materials.append(alu)
sm = sp.modifiers.new('solid', 'SOLIDIFY'); sm.thickness = 0.0012; sm.offset = 1
md = sp.modifiers.new('bevel', 'BEVEL'); md.width = 0.0006; md.segments = 1; md.limit_method = 'ANGLE'
# handle on the left (-X): bracket, then a black tube out and down past the mouth (as drawn)
kit.box((0.012, 0.016, 0.040), at=(-0.0445, 0, 0.064), rot=(0, -9, 0), material=alu, bevel=0.003, segments=2,
        name='handle_bracket')
H = [(-0.047, 0, 0.082), (-0.061, 0, 0.0835), (-0.072, 0, 0.077), (-0.079, 0, 0.060), (-0.083, 0, 0.034),
     (-0.084, 0, 0.008), (-0.0835, 0, -0.005)]
kit.tube(H, 0.0075, material=bakelite, bevel_res=14, name='handle')
kit.box((0.018, 0.012, 0.008), at=(-0.0435, 0, 0.040), material=alu, bevel=0.002, name='handle_lower_tab')
kit.tube([(-0.043, 0, 0.040), (-0.062, 0, 0.040), (-0.079, 0, 0.036)], 0.0045, material=bakelite, bevel_res=8,
         name='handle_strut')
top = group('upper_chamber_part', new_since(before), (-35, 15, 0))
tx, tz = D(598, 228)
pose(top, SPOUT_TIP, (tx, 0, tz))

# falling grounds under the chamber's mouth (her specks)
mouth = top.matrix_world @ Vector((0, 0, 0))
heap = funnel.matrix_world @ Vector((0, 0, 0.0165 + HEAP))
z_hi, z_lo = mouth.z - 0.016, heap.z + 0.012
for i in range(22):
    t = random.random() ** 1.6                       # denser just under the mouth
    z = z_hi - t * (z_hi - z_lo)
    x = mouth.x - 0.004 + random.uniform(-0.009, 0.009) * (0.6 + t)
    y = mouth.y * (1 - 0.5 * t) + random.uniform(-0.007, 0.007)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.0007, 0.0013), location=(x, y, z))
    o = bpy.context.object; o.rotation_euler = [random.uniform(0, 3) for _ in range(3)]
    kit.finish(o, grounds, smooth=0).name = 'falling_ground'

# =====================================================================================================
# COFFEE: the stream and the letters, traced from her drawing (u, v, radius in px), as one liquid
# =====================================================================================================
STREAM = [
    [(612, 238, 4), (613, 258, 6), (614, 280, 7)],                                          # drip off the spout
    [(622, 192, 7), (648, 177, 9), (684, 180, 10), (700, 204, 10), (690, 236, 9), (676, 266, 8), (680, 296, 10)],
    [(706, 236, 5), (730, 252, 10), (752, 266, 15)],                                        # splash off the squiggle
    [(718, 310, 5), (722, 330, 8)],
    [(668, 343, 5), (658, 370, 9)],
    [(604, 446, 4), (592, 470, 8), (574, 505, 13), (562, 528, 15)],                        # long falling drop
    [(746, 440, 6), (744, 470, 10), (728, 510, 11), (700, 540, 12), (662, 566, 12), (630, 592, 12), (610, 625, 13),
     (604, 662, 15), (606, 684, 13)],                                                       # the S ribbon
    [(736, 578, 6), (744, 610, 11), (756, 648, 16), (772, 676, 19), (800, 690, 9), (828, 690, 5)],
    [(536, 688, 5), (528, 704, 8)],
    [(706, 652, 4), (704, 668, 6)],
    [(552, 940, 16), (566, 960, 19), (586, 990, 13), (598, 1015, 9), (602, 1034, 7)],      # under the C
    [(700, 1004, 11), (716, 1022, 13), (740, 1048, 10), (764, 1078, 8), (772, 1090, 7)],
    [(786, 990, 3), (787, 1012, 4), (788, 1028, 4)],
    [(792, 1116, 4), (792, 1132, 8), (792, 1146, 10)],                                      # last drop by the boiler
]
LETTERS = [
    # C
    [(598, 770, 10), (590, 748, 11), (568, 740, 12), (548, 756, 13), (538, 790, 14), (536, 830, 14), (544, 862, 13),
     (560, 882, 12), (580, 882, 11), (594, 864, 10), (598, 846, 9)],
    # 1 (with its flag)
    [(655, 778, 9), (668, 760, 11), (684, 746, 12), (684, 775, 12), (679, 820, 12), (673, 860, 12), (668, 884, 11)],
    # 3
    [(748, 758, 12), (770, 742, 14), (800, 744, 15), (816, 766, 15), (810, 792, 14), (788, 810, 12), (778, 814, 11),
     (800, 822, 13), (822, 840, 16), (830, 868, 17), (818, 900, 17), (790, 914, 16), (760, 906, 14), (742, 890, 12)],
]


def catmull(pts, n=10):
    P = [Vector(p) for p in pts]
    if len(P) == 2:
        return [P[0].lerp(P[1], k / n) for k in range(n + 1)]
    P = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


# Metaball resolution bottoms out at 0.005 units, so the liquid is built K times larger and scaled back down.
K = 20.0
mb = bpy.data.metaballs.new('coffee'); mb.threshold = 0.6
mb.resolution = mb.render_resolution = 0.0006 * K
liquid = bpy.data.objects.new('coffee', mb); bpy.context.collection.objects.link(liquid)
BALL = 1.5      # a dense line of balls of radius R makes a tube of radius ~R/1.5


def pour(strokes, y0, fat, wobble):
    for si, stroke in enumerate(strokes):
        pts = []
        for (u, v, r) in stroke:
            x, z = D(u, v)
            pts.append((x, 0.0, z, r * S * fat))
        dense = catmull(pts)
        acc = 0.0; last = None; s = 0.0
        for p in dense:
            q = Vector((p[0], p[1], p[2]))
            if last is not None:
                s += (q - last).length
            if last is None or s - acc >= 0.35 * BALL * p[3] or p is dense[-1]:
                rv = p[3] * (1 + wobble * noise.noise(Vector((s * 400, si * 7.3, 0.5))))
                y = y0 + 0.0012 * noise.noise(Vector((s * 120, si * 3.1, 2.0)))
                e = mb.elements.new(); e.co = (q.x * K, y * K, q.z * K); e.radius = BALL * rv * K; e.stiffness = 2.0
                acc = s
            last = q


pour(STREAM, 0.0, 1.25, 0.15)
pour(LETTERS, -0.002, 1.3, 0.08)
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = liquid; liquid.select_set(True)
bpy.ops.object.convert(target='MESH')
liquid = bpy.context.object; liquid.name = 'coffee'
liquid.scale = (1 / K,) * 3
bpy.ops.object.transform_apply(scale=True)
kit.finish(liquid, coffee, smooth=180)
dec = liquid.modifiers.new('decimate', 'DECIMATE'); dec.ratio = 0.16   # ~110k -> ~18k triangles, still smooth

kit.export('coffee-grinder')
