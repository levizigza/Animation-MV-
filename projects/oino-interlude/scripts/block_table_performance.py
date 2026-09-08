"""Block SCN_08_TABLE_ROOM performance in four phases.

Phases: Arrival → Pleasure → First Reset → Loss of Spontaneity.
Dread from repetition and missing life — never horror sting / red warning / monster.

Usage:
  python scripts/block_table_performance.py
  python scripts/block_table_performance.py --check-table-room
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

BLOCK_JSON = DOCS_DIR / "table_performance_block.json"
STATUS_MD = DOCS_DIR / "table_performance_block.md"
MARKERS_JSON = DOCS_DIR / "table_performance_markers.json"
TABLE_BRIEF = DOCS_DIR / "table_room_brief.json"
TABLE_MARKERS = DOCS_DIR / "table_room_markers.json"

REQUIRED_PHASE_IDS = (
    "PHASE_1_ARRIVAL",
    "PHASE_2_PLEASURE",
    "PHASE_3_FIRST_RESET",
    "PHASE_4_LOSS_OF_SPONTANEITY",
)

REQUIRED_PRIORITY_IDS = (
    "eyes_eyelines",
    "breathing",
    "fingers_hand_contact",
    "weight_shifts",
    "conceal_reset",
    "father_independent_attention",
    "recognition_own_hand",
)

FORBIDDEN_ANNOUNCEMENTS = (
    "horror_music",
    "red_warning_light",
    "monster_reveal",
)


def load_block() -> dict[str, Any]:
    if not BLOCK_JSON.is_file():
        raise FileNotFoundError(f"Missing {BLOCK_JSON}")
    return json.loads(BLOCK_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("scene") != "SCN_08_TABLE_ROOM":
        errors.append("scene must be SCN_08_TABLE_ROOM")

    policy = data.get("policy") or {}
    for key in FORBIDDEN_ANNOUNCEMENTS:
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    dread = (policy.get("dread_from") or "").lower()
    if "repetition" not in dread or "missing life" not in dread:
        errors.append("policy.dread_from must cite repetition and missing life")
    if policy.get("first_pass_must_feel_safe") is not True:
        errors.append("policy.first_pass_must_feel_safe must be true")
    if policy.get("father_independent_attention_required_before_shadow") is not True:
        errors.append(
            "policy.father_independent_attention_required_before_shadow must be true"
        )

    priorities = data.get("animation_priorities") or []
    pids = [p.get("id") for p in priorities]
    if len(pids) != len(set(pids)):
        errors.append("animation_priorities ids must be unique")
    for req in REQUIRED_PRIORITY_IDS:
        if req not in pids:
            errors.append(f"Missing animation priority: {req}")
    for p in priorities:
        pid = p.get("id", "?")
        if not (p.get("label") or "").strip():
            errors.append(f"{pid}: label required")
        if not (p.get("craft") or "").strip():
            errors.append(f"{pid}: craft required")

    phases = data.get("phases") or []
    if len(phases) != 4:
        errors.append(f"Need exactly 4 phases, found {len(phases)}")
    ids = [ph.get("id") for ph in phases]
    for req in REQUIRED_PHASE_IDS:
        if req not in ids:
            errors.append(f"Missing phase: {req}")

    prev_end = 0
    for ph in phases:
        pid = ph.get("id", "?")
        if not (ph.get("name") or "").strip():
            errors.append(f"{pid}: name required")
        if not (ph.get("emotional_register") or "").strip():
            errors.append(f"{pid}: emotional_register required")
        start = int(ph.get("frame_start") or 0)
        end = int(ph.get("frame_end") or 0)
        if end < start:
            errors.append(f"{pid}: frame_end before frame_start")
        if start < prev_end:
            errors.append(f"{pid}: overlaps previous phase frames")
        prev_end = end
        if not ph.get("must_not"):
            errors.append(f"{pid}: must_not required (forbid scare announcements)")
        must_not_blob = " ".join(ph.get("must_not") or []).lower()
        if ph.get("number") in (3, 4):
            for term in ("horror", "red", "monster"):
                if term not in must_not_blob:
                    errors.append(
                        f"{pid}: must_not should forbid scare path including '{term}'"
                    )
        beats = ph.get("beats") or []
        if not beats:
            errors.append(f"{pid}: at least one beat required")
        beat_ids: list[str] = []
        for b in beats:
            bid = b.get("id", "?")
            beat_ids.append(bid)
            for key in ("marker", "who", "action", "staging"):
                if not (b.get(key) or "").strip():
                    errors.append(f"{bid}: {key} required")
            focus = b.get("priority_focus") or []
            if not focus:
                errors.append(f"{bid}: priority_focus required")
            for f in focus:
                if f not in REQUIRED_PRIORITY_IDS:
                    errors.append(f"{bid}: unknown priority_focus '{f}'")
        if len(beat_ids) != len(set(beat_ids)):
            errors.append(f"{pid}: beat ids must be unique")

    # Phase content anchors from the brief
    phase_by_id = {ph.get("id"): ph for ph in phases}
    p1 = phase_by_id.get("PHASE_1_ARRIVAL") or {}
    p1_actions = " ".join(b.get("action", "") for b in (p1.get("beats") or [])).lower()
    for needle in ("cautious", "mistake"):
        if needle not in p1_actions and needle not in (p1.get("emotional_register") or "").lower():
            # check staging too
            blob = p1_actions + " " + " ".join(
                b.get("staging", "") for b in (p1.get("beats") or [])
            ).lower()
            if needle not in blob and (
                needle != "cautious"
                or "cautious" not in " ".join(
                    b.get("action", "") + " " + b.get("staging", "")
                    for b in (p1.get("beats") or [])
                ).lower()
            ):
                if needle == "mistake" and "mistake" not in blob:
                    errors.append("PHASE_1 must include the familiar musical mistake")
                if needle == "cautious" and "cautious" not in blob:
                    errors.append("PHASE_1 must include Oino entering cautiously")

    p2 = phase_by_id.get("PHASE_2_PLEASURE") or {}
    p2_blob = " ".join(
        (b.get("action", "") + " " + b.get("staging", ""))
        for b in (p2.get("beats") or [])
    ).lower()
    for needle in ("laugh", "sit", "ordinary"):
        if needle not in p2_blob:
            errors.append(f"PHASE_2 must include beat language for '{needle}'")

    p3 = phase_by_id.get("PHASE_3_FIRST_RESET") or {}
    p3_blob = " ".join(
        (b.get("action", "") + " " + b.get("staging", ""))
        for b in (p3.get("beats") or [])
    ).lower()
    for needle in ("leave", "control", "merciful", "precise"):
        if needle not in p3_blob:
            errors.append(f"PHASE_3 must include '{needle}'")

    p4 = phase_by_id.get("PHASE_4_LOSS_OF_SPONTANEITY") or {}
    p4_blob = " ".join(
        (b.get("action", "") + " " + b.get("staging", ""))
        for b in (p4.get("beats") or [])
    ).lower()
    for needle in (
        "pause",
        "disagreement",
        "glance",
        "departure",
        "same frame",
        "independen",
        "own hand",
    ):
        if needle not in p4_blob:
            errors.append(f"PHASE_4 must include '{needle}'")

    return errors


def check_table_room(data: dict[str, Any], report: RunReport) -> list[str]:
    """Optional cross-check against table room brief/markers."""
    notes: list[str] = []
    if not TABLE_BRIEF.is_file():
        report.note("table_room_brief.json not found — skip cross-check detail")
        return notes
    brief = json.loads(TABLE_BRIEF.read_text(encoding="utf-8"))
    if brief.get("scene") != data.get("scene"):
        notes.append(
            f"scene mismatch: block={data.get('scene')} table={brief.get('scene')}"
        )
    cam_ids = {c.get("id") for c in (brief.get("cameras") or [])}
    for ph in data.get("phases") or []:
        for cam in ph.get("camera_bias") or []:
            if cam not in cam_ids:
                notes.append(f"{ph.get('id')}: camera_bias unknown in table room: {cam}")
    father_markers = {
        b.get("marker") for b in (brief.get("father_life_beats") or [])
    }
    event_markers = {e.get("marker") for e in (brief.get("events") or [])}
    known = father_markers | event_markers
    if TABLE_MARKERS.is_file():
        tm = json.loads(TABLE_MARKERS.read_text(encoding="utf-8"))
        known |= {m.get("name") for m in (tm.get("markers") or [])}
    for ph in data.get("phases") or []:
        for b in ph.get("beats") or []:
            link = b.get("link_table_marker")
            if link and link not in known:
                notes.append(f"{b.get('id')}: link_table_marker missing in table room: {link}")
            for link in b.get("link_table_markers") or []:
                if link not in known:
                    notes.append(
                        f"{b.get('id')}: link_table_markers missing in table room: {link}"
                    )
    for n in notes:
        report.fail("cross-check", n)
    if not notes:
        report.note("table room cross-check ok")
    return notes


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = []
    for ph in data.get("phases") or []:
        markers.append(
            {
                "name": f"{ph['id']}_START",
                "frame": ph["frame_start"],
                "phase": ph["id"],
                "note": ph.get("emotional_register"),
            }
        )
        for b in ph.get("beats") or []:
            markers.append(
                {
                    "name": b["marker"],
                    "frame": b["frame"],
                    "phase": ph["id"],
                    "who": b.get("who"),
                    "action": b.get("action"),
                    "priority_focus": b.get("priority_focus"),
                    "note": b.get("staging"),
                }
            )
        markers.append(
            {
                "name": f"{ph['id']}_END",
                "frame": ph["frame_end"],
                "phase": ph["id"],
                "note": f"End {ph.get('name')}",
            }
        )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "dread_from": (data.get("policy") or {}).get("dread_from"),
        "forbidden": {
            k: False for k in FORBIDDEN_ANNOUNCEMENTS
        },
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/table_performance_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    lines = [
        "# Table performance block — SCN_08_TABLE_ROOM",
        "",
        f"**Throughline:** {data.get('throughline')}  ",
        f"**Dread from:** {policy.get('dread_from')}",
        "",
        "## Hard rules",
        "",
        f"- Horror music: `{policy.get('horror_music')}`",
        f"- Red warning light: `{policy.get('red_warning_light')}`",
        f"- Monster reveal: `{policy.get('monster_reveal')}`",
        f"- First pass must feel safe: `{policy.get('first_pass_must_feel_safe')}`",
        f"- Shadow is: {policy.get('shadow_is')}",
        "",
        "## Animation priorities",
        "",
    ]
    for p in data.get("animation_priorities") or []:
        lines.append(f"- **{p['label']}** (`{p['id']}`): {p['craft']}")
    lines += ["", "## Phases", ""]
    for ph in data.get("phases") or []:
        lines += [
            f"### Phase {ph['number']} — {ph['name']}",
            "",
            f"**Frames:** {ph['frame_start']}–{ph['frame_end']}  ",
            f"**Register:** {ph.get('emotional_register')}  ",
            f"**Cameras:** " + ", ".join(f"`{c}`" for c in (ph.get("camera_bias") or [])),
            "",
            "| Frame | Marker | Who | Action |",
            "|-------|--------|-----|--------|",
        ]
        for b in ph.get("beats") or []:
            lines.append(
                f"| {b['frame']} | `{b['marker']}` | {b['who']} | {b['action']} |"
            )
        lines += ["", "**Must preserve**", ""]
        for item in ph.get("must_preserve") or []:
            lines.append(f"- {item}")
        lines += ["", "**Must not**", ""]
        for item in ph.get("must_not") or []:
            lines.append(f"- {item}")
        lines.append("")
    vn = data.get("version_notes") or {}
    if vn:
        lines += ["## Pass versions", ""]
        for key, note in vn.items():
            lines.append(f"- **{key}:** {note}")
        lines.append("")
    lines += [
        "## Rebuild",
        "",
        "```text",
        "python scripts/block_table_performance.py",
        "python scripts/block_table_performance.py --check-table-room",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/table_performance_block.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Block table performance in four phases"
    )
    parser.add_argument(
        "--check-table-room",
        action="store_true",
        help="Cross-check camera/marker links against table room brief",
    )
    args = parser.parse_args()

    report = RunReport(script="block_table_performance", seed=20261210)
    try:
        data = load_block()
        report.mark("reused", "docs/table_performance_block.json")
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

    if args.check_table_room:
        check_table_room(data, report)

    report.note(
        "Four phases blocked; dread=repetition/missing life; "
        "no horror music / red warning / monster reveal"
    )
    report.write(REPORTS_DIR)
    n_beats = sum(len(ph.get("beats") or []) for ph in data.get("phases") or [])
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"phases={len(data['phases'])} beats={n_beats} "
        f"priorities={len(data['animation_priorities'])}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
