"""Shared dimensions (metres). Blender space: +Y forward, +Z up, -X = car's left (driver side).

Real-world reference: 1994 Chevrolet/GMC GMT400 C/K1500 regular cab, short (6.5 ft) bed.
  wheelbase        117.5 in  = 2.985 m      -> WB 2.98
  body width        76.8 in  = 1.95 m       -> 2 x BODY_X 1.96 (wide-body flares add ~0.11 m per side)
  box length (in)   78.0 in  = 1.98 m       -> bed tub below
  front overhang    ~35 in   = 0.89 m       -> FRONT_Y - FA 0.73 + bumper/splitter
  rear overhang     ~42 in   = 1.07 m       -> RA - REAR_Y 0.99 + bumper
  cab (firewall->back) ~1.32 m              -> FIREWALL_Y - CAB_BACK_Y
  tyres  285/35R20 front, 335/30R20 rear    -> radius 0.354 / 0.355 m
"""
WB = 2.98
FA, RA = WB / 2, -WB / 2
TRACK_F, TRACK_R = 1.72, 1.70
TYRE_R = 0.355
RIM_R = 0.254
TYRE_W_F, TYRE_W_R = 0.285, 0.335
WHEEL_Z = TYRE_R
ARCH_R = 0.40
ARCH_Z = WHEEL_Z + 0.02
BODY_X = 0.98
BELT_Z = 1.04
ROOF_Z = 1.58
ROCKER_Z = 0.27
CREASE_Z = 0.88   # GMT400 shoulder line
FRONT_Y = 2.22
REAR_Y = -2.48
FIREWALL_Y = 0.92
CAB_BACK_Y = -0.40
BED_FRONT_Y = -0.46
BED_FLOOR_Z = 0.62
BAY_FLOOR_Z = 0.50
CAB_FLOOR_Z = 0.36
DRIVER_X = -0.42

# door shut lines (real GMT400 regular cab door is ~1.10 m long)
DOOR_FRONT_Y = 0.88
DOOR_REAR_Y = -0.22

# bed-mounted twin turbo: exhaust exits through the bed side ("box") just ahead of the rear wheels
EXIT_Y = (-0.80, -0.90)
EXIT_Z = 0.42
EXIT_R = 0.042
BED_KIT_SHIFT = 0.30          # turbo kit sits this far forward of where it was first modelled
