"""Toilet paper (no student drawing in the folder: a generic, carefully made roll).

A real-size roll (11.6 cm across, 10.5 cm wide) lying on its side, so the spin alternates between the long silhouette
and the cardboard core. The last sheets peel over the front and lie on the ground, ending at a perforation.
Quilted embossing and the perforations are a small normal map; the end faces carry faint ripples for the wound layers.
"""
import sys, os, math, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
import numpy as np
from mathutils import Vector

R = 0.058          # roll radius
WID = 0.105        # roll width (along X)
RC_IN, RC_OUT = 0.0205, 0.0217   # cardboard core
EDGE = 0.0045      # softened paper edge radius
SHEET = 0.11       # sheet length between perforations
TMP = tempfile.gettempdir()


# ---------------------------------------------------------------- textures
def save_img(name, arr, path, non_color=False):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = arr[::-1]
    img.pixels = px.ravel()
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


def quilt_height(u, v, n):
    """Diamond quilting: puffy cells between ±45° lines, n diamonds per tile edge."""
    a = (u + v) * n; b = (u - v) * n
    fa = a - np.floor(a); fb = b - np.floor(b)
    pillow = np.sin(np.pi * fa) * np.sin(np.pi * fb)
    pillow = np.clip(pillow, 0, 1) ** 0.6
    # a tiny dot in the middle of every other cell, like real embossing
    dot = np.exp(-(((fa - 0.5) ** 2 + (fb - 0.5) ** 2) / 0.006))
    return pillow * 0.85 - dot * 0.35


def normal_from_height(h, strength):
    gy, gx = np.gradient(h)
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def roll_normal_map(size=256):
    v, u = np.mgrid[0:size, 0:size] / size
    h = quilt_height(u, v, 4)
    return save_img('roll_nrm', normal_from_height(h, 9.0), os.path.join(TMP, 'tp_roll_nrm.png'))


def sheet_maps(size=512):
    """One sheet (WID across u, SHEET along v): quilting at the roll's scale plus a perforation row at v=0."""
    v, u = np.mgrid[0:size, 0:size] / size
    nu = WID / 0.032 * 4 / 4  # diamonds across, matching the roll (tile 3.2 cm, 4 per tile)
    h = quilt_height(u * (WID / 0.032), v * (SHEET / 0.032), 4)
    # perforation: a row of short slits at v ~ 0 (wraps to v ~ 1)
    dv = np.minimum(v, 1 - v)
    slit = (dv < 0.006) & (((u * 46) % 1.0) < 0.62)
    groove = np.exp(-(dv / 0.008) ** 2)
    h = h * (1 - groove) - groove * 0.9
    nrm = normal_from_height(h, 9.0)
    paper = np.array([0xf3, 0xf0, 0xe9]) / 255.0
    col = np.ones((size, size, 3)) * paper
    col[slit] = paper * 0.62
    return (save_img('sheet_nrm', nrm, os.path.join(TMP, 'tp_sheet_nrm.png')),
            save_img('sheet_col', col, os.path.join(TMP, 'tp_sheet_col.png')))


def paper_mat(name, nrm_path, col_path=None, color='#f3f0e9', rough=0.86, strength=0.38):
    m = kit.mat(color, rough=rough, name=name, image=col_path)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(nrm_path)
    t.image.colorspace_settings.name = 'Non-Color'
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = strength
    nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


M_ROLL = paper_mat('paper_roll', roll_normal_map())
sheet_nrm, sheet_col = sheet_maps()
M_SHEET = paper_mat('paper_sheet', sheet_nrm, sheet_col)
M_END = kit.mat('#f1ede4', rough=0.9, name='paper_end')
M_CORE = kit.mat('#b98c5c', rough=0.8, name='cardboard')
M_CORE_IN = kit.mat('#a87c4e', rough=0.85, name='cardboard_in')
M_SEAM = kit.mat('#8a6440', rough=0.85, name='core_seam')


# ---------------------------------------------------------------- the roll: a lathe around X with UVs
def revolve_x(profile, steps, mats_per_seg, u_rep, tile, name):
    """profile: [(r, x), ...] closed loop; returns a mesh revolved about X with UVs (u around, v along arc)."""
    n = len(profile)
    verts, faces, fmat, uvs = [], [], [], []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        for r, x in profile:
            verts.append((x, r * math.cos(a), r * math.sin(a) + R))
    arc = [0.0]
    for i in range(1, n + 1):
        r0, x0 = profile[i - 1]; r1, x1 = profile[i % n]
        arc.append(arc[-1] + math.hypot(r1 - r0, x1 - x0))
    for k in range(steps):
        k2 = (k + 1) % steps
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((k * n + i, k * n + i2, k2 * n + i2, k2 * n + i))
            fmat.append(mats_per_seg[i])
            u0, u1 = k / steps * u_rep, (k + 1) / steps * u_rep
            v0, v1 = arc[i] / tile, arc[i + 1] / tile
            uvs.append([(u0, v0), (u0, v1), (u1, v1), (u1, v0)])
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    for p, quad in zip(me.polygons, uvs):
        for li, uv in zip(p.loop_indices, quad):
            uvl.data[li].uv = uv
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return o, fmat


prof, segmat = [], []
hw = WID / 2
# inner bore (against the core), right to left
prof += [(RC_OUT, hw - 0.0006), (RC_OUT, -hw + 0.0006)]; segmat += [2, 1]
# left end face: rings for the wound layers, out to the soft edge
nr = 22
for i in range(nr + 1):
    r = RC_OUT + 0.001 + (R - EDGE - RC_OUT - 0.001) * i / nr
    rip = 0.00035 * math.sin(i * 2.6) - 0.0006 * (1 - abs(2 * i / nr - 1))  # slight dish + layer ripples
    prof.append((r, -hw - rip)); segmat.append(1)
