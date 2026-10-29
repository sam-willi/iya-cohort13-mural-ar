"""Pinball machine (Leanne W.): her Hollywood-themed table. Cabinet on four tall legs with
"COHORT 13" down the side, coin door, start button and plunger on the front, a sloped playfield under
glass (star at the top, HOLLYWOOD on the hills, the city skyline, WOW clouds, bumpers, a winding ramp
on the left, flippers and slingshots), and a backbox with "IYA" and stars on the backglass and a
score display."""
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
CAB = kit.mat('cardinal', rough=0.45, name='cabinet_paint')
CHROME = kit.mat('chrome', rough=0.2, metal=1.0, name='chrome')
STEEL = kit.mat('steel', rough=0.32, metal=0.9, name='steel')
BLACK = kit.mat('black', rough=0.5, name='black')
RUBBER = kit.mat('rubber', rough=0.85, name='rubber')
DOOR = kit.mat('gunmetal', rough=0.35, metal=0.8, name='coin_door')
GLASS = kit.mat('glass', rough=0.03, alpha=0.08, name='glass')
WHITE = kit.mat('white', rough=0.4, name='plastic_white')
REDP = kit.mat('red', rough=0.3, name='plastic_red')
AMBERP = kit.mat('amber', rough=0.3, emit=0.6, name='lit_amber')
LAMP = kit.mat('lamp', rough=0.3, emit=1.2, name='lit_lamp')
CREAM = kit.mat('cream', rough=0.5, name='apron')
CLEAR = kit.mat('#cfe3ea', rough=0.05, alpha=0.45, name='clear_ramp')

# ---------- dimensions ----------
W, L = 0.72, 1.24          # cabinet width (x) and length (y); front at -Y
ZB = 0.70                  # cabinet bottom
ZF, ZR = 1.03, 1.17        # top rail height at the front and back


def ztop(y):
    return ZF + (ZR - ZF) * (y + L / 2) / L


SLOPE = math.atan2(ZR - ZF, L)

# ---------- textures ----------
FONT = """
def disp(px):
    for f in ('/System/Library/Fonts/Supplemental/Arial Black.ttf', '/System/Library/Fonts/Supplemental/Impact.ttf'):
        try:
            return ImageFont.truetype(f, px)
        except Exception:
            pass
    return font(px)
def star(cx, cy, r, fill, rot=-90, inner=0.42):
    import math
    pts = []
    for i in range(10):
        a = math.radians(rot + 36 * i); rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)
def ctext(x, y, s, f, fill, outline=None, ow=0):
    if outline:
        d.text((x, y), s, font=f, fill=fill, anchor='mm', stroke_width=ow, stroke_fill=outline)
    else:
        d.text((x, y), s, font=f, fill=fill, anchor='mm')
"""

