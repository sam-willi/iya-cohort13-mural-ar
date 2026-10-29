"""Exercise weights - no student drawing in the folder, so a generic pair.

A pair of rubber hex dumbbells: one lying on a flat of its hexes, one stood on end beside it (gives the pair a
silhouette that reads at a glance while it spins, and some height in the lens). Knurled chrome handles, chrome
collars, steel end caps with a cardinal inset. No lettering.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy

kit.reset()

R = 0.072                  # hex circumradius
RI = R * math.cos(math.radians(30))
HL = 0.062                 # head length
GL = 0.128                 # handle length between the heads
HR = 0.0165                # handle radius

rubber_m = kit.mat('#222224', rough=0.8, name='rubber')
chrome_m = kit.mat('chrome', rough=0.22, metal=0.95, name='chrome')
knurl_m = kit.mat('#8d939b', rough=0.5, metal=0.9, name='knurl')
steel_m = kit.mat('steel', rough=0.35, metal=0.9, name='steel')
accent_m = kit.mat('cardinal', rough=0.45, name='accent')


def hexagon(r):
    return [(r * math.cos(math.radians(30 + 60 * k)), r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]


def dumbbell(name):
    """Built along +x, centred on the origin, flat of the hexes facing -z. Returns its parts."""
    parts = []
    for s in (-1, 1):
        x0 = s * (GL / 2)                                   # inner face of the head
        head = kit.extrude(hexagon(R), HL, material=rubber_m, bevel=0.007, segments=3, name=name + '_head')
        head.rotation_euler = (0, math.radians(90), 0)
        head.location = (x0 if s > 0 else x0 - HL, 0, 0)
        parts.append(head)
        # steel end cap set into a shallow recess in the rubber, with a cardinal inset and a bolt (all below the
        # rubber face, so a dumbbell stood on end sits on its rubber)
        xe = s * (GL / 2 + HL)
        bpy.ops.object.select_all(action='DESELECT'); head.select_set(True); bpy.context.view_layer.objects.active = head
        bpy.ops.object.modifier_apply(modifier='bevel')
        kit.boolean(head, kit.cyl(0.042, 0.008, at=(xe, 0, 0), rot=(0, 90, 0), verts=48))
        md = head.modifiers.new('b2', 'BEVEL'); md.width = 0.0012; md.segments = 2; md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(50)
        parts.append(kit.cyl(0.041, 0.004, at=(xe - s * 0.0045, 0, 0), rot=(0, 90, 0), material=steel_m,
                             bevel=0.001, verts=48))
        parts.append(kit.cyl(0.03, 0.001, at=(xe - s * 0.0023, 0, 0), rot=(0, 90, 0), material=accent_m, verts=48))
        parts.append(kit.cyl(0.009, 0.003, at=(xe - s * 0.0025, 0, 0), rot=(0, 90, 0), material=chrome_m,
                             bevel=0.0008, verts=6))
        # chrome collar where the handle meets the head
        parts.append(kit.lathe([(0.0, 0.0), (0.03, 0.0), (0.03, 0.004), (0.024, 0.01), (0.0, 0.01)],
                               at=(s * GL / 2, 0, 0), rot=(0, -90 * s, 0), material=chrome_m, steps=48))
    # handle: smooth ends, a knurled grip with ring grooves in the middle
    prof = [(0.0, -GL / 2 - 0.01), (HR, -GL / 2 - 0.01), (HR, -0.047)]
    n = 40   # fine, shallow rings: reads as a knurled band at phone scale rather than a thread
    for k in range(n + 1):
        z = -0.045 + 0.09 * k / n
        prof += [(HR - 0.0001, z - 0.0007), (HR - 0.0006, z), (HR - 0.0001, z + 0.0007)] if 0 < k < n else [(HR, z)]
    prof += [(HR, 0.047), (HR, GL / 2 + 0.01), (0.0, GL / 2 + 0.01)]
    grip = kit.lathe(prof, rot=(0, 90, 0), material=knurl_m, steps=28, name=name + '_grip')
    parts.append(grip)
    for s in (-1, 1):   # polished bands between the grip and the collars
        parts.append(kit.cyl(HR + 0.0004, 0.014, at=(s * 0.054, 0, 0), rot=(0, 90, 0), material=chrome_m, verts=40))
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    for p in parts:
        p.parent = root
    return root


lying = dumbbell('lying')
lying.location = (0.0, -0.06, RI)
lying.rotation_euler = (0, 0, math.radians(8))
standing = dumbbell('standing')
standing.rotation_euler = (0, math.radians(-90), math.radians(25))   # stood on one end cap
standing.location = (0.03, 0.105, GL / 2 + HL)

kit.export('exercise-weights')
