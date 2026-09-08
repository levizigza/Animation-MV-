# Invoked by build_oino_archive.py — builds SCN_02_OINO_ARCHIVE.
# Named objects/collections; preserves user work unless reset=true.

import json
import math
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy
from mathutils import Euler, Vector

SCENE = "SCN_02_OINO_ARCHIVE"
RESET = bool(data.get("reset", False))
FPS = int(data["fps"])
F0 = int(data["scene_frame_start"])
F1 = int(data["scene_frame_end"])
created, reused, skipped = [], [], []


def ensure_collection(name):
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
        created.append(f"col:{name}")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    else:
        reused.append(f"col:{name}")
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


def add_cylinder(name, loc, scale, col):
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


def add_text(name, body, loc, col, scale=0.15):
    if name in bpy.data.objects and not RESET:
        obj = bpy.data.objects[name]
        link(obj, col)
        reused.append(name)
        return obj
    if name in bpy.data.objects and RESET:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    curve = bpy.data.curves.new(name=name + "_Data", type="FONT")
    curve.body = body
    obj = bpy.data.objects.new(name, curve)
    obj.location = Vector(loc)
    obj.scale = (scale, scale, scale)
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
    light = bpy.data.lights.new(name=name + "_Data", type=ltype)
    light.energy = energy
    obj = bpy.data.objects.new(name, light)
    obj.location = Vector(loc)
    link(obj, col)
    created.append(name)
    return obj


def add_camera(name, loc, rot_deg, col, lens=35):
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
    obj.rotation_euler = Euler([math.radians(a) for a in rot_deg], "XYZ")
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
scene.render.fps = FPS
scene.frame_start = F0
scene.frame_end = F1
scene.render.resolution_x = int(data.get("resolution", [1920, 1080])[0])
scene.render.resolution_y = int(data.get("resolution", [1920, 1080])[1])
try:
    scene.render.engine = data.get("engine", "BLENDER_EEVEE_NEXT")
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

cols = {n: ensure_collection(n) for n in data["collections"]}

# Floor / shelves
add_plane("ARCHIVE_Floor", (0, 0, 0), (8, 8, 1), cols["ARCHIVE_PROPS"])
add_cube("ARCHIVE_Shelf", (-2.5, 1.5, 1.2), (2.5, 0.4, 2.0), cols["ARCHIVE_PROPS"])

# Reels + equipment
reels = cols["ARCHIVE_REELS"]
add_cylinder("PROP_FilmReel_A", (-1.5, 0.2, 0.35), (0.45, 0.08, 0.45), reels)
add_cylinder("PROP_FilmReel_B", (-0.7, 0.35, 0.35), (0.4, 0.08, 0.4), reels)
add_cylinder("PROP_FilmReel_C", (-1.1, -0.3, 0.35), (0.35, 0.08, 0.35), reels)
add_cube("PROP_OldProjector", (0.8, 1.2, 0.55), (0.7, 0.5, 0.5), reels)
add_cube("PROP_TapeDeck", (1.6, 1.1, 0.35), (0.6, 0.4, 0.25), reels)
add_cube("PROP_CRT_Monitor", (2.4, 1.0, 0.7), (0.55, 0.4, 0.5), reels)

# Documents / photos
docs = cols["ARCHIVE_DOCUMENTS"]
add_plane("DOC_Photo_Stack", (-2.0, -0.8, 0.52), (0.5, 0.35, 1), docs, rot=(5, 0, 12))
add_plane("DOC_Photo_Loose_A", (-1.4, -1.1, 0.51), (0.4, 0.28, 1), docs, rot=(8, 0, -20))
add_plane("DOC_Photo_Loose_B", (-2.3, -1.2, 0.51), (0.35, 0.25, 1), docs, rot=(3, 0, 35))
add_plane("DOC_Letter_Worn", (0.2, -1.0, 0.51), (0.55, 0.4, 1), docs, rot=(2, 0, -8))
add_plane("DOC_Ledger_Page", (0.7, -1.3, 0.505), (0.5, 0.35, 1), docs, rot=(1, 0, 15))
add_plane("DOC_Note_Fragment", (1.1, -0.9, 0.508), (0.25, 0.18, 1), docs, rot=(4, 0, -40))
add_plane("DOC_FamilyRegister_Damaged", (-0.3, -0.5, 0.52), (0.7, 0.5, 1), docs, rot=(6, 0, 5))
add_plane("DOC_Name_Handwritten", (0.0, -0.2, 0.53), (0.45, 0.2, 1), docs, rot=(0, 0, -5))
add_text("TXT_NamePlate_Fragment", "—nius / Oi…", (-2.2, 0.6, 1.6), docs, 0.08)
add_text("TXT_Date_Obscured", "19?? / 1—", (-1.6, 0.55, 1.45), docs, 0.06)

