# Invoked by build_table_room.py — SCN_08_TABLE_ROOM warm first reunion.

import json
import math
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy
from mathutils import Euler, Vector

SCENE = "SCN_08_TABLE_ROOM"
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


def add_empty(name, loc, col, display="PLAIN_AXES"):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.location = Vector(loc)
    link(obj, col)
    created.append(name)
    return obj


def add_light(name, ltype, loc, energy, col, color=None):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    light = bpy.data.lights.new(name + "_Data", type=ltype)
    light.energy = energy
    if color is not None:
        light.color = color
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


def store_camera_marker(scene, cam_obj, name, frame):
    """Timeline marker bound to a camera for saved positions."""
    ensure_marker(scene, name, frame)
    marker = scene.timeline_markers.get(name)
    if marker is not None and cam_obj is not None:
        marker.camera = cam_obj


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
scene.frame_end = int(data.get("scene_frame_end", 480))
res = data.get("resolution", [1920, 1080])
scene.render.resolution_x = int(res[0])
scene.render.resolution_y = int(res[1])
try:
    scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

scene["table_is_centre"] = True
scene["emotional_register"] = "warm_pleasurable_funny_safe"
scene["villain"] = False
scene["father_as_monster"] = False
scene["father_has_life_beyond_desire"] = True
scene["dionysian_uncertainty_optional"] = True
scene["explain_dionysian_uncertainty"] = False

cols = {n: ensure_collection(n) for n in data["collections"]}

arch = cols["TABLE_ROOM_ARCHITECTURE"]
add_plane("TABLE_Floor", (0, 0, 0), (10, 12, 1), arch)
add_cube("ARCH_IndustrialFrame_A", (-4, 0, 2), (0.2, 0.2, 4), arch)
add_cube("ARCH_IndustrialFrame_B", (4, 0, 2), (0.2, 0.2, 4), arch)
add_cube("ARCH_BeamQuiet", (0, -3, 3.2), (5, 0.25, 0.25), arch)
add_cylinder("ARCH_ColumnRepurposed", (3.2, 2.5, 1.5), (0.35, 0.35, 3), arch)
# Impossible room shell — industrial frames become walls without shouting factory
add_cube("ARCH_QuietWall_Back", (0, 4.5, 2), (6, 0.15, 4), arch)
add_cube("ARCH_QuietWall_L", (-5, 0.5, 2), (0.15, 6, 4), arch)
add_cube("ARCH_QuietWall_R", (5, 0.5, 2), (0.15, 6, 4), arch)

furn = cols["TABLE_FURNITURE"]
add_cube("TABLE_WornSurface", (0, 0, 0.75), (1.8, 1.0, 0.06), furn)
add_cylinder("TABLE_Leg_A", (-0.7, -0.35, 0.35), (0.06, 0.06, 0.7), furn)
add_cylinder("TABLE_Leg_B", (0.7, -0.35, 0.35), (0.06, 0.06, 0.7), furn)
add_cylinder("TABLE_Leg_C", (-0.7, 0.35, 0.35), (0.06, 0.06, 0.7), furn)
add_cylinder("TABLE_Leg_D", (0.7, 0.35, 0.35), (0.06, 0.06, 0.7), furn)
add_cube("CHAIR_Father_Habitual", (0, 0.85, 0.45), (0.4, 0.4, 0.9), furn)
add_cube("CHAIR_Oino", (0, -0.9, 0.45), (0.4, 0.4, 0.9), furn)
# Window / opening that can attract the father
add_cube("TABLE_WindowOpening", (0, 4.4, 2.2), (1.6, 0.08, 1.4), furn)
add_empty("TABLE_WindowAttention", (0, 5.2, 2.0), furn)

props = cols["TABLE_PROPS"]
add_cube("PROP_PlaybackDevice", (-0.35, -0.15, 0.85), (0.35, 0.22, 0.08), props)
add_cube("PROP_PlaybackControl", (-0.2, -0.25, 0.9), (0.08, 0.05, 0.03), props)
add_cylinder("PROP_Bowl", (0.45, 0.1, 0.82), (0.18, 0.18, 0.1), props)
add_cylinder("PROP_Cup", (-0.55, 0.25, 0.88), (0.07, 0.07, 0.12), props)

