"""Boom box - Daniel Thomas.

His drawing: a long, shallow box (W:H:D about 1 : 0.38 : 0.26) with a thin control strip along the top of the
front, two small speakers set low on either side, a tall centre panel (cassette window with two reel hubs, a
display with a sine wave, three round buttons beside three bar keys) and a flat, squared-off U handle standing
on top. Line-only, so the finish is an 80s gunmetal body with a brushed-aluminium top cap and amber display.
Invented: back (battery door, screws, AC socket, vent slots), side jack, rubber feet.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit
import math, bpy

kit.reset()


def bake(o):
    """Apply o's modifiers now (so later boolean cuts don't inherit its big bevel)."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def edge_bevel(o, w, seg=2, angle=60):
    """After cuts: mark the new hard edges sharp and give only those (> angle) a small bevel."""
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30), keep_sharp_edges=True)
    md = o.modifiers.new('bevel2', 'BEVEL'); md.width = w; md.segments = seg
    md.limit_method = 'ANGLE'; md.angle_limit = math.radians(angle)
    return o

W, D, H = 0.62, 0.16, 0.235
CAP = 0.024            # height of the aluminium top cap
FY = -D / 2            # front face plane
SZ = 0.082             # speaker centre height (a third of H, as drawn)
SK = 0.8               # speaker scale vs. first pass

body_m = kit.mat('gunmetal', rough=0.42, name='body')
cap_m = kit.mat('chrome', rough=0.32, metal=0.8, name='alu')
black_m = kit.mat('black', rough=0.5, name='black')
cone_m = kit.mat('#2a2826', rough=0.75, name='cone')
rubber_m = kit.mat('rubber', rough=0.85, name='rubber')
chrome_m = kit.mat('chrome', rough=0.22, metal=0.95, name='chrome')
glass_m = kit.mat('#101214', rough=0.08, name='smoked')
amber_m = kit.mat('amber', rough=0.4, emit=2.5, name='wave')
cream_m = kit.mat('cream', rough=0.45, name='key')
red_m = kit.mat('red', rough=0.4, name='redkey')
orange_m = kit.mat('orange', rough=0.4, name='orangekey')
tape_m = kit.mat('#3a2a1e', rough=0.6, name='tape')
white_m = kit.mat('white', rough=0.5, name='hub')


def rrect(w, h, r, n=6, cx=0.0, cy=0.0):
    """Rounded rectangle polygon (CCW) centred on (cx, cy)."""
    pts = []
    for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oy = cx + qx * (w / 2 - r), cy + qy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    return pts


def front_plate(w, h, t, x, z, material, r=0.004, bevel=0.0012, y=FY):
    """A rounded-rectangle plate lying on the front face (normal -Y), t thick, outer face at y - t."""
    o = kit.extrude(rrect(w, h, r), t, material=material, bevel=bevel, segments=2)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.location = (x, y, z)
    return o


# ---------------------------------------------------------------- shell
body = kit.box((W, D, H - CAP - 0.002), at=(0, 0, (H - CAP - 0.002) / 2), material=body_m, bevel=0.008, segments=3,
               name='body')
core = kit.box((W - 0.01, D - 0.01, 0.02), at=(0, 0, H - CAP - 0.004), material=black_m, name='seam_core')
cap = kit.box((W, D, CAP), at=(0, 0, H - CAP / 2), material=cap_m, bevel=0.006, segments=3, name='cap')
bake(body); bake(cap)

# speaker recesses and the centre-panel recess, cut into the front
for sx in (-0.2, 0.2):
    c = kit.cyl(0.064 * SK, 0.03, at=(sx, FY, SZ), rot=(90, 0, 0), verts=48)
    kit.boolean(body, c)
c = kit.box((0.138, 0.012, 0.176), at=(0, FY, 0.0185 + 0.088))
kit.boolean(body, c)

