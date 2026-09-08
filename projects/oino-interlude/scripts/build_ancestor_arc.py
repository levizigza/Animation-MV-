"""Build the ancestor arc: watcher -> incomplete warning.

Validates eight beats, the unedited dinner-call camera clip, and writes
continuity docs + markers. Not an omniscient prophet or supernatural judge.

Usage:
  python scripts/build_ancestor_arc.py
  python scripts/build_ancestor_arc.py --list
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
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR  # noqa: E402

ARC_JSON = DOCS_DIR / "ancestor_arc.json"
TRACKING_MD = DOCS_DIR / "ancestor_arc.md"
MARKERS_JSON = DOCS_DIR / "ancestor_arc_markers.json"
CLIP_BRIEF = DOCS_DIR / "ancestor_dinner_camera_clip.md"

REQUIRED_BEAT_IDS = (
    "ANC_01_NOTICES_CHANGE",
    "ANC_02_MENDS_SLEEVE",
    "ANC_03_COAT_CATCHES",
    "ANC_04_WATCHES_ASK",
    "ANC_05_FOLLOWS_MELODY",
    "ANC_06_PRESERVES_THROUGH_CALL",
    "ANC_07_CANNOT_TELL_TRUE",
    "ANC_08_ZONE_EXIT_NO_CERTAINTY",
)

REQUIRED_VISUALS = (
    "reflections",
    "partial faces",
    "damaged film",
    "documents",
    "reconstructed images",
    "out-of-focus movement",
)


def load_arc() -> dict[str, Any]:
    if not ARC_JSON.is_file():
        raise FileNotFoundError(f"Missing {ARC_JSON}")
    return json.loads(ARC_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    char = data.get("character") or {}
    if (char.get("starts_as") or "").lower() != "watcher":
        errors.append("character.starts_as must be watcher")
    if (char.get("ends_as") or "").lower() != "incomplete warning":
        errors.append("character.ends_as must be incomplete warning")

    policy = data.get("policy") or {}
    for key in (
        "omniscient_prophet",
        "supernatural_judge",
        "simple_anti_ambition_sermon",
    ):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")

    visuals = [v.lower() for v in (data.get("visual_language") or [])]
    for req in REQUIRED_VISUALS:
        if req not in visuals:
            errors.append(f"visual_language missing '{req}'")

    beats = data.get("beats") or []
    if len(beats) != 8:
        errors.append(f"Need exactly 8 beats, found {len(beats)}")
    ids = [b.get("id") for b in beats]
    if len(ids) != len(set(ids)):
        errors.append("beat ids must be unique")
    for req in REQUIRED_BEAT_IDS:
        if req not in ids:
            errors.append(f"Missing beat: {req}")
    for b in beats:
        bid = b.get("id", "?")
        for field in ("action", "staging", "watcher_mode", "implication", "marker"):
            if not (b.get(field) or "").strip():
                errors.append(f"{bid}: missing {field}")

    # Arc ends incomplete
    last = sorted(beats, key=lambda x: int(x.get("order", 0)))[-1] if beats else {}
    if last.get("id") != "ANC_08_ZONE_EXIT_NO_CERTAINTY":
        errors.append("Final beat must be ANC_08_ZONE_EXIT_NO_CERTAINTY")
    if "certainty" not in (last.get("action") or "").lower() and "no certainty" not in (
        last.get("action") or ""
    ).lower():
        if "certainty" not in (last.get("action") or "").lower():
            errors.append("Final beat must offer no certainty")

    clip = data.get("unedited_archive_clip") or {}
    if not clip:
        errors.append("unedited_archive_clip required")
    else:
        if clip.get("footage_class") != "ancestor_origin":
            errors.append("clip.footage_class must be ancestor_origin")
        if clip.get("not_footage_class") != "reconstructed":
            errors.append("clip must be distinguished from reconstructed footage")
        tone = [t.lower() for t in (clip.get("emotional_tone") or [])]
        if "ordinary" not in tone or "embarrassing" not in " ".join(tone):
            errors.append("clip must be ordinary and slightly embarrassing")
        action = clip.get("action") or {}
        if "adjust" not in (action.get("on_screen") or "").lower():
            errors.append("clip on_screen must include adjusting the camera")
        if "dinner" not in (action.get("off_screen") or "").lower():
            errors.append("clip off_screen must include a dinner call")
        if "preserve" not in (clip.get("reveals") or "").lower():
            errors.append("clip.reveals must state participation in preserving everything")
        forb = " ".join(clip.get("he_does_not") or []).lower()
        if "prophet" not in forb and "sermon" not in forb:
            errors.append("clip.he_does_not should block sermon/prophet staging")

    return errors


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = []
    for b in sorted(data["beats"], key=lambda x: int(x["order"])):
        markers.append(
            {
                "name": b["marker"],
                "frame": b.get("approx_frame"),
                "shot": b.get("approx_shot"),
                "order": b["order"],
                "watcher_mode": b.get("watcher_mode"),
                "note": b.get("action"),
            }
        )
    clip = data["unedited_archive_clip"]
    craft = clip.get("craft") or {}
    markers.append(
        {
            "name": craft.get("marker_start"),
            "frame": craft.get("approx_frame_start"),
            "kind": "archive_clip",
            "clip_id": clip["id"],
            "note": "Unedited dinner-call camera fidget starts",
        }
    )
    markers.append(
        {
            "name": craft.get("marker_end"),
            "frame": craft.get("approx_frame_end"),
            "kind": "archive_clip",
            "clip_id": clip["id"],
            "note": "Clip ends; still no dinner answer",
        }
    )
    out = {
        "schema_version": 1,
        "editable": True,
        "starts_as": "watcher",
        "ends_as": "incomplete warning",
        "no_omniscient_prophet": True,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/ancestor_arc_markers.json")
    return MARKERS_JSON


def write_clip_brief(data: dict[str, Any], report: RunReport) -> Path:
    clip = data["unedited_archive_clip"]
    craft = clip.get("craft") or {}
    action = clip.get("action") or {}
    lines = [
        "# Unedited archive clip - dinner call while adjusting camera",
        "",
        f"**Id:** `{clip['id']}`  ",
        f"**Footage class:** `{clip['footage_class']}` (not `{clip['not_footage_class']}`)",
        f"**Tone:** {', '.join(clip.get('emotional_tone') or [])}",
        f"**Target duration:** ~{clip.get('duration_seconds_target')}s",
        "",
        "## Action",
        "",
        f"- **On screen:** {action.get('on_screen')}",
        f"- **Off screen:** {action.get('off_screen')}",
        "",
        "## He does not",
        "",
    ]
    for item in clip.get("he_does_not") or []:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Reveals",
        "",
        clip.get("reveals", ""),
        "",
        "## Craft look",
        "",
    ]
    for look in craft.get("look") or []:
        lines.append(f"- {look}")
    lines += [
        "",
        "## Objects / labels",
        "",
    ]
    for obj in craft.get("objects") or []:
        lines.append(f"- `{obj}`")
    lines += [
        "",
        f"**Markers:** `{craft.get('marker_start')}` -> `{craft.get('marker_end')}` "
        f"(f{craft.get('approx_frame_start')}–{craft.get('approx_frame_end')})",
        "",
        f"Linked call motif: `{clip.get('link_to_call_motif')}`",
        "",
    ]
    CLIP_BRIEF.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/ancestor_dinner_camera_clip.md")
    return CLIP_BRIEF


def write_tracking_md(data: dict[str, Any], report: RunReport) -> Path:
    char = data["character"]
    policy = data["policy"]
    lines = [
        "# Ancestor arc - watcher to incomplete warning",
        "",
        f"**Starts as:** {char.get('starts_as')}  ",
        f"**Ends as:** {char.get('ends_as')}  ",
        f"**Qualities:** {', '.join(char.get('qualities') or [])}",
        "",
        "## Hard rules",
        "",
        f"- Omniscient prophet: `{policy.get('omniscient_prophet')}`",
        f"- Supernatural judge: `{policy.get('supernatural_judge')}`",
        f"- Simple anti-ambition sermon: `{policy.get('simple_anti_ambition_sermon')}`",
        "",
        policy.get("note", ""),
        "",
        "## Visual language",
        "",
    ]
    for v in data.get("visual_language") or []:
        lines.append(f"- {v}")
    lines += [
        "",
        "## Beats",
        "",
        "| # | Id | Action | Mode | Implication |",
        "|---|----|--------|------|-------------|",
    ]
    for b in sorted(data["beats"], key=lambda x: int(x["order"])):
        lines.append(
            f"| {b['order']} | `{b['id']}` | {b['action']} | {b['watcher_mode']} | {b['implication']} |"
        )
    lines += [
        "",
        "## Per-beat staging",
        "",
    ]
    for b in sorted(data["beats"], key=lambda x: int(x["order"])):
        lines += [
            f"### {b['order']}. `{b['id']}` - {b.get('title')}",
            "",
            f"- **Shot / frame:** `{b.get('approx_shot')}` / f{b.get('approx_frame')}",
            f"- **Marker:** `{b.get('marker')}`",
            f"- **Staging:** {b.get('staging')}",
            "",
        ]

    clip = data["unedited_archive_clip"]
    lines += [
        "## Key clip",
        "",
        f"See [`ancestor_dinner_camera_clip.md`](ancestor_dinner_camera_clip.md) "
        f"(`{clip['id']}`).",
        "",
        "## Continuity checklist",
        "",
        "- [ ] Beauty and danger noticed without prophetic voice-over.",
        "- [ ] Sleeve mend and coat catch stay mutual, ordinary, slightly awkward.",
        "- [ ] Melody pull leaves the asking worker unanswered.",
        "- [ ] Dinner-call camera clip is embarrassing, not sermonizing.",
        "- [ ] He cannot name the true recording; Zone exit offers no certainty.",
        "- [ ] Ancestor-origin vs reconstructed footage stay visually distinct.",
        "",
        "## Sources",
        "",
        "- [`ancestor_arc.json`](ancestor_arc.json)",
        "- [`ancestor_arc_markers.json`](ancestor_arc_markers.json)",
        "",
        "```text",
        "python scripts/build_ancestor_arc.py",
        "```",
        "",
    ]
    TRACKING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/ancestor_arc.md")
    return TRACKING_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Ancestor arc builder")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_ancestor_arc", seed=20261210)
    try:
        data = load_arc()
        report.mark("reused", "docs/ancestor_arc.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("arc_json", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    if args.list:
        for b in sorted(data["beats"], key=lambda x: int(x["order"])):
            print(f"{b['order']}. {b['id']} - {b['action']}")
        print(f"CLIP {data['unedited_archive_clip']['id']}")
        return 0

    write_markers(data, report)
    write_clip_brief(data, report)
    write_tracking_md(data, report)
    report.note(
        "Ancestor: watcher -> incomplete warning; "
        "dinner-cam clip shows desire to preserve everything"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} beats=8 "
        f"clip={data['unedited_archive_clip']['id']} "
        f"doc={TRACKING_MD.relative_to(PROJECT_ROOT).as_posix()}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
