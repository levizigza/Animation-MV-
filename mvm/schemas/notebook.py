"""Reference notebooks — explicit craft metadata, not opaque style imitation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now
from mvm.schemas.models import ApprovalState


class SourceAttribution(BaseModel):
    """Required provenance for attached reference media."""

    source_title: str = Field(..., min_length=1)
    creator_or_rights: str = ""
    url_or_path: str = ""
    license_or_fair_use_note: str = ""
    captured_at: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def title_required(self) -> SourceAttribution:
        if not self.source_title.strip():
            raise ValueError("SourceAttribution.source_title is required")
        return self


class NotebookMedia(BaseModel):
    """Reference image or video entry with mandatory attribution."""

    id: str = Field(default_factory=lambda: new_id("nmedia"))
    media_type: Literal["image", "video", "other"] = "image"
    path_or_uri: str = Field(..., min_length=1)
    caption: str = ""
    attribution: SourceAttribution
    # Optional observational cue for video (timecode / beat) — not pixels
    observation_cue: str = ""


class AssistanceMetadata(BaseModel):
    """What assistants may use — explicit fields only, never a latent style vector."""

    preserve: list[str] = Field(default_factory=list)
    exaggerate: list[str] = Field(default_factory=list)
    omit: list[str] = Field(default_factory=list)
    acting_observations: list[str] = Field(default_factory=list)
    movement_vocabulary: list[str] = Field(default_factory=list)
    recurring_behaviors: list[str] = Field(default_factory=list)
    transformation_notes: list[str] = Field(default_factory=list)
    media_ids: list[str] = Field(default_factory=list)
    attribution_summaries: list[str] = Field(default_factory=list)
    notes_for_agents: str = ""
    # Hard discriminator against opaque imitation pipelines
    influence_mode: Literal["explicit_metadata"] = "explicit_metadata"


class ReferenceNotebook(BaseModel):
    """Project- or character-scoped craft notebook."""

    id: str
    scope: Literal["project", "character"]
    # Project slug or workspace name; required for project scope
    project_slug: str = ""
    character_id: str | None = None
    character_name: str = ""
    title: str = ""
    version: int = Field(1, ge=1)
    parent_notebook_id: str | None = None
    media: list[NotebookMedia] = Field(default_factory=list)
    observational_notes: list[str] = Field(default_factory=list)
    preserve: list[str] = Field(default_factory=list)
    exaggerate: list[str] = Field(default_factory=list)
    omit: list[str] = Field(default_factory=list)
    acting_observations: list[str] = Field(default_factory=list)
    movement_vocabulary: list[str] = Field(default_factory=list)
    recurring_behaviors: list[str] = Field(default_factory=list)
    transformation_notes: list[str] = Field(default_factory=list)
    # Denormalized explicit assist payload (rebuilt on edit)
    assistance: AssistanceMetadata = Field(default_factory=AssistanceMetadata)
    opaque_style_imitation: Literal[False] = False
    revision_id: str | None = None
    approval: ApprovalState = ApprovalState.DRAFT
    at: str = Field(default_factory=utc_now)
    notes: str = ""

    @model_validator(mode="after")
    def scope_and_no_opaque(self) -> ReferenceNotebook:
        if self.opaque_style_imitation is not False:
            raise ValueError(
                "ReferenceNotebook must not use opaque style imitation — "
                "influence only via explicit assistance metadata"
            )
        if self.scope == "character" and not (self.character_id or "").strip():
            raise ValueError("character-scoped notebook requires character_id")
        if self.scope == "project" and not (self.project_slug or "").strip():
            raise ValueError("project-scoped notebook requires project_slug")
        return self


def build_assistance_metadata(notebook: ReferenceNotebook) -> AssistanceMetadata:
    """Rebuild explicit assist metadata from notebook fields (no latent style)."""
    attributions = []
    for m in notebook.media:
        a = m.attribution
        attributions.append(
            f"{m.media_type}:{m.path_or_uri} ← {a.source_title}"
            + (f" ({a.creator_or_rights})" if a.creator_or_rights else "")
        )
    return AssistanceMetadata(
        preserve=list(notebook.preserve),
        exaggerate=list(notebook.exaggerate),
        omit=list(notebook.omit),
        acting_observations=list(notebook.acting_observations),
        movement_vocabulary=list(notebook.movement_vocabulary),
        recurring_behaviors=list(notebook.recurring_behaviors),
        transformation_notes=list(notebook.transformation_notes),
        media_ids=[m.id for m in notebook.media],
        attribution_summaries=attributions,
        notes_for_agents=(
            "Use only these explicit fields. Do not imitate style latently. "
            + (notebook.notes or "")
        ).strip(),
        influence_mode="explicit_metadata",
    )
