# Short-sequence craft pilot — findings

Sequence: `seq_pilot_short` · Focus shot: `shot_pilot_main`

**Original intent:** Land a clear apology line, then a delayed listener reaction — readable acting without busy lip chatter.

**Final lifecycle:** `approved` · Intent preserved (text): `True` · Revision history understandable: `True`

Short sequence pilot completed 11/11 stages. Findings: P0=1 P1=3 P2=4. No product features added during pilot.

Policy: no product features were added during the pilot (`features_added_during_pilot=false`). No aggregate quality score.

## Measurements

- Stages completed: intent, storyboard, layout, animatic, key_poses, timing, in_betweens, sound, review, revision, approval
- Suggestions accepted: 1
- Suggestions rejected: 1
- Suggestions deferred (assistants / incomplete): 2
- Revisions: 34 · Provenance: 40

### Suggestion outcomes

- **deferred** `pose_assistant` `asug_5e5c242bdcc1` — Assistant returns suggestions only; not applied silently.
- **deferred** `timing_assistant` `asug_cb5945a6cc2e` — Timing assistant suggest-only; human did not apply auto spacing.
- **accepted** `inbetween_slots` `sug_d08142c8839b` — Spacing slow_out between hesitate→apology accepted for pilot.
- **rejected** `inbetween_slots` `sug_8484ad7bf3c8` — Linear into hold undermines stillness; rejected with comment.

## Findings by priority

### P0

#### No first-class final-approval workflow after sound_edit_review

- **Axis:** user_confusion
- **Stage:** approval
- **Demonstrated failure:** True
- **Detail:** Lifecycle states exist through final_review → approved, but the pilot had to call transition_shot manually. Users following CLI modules (storyboard, keypose, timing, sound, critique) have no clear 'finish the shot' command; easy to stop after animatic approve without a final_review command.
- **Evidence:** `{"from": "sound_edit_review", "needed": ["final_review", "approved"]}`

### P1

#### Animatic approve can auto-create a layout stub

- **Axis:** unjustified_assumption
- **Stage:** layout
- **Demonstrated failure:** False
- **Detail:** approve_animatic._ensure_layout_for_animatic invents a layout from the shot when missing. It is labeled, but users may not notice and may treat stub camera/placement as intentional craft.
- **Evidence:** `{"api": "mvm.storyboard.approve._ensure_layout_for_animatic"}`

#### Revision trail spans many operations without a sequence-level timeline UI

- **Axis:** revision_history
- **Stage:** revision
- **Demonstrated failure:** False
- **Detail:** Pilot produced 34 revisions and 40 provenance records. Inspectable on disk, but there is no single sequence timeline that groups animatic/key/timing/sound/review events for a human walkthrough.
- **Evidence:** `{"revision_count": 34, "provenance_count": 40, "sample_ops": ["assistant.timing.suggest", "human.timing_create", "human.craft_review_add_critique", "human.sound_plan_create", "human.craft_review_add_critique", "pilot.short_sequence.complete", "human.mark_key_pose", "human.craft_review_add_critique", "human.approve_key_pose", "human.reject_inbetween_suggestion", "human.sound_to_motion_link", "human`

#### Lifecycle order vs CLI order is non-obvious

- **Axis:** user_confusion
- **Stage:** storyboard
- **Demonstrated failure:** False
- **Detail:** Legal path is intent→storyboard→layout→animatic, but panels jump to storyboard and animatic approve may create layout. Users can think layout is optional scenery rather than a gate.
- **Evidence:** `{"legal": "INTENT\u2192STORYBOARD\u2192LAYOUT\u2192ANIMATIC"}`

### P2

#### Animatic gate correctly leaves shot.approval pending

- **Axis:** user_confusion
- **Stage:** animatic
- **Demonstrated failure:** False
- **Detail:** animatic_approved unlocks keys; shot.approval stays pending_review until final_review → approved.
- **Evidence:** `{"lifecycle_state": "animatic", "approval": "pending_review", "animatic_approved": true}`

#### Intent string preserved; visual communication still needs human eye

- **Axis:** intent_communication
- **Stage:** approval
- **Demonstrated failure:** False
- **Detail:** Purpose text survived the pipeline unchanged. That is necessary but not sufficient — pilot cannot verify drawn acting without artwork.
- **Evidence:** `{"purpose": "Land a clear apology line, then a delayed listener reaction \u2014 readable acting without busy lip chatter."}`

#### Narrow assistants correctly stay suggestion-only

- **Axis:** suggestion_accepted
- **Stage:** key_poses
- **Demonstrated failure:** False
- **Detail:** Pose/timing assistants recorded provenance and deferred application. Accepted/rejected craft suggestions in this pilot came from keypose in-between workflow, which has explicit accept/reject.
- **Evidence:** `{"accepted": 1, "rejected": 1, "deferred": 2}`

#### Sound plan is not auto-linked into lifecycle gates

- **Axis:** unjustified_assumption
- **Stage:** sound
- **Demonstrated failure:** False
- **Detail:** Entering sound_edit_review only needs prior transitions/timing — a shot can reach sound_edit_review with an empty sound plan. Not forced (good), but easy to assume sound was reviewed when only the state changed.

## Stage log (abbrev)

- `intent` [ok] — Explicit ShotIntent required and recorded.
- `storyboard` [ok] — Three panels linked; lifecycle moved to storyboard on first panel.
- `layout` [ok] — Explicit layout authored before animatic approve.
- `animatic` [ok] — Animatic built and human-approved; key poses unlocked; shot.approval=pending_review.
- `key_poses` [ok] — Three keys marked; A/B approved; C remains draft by choice.
- `timing` [ok] — Timing plan + hold authored; allow_auto_smooth remains false.
- `in_betweens` [ok] — Accepted one in-between suggestion; rejected another with reason.
- `sound` [ok] — Dialogue + silence cues; silence maps to hold (not forced chatter).
- `review` [ok] — Multi-category craft review stored; no aggregate score.
- `revision` [ok] — Revision + provenance persisted for each meaningful step.
- `approval` [ok] — Reached lifecycle approved via explicit transitions.
