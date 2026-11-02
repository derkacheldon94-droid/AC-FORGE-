"""Direct Assetto Corsa .kn5 exporter (no ksEditor, no FBX round trip).

Coordinate conversion: Blender is right-handed Z-up with the truck facing +Y and its left side at -X.
Assetto Corsa is left-handed Y-up with cars facing +Z and the left side at -X. So
    AC (x, y, z) = Blender (x, z, y)
which is a reflection: left/right and front/back are preserved, triangle winding is reversed (D3D treats
clockwise as front), and the V texture coordinate is flipped.

File layout (version 6):
    "sc6969" int32 version, int32 extra
    textures:  int32 n, each {int32 active, str name, int32 size, bytes}
    materials: int32 n, each {str name, str shader, u8 blend, u8 alpha_test, int32 depth_mode,
                              int32 nprops, each {str name, 10 x float32 (a, vec2, vec3, vec4)},
                              int32 nmaps,  each {str slot_name, int32 slot, str texture}}
    nodes (recursive): int32 class (1 dummy, 2 mesh), str name, int32 child_count, u8 active,
        dummy: 16 x float32 row-major matrix (translation in the last row)
        mesh:  u8 cast_shadows, u8 visible, u8 transparent, int32 nverts,
               nverts x (pos3, normal3, uv2, tangent3) float32, int32 nindices, nindices x uint16,
               int32 material, int32 layer, float32 lod_in, float32 lod_out,
               float32 sphere x/y/z/radius, u8 renderable
    strings are int32 length + UTF-8 bytes.
"""

import os
import struct

import numpy as np

import bpy
from mathutils import Matrix

MAGIC = b"sc6969"
VERSION = 6
MAX_MESH_VERTS = 65535          # kn5 meshes use 16-bit indices: a hard format limit
SAFE_MESH_VERTS = 65000

_P = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))

# ---------------------------------------------------------------- material table
# (ksAmbient, ksDiffuse, ksSpecular, ksSpecularEXP)
SHADING = {
    "Paint_Black": (0.50, 0.55, 0.85, 220), "Gloss_Black": (0.45, 0.50, 0.90, 260), "Trim_Black": (0.45, 0.50, 0.25, 40),
    "Carbon": (0.50, 0.60, 0.75, 130), "Grille_Mesh": (0.45, 0.60, 0.50, 80), "Bed_Liner": (0.45, 0.60, 0.08, 6),
    "Rubber": (0.40, 0.55, 0.05, 8), "Chrome": (0.55, 0.80, 1.00, 300), "Metal_Polished": (0.55, 0.80, 1.00, 240),
    "Brushed_Alu": (0.55, 0.75, 0.70, 70), "Cast_Alu": (0.55, 0.75, 0.50, 45), "Engine_Dark": (0.45, 0.60, 0.45, 40),
    "Valve_Red": (0.50, 0.70, 0.60, 90), "Intercooler_Fins": (0.50, 0.70, 0.55, 60), "Heat_Wrap": (0.50, 0.70, 0.08, 6),
    "Braided": (0.50, 0.70, 0.45, 40), "Turbo_Hot": (0.50, 0.70, 0.60, 70), "Silicone_Red": (0.50, 0.70, 0.35, 40),
    "Thread_Alu": (0.55, 0.75, 0.60, 60), "Anodized_Black": (0.45, 0.60, 0.60, 90), "Anodized_Blue": (0.50, 0.70, 0.60, 90),
    "Rim_Red": (0.55, 0.70, 0.70, 120), "Rim_Lip": (0.60, 0.85, 1.00, 250), "Rim_Blur": (0.55, 0.70, 0.40, 60),
    "Tyre_Front": (0.40, 0.55, 0.05, 6), "Tyre_Rear": (0.40, 0.55, 0.05, 6), "Brake_Disc": (0.55, 0.75, 0.50, 60),
    "Caliper_Red": (0.55, 0.75, 0.55, 90), "Decal_White": (0.50, 0.70, 0.30, 30), "Spring_Red": (0.50, 0.70, 0.45, 70),
    "Seat_Red": (0.50, 0.70, 0.08, 6), "Interior_Black": (0.45, 0.60, 0.10, 12), "Carpet": (0.40, 0.55, 0.0, 1),
    "Strap_Red": (0.50, 0.70, 0.12, 10), "Gauge_Tach": (0.55, 0.70, 0.45, 80), "Gauge_Speed": (0.55, 0.70, 0.45, 80),
    "Gauge_Boost": (0.55, 0.70, 0.45, 80), "Plate": (0.55, 0.75, 0.30, 40), "Mirror_Glass": (0.60, 0.80, 1.00, 300),
    "Reflector": (0.60, 0.80, 1.00, 200), "Filter_Red": (0.50, 0.70, 0.08, 6), "Heat_Gold": (0.55, 0.75, 0.80, 120),
    "Light_Head": (0.60, 0.80, 0.30, 30), "Light_Tail": (0.50, 0.70, 0.40, 40), "Light_Marker": (0.50, 0.70, 0.40, 40),
}
# alpha-blended glass-like materials: (ksAmbient, ksDiffuse, ksSpecular, ksSpecularEXP)
ALPHA = {"Glass": (0.40, 0.50, 1.00, 320), "Lens_Clear": (0.50, 0.60, 0.90, 220), "Lens_Red": (0.50, 0.60, 0.80, 160),
         "Lens_Amber": (0.50, 0.60, 0.80, 160), "Rim_Blur": (0.55, 0.70, 0.40, 60)}
