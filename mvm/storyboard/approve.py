"""Human animatic approve / reject — lifecycle + Review (first-class artifact)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.project.reviews import gate_context_for_shot, save_review
from mvm.schemas.compat import attribute_suggestion, layout_from_shot
from mvm.schemas.domain import ActorKind, Review, make_provenance, new_id
from mvm.schemas.lifecycle import transition_shot
from mvm.schemas.models import ApprovalState, Shot, ShotLifecycleState
from mvm.storyboard.workflow import (
    list_animatics_for_shot,
    load_animatic,
    load_panels_for_shot,
    save_animatic,
)


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_shot(root: Path, shot_id: str) -> Shot:
    return Shot.model_validate_json(
        (root / "shots" / f"{shot_id}.json").read_text(encoding="utf-8")
    )


def _ensure_layout_for_animatic(root: Path, shot: Shot) -> tuple[Shot, list[dict[str, Any]]]:
    """Animatic requires layout gate — create an explicit stub layout if missing."""
    notes: list[dict[str, Any]] = []
    ctx = gate_context_for_shot(root, shot)
    if ctx.has_layout:
        return shot, notes

    panels = load_panels_for_shot(root, shot.id)
    if not panels:
        notes.append(
            {
                "ok": False,
                "reason": "Cannot create layout stub without storyboard panels.",
            }
        )
        return shot, notes

    layout = layout_from_shot(shot)
    layout.description = (
        (layout.description or "")
        + " [auto-created for animatic approve — review/replace before final]"
    ).strip()
    ensure_domain_dirs(root)
    (root / "layouts").mkdir(parents=True, exist_ok=True)
    _write(root / "layouts" / f"{layout.id}.json", layout)
    shot = shot.model_copy(deep=True)
    shot.layout_id = layout.id
    rev, prov = attribute_suggestion(
        operation="human.animatic_ensure_layout",
        target_type="layout",
        target_id=layout.id,
        snapshot=layout.model_dump(mode="json"),
        summary=f"Layout stub created so animatic can be approved for {shot.id}",
        inputs={"shot_id": shot.id, "panel_count": len(panels)},
    )
    save_revision(root, rev)
    save_provenance(root, prov)
    notes.append(
        {
            "ok": True,
            "reason": (
                f"Created layout {layout.id} for animatic gate "
                "(explicit stub, not a silent default)."
            ),
            "layout_id": layout.id,
            "revision_id": rev.id,
            "provenance_id": prov.id,
        }
    )
    return shot, notes


def _advance_to_animatic(root: Path, shot: Shot) -> tuple[Shot, list[dict[str, Any]]]:
    """Walk legal transitions toward ANIMATIC; record blockers."""
    log: list[dict[str, Any]] = []
    current = shot.model_copy(deep=True)
    # Ensure storyboard then layout then animatic
    path = [
        ShotLifecycleState.STORYBOARD,
        ShotLifecycleState.LAYOUT,
        ShotLifecycleState.ANIMATIC,
    ]
    order = [
        ShotLifecycleState.INTENT,
        ShotLifecycleState.STORYBOARD,
        ShotLifecycleState.LAYOUT,
        ShotLifecycleState.ANIMATIC,
    ]
    for target in path:
        if current.lifecycle_state == target:
            continue
        if order.index(current.lifecycle_state) >= order.index(target):
            continue
        ctx = gate_context_for_shot(root, current)
        result = transition_shot(current, target, ctx)
        log.append(
            {
                "from": current.lifecycle_state.value,
                "to": target.value,
                "ok": result.ok,
                "reason": result.reason,
                "blockers": result.blockers,
            }
        )
        if not result.ok or result.shot is None:
            break
        current = result.shot
    return current, log


def approve_animatic(
    root: Path,
    shot_id: str,
    animatic_id: str,
    *,
    comment: str = "Animatic approved — unlock key poses",
    reviewer: str = "human",
) -> dict[str, Any]:
    """Approve a first-class animatic: lifecycle → animatic, flag, Review."""
    ensure_domain_dirs(root)
    (root / "reviews").mkdir(parents=True, exist_ok=True)

    shot = _load_shot(root, shot_id)
    anim = load_animatic(root, animatic_id)
    if anim.shot_id != shot_id:
        return {
            "ok": False,
            "reason": f"Animatic {animatic_id} belongs to {anim.shot_id}, not {shot_id}.",
        }
    if not anim.panels:
        return {
            "ok": False,
            "reason": "Cannot approve an empty animatic (no panels).",
        }

    shot, layout_notes = _ensure_layout_for_animatic(root, shot)
    if layout_notes and not layout_notes[-1].get("ok", True) and not gate_context_for_shot(root, shot).has_layout:
        return {
            "ok": False,
            "reason": layout_notes[-1]["reason"],
            "layout_notes": layout_notes,
        }

    shot, transition_log = _advance_to_animatic(root, shot)
    if shot.lifecycle_state != ShotLifecycleState.ANIMATIC:
        return {
            "ok": False,
            "reason": (
                f"Could not reach animatic lifecycle state "
                f"(stuck at {shot.lifecycle_state.value}). See transition_log."
            ),
            "transition_log": transition_log,
            "layout_notes": layout_notes,
            "blockers": transition_log[-1].get("blockers", []) if transition_log else [],
        }

    shot.animatic_approved = True
    # Do not set shot.approval=APPROVED here — that means final shot approval.
    # Animatic gate is animatic_approved + Animatic.approved + Review record.
    shot.approval = ApprovalState.PENDING_REVIEW
    anim = anim.model_copy(deep=True)
    anim.approved = True

    rev, prov = attribute_suggestion(
        operation="human.approve_animatic",
        target_type="shot",
        target_id=shot_id,
        snapshot={
            "animatic_id": anim.id,
            "animatic_version": anim.version,
            "lifecycle_state": shot.lifecycle_state.value,
            "animatic_approved": True,
            "shot_approval": shot.approval.value,
            "total_frames": anim.total_duration_frames,
        },
        summary=comment,
        inputs={"animatic_id": animatic_id, "reviewer": reviewer},
        outputs={
            "animatic_approved": True,
            "lifecycle_state": "animatic",
            "shot_approval": "pending_review",
        },
        parent_revision_id=anim.revision_id,
    )
    anim.revision_id = rev.id
    shot.revision_id = rev.id
    save_revision(root, rev)
    save_provenance(root, prov)
    save_animatic(root, anim)
    _write(root / "shots" / f"{shot.id}.json", shot)

    review = Review(
        id=new_id("revw"),
        target_type="shot",
        target_id=shot_id,
        revision_id=rev.id,
        state=ApprovalState.APPROVED,
        reviewer=reviewer,
        comment=comment,
    )
    save_review(root, review)

    return {
        "ok": True,
        "shot": shot.model_dump(mode="json"),
        "animatic": anim.model_dump(mode="json"),
        "review": review.model_dump(mode="json"),
        "revision_id": rev.id,
        "provenance_id": prov.id,
        "transition_log": transition_log,
        "layout_notes": layout_notes,
        "note": (
            "Animatic approved as a first-class artifact "
            "(animatic_approved=True; Animatic.approved=True). "
            "Shot.approval remains pending_review until final_review → approved. "
            "Key poses are unlocked. Duration/order stay on the animatic; "
            "artwork panels untouched."
        ),
    }


def reject_animatic(
    root: Path,
    shot_id: str,
    animatic_id: str,
    *,
    comment: str,
    reviewer: str = "human",
    restore_revision_id: str | None = None,
) -> dict[str, Any]:
    """Reject animatic approval — requires comment; revisions stay recoverable."""
    if not (comment or "").strip():
        return {
            "ok": False,
            "reason": "Rejecting an animatic requires a non-empty comment.",
        }

    shot = _load_shot(root, shot_id)
    anim = load_animatic(root, animatic_id)
    if anim.shot_id != shot_id:
        return {
            "ok": False,
            "reason": f"Animatic {animatic_id} belongs to {anim.shot_id}, not {shot_id}.",
        }

    shot = shot.model_copy(deep=True)
    shot.animatic_approved = False
    shot.approval = ApprovalState.REJECTED
    anim = anim.model_copy(deep=True)
    anim.approved = False

    # Rewind toward layout/storyboard via legal transitions when possible
    transition_log: list[dict[str, Any]] = []
    if shot.lifecycle_state == ShotLifecycleState.ANIMATIC:
        ctx = gate_context_for_shot(root, shot)
        result = transition_shot(shot, ShotLifecycleState.LAYOUT, ctx)
        transition_log.append(
            {
                "from": ShotLifecycleState.ANIMATIC.value,
                "to": ShotLifecycleState.LAYOUT.value,
                "ok": result.ok,
                "reason": result.reason,
                "blockers": result.blockers,
            }
        )
        if result.ok and result.shot is not None:
            shot = result.shot
            shot.animatic_approved = False
            shot.approval = ApprovalState.REJECTED

    rev_id = anim.revision_id or new_id("rev")
    review = Review(
        id=new_id("revw"),
        target_type="shot",
        target_id=shot_id,
        revision_id=rev_id,
        state=ApprovalState.REJECTED,
        reviewer=reviewer,
        comment=comment,
        restore_revision_id=restore_revision_id,
    )
    save_review(root, review)
    prov = make_provenance(
        operation="human.reject_animatic",
        revision_id=rev_id,
        actor=ActorKind.HUMAN,
        summary=comment,
        inputs={"animatic_id": animatic_id},
        outputs={"animatic_approved": False},
    )
    save_provenance(root, prov)
    save_animatic(root, anim)
    _write(root / "shots" / f"{shot.id}.json", shot)

    return {
        "ok": True,
        "shot": shot.model_dump(mode="json"),
        "animatic": anim.model_dump(mode="json"),
        "review": review.model_dump(mode="json"),
        "transition_log": transition_log,
        "note": "Animatic rejected; revision store untouched (recoverable).",
    }
