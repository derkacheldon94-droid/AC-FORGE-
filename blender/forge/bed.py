"""Rear bed-mounted twin-turbo kit (exhaust exits through both bed sides ahead of the rear wheels),
fuel cell, battery, rear coilovers + shock crossbar."""

import math

import bpy  # noqa: F401
from mathutils import Vector

from . import geo as G
from .dims import BED_FLOOR_Z, BODY_X, EXIT_R, EXIT_Y, EXIT_Z, REAR_Y

TY, TZ = -1.17, 0.98
CX = 0.36


def _spiral(a, R0, dR, r0, dr, turns=0.92, out_len=0.08, n=44):
    """Snail-shell volute around the X axis at axial position a. Returns (bmesh, outlet point, outlet dir)."""
    pts, radii = [], []
    for i in range(n + 1):
        th = turns * G.TAU * i / n
        f = th / G.TAU
        R = R0 + dR * f
        pts.append(Vector((a, TY + R * math.cos(th), TZ + R * math.sin(th))))
        radii.append(r0 + dr * f)
    d = (pts[-1] - pts[-2]).normalized()
    for k in range(1, 5):
        pts.append(pts[n] + d * out_len * k / 4)
        radii.append(radii[n])
    m = len(pts)
    bm = G.sweep(pts, G.circle2d(1.0, 16), scale=lambda t: radii[min(m - 1, round(t * (m - 1)))])
    return bm, pts[-1], d


