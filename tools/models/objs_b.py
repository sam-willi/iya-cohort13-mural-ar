from mk import *
import numpy as np
from shapely.geometry import Polygon, Point, box as sbox
from shapely import affinity

def star2d(r, k=0.45, n=5):
    return Polygon([(r * (1 if i % 2 == 0 else k) * np.cos(a), r * (1 if i % 2 == 0 else k) * np.sin(a))
                    for i, a in enumerate(np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, 2 * n, endpoint=False))])

def handheld_fan():
    m = Model('Handheld fan')
    N = 18; Rr = 1.0; r0 = 0.35
    for i in range(N):
        a0 = np.radians(10 + 160 * i / N); a1 = np.radians(10 + 160 * (i + 1) / N)
        seg = Polygon([(r0 * np.cos(a0), r0 * np.sin(a0)), (Rr * np.cos(a0), Rr * np.sin(a0)),
                       (Rr * np.cos(a1), Rr * np.sin(a1)), (r0 * np.cos(a1), r0 * np.sin(a1))])
        m.ext(seg, 0.012, at=(0, 0, 0.015 if i % 2 else 0), color='navy' if i % 2 else 'blue', rough=0.8)
    for i in range(N + 1):
        a = np.radians(10 + 160 * i / N)
        m.rod((0, 0, 0.03), (Rr * 0.98 * np.cos(a), Rr * 0.98 * np.sin(a), 0.03), 0.008, color='oak')
    for a, r in ((40, 0.8), (70, 0.62), (100, 0.85), (130, 0.7), (155, 0.55), (25, 0.55)):
        m.ext(star2d(0.05), 0.01, at=(r * np.cos(np.radians(a)), r * np.sin(np.radians(a)), 0.035), color='yellow')
    m.sph(0.07, at=(0.75 * np.cos(np.radians(150)), 0.75 * np.sin(np.radians(150)), 0.04), scale=(1, 1, 0.3), color='orange')
    m.tor(0.11, 0.01, at=(0.75 * np.cos(np.radians(150)), 0.75 * np.sin(np.radians(150)), 0.04), axis='z', color='yellow', rot=('x', 60))
    m.sph(0.06, at=(0.75 * np.cos(np.radians(55)), 0.75 * np.sin(np.radians(55)), 0.04), scale=(1, 1, 0.3), color='mint')
    m.cyl(0.04, 0.08, at=(0, 0, 0.02), axis='z', color='brass', metal=0.7)
    return m

def electric_fan():
    m = Model('Electric fan')
    m.lathe([(0, 0), (0.35, 0), (0.33, 0.06), (0.12, 0.08), (0, 0.08)], color='cream')
    m.cyl(0.04, 0.55, at=(0, 0.35, 0), color='chrome', metal=0.8, rough=0.3)
    m.sph(0.13, at=(0, 0.75, -0.1), scale=(1, 1, 1.3), color='cream')
    m.cyl(0.05, 0.08, at=(0, 0.75, 0.08), axis='z', color='chrome', metal=0.8)
    for i in range(3):
        a = np.radians(90 + i * 120)
        blade = affinity.rotate(Point(0, 0.22).buffer(0.13), i * 120, origin=(0, 0))
        blade = affinity.scale(blade, 1, 1)
        m.ext(blade, 0.015, at=(0, 0.75, 0.12), color='sky', rot=None)
    m.tor(0.42, 0.012, at=(0, 0.75, 0.12), axis='z', color='chrome', metal=0.8)
    m.tor(0.42, 0.012, at=(0, 0.75, 0.04), axis='z', color='chrome', metal=0.8)
    for i in range(16):
        a = 2 * np.pi * i / 16
        m.rod((0, 0.75, 0.2), (0.42 * np.cos(a), 0.75 + 0.42 * np.sin(a), 0.12), 0.005, color='chrome', metal=0.8)
        m.rod((0.42 * np.cos(a), 0.75 + 0.42 * np.sin(a), 0.12), (0.42 * np.cos(a), 0.75 + 0.42 * np.sin(a), 0.04), 0.005, color='chrome')
    m.cyl(0.06, 0.03, at=(0, 0.75, 0.2), axis='z', color='orange')
    return m

