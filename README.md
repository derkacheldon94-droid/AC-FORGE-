# AC Forge: '94 Silverado Z71 Twin Turbo

A high-detail **1994 Chevrolet Silverado Z71** regular cab for **Assetto Corsa**. The truck is slammed on riveted carbon wide-body flares. It has an iron V8 in an open front bay and a **rear bed-mounted twin-turbo system** whose exhaust exits **through both sides of the box, just ahead of the rear wheels**.

Everything is generated from code. The 3D model comes from Blender scripts in `blender/forge/`, and the physics are plain-text `.ini` files.

| | |
|---|---|
| ![front quarter](blender/out/preview_front_quarter.png) | ![rear quarter](blender/out/preview_rear_quarter.png) |
| ![engine bay](blender/out/preview_detail_engine.png) | ![bed twin turbo](blender/out/preview_detail_bed.png) |
| ![wheel and brakes](blender/out/preview_detail_wheel.png) | ![interior](blender/out/preview_detail_interior.png) |

![side](blender/out/preview_side.png)

## What's modelled

- **Body:** a lofted GMT400 shell with the shoulder crease, door and cab-to-bed gaps, fuel door, flush handles and window seals.
  - Carbon flares with rivets.
  - Open bed with wheel tubs and ribbed liner. The bed has no tailgate.
  - Red and white pinstripes.
  - Z71 badges.
- **Front:**
  - Quad headlamps with LED light strips and projectors, honeycomb grille with a red Z71, slatted bumper intakes.
  - Intercooler with end tanks and couplers.
  - Carbon splitter with endplates, canards and support rods, plus a tow strap.
  - Mirrors, wipers and a cowl.
- **Engine bay:**
  - V8 long-block with finned red valve covers, coil packs, intake runners and twin throttle bodies under a carbon twin-oval airbox.
  - Carbon intake tube with red bands to a cone filter, fuel rails with braided lines.
  - Serpentine belt drive, radiator with fans, heat-wrapped headers, red strut brace, brake booster and master cylinder.
- **Bed twin-turbo kit:**
  - Two turbos with snail-shell housings and visible compressor wheels.
  - Silver charge pipes into a center plenum.
  - Red cone filters, wastegates with screamer pipes, a gold heat shield.
  - Diagonal inboard coilovers on an aluminium A-bracket.
  - Strapped aluminium fuel cell low in the open back, plus the battery.
- **Exhaust:** twin tips through **both** bed sides ahead of the rear wheels. Crossover pipes run from the headers back to the turbines under the cab.
- **Wheels:**
  - 20" red split 7-spoke rims with polished riveted lips and hex lug nuts.
  - Semi-slick tyres with sidewall lettering.
  - Drilled two-piece rotors and 6-piston calipers.
  - Blurred rim discs for speed.
- **Interior:**
  - Red buckets with 5-point harnesses and a roll cage.
  - Dash with tach and speedo, plus A-pillar boost gauges.
  - A switch panel, pedals, shifter and hydraulic handbrake.
  - A steering wheel that turns in game.
  - Door cards, rear-view mirror and a fire extinguisher.

## Files

```
blender/build_truck.py            entry point
blender/forge/                    geometry toolkit + one module per area (body, front_rear, engine, bed,
                                  interior, wheels, chassis), materials/textures, LOD + FBX export, renders
blender/out/
  acf_blackout_pickup.fbx           LOD A, full detail (~318k triangles, includes COCKPIT_LR)
  acf_blackout_pickup_B/C/D.fbx     distance LODs (~114k / ~45k / ~19k triangles)
  acf_blackout_pickup.blend         editable Blender scene
  acf_blackout_pickup.glb           quick look in any 3D viewer
  texture/*.png                     textures referenced by the FBX files
  preview_*.png                     renders
content/cars/acf_blackout_pickup/
  data/      physics, lights.ini, lods.ini, blurred_objects.ini ...
  ui/        name, specs and curves for the car menu
  skins/     default skin
```

## Rebuild the model

This needs Blender 4.2 or newer (tested on 5.1). The `bpy` module plus `pillow` and `numpy` also work.

```bash
blender -b -P blender/build_truck.py -- --render
```

