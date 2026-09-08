"""Animate the holy-fool turning — release what she still wants.

Ancestor at the exit: no explanation, no guarantee of return.
Ordinary and costly. No cosmic reward, explosion, or proof the world is saved.
At most one optional Dionysian release image unless the animatic proves more helps.

Usage:
  python scripts/animate_holy_fool_turning.py
  python scripts/animate_holy_fool_turning.py --check-links
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

HF_JSON = DOCS_DIR / "holy_fool_turning.json"
STATUS_MD = DOCS_DIR / "holy_fool_turning.md"
MARKERS_JSON = DOCS_DIR / "holy_fool_turning_markers.json"
ANCESTOR_ARC = DOCS_DIR / "ancestor_arc.json"
TABLE_BRIEF = DOCS_DIR / "table_room_brief.json"
KNOCK_JSON = DOCS_DIR / "knock_animation.json"
DION_JSON = DOCS_DIR / "dionysus_presence.json"
ANIMATIC = DOCS_DIR / "animatic_shot_list.json"

REQUIRED_BEAT_IDS = (
    "HF_LOOK_ANCESTOR_TO_FATHER",
    "HF_FATHER_TENDER_PERSONAL",
    "HF_ANCESTOR_NOT_ORACLE",
    "HF_RELEASE_CONTROL",
    "HF_SEQUENCE_FORWARD",
    "HF_FATHER_FINISHES_MELODY",
    "HF_FATHER_STANDS_LEAVES",
    "HF_LISTEN_SOUND_AND_SILENCE",
    "HF_CARRY_RECORDING_OUT",
    "HF_LOOK_BACK_THRESHOLD",
)

REQUIRED_RELEASE_OPTIONS = (
    "REL_VINE_LOOSENS",
    "REL_DUST_TO_WHITE_BIRDS",
    "REL_RED_REFLECTION_BREAKS",
    "REL_RHYTHM_BECOMES_BREATH",
)

FORBIDDEN = (
    "cosmic_reward",
    "explosion",
    "proof_world_saved",
    "ancestor_as_oracle",
    "guarantee_of_return",
    "father_as_monster",
)


def load_hf() -> dict[str, Any]:
    if not HF_JSON.is_file():
        raise FileNotFoundError(f"Missing {HF_JSON}")
    return json.loads(HF_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("scene") != "SCN_08_TABLE_ROOM":
        errors.append("scene must be SCN_08_TABLE_ROOM")

    policy = data.get("policy") or {}
    for key in FORBIDDEN:
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    action = (policy.get("holy_fool_action") or "").lower()
    if "leave" not in action or "want" not in action:
        errors.append(
            "policy.holy_fool_action must be allowing father to leave while wanting him to stay"
        )
    quality = (policy.get("action_quality") or "").lower()
    if "ordinary" not in quality or "costly" not in quality:
        errors.append("policy.action_quality must be ordinary and costly")

    anc = data.get("ancestor_at_exit") or {}
    if not (anc.get("marker") and anc.get("frame") is not None):
        errors.append("ancestor_at_exit.marker and frame required")
    offers = anc.get("offers") or {}
    if offers.get("explanation") is not False:
        errors.append("ancestor_at_exit.offers.explanation must be false")
    if offers.get("guarantee_oino_can_return") is not False:
        errors.append("ancestor_at_exit.offers.guarantee_oino_can_return must be false")
    if anc.get("link_ancestor_beat") != "ANC_08_ZONE_EXIT_NO_CERTAINTY":
        errors.append("ancestor_at_exit must link ANC_08_ZONE_EXIT_NO_CERTAINTY")

    beats = data.get("beats") or []
    ids = [b.get("id") for b in beats]
    if len(ids) != len(set(ids)):
        errors.append("beat ids must be unique")
    for req in REQUIRED_BEAT_IDS:
        if req not in ids:
            errors.append(f"Missing beat: {req}")
    hinge_count = 0
    prev_frame = -1
    for b in beats:
        bid = b.get("id", "?")
        for key in ("marker", "who", "action", "staging"):
            if not (b.get(key) or "").strip():
                errors.append(f"{bid}: {key} required")
        frame = int(b.get("frame") or 0)
        if frame <= prev_frame:
            errors.append(f"{bid}: frames must increase")
        prev_frame = frame
        if b.get("holy_fool_hinge"):
            hinge_count += 1
    if hinge_count != 1:
        errors.append("Exactly one beat must set holy_fool_hinge true (release control)")
    release = next((b for b in beats if b.get("id") == "HF_RELEASE_CONTROL"), None)
    if release and not release.get("holy_fool_hinge"):
        errors.append("HF_RELEASE_CONTROL must be the holy_fool_hinge")

    # Action language anchors
    by_id = {b.get("id"): b for b in beats}
    checks = {
        "HF_LOOK_ANCESTOR_TO_FATHER": ("ancestor", "father"),
        "HF_FATHER_TENDER_PERSONAL": ("tender",),
        "HF_ANCESTOR_NOT_ORACLE": ("oracle",),
        "HF_RELEASE_CONTROL": ("releas", "control"),
        "HF_SEQUENCE_FORWARD": ("forward",),
        "HF_FATHER_FINISHES_MELODY": ("finish", "melody"),
        "HF_FATHER_STANDS_LEAVES": ("stand", "leav"),
        "HF_LISTEN_SOUND_AND_SILENCE": ("listen", "silence"),
        "HF_CARRY_RECORDING_OUT": ("carry", "record"),
        "HF_LOOK_BACK_THRESHOLD": ("look back", "threshold"),
    }
    for bid, needles in checks.items():
        blob = (
            ((by_id.get(bid) or {}).get("action") or "")
            + " "
            + ((by_id.get(bid) or {}).get("staging") or "")
        ).lower()
        for n in needles:
            if n not in blob:
                errors.append(f"{bid}: action/staging must include '{n}'")

    dion = data.get("dionysian_release") or {}
    if dion.get("optional") is not True:
        errors.append("dionysian_release.optional must be true")
    if dion.get("explain") is not False:
        errors.append("dionysian_release.explain must be false")
    if int(dion.get("max_images_in_final_shot") or 0) != 1:
        errors.append("dionysian_release.max_images_in_final_shot must be 1")
    if "animatic" not in (dion.get("additional_only_if") or "").lower():
        errors.append(
            "dionysian_release.additional_only_if must require animatic proof for more images"
        )
    opts = dion.get("options") or []
    oids = [o.get("id") for o in opts]
    for req in REQUIRED_RELEASE_OPTIONS:
        if req not in oids:
            errors.append(f"Missing Dionysian release option: {req}")
    default = dion.get("default_choice")
    if default not in oids:
        errors.append("dionysian_release.default_choice must be one of the options")

    must_not = " ".join(data.get("must_not") or []).lower()
    for term in ("cosmic", "explosion", "world has been saved", "oracle"):
        if term not in must_not:
            errors.append(f"must_not should forbid path including '{term}'")

    return errors


def check_links(data: dict[str, Any], report: RunReport) -> None:
    if ANCESTOR_ARC.is_file():
        arc = json.loads(ANCESTOR_ARC.read_text(encoding="utf-8"))
        ids = {b.get("id") for b in (arc.get("beats") or [])}
        link = (data.get("ancestor_at_exit") or {}).get("link_ancestor_beat")
        if link not in ids:
            report.fail("link", f"ancestor beat missing: {link}")
        else:
            report.note(f"ancestor link ok: {link}")
        if (arc.get("policy") or {}).get("omniscient_prophet") is not False:
            report.fail("link", "ancestor_arc allows omniscient_prophet")
    else:
        report.note("ancestor_arc.json missing — skip ancestor link")

    if TABLE_BRIEF.is_file():
        brief = json.loads(TABLE_BRIEF.read_text(encoding="utf-8"))
        cams = {c.get("id") for c in (brief.get("cameras") or [])}
        for need in (
            "CAM_TABLE_OINO_CONTROL",
            "CAM_TABLE_FATHER_LEAVING",
            "CAM_TABLE_DOORWAY_LOOKBACK",
        ):
            if need not in cams:
                report.fail("link", f"table camera missing: {need}")
        report.note("table room cameras for release/leave/lookback ok")
    else:
        report.note("table_room_brief.json missing — skip camera links")

    if KNOCK_JSON.is_file():
        knock = json.loads(KNOCK_JSON.read_text(encoding="utf-8"))
        stages = knock.get("oino_stages") or []
        last = max((int(s.get("frame") or 0) for s in stages), default=0)
        first_hf = int((data.get("ancestor_at_exit") or {}).get("frame") or 0)
        if first_hf <= last:
            report.fail(
                "link",
                f"holy-fool start f{first_hf} must follow knock stages (last f{last})",
            )
        else:
            report.note(f"holy-fool f{first_hf} follows knock (last f{last})")
    else:
        report.note("knock_animation.json missing — skip knock order link")

    if ANIMATIC.is_file():
        anim = json.loads(ANIMATIC.read_text(encoding="utf-8"))
        shot_id = data.get("approx_animatic_shot")
        shot = next(
            (s for s in (anim.get("shots") or []) if s.get("id") == shot_id),
            None,
        )
        if not shot:
            report.fail("link", f"animatic shot missing: {shot_id}")
        else:
            beat = (shot.get("beat") or "").lower()
            if "releas" not in beat and "holy" not in beat:
                report.fail("link", f"{shot_id} beat should describe release/holy-fool")
            else:
                report.note(f"animatic {shot_id} linked")
    else:
        report.note("animatic_shot_list.json missing — skip animatic link")

    if DION_JSON.is_file():
        dion = json.loads(DION_JSON.read_text(encoding="utf-8"))
        echo_id = (data.get("dionysian_release") or {}).get("link_echo")
        echoes = dion.get("echoes") or dion.get("echo_map") or []
        if isinstance(echoes, dict):
            found = echo_id in echoes
        else:
            found = any(e.get("id") == echo_id for e in echoes)
        if echo_id and not found:
            report.note(
                f"dionysus_presence.json present but {echo_id} not found as structured echo — md map remains craft authority"
            )
        elif echo_id:
            report.note(f"dionysus presence link noted: {echo_id}")
    else:
        report.note("dionysus_presence.json missing — default birds image still valid via map")


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = [
        {
            "name": data["ancestor_at_exit"]["marker"],
            "frame": data["ancestor_at_exit"]["frame"],
            "note": data["ancestor_at_exit"].get("staging"),
            "offers_explanation": False,
            "guarantee_return": False,
        }
    ]
    for b in data.get("beats") or []:
        markers.append(
            {
                "name": b["marker"],
                "frame": b["frame"],
                "who": b.get("who"),
                "action": b.get("action"),
                "note": b.get("staging"),
                "holy_fool_hinge": bool(b.get("holy_fool_hinge")),
            }
        )
    dion = data.get("dionysian_release") or {}
    default = dion.get("default_choice")
    opt = next(
        (o for o in (dion.get("options") or []) if o.get("id") == default),
        None,
    )
    if opt:
        lookback = next(
            (b for b in data["beats"] if b["id"] == "HF_LOOK_BACK_THRESHOLD"),
            None,
        )
        markers.append(
            {
                "name": f"HF_DIONYSUS_{default}",
                "frame": int((lookback or {}).get("frame") or 684),
                "optional": True,
                "image": opt.get("image"),
                "note": opt.get("staging"),
                "max_in_final_shot": 1,
            }
        )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "holy_fool_action": (data.get("policy") or {}).get("holy_fool_action"),
        "cosmic_reward": False,
        "explosion": False,
        "proof_world_saved": False,
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/holy_fool_turning_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    anc = data["ancestor_at_exit"]
    dion = data["dionysian_release"]
    lines = [
        "# Holy-fool turning — SCN_08_TABLE_ROOM",
        "",
        f"**Throughline:** {data.get('throughline')}  ",
        f"**Animatic:** `{data.get('approx_animatic_shot')}`  ",
        f"**Holy-fool action:** {policy.get('holy_fool_action')}  ",
        f"**Quality:** {policy.get('action_quality')}",
        "",
        "## Hard rules",
        "",
        f"- Cosmic reward: `{policy.get('cosmic_reward')}`",
        f"- Explosion: `{policy.get('explosion')}`",
        f"- Proof world saved: `{policy.get('proof_world_saved')}`",
        f"- Ancestor as oracle: `{policy.get('ancestor_as_oracle')}`",
        f"- Guarantee of return: `{policy.get('guarantee_of_return')}`",
        "",
        "## Ancestor at exit",
        "",
        f"- `{anc.get('marker')}` @ f{anc.get('frame')}: {anc.get('stance')}",
        f"- Explanation: `{anc.get('offers', {}).get('explanation')}`",
        f"- Guarantee Oino can return: `{anc.get('offers', {}).get('guarantee_oino_can_return')}`",
        f"- Link: `{anc.get('link_ancestor_beat')}`",
        f"- Staging: {anc.get('staging')}",
        "",
        "## Beats",
        "",
        "| Frame | Marker | Who | Action |",
        "|-------|--------|-----|--------|",
    ]
    for b in data.get("beats") or []:
        hinge = " (hinge)" if b.get("holy_fool_hinge") else ""
        lines.append(
            f"| {b['frame']} | `{b['marker']}`{hinge} | {b['who']} | {b['action']} |"
        )
    lines += [
        "",
        "_Hinge = releasing the playback control._",
        "",
        "## Optional Dionysian release",
        "",
        f"- Max images in final shot: `{dion.get('max_images_in_final_shot')}`",
        f"- Additional only if: {dion.get('additional_only_if')}",
        f"- Default: `{dion.get('default_choice')}` → {next((o['image'] for o in dion.get('options') or [] if o['id'] == dion.get('default_choice')), '')}",
        f"- Explain: `{dion.get('explain')}`",
        "",
        "Options:",
        "",
    ]
    for o in dion.get("options") or []:
        lines.append(f"- `{o['id']}` — {o['image']}")
    lines += ["", "## Must preserve", ""]
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
        "python scripts/animate_holy_fool_turning.py",
        "python scripts/animate_holy_fool_turning.py --check-links",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/holy_fool_turning.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Animate holy-fool turning")
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Cross-check ancestor arc, table cameras, knock order, animatic",
    )
    args = parser.parse_args()

    report = RunReport(script="animate_holy_fool_turning", seed=20261210)
    try:
        data = load_hf()
        report.mark("reused", "docs/holy_fool_turning.json")
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
        "Holy-fool turning: ordinary costly release; no cosmic reward/explosion/"
        "saved-world proof; max one optional Dionysian image"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"beats={len(data['beats'])} "
        f"dionysian_options={len(data['dionysian_release']['options'])} "
        f"max_release_images={data['dionysian_release']['max_images_in_final_shot']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
