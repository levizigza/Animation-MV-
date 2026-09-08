"""Build the Oino motif system tracker.

Reads ``docs/motif_system.json``, validates first→transformation→final arcs,
flags symbols without later transformation, writes ``docs/motif_tracking.md``.

Policy: do not add new symbols until this system is readable.

Usage:
  python scripts/build_motif_system.py
  python scripts/build_motif_system.py --check-links
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

SYSTEM_JSON = DOCS_DIR / "motif_system.json"
TRACKING_MD = DOCS_DIR / "motif_tracking.md"
MARKERS_JSON = DOCS_DIR / "motif_system_markers.json"

REQUIRED_MOTIF_IDS = (
    "MOTIF_RECORDING",
    "MOTIF_HAND",
    "MOTIF_DOORWAY",
    "MOTIF_BOWL_TABLE",
    "MOTIF_VINE_WATER",
    "MOTIF_MASK_THEATRE",
    "MOTIF_MELODY_CALL",
)

REQUIRED_ROLES = ("first_appearance", "transformation", "final_meaning")

REQUIRED_MEANINGS: dict[str, tuple[str, ...]] = {
    "MOTIF_RECORDING": (
        "protected fragment",
        "ancestral evidence",
        "substitute for presence",
        "memory shared with the living",
    ),
    "MOTIF_HAND": (
        "closes the attic door",
        "touches the archive",
        "helps or fails to help",
        "rewinds and grips the control",
        "releases the control",
        "accepts the bowl",
        "follows the sister's rhythm",
    ),
    "MOTIF_DOORWAY": (
        "excludes the sister",
        "becomes a factory gate",
        "becomes the Zone threshold",
        "becomes the route home",
        "remains open at the end",
    ),
    "MOTIF_BOWL_TABLE": (
        "waiting",
        "nourishment",
        "Oino's absence",
        "reflected consequence",
        "shared participation",
    ),
    "MOTIF_VINE_WATER": (
        "inherited Oino lineage",
        "life growing through machines",
        "transformation",
        "nourishment",
        "release from rigid structures",
    ),
    "MOTIF_MASK_THEATRE": (
        "people performing futures",
        "artificial versions of the self",
        "Dionysian presence",
        "the father as a person rather than a perfect performance",
    ),
    "MOTIF_MELODY_CALL": (
        "invitation refused",
        "archive opened",
        "industrial rhythm",
        "memorial loop",
        "interruption",
        "living variation",
    ),
}


def load_system() -> dict[str, Any]:
    if not SYSTEM_JSON.is_file():
        raise FileNotFoundError(f"Missing {SYSTEM_JSON}")
    return json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))


def find_untransformed(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flag stages/symbols that appear without a later transformation path."""
    flags: list[dict[str, Any]] = []
    for item in data.get("explicit_untransformed") or []:
        flags.append(
            {
                "kind": "explicit",
                "motif_id": item.get("motif_id"),
                "stage_id": item.get("stage_id") or item.get("id"),
                "meaning": item.get("meaning") or item.get("symbol"),
                "note": item.get("note")
                or "Listed in explicit_untransformed — appears without later transformation.",
            }
        )

    for motif in data.get("motifs") or []:
        mid = motif.get("id", "?")
        stages = motif.get("stages") or []
        roles = [s.get("role") for s in stages]
        has_transform = "transformation" in roles
        has_final = "final_meaning" in roles
        for s in stages:
            sid = s.get("id", "?")
            role = s.get("role")
            if role == "first_appearance" and not has_transform and not has_final:
                flags.append(
                    {
                        "kind": "orphan_first",
                        "motif_id": mid,
                        "stage_id": sid,
                        "meaning": s.get("meaning"),
                        "note": "First appearance with no transformation or final meaning.",
                    }
                )
            if role == "transformation" and not has_final:
                flags.append(
                    {
                        "kind": "transform_without_final",
                        "motif_id": mid,
                        "stage_id": sid,
                        "meaning": s.get("meaning"),
                        "note": "Transformation present but motif lacks final_meaning.",
                    }
                )
            if s.get("no_later_transform") is True:
                flags.append(
                    {
                        "kind": "marked_no_later",
                        "motif_id": mid,
                        "stage_id": sid,
                        "meaning": s.get("meaning"),
                        "note": "Stage marked no_later_transform=true.",
                    }
                )
    return flags


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    if policy.get("allow_new_symbols") is not False:
        errors.append("policy.allow_new_symbols must be false until system is readable")
    if policy.get("flag_untransformed") is not True:
        errors.append("policy.flag_untransformed must be true")
    required = policy.get("require_each_motif") or []
    for role in REQUIRED_ROLES:
        if role not in required:
            errors.append(f"policy.require_each_motif must include {role}")

    motifs = data.get("motifs") or []
    ids = [m.get("id") for m in motifs]
    if len(ids) != len(set(ids)):
        errors.append("motif ids must be unique")
    for req in REQUIRED_MOTIF_IDS:
        if req not in ids:
            errors.append(f"Missing motif: {req}")
    if len(motifs) != len(REQUIRED_MOTIF_IDS):
        errors.append(
            f"Expected exactly {len(REQUIRED_MOTIF_IDS)} locked motifs "
            f"(no new symbols); found {len(motifs)}"
        )

    for motif in motifs:
        mid = motif.get("id", "?")
        name = motif.get("name") or ""
        if not name.strip():
            errors.append(f"{mid}: name required")
        stages = motif.get("stages") or []
        if not stages:
            errors.append(f"{mid}: stages required")
        sids = [s.get("id") for s in stages]
        if len(sids) != len(set(sids)):
            errors.append(f"{mid}: stage ids must be unique")
        roles = [s.get("role") for s in stages]
        for role in REQUIRED_ROLES:
            if role not in roles:
                errors.append(f"{mid}: missing role {role}")
        if roles.count("final_meaning") != 1:
            errors.append(f"{mid}: exactly one final_meaning required")
        if roles.count("first_appearance") != 1:
            errors.append(f"{mid}: exactly one first_appearance required")

        meanings = [(s.get("meaning") or "").strip() for s in stages]
        expected = REQUIRED_MEANINGS.get(mid) or ()
        for exp in expected:
            if exp not in meanings:
                errors.append(f"{mid}: missing meaning '{exp}'")
        if expected and len(meanings) != len(expected):
            errors.append(
                f"{mid}: expected {len(expected)} stages matching locked meanings, "
                f"found {len(meanings)}"
            )

        for s in stages:
            sid = s.get("id", "?")
            if s.get("role") not in REQUIRED_ROLES:
                errors.append(f"{sid}: role must be one of {REQUIRED_ROLES}")
            for key in ("meaning", "marker", "staging"):
                if not (s.get(key) or "").strip():
                    errors.append(f"{sid}: {key} required")

    # New-symbol gate: only locked motif ids allowed
    for mid in ids:
        if mid not in REQUIRED_MOTIF_IDS:
            errors.append(
                f"New motif '{mid}' blocked — allow_new_symbols is false "
                "until system is readable"
            )

    return errors


