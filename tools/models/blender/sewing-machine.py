"""Sewing machine, after Anne Pham's drawing (RV P5a).

The drawing: a vintage cast-iron machine head on a wooden base. A tall head on the left with a spool on top, an arm
whose top line swoops down and back up to the pillar on the right (second spool pin on top), a big arch underneath,
scrolls/leaves/spirals decorating the front, a round boss on the pillar, a six-spoke handwheel with curved spokes,
the needle bar and foot coming down to a square needle plate, a bed with two screw holes, and a wooden base with
carved corners.
Line-only drawing, so the colours are the classic ones: black enamel with gold decals and pinstriping, nickel
handwheel and fittings, walnut base. The decals are a painted texture laid out after hers (vine and spirals down the
pillar, scrolls along the arm, small motifs on the head), mirrored on the back. Red thread on the spool, threaded
down to the needle.
"""
import sys, os, math, json, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

kit.reset()


# ---------------------------------------------------------------- helpers (local to this script)
def fillet(pts, r, n=4, closed=False):
    m = len(pts); out = []
    for i, p in enumerate(pts):
        ri = r[i] if isinstance(r, (list, tuple)) else r
        if (not closed and i in (0, m - 1)) or not ri:
            out.append(p); continue
        P = Vector(p); A = Vector(pts[i - 1]); B = Vector(pts[(i + 1) % m])
        u = (A - P); v = (B - P); lu, lv = u.length, v.length
        u.normalize(); v.normalize()
        ang = u.angle(v, math.pi)
        if ang > math.pi - 1e-3:
            out.append(p); continue
        d = min(ri / math.tan(ang / 2), 0.48 * lu, 0.48 * lv)
        t1, t2 = P + u * d, P + v * d
        for k in range(n + 1):
            t = k / n
            q = t1 * (1 - t) ** 2 + P * 2 * (1 - t) * t + t2 * t * t
            out.append((q.x, q.y))
    return out


def inset(poly, d):
    """Offset a CCW polygon inward by d (fine for smooth, filleted outlines)."""
    out = []; m = len(poly)
    for i in range(m):
        A, P, B = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % m])
        e1 = (P - A).normalized(); e2 = (B - P).normalized()
        n1 = Vector((-e1.y, e1.x)); n2 = Vector((-e2.y, e2.x))
        nn = (n1 + n2); nn = nn.normalized() if nn.length > 1e-6 else n1
        k = max(0.5, n1.dot(nn))
        out.append(tuple(P + nn * d / k))
    return out


