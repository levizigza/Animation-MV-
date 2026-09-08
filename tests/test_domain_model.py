"""Domain model: serialization, validation, backward-compatible upgrades."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mvm.schemas.compat import (
    attribute_suggestion,
    intent_from_legacy_shot,
    project_from_meta,
    sequences_from_shots,
    shot_to_craft,
    timing_plan_from_xsheet,
    upgrade_shot_dict,
)
from mvm.schemas.domain import (
    ActorKind,
    AudioCue,
    ExposureHold,
    InBetweenSlot,
    KeyPose,
    Layout,
    Project,
    ProvenanceRecord,
    Reference,
    Review,
    Revision,
    Sequence,
    ShotCraft,
    ShotIntent,
    StoryboardPanel,
    TimingPlan,
    make_provenance,
    make_revision,
    new_id,
    restore_snapshot,
)
from mvm.schemas.models import (
    ApprovalState,
    CelPolicy,
    ProjectMeta,
    Shot,
    XSheet,
    XSheetCell,
)


def test_shot_intent_required_and_serializes():
    intent = ShotIntent(purpose="Establish rain-slick street before chorus hit")
    shot = Shot(
        id="shot_001_intro",
        index=1,
        section="intro",
        start=0.0,
        end=4.0,
        duration=4.0,
        intent=intent,
        description="Wide establish",
    )
    payload = json.loads(shot.model_dump_json())
    again = Shot.model_validate(payload)
    assert again.intent.purpose.startswith("Establish")
    assert again.intent.animation_priority == "performance"


def test_shot_intent_rejects_blank_purpose():
    with pytest.raises(ValidationError):
        ShotIntent(purpose="   ")


def test_legacy_shot_json_backfills_intent():
    legacy = {
        "id": "shot_001_verse",
        "index": 1,
        "section": "verse",
        "start": 0.0,
        "end": 8.0,
        "duration": 8.0,
        "description": "Lead walks the motif",
        "blocking": "center stage",
    }
    shot = Shot.model_validate(legacy)
    assert shot.intent.purpose == "Lead walks the motif"
    assert "backfilled" in shot.intent.notes


def test_upgrade_shot_dict_roundtrip():
    legacy = {
        "id": "shot_002",
        "index": 2,
        "section": "chorus",
        "start": 8.0,
        "end": 16.0,
        "duration": 8.0,
    }
    upgraded = upgrade_shot_dict(legacy)
    shot = Shot.model_validate(upgraded)
    assert "chorus" in shot.intent.purpose.lower() or "Section beat" in shot.intent.purpose


def test_key_pose_not_inbetween_and_timing_independent():
    pose = KeyPose(id="pose_a", shot_id="shot_1", frame=1, label="anticipation", is_extreme=True)
    assert pose.role == "key"
    slot = InBetweenSlot(
        frame=3,
        from_key_pose_id="pose_a",
        to_key_pose_id="pose_b",
        kind="inbetween",
        suggested_by_operation="agents.animation_director",
    )
    plan = TimingPlan(
        id="timing_1",
        shot_id="shot_1",
        end_frame=24,
        key_pose_ids=["pose_a", "pose_b"],
        exposures=[
            ExposureHold(frame=1, kind="exposure", duration_frames=2, key_pose_id="pose_a")
        ],
        inbetween_slots=[slot],
        cel=CelPolicy(mode="limited", exposure="2s"),
    )
    # Timing plan has no render paths
    dumped = plan.model_dump(mode="json")
    assert "frames/" not in json.dumps(dumped)
    assert dumped["inbetween_slots"][0]["kind"] == "inbetween"
    assert "pose_a" in dumped["key_pose_ids"]


def test_timing_plan_rejects_inverted_range():
    with pytest.raises(ValidationError):
        TimingPlan(id="t", shot_id="s", start_frame=10, end_frame=5)


def test_provenance_requires_operation_and_revision():
    rev = make_revision(
        target_type="shot",
        target_id="shot_1",
        snapshot={"id": "shot_1"},
        summary="Director draft",
        created_by=ActorKind.HEURISTIC_AGENT,
    )
    prov = make_provenance(
        operation="agents.director",
        revision_id=rev.id,
        summary="Suggested camera push",
        outputs={"camera.type": "push_in"},
    )
    assert prov.operation == "agents.director"
    assert prov.revision_id == rev.id
    rev.provenance_ids.append(prov.id)
    blob = json.loads(Revision.model_validate(rev.model_dump()).model_dump_json())
    assert blob["provenance_ids"] == [prov.id]


def test_review_reject_requires_comment_and_can_restore():
    with pytest.raises(ValidationError):
        Review(
            id="revw_1",
            target_type="shot",
            target_id="shot_1",
            revision_id="rev_bad",
            state=ApprovalState.REJECTED,
            comment="",
        )
    good = Review(
        id="revw_2",
        target_type="shot",
        target_id="shot_1",
        revision_id="rev_bad",
        state=ApprovalState.REJECTED,
        comment="Smear density too high for verse",
        restore_revision_id="rev_good",
    )
    assert good.restore_revision_id == "rev_good"


def test_revision_restore_snapshot():
    snap = {"intent": {"purpose": "Quiet hold"}, "cel": {"mode": "held_atmosphere"}}
    rev = make_revision(
        target_type="shot",
        target_id="shot_1",
        snapshot=snap,
        summary="Approved quiet hold",
        created_by=ActorKind.HUMAN,
    )
    restored = restore_snapshot(rev)
    assert restored == snap
    restored["intent"]["purpose"] = "mutated"
    assert rev.snapshot["intent"]["purpose"] == "Quiet hold"


def test_attribute_suggestion_links_provenance_to_revision():
    rev, prov = attribute_suggestion(
        operation="cel.xsheet_rebuild",
        target_type="timing_plan",
        target_id="timing_1",
        snapshot={"end_frame": 48},
        summary="Rebuilt timing after cel_mode change",
        inputs={"cel_mode": "full"},
        outputs={"key_count": 6},
    )
    assert prov.revision_id == rev.id
    assert prov.id in rev.provenance_ids
    assert rev.created_by == ActorKind.HEURISTIC_AGENT


def test_project_sequence_shotcraft_roundtrip():
    meta = ProjectMeta(
        slug="demo",
        title="Demo",
        prompt="chrome rain",
        audio_path="audio/master.wav",
        style_pack="akira_chrome",
    )
    shot = Shot(
        id="shot_001_intro",
        index=1,
        section="intro",
        start=0.0,
        end=4.0,
        duration=4.0,
        intent=ShotIntent(purpose="Breath before impact"),
    )
    seqs = sequences_from_shots([shot])
    assert len(seqs) == 1
    project = project_from_meta(meta, sequences=seqs)
    assert project.schema_version == 2
    craft = shot_to_craft(shot, sequence_id=seqs[0].id)
    assert isinstance(craft, ShotCraft)
    assert craft.intent.purpose == "Breath before impact"
    # full aggregate serialization
    payload = {
        "project": project.model_dump(mode="json"),
        "sequences": [s.model_dump(mode="json") for s in seqs],
        "shots": [craft.model_dump(mode="json")],
        "layout": Layout(
            id="layout_1", shot_id=shot.id, camera={"type": "slow_push"}
        ).model_dump(mode="json"),
        "panel": StoryboardPanel(
            id="panel_1", shot_id=shot.id, index=1, intent_summary=craft.intent.purpose
        ).model_dump(mode="json"),
        "reference": Reference(
            id="ref_1", kind="style", path_or_uri="styles/akira_chrome.json"
        ).model_dump(mode="json"),
        "audio_cue": AudioCue(
            id="cue_1", time_sec=0.5, kind="downbeat", shot_id=shot.id
        ).model_dump(mode="json"),
    }
    Project.model_validate(payload["project"])
    Sequence.model_validate(payload["sequences"][0])
    ShotCraft.model_validate(payload["shots"][0])


def test_timing_plan_from_xsheet_separates_keys_and_slots():
    shot = Shot(
        id="shot_x",
        index=1,
        section="chorus",
        start=0.0,
        end=1.0,
        duration=1.0,
        intent=ShotIntent(purpose="Chorus impact keys"),
        cel=CelPolicy(mode="full", exposure="1s"),
    )
    xs = XSheet(
        shot_id=shot.id,
        fps=24,
        end_frame=6,
        cells=[
            XSheetCell(frame=1, layer="character", exposure="key", pose_id="pose_01"),
            XSheetCell(frame=2, layer="character", exposure="hold"),
            XSheetCell(frame=3, layer="character", exposure="inbetween"),
            XSheetCell(frame=4, layer="character", exposure="breakdown"),
            XSheetCell(frame=5, layer="character", exposure="smear"),
            XSheetCell(frame=6, layer="character", exposure="key", pose_id="pose_02"),
        ],
    )
    plan, keys = timing_plan_from_xsheet(xs, shot)
    assert [k.id for k in keys] == ["pose_01", "pose_02"]
    assert all(k.role == "key" for k in keys)
    assert len(plan.inbetween_slots) == 2
    assert 5 in plan.smear_frames
    assert plan.legacy_xsheet_shot_id == shot.id
