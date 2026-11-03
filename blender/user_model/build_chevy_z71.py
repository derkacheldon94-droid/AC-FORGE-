"""
Turn the user-supplied sculpted Silverado model (source/chevy_z71.kn5) into a complete Assetto Corsa car
for Content Manager: content/cars/chevy_z71 + dist/chevy_z71.zip.

The source geometry is kept as delivered (same mesh, normals and UVs); this script only
  - gives the three materials proper paint / rubber / metal shading values,
  - fits LOD A under the project's 200,000 in-game vertex limit (VERTEX_BUDGET in forge/export.py;
    the wheels are left untouched, the body is collapse-decimated),
  - writes LOD B/C/D for distance,
  - builds data/ (physics fitted to this model's wheelbase, track, tyre size and body), UI, skins, zip.

Run (Blender 4.2+ or the bpy module, plus pillow and numpy):
  python blender/user_model/build_chevy_z71.py [--render]
"""

import os
import re
import shutil
import sys

import bpy  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "blender"))

from forge import export as E  # noqa: E402
from forge import kn5, kn5_import, package as PK  # noqa: E402

CAR = "chevy_z71"
SRC = os.path.join(HERE, "source", "chevy_z71.kn5")
OUT = os.path.join(HERE, "out")
CAR_DIR = os.path.join(REPO, "content", "cars", CAR)
TEMPLATE = os.path.join(REPO, "content", "cars", "acf_blackout_pickup", "data")

# measured from the model (AC frame: x right, y up, z forward; ground y = 0)
WHEEL_Y = 0.492            # wheel centre height
FRONT_Z, REAR_Z = 1.874, -1.218
HALF_TRACK = 0.913
TYRE_R, RIM_R = 0.465, 0.340
CG_H = 0.60
CG_FRONT = 0.55            # share of weight on the front axle
WB = FRONT_Z - REAR_Z
CG_Z = REAR_Z + CG_FRONT * WB

kn5.SHADING.update({"Silver_Paint": (0.50, 0.55, 0.85, 220), "Tire_Rubber": (0.40, 0.55, 0.05, 6),
                    "Wheel_Alloy": (0.55, 0.80, 0.90, 180)})


def set_key(text, section, key, value):
    """Replace KEY=value inside [SECTION] of an ini text (keeps comments elsewhere)."""
    out, cur, done = [], None, False
    for line in text.splitlines():
        m = re.match(r"\s*\[([^\]]+)\]", line)
        if m:
            cur = m.group(1)
        if cur == section and re.match(rf"\s*{re.escape(key)}\s*=", line) and not done:
            line = f"{key}={value}"
            done = True
        out.append(line)
    if not done:
        raise KeyError(f"{section}/{key}")
    return "\n".join(out) + "\n"


