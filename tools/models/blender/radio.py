"""Radio (Art Deco) - Mikayla Wang.

Her drawing: a tabletop radio built as IYA's own building, "Iovine and Young Hall". A tall block with rounded roof edges;
four knobs across the top of the front; a lintel band lettered IOVINE AND YOUNG HALL; stone courses below it; a big
chamfered (Tudor) arch with a moulded surround holding the speaker grille - a cross-hatched lattice split by mullions;
a plinth with corner blocks. On top, raised Deco bars, one of which wraps over the roof and runs down each side as a
pilaster between columns of mullioned windows, with a few loose bricks showing.
Line drawing, so materials are a choice: cream stone-coloured cabinet, butterscotch bakelite trim and relief (period
Catalin colours, pulled to the mural's honey), brass knobs, lattice and lettering, walnut grille cloth, dark window glass.
The back (not drawn) carries on the building's windows.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix

FONTS = '/System/Library/Fonts/Supplemental/'


def cut(target, cutter, op='DIFFERENCE', self_=False):
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'; md.use_self = self_
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('cut') > 0:
        bpy.ops.object.modifier_move_up(modifier='cut')
    bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def apply_xform(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def front_prism(poly, y0, depth, material, name):
    """Extrude a front-view polygon [(x, z)] from y0 back by depth (+Y)."""
    o = kit.extrude(poly, depth, material=material, name=name)
    o.rotation_euler = (math.radians(90), 0, 0); o.location = (0, y0 + depth, 0)
    apply_xform(o)
    return o


def side_place(o, s, W):
    """Objects modelled on the -Y (front) face, re-laid onto the +-X sides: rotate about Z."""
    o.data.transform(Matrix.Rotation(math.radians(90 if s > 0 else -90), 4, 'Z')); o.data.update()
    return o


def text(s, size, font, material, depth):
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(font); cu.resolution_u = 3; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    o = bpy.data.objects.new('txt', cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    return o


# ---------------------------------------------------------------- materials
STONE = kit.mat('#ece0c4', rough=0.55, name='cabinet')
JOINT = kit.mat('#b9a684', rough=0.8, name='joint')
TRIM = kit.mat('honey', rough=0.32, name='bakelite')
BRASS = kit.mat('brass', rough=0.28, metal=1.0, name='brass')
CLOTH = kit.mat('walnut', rough=0.9, name='grillecloth')
KNOB = kit.mat('#4a2a17', rough=0.25, name='knob')
GLASS = kit.mat('#22313a', rough=0.06, name='window')
BRICK = kit.mat('copper', rough=0.7, name='brick')

W, D, H = 0.22, 0.17, 0.36
YF = -D / 2
RR = 0.032                                  # roof edge radius

# ---------------------------------------------------------------- cabinet: big round on the roof edges only
bpy.ops.mesh.primitive_cube_add(size=1)
cab = bpy.context.object; cab.name = 'cabinet'; cab.scale = (W, D, H)
bpy.ops.object.transform_apply(scale=True); cab.location = (0, 0, H / 2); apply_xform(cab)
me = cab.data
bw = me.attributes.new('bevel_weight_edge', 'FLOAT', 'EDGE')
for e in me.edges:
    a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
    bw.data[e.index].value = 1.0 if (a.z > H - 1e-4 and b.z > H - 1e-4) else 0.0
md = cab.modifiers.new('roof', 'BEVEL'); md.width = RR; md.segments = 6; md.limit_method = 'WEIGHT'
md = cab.modifiers.new('edges', 'BEVEL'); md.width = 0.0025; md.segments = 2; md.limit_method = 'ANGLE'
md.angle_limit = math.radians(60)
apply_mods(cab)
cab.data.materials.append(STONE)

# arch: Tudor-chamfered opening, recessed for the grille
AW, AZ0, AZS, AZT, AFW = 0.142, 0.03, 0.188, 0.248, 0.056


def arch(w, z0, zs, zt, fw):
    return [(-w / 2, z0), (w / 2, z0), (w / 2, zs), (fw / 2, zt), (-fw / 2, zt), (-w / 2, zs)]


cut(cab, front_prism(arch(AW, AZ0 - 0.01, AZS, AZT, AFW), YF - 0.01, 0.026, CLOTH, 'archcut'))

# stone courses on the front below the lintel (one cutter, then one boolean)
grooves = []
gz = [0.058, 0.088, 0.118, 0.148, 0.178, 0.208, 0.238]
for z in gz:
    grooves.append(kit.box((W + 0.01, 0.004, 0.0016), at=(0, YF, z), material=JOINT))
for i, (z0, z1) in enumerate(zip([0.03] + gz, gz + [0.262])):
    off = 0.0 if i % 2 == 0 else 0.026
    for x in [-0.104 + off + k * 0.052 for k in range(5)]:
        if abs(x) < W / 2 - 0.004:
            grooves.append(kit.box((0.0016, 0.004, z1 - z0 - 0.0016), at=(x, YF, (z0 + z1) / 2), material=JOINT))
g = join(grooves)
cut(cab, g, self_=True)
kit.finish(cab, None, smooth=35)

# arch surround moulding and its foot blocks
outer = front_prism(arch(AW + 0.028, AZ0, AZS + 0.006, AZT + 0.014, AFW + 0.02), YF - 0.007, 0.008, TRIM, 'surround')
cut(outer, front_prism(arch(AW, AZ0 - 0.02, AZS, AZT, AFW), YF - 0.02, 0.05, TRIM, 'surroundhole'))
md = outer.modifiers.new('bevel', 'BEVEL'); md.width = 0.0022; md.segments = 2; md.limit_method = 'ANGLE'
kit.finish(outer, None, smooth=35)
for s in (1, -1):
    kit.box((0.022, 0.014, 0.03), at=(s * (AW / 2 + 0.007), YF - 0.004, 0.04), material=TRIM, bevel=0.002, name='foot')

# grille: walnut cloth, brass diagonal lattice clipped to the arch, bakelite mullions
YG = YF + 0.012
kit.box((AW, 0.004, AZT - AZ0), at=(0, YG + 0.004, (AZ0 + AZT) / 2), material=CLOTH, name='cloth')
bars = []
for sgn in (1, -1):
    for k in range(-18, 19):
        c = k * 0.0105
        bars.append(kit.box((0.0016, 0.0022, 0.40), at=(c, YG, 0.14), rot=(0, sgn * 40, 0), material=BRASS,
                            name='lattice'))
lat = join(bars); apply_xform(lat)
cut(lat, front_prism(arch(AW + 0.002, AZ0 - 0.005, AZS, AZT, AFW), YG - 0.01, 0.02, BRASS, 'clip'), 'INTERSECT',
    self_=True)
for x in (-0.024, 0.024):
    kit.box((0.0055, 0.006, AZT - AZ0), at=(x, YG - 0.002, (AZ0 + AZT) / 2), material=TRIM, bevel=0.0015, name='mullion')
kit.box((AW, 0.006, 0.0055), at=(0, YG - 0.002, 0.165), material=TRIM, bevel=0.0015, name='transom')

# lintel band with the name in brass Deco capitals ("AND" small and stacked, as she drew it)
kit.box((W - 0.004, 0.006, 0.034), at=(0, YF - 0.002, 0.282), material=STONE, bevel=0.0015, name='lintel')
for z in (0.2645, 0.2995):
    kit.box((W - 0.002, 0.008, 0.0028), at=(0, YF - 0.002, z), material=TRIM, bevel=0.0008, name='lintelrule')
YT = YF - 0.0052
parts = [('IOVINE', 0.0195, None), ('AND', 0.0095, None), ('YOUNG HALL', 0.0195, None)]
objs = [text(t, s, FONTS + 'Futura.ttc', BRASS, 0.0012) for t, s, _ in parts]
widths = [o.dimensions.x for o in objs]
gap = 0.006
total = sum(widths) + gap * 2
scale = min(1.0, (W - 0.022) / total)
x = -total * scale / 2
for o, w_, (t, s, _) in zip(objs, widths, parts):
    o.scale = (scale, scale, 1)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (x + w_ * scale / 2, YT, 0.282 + (0.002 if t == 'AND' else 0.0))
    apply_xform(o)
    x += (w_ + gap) * scale

# four knobs across the top of the front; the middle two have pointer lines
for i, x in enumerate((-0.078, -0.026, 0.026, 0.078)):
    k = kit.lathe([(0.0, 0.0), (0.0112, 0.0), (0.0115, 0.0025), (0.0106, 0.0105), (0.0094, 0.0135), (0.0, 0.0142)],
                  material=KNOB, steps=40, name='knob')
    k.rotation_euler = (math.radians(90), 0, 0); k.location = (x, YF, 0.315)
    kit.torus(0.0116, 0.0011, at=(x, YF - 0.0025, 0.315), rot=(90, 0, 0), material=BRASS, major=32, minor=6,
              name='knobring')
    if i in (1, 2):
        a = math.radians(-35 if i == 1 else 20)
        kit.box((0.0016, 0.002, 0.0075), at=(x + 0.0036 * math.sin(a), YF - 0.0142, 0.315 + 0.0036 * math.cos(a)),
                rot=(0, a * 180 / math.pi, 0), material=BRASS, name='pointer')

# plinth: a bakelite base course all round
kit.box((W + 0.010, D + 0.010, 0.026), at=(0, 0, 0.013), material=TRIM, bevel=0.003, segments=2, name='plinth')
kit.box((W + 0.004, D + 0.004, 0.006), at=(0, 0, 0.029), material=TRIM, bevel=0.0015, name='plinthcap')

# ---------------------------------------------------------------- roof relief and the wrapping pilaster band
YBAND = 0.012                         # the band crosses the roof a little behind centre
BW = 0.026


def roof_band(width, y, t=0.006):
    """A band of width `width` (along Y) wrapping over the roof from side to side and down both flanks."""
    pts = []
    zt = H + t
    # follow the cabinet's rounded roof edge (radius RR) outwards by t
    path = [(-W / 2 - t, 0.035)]
    for i in range(9):
        a = math.pi - i / 8 * (math.pi / 2)
        path.append((-W / 2 + RR + (RR + t) * math.cos(a), H - RR + (RR + t) * math.sin(a)))
    for i in range(9):
        a = math.pi / 2 - i / 8 * (math.pi / 2)
        path.append((W / 2 - RR + (RR + t) * math.cos(a), H - RR + (RR + t) * math.sin(a)))
    path.append((W / 2 + t, 0.035))
    inner = []
    path_in = [(-W / 2 - 0.0005, 0.035)]
    for i in range(9):
        a = math.pi - i / 8 * (math.pi / 2)
        path_in.append((-W / 2 + RR + (RR - 0.0005) * math.cos(a), H - RR + (RR - 0.0005) * math.sin(a)))
    for i in range(9):
        a = math.pi / 2 - i / 8 * (math.pi / 2)
        path_in.append((W / 2 - RR + (RR - 0.0005) * math.cos(a), H - RR + (RR - 0.0005) * math.sin(a)))
    path_in.append((W / 2 + 0.0005, 0.035))
    poly = path + list(reversed(path_in))
    o = kit.extrude(poly, width, material=TRIM, name='band')
    o.rotation_euler = (math.radians(90), 0, 0); o.location = (0, y + width / 2, 0)
    apply_xform(o)
    md = o.modifiers.new('bevel', 'BEVEL'); md.width = 0.0018; md.segments = 2; md.limit_method = 'ANGLE'
    return kit.finish(o, None, smooth=35)


roof_band(BW, YBAND)
# Deco bars standing on the roof's flat: one long bar crossing the band, two short ones beside it
flat = W / 2 - RR
for (x, y, lx, ly) in ((-0.045, 0.0, 0.026, D - 2 * RR - 0.002), (0.046, 0.039, 0.026, 0.026),
                       (0.033, -0.034, 0.088, 0.022)):
    kit.box((lx, ly, 0.012), at=(x, y, H + 0.005), material=TRIM, bevel=0.0018, segments=2, name='decobar')

# ---------------------------------------------------------------- windows on the flanks and the back
def window(cx, cz, w, h, rows, face, s=1):
    """A mullioned window modelled facing -Y at the origin, then laid on `face` ('L', 'R' or 'B')."""
    out = []
    out.append(kit.box((w + 0.006, 0.004, h + 0.006), at=(cx, 0.0, cz), material=TRIM, bevel=0.001, name='wframe'))
    out.append(kit.box((w, 0.004, h), at=(cx, -0.0012, cz), material=GLASS, name='glass'))
    out.append(kit.box((0.0018, 0.006, h), at=(cx, -0.0016, cz), material=BRASS, name='muntin'))
    for r in range(1, rows):
        out.append(kit.box((w, 0.006, 0.0018), at=(cx, -0.0016, cz - h / 2 + r * h / rows), material=BRASS,
                           name='muntin'))
    out.append(kit.box((w + 0.012, 0.009, 0.0045), at=(cx, -0.002, cz - h / 2 - 0.004), material=TRIM, bevel=0.001,
                       name='sill'))
    for o in out:
        apply_xform(o)
        if face == 'R':
            o.data.transform(Matrix.Translation((W / 2 + 0.0015, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
        elif face == 'L':
            o.data.transform(Matrix.Translation((-W / 2 - 0.0015, 0, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z'))
        else:
            o.data.transform(Matrix.Translation((0, D / 2 + 0.0015, 0)) @ Matrix.Rotation(math.radians(180), 4, 'Z'))
        o.data.update()


# flank: in front of the pilaster (toward -Y) and behind it; in side-local coords x runs back-to-front
for face in ('R', 'L'):
    sgn = 1 if face == 'R' else -1
    for col_y in (-0.048, 0.056):                 # world Y of the window column
        for cz, h, rows in ((0.085, 0.052, 2), (0.170, 0.052, 2), (0.255, 0.058, 3)):
            cx = col_y if face == 'R' else -col_y
            window(cx, cz, 0.032, h, rows, face)
    # loose bricks showing through the render, as in the drawing
    for (yy, zz) in ((-0.072, 0.30), (-0.02, 0.05), (0.075, 0.13), (0.03, 0.31)):
        for dz, dy in ((0.0, 0.0), (0.0065, 0.009)):
            b = kit.box((0.003, 0.016, 0.0055), at=(sgn * (W / 2 + 0.0008), yy + dy, zz + dz), material=BRICK,
                        bevel=0.0008, name='brick')
for cx in (-0.06, 0.0, 0.06):
    for cz, h, rows in ((0.085, 0.052, 2), (0.170, 0.052, 2), (0.255, 0.058, 3)):
        window(cx, cz, 0.032, h, rows, 'B')
# a little power cord out of the back, coiled at the foot
kit.cyl(0.006, 0.01, at=(0.08, D / 2 + 0.004, 0.045), rot=(90, 0, 0), material=KNOB, verts=16, name='grommet')

kit.export('radio')
