"""
Blender headless craft script — hybrid 3D layout + Grease Pencil cel performance.

Invoked as:
  blender --background --python craft_shot.py -- /path/to/craft_payload.json
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path


def _argv_payload() -> Path:
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        args = sys.argv[idx + 1 :]
        if args:
            return Path(args[0])
    raise SystemExit("Usage: blender --python craft_shot.py -- craft_payload.json")


def main() -> None:
    import bpy
    from mathutils import Euler, Vector

    payload_path = _argv_payload()
    data = json.loads(payload_path.read_text(encoding="utf-8"))
    shot = data["shot"]
    xsheet = data["xsheet"]
    style = data["style"]
    out_dir = Path(data["output_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = int(data.get("fps", 24))
    res = data.get("resolution", [1920, 1080])
    preview = os.environ.get("MVM_PREVIEW", "1") == "1"

    # Reset scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = int(xsheet["end_frame"])
    scene.render.resolution_x = int(res[0] // (2 if preview else 1))
    scene.render.resolution_y = int(res[1] // (2 if preview else 1))
    # PNG sequence is reliable; Blender's built-in FFMPEG often leaves empty/moov-less mp4s.
    frames_dir = out_dir / "frames"
    if frames_dir.exists():
        for old in frames_dir.glob("frame_*.png"):
            old.unlink()
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(frames_dir / "frame_")
    scene.render.use_file_extension = True
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "EEVEE") or True else "BLENDER_EEVEE"
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    if preview:
        try:
            scene.eevee.taa_render_samples = 8
        except Exception:
            pass
        try:
            scene.eevee.taa_samples = 8
        except Exception:
            pass

    # World / light
    world = bpy.data.worlds.new("MVMWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        if style.get("id") == "akira_chrome":
            bg.inputs[0].default_value = (0.05, 0.03, 0.1, 1)
        elif style.get("id") == "ghibli_atmosphere":
            bg.inputs[0].default_value = (0.55, 0.7, 0.85, 1)
        else:
            bg.inputs[0].default_value = (0.85, 0.82, 0.78, 1)

    sun = bpy.data.objects.new("KeyLight", bpy.data.lights.new("KeyLight", type="SUN"))
    scene.collection.objects.link(sun)
    sun.rotation_euler = Euler((math.radians(50), math.radians(20), 0), "XYZ")

    # 3D layout plate (toon-ish cube set)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "LayoutFloor"
    bpy.ops.mesh.primitive_cube_add(size=1.5, location=(0, 0, 0.75))
    block = bpy.context.active_object
    block.name = "SetBlock"

    mat = bpy.data.materials.new("ToonPlate")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs[0].default_value = (0.7, 0.65, 0.6, 1.0)
    links.new(emission.outputs[0], out.inputs[0])
    floor.data.materials.append(mat)
    block.data.materials.append(mat)

    # Camera from shot grammar
    cam_data = bpy.data.cameras.new("MVMCamera")
    cam = bpy.data.objects.new("MVMCamera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam_data.lens = float(shot.get("lens_mm", 35))
    cam_info = shot.get("camera", {})
    start = cam_info.get("start", {"loc": [0, -6, 1.6], "rot_deg": [75, 0, 0]})
    end = cam_info.get("end", start)
    cam.location = Vector(start["loc"])
    cam.rotation_euler = Euler([math.radians(a) for a in start["rot_deg"]], "XYZ")
    cam.keyframe_insert(data_path="location", frame=1)
    cam.keyframe_insert(data_path="rotation_euler", frame=1)
    cam.location = Vector(end["loc"])
    cam.rotation_euler = Euler([math.radians(a) for a in end.get("rot_deg", start["rot_deg"])], "XYZ")
    cam.keyframe_insert(data_path="location", frame=scene.frame_end)
    cam.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)

    # Grease Pencil character + FX layers (Blender 4.3+ GreasePencil v3 API)
    bpy.ops.object.grease_pencil_add(type="EMPTY")
    gp_obj = bpy.context.active_object
    gp_obj.name = "CelPerformance"
    gp_data = gp_obj.data
    gp_data.name = "CelPerformance"
    gp_obj.location = (0, 0, 1.2)

    # Clear default layer if present, then author character + fx
    while len(gp_data.layers) > 0:
        gp_data.layers.remove(gp_data.layers[0])
    layer_char = gp_data.layers.new("character")
    layer_fx = gp_data.layers.new("fx")

    line_w = float(style.get("gp_line_settings", {}).get("line_width", 3.0))
    line_col = style.get("gp_line_settings", {}).get("color", [0.05, 0.05, 0.08, 1.0])

    material = bpy.data.materials.new("GP_Line")
    bpy.data.materials.create_gpencil_data(material)
    try:
        material.grease_pencil.color = line_col
    except Exception:
        pass
    gp_data.materials.append(material)

    char_by_frame = {
        c["frame"]: c for c in xsheet["cells"] if c["layer"] == "character"
    }
    fx_by_frame = {c["frame"]: c for c in xsheet["cells"] if c["layer"] == "fx"}

    def draw_figure(drawing, phase: float, smear: bool = False) -> None:
        pts = []
        for i in range(12):
            a = (i / 12) * math.tau
            pts.append(
                (
                    math.cos(a) * 0.25 + 0.05 * math.sin(phase),
                    0.0,
                    0.9 + math.sin(a) * 0.25,
                )
            )
        sway = 0.15 * math.sin(phase)
        pts += [
            (0.0, 0.0, 0.65),
            (0.0, 0.0, 0.2),
            (-0.35 - sway, 0.0, 0.45),
            (0.35 + sway, 0.0, 0.4),
            (-0.2 + sway, 0.0, -0.5),
            (0.2 - sway, 0.0, -0.5),
        ]
        if smear:
            for i in range(5):
                pts.append((0.5 + i * 0.15, 0.0, 0.3 - i * 0.05))
        drawing.add_strokes([len(pts)])
        stroke = drawing.strokes[-1]
        stroke.material_index = 0
        radius = max(0.002, line_w * 0.004)
        for p, co in zip(stroke.points, pts):
            p.position = co
            p.radius = radius * (0.8 if not smear else 0.4)
            p.opacity = 1.0
        drawing.tag_positions_changed()

    phase = 0.0
    for f in range(1, scene.frame_end + 1):
        cell = char_by_frame.get(f, {"exposure": "hold"})
        exp = cell.get("exposure", "hold")
        if exp in ("key", "breakdown", "inbetween", "smear") or f == 1:
            if exp == "key":
                phase += 1.0
            elif exp == "breakdown":
                phase += 0.35
            elif exp == "inbetween":
                phase += 0.15
            elif exp == "smear":
                phase += 0.7
            fr = layer_char.frames.new(f)
            draw_figure(fr.drawing, phase, smear=(exp == "smear"))

        fx = fx_by_frame.get(f, {})
        if fx.get("exposure") == "smear":
            frx = layer_fx.frames.new(f)
            frx.drawing.add_strokes([4])
            stroke = frx.drawing.strokes[-1]
            for i, p in enumerate(stroke.points):
                p.position = (0.6 + i * 0.25, 0.0, 0.4 - i * 0.08)
                p.radius = max(0.002, line_w * 0.002)
                p.opacity = 0.7
            frx.drawing.tag_positions_changed()

    # Save blend for human craft continuation
    blend_path = out_dir / "shot_craft.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    # Render animation as PNG sequence
    bpy.ops.render.render(animation=True)

    # Encode durable H.264 plate with system ffmpeg (Blender FFMPEG mux is flaky here)
    import shutil
    import subprocess

    canonical = out_dir / "shot_preview.mp4"
    for stale in out_dir.glob("shot_preview*.mp4"):
        try:
            stale.unlink()
        except OSError:
            pass
    ffmpeg = shutil.which("ffmpeg")
    frame_pattern = str(frames_dir / "frame_%04d.png")
    if ffmpeg and list(frames_dir.glob("frame_*.png")):
        enc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                frame_pattern,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "23",
                "-movflags",
                "+faststart",
                str(canonical),
            ],
            capture_output=True,
            text=True,
        )
        if enc.returncode != 0:
            print(f"MVM_FFMPEG_FAIL {enc.stderr[-800:]}")
    print(f"MVM_RENDER_OK {out_dir} mp4={canonical.exists()}")


if __name__ == "__main__":
    main()
