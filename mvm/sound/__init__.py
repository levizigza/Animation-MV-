"""Sound-aware animation planning."""

from mvm.sound.workflow import (
    add_sound_cue,
    assert_silence_and_non_reaction_allowed,
    build_sound_aware_timeline,
    create_sound_plan,
    import_beats_as_cues,
    inspect_sound_timing,
    link_sound_to_motion,
    load_sound_plan,
    load_sound_plan_for_shot,
    unassigned_cues,
)
from mvm.schemas.sound import (
    MotionResponse,
    SoundCue,
    SoundCueKind,
    SoundPlan,
    SoundToMotionRelationship,
)

__all__ = [
    "MotionResponse",
    "SoundCue",
    "SoundCueKind",
    "SoundPlan",
    "SoundToMotionRelationship",
    "add_sound_cue",
    "assert_silence_and_non_reaction_allowed",
    "build_sound_aware_timeline",
    "create_sound_plan",
    "import_beats_as_cues",
    "inspect_sound_timing",
    "link_sound_to_motion",
    "load_sound_plan",
    "load_sound_plan_for_shot",
    "unassigned_cues",
]
