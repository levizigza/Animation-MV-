"""Canonical paths for the Oino (Interlude) Blender production tree.

Safe to import from other scripts. Does not modify the filesystem unless
``ensure_dirs()`` is called.
"""

from __future__ import annotations

import json
from pathlib import Path

# projects/oino-interlude/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]

AUDIO_DIR = PROJECT_ROOT / "audio"
ASSETS_DIR = PROJECT_ROOT / "assets"
CHARACTERS_DIR = ASSETS_DIR / "characters"
ENVIRONMENTS_DIR = ASSETS_DIR / "environments"
MATERIALS_DIR = ASSETS_DIR / "materials"
PROPS_DIR = ASSETS_DIR / "props"
CACHE_DIR = PROJECT_ROOT / "cache"
CONFIG_DIR = PROJECT_ROOT / "config"
DOCS_DIR = PROJECT_ROOT / "docs"
SCENES_DIR = PROJECT_ROOT / "scenes"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RENDERS_DIR = PROJECT_ROOT / "renders"
RENDERS_ANIMATIC = RENDERS_DIR / "animatic"
RENDERS_PREVIEW = RENDERS_DIR / "preview"
RENDERS_FINAL = RENDERS_DIR / "final"
REPORTS_DIR = CACHE_DIR / "reports"

MASTER_AUDIO = AUDIO_DIR / "master.wav"
PIPELINE_CONFIG = CONFIG_DIR / "pipeline.json"
SHOW_CONFIG = CONFIG_DIR / "show_config.json"
CANON_PATH = PROJECT_ROOT / "CANON.md"
PROJECT_JSON = PROJECT_ROOT / "project.json"
BEATMAP_JSON = PROJECT_ROOT / "beatmap.json"

REQUIRED_DIRS = (
    AUDIO_DIR,
    CHARACTERS_DIR,
    ENVIRONMENTS_DIR,
    MATERIALS_DIR,
    PROPS_DIR,
    CACHE_DIR,
    CONFIG_DIR,
    DOCS_DIR,
    SCENES_DIR,
    SCRIPTS_DIR,
    RENDERS_ANIMATIC,
    RENDERS_PREVIEW,
    RENDERS_FINAL,
    REPORTS_DIR,
)


def load_pipeline_config() -> dict:
    if not PIPELINE_CONFIG.is_file():
        raise FileNotFoundError(
            f"Missing pipeline config: {PIPELINE_CONFIG}. "
            "Run scripts/run_build.py once to recreate the foundation."
        )
    return json.loads(PIPELINE_CONFIG.read_text(encoding="utf-8"))


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required {label} missing: {path}. "
            "Restore from backup or re-copy the asset before continuing."
        )
    return path


def ensure_dirs(*, dry_run: bool = False) -> dict[str, list[str]]:
    """Create production directories if missing. Idempotent."""
    created: list[str] = []
    reused: list[str] = []
    for d in REQUIRED_DIRS:
        rel = str(d.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if d.is_dir():
            reused.append(rel)
            continue
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)
            # Keep empty dirs visible in git-like trees
            keep = d / ".gitkeep"
            if not keep.exists():
                keep.write_text("", encoding="utf-8")
        created.append(rel)
    return {"created": created, "reused": reused, "skipped": [], "failed": []}
