"""Sound-aware planning: cues on timing, silence/non-reaction valid, no forced motion."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mvm.schemas.models import Beatmap, Section
from mvm.schemas.sound import MotionResponse, SoundCueKind, SoundPlan
from mvm.sound import (
    add_sound_cue,
    assert_silence_and_non_reaction_allowed,
    create_sound_plan,
    import_beats_as_cues,
    inspect_sound_timing,
    link_sound_to_motion,
    load_sound_plan,
    unassigned_cues,
)
from mvm.timing import create_timing_plan


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in ("sound_plans", "timing", "key_poses", "revisions", "provenance"):
        (root / sub).mkdir(parents=True)
    return root


def test_all_cue_kinds_and_non_reaction_silence_valid():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        plan = create_sound_plan(root, shot_id="shot_s", fps=24, shot_start_sec=0.0)
        kinds = [
            "dialogue",
            "phoneme",
            "emphasis",
            "impact",
            "breath",
            "music_beat",
            "silence",
            "environmental",
        ]
        for i, kind in enumerate(kinds):
            plan = add_sound_cue(
                root,
                plan.id,
                kind=kind,
                time_sec=0.1 * i,
                end_time_sec=0.1 * i + 0.05 if kind == "silence" else None,
                label=kind,
                text="ah" if kind == "phoneme" else "",
            )
        assert len(plan.cues) == 8
        assert {c.kind.value for c in plan.cues} == set(kinds)

        silence = next(c for c in plan.cues if c.kind == SoundCueKind.SILENCE)
        impact = next(c for c in plan.cues if c.kind == SoundCueKind.IMPACT)
        plan = link_sound_to_motion(
            root, plan.id, silence.id, response="silence", notes="Hold through quiet"
        )
        plan = link_sound_to_motion(
            root,
            plan.id,
            impact.id,
            response="non_reaction",
            notes="Hear the hit; face stays still",
        )
        assert_silence_and_non_reaction_allowed(plan)
        assert plan.force_every_cue_to_motion is False
        responses = {r.cue_id: r.response for r in plan.relationships}
        assert responses[silence.id] == MotionResponse.SILENCE
        assert responses[impact.id] == MotionResponse.NON_REACTION
        assert all(r.applies_automatically is False for r in plan.relationships)

        # Unlinked cues remain valid (visible, no forced move)
        assert len(unassigned_cues(plan)) == 6

        with pytest.raises(Exception):
            data = plan.model_dump(mode="json")
            data["force_every_cue_to_motion"] = True
            SoundPlan.model_validate(data)


def test_sound_cues_visible_on_timing_without_forcing_exposures():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        timing = create_timing_plan(root, shot_id="shot_s", end_frame=48, fps=24)
        sound = create_sound_plan(root, shot_id="shot_s", fps=24, shot_start_sec=0.0)
        sound = add_sound_cue(
            root, sound.id, kind="breath", time_sec=0.5, label="inhale"
        )
        sound = add_sound_cue(
            root,
            sound.id,
            kind="dialogue",
            time_sec=1.0,
            end_time_sec=1.4,
            label="line",
            text="Stay.",
        )
        breath = next(c for c in sound.cues if c.kind == SoundCueKind.BREATH)
        sound = link_sound_to_motion(
            root, sound.id, breath.id, response="non_reaction"
        )

        tl = inspect_sound_timing(
            root, timing_plan_id=timing.id, sound_plan_id=sound.id
        )
        assert tl.force_every_cue_to_motion is False
        assert tl.sound_cue_count == 2
        sound_frames = [e for e in tl.entries if e.sound_cue_ids]
        assert sound_frames, "expected sound cues visible on timeline frames"
        assert any("breath" in e.sound_cue_kinds for e in sound_frames)
        assert any("non_reaction" in e.motion_responses for e in sound_frames)
        # Timing exposures unchanged — overlay does not invent motion
        from mvm.timing import load_timing_plan

        plan_after = load_timing_plan(root, timing.id)
        assert plan_after.exposures == []
        assert plan_after.inbetween_slots == []


def test_import_beats_creates_cues_without_motion_links():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        sound = create_sound_plan(root, shot_id="shot_s", fps=24)
        beatmap = Beatmap(
            duration=4.0,
            sample_rate=22050,
            bpm=120.0,
            beat_times=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5],
            sections=[Section(name="verse", start=0.0, end=4.0, energy=0.5)],
        )
        sound = import_beats_as_cues(
            root, sound.id, beatmap, shot_start=0.0, shot_end=2.0
        )
        beats = [c for c in sound.cues if c.kind == SoundCueKind.MUSIC_BEAT]
        assert len(beats) == 4  # 0, 0.5, 1.0, 1.5
        assert sound.relationships == []
        assert sound.force_every_cue_to_motion is False
        assert all(c.notes.find("no motion forced") >= 0 for c in beats)
