"""Craft-first domain model — timing, keys, intent, review, revision, provenance.

Conventions match existing Pydantic schemas in ``models.py``.
Timing and key poses are authoring data; they are not rendered frame buffers.
AI/heuristic suggestions must attach to a ``Revision`` via ``ProvenanceRecord``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from mvm.schemas.models import ApprovalState, CelPolicy, ProjectMeta, ShotIntent


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActorKind(str, Enum):
    HUMAN = "human"
    HEURISTIC_AGENT = "heuristic_agent"
    SYSTEM = "system"


class TimingSource(str, Enum):
    """Who authored a timing decision — never collapse generated into authored."""

    AUTHORED = "authored"
    GENERATED = "generated"


class SpacingMode(str, Enum):
    """Explicit spacing policy. No silent bezier / auto-smooth."""

    LINEAR = "linear"
    STEPPED = "stepped"
    SLOW_IN = "slow_in"
    SLOW_OUT = "slow_out"
    SLOW_IN_OUT = "slow_in_out"
    CUSTOM = "custom"


# ShotIntent lives in models.py (attached to legacy Shot) — re-exported here.


class PoseArc(BaseModel):
    """Anticipation / follow-through around a key — unset fields mean 'not defined'.

    Use ``0`` for an explicit choice of no anticipation/follow-through.
    ``None`` means the author has not decided yet (suggestion blockers).
    """

    anticipation_frames: int | None = Field(
        default=None, ge=0, description="None=unset; 0=explicitly none"
    )
    follow_through_frames: int | None = Field(
        default=None, ge=0, description="None=unset; 0=explicitly none"
    )
    anticipation_notes: str = ""
    follow_through_notes: str = ""
    anticipation_pose_id: str | None = None
    follow_through_pose_id: str | None = None


class KeyPose(BaseModel):
    """Authored extreme / key drawing. Never an in-between."""

    id: str
    shot_id: str
    frame: int = Field(..., ge=1, description="TimingPlan frame index (not a render path)")
    label: str = ""
    description: str = ""
    # Action the drawing performs / intention it serves (craft authoring)
    action: str = ""
    intention: str = ""
    is_extreme: bool = False
    # True once explicitly marked as a key in the key-pose-first workflow
    marked_as_key: bool = False
    arc: PoseArc = Field(default_factory=PoseArc)
    layer: str = "character"
    asset_ref: str | None = None
    revision_id: str | None = None
    approval: ApprovalState = ApprovalState.DRAFT
    # Discriminator: keys stay keys
    role: Literal["key"] = "key"

    @field_validator("role")
    @classmethod
    def keys_only(cls, v: Literal["key"]) -> Literal["key"]:
        return "key"


class InBetweenSlot(BaseModel):
    """Planned in-between *slot* on the timing plan — not generated pixels."""

    frame: int = Field(..., ge=1)
    from_key_pose_id: str
    to_key_pose_id: str
    kind: Literal["breakdown", "inbetween"] = "inbetween"
    notes: str = ""
    # Suggestions may fill this; human must approve via Review/Revision
    suggested_by_operation: str | None = None
    revision_id: str | None = None
    source: TimingSource = TimingSource.AUTHORED
    # Parametric progress along the spacing curve at this frame (0..1), if known
    spacing_t: float | None = Field(default=None, ge=0.0, le=1.0)


class InBetweenSuggestion(BaseModel):
    """Non-destructive in-between suggestion — not applied until accept/partial accept."""

    id: str
    shot_id: str
    timing_plan_id: str
    from_key_pose_id: str
    to_key_pose_id: str
    status: Literal["preview", "accepted", "rejected", "partial", "blocked"] = "preview"
    spacing_mode: str = ""
    slots: list[InBetweenSlot] = Field(default_factory=list)
    accepted_frames: list[int] = Field(default_factory=list)
    rejected_frames: list[int] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    rationale: str = ""
    # Explicit: preview must not mutate TimingPlan until accept
    applied_to_timing: bool = False
    revision_id: str | None = None
    created_by: ActorKind = ActorKind.HEURISTIC_AGENT
    at: str = Field(default_factory=utc_now)


class ExposureHold(BaseModel):
    """Exposure / hold on the sheet: how long a drawing stays on screen.

    Independent from rendered frame files. Maps cleanly to X-sheet holds.
    """

    frame: int = Field(..., ge=1, description="First frame of this exposure")
    layer: str = "character"
    kind: Literal[
        "hold",
        "exposure",
        "smear",
        "blank",
        "pause",
        "anticipation",
        "impact",
    ] = "hold"
    duration_frames: int = Field(1, ge=1)
    key_pose_id: str | None = Field(
        default=None, description="If holding an authored key pose"
    )
    notes: str = ""
    source: TimingSource = TimingSource.AUTHORED
    suggested_by_operation: str | None = None


class SpacingCurve(BaseModel):
    """Named or custom spacing. Custom uses piecewise-linear control points only.

    Never auto-fits a smooth spline. Callers must set ``mode`` explicitly.
    """

    id: str
    mode: SpacingMode = SpacingMode.LINEAR
    # For stepped: number of discrete holds across the segment (excluding end key)
    step_count: int = Field(2, ge=1)
    # CUSTOM only: (input_t, output_progress) in [0,1], sorted by input_t
    control_points: list[tuple[float, float]] = Field(default_factory=list)
    source: TimingSource = TimingSource.AUTHORED
    suggested_by_operation: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def custom_needs_points(self) -> SpacingCurve:
        if self.mode == SpacingMode.CUSTOM and len(self.control_points) < 2:
            raise ValueError(
                "CUSTOM spacing requires >= 2 authored control points "
                "(no silent curve fitting)"
            )
        for t, v in self.control_points:
            if not (0.0 <= t <= 1.0 and 0.0 <= v <= 1.0):
                raise ValueError("Spacing control points must lie in [0,1]x[0,1]")
        return self


class TimingSegment(BaseModel):
    """Spacing between two key poses — inspectable without rendering."""

    id: str
    from_key_pose_id: str
    to_key_pose_id: str
    start_frame: int = Field(..., ge=1)
    end_frame: int = Field(..., ge=1)
    spacing: SpacingCurve
    pause_frames: list[int] = Field(default_factory=list)
    anticipation_frames: list[int] = Field(default_factory=list)
    impact_frames: list[int] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def end_after_start(self) -> TimingSegment:
        if self.end_frame < self.start_frame:
            raise ValueError("TimingSegment.end_frame must be >= start_frame")
        return self


class TimingAnnotation(BaseModel):
    """Human or generated note attached to timing (not artwork)."""

    id: str
    frame: int = Field(..., ge=1)
    end_frame: int | None = None
    kind: Literal[
        "note",
        "anticipation",
        "impact",
        "pause",
        "hold",
        "spacing",
        "exposure",
    ] = "note"
    text: str = ""
    source: TimingSource = TimingSource.AUTHORED
    suggested_by_operation: str | None = None


class TimingPlan(BaseModel):
    """Frame timing authority — stored independently from rendered frames."""

    id: str
    shot_id: str
    version: int = Field(1, ge=1)
    label: str = ""
    parent_timing_id: str | None = None
    fps: int = 24
    start_frame: int = 1
    end_frame: int = Field(..., ge=1)
    key_pose_ids: list[str] = Field(default_factory=list)
    exposures: list[ExposureHold] = Field(default_factory=list)
    inbetween_slots: list[InBetweenSlot] = Field(default_factory=list)
    smear_frames: list[int] = Field(default_factory=list)
    spacing_segments: list[TimingSegment] = Field(default_factory=list)
    annotations: list[TimingAnnotation] = Field(default_factory=list)
    cel: CelPolicy = Field(default_factory=CelPolicy)
    # Optional link to legacy X-sheet file id/path — not the pixels themselves
    legacy_xsheet_shot_id: str | None = None
    revision_id: str | None = None
    approval: ApprovalState = ApprovalState.DRAFT
    # Hard rule: engines must not silently smooth / auto-ease this plan
    allow_auto_smooth: Literal[False] = False

    @model_validator(mode="after")
    def end_after_start(self) -> TimingPlan:
        if self.end_frame < self.start_frame:
            raise ValueError("TimingPlan.end_frame must be >= start_frame")
        if self.allow_auto_smooth is not False:
            raise ValueError("TimingPlan.allow_auto_smooth must remain False")
        return self


class TimingTimelineEntry(BaseModel):
    """One inspectable frame of a timing plan — no pixels required."""

    frame: int
    roles: list[str] = Field(default_factory=list)
    key_pose_id: str | None = None
    exposure_kind: str | None = None
    inbetween: bool = False
    spacing_t: float | None = None
    spacing_mode: str | None = None
    source: TimingSource = TimingSource.AUTHORED
    annotation_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    # Sound-aware overlay (visible while editing timing; does not imply motion)
    sound_cue_ids: list[str] = Field(default_factory=list)
    sound_cue_kinds: list[str] = Field(default_factory=list)
    sound_labels: list[str] = Field(default_factory=list)
    motion_responses: list[str] = Field(default_factory=list)


class TimingTimeline(BaseModel):
    """Structured timing readout for review without rendering the shot."""

    timing_plan_id: str
    version: int
    shot_id: str
    fps: int
    start_frame: int
    end_frame: int
    entries: list[TimingTimelineEntry] = Field(default_factory=list)
    authored_count: int = 0
    generated_count: int = 0
    summary: str = ""
    # Sound overlay stats (cues visible ≠ forced motion)
    sound_cue_count: int = 0
    sound_linked_count: int = 0
    sound_non_reaction_count: int = 0
    force_every_cue_to_motion: Literal[False] = False


class TimingDiff(BaseModel):
    timing_a_id: str
    timing_b_id: str
    version_a: int
    version_b: int
    end_frame_a: int
    end_frame_b: int
    exposure_changes: list[dict[str, Any]] = Field(default_factory=list)
    segment_changes: list[dict[str, Any]] = Field(default_factory=list)
    annotation_changes: list[dict[str, Any]] = Field(default_factory=list)
    slot_frames_only_in_a: list[int] = Field(default_factory=list)
    slot_frames_only_in_b: list[int] = Field(default_factory=list)
    key_pose_ids_a: list[str] = Field(default_factory=list)
    key_pose_ids_b: list[str] = Field(default_factory=list)
    key_pose_ids_unchanged: bool = True
    summary: str = ""


class Layout(BaseModel):
    """3D / scene layout for a shot (camera, set, placement) — not character keys."""

    id: str
    shot_id: str
    description: str = ""
    camera: dict[str, Any] = Field(default_factory=dict)
    lens_mm: float = 35.0
    set_notes: str = ""
    character_placements: list[dict[str, Any]] = Field(default_factory=list)
    revision_id: str | None = None


class StoryboardPanel(BaseModel):
    """Storyboard drawing/caption — artwork identity separate from animatic timing."""

    id: str
    shot_id: str
    index: int
    caption: str = ""
    intent_summary: str = ""
    thumbnail_ref: str | None = None
    # Default suggestion only; animatic versions own authoritative duration.
    default_duration_frames: int = Field(24, ge=1)
    revision_id: str | None = None


class AnimaticPanelRef(BaseModel):
    """Panel placement on an animatic version — timing only, not artwork bytes."""

    panel_id: str
    order: int = Field(..., ge=0)
    duration_frames: int = Field(24, ge=1)
    notes: str = ""


class Animatic(BaseModel):
    """First-class rough-timing artifact (not a disposable preview)."""

    id: str
    shot_id: str
    version: int = Field(1, ge=1)
    label: str = ""
    fps: int = 24
    panels: list[AnimaticPanelRef] = Field(default_factory=list)
    parent_animatic_id: str | None = None
    revision_id: str | None = None
    approved: bool = False
    # Explicit: duration/order edits must not rewrite panel artwork fields
    timing_only: Literal[True] = True

    @property
    def total_duration_frames(self) -> int:
        return sum(p.duration_frames for p in self.panels)

    @property
    def total_duration_sec(self) -> float:
        return self.total_duration_frames / float(self.fps) if self.fps else 0.0


class AnimaticPreviewFrame(BaseModel):
    """Rough animatic preview beat — structured timeline, not rendered polish."""

    order: int
    panel_id: str
    caption: str = ""
    intent_summary: str = ""
    start_frame: int
    end_frame: int
    duration_frames: int
    start_sec: float
    end_sec: float


class AnimaticDiff(BaseModel):
    animatic_a_id: str
    animatic_b_id: str
    version_a: int
    version_b: int
    order_changed: bool
    order_a: list[str]
    order_b: list[str]
    duration_changes: list[dict[str, Any]] = Field(default_factory=list)
    panels_only_in_a: list[str] = Field(default_factory=list)
    panels_only_in_b: list[str] = Field(default_factory=list)
    total_frames_a: int
    total_frames_b: int
    total_sec_a: float
    total_sec_b: float
    summary: str = ""


class AudioCue(BaseModel):
    id: str
    time_sec: float = Field(..., ge=0.0)
    kind: Literal["beat", "onset", "downbeat", "lyric", "section", "manual"] = "beat"
    label: str = ""
    shot_id: str | None = None
    section: str | None = None


class Reference(BaseModel):
    id: str
    kind: Literal["model_sheet", "style", "film_still", "audio", "layout", "other"] = (
        "other"
    )
    path_or_uri: str = ""
    notes: str = ""
    shot_id: str | None = None
    sequence_id: str | None = None


class ProvenanceAcceptance(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProvenanceRecord(BaseModel):
    """Attribution for any AI/heuristic/system suggestion or transform.

    Every meaningful change should leave an inspectable record. Generated work
    must stay visibly labeled. Guardrail breaches are refused, not hidden.
    """

    id: str
    operation: str = Field(
        ...,
        min_length=1,
        description="Stable operation id, e.g. agents.plan, cel.xsheet_rebuild",
    )
    revision_id: str
    at: str = Field(default_factory=utc_now)
    actor: ActorKind = ActorKind.SYSTEM
    # Human-readable creator (may match actor or a named reviewer/tool)
    creator: str = ""
    summary: str = ""
    # Source refs (files, cue ids, notebook media, URLs) — required for asset swaps
    source_references: list[str] = Field(default_factory=list)
    # Alias surface for "model or assistant operation"
    model_or_assistant_operation: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    # Explicit synonym retained for callers/docs
    input_parameters: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    generated_alternatives: list[dict[str, Any]] = Field(default_factory=list)
    acceptance_state: ProvenanceAcceptance = ProvenanceAcceptance.PENDING
    human_edits_after_generation: list[dict[str, Any]] = Field(default_factory=list)
    final_approval: bool = False
    final_approval_by: str | None = None
    final_approval_at: str | None = None
    # Generated suggestions must be visibly labeled in UI/exports
    visibly_labeled_generated: bool = False
    reversible: bool = True
    # Snapshot of guardrail checks at write time
    guardrails: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_and_label(self) -> ProvenanceRecord:
        if not self.creator:
            self.creator = self.actor.value
        if not self.model_or_assistant_operation:
            self.model_or_assistant_operation = self.operation
        if not self.input_parameters and self.inputs:
            self.input_parameters = dict(self.inputs)
        elif self.input_parameters and not self.inputs:
            self.inputs = dict(self.input_parameters)
        if self.actor in (ActorKind.HEURISTIC_AGENT,) or self.visibly_labeled_generated:
            # Heuristic/model output must stay labeled
            if self.actor == ActorKind.HEURISTIC_AGENT:
                self.visibly_labeled_generated = True
        if self.final_approval and self.acceptance_state == ProvenanceAcceptance.PENDING:
            self.acceptance_state = ProvenanceAcceptance.ACCEPTED
        return self


class Review(BaseModel):
    """Human judgment of a revision — supports reject + restore."""

    id: str
    target_type: Literal[
        "project", "sequence", "shot", "timing_plan", "storyboard", "layout"
    ]
    target_id: str
    revision_id: str
    state: ApprovalState
    reviewer: str = "human"
    comment: str = ""
    at: str = Field(default_factory=utc_now)
    # On reject, optionally restore a prior accepted revision
    restore_revision_id: str | None = None

    @model_validator(mode="after")
    def reject_may_restore(self) -> Review:
        if (
            self.state == ApprovalState.REJECTED
            and self.restore_revision_id is None
            and not self.comment
        ):
            # Allow reject without restore, but encourage comment via soft rule:
            # hard-require comment on reject for auditability
            raise ValueError("Rejected reviews require a comment (and may set restore_revision_id)")
        return self


class Revision(BaseModel):
    """Versioned snapshot of a domain target — enables restore after rejection."""

    id: str
    parent_id: str | None = None
    target_type: Literal[
        "project",
        "sequence",
        "shot",
        "timing_plan",
        "storyboard",
        "layout",
        "key_pose",
        "notebook",
    ]
    target_id: str
    at: str = Field(default_factory=utc_now)
    summary: str = ""
    snapshot: dict[str, Any] = Field(default_factory=dict)
    created_by: ActorKind = ActorKind.SYSTEM
    provenance_ids: list[str] = Field(default_factory=list)


class Sequence(BaseModel):
    """Ordered group of shots (often one musical section)."""

    id: str
    index: int
    name: str
    section: str = ""
    start: float = 0.0
    end: float = 0.0
    shot_ids: list[str] = Field(default_factory=list)
    approval: ApprovalState = ApprovalState.DRAFT
    revision_id: str | None = None


class Project(BaseModel):
    """Stable project aggregate (wraps existing ProjectMeta)."""

    schema_version: int = 2
    meta: ProjectMeta
    sequence_ids: list[str] = Field(default_factory=list)
    active_revision_id: str | None = None
    reference_ids: list[str] = Field(default_factory=list)
    audio_cue_ids: list[str] = Field(default_factory=list)


class ShotCraft(BaseModel):
    """Full craft-facing shot record (extends legacy shot fields + intent).

    Prefer this for new domain code. Legacy ``Shot`` in models.py remains for
    on-disk backward compatibility and gains an ``intent`` field.
    """

    id: str
    index: int
    sequence_id: str | None = None
    section: str
    start: float
    end: float
    duration: float
    intent: ShotIntent
    description: str = ""
    camera: dict[str, Any] = Field(default_factory=dict)
    blocking: str = ""
    lens_mm: float = 35.0
    cel: CelPolicy = Field(default_factory=CelPolicy)
    characters: list[str] = Field(default_factory=list)
    color_script: str = ""
    layout_id: str | None = None
    timing_plan_id: str | None = None
    storyboard_panel_ids: list[str] = Field(default_factory=list)
    key_pose_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    approval: ApprovalState = ApprovalState.DRAFT
    revision_id: str | None = None
    notes: str = ""

    @model_validator(mode="after")
    def intent_required(self) -> ShotCraft:
        # purpose validator already enforces non-empty
        if not self.intent.purpose.strip():
            raise ValueError("Every shot must have an explicit ShotIntent.purpose")
        return self


def make_revision(
    *,
    target_type: str,
    target_id: str,
    snapshot: dict[str, Any],
    summary: str = "",
    parent_id: str | None = None,
    created_by: ActorKind = ActorKind.SYSTEM,
    provenance_ids: list[str] | None = None,
) -> Revision:
    return Revision(
        id=new_id("rev"),
        parent_id=parent_id,
        target_type=target_type,  # type: ignore[arg-type]
        target_id=target_id,
        summary=summary,
        snapshot=snapshot,
        created_by=created_by,
        provenance_ids=provenance_ids or [],
    )


def make_provenance(
    *,
    operation: str,
    revision_id: str,
    actor: ActorKind = ActorKind.HEURISTIC_AGENT,
    summary: str = "",
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    creator: str = "",
    source_references: list[str] | None = None,
    generated_alternatives: list[dict[str, Any]] | None = None,
    visibly_labeled_generated: bool | None = None,
    guardrails: dict[str, bool] | None = None,
    acceptance_state: ProvenanceAcceptance | None = None,
) -> ProvenanceRecord:
    labeled = visibly_labeled_generated
    if labeled is None:
        labeled = actor == ActorKind.HEURISTIC_AGENT
    return ProvenanceRecord(
        id=new_id("prov"),
        operation=operation,
        revision_id=revision_id,
        actor=actor,
        creator=creator or actor.value,
        summary=summary,
        inputs=inputs or {},
        input_parameters=dict(inputs or {}),
        outputs=outputs or {},
        source_references=list(source_references or []),
        model_or_assistant_operation=operation,
        generated_alternatives=list(generated_alternatives or []),
        visibly_labeled_generated=bool(labeled),
        guardrails=dict(guardrails or {}),
        acceptance_state=acceptance_state or ProvenanceAcceptance.PENDING,
    )


def restore_snapshot(revision: Revision) -> dict[str, Any]:
    """Return a deep copy of the revision snapshot for restoration after rejection."""
    import copy

    return copy.deepcopy(revision.snapshot)
