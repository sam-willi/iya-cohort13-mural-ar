"""Binoculars (Cara Austring): Porro-prism binoculars lying flat, as in her drawing. Each half has a
prism housing with the two-lobed end plates she drew, a dark band where the tapered objective
barrel starts, and an eyepiece with a rubber cup. The halves meet at a centre hinge with a knurled
focus wheel and a small cap at the front of the hinge.
Her "13" is restored: square-cut block numerals (a "1" with a long flag, a "3" of three equal bars on a stem,
extruded about one stroke deep) standing just beside the right-hand objective and turned toward the viewer. Her
drawing has it farther out in front; this keeps it readable and the binoculars large in the lens. The whole set is
turned so the app's front view is her three-quarter view, objectives pointing front-right."""
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
LEATHER = kit.mat('#3b2416', rough=0.88, name='leather')       # pebbled brown leather covering
ENAMEL = kit.mat('#1f1e1d', rough=0.32, metal=0.85, name='black_enamel')
CHROME = kit.mat('chrome', rough=0.22, metal=1.0, name='chrome')
RUBBER = kit.mat('rubber', rough=0.85, name='rubber')
LENS = kit.mat('#2c4652', rough=0.05, metal=0.6, name='coated_lens')
LENS_IN = kit.mat('#0e1213', rough=0.4, name='lens_shadow')

ZA = 0.0              # optical axes height (the whole thing is rested on the table at the end)
XE, XO = 0.034, 0.058  # eyepiece / objective axis offsets from the centre line
RE, RO = 0.0185, 0.0228

# along-axis stations (y; front of the binoculars is -Y)
Y_FRONT = -0.090      # objective rim
Y_BAND0, Y_BAND1 = -0.0215, -0.0135
Y_H0, Y_H1 = -0.0125, 0.049   # housing
Y_EYE1 = 0.066
Y_CUP1 = 0.078


def axis_lathe(profile, x, mat, name, steps=48):
    """profile [(r, s)] with s measured toward the FRONT (-Y) from y=0; revolved round a Y-parallel axis at x."""
    o = kit.lathe([(r, s) for r, s in profile], material=mat, steps=steps, name=name)
    o.rotation_euler = (math.radians(90), 0, 0)   # +Z -> -Y
    o.location = (x, 0, ZA)
    return o


def two_lobe(xe, re, xo, ro, grow=0.0, n=96, soften=5):
    """Outline (x, z) of the prism housing seen end-on: two circles joined, with the waist softened."""
    mx = (xe + xo) / 2
    rs = []
    for i in range(n):
        t = math.tau * i / n
        dx, dz = math.cos(t), math.sin(t)
        best = 0
        for cx, r in ((xe, re + grow), (xo, ro + grow)):
            ox = mx - cx
            b = ox * dx; c = ox * ox - r * r
            disc = b * b - c
            if disc >= 0:
                best = max(best, -b + math.sqrt(disc))
        rs.append(best)
    sm = []
    for i in range(n):
        acc = 0; w = 0
        for k in range(-soften, soften + 1):
            ww = 1 - abs(k) / (soften + 1); acc += rs[(i + k) % n] * ww; w += ww
        sm.append(acc / w)
    return [(mx + r * math.cos(math.tau * i / n), r * math.sin(math.tau * i / n)) for i, r in enumerate(sm)]


def y_extrude(outline_xz, y0, y1, mat, name, bevel=0.0):
    """Extrude an (x, z) outline along +Y from y0 to y1."""
    o = kit.extrude([(x, -z) for x, z in outline_xz], y1 - y0, name=name)
    o.rotation_euler = (math.radians(-90), 0, 0)  # local +Z -> +Y, local y -> z (flipped back by the -z above)
    o.location = (0, y0, ZA)
    return kit.finish(o, mat, bevel=bevel, segments=2, smooth=40)


