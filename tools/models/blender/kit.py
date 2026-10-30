"""Shared helpers for the Blender-built 3D renderings.

Each object is one script, tools/models/blender/<id>.py, that builds the object with these helpers:

    blender -b -P tools/models/blender/<id>.py                 # -> models/incoming/<id>.glb
    blender -b -P tools/models/blender/<id>.py -- --check      # also renders tools/models/blender/check/<id>.png

then `npm run models` compresses models/incoming/ into models/.

Conventions (the app relies on these):
- Blender is Z up. Model the object standing on z=0, centred on x/y, with its FRONT facing -Y
  (what Blender's Front view shows). The glTF exporter turns that into Y up, front +Z.
- Units don't matter (the app fits every model), but model at real size in metres so bevel widths are sane.
- Budget: under 50,000 triangles and 1.5 MB compressed. Bevel segments of 2-3 are plenty.
- Materials are plain PBR (base colour, roughness, metallic). Procedural textures don't export;
  small image textures (<= 1024 px) made with PIL do.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))

# The mural's palette (sRGB hex). Use the object's real colours, pulled toward these.
PALETTE = {
    'walnut': '#5a3a22', 'oak': '#9a6a3c', 'honey': '#c8893d', 'amber': '#e8a33a', 'lamp': '#f6c25a',
    'cream': '#efe3c8', 'paper': '#f4ecd8', 'sky': '#8fc3dc', 'teal': '#2f7d86', 'red': '#b8322a',
    'cardinal': '#99201c', 'orange': '#d9662a', 'brass': '#b8893a', 'copper': '#b0663c',
    'chrome': '#c9ccd1', 'steel': '#8a9099', 'gunmetal': '#3c4047', 'black': '#1e1d1c',
    'rubber': '#262422', 'white': '#f2efe8', 'glass': '#bcd9e6',
}


def hex_rgb(c):
    if isinstance(c, str):
        c = PALETTE.get(c, c).lstrip('#')
        c = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (lin(c[0]), lin(c[1]), lin(c[2]), 1.0)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()


_MATS = {}


def mat(color, rough=0.5, metal=0.0, name=None, alpha=1.0, emit=0.0, image=None):
    """A Principled material. color: palette name, hex, or (r,g,b) in 0..1 sRGB. image: path to a texture."""
    key = (str(color), rough, metal, alpha, emit, image)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name or f'm{len(_MATS)}')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = hex_rgb(color)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = hex_rgb(color)
        b.inputs['Emission Strength'].default_value = emit
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        m.surface_render_method = 'BLENDED'
    if image:
        t = m.node_tree.nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(image)
        m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    _MATS[key] = m
    return m


def finish(obj, material=None, bevel=0.0, segments=2, smooth=30, subsurf=0):
    """Assign material, add bevel / subdivision, and shade smooth by angle. Returns obj."""
    if material is not None:
        obj.data.materials.clear()
        obj.data.materials.append(material)
    if bevel:
        md = obj.modifiers.new('bevel', 'BEVEL')
        md.width = bevel; md.segments = segments; md.limit_method = 'ANGLE'
        md.harden_normals = False
    if subsurf:
        md = obj.modifiers.new('subsurf', 'SUBSURF'); md.levels = subsurf; md.render_levels = subsurf
    if smooth and obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True
        try:
            sm = obj.modifiers.new('smooth', 'NODES')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_remove(modifier='smooth')
            bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth))
        except Exception:
            pass
    return obj


def _place(obj, at, rot, scale):
    obj.location = at
    if rot:
        obj.rotation_euler = [math.radians(a) for a in rot]
    if scale:
        obj.scale = scale
    return obj


def box(size, at=(0, 0, 0), rot=None, material=None, bevel=0.0, segments=2, name='box'):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    _place(o, at, rot, None)
    return finish(o, material, bevel, segments)


def cyl(r, h, at=(0, 0, 0), rot=None, material=None, bevel=0.0, segments=2, verts=48, r2=None, name='cyl'):
    """Cylinder (or cone if r2 given) along Z, centred at `at`."""
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=h, vertices=verts)
    o = bpy.context.object; o.name = name
    _place(o, at, rot, None)
    return finish(o, material, bevel, segments)


def sphere(r, at=(0, 0, 0), scale=None, material=None, segs=48, rings=24, name='sphere'):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=rings)
    o = bpy.context.object; o.name = name
    if scale:
        o.scale = scale; bpy.ops.object.transform_apply(scale=True)
    _place(o, at, None, None)
    return finish(o, material)


def torus(R, r, at=(0, 0, 0), rot=None, material=None, major=64, minor=16, name='torus'):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=major, minor_segments=minor)
    o = bpy.context.object; o.name = name
    _place(o, at, rot, None)
    return finish(o, material)


def lathe(profile, at=(0, 0, 0), rot=None, material=None, steps=64, name='lathe', bevel=0.0):
    """Revolve a 2D profile [(radius, z), ...] around Z. Close the profile on the axis for solids."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((r, 0, z)) for r, z in profile]
    for a, b in zip(vs, vs[1:]):
        bm.edges.new((a, b))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=math.tau, steps=steps, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    _place(o, at, rot, None)
    return finish(o, material, bevel)


