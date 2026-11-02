"""Front engine bay: iron V8 long-block, red valve covers, coil packs, intake + twin throttle bodies,
fuel rails, accessory drive with belt, radiator + fans, headers, strut brace, booster, breathers."""

import math

import bpy  # noqa: F401
from mathutils import Euler, Matrix, Vector

from . import geo as G

YC = 1.45          # engine centre (front-back)
BANK = 0.62        # head tilt (radians) each side


def _bank_m(s, loc):
    return G.xf(loc, (0, -s * BANK, 0))


def pleated_cone(r0, r1, length, pleats=36, depth=0.006):
    prof = [(0.001, 0.0), (r0, 0.0), (r0, 0.004)] + \
           [(r0 + (r1 - r0) * t, 0.004 + (length - 0.02) * t) for t in [i / 8 for i in range(9)]] + \
           [(r1, length - 0.012), (r1 * 0.6, length), (0.001, length)]

    def mod(i, k, r):
        if 3 <= k <= 11:
            return r + depth * (1 if i % 2 else -1)
        return r
    return G.lathe(prof, segs=pleats * 2, closed=False, uv=True, modulate=mod)


def long_block(col, M):
    blk = G.Part("ENGINE_BLOCK", "Engine_Dark", smooth=40)
    blk.add(G.box((0.40, 0.62, 0.28), r=0.03), loc=(0, YC, 0.66))
    blk.add(G.box((0.34, 0.52, 0.11), r=0.035), loc=(0, YC, 0.49))                 # oil pan
    for s in (-1, 1):
        blk.add(G.box((0.17, 0.64, 0.11), r=0.02), matrix=_bank_m(s, (s * 0.205, YC, 0.835)))
        for i in range(4):                                                          # exhaust port bosses
            y = YC - 0.235 + i * 0.155
            blk.add(G.box((0.05, 0.07, 0.06), r=0.012), loc=(s * 0.29, y, 0.79))
    blk.add(G.box((0.32, 0.05, 0.30), r=0.03), loc=(0, YC + 0.335, 0.70))         # timing cover
    blk.build(col, M)
    bell = G.Part("ENGINE_BELLHOUSING", "Cast_Alu", smooth=40)
    bell.add(G.lathe([(0.04, 0.0), (0.23, 0.0), (0.24, 0.02), (0.19, 0.17), (0.04, 0.17)], segs=48, uv=False),
             loc=(0, YC - 0.31, 0.62), rot=(0, 0, math.pi / 2), scale=(-1, 1, 1))
    bell.build(col, M)


def valve_covers(col, M):
    vc = G.Part("ENGINE_VALVE_COVERS", "Valve_Red", smooth=40)
    bolts = G.Part("BOLTS_VALVE_COVERS", "Chrome", smooth=40)
    txt = G.Part("BADGE_VALVE_COVERS", "Chrome", smooth=30)
    caps = G.Part("ENGINE_SMALL_CAPS", "Anodized_Black", smooth=40)
    filt = G.Part("ENGINE_SMALL_BREATHERS", "Filter_Red", smooth=40)
    for s in (-1, 1):
        m = _bank_m(s, (s * 0.255, YC, 0.905))
        vc.add(G.box((0.16, 0.60, 0.065), r=0.026), matrix=m)
        for k in range(-2, 3):                                                      # cooling ribs
            vc.add(G.box((0.010, 0.44, 0.016), r=0.004), matrix=m @ G.xf((k * 0.026, 0.06, 0.036)))
        for j in range(6):
            for side in (-1, 1):
                bolts.add(G.cyl(0.006, 0.012, segs=6), matrix=m @ G.xf((side * 0.07, -0.26 + j * 0.104, 0.03)))
        txt.add(G.text("CHEVROLET", size=0.024, depth=0.003), matrix=m @ G.xf((0, -0.10, 0.0335), (0, 0, s * math.pi / 2)))
        # oil cap / breather filter on top of each cover
        caps.add(G.cyl(0.026, 0.02, segs=24), matrix=m @ G.xf((0.0, 0.22, 0.045)))
        filt.add(pleated_cone(0.024, 0.032, 0.06, pleats=18, depth=0.003), matrix=m @ G.xf((0.0, 0.22, 0.055), (0, -math.pi / 2, 0)))
    for p in (vc, bolts, txt, caps, filt):
        p.build(col, M)


