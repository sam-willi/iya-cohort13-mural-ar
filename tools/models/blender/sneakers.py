"""Running shoes (Adityavardhan Singh): a pair side by side, as in his drawing. Chunky midsole that
rises round the heel, rubber outsole wrapping up over the toe, a high padded collar, tongue standing
proud of the laces, crisscross laces through two eyestays, and the sweeping side overlays he drew
(one band from the heel up to the laces, one from the forefoot), plus toe cap and heel counter."""
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


def tex_mat(image, rough=0.5, metal=0.0, name='tex'):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = image
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


# ---------- materials ----------
MIDSOLE_C = '#f1ece2'
OUTSOLE = kit.mat('#2b2725', rough=0.82, name='outsole_rubber')
LINING = kit.mat('#26585f', rough=0.8, name='lining')
INSOLE = kit.mat('#d9d0c0', rough=0.8, name='insole')
LACE = kit.mat('white', rough=0.75, name='lace')
EYELET = kit.mat('gunmetal', rough=0.35, metal=0.85, name='eyelet')
TONGUE = kit.mat('cream', rough=0.75, name='tongue')
COLLAR = kit.mat('cream', rough=0.8, name='collar_pad')
TAB = kit.mat('orange', rough=0.6, name='heel_tab')

# ---------- footprint (right shoe; toe toward -Y, lateral side toward -X) ----------
L = 0.29


def interp(keys, p):
    for (p0, v0), (p1, v1) in zip(keys, keys[1:]):
        if p <= p1:
            t = (p - p0) / (p1 - p0); t = (1 - math.cos(math.pi * t)) / 2
            return v0 + (v1 - v0) * t
    return keys[-1][1]


LAT = [(0, 0.031), (0.15, 0.035), (0.35, 0.034), (0.55, 0.044), (0.7, 0.049), (0.85, 0.045), (1.0, 0.03)]
MED = [(0, 0.031), (0.15, 0.034), (0.35, 0.029), (0.55, 0.040), (0.7, 0.048), (0.85, 0.046), (1.0, 0.032)]
NS = 40
PS = [(1 - math.cos(math.pi * i / NS)) / 2 for i in range(NS + 1)]


def endf(p):
    return math.sqrt(max(0.0, 1 - abs(2 * p - 1) ** 6))


def cline(p):
    return 0.006 * p * p


def outline(delta):
    """Footprint inset by delta: list of (x, y, p). Lateral heel->toe, then medial toe->heel."""
    yh, yt = L / 2 - delta, -L / 2 + delta
    pts = []
    for p in PS:
        w = max(interp(LAT, p) * endf(p) - delta, 0)
        pts.append((cline(p) - w, yh + (yt - yh) * p, p))
    for p in reversed(PS[1:-1]):
        w = max(interp(MED, p) * endf(p) - delta, 0)
        pts.append((cline(p) + w, yh + (yt - yh) * p, p))
    return pts


def rocker(p):
    if p < 0.12:
        return 0.007 * ((0.12 - p) / 0.12) ** 2
    if p > 0.62:
        return 0.02 * ((p - 0.62) / 0.38) ** 2
    return 0.0


MS = [(0, 0.047), (0.1, 0.046), (0.22, 0.038), (0.4, 0.031), (0.6, 0.027), (0.8, 0.023), (1.0, 0.02)]


def ms_top(p):
    return rocker(p) + interp(MS, p)