Options:
- `--quick` renders fast low-sample previews.
- `--views side,front_quarter` renders only some views.
- `--no-lods` skips the distance versions.
- `--only body,engine` builds only some parts, for testing.

The headlight style is the constant `LAMP_STYLE` in `blender/forge/front_rear.py`:
- `"angled"` gives the angled LED strips from the photo-style reference.
- `"bracket"` gives the square brackets from the drawn concept art.

## Getting it into the game

1. **Make the models:** in the **AC Editor** (`assettocorsa/sdk/editor/ksEditor.exe`), load each FBX with the `texture/` folder next to it.
   - Set the shaders using the table below.
   - Save `acf_blackout_pickup.fbx` as `acf_blackout_pickup.kn5`.
   - Save `_B`, `_C` and `_D` as `acf_blackout_pickup_B.kn5`, `acf_blackout_pickup_C.kn5` and `acf_blackout_pickup_D.kn5`.
   - Put all four `.kn5` files in `content/cars/acf_blackout_pickup/`. `data/lods.ini` switches between them by distance.
2. **Install the car:** copy `content/cars/acf_blackout_pickup` into your game's `content/cars/` folder.
3. **Add sound:** in **Content Manager**, use *Sound → Replace sound* with a V8 donor car. That creates `sfx/`.
4. **Check the fit:** look at the car in the Showroom. Tweak `GRAPHICS_OFFSET` in `data/car.ini` until the wheels sit in the arches. If the cockpit camera is in the wrong seat, flip the sign of the first `DRIVEREYES` value.
5. **Pack the data (optional):** once the physics are final, use *Car → Pack data*.

### Shaders for ksEditor

| Material | Shader | Notes |
|---|---|---|
| Paint_Black | `ksPerPixelMultiMap` | the skin repaints `Paint_Black.png` |
| Carbon, Trim_Black, Gloss_Black, Interior_Black, Grille_Mesh, Bed_Liner, Rubber, Carpet | `ksPerPixel` | |
| Chrome, Metal_Polished, Brushed_Alu, Cast_Alu, Rim_Lip, Mirror_Glass, Reflector, Heat_Gold | `ksPerPixel` | raise `ksSpecular`/`ksSpecularEXP` for shine |
| Rim_Red, Caliper_Red, Valve_Red, Seat_Red, Strap_Red, Spring_Red, Silicone_Red, Filter_Red | `ksPerPixel` | |
| Engine_Dark, Turbo_Hot, Heat_Wrap, Braided, Intercooler_Fins, Thread_Alu, Anodized_* | `ksPerPixel` | |
| Tyre | `ksTyres` (or `ksPerPixel`) | sidewall lettering is in the texture |
| Brake_Disc | `ksBrakeDisc` (or `ksPerPixel`) | |
| Glass, Lens_Clear, Lens_Red, Lens_Amber, Rim_Blur | `ksPerPixelAlpha` | Alpha blend **on**, depth mode **read-only** |
| Light_Head, Light_Tail, Light_Marker | `ksPerPixel` | `data/lights.ini` makes them glow |
| Gauge_*, Plate, Decal_White | `ksPerPixel` | |

### Node names AC uses (already set in the model)

| Node | Behaviour |
|---|---|
| `WHEEL_LF/RF/LR/RR` | tyres and rims; rotate and steer |
| `DISC_*` | rotors; rotate and glow |
| `SUSP_*` | calipers and uprights; steer, don't rotate |
| `STEER_HR` / `STEER_LR` | steering wheel |
| `COCKPIT_HR` / `COCKPIT_LR` | interior, high-res and low-res |
| `RIM_BLUR_*` | blurred rims (`data/blurred_objects.ini`) |
| `LIGHT_HEAD_L/R`, `LIGHT_TAIL_L/R`, `LIGHT_BRAKE3`, `LIGHT_MARKER_F/R` | lights (`data/lights.ini`) |

## Known limits

- **Logos:** the bowtie is left as a blank badge plate. Add the logo in a skin texture if you want it.
- **Missing parts:** there's no driver model, and the doors and wipers aren't animated.
- **Untested physics:** the physics follow Kunos formats but haven't been driven yet. Expect to tune `tyres.ini` and `suspensions.ini`.
- **`.ini` details:** the `lods.ini` and `blurred_objects.ini` formats come from Kunos cars. Check the switch distances and speeds in game.
