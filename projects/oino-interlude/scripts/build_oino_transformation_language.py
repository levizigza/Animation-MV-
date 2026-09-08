"""Build Oino transformation language (Oenotropae as visual/emotional grammar).

Not a superhero power set. Tracks subtle material transformations, nourishment
domains, forced-production parallels, and the resolution: change how the gift
is used — carry memory home and share it.

Usage:
  python scripts/build_oino_transformation_language.py
  python scripts/build_oino_transformation_language.py --list
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

LANG_JSON = DOCS_DIR / "oino_transformation_language.json"
TRACKING_MD = DOCS_DIR / "oino_transformation_language.md"
MARKERS_JSON = DOCS_DIR / "oino_transformation_markers.json"

REQUIRED_CHAIN_IDS = (
    "XF_WATER_TO_STEAM",
    "XF_STEAM_TO_ELECTRIC_HAZE",
    "XF_HAZE_TO_SCREEN_GLOW",
    "XF_SCREEN_TO_AMBER",
    "XF_DRY_BOWL_TO_MEAL",
    "XF_MECH_TO_HUMAN_MELODY",
    "XF_PRESERVED_TO_LIVING",
    "XF_CABLE_TO_VINE",
    "XF_VINE_TO_PATH",
)

REQUIRED_NOURISHMENT = (
    "food",
    "water",
    "time returned by machines",
    "speech restored through assistance",
    "memory preserved through recording",
    "music changed by another person",
)

REQUIRED_PARALLELS = (
    "FP_WORKERS_MEASURED",
    "FP_OENOTROPAE_RESOURCE",
    "FP_VOICES_HARVESTED",
    "FP_OINO_EXTRACTS_REUNION",
)


def load_lang() -> dict[str, Any]:
    if not LANG_JSON.is_file():
        raise FileNotFoundError(f"Missing {LANG_JSON}")
    return json.loads(LANG_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    if policy.get("generic_superhero_powers") is not False:
        errors.append("policy.generic_superhero_powers must be false")
    if policy.get("destroy_the_gift") is not False:
        errors.append("policy.destroy_the_gift must be false")
    if policy.get("force_reunion_forever") is not False:
        errors.append("policy.force_reunion_forever must be false")
    if "share" not in (policy.get("answer") or "").lower():
        errors.append("policy.answer must describe sharing memory home")

    if (data.get("inherited_principle") or "").strip().lower() != (
        "transformation toward nourishment"
    ):
        errors.append(
            "inherited_principle must be 'transformation toward nourishment'"
        )

    myth = data.get("mythic_source") or {}
    if "superhero" not in (myth.get("not") or "").lower():
        errors.append("mythic_source.not must reject generic superhero power")

    chain = data.get("transformation_chain") or []
    ids = [c.get("id") for c in chain]
    if len(ids) != len(set(ids)):
        errors.append("transformation ids must be unique")
    for req in REQUIRED_CHAIN_IDS:
        if req not in ids:
            errors.append(f"Missing transformation: {req}")
    for c in chain:
        cid = c.get("id", "?")
        for field in ("from", "to", "nourishment_link", "emotional_read", "marker"):
            if not (c.get(field) or "").strip():
                errors.append(f"{cid}: missing {field}")

    tracks = data.get("nourishment_tracks") or []
    domains = [t.get("domain") for t in tracks]
    for d in REQUIRED_NOURISHMENT:
        if d not in domains:
            errors.append(f"Missing nourishment track: {d}")
    for t in tracks:
        tid = t.get("id", "?")
        if not t.get("throughline") or not t.get("forced_production_risk"):
            errors.append(f"{tid}: throughline and forced_production_risk required")

    parallels = data.get("forced_production_parallels") or []
    pids = [p.get("id") for p in parallels]
    for req in REQUIRED_PARALLELS:
        if req not in pids:
            errors.append(f"Missing forced-production parallel: {req}")
    for p in parallels:
        pid = p.get("id", "?")
        for field in ("image", "parallel_to", "oino_echo", "marker"):
            if not (p.get(field) or "").strip():
                errors.append(f"{pid}: missing {field}")

    res = data.get("resolution") or {}
    if "destruction" not in (res.get("not") or "").lower():
        errors.append("resolution.not must reject destruction of the gift")
    if "changing how" not in (res.get("is") or "").lower():
        errors.append("resolution.is must be changing how the gift is used")
    if "share" not in (res.get("action") or "").lower():
        errors.append("resolution.action must include sharing memory home")

    return errors


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = []
    for c in data["transformation_chain"]:
        markers.append(
            {
                "name": c["marker"],
                "frame": c.get("approx_frame"),
                "shot": c.get("approx_shot"),
                "from": c["from"],
                "to": c["to"],
                "nourishment_link": c["nourishment_link"],
                "note": c["emotional_read"],
            }
        )
    for p in data["forced_production_parallels"]:
        markers.append(
            {
                "name": p["marker"],
                "frame": p.get("approx_frame"),
                "shot": p.get("approx_shot"),
                "kind": "forced_production_parallel",
                "image": p["image"],
                "note": p["oino_echo"],
            }
        )
    for mid in (data.get("resolution") or {}).get("markers") or []:
        markers.append(
            {
                "name": f"RES_REF_{mid}",
                "ref": mid,
                "kind": "resolution_reference",
                "note": "Gift used as sharing, not endless extraction",
            }
        )
    out = {
        "schema_version": 1,
        "editable": True,
        "inherited_principle": data.get("inherited_principle"),
        "no_superhero_powers": True,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/oino_transformation_markers.json")
    return MARKERS_JSON


def write_tracking_md(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    myth = data["mythic_source"]
    res = data["resolution"]
    lines = [
        "# Oino transformation language",
        "",
        f"**Mythic source:** {myth.get('name')} as *{myth.get('use')}* — not {myth.get('not')}.",
        f"**Inherited principle:** {data.get('inherited_principle')}",
        "",
        "## Hard rules",
        "",
        f"- Generic superhero powers: `{policy.get('generic_superhero_powers')}`",
        f"- Destroy the gift: `{policy.get('destroy_the_gift')}`",
        f"- Force reunion forever: `{policy.get('force_reunion_forever')}`",
        f"- **Answer:** {policy.get('answer')}",
        "",
        "## Subtle transformation chain",
        "",
        "| Id | From -> To | Nourishment link | Emotional read |",
        "|----|------------|------------------|----------------|",
    ]
    for c in data["transformation_chain"]:
        lines.append(
            f"| `{c['id']}` | {c['from']} -> {c['to']} | {c['nourishment_link']} | {c['emotional_read']} |"
        )

    lines += [
        "",
        "## Nourishment tracks",
        "",
    ]
    for t in data["nourishment_tracks"]:
        lines += [
            f"### {t['domain']} (`{t['id']}`)",
            "",
            f"- **Throughline:** {t['throughline']}",
            f"- **Forced-production risk:** {t['forced_production_risk']}",
            "- **Markers:** "
            + ", ".join(f"`{m}`" for m in (t.get("key_markers") or [])),
            "",
        ]

    lines += [
        "## Danger of forced production (visual parallels)",
        "",
        "| Parallel | Image | Echoes |",
        "|----------|-------|--------|",
    ]
    for p in data["forced_production_parallels"]:
        lines.append(
            f"| `{p['id']}` | {p['image']} | {p['oino_echo']} (cf. {p['parallel_to']}) |"
        )

    lines += [
        "",
        "## Resolution",
        "",
        f"- **Not:** {res.get('not')}",
        f"- **Is:** {res.get('is')}",
        f"- **Action:** {res.get('action')}",
        "",
        "### Beats",
        "",
    ]
    for b in res.get("beats") or []:
        lines.append(f"- {b}")
    lines += [
        "",
        "## Continuity checklist",
        "",
        "- [ ] No laser hands / generic magic powers for Oino.",
        "- [ ] Water/steam/haze/screen/amber read as one changing world.",
        "- [ ] Dry bowl becomes shared meal; sister changes the music.",
        "- [ ] Workers measured // gift-as-resource // harvested voices // Oino's rewind are visibly parallel.",
        "- [ ] Ending shares memory home — does not smash the archive or loop the father forever.",
        "",
        "## Sources",
        "",
        "- [`oino_transformation_language.json`](oino_transformation_language.json)",
        "- [`oino_transformation_markers.json`](oino_transformation_markers.json)",
        "",
        "```text",
        "python scripts/build_oino_transformation_language.py",
        "```",
        "",
    ]
    TRACKING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/oino_transformation_language.md")
    return TRACKING_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Oino transformation language")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_oino_transformation_language", seed=20261210)
    try:
        data = load_lang()
        report.mark("reused", "docs/oino_transformation_language.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("lang_json", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    if args.list:
        for c in data["transformation_chain"]:
            print(f"{c['id']}: {c['from']} -> {c['to']}")
        print("--- forced production ---")
        for p in data["forced_production_parallels"]:
            print(f"{p['id']}: {p['image']}")
        return 0

    write_markers(data, report)
    write_tracking_md(data, report)
    report.note(
        "Principle: transformation toward nourishment; "
        "answer is share home, not destroy gift or force forever"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} "
        f"transforms={len(data['transformation_chain'])} "
        f"parallels={len(data['forced_production_parallels'])} "
        f"doc={TRACKING_MD.relative_to(PROJECT_ROOT).as_posix()}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
