"""Reference notebook workflow — attach media, attribute, revise, assist metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.domain import new_id
from mvm.schemas.notebook import (
    NotebookMedia,
    ReferenceNotebook,
    SourceAttribution,
    build_assistance_metadata,
)


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_notebook_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "notebooks").mkdir(parents=True, exist_ok=True)


def save_notebook(root: Path, notebook: ReferenceNotebook) -> Path:
    ensure_notebook_dirs(root)
    if notebook.opaque_style_imitation is not False:
        raise ValueError("Refusing notebook with opaque_style_imitation enabled")
    notebook = notebook.model_copy(deep=True)
    notebook.assistance = build_assistance_metadata(notebook)
    path = root / "notebooks" / f"{notebook.id}.json"
    _write(path, notebook)
    # Latest pointer per scope key
    if notebook.scope == "project":
        ptr = root / "notebooks" / f"project_{notebook.project_slug}_latest.json"
    else:
        ptr = root / "notebooks" / f"character_{notebook.character_id}_latest.json"
    _write(
        ptr,
        {
            "notebook_id": notebook.id,
            "version": notebook.version,
            "scope": notebook.scope,
        },
    )
    return path


def load_notebook(root: Path, notebook_id: str) -> ReferenceNotebook:
    return ReferenceNotebook.model_validate(
        _read(root / "notebooks" / f"{notebook_id}.json")
    )


def list_notebooks(
    root: Path,
    *,
    scope: str | None = None,
    character_id: str | None = None,
    project_slug: str | None = None,
) -> list[ReferenceNotebook]:
    d = root / "notebooks"
    if not d.exists():
        return []
    out: list[ReferenceNotebook] = []
    for p in d.glob("*.json"):
        if p.name.endswith("_latest.json") or p.name.endswith("_assist.json"):
            continue
        data = _read(p)
        if "media" not in data or "scope" not in data:
            continue
        nb = ReferenceNotebook.model_validate(data)
        if scope and nb.scope != scope:
            continue
        if character_id and nb.character_id != character_id:
            continue
        if project_slug and nb.project_slug != project_slug:
            continue
        out.append(nb)
    return sorted(out, key=lambda n: (n.scope, n.version, n.id))


def create_notebook(
    root: Path,
    *,
    scope: str,
    project_slug: str,
    title: str = "",
    character_id: str | None = None,
    character_name: str = "",
) -> ReferenceNotebook:
    ensure_notebook_dirs(root)
    if scope not in ("project", "character"):
        raise ValueError("scope must be 'project' or 'character'")
    nb = ReferenceNotebook(
        id=new_id("nb"),
        scope=scope,  # type: ignore[arg-type]
        project_slug=project_slug,
        character_id=character_id,
        character_name=character_name,
        title=title
        or (
            f"{character_name or character_id} notebook"
            if scope == "character"
            else f"{project_slug} project notebook"
        ),
        opaque_style_imitation=False,
    )
    nb.assistance = build_assistance_metadata(nb)
    rev, prov = attribute_suggestion(
        operation="human.notebook_create",
        target_type="notebook",
        target_id=nb.id,
        snapshot=nb.model_dump(mode="json"),
        summary=f"Created {scope} reference notebook {nb.id}",
        outputs={
            "opaque_style_imitation": False,
            "influence_mode": "explicit_metadata",
        },
    )
    nb.revision_id = rev.id
    save_notebook(root, nb)
    save_revision(root, rev)
    save_provenance(root, prov)
    return nb


def attach_media(
    root: Path,
    notebook_id: str,
    *,
    path_or_uri: str,
    media_type: str = "image",
    caption: str = "",
    attribution: SourceAttribution | dict[str, Any],
    observation_cue: str = "",
) -> ReferenceNotebook:
    """Attach reference image/video. Attribution is mandatory."""
    nb = load_notebook(root, notebook_id)
    attr = (
        attribution
        if isinstance(attribution, SourceAttribution)
        else SourceAttribution.model_validate(attribution)
    )
    if not attr.source_title.strip():
        raise ValueError("Cannot attach media without source attribution (source_title)")
    media = NotebookMedia(
        path_or_uri=path_or_uri,
        media_type=media_type,  # type: ignore[arg-type]
        caption=caption,
        attribution=attr,
        observation_cue=observation_cue,
    )
    nb = nb.model_copy(deep=True)
    nb.media = list(nb.media) + [media]
    nb.assistance = build_assistance_metadata(nb)

    rev, prov = attribute_suggestion(
        operation="human.notebook_attach_media",
        target_type="notebook",
        target_id=nb.id,
        snapshot={
            "notebook_id": nb.id,
            "media": media.model_dump(mode="json"),
            "attribution": attr.model_dump(mode="json"),
        },
        summary=(
            f"Attached {media.media_type} {path_or_uri} "
            f"attributed to '{attr.source_title}'"
        ),
        inputs={"path_or_uri": path_or_uri},
        outputs={
            "media_id": media.id,
            "source_title": attr.source_title,
            "opaque_style_imitation": False,
        },
    )
    nb.revision_id = rev.id
    save_notebook(root, nb)
    save_revision(root, rev)
    save_provenance(root, prov)
    return nb


def update_craft_notes(
    root: Path,
    notebook_id: str,
    *,
    observational_notes: Iterable[str] | None = None,
    preserve: Iterable[str] | None = None,
    exaggerate: Iterable[str] | None = None,
    omit: Iterable[str] | None = None,
    acting_observations: Iterable[str] | None = None,
    movement_vocabulary: Iterable[str] | None = None,
    recurring_behaviors: Iterable[str] | None = None,
    transformation_notes: Iterable[str] | None = None,
) -> ReferenceNotebook:
    """Update explicit craft fields that drive assistance metadata."""
    nb = load_notebook(root, notebook_id).model_copy(deep=True)

    def _extend(field: str, values: Iterable[str] | None) -> None:
        if values is None:
            return
        current = list(getattr(nb, field))
        for v in values:
            v = v.strip()
            if v and v not in current:
                current.append(v)
        setattr(nb, field, current)

    _extend("observational_notes", observational_notes)
    _extend("preserve", preserve)
    _extend("exaggerate", exaggerate)
    _extend("omit", omit)
    _extend("acting_observations", acting_observations)
    _extend("movement_vocabulary", movement_vocabulary)
    _extend("recurring_behaviors", recurring_behaviors)
    _extend("transformation_notes", transformation_notes)
    nb.assistance = build_assistance_metadata(nb)

    rev, prov = attribute_suggestion(
        operation="human.notebook_update_notes",
        target_type="notebook",
        target_id=nb.id,
        snapshot=nb.model_dump(mode="json"),
        summary=f"Updated craft notes on notebook {nb.id}",
        outputs={"influence_mode": "explicit_metadata"},
    )
    nb.revision_id = rev.id
    save_notebook(root, nb)
    save_revision(root, rev)
    save_provenance(root, prov)
    return nb


def revise_notebook(
    root: Path,
    notebook_id: str,
    *,
    summary: str = "Notebook revision",
) -> ReferenceNotebook:
    """Fork a new notebook version; media + attribution persist intact."""
    parent = load_notebook(root, notebook_id)
    versions = [
        n
        for n in list_notebooks(
            root,
            scope=parent.scope,
            character_id=parent.character_id,
            project_slug=parent.project_slug if parent.scope == "project" else None,
        )
        if (
            (parent.scope == "project" and n.project_slug == parent.project_slug)
            or (parent.scope == "character" and n.character_id == parent.character_id)
        )
    ]
    next_v = max((n.version for n in versions), default=parent.version) + 1
    child = parent.model_copy(deep=True)
    child.id = new_id("nb")
    child.version = next_v
    child.parent_notebook_id = parent.id
    child.assistance = build_assistance_metadata(child)

    rev, prov = attribute_suggestion(
        operation="human.notebook_revise",
        target_type="notebook",
        target_id=child.id,
        snapshot={
            "parent_id": parent.id,
            "child": child.model_dump(mode="json"),
            "media_ids_persisted": [m.id for m in child.media],
            "attributions_persisted": [
                m.attribution.model_dump(mode="json") for m in child.media
            ],
        },
        summary=summary or f"Notebook v{next_v} from {parent.id}",
        outputs={
            "version": next_v,
            "parent_notebook_id": parent.id,
            "media_count": len(child.media),
        },
    )
    child.revision_id = rev.id
    save_notebook(root, child)
    save_revision(root, rev)
    save_provenance(root, prov)
    return child


def assistance_context(root: Path, notebook_id: str) -> dict[str, Any]:
    """Return explicit metadata for assistants — never an opaque style blob."""
    nb = load_notebook(root, notebook_id)
    meta = build_assistance_metadata(nb)
    payload = {
        "notebook_id": nb.id,
        "scope": nb.scope,
        "character_id": nb.character_id,
        "project_slug": nb.project_slug,
        "version": nb.version,
        "observational_notes": list(nb.observational_notes),
        "assistance": meta.model_dump(mode="json"),
        "opaque_style_imitation": False,
        "influence_mode": "explicit_metadata",
    }
    _write(root / "notebooks" / f"{nb.id}_assist.json", payload)
    return payload