def turbo(s, P):
    ac, at = s * CX + s * 0.085, s * CX - s * 0.085
    mir = (s, 1, 1)
    # compressor side
    vol, c_out, c_dir = _spiral(ac, 0.085, 0.03, 0.022, 0.03)
    P["alu"].add(vol)
    P["alu"].add(G.lathe([(0.03, -0.035), (0.11, -0.035), (0.115, 0.0), (0.09, 0.035), (0.072, 0.06),
                          (0.072, 0.14), (0.083, 0.14), (0.083, 0.156), (0.062, 0.156), (0.062, 0.06),
                          (0.03, 0.05)], segs=56, uv=False), loc=(ac, TY, TZ), scale=mir)
    for k in range(10):                                   # compressor wheel blades
        a = G.TAU * k / 10
        P["blades"].add(G.box((0.05, 0.003, 0.04)),
                        matrix=G.xf((ac + s * 0.085, TY, TZ), (a, 0, 0)) @ G.xf((0, 0, 0.035), (0, 0.5 * s, 0)))
    P["chrome"].add(G.cyl(0.012, 0.03, segs=6), loc=(ac + s * 0.10, TY, TZ), rot=(0, math.pi / 2, 0))
    # centre cartridge
    P["alu"].add(G.lathe([(0.03, -0.06), (0.05, -0.06), (0.055, -0.03), (0.055, 0.03), (0.05, 0.06), (0.03, 0.06)],
                         segs=32, uv=False), loc=(s * CX, TY, TZ))
    # turbine side
    vol_t, t_in, t_dir = _spiral(at, 0.075, 0.025, 0.02, 0.026, out_len=0.05)
    P["hot"].add(vol_t)
    P["hot"].add(G.lathe([(0.02, -0.03), (0.095, -0.03), (0.10, 0.0), (0.07, 0.04), (0.06, 0.10), (0.072, 0.10),
                          (0.072, 0.115), (0.05, 0.115), (0.02, 0.05)], segs=48, uv=False), loc=(at, TY, TZ),
                 scale=(-s, 1, 1))
    for x in (ac - s * 0.032, at + s * 0.032, at - s * 0.105):
        ring = [(0.075 + 0.006 * math.cos(q), 0.006 * math.sin(q)) for q in [G.TAU * i / 6 for i in range(6)]]
        P["chrome"].add(G.lathe(ring, segs=48, uv=False), loc=(x, TY, TZ))
    # oil feed (braided) + drain
    P["braid"].add(G.tube([(s * CX, TY, TZ + 0.055), (s * CX, TY + 0.05, TZ + 0.12), (s * 0.15, -0.95, 1.0),
                           (s * 0.12, -0.93, BED_FLOOR_Z)], 0.006, segs=8))
    P["rubber"].add(G.tube([(s * CX, TY, TZ - 0.055), (s * CX, TY + 0.02, TZ - 0.18), (s * CX, TY + 0.05, BED_FLOOR_Z)],
                           0.012, segs=10))

    # exhaust feed from below the bed floor into the turbine (comes back from the headers under the cab)
    P["wrap"].add(G.tube([(at + s * 0.01, TY - 0.21, BED_FLOOR_Z - 0.05), (at + s * 0.01, TY - 0.20, BED_FLOOR_Z + 0.1),
                          (at, TY - 0.16, TZ - 0.09), (at, TY - 0.08, TZ - 0.085)], 0.042, segs=16))
    # external wastegate with screamer pipe
    wg = Vector((at + s * 0.01, TY - 0.24, BED_FLOOR_Z + 0.16))
    P["anod"].add(G.cyl(0.04, 0.07, segs=24), loc=wg + Vector((s * 0.06, 0, 0.0)), rot=(0, math.pi / 2, 0))
    P["red"].add(G.cyl(0.042, 0.02, segs=24), loc=wg + Vector((s * 0.105, 0, 0.0)), rot=(0, math.pi / 2, 0))
    P["polish"].add(G.tube([wg + Vector((s * 0.06, 0, -0.03)), wg + Vector((s * 0.14, -0.06, -0.04)),
                            wg + Vector((s * 0.22, -0.12, 0.10)), wg + Vector((s * 0.23, -0.13, 0.30))], 0.022, segs=14))
    P["polish"].add(G.lathe([(0.022, 0.0), (0.026, 0.0), (0.03, 0.03), (0.026, 0.03)], segs=24, uv=False),
                    loc=wg + Vector((s * 0.23, -0.13, 0.30)), rot=(0, -math.pi / 2, 0))

    # downpipe: turbine outlet -> down through the bed floor -> forward -> split into twin exits
    o = Vector((at - s * 0.12, TY, TZ))
    P["wrap"].add(G.tube([o, o + Vector((-s * 0.08, 0.0, -0.02)), Vector((s * 0.12, TY + 0.04, 0.70)),
                          Vector((s * 0.14, TY + 0.10, BED_FLOOR_Z - 0.08)), Vector((s * 0.30, -1.0, EXIT_Z))],
                         0.05, segs=16))
    for y in EXIT_Y:
        P["polish"].add(G.tube([(s * 0.30, -1.0, EXIT_Z), (s * 0.45, y, EXIT_Z), (s * (BODY_X - 0.05), y, EXIT_Z)],
                               EXIT_R - 0.004, segs=20))
        tip = [(EXIT_R - 0.004, -0.06), (EXIT_R, -0.06), (EXIT_R + 0.004, 0.01), (EXIT_R + 0.002, 0.03),
               (EXIT_R - 0.004, 0.03), (EXIT_R - 0.006, -0.02)]
        P["tips"].add(G.lathe(tip, segs=40, uv=False), loc=(s * BODY_X, y, EXIT_Z), scale=(s, 1, 1))
        P["hot_tip"].add(G.lathe([(EXIT_R - 0.007, -0.10), (EXIT_R - 0.005, -0.10), (EXIT_R - 0.005, 0.01),
                                  (EXIT_R - 0.007, 0.01)], segs=32, uv=False), loc=(s * BODY_X, y, EXIT_Z), scale=(s, 1, 1))

    # charge pipe: compressor outlet -> over the turbine -> down into the centre plenum (silver, like the build)
    P["sil"].add(G.cyl(0.064, 0.07, segs=24), matrix=G.xf(c_out + c_dir * 0.03) @ G.look_rot(c_dir))
    c2 = c_out + c_dir * 0.065
    P["silver"].add(G.tube([c2, c2 + c_dir * 0.07, Vector((s * 0.30, -0.98, 1.20)), Vector((s * 0.17, -1.0, 1.14)),
                            Vector((s * 0.13, -1.0, 1.06))], 0.052, segs=20))
    P["sil"].add(G.cyl(0.058, 0.05, segs=24), loc=(s * 0.14, -1.0, 1.08), rot=(0, math.pi / 2, 0))
    # inlet: compressor -> down and back -> red cone filter low by the bed side
    ci = Vector((ac + s * 0.156, TY, TZ))
    P["silver"].add(G.tube([ci, ci + Vector((s * 0.06, 0, 0)), Vector((s * 0.66, TY - 0.10, 0.90)),
                            Vector((s * 0.64, -1.40, 0.78))], 0.07, segs=24))
    from .engine import pleated_cone
    fl = Vector((s * 0.64, -1.42, 0.78))
    d = Vector((s * 0.25, -1.0, -0.05)).normalized()
    P["filter"].add(pleated_cone(0.074, 0.06, 0.17, pleats=30, depth=0.004),
                    matrix=G.xf(fl) @ G.look_rot(d) @ G.xf(rot=(0, -math.pi / 2, 0)))
    # support stand
    for dy in (-0.07, 0.07):
        P["anod"].add(G.tube([(s * CX, TY + dy, BED_FLOOR_Z), (s * CX, TY + dy, TZ - 0.05)], 0.012, segs=8))


