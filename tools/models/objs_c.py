from mk import *
import numpy as np
from shapely.geometry import Polygon, Point, box as sbox
from shapely import affinity
from objs_b import star2d

def stroller():
    m = Model('Baby stroller')
    side = Polygon([(-0.55, 0.15), (0.6, 0.15), (0.62, 0.45), (0.25, 0.5), (0.1, 0.4), (-0.3, 0.45), (-0.55, 0.65)])
    for z in (-0.32, 0.32):
        m.ext(side, 0.06, at=(0, 0, z), color='mint', rough=0.4)
    m.box((1.1, 0.06, 0.64), at=(0.02, 0.18, 0), color='mint')
    m.box((0.55, 0.05, 0.6), at=(-0.15, 0.3, 0), color='cream')  # seat
    m.box((0.06, 0.32, 0.6), at=(-0.45, 0.48, 0), color='cream', rot=('z', 10))
    m.box((0.08, 0.3, 0.58), at=(0.6, 0.32, 0), color='grey')  # front grille
    for y in np.linspace(0.2, 0.44, 6):
        m.rod((0.65, y, -0.28), (0.65, y, 0.28), 0.006, color='black')
    m.box((0.02, 0.1, 0.3), at=(0.68, 0.12, 0), color='white')
    m.text('IYA', 0.07, 0.01, at=(0.695, 0.12, 0), color='navy', rot=('y', 90))
    m.text('13', 0.14, 0.02, at=(-0.1, 0.42, 0.36), color='navy')
    for s in (-1, 1):  # handle
        m.rod((-0.5, 0.6, s * 0.3), (-0.75, 1.35, s * 0.3), 0.025, color='chrome', metal=0.8)
    m.rod((-0.75, 1.35, -0.32), (-0.75, 1.35, 0.32), 0.04, color='black')
    for x in (-0.38, 0.45):
        for z in (-0.38, 0.38):
            m.cyl(0.14, 0.07, at=(x, 0.14, z), axis='z', color='rubber')
            m.cyl(0.07, 0.08, at=(x, 0.14, z), axis='z', color='white')
    return m

def smartwatch():
    m = Model('Smartwatch')
    m.rbox((0.6, 0.18, 0.7), 0.12, at=(0, 0, 0), color='charcoal', rot=('x', 90), metal=0.4, rough=0.3)
    m.rbox((0.5, 0.6, 0.02), 0.1, at=(0, 0, 0.09), color='black', rough=0.1, rot=None) if False else None
    m.box((0.48, 0.58, 0.02), at=(0, 0, 0.1), color='navy', rough=0.1)
    m.text('20', 0.16, 0.02, at=(-0.1, 0.08, 0.115), color='mint')
    m.text('13', 0.16, 0.02, at=(0.12, 0.08, 0.115), color='orange')
    for i, x in enumerate((-0.14, 0, 0.14)):
        m.cyl(0.045, 0.02, at=(x, -0.17, 0.115), axis='z', color=['red', 'yellow', 'sky'][i])
    m.cyl(0.05, 0.08, at=(0.34, 0.08, 0), axis='x', color='chrome', metal=0.8)
    band = trimesh.creation.torus(major_radius=0.5, minor_radius=0.04, major_sections=48, minor_sections=12)
    band.apply_scale([1, 1, 4.5]); band.apply_transform(R('y', 90)); band.apply_translation([0, 0, -0.45])
    m.add(band, 'orange', rough=0.6)
    for y in np.linspace(-0.35, -0.6, 4):
        m.cyl(0.015, 0.36, at=(0, y, -0.45 + np.sqrt(max(0, 0.25 - y * y))), axis='x', color='darkwood') if abs(y) < 0.5 else None
    return m