def write_data():
    data = os.path.join(CAR_DIR, "data")
    if os.path.exists(data):
        shutil.rmtree(data)
    shutil.copytree(TEMPLATE, data)

    def patch(name, edits):
        p = os.path.join(data, name)
        t = open(p).read()
        for sec, key, val in edits:
            t = set_key(t, sec, key, val)
        open(p, "w", newline="\n").write(t)

    f = lambda v: f"{v:.3f}"  # noqa: E731
    patch("car.ini", [
        ("INFO", "SCREEN_NAME", "Chevrolet Silverado Z71 Widebody (Sculpt)"),
        ("INFO", "SHORT_NAME", "Z71SC"),
        ("BASIC", "GRAPHICS_OFFSET", f"0,{f(-CG_H)},{f(-CG_Z)}"),
        ("BASIC", "INERTIA", "2.10,1.50,5.40"),
        ("GRAPHICS", "DRIVEREYES", "-0.42,1.42,0.00"),
        ("GRAPHICS", "MIRROR_POSITION", "0,1.65,0.70"),
        ("GRAPHICS", "BUMPER_CAMERA_POS", "0,0.55,3.00"),
        ("GRAPHICS", "BONNET_CAMERA_POS", "0,1.50,1.25"),
        ("FUELTANK", "POSITION", f"0,-0.10,{f(-1.90 - CG_Z)}"),
    ])
    patch("suspensions.ini", [
        ("BASIC", "WHEELBASE", f(WB)), ("BASIC", "CG_LOCATION", f"{CG_FRONT:.2f}"),
        ("FRONT", "BASEY", f(WHEEL_Y - CG_H)), ("FRONT", "TRACK", f(2 * HALF_TRACK)),
        ("FRONT", "WBTYRE_TOP", "0.788,0.16,0.0"), ("FRONT", "WBTYRE_BOTTOM", "0.858,-0.12,0.0"),
        ("FRONT", "WBTYRE_STEER", "0.823,-0.06,-0.14"),
        ("REAR", "BASEY", f(WHEEL_Y - CG_H)), ("REAR", "TRACK", f(2 * HALF_TRACK)),
        ("REAR", "WBTYRE_TOP", "0.788,0.15,0.0"), ("REAR", "WBTYRE_BOTTOM", "0.858,-0.12,0.0"),
        ("REAR", "WBTYRE_STEER", "0.843,-0.05,-0.18"),
    ])
    patch("tyres.ini", [
        ("FRONT", "RADIUS", f(TYRE_R)), ("FRONT", "RIM_RADIUS", f(RIM_R)), ("FRONT", "WIDTH", "0.330"),
        ("FRONT", "ANGULAR_INERTIA", "2.40"),
        ("REAR", "RADIUS", f(TYRE_R)), ("REAR", "RIM_RADIUS", f(RIM_R)), ("REAR", "WIDTH", "0.360"),
        ("REAR", "ANGULAR_INERTIA", "2.60"),
    ])
    # bigger tyres: keep the same road speed per gear
    patch("drivetrain.ini", [("GEARS", "FINAL", f"{3.73 * TYRE_R / 0.355:.3f}")])
    cz = (2.946 - 2.354) / 2 - CG_Z
    open(os.path.join(data, "colliders.ini"), "w", newline="\n").write(
        "; Boxes relative to the CG: CENTRE = x,y,z ; SIZE = width,height,length\n"
        f"[COLLIDER_0]\nCENTRE=0,{f(0.675 - CG_H)},{f(cz)}\nSIZE=2.05,1.05,5.25\nGROUND_ENABLE=1\n\n"
        f"[COLLIDER_1]\nCENTRE=0,{f(1.50 - CG_H)},{f(0.325 - CG_Z)}\nSIZE=1.85,0.60,1.15\nGROUND_ENABLE=0\n")
    open(os.path.join(data, "lights.ini"), "w", newline="\n").write(
        "; The sculpted model is one joined body mesh, so it has no separate light meshes.\n[HEADER]\nVERSION=3\n")
    open(os.path.join(data, "lods.ini"), "w", newline="\n").write(
        "[COCKPIT_HR]\nDISTANCE_SWITCH=7.0\n\n"
        f"[LOD_0]\nFILE={CAR}.kn5\nIN=0\nOUT=14\n\n[LOD_1]\nFILE={CAR}_B.kn5\nIN=14\nOUT=40\n\n"
        f"[LOD_2]\nFILE={CAR}_C.kn5\nIN=40\nOUT=110\n\n[LOD_3]\nFILE={CAR}_D.kn5\nIN=110\nOUT=1500\n")
    open(os.path.join(data, "blurred_objects.ini"), "w", newline="\n").write(
        "; The sculpted wheels have no separate blurred-rim meshes.\n")
    open(os.path.join(data, "ambient_shadows.ini"), "w", newline="\n").write("[SETTINGS]\nWIDTH=1.22\nLENGTH=2.90\n")


