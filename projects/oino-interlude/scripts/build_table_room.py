"""Build SCN_08_TABLE_ROOM — warm first table reunion; father has a life beyond desire.

Usage:
  python scripts/build_table_room.py
  python scripts/build_table_room.py --write-blend
  python scripts/build_table_room.py --write-blend --reset
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

BRIEF = DOCS_DIR / "table_room_brief.json"
STATUS_MD = DOCS_DIR / "table_room.md"
MARKERS_JSON = DOCS_DIR / "table_room_markers.json"
BLEND = SCENES_DIR / "SCN_08_TABLE_ROOM.blend"
HELPER = SCRIPTS_DIR / "_blender_table_room.py"
PAYLOAD = PROJECT_ROOT / "cache" / "table_room_payload.json"
BLEND_REPORT = PROJECT_ROOT / "cache" / "table_room_blender_report.json"

REQUIRED_ELEMENT_KEYS = (
    "worn_table_surface",
    "father_habitual_chair",
    "oino_chair",
    "window_or_opening",
    "playback_device",
    "bowl_or_cup",
    "machinery_as_quiet_architecture",
    "warm_human_light",
    "colder_surrounding_space",
    "vine_growth_one_table_leg",
    "reflective_surface_sister_downstairs",
)

REQUIRED_FATHER_BEATS = (
    "FATHER_MUSICAL_MISTAKE",
    "FATHER_LAUGH",
    "FATHER_NOTE_DISAGREEMENT",
    "FATHER_GLANCE_WINDOW",
    "FATHER_PHYSICAL_HABIT",
    "FATHER_ORDINARY_PAUSE",
)

REQUIRED_CAMERAS = (
    "CAM_TABLE_ARRIVAL",
    "CAM_TABLE_TWO_SHOT",
    "CAM_TABLE_FATHER_HANDS",
    "CAM_TABLE_OINO_CONTROL",
    "CAM_TABLE_REFLECTION",
    "CAM_TABLE_FATHER_LEAVING",
    "CAM_TABLE_DOORWAY_LOOKBACK",
)


def load_brief() -> dict[str, Any]:
    if not BRIEF.is_file():
        raise FileNotFoundError(f"Missing {BRIEF}")
    return json.loads(BRIEF.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("scene") != "SCN_08_TABLE_ROOM":
        errors.append("scene must be SCN_08_TABLE_ROOM")

    role = data.get("role") or {}
    register = (role.get("emotional_register") or "").lower()
    for word in ("warm", "pleasurable", "funny", "safe"):
        if word not in register:
            errors.append(f"role.emotional_register must include '{word}'")

    policy = data.get("policy") or {}
    for key in ("villain", "father_as_monster", "explain_dionysian_uncertainty"):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    for key in (
        "dionysian_uncertainty_optional",
        "father_has_life_beyond_oino_desire",
        "first_scene_must_feel_safe",
    ):
        if policy.get(key) is not True:
            errors.append(f"policy.{key} must be true")

    elements = data.get("elements") or {}
    for key in REQUIRED_ELEMENT_KEYS:
        if not elements.get(key):
            errors.append(f"elements.{key} required")

    beats = data.get("father_life_beats") or []
    ids = [b.get("id") for b in beats]
    if len(ids) != len(set(ids)):
        errors.append("father_life_beats ids must be unique")
    for req in REQUIRED_FATHER_BEATS:
        if req not in ids:
            errors.append(f"Missing father beat: {req}")
    for b in beats:
        bid = b.get("id", "?")
        if not (b.get("beat") or "").strip():
            errors.append(f"{bid}: beat required")
        if not (b.get("staging") or "").strip():
            errors.append(f"{bid}: staging required")

    cams = data.get("cameras") or []
    cam_ids = [c.get("id") for c in cams]
    for req in REQUIRED_CAMERAS:
        if req not in cam_ids:
            errors.append(f"Missing camera: {req}")

    dion = data.get("dionysian_uncertainty") or {}
    if dion.get("optional") is not True:
        errors.append("dionysian_uncertainty.optional must be true")
    if dion.get("explain") is not False:
        errors.append("dionysian_uncertainty.explain must be false")

    return errors


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = []
    for e in data.get("events") or []:
        markers.append(
            {
                "name": e["marker"],
                "frame": e["frame"],
                "note": e.get("note"),
            }
        )
    for b in data.get("father_life_beats") or []:
        markers.append(
            {
                "name": b["marker"],
                "frame": b["frame"],
                "beat": b["beat"],
                "note": b.get("staging"),
            }
        )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "emotional_register": (data.get("role") or {}).get("emotional_register"),
        "father_has_life_beyond_desire": True,
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/table_room_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], blender: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    role = data["role"]
    dion = data.get("dionysian_uncertainty") or {}
    lines = [
        "# Table Room - SCN_08_TABLE_ROOM",
        "",
        f"**Role:** {role.get('is')}  ",
        f"**Register:** {role.get('emotional_register')}  ",
        f"**Oino receives:** {role.get('oino_receives')}",
        "",
        "## Hard rules",
        "",
        f"- Villain: `{policy.get('villain')}`",
        f"- Father as monster: `{policy.get('father_as_monster')}`",
        f"- Father life beyond Oino's desire: `{policy.get('father_has_life_beyond_oino_desire')}`",
        f"- First scene must feel safe: `{policy.get('first_scene_must_feel_safe')}`",
        f"- Explain Dionysian uncertainty: `{policy.get('explain_dionysian_uncertainty')}`",
        f"- Dionysian uncertainty optional: `{policy.get('dionysian_uncertainty_optional')}`",
        "",
        "## Elements",
        "",
    ]
    for key, items in (data.get("elements") or {}).items():
        lines.append(f"- **{key}:** " + ", ".join(f"`{i}`" for i in items))
    lines += [
        "",
        "## Father life beats",
        "",
        "| Id | Beat | Frame |",
        "|----|------|-------|",
    ]
    for b in data.get("father_life_beats") or []:
        lines.append(f"| `{b['id']}` | {b['beat']} | {b['frame']} |")
    lines += [
        "",
        "## Saved cameras",
        "",
    ]
    for c in data.get("cameras") or []:
        lines.append(f"- `{c['id']}` — {c['role']}: {c.get('note', '')}")
    lines += [
        "",
        "## Dionysian uncertainty (optional)",
        "",
        f"- Default choice: {dion.get('default_choice')}",
        f"- Object: `{dion.get('object')}`",
        f"- Explain: `{dion.get('explain')}`",
        f"- Staging: {dion.get('staging')}",
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
        "python scripts/build_table_room.py --write-blend",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/table_room.md")
    return STATUS_MD


def try_blend(payload: dict[str, Any], *, write: bool, report: RunReport) -> dict[str, Any]:
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "cache/table_room_payload.json")
    if not write:
        return {"status": "skipped", "detail": "Pass --write-blend to create .blend"}
    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed - SCN_08_TABLE_ROOM.blend deferred")
        return {
            "status": "deferred",
            "detail": "Install Blender, then re-run with --write-blend",
        }
    if BLEND.exists() and not payload.get("reset"):
        report.mark("reused", "scenes/SCN_08_TABLE_ROOM.blend")
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
        report.fail("SCN_08_TABLE_ROOM.blend", err or f"exit {proc.returncode}")
        return {"status": "failed", "detail": err}
    report.mark("created", "scenes/SCN_08_TABLE_ROOM.blend")
    return {"status": "created", "detail": str(BLEND)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCN_08_TABLE_ROOM")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_table_room", seed=20261210, reset=args.reset)
    try:
        data = load_brief()
        report.mark("reused", "docs/table_room_brief.json")
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
        report.mark("reused", "scripts/_blender_table_room.py")
    blender_status = try_blend(payload, write=args.write_blend, report=report)
    write_status(data, blender_status, report)
    report.note(
        "Table centre; warm/funny/safe first reunion; "
        "father life beyond desire; Dionysian edge optional unexplained"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"father_beats={len(data['father_life_beats'])} "
        f"cameras={len(data['cameras'])} blend={blender_status['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
