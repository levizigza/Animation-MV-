"""Shot lifecycle — explicit states, legal transitions, blocked reasons.

Detailed animation means ``key_poses`` and later. Final review requires an
approved animatic. Generated in-betweens must never overwrite approved keys.
Rejected revisions stay on disk / in the revision list and remain recoverable.
"""

from __future__ import annotations

from typing import Any, Iterable

from pydantic import BaseModel, Field

from mvm.schemas.domain import (
    InBetweenSlot,
    KeyPose,
    Revision,
    Review,
    TimingPlan,
    restore_snapshot,
)
from mvm.schemas.models import ApprovalState, Shot, ShotIntent, ShotLifecycleState


# Forward craft flow + limited rewind for revision (not silent skips).
LEGAL_TRANSITIONS: dict[ShotLifecycleState, frozenset[ShotLifecycleState]] = {
    ShotLifecycleState.INTENT: frozenset({ShotLifecycleState.STORYBOARD}),
    ShotLifecycleState.STORYBOARD: frozenset(
        {ShotLifecycleState.LAYOUT, ShotLifecycleState.INTENT}
    ),
    ShotLifecycleState.LAYOUT: frozenset(
        {ShotLifecycleState.ANIMATIC, ShotLifecycleState.STORYBOARD}
    ),
    ShotLifecycleState.ANIMATIC: frozenset(
        {ShotLifecycleState.KEY_POSES, ShotLifecycleState.LAYOUT}
    ),
    ShotLifecycleState.KEY_POSES: frozenset(
        {ShotLifecycleState.TIMING_REVIEW, ShotLifecycleState.ANIMATIC}
    ),
    ShotLifecycleState.TIMING_REVIEW: frozenset(
        {
            ShotLifecycleState.INBETWEEN_REVIEW,
            ShotLifecycleState.KEY_POSES,
        }
    ),
    ShotLifecycleState.INBETWEEN_REVIEW: frozenset(
        {
            ShotLifecycleState.SOUND_EDIT_REVIEW,
            ShotLifecycleState.TIMING_REVIEW,
            ShotLifecycleState.KEY_POSES,
        }
    ),
    ShotLifecycleState.SOUND_EDIT_REVIEW: frozenset(
        {
            ShotLifecycleState.FINAL_REVIEW,
            ShotLifecycleState.INBETWEEN_REVIEW,
        }
    ),
    ShotLifecycleState.FINAL_REVIEW: frozenset(
        {
            ShotLifecycleState.APPROVED,
            ShotLifecycleState.SOUND_EDIT_REVIEW,
            ShotLifecycleState.ANIMATIC,  # reject back toward approved animatic gate
        }
    ),
    ShotLifecycleState.APPROVED: frozenset(
        {ShotLifecycleState.FINAL_REVIEW}  # explicit reopen only
    ),
}

# States that count as "detailed animation" (require explicit intent).
DETAILED_ANIMATION_STATES = frozenset(
    {
        ShotLifecycleState.KEY_POSES,
        ShotLifecycleState.TIMING_REVIEW,
        ShotLifecycleState.INBETWEEN_REVIEW,
        ShotLifecycleState.SOUND_EDIT_REVIEW,
        ShotLifecycleState.FINAL_REVIEW,
        ShotLifecycleState.APPROVED,
    }
)

PLACEHOLDER_INTENT_NOTES = frozenset(
    {"default_intent_placeholder", "backfilled_from_legacy_shot_fields"}
)


class LifecycleGateContext(BaseModel):
    """Facts checked at transition time — all visible, nothing silent."""

    has_storyboard_panel: bool = False
    has_layout: bool = False
    animatic_approved: bool = False
    key_poses_approved: bool = False
    timing_plan_id: str | None = None
    approved_key_pose_ids: list[str] = Field(default_factory=list)
    recoverable_revision_ids: list[str] = Field(default_factory=list)


class TransitionResult(BaseModel):
    ok: bool
    from_state: ShotLifecycleState
    to_state: ShotLifecycleState
    reason: str
    shot: Shot | None = None
    blockers: list[str] = Field(default_factory=list)


class InBetweenApplyResult(BaseModel):
    ok: bool
    reason: str
    timing_plan: TimingPlan | None = None
    blocked_key_pose_ids: list[str] = Field(default_factory=list)