pf_img = pil_texture('playfield', FONT + """
import math, random
random.seed(5)
CW, CH = 576, 1024
img = Image.new('RGB', (CW, CH)); d = ImageDraw.Draw(img)
for y in range(CH):                       # night sky to teal
    t = y / CH
    d.line([(0, y), (CW, y)], fill=(int(31 + 16 * t), int(50 + 75 * t), int(80 + 54 * t)))
for i in range(60):
    x, y = random.randint(0, CW), random.randint(0, 420)
    d.ellipse([x, y, x + 3, y + 3], fill=(240, 228, 200))
# searchlights either side of the big star
for sx in (150, 426):
    d.polygon([(sx, 330), (sx - 60 + (sx - 288) // 3, 40), (sx + 10 + (sx - 288) // 3, 40)], fill=(70, 98, 120))
star(288, 120, 92, (246, 194, 90)); star(288, 120, 52, (232, 163, 58))
# hills with the sign
d.polygon([(0, 470), (90, 380), (190, 350), (300, 395), (400, 340), (500, 372), (576, 420), (576, 520), (0, 520)], fill=(90, 58, 34))
f = disp(46)
ctext(288, 405, 'HOLLYWOOD', f, (242, 239, 232))
# skyline
x = 0
while x < CW:
    w = random.randint(34, 70); h = random.randint(90, 230)
    col = random.choice([(90, 58, 34), (60, 64, 71), (154, 106, 60)])
    d.rectangle([x, 760 - h, x + w, 760], fill=col)
    for wy in range(760 - h + 12, 752, 18):
        for wx in range(x + 7, x + w - 8, 14):
            if random.random() < 0.6:
                d.rectangle([wx, wy, wx + 6, wy + 8], fill=(246, 194, 90))
    x += w + random.randint(0, 6)
d.rectangle([0, 760, CW, 1024], fill=(39, 70, 84))
# WOW clouds
for cx, cy, s in ((130, 880, 1.0), (440, 600, 0.85), (300, 520, 0.6)):
    for dx, dy, r in ((-40, 0, 34), (0, -14, 40), (40, 0, 34), (0, 18, 30)):
        d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s], fill=(239, 227, 200))
    ctext(cx, cy + 2, 'WOW', disp(int(30 * s)), (184, 50, 42))
# insert lights: arrows up the lanes and a ring of round inserts
for x, y, c in ((120, 690, (232, 163, 58)), (288, 650, (184, 50, 42)), (456, 690, (217, 102, 42))):
    d.polygon([(x, y - 34), (x + 22, y + 14), (x - 22, y + 14)], fill=c, outline=(242, 239, 232))
for i in range(7):
    a = math.radians(200 + i * 20)
    x, y = 288 + 150 * math.cos(a), 900 + 110 * math.sin(a)
    d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=[(232, 163, 58), (184, 50, 42), (143, 195, 220)][i % 3], outline=(30, 29, 28))
# top rollover lanes
for x in (200, 288, 376):
    d.rectangle([x - 3, 210, x + 3, 300], fill=(242, 239, 232))
# inlane / outlane guides and the plunger lane
for sx in (-1, 1):
    d.line([(288 + sx * 250, 760), (288 + sx * 250, 930), (288 + sx * 120, 985)], fill=(242, 239, 232), width=5)
d.rectangle([522, 60, 576, 1024], fill=(30, 29, 28))
img = img.resize((S, S))
""", size=1024)
PLAYFIELD = tex_mat(pf_img, rough=0.25, name='playfield')

bg_img = pil_texture('backglass', FONT + """
import math
CW, CH = 720, 600
img = Image.new('RGB', (CW, CH)); d = ImageDraw.Draw(img)
for y in range(CH):
    t = y / CH
    d.line([(0, y), (CW, y)], fill=(int(30 + 40 * t), int(40 + 30 * t), int(70 + 20 * t)))
for i in range(14):
    a = math.radians(i * 360 / 14)
    d.polygon([(360, 230), (360 + 600 * math.cos(a), 230 + 600 * math.sin(a)), (360 + 600 * math.cos(a + 0.12), 230 + 600 * math.sin(a + 0.12))],
              fill=(52, 66, 96))
ctext(360, 220, 'IYA', disp(230), (239, 227, 200), (184, 50, 42), 10)
for x, y, r in ((90, 80, 34), (620, 120, 40), (130, 380, 26), (560, 360, 30), (470, 60, 20), (250, 400, 18)):
    star(x, y, r, (246, 194, 90))
# score display
d.rectangle([200, 470, 520, 560], fill=(18, 16, 14), outline=(184, 137, 58), width=6)
ctext(360, 516, '15500', disp(64), (232, 120, 30))
img = img.resize((S, S))
""", size=1024)
BACKGLASS = tex_mat(bg_img, rough=0.15, name='backglass')

side_img = pil_texture('side_art', FONT + """
import math
CW, CH = 1024, 440
img = Image.new('RGB', (CW, CH), (153, 32, 28)); d = ImageDraw.Draw(img)
for i in range(18):
    a = math.radians(-90 + i * 20)
    d.polygon([(160, 330), (160 + 1400 * math.cos(a), 330 + 1400 * math.sin(a)), (160 + 1400 * math.cos(a + 0.17), 330 + 1400 * math.sin(a + 0.17))],
              fill=(170, 44, 36))
ctext(470, 245, 'COHORT 13', disp(124), (246, 194, 90), (30, 29, 28), 7)
for x, y, r in ((120, 90, 46), (930, 110, 40), (860, 380, 30), (230, 380, 24)):
    star(x, y, r, (239, 227, 200))
img = img.resize((S, S))
""", size=1024)
SIDE = tex_mat(side_img, rough=0.4, name='side_art')

