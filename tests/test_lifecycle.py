"""Unit tests: shot lifecycle transitions, gates, in-between safety, recovery."""

from __future__ import annotations

import pytest

from mvm.schemas.domain import (
    InBetweenSlot,
    KeyPose,
    Revision,
    Review,
    TimingPlan,
    make_revision,
    new_id,
)
from mvm.schemas.lifecycle import (
    DETAILED_ANIMATION_STATES,
    LEGAL_TRANSITIONS,
    LifecycleGateContext,
    apply_generated_inbetweens,
    explain_transition,
    intent_is_explicit,
    recover_rejected_revision,
    transition_shot,
)
from mvm.schemas.models import (
    ApprovalState,
    Shot,
    ShotIntent,
    ShotLifecycleState,
)


def _shot(**kwargs) -> Shot:
    base = dict(
        id="shot_001",
        index=1,
        section="verse",
        start=0.0,
        end=4.0,
        duration=4.0,
        intent=ShotIntent(purpose="Clear silhouette walk into rain"),
        lifecycle_state=ShotLifecycleState.INTENT,
    )
    base.update(kwargs)
    return Shot(**base)


def test_legal_graph_covers_all_states():
    assert set(LEGAL_TRANSITIONS) == set(ShotLifecycleState)
    assert ShotLifecycleState.KEY_POSES in DETAILED_ANIMATION_STATES
    assert ShotLifecycleState.FINAL_REVIEW in DETAILED_ANIMATION_STATES


def test_valid_path_intent_to_storyboard():
    shot = _shot()
    result = transition_shot(shot, ShotLifecycleState.STORYBOARD)
    assert result.ok
    assert result.shot is not None
    assert result.shot.lifecycle_state == ShotLifecycleState.STORYBOARD
    assert "OK:" in result.reason


def test_illegal_skip_intent_to_key_poses_explained():
    shot = _shot()
    result = explain_transition(shot, ShotLifecycleState.KEY_POSES)
    assert not result.ok
    assert "Illegal transition" in result.reason
    assert "storyboard" in result.reason
    assert result.blockers


def test_cannot_enter_detailed_animation_without_explicit_intent():
    shot = _shot(
        intent=ShotIntent(
            purpose="Legacy shot — set an explicit intent before craft approval",
            notes="default_intent_placeholder",
        ),
        lifecycle_state=ShotLifecycleState.ANIMATIC,
    )
    assert not intent_is_explicit(shot.intent)
    ctx = LifecycleGateContext(animatic_approved=True, has_layout=True, has_storyboard_panel=True)
    result = transition_shot(shot, ShotLifecycleState.KEY_POSES, ctx)
    assert not result.ok
    assert any("explicit ShotIntent" in b for b in result.blockers)


def test_key_poses_require_approved_animatic():
    shot = _shot(lifecycle_state=ShotLifecycleState.ANIMATIC)
    ctx = LifecycleGateContext(animatic_approved=False, has_layout=True)
    result = transition_shot(shot, ShotLifecycleState.KEY_POSES, ctx)
    assert not result.ok
    assert any("animatic is approved" in b for b in result.blockers)

    ctx.animatic_approved = True
    result2 = transition_shot(shot, ShotLifecycleState.KEY_POSES, ctx)
    assert result2.ok


def test_final_review_requires_approved_animatic():
    shot = _shot(
        lifecycle_state=ShotLifecycleState.SOUND_EDIT_REVIEW,
        key_pose_ids=["pose_a"],
        timing_plan_id="timing_1",
    )
    ctx = LifecycleGateContext(
        animatic_approved=False,
        timing_plan_id="timing_1",
        key_poses_approved=True,
    )
    result = transition_shot(shot, ShotLifecycleState.FINAL_REVIEW, ctx)
    assert not result.ok
    assert any("approved animatic" in b for b in result.blockers)

    ctx.animatic_approved = True
    assert transition_shot(shot, ShotLifecycleState.FINAL_REVIEW, ctx).ok


