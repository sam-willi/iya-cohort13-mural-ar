from mk import *
import numpy as np
from shapely.geometry import Polygon, Point, box as sbox
from shapely import affinity

def boombox():
    m = Model('Boom box')
    m.rbox((1.6, 0.8, 0.45), 0.06, color='charcoal')
    for x in (-0.52, 0.52):
        m.cyl(0.27, 0.04, at=(x, -0.02, 0.23), axis='z', color='iron')
        m.cyl(0.22, 0.05, at=(x, -0.02, 0.24), axis='z', color='black')
        m.cyl(0.07, 0.07, at=(x, -0.02, 0.25), axis='z', color='chrome', metal=0.8, rough=0.3)
    m.box((0.5, 0.32, 0.04), at=(0, -0.08, 0.23), color='sky', rough=0.2)
    m.box((0.36, 0.14, 0.05), at=(0, -0.08, 0.235), color='cream')
    for i, x in enumerate(np.linspace(-0.2, 0.2, 5)):
        m.box((0.06, 0.04, 0.05), at=(x, 0.22, 0.23), color='orange' if i == 2 else 'lightgrey')
    m.box((0.5, 0.05, 0.03), at=(0, 0.32, 0.23), color='black')
    # handle
    m.rod((-0.55, 0.4, 0), (-0.55, 0.62, 0), 0.035, color='chrome', metal=0.8, rough=0.3)
    m.rod((0.55, 0.4, 0), (0.55, 0.62, 0), 0.035, color='chrome', metal=0.8, rough=0.3)
    m.rod((-0.55, 0.62, 0), (0.55, 0.62, 0), 0.045, color='black')
    m.rod((0.6, 0.4, -0.1), (0.9, 0.85, -0.1), 0.012, color='chrome', metal=0.9)  # antenna
    return m

def jukebox():
    m = Model('Jukebox')
    body = Polygon([(-0.5, 0), (0.5, 0), (0.5, 1.15)] + [(0.5 * np.cos(a), 1.15 + 0.5 * np.sin(a)) for a in np.linspace(0, np.pi, 24)] + [(-0.5, 1.15)])
    m.ext(body, 0.5, color='wood')
    m.ext(affinity.scale(body, 0.78, 0.86, origin=(0, 0)), 0.04, at=(0, 0.13, 0.26), color='orange', rough=0.3)
    # side neon pillars
    for x in (-0.47, 0.47):
        m.box((0.08, 1.15, 0.08), at=(x, 0.6, 0.24), color='yellow', rough=0.2)
    # glass window with records
    m.box((0.6, 0.35, 0.03), at=(0, 1.15, 0.29), color='glass', alpha=0.85, rough=0.1)
    for i in range(5):
        m.cyl(0.12, 0.01, at=(-0.24 + i * 0.12, 1.12, 0.27), axis='x', color='black')
    m.text('13', 0.22, 0.05, at=(0, 1.45, 0.27), color='cream')
    # grille diamond lattice
    m.box((0.58, 0.5, 0.03), at=(0, 0.45, 0.29), color='brass', metal=0.7, rough=0.35)
    for i in range(-3, 4):
        m.rod((-0.28, 0.2 + 0.0, 0.31), (0.28, 0.7, 0.31), 0.008, color='darkwood') if i == 0 else None
    for t in np.linspace(-0.25, 0.25, 6):
        m.rod((t - 0.12, 0.22, 0.31), (t + 0.12, 0.68, 0.31), 0.01, color='darkwood')
        m.rod((t + 0.12, 0.22, 0.31), (t - 0.12, 0.68, 0.31), 0.01, color='darkwood')
    for x in (-0.38, 0.38):
        for z in (-0.18, 0.18):
            m.cyl(0.05, 0.06, at=(x, -0.03, z), color='black')
    return m