organic = cols["TABLE_ORGANIC"]
# Subtle vine around one table leg only
add_cylinder("TABLE_VineLeg", (-0.7, -0.35, 0.25), (0.04, 0.04, 0.55), organic, rot=(15, 0, 25))
add_cylinder("TABLE_VineTendril", (-0.65, -0.4, 0.5), (0.025, 0.025, 0.35), organic, rot=(40, 10, -20))

refl = cols["TABLE_REFLECTION"]
mirror = add_plane(
    "PROP_ReflectiveSurface_Sister",
    (1.6, -0.2, 1.1),
    (0.55, 0.7, 1),
    refl,
    rot=(85, 0, -25),
)
mirror["can_show_sister_downstairs"] = True
add_empty("REFLECT_SisterDownstairs_Hint", (1.6, -2.5, -1.5), refl)

light_col = cols["TABLE_LIGHT"]
warm = add_light(
    "LIGHT_WarmHuman",
    "AREA",
    (0, 0, 2.4),
    180,
    light_col,
    color=(1.0, 0.82, 0.62),
)
warm["human_warmth"] = True
cold = add_light(
    "LIGHT_ColdSurround",
    "AREA",
    (0, -4, 3.5),
    40,
    light_col,
    color=(0.55, 0.65, 0.85),
)
cold["surround_cold"] = True
add_light("LIGHT_WindowSoft", "AREA", (0, 4.2, 2.5), 35, light_col, color=(0.7, 0.75, 0.9))

prox = cols["TABLE_PROXIES"]
add_uv_sphere("PROXY_Father_Head", (0, 0.75, 1.45), (0.28, 0.28, 0.28), prox)
add_cube("PROXY_Father_Body", (0, 0.75, 0.95), (0.4, 0.25, 0.7), prox)
add_cube("PROXY_Father_Hand_L", (-0.25, 0.35, 0.85), (0.12, 0.08, 0.05), prox)
add_cube("PROXY_Father_Hand_R", (0.2, 0.3, 0.85), (0.12, 0.08, 0.05), prox)
add_uv_sphere("PROXY_Oino_Head", (0, -0.8, 1.4), (0.26, 0.26, 0.26), prox)
add_cube("PROXY_Oino_Body", (0, -0.85, 0.9), (0.35, 0.22, 0.65), prox)
add_cube("PROXY_Oino_Hand_Control", (-0.2, -0.35, 0.92), (0.1, 0.06, 0.04), prox)

life = cols["TABLE_FATHER_LIFE"]
for b in data.get("father_life_beats") or []:
    empty = add_empty(b["id"], (0, 0.5, 1.0), life, display="SPHERE")
    empty["beat"] = b.get("beat", "")
    empty["staging"] = b.get("staging", "")

# Simple father life animation: glance to window, habit, pause pose shifts
hand_r = bpy.data.objects.get("PROXY_Father_Hand_R")
hand_l = bpy.data.objects.get("PROXY_Father_Hand_L")
father_head = bpy.data.objects.get("PROXY_Father_Head")
father_body = bpy.data.objects.get("PROXY_Father_Body")
cup = bpy.data.objects.get("PROP_Cup")

if father_head:
    father_head.rotation_euler = Euler((0, 0, 0), "XYZ")
    father_head.keyframe_insert(data_path="rotation_euler", frame=200)
    # Glance toward window
    father_head.rotation_euler = Euler((math.radians(-8), 0, math.radians(18)), "XYZ")
    father_head.keyframe_insert(data_path="rotation_euler", frame=216)
    father_head.rotation_euler = Euler((0, 0, 0), "XYZ")
    father_head.keyframe_insert(data_path="rotation_euler", frame=240)

if hand_l and cup:
    # Physical habit: thumb path toward cup rim
    hand_l.location = Vector((-0.25, 0.35, 0.85))
    hand_l.keyframe_insert(data_path="location", frame=250)
    hand_l.location = Vector((-0.5, 0.28, 0.9))
    hand_l.keyframe_insert(data_path="location", frame=264)
    hand_l.location = Vector((-0.25, 0.35, 0.85))
    hand_l.keyframe_insert(data_path="location", frame=290)

if hand_r:
    # Musical mistake / note disagreement — small restless motion on device side
    hand_r.location = Vector((0.2, 0.3, 0.85))
    hand_r.keyframe_insert(data_path="location", frame=60)
    hand_r.location = Vector((0.05, 0.15, 0.88))
    hand_r.keyframe_insert(data_path="location", frame=72)
    hand_r.location = Vector((0.15, 0.2, 0.86))
    hand_r.keyframe_insert(data_path="location", frame=168)
    hand_r.location = Vector((0.2, 0.3, 0.85))
    hand_r.keyframe_insert(data_path="location", frame=190)

