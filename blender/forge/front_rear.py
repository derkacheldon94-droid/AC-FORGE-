"""Front fascia (quad lamps, grille, bumper, intercooler, splitter), rear end, mirrors, trim, badges."""

import math

import bpy  # noqa: F401
from mathutils import Vector

from . import geo as G
from .dims import BELT_Z, BODY_X, CAB_BACK_Y, DOOR_REAR_Y, FRONT_Y, REAR_Y, ROOF_Z

Y0 = FRONT_Y


LAMP_STYLE = "angled"   # "angled" (photo reference) or "bracket" (drawn concept art)


def _bracket(part, xc, z, s, y, w=0.10, h=0.06):
    """LED light signature. angled: a diagonal dropping inward, then a horizontal run toward the car
    centre. bracket: a square bracket opening toward the centre."""
    if LAMP_STYLE == "bracket":
        w, h = 0.08, 0.09
        x_out, x_in = xc + s * w / 2, xc - s * w / 2
        pts = [(x_in, y, z + h / 2), (x_out, y, z + h / 2), (x_out, y, z - h / 2), (x_in, y, z - h / 2)]
        r = 0.014
    else:
        x_out, x_mid, x_in = xc + s * w / 2, xc + s * w * 0.1, xc - s * w / 2
        pts = [(x_out, y, z + h / 2), (x_mid, y, z - h / 2), (x_in, y, z - h / 2)]
        r = 0.01
    path = G.fillet_open(pts, r, k=6)
    part.add(G.sweep(path, G.rrect2d(0.008, 0.013, 0.003, k=3), up_hint=(0, 1, 0)))


def headlamps(col, M):
    housing = G.Part("LAMP_HOUSINGS", "Gloss_Black", smooth=40)
    inner = G.Part("LAMP_INNER_REFLECTORS", "Reflector", smooth=40)
    proj = G.Part("LAMP_INNER_PROJECTORS", "Lens_Clear", smooth=60)
    lens = G.Part("LAMP_LENSES", "Lens_Clear", smooth=30)
    leds = {s: G.Part(f"LIGHT_HEAD_{'L' if s < 0 else 'R'}", "Light_Head", smooth=50) for s in (-1, 1)}
    for s in (-1, 1):
        for z in (0.70, 0.885):
            xc = s * 0.735
            housing.add(G.box((0.31, 0.045, 0.16), r=0.012), loc=(xc, Y0 + 0.0225, z))
            for dz in (-0.077, 0.077):         # bezel lips around the lens
                housing.add(G.box((0.31, 0.026, 0.008), r=0.003), loc=(xc, Y0 + 0.058, z + dz))
            for dx in (-0.152, 0.152):
                housing.add(G.box((0.008, 0.026, 0.16), r=0.003), loc=(xc + dx, Y0 + 0.058, z))
            inner.add(G.box((0.29, 0.004, 0.14), r=0.01), loc=(xc, Y0 + 0.047, z))
            for bx in (xc - 0.07, xc + 0.07):
                _bracket(leds[s], bx, z, s, Y0 + 0.056)
                # projector bowl + lens in the middle of each bracket
                inner.add(G.lathe([(0.004, 0.0), (0.022, 0.004), (0.03, 0.012), (0.032, 0.016)], segs=24,
                                  closed=False, uv=False), loc=(bx - s * 0.012, Y0 + 0.047, z + 0.022),
                          rot=(0, 0, -math.pi / 2))
                proj.add(G.sphere(0.018, segs=16), loc=(bx - s * 0.012, Y0 + 0.054, z + 0.022))
            lens.add(G.box((0.30, 0.006, 0.152), r=0.003), loc=(xc, Y0 + 0.068, z))
    for p in (housing, inner, proj, lens, *leds.values()):
        p.build(col, M)