def violin():
    m = Model('Violin')
    out = Point(0, 0.3).buffer(0.32, quad_segs=24).union(Point(0, -0.3).buffer(0.38, quad_segs=24))
    waist = Point(-0.42, 0).buffer(0.17).union(Point(0.42, 0).buffer(0.17))
    body = out.union(sbox(-0.25, -0.3, 0.25, 0.3)).difference(waist)
    m.ext(body, 0.16, color='copper', rough=0.25)
    m.ext(body.buffer(-0.02), 0.02, at=(0, 0, 0.09), color='oak', rough=0.25)
    for x in (-0.13, 0.13):  # f-holes
        m.ext(affinity.rotate(sbox(-0.012, -0.12, 0.012, 0.12), 8 if x < 0 else -8), 0.02, at=(x, -0.02, 0.1), color='black')
    m.box((0.1, 0.9, 0.06), at=(0, 0.75, 0.12), color='black', rough=0.3)  # fingerboard
    m.box((0.08, 0.45, 0.08), at=(0, 1.05, 0.05), color='copper')  # neck
    m.box((0.1, 0.22, 0.12), at=(0, 1.35, 0.05), color='copper')  # pegbox
    m.tor(0.06, 0.025, at=(0, 1.5, 0.05), axis='x', color='copper')  # scroll
    for y in (1.28, 1.4):
        m.cyl(0.015, 0.22, at=(0, y, 0.05), axis='x', color='black')
    m.box((0.16, 0.03, 0.06), at=(0, -0.15, 0.13), color='cream')  # bridge
    m.box((0.08, 0.28, 0.04), at=(0, -0.48, 0.11), color='black')  # tailpiece
    for x in (-0.03, -0.01, 0.01, 0.03):
        m.rod((x, -0.38, 0.165), (x, 1.2, 0.16), 0.003, color='chrome', metal=0.9)
    # bow
    m.rod((0.55, -0.7, 0.2), (0.25, 1.1, 0.2), 0.012, color='darkwood')
    m.rod((0.58, -0.65, 0.2), (0.28, 1.1, 0.2), 0.005, color='white')
    return m

def gaming_mouse():
    m = Model('Gaming mouse')
    prof = [(0, 0), (0.42, 0), (0.45, 0.05), (0.43, 0.14), (0.35, 0.22), (0.2, 0.27), (0, 0.29)]
    body = m.lathe(prof, color='charcoal', seg=40)
    body.vertices[:, 2] *= 1.5; body.vertices[:, 0] *= 0.7; body.vertices[:, 1] *= 1.3
    # buttons split + side wings
    m.box((0.015, 0.06, 0.3), at=(0, 0.33, 0.35), color='black')
    m.cyl(0.05, 0.06, at=(0, 0.36, 0.3), axis='x', color='red', rough=0.3)  # wheel
    for s in (-1, 1):
        m.box((0.03, 0.08, 0.45), at=(s * 0.3, 0.1, 0.0), color='red', rough=0.3, rot=('y', s * 8))
        m.box((0.03, 0.03, 0.28), at=(s * 0.17, 0.33, -0.05), color='red', rough=0.3, rot=('y', s * -12))
    m.text('XIII', 0.14, 0.03, at=(0, 0.34, -0.2), color='cream', rot=('x', -80))
    m.rod((0, 0.05, 0.68), (0, 0.05, 0.95), 0.025, color='black')
    return m

