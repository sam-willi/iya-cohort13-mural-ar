"""Rebuild the 3D renderings from code.

    pip install trimesh shapely mapbox_earcut matplotlib
    python3 tools/models/build.py               # all models -> models/incoming/<id>.glb
    python3 tools/models/build.py typewriter    # just these object ids (or checklist numbers)
    npm run models                              # compress models/incoming/ into models/<id>.glb

Each model is plain Python in objs_*.py, one function per object. Edit a function, rerun,
then compress. Models are exported Y up with the front facing +Z, centred, longest side 1.
manifest_src.py lists which drawing and student each model comes from, and IDS maps each
build function to its object id in data/objects.json.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import objs_a, objs_b, objs_c, objs_d
from manifest_src import ITEMS, IDS

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'models', 'incoming')

def find(fn):
    for mod in (objs_a, objs_b, objs_c, objs_d):
        if hasattr(mod, fn): return getattr(mod, fn)
    raise KeyError(fn)

def main(only):
    os.makedirs(OUT, exist_ok=True)
    entries = []
    for num, name, fn, student, drawing, note in ITEMS:
        oid = IDS[fn]
        entries.append(dict(id=oid, checklist=num, name=name, model=f"models/{oid}.glb",
                            student=student, drawing=drawing, note=note))
        if only and oid not in only and str(num) not in only: continue
        find(fn)().export(os.path.join(OUT, f"{oid}.glb"))
        print('built', oid)
    with open(os.path.join(HERE, 'catalog.json'), 'w') as fh:
        json.dump({'models': entries}, fh, indent=2)

if __name__ == '__main__':
    main(set(sys.argv[1:]))
