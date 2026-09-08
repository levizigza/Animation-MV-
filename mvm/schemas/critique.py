"""Structured craft critique — multi-category, never a single quality score."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now
from mvm.schemas.models import ApprovalState


class CritiqueCategory(str, Enum):
    INTENT_CLARITY = "intent_clarity"
    STAGING = "staging"
    SILHOUETTE_READABILITY = "silhouette_readability"
    POSE = "pose"
    TIMING = "timing"
    SPACING = "spacing"
    WEIGHT = "weight"
    ACTING = "acting"
    EMOTIONAL_TRANSITION = "emotional_transition"
    CONTINUITY = "continuity"
    SOUND_RELATIONSHIP = "sound_relationship"
    ORIGINALITY_AUTHORSHIP = "originality_authorship"


ALL_CRITIQUE_CATEGORIES: tuple[CritiqueCategory, ...] = tuple(CritiqueCategory)


class CritiqueSeverity(str, Enum):
    NOTE = "note"
    MINOR = "minor"
    MAJOR = "major"
    BLOCKER = "blocker"


class FrameOrTimeRef(BaseModel):
    """Frame and/or time-range reference for a critique note."""

    frame: int | None = Field(default=None, ge=1)
    end_frame: int | None = Field(default=None, ge=1)
    time_sec: float | None = Field(default=None, ge=0.0)
    end_time_sec: float | None = Field(default=None, ge=0.0)
    label: str = ""

    @model_validator(mode="after")
    def coherent_range(self) -> FrameOrTimeRef:
        if self.frame is not None and self.end_frame is not None:
            if self.end_frame < self.frame:
                raise ValueError("end_frame must be >= frame")
        if self.time_sec is not None and self.end_time_sec is not None:
            if self.end_time_sec < self.time_sec:
                raise ValueError("end_time_sec must be >= time_sec")
        if (
            self.frame is None
            and self.end_frame is None
            and self.time_sec is None
            and self.end_time_sec is None
            and not self.label
        ):
            raise ValueError(
                "FrameOrTimeRef needs frame, time_sec, and/or label"
            )
        return self


class CritiqueItem(BaseModel):
    """One category-scoped critique. Never rolled into an aggregate score."""

    id: str = Field(default_factory=lambda: new_id("crit"))
    category: CritiqueCategory
    notes: str = Field(..., min_length=1)
    severity: CritiqueSeverity = CritiqueSeverity.NOTE
    range: FrameOrTimeRef | None = None
    resolved: bool = False
    resolution_notes: str = ""
    resolved_at: str | None = None
    at: str = Field(default_factory=utc_now)


class CraftReview(BaseModel):
    """Structured review session for a target revision.

    Categories stay separate. ``has_aggregate_quality_score`` is locked False.
    """

    id: str
    target_type: Literal[
        "project",
        "sequence",
        "shot",
        "timing_plan",
        "storyboard",
        "layout",
        "animatic",
        "key_pose",
        "notebook",
        "motion_request",
    ] = "shot"
    target_id: str
    # Revision under critique
    revision_id: str
    previous_revision_id: str | None = None
    reviewer: str = Field(..., min_length=1)
    items: list[CritiqueItem] = Field(default_factory=list)
    # Written session notes — not a numeric score
    summary_notes: str = ""
    revision_status: Literal[
        "open",
        "in_progress",
        "needs_revisions",
        "resolved",
        "closed",
    ] = "open"
    approval: ApprovalState = ApprovalState.PENDING_REVIEW
    has_aggregate_quality_score: Literal[False] = False
    # Forbidden field guard — if present in raw JSON as a number, reject
    quality_score: None = None
    at: str = Field(default_factory=utc_now)
    provenance_id: str | None = None

    @model_validator(mode="after")
    def no_aggregate_score(self) -> CraftReview:
        if self.has_aggregate_quality_score is not False:
            raise ValueError(
                "CraftReview must not collapse categories into one quality score"
            )
        if self.quality_score is not None:
            raise ValueError(
                "quality_score is forbidden — keep per-category critiques"
            )
        return self

    def unresolved_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {c.value: 0 for c in CritiqueCategory}
        for item in self.items:
            if not item.resolved:
                counts[item.category.value] += 1
        return counts

    def severity_counts(self, *, unresolved_only: bool = False) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in CritiqueSeverity}
        for item in self.items:
            if unresolved_only and item.resolved:
                continue
            counts[item.severity.value] += 1
        return counts


class CritiqueRevisionCompare(BaseModel):
    """Current revision vs previous — category-preserving comparison view."""

    current_review_id: str
    previous_review_id: str | None
    current_revision_id: str
    previous_revision_id: str | None
    # Per-category unresolved counts (never a single score)
    unresolved_by_category_current: dict[str, int] = Field(default_factory=dict)
    unresolved_by_category_previous: dict[str, int] = Field(default_factory=dict)
    unresolved_delta_by_category: dict[str, int] = Field(default_factory=dict)
    severity_current: dict[str, int] = Field(default_factory=dict)
    severity_previous: dict[str, int] = Field(default_factory=dict)
    resolved_since_previous: list[dict[str, Any]] = Field(default_factory=list)
    still_unresolved: list[dict[str, Any]] = Field(default_factory=list)
    new_items_in_current: list[dict[str, Any]] = Field(default_factory=list)
    categories_improved: list[str] = Field(default_factory=list)
    categories_regressed: list[str] = Field(default_factory=list)
    summary: str = ""
    has_aggregate_quality_score: Literal[False] = False