def utensil_boat():
    m = Model('Spatula, spoon, fork')
    hull = Polygon([(-0.75, 0.3), (-0.7, 0.05), (-0.5, 0.0), (0.5, 0.0), (0.85, 0.3)])
    m.ext(hull, 0.42, color='wood')
    m.ext(Polygon([(-0.75, 0.0), (0.55, 0.0), (0.85, 0.0), (0.55, 0.0)]).buffer(0) if False else hull.buffer(-0.03), 0.36, at=(0, 0.04, 0), color='darkwood')
    # spatula mast/sail
    m.rod((0, -0.05, 0), (0, 0.85, 0), 0.025, color='black')
    sail = sbox(-0.17, 0, 0.17, 0.42)
    for i in range(4):
        sail = sail.difference(sbox(-0.13 + i * 0.075, 0.08, -0.095 + i * 0.075, 0.36))
    m.ext(sail, 0.025, at=(0, 0.85, 0), color='steel', metal=0.7, rough=0.35)
    m.ext(Polygon([(0, 0), (0.3, 0.08), (0, 0.16)]), 0.01, at=(0.18, 1.12, 0), color='red')
    m.rod((0.02, 1.0, 0), (0.02, 1.32, 0), 0.01, color='black')
    m.text('13', 0.07, 0.015, at=(0.11, 1.2, 0.01), color='cream')
    # spoon oar
    m.rod((0.3, 0.32, 0.22), (0.95, 0.1, 0.5), 0.02, color='steel', metal=0.8, rough=0.3)
    m.sph(0.1, at=(1.02, 0.05, 0.56), scale=(1, 0.35, 1.5), color='steel', metal=0.8, rough=0.3, rot=('y', 40))
    # fork rudder
    m.rod((-0.7, 0.25, 0), (-1.05, -0.1, 0), 0.02, color='steel', metal=0.8, rough=0.3)
    for z in (-0.05, -0.017, 0.017, 0.05):
        m.rod((-1.05, -0.1, z * 0.6), (-1.2, -0.28, z), 0.01, color='steel', metal=0.8)
    return m

def top_hat_lana():
    m = Model('Top hat (Lana Kim)')
    brim = Point(0, 0).buffer(0.55, quad_segs=6)
    brim = affinity.scale(sbox(-0.55, -0.55, 0.55, 0.55).buffer(0.0), 1, 1).buffer(-0.15).buffer(0.15)
    m.ext(brim, 0.04, color='black', rot=('x', 90))
    m.tor(0.5, 0.03, at=(0, 0.02, 0), color='charcoal', rot=('x', 0))
    m.rbox((0.6, 0.6, 0.6), 0.14, at=(0, 0.32, 0), color='black', rough=0.5)
    m.rbox((0.62, 0.1, 0.62), 0.14, at=(0, 0.1, 0), color='red')
    # crescent + star emblem
    cres = Point(0, 0).buffer(0.09).difference(Point(0.04, 0.02).buffer(0.075))
    m.ext(cres, 0.02, at=(0.18, 0.12, 0.32), color='gold', metal=0.7, rough=0.3)
    m.ext(Polygon([(0.06 * np.cos(a) * (1 if i % 2 == 0 else 0.45), 0.06 * np.sin(a) * (1 if i % 2 == 0 else 0.45)) for i, a in enumerate(np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, 10, endpoint=False))]), 0.02, at=(0.28, 0.15, 0.32), color='gold', metal=0.7, rough=0.3)
    m.box((0.18, 0.18, 0.18), at=(-0.05, 0.71, 0.0), color='cream')  # cube on top
    m.box((0.004, 0.2, 0.12), at=(-0.05, 0.98, 0.0), color='white', rot=('y', 20))  # card
    return m

def basketball_baseball():
    m = Model('Basketball + baseball')
    m.sph(0.5, at=(-0.2, 0.5, 0), color='orange', rough=0.8)
    for ax in ('x', 'y'):
        m.tor(0.5, 0.012, at=(-0.2, 0.5, 0), axis=ax, color='black')
    m.tor(0.42, 0.012, at=(-0.2, 0.75, 0), axis='y', color='black')
    m.tor(0.42, 0.012, at=(-0.2, 0.25, 0), axis='y', color='black')
    m.sph(0.2, at=(0.48, 0.2, 0.2), color='white', rough=0.7)
    pts = [(0.48 + 0.2 * np.cos(t) * 1.0, 0.2 + 0.2 * 0.6 * np.sin(2 * t), 0.2 + 0.2 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 60)]
    pts = [np.array(p) for p in pts]
    c = np.array([0.48, 0.2, 0.2]); pts = [c + (p - c) / np.linalg.norm(p - c) * 0.203 for p in pts]
    m.tube(pts, 0.01, color='red', closed=True)
    return m