def grille(col, M):
    frame = G.Part("FRONT_GRILLE_FRAME", "Gloss_Black", smooth=40)
    mesh = G.Part("FRONT_GRILLE_MESH", "Grille_Mesh", smooth=0, uv_scale=5)
    zc, h, w = 0.795, 0.33, 1.12
    mesh.add(G.box((w, 0.01, h)), loc=(0, Y0 + 0.012, zc))
    for dz in (-h / 2, h / 2):
        frame.add(G.box((w + 0.05, 0.05, 0.03), r=0.01), loc=(0, Y0 + 0.025, zc + dz))
    for dx in (-w / 2, w / 2):
        frame.add(G.box((0.03, 0.05, h + 0.03), r=0.01), loc=(dx, Y0 + 0.025, zc))
    for dz in (-0.055, 0.055):                                     # horizontal bars
        frame.add(G.box((w, 0.035, 0.022), r=0.008), loc=(0, Y0 + 0.03, zc + dz))
    # centre badge
    frame.add(G.box((0.26, 0.03, 0.085), r=0.02), loc=(0, Y0 + 0.042, zc))
    chrome = G.Part("BADGE_FRONT", "Chrome", smooth=40)
    ring = [Vector((x, Y0 + 0.058, zc + z)) for x, z in G.fillet_poly([(-0.13, -0.042), (0.13, -0.042),
                                                                        (0.13, 0.042), (-0.13, 0.042)], 0.02, k=5)]
    chrome.add(G.sweep(ring, G.circle2d(0.004, 6), closed=True))
    # (the plate is left blank where the bowtie goes)
    z71 = G.Part("BADGE_FRONT_Z71", "Caliper_Red", smooth=30)
    z71.add(G.text("Z71", size=0.06, depth=0.005), matrix=G.basis((-0.22, Y0 + 0.05, zc), (-1, 0, 0), (0, 0, 1),
                                                                  (0, 1, 0)))
    z71.build(col, M)
    frame.build(col, M)
    mesh.build(col, M)
    chrome.build(col, M)


def bumper_front(col, M):
    body = G.Part("FRONT_BUMPER", "Paint_Black", smooth=40)
    trim = G.Part("FRONT_BUMPER_TRIM", "Gloss_Black", smooth=40)
    mesh = G.Part("FRONT_BUMPER_MESH", "Grille_Mesh", smooth=0, uv_scale=6)
    carbon = G.Part("FRONT_SPLITTER", "Carbon", smooth=30, uv_scale=8)
    body.add(G.box((2.02, 0.27, 0.15), r=0.045), loc=(0, Y0 + 0.075, 0.565))
    for s in (-1, 1):
        body.add(G.box((0.40, 0.29, 0.31), r=0.06), loc=(s * 0.80, Y0 + 0.085, 0.355))
        trim.add(G.box((0.25, 0.02, 0.16), r=0.03), loc=(s * 0.80, Y0 + 0.226, 0.36))
        mesh.add(G.box((0.22, 0.01, 0.13)), loc=(s * 0.80, Y0 + 0.233, 0.36))
        for k in range(5):
            trim.add(G.box((0.22, 0.02, 0.008), r=0.002), loc=(s * 0.80, Y0 + 0.236, 0.31 + k * 0.025))
    body.add(G.box((1.24, 0.22, 0.05), r=0.02), loc=(0, Y0 + 0.07, 0.235))
    trim.add(G.box((1.24, 0.03, 0.03), r=0.01), loc=(0, Y0 + 0.19, 0.49))
    trim.add(G.box((1.24, 0.03, 0.03), r=0.01), loc=(0, Y0 + 0.19, 0.265))
    # splitter (carbon) with endplates and support rods
    plan = G.fillet_poly([(-1.03, Y0 - 0.02), (1.03, Y0 - 0.02), (1.03, Y0 + 0.31), (0.86, Y0 + 0.37),
                          (-0.86, Y0 + 0.37), (-1.03, Y0 + 0.31)], [0, 0, 0.05, 0.08, 0.08, 0.05], k=6)
    carbon.add(G.prism(plan, 0.018, axis="Z"), loc=(0, 0, 0.212))
    for s in (-1, 1):
        ep = G.fillet_poly([(Y0 + 0.08, 0.20), (Y0 + 0.33, 0.20), (Y0 + 0.30, 0.27), (Y0 + 0.10, 0.31)],
                           0.015, k=4)
        carbon.add(G.prism(ep, 0.012, axis="X"), loc=(s * 1.03, 0, 0))
        canard = G.fillet_poly([(Y0 + 0.07, 0.40), (Y0 + 0.24, 0.42), (Y0 + 0.24, 0.44), (Y0 + 0.07, 0.47)],
                               0.01, k=3)
        carbon.add(G.prism(canard, 0.09, axis="X"), loc=(s * 1.03, 0, 0), rot=(0, 0, s * 0.08))
    rods = G.Part("DETAIL_SPLITTER_RODS", "Anodized_Black", smooth=40)
    for s in (-0.55, 0.55):
        rods.add(G.tube([(s, Y0 + 0.2, 0.30), (s, Y0 + 0.3, 0.223)], 0.006, segs=8))
        rods.add(G.sphere(0.011, 8), loc=(s, Y0 + 0.2, 0.30))
        rods.add(G.sphere(0.011, 8), loc=(s, Y0 + 0.3, 0.226))
    for p in (body, trim, mesh, carbon, rods):
        p.build(col, M)


