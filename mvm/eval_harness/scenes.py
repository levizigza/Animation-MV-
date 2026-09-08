"""Three fixed craft evaluation scenes — dialogue, physical action, quiet."""

from __future__ import annotations

from mvm.schemas.eval_harness import EvalSceneFixture, SceneKind


def dialogue_scene() -> EvalSceneFixture:
    return EvalSceneFixture(
        id="eval_scene_dialogue",
        kind=SceneKind.DIALOGUE,
        title="Kitchen table — readable acting",
        summary=(
            "Two-character dialogue beat: one speaks a difficult line, "
            "the other listens then answers. Requires readable face/gesture acting."
        ),
        craft_focus=[
            "intent clarity of the conversational beat",
            "pose readability of speaker vs listener",
            "timing of line delivery and reaction",
            "sound relationship to dialogue cues without forced motion",
        ],
        success_criteria=[
            "Audience can tell who is speaking and what they feel without audio",
            "Listener holds are intentional, not empty freezes",
            "Phoneme/dialogue cues do not auto-force mouth motion every frame",
        ],
        shot_id="shot_eval_dialogue",
        sequence_id="seq_eval_harness",
        intent={
            "purpose": "Deliver the apology line and land the listener's delayed reaction",
            "emotional_beat": "guilt → guarded hope",
            "staging_goal": "Speaker 3/4; listener profile with clear eye-line",
            "animation_priority": "performance",
            "must_read_silhouette": True,
            "hold_for_lyric": False,
            "notes": "Acting readability first; avoid chatter on every syllable",
        },
        key_poses=[
            {
                "id": "pose_dlg_anticipate",
                "frame": 1,
                "label": "inhale before line",
                "action": "prepare to speak",
                "intention": "show hesitation before the apology",
                "is_extreme": True,
                "marked_as_key": True,
            },
            {
                "id": "pose_dlg_speak",
                "frame": 18,
                "label": "line peak",
                "action": "speak apology",
                "intention": "make the words land as sincere",
                "is_extreme": True,
                "marked_as_key": True,
            },
            {
                "id": "pose_dlg_listen",
                "frame": 48,
                "label": "listener hold",
                "action": "listen",
                "intention": "absorb before answering",
                "is_extreme": True,
                "marked_as_key": True,
            },
            {
                "id": "pose_dlg_reply",
                "frame": 72,
                "label": "soft reply",
                "action": "answer",
                "intention": "open a small door without fully forgiving",
                "is_extreme": True,
                "marked_as_key": True,
            },
        ],
        timing={
            "id": "timing_eval_dialogue",
            "fps": 24,
            "start_frame": 1,
            "end_frame": 96,
            "allow_auto_smooth": False,
            "holds": [
                {"start": 48, "duration": 18, "kind": "hold", "note": "listener stillness"},
                {"start": 72, "duration": 12, "kind": "hold", "note": "reply settle"},
            ],
            "spacing_mode": "slow_out",
        },
        sound_cues=[
            {
                "id": "scue_dlg_line",
                "kind": "dialogue",
                "time_sec": 0.5,
                "label": "I'm sorry I left",
                "motion_response": "move",
            },
            {
                "id": "scue_dlg_silence",
                "kind": "silence",
                "time_sec": 2.0,
                "end_time_sec": 2.8,
                "label": "pause before reply",
                "motion_response": "hold",
            },
            {
                "id": "scue_dlg_reply",
                "kind": "dialogue",
                "time_sec": 3.0,
                "label": "I heard you",
                "motion_response": "move",
            },
        ],
        sequence_neighbors={
            "previous_shot_id": "shot_eval_dialogue_prev",
            "next_shot_id": "shot_eval_dialogue_next",
            "previous_note": "Wide establishing — both seated",
            "next_note": "Cut to hands — tea cup reaction",
        },
        revision_notes="v1 dialogue performance pass — acting readability focus",
    )


