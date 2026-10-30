"""Washing machine (Christian Kim). Front-loader as drawn: tall cabinet, a control console sloping back along the
top front edge (drawer | dial | display), a big porthole door set a little left of centre with the drum and its
lifters visible through the glass, a deep kick plinth, and a sculpted arc swept across the side panel."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math, tempfile
import numpy as np
from mathutils import Vector, Matrix


# ---------- local helpers ----------
def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def resmooth(o, angle=30):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    return o


def xform(objs, M):
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    return objs


def save_tex(name, rgb):
    """rgb: HxWx3 float array of sRGB values, row 0 = top. Writes a PNG and returns its path."""
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 4), np.float32); a[..., :3] = rgb[::-1]
    img = bpy.data.images.new(name, w, h)
    img.pixels.foreach_set(a.ravel())
    path = os.path.join(tempfile.gettempdir(), f'{name}.png')
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


def uv_cyl(o, u_rep=1.0, v_scale=1.0):
    """Cylindrical UVs around the object's local Z axis."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        us = [(math.atan2(l.vert.co.y, l.vert.co.x) / math.tau) % 1.0 for l in f.loops]
        if max(us) - min(us) > 0.5:
            us = [u + 1 if u < 0.5 else u for u in us]
        for l, u in zip(f.loops, us):
            l[uv].uv = (u * u_rep, l.vert.co.z * v_scale)
    bm.to_mesh(o.data); bm.free()
    return o


# ---------- dimensions (from the drawing: tall cabinet, ~1.6 x the width) ----------
W, D, H = 0.60, 0.60, 0.95
PL = 0.12                   # plinth height
TOP = 0.025                 # top lid thickness
HS1 = H - TOP               # top of the sloped console
HS0 = HS1 - 0.13            # bottom of the console (top of the vertical front)
SET = 0.075                 # how far the console leans back
FY = -D / 2                 # front plane

body = kit.mat('#efe8d8', rough=0.32, name='enamel')
plinth_m = kit.mat('#d8cfbc', rough=0.45, name='plinth')
fascia = kit.mat('#23221f', rough=0.18, name='fascia')
chrome = kit.mat('chrome', rough=0.22, metal=0.95, name='chrome')
satin = kit.mat('steel', rough=0.35, metal=0.85, name='satin')
rubber = kit.mat('#2a2826', rough=0.8, name='rubber')
glass = kit.mat('#9fbccb', rough=0.05, alpha=0.28, name='glass')
smoke = kit.mat('#3b3a38', rough=0.08, name='smoke')
amber = kit.mat('amber', rough=0.4, emit=2.0, name='led')
hose_m = kit.mat('#8f8a80', rough=0.6, name='hose')
brass = kit.mat('brass', rough=0.3, metal=0.9, name='brass')

# ---------- cabinet: side profile extruded across the width ----------
prof = [(FY, PL), (D / 2, PL), (D / 2, HS1), (FY + SET, HS1), (FY, HS0)]
cab = kit.extrude(prof, W, at=(-W / 2, 0, 0), rot=(90, 0, 90), material=body, bevel=0.014, segments=3, name='cabinet')
apply_mods(cab)

# door opening into the drum
DX, DZ = -0.015, 0.505
cut = kit.cyl(0.207, 0.6, at=(DX, FY, DZ), rot=(90, 0, 0), verts=64)
kit.boolean(cab, cut)

# the arc swept across each side panel (the drawing's side swoosh), as a soft recessed groove
arc = [(0.20, 0.52), (0.212, 0.40), (0.19, 0.29), (0.12, 0.225), (0.0, 0.21), (-0.12, 0.235), (-0.21, 0.29)]
for sx in (-1, 1):
    c = kit.tube([(sx * W / 2, y, z) for y, z in arc], 0.011, name='groove')
    kit.boolean(cab, c)
# back vents
for i in range(6):
    v = kit.box((0.20, 0.03, 0.012), at=(0.12, D / 2, 0.80 - i * 0.026), bevel=0.004)
    kit.boolean(cab, v)
resmooth(cab)