def drone(variant='hudsen'):
    m = Model('Drone')
    m.rbox((0.55, 0.18, 0.4), 0.06, at=(0, 0.2, 0), color='white' if variant == 'hudsen' else 'grey', rough=0.35)
    m.box((0.2, 0.05, 0.2), at=(0, 0.32, 0), color='black')
    if variant == 'hudsen':
        m.text('13', 0.12, 0.02, at=(0.2, 0.2, 0.205), color='navy')
    else:
        m.sph(0.1, at=(0.2, 0.1, 0), color='black', rough=0.1)  # camera
    for sx in (-1, 1):
        for sz in (-1, 1):
            tip = np.array([sx * 0.6, 0.24, sz * 0.48])
            m.rod((sx * 0.15, 0.22, sz * 0.12), tip, 0.025, color='charcoal')
            m.cyl(0.05, 0.12, at=tip + (0, 0.04, 0), color='black')
            for a in (0, 90):
                m.box((0.42, 0.01, 0.04), at=tip + (0, 0.11, 0), color='sky' if variant == 'hudsen' else 'orange', rot=('y', a + sx * sz * 20))
            m.rod(tip, tip + (0, -0.15, 0), 0.015, color='grey')
    if variant == 'celeste':
        m.tube([(0.0, 0.1, 0), (-0.05, -0.2, 0.1), (0.1, -0.6, 0.15), (0.0, -1.0, 0.1)], 0.01, color='black')
        ban = Polygon([(-0.12, 0), (0.12, 0), (0.25, -0.9), (-0.25, -0.9)])
        m.ext(ban, 0.02, at=(0.0, 0.05, 0.25), color='cream', rot=('x', 10))
        m.text('COHORT13', 0.1, 0.02, at=(0.0, -0.4, 0.3), color='navy', rot=[('z', 90), ('x', 10)])
        for i in range(5):
            fl = Polygon([(-0.05, 0), (0.05, 0), (0, -0.18)])
            m.ext(fl, 0.02, at=(-0.2 + i * 0.1, -0.9, 0.38), color='orange' if i % 2 else 'red')
    return m

def drone_hudsen(): return drone('hudsen')
def drone_celeste(): return drone('celeste')

def sewing_machine():
    m = Model('Sewing machine')
    m.rbox((1.1, 0.12, 0.6), 0.04, at=(0, 0.06, 0), color='wood')
    m.box((1.0, 0.1, 0.5), at=(0, 0.17, 0), color='black', rough=0.3)
    m.rbox((0.3, 0.6, 0.3), 0.08, at=(0.35, 0.52, 0), color='black', rough=0.3)  # pillar
    m.rbox((0.95, 0.22, 0.26), 0.1, at=(0.0, 0.88, 0), color='black', rough=0.3)  # arm
    m.rbox((0.18, 0.5, 0.22), 0.06, at=(-0.38, 0.64, 0), color='black', rough=0.3)  # head
    m.rod((-0.38, 0.4, 0.05), (-0.38, 0.25, 0.05), 0.012, color='chrome', metal=0.9)  # needle bar
    m.box((0.06, 0.02, 0.08), at=(-0.38, 0.24, 0.05), color='chrome', metal=0.9)
    m.cyl(0.05, 0.12, at=(0.0, 1.05, 0.0), color='white')  # spool
    m.cyl(0.015, 0.2, at=(0.0, 1.05, 0.0), color='brass', metal=0.7)
    # gold scroll decals
    for x in np.linspace(-0.3, 0.3, 4):
        m.tor(0.04, 0.008, at=(x, 0.88, 0.13), axis='z', color='gold', metal=0.7)
    m.text('13', 0.1, 0.01, at=(0.35, 0.55, 0.155), color='gold', metal=0.7)
    # flywheel with spokes
    spokes_wheel(m, 0.22, (0.55, 0.88, 0), axis='x', tire='chrome', rim='chrome', spokes=6, w=0.04)
    return m

