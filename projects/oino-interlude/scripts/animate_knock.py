"""Animate the knock that breaks the table's artificial rhythm.

Source stays uncertain until the reflection reveals the sister.
Cost already exists — not a hypothetical later warning. No jump scare.

Usage:
  python scripts/animate_knock.py
  python scripts/animate_knock.py --check-links
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

KNOCK_JSON = DOCS_DIR / "knock_animation.json"
STATUS_MD = DOCS_DIR / "knock_animation.md"
MARKERS_JSON = DOCS_DIR / "knock_markers.json"
TABLE_BRIEF = DOCS_DIR / "table_room_brief.json"
CALL_MOTIF = DOCS_DIR / "call_to_dinner_motif.json"
PERF_BLOCK = DOCS_DIR / "table_performance_block.json"

REQUIRED_SOURCE_IDS = (
    "SRC_SISTER_TAP_DOWNSTAIRS",
    "SRC_ATTIC_DOOR",
    "SRC_BOWL_TABLE",
    "SRC_MACHINE_MELODY",
    "SRC_ZONE_FORCE",
)

REQUIRED_REFL_IDS = (
    "REFL_SISTER_WAITING",
    "REFL_TWO_BOWLS",
    "REFL_UNTOUCHED_PLACE",
    "REFL_SISTER_EATS_ALONE",
)

REQUIRED_OINO_STAGES = (
    "OINO_KNOCK_1_IGNORE",
    "OINO_KNOCK_2_RECOGNIZES_FAILURE",
    "OINO_KNOCK_3_HAND_REMAINS",
)


def load_knock() -> dict[str, Any]:
    if not KNOCK_JSON.is_file():
        raise FileNotFoundError(f"Missing {KNOCK_JSON}")
    return json.loads(KNOCK_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("scene") != "SCN_08_TABLE_ROOM":
        errors.append("scene must be SCN_08_TABLE_ROOM")

    policy = data.get("policy") or {}
    for key in ("jump_scare", "horror_music_sting", "monster_reveal"):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    if policy.get("source_certain_before_reflection") is not False:
        errors.append("policy.source_certain_before_reflection must be false")
    if policy.get("cost_is_hypothetical_warning") is not False:
        errors.append("policy.cost_is_hypothetical_warning must be false")
    if policy.get("cost_already_exists") is not True:
        errors.append("policy.cost_already_exists must be true")
    if policy.get("breaks_artificial_rhythm") is not True:
        errors.append("policy.breaks_artificial_rhythm must be true")

    sources = data.get("possible_sources") or []
    sids = [s.get("id") for s in sources]
    if len(sids) != len(set(sids)):
        errors.append("possible_sources ids must be unique")
    for req in REQUIRED_SOURCE_IDS:
        if req not in sids:
            errors.append(f"Missing possible source: {req}")
    for s in sources:
        sid = s.get("id", "?")
        if not (s.get("label") or "").strip():
            errors.append(f"{sid}: label required")
        if s.get("confirmed_before_reflection") is not False:
            errors.append(f"{sid}: confirmed_before_reflection must be false")

    reveal = data.get("source_reveal") or {}
    if reveal.get("when") != "reflection_reveals_sister":
        errors.append("source_reveal.when must be reflection_reveals_sister")
    if reveal.get("confirmed_source") != "SRC_SISTER_TAP_DOWNSTAIRS":
        errors.append(
            "source_reveal.confirmed_source must be SRC_SISTER_TAP_DOWNSTAIRS"
        )

    knock = data.get("knock") or {}
    if not knock.get("marker") or knock.get("frame") is None:
        errors.append("knock.marker and knock.frame required")
    rhythm = knock.get("rhythm") or {}
    if not rhythm.get("pattern"):
        errors.append("knock.rhythm.pattern required")
    avoid = " ".join(knock.get("avoid") or []).lower()
    if "jump" not in avoid and "scare" not in avoid:
        errors.append("knock.avoid must forbid jump-scare staging")

    refl = data.get("reflection_animation") or {}
    if refl.get("surface") != "PROP_ReflectiveSurface_Sister":
        errors.append("reflection_animation.surface must be PROP_ReflectiveSurface_Sister")
    if refl.get("camera") != "CAM_TABLE_REFLECTION":
        errors.append("reflection_animation.camera must be CAM_TABLE_REFLECTION")
    beats = refl.get("beats") or []
    bids = [b.get("id") for b in beats]
    for req in REQUIRED_REFL_IDS:
        if req not in bids:
            errors.append(f"Missing reflection beat: {req}")
    required_images = {
        "REFL_SISTER_WAITING": "waiting",
        "REFL_TWO_BOWLS": "two bowls",
        "REFL_UNTOUCHED_PLACE": "untouched",
        "REFL_SISTER_EATS_ALONE": "alone",
    }
    by_id = {b.get("id"): b for b in beats}
    for rid, needle in required_images.items():
        img = ((by_id.get(rid) or {}).get("image") or "").lower()
        if needle not in img:
            errors.append(f"{rid}: image must include '{needle}'")
        if not (by_id.get(rid) or {}).get("staging"):
            errors.append(f"{rid}: staging required")

    stages = data.get("oino_stages") or []
    if len(stages) != 3:
        errors.append(f"Need exactly 3 oino_stages, found {len(stages)}")
    stids = [s.get("id") for s in stages]
    for req in REQUIRED_OINO_STAGES:
        if req not in stids:
            errors.append(f"Missing Oino stage: {req}")
    for s in stages:
        sid = s.get("id", "?")
        for key in ("marker", "action", "staging", "cost_read"):
            if not (s.get(key) or "").strip():
                errors.append(f"{sid}: {key} required")
        if not isinstance(s.get("body"), dict) or not s.get("body"):
            errors.append(f"{sid}: body craft object required")
        cost = (s.get("cost_read") or "").lower()
        if "later" in cost and "not later" not in cost and "not a" not in cost:
            # allow explicit rejection of later; flag soft hypotheticals
            if "might" in cost or "will happen" in cost:
                errors.append(f"{sid}: cost_read must not be a later hypothetical")

    # Stage action anchors
    stage_blob = {
        s.get("id"): ((s.get("action") or "") + " " + (s.get("staging") or "")).lower()
        for s in stages
    }
    if "ignore" not in stage_blob.get("OINO_KNOCK_1_IGNORE", ""):
        errors.append("Stage 1 must include trying to ignore the interrupt")
    s2 = stage_blob.get("OINO_KNOCK_2_RECOGNIZES_FAILURE", "")
    if "sister" not in s2 or "ancestor" not in s2 and "failure" not in s2:
        if "failure" not in s2:
            errors.append("Stage 2 must recognize ancestor failure via sister")
    if "ancestor" not in s2:
        errors.append("Stage 2 must name the ancestor's failure")
    s3 = stage_blob.get("OINO_KNOCK_3_HAND_REMAINS", "")
    if "hand" not in s3 or "control" not in s3:
        errors.append("Stage 3 must keep her hand on the control")
    if "stay" not in s3 and "want" not in s3:
        errors.append("Stage 3 must keep wanting the father to stay")

    if not data.get("must_not"):
        errors.append("must_not required")
    must_not = " ".join(data.get("must_not") or []).lower()
    for term in ("jump scare", "hypothetical", "before reflection"):
        # "before reflection" appears in "Confirm source before reflection"
        if term == "before reflection" and "before reflection" not in must_not:
            errors.append("must_not should forbid confirming source before reflection")
        elif term == "jump scare" and "jump scare" not in must_not:
            errors.append("must_not should forbid jump scare")
        elif term == "hypothetical" and "hypothetical" not in must_not and "later" not in must_not:
            errors.append("must_not should forbid hypothetical later warning")

    return errors


def check_links(data: dict[str, Any], report: RunReport) -> None:
    if TABLE_BRIEF.is_file():
        brief = json.loads(TABLE_BRIEF.read_text(encoding="utf-8"))
        cams = {c.get("id") for c in (brief.get("cameras") or [])}
        elems = brief.get("elements") or {}
        refl_objs = set(elems.get("reflective_surface_sister_downstairs") or [])
        surface = (data.get("reflection_animation") or {}).get("surface")
        camera = (data.get("reflection_animation") or {}).get("camera")
        if camera and camera not in cams:
            report.fail("link", f"camera not in table room: {camera}")
        if surface and surface not in refl_objs and surface not in {
            o for vals in elems.values() for o in (vals or [])
        }:
            report.fail("link", f"reflection surface not in table room: {surface}")
        report.note("table room reflection/camera links checked")
    else:
        report.note("table_room_brief.json missing — skip table links")

    if CALL_MOTIF.is_file():
        motif = json.loads(CALL_MOTIF.read_text(encoding="utf-8"))
        if (motif.get("policy") or {}).get("jump_scare") is not False:
            report.fail("link", "call_to_dinner_motif allows jump_scare")
        ids = {a.get("id") for a in (motif.get("appearances") or [])}
        if "CALL_05_ZONE_KNOCK" not in ids:
            report.fail("link", "CALL_05_ZONE_KNOCK missing from call motif")
        else:
            report.note("call motif jump_scare=false; CALL_05 present")
    else:
        report.note("call_to_dinner_motif.json missing — skip motif links")

    if PERF_BLOCK.is_file():
        perf = json.loads(PERF_BLOCK.read_text(encoding="utf-8"))
        # Knock should land during/after artificial rhythm (phase 4)
        p4 = next(
            (
                ph
                for ph in (perf.get("phases") or [])
                if ph.get("id") == "PHASE_4_LOSS_OF_SPONTANEITY"
            ),
            None,
        )
        knock_frame = int((data.get("knock") or {}).get("frame") or 0)
        if p4:
            start = int(p4.get("frame_start") or 0)
            end = int(p4.get("frame_end") or 0)
            if knock_frame < start:
                report.fail(
                    "link",
                    f"knock frame {knock_frame} before Phase 4 artificial rhythm "
                    f"({start}-{end})",
                )
            else:
                report.note(
                    f"knock f{knock_frame} lands in/after Phase 4 "
                    f"({start}-{end}) — breaks artificial rhythm"
                )
    else:
        report.note("table_performance_block.json missing — skip phase link")


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = [
        {
            "name": data["knock"]["marker"],
            "frame": data["knock"]["frame"],
            "note": data["knock"]["rhythm"].get("pattern"),
            "kind": "knock_interrupt",
        }
    ]
    for s in data.get("oino_stages") or []:
        markers.append(
            {
                "name": s["marker"],
                "frame": s["frame"],
                "stage": s["number"],
                "action": s["action"],
                "note": s.get("staging"),
                "cost_read": s.get("cost_read"),
            }
        )
    for b in (data.get("reflection_animation") or {}).get("beats") or []:
        markers.append(
            {
                "name": b["marker"],
                "frame": b["frame"],
                "image": b["image"],
                "note": b.get("staging"),
                "kind": "reflection",
            }
        )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "jump_scare": False,
        "cost_already_exists": True,
        "source_uncertain_until_reflection": True,
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/knock_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    knock = data["knock"]
    refl = data["reflection_animation"]
    lines = [
        "# Knock animation — SCN_08_TABLE_ROOM",
        "",
        f"**Throughline:** {data.get('throughline')}",
        "",
        "## Hard rules",
        "",
        f"- Jump scare: `{policy.get('jump_scare')}`",
        f"- Source certain before reflection: `{policy.get('source_certain_before_reflection')}`",
        f"- Cost already exists: `{policy.get('cost_already_exists')}`",
        f"- Hypothetical later warning: `{policy.get('cost_is_hypothetical_warning')}`",
        f"- Breaks artificial rhythm: `{policy.get('breaks_artificial_rhythm')}`",
        "",
        "## Knock",
        "",
        f"- Marker: `{knock.get('marker')}` @ f{knock.get('frame')}",
        f"- Pattern: {knock.get('rhythm', {}).get('pattern')}",
        f"- Avoid: " + "; ".join(knock.get("avoid") or []),
        "",
        "## Possible sources (uncertain until reflection)",
        "",
    ]
    for s in data.get("possible_sources") or []:
        lines.append(f"- `{s['id']}` — {s['label']}")
    reveal = data.get("source_reveal") or {}
    lines += [
        "",
        f"**Reveal:** {reveal.get('when')} → `{reveal.get('confirmed_source')}`",
        "",
        "## Reflection",
        "",
        f"- Surface: `{refl.get('surface')}`  ",
        f"- Camera: `{refl.get('camera')}`  ",
        f"- Frames: {refl.get('frames', {}).get('start')}–{refl.get('frames', {}).get('end')}",
        "",
        "| Frame | Marker | Image |",
        "|-------|--------|-------|",
    ]
    for b in refl.get("beats") or []:
        lines.append(f"| {b['frame']} | `{b['marker']}` | {b['image']} |")
    lines += ["", "## Oino — three stages", ""]
    for s in data.get("oino_stages") or []:
        lines += [
            f"### {s['number']}. {s['action']}",
            "",
            f"- Marker: `{s['marker']}` @ f{s['frame']}",
            f"- Staging: {s.get('staging')}",
            f"- Cost: {s.get('cost_read')}",
            "",
        ]
    lines += ["## Must preserve", ""]
    for item in data.get("must_preserve") or []:
        lines.append(f"- {item}")
    lines += ["", "## Must not", ""]
    for item in data.get("must_not") or []:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/animate_knock.py",
        "python scripts/animate_knock.py --check-links",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/knock_animation.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Animate knock interrupt at the controlled table"
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Cross-check table room, call motif, and Phase 4 timing",
    )
    args = parser.parse_args()

    report = RunReport(script="animate_knock", seed=20261210)
    try:
        data = load_knock()
        report.mark("reused", "docs/knock_animation.json")
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
    if args.check_links:
        check_links(data, report)

    report.note(
        "Knock breaks artificial rhythm; source uncertain until sister in reflection; "
        "cost already exists; no jump scare"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"sources={len(data['possible_sources'])} "
        f"refl_beats={len(data['reflection_animation']['beats'])} "
        f"oino_stages={len(data['oino_stages'])}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