def intercooler(col, M):
    core = G.Part("FRONT_INTERCOOLER_CORE", "Intercooler_Fins", smooth=0, uv_scale=10)
    tanks = G.Part("FRONT_INTERCOOLER_TANKS", "Cast_Alu", smooth=40)
    pipes = G.Part("ENGINE_CHARGE_PIPES_FRONT", "Metal_Polished", smooth=50)
    sil = G.Part("ENGINE_SMALL_COUPLERS_FRONT", "Silicone_Red", smooth=50)
    core.add(G.box((1.10, 0.07, 0.205)), loc=(0, Y0 + 0.09, 0.378))
    for i in range(12):
        tanks.add(G.box((1.10, 0.004, 0.003)), loc=(0, Y0 + 0.127, 0.282 + i * 0.0175))
    for s in (-1, 1):
        tanks.add(G.box((0.10, 0.11, 0.25), r=0.03), loc=(s * 0.60, Y0 + 0.09, 0.378))
        path = [(s * 0.60, Y0 + 0.07, 0.50), (s * 0.62, Y0 + 0.0, 0.60), (s * 0.58, 2.05, 0.70),
                (s * 0.52, 1.95, 0.80)]
        pipes.add(G.tube(path, 0.038, segs=20))
        sil.add(G.cyl(0.043, 0.07, segs=24), loc=(s * 0.60, Y0 + 0.07, 0.53))
    for p in (core, tanks, pipes, sil):
        p.build(col, M)
    clamps_ring = G.Part("BOLTS_IC_CLAMP_RINGS", "Chrome", smooth=50)
    for s in (-1, 1):
        for dz in (-0.022, 0.022):
            ring = [(0.045 + 0.004 * math.cos(a), 0.004 * math.sin(a)) for a in [G.TAU * i / 6 for i in range(6)]]
            clamps_ring.add(G.lathe(ring, segs=24, uv=False), loc=(s * 0.60, Y0 + 0.07, 0.53 + dz),
                            rot=(0, -math.pi / 2, 0))
    clamps_ring.build(col, M)


def tow_straps(col, M):
    strap = G.Part("FRONT_TOW_STRAPS", "Strap_Red", smooth=40, uv_scale=8)
    for loc, plane in (((0.42, Y0 + 0.235, 0.46), "front"), ((-0.55, REAR_Y - 0.19, 0.36), "rear")):
        cx, cy, cz = loc
        sgn = 1 if plane == "front" else -1
        path = [(cx, cy + sgn * (0.035 + 0.035 * math.cos(a)), cz - 0.075 * (1 - math.sin(a)) / 2 - 0.0)
                for a in [G.TAU * i / 24 for i in range(24)]]
        strap.add(G.sweep(path, G.rrect2d(0.035, 0.005, 0.002, k=2), closed=True, up_hint=(1, 0, 0)))
    strap.build(col, M)


