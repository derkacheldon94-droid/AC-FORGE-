"""Geometry toolkit: primitives built in temporary bmeshes and merged into parts.

Every primitive returns its own bmesh (local coordinates). `Part.add()` copies it
into the part with a transform, so building thousands of pieces stays fast.
Faces that come with their own UVs keep them; everything else gets box UVs.
"""

import math

import bpy  # noqa: F401  (must be imported before bmesh/mathutils when used as a module)
import bmesh
from mathutils import Euler, Matrix, Vector

TAU = 2 * math.pi


# ---------------------------------------------------------------- transforms
def xf(loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    m = Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()
    if scale is not None:
        if isinstance(scale, (int, float)):
            scale = (scale, scale, scale)
        m = m @ Matrix.Diagonal((*scale, 1.0))
    return m


def basis(origin, right, up, normal):
    """Matrix mapping local X->right, Y->up, Z->normal, placed at origin."""
    r, u, n = Vector(right).normalized(), Vector(up).normalized(), Vector(normal).normalized()
    m = Matrix((r, u, n)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def look_rot(direction, up=(0, 0, 1)):
    """Rotation matrix whose local Z points along direction."""
    d = Vector(direction).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    return q.to_matrix().to_4x4()


# ---------------------------------------------------------------- 2D helpers
def fillet_poly(corners, radii, k=6, edge_div=1):
    """Round the corners of a closed 2D polygon. Returns a fixed number of points
    (len(corners) * (k + edge_div)), so sections with the same corner count loft cleanly."""
    n = len(corners)
    if isinstance(radii, (int, float)):
        radii = [radii] * n
    C = [Vector(c) for c in corners]
    arcs = []
    for i in range(n):
        p, a, b = C[i], C[i - 1], C[(i + 1) % n]
        u, v = (a - p), (b - p)
        la, lb = u.length, v.length
        u.normalize()
        v.normalize()
        cosang = max(-0.9999, min(0.9999, u.dot(v)))
        ang = math.acos(cosang)
        r = radii[i]
        t = r / math.tan(ang / 2) if r > 0 else 0.0
        t = min(t, 0.48 * la, 0.48 * lb)
        r_eff = t * math.tan(ang / 2)
        s, e = p + u * t, p + v * t
        if r_eff < 1e-6:
            arcs.append([p.copy() for _ in range(k)])
            continue
        bis = (u + v).normalized()
        c = p + bis * (r_eff / math.sin(ang / 2))
        a0 = math.atan2(s.y - c.y, s.x - c.x)
        a1 = math.atan2(e.y - c.y, e.x - c.x)
        da = (a1 - a0 + math.pi) % TAU - math.pi
        arcs.append([c + Vector((math.cos(a0 + da * j / (k - 1)), math.sin(a0 + da * j / (k - 1)))) * r_eff
                     for j in range(k)])
    out = []
    for i in range(n):
        out.extend(arcs[i])
        nxt = arcs[(i + 1) % n][0]
        last = arcs[i][-1]
        for j in range(1, edge_div + 1):
            out.append(last.lerp(nxt, j / (edge_div + 1)))
    return [tuple(p) for p in out]


def circle2d(r, n=16, rx=None):
    rx = r if rx is None else rx
    return [(rx * math.cos(TAU * i / n), r * math.sin(TAU * i / n)) for i in range(n)]


def rrect2d(w, h, r, k=4):
    hw, hh = w / 2, h / 2
    return fillet_poly([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)], r, k=k, edge_div=0)


def spline(points, per_seg=8, closed=False):
    """Catmull-Rom spline through points."""
    P = [Vector(p) for p in points]
    if len(P) < 3:
        out = []
        for a, b in zip(P, P[1:]):
            out += [a.lerp(b, i / per_seg) for i in range(per_seg)]
        return out + [P[-1]]
    out = []
    n = len(P)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[i - 1] if (i > 0 or closed) else P[i]
        p1, p2 = P[i], P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (i + 2 < n or closed) else P[(i + 1) % n]
        for s in range(per_seg):
            t = s / per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(P[-1])
    return out


# ---------------------------------------------------------------- primitives
def _new():
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bm.faces.layers.int.new("has_uv")
    return bm


def _cap(bm, ring, reverse=False):
    try:
        f = bm.faces.new(ring[::-1] if reverse else ring)
        return f
    except ValueError:
        return None


def box(size, r=0.0, segs=3):
    bm = _new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if r > 0:
        r = min(r, 0.49 * min(size))
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=segs, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    return bm


def cyl(r, depth, segs=24, r2=None, caps=True):
    """Cylinder/cone along Z, centred on the origin."""
    bm = _new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    return bm


def sphere(r, segs=16):
    bm = _new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(6, segs // 2), radius=r)
    return bm


def lathe(prof, segs=48, closed=True, uv=True, modulate=None, arc=TAU):
    """Revolve [(radius, axial)] around the X axis. `modulate(i, k, r)` can return a new radius
    per segment/profile point (tread blocks, pleats...). UV: u = around, v = along profile."""
    bm = _new()
    uvl = bm.loops.layers.uv.active
    has = bm.faces.layers.int["has_uv"]
    full = abs(arc - TAU) < 1e-6
    ring_count = segs if full else segs + 1
    rings = []
    for i in range(ring_count):
        t = arc * i / segs
        c, s = math.cos(t), math.sin(t)
        ring = []
        for k, (r, a) in enumerate(prof):
            rr = modulate(i, k, r) if modulate else r
            ring.append(bm.verts.new((a, rr * c, rr * s)))
        rings.append(ring)
    n = len(prof)
    kmax = n if closed else n - 1
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % ring_count]
        for k in range(kmax):
            k2 = (k + 1) % n
            try:
                f = bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
            except ValueError:
                continue
            if uv:
                f[has] = 1
                us = (i / segs, i / segs, (i + 1) / segs, (i + 1) / segs)
                vs = (k / kmax, (k + 1) / kmax, (k + 1) / kmax, k / kmax)
                for lp, u_, v_ in zip(f.loops, us, vs):
                    lp[uvl].uv = (u_, v_)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return bm


def loft(sections, closed_ring=True, caps=True):
    """Connect a list of same-length 3D point rings."""
    bm = _new()
    rings = [[bm.verts.new(p) for p in sec] for sec in sections]
    n = len(sections[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(n if closed_ring else n - 1):
            k2 = (k + 1) % n
            try:
                bm.faces.new((a[k], a[k2], b[k2], b[k]))
            except ValueError:
                pass
    if caps and closed_ring:
        _cap(bm, rings[0], reverse=True)
        _cap(bm, rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sweep(path, profile, closed=False, caps=True, scale=None, up_hint=None):
    """Sweep a closed 2D profile along a 3D path with parallel-transport frames.
    scale(t) optionally scales the profile along the path (t in 0..1)."""
    P = [Vector(p) for p in path]
    n = len(P)
    T = []
    for i in range(n):
        if closed:
            d = P[(i + 1) % n] - P[i - 1]
        elif i == 0:
            d = P[1] - P[0]
        elif i == n - 1:
            d = P[-1] - P[-2]
        else:
            d = P[i + 1] - P[i - 1]
        T.append(d.normalized() if d.length > 1e-9 else Vector((0, 0, 1)))
    hint = Vector(up_hint) if up_hint else (Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0)))
    N = [(hint - T[0] * hint.dot(T[0])).normalized()]
    for i in range(1, n):
        q = T[i - 1].rotation_difference(T[i])
        nn = q @ N[-1]
        nn = (nn - T[i] * nn.dot(T[i])).normalized()
        N.append(nn)
    sections = []
    for i in range(n):
        b = T[i].cross(N[i])
        s = scale(i / max(1, n - 1)) if scale else 1.0
        sections.append([P[i] + N[i] * (u * s) + b * (v * s) for u, v in profile])
    bm = _new()
    rings = [[bm.verts.new(p) for p in sec] for sec in sections]
    m = len(profile)
    seg_range = range(n) if closed else range(n - 1)
    for i in seg_range:
        a, b_ = rings[i], rings[(i + 1) % n]
        for k in range(m):
            k2 = (k + 1) % m
            try:
                bm.faces.new((a[k], a[k2], b_[k2], b_[k]))
            except ValueError:
                pass
    if caps and not closed:
        _cap(bm, rings[0], reverse=True)
        _cap(bm, rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def tube(path, r, segs=14, closed=False, smooth=True, per_seg=6):
    pts = spline(path, per_seg=per_seg, closed=closed) if smooth and len(path) > 2 else path
    return sweep(pts, circle2d(r, segs), closed=closed)


def prism(pts2d, depth, axis="X"):
    """Extrude a closed 2D polygon. axis=X: pts are (y, z); axis=Y: (x, z); axis=Z: (x, y)."""
    bm = _new()

    def P(a, b, d):
        if axis == "X":
            return (d, a, b)
        if axis == "Y":
            return (a, d, b)
        return (a, b, d)
    lo = [bm.verts.new(P(a, b, -depth / 2)) for a, b in pts2d]
    hi = [bm.verts.new(P(a, b, depth / 2)) for a, b in pts2d]
    _cap(bm, lo)
    _cap(bm, hi, reverse=True)
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def helix(radius, length, turns, wire, steps_per_turn=24, wire_segs=8):
    pts = []
    n = int(turns * steps_per_turn)
    for i in range(n + 1):
        t = i / n
        a = t * turns * TAU
        pts.append((radius * math.cos(a), radius * math.sin(a), length * t))
    return sweep(pts, circle2d(wire, wire_segs))


_font_cache = {}


def text(body, size=0.1, depth=0.002, bevel=0.0, font_path=None):
    """Text as a mesh (XY plane, facing +Z, centred)."""
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth / 2
    cu.bevel_depth = bevel
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    if font_path:
        if font_path not in _font_cache:
            _font_cache[font_path] = bpy.data.fonts.load(font_path)
        cu.font = _font_cache[font_path]
    o = bpy.data.objects.new("txt_tmp", cu)
    bpy.context.scene.collection.objects.link(o)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o)
    bpy.data.curves.remove(cu)
    bm = _new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    if "has_uv" not in bm.faces.layers.int:
        bm.faces.layers.int.new("has_uv")
    return bm


def from_object(o, apply_mods=True):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg) if apply_mods else o)
    bm = _new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    if "has_uv" not in bm.faces.layers.int:
        bm.faces.layers.int.new("has_uv")
    return bm


