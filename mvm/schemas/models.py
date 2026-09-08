"""Project file schemas — source of truth for Studio, agents, and Blender."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ApprovalState(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ShotLifecycleState(str, Enum):
    """Authoring lifecycle for a shot — see ``mvm.schemas.lifecycle`` for transitions."""

    INTENT = "intent"
    STORYBOARD = "storyboard"
    LAYOUT = "layout"
    ANIMATIC = "animatic"
    KEY_POSES = "key_poses"
    TIMING_REVIEW = "timing_review"
    INBETWEEN_REVIEW = "inbetween_review"
    SOUND_EDIT_REVIEW = "sound_edit_review"
    FINAL_REVIEW = "final_review"
    APPROVED = "approved"


class Section(BaseModel):
    name: str
    start: float
    end: float
    energy: float = 0.5


class Beatmap(BaseModel):
    duration: float
    sample_rate: int
    bpm: float
    beat_times: list[float] = Field(default_factory=list)
    downbeat_times: list[float] = Field(default_factory=list)
    onset_times: list[float] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    energy_curve: list[dict[str, float]] = Field(default_factory=list)
    spectral_flux: list[dict[str, float]] = Field(default_factory=list)


class Character(BaseModel):
    id: str
    name: str
    description: str = ""
    color_keys: list[str] = Field(default_factory=list)
    line_weight: Literal["thin", "medium", "bold"] = "medium"
    model_sheet_notes: str = ""


class CelPolicy(BaseModel):
    """How this shot is animated on the exposure sheet."""

    mode: Literal["full", "limited", "held_atmosphere"] = "limited"
    exposure: Literal["1s", "2s", "3s"] = "2s"
    hold_on_lyrics: bool = True
    smear_on_accents: bool = True
    smear_density: float = Field(0.5, ge=0.0, le=1.0)
    anticipation_frames: int = 2
    follow_through_frames: int = 3
    masters_pack: str = "classic_cel"
    key_on_beats: bool = True
    fx_vocab: list[str] = Field(default_factory=lambda: ["smear", "impact"])


class ShotIntent(BaseModel):
    """Explicit reason the shot exists — required on every Shot."""

    purpose: str = Field(..., min_length=1)
    emotional_beat: str = ""
    staging_goal: str = ""
    animation_priority: Literal["performance", "atmosphere", "impact", "transition"] = (
        "performance"
    )
    must_read_silhouette: bool = True
    hold_for_lyric: bool = False
    notes: str = ""

    @field_validator("purpose")
    @classmethod
    def purpose_not_blank(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("ShotIntent.purpose must be explicit (non-empty)")
        return cleaned


def _legacy_intent() -> ShotIntent:
    return ShotIntent(
        purpose="Legacy shot — set an explicit intent before craft approval",
        notes="default_intent_placeholder",
    )


class Shot(BaseModel):
    id: str
    index: int
    section: str
    start: float
    end: float
    duration: float
    intent: ShotIntent = Field(default_factory=_legacy_intent)
    description: str = ""
    camera: dict[str, Any] = Field(default_factory=dict)
    blocking: str = ""
    lens_mm: float = 35.0
    cel: CelPolicy = Field(default_factory=CelPolicy)
    characters: list[str] = Field(default_factory=list)
    color_script: str = ""
    approval: ApprovalState = ApprovalState.DRAFT
    notes: str = ""
    # Domain v2 optional links (backward compatible defaults)
    sequence_id: str | None = None
    layout_id: str | None = None
    timing_plan_id: str | None = None
    storyboard_panel_ids: list[str] = Field(default_factory=list)
    key_pose_ids: list[str] = Field(default_factory=list)
    revision_id: str | None = None
    lifecycle_state: ShotLifecycleState = ShotLifecycleState.INTENT
    animatic_approved: bool = False

    @model_validator(mode="before")
    @classmethod
    def ensure_intent(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        intent = data.get("intent")
        if intent is None or (isinstance(intent, dict) and not (intent.get("purpose") or "").strip()):
            purpose = (data.get("description") or data.get("notes") or "").strip()
            if not purpose:
                purpose = f"Section beat: {data.get('section', 'untitled')}"
            data = dict(data)
            data["intent"] = {
                "purpose": purpose,
                "emotional_beat": str(data.get("section", "")),
                "staging_goal": str(data.get("blocking", "")),
                "notes": "backfilled_from_legacy_shot_fields",
            }
        return data


class Story(BaseModel):
    title: str
    prompt: str
    logline: str = ""
    themes: list[str] = Field(default_factory=list)
    visual_temperature: str = "neutral"
    narrative_arc: list[str] = Field(default_factory=list)
    characters: list[Character] = Field(default_factory=list)
    motif_recurrence: list[str] = Field(default_factory=list)
    style_pack: str = "classic_cel"
    approval: ApprovalState = ApprovalState.DRAFT


class XSheetCell(BaseModel):
    frame: int
    layer: str
    exposure: Literal["key", "breakdown", "inbetween", "hold", "smear", "blank"] = "hold"
    pose_id: str | None = None
    notes: str = ""


class XSheet(BaseModel):
    shot_id: str
    fps: int = 24
    start_frame: int = 1
    end_frame: int
    layers: list[str] = Field(default_factory=lambda: ["character", "fx", "bg"])
    cells: list[XSheetCell] = Field(default_factory=list)
    timing_chart: dict[str, Any] = Field(default_factory=dict)
    approval: ApprovalState = ApprovalState.DRAFT


class StylePack(BaseModel):
    id: str
    name: str
    description: str
    masters_influence: list[str] = Field(default_factory=list)
    default_exposure: Literal["1s", "2s", "3s"] = "2s"
    hold_bias: float = 0.4
    smear_bias: float = 0.4
    camera_grammar: dict[str, Any] = Field(default_factory=dict)
    color_guidance: dict[str, Any] = Field(default_factory=dict)
    gp_line_settings: dict[str, Any] = Field(default_factory=dict)
    toon_settings: dict[str, Any] = Field(default_factory=dict)


class ProjectMeta(BaseModel):
    slug: str
    title: str
    prompt: str
    audio_path: str
    fps: int = 24
    resolution: tuple[int, int] = (1920, 1080)
    style_pack: str = "classic_cel"
    created_at: str = ""
    plan_approved: bool = False
    render_approved: bool = False
