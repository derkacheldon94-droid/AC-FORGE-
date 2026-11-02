"""Low-res cockpit, LOD generation, mesh-limit checks and FBX/GLB/.blend export."""

import os

import bmesh
import bpy

from . import geo as G
from . import kn5

KN5_VERT_LIMIT = 65000          # a kn5 mesh holds at most 65,535 vertices (16-bit indices): a hard format limit
VERTEX_BUDGET = 200_000         # total in-game vertices for the full-detail model (LOD A, incl. COCKPIT_LR)
PROTECTED = ("LIGHT_", "GLASS", "BODY_SHELL", "BODY_CAB_TOP", "BODY_HOOD", "BODY_FLARES", "WIDEBODY_", "WHEEL_", "STEER_",
             "DISC_", "RIM_BLUR")

# objects whose name starts with one of these are dropped at each LOD level
DROP = {
    "B": ("BOLTS_", "DETAIL_", "INT_GAUGE", "INT_HARNESS_HW", "COCKPIT_LR_", "ENGINE_SMALL", "TURBO_SMALL",
          "BED_SMALL"),
    "C": ("BOLTS_", "DETAIL_", "INT_", "ENGINE_SMALL", "ENGINE_WIRES", "TURBO_SMALL", "BED_SMALL", "CHASSIS_",
          "BODY_SEALS", "SUSP_", "STEER_", "LAMP_INNER", "BADGE_", "COCKPIT_LR_"),
    "D": ("BOLTS_", "DETAIL_", "INT_", "ENGINE_", "TURBO_", "BED_", "CHASSIS_", "BODY_SEALS", "SUSP_", "STEER_",
          "LAMP_", "BADGE_", "COCKPIT_LR_", "EXHAUST_", "FRONT_INTERCOOLER", "FRONT_TOW", "MIRROR_GLASS",
          "BODY_WHEELHOUSES"),
}
RATIO = {"B": 0.40, "C": 0.15, "D": 0.05}
KEEP_EXACT = ("LIGHT_",)   # emissive meshes referenced by lights.ini: never decimated away


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("PREVIEW")]


def stats(label):
    tris = 0
    for o in meshes():
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"[{label}] {len(meshes())} meshes, {tris:,} triangles", flush=True)
    return tris


def split_big(o):
    """Split meshes above the kn5 vertex limit into chunks of loose parts."""
    if len(o.data.vertices) <= KN5_VERT_LIMIT:
        return [o]
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            isl.append(cur.index)
            for e in cur.link_edges:
                w = e.other_vert(cur)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        islands.append(isl)
    bm.free()
    chunks, cur, cnt = [], [], 0
    for isl in islands:
        if cnt + len(isl) > KN5_VERT_LIMIT and cur:
            chunks.append(cur)
            cur, cnt = [], 0
        cur.extend(isl)
        cnt += len(isl)
    chunks.append(cur)
    out = []
    for i, idx in enumerate(chunks):
        keep = set(idx)
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
        me = bpy.data.meshes.new(f"{o.name}_{i}")
        bm.to_mesh(me)
        bm.free()
        for m in o.data.materials:
            me.materials.append(m)
        n = bpy.data.objects.new(f"{o.name}_{i}", me)
        for c in o.users_collection:
            c.objects.link(n)
        n.parent = o.parent
        n.matrix_world = o.matrix_world.copy()
        out.append(n)
    bpy.data.objects.remove(o)
    print(f"  split {out[0].name[:-2]} into {len(out)} meshes (kn5 vertex limit)")
    return out