# ---------------------------------------------------------------- merge / parts
def merge(dst, src, matrix=None, free=True):
    m = matrix or Matrix.Identity(4)
    uv_s = src.loops.layers.uv.active
    uv_d = dst.loops.layers.uv.active
    has_s = src.faces.layers.int.get("has_uv")
    has_d = dst.faces.layers.int["has_uv"]
    vmap = {}
    for v in src.verts:
        vmap[v] = dst.verts.new(m @ v.co)
    flip = m.to_3x3().determinant() < 0
    for f in src.faces:
        vs = [vmap[v] for v in f.verts]
        loops = list(f.loops)
        if flip:
            vs.reverse()
            loops.reverse()
        try:
            nf = dst.faces.new(vs)
        except ValueError:
            continue
        if has_s is not None and f[has_s] and uv_s is not None:
            nf[has_d] = 1
            for lp_d, lp_s in zip(nf.loops, loops):
                lp_d[uv_d].uv = lp_s[uv_s].uv
    if free:
        src.free()


def box_uv(bm, scale=1.0, only_missing=True):
    bm.normal_update()
    uv = bm.loops.layers.uv.active
    has = bm.faces.layers.int["has_uv"]
    for f in bm.faces:
        if only_missing and f[has]:
            continue
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            c = lp.vert.co
            if ax == 0:
                lp[uv].uv = (c.y * scale, c.z * scale)
            elif ax == 1:
                lp[uv].uv = (c.x * scale, c.z * scale)
            else:
                lp[uv].uv = (c.x * scale, c.y * scale)