bside_img = pil_texture('backbox_side', FONT + """
img.paste((153, 32, 28), (0, 0, S, S))
for x, y, r in ((300, 260, 120), (700, 520, 90), (360, 800, 70), (760, 180, 50)):
    star(x, y, r, (246, 194, 90))
""", size=512)
BSIDE = tex_mat(bside_img, rough=0.4, name='backbox_art')

# ---------- cabinet ----------
prof = [(-L / 2, ZB), (L / 2, ZB), (L / 2, ZR), (-L / 2, ZF)]
YZX = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # extrude's (x, y, z) -> world (y, z, x)
cab = kit.extrude([(y, z) for y, z in prof], W, name='cabinet')
cab.data.transform(Matrix.Translation((-W / 2, 0, 0)) @ YZX)
kit.finish(cab, CAB, smooth=0)
# playfield well
WI, YI0, YI1, DEP = 0.03, -L / 2 + 0.035, 0.335, 0.085
well = kit.extrude([(YI0, ztop(YI0) - DEP), (YI1, ztop(YI1) - DEP), (YI1, 2.0), (YI0, 2.0)], W - 2 * WI, name='well')
well.data.transform(Matrix.Translation((-(W - 2 * WI) / 2, 0, 0)) @ YZX)
kit.boolean(cab, well)
bv = cab.modifiers.new('bevel', 'BEVEL'); bv.width = 0.006; bv.segments = 2; bv.limit_method = 'ANGLE'
weighted_normals(cab)


def on_slope(x, y, h):
    """A point h above the playfield floor (which sits DEP below the rails)."""
    return Vector((x, y, ztop(y) - DEP + h))


PX = W / 2 - WI
pf = uv_quad([on_slope(-PX, YI0, 0.0005), on_slope(PX, YI0, 0.0005), on_slope(PX, YI1, 0.0005), on_slope(-PX, YI1, 0.0005)],
             [(0, 0), (1, 0), (1, 1), (0, 1)], 'playfield', PLAYFIELD)
glass = uv_quad([on_slope(-PX, YI0, DEP - 0.004), on_slope(PX, YI0, DEP - 0.004), on_slope(PX, YI1, DEP - 0.004), on_slope(-PX, YI1, DEP - 0.004)],
                [(0, 0), (1, 0), (1, 1), (0, 1)], 'glass', GLASS)
# side rails and lockdown bar
for sx in (-1, 1):
    r = kit.box((0.035, L - 0.02, 0.012), material=CHROME, bevel=0.004, segments=3, name='side_rail')
    r.location = (sx * (W / 2 - 0.0175), 0, (ZF + ZR) / 2 + 0.004); r.rotation_euler = (SLOPE, 0, 0)
kit.box((W + 0.006, 0.05, 0.022), at=(0, -L / 2 + 0.02, ZF + 0.008), material=CHROME, bevel=0.006, segments=3, name='lockdown_bar')
# side art panels, both sides
for sx in (-1, 1):
    x = sx * (W / 2 + 0.0008)
    m = 0.02
    c = [(x, -L / 2 + m, ZB + m), (x, L / 2 - m, ZB + m), (x, L / 2 - m, ZR - m), (x, -L / 2 + m, ZF - m)]
    uv = [((y + L / 2) / L, (z - ZB) / (ZR - ZB)) for _, y, z in c]
    if sx < 0:
        c = c[::-1]; uv = [(1 - u, v) for u, v in uv[::-1]]
    uv_quad(c, uv, 'side_art', SIDE)
    # flipper button
    kit.cyl(0.014, 0.02, at=(sx * (W / 2 + 0.006), -L / 2 + 0.11, ZF - 0.07), rot=(0, 90, 0), material=REDP, bevel=0.003, verts=24, name='flipper_button')
    kit.cyl(0.019, 0.006, at=(sx * (W / 2 + 0.001), -L / 2 + 0.11, ZF - 0.07), rot=(0, 90, 0), material=CHROME, bevel=0.0015, verts=24, name='button_ring')