def check_links(data: dict[str, Any], report: RunReport) -> None:
    call = DOCS_DIR / "call_to_dinner_motif.json"
    if call.is_file():
        motif = json.loads(call.read_text(encoding="utf-8"))
        call_ids = {a.get("id") for a in (motif.get("appearances") or [])}
        needed = {
            "CALL_01_SISTER_DOWNSTAIRS",
            "CALL_06_TABLE_TAP_NEW_MELODY",
            "CALL_05_ZONE_KNOCK",
        }
        missing = sorted(needed - call_ids)
        if missing:
            report.fail("link", f"call motif missing {missing}")
        else:
            report.note("call-to-dinner motif links ok")
    else:
        report.note("call_to_dinner_motif.json missing")

    for name in (
        "final_meal_animation.json",
        "holy_fool_turning.json",
        "knock_animation.json",
        "table_performance_block.json",
    ):
        path = DOCS_DIR / name
        if path.is_file():
            report.note(f"craft brief present: {name}")
        else:
            report.note(f"craft brief missing (non-fatal): {name}")


def write_markers(data: dict[str, Any], flags: list[dict[str, Any]], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = []
    for motif in data.get("motifs") or []:
        for s in motif.get("stages") or []:
            markers.append(
                {
                    "name": s["marker"],
                    "motif_id": motif["id"],
                    "motif_name": motif["name"],
                    "stage_id": s["id"],
                    "role": s["role"],
                    "meaning": s["meaning"],
                    "approx_shot": s.get("approx_shot"),
                    "note": s.get("staging"),
                    "links": s.get("links") or [],
                }
            )
    out = {
        "schema_version": 1,
        "system_id": data.get("system_id"),
        "editable": True,
        "allow_new_symbols": False,
        "untransformed_flags": flags,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/motif_system_markers.json")
    return MARKERS_JSON


def write_tracking_md(
    data: dict[str, Any], flags: list[dict[str, Any]], report: RunReport
) -> Path:
    policy = data["policy"]
    readability = data.get("readability") or {}
    lines = [
        "# Motif tracking — Oino (Interlude)",
        "",
        f"**System:** `{data.get('system_id')}`  ",
        f"**Film:** {data.get('film')}  ",
        f"**Allow new symbols:** `{policy.get('allow_new_symbols')}`  ",
        f"**Readability:** {readability.get('status')} — {readability.get('gate')}",
        "",
        "## Policy",
        "",
        f"- {policy.get('note')}",
        f"- Required arc per motif: "
        + ", ".join(f"`{r}`" for r in (policy.get("require_each_motif") or [])),
        "- **Do not add new symbols until this system is readable.**",
        "",
        "## Untransformed flags",
        "",
    ]
    if not flags:
        lines += [
            "None. Every locked motif has first appearance, transformation(s), "
            "and final meaning.",
            "",
        ]
    else:
        lines += [
            "| Kind | Motif | Stage | Meaning | Note |",
            "|------|-------|-------|---------|------|",
        ]
        for f in flags:
            lines.append(
                f"| `{f.get('kind')}` | `{f.get('motif_id')}` | "
                f"`{f.get('stage_id')}` | {f.get('meaning')} | {f.get('note')} |"
            )
        lines.append("")

    lines += [
        "## Motifs (summary)",
        "",
        "| Motif | First | Transformations | Final |",
        "|-------|-------|-----------------|-------|",
    ]
    for motif in data.get("motifs") or []:
        stages = motif.get("stages") or []
        first = next(
            (s["meaning"] for s in stages if s.get("role") == "first_appearance"),
            "—",
        )
        transforms = [
            s["meaning"] for s in stages if s.get("role") == "transformation"
        ]
        final = next(
            (s["meaning"] for s in stages if s.get("role") == "final_meaning"),
            "—",
        )
        lines.append(
            f"| **{motif['name']}** | {first} | "
            + "; ".join(transforms)
            + f" | {final} |"
        )

    lines += ["", "## Motif detail", ""]
    for motif in data.get("motifs") or []:
        lines += [
            f"### {motif['name']}",
            "",
            f"**Id:** `{motif['id']}`",
            "",
            "| Role | Meaning | Shot | Marker |",
            "|------|---------|------|--------|",
        ]
        for s in motif.get("stages") or []:
            lines.append(
                f"| `{s['role']}` | {s['meaning']} | "
                f"`{s.get('approx_shot', '—')}` | `{s['marker']}` |"
            )
        lines.append("")
        for s in motif.get("stages") or []:
            lines += [
                f"#### {s['meaning']}",
                "",
                f"- **Staging:** {s.get('staging')}",
            ]
            links = s.get("links") or []
            if links:
                lines.append(
                    "- **Links:** " + ", ".join(f"`{x}`" for x in links)
                )
            lines.append("")

    lines += [
        "## Continuity checklist",
        "",
        "- [ ] Recording ends as memory shared with the living (not only a loop).",
        "- [ ] Hand arc: close door → grip control → release → accept bowl → follow sister.",
        "- [ ] Doorway ends open (story final), answering the closed attic.",
        "- [ ] Bowl/table: waiting → absence/reflection → shared participation.",
        "- [ ] Vine/water: lineage through machines toward release from rigid structures.",
        "- [ ] Mask/theatre: futures and artificial selves resolve toward father as person.",
        "- [ ] Melody/call: refused invitation → living variation (CALL_01 → CALL_06).",
        "- [ ] No new symbols added while `allow_new_symbols` is false.",
        "- [ ] Untransformed flags list is empty or explicitly resolved.",
        "",
        "## Sources",
        "",
        "- Machine-readable: [`motif_system.json`](motif_system.json)",
        "- Markers: [`motif_system_markers.json`](motif_system_markers.json)",
        "- Related: [`call_to_dinner_tracking.md`](call_to_dinner_tracking.md), "
        "[`final_meal_animation.md`](final_meal_animation.md), "
        "[`holy_fool_turning.md`](holy_fool_turning.md)",
        "",
        "```text",
        "python scripts/build_motif_system.py",
        "python scripts/build_motif_system.py --check-links",
        "```",
        "",
    ]
    TRACKING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/motif_tracking.md")
    return TRACKING_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Oino motif tracking system")
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Note related craft briefs / call motif presence",
    )
    args = parser.parse_args()

    report = RunReport(script="build_motif_system", seed=20261210)
    try:
        data = load_system()
        report.mark("reused", "docs/motif_system.json")
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

    flags = find_untransformed(data)
    if flags:
        for f in flags:
            report.note(
                f"UNTRANSFORMED {f.get('kind')}: {f.get('motif_id')}/"
                f"{f.get('stage_id')} — {f.get('meaning')}"
            )
    else:
        report.note("No untransformed symbol flags")

    write_markers(data, flags, report)
    write_tracking_md(data, flags, report)
    if args.check_links:
        check_links(data, report)

    report.note(
        "Motif system locked to 7 symbols; allow_new_symbols=false until readable"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} motifs={len(data['motifs'])} "
        f"untransformed_flags={len(flags)} "
        f"allow_new_symbols={data['policy']['allow_new_symbols']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
