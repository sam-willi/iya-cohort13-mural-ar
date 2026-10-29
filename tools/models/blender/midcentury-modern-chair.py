"""Midcentury mod chair (Ame Wang): her leather lounge chair and ottoman, with everything she put on it.
Walnut frame: a "#" lattice down the right side, legs and a runner on the left carrying a side shelf
with the "BUIN" briefcase. Cognac leather seat, an upholstered lower back with the "acad" pillow
leaning on it, and the tufted back cushion on two posts. Behind it rises the light bulb with a "13"
filament on a gear collar with its antenna. In front, the ottoman on a four-star base with a pair
of high-tops on it."""
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
WALNUT = kit.mat('walnut', rough=0.55, name='walnut')
LEATHER = kit.mat('#8a4622', rough=0.48, name='cognac_leather')
BUTTON = kit.mat('#5e3317', rough=0.45, name='button')
CASE = kit.mat('cardinal', rough=0.5, name='briefcase')
BRASS = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
CREAMM = kit.mat('cream', rough=0.6, name='cream')
ALU = kit.mat('chrome', rough=0.28, metal=1.0, name='aluminium')
GLIDE = kit.mat('black', rough=0.6, name='glide')
GLASSM = kit.mat('#f3ead2', rough=0.05, alpha=0.16, name='bulb_glass')
FILAMENT = kit.mat('#f0a020', rough=0.4, emit=6.0, name='filament')
WHITE = kit.mat('white', rough=0.55, name='shoe_white')
SHOE_RED = kit.mat('red', rough=0.55, name='shoe_red')
SOLE = kit.mat('#e9e0cc', rough=0.7, name='shoe_sole')
DARK = kit.mat('#2a2522', rough=0.8, name='shoe_inside')


def planar_uv(o, axes=(0, 2), scale=1.0, offset=(0.0, 0.0)):
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (co[axes[0]] * scale + offset[0], co[axes[1]] * scale + offset[1])


def cushion(size, name, mat, sub=2, bulge=0.0, tufts=(), tuft_depth=0.0, bevel_frac=0.32):
    """A leather cushion built facing -Y (thickness along Y): rounded box, smoothed, front and back
    puffed by `bulge`, optional button tufts pulled into the front with creases running out of them."""
    sx, sy, sz = size
    o = kit.box(size, bevel=min(size) * bevel_frac, segments=2, name=name)
    apply_all(o)
    if tufts:
        # give the front face enough vertices to carry the dimples
        bm = bmesh.new(); bm.from_mesh(o.data)
        front = max(bm.faces, key=lambda f: (-f.normal.y) * f.calc_area())
        bmesh.ops.subdivide_edges(bm, edges=list(front.edges), cuts=10, use_grid_fill=True)
        bm.to_mesh(o.data); bm.free()
    md = o.modifiers.new('sub', 'SUBSURF'); md.levels = sub; md.render_levels = sub
    apply_all(o)
    hx, hz = sx / 2, sz / 2
    for v in o.data.vertices:
        x, y, z = v.co
        fx = max(0.0, 1 - (x / hx) ** 2); fz = max(0.0, 1 - (z / hz) ** 2)
        side = -1 if y < 0 else 1
        v.co.y += side * bulge * fx * fz
        if y < 0 and tufts:
            dy = 0.0
            for tx, tz in tufts:
                dx, dz = x - tx, z - tz
                r2 = dx * dx + dz * dz
                dy += tuft_depth * math.exp(-r2 / 0.0011)
                # four creases running diagonally out of each button
                ang = math.atan2(dz, dx)
                crease = abs(math.sin(2 * ang)) ** 18
                dy += 0.35 * tuft_depth * crease * math.exp(-r2 / 0.006)
            v.co.y += dy * fx * fz
    o.data.update()
    return kit.finish(o, mat, smooth=60)


def place(o, loc, rot_deg=(0, 0, 0)):
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot_deg]
    return o