def decimate(o, ratio):
    if len(o.data.polygons) < 300 or o.name.startswith(KEEP_EXACT):
        return
    mod = o.modifiers.new("dec", "DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    G.apply_modifiers(o)


def game_vertices():
    """In-game vertex count per mesh object: unique (position, normal, uv), exactly what the kn5 stores."""
    return {o.name: kn5.count_vertices(o) for o in meshes()}


def enforce_budget(budget=VERTEX_BUDGET, max_rounds=6):
    """Bring the whole model under `budget` in-game vertices.
    Silhouette-critical parts (body panels, flares, tyres, glass, lights) are never touched; everything
    else (fasteners, small engine/turbo parts, interior, text) is collapse-decimated by the same ratio."""
    for rnd in range(max_rounds):
        counts = game_vertices()
        total = sum(counts.values())
        print(f"[budget] round {rnd}: {total:,} in-game vertices (limit {budget:,})", flush=True)
        if total <= budget:
            return total
        fixed = sum(v for n, v in counts.items() if n.startswith(PROTECTED))
        flex = total - fixed
        if flex <= 0:
            break
        ratio = max(0.2, min(0.97, (budget * 0.985 - fixed) / flex))
        for o in meshes():
            if o.name.startswith(PROTECTED) or counts[o.name] < 120:
                continue
            mod = o.modifiers.new("budget", "DECIMATE")
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            G.apply_modifiers(o)
            G.smooth_by_angle(o, 40)
    total = sum(game_vertices().values())
    print(f"[budget] final: {total:,} in-game vertices", flush=True)
    return total


def make_cockpit_lr(col):
    """COCKPIT_LR: decimated copy of the interior, shown when the camera is outside the car."""
    hr = bpy.data.objects.get("COCKPIT_HR")
    if hr is None:
        return
    lr = bpy.data.objects.new("COCKPIT_LR", None)
    col.objects.link(lr)
    lr.location = hr.location

    def copy_tree(src, parent):
        dst = src.copy()
        if src.type == "MESH":
            dst.data = src.data.copy()
        dst.name = src.name.replace("_HR", "_LR") if src.name.endswith("_HR") else "COCKPIT_LR_" + src.name
        col.objects.link(dst)
        dst.parent = parent
        dst.matrix_parent_inverse = src.matrix_parent_inverse.copy()
        if dst.type == "MESH":
            decimate(dst, 0.15)
        for ch in src.children:
            copy_tree(ch, dst)
    for ch in hr.children:
        copy_tree(ch, lr)


def export_fbx(path):
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=False, object_types={"MESH", "EMPTY"},
        axis_forward="Z", axis_up="Y", apply_unit_scale=True, use_mesh_modifiers=True,
        mesh_smooth_type="OFF", use_tspace=False, path_mode="RELATIVE", embed_textures=False, bake_anim=False)
    print("wrote", path, flush=True)


def finish(out_dir, car_id, lods=True, car_dir=None):
    col = bpy.context.scene.collection
    for o in list(meshes()):
        split_big(o)
    make_cockpit_lr(col)
    enforce_budget()
    stats("LOD A")
    blend = os.path.join(out_dir, car_id + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    export_fbx(os.path.join(out_dir, car_id + ".fbx"))
    try:
        bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, car_id + ".glb"), export_format="GLB")
    except Exception as exc:
        print("GLB export skipped:", exc)
    if car_dir:
        os.makedirs(car_dir, exist_ok=True)
        print("kn5 LOD A:", kn5.export(os.path.join(car_dir, car_id + ".kn5"), car_id), flush=True)
    if not lods:
        return
    for lod in ("B", "C", "D"):
        for o in list(meshes()):
            if o.name.startswith(DROP[lod]) and not o.name.startswith(KEEP_EXACT):
                bpy.data.objects.remove(o)
        for e in [o for o in bpy.data.objects if o.type == "EMPTY" and o.name.startswith(("COCKPIT_LR",))]:
            if lod in ("C", "D") and not e.children:
                bpy.data.objects.remove(e)
        for o in meshes():
            decimate(o, RATIO[lod] if lod == "B" else RATIO[lod] / RATIO["B" if lod == "C" else "C"])
        stats(f"LOD {lod}")
        export_fbx(os.path.join(out_dir, f"{car_id}_{lod}.fbx"))
        if car_dir:
            print(f"kn5 LOD {lod}:", kn5.export(os.path.join(car_dir, f"{car_id}_{lod}.kn5"), car_id), flush=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
