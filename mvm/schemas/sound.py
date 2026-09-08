"""Sound-aware animation planning — cues visible on timing; motion never forced."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from mvm.schemas.domain import TimingSource, new_id, utc_now
from mvm.schemas.models import ApprovalState


class SoundCueKind(str, Enum):
    DIALOGUE = "dialogue"
    PHONEME = "phoneme"
    EMPHASIS = "emphasis"
    IMPACT = "impact"
    BREATH = "breath"
    MUSIC_BEAT = "music_beat"
    SILENCE = "silence"
    ENVIRONMENTAL = "environmental"
    # MIR / legacy-compatible
    ONSET = "onset"
    DOWNBEAT = "downbeat"
    LYRIC = "lyric"
    SECTION = "section"
    MANUAL = "manual"


class MotionResponse(str, Enum):
    """Authored response to a sound cue. Non-reaction and silence are first-class."""

    MOVE = "move"
    HOLD = "hold"
    SILENCE = "silence"
    NON_REACTION = "non_reaction"
    UNASSIGNED = "unassigned"


class SoundCue(BaseModel):
    """One sound event on the plan — not a motion command."""

    id: str = Field(default_factory=lambda: new_id("scue"))
    kind: SoundCueKind
    time_sec: float = Field(..., ge=0.0)
    end_time_sec: float | None = Field(default=None, ge=0.0)
    label: str = ""
    shot_id: str | None = None
    section: str | None = None
    # Optional phoneme / dialogue text payload
    text: str = ""
    source: TimingSource = TimingSource.AUTHORED
    suggested_by_operation: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def end_after_start(self) -> SoundCue:
        if self.end_time_sec is not None and self.end_time_sec < self.time_sec:
            raise ValueError("SoundCue.end_time_sec must be >= time_sec")
        return self


class SoundToMotionRelationship(BaseModel):
    """Optional link from a cue to an authored motion choice.

    Does not rewrite timing/keys automatically.
    """

    id: str = Field(default_factory=lambda: new_id("s2m"))
    cue_id: str
    response: MotionResponse = MotionResponse.UNASSIGNED
    layer: str = "character"
    notes: str = ""
    # Hard rule: relationships are advisory until a human craft step applies them
    applies_automatically: Literal[False] = False

    @model_validator(mode="after")
    def no_auto_apply(self) -> SoundToMotionRelationship:
        if self.applies_automatically is not False:
            raise ValueError(
                "SoundToMotionRelationship must not apply automatically — "
                "silence and non-reaction stay valid authored choices"
            )
        return self


class SoundPlan(BaseModel):
    """Shot-scoped sound plan for timing editors."""

    id: str
    shot_id: str
    fps: int = 24
    shot_start_sec: float = 0.0
    cues: list[SoundCue] = Field(default_factory=list)
    relationships: list[SoundToMotionRelationship] = Field(default_factory=list)
    # Never force every cue into visible movement
    force_every_cue_to_motion: Literal[False] = False
    approval: ApprovalState = ApprovalState.DRAFT
    revision_id: str | None = None
    at: str = Field(default_factory=utc_now)
    notes: str = (
        "Sound cues are visible while editing timing. "
        "Silence and non-reaction are valid authored choices."
    )

    @model_validator(mode="after")
    def never_force_motion(self) -> SoundPlan:
        if self.force_every_cue_to_motion is not False:
            raise ValueError(
                "SoundPlan.force_every_cue_to_motion must remain False"
            )
        return self
