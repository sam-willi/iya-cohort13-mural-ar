"""Desk lamp (Art Nouveau), after Grace Li's drawing (RV P4a).

As drawn: a broad glass dome with eight scalloped lobes on a bronze overlay frame: ribs sweeping from the crown to the
cusps, twisted braids with diamond openings running down to the front cusp (and, by symmetry, the side and back cusps),
poppies on S-shaped tendrils with serrated leaves on the side panels, "IYA" and "XIII" lettered along the two front
lobes, a small crown finial, a pull chain with a ball, a collar under the shade, a fluted baluster stem and a round foot
with radial ribs.
Colours (the drawing is pencil): caramel slag glass that glows, aged bronze, red glass poppies. The back panels repeat the
side pattern without letters.
"""
import sys, os, math, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit
kit.reset()
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

TMP = tempfile.gettempdir()

# ---------------------------------------------------------------- shade surface S(theta, phi)
R, H, ZC = 0.21, 0.235, 0.372        # dome: radius, height above the widest ring, widest ring height
Z_CUSP, LOBE = 0.36, 0.03            # eight scalloped lobes
PHI_TOP = 0.14                       # leave the crown for the bronze cap
PEXP = 0.78                          # <1 broadens the crown, like the drawing's mushroom dome


def prof(ph):
    c = math.cos(ph)
    z = ZC + H * (abs(c) ** PEXP) * (1 if c >= 0 else -1) if c >= 0 else ZC + H * c
    return R * math.sin(ph), z


def S(th, ph):
    r, z = prof(ph)
    return Vector((r * math.sin(th), -r * math.cos(th), z))


def Nrm(th, ph):
    e = 1e-4
    r0, z0 = prof(max(ph - e, 1e-4)); r1, z1 = prof(ph + e)
    dr, dz = r1 - r0, z1 - z0
    nr, nz = dz, -dr
    l = math.hypot(nr, nz); nr, nz = -nr / l, -nz / l
    if nr < 0:
        nr, nz = -nr, -nz
    return Vector((nr * math.sin(th), -nr * math.cos(th), nz))


def speed(ph):
    e = 1e-4
    r0, z0 = prof(max(ph - e, 1e-4)); r1, z1 = prof(ph + e)
    return math.hypot(r1 - r0, z1 - z0) / (ph + e - max(ph - e, 1e-4))


def z_edge(th):
    f = (th % (math.pi / 4)) / (math.pi / 4)
    return Z_CUSP - LOBE * math.sin(math.pi * f) ** 0.75


def phi_edge(th):
    return math.acos(max(-1, min(1, (z_edge(th) - ZC) / H)))   # below the widest ring the profile is a plain ellipse


def SP(th, ph, off=0.0):
    return S(th, ph) + Nrm(th, ph) * off


# ---------------------------------------------------------------- helpers
def mesh_obj(name, verts, faces, material=None, uvs=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            for li in p.loop_indices:
                uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if material is not None:
        o.data.materials.append(material)
    for p in me.polygons:
        p.use_smooth = smooth
    return o


def _catmull(points, subdiv):
    P = [Vector(p) for p in points]
    if len(P) < 3 or subdiv <= 1:
        return P
    out = []
    n = len(P)
    for i in range(n - 1):
        p0 = P[max(i - 1, 0)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(i + 2, n - 1)]
        for k in range(subdiv):
            t = k / subdiv; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return out


def tube(points, r, material=None, sides=8, subdiv=1, closed=False, name='tube'):
    P = _catmull(points, subdiv) if not closed else [Vector(p) for p in points]
    n = len(P)
    rad = (lambda t: r) if not callable(r) else r
    T = [((P[(i + 1) % n] - P[i - 1]) if closed else (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])).normalized() for i in range(n)]
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = (up - T[0] * up.dot(T[0])).normalized()
    verts, faces = [], []
    for i in range(n):
        if i:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-9:
                N = Matrix.Rotation(T[i - 1].angle(T[i]), 3, b.normalized()) @ N
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N); rr = rad(i / max(n - 1, 1))
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(P[i] + (N * math.cos(a) + B * math.sin(a)) * rr)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, j * sides + k2, j * sides + k))
    if not closed:
        c0 = len(verts); verts.append(P[0]); c1 = len(verts); verts.append(P[-1])
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((c0, k2, k)); faces.append((c1, (n - 1) * sides + k, (n - 1) * sides + k2))
    o = mesh_obj(name, verts, faces, material)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return kit.finish(o, None, smooth=55)


