"""Contemporary robot (Iris Zhang). A slim mannequin-like humanoid as drawn: rounded-box head whose face screen reads
'C13' with a little heart, a slotted neck collar, a smooth egg-shaped chest ending in a V over a narrow waist, a ribbed
pelvis with big drum hip joints, disc shoulders, thin limbs with ball elbows and a screwed wrist joint, U-shaped
gripper hands (one raised in a wave), tapered legs with cuffed knees and rounded slipper feet. Line drawing, so the
finish is ours: warm white shells, graphite joints, an amber face and small teal accents."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
from mathutils import Vector, Matrix


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


def align(o, p0, p1):
    """Place an object built along +Z from its origin so it runs from p0 toward p1."""
    d = (Vector(p1) - Vector(p0)).normalized()
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    o.location = p0
    return o


def limb(p0, p1, r0, r1, material, name='limb', steps=32):
    """Tapered capsule-ish segment from p0 (radius r0) to p1 (radius r1)."""
    L = (Vector(p1) - Vector(p0)).length
    prof = [(0, -r0 * 0.25), (r0 * 0.75, -r0 * 0.12), (r0, 0.02 * L), (r0 * 0.97, 0.2 * L), (r1 * 1.02, 0.85 * L),
            (r1, 0.97 * L), (r1 * 0.7, L + r1 * 0.12), (0, L + r1 * 0.25)]
    o = kit.lathe(prof, material=material, steps=steps, name=name)
    return align(o, Vector(p0), Vector(p1))


def disc_joint(c, axis, r, depth, shell_m, hub_m, ring_m, name='joint'):
    """A drum joint: rounded cap with a hub and an accent ring, facing along axis."""
    objs = []
    cap = kit.lathe([(0, 0), (r, 0), (r * 1.02, depth * 0.35), (r * 0.96, depth * 0.85), (r * 0.82, depth), (0, depth)],
                    material=shell_m, steps=40, name=name)
    hub = kit.lathe([(0, depth - 0.002), (r * 0.5, depth - 0.002), (r * 0.5, depth + 0.004), (r * 0.42, depth + 0.009),
                     (r * 0.18, depth + 0.009), (r * 0.18, depth + 0.004), (0, depth + 0.004)], material=hub_m, steps=32,
                    name=name + '_hub')
    ring = kit.torus(r * 0.66, r * 0.035, material=ring_m, major=40, minor=6, name=name + '_ring')
    ring.location = (0, 0, depth + 0.0005)
    for o in (cap, hub, ring):
        M = Matrix.Translation(c) @ Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
        o.matrix_world = M @ o.matrix_world
    return [cap, hub, ring]


def gripper(wrist, direction, facing, material, cuff_m, name='hand'):
    """The drawing's U-shaped hand: a wrist cuff, a small palm and a U whose opening points along `direction`."""
    d = Vector(direction).normalized(); f = Vector(facing).normalized()
    side = d.cross(f).normalized(); f = side.cross(d).normalized()
    W = Vector(wrist)
    cuff = kit.cyl(0.022, 0.03, material=cuff_m, verts=24, bevel=0.004, name=name + '_cuff')
    align(cuff, W, W + d); cuff.location = W + d * 0.0
    palm = kit.box((0.05, 0.026, 0.03), material=material, bevel=0.009, segments=2, name=name + '_palm')
    palm.matrix_world = Matrix.Translation(W + d * 0.028) @ Matrix((side, f, d)).transposed().to_4x4()
    R, h = 0.026, 0.028
    base = W + d * (0.04 + R)
    pts = [base + side * (-R) + d * h, base + side * (-R)]
    for k in range(1, 8):
        a = math.pi * k / 8
        pts.append(base - side * R * math.cos(a) - d * R * math.sin(a))
    pts += [base + side * R, base + side * R + d * h]
    u = kit.tube([tuple(p) for p in pts], 0.0105, material=material, bevel_res=10, name=name + '_u')
    tips = [kit.sphere(0.0108, at=tuple(p), material=material, segs=16, rings=8, name=name + '_tip') for p in (pts[0], pts[-1])]
    return [cuff, palm, u] + tips


def heart(size):
    pts = []
    for i in range(40):
        t = math.tau * i / 40
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * size / 32, y * size / 32))
    return pts


shell = kit.mat('#efe9dd', rough=0.3, name='shell')
graphite = kit.mat('#34373c', rough=0.42, name='graphite')
joint_m = kit.mat('gunmetal', rough=0.35, metal=0.85, name='joint_metal')
teal = kit.mat('teal', rough=0.35, name='teal')
screen = kit.mat('#121417', rough=0.08, name='screen')
glow = kit.mat('amber', rough=0.4, emit=4.0, name='glow')
heart_m = kit.mat('#e0453a', rough=0.4, emit=3.0, name='heart')
sole = kit.mat('rubber', rough=0.8, name='sole')