def fuel_cell_battery_coilovers(col, M):
    # fuel cell sits low in the open back of the bed, strapped down (like the build)
    yc, zc = REAR_Y + 0.25, 0.55
    cell = G.Part("BED_FUEL_CELL", "Brushed_Alu", smooth=40)
    cell.add(G.box((1.08, 0.40, 0.30), r=0.025), loc=(0, yc, zc))
    cell.build(col, M)
    sm = G.Part("BED_SMALL_HW", "Anodized_Black", smooth=40)
    red = G.Part("BED_SMALL_RED", "Caliper_Red", smooth=40)
    blue = G.Part("BED_SMALL_BLUE", "Anodized_Blue", smooth=40)
    alu = G.Part("BED_SMALL_ALU", "Cast_Alu", smooth=40)
    brass = G.Part("BOLTS_BED_BRASS", "Heat_Gold", smooth=40)
    chrome = G.Part("BOLTS_BED_CHROME", "Chrome", smooth=40)
    braid = G.Part("BED_SMALL_LINES", "Braided", smooth=50, uv_scale=20)
    for x in (-0.33, 0.33):                                         # black straps wrapping the cell
        sm.add(G.box((0.06, 0.41, 0.012), r=0.004), loc=(x, yc, zc + 0.152))
        sm.add(G.box((0.06, 0.012, 0.36), r=0.004), loc=(x, yc - 0.205, zc - 0.02))
        brass.add(G.cyl(0.013, 0.02, segs=6), loc=(x, yc - 0.215, zc - 0.17), rot=(math.pi / 2, 0, 0))
    sm.add(G.cyl(0.075, 0.012, segs=48), loc=(0, yc, zc + 0.156))      # filler flange + cap
    sm.add(G.cyl(0.045, 0.03, segs=32), loc=(0, yc, zc + 0.175))
    for k in range(12):
        a = G.TAU * k / 12
        chrome.add(G.cyl(0.006, 0.01, segs=6), loc=(0.062 * math.cos(a), yc + 0.062 * math.sin(a), zc + 0.165))
    for x, part in ((-0.45, red), (-0.40, blue), (0.40, red), (0.45, blue)):
        part.add(G.cyl(0.013, 0.03, segs=6), loc=(x, yc + 0.1, zc + 0.165))
    braid.add(G.tube([(-0.45, yc + 0.1, zc + 0.18), (-0.50, yc + 0.3, zc + 0.20), (-0.62, -1.0, BED_FLOOR_Z + 0.02),
                      (-0.62, -0.93, BED_FLOOR_Z)], 0.008, segs=8))
    # battery + tray + cut-off switch
    alu.add(G.box((0.29, 0.21, 0.02), r=0.006), loc=(0.72, -2.25, BED_FLOOR_Z + 0.03))
    gb = G.Part("BED_BATTERY", "Gloss_Black", smooth=40)
    gb.add(G.box((0.26, 0.18, 0.19), r=0.012), loc=(0.72, -2.25, BED_FLOOR_Z + 0.135))
    gb.build(col, M)
    red.add(G.cyl(0.012, 0.02, segs=12), loc=(0.64, -2.25, BED_FLOOR_Z + 0.24))
    sm.add(G.cyl(0.012, 0.02, segs=12), loc=(0.80, -2.25, BED_FLOOR_Z + 0.24))
    # centre aluminium A-bracket + diagonal inboard coilovers (pushrod style, like the build)
    bracket = G.fillet_poly([(-0.42, BED_FLOOR_Z + 0.01), (0.42, BED_FLOOR_Z + 0.01), (0.20, 0.80), (-0.20, 0.80)],
                            [0.02, 0.02, 0.03, 0.03], k=4)
    alu.add(G.prism([(x, z) for x, z in bracket], 0.03, axis="Y"), loc=(0, -1.80, 0))
    for s in (-1, 1):
        alu.add(G.prism([(0.0, BED_FLOOR_Z + 0.01), (0.14, BED_FLOOR_Z + 0.01), (0.0, 0.74)], 0.02, axis="Y"),
                loc=(s * 0.10, -1.80, 0), scale=(s, 1, 1))
        b, t = Vector((s * 0.18, -1.80, 0.76)), Vector((s * 0.80, -1.66, 0.97))
        axis = (t - b)
        L = axis.length
        m = G.xf(b) @ G.look_rot(axis)
        rot_l = G.xf(rot=(0, -math.pi / 2, 0))
        alu.add(G.lathe([(0.0, 0.0), (0.032, 0.0), (0.032, L * 0.50), (0.0, L * 0.50)], segs=24), matrix=m @ rot_l)
        sm.add(G.lathe([(0.03, L * 0.22), (0.062, L * 0.22), (0.062, L * 0.25), (0.03, L * 0.25)], segs=32,
                       uv=False), matrix=m @ rot_l)
        sm.add(G.lathe([(0.012, L * 0.90), (0.062, L * 0.90), (0.062, L * 0.93), (0.012, L * 0.93)], segs=32,
                       uv=False), matrix=m @ rot_l)
        chrome.add(G.helix(0.054, L * 0.64, 7.0, 0.0085, steps_per_turn=24), matrix=m @ G.xf((0, 0, L * 0.25)))
        chrome.add(G.cyl(0.012, L * 0.45, segs=12), matrix=m @ G.xf((0, 0, L * 0.72)))
        sm.add(G.cyl(0.024, 0.15, segs=16), matrix=m @ G.xf((0.055, 0, 0.14)))                # reservoir
        red.add(G.cyl(0.026, 0.02, segs=16), matrix=m @ G.xf((0.055, 0, 0.22)))
        for p in (b, t):
            brass.add(G.cyl(0.016, 0.06, segs=12), loc=p, rot=(math.pi / 2, 0, 0))
        alu.add(G.box((0.03, 0.12, 0.12), r=0.01), loc=(s * 0.87, -1.66, 0.97))              # outer mount
    # tie-down hooks
    for x in (-0.89, 0.89):
        for y in (-1.0, -2.40):
            chrome.add(G.lathe([(0.018 + 0.005 * math.cos(q), 0.005 * math.sin(q)) for q in
                                [G.TAU * i / 6 for i in range(6)]], segs=20, uv=False), loc=(x, y, 0.95),
                       rot=(0, 0, math.pi / 2))
    for p in (sm, red, blue, alu, brass, chrome, braid):
        p.build(col, M)


