"""Configure the modular world as four revolution movements + possible futures.

Writes pass presets, continuity docs, and markers. Optionally refreshes modular
world control snapshot / blend payload for a chosen pass.

Usage:
  python scripts/build_revolution_passes.py
  python scripts/build_revolution_passes.py --pass MOV_02_ELECTRICITY_LIGHT_TIME
  python scripts/build_revolution_passes.py --pass MOV_01_WATER_STEAM_HANDS --write-world
  python scripts/build_revolution_passes.py --list
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
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR  # noqa: E402

PASSES_JSON = DOCS_DIR / "revolution_passes.json"
TRACKING_MD = DOCS_DIR / "revolution_passes.md"
PRESETS_JSON = DOCS_DIR / "revolution_pass_presets.json"
MARKERS_JSON = DOCS_DIR / "revolution_pass_markers.json"
WORLD_BUILDER = SCRIPTS_DIR / "build_modular_industrial_world.py"

REQUIRED_FIELDS = (
    "benefit",
    "cost",
    "gesture_of_care",
    "temptation_toward_control",
    "dionysian_echo",
)

REQUIRED_MOVEMENT_IDS = (
    "MOV_01_WATER_STEAM_HANDS",
    "MOV_02_ELECTRICITY_LIGHT_TIME",
    "MOV_03_COMPUTING_SCREENS_CONFESSION",
    "MOV_04_ASSISTANCE_MEMORIAL_FUTURES",
)


def load_passes() -> dict[str, Any]:
    if not PASSES_JSON.is_file():
        raise FileNotFoundError(f"Missing {PASSES_JSON}")
    return json.loads(PASSES_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    if policy.get("on_screen_era_labels") is not False:
        errors.append("policy.on_screen_era_labels must be false")
    if policy.get("four_unrelated_cities") is not False:
        errors.append("policy.four_unrelated_cities must be false")
    carriers = policy.get("history_carried_by") or []
    for need in (
        "energy_systems",
        "materials",
        "interfaces",
        "labour",
        "food",
        "music",
        "relationships",
    ):
        if need not in carriers:
            errors.append(f"policy.history_carried_by missing '{need}'")

    movements = data.get("movements") or []
    if len(movements) != 4:
        errors.append(f"Need exactly 4 movements, found {len(movements)}")
    ids = [m.get("id") for m in movements]
    if len(ids) != len(set(ids)):
        errors.append("movement ids must be unique")
    for req in REQUIRED_MOVEMENT_IDS:
        if req not in ids:
            errors.append(f"Missing movement: {req}")

    for m in movements:
        mid = m.get("id", "?")
        if m.get("on_screen_label") not in (None, ""):
            errors.append(f"{mid}: on_screen_label must be null (no era labels on screen)")
        for field in REQUIRED_FIELDS:
            if not (m.get(field) or "").strip():
                errors.append(f"{mid}: missing {field}")
        preset = m.get("control_preset") or {}
        for c in ("era_blend", "future_branch", "organic_growth", "dionysus_presence"):
            if c not in preset:
                errors.append(f"{mid}: control_preset.{c} required")
            else:
                v = float(preset[c])
                if not 0.0 <= v <= 1.0:
                    errors.append(f"{mid}: control_preset.{c} must be 0..1")
        beats = m.get("beats") or []
        if len(beats) < 3:
            errors.append(f"{mid}: need staging beats")
        beat_ids = [b.get("id") for b in beats]
        if len(beat_ids) != len(set(beat_ids)):
            errors.append(f"{mid}: beat ids must be unique")

    fut = data.get("possible_futures") or {}
    if not fut:
        errors.append("possible_futures block required")
    else:
        for field in REQUIRED_FIELDS:
            if not (fut.get(field) or "").strip():
                errors.append(f"possible_futures: missing {field}")
        if "ordinary table" not in " ".join(fut.get("staging") or []).lower():
            errors.append("possible_futures staging must include the ordinary table")

    return errors


def write_presets(data: dict[str, Any], report: RunReport) -> Path:
    presets = {
        "schema_version": 1,
        "scene": data.get("scene"),
        "policy": data.get("policy"),
        "passes": {},
    }
    for m in data["movements"]:
        presets["passes"][m["id"]] = {
            "order": m["order"],
            "title_internal": m["title_internal"],
            "control_preset": m["control_preset"],
            "collection_emphasis": m.get("collection_emphasis"),
        }
    presets["passes"][data["possible_futures"]["id"]] = {
        "order": 5,
        "title_internal": "Possible futures",
        "control_preset": data["possible_futures"]["control_preset"],
        "collection_emphasis": [
            "WORLD_POSSIBLE_FUTURES",
            "WORLD_STRUCTURE",
        ],
    }
    PRESETS_JSON.write_text(json.dumps(presets, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/revolution_pass_presets.json")
    return PRESETS_JSON


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = []
    # Approximate frame windows across industrial pilgrimage (animatic SH040-SH070)
    windows = {
        "MOV_01_WATER_STEAM_HANDS": (746, 1000),
        "MOV_02_ELECTRICITY_LIGHT_TIME": (1001, 1300),
        "MOV_03_COMPUTING_SCREENS_CONFESSION": (1301, 1700),
        "MOV_04_ASSISTANCE_MEMORIAL_FUTURES": (1701, 1999),
        "PASS_FUTURES": (2000, 2424),
    }
    for m in data["movements"]:
        start, end = windows.get(m["id"], (1, 100))
        markers.append(
            {
                "name": m["id"],
                "frame": start,
                "frame_end": end,
                "note": m["title_internal"],
                "on_screen_label": None,
            }
        )
        for b in m.get("beats") or []:
            markers.append(
                {
                    "name": b["id"],
                    "frame": start,
                    "parent_pass": m["id"],
                    "note": b["action"],
                }
            )
    fut = data["possible_futures"]
    fs, fe = windows["PASS_FUTURES"]
    markers.append(
        {
            "name": fut["id"],
            "frame": fs,
            "frame_end": fe,
            "note": "Possible futures / table centre",
            "on_screen_label": None,
        }
    )
    out = {
        "schema_version": 1,
        "editable": True,
        "no_on_screen_era_labels": True,
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/revolution_pass_markers.json")
    return MARKERS_JSON


def write_tracking_md(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    lines = [
        "# Revolution passes - four movements + possible futures",
        "",
        f"**Scene:** `{data.get('scene')}`  ",
        "**On-screen era labels:** forbidden  ",
        f"**History carried by:** {', '.join(policy.get('history_carried_by') or [])}",
        "",
        "One modular world. Not four unrelated cities.",
        "",
    ]
    for m in sorted(data["movements"], key=lambda x: int(x["order"])):
        lines += [
            f"## Movement {m['order']} - {m['title_internal']} (`{m['id']}`)",
            "",
            f"**Internal only** - no slate text on screen.",
            "",
            f"- **Controls:** "
            + ", ".join(f"{k}={v}" for k, v in m["control_preset"].items()),
            f"- **Collections:** "
            + ", ".join(f"`{c}`" for c in m.get("collection_emphasis") or []),
            f"- **Palette:** " + ", ".join(m.get("visual_palette") or []),
            "",
            "| Axis | Content |",
            "|------|---------|",
            f"| Benefit | {m['benefit']} |",
            f"| Cost | {m['cost']} |",
            f"| Gesture of care | {m['gesture_of_care']} |",
            f"| Temptation toward control | {m['temptation_toward_control']} |",
            f"| Dionysian echo | {m['dionysian_echo']} |",
            "",
            "### Staging beats",
            "",
        ]
        for b in m.get("beats") or []:
            lines.append(f"- `{b['id']}`: {b['action']}")
        lines.append("")

    fut = data["possible_futures"]
    lines += [
        f"## Possible futures (`{fut['id']}`)",
        "",
        f"- **Controls:** "
        + ", ".join(f"{k}={v}" for k, v in fut["control_preset"].items()),
        "",
        "| Axis | Content |",
        "|------|---------|",
        f"| Benefit | {fut['benefit']} |",
        f"| Cost | {fut['cost']} |",
        f"| Gesture of care | {fut['gesture_of_care']} |",
        f"| Temptation toward control | {fut['temptation_toward_control']} |",
        f"| Dionysian echo | {fut['dionysian_echo']} |",
        "",
        "### Staging",
        "",
    ]
    for s in fut.get("staging") or []:
        lines.append(f"- {s}")
    lines += [
        "",
        "## Sources",
        "",
        "- [`revolution_passes.json`](revolution_passes.json)",
        "- [`revolution_pass_presets.json`](revolution_pass_presets.json)",
        "- [`revolution_pass_markers.json`](revolution_pass_markers.json)",
        "- World: [`modular_industrial_world.json`](modular_industrial_world.json)",
        "",
        "```text",
        "python scripts/build_revolution_passes.py --pass MOV_01_WATER_STEAM_HANDS --write-world",
        "```",
        "",
    ]
    TRACKING_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/revolution_passes.md")
    return TRACKING_MD


def apply_pass_to_world(pass_id: str, preset: dict[str, float], report: RunReport) -> int:
    if not WORLD_BUILDER.is_file():
        report.fail("world_builder", f"Missing {WORLD_BUILDER}")
        return 1
    cmd = [
        sys.executable,
        str(WORLD_BUILDER),
        "--era-blend",
        str(preset["era_blend"]),
        "--future-branch",
        str(preset["future_branch"]),
        "--organic-growth",
        str(preset["organic_growth"]),
        "--dionysus-presence",
        str(preset["dionysus_presence"]),
    ]
    report.note(f"Applying {pass_id} controls via build_modular_industrial_world.py")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        report.fail("write_world", (proc.stderr or proc.stdout or "")[-1500:])
        return 1
    report.mark("created", f"world_controls_from:{pass_id}")
    if proc.stdout:
        for line in proc.stdout.strip().splitlines()[-3:]:
            report.note(line)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Revolution passes for modular world")
    parser.add_argument(
        "--pass",
        dest="pass_id",
        default=None,
        help="Movement or PASS_FUTURES id to spotlight",
    )
    parser.add_argument(
        "--write-world",
        action="store_true",
        help="Push selected pass control_preset into modular world builder",
    )
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="build_revolution_passes", seed=20261210)
    try:
        data = load_passes()
        report.mark("reused", "docs/revolution_passes.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("passes_json", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    if args.list:
        for m in data["movements"]:
            print(f"{m['order']}. {m['id']} - {m['title_internal']}")
        print(f"5. {data['possible_futures']['id']} - Possible futures")
        return 0

    write_presets(data, report)
    write_markers(data, report)
    write_tracking_md(data, report)

    by_id = {m["id"]: m for m in data["movements"]}
    by_id[data["possible_futures"]["id"]] = {
        "id": data["possible_futures"]["id"],
        "control_preset": data["possible_futures"]["control_preset"],
        "title_internal": "Possible futures",
    }

    if args.pass_id:
        if args.pass_id not in by_id:
            report.fail("pass", f"Unknown pass id: {args.pass_id}")
            report.write(REPORTS_DIR)
            return 1
        selected = by_id[args.pass_id]
        report.note(f"Selected pass: {args.pass_id} ({selected.get('title_internal')})")
        report.note(
            "Controls: "
            + ", ".join(f"{k}={v}" for k, v in selected["control_preset"].items())
        )
        if args.write_world:
            rc = apply_pass_to_world(args.pass_id, selected["control_preset"], report)
            if rc != 0:
                report.write(REPORTS_DIR)
                return rc
    elif args.write_world:
        report.fail("pass", "--write-world requires --pass <id>")
        report.write(REPORTS_DIR)
        return 1

    report.note(
        "No on-screen era labels; history via energy, materials, interfaces, "
        "labour, food, music, relationships"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} movements=4 futures=1 "
        f"tracking={TRACKING_MD.relative_to(PROJECT_ROOT).as_posix()}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