def planar_uv(bm, origin, u_axis, v_axis, size_u, size_v):
    """Planar projection of the whole bmesh into 0..1 (for decals, gauges, plates)."""
    uv = bm.loops.layers.uv.active
    has = bm.faces.layers.int["has_uv"]
    o, U, Vv = Vector(origin), Vector(u_axis), Vector(v_axis)
    for f in bm.faces:
        f[has] = 1
        for lp in f.loops:
            d = lp.vert.co - o
            lp[uv].uv = (0.5 + d.dot(U) / size_u, 0.5 + d.dot(Vv) / size_v)


class Part:
    """One output mesh object (one material)."""

    registry = []
    post = None      # optional matrix applied to every part built while set (e.g. left-side wheels)

    def __init__(self, name, material, parent=None, smooth=35, uv_scale=1.0, group=None):
        self.name, self.material, self.parent = name, material, parent
        self.smooth, self.uv_scale, self.group = smooth, uv_scale, group
        self.bm = _new()

    def add(self, prim, loc=(0, 0, 0), rot=(0, 0, 0), scale=None, matrix=None):
        merge(self.bm, prim, matrix if matrix is not None else xf(loc, rot, scale))
        return self

    def mirror_x(self):
        """Duplicate everything mirrored across X (left/right)."""
        tmp = self.bm.copy()
        merge(self.bm, tmp, Matrix.Diagonal((-1, 1, 1, 1)))
        return self

    def build(self, collection, materials):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        box_uv(bm, self.uv_scale)
        if Part.post is not None:
            bmesh.ops.transform(bm, matrix=Part.post, verts=bm.verts)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(materials[self.material])
        if self.smooth:
            me.shade_smooth()
            try:
                me.set_sharp_from_angle(angle=math.radians(self.smooth))
            except Exception:
                pass
        o = bpy.data.objects.new(self.name, me)
        collection.objects.link(o)
        if self.parent is not None:
            o.parent = self.parent
        o["forge_group"] = self.group or ""
        return o


