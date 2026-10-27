from mk import *
import numpy as np
from shapely.geometry import Polygon, Point, box as sbox
from shapely import affinity
from objs_b import star2d

def radio_deco():
    m = Model('Radio (Art Deco)')
    m.box((0.8, 1.3, 0.55), at=(0, 0.65, 0), color='cream', rough=0.5)
    m.box((0.5, 0.15, 0.35), at=(0, 1.37, 0), color='cream')
    m.box((0.3, 0.12, 0.25), at=(0, 1.5, 0), color='oak')
    arch = sbox(-0.25, 0, 0.25, 0.45).union(Point(0, 0.45).buffer(0.25))
    m.ext(arch, 0.03, at=(0, 0.1, 0.28), color='brass', metal=0.7, rough=0.35)
    for x in np.linspace(-0.2, 0.2, 6):
        m.box((0.015, 0.55, 0.02), at=(x, 0.4, 0.3), color='darkwood')
    for y in np.linspace(0.18, 0.6, 5):
        m.box((0.48, 0.015, 0.02), at=(0, y, 0.3), color='darkwood')
    for x in (-0.25, 0.0, 0.25):
        m.cyl(0.05, 0.08, at=(x, 1.25, 0.28), axis='z', color='brass', metal=0.7)
    for s in (-1, 1):
        for y in (0.35, 0.65, 0.95):
            m.box((0.12, 0.2, 0.02), at=(s * 0.4 + s * 0.0, y, 0.14), color='navy', rot=('y', s * 90))
        m.box((0.06, 1.3, 0.06), at=(s * 0.32, 0.65, 0.28), color='oak')
    m.text('IOVINE & YOUNG', 0.045, 0.01, at=(0, 1.05, 0.28), color='darkwood')
    m.box((0.9, 0.08, 0.62), at=(0, 0.04, 0), color='oak')
    return m

def rain_jacket():
    m = Model('Rain jacket')
    Y = 'yellow'
    m.rbox((0.75, 0.9, 0.35), 0.12, at=(0, 0.55, 0), color=Y, rough=0.3)
    m.sph(0.28, at=(0, 1.12, -0.05), scale=(1, 1.05, 0.9), color=Y, rough=0.3)  # hood
    m.sph(0.2, at=(0, 1.1, 0.05), scale=(1, 1.1, 0.8), color='darkwood')  # hood opening
    for s in (-1, 1):
        m.rod((s * 0.35, 0.9, 0), (s * 0.55, 0.45, 0.08), 0.12, color=Y, rough=0.3)
        m.rod((s * 0.55, 0.45, 0.08), (s * 0.58, 0.15, 0.12), 0.1, color=Y, rough=0.3)
        m.box((0.18, 0.12, 0.02), at=(s * 0.2, 0.35, 0.18), color='orange')
        m.cyl(0.015, 0.25, at=(s * 0.07, 0.95, 0.17), color='white')
    m.box((0.02, 0.85, 0.02), at=(0, 0.55, 0.18), color='charcoal')
    for y in np.linspace(0.25, 0.85, 5):
        m.cyl(0.02, 0.02, at=(0.05, y, 0.185), axis='z', color='white')
    m.text('13', 0.12, 0.01, at=(0.2, 0.7, 0.18), color='navy')
    return m

def espresso():
    m = Model('Espresso machine')
    m.rbox((0.9, 0.08, 0.7), 0.06, at=(0, 0.04, 0.05), color='chrome', metal=0.85, rough=0.25)
    m.rbox((0.8, 0.85, 0.55), 0.06, at=(0, 0.75, -0.05), color='chrome', metal=0.85, rough=0.25)
    m.box((0.8, 0.3, 0.55), at=(0, 0.25, -0.05), color='black')
    for x in np.linspace(-0.3, 0.3, 9):
        m.box((0.03, 0.02, 0.45), at=(x, 1.185, -0.05), color='black')
    m.cyl(0.08, 0.03, at=(-0.22, 0.85, 0.235), axis='z', color='white')
    m.rod((-0.22, 0.85, 0.25), (-0.18, 0.9, 0.25), 0.005, color='black')
    m.box((0.3, 0.12, 0.02), at=(0.15, 0.88, 0.23), color='darkwood')
    m.text('IYA', 0.08, 0.01, at=(0.15, 0.88, 0.245), color='cream')
    m.cyl(0.05, 0.05, at=(0.3, 0.68, 0.245), axis='z', color='black')
    m.cyl(0.1, 0.08, at=(-0.05, 0.42, 0.15), color='black')  # group head
    m.rod((-0.05, 0.36, 0.15), (-0.45, 0.33, 0.55), 0.035, color='black')  # portafilter
    m.rod((0.35, 0.6, 0.15), (0.45, 0.25, 0.4), 0.015, color='chrome', metal=0.9)  # steam wand
    m.lathe([(0, 0), (0.08, 0), (0.11, 0.12), (0.1, 0.12), (0, 0.02)], at=(-0.05, 0.09, 0.15), color='white')
    m.cyl(0.095, 0.01, at=(-0.05, 0.2, 0.15), color='brown')
    m.tor(0.04, 0.012, at=(0.07, 0.15, 0.15), axis='z', color='white')
    return m

