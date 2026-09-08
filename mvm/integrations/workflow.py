"""Persist external craft references — human accept only; never silent finals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import httpx

from mvm.integrations import clients
from mvm.integrations.catalog import get_catalog_entry, list_catalog
from mvm.notebook.workflow import load_notebook, save_notebook
from mvm.project.domain_store import ensure_domain_dirs
from mvm.provenance import record_meaningful_change
from mvm.schemas.domain import ActorKind
from mvm.schemas.integrations import (
    ExternalReference,
    ReferenceKind,
    ReferenceProvider,
)
from mvm.schemas.notebook import NotebookMedia, SourceAttribution


Fetcher = Callable[..., dict[str, Any]]


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_integration_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "external_refs").mkdir(parents=True, exist_ok=True)


def save_external_reference(root: Path, ref: ExternalReference) -> Path:
    ensure_integration_dirs(root)
    if ref.applied_as_final is not False:
        raise ValueError("Refusing external reference marked applied_as_final")
    path = root / "external_refs" / f"{ref.id}.json"
    _write(path, ref)
    return path


def load_external_reference(root: Path, ref_id: str) -> ExternalReference:
    return ExternalReference.model_validate(
        _read(root / "external_refs" / f"{ref_id}.json")
    )


def list_external_references(
    root: Path,
    *,
    provider: str | None = None,
    shot_id: str | None = None,
) -> list[ExternalReference]:
    d = root / "external_refs"
    if not d.exists():
        return []
    out: list[ExternalReference] = []
    for p in d.glob("*.json"):
        ref = ExternalReference.model_validate(_read(p))
        if provider and ref.provider.value != provider:
            continue
        if shot_id and ref.shot_id != shot_id:
            continue
        out.append(ref)
    return sorted(out, key=lambda r: r.at)


def _store_fetch(
    root: Path,
    fetched: dict[str, Any],
    *,
    shot_id: str | None = None,
) -> ExternalReference:
    attr = fetched["attribution"]
    if isinstance(attr, dict):
        attr = SourceAttribution.model_validate(attr)
    ref = ExternalReference(
        provider=ReferenceProvider(fetched["provider"]),
        kind=ReferenceKind(fetched["kind"]),
        query=fetched.get("query") or "",
        title=fetched.get("title") or "",
        summary=fetched.get("summary") or "",
        payload=fetched.get("payload") or {},
        attribution=attr,
        craft_use=fetched["craft_use"],
        source_url=fetched.get("source_url") or "",
        applied_as_final=False,
        human_accepted=False,
        visibly_labeled_external=True,
        shot_id=shot_id,
    )
    save_external_reference(root, ref)
    entry = get_catalog_entry(ref.provider)
    record_meaningful_change(
        root,
        operation=f"integrations.fetch.{ref.provider.value}",
        target_type="shot" if shot_id else "project",
        target_id=shot_id or "project",
        snapshot=ref.model_dump(mode="json"),
        summary=f"Fetched external craft reference: {ref.title}",
        creator="integrations",
        actor=ActorKind.SYSTEM,
        source_references=[ref.source_url or entry.docs_url, f"provider:{ref.provider.value}"],
        input_parameters={"query": ref.query, "provider": ref.provider.value},
        outputs={
            "ref_id": ref.id,
            "applied_as_final": False,
            "human_accepted": False,
            "kind": ref.kind.value,
        },
        generated=True,
    )
    return ref


def fetch_and_store_dictionary(
    root: Path, word: str, *, shot_id: str | None = None, client: httpx.Client | None = None
) -> ExternalReference:
    return _store_fetch(root, clients.fetch_dictionary(word, client=client), shot_id=shot_id)


def fetch_and_store_artic(
    root: Path,
    query: str,
    *,
    limit: int = 5,
    shot_id: str | None = None,
    client: httpx.Client | None = None,
) -> ExternalReference:
    return _store_fetch(
        root,
        clients.fetch_artic_artworks(query, limit=limit, client=client),
        shot_id=shot_id,
    )


def fetch_and_store_met(
    root: Path,
    query: str,
    *,
    limit: int = 5,
    shot_id: str | None = None,
    client: httpx.Client | None = None,
) -> ExternalReference:
    return _store_fetch(
        root,
        clients.fetch_met_objects(query, limit=limit, client=client),
        shot_id=shot_id,
    )


def fetch_and_store_musicbrainz(
    root: Path,
    query: str,
    *,
    limit: int = 5,
    shot_id: str | None = None,
    client: httpx.Client | None = None,
) -> ExternalReference:
    return _store_fetch(
        root,
        clients.fetch_musicbrainz_recordings(query, limit=limit, client=client),
        shot_id=shot_id,
    )


def fetch_and_store_palette(
    root: Path,
    *,
    model: str = "default",
    shot_id: str | None = None,
    client: httpx.Client | None = None,
) -> ExternalReference:
    return _store_fetch(
        root,
        clients.fetch_colormind_palette(model=model, client=client),
        shot_id=shot_id,
    )


def fetch_and_store_lyrics(
    root: Path,
    artist: str,
    title: str,
    *,
    shot_id: str | None = None,
    client: httpx.Client | None = None,
) -> ExternalReference:
    return _store_fetch(
        root,
        clients.fetch_lyrics_ovh(artist, title, client=client),
        shot_id=shot_id,
    )


def accept_external_reference(
    root: Path,
    ref_id: str,
    *,
    reviewer: str,
    note: str = "",
) -> ExternalReference:
    """Human accepts a reference for craft use — still not applied_as_final."""
    if not reviewer.strip():
        raise ValueError("reviewer required to accept an external reference")
    ref = load_external_reference(root, ref_id).model_copy(deep=True)
    ref.human_accepted = True
    ref.applied_as_final = False
    if note.strip():
        ref.summary = f"{ref.summary} | accepted: {note.strip()}"
    save_external_reference(root, ref)
    record_meaningful_change(
        root,
        operation="integrations.accept",
        target_type="shot" if ref.shot_id else "project",
        target_id=ref.shot_id or "project",
        snapshot=ref.model_dump(mode="json"),
        summary=f"Human accepted external ref {ref.id} ({ref.provider.value})",
        creator=reviewer.strip(),
        actor=ActorKind.HUMAN,
        source_references=[ref.source_url or ref.id],
        input_parameters={"ref_id": ref_id, "note": note},
        outputs={"human_accepted": True, "applied_as_final": False},
        generated=False,
    )
    return ref


def attach_visual_ref_to_notebook(
    root: Path,
    *,
    ref_id: str,
    notebook_id: str,
    hit_index: int = 0,
    reviewer: str,
) -> dict[str, Any]:
    """Attach one visual hit from an accepted ARTIC/Met ref into a notebook."""
    if not reviewer.strip():
        raise ValueError("reviewer required")
    ref = load_external_reference(root, ref_id)
    if ref.kind != ReferenceKind.VISUAL_REFERENCE:
        raise ValueError("Only visual_reference providers can attach to notebooks")
    if not ref.human_accepted:
        raise ValueError("Accept the external reference before attaching to a notebook")
    hits = (ref.payload.get("hits") or [])
    if hit_index < 0 or hit_index >= len(hits):
        raise IndexError("hit_index out of range")
    hit = hits[hit_index]
    uri = (
        hit.get("thumbnail_url")
        or hit.get("primaryImageSmall")
        or hit.get("page_url")
        or hit.get("objectURL")
        or ""
    )
    if not uri:
        raise ValueError("Selected hit has no image/page URI")
    title = hit.get("title") or ref.title
    creator = (
        hit.get("artist_display")
        or hit.get("artistDisplayName")
        or ref.attribution.creator_or_rights
    )
    nb = load_notebook(root, notebook_id).model_copy(deep=True)
    media = NotebookMedia(
        media_type="image",
        path_or_uri=uri,
        caption=title,
        attribution=SourceAttribution(
            source_title=title,
            creator_or_rights=str(creator),
            url_or_path=uri,
            license_or_fair_use_note=ref.attribution.license_or_fair_use_note,
            notes=f"Attached from external_ref {ref.id} by {reviewer}",
        ),
        observation_cue=ref.craft_use,
    )
    nb.media = list(nb.media) + [media]
    save_notebook(root, nb)
    ref = ref.model_copy(deep=True)
    ref.notebook_id = notebook_id
    save_external_reference(root, ref)
    record_meaningful_change(
        root,
        operation="integrations.attach_notebook",
        target_type="notebook",
        target_id=notebook_id,
        snapshot={"ref_id": ref.id, "media_id": media.id, "uri": uri},
        summary=f"Attached {title} to notebook {notebook_id}",
        creator=reviewer.strip(),
        actor=ActorKind.HUMAN,
        source_references=[uri, ref.source_url],
        input_parameters={"ref_id": ref_id, "hit_index": hit_index},
        outputs={"media_id": media.id, "applied_as_final": False},
        generated=False,
    )
    return {"notebook": nb, "media": media, "ref": ref}


def catalog_summary() -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in list_catalog()]