def fillet_open(points, r, k=6):
    """Round the interior corners of an open 3D polyline."""
    P = [Vector(p) for p in points]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        p, a, b = P[i], P[i - 1], P[i + 1]
        u, v = (a - p), (b - p)
        la, lb = u.length, v.length
        u.normalize()
        v.normalize()
        ang = math.acos(max(-0.9999, min(0.9999, u.dot(v))))
        t = min(r / math.tan(ang / 2), 0.48 * la, 0.48 * lb)
        s, e = p + u * t, p + v * t
        for j in range(k):
            w = j / (k - 1)
            # quadratic bezier s -> p -> e approximates the arc well
            out.append(s * (1 - w) ** 2 + p * 2 * w * (1 - w) + e * w * w)
    out.append(P[-1])
    return out


# ---------------------------------------------------------------- object-level ops
def apply_modifiers(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = o.name
    bpy.data.meshes.remove(old)
    return o


def bm_to_object(bm, name, collection):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    collection.objects.link(o)
    return o


def boolean(o, cutters, operation="DIFFERENCE"):
    """Apply an exact boolean with a list of cutter bmeshes."""
    scene = bpy.context.scene
    col = bpy.data.collections.new("_cutters")
    scene.collection.children.link(col)
    for i, c in enumerate(cutters):
        bmesh.ops.recalc_face_normals(c, faces=c.faces)
        bm_to_object(c, f"_cut{i}", col)
    mod = o.modifiers.new("bool", "BOOLEAN")
    mod.operation = operation
    mod.operand_type = "COLLECTION"
    mod.collection = col
    mod.solver = "EXACT"
    apply_modifiers(o)
    for ob in list(col.objects):
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    bpy.data.collections.remove(col)
    return o


def bevel_mod(o, width, segments=2, angle=40):
    mod = o.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.use_clamp_overlap = True
    apply_modifiers(o)
    return o


def solidify_mod(o, thickness, offset=-1.0):
    mod = o.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = True
    apply_modifiers(o)
    return o


def smooth_by_angle(o, angle=35):
    me = o.data
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def weighted_normals(o, weight=50):
    """Face-area weighted normals: keeps big flat panels flat next to rounded edges."""
    mod = o.modifiers.new("wn", "WEIGHTED_NORMAL")
    mod.weight = weight
    mod.keep_sharp = True
    mod.mode = "FACE_AREA"
    apply_modifiers(o)
