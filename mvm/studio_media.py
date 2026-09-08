"""Inspect craft preview media on disk — for Studio cinema stage."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mvm.schemas.models import XSheet

_FRAME_RE = re.compile(r"^frame_(\d+)\.(png|jpg|jpeg|ppm)$", re.I)


def preview_dir(root: Path, shot_id: str) -> Path:
    return root / "previews" / shot_id


def frames_dir(root: Path, shot_id: str) -> Path:
    return preview_dir(root, shot_id) / "frames"


def preview_mp4_path(root: Path, shot_id: str) -> Path:
    return preview_dir(root, shot_id) / "shot_preview.mp4"


def list_frame_files(root: Path, shot_id: str) -> list[Path]:
    d = frames_dir(root, shot_id)
    if not d.is_dir():
        return []
    files = [p for p in d.iterdir() if p.is_file() and _FRAME_RE.match(p.name)]
    return sorted(files, key=lambda p: int(_FRAME_RE.match(p.name).group(1)))  # type: ignore[union-attr]


def safe_frame_path(root: Path, shot_id: str, name: str) -> Path | None:
    """Resolve a frame filename under frames/; reject path traversal."""
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    if not _FRAME_RE.match(name):
        return None
    path = frames_dir(root, shot_id) / name
    try:
        path.resolve().relative_to(frames_dir(root, shot_id).resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def craft_status(root: Path, shot_id: str, xsheet: XSheet | None = None) -> dict[str, Any]:
    mp4 = preview_mp4_path(root, shot_id)
    frames = list_frame_files(root, shot_id)
    payload = preview_dir(root, shot_id) / "craft_payload.json"
    return {
        "shot_id": shot_id,
        "has_mp4": mp4.is_file(),
        "has_frames": bool(frames),
        "frame_count": len(frames),
        "expected_frames": xsheet.end_frame if xsheet else None,
        "fps": xsheet.fps if xsheet else None,
        "payload_exists": payload.is_file(),
        "mp4_mtime": mp4.stat().st_mtime if mp4.is_file() else None,
    }


def frames_manifest(
    root: Path,
    shot_id: str,
    slug: str,
    xsheet: XSheet | None = None,
) -> dict[str, Any]:
    files = list_frame_files(root, shot_id)
    key_frames = set()
    smear_frames = set()
    if xsheet and xsheet.timing_chart:
        key_frames = set(xsheet.timing_chart.get("key_frames") or [])
        smear_frames = set(xsheet.timing_chart.get("smear_frames") or [])

    # Also derive from cells if timing_chart empty
    if xsheet and not key_frames:
        for c in xsheet.cells:
            if c.layer == "character" and c.exposure == "key":
                key_frames.add(c.frame)
            if c.exposure == "smear":
                smear_frames.add(c.frame)

    frames_out: list[dict[str, Any]] = []
    for p in files:
        m = _FRAME_RE.match(p.name)
        assert m
        idx = int(m.group(1))
        frames_out.append(
            {
                "frame": idx,
                "name": p.name,
                "url": f"/api/projects/{slug}/shots/{shot_id}/frames/{p.name}",
                "is_key": idx in key_frames,
                "is_smear": idx in smear_frames,
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
        )

    mp4 = preview_mp4_path(root, shot_id)
    return {
        "shot_id": shot_id,
        "fps": xsheet.fps if xsheet else 24,
        "end_frame": xsheet.end_frame if xsheet else (frames_out[-1]["frame"] if frames_out else 0),
        "frame_count": len(frames_out),
        "has_mp4": mp4.is_file(),
        "preview_url": (
            f"/api/projects/{slug}/shots/{shot_id}/preview" if mp4.is_file() else None
        ),
        "key_frames": sorted(key_frames),
        "smear_frames": sorted(smear_frames),
        "frames": frames_out,
    }