def coils_and_wires(col, M):
    coils = G.Part("ENGINE_COILS", "Anodized_Black", smooth=40)
    wires = G.Part("ENGINE_WIRES", "Rubber", smooth=50)
    for s in (-1, 1):
        for i in range(4):
            y = YC - 0.235 + i * 0.155
            m = _bank_m(s, (s * 0.255, y, 0.905))
            coils.add(G.box((0.055, 0.065, 0.085), r=0.012), matrix=m @ G.xf((s * 0.115, 0, 0.02)))
            coils.add(G.box((0.03, 0.03, 0.03), r=0.006), matrix=m @ G.xf((s * 0.115, 0.045, 0.04)))
            wires.add(G.tube([m @ Vector((s * 0.12, 0.045, 0.055)), m @ Vector((s * 0.10, 0.06, 0.08)),
                              m @ Vector((s * 0.085, 0.07, 0.07))], 0.005, segs=6))
        loom = [_bank_m(s, (s * 0.255, YC - 0.29 + t * 0.6, 0.905)) @ Vector((s * 0.085, 0.0, 0.075))
                for t in (0, 0.33, 0.66, 1.0)]
        wires.add(G.tube(loom + [Vector((s * 0.40, 1.02, 0.93)), Vector((s * 0.62, 1.0, 0.86))], 0.011, segs=8))
    coils.build(col, M)
    wires.build(col, M)


def intake(col, M):
    alu = G.Part("ENGINE_INTAKE", "Cast_Alu", smooth=40)
    alu.add(G.box((0.25, 0.54, 0.10), r=0.045), loc=(0, YC, 1.015))
    for s in (-1, 1):
        for i in range(4):
            y = YC - 0.235 + i * 0.155
            alu.add(G.tube([(s * 0.09, y, 1.0), (s * 0.15, y, 0.995), (s * 0.19, y, 0.955), (s * 0.20, y, 0.93)],
                           0.021, segs=12, per_seg=4))
    alu.add(G.box((0.22, 0.10, 0.08), r=0.03), loc=(0, YC + 0.27, 1.04))               # throttle-body adapter
    alu.build(col, M)
    tb = G.Part("ENGINE_THROTTLE_BODIES", "Anodized_Black", smooth=40)
    stacks = G.Part("ENGINE_SMALL_STACKS", "Chrome", smooth=40)
    blades = G.Part("ENGINE_SMALL_TB_BLADES", "Brushed_Alu", smooth=0)
    for s in (-1, 1):
        rot = (math.pi / 2 - 0.35, 0, 0)
        loc = Vector((s * 0.068, YC + 0.30, 1.10))
        m = G.xf(loc, rot)
        tb.add(G.lathe([(0.058, -0.06), (0.066, -0.06), (0.066, 0.05), (0.058, 0.05)], segs=40, uv=False),
               matrix=m @ G.xf(rot=(0, -math.pi / 2, 0)))
        tb.add(G.box((0.03, 0.05, 0.05), r=0.01), matrix=m @ G.xf((s * 0.07, 0, -0.01)))
        stacks.add(G.lathe([(0.062, 0.05), (0.066, 0.05), (0.072, 0.075), (0.085, 0.092), (0.092, 0.095),
                            (0.090, 0.099), (0.078, 0.094), (0.064, 0.072), (0.058, 0.05)], segs=40, uv=False),
                   matrix=m @ G.xf(rot=(0, -math.pi / 2, 0)))
        blades.add(G.cyl(0.056, 0.002, segs=32), matrix=m @ G.xf((0, 0, 0.0), (0.5, 0, 0)))
    for p in (tb, blades):
        p.build(col, M)
    rails = G.Part("ENGINE_FUEL_RAILS", "Brushed_Alu", smooth=40)
    fittings = G.Part("ENGINE_SMALL_FITTINGS", "Caliper_Red", smooth=40)
    braided = G.Part("ENGINE_SMALL_FUEL_LINES", "Braided", smooth=50, uv_scale=20)
    for s in (-1, 1):
        rails.add(G.box((0.022, 0.62, 0.022), r=0.005), loc=(s * 0.145, YC, 0.985))
        for i in range(4):
            y = YC - 0.235 + i * 0.155
            rails.add(G.cyl(0.008, 0.04, segs=10), loc=(s * 0.16, y, 0.96), rot=(0, s * 0.5, 0))
        for y in (YC - 0.32, YC + 0.32):
            fittings.add(G.cyl(0.013, 0.025, segs=6), loc=(s * 0.145, y, 0.985), rot=(math.pi / 2, 0, 0))
        braided.add(G.tube([(s * 0.145, YC - 0.335, 0.985), (s * 0.15, YC - 0.42, 0.97), (s * 0.30, 1.0, 0.82),
                            (s * 0.55, 0.98, 0.60)], 0.008, segs=8))
    for p in (rails, fittings, braided):
        p.build(col, M)


