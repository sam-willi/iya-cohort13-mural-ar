"""Backpack (Asher Lasky): a tall school pack built in layers like his drawing: the main compartment
and a front compartment, each with an arched top and a zip with a pair of pulls, a front pocket
laced with a crisscross shock cord, dark mesh bottle pockets on both sides, a grab loop and two
padded shoulder straps on the back."""
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
NYLON = kit.mat('#a5261f', rough=0.7, name='nylon')
BLACK = kit.mat('#232120', rough=0.75, name='black_webbing')
PAD = kit.mat('#2b2927', rough=0.85, name='strap_pad')
ZIP = kit.mat('#1d1c1b', rough=0.55, name='zip_tape')
METAL = kit.mat('steel', rough=0.3, metal=0.9, name='slider')
CORD = kit.mat('cream', rough=0.7, name='shock_cord')
HOOK = kit.mat('#1a1918', rough=0.45, name='hook')


# ---------- outline + soft-slab builders ----------

def rrect2(w, h, rt, rb, n=10, z0=0.0, sag=0.0):
    """Outline in (x, z): width w, height h from z0, top corner radius rt, bottom rb, CCW from bottom centre.
    sag lowers the middle of the top edge (a seam that dips)."""
    pts = [(0, z0)]
    def arc(cx, cz, r, a0, a1):
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    arc(w / 2 - rb, z0 + rb, rb, -90, 0)
    arc(w / 2 - rt, z0 + h - rt, rt, 0, 90)
    if sag:
        for i in range(1, 16):
            x = (w / 2 - rt) * (1 - 2 * i / 16)
            pts.append((x, z0 + h - sag * (1 - (x / (w / 2 - rt)) ** 2)))
    arc(-w / 2 + rt, z0 + h - rt, rt, 90, 180)
    arc(-w / 2 + rb, z0 + rb, rb, 180, 270)
    return pts


def slab(outline, y_front, y_back, er, name, mat, bulge=0.0, er_back=None, N=80, back_cap=True):
    """A soft panel: the outline (x, z) pushed along Y from y_front to y_back, edges rounded with radius er,
    the front face optionally bowed forward by `bulge`. Rings are the outline shrunk toward its centre."""
    er_back = er if er_back is None else er_back
    ring0 = resample([(x, z) for x, z in outline], N, closed=True)
    xs = [p.x for p in ring0]; zs = [p.y for p in ring0]
    cx, cz = (max(xs) + min(xs)) / 2, (max(zs) + min(zs)) / 2
    W, H = max(xs) - min(xs), max(zs) - min(zs)

    def ring(delta, y):
        sx, sz = (W - 2 * delta) / W, (H - 2 * delta) / H
        return [Vector((cx + (p.x - cx) * sx, y, cz + (p.y - cz) * sz)) for p in ring0]

    rings = []
    # back face fillet (from the back face toward the front)
    for i in range(7):
        t = math.pi / 2 * (1 - i / 6)
        rings.append(ring(er_back * (1 - math.cos(t)), y_back - er_back + er_back * math.sin(t)))
    # front face fillet
    for i in range(7):
        t = math.pi / 2 * i / 6
        rings.append(ring(er * (1 - math.cos(t)), y_front + er - er * math.sin(t)))
    if bulge:
        for i in range(1, 6):
            f = i / 6
            rings.append(ring(er + (min(W, H) / 2 - er) * f * 0.85, y_front - bulge * math.sin(f * math.pi / 2)))
    o = loft(rings, name=name, material=mat, cap_start=back_cap, cap_end=True, smooth=60)
    return o


def top_z(outline, x):
    """Height of an outline's top edge at x."""
    best = -1
    P = resample(outline, 400, closed=True)
    for a, b in zip(P, P[1:] + P[:1]):
        if (a.x - x) * (b.x - x) <= 0 and a.x != b.x:
            t = (x - a.x) / (b.x - a.x); best = max(best, a.y + (b.y - a.y) * t)
    return best


def planar_uv(o, axes=(1, 2), scale=1.0):
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (co[axes[0]] * scale, co[axes[1]] * scale)


# ---------- body ----------
W, H = 0.31, 0.46
MAIN = rrect2(W, H, 0.125, 0.045)
FRONT = rrect2(W - 0.012, H - 0.03, 0.118, 0.045)
YB, YM, YF = 0.105, -0.003, -0.074      # back face, main/front split, front face

main = slab(MAIN, YM, YB, 0.02, 'main', NYLON, er_back=0.035)
weighted_normals(main)
front = slab(FRONT, YF, YM - 0.006, 0.026, 'front_compartment', NYLON, bulge=0.008, er_back=0.016)
# the seam between them, sunk in the groove the two rounded edges make
slab(rrect2(W - 0.03, H - 0.035, 0.11, 0.035, z0=0.012), YM - 0.012, YM + 0.006, 0.004, 'seam_core', NYLON)

