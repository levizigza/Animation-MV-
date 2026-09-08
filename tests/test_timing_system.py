"""Timing system: holds, spacing, authored vs generated, reversible interpolation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from mvm.schemas.domain import (
    KeyPose,
    SpacingCurve,
    SpacingMode,
    TimingSource,
)
from mvm.timing import (
    add_annotation,
    add_hold,
    apply_spacing_interpolation,
    build_timeline,
    compare_timing_plans,
    create_timing_plan,
    custom_curve_roundtrip,
    export_timing_bundle,
    import_timing_bundle,
    inspect_timeline,
    load_timing_plan,
    new_timing_version,
    progress_at,
    revert_generated_interpolation,
    sample_progress,
    set_spacing_segment,
)
from mvm.timing.curves import reconstruct_custom_from_samples


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in ("timing", "key_poses", "revisions", "provenance", "timing_exports"):
        (root / sub).mkdir(parents=True)
    return root


def test_intentional_holds_survive_export_import():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        pose = KeyPose(
            id="pose_hold",
            shot_id="shot_t",
            frame=1,
            label="settle",
            description="authored extreme",
            is_extreme=True,
        )
        plan = create_timing_plan(
            root, shot_id="shot_t", end_frame=24, key_poses=[pose]
        )
        plan = add_hold(
            root,
            plan.id,
            frame=1,
            duration_frames=6,
            kind="hold",
            key_pose_id=pose.id,
            notes="intentional settle hold",
        )
        plan = add_hold(
            root, plan.id, frame=10, duration_frames=3, kind="pause", notes="breath"
        )
        plan = add_hold(
            root,
            plan.id,
            frame=16,
            duration_frames=1,
            kind="anticipation",
            notes="coil",
        )
        plan = add_hold(
            root, plan.id, frame=18, duration_frames=1, kind="impact", notes="hit"
        )

        bundle = export_timing_bundle(root, plan.id)
        imported = import_timing_bundle(root, bundle, new_ids=True)

        kinds = {(e.kind, e.duration_frames, e.notes) for e in imported.exposures}
        assert ("hold", 6, "intentional settle hold") in kinds
        assert ("pause", 3, "breath") in kinds
        assert ("anticipation", 1, "coil") in kinds
        assert ("impact", 1, "hit") in kinds
        assert all(e.source == TimingSource.AUTHORED for e in imported.exposures)
        assert imported.allow_auto_smooth is False


def test_timing_edits_do_not_alter_key_pose_content():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        pose_a = KeyPose(
            id="pose_a",
            shot_id="shot_t",
            frame=1,
            label="A",
            description="do not touch",
            asset_ref="keys/a.gpencil",
        )
        pose_b = KeyPose(
            id="pose_b",
            shot_id="shot_t",
            frame=20,
            label="B",
            description="also sacred",
            asset_ref="keys/b.gpencil",
        )
        plan = create_timing_plan(
            root, shot_id="shot_t", end_frame=24, key_poses=[pose_a, pose_b]
        )
        before_a = json.loads((root / "key_poses" / "pose_a.json").read_text(encoding="utf-8"))
        before_b = json.loads((root / "key_poses" / "pose_b.json").read_text(encoding="utf-8"))

        add_hold(root, plan.id, frame=1, duration_frames=4, key_pose_id="pose_a")
        add_annotation(root, plan.id, frame=5, text="ease into B", kind="spacing")
        set_spacing_segment(
            root,
            plan.id,
            from_key_pose_id="pose_a",
            to_key_pose_id="pose_b",
            start_frame=1,
            end_frame=20,
            mode=SpacingMode.SLOW_IN_OUT,
            anticipation_frames=[3],
            impact_frames=[20],
            pause_frames=[12],
        )
        plan2 = load_timing_plan(root, plan.id)
        seg = plan2.spacing_segments[0]
        apply_spacing_interpolation(root, plan.id, seg.id)

        after_a = json.loads((root / "key_poses" / "pose_a.json").read_text(encoding="utf-8"))
        after_b = json.loads((root / "key_poses" / "pose_b.json").read_text(encoding="utf-8"))
        assert after_a == before_a
        assert after_b == before_b
        assert after_a["description"] == "do not touch"
        assert after_a["asset_ref"] == "keys/a.gpencil"


def test_interpolation_remains_reversible():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        pose_a = KeyPose(id="pose_a", shot_id="shot_t", frame=1, label="A")
        pose_b = KeyPose(id="pose_b", shot_id="shot_t", frame=13, label="B")
        plan = create_timing_plan(
            root, shot_id="shot_t", end_frame=16, key_poses=[pose_a, pose_b]
        )
        set_spacing_segment(
            root,
            plan.id,
            from_key_pose_id="pose_a",
            to_key_pose_id="pose_b",
            start_frame=1,
            end_frame=13,
            mode=SpacingMode.STEPPED,
            step_count=4,
        )
        # Authored slot should survive revert of generated ones
        from mvm.schemas.domain import InBetweenSlot
        from mvm.timing.workflow import save_timing_plan

        plan = load_timing_plan(root, plan.id)
        plan.inbetween_slots.append(
            InBetweenSlot(
                frame=7,
                from_key_pose_id="pose_a",
                to_key_pose_id="pose_b",
                kind="breakdown",
                notes="human breakdown",
                source=TimingSource.AUTHORED,
            )
        )
        save_timing_plan(root, plan)

        seg = load_timing_plan(root, plan.id).spacing_segments[0]
        result = apply_spacing_interpolation(root, plan.id, seg.id)
        assert result["ok"]
        mid = load_timing_plan(root, plan.id)
        assert any(s.source == TimingSource.GENERATED for s in mid.inbetween_slots)
        assert any(
            s.source == TimingSource.AUTHORED and s.notes == "human breakdown"
            for s in mid.inbetween_slots
        )

        reverted = revert_generated_interpolation(
            root, plan.id, revision_id=result["revision_id"]
        )
        assert reverted["ok"]
        restored = reverted["timing_plan"]
        assert all(s.source != TimingSource.GENERATED for s in restored.inbetween_slots)
        assert any(s.notes == "human breakdown" for s in restored.inbetween_slots)

        # Custom curve sample reconstruction
        pts = [(0.0, 0.0), (0.5, 0.2), (1.0, 1.0)]
        rebuilt = custom_curve_roundtrip(pts, sample_count=5)
        assert rebuilt.mode == SpacingMode.CUSTOM
        samples = sample_progress(
            SpacingCurve(id="c", mode=SpacingMode.CUSTOM, control_points=pts), 5
        )
        again = reconstruct_custom_from_samples(samples, curve_id="c2")
        for t, v in samples:
            assert abs(progress_at(again, t) - v) < 1e-9


def test_authored_vs_generated_distinguishable_on_timeline():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        pose_a = KeyPose(id="pose_a", shot_id="shot_t", frame=1, label="A")
        pose_b = KeyPose(id="pose_b", shot_id="shot_t", frame=10, label="B")
        plan = create_timing_plan(
            root, shot_id="shot_t", end_frame=12, key_poses=[pose_a, pose_b]
        )
        add_hold(
            root,
            plan.id,
            frame=1,
            duration_frames=2,
            kind="hold",
            key_pose_id="pose_a",
            notes="authored hold",
        )
        set_spacing_segment(
            root,
            plan.id,
            from_key_pose_id="pose_a",
            to_key_pose_id="pose_b",
            start_frame=1,
            end_frame=10,
            mode=SpacingMode.SLOW_IN,
            anticipation_frames=[2],
            impact_frames=[10],
        )
        seg = load_timing_plan(root, plan.id).spacing_segments[0]
        apply_spacing_interpolation(root, plan.id, seg.id)

        tl = inspect_timeline(root, plan.id)
        assert tl.authored_count >= 1
        assert tl.generated_count >= 1
        sources = {e.frame: e.source for e in tl.entries}
        # Hold frames authored
        assert sources.get(1) == TimingSource.AUTHORED
        # Interior generated spacing slots
        generated_frames = [
            e.frame for e in tl.entries if e.source == TimingSource.GENERATED
        ]
        assert generated_frames, "expected generated timing frames on timeline"
        authored_frames = [
            e.frame for e in tl.entries if e.source == TimingSource.AUTHORED
        ]
        assert authored_frames, "expected authored timing frames on timeline"
        hold_authored = {
            e.frame
            for e in tl.entries
            if e.exposure_kind == "hold" and e.source == TimingSource.AUTHORED
        }
        assert hold_authored
        assert set(generated_frames).isdisjoint(hold_authored)
        # Explicit discrimination in summary
        assert "authored=" in tl.summary and "generated=" in tl.summary
        assert "auto_smooth=False" in tl.summary


def test_timing_version_compare_and_stepped_no_silent_smooth():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        pose_a = KeyPose(id="pose_a", shot_id="shot_t", frame=1, label="A")
        pose_b = KeyPose(id="pose_b", shot_id="shot_t", frame=9, label="B")
        plan = create_timing_plan(
            root, shot_id="shot_t", end_frame=12, key_poses=[pose_a, pose_b]
        )
        set_spacing_segment(
            root,
            plan.id,
            from_key_pose_id="pose_a",
            to_key_pose_id="pose_b",
            start_frame=1,
            end_frame=9,
            mode=SpacingMode.STEPPED,
            step_count=2,
        )
        child = new_timing_version(root, plan.id, label="slow-out experiment")
        set_spacing_segment(
            root,
            child.id,
            from_key_pose_id="pose_a",
            to_key_pose_id="pose_b",
            start_frame=1,
            end_frame=9,
            mode=SpacingMode.SLOW_OUT,
        )
        add_annotation(root, child.id, frame=5, text="try slow-out", kind="spacing")

        diff = compare_timing_plans(root, plan.id, child.id)
        assert diff.key_pose_ids_unchanged
        assert any(c.get("mode_a") == "stepped" for c in diff.segment_changes)
        assert any(c.get("mode_b") == "slow_out" for c in diff.segment_changes)

        curve = SpacingCurve(
            id="c", mode=SpacingMode.STEPPED, step_count=2, source=TimingSource.AUTHORED
        )
        # Stepped plateaus — not a continuous ease
        assert progress_at(curve, 0.0) == 0.0
        assert progress_at(curve, 0.49) == 0.0
        assert progress_at(curve, 0.5) == 0.5
        assert progress_at(curve, 0.99) == 0.5

        with pytest.raises(Exception):
            SpacingCurve(id="bad", mode=SpacingMode.CUSTOM, control_points=[])

        tl = build_timeline(load_timing_plan(root, child.id))
        assert tl.version == child.version