def physical_action_scene() -> EvalSceneFixture:
    return EvalSceneFixture(
        id="eval_scene_physical",
        kind=SceneKind.PHYSICAL_ACTION,
        title="Crate lift — weight and timing",
        summary=(
            "Character lifts a heavy crate: anticipation, strain, contact, "
            "settle. Requires weight and timing more than facial acting."
        ),
        craft_focus=[
            "weight through anticipation and settle",
            "timing of effort and impact",
            "spacing into contact",
            "sound relationship to impact without forcing every onset",
        ],
        success_criteria=[
            "Mass reads through pose and timing, not just a fast grab",
            "Impact cue may hold or move — not forced every time",
            "Spacing into contact is explicit (not silent ease)",
        ],
        shot_id="shot_eval_physical",
        sequence_id="seq_eval_harness",
        intent={
            "purpose": "Sell the weight of the crate through body mechanics",
            "emotional_beat": "effort → relief",
            "staging_goal": "Full body silhouette against the doorway",
            "animation_priority": "impact",
            "must_read_silhouette": True,
            "hold_for_lyric": False,
            "notes": "Weight and timing; smear optional only on peak strain",
        },
        key_poses=[
            {
                "id": "pose_phys_anticipation",
                "frame": 1,
                "label": "crouch anticipate",
                "action": "anticipate lift",
                "intention": "load the body before force",
                "is_extreme": True,
                "marked_as_key": True,
                "arc": {"anticipation_frames": 8, "follow_through_frames": None},
            },
            {
                "id": "pose_phys_strain",
                "frame": 20,
                "label": "peak strain",
                "action": "lift under load",
                "intention": "show mass resisting",
                "is_extreme": True,
                "marked_as_key": True,
            },
            {
                "id": "pose_phys_contact",
                "frame": 36,
                "label": "crate clears floor",
                "action": "contact success",
                "intention": "register weight shift",
                "is_extreme": True,
                "marked_as_key": True,
            },
            {
                "id": "pose_phys_settle",
                "frame": 52,
                "label": "settle hold",
                "action": "hold load",
                "intention": "prove the mass is still there",
                "is_extreme": True,
                "marked_as_key": True,
                "arc": {"anticipation_frames": 0, "follow_through_frames": 10},
            },
        ],
        timing={
            "id": "timing_eval_physical",
            "fps": 24,
            "start_frame": 1,
            "end_frame": 72,
            "allow_auto_smooth": False,
            "holds": [
                {"start": 52, "duration": 14, "kind": "hold", "note": "weight settle"},
            ],
            "spacing_mode": "slow_in",
            "smear_hint_frames": [20],
        },
        sound_cues=[
            {
                "id": "scue_phys_breath",
                "kind": "breath",
                "time_sec": 0.3,
                "label": "effort breath",
                "motion_response": "move",
            },
            {
                "id": "scue_phys_impact",
                "kind": "impact",
                "time_sec": 1.5,
                "label": "crate scrape / lift",
                "motion_response": "move",
            },
            {
                "id": "scue_phys_env",
                "kind": "environmental",
                "time_sec": 2.2,
                "label": "room tone",
                "motion_response": "non_reaction",
            },
        ],
        sequence_neighbors={
            "previous_shot_id": "shot_eval_physical_prev",
            "next_shot_id": "shot_eval_physical_next",
            "previous_note": "Hands approach crate — no lift yet",
            "next_note": "Carry through doorway — continuous weight",
        },
        revision_notes="v1 physical pass — weight and timing focus",
    )


def quiet_scene() -> EvalSceneFixture:
    return EvalSceneFixture(
        id="eval_scene_quiet",
        kind=SceneKind.QUIET,
        title="Window light — stillness and subtext",
        summary=(
            "A quiet beat: character alone at a window. Stillness, long holds, "
            "and emotional subtext without busy acting."
        ),
        craft_focus=[
            "stillness and intentional holds",
            "emotional subtext in intent and sparse poses",
            "silence as a valid sound choice",
            "sequence context from louder previous beat into calm",
        ],
        success_criteria=[
            "Stillness reads as choice, not missing animation",
            "Silence / non_reaction cues remain valid",
            "Subtext is stated in intent — not invented by auto-metrics",
        ],
        shot_id="shot_eval_quiet",
        sequence_id="seq_eval_harness",
        intent={
            "purpose": "Let the character sit with unresolved news in silence",
            "emotional_beat": "hollow calm — grief under composure",
            "staging_goal": "Profile against window; sparse gesture",
            "animation_priority": "atmosphere",
            "must_read_silhouette": True,
            "hold_for_lyric": True,
            "notes": "Do not fill the quiet with busy secondary action",
        },
        key_poses=[
            {
                "id": "pose_quiet_arrive",
                "frame": 1,
                "label": "arrive at window",
                "action": "settle into stillness",
                "intention": "choose not to speak",
                "is_extreme": True,
                "marked_as_key": True,
            },
            {
                "id": "pose_quiet_micro",
                "frame": 60,
                "label": "micro shift of breath",
                "action": "tiny weight shift",
                "intention": "alive stillness — not dead hold",
                "is_extreme": False,
                "marked_as_key": True,
            },
            {
                "id": "pose_quiet_end",
                "frame": 120,
                "label": "eyes lower",
                "action": "accept the quiet",
                "intention": "close the emotional beat without a speech",
                "is_extreme": True,
                "marked_as_key": True,
            },
        ],
        timing={
            "id": "timing_eval_quiet",
            "fps": 24,
            "start_frame": 1,
            "end_frame": 144,
            "allow_auto_smooth": False,
            "holds": [
                {"start": 12, "duration": 40, "kind": "hold", "note": "primary stillness"},
                {"start": 72, "duration": 36, "kind": "hold", "note": "after micro shift"},
            ],
            "spacing_mode": "stepped",
        },
        sound_cues=[
            {
                "id": "scue_quiet_silence",
                "kind": "silence",
                "time_sec": 0.0,
                "end_time_sec": 4.0,
                "label": "authored silence",
                "motion_response": "silence",
            },
            {
                "id": "scue_quiet_breath",
                "kind": "breath",
                "time_sec": 2.5,
                "label": "barely audible breath",
                "motion_response": "non_reaction",
            },
            {
                "id": "scue_quiet_env",
                "kind": "environmental",
                "time_sec": 1.0,
                "label": "distant traffic",
                "motion_response": "non_reaction",
            },
        ],
        sequence_neighbors={
            "previous_shot_id": "shot_eval_quiet_prev",
            "next_shot_id": "shot_eval_quiet_next",
            "previous_note": "Loud argument — high energy exit",
            "next_note": "Cut to empty table — aftermath",
        },
        revision_notes="v1 quiet pass — stillness and subtext focus",
    )


HARNESS_SCENES: tuple[EvalSceneFixture, ...] = (
    dialogue_scene(),
    physical_action_scene(),
    quiet_scene(),
)


def get_scene(scene_id: str) -> EvalSceneFixture:
    for s in HARNESS_SCENES:
        if s.id == scene_id or s.kind.value == scene_id:
            return s
    raise KeyError(f"Unknown eval scene: {scene_id}")


def list_scenes() -> list[EvalSceneFixture]:
    return list(HARNESS_SCENES)
