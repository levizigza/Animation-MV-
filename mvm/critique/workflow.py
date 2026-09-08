"""Structured craft review workflow — categories stay separate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mvm.project.domain_store import ensure_domain_dirs, save_provenance, save_revision
from mvm.schemas.compat import attribute_suggestion
from mvm.schemas.critique import (
    ALL_CRITIQUE_CATEGORIES,
    CraftReview,
    CritiqueCategory,
    CritiqueItem,
    CritiqueRevisionCompare,
    CritiqueSeverity,
    FrameOrTimeRef,
)
from mvm.schemas.domain import ActorKind, make_provenance, new_id, utc_now


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_critique_dirs(root: Path) -> None:
    ensure_domain_dirs(root)
    (root / "critiques").mkdir(parents=True, exist_ok=True)


def save_craft_review(root: Path, review: CraftReview) -> Path:
    ensure_critique_dirs(root)
    if review.has_aggregate_quality_score is not False or review.quality_score is not None:
        raise ValueError("Refusing CraftReview with aggregate quality score")
    path = root / "critiques" / f"{review.id}.json"
    _write(path, review)
    return path


def load_craft_review(root: Path, review_id: str) -> CraftReview:
    return CraftReview.model_validate(_read(root / "critiques" / f"{review_id}.json"))


def list_craft_reviews(
    root: Path,
    *,
    target_id: str | None = None,
    revision_id: str | None = None,
) -> list[CraftReview]:
    d = root / "critiques"
    if not d.exists():
        return []
    out: list[CraftReview] = []
    for p in d.glob("*.json"):
        if p.name.endswith("_compare.json"):
            continue
        data = _read(p)
        if "items" not in data or "reviewer" not in data:
            continue
        rev = CraftReview.model_validate(data)
        if target_id and rev.target_id != target_id:
            continue
        if revision_id and rev.revision_id != revision_id:
            continue
        out.append(rev)
    return sorted(out, key=lambda r: r.at)


def create_craft_review(
    root: Path,
    *,
    target_type: str,
    target_id: str,
    revision_id: str,
    reviewer: str,
    previous_revision_id: str | None = None,
    summary_notes: str = "",
) -> CraftReview:
    ensure_critique_dirs(root)
    if not reviewer.strip():
        raise ValueError("reviewer identity is required")
    review = CraftReview(
        id=new_id("crev"),
        target_type=target_type,  # type: ignore[arg-type]
        target_id=target_id,
        revision_id=revision_id,
        previous_revision_id=previous_revision_id,
        reviewer=reviewer.strip(),
        summary_notes=summary_notes,
        revision_status="open",
        has_aggregate_quality_score=False,
        quality_score=None,
    )
    rev, prov = attribute_suggestion(
        operation="human.craft_review_create",
        target_type="shot" if target_type == "shot" else "project",
        target_id=target_id,
        snapshot=review.model_dump(mode="json"),
        summary=f"Opened craft review {review.id} by {reviewer} on rev {revision_id}",
        outputs={
            "review_id": review.id,
            "has_aggregate_quality_score": False,
            "categories_supported": [c.value for c in ALL_CRITIQUE_CATEGORIES],
        },
    )
    review.provenance_id = prov.id
    save_craft_review(root, review)
    save_revision(root, rev)
    save_provenance(root, prov)
    return review


def add_critique(
    root: Path,
    review_id: str,
    *,
    category: CritiqueCategory | str,
    notes: str,
    severity: CritiqueSeverity | str = CritiqueSeverity.NOTE,
    frame: int | None = None,
    end_frame: int | None = None,
    time_sec: float | None = None,
    end_time_sec: float | None = None,
    range_label: str = "",
) -> CraftReview:
    review = load_craft_review(root, review_id)
    cat = (
        category
        if isinstance(category, CritiqueCategory)
        else CritiqueCategory(str(category))
    )
    sev = (
        severity
        if isinstance(severity, CritiqueSeverity)
        else CritiqueSeverity(str(severity))
    )
    if not notes.strip():
        raise ValueError("Critique notes are required")

    range_ref = None
    if any(x is not None for x in (frame, end_frame, time_sec, end_time_sec)) or range_label:
        range_ref = FrameOrTimeRef(
            frame=frame,
            end_frame=end_frame,
            time_sec=time_sec,
            end_time_sec=end_time_sec,
            label=range_label,
        )

    item = CritiqueItem(
        category=cat,
        notes=notes.strip(),
        severity=sev,
        range=range_ref,
        resolved=False,
    )
    review = review.model_copy(deep=True)
    review.items = list(review.items) + [item]
    review.revision_status = "needs_revisions" if sev in (
        CritiqueSeverity.MAJOR,
        CritiqueSeverity.BLOCKER,
    ) else ("in_progress" if review.revision_status == "open" else review.revision_status)

    prov = make_provenance(
        operation="human.craft_review_add_critique",
        revision_id=review.revision_id,
        actor=ActorKind.HUMAN,
        summary=f"{cat.value}/{sev.value}: {notes[:120]}",
        inputs={"review_id": review.id, "category": cat.value},
        outputs={
            "item_id": item.id,
            "resolved": False,
            "has_aggregate_quality_score": False,
        },
    )
    review.provenance_id = prov.id
    save_craft_review(root, review)
    save_provenance(root, prov)
    return review


def resolve_critique(
    root: Path,
    review_id: str,
    item_id: str,
    *,
    resolution_notes: str = "",
    resolved: bool = True,
) -> CraftReview:
    review = load_craft_review(root, review_id).model_copy(deep=True)
    found = False
    for item in review.items:
        if item.id == item_id:
            item.resolved = resolved
            item.resolution_notes = resolution_notes
            item.resolved_at = utc_now() if resolved else None
            found = True
            break
    if not found:
        raise KeyError(f"Critique item {item_id} not found in review {review_id}")

    if review.items and all(i.resolved for i in review.items):
        review.revision_status = "resolved"
    elif any(not i.resolved for i in review.items):
        if review.revision_status == "resolved":
            review.revision_status = "needs_revisions"

    prov = make_provenance(
        operation="human.craft_review_resolve_item",
        revision_id=review.revision_id,
        actor=ActorKind.HUMAN,
        summary=f"{'Resolved' if resolved else 'Reopened'} {item_id}",
        outputs={"item_id": item_id, "resolved": resolved},
    )
    save_craft_review(root, review)
    save_provenance(root, prov)
    return review


def set_revision_status(
    root: Path,
    review_id: str,
    status: str,
) -> CraftReview:
    review = load_craft_review(root, review_id).model_copy(deep=True)
    allowed = {"open", "in_progress", "needs_revisions", "resolved", "closed"}
    if status not in allowed:
        raise ValueError(f"revision_status must be one of {sorted(allowed)}")
    review.revision_status = status  # type: ignore[assignment]
    save_craft_review(root, review)
    return review


def _item_fingerprint(item: CritiqueItem) -> str:
    rng = item.range.model_dump(mode="json") if item.range else {}
    return f"{item.category.value}|{item.severity.value}|{item.notes}|{rng}"


def compare_craft_reviews(
    root: Path,
    current_review_id: str,
    previous_review_id: str | None = None,
) -> CritiqueRevisionCompare:
    """Compare current review vs previous (or vs linked previous_revision review)."""
    current = load_craft_review(root, current_review_id)
    previous: CraftReview | None = None
    if previous_review_id:
        previous = load_craft_review(root, previous_review_id)
    elif current.previous_revision_id:
        candidates = list_craft_reviews(
            root, revision_id=current.previous_revision_id
        )
        previous = candidates[-1] if candidates else None

    cur_unres = current.unresolved_by_category()
    prev_unres = previous.unresolved_by_category() if previous else {c.value: 0 for c in CritiqueCategory}
    delta = {
        k: cur_unres.get(k, 0) - prev_unres.get(k, 0) for k in cur_unres
    }
    improved = [k for k, v in delta.items() if v < 0]
    regressed = [k for k, v in delta.items() if v > 0]

    prev_fps = {_item_fingerprint(i): i for i in (previous.items if previous else [])}
    cur_fps = {_item_fingerprint(i): i for i in current.items}

    resolved_since = []
    if previous:
        for fp, prev_item in prev_fps.items():
            if not prev_item.resolved:
                # same note now resolved, or gone
                match = next(
                    (
                        i
                        for i in current.items
                        if i.category == prev_item.category
                        and i.notes == prev_item.notes
                    ),
                    None,
                )
                if match and match.resolved:
                    resolved_since.append(match.model_dump(mode="json"))
                elif fp not in cur_fps and match is None:
                    # treated as addressed by removal — still list as resolved context
                    resolved_since.append(
                        {
                            **prev_item.model_dump(mode="json"),
                            "resolved": True,
                            "resolution_notes": "absent from current review",
                        }
                    )

    still = [i.model_dump(mode="json") for i in current.items if not i.resolved]
    new_items = []
    if previous:
        prev_notes = {(i.category, i.notes) for i in previous.items}
        for i in current.items:
            if (i.category, i.notes) not in prev_notes:
                new_items.append(i.model_dump(mode="json"))
    else:
        new_items = [i.model_dump(mode="json") for i in current.items]

    summary = (
        f"Compare review {current.id} (rev {current.revision_id}) vs "
        f"{previous.id if previous else 'none'} "
        f"(rev {previous.revision_id if previous else current.previous_revision_id}). "
        f"Improved categories: {improved or 'none'}. "
        f"Regressed: {regressed or 'none'}. "
        f"Unresolved items now: {len(still)}. "
        f"No aggregate quality score."
    )
    compare = CritiqueRevisionCompare(
        current_review_id=current.id,
        previous_review_id=previous.id if previous else previous_review_id,
        current_revision_id=current.revision_id,
        previous_revision_id=(
            previous.revision_id if previous else current.previous_revision_id
        ),
        unresolved_by_category_current=cur_unres,
        unresolved_by_category_previous=prev_unres,
        unresolved_delta_by_category=delta,
        severity_current=current.severity_counts(),
        severity_previous=previous.severity_counts() if previous else {},
        resolved_since_previous=resolved_since,
        still_unresolved=still,
        new_items_in_current=new_items,
        categories_improved=improved,
        categories_regressed=regressed,
        summary=summary,
        has_aggregate_quality_score=False,
    )
    _write(root / "critiques" / f"compare_{current.id}.json", compare)
    return compare


def category_breakdown(root: Path, review_id: str) -> dict[str, Any]:
    """Explicit per-category view — refuses to emit a single score."""
    review = load_craft_review(root, review_id)
    by_cat: dict[str, list[dict[str, Any]]] = {c.value: [] for c in CritiqueCategory}
    for item in review.items:
        by_cat[item.category.value].append(item.model_dump(mode="json"))
    return {
        "review_id": review.id,
        "reviewer": review.reviewer,
        "revision_id": review.revision_id,
        "revision_status": review.revision_status,
        "by_category": by_cat,
        "unresolved_by_category": review.unresolved_by_category(),
        "severity_counts": review.severity_counts(),
        "has_aggregate_quality_score": False,
        "quality_score": None,
        "summary_notes": review.summary_notes,
    }