# zips: dark tape round the top half of each compartment's front edge, pulls at the top
def zip_path(outline, y, inset, zmin):
    P = resample(outline, 300, closed=True)
    xs = [p.x for p in P]; zs = [p.y for p in P]
    cx, cz = (max(xs) + min(xs)) / 2, (max(zs) + min(zs)) / 2
    Wd, Hd = max(xs) - min(xs), max(zs) - min(zs)
    sx, sz = (Wd - 2 * inset) / Wd, (Hd - 2 * inset) / Hd
    pts = [(cx + (p.x - cx) * sx, y, cz + (p.y - cz) * sz) for p in P]
    pts = [p for p in pts if p[2] > zmin]
    ang = lambda p: math.atan2(p[2] - cz, p[0] - cx)
    pts.sort(key=lambda p: ang(p) + (math.tau if ang(p) < -math.pi / 2 else 0))
    return pts


for outline, y, inset, tag in ((MAIN, YM - 0.0035, 0.0045, 'main'), (FRONT, YF + 0.012, -0.0005, 'front')):
    pts = zip_path(outline, y, inset, 0.2)
    path = resample(pts, 120)
    sweep(path, rounded_rect(0.0035, 0.011, 0.001, n=1) if tag == 'main' else rounded_rect(0.0034, 0.009, 0.001, n=1),
          name=f'zip_{tag}', material=ZIP, up=(0, 1, 0))
    # two pulls meeting at the top, their tabs lying flat along the zip, one each way
    for sx in (-1, 1):
        x = sx * 0.011
        z = top_z(outline, x) - inset
        kit.box((0.014, 0.008, 0.006), at=(x, y, z + 0.0035), material=METAL, bevel=0.0018, name='slider')
        xt = sx * 0.034
        zt = top_z(outline, xt) - inset
        slope = math.degrees(math.atan2(top_z(outline, xt + 0.005) - top_z(outline, xt - 0.005), 0.01))
        kit.box((0.032, 0.0095, 0.0032), at=(xt, y, zt + 0.0052), rot=(0, -slope, 0), material=HOOK, bevel=0.0014, name='pull_tab')
        kit.torus(0.0034, 0.0009, at=(sx * 0.018, y, z + 0.005), rot=(90, 0, 0), material=METAL, major=16, minor=6, name='pull_ring')

# ---------- front pocket with crisscross shock cord ----------
PW, PH = W - 0.03, 0.27
POCKET = rrect2(PW, PH, 0.035, 0.04, z0=0.004, sag=0.012)
YP = YF - 0.03
pocket = slab(POCKET, YP, YF + 0.012, 0.014, 'front_pocket', NYLON, er_back=0.005)
weighted_normals(pocket)
# binding along the pocket's top edge
tp = [(x, z) for x, z in resample(POCKET, 300, closed=True) if z > 0.004 + PH - 0.04]
tp.sort(key=lambda p: p[0])
edge = [(x * 0.985, YP + 0.006, z - 0.004) for x, z in tp if abs(x) < PW / 2 - 0.02]
sweep(resample(edge, 60), [(0.0035 * math.cos(a), 0.0035 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]],
      name='pocket_binding', material=BLACK)
# hooks on both edges, cord laced across in X's
HX = PW / 2 - 0.022
levels = [0.215, 0.155, 0.095, 0.035]
for z in levels:
    for sx in (-1, 1):
        kit.box((0.012, 0.006, 0.014), at=(sx * HX, YP - 0.0018, z + 0.004), material=HOOK, bevel=0.002, name='cord_hook')
cy = YP - 0.0052
a_side = [(HX if i % 2 == 0 else -HX, cy, z + 0.004) for i, z in enumerate(levels)]
b_side = [(-HX if i % 2 == 0 else HX, cy, z + 0.004) for i, z in enumerate(levels)]
for pts in (a_side, b_side):
    sweep(pts, [(0.0021 * math.cos(a), 0.0021 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]],
          name='cord', material=CORD)
sweep([(-HX, cy, levels[0] + 0.004), (HX, cy, levels[0] + 0.004)],
      [(0.0021 * math.cos(a), 0.0021 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]], name='cord_top', material=CORD)
# a cord lock at the bottom end
kit.cyl(0.0055, 0.014, at=(HX - 0.012, cy - 0.003, levels[-1] - 0.004), rot=(0, 90, 0), material=HOOK, verts=16, bevel=0.0015, name='cord_lock')

