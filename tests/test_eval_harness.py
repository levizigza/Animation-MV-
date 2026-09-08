"""Evaluation harness: three scenes, multi-dimension, human form, no single score."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mvm.eval_harness import (
    ALL_EVAL_DIMENSIONS,
    AUTO_EVAL_DIMENSIONS,
    EvalDimension,
    EvalSession,
    HumanReviewForm,
    SceneKind,
    evaluate_scene_automatic,
    list_scenes,
    load_session,
    run_all_scenes_auto,
    seed_harness_scenes,
    start_eval_session,
    submit_human_form,
)
from mvm.schemas.eval_harness import AutoEvalPass, PreferenceChoice
from mvm.project.domain_store import load_provenance


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in (
        "eval_scenes",
        "eval_sessions",
        "eval_forms",
        "provenance",
        "revisions",
    ):
        (root / sub).mkdir(parents=True)
    return root


def _filled_responses() -> list[dict]:
    notes = {
        EvalDimension.INTENT_CLARITY: "Purpose reads; emotional beat is clear in staging.",
        EvalDimension.POSE_READABILITY: "Speaker/listener silhouettes read without audio.",
        EvalDimension.TIMING: "Reaction delay after the line feels intentional.",
        EvalDimension.SPACING: "Slow-out into the listener hold feels authored.",
        EvalDimension.STILLNESS: "Listener hold is alive stillness, not a freeze bug.",
        EvalDimension.SEQUENCE_CONTEXT: "Works after the wide; sets up the hands cut.",
        EvalDimension.SOUND_RELATIONSHIP: "Silence before reply is kept; no forced lip flap.",
        EvalDimension.REVISION_QUALITY: "Better acting clarity than previous pass.",
        EvalDimension.HUMAN_REVIEWER_PREFERENCE: (
            "Prefer current revision for acting clarity; still watch the reply settle."
        ),
    }
    return [
        {
            "dimension": dim.value,
            "notes": notes[dim],
            "preference": PreferenceChoice.PREFER_CURRENT.value
            if dim == EvalDimension.HUMAN_REVIEWER_PREFERENCE
            else PreferenceChoice.UNDECIDED.value,
            "emphasis": "mild",
            "would_block_approval": False,
        }
        for dim in ALL_EVAL_DIMENSIONS
    ]


def test_three_scenes_cover_required_kinds():
    scenes = list_scenes()
    assert len(scenes) == 3
    kinds = {s.kind for s in scenes}
    assert kinds == {
        SceneKind.DIALOGUE,
        SceneKind.PHYSICAL_ACTION,
        SceneKind.QUIET,
    }
    assert len(ALL_EVAL_DIMENSIONS) == 9
    assert EvalDimension.HUMAN_REVIEWER_PREFERENCE in ALL_EVAL_DIMENSIONS
    assert EvalDimension.HUMAN_REVIEWER_PREFERENCE not in AUTO_EVAL_DIMENSIONS


def test_auto_pass_has_no_aggregate_and_skips_human_preference():
    for scene in list_scenes():
        auto = evaluate_scene_automatic(scene)
        assert auto.substitutes_for_human_review is False
        assert auto.has_aggregate_quality_score is False
        assert auto.quality_score is None
        dims = {o.dimension for o in auto.observations}
        assert EvalDimension.HUMAN_REVIEWER_PREFERENCE not in dims
        for d in AUTO_EVAL_DIMENSIONS:
            assert d in dims
        assert all(o.confidence >= 0.0 and o.message for o in auto.observations)

    with pytest.raises(Exception):
        AutoEvalPass(
            scene_id="x",
            observations=[],
            substitutes_for_human_review=True,  # type: ignore[arg-type]
        )


def test_seed_run_submit_stores_project_data_without_score():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        seeded = seed_harness_scenes(root)
        assert len(seeded) == 3
        assert (root / "eval_scenes" / "eval_scene_dialogue.json").exists()

        session = start_eval_session(
            root,
            scene_id="eval_scene_dialogue",
            revision_id="rev_a",
            previous_revision_id="rev_prev",
            run_auto=True,
        )
        assert session.human_review_required is True
        assert session.quality_score is None
        assert session.human_form and not session.human_form.completed
        assert session.auto_pass and session.auto_pass.observations

        # Blank prompts cannot be submitted
        with pytest.raises(ValueError, match="blank prompt"):
            submit_human_form(
                root,
                session_id=session.id,
                reviewer="director.lee",
                responses=[
                    r.model_dump(mode="json") for r in session.human_form.responses
                ],
            )

        session = submit_human_form(
            root,
            session_id=session.id,
            reviewer="director.lee",
            responses=_filled_responses(),
            overall_notes="Use for workflow improvement; no single score.",
        )
        assert session.human_form and session.human_form.completed
        summary = session.dimension_summary()
        assert summary["has_aggregate_quality_score"] is False
        assert summary["quality_score"] is None
        assert summary["human_form_completed"] is True
        for dim in ALL_EVAL_DIMENSIONS:
            assert summary[dim.value]["human_complete"] is True

        reloaded = load_session(root, session.id)
        assert reloaded.human_form.reviewer == "director.lee"
        assert (root / "eval_forms" / f"{reloaded.human_form.id}.json").exists()

        with pytest.raises(Exception):
            data = reloaded.model_dump(mode="json")
            data["quality_score"] = 88
            EvalSession.model_validate(data)

        with pytest.raises(Exception):
            data = reloaded.human_form.model_dump(mode="json")
            data["has_aggregate_quality_score"] = True
            HumanReviewForm.model_validate(data)

        with pytest.raises(ValueError, match="aggregate quality score"):
            submit_human_form(
                root,
                session_id=session.id,
                reviewer="director.lee",
                responses=[
                    {**r, "quality_score": 90} for r in _filled_responses()
                ],
            )

        provs = load_provenance(root)
        assert any(p.operation == "eval.seed_scenes" for p in provs)
        assert any(p.operation == "eval.human_submit" for p in provs)
        human = next(p for p in provs if p.operation == "eval.human_submit")
        assert human.actor.value == "human"


def test_run_all_creates_three_sessions():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        sessions = run_all_scenes_auto(root)
        assert len(sessions) == 3
        kinds = {s.scene_kind for s in sessions}
        assert kinds == {
            SceneKind.DIALOGUE,
            SceneKind.PHYSICAL_ACTION,
            SceneKind.QUIET,
        }
        for s in sessions:
            assert s.auto_pass is not None
            assert s.human_form is not None
            assert s.human_form.completed is False
