"""Japanese toy robot (80s) - Keanna Bantay.

Her drawing: a blocky stand-up robot with a big helmeted head (a rounded crest running front to back, a visor slot
and a grille mouth on a face plate), a wide chest with a horizontal band, box shoulders, long box arms (a square
light on the right forearm), stacked leg blocks with rounded knee guards and big box feet; the left hand holds a
sword low and level across the front of the legs, pointing to the robot's right.
Line-only, so it is painted the way those toys were: white, red, blue (the palette's teal) and yellow, with
chrome and gunmetal joints - painted die-cast and plastic, not cartoon flat.
Invented: the back (backpack with two thrusters, battery hatch and screws), ear bolts, joint pins.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy

kit.reset()

white_m = kit.mat('#ece6da', rough=0.35, name='white')
red_m = kit.mat('red', rough=0.32, name='red')
blue_m = kit.mat('teal', rough=0.35, name='blue')
yellow_m = kit.mat('amber', rough=0.35, name='yellow')
gun_m = kit.mat('gunmetal', rough=0.35, metal=0.85, name='gunmetal')
chrome_m = kit.mat('chrome', rough=0.2, metal=0.95, name='chrome')
brass_m = kit.mat('brass', rough=0.3, metal=0.9, name='brass')
dark_m = kit.mat('#141516', rough=0.5, name='dark')
visor_m = kit.mat('amber', rough=0.2, emit=1.6, name='visor')


def part(size, at, m, bevel=0.003, seg=3, name='part', rot=None):
    return kit.box(size, at=at, rot=rot, material=m, bevel=bevel, segments=seg, name=name)


def pin(r, length, at, m=gun_m, axis='x'):
    rot = {'x': (0, 90, 0), 'y': (90, 0, 0), 'z': None}[axis]
    return kit.cyl(r, length, at=at, rot=rot, material=m, bevel=min(r, length) * 0.2, verts=24)


def screw(at, axis='y', r=0.0018):
    return pin(r, 0.0016, at, chrome_m, axis)


# ---------------------------------------------------------------- legs
for s in (-1, 1):
    x = s * 0.03
    part((0.047, 0.074, 0.03), (x, -0.012, 0.015), red_m, bevel=0.005, name='foot')
    part((0.035, 0.012, 0.012), (x, -0.045, 0.024), white_m, bevel=0.003, name='toe_cap')
    part((0.045, 0.051, 0.012), (x, 0.0, 0.036), yellow_m, bevel=0.0025, name='cuff')
    part((0.04, 0.046, 0.05), (x, 0.0, 0.066), blue_m, bevel=0.004, name='shin')
    part((0.026, 0.004, 0.03), (x, -0.024, 0.064), white_m, bevel=0.0015, name='shin_panel')
    for z in (0.056, 0.064, 0.072):
        part((0.018, 0.002, 0.0025), (x, -0.0262, z), dark_m, bevel=0.0006, name='shin_vent')
    pin(0.012, 0.036, (x, 0.002, 0.094))
    part((0.036, 0.017, 0.03), (x, -0.024, 0.095), red_m, bevel=0.007, seg=4, name='knee')
    part((0.034, 0.04, 0.042), (x, 0.0, 0.118), white_m, bevel=0.004, name='thigh')
    pin(0.01, 0.012, (s * 0.044, 0.0, 0.135))

# ---------------------------------------------------------------- hips and torso
part((0.09, 0.05, 0.03), (0, 0, 0.146), gun_m, bevel=0.004, name='hips')
part((0.03, 0.006, 0.032), (0, -0.026, 0.142), red_m, bevel=0.002, name='crotch_plate')
part((0.08, 0.056, 0.038), (0, 0, 0.174), white_m, bevel=0.004, name='abdomen')
part((0.096, 0.064, 0.02), (0, 0, 0.198), yellow_m, bevel=0.003, name='chest_band')
for k in range(-3, 4):
    part((0.004, 0.002, 0.012), (k * 0.009, -0.0325, 0.198), dark_m, bevel=0.0006, name='band_slot')
chest = part((0.102, 0.066, 0.042), (0, 0, 0.228), red_m, bevel=0.005, seg=3, name='chest')
part((0.07, 0.003, 0.03), (0, -0.0335, 0.229), red_m, bevel=0.002, name='chest_plate')
for x in (-0.031, 0.031):
    screw((x, -0.0355, 0.24))

# back: battery hatch and a backpack with two thrusters
part((0.06, 0.004, 0.034), (0, 0.034, 0.175), white_m, bevel=0.0015, name='hatch')
for x in (-0.024, 0.024):
    for z in (0.162, 0.188):
        screw((x, 0.0365, z))
part((0.064, 0.022, 0.05), (0, 0.042, 0.222), blue_m, bevel=0.006, name='backpack')
for x in (-0.018, 0.018):
    kit.lathe([(0.0, 0.0), (0.009, 0.0), (0.009, 0.004), (0.011, 0.016), (0.0085, 0.016), (0.007, 0.006),
               (0.0, 0.006)], at=(x, 0.044, 0.197), rot=(180, 0, 0), material=chrome_m, steps=32, name='thruster')

# ---------------------------------------------------------------- head (big helmet, as drawn)
HZ = 0.284                                  # head centre height
pin(0.016, 0.01, (0, 0.002, 0.255), m=gun_m, axis='z')
head = part((0.062, 0.064, 0.058), (0, 0.004, HZ), white_m, bevel=0.016, seg=4, name='head')
part((0.05, 0.005, 0.042), (0, -0.0275, HZ - 0.005), gun_m, bevel=0.0035, name='face_plate')
part((0.04, 0.005, 0.0085), (0, -0.0305, HZ + 0.005), visor_m, bevel=0.003, name='visor')
part((0.022, 0.004, 0.014), (0, -0.0305, HZ - 0.015), chrome_m, bevel=0.0014, name='grille')
for z in (HZ - 0.0195, HZ - 0.015, HZ - 0.0105):
    part((0.016, 0.002, 0.0016), (0, -0.0325, z), dark_m, bevel=0.0004, name='grille_slot')
for s in (-1, 1):
    pin(0.009, 0.006, (s * 0.033, 0.004, HZ))
    pin(0.004, 0.009, (s * 0.0385, 0.004, HZ), m=chrome_m)
# crest: a broad arched fin running front to back over the helmet
crest_prof = [(-0.03, HZ + 0.02), (-0.027, HZ + 0.033), (-0.016, HZ + 0.043), (0.002, HZ + 0.046),
              (0.02, HZ + 0.041), (0.031, HZ + 0.029), (0.034, HZ + 0.012), (0.0, HZ + 0.012)]
crest = kit.extrude([(y, z) for y, z in crest_prof], 0.026, material=red_m, bevel=0.005, segments=3, name='crest')
crest.rotation_euler = (math.radians(90), 0, math.radians(90)); crest.location = (-0.013, 0.0, 0.0)

# ---------------------------------------------------------------- shoulders and arms
for s in (-1, 1):
    part((0.038, 0.064, 0.036), (s * 0.07, 0, 0.232), blue_m, bevel=0.006, seg=3, name='shoulder')
    part((0.03, 0.003, 0.02), (s * 0.07, -0.0335, 0.232), white_m, bevel=0.0012, name='shoulder_panel')
    screw((s * 0.07, -0.0352, 0.24))


def arm(s, swing, light=False):
    """Arm hanging from the shoulder pivot; swing (deg) brings the fist forward. Returns the fist's pivot empty."""
    root = bpy.data.objects.new('arm', None); bpy.context.collection.objects.link(root)
    root.location = (s * 0.072, 0.0, 0.218); root.rotation_euler = (math.radians(-swing), 0, 0)
    ps = [pin(0.011, 0.03, (0, 0, 0)),
          part((0.026, 0.032, 0.046), (0, 0, -0.03), white_m, bevel=0.004, name='upper_arm'),
          pin(0.011, 0.03, (0, 0, -0.057)),
          part((0.033, 0.039, 0.047), (0, 0, -0.082), blue_m, bevel=0.0045, name='forearm'),
          part((0.035, 0.041, 0.008), (0, 0, -0.1), yellow_m, bevel=0.002, name='wrist_band'),
          part((0.03, 0.035, 0.027), (0, -0.002, -0.118), gun_m, bevel=0.008, seg=4, name='fist')]
    for k in range(3):
        ps.append(part((0.024, 0.002, 0.0012), (0, -0.0195, -0.112 - k * 0.0055), dark_m, bevel=0.0004,
                       name='knuckle'))
    if light:
        ps.append(part((0.009, 0.003, 0.009), (0, -0.0205, -0.08), visor_m, bevel=0.0012, name='forearm_light'))
        ps.append(part((0.013, 0.002, 0.013), (0, -0.0195, -0.08), gun_m, bevel=0.0008, name='light_bezel'))
    for p in ps:
        p.parent = root
    return root


