"""Craft integrations: public-apis refs + human final approve — never silent finals."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import httpx
import pytest

from mvm.integrations import (
    IntegrationError,
    accept_external_reference,
    attach_visual_ref_to_notebook,
    fetch_and_store_artic,
    fetch_and_store_dictionary,
    fetch_and_store_palette,
    list_catalog,
    list_external_references,
)
from mvm.integrations.clients import fetch_dictionary
from mvm.notebook import create_notebook
from mvm.project.reviews import approve_shot_final
from mvm.schemas.integrations import ExternalReference
from mvm.schemas.models import ApprovalState, Shot, ShotIntent, ShotLifecycleState
from mvm.project.workspace import _write_json


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in (
        "external_refs",
        "notebooks",
        "provenance",
        "revisions",
        "reviews",
        "shots",
        "layouts",
        "panels",
    ):
        (root / sub).mkdir(parents=True)
    return root


def test_catalog_curates_public_apis_for_craft_not_generation():
    entries = list_catalog()
    assert len(entries) >= 5
    providers = {e.provider.value for e in entries}
    assert "free_dictionary" in providers
    assert "art_institute_chicago" in providers
    assert "musicbrainz" in providers
    for e in entries:
        assert e.non_generative_guarantee
        assert e.craft_role


def test_dictionary_fetch_mocked_and_never_final():
    payload = [
        {
            "word": "sorry",
            "phonetics": [{"text": "/ˈsɒr.i/", "audio": "", "sourceUrl": "https://example"}],
            "meanings": [
                {
                    "partOfSpeech": "adjective",
                    "definitions": [{"definition": "feeling regret"}],
                }
            ],
            "license": {"name": "CC BY-SA 3.0"},
            "sourceUrls": ["https://en.wiktionary.org/wiki/sorry"],
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert "dictionaryapi.dev" in str(request.url)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        data = fetch_dictionary("sorry", client=client)
        assert data["kind"] == "phonetics"
        assert data["payload"]["phonetics"][0]["text"]

    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        with httpx.Client(transport=transport) as client:
            ref = fetch_and_store_dictionary(
                root, "sorry", shot_id="shot_1", client=client
            )
        assert ref.applied_as_final is False
        assert ref.human_accepted is False
        assert ref.visibly_labeled_external is True
        assert (root / "external_refs" / f"{ref.id}.json").exists()
        accepted = accept_external_reference(
            root, ref.id, reviewer="animator.kim", note="Use for apology mouth shapes"
        )
        assert accepted.human_accepted is True
        assert accepted.applied_as_final is False

        with pytest.raises(Exception):
            raw = accepted.model_dump(mode="json")
            raw["applied_as_final"] = True
            ExternalReference.model_validate(raw)


def test_artic_attach_requires_human_accept():
    artic_body = {
        "data": [
            {
                "id": 1,
                "title": "Dancer",
                "artist_display": "Anon",
                "date_display": "1900",
                "image_id": "abc",
                "is_public_domain": True,
            }
        ],
        "config": {"iiif_url": "https://www.artic.edu/iiif/2"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=artic_body)

    transport = httpx.MockTransport(handler)
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        nb = create_notebook(
            root, scope="project", project_slug="proj", title="Refs"
        )
        with httpx.Client(transport=transport) as client:
            ref = fetch_and_store_artic(root, "dance", client=client)
        with pytest.raises(ValueError, match="Accept"):
            attach_visual_ref_to_notebook(
                root,
                ref_id=ref.id,
                notebook_id=nb.id,
                reviewer="lee",
            )
        accept_external_reference(root, ref.id, reviewer="lee")
        out = attach_visual_ref_to_notebook(
            root, ref_id=ref.id, notebook_id=nb.id, reviewer="lee", hit_index=0
        )
        assert out["media"].path_or_uri.startswith("https://")
        assert out["media"].attribution.source_title


def test_palette_mocked():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"result": [[255, 0, 0], [0, 255, 0], [0, 0, 255], [10, 10, 10], [200, 200, 200]]}
        )

    transport = httpx.MockTransport(handler)
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        with httpx.Client(transport=transport) as client:
            ref = fetch_and_store_palette(root, client=client)
        assert ref.kind.value == "color_palette"
        assert len(ref.payload["hex"]) == 5


def test_approve_shot_final_requires_comment_and_animatic():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        shot = Shot(
            id="shot_f",
            index=1,
            section="verse",
            start=0.0,
            end=2.0,
            duration=2.0,
            intent=ShotIntent(purpose="Clear apology read"),
            lifecycle_state=ShotLifecycleState.SOUND_EDIT_REVIEW,
            animatic_approved=True,
            timing_plan_id="timing_1",
            key_pose_ids=["pose_a"],
        )
        _write_json(root / "shots" / "shot_f.json", shot)

        bad = approve_shot_final(root, "shot_f", comment="", reviewer="lee")
        assert bad["ok"] is False

        early = Shot(
            id="shot_early",
            index=0,
            section="verse",
            start=0.0,
            end=1.0,
            duration=1.0,
            intent=ShotIntent(purpose="Too early"),
            lifecycle_state=ShotLifecycleState.ANIMATIC,
            animatic_approved=True,
        )
        _write_json(root / "shots" / "shot_early.json", early)
        blocked = approve_shot_final(
            root, "shot_early", comment="Looks fine", reviewer="lee"
        )
        assert blocked["ok"] is False

        ok = approve_shot_final(
            root,
            "shot_f",
            comment="Intent reads: delayed listener reaction lands.",
            reviewer="lee",
        )
        assert ok["ok"] is True
        assert ok["shot"]["lifecycle_state"] == "approved"
        assert ok["shot"]["approval"] == ApprovalState.APPROVED.value
        assert list_external_references(root) == []


def test_dictionary_empty_word_fails_visibly():
    with pytest.raises(IntegrationError):
        fetch_dictionary("  ")