def extrude(poly, depth, at=(0, 0, 0), rot=None, material=None, bevel=0.0, segments=2, name='extrude'):
    """Extrude a 2D polygon [(x, y), ...] (counter-clockwise) by depth along +Z from z=0."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0)) for x, y in poly]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    top = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, depth))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    _place(o, at, rot, None)
    return finish(o, material, bevel, segments)


def tube(points, r, material=None, closed=False, bevel_res=12, name='tube'):
    """A round tube along a smooth path through 3D points (cables, handles, frames)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY' if len(points) < 3 else 'NURBS')
    sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (*c, 1)
    if sp.type == 'NURBS':
        sp.use_endpoint_u = not closed; sp.order_u = min(4, len(points))
    sp.use_cyclic_u = closed
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.resolution_u = bevel_res; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')  # convert() acts on every selected object
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    return finish(o, material)


def boolean(target, cutter, op='DIFFERENCE'):
    """Cut `cutter` out of `target` (or UNION / INTERSECT), then delete the cutter."""
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    # move the boolean ahead of bevel/subsurf so they apply to the cut shape
    while target.modifiers.find('bool') > 0:
        bpy.ops.object.modifier_move_up(modifier='bool')
    bpy.ops.object.modifier_apply(modifier='bool')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def text(s, size, depth, at=(0, 0, 0), rot=(90, 0, 0), material=None, align='CENTER', name='text'):
    """Raised lettering. Default rot stands it up facing -Y (the front)."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = depth / 2
    cu.align_x = align; cu.align_y = 'CENTER'
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    _place(o, at, rot, None)
    bpy.ops.object.select_all(action='DESELECT')  # convert() acts on every selected object
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.object
    if material is not None:
        o.data.materials.clear(); o.data.materials.append(material)
    return o


def mirror_x(obj):
    md = obj.modifiers.new('mirror', 'MIRROR'); md.use_axis[0] = True
    return obj


def array(obj, count, offset):
    md = obj.modifiers.new('array', 'ARRAY'); md.count = count
    md.use_relative_offset = False; md.use_constant_offset = True; md.constant_offset_displace = offset
    return obj


def triangles():
    dg = bpy.context.evaluated_depsgraph_get(); n = 0
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            m = o.evaluated_get(dg).to_mesh(); m.calc_loop_triangles(); n += len(m.loop_triangles)
            o.evaluated_get(dg).to_mesh_clear()
    return n


def export(obj_id):
    """Write models/incoming/<id>.glb and, with `-- --check`, a 4-view check render."""
    out = os.path.join(ROOT, 'models', 'incoming'); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f'{obj_id}.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_apply=True, export_yup=True,
                              use_selection=False, export_lights=False, export_cameras=False)
    tris = triangles()
    print(f'EXPORTED {path} tris={tris} size={os.path.getsize(path) // 1024}KB')
    if tris > 50000:
        print('WARNING: over the 50,000 triangle budget')
    if '--check' in sys.argv:
        check_render(obj_id)
    return path


def check_render(obj_id, res=520):
    """Render front-3/4, back-3/4, side and top-ish views into one PNG under tools/models/blender/check/."""
    sc = bpy.context.scene
    objs = [o for o in sc.objects if o.type == 'MESH']
    lo = Vector((min(min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in objs) for i in range(3)))
    hi = Vector((max(max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) for o in objs) for i in range(3)))
    ctr = (lo + hi) / 2; rad = (hi - lo).length / 2
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'  # closer to how three.js shows colours than Blender's AgX
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = hex_rgb('#efe6d4')
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    def light(name, loc, energy, color):
        L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = rad * 3; L.color = hex_rgb(color)[:3]
        o = bpy.data.objects.new(name, L); sc.collection.objects.link(o)
        o.location = ctr + Vector(loc) * rad * 4
        o.rotation_euler = (ctr - o.location).to_track_quat('-Z', 'Y').to_euler()
    light('key', (-0.6, -1, 0.9), 520 * rad * rad, '#ffd9a0')
    light('fill', (1, -0.4, 0.3), 180 * rad * rad, '#dfe8ff')
    light('rim', (0.3, 1, 0.8), 300 * rad * rad, '#ffffff')
    cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 70
    cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
    views = [(-35, 22), (145, 22), (90, 8), (-20, 60)]
    tiles = []
    tmp = os.path.join(HERE, 'check'); os.makedirs(tmp, exist_ok=True)
    for i, (az, el) in enumerate(views):
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = ctr + d * rad * 4.2
        cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        f = os.path.join(tmp, f'_{obj_id}_{i}.png'); sc.render.filepath = f
        bpy.ops.render.render(write_still=True); tiles.append(f)
    import subprocess
    out = os.path.join(tmp, f'{obj_id}.png')
    script = ("import sys;from PIL import Image;r=int(sys.argv[1]);o=sys.argv[2];fs=sys.argv[3:];"
              "s=Image.new('RGB',(r*2,r*2));[s.paste(Image.open(f).convert('RGB'),((i%2)*r,(i//2)*r)) for i,f in enumerate(fs)];s.save(o)")
    subprocess.run(['/usr/bin/env', 'python3', '-c', script, str(res), out, *tiles], check=True)
    for f in tiles:
        os.remove(f)
    print(f'CHECK {os.path.join(tmp, obj_id + ".png")}')
