"""Pilot findings models — prioritized report, not a single quality score."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now


class FindingPriority(str, Enum):
    P0 = "P0"  # blocks trustworthy craft / approval
    P1 = "P1"  # high confusion or unjustified assumption risk
    P2 = "P2"  # polish / clarity / nice-to-have


class MeasurementAxis(str, Enum):
    USER_CONFUSION = "user_confusion"
    UNJUSTIFIED_ASSUMPTION = "unjustified_assumption"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_REJECTED = "suggestion_rejected"
    REVISION_HISTORY = "revision_history"
    INTENT_COMMUNICATION = "intent_communication"


class PilotFinding(BaseModel):
    id: str = Field(default_factory=lambda: new_id("find"))
    priority: FindingPriority
    axis: MeasurementAxis
    stage: str
    title: str
    detail: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    demonstrated_failure: bool = False
    feature_added: bool = False  # pilot policy: stay False unless failure required a fix


class StageLog(BaseModel):
    stage: str
    ok: bool
    notes: str = ""
    artifacts: dict[str, Any] = Field(default_factory=dict)
    confusion_signals: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class SuggestionOutcome(BaseModel):
    suggestion_id: str
    kind: str
    decision: Literal["accepted", "rejected", "partial", "deferred"]
    reason: str
    stage: str


class PilotReport(BaseModel):
    """Prioritized findings from one short-sequence pilot."""

    id: str = Field(default_factory=lambda: new_id("pilot"))
    sequence_id: str
    focus_shot_id: str
    original_intent: str
    stages_completed: list[str] = Field(default_factory=list)
    stage_log: list[StageLog] = Field(default_factory=list)
    suggestion_outcomes: list[SuggestionOutcome] = Field(default_factory=list)
    findings: list[PilotFinding] = Field(default_factory=list)
    measurements: dict[str, Any] = Field(default_factory=dict)
    final_lifecycle_state: str = ""
    final_intent: str = ""
    intent_still_communicated: bool | None = None
    revision_history_understandable: bool | None = None
    features_added_during_pilot: Literal[False] = False
    has_aggregate_quality_score: Literal[False] = False
    quality_score: None = None
    at: str = Field(default_factory=utc_now)
    summary: str = ""

    @model_validator(mode="after")
    def no_score(self) -> PilotReport:
        if self.has_aggregate_quality_score is not False or self.quality_score is not None:
            raise ValueError("Pilot report must not use an aggregate quality score")
        if self.features_added_during_pilot is not False:
            raise ValueError("Pilot must not silently add product features")
        return self

    def findings_by_priority(self) -> dict[str, list[PilotFinding]]:
        out: dict[str, list[PilotFinding]] = {"P0": [], "P1": [], "P2": []}
        for f in self.findings:
            out[f.priority.value].append(f)
        return out
