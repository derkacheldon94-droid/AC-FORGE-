"""
AC Forge - Blackout Pickup: procedural 3D model builder for Assetto Corsa.

Builds a lowered, wide-body, twin-turbo regular-cab pickup (based on the
concept art in /concept) entirely from code, then exports:
  out/acf_blackout_pickup.fbx   -> import into the AC Editor (ksEditor) to make the .kn5
  out/acf_blackout_pickup.blend -> editable Blender source
  out/acf_blackout_pickup.glb   -> quick preview in any 3D viewer
  out/textures/*.png            -> textures referenced by the FBX
  out/preview_*.png             -> renders (when run with --render)

Run with Blender 4.2+ (or the `bpy` Python module):
  blender -b -P blender/build_truck.py -- [--render]
  python blender/build_truck.py [--render]          (with `pip install bpy`)

Coordinates while modelling (Blender): +Y = forward, +Z = up, -X = car's LEFT
(driver side, US left-hand drive). Ground is z = 0, origin is the middle of the
wheelbase. The FBX is exported Y-up / Z-forward, which is what AC uses.

Node names follow Assetto Corsa conventions so wheels spin/steer in game:
  WHEEL_LF/RF/LR/RR  rims + tyres (rotate and steer)
  SUSP_LF/...        calipers (steer, don't rotate)
  DISC_LF/...        brake discs (rotate, glow)
  STEER_HR           steering wheel (rotates around its local Z in AC)
  COCKPIT_HR         interior group
  LIGHT_HEAD_L/R, LIGHT_TAIL_L/R   emissive meshes referenced by data/lights.ini
"""

import math
import os
import sys

import bpy  # must be imported before bmesh/mathutils when used as a module
import bmesh
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TEX = os.path.join(OUT, "textures")
CAR_ID = "acf_blackout_pickup"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
DO_RENDER = "--render" in argv

# ---------------------------------------------------------------- dimensions
WB = 2.98                 # wheelbase
FA, RA = WB / 2, -WB / 2  # front / rear axle Y
TRACK_F, TRACK_R = 1.72, 1.70
TYRE_R = 0.355            # 275/35R20-ish, slammed
RIM_R = 0.254             # 20" rims
TYRE_W_F, TYRE_W_R = 0.285, 0.335
WHEEL_Z = TYRE_R
ARCH_R = 0.40
BODY_X = 0.98             # outer face of the body sides
BELT_Z = 1.04             # beltline height
ROOF_Z = 1.58
ROCKER_Z = 0.27
FRONT_Y = 2.22
REAR_Y = -2.53

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COL = scene.collection
os.makedirs(TEX, exist_ok=True)

# ---------------------------------------------------------------- materials
M = {}


def make_texture(name, rgb, size=64, stripes=None, a=1.0):
    """Write a small solid (or striped) PNG and return the image datablock."""
    img = bpy.data.images.new(name, size, size, alpha=a < 1.0)
    px = []
    for yy in range(size):
        for xx in range(size):
            c = rgb
            if stripes and (yy // stripes[0]) % 2 == 0:
                c = stripes[1]
            px.extend((c[0], c[1], c[2], a))
    img.pixels = px
    path = os.path.join(TEX, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    if a < 1.0:
        img.alpha_mode = "STRAIGHT"
    img.save()
    return img


def mat(name, rgb, metal=0.0, rough=0.5, emit=None, emit_k=0.0, alpha=1.0, stripes=None):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = make_texture(name, rgb, stripes=stripes, a=alpha)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-400, 200)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = emit_k
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    m.diffuse_color = (*rgb, alpha)
    M[name] = m
    return m


mat("Paint_Black", (0.018, 0.02, 0.02), metal=0.3, rough=0.35)
mat("Trim_Black", (0.008, 0.008, 0.008), rough=0.6)
mat("Grille_Black", (0.012, 0.012, 0.013), rough=0.5, stripes=(4, (0.003, 0.003, 0.003)))
mat("Interior_Black", (0.02, 0.02, 0.02), rough=0.8)
mat("Seat_Red", (0.45, 0.02, 0.02), rough=0.6)
mat("Rim_Red", (0.42, 0.015, 0.015), metal=0.6, rough=0.3)
mat("Rim_Lip_Silver", (0.65, 0.66, 0.68), metal=1.0, rough=0.2)
mat("Tyre", (0.02, 0.02, 0.02), rough=0.9)
mat("Brake_Disc", (0.32, 0.32, 0.33), metal=1.0, rough=0.4)
mat("Caliper_Red", (0.55, 0.02, 0.02), rough=0.35)
mat("Metal_Polished", (0.8, 0.8, 0.82), metal=1.0, rough=0.12)
mat("Metal_Alu", (0.55, 0.56, 0.58), metal=1.0, rough=0.35)
mat("Engine_Dark", (0.06, 0.06, 0.065), metal=0.6, rough=0.5)
mat("ValveCover_Red", (0.5, 0.03, 0.02), metal=0.3, rough=0.3)
mat("Intercooler", (0.45, 0.46, 0.47), metal=0.8, rough=0.5, stripes=(2, (0.2, 0.2, 0.21)))
mat("Rubber_Hose", (0.015, 0.015, 0.015), rough=0.7)
mat("Glass", (0.05, 0.06, 0.07), rough=0.05, alpha=0.25)
mat("Lamp_Glass", (0.01, 0.01, 0.012), rough=0.1)
mat("Light_Head", (1.0, 1.0, 1.0), emit=(0.85, 0.9, 1.0), emit_k=6.0)
mat("Light_Tail", (0.45, 0.02, 0.02), emit=(1.0, 0.05, 0.03), emit_k=2.0)
mat("Filter_Red", (0.55, 0.03, 0.03), rough=0.8)
mat("Strap_Red", (0.5, 0.02, 0.02), rough=0.7)


# ---------------------------------------------------------------- mesh helpers
def cube_uv(bm, scale=1.0):
    """Box-project UVs (needed by ksEditor even for solid-colour textures)."""
    bm.normal_update()
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
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


def obj(name, bm, mat_name, parent=None, smooth=False, loc=None, recalc=True):
    if recalc:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cube_uv(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M[mat_name])
    if smooth:
        try:
            me.shade_smooth()
        except Exception:
            for p in me.polygons:
                p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    COL.objects.link(o)
    if parent is not None:
        o.parent = parent
    if loc is not None:
        o.location = loc
    return o


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.2
    e.location = loc
    e.rotation_euler = rot
    COL.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


def _xf(rot=(0, 0, 0), loc=(0, 0, 0)):
    return Matrix.Translation(loc) @ Euler(rot).to_matrix().to_4x4()


def add_box(bm, size, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    vs = ret["verts"]
    bmesh.ops.scale(bm, vec=size, verts=vs)
    bmesh.ops.transform(bm, matrix=_xf(rot, loc), verts=vs)
    if bevel > 0:
        edges = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=2, profile=0.5, affect="EDGES",
                        clamp_overlap=True)


def add_cyl(bm, r, depth, loc=(0, 0, 0), rot=(0, 0, 0), segs=24, r2=None):
    """Cylinder/cone along local Z."""
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r if r2 is None else r2, depth=depth)
    bmesh.ops.transform(bm, matrix=_xf(rot, loc), verts=ret["verts"])


