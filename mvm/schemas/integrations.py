"""External craft references — fetched suggestions, never silent finals."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import new_id, utc_now
from mvm.schemas.notebook import SourceAttribution


class ReferenceProvider(str, Enum):
    FREE_DICTIONARY = "free_dictionary"
    ARTIC = "art_institute_chicago"
    MUSICBRAINZ = "musicbrainz"
    COLORMIND = "colormind"
    LYRICS_OVH = "lyrics_ovh"
    MET_MUSEUM = "metropolitan_museum"


class ReferenceKind(str, Enum):
    PHONETICS = "phonetics"
    VISUAL_REFERENCE = "visual_reference"
    MUSIC_METADATA = "music_metadata"
    COLOR_PALETTE = "color_palette"
    LYRICS = "lyrics"


class ExternalReference(BaseModel):
    """One fetched reference stored as project data for human craft decisions.

    Never applied as final animation automatically.
    """

    id: str = Field(default_factory=lambda: new_id("xref"))
    provider: ReferenceProvider
    kind: ReferenceKind
    query: str = ""
    title: str = ""
    summary: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    attribution: SourceAttribution
    craft_use: str = Field(
        ...,
        min_length=1,
        description="How a human animator might use this — not an auto-apply instruction",
    )
    source_url: str = ""
    applied_as_final: Literal[False] = False
    human_accepted: bool = False
    visibly_labeled_external: Literal[True] = True
    shot_id: str | None = None
    notebook_id: str | None = None
    at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def never_final(self) -> ExternalReference:
        if self.applied_as_final is not False:
            raise ValueError("External references must not be applied as final")
        if self.visibly_labeled_external is not True:
            raise ValueError("External references must be visibly labeled")
        return self


class IntegrationCatalogEntry(BaseModel):
    """Curated public-apis entry with craft-first rationale."""

    provider: ReferenceProvider
    public_apis_category: str
    name: str
    docs_url: str
    auth: str
    cors: str
    craft_role: str
    enhances: list[str] = Field(default_factory=list)
    # Why this does NOT manufacture “great animation”
    non_generative_guarantee: str = ""
    reliability_note: str = ""
