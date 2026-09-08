"""Structured craft reviews: categories, resolve state, revision comparison."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mvm.critique import (
    ALL_CRITIQUE_CATEGORIES,
    CraftReview,
    CritiqueCategory,
    add_critique,
    category_breakdown,
    compare_craft_reviews,
    create_craft_review,
    resolve_critique,
)
from mvm.schemas.critique import CritiqueSeverity


def _root(td: str) -> Path:
    root = Path(td) / "proj"
    for sub in ("critiques", "revisions", "provenance"):
        (root / sub).mkdir(parents=True)
    return root


def test_all_categories_supported_without_aggregate_score():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        review = create_craft_review(
            root,
            target_type="shot",
            target_id="shot_1",
            revision_id="rev_current",
            reviewer="director.lee",
            previous_revision_id="rev_prev",
            summary_notes="Pass focusing on readability",
        )
        assert review.has_aggregate_quality_score is False
        assert review.quality_score is None
        assert review.reviewer == "director.lee"
        assert review.revision_status == "open"

        assert len(ALL_CRITIQUE_CATEGORIES) == 12
        for cat in ALL_CRITIQUE_CATEGORIES:
            review = add_critique(
                root,
                review.id,
                category=cat,
                notes=f"Note on {cat.value}",
                severity="minor",
                frame=12,
                end_frame=18,
            )
        assert len(review.items) == 12
        cats = {i.category for i in review.items}
        assert cats == set(ALL_CRITIQUE_CATEGORIES)

        breakdown = category_breakdown(root, review.id)
        assert breakdown["has_aggregate_quality_score"] is False
        assert breakdown["quality_score"] is None
        for cat in CritiqueCategory:
            assert len(breakdown["by_category"][cat.value]) == 1

        with pytest.raises(Exception):
            data = review.model_dump(mode="json")
            data["has_aggregate_quality_score"] = True
            CraftReview.model_validate(data)

        with pytest.raises(Exception):
            data = review.model_dump(mode="json")
            data["quality_score"] = 87
            CraftReview.model_validate(data)


def test_resolve_unresolved_and_revision_status():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        review = create_craft_review(
            root,
            target_type="shot",
            target_id="shot_1",
            revision_id="rev_a",
            reviewer="animator.kim",
        )
        review = add_critique(
            root,
            review.id,
            category="timing",
            notes="Hold too short on lyric",
            severity=CritiqueSeverity.MAJOR,
            time_sec=1.2,
            end_time_sec=1.8,
        )
        item_id = review.items[0].id
        assert review.items[0].resolved is False
        assert review.revision_status == "needs_revisions"

        review = resolve_critique(
            root, review.id, item_id, resolution_notes="Extended hold to 6f"
        )
        assert review.items[0].resolved is True
        assert review.revision_status == "resolved"

        review = resolve_critique(root, review.id, item_id, resolved=False)
        assert review.items[0].resolved is False
        assert review.revision_status == "needs_revisions"


def test_compare_current_versus_previous_revision_reviews():
    with tempfile.TemporaryDirectory() as td:
        root = _root(td)
        prev = create_craft_review(
            root,
            target_type="shot",
            target_id="shot_1",
            revision_id="rev_v1",
            reviewer="director.lee",
        )
        prev = add_critique(
            root,
            prev.id,
            category="silhouette_readability",
            notes="Arm merges with torso",
            severity="major",
            frame=8,
        )
        prev = add_critique(
            root,
            prev.id,
            category="acting",
            notes="Glance feels unmotivated",
            severity="minor",
            frame=20,
        )
        # Mark silhouette fixed on previous record for compare baseline
        prev = resolve_critique(
            root, prev.id, prev.items[0].id, resolution_notes="Fixed in v2 drawing"
        )

        cur = create_craft_review(
            root,
            target_type="shot",
            target_id="shot_1",
            revision_id="rev_v2",
            reviewer="director.lee",
            previous_revision_id="rev_v1",
        )
        # Silhouette addressed; acting still open; new timing note
        cur = add_critique(
            root,
            cur.id,
            category="acting",
            notes="Glance feels unmotivated",
            severity="minor",
            frame=20,
        )
        cur = add_critique(
            root,
            cur.id,
            category="timing",
            notes="Settle arrives late vs kick",
            severity="blocker",
            frame=30,
            end_frame=36,
        )

        diff = compare_craft_reviews(root, cur.id, prev.id)
        assert diff.has_aggregate_quality_score is False
        assert diff.current_revision_id == "rev_v2"
        assert diff.previous_revision_id == "rev_v1"
        assert "timing" in diff.categories_regressed or diff.unresolved_delta_by_category.get("timing", 0) > 0
        assert diff.unresolved_by_category_current["acting"] == 1
        assert diff.unresolved_by_category_current["timing"] == 1
        assert any(i["category"] == "timing" for i in diff.new_items_in_current)
        assert "aggregate" in diff.summary.lower() or "No aggregate" in diff.summary
        # Still category maps — not one score
        assert isinstance(diff.unresolved_by_category_current, dict)
        assert len(diff.unresolved_by_category_current) == 12
