"""Television screen (Shayla Nguyen).

The drawing: a boxy retro TV on four splayed legs with a whole amusement park on its roof (vertical-loop
roller coaster, a tall lift hill, a Ferris wheel, a carousel, a station and a pond). The coaster track leaves
the roof, curves down the right side over graffiti ("C13 IYA", Audi rings, a melting popsicle "A"), runs
along the bottom of the front and climbs back up the left side. The screen shows two smiling faces: we put
Shayla's own pencil drawing of them on the screen, like a black-and-white broadcast.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, subprocess, tempfile
from mathutils import Vector, Matrix

kit.reset()
DRAWING = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'tv-screen-drawing.jpg')  # Shayla Nguyen's drawing
FONT_ROUND = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'


# ---------------- helpers ----------------
def link(o):
    bpy.context.collection.objects.link(o); return o


def mesh_obj(bm, name, material=None, smooth=40):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    return kit.finish(o, material, smooth=smooth)


def frames(P, ups):
    out = []
    n = len(P)
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        side = t.cross(ups[i]).normalized(); up = side.cross(t).normalized()
        out.append((t, side, up))
    return out


def sweep_frames(P, F, prof, offset=(0, 0), material=None, name='sweep', caps=True, smooth=60):
    bm = bmesh.new(); rings = []
    for p, (t, side, up) in zip(P, F):
        c = p + side * offset[0] + up * offset[1]
        rings.append([bm.verts.new(c + side * u + up * v) for u, v in prof])
    m = len(prof)
    for a, b in zip(rings, rings[1:]):
        for j in range(m):
            bm.faces.new((a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]))
    if caps:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(bm, name, material, smooth)


def circle(r, k=8):
    return [(r * math.cos(a), r * math.sin(a)) for a in (i * math.tau / k for i in range(k))]


def catmull(ctrl, per=10):
    """Uniform Catmull-Rom through control points [(Vector p, Vector up, tag)]; returns dense samples."""
    out = []
    n = len(ctrl)
    for i in range(n - 1):
        p0 = ctrl[max(i - 1, 0)][0]; p1 = ctrl[i][0]; p2 = ctrl[i + 1][0]; p3 = ctrl[min(i + 2, n - 1)][0]
        u1, u2 = ctrl[i][1], ctrl[i + 1][1]
        for k in range(per):
            t = k / per
            p = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                       (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
            up = (u1 * (1 - t) + u2 * t).normalized()
            out.append((p, up, ctrl[i][2]))
    out.append(ctrl[-1])
    return out


def resample(samples, step):
    """Even arc-length resampling of [(p, up, tag)]."""
    out = [samples[0]]; acc = 0.0
    for (a, ua, ta), (b, ub, tb) in zip(samples, samples[1:]):
        L = (b - a).length
        if L == 0:
            continue
        d = step - acc
        while d <= L:
            f = d / L
            out.append((a.lerp(b, f), ua.lerp(ub, f).normalized(), ta))
            d += step
        acc = L - (d - step)
    out.append(samples[-1])
    return out


def text3d(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, offset=0.0, bevel=0.0,
           res=2, spacing=1.0, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font:
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.offset = offset; cu.resolution_u = res
    cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.space_character = spacing
    o = link(bpy.data.objects.new(name, cu))
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def rod(a, b, r, material, verts=8, name='rod'):
    a, b = Vector(a), Vector(b); d = b - a
    o = kit.cyl(r, d.length, at=tuple((a + b) / 2), verts=verts, name=name)
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
    return kit.finish(o, material)


# ---------------- materials ----------------
oak = kit.mat('#6e4729', rough=0.42, name='veneer')
walnut = kit.mat('#3f2816', rough=0.55, name='walnut')
cream = kit.mat('cream', rough=0.45, name='cream_plastic')
bezel_m = kit.mat('#2a2622', rough=0.4, name='bezel')
brass = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
chrome = kit.mat('chrome', rough=0.22, metal=1.0, name='chrome')
grille = kit.mat('#1e1d1c', rough=0.7, name='grille')
rail_m = kit.mat('red', rough=0.35, metal=0.3, name='rail')
tie_m = kit.mat('#3c2a1c', rough=0.65, name='tie')
post_m = kit.mat('#efe3c8', rough=0.45, name='post')
water = kit.mat('#5aa6c2', rough=0.12, name='water')
water_edge = kit.mat('#c8b48a', rough=0.8, name='sand')
roof_r = kit.mat('red', rough=0.5, name='roof_red')
roof_c = kit.mat('cream', rough=0.5, name='roof_cream')
amber = kit.mat('amber', rough=0.4, name='amber')
teal = kit.mat('teal', rough=0.4, name='teal')
sky = kit.mat('sky', rough=0.45, name='sky')
orange = kit.mat('orange', rough=0.5, name='paint_orange')
paint_red = kit.mat('#c23a2c', rough=0.5, name='paint_red')
paint_outline = kit.mat('#1e1d1c', rough=0.55, name='paint_black')
paint_white = kit.mat('#f4ecd8', rough=0.5, name='paint_white')
skin = kit.mat('#d9a27a', rough=0.6, name='skin')
car_m = kit.mat('amber', rough=0.35, metal=0.2, name='car')
rubber = kit.mat('rubber', rough=0.8, name='rubber')

# ---------------- dimensions ----------------
W, D, H, LEG = 0.52, 0.50, 0.46, 0.14
Z0, T = LEG, LEG + H              # cabinet bottom / top
FY = -D / 2                       # front face plane

# ---------------- cabinet ----------------
cab = kit.box((W, D, H), at=(0, 0, Z0 + H / 2), material=oak, bevel=0.014, segments=3, name='cabinet')
# screen opening (rounded rectangle) cut into the front
SX0, SX1, SZ0, SZ1 = -0.232, 0.150, 0.190, 0.528
scx, scz, sw, sh = (SX0 + SX1) / 2, (SZ0 + SZ1) / 2, SX1 - SX0, SZ1 - SZ0
cut = kit.box((sw, 0.08, sh), at=(scx, FY, scz), bevel=0.045, segments=6, name='cut')
kit.boolean(cab, cut)
# control-panel recess on the right of the screen
cut2 = kit.box((0.072, 0.012, 0.34), at=(0.205, FY, scz), bevel=0.006, segments=2, name='cut2')
kit.boolean(cab, cut2)
# back panel recess
cut3 = kit.box((W - 0.08, 0.012, H - 0.08), at=(0, D / 2, Z0 + H / 2), bevel=0.004, segments=2, name='cut3')
kit.boolean(cab, cut3)
bpy.context.view_layer.objects.active = cab; bpy.ops.object.select_all(action='DESELECT'); cab.select_set(True)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))

# bezel: dark rounded frame proud of the front
bz = kit.box((sw + 0.036, 0.010, sh + 0.036), at=(scx, FY - 0.003, scz), bevel=0.012, segments=4, name='bezel')
bzc = kit.box((sw - 0.004, 0.05, sh - 0.004), at=(scx, FY - 0.003, scz), bevel=0.044, segments=6, name='bzc')
kit.boolean(bz, bzc)
kit.finish(bz, bezel_m)
bpy.context.view_layer.objects.active = bz; bpy.ops.object.select_all(action='DESELECT'); bz.select_set(True)
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))

# screen texture: Shayla's drawing of the two faces, un-skewed from the isometric face and toned like an
# old black-and-white broadcast
tex_path = None
if os.path.exists(DRAWING):
    tex_path = os.path.join(tempfile.mkdtemp(), 'tv_screen.png')
    script = r'''
import sys
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageChops
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('L')
TL, TR, BL = (184, 668), (571, 850), (170, 1018)     # screen corners in the drawing (inset from the outline)
Wt, Ht = 768, 668
a = (TR[0] - TL[0]) / Wt; b = (BL[0] - TL[0]) / Ht; c = TL[0]
d = (TR[1] - TL[1]) / Wt; e = (BL[1] - TL[1]) / Ht; f = TL[1]
im = im.transform((Wt, Ht), Image.AFFINE, (a, b, c, d, e, f), resample=Image.BICUBIC)
im = ImageOps.autocontrast(im, cutoff=(1, 4))
im = im.point(lambda v: int(40 + (v / 255) ** 1.3 * 200))
# vignette + faint scanlines
vig = Image.new('L', (Wt, Ht), 0); dr = ImageDraw.Draw(vig)
dr.rounded_rectangle((20, 20, Wt - 20, Ht - 20), radius=120, fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(70))
im = ImageChops.multiply(im, vig)
for y in range(0, Ht, 4):
    ImageDraw.Draw(im).line([(0, y), (Wt, y)], fill=None)
rgb = Image.merge('RGB', (im.point(lambda v: int(v * 0.93)), im.point(lambda v: int(v * 0.98)), im))
rgb = rgb.resize((512, 446), Image.LANCZOS)
rgb.save(out)
'''
    subprocess.run(['/usr/bin/env', 'python3', '-c', script, DRAWING, tex_path], check=True)

screen_m = kit.mat('#d8dde0', rough=0.18, name='screen', image=tex_path)
if tex_path:
    nt = screen_m.node_tree; bsdf = nt.nodes['Principled BSDF']
    timg = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
    nt.links.new(timg.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = 0.45

# the CRT: a gently bulged grid with planar UVs, sitting in the opening behind the bezel
bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
NX, NZ = 24, 20
gx0, gx1, gz0, gz1 = SX0 - 0.01, SX1 + 0.01, SZ0 - 0.01, SZ1 + 0.01
V = []
for j in range(NZ + 1):
    row = []
    for i in range(NX + 1):
        u, v = i / NX, j / NZ
        x = gx0 + (gx1 - gx0) * u; z = gz0 + (gz1 - gz0) * v
        bulge = 0.012 * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
        row.append(bm.verts.new((x, FY + 0.012 - bulge, z)))
    V.append(row)
for j in range(NZ):
    for i in range(NX):
        f = bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = ((co.x - SX0) / (SX1 - SX0), (co.z - SZ0) / (SZ1 - SZ0))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    if f.normal.y > 0:
        f.normal_flip()
scr = mesh_obj(bm, 'screen', screen_m, smooth=80)
# dark cavity behind the glass edges so nothing shows through the cut
kit.box((sw + 0.004, 0.004, sh + 0.004), at=(scx, FY + 0.026, scz), material=grille, name='cavity')

# control panel: brass plate, two knobs, two buttons, speaker slots
kit.box((0.066, 0.004, 0.33), at=(0.205, FY + 0.004, scz), material=kit.mat('#d9c9a3', rough=0.4, name='panel'),
        bevel=0.002, name='panel')
for zk in (0.47, 0.405):
    k = kit.cyl(0.019, 0.018, at=(0.205, FY - 0.006, zk), rot=(90, 0, 0), material=cream, bevel=0.003, verts=24,
                name='knob')
    kit.cyl(0.013, 0.006, at=(0.205, FY - 0.017, zk), rot=(90, 0, 0), material=brass, bevel=0.0015, verts=24,
            name='knobcap')
    kit.box((0.003, 0.004, 0.012), at=(0.205, FY - 0.021, zk + 0.004), material=bezel_m, name='pointer')
for zb in (0.355,):
    for xb in (0.19, 0.22):
        kit.cyl(0.0065, 0.008, at=(xb, FY - 0.002, zb), rot=(90, 0, 0), material=bezel_m, bevel=0.0015, verts=20,
                name='button')
for i in range(6):
    kit.box((0.048, 0.006, 0.0055), at=(0.205, FY + 0.001, 0.22 + i * 0.016), material=grille, bevel=0.0015,
            name='slot')

# back: vent slots and a cord
kit.box((W - 0.09, 0.004, H - 0.09), at=(0, D / 2 - 0.004, Z0 + H / 2), material=walnut, name='backpanel')
for i in range(9):
    kit.box((0.012, 0.006, 0.14), at=(-0.14 + i * 0.035, D / 2 - 0.0035, Z0 + H * 0.62), material=grille,
            bevel=0.004, segments=1, name='vent')
cpts = [Vector(p_) for p_ in [(0.12, D / 2 - 0.004, Z0 + 0.08), (0.12, D / 2 + 0.04, Z0 + 0.06),
                              (0.14, D / 2 + 0.07, 0.03), (0.10, D / 2 + 0.09, 0.005), (0.0, D / 2 + 0.07, 0.005),
                              (-0.06, D / 2 + 0.12, 0.005)]]
cd_ = catmull([(p_, Vector((0, 0, 1)), '') for p_ in cpts], per=8)
cp_ = [c[0] for c in resample(cd_, 0.012)]
sweep_frames(cp_, frames(cp_, [Vector((0.3, 0.2, 1)).normalized()] * len(cp_)), circle(0.005, 8), material=rubber,
             name='cord')
kit.box((0.026, 0.04, 0.016), at=(-0.075, D / 2 + 0.15, 0.008), rot=(0, 0, 30), material=rubber, bevel=0.004,
        name='plug')

# legs: tapered, splayed, with brass ferrules
for sx in (-1, 1):
    for sy in (-1, 1):
        top = Vector((sx * (W / 2 - 0.06), sy * (D / 2 - 0.06), Z0 + 0.004))
        foot = Vector((sx * (W / 2 - 0.035), sy * (D / 2 - 0.035), 0.0))
        d = top - foot
        leg = kit.cyl(0.0135, d.length, r2=0.022, verts=24, name='leg')
        leg.location = (foot + top) / 2
        leg.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        kit.finish(leg, walnut)
        fer = kit.cyl(0.0148, 0.022, at=tuple(foot + d.normalized() * 0.011), verts=24, name='ferrule')
        fer.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        kit.finish(fer, brass)

# ---------------- roof: the park ----------------
G = T + 0.0  # ground level on the roof
# pond (right-hand side, under the big drop)
pond_pts = [(0.095 + 0.07 * math.cos(a) + 0.05 * math.cos(a) ** 3 + 0.012 * math.sin(3 * a),
             0.03 + 0.12 * math.sin(a) + 0.015 * math.cos(2 * a)) for a in (i * math.tau / 40 for i in range(40))]
pond_pts = [(x + 0.06, y) for x, y in pond_pts]
kit.extrude([(x, y) for x, y in pond_pts], 0.004, at=(0, 0, G), material=water_edge, bevel=0.0015, name='shore')
inner = [(0.155 + (x - 0.155) * 0.9, 0.03 + (y - 0.03) * 0.9) for x, y in pond_pts]
kit.extrude(inner, 0.0052, at=(0, 0, G), material=water, name='pond')
# little wave crests
for (wx, wy) in ((0.13, -0.03), (0.18, 0.08), (0.12, 0.10), (0.20, -0.02), (0.15, 0.03), (0.17, 0.13)):
    wp = [Vector((wx - 0.014 + 0.028 * k / 8, wy + 0.003 * math.sin(k * 1.6), G + 0.0055)) for k in range(9)]
    sweep_frames(wp, frames(wp, [Vector((0, 0, 1))] * 9), [(0.0014, 0), (0, 0.0012), (-0.0014, 0), (0, -0.0008)],
                 material=paint_white, name='wave')

# ---------------- coaster track ----------------
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
E = 0.018      # side offset of track from faces
RH = 0.02      # rail height above roof
ctrl = []


def cp(x, y, z, up=Z, tag='top'):
    ctrl.append((Vector((x, y, z)), Vector(up).normalized(), tag))


# climb onto the roof at the front-left, then the vertical loop
cp(-W / 2 - E, -0.205, T - 0.03, -X, 'left')
cp(-W / 2 - E + 0.004, -0.203, T + 0.004, (-1, 0, 1.2), 'none')
cp(-W / 2 + 0.012, -0.200, G + RH, Z, 'top')
cp(-0.20, -0.195, G + RH)
cp(-0.16, -0.19, G + RH)
LX, LZ, LCX, LY0, LSH = 0.095, 0.155, -0.105, -0.19, 0.045
NL = 36
for i in range(NL + 1):
    ph = i / NL * math.tau
    p = Vector((LCX + LX * math.sin(ph), LY0 + LSH * (0.5 - 0.5 * math.cos(ph / 2)), G + RH + LZ * (1 - math.cos(ph))))
    cen = Vector((LCX, p.y, G + RH + LZ))
    up = (cen - p); up = up.normalized() if up.length > 1e-6 else Z
    if i in (0, NL):
        up = Z
    ctrl.append((p, up, 'loop'))
cp(-0.04, LY0 + LSH, G + RH)
cp(0.0, LY0 + LSH + 0.002, G + RH)
cp(0.035, -0.125, G + RH)
cp(0.05, -0.09, G + RH)
cp(0.055, -0.05, G + RH, Z, 'station')
cp(0.056, -0.015, G + RH + 0.01)
# lift hill
cp(0.058, 0.02, G + 0.09, Z, 'lift')
cp(0.060, 0.060, G + 0.24, Z, 'lift')
cp(0.062, 0.090, G + 0.36, Z, 'lift')
cp(0.068, 0.112, G + 0.415, Z, 'lift')
cp(0.085, 0.125, G + 0.435, Z, 'lift')
cp(0.108, 0.122, G + 0.425, (-0.3, 0, 1), 'lift')
cp(0.128, 0.110, G + 0.38, (-0.4, 0.1, 1), 'lift')
# the drop, into the pond
cp(0.150, 0.090, G + 0.26, (-0.6, 0.2, 1), 'lift')
cp(0.168, 0.070, G + 0.13, (-0.5, 0.2, 1), 'lift')
cp(0.182, 0.055, G + 0.05, Z, 'lift')
cp(0.196, 0.050, G + RH + 0.004)
cp(0.212, 0.062, G + RH + 0.004, (-0.3, 0, 1))
cp(0.222, 0.088, G + RH + 0.01, (-0.2, 0, 1))
# camel hump at the back right
cp(0.224, 0.120, G + 0.075)
cp(0.224, 0.150, G + 0.095)
cp(0.224, 0.178, G + 0.06)
cp(0.226, 0.198, G + RH + 0.006)
cp(0.238, 0.212, G + RH, (0, 0, 1))
cp(W / 2 - 0.004, 0.215, G + RH - 0.004, (1, 0, 1.2), 'none')
# over the edge and down the right side in one long curve
cp(W / 2 + E, 0.212, T - 0.04, X, 'right')
cp(W / 2 + E, 0.170, T - 0.10, X, 'right')
cp(W / 2 + E, 0.100, T - 0.16, X, 'right')
cp(W / 2 + E, 0.030, T - 0.23, X, 'right')
cp(W / 2 + E, -0.040, T - 0.30, X, 'right')
cp(W / 2 + E, -0.110, Z0 + 0.09, X, 'right')
cp(W / 2 + E, -0.175, Z0 + 0.04, X, 'right')
cp(W / 2 + E - 0.002, -0.225, Z0 + 0.008, (1, -0.3, 0.6), 'none')
# round the front-right corner and along the bottom of the front
cp(W / 2 - 0.005, -D / 2 - 0.02, Z0 - 0.012, (0.4, -0.3, 1), 'front')
cp(W / 2 - 0.05, -D / 2 - 0.035, Z0 - 0.018, Z, 'front')
cp(0.10, -D / 2 - 0.04, Z0 - 0.028, Z, 'front')
cp(-0.05, -D / 2 - 0.04, Z0 - 0.030, Z, 'front')
cp(-0.18, -D / 2 - 0.035, Z0 - 0.022, Z, 'front')
cp(-W / 2 + 0.02, -D / 2 - 0.022, Z0 - 0.010, (-0.4, -0.3, 1), 'front')
# round the front-left corner and up the left side
cp(-W / 2 - E + 0.002, -0.228, Z0 + 0.02, (-1, -0.3, 0.6), 'none')
cp(-W / 2 - E, -0.215, Z0 + 0.09, -X, 'left')
cp(-W / 2 - E, -0.208, Z0 + 0.22, -X, 'left')
cp(-W / 2 - E, -0.206, T - 0.10, -X, 'left')
cp(-W / 2 - E, -0.205, T - 0.03, -X, 'left')

dense = catmull(ctrl, per=8)
S = resample(dense, 0.004)
P = [s_[0] for s_ in S]; U = [s_[1] for s_ in S]; TAG = [s_[2] for s_ in S]
F = frames(P, U)
SR = resample(dense, 0.0085)
PR = [s_[0] for s_ in SR]; FR = frames(PR, [s_[1] for s_ in SR])

GA = 0.0075   # half gauge
rail_prof = circle(0.0021, 6)
sweep_frames(PR, FR, rail_prof, offset=(GA, 0.003), material=rail_m, name='rail')
sweep_frames(PR, FR, rail_prof, offset=(-GA, 0.003), material=rail_m, name='rail')

# ties: one mesh
bm = bmesh.new()
step = 3   # every 3rd sample = 12 mm
for i in range(0, len(P), step):
    t, side, up = F[i]; c = P[i]
    hx, hy, hz = 0.0115, 0.0022, 0.0018
    corners = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                corners.append(bm.verts.new(c + side * sx * hx + t * sy * hy + up * (sz * hz + 0.0002)))
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for q in idx:
        bm.faces.new([corners[k] for k in q])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
mesh_obj(bm, 'ties', tie_m, smooth=0)

# supports
acc = 0.0
for i in range(1, len(P)):
    acc += (P[i] - P[i - 1]).length
    if acc < 0.045:
        continue
    t, side, up = F[i]; p = P[i] - up * 0.006
    tag = TAG[i]
    if tag in ('top', 'station') and p.z > G + 0.012 and up.z > 0.8 and acc > 0.06:
        rod(p, (p.x, p.y, G), 0.0024, post_m, name='post'); acc = 0
        kit.cyl(0.005, 0.003, at=(p.x, p.y, G + 0.0015), material=post_m, verts=8, name='footing')
    elif tag == 'right':
        rod(p, (W / 2 - 0.001, p.y, p.z), 0.0022, post_m, name='bracket'); acc = 0
        kit.cyl(0.006, 0.003, at=(W / 2 + 0.001, p.y, p.z), rot=(0, 90, 0), material=post_m, verts=10, name='plate')
    elif tag == 'left':
        rod(p, (-W / 2 + 0.001, p.y, p.z), 0.0022, post_m, name='bracket'); acc = 0
        kit.cyl(0.006, 0.003, at=(-W / 2 - 0.001, p.y, p.z), rot=(0, 90, 0), material=post_m, verts=10, name='plate')
    elif tag == 'front' and acc > 0.09:
        rod(p, (p.x, p.y - 0.01, 0.0), 0.0026, post_m, name='leg'); acc = 0
        rod(p + side * 0.0, (p.x, p.y + 0.02, 0.0), 0.002, post_m, name='leg')
        kit.cyl(0.007, 0.003, at=(p.x, p.y - 0.01, 0.0015), material=post_m, verts=12, name='foot')
# the lift hill's A-frame: crossbars between the climbing and the falling leg (as drawn), plus two feet
LI = [i for i, tg in enumerate(TAG) if tg == 'lift']
crest = max(LI, key=lambda i: P[i].z)
rise = [i for i in LI if i < crest]; fall = [i for i in LI if i > crest]
for h in (0.10, 0.20, 0.30):
    a_ = min(rise, key=lambda i: abs(P[i].z - (G + h))); b_ = min(fall, key=lambda i: abs(P[i].z - (G + h)))
    rod(P[a_] - F[a_][2] * 0.005, P[b_] - F[b_][2] * 0.005, 0.0022, post_m, name='crossbar')
for i in (min(rise, key=lambda i: abs(P[i].z - (G + 0.10))), min(fall, key=lambda i: abs(P[i].z - (G + 0.10)))):
    q = P[i] - F[i][2] * 0.005
    rod(q, (q.x, q.y, G), 0.0026, post_m, name='post')
    kit.cyl(0.005, 0.003, at=(q.x, q.y, G + 0.0015), material=post_m, verts=8, name='footing')
# the loop's side legs
for sgn in (-1, 1):
    px = LCX + sgn * (LX + 0.006)
    for dy in (0.0, LSH):
        rod((px, LY0 + dy * (0.25 if sgn > 0 else 0.75), G + RH + LZ), (px + sgn * 0.02, LY0 + dy * 0.5, G), 0.0026,
            post_m, name='loopleg')

# cars with riders: (sample index fraction, count)
def train(i0, n=3):
    for k in range(n):
        i = max(0, min(len(P) - 1, i0 - k * 8))
        t, side, up = F[i]; c = P[i] + up * 0.011
        m = Matrix((side, t, up)).transposed().to_4x4(); m.translation = c
        car = kit.box((0.022, 0.028, 0.012), material=car_m, bevel=0.004, segments=2, name='car')
        car.matrix_world = m
        for s in (-1, 1):
            hd = kit.sphere(0.0042, segs=8, rings=5, material=skin, name='head')
            hd.location = c + up * 0.012 + side * s * 0.005
            for a in (-1, 1):
                rod(c + up * 0.008 + side * (s * 0.005 + a * 0.003), c + up * 0.026 + side * (s * 0.005 + a * 0.008),
                    0.0012, skin, verts=6, name='arm')


tot = len(P)
iloop = [i for i, tg in enumerate(TAG) if tg == 'loop']
train(iloop[len(iloop) // 2] + 6)
ilift = [i for i, tg in enumerate(TAG) if tg == 'lift']
train(ilift[0] + int(len(ilift) * 0.42))
iright = [i for i, tg in enumerate(TAG) if tg == 'right']
train(iright[len(iright) // 2])

# ---------------- Ferris wheel (back left) ----------------
FWX, FWY, FWZ, FWR = -0.125, 0.12, G + 0.118, 0.092
for dy in (-0.012, 0.012):
    kit.torus(FWR, 0.0028, at=(FWX, FWY + dy, FWZ), rot=(90, 0, 0), material=post_m, major=48, minor=6, name='rim')
    for k in range(12):
        a = k * math.tau / 12
        rod((FWX, FWY + dy, FWZ), (FWX + FWR * math.cos(a), FWY + dy, FWZ + FWR * math.sin(a)), 0.0012, post_m,
            verts=5, name='spoke')
kit.cyl(0.010, 0.04, at=(FWX, FWY, FWZ), rot=(90, 0, 0), material=chrome, verts=16, name='hub')
for dy in (-0.022, 0.022):
    for sx in (-1, 1):
        rod((FWX, FWY + dy, FWZ), (FWX + sx * 0.06, FWY + dy * 1.6, G), 0.0035, kit.mat('steel', 0.35, 0.8, 'steel'),
            name='aleg')
gond = [roof_r, amber, teal, sky]
for k in range(8):
    a = k * math.tau / 8 + 0.2
    px, pz = FWX + FWR * math.cos(a), FWZ + FWR * math.sin(a)
    rod((px, FWY - 0.014, pz), (px, FWY + 0.014, pz), 0.0016, chrome, verts=6, name='axle')
    kit.box((0.018, 0.016, 0.014), at=(px, FWY, pz - 0.012), material=gond[k % 4], bevel=0.004, segments=1,
            name='gondola')
    kit.box((0.02, 0.018, 0.003), at=(px, FWY, pz - 0.0035), material=gond[k % 4], name='gtop')

# ---------------- carousel (front right) ----------------
CX, CY = 0.175, -0.15
kit.cyl(0.058, 0.010, at=(CX, CY, G + 0.005), material=kit.mat('honey', 0.45, 0, 'honey'), bevel=0.002, verts=40,
        name='platform')
kit.cyl(0.010, 0.10, at=(CX, CY, G + 0.06), material=brass, verts=16, name='centrepole')
for k in range(8):
    a = k * math.tau / 8
    px, py = CX + 0.045 * math.cos(a), CY + 0.045 * math.sin(a)
    rod((px, py, G + 0.01), (px, py, G + 0.093), 0.0016, brass, verts=6, name='pole')
    hz = G + 0.035 + 0.008 * math.sin(k * 1.7)
    horse = kit.box((0.006, 0.020, 0.011), at=(px, py, hz), rot=(0, 0, math.degrees(a)),
                    material=paint_white if k % 2 else amber, bevel=0.003, segments=1, name='horse')
    hd = kit.box((0.005, 0.007, 0.012), at=(px + 0.009 * -math.sin(a), py + 0.009 * math.cos(a), hz + 0.008),
                 rot=(0, 0, math.degrees(a)), material=horse.data.materials[0], bevel=0.002, segments=1,
                 name='horsehead')
# striped conical roof (alternating segments) + valance
for k in range(16):
    a0 = k * math.tau / 16; a1 = (k + 1) * math.tau / 16
    bm = bmesh.new()
    apex = bm.verts.new((CX, CY, G + 0.135))
    ring = [bm.verts.new((CX + 0.064 * math.cos(a0 + (a1 - a0) * s / 3), CY + 0.064 * math.sin(a0 + (a1 - a0) * s / 3),
                          G + 0.095)) for s in range(4)]
    for s in range(3):
        bm.faces.new((apex, ring[s], ring[s + 1]))
    under = [bm.verts.new((v.co.x, v.co.y, v.co.z - 0.0025)) for v in ring]
    for s in range(3):
        bm.faces.new((ring[s + 1], ring[s], under[s], under[s + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_obj(bm, 'roof', roof_r if k % 2 else roof_c, smooth=0)
for k in range(16):
    a = (k + 0.5) * math.tau / 16
    kit.sphere(0.0055, at=(CX + 0.062 * math.cos(a), CY + 0.062 * math.sin(a), G + 0.091), scale=(1, 1, 0.8),
               material=roof_c if k % 2 else roof_r, segs=8, rings=5, name='scallop')
kit.sphere(0.006, at=(CX, CY, G + 0.139), material=brass, segs=12, rings=8, name='finial')
rod((CX, CY, G + 0.139), (CX, CY, G + 0.158), 0.001, brass, name='flagpole')
kit.box((0.012, 0.001, 0.007), at=(CX + 0.006, CY, G + 0.154), material=roof_r, name='flag')

# ---------------- station (front middle, straddles the track) ----------------
STX, STY = 0.055, -0.055
for dx in (-0.020, 0.020):
    kit.box((0.010, 0.07, 0.042), at=(STX + dx, STY, G + 0.021), material=cream, bevel=0.0015, name='stwall')
    for wy in (-0.02, 0.0, 0.02):
        kit.box((0.0012, 0.010, 0.016), at=(STX + dx + (0.0052 if dx > 0 else -0.0052), STY + wy, G + 0.026),
                material=tie_m, name='window')
for k, (yy, mtl) in enumerate(((-0.018, roof_r), (0.018, roof_r))):
    for s in (-1, 1):
        kit.box((0.034, 0.038, 0.003), at=(STX + s * 0.0125, STY + yy, G + 0.052), rot=(0, s * -32, 0),
                material=mtl, bevel=0.001, name='gable')
    tri = kit.extrude([(-0.025, 0), (0.025, 0), (0, 0.016)], 0.003, at=(STX, STY + yy - 0.017, G + 0.042),
                      rot=(90, 0, 0), material=cream, name='gable_end')

# ---------------- graffiti on the right side (+X face) ----------------
GX = W / 2 + 0.0004


def face_text(s_, size, y, z, mat_fill, mat_line, tilt=0.0, offset=0.005, font=FONT_ROUND, spacing=0.92):
    o1 = text3d(s_, size, 0.0012, font=font, at=(GX + 0.0006, y, z), rot=(90, -tilt, 90), material=mat_line,
                offset=offset, res=2, spacing=spacing, name='tag_line')
    o2 = text3d(s_, size, 0.0016, font=font, at=(GX + 0.0016, y, z), rot=(90, -tilt, 90), material=mat_fill,
                offset=0.0, bevel=0.0012, res=2, spacing=spacing, name='tag_fill')
    return o1, o2


face_text('C13', 0.115, -0.125, Z0 + 0.085, paint_red, paint_outline, tilt=8)
face_text('IYA', 0.14, 0.105, Z0 + 0.175, orange, paint_outline, tilt=10)
# Audi-style rings, top back
for k in range(4):
    kit.torus(0.021, 0.0032, at=(GX + 0.001, 0.055 + k * 0.03, T - 0.06), rot=(0, 90, 0), material=chrome,
              major=24, minor=5, name='ring').scale = (0.35, 1, 1)
# melting popsicle "A", top front
kit.box((0.003, 0.05, 0.065), at=(GX + 0.0015, -0.15, T - 0.10), material=sky, bevel=0.0012, name='pop')
for dz, dyy in ((0.04, -0.012), (0.03, 0.008), (0.05, 0.018)):
    kit.box((0.0025, 0.007, dz), at=(GX + 0.0015, -0.15 + dyy, T - 0.13 - dz / 2), material=sky, bevel=0.0012,
            name='drip')
kit.box((0.003, 0.007, 0.03), at=(GX + 0.0015, -0.15, T - 0.145), material=kit.mat('#c8a06a', 0.6, 0, 'stick'),
        name='stick')
text3d('A', 0.035, 0.0012, font=FONT_ROUND, at=(GX + 0.0034, -0.15, T - 0.10), rot=(90, 0, 90),
       material=paint_white, name='popA')
# three dripping slashes, middle back
for k in range(3):
    kit.box((0.003, 0.012, 0.04), at=(GX + 0.0015, 0.05 + k * 0.022, T - 0.15 - k * 0.006), rot=(-25, 0, 0),
            material=paint_red, bevel=0.0012, name='slash')

kit.export('tv-screen')
