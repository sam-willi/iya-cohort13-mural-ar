"""Trumpet (Shin Masada).

The drawing: a trumpet with its bell up and to the right, a straight lead pipe from the mouthpiece into three
tall valves with finger buttons, a long oval slide loop wrapped round the valves, a "COHORT 13" banner hanging
from the valve casings, and ribbons streaming out of the bell reading "IOVINE", "AND", "YOUNG", "ACADEMY".
Line-only, so: lacquered brass, pearl buttons, a silver mouthpiece; cardinal banner with gold lettering and
gold ribbons with cardinal lettering (USC colours, which sit inside the mural's palette).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, subprocess, tempfile
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def link(o):
    bpy.context.collection.objects.link(o); return o


def catmull(pts, per=8):
    P = [Vector(p) for p in pts]; n = len(P); out = []
    for i in range(n - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


def pipe(pts, r, material, k=16, closed=False, per=8, name='pipe', smooth=True, radii=None):
    """Round tube through points (Catmull-Rom smoothed). radii: optional per-control-point radius."""
    P = catmull(pts, per) if smooth else [Vector(p) for p in pts]
    if radii:
        R = []
        for i in range(len(radii) - 1):
            for s in range(per):
                R.append(radii[i] + (radii[i + 1] - radii[i]) * s / per)
        R.append(radii[-1])
    else:
        R = [r] * len(P)
    bm = bmesh.new(); rings = []
    n = len(P)
    ref = Vector((0, 0, 1))
    N = None
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        if N is None:
            N = t.cross(Vector((0, 1, 0)) if abs(t.y) < 0.9 else Vector((1, 0, 0))).normalized()
        else:
            N = (N - t * N.dot(t)).normalized()
        B = t.cross(N)
        rings.append([bm.verts.new(P[i] + (N * math.cos(a) + B * math.sin(a)) * R[i])
                      for a in (j * math.tau / k for j in range(k))])
    for a, b in zip(rings, rings[1:]):
        for j in range(k):
            bm.faces.new((a[j], a[(j + 1) % k], b[(j + 1) % k], b[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    return kit.finish(o, material, smooth=60)


def text3d(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, res=3, spacing=1.0, name='t'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res; cu.space_character = spacing
    o = link(bpy.data.objects.new(name, cu))
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


# ---------- materials ----------
brass = kit.mat('#c99a45', rough=0.22, metal=0.95, name='lacquered_brass')
brass_dk = kit.mat('#a8792f', rough=0.3, metal=0.9, name='brass_dark')
silver = kit.mat('chrome', rough=0.18, metal=1.0, name='silver')
pearl = kit.mat('#f4ecd8', rough=0.18, name='pearl')
cardinal = kit.mat('cardinal', rough=0.75, name='banner_cardinal')
gold_thread = kit.mat('#e0b04a', rough=0.45, metal=0.5, name='gold_thread')

# ---------- layout (x = along the horn, mouthpiece at -x, bell at +x; valves point up +z) ----------
ZA = 0.30                     # height of the lead-pipe axis (banner hangs below)
VX = [-0.028, -0.004, 0.020]  # valve centres
VR = 0.0098                   # casing radius
VZ0, VZ1 = ZA - 0.075, ZA + 0.04
TR = 0.0065                   # tubing radius
LY = 0.024                    # the slide loop sits just behind the valves

# valves: casings with ferrules, top caps, stems and pearl finger buttons; bottom caps
for x in VX:
    kit.cyl(VR, VZ1 - VZ0, at=(x, 0, (VZ0 + VZ1) / 2), material=brass, verts=32, name='casing')
    for z in (VZ0 + 0.006, VZ1 - 0.006, ZA - 0.022):
        kit.cyl(VR + 0.0012, 0.006, at=(x, 0, z), material=brass_dk, bevel=0.001, verts=32, name='ferrule')
    kit.cyl(VR + 0.0008, 0.008, at=(x, 0, VZ1 + 0.003), material=brass_dk, bevel=0.0015, verts=32, name='topcap')
    kit.cyl(0.0022, 0.022, at=(x, 0, VZ1 + 0.018), material=silver, verts=12, name='stem')
    kit.cyl(0.0085, 0.006, at=(x, 0, VZ1 + 0.031), material=brass_dk, bevel=0.0015, verts=28, name='buttoncup')
    kit.cyl(0.0078, 0.004, at=(x, 0, VZ1 + 0.0355), material=pearl, bevel=0.0015, verts=28, name='button')
    kit.cyl(VR + 0.0006, 0.008, at=(x, 0, VZ0 - 0.003), material=brass_dk, bevel=0.0015, verts=32, name='bottomcap')
# valve block braces between the casings
for a, b in zip(VX, VX[1:]):
    for z in (ZA + 0.022, ZA - 0.045):
        kit.box((b - a, 0.004, 0.006), at=((a + b) / 2, 0, z), material=brass, bevel=0.001, name='brace')

# lead pipe: mouthpiece receiver -> first valve (slight taper)
MP_X = -0.235
pipe([(MP_X + 0.03, 0, ZA), (-0.12, 0, ZA), (VX[0] - VR + 0.002, 0, ZA)], TR, brass, per=2, name='leadpipe',
     radii=[0.0048, 0.0053, TR])
kit.cyl(0.0075, 0.03, at=(MP_X + 0.03 + 0.015, 0, ZA), rot=(0, 90, 0), material=brass_dk, bevel=0.0015, verts=24,
        name='receiver')
# mouthpiece: lathe (cup, rim, shank), axis along x
mp = kit.lathe([(0.0, 0.0), (0.0035, 0.0), (0.004, 0.03), (0.006, 0.06), (0.0085, 0.075), (0.0125, 0.083),
                (0.0135, 0.087), (0.0125, 0.09), (0.0085, 0.089), (0.0, 0.082)], material=silver, steps=32,
               name='mouthpiece')
mp.rotation_euler = (0, math.radians(-90), 0); mp.location = (MP_X + 0.045, 0, ZA)
# finger hook on the lead pipe
pipe([(-0.06, 0, ZA + TR), (-0.06, 0, ZA + 0.018), (-0.048, 0, ZA + 0.022), (-0.04, 0, ZA + 0.016)], 0.0018, brass,
     per=6, name='fingerhook')

# bell pipe: third valve -> bell, then the flare
BX0, BX1 = VX[2] + VR, 0.235
pipe([(BX0 - 0.002, 0, ZA), (0.06, 0, ZA + 0.002), (0.095, 0, ZA + 0.004)], TR, brass, per=4, name='bellpipe',
     radii=[TR, TR * 1.05, TR * 1.25])
prof = []
N = 30
for i in range(N + 1):
    t = i / N
    x = 0.095 + (BX1 - 0.095) * t
    r = 0.0073 + 0.0555 * (t ** 3.2)          # exponential-ish flare
    prof.append((r, x))
outer = [(r + 0.0012, x) for r, x in prof]
inner = [(r, x) for r, x in reversed(prof)]
rimroll = [(prof[-1][0] + 0.0035, BX1 - 0.0005), (prof[-1][0] + 0.0028, BX1 + 0.0025), (prof[-1][0] + 0.0006, BX1 + 0.0022)]
bell = kit.lathe(outer + rimroll + inner, material=brass, steps=72, name='bell')
bell.rotation_euler = (0, math.radians(90), 0); bell.location = (0, 0, ZA)
for v in bell.data.vertices:          # lathe ran along z; after rotation z -> x already handled by rotation
    pass
kit.torus(prof[-1][0] + 0.0022, 0.0028, at=(BX1 + 0.001, 0, ZA), rot=(0, 90, 0), material=brass_dk, major=72,
          minor=10, name='bellrim')
kit.cyl(0.0105, 0.012, at=(0.098, 0, ZA + 0.004), rot=(0, 90, 0), material=brass_dk, bevel=0.0015, verts=24,
        name='bellferrule')
# bell brace to the slide loop
pipe([(0.07, 0, ZA + 0.003), (0.07, LY * 0.5, ZA + 0.001), (0.07, LY, ZA)], 0.0025, brass, per=3, name='bellbrace')

# the long slide loop round the valves (as drawn): top run behind everything, bows at both ends,
# bottom runs into the bottoms of the first and third valves
LZT, LZB = ZA - 0.0, ZA - 0.072
XB, XF = -0.15, 0.125
rb = (LZT - LZB) / 2
loop_pts = [(VX[2], 0.0, VZ0 - 0.005), (VX[2] + 0.004, LY * 0.5, LZB + 0.004), (VX[2] + 0.03, LY, LZB),
            (XF - rb, LY, LZB)]
for i in range(1, 8):
    a = -math.pi / 2 + math.pi * i / 8
    loop_pts.append((XF - rb + rb * math.cos(a), LY, (LZT + LZB) / 2 + rb * math.sin(a)))
loop_pts += [(XF - rb, LY, LZT), (XB + rb, LY, LZT)]
for i in range(1, 8):
    a = math.pi / 2 + math.pi * i / 8
    loop_pts.append((XB + rb + rb * math.cos(a), LY, (LZT + LZB) / 2 + rb * math.sin(a)))
loop_pts += [(XB + rb, LY, LZB), (VX[0] - 0.03, LY, LZB), (VX[0] - 0.004, LY * 0.5, LZB + 0.004),
             (VX[0], 0.0, VZ0 - 0.005)]
pipe(loop_pts, TR, brass, per=5, name='slideloop')
# slide ferrules and a water key on the front bow
for x in (XF - rb - 0.02, XB + rb + 0.02):
    for z in (LZT, LZB):
        kit.cyl(TR + 0.0012, 0.008, at=(x, LY, z), rot=(0, 90, 0), material=brass_dk, bevel=0.001, verts=20,
                name='slideferrule')
kit.box((0.012, 0.004, 0.004), at=(XF + 0.001, LY, (LZT + LZB) / 2 - 0.012), rot=(0, 30, 0), material=brass_dk,
        bevel=0.001, name='waterkey')
# braces: lead pipe to the loop top run
for x in (-0.11, -0.07):
    pipe([(x, 0.0, ZA), (x, LY, LZT)], 0.002, brass, per=1, name='brace', smooth=False)

# ---------- the "COHORT 13" banner hanging from the valve casings ----------
tdir = tempfile.mkdtemp()
subprocess.run(['/usr/bin/env', 'python3', '-c', r"""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageOps
F = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def font(n):
    try: return ImageFont.truetype(F, n)
    except Exception: return ImageFont.load_default()
