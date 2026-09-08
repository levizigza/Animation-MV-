# Invoked by setup_animatic.py — builds ANIMATIC_MASTER with proxies + cameras.
# Safe to re-run: named objects/collections reused unless reset=true.

import json
import math
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy
from mathutils import Euler, Vector

SCENE_NAME = "ANIMATIC_MASTER"
RESET = bool(data.get("reset", False))
FPS = int(data["fps"])
FRAME_END = int(data["final_frame"])
RES = data.get("resolution", [1920, 1080])

COLLECTION_NAMES = list(data["collections"])


def ensure_collection(name: str):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
    scene = bpy.context.scene
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def link_object(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def ensure_object(name: str, create_fn, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        return obj, False
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    obj = create_fn()
    obj.name = name
    link_object(obj, col)
    return obj, True


def mesh_obj(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    return obj


# --- Scene ---
if SCENE_NAME in bpy.data.scenes and not RESET:
    scene = bpy.data.scenes[SCENE_NAME]
else:
    if SCENE_NAME in bpy.data.scenes and RESET:
        bpy.data.scenes.remove(bpy.data.scenes[SCENE_NAME])
    # Start from empty-ish: new scene
    scene = bpy.data.scenes.new(SCENE_NAME)

bpy.context.window.scene = scene
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.resolution_x = int(RES[0])
scene.render.resolution_y = int(RES[1])
scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
try:
    scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

cols = {n: ensure_collection(n) for n in COLLECTION_NAMES}
created, reused, skipped = [], [], []

# --- Proxies (priority: hand, table, door/knock, sister, father, bowls) ---
prox = cols["ANIMATIC_PROXIES"]


def add_cube(name, loc, scale, col):
    def _c():
        mesh = bpy.data.meshes.new(name + "_Mesh")
        obj = mesh_obj(name, mesh)
        # Build cube via ops in context alternate: primitive then rename
        return obj

    # Prefer operators for simple primitives
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    link_object(obj, col)
    created.append(name)
    return obj


def add_uv_sphere(name, loc, scale, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    link_object(obj, col)
    created.append(name)
    return obj


def add_cylinder(name, loc, scale, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    link_object(obj, col)
    created.append(name)
    return obj


def add_plane(name, loc, scale, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    link_object(obj, col)
    created.append(name)
    return obj


# Floor / attic / table world
add_plane("PROXY_Floor", (0, 0, 0), (12, 12, 1), prox)
add_cube("PROXY_Attic", (-4, 0, 1.5), (2.5, 2.5, 1.5), prox)
add_cube("PROXY_AtticDoor", (-2.6, 0, 1.2), (0.15, 1.0, 1.8), prox)
# Priority: table + bowls + hand
add_cube("PROP_Table", (3.5, 0, 0.45), (2.2, 1.2, 0.12), prox)
add_cylinder("PROP_TableLeg_A", (2.7, -0.4, 0.2), (0.08, 0.08, 0.4), prox)
add_cylinder("PROP_TableLeg_B", (4.3, 0.4, 0.2), (0.08, 0.08, 0.4), prox)
add_cylinder("PROP_Bowl_L", (3.1, 0.2, 0.55), (0.25, 0.25, 0.12), prox)
add_cylinder("PROP_Bowl_R", (3.9, -0.15, 0.55), (0.25, 0.25, 0.12), prox)
# Proxy characters (capsule-ish)
add_uv_sphere("PROXY_Oino_Head", (-3.5, -0.8, 1.7), (0.35, 0.35, 0.35), prox)
add_cube("PROXY_Oino_Body", (-3.5, -0.8, 1.0), (0.4, 0.25, 0.7), prox)
add_cube("Oino_Hand", (-3.1, -0.5, 1.05), (0.18, 0.12, 0.08), prox)
add_uv_sphere("PROXY_Sister_Head", (5.5, 1.5, 1.6), (0.32, 0.32, 0.32), prox)
add_cube("PROXY_Sister_Body", (5.5, 1.5, 0.95), (0.35, 0.22, 0.65), prox)
add_uv_sphere("PROXY_Father_Head", (3.5, -1.2, 1.55), (0.34, 0.34, 0.34), prox)
add_cube("PROXY_Father_Body", (3.5, -1.2, 0.95), (0.38, 0.22, 0.65), prox)
add_cube("PROP_Recording", (-3.2, -1.4, 0.9), (0.35, 0.2, 0.08), prox)
add_cube("PROP_Archive", (-4.5, 1.2, 0.8), (0.8, 0.5, 0.4), prox)
# Era blocks (changing world — not detailed)
add_cube("PROXY_Era_Steam", (0, 3, 1), (1.2, 0.8, 1.5), prox)
add_cube("PROXY_Era_Electric", (2, 3, 1), (1.2, 0.8, 1.5), prox)
add_cube("PROXY_Era_Digital", (4, 3, 1), (1.2, 0.8, 1.5), prox)
add_cube("PROXY_Era_Future", (6, 3, 1), (1.2, 0.8, 1.5), prox)
add_cube("PROXY_Care", (1, -3, 1), (0.8, 0.8, 1.2), prox)
add_cube("PROXY_Harm", (2.5, -3, 1), (0.8, 0.8, 1.2), prox)
add_cylinder("PROXY_ZonePassage", (0, -5, 1.5), (1.2, 1.2, 3.0), prox)

# Dionysus echoes — sparse primitives, not a literal god
echo = cols["ANIMATIC_DIONYSUS_ECHOES"]
add_cylinder("ECHO_VineCoil", (-1, 2, 0.5), (0.15, 0.15, 1.5), echo)
add_uv_sphere("ECHO_WineLight", (3.5, 0, 2.2), (0.4, 0.4, 0.4), echo)
add_cube("ECHO_Mask", (0.5, -1, 1.8), (0.35, 0.1, 0.45), echo)

# --- Lights ---
lights = cols["ANIMATIC_LIGHTS"]


def ensure_light(name, ltype, loc, energy, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    light = bpy.data.lights.new(name=name + "_Data", type=ltype)
    light.energy = energy
    obj = bpy.data.objects.new(name, light)
    obj.location = loc
    link_object(obj, col)
    created.append(name)
    return obj


ensure_light("LIGHT_Key", "AREA", (2, -4, 5), 400, lights)
ensure_light("LIGHT_Fill", "AREA", (-4, 2, 3), 120, lights)
ensure_light("LIGHT_WineEcho", "POINT", (3.5, 0, 2.4), 80, lights)

# --- Cameras per shot ---
cams = cols["ANIMATIC_CAMERAS"]
shot_list = data["shots"]

# Simple camera placements keyed by shot index
cam_rigs = [
    ((-5.5, -4.0, 1.6), (75, 0, -35)),   # SH010 attic / door
    ((-2.5, -2.5, 1.3), (70, 0, -20)),   # SH020 tape / hand
    ((-5.0, 0.5, 1.5), (72, 0, -10)),    # SH030 archive
    ((-1.0, -3.0, 1.8), (68, 0, 10)),    # SH040 melody opens
    ((3.0, -6.0, 2.5), (65, 0, 0)),      # SH050 eras
    ((1.5, -5.0, 1.8), (70, 0, 5)),      # SH060 care/harm
    ((0.0, -8.0, 1.5), (78, 0, 0)),      # SH070 zone
    ((3.5, -4.0, 1.4), (72, 0, 0)),      # SH080 table father
    ((3.2, -3.0, 1.3), (70, 0, 15)),     # SH090 rewind
    ((3.5, -2.2, 1.1), (85, 0, 0)),      # SH100 reflection
    ((4.0, -3.5, 1.5), (70, 0, -10)),    # SH110 release
    ((5.0, -3.0, 1.5), (72, 0, 20)),     # SH120 sister note
    ((0.0, -6.0, 1.8), (90, 0, 0)),      # SH130 title
]


def ensure_camera(name, loc, rot_deg, col):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    cam_data = bpy.data.cameras.new(name + "_Data")
    cam_data.lens = 35
    obj = bpy.data.objects.new(name, cam_data)
    obj.location = Vector(loc)
    obj.rotation_euler = Euler([math.radians(a) for a in rot_deg], "XYZ")
    link_object(obj, col)
    created.append(name)
    return obj


for i, shot in enumerate(shot_list):
    loc, rot = cam_rigs[min(i, len(cam_rigs) - 1)]
    cam = ensure_camera(shot["camera"], loc, rot, cams)
    # Marker-driven camera bind via timeline markers only; set first cam active
    if i == 0:
        scene.camera = cam

# --- Text markers (shot labels + title) ---
text_col = cols["ANIMATIC_TEXT"]


def ensure_text(name, body, loc, col, scale=0.4):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link_object(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    curve = bpy.data.curves.new(name=name + "_Curve", type="FONT")
    curve.body = body
    obj = bpy.data.objects.new(name, curve)
    obj.location = Vector(loc)
    obj.scale = (scale, scale, scale)
    link_object(obj, col)
    created.append(name)
    return obj


for shot in shot_list:
    ensure_text(
        f"TXT_{shot['id']}",
        shot["id"].replace("_", " "),
        (0, -7.5, 0.2 + shot_list.index(shot) * 0.05),
        text_col,
        scale=0.25,
    )

title = data.get("title_card") or {}
ensure_text(
    "TXT_TITLE_CARD",
    title.get("text", "One Of God's Fools"),
    (0, 0, 3.2),
    text_col,
    scale=0.55,
)
ensure_text(
    "TXT_RELEASE_DATE",
    title.get("release_date", "2026-12-10"),
    (0, 0, 2.6),
    text_col,
    scale=0.35,
)

# --- Audio on VSE ---
audio_col = cols["ANIMATIC_AUDIO"]
if not scene.sequence_editor:
    scene.sequence_editor_create()
sed = scene.sequence_editor
if RESET:
    for s in list(sed.sequences_all):
        sed.sequences.remove(s)

music = data.get("music_path")
if music:

    def ensure_sound(name, path, channel):
        existing = sed.sequences.get(name) if hasattr(sed, "sequences") else None
        # Blender 4 uses sequences_all / new API variants
        try:
            seqs = sed.sequences
        except Exception:
            seqs = sed.sequences_all
        existing = None
        for s in sed.sequences_all:
            if s.name == name:
                existing = s
                break
        if existing and not RESET:
            reused.append(name)
            return existing
        if existing and RESET:
            sed.sequences.remove(existing)
        strip = sed.sequences.new_sound(
            name=name, filepath=path, channel=channel, frame_start=1
        )
        created.append(name)
        return strip

    ensure_sound("ANIMATIC_MUSIC", music, 1)
    if data.get("narration_path"):
        ensure_sound("ANIMATIC_NARRATION", data["narration_path"], 2)

# Empty null for audio collection bookkeeping
if "AUDIO_ANCHOR" not in bpy.data.objects:
    anchor = bpy.data.objects.new("AUDIO_ANCHOR", None)
    link_object(anchor, audio_col)
    created.append("AUDIO_ANCHOR")
else:
    link_object(bpy.data.objects["AUDIO_ANCHOR"], audio_col)
    reused.append("AUDIO_ANCHOR")

# --- Timeline markers: shots, story circle, monologue, music cues ---
def ensure_marker(name, frame):
    if name in scene.timeline_markers:
        if not RESET:
            skipped.append(f"marker:{name}")
            return
        scene.timeline_markers.remove(scene.timeline_markers[name])
    m = scene.timeline_markers.new(name, frame=int(frame))
    m.name = name
    created.append(f"marker:{name}")


for shot in shot_list:
    ensure_marker(shot["id"], shot["frame_start"])
    ensure_marker(shot["id"] + "_END", shot["frame_end"])

for sc in data.get("story_circle_beats", []):
    ensure_marker(sc["name"], sc["frame"])

for mono in data.get("monologue_anchors", []):
    ensure_marker(mono["name"], mono["frame"])

for cue in data.get("music_cues", []):
    ensure_marker(cue["name"], cue["frame"])

for sm in data.get("structural_audio_markers", []):
    ensure_marker(sm["name"], sm["frame"])

# Bind camera switches via markers (timeline marker camera attribute if available)
for shot in shot_list:
    cam_name = shot["camera"]
    if cam_name in bpy.data.objects and shot["id"] in scene.timeline_markers:
        marker = scene.timeline_markers[shot["id"]]
        try:
            marker.camera = bpy.data.objects[cam_name]
        except Exception:
            pass

scene["oino_animatic"] = True
scene["vse_timeline_name"] = "AUDIO_TIMELINE"

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))

report = {
    "created": created,
    "reused": reused,
    "skipped": skipped,
    "blend": str(out),
}
Path(data["report_out"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"OINO_ANIMATIC_MASTER_OK {out}")
print(json.dumps({"created": len(created), "reused": len(reused), "skipped": len(skipped)}))
