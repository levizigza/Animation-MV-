"""Foundation build for Oino (Interlude) — dirs, config placeholders, status.

Idempotent by default. Pass ``--reset`` only to recreate generated placeholders
(never deletes audio, CANON, beatmap, project.json, or user assets).

Usage (from repo root or this folder):
  python projects/oino-interlude/scripts/run_build.py
  python projects/oino-interlude/scripts/run_build.py --reset
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import (  # noqa: E402
    BEATMAP_JSON,
    CANON_PATH,
    MASTER_AUDIO,
    PIPELINE_CONFIG,
    PROJECT_JSON,
    PROJECT_ROOT,
    REPORTS_DIR,
    ensure_dirs,
    load_pipeline_config,
    require_file,
)


PLACEHOLDER_README = """# {title}

PLACEHOLDER — no authored assets yet.

Do not delete user-created files in this folder.
Pipeline scripts skip existing named assets unless ``--reset`` is passed
(and even then, never touch audio / CANON / beatmap / project.json).
"""


ASSET_PLACEHOLDERS = {
    "assets/characters/README.md": "Characters (Oino, Sister, Father, Watcher)",
    "assets/environments/README.md": "Environments (table, archive, industrial eras, Zone)",
    "assets/materials/README.md": "Materials (source materials recoverable in SOURCE_Materials)",
    "assets/props/README.md": "Props (melody object, archive media, dinner setting)",
    "scenes/README.md": "Blender .blend scenes (SCN_* names from config/pipeline.json)",
    "cache/README.md": "Caches and versioned run reports (safe to regenerate)",
}


def _write_placeholder(path: Path, title: str, report: RunReport, *, reset: bool) -> None:
    if path.exists() and not reset:
        report.mark("reused", str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
        return
    if path.exists() and reset:
        report.mark("skipped", f"reset_refused_existing:{path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PLACEHOLDER_README.format(title=title), encoding="utf-8")
    report.mark("created", str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Oino Interlude foundation build")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reserved: does not delete preserved user/canon/audio files",
    )
    parser.add_argument("--seed", type=int, default=None, help="Override config seed")
    args = parser.parse_args()

    cfg = load_pipeline_config() if PIPELINE_CONFIG.is_file() else {}
    seed = args.seed if args.seed is not None else int(cfg.get("seed", 20261210))
    random.seed(seed)

    report = RunReport(script="run_build", seed=seed, reset=args.reset)
    report.note(f"project_root={PROJECT_ROOT}")
    report.note(f"seed={seed}")
    if args.reset:
        report.note(
            "reset flag set — still preserving audio, CANON, beatmap, project.json, user assets"
        )

    # Required preserved inputs
    try:
        require_file(MASTER_AUDIO, "master audio")
        report.mark("reused", "audio/master.wav")
    except FileNotFoundError as exc:
        report.fail("audio/master.wav", exc)
        report.write(REPORTS_DIR)
        return 1

    for label, path in (
        ("CANON", CANON_PATH),
        ("project.json", PROJECT_JSON),
        ("beatmap.json", BEATMAP_JSON),
        ("pipeline.json", PIPELINE_CONFIG),
    ):
        if path.is_file():
            report.mark("reused", str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
        else:
            report.fail(str(path), f"missing required {label}")

    if report.failed and not PIPELINE_CONFIG.is_file():
        report.write(REPORTS_DIR)
        return 1

    dir_result = ensure_dirs()
    for rel in dir_result["created"]:
        report.mark("created", rel + "/")
    for rel in dir_result["reused"]:
        report.mark("reused", rel + "/")

    for rel, title in ASSET_PLACEHOLDERS.items():
        _write_placeholder(PROJECT_ROOT / rel, title, report, reset=False)

    # Refresh missing_placeholders inventory without wiping user edits to pipeline.json
    try:
        cfg = load_pipeline_config()
        missing = cfg.get("missing_placeholders") or {}
        blender = cfg.get("blender") or {}
        if not blender.get("exe"):
            report.note(
                "PLACEHOLDER blender.exe — set config/pipeline.json blender.exe "
                "or env BLENDER_PATH / BLENDER_EXE"
            )
        for key, val in missing.items():
            if val is None:
                report.note(f"PLACEHOLDER missing asset key: {key}")
        cfg["last_foundation_build"] = report.started_at
        PIPELINE_CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        report.mark("reused", "config/pipeline.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("config/pipeline.json", exc)

    report.note("No detailed scenery built (foundation only).")
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY created={len(report.created)} reused={len(report.reused)} "
        f"skipped={len(report.skipped)} failed={len(report.failed)} ok={report.ok}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
