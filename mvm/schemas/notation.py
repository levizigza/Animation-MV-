"""Lightweight creator-intent notation → structured motion requests.

Notation is explicit authoring data. It never becomes an irreversible final
animation in this module (``applied_as_final`` stays False).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import ActorKind, new_id, utc_now
from mvm.schemas.models import ApprovalState


class NotationKind(str, Enum):
    MOTION_PATH = "motion_path"
    SOURCE_OBJECT = "source_object"
    TARGET_OBJECT = "target_object"
    FORCE_DIRECTION = "force_direction"
    TIMING_EMPHASIS = "timing_emphasis"
    CONTACT_POINT = "contact_point"
    ANTICIPATION = "anticipation"
    OVERSHOOT = "overshoot"
    SETTLE = "settle"
    INTENDED_STILLNESS = "intended_stillness"


class NotationMark(BaseModel):
    """One explicit notation glyph / label — not a rendered stroke buffer."""

    id: str = Field(default_factory=lambda: new_id("nmark"))
    kind: NotationKind
    # Human-readable explicit value (object name, path label, direction, etc.)
    value: str = Field(..., min_length=1)
    frame: int | None = Field(default=None, ge=1)
    end_frame: int | None = Field(default=None, ge=1)
    # Optional structured extras (e.g. path waypoints as labels — not pixels)
    meta: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""

    @model_validator(mode="after")
    def end_after_start(self) -> NotationMark:
        if (
            self.frame is not None
            and self.end_frame is not None
            and self.end_frame < self.frame
        ):
            raise ValueError("NotationMark.end_frame must be >= frame")
        return self


class IntentNotation(BaseModel):
    """Shot-scoped creator notation. Freehand refs are links only — not auto-baked."""

    id: str
    shot_id: str
    marks: list[NotationMark] = Field(default_factory=list)
    # Optional pointer to a sketch/file; never auto-converted to finals
    freehand_ref: str | None = None
    status: Literal["draft", "ambiguous", "resolved", "rejected"] = "draft"
    chosen_interpretation_id: str | None = None
    revision_id: str | None = None
    approval: ApprovalState = ApprovalState.DRAFT
    # Hard rule for this artifact class
    converts_to_final_animation: Literal[False] = False
    at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def never_final(self) -> IntentNotation:
        if self.converts_to_final_animation is not False:
            raise ValueError("IntentNotation must not convert directly to final animation")
        return self


class NotationInterpretation(BaseModel):
    """One plausible reading of ambiguous notation — user must choose."""

    id: str
    label: str
    summary: str
    # What this reading assumes that was not explicit in the marks
    assumptions: list[str] = Field(default_factory=list)
    # Preview of the motion request fields this reading would produce
    motion_preview: dict[str, Any] = Field(default_factory=dict)


class AmbiguityReport(BaseModel):
    notation_id: str
    shot_id: str
    ambiguities: list[str] = Field(default_factory=list)
    interpretations: list[NotationInterpretation] = Field(default_factory=list)
    awaiting_choice: bool = True
    message: str = (
        "Notation is ambiguous. Choose an interpretation id before a motion request "
        "is recorded. Nothing has been applied as final animation."
    )


class MotionRequest(BaseModel):
    """Structured motion intent derived from notation — craft request, not a final."""

    id: str
    shot_id: str
    notation_id: str
    interpretation_id: str | None = None
    source_object: str | None = None
    target_object: str | None = None
    motion_path: str | None = None
    force_direction: str | None = None
    timing_emphasis: str | None = None
    contact_point: str | None = None
    anticipation: str | None = None
    overshoot: str | None = None
    settle: str | None = None
    intended_stillness: str | None = None
    # Frames if known
    start_frame: int | None = None
    end_frame: int | None = None
    status: Literal[
        "draft",
        "pending_choice",
        "ready_for_review",
        "rejected",
    ] = "draft"
    # Explicit: translating notation must not bake irreversible animation
    applied_as_final: Literal[False] = False
    assumptions_applied: list[str] = Field(default_factory=list)
    revision_id: str | None = None
    approval: ApprovalState = ApprovalState.DRAFT
    created_by: ActorKind = ActorKind.SYSTEM
    at: str = Field(default_factory=utc_now)
    notes: str = ""

    @model_validator(mode="after")
    def not_final(self) -> MotionRequest:
        if self.applied_as_final is not False:
            raise ValueError(
                "MotionRequest.applied_as_final must remain False — "
                "notation cannot become irreversible final animation here"
            )
        return self