def aquarium():
    m = Model('Fish aquarium')
    m.box((1.0, 0.25, 0.6), at=(0, 0.125, 0), color='darkwood')
    m.box((1.0, 0.75, 0.6), at=(0, 0.625, 0), color='glass', alpha=0.35, rough=0.05)
    m.box((0.96, 0.55, 0.56), at=(0, 0.53, 0), color='sky', alpha=0.4, rough=0.05)
    m.box((1.04, 0.1, 0.64), at=(0, 1.05, 0), color='black')
    m.box((0.96, 0.06, 0.56), at=(0, 0.28, 0), color='tan')
    for x, y, c in ((-0.15, 0.6, 'orange'), (0.2, 0.75, 'yellow'), (0.0, 0.45, 'red')):
        m.sph(0.07, at=(x, y, 0.05), scale=(1.4, 0.8, 0.5), color=c)
        m.ext(Polygon([(0, 0), (0.09, 0.06), (0.09, -0.06)]), 0.02, at=(x + 0.08, y, 0.05), color=c)
    for x in (-0.38, -0.3, 0.35):
        m.tube([(x, 0.3, -0.15), (x + 0.04, 0.5, -0.15), (x - 0.03, 0.7, -0.15), (x + 0.02, 0.82, -0.15)], 0.02, color='green')
    for i in range(7):
        m.sph(0.018 + 0.006 * (i % 3), at=(0.35 + 0.02 * np.sin(i), 0.4 + i * 0.08, 0.1), color='white', alpha=0.7)
    m.sph(0.08, at=(-0.1, 0.33, -0.1), scale=(1, 0.6, 1), color='red')  # crab
    return m

def motorcycle():
    m = Model('Motorcycle')
    for x in (-0.65, 0.7):
        m.tor(0.32, 0.08, at=(x, 0.32, 0), axis='z', color='rubber')
        m.cyl(0.22, 0.05, at=(x, 0.32, 0), axis='z', color='chrome', metal=0.85, rough=0.25)
    m.rbox((0.55, 0.3, 0.3), 0.08, at=(-0.02, 0.45, 0), color='iron', metal=0.5)  # engine
    m.sph(0.25, at=(0.15, 0.85, 0), scale=(1.4, 0.7, 0.75), color='red', rough=0.25, metal=0.3)  # tank
    m.rbox((0.55, 0.1, 0.32), 0.05, at=(-0.35, 0.85, 0), color='leather')  # seat
    m.rod((0.45, 0.85, 0), (0.7, 0.32, 0), 0.04, color='chrome', metal=0.85)  # fork
    m.rod((0.45, 0.85, 0), (0.5, 1.08, 0), 0.04, color='chrome', metal=0.85)
    m.rod((0.5, 1.08, -0.32), (0.5, 1.08, 0.32), 0.025, color='black')  # bars
    m.cyl(0.09, 0.08, at=(0.62, 0.95, 0), axis='x', color='yellow')  # headlight
    m.rod((-0.65, 0.32, 0), (-0.1, 0.62, 0), 0.04, color='iron')  # swingarm
    m.rod((-0.25, 0.3, 0.18), (-0.85, 0.42, 0.18), 0.04, color='chrome', metal=0.9)  # exhaust
    m.box((0.35, 0.05, 0.25), at=(-0.65, 0.68, 0), color='red', rot=('z', -10))  # fender
    return m

