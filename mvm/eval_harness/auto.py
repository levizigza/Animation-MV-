"""Automatic observations for eval scenes — signals, not grades or scores."""

from __future__ import annotations

from typing import Any

from mvm.schemas.eval_harness import (
    AUTO_EVAL_DIMENSIONS,
    AutoEvalPass,
    DimensionObservation,
    EvalDimension,
    EvalSceneFixture,
    ObservationKind,
)


def _obs(
    dimension: EvalDimension,
    kind: ObservationKind,
    message: str,
    *,
    confidence: float,
    uncertainty: str = "",
    evidence: dict[str, Any] | None = None,
) -> DimensionObservation:
    return DimensionObservation(
        dimension=dimension,
        kind=kind,
        message=message,
        confidence=confidence,
        uncertainty=uncertainty,
        evidence=evidence or {},
        source="automatic",
    )


def evaluate_scene_automatic(scene: EvalSceneFixture) -> AutoEvalPass:
    """Heuristic observations per dimension. Never fills human preference."""
    observations: list[DimensionObservation] = []

    intent = scene.intent or {}
    purpose = (intent.get("purpose") or "").strip()
    emotional = (intent.get("emotional_beat") or "").strip()
    if purpose and emotional:
        observations.append(
            _obs(
                EvalDimension.INTENT_CLARITY,
                ObservationKind.OK,
                f"Intent states purpose and emotional beat for '{scene.title}'.",
                confidence=0.75,
                uncertainty="Clarity still needs human acting judgment.",
                evidence={"purpose": purpose, "emotional_beat": emotional},
            )
        )
    elif purpose:
        observations.append(
            _obs(
                EvalDimension.INTENT_CLARITY,
                ObservationKind.GAP,
                "Purpose present but emotional beat is thin or missing.",
                confidence=0.7,
                uncertainty="Auto cannot invent subtext.",
                evidence={"purpose": purpose},
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.INTENT_CLARITY,
                ObservationKind.RISK,
                "No explicit purpose — detailed craft should not proceed.",
                confidence=0.9,
            )
        )

    poses = scene.key_poses or []
    labeled = [p for p in poses if (p.get("label") or p.get("action") or "").strip()]
    if len(labeled) >= 2:
        observations.append(
            _obs(
                EvalDimension.POSE_READABILITY,
                ObservationKind.INFO,
                f"{len(labeled)} labeled key poses available for silhouette/acting read.",
                confidence=0.55,
                uncertainty="Readability requires visual review — labels ≠ readable drawing.",
                evidence={"pose_ids": [p.get("id") for p in labeled]},
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.POSE_READABILITY,
                ObservationKind.GAP,
                "Fewer than two labeled keys — hard to judge pose readability automatically.",
                confidence=0.8,
            )
        )

    timing = scene.timing or {}
    holds = timing.get("holds") or []
    auto_smooth = timing.get("allow_auto_smooth", False)
    if auto_smooth:
        observations.append(
            _obs(
                EvalDimension.TIMING,
                ObservationKind.RISK,
                "allow_auto_smooth is true — craft engine forbids silent smoothing.",
                confidence=0.95,
            )
        )
    elif holds:
        observations.append(
            _obs(
                EvalDimension.TIMING,
                ObservationKind.OK,
                f"{len(holds)} authored hold(s) present; auto-smooth remains false.",
                confidence=0.7,
                evidence={"holds": holds, "allow_auto_smooth": False},
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.TIMING,
                ObservationKind.INFO,
                "No holds listed — may be fine for continuous action; human must judge.",
                confidence=0.4,
                uncertainty="Absence of holds is not automatically a failure.",
            )
        )

    spacing = timing.get("spacing_mode")
    if spacing:
        observations.append(
            _obs(
                EvalDimension.SPACING,
                ObservationKind.OK,
                f"Explicit spacing mode '{spacing}' recorded (not silent ease).",
                confidence=0.75,
                evidence={"spacing_mode": spacing},
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.SPACING,
                ObservationKind.GAP,
                "No explicit spacing mode on the fixture timing block.",
                confidence=0.65,
            )
        )

    total_hold = sum(int(h.get("duration") or 0) for h in holds)
    end_f = int(timing.get("end_frame") or 0)
    start_f = int(timing.get("start_frame") or 1)
    span = max(end_f - start_f + 1, 1)
    hold_ratio = total_hold / span
    if scene.kind.value == "quiet":
        if hold_ratio >= 0.35:
            observations.append(
                _obs(
                    EvalDimension.STILLNESS,
                    ObservationKind.OK,
                    f"Quiet scene hold ratio ~{hold_ratio:.2f} supports authored stillness.",
                    confidence=0.6,
                    uncertainty="Ratio ≠ emotional subtext quality.",
                    evidence={"hold_ratio": hold_ratio, "total_hold_frames": total_hold},
                )
            )
        else:
            observations.append(
                _obs(
                    EvalDimension.STILLNESS,
                    ObservationKind.GAP,
                    f"Quiet scene hold ratio ~{hold_ratio:.2f} looks busy for the brief.",
                    confidence=0.55,
                    uncertainty="Human may still prefer sparse motion.",
                    evidence={"hold_ratio": hold_ratio},
                )
            )
    else:
        observations.append(
            _obs(
                EvalDimension.STILLNESS,
                ObservationKind.INFO,
                f"Hold ratio ~{hold_ratio:.2f} — stillness judged relative to scene kind.",
                confidence=0.45,
                uncertainty="Dialogue/action may need different stillness budgets.",
                evidence={"hold_ratio": hold_ratio, "scene_kind": scene.kind.value},
            )
        )

    neighbors = scene.sequence_neighbors or {}
    if neighbors.get("previous_shot_id") and neighbors.get("next_shot_id"):
        observations.append(
            _obs(
                EvalDimension.SEQUENCE_CONTEXT,
                ObservationKind.OK,
                "Prev/next shot context noted for continuity review.",
                confidence=0.7,
                evidence=neighbors,
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.SEQUENCE_CONTEXT,
                ObservationKind.GAP,
                "Missing previous or next shot context.",
                confidence=0.75,
            )
        )

    cues = scene.sound_cues or []
    responses = {c.get("motion_response") for c in cues}
    if any(c.get("kind") == "silence" for c in cues) or "non_reaction" in responses:
        observations.append(
            _obs(
                EvalDimension.SOUND_RELATIONSHIP,
                ObservationKind.OK,
                "Silence and/or non_reaction present — motion is not forced for every cue.",
                confidence=0.8,
                evidence={"cue_count": len(cues), "responses": sorted(str(r) for r in responses)},
            )
        )
    elif cues:
        observations.append(
            _obs(
                EvalDimension.SOUND_RELATIONSHIP,
                ObservationKind.INFO,
                "Cues exist but no silence/non_reaction — verify force_every_cue_to_motion stays false.",
                confidence=0.55,
                evidence={"cue_count": len(cues)},
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.SOUND_RELATIONSHIP,
                ObservationKind.GAP,
                "No sound cues on fixture — relationship cannot be assessed automatically.",
                confidence=0.7,
            )
        )

    if (scene.revision_notes or "").strip():
        observations.append(
            _obs(
                EvalDimension.REVISION_QUALITY,
                ObservationKind.INFO,
                "Revision notes present; inspectability depends on provenance linkage at seed time.",
                confidence=0.5,
                uncertainty="Auto cannot judge whether the revision improved craft.",
                evidence={"revision_notes": scene.revision_notes},
            )
        )
    else:
        observations.append(
            _obs(
                EvalDimension.REVISION_QUALITY,
                ObservationKind.GAP,
                "No revision notes — hard to compare passes without human form.",
                confidence=0.7,
            )
        )

    # Ensure every auto dimension has at least one observation
    covered = {o.dimension for o in observations}
    for dim in AUTO_EVAL_DIMENSIONS:
        if dim not in covered:
            observations.append(
                _obs(
                    dim,
                    ObservationKind.INFO,
                    f"No specific automatic signal for {dim.value}; human form required.",
                    confidence=0.3,
                    uncertainty="Missing auto coverage is expected for some craft aspects.",
                )
            )

    return AutoEvalPass(
        scene_id=scene.id,
        observations=observations,
        substitutes_for_human_review=False,
        has_aggregate_quality_score=False,
        quality_score=None,
    )
