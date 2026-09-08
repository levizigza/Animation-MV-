"""Evaluation harness workflow — seed scenes, auto pass, human form, store results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.eval_harness.auto import evaluate_scene_automatic
from mvm.eval_harness.scenes import HARNESS_SCENES, get_scene, list_scenes
from mvm.project.domain_store import ensure_domain_dirs
from mvm.provenance import record_meaningful_change
from mvm.schemas.domain import ActorKind, new_id
from mvm.schemas.eval_harness import (
    ALL_EVAL_DIMENSIONS,
    EvalDimension,
    EvalSceneFixture,
    EvalSession,
    HumanDimensionResponse,
    HumanReviewForm,
    PreferenceChoice,
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


def ensure_eval_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    for name in ("eval_scenes", "eval_sessions", "eval_forms"):
        (root / name).mkdir(parents=True, exist_ok=True)


def seed_harness_scenes(root: Path) -> list[EvalSceneFixture]:
    """Write the three test scenes into project data (idempotent overwrite by id)."""
    ensure_eval_dirs(root)
    out: list[EvalSceneFixture] = []
    for scene in HARNESS_SCENES:
        path = root / "eval_scenes" / f"{scene.id}.json"
        _write(path, scene)
        out.append(scene)
    record_meaningful_change(
        root,
        operation="eval.seed_scenes",
        target_type="project",
        target_id="eval_harness",
        snapshot={"scene_ids": [s.id for s in out]},
        summary="Seeded three craft evaluation harness scenes",
        creator="eval_harness",
        actor=ActorKind.SYSTEM,
        source_references=["eval_harness:scenes"],
        input_parameters={"scene_count": len(out)},
        outputs={"scene_ids": [s.id for s in out]},
        generated=False,
    )
    return out


def load_scene(root: Path, scene_id: str) -> EvalSceneFixture:
    path = root / "eval_scenes" / f"{scene_id}.json"
    if path.exists():
        return EvalSceneFixture.model_validate(_read(path))
    return get_scene(scene_id)


def blank_human_form(
    *,
    scene_id: str,
    revision_id: str,
    previous_revision_id: str | None = None,
    session_id: str | None = None,
    reviewer: str = "",
) -> HumanReviewForm:
    """Human review form with a prompt stub per dimension (notes must be filled)."""
    prompts = {
        EvalDimension.INTENT_CLARITY: (
            "[Fill] Is the shot's purpose and emotional beat clear on screen?"
        ),
        EvalDimension.POSE_READABILITY: (
            "[Fill] Do key silhouettes / acting poses read without audio?"
        ),
        EvalDimension.TIMING: (
            "[Fill] Does timing support the beat (holds, accents, reaction delay)?"
        ),
        EvalDimension.SPACING: (
            "[Fill] Is spacing intentional (slow-in/out/stepped) vs accidental?"
        ),
        EvalDimension.STILLNESS: (
            "[Fill] Does stillness feel authored — especially in quiet beats?"
        ),
        EvalDimension.SEQUENCE_CONTEXT: (
            "[Fill] Does this shot work with prev/next for continuity and pacing?"
        ),
        EvalDimension.SOUND_RELATIONSHIP: (
            "[Fill] Are sound→motion choices appropriate? Silence/non-reaction OK?"
        ),
        EvalDimension.REVISION_QUALITY: (
            "[Fill] Compared to previous revision, what improved or regressed?"
        ),
        EvalDimension.HUMAN_REVIEWER_PREFERENCE: (
            "[Fill] Which revision do you prefer, and why? (not a numeric score)"
        ),
    }
    responses = [
        HumanDimensionResponse(
            dimension=dim,
            notes=prompts[dim],
            preference=PreferenceChoice.UNDECIDED,
            emphasis="note",
            would_block_approval=False,
        )
        for dim in ALL_EVAL_DIMENSIONS
    ]
    return HumanReviewForm(
        scene_id=scene_id,
        session_id=session_id,
        reviewer=reviewer,
        revision_id=revision_id,
        previous_revision_id=previous_revision_id,
        responses=responses,
        completed=False,
        has_aggregate_quality_score=False,
        quality_score=None,
    )


def save_human_form(root: Path, form: HumanReviewForm) -> Path:
    ensure_eval_dirs(root)
    if form.has_aggregate_quality_score is not False or form.quality_score is not None:
        raise ValueError("Refusing human form with aggregate quality score")
    path = root / "eval_forms" / f"{form.id}.json"
    _write(path, form)
    return path


def load_human_form(root: Path, form_id: str) -> HumanReviewForm:
    return HumanReviewForm.model_validate(_read(root / "eval_forms" / f"{form_id}.json"))


def save_session(root: Path, session: EvalSession) -> Path:
    ensure_eval_dirs(root)
    if session.has_aggregate_quality_score is not False or session.quality_score is not None:
        raise ValueError("Refusing eval session with aggregate quality score")
    path = root / "eval_sessions" / f"{session.id}.json"
    _write(path, session)
    return path


def load_session(root: Path, session_id: str) -> EvalSession:
    return EvalSession.model_validate(_read(root / "eval_sessions" / f"{session_id}.json"))


def list_sessions(root: Path) -> list[EvalSession]:
    d = root / "eval_sessions"
    if not d.exists():
        return []
    out: list[EvalSession] = []
    for p in d.glob("*.json"):
        out.append(EvalSession.model_validate(_read(p)))
    return sorted(out, key=lambda s: s.at)


def start_eval_session(
    root: Path,
    *,
    scene_id: str,
    revision_id: str,
    previous_revision_id: str | None = None,
    run_auto: bool = True,
) -> EvalSession:
    """Create a session: optional auto observations + blank human form."""
    ensure_eval_dirs(root)
    scene = load_scene(root, scene_id)
    session_id = new_id("esess")
    auto = evaluate_scene_automatic(scene) if run_auto else None
    form = blank_human_form(
        scene_id=scene.id,
        revision_id=revision_id,
        previous_revision_id=previous_revision_id,
        session_id=session_id,
    )
    save_human_form(root, form)
    session = EvalSession(
        id=session_id,
        scene_id=scene.id,
        scene_kind=scene.kind,
        revision_id=revision_id,
        previous_revision_id=previous_revision_id,
        auto_pass=auto,
        human_form=form,
        workflow_notes=(
            "Automatic observations are signals only. Complete the human review "
            "form before treating this session as workflow evidence."
        ),
        has_aggregate_quality_score=False,
        quality_score=None,
        human_review_required=True,
    )
    save_session(root, session)
    record_meaningful_change(
        root,
        operation="eval.session_start",
        target_type="shot",
        target_id=scene.shot_id,
        snapshot=session.model_dump(mode="json"),
        summary=f"Started eval session for {scene.id}",
        creator="eval_harness",
        actor=ActorKind.SYSTEM,
        source_references=[f"eval_scene:{scene.id}"],
        input_parameters={
            "scene_id": scene.id,
            "revision_id": revision_id,
            "run_auto": run_auto,
        },
        outputs={
            "session_id": session.id,
            "form_id": form.id,
            "auto_observation_count": len(auto.observations) if auto else 0,
            "has_aggregate_quality_score": False,
        },
        generated=True,
    )
    return session


def submit_human_form(
    root: Path,
    *,
    session_id: str,
    reviewer: str,
    responses: list[dict[str, Any]],
    overall_notes: str = "",
) -> EvalSession:
    """Attach completed human responses. Rejects aggregate scores and stub notes."""
    session = load_session(root, session_id)
    if not reviewer.strip():
        raise ValueError("reviewer identity is required")

    parsed: list[HumanDimensionResponse] = []
    for raw in responses:
        if isinstance(raw, dict) and (
            raw.get("quality_score") is not None
            or raw.get("has_aggregate_quality_score") is True
        ):
            raise ValueError(
                "Human responses must not include an aggregate quality score"
            )
        resp = HumanDimensionResponse.model_validate(raw)
        note = resp.notes.strip()
        if note.startswith("[Fill]") or len(note) < 8:
            raise ValueError(
                f"Human notes for {resp.dimension.value} still look like a blank prompt"
            )
        parsed.append(resp)

    dims = {r.dimension for r in parsed}
    missing = set(ALL_EVAL_DIMENSIONS) - dims
    if missing:
        raise ValueError(
            "Human form incomplete; missing dimensions: "
            + ", ".join(sorted(d.value for d in missing))
        )
    if EvalDimension.HUMAN_REVIEWER_PREFERENCE not in dims:
        raise ValueError("human_reviewer_preference response is required")

    form = session.human_form or blank_human_form(
        scene_id=session.scene_id,
        revision_id=session.revision_id,
        previous_revision_id=session.previous_revision_id,
        session_id=session.id,
    )
    form.reviewer = reviewer.strip()
    form.responses = parsed
    form.overall_notes = overall_notes
    form.completed = True
    form.has_aggregate_quality_score = False
    form.quality_score = None
    form.session_id = session.id
    save_human_form(root, form)

    session.human_form = form
    save_session(root, session)
    record_meaningful_change(
        root,
        operation="eval.human_submit",
        target_type="shot",
        target_id=session.scene_id,
        snapshot={
            "session_id": session.id,
            "form_id": form.id,
            "dimension_summary": session.dimension_summary(),
        },
        summary=f"Human eval form submitted by {reviewer} for {session.scene_id}",
        creator=reviewer.strip(),
        actor=ActorKind.HUMAN,
        source_references=[f"eval_session:{session.id}"],
        input_parameters={"reviewer": reviewer, "session_id": session_id},
        outputs={
            "completed": True,
            "has_aggregate_quality_score": False,
            "preference": next(
                (
                    r.preference.value
                    for r in parsed
                    if r.dimension == EvalDimension.HUMAN_REVIEWER_PREFERENCE
                ),
                None,
            ),
        },
        generated=False,
    )
    return session


def run_all_scenes_auto(root: Path, *, revision_prefix: str = "rev_eval") -> list[EvalSession]:
    """Convenience: seed + start a session (auto + blank form) for each scene."""
    seed_harness_scenes(root)
    sessions: list[EvalSession] = []
    for scene in list_scenes():
        sessions.append(
            start_eval_session(
                root,
                scene_id=scene.id,
                revision_id=f"{revision_prefix}_{scene.kind.value}",
                run_auto=True,
            )
        )
    return sessions
