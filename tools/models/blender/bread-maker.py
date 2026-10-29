"""Bread maker (Sara Attal).

Drawn in Sara_Attal_RV_P5a_Cohort_Mural (1).pdf: a long boxy machine with "BREAD / MAKER" across its long
face, a raised lid over the right half of the top, and a thick slice of bread with a "$" on it popping up out
of a slot on the left: it makes "bread". Line-only drawing, so: teal enamel body, cream lettering, chrome
trim, golden toast with a toasted "$".
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math, subprocess, tempfile
from mathutils import Vector, Matrix

kit.reset()
FUTURA = '/System/Library/Fonts/Supplemental/Futura.ttc'
FONT_BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def text3d(s, size, depth, font=None, at=(0, 0, 0), rot=(90, 0, 0), material=None, bevel=0.0, res=3,
           spacing=1.0, align='CENTER', name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    cu.align_x = align; cu.align_y = 'CENTER'; cu.resolution_u = res; cu.space_character = spacing
    cu.bevel_depth = bevel; cu.bevel_resolution = 1
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def resmooth(o, angle=35):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


# ---------- materials ----------
enamel = kit.mat('#2c7680', rough=0.32, name='enamel')
enamel_dk = kit.mat('#21585f', rough=0.4, name='enamel_dark')
cream = kit.mat('cream', rough=0.4, name='cream')
chrome = kit.mat('chrome', rough=0.18, metal=1.0, name='chrome')
rubber = kit.mat('rubber', rough=0.8, name='rubber')
dark = kit.mat('#141312', rough=0.6, name='slot_dark')
crust = kit.mat('#8a4c1c', rough=0.72, name='crust')
# crumb: a small generated texture (pores + a toasted edge) so the slice reads as bread, not plastic
crumb_tex = os.path.join(tempfile.mkdtemp(), 'crumb.png')
subprocess.run(['/usr/bin/env', 'python3', '-c', r"""
import sys, random
from PIL import Image, ImageDraw, ImageFilter
random.seed(13); N = 512
im = Image.new('RGB', (N, N), (238, 206, 146)); d = ImageDraw.Draw(im)
for _ in range(2600):
    x, y = random.uniform(0, N), random.uniform(0, N); r = random.uniform(1.2, 5.5) * random.choice((1, 1, 1, 1.8))
    t = random.uniform(0.62, 0.86)
    d.ellipse((x - r, y - r * random.uniform(0.5, 1.0), x + r, y + r * random.uniform(0.5, 1.0)),
              fill=(int(238 * t), int(200 * t), int(140 * t)))
for _ in range(900):
    x, y = random.uniform(0, N), random.uniform(0, N); r = random.uniform(0.8, 2.2)
    d.ellipse((x - r, y - r, x + r, y + r), fill=(250, 228, 184))
