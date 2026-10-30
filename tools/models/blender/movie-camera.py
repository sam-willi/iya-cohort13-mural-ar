import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

# ---- local helpers (kept in this file so the script stands alone) ----
TAU = math.tau


def desel():
    for o in bpy.context.selected_objects:
        o.select_set(False)


def tube(points, r, material=None, closed=False, res=12, name='tube'):
    # kit.tube converts *every* selected object to mesh; deselect first so it only touches the new curve.
    desel()
    return kit.tube(points, r, material, closed, res, name)


def link(name, bm, material=None, smooth=30, bevel=0.0, segments=2, at=(0, 0, 0), rot=None):
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = at
    if rot:
        o.rotation_euler = [math.radians(a) for a in rot]
    return kit.finish(o, material, bevel, segments, smooth)


def rrect(w, h, r, n=6, cx=0.0, cy=0.0):
    """Rounded rectangle, CCW, as [(x, y)]; n segments per corner."""
    r = min(r, w / 2 - 1e-5, h / 2 - 1e-5)
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def resample(poly, n):
    """Resample a closed polyline to n points evenly spaced by arc length."""
    P = [Vector((p[0], p[1], 0)) for p in poly]
    seg = [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    L = [(b - a).length for a, b in seg]; tot = sum(L)
    out = []
    for k in range(n):
        d = tot * k / n; i = 0
        while d > L[i] and i < len(L) - 1:
            d -= L[i]; i += 1
        a, b = seg[i]; t = d / L[i] if L[i] else 0
        q = a.lerp(b, t); out.append((q.x, q.y))
    return out


def loft(rings, name='loft', material=None, cap0=True, cap1=True, smooth=40, bevel=0.0, closed=True):
    """rings: list of rings, each a list of 3D points (same count). Quads between rings, n-gon caps."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap0:
        bm.faces.new(list(reversed(vr[0])))
    if cap1:
        bm.faces.new(vr[-1])
    return link(name, bm, material, smooth, bevel)


def apply_all(o):
    desel(); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.select_set(False)
    return o


def cut(target, cutter, op='DIFFERENCE'):
    """Boolean with modifiers on the cutter applied first."""
    cutter = apply_all(cutter)
    return kit.boolean(target, cutter, op)


def text_mesh(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, align='CENTER', name='text',
              spacing=1.0, res=5):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.resolution_u = res
    cu.align_x = align; cu.align_y = 'CENTER'; cu.space_character = spacing
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    desel(); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.select_set(False)
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def image_mat(name, rgb_array, rough=0.6, metal=0.0):
    """Material with a generated texture. rgb_array: HxWx3 float sRGB 0..1."""
    h, w, _ = rgb_array.shape
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = np.clip(rgb_array, 0, 1)
    img.pixels.foreach_set(px[::-1].ravel()); img.pack()
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


def wood_tex(base, dark, size=512, rings=14.0, seed=1, figure=1.0, contrast=1.0):
    """Straight-grain wood (grain runs along U): soft latewood lines, fine streaks, slow colour drift.
    Returns HxWx3 sRGB floats."""
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size] / size          # v across the grain, u along it

    def smooth1d(n, k):
        a = rng.normal(0, 1, n + 2 * k)
        w = np.hanning(2 * k + 1); w /= w.sum()
        return np.convolve(a, w, 'valid')[:n]
    # gentle waviness of the growth rings along the board
    d = np.zeros_like(u)
    for k in range(1, 4):
        d += rng.uniform(0.3, 1.0) / k * np.sin(TAU * (k * u + rng.uniform()) + v * rng.uniform(0, 2))
    p = v * rings + d * 0.25 * figure + smooth1d(size, 12)[:, None] * 0.6
    f = p - np.floor(p)
    late = np.clip((f - 0.62) / 0.3, 0, 1) ** 1.5 * (1 - np.clip((f - 0.95) / 0.05, 0, 1))
    streak = smooth1d(size, 1)[:, None] * np.ones((1, size)) * 0.5 + smooth1d(size * 4, 2).reshape(size, 4).mean(1)[:, None] * 0.3
    drift = smooth1d(size, 60)[:, None] * 0.8 + smooth1d(size, 80)[None, :] * 0.6
    t = 0.55 * late + 0.12 * streak + 0.18 * drift + 0.18
    t = np.clip(0.5 + (t - 0.5) * contrast, 0, 1)[..., None]
    c0 = np.array(kit.hex_rgb(base)[:3]) ** (1 / 2.2); c1 = np.array(kit.hex_rgb(dark)[:3]) ** (1 / 2.2)
    return c0 * (1 - t) + c1 * t


def box_uv(o, grain='z', scale=1.0):
    """Box-project UVs in object space so wood grain runs along `grain` (U runs along it)."""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new()
    uv = me.uv_layers.active.data
    ax = 'xyz'.index(grain); others = [i for i in range(3) if i != ax]
    for p in me.polygons:
        nrm = p.normal; dom = max(range(3), key=lambda i: abs(nrm[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if dom == ax:
                u, v = co[others[0]], co[others[1]]
            else:
                side = [i for i in others if i != dom][0] if dom in others else others[0]
                u, v = co[ax], co[side]
            uv[li].uv = (u * scale, v * scale)
    return o


def merge_by_material():
    """Apply modifiers and join meshes that share a material (fewer draw calls on the phone)."""
    groups = {}
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH':
            continue
        o = apply_all(o)
        key = o.data.materials[0].name if o.data.materials else ''
        groups.setdefault(key, []).append(o)
    for key, objs in groups.items():
        if len(objs) < 2:
            continue
        desel()
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
    desel()


def drop_to_floor():
    """Shift everything so the lowest vertex sits on z=0."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); lo = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            ev = o.evaluated_get(dg)
            for v in ev.to_mesh().vertices:
                lo = min(lo, (o.matrix_world @ v.co).z)
            ev.to_mesh_clear()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.location.z -= lo


def ground_check():
    """Print the lowest z so we know the model stands on z=0."""
    dg = bpy.context.evaluated_depsgraph_get(); lo = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            ev = o.evaluated_get(dg)
            for v in ev.to_mesh().vertices:
                lo = min(lo, (o.matrix_world @ v.co).z)
            ev.to_mesh_clear()
    print('MIN_Z', round(lo, 5))


def turn_all(deg=0.0):
    """Rotate the finished model about world Z, then centre it on x/y (front stays -Y)."""
    Rz = Matrix.Rotation(math.radians(deg), 4, 'Z')
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in objs:
        o.matrix_world = Rz @ o.matrix_world
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in objs:
        ev = o.evaluated_get(dg); m = ev.to_mesh()
        for v in m.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        ev.to_mesh_clear()
    c = (lo + hi) / 2
    for o in objs:
        o.location.x -= c.x; o.location.y -= c.y
    print('BBOX', [round(v, 4) for v in (hi - lo)])


# ---- end helpers ----

# Movie camera on a wooden tripod, after Samuel Poole's isometric drawing: twin-reel magazine on top, a side door
# with a centre knob, a control panel, a side viewfinder with its eyepiece out the back, a lens turret with a
# matte box carried on rods, a geared tilt head with a pan handle, and a three-legged wooden tripod with clamps.
# Built with the lens on +X and the door on -Y, then turned 45 degrees so the front view matches the drawing.
PAINT = kit.mat('#34373c', rough=0.5, name='body_paint')
BLACK = kit.mat('black', rough=0.45, name='black')
BRASS = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
CHROME = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
STEEL = kit.mat('steel', rough=0.35, metal=0.9, name='steel')
GLASS = kit.mat('#203440', rough=0.05, name='lens_glass')
LEG = image_mat('leg_wood', wood_tex('#b98250', '#7f5230', size=512, rings=8, seed=11, figure=0.5), rough=0.55)
TOP = image_mat('top_wood', wood_tex('#6a4428', '#3f2716', size=256, rings=8, seed=3), rough=0.55)
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')
CREAM = kit.mat('cream', rough=0.5, name='dial')

L, D, H = 0.30, 0.115, 0.265     # body
ZT = 1.00                        # top of the tripod plate
ZB = ZT + 0.075                  # bottom of the camera body
ZM = ZB + H / 2

body = kit.box((L, D, H - 0.036), at=(0, 0, ZB + (H - 0.036) / 2), material=PAINT, bevel=0.006, segments=3, name='body')
# the lid, a touch proud of the body so the parting line reads
kit.box((L + 0.004, D + 0.004, 0.036), at=(0, 0, ZB + H - 0.018), material=PAINT, bevel=0.006, segments=3, name='lid')
kit.box((L - 0.006, D - 0.006, 0.010), at=(0, 0, ZB + H - 0.036), material=BLACK, name='lid_gap')
YF = -D / 2                      # door face

# ---- door face (-Y): the big door with its centre knob, and the control panel ----
door = kit.box((0.168, 0.006, 0.190), at=(-0.052, YF - 0.0015, ZB + 0.125), material=PAINT, bevel=0.0025,
               segments=2, name='door')
cut(door, kit.box((0.150, 0.01, 0.172), at=(-0.052, YF - 0.0065, ZB + 0.125)))   # raised rim, recessed field
kit.cyl(0.027, 0.008, at=(-0.052, YF - 0.006, ZB + 0.125), rot=(90, 0, 0), material=BRASS, bevel=0.0015, name='knob')
kit.cyl(0.010, 0.012, at=(-0.052, YF - 0.010, ZB + 0.125), rot=(90, 0, 0), material=CHROME, bevel=0.0015, name='hub')
for x, z in ((-0.128, ZB + 0.042), (-0.128, ZB + 0.208), (0.024, ZB + 0.208), (0.024, ZB + 0.042)):
    kit.cyl(0.0055, 0.004, at=(x, YF - 0.0035, z), rot=(90, 0, 0), material=CHROME, verts=16, name='hinge_screw')
kit.cyl(0.012, 0.010, at=(-0.120, YF - 0.009, ZB + 0.020), rot=(90, 0, 0), material=BRASS, bevel=0.002, name='corner_knob')
kit.cyl(0.004, 0.012, at=(-0.120, YF - 0.012, ZB + 0.020), rot=(90, 0, 0), material=CHROME, verts=12, name='corner_pin')
panel = kit.box((0.090, 0.004, 0.190), at=(0.088, YF - 0.001, ZB + 0.125), material=BLACK, bevel=0.0015, name='panel')
for x in (0.066, 0.082):   # the two slots with slider tabs
    cut(panel, kit.box((0.006, 0.02, 0.040), at=(x, YF - 0.004, ZB + 0.150), bevel=0.0015))
    kit.box((0.008, 0.006, 0.008), at=(x, YF - 0.003, ZB + 0.158), material=CHROME, bevel=0.0015, name='slider')
kit.cyl(0.008, 0.004, at=(0.088, YF - 0.004, ZB + 0.210), rot=(90, 0, 0), material=CHROME, name='toggle_base')
tg = kit.cyl(0.0028, 0.020, at=(0.088, YF - 0.010, ZB + 0.214), material=CHROME, verts=12, name='toggle')
tg.rotation_euler = (math.radians(60), 0, 0)
kit.cyl(0.0095, 0.012, at=(0.112, YF - 0.008, ZB + 0.150), rot=(90, 0, 0), material=BLACK, bevel=0.002,
        name='panel_knob')
kit.cyl(0.0045, 0.012, at=(0.075, YF - 0.006, ZB + 0.075), rot=(90, 0, 0), material=CHROME, verts=16, name='lever_pivot')
lv = kit.cyl(0.0025, 0.040, at=(0.090, YF - 0.011, ZB + 0.075), rot=(0, 90, 0), material=CHROME, verts=10, name='lever')
kit.sphere(0.005, at=(0.110, YF - 0.011, ZB + 0.075), material=BLACK, segs=16, rings=8, name='lever_ball')
# footage dial
kit.cyl(0.013, 0.003, at=(0.112, YF - 0.0035, ZB + 0.205), rot=(90, 0, 0), material=CREAM, name='dial')
kit.box((0.0016, 0.002, 0.011), at=(0.112, YF - 0.0055, ZB + 0.209), material=BLACK, name='needle')

# ---- far side (+Y): the hand crank and a maker's plate ----
YB = D / 2
kit.cyl(0.030, 0.008, at=(-0.030, YB + 0.003, ZB + 0.120), rot=(90, 0, 0), material=BRASS, bevel=0.002, name='crank_boss')
kit.cyl(0.010, 0.020, at=(-0.030, YB + 0.012, ZB + 0.120), rot=(90, 0, 0), material=CHROME, name='crank_shaft')
arm = kit.box((0.016, 0.008, 0.090), at=(-0.030, YB + 0.022, ZB + 0.120 - 0.040), material=BLACK, bevel=0.003,
              name='crank_arm')
kit.cyl(0.005, 0.016, at=(-0.030, YB + 0.032, ZB + 0.042), rot=(90, 0, 0), material=CHROME, verts=16, name='crank_pin')
kit.lathe([(0, 0), (0.010, 0), (0.012, 0.010), (0.011, 0.040), (0.009, 0.048), (0, 0.048)],
          at=(-0.030, YB + 0.036, ZB + 0.042), rot=(-90, 0, 0), material=TOP, steps=24, name='crank_knob')
kit.box((0.080, 0.003, 0.034), at=(0.070, YB + 0.0015, ZB + 0.180), material=BRASS, bevel=0.001, name='plate')
for x in (0.034, 0.106):
    kit.cyl(0.003, 0.003, at=(x, YB + 0.003, ZB + 0.180), rot=(90, 0, 0), material=CHROME, verts=12, name='plate_screw')
for x in (-0.12, 0.12):
    kit.box((0.012, 0.006, 0.030), at=(x, YB + 0.002, ZB + 0.050), material=BLACK, bevel=0.002, name='foot_latch')

# ---- side viewfinder along the top of the door side, eyepiece out the back ----
VY, VZ = YF + 0.006, ZB + H + 0.013
kit.cyl(0.0125, 0.25, at=(-0.035, VY, VZ), rot=(0, 90, 0), material=PAINT, bevel=0.002, name='finder')
kit.cyl(0.0145, 0.012, at=(0.090, VY, VZ), rot=(0, 90, 0), material=BRASS, bevel=0.002, name='finder_cap')
kit.lathe([(0, 0), (0.0155, 0), (0.0165, 0.004), (0.0165, 0.048), (0.019, 0.052), (0.021, 0.070), (0.018, 0.074),
           (0, 0.074)], at=(-0.160, VY, VZ), rot=(0, -90, 0), material=BLACK, steps=40, name='eyepiece')
for k in range(7):   # knurled grip rings on the eyepiece
    kit.torus(0.0165, 0.0018, at=(-0.172 - k * 0.0055, VY, VZ), rot=(0, 90, 0), material=BLACK, major=32, minor=6,
              name='knurl')
for x in (-0.12, 0.05):
    kit.box((0.016, 0.014, 0.020), at=(x, VY, VZ - 0.012), material=PAINT, bevel=0.002, name='finder_bracket')

# ---- twin-reel magazine on top ----
MZ = ZB + H + 0.112
RX0, RX1, RR = -0.085, 0.125, 0.100
for x in (RX0, RX1):
    kit.cyl(RR, 0.048, at=(x, 0, MZ), rot=(90, 0, 0), material=PAINT, bevel=0.007, segments=3, verts=72, name='reel')
kit.box((RX1 - RX0, 0.044, 0.090), at=((RX0 + RX1) / 2, 0, MZ - 0.045), material=PAINT, bevel=0.004, name='mag_web')
kit.box((0.080, 0.040, 0.040), at=(0.040, 0, ZB + H + 0.010), material=PAINT, bevel=0.004, name='mag_neck')
for x in (RX0, RX1):
    for s in (-1, 1):
        kit.cyl(0.019, 0.006, at=(x, s * 0.026, MZ), rot=(90, 0, 0), material=BRASS, bevel=0.0015, name='mag_hub')
        k = kit.extrude(rrect(0.012, 0.005, 0.0025, 4), 0.004, at=(x, s * 0.0275, MZ), rot=(90 if s < 0 else -90, 0, 0),
                        material=BLACK, name='key')
        kit.cyl(0.0035, 0.004, at=(x, s * 0.0305, MZ), rot=(90, 0, 0), material=CHROME, verts=16, name='key_pin')
    for k in range(3):   # spoke ribs pressed into the reel cover
        a = TAU * k / 3 + 0.4
        for s in (-1, 1):
            rb = kit.box((0.060, 0.003, 0.008), material=PAINT, bevel=0.0012, name='rib')
            rb.location = (x + 0.052 * math.cos(a), s * 0.0245, MZ + 0.052 * math.sin(a))
            rb.rotation_euler = (0, -a, 0)
# footage counter box between the reels, framed window
cb = kit.box((0.052, 0.012, 0.064), at=(0.020, -0.026, MZ - 0.040), material=PAINT, bevel=0.003, name='counter')
cut(cb, kit.box((0.034, 0.02, 0.044), at=(0.020, -0.034, MZ - 0.040)))
kit.box((0.036, 0.004, 0.046), at=(0.020, -0.0235, MZ - 0.040), material=BRASS, name='counter_frame')
kit.box((0.022, 0.003, 0.012), at=(0.020, -0.026, MZ - 0.032), material=CREAM, name='counter_window')
kit.box((0.026, 0.003, 0.004), at=(0.020, -0.026, MZ - 0.052), material=BLACK, name='counter_slot')

# ---- lens face (+X): turret, lenses, matte box on rods ----
XF = L / 2
TY, TZ = 0.0, ZB + 0.150
kit.cyl(0.050, 0.010, at=(XF + 0.005, TY, TZ), rot=(0, 90, 0), material=BRASS, bevel=0.002, verts=56, name='turret')
kit.cyl(0.036, 0.012, at=(XF + 0.009, TY, TZ), rot=(0, 90, 0), material=BLACK, bevel=0.002, name='turret_cap')
LY, LZ = 0.022, TZ + 0.016                 # taking lens
kit.lathe([(0, 0), (0.024, 0), (0.024, 0.030), (0.027, 0.034), (0.027, 0.056), (0.024, 0.060), (0.024, 0.085),
           (0, 0.085)], at=(XF + 0.008, LY, LZ), rot=(0, 90, 0), material=CHROME, steps=48, name='lens')
for k in range(12):
    a = TAU * k / 12
    kit.box((0.020, 0.003, 0.003), at=(XF + 0.053, LY + 0.0275 * math.cos(a), LZ + 0.0275 * math.sin(a)),
            rot=(math.degrees(a), 0, 0), material=BRASS, name='focus_grip')
kit.cyl(0.021, 0.004, at=(XF + 0.092, LY, LZ), rot=(0, 90, 0), material=GLASS, name='glass')
for dy, dz in ((-0.026, -0.006), (-0.010, -0.032)):   # the two spare lenses on the turret
    kit.lathe([(0, 0), (0.011, 0), (0.011, 0.020), (0.013, 0.022), (0.013, 0.030), (0, 0.030)],
              at=(XF + 0.012, TY + dy, TZ + dz), rot=(0, 90, 0), material=BLACK, steps=32, name='spare_lens')
    kit.cyl(0.009, 0.003, at=(XF + 0.0425, TY + dy, TZ + dz), rot=(0, 90, 0), material=GLASS, verts=24, name='glass')
# small label window and the rod sockets below the turret
kit.box((0.003, 0.030, 0.010), at=(XF + 0.001, -0.015, ZB + 0.080), material=CREAM, name='label')
RODZ = ZB + 0.026
for y in (-0.030, 0.030):
    kit.box((0.012, 0.020, 0.020), at=(XF + 0.004, y, RODZ), material=BLACK, bevel=0.002, name='socket')
    kit.cyl(0.0065, 0.28, at=(XF + 0.140, y, RODZ), rot=(0, 90, 0), material=CHROME, verts=20, name='rod')
    kit.sphere(0.0072, at=(XF + 0.281, y, RODZ), scale=(0.6, 1, 1), material=BLACK, segs=16, rings=8, name='rod_cap')
# bridge plate on the rods carrying the matte box post
kit.box((0.040, 0.085, 0.014), at=(XF + 0.150, 0, RODZ), material=BLACK, bevel=0.002, name='rod_bridge')
kit.box((0.012, 0.012, LZ - RODZ - 0.050), at=(XF + 0.150, LY, (RODZ + LZ - 0.050) / 2 + 0.004), material=CHROME,
        name='mb_post')
# matte box: a flared square hood, open at the front, black inside
X0m, X1m = XF + 0.090, XF + 0.195


def rect_ring(x, w, h):
    return [(x, LY + y, LZ + z) for y, z in rrect(w, h, 0.004, 2)]


mb = loft([rect_ring(X0m, 0.070, 0.066), rect_ring(X1m, 0.150, 0.124)], name='mattebox', material=BLACK, smooth=20)
cut(mb, loft([rect_ring(X0m + 0.004, 0.056, 0.052), rect_ring(X1m + 0.004, 0.146, 0.120)], name='mb_in'))
cut(mb, kit.cyl(0.0245, 0.03, at=(X0m, LY, LZ), rot=(0, 90, 0), verts=40))
kit.box((0.010, 0.074, 0.010), at=(X0m + 0.006, LY, LZ - 0.035), material=BLACK, name='mb_clamp')

# ---- tilt head and pan handle ----
kit.box((0.230, 0.110, 0.013), at=(0, 0, ZB - 0.0065), material=BLACK, bevel=0.002, name='mount_plate')
kit.box((0.085, 0.070, 0.040), at=(0, 0, ZT + 0.042), material=PAINT, bevel=0.004, name='tilt_block')
kit.lathe([(0, 0), (0.058, 0), (0.060, 0.003), (0.060, 0.016), (0.054, 0.022), (0, 0.022)], at=(0, 0, ZT),
          material=BLACK, steps=48, name='pan_base')
gw = kit.cyl(0.034, 0.010, at=(0, -0.041, ZT + 0.047), rot=(90, 0, 0), material=BRASS, bevel=0.0015, name='tilt_wheel')
for k in range(28):
    a = TAU * k / 28
    t = kit.box((0.005, 0.010, 0.006), material=BRASS, name='tooth')
    t.location = (0.035 * math.cos(a), -0.041, ZT + 0.047 + 0.035 * math.sin(a))
    t.rotation_euler = (0, -a, 0)
kit.cyl(0.011, 0.012, at=(0, -0.047, ZT + 0.047), rot=(90, 0, 0), material=CHROME, name='wheel_hub')
kit.cyl(0.004, 0.006, at=(0, -0.055, ZT + 0.047), rot=(90, 0, 0), material=BLACK, verts=12, name='wheel_dot')
kit.cyl(0.010, 0.018, at=(0.030, -0.044, ZT + 0.020), rot=(90, 0, 0), material=BLACK, bevel=0.002, name='lock_knob')
p0, p1 = Vector((-0.030, 0.0, ZT + 0.045)), Vector((-0.300, -0.020, ZT - 0.010))
dd = p1 - p0
ph = kit.cyl(0.0075, dd.length, at=(p0 + p1) / 2, material=CHROME, verts=20, name='pan_bar')
ph.rotation_euler = dd.to_track_quat('Z', 'Y').to_euler()
gd = dd.normalized()
grip = kit.lathe([(0, 0), (0.014, 0), (0.016, 0.010), (0.013, 0.085), (0.010, 0.095), (0, 0.095)],
                 material=BLACK, steps=32, name='pan_grip')
grip.matrix_world = Matrix.Translation(p1 - gd * 0.070) @ gd.to_track_quat('Z', 'Y').to_matrix().to_4x4()

# ---- tripod: walnut top plate, three two-section oak legs with brass clamps and steel spikes ----
tp = kit.box((0.175, 0.175, 0.028), at=(0, 0, ZT - 0.014), material=TOP, bevel=0.004, segments=2, name='top_plate')
box_uv(tp, grain='x', scale=3.0)


def bar(p, q, w, d, mat, name, grain=True):
    p, q = Vector(p), Vector(q); v = q - p
    o = kit.box((w, d, v.length), name=name)
    if grain:
        box_uv(o, grain='z', scale=2.0)
    o.data.materials.clear(); o.data.materials.append(mat)
    kit.finish(o, None, bevel=0.0025, segments=2)
    o.location = (p + q) / 2
    o.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()
    return o


for ang in (0, 270, 135):            # build angles -> front-right, front-left and back after the 45 degree turn
    a = math.radians(ang)
    u = Vector((math.cos(a), math.sin(a), 0))
    top = u * 0.068 + Vector((0, 0, ZT - 0.030))
    foot = u * 0.44 + Vector((0, 0, 0.045))
    ax = (foot - top).normalized()
    kit.box((0.040, 0.040, 0.030), at=top + Vector((0, 0, 0.004)), rot=(0, 0, ang), material=BRASS, bevel=0.003,
            name='hinge')
    kit.cyl(0.008, 0.050, at=top + Vector((0, 0, 0.004)), rot=(90, 0, ang), material=CHROME, verts=16, name='hinge_pin')
    s1 = top + ax * 0.58 * (foot - top).length
    bar(top, s1, 0.036, 0.026, LEG, 'leg_upper')
    s2 = top + ax * 0.42 * (foot - top).length
    bar(s2, foot, 0.025, 0.019, LEG, 'leg_lower')
    for f in (0.30, 0.56):           # clamps
        c = top + ax * f * (foot - top).length
        cl = bar(c - ax * 0.012, c + ax * 0.012, 0.043, 0.033, BRASS, 'clamp', grain=False)
        kit.cyl(0.006, 0.014, at=c + u.cross(Vector((0, 0, 1))) * 0.023, rot=(0, 0, 0), material=BLACK, verts=12,
                name='clamp_screw').rotation_euler = (math.radians(90), 0, a)
    sp = kit.lathe([(0, -0.012), (0.0145, -0.012), (0.0145, 0.010), (0.0045, 0.050), (0, 0.054)], material=STEEL, steps=24,
                   name='spike')
    sp.matrix_world = Matrix.Translation(foot) @ ax.to_track_quat('Z', 'Y').to_matrix().to_4x4()

turn_all(-45)
merge_by_material()
drop_to_floor()        # spike tips on the floor
ground_check()
kit.export('movie-camera')