# ---------- head ----------
HC = Vector((0, -0.004, 1.462))
HW, HD, HH = 0.27, 0.235, 0.29
head = kit.box((HW, HD, HH), at=tuple(HC), material=shell, bevel=0.06, segments=5, name='head')
apply_mods(head)
SW, SH = 0.172, 0.19
rec = kit.box((SW + 0.008, 0.05, SH + 0.008), at=(HC.x, HC.y - HD / 2, HC.z - 0.005), bevel=0.034, segments=4)
kit.boolean(head, rec); resmooth(head)
SF = HC.y - HD / 2 - 0.002   # screen front, just proud of the head
kit.box((SW, 0.03, SH), at=(HC.x, SF + 0.015, HC.z - 0.005), material=screen, bevel=0.012, segments=3, name='face_screen')
FZ = SF - 0.0005
c13 = kit.text('C13', 0.072, 0.002, at=(HC.x - 0.002, FZ, HC.z + 0.026), material=glow, name='c13')
FONT = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'   # a '1' with a flag, like the drawing
if os.path.exists(FONT):
    bpy.data.objects.remove(c13, do_unlink=True)
    cu = bpy.data.curves.new('c13', 'FONT'); cu.body = 'C13'; cu.size = 0.07; cu.extrude = 0.001
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.font = bpy.data.fonts.load(FONT)
    c13 = bpy.data.objects.new('c13', cu); bpy.context.collection.objects.link(c13)
    c13.location = (HC.x - 0.002, FZ, HC.z + 0.026); c13.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.view_layer.objects.active = c13; c13.select_set(True); bpy.ops.object.convert(target='MESH')
    c13 = bpy.context.object; c13.data.materials.append(glow)
kit.extrude(heart(0.026), 0.002, at=(HC.x + 0.012, SF + 0.0005, HC.z - 0.04), rot=(90, 0, 0), material=heart_m,
            name='heart')
for sx in (-1, 1):   # side sensors ("ears")
    disc_joint(Vector((sx * HW / 2 - sx * 0.004, HC.y + 0.01, HC.z + 0.0)), (sx, 0, 0), 0.034, 0.012, shell, graphite, teal,
               name='ear')
# antenna-free crown seam
kit.torus(0.06, 0.003, at=(HC.x, HC.y + 0.01, HC.z + HH / 2 - 0.0005), material=graphite, major=40, minor=6,
          name='crown_seam')

# ---------- neck and collar ----------
kit.cyl(0.04, 0.12, at=(0, 0, 1.275), material=graphite, verts=32, name='neck')
collar = kit.lathe([(0.04, 1.236), (0.072, 1.236), (0.079, 1.243), (0.07, 1.28), (0.052, 1.29), (0.04, 1.29),
                    (0.04, 1.236)], material=shell, steps=48, name='collar')
apply_mods(collar)
for i in range(10):
    a = i * math.tau / 10
    slot = kit.box((0.007, 0.05, 0.03), at=(0.075 * math.cos(a), 0.075 * math.sin(a), 1.268), rot=(0, 0, math.degrees(a) + 90))
    kit.boolean(collar, slot)
resmooth(collar)

# ---------- chest: egg-shaped shell, V at the bottom front, seam down the middle ----------
chest = kit.lathe([(0, 0.925), (0.07, 0.928), (0.115, 0.96), (0.148, 1.03), (0.158, 1.1), (0.152, 1.16), (0.128, 1.205),
                   (0.09, 1.232), (0.05, 1.242), (0, 1.244)], material=shell, steps=48, name='chest')
chest.scale = (1, 0.66, 1); bpy.context.view_layer.objects.active = chest
bpy.ops.object.select_all(action='DESELECT'); chest.select_set(True)
bpy.ops.object.transform_apply(scale=True)
apply_mods(chest)
v = kit.extrude([(-0.2, 0.8), (0.2, 0.8), (0.2, 1.035), (0.0, 0.93), (-0.2, 1.035)], 0.2, at=(0, 0, 0), rot=(90, 0, 0))
kit.boolean(chest, v)
seam = kit.box((0.005, 0.2, 0.2), at=(0, -0.1, 1.095))
kit.boolean(chest, seam)
resmooth(chest)
# back pack: battery housing with vents and a status light
bp = kit.box((0.17, 0.05, 0.19), at=(0, 0.098, 1.09), material=shell, bevel=0.022, segments=3, name='backpack')
for i in range(5):
    kit.box((0.09, 0.004, 0.008), at=(0, 0.1235, 1.13 - i * 0.018), material=graphite, bevel=0.002, name='vent')
kit.cyl(0.008, 0.004, at=(0.052, 0.1235, 1.15), rot=(90, 0, 0), material=teal, verts=16, name='status')

# ---------- waist and pelvis ----------
kit.lathe([(0, 0.84), (0.07, 0.84), (0.078, 0.87), (0.07, 0.9), (0.075, 0.93), (0.064, 0.96), (0, 0.96)],
          material=graphite, steps=40, name='waist')