def crystal_ball():
    m = Model('Crystal ball')
    m.box((0.85, 0.35, 0.85), at=(0, 0.175, 0), color='darkwood')
    m.text('ASK', 0.2, 0.04, at=(0, 0.18, 0.43), color='gold', metal=0.6)
    m.cyl(0.32, 0.08, at=(0, 0.39, 0), color='brass', metal=0.7, rough=0.3)
    m.sph(0.42, at=(0, 0.82, 0), color='lilac', alpha=0.55, rough=0.05)
    m.text('13', 0.3, 0.12, at=(0, 0.84, 0), color='white')
    pts = [(0.62 * np.cos(t), 0.82 + 0.06 * np.sin(3 * t), 0.62 * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 80)]
    m.tube(pts, 0.025, color='sky', closed=True)
    for t in np.linspace(0, 2 * np.pi, 6, endpoint=False):
        m.sph(0.03, at=(0.66 * np.cos(t), 0.85, 0.66 * np.sin(t)), color='yellow')
    return m

def rice_cooker():
    m = Model('Rice cooker')
    m.rbox((0.9, 0.55, 0.7), 0.2, at=(0, 0.275, 0), color='white', rough=0.35)
    m.rbox((0.75, 0.04, 0.55), 0.18, at=(0, 0.56, 0), color='lightgrey')
    m.cyl(0.28, 0.03, at=(0, 0.58, 0.0), color='cream')
    for i in range(30):
        a = i * 2.4; r = 0.24 * np.sqrt((i + 0.5) / 30)
        m.sph(0.035, at=(r * np.cos(a), 0.6, r * np.sin(a)), scale=(1, 0.6, 1.4), color='white')
    # open lid hinged at back
    lid = m.rbox((0.86, 0.12, 0.66), 0.2, at=(0, 0.33, 0), color='white', rough=0.35, rot=('x', -80))
    lid.apply_translation((0, 0.55, -0.38 - 0.06))
    m.cyl(0.25, 0.02, at=(0, 0.88, -0.38), axis='z', color='steel', metal=0.6)
    m.box((0.32, 0.14, 0.03), at=(0, 0.3, 0.36), color='navy')
    m.text('13', 0.1, 0.02, at=(0, 0.3, 0.38), color='mint')
    for i, ch in enumerate('DISRUPT'):
        m.text(ch, 0.11, 0.05, at=(-0.18 + i * 0.07, 0.8 + i * 0.09, 0.05 + 0.03 * np.sin(i)), color='cream', rot=('y', 15))
    return m

def hand_mixer():
    m = Model('Hand mixer (Jonathan Bakhash)')
    m.cyl(0.62, 0.06, at=(0, 0.03, 0), color='steel', metal=0.6, rough=0.3)
    m.lathe([(0, 0), (0.42, 0), (0.42, 0.1), (0.36, 0.45), (0.26, 0.62), (0, 0.66)], at=(0, 0.06, 0), color='red', rough=0.35)
    m.tor(0.27, 0.05, at=(0, 0.66, 0), color='charcoal')
    swirl = [(0.22 * (1 - t) * np.cos(10 * t), 0.7 + 0.45 * t, 0.22 * (1 - t) * np.sin(10 * t)) for t in np.linspace(0, 1, 90)]
    m.tube(swirl, 0.07, color='cream')
    for y in (0.25, 0.35, 0.45):
        m.rbox((0.32, 0.05, 0.04), 0.02, at=(0.0, y, 0.38), color='charcoal', rot=('x', -15))
    m.box((0.06, 0.3, 0.04), at=(-0.27, 0.32, 0.29), color='black', rot=('y', -40))
    m.rod((0.3, 0.45, 0), (0.75, 0.62, 0), 0.025, color='chrome', metal=0.85)  # beater arm
    m.sph(0.06, at=(0.77, 0.63, 0), color='chrome', metal=0.85)
    for x in np.linspace(-0.28, 0.28, 6):
        m.cyl(0.02, 0.02, at=(x, 0.12, 0.42), axis='z', color='black')
    return m

