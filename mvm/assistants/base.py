"""Narrow craft assistants — scoped suggestions only, never silent cross-domain edits."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now


class AssistantId(str, Enum):
    STORYBOARD = "storyboard"
    TIMING = "timing"
    POSE = "pose"
    CONTINUITY = "continuity"
    SOUND = "sound"
    CRITIQUE = "critique"
    PROVENANCE = "provenance"


# Domains an assistant may *read*. Writes during suggest() are fenced separately.
ASSISTANT_READ_DOMAINS: dict[AssistantId, frozenset[str]] = {
    AssistantId.STORYBOARD: frozenset(
        {"shots", "panels", "animatics", "sequences", "project"}
    ),
    AssistantId.TIMING: frozenset(
        {"shots", "timing", "xsheets", "beatmap", "sound_plans"}
    ),
    AssistantId.POSE: frozenset(
        {"shots", "key_poses", "timing", "suggestions", "notebooks"}
    ),
    AssistantId.CONTINUITY: frozenset(
        {"shots", "sequences", "layouts", "sequence_evals"}
    ),
    AssistantId.SOUND: frozenset({"shots", "sound_plans", "beatmap", "timing"}),
    AssistantId.CRITIQUE: frozenset(
        {"shots", "critiques", "sequence_evals", "timing", "key_poses"}
    ),
    AssistantId.PROVENANCE: frozenset(
        {"provenance", "revisions", "provenance_exports", "project"}
    ),
}

# Domains an assistant may never mutate (even via tools) during suggest().
# Provenance/revisions/assistant_suggestions are the only suggest-time writes.
ASSISTANT_FORBIDDEN_WRITE_DOMAINS: dict[AssistantId, frozenset[str]] = {
    AssistantId.STORYBOARD: frozenset(
        {
            "timing",
            "key_poses",
            "sound_plans",
            "critiques",
            "xsheets",
            "layouts",
            "notebooks",
        }
    ),
    AssistantId.TIMING: frozenset(
        {
            "panels",
            "animatics",
            "key_poses",
            "sound_plans",
            "critiques",
            "shots",
            "layouts",
        }
    ),
    AssistantId.POSE: frozenset(
        {
            "panels",
            "animatics",
            "sound_plans",
            "critiques",
            "shots",
            "xsheets",
            "layouts",
            "timing",  # pose assistant must not rewrite timing sheets
        }
    ),
    AssistantId.CONTINUITY: frozenset(
        {
            "panels",
            "animatics",
            "timing",
            "key_poses",
            "sound_plans",
            "critiques",
            "shots",
            "xsheets",
        }
    ),
    AssistantId.SOUND: frozenset(
        {
            "panels",
            "animatics",
            "timing",
            "key_poses",
            "critiques",
            "shots",
            "xsheets",
            "layouts",
        }
    ),
    AssistantId.CRITIQUE: frozenset(
        {
            "panels",
            "animatics",
            "timing",
            "key_poses",
            "sound_plans",
            "shots",
            "xsheets",
            "layouts",
        }
    ),
    AssistantId.PROVENANCE: frozenset(
        {
            "panels",
            "animatics",
            "timing",
            "key_poses",
            "sound_plans",
            "critiques",
            "shots",
            "xsheets",
            "layouts",
            "sequences",
        }
    ),
}

# Suggest-time write allowlist (shared)
SUGGEST_WRITE_ALLOWLIST = frozenset(
    {"provenance", "revisions", "assistant_suggestions"}
)


class DomainFence(BaseModel):
    """Explicit tool boundary — blocks writes outside an assistant's allowlist."""

    assistant_id: AssistantId
    attempted_writes: list[dict[str, str]] = Field(default_factory=list)

    def check_write(self, domain: str, *, path: str = "") -> None:
        """Suggest-time writes: only provenance / revisions / assistant_suggestions."""
        self.attempted_writes.append({"domain": domain, "path": path})
        if domain in SUGGEST_WRITE_ALLOWLIST:
            return
        forbidden = ASSISTANT_FORBIDDEN_WRITE_DOMAINS[self.assistant_id]
        scope_note = (
            f"forbidden for this assistant"
            if domain in forbidden
            else "not in suggest-time write allowlist"
        )
        raise PermissionError(
            f"Assistant '{self.assistant_id.value}' cannot modify domain "
            f"'{domain}' ({scope_note}). Operate only within assigned scope; "
            f"return suggestions rather than silently editing."
        )

    def assert_tool_domain(self, domain: str) -> None:
        """Refuse tools that target another assistant's mutable domain."""
        forbidden = ASSISTANT_FORBIDDEN_WRITE_DOMAINS[self.assistant_id]
        if domain in forbidden:
            raise PermissionError(
                f"Assistant '{self.assistant_id.value}' tool boundary: "
                f"domain '{domain}' is outside assigned scope."
            )


class AssistantSuggestion(BaseModel):
    """One scoped suggestion — not an applied edit."""

    id: str = Field(default_factory=lambda: new_id("asug"))
    assistant_id: AssistantId
    domain: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: str = ""
    visibly_labeled_generated: Literal[True] = True
    applied: Literal[False] = False

    @model_validator(mode="after")
    def suggestion_only(self) -> AssistantSuggestion:
        if self.applied is not False:
            raise ValueError("AssistantSuggestion.applied must remain False")
        if self.visibly_labeled_generated is not True:
            raise ValueError("Generated assistant suggestions must be visibly labeled")
        return self


class AssistantResult(BaseModel):
    assistant_id: AssistantId
    input_assumptions: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    suggestions: list[AssistantSuggestion] = Field(default_factory=list)
    refused_writes: list[dict[str, str]] = Field(default_factory=list)
    provenance_id: str | None = None
    revision_id: str | None = None
    silently_edited: Literal[False] = False
    at: str = Field(default_factory=utc_now)
    summary: str = ""

    @model_validator(mode="after")
    def no_silent_edit(self) -> AssistantResult:
        if self.silently_edited is not False:
            raise ValueError("Assistants must not silently edit")
        return self
