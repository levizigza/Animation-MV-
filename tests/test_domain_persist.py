"""Persist sequences/timing/revisions/provenance after plan and cel rebuild."""

from __future__ import annotations

from pathlib import Path
import tempfile

from mvm.agents.pipeline import run_planning_pipeline
from mvm.audio.analyze import analyze_audio
from mvm.audio.demo_tone import write_demo_wav
from mvm.cel.xsheet import build_xsheet_for_shot
from mvm.project.domain_store import (
    domain_to_dict,
    load_provenance,
    load_revisions,
    load_sequences,
    load_timing_plans,
    persist_plan_domain,
    persist_timing_rebuild,
)
from mvm.project.workspace import ProjectWorkspace, _write_json
from mvm.schemas.models import ApprovalState, ProjectMeta


def _mini_project(td: Path) -> ProjectWorkspace:
    wav = td / "t.wav"
    write_demo_wav(wav, duration=8.0)
    proj = td / "proj"
    for sub in (
        "audio",
        "shots",
        "xsheets",
        "sequences",
        "timing",
        "key_poses",
        "layouts",
        "panels",
        "revisions",
        "provenance",
    ):
        (proj / sub).mkdir(parents=True)
    (proj / "audio" / "master.wav").write_bytes(wav.read_bytes())
    meta = ProjectMeta(
        slug="proj",
        title="T",
        prompt="rain chrome chorus",
        audio_path="audio/master.wav",
        style_pack="akira_chrome",
    )
    _write_json(proj / "project.json", meta)
    return ProjectWorkspace(proj)


def test_persist_plan_writes_domain_tree_and_provenance():
    with tempfile.TemporaryDirectory() as td:
        ws = _mini_project(Path(td))
        beatmap = analyze_audio(ws.audio_file())
        ws.save_beatmap(beatmap)
        result = run_planning_pipeline(
            ws.meta().prompt, beatmap, style_pack="akira_chrome", fps=24
        )
        ws.save_story(result["story"])
        ws.save_shots(result["shots"])
        ws.save_xsheets(result["xsheets"])
        out = persist_plan_domain(
            ws.root, meta=ws.meta(), shots=result["shots"], xsheets=result["xsheets"]
        )
        assert (ws.root / "domain_project.json").exists()
        assert load_sequences(ws.root)
        assert load_timing_plans(ws.root)
        assert (ws.root / "key_poses").glob("*.json")
        revs = load_revisions(ws.root)
        provs = load_provenance(ws.root)
        assert len(revs) == 1
        assert len(provs) == 1
        assert provs[0].operation == "agents.plan"
        assert provs[0].revision_id == revs[0].id
        assert "inbetween_slots are planned" in revs[0].snapshot["note"]
        # shots gained domain ids
        shot = ws.load_shots()[0]
        assert shot.intent.purpose
        assert shot.timing_plan_id
        assert shot.sequence_id
        blob = domain_to_dict(ws.root)
        assert blob["revisions"][0]["id"] == out["revision"].id


def test_persist_timing_rebuild_attributes_child_revision():
    with tempfile.TemporaryDirectory() as td:
        ws = _mini_project(Path(td))
        beatmap = analyze_audio(ws.audio_file())
        ws.save_beatmap(beatmap)
        result = run_planning_pipeline("rain", beatmap, style_pack="classic_cel", fps=24)
        ws.save_shots(result["shots"])
        ws.save_xsheets(result["xsheets"])
        plan_out = persist_plan_domain(
            ws.root, meta=ws.meta(), shots=result["shots"], xsheets=result["xsheets"]
        )
        shot = ws.load_shots()[0]
        shot.cel.mode = "full" if shot.cel.mode != "full" else "limited"
        shot.approval = ApprovalState.PENDING_REVIEW
        xs = build_xsheet_for_shot(shot, beatmap, fps=24)
        rebuilt = persist_timing_rebuild(
            ws.root,
            shot=shot,
            xsheet=xs,
            changed_fields=["cel_mode"],
            parent_revision_id=plan_out["revision"].id,
        )
        assert rebuilt["provenance"].operation == "cel.xsheet_rebuild"
        assert rebuilt["revision"].parent_id == plan_out["revision"].id
        assert "interpolation_note" in rebuilt["revision"].snapshot
        assert len(load_revisions(ws.root)) == 2
        assert len(load_provenance(ws.root)) == 2
        assert rebuilt["shot"].timing_plan_id == rebuilt["timing_plan"].id
