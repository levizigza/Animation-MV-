"""Fixture-based sequence-aware evaluation — identifies issues, never auto-fixes."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mvm.sequence_analysis import (
    SequenceEvaluation,
    evaluate_sequence,
    evaluate_shot_in_sequence,
    load_shots_fixture,
)

FIXTURES = Path(__file__).parent / "fixtures" / "sequences"


def test_closeup_repeat_and_gesture_explanations():
    seq_id, shots = load_shots_fixture(FIXTURES / "closeup_repeat.json")
    before = [s.model_dump(mode="json") for s in shots]

    ev = evaluate_shot_in_sequence(shots, "shot_b", sequence_id=seq_id)
    assert ev.previous_shot_id == "shot_a"
    assert ev.following_shot_id == "shot_c"
    assert ev.auto_fix_applied is False
    assert ev.shots_mutated is False

    explanations = [i.explanation for i in ev.issues]
    assert any(
        "close-up repeats the previous shot" in e.lower()
        or "close-up repeats the previous shot" in e.replace("\u2019", "'").lower()
        for e in explanations
    )
    # Normalize curly apostrophe
    assert any("repeats the previous shot" in e for e in explanations)
    assert any(i.kind == "repeated_gesture" for i in ev.issues)
    assert any("glance" in i.explanation for i in ev.issues if i.kind == "repeated_gesture")
    assert all(i.auto_fixed is False for i in ev.issues)

    after = [s.model_dump(mode="json") for s in shots]
    assert after == before


def test_pause_reaction_character_and_spatial_issues():
    seq_id, shots = load_shots_fixture(FIXTURES / "pause_and_reaction.json")
    fingerprints = {s.id: copy.deepcopy(s.model_dump(mode="json")) for s in shots}

    ev = evaluate_shot_in_sequence(shots, "shot_2", sequence_id=seq_id)
    texts = [i.explanation for i in ev.issues]
    assert any("pause is longer than the established rhythm" in t for t in texts)
    assert any(
        "reaction does not reflect the preceding event" in t.replace("\u2019", "'")
        for t in texts
    )

    # Character state: shadow/lead present, gone, return — on shot_2 or when evaluating shot_2
    assert any(i.kind == "character_state" for i in ev.issues) or any(
        st.present_in_previous and not st.present_in_current and st.present_in_following
        for st in ev.character_states
    )

    # Spatial jump more visible on shot_3
    ev3 = evaluate_shot_in_sequence(shots, "shot_3", sequence_id=seq_id)
    assert any(i.kind == "spatial_continuity" for i in ev3.issues) or any(
        "spatial continuity" in i.explanation.lower() for i in ev3.issues
    )

    for s in shots:
        assert s.model_dump(mode="json") == fingerprints[s.id]


def test_evaluate_sequence_never_auto_fixes_and_covers_neighbors():
    seq_id, shots = load_shots_fixture(FIXTURES / "closeup_repeat.json")
    reports = evaluate_sequence(shots, sequence_id=seq_id)
    assert len(reports) == 3
    focus_ids = [r.focus_shot_id for r in reports]
    assert focus_ids == ["shot_a", "shot_b", "shot_c"]
    # First has no previous; last has no following
    assert reports[0].previous_shot_id is None
    assert reports[-1].following_shot_id is None
    assert all(r.auto_fix_applied is False for r in reports)

    with pytest.raises(Exception):
        data = reports[1].model_dump(mode="json")
        data["auto_fix_applied"] = True
        SequenceEvaluation.model_validate(data)