def skins(render):
    from PIL import Image
    tex = os.path.join(OUT, "texture", "Silver_Paint.png")
    for skin, colour in (("silver_clay", None), ("blackout", (14, 14, 15))):
        d = os.path.join(CAR_DIR, "skins", skin)
        os.makedirs(d, exist_ok=True)
        if colour is None:
            shutil.copyfile(tex, os.path.join(d, "Silver_Paint.png"))
        else:
            Image.new("RGB", (4, 4), colour).save(os.path.join(d, "Silver_Paint.png"))
        PK.write(os.path.join(d, "ui_skin.json"),
                 '{\n  "skinname": "%s",\n  "drivername": "",\n  "country": "",\n  "team": "",\n  "number": ""\n}\n'
                 % ("Silver Clay" if colour is None else "Blackout"))
        PK.livery(os.path.join(d, "livery.png"))
        src = os.path.join(OUT, f"preview_{skin}.png")
        if os.path.exists(src):
            im = Image.open(src).convert("RGB")
            w, h = im.size
            cw = int(w * 0.84)
            ch = int(cw * 575 / 1022)
            x0, y0 = int(w * 0.08), int(h * 0.20)
            im.crop((x0, y0, x0 + cw, y0 + ch)).resize((1022, 575), Image.LANCZOS).save(
                os.path.join(d, "preview.jpg"), quality=92)


def render_skins():
    from forge import render as R
    R.VIEWS["skin"] = ((-6.0, 7.2, 2.6), (0, 0.4, 0.8), 40)
    paint = bpy.data.materials["Silver_Paint"]
    node = next(n for n in paint.node_tree.nodes if n.type == "TEX_IMAGE")
    silver = node.image
    black = bpy.data.images.new("Blackout_Preview", 4, 4)
    black.pixels = [0.006, 0.006, 0.007, 1.0] * 16
    first = True
    for skin, img in (("silver_clay", silver), ("blackout", black)):
        node.image = img
        if first:
            R.render(OUT, views=["skin"], samples=64, res=(1440, 900))
            first = False
        else:
            bpy.context.scene.render.filepath = os.path.join(OUT, "preview_skin.png")
            bpy.ops.render.render(write_still=True)
        os.replace(os.path.join(OUT, "preview_skin.png"), os.path.join(OUT, f"preview_{skin}.png"))
    node.image = silver
    bpy.data.images.remove(black)


def main():
    do_render = "--render" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CAR_DIR, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kn5_import.import_kn5(SRC, os.path.join(OUT, "texture"))
    print("source in-game vertices:", f"{sum(E.game_vertices().values()):,}", flush=True)

    E.enforce_budget()
    E.stats("LOD A")
    print("kn5 LOD A:", kn5.export(os.path.join(CAR_DIR, f"{CAR}.kn5"), CAR), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{CAR}.blend"))
    if do_render:
        render_skins()
    for lod, ratio in (("B", 0.40), ("C", 0.375), ("D", 0.33)):
        for o in E.meshes():
            E.decimate(o, ratio)
        E.stats(f"LOD {lod}")
        print(f"kn5 LOD {lod}:", kn5.export(os.path.join(CAR_DIR, f"{CAR}_{lod}.kn5"), CAR), flush=True)

    write_data()
    os.makedirs(os.path.join(CAR_DIR, "ui"), exist_ok=True)
    PK.badge(os.path.join(CAR_DIR, "ui", "badge.png"))
    PK.shadows(CAR_DIR)
    PK.setup_ini(os.path.join(CAR_DIR, "data", "setup.ini"))
    tq, pw = PK.curves(CAR_DIR)
    PK.ui_json(CAR_DIR, CAR, int(max(p[1] for p in pw)), int(max(t[1] for t in tq)), tq, pw)
    import json
    ui_path = os.path.join(CAR_DIR, "ui", "ui_car.json")
    ui = json.load(open(ui_path))
    ui["name"] = "Chevrolet Silverado Z71 Widebody (Sculpt)"
    ui["description"] = ("Sculpted widebody 1994 Silverado Z71 regular cab with a hood scoop, oversized multi-spoke "
                         "wheels and side-exit exhaust ahead of the rear wheels. Model by the owner; physics, LODs "
                         "and packaging by AC Forge. RWD, twin-turbo V8, 6-speed manual.")
    PK.write(ui_path, json.dumps(ui, indent=2))
    skins(do_render)
    print("zip:", PK.make_zip(CAR_DIR, CAR, os.path.join(REPO, "dist")), flush=True)


if __name__ == "__main__":
    main()
