"""Drive installed Blender for hybrid 3D + Grease Pencil cel craft."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from mvm.schemas.models import Shot, StylePack, XSheet
from mvm.cel.masters import load_style_pack

ROOT = Path(__file__).resolve().parents[2]
BLENDER_SCRIPT = Path(__file__).resolve().parent / "scripts" / "craft_shot.py"


def find_blender() -> Path | None:
    env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_EXE")
    if env and Path(env).exists():
        return Path(env)
    candidates = [
        shutil.which("blender"),
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        "/usr/bin/blender",
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return None


def write_craft_payload(
    project_root: Path,
    shot: Shot,
    xsheet: XSheet,
    style_pack: str | StylePack,
    out_dir: Path,
) -> Path:
    pack = style_pack if isinstance(style_pack, StylePack) else load_style_pack(style_pack)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_root": str(project_root),
        "shot": shot.model_dump(mode="json"),
        "xsheet": xsheet.model_dump(mode="json"),
        "style": pack.model_dump(mode="json"),
        "output_dir": str(out_dir),
        "fps": xsheet.fps,
        "resolution": [1920, 1080],
    }
    path = out_dir / "craft_payload.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def render_shot(
    project_root: Path,
    shot: Shot,
    xsheet: XSheet,
    style_pack: str = "classic_cel",
    preview: bool = True,
    blender_path: Path | None = None,
    on_frame: Callable[[int, int, Path], None] | None = None,
) -> dict[str, Any]:
    """Run Blender headless. Falls back to a crafted OpenCV/numpy plate if Blender missing.

    ``on_frame(frame_index, total_frames, path)`` is invoked for fallback PNG writes
    so Studio can stream craft progress. Blender path may emit frames via dir poll.
    """
    out_dir = project_root / ("previews" if preview else "renders") / shot.id
    payload_path = write_craft_payload(project_root, shot, xsheet, style_pack, out_dir)

    blender = blender_path or find_blender()
    if blender is None:
        fallback = _fallback_render(payload_path, out_dir, xsheet, on_frame=on_frame)
        return {
            "ok": True,
            "engine": "fallback_cel_preview",
            "output": str(fallback),
            "payload": str(payload_path),
            "warning": "Blender not found; wrote procedural cel preview frames.",
        }

    cmd = [
        str(blender),
        "--background",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(payload_path),
    ]
    if preview:
        env = os.environ.copy()
        env["MVM_PREVIEW"] = "1"
    else:
        env = os.environ.copy()
        env["MVM_PREVIEW"] = "0"

    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    video = out_dir / "shot_preview.mp4"
    if proc.returncode != 0 and not video.exists():
        fallback = _fallback_render(payload_path, out_dir, xsheet, on_frame=on_frame)
        return {
            "ok": True,
            "engine": "fallback_cel_preview",
            "output": str(fallback),
            "payload": str(payload_path),
            "blender_stderr": proc.stderr[-2000:],
            "warning": "Blender failed; used procedural cel preview.",
        }
    return {
        "ok": proc.returncode == 0 or video.exists(),
        "engine": "blender",
        "output": str(video if video.exists() else out_dir),
        "payload": str(payload_path),
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def _fallback_render(
    payload_path: Path,
    out_dir: Path,
    xsheet: XSheet,
    on_frame: Callable[[int, int, Path], None] | None = None,
) -> Path:
    """Author frames from X-sheet without Blender — still craft-timed, not diffusion."""
    import numpy as np

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Minimal raw PPM sequence if Pillow missing
        return _ppm_fallback(out_dir, xsheet)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    shot = payload["shot"]
    style = payload["style"]
    w, h = 1280, 720
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    char_cells = {
        c["frame"]: c
        for c in payload["xsheet"]["cells"]
        if c["layer"] == "character"
    }
    fx_cells = {
        c["frame"]: c for c in payload["xsheet"]["cells"] if c["layer"] == "fx"
    }

    line = tuple(int(255 * c) for c in style.get("gp_line_settings", {}).get("color", [0, 0, 0, 1])[:3])
    bg_color = (245, 238, 228) if "ghibli" in style.get("id", "") else (18, 18, 28)
    if style.get("id") == "akira_chrome":
        bg_color = (12, 8, 24)
    elif style.get("id") == "classic_cel":
        bg_color = (240, 232, 220)

    total = xsheet.end_frame
    # Pose state machine from keys
    pose_phase = 0.0
    for f in range(1, total + 1):
        cell = char_cells.get(f, {"exposure": "hold"})
        exp = cell.get("exposure", "hold")
        if exp == "key":
            pose_phase = (pose_phase + 1.0) % 4
        elif exp == "breakdown":
            pose_phase += 0.35
        elif exp == "inbetween":
            pose_phase += 0.15
        elif exp == "smear":
            pose_phase += 0.8

        img = Image.new("RGB", (w, h), bg_color)
        draw = ImageDraw.Draw(img)

        # Simple crafted figure — silhouette changes with pose_phase
        cx, cy = w // 2, int(h * 0.55)
        sway = int(40 * np.sin(pose_phase))
        arm = int(50 * np.sin(pose_phase * 1.3))

        # Head
        draw.ellipse([cx - 40 + sway // 3, cy - 180, cx + 40 + sway // 3, cy - 100], outline=line, width=3)
        # Body
        draw.line([(cx + sway // 4, cy - 100), (cx, cy)], fill=line, width=4)
        # Arms
        draw.line([(cx, cy - 70), (cx - 70 - arm, cy - 20)], fill=line, width=3)
        draw.line([(cx, cy - 70), (cx + 70 + arm, cy - 10)], fill=line, width=3)
        # Legs
        draw.line([(cx, cy), (cx - 35 + sway, cy + 120)], fill=line, width=3)
        draw.line([(cx, cy), (cx + 35 - sway, cy + 120)], fill=line, width=3)

        if exp == "smear" or fx_cells.get(f, {}).get("exposure") == "smear":
            for i in range(6):
                y = cy - 40 + i * 18
                draw.line([(cx + 80, y), (cx + 200 + i * 10, y - 5)], fill=line, width=2)

        # Label craft metadata
        draw.text((24, 20), f"{shot['id']}  f{f}  {exp}", fill=line)
        draw.text((24, h - 40), f"cel:{shot['cel']['mode']}  pack:{style.get('id')}", fill=line)

        frame_path = frames_dir / f"frame_{f:04d}.png"
        img.save(frame_path)
        if on_frame is not None:
            on_frame(f, total, frame_path)

    # Try ffmpeg to encode
    video = out_dir / "shot_preview.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    if ffmpeg:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(xsheet.fps),
                "-i",
                str(frames_dir / "frame_%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(video),
            ],
            capture_output=True,
        )
        if video.exists():
            return video
    return frames_dir


def _ppm_fallback(out_dir: Path, xsheet: XSheet) -> Path:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    (frames_dir / "README.txt").write_text(
        f"Install Pillow or Blender to render. X-sheet frames: {xsheet.end_frame}\n",
        encoding="utf-8",
    )
    return frames_dir
