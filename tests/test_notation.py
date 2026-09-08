"""Creator-intent notation: ambiguity choice → draft MotionRequest (never final)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from mvm.notation import (
    NotationKind,
    NotationMark,
    analyze_notation,
    choose_interpretation,
    create_notation,
    load_motion_request,
    load_notation,
    translate_notation,
)
from mvm.project.domain_store import load_provenance, load_revisions


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in ("notation", "motion_requests", "revisions", "provenance", "shots"):
        (root / sub).mkdir(parents=True)
    return root


def test_ambiguous_notation_shows_interpretations_and_asks_choice():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        notation = create_notation(
            root,
            shot_id="shot_n",
            marks=[
                NotationMark(kind=NotationKind.FORCE_DIRECTION, value="up-left"),
                NotationMark(kind=NotationKind.MOTION_PATH, value="whip_arc"),
                NotationMark(kind=NotationKind.ANTICIPATION, value="coil_2f"),
                # Missing source/target, timing_emphasis, resolve after anticipation
            ],
        )
        result = translate_notation(root, notation.id)
        assert result["ok"] is False
        assert result["needs_choice"] is True
        assert result["ask_user_to_choose"] is True
        assert result["applied_as_final"] is False
        assert len(result["ambiguities"]) >= 1
        assert 2 <= len(result["interpretations"]) <= 3
        # No motion request baked yet
        assert list((root / "motion_requests").glob("*.json")) == []


def test_choice_recorded_in_provenance_and_motion_request_not_final():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        notation = create_notation(
            root,
            shot_id="shot_n",
            marks=[
                NotationMark(kind=NotationKind.SOURCE_OBJECT, value="fist"),
                NotationMark(kind=NotationKind.TARGET_OBJECT, value="chin"),
                NotationMark(kind=NotationKind.FORCE_DIRECTION, value="forward"),
                NotationMark(kind=NotationKind.MOTION_PATH, value="straight_jab"),
                NotationMark(kind=NotationKind.CONTACT_POINT, value="knuckle"),
                NotationMark(kind=NotationKind.ANTICIPATION, value="pull_back"),
                NotationMark(
                    kind=NotationKind.INTENDED_STILLNESS, value="hold_on_hit", frame=12
                ),
            ],
        )
        analyzed = analyze_notation(root, notation.id)
        assert analyzed["needs_choice"] is True
        interps = analyzed["ambiguity"].interpretations
        assert len(interps) >= 2

        chosen = interps[0]
        out = choose_interpretation(root, notation.id, chosen.id)
        assert out["ok"]
        assert out["applied_as_final"] is False
        req = out["motion_request"]
        assert req.applied_as_final is False
        assert req.status == "ready_for_review"
        assert req.interpretation_id == chosen.id
        assert req.source_object == "fist"
        assert req.target_object == "chin"

        loaded = load_motion_request(root, req.id)
        assert loaded.applied_as_final is False

        resolved = load_notation(root, notation.id)
        assert resolved.status == "resolved"
        assert resolved.chosen_interpretation_id == chosen.id
        assert resolved.converts_to_final_animation is False

        provs = load_provenance(root)
        assert any(
            p.operation == "human.notation_choose_interpretation"
            and p.outputs.get("interpretation_id") == chosen.id
            and p.outputs.get("applied_as_final") is False
            for p in provs
        )
        revs = load_revisions(root)
        assert any(
            r.snapshot.get("chosen_interpretation_id") == chosen.id for r in revs
        )


def test_freehand_alone_refuses_irreversible_conversion():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        notation = create_notation(
            root,
            shot_id="shot_n",
            marks=[],
            freehand_ref="sketches/rough_arrow.png",
        )
        result = translate_notation(root, notation.id)
        assert result["ok"] is False
        assert "freehand" in result["reason"].lower()
        assert result["applied_as_final"] is False
        assert list((root / "motion_requests").glob("*.json")) == []


def test_unambiguous_translate_still_not_final():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        notation = create_notation(
            root,
            shot_id="shot_n",
            marks=[
                NotationMark(kind=NotationKind.SOURCE_OBJECT, value="hand"),
                NotationMark(kind=NotationKind.TARGET_OBJECT, value="rail"),
                NotationMark(kind=NotationKind.MOTION_PATH, value="reach_out"),
                NotationMark(kind=NotationKind.FORCE_DIRECTION, value="forward"),
                NotationMark(kind=NotationKind.TIMING_EMPHASIS, value="contact"),
                NotationMark(kind=NotationKind.CONTACT_POINT, value="palm"),
                NotationMark(kind=NotationKind.ANTICIPATION, value="1f"),
                NotationMark(kind=NotationKind.OVERSHOOT, value="soft"),
                NotationMark(kind=NotationKind.SETTLE, value="2f"),
            ],
        )
        result = translate_notation(root, notation.id)
        assert result["ok"]
        req = result["motion_request"]
        assert req.applied_as_final is False
        assert req.timing_emphasis == "contact"
        assert req.motion_path == "reach_out"
        # Schema hard-locks final flag
        with pytest.raises(Exception):
            data = req.model_dump(mode="json")
            data["applied_as_final"] = True
            from mvm.schemas.notation import MotionRequest

            MotionRequest.model_validate(data)
