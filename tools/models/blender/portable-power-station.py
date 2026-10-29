"""Portable power station - Jake Ellengold.

His drawing: a stepped tower of boxes. A long base with two US outlets on its front (drawn as startled faces: the two
slots are eyes, the ground hole a mouth) and a side panel of two round sockets at the right end; a second tier set back
with two USB ports; a third box with another outlet face; a top cube holding a flagpole whose flag reads
"Don't step on me!"; a carry handle curled at the base's right corner; and a cord snaking off the left end to a plug.
Line-only drawing, so colours are a choice: orange housings (the classic power-station look, in the mural's orange),
dark gunmetal faceplates, cream outlets, a yellow Gadsden-style flag for the "don't step on me" joke.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix

FONTS = '/System/Library/Fonts/Supplemental/'


def mesh_obj(name, verts, faces, materials=()):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for m in materials:
        o.data.materials.append(m)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def rod(points, r, material, n=10, name='rod'):
    P = [Vector(p) for p in points]; verts = []; faces = []; m = len(P)
    for i, p in enumerate(P):
        t = (P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(ref).normalized(); v = t.cross(u).normalized()
        for k in range(n):
            a = k / n * math.tau
            verts.append(tuple(p + (u * math.cos(a) + v * math.sin(a)) * r))
    for i in range(m - 1):
        for k in range(n):
            faces.append((i * n + k, i * n + (k + 1) % n, (i + 1) * n + (k + 1) % n, (i + 1) * n + k))
    faces.append(tuple(reversed(range(n)))); faces.append(tuple(range((m - 1) * n, m * n)))
    return kit.finish(mesh_obj(name, verts, faces, [material]), None, smooth=60)


def cut(target, cutter, op='DIFFERENCE'):
    md = target.modifiers.new('cut', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'
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


def nurbs(ctrl, n=40):
    """Sample a smooth Catmull-Rom curve through control points."""
    P = [Vector(c) for c in ctrl]; out = []
    P = [P[0]] + P + [P[-1]]
    for i in range(1, len(P) - 2):
        for k in range(n // (len(P) - 3)):
            t = k / (n // (len(P) - 3))
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return [tuple(p) for p in out]


def text(s, size, font, material, depth, align='CENTER', res=3):
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(font); cu.resolution_u = res; cu.align_x = align; cu.align_y = 'CENTER'
    cu.space_line = 0.9
    o = bpy.data.objects.new('txt', cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    return o


# ---------------------------------------------------------------- materials
SHELL = kit.mat('orange', rough=0.5, name='housing')
PLATE = kit.mat('gunmetal', rough=0.45, name='faceplate')
CREAM = kit.mat('cream', rough=0.4, name='outlet')
HOLE = kit.mat('#0b0b0b', rough=0.8, name='hole')
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')
CORD = kit.mat('#1a1a1a', rough=0.55, name='cord')
METAL = kit.mat('chrome', rough=0.22, metal=1.0, name='metal')
BRASS = kit.mat('brass', rough=0.3, metal=0.95, name='brass')
FLAG = kit.mat('#ecc23c', rough=0.75, name='flag')
INK = kit.mat('black', rough=0.6, name='ink')


def housing(size, at, name):
    """A tier: orange shell with rounded edges and a dark rubber bumper band round its base."""
    sx, sy, sz = size
    o = kit.box(size, at=at, material=SHELL, bevel=0.012, segments=3, name=name)
    kit.box((sx + 0.006, sy + 0.006, 0.016), at=(at[0], at[1], at[2] - sz / 2 + 0.008), material=RUBBER, bevel=0.006,
            segments=2, name=name + '_bumper')
    return o


def front_panel(x, z, w, h, y_face, name):
    """Recessed dark faceplate on a -Y face."""
    kit.box((w, 0.006, h), at=(x, y_face - 0.001, z), material=PLATE, bevel=0.003, segments=2, name=name)
    return y_face - 0.004


def outlet(x, z, y_face, s=0.052, name='outlet'):
    """US receptacle facing -Y: cream plate, two vertical slots (eyes), round ground hole (mouth)."""
    p = kit.box((s, 0.006, s * 1.12), at=(x, y_face - 0.003, z), material=CREAM, bevel=0.005, segments=3, name=name)
    yf = y_face - 0.006
    for dx, hgt in ((-0.0105, 0.0135), (0.0105, 0.0115)):    # neutral slot a touch taller, as on a real outlet
        cut(p, kit.box((0.0032, 0.02, hgt), at=(x + dx * s / 0.052, yf, z + 0.010 * s / 0.052), material=HOLE))
    cut(p, kit.cyl(0.0052 * s / 0.052, 0.02, at=(x, yf, z - 0.014 * s / 0.052), rot=(90, 0, 0), material=HOLE, verts=20))
    # mounting screw between eyes and mouth
    kit.cyl(0.0022, 0.002, at=(x, yf - 0.0006, z - 0.002), rot=(90, 0, 0), material=METAL, verts=12, name='screw')
    return p


def usb(x, z, y_face, name='usb'):
    p = kit.box((0.026, 0.005, 0.032), at=(x, y_face - 0.0025, z), material=CREAM, bevel=0.003, segments=2, name=name)
    cut(p, kit.box((0.013, 0.02, 0.0048), at=(x, y_face - 0.005, z), material=HOLE))
    kit.box((0.010, 0.002, 0.0018), at=(x, y_face - 0.003, z - 0.0008), material=METAL, name='usbtongue')
    return p


# ---------------------------------------------------------------- tiers
BL, BD, BH = 0.40, 0.20, 0.14            # base
base = housing((BL, BD, BH), (0, 0, BH / 2), 'base')
T2 = (0.29, 0.10, 0.12); T2c = (-0.035, 0.045, BH + T2[2] / 2)
housing(T2, T2c, 'tier2')
T3 = (0.10, 0.075, 0.095); T3c = (-0.085, 0.055, BH + T2[2] + T3[2] / 2)
housing(T3, T3c, 'tier3')
T4 = (0.068, 0.062, 0.068); T4c = (-0.085, 0.058, BH + T2[2] + T3[2] + T4[2] / 2)
housing(T4, T4c, 'tier4')

# base front: two outlet faces on a dark panel, and a side panel of round sockets at the right end
yb = front_panel(-0.055, 0.075, 0.25, 0.10, -BD / 2, 'basepanel')
outlet(-0.118, 0.075, yb, s=0.062)
outlet(0.008, 0.075, yb, s=0.062)
ys = front_panel(0.145, 0.075, 0.075, 0.09, -BD / 2, 'sidepanel')
for z in (0.096, 0.054):
    kit.cyl(0.0125, 0.006, at=(0.145, ys - 0.002, z), rot=(90, 0, 0), material=METAL, verts=32, bevel=0.002,
            name='socketrim')
    kit.sphere(1, at=(0.145, ys - 0.0052, z), scale=(0.0098, 0.001, 0.0062), material=HOLE, segs=24, rings=8,
               name='socket')
kit.box((0.002, 0.003, 0.08), at=(0.104, -BD / 2 - 0.002, 0.075), material=PLATE, name='divider')

# tier 2 front: two USB ports
y2 = front_panel(T2c[0] + 0.03, T2c[2], 0.17, 0.06, T2c[1] - T2[1] / 2, 't2panel')
usb(T2c[0] - 0.02, T2c[2] - 0.008, y2)
usb(T2c[0] + 0.07, T2c[2] + 0.004, y2)
# tier 3 front: one more outlet face
y3 = front_panel(T3c[0], T3c[2], 0.082, 0.08, T3c[1] - T3[1] / 2, 't3panel')
outlet(T3c[0], T3c[2], y3, s=0.054)
# tier 4: flagpole socket on its front, the pole rising out of its top
y4 = T4c[1] - T4[1] / 2
kit.cyl(0.011, 0.005, at=(T4c[0], y4 - 0.002, T4c[2] - 0.004), rot=(90, 0, 0), material=METAL, verts=24, bevel=0.0015,
        name='button')
kit.cyl(0.0065, 0.004, at=(T4c[0], y4 - 0.004, T4c[2] - 0.004), rot=(90, 0, 0),
        material=kit.mat('amber', rough=0.3, emit=1.2, name='led'), verts=20, name='buttonlight')

# ---------------------------------------------------------------- flag "Don't step on me!"
top4 = T4c[2] + T4[2] / 2
PX, PY = T4c[0] - 0.012, T4c[1]
kit.cyl(0.012, 0.012, at=(PX, PY, top4 + 0.004), material=METAL, verts=24, bevel=0.003, name='polebase')
POLE_H = 0.34
kit.cyl(0.0042, POLE_H, at=(PX, PY, top4 + POLE_H / 2), material=BRASS, verts=16, name='pole')
kit.sphere(0.0085, at=(PX, PY, top4 + POLE_H + 0.004), material=BRASS, segs=16, rings=8, name='finial')
FW, FH = 0.19, 0.125
F_Z1 = top4 + POLE_H - 0.012
wave = lambda x: 0.010 * math.sin((x / FW) * math.pi * 1.6) * (x / FW) ** 0.8
nx, nz = 24, 6
verts = []; faces = []
for side in (-1, 1):
    for i in range(nx + 1):
        for j in range(nz + 1):
            x = i / nx * FW; z = F_Z1 - j / nz * FH
            verts.append((PX + 0.004 + x, PY + wave(x) + side * 0.0012, z))
off = (nx + 1) * (nz + 1)
for i in range(nx):
    for j in range(nz):
        a = i * (nz + 1) + j; b = a + (nz + 1)
        faces.append((a, a + 1, b + 1, b)); faces.append((off + a, off + b, off + b + 1, off + a + 1))
for i in range(nx):                                              # close the edges
    a = i * (nz + 1); b = (i + 1) * (nz + 1)
    faces.append((a, b, off + b, off + a))
    a2 = a + nz; b2 = b + nz
    faces.append((a2, off + a2, off + b2, b2))
for j in range(nz):
    faces.append((j, off + j, off + j + 1, j + 1))
    a = nx * (nz + 1) + j
    faces.append((a, a + 1, off + a + 1, off + a))
flag = mesh_obj('flag', verts, faces, [FLAG])
kit.finish(flag, None, smooth=50)
# hem rings at the pole
for z in (F_Z1 - 0.008, F_Z1 - FH + 0.008):
    kit.torus(0.0062, 0.0017, at=(PX, PY, z), material=METAL, major=16, minor=6, name='ring')
# the words, on both faces, following the flag's wave
for side in (-1, 1):
    t = text("Don't\nstep on\nme!", 0.040, FONTS + 'Bradley Hand Bold.ttf', INK, 0.0008, res=1)
    t.rotation_euler = (math.radians(90), 0, math.radians(0 if side < 0 else 180))
    t.location = (PX + 0.004 + FW / 2, PY, F_Z1 - FH / 2)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    for v in t.data.vertices:
        x = v.co.x - (PX + 0.004)
        v.co.y = PY + wave(x) + side * (0.0016) + (v.co.y - PY)
    t.data.update()

# ---------------------------------------------------------------- carry handle curled at the base's right corner
hx = BL / 2 - 0.04
for sy in (-1, 1):
    kit.cyl(0.011, 0.014, at=(hx, sy * 0.055, BH + 0.006), rot=(90, 0, 0), material=RUBBER, verts=20, bevel=0.003,
            name='handlepivot')
hpts = [(hx, -0.055, BH + 0.008), (hx + 0.012, -0.05, BH + 0.035), (hx + 0.03, -0.02, BH + 0.05),
        (hx + 0.03, 0.02, BH + 0.05), (hx + 0.012, 0.05, BH + 0.035), (hx, 0.055, BH + 0.008)]
rod(nurbs(hpts, 30), 0.0085, RUBBER, n=12, name='handle')

# ---------------------------------------------------------------- the cord and plug, off the left end
ex = -BL / 2
kit.cyl(0.016, 0.02, at=(ex - 0.008, -0.02, 0.05), rot=(0, 90, 0), material=RUBBER, verts=24, bevel=0.004,
        name='strainrelief')
cord_ctrl = [(ex - 0.015, -0.02, 0.05), (ex - 0.06, -0.03, 0.045), (ex - 0.10, -0.07, 0.012),
             (ex - 0.15, -0.14, 0.009), (ex - 0.19, -0.12, 0.009), (ex - 0.22, -0.18, 0.009), (ex - 0.25, -0.22, 0.011)]
cord_pts = nurbs(cord_ctrl, 48)
rod(cord_pts, 0.0072, CORD, n=10, name='cord')
end = Vector(cord_pts[-1]); prev = Vector(cord_pts[-4]); d = (end - prev); d.z = 0; d.normalize()
yaw = math.atan2(d.y, d.x)
R = Matrix.Translation(end) @ Matrix.Rotation(yaw, 4, 'Z')
plug = kit.box((0.05, 0.034, 0.024), at=(0, 0, 0), material=CORD, bevel=0.007, segments=3, name='plug')
plug.data.transform(R @ Matrix.Translation((0.03, 0, 0.001))); plug.data.update()
grip = kit.cyl(0.011, 0.016, at=(0, 0, 0), material=CORD, verts=20, bevel=0.003, name='plugboot')
grip.data.transform(R @ Matrix.Translation((0.002, 0, 0.0)) @ Matrix.Rotation(math.radians(90), 4, 'Y')); grip.data.update()
for dy, w in ((-0.0063, 0.0015), (0.0063, 0.0015)):
    b = kit.box((0.019, w, 0.0075), at=(0, 0, 0), material=METAL, bevel=0.0005, name='prong')
    b.data.transform(R @ Matrix.Translation((0.064, dy, 0.003))); b.data.update()
g = kit.cyl(0.0022, 0.022, at=(0, 0, 0), material=METAL, verts=12, name='groundpin')
g.data.transform(R @ Matrix.Translation((0.064, 0, -0.006)) @ Matrix.Rotation(math.radians(90), 4, 'Y')); g.data.update()

# ---------------------------------------------------------------- back: vent slots and the AC input; feet
for i in range(9):
    kit.box((0.006, 0.004, 0.07), at=(-0.12 + i * 0.016, BD / 2 + 0.0005, 0.07), material=HOLE, bevel=0.0015,
            name='vent')
kit.box((0.05, 0.005, 0.035), at=(0.12, BD / 2 + 0.001, 0.07), material=PLATE, bevel=0.003, name='acin')
kit.box((0.028, 0.006, 0.016), at=(0.12, BD / 2 + 0.003, 0.07), material=HOLE, bevel=0.002, name='acinhole')
for x in (-0.16, 0.16):
    for y in (-0.07, 0.07):
        kit.cyl(0.014, 0.004, at=(x, y, 0.0), material=RUBBER, verts=20, name='foot')

# lift everything onto z = 0 (feet stand on the floor; the plug and cord lie on it)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in objs:
    o.location.z += 0.002
kit.export('portable-power-station')
