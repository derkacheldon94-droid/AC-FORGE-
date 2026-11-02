"""Preview renders (Cycles CPU, studio white)."""

import os

import bpy
from mathutils import Vector

VIEWS = {
    "front_quarter": ((-5.4, 6.2, 2.3), (0, 0.25, 0.72), 40),
    "side": ((-10.5, 0.0, 1.0), (0, -0.15, 0.78), 45),
    "rear_quarter": ((5.0, -6.4, 3.4), (0, -0.7, 0.62), 40),
    "front": ((0.0, 8.5, 1.0), (0, 0, 0.75), 45),
    "detail_engine": ((-1.5, 3.3, 2.2), (0, 1.45, 0.85), 40),
    "detail_bed": ((1.6, -3.6, 2.4), (0, -1.6, 0.85), 38),
    "detail_wheel": ((-2.5, 2.9, 0.55), (-0.86, 1.49, 0.36), 50),
    "detail_interior": ((-1.5, -0.2, 1.35), (0.1, 0.55, 0.95), 28),
    "rear": ((0.0, -8.5, 1.6), (0, 0, 0.75), 45),
}


def setup(samples=64, res=(1600, 1000)):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 0.85
    scene.world = world

    me = bpy.data.meshes.new("PREVIEW_GROUND")
    me.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("PREVIEW_GROUND", me)
    scene.collection.objects.link(g)
    try:
        g.is_shadow_catcher = True
    except Exception:
        pass

    for name, rot, energy in (("Key", (0.65, 0.15, 0.9), 3.2), ("Fill", (1.0, -0.2, -2.3), 1.0)):
        L = bpy.data.lights.new(name, "SUN")
        L.energy = energy
        L.angle = 0.35
        o = bpy.data.objects.new(name, L)
        o.rotation_euler = rot
        scene.collection.objects.link(o)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Standard"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def render(out_dir, views=None, samples=64, res=(1600, 1000)):
    for o in bpy.data.objects:          # speed-blur discs and the low-res cockpit are in-game only
        if o.name.startswith(("RIM_BLUR", "COCKPIT_LR")) or (o.parent and o.parent.name.startswith("COCKPIT_LR")):
            o.hide_render = True
    for o in bpy.data.objects:
        p = o.parent
        while p is not None:
            if p.name == "COCKPIT_LR":
                o.hide_render = True
            p = p.parent
    cam = setup(samples, res)
    scene = bpy.context.scene
    paths = []
    for name in (views or VIEWS.keys()):
        pos, target, lens = VIEWS[name]
        cam.location = pos
        cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        scene.render.filepath = os.path.join(out_dir, f"preview_{name}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(scene.render.filepath)
        print("rendered", scene.render.filepath, flush=True)
    return paths
