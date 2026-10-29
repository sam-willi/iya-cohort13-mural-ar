"""Top hat (Lana Kim). Her hat is square-cornered, not round: a rounded-square crown on a wide rounded-square brim
with a rolled, dark-bound edge, a dark band at the crown's foot with a crescent-moon-and-star brooch, and a little
cube on the crown carrying a flag on a stick. The drawing only shades the band and the brim edge, so the felt is light."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import kit; kit.reset()
import bpy, bmesh, math
import numpy as np


def rsq_ring(a, b, r, d, n):
    pts = []
    cs = ((a - r, b - r), (-(a - r), b - r), (-(a - r), -(b - r)), (a - r, -(b - r)))
    for k, (cx, cy) in enumerate(cs):
        for i in range(n + 1):
            t = math.radians(90 * k + 90 * i / n)
            pts.append((cx + (r + d) * math.cos(t), cy + (r + d) * math.sin(t)))
    return pts


def rsq_lathe(a, b, r, profile, mats, seg_mat=None, n=10, cap0=False, cap1=False, cap_mat=(0, 0), name='rsq'):
    """'Lathe' a profile [(offset, z), ...] around a rounded rectangle (half sizes a, b, corner radius r).
    mats: list of materials; seg_mat[i] picks the material of profile segment i."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for x, y in rsq_ring(a, b, r, d, n)] for d, z in profile]
    m = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(m):
            f = bm.faces.new((rings[i][j], rings[i][(j + 1) % m], rings[i + 1][(j + 1) % m], rings[i + 1][j]))
            f.material_index = seg_mat[i] if seg_mat else 0
    if cap0:
        f = bm.faces.new(rings[0][::-1]); f.material_index = cap_mat[0]
    if cap1:
        f = bm.faces.new(rings[-1]); f.material_index = cap_mat[1]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for mt in mats:
        o.data.materials.append(mt)
    return kit.finish(o, None, smooth=40)


def crescent(R, R2, off, tilt, n=40):
    """Crescent opening to +x: circle R at origin minus circle R2 centred at (off, 0)."""
    # intersection angle on the outer circle
    cx = (R * R - R2 * R2 + off * off) / (2 * off)
    a0 = math.acos(max(-1, min(1, cx / R)))
    b0 = math.atan2(math.sqrt(max(0, R * R - cx * cx)), cx - off)
    pts = [(R * math.cos(t), R * math.sin(t)) for t in np.linspace(a0, math.tau - a0, n)]
    pts += [(off + R2 * math.cos(t), R2 * math.sin(t)) for t in np.linspace(math.tau - b0, b0, n)[1:-1]]
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def faceted_star(R, r_in, h_front, h_back, rot_deg, name, material):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ring = []
    for i in range(10):
        t = math.radians(90 + rot_deg + i * 36)
        rr = R if i % 2 == 0 else r_in
        ring.append(bm.verts.new((rr * math.cos(t), rr * math.sin(t), 0)))
    fa = bm.verts.new((0, 0, h_front)); ba = bm.verts.new((0, 0, -h_back))
    for i in range(10):
        bm.faces.new((ring[i], ring[(i + 1) % 10], fa))
        bm.faces.new((ring[(i + 1) % 10], ring[i], ba))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.data.materials.append(material)
    return o   # flat shaded: the drawing shows the facets


felt = kit.mat('#252220', rough=0.5, name='felt')            # black silk-plush felt
binding = kit.mat('#141312', rough=0.32, name='binding')      # satin edge binding, a touch glossier
ribbon = kit.mat('cardinal', rough=0.6, name='ribbon')        # grosgrain band
brass = kit.mat('brass', rough=0.28, metal=0.9, name='brass')
oak = kit.mat('oak', rough=0.6, name='oak')
pole_m = kit.mat('black', rough=0.4, name='pole')
flag_m = kit.mat('red', rough=0.7, name='flag')