def band(path, width, off, thick, material, name='band'):
    """Flat overlay strip along a list of (theta, phi), lying on the glass."""
    verts, faces = [], []
    n = len(path)
    for i, (th, ph) in enumerate(path):
        c = SP(th, ph, off)
        a = SP(*path[min(i + 1, n - 1)], off); b = SP(*path[max(i - 1, 0)], off)
        t = (a - b).normalized(); nm = Nrm(th, ph)
        side = nm.cross(t).normalized()
        verts += [c - side * width / 2, c + side * width / 2]
    for i in range(n - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    o = mesh_obj(name, verts, faces, material)
    sd = o.modifiers.new('solid', 'SOLIDIFY'); sd.thickness = thick; sd.offset = 1.0
    return kit.finish(o, None, smooth=40)


def wrap(o, th_c, ph_c, ang=0.0, off=0.002, baseline=None):
    """Bend a flat mesh (local x right, y up, z out; in metres) onto the shade around (th_c, ph_c).
    baseline(th) -> phi lets text follow a curve (the scalloped lobe)."""
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ca, sa = math.cos(ang), math.sin(ang)
    rc = R * math.sin(ph_c)
    for v in o.data.vertices:
        x, y, z = v.co
        u = x * ca - y * sa; w = x * sa + y * ca
        th = th_c + u / rc
        ph0 = baseline(th) if baseline else ph_c
        ph = ph0 - w / speed(ph0)
        v.co = SP(th, ph, off + z)
    o.data.update()
    return o


def flat_poly(poly, thick, material, name):
    o = kit.extrude(poly, thick, material=material, name=name)
    return o


# ---------------------------------------------------------------- materials
def slag_texture(path, size=256, seed=5):
    rng = np.random.default_rng(seed)
    v, u = np.mgrid[0:size, 0:size] / size
    f = np.zeros_like(u)
    for k in range(8):
        fu, fv = rng.integers(1, 5), rng.integers(1, 4)
        f += rng.uniform(0.2, 0.6) * np.sin(2 * np.pi * (fu * u + fv * v + 0.3 * np.sin(2 * np.pi * (rng.integers(1, 3) * v + u))) + rng.uniform(0, 6.3))
    f = (f - f.min()) / (f.max() - f.min())
    streak = np.clip((f - 0.55) * 3, 0, 1) ** 1.5
    deep = np.array([0.62, 0.30, 0.07]); honey = np.array([0.90, 0.60, 0.22]); cream = np.array([0.98, 0.84, 0.55])
    grad = v[..., None]                      # v: 0 at the crown, 1 at the lobes
    base = deep * (1 - grad) * 0.55 + honey * (0.45 + 0.55 * grad)
    rgb = base * (1 - streak[..., None] * 0.6) + cream * streak[..., None] * 0.6
    rgb = np.clip(rgb * (0.9 + 0.15 * f[..., None]), 0, 1)
    img = bpy.data.images.new('slag', size, size)
    px = np.ones((size, size, 4), np.float32); px[..., :3] = rgb[::-1]
    img.pixels = px.ravel(); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return path


slag = slag_texture(os.path.join(TMP, 'nouveau_slag.png'))
M_GLASS = kit.mat('#ffffff', rough=0.3, alpha=0.92, image=slag, name='slag_glass')
nt = M_GLASS.node_tree; bsdf = nt.nodes['Principled BSDF']
texn = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
nt.links.new(texn.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 0.2
M_BRONZE = kit.mat('#7d5a34', rough=0.36, metal=0.85, name='bronze')
M_BRONZE_HI = kit.mat('#a87c45', rough=0.3, metal=0.9, name='bronze_hi')
M_POPPY = kit.mat('#c0392b', rough=0.3, alpha=0.95, emit=0.35, name='poppy_glass')
M_BULB = kit.mat('#fff2d0', rough=0.2, emit=4.0, name='bulb')

# ---------------------------------------------------------------- the glass shell (UV: u around, v crown->lobes)
NT, NS = 128, 22
verts, faces, uvs = [], [], []
for i in range(NT + 1):
    th = 2 * math.pi * i / NT
    pe = phi_edge(th)
    for j in range(NS + 1):
        s = j / NS
        ph = PHI_TOP + (pe - PHI_TOP) * s
        verts.append(S(th, ph)); uvs.append((i / NT * 2, s))
for i in range(NT):
    for j in range(NS):
        a = i * (NS + 1) + j; b = (i + 1) * (NS + 1) + j
        faces.append((a, b, b + 1, a + 1))
shell = mesh_obj('shade_glass', verts, faces, M_GLASS, uvs)
bm = bmesh.new(); bm.from_mesh(shell.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
bm.to_mesh(shell.data); bm.free()

# ---------------------------------------------------------------- frame: lobe rim band, ribs, braids
OFF = 0.0012
rim = [(2 * math.pi * k / 256, phi_edge(2 * math.pi * k / 256) - 0.012) for k in range(257)]
band(rim, 0.016, OFF, 0.0022, M_BRONZE, 'rim_band')
tube([SP(th, phi_edge(th), 0.001) for th in [2 * math.pi * k / 192 for k in range(192)]], 0.0034, M_BRONZE_HI, sides=6,
     closed=True, name='rim_bead')

# ribs on the meridians at +-45 and +-135 degrees, crown to cusp
for k in (1, 3, 5, 7):
    th = k * math.pi / 4
    pe = phi_edge(th)
    path = [(th, PHI_TOP + (pe - 0.012 - PHI_TOP) * t / 40) for t in range(41)]
    band(path, 0.013, OFF, 0.0024, M_BRONZE, 'rib')
    tube([SP(a, b, OFF + 0.0024) for a, b in path], 0.0016, M_BRONZE_HI, sides=5, name='rib_bead')

# braids down the meridians at 0, 90, 180, 270: two strands crossing into diamonds
for k in (0, 2, 4, 6):
    th0 = k * math.pi / 4
    pe = phi_edge(th0)
    p0, p1 = PHI_TOP + 0.05, pe - 0.016
    for sgn in (1, -1):
        pts = []
        for i in range(55):
            t = i / 54
            ph = p0 + (p1 - p0) * t
            half = 0.011 * (0.35 + 0.65 * math.sin(math.pi * min(1, t * 1.15)) ) * (1 - 0.6 * (t > 0.92) * (t - 0.92) / 0.08)
            dth = sgn * half / (R * math.sin(ph)) * math.sin(math.pi * 4.5 * t)
            pts.append(SP(th0 + dth, ph, OFF + 0.002))
        tube(pts, 0.003, M_BRONZE, sides=6, name='braid')
    # spine under the strands + small diamond studs in each opening
    path = [(th0, p0 + (p1 - p0) * t / 30) for t in range(31)]
    band(path, 0.005, OFF, 0.0015, M_BRONZE, 'braid_spine')
    for d in range(4):
        t = (d + 0.5) / 4.5
        ph = p0 + (p1 - p0) * t
        st = kit.extrude([(0, -0.009), (0.0035, 0), (0, 0.009), (-0.0035, 0)], 0.0025, material=M_BRONZE_HI, name='diamond')
        wrap(st, th0, ph, 0.0, OFF + 0.0012)
    # where the braid leaves the crown it splits into two scrolls toward the neighbouring ribs
    for sgn in (1, -1):
        pts = []
        for i in range(25):
            t = i / 24
            ph = PHI_TOP + 0.05 + 0.10 * math.sin(math.pi * t) + 0.02 * t
            th = th0 + sgn * (math.pi / 4) * t * 0.85
            pts.append(SP(th, ph, OFF + 0.0018))
        tube(pts, 0.0024, M_BRONZE, sides=5, name='scroll')

# ---------------------------------------------------------------- floral panels: S-tendrils, serrated leaves, poppies
def leaf_poly(L=0.03, W=0.009, teeth=5):
    pts = []
    for i in range(21):
        t = i / 20
        w = W * math.sin(math.pi * t) ** 0.8 + (0.0018 * abs(math.sin(teeth * math.pi * t)) if 0.1 < t < 0.9 else 0)
        pts.append((t * L - L / 2, w))
    for i in range(19, 0, -1):
        t = i / 20
        w = W * 0.85 * math.sin(math.pi * t) ** 0.8
        pts.append((t * L - L / 2, -w))
    return pts


def poppy(th, ph, size, droop=0.0, name='poppy'):
    for k in range(5):
        b = 2 * math.pi * k / 5 + 0.3
        pet = [(size * 0.55 * math.cos(a) + size * 0.55, size * 0.42 * math.sin(a) * (1 + 0.25 * math.cos(3 * a))) for a in
               [2 * math.pi * q / 14 for q in range(14)]]
        rot = [(x * math.cos(b) - y * math.sin(b), x * math.sin(b) + y * math.cos(b) + droop * size) for x, y in pet]
        o = kit.extrude(rot, 0.0018, material=M_POPPY, name=name + '_petal')
        wrap(o, th, ph, 0.0, OFF + 0.0015 + 0.0004 * k)
        # bronze outline round each petal
        pts = [SP(th + (x * 1.0) / (R * math.sin(ph)), ph - y / speed(ph), OFF + 0.0035 + 0.0004 * k) for x, y in rot]
        tube(pts, 0.0013, M_BRONZE, sides=4, closed=True, name=name + '_edge')
    c = kit.sphere(0.0045, material=M_BRONZE_HI, segs=12, rings=8, name=name + '_heart')
    c.location = SP(th, ph, OFF + 0.006)


def floral(th_a, mirror):
    """One panel's motif. th_a: the rib it grows from; mirror=+1 grows toward increasing theta."""
    def T(dt):
        return th_a + mirror * dt
    # the S-tendril, crown to lower panel
    ctrl = [(T(0.10), PHI_TOP + 0.14), (T(0.26), 0.50), (T(0.12), 0.85), (T(0.20), 1.18), (T(0.42), 1.40)]
    pts = []
    for i in range(len(ctrl)):
        pts.append(SP(ctrl[i][0], ctrl[i][1], OFF + 0.0022))
    tube(pts, lambda t: 0.0048 - 0.002 * t, M_BRONZE, sides=6, subdiv=10, name='tendril')
    # a second, shorter stem that hangs a bud near the crown (the drawing's top flowers)
    bud = [(T(0.14), PHI_TOP + 0.10), (T(0.30), 0.36), (T(0.36), 0.56)]
    tube([SP(a, b, OFF + 0.002) for a, b in bud], 0.003, M_BRONZE, sides=6, subdiv=8, name='bud_stem')
    poppy(T(0.36), 0.66, 0.021, droop=0.0, name='bud')
    # serrated leaves along the tendril
    for (dt, ph, ang) in ((0.20, 0.70, 60), (0.13, 0.98, -50), (0.30, 1.30, 20)):
        lf = kit.extrude(leaf_poly(0.05, 0.012), 0.0018, material=M_BRONZE, name='leaf')
        wrap(lf, T(dt), ph, math.radians(ang) * mirror, OFF + 0.0016)
    # the big poppy at the end of the tendril
    poppy(T(0.45), 1.30, 0.032, name='poppy')


for rib_k in (1, 3, 5, 7):
    th_r = rib_k * math.pi / 4
    # panels either side of the side braids (90 and 270 degrees): grow from the 45/135/225/315 ribs toward the braid
    toward = 1 if rib_k in (1, 5) else -1
    floral(th_r, toward)

# ---------------------------------------------------------------- IYA and XIII along the two front lobes
def letters(s, th_c, size):
    bpy.ops.object.text_add()
    t = bpy.context.object
    t.data.body = s; t.data.size = size; t.data.extrude = 0.002; t.data.align_x = 'CENTER'; t.data.align_y = 'CENTER'
    t.data.space_character = 1.15
    bpy.ops.object.convert(target='MESH')
    t = bpy.context.object; t.name = 'letters_' + s
    t.data.materials.append(M_BRONZE_HI)
    # sit the letters along the lobe, just above the rim band, following its curve
    wrap(t, th_c, phi_edge(th_c) - 0.09, 0.0, OFF + 0.0024, baseline=lambda th: phi_edge(th) - 0.095)
    return t


letters('IYA', -math.pi / 8, 0.036)
letters('XIII', math.pi / 8, 0.036)

# ---------------------------------------------------------------- crown cap and finial
cap_prof = [(0.0, ZC + H + 0.004)]
for i in range(1, 9):
    ph = PHI_TOP * 1.25 * i / 8
    p = S(0, ph) + Nrm(0, ph) * 0.003
    cap_prof.append((math.hypot(p.x, p.y), p.z))
cap_prof += [(cap_prof[-1][0], cap_prof[-1][1] - 0.008), (0.0, cap_prof[-1][1] - 0.008)]
kit.lathe(cap_prof, material=M_BRONZE, steps=64, name='crown_cap')
kit.torus(R * math.sin(PHI_TOP * 1.25) + 0.001, 0.0035, at=(0, 0, S(0, PHI_TOP * 1.25).z + 0.001), material=M_BRONZE_HI,
          major=48, minor=6, name='crown_ring')
kit.lathe([(0.0, ZC + H), (0.017, ZC + H), (0.019, ZC + H + 0.006), (0.019, ZC + H + 0.014), (0.015, ZC + H + 0.016),
           (0.0, ZC + H + 0.016)], material=M_BRONZE_HI, steps=40, name='finial')
kit.torus(0.019, 0.0025, at=(0, 0, ZC + H + 0.016), material=M_BRONZE, major=40, minor=8, name='finial_ring')

# ---------------------------------------------------------------- inside: harp, socket, bulb
kit.cyl(0.006, ZC + H - 0.3, at=(0, 0, (ZC + H + 0.3) / 2), material=M_BRONZE, verts=16, name='center_rod')
kit.cyl(0.017, 0.045, at=(0, 0, 0.405), material=M_BRONZE_HI, verts=32, bevel=0.003, name='socket')
kit.sphere(0.032, at=(0, 0, 0.465), scale=(1, 1, 1.15), material=M_BULB, segs=24, rings=12, name='bulb')
for k in range(3):
    a = 2 * math.pi * k / 3
    tube([(0, 0, 0.395), (0.09 * math.cos(a), 0.09 * math.sin(a), 0.43), (S(a + math.pi / 2, 1.2) * 0.985).to_tuple()],
         0.0022, M_BRONZE, sides=6, subdiv=6, name='spider_arm')

# ---------------------------------------------------------------- stem: rod, collar, fluted baluster
def fluted_lathe(profile, flutes, depth, steps, material, name):
    verts, faces = [], []
    n = len(profile)
    for k in range(steps):
        a = 2 * math.pi * k / steps
        m = 1 - depth * (0.5 + 0.5 * math.cos(flutes * a)) ** 3
        for r, z, f in profile:
            rr = r * (1 - (1 - m) * f)
            verts.append((rr * math.cos(a), rr * math.sin(a), z))
    for k in range(steps):
        k2 = (k + 1) % steps
        for i in range(n - 1):
            faces.append((k * n + i, k2 * n + i, k2 * n + i + 1, k * n + i + 1))
    o = mesh_obj(name, verts, faces, material)
    top = [k * n + n - 1 for k in range(steps)]; bot = [k * n for k in range(steps)]
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    bm.faces.new([bm.verts[i] for i in top]); bm.faces.new([bm.verts[i] for i in bot][::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return kit.finish(o, None, smooth=50)


kit.cyl(0.0095, 0.08, at=(0, 0, 0.335), material=M_BRONZE, verts=24, name='stem_rod')
kit.lathe([(0.0, 0.287), (0.021, 0.287), (0.024, 0.292), (0.024, 0.304), (0.021, 0.309), (0.0, 0.309)], material=M_BRONZE_HI,
          steps=48, name='collar')
bal = []
for i in range(29):
    t = i / 28
    z = 0.287 - (0.287 - 0.062) * t
    # vase: narrow top, swelling at 1/3, long taper to the neck
    r = 0.016 + 0.017 * math.sin(math.pi * min(1, t / 0.75)) ** 1.4 * (1 if t < 0.75 else 0) - 0.002 * t
    bal.append((max(r, 0.014), z, 1.0))
bal += [(0.016, 0.055, 0.4), (0.022, 0.048, 0.0), (0.03, 0.043, 0.0)]
bal = list(reversed(bal))
fluted_lathe(bal, 12, 0.10, 72, M_BRONZE, 'baluster')

# ---------------------------------------------------------------- foot: round, gently domed, sixteen radial ribs
foot = []
steps = 160
prof = [(0.0, 0.043), (0.03, 0.041), (0.06, 0.034), (0.10, 0.025), (0.125, 0.019), (0.132, 0.015), (0.134, 0.006),
        (0.13, 0.0), (0.0, 0.0)]
verts, faces = [], []
n = len(prof)
for k in range(steps):
    a = 2 * math.pi * k / steps
    rib = max(0.0, math.cos(16 * a)) ** 10
    for i, (r, z) in enumerate(prof):
        lift = 0.0022 * rib if 1 <= i <= 4 else 0.0
        verts.append((r * math.cos(a), r * math.sin(a), z + lift))
for k in range(steps):
    k2 = (k + 1) % steps
    for i in range(n - 1):
        faces.append((k * n + i, k2 * n + i, k2 * n + i + 1, k * n + i + 1))
fo = mesh_obj('foot', verts, faces, M_BRONZE)
bm = bmesh.new(); bm.from_mesh(fo.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(fo.data); bm.free()
kit.finish(fo, None, smooth=40)

# ---------------------------------------------------------------- pull chain with a ball (front left, as drawn)
cx, cy = -0.07, -0.05
ztop = 0.40
for i in range(26):
    kit.sphere(0.0024, at=(cx, cy, ztop - i * 0.0046), material=M_BRONZE_HI, segs=6, rings=4, name='chain_bead')
kit.sphere(0.0095, at=(cx, cy, ztop - 26 * 0.0046 - 0.008), material=M_BRONZE_HI, segs=20, rings=12, name='pull_ball')

kit.export('art-nouveau-desk-lamp')