def umbrella():
    m = Model('Umbrella')
    N = 8; Rr = 0.8
    can = []
    for i in range(N):
        a0 = 2 * np.pi * i / N; a1 = 2 * np.pi * (i + 1) / N
        top = np.array([0, 1.1, 0]); p0 = np.array([Rr * np.cos(a0), 0.75, Rr * np.sin(a0)]); p1 = np.array([Rr * np.cos(a1), 0.75, Rr * np.sin(a1)])
        mid = (p0 + p1) / 2 * np.array([0.93, 1, 0.93]) + np.array([0, 0.08, 0])
        verts = np.array([top, p0, mid, p1]); faces = np.array([[0, 2, 1], [0, 3, 2]])
        tm = trimesh.Trimesh(verts, faces); tm = tm.subdivide().subdivide()
        v = tm.vertices; r = np.linalg.norm(v[:, [0, 2]], axis=1); v[:, 1] = 1.1 - 0.35 * (r / Rr) ** 1.6
        m.add(tm, 'red' if i % 2 == 0 else 'black', rough=0.6)
        m.rod(top, p0, 0.008, color='black')
    m.rod((0, 1.18, 0), (0, 0.05, 0), 0.02, color='black')
    hook = [(0, 0.08, 0)] + [(0.08 - 0.08 * np.cos(t), 0.0 - 0.08 * np.sin(t) + 0.08, 0) for t in np.linspace(0, np.pi, 12)][1:]
    m.tube([(0, 0.1, 0), (0, 0.0, 0)] + [(0.08 - 0.08 * np.cos(t), -0.08 * np.sin(t), 0) for t in np.linspace(0, np.pi, 12)][1:], 0.03, color='wood')
    return m

def tiffany_lamp():
    m = Model('Desk lamp (Art Nouveau)')
    m.lathe([(0, 0), (0.4, 0), (0.42, 0.03), (0.3, 0.07), (0.08, 0.1), (0.06, 0.3), (0.1, 0.55), (0.06, 0.75), (0.04, 0.95), (0, 0.95)], color='brass', metal=0.7, rough=0.35)
    shade = lathe([(0.0, 1.55), (0.12, 1.53), (0.35, 1.4), (0.55, 1.12), (0.6, 1.0), (0.58, 0.98), (0.0, 0.98)], 64)
    cols = ['orange', 'yellow', 'green', 'teal', 'red', 'gold']
    ang = np.degrees(np.arctan2(shade.vertices[:, 2], shade.vertices[:, 0])) % 360
    for k in range(12):
        g = shade.copy(); fa = ang[g.faces].mean(1)
        g.update_faces((fa >= k * 30) & (fa < (k + 1) * 30)); g.remove_unreferenced_vertices()
        m.add(g, cols[k % len(cols)], alpha=0.95, rough=0.2)
    for k in range(12):
        a = np.radians(k * 30)
        pts = [(r * np.cos(a), y, r * np.sin(a)) for r, y in ((0.12, 1.53), (0.355, 1.4), (0.555, 1.12), (0.605, 1.0))]
        m.tube(pts, 0.008, color='darkwood')
    m.tor(0.6, 0.012, at=(0, 0.99, 0), color='brass', metal=0.7)
    m.sph(0.05, at=(0, 1.58, 0), color='brass', metal=0.7)
    m.rod((0.15, 0.97, 0), (0.15, 0.75, 0), 0.004, color='brass')
    m.sph(0.02, at=(0.15, 0.74, 0), color='brass', metal=0.7)
    return m

def movie_camera():
    m = Model('Movie camera')
    m.rbox((0.5, 0.4, 0.3), 0.04, at=(0, 1.1, 0), color='black', rough=0.35)
    for x, y in ((-0.12, 1.5), (0.18, 1.5)):
        m.cyl(0.18, 0.06, at=(x, y, 0), axis='z', color='charcoal')
        m.cyl(0.04, 0.08, at=(x, y, 0), axis='z', color='chrome', metal=0.8)
        for k in range(5):
            a = 2 * np.pi * k / 5
            m.cyl(0.035, 0.07, at=(x + 0.1 * np.cos(a), y + 0.1 * np.sin(a), 0), axis='z', color='grey')
    m.lathe([(0, 0), (0.09, 0), (0.09, 0.15), (0.11, 0.25), (0, 0.25)], axis='x', at=(0.25, 1.1, 0), color='chrome', metal=0.8)
    m.cyl(0.1, 0.01, at=(0.5, 1.1, 0), axis='x', color='glass', rough=0.05)
    m.box((0.12, 0.12, 0.14), at=(0.1, 1.33, 0.08), color='brass', metal=0.7)  # viewfinder
    m.cyl(0.05, 0.08, at=(-0.3, 1.05, 0.1), axis='x', color='brass', metal=0.7)  # crank
    m.rod((-0.34, 1.05, 0.1), (-0.34, 0.92, 0.12), 0.012, color='brass')
    m.box((0.2, 0.06, 0.2), at=(0, 0.88, 0), color='oak')
    for a in (0, 120, 240):
        t = np.radians(a + 30)
        m.rod((0, 0.85, 0), (0.45 * np.cos(t), 0.0, 0.45 * np.sin(t)), 0.025, color='oak')
    return m

