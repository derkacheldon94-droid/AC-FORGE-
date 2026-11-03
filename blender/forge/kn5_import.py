"""Import a .kn5 into the current Blender scene (inverse of forge.kn5's export conversion).

AC (left-handed, Y up, front +Z, left -X)  ->  Blender (right-handed, Z up, front +Y, left -X):
    Blender (x, y, z) = AC (x, z, y), triangle winding reversed back, V flipped back.
Mesh chunks of the same node are merged into one object; dummies become empties.
Embedded textures are written next to `tex_dir` and wired into simple materials.
"""

import os

import numpy as np

import bpy
from mathutils import Matrix

from . import kn5

_P = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def _to_blender_matrix(m16):
    row = Matrix([m16[0:4], m16[4:8], m16[8:12], m16[12:16]])
    return _P @ row.transposed() @ _P


def _materials(k, tex_dir):
    os.makedirs(tex_dir, exist_ok=True)
    paths = {}
    for name, data in k["textures"]:
        p = os.path.join(tex_dir, name)
        with open(p, "wb") as f:
            f.write(data)
        paths[name] = p
    out = []
    for m in k["materials"]:
        mat = bpy.data.materials.new(m["name"])
        try:
            mat.use_nodes = True
        except Exception:
            pass
        tex = next((t for slot, _, t in m["maps"] if slot == "txDiffuse"), None)
        if tex and tex in paths:
            nt = mat.node_tree
            bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            node = nt.nodes.new("ShaderNodeTexImage")
            node.image = bpy.data.images.load(paths[tex])
            nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        out.append(mat)
    return out


def _mesh(name, chunks, mats, col):
    pos, nor, uv, faces, mat_idx = [], [], [], [], []
    base = 0
    for n in chunks:
        v = n["vertices"]
        p = v[:, [0, 2, 1]]
        pos.append(p)
        nor.append(v[:, [3, 5, 4]])
        uv.append(np.stack([v[:, 6], 1.0 - v[:, 7]], axis=1))
        idx = n["indices"].astype(np.int64).reshape(-1, 3)[:, [0, 2, 1]] + base
        faces.append(idx)
        mat_idx.append(np.full(len(idx), n["material"], np.int32))
        base += len(v)
    P, N, U, F, MI = (np.concatenate(a) for a in (pos, nor, uv, faces, mat_idx))
    me = bpy.data.meshes.new(name)
    me.from_pydata(P.tolist(), [], F.tolist())
    used = sorted(set(MI.tolist()))
    for i in used:
        me.materials.append(mats[i])
    remap = {m: j for j, m in enumerate(used)}
    me.polygons.foreach_set("material_index", np.array([remap[m] for m in MI], np.int32))
    lu = me.uv_layers.new(name="UVMap")
    corner_v = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", corner_v)
    lu.data.foreach_set("uv", U[corner_v].ravel())
    me.shade_smooth()
    me.normals_split_custom_set_from_vertices(N.tolist())
    me.update()
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def import_kn5(path, tex_dir, col=None):
    """Returns {node name: object} for the imported scene."""
    col = col or bpy.context.scene.collection
    k = kn5.read(path)
    mats = _materials(k, tex_dir)
    made = {}

    def walk(node, parent):
        if node["cls"] != 1:
            return
        meshes = [c for c in node["children"] if c["cls"] == 2]
        dummies = [c for c in node["children"] if c["cls"] == 1]
        if meshes:
            # group mesh chunks by material so each Blender object keeps a single material
            by_mat = {}
            for m in meshes:
                by_mat.setdefault(m["material"], []).append(m)
            if len(by_mat) == 1:
                o = _mesh(node["name"], meshes, mats, col)
                o.matrix_basis = _to_blender_matrix(node["matrix"])
                o.parent = parent
                made[node["name"]] = o
                holder = o
            else:
                holder = bpy.data.objects.new(node["name"], None)
                col.objects.link(holder)
                holder.matrix_basis = _to_blender_matrix(node["matrix"])
                holder.parent = parent
                made[node["name"]] = holder
                for mi, group in by_mat.items():
                    o = _mesh(f"{node['name']}_{mats[mi].name.upper()}", group, mats, col)
                    o.parent = holder
                    made[o.name] = o
        else:
            holder = bpy.data.objects.new(node["name"], None)
            col.objects.link(holder)
            holder.matrix_basis = _to_blender_matrix(node["matrix"])
            holder.parent = parent
            made[node["name"]] = holder
        for d in dummies:
            walk(d, holder)

    for top in k["root"]["children"]:
        walk(top, None)
    return made
