"""Astronaut helmet (Jessy Elias).

The drawing: a round helmet with a big visor framed by a thick rim, a "13" roundel on the side, a round
port below it, a ribbed hose curling from the side down to the neck ring, a little "13" box on the neck ring,
and a flag pole clipped to a bracket at the back flying a long pennant that reads "C13". Line-only, so: white
shell, gold mirrored visor, teal anodised neck ring, cream pennant with red lettering.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, subprocess, tempfile
from mathutils import Vector, Matrix, Quaternion

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'
DIN = '/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf'


def text3d(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, bevel=0.0, res=3,
           spacing=1.0, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res; cu.space_character = spacing
    cu.bevel_depth = bevel; cu.bevel_resolution = 1
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def orient(o, normal, at, spin=0.0):
    """Turn an object built facing +Z so it faces `normal`, then place it."""
    q = Vector((0, 0, 1)).rotation_difference(Vector(normal).normalized())
    if spin:
        q = q @ Quaternion((0, 0, 1), spin)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = q; o.location = at
    return o


def rod(a, b, r, material, verts=16, name='rod'):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=tuple((a + b) / 2), verts=verts, name=name)
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    return kit.finish(o, material)


def resmooth(o, angle=35):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


# ---------- materials ----------
shell_m = kit.mat('#f2efe8', rough=0.32, name='shell')
visor_m = kit.mat('#d9a441', rough=0.08, metal=1.0, name='visor_gold')
rim_m = kit.mat('#b9bcc2', rough=0.3, metal=0.85, name='visor_rim')
ring_m = kit.mat('#2f7d86', rough=0.3, metal=0.75, name='anodised_teal')
alu = kit.mat('chrome', rough=0.25, metal=1.0, name='alu')
steel = kit.mat('steel', rough=0.35, metal=0.85, name='steel')
cream = kit.mat('cream', rough=0.45, name='cream')
ink = kit.mat('#1e1d1c', rough=0.5, name='ink')
red = kit.mat('red', rough=0.45, name='red')
hose_m = kit.mat('#e6e2d8', rough=0.7, name='hose')
dark = kit.mat('#2a2826', rough=0.6, name='dark')

# ---------- dimensions ----------
R = 0.155                   # shell radius
C = Vector((0, 0, 0.142))   # shell centre
RING_TOP = 0.046

# ---------- shell ----------
shell = kit.sphere(R, at=tuple(C), segs=72, rings=36, material=shell_m, name='shell')
shell.scale = (1.0, 1.04, 1.0)
cutb = kit.box((1, 1, 0.2), at=(0, 0, 0.03 - 0.1), name='cut')
kit.boolean(shell, cutb)
resmooth(shell, 50)

# ---------- visor: a gold cap facing the front, tilted up, framed by a thick rim ----------
AX = Vector((0, -math.cos(math.radians(16)), math.sin(math.radians(16)))).normalized()
HALF = math.radians(56)
bm = bmesh.new()
NT, NP = 14, 64
rows = []
q = Vector((0, 0, 1)).rotation_difference(AX)
center_v = bm.verts.new(C + AX * (R * 1.04 + 0.002))
for i in range(1, NT + 1):
    th = HALF * i / NT
    row = []
    for j in range(NP):
        ph = j * math.tau / NP
        d = q @ Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
        # follow the (slightly deep) shell: scale y like the shell
        p = Vector((d.x * (R + 0.0025), d.y * (R * 1.04 + 0.0025), d.z * (R + 0.0025)))
        row.append(bm.verts.new(C + p))
    rows.append(row)
for j in range(NP):
    bm.faces.new((center_v, rows[0][j], rows[0][(j + 1) % NP]))
for a, b in zip(rows, rows[1:]):
    for j in range(NP):
        bm.faces.new((a[j], b[j], b[(j + 1) % NP], a[(j + 1) % NP]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('visor'); bm.to_mesh(me); bm.free()
visor = bpy.data.objects.new('visor', me); bpy.context.collection.objects.link(visor)
kit.finish(visor, visor_m, smooth=80)
for f in visor.data.polygons:
    f.use_smooth = True
# make sure the visor's normals face outward
if (visor.data.polygons[0].center - (C - Vector((0, 0, 0)))).dot(visor.data.polygons[0].normal) < 0:
    bpy.context.view_layer.objects.active = visor; bpy.ops.object.select_all(action='DESELECT'); visor.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT')
# the rim: a swept rounded band along the visor's edge
rim_pts = []
for j in range(NP):
    ph = j * math.tau / NP
    d = q @ Vector((math.sin(HALF) * math.cos(ph), math.sin(HALF) * math.sin(ph), math.cos(HALF)))
    rim_pts.append(C + Vector((d.x * (R + 0.004), d.y * (R * 1.04 + 0.004), d.z * (R + 0.004))))
bm = bmesh.new(); rings = []
prof = [(0.019 * math.cos(a), 0.0105 * math.sin(a)) for a in (k * math.tau / 12 for k in range(12))]
for j, p in enumerate(rim_pts):
    t = (rim_pts[(j + 1) % NP] - rim_pts[j - 1]).normalized()
    out = (p - C).normalized()
    side = t.cross(out).normalized(); up = side.cross(t).normalized()
    rings.append([bm.verts.new(p + side * u + up * v) for u, v in prof])
for j in range(NP):
    a, b = rings[j], rings[(j + 1) % NP]
    for k in range(len(prof)):
        bm.faces.new((a[k], a[(k + 1) % len(prof)], b[(k + 1) % len(prof)], b[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new('rim'); bm.to_mesh(me); bm.free()
rim = bpy.data.objects.new('visor_rim', me); bpy.context.collection.objects.link(rim)
kit.finish(rim, rim_m, smooth=70)


def on_shell(dirv, lift=0.0):
    d = Vector(dirv).normalized()
    return C + Vector((d.x * (R + lift), d.y * (R * 1.04 + lift), d.z * (R + lift))), d


# ---------- "13" roundel high on the right side ----------
p, d = on_shell((1.0, 0.12, 0.62), 0.001)
disc = kit.cyl(0.036, 0.006, verts=40, material=cream, bevel=0.0018, name='roundel')
orient(disc, d, p)
ringb = kit.torus(0.036, 0.003, material=ink, major=40, minor=6, name='roundel_ring')
orient(ringb, d, p + d * 0.002)
t13 = text3d('13', 0.036, 0.002, font=FONT, rot=(0, 0, 0), material=ink, name='roundel_13')
# text is built in XY facing +Z; turn it to face out with its up toward world +Z
up_w = (Vector((0, 0, 1)) - d * d.z).normalized()
xr = up_w.cross(d).normalized()
M = Matrix((xr, up_w, d)).transposed().to_4x4(); M.translation = p + d * 0.0035
t13.matrix_world = M

# ---------- ports: a round connector each side, the right one feeding the hose ----------
for sx in (-1, 1):
    p, d = on_shell((sx * 1.0, 0.05, -0.18), 0.0)
    boss = kit.cyl(0.034, 0.022, verts=40, material=steel, bevel=0.003, name='port')
    orient(boss, d, p + d * 0.004)
    face = kit.cyl(0.026, 0.006, verts=40, material=ring_m, bevel=0.0015, name='portface')
    orient(face, d, p + d * 0.016)
    oval = kit.cyl(0.013, 0.004, verts=32, material=dark, name='portoval')
    oval.scale = (0.7, 1.0, 1.0)
    orient(oval, d, p + d * 0.0185)
    if sx > 0:
        PORT = p + d * 0.01

# ---------- neck ring ----------
ring = kit.lathe([(0.098, 0.0), (0.134, 0.0), (0.138, 0.006), (0.138, 0.022), (0.132, 0.026), (0.132, 0.034),
                  (0.136, 0.038), (0.136, RING_TOP - 0.004), (0.13, RING_TOP), (0.105, RING_TOP), (0.098, 0.04),
                  (0.098, 0.0)], material=ring_m, steps=72, name='neckring')
resmooth(ring, 30)
kit.torus(0.1345, 0.0035, at=(0, 0, 0.03), material=alu, major=72, minor=8, name='lockband')
# latch lugs on the ring
for a in (35, 145, 215, 325):
    ar = math.radians(a)
    kit.box((0.016, 0.012, 0.012), at=(0.14 * math.cos(ar), 0.14 * math.sin(ar), 0.03), rot=(0, 0, a),
            material=alu, bevel=0.003, segments=2, name='lug')
# the "13" box on the front-left of the ring
ab = math.radians(-118)
bx, by = 0.15 * math.cos(ab), 0.15 * math.sin(ab)
box13 = kit.box((0.062, 0.034, 0.036), at=(bx, by, 0.028), rot=(0, 0, math.degrees(ab) + 90), material=cream,
                bevel=0.004, segments=2, name='box13')
n = Vector((math.cos(ab), math.sin(ab), 0))
tb = text3d('13', 0.026, 0.0012, font=DIN, rot=(0, 0, 0), material=ink, name='box13_txt')
xr = Vector((0, 0, 1)).cross(n).normalized()
M = Matrix((xr, Vector((0, 0, 1)), n)).transposed().to_4x4(); M.translation = Vector((bx, by, 0.028)) + n * 0.0175
tb.matrix_world = M

# ---------- ribbed hose: from under the right port, down and round to the back of the neck ring ----------
CONN, dc = on_shell((1.0, 0.32, -0.42), 0.0)
cn = kit.cyl(0.019, 0.02, verts=24, material=steel, bevel=0.003, name='hoseport')
orient(cn, dc, CONN + dc * 0.004)
hp = [CONN + dc * 0.01, CONN + dc * 0.03, CONN + dc * 0.045 + Vector((0, 0.025, -0.02)), Vector((0.185, 0.115, 0.034)),
      Vector((0.15, 0.15, 0.024)), Vector((0.11, 0.152, 0.024)), Vector((0.086, 0.128, 0.025))]
hose = kit.tube([tuple(v) for v in hp], 0.0145, material=hose_m, name='hose')
# ribs along the hose
cu = bpy.data.curves.new('hp', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('NURBS'); sp.points.add(len(hp) - 1)
for pt, v in zip(sp.points, hp):
    pt.co = (*v, 1)
sp.use_endpoint_u = True; sp.order_u = 4; cu.resolution_u = 40
tmp = bpy.data.objects.new('hp', cu); bpy.context.collection.objects.link(tmp)
bpy.context.view_layer.objects.active = tmp; bpy.ops.object.select_all(action='DESELECT'); tmp.select_set(True)
bpy.ops.object.convert(target='MESH'); tmp = bpy.context.object
path = [tmp.matrix_world @ v.co for v in tmp.data.vertices]
bpy.data.objects.remove(tmp, do_unlink=True)
acc = 0.0
for i in range(1, len(path) - 1):
    acc += (path[i] - path[i - 1]).length
    if acc >= 0.011:
        acc = 0.0
        t = (path[i + 1] - path[i - 1]).normalized()
        rb = kit.torus(0.0145, 0.0036, material=hose_m, major=20, minor=6, name='rib')
        orient(rb, t, path[i])
# hose cuffs
for v, w in ((path[0], path[1]), (path[-1], path[-2])):
    cf = kit.cyl(0.019, 0.016, verts=24, material=steel, bevel=0.002, name='cuff')
    orient(cf, (w - v), v + (w - v).normalized() * 0.004)

# ---------- flag bracket, pole and pennant at the back right ----------
p, d = on_shell((0.62, 0.72, 0.42), 0.0)
br = kit.box((0.03, 0.022, 0.07), material=steel, bevel=0.004, segments=2, name='bracket')
tang_up = (Vector((0, 0, 1)) - d * d.z).normalized()
xr = d.cross(tang_up).normalized()
M = Matrix((xr, d, tang_up)).transposed().to_4x4(); M.translation = p + d * 0.008
br.matrix_world = M
tab = kit.box((0.012, 0.014, 0.012), material=steel, bevel=0.002, name='tab')
M2 = M.copy(); M2.translation = p + d * 0.02 + xr * 0.018 - tang_up * 0.01
tab.matrix_world = M2
pole_dir = (d * 0.25 + Vector((0.12, 0.05, 1.0))).normalized()
P0 = p + d * 0.02 - tang_up * 0.03
P1 = P0 + pole_dir * 0.36
rod(P0, P1, 0.0055, alu, name='pole')
for f in (0.33, 0.62):
    jc = kit.cyl(0.0075, 0.016, verts=16, material=steel, bevel=0.0015, name='joint')
    orient(jc, pole_dir, P0 + pole_dir * 0.36 * f)
ringtop = kit.torus(0.011, 0.0028, material=alu, major=24, minor=8, name='finial_ring')
side_dir = pole_dir.cross(Vector((0, 0, 1))).normalized()
orient(ringtop, side_dir, P1 + pole_dir * 0.012)

# pennant: generated textures with "C13" (the back one mirrored so it reads from both sides)
tdir = tempfile.mkdtemp()
subprocess.run(['/usr/bin/env', 'python3', '-c', r"""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageOps
W, H = 1024, 256
try:
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf', 150)
except Exception:
    f = ImageFont.load_default()