def pet_carrier():
    m = Model('Pet carrier')
    side = Polygon([(-0.45, 0), (0.45, 0), (0.45, 0.8)] + [(0.45 * np.cos(a), 0.8 + 0.25 * np.sin(a)) for a in np.linspace(0, np.pi, 20)] + [(-0.45, 0.8)])
    m.ext(side, 0.7, color='sky', rough=0.5)
    win = sbox(-0.3, 0.12, 0.3, 0.75).buffer(0.08)
    m.ext(win, 0.02, at=(0, 0, 0.355), color='charcoal')
    for x in np.linspace(-0.3, 0.3, 7):
        m.rod((x, 0.08, 0.37), (x, 0.8, 0.37), 0.01, color='chrome', metal=0.8)
    m.sph(0.18, at=(0, 0.5, 0.2), scale=(1, 0.9, 0.8), color='orange')  # pet
    for s in (-1, 1):
        m.cone(0.07, 0.0, 0.12, at=(s * 0.11, 0.68, 0.2), color='orange')
        m.sph(0.025, at=(s * 0.06, 0.53, 0.34), color='black')
    m.tube([(-0.2, 1.05, 0), (0, 1.2, 0), (0.2, 1.05, 0)], 0.03, color='black')
    m.box((0.95, 0.06, 0.74), at=(0, 0.03, 0), color='navy')
    return m

def suitcase():
    m = Model('Suitcase')
    m.rbox((1.0, 0.45, 0.62), 0.07, at=(0, 0.23, 0), color='leather', rough=0.6)
    m.rbox((0.8, 0.35, 0.5), 0.06, at=(0, 0.64, 0), color='oak', rough=0.6)
    for y, w, d in ((0.23, 1.0, 0.62), (0.64, 0.8, 0.5)):
        m.box((w + 0.01, 0.025, d + 0.01), at=(0, y, 0), color='darkwood')
        for x in (-w / 2 + 0.03, w / 2 - 0.03):
            for z in (-d / 2 + 0.03, d / 2 - 0.03):
                m.sph(0.04, at=(x, y + 0.18 * (1 if y < 0.5 else 0.85), z), color='brass', metal=0.8)
    for s in (-0.25, 0.25):
        m.box((0.05, 0.47, 0.64), at=(s, 0.23, 0), color='brown')
    m.tube([(-0.12, 0.26, 0.31), (-0.1, 0.32, 0.35), (0.1, 0.32, 0.35), (0.12, 0.26, 0.31)], 0.025, color='darkwood')
    m.tube([(-0.1, 0.82, 0), (-0.08, 0.9, 0), (0.08, 0.9, 0), (0.1, 0.82, 0)], 0.02, color='darkwood')
    m.box((0.08, 0.06, 0.02), at=(0.3, 0.42, 0.31), color='brass', metal=0.8)
    m.text('13', 0.1, 0.01, at=(0, 0.64, 0.255), color='cream')
    return m

def top_hat_april():
    m = Model('Top hat (April Ortiz)')
    m.lathe([(0, 0), (0.62, 0), (0.66, 0.03), (0.6, 0.05), (0.36, 0.05), (0.38, 0.85), (0.33, 0.85), (0.31, 0.06), (0, 0.06)], color='black', rough=0.5)
    m.lathe([(0.355, 0.08), (0.37, 0.08), (0.375, 0.22), (0.36, 0.22)], color='red')
    # plush horse peeking
    m.sph(0.24, at=(0, 0.92, 0), scale=(1, 0.8, 0.9), color='cream', rough=0.95)
    m.sph(0.15, at=(0, 0.88, 0.2), scale=(0.9, 0.7, 1), color='tan', rough=0.95)
    for s in (-1, 1):
        m.sph(0.03, at=(s * 0.09, 0.98, 0.18), color='black', rough=0.2)
        m.cone(0.07, 0.01, 0.17, at=(s * 0.14, 1.14, -0.02), color='cream', rot=('z', -s * 20))
        m.sph(0.08, at=(s * 0.28, 0.86, 0.15), scale=(1, 0.6, 1.2), color='cream')  # hooves on brim
    m.tor(0.18, 0.025, at=(0, 0.86, 0.02), color='navy', rot=('x', 20))  # bridle
    return m

def toaster():
    m = Model('Toaster oven')
    m.rbox((0.95, 0.6, 0.55), 0.16, at=(0, 0.35, 0), color='chrome', metal=0.85, rough=0.25)
    m.box((1.0, 0.08, 0.6), at=(0, 0.04, 0), color='black')
    for z in (-0.12, 0.12):
        m.box((0.7, 0.03, 0.08), at=(0, 0.66, z), color='black')
    m.box((0.06, 0.28, 0.02), at=(-0.38, 0.38, 0.28), color='black')
    m.box((0.1, 0.05, 0.06), at=(-0.38, 0.42, 0.31), color='black')
    m.cyl(0.04, 0.03, at=(-0.38, 0.16, 0.28), axis='z', color='black')
    m.text('1', 0.4, 0.07, at=(-0.15, 0.82, -0.12), color='oak', rot=('y', 90))
    m.text('3', 0.4, 0.07, at=(0.15, 0.82, 0.12), color='oak', rot=('y', 90))
    return m