def telescope():
    m = Model('Telescope')
    a = np.array([-0.75, 0.55, 0]); b = np.array([0.55, 1.05, 0])
    d = (b - a) / np.linalg.norm(b - a)
    m.rod(a, b, 0.11, color='navy', rough=0.3, seg=32)
    m.rod(b - d * 0.05, b + d * 0.12, 0.13, color='brass', metal=0.7, rough=0.3, seg=32)
    m.rod(a, a - d * 0.25, 0.06, color='brass', metal=0.7, seg=24)
    m.rod(a - d * 0.25, a - d * 0.35, 0.05, color='black', seg=24)
    m.rod((-0.25, 0.85, 0.0), (-0.15, 0.95, 0.0), 0.03, color='black')  # finder
    m.rod((-0.3, 0.86, 0.13), (0.05, 1.0, 0.13), 0.035, color='brass', metal=0.7)
    hub = np.array([-0.1, 0.62, 0])
    m.sph(0.08, at=hub, color='black')
    m.rod(hub, (-0.1, 0.78, 0), 0.04, color='black')
    for ang in (0, 120, 240):
        t = np.radians(ang)
        m.rod(hub, hub + np.array([0.42 * np.cos(t), -0.62, 0.42 * np.sin(t)]), 0.03, color='oak')
    # light beam with IYA
    tip = b + d * 0.12
    cone = trimesh.creation.cone(radius=0.3, height=0.6, sections=32)
    cone.apply_transform(R('x', 180)); cone.apply_translation([0, 0, 0.6])
    # orient along d
    z = np.array([0, 0, 1.0]); ax = np.cross(z, d); ang = np.degrees(np.arccos(np.dot(z, d)))
    cone.apply_transform(R(ax / np.linalg.norm(ax), ang)); cone.apply_translation(tip)
    m.add(cone, 'yellow', alpha=0.25, rough=0.1)
    tp = tip + d * 0.45
    m.text('IYA', 0.22, 0.04, at=tp, color='orange', rot=[('y', 90), ('z', np.degrees(np.arctan2(d[1], d[0])))])
    return m

def sunglasses():
    m = Model('Sunglasses')
    lens = sbox(-0.22, -0.16, 0.22, 0.16).buffer(0.08)
    for x in (-0.35, 0.35):
        m.ext(lens.buffer(0.03).difference(lens), 0.06, at=(x, 0, 0), color='black', rough=0.3)
        m.ext(lens, 0.02, at=(x, 0, 0), color='charcoal', alpha=0.85, rough=0.05, metal=0.3)
    m.box((0.12, 0.05, 0.05), at=(0, 0.1, 0), color='black')
    for s in (-1, 1):
        m.box((0.06, 0.06, 0.95), at=(s * 0.68, 0.12, -0.47), color='black')
        m.box((0.05, 0.12, 0.06), at=(s * 0.68, 0.06, -0.97), color='black', rot=('x', 30))
    m.text('CMBR', 0.05, 0.01, at=(0.715, 0.12, -0.45), color='white', rot=('y', 90))
    return m

def bike_lock():
    m = Model('Bike lock')
    m.rbox((0.7, 0.4, 0.3), 0.06, at=(0, 0.2, 0), color='steel', metal=0.7, rough=0.35)
    pts = [(-0.22, 0.38, 0), (-0.22, 0.95, 0)] + [(-0.22 * np.cos(t), 0.95 + 0.22 * np.sin(t), 0) for t in np.linspace(0, np.pi, 20)][1:] + [(0.22, 0.38, 0)]
    m.tube(pts, 0.06, color='red', rough=0.3)
    m.text('LOVE', 0.13, 0.02, at=(-0.1, 0.2, 0.155), color='black')
    heart = Point(-0.03, 0.02).buffer(0.035).union(Point(0.03, 0.02).buffer(0.035)).union(Polygon([(-0.06, 0.0), (0.06, 0.0), (0, -0.07)]))
    m.ext(heart, 0.02, at=(0.22, 0.2, 0.155), color='red')
    m.cyl(0.04, 0.02, at=(0.22, 0.2, 0.16), axis='z', color='black')
    return m