def bake_join(name, objs=None):
    objs = objs or [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o


def settle(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    o.data.transform(Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
    return o


def rod(a, b, r, material=None, verts=24, bevel=0.0, name='rod'):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=(a + b) / 2, material=material, verts=verts, bevel=bevel, name=name)
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


def tex_mat(name, img, rough=0.45, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img
    uvn = m.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
    m.node_tree.links.new(uvn.outputs['UV'], t.inputs['Vector'])
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


def srgb_lin(c):
    return [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c]


def kit_hex(h):
    h = kit.PALETTE.get(h, h).lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def wood_image(name, light, dark, seed=3, n=512, lines=70):
    import numpy as np
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, n)[:, None]; u = np.linspace(0, 1, n)[None, :]
    warp = 0.006 * np.sin(u * math.tau * 1.3 + 0.7) + 0.003 * np.sin(u * math.tau * 3.7 + 2.0)
    phase = (v + warp) * lines + 1.5 * np.sin(v * math.tau * 2 + 1.0) + 0.8 * np.sin(v * math.tau * 5 + 0.3)
    g = (0.5 + 0.5 * np.sin(phase * math.tau)) ** 4
    streak = np.convolve(rng.normal(0, 1, n), np.ones(9) / 9, mode='same')[:, None] * 0.25
    t = np.clip(0.38 * g + 0.22 + streak * 0.8 + rng.normal(0, 0.03, (n, n)), 0, 1)
    L = np.array(srgb_lin(kit_hex(light))); D = np.array(srgb_lin(kit_hex(dark)))
    rgb = L[None, None, :] * (1 - t[..., None]) + D[None, None, :] * t[..., None]
    rgba = np.concatenate([rgb, np.ones((n, n, 1))], axis=2).astype(np.float32)
    img = bpy.data.images.new(name, n, n, alpha=False)
    img.pixels.foreach_set(rgba.ravel()); img.pack()
    return img


def box_uv(o, scale=1.0, front=None):
    """Apply modifiers, then project UVs per face along its dominant axis."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    me = o.data
    lay = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv = (co.x, co.y) if ax == 2 else (co.x, co.z) if ax == 1 else (co.y, co.z)
            lay.data[li].uv = (uv[0] * scale + 0.5, uv[1] * scale + 0.5)
    return o


PAINTER = r'''
import sys, json
from PIL import Image, ImageDraw
spec = json.load(open(sys.argv[1])); S = 2
W, H = spec["size"]
im = Image.new("RGB", (W * S, H * S), tuple(spec["bg"]))
d = ImageDraw.Draw(im)
for it in spec["items"]:
    col = tuple(it["color"])
    if it["kind"] == "line":
        pts = [(x * S, y * S) for x, y in it["pts"]]
        d.line(pts, fill=col, width=max(1, int(it["width"] * S)), joint="curve")
        r = it["width"] * S / 2
        for x, y in (pts[0], pts[-1]):
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    elif it["kind"] == "poly":
        d.polygon([(x * S, y * S) for x, y in it["pts"]], fill=col)
    elif it["kind"] == "dot":
        x, y, r = it["x"] * S, it["y"] * S, it["r"] * S
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
im = im.resize((W, H), Image.LANCZOS)
im.save(sys.argv[2])
'''


def paint(spec, name):
    tmp = tempfile.mkdtemp(prefix='sewdecal')
    js = os.path.join(tmp, 'spec.json'); png = os.path.join(tmp, name + '.png')
    json.dump(spec, open(js, 'w'))
    subprocess.run(['/usr/bin/env', 'python3', '-c', PAINTER, js, png], check=True)
    img = bpy.data.images.load(png); img.pack()
    return img


# ---------------------------------------------------------------- materials
ENAMEL_HEX = '#141312'
NICKEL = kit.mat('#cfd0cf', rough=0.25, metal=0.85, name='nickel')
DARK = kit.mat('#2a2826', rough=0.4, name='dark_steel')
THREAD_R = kit.mat('cardinal', rough=0.7, name='thread_red')
THREAD_C = kit.mat('teal', rough=0.7, name='thread_teal')
SPOOL = kit.mat('#d8b98a', rough=0.6, name='spool_wood')
ENAMEL = kit.mat(ENAMEL_HEX, rough=0.25, name='enamel')
GOLD = (201, 160, 74)

# ---------------------------------------------------------------- wooden base with carved corners, cast bed on top
BW, BD, BH = 0.47, 0.27, 0.050
c = 0.024
base_poly = []
for sx, sy, start in ((1, -1, 180), (1, 1, 270), (-1, 1, 360), (-1, -1, 90)):   # CCW; a cove bitten out of each corner
    cx, cy = sx * BW / 2, sy * BD / 2
    for k in range(9):
        t = math.radians(start - 90 * k / 8)
        base_poly.append((cx + c * math.cos(t), cy + c * math.sin(t)))
WOOD = tex_mat('walnut', wood_image('walnut_grain', '#6d4528', '#3f2514'), rough=0.5)
base = kit.extrude(base_poly, BH, material=WOOD, bevel=0.004, segments=2, name='base')
box_uv(base, 1.4)
# a moulded lip under the bed
lip = kit.extrude(fillet([(-0.222, -0.112), (0.222, -0.112), (0.222, 0.112), (-0.222, 0.112)], 0.02, n=4, closed=True), 0.008,
                  at=(0, 0, BH - 0.001), material=WOOD, bevel=0.003, name='lip')
box_uv(lip, 1.4)
BED_Z = BH + 0.007
BED_T = 0.026
bed = kit.extrude(fillet([(-0.215, -0.104), (0.215, -0.104), (0.215, 0.104), (-0.215, 0.104)], 0.018, n=5, closed=True), BED_T,
                  at=(0, 0, BED_Z), material=ENAMEL, bevel=0.004, segments=2, name='bed')
BT = BED_Z + BED_T            # top of the bed
for x, y in ((-0.192, -0.080), (0.192, -0.080)):           # the two holes in the drawing: hinge-screw bosses
    kit.cyl(0.0085, 0.003, at=(x, y, BT + 0.0005), material=NICKEL, verts=24, bevel=0.0008, name='screw')
    kit.box((0.012, 0.0018, 0.0012), at=(x, y, BT + 0.002), rot=(0, 0, 30), material=DARK, name='slot')

# ---------------------------------------------------------------- the arm: one cast profile, rounded, with decals
P = [(-0.205, 0.075), (-0.118, 0.075), (-0.118, 0.194), (-0.030, 0.197), (0.040, 0.172), (0.072, 0.100), (0.064, 0.0),
     (0.212, 0.0), (0.180, 0.034), (0.176, 0.200), (0.170, 0.287), (0.100, 0.284), (0.010, 0.264), (-0.080, 0.280),
     (-0.118, 0.285), (-0.205, 0.285)]
R = [0.008, 0.008, 0.020, 0.060, 0.050, 0.040, 0.012, 0.004, 0.030, 0.040, 0.014, 0.050, 0.060, 0.040, 0.010, 0.012]
prof = fillet(P, R, n=6, closed=True)
AD = 0.078            # arm depth
AY = 0.016            # arm centre (a little behind the bed's middle)
arm = kit.extrude(prof, AD, rot=(90, 0, 0), material=ENAMEL, bevel=0.011, segments=3, name='arm')
arm.location = (0, AY + AD / 2, BT)

# decal texture, laid out on the arm's front face in metres -> pixels
xs = [p[0] for p in prof]; zs = [p[1] for p in prof]
X0, X1, Z0, Z1 = min(xs), max(xs), min(zs), max(zs)
TW = 1024; TH = int(TW * (Z1 - Z0) / (X1 - X0))
px = lambda x, z: ((x - X0) / (X1 - X0) * TW, (1 - (z - Z0) / (Z1 - Z0)) * TH)
items = []
gold = list(GOLD)


def line(pts, w=0.0016):
    items.append({'kind': 'line', 'pts': [px(x, z) for x, z in pts], 'width': w / (X1 - X0) * TW, 'color': gold})


def dot(x, z, r=0.002):
    X, Y = px(x, z); items.append({'kind': 'dot', 'x': X, 'y': Y, 'r': r / (X1 - X0) * TW, 'color': gold})


def leaf(x, z, ang, L=0.016, w=0.0045):
    a = math.radians(ang); pts = []
    for k in range(13):
        t = k / 12; pts.append((t * L, w * math.sin(math.pi * t) ** 0.9))
    for k in range(12, -1, -1):
        t = k / 12; pts.append((t * L, -w * math.sin(math.pi * t) ** 0.9))
    pts = [(x + u * math.cos(a) - v * math.sin(a), z + u * math.sin(a) + v * math.cos(a)) for u, v in pts]
    items.append({'kind': 'poly', 'pts': [px(*p) for p in pts], 'color': gold})


def spiral(x, z, r0, turns=1.6, start=0.0, s=1, tail=None, w=0.0015):
    pts = []
    for k in range(60):
        t = k / 59; r = r0 * (1 - 0.82 * t); th = start + s * t * turns * math.tau
        pts.append((x + r * math.cos(th), z + r * math.sin(th)))
    if tail:
        pts = [tail] + pts
    line(pts, w); dot(*pts[-1], r=0.0012)


# pinstripe following the outline, and a second finer one inside it
soft = fillet(P, [max(r, 0.026) for r in R], n=8, closed=True)      # rounder corners so the inset lines don't cross
for d_, w_ in ((0.0145, 0.0015), (0.0185, 0.0008)):
    ring = inset(soft, d_)
    line(ring + [ring[0]], w_)
# pillar: a vine running up with leaves and curling tendrils (as in her drawing)
vine = [(0.120 + 0.009 * math.sin(z * 30), z) for z in [0.035 + 0.205 * k / 40 for k in range(41)]]
line(vine, 0.0018)
for k, z in enumerate((0.055, 0.090, 0.125, 0.160, 0.195, 0.230)):
    xv = 0.120 + 0.009 * math.sin(z * 30)
    side = 1 if k % 2 else -1
    leaf(xv, z, 90 + side * 55, 0.017, 0.005)
spiral(0.146, 0.074, 0.011, 1.5, math.pi, -1, tail=(0.130, 0.064))
spiral(0.099, 0.150, 0.009, 1.5, 0.0, 1, tail=(0.112, 0.141))
spiral(0.146, 0.214, 0.009, 1.4, math.pi, -1, tail=(0.130, 0.203))
# pillar foot: a big curl where the casting meets the bed
spiral(0.098, 0.030, 0.012, 1.3, math.pi * 0.9, -1, tail=(0.126, 0.019))
# arm: scrolls following the arch, mirrored about a small flower
ZA = 0.229
for s in (-1, 1):
    cx = -0.012 + s * 0.046
    pts = [(cx + s * 0.034 * (k / 30), ZA - 0.004 + 0.008 * math.sin(math.pi * k / 30)) for k in range(31)]
    line(pts, 0.0014)
    spiral(cx + s * 0.040, ZA - 0.004, 0.0075, 1.4, math.pi if s > 0 else 0.0, -s)
    spiral(cx - s * 0.006, ZA, 0.0065, 1.3, 0.0 if s > 0 else math.pi, s)
    leaf(cx + s * 0.018, ZA + 0.006, 90 - s * 65, 0.012, 0.0035)
for k in range(6):
    a = k * math.tau / 6
    leaf(-0.012, ZA, math.degrees(a), 0.0075, 0.0028)
dot(-0.012, ZA, 0.0024)
# head: a column of small motifs
spiral(-0.158, 0.250, 0.010, 1.5, 0.0, 1)
dot(-0.158, 0.222, 0.0025)
spiral(-0.158, 0.196, 0.010, 1.5, math.pi, -1)
leaf(-0.166, 0.150, 70, 0.018, 0.005); leaf(-0.150, 0.150, 110, 0.018, 0.005)
dot(-0.158, 0.120, 0.0022)

decal = paint({'size': [TW, TH], 'bg': [int(255 * v) for v in kit_hex(ENAMEL_HEX)], 'items': items}, 'sewing_decals')
DECAL = tex_mat('enamel_decals', decal, rough=0.25)

# UVs: front face gets the decal, back face gets it mirrored, everything else samples a plain corner of the texture
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.convert(target='MESH')
me = arm.data
me.materials.clear(); me.materials.append(ENAMEL); me.materials.append(DECAL)
lay = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
# arm local coords: x = x, local y (profile) -> world z, local z (extrusion) -> -world y
for p in me.polygons:
    nz = p.normal.z
    if abs(nz) > 0.98:
        p.material_index = 1
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u = (co.x - X0) / (X1 - X0); v = (co.y - Z0) / (Z1 - Z0)
            lay.data[li].uv = (u if nz < 0 else u, v)
    else:
        p.material_index = 0
        for li in p.loop_indices:
            lay.data[li].uv = (0.002, 0.002)

# ---------------------------------------------------------------- head fittings: face plate, needle bar, foot, take-up lever, tension
HX = -0.160
FY = AY - AD / 2          # front face of the arm
kit.box((0.004, AD - 0.026, 0.150), at=(-0.205 - 0.0005, AY, BT + 0.180), material=NICKEL, bevel=0.0018, name='faceplate')
for z in (0.125, 0.235):
    kit.cyl(0.0035, 0.002, at=(-0.2075, AY, BT + z), rot=(0, 90, 0), material=DARK, verts=12, name='fpscrew')
rod((HX, FY + 0.016, BT + 0.090), (HX, FY + 0.016, BT + 0.036), 0.0042, material=NICKEL, verts=16, name='needlebar')
kit.box((0.012, 0.010, 0.010), at=(HX, FY + 0.016, BT + 0.036), material=NICKEL, bevel=0.0015, name='clamp')
rod((HX, FY + 0.016, BT + 0.032), (HX, FY + 0.016, BT + 0.001), 0.0009, material=NICKEL, verts=8, name='needle')
rod((HX - 0.014, FY + 0.026, BT + 0.090), (HX - 0.014, FY + 0.026, BT + 0.022), 0.0040, material=NICKEL, verts=16, name='presserbar')
foot = kit.extrude(fillet([(-0.016, -0.007), (0.012, -0.007), (0.016, -0.002), (0.016, 0.002), (0.012, 0.007), (-0.016, 0.007)],
                          0.003, n=3, closed=True), 0.004, at=(HX - 0.004, FY + 0.016, BT + 0.0004), material=NICKEL, bevel=0.001, name='foot')
kit.box((0.006, 0.006, 0.020), at=(HX - 0.014, FY + 0.022, BT + 0.014), material=NICKEL, bevel=0.0012, name='shank')
# take-up lever poking out of the head front, and tension discs
kit.box((0.008, 0.026, 0.006), at=(HX + 0.012, FY - 0.010, BT + 0.250), material=NICKEL, bevel=0.0015, name='takeup')
kit.cyl(0.0035, 0.004, at=(HX + 0.012, FY - 0.024, BT + 0.250), rot=(90, 0, 0), material=NICKEL, verts=12, name='takeupeye')
rod((HX + 0.030, FY + 0.003, BT + 0.200), (HX + 0.030, FY - 0.016, BT + 0.200), 0.0028, material=NICKEL, verts=12, name='tensionstud')
for dy in (0.0045, 0.0075):
    kit.cyl(0.0095, 0.0022, at=(HX + 0.030, FY - dy, BT + 0.200), rot=(90, 0, 0), material=NICKEL, verts=24, bevel=0.0006, name='tension')
kit.cyl(0.0045, 0.006, at=(HX + 0.030, FY - 0.013, BT + 0.200), rot=(90, 0, 0), material=NICKEL, verts=16, bevel=0.001, name='tensionnut')
# needle plate and slide plate on the bed, with feed-dog slots
kit.box((0.064, 0.052, 0.002), at=(HX + 0.004, FY + 0.016, BT + 0.0005), material=NICKEL, bevel=0.0007, name='needleplate')
for dx in (-0.006, 0.006):
    kit.box((0.003, 0.016, 0.0012), at=(HX + 0.004 + dx, FY + 0.016, BT + 0.0013), material=DARK, name='feedslot')
kit.box((0.056, 0.048, 0.002), at=(HX + 0.064, FY + 0.016, BT + 0.0005), material=NICKEL, bevel=0.0007, name='slideplate')
kit.box((0.010, 0.004, 0.0012), at=(HX + 0.064, FY - 0.004, BT + 0.0014), material=DARK, name='thumbslot')

# ---------------------------------------------------------------- spools on the head and pillar
def spool(x, y, z, thread, h=0.034, r=0.012):
    rod((x, y, z - 0.002), (x, y, z + h + 0.012), 0.0024, material=NICKEL, verts=12, name='spoolpin')
    kit.lathe(fillet([(0.0026, z), (r + 0.004, z), (r + 0.004, z + 0.004), (r, z + 0.005), (r, z + h - 0.005), (r + 0.004, z + h - 0.004),
                      (r + 0.004, z + h), (0.0026, z + h)], [0, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0], n=2),
              at=(x, y, 0), material=SPOOL, steps=32, name='spool')
    kit.cyl(r + 0.0025, h - 0.011, at=(x, y, z + h / 2), material=thread, verts=32, name='thread')
    kit.sphere(0.0042, at=(x, y, z + h + 0.013), material=NICKEL, segs=12, rings=8, name='pinball')


spool(-0.160, AY, BT + 0.285, THREAD_R)
spool(0.135, AY, BT + 0.284, THREAD_C, h=0.030, r=0.011)
# red thread: off the spool, through a guide on the arm, down the head to the take-up lever, the tension and the needle
kit.tube([(-0.148, AY - 0.010, BT + 0.300), (-0.130, FY + 0.004, BT + 0.292), (-0.140, FY - 0.006, BT + 0.276), (HX + 0.012, FY - 0.024, BT + 0.256),
          (HX + 0.026, FY - 0.016, BT + 0.205), (HX + 0.010, FY - 0.004, BT + 0.120), (HX + 0.002, FY + 0.010, BT + 0.050),
          (HX, FY + 0.0145, BT + 0.012)], 0.0006, material=THREAD_R, bevel_res=6, name='threadline')
kit.box((0.006, 0.010, 0.006), at=(-0.130, FY + 0.002, BT + 0.290), material=NICKEL, bevel=0.0012, name='guide')

# ---------------------------------------------------------------- pillar boss (stitch regulator) and the handwheel
kit.cyl(0.014, 0.006, at=(0.152, FY - 0.002, BT + 0.135), rot=(90, 0, 0), material=NICKEL, verts=32, bevel=0.0015, name='boss')
kit.cyl(0.008, 0.006, at=(0.152, FY - 0.007, BT + 0.135), rot=(90, 0, 0), material=NICKEL, verts=24, bevel=0.0015, name='bossknob')
WX, WZ, WR = 0.236, BT + 0.104, 0.074
rod((0.168, AY, WZ), (WX + 0.010, AY, WZ), 0.010, material=NICKEL, verts=20, name='axle')
kit.cyl(0.024, 0.012, at=(0.181, AY, WZ), rot=(0, 90, 0), material=ENAMEL, verts=32, bevel=0.003, name='bushing')
rim = kit.lathe(fillet([(WR - 0.010, -0.009), (WR, -0.009), (WR + 0.002, 0.0), (WR, 0.009), (WR - 0.010, 0.009), (WR - 0.012, 0.0)],
                       [0.002, 0.003, 0.004, 0.003, 0.002, 0.003], n=3, closed=False) + [(WR - 0.010, -0.009)],
                material=NICKEL, steps=72, name='rim')
hub = kit.lathe(fillet([(0.0, -0.012), (0.020, -0.012), (0.022, 0.0), (0.020, 0.012), (0, 0.012)], [0, 0.003, 0.004, 0.003, 0], n=3),
                material=NICKEL, steps=40, name='hub')
knob = kit.lathe(fillet([(0.0, 0.010), (0.015, 0.010), (0.016, 0.018), (0.012, 0.024), (0, 0.025)], [0, 0.002, 0.003, 0.003, 0], n=3),
                 material=NICKEL, steps=32, name='clutchknob')
spokes = []
for k in range(6):
    a = k * math.tau / 6
    pts = []
    for j in range(7):
        t = j / 6; r = 0.018 + (WR - 0.028) * t; th = a + 0.55 * math.sin(math.pi * t) + 0.25 * t
        pts.append((r * math.cos(th), r * math.sin(th), 0))
    spokes.append(kit.tube(pts, 0.0048, material=NICKEL, bevel_res=6, name='spoke'))
wheel = bake_join('handwheel', [rim, hub, knob] + spokes)
wheel.matrix_world = Matrix.Translation((WX, AY, WZ)) @ Matrix.Rotation(math.radians(90), 4, 'Y') @ wheel.matrix_world

# ---------------------------------------------------------------- join, settle and export
both = bake_join('sewing_machine')
settle(both)
kit.export('sewing-machine')
