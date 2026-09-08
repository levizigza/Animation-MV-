# Invoked by build_zone.py — SCN_07_ZONE primitives; nature unresolved.

import json
import math
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy
from mathutils import Euler, Vector

SCENE = "SCN_07_ZONE"
RESET = bool(data.get("reset", False))
created, reused, skipped = [], [], []


def ensure_collection(name):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
        reused.append(f"col:{name}")
    else:
        col = bpy.data.collections.new(name)
        created.append(f"col:{name}")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
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


def add_camera(name, loc, rot, col, lens=35):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    cam = bpy.data.cameras.new(name + "_Data")
    cam.lens = lens
    obj = bpy.data.objects.new(name, cam)
    obj.location = Vector(loc)
    obj.rotation_euler = Euler([math.radians(a) for a in rot], "XYZ")
    link(obj, col)
    created.append(name)
    return obj


def ensure_marker(scene, name, frame):
    if name in scene.timeline_markers:
        if not RESET:
            skipped.append(f"marker:{name}")
            return
        scene.timeline_markers.remove(scene.timeline_markers[name])
    m = scene.timeline_markers.new(name, frame=int(frame))
    m.name = name
    created.append(f"marker:{name}")


# --- Scene ---
if SCENE in bpy.data.scenes and not RESET:
    scene = bpy.data.scenes[SCENE]
else:
    if SCENE in bpy.data.scenes and RESET:
        bpy.data.scenes.remove(bpy.data.scenes[SCENE])
    scene = bpy.data.scenes.new(SCENE)

bpy.context.window.scene = scene
scene.render.fps = int(data.get("fps", 24))
scene.frame_start = int(data.get("scene_frame_start", 1))
scene.frame_end = int(data.get("scene_frame_end", 360))
res = data.get("resolution", [1920, 1080])
scene.render.resolution_x = int(res[0])
scene.render.resolution_y = int(res[1])
try:
    scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

scene["zone_nature_resolved"] = False
scene["zone_villain"] = False
scene["zone_technical_explanation"] = False
scene["oino_goal"] = data.get("oino_goal", "follow the unfinished melody")
scene["hold_empty_after_exit"] = True

cols = {n: ensure_collection(n) for n in data["collections"]}

passage = cols["ZONE_PASSAGE"]
add_plane("ZONE_Floor", (0, 0, 0), (16, 24, 1), passage)
add_cube("ZONE_CorridorWall_L", (-3.5, 2, 1.5), (0.3, 12, 3), passage)
add_cube("ZONE_CorridorWall_R", (3.5, 2, 1.5), (0.3, 12, 3), passage)

water = cols["ZONE_WATER"]
add_cube("ZONE_ShallowWater", (0, 1, 0.05), (4, 10, 0.08), water)

debris = cols["ZONE_DEBRIS"]
add_cube("ZONE_Debris_A", (-1.5, 3, 0.25), (0.8, 0.4, 0.3), debris)
add_cube("ZONE_Debris_B", (1.8, 5, 0.2), (0.5, 0.6, 0.25), debris)
add_cube("ZONE_Debris_C", (0.5, 7, 0.15), (1.0, 0.3, 0.2), debris)
add_cylinder("ZONE_Tool_Abandoned_A", (-2, 4, 0.2), (0.08, 0.08, 0.6), debris, rot=(0, 90, 20))
add_cube("ZONE_Tool_Abandoned_B", (2.2, 6, 0.15), (0.4, 0.15, 0.1), debris)

doors = cols["ZONE_DOORS"]
add_cube("ZONE_Door_A", (-3.2, 0, 1.2), (0.15, 1.0, 2.2), doors)
add_cube("ZONE_Door_B", (3.2, 4, 1.2), (0.15, 1.0, 2.2), doors)
add_cube("ZONE_Door_C", (0, 10, 1.3), (1.2, 0.15, 2.4), doors)
# uncertain destinations — empties beyond doors, unnamed purpose
add_empty("ZONE_DoorDest_A_Unknown", (-6, 0, 1), doors)
add_empty("ZONE_DoorDest_B_Unknown", (6, 4, 1), doors)
add_empty("ZONE_DoorDest_C_Unknown", (0, 14, 1), doors)

organic = cols["ZONE_ORGANIC_MACHINE"]
add_cylinder("ZONE_VineThroughPipe", (-1, 2, 1), (0.06, 0.06, 2.5), organic, rot=(30, 0, 40))
add_cube("ZONE_RootMachine", (1.2, 3.5, 0.6), (0.7, 0.5, 0.8), organic)
add_cylinder("ZONE_RootTendril", (1.0, 3.2, 0.4), (0.05, 0.05, 1.2), organic, rot=(80, 10, 0))