def test_generated_inbetweens_cannot_overwrite_approved_keys():
    keys = [
        KeyPose(
            id="pose_a",
            shot_id="shot_001",
            frame=1,
            approval=ApprovalState.APPROVED,
        ),
        KeyPose(
            id="pose_b",
            shot_id="shot_001",
            frame=12,
            approval=ApprovalState.DRAFT,
        ),
    ]
    plan = TimingPlan(id="timing_1", shot_id="shot_001", end_frame=24, key_pose_ids=["pose_a", "pose_b"])
    slots = [
        InBetweenSlot(
            frame=6,
            from_key_pose_id="pose_a",
            to_key_pose_id="pose_b",
            kind="inbetween",
            suggested_by_operation="test.generator",
        )
    ]
    blocked = apply_generated_inbetweens(
        plan, keys, slots, proposed_key_pose_overwrites=["pose_a"]
    )
    assert not blocked.ok
    assert "pose_a" in blocked.blocked_key_pose_ids
    assert "cannot overwrite approved key poses" in blocked.reason.lower()

    # Frame collision with approved key
    collide = apply_generated_inbetweens(
        plan,
        keys,
        [
            InBetweenSlot(
                frame=1,
                from_key_pose_id="pose_a",
                to_key_pose_id="pose_b",
                kind="inbetween",
            )
        ],
    )
    assert not collide.ok

    ok = apply_generated_inbetweens(plan, keys, slots)
    assert ok.ok
    assert ok.timing_plan is not None
    assert len(ok.timing_plan.inbetween_slots) == 1
    assert ok.timing_plan.key_pose_ids == ["pose_a", "pose_b"]


def test_rejected_revision_remains_recoverable():
    good = make_revision(
        target_type="shot",
        target_id="shot_001",
        snapshot={"lifecycle_state": "animatic", "note": "good"},
        summary="Approved animatic",
    )
    bad = make_revision(
        target_type="shot",
        target_id="shot_001",
        snapshot={"lifecycle_state": "key_poses", "note": "bad"},
        summary="Bad keys",
        parent_id=good.id,
    )
    store = {good.id: good, bad.id: bad}
    review = Review(
        id=new_id("revw"),
        target_type="shot",
        target_id="shot_001",
        revision_id=bad.id,
        state=ApprovalState.REJECTED,
        comment="Keys break silhouette",
        restore_revision_id=good.id,
    )
    recovered = recover_rejected_revision(review, store)
    assert recovered.ok
    assert recovered.snapshot["note"] == "good"
    # rejected revision still present
    assert bad.id in store

    missing = recover_rejected_revision(
        review,
        {good.id: good},  # bad (rejected) revision deleted — must fail
    )
    assert not missing.ok
    assert "missing" in missing.reason.lower()


def test_valid_happy_path_to_approved():
    shot = _shot()
    ctx = LifecycleGateContext(
        has_storyboard_panel=True,
        has_layout=True,
        animatic_approved=True,
        key_poses_approved=True,
        timing_plan_id="timing_1",
    )
    path = [
        ShotLifecycleState.STORYBOARD,
        ShotLifecycleState.LAYOUT,
        ShotLifecycleState.ANIMATIC,
        ShotLifecycleState.KEY_POSES,
        ShotLifecycleState.TIMING_REVIEW,
        ShotLifecycleState.INBETWEEN_REVIEW,
        ShotLifecycleState.SOUND_EDIT_REVIEW,
        ShotLifecycleState.FINAL_REVIEW,
        ShotLifecycleState.APPROVED,
    ]
    current = shot
    # Enrich as we go for gate requirements
    for state in path:
        if state == ShotLifecycleState.KEY_POSES:
            current = current.model_copy(
                update={"key_pose_ids": ["pose_a"], "timing_plan_id": "timing_1"}
            )
        if state in (
            ShotLifecycleState.TIMING_REVIEW,
            ShotLifecycleState.INBETWEEN_REVIEW,
            ShotLifecycleState.SOUND_EDIT_REVIEW,
            ShotLifecycleState.FINAL_REVIEW,
            ShotLifecycleState.APPROVED,
        ):
            current = current.model_copy(
                update={"key_pose_ids": ["pose_a"], "timing_plan_id": "timing_1"}
            )
        result = transition_shot(current, state, ctx)
        assert result.ok, result.reason
        assert result.shot is not None
        current = result.shot
    assert current.lifecycle_state == ShotLifecycleState.APPROVED
    assert current.approval == ApprovalState.APPROVED


def test_layout_requires_storyboard_panel():
    shot = _shot(lifecycle_state=ShotLifecycleState.STORYBOARD)
    result = transition_shot(shot, ShotLifecycleState.LAYOUT, LifecycleGateContext())
    assert not result.ok
    assert any("storyboard panel" in b for b in result.blockers)