def add_sphere(bm, r, loc=(0, 0, 0), segs=12):
    ret = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=max(6, segs // 2), radius=r)
    bmesh.ops.translate(bm, vec=loc, verts=ret["verts"])


def add_beam(bm, p1, p2, w, h=None, round_=False, segs=12):
    """Box (or cylinder) spanning p1 -> p2."""
    p1, p2 = Vector(p1), Vector(p2)
    v = p2 - p1
    q = Vector((0, 0, 1)).rotation_difference(v.normalized())
    mid = (p1 + p2) / 2
    if round_:
        ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                    radius1=w, radius2=w, depth=v.length)
    else:
        ret = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(w, h or w, v.length), verts=ret["verts"])
    bmesh.ops.transform(bm, matrix=Matrix.Translation(mid) @ q.to_matrix().to_4x4(), verts=ret["verts"])


def add_pipe(bm, pts, r, segs=12):
    pts = [Vector(p) for p in pts]
    for a, b in zip(pts, pts[1:]):
        add_beam(bm, a, b, r, round_=True, segs=segs)
    for p in pts[1:-1]:
        add_sphere(bm, r, p, segs=segs)


def add_lathe(bm, prof, segs=48, rot=(0, 0, 0), loc=(0, 0, 0), closed=True):
    """Revolve a profile of (radius, axial) points around the X axis."""
    rings = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        c, s = math.cos(t), math.sin(t)
        rings.append([bm.verts.new((a, r * c, r * s)) for r, a in prof])
    n = len(prof)
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % segs]
        for k in range(n if closed else n - 1):
            k2 = (k + 1) % n
            bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
    allv = [v for ring in rings for v in ring]
    bmesh.ops.transform(bm, matrix=_xf(rot, loc), verts=allv)


def add_prism_x(bm, pts, x0, x1):
    """Extrude a side-view polygon [(y, z), ...] across X from x0 to x1."""
    a = [bm.verts.new((x0, y, z)) for y, z in pts]
    b = [bm.verts.new((x1, y, z)) for y, z in pts]
    bm.faces.new(a)
    bm.faces.new(b[::-1])
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))


def add_helix(bm, base, top, radius, turns, wire, steps_per_turn=16):
    base, top = Vector(base), Vector(top)
    axis = top - base
    q = Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix()
    pts = []
    n = int(turns * steps_per_turn)
    for i in range(n + 1):
        t = i / n
        ang = t * turns * 2 * math.pi
        local = Vector((radius * math.cos(ang), radius * math.sin(ang), axis.length * t))
        pts.append(base + q @ local)
    for a, b in zip(pts, pts[1:]):
        add_beam(bm, a, b, wire, round_=True, segs=6)


