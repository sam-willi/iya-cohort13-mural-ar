import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix, Quaternion

# ---------------------------------------------------------------- local helpers (kept in this file on purpose)

def _mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return o


def loft(rings, name='loft', cap_start=True, cap_end=True, closed=True, loop=False, material=None, bevel=0.0, smooth=30):
    """Skin a list of rings (each a list of 3D points, same count). loop=True joins the last ring back to the first."""
    bm = bmesh.new()
    vs = [[bm.verts.new(tuple(p)) for p in ring] for ring in rings]
    n = len(rings[0])
    pairs = list(zip(vs, vs[1:])) + ([(vs[-1], vs[0])] if loop else [])
    for a, b in pairs:
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if not loop:
        if cap_start: bm.faces.new(vs[0][::-1])
        if cap_end: bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _mesh_obj(name, bm)
    return kit.finish(o, material, bevel, smooth=smooth)


def rrect(w, h, r, seg=6, cx=0.0, cy=0.0):
    """Counter-clockwise rounded rectangle polygon."""
    r = min(r, w / 2 - 1e-5, h / 2 - 1e-5); pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return pts


def circle2(r, n=32, cx=0.0, cy=0.0, a0=0.0):
    return [(cx + r * math.cos(a0 + math.tau * i / n), cy + r * math.sin(a0 + math.tau * i / n)) for i in range(n)]