# ---------------------------------------------------------------- speakers
for sx in (-0.2, 0.2):
    # cone: concave paper cone + rubber surround, revolved about the speaker axis
    # rotation (90,0,0) maps profile z to -y: negative z goes into the body
    cone = kit.lathe([(0.0, -0.0085), (0.018 * SK, -0.0085), (0.03 * SK, -0.006), (0.044 * SK, -0.003),
                      (0.05 * SK, -0.001), (0.054 * SK, 0.0)], material=cone_m, steps=48, name='cone')
    cone.rotation_euler = (math.radians(90), 0, 0); cone.location = (sx, FY + 0.004, SZ)
    sur = kit.torus(0.051 * SK, 0.0028, material=rubber_m, major=48, minor=8, name='surround')
    sur.rotation_euler = (math.radians(90), 0, 0); sur.location = (sx, FY + 0.0042, SZ)
    cap_d = kit.sphere(0.016, scale=(1, 1, 0.45), material=black_m, segs=24, rings=10, name='dustcap')
    cap_d.rotation_euler = (math.radians(90), 0, 0); cap_d.location = (sx, FY + 0.0125, SZ)
    kit.cyl(0.063 * SK, 0.002, at=(sx, FY + 0.014, SZ), rot=(90, 0, 0), material=black_m, verts=32)  # recess floor
    # chrome trim ring around the recess lip
    ring = kit.lathe([(0.0555 * SK, -0.001), (0.0555 * SK, 0.003), (0.058 * SK, 0.0045), (0.064 * SK, 0.0045),
                      (0.0665 * SK, 0.003), (0.0665 * SK, -0.001)], material=chrome_m, steps=48, name='trim')
    ring.rotation_euler = (math.radians(90), 0, 0); ring.location = (sx, FY + 0.0005, SZ)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        kit.cyl(0.0019, 0.002, at=(sx + 0.061 * SK * math.cos(a), FY - 0.0045, SZ + 0.061 * SK * math.sin(a)),
                rot=(90, 0, 0), material=black_m, verts=12)

# ---------------------------------------------------------------- centre panel
panel = front_plate(0.132, 0.17, 0.004, 0, 0.0185 + 0.088, black_m, r=0.005, y=FY + 0.006)
# cassette door: frame, smoked window, tape and the two reel hubs
door = front_plate(0.11, 0.058, 0.003, 0, 0.158, body_m, r=0.004, y=FY + 0.002)
win = front_plate(0.078, 0.03, 0.001, 0, 0.16, glass_m, r=0.006, bevel=0.0, y=FY - 0.0005)
for hx in (-0.021, 0.021):
    kit.cyl(0.0115, 0.001, at=(hx, FY - 0.0012, 0.16), rot=(90, 0, 0), material=tape_m, verts=32)
    kit.cyl(0.0062, 0.0016, at=(hx, FY - 0.0018, 0.16), rot=(90, 0, 0), material=white_m, verts=6)
    kit.cyl(0.0028, 0.002, at=(hx, FY - 0.002, 0.16), rot=(90, 0, 0), material=black_m, verts=12)
kit.box((0.03, 0.002, 0.005), at=(0, FY - 0.0005, 0.136), material=black_m, bevel=0.0008)  # door finger lip

# display with the sine wave
bezel = front_plate(0.11, 0.05, 0.002, 0, 0.1035, body_m, r=0.004, bevel=0.0006, y=FY + 0.0025)
disp = front_plate(0.102, 0.042, 0.001, 0, 0.1035, glass_m, r=0.003, bevel=0.0, y=FY + 0.001)
pts = []
for i in range(17):
    t = i / 16
    pts.append((-0.045 + 0.09 * t, FY - 0.0005, 0.1035 + 0.0145 * math.sin(t * math.tau * 1.25 + 0.6)))
kit.tube(pts, 0.0011, material=amber_m, bevel_res=4, name='wave')

# lower block: three round buttons in a column, three bar keys beside them
for k in range(3):
    z = 0.068 - k * 0.019
    kit.cyl(0.0042, 0.006, at=(-0.045, FY + 0.0015, z), rot=(90, 0, 0), material=chrome_m, bevel=0.0008, verts=24)
    kit.box((0.06, 0.006, 0.0048), at=(0.012, FY + 0.0015, z), material=cream_m if k else orange_m, bevel=0.0012,
            segments=2)

# ---------------------------------------------------------------- control strip on the cap front
CZ = H - CAP / 2
CY = FY
for side in (-1, 1):
    # big tuning / volume dial with knurled skirt
    dial = kit.cyl(0.0105, 0.009, at=(side * 0.27, CY - 0.0035, CZ), rot=(90, 0, 0), material=black_m, bevel=0.0012,
                   verts=40)
    kit.cyl(0.0075, 0.0012, at=(side * 0.27, CY - 0.0085, CZ), rot=(90, 0, 0), material=chrome_m, verts=32)
    for k in range(2):
        kit.cyl(0.0042, 0.004, at=(side * (0.243 - k * 0.016), CY - 0.0012, CZ), rot=(90, 0, 0), material=black_m,
                bevel=0.0008, verts=20)
    # slider slot with a small knob
    slot = kit.box((0.05, 0.004, 0.005), at=(side * 0.175, CY, CZ))
    kit.boolean(cap, slot)
    kit.box((0.05, 0.002, 0.0045), at=(side * 0.175, CY + 0.0015, CZ), material=black_m)
    kit.box((0.007, 0.007, 0.011), at=(side * (0.175 - side * 0.01), CY - 0.0015, CZ), material=black_m, bevel=0.0015)
    # three level LEDs
    for k in range(3):
        kit.cyl(0.0016, 0.002, at=(side * (0.124 - k * 0.008), CY - 0.0005, CZ), rot=(90, 0, 0),
                material=amber_m if k == 0 else kit.mat('#5a3a22', rough=0.3), verts=12)