def arch_pts(cy, cz, r, zb, n=14):
    a0 = math.asin((zb - cz) / r)
    out = []
    for i in range(n + 1):
        a = (math.pi - a0) + (2 * a0 - math.pi) * i / n
        out.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return out


def mirror_sides(fn):
    """Call fn(sign) for the left (-1) and right (+1) side."""
    for s in (-1, 1):
        fn(s)


# ================================================================ BODY
def build_body():
    # --- side panels (front fender + door + bed side) with wheel arches cut in
    zb = ROCKER_Z
    prof = [(REAR_Y, zb + 0.04)]
    prof += arch_pts(RA, WHEEL_Z + 0.02, ARCH_R, zb)
    prof += arch_pts(FA, WHEEL_Z + 0.02, ARCH_R, zb)
    prof += [(FRONT_Y, zb + 0.06), (FRONT_Y, 0.98), (FRONT_Y - 0.06, BELT_Z - 0.02),
             (REAR_Y + 0.03, BELT_Z), (REAR_Y, BELT_Z - 0.04)]
    for s in (-1, 1):
        bm = bmesh.new()
        add_prism_x(bm, prof, s * (BODY_X - 0.05), s * BODY_X)
        obj(f"BODY_SIDE_{'L' if s < 0 else 'R'}", bm, "Paint_Black")

    bm = bmesh.new()
    # floor pan / underbody
    add_box(bm, (2 * BODY_X - 0.1, 3.3, 0.05), (0, -0.05, 0.31))
    # firewall
    add_box(bm, (2 * BODY_X - 0.1, 0.05, 0.72), (0, 0.92, 0.68))
    # cowl (between engine bay and windshield)
    add_box(bm, (2 * BODY_X - 0.06, 0.16, 0.05), (0, 0.98, BELT_Z - 0.01), bevel=0.01)
    # cab back wall lower + bed front wall
    add_box(bm, (2 * BODY_X - 0.1, 0.05, 0.75), (0, -0.83, 0.68))
    add_box(bm, (2 * BODY_X - 0.1, 0.05, 0.45), (0, -0.92, 0.82))
    # bed floor
    add_box(bm, (2 * BODY_X - 0.1, 1.56, 0.04), (0, -1.72, 0.60))
    # tailgate
    add_box(bm, (2 * BODY_X - 0.02, 0.06, BELT_Z - zb - 0.05), (0, REAR_Y - 0.0, (BELT_Z + zb) / 2),
            bevel=0.015)
    # bed rail caps
    for s in (-1, 1):
        add_box(bm, (0.1, 1.62, 0.03), (s * (BODY_X - 0.05), -1.71, BELT_Z + 0.01), bevel=0.008)
    # inner fender walls (engine bay)
    for s in (-1, 1):
        add_box(bm, (0.04, 1.25, 0.5), (s * 0.70, 1.58, 0.72))
    # core support top bar
    add_box(bm, (1.6, 0.08, 0.05), (0, 2.12, 0.98))
    obj("BODY_SHELL", bm, "Paint_Black")

    # --- fender flares (wide body) around all four arches
    bm = bmesh.new()
    for cy, x_out in ((FA, 1.065), (RA, 1.08)):
        for s in (-1, 1):
            n = 18
            a0 = math.asin((ROCKER_Z + 0.02 - (WHEEL_Z + 0.02)) / ARCH_R)
            prev = None
            for i in range(n + 1):
                a = (math.pi - a0) + (2 * a0 - math.pi) * i / n
                ca, sa = math.cos(a), math.sin(a)
                taper = 1.0 - 0.5 * abs(ca) ** 4       # thinner at the ends
                r_in, r_out = ARCH_R - 0.005, ARCH_R + 0.085 * taper
                xi = s * (BODY_X - 0.02)
                xo = s * (BODY_X + (x_out - BODY_X) * taper)
                zc = WHEEL_Z + 0.02
                ring = [
                    bm.verts.new((xi, cy + r_in * ca, zc + r_in * sa)),
                    bm.verts.new((xo, cy + r_in * ca, zc + r_in * sa)),
                    bm.verts.new((xo, cy + r_out * ca, zc + r_out * sa)),
                    bm.verts.new((xi, cy + (r_out + 0.03) * ca, zc + (r_out + 0.03) * sa)),
                ]
                if prev:
                    for k in range(3):
                        bm.faces.new((prev[k], prev[k + 1], ring[k + 1], ring[k]))
                else:
                    bm.faces.new(ring)
                prev = ring
            bm.faces.new(prev[::-1])
    obj("BODY_FLARES", bm, "Paint_Black")

    # --- side skirts and rear bumper (black trim)
    bm = bmesh.new()
    for s in (-1, 1):
        add_box(bm, (0.08, FA - RA - 2 * ARCH_R - 0.12, 0.09),
                (s * (BODY_X + 0.01), (FA + RA) / 2, ROCKER_Z + 0.02), bevel=0.02)
    add_box(bm, (2 * BODY_X + 0.06, 0.14, 0.22), (0, REAR_Y - 0.09, 0.40), bevel=0.03)
    add_box(bm, (1.6, 0.25, 0.03), (0, REAR_Y - 0.05, 0.27))          # rear diffuser
    for x in (-0.5, -0.25, 0, 0.25, 0.5):
        add_box(bm, (0.01, 0.25, 0.08), (x, REAR_Y - 0.05, 0.31))
    obj("BODY_TRIM_REAR", bm, "Trim_Black")

    # --- panel gaps, door handle, fuel door (small dark details)
    bm = bmesh.new()
    for s in (-1, 1):
        x = s * (BODY_X + 0.002)
        for y in (0.88, -0.70, -0.875):
            add_box(bm, (0.004, 0.006, BELT_Z - ROCKER_Z - 0.08), (x, y, (BELT_Z + ROCKER_Z) / 2 + 0.02))
        add_box(bm, (0.012, 0.16, 0.03), (s * (BODY_X + 0.006), -0.52, 0.90), bevel=0.005)  # handle
    add_cyl(bm, 0.075, 0.006, (-(BODY_X + 0.003), -1.0, 0.80), rot=(0, math.pi / 2, 0), segs=24)  # fuel door
    obj("BODY_DETAILS", bm, "Trim_Black")

    # --- greenhouse: roof, pillars, mirrors
    bm = bmesh.new()
    add_box(bm, (1.64, 1.14, 0.05), (0, -0.25, ROOF_Z - 0.02), bevel=0.02)
    for s in (-1, 1):
        x_lo, x_hi = s * (BODY_X - 0.10), s * 0.80
        add_beam(bm, (x_lo, 0.94, BELT_Z), (x_hi, 0.32, ROOF_Z - 0.03), 0.06, 0.05)  # A-pillar
        add_box(bm, (0.07, 0.16, ROOF_Z - BELT_Z), (s * 0.82, -0.75, (ROOF_Z + BELT_Z) / 2 - 0.01))  # C
        add_box(bm, (0.05, 0.05, ROOF_Z - BELT_Z), (s * 0.84, -0.42, (ROOF_Z + BELT_Z) / 2 - 0.01))  # B
        # mirror arm + housing
        add_beam(bm, (s * (BODY_X - 0.02), 0.82, BELT_Z + 0.03), (s * 1.10, 0.80, BELT_Z + 0.08), 0.025, 0.04)
        add_box(bm, (0.13, 0.08, 0.13), (s * 1.13, 0.79, BELT_Z + 0.11), bevel=0.02)
    add_box(bm, (1.62, 0.06, 0.04), (0, -0.81, BELT_Z + 0.01))      # rear window sill
    add_box(bm, (1.62, 0.06, 0.04), (0, -0.81, ROOF_Z - 0.05))      # rear window header
    obj("BODY_GREENHOUSE", bm, "Paint_Black")

    bm = bmesh.new()
    add_beam(bm, (0, 0.95, BELT_Z + 0.02), (0, 0.33, ROOF_Z - 0.05), 1.56, 0.01)   # windshield
    add_box(bm, (1.56, 0.01, ROOF_Z - BELT_Z - 0.08), (0, -0.81, (ROOF_Z + BELT_Z) / 2 - 0.01))  # back glass
    obj("GLASS_WINDOWS", bm, "Glass")