out = sys.argv[1]
# banner: cardinal cloth, gold border and lettering
W, H = 512, 640
for name, mirror in (('banner_f.png', False), ('banner_b.png', True)):
    t = Image.new('L', (W, H), 0); d = ImageDraw.Draw(t)
    d.text((W // 2, 250), 'COHORT', font=font(100), fill=255, anchor='mm')
    d.text((W // 2, 400), '13', font=font(150), fill=255, anchor='mm')
    if mirror: t = ImageOps.mirror(t)
    im = Image.new('RGB', (W, H), (153, 32, 28))
    im.paste((224, 176, 74), (0, 0, W, H), t)
    ImageDraw.Draw(im).rectangle((18, 18, W - 18, H - 18), outline=(224, 176, 74), width=10)
    im.save(os.path.join(out, name))
# ribbons: gold silk, cardinal lettering
for word in ('IOVINE', 'AND', 'YOUNG', 'ACADEMY'):
    W, H = 1024, 76
    for suf, mirror in (('f', False), ('b', True)):
        t = Image.new('L', (W, H), 0)
        d = ImageDraw.Draw(t); f = font(64); step = min(120, 700 // len(word))
        x0 = W * 0.58 - step * (len(word) - 1) / 2
        for k, ch in enumerate(word):
            d.text((x0 + k * step, H // 2 + 3), ch, font=f, fill=255, anchor='mm')
        if mirror: t = ImageOps.mirror(t)
        im = Image.new('RGB', (W, H), (214, 158, 56))
        im.paste((153, 32, 28), (0, 0, W, H), t)
        im.save(os.path.join(out, f'rib_{word}_{suf}.png'))
""", tdir], check=True)


def cloth(grid_fn, NU, NV, tex_f, tex_b, name, thick=0.0007):
    """A two-sided cloth surface. grid_fn(u, v) -> (point, normal-ish). Front face gets tex_f, back gets tex_b."""
    objs = []
    for face, tex in ((1, tex_f), (-1, tex_b)):
        m = kit.mat('#ffffff', rough=0.7, name=os.path.basename(tex)[:-4], image=tex)
        m.use_backface_culling = True
        bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); G = []
        for i in range(NU + 1):
            col = []
            for j in range(NV + 1):
                p, n = grid_fn(i / NU, j / NV)
                col.append(bm.verts.new(p + n * thick * face))
            G.append(col)
        for i in range(NU):
            for j in range(NV):
                ids = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                if face < 0:
                    ids = ids[::-1]
                f = bm.faces.new([G[a][b] for a, b in ids])
                for l, (a, b) in zip(f.loops, ids):
                    l[uvl].uv = (a / NU, b / NV)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = link(bpy.data.objects.new(name, me))
        kit.finish(o, m, smooth=80)
        objs.append(o)
    return objs


# banner: top hem at the casings' lower ferrules, hanging down with a wavy hem
BW_, BH_ = 0.105, 0.16
BX = (VX[0] + VX[2]) / 2
BTOP = VZ0 + 0.018
BYF = -VR - 0.0035


def banner_pt(u, v):
    x = BX - BW_ / 2 + BW_ * u
    bottom_wave = 0.012 * math.sin(u * math.tau * 1.0 + 0.5)
    z = BTOP - (BH_ + bottom_wave) * (1 - v)
    y = BYF - 0.006 * math.sin(u * math.pi) * (1 - v) - 0.004 * math.sin(u * 7 + 1) * (1 - v) ** 2
    return Vector((x, y, z)), Vector((0, -1, 0))


# front face is the one that faces -y; build so u runs +x and v runs bottom->top
cloth(banner_pt, 16, 10,
      os.path.join(tdir, 'banner_f.png'), os.path.join(tdir, 'banner_b.png'), 'banner')
# hem sleeve the banner hangs from, wrapped round the casings
kit.box((BW_ + 0.004, 2 * VR + 0.01, 0.012), at=(BX, 0, BTOP - 0.002), material=cardinal, bevel=0.004, segments=2,
        name='hem')
kit.box((BW_ + 0.006, 2 * VR + 0.012, 0.003), at=(BX, 0, BTOP - 0.009), material=gold_thread, bevel=0.001,
        name='hemcord')
for sx in (-1, 1):
    kit.sphere(0.0045, at=(BX + sx * (BW_ / 2 + 0.004), 0, BTOP - 0.009), material=gold_thread, segs=12, rings=8,
               name='tassel_knot')
    kit.cyl(0.0035, 0.022, r2=0.0016, at=(BX + sx * (BW_ / 2 + 0.004), 0, BTOP - 0.022), rot=(180, 0, 0),
            material=gold_thread, verts=12, name='tassel')

# ---------- ribbons streaming out of the bell ----------
specs = [  # word, start angle on the bell mouth, direction (dy, dz) spread, length, twist phase
    ('IOVINE', 70, (0.10, 0.62), 0.33, 0.0),
    ('AND', 25, (0.02, 0.38), 0.25, 1.3),
    ('YOUNG', -20, (-0.04, 0.22), 0.32, 2.1),
    ('ACADEMY', -70, (-0.06, -0.10), 0.34, 3.0),
]
RW = 0.03
BELL_R = prof[-1][0]
for word, ang, (dy, dz), L, ph in specs:
    a = math.radians(ang)
    start = Vector((BX1 - 0.028, -BELL_R * 0.18 * math.cos(a), ZA + BELL_R * 0.5 * math.sin(a)))
    dirv = Vector((1.0, dy, dz)).normalized()

    def rib_pt(u, v, start=start, dirv=dirv, L=L, ph=ph):
        side = Vector((0, 0, 1)) - dirv * dirv.z; side.normalize()
        nrm = dirv.cross(side).normalized()
        c = start + dirv * (L * u)
        c += nrm * (0.022 * math.sin(u * 7.0 + ph) * u) + side * (0.03 * math.sin(u * 3.5 + ph) * u)
        tw = 0.5 * math.sin(u * 4.0 + ph) * u
        sd = side * math.cos(tw) + nrm * math.sin(tw)
        nn = nrm * math.cos(tw) - side * math.sin(tw)
        w = RW * (1 - 0.1 * u)
        if u >= 1.0 and abs(v - 0.5) < 1e-6:      # swallow-tail notch at the free end
            c = c - dirv * 0.02
        return c + sd * (w * (v - 0.5)), nn

    objs = cloth(rib_pt, 40, 2, os.path.join(tdir, f'rib_{word}_f.png'), os.path.join(tdir, f'rib_{word}_b.png'),
                 'ribbon_' + word)

# it is a held object: drop it so its lowest point sits on z=0
dg = bpy.context.evaluated_depsgraph_get()
lo = min((o.matrix_world @ Vector(c)).z for o in bpy.context.scene.objects if o.type == 'MESH'
         for c in o.evaluated_get(dg).bound_box)
for o in bpy.context.scene.objects:
    o.location.z -= lo

kit.export('trumpet')