for s in (-1, 1):
    xe, xo = s * XE, s * XO
    # prism housing: leather-covered body between two enamel end plates
    body = y_extrude(two_lobe(xe, RE, xo, RO, grow=-0.0004), Y_H0 + 0.003, Y_H1 - 0.003, LEATHER, 'housing')
    weighted_normals(body)
    for y0 in (Y_H0, Y_H1 - 0.0045):
        y_extrude(two_lobe(xe, RE, xo, RO, grow=0.0012), y0, y0 + 0.0045, ENAMEL, 'end_plate', bevel=0.0009)
    # objective barrel: dark band, leather-covered taper, chrome rim, recessed lens
    s0 = -Y_H0  # distance toward the front where the barrel starts
    axis_lathe([(0, s0), (RO - 0.0006, s0), (RO - 0.0006, s0 + 0.001)], xo, ENAMEL, 'barrel_root')
    axis_lathe([(0, -Y_BAND1), (RO + 0.0003, -Y_BAND1), (RO + 0.0008, -Y_BAND1 + 0.001), (RO + 0.0008, -Y_BAND0 - 0.001),
                (RO + 0.0003, -Y_BAND0), (0, -Y_BAND0)], xo, ENAMEL, 'band')
    rf = 0.0312
    axis_lathe([(0, -Y_BAND0), (RO - 0.0002, -Y_BAND0), (rf - 0.0012, -Y_FRONT - 0.007), (0, -Y_FRONT - 0.007)], xo, LEATHER, 'barrel')
    axis_lathe([(rf - 0.0016, -Y_FRONT - 0.0075), (rf - 0.0004, -Y_FRONT - 0.0075), (rf, -Y_FRONT - 0.006), (rf, -Y_FRONT - 0.001),
                (rf - 0.0008, -Y_FRONT), (rf - 0.0045, -Y_FRONT), (rf - 0.0052, -Y_FRONT - 0.0012),
                (rf - 0.0052, -Y_FRONT - 0.0055), (0.0, -Y_FRONT - 0.0055)], xo, CHROME, 'rim')
    axis_lathe([(0, -Y_FRONT - 0.0062), (rf - 0.0055, -Y_FRONT - 0.0062), (rf - 0.0055, -Y_FRONT - 0.0058), (0.0, -Y_FRONT - 0.0058)],
               xo, LENS_IN, 'lens_ring')
    axis_lathe([(0, -Y_FRONT - 0.0047), (0.0195, -Y_FRONT - 0.0052), (rf - 0.0055, -Y_FRONT - 0.0056), (rf - 0.0055, -Y_FRONT - 0.0059),
                (0, -Y_FRONT - 0.0059)], xo, LENS, 'objective_lens')
    # black retaining ring just inside the rim, so the lens sits in a shadowed seat
    axis_lathe([(rf - 0.0072, -Y_FRONT - 0.0046), (rf - 0.0053, -Y_FRONT - 0.0044), (rf - 0.0053, -Y_FRONT - 0.0056),
                (rf - 0.0072, -Y_FRONT - 0.0056)], xo, LENS_IN, 'lens_seat')
    # eyepiece: enamel tube, ribbed rubber cup, small recessed lens
    e0 = -Y_H1
    axis_lathe([(0, e0), (0.0155, e0), (0.0155, e0 - 0.006), (0.0145, e0 - 0.0065), (0.0145, -Y_EYE1), (0, -Y_EYE1)],
               xe, ENAMEL, 'eyepiece')
    for k in range(3):
        y = e0 - 0.0075 - k * 0.0028
        axis_lathe([(0.0145, y), (0.0153, y - 0.0005), (0.0153, y - 0.0012), (0.0145, y - 0.0017)], xe, ENAMEL, 'diopter_rib', steps=32)
    cup = []
    for i in range(13):
        a = math.pi * i / 12
        cup.append((0.0165 + 0.0032 * math.sin(a), -Y_EYE1 + 0.0004 - (Y_CUP1 - Y_EYE1) * (1 - math.cos(a)) / 2))
    axis_lathe([(0.0115, -Y_EYE1 + 0.0004)] + cup + [(0.0115, -Y_CUP1 + 0.0004), (0.0105, -Y_CUP1 + 0.003),
                                                    (0.0105, -Y_EYE1 + 0.0004)], xe, RUBBER, 'eyecup')
    axis_lathe([(0, -Y_CUP1 + 0.0035), (0.0105, -Y_CUP1 + 0.0035), (0.0105, -Y_CUP1 + 0.004), (0, -Y_CUP1 + 0.004)],
               xe, LENS_IN, 'eye_well')
    axis_lathe([(0, -Y_CUP1 + 0.0032), (0.0075, -Y_CUP1 + 0.0034), (0.0075, -Y_CUP1 + 0.0036), (0, -Y_CUP1 + 0.0036)],
               xe, LENS, 'eye_lens')
    # strap lug on the outer flank of the housing
    kit.torus(0.0042, 0.0012, at=(s * (XO + RO + 0.0028), Y_H1 - 0.012, ZA + 0.006), rot=(90, 0, 0),
              material=CHROME, major=20, minor=8, name='lug')
    kit.box((0.003, 0.006, 0.006), at=(s * (XO + RO - 0.0004), Y_H1 - 0.012, ZA + 0.006), material=ENAMEL, bevel=0.0008, name='lug_post')