arm(-1, 0, light=True)          # robot's right arm hangs at its side
left = arm(1, 16)               # robot's left arm brings the sword forward
# sword in the left fist, held level across the legs, tip a little up and forward
fist_z, fist_y = -0.118, -0.002
sw = bpy.data.objects.new('sword', None); bpy.context.collection.objects.link(sw)
sw.parent = left; sw.location = (0, fist_y, fist_z)
sw.rotation_euler = (math.radians(16), math.radians(8), math.radians(8))   # undo the arm swing, then pitch and yaw
parts = [kit.cyl(0.0048, 0.044, at=(0.002, 0, 0), rot=(0, 90, 0), material=kit.mat('#5a3a22', rough=0.6), verts=16,
                 name='grip'),
         kit.sphere(0.0068, at=(0.026, 0, 0), material=brass_m, segs=20, rings=10, name='pommel'),
         part((0.006, 0.011, 0.034), (-0.0195, 0, 0), brass_m, bevel=0.002, name='guard')]
blade = kit.extrude([(-0.0225, -0.0062), (-0.142, -0.0062), (-0.162, 0.0), (-0.142, 0.0062), (-0.0225, 0.0062)],
                    0.0028, material=chrome_m, bevel=0.0009, segments=2, name='blade')
blade.rotation_euler = (math.radians(90), 0, 0); blade.location = (0, 0.0014, 0)
parts += [blade, part((0.11, 0.0034, 0.0016), (-0.08, 0, 0), kit.mat('steel', rough=0.3, metal=0.9), bevel=0.0005,
                      name='fuller')]
for p in parts:
    p.parent = sw

kit.export('japanese-toy-robot')