for z in (0.87, 0.9):
    kit.torus(0.074, 0.004, at=(0, 0, z), material=joint_m, major=40, minor=6, name='waist_ring')
pelvis = kit.box((0.26, 0.17, 0.15), at=(0, 0.004, 0.785), material=shell, bevel=0.05, segments=4, name='pelvis')
apply_mods(pelvis)
for i in range(4):   # the ribbed front plate of the drawing
    g = kit.box((0.12, 0.03, 0.006), at=(0, -0.081, 0.76 + i * 0.022), bevel=0.0)
    kit.boolean(pelvis, g)
resmooth(pelvis)
for sx in (-1, 1):
    disc_joint(Vector((sx * 0.128, 0.004, 0.77)), (sx, 0, 0), 0.068, 0.04, shell, graphite, teal, name='hip')

# ---------- shoulders and arms ----------
SHL = {-1: Vector((-0.178, 0.0, 1.185)), 1: Vector((0.178, 0.0, 1.185))}
for sx in (-1, 1):
    kit.sphere(0.045, at=tuple(SHL[sx]), material=joint_m, segs=24, rings=12, name='shoulder_ball')
    disc_joint(SHL[sx] + Vector((sx * 0.026, 0, 0)), (sx, 0, 0), 0.052, 0.022, shell, graphite, teal, name='shoulder')
# right arm (-X) raised in a wave
S, E, W = SHL[-1] + Vector((-0.03, 0, -0.01)), Vector((-0.31, -0.035, 1.05)), Vector((-0.355, -0.06, 1.25))
limb(S, E, 0.032, 0.026, shell, name='upper_arm_r')
kit.sphere(0.03, at=tuple(E), material=joint_m, segs=24, rings=12, name='elbow')
limb(E, W, 0.026, 0.021, shell, name='forearm_r')
gripper(W, W - E, (0, -1, 0.0), graphite, joint_m, name='hand_r')
# left arm (+X) hanging, with the screwed wrist joint
S, E, W = SHL[1] + Vector((0.03, 0, -0.01)), Vector((0.225, 0.004, 0.935)), Vector((0.242, -0.012, 0.725))
limb(S, E, 0.032, 0.026, shell, name='upper_arm_l')
kit.sphere(0.03, at=tuple(E), material=joint_m, segs=24, rings=12, name='elbow')
limb(E, W, 0.026, 0.021, shell, name='forearm_l')
J = E + (W - E) * 0.55
wj = kit.cyl(0.028, 0.03, material=graphite, verts=24, bevel=0.005, name='wrist_joint')
align(wj, J, J + (W - E).normalized())
kit.cyl(0.006, 0.006, at=tuple(J + Vector((0, -0.028, 0))), rot=(90, 0, 0), material=joint_m, verts=12, name='screw')
gripper(W, W - E, (0, -1, 0.0), graphite, joint_m, name='hand_l')

# ---------- legs ----------
legs = {-1: (Vector((-0.09, 0.02, 0.73)), Vector((-0.095, 0.03, 0.41)), Vector((-0.098, 0.035, 0.095))),
        1: (Vector((0.09, -0.008, 0.73)), Vector((0.096, -0.03, 0.41)), Vector((0.1, -0.045, 0.095)))}
for sx, (Hp, K, A) in legs.items():
    limb(Hp, K + (K - Hp).normalized() * 0.02, 0.068, 0.046, shell, name='thigh')
    kit.sphere(0.042, at=tuple(K), material=joint_m, segs=24, rings=12, name='knee')
    # shin with a cuff at the top that sits over the knee (the drawing's notch)
    limb(K, A, 0.047, 0.034, shell, name='shin')
    cuff = kit.lathe([(0.044, -0.005), (0.054, -0.002), (0.056, 0.03), (0.05, 0.05), (0.044, 0.05), (0.044, -0.005)],
                     material=graphite, steps=32, name='knee_cuff')
    align(cuff, K + (A - K).normalized() * 0.01, A)
    ak = kit.cyl(0.03, 0.04, material=graphite, verts=24, bevel=0.004, name='ankle')
    align(ak, A - Vector((0, 0, 0.03)), A + Vector((0, 0, 1)))
    # slipper foot: rounded upper on a thin sole
    fy = A.y - 0.045
    foot = kit.sphere(0.06, at=(A.x, fy, 0.022), scale=(0.85, 1.85, 0.85), material=shell, segs=32, rings=16, name='foot')
    cut = kit.box((0.3, 0.4, 0.1), at=(A.x, fy, -0.034))
    kit.boolean(foot, cut); resmooth(foot, 50)
    so = kit.lathe([(0, 0), (0.046, 0), (0.0505, 0.004), (0.0515, 0.012), (0.049, 0.017), (0, 0.017)],
                   at=(A.x, fy, 0.0), material=sole, steps=40, name='sole')
    so.scale = (1, 2.13, 1)



kit.export('contemporary-robot')