def accessory_drive(col, M):
    yb = YC + 0.39
    pulleys = [((0.0, 0.58), 0.105), ((0.0, 0.79), 0.072), ((0.22, 0.90), 0.045), ((-0.21, 0.88), 0.055),
               ((0.12, 0.69), 0.035), ((-0.13, 0.70), 0.035)]
    pul = G.Part("ENGINE_PULLEYS", "Brushed_Alu", smooth=40)
    for (x, z), r in pulleys:
        prof = [(0.01, -0.025), (r, -0.025), (r, -0.02), (r - 0.006, -0.012), (r - 0.006, 0.012), (r, 0.02),
                (r, 0.025), (0.01, 0.025)]
        pul.add(G.lathe(prof, segs=48, uv=False), loc=(x, yb, z), rot=(0, 0, math.pi / 2))
    pul.build(col, M)
    # serpentine belt: convex hull around all pulleys
    pts = []
    for (x, z), r in pulleys:
        for k in range(48):
            a = G.TAU * k / 48
            pts.append((x + (r - 0.004) * math.cos(a), z + (r - 0.004) * math.sin(a)))
    hull = _hull(pts)
    belt = G.Part("ENGINE_BELT", "Rubber", smooth=40)
    belt.add(G.sweep([(x, yb, z) for x, z in hull], G.rrect2d(0.004, 0.022, 0.0015, k=2), closed=True,
                     up_hint=(0, 1, 0)))
    belt.build(col, M)
    acc = G.Part("ENGINE_ACCESSORIES", "Cast_Alu", smooth=40)
    acc.add(G.lathe([(0.02, -0.06), (0.075, -0.06), (0.08, -0.04), (0.08, 0.05), (0.06, 0.07), (0.02, 0.07)],
                    segs=40, uv=False), loc=(0.22, yb - 0.09, 0.90), rot=(0, 0, math.pi / 2))     # alternator
    for k in range(16):
        a = G.TAU * k / 16
        acc.add(G.box((0.004, 0.07, 0.012)), loc=(0.22 + 0.081 * math.cos(a), yb - 0.09, 0.90 + 0.081 * math.sin(a)),
                rot=(0, -a, 0))
    acc.add(G.lathe([(0.02, -0.05), (0.06, -0.05), (0.065, 0.04), (0.02, 0.05)], segs=32, uv=False),
            loc=(-0.21, yb - 0.08, 0.88), rot=(0, 0, math.pi / 2))                                   # PS pump
    acc.add(G.box((0.20, 0.06, 0.16), r=0.03), loc=(0, yb - 0.04, 0.79))                            # water pump
    acc.build(col, M)


