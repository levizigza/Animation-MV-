"""Craft-first timing workflow: holds, spacing, annotations, versions, export.

Timing edits never mutate KeyPose content. Generated interpolation is tagged
and reversible. Auto-smooth is forbidden.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.domain import (
    ActorKind,
    ExposureHold,
    InBetweenSlot,
    KeyPose,
    SpacingCurve,
    SpacingMode,
    TimingAnnotation,
    TimingDiff,
    TimingPlan,
    TimingSegment,
    TimingSource,
    make_provenance,
    new_id,
)
from mvm.timing.curves import progress_at, reconstruct_custom_from_samples, sample_progress
from mvm.timing.timeline import build_timeline


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_timing_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "timing").mkdir(parents=True, exist_ok=True)
    (root / "key_poses").mkdir(parents=True, exist_ok=True)
    (root / "timing_exports").mkdir(parents=True, exist_ok=True)


def save_timing_plan(root: Path, plan: TimingPlan) -> Path:
    ensure_timing_dirs(root)
    if plan.allow_auto_smooth is not False:
        raise ValueError("Refusing to save TimingPlan with allow_auto_smooth enabled")
    path = root / "timing" / f"{plan.id}.json"
    _write(path, plan)
    ptr = root / "timing" / f"shot_{plan.shot_id}_latest.json"
    _write(
        ptr,
        {
            "timing_plan_id": plan.id,
            "version": plan.version,
            "shot_id": plan.shot_id,
        },
    )
    return path


def load_timing_plan(root: Path, timing_id: str) -> TimingPlan:
    return TimingPlan.model_validate(_read(root / "timing" / f"{timing_id}.json"))


def load_key_pose(root: Path, pose_id: str) -> KeyPose:
    return KeyPose.model_validate(_read(root / "key_poses" / f"{pose_id}.json"))


def save_key_pose(root: Path, pose: KeyPose) -> Path:
    ensure_timing_dirs(root)
    path = root / "key_poses" / f"{pose.id}.json"
    _write(path, pose)
    return path


def list_timing_versions(root: Path, shot_id: str) -> list[TimingPlan]:
    d = root / "timing"
    if not d.exists():
        return []
    out: list[TimingPlan] = []
    for p in d.glob("*.json"):
        if p.name.startswith("shot_") and p.name.endswith("_latest.json"):
            continue
        data = _read(p)
        if data.get("shot_id") == shot_id and "exposures" in data:
            out.append(TimingPlan.model_validate(data))
    return sorted(out, key=lambda t: (t.version, t.id))


def create_timing_plan(
    root: Path,
    *,
    shot_id: str,
    end_frame: int,
    fps: int = 24,
    label: str = "",
    key_poses: Iterable[KeyPose] | None = None,
) -> TimingPlan:
    """Create an empty authored timing plan (keys optional, stored separately)."""
    ensure_timing_dirs(root)
    poses = list(key_poses or [])
    for pose in poses:
        if pose.shot_id != shot_id:
            raise ValueError("KeyPose.shot_id must match timing shot_id")
        save_key_pose(root, pose)
    plan = TimingPlan(
        id=new_id("timing"),
        shot_id=shot_id,
        version=1,
        label=label or "timing v1",
        fps=fps,
        start_frame=1,
        end_frame=end_frame,
        key_pose_ids=[p.id for p in poses],
        allow_auto_smooth=False,
    )
    rev, prov = attribute_suggestion(
        operation="human.timing_create",
        target_type="timing_plan",
        target_id=plan.id,
        snapshot=plan.model_dump(mode="json"),
        summary=f"Created timing plan for {shot_id}",
        outputs={"version": 1, "allow_auto_smooth": False},
    )
    plan.revision_id = rev.id
    save_timing_plan(root, plan)
    save_revision(root, rev)
    save_provenance(root, prov)
    return plan


def add_hold(
    root: Path,
    timing_id: str,
    *,
    frame: int,
    duration_frames: int = 1,
    key_pose_id: str | None = None,
    kind: str = "hold",
    notes: str = "",
) -> TimingPlan:
    """Add an authored exposure/hold/pause/anticipation/impact — does not touch KeyPose JSON."""
    plan = load_timing_plan(root, timing_id)
    before_keys = list(plan.key_pose_ids)
    exp = ExposureHold(
        frame=frame,
        kind=kind,  # type: ignore[arg-type]
        duration_frames=duration_frames,
        key_pose_id=key_pose_id,
        notes=notes,
        source=TimingSource.AUTHORED,
    )
    plan = plan.model_copy(deep=True)
    plan.exposures = list(plan.exposures) + [exp]
    if plan.key_pose_ids != before_keys:
        raise RuntimeError("Timing edit mutated key_pose_ids unexpectedly")
    # Verify linked key pose content unchanged if present on disk
    if key_pose_id:
        pose_path = root / "key_poses" / f"{key_pose_id}.json"
        if pose_path.exists():
            before = pose_path.read_text(encoding="utf-8")
            save_timing_plan(root, plan)
            after = pose_path.read_text(encoding="utf-8")
            if before != after:
                raise RuntimeError("Timing edit altered KeyPose content")
            return plan
    save_timing_plan(root, plan)
    return plan


def add_annotation(
    root: Path,
    timing_id: str,
    *,
    frame: int,
    text: str,
    kind: str = "note",
    end_frame: int | None = None,
) -> TimingPlan:
    plan = load_timing_plan(root, timing_id).model_copy(deep=True)
    ann = TimingAnnotation(
        id=new_id("tann"),
        frame=frame,
        end_frame=end_frame,
        kind=kind,  # type: ignore[arg-type]
        text=text,
        source=TimingSource.AUTHORED,
    )
    plan.annotations = list(plan.annotations) + [ann]
    save_timing_plan(root, plan)
    return plan


def set_spacing_segment(
    root: Path,
    timing_id: str,
    *,
    from_key_pose_id: str,
    to_key_pose_id: str,
    start_frame: int,
    end_frame: int,
    mode: SpacingMode,
    step_count: int = 2,
    control_points: list[tuple[float, float]] | None = None,
    pause_frames: list[int] | None = None,
    anticipation_frames: list[int] | None = None,
    impact_frames: list[int] | None = None,
    notes: str = "",
    source: TimingSource = TimingSource.AUTHORED,
    suggested_by_operation: str | None = None,
) -> TimingPlan:
    """Attach an explicit spacing segment. Never auto-smooths."""
    plan = load_timing_plan(root, timing_id).model_copy(deep=True)
    curve = SpacingCurve(
        id=new_id("curve"),
        mode=mode,
        step_count=step_count,
        control_points=list(control_points or []),
        source=source,
        suggested_by_operation=suggested_by_operation,
        notes=notes,
    )
    seg = TimingSegment(
        id=new_id("tseg"),
        from_key_pose_id=from_key_pose_id,
        to_key_pose_id=to_key_pose_id,
        start_frame=start_frame,
        end_frame=end_frame,
        spacing=curve,
        pause_frames=list(pause_frames or []),
        anticipation_frames=list(anticipation_frames or []),
        impact_frames=list(impact_frames or []),
        notes=notes,
    )
    # Replace segment with same key pair if present
    plan.spacing_segments = [
        s
        for s in plan.spacing_segments
        if not (
            s.from_key_pose_id == from_key_pose_id and s.to_key_pose_id == to_key_pose_id
        )
    ] + [seg]
    save_timing_plan(root, plan)
    return plan


def apply_spacing_interpolation(
    root: Path,
    timing_id: str,
    segment_id: str,
    *,
    operation: str = "timing.generate_spacing_slots",
) -> dict[str, Any]:
    """Generate in-between *slots* from an explicit spacing segment.

    Does not alter KeyPose files. Tags slots as generated. Reversible via
    ``revert_generated_interpolation``. Never applies auto-smooth.
    """
    plan = load_timing_plan(root, timing_id)
    seg = next((s for s in plan.spacing_segments if s.id == segment_id), None)
    if seg is None:
        return {"ok": False, "reason": f"Segment {segment_id} not found"}

    key_snapshots: dict[str, dict[str, Any]] = {}
    for kid in (seg.from_key_pose_id, seg.to_key_pose_id):
        path = root / "key_poses" / f"{kid}.json"
        if path.exists():
            key_snapshots[kid] = _read(path)

    before = plan.model_dump(mode="json")
    # Always keep authored slots. Replace only generated slots inside this span.
    authored_slots = [
        s for s in plan.inbetween_slots if s.source == TimingSource.AUTHORED
    ]
    generated_outside = [
        s
        for s in plan.inbetween_slots
        if s.source == TimingSource.GENERATED
        and not (seg.start_frame < s.frame < seg.end_frame)
    ]
    generated: list[InBetweenSlot] = []
    span = seg.end_frame - seg.start_frame
    if span < 2:
        return {"ok": False, "reason": "Segment too short for in-betweens"}

    skip = set(seg.pause_frames) | set(seg.anticipation_frames) | set(seg.impact_frames)
    authored_frames = {s.frame for s in authored_slots}
    for f in range(seg.start_frame + 1, seg.end_frame):
        if f in skip or f in authored_frames:
            continue
        t = (f - seg.start_frame) / float(span)
        progress = progress_at(seg.spacing, t)
        generated.append(
            InBetweenSlot(
                frame=f,
                from_key_pose_id=seg.from_key_pose_id,
                to_key_pose_id=seg.to_key_pose_id,
                kind="inbetween",
                notes=(
                    f"Generated spacing {seg.spacing.mode.value} t={t:.4f} "
                    f"progress={progress:.4f} (not auto-smoothed)"
                ),
                suggested_by_operation=operation,
                source=TimingSource.GENERATED,
                spacing_t=progress,
            )
        )

    updated = plan.model_copy(deep=True)
    updated.inbetween_slots = authored_slots + generated_outside + generated

    rev, prov = attribute_suggestion(
        operation=operation,
        target_type="timing_plan",
        target_id=plan.id,
        snapshot={
            "before": before,
            "after": updated.model_dump(mode="json"),
            "segment_id": segment_id,
            "interpolation_note": (
                "Generated in-between slots from explicit SpacingMode only. "
                "No silent smoothing. Key poses unchanged."
            ),
            "key_pose_snapshots": key_snapshots,
        },
        summary=(
            f"Generated {len(generated)} spacing slots on {plan.id} "
            f"mode={seg.spacing.mode.value}"
        ),
        inputs={"segment_id": segment_id, "mode": seg.spacing.mode.value},
        outputs={"generated_slots": len(generated)},
    )
    updated.revision_id = rev.id
    save_timing_plan(root, updated)
    save_revision(root, rev)
    save_provenance(root, prov)

    # Prove keys untouched
    for kid, snap in key_snapshots.items():
        current = _read(root / "key_poses" / f"{kid}.json")
        if current != snap:
            raise RuntimeError(f"Interpolation altered KeyPose {kid}")

    return {
        "ok": True,
        "timing_plan": updated,
        "generated_count": len(generated),
        "revision_id": rev.id,
        "provenance_id": prov.id,
    }


def revert_generated_interpolation(
    root: Path,
    timing_id: str,
    *,
    revision_id: str | None = None,
) -> dict[str, Any]:
    """Remove generated slots or restore from a revision snapshot (reversible)."""
    plan = load_timing_plan(root, timing_id)
    if revision_id:
        rev_path = root / "revisions" / f"{revision_id}.json"
        rev = json.loads(rev_path.read_text(encoding="utf-8"))
        before = rev.get("snapshot", {}).get("before")
        if not before:
            return {"ok": False, "reason": "Revision has no before snapshot"}
        restored = TimingPlan.model_validate(before)
        save_timing_plan(root, restored)
        prov = make_provenance(
            operation="human.timing_revert_interpolation",
            revision_id=revision_id,
            actor=ActorKind.HUMAN,
            summary=f"Restored timing {timing_id} from revision {revision_id}",
        )
        save_provenance(root, prov)
        return {"ok": True, "timing_plan": restored, "mode": "snapshot_restore"}

    cleaned = plan.model_copy(deep=True)
    cleaned.inbetween_slots = [
        s for s in plan.inbetween_slots if s.source != TimingSource.GENERATED
    ]
    save_timing_plan(root, cleaned)
    return {"ok": True, "timing_plan": cleaned, "mode": "drop_generated"}


def new_timing_version(root: Path, timing_id: str, *, label: str = "") -> TimingPlan:
    parent = load_timing_plan(root, timing_id)
    versions = list_timing_versions(root, parent.shot_id)
    next_v = max((t.version for t in versions), default=parent.version) + 1
    child = parent.model_copy(deep=True)
    child.id = new_id("timing")
    child.version = next_v
    child.parent_timing_id = parent.id
    child.label = label or f"timing v{next_v}"
    child.approval = parent.approval
    rev, prov = attribute_suggestion(
        operation="human.timing_version",
        target_type="timing_plan",
        target_id=child.id,
        snapshot=child.model_dump(mode="json"),
        summary=f"Forked timing v{next_v} from {parent.id}",
        outputs={"version": next_v, "parent": parent.id},
    )
    child.revision_id = rev.id
    save_timing_plan(root, child)
    save_revision(root, rev)
    save_provenance(root, prov)
    return child


def compare_timing_plans(root: Path, timing_a_id: str, timing_b_id: str) -> TimingDiff:
    a = load_timing_plan(root, timing_a_id)
    b = load_timing_plan(root, timing_b_id)

    def exp_key(e: ExposureHold) -> tuple:
        return (e.frame, e.kind, e.duration_frames, e.key_pose_id, e.source.value)

    set_a = {exp_key(e) for e in a.exposures}
    set_b = {exp_key(e) for e in b.exposures}
    exposure_changes: list[dict[str, Any]] = []
    for e in a.exposures:
        k = exp_key(e)
        if k not in set_b:
            exposure_changes.append({"side": "a_only", "frame": e.frame, "kind": e.kind})
    for e in b.exposures:
        k = exp_key(e)
        if k not in set_a:
            exposure_changes.append({"side": "b_only", "frame": e.frame, "kind": e.kind})

    seg_a = {
        (s.from_key_pose_id, s.to_key_pose_id): s.spacing.mode.value
        for s in a.spacing_segments
    }
    seg_b = {
        (s.from_key_pose_id, s.to_key_pose_id): s.spacing.mode.value
        for s in b.spacing_segments
    }
    segment_changes: list[dict[str, Any]] = []
    for key, mode in seg_a.items():
        if key not in seg_b:
            segment_changes.append(
                {"pair": list(key), "mode_a": mode, "mode_b": None}
            )
        elif seg_b[key] != mode:
            segment_changes.append(
                {"pair": list(key), "mode_a": mode, "mode_b": seg_b[key]}
            )
    for key, mode in seg_b.items():
        if key not in seg_a:
            segment_changes.append(
                {"pair": list(key), "mode_a": None, "mode_b": mode}
            )

    ann_a = {(x.frame, x.kind, x.text) for x in a.annotations}
    ann_b = {(x.frame, x.kind, x.text) for x in b.annotations}
    annotation_changes = [
        {"side": "a_only", "frame": f, "kind": k, "text": t}
        for f, k, t in sorted(ann_a - ann_b)
    ] + [
        {"side": "b_only", "frame": f, "kind": k, "text": t}
        for f, k, t in sorted(ann_b - ann_a)
    ]

    slots_a = {s.frame for s in a.inbetween_slots}
    slots_b = {s.frame for s in b.inbetween_slots}
    keys_same = list(a.key_pose_ids) == list(b.key_pose_ids)
    summary = (
        f"Timing {a.id} v{a.version} vs {b.id} v{b.version}: "
        f"end {a.end_frame}->{b.end_frame}, "
        f"exposure_deltas={len(exposure_changes)}, "
        f"segment_deltas={len(segment_changes)}, "
        f"key_pose_ids_unchanged={keys_same}"
    )
    return TimingDiff(
        timing_a_id=a.id,
        timing_b_id=b.id,
        version_a=a.version,
        version_b=b.version,
        end_frame_a=a.end_frame,
        end_frame_b=b.end_frame,
        exposure_changes=exposure_changes,
        segment_changes=segment_changes,
        annotation_changes=annotation_changes,
        slot_frames_only_in_a=sorted(slots_a - slots_b),
        slot_frames_only_in_b=sorted(slots_b - slots_a),
        key_pose_ids_a=list(a.key_pose_ids),
        key_pose_ids_b=list(b.key_pose_ids),
        key_pose_ids_unchanged=keys_same,
        summary=summary,
    )


def export_timing_bundle(root: Path, timing_id: str, dest: Path | None = None) -> Path:
    """Export timing + linked key poses. Holds survive as structured JSON."""
    ensure_timing_dirs(root)
    plan = load_timing_plan(root, timing_id)
    keys = []
    for kid in plan.key_pose_ids:
        path = root / "key_poses" / f"{kid}.json"
        if path.exists():
            keys.append(_read(path))
    bundle = {
        "format": "mvm.timing_bundle",
        "format_version": 1,
        "timing_plan": plan.model_dump(mode="json"),
        "key_poses": keys,
        "notes": (
            "Holds/exposures/spacing are authoring data. "
            "allow_auto_smooth is always false. Generated slots are tagged."
        ),
    }
    out = dest or (root / "timing_exports" / f"{timing_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return out


def import_timing_bundle(
    root: Path,
    bundle_path: Path,
    *,
    new_ids: bool = True,
) -> TimingPlan:
    """Import a timing bundle. Intentional holds round-trip intact."""
    ensure_timing_dirs(root)
    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    if data.get("format") != "mvm.timing_bundle":
        raise ValueError("Not an mvm.timing_bundle")
    plan = TimingPlan.model_validate(data["timing_plan"])
    if plan.allow_auto_smooth is not False:
        raise ValueError("Refusing import with allow_auto_smooth enabled")

    id_map: dict[str, str] = {}
    if new_ids:
        id_map[plan.id] = new_id("timing")
        plan.id = id_map[plan.id]
        for pose in data.get("key_poses") or []:
            old = pose["id"]
            new = new_id("pose")
            id_map[old] = new
            pose = copy.deepcopy(pose)
            pose["id"] = new
            save_key_pose(root, KeyPose.model_validate(pose))
        plan.key_pose_ids = [id_map.get(k, k) for k in plan.key_pose_ids]
        for exp in plan.exposures:
            if exp.key_pose_id and exp.key_pose_id in id_map:
                exp.key_pose_id = id_map[exp.key_pose_id]
        for slot in plan.inbetween_slots:
            slot.from_key_pose_id = id_map.get(
                slot.from_key_pose_id, slot.from_key_pose_id
            )
            slot.to_key_pose_id = id_map.get(slot.to_key_pose_id, slot.to_key_pose_id)
        for seg in plan.spacing_segments:
            seg.from_key_pose_id = id_map.get(
                seg.from_key_pose_id, seg.from_key_pose_id
            )
            seg.to_key_pose_id = id_map.get(seg.to_key_pose_id, seg.to_key_pose_id)
            seg.id = new_id("tseg")
            seg.spacing.id = new_id("curve")
        for ann in plan.annotations:
            ann.id = new_id("tann")
    else:
        for pose in data.get("key_poses") or []:
            save_key_pose(root, KeyPose.model_validate(pose))

    save_timing_plan(root, plan)
    return plan


def inspect_timeline(root: Path, timing_id: str) -> Any:
    return build_timeline(load_timing_plan(root, timing_id))


def custom_curve_roundtrip(
    control_points: list[tuple[float, float]],
    *,
    sample_count: int = 5,
) -> SpacingCurve:
    """Prove custom piecewise-linear interpolation is reconstructible."""
    curve = SpacingCurve(
        id=new_id("curve"),
        mode=SpacingMode.CUSTOM,
        control_points=control_points,
        source=TimingSource.AUTHORED,
    )
    samples = sample_progress(curve, sample_count)
    rebuilt = reconstruct_custom_from_samples(samples, curve_id=curve.id)
    # Midpoint identity for piecewise-linear through the same samples
    for t, _ in samples:
        if abs(progress_at(curve, t) - progress_at(rebuilt, t)) > 1e-9:
            raise AssertionError("Custom curve roundtrip failed")
    return rebuilt