def trumpet():
    m = Model('Trumpet')
    B = dict(color='brass', metal=0.85, rough=0.25)
    m.lathe([(0.0, 0), (0.025, 0), (0.025, 0.55), (0.06, 0.7), (0.2, 0.85), (0.24, 0.87), (0.0, 0.87)], axis='x', at=(0.0, 0.5, 0), **B)
    m.rod((-0.65, 0.5, 0), (0.0, 0.5, 0), 0.025, **B)
    m.cone(0.025, 0.012, 0.12, at=(-0.7, 0.5, 0), axis='x', color='chrome', metal=0.9)
    loop = [(-0.5, 0.5, 0.0), (-0.65, 0.42, 0.0), (-0.65, 0.3, 0.0), (-0.5, 0.25, 0.0), (0.1, 0.25, 0.0), (0.25, 0.32, 0), (0.25, 0.42, 0), (0.1, 0.5, 0)]
    m.tube(loop, 0.025, **B)
    for x in (-0.25, -0.15, -0.05):
        m.cyl(0.04, 0.32, at=(x, 0.45, 0), **B)
        m.cyl(0.03, 0.06, at=(x, 0.65, 0), color='cream')
    m.ext(sbox(-0.12, -0.12, 0.12, 0.08), 0.01, at=(-0.15, 0.12, 0.05), color='cream')
    m.text('COHORT 13', 0.035, 0.01, at=(-0.15, 0.1, 0.06), color='navy')
    return m

def kettle():
    m = Model('Electric kettle')
    m.lathe([(0, 0), (0.42, 0), (0.42, 0.08), (0, 0.08)], color='black')
    m.lathe([(0, 0.09), (0.36, 0.09), (0.38, 0.2), (0.37, 0.8), (0.33, 0.95), (0, 0.95)], color='white', rough=0.3)
    m.lathe([(0, 0.95), (0.3, 0.95), (0.3, 0.98), (0, 0.98)], color='chrome', metal=0.8)
    m.ext(Polygon([(0, 0), (0.15, 0.08), (0.14, 0.13), (0, 0.15)]), 0.18, at=(-0.36, 0.8, 0), color='white', rot=('y', 180))
    hand = sbox(0, 0, 0.22, 0.65).difference(sbox(0.06, 0.08, 0.16, 0.57))
    m.ext(hand, 0.1, at=(0.35, 0.2, 0), color='charcoal')
    m.box((0.06, 0.5, 0.02), at=(0.0, 0.5, 0.36), color='sky', alpha=0.7)
    m.tube([(0.2, 0.03, 0.3), (0.5, 0.03, 0.6), (0.9, 0.03, 0.5)], 0.015, color='black')
    return m

def ice_cream_truck():
    m = Model('Ice cream truck')
    cone = lathe([(0, 0), (0.05, 0), (0.3, 1.0), (0, 1.0)], 40)
    cone.apply_transform(R('z', 90)); cone.apply_translation([0.5, 0.35, 0])
    m.add(cone, 'oak', rough=0.8)
    for x in np.linspace(-0.4, 0.35, 6):
        rr = 0.05 + 0.25 * (0.5 - x) / 1.0
        m.tor(rr, 0.01, at=(x, 0.35, 0), axis='x', color='brown')
    m.sph(0.33, at=(-0.55, 0.38, 0), color='pink', rough=0.7)
    m.sph(0.25, at=(-0.82, 0.45, 0), color='cream', rough=0.7)
    m.sph(0.04, at=(-1.0, 0.6, 0), color='red')
    m.box((0.25, 0.15, 0.02), at=(-0.1, 0.55, 0.22), color='sky', rot=('y', -5))
    m.text('IYA', 0.07, 0.01, at=(-0.1, 0.55, 0.235), color='navy')
    for x in (-0.65, 0.05):
        for z in (-0.22, 0.22):
            m.cyl(0.1, 0.06, at=(x, 0.1, z), axis='z', color='rubber')
            m.cyl(0.05, 0.07, at=(x, 0.1, z), axis='z', color='chrome', metal=0.8)
    m.box((0.02, 0.15, 0.25), at=(-0.35, 0.82, 0), color='white')
    m.text('ICE CREAM', 0.035, 0.01, at=(-0.34, 0.82, 0), color='red', rot=('y', 90))
    return m

def air_purifier():
    m = Model('Air purifier')
    m.rbox((0.7, 1.2, 0.4), 0.04, at=(0, 0.6, 0), color='white', rough=0.4)
    for y in np.linspace(0.12, 0.7, 14):
        m.box((0.6, 0.015, 0.01), at=(0, y, 0.2), color='lightgrey')
    m.box((0.6, 0.02, 0.3), at=(0, 1.21, 0), color='lightgrey')
    for x in np.linspace(-0.2, 0.2, 5):
        m.cyl(0.025, 0.02, at=(x, 1.22, 0.12), color='mint')
    m.rbox((0.22, 0.1, 0.02), 0.04, at=(0, 1.0, 0.2), color='sky')
    m.text('IYA', 0.05, 0.01, at=(0, 1.0, 0.215), color='navy')
    return m