def markers_mirrors_trim(col, M):
    lens_a = G.Part("LAMP_MARKER_LENS_F", "Lens_Amber", smooth=30)
    lens_r = G.Part("LAMP_MARKER_LENS_R", "Lens_Red", smooth=30)
    mk_f = G.Part("LIGHT_MARKER_F", "Light_Marker", smooth=0)
    mk_r = G.Part("LIGHT_MARKER_R", "Light_Tail", smooth=0)
    for s in (-1, 1):
        lens_a.add(G.box((0.012, 0.11, 0.042), r=0.005), loc=(s * (BODY_X + 0.001), 2.06, 0.86))
        mk_f.add(G.box((0.004, 0.09, 0.03)), loc=(s * (BODY_X - 0.004), 2.06, 0.86))
        lens_r.add(G.box((0.012, 0.11, 0.042), r=0.005), loc=(s * (BODY_X + 0.001), REAR_Y + 0.12, 0.86))
        mk_r.add(G.box((0.004, 0.09, 0.03)), loc=(s * (BODY_X - 0.004), -2.38, 0.86))
    for p in (lens_a, lens_r, mk_f, mk_r):
        p.build(col, M)

    housing = G.Part("BODY_MIRRORS", "Paint_Black", smooth=40)
    glass = G.Part("MIRROR_GLASS", "Mirror_Glass", smooth=0)
    for s in (-1, 1):
        housing.add(G.box((0.18, 0.095, 0.125), r=0.04), loc=(s * 1.115, 0.80, BELT_Z + 0.115))
        housing.add(G.tube([(s * 0.962, 0.85, BELT_Z + 0.025), (s * 1.0, 0.84, BELT_Z + 0.07),
                            (s * 1.04, 0.815, BELT_Z + 0.10)], 0.017, segs=12))
        housing.add(G.box((0.03, 0.12, 0.07), r=0.012), loc=(s * 0.965, 0.86, BELT_Z + 0.03))
        glass.add(G.box((0.155, 0.004, 0.10), r=0.025), loc=(s * 1.115, 0.80 - 0.047, BELT_Z + 0.115))
    housing.build(col, M)
    glass.build(col, M)

    trim = G.Part("DETAIL_BODY_HARDWARE", "Gloss_Black", smooth=40)
    chrome = G.Part("DETAIL_BODY_CHROME", "Chrome", smooth=40)
    for s in (-1, 1):
        trim.add(G.box((0.012, 0.15, 0.032), r=0.006), loc=(s * (BODY_X - 0.008), -0.10, 0.905))
        chrome.add(G.cyl(0.009, 0.01, segs=16), loc=(s * (BODY_X - 0.002), 0.04, 0.905), rot=(0, math.pi / 2, 0))
    paint = G.Part("BODY_FUEL_DOOR", "Paint_Black", smooth=40)
    paint.add(G.cyl(0.069, 0.006, segs=48), loc=(-(BODY_X - 0.007), -0.98, 0.80), rot=(0, math.pi / 2, 0))
    paint.build(col, M)
    # cowl panel + wipers
    trim.add(G.box((1.84, 0.13, 0.016), r=0.005), loc=(0, 1.0, BELT_Z + 0.004))
    for i in range(24):
        trim.add(G.box((0.045, 0.006, 0.012)), loc=(-0.80 + i * 0.07, 1.03, BELT_Z + 0.014))
    ws_a, ws_b = Vector((0, 0.975, BELT_Z - 0.025)), Vector((0, 0.355, ROOF_Z))
    up = (ws_b - ws_a).normalized()
    nrm = Vector((1, 0, 0)).cross(up)
    for px, length in ((-0.22, 0.55), (0.40, 0.50)):
        base = ws_a + up * 0.07 + nrm * 0.012
        m = G.basis(Vector((px, base.y, base.z)), (1, 0, 0), up, nrm)
        trim.add(G.box((length, 0.012, 0.008), r=0.003), matrix=m @ G.xf((-length / 2, 0, 0)))
        trim.add(G.box((length * 0.95, 0.008, 0.016), r=0.003), matrix=m @ G.xf((-length / 2, 0.02, 0.006)))
        trim.add(G.cyl(0.018, 0.02, segs=16), matrix=m @ G.xf((0, 0, 0)))
    # stubby antenna
    trim.add(G.cyl(0.004, 0.22, r2=0.0025, segs=8), loc=(0.93, 1.85, BELT_Z + 0.11), rot=(-0.25, 0, 0))
    trim.add(G.cyl(0.012, 0.02, segs=12), loc=(0.93, 1.83, BELT_Z + 0.008))
    trim.build(col, M)
    chrome.build(col, M)

    badges = G.Part("BADGE_SIDES", "Chrome", smooth=30)
    red_badges = G.Part("BADGE_SIDES_Z71", "Caliper_Red", smooth=30)
    for s in (-1, 1):
        n = Vector((s, 0, 0))
        right = Vector((0, 0, 1)).cross(n)
        badges.add(G.text("TWIN TURBO", size=0.032, depth=0.003), matrix=G.basis((s * (BODY_X + 0.001), -2.12, 0.80),
                                                                                  right, (0, 0, 1), n))
        red_badges.add(G.text("Z71", size=0.10, depth=0.004), matrix=G.basis((s * (BODY_X + 0.001), -2.12, 0.90),
                                                                             right, (0, 0, 1), n))
    # pinstripes / graphics from the reference: roof stripes + red/white wedges on the rear bed sides
    stripe_r = G.Part("DECAL_STRIPES_RED", "Caliper_Red", smooth=0)
    stripe_w = G.Part("DECAL_STRIPES_WHITE", "Decal_White", smooth=0)
    roof_z = ROOF_Z + 0.019
    for x in (-0.09, 0.09):
        stripe_r.add(G.box((0.022, 0.70, 0.002)), loc=(x, -0.01, roof_z))
    for x in (-0.06, 0.06):
        stripe_w.add(G.box((0.012, 0.70, 0.002)), loc=(x, -0.01, roof_z))
    for s in (-1, 1):
        for part, off, wd in ((stripe_r, 0.0, 0.05), (stripe_w, 0.07, 0.02)):
            wedge = [(REAR_Y + 0.05, BELT_Z - 0.03 - off), (REAR_Y + 0.21, BELT_Z - 0.03 - off),
                     (REAR_Y + 0.05, BELT_Z - 0.03 - off - 0.15)]
            part.add(G.prism(wedge, 0.002, axis="X"), loc=(s * (BODY_X + 0.0015), 0, 0))
        stripe_r.add(G.box((0.004, 0.08, 0.006)), loc=(s * 1.206, 0.80, BELT_Z + 0.115))   # mirror accent
    for p in (badges, red_badges, stripe_r, stripe_w):
        p.build(col, M)


