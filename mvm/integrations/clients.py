"""HTTP clients for curated public craft-reference APIs (httpx)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from mvm.schemas.integrations import ReferenceKind, ReferenceProvider
from mvm.schemas.notebook import SourceAttribution

USER_AGENT = "MusicVideoMaker-CraftEngine/0.1 (craft-reference; +https://github.com/)"
DEFAULT_TIMEOUT = 20.0


class IntegrationError(RuntimeError):
    """Visible fetch failure — never silently invent craft data."""


def _client(client: httpx.Client | None = None) -> tuple[httpx.Client, bool]:
    if client is not None:
        return client, False
    return (
        httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ),
        True,
    )


def fetch_dictionary(
    word: str,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Free Dictionary API — phonetics for acting decisions."""
    w = (word or "").strip()
    if not w:
        raise IntegrationError("dictionary word is required")
    c, own = _client(client)
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(w)}"
        r = c.get(url)
        if r.status_code == 404:
            raise IntegrationError(f"No dictionary entry for {w!r}")
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            raise IntegrationError("Unexpected dictionary response")
        entry = data[0]
        phonetics = []
        for p in entry.get("phonetics") or []:
            phonetics.append(
                {
                    "text": p.get("text") or "",
                    "audio": p.get("audio") or "",
                    "source_url": p.get("sourceUrl") or "",
                    "license": (p.get("license") or {}).get("name", ""),
                }
            )
        meanings = []
        for m in (entry.get("meanings") or [])[:3]:
            defs = [
                d.get("definition", "")
                for d in (m.get("definitions") or [])[:2]
                if d.get("definition")
            ]
            meanings.append({"part_of_speech": m.get("partOfSpeech"), "definitions": defs})
        return {
            "provider": ReferenceProvider.FREE_DICTIONARY.value,
            "kind": ReferenceKind.PHONETICS.value,
            "query": w,
            "title": entry.get("word") or w,
            "summary": f"Phonetics for acting: {w}",
            "payload": {
                "word": entry.get("word"),
                "phonetics": phonetics,
                "meanings": meanings,
                "source_urls": entry.get("sourceUrls") or [],
                "license": entry.get("license") or {},
            },
            "source_url": url,
            "attribution": SourceAttribution(
                source_title=f"Free Dictionary: {w}",
                creator_or_rights="dictionaryapi.dev / Wiktionary contributors",
                url_or_path=url,
                license_or_fair_use_note=str(
                    (entry.get("license") or {}).get("name") or "See sourceUrls"
                ),
                notes="Reference for human dialogue acting — not auto lip-sync.",
            ),
            "craft_use": (
                "Inspect phonetics/audio when planning dialogue mouth shapes and "
                "emphasis; do not force a cue per phoneme."
            ),
        }
    finally:
        if own:
            c.close()


