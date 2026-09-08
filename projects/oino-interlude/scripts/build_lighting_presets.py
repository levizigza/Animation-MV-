"""Build Oino lighting presets from the film palette.

Creates preset docs for ATTIC_DUST … TITLE_CARD_BLACK.
Dionysian colour is a living interruption — not every shot red.

Usage:
  python scripts/build_lighting_presets.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, REPORTS_DIR  # noqa: E402

PRESETS_JSON = DOCS_DIR / "lighting_presets.json"
STATUS_MD = DOCS_DIR / "lighting_presets.md"
MARKERS_JSON = DOCS_DIR / "lighting_preset_markers.json"

REQUIRED_PRESETS = (
    "ATTIC_DUST",
    "OINO_ARCHIVE",
    "STEAM_SOOT",
    "ELECTRIC_WARMTH",
    "DIGITAL_COLD",
    "DIONYSUS_AMBER_RED",
    "ZONE_REFLECTION",
    "TABLE_WARMTH",
    "OPEN_DOOR_DAWN",
    "TITLE_CARD_BLACK",
)

REQUIRED_FAMILIES = (
    "attic",
    "steam",
    "electricity",
    "digital",
    "dionysus",
    "table",
    "title_card",
)


def load() -> dict[str, Any]:
    if not PRESETS_JSON.is_file():
        raise FileNotFoundError(f"Missing {PRESETS_JSON}")
    return json.loads(PRESETS_JSON.read_text(encoding="utf-8"))


def _resolve_color(
    families: dict[str, Any], family: str, key: str
) -> dict[str, Any] | None:
    fam = families.get(family) or {}
    return fam.get(key)


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    if policy.get("dionysian_every_shot_red") is not False:
        errors.append("policy.dionysian_every_shot_red must be false")
    role = (policy.get("dionysian_role") or "").lower()
    if "interruption" not in role:
        errors.append("policy.dionysian_role must describe living interruption")

    families = data.get("palette_families") or {}
    for fam in REQUIRED_FAMILIES:
        if fam not in families:
            errors.append(f"Missing palette family: {fam}")
        else:
            for name, swatch in (families.get(fam) or {}).items():
                if not swatch.get("hex") or not swatch.get("rgba"):
                    errors.append(f"{fam}.{name}: hex and rgba required")

    presets = data.get("presets") or []
    ids = [p.get("id") for p in presets]
    if len(ids) != len(set(ids)):
        errors.append("preset ids must be unique")
    for req in REQUIRED_PRESETS:
        if req not in ids:
            errors.append(f"Missing preset: {req}")
    if len(presets) != len(REQUIRED_PRESETS):
        errors.append(
            f"Expected exactly {len(REQUIRED_PRESETS)} presets, found {len(presets)}"
        )

    for p in presets:
        pid = p.get("id", "?")
        fam = p.get("palette_family")
        if fam not in families:
            errors.append(f"{pid}: unknown palette_family {fam}")
        for lamp in ("key", "fill", "rim"):
            block = p.get(lamp) or {}
            if "energy" not in block:
                errors.append(f"{pid}.{lamp}: energy required")
            ck = block.get("color_key")
            if ck and fam and not _resolve_color(families, fam, ck):
                # TITLE_CARD may use near_black; secondary palette keys need check
                sec = p.get("secondary_palette")
                ok = False
                if sec and _resolve_color(families, sec, ck):
                    ok = True
                # cold_surround uses color_key_from
                if not ok and lamp == "key":
                    pass
                if not ok and not _resolve_color(families, fam or "", ck):
                    # allow color from secondary or same family only
                    if sec and _resolve_color(families, sec, ck):
                        ok = True
                    if not ok:
                        errors.append(f"{pid}.{lamp}: color_key '{ck}' not in {fam}")
        if not p.get("must_not"):
            errors.append(f"{pid}: must_not required")

    dion = next((p for p in presets if p.get("id") == "DIONYSUS_AMBER_RED"), None)
    if dion:
        must_not = " ".join(dion.get("must_not") or []).lower()
        if "every shot red" not in must_not and "every shot" not in must_not:
            errors.append("DIONYSUS_AMBER_RED must forbid every-shot-red")

    title = next((p for p in presets if p.get("id") == "TITLE_CARD_BLACK"), None)
    if title:
        if title.get("palette_family") != "title_card":
            errors.append("TITLE_CARD_BLACK must use title_card palette")
        if not title.get("type_color_key"):
            errors.append("TITLE_CARD_BLACK needs type_color_key")

    return errors


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = []
    for p in data.get("presets") or []:
        markers.append(
            {
                "name": f"LIGHT_{p['id']}",
                "preset": p["id"],
                "palette_family": p.get("palette_family"),
                "approx_shots": p.get("approx_shots") or [],
                "note": p.get("note") or p.get("volume_hint"),
            }
        )
    out = {
        "schema_version": 1,
        "system_id": data.get("system_id"),
        "editable": True,
        "dionysian_every_shot_red": False,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/lighting_preset_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    families = data["palette_families"]
    lines = [
        "# Lighting presets — Oino (Interlude)",
        "",
        f"**System:** `{data.get('system_id')}`  ",
        f"**Dionysian role:** {policy.get('dionysian_role')}  ",
        f"**Every shot red:** `{policy.get('dionysian_every_shot_red')}`",
        "",
        "## Palette families",
        "",
    ]
    for fam, swatches in families.items():
        lines.append(f"### {fam}")
        lines.append("")
        lines.append("| Swatch | Hex |")
        lines.append("|--------|-----|")
        for name, sw in swatches.items():
            lines.append(f"| {name.replace('_', ' ')} | `{sw.get('hex')}` |")
        lines.append("")

    lines += [
        "## Presets",
        "",
        "| Id | Family | Key energy | Motif links |",
        "|----|--------|------------|-------------|",
    ]
    for p in data.get("presets") or []:
        key_e = (p.get("key") or {}).get("energy")
        links = ", ".join(f"`{m}`" for m in (p.get("motif_links") or [])[:3]) or "—"
        lines.append(
            f"| `{p['id']}` | {p.get('palette_family')} | {key_e} | {links} |"
        )

    lines += ["", "## Preset detail", ""]
    for p in data.get("presets") or []:
        lines += [
            f"### `{p['id']}`",
            "",
            f"- **Family:** {p.get('palette_family')}",
            f"- **World:** strength {p.get('world_strength')} / "
            f"color `{p.get('world_color_key')}`",
            f"- **Key / fill / rim:** "
            f"{(p.get('key') or {}).get('energy')} / "
            f"{(p.get('fill') or {}).get('energy')} / "
            f"{(p.get('rim') or {}).get('energy')}",
            f"- **Volume:** {p.get('volume_hint')}",
            f"- **Shots:** "
            + ", ".join(f"`{s}`" for s in (p.get("approx_shots") or [])),
            f"- **Must not:** " + "; ".join(p.get("must_not") or []),
        ]
        if p.get("note"):
            lines.append(f"- **Note:** {p['note']}")
        if p.get("usage"):
            lines.append(f"- **Usage:** {p['usage']}")
        lines.append("")

    lines += [
        "## Rebuild",
        "",
        "```text",
        "python scripts/build_lighting_presets.py",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/lighting_presets.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Oino lighting presets")
    parser.parse_args()

    report = RunReport(script="build_lighting_presets", seed=20261213)
    try:
        data = load()
        report.mark("reused", "docs/lighting_presets.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("brief", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    write_markers(data, report)
    write_status(data, report)
    report.note(
        "10 lighting presets; Dionysian amber/red is interruption only — not every shot red"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} presets={len(data['presets'])} "
        f"families={len(data['palette_families'])}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
