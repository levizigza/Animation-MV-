"""Craft evaluation harness — multi-dimension, never a single quality score."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now


class EvalDimension(str, Enum):
    """Per-scene craft dimensions. Kept separate — never rolled into one score."""

    INTENT_CLARITY = "intent_clarity"
    POSE_READABILITY = "pose_readability"
    TIMING = "timing"
    SPACING = "spacing"
    STILLNESS = "stillness"
    SEQUENCE_CONTEXT = "sequence_context"
    SOUND_RELATIONSHIP = "sound_relationship"
    REVISION_QUALITY = "revision_quality"
    HUMAN_REVIEWER_PREFERENCE = "human_reviewer_preference"


ALL_EVAL_DIMENSIONS: tuple[EvalDimension, ...] = tuple(EvalDimension)

# Dimensions where automatic heuristics may emit observations.
# Human preference is never auto-filled as a ranking.
AUTO_EVAL_DIMENSIONS: tuple[EvalDimension, ...] = tuple(
    d for d in EvalDimension if d != EvalDimension.HUMAN_REVIEWER_PREFERENCE
)


class SceneKind(str, Enum):
    DIALOGUE = "dialogue"
    PHYSICAL_ACTION = "physical_action"
    QUIET = "quiet"


class ObservationKind(str, Enum):
    """Heuristic signal — not a grade."""

    OK = "ok"
    INFO = "info"
    GAP = "gap"
    RISK = "risk"


class PreferenceChoice(str, Enum):
    PREFER_CURRENT = "prefer_current"
    PREFER_PREVIOUS = "prefer_previous"
    PREFER_NEITHER = "prefer_neither"
    UNDECIDED = "undecided"
    NOT_APPLICABLE = "not_applicable"


class DimensionObservation(BaseModel):
    """One automatic or human-facing observation for a single dimension."""

    dimension: EvalDimension
    kind: ObservationKind
    message: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: Literal["automatic", "human"] = "automatic"


class HumanDimensionResponse(BaseModel):
    """Human answer for one dimension — notes required; no numeric score."""

    dimension: EvalDimension
    notes: str = Field(..., min_length=1)
    preference: PreferenceChoice = PreferenceChoice.UNDECIDED
    # Qualitative weight of the human judgment — not a score
    emphasis: Literal["note", "mild", "strong"] = "note"
    would_block_approval: bool = False


class HumanReviewForm(BaseModel):
    """Blank or filled human review form for a scene evaluation pass."""

    id: str = Field(default_factory=lambda: new_id("hform"))
    scene_id: str
    session_id: str | None = None
    reviewer: str = ""
    revision_id: str = ""
    previous_revision_id: str | None = None
    responses: list[HumanDimensionResponse] = Field(default_factory=list)
    overall_notes: str = ""
    # Explicit: preference is multi-dimensional; no roll-up score
    has_aggregate_quality_score: Literal[False] = False
    quality_score: None = None
    completed: bool = False
    at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def no_aggregate(self) -> HumanReviewForm:
        if self.has_aggregate_quality_score is not False:
            raise ValueError("HumanReviewForm must not carry an aggregate score")
        if self.quality_score is not None:
            raise ValueError("HumanReviewForm.quality_score must remain None")
        return self


class EvalSceneFixture(BaseModel):
    """One of the three harness scenes with craft-facing expectations."""

    id: str
    kind: SceneKind
    title: str
    summary: str
    craft_focus: list[str] = Field(default_factory=list)
    # What success looks like in prose — not a metric target
    success_criteria: list[str] = Field(default_factory=list)
    # Embedded snapshot used for seeding project data
    shot_id: str
    sequence_id: str
    intent: dict[str, Any] = Field(default_factory=dict)
    key_poses: list[dict[str, Any]] = Field(default_factory=list)
    timing: dict[str, Any] = Field(default_factory=dict)
    sound_cues: list[dict[str, Any]] = Field(default_factory=list)
    sequence_neighbors: dict[str, Any] = Field(default_factory=dict)
    revision_notes: str = ""


class AutoEvalPass(BaseModel):
    """Automatic observations only — never substitutes for human preference."""

    id: str = Field(default_factory=lambda: new_id("aev"))
    scene_id: str
    observations: list[DimensionObservation] = Field(default_factory=list)
    # Locked: auto pass is incomplete without human form
    substitutes_for_human_review: Literal[False] = False
    has_aggregate_quality_score: Literal[False] = False
    quality_score: None = None
    at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def no_score_or_substitution(self) -> AutoEvalPass:
        if self.substitutes_for_human_review is not False:
            raise ValueError("Automatic metrics must not substitute for human review")
        if self.has_aggregate_quality_score is not False or self.quality_score is not None:
            raise ValueError("AutoEvalPass must not carry an aggregate quality score")
        dims = {o.dimension for o in self.observations}
        if EvalDimension.HUMAN_REVIEWER_PREFERENCE in dims:
            raise ValueError(
                "Automatic pass must not claim human_reviewer_preference"
            )
        return self


class EvalSession(BaseModel):
    """Stored evaluation run: scene + auto observations + optional human form."""

    id: str
    scene_id: str
    scene_kind: SceneKind
    revision_id: str
    previous_revision_id: str | None = None
    auto_pass: AutoEvalPass | None = None
    human_form: HumanReviewForm | None = None
    workflow_notes: str = ""
    # Engine improvement signal: structured, multi-dimension, no single score
    has_aggregate_quality_score: Literal[False] = False
    quality_score: None = None
    human_review_required: Literal[True] = True
    at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def craft_not_single_score(self) -> EvalSession:
        if self.has_aggregate_quality_score is not False:
            raise ValueError("EvalSession must not use an aggregate quality score")
        if self.quality_score is not None:
            raise ValueError("EvalSession.quality_score must remain None")
        if self.human_review_required is not True:
            raise ValueError("Eval sessions always require human review")
        return self

    def dimension_summary(self) -> dict[str, Any]:
        """Per-dimension view for workflow improvement — never a total score."""
        out: dict[str, Any] = {}
        for dim in EvalDimension:
            auto = [
                o.model_dump(mode="json")
                for o in (self.auto_pass.observations if self.auto_pass else [])
                if o.dimension == dim
            ]
            human = None
            if self.human_form:
                for r in self.human_form.responses:
                    if r.dimension == dim:
                        human = r.model_dump(mode="json")
                        break
            out[dim.value] = {
                "automatic_observations": auto,
                "human_response": human,
                "human_complete": bool(human),
            }
        out["has_aggregate_quality_score"] = False
        out["quality_score"] = None
        out["human_form_completed"] = bool(
            self.human_form and self.human_form.completed
        )
        return out
