"""Air purifier, after Manya Singh's drawing (RV P5a).

The drawing: an upright box with softly rounded edges on a thin inset base; a stepped, recessed control panel on
top with a row of five round buttons; the Clorox diamond badge near the top of the front with a short vertical
indicator line under it; and horizontal louvres across the lower two thirds of the front.
Line-only drawing, so colours are a call: warm white plastic, a dark grey grille behind the louvres and control
panel, the badge in the brand's blue pulled toward the mural's teal, a soft blue indicator glow. The back and sides
aren't drawn: a slotted filter cover and power socket on the back, finger grips on the sides.
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


def rrect(w, h, r, n=5):
    return fillet([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], r, n=n, closed=True)


def ftext(s, size, depth, material=None, bevel=0.0, res=4, name='text'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.resolution_u = res
    if bevel:
        cu.bevel_depth = bevel; cu.bevel_resolution = 1; cu.offset = -bevel
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def bake_join(name, objs=None):
    objs = objs or [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    o = bpy.context.object; o.name = name
    return o


def settle(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    vs = [v.co for v in o.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    o.data.transform(Matrix.Translation(Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))))
    return o


# ---------------------------------------------------------------- materials
SHELL = kit.mat('#efebe2', rough=0.42, name='shell')
GRILLE = kit.mat('#3a3d42', rough=0.55, name='grille_back')
PANEL = kit.mat('#2c2e33', rough=0.25, name='panel')
BASE = kit.mat('#8e8a84', rough=0.5, name='base')
BUTTON = kit.mat('#d9d5cc', rough=0.4, name='button')
BADGE = kit.mat('#1f6f9c', rough=0.35, name='badge')
BADGE_TXT = kit.mat('white', rough=0.4, name='badge_text')
GLOW = kit.mat('#8fd0f0', rough=0.3, emit=1.5, name='indicator')
POWER = kit.mat('amber', rough=0.3, emit=1.0, name='power_ring')
RUBBER = kit.mat('rubber', rough=0.8, name='rubber')

W, D, H = 0.355, 0.170, 0.560
B = 0.016                     # base height
R = 0.024                     # vertical edge radius
FY = -D / 2                   # front face

# ---------------------------------------------------------------- body, inset base, feet
body = kit.extrude(rrect(W, D, R, n=6), H - B, at=(0, 0, B), material=SHELL, name='body')
# stepped control recess on top
kit.boolean(body, kit.extrude(rrect(W - 0.040, D - 0.040, 0.016, n=5), 0.05, at=(0, 0, H - 0.004), name='step1'))
kit.boolean(body, kit.extrude(rrect(W - 0.064, D - 0.064, 0.010, n=5), 0.05, at=(0, 0, H - 0.010), name='step2'))
# louvre recess on the front, filter-cover recess on the back, finger grips on the sides
GX0, GX1, GZ0, GZ1 = -W / 2 + 0.022, W / 2 - 0.022, 0.050, 0.385
kit.boolean(body, kit.box((GX1 - GX0, 0.030, GZ1 - GZ0), at=(0, FY, (GZ0 + GZ1) / 2), name='grillecut'))
kit.boolean(body, kit.box((W - 0.060, 0.024, 0.38), at=(0, -FY, 0.26), name='backcut'))
for sx in (-1, 1):
    g = kit.extrude(rrect(0.026, 0.090, 0.012, n=4), 0.04, at=(W / 2 - 0.012 if sx > 0 else -W / 2 - 0.028, 0, H - 0.075), rot=(0, 90, 0), name='grip')
    kit.boolean(body, g)
kit.finish(body, bevel=0.0035, segments=2)
kit.extrude(rrect(W - 0.014, D - 0.014, R - 0.007, n=6), B + 0.002, at=(0, 0, 0.0), material=BASE, bevel=0.002, name='base')
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cyl(0.010, 0.003, at=(sx * (W / 2 - 0.035), sy * (D / 2 - 0.030), 0.0015), material=RUBBER, verts=16, name='foot')

# ---------------------------------------------------------------- control panel and five buttons
kit.extrude(rrect(W - 0.068, D - 0.068, 0.008, n=5), 0.003, at=(0, 0, H - 0.010), material=PANEL, bevel=0.001, name='panel')
PZ = H - 0.007
for i in range(5):
    x = -0.090 + i * 0.045
    y = -0.012
    kit.lathe(fillet([(0, 0), (0.0085, 0), (0.0085, 0.0025), (0.0070, 0.0040), (0, 0.0042)], [0, 0, 0.001, 0.001, 0], n=2),
              at=(x, y, PZ), material=BUTTON, steps=24, name='button')
    if i == 4:
        kit.torus(0.0098, 0.0012, at=(x, y, PZ + 0.0004), material=POWER, major=24, minor=6, name='powerring')
    # a tiny indicator dot above each button
    kit.cyl(0.0016, 0.0008, at=(x, y + 0.019, PZ + 0.0002), material=GLOW if i < 4 else POWER, verts=8, name='dot')

# ---------------------------------------------------------------- front louvres over a dark backing
kit.box((GX1 - GX0 + 0.002, 0.004, GZ1 - GZ0 + 0.002), at=(0, FY + 0.013, (GZ0 + GZ1) / 2), material=GRILLE, name='backing')
n = 26
pitch = (GZ1 - GZ0) / n
for k in range(n):
    z = GZ0 + pitch * (k + 0.5)
    sl = kit.box((GX1 - GX0 - 0.002, 0.012, pitch * 0.55), at=(0, FY + 0.006, z), material=SHELL, bevel=0.0012, name='louvre')
    sl.rotation_euler = (math.radians(-22), 0, 0)
for sx in (-1, 1):            # the louvres' side rails
    kit.box((0.004, 0.012, GZ1 - GZ0), at=(sx * ((GX1 - GX0) / 2 - 0.001), FY + 0.006, (GZ0 + GZ1) / 2), material=SHELL, name='rail')

# ---------------------------------------------------------------- badge and indicator line
diamond = [(0.0, -0.026), (0.062, 0.0), (0.0, 0.026), (-0.062, 0.0)]
badge = kit.extrude(fillet(diamond, 0.004, n=3, closed=True), 0.0025, rot=(90, 0, 0), material=BADGE, bevel=0.0008, name='badge')
badge.location = (0.0, FY + 0.0005, 0.478)
kit.extrude(fillet([(0.0, -0.022), (0.054, 0.0), (0.0, 0.022), (-0.054, 0.0)], 0.003, n=3, closed=True), 0.0008, rot=(90, 0, 0),
            material=BADGE_TXT, name='badgeline').location = (0.0, FY - 0.0018, 0.478)
kit.extrude(fillet([(0.0, -0.0205), (0.051, 0.0), (0.0, 0.0205), (-0.051, 0.0)], 0.003, n=3, closed=True), 0.0010, rot=(90, 0, 0),
            material=BADGE, name='badgeinner').location = (0.0, FY - 0.0019, 0.478)
t = ftext('CLOROX', 0.0105 / 0.515, 0.0012, material=BADGE_TXT, res=3, name='clorox')
t.matrix_world = Matrix.Translation((0.0, FY - 0.0026, 0.4788)) @ Matrix.Rotation(math.radians(90), 4, 'X')
kit.box((0.0040, 0.002, 0.040), at=(0.0, FY - 0.0002, 0.420), material=GLOW, bevel=0.0009, name='indicator')

# ---------------------------------------------------------------- back: slotted filter cover, power socket
kit.box((W - 0.060, 0.004, 0.38), at=(0, -FY - 0.010, 0.26), material=GRILLE, name='backbacking')
NB = 15                       # vertical slats on the filter door, so the back doesn't read as a second front
for k in range(NB):
    x = -(W - 0.064) / 2 + (W - 0.064) * (k + 0.5) / NB
    kit.box(((W - 0.064) / NB * 0.5, 0.010, 0.376), at=(x, -FY - 0.006, 0.26), material=SHELL, bevel=0.0012, name='backslat')
kit.box((W - 0.062, 0.010, 0.012), at=(0, -FY - 0.006, 0.26 + 0.188 - 0.006), material=SHELL, bevel=0.0012, name='backframe')
kit.box((W - 0.062, 0.010, 0.012), at=(0, -FY - 0.006, 0.26 - 0.188 + 0.006), material=SHELL, bevel=0.0012, name='backframe')
kit.box((0.040, 0.006, 0.010), at=(0, -FY - 0.001, 0.26 + 0.170), material=PANEL, bevel=0.002, name='latch')
kit.box((0.030, 0.004, 0.020), at=(0.09, -FY + 0.001, 0.035), material=PANEL, bevel=0.002, name='socket')
for dx in (-0.006, 0.006):
    kit.box((0.002, 0.004, 0.007), at=(0.09 + dx, -FY + 0.002, 0.035), material=RUBBER, name='pin')

# ---------------------------------------------------------------- join, settle, export
ap = bake_join('air_purifier')
settle(ap)
kit.export('air-purifier')