def djembe():
    m = Model('African drums')
    prof = [(0, 0), (0.25, 0), (0.22, 0.12), (0.12, 0.45), (0.11, 0.55), (0.2, 0.7), (0.33, 0.95), (0.35, 1.08), (0, 1.08)]
    m.lathe(prof, color='wood', rough=0.6)
    m.lathe([(0, 1.08), (0.36, 1.08), (0.36, 1.1), (0, 1.1)], color='tan', rough=0.9)
    m.tor(0.35, 0.02, at=(0, 1.06, 0), color='darkwood')
    m.tor(0.24, 0.02, at=(0, 0.1, 0), color='darkwood')
    for k in range(16):
        a = 2 * np.pi * k / 16
        m.rod((0.355 * np.cos(a), 1.05, 0.355 * np.sin(a)), (0.335 * np.cos(a + 0.2), 0.85, 0.335 * np.sin(a + 0.2)), 0.006, color='cream')
    for y in (0.5, 0.58):
        m.tor(0.12 if y < 0.55 else 0.135, 0.012, at=(0, y, 0), color='red')
    m.tor(0.2, 0.012, at=(0, 0.25, 0), color='orange'); m.tor(0.17, 0.012, at=(0, 0.33, 0), color='yellow')
    m.text('IYA', 0.12, 0.01, at=(0, 1.105, -0.05), color='darkwood', rot=('x', -90))
    m.text('30', 0.12, 0.01, at=(0, 1.105, 0.1), color='darkwood', rot=('x', -90))
    for k in range(7):
        m.sph(0.03, at=(0.36, 0.95 - k * 0.06, 0.0), color='cream')
    return m

def running_shoes():
    m = Model('Running shoes')
    for z, c in ((-0.22, 'red'), (0.22, 'red')):
        sole = Polygon([(-0.55, 0), (0.45, 0)] + [(0.45 + 0.1 * np.sin(t), 0.1 - 0.1 * np.cos(t)) for t in np.linspace(0, np.pi, 8)] + [(-0.55, 0.12)])
        m.ext(sole.buffer(0.0), 0.32, at=(0, 0, z), color='white', rough=0.5)
        upper = m.sph(0.3, at=(0.0, 0.22, z), scale=(1.8, 0.75, 0.55), color=c, rough=0.7)
        v = upper.vertices; v[v[:, 1] < 0.12, 1] = 0.12
        m.cyl(0.13, 0.3, at=(-0.35, 0.33, z), color=c, rough=0.7)
        m.cyl(0.11, 0.05, at=(-0.35, 0.49, z), color='black')
        for x in np.linspace(-0.15, 0.2, 5):
            m.box((0.02, 0.01, 0.18), at=(x, 0.36 - x * 0.25, z), color='white', rot=('z', -14))
        m.tube([(0.2, 0.15, z + 0.16), (-0.1, 0.25, z + 0.165), (-0.45, 0.2, z + 0.16)], 0.012, color='white')
    return m

def portable_blender():
    m = Model('Portable blender')
    m.cyl(0.32, 0.4, at=(0, 0.2, 0), color='lilac', rough=0.4)
    m.cyl(0.33, 0.06, at=(0, 0.43, 0), color='charcoal')
    m.cyl(0.3, 0.7, at=(0, 0.81, 0), color='glass', alpha=0.45, rough=0.05)
    m.cyl(0.28, 0.4, at=(0, 0.66, 0), color='pink', alpha=0.9)
    m.cyl(0.32, 0.1, at=(0, 1.2, 0), color='lilac')
    m.cyl(0.07, 0.08, at=(0.0, 1.29, 0.0), color='charcoal')
    m.ext(sbox(0, 0, 0.12, 0.55).union(sbox(0, 0.43, 0.5, 0.55)).union(sbox(0.38, 0, 0.5, 0.55)), 0.1, at=(-0.25, 1.2, -0.05), color='lilac', rot=('x', 90))
    m.cyl(0.05, 0.03, at=(0.15, 0.2, 0.31), axis='z', color='white')
    m.text('IYA', 0.08, 0.01, at=(-0.05, 0.2, 0.32), color='white')
    return m

