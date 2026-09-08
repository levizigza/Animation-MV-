"""Reference notebooks: attachment, attribution, revision persistence."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mvm.notebook import (
    SourceAttribution,
    assistance_context,
    attach_media,
    create_notebook,
    load_notebook,
    revise_notebook,
    update_craft_notes,
)
from mvm.project.domain_store import load_provenance, load_revisions
from mvm.schemas.notebook import ReferenceNotebook


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in ("notebooks", "revisions", "provenance"):
        (root / sub).mkdir(parents=True)
    return root


def test_attach_requires_attribution_and_persists():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        nb = create_notebook(
            root, scope="character", project_slug="demo", character_id="hero", character_name="Hero"
        )
        with pytest.raises(Exception):
            attach_media(
                root,
                nb.id,
                path_or_uri="refs/hero.png",
                attribution={"source_title": ""},
            )

        nb = attach_media(
            root,
            nb.id,
            path_or_uri="refs/hero_turnaround.png",
            media_type="image",
            caption="3/4 turn",
            attribution=SourceAttribution(
                source_title="Production model sheet v2",
                creator_or_rights="Studio Art Dept",
                url_or_path="refs/hero_turnaround.png",
                license_or_fair_use_note="internal production asset",
            ),
        )
        nb = attach_media(
            root,
            nb.id,
            path_or_uri="refs/walk_ref.mp4",
            media_type="video",
            caption="weight shift",
            attribution=SourceAttribution(
                source_title="Acting reel clip 04",
                creator_or_rights="Performer Name",
                url_or_path="refs/walk_ref.mp4",
            ),
            observation_cue="00:01:12 weight onto front foot",
        )
        loaded = load_notebook(root, nb.id)
        assert len(loaded.media) == 2
        assert loaded.media[0].attribution.source_title == "Production model sheet v2"
        assert loaded.media[1].media_type == "video"
        assert loaded.opaque_style_imitation is False

        provs = load_provenance(root)
        assert any(
            p.operation == "human.notebook_attach_media"
            and p.outputs.get("source_title") == "Acting reel clip 04"
            for p in provs
        )


def test_assistance_is_explicit_metadata_not_opaque_imitation():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        nb = create_notebook(root, scope="project", project_slug="demo", title="World refs")
        update_craft_notes(
            root,
            nb.id,
            observational_notes=["Shoulders lead turns"],
            preserve=["clear silhouette", "heavy boots"],
            exaggerate=["coat flare on turns"],
            omit=["facial micro-twitch", "realistic sweat"],
            acting_observations=["glance then commit"],
            movement_vocabulary=["planted stop", "coat drag"],
            recurring_behaviors=["adjusts cuff before exit"],
            transformation_notes=["simplify hands to mitten shapes in far shots"],
        )
        ctx = assistance_context(root, nb.id)
        assert ctx["influence_mode"] == "explicit_metadata"
        assert ctx["opaque_style_imitation"] is False
        assist = ctx["assistance"]
        assert assist["influence_mode"] == "explicit_metadata"
        assert "clear silhouette" in assist["preserve"]
        assert "facial micro-twitch" in assist["omit"]
        assert "planted stop" in assist["movement_vocabulary"]
        assert "adjusts cuff before exit" in assist["recurring_behaviors"]

        with pytest.raises(Exception):
            data = load_notebook(root, nb.id).model_dump(mode="json")
            data["opaque_style_imitation"] = True
            ReferenceNotebook.model_validate(data)


def test_revision_persists_media_and_attribution():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        nb = create_notebook(
            root, scope="character", project_slug="demo", character_id="hero"
        )
        nb = attach_media(
            root,
            nb.id,
            path_or_uri="refs/a.png",
            attribution=SourceAttribution(
                source_title="Sheet A",
                creator_or_rights="Artist",
                url_or_path="refs/a.png",
            ),
        )
        media_before = [m.model_dump(mode="json") for m in nb.media]
        child = revise_notebook(root, nb.id, summary="Add more acting notes later")
        assert child.id != nb.id
        assert child.version == nb.version + 1
        assert child.parent_notebook_id == nb.id
        assert len(child.media) == len(media_before)
        assert child.media[0].attribution.source_title == "Sheet A"
        assert child.media[0].path_or_uri == "refs/a.png"
        # Parent unchanged on disk
        parent = load_notebook(root, nb.id)
        assert parent.media[0].attribution.source_title == "Sheet A"

        revs = load_revisions(root)
        assert any(
            r.target_type == "notebook"
            and r.snapshot.get("parent_id") == nb.id
            and r.snapshot.get("attributions_persisted")
            for r in revs
        )
        assert any(
            p.operation == "human.notebook_revise"
            and p.outputs.get("media_count") == 1
            for p in load_provenance(root)
        )
