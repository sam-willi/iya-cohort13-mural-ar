"""African drums - Jerry Wu.

His drawing: a djembe. A skin head lettered "IYA / 30", a crown ring knotted all round, rope verticals running down the
bowl to a ring at the waist, a loop of beads hanging off one side as a handle, and a carved waist and foot: a dark band of
nested diamonds, a band of chevrons, then a wavy rule and running spirals round the flared foot.
Colours are a choice: honey hardwood with the carving burned dark into it (a PIL texture), cream goatskin, red rope,
cowrie-shell beads.  The "30" is read as drawn.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, subprocess, tempfile
from mathutils import Vector, Matrix

FONTS = '/System/Library/Fonts/Supplemental/'

# ---------------------------------------------------------------- the carving, drawn with PIL (u = around, v = up)
ZTOP = 0.585
BANDS = {'rim': (0.0, 0.012), 'spiral': (0.016, 0.086), 'wave': (0.090, 0.110), 'chevron': (0.150, 0.204),
         'diamond': (0.207, 0.257), 'collar': (0.261, 0.284)}
TEX = os.path.join(tempfile.gettempdir(), 'african-drums-carving.png')
PIL_SCRIPT = r'''
import sys, math, random
from PIL import Image, ImageDraw, ImageFilter
W, H, ZT = 1024, 1024, float(sys.argv[2])
B = eval(sys.argv[3])
random.seed(7)
wood = (196, 134, 66); dark = (62, 34, 16); mid = (150, 92, 42)
im = Image.new('RGB', (W, H), wood)
d = ImageDraw.Draw(im)
# grain: long vertical streaks
for i in range(900):
    x = random.uniform(0, W); w = random.uniform(0.6, 2.2); c = random.uniform(-26, 18)
    col = tuple(int(max(0, min(255, v + c))) for v in wood)
    d.line([(x, 0), (x + random.uniform(-6, 6), H)], fill=col, width=int(w) + 1)
im = im.filter(ImageFilter.GaussianBlur(1.2)); d = ImageDraw.Draw(im)
def y(z): return H - z / ZT * H
def band(name): z0, z1 = B[name]; return y(z1), y(z0)
LW = 5
# foot rim
t, b = band('rim'); d.rectangle([0, t, W, b], fill=mid)
# running spirals with S-curves between them (8 round the foot)
t, b = band('spiral'); n = 8; cw = W / n; cy = (t + b) / 2; R = (b - t) * 0.36
for k in range(n + 1):
    cx = k * cw + cw * 0.5
    pts = []
    for i in range(70):
        a = i / 69 * 3.3 * math.pi; r = R * (1 - i / 69 * 0.92)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.line(pts, fill=dark, width=LW)
    # S-curve from this spiral's outer end up and over to the next
    pts = []
    for i in range(40):
        s = i / 39
        pts.append((cx + R + s * (cw - 2 * R), cy - R * 0.2 + math.sin(s * math.pi) * -R * 0.9 + s * R * 0.4))
    d.line(pts, fill=dark, width=LW)
d.line([(0, t), (W, t)], fill=dark, width=LW); d.line([(0, b), (W, b)], fill=dark, width=LW)
# wavy rule
t, b = band('wave'); d.line([(0, t), (W, t)], fill=dark, width=LW); d.line([(0, b), (W, b)], fill=dark, width=LW)
pts = [(x, (t + b) / 2 + (b - t) * 0.26 * math.sin(x / W * 24 * math.pi)) for x in range(0, W + 1, 4)]
d.line(pts, fill=dark, width=LW - 1)
# chevrons: nested V's, 12 round
t, b = band('chevron'); n = 12; cw = W / n
d.line([(0, t), (W, t)], fill=dark, width=LW); d.line([(0, b), (W, b)], fill=dark, width=LW)
for k in range(n):
    x0 = k * cw
    for j in range(4):
        o = j * (b - t) * 0.22
        d.line([(x0 + o * 0.55, t + 4), (x0 + cw / 2, b - 4 - o), (x0 + cw - o * 0.55, t + 4)], fill=dark, width=LW - 1)
# diamonds: dark field, nested light diamonds with a dark eye, 10 round
t, b = band('diamond'); n = 10; cw = W / n; cy = (t + b) / 2; hh = (b - t) / 2
d.rectangle([0, t, W, b], fill=dark)
for k in range(n):
    cx = k * cw + cw / 2
    for s, col in ((1.0, wood), (0.72, dark), (0.5, wood), (0.26, dark)):
        d.polygon([(cx, cy - hh * s * 0.92), (cx + cw * 0.46 * s, cy), (cx, cy + hh * s * 0.92), (cx - cw * 0.46 * s, cy)],
                  fill=col)
    d.polygon([(k * cw, t), (k * cw + cw * 0.08, t), (k * cw, t + hh * 0.3)], fill=wood)
# collar with a small wave
t, b = band('collar'); d.line([(0, t), (W, t)], fill=dark, width=LW - 1); d.line([(0, b), (W, b)], fill=dark, width=LW - 1)
pts = [(x, (t + b) / 2 + (b - t) * 0.2 * math.sin(x / W * 40 * math.pi)) for x in range(0, W + 1, 4)]
d.line(pts, fill=dark, width=3)
im.save(sys.argv[1])
'''
subprocess.run(['/usr/bin/env', 'python3', '-c', PIL_SCRIPT, TEX, str(ZTOP), repr(BANDS)], check=True)
carving = bpy.data.images.load(TEX); carving.pack()


def tex_mat(name, image, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = image
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    return m


def lathe_uv(profile, steps, material, name, zmax=ZTOP):
    """Revolve [(r, z)] round Z with UVs: u round the drum, v = height (so the carving texture wraps true)."""
    verts, faces, uvs = [], [], []
    n = len(profile)
    for k in range(steps + 1):
        a = k / steps * math.tau
        for r, z in profile:
            verts.append((r * math.sin(a), -r * math.cos(a), z))
    for k in range(steps):
        for i in range(n - 1):
            a = k * n + i; b = (k + 1) * n + i
            faces.append((a, b, b + 1, a + 1))
            uvs.append([(k / steps, profile[i][1] / zmax), ((k + 1) / steps, profile[i][1] / zmax),
                        ((k + 1) / steps, profile[i + 1][1] / zmax), (k / steps, profile[i + 1][1] / zmax)])
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uv = me.uv_layers.new(name='UVMap')
    for p, quad in zip(me.polygons, uvs):
        for li, c in zip(p.loop_indices, quad):
            uv.data[li].uv = c
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return kit.finish(o, None, smooth=50)


def mesh_obj(name, verts, faces, materials=()):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in materials:
        o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def rod(points, r, material, n=8, closed=False, name='rod'):
    P = [Vector(p) for p in points]; verts = []; faces = []; m = len(P)
    for i, p in enumerate(P):
        t = ((P[(i + 1) % m] - P[i - 1]) if closed else (P[min(i + 1, m - 1)] - P[max(i - 1, 0)])).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized(); v = t.cross(u).normalized()
        for k in range(n):
            a = k / n * math.tau
            verts.append(tuple(p + (u * math.cos(a) + v * math.sin(a)) * r))
    for i in range(m if closed else m - 1):
        i2 = (i + 1) % m
        for k in range(n):
            faces.append((i * n + k, i * n + (k + 1) % n, i2 * n + (k + 1) % n, i2 * n + k))
    if not closed:
        faces.append(tuple(reversed(range(n)))); faces.append(tuple(range((m - 1) * n, m * n)))
    return kit.finish(mesh_obj(name, verts, faces, [material]), None, smooth=60)


# ---------------------------------------------------------------- materials
WOOD = tex_mat('carved wood', carving, 0.55)
SKIN = kit.mat('#ecdcb8', rough=0.7, name='goatskin')
SKIN_EDGE = kit.mat('#c9ab7c', rough=0.85, name='skinedge')
ROPE = kit.mat('red', rough=0.8, name='rope')
SHELL = kit.mat('#ecdfc2', rough=0.35, name='cowrie')
INK = kit.mat('#3a2414', rough=0.75, name='ink')
INSIDE = kit.mat('#3b2412', rough=0.9, name='inside')

# ---------------------------------------------------------------- body: one turned shell, foot to rim
PROF = [(0.045, 0.004), (0.100, 0.0), (0.107, 0.004), (0.111, 0.014), (0.113, 0.040), (0.110, 0.068), (0.102, 0.095),
        (0.093, 0.125), (0.085, 0.160), (0.077, 0.200), (0.070, 0.240), (0.065, 0.270), (0.063, 0.284),
        (0.064, 0.296), (0.072, 0.312), (0.086, 0.335), (0.101, 0.365), (0.116, 0.400), (0.130, 0.440),
        (0.142, 0.480), (0.152, 0.520), (0.159, 0.555), (0.163, 0.575), (0.164, 0.585), (0.150, 0.585)]
body = lathe_uv(PROF, 96, WOOD, 'body')
# a dark inside under the head and up from the foot (it's a hollow drum)
kit.cyl(0.050, 0.003, at=(0, 0, 0.0045), material=INSIDE, verts=48, name='footopening')

# ---------------------------------------------------------------- head: skin, its tucked edge, crown ring and knots
head = lathe_uv([(0.0, 0.597), (0.08, 0.5965), (0.150, 0.594), (0.166, 0.590), (0.171, 0.582), (0.172, 0.568),
                 (0.170, 0.556), (0.166, 0.552)], 96, SKIN, 'skin', zmax=1.0)
kit.torus(0.1715, 0.0055, at=(0, 0, 0.560), material=ROPE, major=96, minor=8, name='crownring')
kit.torus(0.1705, 0.004, at=(0, 0, 0.549), material=ROPE, major=96, minor=8, name='lowerring')
NK = 16
for k in range(NK):
    a = k / NK * math.tau
    p = (0.176 * math.sin(a), -0.176 * math.cos(a), 0.556)
    kit.sphere(0.0072, at=p, scale=None, material=ROPE, segs=12, rings=8, name='knot')

# "IYA / 30" painted on the skin, read as drawn
cu = bpy.data.curves.new('lbl', 'FONT'); cu.body = 'IYA\n30'; cu.size = 0.085; cu.extrude = 0.0006
cu.font = bpy.data.fonts.load(FONTS + 'Futura.ttc'); cu.resolution_u = 3; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
cu.space_line = 0.95
lbl = bpy.data.objects.new('lbl', cu); bpy.context.collection.objects.link(lbl)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = lbl; lbl.select_set(True)
bpy.ops.object.convert(target='MESH'); lbl = bpy.context.object
lbl.data.materials.clear(); lbl.data.materials.append(INK)
for v in lbl.data.vertices:
    r = math.hypot(v.co.x, v.co.y)
    v.co.z = 0.597 - 0.003 * (r / 0.15) ** 2 + v.co.z + 0.0002
lbl.data.update()

# ---------------------------------------------------------------- rope verticals: a zig-zag from the knots to the waist ring
WAIST_Z = 0.318
kit.torus(0.080, 0.005, at=(0, 0, WAIST_Z), material=ROPE, major=64, minor=8, name='waistring')


def r_at(z):
    for (r0, z0), (r1, z1) in zip(PROF, PROF[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return PROF[-2][0]


for k in range(NK):
    for side in (-0.5, 0.5):
        a0 = k / NK * math.tau; a1 = (k + side) / NK * math.tau
        pts = []
        for i in range(13):
            t = i / 12
            z = 0.550 + (WAIST_Z + 0.004 - 0.550) * t
            a = a0 + (a1 - a0) * t
            r = r_at(z) + 0.0035
            pts.append((r * math.sin(a), -r * math.cos(a), z))
        rod(pts, 0.0026, ROPE, n=6, name='vertical')

# ---------------------------------------------------------------- the beaded handle on the right flank
beads = []
A0, Z0b = math.radians(90), 0.552                       # from the crown ring...
A1, Z1b = math.radians(90), 0.335                       # ...down to just above the waist ring
NB = 11
for i in range(NB):
    t = (i + 0.5) / NB
    z = Z0b + (Z1b - Z0b) * t
    bulge = 0.075 * math.sin(t * math.pi) ** 0.8
    r = r_at(z) + 0.012 + bulge
    p = Vector((r * math.sin(A0), -r * math.cos(A0), z))
    # bead long axis along the chain
    t2 = min(1, t + 0.02); z2 = Z0b + (Z1b - Z0b) * t2; r2 = r_at(z2) + 0.012 + 0.075 * math.sin(t2 * math.pi) ** 0.8
    q = Vector((r2 * math.sin(A0), -r2 * math.cos(A0), z2))
    d = (q - p).normalized()
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    b = kit.sphere(1, at=(0, 0, 0), scale=(0.0115, 0.0085, 0.0145), material=SHELL, segs=16, rings=10, name='cowrie')
    b.data.transform(Matrix.Translation(p) @ rot); b.data.update()
    beads.append(p)
# the cord the beads are strung on, tied into the crown ring and waist ring
cord = [(0.176 * math.sin(A0), -0.176 * math.cos(A0), 0.556)] + [tuple(p) for p in beads] + \
       [((r_at(WAIST_Z) + 0.006) * math.sin(A0), -(r_at(WAIST_Z) + 0.006) * math.cos(A0), WAIST_Z + 0.003)]
rod(cord, 0.0022, ROPE, n=6, name='beadcord')

kit.export('african-drums')