# ================================================================ FRONT END
def build_front():
    fy = FRONT_Y
    bm = bmesh.new()
    # fascia frame between lamps
    add_box(bm, (2 * BODY_X - 0.02, 0.08, 0.42), (0, fy - 0.02, 0.80), bevel=0.01)
    # front bumper (frame around the intercooler)
    add_box(bm, (2 * BODY_X + 0.04, 0.24, 0.11), (0, fy + 0.07, 0.565), bevel=0.03)   # top bar
    for s in (-1, 1):
        add_box(bm, (0.36, 0.26, 0.30), (s * (BODY_X - 0.16), fy + 0.08, 0.36), bevel=0.04)
        add_box(bm, (0.12, 0.02, 0.12), (s * (BODY_X - 0.16), fy + 0.215, 0.38))   # brake duct
        add_beam(bm, (s * 0.98, fy + 0.2, 0.26), (s * 1.06, fy + 0.05, 0.30), 0.02, 0.12)  # canard
    add_box(bm, (2.06, 0.36, 0.025), (0, fy + 0.17, 0.215), bevel=0.008)              # splitter
    obj("BODY_FRONT_BUMPER", bm, "Trim_Black")

    bm = bmesh.new()
    # grille mesh with horizontal slats
    add_box(bm, (1.18, 0.03, 0.36), (0, fy + 0.01, 0.80))
    for z in (0.67, 0.73, 0.79, 0.85, 0.91):
        add_box(bm, (1.16, 0.035, 0.012), (0, fy + 0.03, z))
    add_box(bm, (0.04, 0.035, 0.34), (0, fy + 0.03, 0.80))
    # bumper mouth backing
    add_box(bm, (1.25, 0.02, 0.26), (0, fy + 0.01, 0.37))
    obj("BODY_GRILLE", bm, "Grille_Black")

    # intercooler core + end tanks in the bumper mouth
    bm = bmesh.new()
    add_box(bm, (1.12, 0.07, 0.22), (0, fy + 0.07, 0.38))
    obj("ENGINE_INTERCOOLER", bm, "Intercooler")
    bm = bmesh.new()
    for s in (-1, 1):
        add_box(bm, (0.08, 0.09, 0.25), (s * 0.60, fy + 0.07, 0.38), bevel=0.02)
    obj("ENGINE_INTERCOOLER_TANKS", bm, "Metal_Alu")

    # quad lamps: dark lens housing + emissive double-bracket light signatures
    bm = bmesh.new()
    for s in (-1, 1):
        for z in (0.69, 0.89):
            add_box(bm, (0.30, 0.04, 0.15), (s * 0.79, fy + 0.005, z), bevel=0.01)
    obj("LAMP_HOUSINGS", bm, "Lamp_Glass")

    for s in (-1, 1):
        bm = bmesh.new()
        for z in (0.69, 0.89):
            for k, xc in enumerate((0.70, 0.86)):
                # bracket opening towards the car centre on each side ( "]]" / "[[" )
                x = s * xc
                add_box(bm, (0.09, 0.012, 0.012), (x, fy + 0.03, z + 0.045))
                add_box(bm, (0.09, 0.012, 0.012), (x, fy + 0.03, z - 0.045))
                add_box(bm, (0.012, 0.012, 0.10), (x + s * 0.045, fy + 0.03, z))
        obj(f"LIGHT_HEAD_{'L' if s < 0 else 'R'}", bm, "Light_Head")

    # tail lights
    for s in (-1, 1):
        bm = bmesh.new()
        add_box(bm, (0.12, 0.05, 0.40), (s * (BODY_X - 0.07), REAR_Y - 0.02, 0.80), bevel=0.01)
        obj(f"LIGHT_TAIL_{'L' if s < 0 else 'R'}", bm, "Light_Tail")


