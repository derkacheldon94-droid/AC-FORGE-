"""Content Manager / Assetto Corsa car-folder assets that are not geometry:
badge, livery swatch, ambient body shadow, tyre shadows, ambient_shadows.ini, setup.ini, blur config,
ui_car.json. Everything is generated, nothing is copied from another car."""

import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SKIN = "blackout_red"


def _font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except OSError:
        return ImageFont.load_default()


def badge(path, size=128):
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, s - 8, s - 8), fill=(14, 14, 16, 255), outline=(190, 20, 24, 255), width=s // 18)
    d.text((s / 2, s * 0.40), "FORGE", font=_font(int(s * 0.19)), fill=(235, 235, 235, 255), anchor="mm")
    d.text((s / 2, s * 0.62), "Z71", font=_font(int(s * 0.25)), fill=(210, 30, 30, 255), anchor="mm")
    img.resize((size, size), Image.LANCZOS).save(path)


def livery(path, size=64):
    s = size * 4
    img = Image.new("RGBA", (s, s), (12, 12, 13, 255))
    d = ImageDraw.Draw(img)
    for x, w, c in ((s * 0.38, s * 0.07, (200, 25, 28)), (s * 0.54, s * 0.035, (235, 235, 235))):
        d.rectangle((x, 0, x + w, s), fill=c + (255,))
    d.rectangle((2, 2, s - 3, s - 3), outline=(60, 60, 64, 255), width=6)
    img.resize((size, size), Image.LANCZOS).save(path)


def _soft_rect(path, w, h, box, radius, blur, alpha, size=None):
    big = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(big).rounded_rectangle([c * 2 for c in box], radius=radius * 2, fill=alpha)
    big = big.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.putalpha(big)
    img.save(path)


def shadows(car_dir):
    _soft_rect(os.path.join(car_dir, "body_shadow.png"), 512, 512, (70, 36, 442, 476), 70, 26, 235)
    _soft_rect(os.path.join(car_dir, "tyre_1_shadow.png"), 64, 64, (14, 6, 50, 58), 8, 4, 200)
    _soft_rect(os.path.join(car_dir, "tyre_2_shadow.png"), 64, 64, (11, 6, 53, 58), 8, 4, 200)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(text)


SETUP = """[DISPLAY_METHOD]
SHOW_CLICKS=1

[GEARS]
USE_GEARSET=0

; ---- TYRES -------------------------------------------------------------
{pressure}
; ---- ALIGNMENT ---------------------------------------------------------
{align}
; ---- GENERIC -----------------------------------------------------------
[FUEL]
SHOW_CLICKS=0
TAB=GENERIC
NAME=Fuel
MIN=5
MAX=80
STEP=1
POS_X=0.5
POS_Y=0
HELP=HELP_FUEL

[FRONT_BIAS]
SHOW_CLICKS=0
TAB=GENERIC
NAME=Brake Bias
MIN=50
MAX=75
STEP=1
POS_X=0.5
POS_Y=1
HELP=HELP_BRAKE_BIAS

[BRAKE_POWER_MULT]
SHOW_CLICKS=0
TAB=GENERIC
NAME=Brake power
MIN=80
MAX=100
STEP=1
POS_X=0.5
POS_Y=2
HELP=HELP_BRAKE_POWER_MULT
"""


def setup_ini(path):
    corners = (("LF", 0, 2), ("RF", 1, 2), ("LR", 0, 4), ("RR", 1, 4))
    pressure = "".join(
        f"[PRESSURE_{c}]\nSHOW_CLICKS=0\nTAB=TYRES\nNAME=Pressure {c}\nMIN=20\nMAX=40\nSTEP=1\nPOS_X={x}\nPOS_Y={y}\n"
        f"HELP=HELP_{c}_PRESSURE\n\n" for c, x, y in corners)
    align = ""
    for c, x, y in (("LF", 0, 0), ("RF", 1, 0), ("LR", 0, 3), ("RR", 1, 3)):
        align += (f"[CAMBER_{c}]\nSHOW_CLICKS=0\nTAB=ALIGNMENT\nNAME=Camber {c}\nMIN=-5.0\nMAX=0.5\nSTEP=1\n"
                  f"POS_X={x}\nPOS_Y={y}\nHELP=HELP_{c}_CAMBER\n\n")
        align += (f"[TOE_OUT_{c}]\nSHOW_CLICKS=2\nTAB=ALIGNMENT\nNAME=Toe {c}\nMIN=-60\nMAX=70\nSTEP=10\n"
                  f"POS_X={x}\nPOS_Y={y + 1}\nHELP=HELP_{c}_TOE\n\n")
    write(path, SETUP.format(pressure=pressure, align=align))


def blur_ini(path):
    out = ["; Wheel blurring at speed is simulated by swapping 3D rims at different speeds (km/h).",
           "; WHEEL INDEXES: 0=LEFT FRONT  1=RIGHT FRONT  2=LEFT REAR  3=RIGHT REAR", ""]
    i = 0
    for idx, tag in enumerate(("LF", "RF", "LR", "RR")):
        out += [f"[OBJECT_{i}]", f"WHEEL_INDEX={idx}", f"NAME=WHEEL_{tag}_RIM", "MIN_SPEED=0", "MAX_SPEED=40", ""]
        out += [f"[OBJECT_{i + 1}]", f"WHEEL_INDEX={idx}", f"NAME=RIM_BLUR_{tag}", "MIN_SPEED=30", "MAX_SPEED=10000", ""]
        i += 2
    write(path, "\n".join(out))


