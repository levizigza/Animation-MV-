"""Ticket A: decisions ledger, cel-edit X-sheet rebuild, approval revoke."""

from pathlib import Path
import tempfile

from mvm.agents.pipeline import run_planning_pipeline
from mvm.audio.analyze import analyze_audio
from mvm.audio.demo_tone import write_demo_wav
from mvm.cel.decisions import load_decisions, record_plan
from mvm.cel.xsheet import build_xsheet_for_shot
from mvm.project.workspace import create_project
from mvm.schemas.models import ApprovalState


def test_plan_writes_decisions_ledger():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Point projects into temp by creating workspace under td directly
        wav = root / "t.wav"
        write_demo_wav(wav, duration=8.0)
        # Manual mini-project (avoid global projects/)
        proj = root / "proj"
        proj.mkdir()
        (proj / "audio").mkdir()
        (proj / "shots").mkdir()
        (proj / "xsheets").mkdir()
        audio = proj / "audio" / "master.wav"
        audio.write_bytes(wav.read_bytes())
        from mvm.schemas.models import ProjectMeta
        from mvm.project.workspace import ProjectWorkspace, _write_json

        meta = ProjectMeta(
            slug="proj",
            title="T",
            prompt="rain city chrome",
            audio_path="audio/master.wav",
            style_pack="akira_chrome",
        )
        _write_json(proj / "project.json", meta)
        ws = ProjectWorkspace(proj)
        beatmap = analyze_audio(ws.audio_file())
        ws.save_beatmap(beatmap)
        result = run_planning_pipeline(
            meta.prompt, beatmap, style_pack="akira_chrome", fps=24
        )
        ws.save_story(result["story"])
        ws.save_shots(result["shots"])
        ws.save_xsheets(result["xsheets"])
        record_plan(
            ws.root,
            prompt=meta.prompt,
            style_pack="akira_chrome",
            beatmap=beatmap,
            shots=result["shots"],
            xsheets=result["xsheets"],
            analysis=result["analysis"],
            verification=result["verification"],
        )
        data = load_decisions(ws.root)
        assert data["events"]
        assert data["events"][-1]["type"] == "plan"
        assert "section_labels" in data["events"][-1]["music"]
        assert data["events"][-1]["shots"][0]["interpolation_note"]


def test_cel_edit_rebuilds_xsheet_and_revokes_approval():
    """Mirror studio_api cel-edit policy without HTTP."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        wav = root / "t.wav"
        write_demo_wav(wav, duration=8.0)
        proj = root / "proj"
        for sub in ("audio", "shots", "xsheets"):
            (proj / sub).mkdir(parents=True)
        (proj / "audio" / "master.wav").write_bytes(wav.read_bytes())
        from mvm.schemas.models import ProjectMeta
        from mvm.project.workspace import ProjectWorkspace, _write_json
        from mvm.cel.decisions import record_cel_edit

        meta = ProjectMeta(
            slug="proj",
            title="T",
            prompt="rain",
            audio_path="audio/master.wav",
            style_pack="classic_cel",
            plan_approved=True,
        )
        _write_json(proj / "project.json", meta)
        ws = ProjectWorkspace(proj)
        beatmap = analyze_audio(ws.audio_file())
        ws.save_beatmap(beatmap)
        result = run_planning_pipeline("rain", beatmap, style_pack="classic_cel", fps=24)
        ws.save_story(result["story"])
        ws.save_shots(result["shots"])
        ws.save_xsheets(result["xsheets"])
        ws.set_plan_approved(True)

        shot = ws.load_shots()[0]
        old_xs = next(x for x in ws.load_xsheets() if x.shot_id == shot.id)
        shot.cel.mode = "full" if shot.cel.mode != "full" else "limited"
        shot.approval = ApprovalState.PENDING_REVIEW
        ws.save_shot(shot)
        new_xs = build_xsheet_for_shot(shot, beatmap, fps=24)
        new_xs.approval = ApprovalState.PENDING_REVIEW
        ws.save_xsheet(new_xs)
        ws.set_plan_approved(False)
        record_cel_edit(
            ws.root,
            shot=shot,
            xsheet=new_xs,
            changed_fields=["cel_mode"],
            approval_revoked=True,
        )

        assert ws.meta().plan_approved is False
        ledger = load_decisions(ws.root)
        assert ledger["events"][-1]["type"] == "cel_edit"
        assert ledger["events"][-1]["approval_revoked"] is True
        # Exposure policy change should alter timing chart mode at least
        assert new_xs.timing_chart.get("mode") == shot.cel.mode
        assert old_xs.shot_id == new_xs.shot_id