# ================================================================ ENGINE + TURBO KIT
def build_engine():
    # --- V8 in the front bay
    bm = bmesh.new()
    add_box(bm, (0.46, 0.70, 0.36), (0, 1.40, 0.62), bevel=0.02)            # block
    add_box(bm, (0.30, 0.20, 0.25), (0, 1.86, 0.60), bevel=0.02)            # timing cover / front
    for x, z in ((-0.12, 0.62), (0.12, 0.62), (0, 0.76)):
        add_cyl(bm, 0.055, 0.03, (x, 1.98, z), rot=(math.pi / 2, 0, 0))     # pulleys
    add_box(bm, (0.12, 0.62, 0.10), (0, 1.40, 0.94), bevel=0.02)            # intake runners base
    add_box(bm, (1.52, 0.04, 0.48), (0, 2.08, 0.70))                       # radiator
    obj("ENGINE_BLOCK", bm, "Engine_Dark")

    bm = bmesh.new()
    for s in (-1, 1):
        add_box(bm, (0.17, 0.62, 0.08), (s * 0.20, 1.40, 0.88), rot=(0, -s * 0.55, 0), bevel=0.02)
    obj("ENGINE_VALVE_COVERS", bm, "ValveCover_Red")

    bm = bmesh.new()
    for s in (-1, 1):
        for i in range(4):
            add_box(bm, (0.05, 0.05, 0.08), (s * 0.27, 1.17 + i * 0.155, 0.96), rot=(0, -s * 0.55, 0))
        add_beam(bm, (s * 0.30, 1.12, 0.97), (s * 0.30, 1.68, 0.97), 0.008, round_=True, segs=6)
    # twin throttle bodies (oval inlets on top, as in the concept art)
    for s in (-1, 1):
        add_cyl(bm, 0.075, 0.16, (s * 0.09, 1.70, 1.08), rot=(math.pi / 2 - 0.25, 0, 0), segs=20)
    obj("ENGINE_COILS_THROTTLE", bm, "Trim_Black")

    bm = bmesh.new()
    add_box(bm, (0.30, 0.62, 0.10), (0, 1.40, 1.02), bevel=0.03)            # intake plenum
    for s in (-1, 1):                                                       # headers
        for i in range(4):
            y = 1.17 + i * 0.155
            add_pipe(bm, [(s * 0.24, y, 0.66), (s * 0.40, y, 0.62), (s * 0.48, y - 0.1, 0.45),
                          (s * 0.48, 0.95, 0.40)], 0.022, segs=8)
    obj("ENGINE_METAL", bm, "Metal_Alu")

    # charge pipe + red cone filter in the bay
    bm = bmesh.new()
    add_pipe(bm, [(0.45, 2.02, 0.48), (0.50, 1.95, 0.80), (0.40, 1.80, 1.02), (0.12, 1.78, 1.10)], 0.045)
    add_pipe(bm, [(-0.45, 2.02, 0.48), (-0.55, 1.6, 0.75)], 0.04)
    obj("ENGINE_CHARGE_PIPES", bm, "Metal_Polished")
    bm = bmesh.new()
    add_cyl(bm, 0.08, 0.20, (-0.55, 1.47, 0.82), rot=(math.pi / 2 + 0.4, 0, 0), r2=0.06)
    obj("ENGINE_FILTER", bm, "Filter_Red")

    # --- twin-turbo package in the bed (behind the cab)
    bm = bmesh.new()
    for s in (-1, 1):
        cx = s * 0.36
        # compressor housing (snail) + turbine housing, shaft along X
        add_lathe(bm, [(0.02, -0.07), (0.15, -0.07), (0.17, -0.03), (0.17, 0.03), (0.15, 0.07), (0.02, 0.07)],
                  segs=28, loc=(cx, -1.20, 0.98))
        add_lathe(bm, [(0.02, -0.06), (0.12, -0.06), (0.13, 0.0), (0.12, 0.06), (0.02, 0.06)],
                  segs=24, loc=(cx + s * 0.17, -1.20, 0.98))
        add_cyl(bm, 0.07, 0.12, (cx - s * 0.12, -1.20, 0.98), rot=(0, math.pi / 2, 0))     # inlet bell
    obj("TURBO_HOUSINGS", bm, "Metal_Alu")

    bm = bmesh.new()
    for s in (-1, 1):
        cx = s * 0.36
        # hot side: down-pipe through the bed floor; cold side: big charge pipes to the cab wall
        add_pipe(bm, [(cx + s * 0.17, -1.20, 0.86), (cx + s * 0.17, -1.20, 0.70), (cx + s * 0.25, -1.05, 0.62)], 0.05)
        add_pipe(bm, [(cx, -1.05, 1.10), (cx * 0.6, -0.97, 1.16), (cx * 0.4, -0.97, 0.64)], 0.055)
        add_pipe(bm, [(cx, -1.36, 1.05), (cx, -1.55, 1.05), (cx * 0.5, -1.75, 0.95), (cx * 0.5, -1.95, 0.75)], 0.05)
    # crossover / log manifold between the turbos
    add_pipe(bm, [(-0.36, -1.32, 0.80), (0, -1.36, 0.76), (0.36, -1.32, 0.80)], 0.045)
    obj("TURBO_PIPES", bm, "Metal_Polished")

    # blow-off / filters on the turbo inlets
    bm = bmesh.new()
    for s in (-1, 1):
        add_cyl(bm, 0.075, 0.14, (s * 0.12, -1.20, 0.98), rot=(0, math.pi / 2, 0), r2=0.06)
    obj("TURBO_FILTERS", bm, "Filter_Red")

    # fuel cell, straps, coilovers, driveshaft
    bm = bmesh.new()
    add_box(bm, (1.10, 0.40, 0.24), (0, -2.22, 0.74), bevel=0.02)
    add_cyl(bm, 0.06, 0.04, (0.2, -2.22, 0.88))
    obj("BED_FUEL_CELL", bm, "Metal_Polished")
    bm = bmesh.new()
    for x in (-0.38, 0.38):
        add_box(bm, (0.05, 0.42, 0.26), (x, -2.22, 0.74))
    add_cyl(bm, 0.035, 0.03, (0.2, -2.22, 0.905))
    obj("BED_STRAPS", bm, "Trim_Black")

    bm = bmesh.new()
    for s in (-1, 1):
        add_helix(bm, (s * 0.62, -1.62, 0.66), (s * 0.70, -1.42, 1.00), 0.045, 6, 0.008)
    obj("BED_COILOVER_SPRINGS", bm, "Caliper_Red")
    bm = bmesh.new()
    for s in (-1, 1):
        add_beam(bm, (s * 0.62, -1.64, 0.62), (s * 0.71, -1.40, 1.04), 0.022, round_=True)
    add_beam(bm, (0, 0.95, 0.30), (0, RA + 0.1, 0.30), 0.04, round_=True)      # driveshaft
    add_cyl(bm, 0.14, 0.28, (0, RA, WHEEL_Z), rot=(0, math.pi / 2, 0))        # diff
    add_beam(bm, (-0.75, RA, WHEEL_Z), (0.75, RA, WHEEL_Z), 0.035, round_=True)  # axles
    add_beam(bm, (-0.55, FA, WHEEL_Z), (0.55, FA, WHEEL_Z), 0.03, round_=True)
    obj("CHASSIS_PARTS", bm, "Engine_Dark")

    # side-exit twin exhaust tips (ahead of the rear wheels)
    bm = bmesh.new()
    for s in (-1, 1):
        for dy in (-0.05, 0.05):
            add_lathe(bm, [(0.035, -0.10), (0.045, -0.10), (0.045, 0.08), (0.035, 0.08)], segs=20,
                      loc=(s * (BODY_X - 0.03), RA + ARCH_R + 0.22 + dy, 0.30))
    obj("EXHAUST_TIPS", bm, "Metal_Polished", smooth=True)


