"""Body shell, cab greenhouse, flares, glass, seals, liners."""

import math

import bpy  # noqa: F401
import bmesh
from mathutils import Vector

from . import geo as G
from .dims import (EXIT_R, EXIT_Y, EXIT_Z, ARCH_R, ARCH_Z, BED_FLOOR_Z, BED_FRONT_Y, BELT_Z, BODY_X, CAB_BACK_Y, CAB_FLOOR_Z,
                   CREASE_Z, FA, FIREWALL_Y, FRONT_Y, RA, REAR_Y, ROCKER_Z, ROOF_Z, BAY_FLOOR_Z)


def _section(y):
    """Cross-section of the lower body at station y (closed polygon in XZ)."""
    hw, zt, zb = BODY_X, BELT_Z, ROCKER_Z
    for d, R, Rv in ((FRONT_Y - y, 0.07, 0.05), (y - REAR_Y, 0.05, 0.03)):
        if d < R:
            hw -= R - math.sqrt(max(0.0, R * R - (R - d) ** 2))
        if d < Rv:
            zt -= Rv - math.sqrt(max(0.0, Rv * Rv - (Rv - d) ** 2))
    if y > FA + ARCH_R:                                   # front valance sits a bit higher
        zb += 0.04 * min(1.0, (y - FA - ARCH_R) / 0.2)
    corners = [(-hw + 0.03, zb), (hw - 0.03, zb), (hw, zb + 0.08), (hw, CREASE_Z),
               (hw - 0.022, zt), (-(hw - 0.022), zt), (-hw, CREASE_Z), (-hw, zb + 0.08)]
    radii = [0.02, 0.02, 0.03, 0.012, 0.03, 0.03, 0.012, 0.03]
    pts = G.fillet_poly(corners, radii, k=5, edge_div=1)
    return [(x, y, z) for x, z in pts]


def _stations():
    ys = []
    # dense at both ends for the rounded plan-view corners
    for i in range(10):
        ys.append(REAR_Y + 0.06 * (1 - math.cos(math.pi / 2 * i / 9)))
    y = REAR_Y + 0.07
    while y < FRONT_Y - 0.08:
        ys.append(y)
        y += 0.035
    for i in range(10):
        ys.append(FRONT_Y - 0.08 + 0.08 * math.sin(math.pi / 2 * i / 9))
    return ys


def lower_shell(col, M):
    bm = G.loft([_section(y) for y in _stations()])
    part = G.Part("BODY_SHELL", "Paint_Black", smooth=40)
    part.add(bm)
    o = part.build(col, M)

    cutters = []

    def cbox(size, loc, r=0.0, rot=(0, 0, 0)):
        c = G.box(size, r=r)
        bmesh.ops.transform(c, matrix=G.xf(loc, rot), verts=c.verts)
        cutters.append(c)

    def ccyl(r, depth, loc, rot, segs=64):
        c = G.cyl(r, depth, segs=segs)
        bmesh.ops.transform(c, matrix=G.xf(loc, rot), verts=c.verts)
        cutters.append(c)

    # engine bay, cab tub, bed tub
    cbox((1.80, FRONT_Y - 0.06 - FIREWALL_Y - 0.03, 1.6), (0, (FRONT_Y - 0.06 + FIREWALL_Y + 0.03) / 2, BAY_FLOOR_Z + 0.8),
         r=0.03)
    cbox((1.86, FIREWALL_Y - CAB_BACK_Y, 1.6), (0, (FIREWALL_Y + CAB_BACK_Y) / 2, CAB_FLOOR_Z + 0.8), r=0.03)
    # open bed (no tailgate, like the build) + a low well at the back for the fuel cell
    cbox((1.84, BED_FRONT_Y - (REAR_Y - 0.3), 1.6), (0, (BED_FRONT_Y + REAR_Y - 0.3) / 2, BED_FLOOR_Z + 0.8), r=0.03)
    cbox((1.20, 0.75, 0.70), (0, REAR_Y + 0.2, 0.36 + 0.35), r=0.02)
    # cab / bed separation gap
    cbox((2.4, 0.018, 1.6), (0, (CAB_BACK_Y + BED_FRONT_Y) / 2, 0.33 + 0.8))
    # wheel arches
    for y in (FA, RA):
        ccyl(ARCH_R, 2.6, (0, y, ARCH_Z), (0, math.pi / 2, 0))
    # panel grooves (doors, tailgate) - shallow slabs on the outer skin
    g = 0.005
    for s in (-1, 1):
        xo = s * (BODY_X - 0.006 + 0.11)
        for y in (0.895, -0.70):
            cbox((0.22, g, BELT_Z - 0.30), (xo, y, (BELT_Z + 0.30) / 2 + 0.01))
        cbox((0.22, 0.895 + 0.70, g), (xo, (0.895 - 0.70) / 2, 0.36))
        # door handle recess + fuel door
        cbox((0.22, 0.17, 0.055), (s * (BODY_X - 0.012 + 0.11), -0.52, 0.905), r=0.015)
    ccyl(0.078, 0.22, (-(BODY_X - 0.004 + 0.11), -0.98, 0.80), (0, math.pi / 2, 0), segs=48)
    ccyl(0.072, 0.30, (-(BODY_X + 0.14), -0.98, 0.80), (0, math.pi / 2, 0), segs=48)
    for s in (-1, 1):             # exhaust exits through the bed side, ahead of the rear wheels
        for y in EXIT_Y:
            ccyl(EXIT_R + 0.006, 0.40, (s * (BODY_X - 0.10), y, EXIT_Z), (0, math.pi / 2, 0), segs=32)

    G.boolean(o, cutters)
    G.bevel_mod(o, 0.004, segments=2, angle=50)
    G.smooth_by_angle(o, 40)
    G.weighted_normals(o)
    return o