def bike_helmet():
    m = Model('Bicycle helmet')
    shell = trimesh.creation.icosphere(subdivisions=4, radius=0.5)
    v = shell.vertices; shell.update_faces(v[shell.faces].mean(1)[:, 1] > -0.05); shell.remove_unreferenced_vertices()
    shell.apply_scale([0.85, 0.85, 1.15])
    m.add(shell, 'white', at=(0, 0.3, 0), rough=0.35)
    for x in (-0.2, 0.0, 0.2):
        for z in (-0.3, 0.05):
            yy = 0.3 + 0.425 * np.sqrt(max(0, 1 - (x / 0.425) ** 2 - (z / 0.575) ** 2))
            m.sph(0.07, at=(x, yy, z), scale=(0.8, 0.5, 2.0), color='black')
    m.ext(Polygon([(-0.32, 0), (0.32, 0), (0.25, 0.1), (-0.25, 0.1)]), 0.03, at=(0, 0.33, 0.56), color='black', rot=('x', -60))
    for s in (-1, 1):
        m.rod((s * 0.38, 0.28, 0.25), (s * 0.18, -0.25, 0.1), 0.015, color='black')
        m.rod((s * 0.38, 0.28, -0.3), (s * 0.18, -0.25, 0.1), 0.015, color='black')
        m.box((0.05, 0.06, 0.02), at=(s * 0.26, 0.0, 0.0), color='grey')
    m.box((0.14, 0.05, 0.05), at=(0, -0.27, 0.1), color='grey')
    return m

def bicycle():
    m = Model('Bicycle')
    for x in (-0.6, 0.6):
        spokes_wheel(m, 0.35, (x, 0.35, 0), axis='z', tire='rubber', rim='chrome', spokes=12, w=0.05)
    F = dict(color='teal', rough=0.3, metal=0.3)
    bb = (0, 0.32, 0); st = (-0.12, 0.85, 0); ht = (0.45, 0.8, 0); ht2 = (0.42, 0.68, 0)
    m.rod(bb, st, 0.03, **F); m.rod(st, ht, 0.03, **F); m.rod(bb, ht2, 0.035, **F)
    m.rod(bb, (-0.6, 0.35, 0), 0.02, **F); m.rod(st, (-0.6, 0.35, 0), 0.02, **F)
    m.rod(ht, (0.6, 0.35, 0), 0.025, **F)
    m.rod(ht, (0.42, 1.0, 0), 0.025, color='chrome', metal=0.8)
    m.rod((0.35, 1.0, -0.3), (0.42, 1.0, 0.3), 0.022, color='black')
    m.rod(st, (-0.15, 0.98, 0), 0.02, color='chrome', metal=0.8)
    m.rbox((0.3, 0.06, 0.15), 0.05, at=(-0.15, 1.0, 0), color='black')
    m.rbox((0.04, 0.28, 0.25), 0.04, at=(-0.32, 1.15, 0), color='black', rot=('z', 10))  # backrest
    m.text('13', 0.13, 0.02, at=(-0.32, 1.32, 0.0), color='orange', rot=('y', 90))
    m.cyl(0.09, 0.03, at=bb, axis='z', color='chrome', metal=0.8)
    for s in (-1, 1):
        m.rod((0, 0.32, s * 0.03), (s * 0.1, 0.32 - s * 0.15, s * 0.08), 0.012, color='chrome')
        m.box((0.1, 0.02, 0.05), at=(s * 0.1, 0.32 - s * 0.15, s * 0.1), color='black')
    m.text('IYA', 0.07, 0.01, at=(0.2, 0.84, 0.035), color='white', rot=('z', -6))
    return m

def lamp_renzo():
    m = Model('Lamp - ceiling or floor')
    for i in range(4):
        m.rbox((0.6, 0.3, 0.6), 0.1, at=(0, 0.17 + i * 0.33, 0), color='cream' if i % 2 else 'oak', rough=0.6)
    m.text('DEGREES IN', 0.05, 0.01, at=(0, 1.2, 0.305), color='darkwood')
    m.text('DISRUPTION', 0.05, 0.01, at=(0, 1.12, 0.305), color='darkwood')
    m.cyl(0.08, 0.1, at=(0, 1.42, 0), color='brass', metal=0.7)
    m.sph(0.14, at=(0, 1.6, 0), scale=(1, 1.2, 1), color='yellow', alpha=0.85, rough=0.1)
    for k in range(6):
        a = 2 * np.pi * k / 6
        m.rod((0.2 * np.cos(a), 1.62 + 0.2 * np.sin(a) * 0.6, 0.2 * np.sin(a) * 0.3), (0.3 * np.cos(a), 1.62 + 0.3 * np.sin(a) * 0.6, 0.3 * np.sin(a) * 0.3), 0.01, color='yellow')
    return m

def headphones():
    m = Model('Noise-canceling headphones')
    band = [(0.48 * np.cos(t), 0.55 + 0.55 * np.sin(t), 0) for t in np.linspace(0.05, np.pi - 0.05, 40)]
    m.tube(band, 0.045, color='black')
    m.tube([(0.44 * np.cos(t), 0.55 + 0.5 * np.sin(t), 0) for t in np.linspace(0.6, np.pi - 0.6, 24)], 0.05, color='charcoal')
    for s in (-1, 1):
        m.cyl(0.3, 0.16, at=(s * 0.5, 0.4, 0), axis='x', color='red', rough=0.35)
        m.cyl(0.26, 0.08, at=(s * 0.4, 0.4, 0), axis='x', color='black', rough=0.9)
        m.cyl(0.12, 0.02, at=(s * 0.585, 0.4, 0), axis='x', color='white')
        m.text('b', 0.16, 0.02, at=(s * 0.595, 0.4, 0), color='red', rot=('y', s * 90))
        m.rod((s * 0.5, 0.6, 0), (s * 0.48, 0.72, 0), 0.03, color='chrome', metal=0.8)
    return m

