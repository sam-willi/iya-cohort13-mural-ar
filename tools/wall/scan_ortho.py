import bpy, sys, math, json, numpy as np
from mathutils import Vector, Matrix
args = sys.argv[sys.argv.index('--') + 1:]
path, out, mm_per_px = args[0], args[1], float(args[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=path)
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
mw = ob.matrix_world
P = np.array([tuple(mw @ v.co) for v in ob.data.vertices])
c = P.mean(0)
_, _, Vt = np.linalg.svd(P - c, full_matrices=False)
up = np.array([0, 0, 1.0])
h = Vt[0] - Vt[0] @ up * up; h /= np.linalg.norm(h)
n = np.cross(h, up); n /= np.linalg.norm(n)
# face normals: put the camera on the side the painted surface faces
nm = mw.to_3x3()
acc = np.zeros(3)
for p in ob.data.polygons:
    fn = np.array(tuple(nm @ p.normal)); 
    if abs(fn @ n) > 0.7: acc += fn * p.area
if acc @ n < 0: n = -n; h = -h          # keep h pointing to the viewer's right
d = (P - c) @ n
hist, edges = np.histogram(d, bins=400); k = hist.argmax(); off = (edges[k] + edges[k + 1]) / 2
near = np.abs(d - off) < 0.25
x = (P - c) @ h; z = P[:, 2]
x0, x1 = np.percentile(x[near], 0.2), np.percentile(x[near], 99.8)
z0, z1 = np.percentile(z[near], 0.2), np.percentile(z[near], 99.8)
W, H = x1 - x0, z1 - z0
center = c + n * off + h * (x0 + x1) / 2
center[2] = (z0 + z1) / 2
sc = bpy.context.scene
cam_d = bpy.data.cameras.new('ortho'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = max(W, H)
cam_d.clip_start = 5 - 0.4; cam_d.clip_end = 5 + 0.4
cam = bpy.data.objects.new('ortho', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.location = Vector(center + n * 5)
R = Matrix((tuple(h), tuple(up), tuple(n))).transposed()   # camera x=h, y=up, looks along -n
cam.rotation_euler = R.to_euler()
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'TEXTURE'
sc.view_settings.view_transform = 'Standard'
sc.render.film_transparent = True
sc.render.resolution_x = int(round(W * 1000 / mm_per_px)); sc.render.resolution_y = int(round(H * 1000 / mm_per_px))
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
info = dict(width_m=round(W, 3), height_m=round(H, 3), px=[sc.render.resolution_x, sc.render.resolution_y], mm_per_px=mm_per_px,
            wall_offset_m=round(float(off), 3), near_fraction=round(float(near.mean()), 3), tilt_deg=round(math.degrees(math.asin(abs(Vt[0][2]))), 2))
json.dump(info, open(out.rsplit('.', 1)[0] + '.json', 'w')); print('ORTHO', info)