if father_body:
    # Ordinary pause — settle; later begin leaving toward window
    father_body.location = Vector((0, 0.75, 0.95))
    father_body.keyframe_insert(data_path="location", frame=300)
    father_body.keyframe_insert(data_path="location", frame=312)
    father_body.location = Vector((0.2, 1.4, 0.95))
    father_body.keyframe_insert(data_path="location", frame=360)
    father_body.location = Vector((0.4, 2.2, 0.95))
    father_body.keyframe_insert(data_path="location", frame=400)
    if father_head:
        father_head.location = Vector((0, 0.75, 1.45))
        father_head.keyframe_insert(data_path="location", frame=300)
        father_head.location = Vector((0.2, 1.4, 1.45))
        father_head.keyframe_insert(data_path="location", frame=360)
        father_head.location = Vector((0.4, 2.2, 1.45))
        father_head.keyframe_insert(data_path="location", frame=400)

# Laugh / note disagreement as audio empties (craft later)
add_empty("AUDIO_FatherLaugh", (0, 0.6, 1.3), life)
add_empty("AUDIO_NoteDisagreement", (-0.2, 0.2, 1.0), life)
add_empty("AUDIO_MusicalMistake", (-0.3, 0.0, 0.95), life)
bpy.data.objects["AUDIO_FatherLaugh"]["one_laugh"] = True

edge = cols["TABLE_DIONYSUS_EDGE"]
# Vine-like shadow only at edge — optional, never explained
shadow = add_cylinder(
    "EDGE_DionysianUncertainty",
    (-4.6, -1.5, 1.2),
    (0.08, 0.08, 1.8),
    edge,
    rot=(10, 5, -30),
)
shadow["optional"] = True
shadow["explain"] = False
shadow["form"] = data.get("dionysian_uncertainty", {}).get("default_choice", "vine-like shadow")
shadow.hide_render = False  # can be toggled off per pass
add_empty("EDGE_OmitPass_Toggle", (-4.6, -1.5, 2.5), edge)

cams = cols["TABLE_CAMERAS"]
cam_specs = {
    "CAM_TABLE_ARRIVAL": ((0, -4.5, 1.6), (72, 0, 0), 32, 1),
    "CAM_TABLE_TWO_SHOT": ((2.2, -1.2, 1.35), (75, 0, 55), 40, 48),
    "CAM_TABLE_FATHER_HANDS": ((0.4, 0.1, 1.05), (55, 0, 10), 50, 72),
    "CAM_TABLE_OINO_CONTROL": ((-0.6, -1.1, 1.1), (50, 0, -25), 55, 100),
    "CAM_TABLE_REFLECTION": ((2.0, -0.8, 1.3), (70, 0, 100), 45, 192),
    "CAM_TABLE_FATHER_LEAVING": ((-1.5, -0.5, 1.5), (78, 0, -20), 35, 360),
    "CAM_TABLE_DOORWAY_LOOKBACK": ((0, -5.5, 1.7), (78, 0, 0), 28, 420),
}
cam_objs = {}
for cid, (loc, rot, lens, frame) in cam_specs.items():
    obj = add_camera(cid, loc, rot, cams, lens=lens)
    for c in data.get("cameras") or []:
        if c.get("id") == cid:
            obj["role"] = c.get("role", "")
            obj["note"] = c.get("note", "")
            break
    cam_objs[cid] = obj
    store_camera_marker(scene, obj, f"SAVE_{cid}", frame)

scene.camera = cam_objs.get("CAM_TABLE_ARRIVAL")

for e in data.get("events") or []:
    ensure_marker(scene, e["marker"], e["frame"])
for b in data.get("father_life_beats") or []:
    ensure_marker(scene, b["marker"], b["frame"])

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
Path(data["report_out"]).write_text(
    json.dumps({"created": created, "reused": reused, "skipped": skipped}, indent=2),
    encoding="utf-8",
)
print(f"OINO_TABLE_ROOM_OK {out}")
print(
    json.dumps(
        {
            "created": len(created),
            "reused": len(reused),
            "cameras": len(cam_objs),
            "warm_safe": True,
        }
    )
)
