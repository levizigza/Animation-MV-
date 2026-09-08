"""Build SymbolicCraftState — hard craft facts for grounding."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mvm.neurosymbolic.schemas import SymbolicCraftState, SymbolicPredicate
from mvm.schemas.lifecycle import intent_is_explicit
from mvm.schemas.models import Shot, XSheet


def _pred(name: str, holds: bool, value: Any = None, explanation: str = "") -> SymbolicPredicate:
    return SymbolicPredicate(
        name=name, holds=holds, value=value, explanation=explanation or name
    )


def build_symbolic_state(
    *,
    shot: Shot,
    xsheet: XSheet | None = None,
    style_pack: str = "",
    section_energy: float | None = None,
    allow_auto_smooth: bool = False,
    force_every_cue_to_motion: bool = False,
    timing_plan_id: str | None = None,
) -> SymbolicCraftState:
    """Derive inspectable symbolic predicates from craft artifacts."""
    intent_ok = intent_is_explicit(shot.intent)
    key_frames: list[int] = []
    smear_frames: list[int] = []
    key_pose_count = len(shot.key_pose_ids or [])

    if xsheet:
        chart = xsheet.timing_chart or {}
        key_frames = list(chart.get("key_frames") or [])
        smear_frames = list(chart.get("smear_frames") or [])
        if not key_frames:
            key_frames = [
                c.frame
                for c in xsheet.cells
                if c.layer == "character" and c.exposure == "key"
            ]
        if not smear_frames:
            smear_frames = [c.frame for c in xsheet.cells if c.exposure == "smear"]
        if key_pose_count == 0:
            key_pose_count = len(key_frames)

    tid = timing_plan_id or shot.timing_plan_id
    preds = [
        _pred(
            "intent_explicit",
            intent_ok,
            shot.intent.purpose if shot.intent else "",
            "Detailed animation requires explicit ShotIntent.purpose",
        ),
        _pred(
            "animatic_approved",
            bool(shot.animatic_approved),
            shot.animatic_approved,
            "Key poses unlock only after human animatic approval",
        ),
        _pred(
            "allow_auto_smooth_forbidden",
            allow_auto_smooth is False,
            allow_auto_smooth,
            "TimingPlan.allow_auto_smooth must remain false",
        ),
        _pred(
            "force_cue_to_motion_forbidden",
            force_every_cue_to_motion is False,
            force_every_cue_to_motion,
            "Sound must not force every cue to motion",
        ),
        _pred(
            "has_timing_plan",
            bool(tid),
            tid,
            "In-between review needs an independent TimingPlan",
        ),
        _pred(
            "has_character_keys",
            key_pose_count >= 2 or len(key_frames) >= 2,
            {"key_pose_count": key_pose_count, "key_frames": key_frames},
            "Readable craft usually needs ≥2 character keys",
        ),
    ]

    return SymbolicCraftState(
        shot_id=shot.id,
        lifecycle_state=getattr(shot.lifecycle_state, "value", str(shot.lifecycle_state)),
        animatic_approved=bool(shot.animatic_approved),
        intent_explicit=intent_ok,
        intent_purpose=(shot.intent.purpose if shot.intent else ""),
        allow_auto_smooth=False if allow_auto_smooth is False else True,
        force_every_cue_to_motion=bool(force_every_cue_to_motion),
        timing_plan_id=tid,
        key_pose_count=key_pose_count,
        key_frames=key_frames,
        smear_frames=smear_frames,
        cel_mode=shot.cel.mode if shot.cel else "full",
        style_pack=style_pack or (shot.cel.masters_pack if shot.cel else ""),
        section_energy=section_energy,
        predicates=preds,
    )


def load_symbolic_state_for_shot(
    root: Path,
    shot_id: str,
    *,
    style_pack: str = "",
    section_energy: float | None = None,
) -> SymbolicCraftState:
    """Load shot/xsheet from disk and build symbolic state."""
    import json

    shot = Shot.model_validate_json(
        (root / "shots" / f"{shot_id}.json").read_text(encoding="utf-8")
    )
    xs_path = root / "xsheets" / f"{shot_id}.json"
    xsheet = None
    if xs_path.exists():
        xsheet = XSheet.model_validate_json(xs_path.read_text(encoding="utf-8"))

    allow_smooth = False
    force_motion = False
    timing_id = shot.timing_plan_id
    if timing_id and (root / "timing" / f"{timing_id}.json").exists():
        timing = json.loads((root / "timing" / f"{timing_id}.json").read_text(encoding="utf-8"))
        allow_smooth = bool(timing.get("allow_auto_smooth", False))

    sound_ptr = root / "sound_plans" / f"shot_{shot_id}_latest.json"
    if sound_ptr.exists():
        sp = json.loads(sound_ptr.read_text(encoding="utf-8"))
        plan_id = sp.get("sound_plan_id")
        if plan_id and (root / "sound_plans" / f"{plan_id}.json").exists():
            plan = json.loads(
                (root / "sound_plans" / f"{plan_id}.json").read_text(encoding="utf-8")
            )
            force_motion = bool(plan.get("force_every_cue_to_motion", False))

    meta_pack = style_pack
    if not meta_pack and (root / "project.json").exists():
        meta = json.loads((root / "project.json").read_text(encoding="utf-8"))
        meta_pack = meta.get("style_pack") or ""

    return build_symbolic_state(
        shot=shot,
        xsheet=xsheet,
        style_pack=meta_pack,
        section_energy=section_energy,
        allow_auto_smooth=allow_smooth,
        force_every_cue_to_motion=force_motion,
        timing_plan_id=timing_id,
    )
