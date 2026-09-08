"""Cinema craft media API: frame manifest, status, path safety."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from mvm.studio_api import app
from mvm.studio_media import frames_manifest, safe_frame_path
from mvm.schemas.models import (
    CelPolicy,
    ProjectMeta,
    Shot,
    ShotIntent,
    XSheet,
    XSheetCell,
)


def _seed_project(root: Path, slug: str = "cinema-demo") -> Path:
    proj = root / slug
    for sub in ("shots", "xsheets", "previews", "audio"):
        (proj / sub).mkdir(parents=True)
    meta = ProjectMeta(
        slug=slug,
        title="Cinema Demo",
        prompt="Test craft cinema",
        audio_path="audio/master.wav",
        plan_approved=True,
        style_pack="classic_cel",
    )
    (proj / "project.json").write_text(
        json.dumps(meta.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    (proj / "audio" / "master.wav").write_bytes(b"RIFF....WAVEfmt ")
    shot = Shot(
        id="shot_001_intro",
        index=1,
        section="intro",
        start=0.0,
        end=2.0,
        duration=2.0,
        intent=ShotIntent(purpose="Verify cel frames on stage"),
        cel=CelPolicy(mode="full", exposure="2s", smear_density=0.2),
    )
    (proj / "shots" / f"{shot.id}.json").write_text(
        json.dumps(shot.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    xs = XSheet(
        shot_id=shot.id,
        fps=12,
        end_frame=4,
        cells=[
            XSheetCell(frame=1, layer="character", exposure="key"),
            XSheetCell(frame=2, layer="character", exposure="hold"),
            XSheetCell(frame=3, layer="character", exposure="smear"),
            XSheetCell(frame=4, layer="character", exposure="hold"),
        ],
        timing_chart={"key_frames": [1], "smear_frames": [3]},
    )
    (proj / "xsheets" / f"{shot.id}.json").write_text(
        json.dumps(xs.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    frames = proj / "previews" / shot.id / "frames"
    frames.mkdir(parents=True)
    for i in range(1, 5):
        # minimal PNG header-ish bytes — file existence is enough for routes
        (frames / f"frame_{i:04d}.png").write_bytes(
            b"\x89PNG\r\n\x1a\n" + bytes([i]) * 16
        )
    return proj


def test_frames_manifest_marks_keys_and_smears(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proj = _seed_project(root)
        from mvm.project import workspace as ws_mod

        monkeypatch.setattr(ws_mod, "PROJECTS_DIR", root)
        monkeypatch.setattr("mvm.studio_api.PROJECTS_DIR", root)

        xs = XSheet.model_validate_json(
            (proj / "xsheets" / "shot_001_intro.json").read_text(encoding="utf-8")
        )
        man = frames_manifest(proj, "shot_001_intro", "cinema-demo", xs)
        assert man["frame_count"] == 4
        assert man["frames"][0]["is_key"] is True
        assert man["frames"][2]["is_smear"] is True
        assert man["frames"][0]["url"].endswith("/frames/frame_0001.png")


def test_safe_frame_path_rejects_traversal():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proj = _seed_project(root)
        assert safe_frame_path(proj, "shot_001_intro", "../evil.png") is None
        assert safe_frame_path(proj, "shot_001_intro", "frame_0001.png") is not None


def test_api_craft_status_and_frames(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _seed_project(root)
        monkeypatch.setattr("mvm.studio_api.PROJECTS_DIR", root)
        monkeypatch.setattr("mvm.project.workspace.PROJECTS_DIR", root)

        client = TestClient(app)
        st = client.get("/api/projects/cinema-demo/shots/shot_001_intro/craft-status")
        assert st.status_code == 200
        body = st.json()
        assert body["has_frames"] is True
        assert body["frame_count"] == 4
        assert body["has_mp4"] is False

        man = client.get("/api/projects/cinema-demo/shots/shot_001_intro/frames")
        assert man.status_code == 200
        assert man.json()["frame_count"] == 4

        fr = client.get(
            "/api/projects/cinema-demo/shots/shot_001_intro/frames/frame_0002.png"
        )
        assert fr.status_code == 200

        bad = client.get(
            "/api/projects/cinema-demo/shots/shot_001_intro/frames/not_a_frame.txt"
        )
        assert bad.status_code == 404

        trav = client.get(
            "/api/projects/cinema-demo/shots/shot_001_intro/frames/frame_9999.png"
        )
        assert trav.status_code == 404

        prev = client.get("/api/projects/cinema-demo/shots/shot_001_intro/preview")
        assert prev.status_code == 404