def skillet():
    m = Model('Cast iron skillet')
    m.lathe([(0, 0), (0.5, 0), (0.58, 0.14), (0.55, 0.14), (0.47, 0.03), (0, 0.03)], color='iron', metal=0.4, rough=0.7)
    m.ext(Polygon([(0.5, -0.07), (1.15, -0.05), (1.2, 0), (1.15, 0.05), (0.5, 0.07)]), 0.05, rot=('x', 90), at=(0, 0.12, 0), color='iron', metal=0.4, rough=0.7)
    m.cyl(0.04, 0.06, at=(1.12, 0.12, 0), color='cream')  # hole
    for s in (-1, 1):
        m.box((0.12, 0.05, 0.06), at=(0, 0.11, s * 0.56), color='iron')  # pour spouts
    m.text('IYA', 0.28, 0.04, at=(0, 0.06, -0.1), color='charcoal', rot=('x', -90))
    m.text('30', 0.22, 0.04, at=(0, 0.06, 0.18), color='charcoal', rot=('x', -90))
    return m

def car50s():
    m = Model('Car (50s)')
    side = Polygon([(-1.0, 0.15), (1.0, 0.15), (1.05, 0.35), (0.95, 0.45), (0.45, 0.48), (0.25, 0.75), (-0.4, 0.75), (-0.6, 0.48), (-0.95, 0.47), (-1.08, 0.55), (-1.05, 0.3)])
    m.ext(side, 0.8, color='sky', rough=0.3, metal=0.2)
    m.box((0.52, 0.2, 0.82), at=(-0.08, 0.6, 0), color='glass', alpha=0.7, rough=0.1)
    m.box((0.68, 0.03, 0.78), at=(-0.08, 0.76, 0), color='white')  # roof
    m.text('IYA', 0.22, 0.02, at=(-0.08, 0.78, 0), color='red', rot=('x', -90))
    m.box((2.12, 0.06, 0.84), at=(0, 0.33, 0), color='chrome', metal=0.85, rough=0.25)  # trim
    m.box((0.08, 0.14, 0.7), at=(1.05, 0.25, 0), color='chrome', metal=0.85, rough=0.25)  # bumper
    m.box((0.08, 0.14, 0.7), at=(-1.07, 0.25, 0), color='chrome', metal=0.85, rough=0.25)
    m.text('Cohort 13', 0.1, 0.02, at=(0.72, 0.46, 0), color='white', rot=[('x', -90), ('y', 90)])
    for x in (-0.62, 0.62):
        for z in (-0.38, 0.38):
            m.cyl(0.17, 0.12, at=(x, 0.17, z), axis='z', color='rubber')
            m.cyl(0.09, 0.13, at=(x, 0.17, z), axis='z', color='white')
    for z in (-0.28, 0.28):
        m.cyl(0.06, 0.04, at=(1.06, 0.4, z), axis='x', color='yellow')
        m.ext(Polygon([(0, 0), (0.25, 0), (0, 0.12)]), 0.03, at=(-0.95, 0.47, z), color='sky')  # fins
    return m

def backpack():
    m = Model('Backpack')
    m.rbox((0.75, 1.0, 0.35), 0.18, at=(0, 0.55, 0), color='navy', rough=0.8)
    m.sph(0.37, at=(0, 1.02, 0), scale=(1, 0.35, 0.47), color='navy', rough=0.8)
    m.rbox((0.6, 0.45, 0.14), 0.12, at=(0, 0.35, 0.2), color='grey', rough=0.8)  # front pocket
    m.rod((-0.3, 0.12, 0.28), (0.3, 0.58, 0.28), 0.012, color='black')
    m.rod((0.3, 0.12, 0.28), (-0.3, 0.58, 0.28), 0.012, color='black')
    m.tube([(-0.36, 0.8, 0.12), (0, 1.12, 0.14), (0.36, 0.8, 0.12)], 0.012, color='black')  # zipper
    m.tube([(-0.1, 1.15, 0), (0, 1.25, 0), (0.1, 1.15, 0)], 0.03, color='black')  # handle
    for x in (-0.22, 0.22):
        m.tube([(x, 1.0, -0.18), (x * 1.2, 0.9, -0.3), (x * 1.3, 0.4, -0.3), (x * 1.4, 0.1, -0.18)], 0.04, color='black')
    for s in (-1, 1):
        m.rbox((0.12, 0.35, 0.25), 0.05, at=(s * 0.42, 0.3, 0), color='charcoal')  # side mesh
    return m

