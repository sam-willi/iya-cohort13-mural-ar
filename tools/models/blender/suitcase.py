"""Suitcase (Maddie Cheng): a stack of two cases, as in her drawing. The big trunk below has dark
leather corner caps, two buckled straps running over the top and down the front, a front grip
between them and a framed panel on each end. The smaller case on top has a seam round its middle,
two clasps and a centre lock with a D pull, and two stripes across the lid."""
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
TAN = kit.mat('#8e5d33', rough=0.55, name='trunk_leather')
DARK = kit.mat('walnut', rough=0.6, name='dark_leather')
WELT = kit.mat('#3a2616', rough=0.7, name='welt')
BRASS = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
TEAL = kit.mat('teal', rough=0.5, name='case_leatherette')
CREAM = kit.mat('cream', rough=0.55, name='stripe')
HOLE = kit.mat('#1c140d', rough=0.8, name='hole')

LIFT = 0.0035  # the bottom corner caps stand 3.5 mm proud of the trunk


def ybox_section_path(D, H, r, off, z0, zc, z_end, n=10):
    """Points in (y, z) round a D x H rounded section (centre zc, corner radius r) offset outward by `off`:
    up the back from z0, over the top, down the front to z_end."""
    pts = rounded_rect(D + 2 * off, H + 2 * off, r + off, n=n, cy=zc)
    k = n + 1
    top = pts[:2 * k]   # (+y,+z) corner then (-y,+z) corner
    path = [(D / 2 + off, z0)] + top + [(-D / 2 - off, z_end)]
    return path


def frame_cutter(w, h, r, depth, name):
    return kit.extrude(rounded_rect(w, h, r, n=6), depth, name=name)


# =====================================================================
# Bottom trunk
# =====================================================================
L, D, H, R = 0.78, 0.54, 0.32, 0.04
Z0 = LIFT
trunk = kit.box((L, D, H), at=(0, 0, Z0 + H / 2), material=TAN, bevel=R, segments=6, name='trunk')
apply_all(trunk)

# framed, recessed panel on each end
for s in (-1, 1):
    c = frame_cutter(D - 0.13, H - 0.11, 0.035, 0.012, 'panel_cut')
    c.rotation_euler = (math.radians(90), 0, math.radians(90 * s)); c.location = (s * (L / 2 - 0.006), 0, Z0 + H / 2)
    kit.boolean(trunk, c)
bv = trunk.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0025; bv.segments = 2; bv.limit_method = 'ANGLE'
weighted_normals(trunk)

# corner caps: the trunk's own rounded shape grown 4 mm, kept within a ball round each corner
for sx in (-1, 1):
    for sy in (-1, 1):
        for sz in (0, 1):
            shell = kit.box((L + 0.007, D + 0.007, H + 0.007), at=(0, 0, Z0 + H / 2), bevel=R + 0.0035, segments=6, name='cap')
            apply_all(shell)
            ball = kit.sphere(0.072, at=(sx * L / 2, sy * D / 2, Z0 + sz * H), segs=32, rings=16, name='cap_ball')
            kit.boolean(shell, ball, op='INTERSECT')
            kit.finish(shell, DARK, smooth=35)
            # a brass rivet on the cap, on the end face
            kit.sphere(0.0065, at=(sx * (L / 2 + 0.005), sy * (D / 2 - 0.045), Z0 + (H - 0.045 if sz else 0.045)),
                       scale=(0.45, 1, 1), material=BRASS, segs=16, rings=8, name='rivet')

# piping along all twelve edges, down the middle of each rounded edge (ends tuck under the caps)
PR = 0.0032
m = R * (1 - 1 / math.sqrt(2)) - 0.0012  # how far the arc's midpoint sits in from the box corner
for sy in (-1, 1):
    for sz in (0, 1):
        z = Z0 + (H - m if sz else m)
        kit.cyl(PR, L - 0.1, at=(0, sy * (D / 2 - m), z), rot=(0, 90, 0), material=DARK, verts=12, name='piping')
for sx in (-1, 1):
    for sz in (0, 1):
        z = Z0 + (H - m if sz else m)
        kit.cyl(PR, D - 0.1, at=(sx * (L / 2 - m), 0, z), rot=(90, 0, 0), material=DARK, verts=12, name='piping')
    for sy in (-1, 1):
        kit.cyl(PR, H - 0.1, at=(sx * (L / 2 - m), sy * (D / 2 - m), Z0 + H / 2), material=DARK, verts=12, name='piping')

