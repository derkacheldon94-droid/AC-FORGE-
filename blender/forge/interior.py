"""Interior (COCKPIT_HR): red buckets + 5-point harnesses, roll cage, dash with gauges, steering wheel
(STEER_HR), pedals, shifter, hydraulic handbrake, door cards, mirror, extinguisher."""

import math

import bpy
from mathutils import Vector

from . import geo as G
from .dims import CAB_FLOOR_Z, DRIVER_X

SEAT_Y, SEAT_Z = -0.34, 0.47


def _empty(name, col, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.15
    col.objects.link(e)
    e.location, e.rotation_euler = loc, rot
    if parent is not None:
        e.parent = parent
    return e


def seats(cp, col, M):
    red = G.Part("INT_SEATS", "Seat_Red", parent=cp, smooth=45, uv_scale=3)
    slots = G.Part("INT_SEAT_SLOTS", "Gloss_Black", parent=cp, smooth=40)
    mounts = G.Part("INT_SEAT_MOUNTS", "Anodized_Black", parent=cp, smooth=40)
    for x in (DRIVER_X, -DRIVER_X):
        base = G.xf((x, SEAT_Y, SEAT_Z))
        red.add(G.box((0.40, 0.46, 0.08), r=0.035), matrix=base @ G.xf((0, 0.05, 0.0)))
        red.add(G.box((0.36, 0.08, 0.06), r=0.03), matrix=base @ G.xf((0, 0.27, 0.03)))
        for s in (-1, 1):
            red.add(G.box((0.075, 0.46, 0.15), r=0.035), matrix=base @ G.xf((s * 0.235, 0.05, 0.04), (0, s * 0.12, 0)))
        back = base @ G.xf((0, -0.20, 0.02), (0.24, 0, 0))
        red.add(G.box((0.44, 0.075, 0.74), r=0.035), matrix=back @ G.xf((0, -0.03, 0.37)))
        for s in (-1, 1):
            red.add(G.box((0.085, 0.22, 0.52), r=0.04), matrix=back @ G.xf((s * 0.25, 0.06, 0.30), (0, 0, -s * 0.25)))
            red.add(G.box((0.075, 0.15, 0.20), r=0.035), matrix=back @ G.xf((s * 0.19, 0.05, 0.66), (0, 0, -s * 0.35)))
            slots.add(G.box((0.05, 0.02, 0.085), r=0.012), matrix=back @ G.xf((s * 0.085, 0.01, 0.57)))
            slots.add(G.box((0.03, 0.02, 0.07), r=0.01), matrix=back @ G.xf((s * 0.19, 0.04, 0.12)))
            mounts.add(G.box((0.02, 0.36, 0.12), r=0.008), matrix=base @ G.xf((s * 0.25, -0.02, -0.07)))
            mounts.add(G.box((0.03, 0.46, 0.02), r=0.006), loc=(x + s * 0.16, SEAT_Y + 0.03, CAB_FLOOR_Z + 0.02))
        slots.add(G.box((0.06, 0.02, 0.05), r=0.01), matrix=base @ G.xf((0, 0.29, 0.03)))
    for p in (red, slots, mounts):
        p.build(col, M)


def harnesses(cp, col, M):
    strap = G.Part("INT_HARNESS", "Strap_Red", parent=cp, smooth=40, uv_scale=10)
    hw = G.Part("INT_HARNESS_HW", "Chrome", parent=cp, smooth=40)
    flat = G.rrect2d(0.05, 0.004, 0.0015, k=2)
    for x in (DRIVER_X, -DRIVER_X):
        lock = Vector((x, SEAT_Y + 0.18, SEAT_Z + 0.16))
        for s in (-1, 1):
            path = [(x + s * 0.10, -0.79, 1.08), (x + s * 0.09, -0.62, 1.04), (x + s * 0.085, -0.52, 1.0),
                    (x + s * 0.07, -0.38, 0.86), (x + s * 0.03, lock.y - 0.03, lock.z + 0.04)]
            strap.add(G.sweep(G.spline(path, 6), flat, up_hint=(1, 0, 0)))
            lap = [(x + s * 0.21, SEAT_Y - 0.05, SEAT_Z + 0.10), (x + s * 0.17, SEAT_Y + 0.08, SEAT_Z + 0.16),
                   (x + s * 0.05, lock.y - 0.01, lock.z)]
            strap.add(G.sweep(G.spline(lap, 6), flat, up_hint=(0, 0, 1)))
            hw.add(G.box((0.06, 0.012, 0.03), r=0.004), loc=(x + s * 0.075, -0.42, 0.90), rot=(0.7, 0, 0))
        sub = [(x, SEAT_Y + 0.26, SEAT_Z + 0.06), (x, SEAT_Y + 0.22, SEAT_Z + 0.10), (x, lock.y, lock.z - 0.03)]
        strap.add(G.sweep(G.spline(sub, 6), flat, up_hint=(1, 0, 0)))
        hw.add(G.lathe([(0.0, -0.008), (0.042, -0.008), (0.045, 0.0), (0.04, 0.010), (0.0, 0.012)], segs=32, uv=False),
               loc=lock + Vector((0, 0.01, 0)), rot=(0, 0, math.pi / 2))
    strap.build(col, M)
    hw.build(col, M)


def cage(cp, col, M):
    c = G.Part("INT_CAGE", "Gloss_Black", parent=cp, smooth=50)
    r = 0.02
    hoop = G.fillet_open([(-0.84, -0.79, CAB_FLOOR_Z), (-0.84, -0.79, 1.42), (-0.70, -0.79, 1.51),
                          (0.70, -0.79, 1.51), (0.84, -0.79, 1.42), (0.84, -0.79, CAB_FLOOR_Z)], 0.12, k=8)
    c.add(G.sweep(hoop, G.circle2d(r, 12)))
    c.add(G.tube([(-0.84, -0.79, 1.08), (0.84, -0.79, 1.08)], r, segs=12, smooth=False))       # harness bar
    c.add(G.tube([(-0.80, -0.79, 1.45), (0.84, -0.79, 0.60)], r * 0.9, segs=12, smooth=False))  # diagonal
    for s in (-1, 1):
        a = G.fillet_open([(s * 0.76, -0.79, 1.50), (s * 0.76, 0.33, 1.50), (s * 0.84, 0.84, 1.07),
                           (s * 0.86, 0.86, CAB_FLOOR_Z)], 0.10, k=8)
        c.add(G.sweep(a, G.circle2d(r, 12)))
        c.add(G.tube([(s * 0.86, 0.80, 0.62), (s * 0.84, -0.77, 0.62)], r * 0.9, segs=12, smooth=False))  # door bar
    plates = G.Part("INT_CAGE_PLATES", "Brushed_Alu", parent=cp, smooth=30)
    for x, y in ((-0.84, -0.79), (0.84, -0.79), (-0.86, 0.86), (0.86, 0.86)):
        plates.add(G.box((0.10, 0.10, 0.006), r=0.01), loc=(x, y, CAB_FLOOR_Z + 0.008))
    c.build(col, M)
    plates.build(col, M)


def dash(cp, col, M):
    d = G.Part("INT_DASH", "Interior_Black", parent=cp, smooth=40)
    prof = G.fillet_poly([(0.93, 0.70), (0.93, 1.015), (0.86, 1.045), (0.66, 1.06), (0.57, 1.0), (0.59, 0.86),
                          (0.70, 0.70)], [0.0, 0.02, 0.03, 0.04, 0.03, 0.04, 0.02], k=5)
    d.add(G.prism(prof, 1.84, axis="X"))
    d.add(G.box((0.40, 0.14, 0.09), r=0.035), loc=(DRIVER_X, 0.64, 1.085))               # gauge hood
    d.add(G.box((0.30, 0.14, 0.26), r=0.03), loc=(0, 0.66, 0.84))                       # centre stack
    d.add(G.box((0.26, 0.60, 0.14), r=0.04), loc=(0, 0.25, CAB_FLOOR_Z + 0.14))          # console
    for s in (-1, 1):                                                                   # door cards
        d.add(G.box((0.035, 1.40, 0.58), r=0.015), loc=(s * 0.905, 0.03, 0.70))
        d.add(G.box((0.07, 0.40, 0.05), r=0.02), loc=(s * 0.875, -0.05, 0.80))
    d.add(G.box((1.72, 1.12, 0.012), r=0.004), loc=(0, -0.24, 1.548))                    # headliner
    for s in (-1, 1):
        d.add(G.box((0.36, 0.17, 0.018), r=0.008), loc=(s * 0.42, 0.28, 1.53), rot=(0.25, 0, 0))   # visors
    d.add(G.tube([(DRIVER_X, 0.47, 0.97), (DRIVER_X, 0.74, 0.86)], 0.03, segs=16, smooth=False))  # column
    d.add(G.box((0.11, 0.12, 0.09), r=0.03), loc=(DRIVER_X, 0.56, 0.93), rot=(-0.35, 0, 0))       # shroud
    d.build(col, M)

    gauges = [("Gauge_Tach", (DRIVER_X + 0.08, 0.578, 1.025), 0.058), ("Gauge_Speed", (DRIVER_X - 0.08, 0.578, 1.025), 0.058)]
    pod_n = Vector((0.45, -1.0, -0.1)).normalized()
    for k, z in enumerate((1.16, 1.09)):
        gauges.append(("Gauge_Boost", (-0.74 + 0.03 * k, 0.78 - 0.04 * k, z), 0.032))
    bez = G.Part("INT_GAUGE_BEZELS", "Chrome", parent=cp, smooth=40)
    needles = G.Part("INT_GAUGE_NEEDLES", "Caliper_Red", parent=cp, smooth=0)
    pod = G.Part("INT_GAUGE_POD", "Interior_Black", parent=cp, smooth=40)
    faces = {}
    for i, (mat, c, r) in enumerate(gauges):
        c = Vector(c)
        n = Vector((0, -1, 0)) if r > 0.04 else pod_n
        right = Vector((0, 0, 1)).cross(n).normalized()
        up = n.cross(right).normalized()
        m = G.basis(c, right, up, n)
        face = G.cyl(r, 0.004, segs=48)
        G.planar_uv(face, (0, 0, 0), (1, 0, 0), (0, 1, 0), 2 * r, 2 * r)
        faces.setdefault(mat, G.Part(f"INT_GAUGE_FACE_{mat}", mat, parent=cp, smooth=0)).add(face, matrix=m)
        ring = [(r + 0.004 + 0.004 * math.cos(q), 0.004 * math.sin(q)) for q in [G.TAU * j / 6 for j in range(6)]]
        bez.add(G.lathe(ring, segs=48, uv=False), matrix=m @ G.xf(rot=(0, -math.pi / 2, 0)))
        needles.add(G.box((r * 0.8, 0.004, 0.003)), matrix=m @ G.xf((0.0, 0.0, 0.004), (0, 0, 2.3)) @ G.xf((r * 0.35, 0, 0)))
        if r < 0.04:
            pod.add(G.cyl(r + 0.012, 0.05, segs=32), matrix=m @ G.xf((0, 0, -0.025)))
    for p in (bez, needles, pod, *faces.values()):
        p.build(col, M)

    sw = G.Part("INT_SWITCH_PANEL", "Carbon", parent=cp, smooth=0, uv_scale=10)
    sw.add(G.box((0.26, 0.01, 0.16), r=0.01), loc=(0, 0.585, 0.85))
    sw.build(col, M)
    tog = G.Part("INT_SWITCHES", "Chrome", parent=cp, smooth=40)
    guard = G.Part("INT_SWITCH_GUARDS", "Caliper_Red", parent=cp, smooth=40)
    for i in range(5):
        x = -0.10 + i * 0.05
        tog.add(G.cyl(0.004, 0.03, segs=8), loc=(x, 0.57, 0.88), rot=(math.pi / 2 - 0.4, 0, 0))
        guard.add(G.box((0.03, 0.03, 0.012), r=0.004), loc=(x, 0.57, 0.82), rot=(0.3, 0, 0))
    for s in (-1, 1):
        tog.add(G.lathe([(0.035, 0.0), (0.042, 0.0), (0.042, 0.012), (0.035, 0.012)], segs=32, uv=False),
                loc=(s * 0.78, 0.585, 0.97), rot=(0, 0, -math.pi / 2))
    tog.build(col, M)
    guard.build(col, M)


def controls(cp, col, M):
    alu = G.Part("INT_PEDALS", "Brushed_Alu", parent=cp, smooth=30)
    for dx in (-0.13, 0.0, 0.11):
        x = DRIVER_X + dx
        alu.add(G.box((0.02, 0.02, 0.22), r=0.006), loc=(x, 0.80, 0.56), rot=(-0.3, 0, 0))
        alu.add(G.box((0.075 if dx else 0.07, 0.015, 0.09), r=0.008), loc=(x, 0.77, 0.45), rot=(-0.35, 0, 0))
    alu.add(G.cyl(0.03, 0.12, segs=20), loc=(-0.06, 0.02, 0.62), rot=(-0.2, 0, 0))                 # handbrake cyl
    alu.build(col, M)
    red = G.Part("INT_HANDBRAKE", "Caliper_Red", parent=cp, smooth=40)
    red.add(G.tube([(-0.06, 0.03, 0.64), (-0.06, 0.08, 0.85), (-0.06, 0.12, 0.95)], 0.012, segs=12))
    red.add(G.box((0.03, 0.04, 0.10), r=0.012), loc=(-0.06, 0.125, 0.98))
    red.add(G.cyl(0.04, 0.32, segs=24), loc=(0.42, 0.55, CAB_FLOOR_Z + 0.06), rot=(0, math.pi / 2, 0))  # extinguisher
    red.build(col, M)
    sh = G.Part("INT_SHIFTER", "Chrome", parent=cp, smooth=40)
    sh.add(G.tube([(-0.02, 0.22, 0.50), (-0.03, 0.20, 0.68), (-0.05, 0.18, 0.76)], 0.007, segs=10))
    sh.add(G.cyl(0.006, 0.36, segs=8), loc=(0.42, 0.55, CAB_FLOOR_Z + 0.10), rot=(0, math.pi / 2, 0))
    sh.build(col, M)
    knob = G.Part("INT_SHIFT_KNOB", "Gloss_Black", parent=cp, smooth=60)
    knob.add(G.sphere(0.024, 20), loc=(-0.05, 0.18, 0.775))
    knob.add(G.box((0.24, 0.03, 0.06), r=0.02), loc=(0, 0.46, 1.44))                    # rear-view mirror
    knob.add(G.tube([(0, 0.46, 1.47), (0, 0.48, 1.53)], 0.008, segs=8, smooth=False))
    knob.build(col, M)
    mg = G.Part("INT_MIRROR_GLASS", "Mirror_Glass", parent=cp, smooth=0)
    mg.add(G.box((0.22, 0.004, 0.05), r=0.015), loc=(0, 0.444, 1.44))
    mg.build(col, M)
    boot = G.Part("INT_SHIFT_BOOT", "Rubber", parent=cp, smooth=50)
    boot.add(G.lathe([(0.0, 0.0), (0.07, 0.0), (0.05, 0.04), (0.02, 0.10), (0.0, 0.10)], segs=24, uv=False),
             loc=(-0.02, 0.22, 0.50), rot=(0, -math.pi / 2, 0))
    boot.build(col, M)


def steering(cp, col, M):
    tilt = -0.35
    steer = _empty("STEER_HR", col, loc=(DRIVER_X, 0.42, 0.99), rot=(tilt, 0, 0), parent=cp)
    rim = G.Part("STEER_HR_RIM", "Interior_Black", parent=steer, smooth=60)
    ell = [(0.175 + 0.016 * math.cos(a), 0.013 * math.sin(a)) for a in [G.TAU * i / 12 for i in range(12)]]
    rim.add(G.lathe(ell, segs=64, uv=False), rot=(0, 0, math.pi / 2))
    rim.build(col, M)
    sp = G.Part("STEER_HR_SPOKES", "Anodized_Black", parent=steer, smooth=40)
    for a in (0.0, math.pi, -math.pi / 2):
        d = Vector((math.cos(a), 0, math.sin(a)))
        sp.add(G.box((0.15, 0.04, 0.012), r=0.005), matrix=G.basis(d * 0.095 + Vector((0, 0.012, 0)), d,
                                                                    Vector((0, 1, 0)).cross(d), (0, 1, 0)))
    sp.add(G.cyl(0.045, 0.04, segs=32), loc=(0, 0.03, 0), rot=(math.pi / 2, 0, 0))
    sp.build(col, M)
    hub = G.Part("STEER_HR_HUB", "Cast_Alu", parent=steer, smooth=40)
    hub.add(G.cyl(0.032, 0.06, segs=24), loc=(0, 0.08, 0), rot=(math.pi / 2, 0, 0))
    hub.build(col, M)
    btn = G.Part("STEER_HR_HORN", "Caliper_Red", parent=steer, smooth=40)
    btn.add(G.cyl(0.03, 0.012, segs=24), loc=(0, 0.004, 0), rot=(math.pi / 2, 0, 0))
    btn.add(G.box((0.02, 0.03, 0.03), r=0.005), loc=(0, 0.0, 0.176))                       # top marker
    btn.build(col, M)


def build(col, M):
    cp = _empty("COCKPIT_HR", col)
    seats(cp, col, M)
    harnesses(cp, col, M)
    cage(cp, col, M)
    dash(cp, col, M)
    controls(cp, col, M)
    steering(cp, col, M)