def contemporary_robot():
    m = Model('Contemporary robot')
    W = 'white'
    m.rbox((0.32, 0.36, 0.3), 0.08, at=(0, 1.72, 0), color=W, rough=0.3)
    m.box((0.24, 0.16, 0.02), at=(0, 1.74, 0.15), color='black', rough=0.2)
    m.text('C13', 0.09, 0.02, at=(0, 1.74, 0.165), color='mint')
    m.cyl(0.06, 0.12, at=(0, 1.5, 0), color='grey')
    m.rbox((0.48, 0.45, 0.3), 0.1, at=(0, 1.22, 0), color=W, rough=0.3)
    m.cyl(0.07, 0.03, at=(0, 1.25, 0.16), axis='z', color='orange')
    m.cyl(0.16, 0.22, at=(0, 0.92, 0), color='grey')
    m.rbox((0.44, 0.18, 0.3), 0.08, at=(0, 0.75, 0), color=W)
    for s in (-1, 1):
        m.sph(0.08, at=(s * 0.3, 1.38, 0), color='grey')
        m.rod((s * 0.32, 1.35, 0), (s * 0.38, 1.05, 0.05), 0.055, color=W)
        m.sph(0.06, at=(s * 0.38, 1.05, 0.05), color='grey')
        m.rod((s * 0.38, 1.05, 0.05), (s * 0.42, 0.8, 0.12 if s < 0 else 0.0), 0.05, color=W)
        m.sph(0.06, at=(s * 0.42, 0.76, 0.12 if s < 0 else 0.0), color='grey')
        m.rod((s * 0.12, 0.68, 0), (s * 0.13, 0.38, 0), 0.07, color=W)
        m.sph(0.07, at=(s * 0.13, 0.36, 0), color='grey')
        m.rod((s * 0.13, 0.36, 0), (s * 0.14, 0.08, 0), 0.065, color=W)
        m.rbox((0.14, 0.07, 0.22), 0.03, at=(s * 0.14, 0.035, 0.04), color='grey')
    return m

def bowler_hat():
    m = Model('Bowler hat')
    m.lathe([(0, 0), (0.62, 0), (0.66, 0.04), (0.6, 0.06), (0.42, 0.05), (0.42, 0.25), (0.38, 0.42), (0.25, 0.52), (0, 0.55)], color='black', rough=0.6)
    m.lathe([(0.425, 0.05), (0.435, 0.05), (0.435, 0.14), (0.425, 0.14)], color='brown', rough=0.4)
    m.box((0.06, 0.08, 0.04), at=(0.42, 0.1, 0.12), color='brown', rot=('y', -20))
    return m

def toilet_paper():
    m = Model('Toilet paper')
    m.lathe([(0.12, 0), (0.42, 0), (0.42, 0.85), (0.12, 0.85)], color='white', rough=0.9, seg=56)
    m.lathe([(0.1, 0), (0.12, 0), (0.12, 0.85), (0.1, 0.85)], color='tan', rough=0.9)
    m.box((0.55, 0.7, 0.012), at=(0, 0.3, 0.43), color='white', rough=0.9)
    m.box((0.55, 0.006, 0.016), at=(0, 0.25, 0.437), color='lightgrey')
    m.box((0.55, 0.012, 0.25), at=(0, -0.045, 0.55), color='white', rough=0.9)
    return m