# ---------- front panel ----------
FY = -L / 2
door = kit.box((0.27, 0.012, 0.21), at=(-0.04, FY - 0.004, ZB + 0.15), material=DOOR, bevel=0.004, segments=2, name='coin_door')
for dx in (-0.06, 0.06):
    kit.box((0.05, 0.008, 0.06), at=(-0.04 + dx, FY - 0.011, ZB + 0.19), material=BLACK, bevel=0.002, name='coin_slot_plate')
    kit.box((0.026, 0.006, 0.034), at=(-0.04 + dx, FY - 0.014, ZB + 0.19), material=AMBERP, bevel=0.002, name='coin_button')
    kit.box((0.05, 0.008, 0.03), at=(-0.04 + dx, FY - 0.011, ZB + 0.09), material=BLACK, bevel=0.002, name='coin_return')
kit.cyl(0.009, 0.01, at=(-0.04, FY - 0.012, ZB + 0.13), rot=(90, 0, 0), material=CHROME, bevel=0.002, verts=20, name='door_lock')
kit.cyl(0.016, 0.012, at=(-0.28, FY - 0.005, ZF - 0.06), rot=(90, 0, 0), material=LAMP, bevel=0.004, verts=24, name='start_button')
kit.cyl(0.022, 0.004, at=(-0.28, FY - 0.001, ZF - 0.06), rot=(90, 0, 0), material=CHROME, bevel=0.001, verts=24, name='start_ring')
# plunger: chrome housing, rod and a ball knob
kit.cyl(0.024, 0.012, at=(0.27, FY - 0.006, ZF - 0.085), rot=(90, 0, 0), material=CHROME, bevel=0.003, verts=24, name='plunger_housing')
kit.cyl(0.006, 0.07, at=(0.27, FY - 0.045, ZF - 0.085), rot=(90, 0, 0), material=CHROME, verts=16, name='plunger_rod')
kit.cyl(0.014, 0.022, at=(0.27, FY - 0.086, ZF - 0.085), rot=(90, 0, 0), material=REDP, bevel=0.006, segments=3, verts=24, name='plunger_knob')
kit.torus(0.011, 0.0035, at=(0.27, FY - 0.062, ZF - 0.085), rot=(90, 0, 0), material=STEEL, name='plunger_spring')

# ---------- legs ----------
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * (W / 2 - 0.045), sy * (L / 2 - 0.05)
        leg = kit.cyl(0.04, ZB - 0.03, r2=0.028, verts=4, at=(x, y, 0.03 + (ZB - 0.03) / 2), material=CHROME, name='leg')
        leg.rotation_euler = (0, math.radians(180), math.radians(45))
        kit.finish(leg, CHROME, bevel=0.004, segments=2, smooth=0)
        kit.box((0.075, 0.075, 0.012), at=(x, y, ZB - 0.004), material=STEEL, bevel=0.002, name='leg_plate')
        kit.cyl(0.006, 0.03, at=(x, y, 0.025), material=STEEL, verts=12, name='leveler')
        kit.cyl(0.02, 0.012, at=(x, y, 0.006), material=RUBBER, bevel=0.003, verts=24, name='foot')

# ---------- backbox ----------
BY0, BY1, BZ0, BZ1 = 0.355, L / 2, 1.13, 1.86
bb = kit.box((W - 0.01, BY1 - BY0, BZ1 - BZ0), at=(0, (BY0 + BY1) / 2, (BZ0 + BZ1) / 2), material=CAB, bevel=0.008, segments=2, name='backbox')
# backglass in a chrome frame, and a speaker strip under it
gz0, gz1 = 1.27, 1.82
kit.box((W - 0.03, 0.008, gz1 - gz0 + 0.03), at=(0, BY0 - 0.002, (gz0 + gz1) / 2), material=CHROME, bevel=0.003, name='backglass_frame')
uv_quad([(-(W - 0.07) / 2, BY0 - 0.0065, gz0), ((W - 0.07) / 2, BY0 - 0.0065, gz0), ((W - 0.07) / 2, BY0 - 0.0065, gz1), (-(W - 0.07) / 2, BY0 - 0.0065, gz1)],
        [(0, 0), (1, 0), (1, 1), (0, 1)], 'backglass', BACKGLASS)
