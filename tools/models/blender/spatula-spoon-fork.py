"""Spatula, spoon, fork (Lelia Twersky): her little kitchen boat. A planked wooden boat with a square
transom, a slotted spatula for the mast and sail, a "13" pennant clipped to the blade, a wooden
spoon worked as an oar from a rowlock by the bow, a fork hung off the transom as the rudder, and the
slatted crate and cleat on the raised foredeck. Bow toward +X, so the front three-quarter view
matches her drawing (stern and starboard side)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()

# ---------- local helpers (kept in this file so the script stands alone) ----------

def sweep(path, profile, name='sweep', material=None, cap=True, closed=False, smooth=40, up=None):
    """Sweep a closed 2D profile [(u, v)] along a 3D polyline (parallel-transported frames).
    u runs along the frame normal, v along the binormal. `up` seeds the first normal's reference."""
    P = [Vector(p) for p in path]
    n = len(P)
    T = []
    for i in range(n):
        if closed:
            a, b = P[i - 1], P[(i + 1) % n]
        else:
            a, b = P[max(i - 1, 0)], P[min(i + 1, n - 1)]
        T.append((b - a).normalized())
    ref = Vector(up) if up else (Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((0, 1, 0)))
    N = [T[0].cross(ref).normalized()]
    for i in range(1, n):
        v = N[-1] - T[i] * N[-1].dot(T[i]); N.append(v.normalized())
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for p, t, nn in zip(P, T, N):
        b = t.cross(nn)
        rings.append([bm.verts.new(p + nn * u + b * v) for u, v in profile])
    k = len(profile)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for r0, r1 in pairs:
        for j in range(k):
            bm.faces.new((r0[j], r0[(j + 1) % k], r1[(j + 1) % k], r1[j]))
    if cap and not closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, smooth=smooth)


def loft(rings, name='loft', material=None, cap_start=True, cap_end=True, smooth=50, uvs=None):
    """Skin a list of closed rings (each a list of 3D points, same count) into one mesh.
    uvs: optional uvs[i][j] = (u, v) per ring point, plus u for the seam via a duplicated column (handled here)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    k = len(rings[0])
    V = [[bm.verts.new(p) for p in r] + [None] for r in rings]
    for r in V:
        r[k] = bm.verts.new(r[0].co)  # seam duplicate, merged below (UVs live on loops, so they survive)
    uv_layer = bm.loops.layers.uv.new('UVMap') if uvs else None
    for i in range(len(V) - 1):
        for j in range(k):
            f = bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
            if uv_layer:
                def U(ii, jj):
                    if jj == k:
                        u, v = uvs[ii][0]; return (u + 1.0, v)
                    return uvs[ii][jj]
                for l, t in zip(f.loops, (U(i, j), U(i, j + 1), U(i + 1, j + 1), U(i + 1, j))):
                    l[uv_layer].uv = t
    if cap_start:
        bm.faces.new(list(reversed(V[0][:k])))
    if cap_end:
        bm.faces.new(V[-1][:k])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material, smooth=smooth)


def rounded_rect(w, h, r, n=4, support=0.0, cx=0.0, cy=0.0):
    """Rounded rectangle, CCW. `support` adds a point that far along each flat side next to every corner,
    so smooth shading stays on the corners and the flat sides read flat."""
    pts = []
    for ox, oy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        a0r, a1r = math.radians(a0), math.radians(a0 + 90)
        if support:
            pts.append((cx + ox + r * math.cos(a0r) + support * math.sin(a0r), cy + oy + r * math.sin(a0r) - support * math.cos(a0r)))
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + ox + r * math.cos(a), cy + oy + r * math.sin(a)))
        if support:
            pts.append((cx + ox + r * math.cos(a1r) - support * math.sin(a1r), cy + oy + r * math.sin(a1r) + support * math.cos(a1r)))
    return pts


def resample(pts, n, closed=False):
    """Resample a polyline to n points evenly by arc length."""
    P = [Vector(p) for p in pts]
    if closed:
        P = P + [P[0]]
    d = [0.0]
    for a, b in zip(P, P[1:]):
        d.append(d[-1] + (b - a).length)
    out = []
    m = n if closed else n - 1
    for i in range(n):
        t = d[-1] * i / m
        j = 1
        while j < len(d) - 1 and d[j] < t:
            j += 1
        s = (t - d[j - 1]) / max(d[j] - d[j - 1], 1e-12)
        out.append(P[j - 1].lerp(P[j], min(max(s, 0), 1)))
    return out


def weighted_normals(o):
    m = o.modifiers.new('wn', 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 100
    return o


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def apply_all(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def text_obj(s, size, depth, offset=0.0, name='txt', align='CENTER', spacing=1.0):
    """Flat lettering in the XY plane, extruded from z=0 to z=depth."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.align_x = align; cu.align_y = 'CENTER'; cu.offset = offset; cu.space_character = spacing
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    o.data.transform(Matrix.Translation((0, 0, depth / 2)))
    return o


