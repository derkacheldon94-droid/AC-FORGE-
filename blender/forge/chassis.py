"""Underside: frame, crossmembers, suspension arms, steering rack, IRS diff + half shafts, driveshaft,
header crossover pipes running back to the bed turbos, charge pipe forward to the intercooler."""

import math

import bpy  # noqa: F401

from . import geo as G
from .dims import BED_KIT_SHIFT, FA, FRONT_Y, RA, TRACK_F, TRACK_R, WHEEL_Z

TY = -1.17 + BED_KIT_SHIFT


def build(col, M):
    frame = G.Part("CHASSIS_FRAME", "Engine_Dark", smooth=30)
    for s in (-1, 1):
        frame.add(G.box((0.07, 4.50, 0.07), r=0.008), loc=(s * 0.50, -0.20, 0.235))
    for y in (1.95, 0.90, -0.50, -2.05, -2.42):
        frame.add(G.box((1.06, 0.07, 0.06), r=0.008), loc=(0, y, 0.235))
    frame.build(col, M)

    arms = G.Part("CHASSIS_ARMS", "Anodized_Black", smooth=40)
    alu = G.Part("CHASSIS_ALU", "Cast_Alu", smooth=40)
    rub = G.Part("CHASSIS_BOOTS", "Rubber", smooth=50)
    for y0, rear in ((FA, False), (RA, True)):
        for s in (-1, 1):
            hw = (TRACK_R if rear else TRACK_F) / 2
            hub = (s * (hw - 0.14), y0, WHEEL_Z - 0.12)
            for dy in (-0.16, 0.16):
                arms.add(G.tube([(s * 0.30, y0 + dy, 0.24), hub], 0.016, segs=10, smooth=False))
            top = (s * (hw - 0.16), y0, WHEEL_Z + 0.17)
            for dy in (-0.12, 0.12):
                arms.add(G.tube([(s * 0.42, y0 + dy, 0.56), top], 0.014, segs=10, smooth=False))
            arms.add(G.sphere(0.022, 10), loc=hub)
            arms.add(G.sphere(0.02, 10), loc=top)
            if rear:      # half shafts with CV boots
                arms.add(G.tube([(s * 0.16, y0, 0.36), (s * (hw - 0.18), y0, WHEEL_Z)], 0.022, segs=14, smooth=False))
                for x in (0.22, hw - 0.24):
                    rub.add(G.lathe([(0.022, -0.04), (0.045, -0.02), (0.035, 0.0), (0.045, 0.02), (0.022, 0.04)],
                                    segs=20, uv=False), loc=(s * x, y0, 0.36 + (WHEEL_Z - 0.36) * (x - 0.16) / (hw - 0.34)))
            else:         # steering rack + tie rods
                arms.add(G.tube([(s * 0.30, y0 - 0.13, 0.30), (s * (hw - 0.12), y0 - 0.13, WHEEL_Z - 0.03)], 0.011,
                                segs=10, smooth=False))
                rub.add(G.lathe([(0.012, -0.05), (0.03, -0.03), (0.02, 0.0), (0.03, 0.03), (0.012, 0.05)], segs=16,
                                uv=False), loc=(s * 0.32, y0 - 0.13, 0.30))
    alu.add(G.cyl(0.03, 0.56, segs=16), loc=(0, FA - 0.13, 0.30), rot=(0, math.pi / 2, 0))     # rack
    alu.add(G.lathe([(0.04, -0.12), (0.15, -0.10), (0.16, 0.0), (0.15, 0.08), (0.06, 0.12), (0.04, 0.12)], segs=40,
                    uv=False), loc=(0, RA, 0.36), rot=(0, 0, math.pi / 2))                       # diff
    for k in range(7):
        alu.add(G.box((0.20, 0.006, 0.03)), loc=(0, RA - 0.125, 0.30 + k * 0.02))               # cover fins
    arms.add(G.tube([(0, 0.95, 0.27), (0, RA + 0.13, 0.33)], 0.038, segs=16, smooth=False))     # driveshaft
    for p in (arms, alu, rub):
        p.build(col, M)

    # exhaust crossover: header collectors -> under the cab -> up through the bed floor to the turbines
    wrap = G.Part("CHASSIS_EXHAUST_CROSSOVER", "Heat_Wrap", smooth=50, uv_scale=12)
    for s in (-1, 1):
        at = s * 0.36 - s * 0.085
        wrap.add(G.tube([(s * 0.40, 1.10, 0.44), (s * 0.42, 0.95, 0.20), (s * 0.40, -0.55, 0.19),
                         (at + s * 0.02, TY - 0.17, 0.20), (at + s * 0.01, TY - 0.21, 0.57)], 0.045, segs=16))
    wrap.build(col, M)
    # charge pipe: centre plenum -> under the floor -> front intercooler (left tank)
    pol = G.Part("CHASSIS_CHARGE_PIPE", "Metal_Polished", smooth=50)
    pol.add(G.tube([(0, -0.98 + BED_KIT_SHIFT, 0.58), (-0.05, -0.90 + BED_KIT_SHIFT, 0.21), (-0.22, -0.40, 0.19), (-0.22, 1.60, 0.19),
                    (-0.55, FRONT_Y - 0.05, 0.22), (-0.60, FRONT_Y + 0.07, 0.27)], 0.045, segs=18))
    pol.build(col, M)