def tennis_racket():
    m = Model('Tennis racket')
    m.tor(0.36, 0.03, at=(0, 1.0, 0), axis='z', color='red', rough=0.3)
    ring = m.parts[-1]['mesh']; ring.vertices[:, 1] = 1.0 + (ring.vertices[:, 1] - 1.0) * 1.3
    for x in np.linspace(-0.3, 0.3, 11):
        h = 0.47 * np.sqrt(max(0, 1 - (x / 0.36) ** 2))
        m.rod((x, 1.0 - h, 0), (x, 1.0 + h, 0), 0.004, color='white')
    for y in np.linspace(-0.4, 0.4, 13):
        w = 0.36 * np.sqrt(max(0, 1 - (y / 0.47) ** 2))
        m.rod((-w, 1.0 + y, 0), (w, 1.0 + y, 0), 0.004, color='white')
    m.rod((-0.15, 0.6, 0), (0, 0.4, 0), 0.03, color='red')
    m.rod((0.15, 0.6, 0), (0, 0.4, 0), 0.03, color='red')
    m.cyl(0.045, 0.42, at=(0, 0.2, 0), color='black', rough=0.9)
    for y in np.linspace(0.02, 0.38, 9):
        m.tor(0.047, 0.006, at=(0, y, 0), color='white', rot=('x', 12))
    m.cyl(0.05, 0.03, at=(0, -0.01, 0), color='red')
    m.sph(0.1, at=(0.6, 1.25, 0.1), color='#d8e84a', rough=0.9)
    m.tor(0.1, 0.008, at=(0.6, 1.25, 0.1), axis='z', color='white', rot=('y', 40))
    return m

def tv_coaster():
    m = Model('Television screen')
    m.rbox((1.0, 0.72, 0.75), 0.08, at=(0, 0.62, 0), color='wood', rough=0.5)
    m.rbox((0.7, 0.52, 0.05), 0.12, at=(-0.08, 0.64, 0.37), color='charcoal', rough=0.15)
    m.rbox((0.62, 0.44, 0.04), 0.1, at=(-0.08, 0.64, 0.4), color='sky', rough=0.1)
    m.text('IYA', 0.14, 0.02, at=(-0.08, 0.64, 0.42), color='navy')
    for y in (0.78, 0.66):
        m.cyl(0.035, 0.04, at=(0.38, y, 0.39), axis='z', color='brass', metal=0.7)
    for x in (-0.42, 0.42):
        for z in (-0.3, 0.3):
            m.rod((x, 0.26, z), (x * 1.08, 0.0, z * 1.08), 0.03, color='darkwood')
    # rooftop amusement park: roller coaster loop + ferris wheel
    m.box((0.98, 0.02, 0.73), at=(0, 0.99, 0), color='green')
    loop = [(-0.2 + 0.2 * np.sin(t), 1.2 + 0.2 * np.cos(t + np.pi), -0.15 + 0.03 * t) for t in np.linspace(0, 2 * np.pi, 40)]
    m.tube(loop, 0.012, color='red')
    hills = [(x, 1.0 + 0.25 * abs(np.sin(x * 5)), 0.2 * np.cos(x * 3)) for x in np.linspace(-0.45, 0.45, 50)]
    m.tube(hills, 0.012, color='red')
    for x in np.linspace(-0.45, 0.45, 8):
        y = 1.0 + 0.25 * abs(np.sin(x * 5))
        m.rod((x, 1.0, 0.2 * np.cos(x * 3)), (x, y, 0.2 * np.cos(x * 3)), 0.006, color='white')
    m.tor(0.16, 0.008, at=(0.25, 1.2, -0.2), axis='z', color='white')
    for a in np.linspace(0, np.pi, 4, endpoint=False):
        m.rod((0.25 - 0.16 * np.cos(a), 1.2 - 0.16 * np.sin(a), -0.2), (0.25 + 0.16 * np.cos(a), 1.2 + 0.16 * np.sin(a), -0.2), 0.005, color='white')
    m.rod((0.25, 1.2, -0.2), (0.18, 1.0, -0.2), 0.01, color='grey'); m.rod((0.25, 1.2, -0.2), (0.32, 1.0, -0.2), 0.01, color='grey')
    m.cone(0.08, 0.0, 0.1, at=(0.0, 1.06, 0.15), color='red')  # carousel
    m.cyl(0.08, 0.06, at=(0.0, 1.03, 0.15), color='yellow')
    return m
