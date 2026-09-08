"""Narrow assistants: scoped suggestions, provenance, no cross-domain writes."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mvm.assistants import (
    ASSISTANT_FORBIDDEN_WRITE_DOMAINS,
    AssistantId,
    attempt_forbidden_write,
    continuity_assistant,
    critique_assistant,
    pose_assistant,
    provenance_assistant,
    sound_assistant,
    storyboard_assistant,
    timing_assistant,
)
from mvm.project.domain_store import load_provenance


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in (
        "provenance",
        "revisions",
        "assistant_suggestions",
        "timing",
        "key_poses",
        "panels",
        "sound_plans",
        "critiques",
    ):
        (root / sub).mkdir(parents=True)
    return root


def test_each_assistant_states_assumptions_and_suggests_with_provenance():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        results = [
            storyboard_assistant(
                root, shot_id="shot_1", panel_ids=["p1"], durations=[4]
            ),
            timing_assistant(
                root, shot_id="shot_1", timing_plan_id="timing_1", mean_hold_frames=1
            ),
            pose_assistant(
                root,
                shot_id="shot_1",
                missing=["anticipation_frames unset on pose_a"],
            ),
            continuity_assistant(
                root,
                sequence_id="seq_1",
                focus_shot_id="shot_2",
                explanations=["This close-up repeats the previous shot’s emphasis."],
            ),
            sound_assistant(
                root, shot_id="shot_1", unassigned_cue_ids=["scue_beat_1"]
            ),
            critique_assistant(
                root, shot_id="shot_1", revision_id="rev_1", category_hints=["acting"]
            ),
            provenance_assistant(root, pending_provenance_ids=["prov_pending"]),
        ]
        assert len(results) == 7
        for r in results:
            assert r.input_assumptions, f"{r.assistant_id} missing assumptions"
            assert r.scope
            assert r.silently_edited is False
            assert r.provenance_id
            assert r.suggestions
            for s in r.suggestions:
                assert s.applied is False
                assert s.visibly_labeled_generated is True
                assert 0.0 <= s.confidence <= 1.0
                assert s.reason
                assert s.uncertainty is not None

        provs = load_provenance(root)
        assert any(p.operation.startswith("assistant.") for p in provs)
        assert any(p.visibly_labeled_generated for p in provs)


def test_assistants_cannot_modify_outside_allowed_domain():
    """One assistant must not write another domain's craft data."""
    cases = [
        (AssistantId.STORYBOARD, "timing"),
        (AssistantId.STORYBOARD, "key_poses"),
        (AssistantId.STORYBOARD, "sound_plans"),
        (AssistantId.TIMING, "key_poses"),
        (AssistantId.TIMING, "panels"),
        (AssistantId.TIMING, "animatics"),
        (AssistantId.POSE, "timing"),
        (AssistantId.POSE, "sound_plans"),
        (AssistantId.POSE, "panels"),
        (AssistantId.CONTINUITY, "shots"),
        (AssistantId.CONTINUITY, "timing"),
        (AssistantId.SOUND, "timing"),
        (AssistantId.SOUND, "key_poses"),
        (AssistantId.CRITIQUE, "key_poses"),
        (AssistantId.CRITIQUE, "sound_plans"),
        (AssistantId.PROVENANCE, "timing"),
        (AssistantId.PROVENANCE, "critiques"),
        (AssistantId.PROVENANCE, "shots"),
    ]
    for assistant_id, domain in cases:
        assert domain in ASSISTANT_FORBIDDEN_WRITE_DOMAINS[assistant_id]
        with pytest.raises(PermissionError, match="cannot modify domain"):
            attempt_forbidden_write(assistant_id, domain)

    # Suggest-time allowlist still blocks craft domains even if not listed forbidden
    with pytest.raises(PermissionError):
        attempt_forbidden_write(AssistantId.STORYBOARD, "xsheets")


def test_pose_assistant_run_does_not_write_timing_files():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        timing_dir = root / "timing"
        before = {p.name: p.read_bytes() for p in timing_dir.glob("*.json")}
        # plant a file that must remain untouched
        marker = timing_dir / "do_not_touch.json"
        marker.write_text('{"keep": true}', encoding="utf-8")

        result = pose_assistant(root, shot_id="shot_1", from_pose_id="a", to_pose_id="b")
        assert result.silently_edited is False
        assert marker.read_text(encoding="utf-8") == '{"keep": true}'
        after = {p.name: p.read_bytes() for p in timing_dir.glob("*.json")}
        assert after["do_not_touch.json"] == before.get(
            "do_not_touch.json", marker.read_bytes()
        )
        # Only assistant_suggestions / provenance / revisions should gain files
        assert (root / "assistant_suggestions").exists()
