"""Wide-body kit: carbon side skirts joining the over-fenders, front/rear fender extensions to the bumpers,
and machined trim rings around the bed-side exhaust exits."""

import math

import bpy  # noqa: F401
from mathutils import Vector

from . import geo as G
from .dims import ARCH_R, BODY_X, EXIT_R, EXIT_Y, EXIT_Z, FA, FRONT_Y, RA, REAR_Y, ROCKER_Z


def _sm(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def skirts(col, M):
    carbon = G.Part("WIDEBODY_SKIRTS", "Carbon", smooth=35, uv_scale=8)
    lip = G.Part("WIDEBODY_SKIRT_LIPS", "Carbon", smooth=30, uv_scale=8)
    bolts = G.Part("BOLTS_WIDEBODY_SKIRTS", "Chrome", smooth=40)
    y0 = RA + 0.385 - 0.04
    y1 = FA - 0.385 + 0.04
    for s in (-1, 1):
        secs = []
        n = 56
        for i in range(n + 1):
            t = i / n
            y = y0 + (y1 - y0) * t
            e = min(_sm(t / 0.10), _sm((1 - t) / 0.10))
            k = 0.45 + 0.55 * e
            w, h = 0.118 * k, 0.150 * k
            cx = s * (BODY_X + 0.040 + 0.012 * (1 - k))
            cz = ROCKER_Z - 0.01
            pts = G.rrect2d(w, h, 0.028 * k, k=5)
            secs.append([(cx + px, y, cz + pz) for px, pz in pts])
        carbon.add(G.loft(secs))
        lip.add(G.box((0.085, y1 - y0 - 0.20, 0.012), r=0.004), loc=(s * (BODY_X + 0.088), (y0 + y1) / 2, ROCKER_Z - 0.095))
        n_b = 14
        for i in range(n_b):
            y = y0 + 0.10 + (y1 - y0 - 0.20) * i / (n_b - 1)
            bolts.add(G.bolt(0.0065, 0.007), loc=(s * (BODY_X + 0.040 + 0.059 + 0.002), y, ROCKER_Z - 0.01),
                      rot=(0, math.pi / 2, 0))
            bolts.add(G.washer(0.0095, 0.002), loc=(s * (BODY_X + 0.040 + 0.059), y, ROCKER_Z - 0.01),
                      rot=(0, math.pi / 2, 0))
    carbon.build(col, M)
    lip.build(col, M)
    bolts.build(col, M)


def extensions(col, M):
    """Fender extensions that carry the flare line forward/back into the bumpers."""
    ext = G.Part("WIDEBODY_EXTENSIONS", "Carbon", smooth=40, uv_scale=8)
    bolts = G.Part("BOLTS_WIDEBODY_EXT", "Chrome", smooth=40)
    front = G.fillet_poly([(0.96, FA + 0.33), (1.085, FA + 0.33), (1.09, FA + 0.46), (1.06, FRONT_Y + 0.00),
                           (1.02, FRONT_Y + 0.10), (0.93, FRONT_Y + 0.12)], [0.0, 0.03, 0.04, 0.06, 0.04, 0.0], k=5)
    rear = G.fillet_poly([(0.96, RA - 0.33), (1.095, RA - 0.33), (1.10, RA - 0.46), (1.07, REAR_Y + 0.14),
                          (1.02, REAR_Y - 0.06), (0.93, REAR_Y - 0.06)], [0.0, 0.03, 0.04, 0.06, 0.04, 0.0], k=5)
    for s in (-1, 1):
        ext.add(G.prism(front, 0.29, axis="Z"), loc=(0, 0, 0.455), scale=(s, 1, 1))
        ext.add(G.prism(rear, 0.34, axis="Z"), loc=(0, 0, 0.47), scale=(s, 1, 1))
        for y, z in ((FA + 0.52, 0.36), (FA + 0.52, 0.55), (FRONT_Y - 0.10, 0.36), (FRONT_Y - 0.10, 0.55)):
            bolts.add(G.bolt(0.0065, 0.007), loc=(s * 1.085, y, z), rot=(0, math.pi / 2, 0))
        for y, z in ((RA - 0.55, 0.36), (RA - 0.55, 0.58), (REAR_Y + 0.30, 0.36), (REAR_Y + 0.30, 0.58)):
            bolts.add(G.bolt(0.0065, 0.007), loc=(s * 1.09, y, z), rot=(0, math.pi / 2, 0))
    ext.build(col, M)
    bolts.build(col, M)


def exit_trims(col, M):
    ring = G.Part("EXHAUST_EXIT_TRIM", "Anodized_Black", smooth=40)
    screws = G.Part("BOLTS_EXHAUST_EXIT_TRIM", "Chrome", smooth=30)
    r0 = EXIT_R + 0.006
    for s in (-1, 1):
        for y in EXIT_Y:
            prof = [(r0, -0.004), (r0 + 0.020, -0.004), (r0 + 0.024, 0.002), (r0 + 0.020, 0.008), (r0 + 0.006, 0.012),
                    (r0, 0.012)]
            ring.add(G.lathe(prof, segs=64, uv=False), loc=(s * (BODY_X + 0.004), y, EXIT_Z), scale=(s, 1, 1))
            for k in range(6):
                a = G.TAU * k / 6 + 0.3
                screws.add(G.bolt(0.0035, 0.004),
                           loc=(s * (BODY_X + 0.015), y + (r0 + 0.012) * math.cos(a), EXIT_Z + (r0 + 0.012) * math.sin(a)),
                           rot=(0, math.pi / 2, 0))
    ring.build(col, M)
    screws.build(col, M)


def build(col, M):
    skirts(col, M)
    exit_trims(col, M)