def japanese_robot():
    m = Model('Japanese toy robot (80s)')
    m.box((0.36, 0.3, 0.3), at=(0, 1.62, 0), color='white')
    m.box((0.06, 0.25, 0.32), at=(0, 1.85, 0), color='red')
    m.box((0.26, 0.08, 0.02), at=(0, 1.65, 0.16), color='yellow')
    m.box((0.7, 0.55, 0.38), at=(0, 1.15, 0), color='blue')
    m.box((0.5, 0.18, 0.4), at=(0, 1.25, 0.01), color='red')
    m.ext(Polygon([(-0.18, 0), (0.18, 0), (0, -0.18)]), 0.02, at=(0, 1.0, 0.2), color='yellow')
    m.box((0.5, 0.15, 0.32), at=(0, 0.82, 0), color='grey')
    for s in (-1, 1):
        m.box((0.18, 0.18, 0.2), at=(s * 0.45, 1.32, 0), color='red')
        m.box((0.14, 0.45, 0.14), at=(s * 0.47, 1.0, 0), color='white')
        m.box((0.12, 0.12, 0.18), at=(s * 0.47, 0.72, 0.03), color='grey')
        m.box((0.2, 0.42, 0.24), at=(s * 0.14, 0.52, 0), color='white')
        m.box((0.22, 0.25, 0.3), at=(s * 0.14, 0.13, 0.03), color='blue')
    m.text('13', 0.12, 0.02, at=(0, 1.42, 0.2), color='white')
    m.box((0.06, 0.6, 0.06), at=(0.6, 0.85, 0.12), color='chrome', metal=0.8)  # sword
    return m

def toothbrush():
    m = Model('Electric toothbrush')
    m.lathe([(0, 0), (0.13, 0), (0.15, 0.1), (0.15, 0.95), (0.12, 1.1), (0.04, 1.2), (0, 1.2)], color='white', rough=0.3)
    m.rbox((0.08, 0.2, 0.03), 0.035, at=(0, 0.65, 0.15), color='sky')
    m.cyl(0.03, 0.02, at=(0, 0.66, 0.165), axis='z', color='white')
    m.lathe([(0, 1.2), (0.04, 1.2), (0.025, 1.7), (0, 1.7)], color='white')
    m.cyl(0.07, 0.04, at=(0, 1.72, 0.03), axis='z', color='white')
    for k in range(18):
        a = 2 * np.pi * k / 18; r = 0.04 if k % 2 else 0.055
        m.cyl(0.008, 0.06, at=(r * np.cos(a), 1.72 + r * np.sin(a), 0.08), axis='z', color='sky' if k % 3 else 'white')
    m.lathe([(0, 0), (0.16, 0), (0.16, 0.05), (0, 0.05)], at=(0, -0.05, 0), color='lightgrey')
    return m

def baby_mobile():
    m = Model('Mobile for babies')
    m.tor(0.5, 0.04, at=(0, 1.6, 0), color='oak')
    for k in range(8):
        a = np.pi * k / 4
        m.rod((0, 1.6, 0), (0.5 * np.cos(a), 1.6, 0.5 * np.sin(a)), 0.012, color='oak')
    m.rod((0, 1.6, 0), (0, 1.95, 0), 0.02, color='oak')
    items = [(0.0, 'star', 'yellow'), (45, 'moon', 'cream'), (90, 'cloud', 'white'), (135, 'star', 'orange'), (180, 'cloud', 'white'),
             (225, 'moon', 'yellow'), (270, 'star', 'sky'), (315, 'cloud', 'white')]
    for i, (a, kind, c) in enumerate(items):
        p = np.array([0.48 * np.cos(np.radians(a)), 0, 0.48 * np.sin(np.radians(a))])
        drop = 0.35 + 0.15 * (i % 3)
        m.rod(p + (0, 1.6, 0), p + (0, 1.6 - drop, 0), 0.004, color='grey')
        at = p + (0, 1.6 - drop - 0.08, 0)
        if kind == 'star': m.ext(star2d(0.09), 0.03, at=at, color=c)
        elif kind == 'moon': m.ext(Point(0, 0).buffer(0.08).difference(Point(0.04, 0.02).buffer(0.07)), 0.03, at=at, color=c)
        else:
            for dx in (-0.05, 0, 0.05): m.sph(0.05 + 0.01 * (dx == 0), at=at + (dx, 0, 0), color=c)
    m.rod((0, 1.6, 0), (0, 0.95, 0), 0.004, color='grey')
    m.sph(0.17, at=(0, 0.8, 0), color='orange', rough=0.5)
    for i, (ch, h) in enumerate((('I', 0.45), ('Y', 0.25), ('A', 0.4))):
        x = (i - 1) * 0.25
        m.rod((x, 1.6, 0.0 if i != 1 else 0.3), (x, h + 0.12, 0.0 if i != 1 else 0.3), 0.004, color='grey') if False else None
        m.text(ch, 0.18, 0.05, at=(x, h, 0.25), color=['red', 'blue', 'green'][i])
        m.rod((x, 1.6 if abs(x) < 0.4 else 1.6, 0.25 * (abs(x) < 0.01)), (x, h + 0.1, 0.25), 0.004, color='grey')
    return m

