"""mvm CLI — init / analyze / plan / approve / craft / assemble."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mvm import __version__
from mvm.agents.pipeline import run_planning_pipeline
from mvm.audio.analyze import analyze_audio
from mvm.blender.runner import find_blender, render_shot
from mvm.cel.masters import list_style_packs
from mvm.editorial.assemble import (
    concat_shots,
    mux_shot_with_audio,
    write_remotion_props,
)
from mvm.project.workspace import PROJECTS_DIR, ProjectWorkspace, create_project
from mvm.project.workspace import ROOT as REPO_ROOT
from mvm.schemas.models import ApprovalState

app = typer.Typer(
    name="mvm",
    help="Cel Music Video Studio — Blender-primary craft pipeline",
    add_completion=False,
)
console = Console()


@app.callback()
def main() -> None:
    """Cel Music Video Studio."""


@app.command()
def version() -> None:
    console.print(f"mvm {__version__}")


@app.command("styles")
def styles_cmd() -> None:
    for s in list_style_packs():
        console.print(f" • {s}")


@app.command()
def init(
    audio: Path = typer.Argument(..., exists=True, readable=True),
    title: str = typer.Option(..., "--title", "-t", help="Project title"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Creative prompt"),
    style: str = typer.Option("classic_cel", "--style", "-s"),
    fps: int = typer.Option(24, "--fps"),
) -> None:
    """Create a project from audio + prompt."""
    ws = create_project(title=title, prompt=prompt, audio_path=audio, style_pack=style, fps=fps)
    console.print(f"[green]Created[/green] {ws.root}")
    console.print(f"Next: mvm analyze {ws.meta().slug}")


@app.command()
def analyze(slug: str = typer.Argument(...)) -> None:
    """Run MIR Audio Lab → beatmap.json."""
    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    console.print(f"Analyzing {ws.audio_file()} …")
    beatmap = analyze_audio(ws.audio_file())
    path = ws.save_beatmap(beatmap)
    table = Table(title="Beatmap")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("BPM", f"{beatmap.bpm:.2f}")
    table.add_row("Duration", f"{beatmap.duration:.2f}s")
    table.add_row("Beats", str(len(beatmap.beat_times)))
    table.add_row("Sections", ", ".join(f"{s.name}" for s in beatmap.sections))
    console.print(table)
    console.print(f"Wrote {path}")


@app.command()
def plan(
    slug: str = typer.Argument(...),
    style: Optional[str] = typer.Option(None, "--style", "-s"),
) -> None:
    """Run creative agents → story, shots, X-sheets (pending review)."""
    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    meta = ws.meta()
    if not (ws.root / "beatmap.json").exists():
        console.print("[yellow]No beatmap - running analyze first[/yellow]")
        beatmap = analyze_audio(ws.audio_file())
        ws.save_beatmap(beatmap)
    else:
        beatmap = ws.load_beatmap()

    pack = style or meta.style_pack
    result = run_planning_pipeline(meta.prompt, beatmap, style_pack=pack, fps=meta.fps)
    ws.save_story(result["story"])
    ws.save_shots(result["shots"])
    ws.save_xsheets(result["xsheets"])
    from mvm.cel.decisions import record_plan
    from mvm.neurosymbolic.bridge import ground_planning_mir, summarize_decisions

    ns_persisted = ground_planning_mir(
        ws.root,
        beatmap=beatmap,
        shots=result["shots"],
        style_pack=pack,
    )
    ns_summary = {
        **(result.get("neurosymbolic") or {}).get("summary", {}),
        **summarize_decisions(ns_persisted),
        "persisted": len(ns_persisted),
    }
    record_plan(
        ws.root,
        prompt=meta.prompt,
        style_pack=pack,
        beatmap=beatmap,
        shots=result["shots"],
        xsheets=result["xsheets"],
        analysis=result["analysis"],
        verification=result["verification"],
        neurosymbolic=ns_summary,
    )
    domain = ws.persist_plan_domain(result["shots"], result["xsheets"])
    meta.style_pack = pack
    meta.plan_approved = False
    ws.save_meta(meta)

    v = result["verification"]
    console.print(f"Story: [bold]{result['story'].title}[/bold]")
    console.print(f"Shots: {len(result['shots'])}  X-sheets: {len(result['xsheets'])}")
    console.print(f"Decisions ledger: {ws.root / 'decisions.json'}")
    console.print(
        f"Neuro-symbolic: accepted={ns_summary.get('accepted', 0)} "
        f"blocked={ns_summary.get('blocked', 0)} "
        f"needs_human={ns_summary.get('needs_human', 0)} "
        f"(suggestions only)"
    )
    console.print(
        f"Domain: {len(domain['sequences'])} sequences, "
        f"{len(domain['timing_plans'])} timing plans, "
        f"revision={domain['revision'].id}, provenance={domain['provenance'].id}"
    )
    if v["ok"]:
        console.print("[green]Verifier OK[/green] - review in Studio, then: mvm approve-plan " + slug)
    else:
        console.print("[red]Verifier issues:[/red]")
        for issue in v["issues"]:
            console.print(f"  - {issue}")


@app.command("approve-plan")
def approve_plan(
    slug: str = typer.Argument(...),
    comment: str = typer.Option("Plan approved for craft preview", "--comment", "-c"),
) -> None:
    """Human gate: lifecycle advance + Review records before craft render."""
    from mvm.project.reviews import approve_plan as do_approve

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    if not (ws.root / "story.json").exists():
        console.print("[red]No plan found. Run: mvm plan " + slug)
        raise typer.Exit(1)
    result = do_approve(ws.root, ws.load_shots(), comment=comment)
    for xs in ws.load_xsheets():
        xs.approval = ApprovalState.APPROVED
        ws.save_xsheet(xs)
    story = ws.load_story()
    story.approval = ApprovalState.APPROVED
    ws.save_story(story)
    ws.set_plan_approved(True)
    console.print(f"[green]Plan approved[/green] for {slug}")
    console.print(f"Reviews: {len(result['reviews'])}  revision={result['revision_id']}")
    for entry in result["transition_logs"]:
        for step in entry["steps"]:
            flag = "ok" if step["ok"] else "blocked"
            console.print(f"  {entry['shot_id']}: {step['from']} -> {step['to']} [{flag}] {step['reason']}")


@app.command("approve-shot")
def approve_shot_cmd(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    comment: str = typer.Option(..., "--comment", "-c", help="Why this shot communicates intent"),
    reviewer: str = typer.Option("human", "--reviewer"),
) -> None:
    """Human final gate: advance to approved with explicit authorship comment."""
    from mvm.project.reviews import approve_shot_final

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = approve_shot_final(
        ws.root, shot_id, comment=comment, reviewer=reviewer
    )
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        for step in result.get("transition_log") or []:
            console.print(f"  {step}")
        raise typer.Exit(1)
    console.print(f"[green]Shot final-approved[/green] {shot_id}")
    console.print(result.get("note", ""))
    console.print(f"revision={result['revision_id']} review={result['review']['id']}")


@app.command("reject-plan")
def reject_plan(
    slug: str = typer.Argument(...),
    comment: str = typer.Option(..., "--comment", "-c", help="Why the plan is rejected"),
    restore_revision: Optional[str] = typer.Option(None, "--restore-revision"),
) -> None:
    """Reject plan: write Review records; keep revisions recoverable."""
    from mvm.project.reviews import reject_plan as do_reject

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = do_reject(
        ws.root,
        ws.load_shots(),
        comment=comment,
        restore_revision_id=restore_revision,
    )
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    ws.set_plan_approved(False)
    console.print(f"[yellow]Plan rejected[/yellow] for {slug}: {comment}")
    if result.get("recovery"):
        console.print(f"Recovery: {result['recovery'].get('reason')}")


@app.command()
def craft(
    slug: str = typer.Argument(...),
    shot_id: Optional[str] = typer.Option(None, "--shot"),
    preview: bool = typer.Option(True, "--preview/--final"),
) -> None:
    """Craft Grease Pencil / hybrid frames via Blender (requires plan approval)."""
    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    meta = ws.meta()
    if not meta.plan_approved:
        console.print("[red]Plan not approved.[/red] Run Studio review or: mvm approve-plan " + slug)
        raise typer.Exit(1)

    shots = ws.load_shots()
    xsheets = {x.shot_id: x for x in ws.load_xsheets()}
    if shot_id:
        shots = [s for s in shots if s.id == shot_id]
        if not shots:
            console.print(f"[red]Shot not found:[/red] {shot_id}")
            raise typer.Exit(1)

    blender = find_blender()
    console.print(f"Blender: {blender or 'not found (fallback preview)'}")

    for shot in shots:
        xs = xsheets[shot.id]
        result = render_shot(
            ws.root, shot, xs, style_pack=meta.style_pack, preview=preview
        )
        from mvm.cel.decisions import record_craft

        record_craft(ws.root, shot=shot, xsheet=xs, craft_result=result)
        console.print(f"{shot.id}: {result.get('engine')} -> {result.get('output')}")
        if result.get("warning"):
            console.print(f"  [yellow]{result['warning']}[/yellow]")


@app.command()
def assemble(
    slug: str = typer.Argument(...),
    shot_id: Optional[str] = typer.Option(None, "--shot"),
) -> None:
    """Mux crafted plates with audio; write Remotion props."""
    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    meta = ws.meta()
    beatmap = ws.load_beatmap()
    shots = ws.load_shots()
    write_remotion_props(
        ws.root,
        [s.model_dump(mode="json") for s in shots],
        beatmap.model_dump(mode="json"),
    )

    targets = shots
    if shot_id:
        targets = [s for s in shots if s.id == shot_id]

    muxed: list[Path] = []
    for shot in targets:
        preview = ws.root / "previews" / shot.id / "shot_preview.mp4"
        frames = ws.root / "previews" / shot.id / "frames"
        src = preview if preview.exists() else frames
        if not src.exists():
            console.print(f"[yellow]Skip {shot.id} - craft first[/yellow]")
            continue
        out = ws.root / "final" / f"{shot.id}.mp4"
        result = mux_shot_with_audio(
            src, ws.audio_file(), out, start_sec=shot.start, duration_sec=shot.duration
        )
        if result["ok"]:
            console.print(f"Muxed {out}")
            muxed.append(out)
        else:
            console.print(f"[red]{shot.id}: {result.get('error') or result.get('stderr')}[/red]")

    if len(muxed) > 1:
        full = ws.root / "final" / "mv_preview.mp4"
        r = concat_shots(muxed, full)
        if r["ok"]:
            console.print(f"[green]Full preview:[/green] {full}")


@app.command("review-export")
def review_export(slug: str = typer.Argument(...)) -> None:
    """Export project JSON for Studio UI."""
    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    data = ws.to_dict()
    out = ws.root / "review_export.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"Wrote {out}")


@app.command("list")
def list_projects() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(PROJECTS_DIR.iterdir()):
        if (p / "project.json").exists():
            console.print(p.name)


storyboard_app = typer.Typer(help="Storyboard + first-class animatic workflow")
app.add_typer(storyboard_app, name="storyboard")


@storyboard_app.command("create-shot")
def sb_create_shot(
    slug: str = typer.Argument(...),
    purpose: str = typer.Option(..., "--purpose", "-p"),
    section: str = typer.Option("verse", "--section"),
) -> None:
    from mvm.storyboard import create_shot

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    shot = create_shot(ws.root, purpose=purpose, section=section)
    console.print(f"Created {shot.id} intent={shot.intent.purpose}")


@storyboard_app.command("add-panel")
def sb_add_panel(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    caption: str = typer.Option("", "--caption", "-c"),
    duration: int = typer.Option(24, "--duration", "-d"),
) -> None:
    from mvm.storyboard import add_storyboard_panel

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    panel = add_storyboard_panel(
        ws.root, shot_id, caption=caption, default_duration_frames=duration
    )
    console.print(f"Panel {panel.id} index={panel.index} default_frames={panel.default_duration_frames}")


@storyboard_app.command("animatic")
def sb_animatic(slug: str = typer.Argument(...), shot_id: str = typer.Argument(...)) -> None:
    from mvm.storyboard import build_or_get_animatic, preview_animatic

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    anim = build_or_get_animatic(ws.root, shot_id)
    timeline = preview_animatic(ws.root, anim.id)
    console.print(
        f"Animatic {anim.id} v{anim.version} panels={len(anim.panels)} "
        f"total_frames={anim.total_duration_frames}"
    )
    for beat in timeline:
        console.print(
            f"  [{beat.order}] {beat.panel_id} f{beat.start_frame}-{beat.end_frame} "
            f"({beat.duration_frames}f) {beat.caption}"
        )


@storyboard_app.command("reorder")
def sb_reorder(
    slug: str = typer.Argument(...),
    animatic_id: str = typer.Argument(...),
    panel_ids: str = typer.Option(..., "--panels", help="Comma-separated panel ids in order"),
) -> None:
    from mvm.storyboard import reorder_panels

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    anim = reorder_panels(ws.root, animatic_id, [p.strip() for p in panel_ids.split(",") if p.strip()])
    console.print(f"Reordered: {[p.panel_id for p in sorted(anim.panels, key=lambda x: x.order)]}")


@storyboard_app.command("set-duration")
def sb_set_duration(
    slug: str = typer.Argument(...),
    animatic_id: str = typer.Argument(...),
    panel_id: str = typer.Argument(...),
    frames: int = typer.Argument(...),
) -> None:
    from mvm.storyboard import load_panel, set_panel_duration

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    before = load_panel(ws.root, panel_id).default_duration_frames
    anim = set_panel_duration(ws.root, animatic_id, panel_id, frames)
    after_panel = load_panel(ws.root, panel_id).default_duration_frames
    console.print(
        f"Animatic duration for {panel_id} -> {frames}f "
        f"(panel artwork default unchanged: {before} -> {after_panel})"
    )
    console.print(f"Total animatic frames: {anim.total_duration_frames}")


@storyboard_app.command("version")
def sb_version(slug: str = typer.Argument(...), animatic_id: str = typer.Argument(...)) -> None:
    from mvm.storyboard import new_animatic_version

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    child = new_animatic_version(ws.root, animatic_id)
    console.print(f"Forked {child.id} v{child.version} parent={child.parent_animatic_id}")


@storyboard_app.command("compare")
def sb_compare(
    slug: str = typer.Argument(...),
    anim_a: str = typer.Argument(...),
    anim_b: str = typer.Argument(...),
) -> None:
    from mvm.storyboard import compare_animatics

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    diff = compare_animatics(ws.root, anim_a, anim_b)
    console.print(diff.summary)
    console.print(f"frames {diff.total_frames_a} vs {diff.total_frames_b}")
    if diff.order_changed:
        console.print(f"order A: {diff.order_a}")
        console.print(f"order B: {diff.order_b}")
    for ch in diff.duration_changes:
        console.print(
            f"  {ch['panel_id']}: {ch['duration_a']}f -> {ch['duration_b']}f "
            f"(delta {ch['delta_frames']})"
        )


@storyboard_app.command("approve-animatic")
def sb_approve_animatic(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    animatic_id: str = typer.Argument(...),
    comment: str = typer.Option("Animatic approved — unlock key poses", "--comment", "-c"),
) -> None:
    from mvm.storyboard import approve_animatic

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = approve_animatic(ws.root, shot_id, animatic_id, comment=comment)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        for step in result.get("transition_log") or []:
            console.print(f"  {step.get('from')} -> {step.get('to')}: {step.get('reason')}")
        raise typer.Exit(1)
    console.print(f"[green]Animatic approved[/green] {animatic_id}")
    console.print(
        "lifecycle=animatic animatic_approved=True shot.approval=pending_review "
        f"review={result['review']['id']}"
    )
    if result.get("note"):
        console.print(result["note"])
    for step in result.get("transition_log") or []:
        flag = "ok" if step["ok"] else "blocked"
        console.print(f"  [{flag}] {step['from']} -> {step['to']}: {step['reason']}")


@storyboard_app.command("reject-animatic")
def sb_reject_animatic(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    animatic_id: str = typer.Argument(...),
    comment: str = typer.Option(..., "--comment", "-c"),
) -> None:
    from mvm.storyboard import reject_animatic

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = reject_animatic(ws.root, shot_id, animatic_id, comment=comment)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    console.print(f"[yellow]Animatic rejected[/yellow]: {comment}")


timing_app = typer.Typer(help="Craft timing: holds, spacing, annotations, versions")
app.add_typer(timing_app, name="timing")


@timing_app.command("create")
def timing_create(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    end_frame: int = typer.Option(48, "--end-frame", "-e"),
    fps: int = typer.Option(24, "--fps"),
) -> None:
    from mvm.timing import create_timing_plan

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = create_timing_plan(ws.root, shot_id=shot_id, end_frame=end_frame, fps=fps)
    console.print(
        f"Timing {plan.id} v{plan.version} frames=1-{plan.end_frame} "
        f"allow_auto_smooth={plan.allow_auto_smooth}"
    )


@timing_app.command("hold")
def timing_hold(
    slug: str = typer.Argument(...),
    timing_id: str = typer.Argument(...),
    frame: int = typer.Argument(...),
    duration: int = typer.Option(1, "--duration", "-d"),
    kind: str = typer.Option("hold", "--kind", "-k"),
    key_pose_id: Optional[str] = typer.Option(None, "--key"),
    notes: str = typer.Option("", "--notes"),
) -> None:
    from mvm.timing import add_hold

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = add_hold(
        ws.root,
        timing_id,
        frame=frame,
        duration_frames=duration,
        kind=kind,
        key_pose_id=key_pose_id,
        notes=notes,
    )
    console.print(
        f"Added authored {kind} @f{frame} x{duration} "
        f"(exposures={len(plan.exposures)}, source=authored)"
    )


@timing_app.command("annotate")
def timing_annotate(
    slug: str = typer.Argument(...),
    timing_id: str = typer.Argument(...),
    frame: int = typer.Argument(...),
    text: str = typer.Argument(...),
    kind: str = typer.Option("note", "--kind", "-k"),
) -> None:
    from mvm.timing import add_annotation

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = add_annotation(ws.root, timing_id, frame=frame, text=text, kind=kind)
    console.print(f"Annotations={len(plan.annotations)} last kind={kind} @f{frame}")


@timing_app.command("timeline")
def timing_timeline(slug: str = typer.Argument(...), timing_id: str = typer.Argument(...)) -> None:
    from mvm.timing import inspect_timeline

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    tl = inspect_timeline(ws.root, timing_id)
    console.print(tl.summary)
    for e in tl.entries[:40]:
        console.print(
            f"  f{e.frame}: roles={e.roles} source={e.source.value} "
            f"t={e.spacing_t} mode={e.spacing_mode} key={e.key_pose_id}"
        )
    if len(tl.entries) > 40:
        console.print(f"  ... {len(tl.entries) - 40} more frames")


@timing_app.command("version")
def timing_version(slug: str = typer.Argument(...), timing_id: str = typer.Argument(...)) -> None:
    from mvm.timing import new_timing_version

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    child = new_timing_version(ws.root, timing_id)
    console.print(f"Forked {child.id} v{child.version} parent={child.parent_timing_id}")


@timing_app.command("compare")
def timing_compare(
    slug: str = typer.Argument(...),
    timing_a: str = typer.Argument(...),
    timing_b: str = typer.Argument(...),
) -> None:
    from mvm.timing import compare_timing_plans

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    diff = compare_timing_plans(ws.root, timing_a, timing_b)
    console.print(diff.summary)
    for ch in diff.exposure_changes[:20]:
        console.print(f"  exposure {ch}")
    for ch in diff.segment_changes[:20]:
        console.print(f"  segment {ch}")


@timing_app.command("export")
def timing_export(
    slug: str = typer.Argument(...),
    timing_id: str = typer.Argument(...),
) -> None:
    from mvm.timing import export_timing_bundle

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    path = export_timing_bundle(ws.root, timing_id)
    console.print(f"Exported {path}")


@timing_app.command("import-bundle")
def timing_import(
    slug: str = typer.Argument(...),
    bundle: Path = typer.Argument(...),
) -> None:
    from mvm.timing import import_timing_bundle

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = import_timing_bundle(ws.root, bundle)
    holds = [e for e in plan.exposures if e.kind in ("hold", "pause")]
    console.print(
        f"Imported {plan.id} exposures={len(plan.exposures)} "
        f"holds/pauses={len(holds)} allow_auto_smooth={plan.allow_auto_smooth}"
    )


keypose_app = typer.Typer(help="Key-pose-first workflow: mark, arc, suggest, accept")
app.add_typer(keypose_app, name="keypose")


@keypose_app.command("mark")
def kp_mark(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    frame: int = typer.Argument(...),
    label: str = typer.Option("", "--label", "-l"),
) -> None:
    from mvm.keyposes import mark_key_pose

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    pose = mark_key_pose(ws.root, shot_id=shot_id, frame=frame, label=label)
    console.print(
        f"Key pose {pose.id} @f{pose.frame} marked_as_key={pose.marked_as_key} "
        f"approval={pose.approval.value}"
    )


@keypose_app.command("action")
def kp_action(
    slug: str = typer.Argument(...),
    pose_id: str = typer.Argument(...),
    action: str = typer.Option("", "--action", "-a"),
    intention: str = typer.Option("", "--intention", "-i"),
) -> None:
    from mvm.keyposes import set_pose_action

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    pose = set_pose_action(ws.root, pose_id, action=action, intention=intention)
    console.print(f"{pose.id} action={pose.action!r} intention={pose.intention!r}")


@keypose_app.command("arc")
def kp_arc(
    slug: str = typer.Argument(...),
    pose_id: str = typer.Argument(...),
    anticipation: Optional[int] = typer.Option(None, "--anticipation"),
    follow_through: Optional[int] = typer.Option(None, "--follow-through"),
) -> None:
    from mvm.keyposes import set_anticipation_follow_through

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    pose = set_anticipation_follow_through(
        ws.root,
        pose_id,
        anticipation_frames=anticipation,
        follow_through_frames=follow_through,
    )
    console.print(
        f"{pose.id} anticipation={pose.arc.anticipation_frames} "
        f"follow_through={pose.arc.follow_through_frames}"
    )


@keypose_app.command("approve")
def kp_approve(slug: str = typer.Argument(...), pose_id: str = typer.Argument(...)) -> None:
    from mvm.keyposes import approve_key_pose

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    pose = approve_key_pose(ws.root, pose_id)
    console.print(f"[green]Approved[/green] {pose.id}")


@keypose_app.command("suggest")
def kp_suggest(
    slug: str = typer.Argument(...),
    from_pose: str = typer.Argument(...),
    to_pose: str = typer.Argument(...),
    spacing: Optional[str] = typer.Option(None, "--spacing", "-s"),
) -> None:
    from mvm.keyposes import suggest_inbetweens

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = suggest_inbetweens(
        ws.root,
        from_key_pose_id=from_pose,
        to_key_pose_id=to_pose,
        spacing_mode=spacing,
    )
    sug = result["suggestion"]
    if not result["ok"]:
        console.print(f"[yellow]Blocked[/yellow]: {result['reason']}")
        for m in result.get("missing_information") or []:
            console.print(f"  missing: {m}")
        console.print(f"suggestion={sug.id} (no timing mutation)")
        raise typer.Exit(1)
    console.print(f"[green]Preview[/green] {sug.id} slots={len(sug.slots)} applied=False")
    console.print(sug.rationale)


@keypose_app.command("preview")
def kp_preview(slug: str = typer.Argument(...), suggestion_id: str = typer.Argument(...)) -> None:
    from mvm.keyposes import preview_suggestion

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    prev = preview_suggestion(ws.root, suggestion_id)
    console.print(
        f"{prev['suggestion_id']} status={prev['status']} "
        f"applied={prev['applied_to_timing']} slots={len(prev['slots'])}"
    )
    for slot in prev["slots"][:30]:
        console.print(
            f"  f{slot['frame']} {slot['kind']} source={slot['source']} "
            f"t={slot.get('spacing_t')}"
        )


@keypose_app.command("accept")
def kp_accept(slug: str = typer.Argument(...), suggestion_id: str = typer.Argument(...)) -> None:
    from mvm.keyposes import accept_suggestion

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = accept_suggestion(ws.root, suggestion_id)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Accepted[/green] frames={result['accepted_frames']}")


@keypose_app.command("partial-accept")
def kp_partial(
    slug: str = typer.Argument(...),
    suggestion_id: str = typer.Argument(...),
    frames: str = typer.Option(..., "--frames", help="Comma-separated frames to accept"),
) -> None:
    from mvm.keyposes import partial_accept_suggestion

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    accept_frames = [int(x.strip()) for x in frames.split(",") if x.strip()]
    result = partial_accept_suggestion(ws.root, suggestion_id, accept_frames=accept_frames)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    console.print(
        f"[green]Partial[/green] accepted={result['accepted_frames']} "
        f"rejected={result['rejected_frames']}"
    )


@keypose_app.command("reject-suggestion")
def kp_reject_sug(
    slug: str = typer.Argument(...),
    suggestion_id: str = typer.Argument(...),
    comment: str = typer.Option(..., "--comment", "-c"),
) -> None:
    from mvm.keyposes import reject_suggestion

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = reject_suggestion(ws.root, suggestion_id, comment=comment)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    console.print(f"[yellow]Rejected suggestion[/yellow]: {comment}")


notation_app = typer.Typer(help="Creator-intent notation → structured motion requests")
app.add_typer(notation_app, name="notation")


@notation_app.command("create")
def notation_create(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    marks: str = typer.Option(
        ...,
        "--marks",
        "-m",
        help="Semicolon-separated kind=value pairs, e.g. motion_path=arc;force_direction=up",
    ),
    freehand_ref: Optional[str] = typer.Option(None, "--freehand"),
) -> None:
    from mvm.notation import NotationMark, NotationKind, create_notation

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    parsed = []
    for part in marks.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            console.print(f"[red]Bad mark (need kind=value): {part}[/red]")
            raise typer.Exit(1)
        kind_s, value = part.split("=", 1)
        parsed.append(NotationMark(kind=NotationKind(kind_s.strip()), value=value.strip()))
    notation = create_notation(
        ws.root, shot_id=shot_id, marks=parsed, freehand_ref=freehand_ref
    )
    console.print(
        f"Notation {notation.id} marks={len(notation.marks)} "
        f"converts_to_final={notation.converts_to_final_animation}"
    )


@notation_app.command("analyze")
def notation_analyze(slug: str = typer.Argument(...), notation_id: str = typer.Argument(...)) -> None:
    from mvm.notation import analyze_notation

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = analyze_notation(ws.root, notation_id)
    console.print(result["message"])
    report = result["ambiguity"]
    for a in report.ambiguities:
        console.print(f"  ambiguity: {a}")
    for interp in report.interpretations:
        console.print(f"  [{interp.id}] {interp.label}: {interp.summary}")
        for assumption in interp.assumptions:
            console.print(f"      assumes: {assumption}")
    if result.get("needs_choice"):
        console.print("[yellow]Choose an interpretation with: mvm notation choose ...[/yellow]")


@notation_app.command("translate")
def notation_translate(
    slug: str = typer.Argument(...),
    notation_id: str = typer.Argument(...),
    interpretation_id: Optional[str] = typer.Option(None, "--interpretation", "-i"),
) -> None:
    from mvm.notation import translate_notation

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = translate_notation(
        ws.root, notation_id, interpretation_id=interpretation_id
    )
    if result.get("needs_choice") or result.get("ask_user_to_choose"):
        console.print(f"[yellow]{result.get('message') or result.get('reason')}[/yellow]")
        for a in result.get("ambiguities") or []:
            console.print(f"  ambiguity: {a}")
        for interp in result.get("interpretations") or []:
            console.print(
                f"  [{interp['id']}] {interp['label']}: {interp['summary']}"
            )
        console.print("Ask user to choose — nothing applied as final animation.")
        raise typer.Exit(1)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    req = result["motion_request"]
    console.print(
        f"[green]MotionRequest[/green] {req.id} status={req.status} "
        f"applied_as_final={req.applied_as_final}"
    )
    console.print(result.get("message", ""))


@notation_app.command("choose")
def notation_choose(
    slug: str = typer.Argument(...),
    notation_id: str = typer.Argument(...),
    interpretation_id: str = typer.Argument(...),
) -> None:
    from mvm.notation import choose_interpretation

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = choose_interpretation(ws.root, notation_id, interpretation_id)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    req = result["motion_request"]
    console.print(
        f"[green]Chose[/green] {result['interpretation'].label} → {req.id} "
        f"(provenance={result['provenance_id']}, applied_as_final=False)"
    )


notebook_app = typer.Typer(help="Project/character reference notebooks")
app.add_typer(notebook_app, name="notebook")


@notebook_app.command("create")
def nb_create(
    slug: str = typer.Argument(...),
    scope: str = typer.Option("project", "--scope"),
    title: str = typer.Option("", "--title", "-t"),
    character_id: Optional[str] = typer.Option(None, "--character"),
    character_name: str = typer.Option("", "--name"),
) -> None:
    from mvm.notebook import create_notebook

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    nb = create_notebook(
        ws.root,
        scope=scope,
        project_slug=slug,
        title=title,
        character_id=character_id,
        character_name=character_name,
    )
    console.print(
        f"Notebook {nb.id} scope={nb.scope} v{nb.version} "
        f"opaque_style_imitation={nb.opaque_style_imitation}"
    )


@notebook_app.command("attach")
def nb_attach(
    slug: str = typer.Argument(...),
    notebook_id: str = typer.Argument(...),
    path: str = typer.Option(..., "--path", "-p"),
    media_type: str = typer.Option("image", "--type"),
    source_title: str = typer.Option(..., "--source-title"),
    creator: str = typer.Option("", "--creator"),
    caption: str = typer.Option("", "--caption"),
) -> None:
    from mvm.notebook import SourceAttribution, attach_media

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    nb = attach_media(
        ws.root,
        notebook_id,
        path_or_uri=path,
        media_type=media_type,
        caption=caption,
        attribution=SourceAttribution(
            source_title=source_title, creator_or_rights=creator, url_or_path=path
        ),
    )
    last = nb.media[-1]
    console.print(
        f"Attached {last.id} type={last.media_type} "
        f"attr={last.attribution.source_title!r}"
    )


@notebook_app.command("notes")
def nb_notes(
    slug: str = typer.Argument(...),
    notebook_id: str = typer.Argument(...),
    preserve: Optional[str] = typer.Option(None, "--preserve"),
    exaggerate: Optional[str] = typer.Option(None, "--exaggerate"),
    omit: Optional[str] = typer.Option(None, "--omit"),
    acting: Optional[str] = typer.Option(None, "--acting"),
    movement: Optional[str] = typer.Option(None, "--movement"),
    behavior: Optional[str] = typer.Option(None, "--behavior"),
    transform: Optional[str] = typer.Option(None, "--transform"),
    observe: Optional[str] = typer.Option(None, "--observe"),
) -> None:
    from mvm.notebook import update_craft_notes

    def split(v: Optional[str]) -> list[str] | None:
        if v is None:
            return None
        return [x.strip() for x in v.split("|") if x.strip()]

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    nb = update_craft_notes(
        ws.root,
        notebook_id,
        observational_notes=split(observe),
        preserve=split(preserve),
        exaggerate=split(exaggerate),
        omit=split(omit),
        acting_observations=split(acting),
        movement_vocabulary=split(movement),
        recurring_behaviors=split(behavior),
        transformation_notes=split(transform),
    )
    console.print(
        f"Updated {nb.id}: preserve={len(nb.preserve)} exaggerate={len(nb.exaggerate)} "
        f"omit={len(nb.omit)} influence={nb.assistance.influence_mode}"
    )


@notebook_app.command("revise")
def nb_revise(slug: str = typer.Argument(...), notebook_id: str = typer.Argument(...)) -> None:
    from mvm.notebook import revise_notebook

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    child = revise_notebook(ws.root, notebook_id)
    console.print(
        f"Forked {child.id} v{child.version} parent={child.parent_notebook_id} "
        f"media={len(child.media)}"
    )


@notebook_app.command("assist")
def nb_assist(slug: str = typer.Argument(...), notebook_id: str = typer.Argument(...)) -> None:
    from mvm.notebook import assistance_context

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    ctx = assistance_context(ws.root, notebook_id)
    console.print(
        f"influence_mode={ctx['influence_mode']} "
        f"opaque_style_imitation={ctx['opaque_style_imitation']}"
    )
    assist = ctx["assistance"]
    for key in (
        "preserve",
        "exaggerate",
        "omit",
        "movement_vocabulary",
        "recurring_behaviors",
        "attribution_summaries",
    ):
        vals = assist.get(key) or []
        if vals:
            console.print(f"  {key}: {vals}")


critique_app = typer.Typer(help="Structured multi-category craft reviews")
app.add_typer(critique_app, name="critique")


@critique_app.command("create")
def critique_create(
    slug: str = typer.Argument(...),
    target_id: str = typer.Argument(...),
    revision_id: str = typer.Argument(...),
    reviewer: str = typer.Option(..., "--reviewer", "-r"),
    target_type: str = typer.Option("shot", "--type"),
    previous_revision: Optional[str] = typer.Option(None, "--previous-rev"),
    notes: str = typer.Option("", "--notes"),
) -> None:
    from mvm.critique import create_craft_review

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    rev = create_craft_review(
        ws.root,
        target_type=target_type,
        target_id=target_id,
        revision_id=revision_id,
        reviewer=reviewer,
        previous_revision_id=previous_revision,
        summary_notes=notes,
    )
    console.print(
        f"CraftReview {rev.id} reviewer={rev.reviewer} status={rev.revision_status} "
        f"aggregate_score={rev.has_aggregate_quality_score}"
    )


@critique_app.command("add")
def critique_add(
    slug: str = typer.Argument(...),
    review_id: str = typer.Argument(...),
    category: str = typer.Option(..., "--category", "-c"),
    notes: str = typer.Option(..., "--notes", "-n"),
    severity: str = typer.Option("note", "--severity", "-s"),
    frame: Optional[int] = typer.Option(None, "--frame"),
    end_frame: Optional[int] = typer.Option(None, "--end-frame"),
    time_sec: Optional[float] = typer.Option(None, "--time"),
    end_time: Optional[float] = typer.Option(None, "--end-time"),
) -> None:
    from mvm.critique import add_critique

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    rev = add_critique(
        ws.root,
        review_id,
        category=category,
        notes=notes,
        severity=severity,
        frame=frame,
        end_frame=end_frame,
        time_sec=time_sec,
        end_time_sec=end_time,
    )
    item = rev.items[-1]
    console.print(
        f"Added {item.id} category={item.category.value} severity={item.severity.value} "
        f"resolved={item.resolved}"
    )


@critique_app.command("resolve")
def critique_resolve(
    slug: str = typer.Argument(...),
    review_id: str = typer.Argument(...),
    item_id: str = typer.Argument(...),
    notes: str = typer.Option("", "--notes"),
) -> None:
    from mvm.critique import resolve_critique

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    rev = resolve_critique(ws.root, review_id, item_id, resolution_notes=notes)
    console.print(f"Review status={rev.revision_status}")


@critique_app.command("compare")
def critique_compare(
    slug: str = typer.Argument(...),
    current_id: str = typer.Argument(...),
    previous_id: Optional[str] = typer.Argument(None),
) -> None:
    from mvm.critique import compare_craft_reviews

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    diff = compare_craft_reviews(ws.root, current_id, previous_id)
    console.print(diff.summary)
    console.print(f"improved: {diff.categories_improved}")
    console.print(f"regressed: {diff.categories_regressed}")
    for cat, n in diff.unresolved_by_category_current.items():
        if n or diff.unresolved_by_category_previous.get(cat):
            console.print(
                f"  {cat}: prev={diff.unresolved_by_category_previous.get(cat, 0)} "
                f"cur={n} delta={diff.unresolved_delta_by_category.get(cat, 0)}"
            )


@critique_app.command("show")
def critique_show(slug: str = typer.Argument(...), review_id: str = typer.Argument(...)) -> None:
    from mvm.critique import category_breakdown

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    breakdown = category_breakdown(ws.root, review_id)
    console.print(
        f"{breakdown['review_id']} reviewer={breakdown['reviewer']} "
        f"status={breakdown['revision_status']} "
        f"aggregate={breakdown['has_aggregate_quality_score']}"
    )
    for cat, items in breakdown["by_category"].items():
        if not items:
            continue
        console.print(f"  [{cat}] ({len(items)})")
        for it in items:
            flag = "done" if it["resolved"] else "open"
            console.print(f"    ({flag}/{it['severity']}) {it['notes'][:80]}")


sequence_app = typer.Typer(help="Sequence-aware analysis (identify issues, never auto-fix)")
app.add_typer(sequence_app, name="sequence")


@sequence_app.command("evaluate")
def sequence_evaluate(
    slug: str = typer.Argument(...),
    shot_id: Optional[str] = typer.Option(None, "--shot"),
    save: bool = typer.Option(True, "--save/--no-save"),
) -> None:
    from mvm.sequence_analysis import evaluate_sequence, evaluate_shot_in_sequence, save_evaluation

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    shots = ws.load_shots()
    if not shots:
        console.print("[red]No shots[/red]")
        raise typer.Exit(1)
    seq_id = shots[0].sequence_id or "sequence"
    if shot_id:
        reports = [evaluate_shot_in_sequence(shots, shot_id, sequence_id=seq_id)]
    else:
        reports = evaluate_sequence(shots, sequence_id=seq_id)
    for ev in reports:
        console.print(ev.summary)
        for issue in ev.issues:
            console.print(f"  [{issue.kind}] {issue.explanation}")
            console.print(f"      attention: {issue.suggested_attention}")
        if save:
            path = save_evaluation(ws.root, ev)
            console.print(f"  saved {path.name} (auto_fix=False)")


sound_app = typer.Typer(help="Sound-aware planning (cues visible; motion never forced)")
app.add_typer(sound_app, name="sound")


@sound_app.command("create")
def sound_create(
    slug: str = typer.Argument(...),
    shot_id: str = typer.Argument(...),
    fps: int = typer.Option(24, "--fps"),
    start: float = typer.Option(0.0, "--start"),
) -> None:
    from mvm.sound import create_sound_plan

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = create_sound_plan(ws.root, shot_id=shot_id, fps=fps, shot_start_sec=start)
    console.print(
        f"SoundPlan {plan.id} force_motion={plan.force_every_cue_to_motion}"
    )


@sound_app.command("cue")
def sound_cue(
    slug: str = typer.Argument(...),
    plan_id: str = typer.Argument(...),
    kind: str = typer.Option(..., "--kind", "-k"),
    time_sec: float = typer.Option(..., "--time", "-t"),
    end: Optional[float] = typer.Option(None, "--end"),
    label: str = typer.Option("", "--label"),
    text: str = typer.Option("", "--text"),
) -> None:
    from mvm.sound import add_sound_cue

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = add_sound_cue(
        ws.root,
        plan_id,
        kind=kind,
        time_sec=time_sec,
        end_time_sec=end,
        label=label,
        text=text,
    )
    cue = plan.cues[-1]
    console.print(
        f"Cue {cue.id} {cue.kind.value} @{cue.time_sec}s "
        f"(no motion forced; unassigned until link)"
    )


@sound_app.command("link")
def sound_link(
    slug: str = typer.Argument(...),
    plan_id: str = typer.Argument(...),
    cue_id: str = typer.Argument(...),
    response: str = typer.Option(..., "--response", "-r"),
    notes: str = typer.Option("", "--notes"),
) -> None:
    from mvm.sound import link_sound_to_motion

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    plan = link_sound_to_motion(
        ws.root, plan_id, cue_id, response=response, notes=notes
    )
    rel = plan.relationships[-1]
    console.print(
        f"Link {rel.id} → {rel.response.value} auto={rel.applies_automatically}"
    )


@sound_app.command("import-beats")
def sound_import_beats(
    slug: str = typer.Argument(...),
    plan_id: str = typer.Argument(...),
    shot_start: float = typer.Option(..., "--start"),
    shot_end: float = typer.Option(..., "--end"),
) -> None:
    from mvm.sound import import_beats_as_cues

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    beatmap = ws.load_beatmap()
    plan = import_beats_as_cues(
        ws.root, plan_id, beatmap, shot_start=shot_start, shot_end=shot_end
    )
    console.print(
        f"Beats on plan: {sum(1 for c in plan.cues if c.kind.value == 'music_beat')} "
        f"(relationships still optional)"
    )


@sound_app.command("timeline")
def sound_timeline(
    slug: str = typer.Argument(...),
    timing_id: str = typer.Argument(...),
    sound_id: Optional[str] = typer.Option(None, "--sound"),
) -> None:
    from mvm.sound import inspect_sound_timing

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    tl = inspect_sound_timing(ws.root, timing_plan_id=timing_id, sound_plan_id=sound_id)
    console.print(tl.summary)
    for e in tl.entries:
        if e.sound_cue_ids:
            console.print(
                f"  f{e.frame}: sound={e.sound_labels} "
                f"kinds={e.sound_cue_kinds} response={e.motion_responses} "
                f"roles={e.roles}"
            )


provenance_app = typer.Typer(help="Provenance tracking, guardrails, restore")
app.add_typer(provenance_app, name="provenance")


@provenance_app.command("inspect")
def prov_inspect(slug: str = typer.Argument(...), provenance_id: str = typer.Argument(...)) -> None:
    from mvm.provenance import inspect_provenance

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    info = inspect_provenance(ws.root, provenance_id)
    for k, v in info.items():
        console.print(f"{k}: {v}")


@provenance_app.command("accept")
def prov_accept(
    slug: str = typer.Argument(...),
    provenance_id: str = typer.Argument(...),
    notes: str = typer.Option("", "--notes"),
) -> None:
    from mvm.provenance import set_acceptance

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    prov = set_acceptance(ws.root, provenance_id, state="accepted", notes=notes)
    console.print(f"acceptance={prov.acceptance_state.value}")


@provenance_app.command("reject")
def prov_reject(
    slug: str = typer.Argument(...),
    provenance_id: str = typer.Argument(...),
    notes: str = typer.Option(..., "--notes", "-n"),
) -> None:
    from mvm.provenance import set_acceptance

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    prov = set_acceptance(ws.root, provenance_id, state="rejected", notes=notes)
    console.print(f"acceptance={prov.acceptance_state.value}")


@provenance_app.command("approve")
def prov_final_approve(
    slug: str = typer.Argument(...),
    provenance_id: str = typer.Argument(...),
    by: str = typer.Option(..., "--by"),
) -> None:
    from mvm.provenance import final_approve_provenance

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    prov = final_approve_provenance(ws.root, provenance_id, approved_by=by)
    console.print(f"final_approval={prov.final_approval} by={prov.final_approval_by}")


@provenance_app.command("export")
def prov_export(slug: str = typer.Argument(...)) -> None:
    from mvm.provenance import export_provenance_bundle

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    path = export_provenance_bundle(ws.root)
    console.print(f"Exported {path}")


@provenance_app.command("import-bundle")
def prov_import(slug: str = typer.Argument(...), bundle: Path = typer.Argument(...)) -> None:
    from mvm.provenance import import_provenance_bundle

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = import_provenance_bundle(ws.root, bundle)
    console.print(result)


@provenance_app.command("restore")
def prov_restore(
    slug: str = typer.Argument(...),
    revision_id: str = typer.Argument(...),
    by: str = typer.Option("human", "--by"),
) -> None:
    from mvm.provenance import restore_revision

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    result = restore_revision(ws.root, revision_id, restored_by=by)
    if not result.get("ok"):
        console.print(f"[red]{result.get('reason')}[/red]")
        raise typer.Exit(1)
    console.print(
        f"Restored {revision_id} → provenance={result['provenance'].id} "
        f"(inspectable at {result['restore_path'].name})"
    )


assistant_app = typer.Typer(help="Narrow scoped assistants (suggestions only)")
app.add_typer(assistant_app, name="assistant")


@assistant_app.command("run")
def assistant_run(
    slug: str = typer.Argument(...),
    name: str = typer.Argument(
        ...,
        help="storyboard|timing|pose|continuity|sound|critique|provenance",
    ),
    shot_id: str = typer.Option("shot_001", "--shot"),
) -> None:
    from mvm.assistants import (
        continuity_assistant,
        critique_assistant,
        pose_assistant,
        provenance_assistant,
        sound_assistant,
        storyboard_assistant,
        timing_assistant,
    )

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    runners = {
        "storyboard": lambda: storyboard_assistant(ws.root, shot_id=shot_id),
        "timing": lambda: timing_assistant(
            ws.root, shot_id=shot_id, timing_plan_id="timing_unknown"
        ),
        "pose": lambda: pose_assistant(ws.root, shot_id=shot_id),
        "continuity": lambda: continuity_assistant(
            ws.root, sequence_id="seq", focus_shot_id=shot_id
        ),
        "sound": lambda: sound_assistant(ws.root, shot_id=shot_id),
        "critique": lambda: critique_assistant(
            ws.root, shot_id=shot_id, revision_id="rev_unknown"
        ),
        "provenance": lambda: provenance_assistant(ws.root),
    }
    if name not in runners:
        console.print(f"[red]Unknown assistant {name}[/red]")
        raise typer.Exit(1)
    result = runners[name]()
    console.print(f"{result.assistant_id.value} assumptions={result.input_assumptions}")
    console.print(f"provenance={result.provenance_id} silently_edited={result.silently_edited}")
    for s in result.suggestions:
        console.print(
            f"  [{s.confidence:.2f}] {s.action}: {s.reason} "
            f"(uncertainty={s.uncertainty!r})"
        )


eval_app = typer.Typer(
    help="Craft evaluation harness (multi-dimension; never a single score)"
)
app.add_typer(eval_app, name="eval")


@eval_app.command("scenes")
def eval_scenes() -> None:
    from mvm.eval_harness import list_scenes

    for s in list_scenes():
        console.print(f"{s.id} [{s.kind.value}] — {s.title}")
        console.print(f"  {s.summary}")


@eval_app.command("seed")
def eval_seed(slug: str = typer.Argument(...)) -> None:
    from mvm.eval_harness import seed_harness_scenes

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    scenes = seed_harness_scenes(ws.root)
    console.print(f"Seeded {len(scenes)} eval scenes under eval_scenes/")


@eval_app.command("run")
def eval_run(
    slug: str = typer.Argument(...),
    scene: str = typer.Option(
        ...,
        "--scene",
        help="eval_scene_dialogue|eval_scene_physical|eval_scene_quiet|kind",
    ),
    revision_id: str = typer.Option("rev_eval", "--revision"),
    previous_revision_id: str | None = typer.Option(None, "--previous"),
    no_auto: bool = typer.Option(False, "--no-auto"),
) -> None:
    from mvm.eval_harness import start_eval_session

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    session = start_eval_session(
        ws.root,
        scene_id=scene,
        revision_id=revision_id,
        previous_revision_id=previous_revision_id,
        run_auto=not no_auto,
    )
    console.print(
        f"session={session.id} scene={session.scene_id} "
        f"human_review_required={session.human_review_required} "
        f"aggregate_score={session.quality_score}"
    )
    if session.auto_pass:
        for o in session.auto_pass.observations:
            console.print(
                f"  [{o.dimension.value}/{o.kind.value} {o.confidence:.2f}] {o.message}"
            )
    if session.human_form:
        console.print(
            f"Blank human form: {session.human_form.id} "
            f"(fill all {len(session.human_form.responses)} dimensions, then submit)"
        )


@eval_app.command("run-all")
def eval_run_all(slug: str = typer.Argument(...)) -> None:
    from mvm.eval_harness import run_all_scenes_auto

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    sessions = run_all_scenes_auto(ws.root)
    console.print(f"Started {len(sessions)} sessions (auto + blank human forms)")
    for s in sessions:
        console.print(f"  {s.scene_kind.value}: session={s.id} form={s.human_form.id if s.human_form else None}")


@eval_app.command("form")
def eval_form(
    slug: str = typer.Argument(...),
    session_id: str = typer.Argument(...),
) -> None:
    from mvm.eval_harness import load_session

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    session = load_session(ws.root, session_id)
    form = session.human_form
    if not form:
        console.print("[red]No human form on session[/red]")
        raise typer.Exit(1)
    console.print(f"form={form.id} completed={form.completed} reviewer={form.reviewer!r}")
    for r in form.responses:
        console.print(f"  {r.dimension.value}: {r.notes[:80]}…")


@eval_app.command("submit")
def eval_submit(
    slug: str = typer.Argument(...),
    session_id: str = typer.Argument(...),
    reviewer: str = typer.Option(..., "--reviewer"),
    responses_json: Path = typer.Option(
        ...,
        "--responses",
        help="JSON array of {dimension, notes, preference, emphasis, would_block_approval}",
    ),
    overall_notes: str = typer.Option("", "--notes"),
) -> None:
    import json

    from mvm.eval_harness import submit_human_form

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    responses = json.loads(responses_json.read_text(encoding="utf-8"))
    session = submit_human_form(
        ws.root,
        session_id=session_id,
        reviewer=reviewer,
        responses=responses,
        overall_notes=overall_notes,
    )
    summary = session.dimension_summary()
    console.print(
        f"Submitted form for {session.scene_id}; "
        f"human_complete={summary['human_form_completed']} "
        f"aggregate={summary['quality_score']}"
    )


@eval_app.command("show")
def eval_show(
    slug: str = typer.Argument(...),
    session_id: str = typer.Argument(...),
) -> None:
    from mvm.eval_harness import load_session

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    session = load_session(ws.root, session_id)
    summary = session.dimension_summary()
    console.print(
        f"{session.id} [{session.scene_kind.value}] "
        f"revision={session.revision_id} score={summary['quality_score']}"
    )
    for dim, block in summary.items():
        if dim in ("has_aggregate_quality_score", "quality_score", "human_form_completed"):
            continue
        auto_n = len(block["automatic_observations"])
        human = "yes" if block["human_complete"] else "no"
        console.print(f"  {dim}: auto={auto_n} human={human}")


refs_app = typer.Typer(
    help="External craft references (public-apis) — suggestions, never silent finals"
)
app.add_typer(refs_app, name="refs")


@refs_app.command("catalog")
def refs_catalog() -> None:
    from mvm.integrations import list_catalog

    for e in list_catalog():
        console.print(f"[bold]{e.name}[/bold] ({e.provider.value}) — {e.public_apis_category}")
        console.print(f"  auth={e.auth}  docs={e.docs_url}")
        console.print(f"  craft: {e.craft_role}")
        if e.reliability_note:
            console.print(f"  note: {e.reliability_note}")


@refs_app.command("dictionary")
def refs_dictionary(
    slug: str = typer.Argument(...),
    word: str = typer.Argument(...),
    shot_id: str | None = typer.Option(None, "--shot"),
) -> None:
    from mvm.integrations import IntegrationError, fetch_and_store_dictionary

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    try:
        ref = fetch_and_store_dictionary(ws.root, word, shot_id=shot_id)
    except IntegrationError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"ref={ref.id} phonetics stored (applied_as_final=False)")
    console.print(f"craft_use: {ref.craft_use}")


@refs_app.command("art")
def refs_art(
    slug: str = typer.Argument(...),
    query: str = typer.Argument(...),
    source: str = typer.Option("artic", "--source", help="artic|met"),
    limit: int = typer.Option(5, "--limit"),
    shot_id: str | None = typer.Option(None, "--shot"),
) -> None:
    from mvm.integrations import (
        IntegrationError,
        fetch_and_store_artic,
        fetch_and_store_met,
    )

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    try:
        if source == "met":
            ref = fetch_and_store_met(ws.root, query, limit=limit, shot_id=shot_id)
        else:
            ref = fetch_and_store_artic(ws.root, query, limit=limit, shot_id=shot_id)
    except IntegrationError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    hits = len((ref.payload.get("hits") or []))
    console.print(f"ref={ref.id} hits={hits} (accept before notebook attach)")


@refs_app.command("music")
def refs_music(
    slug: str = typer.Argument(...),
    query: str = typer.Argument(...),
    shot_id: str | None = typer.Option(None, "--shot"),
) -> None:
    from mvm.integrations import IntegrationError, fetch_and_store_musicbrainz

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    try:
        ref = fetch_and_store_musicbrainz(ws.root, query, shot_id=shot_id)
    except IntegrationError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"ref={ref.id} recordings={len(ref.payload.get('recordings') or [])}")


@refs_app.command("palette")
def refs_palette(
    slug: str = typer.Argument(...),
    shot_id: str | None = typer.Option(None, "--shot"),
) -> None:
    from mvm.integrations import IntegrationError, fetch_and_store_palette

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    try:
        ref = fetch_and_store_palette(ws.root, shot_id=shot_id)
    except IntegrationError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"ref={ref.id} {ref.summary}")


@refs_app.command("lyrics")
def refs_lyrics(
    slug: str = typer.Argument(...),
    artist: str = typer.Argument(...),
    title: str = typer.Argument(...),
    shot_id: str | None = typer.Option(None, "--shot"),
) -> None:
    from mvm.integrations import IntegrationError, fetch_and_store_lyrics

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    try:
        ref = fetch_and_store_lyrics(ws.root, artist, title, shot_id=shot_id)
    except IntegrationError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    console.print(f"ref={ref.id} lyrics stored — do not force lip motion")


@refs_app.command("accept")
def refs_accept(
    slug: str = typer.Argument(...),
    ref_id: str = typer.Argument(...),
    reviewer: str = typer.Option(..., "--reviewer"),
    note: str = typer.Option("", "--note"),
) -> None:
    from mvm.integrations import accept_external_reference

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    ref = accept_external_reference(
        ws.root, ref_id, reviewer=reviewer, note=note
    )
    console.print(f"Accepted {ref.id} (still applied_as_final=False)")


@refs_app.command("list")
def refs_list(slug: str = typer.Argument(...)) -> None:
    from mvm.integrations import list_external_references

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    for ref in list_external_references(ws.root):
        console.print(
            f"{ref.id} [{ref.provider.value}/{ref.kind.value}] "
            f"accepted={ref.human_accepted} final={ref.applied_as_final} — {ref.title}"
        )


pilot_app = typer.Typer(help="Short-sequence craft pilot + findings report")
app.add_typer(pilot_app, name="pilot")


@pilot_app.command("run")
def pilot_run(
    slug: str = typer.Argument(
        "pilot-short-sequence",
        help="Project slug under projects/ (created if missing)",
    ),
    write_docs: bool = typer.Option(
        True, "--docs/--no-docs", help="Also write docs/PILOT_FINDINGS.md"
    ),
) -> None:
    from mvm.pilot import run_short_sequence_pilot, write_report_files

    root = PROJECTS_DIR / slug
    root.mkdir(parents=True, exist_ok=True)
    report = run_short_sequence_pilot(root)
    docs = REPO_ROOT / "docs" / "PILOT_FINDINGS.md" if write_docs else None
    paths = write_report_files(root, report, docs_path=docs)
    by = report.findings_by_priority()
    console.print(report.summary)
    console.print(
        f"P0={len(by['P0'])} P1={len(by['P1'])} P2={len(by['P2'])} "
        f"intent_ok={report.intent_still_communicated} "
        f"revisions_ok={report.revision_history_understandable}"
    )
    console.print(f"Report JSON: {paths['json']}")
    console.print(f"Report MD:   {paths['md']}")
    if "docs" in paths:
        console.print(f"Docs copy:   {paths['docs']}")


neurosym_app = typer.Typer(
    help="Neuro-symbolic craft: soft proposals grounded by hard symbolic rules"
)
app.add_typer(neurosym_app, name="neurosym")


@neurosym_app.command("inspect")
def neurosym_inspect(
    slug: str = typer.Argument(...),
    shot: str = typer.Option(..., "--shot", "-s", help="Shot id"),
) -> None:
    """Show SymbolicCraftState predicates for a shot."""
    from mvm.neurosymbolic.symbolic import load_symbolic_state_for_shot

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    if not (ws.root / "shots" / f"{shot}.json").exists():
        console.print(f"[red]Shot not found:[/red] {shot}")
        raise typer.Exit(1)
    state = load_symbolic_state_for_shot(ws.root, shot)
    console.print(f"Shot {state.shot_id} · lifecycle={state.lifecycle_state}")
    console.print(
        f"intent_explicit={state.intent_explicit}  "
        f"animatic_approved={state.animatic_approved}  "
        f"cel_mode={state.cel_mode}  style_pack={state.style_pack or '—'}"
    )
    console.print(
        f"keys={state.key_pose_count} frames={state.key_frames} "
        f"smears={state.smear_frames}"
    )
    for p in state.predicates:
        mark = "[green]holds[/green]" if p.holds else "[red]fails[/red]"
        console.print(f"  {mark} {p.name}: {p.explanation}")


@neurosym_app.command("ground")
def neurosym_ground(
    slug: str = typer.Argument(...),
    shot: str = typer.Option(..., "--shot", "-s", help="Shot id"),
    assistants: bool = typer.Option(
        False, "--assistants/--no-assistants", help="Also ground latest assistant suggestions"
    ),
) -> None:
    """Run MIR (and optional assistant) proposals through the symbolic grounder."""
    import json

    from mvm.neurosymbolic.bridge import (
        decide,
        proposals_from_assistant_result,
        proposals_from_music_analysis,
        summarize_decisions,
    )
    from mvm.neurosymbolic.symbolic import load_symbolic_state_for_shot
    from mvm.assistants.base import AssistantResult

    ws = ProjectWorkspace(PROJECTS_DIR / slug)
    if not (ws.root / "shots" / f"{shot}.json").exists():
        console.print(f"[red]Shot not found:[/red] {shot}")
        raise typer.Exit(1)

    shots = ws.load_shots()
    shot_obj = next((s for s in shots if s.id == shot), None)
    if shot_obj is None:
        console.print(f"[red]Shot missing from index:[/red] {shot}")
        raise typer.Exit(1)

    beatmap = ws.load_beatmap() if (ws.root / "beatmap.json").exists() else None
    meta = ws.meta()
    proposals = []
    if beatmap is not None:
        proposals.extend(
            proposals_from_music_analysis(
                beatmap=beatmap,
                shots=[shot_obj],
                style_pack=meta.style_pack,
            )
        )

    if assistants:
        sug_dir = ws.root / "assistant_suggestions"
        if sug_dir.exists():
            for path in sorted(sug_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
                raw = json.loads(path.read_text(encoding="utf-8"))
                try:
                    result = AssistantResult.model_validate(
                        {k: v for k, v in raw.items() if k != "neurosymbolic"}
                    )
                except Exception:
                    continue
                if any(
                    str(s.payload.get("shot_id")) == shot for s in result.suggestions
                ) or not any(s.payload.get("shot_id") for s in result.suggestions):
                    proposals.extend(proposals_from_assistant_result(result))

    state = load_symbolic_state_for_shot(ws.root, shot)
    decisions = decide(ws.root, shot, proposals, state=state, persist=True)
    summary = summarize_decisions(decisions)
    console.print(
        f"Grounded {summary['total']} proposals · "
        f"accepted={summary['accepted']} blocked={summary['blocked']} "
        f"needs_human={summary['needs_human']} · applied=false"
    )
    for d in decisions:
        g = d.grounding
        console.print(
            f"  [{g.status.value}] neuro={d.proposal.source.value} "
            f"{d.proposal.action} / {d.proposal.domain}"
        )
        for ex in g.explanations[:2]:
            console.print(f"      {ex}")
        if g.violated_rules:
            console.print(f"      rules: {', '.join(g.violated_rules)}")


if __name__ == "__main__":
    app()