def _hull(pts):
    pts = sorted(set(pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    # resample evenly so the swept belt has clean segments
    out = []
    for a, b in zip(hull, hull[1:] + hull[:1]):
        d = math.dist(a, b)
        n = max(1, int(d / 0.01))
        for i in range(n):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out


def cooling(col, M):
    core = G.Part("ENGINE_RADIATOR", "Intercooler_Fins", smooth=0, uv_scale=12)
    core.add(G.box((1.30, 0.045, 0.40)), loc=(0, 2.10, 0.74))
    core.build(col, M)
    tanks = G.Part("ENGINE_RADIATOR_TANKS", "Cast_Alu", smooth=40)
    for s in (-1, 1):
        tanks.add(G.box((0.07, 0.07, 0.44), r=0.02), loc=(s * 0.685, 2.10, 0.74))
    tanks.add(G.box((0.12, 0.08, 0.16), r=0.02), loc=(-0.58, 1.95, 0.88))               # overflow tank
    tanks.build(col, M)
    shroud = G.Part("ENGINE_FAN_SHROUD", "Anodized_Black", smooth=40)
    blades = G.Part("ENGINE_FAN_BLADES", "Engine_Dark", smooth=30)
    shroud.add(G.box((1.24, 0.03, 0.40), r=0.02), loc=(0, 2.06, 0.74))
    for x in (-0.32, 0.32):
        shroud.add(G.lathe([(0.17, -0.03), (0.185, -0.03), (0.185, 0.03), (0.17, 0.03)], segs=48, uv=False),
                   loc=(x, 2.03, 0.74), rot=(0, 0, math.pi / 2))
        shroud.add(G.cyl(0.045, 0.06, segs=24), loc=(x, 2.0, 0.74), rot=(math.pi / 2, 0, 0))
        for k in range(7):
            a = G.TAU * k / 7
            blades.add(G.box((0.07, 0.006, 0.12), r=0.002),
                       matrix=G.xf((x, 2.03, 0.74), (0, a, 0)) @ G.xf((0, 0, 0.10), (0, 0, 0.35)))
    shroud.build(col, M)
    blades.build(col, M)
    hoses = G.Part("ENGINE_HOSES", "Silicone_Red", smooth=50)
    hoses.add(G.tube([(0.62, 2.07, 0.90), (0.45, 1.96, 0.92), (0.15, YC + 0.38, 0.86), (0.05, YC + 0.38, 0.84)],
                     0.022, segs=14))
    hoses.add(G.tube([(-0.62, 2.07, 0.58), (-0.40, 1.95, 0.55), (-0.10, YC + 0.38, 0.66)], 0.024, segs=14))
    hoses.build(col, M)


def headers(col, M):
    hdr = G.Part("ENGINE_HEADERS", "Heat_Wrap", smooth=50, uv_scale=12)
    coll = G.Part("ENGINE_COLLECTORS", "Turbo_Hot", smooth=50)
    for s in (-1, 1):
        for i in range(4):
            y = YC - 0.235 + i * 0.155
            path = [(s * 0.31, y, 0.79), (s * 0.40, y, 0.78), (s * 0.47, y - 0.03, 0.66),
                    (s * 0.46, y * 0.5 + 1.08 * 0.5 - 0.1, 0.52), (s * 0.40, 1.10, 0.44)]
            hdr.add(G.tube(path, 0.019, segs=10, per_seg=5))
        coll.add(G.lathe([(0.045, 0.0), (0.06, 0.0), (0.045, 0.12), (0.04, 0.12)], segs=24, closed=True, uv=False),
                 loc=(s * 0.40, 1.10, 0.44), rot=(0, 0, -math.pi / 2))
    hdr.build(col, M)
    coll.build(col, M)


def bay_misc(col, M):
    brace = G.Part("ENGINE_STRUT_BRACE", "Caliper_Red", smooth=50)
    brace.add(G.tube([(-0.80, 1.55, 1.02), (-0.4, 1.20, 1.10), (0.4, 1.20, 1.10), (0.80, 1.55, 1.02)], 0.018,
                     segs=14, per_seg=6))
    brace.build(col, M)
    plates = G.Part("ENGINE_SMALL_BRACE_PLATES", "Brushed_Alu", smooth=40)
    for s in (-1, 1):
        plates.add(G.cyl(0.075, 0.012, segs=32), loc=(s * 0.80, 1.55, 1.015))
        for k in range(3):
            a = G.TAU * k / 3
            plates.add(G.cyl(0.008, 0.02, segs=6), loc=(s * 0.80 + 0.05 * math.cos(a), 1.55 + 0.05 * math.sin(a), 1.025))
    plates.build(col, M)
    bk = G.Part("ENGINE_BOOSTER", "Engine_Dark", smooth=40)
    bk.add(G.lathe([(0.02, 0.0), (0.13, 0.0), (0.135, 0.03), (0.135, 0.08), (0.12, 0.11), (0.02, 0.11)], segs=48,
                   uv=False), loc=(-0.58, 0.96, 0.86), rot=(0, 0, math.pi / 2))
    bk.add(G.box((0.20, 0.15, 0.10), r=0.02), loc=(0.62, 1.10, 0.74))                    # ECU / fuse box
    bk.build(col, M)
    mc = G.Part("ENGINE_SMALL_MASTER_CYL", "Cast_Alu", smooth=40)
    mc.add(G.cyl(0.03, 0.18, segs=20), loc=(-0.58, 1.15, 0.88), rot=(math.pi / 2, 0, 0))
    mc.add(G.box((0.10, 0.10, 0.06), r=0.015), loc=(-0.58, 1.14, 0.94))
    mc.build(col, M)
    lid = G.Part("ENGINE_SMALL_MC_CAP", "Anodized_Black", smooth=40)
    lid.add(G.cyl(0.03, 0.015, segs=20), loc=(-0.58, 1.14, 0.975))
    lid.build(col, M)


def carbon_intake(col, M):
    """Carbon twin-oval airbox over the throttle bodies, carbon intake tube with red bands and a red
    cone filter by the radiator (front reference photo), carbon inner-fender covers."""
    c = G.Part("ENGINE_CARBON_AIRBOX", "Carbon", smooth=40, uv_scale=10)
    dark = G.Part("ENGINE_AIRBOX_THROATS", "Gloss_Black", smooth=40)
    yb, zb = YC + 0.30, 1.15
    c.add(G.box((0.34, 0.26, 0.11), r=0.05), loc=(0, yb - 0.02, zb))
    for s in (-1, 1):
        x = s * 0.078
        secs = []
        for i in range(9):
            t = i / 8
            cy, cz = yb + 0.05 + 0.10 * t, zb + 0.01 + 0.05 * t
            rx, rz = 0.070 + 0.006 * t, 0.042 + 0.004 * t
            secs.append([(x + rx * math.cos(a), cy, cz + rz * math.sin(a)) for a in [G.TAU * k / 32 for k in range(32)]])
        c.add(G.loft(secs))
        ring = [(x + 0.078 * math.cos(a), yb + 0.152, zb + 0.06 + 0.047 * math.sin(a)) for a in
                [G.TAU * k / 40 for k in range(40)]]
        c.add(G.sweep(ring, G.circle2d(0.008, 8), closed=True))
        dark.add(G.cyl(1.0, 0.004, segs=40), matrix=G.xf((x, yb + 0.13, zb + 0.06), (math.pi / 2, 0, 0)) @
                 G.xf(scale=(0.068, 0.040, 1.0)))
    c.add(G.box((0.012, 0.16, 0.10), r=0.004), loc=(0, yb + 0.07, zb + 0.04))
    # carbon intake tube from the airbox to a cone filter beside the radiator
    path = [(0.16, yb - 0.02, zb), (0.30, yb + 0.05, zb - 0.02), (0.42, 1.92, 1.0), (0.50, 2.0, 0.97)]
    c.add(G.tube(path, 0.045, segs=20))
    for s_ in (-1, 1):                                              # carbon inner-fender covers
        c.add(G.box((0.15, 0.40, 0.035), r=0.012), loc=(s_ * 0.80, 1.93, 0.99), rot=(0, s_ * 0.12, 0))
        c.add(G.box((0.15, 0.04, 0.12), r=0.012), loc=(s_ * 0.80, 2.12, 0.93))
    c.build(col, M)
    dark.build(col, M)
    bands = G.Part("ENGINE_SMALL_RED_BANDS", "Silicone_Red", smooth=40)
    for p0, p1 in ((Vector(path[0]), Vector(path[1])), (Vector(path[2]), Vector(path[3]))):
        d = (p1 - p0).normalized()
        bands.add(G.cyl(0.05, 0.03, segs=24), matrix=G.xf(p0.lerp(p1, 0.5)) @ G.look_rot(d))
    bands.build(col, M)
    filt = G.Part("ENGINE_FILTER", "Filter_Red", smooth=50)
    d = Vector((0.6, 0.6, -0.3)).normalized()
    filt.add(pleated_cone(0.05, 0.04, 0.14, pleats=28, depth=0.004),
             matrix=G.xf(path[-1]) @ G.look_rot(d) @ G.xf(rot=(0, -math.pi / 2, 0)))
    filt.build(col, M)
    brass = G.Part("ENGINE_SMALL_BRASS_CAPS", "Heat_Gold", smooth=40)
    brass.add(G.cyl(0.03, 0.02, segs=24), loc=(0.40, 2.10, 0.965))
    brass.add(G.cyl(0.028, 0.02, segs=24), loc=(-0.58, 1.95, 0.97))
    brass.build(col, M)


def build(col, M):
    carbon_intake(col, M)
    long_block(col, M)
    valve_covers(col, M)
    coils_and_wires(col, M)
    intake(col, M)
    accessory_drive(col, M)
    cooling(col, M)
    headers(col, M)
    bay_misc(col, M)
