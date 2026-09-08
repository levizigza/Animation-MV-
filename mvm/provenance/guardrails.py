"""Craft provenance guardrails — refuse hidden/destructive/untraceable changes."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


# Personal living-artist names must not be used as style controls.
# Studio/work titles (e.g. pack ids) are separate; this blocks person-as-prompt controls.
LIVING_ARTIST_STYLE_DENYLIST = frozenset(
    {
        "miyazaki",
        "hayao miyazaki",
        "wes anderson",
        "greta gerwig",
        "quentin tarantino",
        "christopher nolan",
        "hayao",
        "oshii",
        "mamoru oshii",
        "kon",
        "satoshi kon",
        "yuasa",
        "masaaki yuasa",
        "anno",
        "hideaki anno",
    }
)


class GuardrailViolation(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class GuardrailReport(BaseModel):
    ok: bool
    violations: list[GuardrailViolation] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def uses_living_artist_as_style_control(value: str | None) -> bool:
    if not value:
        return False
    n = _norm(value)
    if n in LIVING_ARTIST_STYLE_DENYLIST:
        return True
    # Also catch "in the style of <name>"
    for name in LIVING_ARTIST_STYLE_DENYLIST:
        if name in n and ("style" in n or "like" in n or n == name):
            return True
    return False


def evaluate_guardrails(
    *,
    hidden_full_shot_replacement: bool = False,
    silent_smoothing: bool = False,
    overwrite_approved: bool = False,
    asset_substitution: bool = False,
    asset_source_references: list[str] | None = None,
    style_control: str | None = None,
    generated: bool = False,
    visibly_labeled_generated: bool = False,
) -> GuardrailReport:
    """Return pass/fail for provenance-enforced craft guardrails."""
    violations: list[GuardrailViolation] = []
    checks = {
        "no_hidden_full_shot_replacement": not hidden_full_shot_replacement,
        "no_silent_smoothing": not silent_smoothing,
        "no_overwrite_approved": not overwrite_approved,
        "no_untraceable_asset_substitution": True,
        "no_living_artist_style_controls": True,
        "generated_visibly_labeled": True,
    }

    if hidden_full_shot_replacement:
        violations.append(
            GuardrailViolation(
                code="hidden_full_shot_replacement",
                message="Hidden full-shot replacement is forbidden — surface the change for approval.",
            )
        )
    if silent_smoothing:
        violations.append(
            GuardrailViolation(
                code="silent_smoothing",
                message="Silent smoothing is forbidden — timing/spacing must stay explicit.",
            )
        )
    if overwrite_approved:
        violations.append(
            GuardrailViolation(
                code="overwrite_approved",
                message="Overwriting approved work is forbidden — restore/revise via Revision.",
            )
        )
    if asset_substitution:
        refs = [r for r in (asset_source_references or []) if str(r).strip()]
        if not refs:
            checks["no_untraceable_asset_substitution"] = False
            violations.append(
                GuardrailViolation(
                    code="untraceable_asset_substitution",
                    message=(
                        "Asset substitution requires source_references "
                        "(path/URI/notebook media id) — untraceable swaps are forbidden."
                    ),
                )
            )
    if uses_living_artist_as_style_control(style_control):
        checks["no_living_artist_style_controls"] = False
        violations.append(
            GuardrailViolation(
                code="living_artist_style_control",
                message=(
                    f"Refusing living artist name as a style control: {style_control!r}. "
                    "Use pack ids / craft metadata instead."
                ),
                details={"style_control": style_control},
            )
        )
    if generated and not visibly_labeled_generated:
        checks["generated_visibly_labeled"] = False
        violations.append(
            GuardrailViolation(
                code="unlabeled_generated",
                message="Generated suggestions must be visibly labeled.",
            )
        )

    return GuardrailReport(ok=len(violations) == 0, violations=violations, checks=checks)


def assert_guardrails(report: GuardrailReport) -> None:
    if report.ok:
        return
    msgs = "; ".join(v.message for v in report.violations)
    raise PermissionError(f"Provenance guardrail blocked change: {msgs}")