def rear(col, M):
    housing = G.Part("LAMP_TAIL_HOUSINGS", "Gloss_Black", smooth=40)
    red = G.Part("LAMP_TAIL_LENSES", "Lens_Red", smooth=30)
    clear = G.Part("LAMP_REVERSE_LENSES", "Lens_Clear", smooth=30)
    refl = G.Part("LAMP_INNER_TAIL_REFLECTORS", "Reflector", smooth=30)
    tails = {s: G.Part(f"LIGHT_TAIL_{'L' if s < 0 else 'R'}", "Light_Tail", smooth=40) for s in (-1, 1)}
    yb = REAR_Y
    for s in (-1, 1):
        xc = s * 0.925
        housing.add(G.box((0.11, 0.05, 0.44), r=0.014), loc=(xc, yb - 0.012, 0.79))
        refl.add(G.box((0.095, 0.004, 0.42), r=0.008), loc=(xc, yb - 0.038, 0.79))
        red.add(G.box((0.10, 0.008, 0.31), r=0.004), loc=(xc, yb - 0.05, 0.835))
        for zc in (0.94, 0.83, 0.72):                      # round lamp elements behind the red lens
            refl.add(G.lathe([(0.0, 0.0), (0.040, 0.0), (0.042, 0.012), (0.0, 0.012)], segs=32, uv=False),
                     loc=(xc, yb - 0.040, zc), rot=(0, 0, math.pi / 2))
            tails[s].add(G.lathe([(0.0, 0.0), (0.030, 0.0), (0.030, 0.004), (0.0, 0.006)], segs=32, uv=False),
                         loc=(xc, yb - 0.043, zc), rot=(0, 0, -math.pi / 2))
        clear.add(G.box((0.10, 0.008, 0.09), r=0.004), loc=(xc, yb - 0.05, 0.62))
    # third brake light on the cab
    housing.add(G.box((0.32, 0.045, 0.045), r=0.012), loc=(0, CAB_BACK_Y + 0.00, ROOF_Z - 0.045))
    red.add(G.box((0.30, 0.006, 0.03), r=0.004), loc=(0, CAB_BACK_Y - 0.021, ROOF_Z - 0.045))
    b3 = G.Part("LIGHT_BRAKE3", "Light_Tail", smooth=0)
    b3.add(G.box((0.28, 0.004, 0.02)), loc=(0, CAB_BACK_Y - 0.0185, ROOF_Z - 0.045))
    for p in (housing, red, clear, refl, b3, *tails.values()):
        p.build(col, M)

    bumper = G.Part("REAR_BUMPER", "Paint_Black", smooth=40)
    bumper.add(G.box((2.02, 0.17, 0.25), r=0.045), loc=(0, yb - 0.09, 0.40))
    pad = G.Part("REAR_STEP_PAD", "Bed_Liner", smooth=0, uv_scale=6)
    pad.add(G.box((1.30, 0.11, 0.008), r=0.003), loc=(0, yb - 0.10, 0.527))
    plate = G.Part("REAR_PLATE", "Plate", smooth=0)
    plate.add(G.box((0.31, 0.004, 0.155), r=0.008), loc=(0, yb - 0.177, 0.385))
    trim = G.Part("REAR_TRIM", "Gloss_Black", smooth=40)
    trim.add(G.box((0.33, 0.01, 0.175), r=0.012), loc=(0, yb - 0.172, 0.385))
    carbon = G.Part("REAR_DIFFUSER", "Carbon", smooth=30, uv_scale=8)
    carbon.add(G.box((1.60, 0.32, 0.012)), loc=(0, yb - 0.04, 0.275), rot=(-0.08, 0, 0))
    for i in range(7):
        x = -0.66 + i * 0.22
        fin = G.fillet_poly([(yb - 0.20, 0.28), (yb + 0.12, 0.28), (yb + 0.12, 0.30), (yb - 0.20, 0.36)], 0.01, k=3)
        carbon.add(G.prism(fin, 0.008, axis="X"), loc=(x, 0, 0))
    for p in (bumper, pad, trim, carbon):
        p.build(col, M)
    # plate needs its own planar UV (texture faces -Y)
    G.planar_uv(plate.bm, (0, yb - 0.177, 0.385), (1, 0, 0), (0, 0, 1), 0.31, 0.155)
    plate.build(col, M)


def build(col, M):
    headlamps(col, M)
    grille(col, M)
    bumper_front(col, M)
    intercooler(col, M)
    tow_straps(col, M)
    markers_mirrors_trim(col, M)
    rear(col, M)
