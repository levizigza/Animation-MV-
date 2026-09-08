# Invoked by build_modular_industrial_world.py
# One reusable world; era via collection visibility + materials — not four cities.

import json
import math
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy
from mathutils import Euler, Vector

SCENE = "SCN_MODULAR_INDUSTRIAL_WORLD"
RESET = bool(data.get("reset", False))
created, reused, skipped = [], [], []
vis = data.get("collection_visibility") or {}
controls = data.get("control_values") or {}
preview = bool(data.get("preview_mode", True))


def ensure_collection(name):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
        reused.append(f"col:{name}")
    else:
        col = bpy.data.collections.new(name)
        created.append(f"col:{name}")
    root = bpy.context.scene.collection
    if col.name not in root.children:
        root.children.link(col)
    return col


def link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def add_cube(name, loc, scale, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    link(obj, col)
    created.append(name)
    return obj


def add_cylinder(name, loc, scale, col, rot=None):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if rot:
        obj.rotation_euler = Euler([math.radians(a) for a in rot], "XYZ")
    link(obj, col)
    created.append(name)
    return obj


def add_plane(name, loc, scale, col, rot=None):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if rot:
        obj.rotation_euler = Euler([math.radians(a) for a in rot], "XYZ")
    link(obj, col)
    created.append(name)
    return obj


def add_uv_sphere(name, loc, scale, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    link(obj, col)
    created.append(name)
    return obj


def add_empty(name, loc, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.location = Vector(loc)
    link(obj, col)
    created.append(name)
    return obj


def add_light(name, ltype, loc, energy, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    light = bpy.data.lights.new(name + "_Data", type=ltype)
    light.energy = energy
    obj = bpy.data.objects.new(name, light)
    obj.location = Vector(loc)
    link(obj, col)
    created.append(name)
    return obj


def add_camera(name, loc, rot, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    cam = bpy.data.cameras.new(name + "_Data")
    cam.lens = 28
    obj = bpy.data.objects.new(name, cam)
    obj.location = Vector(loc)
    obj.rotation_euler = Euler([math.radians(a) for a in rot], "XYZ")
    link(obj, col)
    created.append(name)
    return obj


def set_collection_preview(col, weight):
    """Preview visibility: hide collection in viewport when weight low."""
    hide = weight < 0.08
    col.hide_viewport = hide
    col.hide_render = hide
    # Store control readout on collection
    col["oino_visibility_weight"] = float(weight)


def instance_along(source_name, offsets, col, prefix):
    if source_name not in bpy.data.objects:
        skipped.append(f"instance_missing:{source_name}")
        return
    src = bpy.data.objects[source_name]
    for i, off in enumerate(offsets):
        name = f"{prefix}_INST_{i:02d}"
        if name in bpy.data.objects and not RESET:
            obj = bpy.data.objects[name]
            link(obj, col)
            reused.append(name)
            continue
        if name in bpy.data.objects and RESET:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        obj = src.copy()
        obj.data = src.data  # shared mesh = instancing-friendly
        obj.name = name
        obj.location = (
            src.location.x + off["dx"],
            src.location.y + off["dy"],
            src.location.z,
        )
        obj.rotation_euler.rotate_axis("Z", math.radians(off["yaw_deg"]))
        obj.scale = (
            src.scale.x * off["scale"],
            src.scale.y * off["scale"],
            src.scale.z * off["scale"],
        )
        link(obj, col)
        created.append(name)


# --- Scene ---
if SCENE in bpy.data.scenes and not RESET:
    scene = bpy.data.scenes[SCENE]
else:
    if SCENE in bpy.data.scenes and RESET:
        bpy.data.scenes.remove(bpy.data.scenes[SCENE])
    scene = bpy.data.scenes.new(SCENE)

bpy.context.window.scene = scene
scene.render.fps = int(data.get("fps", 24))
scene.frame_start = 1
scene.frame_end = 240
res = data.get("resolution", [1920, 1080])
scene.render.resolution_x = int(res[0])
scene.render.resolution_y = int(res[1])
try:
    scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

cols = {n: ensure_collection(n) for n in data["collections"]}

# Custom properties = exposed controls
scene["era_blend"] = float(controls.get("era_blend", 0.35))
scene["future_branch"] = float(controls.get("future_branch", 0.0))
scene["organic_growth"] = float(controls.get("organic_growth", 0.2))
scene["dionysus_presence"] = float(controls.get("dionysus_presence", 0.15))
scene["oino_one_world"] = True
scene["oino_not_four_cities"] = True

anchors = data["persistent_anchors"]
struct = cols["WORLD_STRUCTURE"]

# Persistent anchors — shared recognition across eras
add_cube(anchors["doorway"], (-2.0, -4.0, 1.2), (0.2, 1.2, 2.2), struct)
add_cylinder(
    anchors["vertical_beam"],
    (0.0, 0.0, 4.0),
    (0.35, 0.35, 8.0),
    struct,
)  # Babel-capable core
add_plane(anchors["path"], (0.0, -2.0, 0.02), (2.0, 10.0, 1), struct)
add_cylinder(anchors["bowl"], (1.5, -3.5, 0.45), (0.25, 0.25, 0.12), struct)
add_cube(anchors["hand_level_surface"], (1.5, -3.5, 0.35), (0.9, 0.5, 0.08), struct)
add_plane("WORLD_Ground", (0, 0, 0), (20, 20, 1), struct)

# Water / early
water = cols["WORLD_WATER_AND_REFLECTIONS"]
add_cube("MOD_WaterChannel_A", (-4.0, 0.0, 0.15), (6.0, 0.8, 0.2), water)
add_cube("MOD_WaterChannel_B", (-4.0, 2.5, 0.15), (4.0, 0.6, 0.2), water)
add_cylinder("MOD_Waterwheel", (-5.5, 0.0, 1.2), (1.2, 0.2, 1.2), water, rot=(90, 0, 0))

# Structure modules — timber / brick / circulation / babel already anchored
add_cube("MOD_TimberBeam_A", (-1.0, 1.0, 2.5), (3.0, 0.15, 0.15), struct)
add_cube("MOD_TimberBeam_B", (1.5, 1.5, 2.8), (2.5, 0.15, 0.15), struct)
add_cube("MOD_TimberBeam_C", (0.0, 2.0, 3.2), (4.0, 0.12, 0.12), struct)
add_cube("MOD_BrickWall_A", (3.5, 0.0, 1.5), (0.3, 4.0, 3.0), struct)
add_cube("MOD_StoneBlock_A", (3.0, -1.5, 0.4), (0.8, 0.6, 0.8), struct)
add_cube("MOD_StoneBlock_B", (4.0, -2.0, 0.35), (0.6, 0.5, 0.7), struct)
add_cube("MOD_OldDoor_A", (-2.0, -4.05, 1.1), (0.08, 0.9, 1.8), struct)
add_cube("MOD_Ladder_A", (2.2, 1.0, 1.8), (0.15, 0.08, 3.2), struct)
add_cube("MOD_Catwalk_A", (0.0, 3.5, 3.5), (5.0, 0.6, 0.08), struct)
add_cube("MOD_Platform_A", (2.5, 3.0, 2.0), (2.0, 1.5, 0.12), struct)
add_cube("MOD_Corridor_A", (0.0, 5.0, 1.5), (2.0, 4.0, 2.5), struct)

# Steam era
steam = cols["WORLD_STEAM"]
add_cylinder("MOD_SteamPipe_A", (-1.5, 0.5, 2.0), (0.12, 0.12, 3.0), steam, rot=(0, 90, 20))
add_cylinder("MOD_SteamPipe_B", (0.5, 1.2, 2.4), (0.1, 0.1, 2.5), steam, rot=(0, 90, -15))
add_cylinder("MOD_SteamPipe_C", (2.0, 0.8, 1.8), (0.08, 0.08, 2.0), steam, rot=(90, 0, 40))
add_cube("MOD_LoomFrame", (-3.0, 2.0, 1.2), (1.5, 0.8, 1.8), steam)
add_cube("MOD_BeltRun_A", (-2.0, 2.0, 1.0), (2.5, 0.08, 0.08), steam)
add_cube("MOD_BeltRun_B", (-1.0, 2.5, 1.3), (2.0, 0.08, 0.08), steam)
add_cylinder("MOD_Valve_A", (-0.5, 0.6, 1.5), (0.2, 0.2, 0.25), steam)
add_cylinder("MOD_Valve_B", (1.0, 1.0, 1.7), (0.18, 0.18, 0.22), steam)

# Electric
elec = cols["WORLD_ELECTRIC"]
add_cylinder("MOD_Pole_A", (5.0, -2.0, 2.5), (0.12, 0.12, 5.0), elec)
add_cylinder("MOD_Pole_B", (5.0, 2.0, 2.5), (0.12, 0.12, 5.0), elec)
add_uv_sphere("MOD_Lamp_A", (5.0, -2.0, 4.8), (0.25, 0.25, 0.25), elec)
add_uv_sphere("MOD_Lamp_B", (5.0, 2.0, 4.8), (0.25, 0.25, 0.25), elec)
add_cube("MOD_Generator", (4.0, 0.5, 0.8), (1.2, 0.9, 1.0), elec)
add_cylinder("MOD_CableBundle_A", (3.5, 0.0, 1.5), (0.15, 0.15, 2.0), elec, rot=(0, 90, 0))
add_cylinder("MOD_CableBundle_B", (4.5, 1.0, 2.0), (0.12, 0.12, 1.8), elec, rot=(0, 60, 30))
add_cube("MOD_AssemblyBay_A", (6.5, 0.0, 1.0), (2.0, 3.0, 1.5), elec)
add_cube("MOD_AssemblyBay_B", (8.5, 0.0, 1.0), (2.0, 3.0, 1.5), elec)
add_light("LIGHT_ElectricA", "POINT", (5.0, -2.0, 4.5), 200, elec)
add_light("LIGHT_ElectricB", "POINT", (5.0, 2.0, 4.5), 200, elec)

# Digital
digital = cols["WORLD_DIGITAL"]
add_cube("MOD_Terminal_A", (7.0, -3.0, 1.1), (0.6, 0.4, 1.2), digital)
add_cube("MOD_Monitor_A", (7.0, -3.0, 1.8), (0.55, 0.08, 0.4), digital)
add_cube("MOD_Monitor_B", (7.6, -2.5, 1.7), (0.5, 0.08, 0.35), digital)
add_cube("MOD_ServerRack_A", (9.0, -3.0, 1.5), (0.8, 0.6, 2.5), digital)
add_cube("MOD_CoolingUnit_A", (9.8, -3.0, 0.8), (0.7, 0.7, 1.0), digital)
add_light("LIGHT_ScreenGlow", "AREA", (7.0, -3.5, 1.8), 80, digital)

# Possible futures — assistive / medical / synth voice (benefit + cost eras)
future = cols["WORLD_POSSIBLE_FUTURES"]
add_cube("MOD_AssistiveComm_A", (8.0, 3.0, 1.0), (0.7, 0.5, 1.0), future)
add_cube("MOD_AssistiveComm_B", (8.8, 3.2, 1.0), (0.5, 0.4, 0.8), future)
add_cube("MOD_MedModule_A", (10.0, 3.0, 1.0), (1.0, 0.8, 1.2), future)
add_cube("MOD_SynthVoicePanel", (9.2, 3.8, 1.4), (0.6, 0.1, 0.5), future)

# Organic growth
organic = cols["WORLD_ORGANIC_GROWTH"]
add_cylinder("GROWTH_Vine_A", (-1.5, -3.5, 1.0), (0.05, 0.05, 2.5), organic, rot=(20, 0, 40))
add_cylinder("GROWTH_Vine_B", (0.5, -3.8, 0.8), (0.04, 0.04, 2.0), organic, rot=(-15, 10, -30))
add_uv_sphere("GROWTH_MossClump_A", (1.4, -3.3, 0.4), (0.3, 0.2, 0.1), organic)

# Dionysus echoes — symbolic only
echo = cols["WORLD_DIONYSUS_ECHOES"]
add_uv_sphere("ECHO_WineLightOrb", (1.5, -3.5, 1.2), (0.2, 0.2, 0.2), echo)
add_cylinder("ECHO_VineCoil", (-0.5, -4.0, 0.6), (0.08, 0.08, 1.2), echo)
add_light("LIGHT_WineEcho", "POINT", (1.5, -3.5, 1.3), 40, echo)

# Seeded instances (shared mesh data)
inst = data.get("instances") or {}
instance_along("MOD_SteamPipe_A", inst.get("steam_pipes") or [], steam, "PIPE")
instance_along("MOD_CableBundle_A", inst.get("cable_bundles") or [], elec, "CABLE")
instance_along("MOD_TimberBeam_A", inst.get("timber_beams") or [], struct, "TIMBER")
instance_along("MOD_AssemblyBay_A", inst.get("assembly_line") or [], elec, "BAY")

# Apply preview visibility from controls
for name, col in cols.items():
    set_collection_preview(col, float(vis.get(name, 1.0)))

# Structure + anchors never fully vanish
struct.hide_viewport = False
struct.hide_render = False

# Camera looking along the persistent path toward doorway + babel core
cam_col = struct
cam = add_camera("CAM_WORLD_PATH", (-0.5, -9.0, 2.2), (72, 0, 0), cam_col)
scene.camera = cam
add_light("LIGHT_WorldKey", "SUN", (4, -6, 10), 3.0, struct)

# Control empty for animators
ctrl = add_empty("CTRL_WorldDrivers", (0, 0, 6), struct)
ctrl["era_blend"] = scene["era_blend"]
ctrl["future_branch"] = scene["future_branch"]
ctrl["organic_growth"] = scene["organic_growth"]
ctrl["dionysus_presence"] = scene["dionysus_presence"]
ctrl["preview_mode"] = preview

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
Path(data["report_out"]).write_text(
    json.dumps(
        {
            "created": created,
            "reused": reused,
            "skipped": skipped,
            "controls": controls,
            "visibility": vis,
            "preview": preview,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"OINO_MODULAR_WORLD_OK {out}")
print(json.dumps({"created": len(created), "reused": len(reused), "controls": controls}))
