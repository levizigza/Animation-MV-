"""Approve/reject animatic: lifecycle, Review, unlock key poses."""

from __future__ import annotations

from pathlib import Path
import tempfile

from mvm.project.reviews import load_reviews
from mvm.project.workspace import _write_json
from mvm.schemas.lifecycle import LifecycleGateContext, transition_shot
from mvm.schemas.models import ProjectMeta, ShotLifecycleState
from mvm.storyboard.approve import approve_animatic, reject_animatic
from mvm.storyboard.workflow import (
    add_storyboard_panel,
    build_or_get_animatic,
    create_shot,
)


def _proj(td: Path) -> Path:
    root = td / "proj"
    for sub in (
        "shots",
        "panels",
        "animatics",
        "layouts",
        "revisions",
        "provenance",
        "reviews",
    ):
        (root / sub).mkdir(parents=True)
    _write_json(
        root / "project.json",
        ProjectMeta(
            slug="proj",
            title="A",
            prompt="t",
            audio_path="audio/master.wav",
        ),
    )
    return root


def test_approve_animatic_sets_flag_and_review():
    with tempfile.TemporaryDirectory() as td:
        root = _proj(Path(td))
        shot = create_shot(root, purpose="Clear rider silhouette into chorus")
        add_storyboard_panel(root, shot.id, caption="open")
        add_storyboard_panel(root, shot.id, caption="hit")
        anim = build_or_get_animatic(root, shot.id)
        out = approve_animatic(
            root, shot.id, anim.id, comment="Timing reads; approve animatic"
        )
        assert out["ok"], out
        assert out["shot"]["animatic_approved"] is True
        assert out["shot"]["lifecycle_state"] == "animatic"
        assert out["shot"]["approval"] == "pending_review"
        assert out["animatic"]["approved"] is True
        reviews = load_reviews(root)
        assert any(r.comment == "Timing reads; approve animatic" for r in reviews)
        assert any(r.state.value == "approved" for r in reviews)

        # Key poses now unblocked by animatic_approved gate
        from mvm.schemas.models import Shot

        shot2 = Shot.model_validate(out["shot"])
        ctx = LifecycleGateContext(
            has_storyboard_panel=True,
            has_layout=True,
            animatic_approved=True,
        )
        step = transition_shot(shot2, ShotLifecycleState.KEY_POSES, ctx)
        assert step.ok, step.reason


def test_reject_animatic_requires_comment_and_clears_flag():
    with tempfile.TemporaryDirectory() as td:
        root = _proj(Path(td))
        shot = create_shot(root, purpose="Reject path test purpose")
        add_storyboard_panel(root, shot.id, caption="a")
        anim = build_or_get_animatic(root, shot.id)
        approve_animatic(root, shot.id, anim.id)
        bad = reject_animatic(root, shot.id, anim.id, comment="")
        assert bad["ok"] is False
        out = reject_animatic(root, shot.id, anim.id, comment="Holds too short on hit")
        assert out["ok"]
        assert out["shot"]["animatic_approved"] is False
        assert out["animatic"]["approved"] is False
        assert any(r.state.value == "rejected" for r in load_reviews(root))
