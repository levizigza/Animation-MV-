"""Sequence-aware evaluation models — identify issues, never auto-fix."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now


class CharacterStateSnapshot(BaseModel):
    """Recurring character state observed across the sequence window."""

    character_id: str
    present_in_previous: bool = False
    present_in_current: bool = False
    present_in_following: bool = False
    last_seen_shot_id: str | None = None
    emotional_hint: str = ""
    gesture_hints: list[str] = Field(default_factory=list)
    notes: str = ""


class SequenceIssue(BaseModel):
    """A possible continuity/craft issue — explanatory only, not a fix."""

    id: str = Field(default_factory=lambda: new_id("siss"))
    kind: Literal[
        "repeated_framing",
        "repeated_gesture",
        "pacing_contrast",
        "emotional_progression",
        "reaction_mismatch",
        "camera_continuity",
        "spatial_continuity",
        "character_state",
    ]
    shot_id: str
    previous_shot_id: str | None = None
    following_shot_id: str | None = None
    explanation: str = Field(..., min_length=1)
    evidence: dict[str, Any] = Field(default_factory=dict)
    # Human-facing attention hint — not an applied edit
    suggested_attention: str = ""
    auto_fixed: Literal[False] = False

    @model_validator(mode="after")
    def never_auto_fixed(self) -> SequenceIssue:
        if self.auto_fixed is not False:
            raise ValueError("SequenceIssue must not auto-fix shots")
        return self


class SequenceEvaluation(BaseModel):
    """Evaluation of one shot in sequence context."""

    id: str = Field(default_factory=lambda: new_id("seqev"))
    sequence_id: str
    focus_shot_id: str
    previous_shot_id: str | None = None
    following_shot_id: str | None = None
    character_states: list[CharacterStateSnapshot] = Field(default_factory=list)
    issues: list[SequenceIssue] = Field(default_factory=list)
    summary: str = ""
    # Hard rule: evaluator never mutates shot JSON / timing / keys
    auto_fix_applied: Literal[False] = False
    shots_mutated: Literal[False] = False
    at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def no_auto_fix(self) -> SequenceEvaluation:
        if self.auto_fix_applied is not False or self.shots_mutated is not False:
            raise ValueError(
                "SequenceEvaluation must not automatically fix shots — "
                "issues are informational only"
            )
        return self