def bool_op(target, cutter, op='DIFFERENCE', transfer=False):
    """Boolean like kit.boolean, optionally giving the cut faces the cutter's material."""
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    if transfer:
        md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def mirrored_copy(o, name=None):
    """A copy mirrored across x = 0 (mesh data flipped, normals fixed)."""
    c = o.copy(); c.data = o.data.copy(); bpy.context.collection.objects.link(c)
    c.data.transform(o.matrix_world); c.matrix_world = Matrix.Identity(4)
    c.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    c.data.flip_normals()
    if name:
        c.name = name
    return c


def pil_texture(name, code, size=1024):
    """Draw a texture with the system Python + PIL (Blender's Python has no PIL), then pack it into the .blend.
    `code` gets `img` (RGB, size x size), `d` (ImageDraw), `S` (size) and `font(px)`."""
    import subprocess, tempfile
    path = os.path.join(tempfile.mkdtemp(), name + '.png')
    prog = ("import sys\nfrom PIL import Image, ImageDraw, ImageFont, ImageFilter\nS=int(sys.argv[2])\n"
            "img=Image.new('RGB',(S,S),(128,128,128)); d=ImageDraw.Draw(img)\n"
            "def font(px, bold=True):\n"
            "    for f in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',\n"
            "              '/System/Library/Fonts/Helvetica.ttc', '/Library/Fonts/Arial.ttf'):\n"
            "        try:\n            return ImageFont.truetype(f, px)\n        except Exception:\n            pass\n"
            "    return ImageFont.load_default()\n" + code + "\nimg.save(sys.argv[1])\n")
    subprocess.run(['/usr/bin/env', 'python3', '-c', prog, path, str(size)], check=True)
    im = bpy.data.images.load(path); im.pack(); im.name = name
    return im