def earbuds():
    m = Model('Wireless earbuds')
    for s, rot in ((-1, 20), (1, -20)):
        bud = Model('t')
        m.sph(0.17, at=(s * 0.55, 0.65, 0), scale=(1, 0.9, 1.1), color='white', rough=0.25)
        m.cyl(0.06, 0.55, at=(s * 0.55, 0.32, 0.03), color='white', rough=0.25)
        m.cyl(0.07, 0.02, at=(s * 0.55, 0.05, 0.03), color='chrome', metal=0.8)
        m.sph(0.06, at=(s * 0.55 - s * 0.12, 0.68, 0.06), scale=(0.6, 0.8, 0.8), color='charcoal')
        m.box((0.05, 0.08, 0.01), at=(s * 0.55, 0.8, 0.17), color='charcoal')
    m.text('IYA', 0.3, 0.08, at=(0, 0.55, 0), color='navy')
    for i in range(8):
        m.box((0.05, 0.05, 0.05), at=(-0.35 + i * 0.1, 0.35 + 0.35 * ((i * 37) % 7) / 7, 0.05 * (i % 3)), color='sky', rot=('y', i * 20))
    return m

def midcentury_chair():
    m = Model('Midcentury mod chair')
    m.rbox((0.75, 0.16, 0.7), 0.06, at=(0, 0.48, 0.05), color='leather', rough=0.5)
    m.box((0.78, 0.04, 0.72), at=(0, 0.38, 0.05), color='darkwood')
    back = m.rbox((0.72, 0.85, 0.14), 0.06, at=(0, 0.9, -0.33), color='leather', rough=0.5, rot=('x', -15))
    m.box((0.76, 0.86, 0.04), at=(0, 0.88, -0.42), color='darkwood', rot=('x', -15))
    for y in (0.75, 1.0):
        for x in (-0.18, 0.18):
            m.sph(0.02, at=(x, y, -0.25 - (y - 0.75) * 0.26), color='darkwood')
    for s in (-1, 1):
        m.rbox((0.12, 0.08, 0.55), 0.03, at=(s * 0.42, 0.65, 0.02), color='leather')
        m.box((0.06, 0.2, 0.06), at=(s * 0.42, 0.53, 0.1), color='darkwood')
    m.cyl(0.05, 0.3, at=(0, 0.22, 0), color='black')
    for a in range(5):
        t = 2 * np.pi * a / 5
        m.rod((0, 0.1, 0), (0.42 * np.cos(t), 0.03, 0.42 * np.sin(t)), 0.025, color='chrome', metal=0.85)
    # ottoman
    m.rbox((0.6, 0.15, 0.48), 0.06, at=(0, 0.3, 0.85), color='leather')
    m.box((0.62, 0.04, 0.5), at=(0, 0.2, 0.85), color='darkwood')
    m.cyl(0.04, 0.15, at=(0, 0.1, 0.85), color='black')
    for a in range(4):
        t = 2 * np.pi * a / 4 + 0.4
        m.rod((0, 0.04, 0.85), (0.3 * np.cos(t), 0.02, 0.85 + 0.3 * np.sin(t)), 0.02, color='chrome', metal=0.85)
    m.text('13', 0.14, 0.02, at=(0, 1.15, -0.3), color='cream', rot=('x', -15))
    return m

def camping_lantern():
    m = Model('Camping lantern')
    m.lathe([(0, 0), (0.28, 0), (0.3, 0.08), (0.3, 0.3), (0.2, 0.38), (0, 0.38)], color='green', metal=0.3, rough=0.4)
    m.cyl(0.18, 0.6, at=(0, 0.68, 0), color='glass', alpha=0.4, rough=0.05)
    m.sph(0.06, at=(0, 0.6, 0), scale=(0.6, 1.4, 0.6), color='orange')
    m.sph(0.035, at=(0, 0.66, 0), scale=(0.5, 1.4, 0.5), color='yellow')
    for k in range(4):
        a = np.pi * k / 2 + np.pi / 4
        m.rod((0.19 * np.cos(a), 0.38, 0.19 * np.sin(a)), (0.19 * np.cos(a), 0.98, 0.19 * np.sin(a)), 0.012, color='iron')
    m.lathe([(0, 0.98), (0.22, 0.98), (0.22, 1.1), (0.17, 1.25), (0.08, 1.3), (0, 1.3)], color='green', metal=0.3, rough=0.4)
    for k in range(14):
        a = k * 2.4; y = 1.02 + 0.2 * ((k * 5) % 7) / 7
        r = 0.22 if y < 1.1 else 0.22 - (y - 1.1) * 0.6
        m.cyl(0.018, 0.02, at=(r * np.cos(a), y, r * np.sin(a)), axis='x', color='black', rot=('y', -np.degrees(a)))
    m.cyl(0.04, 0.06, at=(0.3, 0.2, 0), axis='x', color='brass', metal=0.8)
    m.tube([(-0.2, 1.25, 0)] + [(-0.2 * np.cos(t), 1.25 + 0.25 * np.sin(t), 0) for t in np.linspace(0, np.pi, 16)], 0.012, color='iron')
    return m