# two straps over the top and down the front
SX = 0.2
for s in (-1, 1):
    pts = ybox_section_path(D, H, R, 0.0026, Z0 + 0.03, Z0 + H / 2, Z0 + 0.045)
    path = resample([(s * SX, y, z) for y, z in pts], 120)
    prof = rounded_rect(0.0042, 0.044, 0.0012, n=2)
    sweep(path, prof, name='strap', material=DARK, up=(1, 0, 0))
    # strap tip on the front, slightly pointed: a small wedge of strap below the end
    tip = kit.extrude([(-0.022, 0), (0.022, 0), (0.022, -0.004), (0.0, -0.016), (-0.022, -0.004)], 0.0042, name='strap_tip')
    tip.rotation_euler = (math.radians(90), 0, 0); tip.location = (s * SX, -D / 2 - 0.0005, Z0 + 0.045)
    kit.finish(tip, DARK, bevel=0.0008)
    # buckle: brass frame with a centre bar and prong, high on the front
    bz = Z0 + H - 0.075
    ring_path = resample([(s * SX + u, -D / 2 - 0.0085, bz + v) for u, v in rounded_rect(0.058, 0.05, 0.012, n=5)], 64, closed=True)
    circ = [(0.0028 * math.cos(a), 0.0028 * math.sin(a)) for a in [i * math.tau / 10 for i in range(10)]]
    sweep(ring_path, circ, name='buckle', material=BRASS, closed=True, up=(0, 1, 0))
    kit.cyl(0.0026, 0.058, at=(s * SX, -D / 2 - 0.0085, bz), rot=(0, 90, 0), material=BRASS, verts=12, name='buckle_bar')
    sweep([(s * SX, -D / 2 - 0.0085, bz), (s * SX, -D / 2 - 0.0095, bz - 0.012), (s * SX, -D / 2 - 0.0075, bz - 0.022)],
          circ, name='prong', material=BRASS)
    # the strap's loose end comes back up through the buckle as a short tongue
    kit.box((0.044, 0.0042, 0.07), at=(s * SX, -D / 2 - 0.0067, bz - 0.005), material=DARK, bevel=0.0012, name='tongue')
    # keeper loop just under the buckle
    kit.box((0.05, 0.0068, 0.012), at=(s * SX, -D / 2 - 0.0055, bz - 0.052), material=DARK, bevel=0.0015, name='keeper')
    # punched holes down the strap
    for k in range(3):
        kit.cyl(0.0032, 0.002, at=(s * SX, -D / 2 - 0.0047, bz - 0.085 - k * 0.026), rot=(90, 0, 0), material=HOLE,
                verts=12, name='strap_hole')

# front grip between the straps: brass loops, leather handle hanging down a little
HZ = Z0 + H * 0.55
for s in (-1, 1):
    kit.box((0.034, 0.006, 0.03), at=(s * 0.085, -D / 2 - 0.002, HZ), material=BRASS, bevel=0.002, name='grip_plate')
    kit.torus(0.009, 0.0028, at=(s * 0.085, -D / 2 - 0.009, HZ - 0.004), rot=(0, 90, 0), material=BRASS,
              major=24, minor=8, name='grip_loop')
hp = []
for i in range(41):
    t = i / 40
    x = -0.079 + 0.158 * t
    hp.append((x, -D / 2 - 0.011 - 0.016 * math.sin(math.pi * t), HZ - 0.013 - 0.028 * math.sin(math.pi * t) ** 0.7))
for s in (-1, 1):  # leather ends folded round the loops
    kit.box((0.012, 0.009, 0.017), at=(s * 0.084, -D / 2 - 0.0095, HZ - 0.0125), material=DARK, bevel=0.003, segments=3, name='grip_end')
sweep(hp, rounded_rect(0.013, 0.026, 0.005, n=3), name='grip', material=DARK, up=(0, 0, 1))

