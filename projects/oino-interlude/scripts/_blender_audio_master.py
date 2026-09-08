# Auto-generated helper — invoked by setup_audio.py
import json
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy

# Preserve user work: only rebuild named scene if missing or reset flag
reset = data.get("reset", False)
scene_name = "AUDIO_MASTER"
vse_name = "AUDIO_TIMELINE"

if scene_name in bpy.data.scenes and not reset:
    scene = bpy.data.scenes[scene_name]
else:
    if scene_name in bpy.data.scenes and reset:
        bpy.data.scenes.remove(bpy.data.scenes[scene_name])
    scene = bpy.data.scenes.new(scene_name)

bpy.context.window.scene = scene
fps = int(data["fps"])
scene.render.fps = fps
scene.frame_start = 1
scene.frame_end = int(data["final_frame"])
scene.render.resolution_x = int(data["resolution"][0])
scene.render.resolution_y = int(data["resolution"][1])

if not scene.sequence_editor:
    scene.sequence_editor_create()
sed = scene.sequence_editor
# Clear only strips we own on reset
if reset:
    for s in list(sed.sequences_all):
        sed.sequences.remove(s)

def ensure_sound(name, path, channel, frame_start):
    existing = sed.sequences.get(name)
    if existing and not reset:
        return existing
    if existing and reset:
        sed.sequences.remove(existing)
    return sed.sequences.new_sound(name=name, filepath=path, channel=channel, frame_start=frame_start)

music = data["music_path"]
ensure_sound("MUSIC_MASTER", music, channel=1, frame_start=1)
if data.get("narration_path"):
    ensure_sound("NARRATION", data["narration_path"], channel=2, frame_start=1)

# Timeline markers
for m in data["markers"]:
    name = m["name"]
    frame = int(m["frame"])
    if name in scene.timeline_markers:
        if not reset:
            continue
        scene.timeline_markers.remove(scene.timeline_markers[name])
    marker = scene.timeline_markers.new(name, frame=frame)
    marker.name = name

# Store VSE logical name as custom property
scene["vse_timeline_name"] = vse_name
scene["oino_audio_setup"] = True

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print(f"OINO_AUDIO_MASTER_OK {out}")
