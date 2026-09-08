"""Build Dionysus presence map for Oino (Interlude).

Presence only — not a mythology narrator. Optional switchable echoes.
Writes docs/dionysus_presence_map.md and marker/switch JSON.

Usage:
  python scripts/build_dionysus_presence.py
  python scripts/build_dionysus_presence.py --enable ECHO_WINE_LIGHT ECHO_IVY_THROUGH_MACHINE
  python scripts/build_dionysus_presence.py --disable-all
  python scripts/build_dionysus_presence.py --list
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

PRESENCE_JSON = DOCS_DIR / "dionysus_presence.json"
MAP_MD = DOCS_DIR / "dionysus_presence_map.md"
SWITCHES_JSON = DOCS_DIR / "dionysus_presence_switches.json"
MARKERS_JSON = DOCS_DIR / "dionysus_presence_markers.json"

REQUIRED_ECHO_IDS = (
    "ECHO_RED_GARMENT",
    "ECHO_LAUGH_BEFORE_SOURCE",
    "ECHO_MASK_BLACK_GLASS",
    "ECHO_IVY_THROUGH_MACHINE",
    "ECHO_BROKEN_STAFF_GROWTH",
    "ECHO_WINE_LIGHT",
    "ECHO_HAND_PERCUSSION_DANCE",
    "ECHO_ARCHIVE_FRAME_FIGURE",
    "ECHO_ZONE_EXIT_SILHOUETTE",
    "ECHO_WHITE_BIRDS_RELEASE",
)

REQUIRED_PHASES = ("EARLY", "MIDDLE", "ZONE", "TABLE", "RELEASE")


def load_presence() -> dict[str, Any]:
    if not PRESENCE_JSON.is_file():
        raise FileNotFoundError(f"Missing {PRESENCE_JSON}")
    return json.loads(PRESENCE_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    for key in (
        "glowing_horned_god_giving_instructions",
        "voice_that_names_himself_dionysus",
        "every_red_object_is_a_symbol",
        "explain_mythology_on_screen",
    ):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")

    role = data.get("role") or {}
    if role.get("literal_cameo_default") is not False:
        errors.append("role.literal_cameo_default must be false")

    evo = data.get("evolution") or {}
    for phase in REQUIRED_PHASES:
        if phase not in evo or not (evo[phase].get("note") or "").strip():
            errors.append(f"evolution.{phase} required with note")

    echoes = data.get("echoes") or []
    if len(echoes) != 10:
        errors.append(f"Need exactly 10 switchable echoes, found {len(echoes)}")
    ids = [e.get("id") for e in echoes]
    if len(ids) != len(set(ids)):
        errors.append("echo ids must be unique")
    for req in REQUIRED_ECHO_IDS:
        if req not in ids:
            errors.append(f"Missing echo: {req}")

    for e in echoes:
        eid = e.get("id", "?")
        if e.get("switchable") is not True:
            errors.append(f"{eid}: switchable must be true")
        if "enabled_default" not in e or not isinstance(e.get("enabled_default"), bool):
            errors.append(f"{eid}: enabled_default boolean required")
        for field in ("appears", "does", "meaning_at_appearance"):
            if not (e.get(field) or "").strip():
                errors.append(f"{eid}: missing {field}")
        if "changes_later" not in e or not isinstance(e.get("changes_later"), bool):
            errors.append(f"{eid}: changes_later boolean required")
        if e.get("changes_later"):
            later = e.get("later") or {}
            if not later.get("phase") or not later.get("note"):
                errors.append(f"{eid}: later.phase and later.note required when changes_later")
            if later.get("phase") not in REQUIRED_PHASES:
                errors.append(f"{eid}: later.phase invalid")
        phase = e.get("phase_first")
        if phase not in REQUIRED_PHASES:
            errors.append(f"{eid}: phase_first must be one of {REQUIRED_PHASES}")
        if not e.get("forbid"):
            errors.append(f"{eid}: forbid list required")

    return errors


def write_switches(
    data: dict[str, Any],
    *,
    enable: list[str] | None,
    disable_all: bool,
    report: RunReport,
) -> Path:
    states: dict[str, bool] = {}
    for e in data["echoes"]:
        states[e["id"]] = bool(e.get("enabled_default"))
    if disable_all:
        states = {k: False for k in states}
    if enable:
        unknown = [x for x in enable if x not in states]
        for u in unknown:
            report.fail("enable", f"Unknown echo id: {u}")
        for eid in enable:
            if eid in states:
                states[eid] = True
    out = {
        "schema_version": 1,
        "motif_id": data.get("motif_id"),
        "literal_cameo": False,
        "echoes_enabled": states,
        "note": "Individually switchable. Disabled echoes must not appear in craft.",
    }
    SWITCHES_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/dionysus_presence_switches.json")
    enabled = [k for k, v in states.items() if v]
    report.note(
        "Enabled echoes: " + (", ".join(enabled) if enabled else "(none)")
    )
    return SWITCHES_JSON


def write_markers(data: dict[str, Any], switches: dict[str, bool], report: RunReport) -> Path:
    markers = []
    for e in data["echoes"]:
        markers.append(
            {
                "name": e["marker"],
                "frame": e.get("approx_frame"),
                "shot": e.get("approx_shot"),
                "echo_id": e["id"],
                "enabled": bool(switches.get(e["id"])),
                "phase_first": e.get("phase_first"),
                "changes_later": e.get("changes_later"),
                "note": e.get("meaning_at_appearance"),
            }
        )
    # Phase markers (evolution, not labels on screen)
    phase_frames = {
        "EARLY": 520,
        "MIDDLE": 1131,
        "ZONE": 2000,
        "TABLE": 2425,
        "RELEASE": 2820,
    }
    for phase, frame in phase_frames.items():
        markers.append(
            {
                "name": f"DION_PHASE_{phase}",
                "frame": frame,
                "phase": phase,
                "note": (data.get("evolution") or {}).get(phase, {}).get("note"),
                "on_screen_label": None,
            }
        )
    out = {
        "schema_version": 1,
        "editable": True,
        "no_self_naming_voice": True,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/dionysus_presence_markers.json")
    return MARKERS_JSON


def write_map_md(
    data: dict[str, Any], switches: dict[str, bool], report: RunReport
) -> Path:
    policy = data["policy"]
    role = data["role"]
    evo = data["evolution"]
    lines = [
        "# Dionysus presence map - Oino (Interlude)",
        "",
        f"**Album role:** {role.get('larger_project')} in One Of God's Fools.  ",
        f"**This film:** {role.get('this_interlude')}.  ",
        f"**Literal cameo default:** `{role.get('literal_cameo_default')}`",
        "",
        "## Hard rules",
        "",
        f"- Glowing horned god giving instructions: `{policy.get('glowing_horned_god_giving_instructions')}`",
        f"- Voice saying he is Dionysus: `{policy.get('voice_that_names_himself_dionysus')}`",
        f"- Every red object a symbol: `{policy.get('every_red_object_is_a_symbol')}`",
        f"- Explain mythology on screen: `{policy.get('explain_mythology_on_screen')}`",
        "",
        "Echoes are **optional and individually switchable**. Disabled = must not appear.",
        "",
        "## Evolution (no on-screen phase titles)",
        "",
        "| Phase | Presence |",
        "|-------|----------|",
    ]
    for phase in REQUIRED_PHASES:
        block = evo[phase]
        lines.append(
            f"| **{phase}** | *{block.get('label')}* - {block.get('note')} |"
        )

    lines += [
        "",
        "## Echo map",
        "",
        "| Echo | On? | First phase | Appears | Does | Meaning now | Changes later? |",
        "|------|-----|-------------|---------|------|-------------|----------------|",
    ]
    for e in data["echoes"]:
        on = "yes" if switches.get(e["id"]) else "no"
        later = "-"
        if e.get("changes_later") and e.get("later"):
            later = f"{e['later']['phase']}: {e['later']['note']}"
        elif e.get("changes_later") is False:
            later = "no (terminal image)"
        lines.append(
            "| `{id}` ({title}) | **{on}** | {phase} | {appears} | {does} | {meaning} | {later} |".format(
                id=e["id"],
                title=e.get("title", ""),
                on=on,
                phase=e.get("phase_first"),
                appears=(e.get("appears") or "").replace("|", "/"),
                does=(e.get("does") or "").replace("|", "/"),
                meaning=(e.get("meaning_at_appearance") or "").replace("|", "/"),
                later=later.replace("|", "/"),
            )
        )

    lines += ["", "## Per-echo detail", ""]
    for e in data["echoes"]:
        on = "ENABLED" if switches.get(e["id"]) else "disabled"
        lines += [
            f"### `{e['id']}` - {e.get('title')} [{on}]",
            "",
            f"- **Marker:** `{e.get('marker')}` · shot `{e.get('approx_shot')}` · f{e.get('approx_frame')}",
            f"- **First phase:** {e.get('phase_first')}",
            f"- **Appears:** {e.get('appears')}",
            f"- **Does:** {e.get('does')}",
            f"- **Meaning at appearance:** {e.get('meaning_at_appearance')}",
        ]
        if e.get("changes_later") and e.get("later"):
            lines.append(
                f"- **Later change ({e['later']['phase']}):** {e['later']['note']}"
            )
        else:
            lines.append("- **Later change:** none mapped")
        forb = e.get("forbid") or []
        lines.append("- **Forbid:** " + "; ".join(forb))
        lines.append("")

    lines += [
        "## Continuity checks",
        "",
        "- [ ] No glowing horned instructor.",
        "- [ ] No self-naming Dionysus voice.",
        "- [ ] Not every red practical is an echo.",
        "- [ ] EARLY stays hidden in objects/melody; RELEASE becomes birds/breath/changed music.",
        "- [ ] TABLE sacredness is meal/relationship, not ceremony.",
        "",
        "## Sources",
        "",
        "- [`dionysus_presence.json`](dionysus_presence.json)",
        "- [`dionysus_presence_switches.json`](dionysus_presence_switches.json)",
        "- [`dionysus_presence_markers.json`](dionysus_presence_markers.json)",
        "- Leitmotif proposal: [`dionysus_leitmotif.json`](dionysus_leitmotif.json)",
        "",
        "```text",
        "python scripts/build_dionysus_presence.py --enable ECHO_WINE_LIGHT ECHO_WHITE_BIRDS_RELEASE",
        "```",
        "",
    ]
    MAP_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/dionysus_presence_map.md")
    return MAP_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Dionysus presence map builder")
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--enable",
        nargs="*",
        default=None,
        help="Force-enable these echo ids (others keep defaults unless --disable-all)",
    )
    parser.add_argument(
        "--disable-all",
        action="store_true",
        help="Start from all echoes off (then apply --enable)",
    )
    args = parser.parse_args()

    report = RunReport(script="build_dionysus_presence", seed=20261210)
    try:
        data = load_presence()
        report.mark("reused", "docs/dionysus_presence.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("presence_json", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    if args.list:
        for e in data["echoes"]:
            flag = "on" if e.get("enabled_default") else "off"
            print(f"{e['id']} [{flag}] - {e.get('title')} ({e.get('phase_first')})")
        return 0

    write_switches(
        data,
        enable=args.enable,
        disable_all=args.disable_all,
        report=report,
    )
    if report.failed:
        report.write(REPORTS_DIR)
        return 1

    switches = json.loads(SWITCHES_JSON.read_text(encoding="utf-8"))["echoes_enabled"]
    write_markers(data, switches, report)
    write_map_md(data, switches, report)

    report.note(
        "Presence evolves EARLY->MIDDLE->ZONE->TABLE->RELEASE; "
        "never a self-explaining god"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} echoes=10 "
        f"enabled={sum(1 for v in switches.values() if v)} "
        f"map={MAP_MD.relative_to(PROJECT_ROOT).as_posix()}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
