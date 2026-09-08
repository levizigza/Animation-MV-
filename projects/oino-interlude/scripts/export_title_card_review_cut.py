"""Export a versioned TITLE_CARD_REVIEW cut from existing locked assets.

Compares current title still to the delivery lock PNG; refuses to replace
mismatched assets. Does not rebuild title-card authoring or final delivery.

Scene: SCN_13_TITLE_CARD
Shot:  SH130_TITLE_CARD
Frames: 3051–3148 (global)

Usage:
  python scripts/export_title_card_review_cut.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import (  # noqa: E402
    DOCS_DIR,
    MASTER_AUDIO,
    PROJECT_ROOT,
    RENDERS_DIR,
    REPORTS_DIR,
)

TITLE_EXACT = "One Of Gods Fools"
DATE_EXACT = "December 10, 2026"
SCENE = "SCN_13_TITLE_CARD"
SHOT = "SH130_TITLE_CARD"
FRAME_START = 3051
FRAME_END = 3148
FPS = 24

STILL_SRC = RENDERS_DIR / "final" / "delivery" / "stills" / "title_card_still.png"
LOCK_SRC = RENDERS_DIR / "final" / "delivery" / "assets" / "title_card_lock.png"
BRIEF = DOCS_DIR / "title_card_brief.json"
REVIEW_ROOT = RENDERS_DIR / "review" / "TITLE_CARD_REVIEW"


def _utc() -> str:
    return datetime.now(timezone.utc)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report = RunReport(script="export_title_card_review_cut", seed=20261210)
    stamp = _utc().strftime("%Y%m%dT%H%M%SZ")
    version_id = f"v{stamp}_{SHOT}"
    out_dir = REVIEW_ROOT / version_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not STILL_SRC.is_file() or not LOCK_SRC.is_file():
        report.fail("assets", "Missing title_card_still.png or title_card_lock.png")
        report.write(REPORTS_DIR)
        return 1

    still_hash = sha256(STILL_SRC)
    lock_hash = sha256(LOCK_SRC)
    if still_hash != lock_hash:
        report.fail(
            "compare",
            "title_card_still.png differs from title_card_lock.png — refuse replace",
        )
        report.write(REPORTS_DIR)
        return 1
    report.note(f"Compared still==lock sha256={still_hash[:16]}…")

    if BRIEF.is_file():
        brief = json.loads(BRIEF.read_text(encoding="utf-8"))
        title = (brief.get("title") or {}).get("text")
        date = (brief.get("release_date") or {}).get("text")
        if title != TITLE_EXACT or date != DATE_EXACT:
            report.fail("title_lock", f"brief mismatch title={title!r} date={date!r}")
            report.write(REPORTS_DIR)
            return 1
        if "'" in title or "\u2019" in title:
            report.fail("title_lock", "Apostrophe in Gods forbidden")
            report.write(REPORTS_DIR)
            return 1
        report.mark("reused", "docs/title_card_brief.json")

    still_out = out_dir / "title_card_still.png"
    shutil.copy2(STILL_SRC, still_out)
    report.mark(
        "created",
        str(still_out.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    )

    audio = MASTER_AUDIO
    if not audio.is_file():
        report.fail("audio", f"Missing {audio}")
        report.write(REPORTS_DIR)
        return 1

    start_t = (FRAME_START - 1) / FPS
    duration_s = (FRAME_END - FRAME_START + 1) / FPS
    movie = out_dir / f"{SHOT}_f{FRAME_START}-{FRAME_END}.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(still_out.resolve()),
        "-ss",
        f"{start_t:.6f}",
        "-t",
        f"{duration_s:.6f}",
        "-i",
        str(audio.resolve()),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        "-t",
        f"{duration_s:.6f}",
        "-shortest",
        "-movflags",
        "+faststart",
        str(movie.resolve()),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not movie.is_file():
        report.fail("encode", (proc.stderr or "")[-1500:])
        report.write(REPORTS_DIR)
        return 1
    report.mark("created", str(movie.relative_to(PROJECT_ROOT)).replace("\\", "/"))

    meta: dict[str, Any] = {
        "schema_version": 1,
        "version_id": version_id,
        "created_at": _utc().isoformat(),
        "scene": SCENE,
        "shot": SHOT,
        "frame_start": FRAME_START,
        "frame_end": FRAME_END,
        "fps": FPS,
        "duration_seconds": duration_s,
        "title_card": {
            "text": TITLE_EXACT,
            "date": DATE_EXACT,
            "apostrophe_in_Gods": False,
            "extra_title_or_logline": False,
        },
        "sources_compared": {
            "title_card_still": str(STILL_SRC.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "title_card_lock": str(LOCK_SRC.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": still_hash,
            "identical": True,
        },
        "audio": str(audio.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "outputs": {
            "movie": str(movie.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "still": str(still_out.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        },
        "inspect": (
            f"Open {movie.name}; confirm exact title '{TITLE_EXACT}', "
            f"date '{DATE_EXACT}', no apostrophe, no extra logline, last note audible."
        ),
        "status": "ready_for_human_inspect",
        "not_picture_lock": True,
        "note": "Proxy from locked still + master audio segment. Blender SCN_13_TITLE_CARD.blend still deferred.",
    }
    (out_dir / "version.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    report.mark(
        "created",
        str((out_dir / "version.json").relative_to(PROJECT_ROOT)).replace("\\", "/"),
    )

    inspect_md = "\n".join(
        [
            f"# Inspect — {version_id}",
            "",
            f"- **Scene:** `{SCENE}`",
            f"- **Shot:** `{SHOT}`",
            f"- **Frame range:** `{FRAME_START}`–`{FRAME_END}` ({FPS} fps)",
            f"- **Movie:** `{meta['outputs']['movie']}`",
            f"- **Still:** `{meta['outputs']['still']}`",
            "",
            "## Check",
            "",
            f"1. Title reads exactly `{TITLE_EXACT}` (Gods has **no** apostrophe).",
            f"2. Date reads exactly `{DATE_EXACT}`.",
            "3. No extra title, logline, or credit.",
            "4. Title remains readable on near-black.",
            "5. Last living note / imperfect recording ending is audible before/through hold.",
            "",
            "## Status",
            "",
            "- Ready for human inspect — **not** picture lock.",
            "- Blender `.blend` for this scene remains deferred until Blender is installed.",
            "",
        ]
    )
    (out_dir / "INSPECT.md").write_text(inspect_md + "\n", encoding="utf-8")
    report.mark(
        "created",
        str((out_dir / "INSPECT.md").relative_to(PROJECT_ROOT)).replace("\\", "/"),
    )

    # Pointer for current version history
    latest = REVIEW_ROOT / "LATEST_VERSION.json"
    latest.write_text(
        json.dumps(
            {
                "latest_version_id": version_id,
                "path": str(out_dir.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "scene": SCENE,
                "shot": SHOT,
                "frame_range": [FRAME_START, FRAME_END],
                "movie": meta["outputs"]["movie"],
                "updated_at": meta["created_at"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report.mark("created", "renders/review/TITLE_CARD_REVIEW/LATEST_VERSION.json")

    report.note(f"Inspect {meta['outputs']['movie']}")
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={SCENE} shot={SHOT} "
        f"frames={FRAME_START}-{FRAME_END} out={meta['outputs']['movie']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