# ================================================================ INTERIOR
def build_interior():
    cockpit = empty("COCKPIT_HR")
    bm = bmesh.new()
    add_box(bm, (1.62, 0.36, 0.20), (0, 0.74, 0.93), bevel=0.04)   # dash
    add_box(bm, (0.26, 0.55, 0.22), (0, 0.30, 0.45), bevel=0.04)   # tunnel / console
    for s in (-1, 1):
        add_box(bm, (0.05, 1.45, 0.55), (s * (BODY_X - 0.08), 0.05, 0.66))  # door cards
        add_box(bm, (0.12, 0.10, 0.12), (s * 0.42, -0.36, 0.40))   # seat mounts
    add_beam(bm, (-0.42, 0.40, 0.98), (-0.42, 0.75, 0.86), 0.03, round_=True)  # steering column
    add_beam(bm, (0, 0.18, 0.55), (0, 0.10, 0.75), 0.012, round_=True)        # shifter
    add_sphere(bm, 0.03, (0, 0.10, 0.77))
    obj("INT_DASH", bm, "Interior_Black", parent=cockpit)

    bm = bmesh.new()
    for s in (-1, 1):
        x = s * 0.42
        add_box(bm, (0.50, 0.50, 0.10), (x, -0.30, 0.52), bevel=0.03)                     # cushion
        add_box(bm, (0.50, 0.12, 0.70), (x, -0.62, 0.88), rot=(-0.20, 0, 0), bevel=0.04)  # back
        for t in (-1, 1):                                                                   # bolsters
            add_box(bm, (0.07, 0.42, 0.14), (x + t * 0.23, -0.30, 0.60), bevel=0.02)
            add_box(bm, (0.07, 0.14, 0.55), (x + t * 0.24, -0.57, 0.86), rot=(-0.20, 0, 0), bevel=0.02)
    obj("INT_SEATS", bm, "Seat_Red", parent=cockpit)

    bm = bmesh.new()
    for t in (-1, 1):   # driver harness
        add_beam(bm, (-0.42 + t * 0.09, -0.56, 1.20), (-0.42 + t * 0.07, -0.20, 0.62), 0.045, 0.006)
    obj("INT_HARNESS", bm, "Strap_Red", parent=cockpit)

    # steering wheel: STEER_HR's local Y axis (-> AC local Z) runs along the column
    tilt = -0.35
    steer = empty("STEER_HR", loc=(-0.42, 0.40, 0.98), rot=(tilt, 0, 0), parent=cockpit)
    bm = bmesh.new()
    ring = [(0.17 + 0.016 * math.cos(a), 0.016 * math.sin(a))
            for a in [2 * math.pi * i / 10 for i in range(10)]]
    add_lathe(bm, ring, segs=40, rot=(0, 0, math.pi / 2))      # rim, axis along local Y
    for a in (0, 2.2, -2.2, math.pi):
        if a == math.pi:
            continue
        add_beam(bm, (0, 0.02, 0), (0.16 * math.cos(a + math.pi / 2), 0.0, 0.16 * math.sin(a + math.pi / 2)),
                 0.03, 0.012)
    add_cyl(bm, 0.05, 0.05, (0, 0.02, 0), rot=(math.pi / 2, 0, 0))
    obj("STEER_WHEEL", bm, "Interior_Black", parent=steer, smooth=True)