# Props: vine, thyrsus-mech, seal, bowl, stain, gates
props = cols["ARCHIVE_PROPS"]
add_cylinder("MOTIF_VineVein_Worn", (-0.2, 0.8, 0.15), (0.04, 0.04, 1.2), props)
bpy.data.objects["MOTIF_VineVein_Worn"].rotation_euler = Euler(
    (math.radians(90), 0, math.radians(25)), "XYZ"
)
add_uv_sphere("MOTIF_GrapeCluster_Worn", (0.15, 0.95, 0.25), (0.18, 0.14, 0.16), props)
# Mechanical broken thyrsus — staff + fractured head (not costume)
add_cylinder("PROP_BrokenThyrsus_Mech", (2.0, -0.2, 0.55), (0.05, 0.05, 1.1), props)
add_cube("PROP_BrokenThyrsus_Head", (2.0, -0.2, 1.15), (0.2, 0.12, 0.15), props)
# OINO seal
add_cylinder("PROP_Seal_OINO", (0.4, 0.1, 0.56), (0.12, 0.12, 0.04), props)
add_text("TXT_Seal_OINO", "OINO", (0.28, 0.02, 0.62), props, 0.05)
add_cylinder("PROP_ArchiveBowl", (1.2, 0.2, 0.45), (0.22, 0.22, 0.12), props)
# Water stain — wine only under amber light (material note via custom prop)
stain = add_plane("FX_WaterStain_ConditionalWine", (0.9, -0.4, 0.502), (0.6, 0.35, 1), props)
stain["wine_under_amber_only"] = True
stain["ordinary_reads_as"] = "water_damage"
add_cube("PROP_FilmGate", (-3.2, -2.5, 1.2), (0.15, 1.4, 1.8), props)
add_cube("PROP_FactoryGate", (3.5, -2.5, 1.4), (0.2, 2.0, 2.2), props)
add_cube("PROP_Threshold", (0.0, -3.2, 0.05), (2.5, 0.4, 0.1), props)
add_cylinder("PROP_Cable_FromVein", (0.5, 0.7, 0.12), (0.03, 0.03, 1.0), props)
bpy.data.objects["PROP_Cable_FromVein"].rotation_euler = Euler(
    (math.radians(90), 0, math.radians(-15)), "XYZ"
)
add_cube("Oino_Hand_Archive", (-1.35, 0.05, 0.55), (0.2, 0.12, 0.08), props)
add_uv_sphere("FX_ArchiveDust", (-1.0, 0.5, 1.8), (0.8, 0.8, 0.4), props)
add_uv_sphere("FX_SteamProxy", (3.2, 0.5, 1.6), (0.7, 0.7, 0.5), props)
add_text("TXT_DigitalLabel", "OINO_LABEL_0x1A", (0.0, -0.35, 0.7), props, 0.07)

# Ancestor vs reconstructed footage — clearly distinguished
anc = cols["ARCHIVE_FOOTAGE_ANCESTOR"]
add_plane("FOOTAGE_AncestorPlate_A", (-2.8, -0.2, 1.8), (0.7, 0.45, 1), anc, rot=(90, 0, 0))
add_plane("FOOTAGE_AncestorPlate_B", (-2.8, -0.2, 1.1), (0.7, 0.45, 1), anc, rot=(90, 0, 0))
add_text("LABEL_AncestorOrigin", "ORIGIN: ancestor camera", (-3.3, -0.5, 2.2), anc, 0.06)

rec = cols["ARCHIVE_FOOTAGE_RECONSTRUCTED"]
add_plane(
    "FOOTAGE_ReconstructedPlate_A", (2.8, -0.2, 1.8), (0.7, 0.45, 1), rec, rot=(90, 0, 0)
)
add_plane(
    "FOOTAGE_ReconstructedPlate_B", (2.8, -0.2, 1.1), (0.7, 0.45, 1), rec, rot=(90, 0, 0)
)
add_text(
    "LABEL_Reconstructed_Clear",
    "RECONSTRUCTED — not ancestor-shot",
    (2.2, -0.5, 2.2),
    rec,
    0.055,
)
# Visual distinction: reconstructed plates use wireframe-ish scale offset / empties
for n in ("FOOTAGE_ReconstructedPlate_A", "FOOTAGE_ReconstructedPlate_B"):
    if n in bpy.data.objects:
        bpy.data.objects[n]["footage_class"] = "reconstructed"
for n in ("FOOTAGE_AncestorPlate_A", "FOOTAGE_AncestorPlate_B"):
    if n in bpy.data.objects:
        bpy.data.objects[n]["footage_class"] = "ancestor_origin"

