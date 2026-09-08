"""Provenance survives export/import and revision restoration; guardrails enforced."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mvm.provenance import (
    evaluate_guardrails,
    export_provenance_bundle,
    final_approve_provenance,
    import_provenance_bundle,
    inspect_provenance,
    record_human_edit_after_generation,
    record_meaningful_change,
    restore_revision,
    set_acceptance,
)
from mvm.schemas.domain import ActorKind, ProvenanceAcceptance, ProvenanceRecord


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in ("provenance", "revisions", "provenance_exports"):
        (root / sub).mkdir(parents=True)
    return root


def test_record_fields_and_guardrails():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        out = record_meaningful_change(
            root,
            operation="agents.suggest_inbetweens",
            target_type="timing_plan",
            target_id="timing_1",
            snapshot={"slots": [{"frame": 3}]},
            summary="Generated spacing alternatives",
            creator="heuristic_agent",
            actor=ActorKind.HEURISTIC_AGENT,
            source_references=["timing:timing_1", "pose:pose_a"],
            input_parameters={"mode": "slow_in", "from": "pose_a", "to": "pose_b"},
            generated_alternatives=[
                {"id": "alt_a", "mode": "slow_in"},
                {"id": "alt_b", "mode": "stepped"},
            ],
            outputs={"chosen_preview": "alt_a"},
            generated=True,
        )
        prov = out["provenance"]
        assert prov.creator == "heuristic_agent"
        assert prov.at
        assert prov.source_references == ["timing:timing_1", "pose:pose_a"]
        assert prov.model_or_assistant_operation == "agents.suggest_inbetweens"
        assert prov.input_parameters["mode"] == "slow_in"
        assert len(prov.generated_alternatives) == 2
        assert prov.acceptance_state == ProvenanceAcceptance.PENDING
        assert prov.visibly_labeled_generated is True
        assert prov.final_approval is False
        assert prov.guardrails.get("no_silent_smoothing") is True

        # Living artist style control blocked
        blocked = evaluate_guardrails(style_control="in the style of Miyazaki", generated=False)
        assert blocked.ok is False
        assert any(v.code == "living_artist_style_control" for v in blocked.violations)

        with pytest.raises(PermissionError):
            record_meaningful_change(
                root,
                operation="agents.style",
                target_type="shot",
                target_id="shot_1",
                snapshot={},
                summary="bad",
                style_control="Miyazaki",
                generated=False,
            )

        with pytest.raises(PermissionError):
            record_meaningful_change(
                root,
                operation="agents.replace_shot",
                target_type="shot",
                target_id="shot_1",
                snapshot={},
                summary="hidden replace",
                hidden_full_shot_replacement=True,
                generated=True,
            )

        with pytest.raises(PermissionError):
            record_meaningful_change(
                root,
                operation="agents.smooth",
                target_type="timing_plan",
                target_id="t",
                snapshot={},
                summary="smooth",
                silent_smoothing=True,
                generated=True,
            )

        with pytest.raises(PermissionError):
            record_meaningful_change(
                root,
                operation="agents.overwrite",
                target_type="key_pose",
                target_id="pose_a",
                snapshot={},
                summary="overwrite",
                overwrite_approved=True,
                generated=True,
            )

        with pytest.raises(PermissionError):
            record_meaningful_change(
                root,
                operation="agents.swap_asset",
                target_type="key_pose",
                target_id="pose_a",
                snapshot={},
                summary="swap",
                asset_substitution=True,
                source_references=[],
                generated=True,
            )


def test_provenance_survives_export_import_and_restoration():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        out = record_meaningful_change(
            root,
            operation="agents.plan",
            target_type="project",
            target_id="demo",
            snapshot={"shots": ["shot_1"], "note": "v1 plan"},
            summary="Initial plan",
            source_references=["audio:master.wav"],
            input_parameters={"prompt": "rain chrome"},
            generated_alternatives=[{"id": "plan_a"}],
            generated=True,
        )
        prov = out["provenance"]
        rev = out["revision"]

        prov = set_acceptance(root, prov.id, state="accepted", notes="Looks good")
        prov = record_human_edit_after_generation(
            root,
            prov.id,
            edit_summary="Tweaked shot order",
            fields_changed=["shots[0].index"],
        )
        prov = final_approve_provenance(root, prov.id, approved_by="director.lee")
        assert prov.final_approval is True
        assert prov.acceptance_state == ProvenanceAcceptance.ACCEPTED
        assert len(prov.human_edits_after_generation) >= 2

        viewed = inspect_provenance(root, prov.id)
        assert viewed["creator"]
        assert viewed["timestamp"]
        assert viewed["source_references"]
        assert viewed["model_or_assistant_operation"] == "agents.plan"
        assert viewed["input_parameters"]["prompt"] == "rain chrome"
        assert viewed["generated_alternatives"]
        assert viewed["accepted_rejected_state"] == "accepted"
        assert viewed["human_edits_after_generation"]
        assert viewed["final_approval"] is True
        assert viewed["visibly_labeled_generated"] is True

        bundle = export_provenance_bundle(root, revision_ids=[rev.id])
        # Import into a fresh project tree
        other = Path(td) / "other"
        for sub in ("provenance", "revisions", "provenance_exports"):
            (other / sub).mkdir(parents=True)
        imported = import_provenance_bundle(other, bundle)
        assert imported["ok"]
        assert imported["revisions"] == 1
        assert imported["provenance"] >= 1
        assert imported["labeled_generated"] >= 1

        restored_prov = ProvenanceRecord.model_validate_json(
            (other / "provenance" / f"{prov.id}.json").read_text(encoding="utf-8")
        )
        assert restored_prov.visibly_labeled_generated is True
        assert restored_prov.source_references == ["audio:master.wav"]
        assert restored_prov.final_approval is True
        assert restored_prov.input_parameters.get("prompt") == "rain chrome"

        # Restore prior revision on the original root
        result = restore_revision(root, rev.id, restored_by="animator.kim")
        assert result["ok"]
        assert result["snapshot"]["note"] == "v1 plan"
        assert (root / "revisions" / f"restored_{rev.id}.json").exists()
        restore_prov = result["provenance"]
        assert restore_prov.operation == "human.restore_revision"
        assert f"revision:{rev.id}" in restore_prov.source_references