for name, mirror in (('front.png', False), ('back.png', True)):
    txt = Image.new('L', (W, H), 0); ImageDraw.Draw(txt).text((150, H // 2 + 6), 'C13', font=f, fill=255, anchor='lm')
    if mirror:
        bb = txt.getbbox(); crop = ImageOps.mirror(txt.crop(bb)); txt = Image.new('L', (W, H), 0); txt.paste(crop, bb[:2])
    im = Image.new('RGB', (W, H), (239, 227, 200))
    im.paste((184, 50, 42), (0, 0, W, H), txt)
    ImageDraw.Draw(im).rectangle((0, 0, 38, H), fill=(184, 50, 42))      # hem along the pole
    im.save(os.path.join(sys.argv[1], name))
""", tdir], check=True)
FL, FH = 0.27, 0.115            # length, height at the pole
along = (side_dir * 0.85 + Vector((0.2, 0.35, -0.05))).normalized()
along = (along - pole_dir * along.dot(pole_dir)).normalized()
nrm = along.cross(pole_dir).normalized()
base_top = P1 - pole_dir * 0.012
NU, NV = 28, 6
for face, tex in ((1, 'front.png'), (-1, 'back.png')):
    fm = kit.mat('#ffffff', rough=0.8, name='pennant_' + tex[:-4], image=os.path.join(tdir, tex))
    fm.use_backface_culling = True
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = []
    for i in range(NU + 1):
        u = i / NU
        h = FH * (1 - u) ** 0.85 + 0.004
        droop = 0.16 * u ** 2.4           # the tail curls down, as drawn
        wave = 0.022 * math.sin(u * 6.0 + 0.4) * (0.3 + u)
        col = []
        for j in range(NV + 1):
            v = j / NV
            pt = base_top + along * (FL * u) - pole_dir * (h * v + (FH - h) * 0.5 + droop) + nrm * (wave + face * 0.0006)
            col.append(bm.verts.new(pt))
        grid.append(col)
    for i in range(NU):
        for j in range(NV):
            ids = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if face > 0:
                ids = ids[::-1]
            fc = bm.faces.new([grid[a_][b_] for a_, b_ in ids])
            for l, (a_, b_) in zip(fc.loops, ids):
                l[uvl].uv = (a_ / NU, 1 - b_ / NV)
    me = bpy.data.meshes.new('pennant'); bm.to_mesh(me); bm.free()
    fo = bpy.data.objects.new('pennant', me); bpy.context.collection.objects.link(fo)
    kit.finish(fo, fm, smooth=80)
# pole clips holding the pennant
for f in (0.0, 0.5):
    cl = kit.cyl(0.0072, 0.008, verts=16, material=red, name='clip')
    orient(cl, pole_dir, base_top - pole_dir * (FH * f + 0.004))

kit.export('astronaut-helmet')