def fetch_artic_artworks(
    query: str,
    *,
    limit: int = 5,
    public_domain_only: bool = True,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Art Institute of Chicago — visual references with attribution."""
    q = (query or "").strip()
    if not q:
        raise IntegrationError("art search query is required")
    limit = max(1, min(int(limit), 12))
    c, own = _client(client)
    try:
        fields = "id,title,artist_display,date_display,image_id,is_public_domain"
        r = c.get(
            "https://api.artic.edu/api/v1/artworks/search",
            params={"q": q, "limit": limit, "fields": fields},
        )
        r.raise_for_status()
        body = r.json()
        iiif = (body.get("config") or {}).get("iiif_url") or "https://www.artic.edu/iiif/2"
        hits = []
        for item in body.get("data") or []:
            if public_domain_only and not item.get("is_public_domain"):
                continue
            image_id = item.get("image_id")
            thumb = f"{iiif}/{image_id}/full/400,/0/default.jpg" if image_id else ""
            hits.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "artist_display": item.get("artist_display"),
                    "date_display": item.get("date_display"),
                    "is_public_domain": item.get("is_public_domain"),
                    "image_id": image_id,
                    "thumbnail_url": thumb,
                    "page_url": f"https://www.artic.edu/artworks/{item.get('id')}",
                }
            )
        return {
            "provider": ReferenceProvider.ARTIC.value,
            "kind": ReferenceKind.VISUAL_REFERENCE.value,
            "query": q,
            "title": f"ARTIC search: {q}",
            "summary": f"{len(hits)} artwork hit(s) for notebook reference",
            "payload": {"hits": hits, "iiif_url": iiif},
            "source_url": "https://api.artic.edu/docs/",
            "attribution": SourceAttribution(
                source_title="Art Institute of Chicago API",
                creator_or_rights="Art Institute of Chicago / artwork rights per object",
                url_or_path="https://api.artic.edu/docs/",
                license_or_fair_use_note=(
                    "Metadata largely CC0; images subject to AIC terms — "
                    "prefer is_public_domain=true objects."
                ),
                notes="Attach only after human review; do not opaque-style-imitate.",
            ),
            "craft_use": (
                "Pick PD thumbnails into a reference notebook for pose/staging study; "
                "preserve attribution; never silent style transfer."
            ),
        }
    finally:
        if own:
            c.close()


def fetch_met_objects(
    query: str,
    *,
    limit: int = 5,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Metropolitan Museum — search then hydrate a few objects."""
    q = (query or "").strip()
    if not q:
        raise IntegrationError("met search query is required")
    limit = max(1, min(int(limit), 8))
    c, own = _client(client)
    try:
        search = c.get(
            "https://collectionapi.metmuseum.org/public/collection/v1/search",
            params={"q": q, "hasImages": "true"},
        )
        search.raise_for_status()
        ids = (search.json().get("objectIDs") or [])[:limit]
        hits = []
        for oid in ids:
            obj = c.get(
                f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"
            )
            if obj.status_code != 200:
                continue
            data = obj.json()
            hits.append(
                {
                    "objectID": data.get("objectID"),
                    "title": data.get("title"),
                    "artistDisplayName": data.get("artistDisplayName"),
                    "objectDate": data.get("objectDate"),
                    "isPublicDomain": data.get("isPublicDomain"),
                    "primaryImageSmall": data.get("primaryImageSmall") or "",
                    "objectURL": data.get("objectURL") or "",
                }
            )
        return {
            "provider": ReferenceProvider.MET_MUSEUM.value,
            "kind": ReferenceKind.VISUAL_REFERENCE.value,
            "query": q,
            "title": f"Met search: {q}",
            "summary": f"{len(hits)} Met object(s) for reference",
            "payload": {"hits": hits},
            "source_url": "https://metmuseum.github.io/",
            "attribution": SourceAttribution(
                source_title="The Metropolitan Museum of Art Collection API",
                creator_or_rights="The Metropolitan Museum of Art / per-object rights",
                url_or_path="https://metmuseum.github.io/",
                license_or_fair_use_note="Respect isPublicDomain and Met terms of use.",
                notes="Human attach only.",
            ),
            "craft_use": (
                "Use public-domain images as observational references in notebooks."
            ),
        }
    finally:
        if own:
            c.close()


def fetch_musicbrainz_recordings(
    query: str,
    *,
    limit: int = 5,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """MusicBrainz recordings — metadata for sequence/credits context."""
    q = (query or "").strip()
    if not q:
        raise IntegrationError("musicbrainz query is required")
    limit = max(1, min(int(limit), 10))
    c, own = _client(client)
    try:
        r = c.get(
            "https://musicbrainz.org/ws/2/recording",
            params={"query": q, "fmt": "json", "limit": limit},
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        recordings = []
        for rec in r.json().get("recordings") or []:
            artists = [
                a.get("name")
                for a in (rec.get("artist-credit") or [])
                if isinstance(a, dict) and a.get("name")
            ]
            recordings.append(
                {
                    "id": rec.get("id"),
                    "title": rec.get("title"),
                    "artists": artists,
                    "length_ms": rec.get("length"),
                    "score": rec.get("score"),
                    "url": f"https://musicbrainz.org/recording/{rec.get('id')}",
                }
            )
        return {
            "provider": ReferenceProvider.MUSICBRAINZ.value,
            "kind": ReferenceKind.MUSIC_METADATA.value,
            "query": q,
            "title": f"MusicBrainz: {q}",
            "summary": f"{len(recordings)} recording hit(s)",
            "payload": {"recordings": recordings},
            "source_url": "https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2",
            "attribution": SourceAttribution(
                source_title="MusicBrainz",
                creator_or_rights="MetaBrainz Foundation / contributors",
                url_or_path="https://musicbrainz.org/",
                license_or_fair_use_note="CC BY-NC-SA for MusicBrainz data — credit sources.",
                notes="Metadata aid only; local MIR remains beat authority.",
            ),
            "craft_use": (
                "Confirm track identity/credits for provenance; do not replace beatmap."
            ),
        }
    finally:
        if own:
            c.close()


def fetch_colormind_palette(
    *,
    model: str = "default",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Colormind — palette suggestion for color-script exploration."""
    c, own = _client(client)
    try:
        r = c.post(
            "http://colormind.io/api/",
            json={"model": model},
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        result = r.json().get("result") or []
        hexes = [f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}" for rgb in result]
        return {
            "provider": ReferenceProvider.COLORMIND.value,
            "kind": ReferenceKind.COLOR_PALETTE.value,
            "query": model,
            "title": f"Colormind palette ({model})",
            "summary": f"Suggested palette: {', '.join(hexes)}",
            "payload": {"rgb": result, "hex": hexes, "model": model},
            "source_url": "http://colormind.io/api-access/",
            "attribution": SourceAttribution(
                source_title="Colormind",
                creator_or_rights="colormind.io",
                url_or_path="http://colormind.io/api-access/",
                license_or_fair_use_note="Generated palette suggestion — human must accept.",
                notes="Suggestion only; not a grade or auto color script.",
            ),
            "craft_use": (
                "Compare against silhouette readability; accept into color notes manually."
            ),
        }
    finally:
        if own:
            c.close()


def fetch_lyrics_ovh(
    artist: str,
    title: str,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Lyrics.ovh — best-effort lyrics for hold-for-lyric planning."""
    a = (artist or "").strip()
    t = (title or "").strip()
    if not a or not t:
        raise IntegrationError("lyrics require artist and title")
    c, own = _client(client)
    try:
        url = f"https://api.lyrics.ovh/v1/{quote(a)}/{quote(t)}"
        r = c.get(url)
        if r.status_code == 404:
            raise IntegrationError(
                f"No lyrics found for {a!r} — {t!r} (lyrics.ovh is best-effort)"
            )
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise IntegrationError(str(data["error"]))
        lyrics = (data.get("lyrics") or "").strip()
        if not lyrics:
            raise IntegrationError("Empty lyrics payload")
        return {
            "provider": ReferenceProvider.LYRICS_OVH.value,
            "kind": ReferenceKind.LYRICS.value,
            "query": f"{a} / {t}",
            "title": f"{t} — {a}",
            "summary": f"Lyrics fetched ({len(lyrics.splitlines())} lines) — review before timing",
            "payload": {"artist": a, "title": t, "lyrics": lyrics},
            "source_url": url,
            "attribution": SourceAttribution(
                source_title=f"Lyrics.ovh: {t} by {a}",
                creator_or_rights="lyrics.ovh / underlying lyric rights holders",
                url_or_path=url,
                license_or_fair_use_note=(
                    "Lyrics may be copyrighted — use for private craft timing only; "
                    "do not redistribute."
                ),
                notes="Never force motion per syllable.",
            ),
            "craft_use": (
                "Mark hold_for_lyric and silence regions; do not auto-generate lip flaps."
            ),
        }
    finally:
        if own:
            c.close()