def coffee_grinder():
    m = Model('Coffee grinder')
    m.lathe([(0, 0), (0.3, 0), (0.36, 0.3), (0.28, 0.36), (0, 0.36)], color='black', seg=8)  # base
    m.cyl(0.04, 0.03, at=(0.24, 0.18, 0.2), axis='z', color='chrome', metal=0.8)
    m.lathe([(0, 0.4), (0.24, 0.4), (0.3, 0.55), (0.08, 0.62), (0, 0.62)], color='steel', metal=0.7, seg=24)  # funnel
    m.lathe([(0, 0.66), (0.22, 0.66), (0.36, 0.95), (0.33, 1.05), (0, 1.05)], color='charcoal', seg=8)  # hopper
    m.rod((0, 1.05, 0), (0, 1.15, 0), 0.03, color='chrome', metal=0.8)
    m.rod((0, 1.15, 0), (0.35, 1.18, 0), 0.025, color='chrome', metal=0.8)
    m.sph(0.05, at=(0.38, 1.18, 0), color='wood')
    for i in range(10):
        m.sph(0.035, at=(0.45 + 0.05 * np.sin(i * 2), 0.5 + i * 0.07, 0.1 * np.cos(i)), scale=(1, 0.7, 0.6), color='brown')
    m.text('C13', 0.18, 0.04, at=(0.55, 0.85, 0.0), color='cream')
    return m

def beard_trimmer():
    m = Model('Beard trimmer')
    m.rbox((0.32, 1.1, 0.22), 0.1, at=(0, 0.55, 0), color='charcoal', rough=0.4)
    m.rbox((0.34, 0.5, 0.24), 0.1, at=(0, 0.55, 0), color='black', rough=0.5)
    m.rbox((0.12, 0.18, 0.04), 0.04, at=(0, 0.7, 0.12), color='grey')
    m.tor(0.03, 0.008, at=(0, 0.72, 0.145), axis='z', color='mint')
    m.box((0.34, 0.12, 0.12), at=(0, 1.15, 0), color='steel', metal=0.8, rough=0.3)
    for x in np.linspace(-0.15, 0.15, 11):
        m.box((0.018, 0.1, 0.1), at=(x, 1.25, 0), color='chrome', metal=0.85, rough=0.25)
    m.box((0.1, 0.02, 0.04), at=(0, 0.0, 0.05), color='lightgrey')
    return m

def car_tire():
    m = Model('Car tire')
    m.lathe([(0.45, -0.22), (0.72, -0.22), (0.8, -0.12), (0.8, 0.12), (0.72, 0.22), (0.45, 0.22)], axis='z', color='rubber', rough=0.9, seg=56)
    for i in range(28):
        a = 2 * np.pi * i / 28
        for zz in (-0.1, 0.1):
            m.box((0.06, 0.06, 0.09), at=(0.8 * np.cos(a), 0.8 * np.sin(a), zz), color='black', rot=('z', np.degrees(a) + (20 if zz > 0 else -20)))
    m.cyl(0.46, 0.3, axis='z', color='chrome', metal=0.8, rough=0.3)
    m.cyl(0.36, 0.32, axis='z', color='black')  # speaker
    m.lathe([(0.0, 0.0), (0.3, 0.0), (0.12, 0.08), (0, 0.06)], axis='z', at=(0, 0, 0.12), color='charcoal')
    m.cyl(0.07, 0.06, axis='z', at=(0, 0, 0.2), color='grey', metal=0.5)
    return m

def drill():
    m = Model('Electric drill')
    m.rbox((0.45, 0.16, 0.3), 0.06, at=(0, 0.08, 0), color='charcoal')  # battery base
    m.rbox((0.4, 0.06, 0.26), 0.05, at=(0, 0.19, 0), color='orange')
    m.rbox((0.2, 0.55, 0.18), 0.08, at=(0.02, 0.48, 0), color='orange', rot=('z', -10))  # grip
    m.box((0.08, 0.1, 0.06), at=(0.14, 0.62, 0), color='black')  # trigger
    m.rod((-0.25, 0.85, 0), (0.45, 0.85, 0), 0.17, color='orange', seg=32)  # body
    m.rod((0.45, 0.85, 0), (0.6, 0.85, 0), 0.12, color='black', seg=24)  # clutch
    m.lathe([(0, 0), (0.1, 0), (0.08, 0.2), (0.03, 0.22), (0, 0.22)], axis='x', at=(0.6, 0.85, 0), color='black')
    m.rod((0.82, 0.85, 0), (1.05, 0.85, 0), 0.02, color='chrome', metal=0.9)
    m.cyl(0.17, 0.08, at=(-0.27, 0.85, 0), axis='x', color='black')
    m.box((0.3, 0.12, 0.01), at=(0.08, 0.88, 0.175), color='cream')
    m.text('Cohort13', 0.045, 0.01, at=(0.08, 0.88, 0.183), color='black')
    return m

