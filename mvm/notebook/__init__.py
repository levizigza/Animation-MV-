"""Project/character reference notebooks."""

from mvm.notebook.workflow import (
    assistance_context,
    attach_media,
    create_notebook,
    load_notebook,
    list_notebooks,
    revise_notebook,
    update_craft_notes,
)
from mvm.schemas.notebook import (
    AssistanceMetadata,
    NotebookMedia,
    ReferenceNotebook,
    SourceAttribution,
    build_assistance_metadata,
)

__all__ = [
    "AssistanceMetadata",
    "NotebookMedia",
    "ReferenceNotebook",
    "SourceAttribution",
    "assistance_context",
    "attach_media",
    "build_assistance_metadata",
    "create_notebook",
    "load_notebook",
    "list_notebooks",
    "revise_notebook",
    "update_craft_notes",
]
