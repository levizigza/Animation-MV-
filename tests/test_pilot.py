"""Short-sequence craft pilot: full path, measurements, P0/P1/P2 report."""

from __future__ import annotations

import tempfile
from pathlib import Path

from mvm.pilot import run_short_sequence_pilot, write_report_files
from mvm.pilot.models import FindingPriority, PilotReport
from mvm.schemas.models import ShotLifecycleState


def test_pilot_completes_all_stages_and_writes_prioritized_report():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "pilot_proj"
        report = run_short_sequence_pilot(root)

        assert report.features_added_during_pilot is False
        assert report.has_aggregate_quality_score is False
        assert report.quality_score is None
        assert report.stages_completed == [
            "intent",
            "storyboard",
            "layout",
            "animatic",
            "key_poses",
            "timing",
            "in_betweens",
            "sound",
            "review",
            "revision",
            "approval",
        ]
        assert report.final_lifecycle_state == ShotLifecycleState.APPROVED.value
        assert report.intent_still_communicated is True
        assert report.original_intent in report.final_intent

        accepted = [s for s in report.suggestion_outcomes if s.decision == "accepted"]
        rejected = [s for s in report.suggestion_outcomes if s.decision == "rejected"]
        assert accepted, "pilot should accept at least one suggestion"
        assert rejected, "pilot should reject at least one suggestion"

        by = report.findings_by_priority()
        assert by["P0"], "expected P0 findings from demonstrated friction"
        assert all(f.feature_added is False for f in report.findings)

        paths = write_report_files(root, report)
        assert paths["json"].exists()
        assert paths["md"].exists()
        md = paths["md"].read_text(encoding="utf-8")
        assert "## Findings by priority" in md
        assert "### P0" in md

        shot = (root / "shots" / f"{report.focus_shot_id}.json").read_text(
            encoding="utf-8"
        )
        assert "approved" in shot
        assert (root / "sequences" / f"{report.sequence_id}.json").exists()

        data = report.model_dump(mode="json")
        data["quality_score"] = 91
        try:
            PilotReport.model_validate(data)
            raise AssertionError("should reject quality_score")
        except Exception:
            pass


def test_pilot_measurements_cover_required_axes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "pilot_proj"
        report = run_short_sequence_pilot(root)
        m = report.measurements
        assert "confusion_signals" in m
        assert "assumptions_noted" in m
        assert "suggestions_accepted" in m
        assert "suggestions_rejected" in m
        assert m["revision_count"] >= 1
        assert m["provenance_count"] >= 1
        axes = {f.axis.value for f in report.findings}
        assert "user_confusion" in axes
        assert "unjustified_assumption" in axes
        assert "intent_communication" in axes
        assert any(f.priority == FindingPriority.P0 for f in report.findings)