# top lid, slightly proud of the cabinet so there's a real seam
lid = kit.box((W + 0.006, D - SET + 0.006, TOP), at=(0, (FY + SET + D / 2 + 0.006) / 2, H - TOP / 2),
              material=body, bevel=0.008, segments=3, name='lid')

# plinth: recessed kick plate, darker
pl = kit.box((W - 0.012, D - 0.03, PL - 0.016), at=(0, 0.012, 0.016 + (PL - 0.016) / 2), material=plinth_m,
             bevel=0.006, segments=2, name='plinth')
# pump-filter hatch on the kick plate, bottom right
hatch = kit.box((0.09, 0.006, 0.065), at=(0.19, FY + 0.015, 0.066), material=plinth_m, bevel=0.004, name='hatch')
kit.box((0.026, 0.004, 0.004), at=(0.19, FY + 0.0115, 0.088), material=fascia, name='hatch_slot')
for sx in (-1, 1):
    for sy in (-1, 1):
        kit.cyl(0.022, 0.016, at=(sx * 0.25, sy * 0.25, 0.008), material=rubber, bevel=0.003, verts=24, name='foot')

# ---------- console on the slope ----------
ey = Vector((0, SET, HS1 - HS0)).normalized()          # up the slope
n = Vector((0, -(HS1 - HS0), SET)).normalized()         # out of the slope
P0 = Vector((0, FY + SET / 2, (HS0 + HS1) / 2))
M = Matrix(((1, ey.x, n.x, P0.x), (0, ey.y, n.y, P0.y), (0, ey.z, n.z, P0.z), (0, 0, 0, 1)))
SL = math.hypot(SET, HS1 - HS0)
parts = []
parts.append(kit.box((W - 0.04, SL - 0.03, 0.006), at=(0, 0, 0.002), material=fascia, bevel=0.003, name='fascia'))
# section dividers (thin satin lines like the drawing's three bays)
for x in (-0.085, 0.085):
    parts.append(kit.box((0.003, SL - 0.05, 0.002), at=(x, 0, 0.0055), material=satin, name='divider'))
# left bay: detergent drawer, proud of the fascia with a pull lip along the bottom
dr = kit.box((0.17, SL - 0.05, 0.022), at=(-0.18, 0.004, 0.012), material=body, bevel=0.005, segments=3, name='drawer')
parts.append(dr)
parts.append(kit.box((0.15, 0.06, 0.004), at=(-0.18, 0.012, 0.0235), material=smoke, bevel=0.0015, name='drawer_window'))
parts.append(kit.box((0.15, 0.012, 0.012), at=(-0.18, -(SL - 0.05) / 2 + 0.004, 0.028), material=body, bevel=0.004,
                     name='drawer_lip'))
# centre bay: the programme dial with its tick ring
parts.append(kit.cyl(0.048, 0.006, at=(0, 0, 0.007), material=satin, verts=48, bevel=0.002, name='dial_ring'))
knob = kit.lathe([(0, 0.032), (0.026, 0.032), (0.034, 0.028), (0.037, 0.02), (0.037, 0.008), (0.035, 0.006), (0, 0.006)],
                 material=chrome, steps=48, name='knob')
parts.append(knob)
# grip ridges on the knob skirt
for i in range(18):
    a = i * math.tau / 18
    r = kit.box((0.004, 0.006, 0.014), at=(0.037 * math.cos(a), 0.037 * math.sin(a), 0.016), rot=(0, 0, math.degrees(a)),
                material=chrome, name='ridge')
    parts.append(r)
# the dark half-window on the knob face (drawn shaded)
hw = kit.extrude([(0.019 * math.cos(t), 0.019 * math.sin(t)) for t in np.linspace(math.pi, math.tau, 16)], 0.003,
                 at=(0, 0, 0.0315), material=smoke, name='knob_window')
parts.append(hw)
parts.append(kit.box((0.003, 0.012, 0.003), at=(0, 0.017, 0.0325), material=amber, name='pointer'))
for i in range(11):
    a = math.radians(210 - i * 24)
    parts.append(kit.box((0.012, 0.0025, 0.0015), at=(0.058 * math.cos(a), 0.058 * math.sin(a), 0.0055),
                         rot=(0, 0, math.degrees(a)), material=satin, name='tick'))