def greenhouse(col, M):
    """Cab upper: rounded shell with window openings."""
    zb = BELT_Z - 0.025
    prof = G.fillet_poly([(0.975, zb), (0.355, ROOF_Z), (-0.79, ROOF_Z), (-0.835, zb)],
                         [0.02, 0.11, 0.06, 0.0], k=8, edge_div=2)
    bm = G.prism(prof, 2 * 0.955, axis="X")
    # tumblehome + roof crown
    for v in bm.verts:
        h = (v.co.z - zb) / (ROOF_Z - zb)
        v.co.x *= 1 - 0.085 * max(0.0, h)
        if v.co.z > ROOF_Z - 0.02:
            v.co.z += 0.018 * (1 - (v.co.x / 0.9) ** 2)
    # round the outline edges (everything on the two side caps except the belt edge)
    edges = []
    for e in bm.edges:
        a, b = e.verts
        if abs(abs(a.co.x) - abs(b.co.x)) < 1e-4 and abs(a.co.x) > 0.5:      # edge on a side cap outline
            if a.co.z < zb + 1e-4 and b.co.z < zb + 1e-4:
                continue
            if len(e.link_faces) == 2:
                edges.append(e)
    bmesh.ops.bevel(bm, geom=edges, offset=0.055, segments=5, profile=0.5, affect="EDGES", clamp_overlap=True)
    # remove the floor faces so it can be shelled
    floor = [f for f in bm.faces if all(v.co.z < zb + 1e-4 for v in f.verts)]
    bmesh.ops.delete(bm, geom=floor, context="FACES")
    part = G.Part("BODY_CAB_TOP", "Paint_Black", smooth=40)
    part.add(bm)
    o = part.build(col, M)
    G.solidify_mod(o, 0.03, offset=-1.0)

    cutters = []
    ws_a, ws_b = Vector((0, 0.975, zb)), Vector((0, 0.355, ROOF_Z))
    d = ws_b - ws_a
    L = d.length
    up = d.normalized()
    nrm = Vector((1, 0, 0)).cross(up)
    c = G.box((1.42, L * 0.80, 0.4), r=0.05)
    mid = ws_a + d * 0.5
    bmesh.ops.transform(c, matrix=G.basis(mid, (1, 0, 0), up, nrm), verts=c.verts)
    cutters.append(c)
    side = G.fillet_poly([(0.83, BELT_Z + 0.035), (0.34, ROOF_Z - 0.075), (-0.36, ROOF_Z - 0.075),
                          (-0.36, BELT_Z + 0.035)], [0.02, 0.05, 0.05, 0.03], k=6)
    cutters.append(G.prism(side, 2.6, axis="X"))
    c = G.box((1.26, 0.6, 0.38), r=0.045)
    bmesh.ops.transform(c, matrix=G.xf((0, -0.82, 1.305)), verts=c.verts)
    cutters.append(c)
    G.boolean(o, cutters)
    G.smooth_by_angle(o, 40)
    G.weighted_normals(o)

    # glass + rubber seals
    glass = G.Part("GLASS_WINDOWS", "Glass", smooth=0)
    seals = G.Part("BODY_SEALS", "Rubber", smooth=60)
    inset = 0.018
    gm = G.basis(ws_a + d * 0.5 - nrm * inset, (1, 0, 0), up, nrm)
    glass.add(G.box((1.46, L * 0.83, 0.006), r=0.002), matrix=gm)
    seal_path = [Vector(p) for p in G.fillet_poly([(-0.72, -L * 0.40), (0.72, -L * 0.40), (0.72, L * 0.40),
                                                   (-0.72, L * 0.40)], 0.05, k=6, edge_div=3)]
    seals.add(G.sweep([gm @ Vector((p.x, p.y, 0.0)) for p in seal_path], G.circle2d(0.008, 6), closed=True))
    bm_back = G.basis((0, -0.79 - 0.03 + inset, 1.305), (-1, 0, 0), (0, 0, 1), (0, -1, 0))
    glass.add(G.box((1.28, 0.38, 0.006), r=0.002), matrix=bm_back)
    seal_path = [Vector(p) for p in G.fillet_poly([(-0.63, -0.19), (0.63, -0.19), (0.63, 0.19), (-0.63, 0.19)],
                                                  0.045, k=6, edge_div=3)]
    seals.add(G.sweep([bm_back @ Vector((p.x, p.y, 0.0)) for p in seal_path], G.circle2d(0.008, 6), closed=True))
    # window channel seals along the beltline
    for s in (-1, 1):
        seals.add(G.box((0.03, 1.15, 0.012), r=0.004), loc=(s * 0.945, 0.24, BELT_Z + 0.004))
    # roof drip rails
    for s in (-1, 1):
        x = s * (0.955 * (1 - 0.085) + 0.004)
        pts = [(x, 0.37, ROOF_Z - 0.03), (x, 0.0, ROOF_Z - 0.028), (x, -0.70, ROOF_Z - 0.03), (x, -0.80, ROOF_Z - 0.06)]
        seals.add(G.tube(pts, 0.006, segs=6))
    glass.build(col, M)
    seals.build(col, M)
    return o