def pendulum_clock():
    m = Model('Pendulum clock')
    m.box((0.75, 0.12, 0.5), at=(0, 0.06, 0), color='darkwood')
    pts = [(-0.25 + 0.05 * np.sin(y * 6), y) for y in np.linspace(0.12, 1.6, 30)]
    left = [(x, y) for x, y in pts]; right = [(-x + 0.0, y) for x, y in pts[::-1]]
    case = Polygon(left + right)
    inner = Polygon([(x + 0.07, y) for x, y in left[2:-3]] + [(-x - 0.07, y) for x, y in pts[2:-3][::-1]])
    m.ext(case.difference(inner), 0.36, color='wood')
    m.box((0.36, 1.2, 0.02), at=(0, 0.8, -0.17), color='darkwood')
    m.cyl(0.38, 0.22, at=(0, 1.85, 0), axis='z', color='wood')
    m.cyl(0.32, 0.23, at=(0, 1.85, 0), axis='z', color='cream')
    sp = [(0.03 * t * np.cos(t), 1.85 + 0.03 * t * np.sin(t), 0.12) for t in np.linspace(0, 3.2 * np.pi, 80)]
    m.tube(sp, 0.01, color='black')
    m.rod((0, 1.85, 0.13), (0.22, 1.95, 0.13), 0.015, color='black')
    m.rod((0, 1.6, 0.0), (0.04, 0.85, 0.0), 0.015, color='brass', metal=0.8)
    m.cyl(0.12, 0.04, at=(0.045, 0.78, 0), axis='z', color='brass', metal=0.8)
    return m

def garden_hose():
    m = Model('Garden hose')
    coil = [(0.45 * np.cos(t), 0.06 + 0.012 * t, 0.45 * np.sin(t)) for t in np.linspace(0, 6 * np.pi, 160)]
    end = coil[-1]
    rise = list(bez(end, (0.6, 0.3, 0.3), (0.7, 0.9, 0.0), (0.45, 1.25, 0.0), 30))[1:]
    m.tube(coil + [tuple(p) for p in rise], 0.055, color='green', rough=0.5)
    m.rod((0.45, 1.25, 0), (0.25, 1.35, 0), 0.06, color='brass', metal=0.8)
    m.cone(0.06, 0.03, 0.12, at=(0.18, 1.39, 0), color='brass', metal=0.8, axis='x')
    for i in range(7):
        a = np.radians(150 + i * 6)
        m.rod((0.12, 1.4, 0), (0.12 + 0.35 * np.cos(a), 1.4 + 0.35 * np.sin(a), (i - 3) * 0.03), 0.008, color='sky', alpha=0.7)
    m.text('COHORT 13', 0.08, 0.02, at=(0, 0.2, 0.5), color='cream')
    return m

def scooter():
    m = Model('Electric scooter')
    m.rbox((1.1, 0.06, 0.25), 0.05, at=(0, 0.16, 0), color='charcoal')
    m.text('IYA 30', 0.09, 0.01, at=(0.0, 0.195, 0.0), color='mint', rot=('x', -90))
    for x in (-0.62, 0.62):
        m.tor(0.13, 0.04, at=(x, 0.14, 0), axis='z', color='rubber')
        m.cyl(0.09, 0.06, at=(x, 0.14, 0), axis='z', color='mint')
    m.rod((0.5, 0.18, 0), (0.62, 0.14, 0), 0.03, color='grey')
    m.rod((-0.55, 0.2, 0), (-0.62, 0.14, 0), 0.03, color='grey')
    m.box((0.3, 0.03, 0.2), at=(-0.62, 0.3, 0), color='charcoal', rot=('z', -15))
    m.rod((0.62, 0.14, 0), (0.5, 1.25, 0), 0.035, color='grey', metal=0.6)
    m.rod((0.5, 1.25, -0.3), (0.5, 1.25, 0.3), 0.03, color='black')
    m.cyl(0.04, 0.02, at=(0.55, 0.9, 0), axis='x', color='yellow')
    return m

