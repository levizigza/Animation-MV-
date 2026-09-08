"""Build SCN_02_OINO_ARCHIVE — great-great-grandfather's archive.

Writes brief docs, marker bundle, Blender payload, and (when Blender is available)
``scenes/SCN_02_OINO_ARCHIVE.blend``.

Usage:
  python scripts/build_oino_archive.py
  python scripts/build_oino_archive.py --write-blend
  python scripts/build_oino_archive.py --write-blend --reset
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR, SCENES_DIR  # noqa: E402
from show_config import load_show_config, resolve_render_engine  # noqa: E402

BRIEF = DOCS_DIR / "oino_archive_brief.json"
NOTES = DOCS_DIR / "oino_archive_notes.md"
MARKERS = DOCS_DIR / "oino_archive_markers.json"
STATUS = DOCS_DIR / "oino_archive_status.md"
BLEND = SCENES_DIR / "SCN_02_OINO_ARCHIVE.blend"
HELPER = SCRIPTS_DIR / "_blender_oino_archive.py"
PAYLOAD = PROJECT_ROOT / "cache" / "oino_archive_payload.json"
BLEND_REPORT = PROJECT_ROOT / "cache" / "oino_archive_blender_report.json"


def validate_brief(brief: dict[str, Any], report: RunReport) -> list[str]:
    errors: list[str] = []
    insert = brief.get("family_line_insert") or {}
    fs = int(insert.get("frame_start", 0))
    fe = int(insert.get("frame_end", 0))
    max_f = int(insert.get("max_frames_at_24fps", 45))
    max_s = float(insert.get("max_duration_seconds", 1.9))
    span = fe - fs + 1
    if span > max_f:
        errors.append(
            f"Family-line insert spans {span} frames (> {max_f} / {max_s}s limit)"
        )
    if span / float(brief.get("fps") or 24) > max_s + 1e-6:
        errors.append(
            f"Family-line insert duration {span / 24:.3f}s exceeds {max_s}s"
        )
    text = insert.get("text") or ""
    required = ["DIONYSUS", "STAPHYLUS", "RHOEO", "ANIUS", "OINO"]
    for part in required:
        if part not in text.upper().replace("Ö", "O"):
            # allow unicode variants in display; require ASCII tokens in canon string
            if part not in text:
                errors.append(f"Family-line insert missing token: {part}")
    if not (brief.get("genealogy_project_note") or {}).get("statement"):
        errors.append("genealogy_project_note.statement is required")
    for key in (
        "reels_and_equipment",
        "photographs",
        "handwritten_documents",
        "vine_grape_worn",
        "broken_thyrsus_mechanical",
        "seal",
        "bowl_or_cup",
        "water_stain_wine_under_light",
        "footage_ancestor_shot",
        "footage_reconstructed",
    ):
        inv = (brief.get("inventory") or {}).get(key)
        if not inv:
            errors.append(f"inventory.{key} empty")
    if len(brief.get("transitions") or []) < 6:
        errors.append("Need all six specified transitions")
    ids = [t.get("id") for t in brief.get("transitions") or []]
    if len(ids) != len(set(ids)):
        errors.append("transition ids must be unique")
    for e in errors:
        report.fail("validate", e)
    return errors


def write_markers(brief: dict[str, Any], report: RunReport) -> Path:
    insert = brief["family_line_insert"]
    markers = {
        "schema_version": 1,
        "scene": brief["scene"],
        "editable": True,
        "genealogy_note": brief["genealogy_project_note"],
        "family_line_insert": insert,
        "markers": [
            {
                "name": "INS_FAMILY_LINE_START",
                "frame": insert["frame_start"],
                "note": "Damaged family document insert start (<2s)",
            },
            {
                "name": "INS_FAMILY_LINE_END",
                "frame": insert["frame_end"],
                "note": "Insert end",
            },
        ],
        "transitions": brief["transitions"],
        "intent": brief["intent"],
    }
    for tr in brief["transitions"]:
        markers["markers"].append(
            {
                "name": tr["marker_start"],
                "frame": tr["frame_start"],
                "note": f"{tr['from']} -> {tr['to']}",
            }
        )
        markers["markers"].append(
            {
                "name": tr["marker_end"],
                "frame": tr["frame_end"],
                "note": f"end {tr['id']}",
            }
        )
    MARKERS.write_text(json.dumps(markers, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/oino_archive_markers.json")
    return MARKERS


def write_status(
    brief: dict[str, Any], blender: dict[str, Any], report: RunReport
) -> Path:
    insert = brief["family_line_insert"]
    span = insert["frame_end"] - insert["frame_start"] + 1
    lines = [
        "# Archive status — SCN_02_OINO_ARCHIVE",
        "",
        f"**Intent:** {brief['intent']}",
        "",
        "## Family-line insert",
        "",
        f"- Text: `{insert['text']}`",
        f"- Frames: {insert['frame_start']}–{insert['frame_end']} ({span} f ≈ {span/24:.2f}s)",
        f"- Cap: < {insert['max_duration_seconds']}s",
        f"- Look: {insert['look']}",
        "",
        "## Project note",
        "",
        brief["genealogy_project_note"]["statement"],
        "",
        "## Inventory groups",
        "",
    ]
    for k, items in (brief.get("inventory") or {}).items():
        lines.append(f"- **{k}:** " + ", ".join(f"`{i}`" for i in items))
    lines += ["", "## Transitions", ""]
    for tr in brief["transitions"]:
        lines.append(
            f"- `{tr['id']}`: {tr['from']} → {tr['to']} "
            f"(f{tr['frame_start']}–{tr['frame_end']})"
        )
    lines += [
        "",
        "## Blender",
        "",
        f"- Target: `{BLEND.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Status: **{blender.get('status')}**",
        f"- Detail: {blender.get('detail')}",
        "",
        f"See also [`oino_archive_notes.md`](oino_archive_notes.md).",
        "",
    ]
    STATUS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/oino_archive_status.md")
    return STATUS


def try_blend(payload: dict[str, Any], *, write: bool, report: RunReport) -> dict[str, Any]:
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "cache/oino_archive_payload.json")
    if not write:
        return {"status": "skipped", "detail": "Pass --write-blend to create .blend"}
    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed — SCN_02_OINO_ARCHIVE.blend deferred")
        return {
            "status": "deferred",
            "detail": "Install Blender, then re-run with --write-blend",
        }
    if BLEND.exists() and not payload.get("reset"):
        report.mark("reused", "scenes/SCN_02_OINO_ARCHIVE.blend")
        return {"status": "reused", "detail": "Existing blend preserved"}
    if not HELPER.is_file():
        report.fail("helper", f"Missing {HELPER}")
        return {"status": "failed", "detail": "helper missing"}
    proc = subprocess.run(
        [str(blender), "--background", "--python", str(HELPER), "--", str(PAYLOAD)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not BLEND.exists():
        err = (proc.stderr or proc.stdout or "")[-2000:]
        report.fail("SCN_02_OINO_ARCHIVE.blend", err or f"exit {proc.returncode}")
        return {"status": "failed", "detail": err}
    report.mark("created", "scenes/SCN_02_OINO_ARCHIVE.blend")
    return {"status": "created", "detail": str(BLEND)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCN_02_OINO_ARCHIVE")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_oino_archive", seed=20261210, reset=args.reset)
    if not BRIEF.is_file():
        report.fail("brief", f"Missing {BRIEF}")
        report.write(REPORTS_DIR)
        return 1
    brief = json.loads(BRIEF.read_text(encoding="utf-8"))
    report.mark("reused", "docs/oino_archive_brief.json")
    if NOTES.is_file():
        report.mark("reused", "docs/oino_archive_notes.md")

    if validate_brief(brief, report):
        report.write(REPORTS_DIR)
        return 1

    write_markers(brief, report)
    cfg = load_show_config()
    engine = resolve_render_engine(cfg)
    payload = {
        **brief,
        "resolution": (cfg.get("resolutions") or {}).get("hd") or [1920, 1080],
        "engine": engine.get("engine") or "BLENDER_EEVEE_NEXT",
        "blend_out": str(BLEND.resolve()),
        "report_out": str(BLEND_REPORT.resolve()),
        "reset": args.reset,
    }
    if HELPER.is_file():
        report.mark("reused", "scripts/_blender_oino_archive.py")
    blender_status = try_blend(payload, write=args.write_blend, report=report)
    write_status(brief, blender_status, report)

    report.note(
        "Archive suggests preservation + transformation across generations; "
        "not biological superiority or automatic wisdom"
    )
    report.write(REPORTS_DIR)
    insert = brief["family_line_insert"]
    span = insert["frame_end"] - insert["frame_start"] + 1
    print(
        f"SUMMARY ok={report.ok} scene={brief['scene']} "
        f"lineage_frames={span} blend={blender_status['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