def bar(p0, p1, w, mat=WALNUT, name='bar'):
    """A square wooden bar from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = kit.box((w, w, d.length), material=mat, bevel=0.004, segments=2, name=name)
    o.location = (p0 + p1) / 2
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return o


# =====================================================================
# Chair frame
# =====================================================================
FX = 0.34          # side frames sit at x = +-FX
P = 0.046          # bar thickness
# right side: the "#" lattice
for y in (-0.27, 0.02, 0.29):
    bar((FX, y, 0.0), (FX, y, 0.64), P, name='lattice_post')
bar((FX, -0.37, 0.56), (FX, 0.37, 0.56), P, name='lattice_top_rail')
bar((FX, -0.43, 0.04), (FX, 0.42, 0.04), P, name='lattice_runner')
bar((FX, -0.32, 0.25), (FX, 0.33, 0.25), P, name='lattice_mid_rail')
# left side: legs, runner poking out the front, seat rail
for y in (-0.27, 0.29):
    bar((-FX, y, 0.0), (-FX, y, 0.42), P, name='left_leg')
bar((-FX, -0.45, 0.04), (-FX, 0.4, 0.04), P, name='left_runner')
bar((-FX, -0.32, 0.25), (-FX, 0.33, 0.25), P, name='left_mid_rail')
# stretchers across under the seat, and the seat deck
for y in (-0.27, 0.29):
    bar((-FX, y, 0.2), (FX, y, 0.2), 0.04, name='stretcher')
kit.box((2 * FX - 0.02, 0.62, 0.035), at=(0, 0.01, 0.245), material=WALNUT, bevel=0.006, name='seat_deck')
# back: a walnut panel behind the lower back cushion, two posts carrying the tufted cushion
back = kit.box((2 * FX - 0.02, 0.05, 0.42), material=WALNUT, bevel=0.008, name='back_panel')
place(back, (0, 0.335, 0.47), (-8, 0, 0))
for x in (-0.17, 0.17):
    post = kit.cyl(0.017, 0.14, material=WALNUT, bevel=0.003, verts=20, name='back_post')
    place(post, (x, 0.38, 0.715), (-14, 0, 0))

# side shelf on the left, with its rolled front lip and a brace under the outer end
SH_X0, SH_X1, SH_Y0, SH_Y1, SH_Z = -FX - 0.02, -0.68, -0.17, 0.2, 0.42
shelf = kit.box((SH_X0 - SH_X1, SH_Y1 - SH_Y0, 0.028), at=((SH_X0 + SH_X1) / 2, (SH_Y0 + SH_Y1) / 2, SH_Z + 0.014),
                material=WALNUT, bevel=0.005, name='shelf')
kit.box((SH_X0 - SH_X1, 0.03, 0.06), at=((SH_X0 + SH_X1) / 2, SH_Y0 + 0.004, SH_Z), material=WALNUT, bevel=0.013, segments=3,
        name='shelf_lip')
bar((-FX - 0.02, 0.0, 0.2), (SH_X1 + 0.06, 0.0, SH_Z - 0.002), 0.035, name='shelf_brace')
bar((-FX - 0.02, 0.0, 0.25), (-FX - 0.02, 0.0, SH_Z), 0.035, name='shelf_upright')

# =====================================================================
# Cushions
# =====================================================================
seat = cushion((0.64, 0.15, 0.6), 'seat_cushion', LEATHER, sub=2, bulge=0.018)
place(seat, (0, -0.0, 0.335), (-90, 0, 0))
lower = cushion((0.62, 0.11, 0.3), 'lower_back', LEATHER, sub=2, bulge=0.012)
place(lower, (0, 0.27, 0.53), (-8, 0, 0))
TUFTS = [(-0.13, 0.08), (0.13, 0.08), (-0.13, -0.09), (0.13, -0.09)]
upper = cushion((0.62, 0.12, 0.44), 'back_cushion', LEATHER, sub=2, bulge=0.02, tufts=TUFTS, tuft_depth=0.026)
place(upper, (0, 0.43, 0.97), (-14, 0, 0))
bpy.context.view_layer.update()
for tx, tz in TUFTS:
    hit, loc, nor, idx = upper.ray_cast(Vector((tx, -0.5, tz)), Vector((0, 1, 0)))
    b = kit.cyl(0.013, 0.008, material=BUTTON, bevel=0.003, verts=20, name='tuft_button')
    b.location = upper.matrix_world @ (loc + Vector((0, 0.002, 0)))
    b.rotation_euler = (math.radians(90 - 14), 0, 0)

# "acad" pillow leaning on the lower back
pil_img = pil_texture('acad', """
img.paste((239, 227, 200), (0, 0, S, S))
try:
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf', 185)
except Exception:
    f = font(150, bold=False)