def office_desk():
    m = Model('Office desk')
    m.rbox((1.6, 0.08, 0.75), 0.03, at=(0, 0.75, 0), color='oak')
    m.rbox((0.55, 0.012, 0.32), 0.06, at=(0.2, 0.795, 0), color='black', rough=0.2)  # tablet inset
    for x in (-0.65, 0.65):
        e = Polygon([(-0.08, 0), (0.08, 0), (0.08, 0.71), (-0.08, 0.71)])
        m.box((0.14, 0.71, 0.7), at=(x, 0.355, 0), color='white')
        for y in (0.2, 0.47):
            m.box((0.15, 0.16, 0.5), at=(x, y, 0.1), color='lightgrey')
    m.text('IYA', 0.14, 0.02, at=(-0.65, 0.47, 0.36), color='navy')
    m.text('C13', 0.12, 0.02, at=(-0.65, 0.2, 0.36), color='navy')
    return m

def tripod():
    m = Model('Smartphone tripod')
    m.rod((0, 0.55, 0), (0, 1.15, 0), 0.03, color='black')
    m.box((0.1, 0.1, 0.1), at=(0, 0.55, 0), color='charcoal')
    for a in (0, 120, 240):
        t = np.radians(a)
        m.rod((0, 0.55, 0), (0.55 * np.cos(t), 0.0, 0.55 * np.sin(t)), 0.025, color='black')
        m.sph(0.03, at=(0.55 * np.cos(t), 0.0, 0.55 * np.sin(t)), color='rubber')
    m.box((0.12, 0.14, 0.08), at=(0, 1.2, 0), color='charcoal')
    m.box((0.4, 0.06, 0.12), at=(0, 1.3, 0), color='black')  # clamp
    m.rbox((0.38, 0.75, 0.04), 0.05, at=(0, 1.66, 0), color='black', rot=('x', 90), rough=0.2)
    m.box((0.33, 0.66, 0.01), at=(0, 1.66, 0.025), color='sky', rough=0.05)
    m.box((0.4, 0.06, 0.12), at=(0, 2.02, 0), color='black')
    return m

def office_chair():
    m = Model('Office chair')
    back = Polygon([(-0.35, 0), (0.35, 0), (0.38, 0.8), (0.3, 1.0), (0.0, 1.08), (-0.3, 1.0), (-0.38, 0.8)])
    m.ext(back, 0.1, at=(0, 0.75, -0.32), color='brown', rot=('x', -8))
    m.ext(back.buffer(-0.07), 0.1, at=(0, 0.75, -0.27), color='red', rot=('x', -8), rough=0.9)
    m.rbox((0.8, 0.15, 0.7), 0.1, at=(0, 0.68, 0.02), color='red', rough=0.9)
    m.box((0.82, 0.08, 0.72), at=(0, 0.58, 0.02), color='brown')
    for s in (-1, 1):
        arc = [(s * 0.42, 0.62, 0.35)] + [(s * 0.42, 0.85 + 0.12 * np.sin(t), 0.35 - 0.6 * t / np.pi) for t in np.linspace(0, np.pi, 12)]
        m.tube(arc, 0.04, color='brown')
        m.sph(0.06, at=(s * 0.42, 0.85, 0.37), color='gold', metal=0.7)
    for x in (-0.33, 0.33):
        for z in (-0.28, 0.32):
            m.rod((x, 0.56, z), (x * 1.08, 0.03, z * 1.1), 0.04, color='brown')
            m.sph(0.05, at=(x * 1.08, 0.03, z * 1.1), color='gold', metal=0.7)
    m.ext(Point(0, 0).buffer(0.1), 0.02, at=(0, 1.86, -0.45), color='gold', metal=0.7)
    return m

