"""Build SCN_13_TITLE_CARD — exact album card after the emotional ending.

Emotional ending = Oino follows the sister's changed melody.
Then: doorway hold → living note settles → recording imperfect end →
near-black → fade title → fade date.

Exact text: One Of Gods Fools / December 10, 2026
Marker range: TITLE_CARD_FINAL

Usage:
  python scripts/build_title_card.py
  python scripts/build_title_card.py --write-blend
  python scripts/build_title_card.py --write-blend --reset
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

BRIEF = DOCS_DIR / "title_card_brief.json"
STATUS_MD = DOCS_DIR / "title_card.md"
MARKERS_JSON = DOCS_DIR / "title_card_markers.json"
CONTROLS_JSON = DOCS_DIR / "title_card_controls.json"
BLEND = SCENES_DIR / "SCN_13_TITLE_CARD.blend"
HELPER = SCRIPTS_DIR / "_blender_title_card.py"
PAYLOAD = PROJECT_ROOT / "cache" / "title_card_payload.json"
BLEND_REPORT = PROJECT_ROOT / "cache" / "title_card_blender_report.json"

TITLE_EXACT = "One Of Gods Fools"
DATE_EXACT = "December 10, 2026"

REQUIRED_CONTROLS = (
    "title_fade_in_frames",
    "date_fade_in_frames",
    "title_hold_duration_frames",
    "date_hold_duration_frames",
    "background_colour",
    "type_colour",
    "letter_spacing",
    "final_fade_out",
)

REQUIRED_SEQUENCE = (
    "TC_HOLD_OPEN_DOORWAY",
    "TC_LIVING_NOTE_SETTLES",
    "TC_RECORDING_IMPERFECT_END",
    "TC_FADE_NEAR_BLACK",
    "TC_TITLE_FADE_IN",
    "TC_DATE_FADE_IN",
)


def load_brief() -> dict[str, Any]:
    if not BRIEF.is_file():
        raise FileNotFoundError(f"Missing {BRIEF}")
    return json.loads(BRIEF.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("scene") != "SCN_13_TITLE_CARD":
        errors.append("scene must be SCN_13_TITLE_CARD")

    title = (data.get("title") or {}).get("text") or ""
    if title != TITLE_EXACT:
        errors.append(f"title.text must be exactly '{TITLE_EXACT}'")
    if "'" in title or "\u2019" in title:
        errors.append("title must contain no apostrophe in Gods")
    for bad in (data.get("title") or {}).get("forbidden_forms") or []:
        if title == bad:
            errors.append(f"title matches forbidden form: {bad}")

    date = (data.get("release_date") or {}).get("text") or ""
    if date != DATE_EXACT:
        errors.append(f"release_date.text must be exactly '{DATE_EXACT}'")

    policy = data.get("policy") or {}
    for key in (
        "apostrophe_in_Gods",
        "extra_subtitle",
        "logline",
        "moral_statement",
        "social_handle",
        "unapproved_production_credit",
        "generic_trailer_animation",
        "metallic_text",
        "excessive_glow",
        "fast_movement",
    ):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    typo = (policy.get("typography") or "").lower()
    for word in ("legible", "quiet", "tactile", "archaeological"):
        if word not in typo:
            errors.append(f"policy.typography must include '{word}'")

    controls = data.get("controls") or {}
    for key in REQUIRED_CONTROLS:
        if key not in controls:
            errors.append(f"controls.{key} required")
    fade_out = controls.get("final_fade_out") or {}
    if fade_out.get("enabled") is not False:
        errors.append("controls.final_fade_out.enabled must default false")
    if not isinstance(controls.get("letter_spacing"), (int, float)):
        errors.append("controls.letter_spacing must be a number")
    bg = controls.get("background_colour") or {}
    tc = controls.get("type_colour") or {}
    if not bg.get("hex") or not bg.get("rgba"):
        errors.append("controls.background_colour needs hex and rgba")
    if not tc.get("hex") or not tc.get("rgba"):
        errors.append("controls.type_colour needs hex and rgba")

    seq = data.get("sequence_after_emotional_ending") or []
    ids = [s.get("id") for s in seq]
    for req in REQUIRED_SEQUENCE:
        if req not in ids:
            errors.append(f"Missing sequence beat: {req}")
    for s in seq:
        sid = s.get("id", "?")
        if not (s.get("action") or "").strip():
            errors.append(f"{sid}: action required")
        if s.get("marker") is None:
            errors.append(f"{sid}: marker required")

    emotional = (data.get("emotional_ending") or {}).get("is") or ""
    if "changed melody" not in emotional.lower():
        errors.append("emotional_ending must be following sister's changed melody")

    final = (data.get("markers") or {}).get("TITLE_CARD_FINAL") or {}
    if final.get("name") != "TITLE_CARD_FINAL":
        errors.append("markers.TITLE_CARD_FINAL.name must be TITLE_CARD_FINAL")
    if final.get("frame_start") is None or final.get("frame_end") is None:
        errors.append("TITLE_CARD_FINAL needs frame_start and frame_end")
    if int(final.get("frame_end") or 0) < int(final.get("frame_start") or 0):
        errors.append("TITLE_CARD_FINAL frame_end before frame_start")

    return errors


def write_controls(data: dict[str, Any], report: RunReport) -> Path:
    controls = data["controls"]
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "title_text": TITLE_EXACT,
        "release_date_text": DATE_EXACT,
        "controls": {
            "title_fade_in": controls["title_fade_in_frames"],
            "date_fade_in": controls["date_fade_in_frames"],
            "title_hold_duration": controls["title_hold_duration_frames"],
            "date_hold_duration": controls["date_hold_duration_frames"],
            "background_colour": controls["background_colour"],
            "type_colour": controls["type_colour"],
            "letter_spacing": controls["letter_spacing"],
            "final_fade_out": controls["final_fade_out"],
        },
        "units": "frames @ fps in brief",
        "final_fade_out_default": "off unless delivery requires it",
    }
    CONTROLS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/title_card_controls.json")
    return CONTROLS_JSON


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = []
    for s in data.get("sequence_after_emotional_ending") or []:
        markers.append(
            {
                "name": s["marker"],
                "frame": s["local_frame"],
                "action": s["action"],
                "note": s.get("link") or s.get("camera_language"),
            }
        )
    final = data["markers"]["TITLE_CARD_FINAL"]
    markers.append(
        {
            "name": "TITLE_CARD_FINAL",
            "frame": final["frame_start"],
            "frame_start": final["frame_start"],
            "frame_end": final["frame_end"],
            "global_frame_start": final.get("global_frame_start"),
            "global_frame_end": final.get("global_frame_end"),
            "range": True,
            "note": final.get("note"),
        }
    )
    markers.append(
        {
            "name": "TITLE_CARD_FINAL_END",
            "frame": final["frame_end"],
            "note": "End of TITLE_CARD_FINAL range",
        }
    )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "title_text": TITLE_EXACT,
        "release_date_text": DATE_EXACT,
        "apostrophe_in_Gods": False,
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/title_card_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], blender: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    controls = data["controls"]
    final = data["markers"]["TITLE_CARD_FINAL"]
    lines = [
        "# Title card — SCN_13_TITLE_CARD",
        "",
        f"**Emotional ending (before card):** {(data.get('emotional_ending') or {}).get('is')}  ",
        f"**Title:** **{TITLE_EXACT}**  ",
        f"**Date:** **{DATE_EXACT}**  ",
        f"**Apostrophe in Gods:** `{policy.get('apostrophe_in_Gods')}`",
        "",
        "## Sequence after emotional ending",
        "",
    ]
    for s in data.get("sequence_after_emotional_ending") or []:
        lines.append(
            f"{s['order']}. `{s['marker']}` f{s['local_frame']}: {s['action']}"
        )
    lines += [
        "",
        "## Hard rules",
        "",
        f"- Extra subtitle: `{policy.get('extra_subtitle')}`",
        f"- Logline: `{policy.get('logline')}`",
        f"- Moral statement: `{policy.get('moral_statement')}`",
        f"- Social handle: `{policy.get('social_handle')}`",
        f"- Unapproved production credit: `{policy.get('unapproved_production_credit')}`",
        f"- Trailer animation / metallic / glow / fast move: "
        f"`{policy.get('generic_trailer_animation')}` / "
        f"`{policy.get('metallic_text')}` / "
        f"`{policy.get('excessive_glow')}` / "
        f"`{policy.get('fast_movement')}`",
        f"- Typography: {policy.get('typography')}",
        "",
        "## Exposed controls",
        "",
        f"- title fade in: `{controls['title_fade_in_frames']}` frames",
        f"- date fade in: `{controls['date_fade_in_frames']}` frames",
        f"- title hold duration: `{controls['title_hold_duration_frames']}` frames",
        f"- date hold duration: `{controls['date_hold_duration_frames']}` frames",
        f"- background colour: `{controls['background_colour'].get('hex')}` "
        f"({controls['background_colour'].get('name')})",
        f"- type colour: `{controls['type_colour'].get('hex')}` "
        f"({controls['type_colour'].get('name')})",
        f"- letter spacing: `{controls['letter_spacing']}`",
        f"- final fade out: enabled=`{controls['final_fade_out'].get('enabled')}` "
        f"(default off unless delivery requires it)",
        "",
        "## TITLE_CARD_FINAL",
        "",
        f"- Local range: f{final['frame_start']}–f{final['frame_end']}",
        f"- Global align: f{final.get('global_frame_start')}–f{final.get('global_frame_end')}",
        f"- Note: {final.get('note')}",
        "",
        "## Blender",
        "",
        f"- Target: `{BLEND.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Status: **{blender.get('status')}**",
        f"- Detail: {blender.get('detail')}",
        "",
        "```text",
        "python scripts/build_title_card.py --write-blend",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/title_card.md")
    return STATUS_MD


def try_blend(payload: dict[str, Any], *, write: bool, report: RunReport) -> dict[str, Any]:
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "cache/title_card_payload.json")
    if not write:
        return {"status": "skipped", "detail": "Pass --write-blend to create .blend"}
    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed - SCN_13_TITLE_CARD.blend deferred")
        return {
            "status": "deferred",
            "detail": "Install Blender, then re-run with --write-blend",
        }
    if BLEND.exists() and not payload.get("reset"):
        report.mark("reused", "scenes/SCN_13_TITLE_CARD.blend")
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
        report.fail("SCN_13_TITLE_CARD.blend", err or f"exit {proc.returncode}")
        return {"status": "failed", "detail": err}
    report.mark("created", "scenes/SCN_13_TITLE_CARD.blend")
    return {"status": "created", "detail": str(BLEND)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCN_13_TITLE_CARD")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_title_card", seed=20261210, reset=args.reset)
    try:
        data = load_brief()
        report.mark("reused", "docs/title_card_brief.json")
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

    write_controls(data, report)
    write_markers(data, report)
    cfg = load_show_config()
    engine = resolve_render_engine(cfg)
    payload = {
        **data,
        "resolution": (cfg.get("resolutions") or {}).get("hd") or [1920, 1080],
        "engine": engine.get("engine") or "BLENDER_EEVEE_NEXT",
        "blend_out": str(BLEND.resolve()),
        "report_out": str(BLEND_REPORT.resolve()),
        "reset": args.reset,
    }
    if HELPER.is_file():
        report.mark("reused", "scripts/_blender_title_card.py")
    blender_status = try_blend(payload, write=args.write_blend, report=report)
    write_status(data, blender_status, report)
    report.note(
        f"Title card locked: '{TITLE_EXACT}' / '{DATE_EXACT}'; "
        "TITLE_CARD_FINAL range; final_fade_out default off"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"title={TITLE_EXACT!r} blend={blender_status['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
