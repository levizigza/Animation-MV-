"""Sound-aware planning: cues + optional relationships; timing overlay; no forced motion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.cel.timing import time_to_frame
from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.domain import TimingPlan, TimingSource, TimingTimeline, new_id
from mvm.schemas.models import Beatmap
from mvm.schemas.sound import (
    MotionResponse,
    SoundCue,
    SoundCueKind,
    SoundPlan,
    SoundToMotionRelationship,
)
from mvm.timing.timeline import build_timeline
from mvm.timing.workflow import load_timing_plan


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_sound_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "sound_plans").mkdir(parents=True, exist_ok=True)


def save_sound_plan(root: Path, plan: SoundPlan) -> Path:
    ensure_sound_dirs(root)
    if plan.force_every_cue_to_motion is not False:
        raise ValueError("Refusing SoundPlan that forces every cue to motion")
    path = root / "sound_plans" / f"{plan.id}.json"
    _write(path, plan)
    ptr = root / "sound_plans" / f"shot_{plan.shot_id}_latest.json"
    _write(ptr, {"sound_plan_id": plan.id, "shot_id": plan.shot_id})
    return path


def load_sound_plan(root: Path, plan_id: str) -> SoundPlan:
    return SoundPlan.model_validate(_read(root / "sound_plans" / f"{plan_id}.json"))


def load_sound_plan_for_shot(root: Path, shot_id: str) -> SoundPlan | None:
    ptr = root / "sound_plans" / f"shot_{shot_id}_latest.json"
    if not ptr.exists():
        d = root / "sound_plans"
        if not d.exists():
            return None
        for p in d.glob("*.json"):
            if p.name.endswith("_latest.json"):
                continue
            data = _read(p)
            if data.get("shot_id") == shot_id and "cues" in data:
                return SoundPlan.model_validate(data)
        return None
    return load_sound_plan(root, _read(ptr)["sound_plan_id"])


def create_sound_plan(
    root: Path,
    *,
    shot_id: str,
    fps: int = 24,
    shot_start_sec: float = 0.0,
) -> SoundPlan:
    ensure_sound_dirs(root)
    plan = SoundPlan(
        id=new_id("snd"),
        shot_id=shot_id,
        fps=fps,
        shot_start_sec=shot_start_sec,
        force_every_cue_to_motion=False,
    )
    rev, prov = attribute_suggestion(
        operation="human.sound_plan_create",
        target_type="shot",
        target_id=shot_id,
        snapshot=plan.model_dump(mode="json"),
        summary=f"Created sound plan for {shot_id} (motion not forced)",
        outputs={"force_every_cue_to_motion": False},
    )
    plan.revision_id = rev.id
    save_sound_plan(root, plan)
    save_revision(root, rev)
    save_provenance(root, prov)
    return plan


def add_sound_cue(
    root: Path,
    plan_id: str,
    *,
    kind: SoundCueKind | str,
    time_sec: float,
    end_time_sec: float | None = None,
    label: str = "",
    text: str = "",
    notes: str = "",
    source: TimingSource = TimingSource.AUTHORED,
) -> SoundPlan:
    plan = load_sound_plan(root, plan_id).model_copy(deep=True)
    cue = SoundCue(
        kind=kind if isinstance(kind, SoundCueKind) else SoundCueKind(str(kind)),
        time_sec=time_sec,
        end_time_sec=end_time_sec,
        label=label,
        text=text,
        shot_id=plan.shot_id,
        source=source,
        notes=notes,
    )
    plan.cues = list(plan.cues) + [cue]
    # Default: no relationship — cue is visible, motion unassigned (not forced)
    save_sound_plan(root, plan)
    return plan


def link_sound_to_motion(
    root: Path,
    plan_id: str,
    cue_id: str,
    *,
    response: MotionResponse | str,
    notes: str = "",
    layer: str = "character",
) -> SoundPlan:
    """Author a sound→motion relationship. Never auto-applies to timing/keys."""
    plan = load_sound_plan(root, plan_id).model_copy(deep=True)
    if not any(c.id == cue_id for c in plan.cues):
        raise KeyError(f"Cue {cue_id} not in sound plan {plan_id}")
    resp = (
        response
        if isinstance(response, MotionResponse)
        else MotionResponse(str(response))
    )
    # Replace existing link for cue if present
    plan.relationships = [r for r in plan.relationships if r.cue_id != cue_id]
    rel = SoundToMotionRelationship(
        cue_id=cue_id,
        response=resp,
        layer=layer,
        notes=notes,
        applies_automatically=False,
    )
    plan.relationships = list(plan.relationships) + [rel]
    rev, prov = attribute_suggestion(
        operation="human.sound_to_motion_link",
        target_type="shot",
        target_id=plan.shot_id,
        snapshot={
            "sound_plan_id": plan.id,
            "relationship": rel.model_dump(mode="json"),
            "note": (
                f"Authored response={resp.value}. "
                "Does not auto-edit timing. Silence/non_reaction are valid."
            ),
        },
        summary=f"Linked cue {cue_id} → {resp.value} (no auto-apply)",
        outputs={
            "response": resp.value,
            "applies_automatically": False,
            "force_every_cue_to_motion": False,
        },
    )
    plan.revision_id = rev.id
    save_sound_plan(root, plan)
    save_revision(root, rev)
    save_provenance(root, prov)
    return plan


def import_beats_as_cues(
    root: Path,
    plan_id: str,
    beatmap: Beatmap,
    *,
    shot_start: float,
    shot_end: float,
) -> SoundPlan:
    """Import music beats as visible cues without creating motion links."""
    plan = load_sound_plan(root, plan_id).model_copy(deep=True)
    existing_t = {
        (c.kind, round(c.time_sec, 4))
        for c in plan.cues
        if c.kind == SoundCueKind.MUSIC_BEAT
    }
    added = 0
    for t in beatmap.beat_times:
        if not (shot_start <= t < shot_end):
            continue
        key = (SoundCueKind.MUSIC_BEAT, round(float(t), 4))
        if key in existing_t:
            continue
        plan.cues.append(
            SoundCue(
                kind=SoundCueKind.MUSIC_BEAT,
                time_sec=float(t),
                label="beat",
                shot_id=plan.shot_id,
                source=TimingSource.GENERATED,
                suggested_by_operation="sound.import_beats_as_cues",
                notes="Imported beat — no motion forced",
            )
        )
        added += 1
    rev, prov = attribute_suggestion(
        operation="sound.import_beats_as_cues",
        target_type="shot",
        target_id=plan.shot_id,
        snapshot={"added": added, "force_every_cue_to_motion": False},
        summary=f"Imported {added} beat cues with no automatic motion links",
        outputs={"added": added, "relationships_created": 0},
    )
    plan.revision_id = rev.id
    save_sound_plan(root, plan)
    save_revision(root, rev)
    save_provenance(root, prov)
    return plan


def cue_frame_span(
    cue: SoundCue,
    *,
    fps: int,
    shot_start_sec: float,
    plan_start_frame: int,
    plan_end_frame: int,
) -> tuple[int, int]:
    start_f = time_to_frame(cue.time_sec, fps, start=shot_start_sec)
    if cue.end_time_sec is not None:
        end_f = time_to_frame(cue.end_time_sec, fps, start=shot_start_sec)
    else:
        end_f = start_f
    start_f = max(plan_start_frame, min(plan_end_frame, start_f))
    end_f = max(plan_start_frame, min(plan_end_frame, end_f))
    if end_f < start_f:
        end_f = start_f
    return start_f, end_f


def build_sound_aware_timeline(
    timing_plan: TimingPlan,
    sound_plan: SoundPlan | None,
) -> TimingTimeline:
    """Timing timeline with sound cues visible; does not invent motion exposures."""
    timeline = build_timeline(timing_plan)
    if sound_plan is None:
        timeline.summary += " | sound_cues=0"
        return timeline

    by_frame = {e.frame: e for e in timeline.entries}
    rel_by_cue = {r.cue_id: r for r in sound_plan.relationships}
    non_reaction = 0
    linked = 0

    for cue in sound_plan.cues:
        start_f, end_f = cue_frame_span(
            cue,
            fps=sound_plan.fps or timing_plan.fps,
            shot_start_sec=sound_plan.shot_start_sec,
            plan_start_frame=timing_plan.start_frame,
            plan_end_frame=timing_plan.end_frame,
        )
        rel = rel_by_cue.get(cue.id)
        response = rel.response.value if rel else MotionResponse.UNASSIGNED.value
        if response in (
            MotionResponse.NON_REACTION.value,
            MotionResponse.SILENCE.value,
            MotionResponse.UNASSIGNED.value,
        ):
            non_reaction += 1
        if rel is not None:
            linked += 1

        for f in range(start_f, end_f + 1):
            if f not in by_frame:
                from mvm.schemas.domain import TimingTimelineEntry

                by_frame[f] = TimingTimelineEntry(frame=f)
            e = by_frame[f]
            if cue.id not in e.sound_cue_ids:
                e.sound_cue_ids.append(cue.id)
            if cue.kind.value not in e.sound_cue_kinds:
                e.sound_cue_kinds.append(cue.kind.value)
            label = cue.label or cue.kind.value
            if label not in e.sound_labels:
                e.sound_labels.append(label)
            if response not in e.motion_responses:
                e.motion_responses.append(response)
            if "sound" not in e.roles:
                e.roles.append("sound")

    timeline.entries = [by_frame[f] for f in sorted(by_frame)]
    timeline.sound_cue_count = len(sound_plan.cues)
    timeline.sound_linked_count = linked
    timeline.sound_non_reaction_count = non_reaction
    timeline.force_every_cue_to_motion = False
    timeline.summary = (
        f"{timeline.summary} | sound_cues={len(sound_plan.cues)} "
        f"linked={linked} non_reaction_or_open={non_reaction} "
        f"force_motion={sound_plan.force_every_cue_to_motion}"
    )
    return timeline


def inspect_sound_timing(
    root: Path,
    *,
    timing_plan_id: str,
    sound_plan_id: str | None = None,
    shot_id: str | None = None,
) -> TimingTimeline:
    timing = load_timing_plan(root, timing_plan_id)
    sound: SoundPlan | None = None
    if sound_plan_id:
        sound = load_sound_plan(root, sound_plan_id)
    elif shot_id:
        sound = load_sound_plan_for_shot(root, shot_id)
    else:
        sound = load_sound_plan_for_shot(root, timing.shot_id)
    return build_sound_aware_timeline(timing, sound)


def unassigned_cues(plan: SoundPlan) -> list[SoundCue]:
    linked = {r.cue_id for r in plan.relationships}
    return [c for c in plan.cues if c.id not in linked]


def assert_silence_and_non_reaction_allowed(plan: SoundPlan) -> None:
    """Contract helper: plans must allow stillness / non-reaction."""
    if plan.force_every_cue_to_motion:
        raise AssertionError("force_every_cue_to_motion must be False")
    for rel in plan.relationships:
        if rel.applies_automatically:
            raise AssertionError("relationships must not apply automatically")
        if rel.response in (MotionResponse.SILENCE, MotionResponse.NON_REACTION):
            continue  # explicitly valid
