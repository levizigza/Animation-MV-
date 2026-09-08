"""Build one reusable modular industrial world (multi-era via collections/controls).

Does not build four unrelated cities. Persistent anchors (doorway, vertical beam,
path, bowl, hand surface) remain across era_blend.

Usage:
  python scripts/build_modular_industrial_world.py
  python scripts/build_modular_industrial_world.py --write-blend
  python scripts/build_modular_industrial_world.py --write-blend --reset
  python scripts/build_modular_industrial_world.py --era-blend 0.6 --future-branch 0.2
"""

from __future__ import annotations

import argparse
import json
import math
import random
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

WORLD_JSON = DOCS_DIR / "modular_industrial_world.json"
STATUS_MD = DOCS_DIR / "modular_industrial_world_status.md"
CONTROLS_JSON = DOCS_DIR / "modular_industrial_world_controls.json"
BLEND = SCENES_DIR / "SCN_MODULAR_INDUSTRIAL_WORLD.blend"
HELPER = SCRIPTS_DIR / "_blender_modular_industrial_world.py"
PAYLOAD = PROJECT_ROOT / "cache" / "modular_industrial_world_payload.json"
BLEND_REPORT = PROJECT_ROOT / "cache" / "modular_industrial_world_blender_report.json"

REQUIRED_COLLECTIONS = (
    "WORLD_STRUCTURE",
    "WORLD_STEAM",
    "WORLD_ELECTRIC",
    "WORLD_DIGITAL",
    "WORLD_POSSIBLE_FUTURES",
    "WORLD_ORGANIC_GROWTH",
    "WORLD_WATER_AND_REFLECTIONS",
    "WORLD_DIONYSUS_ECHOES",
)

REQUIRED_ANCHORS = (
    "doorway",
    "vertical_beam",
    "path",
    "bowl",
    "hand_level_surface",
)

REQUIRED_MODULE_GROUPS = (
    "water_channels",
    "waterwheel",
    "timber_beams",
    "brick_and_stone",
    "steam_pipes",
    "loom_and_belt",
    "pressure_valves",
    "electrical_poles_lamps",
    "generators_cables",
    "assembly_line",
    "terminals_monitors",
    "server_cooling",
    "assistive_communication",
    "medical_synthetic_voice",
    "circulation",
    "babel_core",
)


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def era_collection_weight(
    era_blend: float, peak: float, falloff: float
) -> float:
    """Gaussian-ish presence around peak along era_blend."""
    return math.exp(-((era_blend - peak) ** 2) / max(falloff, 1e-6))


def compute_visibility(
    world: dict[str, Any],
    *,
    era_blend: float,
    future_branch: float,
    organic_growth: float,
    dionysus_presence: float,
) -> dict[str, float]:
    era_blend = clamp01(era_blend)
    future_branch = clamp01(future_branch)
    organic_growth = clamp01(organic_growth)
    dionysus_presence = clamp01(dionysus_presence)
    vis: dict[str, float] = {}
    for col, rule in (world.get("era_visibility") or {}).items():
        driven = rule.get("driven_by")
        if driven == "future_branch":
            vis[col] = future_branch
        elif driven == "organic_growth":
            vis[col] = organic_growth
        elif driven == "dionysus_presence":
            vis[col] = dionysus_presence
        else:
            vis[col] = era_collection_weight(
                era_blend,
                float(rule.get("era_peak", 0.5)),
                float(rule.get("falloff", 0.4)),
            )
    # Structure always partly visible — one world
    vis["WORLD_STRUCTURE"] = max(vis.get("WORLD_STRUCTURE", 0.5), 0.55)
    return {k: round(clamp01(v), 4) for k, v in vis.items()}