def power_station():
    m = Model('Portable power station')
    m.rbox((1.0, 0.45, 0.5), 0.05, at=(0, 0.225, 0), color='charcoal')
    m.rbox((0.6, 0.3, 0.42), 0.04, at=(-0.1, 0.6, 0), color='grey')
    m.rbox((0.3, 0.22, 0.32), 0.03, at=(-0.1, 0.86, 0), color='charcoal')
    for i, x in enumerate((-0.3, 0.0, 0.3)):
        m.box((0.16, 0.18, 0.02), at=(x, 0.22, 0.255), color='white')
        for dx in (-0.03, 0.03):
            m.box((0.012, 0.05, 0.01), at=(x + dx, 0.24, 0.27), color='black')
        m.cyl(0.015, 0.01, at=(x, 0.18, 0.27), axis='z', color='black')
    for x in (-0.25, -0.1, 0.05):
        m.box((0.1, 0.1, 0.02), at=(x, 0.6, 0.215), color='white')
    m.box((0.18, 0.1, 0.02), at=(-0.1, 0.86, 0.165), color='mint')
    m.rod((-0.1, 0.97, 0), (-0.1, 1.5, 0), 0.012, color='black')
    m.ext(sbox(0, 0, 0.35, 0.22), 0.01, at=(-0.1, 1.38, 0), color='yellow')
    m.text('13', 0.1, 0.012, at=(0.07, 1.38, 0.0), color='black')
    m.tube([(-0.5, 0.25, 0.2), (-0.7, 0.2, 0.3), (-0.8, 0.05, 0.45), (-0.9, 0.02, 0.6)], 0.02, color='black')
    m.box((0.1, 0.08, 0.06), at=(-0.92, 0.04, 0.62), color='white')
    return m

def binoculars():
    m = Model('Binoculars')
    for z in (-0.25, 0.25):
        m.lathe([(0, 0), (0.17, 0), (0.17, 0.5), (0.2, 0.62), (0.2, 0.8), (0, 0.8)], axis='x', at=(-0.4, 0.3, z), color='black', rough=0.6)
        m.cyl(0.19, 0.02, at=(0.41, 0.3, z), axis='x', color='sky', rough=0.05, metal=0.3)
        m.cyl(0.11, 0.15, at=(-0.45, 0.3, z), axis='x', color='charcoal')
        m.tor(0.172, 0.015, at=(0.0, 0.3, z), axis='x', color='brass', metal=0.8)
    m.box((0.35, 0.08, 0.3), at=(-0.15, 0.42, 0), color='charcoal')
    m.cyl(0.06, 0.12, at=(-0.15, 0.48, 0), axis='z', color='grey')
    m.text('13', 0.25, 0.08, at=(0.35, 0.15, 0.6), color='orange')
    return m

def snow_shovel():
    m = Model('Snow shovel')
    blade = Polygon([(-0.4, 0), (0.4, 0), (0.35, 0.55), (-0.35, 0.55)])
    m.ext(blade, 0.04, at=(0, 0, 0), color='red', rot=('x', -70), rough=0.4)
    m.box((0.8, 0.04, 0.03), at=(0, 0.005, 0.0), color='chrome', metal=0.8)
    for s in (-1, 1):
        m.box((0.03, 0.12, 0.5), at=(s * 0.37, 0.07, -0.2), color='red', rot=('x', -70))
    m.rod((0, 0.4, -0.12), (0, 1.55, -0.55), 0.03, color='oak')
    m.tube([(-0.1, 1.55, -0.55), (-0.1, 1.68, -0.6), (0.1, 1.68, -0.6), (0.1, 1.55, -0.55)], 0.025, color='black')
    m.rod((-0.1, 1.55, -0.55), (0.1, 1.55, -0.55), 0.025, color='black')
    return m

