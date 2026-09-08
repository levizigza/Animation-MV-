"""Decision ledger — durable, user-visible craft/heuristic choices."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mvm.schemas.models import Beatmap, Shot, XSheet


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def decisions_path(project_root: Path) -> Path:
    return Path(project_root) / "decisions.json"


def load_decisions(project_root: Path) -> dict[str, Any]:
    path = decisions_path(project_root)
    if not path.exists():
        return {"version": 1, "events": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_decisions(project_root: Path, data: dict[str, Any]) -> Path:
    path = decisions_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def append_event(project_root: Path, event: dict[str, Any]) -> dict[str, Any]:
    data = load_decisions(project_root)
    event = {**event, "at": event.get("at") or _now()}
    data.setdefault("events", []).append(event)
    save_decisions(project_root, data)
    return data


def xsheet_summary(xsheet: XSheet) -> dict[str, Any]:
    char = [c for c in xsheet.cells if c.layer == "character"]
    return {
        "shot_id": xsheet.shot_id,
        "end_frame": xsheet.end_frame,
        "fps": xsheet.fps,
        "key_frames": [c.frame for c in char if c.exposure == "key"],
        "breakdown_frames": [c.frame for c in char if c.exposure == "breakdown"],
        "inbetween_frames": [c.frame for c in char if c.exposure == "inbetween"],
        "hold_frames": [c.frame for c in char if c.exposure == "hold"],
        "smear_frames": [c.frame for c in char if c.exposure == "smear"],
        "timing_chart": xsheet.timing_chart,
    }


def record_plan(
    project_root: Path,
    *,
    prompt: str,
    style_pack: str,
    beatmap: Beatmap,
    shots: list[Shot],
    xsheets: list[XSheet],
    analysis: dict[str, Any],
    verification: dict[str, Any],
    neurosymbolic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record heuristic planning decisions (not LLM; still must be visible)."""
    xs_by_id = {x.shot_id: x for x in xsheets}
    event: dict[str, Any] = {
            "type": "plan",
            "source": "agents.pipeline (deterministic heuristics)",
            "prompt": prompt,
            "style_pack": style_pack,
            "music": {
                "bpm": beatmap.bpm,
                "duration": beatmap.duration,
                "section_labels": [
                    {
                        "name": s.name,
                        "start": s.start,
                        "end": s.end,
                        "energy": s.energy,
                        "label_method": "energy_novelty_heuristic",
                    }
                    for s in beatmap.sections
                ],
                "beat_count": len(beatmap.beat_times),
                "onset_count": len(beatmap.onset_times),
            },
            "analysis": analysis,
            "verification": verification,
            "shots": [
                {
                    "id": sh.id,
                    "section": sh.section,
                    "cel": sh.cel.model_dump(mode="json"),
                    "camera_type": sh.camera.get("type"),
                    "xsheet": xsheet_summary(xs_by_id[sh.id]) if sh.id in xs_by_id else None,
                    "key_placement_rule": "downbeats_beats_onsets_filtered_by_cel_mode",
                    "smear_rule": "onset_density * smear_density * style.smear_bias"
                    if sh.cel.smear_on_accents
                    else "disabled",
                    "interpolation_note": (

                        "Inbetweens/breakdowns are exposure-sheet craft slots, "
                        "not hidden spline smoothing of final pixels."
                    ),
                }
                for sh in shots
            ],
    }
    if neurosymbolic is not None:
        event["neurosymbolic"] = neurosymbolic
        event["note"] = (
            "MIR/heuristic proposals grounded by symbolic craft rules; "
            "accepted items are suggestions only (applied=false)."
        )
    return append_event(project_root, event)


def record_cel_edit(
    project_root: Path,
    *,
    shot: Shot,
    xsheet: XSheet,
    changed_fields: list[str],
    approval_revoked: bool,
) -> dict[str, Any]:
    return append_event(
        project_root,
        {
            "type": "cel_edit",
            "source": "studio_or_api_patch",
            "shot_id": shot.id,
            "changed_fields": changed_fields,
            "approval_revoked": approval_revoked,
            "cel": shot.cel.model_dump(mode="json"),
            "xsheet_rebuilt": True,
            "xsheet": xsheet_summary(xsheet),
            "note": "Cel policy change rebuilt X-sheet; plan requires human re-approval before craft.",
        },
    )


def record_craft(
    project_root: Path,
    *,
    shot: Shot,
    xsheet: XSheet,
    craft_result: dict[str, Any],
) -> dict[str, Any]:
    return append_event(
        project_root,
        {
            "type": "craft",
            "source": "blender.runner",
            "shot_id": shot.id,
            "engine": craft_result.get("engine"),
            "output": craft_result.get("output"),
            "warning": craft_result.get("warning"),
            "xsheet": xsheet_summary(xsheet),
            "cel": shot.cel.model_dump(mode="json"),
            "note": (
                "fallback_cel_preview is X-sheet-timed silhouette craft, not diffusion. "
                "blender engine uses Grease Pencil + 3D layout from the same X-sheet."
            ),
        },
    )