def bread_maker():
    m = Model('Bread maker')
    m.rbox((1.0, 0.65, 0.65), 0.05, at=(0, 0.325, 0), color='cream')
    m.box((0.9, 0.04, 0.55), at=(0, 0.66, 0), color='white')
    m.text('BREAD', 0.16, 0.03, at=(0, 0.42, 0.33), color='red')
    m.text('MAKER', 0.12, 0.03, at=(0, 0.22, 0.33), color='red')
    for x, h in ((-0.2, 0.9), (0.18, 0.85)):
        sl = Point(0, 0.14).buffer(0.13).union(sbox(-0.12, -0.12, 0.12, 0.14))
        m.ext(sl, 0.06, at=(x, h, 0), color='oak', rot=('y', 90))
        m.ext(sl.buffer(-0.025), 0.065, at=(x, h, 0), color='tan', rot=('y', 90))
    m.box((0.08, 0.06, 0.06), at=(0.44, 0.45, 0.34), color='black')
    return m

def label_maker():
    m = Model('Label maker')
    m.rbox((0.7, 0.65, 0.8), 0.1, at=(0, 0.33, 0), color='white', rough=0.4)
    m.box((0.5, 0.04, 0.02), at=(0, 0.3, 0.405), color='black')
    m.cyl(0.04, 0.02, at=(-0.25, 0.55, 0.41), axis='z', color='grey')
    m.box((0.4, 0.008, 0.6), at=(0, 0.06, 0.7), color='yellow', rot=('x', 6))
    m.text('Cohort 13', 0.07, 0.01, at=(0, 0.035, 0.75), color='black', rot=[('x', -90), ('y', 90)])
    m.text('Label Maker', 0.06, 0.01, at=(0.0, 0.67, 0.0), color='grey', rot=[('x', -90)])
    # handheld
    m.rbox((0.22, 0.45, 0.18), 0.05, at=(0.7, 0.4, -0.2), color='charcoal', rot=('z', -15))
    m.box((0.18, 0.05, 0.2), at=(0.76, 0.66, -0.2), color='black', rot=('z', -15))
    m.box((0.06, 0.007, 0.35), at=(0.85, 0.75, -0.2), color='white', rot=('z', -15))
    return m

def ice_chest():
    m = Model('Ice chest cooler')
    m.rbox((1.2, 0.6, 0.7), 0.06, at=(0, 0.3, 0), color='blue', rough=0.4)
    m.rbox((1.24, 0.15, 0.74), 0.06, at=(0, 0.66, 0), color='white', rough=0.4)
    m.box((0.6, 0.04, 0.3), at=(0, 0.75, 0), color='lightgrey')
    for s in (-1, 1):
        m.tube([(s * 0.62, 0.45, -0.12), (s * 0.7, 0.5, 0), (s * 0.62, 0.45, 0.12)], 0.03, color='white')
    m.box((0.18, 0.12, 0.04), at=(0, 0.6, 0.37), color='white')
    m.box((0.1, 0.06, 0.02), at=(0.45, 0.08, 0.36), color='grey')
    return m

def record_player():
    m = Model('Vinyl record player')
    m.rbox((1.2, 0.18, 1.0), 0.05, at=(0, 0.09, 0), color='oak')
    for x in (-0.5, 0.5):
        for z in (-0.4, 0.4):
            m.cyl(0.05, 0.06, at=(x, -0.03, z), color='black')
    m.cyl(0.42, 0.03, at=(-0.1, 0.195, 0), color='black', rough=0.25)
    m.cyl(0.36, 0.031, at=(-0.1, 0.197, 0), color='teal', rough=0.1)  # lotus pond
    m.cyl(0.08, 0.034, at=(-0.1, 0.2, 0), color='pink')
    for x, z, c in ((-0.25, 0.15, 'orange'), (0.08, -0.12, 'white')):
        m.sph(0.05, at=(x, 0.22, z), scale=(1.6, 0.4, 0.7), color=c)
    for x, z in ((-0.3, -0.18), (0.1, 0.2)):
        m.cyl(0.07, 0.01, at=(x, 0.22, z), color='green')
    m.rod((-0.1, 0.2, 0), (-0.1, 0.65, 0), 0.012, color='green')
    for i in range(10):
        a = 2 * np.pi * i / 10
        m.sph(0.06, at=(-0.1 + 0.08 * np.cos(a), 0.68, 0.08 * np.sin(a)), scale=(1.5, 0.3, 0.6), color='pink', rot=('y', -np.degrees(a)))
    m.sph(0.04, at=(-0.1, 0.69, 0), color='yellow')
    m.cyl(0.05, 0.08, at=(0.45, 0.22, -0.3), color='chrome', metal=0.8)
    m.rod((0.45, 0.27, -0.3), (0.2, 0.25, 0.18), 0.015, color='chrome', metal=0.8)
    m.box((0.05, 0.03, 0.08), at=(0.2, 0.24, 0.2), color='black')
    m.text('COHORT13', 0.06, 0.01, at=(0.25, 0.09, 0.505), color='black')
    m.cyl(0.04, 0.03, at=(-0.45, 0.1, 0.5), axis='z', color='chrome', metal=0.8)
    return m

