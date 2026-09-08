"""Symbolic grounder — hard craft rules veto illegal soft proposals."""

from __future__ import annotations

from typing import Any

from mvm.assistants.base import (
    ASSISTANT_FORBIDDEN_WRITE_DOMAINS,
    AssistantId,
    SUGGEST_WRITE_ALLOWLIST,
)
from mvm.neurosymbolic.schemas import (
    GroundingResult,
    GroundingStatus,
    NeuralProposal,
    SymbolicCraftState,
)
from mvm.schemas.lifecycle import DETAILED_ANIMATION_STATES, explain_transition
from mvm.schemas.models import Shot, ShotIntent, ShotLifecycleState


DETAILED_DOMAINS = frozenset(
    {"key_poses", "timing", "suggestions", "inbetweens", "sound_plans"}
)


def _shot_stub_from_state(state: SymbolicCraftState) -> Shot:
    """Minimal Shot for explain_transition when only SymbolicCraftState is available."""
    purpose = state.intent_purpose or (
        "Explicit craft intent" if state.intent_explicit else "Legacy shot — unset"
    )
    notes = "" if state.intent_explicit else "default_intent_placeholder"
    try:
        life = ShotLifecycleState(state.lifecycle_state)
    except ValueError:
        life = ShotLifecycleState.INTENT
    return Shot(
        id=state.shot_id,
        index=0,
        section="unknown",
        start=0.0,
        end=1.0,
        duration=1.0,
        intent=ShotIntent(purpose=purpose, notes=notes),
        lifecycle_state=life,
        animatic_approved=state.animatic_approved,
        timing_plan_id=state.timing_plan_id,
    )


def ground_proposal(
    state: SymbolicCraftState,
    proposal: NeuralProposal,
) -> GroundingResult:
    """Authorize, block, or escalate a soft proposal against symbolic craft state."""
    violated: list[str] = []
    explanations: list[str] = []
    checked: list[str] = []
    needs_human = False

    payload = proposal.payload or {}
    domain = (proposal.domain or "").strip()
    action = (proposal.action or "").strip()

    # --- universal craft bans ---
    checked.append("no_auto_smooth")
    if payload.get("allow_auto_smooth") is True or proposal.action in {
        "enable_auto_smooth",
        "silent_ease",
    }:
        violated.append("allow_auto_smooth")
        explanations.append(
            "Symbolic veto: silent auto-smooth / ease is forbidden on craft timing."
        )

    checked.append("no_applied_as_final")
    if payload.get("applied_as_final") is True or payload.get("applied") is True:
        violated.append("applied_as_final")
        explanations.append(
            "Symbolic veto: soft proposals cannot apply as final without human accept."
        )

    checked.append("no_force_every_cue")
    if payload.get("force_every_cue_to_motion") is True or action == "force_every_cue_to_motion":
        violated.append("force_every_cue_to_motion")
        explanations.append(
            "Symbolic veto: silence and non_reaction must remain valid sound choices."
        )

    # --- intent before detailed animation domains ---
    checked.append("intent_explicit")
    if domain in DETAILED_DOMAINS and not state.intent_explicit:
        violated.append("intent_explicit")
        explanations.append(
            "Symbolic veto: detailed animation domains require explicit ShotIntent.purpose."
        )

    # --- lifecycle advance proposals must pass explain_transition ---
    checked.append("lifecycle_transition")
    target_raw = payload.get("to_lifecycle") or payload.get("lifecycle_state")
    if action.startswith("advance_lifecycle") or target_raw:
        try:
            to_state = ShotLifecycleState(str(target_raw))
        except ValueError:
            to_state = None
            violated.append("lifecycle_target")
            explanations.append(
                f"Symbolic veto: unknown lifecycle target '{target_raw}'."
            )
        if to_state is not None:
            result = explain_transition(_shot_stub_from_state(state), to_state)
            if not result.ok:
                violated.append("lifecycle_transition")
                explanations.append(f"Symbolic veto: {result.reason}")

    # --- animatic gate for key-pose domain mutations ---
    checked.append("animatic_approved")
    if domain in {"key_poses", "suggestions"} and action.startswith(
        ("rewrite_", "approve_", "mark_")
    ):
        if not state.animatic_approved:
            if "suggest" not in action and action != "suggest_mark_extremes":
                needs_human = True
                explanations.append(
                    "Symbolic note: animatic not approved — human must unlock keys first."
                )

    # --- assistant domain fence ---
    checked.append("assistant_domain_fence")
    if proposal.source.value == "assistant" and proposal.assistant_id:
        try:
            aid = AssistantId(proposal.assistant_id)
        except ValueError:
            aid = None
        if aid is not None:
            forbidden = ASSISTANT_FORBIDDEN_WRITE_DOMAINS.get(aid, frozenset())
            if domain in forbidden and domain not in SUGGEST_WRITE_ALLOWLIST:
                if not action.startswith("suggest_") and not action.startswith("flag_"):
                    violated.append(f"fence:{aid.value}:{domain}")
                    explanations.append(
                        f"Symbolic veto: assistant '{aid.value}' cannot modify domain '{domain}'."
                    )
            if payload.get("write_domain") in forbidden:
                violated.append("fence:write_domain")
                explanations.append(
                    f"Symbolic veto: payload write_domain "
                    f"'{payload.get('write_domain')}' is outside assistant scope."
                )

    if proposal.assistant_id == AssistantId.POSE.value and domain == "timing":
        if not action.startswith("suggest_"):
            violated.append("pose_timing_fence")
            explanations.append(
                "Symbolic veto: pose assistant must not rewrite timing sheets."
            )

    # --- lifecycle awareness ---
    checked.append("lifecycle")
    try:
        life = ShotLifecycleState(state.lifecycle_state)
    except ValueError:
        life = None
    if life is not None and life in DETAILED_ANIMATION_STATES and not state.intent_explicit:
        violated.append("lifecycle_intent")
        explanations.append(
            "Symbolic veto: shot is in a detailed-animation lifecycle without explicit intent."
        )

    # --- MIR soft cel suggestions stay suggestions ---
    checked.append("mir_cel_suggestion")
    if proposal.source.value == "mir" and action in {"suggest_cel_mode", "suggest_smear"}:
        needs_human = True
        explanations.append(
            "Symbolic accept-as-suggestion: MIR energy may inform cel policy, "
            "but style-pack / exposure remain human-authored."
        )

    if violated:
        return GroundingResult(
            status=GroundingStatus.BLOCKED,
            violated_rules=violated,
            explanations=explanations,
            predicates_checked=checked,
        )

    if needs_human:
        return GroundingResult(
            status=GroundingStatus.NEEDS_HUMAN,
            violated_rules=[],
            explanations=explanations
            or ["Symbolic layer defers final creative choice to the human."],
            predicates_checked=checked,
        )

    return GroundingResult(
        status=GroundingStatus.ACCEPTED,
        violated_rules=[],
        explanations=explanations
        or [
            "Symbolic layer accepts this as a labeled suggestion only "
            "(applied remains false)."
        ],
        predicates_checked=checked,
    )