def fortune_teller():
    m = Model('Fortune telling machine')
    m.box((0.8, 0.85, 0.6), at=(0, 0.425, 0), color='darkwood')
    m.box((0.8, 0.85, 0.6), at=(0, 1.3, 0), color='wood')
    m.box((0.66, 0.7, 0.02), at=(0, 1.3, 0.3), color='glass', alpha=0.45, rough=0.05)
    m.box((0.9, 0.08, 0.7), at=(0, 1.76, 0), color='brass', metal=0.7, rough=0.4)
    m.box((0.85, 0.15, 0.65), at=(0, 1.86, 0), color='darkwood')
    # fortune teller figure
    m.sph(0.13, at=(0, 1.4, 0), color='tan')
    m.cone(0.16, 0.0, 0.25, at=(0, 1.6, 0), color='purple')
    m.cone(0.25, 0.15, 0.35, at=(0, 1.13, 0), color='purple')
    m.sph(0.08, at=(0, 1.08, 0.18), color='sky', alpha=0.8)
    for s in (-1, 1):
        m.rod((s * 0.18, 1.2, 0), (s * 0.08, 1.08, 0.18), 0.03, color='purple')
    m.text('ORDRE', 0.09, 0.02, at=(0, 1.55, 0.295), color='gold', metal=0.7)
    m.box((0.18, 0.12, 0.03), at=(0, 0.6, 0.31), color='brass', metal=0.7)
    m.box((0.1, 0.02, 0.04), at=(0, 0.62, 0.33), color='black')
    m.cyl(0.04, 0.03, at=(0.25, 0.5, 0.31), axis='z', color='brass', metal=0.7)
    m.box((0.3, 0.02, 0.03), at=(0, 0.3, 0.31), color='black')
    for x in (-0.4, 0.4):
        m.box((0.06, 1.75, 0.06), at=(x, 0.87, 0.3), color='brass', metal=0.7)
    return m

def vacuum():
    m = Model('Vacuum cleaner')
    m.rbox((0.8, 0.5, 0.6), 0.18, at=(0, 0.25, 0), color='red', rough=0.35)
    m.rbox((0.76, 0.12, 0.56), 0.16, at=(0, 0.55, 0), color='charcoal')
    m.tube([(-0.2, 0.6, 0), (-0.2, 0.9, 0), (0.2, 0.9, 0), (0.2, 0.6, 0)], 0.045, color='charcoal')
    for x in (-0.12, 0.12):
        m.sph(0.06, at=(x, 0.3, 0.3), scale=(0.7, 1, 0.4), color='white')
        m.sph(0.03, at=(x, 0.3, 0.33), color='black')
    for x in (-0.3, 0.3):
        for z in (-0.25, 0.25):
            m.cyl(0.06, 0.05, at=(x, 0.0, z), axis='x', color='black')
    hose = [(0.3, 0.2, 0.25), (0.6, 0.15, 0.5), (0.9, 0.25, 0.4), (1.0, 0.7, 0.0), (0.8, 1.2, -0.3)]
    pts = []
    for i in range(len(hose) - 1):
        a, b = np.array(hose[i]), np.array(hose[i + 1])
        for t in np.linspace(0, 1, 10, endpoint=False): pts.append(a + (b - a) * t)
    pts.append(np.array(hose[-1]))
    m.tube(pts, 0.07, color='grey')
    for p in pts[::2]:
        m.sph(0.075, at=p, scale=(1, 1, 1), color='charcoal')
    return m

def skateboard():
    m = Model('Skateboard')
    deck = sbox(-0.7, -0.2, 0.7, 0.2).buffer(0.0).union(Point(-0.7, 0).buffer(0.2)).union(Point(0.7, 0).buffer(0.2))
    d = m.ext(deck, 0.04, color='oak', rot=('x', 90), at=(0, 0.3, 0))
    v = d.vertices; ends = np.abs(v[:, 0]) > 0.65; v[ends, 1] += (np.abs(v[ends, 0]) - 0.65) * 0.6
    m.ext(deck.buffer(-0.01), 0.005, color='black', rot=('x', 90), at=(0, 0.322, 0))
    m.text('IYA 13', 0.14, 0.01, at=(0, 0.278, 0), color='orange', rot=[('x', 90)])
    for x in (-0.5, 0.5):
        m.box((0.1, 0.08, 0.3), at=(x, 0.24, 0), color='chrome', metal=0.8)
        m.rod((x, 0.17, -0.25), (x, 0.17, 0.25), 0.02, color='chrome', metal=0.8)
        for z in (-0.22, 0.22):
            m.cyl(0.07, 0.06, at=(x, 0.17, z), axis='z', color='yellow', rough=0.5)
    return m

