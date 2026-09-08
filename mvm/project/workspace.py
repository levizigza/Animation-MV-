"""Project tree helpers — agents write, Studio edits, craft engine reads."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slugify import slugify

from mvm.schemas.models import Beatmap, ProjectMeta, Shot, Story, XSheet


ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "projects"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def create_project(
    title: str,
    prompt: str,
    audio_path: Path,
    style_pack: str = "classic_cel",
    fps: int = 24,
) -> "ProjectWorkspace":
    slug = slugify(title) or "untitled-mv"
    root = PROJECTS_DIR / slug
    if root.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        slug = f"{slug}-{stamp}"
        root = PROJECTS_DIR / slug

    for sub in (
        "audio",
        "shots",
        "xsheets",
        "model_sheets",
        "previews",
        "renders",
        "final",
        "sequences",
        "timing",
        "key_poses",
        "layouts",
        "panels",
        "revisions",
        "provenance",
        "reviews",
        "animatics",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)

    dest_audio = root / "audio" / f"master{Path(audio_path).suffix.lower()}"
    shutil.copy2(audio_path, dest_audio)

    meta = ProjectMeta(
        slug=slug,
        title=title,
        prompt=prompt,
        audio_path=str(dest_audio.relative_to(root)).replace("\\", "/"),
        fps=fps,
        style_pack=style_pack,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _write_json(root / "project.json", meta)
    return ProjectWorkspace(root)


class ProjectWorkspace:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(f"Project not found: {self.root}")

    @property
    def project_json(self) -> Path:
        return self.root / "project.json"

    def meta(self) -> ProjectMeta:
        return ProjectMeta.model_validate(_read_json(self.project_json))

    def save_meta(self, meta: ProjectMeta) -> None:
        _write_json(self.project_json, meta)

    def audio_file(self) -> Path:
        meta = self.meta()
        return self.root / meta.audio_path

    def save_beatmap(self, beatmap: Beatmap) -> Path:
        path = self.root / "beatmap.json"
        _write_json(path, beatmap)
        return path

    def load_beatmap(self) -> Beatmap:
        return Beatmap.model_validate(_read_json(self.root / "beatmap.json"))

    def save_story(self, story: Story) -> Path:
        path = self.root / "story.json"
        _write_json(path, story)
        return path

    def load_story(self) -> Story:
        return Story.model_validate(_read_json(self.root / "story.json"))

    def save_shot(self, shot: Shot) -> Path:
        path = self.root / "shots" / f"{shot.id}.json"
        _write_json(path, shot)
        return path

    def save_shots(self, shots: list[Shot]) -> None:
        shots_dir = self.root / "shots"
        if shots_dir.exists():
            for old in shots_dir.glob("*.json"):
                old.unlink()
        for shot in shots:
            self.save_shot(shot)

    def load_shots(self) -> list[Shot]:
        shots = [
            Shot.model_validate(_read_json(p))
            for p in sorted((self.root / "shots").glob("*.json"))
        ]
        return sorted(shots, key=lambda s: s.index)

    def save_xsheet(self, xsheet: XSheet) -> Path:
        path = self.root / "xsheets" / f"{xsheet.shot_id}.json"
        _write_json(path, xsheet)
        return path

    def save_xsheets(self, xsheets: list[XSheet]) -> None:
        xs_dir = self.root / "xsheets"
        if xs_dir.exists():
            for old in xs_dir.glob("*.json"):
                old.unlink()
        for xs in xsheets:
            self.save_xsheet(xs)

    def load_xsheets(self) -> list[XSheet]:
        return [
            XSheet.model_validate(_read_json(p))
            for p in sorted((self.root / "xsheets").glob("*.json"))
        ]

    def set_plan_approved(self, approved: bool = True) -> None:
        meta = self.meta()
        meta.plan_approved = approved
        self.save_meta(meta)

    def set_render_approved(self, approved: bool = True) -> None:
        meta = self.meta()
        meta.render_approved = approved
        self.save_meta(meta)

    def load_decisions(self) -> dict[str, Any]:
        from mvm.cel.decisions import load_decisions

        return load_decisions(self.root)

    def persist_plan_domain(self, shots: list[Shot], xsheets: list[XSheet]) -> dict[str, Any]:
        from mvm.project.domain_store import persist_plan_domain

        return persist_plan_domain(
            self.root, meta=self.meta(), shots=shots, xsheets=xsheets
        )

    def persist_timing_rebuild(
        self,
        shot: Shot,
        xsheet: XSheet,
        changed_fields: list[str],
        parent_revision_id: str | None = None,
    ) -> dict[str, Any]:
        from mvm.project.domain_store import persist_timing_rebuild

        return persist_timing_rebuild(
            self.root,
            shot=shot,
            xsheet=xsheet,
            changed_fields=changed_fields,
            parent_revision_id=parent_revision_id,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"meta": self.meta().model_dump(mode="json")}
        if (self.root / "beatmap.json").exists():
            out["beatmap"] = self.load_beatmap().model_dump(mode="json")
        if (self.root / "story.json").exists():
            out["story"] = self.load_story().model_dump(mode="json")
        out["shots"] = [s.model_dump(mode="json") for s in self.load_shots()]
        out["xsheets"] = [x.model_dump(mode="json") for x in self.load_xsheets()]
        if (self.root / "decisions.json").exists():
            out["decisions"] = self.load_decisions()
        from mvm.project.domain_store import domain_to_dict

        out.update(domain_to_dict(self.root))
        return out
