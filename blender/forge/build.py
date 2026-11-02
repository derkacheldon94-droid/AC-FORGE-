"""Orchestrates the build: materials -> parts -> LODs -> export -> renders."""

import importlib
import os

import bpy

from . import materials

MODULES = ["body", "front_rear", "wheels", "engine", "bed", "interior", "chassis"]
CAR_ID = "acf_blackout_pickup"


def run(out_dir, render=False, quick=False, lods=True, views=None, only=None):
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    col = scene.collection
    from . import wheels
    M = materials.build_library(os.path.join(out_dir, "texture"), tyre_band=wheels.tyre_band())

    for name in MODULES:
        if only and name not in only:
            continue
        try:
            mod = importlib.import_module(f"forge.{name}")
        except ModuleNotFoundError:
            print("skip (not written yet):", name)
            continue
        print("building", name, flush=True)
        mod.build(col, M)

    from . import export
    export.finish(out_dir, CAR_ID, lods=lods and not only)

    if render:
        from . import render as R
        R.render(out_dir, views=views, samples=24 if quick else 64, res=(960, 600) if quick else (1440, 900))
