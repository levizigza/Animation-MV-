"""Prepare Oino review render versions and output paths.

Versions: ANIMATIC_REVIEW, PERFORMANCE_REVIEW, WORLD_REVIEW,
COLOUR_REVIEW, TITLE_CARD_REVIEW, FINAL_REVIEW.

Creates per-version manifests and directories under renders/review/.
Optional slate preview with full audio when --write-slate is passed.
Emotional QA stays in docs/emotional_qa.md — never on screen.

Usage:
  python scripts/render_review_versions.py
  python scripts/render_review_versions.py --write-slate
  python scripts/render_review_versions.py --only TITLE_CARD_REVIEW FINAL_REVIEW
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import wave
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
from show_config import load_show_config, resolve_render_engine  # noqa: E402

REVIEW_JSON = DOCS_DIR / "review_versions.json"
STATUS_MD = DOCS_DIR / "review_versions.md"
EMOTIONAL_QA = DOCS_DIR / "emotional_qa.md"
REVIEW_ROOT = RENDERS_DIR / "review"

REQUIRED_VERSIONS = (
    "ANIMATIC_REVIEW",
    "PERFORMANCE_REVIEW",
    "WORLD_REVIEW",
    "COLOUR_REVIEW",
    "TITLE_CARD_REVIEW",
    "FINAL_REVIEW",
)

TITLE_EXACT = "One Of Gods Fools"
DATE_EXACT = "December 10, 2026"


def load_review() -> dict[str, Any]:
    if not REVIEW_JSON.is_file():
        raise FileNotFoundError(f"Missing {REVIEW_JSON}")
    return json.loads(REVIEW_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if (data.get("policy") or {}).get("emotional_qa_on_screen") is not False:
        errors.append("policy.emotional_qa_on_screen must be false")
    card = data.get("title_card_exact") or {}
    if card.get("text") != TITLE_EXACT:
        errors.append(f"title_card_exact.text must be '{TITLE_EXACT}'")
    if card.get("date") != DATE_EXACT:
        errors.append(f"title_card_exact.date must be '{DATE_EXACT}'")
    versions = data.get("versions") or []
    ids = [v.get("id") for v in versions]
    if len(ids) != len(set(ids)):
        errors.append("review version ids must be unique")
    for req in REQUIRED_VERSIONS:
        if req not in ids:
            errors.append(f"Missing review version: {req}")
    if len(versions) != len(REQUIRED_VERSIONS):
        errors.append(
            f"Expected exactly {len(REQUIRED_VERSIONS)} versions, found {len(versions)}"
        )
    for v in versions:
        vid = v.get("id", "?")
        for key in ("label", "purpose", "resolution_key", "output_subdir"):
            if not (v.get(key) or "").strip():
                errors.append(f"{vid}: {key} required")
        if not isinstance(v.get("emotional_qa_subset"), list):
            errors.append(f"{vid}: emotional_qa_subset list required")
    return errors


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate() or 1)


def write_version_manifest(
    version: dict[str, Any],
    *,
    cfg: dict[str, Any],
    engine: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    res_key = version.get("resolution_key") or "hd"
    res = (cfg.get("resolutions") or {}).get(res_key) or [1920, 1080]
    fps = int((cfg.get("timing") or {}).get("fps") or 24)
    rel_dir = str(out_dir.relative_to(PROJECT_ROOT)).replace("\\", "/")
    movie_name = f"{version['id']}.mp4"
    manifest = {
        "id": version["id"],
        "label": version.get("label"),
        "purpose": version.get("purpose"),
        "focus": version.get("focus") or [],
        "emotional_qa_subset": version.get("emotional_qa_subset") or [],
        "emotional_qa_doc": "docs/emotional_qa.md",
        "emotional_qa_on_screen": False,
        "resolution": res,
        "fps": fps,
        "audio": version.get("audio") or "full",
        "audio_path": "audio/master.wav",
        "title_card_exact": {
            "text": TITLE_EXACT,
            "date": DATE_EXACT,
        },
        "output_dir": rel_dir,
        "output_movie": f"{rel_dir}/{movie_name}",
        "blender_engine": engine.get("engine"),
        "blender_exe": engine.get("blender_exe"),
        "status": "paths_ready",
        "note": "Render from approved scene packages into this folder. Do not burn emotional QA onto picture.",
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                f"# {version['id']}",
                "",
                f"**Purpose:** {version.get('purpose')}",
                "",
                f"**Output:** `{movie_name}`",
                "",
                "**Emotional QA:** see `docs/emotional_qa.md` — development only, never on screen.",
                "",
                f"**Subset questions:** {version.get('emotional_qa_subset')}",
                "",
                f"**Exact title card (when applicable):** {TITLE_EXACT} / {DATE_EXACT}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def write_slate(
    version: dict[str, Any],
    out_dir: Path,
    audio_path: Path,
    duration_s: float,
    resolution: list[int],
    report: RunReport,
) -> dict[str, Any]:
    movie = out_dir / f"{version['id']}.mp4"
    w, h = int(resolution[0]), int(resolution[1])
    label = version["id"].replace("_", " ")
    # Simple colour slate + full audio — not a picture finish
    vf = (
        f"drawtext=text='{label}':x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"fontsize=36:fontcolor=0xE8E4DC:font=Sans,"
        f"drawtext=text='DEV REVIEW SLATE - NOT PICTURE LOCK':"
        f"x=(w-text_w)/2:y=(h-text_h)/2+20:fontsize=18:fontcolor=0xA8A098:font=Sans"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0A0A0A:s={w}x{h}:d={duration_s:.6f}:r=24",
        "-i",
        str(audio_path.resolve()),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(movie.resolve()),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return {"status": "skipped", "detail": "ffmpeg not found"}
    if proc.returncode != 0 or not movie.is_file():
        # retry without drawtext
        cmd2 = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0A0A0A:s={w}x{h}:d={duration_s:.6f}:r=24",
            "-i",
            str(audio_path.resolve()),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(movie.resolve()),
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        if proc2.returncode != 0 or not movie.is_file():
            return {
                "status": "failed",
                "detail": (proc2.stderr or proc.stderr or "")[-1500:],
            }
    return {
        "status": "created",
        "path": str(movie.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "note": "Slate with full audio — replace with real review renders when Blender packages are ready",
    }


def write_status(data: dict[str, Any], results: list[dict[str, Any]], report: RunReport) -> Path:
    lines = [
        "# Review versions — Oino (Interlude)",
        "",
        "**Emotional QA is not part of the film.** See [`emotional_qa.md`](emotional_qa.md).",
        "",
        f"**Title card lock:** `{TITLE_EXACT}` / `{DATE_EXACT}`",
        "",
        "| Version | Purpose | Output | Status |",
        "|---------|---------|--------|--------|",
    ]
    for r in results:
        lines.append(
            f"| `{r['id']}` | {r.get('purpose', '')} | `{r.get('output_dir')}` | "
            f"{r.get('slate_status') or r.get('status')} |"
        )
    lines += [
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/render_review_versions.py",
        "python scripts/render_review_versions.py --write-slate",
        "python scripts/qa_project.py",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/review_versions.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Oino review render versions")
    parser.add_argument(
        "--write-slate",
        action="store_true",
        help="Write placeholder slate MP4s with full audio into each review folder",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=[],
        help="Limit to specific version ids",
    )
    args = parser.parse_args()

    report = RunReport(script="render_review_versions", seed=20261210)
    try:
        data = load_review()
        report.mark("reused", "docs/review_versions.json")
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

    if not EMOTIONAL_QA.is_file():
        report.fail("emotional_qa", f"Missing {EMOTIONAL_QA}")
        report.write(REPORTS_DIR)
        return 1
    report.mark("reused", "docs/emotional_qa.md")

    cfg = load_show_config()
    engine = resolve_render_engine(cfg)
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)

    audio_path = MASTER_AUDIO
    music_rel = ((cfg.get("audio") or {}).get("mixed_master_path") or "audio/master.wav")
    cand = PROJECT_ROOT / music_rel
    if cand.is_file():
        audio_path = cand
    duration_s = 8.0
    if audio_path.is_file():
        try:
            duration_s = audio_duration(audio_path)
            report.mark("reused", str(audio_path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
        except Exception as exc:  # noqa: BLE001
            report.note(f"Audio duration fallback: {exc}")

    only = set(args.only or [])
    results: list[dict[str, Any]] = []
    for version in data.get("versions") or []:
        vid = version["id"]
        if only and vid not in only:
            continue
        out_dir = REVIEW_ROOT / version["output_subdir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = write_version_manifest(
            version, cfg=cfg, engine=engine, out_dir=out_dir
        )
        report.mark("created", f"renders/review/{version['output_subdir']}/manifest.json")
        entry = {
            "id": vid,
            "purpose": version.get("purpose"),
            "output_dir": manifest["output_dir"],
            "status": "paths_ready",
        }
        if args.write_slate:
            res = manifest["resolution"]
            slate = write_slate(
                version, out_dir, audio_path, duration_s, res, report
            )
            entry["slate_status"] = slate.get("status")
            entry["slate"] = slate
            if slate.get("status") == "created":
                report.mark("created", slate["path"])
            elif slate.get("status") == "failed":
                report.fail(vid, slate.get("detail") or "slate failed")
            else:
                report.note(f"{vid}: slate {slate.get('status')}")
        results.append(entry)

    write_status(data, results, report)
    report.note(
        "Review folders ready; emotional QA off-screen only; "
        f"title lock '{TITLE_EXACT}' / '{DATE_EXACT}'"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} versions={len(results)} "
        f"root=renders/review slate={bool(args.write_slate)}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
