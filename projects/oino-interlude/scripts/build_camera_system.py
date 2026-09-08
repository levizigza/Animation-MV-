"""Build Oino camera system and regenerate docs/shot_list.csv.

Camera language by region; hero shots prioritized; every shot records
camera, lens, focus target, duration, emotional purpose, render priority.

Usage:
  python scripts/build_camera_system.py
  python scripts/build_camera_system.py --check-animatic
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, REPORTS_DIR  # noqa: E402

SYSTEM_JSON = DOCS_DIR / "camera_system.json"
SHOT_CSV = DOCS_DIR / "shot_list.csv"
STATUS_MD = DOCS_DIR / "camera_system.md"
MARKERS_JSON = DOCS_DIR / "camera_system_markers.json"
ANIMATIC = DOCS_DIR / "animatic_shot_list.json"

REQUIRED_LANGUAGES = (
    "attic",
    "archive",
    "steam",
    "electric",
    "digital",
    "zone",
    "table",
    "return",
    "title_card",
)

REQUIRED_HERO_LABELS = (
    "sister calling Oino",
    "father's unfinished recording",
    "archive box marked OINO",
    "family-line document",
    "ancestor repairing the sleeve",
    "ancestor ignoring the call to dinner",
    "first factory-gate transition",
    "electricity returning time to a household",
    "person using a synthetic voice",
    "Oino seeing her own recording",
    "first glimpse of the table",
    "father and Oino in the warm two-shot",
    "Oino's hand on the reset control",
    "sister in the table reflection",
    "Oino releasing the control",
    "Oino accepting the bowl",
    "sister changing the melody",
    "open doorway",
    "title card",
)

CSV_FIELDS = (
    "shot_id",
    "hero",
    "hero_label",
    "camera",
    "lens_mm",
    "focus_target",
    "frame_start",
    "frame_end",
    "duration_frames",
    "duration_sec",
    "camera_language",
    "emotional_purpose",
    "render_priority",
    "parent_animatic",
    "lighting_preset",
)

RENDER_PRIORITIES = ("HERO", "HIGH", "MED", "LOW")


def load() -> dict[str, Any]:
    if not SYSTEM_JSON.is_file():
        raise FileNotFoundError(f"Missing {SYSTEM_JSON}")
    return json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))


def duration_frames(shot: dict[str, Any]) -> int:
    return int(shot["frame_end"]) - int(shot["frame_start"]) + 1


def duration_sec(shot: dict[str, Any], fps: float) -> float:
    return round(duration_frames(shot) / float(fps), 3)


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    for key in (
        "avoid_constant_aerial_tours",
        "avoid_aggressive_camera_shake",
        "avoid_cuts_only_for_environment_detail",
        "protect_performance_at_table",
        "title_card_still",
    ):
        if policy.get(key) is not True:
            errors.append(f"policy.{key} must be true")

    langs = data.get("camera_language") or {}
    for req in REQUIRED_LANGUAGES:
        if req not in langs:
            errors.append(f"Missing camera_language: {req}")
        else:
            block = langs[req]
            if not (block.get("framing") or "").strip():
                errors.append(f"camera_language.{req}.framing required")
            if not block.get("must_not"):
                errors.append(f"camera_language.{req}.must_not required")

    # Spot-check framing language from brief
    checks = {
        "attic": "downward",
        "archive": "frames within frames",
        "steam": "low human",
        "electric": "relief",
        "digital": "watch herself",
        "zone": "empty space",
        "table": "two-shot",
        "return": "opening angles",
        "title_card": "still",
    }
    for key, needle in checks.items():
        framing = ((langs.get(key) or {}).get("framing") or "").lower()
        if needle not in framing:
            errors.append(f"camera_language.{key}.framing should include '{needle}'")

    shots = data.get("shots") or []
    ids = [s.get("id") for s in shots]
    if len(ids) != len(set(ids)):
        errors.append("shot ids must be unique")

    hero_labels = [
        (s.get("hero_label") or "").strip()
        for s in shots
        if s.get("hero") is True
    ]
    for req in REQUIRED_HERO_LABELS:
        if req not in hero_labels:
            errors.append(f"Missing hero shot: {req}")
    if len(hero_labels) != len(REQUIRED_HERO_LABELS):
        errors.append(
            f"Expected exactly {len(REQUIRED_HERO_LABELS)} hero shots, "
            f"found {len(hero_labels)}"
        )

    for s in shots:
        sid = s.get("id", "?")
        for key in (
            "camera",
            "lens_mm",
            "focus_target",
            "frame_start",
            "frame_end",
            "camera_language",
            "emotional_purpose",
            "render_priority",
        ):
            if s.get(key) in (None, ""):
                errors.append(f"{sid}: {key} required")
        if s.get("camera_language") not in REQUIRED_LANGUAGES:
            errors.append(f"{sid}: unknown camera_language")
        if s.get("render_priority") not in RENDER_PRIORITIES:
            errors.append(f"{sid}: render_priority must be one of {RENDER_PRIORITIES}")
        if int(s.get("frame_end") or 0) < int(s.get("frame_start") or 0):
            errors.append(f"{sid}: frame_end before frame_start")
        if s.get("hero") is True:
            if not (s.get("hero_label") or "").strip():
                errors.append(f"{sid}: hero_label required for hero shots")
            if s.get("render_priority") != "HERO":
                errors.append(f"{sid}: hero shots must use render_priority HERO")
        if s.get("camera_language") == "title_card":
            if "still" not in (s.get("emotional_purpose") or "").lower() and s.get("id") != "SH130_TITLE_CARD":
                pass
            if s.get("id") == "SH130_TITLE_CARD":
                if (s.get("title_text") or "") != "One Of Gods Fools":
                    errors.append("SH130_TITLE_CARD title_text must be One Of Gods Fools")

    return errors


def check_animatic(data: dict[str, Any], report: RunReport) -> None:
    if not ANIMATIC.is_file():
        report.note("animatic_shot_list.json missing — skip")
        return
    anim = json.loads(ANIMATIC.read_text(encoding="utf-8"))
    parents = {s.get("id") for s in (anim.get("shots") or [])}
    for s in data.get("shots") or []:
        parent = s.get("parent_animatic")
        if parent and parent not in parents:
            report.fail("animatic", f"{s.get('id')}: unknown parent {parent}")
    report.note("animatic parent links checked")


def write_csv(data: dict[str, Any], report: RunReport) -> Path:
    fps = float(data.get("fps") or 24)
    shots = sorted(
        data.get("shots") or [],
        key=lambda s: (int(s.get("frame_start") or 0), s.get("id") or ""),
    )
    SHOT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SHOT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for s in shots:
            writer.writerow(
                {
                    "shot_id": s["id"],
                    "hero": "yes" if s.get("hero") else "no",
                    "hero_label": s.get("hero_label") or "",
                    "camera": s["camera"],
                    "lens_mm": s["lens_mm"],
                    "focus_target": s["focus_target"],
                    "frame_start": s["frame_start"],
                    "frame_end": s["frame_end"],
                    "duration_frames": duration_frames(s),
                    "duration_sec": duration_sec(s, fps),
                    "camera_language": s["camera_language"],
                    "emotional_purpose": s["emotional_purpose"],
                    "render_priority": s["render_priority"],
                    "parent_animatic": s.get("parent_animatic") or "",
                    "lighting_preset": s.get("lighting_preset") or "",
                }
            )
    report.mark("created", "docs/shot_list.csv")
    return SHOT_CSV


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = []
    for s in data.get("shots") or []:
        markers.append(
            {
                "name": f"CAM_{s['id']}",
                "shot_id": s["id"],
                "frame": s["frame_start"],
                "camera": s["camera"],
                "lens_mm": s["lens_mm"],
                "hero": bool(s.get("hero")),
                "render_priority": s["render_priority"],
                "note": s.get("emotional_purpose"),
            }
        )
    out = {
        "schema_version": 1,
        "system_id": data.get("system_id"),
        "editable": True,
        "policy": data.get("policy"),
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/camera_system_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    langs = data["camera_language"]
    shots = data.get("shots") or []
    heroes = [s for s in shots if s.get("hero")]
    lines = [
        "# Camera system — Oino (Interlude)",
        "",
        f"**System:** `{data.get('system_id')}`  ",
        f"**Shots:** {len(shots)} ({len(heroes)} hero)  ",
        f"**CSV:** [`shot_list.csv`](shot_list.csv)",
        "",
        "## Hard rules",
        "",
        f"- Avoid constant aerial tours: `{policy.get('avoid_constant_aerial_tours')}`",
        f"- Avoid aggressive camera shake: `{policy.get('avoid_aggressive_camera_shake')}`",
        f"- Avoid cuts only for environment detail: "
        f"`{policy.get('avoid_cuts_only_for_environment_detail')}`",
        f"- Protect table performance: `{policy.get('protect_performance_at_table')}`",
        f"- Title card still: `{policy.get('title_card_still')}`",
        "",
        "## Camera language",
        "",
    ]
    for key in REQUIRED_LANGUAGES:
        block = langs[key]
        lines += [
            f"### {key}",
            "",
            f"- **Framing:** {block.get('framing')}",
            f"- **Movement:** {block.get('movement')}",
            f"- **Must not:** " + "; ".join(block.get("must_not") or []),
            "",
        ]

    lines += [
        "## Hero shots",
        "",
        "| Shot | Label | Lens | Priority | Purpose |",
        "|------|-------|------|----------|---------|",
    ]
    for s in sorted(heroes, key=lambda x: int(x["frame_start"])):
        lines.append(
            f"| `{s['id']}` | {s.get('hero_label')} | {s['lens_mm']}mm | "
            f"{s['render_priority']} | {s['emotional_purpose']} |"
        )

    lines += [
        "",
        "## All shots",
        "",
        "See [`shot_list.csv`](shot_list.csv) for camera, lens, focus target, "
        "duration, emotional purpose, and render priority.",
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/build_camera_system.py",
        "python scripts/build_camera_system.py --check-animatic",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/camera_system.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Oino camera system + shot_list.csv")
    parser.add_argument(
        "--check-animatic",
        action="store_true",
        help="Validate parent_animatic ids against animatic_shot_list.json",
    )
    args = parser.parse_args()

    report = RunReport(script="build_camera_system", seed=20261210)
    try:
        data = load()
        report.mark("reused", "docs/camera_system.json")
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

    write_csv(data, report)
    write_markers(data, report)
    write_status(data, report)
    if args.check_animatic:
        check_animatic(data, report)

    n_hero = sum(1 for s in data["shots"] if s.get("hero"))
    report.note(
        f"{len(data['shots'])} shots / {n_hero} hero; "
        "no aerial tours / aggressive shake / env-only cuts"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} shots={len(data['shots'])} "
        f"hero={n_hero} csv={SHOT_CSV.name}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