def arc_u(pts):
    d = [0.0]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        d.append(d[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return [x / d[-1] for x in d[:-1]]


def sole_rings(spec):
    """spec: list of (delta, z(p)) -> rings."""
    rings = []
    for delta, zf in spec:
        rings.append([Vector((x, y, zf(p))) for x, y, p in outline(delta)])
    return rings


U0 = arc_u(outline(0.0))

# ---------- textures ----------
P_LAT = [(p, u) for (x, y, p), u in zip(outline(0.0035), arc_u(outline(0.0035))) if u <= 0.5 + 1e-9]
mid_img = pil_texture('midsole', """
img.paste((241, 236, 226), (0, 0, S, S))
import math
# two-tone midsole: a sculpted line that rides high round the heel and dips under the arch and toe
line = [(x, S * (1 - (0.52 + 0.17 * math.cos(x / S * math.tau)))) for x in range(0, S + 1, 4)]
d.polygon(line + [(S, S), (0, S)], fill=(214, 207, 195))
d.line(line, fill=(168, 160, 148), width=6)
""", size=512)
MIDSOLE = tex_mat(mid_img, rough=0.6, name='midsole')

upper_img = pil_texture('upper', """
import math
P = P_TABLE
def U(p, med=False):
    for (p0, u0), (p1, u1) in zip(P, P[1:]):
        if p <= p1:
            t = (p - p0) / max(p1 - p0, 1e-9); u = u0 + (u1 - u0) * t
            return (1 - u if med else u)
    return 0.5
def XY(p, v, med=False):
    return (U(p, med) * S, (1 - v) * S)
base = (143, 195, 220)
img.paste(base, (0, 0, S, S))
# engineered-mesh texture: fine staggered holes
for j in range(0, S, 8):
    for i in range(0, S, 8):
        o = 4 if (j // 8) % 2 else 0
        d.ellipse([i + o, j, i + o + 3, j + 2], fill=(116, 166, 192))
GREY = (239, 227, 200); ORANGE = (217, 102, 42); DARK = (60, 64, 71); TONG = (239, 227, 200)
def poly_pv(pv, med, fill):
    d.polygon([XY(p, v, med) for p, v in pv], fill=fill)
def stitch_pv(pv, med, col=(120, 110, 100)):
    pts = [XY(p, v, med) for p, v in pv]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(int(math.hypot(x1 - x0, y1 - y0) / 7), 1)
        for k in range(0, n, 2):
            a = k / n; b = min((k + 1) / n, 1)
            d.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill=col, width=2)
def curve(p0, v0, p1, v1, bend, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append((p0 + (p1 - p0) * t, v0 + (v1 - v0) * t + bend * math.sin(math.pi * t)))
    return out
for med in (False, True):
    # heel counter
    top = [(p, 0.78 - 3.2 * p * p) for p in [i * 0.012 for i in range(21)]]
    poly_pv([(0.0, 0.0)] + top + [(0.24, 0.0)], med, GREY)
    stitch_pv([(p, v - 0.03) for p, v in top], med)
    # toe cap / mudguard
    tc = [(0.8 + 0.2 * t, 0.16 + 0.84 * t ** 2.2) for t in [i / 24 for i in range(25)]]
    poly_pv([(0.8, 0.0)] + tc + [(1.0, 0.0)], med, GREY)
    stitch_pv([(p - 0.008, v) for p, v in tc], med)
    # band from the heel sweeping up to the laces
    lo = curve(0.10, 0.06, 0.47, 0.84, -0.10)
    hi = curve(0.05, 0.24, 0.41, 0.86, -0.08)
    poly_pv(lo + hi[::-1], med, ORANGE)
    stitch_pv([(p, v + 0.02) for p, v in lo], med, DARK); stitch_pv([(p, v - 0.02) for p, v in hi], med, DARK)
    # band from the forefoot up to the laces
    lo2 = curve(0.80, 0.05, 0.63, 0.84, 0.05)
    hi2 = curve(0.72, 0.05, 0.56, 0.84, 0.05)
    poly_pv(lo2 + hi2[::-1], med, ORANGE)
    stitch_pv(lo2, med, DARK); stitch_pv(hi2, med, DARK)
    # eyestay along the throat, tongue colour between
    eye = [(0.40, 0.80), (0.73, 0.80), (0.73, 0.93), (0.40, 0.93)]
    poly_pv(eye, med, (60, 64, 71))
    stitch_pv([(0.40, 0.815), (0.73, 0.815)], med, (150, 150, 150))
    poly_pv([(0.40, 0.93), (0.74, 0.93), (0.74, 1.0), (0.40, 1.0)], med, TONG)
""".replace('P_TABLE', repr([(round(p, 5), round(u, 5)) for p, u in P_LAT])), size=1024)
UPPER = tex_mat(upper_img, rough=0.7, name='upper')

# ---------- build one (right) shoe ----------
parts = []

# outsole: rubber, wraps up over the toe
def toebump(p):
    return 0.017 * max(0.0, (p - 0.86) / 0.14) ** 1.6

out_r = sole_rings([(0.0035, lambda p: rocker(p)), (0.0008, lambda p: rocker(p) + 0.0014),
                    (-0.0004, lambda p: rocker(p) + 0.005), (-0.0004, lambda p: rocker(p) + 0.0105 + toebump(p)),
                    (0.0015, lambda p: rocker(p) + 0.0115 + toebump(p))])
parts.append(loft(out_r, name='outsole', material=OUTSOLE, smooth=45))

# midsole
spec = [(0.0015, lambda p: rocker(p) + 0.0092), (-0.0026, lambda p: rocker(p) + 0.0116),
        (-0.0032, lambda p: rocker(p) + 0.017), (-0.0028, lambda p: ms_top(p) - 0.007),
        (-0.0012, lambda p: ms_top(p) - 0.0018), (0.0025, lambda p: ms_top(p))]
mid_r = sole_rings(spec)
uv0 = arc_u(outline(0.0))
mid_uv = [[(u, k / (len(spec) - 1)) for u in uv0] for k in range(len(spec))]
parts.append(loft(mid_r, name='midsole', material=MIDSOLE, smooth=45, uvs=mid_uv))

# upper: from inside the midsole, each point rises on a squared-off quarter ellipse to a ridge line
HT = [(0, 0.112), (0.08, 0.114), (0.2, 0.104), (0.3, 0.097), (0.4, 0.1), (0.5, 0.097), (0.6, 0.087), (0.72, 0.071),
      (0.85, 0.058), (1.0, 0.05)]
MEXP = [(0, 2.8), (0.45, 2.4), (0.7, 1.8), (1.0, 1.5)]
base = outline(0.0038)
ub_u = arc_u(base)
K = 16
rings, uvs = [], []
for k in range(K + 1):
    th = math.pi / 2 * k / K
    ring, ruv = [], []
    for (xb, yb, p), u in zip(base, ub_u):
        zb = ms_top(p) - 0.003
        yr = (L / 2 - 0.035) - p * (L - 0.035 - 0.05)
        xr = cline(p)
        h = rocker(p) + interp(HT, p)
        m = interp(MEXP, p)
        f = (1 - math.cos(th)) ** m
        ring.append(Vector((xb + (xr - xb) * f, yb + (yr - yb) * f, zb + (h - zb) * math.sin(th))))
        ruv.append((u, k / K))
    rings.append(ring); uvs.append(ruv)
upper = loft(rings, name='upper', material=UPPER, cap_end=False, smooth=55, uvs=uvs)
upper.data.materials.append(LINING)

# foot opening: an elliptical well, its walls and floor in the lining colour
OY, OAY, OCX = L / 2 - 0.068, 0.05, -0.0015


def opening(t, grow=0.0):
    """Egg-shaped foot opening: wider round the heel (+Y), narrower toward the laces."""
    a = 0.0205 + 0.0035 * math.sin(t) + grow
    return (OCX + a * math.cos(t), OY + (OAY + grow) * math.sin(t))


cut = kit.extrude([opening(i * math.tau / 64) for i in range(64)], 0.3, name='opening')
cut.location = (0, 0, 0.049); cut.rotation_euler = (math.radians(5), 0, 0)
kit.finish(cut, LINING, smooth=0)
bool_op(upper, cut, transfer=True)
parts.append(upper)
# insole on the floor of the well
ins = kit.extrude([opening(i * math.tau / 48, -0.0015) for i in range(48)], 0.003, name='insole')
ins.location = (0, 0, 0.0485); ins.rotation_euler = (math.radians(5), 0, 0)
parts.append(kit.finish(ins, INSOLE, bevel=0.001, smooth=30))
bpy.context.view_layer.update()


def surface(x, y, from_z=0.4):
    hit, loc, nor, idx = upper.ray_cast(Vector((x, y, from_z)), Vector((0, 0, -1)))
    return (loc, nor) if hit else (None, None)


# padded collar rolled round the back and sides of the rim (the front of the opening is the tongue's)
rim = []
for i in range(73):
    t = math.radians(-20) + math.radians(220) * i / 72   # round the heel end (90 deg) from side to side
    x, y = opening(t, 0.0035)
    loc, nor = surface(x, y)
    if loc is None:
        continue
    sink = 0.009 * max(0.0, 1 - min(i, 72 - i) / 10) ** 2   # the ends dive into the wall
    x, y = opening(t, 0.0012)
    rim.append(Vector((x, y, loc.z - 0.0015 - sink)))
roll = sweep(resample(rim, 80), [(0.0052 * math.cos(t), 0.0052 * math.sin(t)) for t in [i * math.tau / 12 for i in range(12)]],
             name='collar', material=COLLAR, up=(0, 0, 1))
parts.append(roll)

# tongue standing up out of the front of the opening
yf = OY - OAY
tpath = [(cline(0.42), yf + 0.016, 0.05), (cline(0.42), yf + 0.011, 0.08), (cline(0.42), yf + 0.001, 0.1), (cline(0.42), yf - 0.01, 0.108)]
tg = sweep(resample(tpath, 14), rounded_rect(0.008, 0.036, 0.0036, n=3), name='tongue', material=TONGUE, up=(1, 0, 0))
parts.append(tg)
# tongue top: a soft rounded cap
parts.append(kit.sphere(0.018, at=(cline(0.42), yf - 0.01, 0.108), scale=(1, 0.22, 0.26), material=TONGUE, segs=24, rings=12, name='tongue_cap'))

# eyelets and laces
EP = [0.435 + 0.049 * i for i in range(6)]
eyes = {-1: [], 1: []}
for p in EP:
    y = L / 2 - p * L
    for s in (-1, 1):
        x = cline(p) + s * 0.0175
        loc, nor = surface(x, y)
        eyes[s].append((loc, nor))
        e = kit.torus(0.0028, 0.0009, material=EYELET, major=14, minor=6, name='eyelet')
        e.location = loc + nor * 0.0004
        e.rotation_euler = nor.to_track_quat('Z', 'Y').to_euler()
        parts.append(e)


def lace(a, b, lift):
    pts = []
    for i in range(9):
        t = i / 8
        q = a.lerp(b, t)
        loc, nor = surface(q.x, q.y)
        pts.append(loc + Vector((0, 0, lift + 0.0018 * math.sin(math.pi * t))))
    return sweep(pts, [(0.0016 * math.cos(t), 0.0016 * math.sin(t)) for t in [i * math.tau / 8 for i in range(8)]],
                 name='lace', material=LACE)


for i in range(len(EP) - 1):
    parts.append(lace(eyes[-1][i][0], eyes[1][i + 1][0], 0.0022))
    parts.append(lace(eyes[1][i][0], eyes[-1][i + 1][0], 0.0034))
parts.append(lace(eyes[-1][-1][0], eyes[1][-1][0], 0.0022))
# a bow on the top pair: loops and ends lying on the laces
top = (eyes[-1][0][0] + eyes[1][0][0]) / 2 + Vector((0, 0.0, 0.004))


def on_surface(pts, lift):
    out = []
    for q in pts:
        loc, nor = surface(q.x, q.y)
        out.append(Vector((q.x, q.y, (loc.z if loc else q.z) + lift)))
    return out


for s in (-1, 1):
    loop = [top + Vector(v) for v in ((0, 0, 0), (s * 0.011, 0.005, 0), (s * 0.019, -0.001, 0), (s * 0.012, -0.007, 0), (s * 0.002, -0.002, 0))]
    parts.append(sweep(on_surface(resample(loop, 16), 0.0055), [(0.0016 * math.cos(t), 0.0016 * math.sin(t)) for t in [i * math.tau / 8 for i in range(8)]],
                       name='bow', material=LACE))
    end = [top, top + Vector((s * 0.005, -0.012, 0)), top + Vector((s * 0.008, -0.024, 0))]
    parts.append(sweep(on_surface(resample(end, 8), 0.0045), [(0.0016 * math.cos(t), 0.0016 * math.sin(t)) for t in [i * math.tau / 8 for i in range(8)]],
                       name='lace_end', material=LACE))
top = on_surface([top], 0.006)[0]
parts.append(kit.sphere(0.0034, at=top, material=LACE, segs=12, rings=6, name='knot'))

# heel pull tab on the back of the collar
hl, hn = surface(cline(0.0), L / 2 - 0.012)
tab = kit.box((0.018, 0.007, 0.022), at=(cline(0.0), L / 2 - 0.004, (hl.z if hl else 0.11) - 0.002), rot=(-10, 0, 0),
              material=TAB, bevel=0.003, segments=3, name='heel_tab')
parts.append(tab)

# ---------- the pair: mirror for the left shoe, toes turned out a touch ----------
right = [o for o in bpy.context.scene.objects if o.type == 'MESH']
left = [mirrored_copy(o, o.name + '_L') for o in right]
for objs, s, ang, dy in ((right, -1, -4, 0.012), (left, 1, 4, -0.014)):
    M = Matrix.Translation((s * 0.064, dy, 0)) @ Matrix.Rotation(math.radians(ang), 4, 'Z')
    for o in objs:
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
        o.data.transform(M)

kit.export('sneakers')
