"""Key-pose-first workflow: mark, suggest (or missing info), preview, accept/reject."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from mvm.keyposes import (
    accept_suggestion,
    approve_key_pose,
    mark_key_pose,
    partial_accept_suggestion,
    preview_suggestion,
    reject_suggestion,
    set_anticipation_follow_through,
    set_pose_action,
    suggest_inbetweens,
)
from mvm.schemas.models import ApprovalState, Shot, ShotIntent
from mvm.timing import create_timing_plan, load_timing_plan


def _setup(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in (
        "shots",
        "timing",
        "key_poses",
        "suggestions",
        "revisions",
        "provenance",
    ):
        (root / sub).mkdir(parents=True)
    shot = Shot(
        id="shot_k",
        index=1,
        section="verse",
        start=0.0,
        end=2.0,
        duration=2.0,
        intent=ShotIntent(purpose="Punch into chorus silhouette"),
    )
    (root / "shots" / "shot_k.json").write_text(
        json.dumps(shot.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    plan = create_timing_plan(root, shot_id="shot_k", end_frame=24)
    shot.timing_plan_id = plan.id
    (root / "shots" / "shot_k.json").write_text(
        json.dumps(shot.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return root


def _ready_pair(root: Path):
    a = mark_key_pose(root, shot_id="shot_k", frame=1, label="anticipation settle")
    b = mark_key_pose(root, shot_id="shot_k", frame=12, label="impact")
    set_pose_action(root, a.id, action="coil back", intention="load the punch")
    set_pose_action(root, b.id, action="strike", intention="hit silhouette")
    set_anticipation_follow_through(root, a.id, anticipation_frames=2, follow_through_frames=0)
    set_anticipation_follow_through(root, b.id, anticipation_frames=0, follow_through_frames=3)
    return a, b


def test_suggest_surfaces_missing_information_instead_of_guessing():
    with tempfile.TemporaryDirectory() as td:
        root = _setup(td)
        a = mark_key_pose(root, shot_id="shot_k", frame=1, label="A")
        b = mark_key_pose(root, shot_id="shot_k", frame=10, label="B")
        # No action, no arc, no spacing_mode
        result = suggest_inbetweens(
            root, from_key_pose_id=a.id, to_key_pose_id=b.id, spacing_mode=None
        )
        assert result["ok"] is False
        missing = result["missing_information"]
        assert any("action or intention" in m for m in missing)
        assert any("anticipation_frames unset" in m for m in missing)
        assert any("follow_through_frames unset" in m for m in missing)
        assert any("spacing_mode required" in m for m in missing)
        sug = result["suggestion"]
        assert sug.status == "blocked"
        assert sug.slots == []
        assert sug.applied_to_timing is False
        # Timing untouched
        shot = json.loads((root / "shots" / "shot_k.json").read_text(encoding="utf-8"))
        plan = load_timing_plan(root, shot["timing_plan_id"])
        assert plan.inbetween_slots == []


def test_preview_non_destructive_then_partial_accept():
    with tempfile.TemporaryDirectory() as td:
        root = _setup(td)
        a, b = _ready_pair(root)
        shot = json.loads((root / "shots" / "shot_k.json").read_text(encoding="utf-8"))
        plan_before = load_timing_plan(root, shot["timing_plan_id"]).model_dump(mode="json")

        result = suggest_inbetweens(
            root,
            from_key_pose_id=a.id,
            to_key_pose_id=b.id,
            spacing_mode="slow_in",
        )
        assert result["ok"]
        sug = result["suggestion"]
        assert sug.status == "preview"
        assert sug.applied_to_timing is False
        assert len(sug.slots) >= 1

        plan_mid = load_timing_plan(root, shot["timing_plan_id"]).model_dump(mode="json")
        assert plan_mid == plan_before

        prev = preview_suggestion(root, sug.id)
        assert prev["applied_to_timing"] is False
        assert len(prev["slots"]) == len(sug.slots)

        keep = [sug.slots[0].frame]
        if len(sug.slots) > 1:
            keep = [sug.slots[0].frame, sug.slots[1].frame]
        partial = partial_accept_suggestion(root, sug.id, accept_frames=keep)
        assert partial["ok"]
        assert partial["accepted_frames"] == sorted(keep)
        assert partial["suggestion"].status == "partial"
        assert partial["suggestion"].applied_to_timing is True

        plan = load_timing_plan(root, shot["timing_plan_id"])
        applied_frames = {s.frame for s in plan.inbetween_slots}
        assert set(keep).issubset(applied_frames)
        assert all(s.source.value == "generated" for s in plan.inbetween_slots if s.frame in keep)


def test_reject_suggestion_does_not_mutate_timing():
    with tempfile.TemporaryDirectory() as td:
        root = _setup(td)
        a, b = _ready_pair(root)
        shot = json.loads((root / "shots" / "shot_k.json").read_text(encoding="utf-8"))
        result = suggest_inbetweens(
            root, from_key_pose_id=a.id, to_key_pose_id=b.id, spacing_mode="linear"
        )
        before = load_timing_plan(root, shot["timing_plan_id"]).model_dump(mode="json")
        rejected = reject_suggestion(
            root, result["suggestion"].id, comment="Too floaty — redo breakdowns"
        )
        assert rejected["ok"]
        after = load_timing_plan(root, shot["timing_plan_id"]).model_dump(mode="json")
        assert after == before
        assert rejected["suggestion"].status == "rejected"


def test_never_rewrites_approved_key_poses_automatically():
    with tempfile.TemporaryDirectory() as td:
        root = _setup(td)
        a, b = _ready_pair(root)
        approve_key_pose(root, a.id, comment="Lock anticipation key")
        approved = json.loads((root / "key_poses" / f"{a.id}.json").read_text(encoding="utf-8"))

        with pytest.raises(PermissionError):
            set_pose_action(root, a.id, action="silently rewrite action")

        with pytest.raises(PermissionError):
            set_anticipation_follow_through(root, a.id, anticipation_frames=9)

        result = suggest_inbetweens(
            root, from_key_pose_id=a.id, to_key_pose_id=b.id, spacing_mode="stepped"
        )
        assert result["ok"]
        accept_suggestion(root, result["suggestion"].id)

        after = json.loads((root / "key_poses" / f"{a.id}.json").read_text(encoding="utf-8"))
        assert after == approved
        assert after["approval"] == ApprovalState.APPROVED.value
        assert after["action"] == "coil back"


def test_full_accept_and_mark_workflow():
    with tempfile.TemporaryDirectory() as td:
        root = _setup(td)
        a, b = _ready_pair(root)
        assert a.marked_as_key and b.marked_as_key
        result = suggest_inbetweens(
            root, from_key_pose_id=a.id, to_key_pose_id=b.id, spacing_mode="slow_out"
        )
        accepted = accept_suggestion(root, result["suggestion"].id)
        assert accepted["ok"]
        assert accepted["suggestion"].status == "accepted"
        shot = json.loads((root / "shots" / "shot_k.json").read_text(encoding="utf-8"))
        plan = load_timing_plan(root, shot["timing_plan_id"])
        assert len(plan.inbetween_slots) == len(result["suggestion"].slots)
