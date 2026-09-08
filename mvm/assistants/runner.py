"""Shared runner for narrow assistants — suggestions + provenance, no silent edits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from mvm.assistants.base import (
    ASSISTANT_READ_DOMAINS,
    AssistantId,
    AssistantResult,
    AssistantSuggestion,
    DomainFence,
)
from mvm.provenance import record_meaningful_change
from mvm.schemas.domain import ActorKind


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_assistant_result(root: Path, result: AssistantResult) -> Path:
    d = root / "assistant_suggestions"
    d.mkdir(parents=True, exist_ok=True)
    name = result.provenance_id or (
        result.suggestions[0].id if result.suggestions else result.assistant_id.value
    )
    path = d / f"{name}.json"
    _write(path, result)
    return path


def run_scoped_suggest(
    root: Path,
    *,
    assistant_id: AssistantId,
    input_assumptions: list[str],
    build_suggestions: Callable[[DomainFence], list[AssistantSuggestion]],
    summary: str,
    input_parameters: dict[str, Any] | None = None,
) -> AssistantResult:
    """Run an assistant suggest pass under a domain fence."""
    fence = DomainFence(assistant_id=assistant_id)
    suggestions = build_suggestions(fence)
    for s in suggestions:
        if s.applied is not False:
            raise RuntimeError("Assistant attempted to mark suggestion applied")
        if s.assistant_id != assistant_id:
            raise PermissionError("Suggestion assistant_id mismatch")

    # Allowed suggest-time write: provenance bundle
    fence.check_write("assistant_suggestions")
    fence.check_write("provenance")
    fence.check_write("revisions")

    recorded = record_meaningful_change(
        root,
        operation=f"assistant.{assistant_id.value}.suggest",
        target_type="shot",
        target_id=str((input_parameters or {}).get("shot_id") or "project"),
        snapshot={
            "assistant_id": assistant_id.value,
            "suggestions": [s.model_dump(mode="json") for s in suggestions],
            "input_assumptions": input_assumptions,
            "silently_edited": False,
        },
        summary=summary,
        creator=f"assistant:{assistant_id.value}",
        actor=ActorKind.HEURISTIC_AGENT,
        source_references=[f"assistant:{assistant_id.value}"],
        input_parameters={
            "assumptions": input_assumptions,
            "scope": sorted(ASSISTANT_READ_DOMAINS[assistant_id]),
            **(input_parameters or {}),
        },
        outputs={
            "suggestion_count": len(suggestions),
            "visibly_labeled_generated": True,
        },
        generated_alternatives=[
            {"id": s.id, "action": s.action, "confidence": s.confidence}
            for s in suggestions
        ],
        generated=True,
    )

    result = AssistantResult(
        assistant_id=assistant_id,
        input_assumptions=input_assumptions,
        scope=sorted(ASSISTANT_READ_DOMAINS[assistant_id]),
        suggestions=suggestions,
        refused_writes=[],
        provenance_id=recorded["provenance"].id,
        revision_id=recorded["revision"].id,
        silently_edited=False,
        summary=summary,
    )
    save_assistant_result(root, result)

    # Soft proposals → symbolic grounder (blocked stay visible with reasons)
    from mvm.neurosymbolic.bridge import ground_assistant_result

    shot_id = str((input_parameters or {}).get("shot_id") or "") or None
    ground_assistant_result(root, result, shot_id=shot_id)
    return result
