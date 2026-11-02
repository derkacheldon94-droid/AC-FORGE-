"""Wheels: lettered semi-slick tyres, 3-piece-look split 7-spoke rims, vented 2-piece rotors,
6-piston calipers, uprights. Plus rim-blur discs for speed (blurred_objects.ini)."""

import math

import bpy  # noqa: F401
from mathutils import Vector

from . import geo as G
from .dims import FA, RA, RIM_R, TRACK_F, TRACK_R, TYRE_R, TYRE_W_F, TYRE_W_R, WHEEL_Z


def tyre_profile(hw):
    """Closed (radius, axial) loop. Returns (points, (k_start, k_end) of the outer sidewall band)."""
    R = TYRE_R
    outer = [(RIM_R + 0.004, hw - 0.012), (RIM_R + 0.018, hw - 0.004), (RIM_R + 0.040, hw + 0.004),
             (RIM_R + 0.065, hw + 0.006), (R - 0.026, hw + 0.002), (R - 0.011, hw - 0.012),
             (R - 0.003, hw - 0.028), (R, hw - 0.048)]
    grooves = [hw * 0.36, -hw * 0.36]
    tread = []
    for g in grooves:
        tread += [(R, g + 0.009), (R - 0.006, g + 0.006), (R - 0.006, g - 0.006), (R, g - 0.009)]
    inner = [(r, -a) for r, a in reversed(outer)]
    bead = [(RIM_R - 0.004, -hw + 0.016), (RIM_R - 0.004, hw - 0.016)]
    pts = outer + tread + inner + bead
    return pts, (1, 4)


def tyre_band():
    pts, (k0, k1) = tyre_profile(TYRE_W_F / 2)
    n = len(pts)
    return (k0 / n, k1 / n)


