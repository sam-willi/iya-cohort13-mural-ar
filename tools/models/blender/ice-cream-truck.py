"""Ice cream truck - Isabel Rosse (Cohort 13).

Her drawing: the truck *is* an ice cream cone on its side. The waffle cone (ringed and ruled) is the
tail, a big scoop is the body with a dark serving window in its side, a smaller scoop in front is the
cab (door with a handle, a windshield with the steering wheel showing through), a round ball is the
nose, an "ICE CREAM" sign stands on top, and it rolls on small wheels with cross hubcaps.
Ballpoint only, so the flavours are mine: strawberry body, vanilla cab, cherry nose, honey waffle.
Nose points +X; the serving-window side faces the front (-Y), as in her view.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, bmesh, math
from mathutils import Vector, Matrix

kit.reset()


# ---------------------------------------------------------------- local helpers
def framed_check(obj_id, res=520):
    """kit.check_render frames at 3.2x the bounding radius with a 70 mm lens, which crops tall or long
    objects. Pad the bounds with a vertex-only (invisible) mesh first; the GLB is already written."""
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
    hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
    ctr, half = (lo + hi) / 2, (hi - lo) / 2
    k = max(half) / (0.8 * half.length) * 1.08
    if k > 1:
        me = bpy.data.meshes.new('frame_pad'); me.from_pydata([tuple(ctr - half * k), tuple(ctr + half * k)], [], [])
        bpy.context.collection.objects.link(bpy.data.objects.new('frame_pad', me))
    _kit_check(obj_id, res)


_kit_check = kit.check_render
kit.check_render = framed_check


def boolean(target, cutter, op='DIFFERENCE'):
    """Like kit.boolean, but cut faces take the cutter's material."""
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op; md.object = cutter
    md.solver = 'EXACT'; md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def grid_mesh(fn, nu, nv, name, material, close_u=False, close_v=True):
    """Mesh from a parametric surface fn(u, v) -> (x, y, z), u in [0,1], v in [0,1)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = [[bm.verts.new(fn(i / nu, j / nv)) for j in range(nv)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv if close_v else nv - 1):
            bm.faces.new((rows[i][j], rows[i][(j + 1) % nv], rows[i + 1][(j + 1) % nv], rows[i + 1][j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    holes = [e for e in bm.edges if e.is_boundary]
    if holes:
        bmesh.ops.holes_fill(bm, edges=holes)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return kit.finish(o, material)


def ellipsoid(c, r, material, name, segs=64, rings=32):
    return kit.sphere(1.0, at=c, scale=r, material=material, segs=segs, rings=rings, name=name)


waffle = kit.mat('honey', rough=0.62, name='waffle')
strawberry = kit.mat('#e8a29a', rough=0.5, name='strawberry')
vanilla = kit.mat('cream', rough=0.5, name='vanilla')
cherry = kit.mat('#b3241e', rough=0.2, name='cherry')
dark = kit.mat('#2a1c18', rough=0.6, name='inside_dark')
glass = kit.mat('glass', rough=0.05, alpha=0.22, name='windshield')
cabin = kit.mat('#a87a52', rough=0.7, name='cabin')
chrome = kit.mat('chrome', rough=0.2, metal=0.85, name='chrome')
tyre = kit.mat('rubber', rough=0.85, name='tyre')
sign_c = kit.mat('paper', rough=0.5, name='sign')
sign_red = kit.mat('red', rough=0.4, name='sign_red')
black = kit.mat('black', rough=0.5, name='black')
amber = kit.mat('amber', rough=0.3, emit=0.5, name='lamp')

AZ = 0.22                    # height of the cone's axis
TIP_X, RIM_X, RIM_R = -0.64, -0.17, 0.19

# ---------------------------------------------------------------- the waffle cone (tail): ruled and ringed, as drawn


def cone_fn(u, v):
    x = TIP_X + (RIM_X - TIP_X) * u
    r = RIM_R * u
    a = math.tau * v
    # grooves: rings along the cone and lines running to the tip
    ring = abs(math.sin(math.pi * 9 * u))
    line = abs(math.sin(math.pi * 18 * v))
    g = min(ring / 0.22, line / 0.22, 1.0)
    r = max(r - 0.004 * (1 - g) ** 1.5 * min(1.0, u * 6), 0.0)
    return (x, r * math.cos(a), AZ + r * math.sin(a))


cone = grid_mesh(cone_fn, 60, 108, 'cone', waffle)
# rolled lip at the open end
kit.torus(RIM_R - 0.004, 0.012, at=(RIM_X - 0.004, 0, AZ), rot=(0, 90, 0), material=waffle, major=96, minor=12, name='cone_lip')

# ---------------------------------------------------------------- the scoops: strawberry body, vanilla cab, cherry nose
BC, BR = Vector((-0.09, 0, AZ + 0.005)), Vector((0.225, 0.2, 0.2))
body = ellipsoid(BC, BR, strawberry, 'body_scoop')
# melty ruffle where the scoop sits in the cone's mouth


def ruffle_fn(u, v):
    a = math.tau * v
    wob = 0.012 * math.sin(11 * a) + 0.006 * math.sin(5 * a + 1.3)
    R = RIM_R + 0.012 + 0.004 * math.sin(11 * a)
    t = math.tau * u
    return (RIM_X + 0.018 + 0.016 * math.cos(t) - abs(wob) * 0.6, (R + 0.014 * math.sin(t)) * math.cos(a), AZ + (R + 0.014 * math.sin(t)) * math.sin(a))


grid_mesh(ruffle_fn, 12, 132, 'ruffle', strawberry, close_u=True)

CAB = Vector((0.205, 0, 0.18)); CAB_R = 0.15
cab = ellipsoid(CAB, (CAB_R, CAB_R * 0.97, CAB_R), vanilla, 'cab_scoop')
NOSE = Vector((0.375, 0, 0.11))
nose = ellipsoid(NOSE, (0.095, 0.095, 0.093), cherry, 'nose_cherry', segs=48, rings=24)

# ---------------------------------------------------------------- serving window in the body's side (dark, as she shaded it)
WX, WZ, WW_, WH = -0.075, AZ + 0.05, 0.17, 0.095


def on_body(x, z, off=0.0):
    """Point on the front (-Y) surface of the body scoop at (x, z)."""
    q = 1 - ((x - BC.x) / BR.x) ** 2 - ((z - BC.z) / BR.z) ** 2
    return Vector((x, -BR.y * math.sqrt(max(q, 0.0)) - off, z))


win = kit.box((WW_, 0.3, WH), at=(WX, -0.15, WZ), material=dark, name='cut')
boolean(win, ellipsoid(BC, BR - Vector((0.03, 0.03, 0.03)), dark, 'inner'))
boolean(body, win)
# chrome frame following the scoop's curve, a sill and a striped awning over it
outline = []
for k in range(16):
    outline.append((WX - WW_ / 2 + WW_ * k / 16, WZ + WH / 2))
for k in range(16):
    outline.append((WX + WW_ / 2, WZ + WH / 2 - WH * k / 16))
for k in range(16):
    outline.append((WX + WW_ / 2 - WW_ * k / 16, WZ - WH / 2))
for k in range(16):
    outline.append((WX - WW_ / 2, WZ - WH / 2 + WH * k / 16))
pts = [tuple(on_body(x, z, -0.001)) for x, z in outline]
cu = bpy.data.curves.new('win_frame', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
for p, c in zip(sp.points, pts):
    p.co = (*c, 1)
sp.use_cyclic_u = True; cu.bevel_depth = 0.006; cu.bevel_resolution = 1
ob = bpy.data.objects.new('win_frame', cu); bpy.context.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.convert(target='MESH'); kit.finish(bpy.context.object, chrome)
yw = on_body(WX, WZ).y
yb = on_body(WX, WZ - WH / 2).y
kit.box((WW_ + 0.02, 0.07, 0.01), at=(WX, yb + 0.012, WZ - WH / 2 - 0.008), material=chrome, bevel=0.003, name='sill')
yt = on_body(WX, WZ + WH / 2 + 0.012).y
aw = kit.extrude([(-0.105, -0.03), (0.105, -0.03), (0.1, 0.055), (-0.1, 0.055)], 0.006, at=(WX, yt + 0.02, WZ + WH / 2 + 0.014),
                 rot=(-28, 0, 0), material=sign_red, bevel=0.002, name='awning')
lip = aw.matrix_world @ Vector((0, 0.055, 0))
for k in range(7):
    x = WX - 0.09 + k * 0.03
    kit.sphere(0.0125, at=(x, lip.y + 0.004, lip.z - 0.006), scale=(1, 0.35, 0.8), material=sign_red if k % 2 else vanilla,
               segs=16, rings=8, name='scallop')
# warm light inside the window
kit.box((WW_ - 0.02, 0.01, WH - 0.02), at=(WX, yw + 0.023, WZ), material=amber, name='window_glow')

# ---------------------------------------------------------------- cab: door with handle, windshield with the wheel inside
for sy in (-1, 1):            # a door on each side (her view shows the right-hand one)
    door = kit.box((0.09, 0.3, 0.125), at=(0.19, sy * 0.15, 0.172), rot=(0, -8, 0), material=dark, name='cut')
    door_in = kit.box((0.082, 0.32, 0.117), at=(0.19, sy * 0.15, 0.172), rot=(0, -8, 0), name='door_in')
    boolean(door, door_in)
    boolean(door, ellipsoid(CAB, (CAB_R - 0.003, CAB_R * 0.97 - 0.003, CAB_R - 0.003), dark, 'inner'))
    boolean(cab, door)
    hp = Vector((0.218, 0, 0.165))
    hp.y = sy * math.sqrt(CAB_R ** 2 * 0.97 ** 2 * (1 - ((hp.x - CAB.x) / CAB_R) ** 2 - ((hp.z - CAB.z) / CAB_R) ** 2))
    kit.sphere(0.0075, at=hp + Vector((0, sy * 0.003, 0)), material=chrome, segs=16, rings=8, name='door_handle')
    kit.box((0.022, 0.006, 0.006), at=hp + Vector((-0.01, sy * 0.004, 0)), material=chrome, bevel=0.002, name='door_handle_bar')

# windshield: a rounded opening on the front-top of the cab facing forward
ws_poly = []
for k in range(40):
    a = math.tau * k / 40
    ws_poly.append((0.08 * math.cos(a) * (1 + 0.15 * math.sin(a)), 0.046 * math.sin(a) + 0.008 * math.cos(2 * a)))
ws = kit.extrude(ws_poly, 0.3, at=(CAB.x, 0, CAB.z + 0.062), rot=(90, 0, 90), material=cabin, name='cut')
boolean(ws, ellipsoid(CAB, (CAB_R - 0.04, CAB_R * 0.97 - 0.04, CAB_R - 0.04), cabin, 'inner'))
boolean(cab, ws)
# steering wheel and a little dial, seen through the glass
sw_c = Vector((CAB.x + 0.118, -0.028, CAB.z + 0.045))
kit.torus(0.022, 0.0035, at=sw_c, rot=(0, 70, 0), material=black, major=32, minor=8, name='steering_wheel')
for k in range(3):
    a = math.radians(90 + 120 * k)
    d = Matrix.Rotation(math.radians(70), 3, 'Y') @ Vector((math.cos(a), math.sin(a), 0))
    kit.tube([tuple(sw_c), tuple(sw_c + d * 0.022)], 0.0022, material=black, name='spoke')
kit.cyl(0.008, 0.06, at=sw_c - Matrix.Rotation(math.radians(70), 3, 'Y') @ Vector((0, 0, 0.03)), rot=(0, 70, 0),
        material=black, verts=12, name='column')
kit.cyl(0.012, 0.006, at=(CAB.x + 0.113, 0.032, CAB.z + 0.035), rot=(0, 70, 0), material=chrome, verts=20, name='dial')
# the glass: a curved pane following the cab
pane = kit.extrude(ws_poly, 0.3, at=(CAB.x, 0, CAB.z + 0.062), rot=(90, 0, 90), material=glass, name='pane')
boolean(pane, ellipsoid(CAB, (CAB_R - 0.004, CAB_R * 0.97 - 0.004, CAB_R - 0.004), glass, 'outer'), op='INTERSECT')
boolean(pane, ellipsoid(CAB, (CAB_R - 0.008, CAB_R * 0.97 - 0.008, CAB_R - 0.008), glass, 'inner'))
# chrome surround on the windshield
ring = []
for x2, z2 in ws_poly + ws_poly[:1]:
    y = x2; z = CAB.z + 0.062 + z2
    xx = CAB.x + math.sqrt(max(0.0, CAB_R ** 2 - (y / 0.97) ** 2 - (z - CAB.z) ** 2)) + 0.001
    ring.append((xx, y, z))
cu = bpy.data.curves.new('ws_ring', 'CURVE'); cu.dimensions = '3D'
sp = cu.splines.new('POLY'); sp.points.add(len(ring) - 1)
for p, c in zip(sp.points, ring):
    p.co = (*c, 1)
cu.bevel_depth = 0.004; cu.bevel_resolution = 1
ob = bpy.data.objects.new('ws_ring', cu); bpy.context.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.convert(target='MESH'); kit.finish(bpy.context.object, chrome)

# headlamp glints on the cherry nose, and tail lights on the cone
for sy in (-1, 1):
    kit.sphere(0.012, at=(NOSE.x + 0.06, sy * 0.045, NOSE.z + 0.02), scale=(0.5, 1, 1), material=amber, segs=16, rings=8, name='headlamp')

# ---------------------------------------------------------------- wheels with cross hubcaps, in arches
WR, WW = 0.06, 0.042
for wx, wy in ((-0.29, 0.098), (0.205, 0.1)):
    for sy in (-1, 1):
        arch = kit.cyl(WR + 0.012, WW + 0.03, at=(wx, sy * wy, WR), rot=(90, 0, 0), material=dark, verts=40, name='cut')
        tgt = cone if wx < 0 else cab
        boolean(tgt, arch)
        if wx > 0:
            arch = kit.cyl(WR + 0.012, WW + 0.03, at=(wx, sy * wy, WR), rot=(90, 0, 0), material=dark, verts=40, name='cut')
            boolean(body, arch)
        tire = kit.lathe([(0.028, -WW / 2 + 0.004), (0.045, -WW / 2), (WR - 0.006, -WW / 2), (WR, -WW / 2 + 0.008),
                          (WR, WW / 2 - 0.008), (WR - 0.006, WW / 2), (0.045, WW / 2), (0.028, WW / 2 - 0.004), (0.028, -WW / 2 + 0.004)],
                         material=tyre, steps=48, name='tyre')
        tire.data.polygons.foreach_set('use_smooth', [True] * len(tire.data.polygons))
        tire.rotation_euler = (math.radians(90), 0, 0); tire.location = (wx, sy * wy, WR)
        # tread blocks
        for k in range(24):
            a = math.tau * k / 24
            kit.box((0.008, WW - 0.01, 0.004), at=(wx + (WR - 0.0022) * math.cos(a), sy * wy, WR + (WR - 0.0022) * math.sin(a)),
                    rot=(0, -math.degrees(a) + 90, 0), material=tyre, name='tread')
        hub = kit.lathe([(0, 0), (0.036, 0), (0.036, 0.006), (0.03, 0.012), (0, 0.014)], material=chrome, steps=40, name='hubcap')
        hub.rotation_euler = (math.radians(-90 * sy), 0, 0); hub.location = (wx, sy * (wy + WW / 2 - 0.008), WR)
        # the cross she drew on each hubcap
        for rz in (45, -45):
            b = kit.box((0.05, 0.006, 0.008), at=(wx, sy * (wy + WW / 2 + 0.006), WR), rot=(0, rz, 0), material=black, bevel=0.002, name='hub_cross')
        kit.cyl(0.008, 0.008, at=(wx, sy * (wy + WW / 2 + 0.008), WR), rot=(90, 0, 0), material=chrome, verts=16, name='hub_nut')

# ---------------------------------------------------------------- "ICE CREAM" sign on top
sx_ = -0.12
top_z = BC.z + BR.z * math.sqrt(1 - ((sx_ - BC.x) / BR.x) ** 2) - 0.004
kit.cyl(0.0045, 0.06, at=(sx_, 0, top_z + 0.02), material=chrome, verts=12, name='sign_post')
board = kit.box((0.17, 0.014, 0.055), at=(sx_, 0, top_z + 0.075), material=sign_c, bevel=0.004, name='sign_board')
kit.box((0.176, 0.016, 0.006), at=(sx_, 0, top_z + 0.075 + 0.0275), material=sign_red, bevel=0.002, name='sign_trim')
kit.box((0.176, 0.016, 0.006), at=(sx_, 0, top_z + 0.075 - 0.0275), material=sign_red, bevel=0.002, name='sign_trim')
for side in (-1, 1):
    t = kit.text('ICE CREAM', 0.033, 0.003, at=(sx_, side * 0.0075, top_z + 0.074), rot=(90, 0, 0 if side < 0 else 180),
                 material=sign_red, name='sign_text')

kit.export('ice-cream-truck')