class RecoveryResult(BaseModel):
    ok: bool
    reason: str
    revision_id: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)


def intent_is_explicit(intent: ShotIntent | None) -> bool:
    if intent is None:
        return False
    purpose = (intent.purpose or "").strip()
    if not purpose:
        return False
    if purpose.startswith("Legacy shot"):
        return False
    if (intent.notes or "") in PLACEHOLDER_INTENT_NOTES:
        return False
    return True


def legal_targets(state: ShotLifecycleState) -> frozenset[ShotLifecycleState]:
    return LEGAL_TRANSITIONS.get(state, frozenset())


def _gate_blockers(
    shot: Shot,
    to_state: ShotLifecycleState,
    ctx: LifecycleGateContext,
) -> list[str]:
    blockers: list[str] = []

    if to_state in DETAILED_ANIMATION_STATES and not intent_is_explicit(shot.intent):
        blockers.append(
            "Cannot enter detailed animation without an explicit ShotIntent.purpose "
            "(placeholder/legacy backfill intents are not enough)."
        )

    if to_state == ShotLifecycleState.LAYOUT and not ctx.has_storyboard_panel:
        blockers.append(
            "Cannot enter layout without at least one storyboard panel linked to the shot."
        )

    if to_state == ShotLifecycleState.ANIMATIC and not ctx.has_layout:
        blockers.append("Cannot enter animatic without a layout for this shot.")

    if to_state == ShotLifecycleState.KEY_POSES and not ctx.animatic_approved:
        blockers.append(
            "Cannot enter key poses until the animatic is approved "
            "(set animatic_approved=True after human review)."
        )

    if to_state == ShotLifecycleState.TIMING_REVIEW and not (
        shot.key_pose_ids or ctx.key_poses_approved
    ):
        blockers.append(
            "Cannot enter timing review without key poses on the shot "
            "(key_pose_ids must be non-empty)."
        )

    if to_state == ShotLifecycleState.INBETWEEN_REVIEW and not ctx.timing_plan_id:
        blockers.append(
            "Cannot enter in-between review without a TimingPlan "
            "(timing is stored independently from rendered frames)."
        )

    if to_state == ShotLifecycleState.FINAL_REVIEW and not ctx.animatic_approved:
        blockers.append(
            "Cannot enter final review without an approved animatic."
        )

    if to_state == ShotLifecycleState.APPROVED and shot.lifecycle_state != (
        ShotLifecycleState.FINAL_REVIEW
    ):
        # structural — also covered by LEGAL_TRANSITIONS
        blockers.append("Shot can only be approved from final_review.")

    return blockers


def explain_transition(
    shot: Shot,
    to_state: ShotLifecycleState,
    ctx: LifecycleGateContext | None = None,
) -> TransitionResult:
    """Explain whether a transition is legal — always returns a human-readable reason."""
    ctx = ctx or LifecycleGateContext()
    from_state = shot.lifecycle_state
    allowed = legal_targets(from_state)

    if to_state not in allowed:
        legal = ", ".join(sorted(s.value for s in allowed)) or "(none)"
        return TransitionResult(
            ok=False,
            from_state=from_state,
            to_state=to_state,
            reason=(
                f"Illegal transition: {from_state.value} → {to_state.value}. "
                f"Legal next states: {legal}."
            ),
            blockers=[
                f"{from_state.value} may only move to: {legal}",
            ],
        )

    blockers = _gate_blockers(shot, to_state, ctx)
    if blockers:
        return TransitionResult(
            ok=False,
            from_state=from_state,
            to_state=to_state,
            reason="Transition blocked by validation gates: " + " ".join(blockers),
            blockers=blockers,
        )

    return TransitionResult(
        ok=True,
        from_state=from_state,
        to_state=to_state,
        reason=f"OK: {from_state.value} → {to_state.value}",
        blockers=[],
    )


