"""Unified provenance tracking — record, accept/reject, export/import, restore."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import (
    ensure_domain_dirs,
    load_provenance,
    load_revisions,
    save_provenance,
    save_revision,
)
from mvm.provenance.guardrails import assert_guardrails, evaluate_guardrails
from mvm.schemas.domain import (
    ActorKind,
    ProvenanceAcceptance,
    ProvenanceRecord,
    Revision,
    make_provenance,
    make_revision,
    new_id,
    restore_snapshot,
    utc_now,
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


def ensure_provenance_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "provenance").mkdir(parents=True, exist_ok=True)
    (root / "revisions").mkdir(parents=True, exist_ok=True)
    (root / "provenance_exports").mkdir(parents=True, exist_ok=True)


def load_provenance_record(root: Path, provenance_id: str) -> ProvenanceRecord:
    return ProvenanceRecord.model_validate(
        _read(root / "provenance" / f"{provenance_id}.json")
    )


def record_meaningful_change(
    root: Path,
    *,
    operation: str,
    target_type: str,
    target_id: str,
    snapshot: dict[str, Any],
    summary: str,
    creator: str = "",
    actor: ActorKind = ActorKind.HEURISTIC_AGENT,
    source_references: list[str] | None = None,
    input_parameters: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    generated_alternatives: list[dict[str, Any]] | None = None,
    parent_revision_id: str | None = None,
    # Guardrail signals (callers must be honest — defaults assume safe)
    hidden_full_shot_replacement: bool = False,
    silent_smoothing: bool = False,
    overwrite_approved: bool = False,
    asset_substitution: bool = False,
    style_control: str | None = None,
    generated: bool = True,
) -> dict[str, Any]:
    """Record a meaningful change with full provenance + guardrail checks."""
    ensure_provenance_dirs(root)
    labeled = generated and actor in (
        ActorKind.HEURISTIC_AGENT,
        ActorKind.SYSTEM,
    )
    report = evaluate_guardrails(
        hidden_full_shot_replacement=hidden_full_shot_replacement,
        silent_smoothing=silent_smoothing,
        overwrite_approved=overwrite_approved,
        asset_substitution=asset_substitution,
        asset_source_references=source_references,
        style_control=style_control,
        generated=generated,
        visibly_labeled_generated=labeled or not generated,
    )
    assert_guardrails(report)

    params = dict(input_parameters or {})
    if style_control:
        params.setdefault("style_control_checked", style_control)

    rev = make_revision(
        target_type=target_type,
        target_id=target_id,
        snapshot=snapshot,
        summary=summary,
        parent_id=parent_revision_id,
        created_by=actor,
    )
    prov = make_provenance(
        operation=operation,
        revision_id=rev.id,
        actor=actor,
        creator=creator or actor.value,
        summary=summary,
        inputs=params,
        outputs=outputs,
        source_references=source_references,
        generated_alternatives=generated_alternatives,
        visibly_labeled_generated=labeled or (actor == ActorKind.HEURISTIC_AGENT),
        guardrails=report.checks,
        acceptance_state=ProvenanceAcceptance.PENDING,
    )
    rev.provenance_ids.append(prov.id)
    save_revision(root, rev)
    save_provenance(root, prov)
    return {
        "ok": True,
        "revision": rev,
        "provenance": prov,
        "guardrails": report.checks,
        "visibly_labeled_generated": prov.visibly_labeled_generated,
    }


def set_acceptance(
    root: Path,
    provenance_id: str,
    *,
    state: ProvenanceAcceptance | str,
    actor: str = "human",
    notes: str = "",
) -> ProvenanceRecord:
    prov = load_provenance_record(root, provenance_id).model_copy(deep=True)
    st = state if isinstance(state, ProvenanceAcceptance) else ProvenanceAcceptance(str(state))
    prov.acceptance_state = st
    if notes:
        prov.human_edits_after_generation = list(prov.human_edits_after_generation) + [
            {
                "at": utc_now(),
                "actor": actor,
                "kind": "acceptance",
                "state": st.value,
                "notes": notes,
            }
        ]
    save_provenance(root, prov)
    return prov


def record_human_edit_after_generation(
    root: Path,
    provenance_id: str,
    *,
    edit_summary: str,
    fields_changed: list[str] | None = None,
    actor: str = "human",
) -> ProvenanceRecord:
    prov = load_provenance_record(root, provenance_id).model_copy(deep=True)
    prov.human_edits_after_generation = list(prov.human_edits_after_generation) + [
        {
            "at": utc_now(),
            "actor": actor,
            "kind": "human_edit",
            "summary": edit_summary,
            "fields_changed": list(fields_changed or []),
        }
    ]
    save_provenance(root, prov)
    return prov


def final_approve_provenance(
    root: Path,
    provenance_id: str,
    *,
    approved_by: str,
) -> ProvenanceRecord:
    if not approved_by.strip():
        raise ValueError("final approval requires approved_by identity")
    prov = load_provenance_record(root, provenance_id).model_copy(deep=True)
    prov.final_approval = True
    prov.final_approval_by = approved_by.strip()
    prov.final_approval_at = utc_now()
    prov.acceptance_state = ProvenanceAcceptance.ACCEPTED
    save_provenance(root, prov)
    return prov


def export_provenance_bundle(
    root: Path,
    *,
    revision_ids: list[str] | None = None,
    dest: Path | None = None,
) -> Path:
    """Export revisions + provenance for inspect/restore across machines."""
    ensure_provenance_dirs(root)
    revs = load_revisions(root)
    provs = load_provenance(root)
    if revision_ids is not None:
        want = set(revision_ids)
        revs = [r for r in revs if r.id in want]
        linked = {pid for r in revs for pid in r.provenance_ids}
        # Also include provenance that points at these revisions
        provs = [
            p
            for p in provs
            if p.id in linked or p.revision_id in want
        ]
    bundle = {
        "format": "mvm.provenance_bundle",
        "format_version": 1,
        "revisions": [r.model_dump(mode="json") for r in revs],
        "provenance": [p.model_dump(mode="json") for p in provs],
        "notes": (
            "Provenance survives export/import. Generated entries stay labeled. "
            "Restore via restore_revision."
        ),
    }
    out = dest or (
        root / "provenance_exports" / f"bundle_{new_id('pb')}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return out


def import_provenance_bundle(root: Path, bundle_path: Path) -> dict[str, Any]:
    ensure_provenance_dirs(root)
    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    if data.get("format") != "mvm.provenance_bundle":
        raise ValueError("Not an mvm.provenance_bundle")
    revs = [Revision.model_validate(r) for r in data.get("revisions") or []]
    provs = [ProvenanceRecord.model_validate(p) for p in data.get("provenance") or []]
    for r in revs:
        save_revision(root, r)
    for p in provs:
        # Preserve labels after import
        if p.actor == ActorKind.HEURISTIC_AGENT:
            p.visibly_labeled_generated = True
        save_provenance(root, p)
    return {
        "ok": True,
        "revisions": len(revs),
        "provenance": len(provs),
        "labeled_generated": sum(1 for p in provs if p.visibly_labeled_generated),
    }


def restore_revision(
    root: Path,
    revision_id: str,
    *,
    restored_by: str = "human",
) -> dict[str, Any]:
    """Inspect and restore a prior revision snapshot; record provenance of restore."""
    ensure_provenance_dirs(root)
    path = root / "revisions" / f"{revision_id}.json"
    if not path.exists():
        return {"ok": False, "reason": f"Revision {revision_id} not found"}
    rev = Revision.model_validate(_read(path))
    snapshot = restore_snapshot(rev)

    # Write restored payload beside revisions for inspectability
    restore_path = root / "revisions" / f"restored_{revision_id}.json"
    _write(
        restore_path,
        {
            "restored_from": revision_id,
            "target_type": rev.target_type,
            "target_id": rev.target_id,
            "snapshot": snapshot,
            "at": utc_now(),
            "restored_by": restored_by,
        },
    )

    out = record_meaningful_change(
        root,
        operation="human.restore_revision",
        target_type=rev.target_type,
        target_id=rev.target_id,
        snapshot={
            "restored_from": revision_id,
            "snapshot": snapshot,
        },
        summary=f"Restored prior revision {revision_id}",
        creator=restored_by,
        actor=ActorKind.HUMAN,
        source_references=[f"revision:{revision_id}"],
        input_parameters={"revision_id": revision_id},
        outputs={"restore_path": str(restore_path.name)},
        generated=False,
        parent_revision_id=revision_id,
    )
    out["snapshot"] = snapshot
    out["restore_path"] = restore_path
    return out


def inspect_provenance(root: Path, provenance_id: str) -> dict[str, Any]:
    prov = load_provenance_record(root, provenance_id)
    return {
        "id": prov.id,
        "creator": prov.creator,
        "timestamp": prov.at,
        "source_references": prov.source_references,
        "model_or_assistant_operation": prov.model_or_assistant_operation,
        "input_parameters": prov.input_parameters or prov.inputs,
        "generated_alternatives": prov.generated_alternatives,
        "accepted_rejected_state": prov.acceptance_state.value,
        "human_edits_after_generation": prov.human_edits_after_generation,
        "final_approval": prov.final_approval,
        "final_approval_by": prov.final_approval_by,
        "visibly_labeled_generated": prov.visibly_labeled_generated,
        "guardrails": prov.guardrails,
        "reversible": prov.reversible,
        "revision_id": prov.revision_id,
    }
