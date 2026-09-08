"""Backward-compatible upgrades from legacy project/shot JSON to domain v2."""

from __future__ import annotations

from typing import Any

from mvm.schemas.domain import (
    ActorKind,
    AudioCue,
    ExposureHold,
    InBetweenSlot,
    KeyPose,
    Layout,
    Project,
    ProvenanceRecord,
    Sequence,
    ShotCraft,
    ShotIntent,
    StoryboardPanel,
    TimingPlan,
    TimingSource,
    make_provenance,
    make_revision,
    new_id,
    utc_now,
)
from mvm.schemas.models import ApprovalState, CelPolicy, ProjectMeta, Shot, XSheet


def intent_from_legacy_shot(data: dict[str, Any] | Shot) -> ShotIntent:
    if isinstance(data, Shot):
        raw = data.model_dump(mode="json")
    else:
        raw = data
    if "intent" in raw and isinstance(raw["intent"], dict) and raw["intent"].get("purpose"):
        return ShotIntent.model_validate(raw["intent"])
    purpose = (raw.get("description") or raw.get("notes") or "").strip()
    if not purpose:
        purpose = f"Section beat: {raw.get('section', 'untitled')} — legacy import"
    priority = "atmosphere"
    mode = (raw.get("cel") or {}).get("mode") if isinstance(raw.get("cel"), dict) else None
    if mode == "full":
        priority = "impact"
    elif mode == "limited":
        priority = "performance"
    return ShotIntent(
        purpose=purpose,
        emotional_beat=str(raw.get("section", "")),
        staging_goal=str(raw.get("blocking", "")),
        animation_priority=priority,  # type: ignore[arg-type]
        notes="Migrated from legacy Shot without explicit intent",
    )


