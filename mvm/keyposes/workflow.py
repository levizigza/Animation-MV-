"""Key-pose-first workflow: mark keys, arcs, suggest in-betweens with human accept.

Approved key poses are never rewritten automatically. Suggestions are preview-only
until accept / partial accept. Missing information is surfaced instead of guessed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.domain import (
    ActorKind,
    InBetweenSlot,
    InBetweenSuggestion,
    KeyPose,
    SpacingMode,
    TimingSource,
    make_provenance,
    new_id,
)
from mvm.schemas.lifecycle import apply_generated_inbetweens
from mvm.schemas.models import ApprovalState, Shot
from mvm.timing.curves import progress_at
from mvm.timing.workflow import load_timing_plan, save_key_pose, save_timing_plan


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_keypose_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "key_poses").mkdir(parents=True, exist_ok=True)
    (root / "suggestions").mkdir(parents=True, exist_ok=True)
    (root / "shots").mkdir(parents=True, exist_ok=True)


def load_key_pose(root: Path, pose_id: str) -> KeyPose:
    return KeyPose.model_validate(_read(root / "key_poses" / f"{pose_id}.json"))


def load_suggestion(root: Path, suggestion_id: str) -> InBetweenSuggestion:
    return InBetweenSuggestion.model_validate(
        _read(root / "suggestions" / f"{suggestion_id}.json")
    )


def save_suggestion(root: Path, suggestion: InBetweenSuggestion) -> Path:
    ensure_keypose_dirs(root)
    path = root / "suggestions" / f"{suggestion.id}.json"
    _write(path, suggestion)
    return path


def _load_shot(root: Path, shot_id: str) -> Shot:
    return Shot.model_validate(_read(root / "shots" / f"{shot_id}.json"))


def _save_shot(root: Path, shot: Shot) -> None:
    _write(root / "shots" / f"{shot.id}.json", shot)


def _pose_content_fingerprint(pose: KeyPose) -> dict[str, Any]:
    """Fields that constitute pose *content* (must not auto-rewrite when approved)."""
    return {
        "frame": pose.frame,
        "label": pose.label,
        "description": pose.description,
        "action": pose.action,
        "intention": pose.intention,
        "asset_ref": pose.asset_ref,
        "layer": pose.layer,
        "arc": pose.arc.model_dump(mode="json"),
    }


def _refuse_approved_rewrite(existing: KeyPose, updated: KeyPose) -> None:
    if existing.approval != ApprovalState.APPROVED:
        return
    if _pose_content_fingerprint(existing) != _pose_content_fingerprint(updated):
        raise PermissionError(
            f"Refusing to rewrite approved key pose {existing.id}. "
            "Reject the pose first, or create a new revision via human reject/restore."
        )


def mark_key_pose(
    root: Path,
    *,
    shot_id: str,
    frame: int,
    label: str = "",
    pose_id: str | None = None,
    description: str = "",
) -> KeyPose:
    """Create or mark a drawing as a key pose (is_extreme + marked_as_key)."""
    ensure_keypose_dirs(root)
    if pose_id and (root / "key_poses" / f"{pose_id}.json").exists():
        pose = load_key_pose(root, pose_id)
        if pose.approval == ApprovalState.APPROVED and pose.frame != frame:
            raise PermissionError(
                f"Cannot reframe approved key pose {pose_id} automatically."
            )
        updated = pose.model_copy(deep=True)
        updated.marked_as_key = True
        updated.is_extreme = True
        if label:
            updated.label = label
        if description:
            updated.description = description
        _refuse_approved_rewrite(pose, updated)
        save_key_pose(root, updated)
        pose = updated
    else:
        pose = KeyPose(
            id=pose_id or new_id("pose"),
            shot_id=shot_id,
            frame=frame,
            label=label or f"key@{frame}",
            description=description,
            is_extreme=True,
            marked_as_key=True,
            approval=ApprovalState.DRAFT,
        )
        save_key_pose(root, pose)

    shot_path = root / "shots" / f"{shot_id}.json"
    if shot_path.exists():
        shot = _load_shot(root, shot_id)
        if pose.id not in shot.key_pose_ids:
            shot = shot.model_copy(deep=True)
            shot.key_pose_ids = list(shot.key_pose_ids) + [pose.id]
            _save_shot(root, shot)
        if shot.timing_plan_id:
            plan = load_timing_plan(root, shot.timing_plan_id)
            if pose.id not in plan.key_pose_ids:
                plan = plan.model_copy(deep=True)
                plan.key_pose_ids = list(plan.key_pose_ids) + [pose.id]
                save_timing_plan(root, plan)

    rev, prov = attribute_suggestion(
        operation="human.mark_key_pose",
        target_type="key_pose",
        target_id=pose.id,
        snapshot=pose.model_dump(mode="json"),
        summary=f"Marked key pose {pose.id} @f{pose.frame}",
    )
    pose = pose.model_copy(deep=True)
    pose.revision_id = rev.id
    save_key_pose(root, pose)
    save_revision(root, rev)
    save_provenance(root, prov)
    return pose


def set_pose_action(
    root: Path,
    pose_id: str,
    *,
    action: str = "",
    intention: str = "",
) -> KeyPose:
    """Attach action / intention to a key pose. Refuses approved content rewrite."""
    existing = load_key_pose(root, pose_id)
    updated = existing.model_copy(deep=True)
    if action:
        updated.action = action
    if intention:
        updated.intention = intention
    if not (updated.action.strip() or updated.intention.strip()):
        raise ValueError("Provide a non-empty action and/or intention")
    _refuse_approved_rewrite(existing, updated)
    save_key_pose(root, updated)
    return updated


def set_anticipation_follow_through(
    root: Path,
    pose_id: str,
    *,
    anticipation_frames: int | None = None,
    follow_through_frames: int | None = None,
    anticipation_notes: str = "",
    follow_through_notes: str = "",
) -> KeyPose:
    """Define anticipation / follow-through. Pass ints (incl. 0) to set explicitly."""
    existing = load_key_pose(root, pose_id)
    updated = existing.model_copy(deep=True)
    arc = updated.arc.model_copy(deep=True)
    if anticipation_frames is not None:
        arc.anticipation_frames = anticipation_frames
    if follow_through_frames is not None:
        arc.follow_through_frames = follow_through_frames
    if anticipation_notes:
        arc.anticipation_notes = anticipation_notes
    if follow_through_notes:
        arc.follow_through_notes = follow_through_notes
    updated.arc = arc
    _refuse_approved_rewrite(existing, updated)
    save_key_pose(root, updated)
    return updated


def approve_key_pose(root: Path, pose_id: str, *, comment: str = "") -> KeyPose:
    pose = load_key_pose(root, pose_id).model_copy(deep=True)
    pose.approval = ApprovalState.APPROVED
    pose.marked_as_key = True
    pose.is_extreme = True
    rev, prov = attribute_suggestion(
        operation="human.approve_key_pose",
        target_type="key_pose",
        target_id=pose.id,
        snapshot=pose.model_dump(mode="json"),
        summary=comment or f"Approved key pose {pose.id}",
    )
    pose.revision_id = rev.id
    save_key_pose(root, pose)
    save_revision(root, rev)
    save_provenance(root, prov)
    return pose


def reject_key_pose(root: Path, pose_id: str, *, comment: str) -> KeyPose:
    if not comment.strip():
        raise ValueError("Rejecting a key pose requires a comment")
    pose = load_key_pose(root, pose_id).model_copy(deep=True)
    pose.approval = ApprovalState.REJECTED
    rev, prov = attribute_suggestion(
        operation="human.reject_key_pose",
        target_type="key_pose",
        target_id=pose.id,
        snapshot={"pose": pose.model_dump(mode="json"), "comment": comment},
        summary=comment,
    )
    pose.revision_id = rev.id
    save_key_pose(root, pose)
    save_revision(root, rev)
    save_provenance(root, prov)
    return pose


def missing_information_for_suggestion(
    *,
    from_pose: KeyPose,
    to_pose: KeyPose,
    timing_plan_id: str | None,
    spacing_mode: SpacingMode | str | None,
) -> list[str]:
    """List what is missing for a useful suggestion — never invent these."""
    missing: list[str] = []
    if not from_pose.marked_as_key and not from_pose.is_extreme:
        missing.append(f"from pose {from_pose.id} is not marked as a key pose")
    if not to_pose.marked_as_key and not to_pose.is_extreme:
        missing.append(f"to pose {to_pose.id} is not marked as a key pose")
    if from_pose.shot_id != to_pose.shot_id:
        missing.append("from/to key poses belong to different shots")
    if to_pose.frame - from_pose.frame < 2:
        missing.append(
            f"need at least one frame between keys "
            f"(from f{from_pose.frame} to f{to_pose.frame})"
        )
    if not (from_pose.action.strip() or from_pose.intention.strip()):
        missing.append(
            f"from pose {from_pose.id} needs an action or intention "
            "(set via set_pose_action)"
        )
    if not (to_pose.action.strip() or to_pose.intention.strip()):
        missing.append(
            f"to pose {to_pose.id} needs an action or intention "
            "(set via set_pose_action)"
        )
    if from_pose.arc.anticipation_frames is None:
        missing.append(
            f"anticipation_frames unset on {from_pose.id} "
            "(set explicitly, use 0 for none)"
        )
    if to_pose.arc.follow_through_frames is None:
        missing.append(
            f"follow_through_frames unset on {to_pose.id} "
            "(set explicitly, use 0 for none)"
        )
    if not timing_plan_id:
        missing.append("timing_plan_id required (timing stored independently of pixels)")
    if spacing_mode is None or spacing_mode == "":
        missing.append(
            "spacing_mode required (linear|stepped|slow_in|slow_out|slow_in_out|custom) "
            "— will not guess or auto-smooth"
        )
    return missing


def suggest_inbetweens(
    root: Path,
    *,
    from_key_pose_id: str,
    to_key_pose_id: str,
    spacing_mode: SpacingMode | str | None = None,
    timing_plan_id: str | None = None,
    step_count: int = 2,
) -> dict[str, Any]:
    """Request suggested in-betweens. Non-destructive. Surfaces missing info."""
    ensure_keypose_dirs(root)
    from_pose = load_key_pose(root, from_key_pose_id)
    to_pose = load_key_pose(root, to_key_pose_id)

    plan_id = timing_plan_id
    shot_path = root / "shots" / f"{from_pose.shot_id}.json"
    if not plan_id and shot_path.exists():
        plan_id = _load_shot(root, from_pose.shot_id).timing_plan_id

    mode: SpacingMode | None = None
    if spacing_mode is not None and spacing_mode != "":
        mode = (
            spacing_mode
            if isinstance(spacing_mode, SpacingMode)
            else SpacingMode(str(spacing_mode))
        )

    missing = missing_information_for_suggestion(
        from_pose=from_pose,
        to_pose=to_pose,
        timing_plan_id=plan_id,
        spacing_mode=mode,
    )
    suggestion = InBetweenSuggestion(
        id=new_id("sug"),
        shot_id=from_pose.shot_id,
        timing_plan_id=plan_id or "",
        from_key_pose_id=from_pose.id,
        to_key_pose_id=to_pose.id,
        status="blocked" if missing else "preview",
        spacing_mode=mode.value if mode else "",
        missing_information=missing,
        rationale="",
        applied_to_timing=False,
        created_by=ActorKind.HEURISTIC_AGENT,
    )

    if missing:
        suggestion.rationale = (
            "Insufficient information for a useful suggestion. "
            "No slots generated — refusing to guess."
        )
        save_suggestion(root, suggestion)
        rev, prov = attribute_suggestion(
            operation="agents.suggest_inbetweens_blocked",
            target_type="timing_plan",
            target_id=plan_id or from_pose.shot_id,
            snapshot=suggestion.model_dump(mode="json"),
            summary=suggestion.rationale,
            outputs={"missing_information": missing},
        )
        suggestion.revision_id = rev.id
        save_suggestion(root, suggestion)
        save_revision(root, rev)
        save_provenance(root, prov)
        return {
            "ok": False,
            "suggestion": suggestion,
            "missing_information": missing,
            "reason": suggestion.rationale,
        }

    assert mode is not None and plan_id
    plan_before = load_timing_plan(root, plan_id).model_dump(mode="json")
    from mvm.schemas.domain import SpacingCurve

    curve = SpacingCurve(
        id=new_id("curve"),
        mode=mode,
        step_count=step_count,
        source=TimingSource.GENERATED,
        suggested_by_operation="agents.suggest_inbetweens",
        notes="Preview suggestion only — not applied until accept",
    )
    span = to_pose.frame - from_pose.frame
    ant = from_pose.arc.anticipation_frames or 0
    ft = to_pose.arc.follow_through_frames or 0
    slots: list[InBetweenSlot] = []
    for f in range(from_pose.frame + 1, to_pose.frame):
        # Anticipation window stays near outgoing key; follow-through near incoming
        near_start = f <= from_pose.frame + ant
        near_end = f >= to_pose.frame - ft
        kind = "breakdown" if near_start or near_end else "inbetween"
        t = (f - from_pose.frame) / float(span)
        progress = progress_at(curve, t)
        note_bits = [
            f"suggested {mode.value}",
            f"t={t:.4f}",
            f"progress={progress:.4f}",
            f"action:{from_pose.action or from_pose.intention}",
            f"->:{to_pose.action or to_pose.intention}",
        ]
        if near_start and ant:
            note_bits.append(f"anticipation_window={ant}f")
        if near_end and ft:
            note_bits.append(f"follow_through_window={ft}f")
        slots.append(
            InBetweenSlot(
                frame=f,
                from_key_pose_id=from_pose.id,
                to_key_pose_id=to_pose.id,
                kind=kind,  # type: ignore[arg-type]
                notes="; ".join(note_bits) + " (generated preview)",
                suggested_by_operation="agents.suggest_inbetweens",
                source=TimingSource.GENERATED,
                spacing_t=progress,
            )
        )

    suggestion.slots = slots
    suggestion.rationale = (
        f"Preview {len(slots)} generated slots from {from_pose.id}@f{from_pose.frame} "
        f"to {to_pose.id}@f{to_pose.frame} using explicit spacing_mode={mode.value}. "
        "TimingPlan not modified. Approved keys untouched."
    )
    rev, prov = attribute_suggestion(
        operation="agents.suggest_inbetweens",
        target_type="timing_plan",
        target_id=plan_id,
        snapshot={
            "suggestion": suggestion.model_dump(mode="json"),
            "timing_plan_before": plan_before,
            "note": "Non-destructive preview",
        },
        summary=suggestion.rationale,
        outputs={"slot_count": len(slots), "applied_to_timing": False},
    )
    suggestion.revision_id = rev.id
    save_suggestion(root, suggestion)
    save_revision(root, rev)
    save_provenance(root, prov)

    # Prove timing unchanged
    plan_after = load_timing_plan(root, plan_id).model_dump(mode="json")
    if plan_after != plan_before:
        raise RuntimeError("suggest_inbetweens mutated TimingPlan — must be non-destructive")

    return {
        "ok": True,
        "suggestion": suggestion,
        "missing_information": [],
        "reason": suggestion.rationale,
    }


def preview_suggestion(root: Path, suggestion_id: str) -> dict[str, Any]:
    """Return suggestion slots for inspection without applying them."""
    sug = load_suggestion(root, suggestion_id)
    return {
        "suggestion_id": sug.id,
        "status": sug.status,
        "applied_to_timing": sug.applied_to_timing,
        "missing_information": sug.missing_information,
        "rationale": sug.rationale,
        "slots": [s.model_dump(mode="json") for s in sug.slots],
        "from_key_pose_id": sug.from_key_pose_id,
        "to_key_pose_id": sug.to_key_pose_id,
        "spacing_mode": sug.spacing_mode,
    }


def _apply_selected_slots(
    root: Path,
    sug: InBetweenSuggestion,
    selected_frames: list[int],
    *,
    status: str,
) -> dict[str, Any]:
    if sug.status == "blocked" or sug.missing_information:
        return {
            "ok": False,
            "reason": "Cannot accept a blocked suggestion; resolve missing_information first.",
            "missing_information": sug.missing_information,
        }
    if not sug.timing_plan_id:
        return {"ok": False, "reason": "Suggestion has no timing_plan_id"}

    plan = load_timing_plan(root, sug.timing_plan_id)
    keys = []
    for kid in plan.key_pose_ids:
        path = root / "key_poses" / f"{kid}.json"
        if path.exists():
            keys.append(load_key_pose(root, kid))
    # Always include from/to
    for kid in (sug.from_key_pose_id, sug.to_key_pose_id):
        if kid not in {k.id for k in keys}:
            keys.append(load_key_pose(root, kid))

    key_snapshots = {
        k.id: _read(root / "key_poses" / f"{k.id}.json")
        for k in keys
        if (root / "key_poses" / f"{k.id}.json").exists()
    }
    approved_before = {
        k.id: k.model_dump(mode="json")
        for k in keys
        if k.approval == ApprovalState.APPROVED
    }

    selected = [s for s in sug.slots if s.frame in selected_frames]
    rejected = [s.frame for s in sug.slots if s.frame not in selected_frames]
    if not selected:
        return {"ok": False, "reason": "No frames selected to accept"}

    # Merge: keep slots outside selected frames; replace selected span frames
    keep = [s for s in plan.inbetween_slots if s.frame not in selected_frames]
    merged = keep + selected

    # Refuse if generator proposes overwriting approved keys
    result = apply_generated_inbetweens(
        plan,
        keys,
        merged,
        proposed_key_pose_overwrites=[],
    )
    if not result.ok or result.timing_plan is None:
        return {
            "ok": False,
            "reason": result.reason,
            "blocked_key_pose_ids": result.blocked_key_pose_ids,
        }

    save_timing_plan(root, result.timing_plan)
    sug = sug.model_copy(deep=True)
    sug.status = status  # type: ignore[assignment]
    sug.accepted_frames = sorted(selected_frames)
    sug.rejected_frames = sorted(rejected)
    sug.applied_to_timing = True

    rev, prov = attribute_suggestion(
        operation="human.accept_inbetween_suggestion",
        target_type="timing_plan",
        target_id=plan.id,
        snapshot={
            "suggestion_id": sug.id,
            "accepted_frames": sug.accepted_frames,
            "rejected_frames": sug.rejected_frames,
            "status": status,
            "approved_key_poses_unchanged": approved_before,
        },
        summary=(
            f"{status} suggestion {sug.id}: accepted {len(selected)} slots, "
            f"rejected {len(rejected)}. Approved keys not rewritten."
        ),
    )
    sug.revision_id = rev.id
    save_suggestion(root, sug)
    save_revision(root, rev)
    save_provenance(root, prov)

    for kid, snap in key_snapshots.items():
        current = _read(root / "key_poses" / f"{kid}.json")
        if kid in approved_before and current != snap:
            raise RuntimeError(
                f"Accept mutated approved key pose {kid} — rolling contract broken"
            )
        if current != snap:
            # Even draft keys should not be rewritten by accept
            raise RuntimeError(f"Accept mutated key pose content {kid}")

    return {
        "ok": True,
        "suggestion": sug,
        "timing_plan": result.timing_plan,
        "accepted_frames": sug.accepted_frames,
        "rejected_frames": sug.rejected_frames,
        "reason": rev.summary,
    }


def accept_suggestion(root: Path, suggestion_id: str) -> dict[str, Any]:
    sug = load_suggestion(root, suggestion_id)
    frames = [s.frame for s in sug.slots]
    return _apply_selected_slots(root, sug, frames, status="accepted")


def partial_accept_suggestion(
    root: Path,
    suggestion_id: str,
    *,
    accept_frames: list[int],
) -> dict[str, Any]:
    sug = load_suggestion(root, suggestion_id)
    valid = {s.frame for s in sug.slots}
    unknown = [f for f in accept_frames if f not in valid]
    if unknown:
        return {
            "ok": False,
            "reason": f"Frames not in suggestion: {unknown}",
        }
    return _apply_selected_slots(root, sug, list(accept_frames), status="partial")


def reject_suggestion(root: Path, suggestion_id: str, *, comment: str) -> dict[str, Any]:
    if not comment.strip():
        return {"ok": False, "reason": "Reject requires a comment"}
    sug = load_suggestion(root, suggestion_id).model_copy(deep=True)
    plan_before = None
    if sug.timing_plan_id and (root / "timing" / f"{sug.timing_plan_id}.json").exists():
        plan_before = load_timing_plan(root, sug.timing_plan_id).model_dump(mode="json")

    sug.status = "rejected"
    sug.rejected_frames = [s.frame for s in sug.slots]
    sug.accepted_frames = []
    sug.applied_to_timing = False
    sug.rationale = (sug.rationale + f" | REJECTED: {comment}").strip()

    prov = make_provenance(
        operation="human.reject_inbetween_suggestion",
        revision_id=sug.revision_id or new_id("rev"),
        actor=ActorKind.HUMAN,
        summary=comment,
        outputs={"suggestion_id": sug.id, "applied_to_timing": False},
    )
    save_suggestion(root, sug)
    save_provenance(root, prov)

    if plan_before is not None:
        plan_after = load_timing_plan(root, sug.timing_plan_id).model_dump(mode="json")
        if plan_after != plan_before:
            return {
                "ok": False,
                "reason": "Reject unexpectedly changed TimingPlan",
                "suggestion": sug,
            }

    return {
        "ok": True,
        "suggestion": sug,
        "reason": f"Rejected suggestion {sug.id}: {comment}",
    }