def transition_shot(
    shot: Shot,
    to_state: ShotLifecycleState,
    ctx: LifecycleGateContext | None = None,
) -> TransitionResult:
    """Validate and apply lifecycle transition; returns updated shot copy on success."""
    result = explain_transition(shot, to_state, ctx)
    if not result.ok:
        return result
    updated = shot.model_copy(deep=True)
    updated.lifecycle_state = to_state
    if to_state == ShotLifecycleState.APPROVED:
        updated.approval = ApprovalState.APPROVED
    elif to_state != ShotLifecycleState.APPROVED and updated.approval == ApprovalState.APPROVED:
        updated.approval = ApprovalState.PENDING_REVIEW
    return TransitionResult(
        ok=True,
        from_state=result.from_state,
        to_state=to_state,
        reason=result.reason,
        shot=updated,
        blockers=[],
    )


def apply_generated_inbetweens(
    timing_plan: TimingPlan,
    key_poses: Iterable[KeyPose],
    new_slots: list[InBetweenSlot],
    *,
    proposed_key_pose_overwrites: list[str] | None = None,
) -> InBetweenApplyResult:
    """Merge generated in-between *slots* only.

    Never overwrites approved key poses. ``proposed_key_pose_overwrites`` lists
    key pose ids a generator wants to replace — blocked if those keys are approved.
    """
    approved_ids = {
        k.id
        for k in key_poses
        if getattr(k, "approval", ApprovalState.DRAFT) == ApprovalState.APPROVED
    }
    proposed = list(proposed_key_pose_overwrites or [])
    blocked = [kid for kid in proposed if kid in approved_ids]
    if blocked:
        return InBetweenApplyResult(
            ok=False,
            reason=(
                "Generated in-betweens cannot overwrite approved key poses: "
                + ", ".join(blocked)
                + ". Reject or revise via a new Revision; do not mutate approved keys."
            ),
            blocked_key_pose_ids=blocked,
        )

    # Also refuse slots that claim a frame already owned by an approved key
    key_frames = {
        k.frame: k.id
        for k in key_poses
        if getattr(k, "approval", ApprovalState.DRAFT) == ApprovalState.APPROVED
    }
    frame_blocked: list[str] = []
    for slot in new_slots:
        if slot.frame in key_frames:
            frame_blocked.append(key_frames[slot.frame])
    if frame_blocked:
        uniq = sorted(set(frame_blocked))
        return InBetweenApplyResult(
            ok=False,
            reason=(
                "In-between slots collide with approved key pose frames for: "
                + ", ".join(uniq)
            ),
            blocked_key_pose_ids=uniq,
        )

    updated = timing_plan.model_copy(deep=True)
    # Replace only inbetween/breakdown slots; keep exposures / key ids intact
    updated.inbetween_slots = list(new_slots)
    return InBetweenApplyResult(
        ok=True,
        reason=(
            f"Applied {len(new_slots)} in-between slots on TimingPlan {timing_plan.id}. "
            "Key poses unchanged."
        ),
        timing_plan=updated,
    )


def recover_rejected_revision(
    review: Review,
    revisions: dict[str, Revision] | list[Revision],
) -> RecoveryResult:
    """Restore snapshot from a rejected review's restore target, or the rejected rev itself.

    Rejected revisions must remain in ``revisions`` — this never deletes them.
    """
    by_id: dict[str, Revision]
    if isinstance(revisions, dict):
        by_id = revisions
    else:
        by_id = {r.id: r for r in revisions}

    if review.state != ApprovalState.REJECTED:
        return RecoveryResult(
            ok=False,
            reason=f"Review {review.id} is not rejected (state={review.state.value}).",
        )

    target_id = review.restore_revision_id or review.revision_id
    if target_id not in by_id:
        return RecoveryResult(
            ok=False,
            reason=(
                f"Cannot recover: revision {target_id} is missing from the revision store. "
                "Rejected revisions must remain recoverable — do not delete them."
            ),
            revision_id=target_id,
        )

    rev = by_id[target_id]
    # Ensure the rejected revision itself is still present when restore points elsewhere
    if review.revision_id not in by_id:
        return RecoveryResult(
            ok=False,
            reason=(
                f"Rejected revision {review.revision_id} is missing; "
                "recovery requires rejected revisions to remain in the store."
            ),
            revision_id=review.revision_id,
        )

    snap = restore_snapshot(rev)
    return RecoveryResult(
        ok=True,
        reason=(
            f"Recovered snapshot from revision {rev.id} "
            f"(rejected review {review.id} remains on record)."
        ),
        revision_id=rev.id,
        snapshot=snap,
    )
