"""Individual narrow assistants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mvm.assistants.base import AssistantId, AssistantSuggestion, DomainFence
from mvm.assistants.runner import run_scoped_suggest


def _sug(
    assistant_id: AssistantId,
    *,
    domain: str,
    action: str,
    payload: dict[str, Any],
    reason: str,
    confidence: float,
    uncertainty: str = "",
) -> AssistantSuggestion:
    return AssistantSuggestion(
        assistant_id=assistant_id,
        domain=domain,
        action=action,
        payload=payload,
        reason=reason,
        confidence=confidence,
        uncertainty=uncertainty,
        visibly_labeled_generated=True,
        applied=False,
    )


def storyboard_assistant(
    root: Path,
    *,
    shot_id: str,
    panel_ids: list[str] | None = None,
    durations: list[int] | None = None,
) -> Any:
    assumptions = [
        "Shot has or will have storyboard panels",
        "Duration suggestions are animatic-timing only (not artwork rewrites)",
        "No timing-sheet / key-pose / sound mutations in this pass",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        out: list[AssistantSuggestion] = []
        panels = panel_ids or []
        durs = durations or []
        if panels and durs and len(panels) == len(durs):
            for pid, dur in zip(panels, durs):
                if dur < 8:
                    out.append(
                        _sug(
                            AssistantId.STORYBOARD,
                            domain="animatics",
                            action="suggest_panel_duration",
                            payload={"panel_id": pid, "duration_frames": 12},
                            reason=(
                                f"Panel {pid} at {dur}f may read as a flash cut; "
                                "consider ≥12f for readability."
                            ),
                            confidence=0.55,
                            uncertainty="Without animatic playback, readability is approximate.",
                        )
                    )
        if not out:
            out.append(
                _sug(
                    AssistantId.STORYBOARD,
                    domain="animatics",
                    action="suggest_review_order",
                    payload={"shot_id": shot_id},
                    reason="Confirm panel order matches emotional beat progression.",
                    confidence=0.4,
                    uncertainty="No panel timing data provided.",
                )
            )
        return out

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.STORYBOARD,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary=f"Storyboard assistant suggestions for {shot_id}",
        input_parameters={"shot_id": shot_id},
    )


def timing_assistant(
    root: Path,
    *,
    shot_id: str,
    timing_plan_id: str,
    mean_hold_frames: int | None = None,
) -> Any:
    assumptions = [
        f"Timing plan {timing_plan_id} exists for shot {shot_id}",
        "Suggestions do not enable allow_auto_smooth",
        "No key-pose content or storyboard artwork changes",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        out: list[AssistantSuggestion] = []
        hold = mean_hold_frames if mean_hold_frames is not None else 2
        if hold < 2:
            out.append(
                _sug(
                    AssistantId.TIMING,
                    domain="timing",
                    action="suggest_hold",
                    payload={
                        "timing_plan_id": timing_plan_id,
                        "duration_frames": 2,
                        "allow_auto_smooth": False,
                    },
                    reason=(
                        "Single-frame chatter may feel nervous; "
                        "a 2s hold often stabilizes the read."
                    ),
                    confidence=0.6,
                    uncertainty="Depends on beat density and exposure policy.",
                )
            )
        out.append(
            _sug(
                AssistantId.TIMING,
                domain="timing",
                action="suggest_spacing_mode",
                payload={
                    "timing_plan_id": timing_plan_id,
                    "mode": "slow_in",
                    "note": "explicit mode — not silent smooth",
                },
                reason="If accelerating into a contact, prefer explicit slow_in over auto-ease.",
                confidence=0.5,
                uncertainty="Requires authored key pair frames to apply later.",
            )
        )
        return out

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.TIMING,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary=f"Timing assistant suggestions for {timing_plan_id}",
        input_parameters={"shot_id": shot_id, "timing_plan_id": timing_plan_id},
    )


def pose_assistant(
    root: Path,
    *,
    shot_id: str,
    from_pose_id: str | None = None,
    to_pose_id: str | None = None,
    missing: list[str] | None = None,
) -> Any:
    assumptions = [
        "Key poses are authored extremes (not in-betweens)",
        "Will not rewrite approved key pose content",
        "Will not mutate timing sheets in this suggest pass",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        out: list[AssistantSuggestion] = []
        if missing:
            out.append(
                _sug(
                    AssistantId.POSE,
                    domain="key_poses",
                    action="surface_missing_for_inbetweens",
                    payload={"missing_information": list(missing)},
                    reason=(
                        "Insufficient pose/arc/spacing info for a useful "
                        "in-between suggestion."
                    ),
                    confidence=0.9,
                    uncertainty="No guessing — fill missing fields before generating slots.",
                )
            )
        elif from_pose_id and to_pose_id:
            out.append(
                _sug(
                    AssistantId.POSE,
                    domain="suggestions",
                    action="suggest_request_inbetweens",
                    payload={
                        "from_key_pose_id": from_pose_id,
                        "to_key_pose_id": to_pose_id,
                        "spacing_mode": "linear",
                        "preview_only": True,
                    },
                    reason="Pair is ready for a non-destructive in-between preview request.",
                    confidence=0.65,
                    uncertainty="Spacing mode still human-chosen (linear proposed, not forced).",
                )
            )
        else:
            out.append(
                _sug(
                    AssistantId.POSE,
                    domain="key_poses",
                    action="suggest_mark_extremes",
                    payload={"shot_id": shot_id},
                    reason="Mark anticipation and contact extremes before spacing work.",
                    confidence=0.45,
                    uncertainty="No pose ids supplied.",
                )
            )
        return out

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.POSE,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary=f"Pose assistant suggestions for {shot_id}",
        input_parameters={"shot_id": shot_id},
    )


def continuity_assistant(
    root: Path,
    *,
    sequence_id: str,
    focus_shot_id: str,
    explanations: list[str] | None = None,
) -> Any:
    assumptions = [
        f"Evaluating shot {focus_shot_id} with prev/next context in {sequence_id}",
        "Issues are informational — no auto-fix of shot JSON",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        out: list[AssistantSuggestion] = []
        for exp in explanations or [
            "Inspect preceding and following shots for framing/pacing continuity."
        ]:
            out.append(
                _sug(
                    AssistantId.CONTINUITY,
                    domain="sequence_evals",
                    action="flag_continuity_issue",
                    payload={"focus_shot_id": focus_shot_id, "explanation": exp},
                    reason=exp,
                    confidence=0.7 if explanations else 0.35,
                    uncertainty="Heuristic continuity — confirm in editorial review.",
                )
            )
        return out

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.CONTINUITY,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary=f"Continuity assistant for {focus_shot_id}",
        input_parameters={"shot_id": focus_shot_id, "sequence_id": sequence_id},
    )


def sound_assistant(
    root: Path,
    *,
    shot_id: str,
    sound_plan_id: str | None = None,
    unassigned_cue_ids: list[str] | None = None,
) -> Any:
    assumptions = [
        "Sound cues may be visible without producing motion",
        "Silence and non_reaction remain valid authored choices",
        "force_every_cue_to_motion stays false",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        out: list[AssistantSuggestion] = []
        for cid in unassigned_cue_ids or []:
            out.append(
                _sug(
                    AssistantId.SOUND,
                    domain="sound_plans",
                    action="suggest_motion_response",
                    payload={
                        "cue_id": cid,
                        "response": "non_reaction",
                        "applies_automatically": False,
                    },
                    reason=(
                        f"Cue {cid} is unassigned; default suggestion is non_reaction "
                        "(do not force visible movement)."
                    ),
                    confidence=0.5,
                    uncertainty="Animator may instead choose move/hold/silence explicitly.",
                )
            )
        if not out:
            out.append(
                _sug(
                    AssistantId.SOUND,
                    domain="sound_plans",
                    action="suggest_review_silence",
                    payload={"shot_id": shot_id, "sound_plan_id": sound_plan_id},
                    reason="Review silence regions — stillness is a valid performance choice.",
                    confidence=0.4,
                    uncertainty="No unassigned cues listed.",
                )
            )
        return out

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.SOUND,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary=f"Sound assistant suggestions for {shot_id}",
        input_parameters={"shot_id": shot_id, "sound_plan_id": sound_plan_id},
    )


def critique_assistant(
    root: Path,
    *,
    shot_id: str,
    revision_id: str,
    category_hints: list[str] | None = None,
) -> Any:
    assumptions = [
        f"Critique targets revision {revision_id} on {shot_id}",
        "No aggregate quality score will be produced",
        "Suggestions are critique items — not auto-applied fixes",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        cats = category_hints or ["timing", "continuity"]
        return [
            _sug(
                AssistantId.CRITIQUE,
                domain="critiques",
                action="suggest_critique_item",
                payload={
                    "category": cat,
                    "severity": "note",
                    "notes": f"Review {cat} on revision {revision_id}",
                },
                reason=(
                    f"Structured critique category '{cat}' deserves an explicit note "
                    "(not a single score)."
                ),
                confidence=0.5,
                uncertainty="Human must write the actual craft note.",
            )
            for cat in cats
        ]

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.CRITIQUE,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary=f"Critique assistant suggestions for {shot_id}",
        input_parameters={"shot_id": shot_id, "revision_id": revision_id},
    )


def provenance_assistant(
    root: Path,
    *,
    pending_provenance_ids: list[str] | None = None,
) -> Any:
    assumptions = [
        "Only provenance/revisions may be written at suggest time",
        "Will not mutate craft domains (timing, poses, storyboard, sound, critiques)",
    ]

    def build(fence: DomainFence) -> list[AssistantSuggestion]:
        out: list[AssistantSuggestion] = []
        for pid in pending_provenance_ids or []:
            out.append(
                _sug(
                    AssistantId.PROVENANCE,
                    domain="provenance",
                    action="suggest_accept_or_reject",
                    payload={"provenance_id": pid},
                    reason=(
                        f"Provenance {pid} is still pending — accept/reject to keep "
                        "the ledger current."
                    ),
                    confidence=0.8,
                    uncertainty="Requires human judgment on the underlying change.",
                )
            )
        if not out:
            out.append(
                _sug(
                    AssistantId.PROVENANCE,
                    domain="provenance",
                    action="suggest_export_bundle",
                    payload={},
                    reason="Export a provenance bundle so revisions remain inspectable/restorable.",
                    confidence=0.6,
                    uncertainty="No pending ids supplied.",
                )
            )
        return out

    return run_scoped_suggest(
        root,
        assistant_id=AssistantId.PROVENANCE,
        input_assumptions=assumptions,
        build_suggestions=build,
        summary="Provenance assistant suggestions",
        input_parameters={"pending": pending_provenance_ids or []},
    )


def attempt_forbidden_write(assistant_id: AssistantId, domain: str) -> None:
    """Test/helper: simulate a cross-domain write attempt under the fence."""
    fence = DomainFence(assistant_id=assistant_id)
    fence.check_write(domain, path=f"{domain}/illegal.json")
