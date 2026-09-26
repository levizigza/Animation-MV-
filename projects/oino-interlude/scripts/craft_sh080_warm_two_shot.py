"""Nightly craft for SH080_WARM_TWO_SHOT — genuine father/Oino comfort beat.

Craft-first Blender plate only. Human gate stays required:
  - does NOT approve PERFORMANCE_REVIEW
  - does NOT auto-smooth
  - does NOT push creative merges

Success contract:
  - stdout includes SH080_PROOF_OK
  - engine must be real Blender (fallback_cel_preview is failure)
  - shot_preview.mp4 must be freshly written this run
  - review mp4 under renders/review/SH080_WARM_TWO_SHOT/

Usage (repo root):
  export BLENDER_PATH=...
  python projects/oino-interlude/scripts/craft_sh080_warm_two_shot.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = PROJECT_ROOT.parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from logging_utils import RunReport  # noqa: E402
from project_paths import REPORTS_DIR  # noqa: E402

from mvm.blender.ensure import ensure_blender  # noqa: E402
from mvm.blender.runner import find_blender, render_shot  # noqa: E402
from mvm.cel.decisions import record_craft  # noqa: E402
from mvm.project.workspace import ProjectWorkspace  # noqa: E402

SHOT_ID = "SH080_WARM_TWO_SHOT"
PROOF_TOKEN = "SH080_PROOF_OK"
REVIEW_ROOT = PROJECT_ROOT / "renders" / "review" / SHOT_ID
PREVIEW_DIR = PROJECT_ROOT / "previews" / SHOT_ID
PREVIEW_MP4 = PREVIEW_DIR / "shot_preview.mp4"
HUMAN_GATE_NOTE = (
    "Human gate required: PERFORMANCE_REVIEW not approved; "
    "no auto-smooth; no creative merge."
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_blender(*, allow_ensure: bool) -> Path:
    env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_EXE")
    if env and Path(env).is_file():
        return Path(env).resolve()
    found = find_blender()
    if found and found.is_file():
        return found.resolve()
    if not allow_ensure:
        raise FileNotFoundError(
            "Blender not found. Set BLENDER_PATH or run: python -m mvm.blender.ensure"
        )
    return ensure_blender()


def load_shot_and_xsheet(ws: ProjectWorkspace):
    shots = {s.id: s for s in ws.load_shots()}
    xsheets = {x.shot_id: x for x in ws.load_xsheets()}
    if SHOT_ID not in shots:
        raise FileNotFoundError(f"Missing shot {SHOT_ID}")
    if SHOT_ID not in xsheets:
        raise FileNotFoundError(f"Missing xsheet {SHOT_ID}")
    return shots[SHOT_ID], xsheets[SHOT_ID]


def file_mtime(path: Path) -> float | None:
    if not path.is_file():
        return None
    return path.stat().st_mtime


def require_fresh_preview(*, before_mtime: float | None, started_at: float) -> Path:
    if not PREVIEW_MP4.is_file():
        raise FileNotFoundError(f"Missing fresh preview: {PREVIEW_MP4}")
    size = PREVIEW_MP4.stat().st_size
    if size < 1024:
        raise RuntimeError(f"Preview too small ({size} bytes): {PREVIEW_MP4}")
    mtime = PREVIEW_MP4.stat().st_mtime
    if before_mtime is not None and mtime <= before_mtime + 0.001:
        raise RuntimeError(
            f"Stale shot_preview.mp4 (mtime unchanged): {PREVIEW_MP4}"
        )
    # Allow small filesystem timestamp skew, but require write after run start.
    if mtime + 1.0 < started_at:
        raise RuntimeError(
            f"Stale shot_preview.mp4 (mtime before run start): {PREVIEW_MP4}"
        )
    return PREVIEW_MP4


def publish_review(preview: Path, blender: Path, craft_result: dict[str, Any]) -> Path:
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    version_dir = REVIEW_ROOT / f"v{stamp}_{SHOT_ID}"
    version_dir.mkdir(parents=True, exist_ok=True)
    review_mp4 = version_dir / "shot_preview.mp4"
    shutil.copy2(preview, review_mp4)
    # Also refresh a stable pointer for nightly readers.
    stable = REVIEW_ROOT / "shot_preview.mp4"
    shutil.copy2(preview, stable)

    manifest = {
        "shot_id": SHOT_ID,
        "purpose": "Genuine comfort — why she stays; protect performance.",
        "engine": craft_result.get("engine"),
        "blender_path": str(blender),
        "preview_source": str(preview.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "review_mp4": str(review_mp4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "stable_review_mp4": str(stable.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "performance_review_approved": False,
        "auto_smooth": False,
        "creative_merge": False,
        "human_gate": HUMAN_GATE_NOTE,
        "canon": {
            "protagonist": "Oino",
            "beat": "father reunion genuinely comforts Oino before her shadow",
            "table": "ordinary/intimate/sacred destination",
        },
    }
    (version_dir / "version.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (REVIEW_ROOT / "manifest.json").write_text(
        json.dumps(
            {
                "shot_id": SHOT_ID,
                "latest_version": version_dir.name,
                "latest_mp4": str(review_mp4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "stable_mp4": str(stable.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "performance_review_approved": False,
                "human_gate": HUMAN_GATE_NOTE,
                "updated_at": manifest["created_at"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (REVIEW_ROOT / "README.md").write_text(
        "\n".join(
            [
                f"# {SHOT_ID}",
                "",
                "Nightly Blender craft review for the warm two-shot.",
                "",
                f"**Human gate:** {HUMAN_GATE_NOTE}",
                "",
                f"**Latest plate:** `{review_mp4.relative_to(PROJECT_ROOT).as_posix()}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return review_mp4


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Craft {SHOT_ID} Blender review plate")
    parser.add_argument(
        "--no-ensure",
        action="store_true",
        help="Fail if Blender is missing instead of downloading portable 4.5",
    )
    parser.add_argument(
        "--skip-record",
        action="store_true",
        help="Skip decisions.json craft record (still writes review plate)",
    )
    args = parser.parse_args()

    report = RunReport(script="craft_sh080_warm_two_shot", seed=20261210)
    started_at = time.time()
    before_mtime = file_mtime(PREVIEW_MP4)

    try:
        blender = resolve_blender(allow_ensure=not args.no_ensure)
    except Exception as exc:  # noqa: BLE001
        report.fail("blender", exc)
        report.write(REPORTS_DIR)
        print(f"SUMMARY ok=False blender=missing error={exc}")
        return 1

    os.environ["BLENDER_PATH"] = str(blender)
    os.environ["BLENDER_EXE"] = str(blender)
    report.note(f"Blender: {blender}")
    report.note(HUMAN_GATE_NOTE)

    ws = ProjectWorkspace(PROJECT_ROOT)
    try:
        shot, xsheet = load_shot_and_xsheet(ws)
    except Exception as exc:  # noqa: BLE001
        report.fail("load", exc)
        report.write(REPORTS_DIR)
        print(f"SUMMARY ok=False blender={blender} error={exc}")
        return 1

    # Touch output dir so mtime comparisons are meaningful even on first run.
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    result = render_shot(
        ws.root,
        shot,
        xsheet,
        style_pack=ws.meta().style_pack,
        preview=True,
        blender_path=blender,
    )
    engine = str(result.get("engine") or "")
    report.note(f"engine={engine} output={result.get('output')}")
    if result.get("warning"):
        report.note(str(result["warning"]))
    if engine != "blender":
        report.fail(
            "engine",
            f"expected blender craft, got {engine!r} "
            f"(fallback/stale plates are not success)",
        )
        if result.get("blender_stderr"):
            report.note(f"blender_stderr_tail={result['blender_stderr'][-1200:]}")
        if result.get("blender_stdout"):
            report.note(f"blender_stdout_tail={result['blender_stdout'][-1200:]}")
        report.write(REPORTS_DIR)
        print(f"SUMMARY ok=False blender={blender} engine={engine}")
        return 1

    try:
        preview = require_fresh_preview(before_mtime=before_mtime, started_at=started_at)
    except Exception as exc:  # noqa: BLE001
        report.fail("preview", exc)
        report.write(REPORTS_DIR)
        print(f"SUMMARY ok=False blender={blender} error={exc}")
        return 1

    if not args.skip_record:
        record_craft(ws.root, shot=shot, xsheet=xsheet, craft_result=result)
        report.mark("created", "decisions.json craft record")

    review_mp4 = publish_review(preview, blender, result)
    report.mark("created", str(review_mp4.relative_to(PROJECT_ROOT)).replace("\\", "/"))
    report.mark("created", str((REVIEW_ROOT / "shot_preview.mp4").relative_to(PROJECT_ROOT)).replace("\\", "/"))
    report.write(REPORTS_DIR)

    print(PROOF_TOKEN)
    print(
        f"SUMMARY ok=True blender={blender} preview={preview} "
        f"review={review_mp4} performance_review_approved=False"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