# ================================================================ WHEELS
def wheel_meshes(parent, width, outward):
    """Build rim + tyre around the parent's origin, outer face toward +X then flipped for the left."""
    yaw = (0, 0, 0) if outward > 0 else (0, 0, math.pi)
    hw = width / 2

    bm = bmesh.new()
    tread = [(RIM_R - 0.004, -hw + 0.012), (TYRE_R - 0.04, -hw), (TYRE_R - 0.012, -hw + 0.018),
             (TYRE_R, -hw + 0.05), (TYRE_R, hw - 0.05), (TYRE_R - 0.012, hw - 0.018),
             (TYRE_R - 0.04, hw), (RIM_R - 0.004, hw - 0.012)]
    add_lathe(bm, tread, segs=64, rot=yaw)
    obj(f"{parent.name}_TYRE", bm, "Tyre", parent=parent, smooth=True)

    # outer lip + inner barrel (silver)
    bm = bmesh.new()
    lip = [(RIM_R - 0.035, hw - 0.04), (RIM_R + 0.008, hw - 0.04), (RIM_R + 0.008, hw - 0.012),
           (RIM_R - 0.03, hw - 0.012)]
    add_lathe(bm, lip, segs=56, rot=yaw)
    barrel = [(RIM_R - 0.012, -hw + 0.01), (RIM_R + 0.004, -hw + 0.01), (RIM_R + 0.004, hw - 0.04),
              (RIM_R - 0.012, hw - 0.04)]
    add_lathe(bm, barrel, segs=40, rot=yaw)
    for i in range(6):   # lug nuts
        a = 2 * math.pi * i / 6
        p = Euler(yaw).to_matrix() @ Vector((hw - 0.07, 0.05 * math.cos(a), 0.05 * math.sin(a)))
        add_cyl(bm, 0.009, 0.02, tuple(p), rot=(0, math.pi / 2, 0), segs=6)
    obj(f"{parent.name}_RIM_LIP", bm, "Rim_Lip_Silver", parent=parent, smooth=True)

    # red multi-spoke face: 7 double spokes, slightly concave
    bm = bmesh.new()
    face_x = hw - 0.075
    for i in range(14):
        a = 2 * math.pi * (i // 2) / 7 + (0.11 if i % 2 else -0.11)
        a_out = a + (0.06 if i % 2 else -0.06)
        p_in = Vector((face_x - 0.02, 0.07 * math.cos(a), 0.07 * math.sin(a)))
        p_out = Vector((face_x + 0.03, (RIM_R - 0.03) * math.cos(a_out), (RIM_R - 0.03) * math.sin(a_out)))
        R = Euler(yaw).to_matrix()
        add_beam(bm, tuple(R @ p_in), tuple(R @ p_out), 0.022, 0.018)
    add_lathe(bm, [(0.02, face_x - 0.06), (0.085, face_x - 0.06), (0.085, face_x - 0.01), (0.02, face_x - 0.01)],
              segs=32, rot=yaw)                                                         # hub
    add_lathe(bm, [(RIM_R - 0.04, hw - 0.075), (RIM_R - 0.012, hw - 0.075), (RIM_R - 0.012, hw - 0.04),
                   (RIM_R - 0.04, hw - 0.04)], segs=48, rot=yaw)                         # spoke ring
    obj(f"{parent.name}_RIM", bm, "Rim_Red", parent=parent, smooth=True)


def build_wheels():
    for tag, y, track, width in (("LF", FA, TRACK_F, TYRE_W_F), ("RF", FA, TRACK_F, TYRE_W_F),
                                 ("LR", RA, TRACK_R, TYRE_W_R), ("RR", RA, TRACK_R, TYRE_W_R)):
        s = -1 if tag[0] == "L" else 1
        center = (s * track / 2, y, WHEEL_Z)
        w = empty(f"WHEEL_{tag}", loc=center)
        wheel_meshes(w, width, s)

        d = empty(f"DISC_{tag}", loc=center)
        bm = bmesh.new()
        hw = width / 2
        add_lathe(bm, [(0.09, -0.016), (0.19, -0.016), (0.19, 0.016), (0.09, 0.016)], segs=48,
                  loc=(s * (hw - 0.14), 0, 0))
        obj(f"DISC_{tag}_MESH", bm, "Brake_Disc", parent=d, smooth=True)

        sp = empty(f"SUSP_{tag}", loc=center)
        bm = bmesh.new()
        add_box(bm, (0.07, 0.20, 0.08), (s * (hw - 0.14), -0.12, 0.13), rot=(-0.75, 0, 0), bevel=0.015)
        obj(f"SUSP_{tag}_CALIPER", bm, "Caliper_Red", parent=sp)


# ================================================================ BUILD
build_body()
build_front()
build_engine()
build_interior()
build_wheels()

# ---------------------------------------------------------------- export
bpy.context.view_layer.update()
blend_path = os.path.join(OUT, CAR_ID + ".blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

bpy.ops.export_scene.fbx(
    filepath=os.path.join(OUT, CAR_ID + ".fbx"),
    use_selection=False,
    object_types={"MESH", "EMPTY"},
    axis_forward="Z", axis_up="Y",
    apply_unit_scale=True,
    use_mesh_modifiers=True,
    mesh_smooth_type="FACE",
    path_mode="COPY",
    embed_textures=False,
    bake_anim=False,
)
try:
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, CAR_ID + ".glb"), export_format="GLB")
except Exception as exc:  # glTF add-on missing
    print("GLB export skipped:", exc)

