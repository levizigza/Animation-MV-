"""Inspectable timing timeline — no shot render required."""

from __future__ import annotations

from mvm.schemas.domain import (
    TimingPlan,
    TimingSource,
    TimingTimeline,
    TimingTimelineEntry,
)
from mvm.timing.curves import progress_at


def build_timeline(plan: TimingPlan) -> TimingTimeline:
    """Expand a TimingPlan into per-frame roles for review without rendering."""
    by_frame: dict[int, TimingTimelineEntry] = {}

    def entry(frame: int) -> TimingTimelineEntry:
        if frame not in by_frame:
            by_frame[frame] = TimingTimelineEntry(frame=frame)
        return by_frame[frame]

    for exp in plan.exposures:
        for offset in range(exp.duration_frames):
            f = exp.frame + offset
            if f < plan.start_frame or f > plan.end_frame:
                continue
            e = entry(f)
            if exp.kind not in e.roles:
                e.roles.append(exp.kind)
            e.exposure_kind = exp.kind
            if exp.key_pose_id:
                e.key_pose_id = exp.key_pose_id
            if exp.notes and not e.notes:
                e.notes = exp.notes
            # Generated exposure wins the source flag if any generated touch this frame
            if exp.source == TimingSource.GENERATED:
                e.source = TimingSource.GENERATED
            elif e.source != TimingSource.GENERATED:
                e.source = exp.source

    for slot in plan.inbetween_slots:
        e = entry(slot.frame)
        e.inbetween = True
        if "inbetween" not in e.roles:
            e.roles.append(slot.kind)
        e.spacing_t = slot.spacing_t
        if slot.source == TimingSource.GENERATED:
            e.source = TimingSource.GENERATED
        elif e.source != TimingSource.GENERATED and slot.source == TimingSource.AUTHORED:
            e.source = TimingSource.AUTHORED
        if slot.notes and not e.notes:
            e.notes = slot.notes

    for seg in plan.spacing_segments:
        span = max(1, seg.end_frame - seg.start_frame)
        for f in range(seg.start_frame, seg.end_frame + 1):
            e = entry(f)
            if e.spacing_mode is None:
                e.spacing_mode = seg.spacing.mode.value
            if e.spacing_t is None and f not in (
                set(seg.pause_frames)
                | set(seg.anticipation_frames)
                | set(seg.impact_frames)
            ):
                t = (f - seg.start_frame) / float(span)
                e.spacing_t = progress_at(seg.spacing, t)
            if seg.spacing.source == TimingSource.GENERATED:
                e.source = TimingSource.GENERATED
        for f in seg.pause_frames:
            e = entry(f)
            if "pause" not in e.roles:
                e.roles.append("pause")
        for f in seg.anticipation_frames:
            e = entry(f)
            if "anticipation" not in e.roles:
                e.roles.append("anticipation")
        for f in seg.impact_frames:
            e = entry(f)
            if "impact" not in e.roles:
                e.roles.append("impact")

    for ann in plan.annotations:
        end = ann.end_frame or ann.frame
        for f in range(ann.frame, end + 1):
            e = entry(f)
            e.annotation_ids.append(ann.id)
            if ann.kind not in e.roles:
                e.roles.append(ann.kind)
            if ann.source == TimingSource.GENERATED:
                e.source = TimingSource.GENERATED

    for f in plan.smear_frames:
        e = entry(f)
        if "smear" not in e.roles:
            e.roles.append("smear")

    entries = [by_frame[f] for f in sorted(by_frame)]
    authored = sum(1 for e in entries if e.source == TimingSource.AUTHORED)
    generated = sum(1 for e in entries if e.source == TimingSource.GENERATED)
    summary = (
        f"Timing {plan.id} v{plan.version}: frames {plan.start_frame}-{plan.end_frame}, "
        f"{len(entries)} marked, authored={authored}, generated={generated}, "
        f"auto_smooth={plan.allow_auto_smooth}"
    )
    return TimingTimeline(
        timing_plan_id=plan.id,
        version=plan.version,
        shot_id=plan.shot_id,
        fps=plan.fps,
        start_frame=plan.start_frame,
        end_frame=plan.end_frame,
        entries=entries,
        authored_count=authored,
        generated_count=generated,
        summary=summary,
    )