# piano keys over the centre panel
for k, m in enumerate((cream_m, cream_m, cream_m, red_m)):
    x = -0.042 + k * 0.028
    kit.box((0.022, 0.016, 0.012), at=(x, CY, CZ - 0.002), material=m, bevel=0.0025, segments=3)
    cut = kit.box((0.025, 0.02, 0.015), at=(x, CY - 0.002, CZ - 0.002))
    kit.boolean(cap, cut)

# ---------------------------------------------------------------- handle
HX, HH, HT, HY = 0.09, 0.078, 0.02, -0.022   # half-width, height above cap, bar thickness, y position
u = [(-HX, 0), (-HX + HT, 0), (-HX + HT, HH - HT), (HX - HT, HH - HT), (HX - HT, 0), (HX, 0), (HX, HH), (-HX, HH)]
handle = kit.extrude(u, 0.018, material=black_m, bevel=0.004, segments=3, name='handle')
handle.rotation_euler = (math.radians(90), 0, 0); handle.location = (0, HY + 0.009, H - 0.004)
grip = kit.box((2 * HX - 2 * HT + 0.004, 0.024, 0.026), at=(0, HY, H - 0.004 + HH - HT / 2), material=rubber_m,
               bevel=0.008, segments=3, name='grip')
bake(grip)
for gx in range(-5, 6):
    g = kit.box((0.0025, 0.03, 0.032), at=(gx * 0.011, HY, H - 0.004 + HH - HT / 2))
    kit.boolean(grip, g)
edge_bevel(grip, 0.0006)
for side in (-1, 1):
    for cy in (-1, 1):   # two cheeks either side of each post, with a pivot pin through them
        kit.box((0.026, 0.005, 0.026), at=(side * (HX - HT / 2), HY + cy * 0.0118, H + 0.009), material=chrome_m,
                bevel=0.002, segments=2, name='cheek')
    kit.cyl(0.0042, 0.03, at=(side * (HX - HT / 2), HY, H + 0.012), rot=(90, 0, 0), material=chrome_m, bevel=0.001,
            verts=20)

# ---------------------------------------------------------------- back
BY = D / 2
door_b = front_plate(0.3, 0.12, 0.003, 0, 0.085, body_m, r=0.008, y=BY)
door_b.rotation_euler = (math.radians(90), 0, math.radians(180)); door_b.location = (0, BY, 0.085)
for k in range(-6, 7):
    kit.box((0.0025, 0.004, 0.03), at=(k * 0.008, BY + 0.003, 0.115), material=black_m, bevel=0.0008)
for sx in (-0.26, 0.26):
    for sz in (0.03, 0.17):
        kit.cyl(0.0035, 0.002, at=(sx, BY + 0.001, sz), rot=(90, 0, 0), material=chrome_m, verts=16)
# AC socket
sock = kit.box((0.024, 0.01, 0.016), at=(0.22, BY, 0.1))
kit.boolean(body, sock)
kit.box((0.022, 0.002, 0.014), at=(0.22, BY - 0.004, 0.1), material=black_m)
for px in (-0.005, 0.005):
    kit.cyl(0.0014, 0.004, at=(0.22 + px, BY - 0.003, 0.1), rot=(90, 0, 0), material=chrome_m, verts=10)
# vent slots
for k in range(7):
    v = kit.box((0.004, 0.012, 0.05), at=(-0.25 + k * 0.009, BY, 0.1))
    kit.boolean(body, v)
kit.box((0.07, 0.002, 0.052), at=(-0.223, BY - 0.0055, 0.1), material=black_m)

# side headphone jack (right end) and a hold switch (left end)
jack = kit.cyl(0.0045, 0.01, at=(W / 2, 0.02, 0.12), rot=(0, 90, 0), verts=24)
kit.boolean(body, jack)
kit.torus(0.0052, 0.0011, at=(W / 2, 0.02, 0.12), rot=(0, 90, 0), material=chrome_m, major=24, minor=8)
kit.cyl(0.0035, 0.002, at=(W / 2 - 0.004, 0.02, 0.12), rot=(0, 90, 0), material=black_m, verts=16)

edge_bevel(body, 0.0012); edge_bevel(cap, 0.0008)

# rubber feet, then lift everything so the feet stand on z=0
for fx in (-0.25, 0.25):
    for fy in (-0.05, 0.05):
        kit.cyl(0.012, 0.004, at=(fx, fy, -0.001), material=rubber_m, bevel=0.0015, verts=24)
for o in bpy.context.scene.objects:
    o.location.z += 0.003

kit.export('boombox')
