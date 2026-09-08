"""Curated public-apis integrations that create better human craft conditions.

Source catalog: https://github.com/public-apis/public-apis
Principle: fetch references for decisions — never auto-manufacture animation.
"""

from __future__ import annotations

from mvm.schemas.integrations import IntegrationCatalogEntry, ReferenceProvider

CRAFT_INTEGRATIONS: tuple[IntegrationCatalogEntry, ...] = (
    IntegrationCatalogEntry(
        provider=ReferenceProvider.FREE_DICTIONARY,
        public_apis_category="Dictionaries",
        name="Free Dictionary API",
        docs_url="https://dictionaryapi.dev/",
        auth="No",
        cors="Yes",
        craft_role=(
            "Phonetics and pronunciation audio for dialogue acting decisions "
            "(mouth shapes, emphasis) — human chooses what to use."
        ),
        enhances=["dialogue", "acting", "sound_relationship", "intent_clarity"],
        non_generative_guarantee=(
            "Returns dictionary data only; does not generate drawings or timing."
        ),
    ),
    IntegrationCatalogEntry(
        provider=ReferenceProvider.ARTIC,
        public_apis_category="Art & Design",
        name="Art Institute of Chicago",
        docs_url="https://api.artic.edu/docs/",
        auth="No",
        cors="Yes",
        craft_role=(
            "Public-domain artworks as attributed visual references for notebooks "
            "(pose, silhouette, staging study) — attach only with human accept."
        ),
        enhances=["pose_readability", "staging", "notebooks", "authorship"],
        non_generative_guarantee=(
            "Search/metadata + IIIF image URLs; never baked into finals automatically."
        ),
    ),
    IntegrationCatalogEntry(
        provider=ReferenceProvider.MET_MUSEUM,
        public_apis_category="Art & Design",
        name="Metropolitan Museum of Art",
        docs_url="https://metmuseum.github.io/",
        auth="No",
        cors="Yes",
        craft_role=(
            "Additional public collection search for reference boards; "
            "attribution required before notebook attach."
        ),
        enhances=["notebooks", "visual_reference", "authorship"],
        non_generative_guarantee="Collection metadata/images only; human attach gate.",
    ),
    IntegrationCatalogEntry(
        provider=ReferenceProvider.MUSICBRAINZ,
        public_apis_category="Music",
        name="MusicBrainz",
        docs_url="https://musicbrainz.org/doc/Development/XML_Web_Service/Version_2",
        auth="No",
        cors="Unknown",
        craft_role=(
            "Recording/release metadata for sequence context and credit provenance "
            "(not beat detection — local MIR remains authoritative)."
        ),
        enhances=["sequence_context", "provenance", "sound_relationship"],
        non_generative_guarantee="Metadata only; does not rewrite timing or craft shots.",
    ),
    IntegrationCatalogEntry(
        provider=ReferenceProvider.COLORMIND,
        public_apis_category="Art & Design",
        name="Colormind",
        docs_url="http://colormind.io/api-access/",
        auth="No",
        cors="Unknown",
        craft_role=(
            "Palette suggestions for color-script exploration — visible suggestions "
            "with confidence; human accepts into notes, never silent grade."
        ),
        enhances=["staging", "color_script", "readability"],
        non_generative_guarantee="RGB palettes only; not applied to renders automatically.",
    ),
    IntegrationCatalogEntry(
        provider=ReferenceProvider.LYRICS_OVH,
        public_apis_category="Music",
        name="Lyrics.ovh",
        docs_url="https://lyricsovh.docs.apiary.io/",
        auth="No",
        cors="Yes",
        craft_role=(
            "Optional lyrics text for hold-for-lyric planning and dialogue timing "
            "reviews — never forces lip motion per syllable."
        ),
        enhances=["timing", "sound_relationship", "intent_clarity"],
        non_generative_guarantee=(
            "Plain lyrics text if found; force_every_cue_to_motion stays false."
        ),
        reliability_note=(
            "Public reports of intermittent 404 / missing lyrics — treat as best-effort."
        ),
    ),
)


def list_catalog() -> list[IntegrationCatalogEntry]:
    return list(CRAFT_INTEGRATIONS)


def get_catalog_entry(provider: ReferenceProvider | str) -> IntegrationCatalogEntry:
    key = (
        provider
        if isinstance(provider, ReferenceProvider)
        else ReferenceProvider(str(provider))
    )
    for e in CRAFT_INTEGRATIONS:
        if e.provider == key:
            return e
    raise KeyError(f"Unknown provider: {provider}")
