"""Human plan approve / reject — lifecycle transitions + Review records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import (
    ensure_domain_dirs,
    load_revisions,
    save_provenance,
    save_revision,
)
from mvm.schemas.domain import (
    ActorKind,
    Review,
    make_provenance,
    make_revision,
    new_id,
)
from mvm.schemas.lifecycle import (
    LEGAL_TRANSITIONS,
    LifecycleGateContext,
    recover_rejected_revision,
    transition_shot,
)
from mvm.schemas.models import ApprovalState, Shot, ShotLifecycleState


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_review(root: Path, review: Review) -> Path:
    ensure_domain_dirs(root)
    reviews = root / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    path = reviews / f"{review.id}.json"
    _write(path, review)
    return path


def load_reviews(root: Path) -> list[Review]:
    d = root / "reviews"
    if not d.exists():
        return []
    return [
        Review.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(d.glob("*.json"))
    ]


def gate_context_for_shot(root: Path, shot: Shot) -> LifecycleGateContext:
    panels_dir = root / "panels"
    layouts_dir = root / "layouts"
    has_panel = bool(shot.storyboard_panel_ids)
    if not has_panel and panels_dir.exists():
        has_panel = any(
            json.loads(p.read_text(encoding="utf-8")).get("shot_id") == shot.id
            for p in panels_dir.glob("*.json")
        )
    has_layout = bool(shot.layout_id)
    if not has_layout and layouts_dir.exists():
        has_layout = any(
            json.loads(p.read_text(encoding="utf-8")).get("shot_id") == shot.id
            for p in layouts_dir.glob("*.json")
        )
    return LifecycleGateContext(
        has_storyboard_panel=has_panel,
        has_layout=has_layout,
        animatic_approved=shot.animatic_approved,
        key_poses_approved=False,
        timing_plan_id=shot.timing_plan_id,
        approved_key_pose_ids=[],
        recoverable_revision_ids=[r.id for r in load_revisions(root)],
    )


def _active_revision_id(root: Path) -> str | None:
    dp = root / "domain_project.json"
    if not dp.exists():
        return None
    return json.loads(dp.read_text(encoding="utf-8")).get("active_revision_id")


def advance_shot_for_plan_approve(
    root: Path, shot: Shot
) -> tuple[Shot, list[dict[str, Any]]]:
    """Advance intent→storyboard→layout one legal step at a time when gates pass."""
    log: list[dict[str, Any]] = []
    current = shot.model_copy(deep=True)
    forward = [
        ShotLifecycleState.STORYBOARD,
        ShotLifecycleState.LAYOUT,
    ]
    for target in forward:
        if current.lifecycle_state == target:
            continue
        # Stop once we reach or pass layout
        if current.lifecycle_state == ShotLifecycleState.LAYOUT:
            break
        order = [
            ShotLifecycleState.INTENT,
            ShotLifecycleState.STORYBOARD,
            ShotLifecycleState.LAYOUT,
        ]
        if order.index(current.lifecycle_state) >= order.index(target):
            continue
        # Only move one step: must be immediate neighbor
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
    current.approval = ApprovalState.APPROVED
    return current, log


def approve_plan(
    root: Path,
    shots: list[Shot],
    *,
    reviewer: str = "human",
    comment: str = "Plan approved for craft preview",
) -> dict[str, Any]:
    """Human approve: lifecycle advance + Review records. Blockers stay visible."""
    ensure_domain_dirs(root)
    (root / "reviews").mkdir(parents=True, exist_ok=True)

    rev_id = _active_revision_id(root)
    if not rev_id:
        human_rev = make_revision(
            target_type="project",
            target_id=root.name,
            snapshot={"event": "approve_plan", "shot_ids": [s.id for s in shots]},
            summary=comment,
            created_by=ActorKind.HUMAN,
        )
        save_revision(root, human_rev)
        prov = make_provenance(
            operation="human.approve_plan",
            revision_id=human_rev.id,
            actor=ActorKind.HUMAN,
            summary=comment,
        )
        save_provenance(root, prov)
        rev_id = human_rev.id
        dp = root / "domain_project.json"
        if dp.exists():
            data = json.loads(dp.read_text(encoding="utf-8"))
            data["active_revision_id"] = rev_id
            _write(dp, data)

    # Human provenance on existing plan revision
    prov = make_provenance(
        operation="human.approve_plan",
        revision_id=rev_id,
        actor=ActorKind.HUMAN,
        summary=comment,
        inputs={"shot_ids": [s.id for s in shots]},
    )
    save_provenance(root, prov)

    updated_shots: list[Shot] = []
    transition_logs: list[dict[str, Any]] = []
    reviews: list[Review] = []

    for shot in shots:
        advanced, log = advance_shot_for_plan_approve(root, shot)
        updated_shots.append(advanced)
        transition_logs.append({"shot_id": shot.id, "steps": log})
        review = Review(
            id=new_id("revw"),
            target_type="shot",
            target_id=shot.id,
            revision_id=rev_id,
            state=ApprovalState.APPROVED,
            reviewer=reviewer,
            comment=comment,
        )
        save_review(root, review)
        reviews.append(review)
        _write(root / "shots" / f"{advanced.id}.json", advanced)

    return {
        "ok": True,
        "revision_id": rev_id,
        "shots": updated_shots,
        "reviews": [r.model_dump(mode="json") for r in reviews],
        "transition_logs": transition_logs,
        "provenance_id": prov.id,
        "note": (
            "Human plan approval recorded. Shots advanced toward layout when gates passed; "
            "blocked steps are listed in transition_logs (nothing silent)."
        ),
    }


def reject_plan(
    root: Path,
    shots: list[Shot],
    *,
    comment: str,
    reviewer: str = "human",
    restore_revision_id: str | None = None,
) -> dict[str, Any]:
    """Human reject: Review REJECTED; revisions remain recoverable."""
    if not (comment or "").strip():
        return {
            "ok": False,
            "reason": "Rejected plan requires a non-empty comment explaining why.",
        }

    ensure_domain_dirs(root)
    (root / "reviews").mkdir(parents=True, exist_ok=True)
    rev_id = _active_revision_id(root)
    if not rev_id:
        return {
            "ok": False,
            "reason": "No active revision to reject. Run plan first.",
        }

    revisions = {r.id: r for r in load_revisions(root)}
    reviews: list[Review] = []
    rewind_logs: list[dict[str, Any]] = []

    for shot in shots:
        current = shot.model_copy(deep=True)
        current.approval = ApprovalState.REJECTED
        # Explicit rewind via legal transitions where possible
        rewind_log: list[dict[str, Any]] = []
        safety = 8
        while (
            safety > 0
            and current.lifecycle_state
            not in (ShotLifecycleState.INTENT, ShotLifecycleState.STORYBOARD)
        ):
            safety -= 1
            ctx = gate_context_for_shot(root, current)
            # Prefer stepping toward storyboard/layout parents
            candidates = [
                ShotLifecycleState.SOUND_EDIT_REVIEW,
                ShotLifecycleState.INBETWEEN_REVIEW,
                ShotLifecycleState.TIMING_REVIEW,
                ShotLifecycleState.KEY_POSES,
                ShotLifecycleState.ANIMATIC,
                ShotLifecycleState.LAYOUT,
                ShotLifecycleState.STORYBOARD,
                ShotLifecycleState.INTENT,
            ]
            moved = False
            for target in candidates:
                result = transition_shot(current, target, ctx)
                if result.ok and result.shot is not None:
                    rewind_log.append(
                        {
                            "from": current.lifecycle_state.value,
                            "to": target.value,
                            "ok": True,
                            "reason": result.reason,
                        }
                    )
                    current = result.shot
                    moved = True
                    break
            if not moved:
                rewind_log.append(
                    {
                        "from": current.lifecycle_state.value,
                        "ok": False,
                        "reason": (
                            f"No legal rewind from {current.lifecycle_state.value}; "
                            "leaving state unchanged except approval=rejected."
                        ),
                    }
                )
                break
        _write(root / "shots" / f"{current.id}.json", current)
        rewind_logs.append({"shot_id": shot.id, "steps": rewind_log})

        review = Review(
            id=new_id("revw"),
            target_type="shot",
            target_id=shot.id,
            revision_id=rev_id,
            state=ApprovalState.REJECTED,
            reviewer=reviewer,
            comment=comment,
            restore_revision_id=restore_revision_id,
        )
        save_review(root, review)
        reviews.append(review)

    recovery = None
    if restore_revision_id and reviews:
        recovery = recover_rejected_revision(reviews[0], revisions)
        if recovery.ok:
            _write(
                root / "reviews" / f"recovery_{reviews[0].id}.json",
                {
                    "recovered_from": recovery.revision_id,
                    "reason": recovery.reason,
                    "snapshot_keys": list(recovery.snapshot.keys()),
                    "note": "Rejected revision was not deleted.",
                },
            )

    return {
        "ok": True,
        "revision_id": rev_id,
        "reviews": [r.model_dump(mode="json") for r in reviews],
        "rewind_logs": rewind_logs,
        "recovery": recovery.model_dump(mode="json") if recovery else None,
        "note": (
            "Plan rejected. Rejected revision remains in revisions/. "
            "Recovery attempted if restore_revision_id was provided."
        ),
    }


def approve_shot_final(
    root: Path,
    shot_id: str,
    *,
    comment: str,
    reviewer: str = "human",
) -> dict[str, Any]:
    """Human final approval: sound_edit_review → final_review → approved.

    Requires animatic_approved. Does not invent craft content — only stamps authorship.
    """
    if not (comment or "").strip():
        return {
            "ok": False,
            "reason": "Final shot approval requires a non-empty comment "
            "(preserve authorship — say why it communicates intent).",
        }
    if not (reviewer or "").strip():
        return {"ok": False, "reason": "reviewer identity is required"}

    ensure_domain_dirs(root)
    (root / "reviews").mkdir(parents=True, exist_ok=True)
    path = root / "shots" / f"{shot_id}.json"
    if not path.exists():
        return {"ok": False, "reason": f"Shot not found: {shot_id}"}

    shot = Shot.model_validate_json(path.read_text(encoding="utf-8"))
    if not shot.animatic_approved:
        return {
            "ok": False,
            "reason": "Cannot final-approve without animatic_approved=True "
            "(human animatic gate first).",
            "blockers": ["animatic_approved"],
        }

    forward = [
        ShotLifecycleState.KEY_POSES,
        ShotLifecycleState.TIMING_REVIEW,
        ShotLifecycleState.INBETWEEN_REVIEW,
        ShotLifecycleState.SOUND_EDIT_REVIEW,
        ShotLifecycleState.FINAL_REVIEW,
        ShotLifecycleState.APPROVED,
    ]
    order = [
        ShotLifecycleState.INTENT,
        ShotLifecycleState.STORYBOARD,
        ShotLifecycleState.LAYOUT,
        ShotLifecycleState.ANIMATIC,
        *forward,
    ]
    log: list[dict[str, Any]] = []
    current = shot.model_copy(deep=True)

    # If still at or before animatic, refuse — keys+timing path must be intentional
    if current.lifecycle_state in {
        ShotLifecycleState.INTENT,
        ShotLifecycleState.STORYBOARD,
        ShotLifecycleState.LAYOUT,
        ShotLifecycleState.ANIMATIC,
    }:
        return {
            "ok": False,
            "reason": (
                f"Shot is still at {current.lifecycle_state.value}. "
                "Advance through key poses / timing / in-betweens / sound before final approve."
            ),
            "lifecycle_state": current.lifecycle_state.value,
        }

    for target in forward:
        if order.index(current.lifecycle_state) >= order.index(target):
            continue
        # Only one legal step at a time
        ctx = gate_context_for_shot(root, current)
        ctx.animatic_approved = True
        if current.key_pose_ids:
            ctx.key_poses_approved = True
            ctx.approved_key_pose_ids = list(current.key_pose_ids)
        if current.timing_plan_id:
            ctx.timing_plan_id = current.timing_plan_id
        # Prefer immediate neighbor only
        legal = LEGAL_TRANSITIONS.get(current.lifecycle_state, frozenset())
        if target not in legal:
            # find next legal toward approved
            nxt = None
            for cand in forward:
                if cand in legal and order.index(cand) > order.index(
                    current.lifecycle_state
                ):
                    nxt = cand
                    break
            if nxt is None:
                break
            target = nxt
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
            return {
                "ok": False,
                "reason": result.reason,
                "transition_log": log,
                "blockers": result.blockers,
            }
        current = result.shot
        if current.lifecycle_state == ShotLifecycleState.APPROVED:
            break

    if current.lifecycle_state != ShotLifecycleState.APPROVED:
        return {
            "ok": False,
            "reason": (
                f"Could not reach approved (stuck at {current.lifecycle_state.value}). "
                "See transition_log."
            ),
            "transition_log": log,
        }

    rev = make_revision(
        target_type="shot",
        target_id=shot_id,
        snapshot={
            "lifecycle_state": current.lifecycle_state.value,
            "intent": current.intent.model_dump(mode="json"),
            "animatic_approved": current.animatic_approved,
        },
        summary=comment.strip(),
        created_by=ActorKind.HUMAN,
    )
    save_revision(root, rev)
    prov = make_provenance(
        operation="human.approve_shot_final",
        revision_id=rev.id,
        actor=ActorKind.HUMAN,
        creator=reviewer.strip(),
        summary=comment.strip(),
        inputs={"shot_id": shot_id, "reviewer": reviewer},
        outputs={
            "lifecycle_state": "approved",
            "shot_approval": "approved",
            "intent_purpose": current.intent.purpose,
        },
    )
    save_provenance(root, prov)
    current.revision_id = rev.id
    current.approval = ApprovalState.APPROVED
    _write(path, current)

    review = Review(
        id=new_id("revw"),
        target_type="shot",
        target_id=shot_id,
        revision_id=rev.id,
        state=ApprovalState.APPROVED,
        reviewer=reviewer.strip(),
        comment=comment.strip(),
    )
    save_review(root, review)

    return {
        "ok": True,
        "shot": current.model_dump(mode="json"),
        "review": review.model_dump(mode="json"),
        "revision_id": rev.id,
        "provenance_id": prov.id,
        "transition_log": log,
        "note": (
            "Final shot approved. Authorship preserved via Review + Provenance. "
            "Intent purpose recorded; no craft content was auto-generated."
        ),
    }
