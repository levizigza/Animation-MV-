# Invoked by build_title_card.py — SCN_13_TITLE_CARD still card; no trailer motion.

import json
import math
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy
from mathutils import Euler, Vector

SCENE = "SCN_13_TITLE_CARD"
RESET = bool(data.get("reset", False))
created, reused, skipped = [], [], []

TITLE = (data.get("title") or {}).get("text") or "One Of Gods Fools"
DATE = (data.get("release_date") or {}).get("text") or "December 10, 2026"
CTRL = data.get("controls") or {}
OBJS = data.get("objects") or {}


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


def ensure_marker(scene, name, frame):
    if name in scene.timeline_markers:
        if not RESET:
            skipped.append(f"marker:{name}")
            return scene.timeline_markers[name]
        scene.timeline_markers.remove(scene.timeline_markers[name])
    m = scene.timeline_markers.new(name, frame=int(frame))
    m.name = name
    created.append(f"marker:{name}")
    return m


def make_emit_mat(name, color, alpha=1.0):
    if name in bpy.data.materials and not RESET:
        return bpy.data.materials[name]
    if name in bpy.data.materials and RESET:
        bpy.data.materials.remove(bpy.data.materials[name])
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (
        float(color[0]),
        float(color[1]),
        float(color[2]),
        1.0,
    )
    emit.inputs["Strength"].default_value = 1.0
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    # Fac 0 = transparent, 1 = emission visible
    mix.inputs["Fac"].default_value = float(alpha)
    nt.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nt.links.new(emit.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    mat.blend_method = "BLEND"
    try:
        mat.shadow_method = "NONE"
    except Exception:
        pass
    created.append(f"mat:{name}")
    return mat


def set_alpha_keyframes(mat, frames_alphas):
    """Key Fac on Mix Shader (input 0) for fade."""
    nt = mat.node_tree
    mix = next(n for n in nt.nodes if n.type == "MIX_SHADER")
    fac = mix.inputs["Fac"]
    for frame, alpha in frames_alphas:
        fac.default_value = float(alpha)
        fac.keyframe_insert(data_path="default_value", frame=int(frame))


def add_plane(name, loc, scale, col, mat):
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
    obj.rotation_euler = Euler((math.radians(90), 0, 0), "XYZ")
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    link(obj, col)
    created.append(name)
    return obj


def add_text(name, body, loc, col, mat, size=0.35, spacing=0.08):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    curve = bpy.data.curves.new(name=name + "_Curve", type="FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size
    curve.space_character = float(spacing)
    obj = bpy.data.objects.new(name, curve)
    obj.location = Vector(loc)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    link(obj, col)
    created.append(name)
    return obj


def add_camera(name, loc, rot, col, lens=50):
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
scene.frame_end = int(data.get("scene_frame_end", 148))
res = data.get("resolution", [1920, 1080])
scene.render.resolution_x = int(res[0])
scene.render.resolution_y = int(res[1])
try:
    scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

bg_col = (CTRL.get("background_colour") or {}).get("rgba") or [0.039, 0.039, 0.039, 1.0]
type_col = (CTRL.get("type_colour") or {}).get("rgba") or [0.91, 0.894, 0.863, 1.0]
spacing = float(CTRL.get("letter_spacing") or 0.08)
title_fade = int(CTRL.get("title_fade_in_frames") or 12)
date_fade = int(CTRL.get("date_fade_in_frames") or 10)
title_hold = int(CTRL.get("title_hold_duration_frames") or 72)
date_hold = int(CTRL.get("date_hold_duration_frames") or 54)
final_out = CTRL.get("final_fade_out") or {}
final_out_on = bool(final_out.get("enabled"))
final_out_frames = int(final_out.get("frames") or 12)

scene["title_text"] = TITLE
scene["release_date_text"] = DATE
scene["apostrophe_in_Gods"] = False
scene["extra_subtitle"] = False
scene["logline"] = False
scene["moral_statement"] = False
scene["social_handle"] = False
scene["unapproved_production_credit"] = False
scene["generic_trailer_animation"] = False
scene["title_fade_in_frames"] = title_fade
scene["date_fade_in_frames"] = date_fade
scene["title_hold_duration_frames"] = title_hold
scene["date_hold_duration_frames"] = date_hold
scene["letter_spacing"] = spacing
scene["final_fade_out_enabled"] = final_out_on

world = scene.world or bpy.data.worlds.new("TITLE_WORLD")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs["Color"].default_value = (
        float(bg_col[0]),
        float(bg_col[1]),
        float(bg_col[2]),
        1.0,
    )
    bg_node.inputs["Strength"].default_value = 1.0

cols = {n: ensure_collection(n) for n in data["collections"]}

mat_bg = make_emit_mat("MAT_TitleBG", bg_col, alpha=1.0)
mat_title = make_emit_mat("MAT_TitleType", type_col, alpha=0.0)
mat_date = make_emit_mat("MAT_DateType", type_col, alpha=0.0)

add_plane(
    OBJS.get("background", "TITLE_BG_NearBlack"),
    (0, 0, 0),
    (8, 4.5, 1),
    cols["TITLE_CARD_BG"],
    mat_bg,
)

title_obj = add_text(
    OBJS.get("title_text", "TXT_TITLE_OneOfGodsFools"),
    TITLE,
    (0, -0.05, 0.35),
    cols["TITLE_CARD_TYPE"],
    mat_title,
    size=0.42,
    spacing=spacing,
)
date_obj = add_text(
    OBJS.get("date_text", "TXT_DATE_December10_2026"),
    DATE,
    (0, -0.05, -0.25),
    cols["TITLE_CARD_TYPE"],
    mat_date,
    size=0.22,
    spacing=spacing * 0.75,
)

# Still camera — no decorative trailer motion
cam = add_camera(
    OBJS.get("camera", "CAM_TITLE_STILL"),
    (0, -3.2, 0),
    (90, 0, 0),
    cols["TITLE_CARD_CAMERAS"],
    lens=50,
)
scene.camera = cam

ctrl = add_empty(
    OBJS.get("controls_empty", "CTRL_TitleCard"),
    (0, -1, 0),
    cols["TITLE_CARD_CONTROLS"],
)
ctrl["title_fade_in_frames"] = title_fade
ctrl["date_fade_in_frames"] = date_fade
ctrl["title_hold_duration_frames"] = title_hold
ctrl["date_hold_duration_frames"] = date_hold
ctrl["letter_spacing"] = spacing
ctrl["final_fade_out_enabled"] = final_out_on
ctrl["background_colour_hex"] = (CTRL.get("background_colour") or {}).get("hex", "#0A0A0A")
ctrl["type_colour_hex"] = (CTRL.get("type_colour") or {}).get("hex", "#E8E4DC")

# Timing from sequence markers
seq = {s["id"]: s for s in (data.get("sequence_after_emotional_ending") or [])}
f_black = int((seq.get("TC_FADE_NEAR_BLACK") or {}).get("local_frame") or 40)
f_title = int((seq.get("TC_TITLE_FADE_IN") or {}).get("local_frame") or 52)
f_date = int((seq.get("TC_DATE_FADE_IN") or {}).get("local_frame") or 70)
final_meta = (data.get("markers") or {}).get("TITLE_CARD_FINAL") or {}
f_final_start = int(final_meta.get("frame_start") or f_title)
f_final_end = int(final_meta.get("frame_end") or data.get("scene_frame_end") or 148)

# Title fade in then hold
set_alpha_keyframes(
    mat_title,
    [
        (f_title - 1, 0.0),
        (f_title + title_fade, 1.0),
        (f_title + title_fade + title_hold, 1.0),
    ],
)
set_alpha_keyframes(
    mat_date,
    [
        (f_date - 1, 0.0),
        (f_date + date_fade, 1.0),
        (f_date + date_fade + date_hold, 1.0),
    ],
)

if final_out_on:
    out_start = f_final_end - final_out_frames
    set_alpha_keyframes(
        mat_title,
        [(out_start, 1.0), (f_final_end, 0.0)],
    )
    set_alpha_keyframes(
        mat_date,
        [(out_start, 1.0), (f_final_end, 0.0)],
    )

for s in data.get("sequence_after_emotional_ending") or []:
    ensure_marker(scene, s["marker"], s["local_frame"])

# TITLE_CARD_FINAL range: start marker + end marker + scene props
m_final = ensure_marker(scene, "TITLE_CARD_FINAL", f_final_start)
ensure_marker(scene, "TITLE_CARD_FINAL_END", f_final_end)
scene["TITLE_CARD_FINAL_frame_start"] = f_final_start
scene["TITLE_CARD_FINAL_frame_end"] = f_final_end
if m_final is not None:
    m_final["frame_end"] = f_final_end
    m_final["range"] = True

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
Path(data["report_out"]).write_text(
    json.dumps(
        {
            "created": created,
            "reused": reused,
            "skipped": skipped,
            "title": TITLE,
            "date": DATE,
            "TITLE_CARD_FINAL": [f_final_start, f_final_end],
            "final_fade_out": final_out_on,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"OINO_TITLE_CARD_OK {out}")
print(json.dumps({"title": TITLE, "date": DATE, "apostrophe": False}))