def ambient_ini(path):
    write(path, "[SETTINGS]\nWIDTH=1.25\nLENGTH=2.75\n")


def ui_json(car_dir, car_id, peak_hp, peak_nm, torque, power):
    path = os.path.join(car_dir, "ui", "ui_car.json")
    try:
        ui = json.load(open(path))
    except (OSError, ValueError):
        ui = {}
    ui.update({
        "name": "Chevrolet Silverado Z71 1994 Twin Turbo",
        "brand": "Chevrolet",
        "class": "street",
        "country": "USA",
        "description": ("1994 Silverado Z71 short-bed regular cab on a carbon wide-body kit. Iron V8 in an open front bay "
                        "under a carbon twin-oval airbox; bed-mounted twin-turbo system with the exhaust exiting through "
                        "both sides of the box just ahead of the rear wheels. Red buckets with harnesses, roll cage, "
                        "strapped aluminium fuel cell in the open bed, 20-inch split-spoke wheels. RWD, 6-speed manual."),
        "tags": ["#Street", "rwd", "manual", "turbo", "pickup", "drift", "v8", "usa", "widebody"],
        "specs": {"bhp": f"{peak_hp} bhp", "torque": f"{peak_nm} Nm", "weight": "1580 kg", "topspeed": "~320 km/h",
                  "acceleration": "--", "pwratio": f"{1580 / peak_hp:.2f} kg/hp"},
        "torqueCurve": torque, "powerCurve": power, "year": 1994, "author": "AC Forge", "version": "0.2", "url": ""})
    ui.pop("range", None)
    ui.pop("parent", None)
    write(path, json.dumps(ui, indent=2))


def curves(car_dir):
    """Torque/power curves for the UI from data/power.lut plus the two turbos defined in engine.ini."""
    lut = []
    with open(os.path.join(car_dir, "data", "power.lut")) as f:
        for line in f:
            if "|" in line and not line.strip().startswith(";"):
                r, t = line.strip().split("|")[:2]
                lut.append((float(r), float(t)))
    boost, ref, gamma, limiter = 0.0, 4300.0, 2.6, 7200
    for ln in open(os.path.join(car_dir, "data", "engine.ini")):
        k, _, v = ln.split(";")[0].strip().partition("=")
        if k == "WASTEGATE":
            boost += float(v)
        elif k == "REFERENCE_RPM":
            ref = float(v)
        elif k == "GAMMA":
            gamma = float(v)
        elif k == "LIMITER":
            limiter = int(float(v))
    tq, pw = [], []
    for rpm, t in lut:
        if rpm < 1000 or rpm > limiter:
            continue
        nm = t * (1 + boost * min(1.0, (rpm / ref) ** gamma))
        tq.append([rpm, round(nm, 1)])
        pw.append([rpm, round(nm * rpm / 9549 * 1.341, 1)])
    return tq, pw


def previews(car_dir, out_dir):
    """Skin preview in Content Manager's size (1022x575), cropped from the front-quarter render."""
    src = os.path.join(out_dir, "preview_front_quarter.png")
    if not os.path.exists(src):
        return False
    im = Image.open(src).convert("RGB")
    w, h = im.size
    cw = int(w * 0.80)
    ch = int(cw * 575 / 1022)
    x0, y0 = int(w * 0.075), int(h * 0.20)
    im.crop((x0, y0, x0 + cw, y0 + ch)).resize((1022, 575), Image.LANCZOS).save(
        os.path.join(car_dir, "skins", SKIN, "preview.jpg"), quality=92)
    hero = os.path.join(car_dir, "ui", "preview_hero.jpg")
    if os.path.exists(hero):
        os.remove(hero)
    return True


def make_zip(car_dir, car_id, dist_dir):
    import zipfile
    os.makedirs(dist_dir, exist_ok=True)
    out = os.path.join(dist_dir, car_id + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _, files in os.walk(car_dir):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                z.write(full, os.path.join(car_id, os.path.relpath(full, car_dir)))
    return out


def all_assets(car_dir, car_id, tex_dir=None):
    os.makedirs(os.path.join(car_dir, "ui"), exist_ok=True)
    os.makedirs(os.path.join(car_dir, "skins", SKIN), exist_ok=True)
    if tex_dir and os.path.exists(os.path.join(tex_dir, "Paint_Black.png")):
        import shutil
        shutil.copyfile(os.path.join(tex_dir, "Paint_Black.png"), os.path.join(car_dir, "skins", SKIN, "Paint_Black.png"))
    badge(os.path.join(car_dir, "ui", "badge.png"))
    livery(os.path.join(car_dir, "skins", SKIN, "livery.png"))
    shadows(car_dir)
    setup_ini(os.path.join(car_dir, "data", "setup.ini"))
    blur_ini(os.path.join(car_dir, "data", "blurred_objects.ini"))
    ambient_ini(os.path.join(car_dir, "data", "ambient_shadows.ini"))
    tq, pw = curves(car_dir)
    ui_json(car_dir, car_id, int(max(p[1] for p in pw)), int(max(t[1] for t in tq)), tq, pw)