def upgrade_shot_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure a legacy shot dict validates as current Shot (with intent)."""
    out = dict(data)
    if "intent" not in out or not (out.get("intent") or {}).get("purpose"):
        out["intent"] = intent_from_legacy_shot(out).model_dump(mode="json")
    return out


def shot_to_craft(shot: Shot, *, sequence_id: str | None = None) -> ShotCraft:
    intent = shot.intent if shot.intent.purpose.strip() else intent_from_legacy_shot(shot)
    return ShotCraft(
        id=shot.id,
        index=shot.index,
        sequence_id=sequence_id,
        section=shot.section,
        start=shot.start,
        end=shot.end,
        duration=shot.duration,
        intent=intent,
        description=shot.description,
        camera=shot.camera,
        blocking=shot.blocking,
        lens_mm=shot.lens_mm,
        cel=shot.cel,
        characters=shot.characters,
        color_script=shot.color_script,
        layout_id=shot.layout_id,
        timing_plan_id=shot.timing_plan_id,
        storyboard_panel_ids=list(shot.storyboard_panel_ids),
        key_pose_ids=list(shot.key_pose_ids),
        approval=shot.approval,
        revision_id=shot.revision_id,
        notes=shot.notes,
    )


def timing_plan_from_xsheet(xsheet: XSheet, shot: Shot) -> tuple[TimingPlan, list[KeyPose]]:
    """Derive TimingPlan + KeyPoses from legacy X-sheet (keys ≠ inbetweens)."""
    keys: list[KeyPose] = []
    exposures: list[ExposureHold] = []
    slots: list[InBetweenSlot] = []
    smear_frames: list[int] = []
    last_key_id: str | None = None

    char_cells = sorted(
        (c for c in xsheet.cells if c.layer == "character"),
        key=lambda c: c.frame,
    )
    for cell in char_cells:
        if cell.exposure == "key":
            kid = cell.pose_id or new_id("pose")
            keys.append(
                KeyPose(
                    id=kid,
                    shot_id=shot.id,
                    frame=cell.frame,
                    label=cell.notes or kid,
                    description=cell.notes,
                    is_extreme=cell.frame in (xsheet.start_frame, xsheet.end_frame),
                    layer=cell.layer,
                )
            )
            exposures.append(
                ExposureHold(
                    frame=cell.frame,
                    layer=cell.layer,
                    kind="exposure",
                    duration_frames=1,
                    key_pose_id=kid,
                    notes="key exposure",
                    source=TimingSource.AUTHORED,
                )
            )
            last_key_id = kid
        elif cell.exposure == "hold":
            exposures.append(
                ExposureHold(
                    frame=cell.frame,
                    layer=cell.layer,
                    kind="hold",
                    duration_frames=1,
                    key_pose_id=last_key_id,
                    source=TimingSource.AUTHORED,
                )
            )
        elif cell.exposure in ("breakdown", "inbetween") and last_key_id:
            # slot only — no fabricated pose asset; marked generated from legacy sheet
            slots.append(
                InBetweenSlot(
                    frame=cell.frame,
                    from_key_pose_id=last_key_id,
                    to_key_pose_id=last_key_id,
                    kind="breakdown" if cell.exposure == "breakdown" else "inbetween",
                    notes=cell.notes,
                    suggested_by_operation="compat.timing_plan_from_xsheet",
                    source=TimingSource.GENERATED,
                )
            )
        elif cell.exposure == "smear":
            smear_frames.append(cell.frame)
            exposures.append(
                ExposureHold(
                    frame=cell.frame,
                    layer=cell.layer,
                    kind="smear",
                    duration_frames=1,
                    notes=cell.notes,
                    source=TimingSource.AUTHORED,
                )
            )

    plan = TimingPlan(
        id=new_id("timing"),
        shot_id=shot.id,
        fps=xsheet.fps,
        start_frame=xsheet.start_frame,
        end_frame=xsheet.end_frame,
        key_pose_ids=[k.id for k in keys],
        exposures=exposures,
        inbetween_slots=slots,
        smear_frames=smear_frames,
        cel=shot.cel,
        legacy_xsheet_shot_id=xsheet.shot_id,
        approval=xsheet.approval,
    )
    return plan, keys


def project_from_meta(
    meta: ProjectMeta,
    *,
    sequences: list[Sequence] | None = None,
) -> Project:
    seqs = sequences or []
    return Project(
        schema_version=2,
        meta=meta,
        sequence_ids=[s.id for s in seqs],
    )


def sequences_from_shots(shots: list[Shot]) -> list[Sequence]:
    """Group legacy flat shots into sequences by section name (stable, reversible)."""
    order: list[str] = []
    buckets: dict[str, list[Shot]] = {}
    for sh in sorted(shots, key=lambda s: s.index):
        key = sh.section or "untitled"
        if key not in buckets:
            order.append(key)
            buckets[key] = []
        buckets[key].append(sh)
    sequences: list[Sequence] = []
    for i, name in enumerate(order):
        group = buckets[name]
        sequences.append(
            Sequence(
                id=new_id("seq"),
                index=i + 1,
                name=name,
                section=name,
                start=group[0].start,
                end=group[-1].end,
                shot_ids=[s.id for s in group],
                approval=ApprovalState.DRAFT,
            )
        )
    return sequences


def attribute_suggestion(
    *,
    operation: str,
    target_type: str,
    target_id: str,
    snapshot: dict[str, Any],
    summary: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    parent_revision_id: str | None = None,
) -> tuple[Revision, ProvenanceRecord]:
    """Create a Revision + ProvenanceRecord for any AI/heuristic suggestion."""
    rev = make_revision(
        target_type=target_type,
        target_id=target_id,
        snapshot=snapshot,
        summary=summary,
        parent_id=parent_revision_id,
        created_by=ActorKind.HEURISTIC_AGENT,
    )
    prov = make_provenance(
        operation=operation,
        revision_id=rev.id,
        actor=ActorKind.HEURISTIC_AGENT,
        summary=summary,
        inputs=inputs,
        outputs=outputs,
    )
    rev.provenance_ids.append(prov.id)
    return rev, prov


def layout_from_shot(shot: Shot) -> Layout:
    return Layout(
        id=new_id("layout"),
        shot_id=shot.id,
        description=shot.blocking or shot.description,
        camera=dict(shot.camera),
        lens_mm=shot.lens_mm,
        set_notes=shot.color_script,
    )


def panel_from_shot(shot: Shot, index: int | None = None) -> StoryboardPanel:
    return StoryboardPanel(
        id=new_id("panel"),
        shot_id=shot.id,
        index=index if index is not None else shot.index,
        caption=shot.description,
        intent_summary=shot.intent.purpose if shot.intent else "",
        default_duration_frames=24,
    )


def audio_cues_from_beatmap_section(
    *,
    shot_id: str,
    beat_times: list[float],
    start: float,
    end: float,
) -> list[AudioCue]:
    cues: list[AudioCue] = []
    for t in beat_times:
        if start <= t < end:
            cues.append(
                AudioCue(
                    id=new_id("cue"),
                    time_sec=t,
                    kind="beat",
                    label="beat",
                    shot_id=shot_id,
                )
            )
    return cues