def validate_world(world: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cols = world.get("collections") or []
    for c in REQUIRED_COLLECTIONS:
        if c not in cols:
            errors.append(f"Missing collection: {c}")
    anchors = world.get("persistent_anchors") or {}
    for key in REQUIRED_ANCHORS:
        if not anchors.get(key):
            errors.append(f"Missing persistent anchor: {key}")
    modules = world.get("modules") or {}
    for g in REQUIRED_MODULE_GROUPS:
        if not modules.get(g):
            errors.append(f"Missing module group: {g}")
    controls = world.get("controls") or {}
    for name in ("era_blend", "future_branch", "organic_growth", "dionysus_presence"):
        c = controls.get(name)
        if not isinstance(c, dict):
            errors.append(f"controls.{name} required")
            continue
        if float(c.get("min", 0)) != 0.0 or float(c.get("max", 1)) != 1.0:
            errors.append(f"controls.{name} must be 0..1")
    names: list[str] = []
    for group, items in modules.items():
        if group == "babel_core":
            # May intentionally name the persistent vertical beam
            continue
        names.extend(items)
    for key in REQUIRED_ANCHORS:
        names.append(anchors[key])
    if len(names) != len(set(names)):
        errors.append("Module/anchor object names must be unique")
    babel = modules.get("babel_core") or []
    if anchors.get("vertical_beam") not in babel:
        errors.append("babel_core must include the persistent vertical_beam anchor")
    return errors


def seeded_instance_offsets(
    seed: int, count: int
) -> list[dict[str, float]]:
    rng = random.Random(seed)
    out = []
    for i in range(count):
        out.append(
            {
                "dx": round(rng.uniform(-6.0, 6.0), 3),
                "dy": round(rng.uniform(-4.0, 8.0), 3),
                "yaw_deg": round(rng.uniform(-25, 25), 2),
                "scale": round(rng.uniform(0.85, 1.15), 3),
            }
        )
    return out


def write_controls_snapshot(
    world: dict[str, Any],
    values: dict[str, float],
    visibility: dict[str, float],
    report: RunReport,
) -> Path:
    payload = {
        "scene": world["scene"],
        "seed": world.get("seed"),
        "controls": values,
        "collection_visibility": visibility,
        "persistent_anchors": world.get("persistent_anchors"),
        "preview": world.get("preview"),
        "note": world.get("intent"),
    }
    CONTROLS_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/modular_industrial_world_controls.json")
    return CONTROLS_JSON


def write_status(
    world: dict[str, Any],
    values: dict[str, float],
    visibility: dict[str, float],
    blender: dict[str, Any],
    report: RunReport,
) -> Path:
    anchors = world["persistent_anchors"]
    lines = [
        "# Modular industrial world",
        "",
        f"**Scene:** `{world['scene']}`  ",
        f"**Intent:** {world['intent']}",
        "",
        "## Controls (0..1)",
        "",
        "| Control | Value | Meaning |",
        "|---------|-------|---------|",
    ]
    for name, val in values.items():
        meaning = (world.get("controls") or {}).get(name, {}).get("meaning", "")
        lines.append(f"| `{name}` | {val:.3f} | {meaning} |")
    lines += [
        "",
        "## Collection visibility (derived)",
        "",
        "| Collection | Weight |",
        "|------------|--------|",
    ]
    for col, w in sorted(visibility.items()):
        lines.append(f"| `{col}` | {w:.3f} |")
    lines += [
        "",
        "## Persistent anchors (same human needs)",
        "",
        f"- Doorway: `{anchors['doorway']}`",
        f"- Vertical beam (Babel-capable): `{anchors['vertical_beam']}`",
        f"- Path: `{anchors['path']}`",
        f"- Bowl: `{anchors['bowl']}`",
        f"- Hand-level surface: `{anchors['hand_level_surface']}`",
        "",
        "## Module groups",
        "",
    ]
    for g, items in (world.get("modules") or {}).items():
        lines.append(f"- **{g}:** " + ", ".join(f"`{i}`" for i in items))
    lines += [
        "",
        "## Blender",
        "",
        f"- Target: `{BLEND.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Status: **{blender.get('status')}**",
        f"- Detail: {blender.get('detail')}",
        "",
        "Rebuild: `python scripts/build_modular_industrial_world.py --write-blend`",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/modular_industrial_world_status.md")
    return STATUS_MD


def try_blend(payload: dict[str, Any], *, write: bool, report: RunReport) -> dict[str, Any]:
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "cache/modular_industrial_world_payload.json")
    if not write:
        return {"status": "skipped", "detail": "Pass --write-blend to create .blend"}
    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed - SCN_MODULAR_INDUSTRIAL_WORLD.blend deferred")
        return {
            "status": "deferred",
            "detail": "Install Blender, then re-run with --write-blend",
        }
    if BLEND.exists() and not payload.get("reset"):
        report.mark("reused", "scenes/SCN_MODULAR_INDUSTRIAL_WORLD.blend")
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
        report.fail("SCN_MODULAR_INDUSTRIAL_WORLD.blend", err or f"exit {proc.returncode}")
        return {"status": "failed", "detail": err}
    report.mark("created", "scenes/SCN_MODULAR_INDUSTRIAL_WORLD.blend")
    return {"status": "created", "detail": str(BLEND)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Modular industrial world builder")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--era-blend", type=float, default=None)
    parser.add_argument("--future-branch", type=float, default=None)
    parser.add_argument("--organic-growth", type=float, default=None)
    parser.add_argument("--dionysus-presence", type=float, default=None)
    parser.add_argument(
        "--preview",
        action="store_true",
        default=True,
        help="Fewer instances for preview (default on)",
    )
    parser.add_argument("--full", action="store_true", help="Full instance counts")
    args = parser.parse_args()

    report = RunReport(script="build_modular_industrial_world", seed=20261210, reset=args.reset)
    if not WORLD_JSON.is_file():
        report.fail("world_json", f"Missing {WORLD_JSON}")
        report.write(REPORTS_DIR)
        return 1
    world = json.loads(WORLD_JSON.read_text(encoding="utf-8"))
    report.mark("reused", "docs/modular_industrial_world.json")
    report.seed = int(world.get("seed") or 20261210)

    errors = validate_world(world)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    controls_def = world["controls"]
    values = {
        "era_blend": clamp01(
            args.era_blend
            if args.era_blend is not None
            else controls_def["era_blend"]["default"]
        ),
        "future_branch": clamp01(
            args.future_branch
            if args.future_branch is not None
            else controls_def["future_branch"]["default"]
        ),
        "organic_growth": clamp01(
            args.organic_growth
            if args.organic_growth is not None
            else controls_def["organic_growth"]["default"]
        ),
        "dionysus_presence": clamp01(
            args.dionysus_presence
            if args.dionysus_presence is not None
            else controls_def["dionysus_presence"]["default"]
        ),
    }
    visibility = compute_visibility(world, **values)
    write_controls_snapshot(world, values, visibility, report)

    preview = not args.full
    inst_count = int(
        (world.get("preview") or {}).get(
            "instance_count_preview" if preview else "instance_count_full", 3
        )
    )
    instances = {
        "steam_pipes": seeded_instance_offsets(report.seed + 1, inst_count),
        "cable_bundles": seeded_instance_offsets(report.seed + 2, inst_count),
        "timber_beams": seeded_instance_offsets(report.seed + 3, inst_count),
        "assembly_line": seeded_instance_offsets(report.seed + 4, max(1, inst_count - 1)),
    }
    report.note(f"preview_mode={preview} instance_slots={inst_count}")
    report.note("One world / shared anchors — not four unrelated cities")

    cfg = load_show_config()
    engine = resolve_render_engine(cfg)
    payload = {
        **world,
        "control_values": values,
        "collection_visibility": visibility,
        "instances": instances,
        "preview_mode": preview,
        "resolution": (cfg.get("resolutions") or {}).get("hd") or [1920, 1080],
        "engine": engine.get("engine") or "BLENDER_EEVEE_NEXT",
        "blend_out": str(BLEND.resolve()),
        "report_out": str(BLEND_REPORT.resolve()),
        "reset": args.reset,
    }
    if HELPER.is_file():
        report.mark("reused", "scripts/_blender_modular_industrial_world.py")
    blender_status = try_blend(payload, write=args.write_blend, report=report)
    write_status(world, values, visibility, blender_status, report)

    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} era_blend={values['era_blend']:.2f} "
        f"future={values['future_branch']:.2f} organic={values['organic_growth']:.2f} "
        f"dionysus={values['dionysus_presence']:.2f} blend={blender_status['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
