"""Camping lantern (Rodrigo Santana). As drawn: a tall candle lantern. A round fuel base with a soft bottom edge and a
rounded shoulder, a hex knob on its side, a domed burner with the wick and flame inside a clear glass chimney held by
two side posts, a deep collar above the glass and a tall dome punched with rows of round vent holes. The top of the
drawing runs off the page; a short stem and hanging ring finish it. Line drawing, so the copper and brass are ours,
following the copper lantern painted at this spot in the mural concept."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, math
from mathutils import Vector


def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def resmooth(o, angle=35):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    return o


copper = kit.mat('copper', rough=0.36, metal=0.85, name='copper')
dark_copper = kit.mat('#6e3d24', rough=0.45, metal=0.8, name='dark_copper')
brass = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
glass = kit.mat('#e8d6b4', rough=0.04, alpha=0.22, name='glass')
flame = kit.mat('lamp', rough=0.5, emit=8.0, name='flame')
flame_core = kit.mat('#fff1c8', rough=0.5, emit=10.0, name='flame_core')
halo = kit.mat('amber', rough=0.5, alpha=0.3, emit=3.0, name='halo')
soot = kit.mat('#1b1714', rough=0.7, name='soot')
wick = kit.mat('#2a211a', rough=0.8, name='wick')

# ---------- fuel base: soft bottom edge, straight side, rounded shoulder into the neck ----------
BR = 0.06
kit.lathe([(0, 0), (0.046, 0), (0.054, 0.003), (0.0588, 0.01), (BR, 0.02), (BR, 0.05), (0.0585, 0.06), (0.0545, 0.067),
           (0.048, 0.0715), (0.0435, 0.0735), (0.0425, 0.076), (0.0425, 0.084), (0.0, 0.084)],
          material=copper, steps=72, name='base')
kit.torus(0.0428, 0.0012, at=(0, 0, 0.0765), material=dark_copper, major=64, minor=6, name='neck_seam')
# hex knob on the side, a little left of front as drawn, with a pointer tick above it
ka = math.radians(-90 - 38)
kd = Vector((math.cos(ka), math.sin(ka), 0))
KZ = 0.04
stem = kit.cyl(0.0042, 0.012, material=brass, verts=16, name='knob_stem')
stem.rotation_mode = 'QUATERNION'; stem.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(kd)
stem.location = kd * (BR + 0.002) + Vector((0, 0, KZ))
hexk = kit.cyl(0.0135, 0.009, material=brass, verts=6, bevel=0.0014, name='hex_knob')
hexk.rotation_mode = 'QUATERNION'; hexk.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(kd)
hexk.location = kd * (BR + 0.009) + Vector((0, 0, KZ))
cap = kit.cyl(0.0068, 0.003, material=brass, verts=20, bevel=0.0008, name='knob_cap')
cap.rotation_mode = 'QUATERNION'; cap.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(kd)
cap.location = kd * (BR + 0.0145) + Vector((0, 0, KZ))
for dz in (0.0175, 0.0205):
    t = kit.box((0.0012, 0.0012, 0.0075), material=brass, name='pointer_tick')
    t.rotation_euler = (0, math.radians(90), ka + math.radians(90))
    t.location = kd * (BR + 0.0004) + Vector((0, 0, KZ + dz))

# ---------- burner dome, wick, flame ----------
kit.lathe([(0, 0.083), (0.039, 0.083), (0.0392, 0.088), (0.0365, 0.1), (0.03, 0.109), (0.02, 0.1145), (0.0, 0.1165)],
          material=dark_copper, steps=56, name='burner')
kit.cyl(0.0048, 0.01, at=(0, 0, 0.12), material=brass, verts=20, bevel=0.0008, name='wick_tube')
kit.cyl(0.0022, 0.006, at=(0, 0, 0.127), material=wick, verts=12, name='wick')
kit.lathe([(0, 0.128), (0.0045, 0.131), (0.0068, 0.137), (0.0066, 0.145), (0.0048, 0.153), (0.0022, 0.161),
           (0, 0.166)], material=flame, steps=24, name='flame')
kit.lathe([(0, 0.13), (0.0026, 0.133), (0.0034, 0.139), (0.0024, 0.146), (0, 0.15)], material=flame_core, steps=16,
          name='flame_core')
kit.lathe([(0, 0.124), (0.011, 0.13), (0.014, 0.142), (0.011, 0.156), (0.005, 0.165), (0, 0.168)], material=halo,
          steps=24, name='flame_glow')

# ---------- glass chimney and the two side posts ----------
G0, G1 = 0.0838, 0.214
GR = 0.0405
kit.lathe([(GR - 0.0018, G0), (GR, G0), (GR, G1), (GR - 0.0018, G1), (GR - 0.0018, G0)], material=glass, steps=64,
          name='glass')
for sx in (-1, 1):
    x = sx * 0.0515
    kit.cyl(0.0036, G1 - 0.064 + 0.006, at=(x, 0, (0.064 + G1) / 2), material=dark_copper, verts=16, name='post')
    kit.cyl(0.0058, 0.004, at=(x, 0, 0.0655), material=brass, verts=16, bevel=0.001, name='post_foot')

# ---------- collar and the vented dome ----------
C0, C1, CR = 0.21, 0.288, 0.0555
kit.lathe([(0.0, C0 + 0.004), (0.039, C0 + 0.004), (0.041, C0), (0.05, C0), (0.0545, C0 + 0.003), (CR, C0 + 0.01),
           (CR, C1 - 0.004), (0.0545, C1), (0.05, C1 + 0.0015), (0.0, C1 + 0.0015)], material=copper, steps=72,
          name='collar')
kit.torus(0.0493, 0.0018, at=(0, 0, C1 + 0.0015), material=dark_copper, major=64, minor=8, name='dome_lip')
DR, DH = 0.0475, 0.076
prof = []
for i in range(19):
    a = math.radians(90 * i / 18)
    prof.append((DR * math.cos(a) ** 0.9 if i < 18 else 0.0, C1 + 0.0015 + DH * math.sin(a)))
inner = [(max(r - 0.0016, 0.0), z - 0.0016) for r, z in reversed(prof)]
dome = kit.lathe(prof + inner + [prof[0]], material=copper, steps=64, name='dome')
apply_mods(dome)
# rows of round vent holes, staggered as drawn
rows = [(0.16, 14, 0.0), (0.42, 12, 0.5), (0.66, 8, 0.0), (0.86, 4, 0.5)]
for t, n, off in rows:
    a = t * math.pi / 2
    r = DR * math.cos(a) ** 0.9; z = C1 + 0.0015 + DH * math.sin(a)
    nrm = Vector((DH * math.cos(a), 0, DR * math.sin(a))).normalized()   # normal in the xz half-plane
    for k in range(n):
        phi = (k + off) * math.tau / n + math.radians(-90)
        d = Vector((nrm.x * math.cos(phi), nrm.x * math.sin(phi), nrm.z))
        p = Vector((r * math.cos(phi), r * math.sin(phi), z))
        h = kit.cyl(0.0036, 0.012, verts=12)
        h.rotation_mode = 'QUATERNION'; h.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
        h.location = p
        kit.boolean(dome, h)
resmooth(dome)
# a dark sooty liner inside the dome, seen through the holes
kit.lathe([(0, C1), (DR - 0.005, C1), (DR * 0.76, C1 + DH * 0.55), (DR * 0.4, C1 + DH * 0.86), (0, C1 + DH * 0.92)],
          material=soot, steps=48, name='dome_liner')
# stem and hanging ring at the top (the drawing runs off the page here)
TOPZ = C1 + 0.0015 + DH
kit.lathe([(0, TOPZ - 0.004), (0.0075, TOPZ - 0.004), (0.0075, TOPZ + 0.002), (0.004, TOPZ + 0.005), (0.004, TOPZ + 0.014),
           (0, TOPZ + 0.014)], material=brass, steps=24, name='finial')
kit.torus(0.0105, 0.0022, at=(0, 0, TOPZ + 0.025), rot=(90, 0, 0), material=brass, major=32, minor=8, name='hang_ring')

kit.export('camping-lantern')
