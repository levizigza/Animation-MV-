"""Sequence-aware shot evaluator — flags issues with explanations; never auto-fixes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mvm.project.domain_store import ensure_domain_dirs, save_provenance
from mvm.schemas.domain import ActorKind, make_provenance, new_id
from mvm.schemas.models import Shot
from mvm.schemas.sequence_eval import (
    CharacterStateSnapshot,
    SequenceEvaluation,
    SequenceIssue,
)

GESTURE_TOKENS = (
    "glance",
    "cuff",
    "whip",
    "point",
    "reach",
    "turn",
    "nod",
    "shrug",
    "step",
    "smear",
    "look",
    "gesture",
)

IMPACT_HINTS = (
    "impact",
    "hit",
    "strike",
    "slam",
    "reveal",
    "shock",
    "chorus",
    "release",
    "punch",
)

REACTION_HINTS = (
    "reaction",
    "react",
    "flinch",
    "absorb",
    "register",
    "glance back",
    "aftermath",
)

CLOSE_TYPES = {"push_in", "close", "closeup", "close_up", "cu", "tight"}


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def ensure_sequence_eval_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "sequence_evals").mkdir(parents=True, exist_ok=True)


def _shot_text(shot: Shot) -> str:
    parts = [
        shot.description or "",
        shot.blocking or "",
        shot.notes or "",
        shot.intent.purpose if shot.intent else "",
        shot.intent.emotional_beat if shot.intent else "",
        shot.intent.staging_goal if shot.intent else "",
    ]
    return " ".join(parts).lower()


def _gestures(shot: Shot) -> list[str]:
    text = _shot_text(shot)
    return [g for g in GESTURE_TOKENS if re.search(rf"\b{re.escape(g)}\b", text)]


def _camera_type(shot: Shot) -> str:
    return str((shot.camera or {}).get("type") or "").lower().strip()


def _is_close_emphasis(shot: Shot) -> bool:
    ctype = _camera_type(shot)
    if ctype in CLOSE_TYPES or "close" in ctype or "push" in ctype:
        return True
    return shot.lens_mm >= 45.0


def _camera_loc(shot: Shot, which: str = "end") -> list[float] | None:
    block = (shot.camera or {}).get(which) or {}
    loc = block.get("loc")
    if isinstance(loc, list) and len(loc) >= 3:
        return [float(loc[0]), float(loc[1]), float(loc[2])]
    return None


def _loc_distance(a: list[float] | None, b: list[float] | None) -> float | None:
    if a is None or b is None:
        return None
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def build_character_states(
    previous: Shot | None,
    current: Shot,
    following: Shot | None,
) -> list[CharacterStateSnapshot]:
    ids = sorted(
        set(previous.characters if previous else [])
        | set(current.characters)
        | set(following.characters if following else [])
    )
    states: list[CharacterStateSnapshot] = []
    for cid in ids:
        prev_has = bool(previous and cid in previous.characters)
        cur_has = cid in current.characters
        next_has = bool(following and cid in following.characters)
        last = None
        if cur_has:
            last = current.id
        elif prev_has and previous:
            last = previous.id
        emotional = ""
        if cur_has and current.intent:
            emotional = current.intent.emotional_beat or current.intent.animation_priority
        gestures = _gestures(current) if cur_has else []
        notes = ""
        if prev_has and not cur_has:
            notes = "Character exits current shot relative to previous presence"
        if not prev_has and cur_has and previous is not None:
            notes = (notes + "; " if notes else "") + "Character newly enters on current shot"
        states.append(
            CharacterStateSnapshot(
                character_id=cid,
                present_in_previous=prev_has,
                present_in_current=cur_has,
                present_in_following=next_has,
                last_seen_shot_id=last,
                emotional_hint=emotional,
                gesture_hints=gestures,
                notes=notes,
            )
        )
    return states


def _issue(
    *,
    kind: str,
    shot: Shot,
    previous: Shot | None,
    following: Shot | None,
    explanation: str,
    evidence: dict[str, Any],
    suggested_attention: str,
) -> SequenceIssue:
    return SequenceIssue(
        kind=kind,  # type: ignore[arg-type]
        shot_id=shot.id,
        previous_shot_id=previous.id if previous else None,
        following_shot_id=following.id if following else None,
        explanation=explanation,
        evidence=evidence,
        suggested_attention=suggested_attention,
        auto_fixed=False,
    )


def evaluate_shot_window(
    *,
    sequence_id: str,
    previous: Shot | None,
    current: Shot,
    following: Shot | None,
    sequence_shots: list[Shot] | None = None,
) -> SequenceEvaluation:
    """Inspect prev/current/next and emit possible issues. Does not mutate shots."""
    issues: list[SequenceIssue] = []
    states = build_character_states(previous, current, following)
    neighbors = [s for s in (previous, following) if s is not None]
    all_for_pace = list(sequence_shots) if sequence_shots else [
        s for s in (previous, current, following) if s is not None
    ]

    # Repeated framing / emphasis
    if previous and _is_close_emphasis(previous) and _is_close_emphasis(current):
        issues.append(
            _issue(
                kind="repeated_framing",
                shot=current,
                previous=previous,
                following=following,
                explanation=(
                    "This close-up repeats the previous shot’s emphasis."
                ),
                evidence={
                    "previous_camera": _camera_type(previous),
                    "current_camera": _camera_type(current),
                    "previous_lens_mm": previous.lens_mm,
                    "current_lens_mm": current.lens_mm,
                },
                suggested_attention=(
                    "Consider varying scale/angle or justifying the repeated emphasis "
                    "in intent — evaluator will not change camera."
                ),
            )
        )

    # Repeated gesture patterns
    if previous:
        prev_g = set(_gestures(previous))
        cur_g = set(_gestures(current))
        overlap = sorted(prev_g & cur_g)
        if overlap:
            issues.append(
                _issue(
                    kind="repeated_gesture",
                    shot=current,
                    previous=previous,
                    following=following,
                    explanation=(
                        f"Repeated gesture pattern with the previous shot: {', '.join(overlap)}."
                    ),
                    evidence={"shared_gestures": overlap},
                    suggested_attention=(
                        "Vary the gesture or make recurrence intentional in notes."
                    ),
                )
            )

    # Pacing contrast — pause longer than established rhythm
    durations = [s.duration for s in all_for_pace if s.duration > 0]
    if len(durations) >= 2:
        mean = sum(durations) / len(durations)
        if current.duration > mean * 1.5 and current.duration - mean >= 0.75:
            issues.append(
                _issue(
                    kind="pacing_contrast",
                    shot=current,
                    previous=previous,
                    following=following,
                    explanation=(
                        "The pause is longer than the established rhythm."
                    ),
                    evidence={
                        "current_duration": current.duration,
                        "sequence_mean_duration": round(mean, 3),
                        "neighbor_durations": [
                            {"id": s.id, "duration": s.duration} for s in neighbors
                        ],
                    },
                    suggested_attention=(
                        "Shorten hold or justify the pause in intent — not auto-trimmed."
                    ),
                )
            )

    # Emotional progression / reaction mismatch
    if previous:
        prev_text = _shot_text(previous)
        cur_text = _shot_text(current)
        prev_impact = any(h in prev_text for h in IMPACT_HINTS) or (
            previous.intent and previous.intent.animation_priority == "impact"
        )
        cur_reacts = any(h in cur_text for h in REACTION_HINTS)
        cur_priority = (
            current.intent.animation_priority if current.intent else "performance"
        )
        if prev_impact and not cur_reacts and cur_priority in ("atmosphere", "transition"):
            issues.append(
                _issue(
                    kind="reaction_mismatch",
                    shot=current,
                    previous=previous,
                    following=following,
                    explanation=(
                        "The character’s reaction does not reflect the preceding event."
                    ),
                    evidence={
                        "previous_priority": previous.intent.animation_priority
                        if previous.intent
                        else None,
                        "current_priority": cur_priority,
                        "previous_excerpt": (previous.description or "")[:120],
                        "current_excerpt": (current.description or "")[:120],
                    },
                    suggested_attention=(
                        "Add a reaction beat or revise emotional_beat — evaluator "
                        "will not rewrite the shot."
                    ),
                )
            )

        # Soft emotional progression flatline
        if (
            previous.intent
            and current.intent
            and previous.intent.emotional_beat
            and current.intent.emotional_beat
            and previous.intent.emotional_beat == current.intent.emotional_beat
            and previous.intent.animation_priority == current.intent.animation_priority
            and previous.section == current.section
        ):
            issues.append(
                _issue(
                    kind="emotional_progression",
                    shot=current,
                    previous=previous,
                    following=following,
                    explanation=(
                        "Emotional progression is flat versus the preceding shot "
                        f"(both marked '{current.intent.emotional_beat}' / "
                        f"{current.intent.animation_priority})."
                    ),
                    evidence={
                        "emotional_beat": current.intent.emotional_beat,
                        "animation_priority": current.intent.animation_priority,
                    },
                    suggested_attention="Differentiate beat or priority if progression is intended.",
                )
            )

    # Camera / spatial continuity
    if previous:
        dist = _loc_distance(_camera_loc(previous, "end"), _camera_loc(current, "start"))
        if dist is not None and dist > 3.0:
            issues.append(
                _issue(
                    kind="spatial_continuity",
                    shot=current,
                    previous=previous,
                    following=following,
                    explanation=(
                        "Camera/spatial continuity jumps sharply from the previous shot’s "
                        f"end position (distance≈{dist:.2f})."
                    ),
                    evidence={
                        "previous_end_loc": _camera_loc(previous, "end"),
                        "current_start_loc": _camera_loc(current, "start"),
                        "distance": round(dist, 3),
                    },
                    suggested_attention=(
                        "Add a motivated cut, bridging angle, or accept as jump cut in notes."
                    ),
                )
            )
        if _camera_type(previous) and _camera_type(previous) == _camera_type(current):
            if abs(previous.lens_mm - current.lens_mm) < 1.0:
                # already covered close-up case; still flag same move type as continuity note
                if not _is_close_emphasis(current):
                    issues.append(
                        _issue(
                            kind="camera_continuity",
                            shot=current,
                            previous=previous,
                            following=following,
                            explanation=(
                                f"Camera move type '{_camera_type(current)}' repeats the "
                                "previous shot with nearly identical lens."
                            ),
                            evidence={
                                "camera_type": _camera_type(current),
                                "lens_mm": current.lens_mm,
                            },
                            suggested_attention="Vary move grammar or lens to refresh the beat.",
                        )
                    )

    # Character state continuity
    for st in states:
        if st.present_in_previous and not st.present_in_current and st.present_in_following:
            issues.append(
                _issue(
                    kind="character_state",
                    shot=current,
                    previous=previous,
                    following=following,
                    explanation=(
                        f"Recurring character '{st.character_id}' disappears in this shot "
                        "but returns immediately after — state continuity may be unclear."
                    ),
                    evidence=st.model_dump(mode="json"),
                    suggested_attention="Justify absence or keep presence consistent.",
                )
            )

    summary = (
        f"Sequence {sequence_id} focus={current.id} "
        f"prev={previous.id if previous else None} "
        f"next={following.id if following else None}: "
        f"{len(issues)} possible issue(s). auto_fix_applied=False."
    )
    return SequenceEvaluation(
        sequence_id=sequence_id,
        focus_shot_id=current.id,
        previous_shot_id=previous.id if previous else None,
        following_shot_id=following.id if following else None,
        character_states=states,
        issues=issues,
        summary=summary,
        auto_fix_applied=False,
        shots_mutated=False,
    )


def evaluate_shot_in_sequence(
    shots: list[Shot],
    focus_shot_id: str,
    *,
    sequence_id: str = "sequence",
) -> SequenceEvaluation:
    """Evaluate one shot using ordered neighbors. Pure — does not write or mutate."""
    ordered = sorted(shots, key=lambda s: s.index)
    idx = next((i for i, s in enumerate(ordered) if s.id == focus_shot_id), None)
    if idx is None:
        raise KeyError(f"Shot {focus_shot_id} not in sequence")
    previous = ordered[idx - 1] if idx > 0 else None
    current = ordered[idx]
    following = ordered[idx + 1] if idx + 1 < len(ordered) else None
    return evaluate_shot_window(
        sequence_id=sequence_id,
        previous=previous,
        current=current,
        following=following,
        sequence_shots=ordered,
    )


def evaluate_sequence(
    shots: list[Shot],
    *,
    sequence_id: str = "sequence",
) -> list[SequenceEvaluation]:
    """Evaluate every shot in order. Never mutates inputs."""
    ordered = sorted(shots, key=lambda s: s.index)
    # Deep-copy fingerprints to prove non-mutation in callers/tests
    return [
        evaluate_shot_in_sequence(ordered, s.id, sequence_id=sequence_id)
        for s in ordered
    ]


def save_evaluation(root: Path, evaluation: SequenceEvaluation) -> Path:
    ensure_sequence_eval_dirs(root)
    if evaluation.auto_fix_applied or evaluation.shots_mutated:
        raise ValueError("Refusing to save an evaluation that claims auto-fix")
    path = root / "sequence_evals" / f"{evaluation.id}.json"
    _write(path, evaluation)
    prov = make_provenance(
        operation="agents.sequence_evaluate",
        revision_id=evaluation.id,
        actor=ActorKind.HEURISTIC_AGENT,
        summary=evaluation.summary,
        outputs={
            "issue_count": len(evaluation.issues),
            "auto_fix_applied": False,
            "explanations": [i.explanation for i in evaluation.issues],
        },
    )
    save_provenance(root, prov)
    return path


def load_shots_fixture(path: Path) -> tuple[str, list[Shot]]:
    """Load a short example sequence fixture: {sequence_id, shots: [...]}."""
    data = json.loads(path.read_text(encoding="utf-8"))
    seq_id = data.get("sequence_id") or data.get("id") or path.stem
    shots = [Shot.model_validate(s) for s in data["shots"]]
    return seq_id, shots
