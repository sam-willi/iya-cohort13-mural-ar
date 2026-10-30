"""Turn the straightened wall scan into everything the game needs.

    pip install pillow numpy opencv-python-headless
    python3 tools/wall/build.py           # writes data/objects.json, images/mural-wall.webp, tools/wall/build/
    npm run targets                       # compiles tools/wall/build/ into targets/objects/<id>.mind

Inputs are tools/wall/wall.json (calibration, windows, and a pixel box for every product found on the
painted wall) and tools/wall/wall-scan.webp (the wall, straight-on, 2.5 mm per pixel).

Each product gets its own small set of AR targets, so the game only loads the ones for the current riddle:
- a square of wall around the product, about 1.6x its size (0.5 to 1.1 m), which is roughly what a phone
  sees from the 2-3 ft a player can stand back in the hallway;
- for products high on the wall, two more copies pre-tilted the way the wall looks from below with the phone
  tipped up 55-70 degrees. MindAR barely recognises the plain square at those angles. A tilted copy carries
  `H`, which maps mural inches to its image pixels, so the game still knows where everything is.
Simulated phone views (see docs/how-it-works.md) put the right product under the crosshair 137 times in 154.
"""
import json, os, sys
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(HERE, 'build')
PPI = 600 / 72          # target resolution, pixels per inch of wall. Half this failed most close-up views.
HIGH_IN = 2.3 / 0.0254  # products centred more than 2.3 m up get pre-tilted copies
TILTS = {'t55': (0.10, 0.62), 't68': (0.16, 0.42)}   # (top-edge inset, vertical squash) as seen from below

wall = json.load(open(os.path.join(HERE, 'wall.json')))
cal = wall['calibration']
K = cal['panel_in'] / cal['panel_px']                 # inches per scan pixel
OX, OY = cal['origin_px']
W_IN, H_IN = cal['panels'][0] * cal['panel_in'], cal['panels'][1] * cal['panel_in']
to_in = np.array([[K, 0, -OX * K], [0, K, -OY * K], [0, 0, 1]])   # scan px -> mural inches
r1 = lambda v: round(float(v), 1)


def rect_in(x, y, w, h):
    return dict(x=r1((x - OX) * K), y=r1((y - OY) * K), w=r1(w * K), h=r1(h * K))


def main():
    img = cv2.imread(os.path.join(HERE, wall['image']), cv2.IMREAD_UNCHANGED)
    a = img[:, :, 3:4] / 255.0
    scan = (img[:, :, :3] * a + 64 * (1 - a)).astype(np.uint8)        # unscanned -> neutral grey

    # the no-camera picture: exactly the 576 x 144 in painted area, 8 px per inch
    picture_px = np.linalg.inv(np.diag([8, 8, 1]) @ to_in)[:2]        # picture px -> scan px
    picture = cv2.warpAffine(scan, picture_px, (int(W_IN * 8), int(H_IN * 8)),
                             flags=cv2.WARP_INVERSE_MAP | cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(os.path.join(ROOT, 'images', 'mural-wall.webp'), picture, [cv2.IMWRITE_WEBP_QUALITY, 82])

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    data_path = os.path.join(ROOT, 'data', 'objects.json')
    data = json.load(open(data_path))
    data['mural'].update(width=W_IN, height=H_IN, panelSize=cal['panel_in'], picture='images/mural-wall.webp',
                         pictureNote='The painted wall, straightened from LiDAR scans (tools/wall). Rebuild with tools/wall/build.py.')
    data['landmarks'] = [dict(name=w['name'], **rect_in(*w['box']), note='Measured from the wall scan') for w in wall['windows']]
    data.pop('targets', None)                   # targets now belong to each object (see "ar")
    manifest = {}
    for obj in data['objects']:
        if obj['id'] == 'demo-card':
            # the MindAR sample card, pretending to be painted on the wall: print it or show it on a screen
            box = obj['location']; t = dict(x=box['x'], y=box['y'], w=20, h=36.24)
            obj['ar'] = dict(mind='targets/objects/demo-card.mind', targets=[t])
            cv2.imwrite(os.path.join(OUT, 'demo-card.png'), cv2.imread(os.path.join(ROOT, 'targets', 'source', '00-demo-card.png')))
            manifest['demo-card'] = ['demo-card.png']
            continue
        box = wall['products'].get(obj['id'])
        if not box:
            obj['location'] = None; obj.pop('ar', None)        # not painted (or not found): left out of the game
            continue
        x, y, w, h = box
        obj['location'] = rect_in(x, y, w, h)
        cx, cy = x + w / 2, y + h / 2
        s = round(max(200, min(440, 1.6 * max(w, h))))        # scan px: 0.5 to 1.1 m
        ox, oy = round(cx - s / 2), round(cy - s / 2)
        cs = round(s * K * PPI)
        files = [f"{obj['id']}.png"]
        cv2.imwrite(os.path.join(OUT, files[0]), cv2.resize(crop(scan, ox, oy, s, s), (cs, cs), interpolation=cv2.INTER_AREA))
        targets = [rect_in(ox, oy, s, s)]
        if (OY + H_IN / K - cy) * K > HIGH_IN:
            for name, (inset, squash) in TILTS.items():
                th = round(cs * squash)
                quad = np.float32([[ox - inset * s, oy], [ox + s + inset * s, oy], [ox + s, oy + s], [ox, oy + s]])
                Hpx = cv2.getPerspectiveTransform(np.float32([[0, 0], [cs, 0], [cs, th], [0, th]]), quad)  # image -> scan px
                tilted = cv2.warpPerspective(scan, Hpx, (cs, th), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_AREA,
                                             borderMode=cv2.BORDER_CONSTANT, borderValue=(64, 64, 64))
                f = f"{obj['id']}.{name}.png"; files.append(f)
                cv2.imwrite(os.path.join(OUT, f), tilted)
                H = np.linalg.inv(to_in @ Hpx); H /= H[2, 2]                  # mural inches -> image px
                bx, by = quad[:, 0], quad[:, 1]
                targets.append(dict(rect_in(bx.min(), by.min(), bx.max() - bx.min(), by.max() - by.min()),
                                    px=[cs, th], H=[[round(float(v), 6) for v in row] for row in H]))
        obj['ar'] = dict(mind=f"targets/objects/{obj['id']}.mind", targets=targets)
        manifest[obj['id']] = files
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False); f.write('\n')
    placed = [o for o in data['objects'] if o.get('location')]
    print(f"{len(placed)} objects placed, {sum(len(v) for v in manifest.values())} target images, "
          f"{sum(len(v) > 1 for v in manifest.values())} with tilted copies; not on the wall: "
          + ', '.join(o['id'] for o in data['objects'] if not o.get('location')))


def crop(img, x, y, w, h):
    """Crop that pads with grey where the box runs off the scan."""
    out = np.full((h, w, 3), 64, np.uint8)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, img.shape[1]), min(y + h, img.shape[0])
    out[y0 - y:y1 - y, x0 - x:x1 - x] = img[y0:y1, x0:x1]
    return out


if __name__ == '__main__':
    sys.exit(main())