NO_SHADOW = ("DECAL", "BADGE", "GLASS", "LAMP", "LIGHT", "INT_GAUGE", "BOLTS_", "BODY_SEALS", "RIM_BLUR",
             "MIRROR_GLASS", "BODY_FLARE_SEAL")


# ---------------------------------------------------------------- low-level writer
class _W:
    def __init__(self):
        self.parts = []

    def raw(self, b):
        self.parts.append(bytes(b))

    def pack(self, fmt, *v):
        self.parts.append(struct.pack("<" + fmt, *v))

    def i32(self, v):
        self.pack("i", v)

    def u8(self, v):
        self.pack("B", v)

    def s(self, v):
        b = v.encode("utf-8")
        self.i32(len(b))
        self.raw(b)

    def data(self):
        return b"".join(self.parts)


def to_ac_matrix(m):
    """Blender (column-vector, Z-up) matrix -> 16 floats row-major for AC (row-vector, Y-up)."""
    a = _P @ m @ _P
    return [a[c][r] for r in range(4) for c in range(4)]       # transpose, flattened row by row


# ---------------------------------------------------------------- mesh conversion
def _unit(v):
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n[n < 1e-12] = 1.0
    return v / n


def mesh_chunks(o):
    """Convert an evaluated Blender mesh object to game-ready chunks.
    Returns [(vertex_bytes, indices(list[int]), vertex_count, sphere)] with every chunk <= SAFE_MESH_VERTS."""
    me = o.data
    me.calc_loop_triangles()
    nl, nv, nt = len(me.loops), len(me.vertices), len(me.loop_triangles)
    if nt == 0:
        return []
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lv = np.empty(nl, np.int32)
    me.loops.foreach_get("vertex_index", lv)
    nrm = np.empty(nl * 3, np.float32)
    try:
        me.corner_normals.foreach_get("vector", nrm)
    except AttributeError:
        me.calc_normals_split()
        me.loops.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    uv = np.zeros(nl * 2, np.float32)
    if me.uv_layers.active is not None:
        layer = me.uv_layers.active
        try:
            layer.uv.foreach_get("vector", uv)
        except (AttributeError, RuntimeError):
            layer.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tri = np.empty(nt * 3, np.int32)
    me.loop_triangles.foreach_get("loops", tri)
    tri = tri.reshape(-1, 3)

    key = np.ascontiguousarray(np.concatenate([co[lv], nrm, uv], axis=1).astype(np.float32))
    void = key.view(np.dtype((np.void, key.dtype.itemsize * key.shape[1]))).ravel()
    _, first, inv = np.unique(void, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    u = key[first]
    # Blender -> AC space
    pos = u[:, [0, 2, 1]]
    nor = _unit(u[:, [3, 5, 4]])
    tex = np.stack([u[:, 6], 1.0 - u[:, 7]], axis=1)
    idx = inv[tri][:, [0, 2, 1]]                                # reversed winding
    bad = np.linalg.norm(u[:, [3, 5, 4]], axis=1) < 0.5          # degenerate normals (e.g. after decimation)
    if bad.any():
        a, b, c = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
        fn = np.cross(b - a, c - a)
        acc = np.zeros_like(pos)
        for k in range(3):
            np.add.at(acc, idx[:, k], fn)
        acc = _unit(acc)
        acc[np.linalg.norm(acc, axis=1) < 0.5] = np.array([0.0, 1.0, 0.0], np.float32)
        nor[bad] = acc[bad]

    chunks = []
    for part in _split_triangles(idx, len(u)):
        used, local = np.unique(part, return_inverse=True)
        p, n, t = pos[used], nor[used], tex[used]
        tg = _tangents(p, n, t, local.reshape(-1, 3))
        vb = np.concatenate([p, n, t, tg], axis=1).astype(np.float32)
        c = p.mean(axis=0)
        r = float(np.max(np.linalg.norm(p - c, axis=1))) if len(p) else 0.0
        chunks.append((vb.tobytes(), local.reshape(-1).astype(np.uint16).tolist(), len(p), (float(c[0]), float(c[1]), float(c[2]), r)))
    return chunks


def _split_triangles(idx, nverts):
    if nverts <= SAFE_MESH_VERTS:
        return [idx]
    k = int(np.ceil(nverts / (SAFE_MESH_VERTS * 0.8)))
    while True:
        parts = np.array_split(idx, k)
        if all(len(np.unique(p)) <= SAFE_MESH_VERTS for p in parts):
            return parts
        k += 1


def _tangents(p, n, t, tris):
    acc = np.zeros_like(p)
    p0, p1, p2 = p[tris[:, 0]], p[tris[:, 1]], p[tris[:, 2]]
    t0, t1, t2 = t[tris[:, 0]], t[tris[:, 1]], t[tris[:, 2]]
    e1, e2 = p1 - p0, p2 - p0
    d1, d2 = t1 - t0, t2 - t0
    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    ok = np.abs(det) > 1e-12
    r = np.zeros_like(det)
    r[ok] = 1.0 / det[ok]
    tan = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) * r[:, None]
    for c in range(3):
        np.add.at(acc, tris[:, c], tan)
    acc = acc - n * np.sum(acc * n, axis=1, keepdims=True)
    ln = np.linalg.norm(acc, axis=1)
    bad = ln < 1e-9
    if bad.any():
        alt = np.cross(n[bad], np.array([0.0, 1.0, 0.0], np.float32))
        alt[np.linalg.norm(alt, axis=1) < 1e-6] = np.array([1.0, 0.0, 0.0])
        acc[bad] = alt
    return _unit(acc)


