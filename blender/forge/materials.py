"""Materials + procedurally painted textures (PIL/numpy), one PNG per material."""

import math
import os

import bpy  # noqa: F401
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_COND = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
if not os.path.exists(FONT_COND):
    FONT_COND = FONT_BOLD

RNG = np.random.default_rng(7)


def _font(size, path=FONT_BOLD):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _rgb(c):
    return tuple(int(max(0, min(1, x)) ** (1 / 2.2) * 255) for x in c)  # linear -> sRGB


def _noise(size, scale=1.0, blur=0):
    n = RNG.normal(0, 1, (size, size)).astype(np.float32)
    if blur:
        img = Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
        n = (np.asarray(img).astype(np.float32) - 128) / 40
    return n * scale


def _solid(rgb, size=256, noise=0.0, blur=0):
    base = np.array(_rgb(rgb), np.float32)[None, None, :] * np.ones((size, size, 1), np.float32)
    if noise:
        base += _noise(size, noise * 255, blur)[..., None]
    return Image.fromarray(base.clip(0, 255).astype(np.uint8))


# ---------------------------------------------------------------- texture painters
def tex_carbon(size=1024, tows=16):
    img = np.zeros((size, size, 3), np.float32)
    t = size // tows
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = xx // t, yy // t
    # 2x2 twill: weave direction alternates on a diagonal staircase
    horiz = ((cx + cy // 2) % 2 == 0)
    fx, fy = (xx % t) / t, (yy % t) / t
    shade_h = 0.55 + 0.45 * np.sin(fy * math.pi)
    shade_v = 0.55 + 0.45 * np.sin(fx * math.pi)
    shade = np.where(horiz, shade_h, shade_v)
    fibre = 0.9 + 0.1 * np.sin((np.where(horiz, xx, yy)) * 1.7)
    v = 14 + 34 * shade * fibre
    img[...] = v[..., None]
    img[..., 2] += 3
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def tex_brushed(rgb, size=512, vertical=False):
    n = RNG.normal(0, 1, (size, 1)).astype(np.float32) * np.ones((1, size), np.float32)
    n = n + RNG.normal(0, 0.4, (size, size))
    if vertical:
        n = n.T
    base = np.array(_rgb(rgb), np.float32)
    img = base[None, None, :] + n[..., None] * 9
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def tex_lines(rgb_a, rgb_b, size=512, period=8, duty=0.5, vertical=False):
    yy = np.arange(size)[:, None] * np.ones((1, size))
    if vertical:
        yy = yy.T
    m = ((yy % period) / period) < duty
    a, b = np.array(_rgb(rgb_a), np.float32), np.array(_rgb(rgb_b), np.float32)
    img = np.where(m[..., None], a, b)
    return Image.fromarray(img.astype(np.uint8))


def tex_hex(size=512, cells=12):
    img = Image.new("RGB", (size, size), _rgb((0.004, 0.004, 0.004)))
    d = ImageDraw.Draw(img)
    r = size / cells / 2
    h = r * math.sqrt(3)
    for row in range(-1, int(size / h) + 2):
        for col in range(-1, cells + 2):
            cx = col * 2 * r + (r if row % 2 else 0)
            cy = row * h
            pts = [(cx + 0.82 * r * math.cos(math.pi / 6 + k * math.pi / 3),
                    cy + 0.82 * r * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(6)]
            d.polygon(pts, fill=_rgb((0.025, 0.025, 0.027)))
    return img


def tex_weave(rgb, size=512, period=12):
    yy, xx = np.mgrid[0:size, 0:size]
    a = np.sin((xx + yy) * math.pi / period)
    b = np.sin((xx - yy) * math.pi / period)
    v = 0.75 + 0.25 * np.maximum(a, b)
    img = np.array(_rgb(rgb), np.float32)[None, None, :] * v[..., None]
    img += RNG.normal(0, 4, (size, size, 1))
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def tex_fabric(rgb, size=512):
    yy, xx = np.mgrid[0:size, 0:size]
    v = 0.85 + 0.08 * np.sin(xx * 1.9) * np.sin(yy * 1.9) + RNG.normal(0, 0.05, (size, size))
    stitch = ((yy % 128) < 2) & ((xx // 6) % 2 == 0)
    img = np.array(_rgb(rgb), np.float32)[None, None, :] * v[..., None]
    img[stitch] = np.array(_rgb((0.08, 0.08, 0.08)))
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def tex_disc(size=1024):
    """Brake rotor face (planar-mapped, disc centre = image centre, outer radius = edge)."""
    img = Image.new("RGB", (size, size), _rgb((0.30, 0.30, 0.31)))
    d = ImageDraw.Draw(img)
    c = size / 2
    yy, xx = np.mgrid[0:size, 0:size]
    rr = np.hypot(xx - c, yy - c) / c
    arr = np.asarray(img).astype(np.float32)
    arr += (np.sin(rr * 260) * 6)[..., None]                      # machining rings
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for ring, count, off in ((0.62, 18, 0.0), (0.74, 18, 0.5), (0.86, 18, 0.25)):
        for i in range(count):
            a = (i + off) * 2 * math.pi / count
            x, y = c + math.cos(a) * ring * c, c + math.sin(a) * ring * c
            rad = size * 0.011
            d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=_rgb((0.02, 0.02, 0.02)))
    for i in range(12):     # curved slots
        a0 = i * 2 * math.pi / 12
        pts = [(c + math.cos(a0 + t * 0.35) * (0.56 + 0.36 * t) * c,
                c + math.sin(a0 + t * 0.35) * (0.56 + 0.36 * t) * c) for t in np.linspace(0, 1, 12)]
        d.line(pts, fill=_rgb((0.06, 0.06, 0.06)), width=max(2, size // 220))
    return img


def tex_gauge(size=512, label="RPM x1000", maxv=9, redline=7.2):
    img = Image.new("RGB", (size, size), (8, 8, 9))
    d = ImageDraw.Draw(img)
    c = size / 2
    d.ellipse((4, 4, size - 4, size - 4), outline=(160, 160, 165), width=6)
    a0, a1 = math.radians(135), math.radians(405)
    for i in range(maxv * 5 + 1):
        v = i / 5
        a = a0 + (a1 - a0) * v / maxv
        major = i % 5 == 0
        r0 = c * (0.78 if major else 0.85)
        col = (220, 30, 30) if v >= redline else (235, 235, 235)
        d.line((c + math.cos(a) * r0, c + math.sin(a) * r0, c + math.cos(a) * c * 0.92, c + math.sin(a) * c * 0.92),
               fill=col, width=6 if major else 3)
        if major:
            f = _font(int(size * 0.09))
            tx, ty = c + math.cos(a) * c * 0.62, c + math.sin(a) * c * 0.62
            d.text((tx, ty), str(int(v)), font=f, fill=col, anchor="mm")
    d.text((c, c * 1.45), label, font=_font(int(size * 0.05)), fill=(180, 180, 180), anchor="mm")
    d.text((c, c * 0.62), "FORGE", font=_font(int(size * 0.06)), fill=(200, 30, 30), anchor="mm")
    return img


def tex_plate(w=1024, h=512, txt="FORGE 01"):
    img = Image.new("RGB", (w, h), (232, 232, 228))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, w - 8, h - 8), radius=30, outline=(20, 20, 20), width=10)
    d.text((w / 2, h * 0.16), "AC FORGE GARAGE", font=_font(int(h * 0.11)), fill=(170, 20, 20), anchor="mm")
    d.text((w / 2, h * 0.58), txt, font=_font(int(h * 0.42), FONT_COND), fill=(15, 15, 20), anchor="mm")
    for x in (0.12, 0.88):
        d.ellipse((w * x - 14, h * 0.5 - 14, w * x + 14, h * 0.5 + 14), fill=(120, 120, 120))
    return img


def tex_rim_blur(size=512):
    """Spinning-rim look: opaque hub, translucent red spoke zone, polished lip ring."""
    yy, xx = np.mgrid[0:size, 0:size]
    c = size / 2
    r = np.hypot(xx - c, yy - c) / c
    img = np.zeros((size, size, 4), np.float32)
    red = np.array(_rgb((0.40, 0.012, 0.012)), np.float32)
    lip = np.array(_rgb((0.78, 0.78, 0.80)), np.float32)
    img[..., :3] = red
    img[..., 3] = np.where(r < 0.36, 255, np.where(r < 0.82, 150 + 40 * np.sin(r * 40), 255))
    img[(r >= 0.82) & (r <= 1.0), :3] = lip
    img[r > 1.0, 3] = 0
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA")


def tex_tyre(w=2048, h=512, v_side_out=(0.02, 0.27), flip=True):
    """Tyre atlas: u around the tyre, v along the lathe profile. Lettering on the outer sidewall band."""
    base = np.full((h, w, 3), 18, np.float32)
    base += RNG.normal(0, 2.0, (h, w, 1))
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    v0, v1 = int(v_side_out[0] * h), int(v_side_out[1] * h)
    band = v1 - v0
    txt_img = Image.new("RGB", (w, band), (18, 18, 18))
    td = ImageDraw.Draw(txt_img)
    f = _font(int(band * 0.42), FONT_COND)
    fs = _font(int(band * 0.18), FONT_BOLD)
    for k in range(2):
        x0 = k * w / 2
        td.text((x0 + w * 0.13, band * 0.5), "FORGE", font=f, fill=(105, 105, 108), anchor="mm")
        td.text((x0 + w * 0.32, band * 0.5), "SEMI-SLICK  R-COMPOUND", font=fs, fill=(88, 88, 90), anchor="mm")
        td.text((x0 + w * 0.43, band * 0.5), "275/35 R20", font=fs, fill=(88, 88, 90), anchor="mm")
    if flip:   # lathe UVs run counter-clockwise seen from outside: mirror so text reads clockwise
        txt_img = txt_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    img.paste(txt_img, (0, h - v1))   # image rows run top-down, UV v runs bottom-up
    return img


# ---------------------------------------------------------------- material factory
class MaterialLib:
    def __init__(self, tex_dir):
        self.tex_dir = tex_dir
        os.makedirs(tex_dir, exist_ok=True)
        self.m = {}

    def __getitem__(self, k):
        return self.m[k]

    def add(self, name, img, metal=0.0, rough=0.5, emit=None, emit_k=0.0, alpha=1.0, base_tint=None):
        path = os.path.join(self.tex_dir, name + ".png")
        rgba = img.mode == "RGBA"
        if alpha < 1.0 and not rgba:
            img = img.convert("RGBA")
            a = Image.new("L", img.size, int(alpha * 255))
            img.putalpha(a)
        img.save(path)
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(path)
        tex.location = (-400, 200)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        if emit:
            bsdf.inputs["Emission Color"].default_value = (*emit, 1)
            bsdf.inputs["Emission Strength"].default_value = emit_k
        if rgba:
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
            try:
                m.surface_render_method = "BLENDED"
            except Exception:
                pass
        elif alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            try:
                m.surface_render_method = "BLENDED"
            except Exception:
                pass
        m.diffuse_color = (*(base_tint or (0.5, 0.5, 0.5)), alpha)
        self.m[name] = m
        return m


def build_library(tex_dir, tyre_band=(0.02, 0.27)):
    L = MaterialLib(tex_dir)
    # body
    L.add("Paint_Black", _solid((0.016, 0.018, 0.018), 512, noise=0.004), metal=0.35, rough=0.28)
    L.add("Trim_Black", _solid((0.010, 0.010, 0.010), 256, noise=0.006, blur=1), rough=0.55)
    L.add("Gloss_Black", _solid((0.006, 0.006, 0.006), 64), rough=0.12)
    L.add("Carbon", tex_carbon(), metal=0.2, rough=0.2)
    L.add("Grille_Mesh", tex_hex(), metal=0.3, rough=0.45)
    L.add("Bed_Liner", _solid((0.014, 0.014, 0.015), 512, noise=0.03, blur=1), rough=0.85)
    L.add("Rubber", _solid((0.012, 0.012, 0.012), 64), rough=0.8)
    # metals
    L.add("Chrome", _solid((0.85, 0.85, 0.87), 64), metal=1.0, rough=0.06)
    L.add("Metal_Polished", tex_brushed((0.78, 0.78, 0.80), 256), metal=1.0, rough=0.12)
    L.add("Brushed_Alu", tex_brushed((0.58, 0.59, 0.61)), metal=1.0, rough=0.32)
    L.add("Cast_Alu", _solid((0.48, 0.49, 0.50), 256, noise=0.03, blur=1), metal=0.9, rough=0.5)
    L.add("Engine_Dark", _solid((0.05, 0.05, 0.055), 256, noise=0.02, blur=1), metal=0.6, rough=0.55)
    L.add("Valve_Red", _solid((0.48, 0.025, 0.02), 256, noise=0.05, blur=0), metal=0.2, rough=0.45)
    L.add("Intercooler_Fins", tex_lines((0.55, 0.56, 0.57), (0.10, 0.10, 0.11), 512, period=6, duty=0.45),
          metal=0.8, rough=0.45)
    L.add("Heat_Wrap", tex_weave((0.55, 0.47, 0.32)), rough=0.8)
    L.add("Braided", tex_weave((0.55, 0.55, 0.57), period=5), metal=0.8, rough=0.4)
    L.add("Turbo_Hot", _solid((0.20, 0.16, 0.14), 256, noise=0.05, blur=1), metal=0.8, rough=0.5)
    L.add("Filter_Red", tex_lines((0.55, 0.03, 0.03), (0.30, 0.01, 0.01), 256, period=10, duty=0.5, vertical=True),
          rough=0.85)
    L.add("Heat_Gold", tex_brushed((0.75, 0.55, 0.18), 256), metal=1.0, rough=0.35)
    L.add("Silicone_Red", _solid((0.45, 0.02, 0.02), 64), rough=0.6)
    L.add("Thread_Alu", tex_lines((0.6, 0.6, 0.62), (0.25, 0.25, 0.27), 256, period=4, duty=0.5),
          metal=1.0, rough=0.3)
    L.add("Anodized_Blue", _solid((0.02, 0.06, 0.45), 64), metal=0.7, rough=0.3)
    L.add("Anodized_Black", _solid((0.02, 0.02, 0.022), 64), metal=0.7, rough=0.35)
    # wheels / brakes
    L.add("Rim_Red", _solid((0.40, 0.012, 0.012), 128, noise=0.005), metal=0.55, rough=0.25)
    L.add("Rim_Lip", tex_brushed((0.80, 0.80, 0.82), 256, vertical=True), metal=1.0, rough=0.1)
    L.add("Rim_Blur", tex_rim_blur(), metal=0.5, rough=0.3)
    L.add("Tyre", tex_tyre(v_side_out=tyre_band), rough=0.92)
    L.add("Brake_Disc", tex_disc(), metal=0.95, rough=0.35)
    L.add("Caliper_Red", _solid((0.55, 0.02, 0.02), 64), rough=0.25)
    L.add("Decal_White", _solid((0.85, 0.85, 0.85), 32), rough=0.4)
    L.add("Spring_Red", _solid((0.50, 0.025, 0.02), 64), metal=0.2, rough=0.3)
    # interior
    L.add("Seat_Red", tex_fabric((0.42, 0.02, 0.02)), rough=0.85)
    L.add("Interior_Black", _solid((0.02, 0.02, 0.02), 256, noise=0.01, blur=1), rough=0.75)
    L.add("Carpet", _solid((0.015, 0.015, 0.016), 512, noise=0.04), rough=1.0)
    L.add("Strap_Red", tex_lines((0.45, 0.02, 0.02), (0.32, 0.01, 0.01), 128, period=3, duty=0.6), rough=0.7)
    L.add("Gauge_Tach", tex_gauge(), rough=0.3)
    L.add("Gauge_Speed", tex_gauge(label="MPH", maxv=20, redline=99), rough=0.3)
    L.add("Gauge_Boost", tex_gauge(label="BOOST PSI", maxv=6, redline=4.5), rough=0.3)
    L.add("Plate", tex_plate(), rough=0.4)
    # glass & lights
    L.add("Glass", _solid((0.04, 0.05, 0.06), 32), rough=0.03, alpha=0.22)
    L.add("Lens_Clear", _solid((0.6, 0.62, 0.65), 32), rough=0.03, alpha=0.18)
    L.add("Lens_Red", _solid((0.5, 0.01, 0.01), 32), rough=0.05, alpha=0.65)
    L.add("Lens_Amber", _solid((0.8, 0.35, 0.02), 32), rough=0.05, alpha=0.7)
    L.add("Mirror_Glass", _solid((0.7, 0.72, 0.75), 32), metal=1.0, rough=0.02)
    L.add("Reflector", _solid((0.75, 0.75, 0.78), 64), metal=1.0, rough=0.15)
    L.add("Light_Head", _solid((1.0, 1.0, 1.0), 32), emit=(0.85, 0.92, 1.0), emit_k=8.0)
    L.add("Light_Tail", _solid((0.6, 0.02, 0.02), 32), emit=(1.0, 0.04, 0.02), emit_k=3.0)
    L.add("Light_Marker", _solid((0.9, 0.4, 0.02), 32), emit=(1.0, 0.45, 0.02), emit_k=1.0)
    return L