# Lineage insert (<2s) — damaged document look
lin = cols["ARCHIVE_LINEAGE_INSERT"]
insert = data["family_line_insert"]
add_plane(
    "DOC_Lineage_DamagedSheet",
    (0.0, -2.0, 1.4),
    (1.6, 0.55, 1),
    lin,
    rot=(85, 0, 8),
)
# Partly obscured / mistranslated fragments
add_text(
    "TXT_Lineage_Main",
    insert["text"],
    (-0.85, -2.05, 1.55),
    lin,
    0.09,
)
add_text("TXT_Lineage_Obscured", "Διόν… / Sta— / Rh…?", (-0.7, -2.15, 1.35), lin, 0.05)
add_text(
    "TXT_Lineage_CanonNote",
    "artistic canon · variant traditions",
    (-0.75, -2.25, 1.2),
    lin,
    0.04,
)
add_cube("DOC_Lineage_Patch_A", (0.55, -1.95, 1.5), (0.25, 0.08, 0.02), lin)
add_cube("DOC_Lineage_Patch_B", (-0.4, -2.1, 1.42), (0.2, 0.06, 0.02), lin)

# Hide lineage objects except during insert window via keyframes (simple hide_render)
fs, fe = int(insert["frame_start"]), int(insert["frame_end"])
assert fe - fs + 1 <= int(insert["max_frames_at_24fps"]) + 1
for n in (
    "DOC_Lineage_DamagedSheet",
    "TXT_Lineage_Main",
    "TXT_Lineage_Obscured",
    "TXT_Lineage_CanonNote",
    "DOC_Lineage_Patch_A",
    "DOC_Lineage_Patch_B",
):
    if n not in bpy.data.objects:
        continue
    obj = bpy.data.objects[n]
    obj.hide_render = True
    obj.hide_viewport = True
    obj.keyframe_insert(data_path="hide_render", frame=fs - 1)
    obj.keyframe_insert(data_path="hide_viewport", frame=fs - 1)
    obj.hide_render = False
    obj.hide_viewport = False
    obj.keyframe_insert(data_path="hide_render", frame=fs)
    obj.keyframe_insert(data_path="hide_viewport", frame=fs)
    obj.hide_render = True
    obj.hide_viewport = True
    obj.keyframe_insert(data_path="hide_render", frame=fe + 1)
    obj.keyframe_insert(data_path="hide_viewport", frame=fe + 1)

# Lights — amber reveal for wine-conditioned stain
lights = cols["ARCHIVE_LIGHTS"]
add_light("LIGHT_ArchiveKey", "AREA", (-1, -3, 4), 350, lights)
add_light("LIGHT_ArchiveFill", "AREA", (3, 1, 2.5), 80, lights)
amber = add_light("LIGHT_AmberReveal", "POINT", (0.9, -0.4, 1.2), 20, lights)
amber["activates_wine_read_on"] = "FX_WaterStain_ConditionalWine"

# Cameras
cams = cols["ARCHIVE_CAMERAS"]
c0 = add_camera("CAM_ARCHIVE_WIDE", (-4.5, -5.5, 2.2), (68, 0, -35), cams)
add_camera("CAM_ARCHIVE_DETAIL_HAND", (-2.2, -1.5, 1.0), (72, 0, -25), cams, lens=50)
add_camera("CAM_LINEAGE_INSERT", (0.0, -3.8, 1.6), (78, 0, 0), cams, lens=50)
add_camera("CAM_THRESHOLD", (0.5, -5.0, 1.4), (75, 0, 5), cams)
scene.camera = c0

# Markers: lineage + transitions
ensure_marker(scene, "INS_FAMILY_LINE_START", fs)
ensure_marker(scene, "INS_FAMILY_LINE_END", fe)
for tr in data.get("transitions", []):
    ensure_marker(scene, tr["marker_start"], tr["frame_start"])
    ensure_marker(scene, tr["marker_end"], tr["frame_end"])
    ensure_marker(scene, tr["id"], tr["frame_start"])

ensure_marker(scene, "ARCHIVE_OPEN", F0)
ensure_marker(scene, "ARCHIVE_CLOSE", F1)

# Custom scene notes
scene["genealogy_artistic_canon"] = True
scene["no_biological_superiority"] = True
scene["oino_archive"] = True
scene["lineage_insert_max_seconds"] = float(insert["max_duration_seconds"])

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
Path(data["report_out"]).write_text(
    json.dumps({"created": created, "reused": reused, "skipped": skipped}, indent=2),
    encoding="utf-8",
)
print(f"OINO_ARCHIVE_OK {out}")
print(
    json.dumps(
        {
            "created": len(created),
            "reused": len(reused),
            "skipped": len(skipped),
            "lineage_frames": fe - fs + 1,
        }
    )
)