def tea_set():
    m = Model('Tea cup and tea pot')
    pot = trimesh.creation.icosphere(subdivisions=4, radius=0.45); pot.apply_scale([1, 0.95, 0.55])
    m.add(pot, 'cream', at=(0, 0.48, 0), rough=0.3)
    m.tor(0.2, 0.015, at=(0, 0.48, 0.24), axis='z', color='teal')
    m.tor(0.32, 0.012, at=(0, 0.48, 0.2), axis='z', color='teal')
    m.cyl(0.12, 0.04, at=(0, 0.92, 0), color='cream')
    m.sph(0.04, at=(0, 0.96, 0), color='teal')
    m.tube([(0.38, 0.55, 0), (0.55, 0.62, 0), (0.62, 0.78, 0)], 0.04, color='cream')
    hand = sbox(0, 0, 0.12, 0.55).union(sbox(0, 0.45, 0.45, 0.55)).union(sbox(0.33, 0, 0.45, 0.55))
    m.ext(hand, 0.06, at=(-0.62, 0.35, 0.0), color='darkwood', rot=('x', 0)) if False else None
    m.tube([(-0.4, 0.75, 0), (-0.55, 0.85, 0), (-0.62, 0.55, 0), (-0.42, 0.32, 0)], 0.035, color='darkwood')
    # cup + saucer
    m.cyl(0.2, 0.02, at=(0.75, 0.01, 0.35), color='cream')
    m.lathe([(0, 0), (0.08, 0), (0.15, 0.22), (0.13, 0.22), (0.07, 0.03), (0, 0.03)], at=(0.75, 0.02, 0.35), color='cream')
    m.cyl(0.13, 0.01, at=(0.75, 0.2, 0.35), color='brown')
    m.tor(0.05, 0.012, at=(0.92, 0.13, 0.35), axis='z', color='cream')
    return m

def typewriter():
    m = Model('Typewriter')
    body = Polygon([(-0.5, 0), (0.5, 0), (0.42, 0.35), (-0.3, 0.42), (-0.45, 0.25)])
    m.ext(body, 1.1, at=(0, 0, 0), color='cream', rot=('y', 90), rough=0.4)
    m.box((1.0, 0.08, 0.95), at=(0, 0.04, 0), color='charcoal')
    for r in range(4):
        for c in range(10 - (r % 2)):
            x = -0.4 + c * 0.09 + (r % 2) * 0.045
            m.cyl(0.035, 0.03, at=(x, 0.25 + r * 0.05, 0.38 - r * 0.07), color='black')
            m.cyl(0.028, 0.032, at=(x, 0.252 + r * 0.05, 0.38 - r * 0.07), color='white')
    m.box((0.5, 0.04, 0.06), at=(0, 0.19, 0.47), color='black')
    m.cyl(0.09, 1.2, at=(0, 0.52, -0.2), axis='x', color='black')
    m.cyl(0.1, 0.06, at=(0.63, 0.52, -0.2), axis='x', color='charcoal')
    m.rod((0.66, 0.6, -0.2), (0.85, 0.75, -0.05), 0.015, color='chrome', metal=0.9)
    m.box((0.08, 0.04, 0.04), at=(0.87, 0.77, -0.04), color='black')
    m.box((0.5, 0.65, 0.008), at=(0, 0.88, -0.18), color='paper', rot=('x', -10))
    m.text('THE PLACE WHERE', 0.04, 0.005, at=(0, 1.08, -0.21), color='black', rot=('x', -10))
    m.text('OUR STORY BEGINS', 0.04, 0.005, at=(0, 1.02, -0.2), color='black', rot=('x', -10))
    for k in range(9):
        a = np.radians(30 + k * 15)
        m.box((0.012, 0.15, 0.01), at=(0.15 * np.cos(a), 0.42 + 0.06 * np.sin(a), 0.0), color='chrome', rot=('z', np.degrees(a) - 90))
    m.box((0.3, 0.08, 0.01), at=(0, 0.2, 0.555), color='cream')
    m.text('COHORT 13', 0.035, 0.01, at=(0, 0.13, 0.56), color='navy')
    return m

def comb():
    m = Model('Comb (Hamza Nassief)')
    sp = sbox(-0.06, 0, 0.06, 1.0)
    for i in range(10):
        sp = sp.union(sbox(-0.35, 0.45 + i * 0.055, 0.0, 0.48 + i * 0.055))
    sp = sp.union(sbox(-0.08, -0.6, 0.08, 0.0).union(Point(0, -0.65).buffer(0.1))).difference(Point(0, -0.65).buffer(0.04))
    m.ext(sp, 0.06, color='charcoal', rough=0.4)
    return m