def _tyre(hw):
    pts, _ = tyre_profile(hw)
    shoulder = {6, len(pts) - 9}

    def mod(i, k, r):
        if k in shoulder and (i // 3) % 2 == 0:
            return r - 0.004
        return r
    return G.lathe(pts, segs=112, closed=True, uv=True, modulate=mod)


def _spokes(hw):
    """Ten thin spokes laid over ten reverse-twisted ones: the crossing 'star mesh' pattern of the art."""
    bm_list = []
    a_hub, a_out = hw - 0.034, hw - 0.064
    r_hub, r_out = 0.078, RIM_R - 0.034
    for i in range(10):
        base = G.TAU * i / 10
        for side, layer in ((1, 0.0), (-1, 0.007)):
            pts = []
            for j in range(9):
                t = j / 8
                r = r_hub + (r_out - r_hub) * t
                th = base + side * (0.03 + 0.20 * t ** 1.3)
                a = a_hub + (a_out - a_hub) * (t ** 0.8) - 0.006 * math.sin(math.pi * t) + layer * math.sin(math.pi * t)
                pts.append((a, r * math.cos(th), r * math.sin(th)))
            bm_list.append(G.sweep(pts, G.rrect2d(0.020, 0.015, 0.006, k=3), up_hint=(1, 0, 0),
                                   scale=lambda t: 1.0 - 0.30 * t))
    return bm_list


def wheel(empty, width, M, col, tag):
    hw = width / 2
    tyre = G.Part(f"{empty.name}_TYRE", "Tyre_Front" if tag[1] == "F" else "Tyre_Rear", parent=empty, smooth=50)
    tyre.add(_tyre(hw))
    tyre.build(col, M)

    lip = G.Part(f"{empty.name}_RIM_LIP", "Rim_Lip", parent=empty, smooth=40)
    lip_prof = [(RIM_R - 0.036, hw - 0.062), (RIM_R - 0.026, hw - 0.062), (RIM_R - 0.022, hw - 0.018),
                (RIM_R + 0.004, hw - 0.012), (RIM_R + 0.013, hw - 0.006), (RIM_R + 0.012, hw - 0.0005),
                (RIM_R - 0.004, hw - 0.001), (RIM_R - 0.030, hw - 0.010), (RIM_R - 0.038, hw - 0.030)]
    lip.add(G.lathe(lip_prof, segs=72, uv=False))
    lip.build(col, M)

    barrel = G.Part(f"{empty.name}_RIM_BARREL", "Cast_Alu", parent=empty, smooth=40)
    barrel.add(G.lathe([(RIM_R - 0.014, -hw + 0.008), (RIM_R + 0.010, -hw + 0.004), (RIM_R + 0.010, -hw + 0.014),
                        (RIM_R - 0.002, -hw + 0.02), (RIM_R - 0.002, hw - 0.06), (RIM_R - 0.014, hw - 0.06)],
                       segs=56, uv=False))
    barrel.build(col, M)

    face = G.Part(f"{empty.name}_RIM", "Rim_Red", parent=empty, smooth=40)
    for s in _spokes(hw):
        face.add(s)
    face.add(G.lathe([(RIM_R - 0.044, hw - 0.075), (RIM_R - 0.012, hw - 0.075), (RIM_R - 0.012, hw - 0.055),
                      (RIM_R - 0.044, hw - 0.055)], segs=96, uv=False))
    face.add(G.lathe([(0.03, hw - 0.055), (0.092, hw - 0.055), (0.096, hw - 0.04), (0.088, hw - 0.026),
                      (0.03, hw - 0.026)], segs=64, uv=False))
    face.build(col, M)

    hw_p = G.Part(f"BOLTS_{empty.name}_HARDWARE", "Chrome", parent=empty, smooth=30)
    for i in range(32):                                   # lip rivets
        th = G.TAU * i / 32
        r = RIM_R - 0.017
        hw_p.add(G.bolt(0.0055, 0.0045, top=0.55), loc=(hw - 0.0085, r * math.cos(th), r * math.sin(th)))
    for i in range(6):                                    # lug nuts (hex) + washers
        th = G.TAU * i / 6 + 0.3
        c = (hw - 0.018, 0.058 * math.cos(th), 0.058 * math.sin(th))
        hw_p.add(G.bolt(0.0115, 0.024), loc=c, rot=(0, math.pi / 2, 0))
        hw_p.add(G.washer(0.015, 0.004), loc=(hw - 0.029, c[1], c[2]), rot=(0, math.pi / 2, 0))
    hw_p.add(G.cyl(0.004, 0.035, segs=8), loc=(hw - 0.03, 0, RIM_R - 0.03), rot=(0, math.pi / 2 - 0.5, 0))
    hw_p.build(col, M)
    cap = G.Part(f"DETAIL_{empty.name}_CAP", "Gloss_Black", parent=empty, smooth=40)
    cap.add(G.lathe([(0.0, hw - 0.03), (0.033, hw - 0.03), (0.034, hw - 0.012), (0.026, hw - 0.004),
                     (0.0, hw - 0.002)], segs=48, uv=False))
    cap.build(col, M)

    blur = G.Part(f"RIM_BLUR_{tag}", "Rim_Blur", parent=empty, smooth=0)
    d = G.cyl(RIM_R + 0.012, 0.004, segs=64)
    G.planar_uv(d, (0, 0, 0), (1, 0, 0), (0, 1, 0), 2 * (RIM_R + 0.012), 2 * (RIM_R + 0.012))
    blur.add(d, loc=(hw - 0.012, 0, 0), rot=(0, math.pi / 2, 0))
    blur.build(col, M)


def brakes(disc_empty, susp_empty, width, front, M, col, tag):
    hw = width / 2
    a_d = hw - 0.15
    r_out = 0.19 if front else 0.175
    r_in = 0.115 if front else 0.105
    rotor = G.Part(f"{disc_empty.name}_ROTOR", "Brake_Disc", parent=disc_empty, smooth=30)
    for off in (-0.011, 0.011):
        plate = G.lathe([(r_in, off - 0.005), (r_out, off - 0.005), (r_out, off + 0.005), (r_in, off + 0.005)],
                        segs=72, uv=False)
        G.planar_uv(plate, (0, 0, 0), (0, 1, 0), (0, 0, 1), 2 * r_out, 2 * r_out)
        rotor.add(plate, loc=(a_d, 0, 0))
    rotor.build(col, M)
    vanes = G.Part(f"{disc_empty.name}_VANES", "Engine_Dark", parent=disc_empty, smooth=0)
    for i in range(28):
        th = G.TAU * i / 28
        rm = (r_in + r_out) / 2
        vanes.add(G.box((0.012, r_out - r_in - 0.004, 0.005)), loc=(a_d, rm * math.cos(th), rm * math.sin(th)),
                  rot=(th - math.pi / 2 + 0.25, 0, 0))
    vanes.build(col, M)
    hat = G.Part(f"{disc_empty.name}_HAT", "Cast_Alu", parent=disc_empty, smooth=40)
    hat.add(G.lathe([(0.03, hw - 0.075), (0.092, hw - 0.075), (r_in + 0.012, a_d + 0.012),
                     (r_in + 0.012, a_d - 0.006), (r_in - 0.004, a_d - 0.006), (0.085, hw - 0.085),
                     (0.03, hw - 0.085)], segs=64, uv=False))
    for i in range(12):
        th = G.TAU * i / 12
        hat.add(G.cyl(0.007, 0.03, segs=10), loc=(a_d, (r_in + 0.004) * math.cos(th), (r_in + 0.004) * math.sin(th)),
                rot=(0, math.pi / 2, 0))
    hat.build(col, M)

    # caliper on the upper-rear of the rotor
    thc = 2.2
    cal = G.Part(f"SUSP_{tag}_CALIPER", "Caliper_Red", parent=susp_empty, smooth=40)
    rc = r_out - 0.022
    path = [(a_d, rc * math.cos(t), rc * math.sin(t)) for t in [thc - 0.5 + 1.0 * j / 16 for j in range(17)]]
    cal.add(G.sweep(path, G.rrect2d(0.105, 0.085, 0.025, k=4), up_hint=(1, 0, 0)))
    for t in (thc - 0.53, thc + 0.53):       # end caps / bridge blocks
        cal.add(G.box((0.11, 0.03, 0.09), r=0.012), loc=(a_d, rc * math.cos(t), rc * math.sin(t)), rot=(t, 0, 0))
    cal.build(col, M)
    det = G.Part(f"SUSP_{tag}_CALIPER_HW", "Chrome", parent=susp_empty, smooth=30)
    for t in (thc - 0.25, thc + 0.25):
        rb = rc + 0.035
        det.add(G.cyl(0.007, 0.12, segs=12), loc=(a_d, rb * math.cos(t), rb * math.sin(t)), rot=(0, math.pi / 2, 0))
    det.add(G.cyl(0.004, 0.02, segs=8), loc=(a_d + 0.05, (rc + 0.03) * math.cos(thc + 0.4),
                                             (rc + 0.03) * math.sin(thc + 0.4)), rot=(0, math.pi / 2, 0))
    det.build(col, M)
    txt = G.Part(f"SUSP_{tag}_CALIPER_LOGO", "Decal_White", parent=susp_empty, smooth=0)
    radial = Vector((0, math.cos(thc), math.sin(thc)))
    normal = Vector((1, 0, 0))
    origin = Vector((a_d + 0.0535, 0, 0)) + radial * rc
    txt.add(G.text("FORGE", size=0.034, depth=0.0015), matrix=G.basis(origin, radial.cross(normal), radial, normal))
    txt.build(col, M)
    upright = G.Part(f"SUSP_{tag}_UPRIGHT", "Cast_Alu", parent=susp_empty, smooth=40)
    upright.add(G.lathe([(0.03, a_d - 0.06), (0.075, a_d - 0.06), (0.075, a_d - 0.03), (0.03, a_d - 0.03)],
                        segs=32, uv=False))
    upright.add(G.box((0.05, 0.08, 0.30), r=0.02), loc=(a_d - 0.07, -0.02, 0.0))
    upright.add(G.box((0.05, 0.22, 0.04), r=0.015), loc=(a_d - 0.07, -0.11 if front else 0.10, -0.02))
    upright.build(col, M)


def build(col, M):
    for tag, y, track, width in (("LF", FA, TRACK_F, TYRE_W_F), ("RF", FA, TRACK_F, TYRE_W_F),
                                 ("LR", RA, TRACK_R, TYRE_W_R), ("RR", RA, TRACK_R, TYRE_W_R)):
        s = -1 if tag[0] == "L" else 1
        center = (s * track / 2, y, WHEEL_Z)
        yaw = (0, 0, 0) if s > 0 else (0, 0, math.pi)
        names = {}
        for kind in ("WHEEL", "DISC", "SUSP"):
            e = bpy.data.objects.new(f"{kind}_{tag}", None)
            e.empty_display_type = "PLAIN_AXES"
            e.empty_display_size = 0.2
            col.objects.link(e)
            e.location = center
            names[kind] = e
        # geometry is built "outer face = +X"; the left side gets a 180 degree yaw baked in
        G.Part.post = G.xf(rot=yaw)
        wheel(names["WHEEL"], width, M, col, tag)
        brakes(names["DISC"], names["SUSP"], width, tag[1] == "F", M, col, tag)
        G.Part.post = None
