"""Smartwatch - Alexis Limary.

Her drawing: a square watch on a wide strap that loops back as if round a wrist, standing on the loop. The face reads
"Thurs AUG 20" (commencement date) over a big "20:13" (the year IYA was founded), with three round complications,
76 (students in the cohort), 13 (cohort 13) and 4 (years). Crown and a long side button on the right. On top of the
strap, a Fight On hand sign and a Fight On pennant; adjustment holes through the strap; a buckle at the back whose
frame sticks out past the strap's edges.
Her notes are all USC, so: gold case, cardinal strap, gold prints. Screen and strap art are PIL-painted textures.
Invented: the case back sensor, the keeper.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy, bmesh, subprocess, tempfile, json

kit.reset()

CW, CH, CT = 0.042, 0.05, 0.011        # case width (x), height (z), thickness (y)
CZ = CH / 2                            # case centre height
BW, BT = 0.034, 0.003                  # strap width and thickness
TMP = tempfile.gettempdir()
SCREEN = os.path.join(TMP, 'smart-watch-screen.jpg')
STRAP = os.path.join(TMP, 'smart-watch-strap.jpg')

# ---------------------------------------------------------------- textures (PIL in system python)
PAINT = r'''
import sys, json, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
a = json.loads(sys.argv[1])
SUP = '/System/Library/Fonts/Supplemental/'
def hexc(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
GOLD, CARD, CREAM, INK = hexc('#f0b13e'), hexc('#99201c'), hexc('#f4ecd8'), hexc('#0b0b0c')
# --- screen: 420 x 512, black glass
W, H = 420, 512
im = Image.new('RGB', (W, H), INK); d = ImageDraw.Draw(im)
f_date = ImageFont.truetype(SUP + 'DIN Alternate Bold.ttf', 50)
f_big = ImageFont.truetype(SUP + 'DIN Condensed Bold.ttf', 236)
f_cpl = ImageFont.truetype(SUP + 'DIN Alternate Bold.ttf', 50)
d.text((W / 2, 62), 'Thurs AUG 20', font=f_date, fill=CREAM, anchor='mm')
d.text((W / 2 - 24, 222), '20', font=f_big, fill=GOLD, anchor='rm')
d.text((W / 2 + 24, 222), '13', font=f_big, fill=GOLD, anchor='lm')
for y in (190, 252):
    d.ellipse((W / 2 - 9, y - 9, W / 2 + 9, y + 9), fill=CARD)
for i, t in enumerate(('76', '13', '4')):
    cx, cy, r = 78 + i * 132, 418, 56
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hexc('#2a0b0a'), outline=GOLD, width=7)
    d.arc((cx - r + 13, cy - r + 13, cx + r - 13, cy + r - 13), -90, -90 + [300, 240, 180][i], fill=CARD, width=8)
    d.text((cx, cy + 2), t, font=f_cpl, fill=CREAM, anchor='mm')
im.save(a['screen'], quality=92)
# --- strap: u across, v along (v=0 at the image bottom = where the strap leaves the top of the case).
# Painted at true aspect, then squeezed to 256 x 1024.
W, H = 256, int(256 * a['length'] / a['width'])
random.seed(2)
im = Image.new('RGB', (W, H), CARD); px = im.load()
for y in range(H):
    for x in range(W):
        n = random.uniform(-6, 6)
        c = px[x, y]; px[x, y] = tuple(max(0, min(255, int(v + n))) for v in c)
d = ImageDraw.Draw(im)
for x in (14, W - 15):                                  # moulded edge lines
    d.line((x, 0, x, H), fill=hexc('#7a1815'), width=4)
def row(v): return (1 - v) * H
# Fight On hand sign, gold outline (Zapf Dingbats victory hand)
f_hand = ImageFont.truetype(SUP + 'ZapfDingbats.ttf', 150)
d.text((W / 2 - 6, row(a['v_hand'])), '✌', font=f_hand, fill=GOLD, anchor='mm')
# Fight On pennant
cx, cy = W / 2 + 8, row(a['v_flag'])
tri = [(cx - 84, cy - 48), (cx + 84, cy), (cx - 84, cy + 48)]
d.polygon(tri, fill=GOLD)
d.polygon([(cx - 73, cy - 37), (cx + 60, cy), (cx - 73, cy + 37)], fill=CARD)
f_flag = ImageFont.truetype(SUP + 'DIN Condensed Bold.ttf', 28)
d.text((cx - 28, cy - 11), 'FIGHT', font=f_flag, fill=GOLD, anchor='mm')
d.text((cx - 28, cy + 14), 'ON', font=f_flag, fill=GOLD, anchor='mm')
d.line((cx - 90, cy - 58, cx - 90, cy + 62), fill=GOLD, width=8)      # the pennant's staff
im = im.filter(ImageFilter.SMOOTH).resize((256, 1024), Image.LANCZOS)
im.save(a['strap'], quality=90)
'''


def paint(v_hand, v_flag, length):
    subprocess.run(['/usr/bin/env', 'python3', '-c', PAINT,
                    json.dumps({'screen': SCREEN, 'strap': STRAP, 'v_hand': v_hand, 'v_flag': v_flag,
                                'length': length, 'width': BW})], check=True)


def tex_mat(name, path, rough, emit=0.0):
    """Principled material with an image on Base Color (and Emission, so a screen glows)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
    m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if emit:
        m.node_tree.links.new(t.outputs['Color'], b.inputs['Emission Color'])
        b.inputs['Emission Strength'].default_value = emit
    return m