# ---------- side mesh pockets ----------
mesh_img = pil_texture('mesh', """
img.paste((34, 33, 32), (0, 0, S, S))
step = S // 16
for i in range(-16, 33):
    d.line([(i * step, 0), (i * step + S, S)], fill=(70, 68, 66), width=step // 4)
    d.line([(i * step, S), (i * step + S, 0)], fill=(70, 68, 66), width=step // 4)
""", size=256)
MESH = tex_mat(mesh_img, rough=0.85, name='side_mesh')
SIDE = rrect2(0.16, 0.17, 0.006, 0.04)
for sx in (-1, 1):
    p = slab([(z_x, z_z) for z_x, z_z in SIDE], -(W / 2 + 0.022), -(W / 2 - 0.01), 0.012, 'mesh_pocket', MESH,
             bulge=0.006, er_back=0.002)
    # outline x is the pack's depth (y), the slab's y is outward along the side
    p.rotation_euler = (0, 0, math.radians(90 if sx > 0 else -90))
    p.location = (0, 0.02, 0)
    bpy.context.view_layer.update()
    planar_uv(p, axes=(1, 2), scale=8.0)
    # elastic binding along the top
    sweep([(sx * (W / 2 + 0.017), 0.02 + y, 0.166) for y in (-0.072, -0.03, 0.03, 0.072)],
          [(0.0034 * math.cos(a), 0.0034 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]],
          name='mesh_binding', material=BLACK)

# ---------- back: padding, grab loop, shoulder straps ----------
for sx in (-1, 1):
    bp = slab(rrect2(0.11, 0.25, 0.04, 0.04, z0=0.13), YB - 0.01, YB + 0.012, 0.002, 'back_pad', PAD, er_back=0.008)
    bp.location.x = sx * 0.066
# grab loop
gt = top_z(MAIN, 0.0)
loop = []
for i in range(25):
    a = math.pi * i / 24
    loop.append((-0.045 * math.cos(a), 0.07, gt - 0.012 + 0.045 * math.sin(a)))
sweep(loop, rounded_rect(0.0055, 0.024, 0.002, n=2), name='grab_loop', material=BLACK, up=(0, 1, 0))
for sx in (-1, 1):
    kit.box((0.03, 0.03, 0.004), at=(sx * 0.045, 0.07, top_z(MAIN, sx * 0.045) - 0.0005), material=BLACK, bevel=0.0012, name='loop_tab')
# padded shoulder straps: from under the grab loop, an S-curve down the back to the bottom corners
for sx in (-1, 1):
    ctrl = [(sx * 0.05, YB - 0.012, 0.415), (sx * 0.06, YB + 0.02, 0.4), (sx * 0.075, YB + 0.045, 0.34),
            (sx * 0.095, YB + 0.052, 0.25), (sx * 0.11, YB + 0.044, 0.17), (sx * 0.118, YB + 0.03, 0.115)]
    cu = bpy.data.curves.new('sp', 'CURVE'); cu.dimensions = '3D'
    spl = cu.splines.new('NURBS'); spl.points.add(len(ctrl) - 1)
    for p, c in zip(spl.points, ctrl):
        p.co = (*c, 1)
    spl.use_endpoint_u = True; spl.order_u = 4
    tmp = bpy.data.objects.new('sp', cu); bpy.context.collection.objects.link(tmp)
    pts = [Vector(p.co[:3]) for p in spl.points]
    # evaluate the curve by converting to mesh
    cu.resolution_u = 24
    bpy.context.view_layer.objects.active = tmp
    bpy.ops.object.select_all(action='DESELECT'); tmp.select_set(True)
    bpy.ops.object.convert(target='MESH')
    tmp = bpy.context.object
    vs = [v.co.copy() for v in tmp.data.vertices]
    bpy.data.objects.remove(tmp, do_unlink=True)
    path = resample(vs, 60)
    sweep(path, rounded_rect(0.022, 0.064, 0.009, n=4), name='strap_pad', material=PAD, up=(1, 0, 0))
    # webbing from the pad down to the bottom corner, with a ladder-lock buckle
    end = path[-1]
    web = [end + Vector((0, -0.004, 0.02)), end + Vector((sx * 0.006, -0.006, -0.03)), Vector((sx * 0.13, YB - 0.004, 0.03))]
    sweep(resample(web, 20), rounded_rect(0.0035, 0.026, 0.001, n=1), name='webbing', material=BLACK, up=(1, 0, 0))
    kit.box((0.034, 0.008, 0.02), at=end + Vector((sx * 0.002, -0.004, -0.018)), rot=(18, 0, 0), material=HOOK, bevel=0.0025, name='ladder_lock')
    kit.box((0.032, 0.006, 0.03), at=(sx * 0.13, YB - 0.001, 0.03), material=BLACK, bevel=0.002, name='web_anchor')

kit.export('backpack')