for i in range(1, 6):
    t = i / 6 * math.pi / 2
    prof.append((R - EDGE + EDGE * math.sin(t), -hw + EDGE - EDGE * math.cos(t))); segmat.append(0 if i >= 3 else 1)
# outer surface
prof.append((R, -hw + EDGE)); segmat.append(0)
prof.append((R, hw - EDGE)); segmat.append(0)
for i in range(1, 6):
    t = i / 6 * math.pi / 2
    prof.append((R - EDGE + EDGE * math.cos(t), hw - EDGE + EDGE * math.sin(t))); segmat.append(0 if i <= 3 else 1)
for i in range(nr, -1, -1):
    r = RC_OUT + 0.001 + (R - EDGE - RC_OUT - 0.001) * i / nr
    rip = 0.00035 * math.sin(i * 2.6 + 1.0) - 0.0006 * (1 - abs(2 * i / nr - 1))
    prof.append((r, hw + rip)); segmat.append(1)
segmat = segmat[:len(prof)]
roll, fmat = revolve_x(prof, 96, segmat, 11, 0.032, 'roll')
for m in (M_ROLL, M_END, M_END):
    roll.data.materials.append(m)
for p, mi in zip(roll.data.polygons, fmat):
    p.material_index = mi
bm = bmesh.new(); bm.from_mesh(roll.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(roll.data); bm.free()
kit.finish(roll, None, smooth=40)

# ---------------------------------------------------------------- cardboard core, with its spiral seam
core = kit.lathe([(RC_IN, -hw + 0.0015), (RC_OUT, -hw + 0.0015), (RC_OUT, hw - 0.0015), (RC_IN, hw - 0.0015),
                  (RC_IN, -hw + 0.0015)], at=(0, 0, R), rot=(0, 90, 0), material=M_CORE, steps=64, name='core')
seam = []
for i in range(121):
    t = i / 120
    a = t * 2 * math.pi * 1.6
    x = -hw + 0.003 + t * (WID - 0.006)
    seam.append((x, (RC_IN - 0.00025) * math.cos(a), R + (RC_IN - 0.00025) * math.sin(a)))
cu = bpy.data.curves.new('seam', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(seam) - 1)
for p, c in zip(sp.points, seam):
    p.co = (*c, 1)
cu.bevel_depth = 0.0004; cu.bevel_resolution = 0
so = bpy.data.objects.new('seam', cu); bpy.context.collection.objects.link(so)
bpy.context.view_layer.objects.active = so; so.select_set(True); bpy.ops.object.convert(target='MESH')
so = bpy.context.object; so.data.materials.append(M_SEAM)

# ---------------------------------------------------------------- the tail: over the front, down, and out along the ground
T = 0.0007                    # sheet thickness
rs = R + T / 2 + 0.0003       # sits just on the roll surface
path = []
for i in range(14):           # wraps the front-top of the roll (the outermost layer, lifting off)
    th = math.radians(78 - 78 * i / 13)
    path.append((-rs * math.cos(th), R + rs * math.sin(th)))
drop_end = 0.014
for i in range(1, 7):         # hangs straight down the front
    z = R - (R - drop_end) * i / 6
    path.append((-rs - 0.0015 * math.sin(i / 6 * math.pi), z))
rb = drop_end - T / 2
for i in range(1, 9):         # bends onto the ground
    a = math.radians(90 * i / 8)
    path.append((-rs - rb + rb * math.cos(a), drop_end - rb * math.sin(a)))
y0 = path[-1][0]
flat = 0.135
for i in range(1, 15):        # lies along the floor, the last few mm curling up
    t = i / 14
    y = y0 - flat * t
    z = T / 2 + (0.006 * ((t - 0.86) / 0.14) ** 2 if t > 0.86 else 0)
    path.append((y, z))

arcl = [0.0]
for a, b in zip(path, path[1:]):
    arcl.append(arcl[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
L = arcl[-1]
nx = 14
verts, faces, uvs = [], [], []
sw = WID - 0.0016
for i, (y, z) in enumerate(path):
    flat_part = max(0.0, (arcl[i] - (L - flat)) / flat)
    for j in range(nx + 1):
        u = j / nx
        x = -sw / 2 + sw * u
        wave = 0.0018 * flat_part * math.sin(u * math.pi * 3 + 0.7) * math.sin(min(1, flat_part * 2) * math.pi / 2)
        verts.append((x, y, z + max(0.0, wave)))
for i in range(len(path) - 1):
    for j in range(nx):
        a = i * (nx + 1) + j
        faces.append((a, a + 1, a + nx + 2, a + nx + 1))
        quad_uv = []
        for (ii, jj) in ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)):
            quad_uv.append((jj / nx, (L - arcl[ii]) / SHEET))
        uvs.append(quad_uv)
me = bpy.data.meshes.new('tail'); me.from_pydata(verts, [], faces); me.update()
uvl = me.uv_layers.new(name='UVMap')
for p, quad in zip(me.polygons, uvs):
    for li, uv in zip(p.loop_indices, quad):
        uvl.data[li].uv = uv
tail = bpy.data.objects.new('tail', me); bpy.context.collection.objects.link(tail)
tail.data.materials.append(M_SHEET)
for p in me.polygons:
    p.use_smooth = True
sd = tail.modifiers.new('solid', 'SOLIDIFY'); sd.thickness = T; sd.offset = 0

kit.export('toilet-paper')