def plenum(col, M):
    box = G.Part("TURBO_PLENUM", "Brushed_Alu", smooth=40)
    box.add(G.box((0.26, 0.16, 0.34), r=0.035), loc=(0, -1.0, 1.0))
    box.add(G.box((0.30, 0.18, 0.03), r=0.01), loc=(0, -1.0, 1.18))
    box.add(G.tube([(0, -1.0, 0.83), (0, -0.98, BED_FLOOR_Z - 0.02)], 0.06, segs=24))
    box.build(col, M)
    tag = G.Part("TURBO_SMALL_PLATE", "Heat_Gold", smooth=0)
    tag.add(G.box((0.08, 0.004, 0.04), r=0.004), loc=(0, -1.082, 1.08))
    tag.build(col, M)
    hoses = G.Part("TURBO_SMALL_VAC", "Rubber", smooth=50)
    for s in (-1, 1):
        hoses.add(G.tube([(s * 0.05, -1.0, 1.195), (s * 0.06, -0.97, 1.30), (s * 0.12, -0.93, 1.32),
                          (s * 0.20, -0.92, 1.20)], 0.012, segs=8))
    hoses.build(col, M)


def build(col, M):
    P = {
        "alu": G.Part("TURBO_COMPRESSORS", "Cast_Alu", smooth=45),
        "blades": G.Part("TURBO_SMALL_BLADES", "Brushed_Alu", smooth=0),
        "hot": G.Part("TURBO_TURBINES", "Turbo_Hot", smooth=45),
        "chrome": G.Part("TURBO_SMALL_CHROME", "Chrome", smooth=45),
        "braid": G.Part("TURBO_SMALL_OIL_FEED", "Braided", smooth=50, uv_scale=20),
        "rubber": G.Part("TURBO_SMALL_DRAINS", "Rubber", smooth=50),
        "wrap": G.Part("TURBO_HOT_PIPES", "Heat_Wrap", smooth=50, uv_scale=12),
        "anod": G.Part("TURBO_WASTEGATES", "Anodized_Black", smooth=45),
        "red": G.Part("TURBO_SMALL_RED", "Caliper_Red", smooth=45),
        "polish": G.Part("TURBO_PIPES", "Metal_Polished", smooth=50),
        "silver": G.Part("TURBO_CHARGE_PIPES", "Brushed_Alu", smooth=50),
        "sil": G.Part("TURBO_SMALL_COUPLERS", "Silicone_Red", smooth=50),
        "filter": G.Part("TURBO_FILTERS", "Filter_Red", smooth=50),
        "tips": G.Part("EXHAUST_TIPS", "Metal_Polished", smooth=50),
        "hot_tip": G.Part("EXHAUST_TIPS_INNER", "Turbo_Hot", smooth=50),
    }
    for s in (-1, 1):
        turbo(s, P)
    for p in P.values():
        p.build(col, M)
    shield = G.Part("TURBO_HEAT_SHIELD", "Heat_Gold", smooth=0, uv_scale=4)
    shield.add(G.box((1.30, 0.55, 0.004), r=0.002), loc=(0, TY - 0.05, BED_FLOOR_Z + 0.035))
    shield.build(col, M)
    fuel_cell_battery_coilovers(col, M)
    plenum(col, M)
