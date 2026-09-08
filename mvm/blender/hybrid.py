"""Hybrid renderer — 3D layout/camera + Grease Pencil performance + style packs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mvm.blender.runner import find_blender, render_shot, write_craft_payload
from mvm.cel.masters import load_style_pack
from mvm.schemas.models import Shot, XSheet


def render_hybrid_shot(
    project_root: Path,
    shot: Shot,
    xsheet: XSheet,
    style_pack: str | None = None,
    preview: bool = True,
) -> dict[str, Any]:
    """
    Render one hybrid plate:
    - 3D set + camera grammar from style pack / shot.camera
    - Grease Pencil character & FX layers driven by X-sheet
    """
    pack_id = style_pack or shot.cel.masters_pack
    pack = load_style_pack(pack_id)
    # Ensure shot cel pack matches style for craft script
    shot.cel.masters_pack = pack.id
    return render_shot(
        project_root=project_root,
        shot=shot,
        xsheet=xsheet,
        style_pack=pack,
        preview=preview,
        blender_path=find_blender(),
    )


def prepare_hybrid_payload(
    project_root: Path,
    shot: Shot,
    xsheet: XSheet,
    style_pack: str,
) -> Path:
    out_dir = project_root / "previews" / shot.id
    return write_craft_payload(project_root, shot, xsheet, style_pack, out_dir)
