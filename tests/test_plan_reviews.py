"""Plan approve/reject writes Reviews and advances lifecycle with visible blockers."""

from __future__ import annotations

from pathlib import Path
import tempfile

from mvm.agents.pipeline import run_planning_pipeline
from mvm.audio.analyze import analyze_audio
from mvm.audio.demo_tone import write_demo_wav
from mvm.project.domain_store import persist_plan_domain
from mvm.project.reviews import approve_plan, load_reviews, reject_plan
from mvm.project.workspace import ProjectWorkspace, _write_json
from mvm.schemas.models import ProjectMeta, ShotLifecycleState


def _prepared(td: Path) -> ProjectWorkspace:
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
        "reviews",
    ):
        (proj / sub).mkdir(parents=True)
    (proj / "audio" / "master.wav").write_bytes(wav.read_bytes())
    meta = ProjectMeta(
        slug="proj",
        title="T",
        prompt="rain chrome",
        audio_path="audio/master.wav",
        style_pack="classic_cel",
    )
    _write_json(proj / "project.json", meta)
    ws = ProjectWorkspace(proj)
    beatmap = analyze_audio(ws.audio_file())
    ws.save_beatmap(beatmap)
    result = run_planning_pipeline(meta.prompt, beatmap, style_pack="classic_cel", fps=24)
    ws.save_story(result["story"])
    ws.save_shots(result["shots"])
    ws.save_xsheets(result["xsheets"])
    persist_plan_domain(ws.root, meta=ws.meta(), shots=result["shots"], xsheets=result["xsheets"])
    return ws


def test_approve_plan_writes_reviews_and_advances_lifecycle():
    with tempfile.TemporaryDirectory() as td:
        ws = _prepared(Path(td))
        before = ws.load_shots()[0]
        assert before.lifecycle_state == ShotLifecycleState.INTENT
        out = approve_plan(ws.root, ws.load_shots(), comment="Looks solid")
        assert out["ok"]
        reviews = load_reviews(ws.root)
        assert reviews
        assert all(r.state.value == "approved" for r in reviews)
        shot = ws.load_shots()[0]
        assert shot.approval.value == "approved"
        # With panels+layouts from persist, should reach layout
        assert shot.lifecycle_state in (
            ShotLifecycleState.STORYBOARD,
            ShotLifecycleState.LAYOUT,
        )
        assert any(entry["steps"] for entry in out["transition_logs"])


def test_reject_plan_requires_comment_and_keeps_revision():
    with tempfile.TemporaryDirectory() as td:
        ws = _prepared(Path(td))
        approve_plan(ws.root, ws.load_shots())
        bad = reject_plan(ws.root, ws.load_shots(), comment="")
        assert bad["ok"] is False
        revs_before = list((ws.root / "revisions").glob("*.json"))
        out = reject_plan(
            ws.root,
            ws.load_shots(),
            comment="Storyboard staging is muddy",
        )
        assert out["ok"]
        assert list((ws.root / "revisions").glob("*.json"))
        assert len(list((ws.root / "revisions").glob("*.json"))) >= len(revs_before)
        rejected = [r for r in load_reviews(ws.root) if r.state.value == "rejected"]
        assert rejected
        assert rejected[-1].comment == "Storyboard staging is muddy"