kit.box((W - 0.06, 0.006, 0.09), at=(0, BY0 - 0.002, 1.19), material=BLACK, bevel=0.002, name='speaker_panel')
for sx in (-1, 1):
    for k in range(5):
        kit.box((0.09, 0.004, 0.006), at=(sx * 0.2, BY0 - 0.006, 1.16 + k * 0.015), material=DOOR, name='grille_slot')
for sx in (-1, 1):
    x = sx * ((W - 0.01) / 2 + 0.0008)
    c = [(x, BY0 + 0.015, BZ0 + 0.02), (x, BY1 - 0.015, BZ0 + 0.02), (x, BY1 - 0.015, BZ1 - 0.02), (x, BY0 + 0.015, BZ1 - 0.02)]
    uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    if sx < 0:
        c = c[::-1]; uv = uv[::-1]
    uv_quad(c, uv, 'backbox_art', BSIDE)
# vents on the back of the backbox
for k in range(6):
    kit.box((0.42, 0.006, 0.012), at=(0, BY1 + 0.001, 1.62 + k * 0.03), material=BLACK, bevel=0.002, name='vent')
# a little lamp on the backbox side, as drawn
lx = (W - 0.01) / 2
kit.cyl(0.006, 0.12, at=(lx + 0.006, 0.5, 1.5), material=CHROME, verts=12, name='lamp_post')
kit.cyl(0.022, 0.04, r2=0.012, at=(lx + 0.02, 0.48, 1.565), rot=(0, -60, 0), material=CHROME, verts=24, name='lamp_shade')
kit.sphere(0.011, at=(lx + 0.034, 0.47, 1.555), material=LAMP, segs=16, rings=8, name='lamp_bulb')
kit.box((0.02, 0.06, 0.02), at=(lx + 0.008, 0.5, 1.44), material=STEEL, bevel=0.002, name='lamp_bracket')

# ---------- playfield toys (built flat, then laid on the slope) ----------
toys = []


def toy(o):
    toys.append(o); return o


def bumper(x, y):
    toy(kit.cyl(0.042, 0.006, at=(x, y, 0.003), material=BLACK, bevel=0.002, verts=32, name='bumper_base'))
    toy(kit.cyl(0.03, 0.035, at=(x, y, 0.022), material=WHITE, bevel=0.002, verts=32, name='bumper_body'))
    toy(kit.cyl(0.04, 0.004, at=(x, y, 0.014), material=STEEL, bevel=0.001, verts=32, name='bumper_ring'))
    toy(kit.cyl(0.036, 0.016, r2=0.03, at=(x, y, 0.047), material=REDP, bevel=0.003, verts=32, name='bumper_cap'))
    toy(kit.cyl(0.012, 0.004, at=(x, y, 0.057), material=LAMP, bevel=0.001, verts=24, name='bumper_lamp'))


for x, y in ((-0.12, 0.17), (0.08, 0.2), (-0.02, 0.06)):
    bumper(x, y)
