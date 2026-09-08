"""Bridge soft MIR / assistant proposals into symbolic grounding + ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.assistants.base import AssistantResult, AssistantSuggestion
from mvm.neurosymbolic.grounding import ground_proposal
from mvm.neurosymbolic.schemas import (
    GroundingStatus,
    NeuralProposal,
    NeuroSymbolicDecision,
    ProposalSource,
    SymbolicCraftState,
)
from mvm.neurosymbolic.symbolic import load_symbolic_state_for_shot
from mvm.provenance import record_meaningful_change
from mvm.schemas.domain import ActorKind
from mvm.schemas.models import Beatmap, Shot


def proposals_from_assistant_result(result: AssistantResult) -> list[NeuralProposal]:
    """Map assistant suggestions onto the stable NeuralProposal interface."""
    out: list[NeuralProposal] = []
    for s in result.suggestions:
        out.append(_suggestion_to_proposal(s))
    return out


def _suggestion_to_proposal(s: AssistantSuggestion) -> NeuralProposal:
    return NeuralProposal(
        id=s.id.replace("asug", "nprop") if s.id.startswith("asug") else s.id,
        source=ProposalSource.ASSISTANT,
        domain=s.domain,
        action=s.action,
        payload=dict(s.payload),
        confidence=s.confidence,
        uncertainty=s.uncertainty,
        reason=s.reason,
        assistant_id=s.assistant_id.value,
    )


def proposals_from_music_analysis(
    *,
    beatmap: Beatmap,
    shots: list[Shot],
    style_pack: str = "",
) -> list[NeuralProposal]:
    """MIR section energy → suggested cel emphasis (never auto-applied)."""
    by_name = {sec.name: sec for sec in beatmap.sections}
    proposals: list[NeuralProposal] = []
    for shot in shots:
        sec = by_name.get(shot.section)
        energy = float(sec.energy) if sec is not None else 0.5
        if energy >= 0.72:
            proposals.append(
                NeuralProposal(
                    source=ProposalSource.MIR,
                    domain="shots",
                    action="suggest_smear",
                    payload={
                        "shot_id": shot.id,
                        "section": shot.section,
                        "energy": energy,
                        "suggested_smear_density": min(1.0, 0.35 + energy * 0.4),
                        "style_pack": style_pack,
                    },
                    confidence=min(0.9, 0.45 + energy * 0.4),
                    uncertainty="Energy peaks do not dictate exposure policy alone.",
                    reason=(
                        f"High section energy ({energy:.2f}) may warrant denser "
                        f"smear accents on {shot.id}; style-pack still decides."
                    ),
                )
            )
        elif energy <= 0.35:
            proposals.append(
                NeuralProposal(
                    source=ProposalSource.MIR,
                    domain="shots",
                    action="suggest_cel_mode",
                    payload={
                        "shot_id": shot.id,
                        "section": shot.section,
                        "energy": energy,
                        "suggested_cel_mode": "limited",
                        "style_pack": style_pack,
                    },
                    confidence=min(0.85, 0.4 + (1.0 - energy) * 0.3),
                    uncertainty="Low energy may still use full animation for story.",
                    reason=(
                        f"Low section energy ({energy:.2f}) may suit limited cel "
                        f"on {shot.id}; human / style-pack must confirm."
                    ),
                )
            )
    return proposals


def decide(
    root: Path,
    shot_id: str | None,
    proposals: list[NeuralProposal],
    *,
    state: SymbolicCraftState | None = None,
    persist: bool = True,
    record_provenance: bool = True,
) -> list[NeuroSymbolicDecision]:
    """Ground proposals, optionally persist decisions + provenance."""
    if state is None:
        if not shot_id:
            raise ValueError("shot_id required when state is not provided")
        state = load_symbolic_state_for_shot(root, shot_id)

    decisions: list[NeuroSymbolicDecision] = []
    for prop in proposals:
        grounding = ground_proposal(state, prop)
        summary = (
            f"{grounding.status.value}: {prop.action} "
            f"({prop.source.value}/{prop.domain})"
        )
        dec = NeuroSymbolicDecision(
            proposal=prop,
            grounding=grounding,
            applied=False,
            shot_id=shot_id or state.shot_id,
            summary=summary,
        )
        if persist:
            path = _persist_decision(root, dec)
            if record_provenance:
                recorded = record_meaningful_change(
                    root,
                    operation="neurosymbolic.ground",
                    target_type="shot",
                    target_id=dec.shot_id or "project",
                    snapshot={
                        "decision_id": dec.id,
                        "proposal": prop.model_dump(mode="json"),
                        "grounding": grounding.model_dump(mode="json"),
                        "layers": {
                            "neuro": prop.source.value,
                            "symbolic": grounding.status.value,
                        },
                        "applied": False,
                    },
                    summary=summary,
                    creator="neurosymbolic.grounder",
                    actor=ActorKind.HEURISTIC_AGENT,
                    source_references=[
                        f"neuro:{prop.source.value}",
                        "symbolic:grounder",
                        f"file:{path.name}",
                    ],
                    input_parameters={
                        "shot_id": dec.shot_id,
                        "proposal_id": prop.id,
                        "action": prop.action,
                    },
                    outputs={
                        "status": grounding.status.value,
                        "violated_rules": grounding.violated_rules,
                        "applied": False,
                    },
                    generated_alternatives=[
                        {
                            "id": prop.id,
                            "action": prop.action,
                            "confidence": prop.confidence,
                            "layer": "neuro",
                        }
                    ],
                    generated=True,
                )
                dec.provenance_id = recorded["provenance"].id
                _persist_decision(root, dec)
        decisions.append(dec)
    return decisions


def ground_assistant_result(
    root: Path,
    result: AssistantResult,
    *,
    shot_id: str | None = None,
) -> AssistantResult:
    """Attach grounding to each suggestion and persist neuro-symbolic decisions."""
    proposals = proposals_from_assistant_result(result)
    if not proposals:
        return result

    sid = shot_id or _infer_shot_id(result)
    state = None
    if sid and (root / "shots" / f"{sid}.json").exists():
        state = load_symbolic_state_for_shot(root, sid)

    grounded_payload: list[dict[str, Any]] = []
    if state is not None:
        decisions = decide(root, sid, proposals, state=state, persist=True)
        by_action = {(d.proposal.action, d.proposal.domain): d for d in decisions}
        for s in result.suggestions:
            key = (s.action, s.domain)
            dec = by_action.get(key)
            if dec is None:
                # fall back match by id prefix
                dec = next(
                    (d for d in decisions if d.proposal.action == s.action),
                    None,
                )
            if dec is not None:
                grounded_payload.append(
                    {
                        "suggestion_id": s.id,
                        "decision_id": dec.id,
                        "grounding": dec.grounding.model_dump(mode="json"),
                        "layers": {
                            "neuro": ProposalSource.ASSISTANT.value,
                            "symbolic": dec.grounding.status.value,
                        },
                    }
                )
    else:
        # No shot on disk yet — ground against a minimal permissive state shell
        from mvm.neurosymbolic.schemas import SymbolicCraftState

        shell = SymbolicCraftState(
            shot_id=sid or "unknown",
            intent_explicit=True,
            animatic_approved=False,
        )
        for prop in proposals:
            g = ground_proposal(shell, prop)
            grounded_payload.append(
                {
                    "proposal_id": prop.id,
                    "grounding": g.model_dump(mode="json"),
                    "layers": {
                        "neuro": prop.source.value,
                        "symbolic": g.status.value,
                    },
                }
            )
            decide(root, sid, [prop], state=shell, persist=True)

    # Re-save assistant result with grounding attachment
    data = result.model_dump(mode="json")
    data["neurosymbolic"] = {
        "grounded": grounded_payload,
        "accepted": sum(
            1
            for g in grounded_payload
            if g.get("grounding", {}).get("status") == GroundingStatus.ACCEPTED.value
        ),
        "blocked": sum(
            1
            for g in grounded_payload
            if g.get("grounding", {}).get("status") == GroundingStatus.BLOCKED.value
        ),
        "needs_human": sum(
            1
            for g in grounded_payload
            if g.get("grounding", {}).get("status") == GroundingStatus.NEEDS_HUMAN.value
        ),
    }
    from mvm.assistants.runner import save_assistant_result

    # Write enriched JSON (schema stays AssistantResult + extra key)
    d = root / "assistant_suggestions"
    d.mkdir(parents=True, exist_ok=True)
    name = result.provenance_id or (
        result.suggestions[0].id if result.suggestions else result.assistant_id.value
    )
    path = d / f"{name}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return result


def ground_planning_mir(
    root: Path,
    *,
    beatmap: Beatmap,
    shots: list[Shot],
    style_pack: str = "",
) -> list[NeuroSymbolicDecision]:
    """Emit MIR proposals, ground each against per-shot symbolic state, persist."""
    proposals = proposals_from_music_analysis(
        beatmap=beatmap, shots=shots, style_pack=style_pack
    )
    all_decisions: list[NeuroSymbolicDecision] = []
    by_shot: dict[str, list[NeuralProposal]] = {}
    for p in proposals:
        sid = str(p.payload.get("shot_id") or "")
        by_shot.setdefault(sid, []).append(p)

    energy_by_section = {s.name: s.energy for s in beatmap.sections}
    for sid, props in by_shot.items():
        shot = next((s for s in shots if s.id == sid), None)
        if shot is None:
            continue
        # Prefer on-disk state; else build from in-memory shot
        if (root / "shots" / f"{sid}.json").exists():
            state = load_symbolic_state_for_shot(
                root,
                sid,
                style_pack=style_pack,
                section_energy=energy_by_section.get(shot.section),
            )
        else:
            from mvm.neurosymbolic.symbolic import build_symbolic_state

            state = build_symbolic_state(
                shot=shot,
                style_pack=style_pack,
                section_energy=energy_by_section.get(shot.section),
            )
        all_decisions.extend(
            decide(root, sid, props, state=state, persist=True)
        )
    return all_decisions


def summarize_decisions(decisions: list[NeuroSymbolicDecision]) -> dict[str, Any]:
    return {
        "total": len(decisions),
        "accepted": sum(
            1 for d in decisions if d.grounding.status == GroundingStatus.ACCEPTED
        ),
        "blocked": sum(
            1 for d in decisions if d.grounding.status == GroundingStatus.BLOCKED
        ),
        "needs_human": sum(
            1 for d in decisions if d.grounding.status == GroundingStatus.NEEDS_HUMAN
        ),
        "applied": False,
        "layers": {"neuro": "proposal", "symbolic": "grounding"},
    }


def _persist_decision(root: Path, decision: NeuroSymbolicDecision) -> Path:
    d = root / "neurosymbolic_decisions"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{decision.id}.json"
    path.write_text(
        json.dumps(decision.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return path


def _infer_shot_id(result: AssistantResult) -> str | None:
    for s in result.suggestions:
        sid = s.payload.get("shot_id")
        if sid:
            return str(sid)
    return None
