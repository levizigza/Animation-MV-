"""Build and validate the recurring call-to-dinner motif tracker.

Reads ``docs/call_to_dinner_motif.json``, validates the six appearances,
writes ``docs/call_to_dinner_tracking.md`` and marker helpers.

Usage:
  python scripts/build_call_to_dinner_motif.py
  python scripts/build_call_to_dinner_motif.py --check-audio-markers
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

MOTIF_JSON = DOCS_DIR / "call_to_dinner_motif.json"
TRACKING_MD = DOCS_DIR / "call_to_dinner_tracking.md"
MARKERS_JSON = DOCS_DIR / "call_to_dinner_markers.json"
AUDIO_MARKERS = DOCS_DIR / "audio_markers.json"

REQUIRED_APPEARANCE_IDS = (
    "CALL_01_SISTER_DOWNSTAIRS",
    "CALL_02_ARCHIVE_ANCESTOR",
    "CALL_03_FACTORY_ALARM",
    "CALL_04_TERMINAL_NOTIFICATION",
    "CALL_05_ZONE_KNOCK",
    "CALL_06_TABLE_TAP_NEW_MELODY",
)

REQUIRED_PHASES = ("opening", "middle", "zone", "ending")
REQUIRED_MEANINGS = {
    "opening": "invitation refused",
    "middle": "ordinary life ignored while preservation continues",
    "zone": "reality interrupting desire",
    "ending": "living relationship accepted",
}


def load_motif() -> dict[str, Any]:
    if not MOTIF_JSON.is_file():
        raise FileNotFoundError(
            f"Missing motif source: {MOTIF_JSON}. "
            "Restore docs/call_to_dinner_motif.json before building."
        )
    return json.loads(MOTIF_JSON.read_text(encoding="utf-8"))


def validate_motif(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    if policy.get("jump_scare") is not False:
        errors.append("policy.jump_scare must be false")
    if not policy.get("origin"):
        errors.append("policy.origin required")

    arc = data.get("meaning_arc") or {}
    for phase, label in REQUIRED_MEANINGS.items():
        block = arc.get(phase) or {}
        if (block.get("label") or "").strip().lower() != label:
            errors.append(
                f"meaning_arc.{phase}.label must be exactly '{label}'"
            )

    apps = data.get("appearances") or []
    if len(apps) != 6:
        errors.append(f"Need exactly 6 appearances, found {len(apps)}")

    ids = [a.get("id") for a in apps]
    if len(ids) != len(set(ids)):
        errors.append("appearance ids must be unique")
    for req in REQUIRED_APPEARANCE_IDS:
        if req not in ids:
            errors.append(f"Missing appearance id: {req}")

    for a in apps:
        aid = a.get("id", "?")
        for key in ("source", "rhythm", "visual_form", "response"):
            if not isinstance(a.get(key), dict):
                errors.append(f"{aid}: {key} must be an object")
        if "oino_responds" not in a or not isinstance(a.get("oino_responds"), bool):
            errors.append(f"{aid}: oino_responds must be boolean")
        src = a.get("source") or {}
        for sk in ("kind", "who", "where", "medium"):
            if not src.get(sk):
                errors.append(f"{aid}: source.{sk} required")
        rh = a.get("rhythm") or {}
        if not rh.get("pattern"):
            errors.append(f"{aid}: rhythm.pattern required")
        vf = a.get("visual_form") or {}
        if not vf.get("primary"):
            errors.append(f"{aid}: visual_form.primary required")
        resp = a.get("response") or {}
        if not resp.get("action") or not resp.get("means"):
            errors.append(f"{aid}: response.action and response.means required")
        phase = a.get("phase")
        if phase not in REQUIRED_PHASES:
            errors.append(f"{aid}: phase must be one of {REQUIRED_PHASES}")
        expected = REQUIRED_MEANINGS.get(phase or "")
        if expected and (a.get("meaning_label") or "").strip().lower() != expected:
            # middle appears twice — same label OK
            if phase == "middle" and expected in (a.get("meaning_label") or "").lower():
                pass
            elif (a.get("meaning_label") or "").strip().lower() != expected:
                errors.append(
                    f"{aid}: meaning_label should match phase '{phase}' → '{expected}'"
                )
        if not vf.get("avoid"):
            errors.append(
                f"{aid}: visual_form.avoid should document non-scare staging"
            )
    # Response pattern: first four refuse/ignore; zone + ending respond
    by_id = {a["id"]: a for a in apps if a.get("id")}
    for early in REQUIRED_APPEARANCE_IDS[:4]:
        if early in by_id and by_id[early].get("oino_responds") is not False:
            errors.append(f"{early}: opening/middle calls should not be fully answered (oino_responds=false)")
    for late in REQUIRED_APPEARANCE_IDS[4:]:
        if late in by_id and by_id[late].get("oino_responds") is not True:
            errors.append(f"{late}: zone/ending should record a response (oino_responds=true)")

    return errors


def write_tracking_md(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    arc = data["meaning_arc"]
    lines = [
        "# Call to dinner - motif tracking",
        "",
        f"**Motif id:** `{data.get('motif_id', 'CALL_TO_DINNER')}`  ",
        f"**Film:** {data.get('film', 'Oino (Interlude)')}",
        "",
        "## Creative rules",
        "",
        f"- **Not a jump scare.** `{policy.get('jump_scare')}`",
        f"- Begins as a **familiar domestic sound** ({policy.get('origin')}).",
        f"- Becomes strange only because **{policy.get('strangeness_source')}**.",
        "- Track through **sound, image, and action** - not sound alone.",
        "- Do not cut the film to every transient of the call.",
        "",
        "## Meaning arc",
        "",
        "| Phase | Meaning | Note |",
        "|-------|---------|------|",
        f"| Opening | **{arc['opening']['label']}** | {arc['opening']['note']} |",
        f"| Middle | **{arc['middle']['label']}** | {arc['middle']['note']} |",
        f"| Zone | **{arc['zone']['label']}** | {arc['zone']['note']} |",
        f"| Ending | **{arc['ending']['label']}** | {arc['ending']['note']} |",
        "",
        "## Appearances",
        "",
    ]

    for a in sorted(data["appearances"], key=lambda x: int(x.get("order", 0))):
        src = a["source"]
        rh = a["rhythm"]
        vf = a["visual_form"]
        resp = a["response"]
        responds = "yes" if a.get("oino_responds") else "no"
        lines += [
            f"### {a['order']}. `{a['id']}`",
            "",
            f"- **Phase / meaning:** {a.get('phase')} - *{a.get('meaning_label')}*",
            f"- **Approx shot / frame:** `{a.get('approx_shot')}` / f{a.get('approx_frame')}",
            f"- **Timeline marker:** `{a.get('marker')}`",
            "",
            "| Field | Record |",
            "|-------|--------|",
            (
                f"| **Source** | {src.get('kind')} / {src.get('who')} / "
                f"{src.get('where')} / via {src.get('medium')} |"
            ),
            f"| **Rhythm** | {rh.get('pattern')} |",
            f"| **Visual form** | {vf.get('primary')} |",
            f"| **Oino responds?** | **{responds}** |",
            (
                f"| **Response / meaning** | {resp.get('action')} "
                f"-> {resp.get('means')} |"
            ),
            "",
            f"*Music relation:* {rh.get('relation_to_music', '-')}  ",
            f"*Avoid:* {vf.get('avoid', '-')}",
            "",
        ]
        support = vf.get("supporting") or []
        if support:
            lines.append(
                "Supporting objects: "
                + ", ".join(f"`{s}`" for s in support)
                + "."
            )
            lines.append("")

    lines += [
        "## Continuity checklist",
        "",
        "- [ ] First call is recognisably domestic (sister downstairs).",
        "- [ ] Archive / factory / terminal versions rhyme without becoming scares.",
        "- [ ] Zone knock is irregular and unexplained.",
        "- [ ] Final table tap is the seed of the changed melody.",
        "- [ ] Opening = refused; ending = living relationship accepted.",
        "",
        "## Sources",
        "",
        f"- Machine-readable: [`call_to_dinner_motif.json`](call_to_dinner_motif.json)",
        f"- Markers: [`call_to_dinner_markers.json`](call_to_dinner_markers.json)",
        f"- Rebuild: `python scripts/build_call_to_dinner_motif.py`",
        "",
    ]
    TRACKING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/call_to_dinner_tracking.md")
    return TRACKING_MD


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = {
        "schema_version": 1,
        "motif_id": data.get("motif_id"),
        "editable": True,
        "policy": data.get("policy"),
        "markers": [
            {
                "name": a["marker"],
                "frame": a.get("approx_frame"),
                "shot": a.get("approx_shot"),
                "phase": a.get("phase"),
                "meaning_label": a.get("meaning_label"),
                "oino_responds": a.get("oino_responds"),
                "note": a["response"]["means"],
            }
            for a in sorted(data["appearances"], key=lambda x: int(x.get("order", 0)))
        ],
    }
    MARKERS_JSON.write_text(json.dumps(markers, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/call_to_dinner_markers.json")
    return MARKERS_JSON


def check_audio_markers(report: RunReport) -> None:
    if not AUDIO_MARKERS.is_file():
        report.note("audio_markers.json not found — skip cross-check")
        return
    audio = json.loads(AUDIO_MARKERS.read_text(encoding="utf-8"))
    names = {m["name"] for m in audio.get("broad_cues", [])}
    names |= {m["name"] for m in audio.get("structural_markers", [])}
    if "CUE_KNOCK" in names:
        report.mark("reused", "docs/audio_markers.json (CUE_KNOCK present)")
        report.note(
            "CALL_01 should stay near CUE_KNOCK without converting it into a jump scare"
        )
    else:
        report.note("CUE_KNOCK missing from audio_markers — add or align CALL_01 by hand")


def main() -> int:
    parser = argparse.ArgumentParser(description="Call-to-dinner motif tracker")
    parser.add_argument(
        "--check-audio-markers",
        action="store_true",
        help="Cross-check CUE_KNOCK / broad cues in audio_markers.json",
    )
    args = parser.parse_args()

    report = RunReport(script="build_call_to_dinner_motif", seed=20261210)
    try:
        data = load_motif()
        report.mark("reused", "docs/call_to_dinner_motif.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("motif_json", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate_motif(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    write_tracking_md(data, report)
    write_markers(data, report)
    if args.check_audio_markers:
        check_audio_markers(report)
    else:
        # Always do a light check
        check_audio_markers(report)

    report.note(
        "Motif path: refused invitation -> ignored ordinary life -> "
        "Zone interruption -> accepted living relationship"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} appearances={len(data['appearances'])} "
        f"tracking={TRACKING_MD.relative_to(PROJECT_ROOT).as_posix()}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
