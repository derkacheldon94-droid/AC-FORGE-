"""Body shell (GMT400 regular cab, short bed): curved lofted panels, cab greenhouse, wide-body flares,
glass, seals, bed rails and liners.

Curvature (all real-world GMT400 traits): barrel-shaped door/bed sides, a shoulder crease, cab tumblehome,
a crowned roof, rounded plan-view corners. Sections carry ~100 points each and stations are 32 mm apart,
so the shell is genuinely high-poly before the boolean cuts and bevels."""

import math

import bpy  # noqa: F401
import bmesh
from mathutils import Vector

from . import geo as G
from .dims import (ARCH_R, ARCH_Z, BAY_FLOOR_Z, BED_FLOOR_Z, BED_FRONT_Y, BELT_Z, BODY_X, CAB_BACK_Y,
                   CAB_FLOOR_Z, CREASE_Z, DOOR_FRONT_Y, DOOR_REAR_Y, EXIT_R, EXIT_Y, EXIT_Z, FA, FIREWALL_Y,
                   FRONT_Y, RA, REAR_Y, ROCKER_Z, ROOF_Z)


def _sm(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _section(y):
    """Cross-section of the lower body at station y: list of (x, y, z)."""
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
    pts = G.fillet_poly(corners, radii, k=5, edge_div=5)

    # barrel curvature along the whole length, fading toward both ends; fender crown over the wheels
    w = min(_sm((FRONT_Y - y) / 0.32), _sm((y - REAR_Y) / 0.32))
    out = []
    for x, z in pts:
        if z <= CREASE_Z:
            u = max(0.0, min(1.0, (z - zb) / (CREASE_Z - zb)))
            dx = 0.016 * w * math.sin(math.pi * u) ** 1.4          # door / bedside barrel bulge
            dx -= 0.004 * w * math.exp(-((z - 0.50) / 0.05) ** 2)   # soft stamped rocker line
        else:
            v = (z - CREASE_Z) / max(1e-6, zt - CREASE_Z)
            dx = -0.030 * w * v ** 1.6                              # tumblehome above the shoulder
        k = 1.0 + dx / BODY_X
        zz = z
        if z >= zt - 1e-6:                                           # top deck crown over the fenders
            zz += 0.010 * math.exp(-((y - FA) / 0.35) ** 2) * (1 - (x / BODY_X) ** 2)
        out.append((x * k, y, zz))
    return out


def _stations():
    ys, n = [], 12
    for i in range(n):
        ys.append(REAR_Y + 0.08 * (1 - math.cos(math.pi / 2 * i / (n - 1))))
    y = REAR_Y + 0.09
    while y < FRONT_Y - 0.09:
        ys.append(y)
        y += 0.042
    for i in range(n):
        ys.append(FRONT_Y - 0.08 + 0.08 * math.sin(math.pi / 2 * i / (n - 1)))
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

    # engine bay, cab tub, open bed tub (no tailgate) + a low well at the back for the fuel cell
    cbox((1.80, FRONT_Y - 0.06 - FIREWALL_Y - 0.03, 1.6), (0, (FRONT_Y - 0.06 + FIREWALL_Y + 0.03) / 2, BAY_FLOOR_Z + 0.8),
         r=0.03)
    cbox((1.86, FIREWALL_Y - CAB_BACK_Y, 1.6), (0, (FIREWALL_Y + CAB_BACK_Y) / 2, CAB_FLOOR_Z + 0.8), r=0.03)
    cbox((1.84, BED_FRONT_Y - (REAR_Y - 0.3), 1.6), (0, (BED_FRONT_Y + REAR_Y - 0.3) / 2, BED_FLOOR_Z + 0.8), r=0.03)
    cbox((1.20, 0.75, 0.70), (0, REAR_Y + 0.2, 0.36 + 0.35), r=0.02)
    # cab / bed separation gap
    cbox((2.4, 0.018, 1.6), (0, (CAB_BACK_Y + BED_FRONT_Y) / 2, 0.33 + 0.8))
    # wheel arches
    for y in (FA, RA):
        ccyl(ARCH_R, 2.6, (0, y, ARCH_Z), (0, math.pi / 2, 0))
    # panel shut lines: doors (front + rear + sill), handle recess
    g = 0.005
    for s in (-1, 1):
        xo = s * (BODY_X - 0.006 + 0.11)
        for y in (DOOR_FRONT_Y, DOOR_REAR_Y):
            cbox((0.22, g, BELT_Z - 0.30), (xo, y, (BELT_Z + 0.30) / 2 + 0.01))
        cbox((0.22, DOOR_FRONT_Y - DOOR_REAR_Y, g), (xo, (DOOR_FRONT_Y + DOOR_REAR_Y) / 2, 0.36))
        cbox((0.22, 0.17, 0.055), (s * (BODY_X - 0.012 + 0.11), -0.10, 0.905), r=0.015)
        # stake pockets in the bed rails
        for y in (BED_FRONT_Y - 0.14, REAR_Y + 0.16):
            cbox((0.040, 0.085, 0.034), (s * (BODY_X - 0.045), y, BELT_Z), r=0.008)
        # exhaust exits through the bed side, ahead of the rear wheels
        for y in EXIT_Y:
            ccyl(EXIT_R + 0.006, 0.40, (s * (BODY_X - 0.10), y, EXIT_Z), (0, math.pi / 2, 0), segs=48)
    # fuel door on the left bed side (just behind the cab)
    ccyl(0.078, 0.22, (-(BODY_X - 0.004 + 0.11), -0.70, 0.84), (0, math.pi / 2, 0), segs=48)
    ccyl(0.072, 0.30, (-(BODY_X + 0.14), -0.70, 0.84), (0, math.pi / 2, 0), segs=48)

    G.boolean(o, cutters)
    G.bevel_mod(o, 0.004, segments=2, angle=50)
    G.smooth_by_angle(o, 40)
    G.weighted_normals(o)
    return o


def greenhouse(col, M):
    """Cab upper: rounded shell with window openings."""
    zb = BELT_Z - 0.025
    back = CAB_BACK_Y
    prof = G.fillet_poly([(0.975, zb), (0.355, ROOF_Z), (back + 0.04, ROOF_Z), (back, zb)],
                         [0.02, 0.11, 0.06, 0.0], k=10, edge_div=3)
    bm = G.prism(prof, 2 * 0.955, axis="X")
    # tumblehome + roof crown
    for v in bm.verts:
        h = (v.co.z - zb) / (ROOF_Z - zb)
        v.co.x *= 1 - 0.085 * max(0.0, h)
        if v.co.z > ROOF_Z - 0.02:
            v.co.z += 0.018 * (1 - (v.co.x / 0.9) ** 2)
    edges = []
    for e in bm.edges:
        a, b = e.verts
        if abs(abs(a.co.x) - abs(b.co.x)) < 1e-4 and abs(a.co.x) > 0.5:
            if a.co.z < zb + 1e-4 and b.co.z < zb + 1e-4:
                continue
            if len(e.link_faces) == 2:
                edges.append(e)
    bmesh.ops.bevel(bm, geom=edges, offset=0.055, segments=6, profile=0.5, affect="EDGES", clamp_overlap=True)
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
    # door glass: A-pillar to just ahead of the rear shut line
    side = G.fillet_poly([(0.83, BELT_Z + 0.035), (0.34, ROOF_Z - 0.075), (DOOR_REAR_Y + 0.07, ROOF_Z - 0.075),
                          (DOOR_REAR_Y + 0.07, BELT_Z + 0.035)], [0.02, 0.05, 0.05, 0.03], k=6)
    cutters.append(G.prism(side, 2.6, axis="X"))
    c = G.box((1.26, 0.30, 0.38), r=0.045)
    bmesh.ops.transform(c, matrix=G.xf((0, back + 0.0, 1.305)), verts=c.verts)
    cutters.append(c)
    G.boolean(o, cutters)
    G.smooth_by_angle(o, 40)
    G.weighted_normals(o)

    glass = G.Part("GLASS_WINDOWS", "Glass", smooth=0)
    seals = G.Part("BODY_SEALS", "Rubber", smooth=60)
    inset = 0.018
    gm = G.basis(ws_a + d * 0.5 - nrm * inset, (1, 0, 0), up, nrm)
    glass.add(G.box((1.46, L * 0.83, 0.006), r=0.002), matrix=gm)
    seal_path = [Vector(p) for p in G.fillet_poly([(-0.72, -L * 0.40), (0.72, -L * 0.40), (0.72, L * 0.40),
                                                   (-0.72, L * 0.40)], 0.05, k=6, edge_div=3)]
    seals.add(G.sweep([gm @ Vector((p.x, p.y, 0.0)) for p in seal_path], G.circle2d(0.008, 6), closed=True))
    by = back + 0.03
    bm_back = G.basis((0, by, 1.305), (-1, 0, 0), (0, 0, 1), (0, -1, 0))
    glass.add(G.box((1.28, 0.38, 0.006), r=0.002), matrix=bm_back)
    seal_path = [Vector(p) for p in G.fillet_poly([(-0.63, -0.19), (0.63, -0.19), (0.63, 0.19), (-0.63, 0.19)],
                                                  0.045, k=6, edge_div=3)]
    seals.add(G.sweep([bm_back @ Vector((p.x, p.y, 0.0)) for p in seal_path], G.circle2d(0.008, 6), closed=True))
    # door glass + beltline sweep seals + roof drip rails
    for s in (-1, 1):
        seals.add(G.box((0.03, DOOR_FRONT_Y - DOOR_REAR_Y, 0.012), r=0.004),
                  loc=(s * 0.945, (DOOR_FRONT_Y + DOOR_REAR_Y) / 2, BELT_Z + 0.004))
        dg = G.fillet_poly([(0.83 - 0.02, BELT_Z + 0.045), (0.34 - 0.01, ROOF_Z - 0.085),
                            (DOOR_REAR_Y + 0.08, ROOF_Z - 0.085), (DOOR_REAR_Y + 0.08, BELT_Z + 0.045)],
                           [0.02, 0.05, 0.05, 0.03], k=6)
        glass.add(G.prism(dg, 0.006, axis="X"), loc=(s * 0.905, 0, 0))
        x = s * (0.955 * (1 - 0.085) + 0.004)
        pts = [(x, 0.37, ROOF_Z - 0.03), (x, 0.0, ROOF_Z - 0.028), (x, back + 0.05, ROOF_Z - 0.03),
               (x, back + 0.0, ROOF_Z - 0.06)]
        seals.add(G.tube(pts, 0.006, segs=6))
    glass.build(col, M)
    seals.build(col, M)
    return o


def flares(col, M):
    """Riveted bolt-on carbon over-fenders: stepped lip, ~110 mm of extra width per side."""
    part = G.Part("BODY_FLARES", "Carbon", smooth=50, uv_scale=8)
    bolts = G.Part("BOLTS_FLARE_HARDWARE", "Chrome", smooth=40)
    seal = G.Part("BODY_FLARE_SEAL", "Rubber", smooth=60)
    # (radial offset, outward offset): bolt-on lip with a raised outer face and a step down to the body
    prof = [(-0.010, -0.03), (-0.010, 0.0), (-0.004, 0.070), (0.004, 0.105), (0.016, 0.118), (0.040, 0.122),
            (0.062, 0.122), (0.075, 0.118), (0.084, 0.098), (0.098, 0.096), (0.110, 0.084), (0.122, 0.050),
            (0.130, 0.012), (0.134, -0.03)]
    for cy, k in ((FA, 1.0), (RA, 1.10)):
        R = ARCH_R + 0.004
        a0 = math.asin((ROCKER_Z + 0.03 - ARCH_Z) / R)
        n = 96
        for s in (-1, 1):
            secs, seal_pts = [], []
            for i in range(n + 1):
                a = (math.pi - a0) + (2 * a0 - math.pi) * i / n
                t = abs(math.cos(a))
                taper = max(0.08, 1.0 - 0.50 * t ** 6)
                rd = Vector((0, math.cos(a), math.sin(a)))
                base = Vector((s * (BODY_X - 0.01), cy, ARCH_Z)) + rd * R
                secs.append([tuple(base + rd * (dr * k * taper) + Vector((s * dx * k * taper, 0, 0)))
                             for dr, dx in prof])
                seal_pts.append(tuple(base + rd * (0.138 * k * taper) + Vector((s * 0.004, 0, 0))))
                if i % 6 == 3 and 0.06 < taper:
                    n_out = (Vector((s, 0, 0)) + rd * 0.35).normalized()
                    for dr, dx in ((0.050, 0.122), (0.104, 0.092)):
                        p = base + rd * (dr * k * taper) + Vector((s * dx * k * taper, 0, 0))
                        bolts.add(G.bolt(0.0065, 0.007), matrix=G.xf(p) @ G.look_rot(n_out))
                        bolts.add(G.washer(0.0095, 0.002), matrix=G.xf(p - n_out * 0.0015) @ G.look_rot(n_out))
            part.add(G.loft(secs))
            seal.add(G.sweep(seal_pts, G.circle2d(0.0035, 6)))
    bolts.build(col, M)
    seal.build(col, M)
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
            bm = G.lathe(prof, segs=64, arc=math.pi + 2 * a_extra, uv=False)
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

    # rounded bed rail caps (painted) + front bed wall cap
    rails = G.Part("BED_RAIL_CAPS", "Paint_Black", smooth=50)
    for s in (-1, 1):
        x = s * (BODY_X - 0.047)
        rails.add(G.sweep([(x, BED_FRONT_Y - 0.005, BELT_Z + 0.007), (x, REAR_Y + 0.045, BELT_Z + 0.002)],
                          G.rrect2d(0.016, 0.082, 0.007, k=4), up_hint=(0, 0, 1)))
    rails.add(G.box((1.84, 0.075, 0.018), r=0.007), loc=(0, BED_FRONT_Y + 0.045, BELT_Z - 0.04))
    rails.build(col, M)


def hood(col, M):
    """GMT400 hood (wireframe drawings): crowned, rolls off at the front, two faint character lines,
    with a rounded cut-out the carbon airbox and throttle bodies stand up through."""
    y0, y1 = FIREWALL_Y + 0.038, FRONT_Y - 0.062          # inside the engine-bay opening, ~4 mm shut gaps
    hx, nx, ny = 0.895, 36, 48
    secs = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        f = (y - y0) / (y1 - y0)
        drop = 0.018 * f ** 2
        top, bot = [], []
        for i in range(nx + 1):
            x = -hx + 2 * hx * i / nx
            z = BELT_Z + 0.004 + 0.030 * (1 - (x / hx) ** 2) + 0.004 * math.exp(-((abs(x) - 0.45) / 0.05) ** 2) - drop
            top.append((x, y, z))
            bot.append((x, y, z - 0.022))
        secs.append(top + bot[::-1])
    part = G.Part("BODY_HOOD", "Paint_Black", smooth=40)
    part.add(G.loft(secs))
    o = part.build(col, M)
    cut = G.box((0.80, 0.50, 0.30), r=0.07)
    bmesh.ops.transform(cut, matrix=G.xf((0, 1.75, BELT_Z + 0.06)), verts=cut.verts)
    G.boolean(o, [cut])
    G.bevel_mod(o, 0.003, segments=2, angle=50)
    G.smooth_by_angle(o, 40)
    G.weighted_normals(o)

    trim = G.Part("BODY_HOOD_TRIM", "Brushed_Alu", smooth=50)
    path = [Vector((x, y, BELT_Z + 0.004 + 0.030 * (1 - (x / hx) ** 2) - 0.018 * ((y - y0) / (y1 - y0)) ** 2 + 0.002))
            for x, y in G.fillet_poly([(-0.40, 1.50), (0.40, 1.50), (0.40, 2.00), (-0.40, 2.00)], 0.07, k=8, edge_div=6)]
    trim.add(G.sweep(path, G.rrect2d(0.010, 0.016, 0.004, k=2), closed=True, up_hint=(0, 0, 1)))
    trim.build(col, M)
    pins = G.Part("DETAIL_HOOD_PINS", "Chrome", smooth=50)
    for s in (-1, 1):
        x, y = s * 0.62, 2.04
        z = BELT_Z + 0.004 + 0.030 * (1 - (x / hx) ** 2) - 0.018 * ((y - y0) / (y1 - y0)) ** 2
        pins.add(G.cyl(0.022, 0.006, segs=24), loc=(x, y, z + 0.002))
        pins.add(G.lathe([(0.010 + 0.003 * math.cos(q), 0.003 * math.sin(q)) for q in [G.TAU * k / 6 for k in range(6)]],
                         segs=16, uv=False), loc=(x + 0.03, y, z + 0.006), rot=(0, 0, 0))
    pins.build(col, M)
    return o


def build(col, M):
    lower_shell(col, M)
    hood(col, M)
    greenhouse(col, M)
    flares(col, M)
    liners(col, M)
    bed_and_floors(col, M)
