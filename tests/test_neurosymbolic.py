"""Neuro-symbolic grounding: soft proposals vetoed/accepted by symbolic craft rules."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from mvm.neurosymbolic.bridge import decide, proposals_from_assistant_result
from mvm.neurosymbolic.grounding import ground_proposal
from mvm.neurosymbolic.schemas import (
    GroundingStatus,
    NeuralProposal,
    NeuroSymbolicDecision,
    ProposalSource,
    SymbolicCraftState,
)
from mvm.neurosymbolic.symbolic import build_symbolic_state
from mvm.assistants.base import AssistantId, AssistantResult, AssistantSuggestion
from mvm.schemas.models import Shot, ShotIntent


def _state(**kwargs) -> SymbolicCraftState:
    shot = Shot(
        id="shot_1",
        index=0,
        section="chorus",
        start=0.0,
        end=2.0,
        duration=2.0,
        intent=ShotIntent(purpose="Read the punchline silhouette"),
        description="test",
    )
    base = build_symbolic_state(shot=shot, style_pack="classic_cel")
    return base.model_copy(update=kwargs)


def test_auto_smooth_proposal_blocked():
    state = _state(intent_explicit=True)
    prop = NeuralProposal(
        source=ProposalSource.HEURISTIC_AGENT,
        domain="timing",
        action="enable_auto_smooth",
        payload={"allow_auto_smooth": True},
        confidence=0.9,
        reason="Ease the holds for polish",
    )
    g = ground_proposal(state, prop)
    assert g.status == GroundingStatus.BLOCKED
    assert "allow_auto_smooth" in g.violated_rules
    assert any("auto-smooth" in e.lower() or "ease" in e.lower() for e in g.explanations)


def test_cross_domain_assistant_write_blocked():
    state = _state(intent_explicit=True)
    prop = NeuralProposal(
        source=ProposalSource.ASSISTANT,
        domain="timing",
        action="rewrite_timing_sheet",
        payload={"write_domain": "timing", "hold_frames": 4},
        confidence=0.7,
        reason="Pose assistant rewriting timing",
        assistant_id=AssistantId.POSE.value,
    )
    g = ground_proposal(state, prop)
    assert g.status == GroundingStatus.BLOCKED
    assert g.violated_rules
    assert any("fence" in r or "pose" in r for r in g.violated_rules)


def test_legal_timing_hold_suggestion_accepted_not_applied():
    state = _state(intent_explicit=True)
    prop = NeuralProposal(
        source=ProposalSource.ASSISTANT,
        domain="timing",
        action="suggest_extend_hold",
        payload={"shot_id": "shot_1", "frames": 2},
        confidence=0.65,
        uncertainty="Hold length is taste",
        reason="Extend hold on beat for readability",
        assistant_id=AssistantId.TIMING.value,
    )
    g = ground_proposal(state, prop)
    assert g.status == GroundingStatus.ACCEPTED
    assert g.ok_as_suggestion

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "proj"
        for sub in ("neurosymbolic_decisions", "provenance", "revisions"):
            (root / sub).mkdir(parents=True)
        decisions = decide(root, "shot_1", [prop], state=state, persist=True)
        assert len(decisions) == 1
        d = decisions[0]
        assert d.applied is False
        assert d.grounding.status == GroundingStatus.ACCEPTED
        assert (root / "neurosymbolic_decisions" / f"{d.id}.json").exists()
        assert d.provenance_id


def test_decision_refuses_aggregate_score_and_silent_apply():
    prop = NeuralProposal(
        source=ProposalSource.MIR,
        domain="shots",
        action="suggest_cel_mode",
        payload={"suggested_cel_mode": "limited"},
        confidence=0.5,
        reason="Low energy section",
    )
    g = ground_proposal(_state(intent_explicit=True), prop)
    with pytest.raises(ValidationError):
        NeuroSymbolicDecision(
            proposal=prop,
            grounding=g,
            applied=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        NeuroSymbolicDecision(
            proposal=prop,
            grounding=g,
            applied=False,
            has_aggregate_quality_score=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        NeuroSymbolicDecision(
            proposal=prop,
            grounding=g,
            applied=False,
            quality_score=0.91,  # type: ignore[arg-type]
        )


def test_force_every_cue_blocked():
    state = _state(intent_explicit=True)
    prop = NeuralProposal(
        source=ProposalSource.ASSISTANT,
        domain="sound_plans",
        action="force_every_cue_to_motion",
        payload={"force_every_cue_to_motion": True},
        confidence=0.8,
        reason="Sync everything",
        assistant_id=AssistantId.SOUND.value,
    )
    g = ground_proposal(state, prop)
    assert g.status == GroundingStatus.BLOCKED
    assert "force_every_cue_to_motion" in g.violated_rules


def test_assistant_bridge_maps_suggestions():
    result = AssistantResult(
        assistant_id=AssistantId.TIMING,
        input_assumptions=["timing plan exists"],
        scope=["timing"],
        suggestions=[
            AssistantSuggestion(
                assistant_id=AssistantId.TIMING,
                domain="timing",
                action="suggest_extend_hold",
                payload={"shot_id": "shot_1"},
                reason="Hold for lyric",
                confidence=0.6,
            )
        ],
        summary="test",
    )
    props = proposals_from_assistant_result(result)
    assert len(props) == 1
    assert props[0].source == ProposalSource.ASSISTANT
    assert props[0].assistant_id == "timing"
