"""Storyboard + animatic: order, duration, version compare, persistence."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from mvm.project.workspace import _write_json
from mvm.schemas.models import ProjectMeta, ShotIntent
from mvm.storyboard.workflow import (
    add_storyboard_panel,
    attach_shot_intention,
    build_or_get_animatic,
    compare_animatics,
    create_shot,
    list_animatics_for_shot,
    load_animatic,
    load_panel,
    new_animatic_version,
    preview_animatic,
    reorder_panels,
    set_panel_duration,
)


def _root(td: Path) -> Path:
    root = td / "proj"
    for sub in ("shots", "panels", "animatics", "revisions", "provenance"):
        (root / sub).mkdir(parents=True)
    _write_json(
        root / "project.json",
        ProjectMeta(
            slug="proj",
            title="SB",
            prompt="test",
            audio_path="audio/master.wav",
        ),
    )
    return root


def test_create_shot_requires_intent_and_persists():
    with tempfile.TemporaryDirectory() as td:
        root = _root(Path(td))
        with pytest.raises(ValueError):
            create_shot(root, purpose="  ")
        shot = create_shot(root, purpose="Wide establish in rain")
        assert shot.intent.purpose == "Wide establish in rain"
        assert (root / "shots" / f"{shot.id}.json").exists()
        updated = attach_shot_intention(
            root, shot.id, ShotIntent(purpose="Closer: rider silhouette")
        )
        assert updated.intent.purpose.startswith("Closer")


def test_panel_order_and_duration_on_animatic_not_artwork():
    with tempfile.TemporaryDirectory() as td:
        root = _root(Path(td))
        shot = create_shot(root, purpose="Animatic test")
        p1 = add_storyboard_panel(root, shot.id, caption="A", default_duration_frames=12)
        p2 = add_storyboard_panel(root, shot.id, caption="B", default_duration_frames=24)
        p3 = add_storyboard_panel(root, shot.id, caption="C", default_duration_frames=36)
        anim = build_or_get_animatic(root, shot.id)
        assert [p.panel_id for p in sorted(anim.panels, key=lambda x: x.order)] == [
            p1.id,
            p2.id,
            p3.id,
        ]

        reordered = reorder_panels(root, anim.id, [p3.id, p1.id, p2.id])
        assert [p.panel_id for p in sorted(reordered.panels, key=lambda x: x.order)] == [
            p3.id,
            p1.id,
            p2.id,
        ]
        # Persist reload
        reloaded = load_animatic(root, anim.id)
        assert [p.panel_id for p in sorted(reloaded.panels, key=lambda x: x.order)] == [
            p3.id,
            p1.id,
            p2.id,
        ]

        artwork_before = load_panel(root, p1.id).default_duration_frames
        set_panel_duration(root, anim.id, p1.id, 48)
        artwork_after = load_panel(root, p1.id).default_duration_frames
        assert artwork_before == artwork_after == 12
        anim2 = load_animatic(root, anim.id)
        dur = next(p.duration_frames for p in anim2.panels if p.panel_id == p1.id)
        assert dur == 48


def test_preview_and_version_compare_persistence():
    with tempfile.TemporaryDirectory() as td:
        root = _root(Path(td))
        shot = create_shot(root, purpose="Compare versions")
        a = add_storyboard_panel(root, shot.id, caption="open", default_duration_frames=10)
        b = add_storyboard_panel(root, shot.id, caption="hit", default_duration_frames=20)
        v1 = build_or_get_animatic(root, shot.id)
        timeline = preview_animatic(root, v1.id)
        assert len(timeline) == 2
        assert timeline[0].start_frame == 0
        assert timeline[0].end_frame == 10
        assert timeline[1].start_frame == 10
        assert timeline[1].duration_frames == 20
        assert (root / "animatics" / f"{v1.id}_preview.json").exists()

        v2 = new_animatic_version(root, v1.id, label="longer hit")
        assert v2.version == 2
        assert v2.parent_animatic_id == v1.id
        set_panel_duration(root, v2.id, b.id, 40)
        reorder_panels(root, v2.id, [b.id, a.id])

        diff = compare_animatics(root, v1.id, v2.id)
        assert diff.order_changed is True
        assert diff.order_a == [a.id, b.id]
        assert diff.order_b == [b.id, a.id]
        assert any(ch["panel_id"] == b.id and ch["delta_frames"] == 20 for ch in diff.duration_changes)
        assert diff.total_frames_a == 30
        assert diff.total_frames_b == 50
        assert (root / "animatics" / f"diff_{v1.id}_{v2.id}.json").exists()

        versions = list_animatics_for_shot(root, shot.id)
        assert [v.version for v in versions] == [1, 2]
        # Both versions remain first-class files
        assert (root / "animatics" / f"{v1.id}.json").exists()
        assert (root / "animatics" / f"{v2.id}.json").exists()
        raw = json.loads((root / "animatics" / f"{v1.id}.json").read_text(encoding="utf-8"))
        assert raw["timing_only"] is True