# right bay: display window with three small buttons at its end
parts.append(kit.box((0.13, SL - 0.06, 0.004), at=(0.16, 0.002, 0.006), material=smoke, bevel=0.002, name='display'))
parts.append(kit.box((0.06, 0.012, 0.0015), at=(0.145, 0.006, 0.0085), material=amber, name='display_glow'))
for j, y in enumerate((0.03, 0.0, -0.03)):
    parts.append(kit.cyl(0.0085, 0.006, at=(0.255, y, 0.008), material=satin, bevel=0.0015, verts=20, name='button'))
xform(parts, M)

# ---------- drum, gasket, door ----------
F = Matrix.Translation((DX, FY, DZ)) @ Matrix.Rotation(math.radians(90), 4, 'X')   # local +Z -> world -Y
# perforated drum texture
tw, th = 1024, 256
yy, xx = np.mgrid[0:th, 0:tw]
pitch = 16
cx = (xx % pitch) - pitch / 2; row = yy // pitch
cy = (yy % pitch) - pitch / 2
cx = np.where(row % 2 == 1, ((xx + pitch // 2) % pitch) - pitch / 2, cx)
d = np.sqrt(cx ** 2 + cy ** 2)
hole = np.clip(3.4 - d, 0, 1)[..., None]
rgb = np.ones((th, tw, 3)) * np.array([0.70, 0.72, 0.75])
rgb = rgb * (1 - hole) + np.array([0.16, 0.17, 0.19]) * hole
drum_tex = kit.mat('#ffffff', rough=0.35, metal=0.85, name='drum', image=save_tex('wm_drum', rgb))

drum_parts = []
drum = kit.lathe([(0.203, 0.0), (0.203, -0.30), (0, -0.30), (0, -0.285), (0.19, -0.285), (0.19, 0.0), (0.203, 0.0)],
                 material=drum_tex, steps=64, name='drum')
uv_cyl(drum, u_rep=1.0, v_scale=3.6)
drum_parts.append(drum)
# drum back: a pressed star hub
drum_parts.append(kit.cyl(0.05, 0.01, at=(0, 0, -0.281), material=satin, bevel=0.003, verts=32, name='hub'))
for i in range(3):
    a = math.radians(90 + i * 120)
    rr = 0.19 - 0.014
    drum_parts.append(kit.box((0.03, 0.035, 0.25), at=(rr * math.cos(a), rr * math.sin(a), -0.155),
                              rot=(0, 0, math.degrees(a)), material=satin, bevel=0.01, segments=3, name='lifter'))
# rubber boot gasket rolling over the opening lip
drum_parts.append(kit.lathe([(0.172, -0.03), (0.19, -0.035), (0.208, -0.012), (0.212, 0.004), (0.2, 0.012), (0.182, 0.01),
                             (0.168, -0.004), (0.172, -0.03)], material=rubber, steps=64, name='gasket'))
# door: chrome outer ring, dark inner bezel, domed glass bowl
drum_parts.append(kit.lathe([(0.198, 0.012), (0.243, 0.016), (0.252, 0.032), (0.246, 0.05), (0.225, 0.058), (0.2, 0.056),
                             (0.198, 0.012)], material=chrome, steps=72, name='door_ring'))
drum_parts.append(kit.lathe([(0.16, 0.012), (0.2, 0.012), (0.2, 0.054), (0.178, 0.05), (0.165, 0.042), (0.158, 0.03),
                             (0.16, 0.012)], material=fascia, steps=64, name='door_bezel'))
drum_parts.append(kit.lathe([(0, -0.062), (0.06, -0.058), (0.11, -0.04), (0.145, -0.012), (0.162, 0.018), (0.166, 0.03),
                             (0.159, 0.03), (0.155, 0.018), (0.139, -0.008), (0.105, -0.034), (0.057, -0.052), (0, -0.056)],
                            material=glass, steps=64, name='door_glass'))
# hinge block on the right of the door, handle recess on the left (the drawing's slot)
drum_parts.append(kit.box((0.034, 0.12, 0.05), at=(0.25, 0, 0.026), material=fascia, bevel=0.008, segments=3, name='hinge'))
xform(drum_parts, F)
door_ring = [o for o in drum_parts if o.name.startswith('door_ring')][0]
slot = kit.box((0.04, 0.09, 0.07), at=(DX - 0.252, FY - 0.04, DZ), bevel=0.0)
kit.boolean(door_ring, slot)
resmooth(door_ring)
# finger pull: a dark scoop set into the notch
kit.box((0.012, 0.03, 0.074), at=(DX - 0.226, FY - 0.035, DZ), material=fascia, bevel=0.004, name='handle_insert')

# ---------- back: service plate, screws, inlet valve, drain hose and hooked cord ----------
BY = D / 2
kit.box((0.46, 0.006, 0.5), at=(0, BY + 0.003, 0.42), material=plinth_m, bevel=0.004, name='back_plate')
for sx in (-1, 1):
    for z in (0.19, 0.65):
        kit.cyl(0.009, 0.004, at=(sx * 0.21, BY + 0.008, z), rot=(-90, 0, 0), material=satin, verts=16, bevel=0.0015,
                name='screw')
# corner transport-bolt caps
for sx in (-1, 1):
    kit.cyl(0.017, 0.006, at=(sx * 0.255, BY + 0.003, 0.88), rot=(-90, 0, 0), material=plinth_m, verts=24, bevel=0.002,
            name='cap')
# cold-water inlet valve, top right
kit.box((0.06, 0.03, 0.05), at=(0.2, BY + 0.015, 0.87), material=plinth_m, bevel=0.006, name='valve_body')
kit.cyl(0.011, 0.03, at=(0.2, BY + 0.045, 0.87), rot=(-90, 0, 0), material=brass, verts=24, name='inlet')
for k in range(4):
    kit.torus(0.0115, 0.0018, at=(0.2, BY + 0.036 + k * 0.006, 0.87), rot=(90, 0, 0), material=brass, major=24, minor=6,
              name='thread')
# drain hose: out low on the left, up the back, over a hook
hose = [(-0.17, BY + 0.0, 0.2), (-0.17, BY + 0.03, 0.22), (-0.17, BY + 0.03, 0.5), (-0.17, BY + 0.03, 0.82),
        (-0.155, BY + 0.03, 0.88), (-0.12, BY + 0.03, 0.86), (-0.12, BY + 0.03, 0.78)]
kit.tube(hose, 0.014, material=hose_m, bevel_res=6, name='drain_hose')
for z in (0.36, 0.6):
    kit.box((0.05, 0.022, 0.018), at=(-0.17, BY + 0.012, z), material=plinth_m, bevel=0.004, name='hose_clip')
kit.tube([(-0.155, BY + 0.0, 0.84), (-0.155, BY + 0.06, 0.84)], 0.006, material=plinth_m, name='hook')
# mains cord: from the lower right, coiled on a hook
kit.tube([(0.16, BY + 0.0, 0.2), (0.16, BY + 0.03, 0.23), (0.16, BY + 0.035, 0.44)], 0.0055, material=fascia, name='cord')
kit.box((0.04, 0.03, 0.03), at=(0.16, BY + 0.012, 0.2), material=fascia, bevel=0.006, name='grommet')
coil = []
for t in np.linspace(0, 3 * math.tau, 40):
    coil.append((0.16 + 0.055 * math.sin(t), BY + 0.035 + 0.004 * t, 0.44 - 0.055 + 0.055 * math.cos(t)))
kit.tube(coil, 0.0055, material=fascia, bevel_res=3, name='cord_coil')
kit.tube([(0.16, BY + 0.0, 0.428), (0.16, BY + 0.11, 0.428), (0.16, BY + 0.125, 0.445)], 0.006, material=plinth_m, name='cord_hook')

kit.export('washing-machine')
