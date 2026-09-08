"""Notation workflow: explicit marks → ambiguity choice → draft MotionRequest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.domain import ActorKind, make_provenance, new_id
from mvm.schemas.notation import (
    AmbiguityReport,
    IntentNotation,
    MotionRequest,
    NotationInterpretation,
    NotationKind,
    NotationMark,
)


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_notation_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "notation").mkdir(parents=True, exist_ok=True)
    (root / "motion_requests").mkdir(parents=True, exist_ok=True)


def save_notation(root: Path, notation: IntentNotation) -> Path:
    ensure_notation_dirs(root)
    if notation.converts_to_final_animation is not False:
        raise ValueError("Refusing to save notation that claims final conversion")
    path = root / "notation" / f"{notation.id}.json"
    _write(path, notation)
    return path


def load_notation(root: Path, notation_id: str) -> IntentNotation:
    return IntentNotation.model_validate(_read(root / "notation" / f"{notation_id}.json"))


def save_motion_request(root: Path, req: MotionRequest) -> Path:
    ensure_notation_dirs(root)
    if req.applied_as_final is not False:
        raise ValueError("Refusing to save MotionRequest marked as final animation")
    path = root / "motion_requests" / f"{req.id}.json"
    _write(path, req)
    return path


def load_motion_request(root: Path, request_id: str) -> MotionRequest:
    return MotionRequest.model_validate(
        _read(root / "motion_requests" / f"{request_id}.json")
    )


def create_notation(
    root: Path,
    *,
    shot_id: str,
    marks: list[NotationMark] | list[dict[str, Any]],
    freehand_ref: str | None = None,
) -> IntentNotation:
    """Create explicit notation. Freehand ref is stored as a link only."""
    ensure_notation_dirs(root)
    parsed: list[NotationMark] = []
    for m in marks:
        if isinstance(m, NotationMark):
            parsed.append(m)
        else:
            parsed.append(NotationMark.model_validate(m))

    if not parsed and freehand_ref:
        # Freehand alone is not enough — surface as draft with no silent bake
        notation = IntentNotation(
            id=new_id("notn"),
            shot_id=shot_id,
            marks=[],
            freehand_ref=freehand_ref,
            status="draft",
            converts_to_final_animation=False,
        )
        rev, prov = attribute_suggestion(
            operation="human.notation_create_freehand_only",
            target_type="shot",
            target_id=shot_id,
            snapshot=notation.model_dump(mode="json"),
            summary=(
                "Freehand notation linked but no explicit marks yet. "
                "Will not convert to final animation."
            ),
        )
        notation.revision_id = rev.id
        save_notation(root, notation)
        save_revision(root, rev)
        save_provenance(root, prov)
        return notation

    if not parsed:
        raise ValueError("create_notation requires at least one mark or a freehand_ref")

    notation = IntentNotation(
        id=new_id("notn"),
        shot_id=shot_id,
        marks=parsed,
        freehand_ref=freehand_ref,
        status="draft",
        converts_to_final_animation=False,
    )
    rev, prov = attribute_suggestion(
        operation="human.notation_create",
        target_type="shot",
        target_id=shot_id,
        snapshot=notation.model_dump(mode="json"),
        summary=f"Created notation {notation.id} with {len(parsed)} explicit marks",
        outputs={"mark_kinds": [m.kind.value for m in parsed]},
    )
    notation.revision_id = rev.id
    save_notation(root, notation)
    save_revision(root, rev)
    save_provenance(root, prov)
    return notation


def _marks_by_kind(notation: IntentNotation) -> dict[NotationKind, list[NotationMark]]:
    out: dict[NotationKind, list[NotationMark]] = {}
    for m in notation.marks:
        out.setdefault(m.kind, []).append(m)
    return out


def _first_value(
    by_kind: dict[NotationKind, list[NotationMark]], kind: NotationKind
) -> str | None:
    marks = by_kind.get(kind) or []
    return marks[0].value if marks else None


def detect_ambiguities(notation: IntentNotation) -> list[str]:
    """Return human-readable ambiguity statements (empty if unambiguous enough)."""
    ambiguities: list[str] = []
    by_kind = _marks_by_kind(notation)

    if not notation.marks:
        ambiguities.append(
            "No explicit marks — freehand alone cannot be translated "
            "(add motion_path, objects, force, etc.)"
        )
        return ambiguities

    has_force = NotationKind.FORCE_DIRECTION in by_kind
    has_source = NotationKind.SOURCE_OBJECT in by_kind
    has_target = NotationKind.TARGET_OBJECT in by_kind
    has_path = NotationKind.MOTION_PATH in by_kind
    has_contact = NotationKind.CONTACT_POINT in by_kind
    has_still = NotationKind.INTENDED_STILLNESS in by_kind
    has_ant = NotationKind.ANTICIPATION in by_kind
    has_over = NotationKind.OVERSHOOT in by_kind
    has_settle = NotationKind.SETTLE in by_kind
    has_timing = NotationKind.TIMING_EMPHASIS in by_kind

    if has_force and not (has_source or has_target):
        ambiguities.append(
            "force_direction present without source_object or target_object "
            "(who applies / receives the force?)"
        )
    if has_path and not has_timing:
        ambiguities.append(
            "motion_path without timing_emphasis "
            "(accent on start, middle, impact, or settle?)"
        )
    if has_contact and not has_target:
        ambiguities.append(
            "contact_point without target_object (what is being contacted?)"
        )
    if has_still and (has_force or has_path):
        ambiguities.append(
            "intended_stillness conflicts with force_direction/motion_path "
            "(hold then move, move then hold, or concurrent regions?)"
        )
    if has_ant and not (has_over or has_settle or has_still):
        ambiguities.append(
            "anticipation without overshoot, settle, or intended_stillness "
            "(how does the action resolve?)"
        )
    if has_over and has_settle and not has_timing:
        ambiguities.append(
            "overshoot and settle both present without timing_emphasis "
            "(which beat owns the emphasis?)"
        )
    if len(by_kind.get(NotationKind.MOTION_PATH, [])) > 1:
        ambiguities.append(
            "multiple motion_path marks — unclear whether sequential or alternative paths"
        )
    if has_source and has_target and not (has_path or has_force or has_contact):
        ambiguities.append(
            "source_object and target_object without motion_path, force_direction, "
            "or contact_point (how do they relate?)"
        )
    return ambiguities


def _preview_from_marks(
    notation: IntentNotation,
    *,
    assumptions: list[str],
    overrides: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    by_kind = _marks_by_kind(notation)
    overrides = overrides or {}
    fields = {
        "source_object": _first_value(by_kind, NotationKind.SOURCE_OBJECT),
        "target_object": _first_value(by_kind, NotationKind.TARGET_OBJECT),
        "motion_path": _first_value(by_kind, NotationKind.MOTION_PATH),
        "force_direction": _first_value(by_kind, NotationKind.FORCE_DIRECTION),
        "timing_emphasis": _first_value(by_kind, NotationKind.TIMING_EMPHASIS),
        "contact_point": _first_value(by_kind, NotationKind.CONTACT_POINT),
        "anticipation": _first_value(by_kind, NotationKind.ANTICIPATION),
        "overshoot": _first_value(by_kind, NotationKind.OVERSHOOT),
        "settle": _first_value(by_kind, NotationKind.SETTLE),
        "intended_stillness": _first_value(by_kind, NotationKind.INTENDED_STILLNESS),
    }
    for k, v in overrides.items():
        fields[k] = v
    frames = [m.frame for m in notation.marks if m.frame is not None]
    end_frames = [m.end_frame for m in notation.marks if m.end_frame is not None]
    return {
        **fields,
        "start_frame": min(frames) if frames else None,
        "end_frame": max(end_frames + frames) if (end_frames or frames) else None,
        "assumptions": assumptions,
        "applied_as_final": False,
    }


def build_interpretations(notation: IntentNotation) -> list[NotationInterpretation]:
    """Produce two or three explicit readings when notation is ambiguous."""
    ambiguities = detect_ambiguities(notation)
    by_kind = _marks_by_kind(notation)
    interpretations: list[NotationInterpretation] = []

    if not ambiguities:
        return [
            NotationInterpretation(
                id=new_id("nint"),
                label="literal",
                summary="Use marks as written; no extra assumptions.",
                assumptions=[],
                motion_preview=_preview_from_marks(notation, assumptions=[]),
            )
        ]

    # Interpretation A — resolve toward impact/contact
    a_assumes = [
        "Emphasize contact/impact as the timing peak" if NotationKind.TIMING_EMPHASIS not in by_kind else "",
        "Treat force as acting from source toward target"
        if NotationKind.FORCE_DIRECTION in by_kind
        else "Infer force along motion_path toward target",
        "Resolve anticipation into overshoot then settle"
        if NotationKind.ANTICIPATION in by_kind
        else "",
    ]
    a_assumes = [x for x in a_assumes if x]
    a_over = {
        "timing_emphasis": _first_value(by_kind, NotationKind.TIMING_EMPHASIS)
        or "impact",
        "overshoot": _first_value(by_kind, NotationKind.OVERSHOOT) or "brief_overshoot",
        "settle": _first_value(by_kind, NotationKind.SETTLE) or "settle_after_contact",
    }
    if NotationKind.INTENDED_STILLNESS in by_kind and (
        NotationKind.FORCE_DIRECTION in by_kind or NotationKind.MOTION_PATH in by_kind
    ):
        a_assumes.append("Stillness after settle (motion then hold)")
        a_over["intended_stillness"] = (
            _first_value(by_kind, NotationKind.INTENDED_STILLNESS) or "hold_after_settle"
        )
    interpretations.append(
        NotationInterpretation(
            id=new_id("nint"),
            label="impact_resolve",
            summary="Read as action into contact with impact emphasis, then settle.",
            assumptions=a_assumes,
            motion_preview=_preview_from_marks(
                notation, assumptions=a_assumes, overrides=a_over
            ),
        )
    )

    # Interpretation B — resolve toward held performance / stillness
    b_assumes = [
        "Emphasize held pose / stillness as the read",
        "Minimize travel; motion_path is a small lead-in only"
        if NotationKind.MOTION_PATH in by_kind
        else "No large travel — pose change is local",
    ]
    if NotationKind.ANTICIPATION in by_kind:
        b_assumes.append("Anticipation into stillness (no overshoot)")
    b_over: dict[str, str | None] = {
        "timing_emphasis": _first_value(by_kind, NotationKind.TIMING_EMPHASIS)
        or "settle",
        "overshoot": _first_value(by_kind, NotationKind.OVERSHOOT) or "none",
        "settle": _first_value(by_kind, NotationKind.SETTLE) or "soft_settle",
        "intended_stillness": _first_value(by_kind, NotationKind.INTENDED_STILLNESS)
        or "held_read",
    }
    interpretations.append(
        NotationInterpretation(
            id=new_id("nint"),
            label="stillness_resolve",
            summary="Read as anticipation into intended stillness; little or no overshoot.",
            assumptions=b_assumes,
            motion_preview=_preview_from_marks(
                notation, assumptions=b_assumes, overrides=b_over
            ),
        )
    )

    # Interpretation C — when path/force or multi-path ambiguity needs a third reading
    if (
        len(by_kind.get(NotationKind.MOTION_PATH, [])) > 1
        or (
            NotationKind.SOURCE_OBJECT in by_kind
            and NotationKind.TARGET_OBJECT in by_kind
            and NotationKind.FORCE_DIRECTION not in by_kind
        )
        or (
            NotationKind.FORCE_DIRECTION in by_kind
            and not (
                NotationKind.SOURCE_OBJECT in by_kind
                or NotationKind.TARGET_OBJECT in by_kind
            )
        )
    ):
        c_assumes = [
            "Prefer first motion_path mark as primary; treat others as alternatives unused",
            "Force direction is environmental (camera/world), not object-local",
        ]
        paths = by_kind.get(NotationKind.MOTION_PATH) or []
        c_over = {
            "motion_path": paths[0].value if paths else None,
            "force_direction": _first_value(by_kind, NotationKind.FORCE_DIRECTION)
            or "world_down",
            "timing_emphasis": _first_value(by_kind, NotationKind.TIMING_EMPHASIS)
            or "middle",
            "source_object": _first_value(by_kind, NotationKind.SOURCE_OBJECT)
            or "environment",
            "target_object": _first_value(by_kind, NotationKind.TARGET_OBJECT)
            or "character",
        }
        interpretations.append(
            NotationInterpretation(
                id=new_id("nint"),
                label="environment_force",
                summary="Read force/path as world-space with first path primary.",
                assumptions=c_assumes,
                motion_preview=_preview_from_marks(
                    notation, assumptions=c_assumes, overrides=c_over
                ),
            )
        )

    return interpretations[:3]


def analyze_notation(root: Path, notation_id: str) -> dict[str, Any]:
    """Show ambiguities and 2–3 interpretations; does not create a MotionRequest."""
    notation = load_notation(root, notation_id)
    ambiguities = detect_ambiguities(notation)
    interpretations = build_interpretations(notation)

    if ambiguities:
        notation = notation.model_copy(deep=True)
        notation.status = "ambiguous"
        save_notation(root, notation)
        report = AmbiguityReport(
            notation_id=notation.id,
            shot_id=notation.shot_id,
            ambiguities=ambiguities,
            interpretations=interpretations,
            awaiting_choice=True,
        )
        # Persist report beside notation for the choose step
        _write(root / "notation" / f"{notation.id}_ambiguity.json", report)
        return {
            "ok": False,
            "needs_choice": True,
            "ambiguity": report,
            "message": report.message,
        }

    report = AmbiguityReport(
        notation_id=notation.id,
        shot_id=notation.shot_id,
        ambiguities=[],
        interpretations=interpretations,
        awaiting_choice=False,
        message="Notation is unambiguous enough to translate after explicit confirm.",
    )
    _write(root / "notation" / f"{notation.id}_ambiguity.json", report)
    return {
        "ok": True,
        "needs_choice": False,
        "ambiguity": report,
        "message": report.message,
    }


def _motion_request_from_preview(
    notation: IntentNotation,
    interpretation: NotationInterpretation,
) -> MotionRequest:
    prev = interpretation.motion_preview
    return MotionRequest(
        id=new_id("mreq"),
        shot_id=notation.shot_id,
        notation_id=notation.id,
        interpretation_id=interpretation.id,
        source_object=prev.get("source_object"),
        target_object=prev.get("target_object"),
        motion_path=prev.get("motion_path"),
        force_direction=prev.get("force_direction"),
        timing_emphasis=prev.get("timing_emphasis"),
        contact_point=prev.get("contact_point"),
        anticipation=prev.get("anticipation"),
        overshoot=prev.get("overshoot"),
        settle=prev.get("settle"),
        intended_stillness=prev.get("intended_stillness"),
        start_frame=prev.get("start_frame"),
        end_frame=prev.get("end_frame"),
        status="ready_for_review",
        applied_as_final=False,
        assumptions_applied=list(interpretation.assumptions),
        created_by=ActorKind.HUMAN,
        notes=(
            f"From notation {notation.id} via interpretation "
            f"{interpretation.label} ({interpretation.id}). Not final animation."
        ),
    )


def choose_interpretation(
    root: Path,
    notation_id: str,
    interpretation_id: str,
) -> dict[str, Any]:
    """Record the user's choice in provenance and emit a draft MotionRequest."""
    notation = load_notation(root, notation_id)
    report_path = root / "notation" / f"{notation_id}_ambiguity.json"
    if not report_path.exists():
        analyzed = analyze_notation(root, notation_id)
        report = analyzed["ambiguity"]
    else:
        report = AmbiguityReport.model_validate(_read(report_path))

    match = next(
        (i for i in report.interpretations if i.id == interpretation_id), None
    )
    if match is None:
        return {
            "ok": False,
            "reason": (
                f"Interpretation {interpretation_id} not found. "
                f"Available: {[i.id for i in report.interpretations]}"
            ),
            "ask_user_to_choose": True,
            "interpretations": [i.model_dump(mode="json") for i in report.interpretations],
        }

    req = _motion_request_from_preview(notation, match)
    notation = notation.model_copy(deep=True)
    notation.status = "resolved"
    notation.chosen_interpretation_id = match.id

    rev, prov = attribute_suggestion(
        operation="human.notation_choose_interpretation",
        target_type="shot",
        target_id=notation.shot_id,
        snapshot={
            "notation_id": notation.id,
            "chosen_interpretation_id": match.id,
            "chosen_label": match.label,
            "assumptions": match.assumptions,
            "ambiguities_resolved": report.ambiguities,
            "motion_request": req.model_dump(mode="json"),
            "note": (
                "Human chose an interpretation. MotionRequest is ready_for_review only — "
                "not applied as irreversible final animation."
            ),
        },
        summary=(
            f"Chose notation interpretation '{match.label}' ({match.id}) "
            f"for {notation.id}"
        ),
        inputs={
            "notation_id": notation.id,
            "ambiguities": report.ambiguities,
            "available_interpretations": [i.id for i in report.interpretations],
        },
        outputs={
            "interpretation_id": match.id,
            "motion_request_id": req.id,
            "applied_as_final": False,
        },
    )
    notation.revision_id = rev.id
    req.revision_id = rev.id
    save_notation(root, notation)
    save_motion_request(root, req)
    save_revision(root, rev)
    save_provenance(root, prov)

    # Update ambiguity report
    report = report.model_copy(deep=True)
    report.awaiting_choice = False
    report.message = (
        f"User chose '{match.label}' ({match.id}). "
        f"MotionRequest {req.id} recorded with applied_as_final=False."
    )
    _write(report_path, report)

    return {
        "ok": True,
        "notation": notation,
        "interpretation": match,
        "motion_request": req,
        "provenance_id": prov.id,
        "revision_id": rev.id,
        "applied_as_final": False,
        "message": report.message,
    }


