"""Smoke tests for schemas, X-sheet craft, and style packs."""

from mvm.agents.pipeline import run_planning_pipeline
from mvm.audio.demo_tone import write_demo_wav
from mvm.audio.analyze import analyze_audio
from mvm.cel.masters import list_style_packs, load_style_pack
from mvm.cel.xsheet import build_xsheet_for_shot
from pathlib import Path
import tempfile


def test_style_packs():
    packs = list_style_packs()
    assert "classic_cel" in packs
    assert "akira_chrome" in packs
    assert load_style_pack("akira_chrome").smear_bias > 0.5


def test_pipeline_with_demo_audio():
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "t.wav"
        write_demo_wav(wav, duration=8.0)
        beatmap = analyze_audio(wav)
        assert beatmap.bpm > 0
        assert beatmap.sections
        result = run_planning_pipeline(
            "rain city chorus chrome", beatmap, style_pack="akira_chrome", fps=24
        )
        assert result["verification"]["ok"]
        assert result["shots"]
        xs = build_xsheet_for_shot(result["shots"][0], beatmap, fps=24)
        keys = [c for c in xs.cells if c.exposure == "key" and c.layer == "character"]
        assert len(keys) >= 2