# flippers
for sx in (-1, 1):
    pts = [(0.0, -0.016), (0.075, -0.007), (0.08, 0.0), (0.075, 0.007), (0.0, 0.016), (-0.012, 0.0)]
    fl = kit.extrude(pts, 0.024, name='flipper')
    fl.data.transform(Matrix.Rotation(math.radians(-25 if sx < 0 else 205), 4, 'Z'))
    fl.location = (sx * 0.095, -0.48, 0.0)
    toy(kit.finish(fl, WHITE, bevel=0.003, smooth=30))
    toy(kit.cyl(0.006, 0.03, at=(sx * 0.095, -0.48, 0.015), material=REDP, verts=12, name='flipper_pivot'))
    # slingshot
    tri = [(0, 0), (0, 0.13), (-0.075 * sx, 0.015)] if sx > 0 else [(0, 0), (-0.075 * sx, 0.015), (0, 0.13)]
    sl = kit.extrude([(sx * 0.17 + px, -0.40 + py) for px, py in tri], 0.03, name='slingshot')
    toy(kit.finish(sl, WHITE, bevel=0.004, smooth=30))
    toy(kit.extrude([(sx * 0.17 + px * 1.12, -0.40 + py * 1.06 - 0.004) for px, py in tri], 0.012, name='sling_rubber'))
    toys[-1].location.z = 0.008
    kit.finish(toys[-1], RUBBER, bevel=0.002, smooth=30)
    # in/outlane guide
    toy(kit.box((0.008, 0.16, 0.025), at=(sx * 0.255, -0.35, 0.0125), material=WHITE, bevel=0.002, name='lane_guide'))
# plunger lane wall, with the arc at the top
toy(kit.box((0.01, 0.82, 0.03), at=(0.265, -0.18, 0.015), material=WHITE, bevel=0.002, name='plunger_wall'))
arcp = [(0.325 - 0.11 + 0.11 * math.cos(a), 0.215 + 0.11 * math.sin(a), 0.015) for a in [math.radians(i * 9) for i in range(11)]]
toy(sweep(arcp, rounded_rect(0.01, 0.03, 0.002, n=1), name='lane_arc', material=WHITE, up=(0, 0, 1)))
# winding ramp on the left: two chrome rails on posts, a clear floor between them
rp = []
for i in range(40):
    t = i / 39
    rp.append((-0.24 + 0.06 * math.sin(t * math.pi * 2.2), -0.25 + 0.55 * t, 0.03 + 0.06 * math.sin(t * math.pi) + 0.02 * t))
rp = resample(rp, 60)
for off in (-0.022, 0.022):
    rail = [p + Vector((off, 0, 0.014)) for p in rp]
    toy(sweep(rail, [(0.0028 * math.cos(a), 0.0028 * math.sin(a)) for a in [i * math.tau / 8 for i in range(8)]], name='ramp_rail', material=CHROME))
toy(sweep(rp, rounded_rect(0.003, 0.05, 0.001, n=1), name='ramp_floor', material=CLEAR, up=(1, 0, 0)))
for i in (8, 30, 52):
    p = rp[i]
    toy(kit.cyl(0.004, p.z, at=(p.x, p.y, p.z / 2), material=CHROME, verts=10, name='ramp_post'))
# the star at the top, standing on a post
st = []
for i in range(10):
    a = math.radians(90 + 36 * i); r = 0.05 if i % 2 == 0 else 0.021
    st.append((r * math.cos(a), r * math.sin(a)))
sto = kit.extrude(st, 0.012, name='star')
sto.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
sto.location = (0.0, 0.29, 0.07)
toy(kit.finish(sto, LAMP, bevel=0.002, smooth=30))
toy(kit.cyl(0.005, 0.04, at=(0.0, 0.29, 0.02), material=CHROME, verts=10, name='star_post'))
# rollover lane guides at the top
for x in (-0.09, 0.0, 0.09):
    toy(kit.box((0.008, 0.07, 0.02), at=(x - 0.045, 0.19 + 0.06, 0.01), material=WHITE, bevel=0.002, name='top_lane'))
# apron and the ball
toy(kit.box((0.5, 0.08, 0.02), at=(0.0, -0.55, 0.01), material=CREAM, bevel=0.004, name='apron'))
toy(kit.sphere(0.0135, at=(0.06, -0.3, 0.0135), material=CHROME, segs=24, rings=12, name='ball'))
for o in toys:
    bpy.context.view_layer.update()
    o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    o.data.transform(Matrix.Translation((0, 0, ZF - DEP + 0.001 + (ZR - ZF) * L / 2 / L)) @ Matrix.Rotation(SLOPE, 4, 'X'))

kit.export('pinball-machine')