def translate_notation(
    root: Path,
    notation_id: str,
    *,
    interpretation_id: str | None = None,
) -> dict[str, Any]:
    """Translate notation into a structured MotionRequest.

    If ambiguous and no interpretation chosen, show ambiguity + interpretations
    and ask the user to choose (no irreversible animation).
    """
    notation = load_notation(root, notation_id)

    if not notation.marks and notation.freehand_ref:
        return {
            "ok": False,
            "reason": (
                "Freehand notation is linked but has no explicit marks. "
                "Add marks (motion_path, source/target, force, etc.) — "
                "refusing to convert freehand directly into animation."
            ),
            "freehand_ref": notation.freehand_ref,
            "applied_as_final": False,
        }

    analyzed = analyze_notation(root, notation_id)
    if analyzed["needs_choice"] and not interpretation_id:
        report: AmbiguityReport = analyzed["ambiguity"]
        return {
            "ok": False,
            "needs_choice": True,
            "ask_user_to_choose": True,
            "ambiguities": report.ambiguities,
            "interpretations": [
                i.model_dump(mode="json") for i in report.interpretations
            ],
            "message": report.message,
            "applied_as_final": False,
        }

    if interpretation_id:
        return choose_interpretation(root, notation_id, interpretation_id)

    # Unambiguous — still require an explicit translate that records provenance
    report = analyzed["ambiguity"]
    literal = report.interpretations[0]
    req = _motion_request_from_preview(notation, literal)
    notation = notation.model_copy(deep=True)
    notation.status = "resolved"
    notation.chosen_interpretation_id = literal.id

    rev, prov = attribute_suggestion(
        operation="human.notation_translate",
        target_type="shot",
        target_id=notation.shot_id,
        snapshot={
            "notation": notation.model_dump(mode="json"),
            "motion_request": req.model_dump(mode="json"),
            "note": "Literal translate — MotionRequest only, not final animation.",
        },
        summary=f"Translated notation {notation.id} → motion request {req.id}",
        outputs={"motion_request_id": req.id, "applied_as_final": False},
    )
    notation.revision_id = rev.id
    req.revision_id = rev.id
    save_notation(root, notation)
    save_motion_request(root, req)
    save_revision(root, rev)
    save_provenance(root, prov)

    return {
        "ok": True,
        "motion_request": req,
        "notation": notation,
        "provenance_id": prov.id,
        "applied_as_final": False,
        "message": (
            f"MotionRequest {req.id} ready_for_review. "
            "Not applied as irreversible final animation."
        ),
    }