def rrect(w, h, r, n=8, cx=0.0, cy=0.0):
    pts = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def sel(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o


gold_m = kit.mat('brass', rough=0.3, metal=0.85, name='gold')
gold_dk_m = kit.mat('#8a6326', rough=0.35, metal=0.85, name='golddk')
glass_m = kit.mat('#0b0c0e', rough=0.06, name='glass')
card_m = kit.mat('cardinal', rough=0.6, name='cardinal')
dark_m = kit.mat('#1a1414', rough=0.5, name='dark')

# ---------------------------------------------------------------- strap path (y, z) and sweep
ZT, ZB = CH - 0.0025 - BT / 2, BT / 2  # centre heights of the top and bottom runs (top enters below the case's top edge)
YB = 0.073                             # back of the loop (centreline)
RC = 0.014                             # back corner radius
path = [(0.0, ZT), (YB - RC, ZT)]
for i in range(1, 9):
    a = math.radians(90 - 90 * i / 8)
    path.append((YB - RC + RC * math.cos(a), ZT - RC + RC * math.sin(a)))
for i in range(1, 9):
    a = math.radians(-90 * i / 8)
    path.append((YB - RC + RC * math.cos(a), ZB + RC + RC * math.sin(a)))
path.append((0.0, ZB))
# densify the straight runs so the texture and the hole cuts have rows to work with
dense = []
for (y0, z0), (y1, z1) in zip(path, path[1:]):
    n = max(1, int(math.dist((y0, z0), (y1, z1)) / 0.006))
    for k in range(n):
        dense.append((y0 + (y1 - y0) * k / n, z0 + (z1 - z0) * k / n))
dense.append(path[-1])
L = [0.0]
for p, q in zip(dense, dense[1:]):
    L.append(L[-1] + math.dist(p, q))
total = L[-1]
V_HAND, V_FLAG = 0.022 / total, 0.047 / total
paint(V_HAND, V_FLAG, total)
screen_m = tex_mat('screen', SCREEN, 0.15, emit=0.9)
strap_m = tex_mat('strap', STRAP, 0.6)

me = bpy.data.meshes.new('strap'); bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
sec = [(-BW / 2, -1), (BW / 2, -1), (BW / 2, 1), (-BW / 2, 1)]   # x, side (-1 outer, +1 inner)
rings = []
for i, (y, z) in enumerate(dense):
    p0 = dense[max(0, i - 1)]; p1 = dense[min(len(dense) - 1, i + 1)]
    ty, tz = p1[0] - p0[0], p1[1] - p0[1]; tl = math.hypot(ty, tz); ty, tz = ty / tl, tz / tl
    ny, nz = tz, -ty                     # normal pointing out of the loop (outer side)
    rings.append([bm.verts.new((x, y + s * -ny * BT / 2, z + s * -nz * BT / 2)) for x, s in sec])
for i in range(len(rings) - 1):
    a, b = rings[i], rings[i + 1]
    for k in range(4):
        f = bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
        for l in f.loops:
            j = i if l.vert in a else i + 1
            u = (l.vert.co.x + BW / 2) / BW
            l[uv].uv = (u, L[j] / total)
for r in (rings[0], rings[-1]):
    f = bm.faces.new(r)
    for l in f.loops:
        l[uv].uv = (0.5, 0.0)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me); bm.free()