im = im.filter(ImageFilter.GaussianBlur(0.8))
# toasted rim: darken towards the outside of the slice
m = Image.new('L', (N, N), 0); md = ImageDraw.Draw(m)
md.rounded_rectangle((34, 20, N - 34, N - 30), radius=120, fill=255)
m = m.filter(ImageFilter.GaussianBlur(26))
dark = Image.new('RGB', (N, N), (196, 140, 72))
Image.composite(im, dark, m).save(sys.argv[1])
""", crumb_tex], check=True)
crumb = kit.mat('#ffffff', rough=0.85, name='crumb', image=crumb_tex)
toast = kit.mat('#6b3a17', rough=0.7, name='toasted')
glass = kit.mat('#bcd9e6', rough=0.05, alpha=0.35, name='window')
amber_led = kit.mat('#f6c25a', rough=0.3, emit=1.2, name='led')

# ---------- dimensions ----------
L, D, H, FT = 0.32, 0.15, 0.165, 0.008     # length (x), depth (y), height, feet
Z0 = FT; TOP = FT + H
SLOT_X = -L / 2 + 0.078                      # bread slot centre
SLOT_W, SLOT_D = 0.124, 0.036

# ---------- body ----------
body = kit.box((L, D, H), at=(0, 0, Z0 + H / 2), material=enamel, bevel=0.014, segments=4, name='body')
slot = kit.box((SLOT_W, SLOT_D, 0.12), at=(SLOT_X, 0, TOP), bevel=0.004, segments=2, name='slotcut')
kit.boolean(body, slot)
# a shallow belt groove around the body: a real seam between the top shell and the base
for sy in (-1, 1):
    g = kit.box((L + 0.01, 0.003, 0.0025), at=(0, sy * D / 2, Z0 + 0.03), name='groove')
    kit.boolean(body, g)
for sx in (-1, 1):
    g = kit.box((0.003, D + 0.01, 0.0025), at=(sx * L / 2, 0, Z0 + 0.03), name='groove')
    kit.boolean(body, g)
resmooth(body, 35)

# chrome bezel around the slot, dark well inside
bz = kit.box((SLOT_W + 0.014, SLOT_D + 0.014, 0.004), at=(SLOT_X, 0, TOP + 0.0005), bevel=0.0018, segments=2,
             name='slotbezel')
bzc = kit.box((SLOT_W, SLOT_D, 0.02), at=(SLOT_X, 0, TOP), bevel=0.004, segments=2, name='bzc')
kit.boolean(bz, bzc)
kit.finish(bz, chrome); resmooth(bz, 40)
kit.box((SLOT_W - 0.002, SLOT_D - 0.002, 0.003), at=(SLOT_X, 0, TOP - 0.0335), material=dark, name='slotfloor')
for sy in (-1, 1):   # dark inner walls so the slot reads deep
    kit.box((SLOT_W - 0.002, 0.002, 0.034), at=(SLOT_X, sy * (SLOT_D / 2 - 0.0012), TOP - 0.017), material=dark,
            name='slotwall')

# lid over the right half (hinged at the back) with a viewing window, like a real bread machine
LX0, LX1 = SLOT_X + SLOT_W / 2 + 0.022, L / 2 - 0.014
lw, ld = LX1 - LX0, D - 0.026
lid = kit.box((lw, ld, 0.018), at=((LX0 + LX1) / 2, 0, TOP + 0.009), material=enamel, bevel=0.007, segments=3,
              name='lid')
win = kit.box((lw - 0.05, ld - 0.05, 0.01), at=((LX0 + LX1) / 2, 0.004, TOP + 0.018), bevel=0.008, segments=3,
              name='wincut')
kit.boolean(lid, win)
resmooth(lid, 35)
kit.box((lw - 0.05, ld - 0.05, 0.004), at=((LX0 + LX1) / 2, 0.004, TOP + 0.0125), material=glass, bevel=0.007,
        segments=3, name='window')
kit.box((lw - 0.052, ld - 0.052, 0.002), at=((LX0 + LX1) / 2, 0.004, TOP + 0.0065), material=dark, bevel=0.006,
        name='windowback')
# hinge knuckles at the back of the lid
for hx in (LX0 + 0.025, LX1 - 0.025):
    kit.cyl(0.0045, 0.03, at=(hx, D / 2 - 0.013, TOP + 0.005), rot=(0, 90, 0), material=chrome, verts=16,
            name='hinge')
# chrome pull at the front of the lid
kit.tube([((LX0 + LX1) / 2 - 0.03, -ld / 2 + 0.002, TOP + 0.009), ((LX0 + LX1) / 2 - 0.026, -ld / 2 - 0.009, TOP + 0.010),
          ((LX0 + LX1) / 2 + 0.026, -ld / 2 - 0.009, TOP + 0.010), ((LX0 + LX1) / 2 + 0.03, -ld / 2 + 0.002, TOP + 0.009)],
         0.0028, material=chrome, name='pull')

# ---------- lettering on the long front face ----------
FY = -D / 2
text3d('BREAD', 0.054, 0.0022, font=FUTURA, at=(0.035, FY - 0.0009, Z0 + 0.105), rot=(90, 0, 0), material=cream,
       spacing=1.02, name='bread_word')
text3d('MAKER', 0.034, 0.0022, font=FUTURA, at=(0.035, FY - 0.0009, Z0 + 0.06), rot=(90, 0, 0), material=cream,
       spacing=1.25, name='maker_word')

# ---------- right end: browning dial, lever and a status light ----------
EX = L / 2
kit.cyl(0.03, 0.004, at=(EX + 0.0015, 0.0, Z0 + 0.075), rot=(0, 90, 0), material=chrome, bevel=0.001, verts=40,
        name='dialplate')
kit.cyl(0.021, 0.014, at=(EX + 0.009, 0.0, Z0 + 0.075), rot=(0, 90, 0), material=cream, bevel=0.003, verts=32,
        name='dial')
kit.box((0.006, 0.004, 0.026), at=(EX + 0.0165, 0.0, Z0 + 0.075), material=enamel_dk, bevel=0.0015, name='grip')
for k in range(7):
    a = math.radians(-60 + k * 20)
    kit.box((0.002, 0.0016, 0.004), at=(EX + 0.0036, 0.026 * math.sin(a), Z0 + 0.075 + 0.026 * math.cos(a)),
            rot=(-math.degrees(a), 0, 0), material=enamel_dk, name='tick')
kit.sphere(0.0035, at=(EX + 0.001, 0.0, Z0 + 0.125), scale=(0.6, 1, 1), material=amber_led, segs=16, rings=8,
           name='led')
# toaster-style lever on the slot end
kit.box((0.004, 0.014, 0.05), at=(-L / 2 - 0.002, 0.0, Z0 + 0.1), material=dark, bevel=0.0015, name='leverslot')
lev = kit.box((0.022, 0.032, 0.012), at=(-L / 2 - 0.012, 0.0, Z0 + 0.118), material=chrome, bevel=0.004,
              segments=3, name='lever')

# ---------- back: vents and cord ----------
for k in range(9):
    kit.box((0.004, 0.003, 0.05), at=(0.02 + k * 0.012, D / 2, Z0 + 0.085), material=dark, bevel=0.0015,
            name='vent')
cord = kit.tube([(-0.09, D / 2 - 0.004, Z0 + 0.03), (-0.09, D / 2 + 0.02, Z0 + 0.025), (-0.07, D / 2 + 0.045, 0.004),
                 (0.0, D / 2 + 0.05, 0.004), (0.045, D / 2 + 0.068, 0.0045), (0.058, D / 2 + 0.077, 0.006)], 0.0035,
                material=rubber, name='cord')
kit.cyl(0.0055, 0.016, at=(-0.09, D / 2 + 0.004, Z0 + 0.03), rot=(90, 0, 0), material=rubber, verts=16,
        name='strain')
kit.box((0.022, 0.03, 0.012), at=(0.064, D / 2 + 0.082, 0.006), rot=(0, 0, 40), material=rubber, bevel=0.003,
        segments=2, name='plug')
for dy in (-0.005, 0.005):
    kit.box((0.012, 0.0012, 0.006), at=(0.064 + 0.017 * math.cos(math.radians(40)) - dy * 0.64,
                                        D / 2 + 0.082 + 0.017 * math.sin(math.radians(40)) + dy * 0.77, 0.006),
            rot=(0, 0, 40), material=chrome, name='prong')

# feet
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cyl(0.011, FT + 0.002, at=(sx * (L / 2 - 0.03), sy * (D / 2 - 0.026), (FT + 0.002) / 2), material=rubber,
                bevel=0.002, verts=24, name='foot')


# ---------- the slice ----------
def slice_outline(w, h, lobe=0.0085, k=40):
    """Classic bread-slice silhouette: straight sides, then a crown that bulges past them. Base at y=0.
    Counter-clockwise from the bottom right."""
    hs = h * 0.44                      # top of the straight sides
    ry = h * 0.36; hc = h - ry         # crown ellipse
    rx = w / 2 + lobe
    pts = [(w / 2, 0.0), (w / 2, hs)]
    a0, a1 = math.radians(-28), math.radians(208)
    for i in range(k + 1):
        a = a0 + (a1 - a0) * i / k
        # flatten the very top a little, like a real loaf
        sy = math.sin(a); yy = hc + ry * (sy if sy < 0 else sy ** 0.8)
        pts.append((rx * math.cos(a), yy))
    pts += [(-w / 2, hs), (-w / 2, 0.0)]
    return pts


BW, BH, BT = 0.106, 0.15, 0.026
outline = slice_outline(BW, BH)
# crust: full silhouette; crumb: inset silhouette standing slightly proud on both faces
c = Vector((sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline)))
inset = []
for p in outline:
    v = Vector(p)
    d = (v - Vector((0, BH * 0.5)))
    inset.append(tuple(Vector((0, BH * 0.5)) + Vector((d.x * (1 - 0.0075 / (BW / 2)), d.y * (1 - 0.0075 / (BH / 2))))))
Z_BREAD = TOP - 0.032
crust_o = kit.extrude(outline, BT, material=crust, bevel=0.004, segments=3, name='crust')
crust_o.rotation_euler = (math.radians(90), 0, 0); crust_o.location = (SLOT_X, BT / 2, Z_BREAD)
crumb_o = kit.extrude(inset, BT + 0.002, material=crumb, bevel=0.0015, segments=2, name='crumb')
bm = bmesh.new(); bm.from_mesh(crumb_o.data); uvl = bm.loops.layers.uv.new('UVMap')
xs = [p[0] for p in inset]; ys = [p[1] for p in inset]
for f in bm.faces:
    for l in f.loops:
        l[uvl].uv = ((l.vert.co.x - min(xs)) / (max(xs) - min(xs)), (l.vert.co.y - min(ys)) / (max(ys) - min(ys)))
bm.to_mesh(crumb_o.data); bm.free()
crumb_o.rotation_euler = (math.radians(90), 0, 0); crumb_o.location = (SLOT_X, BT / 2 + 0.001, Z_BREAD + 0.0)
# toasted "$" on both faces
for side, ry in ((-1, 0), (1, 180)):
    text3d('$', 0.07, 0.0012, font=FONT_BOLD, at=(SLOT_X, side * (BT / 2 + 0.0012), Z_BREAD + BH * 0.5),
           rot=(90, 0, ry), material=toast, res=3, name='dollar')

kit.export('bread-maker')