def flares(col, M):
    part = G.Part("BODY_FLARES", "Carbon", smooth=50, uv_scale=8)
    rivets = G.Part("BOLTS_FLARE_RIVETS", "Chrome", smooth=40)
    prof = [(-0.008, -0.03), (-0.008, 0.0), (0.0, 0.065), (0.012, 0.082), (0.035, 0.09), (0.065, 0.08),
            (0.09, 0.05), (0.105, 0.012), (0.11, -0.03)]
    for cy, k in ((FA, 1.0), (RA, 1.12)):
        R = ARCH_R + 0.004
        a0 = math.asin((ROCKER_Z + 0.03 - ARCH_Z) / R)
        n = 64
        for s in (-1, 1):
            secs = []
            for i in range(n + 1):
                a = (math.pi - a0) + (2 * a0 - math.pi) * i / n
                t = abs(math.cos(a))
                taper = max(0.05, 1.0 - 0.75 * t ** 6)
                rd = Vector((0, math.cos(a), math.sin(a)))
                base = Vector((s * (BODY_X - 0.01), cy, ARCH_Z)) + rd * R
                secs.append([tuple(base + rd * (dr * k * taper) + Vector((s * dx * k * taper, 0, 0)))
                             for dr, dx in prof])
            part.add(G.loft(secs))
            for i in range(2, n - 1, 3):                       # rivets along the outer edge
                a = (math.pi - a0) + (2 * a0 - math.pi) * i / n
                rd = Vector((0, math.cos(a), math.sin(a)))
                t = abs(math.cos(a))
                taper = max(0.05, 1.0 - 0.75 * t ** 6)
                p = Vector((s * (BODY_X - 0.01), cy, ARCH_Z)) + rd * (R + 0.085 * k * taper) + \
                    Vector((s * 0.062 * k * taper, 0, 0))
                rivets.add(G.sphere(0.0055, 8), loc=p)
    rivets.build(col, M)
    return part.build(col, M)


def liners(col, M):
    """Wheel-house liners (also the wheel tubs you see inside the bed)."""
    part = G.Part("BODY_WHEELHOUSES", "Bed_Liner", smooth=50, uv_scale=3)
    for cy in (FA, RA):
        for s in (-1, 1):
            x0, x1 = s * 0.50, s * (BODY_X - 0.012)
            lo, hi = min(x0, x1), max(x0, x1)
            prof = [(ARCH_R + 0.002, lo), (ARCH_R + 0.002, hi), (ARCH_R + 0.012, hi), (ARCH_R + 0.012, lo)]
            a_extra = math.asin(max(-1, min(1, (ARCH_Z - ROCKER_Z) / ARCH_R)))
            bm = G.lathe(prof, segs=48, arc=math.pi + 2 * a_extra, uv=False)
            part.add(bm, loc=(0, cy, ARCH_Z), rot=(-a_extra, 0, 0))
    return part.build(col, M)


def bed_and_floors(col, M):
    liner = G.Part("BED_FLOOR_RIBS", "Bed_Liner", smooth=50, uv_scale=3)
    L = (BED_FRONT_Y - 0.03) - (REAR_Y + 0.60)
    yc = ((BED_FRONT_Y - 0.03) + (REAR_Y + 0.60)) / 2
    liner.add(G.box((1.80, L, 0.012)), loc=(0, yc, BED_FLOOR_Z + 0.006))
    for i in range(11):
        x = -0.80 + i * 0.16
        liner.add(G.box((0.045, L, 0.022), r=0.008), loc=(x, yc, BED_FLOOR_Z + 0.02))
    liner.build(col, M)
    carpet = G.Part("INT_CARPET", "Carpet", smooth=0, uv_scale=4)
    carpet.add(G.box((1.84, FIREWALL_Y - CAB_BACK_Y - 0.02, 0.01)), loc=(0, (FIREWALL_Y + CAB_BACK_Y) / 2, CAB_FLOOR_Z + 0.005))
    carpet.add(G.box((0.30, 0.95, 0.20), r=0.06), loc=(0, 0.35, CAB_FLOOR_Z + 0.09))  # transmission tunnel
    carpet.build(col, M)


def build(col, M):
    lower_shell(col, M)
    greenhouse(col, M)
    flares(col, M)
    liners(col, M)
    bed_and_floors(col, M)