# ---------- brim: wide rounded square sweeping gently up to a rolled, bound edge ----------
BA, BRr = 0.19, 0.085
BT = 0.0048  # brim top where the crown sits
brim_prof = [(-0.075, 0.0), (-0.05, 0.0008), (-0.03, 0.003), (-0.015, 0.006), (-0.005, 0.0092), (0.0, 0.0108),
             (0.004, 0.0118), (0.0078, 0.0145), (0.0078, 0.019), (0.005, 0.0222), (0.001, 0.0222), (-0.002, 0.0205),
             (-0.006, 0.0175), (-0.015, 0.0135), (-0.03, 0.0095), (-0.05, 0.0062), (-0.075, BT)]
brim = rsq_lathe(BA, BA, BRr, brim_prof, [felt, binding],
                 seg_mat=[0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0], n=12,
                 cap0=True, cap1=True, cap_mat=(0, 0), name='brim')

# ---------- crown: straight-sided as drawn, flaring a few millimetres toward a crisp top ----------
CA, CR, CH = 0.09, 0.04, 0.2
crown_prof = [(0, BT - 0.002), (0.0, BT + 0.05), (0.0018, CH * 0.6), (0.004, CH - 0.008), (0.0032, CH - 0.0028),
              (0.0012, CH - 0.0004), (-0.003, CH), (-0.02, CH + 0.0004)]
crown = rsq_lathe(CA, CA, CR, crown_prof, [felt], n=12, cap0=True, cap1=True, name='crown')
TOP = CH + 0.0004

# ---------- band: dark grosgrain ribbon around the foot of the crown ----------
BH = 0.042
band_prof = [(-0.002, BT + 0.0005), (0.0024, BT + 0.0012), (0.0032, BT + 0.004), (0.0032, BT + BH - 0.003),
             (0.0024, BT + BH), (-0.002, BT + BH + 0.0006), (-0.002, BT + 0.0005)]
band = rsq_lathe(CA, CA, CR, band_prof, [ribbon], n=12, name='band')
# ---------- crescent moon and star brooch, on the band at the front, left of centre ----------
FY = -(CA + 0.0032)
moon = kit.extrude(crescent(0.04, 0.034, 0.016, -14), 0.0055, at=(-0.018, FY + 0.0006, BT + 0.047), rot=(90, 0, 0),
                   material=brass, bevel=0.0016, segments=2, name='moon')
star = faceted_star(0.03, 0.013, 0.009, 0.001, 12, 'star', brass)
star.location = (0.022, FY - 0.0035, BT + 0.064); star.rotation_euler = (math.radians(90), 0, 0)
kit.cyl(0.006, 0.006, at=(0.022, FY - 0.0005, BT + 0.064), rot=(90, 0, 0), material=brass, verts=16, name='star_post')

# ---------- the cube on the crown, with its flag on a stick ----------
CS = 0.064
cx, cy = -0.042, 0.004
kit.box((CS, CS, CS), at=(cx, cy, TOP + CS / 2 - 0.0005), material=oak, bevel=0.004, segments=3, name='cube')
PZ0, PL = TOP + CS, 0.2
kit.cyl(0.0028, PL, at=(cx, cy, PZ0 + PL / 2 - 0.002), material=pole_m, verts=16, name='pole')
kit.cyl(0.006, 0.003, at=(cx, cy, PZ0 + 0.0005), material=brass, verts=24, bevel=0.001, name='pole_socket')
kit.sphere(0.0062, at=(cx, cy, PZ0 + PL + 0.003), material=brass, segs=20, rings=10, name='finial')
# flag: a light cloth wave, flying to the right along the front plane (as drawn)
FW, FH = 0.078, 0.064
bpy.ops.mesh.primitive_grid_add(x_subdivisions=14, y_subdivisions=6, size=1)
flag = bpy.context.object; flag.name = 'flag'
for v in flag.data.vertices:
    u = v.co.x + 0.5; w = v.co.y + 0.5
    v.co = (cx + 0.004 + u * FW, cy + 0.006 * math.sin(u * math.pi * 1.6) * u, PZ0 + PL - 0.006 - FH + w * FH)
kit.finish(flag, flag_m)
sol = flag.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.0016; sol.offset = 0
# two little stitched sleeves tying the flag to the stick
for z in (PZ0 + PL - 0.012, PZ0 + PL - 0.064):
    kit.cyl(0.0042, 0.006, at=(cx, cy, z), material=flag_m, verts=16, name='sleeve')

kit.export('top-hat-2')