# =====================================================================
# Top case
# =====================================================================
CL, CD, CH, CR = 0.49, 0.43, 0.205, 0.036
CX, CY = -0.055, 0.02
STUD = 0.007
CZ0 = Z0 + H + STUD
case = kit.box((CL, CD, CH), at=(CX, CY, CZ0 + CH / 2), material=TEAL, bevel=CR, segments=6, name='case')
apply_all(case)
SEAM = CZ0 + CH * 0.36
outer = kit.extrude(rounded_rect(CL + 0.02, CD + 0.02, CR, n=8), 0.0042, at=(CX, CY, SEAM - 0.0021), name='seam_out')
inner = kit.extrude(rounded_rect(CL - 0.007, CD - 0.007, CR - 0.0035, n=8), 0.01, at=(CX, CY, SEAM - 0.005), name='seam_in')
kit.boolean(outer, inner)
kit.boolean(case, outer)
bv = case.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0012; bv.segments = 2; bv.limit_method = 'ANGLE'
weighted_normals(case)
kit.extrude(rounded_rect(CL - 0.004, CD - 0.004, CR - 0.002, n=8), 0.0036, at=(CX, CY, SEAM - 0.0018), material=WELT, name='welt')

# studs it stands on (the straps run underneath)
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cyl(0.009, STUD + 0.002, at=(CX + sx * (CL / 2 - 0.036), CY + sy * (CD / 2 - 0.036), Z0 + H + STUD / 2),
                material=BRASS, verts=20, bevel=0.0015, name='stud')

# two stripes across the lid, front seam to back seam
for x in (CX - 0.12, CX - 0.085):
    pts = rounded_rect(CD + 2 * 0.0011, CH + 2 * 0.0011, CR + 0.0011, n=10, cy=CZ0 + CH / 2)
    k = 11
    top = pts[:2 * k]
    path = [(CD / 2 + 0.0011, SEAM + 0.006)] + top + [(-CD / 2 - 0.0011, SEAM + 0.006)]
    path = resample([(x, CY + y, z) for y, z in path], 90)
    sweep(path, rounded_rect(0.0012, 0.018, 0.0004, n=1), name='stripe', material=CREAM, up=(1, 0, 0))

# clasps on the front, straddling the seam
FY = CY - CD / 2
for s in (-1, 1):
    x = CX + s * 0.14
    kit.box((0.026, 0.005, 0.03), at=(x, FY - 0.0015, SEAM - 0.017), material=BRASS, bevel=0.0018, name='clasp_base')
    kit.box((0.022, 0.005, 0.022), at=(x, FY - 0.0015, SEAM + 0.017), material=BRASS, bevel=0.0018, name='clasp_keeper')
    kit.box((0.012, 0.006, 0.036), at=(x, FY - 0.004, SEAM - 0.002), material=BRASS, bevel=0.002, name='clasp_lever')
    kit.box((0.02, 0.006, 0.006), at=(x, FY - 0.004, SEAM + 0.014), material=BRASS, bevel=0.002, name='clasp_hook')
# centre lock with a D pull
kit.box((0.04, 0.005, 0.032), at=(CX, FY - 0.0015, SEAM - 0.016), material=BRASS, bevel=0.002, name='lock_plate')
kit.cyl(0.0035, 0.002, at=(CX, FY - 0.0042, SEAM - 0.02), rot=(90, 0, 0), material=HOLE, verts=12, name='keyhole')
dpath = [(CX + 0.014 * math.cos(math.pi - math.pi * i / 16), FY - 0.0075, SEAM - 0.004 - 0.02 * math.sin(math.pi * i / 16))
         for i in range(17)]

sweep(resample(dpath, 48, closed=True), [(0.0022 * math.cos(a), 0.0022 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]],
      name='d_pull', material=BRASS, closed=True, up=(0, 1, 0))
# hinges on the back
for s in (-1, 1):
    x = CX + s * 0.14
    kit.box((0.04, 0.004, 0.034), at=(x, CY + CD / 2 + 0.001, SEAM), material=BRASS, bevel=0.0012, name='hinge_leaf')
    kit.cyl(0.0035, 0.042, at=(x, CY + CD / 2 + 0.004, SEAM), rot=(0, 90, 0), material=BRASS, verts=12, name='hinge_pin')
# small brass name-tag holder on the left end
kit.box((0.004, 0.06, 0.034), at=(CX - CL / 2 - 0.0005, CY, SEAM + 0.035), material=BRASS, bevel=0.0015, name='tag_frame')
kit.box((0.004, 0.048, 0.024), at=(CX - CL / 2 - 0.0012, CY, SEAM + 0.035), material=CREAM, bevel=0.001, name='tag_card')

kit.export('suitcase')
