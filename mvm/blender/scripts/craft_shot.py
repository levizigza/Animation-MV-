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
    out_dir = Path(data["output_dir"])
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
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.filepath = str(out_dir / "shot_preview")
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "EEVEE") or True else "BLENDER_EEVEE"
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"

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

    # Grease Pencil character + FX layers
    gp_data = bpy.data.grease_pencils.new("CelPerformance")
    gp_obj = bpy.data.objects.new("CelPerformance", gp_data)
    scene.collection.objects.link(gp_obj)
    gp_obj.location = (0, 0, 1.2)

    layer_char = gp_data.layers.new("character", set_active=True)
    layer_fx = gp_data.layers.new("fx")

    line_w = float(style.get("gp_line_settings", {}).get("line_width", 3.0))
    line_col = style.get("gp_line_settings", {}).get("color", [0.05, 0.05, 0.08, 1.0])

    material = bpy.data.materials.new("GP_Line")
    bpy.data.materials.create_gpencil_data(material)
    material.grease_pencil.color = line_col
    gp_data.materials.append(material)

    char_by_frame = {
        c["frame"]: c for c in xsheet["cells"] if c["layer"] == "character"
    }
    fx_by_frame = {c["frame"]: c for c in xsheet["cells"] if c["layer"] == "fx"}

    def draw_figure(frame_obj, phase: float, smear: bool = False) -> None:
        stroke = frame_obj.strokes.new()
        stroke.display_mode = "3DSPACE"
        stroke.line_width = int(line_w * 10)
        pts = []
        # Head circle approx
        for i in range(12):
            a = (i / 12) * math.tau
            pts.append((math.cos(a) * 0.25 + 0.05 * math.sin(phase), 0, 0.9 + math.sin(a) * 0.25))
        # Spine / limbs
        sway = 0.15 * math.sin(phase)
        pts += [
            (0, 0, 0.65),
            (0, 0, 0.2),
            (-0.35 - sway, 0, 0.45),
            (0.35 + sway, 0, 0.4),
            (-0.2 + sway, 0, -0.5),
            (0.2 - sway, 0, -0.5),
        ]
        if smear:
            for i in range(5):
                pts.append((0.5 + i * 0.15, 0, 0.3 - i * 0.05))
        stroke.points.add(count=len(pts))
        for p, co in zip(stroke.points, pts):
            p.co = co
            p.pressure = 0.8 if not smear else 0.4

    phase = 0.0
    for f in range(1, scene.frame_end + 1):
        cell = char_by_frame.get(f, {"exposure": "hold"})
        exp = cell.get("exposure", "hold")
        # Holds reuse previous drawing — only author new GP frames on change
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
            draw_figure(fr, phase, smear=(exp == "smear"))

        fx = fx_by_frame.get(f, {})
        if fx.get("exposure") == "smear":
            frx = layer_fx.frames.new(f)
            stroke = frx.strokes.new()
            stroke.display_mode = "3DSPACE"
            stroke.line_width = int(line_w * 6)
            stroke.points.add(count=4)
            for i, p in enumerate(stroke.points):
                p.co = (0.6 + i * 0.25, 0, 0.4 - i * 0.08)
                p.pressure = 0.5

    # Save blend for human craft continuation
    blend_path = out_dir / "shot_craft.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    # Render animation
    bpy.ops.render.render(animation=True)
    print(f"MVM_RENDER_OK {out_dir}")


if __name__ == "__main__":
    main()