def air_balloon():
    m = Model('Air balloon')
    gores = 12
    for i in range(gores):
        prof = [(0, 0.55), (0.12, 0.6), (0.42, 0.85), (0.55, 1.15), (0.5, 1.45), (0.3, 1.65), (0, 1.72)]
        g = lathe(prof, 96)
        # keep wedge
        ang = np.degrees(np.arctan2(g.vertices[:, 2], g.vertices[:, 0])) % 360
        lo = 360 * i / gores; hi = 360 * (i + 1) / gores
        keep = np.all(((ang[g.faces] >= lo - 0.01) & (ang[g.faces] <= hi + 0.01)) | (np.linalg.norm(g.vertices[g.faces][:, :, [0, 2]], axis=2) < 1e-6), axis=1)
        g.update_faces(keep); g.remove_unreferenced_vertices()
        m.add(g, ['red', 'cream', 'orange', 'yellow'][i % 4], rough=0.6)
    m.text('IYA', 0.28, 0.04, at=(0, 1.15, 0.53), color='navy')
    m.box((0.22, 0.18, 0.22), at=(0, 0.09, 0), color='wood', rough=0.9)
    for x in (-0.1, 0.1):
        for z in (-0.1, 0.1):
            m.rod((x, 0.18, z), (x * 1.3, 0.58, z * 1.3), 0.006, color='darkwood')
    m.cone(0.06, 0.03, 0.08, at=(0, 0.48, 0), color='grey', metal=0.6)
    return m

def pinball():
    m = Model('Pinball machine')
    top = trimesh.creation.box(extents=(0.7, 0.2, 1.4)); top.apply_transform(R('x', -7))
    m.add(top, 'navy', at=(0, 0.95, 0), rough=0.4)
    m.box((0.62, 0.02, 1.3), at=(0, 1.07, 0.02), color='sky', alpha=0.6, rot=('x', -7), rough=0.05)
    for x, z, c in ((-0.15, -0.3, 'red'), (0.15, -0.25, 'yellow'), (0, -0.05, 'orange')):
        m.cyl(0.07, 0.08, at=(x, 1.05 + z * 0.12, z), color=c)
    for s in (-1, 1):
        m.box((0.15, 0.03, 0.04), at=(s * 0.1, 1.11, 0.55), color='white', rot=[('y', s * 20)])
    m.sph(0.03, at=(0.05, 1.08, 0.2), color='chrome', metal=0.9)
    m.box((0.7, 0.75, 0.15), at=(0, 1.45, -0.68), color='navy')
    m.box((0.6, 0.55, 0.02), at=(0, 1.48, -0.6), color='orange', rough=0.3)
    m.ext(star2d(0.12), 0.02, at=(0, 1.5, -0.58), color='yellow')
    m.text('13', 0.12, 0.02, at=(0, 1.3, -0.58), color='white')
    for x in (-0.3, 0.3):
        for z in (-0.6, 0.6):
            m.rod((x, 0.85, z), (x, 0.0, z), 0.03, color='chrome', metal=0.8)
    m.box((0.08, 0.05, 0.04), at=(0.0, 0.85, 0.72), color='chrome', metal=0.8)
    return m