tri = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print(f"Objects: {len([o for o in bpy.data.objects if o.type == 'MESH'])} meshes, ~{tri} polygons")


# ---------------------------------------------------------------- preview renders
def render_previews():
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    scene.world = world

    # ground plane (shadow catcher look)
    bm = bmesh.new()
    add_box(bm, (40, 40, 0.01), (0, 0, -0.005))
    g = obj("PREVIEW_GROUND", bm, "Trim_Black")
    g.data.materials[0] = bpy.data.materials.new("PreviewGround")
    g.data.materials[0].diffuse_color = (1, 1, 1, 1)
    try:
        g.is_shadow_catcher = True
    except Exception:
        pass

    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 3.0
    sun.angle = 0.3
    so = bpy.data.objects.new("Sun", sun)
    so.rotation_euler = (0.6, 0.2, 0.8)
    COL.objects.link(so)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    try:
        scene.cycles.use_denoising = True
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = 1280, 800
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"

    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    COL.objects.link(cam)
    scene.camera = cam

    views = {
        "front_quarter": ((-5.6, 6.4, 2.6), (0, 0.2, 0.7), 40),
        "side": ((-10.5, 0.0, 1.0), (0, -0.15, 0.75), 45),
        "rear_quarter": ((5.2, -6.6, 3.6), (0, -0.6, 0.6), 40),
    }
    for name, (pos, target, lens) in views.items():
        cam.location = pos
        d = Vector(target) - Vector(pos)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        cam_data.lens = lens
        scene.render.filepath = os.path.join(OUT, f"preview_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)


if DO_RENDER:
    render_previews()