def astronaut_helmet():
    m = Model('Astronaut helmet')
    m.sph(0.55, at=(0, 0.6, 0), color='white', rough=0.4)
    vis = trimesh.creation.icosphere(subdivisions=3, radius=0.565)
    keep = vis.vertices[vis.faces].mean(1); vis.update_faces((keep[:, 2] > 0.18) & (np.abs(keep[:, 1]) < 0.38)); vis.remove_unreferenced_vertices()
    m.add(vis, 'gold', at=(0, 0.6, 0), metal=0.9, rough=0.15)
    m.cyl(0.5, 0.18, at=(0, 0.08, 0), color='lightgrey', metal=0.5)
    m.tor(0.5, 0.05, at=(0, 0.17, 0), color='grey', metal=0.5)
    m.cyl(0.12, 0.04, at=(0.45, 0.65, 0.2), axis='x', color='grey')
    m.text('13', 0.14, 0.02, at=(0.42, 0.8, -0.25), color='navy', rot=('y', 120))
    hose = [(0.35, 0.2, 0.3), (0.5, 0.1, 0.35), (0.62, 0.0, 0.25)]
    m.tube(hose, 0.05, color='grey')
    for p in np.linspace(np.array(hose[0]), np.array(hose[-1]), 6):
        m.tor(0.055, 0.012, at=p, axis='x', color='charcoal')
    m.rod((0.35, 0.95, -0.2), (0.6, 1.5, -0.3), 0.012, color='grey')
    m.ext(Polygon([(0, 0), (0.35, -0.08), (0, -0.25)]), 0.01, at=(0.6, 1.5, -0.3), color='red')
    m.text('C13', 0.07, 0.012, at=(0.72, 1.4, -0.29), color='white')
    return m

def dumbbells():
    m = Model('Exercise weights')
    for z, c in ((-0.3, 'charcoal'), (0.3, 'red')):
        m.rod((-0.45, 0.15, z), (0.45, 0.15, z), 0.04, color='chrome', metal=0.85)
        for x in (-0.38, -0.27, 0.27, 0.38):
            m.cyl(0.15 if abs(x) > 0.3 else 0.13, 0.1, at=(x, 0.15, z), axis='x', color=c, seg=6 if c == 'charcoal' else 40)
    m.lathe([(0, 0), (0.25, 0), (0.22, 0.35), (0.12, 0.45), (0, 0.45)], at=(0.0, 0, -0.9), color='orange')  # kettlebell body
    m.tor(0.13, 0.035, at=(0.0, 0.55, -0.9), axis='z', color='orange')
    m.text('13', 0.12, 0.02, at=(0, 0.2, -0.665), color='white')
    return m

def toolbox():
    m = Model('Toolbox')
    m.box((1.0, 0.45, 0.5), at=(0, 0.225, 0), color='red', metal=0.3, rough=0.4)
    m.box((1.02, 0.08, 0.52), at=(0, 0.48, 0), color='red', metal=0.3, rough=0.4)
    m.ext(Polygon([(-0.5, 0), (0.5, 0), (0.3, 0.12), (-0.3, 0.12)]), 0.5, at=(0, 0.52, 0), color='red', metal=0.3, rough=0.4)
    m.rod((-0.25, 0.75, 0), (0.25, 0.75, 0), 0.03, color='black')
    for x in (-0.25, 0.25):
        m.rod((x, 0.64, 0), (x, 0.75, 0), 0.02, color='chrome', metal=0.8)
    for x in (-0.35, 0.35):
        m.box((0.1, 0.06, 0.03), at=(x, 0.42, 0.26), color='chrome', metal=0.8)
    m.text('13', 0.15, 0.02, at=(0, 0.22, 0.26), color='white')
    m.rod((0.45, 0.66, 0.1), (0.75, 0.95, 0.1), 0.03, color='oak')  # hammer peeking
    m.box((0.1, 0.1, 0.25), at=(0.78, 0.98, 0.1), color='steel', metal=0.8, rot=('z', 45))
    return m
