"""Persist domain v2 artifacts beside legacy shots/xsheets (no editor)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.schemas.compat import (
    attribute_suggestion,
    layout_from_shot,
    panel_from_shot,
    project_from_meta,
    sequences_from_shots,
    timing_plan_from_xsheet,
)
from mvm.schemas.domain import (
    KeyPose,
    Layout,
    Project,
    ProvenanceRecord,
    Revision,
    Sequence,
    StoryboardPanel,
    TimingPlan,
)
from mvm.schemas.models import ProjectMeta, Shot, XSheet


DOMAIN_DIRS = (
    "sequences",
    "timing",
    "key_poses",
    "layouts",
    "panels",
    "revisions",
    "provenance",
    "reviews",
    "animatics",
    "suggestions",
    "notation",
    "motion_requests",
    "notebooks",
    "critiques",
    "sequence_evals",
    "sound_plans",
    "provenance_exports",
    "assistant_suggestions",
    "eval_scenes",
    "eval_sessions",
    "eval_forms",
    "pilot_reports",
    "external_refs",
    "neurosymbolic_decisions",
)


def ensure_domain_dirs(root: Path) -> None:
    for name in DOMAIN_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clear_json_dir(path: Path) -> None:
    if not path.exists():
        return
    for p in path.glob("*.json"):
        p.unlink()


def save_revision(root: Path, revision: Revision) -> Path:
    ensure_domain_dirs(root)
    path = root / "revisions" / f"{revision.id}.json"
    _write(path, revision)
    return path


def save_provenance(root: Path, prov: ProvenanceRecord) -> Path:
    ensure_domain_dirs(root)
    path = root / "provenance" / f"{prov.id}.json"
    _write(path, prov)
    return path


def load_revisions(root: Path) -> list[Revision]:
    d = root / "revisions"
    if not d.exists():
        return []
    return [
        Revision.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(d.glob("*.json"))
    ]


def load_provenance(root: Path) -> list[ProvenanceRecord]:
    d = root / "provenance"
    if not d.exists():
        return []
    return [
        ProvenanceRecord.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(d.glob("*.json"))
    ]


def load_sequences(root: Path) -> list[Sequence]:
    d = root / "sequences"
    if not d.exists():
        return []
    return [
        Sequence.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(d.glob("*.json"))
    ]


def load_timing_plans(root: Path) -> list[TimingPlan]:
    d = root / "timing"
    if not d.exists():
        return []
    return [
        TimingPlan.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(d.glob("*.json"))
    ]


def persist_plan_domain(
    root: Path,
    *,
    meta: ProjectMeta,
    shots: list[Shot],
    xsheets: list[XSheet],
) -> dict[str, Any]:
    """Write sequences, timing plans, key poses, layouts, panels + plan revision/provenance."""
    ensure_domain_dirs(root)
    xs_by_id = {x.shot_id: x for x in xsheets}
    sequences = sequences_from_shots(shots)
    seq_by_shot = {
        sid: seq.id for seq in sequences for sid in seq.shot_ids
    }

    _clear_json_dir(root / "sequences")
    _clear_json_dir(root / "timing")
    _clear_json_dir(root / "key_poses")
    _clear_json_dir(root / "layouts")
    _clear_json_dir(root / "panels")

    timing_plans: list[TimingPlan] = []
    all_keys: list[KeyPose] = []
    layouts: list[Layout] = []
    panels: list[StoryboardPanel] = []
    updated_shots: list[Shot] = []

    for shot in shots:
        xs = xs_by_id.get(shot.id)
        seq_id = seq_by_shot.get(shot.id)
        shot.sequence_id = seq_id
        if xs is None:
            updated_shots.append(shot)
            continue
        plan, keys = timing_plan_from_xsheet(xs, shot)
        layout = layout_from_shot(shot)
        panel = panel_from_shot(shot)
        shot.timing_plan_id = plan.id
        shot.layout_id = layout.id
        shot.storyboard_panel_ids = [panel.id]
        shot.key_pose_ids = [k.id for k in keys]
        timing_plans.append(plan)
        all_keys.extend(keys)
        layouts.append(layout)
        panels.append(panel)
        updated_shots.append(shot)

    for seq in sequences:
        _write(root / "sequences" / f"{seq.id}.json", seq)
    for plan in timing_plans:
        _write(root / "timing" / f"{plan.id}.json", plan)
    for key in all_keys:
        _write(root / "key_poses" / f"{key.id}.json", key)
    for layout in layouts:
        _write(root / "layouts" / f"{layout.id}.json", layout)
    for panel in panels:
        _write(root / "panels" / f"{panel.id}.json", panel)

    # Update shots on disk with domain ids (caller may also save_shots)
    for shot in updated_shots:
        _write(root / "shots" / f"{shot.id}.json", shot)

    project = project_from_meta(meta, sequences=sequences)
    rev, prov = attribute_suggestion(
        operation="agents.plan",
        target_type="project",
        target_id=meta.slug,
        snapshot={
            "schema_version": project.schema_version,
            "sequence_ids": project.sequence_ids,
            "shot_ids": [s.id for s in updated_shots],
            "timing_plan_ids": [t.id for t in timing_plans],
            "intents": {s.id: s.intent.model_dump(mode="json") for s in updated_shots},
            "note": (
                "Heuristic plan. Key poses are authored extremes; "
                "inbetween_slots are planned exposures only — not generated pixels."
            ),
        },
        summary=f"Plan for {meta.slug}: {len(sequences)} sequences, {len(updated_shots)} shots",
        inputs={"style_pack": meta.style_pack, "prompt": meta.prompt},
        outputs={
            "sequences": len(sequences),
            "timing_plans": len(timing_plans),
            "key_poses": len(all_keys),
        },
    )
    project.active_revision_id = rev.id
    _write(root / "domain_project.json", project)
    save_revision(root, rev)
    save_provenance(root, prov)

    # Stamp revision on timing plans
    for plan in timing_plans:
        plan.revision_id = rev.id
        _write(root / "timing" / f"{plan.id}.json", plan)

    return {
        "project": project,
        "sequences": sequences,
        "timing_plans": timing_plans,
        "key_poses": all_keys,
        "shots": updated_shots,
        "revision": rev,
        "provenance": prov,
    }


def persist_timing_rebuild(
    root: Path,
    *,
    shot: Shot,
    xsheet: XSheet,
    changed_fields: list[str],
    parent_revision_id: str | None = None,
) -> dict[str, Any]:
    """After cel edit: rebuild TimingPlan/KeyPoses and attribute a revision."""
    ensure_domain_dirs(root)
    plan, keys = timing_plan_from_xsheet(xsheet, shot)

    # Remove prior timing file for this shot if present
    timing_dir = root / "timing"
    if timing_dir.exists():
        for p in timing_dir.glob("*.json"):
            existing = TimingPlan.model_validate_json(p.read_text(encoding="utf-8"))
            if existing.shot_id == shot.id:
                p.unlink()
    # Remove prior key poses for this shot
    kp_dir = root / "key_poses"
    if kp_dir.exists():
        for p in kp_dir.glob("*.json"):
            existing = KeyPose.model_validate_json(p.read_text(encoding="utf-8"))
            if existing.shot_id == shot.id:
                p.unlink()

    shot.timing_plan_id = plan.id
    shot.key_pose_ids = [k.id for k in keys]
    _write(root / "timing" / f"{plan.id}.json", plan)
    for key in keys:
        _write(root / "key_poses" / f"{key.id}.json", key)
    _write(root / "shots" / f"{shot.id}.json", shot)

    rev, prov = attribute_suggestion(
        operation="cel.xsheet_rebuild",
        target_type="timing_plan",
        target_id=plan.id,
        snapshot={
            "shot_id": shot.id,
            "cel": shot.cel.model_dump(mode="json"),
            "timing_plan": plan.model_dump(mode="json"),
            "key_poses": [k.model_dump(mode="json") for k in keys],
            "changed_fields": changed_fields,
            "interpolation_note": (
                "Inbetween slots re-planned from X-sheet exposures; "
                "no hidden pixel interpolation."
            ),
        },
        summary=f"Timing rebuilt for {shot.id} after {', '.join(changed_fields)}",
        inputs={"changed_fields": changed_fields, "cel": shot.cel.model_dump(mode="json")},
        outputs={
            "key_pose_count": len(keys),
            "inbetween_slots": len(plan.inbetween_slots),
            "smear_frames": plan.smear_frames,
        },
        parent_revision_id=parent_revision_id,
    )
    plan.revision_id = rev.id
    shot.revision_id = rev.id
    _write(root / "timing" / f"{plan.id}.json", plan)
    _write(root / "shots" / f"{shot.id}.json", shot)
    save_revision(root, rev)
    save_provenance(root, prov)

    # Update domain_project active revision if present
    dp = root / "domain_project.json"
    if dp.exists():
        project = Project.model_validate_json(dp.read_text(encoding="utf-8"))
        project.active_revision_id = rev.id
        _write(dp, project)

    return {
        "timing_plan": plan,
        "key_poses": keys,
        "shot": shot,
        "revision": rev,
        "provenance": prov,
    }


def domain_to_dict(root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    dp = root / "domain_project.json"
    if dp.exists():
        out["domain_project"] = json.loads(dp.read_text(encoding="utf-8"))
    out["sequences"] = [s.model_dump(mode="json") for s in load_sequences(root)]
    out["timing_plans"] = [t.model_dump(mode="json") for t in load_timing_plans(root)]
    kp_dir = root / "key_poses"
    if kp_dir.exists():
        out["key_poses"] = [
            json.loads(p.read_text(encoding="utf-8")) for p in sorted(kp_dir.glob("*.json"))
        ]
    out["revisions"] = [r.model_dump(mode="json") for r in load_revisions(root)]
    out["provenance"] = [p.model_dump(mode="json") for p in load_provenance(root)]
    from mvm.project.reviews import load_reviews

    out["reviews"] = [r.model_dump(mode="json") for r in load_reviews(root)]
    return out
