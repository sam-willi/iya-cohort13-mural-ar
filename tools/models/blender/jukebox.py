"""Jukebox - Emma Xiao (Cohort 13).

Her drawing: a tall cabinet with a barrel-arched crown, round pillars on the two front corners
with capped tops and round feet, "30" on the arch face and "IYA" on a band below it, a tall
round-bottomed window holding a diamond lattice, and horizontal trim lines along the side.
Line-only, so the materials are a classic walnut-and-chrome jukebox in the mural's ambers.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import bpy, math
from mathutils import Vector

kit.reset()


# ---------------------------------------------------------------- local helpers
def ptube(points, r, material=None, res=2, closed=False, name='tube'):
    """Round tube through 3D points with straight segments (pass dense points for curves). res 2 = 8 sides."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*c, 1)
    sp.use_cyclic_u = closed
    cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    return kit.finish(bpy.context.object, material)


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


def arch(hw, z0, rise, n=48, cx=0.0):
    """Half-ellipse from (+hw, z0) over the top to (-hw, z0), as XZ points."""
    return [(cx + hw * math.cos(math.pi * i / n), z0 + rise * math.sin(math.pi * i / n)) for i in range(n + 1)]


def slab_xz(poly, y_front, depth, material=None, bevel=0.0, segments=2, name='slab'):
    """Extrude an XZ outline from y_front backwards (+Y) by depth."""
    return kit.extrude(poly, depth, at=(0, y_front + depth, 0), rot=(90, 0, 0),
                       material=material, bevel=bevel, segments=segments, name=name)


def u_shape(hw, z_top, z_bot, n=24):
    """Tall window outline with a round bottom (radius hw) and flat top, as XZ points."""
    zc = z_bot + hw
    pts = [(hw, z_top), (-hw, z_top)]
    for i in range(n + 1):
        a = math.pi + math.pi * i / n          # left -> bottom -> right
        pts.append((hw * math.cos(a), zc + hw * math.sin(a)))
    return pts


def flat_bar(p0, p1, w, t, material, name='bar'):
    """A flat strip from p0 to p1 lying in the XZ plane (thickness t along Y)."""
    a, b = Vector(p0), Vector(p1); d = b - a
    o = kit.box((d.length, t, w), at=(a + b) / 2, material=material, bevel=min(w, t) * 0.3, name=name)
    o.rotation_euler = (0, -math.atan2(d.z, d.x), 0)
    return o


# ---------------------------------------------------------------- dimensions (metres)
W = 0.80            # full width
D = 0.40            # depth
SH = 1.19           # shoulder: where the crown arch springs
RISE = 0.35         # crown rise above the shoulder
YF = -D / 2         # front face
PR = 0.066          # pillar radius
PX = W / 2 - PR + 0.012   # pillar centre x (pillars stand proud of the corners)
PY = YF + 0.03      # pillar centre y (partly sunk into the cabinet corner)

wood = kit.mat('#4e301b', rough=0.38, name='walnut')
wood_lt = kit.mat('#6a4428', rough=0.5, name='walnut_back')
chrome = kit.mat('chrome', rough=0.2, metal=0.85, name='chrome')
brass = kit.mat('brass', rough=0.3, metal=0.85, name='brass')
amber_glow = kit.mat('#f0b24a', rough=0.3, emit=0.35, name='amber_glow')
pillar_glow = kit.mat('#d8682a', rough=0.25, emit=0.3, name='pillar_glow')
cloth = kit.mat('#6a1a15', rough=0.92, name='speaker_cloth')
band_red = kit.mat('cardinal', rough=0.4, name='band_red')
cream = kit.mat('cream', rough=0.35, name='cream')
black = kit.mat('black', rough=0.6, name='black')
rubber = kit.mat('rubber', rough=0.8, name='rubber')
dark = kit.mat('#24160d', rough=0.7, name='dark_wood')

# ---------------------------------------------------------------- cabinet (body + crown in one piece)
outline = [(W / 2 - 0.004, 0.05)] + arch(W / 2 - 0.004, SH, RISE) + [(-W / 2 + 0.004, 0.05)]
cab = slab_xz(outline, YF, D, material=wood, bevel=0.012, segments=3, name='cabinet')