def uv_quad(corners, uvs, name, material):
    """A single flat face through `corners` (3D) with the given per-corner uvs."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new(c) for c in corners]
    f = bm.faces.new(vs)
    lay = bm.loops.layers.uv.new('UVMap')
    for l, uv in zip(f.loops, uvs):
        l[lay].uv = uv
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o


def tex_mat(image, rough=0.5, metal=0.0, name='tex'):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = image
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m

# ---------- materials ----------
TOPSIDE = kit.mat('teal', rough=0.42, name='hull_paint')
BOTTOM = kit.mat('red', rough=0.5, name='bottom_paint')
DECK = kit.mat('honey', rough=0.6, name='deck_planks')
CAP = kit.mat('oak', rough=0.55, name='gunwale_wood')
DARKWOOD = kit.mat('walnut', rough=0.6, name='dark_wood')
STEEL = kit.mat('chrome', rough=0.25, metal=1.0, name='stainless')
BRASS = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
SPOON = kit.mat('#c4914f', rough=0.6, name='spoon_wood')
CLOTH = kit.mat('paper', rough=0.8, name='pennant')
INK = kit.mat('black', rough=0.6, name='ink')

L = 0.5
XS, XB = -0.25, 0.25     # stern (transom) and bow


def half_w(x):
    if x <= -0.05:
        return 0.105 - 0.012 * ((x + 0.05) / 0.2) ** 2
    t = (x + 0.05) / (XB - (-0.05))
    return 0.105 * max(0.0, 1 - t ** 2) ** 0.62


def sheer(x):
    return 0.105 + 0.04 * max(0.0, x / XB) ** 2


def keel(x):
    return 0.065 * max(0.0, (x - 0.08) / (XB - 0.08)) ** 2


def section(x, inset=0.0, n=29):
    """Closed hull section at x: round-bilged V from the starboard sheer, under the keel, up to port,
    then straight back across the top."""
    w = max(half_w(x) - inset, 0.0015)
    zt, zk = sheer(x), keel(x) + inset
    pts = []
    for i in range(n):
        a = math.pi * i / (n - 1)            # 0 = starboard sheer, pi = port sheer
        s = math.cos(a)                      # +1 .. -1 across the beam
        y = -w * s
        depth = zt - zk
        # flat-ish sides that turn under into a shallow V
        z = zk + depth * (1 - math.sin(a) ** 1.6)
        pts.append(Vector((x, y, min(z, zt))))
    for i in range(1, 5):
        t = i / 5
        pts.append(Vector((x, w - 2 * w * t, zt)))
    return pts


stations = [XS + (XB - 0.004 - XS) * (i / 30) ** 0.85 for i in range(31)]
hull = loft([section(x) for x in stations], name='hull', material=TOPSIDE, smooth=50)
hull.data.materials.append(BOTTOM)

# cockpit well, leaving a 12 mm wall, the transom and a raised foredeck
COCK_X1, FLOOR = 0.12, 0.074
plan = []
xs = [XS + 0.012 + (COCK_X1 - XS - 0.012) * i / 24 for i in range(25)]
plan = [(x, -(half_w(x) - 0.013)) for x in xs] + [(x, half_w(x) - 0.013) for x in reversed(xs)]
cut = kit.extrude(plan, 0.5, at=(0, 0, FLOOR), name='cockpit')
kit.boolean(hull, cut)
# paint the bottom below the waterline
for poly in hull.data.polygons:
    c = poly.center
    if c.z < 0.034 + keel(c.x) and poly.normal.z < 0.95:
        poly.material_index = 1
weighted_normals(hull)

# gunwale caps along both sheers and across the transom, a rubbing strake below
for s in (-1, 1):
    pts = [Vector((x, s * (half_w(x) - 0.004), sheer(x) + 0.003)) for x in [XS + (XB - 0.02 - XS) * i / 40 for i in range(41)]]
    sweep(pts, rounded_rect(0.007, 0.017, 0.003, n=2), name='gunwale', material=CAP, up=(0, 0, 1))
    rs = [Vector((x, s * (half_w(x) + 0.0015), sheer(x) - 0.022)) for x in [XS + 0.002 + (XB - 0.035 - XS) * i / 40 for i in range(41)]]
    sweep(rs, rounded_rect(0.008, 0.006, 0.002, n=2), name='rub_strake', material=CAP, up=(0, 0, 1))
kit.box((0.016, 2 * half_w(XS) - 0.004, 0.007), at=(XS + 0.006, 0, sheer(XS) + 0.003), material=CAP, bevel=0.002, name='transom_cap')
# stem band at the bow
kit.sphere(0.008, at=(XB - 0.004, 0, sheer(XB) - 0.004), material=BRASS, segs=16, rings=8, name='stem_cap')

# deck planks in the cockpit, each trimmed to fit
PW, GAP = 0.021, 0.0035
n = 7
for i in range(n):
    yc = (i - (n - 1) / 2) * (PW + GAP)
    x1 = COCK_X1 - 0.002
    while x1 > XS and half_w(x1) - 0.016 < abs(yc) + PW / 2:
        x1 -= 0.002
    x0 = XS + 0.013
    kit.box((x1 - x0, PW, 0.005), at=((x0 + x1) / 2, yc, FLOOR + 0.0025), material=DECK, bevel=0.0012, name='plank')

# raised foredeck: a slatted crate and a cleat
CX = 0.175
cz = sheer(CX)
crate = kit.box((0.07, 0.085, 0.055), at=(CX, 0.0, cz + 0.0275), material=CAP, bevel=0.003, name='crate')
for k in range(3):
    kit.box((0.019, 0.089, 0.006), at=(CX - 0.023 + k * 0.023, 0.0, cz + 0.058), material=DARKWOOD, bevel=0.0015, name='crate_slat')
for s in (-1, 1):
    kit.box((0.074, 0.004, 0.012), at=(CX, s * 0.0435, cz + 0.044), material=DARKWOOD, bevel=0.001, name='crate_band')
# cleat on the port side of the crate
kit.box((0.012, 0.012, 0.012), at=(CX - 0.01, 0.06, cz + 0.006), material=BRASS, bevel=0.002, name='cleat_base')
kit.cyl(0.0045, 0.05, at=(CX - 0.01, 0.06, cz + 0.014), rot=(0, 90, 0), material=BRASS, bevel=0.0015, verts=12, name='cleat_horn')

# ---------- spatula: walnut handle for the mast, slotted steel blade for the sail ----------
MX = -0.07
kit.box((0.05, 0.05, 0.012), at=(MX, 0, FLOOR + 0.011), material=DARKWOOD, bevel=0.003, name='mast_step')
H0, H1 = FLOOR + 0.01, FLOOR + 0.24
handle = kit.box((0.024, 0.013, H1 - H0), at=(MX, 0, (H0 + H1) / 2), material=DARKWOOD, bevel=0.005, segments=3, name='spatula_handle')
for z in (H1 - 0.03, H1 - 0.075):
    kit.cyl(0.0035, 0.016, at=(MX, 0, z), rot=(90, 0, 0), material=BRASS, verts=12, name='rivet')
# tapering steel neck from the handle into the blade
neck = kit.extrude([(-0.008, 0.0), (0.008, 0.0), (0.016, 0.07), (-0.016, 0.07)], 0.003, name='neck')
neck.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
neck.location = (MX, 0.0015, H1 - 0.045)
kit.finish(neck, STEEL, bevel=0.0008, smooth=0)
BW, BH = 0.135, 0.155
BZ = H1 + 0.02
blade_poly = []
for x, y in rounded_rect(BW, BH, 0.028, n=6):
    blade_poly.append((x, y))
blade = kit.extrude(blade_poly, 0.003, name='spatula_blade')
for k in range(4):
    sx = (k - 1.5) * 0.026
    slot = []
    for i in range(16):
        a = math.tau * i / 16
        slot.append((sx + 0.006 * math.cos(a), (0.04 if math.sin(a) > 0 else -0.04) + 0.006 * math.sin(a)))
    c = kit.extrude(slot, 0.02, at=(0, 0.012, -0.01), name='slot')
    kit.boolean(blade, c)
blade.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
blade.location = (MX, 0.0015, BZ + BH / 2)
kit.finish(blade, STEEL, bevel=0.0009, smooth=0)

# pennant: a small brass pole clipped to the bow edge of the blade, "13" on both faces
PX = MX + BW / 2 + 0.008
kit.cyl(0.0028, 0.12, at=(PX, 0, BZ + BH - 0.02), material=BRASS, verts=12, name='flag_pole')
kit.sphere(0.0055, at=(PX, 0, BZ + BH + 0.042), material=BRASS, segs=12, rings=6, name='flag_finial')
for z in (BZ + BH * 0.55, BZ + BH * 0.85):
    kit.box((0.014, 0.008, 0.008), at=(PX - 0.006, 0, z), material=BRASS, bevel=0.0015, name='flag_clip')
pen = kit.extrude([(0, -0.032), (0.15, 0.0), (0, 0.032)], 0.0016, name='pennant')
pen.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
pen.location = (PX + 0.002, 0.0008, BZ + BH + 0.01)
kit.finish(pen, CLOTH, bevel=0.0004, smooth=0)
for s in (-1, 1):
    t = text_obj('13', 0.044, 0.0006, offset=0.0012, name='pennant_13')
    if s > 0:
        t.data.transform(Matrix.Rotation(math.radians(180), 4, 'Z'))
    t.data.transform(Matrix.Rotation(math.radians(90 if s < 0 else -90), 4, 'X'))
    t.location = (PX + 0.045, s * 0.0008, BZ + BH + 0.01)
    t.data.materials.append(INK)

# ---------- spoon oar from a rowlock on the starboard gunwale ----------
OX = 0.11
piv = Vector((OX, -(half_w(OX) - 0.004), sheer(OX) + 0.014))
kit.cyl(0.004, 0.02, at=piv + Vector((0, 0, -0.008)), material=BRASS, verts=12, name='rowlock_pin')
kit.torus(0.009, 0.0025, at=piv + Vector((0, 0, 0.003)), rot=(90, 0, 0), material=BRASS, major=20, minor=8, name='rowlock')
d = Vector((-0.28, -0.85, 0.0))
d.z = -(piv.z - 0.006) / 0.36
d.normalize()
for _ in range(3):   # settle the angle so the bowl just touches the waterline
    tip = piv + d * 0.36
    d.z -= (tip.z - 0.004) / 0.4; d.normalize()
inner = piv - d * 0.05
neck_end = piv + d * 0.26
handle = sweep([inner, piv, neck_end], [(0.0065 * math.cos(a), 0.0055 * math.sin(a)) for a in [i * math.tau / 12 for i in range(12)]],
               name='spoon_handle', material=SPOON)
bowl = kit.sphere(1.0, scale=(0.034, 0.052, 0.012), segs=32, rings=16, name='spoon_bowl')
hollow = kit.sphere(1.0, at=(0, 0, 0.008), scale=(0.029, 0.046, 0.011), segs=32, rings=16, name='hollow')
kit.boolean(bowl, hollow)
kit.finish(bowl, SPOON, smooth=40)
bc = piv + d * (0.26 + 0.046)
up = Vector((0, 0, 1))
side = d.cross(up).normalized(); nrm = side.cross(d).normalized()
bowl.matrix_world = Matrix.Translation(bc) @ Matrix((side, d, nrm)).transposed().to_4x4()

# ---------- fork rudder hung off the transom ----------
gz = 0.055
for z in (gz - 0.018, gz + 0.018):
    kit.box((0.012, 0.03, 0.008), at=(XS - 0.004, 0, z), material=BRASS, bevel=0.0015, name='gudgeon')
kit.cyl(0.0035, 0.05, at=(XS - 0.012, 0, gz), material=BRASS, verts=12, name='pintle')
outline = [(0.0, -0.0075), (0.14, -0.0075)]
TW, TG = 0.0072, 0.0038           # tine width and gap
ys = [-0.021 + k * (TW + TG) for k in range(4)]
outline += [(0.175, -0.0215)]
for k, y0 in enumerate(ys):
    outline += [(0.245, y0), (0.245, y0 + TW)]
    if k < 3:
        outline += [(0.188, y0 + TW + 0.0004), (0.188, y0 + TW + TG - 0.0004)]
outline += [(0.175, 0.0215), (0.14, 0.0075), (0.0, 0.0075), (-0.009, 0.0)]
fork = kit.extrude(outline, 0.0035, name='fork')
fork.data.transform(Matrix.Translation((0, 0, -0.00175)))
kit.finish(fork, STEEL, bevel=0.0008, smooth=0)
fd = Vector((-0.86, 0.06, 0.0)); fd.z = -(gz - 0.004) / 0.245; fd.normalize()
for _ in range(3):
    tip = Vector((XS - 0.012, 0, gz)) + fd * 0.245
    fd.z -= (tip.z - 0.004) / 0.3; fd.normalize()
fside = Vector((0, 0, 1)).cross(fd).normalized(); fup = fd.cross(fside).normalized()
# fork lies in the vertical plane through fd: its width runs up and down like a rudder blade
fork.matrix_world = Matrix.Translation(Vector((XS - 0.012, 0, gz))) @ Matrix((fd, fup, fside)).transposed().to_4x4()
kit.box((0.022, 0.012, 0.016), at=(XS - 0.016, 0, gz), material=BRASS, bevel=0.002, name='rudder_clamp')

kit.export('spatula-spoon-fork')
