"""Public craft-reference integrations (from public-apis) — suggestions, not finals."""

from mvm.integrations.catalog import CRAFT_INTEGRATIONS, get_catalog_entry, list_catalog
from mvm.integrations.clients import IntegrationError
from mvm.integrations.workflow import (
    accept_external_reference,
    attach_visual_ref_to_notebook,
    catalog_summary,
    fetch_and_store_artic,
    fetch_and_store_dictionary,
    fetch_and_store_lyrics,
    fetch_and_store_met,
    fetch_and_store_musicbrainz,
    fetch_and_store_palette,
    list_external_references,
    load_external_reference,
)

__all__ = [
    "CRAFT_INTEGRATIONS",
    "IntegrationError",
    "accept_external_reference",
    "attach_visual_ref_to_notebook",
    "catalog_summary",
    "fetch_and_store_artic",
    "fetch_and_store_dictionary",
    "fetch_and_store_lyrics",
    "fetch_and_store_met",
    "fetch_and_store_musicbrainz",
    "fetch_and_store_palette",
    "get_catalog_entry",
    "list_catalog",
    "list_external_references",
    "load_external_reference",
]
