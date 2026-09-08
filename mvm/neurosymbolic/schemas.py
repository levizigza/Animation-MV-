"""Neuro-symbolic craft contracts — soft proposals grounded by hard rules."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now


class ProposalSource(str, Enum):
    MIR = "mir"
    HEURISTIC_AGENT = "heuristic_agent"
    ASSISTANT = "assistant"
    LEARNED_MODEL = "learned_model"  # reserved plug-in slot


class GroundingStatus(str, Enum):
    ACCEPTED = "accepted"  # accepted as suggestion only
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"


class NeuralProposal(BaseModel):
    """Soft / perceptual proposal — never an applied final by itself."""

    id: str = Field(default_factory=lambda: new_id("nprop"))
    source: ProposalSource
    domain: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: str = ""
    reason: str = Field(..., min_length=1)
    layer: Literal["neuro"] = "neuro"
    assistant_id: str | None = None
    at: str = Field(default_factory=utc_now)


class SymbolicPredicate(BaseModel):
    """One inspectable craft fact used for grounding."""

    name: str
    value: Any = None
    holds: bool = True
    explanation: str = ""


class GroundingResult(BaseModel):
    status: GroundingStatus
    violated_rules: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    layer: Literal["symbolic"] = "symbolic"
    predicates_checked: list[str] = Field(default_factory=list)

    @property
    def ok_as_suggestion(self) -> bool:
        return self.status in (GroundingStatus.ACCEPTED, GroundingStatus.NEEDS_HUMAN)


class NeuroSymbolicDecision(BaseModel):
    """Grounded decision record — soft proposal + symbolic verdict."""

    id: str = Field(default_factory=lambda: new_id("nsdec"))
    proposal: NeuralProposal
    grounding: GroundingResult
    applied: Literal[False] = False
    has_aggregate_quality_score: Literal[False] = False
    quality_score: None = None
    shot_id: str | None = None
    provenance_id: str | None = None
    at: str = Field(default_factory=utc_now)
    summary: str = ""

    @model_validator(mode="after")
    def suggestion_only(self) -> NeuroSymbolicDecision:
        if self.applied is not False:
            raise ValueError("NeuroSymbolicDecision.applied must remain False")
        if self.has_aggregate_quality_score is not False or self.quality_score is not None:
            raise ValueError("Neuro-symbolic decisions must not use an aggregate score")
        return self


class SymbolicCraftState(BaseModel):
    """Hard craft facts for a shot — symbolic authority."""

    shot_id: str
    lifecycle_state: str = "intent"
    animatic_approved: bool = False
    intent_explicit: bool = False
    intent_purpose: str = ""
    allow_auto_smooth: bool = False
    force_every_cue_to_motion: bool = False
    timing_plan_id: str | None = None
    key_pose_count: int = 0
    key_frames: list[int] = Field(default_factory=list)
    smear_frames: list[int] = Field(default_factory=list)
    cel_mode: str = "full"
    style_pack: str = ""
    section_energy: float | None = None
    predicates: list[SymbolicPredicate] = Field(default_factory=list)

    def predicate_map(self) -> dict[str, SymbolicPredicate]:
        return {p.name: p for p in self.predicates}
