"""Tiny CSG-free modeling kit: primitives -> colored parts -> .glb (Y up, +Z = out of the wall)."""
import numpy as np, trimesh
from trimesh import creation as C
from trimesh.transformations import rotation_matrix, translation_matrix
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union

# ---- palette (warm mural palette + material colors) ----
P = dict(
    wood='#8a5a33', darkwood='#5a3820', oak='#b07a45', cream='#f1e4c8', paper='#faf5ea',
    brass='#c9a14a', gold='#e0b04a', copper='#b8733d', steel='#a9adb3', chrome='#d4d7db',
    iron='#3a3a3c', black='#26262a', charcoal='#3d3b3a', white='#f4f2ee', red='#c2412f',
    orange='#e08a2e', teal='#3f8f8f', sky='#9cc9de', glass='#bfe3ee', navy='#2e4a6b',
    green='#5f8a4a', mint='#9fd1b5', pink='#e7a3a8', yellow='#f2c94c', brown='#6b4226',
    leather='#7b4a2c', rubber='#2b2b2b', grey='#7d7f84', lightgrey='#c9c9c9', purple='#7a5aa6',
    tan='#d2b48c', blue='#3b6ea5', lilac='#b9a7d6',
)

def col(c):
    c = P.get(c, c)
    if isinstance(c, str):
        c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)] + [255]
    return list(c) + ([255] if len(c) == 3 else [])

def R(axis, deg):
    ax = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[axis] if isinstance(axis, str) else axis
    return rotation_matrix(np.radians(deg), ax)

class Model:
    def __init__(self, name):
        self.name = name; self.parts = []
    def add(self, mesh, color='grey', at=(0, 0, 0), rot=None, metal=0.0, rough=0.6, name=None, alpha=1.0):
        m = mesh.copy()
        if rot is not None:
            for r in (rot if isinstance(rot, list) else [rot]):
                m.apply_transform(R(*r))
        m.apply_translation(at)
        c = col(color); c[3] = int(alpha * 255)
        self.parts.append(dict(mesh=m, color=c, metal=metal, rough=rough, name=name or f'part{len(self.parts)}'))
        return m
    # convenience
    def box(self, size, at=(0, 0, 0), color='grey', **k): return self.add(C.box(extents=size), color, at, **k)
    def rbox(self, size, r, at=(0, 0, 0), color='grey', **k): return self.add(rounded_box(size, r), color, at, **k)
    def cyl(self, r, h, at=(0, 0, 0), color='grey', axis='y', seg=40, **k):
        m = C.cylinder(radius=r, height=h, sections=seg)  # along z
        m.apply_transform(_axis_from_z(axis)); return self.add(m, color, at, **k)
    def cone(self, r1, r2, h, at=(0, 0, 0), color='grey', axis='y', seg=40, **k):
        m = lathe([(0, 0), (r1, 0), (r2, h), (0, h)], seg); m.apply_translation([0, -h / 2, 0])
        m.apply_transform(_axis_from_y(axis)); return self.add(m, color, at, **k)
    def sph(self, r, at=(0, 0, 0), color='grey', scale=(1, 1, 1), **k):
        m = C.icosphere(subdivisions=3, radius=r); m.apply_scale(scale); return self.add(m, color, at, **k)
    def tor(self, R_, r, at=(0, 0, 0), color='grey', axis='y', **k):
        m = C.torus(major_radius=R_, minor_radius=r, major_sections=48, minor_sections=16)  # ring in xy, axis z
        m.apply_transform(_axis_from_z(axis)); return self.add(m, color, at, **k)
    def lathe(self, prof, at=(0, 0, 0), color='grey', axis='y', seg=48, **k):
        m = lathe(prof, seg); m.apply_transform(_axis_from_y(axis)); return self.add(m, color, at, **k)
    def ext(self, poly, depth, at=(0, 0, 0), color='grey', **k):
        return self.add(extrude(poly, depth), color, at, **k)
    def tube(self, pts, r, color='grey', seg=16, closed=False, **k):
        return self.add(tube(pts, r, seg, closed), color, (0, 0, 0), **k)
    def text(self, s, size, depth, at=(0, 0, 0), color='black', **k):
        return self.add(text_mesh(s, size, depth), color, at, **k)
    def rod(self, a, b, r, color='grey', seg=16, **k):
        return self.add(rod(a, b, r, seg), color, (0, 0, 0), **k)

    def export(self, path, fit=1.0, yaw=0.0):
        sc = trimesh.Scene()
        allv = np.vstack([p['mesh'].vertices for p in self.parts])
        lo, hi = allv.min(0), allv.max(0); ctr = (lo + hi) / 2; s = fit / (hi - lo).max()
        T = np.eye(4); T[:3, :3] *= s; T[:3, 3] = -ctr * s
        if yaw: T = R('y', yaw) @ T
        for p in self.parts:
            m = p['mesh'].copy(); m.apply_transform(T)
            m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=p['color'], metallicFactor=p['metal'], roughnessFactor=p['rough'],
                alphaMode='BLEND' if p['color'][3] < 255 else 'OPAQUE', doubleSided=True, name=p['name']))
            sc.add_geometry(m, node_name=p['name'], geom_name=p['name'])
        sc.metadata['name'] = self.name
        data = trimesh.exchange.gltf.export_glb(sc, include_normals=True)
        open(path, 'wb').write(data)
        return T

