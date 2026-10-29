"""Cast iron skillet, after Sid Chowdhury's drawing (RV P5a).

The drawing: a skillet seen face-on, a thick rim band, two pour spouts, a long handle with a slotted hang hole,
a slotted helper lug opposite, and a cast-in "USC / IYA" logo with a sound-wave mark raised on the cooking floor.
The mural paints it on a shelf with the logo reading upright and the handle off to the right, so that's the
presentation here: face to the front (tipped back a little), handle to the right, logo upright.
Back side (not in the drawing): plain cast bottom with a heat ring and an open channel under the handle.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
import bpy, bmesh
from mathutils import Vector, Matrix

kit.reset()
FONT = '/System/Library/Fonts/Supplemental/Arial Black.ttf'


# ---------------------------------------------------------------- helpers (local to this script)
def fillet(pts, r, n=4, closed=False):
    """Round the corners of a 2D polyline/polygon. r: radius (scalar or per-vertex list, 0 = sharp)."""
    m = len(pts); out = []
    for i, p in enumerate(pts):
        ri = r[i] if isinstance(r, (list, tuple)) else r
        if (not closed and i in (0, m - 1)) or not ri:
            out.append(p); continue
        P = Vector(p); A = Vector(pts[i - 1]); B = Vector(pts[(i + 1) % m])
        u = (A - P); v = (B - P); lu, lv = u.length, v.length
        u.normalize(); v.normalize()
        ang = u.angle(v, math.pi)
        if ang > math.pi - 1e-3:
            out.append(p); continue
        d = min(ri / math.tan(ang / 2), 0.48 * lu, 0.48 * lv)
        t1, t2 = P + u * d, P + v * d
        for k in range(n + 1):
            t = k / n
            q = t1 * (1 - t) ** 2 + P * 2 * (1 - t) * t + t2 * t * t
            out.append((q.x, q.y))
    return out


def ftext(s, size, depth, at=(0, 0, 0), rot=(0, 0, 0), material=None, bevel=0.0, align='CENTER', res=5, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.align_x = align; cu.align_y = 'CENTER'; cu.resolution_u = res
    if bevel:
        cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.offset = -bevel
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.location = at; o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def bake_join(name):
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o


def settle(o, rot=None):
    """Rotate (degrees, XYZ) about the origin, then stand the object on z=0 centred on x/y."""
    if rot:
        o.matrix_world = Matrix.Rotation(math.radians(rot[2]), 4, 'Z') @ Matrix.Rotation(math.radians(rot[1]), 4, 'Y') \
            @ Matrix.Rotation(math.radians(rot[0]), 4, 'X') @ o.matrix_world
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    off = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    o.data.transform(Matrix.Translation(off))
    return o


# ---------------------------------------------------------------- materials
IRON = kit.mat('#1f1d1b', rough=0.42, metal=0.8, name='seasoned_iron')
WORN = kit.mat('#6a6560', rough=0.32, metal=0.85, name='worn_iron')      # raised logo, polished by use

# Built lying flat (cooking side up, handle along +X), then stood up at the end.
R_RIM, H = 0.150, 0.053

# ---------------------------------------------------------------- body: one lathe, rim band, heat ring underneath
prof = [
    (0.0, 0.0025), (0.104, 0.0025), (0.106, 0.0), (0.116, 0.0), (0.118, 0.0025),  # heat ring
    (0.123, 0.0025), (0.127, 0.008),                                             # outer foot corner
    (0.146, 0.046), (0.151, 0.050), (0.151, H),                                  # outer wall up to the rim lip
    (0.143, H), (0.141, 0.049),                                                  # rim band (flat top)
    (0.121, 0.0085), (0.113, 0.0062), (0.0, 0.0062),                             # inner wall, floor
]
rad = [0, 0, 0.0015, 0.0015, 0, 0, 0.006, 0.004, 0.002, 0.0015, 0.0015, 0.002, 0.006, 0, 0]
body = kit.lathe(fillet(prof, rad, n=3), material=IRON, steps=144, name='skillet')

# pour spouts at +-Y: push the upper wall out and dip the rim, with a flat-faced lip like the drawing
bm = bmesh.new(); bm.from_mesh(body.data)
for v in bm.verts:
    x, y, z = v.co
    r = math.hypot(x, y)
    if r < 0.12 or z < 0.02:
        continue
    phi = math.atan2(y, x)
    for sp in (math.pi / 2, -math.pi / 2):
        d = abs((phi - sp + math.pi) % math.tau - math.pi)
        w = 0.24
        if d < w:
            f = (1 - (d / w) ** 2) ** 1.5
            h = ((z - 0.02) / (H - 0.02)) ** 1.6
            nr = r + 0.013 * f * h
            v.co.x, v.co.y = x / r * nr, y / r * nr
            v.co.z = z - 0.0035 * f * h
bm.to_mesh(body.data); bm.free()

# ---------------------------------------------------------------- the cast logo on the cooking floor
FLOOR = 0.0062
RELIEF = 0.0028
usc = ftext('USC', 0.085, RELIEF * 2, at=(0, 0.010, FLOOR), material=WORN, bevel=0.0007, name='usc')
iya = ftext('IYA', 0.068, RELIEF * 2, at=(0.003, -0.058, FLOOR), material=WORN, bevel=0.0007, name='iya')
# the sound-wave mark above USC: nine bars, tallest in the middle
heights = [0.006, 0.011, 0.017, 0.024, 0.032, 0.024, 0.017, 0.011, 0.006]
for i, hgt in enumerate(heights):
    x = (i - 4) * 0.0094
    kit.box((0.0054, hgt, RELIEF * 2), at=(x, 0.073, FLOOR), material=WORN, bevel=0.0008, name='wave')

# ---------------------------------------------------------------- main handle with hang hole and open channel underneath
L = 0.178                     # beyond the rim
outline = [(0.0, -0.0165), (L - 0.02, -0.0135), (L - 0.004, -0.017), (L + 0.012, -0.012), (L + 0.016, 0.0),
           (L + 0.012, 0.012), (L - 0.004, 0.017), (L - 0.02, 0.0135), (0.0, 0.0165)]
outline = fillet(outline, [0, 0.01, 0.006, 0.01, 0.01, 0.01, 0.006, 0.01, 0], n=4, closed=True)
T = 0.0105
handle = kit.extrude(outline, T, material=IRON, name='handle')
slot = kit.extrude(fillet([(-0.014, -0.0055), (0.014, -0.0055), (0.014, 0.0055), (-0.014, 0.0055)], 0.0054, n=4, closed=True),
                   0.05, at=(L - 0.006, 0, -0.02), name='slot')
kit.boolean(handle, slot)
# channel under the handle (cast iron handles are U-section)
chan = kit.extrude(fillet([(0.012, -0.0105), (L - 0.03, -0.008), (L - 0.03, 0.008), (0.012, 0.0105)], 0.004, n=3, closed=True),
                   0.006, at=(0, 0, -0.001), name='chan')
kit.boolean(handle, chan)
kit.finish(handle, bevel=0.0018, segments=2)
handle.location = (0.1425, 0, H - T + 0.0005)
handle.rotation_euler = (0, math.radians(-7), 0)

# cast web under the handle root, blending it into the wall
def r_mid(z):   # middle of the wall's thickness at height z
    ro = 0.127 + (z - 0.008) / (0.046 - 0.008) * (0.146 - 0.127)
    ri = 0.121 + (z - 0.0085) / (0.049 - 0.0085) * (0.141 - 0.121)
    return (ro + ri) / 2
zt, zb = H - T + 0.0015, 0.024
web = kit.extrude(fillet([(r_mid(zt), zt), (0.176, zt), (r_mid(zb), zb)], [0, 0.006, 0], n=4, closed=True), 0.014,
                  rot=(90, 0, 0), material=IRON, name='web')
web.location = (0, 0.007, 0)
for v in web.data.vertices:      # taper the web to a fin as it runs down the wall
    t = max(0.0, min(1.0, (zt - v.co.y) / (zt - zb)))
    v.co.z = 0.007 + (v.co.z - 0.007) * (1 - 0.55 * t)
kit.finish(web, bevel=0.0028, segments=3)

# ---------------------------------------------------------------- helper lug opposite the handle
lug_o = [(0.0, -0.034), (0.040, -0.024), (0.050, -0.012), (0.050, 0.012), (0.040, 0.024), (0.0, 0.034)]
lug_o = fillet(lug_o, [0, 0.01, 0.008, 0.008, 0.01, 0], n=4, closed=True)
lug = kit.extrude([(-x, y) for x, y in reversed(lug_o)], 0.0085, material=IRON, name='lug')
lug_hole = kit.extrude(fillet([(-0.0075, -0.017), (0.0075, -0.017), (0.0075, 0.017), (-0.0075, 0.017)], 0.006, n=4, closed=True),
                       0.05, at=(-0.034, 0, -0.02), name='lughole')
kit.boolean(lug, lug_hole)
kit.finish(lug, bevel=0.0018)
lug.location = (-0.1425, 0, H - 0.0085 - 0.0015)
lug.rotation_euler = (0, math.radians(5), 0)

# ---------------------------------------------------------------- stand it up: cooking side to the front, tipped back 14 degrees
pan = bake_join('pan')
settle(pan, rot=(76, 0, 0))
kit.export('pan')