# ---------- centre hinge ----------
HZ = ZA + 0.006
kit.cyl(0.0068, Y_H1 - Y_H0 + 0.004, at=(0, (Y_H0 + Y_H1) / 2, HZ), rot=(90, 0, 0), material=ENAMEL, bevel=0.0008, verts=32, name='hinge_barrel')
# bridges from each housing into the hinge, interleaved front/back like a real hinge


def bridge_shape(xi, r=0.0085, hh=0.0095):
    side = 1 if xi < 0 else -1          # the round end bulges away from its housing
    pts = [(side * r * math.cos(-math.pi / 2 + math.pi * i / 16), r * math.sin(-math.pi / 2 + math.pi * i / 16)) for i in range(17)]
    return pts + [(xi, hh), (xi, -hh)]


for s, (y0, y1) in ((-1, (Y_H0 + 0.004, Y_H0 + 0.013)), (1, (Y_H0 + 0.0145, Y_H0 + 0.0235)), (-1, (Y_H1 - 0.012, Y_H1 - 0.003))):
    o = kit.extrude([(x, -z) for x, z in bridge_shape(s * (XE - RE + 0.005))], y1 - y0, name='bridge')
    o.rotation_euler = (math.radians(-90), 0, 0); o.location = (0, y0, HZ)
    kit.finish(o, ENAMEL, bevel=0.0012, smooth=40)
# knurled focus wheel toward the eyepiece end
FW0, FW1 = Y_H0 + 0.029, Y_H0 + 0.045
prof = [(0, 0), (0.0108, 0), (0.0118, 0.001)]
prof += [(0.0118, 0.001), (0.0118, FW1 - FW0 - 0.001), (0.0108, FW1 - FW0), (0, FW1 - FW0)]
wheel = kit.lathe(prof, steps=72, name='focus_wheel')
for v in wheel.data.vertices:   # knurling: every other step of the rim pulled in, 36 ribs
    r = math.hypot(v.co.x, v.co.y)
    if r > 0.0115 and round(math.atan2(v.co.y, v.co.x) / (math.tau / 72)) % 2:
        v.co.x *= 0.0106 / r; v.co.y *= 0.0106 / r
