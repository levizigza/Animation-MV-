"""Build SCN_07_ZONE — unresolved passage; follow unfinished melody.

Usage:
  python scripts/build_zone.py
  python scripts/build_zone.py --write-blend
  python scripts/build_zone.py --write-blend --reset
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

BRIEF = DOCS_DIR / "zone_brief.json"
STATUS_MD = DOCS_DIR / "zone.md"
MARKERS_JSON = DOCS_DIR / "zone_markers.json"
BLEND = SCENES_DIR / "SCN_07_ZONE.blend"
HELPER = SCRIPTS_DIR / "_blender_zone.py"
PAYLOAD = PROJECT_ROOT / "cache" / "zone_payload.json"
BLEND_REPORT = PROJECT_ROOT / "cache" / "zone_blender_report.json"

REQUIRED_ELEMENT_KEYS = (
    "shallow_water",
    "industrial_debris",
    "abandoned_tools",
    "doors_uncertain",
    "roots_vines_machinery",
    "sound_reflections_wrong",
    "irregular_knock",
    "unsourced_red_amber_light",
    "table_glimpse",
    "distant_laugh",
    "damaged_frame_dionysus_echo",
)

REQUIRED_THRESHOLDS = (
    "THR_01_MAP_MISMATCH",
    "THR_02_PHOTO_UNPROVEN",
    "THR_03_VOICE_UNCLASSIFIED",
    "THR_04_REFLECTION_LATE",
    "THR_05_ANCESTOR_INCOMPLETE",
)


def load_brief() -> dict[str, Any]:
    if not BRIEF.is_file():
        raise FileNotFoundError(f"Missing {BRIEF}")
    return json.loads(BRIEF.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nature = data.get("nature") or {}
    if nature.get("resolved") is not False:
        errors.append("nature.resolved must be false")
    if nature.get("final_answer_allowed") is not False:
        errors.append("nature.final_answer_allowed must be false")

    policy = data.get("policy") or {}
    for key in (
        "villain",
        "technical_explanation",
        "wish_room_diagram",
        "final_answer_what_zone_is",
    ):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    if policy.get("patient_camera") is not True:
        errors.append("policy.patient_camera must be true")
    if policy.get("hold_empty_space_after_oino_exits_frame") is not True:
        errors.append("policy.hold_empty_space_after_oino_exits_frame must be true")

    goal = (data.get("oino_goal") or "").lower()
    if "unfinished melody" not in goal:
        errors.append("oino_goal must be follow the unfinished melody")

    elements = data.get("elements") or {}
    for key in REQUIRED_ELEMENT_KEYS:
        if not elements.get(key):
            errors.append(f"elements.{key} required")

    thresholds = data.get("thresholds") or []
    ids = [t.get("id") for t in thresholds]
    if len(ids) != len(set(ids)):
        errors.append("threshold ids must be unique")
    for req in REQUIRED_THRESHOLDS:
        if req not in ids:
            errors.append(f"Missing threshold: {req}")
    for t in thresholds:
        tid = t.get("id", "?")
        if not (t.get("certainty_removed") or "").strip():
            errors.append(f"{tid}: certainty_removed required")
        if not (t.get("staging") or "").strip():
            errors.append(f"{tid}: staging required")

    if data.get("scene") != "SCN_07_ZONE":
        errors.append("scene must be SCN_07_ZONE")

    return errors


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = [
        {
            "name": "ZONE_ENTER",
            "frame": data.get("scene_frame_start", 1),
            "note": "Enter unresolved passage; follow unfinished melody",
        }
    ]
    for t in data.get("thresholds") or []:
        markers.append(
            {
                "name": t["marker"],
                "frame": t["frame"],
                "certainty_removed": t["certainty_removed"],
                "note": t.get("staging"),
            }
        )
    for e in data.get("events") or []:
        markers.append(
            {
                "name": e["marker"],
                "frame": e["frame"],
                "note": e.get("note"),
                "link": e.get("link"),
            }
        )
    markers.append(
        {
            "name": "ZONE_EXIT",
            "frame": data.get("scene_frame_end", 360),
            "note": "Leave Zone toward table; nature still unresolved",
        }
    )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "nature_unresolved": True,
        "oino_goal": data.get("oino_goal"),
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/zone_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], blender: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    lines = [
        "# Zone - SCN_07_ZONE",
        "",
        f"**Nature:** {data['nature']['is']}  ",
        f"**Resolved:** `{data['nature']['resolved']}`  ",
        f"**Oino's goal:** {data.get('oino_goal')}",
        "",
        "## Hard rules",
        "",
        f"- Villain: `{policy.get('villain')}`",
        f"- Technical explanation: `{policy.get('technical_explanation')}`",
        f"- Wish-room diagram: `{policy.get('wish_room_diagram')}`",
        f"- Final answer what the Zone is: `{policy.get('final_answer_what_zone_is')}`",
        f"- Patient camera / empty hold after exit: `{policy.get('patient_camera')}` / `{policy.get('hold_empty_space_after_oino_exits_frame')}`",
        "",
        "## Elements",
        "",
    ]
    for key, items in (data.get("elements") or {}).items():
        lines.append(f"- **{key}:** " + ", ".join(f"`{i}`" for i in items))
    lines += [
        "",
        "## Thresholds (certainty removed)",
        "",
        "| Id | Certainty removed | Frame |",
        "|----|-------------------|-------|",
    ]
    for t in data.get("thresholds") or []:
        lines.append(
            f"| `{t['id']}` | {t['certainty_removed']} | {t['frame']} |"
        )
    lines += [
        "",
        "## Events",
        "",
    ]
    for e in data.get("events") or []:
        lines.append(f"- `{e['marker']}` f{e['frame']}: {e['note']}")
    lines += [
        "",
        "## Blender",
        "",
        f"- Target: `{BLEND.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Status: **{blender.get('status')}**",
        f"- Detail: {blender.get('detail')}",
        "",
        "```text",
        "python scripts/build_zone.py --write-blend",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/zone.md")
    return STATUS_MD


def try_blend(payload: dict[str, Any], *, write: bool, report: RunReport) -> dict[str, Any]:
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "cache/zone_payload.json")
    if not write:
        return {"status": "skipped", "detail": "Pass --write-blend to create .blend"}
    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed - SCN_07_ZONE.blend deferred")
        return {
            "status": "deferred",
            "detail": "Install Blender, then re-run with --write-blend",
        }
    if BLEND.exists() and not payload.get("reset"):
        report.mark("reused", "scenes/SCN_07_ZONE.blend")
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
        report.fail("SCN_07_ZONE.blend", err or f"exit {proc.returncode}")
        return {"status": "failed", "detail": err}
    report.mark("created", "scenes/SCN_07_ZONE.blend")
    return {"status": "created", "detail": str(BLEND)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCN_07_ZONE")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_zone", seed=20261210, reset=args.reset)
    try:
        data = load_brief()
        report.mark("reused", "docs/zone_brief.json")
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
        report.mark("reused", "scripts/_blender_zone.py")
    blender_status = try_blend(payload, write=args.write_blend, report=report)
    write_status(data, blender_status, report)
    report.note(
        "Zone unresolved; goal=unfinished melody; "
        "no villain/tech diagram/final answer; hold empty space"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"thresholds={len(data['thresholds'])} blend={blender_status['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
