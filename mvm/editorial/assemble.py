"""Editorial: FFmpeg mux + Remotion overlay hooks."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def find_ffmpeg() -> str | None:
    which = shutil.which("ffmpeg")
    if which:
        return which
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def mux_shot_with_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    start_sec: float = 0.0,
    duration_sec: float | None = None,
) -> dict[str, Any]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "ffmpeg not found on PATH"}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        str(audio_path),
    ]
    if duration_sec is not None:
        cmd += ["-t", f"{duration_sec:.3f}"]

    # If video is a directory of frames, encode first
    if video_path.is_dir():
        frames = sorted(video_path.glob("frame_*.png"))
        if not frames:
            return {"ok": False, "error": f"No frames in {video_path}"}
        tmp = output_path.with_suffix(".silent.mp4")
        enc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                "24",
                "-i",
                str(video_path / "frame_%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(tmp),
            ],
            capture_output=True,
            text=True,
        )
        if enc.returncode != 0:
            return {"ok": False, "error": enc.stderr[-1000:]}
        video_path = tmp

    cmd += [
        "-i",
        str(video_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    # Reorder: video then trimmed audio is cleaner
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        str(audio_path),
    ]
    if duration_sec is not None:
        cmd += ["-t", f"{duration_sec:.3f}"]
    cmd += [
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0 and output_path.exists(),
        "output": str(output_path),
        "stderr": proc.stderr[-1500:] if proc.returncode else "",
    }


def concat_shots(video_paths: list[Path], output_path: Path) -> dict[str, Any]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return {"ok": False, "error": "ffmpeg not found on PATH"}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = output_path.parent / "concat_list.txt"
    lines = []
    for p in video_paths:
        lines.append(f"file '{p.resolve().as_posix()}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    return {
        "ok": proc.returncode == 0 and output_path.exists(),
        "output": str(output_path),
        "stderr": proc.stderr[-1500:] if proc.returncode else "",
    }


def write_remotion_props(project_root: Path, shots: list[dict], beatmap: dict) -> Path:
    """Props JSON for Remotion lyric/title overlays (Phase 2 hook)."""
    editorial = project_root / "final" / "remotion_props.json"
    editorial.parent.mkdir(parents=True, exist_ok=True)
    props = {
        "fps": 24,
        "sections": beatmap.get("sections", []),
        "shots": [
            {
                "id": s["id"],
                "section": s["section"],
                "start": s["start"],
                "end": s["end"],
                "title": s.get("description", s["id"]),
            }
            for s in shots
        ],
        "overlay": {
            "showSectionTitles": True,
            "showBeatPulses": False,
        },
    }
    editorial.write_text(json.dumps(props, indent=2), encoding="utf-8")
    return editorial