wheel.rotation_euler = (math.radians(-90), 0, 0); wheel.location = (0, FW0, HZ)
kit.finish(wheel, ENAMEL, smooth=20)
# hinge caps: chrome at the front, the eyepiece bridge end at the back
kit.cyl(0.0074, 0.004, at=(0, Y_H0 - 0.002, HZ), rot=(90, 0, 0), material=CHROME, bevel=0.0012, verts=32, name='front_cap')
kit.cyl(0.0058, 0.008, at=(0, Y_H1 + 0.004, HZ), rot=(90, 0, 0), material=ENAMEL, bevel=0.001, verts=32, name='back_post')
kit.cyl(0.0062, 0.002, at=(0, Y_H1 + 0.0085, HZ), rot=(90, 0, 0), material=CHROME, bevel=0.0006, verts=32, name='back_cap')

# ---------- rest it on the table: objective rims at the front, eyecups at the back ----------
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    o.data.update()
verts = [v.co.copy() for o in bpy.context.scene.objects if o.type == 'MESH' for v in o.data.vertices]
vf = min((v for v in verts if v.y < Y_FRONT + 0.02), key=lambda v: v.z)
vb = min((v for v in verts if v.y > Y_H1 - 0.02), key=lambda v: v.z)
tilt = math.atan2(vf.z - vb.z, vb.y - vf.y)
M = Matrix.Rotation(tilt, 4, 'X')
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    o.data.transform(M)
zmin = min((v.co.z for o in bpy.context.scene.objects if o.type == 'MESH' for v in o.data.vertices))
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    o.data.transform(Matrix.Translation((0, 0, -zmin)))

# ---------- Cara's "13" ----------
# Measured off her isometric drawing: base centre ~0.136 m ahead of the objective rims, ~0.024 m in from the near
# (left, -X) barrel's axis toward the other; ~0.075 m tall with a stroke of 1/8 the height; strokes as deep as wide.
NUM = kit.mat('amber', rough=0.45, name='numerals')    # pencil outline in the drawing; a warm palette colour reads on the wall
H13 = 0.075; T13 = H13 / 8
one = [(2 * T13, 0), (3 * T13, 0), (3 * T13, H13), (1.6 * T13, H13), (0.9 * T13, H13 - 1.3 * T13), (2 * T13, H13 - 1.3 * T13)]  # short flag, so it can't read as a 7
W3 = 4.2 * T13; HM = H13 / 2
three = [(0, 0), (W3, 0), (W3, H13), (0, H13), (0, H13 - T13), (W3 - T13, H13 - T13), (W3 - T13, HM + T13 / 2),
         (0, HM + T13 / 2), (0, HM - T13 / 2), (W3 - T13, HM - T13 / 2), (W3 - T13, T13), (0, T13)]
W13 = 3 * T13 + 2 * T13 + W3

# ---------- turn the set so the front view is her three-quarter view, and centre it ----------
R = Matrix.Rotation(math.radians(45), 4, 'Z')
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in meshes:
    o.data.transform(R)

# Her "13" stands just beside the right-hand objective, turned toward the viewer, so it reads in the front
# three-quarter view and doesn't push the binoculars small in the lens.
front = min((v.co for o in meshes for v in o.data.vertices), key=lambda c: c.y)  # the front objective's rim
TURN = math.radians(-20)
x0, y0 = front.x + 0.02, front.y + 0.01
for poly, dx, nm in ((one, 0.0, 'num_1'), (three, 5 * T13, 'num_3')):
    o = kit.extrude(poly, T13, at=(0, 0, 0), rot=(90, 0, 0), material=NUM, bevel=0.0008, segments=2, name=nm)
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    o.data.transform(Matrix.Translation((x0 + (dx) * math.cos(TURN), y0 + dx * math.sin(TURN), 0)) @ Matrix.Rotation(TURN, 4, 'Z'))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
xs_ = [v.co.x for o in meshes for v in o.data.vertices]; ys_ = [v.co.y for o in meshes for v in o.data.vertices]
for o in meshes:
    o.data.transform(Matrix.Translation((-(min(xs_) + max(xs_)) / 2, -(min(ys_) + max(ys_)) / 2, 0)))
print('BBOX', round(max(xs_) - min(xs_), 4), round(max(ys_) - min(ys_), 4))

kit.export('binoculars')