panel_hw, panel_z0, panel_rise = 0.262, 1.09, 0.345       # arched light panel in the crown face
win_hw, win_top, win_bot = 0.205, 0.975, 0.165             # tall round-bottomed window
panel = [(panel_hw, panel_z0)] + arch(panel_hw, panel_z0, panel_rise)[1:-1] + [(-panel_hw, panel_z0)]
back = [(0.27, 0.16), (0.27, 1.05)] + arch(0.27, 1.05, 0.3)[1:-1] + [(-0.27, 1.05), (-0.27, 0.16)]
kit.boolean(cab, slab_xz(panel, YF - 0.05, 0.05 + 0.028, name='cut'))
kit.boolean(cab, slab_xz(u_shape(win_hw, win_top, win_bot), YF - 0.05, 0.05 + 0.03, name='cut'))
kit.boolean(cab, slab_xz(back, D / 2 - 0.012, 0.05, name='cut'))

kit.box((W - 0.05, D - 0.04, 0.05), at=(0, 0.01, 0.045), material=dark, bevel=0.008, name='plinth')

# ---------------------------------------------------------------- crown: glowing arched panel, radial ribs, "30"
glass_y = YF + 0.026
slab_xz(panel, glass_y, 0.01, material=amber_glow, name='arch_glass')
for k in range(1, 6):
    a = math.pi * k / 6
    ex, ez = panel_hw * math.cos(a), panel_z0 + panel_rise * math.sin(a)
    flat_bar((0.07 * math.cos(a), glass_y - 0.006, panel_z0 + 0.07 * math.sin(a)),
             (ex * 0.985, glass_y - 0.006, panel_z0 + (ez - panel_z0) * 0.985), 0.011, 0.01, chrome, name='rib')
slab_xz([(0.075, panel_z0)] + arch(0.075, panel_z0, 0.075, 16)[1:-1] + [(-0.075, panel_z0)],
        glass_y - 0.016, 0.014, material=chrome, bevel=0.003, name='rib_hub')
ptube([(x, YF - 0.003, z) for x, z in arch(W / 2 - 0.035, SH, RISE - 0.03, 36)], 0.007, chrome, name='crown_trim')
ptube([(x, YF - 0.002, z) for x, z in arch(panel_hw + 0.008, panel_z0, panel_rise + 0.008, 36)], 0.006, chrome,
      name='panel_bead')
t30 = kit.text('30', 0.15, 0.014, at=(0, glass_y - 0.022, 1.262), material=brass, name='num30')
kit.finish(t30, bevel=0.002, segments=1)

# ---------------------------------------------------------------- "IYA" band under the arch
band_z = (1.012, 1.09)
kit.box((2 * panel_hw + 0.03, 0.022, band_z[1] - band_z[0]), at=(0, YF - 0.006, sum(band_z) / 2),
        material=band_red, bevel=0.005, name='iya_band')
for z in band_z:
    kit.box((2 * panel_hw + 0.05, 0.03, 0.009), at=(0, YF - 0.008, z), material=chrome, bevel=0.003, name='band_rule')
kit.text('IYA', 0.062, 0.008, at=(0, YF - 0.019, sum(band_z) / 2 - 0.001), material=cream, name='iya')

# ---------------------------------------------------------------- tall window: speaker cloth + diamond lattice
slab_xz(u_shape(win_hw, win_top, win_bot), YF + 0.027, 0.01, material=cloth, name='cloth')
bez = u_shape(win_hw + 0.007, win_top + 0.002, win_bot - 0.007, 28)
ptube([(x, YF - 0.002, z) for x, z in bez[1:] + bez[:1]], 0.007, chrome, name='bezel')
ptube([(win_hw + 0.007, YF - 0.002, win_top + 0.002), (-win_hw - 0.007, YF - 0.002, win_top + 0.002)], 0.007, chrome,
      name='bezel_top')

lx, lz0, lz1 = 0.15, 0.30, 0.90
ly = YF + 0.012
for sx in (-1, 1):
    kit.box((0.016, 0.012, lz1 - lz0 + 0.016), at=(sx * lx, ly, (lz0 + lz1) / 2), material=brass, bevel=0.003, name='lat_frame')
for z in (lz0, lz1):
    kit.box((2 * lx + 0.016, 0.012, 0.016), at=(0, ly, z), material=brass, bevel=0.003, name='lat_frame')


def clip_diag(c, sgn):
    """Segment of the line z = sgn*x + c inside the lattice rectangle."""
    pts = [(x, sgn * x + c) for x in (-lx, lx) if lz0 <= sgn * x + c <= lz1]
    pts += [((z - c) * sgn, z) for z in (lz0, lz1) if -lx <= (z - c) * sgn <= lx]
    pts = sorted(set((round(x, 6), round(z, 6)) for x, z in pts))
    return (pts[0], pts[-1]) if len(pts) >= 2 else None