def count_vertices(o):
    return sum(c[2] for c in mesh_chunks(o))


# ---------------------------------------------------------------- materials / textures
def _image_for(mat):
    if mat is None or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image is not None:
            return n.image
    return None


class _Scene:
    def __init__(self, skin_dir=None):
        self.materials, self.mat_index = [], {}
        self.textures, self.tex_seen = [], set()
        self.skin_dir = skin_dir

    def material_id(self, bmat):
        name = bmat.name if bmat is not None else "Trim_Black"
        if name in self.mat_index:
            return self.mat_index[name]
        img = _image_for(bmat)
        tex = os.path.basename(bpy.path.abspath(img.filepath)) if img is not None else None
        alpha = name in ALPHA
        amb, dif, spec, exp = (ALPHA if alpha else SHADING).get(name, (0.5, 0.6, 0.15, 40))
        props = [("ksAmbient", amb, (0, 0, 0)), ("ksDiffuse", dif, (0, 0, 0)), ("ksSpecular", spec, (0, 0, 0)),
                 ("ksSpecularEXP", float(exp), (0, 0, 0)), ("ksEmissive", 0.0, (0.0, 0.0, 0.0)),
                 ("ksAlphaRef", 0.0, (0, 0, 0))]
        m = {"name": name, "shader": "ksPerPixelAlpha" if alpha else "ksPerPixel", "blend": 1 if alpha else 0,
             "depth": 1 if alpha else 0, "props": props, "tex": tex, "alpha": alpha}
        if tex and tex not in self.tex_seen:
            path = bpy.path.abspath(img.filepath)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    self.textures.append((tex, f.read()))
                self.tex_seen.add(tex)
        self.mat_index[name] = len(self.materials)
        self.materials.append(m)
        return self.mat_index[name]


# ---------------------------------------------------------------- node tree
def _skip(o):
    return o.name.startswith("PREVIEW") or o.type not in ("MESH", "EMPTY")


def _write_dummy(w, name, matrix, nchildren):
    w.i32(1)
    w.s(name)
    w.i32(nchildren)
    w.u8(1)
    w.pack("16f", *matrix)


def _write_mesh(w, sc, name, chunk, bmat, shadows):
    vb, idx, nv, sph = chunk
    mid = sc.material_id(bmat)
    w.i32(2)
    w.s(name)
    w.i32(0)
    w.u8(1)
    w.u8(1 if shadows else 0)
    w.u8(1)
    w.u8(1 if sc.materials[mid]["alpha"] else 0)
    w.i32(nv)
    w.raw(vb)
    w.i32(len(idx))
    w.pack(f"{len(idx)}H", *idx)
    w.i32(mid)
    w.i32(0)
    w.pack("2f", 0.0, 0.0)
    w.pack("4f", *sph)
    w.u8(1)