def washing_machine():
    m = Model('Washing machine')
    m.rbox((0.9, 1.0, 0.85), 0.04, at=(0, 0.5, 0), color='white', rough=0.35)
    m.box((0.86, 0.16, 0.02), at=(0, 0.9, 0.43), color='lightgrey')
    m.box((0.2, 0.08, 0.02), at=(-0.25, 0.9, 0.44), color='black')
    m.cyl(0.06, 0.04, at=(0.25, 0.9, 0.44), axis='z', color='chrome', metal=0.8)
    m.tor(0.3, 0.05, at=(0, 0.42, 0.44), axis='z', color='lightgrey', metal=0.5)
    m.cyl(0.29, 0.03, at=(0, 0.42, 0.43), axis='z', color='glass', alpha=0.7, rough=0.05)
    m.sph(0.24, at=(0, 0.38, 0.3), scale=(1, 0.8, 0.6), color='sky')
    m.box((0.05, 0.2, 0.04), at=(0.3, 0.42, 0.48), color='grey')
    return m

def paint_roller():
    m = Model('Paint roller kit')
    m.box((0.8, 1.5, 0.06), at=(0, 0.75, -0.3), color='cream')
    m.box((0.6, 1.1, 0.01), at=(0, 0.95, -0.265), color='orange', rough=0.9)
    for x in (-0.2, 0.0, 0.18):
        m.cyl(0.02, 0.08, at=(x, 0.36, -0.265), color='orange')
        m.sph(0.025, at=(x, 0.32, -0.265), color='orange')
    m.cyl(0.11, 0.65, at=(0, 0.8, -0.13), axis='x', color='orange', rough=0.95)
    m.tube([(0.33, 0.8, -0.13), (0.4, 0.8, -0.13), (0.4, 0.6, 0.0), (0.25, 0.4, 0.15)], 0.015, color='chrome', metal=0.8)
    m.rod((0.25, 0.4, 0.15), (0.1, 0.05, 0.3), 0.045, color='yellow')
    m.text('XIII', 0.25, 0.05, at=(0, 0.03, 0.3), color='navy', rot=('x', -90))
    # tray
    m.box((0.5, 0.05, 0.6), at=(-0.45, 0.025, 0.3), color='grey', metal=0.4, rot=('x', 8))
    m.box((0.44, 0.01, 0.2), at=(-0.45, 0.04, 0.45), color='orange')
    return m

def treadmill():
    m = Model('Treadmill')
    m.rbox((0.75, 0.15, 1.8), 0.06, at=(0, 0.1, 0), color='charcoal')
    m.box((0.6, 0.02, 1.7), at=(0, 0.185, 0), color='black', rough=0.9)
    for s in (-1, 1):
        m.rod((s * 0.35, 0.15, -0.65), (s * 0.35, 1.25, -0.8), 0.04, color='grey', metal=0.6)
        m.rod((s * 0.35, 1.05, -0.78), (s * 0.35, 1.05, -0.3), 0.03, color='black')
    m.rbox((0.8, 0.3, 0.12), 0.05, at=(0, 1.3, -0.82), color='charcoal', rot=('x', -30))
    m.box((0.5, 0.18, 0.02), at=(0, 1.33, -0.75), color='sky', rot=('x', -30))
    m.text('13', 0.1, 0.02, at=(0, 1.33, -0.735), color='navy', rot=('x', -30))
    m.rod((-0.35, 1.05, -0.78), (0.35, 1.05, -0.78), 0.03, color='black')
    return m

def flashlight():
    m = Model('Flashlight')
    m.lathe([(0, 0), (0.17, 0), (0.17, 0.75), (0.28, 1.0), (0.28, 1.15), (0, 1.15)], axis='x', at=(-0.55, 0, 0), color='red', rough=0.35)
    m.tor(0.27, 0.035, at=(0.6, 0, 0), axis='x', color='chrome', metal=0.85)
    m.cyl(0.25, 0.02, at=(0.6, 0, 0), axis='x', color='yellow', rough=0.1)
    m.box((0.12, 0.05, 0.08), at=(-0.1, 0.18, 0), color='black')
    for x in np.linspace(-0.5, -0.25, 4):
        m.tor(0.172, 0.01, at=(x, 0, 0), axis='x', color='black')
    beam = trimesh.creation.cone(radius=0.4, height=0.6, sections=32)
    beam.apply_transform(R('y', -90)); beam.apply_translation([1.2, 0, 0])
    m.add(beam, 'yellow', alpha=0.25, rough=0.1)
    m.text('13', 0.22, 0.06, at=(0.95, -0.38, 0.2), color='orange')
    return m