step = 0.15
for sgn in (1, -1):
    c = lz0 - 2 * lx - step * 0.5
    while c < lz1 + 2 * lx:
        seg = clip_diag(c, sgn)
        if seg and math.dist(seg[0], seg[1]) > 0.03:
            (x0, z0), (x1, z1) = seg
            yy = ly + (0.002 if sgn > 0 else -0.002)
            flat_bar((x0, yy, z0), (x1, yy, z1), 0.009, 0.006, brass, name='lattice')
        c += step
for i in range(-3, 4):
    for j in range(0, 12):
        x, z = i * step / 2, lz0 + j * step / 2
        if abs(x) < lx - 0.02 and lz0 + 0.02 < z < lz1 - 0.02 and (j + i) % 2 == 0:
            kit.sphere(0.008, at=(x, ly - 0.006, z), material=chrome, segs=10, rings=5, name='stud')

# ---------------------------------------------------------------- pillars: fluted glowing tubes, chrome caps, round feet
flutes = []
for i in range(16 * 6):
    a = math.tau * i / (16 * 6)
    r = PR * 0.88 * (1 - 0.07 * abs(math.sin(8 * a)) ** 0.6)
    flutes.append((r * math.cos(a), r * math.sin(a)))
for sx in (-1, 1):
    x = sx * PX
    kit.extrude(flutes, 1.0, at=(x, PY, 0.105), material=pillar_glow, bevel=0.004, name='pillar_tube')
    kit.lathe([(0, 1.1), (PR + 0.006, 1.1), (PR + 0.01, 1.115), (PR + 0.01, 1.15), (PR + 0.004, 1.16),
               (PR + 0.012, 1.175), (PR + 0.012, 1.19), (PR * 0.8, 1.215), (0, 1.222)],
              at=(x, PY, 0), material=chrome, steps=40, name='pillar_cap')
    kit.lathe([(0, 0.05), (PR + 0.012, 0.05), (PR + 0.012, 0.085), (PR + 0.004, 0.1), (PR + 0.004, 0.11), (0, 0.11)],
              at=(x, PY, 0), material=chrome, steps=40, name='pillar_base')
    kit.lathe([(0, 0.0), (PR * 0.75, 0.0), (PR * 0.95, 0.015), (PR + 0.006, 0.035), (PR + 0.006, 0.05), (0, 0.05)],
              at=(x, PY, 0), material=brass, steps=40, name='pillar_foot')
    kit.lathe([(0, 0.0), (0.03, 0.0), (0.038, 0.02), (0.038, 0.03), (0, 0.03)],
              at=(sx * (W / 2 - 0.07), D / 2 - 0.07, 0), material=rubber, steps=24, name='rear_foot')
    kit.box((0.05, 0.06, 0.02), at=(sx * (W / 2 - 0.07), D / 2 - 0.07, 0.035), material=dark, name='rear_foot_block')

# ---------------------------------------------------------------- sides: chrome trim lines near the top (as drawn)
for sx in (-1, 1):
    xs = sx * (W / 2 - 0.004)
    L = D - 0.06
    for z in (0.94, 1.0, 1.06, 1.12):
        kit.box((0.01, L, 0.012), at=(xs + sx * 0.003, YF + 0.045 + L / 2, z), material=chrome, bevel=0.004, name='side_trim')
    for z in (0.97, 1.09):
        kit.box((0.01, 0.012, 0.05), at=(xs + sx * 0.002, YF + 0.045 + L * 0.7, z), material=chrome, bevel=0.003, name='side_tick')
    for k in range(6):
        kit.box((0.012, 0.16, 0.012), at=(xs + sx * 0.002, 0.03, 0.3 + k * 0.035), material=dark, bevel=0.004, name='side_vent')

# ---------------------------------------------------------------- back: service panel, louvres, screws, cable
yb = D / 2 - 0.012
slab_xz(back, yb, 0.006, material=wood_lt, name='back_panel')
ys = D / 2 - 0.006          # outer face of the back panel
for k in range(9):
    kit.box((0.32, 0.008, 0.018), at=(0, ys + 0.003, 0.62 + k * 0.042), material=dark, bevel=0.003, name='back_vent')
for x in (-0.24, 0.24):
    for z in (0.2, 0.98):
        kit.cyl(0.009, 0.004, at=(x, ys + 0.002, z), rot=(90, 0, 0), material=brass, verts=16, name='screw')
kit.box((0.09, 0.014, 0.06), at=(0.12, ys + 0.006, 0.28), material=black, bevel=0.004, name='socket')
ptube([(0.12, ys + 0.012, 0.28), (0.12, ys + 0.04, 0.27), (0.12, ys + 0.06, 0.22), (0.115, ys + 0.07, 0.1),
       (0.1, ys + 0.075, 0.03), (0.07, ys + 0.08, 0.009)], 0.008, black, name='cable')

kit.export('jukebox')
