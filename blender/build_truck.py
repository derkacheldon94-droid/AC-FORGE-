"""
AC Forge - Blackout Pickup (high detail): procedural 3D model builder for Assetto Corsa.

Builds the lowered, wide-body, twin-turbo regular-cab pickup from the concept art,
then exports for the AC Editor (ksEditor):
  out/acf_blackout_pickup.fbx        LOD A - full detail (+ COCKPIT_LR low-res interior)
  out/acf_blackout_pickup_B/C/D.fbx  LOD B / C / D for distance (see data/lods.ini)
  out/acf_blackout_pickup.blend      editable Blender scene
  out/acf_blackout_pickup.glb        quick look in any 3D viewer
  out/textures/*.png                 textures referenced by the FBX files
  out/preview_*.png                  renders (with --render)

Run with Blender 4.2+ (tested on 5.1), or the `bpy` module (also needs pillow + numpy):
  blender -b -P blender/build_truck.py -- [--render] [--quick] [--views side,front_quarter] [--no-lods]

Modelling space: +Y forward, +Z up, -X = car's LEFT (US driver side). Ground z = 0,
origin = middle of the wheelbase. FBX is exported Y-up / Z-forward as AC expects.
"""

import os
import sys
import time

import bpy  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from forge import build  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
opts = {
    "render": "--render" in argv,
    "quick": "--quick" in argv,
    "lods": "--no-lods" not in argv,
    "views": None,
    "only": None,
}
if "--views" in argv:
    opts["views"] = argv[argv.index("--views") + 1].split(",")
if "--only" in argv:
    opts["only"] = argv[argv.index("--only") + 1].split(",")

t0 = time.time()
build.run(os.path.join(HERE, "out"), **opts)
print(f"done in {time.time() - t0:.0f}s")