def _emit(w, sc, o):
    """Write the node for Blender object o (dummy + mesh children) and, recursively, its children."""
    kids = [c for c in o.children if not _skip(c)]
    matrix = to_ac_matrix(o.matrix_local)
    if o.type == "EMPTY":
        _write_dummy(w, o.name, matrix, len(kids))
        for c in kids:
            _emit(w, sc, c)
        return
    chunks = mesh_chunks(o)
    bmat = o.data.materials[0] if o.data.materials else None
    shadows = not o.name.startswith(NO_SHADOW)
    names = [o.name] if len(chunks) <= 1 else [f"{o.name}_SUB{i}" for i in range(len(chunks))]
    _write_dummy(w, o.name, matrix, len(chunks) + len(kids))
    for nm, ch in zip(names, chunks):
        _write_mesh(w, sc, nm, ch, bmat, shadows)
    for c in kids:
        _emit(w, sc, c)


def export(path, root_name, skin_dir=None):
    """Write every non-preview mesh/empty of the current scene to a .kn5 file. Returns a stats dict."""
    sc = _Scene(skin_dir)
    body = _W()
    roots = [o for o in bpy.data.objects if o.parent is None and not _skip(o)]
    _write_dummy(body, f"FBX: {root_name}.fbx", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], len(roots))
    for o in roots:
        _emit(body, sc, o)

    head = _W()
    head.raw(MAGIC)
    head.i32(VERSION)
    head.i32(0)
    head.i32(len(sc.textures))
    for name, data in sc.textures:
        head.i32(1)
        head.s(name)
        head.i32(len(data))
        head.raw(data)
    head.i32(len(sc.materials))
    for m in sc.materials:
        head.s(m["name"])
        head.s(m["shader"])
        head.u8(m["blend"])
        head.u8(0)
        head.i32(m["depth"])
        head.i32(len(m["props"]))
        for pname, a, c in m["props"]:
            head.s(pname)
            head.pack("10f", a, 0, 0, *c, 0, 0, 0, 0)
        if m["tex"]:
            head.i32(1)
            head.s("txDiffuse")
            head.i32(0)
            head.s(m["tex"])
        else:
            head.i32(0)
    with open(path, "wb") as f:
        f.write(head.data())
        f.write(body.data())
    return {"textures": len(sc.textures), "materials": len(sc.materials), "bytes": os.path.getsize(path)}


# ---------------------------------------------------------------- reader (used by tests and tools)
class _R:
    def __init__(self, buf):
        self.b, self.p = memoryview(buf), 0

    def take(self, n):
        v = bytes(self.b[self.p:self.p + n])
        self.p += n
        return v

    def unpack(self, fmt):
        v = struct.unpack_from("<" + fmt, self.b, self.p)
        self.p += struct.calcsize("<" + fmt)
        return v

    def i32(self):
        return self.unpack("i")[0]

    def u8(self):
        return self.unpack("B")[0]

    def s(self):
        return self.take(self.i32()).decode("utf-8", "replace")


def read(path):
    """Parse a kn5 into plain dicts: {'textures': [...], 'materials': [...], 'root': node}."""
    with open(path, "rb") as f:
        r = _R(f.read())
    assert r.take(6) == MAGIC, "bad magic"
    version = r.i32()
    if version > 5:
        r.i32()
    tex = []
    for _ in range(r.i32()):
        r.i32()
        name = r.s()
        tex.append((name, r.take(r.i32())))
    mats = []
    for _ in range(r.i32()):
        m = {"name": r.s(), "shader": r.s(), "blend": r.u8(), "alpha_test": r.u8(), "depth": r.i32(), "props": {}, "maps": []}
        for _ in range(r.i32()):
            n = r.s()
            m["props"][n] = r.unpack("10f")
        for _ in range(r.i32()):
            m["maps"].append((r.s(), r.i32(), r.s()))
        mats.append(m)

    def node():
        cls, name = r.i32(), r.s()
        nchild, active = r.i32(), r.u8()
        n = {"cls": cls, "name": name, "children": []}
        if cls == 1:
            n["matrix"] = r.unpack("16f")
        else:
            n["cast"], n["visible"], n["transparent"] = r.u8(), r.u8(), r.u8()
            nv = r.i32()
            n["vertices"] = np.frombuffer(r.take(nv * 44), np.float32).reshape(-1, 11)
            ni = r.i32()
            n["indices"] = np.frombuffer(r.take(ni * 2), np.uint16)
            n["material"], n["layer"] = r.i32(), r.i32()
            n["lod"] = r.unpack("2f")
            n["sphere"] = r.unpack("4f")
            n["renderable"] = r.u8()
        n["children"] = [node() for _ in range(nchild)]
        return n
    root = node()
    assert r.p == len(r.b), f"{len(r.b) - r.p} trailing bytes"
    return {"version": version, "textures": tex, "materials": mats, "root": root}
