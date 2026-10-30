"""Rain jacket (Michelle Shen): a yellow slicker standing as if worn, the way the mural shows her drawing.
From her drawing: the hood up (three panels, a stiff brim), drawstrings hanging from the collar, a
snap placket down the front, two patch pockets with snapped flaps, and the sleeves held away from the
body. Her drawing is full of birds and rain, so a small bird sits on the left shoulder and
raindrops bead on the hood and shoulders."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

kit.reset()
random.seed(13)

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
SLICKER = kit.mat('#e3a00c', rough=0.32, name='slicker')
SEAM = kit.mat('#c58410', rough=0.36, name='seam_tape')
LINING = kit.mat('#245f66', rough=0.75, name='lining')
SNAP = kit.mat('gunmetal', rough=0.3, metal=0.9, name='snap')
CORD = kit.mat('cream', rough=0.7, name='drawcord')
AGLET = kit.mat('#1e1d1c', rough=0.45, name='toggle')
DROP = kit.mat('#dcecf2', rough=0.04, alpha=0.55, name='raindrop')
BIRD = kit.mat('walnut', rough=0.7, name='bird_back')
BREAST = kit.mat('orange', rough=0.7, name='bird_breast')
BEAK = kit.mat('amber', rough=0.5, name='beak')
EYE = kit.mat('#141210', rough=0.2, name='eye')


def interp(keys, z):
    for (z0, v0), (z1, v1) in zip(keys, keys[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0); t = (1 - math.cos(math.pi * t)) / 2
            return v0 + (v1 - v0) * t
    return keys[-1][1]


def sgnpow(t, e):
    return math.copysign(abs(t) ** e, t)


# ---------- torso ----------
A = [(0.0, 0.272), (0.04, 0.27), (0.25, 0.262), (0.45, 0.258), (0.6, 0.255), (0.66, 0.246), (0.71, 0.228),
     (0.75, 0.18), (0.78, 0.125), (0.8, 0.092)]
B = [(0.0, 0.152), (0.04, 0.15), (0.25, 0.143), (0.45, 0.148), (0.6, 0.145), (0.66, 0.138), (0.71, 0.126),
     (0.75, 0.11), (0.78, 0.095), (0.8, 0.085)]
NE = 2.7


def torso_pt(th, z):
    a, b = interp(A, z), interp(B, z)
    w = 1 + 0.02 * max(0.0, 1 - z / 0.38) ** 1.5 * math.sin(7 * th + 1.3)   # soft folds toward the hem
    return Vector((a * w * sgnpow(math.cos(th), 2 / NE), b * w * sgnpow(math.sin(th), 2 / NE), z))


NT = 72
ZS = [0.0, 0.004] + [0.02 + 0.78 * (i / 25) for i in range(26)]
rings = []
# hem turned up inside: an inner wall rising 3 cm, then the outside up to the neck
inner = [Vector((p.x * 0.965, p.y * 0.94, 0.035)) for p in [torso_pt(math.tau * j / NT, 0.0) for j in range(NT)]]
rings.append(inner)
rings.append([Vector((p.x * 0.97, p.y * 0.95, 0.0)) for p in [torso_pt(math.tau * j / NT, 0.0) for j in range(NT)]])
for z in ZS[1:]:
    rings.append([torso_pt(math.tau * j / NT, z) for j in range(NT)])
torso = loft(rings, name='torso', material=SLICKER, smooth=50)
weighted_normals(torso)
# what you see looking up inside the hem
kit.extrude([(p.x, p.y) for p in inner], 0.002, at=(0, 0, 0.034), material=LINING, name='hem_inside')

# ---------- collar and hood ----------
collar = loft([[Vector((0.106 * sgnpow(math.cos(t), 2 / 2.4), 0.1 * sgnpow(math.sin(t), 2 / 2.4), z)) for t in
                [math.tau * j / 48 for j in range(48)]] for z in (0.772, 0.79, 0.85, 0.866)], name='collar', material=SLICKER, smooth=50)
kit.extrude([(0.094 * sgnpow(math.cos(t), 2 / 2.4), 0.088 * sgnpow(math.sin(t), 2 / 2.4)) for t in
             [math.tau * j / 48 for j in range(48)]], 0.002, at=(0, 0, 0.8655), material=LINING, name='collar_inside')

HC = Vector((0.0, 0.04, 0.945)); HA, HB, HCZ = 0.118, 0.158, 0.18
hood = kit.sphere(1.0, at=HC, scale=(HA, HB, HCZ), segs=56, rings=28, name='hood')
hood.data.materials.clear(); hood.data.materials.append(SLICKER)
for v in hood.data.vertices:   # flatter side panels, like the faceted hood in the drawing
    q = (v.co - HC)
    nx = q.x / HA
    v.co.x = HC.x + HA * math.copysign(abs(nx) ** 0.72, nx) * 0.93
OW, OH, OZ = 0.08, 0.1, 0.942
cut = kit.extrude([(OW * math.cos(t), -(OZ + OH * math.sin(t))) for t in [math.tau * j / 64 for j in range(64)]], 0.25, name='face')
cut.rotation_euler = (math.radians(-90), 0, 0); cut.location = (0, -0.2, 0)
kit.finish(cut, LINING, smooth=0)
bool_op(hood, cut, transfer=True)
weighted_normals(hood)


def hood_y(x, z, grow=0.0):
    """Front surface of the hood at (x, z)."""
    q = 1 - (x / (HA + grow)) ** 2 - ((z - HC.z) / (HCZ + grow)) ** 2
    return HC.y - (HB + grow) * math.sqrt(max(q, 0.0))


# stiff brim over the face opening
arc = []
for i in range(25):
    t = math.radians(18 + 144 * i / 24)
    x, z = (OW + 0.004) * math.cos(t), OZ + (OH + 0.004) * math.sin(t)
    arc.append((x, hood_y(x, z) + 0.004, z))
sweep(arc, [(-0.0022, -0.004), (0.0022, -0.004), (0.0018, 0.022), (-0.0018, 0.022)], name='brim', material=SLICKER, up=(0, 1, 0))
# binding round the rest of the opening
arc2 = []
for i in range(41):
    t = math.radians(162 + 216 * i / 40)
    x, z = (OW + 0.003) * math.cos(t), OZ + (OH + 0.003) * math.sin(t)
    arc2.append((x, hood_y(x, z) + 0.002, z))
sweep(arc2, [(0.0042 * math.cos(a), 0.0042 * math.sin(a)) for a in [i * math.tau / 10 for i in range(10)]], name='hood_binding',
      material=SLICKER, up=(0, 1, 0))
# the two seams that make it a three-panel hood, front edge over the top and down the back
for sx in (-1, 1):
    x = sx * 0.043
    k = math.sqrt(1 - (x / HA) ** 2)
    Bp, Cp = HB * k + 0.0015, HCZ * k + 0.0015
    z0 = OZ + OH + 0.006 - HC.z
    phi0 = math.asin(min(z0 / Cp, 1.0))
    pts = []
    for i in range(41):
        phi = phi0 + (math.pi + 0.55 - phi0) * i / 40
        pts.append((x, HC.y - Bp * math.cos(phi), HC.z + Cp * math.sin(phi)))
    sweep(pts, [(0.0028 * math.cos(a), 0.0028 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]], name='hood_seam',
          material=SEAM, up=(1, 0, 0))

# ---------- yoke seam round the chest and back ----------
yoke = [torso_pt(math.tau * j / 96, 0.645) for j in range(96)]
yoke = [Vector((p.x * 1.012, p.y * 1.018, p.z)) for p in yoke]
sweep(yoke, [(0.0024 * math.cos(a), 0.0024 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]], name='yoke_seam',
      material=SEAM, closed=True, up=(0, 0, 1))

# ---------- placket with snaps ----------
front = [torso_pt(-math.pi / 2, z) for z in [0.012 + 0.84 * i / 30 for i in range(31)] if z < 0.86]
front = [Vector((0, p.y - 0.0035, p.z)) for p in front]
front[-1] = Vector((0, -0.106 - 0.0035, 0.862))
sweep(front, rounded_rect(0.009, 0.056, 0.0035, n=3), name='placket', material=SLICKER, up=(0, 1, 0))
for z in (0.09, 0.22, 0.35, 0.48, 0.61, 0.72):
    p = torso_pt(-math.pi / 2, z)
    kit.cyl(0.0085, 0.0045, at=(0, p.y - 0.0095, z), rot=(90, 0, 0), material=SNAP, bevel=0.0015, verts=24, name='snap')
kit.cyl(0.0075, 0.004, at=(0, -0.106 - 0.009, 0.825), rot=(90, 0, 0), material=SNAP, bevel=0.0013, verts=24, name='collar_snap')

bpy.context.view_layer.update()


def front_hit(x, z, obj=torso):
    hit, loc, nor, idx = obj.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))
    return loc, nor


def patch(x0, x1, z0, z1, t0, t1, name, mat, nx=10, nz=10, round_bottom=0.0):
    """A panel that follows the torso's front: between offsets t0 and t1 along the surface normal."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    grid = []
    for i in range(nx + 1):
        col = []
        for j in range(nz + 1):
            x = x0 + (x1 - x0) * i / nx; z = z0 + (z1 - z0) * j / nz
            if round_bottom and j == 0:
                z += round_bottom * (1 - math.sin(math.pi * i / nx))
            loc, nor = front_hit(x, z)
            col.append((loc + nor * t0, loc + nor * t1))
        grid.append(col)
    vin = [[bm.verts.new(c[0]) for c in col] for col in grid]
    vout = [[bm.verts.new(c[1]) for c in col] for col in grid]
    for i in range(nx):
        for j in range(nz):
            bm.faces.new((vout[i][j], vout[i + 1][j], vout[i + 1][j + 1], vout[i][j + 1]))
            bm.faces.new((vin[i][j + 1], vin[i + 1][j + 1], vin[i + 1][j], vin[i][j]))
    for i in range(nx):
        bm.faces.new((vin[i][0], vin[i + 1][0], vout[i + 1][0], vout[i][0]))
        bm.faces.new((vout[i][nz], vout[i + 1][nz], vin[i + 1][nz], vin[i][nz]))
    for j in range(nz):
        bm.faces.new((vout[0][j], vout[0][j + 1], vin[0][j + 1], vin[0][j]))
        bm.faces.new((vin[nx][j], vin[nx][j + 1], vout[nx][j + 1], vout[nx][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, mat, bevel=0.0018, segments=2, smooth=40)


for sx in (-1, 1):
    cx = sx * 0.135
    patch(cx - 0.072, cx + 0.072, 0.16, 0.335, -0.002, 0.0035, 'pocket', SLICKER)
    patch(cx - 0.078, cx + 0.078, 0.31, 0.375, 0.0, 0.0085, 'pocket_flap', SLICKER, round_bottom=0.008)
    loc, nor = front_hit(cx, 0.335)
    s = kit.cyl(0.0075, 0.004, material=SNAP, bevel=0.0013, verts=24, name='flap_snap')
    s.location = loc + nor * 0.0095; s.rotation_euler = nor.to_track_quat('Z', 'Y').to_euler()

# ---------- sleeves ----------
def sleeve(sx, spread, fwd):
    top = Vector((sx * 0.185, 0.0, 0.672))
    d = Vector((sx * math.sin(math.radians(spread)), -math.sin(math.radians(fwd)), -math.cos(math.radians(spread))))
    d.normalize()
    elbow = top + d * 0.33 + Vector((0, -0.02, 0))
    cuff = elbow + (d + Vector((0, -0.12, 0.05))).normalized() * 0.29
    pts = resample([top, top + d * 0.12, elbow, cuff], 30)
    rings = []
    for i, p in enumerate(pts):
        t = i / (len(pts) - 1)
        a = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        a.normalize()
        u = a.cross(Vector((0, 1, 0))).normalized(); v = a.cross(u).normalized()
        r = 0.084 - 0.026 * t
        wr = 0.006 * math.exp(-((t - 0.52) / 0.08) ** 2)     # bunching at the elbow
        ring = []
        for j in range(40):
            th = math.tau * j / 40
            rr = r * (1 + (wr / r) * math.sin(5 * th + 2 * t))
            ring.append(p + u * rr * math.cos(th) * 1.05 + v * rr * math.sin(th) * 0.95)
        rings.append(ring)
    loft(rings, name='sleeve', material=SLICKER, smooth=50)
    # cuff band, then the dark inside of the sleeve
    a = (pts[-1] - pts[-2]).normalized()
    u = a.cross(Vector((0, 1, 0))).normalized(); v = a.cross(u).normalized()
    c = pts[-1]
    band = []
    for k, (off, rad) in enumerate(((-0.045, 0.0595), (-0.042, 0.063), (0.002, 0.063), (0.005, 0.0585), (-0.01, 0.052))):
        band.append([c + a * off + u * rad * math.cos(th) * 1.05 + v * rad * math.sin(th) * 0.95 for th in [math.tau * j / 40 for j in range(40)]])
    loft(band, name='cuff', material=SLICKER, smooth=50)
    disc = kit.cyl(0.05, 0.002, material=LINING, verts=32, name='sleeve_inside')
    disc.location = c - a * 0.012; disc.rotation_euler = a.to_track_quat('Z', 'Y').to_euler()
    # cuff tab with a snap
    tabc = c - a * 0.02 + v * 0.064
    tab = kit.box((0.03, 0.006, 0.05), material=SLICKER, bevel=0.002, name='cuff_tab')
    tab.location = tabc; tab.rotation_euler = v.to_track_quat('Y', 'Z').to_euler()
    tab.rotation_euler = Matrix((u, v, a)).transposed().to_euler()
    sn = kit.cyl(0.006, 0.004, material=SNAP, bevel=0.001, verts=20, name='cuff_snap')
    sn.location = tabc + v * 0.004; sn.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()
    return top, d


sleeve(-1, 31, 6)
sleeve(1, 25, 10)

# ---------- drawcords from the collar ----------
for sx in (-1, 1):
    x = sx * 0.042
    p0 = Vector((x, -0.1 + 0.004 * 0, 0.835))
    loc, nor = front_hit(x, 0.835, collar)
    start = loc - nor * 0.002 if loc else p0
    eye = kit.torus(0.0055, 0.0016, material=SNAP, major=16, minor=6, name='cord_eyelet')
    eye.location = start + nor * 0.001; eye.rotation_euler = nor.to_track_quat('Z', 'Y').to_euler()
    path = [start, start + Vector((sx * 0.004, -0.012, -0.02))]
    for z in (0.76, 0.7, 0.66):
        q = torso_pt(-math.pi / 2 + sx * 0.2, z)
        path.append(Vector((x + sx * 0.002 * (0.76 - z) * 10, q.y - 0.016, z)))
    path = resample(path, 20)
    sweep(path, [(0.0026 * math.cos(a), 0.0026 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]], name='cord', material=CORD)
    end = path[-1]
    kit.cyl(0.0055, 0.022, at=end + Vector((0, 0, -0.008)), material=AGLET, bevel=0.002, verts=16, name='cord_toggle')

# ---------- a bird on the left shoulder ----------
bpy.context.view_layer.update()
hit, sh, nor, idx = torso.ray_cast(Vector((-0.2, 0.01, 1.2)), Vector((0, 0, -1)))
base = sh + Vector((0, 0, 0.003))
BS = 1.35  # bird scale
bird = []
body = kit.sphere(1.0, at=base + BS * Vector((0, 0.004, 0.034)), scale=(0.024 * BS, 0.036 * BS, 0.024 * BS), material=BIRD, segs=24, rings=12, name='bird_body')
body.rotation_euler = (math.radians(-15), 0, math.radians(-25))
breast = kit.sphere(1.0, at=base + BS * Vector((0.004, -0.012, 0.03)), scale=(0.02 * BS, 0.022 * BS, 0.021 * BS), material=BREAST, segs=24, rings=12, name='bird_breast')
breast.rotation_euler = (math.radians(-15), 0, math.radians(-25))
head = kit.sphere(0.0155 * BS, at=base + BS * Vector((0.009, -0.026, 0.062)), material=BIRD, segs=24, rings=12, name='bird_head')
bk = kit.cyl(0.0042 * BS, 0.012 * BS, r2=0.0, material=BEAK, verts=12, name='beak')
bk.location = base + BS * Vector((0.014, -0.044, 0.061)); bk.rotation_euler = (math.radians(95), 0, math.radians(-25))
for sx in (-1, 1):
    e = kit.sphere(0.0028 * BS, at=base + BS * Vector((0.009 + sx * 0.0125, -0.033, 0.066)), material=EYE, segs=12, rings=6, name='bird_eye')
tail = kit.extrude([(-0.011 * BS, 0), (0.011 * BS, 0), (0.007 * BS, 0.034 * BS), (-0.007 * BS, 0.034 * BS)], 0.004, name='bird_tail')
tail.location = base + BS * Vector((-0.008, 0.03, 0.03)); tail.rotation_euler = (math.radians(-60), 0, math.radians(-25))
kit.finish(tail, BIRD, bevel=0.001)
for sx in (-1, 1):
    wing = kit.sphere(1.0, at=base + BS * Vector((sx * 0.02 - 0.003, 0.01, 0.038)), scale=(0.006 * BS, 0.028 * BS, 0.016 * BS), material=BIRD, segs=16, rings=8, name='bird_wing')
    wing.rotation_euler = (math.radians(-20), 0, math.radians(-25))
    kit.cyl(0.0013 * BS, 0.012 * BS, at=base + BS * Vector((sx * 0.006, -0.004, 0.006)), material=BEAK, verts=8, name='bird_leg')

# ---------- raindrops beading on the hood and shoulders ----------
drops = 0
tries = 0
while drops < 16 and tries < 400:
    tries += 1
    x = random.uniform(-0.27, 0.27); y = random.uniform(-0.14, 0.17)
    best = None
    for o in (hood, torso):
        hit, loc, nor, idx = o.ray_cast(Vector((x, y, 1.4)), Vector((0, 0, -1)))
        if hit and (best is None or loc.z > best[0].z):
            best = (loc, nor)
    if best is None or best[1].z < 0.45 or (abs(x + 0.2) < 0.06 and abs(y) < 0.06):
        continue
    loc, nor = best
    r = random.uniform(0.0045, 0.0085)
    d = kit.sphere(r, scale=(1, 1, 0.55), material=DROP, segs=16, rings=8, name='raindrop')
    d.location = loc + nor * r * 0.15; d.rotation_euler = nor.to_track_quat('Z', 'Y').to_euler()
    drops += 1

kit.export('rain-jacket')