d.text((S // 2, S // 2), 'acad', font=f, fill=(90, 58, 34), anchor='mm')
d.rectangle([14, 14, S - 14, S - 14], outline=(200, 186, 160), width=6)
""", size=512)
PILLOW = tex_mat(pil_img, rough=0.75, name='pillow')
pillow = cushion((0.34, 0.1, 0.26), 'pillow', PILLOW, sub=2, bulge=0.025, bevel_frac=0.45)
planar_uv(pillow, axes=(0, 2), scale=1 / 0.34, offset=(0.5, 0.5 * 0.26 / 0.34 + 0.0))
for l in pillow.data.uv_layers.active.data:
    l.uv = (l.uv[0], (l.uv[1] - 0.5 * 0.26 / 0.34) * 0.34 / 0.26 + 0.5)
place(pillow, (0.12, 0.19, 0.53), (-22, 0, -8))

# =====================================================================
# Briefcase on the shelf
# =====================================================================
BX, BY, BW, BD, BH = (SH_X0 + SH_X1) / 2, 0.03, 0.27, 0.085, 0.21
bc = kit.box((BW, BD, BH), at=(BX, BY, SH_Z + 0.028 + BH / 2), material=CASE, bevel=0.012, segments=3, name='briefcase')
kit.box((BW + 0.003, BD + 0.003, 0.006), at=(BX, BY, SH_Z + 0.028 + BH - 0.035), material=kit.mat('#7a1a17', rough=0.5, name='case_seam'),
        bevel=0.002, name='case_seam')
txt = text_obj('BUIN', 0.075, 0.004, name='buin')
txt.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
txt.location = (BX, BY - BD / 2 + 0.0015, SH_Z + 0.028 + BH * 0.45)
txt.data.materials.append(CREAMM)
for s in (-1, 1):
    kit.box((0.026, 0.008, 0.02), at=(BX + s * 0.085, BY - BD / 2 + 0.001, SH_Z + 0.028 + BH - 0.035), material=BRASS, bevel=0.002, name='case_latch')
    kit.box((0.016, 0.03, 0.01), at=(BX + s * 0.04, BY, SH_Z + 0.028 + BH + 0.004), material=BRASS, bevel=0.002, name='handle_mount')
hp = [(BX - 0.04, BY, SH_Z + 0.028 + BH + 0.006)]
for i in range(1, 16):
    a = math.pi * i / 16
    hp.append((BX - 0.04 * math.cos(a), BY, SH_Z + 0.028 + BH + 0.006 + 0.045 * math.sin(a)))
hp.append((BX + 0.04, BY, SH_Z + 0.028 + BH + 0.006))
sweep(hp, rounded_rect(0.012, 0.018, 0.005, n=2), name='case_handle', material=CASE, up=(0, 1, 0))

# =====================================================================
# Light bulb with the "13" filament, rising behind the back cushion
# =====================================================================
G = Vector((0.13, 0.56, 1.24))      # gear collar centre
gear = []
for i in range(48):
    a = math.tau * i / 48
    r = 0.05 if (i // 3) % 2 == 0 else 0.042
    gear.append((r * math.cos(a), r * math.sin(a)))
g = kit.extrude(gear, 0.014, name='gear')
g.location = G - Vector((0, 0, 0.007)); kit.finish(g, BRASS, bevel=0.0015, smooth=0)
kit.cyl(0.018, 0.016, at=G + Vector((0, 0, 0.006)), material=BRASS, bevel=0.002, verts=24, name='gear_hub')
sock = kit.lathe([(0, 0), (0.024, 0), (0.024, 0.006)] + [(0.0225 + 0.0025 * (k % 2), 0.006 + 0.005 * k) for k in range(1, 10)] +
                 [(0.021, 0.055), (0, 0.055)], material=BRASS, steps=32, name='socket')
sock.location = G + Vector((0, 0, 0.012))
bulb = kit.lathe([(0, 0.0), (0.02, 0.0), (0.03, 0.03), (0.062, 0.085), (0.07, 0.125), (0.064, 0.165), (0.045, 0.195),
                  (0.02, 0.21), (0, 0.212)], material=GLASSM, steps=48, name='bulb')
bulb.location = G + Vector((0, 0, 0.064))
# filament: two lead wires up a glass stem, the "13" glowing between them
kit.cyl(0.006, 0.05, at=G + Vector((0, 0, 0.09)), material=GLASSM, verts=12, name='stem')
for s in (-1, 1):
    kit.cyl(0.0012, 0.07, at=G + Vector((s * 0.012, 0, 0.115)), material=BRASS, verts=6, name='lead')
f13 = text_obj('13', 0.085, 0.004, name='filament_13')
f13.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
f13.location = G + Vector((0, 0.001, 0.19))
f13.data.materials.append(FILAMENT)
# antenna out of the gear, and the curly wire down to the cushion back
ant0 = G + Vector((0.045, -0.005, -0.004))
ant1 = ant0 + Vector((0.12, -0.03, -0.08))
ant = kit.cyl(0.0025, (ant1 - ant0).length, material=ALU, verts=8, name='antenna')
ant.location = (ant0 + ant1) / 2; ant.rotation_euler = (ant1 - ant0).to_track_quat('Z', 'Y').to_euler()
kit.sphere(0.008, at=ant1, material=ALU, segs=12, rings=6, name='antenna_tip')
wire = []
for i in range(40):
    t = i / 39
    a = t * math.tau * 2.2
    base = G.lerp(Vector((0.13, 0.5, 1.12)), t)
    wire.append(base + Vector((0.025 * math.cos(a), 0.02 * math.sin(a), 0)))
sweep(wire, [(0.003 * math.cos(a), 0.003 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]], name='coil_wire', material=BRASS)
# bracket fixing it to the back cushion
bar((0.13, 0.5, 1.12), (0.13, 0.5, 1.235), 0.012, mat=BRASS, name='bulb_bracket')

# =====================================================================
# Ottoman with high-tops
# =====================================================================
O = Vector((-0.17, -0.82, 0.0))
ott = cushion((0.54, 0.13, 0.44), 'ottoman', LEATHER, sub=2, bulge=0.02)
place(ott, O + Vector((0, 0, 0.37)), (-90, 0, 0))
kit.box((0.3, 0.26, 0.025), at=O + Vector((0, 0, 0.297)), material=WALNUT, bevel=0.006, name='ottoman_plate')
kit.cyl(0.03, 0.09, at=O + Vector((0, 0, 0.245)), material=ALU, bevel=0.004, verts=24, name='swivel')
kit.cyl(0.05, 0.03, at=O + Vector((0, 0, 0.2)), material=ALU, bevel=0.006, verts=24, name='hub')
for k in range(4):
    a = math.radians(45 + 90 * k)
    tip = O + Vector((0.3 * math.cos(a), 0.26 * math.sin(a), 0.035))
    hub = O + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), 0.2))
    leg = kit.cyl(0.018, (tip - hub).length, r2=0.009, material=ALU, verts=16, name='star_leg')
    leg.location = (tip + hub) / 2; leg.rotation_euler = (hub - tip).to_track_quat('Z', 'Y').to_euler()
    kit.cyl(0.018, 0.024, at=tip + Vector((0, 0, -0.022)), material=GLIDE, bevel=0.004, verts=20, name='glide')


def high_top(at, yaw):
    """A small white high-top with a red collar, toes toward -Y before turning by yaw."""
    N = 40

    def ell(cy, ry, rx, z, grow=1.0):
        return [Vector((rx * grow * math.cos(a) * (1.08 if math.sin(a) < 0 else 1), cy + ry * grow * math.sin(a), z))
                for a in [math.tau * i / N for i in range(N)]]
    objs = [loft([ell(0, 0.138, 0.044, 0.0), ell(0, 0.14, 0.046, 0.004), ell(0, 0.143, 0.047, 0.012), ell(0, 0.142, 0.047, 0.024)],
                 name='hightop_sole', material=SOLE, smooth=40)]
    rings = []
    for k in range(13):
        t = k / 12
        # the footprint morphs into an ankle opening over the heel, the toe staying low
        rings.append(ell(0.07 * t, 0.137 * (1 - 0.62 * t), 0.045 * (1 - 0.16 * t), 0.022 + 0.13 * t ** 1.5))
    objs.append(loft(rings, name='hightop_upper', material=WHITE, cap_end=False, smooth=50))
    objs.append(loft([ell(0.07, 0.137 * 0.38, 0.045 * 0.84, z, 1.06) for z in (0.12, 0.13, 0.155)], name='hightop_collar',
                     material=SHOE_RED, smooth=50))
    o = kit.cyl(0.036, 0.002, at=(0, 0.07, 0.15), material=DARK, verts=24, name='hightop_opening')
    o.scale = (1.0, 1.4, 1.0); objs.append(o)
    # toe cap and a lace ladder up the front
    objs.append(loft([ell(0, 0.138 * 1.012, 0.045 * 1.012, z) for z in (0.022, 0.032)], name='hightop_foxing', material=SHOE_RED, smooth=40))
    for k in range(5):
        t = 0.3 + k * 0.11
        q = Vector((0, 0.07 * t - 0.137 * (1 - 0.62 * t), 0.022 + 0.13 * t ** 1.5))
        objs.append(kit.box((0.034, 0.006, 0.005), at=q + Vector((0, 0.004, 0.004)), rot=(-50, 0, 0), material=CREAMM, bevel=0.002, name='lace'))
    M = Matrix.Translation(at) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
    bpy.context.view_layer.update()
    for o in objs:
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
        o.data.transform(M)


top_z = 0.37 + 0.065 + 0.018
high_top(O + Vector((-0.1, 0.03, top_z)), 12)
high_top(O + Vector((0.09, -0.02, top_z)), -18)

kit.export('midcentury-modern-chair')
