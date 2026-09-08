"""Storyboard + first-class animatic workflow (timing separate from artwork)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.domain import (
    Animatic,
    AnimaticDiff,
    AnimaticPanelRef,
    AnimaticPreviewFrame,
    StoryboardPanel,
    new_id,
)
from mvm.schemas.models import Shot, ShotIntent, ShotLifecycleState


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_animatic_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "animatics").mkdir(parents=True, exist_ok=True)
    (root / "panels").mkdir(parents=True, exist_ok=True)
    (root / "shots").mkdir(parents=True, exist_ok=True)


def save_panel(root: Path, panel: StoryboardPanel) -> Path:
    ensure_animatic_dirs(root)
    path = root / "panels" / f"{panel.id}.json"
    _write(path, panel)
    return path


def load_panel(root: Path, panel_id: str) -> StoryboardPanel:
    return StoryboardPanel.model_validate(_read(root / "panels" / f"{panel_id}.json"))


def load_panels_for_shot(root: Path, shot_id: str) -> list[StoryboardPanel]:
    d = root / "panels"
    if not d.exists():
        return []
    panels = [
        StoryboardPanel.model_validate(_read(p))
        for p in d.glob("*.json")
        if _read(p).get("shot_id") == shot_id
    ]
    return sorted(panels, key=lambda p: p.index)


def save_animatic(root: Path, animatic: Animatic) -> Path:
    ensure_animatic_dirs(root)
    path = root / "animatics" / f"{animatic.id}.json"
    _write(path, animatic)
    ptr = root / "animatics" / f"shot_{animatic.shot_id}_latest.json"
    _write(
        ptr,
        {
            "animatic_id": animatic.id,
            "version": animatic.version,
            "shot_id": animatic.shot_id,
        },
    )
    return path


def load_animatic(root: Path, animatic_id: str) -> Animatic:
    return Animatic.model_validate(_read(root / "animatics" / f"{animatic_id}.json"))


def list_animatics_for_shot(root: Path, shot_id: str) -> list[Animatic]:
    d = root / "animatics"
    if not d.exists():
        return []
    out: list[Animatic] = []
    for p in d.glob("*.json"):
        if p.name.startswith("shot_") and p.name.endswith("_latest.json"):
            continue
        if "_preview.json" in p.name or p.name.startswith("diff_"):
            continue
        data = _read(p)
        if data.get("shot_id") == shot_id and "version" in data and "panels" in data:
            out.append(Animatic.model_validate(data))
    return sorted(out, key=lambda a: a.version)


def create_shot(
    root: Path,
    *,
    shot_id: str | None = None,
    index: int = 1,
    section: str = "verse",
    start: float = 0.0,
    end: float = 4.0,
    intent: ShotIntent | None = None,
    purpose: str | None = None,
) -> Shot:
    """Create a shot with an explicit intention (required for craft-first)."""
    ensure_animatic_dirs(root)
    if intent is None:
        if not purpose or not purpose.strip():
            raise ValueError("create_shot requires ShotIntent or a non-empty purpose")
        intent = ShotIntent(purpose=purpose.strip())
    sid = shot_id or new_id("shot")
    duration = max(0.1, end - start)
    shot = Shot(
        id=sid,
        index=index,
        section=section,
        start=start,
        end=end,
        duration=duration,
        intent=intent,
        lifecycle_state=ShotLifecycleState.INTENT,
        description=intent.purpose,
    )
    _write(root / "shots" / f"{shot.id}.json", shot)
    return shot


def attach_shot_intention(root: Path, shot_id: str, intent: ShotIntent) -> Shot:
    path = root / "shots" / f"{shot_id}.json"
    shot = Shot.model_validate(_read(path))
    shot.intent = intent
    shot.description = intent.purpose
    _write(path, shot)
    return shot


def add_storyboard_panel(
    root: Path,
    shot_id: str,
    *,
    caption: str = "",
    intent_summary: str = "",
    thumbnail_ref: str | None = None,
    default_duration_frames: int = 24,
    index: int | None = None,
) -> StoryboardPanel:
    shot_path = root / "shots" / f"{shot_id}.json"
    shot = Shot.model_validate(_read(shot_path))
    existing = load_panels_for_shot(root, shot_id)
    idx = index if index is not None else (max((p.index for p in existing), default=0) + 1)
    panel = StoryboardPanel(
        id=new_id("panel"),
        shot_id=shot_id,
        index=idx,
        caption=caption,
        intent_summary=intent_summary or shot.intent.purpose,
        thumbnail_ref=thumbnail_ref,
        default_duration_frames=default_duration_frames,
    )
    save_panel(root, panel)
    ids = list(shot.storyboard_panel_ids)
    if panel.id not in ids:
        ids.append(panel.id)
    shot.storyboard_panel_ids = ids
    if shot.lifecycle_state == ShotLifecycleState.INTENT:
        shot.lifecycle_state = ShotLifecycleState.STORYBOARD
    _write(shot_path, shot)
    return panel


def build_or_get_animatic(root: Path, shot_id: str, *, label: str = "v1") -> Animatic:
    """Create animatic v1 from current panels if none exists (first-class artifact)."""
    existing = list_animatics_for_shot(root, shot_id)
    if existing:
        return existing[-1]
    panels = load_panels_for_shot(root, shot_id)
    if not panels:
        raise ValueError(f"Shot {shot_id} has no storyboard panels for an animatic")
    refs = [
        AnimaticPanelRef(
            panel_id=p.id,
            order=i,
            duration_frames=p.default_duration_frames,
        )
        for i, p in enumerate(sorted(panels, key=lambda x: x.index))
    ]
    anim = Animatic(
        id=new_id("anim"),
        shot_id=shot_id,
        version=1,
        label=label,
        panels=refs,
    )
    rev, prov = attribute_suggestion(
        operation="human.animatic_create",
        target_type="shot",
        target_id=shot_id,
        snapshot=anim.model_dump(mode="json"),
        summary=f"Created animatic v1 for {shot_id}",
        outputs={"panel_count": len(refs), "total_frames": anim.total_duration_frames},
    )
    anim.revision_id = rev.id
    save_revision(root, rev)
    save_provenance(root, prov)
    save_animatic(root, anim)
    return anim


def reorder_panels(root: Path, animatic_id: str, panel_ids_in_order: list[str]) -> Animatic:
    anim = load_animatic(root, animatic_id)
    by_id = {p.panel_id: p for p in anim.panels}
    if set(panel_ids_in_order) != set(by_id):
        missing = set(by_id) - set(panel_ids_in_order)
        extra = set(panel_ids_in_order) - set(by_id)
        raise ValueError(
            f"Reorder must include exactly the animatic panels. missing={missing} extra={extra}"
        )
    new_panels = []
    for i, pid in enumerate(panel_ids_in_order):
        ref = by_id[pid].model_copy(deep=True)
        ref.order = i
        new_panels.append(ref)
    anim.panels = new_panels
    save_animatic(root, anim)
    return anim


def set_panel_duration(
    root: Path,
    animatic_id: str,
    panel_id: str,
    duration_frames: int,
) -> Animatic:
    """Revise duration on the animatic only — does not mutate panel artwork fields."""
    if duration_frames < 1:
        raise ValueError("duration_frames must be >= 1")
    anim = load_animatic(root, animatic_id)
    found = False
    new_panels: list[AnimaticPanelRef] = []
    for ref in anim.panels:
        if ref.panel_id == panel_id:
            found = True
            new_panels.append(ref.model_copy(update={"duration_frames": duration_frames}))
        else:
            new_panels.append(ref)
    if not found:
        raise ValueError(f"Panel {panel_id} not on animatic {animatic_id}")
    anim.panels = new_panels
    save_animatic(root, anim)
    return anim


def new_animatic_version(
    root: Path,
    animatic_id: str,
    *,
    label: str | None = None,
) -> Animatic:
    """Fork a new version for comparison; keeps parent lineage."""
    parent = load_animatic(root, animatic_id)
    versions = list_animatics_for_shot(root, parent.shot_id)
    next_v = max(a.version for a in versions) + 1
    child = Animatic(
        id=new_id("anim"),
        shot_id=parent.shot_id,
        version=next_v,
        label=label or f"v{next_v}",
        fps=parent.fps,
        panels=[p.model_copy(deep=True) for p in parent.panels],
        parent_animatic_id=parent.id,
        approved=False,
    )
    rev, prov = attribute_suggestion(
        operation="human.animatic_version",
        target_type="shot",
        target_id=parent.shot_id,
        snapshot=child.model_dump(mode="json"),
        summary=f"Animatic v{next_v} forked from {parent.id}",
        inputs={"parent_animatic_id": parent.id},
        outputs={"version": next_v},
        parent_revision_id=parent.revision_id,
    )
    child.revision_id = rev.id
    save_revision(root, rev)
    save_provenance(root, prov)
    save_animatic(root, child)
    return child


def preview_animatic(root: Path, animatic_id: str) -> list[AnimaticPreviewFrame]:
    """Rough animatic preview as a frame-accurate timeline (no visual polish)."""
    anim = load_animatic(root, animatic_id)
    frames: list[AnimaticPreviewFrame] = []
    cursor = 0
    ordered = sorted(anim.panels, key=lambda p: p.order)
    for ref in ordered:
        panel = load_panel(root, ref.panel_id)
        start = cursor
        end = cursor + ref.duration_frames
        frames.append(
            AnimaticPreviewFrame(
                order=ref.order,
                panel_id=ref.panel_id,
                caption=panel.caption,
                intent_summary=panel.intent_summary,
                start_frame=start,
                end_frame=end,
                duration_frames=ref.duration_frames,
                start_sec=start / anim.fps,
                end_sec=end / anim.fps,
            )
        )
        cursor = end
    preview_path = root / "animatics" / f"{animatic_id}_preview.json"
    _write(
        preview_path,
        {
            "animatic_id": anim.id,
            "shot_id": anim.shot_id,
            "version": anim.version,
            "fps": anim.fps,
            "total_frames": anim.total_duration_frames,
            "total_sec": anim.total_duration_sec,
            "timeline": [f.model_dump(mode="json") for f in frames],
            "note": "Rough animatic timeline — durations are animatic-owned, not artwork.",
        },
    )
    return frames


def compare_animatics(root: Path, animatic_a_id: str, animatic_b_id: str) -> AnimaticDiff:
    a = load_animatic(root, animatic_a_id)
    b = load_animatic(root, animatic_b_id)
    order_a = [p.panel_id for p in sorted(a.panels, key=lambda x: x.order)]
    order_b = [p.panel_id for p in sorted(b.panels, key=lambda x: x.order)]
    dur_a = {p.panel_id: p.duration_frames for p in a.panels}
    dur_b = {p.panel_id: p.duration_frames for p in b.panels}
    common = set(dur_a) & set(dur_b)
    duration_changes = []
    for pid in sorted(common):
        if dur_a[pid] != dur_b[pid]:
            duration_changes.append(
                {
                    "panel_id": pid,
                    "duration_a": dur_a[pid],
                    "duration_b": dur_b[pid],
                    "delta_frames": dur_b[pid] - dur_a[pid],
                }
            )
    only_a = sorted(set(dur_a) - set(dur_b))
    only_b = sorted(set(dur_b) - set(dur_a))
    order_changed = order_a != order_b
    summary_parts = []
    if order_changed:
        summary_parts.append("panel order differs")
    if duration_changes:
        summary_parts.append(f"{len(duration_changes)} duration change(s)")
    if only_a or only_b:
        summary_parts.append("panel membership differs")
    if not summary_parts:
        summary_parts.append("animatics are timing-identical")
    diff = AnimaticDiff(
        animatic_a_id=a.id,
        animatic_b_id=b.id,
        version_a=a.version,
        version_b=b.version,
        order_changed=order_changed,
        order_a=order_a,
        order_b=order_b,
        duration_changes=duration_changes,
        panels_only_in_a=only_a,
        panels_only_in_b=only_b,
        total_frames_a=a.total_duration_frames,
        total_frames_b=b.total_duration_frames,
        total_sec_a=a.total_duration_sec,
        total_sec_b=b.total_duration_sec,
        summary="; ".join(summary_parts),
    )
    _write(
        root / "animatics" / f"diff_{a.id}_{b.id}.json",
        diff.model_dump(mode="json"),
    )
    return diff