def rod(p0, p1, r, material=None, verts=16, name='rod', bevel=0.0, r2=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    o = kit.cyl(r, d.length, at=(p0 + p1) / 2, material=material, verts=verts, name=name, bevel=bevel, r2=r2)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return o


def fillet(pts, r, seg=6):
    """Round the corners of a polyline."""
    P = [Vector(p) for p in pts]; out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1 = (a - b).normalized(); d2 = (c - b).normalized()
        ang = d1.angle(d2)
        if ang > math.pi - 1e-3:
            out.append(b); continue
        t = min(r / math.tan(ang / 2), (a - b).length * 0.5, (c - b).length * 0.5)
        p1, p2 = b + d1 * t, b + d2 * t
        for k in range(seg + 1):
            s = k / seg; out.append((1 - s) ** 2 * p1 + 2 * (1 - s) * s * b + s * s * p2)
    out.append(P[-1])
    return out


def catmull(pts, n=8, closed=False):
    """Smooth path through points (Catmull-Rom)."""
    P = [Vector(p) for p in pts]; out = []
    m = len(P)
    segs = range(m) if closed else range(m - 1)
    for i in segs:
        p0 = P[(i - 1) % m] if (closed or i > 0) else P[0]
        p1 = P[i]; p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if (closed or i + 2 < m) else P[-1]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


def frames(pts, up=(0, 0, 1), loop=False):
    P = [Vector(p) for p in pts]; m = len(P); T = []
    for i in range(m):
        if loop: t = P[(i + 1) % m] - P[(i - 1) % m]
        elif i == 0: t = P[1] - P[0]
        elif i == m - 1: t = P[-1] - P[-2]
        else: t = P[i + 1] - P[i - 1]
        T.append(t.normalized())
    n = Vector(up); n = n - n.dot(T[0]) * T[0]
    if n.length < 1e-6: n = T[0].orthogonal()
    n.normalize(); N = []
    for i in range(m):
        if i > 0:
            n = T[i - 1].rotation_difference(T[i]) @ n
            n = (n - n.dot(T[i]) * T[i]).normalized()
        N.append(n.copy())
    B = [T[i].cross(N[i]) for i in range(m)]
    return P, T, N, B


def sweep(pts, prof, name='sweep', loop=False, up=(0, 0, 1), material=None, bevel=0.0, caps=True, smooth=30, twist=None):
    """Sweep a 2D profile [(u, v), ...] (u along the frame normal, v along the binormal) along a path."""
    P, T, N, B = frames(pts, up, loop)
    rings = []
    for i in range(len(P)):
        n, b = N[i], B[i]
        if twist:
            a = twist(i / max(1, len(P) - 1)); n, b = n * math.cos(a) + b * math.sin(a), b * math.cos(a) - n * math.sin(a)
        rings.append([P[i] + n * u + b * v for u, v in prof])
    return loft(rings, name, cap_start=caps, cap_end=caps, loop=loop, material=material, bevel=bevel, smooth=smooth)


def apply_mods(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if o.type != 'MESH':
        bpy.ops.object.convert(target='MESH')
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)
    return o


def join(objs, name=None):
    for o in objs: apply_mods(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    if name: o.name = name
    return o


def solidify(o, t, offset=-1.0):
    md = o.modifiers.new('solid', 'SOLIDIFY'); md.thickness = t; md.offset = offset; md.use_even_offset = True
    return o


def xform(o, rot=None, loc=None, scale=None, apply=True):
    """Rotate (degrees XYZ) / move / scale an object and bake it into the mesh."""
    if scale: o.scale = scale
    if rot: o.rotation_mode = 'XYZ'; o.rotation_euler = [math.radians(a) for a in rot]
    if loc: o.location = loc
    if apply:
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.transform_apply(location=bool(loc), rotation=bool(rot), scale=bool(scale))
    return o


def lowest_z():
    dg = bpy.context.evaluated_depsgraph_get(); z = 1e9
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            e = o.evaluated_get(dg); m = e.to_mesh()
            for v in m.vertices:
                z = min(z, (e.matrix_world @ v.co).z)
            e.to_mesh_clear()
    return z


def ground(target=0.0):
    """Shift every root object so the lowest point sits on z=target."""
    dz = target - lowest_z()
    for o in bpy.context.scene.objects:
        if o.parent is None: o.location.z += dz

extrude, tube = kit.extrude, kit.tube

# ---------------------------------------------------------------- model
# Toaster, after JT Lu-Morris's drawing: a two-slot pop-up toaster with soft rounded top edges, a separate base band
# on little feet, the push-down lever (half-moon tab in a slot) and browning dial on the end, and two pieces of toast
# cut as a "1" (back slot) and a "3" (front slot) popping up to read "13" from the front.
ENAMEL = kit.mat('#ece0c4', rough=0.32, name='enamel')
CHROME = kit.mat('chrome', rough=0.22, metal=0.9, name='chrome')
DARK = kit.mat('#2a2826', rough=0.45, name='black_plastic')
SLOT = kit.mat('#3a3633', rough=0.5, metal=0.6, name='slot_steel')
RUBBER = kit.mat('rubber', rough=0.85, name='rubber')
CRUST = kit.mat('#7c4119', rough=0.8, name='toast_crust')


def crumb_texture(path, size=256, seed=3):
    """Toasted crumb: golden base, blotchy browning, small dark pores. Written to a temp PNG."""
    import numpy as np
    rng = np.random.default_rng(seed)
    def smooth_noise(cells):
        g = rng.random((cells + 1, cells + 1)); g[-1, :] = g[0, :]; g[:, -1] = g[:, 0]
        t = np.linspace(0, cells, size, endpoint=False); i = t.astype(int); f = t - i; f = f * f * (3 - 2 * f)
        a = g[i][:, i] * (1 - f)[None, :] + g[i][:, i + 1] * f[None, :]
        b = g[i + 1][:, i] * (1 - f)[None, :] + g[i + 1][:, i + 1] * f[None, :]
        return a * (1 - f)[:, None] + b * f[:, None]
    brown = 0.55 * smooth_noise(4) + 0.3 * smooth_noise(9) + 0.15 * smooth_noise(23)
    pores = (rng.random((size, size)) > 0.985).astype(float)
    pores = np.maximum(pores, np.roll(pores, 1, 0) * 0.6)
    gold = np.array([0.86, 0.62, 0.33]); toast = np.array([0.62, 0.36, 0.15])
    t = np.clip((brown - 0.35) * 1.6, 0, 1)[..., None]
    col = gold * (1 - t) + toast * t
    col = col * (1 - 0.35 * pores[..., None])
    rgba = np.dstack([col, np.ones((size, size))])[::-1]
    img = bpy.data.images.new('crumb', size, size); img.pixels = rgba.astype(np.float32).ravel()
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    return path


import tempfile
CRUMB = kit.mat('white', rough=0.85, name='toast_face', image=crumb_texture(os.path.join(tempfile.gettempdir(), 'toaster_crumb.png')))
COIL = kit.mat('#7a5a40', rough=0.5, metal=0.7, name='coil')

L, W = 0.262, 0.165          # body length (x, along the slots) and width (y)
Z0, Z1 = 0.034, 0.206       # body bottom / top
FEET = 0.008


def rounded_block(lx, ly, z0, z1, r_vert, r_top, r_bot=0.002, name='block'):
    """Box with small vertical corner radii and a large radius on the top edges."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= lx; v.co.y *= ly; v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    vert = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1e-6]
    bmesh.ops.bevel(bm, geom=vert, offset=r_vert, segments=4, profile=0.5, affect='EDGES', clamp_overlap=True)
    top = [e for e in bm.edges if all(abs(v.co.z - z1) < 1e-6 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=top, offset=r_top, segments=8, profile=0.5, affect='EDGES', clamp_overlap=True)
    if r_bot:
        bot = [e for e in bm.edges if all(abs(v.co.z - z0) < 1e-6 for v in e.verts)]
        bmesh.ops.bevel(bm, geom=bot, offset=r_bot, segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _mesh_obj(name, bm)


def cut(target, cutter, mat_transfer=True):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    md.use_self = True
    if mat_transfer: md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)


# body shell with two slots
def loft_block(lx, ly, z0, z1, r_vert, r_top, r_bot=0.002, seg=6, steps=9, name='block'):
    """Rounded box as a stack of rounded-rectangle sections: small vertical radii, big round-over on the top edges."""
    rings = []
    def sec(d, z):
        rr = max(0.0025, r_vert - d * 0.6)
        return [(x, y, z) for x, y in rrect(lx - 2 * d, ly - 2 * d, rr, seg=seg)]
    for k in range(3):  # small round-over at the bottom
        t = (math.pi / 2) * k / 2; d = r_bot * (1 - math.sin(t)); rings.append(sec(d, z0 + r_bot * (1 - math.cos(t))))
    for k in range(steps + 1):
        t = (math.pi / 2) * k / steps; d = r_top * (1 - math.cos(t)); rings.append(sec(d, z1 - r_top + r_top * math.sin(t)))
    return loft(rings, name=name, smooth=40)

body = loft_block(L, W, Z0, Z1, 0.016, 0.04, name='body')
body.data.materials.append(ENAMEL)
SLOT_L, SLOT_W, SLOT_Y = 0.146, 0.034, 0.031
for sy in (-SLOT_Y, SLOT_Y):
    c = extrude(rrect(SLOT_L, SLOT_W, 0.012, seg=5, cy=sy), 0.14, at=(0, 0, Z1 - 0.13), name='slotcut')
    c.data.materials.append(SLOT)
    cut(body, c)
kit.finish(body, None, bevel=0.0012, segments=2, smooth=35)
# chrome trim lips round the slots
for sy in (-SLOT_Y, SLOT_Y):
    outer = rrect(SLOT_L + 0.008, SLOT_W + 0.008, 0.016, seg=5, cy=sy); inner = rrect(SLOT_L, SLOT_W, 0.012, seg=5, cy=sy)
    rings = [[(x, y, Z1 - 0.0005) for x, y in outer], [(x, y, Z1 + 0.0022) for x, y in outer],
             [(x * 0.999, sy + (y - sy) * 0.97, Z1 + 0.0022) for x, y in inner], [(x, y, Z1 - 0.004) for x, y in inner]]
    loft(rings, name='slot_trim', loop=True, material=CHROME, smooth=50)
    # heating element wires on the slot walls and the carriage at the bottom
    for side in (-1, 1):
        yy = sy + side * (SLOT_W / 2 - 0.0012)
        for k in range(9):
            x = -SLOT_L / 2 + 0.014 + k * (SLOT_L - 0.028) / 8
            rod((x - 0.006, yy, Z1 - 0.115), (x + 0.006, yy, Z1 - 0.02), 0.0008, material=COIL, verts=5, name='coil')
    kit.box((SLOT_L - 0.01, SLOT_W - 0.006, 0.004), at=(0, sy, Z1 - 0.118), material=SLOT, name='carriage')

# base band and feet
base = loft_block(L + 0.006, W + 0.006, FEET, Z0 + 0.0005, 0.019, 0.003, r_bot=0.003, steps=3, name='base')
kit.finish(base, CHROME, smooth=40)
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.box((0.026, 0.018, FEET + 0.001), at=(sx * (L / 2 - 0.028), sy * (W / 2 - 0.022), (FEET + 0.001) / 2 - 0.0005),
                material=RUBBER, bevel=0.002, name='foot')
ground_fix = 0.0005

# lever end (-x): recessed lever slot, half-moon lever tab, browning dial with tick dots
EX = -L / 2
lev_cut = extrude(rrect(0.082, 0.013, 0.0065, seg=6), 0.02, at=(EX - 0.004, 0, 0.146), rot=(0, 90, 0), name='levcut')
lev_cut.data.materials.append(DARK)
cut(body, lev_cut)
tab_poly = [(0, -0.024)] + [(-0.026 * math.sin(math.pi * k / 16), -0.024 * math.cos(math.pi * k / 16)) for k in range(1, 16)] + [(0, 0.024)]
tab = extrude(tab_poly, 0.013, at=(EX + 0.002, 0, 0.148), material=DARK, bevel=0.003, segments=3, name='lever')
rod((EX + 0.004, 0, 0.1545), (EX - 0.006, 0, 0.1545), 0.004, material=DARK, verts=12, name='lever_stem')
dial = kit.lathe([(0, 0), (0.0175, 0), (0.0182, 0.002), (0.018, 0.011), (0.0165, 0.0135), (0.006, 0.0145), (0, 0.0145)],
                 at=(EX + 0.0005, 0, 0.066), rot=(0, -90, 0), material=DARK, steps=40, name='dial')
kit.box((0.003, 0.003, 0.012), at=(EX - 0.0145, 0, 0.072), material=CHROME, bevel=0.0008, name='dial_pointer')
for k in range(6):  # browning settings: dots growing round the lower arc of the dial
    a = math.radians(-130 + 260 * k / 5)
    kit.sphere(0.0014 + 0.00035 * k, at=(EX - 0.0003, 0.027 * math.sin(a), 0.066 + 0.027 * math.cos(a) * 0.98), material=DARK,
               segs=10, rings=6, name='tick')

# far end (+x): crumb tray tab under the body
kit.box((0.006, 0.07, 0.012), at=(L / 2 + 0.004, 0, Z0 + 0.006 - 0.012), material=DARK, bevel=0.002, name='crumb_tab')

# back: power cord leaving through a grommet and curling on the floor
gx, gz = -0.08, 0.02
kit.cyl(0.0065, 0.008, at=(gx, W / 2 + 0.0035 + 0.003, gz), rot=(90, 0, 0), material=DARK, verts=16, bevel=0.0015, name='grommet')
cord_pts = [(gx, W / 2 + 0.008, gz), (gx, W / 2 + 0.026, gz - 0.008), (gx + 0.014, W / 2 + 0.042, 0.004),
            (gx + 0.06, W / 2 + 0.05, 0.004), (gx + 0.12, W / 2 + 0.036, 0.004), (gx + 0.17, W / 2 + 0.03, 0.004),
            (gx + 0.2, W / 2 + 0.034, 0.004)]
tube(cord_pts, 0.004, material=DARK, name='cord')

# toast numerals: golden faces, darker crust round the cut edges (Arial Rounded Bold if present, else Blender's font)
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'
def toast_glyph(ch, size, x, y, z_bottom, name):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = ch; cu.size = size; cu.extrude = 0.011
    if os.path.exists(FONT): cu.font = bpy.data.fonts.load(FONT)
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    o.data.materials.clear(); o.data.materials.append(CRUMB); o.data.materials.append(CRUST)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    xs = [v.co.x for v in bm.verts]; zs = [v.co.z for v in bm.verts]
    off = Vector(((min(xs) + max(xs)) / 2, 0, min(zs)))
    for v in bm.verts: v.co -= off
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        f.material_index = 0 if abs(f.normal.y) > 0.6 else 1
        for lp in f.loops: lp[uvl].uv = (lp.vert.co.x / 0.11 + (0.37 if ch == '3' else 0), lp.vert.co.z / 0.11)
    bm.to_mesh(o.data); bm.free()
    o.location = (x, y, z_bottom)
    md = o.modifiers.new('bevel', 'BEVEL'); md.width = 0.0022; md.segments = 2; md.limit_method = 'ANGLE'
    for p in o.data.polygons: p.use_smooth = False
    print(name, 'glyph size', round(max(xs) - min(xs), 3), round(max(zs) - min(zs), 3))
    return o

one = toast_glyph('1', 0.2, -0.03, SLOT_Y, Z1 - 0.032, 'toast_1')
three = toast_glyph('3', 0.2, 0.032, -SLOT_Y, Z1 - 0.05, 'toast_3')

kit.export('toaster')