light_col = cols["ZONE_LIGHT_UNSOURCED"]
amber = add_light("ZONE_LIGHT_AmberUnsourced", "POINT", (0.5, 6, 2.2), 60, light_col)
amber["source_confirmed"] = False
amber["colour_intent"] = "red_or_amber_unconfirmed"

audio = cols["ZONE_AUDIO_WRONG"]
add_empty("ZONE_AUDIO_WrongReflection", (0, 2, 1.5), audio)
add_empty("ZONE_AUDIO_IrregularKnock", (-2.5, 1, 1.2), audio)
add_empty("ZONE_AUDIO_DistantLaugh", (2, 8, 2), audio)
bpy.data.objects["ZONE_AUDIO_WrongReflection"]["slightly_wrong"] = True
bpy.data.objects["ZONE_AUDIO_IrregularKnock"]["irregular"] = True
bpy.data.objects["ZONE_AUDIO_DistantLaugh"]["one_only"] = True

prox = cols["ZONE_PROXIES"]
add_uv_sphere("PROXY_Oino_Zone_Head", (0, -2, 1.5), (0.3, 0.3, 0.3), prox)
add_cube("PROXY_Oino_Zone_Body", (0, -2, 0.9), (0.35, 0.2, 0.6), prox)
add_cube("ZONE_MapProp", (-0.4, -1.5, 1.0), (0.25, 0.02, 0.35), prox)
add_plane("ZONE_Photograph", (0.4, -1.6, 1.05), (0.3, 0.22, 1), prox, rot=(80, 0, 15))
# Table glimpse ahead — before she reaches it
add_cube("ZONE_TableGlimpse", (0, 12, 0.45), (1.8, 0.9, 0.1), prox)
add_cylinder("ZONE_TableGlimpse_Bowl", (0.3, 12, 0.55), (0.2, 0.2, 0.1), prox)

echo = cols["ZONE_DIONYSUS_ECHO"]
add_plane("ZONE_DamagedFrame_PossibleDionysus", (-2.5, 5, 1.8), (0.8, 0.5, 1), echo, rot=(90, 0, 10))
bpy.data.objects["ZONE_DamagedFrame_PossibleDionysus"]["label_forbidden"] = True
bpy.data.objects["ZONE_DamagedFrame_PossibleDionysus"]["possible_echo_only"] = True

thr = cols["ZONE_THRESHOLDS"]
for i, t in enumerate(data.get("thresholds") or []):
    add_empty(t["id"], (0, -1 + i * 2.5, 0.5), thr)

cams = cols["ZONE_CAMERAS"]
c0 = add_camera("CAM_ZONE_PATIENT_WIDE", (0, -8, 2.2), (72, 0, 0), cams, lens=28)
add_camera("CAM_ZONE_THRESHOLD", (-2, -3, 1.6), (70, 0, -15), cams, lens=40)
add_camera("CAM_ZONE_WATER", (1.5, 0, 1.2), (85, 0, 20), cams, lens=50)
add_camera("CAM_ZONE_EXIT", (0, 6, 1.8), (68, 0, 0), cams, lens=35)
scene.camera = c0
add_light("ZONE_LIGHT_FillSoft", "AREA", (0, -4, 4), 120, light_col)

# Markers
ensure_marker(scene, "ZONE_ENTER", data.get("scene_frame_start", 1))
for t in data.get("thresholds") or []:
    ensure_marker(scene, t["marker"], t["frame"])
for e in data.get("events") or []:
    ensure_marker(scene, e["marker"], e["frame"])
ensure_marker(scene, "ZONE_EXIT", data.get("scene_frame_end", 360))

# Simple hide of Oino proxy late for empty hold (patient camera)
oino_body = bpy.data.objects.get("PROXY_Oino_Zone_Body")
oino_head = bpy.data.objects.get("PROXY_Oino_Zone_Head")
empty_frame = 320
for obj in (oino_body, oino_head):
    if not obj:
        continue
    obj.hide_render = False
    obj.hide_viewport = False
    obj.keyframe_insert(data_path="hide_render", frame=empty_frame - 1)
    obj.keyframe_insert(data_path="hide_viewport", frame=empty_frame - 1)
    obj.hide_render = True
    obj.hide_viewport = True
    obj.keyframe_insert(data_path="hide_render", frame=empty_frame)
    obj.keyframe_insert(data_path="hide_viewport", frame=empty_frame)

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
Path(data["report_out"]).write_text(
    json.dumps({"created": created, "reused": reused, "skipped": skipped}, indent=2),
    encoding="utf-8",
)
print(f"OINO_ZONE_OK {out}")
print(json.dumps({"created": len(created), "reused": len(reused), "resolved": False}))
