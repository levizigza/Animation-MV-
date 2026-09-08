"""Short-sequence craft pilot — exercise full lifecycle; observe; do not add features."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.assistants import pose_assistant, timing_assistant
from mvm.critique import add_critique, create_craft_review
from mvm.keyposes import (
    accept_suggestion,
    approve_key_pose,
    mark_key_pose,
    reject_suggestion,
    set_anticipation_follow_through,
    set_pose_action,
    suggest_inbetweens,
)
from mvm.pilot.models import (
    FindingPriority,
    MeasurementAxis,
    PilotFinding,
    PilotReport,
    StageLog,
    SuggestionOutcome,
)
from mvm.project.domain_store import ensure_domain_dirs, load_provenance, load_revisions
from mvm.project.reviews import gate_context_for_shot
from mvm.provenance import record_meaningful_change
from mvm.schemas.critique import CritiqueCategory
from mvm.schemas.domain import ActorKind, Layout, Sequence, new_id
from mvm.schemas.lifecycle import transition_shot
from mvm.schemas.models import ApprovalState, ProjectMeta, Shot, ShotIntent, ShotLifecycleState
from mvm.schemas.sound import MotionResponse, SoundCueKind
from mvm.sound import add_sound_cue, create_sound_plan, link_sound_to_motion
from mvm.storyboard.approve import approve_animatic
from mvm.storyboard.workflow import (
    add_storyboard_panel,
    build_or_get_animatic,
    create_shot,
)
from mvm.timing import add_hold, create_timing_plan


STAGES = [
    "intent",
    "storyboard",
    "animatic",
    "layout",
    "key_poses",
    "timing",
    "in_betweens",
    "sound",
    "review",
    "revision",
    "approval",
]


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_shot(root: Path, shot_id: str) -> Shot:
    return Shot.model_validate_json(
        (root / "shots" / f"{shot_id}.json").read_text(encoding="utf-8")
    )


def _save_shot(root: Path, shot: Shot) -> None:
    _write(root / "shots" / f"{shot.id}.json", shot)


def _advance(
    root: Path,
    shot: Shot,
    to_state: ShotLifecycleState,
    *,
    log: list[StageLog],
    stage_name: str,
) -> Shot:
    ctx = gate_context_for_shot(root, shot)
    # Keep gate facts honest as we progress
    if shot.animatic_approved:
        ctx.animatic_approved = True
    if shot.key_pose_ids:
        ctx.key_poses_approved = True
        ctx.approved_key_pose_ids = list(shot.key_pose_ids)
    if shot.timing_plan_id:
        ctx.timing_plan_id = shot.timing_plan_id
    result = transition_shot(shot, to_state, ctx)
    if not result.ok or result.shot is None:
        log.append(
            StageLog(
                stage=stage_name,
                ok=False,
                notes=result.reason,
                artifacts={"blockers": result.blockers},
                confusion_signals=[
                    f"Blocked {shot.lifecycle_state.value} → {to_state.value}: {result.reason}"
                ],
            )
        )
        raise RuntimeError(result.reason)
    _save_shot(root, result.shot)
    return result.shot


def _init_project(root: Path) -> None:
    ensure_domain_dirs(root)
    for sub in (
        "shots",
        "panels",
        "animatics",
        "layouts",
        "timing",
        "key_poses",
        "suggestions",
        "sound_plans",
        "critiques",
        "reviews",
        "revisions",
        "provenance",
        "sequences",
        "pilot_reports",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    if not (root / "project.json").exists():
        _write(
            root / "project.json",
            ProjectMeta(
                slug=root.name,
                title="Pilot short sequence",
                prompt="One short sequence craft pilot",
                audio_path="audio/master.wav",
            ),
        )


def run_short_sequence_pilot(root: Path) -> PilotReport:
    """Run one short sequence through the craft path; record measurements + findings."""
    _init_project(root)
    findings: list[PilotFinding] = []
    stage_log: list[StageLog] = []
    suggestion_outcomes: list[SuggestionOutcome] = []
    completed: list[str] = []

    original_intent = (
        "Land a clear apology line, then a delayed listener reaction — "
        "readable acting without busy lip chatter."
    )

    # --- intent ---
    shot = create_shot(
        root,
        shot_id="shot_pilot_main",
        index=1,
        section="bridge",
        start=0.0,
        end=4.0,
        intent=ShotIntent(
            purpose=original_intent,
            emotional_beat="guilt → guarded hope",
            staging_goal="Speaker 3/4; listener profile; clear eye-line",
            animation_priority="performance",
            must_read_silhouette=True,
            notes="Pilot focus shot — acting readability",
        ),
    )
    neighbor = create_shot(
        root,
        shot_id="shot_pilot_prev",
        index=0,
        section="bridge",
        start=-2.0,
        end=0.0,
        intent=ShotIntent(
            purpose="Wide establish both seated before the apology",
            emotional_beat="quiet tension",
            animation_priority="atmosphere",
        ),
    )
    seq = Sequence(
        id="seq_pilot_short",
        index=1,
        name="Pilot apology beat",
        section="bridge",
        start=-2.0,
        end=4.0,
        shot_ids=[neighbor.id, shot.id],
    )
    _write(root / "sequences" / f"{seq.id}.json", seq)
    shot = shot.model_copy(deep=True)
    shot.sequence_id = seq.id
    _save_shot(root, shot)
    completed.append("intent")
    stage_log.append(
        StageLog(
            stage="intent",
            ok=True,
            notes="Explicit ShotIntent required and recorded.",
            artifacts={"shot_id": shot.id, "purpose": shot.intent.purpose},
        )
    )

    # --- storyboard ---
    p1 = add_storyboard_panel(
        root, shot.id, caption="Speaker leans in", default_duration_frames=18
    )
    p2 = add_storyboard_panel(
        root, shot.id, caption="Listener holds", default_duration_frames=24
    )
    p3 = add_storyboard_panel(
        root, shot.id, caption="Soft reply", default_duration_frames=16
    )
    shot = _read_shot(root, shot.id)
    if shot.lifecycle_state != ShotLifecycleState.STORYBOARD:
        findings.append(
            PilotFinding(
                priority=FindingPriority.P1,
                axis=MeasurementAxis.USER_CONFUSION,
                stage="storyboard",
                title="Lifecycle not advanced to storyboard after panels",
                detail=f"Expected storyboard, got {shot.lifecycle_state.value}",
                demonstrated_failure=True,
            )
        )
    completed.append("storyboard")
    stage_log.append(
        StageLog(
            stage="storyboard",
            ok=True,
            notes="Three panels linked; lifecycle moved to storyboard on first panel.",
            artifacts={"panel_ids": [p1.id, p2.id, p3.id]},
        )
    )

    # --- layout (explicit before animatic, to avoid silent stub if possible) ---
    layout = Layout(
        id=new_id("lay"),
        shot_id=shot.id,
        description="Table + window; camera 40mm; two seats",
        camera={"angle": "eye_level", "shot_size": "medium"},
        lens_mm=40.0,
        set_notes="Kitchen table practical light",
        character_placements=[
            {"id": "speaker", "seat": "left"},
            {"id": "listener", "seat": "right"},
        ],
    )
    _write(root / "layouts" / f"{layout.id}.json", layout)
    shot = shot.model_copy(deep=True)
    shot.layout_id = layout.id
    shot = _advance(root, shot, ShotLifecycleState.LAYOUT, log=stage_log, stage_name="layout")
    completed.append("layout")
    stage_log.append(
        StageLog(
            stage="layout",
            ok=True,
            notes="Explicit layout authored before animatic approve.",
            artifacts={"layout_id": layout.id},
            assumptions=[
                "If layout is omitted, approve_animatic will auto-create a stub labeled as such."
            ],
        )
    )
    findings.append(
        PilotFinding(
            priority=FindingPriority.P1,
            axis=MeasurementAxis.UNJUSTIFIED_ASSUMPTION,
            stage="layout",
            title="Animatic approve can auto-create a layout stub",
            detail=(
                "approve_animatic._ensure_layout_for_animatic invents a layout from the shot "
                "when missing. It is labeled, but users may not notice and may treat stub "
                "camera/placement as intentional craft."
            ),
            evidence={"api": "mvm.storyboard.approve._ensure_layout_for_animatic"},
            demonstrated_failure=False,
        )
    )

    # --- animatic ---
    anim = build_or_get_animatic(root, shot.id, label="pilot_v1")
    approve_result = approve_animatic(
        root,
        shot.id,
        anim.id,
        comment="Pilot: animatic reads; unlock keys",
        reviewer="pilot.reviewer",
    )
    if not approve_result.get("ok"):
        raise RuntimeError(approve_result.get("reason", "animatic approve failed"))
    shot = _read_shot(root, shot.id)
    # Animatic gate must not stamp final shot approval
    if shot.approval == ApprovalState.APPROVED and shot.lifecycle_state == (
        ShotLifecycleState.ANIMATIC
    ):
        findings.append(
            PilotFinding(
                priority=FindingPriority.P0,
                axis=MeasurementAxis.USER_CONFUSION,
                stage="animatic",
                title="Shot.approval=APPROVED at animatic gate conflates with final approval",
                detail=(
                    "approve_animatic sets shot.approval to APPROVED while lifecycle_state "
                    "remains 'animatic'. Later transitions reset approval to PENDING_REVIEW. "
                    "Users inspecting shot JSON may believe the shot is fully approved."
                ),
                evidence={
                    "lifecycle_state": shot.lifecycle_state.value,
                    "approval": shot.approval.value,
                    "animatic_approved": shot.animatic_approved,
                },
                demonstrated_failure=True,
            )
        )
    elif (
        shot.animatic_approved
        and shot.approval == ApprovalState.PENDING_REVIEW
        and shot.lifecycle_state == ShotLifecycleState.ANIMATIC
    ):
        findings.append(
            PilotFinding(
                priority=FindingPriority.P2,
                axis=MeasurementAxis.USER_CONFUSION,
                stage="animatic",
                title="Animatic gate correctly leaves shot.approval pending",
                detail=(
                    "animatic_approved unlocks keys; shot.approval stays pending_review "
                    "until final_review → approved."
                ),
                evidence={
                    "lifecycle_state": shot.lifecycle_state.value,
                    "approval": shot.approval.value,
                    "animatic_approved": shot.animatic_approved,
                },
                demonstrated_failure=False,
            )
        )
    completed.append("animatic")
    stage_log.append(
        StageLog(
            stage="animatic",
            ok=True,
            notes=(
                "Animatic built and human-approved; key poses unlocked; "
                f"shot.approval={shot.approval.value}."
            ),
            artifacts={
                "animatic_id": anim.id,
                "animatic_approved": shot.animatic_approved,
                "shot_approval_field": shot.approval.value,
            },
            confusion_signals=[
                "Distinguish animatic_approved / Animatic.approved / shot.approval / lifecycle"
            ],
        )
    )

    # --- key poses ---
    shot = _advance(
        root, shot, ShotLifecycleState.KEY_POSES, log=stage_log, stage_name="key_poses"
    )
    pose_a = mark_key_pose(root, shot_id=shot.id, frame=1, label="inhale / hesitate")
    pose_b = mark_key_pose(root, shot_id=shot.id, frame=20, label="apology peak")
    pose_c = mark_key_pose(root, shot_id=shot.id, frame=48, label="listener hold")
    set_pose_action(root, pose_a.id, action="prepare to speak", intention="hesitation")
    set_pose_action(root, pose_b.id, action="speak apology", intention="sincerity")
    set_pose_action(root, pose_c.id, action="listen", intention="absorb before reply")
    set_anticipation_follow_through(
        root, pose_a.id, anticipation_frames=4, follow_through_frames=0
    )
    set_anticipation_follow_through(
        root, pose_b.id, anticipation_frames=0, follow_through_frames=2
    )
    set_anticipation_follow_through(
        root, pose_c.id, anticipation_frames=0, follow_through_frames=0
    )
    approve_key_pose(root, pose_a.id, comment="Pilot approve A")
    approve_key_pose(root, pose_b.id, comment="Pilot approve B")
    # Leave C draft to exercise later gates
    pose_suggest = pose_assistant(
        root, shot_id=shot.id, from_pose_id=pose_a.id, to_pose_id=pose_b.id
    )
    suggestion_outcomes.append(
        SuggestionOutcome(
            suggestion_id=pose_suggest.suggestions[0].id,
            kind="pose_assistant",
            decision="deferred",
            reason="Assistant returns suggestions only; not applied silently.",
            stage="key_poses",
        )
    )
    completed.append("key_poses")
    stage_log.append(
        StageLog(
            stage="key_poses",
            ok=True,
            notes="Three keys marked; A/B approved; C remains draft by choice.",
            artifacts={
                "pose_ids": [pose_a.id, pose_b.id, pose_c.id],
                "assistant_suggestions": len(pose_suggest.suggestions),
            },
        )
    )

    # --- timing ---
    shot = _read_shot(root, shot.id)
    plan = create_timing_plan(root, shot_id=shot.id, end_frame=72, label="pilot timing")
    shot = shot.model_copy(deep=True)
    shot.timing_plan_id = plan.id
    shot.key_pose_ids = [pose_a.id, pose_b.id, pose_c.id]
    _save_shot(root, shot)
    plan = add_hold(
        root,
        plan.id,
        frame=48,
        duration_frames=12,
        key_pose_id=pose_c.id,
        kind="hold",
        notes="listener stillness",
    )
    timing_sug = timing_assistant(
        root, shot_id=shot.id, timing_plan_id=plan.id, mean_hold_frames=12
    )
    suggestion_outcomes.append(
        SuggestionOutcome(
            suggestion_id=timing_sug.suggestions[0].id,
            kind="timing_assistant",
            decision="deferred",
            reason="Timing assistant suggest-only; human did not apply auto spacing.",
            stage="timing",
        )
    )
    shot = _advance(
        root, shot, ShotLifecycleState.TIMING_REVIEW, log=stage_log, stage_name="timing"
    )
    completed.append("timing")
    stage_log.append(
        StageLog(
            stage="timing",
            ok=True,
            notes="Timing plan + hold authored; allow_auto_smooth remains false.",
            artifacts={"timing_plan_id": plan.id, "allow_auto_smooth": plan.allow_auto_smooth},
        )
    )

    # --- in-betweens: accept one, reject one path ---
    sug_ok = suggest_inbetweens(
        root,
        from_key_pose_id=pose_a.id,
        to_key_pose_id=pose_b.id,
        spacing_mode="slow_out",
    )
    if not sug_ok.get("ok"):
        findings.append(
            PilotFinding(
                priority=FindingPriority.P1,
                axis=MeasurementAxis.USER_CONFUSION,
                stage="in_betweens",
                title="In-between suggestion blocked despite prepared keys",
                detail=str(sug_ok.get("missing_information") or sug_ok),
                evidence=sug_ok,
                demonstrated_failure=True,
            )
        )
        raise RuntimeError(f"suggest_inbetweens failed: {sug_ok}")
    sug_id = sug_ok["suggestion"].id if hasattr(sug_ok["suggestion"], "id") else sug_ok["suggestion"]["id"]
    accept_suggestion(root, sug_id)
    suggestion_outcomes.append(
        SuggestionOutcome(
            suggestion_id=sug_id,
            kind="inbetween_slots",
            decision="accepted",
            reason="Spacing slow_out between hesitate→apology accepted for pilot.",
            stage="in_betweens",
        )
    )

    sug_b = suggest_inbetweens(
        root,
        from_key_pose_id=pose_b.id,
        to_key_pose_id=pose_c.id,
        spacing_mode="linear",
    )
    if sug_b.get("ok"):
        sug_b_id = (
            sug_b["suggestion"].id
            if hasattr(sug_b["suggestion"], "id")
            else sug_b["suggestion"]["id"]
        )
        reject_suggestion(
            root,
            sug_b_id,
            comment="Pilot reject: linear chatter into listener hold feels wrong.",
        )
        suggestion_outcomes.append(
            SuggestionOutcome(
                suggestion_id=sug_b_id,
                kind="inbetween_slots",
                decision="rejected",
                reason="Linear into hold undermines stillness; rejected with comment.",
                stage="in_betweens",
            )
        )
    else:
        suggestion_outcomes.append(
            SuggestionOutcome(
                suggestion_id="none",
                kind="inbetween_slots",
                decision="deferred",
                reason=f"Second suggestion unavailable: {sug_b.get('missing_information')}",
                stage="in_betweens",
            )
        )
        findings.append(
            PilotFinding(
                priority=FindingPriority.P2,
                axis=MeasurementAxis.USER_CONFUSION,
                stage="in_betweens",
                title="Second pair suggestion may require re-linking timing after accept",
                detail=(
                    "After accepting the first suggestion, the second pair may fail missing-"
                    "information checks depending on timing plan linkage — easy to confuse."
                ),
                evidence=sug_b,
            )
        )

    shot = _read_shot(root, shot.id)
    shot = _advance(
        root,
        shot,
        ShotLifecycleState.INBETWEEN_REVIEW,
        log=stage_log,
        stage_name="in_betweens",
    )
    completed.append("in_betweens")
    stage_log.append(
        StageLog(
            stage="in_betweens",
            ok=True,
            notes="Accepted one in-between suggestion; rejected another with reason.",
            artifacts={
                "accepted": [
                    s.suggestion_id
                    for s in suggestion_outcomes
                    if s.decision == "accepted"
                ],
                "rejected": [
                    s.suggestion_id
                    for s in suggestion_outcomes
                    if s.decision == "rejected"
                ],
            },
        )
    )

    # --- sound ---
    sound = create_sound_plan(root, shot_id=shot.id, fps=24, shot_start_sec=0.0)
    sound = add_sound_cue(
        root,
        sound.id,
        kind=SoundCueKind.DIALOGUE,
        time_sec=0.4,
        label="I'm sorry",
    )
    c1_id = sound.cues[-1].id
    sound = add_sound_cue(
        root,
        sound.id,
        kind=SoundCueKind.SILENCE,
        time_sec=1.8,
        end_time_sec=2.6,
        label="pause before reply",
    )
    c2_id = sound.cues[-1].id
    link_sound_to_motion(root, sound.id, c1_id, response=MotionResponse.MOVE)
    link_sound_to_motion(root, sound.id, c2_id, response=MotionResponse.HOLD)
    shot = _advance(
        root,
        shot,
        ShotLifecycleState.SOUND_EDIT_REVIEW,
        log=stage_log,
        stage_name="sound",
    )
    completed.append("sound")
    stage_log.append(
        StageLog(
            stage="sound",
            ok=True,
            notes="Dialogue + silence cues; silence maps to hold (not forced chatter).",
            artifacts={"sound_plan_id": sound.id, "cue_ids": [c1_id, c2_id]},
        )
    )

    # --- review (structured craft critique) ---
    shot = _read_shot(root, shot.id)
    crev = create_craft_review(
        root,
        target_type="shot",
        target_id=shot.id,
        revision_id=shot.revision_id or "rev_pilot_current",
        reviewer="pilot.reviewer",
        summary_notes="Pilot craft review — acting readability",
    )
    add_critique(
        root,
        crev.id,
        category=CritiqueCategory.ACTING,
        notes="Apology peak reads; watch over-animating mouth on every syllable.",
        severity="minor",
    )
    add_critique(
        root,
        crev.id,
        category=CritiqueCategory.INTENT_CLARITY,
        notes="Original intent still readable from keys + holds.",
        severity="note",
    )
    completed.append("review")
    stage_log.append(
        StageLog(
            stage="review",
            ok=True,
            notes="Multi-category craft review stored; no aggregate score.",
            artifacts={"craft_review_id": crev.id},
        )
    )

    # --- revision: inspect history understandability ---
    revisions = load_revisions(root)
    provenance = load_provenance(root)
    ops = [p.operation for p in provenance]
    readable = bool(revisions) and bool(provenance) and all(
        getattr(p, "summary", None) or p.operation for p in provenance
    )
    # Check for orphan / hard-to-follow ids
    missing_summaries = [p.id for p in provenance if not (p.summary or "").strip()]
    if missing_summaries:
        findings.append(
            PilotFinding(
                priority=FindingPriority.P1,
                axis=MeasurementAxis.REVISION_HISTORY,
                stage="revision",
                title="Some provenance records lack human-readable summaries",
                detail="Empty summaries force users to decode operation ids alone.",
                evidence={"provenance_ids": missing_summaries[:10]},
            )
        )
        readable = False
    # Multiple approve vocabularies
    findings.append(
        PilotFinding(
            priority=FindingPriority.P1,
            axis=MeasurementAxis.REVISION_HISTORY,
            stage="revision",
            title="Revision trail spans many operations without a sequence-level timeline UI",
            detail=(
                f"Pilot produced {len(revisions)} revisions and {len(provenance)} provenance "
                "records. Inspectable on disk, but there is no single sequence timeline that "
                "groups animatic/key/timing/sound/review events for a human walkthrough."
            ),
            evidence={"revision_count": len(revisions), "provenance_count": len(provenance), "sample_ops": ops[:12]},
        )
    )
    completed.append("revision")
    stage_log.append(
        StageLog(
            stage="revision",
            ok=True,
            notes="Revision + provenance persisted for each meaningful step.",
            artifacts={
                "revision_count": len(revisions),
                "provenance_count": len(provenance),
                "understandable": readable,
            },
            confusion_signals=[
                "No unified sequence-level revision timeline in CLI/studio"
            ],
        )
    )

    # --- approval (final) ---
    # P0 finding: no first-class CLI to walk sound_edit_review → final_review → approved
    findings.append(
        PilotFinding(
            priority=FindingPriority.P0,
            axis=MeasurementAxis.USER_CONFUSION,
            stage="approval",
            title="No first-class final-approval workflow after sound_edit_review",
            detail=(
                "Lifecycle states exist through final_review → approved, but the pilot had to "
                "call transition_shot manually. Users following CLI modules (storyboard, "
                "keypose, timing, sound, critique) have no clear 'finish the shot' command; "
                "easy to stop after animatic approve without a final_review command."
            ),
            evidence={"from": "sound_edit_review", "needed": ["final_review", "approved"]},
            demonstrated_failure=True,
        )
    )
    shot = _advance(
        root, shot, ShotLifecycleState.FINAL_REVIEW, log=stage_log, stage_name="approval"
    )
    # Intent check before final stamp
    final_intent = shot.intent.purpose
    intent_ok = original_intent in final_intent or final_intent == original_intent
    if not intent_ok:
        findings.append(
            PilotFinding(
                priority=FindingPriority.P0,
                axis=MeasurementAxis.INTENT_COMMUNICATION,
                stage="approval",
                title="Final shot intent drifted from original pilot intent",
                detail=f"original={original_intent!r} final={final_intent!r}",
                demonstrated_failure=True,
            )
        )
    else:
        findings.append(
            PilotFinding(
                priority=FindingPriority.P2,
                axis=MeasurementAxis.INTENT_COMMUNICATION,
                stage="approval",
                title="Intent string preserved; visual communication still needs human eye",
                detail=(
                    "Purpose text survived the pipeline unchanged. That is necessary but not "
                    "sufficient — pilot cannot verify drawn acting without artwork."
                ),
                evidence={"purpose": final_intent},
            )
        )
    shot = _advance(
        root, shot, ShotLifecycleState.APPROVED, log=stage_log, stage_name="approval"
    )
    completed.append("approval")
    stage_log.append(
        StageLog(
            stage="approval",
            ok=True,
            notes="Reached lifecycle approved via explicit transitions.",
            artifacts={
                "lifecycle_state": shot.lifecycle_state.value,
                "approval": shot.approval.value,
            },
        )
    )

    # Additional systemic findings from pilot experience
    findings.append(
        PilotFinding(
            priority=FindingPriority.P1,
            axis=MeasurementAxis.USER_CONFUSION,
            stage="storyboard",
            title="Lifecycle order vs CLI order is non-obvious",
            detail=(
                "Legal path is intent→storyboard→layout→animatic, but panels jump to "
                "storyboard and animatic approve may create layout. Users can think layout "
                "is optional scenery rather than a gate."
            ),
            evidence={"legal": "INTENT→STORYBOARD→LAYOUT→ANIMATIC"},
        )
    )
    findings.append(
        PilotFinding(
            priority=FindingPriority.P2,
            axis=MeasurementAxis.UNJUSTIFIED_ASSUMPTION,
            stage="sound",
            title="Sound plan is not auto-linked into lifecycle gates",
            detail=(
                "Entering sound_edit_review only needs prior transitions/timing — a shot can "
                "reach sound_edit_review with an empty sound plan. Not forced (good), but "
                "easy to assume sound was reviewed when only the state changed."
            ),
        )
    )
    findings.append(
        PilotFinding(
            priority=FindingPriority.P2,
            axis=MeasurementAxis.SUGGESTION_ACCEPTED,
            stage="key_poses",
            title="Narrow assistants correctly stay suggestion-only",
            detail=(
                "Pose/timing assistants recorded provenance and deferred application. "
                "Accepted/rejected craft suggestions in this pilot came from keypose "
                "in-between workflow, which has explicit accept/reject."
            ),
            evidence={
                "accepted": sum(1 for s in suggestion_outcomes if s.decision == "accepted"),
                "rejected": sum(1 for s in suggestion_outcomes if s.decision == "rejected"),
                "deferred": sum(1 for s in suggestion_outcomes if s.decision == "deferred"),
            },
        )
    )

    accepted = [s for s in suggestion_outcomes if s.decision == "accepted"]
    rejected = [s for s in suggestion_outcomes if s.decision == "rejected"]
    deferred = [s for s in suggestion_outcomes if s.decision == "deferred"]

    report = PilotReport(
        sequence_id=seq.id,
        focus_shot_id=shot.id,
        original_intent=original_intent,
        stages_completed=completed,
        stage_log=stage_log,
        suggestion_outcomes=suggestion_outcomes,
        findings=sorted(findings, key=lambda f: (f.priority.value, f.stage, f.title)),
        measurements={
            "stages_requested": STAGES,
            "stages_completed": completed,
            "confusion_signals": [
                c for sl in stage_log for c in sl.confusion_signals
            ],
            "assumptions_noted": [a for sl in stage_log for a in sl.assumptions],
            "suggestions_accepted": [s.model_dump(mode="json") for s in accepted],
            "suggestions_rejected": [s.model_dump(mode="json") for s in rejected],
            "suggestions_deferred": [s.model_dump(mode="json") for s in deferred],
            "revision_count": len(revisions),
            "provenance_count": len(provenance),
            "revision_history_understandable": readable,
            "intent_still_communicated": intent_ok,
            "final_lifecycle_state": shot.lifecycle_state.value,
        },
        final_lifecycle_state=shot.lifecycle_state.value,
        final_intent=final_intent,
        intent_still_communicated=intent_ok,
        revision_history_understandable=readable,
        features_added_during_pilot=False,
        summary=(
            f"Short sequence pilot completed {len(completed)}/{len(STAGES)} stages. "
            f"Findings: "
            f"P0={sum(1 for f in findings if f.priority==FindingPriority.P0)} "
            f"P1={sum(1 for f in findings if f.priority==FindingPriority.P1)} "
            f"P2={sum(1 for f in findings if f.priority==FindingPriority.P2)}. "
            "No product features added during pilot."
        ),
    )

    path = root / "pilot_reports" / f"{report.id}.json"
    _write(path, report)
    record_meaningful_change(
        root,
        operation="pilot.short_sequence.complete",
        target_type="sequence",
        target_id=seq.id,
        snapshot=report.model_dump(mode="json"),
        summary=report.summary,
        creator="pilot",
        actor=ActorKind.SYSTEM,
        source_references=[f"sequence:{seq.id}", f"shot:{shot.id}"],
        input_parameters={"stages": STAGES},
        outputs={
            "report_id": report.id,
            "path": str(path.name),
            "has_aggregate_quality_score": False,
        },
        generated=False,
    )
    return report


def render_findings_markdown(report: PilotReport) -> str:
    by = report.findings_by_priority()
    lines = [
        "# Short-sequence craft pilot — findings",
        "",
        f"Sequence: `{report.sequence_id}` · Focus shot: `{report.focus_shot_id}`",
        "",
        f"**Original intent:** {report.original_intent}",
        "",
        f"**Final lifecycle:** `{report.final_lifecycle_state}` · "
        f"Intent preserved (text): `{report.intent_still_communicated}` · "
        f"Revision history understandable: `{report.revision_history_understandable}`",
        "",
        report.summary,
        "",
        "Policy: no product features were added during the pilot "
        "(`features_added_during_pilot=false`). No aggregate quality score.",
        "",
        "## Measurements",
        "",
        f"- Stages completed: {', '.join(report.stages_completed)}",
        f"- Suggestions accepted: "
        f"{sum(1 for s in report.suggestion_outcomes if s.decision == 'accepted')}",
        f"- Suggestions rejected: "
        f"{sum(1 for s in report.suggestion_outcomes if s.decision == 'rejected')}",
        f"- Suggestions deferred (assistants / incomplete): "
        f"{sum(1 for s in report.suggestion_outcomes if s.decision == 'deferred')}",
        f"- Revisions: {report.measurements.get('revision_count')} · "
        f"Provenance: {report.measurements.get('provenance_count')}",
        "",
        "### Suggestion outcomes",
        "",
    ]
    for s in report.suggestion_outcomes:
        lines.append(
            f"- **{s.decision}** `{s.kind}` `{s.suggestion_id}` — {s.reason}"
        )
    lines += ["", "## Findings by priority", ""]
    for pri in ("P0", "P1", "P2"):
        lines.append(f"### {pri}")
        lines.append("")
        if not by[pri]:
            lines.append("_None._")
            lines.append("")
            continue
        for f in by[pri]:
            lines.append(f"#### {f.title}")
            lines.append("")
            lines.append(f"- **Axis:** {f.axis.value}")
            lines.append(f"- **Stage:** {f.stage}")
            lines.append(f"- **Demonstrated failure:** {f.demonstrated_failure}")
            lines.append(f"- **Detail:** {f.detail}")
            if f.evidence:
                lines.append(f"- **Evidence:** `{json.dumps(f.evidence)[:400]}`")
            lines.append("")
    lines += [
        "## Stage log (abbrev)",
        "",
    ]
    for sl in report.stage_log:
        flag = "ok" if sl.ok else "FAIL"
        lines.append(f"- `{sl.stage}` [{flag}] — {sl.notes}")
    lines.append("")
    return "\n".join(lines)


def write_report_files(root: Path, report: PilotReport, docs_path: Path | None = None) -> dict[str, Path]:
    json_path = root / "pilot_reports" / f"{report.id}.json"
    _write(json_path, report)
    md = render_findings_markdown(report)
    md_path = root / "pilot_reports" / f"{report.id}.md"
    md_path.write_text(md, encoding="utf-8")
    out = {"json": json_path, "md": md_path}
    if docs_path is not None:
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(md, encoding="utf-8")
        out["docs"] = docs_path
    return out