strap = bpy.data.objects.new('strap', me); bpy.context.collection.objects.link(strap)
kit.finish(strap, strap_m, smooth=35)
# adjustment holes through the bottom run and up the back
for y in (0.016, 0.028, 0.04):
    h = kit.box((0.0075, 0.0075, 0.02), at=(0, y, ZB))
    kit.boolean(strap, h)
md = strap.modifiers.new('bevel', 'BEVEL'); md.width = 0.0007; md.segments = 2; md.limit_method = 'ANGLE'
md.angle_limit = math.radians(50)

# buckle on the back run: a gold frame wider than the strap, a prong, and a keeper above it
BZ = 0.0295
frame = kit.box((BW + 0.007, BT + 0.004, 0.007), at=(0, YB, BZ), material=gold_m, bevel=0.0012, segments=2,
                name='buckle')
hole = kit.box((BW + 0.002, BT + 0.0012, 0.02), at=(0, YB, BZ))
sel(frame); bpy.ops.object.modifier_apply(modifier='bevel')
kit.boolean(frame, hole)
kit.cyl(0.0008, 0.008, at=(0, YB + BT / 2 + 0.0009, BZ - 0.0035), material=gold_m, verts=10, name='prong')
keeper = kit.box((BW + 0.003, BT + 0.0028, 0.006), at=(0, YB, BZ - 0.0105), material=card_m, bevel=0.0012,
                 segments=2, name='keeper')
sel(keeper); bpy.ops.object.modifier_apply(modifier='bevel')
kit.boolean(keeper, kit.box((BW + 0.0006, BT + 0.0004, 0.02), at=(0, YB, BZ - 0.0105)))

# ---------------------------------------------------------------- case
case = kit.extrude(rrect(CW, CH, 0.0105), CT, material=gold_m, bevel=0.0032, segments=4, name='case')
case.rotation_euler = (math.radians(90), 0, 0); case.location = (0, CT / 2, CZ)
# glass and the screen image on it
glass = kit.extrude(rrect(CW - 0.003, CH - 0.003, 0.009), 0.0012, material=glass_m, bevel=0.0006, segments=2,
                    name='glass')
glass.rotation_euler = (math.radians(90), 0, 0); glass.location = (0, -CT / 2 + 0.0004, CZ)
me = bpy.data.meshes.new('screen'); bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
SW, SH = 0.0345, 0.042
vs = [bm.verts.new((x, -CT / 2 - 0.0009, CZ + z)) for x, z in rrect(SW, SH, 0.0065)]
f = bm.faces.new(vs)
for l in f.loops:
    l[uv].uv = ((l.vert.co.x + SW / 2) / SW, (l.vert.co.z - CZ + SH / 2) / SH)
bm.to_mesh(me); bm.free()
scr = bpy.data.objects.new('screen', me); bpy.context.collection.objects.link(scr)
kit.finish(scr, screen_m, smooth=0)
# crown (with a cardinal ring) and the long side button, on the right
crown = kit.cyl(0.0036, 0.0042, at=(CW / 2 + 0.0019, 0.0, CZ + 0.009), rot=(0, 90, 0), material=gold_m,
                bevel=0.0005, verts=32, name='crown')
for k in range(24):
    a = math.tau * k / 24
    kit.box((0.0034, 0.0005, 0.0005), at=(CW / 2 + 0.0021, 0.0036 * math.cos(a), CZ + 0.009 + 0.0036 * math.sin(a)),
            rot=(math.degrees(a), 0, 0), material=gold_dk_m)
kit.cyl(0.0024, 0.0007, at=(CW / 2 + 0.0043, 0.0, CZ + 0.009), rot=(0, 90, 0), material=card_m, verts=24)
btn = kit.extrude(rrect(0.014, 0.0032, 0.0016), 0.0016, material=gold_m, bevel=0.0005, name='side_button')
btn.rotation_euler = (0, math.radians(90), 0); btn.location = (CW / 2 - 0.0003, 0.0, CZ - 0.008)
# back: sensor window
kit.cyl(0.0085, 0.0012, at=(0, CT / 2 + 0.0002, CZ), rot=(90, 0, 0), material=dark_m, bevel=0.0004, verts=40)
kit.cyl(0.003, 0.0016, at=(0, CT / 2 + 0.0004, CZ), rot=(90, 0, 0), material=glass_m, verts=24)

kit.export('smart-watch')