def _axis_from_z(axis):
    if axis == 'z': return np.eye(4)
    if axis == 'y': return R('x', -90)
    if axis == 'x': return R('y', 90)
    raise ValueError(axis)

def _axis_from_y(axis):
    if axis == 'y': return np.eye(4)
    if axis == 'z': return R('x', 90)
    if axis == 'x': return R('z', -90)
    raise ValueError(axis)

def lathe(prof, seg=48):
    """prof: list of (radius, y). Revolved around Y."""
    pr = np.array(prof, float)
    m = C.revolve(pr, sections=seg)  # revolves (r, z) around z
    m.apply_transform(R('x', -90))
    m.fix_normals()
    return m

def rounded_box(size, r):
    w, h, d = size; r = min(r, w / 2 - 1e-3, d / 2 - 1e-3)
    poly = sbox(-w / 2 + r, -d / 2 + r, w / 2 - r, d / 2 - r).buffer(r, quad_segs=6)
    m = trimesh.creation.extrude_polygon(poly, h)  # z up
    m.apply_translation([0, 0, -h / 2]); m.apply_transform(R('x', -90))
    return m

def extrude(poly, depth):
    """poly: list of (x,y) or shapely polygon in XY plane; extruded along +Z, centered."""
    if not hasattr(poly, 'exterior') and not hasattr(poly, 'geoms'):
        poly = Polygon(poly)
    poly = poly.buffer(0)
    geoms = poly.geoms if hasattr(poly, 'geoms') else [poly]
    ms = [trimesh.creation.extrude_polygon(g, depth) for g in geoms if g.area > 1e-9]
    m = trimesh.util.concatenate(ms); m.apply_translation([0, 0, -depth / 2]); return m

def rod(a, b, r, seg=16):
    a, b = np.array(a, float), np.array(b, float)
    return C.cylinder(radius=r, segment=[a, b], sections=seg)

def tube(pts, r, seg=16, closed=False):
    pts = np.array(pts, float)
    circ = Point(0, 0).buffer(r, quad_segs=max(2, seg // 4))
    try:
        m = trimesh.creation.sweep_polygon(circ, pts, connect=closed)
    except Exception:
        m = trimesh.util.concatenate([rod(pts[i], pts[i + 1], r, seg) for i in range(len(pts) - 1)])
    return m

def bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]; p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3

def text_mesh(s, size, depth):
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), s, size=1.0, prop=FontProperties(family='DejaVu Sans', weight='bold'))
    polys = [Polygon(p) for p in tp.to_polygons() if len(p) > 2]
    # even-odd fill: sort by area, subtract holes
    polys.sort(key=lambda p: -p.area); shapes = []
    for p in polys:
        p = p.buffer(0); hit = False
        for i, sh in enumerate(shapes):
            if sh.contains(p.representative_point()) and sh.area > p.area:
                shapes[i] = sh.difference(p); hit = True; break
        if not hit: shapes.append(p)
    g = unary_union(shapes)
    minx, miny, maxx, maxy = g.bounds
    from shapely import affinity
    g = affinity.translate(g, -(minx + maxx) / 2, -(miny + maxy) / 2)
    g = affinity.scale(g, size, size, origin=(0, 0))
    return extrude(g, depth)

def ngon(n, r, start=0):
    a = np.radians(start) + np.linspace(0, 2 * np.pi, n, endpoint=False)
    return list(zip(r * np.cos(a), r * np.sin(a)))

def ring2d(R_, r):
    return Point(0, 0).buffer(R_, quad_segs=24).difference(Point(0, 0).buffer(r, quad_segs=24))

def spokes_wheel(m, R_, at, axis='x', tire='rubber', rim='chrome', spokes=12, w=0.04, hub=True):
    m.tor(R_, w * 0.9, at=at, color=tire, axis=axis)
    m.tor(R_ * 0.92, w * 0.35, at=at, color=rim, axis=axis, metal=0.8, rough=0.3)
    at = np.array(at, float)
    for i in range(spokes):
        a = 2 * np.pi * i / spokes
        if axis == 'x': d = np.array([0, np.cos(a), np.sin(a)])
        elif axis == 'z': d = np.array([np.cos(a), np.sin(a), 0])
        else: d = np.array([np.cos(a), 0, np.sin(a)])
        m.rod(at, at + d * R_ * 0.9, w * 0.08, color=rim, metal=0.8, rough=0.3)
    if hub: m.cyl(w * 0.6, w * 1.4, at=at, color=rim, axis=axis, metal=0.8, rough=0.3)
