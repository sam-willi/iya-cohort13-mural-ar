"""Software renderer for checking .glb models: isometric-ish view, lambert shading."""
import sys, numpy as np, trimesh
from PIL import Image, ImageDraw

def render(path, W=360, az=-35, el=25):
    sc = trimesh.load(path, force='scene')
    tris, cols = [], []
    for name, g in sc.graph.nodes_geometry and [(n, sc.graph[n]) for n in sc.graph.nodes_geometry]:
        T, gname = g
        m = sc.geometry[gname].copy(); m.apply_transform(T)
        c = np.array([200, 200, 200, 255], float)
        try:
            f = m.visual.material.baseColorFactor
            if f is not None:
                f = np.array(f, float).ravel()
                c[:len(f)] = f * (255 if f.max() <= 1.0 else 1)
        except Exception: pass
        tris.append(m.vertices[m.faces]); cols.append(np.repeat(c[None], len(m.faces), 0))
    tris = np.vstack(tris); cols = np.vstack(cols)
    a, e = np.radians(az), np.radians(el)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    V = tris @ (Rx @ Ry).T
    n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]); nl = np.linalg.norm(n, axis=1) + 1e-12; n /= nl[:, None]
    L = np.array([0.4, 0.7, 0.6]); L /= np.linalg.norm(L)
    shade = 0.35 + 0.65 * np.abs(n @ L)
    xy = V[:, :, :2]; lo = xy.reshape(-1, 2).min(0); hi = xy.reshape(-1, 2).max(0)
    s = (W * 0.9) / (hi - lo).max(); off = (W - (hi - lo) * s) / 2
    P = (xy - lo) * s + off; P[:, :, 1] = W - P[:, :, 1]
    depth = V[:, :, 2].mean(1)
    order = np.argsort(depth)  # painter's: far (small z) first; camera looks down -z? ensure
    img = Image.new('RGB', (W, W), (250, 248, 242)); d = ImageDraw.Draw(img)
    for i in order:
        c = cols[i][:3] * shade[i]
        d.polygon([tuple(p) for p in P[i]], fill=tuple(int(x) for x in np.clip(c, 0, 255)))
    return img

if __name__ == '__main__':
    out = sys.argv[-1]; ims = []
    for p in sys.argv[1:-1]:
        im = render(p); ImageDraw.Draw(im).text((6, 6), p.split('/')[-1][:44], fill=(200, 0, 0)); ims.append(im)
    cols_ = 4; rows = (len(ims) + cols_ - 1) // cols_
    sheet = Image.new('RGB', (360 * cols_, 360 * rows), 'white')
    for i, im in enumerate(ims): sheet.paste(im, ((i % cols_) * 360, (i // cols_) * 360))
    sheet.save(out)
