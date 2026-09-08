"""Build ANIMATIC_MASTER — proxy animatic for the full Oino film.

Creates shot list docs, marker bundle, Blender payload, and (when Blender is
available) ``scenes/ANIMATIC_MASTER.blend`` with collections, cameras, proxies,
text, audio, and timeline markers.

Usage:
  python scripts/setup_animatic.py
  python scripts/setup_animatic.py --write-blend
  python scripts/setup_animatic.py --write-blend --reset
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
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR, SCENES_DIR  # noqa: E402
from show_config import load_show_config, resolve_render_engine  # noqa: E402

SHOT_LIST = DOCS_DIR / "animatic_shot_list.json"
MARKERS_OUT = DOCS_DIR / "animatic_markers.json"
REPORT_MD = DOCS_DIR / "animatic_status.md"
BLEND_OUT = SCENES_DIR / "ANIMATIC_MASTER.blend"
BLENDER_SCRIPT = SCRIPTS_DIR / "_blender_animatic_master.py"
PAYLOAD = PROJECT_ROOT / "cache" / "animatic_master_payload.json"
BLENDER_RUN_REPORT = PROJECT_ROOT / "cache" / "animatic_blender_report.json"
AUDIO_MARKERS = DOCS_DIR / "audio_markers.json"


def _resolve(root: Path, rel: str | None) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    return p if p.is_absolute() else root / p


def load_shot_list() -> dict[str, Any]:
    if not SHOT_LIST.is_file():
        raise FileNotFoundError(f"Missing shot list: {SHOT_LIST}")
    return json.loads(SHOT_LIST.read_text(encoding="utf-8"))


def build_marker_bundle(shots: dict[str, Any], audio_markers: dict[str, Any] | None) -> dict[str, Any]:
    music_cues = list((audio_markers or {}).get("broad_cues") or [])
    structural = list((audio_markers or {}).get("structural_markers") or [])
    return {
        "schema_version": 1,
        "scene": "ANIMATIC_MASTER",
        "editable": True,
        "fps": shots["fps"],
        "final_frame": shots["final_frame"],
        "shot_markers": [
            {
                "name": s["id"],
                "frame": s["frame_start"],
                "frame_end": s["frame_end"],
                "note": s["beat"],
            }
            for s in shots["shots"]
        ],
        "story_circle_beats": shots["story_circle_beats"],
        "monologue_anchors": shots["monologue_anchors"],
        "music_cues": music_cues,
        "structural_audio_markers": structural,
        "priority_staging": shots.get("priority_staging"),
        "policy": shots.get("policy"),
    }


def write_status_md(
    cfg: dict[str, Any],
    shots: dict[str, Any],
    blender_status: dict[str, Any],
    report: RunReport,
) -> Path:
    lines = [
        "# Animatic status — ANIMATIC_MASTER",
        "",
        f"**Film:** {cfg.get('film_title')} · **Album:** {cfg.get('project_title')}",
        f"**Scene:** `ANIMATIC_MASTER` · **Audio VSE:** shared cues / mixed master",
        "",
        "## Intent",
        "",
        "Full-film animatic with **primitive proxies only** — staging, rhythm, eyelines,",
        "Oino's hand, the table, the knock, and the final changed melody.",
        "No detailed modelling. Do not cut to every beat.",
        "",
        "## Collections",
        "",
    ]
    for c in shots["collections"]:
        lines.append(f"- `{c}`")
    lines += ["", "## Shots", "", "| Camera | Frames | Beat |", "|--------|--------|------|"]
    for s in shots["shots"]:
        lines.append(
            f"| `{s['camera']}` | {s['frame_start']}–{s['frame_end']} | {s['beat']} |"
        )
    lines += [
        "",
        "## Markers included",
        "",
        "- All shot start/end markers",
        "- Story Circle: SC_YOU … SC_CHANGE",
        "- Monologue anchors: MONO_*",
        "- Broad music cues from `audio_markers.json`",
        "- Structural audio markers (AUDIO_START, TITLE_CARD_*, …)",
        "",
        "## Blender",
        "",
        f"- Target: `{BLEND_OUT.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Status: **{blender_status.get('status')}**",
        f"- Detail: {blender_status.get('detail')}",
        "",
        "## Source files",
        "",
        "- [`animatic_shot_list.json`](animatic_shot_list.json)",
        "- [`animatic_markers.json`](animatic_markers.json)",
        "- [`audio_markers.json`](audio_markers.json)",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/animatic_status.md")
    return REPORT_MD


def try_write_blend(payload: dict[str, Any], *, write: bool, report: RunReport) -> dict[str, Any]:
    PAYLOAD.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "cache/animatic_master_payload.json")

    if not write:
        return {
            "status": "skipped",
            "detail": "Pass --write-blend to build scenes/ANIMATIC_MASTER.blend",
        }

    engine = resolve_render_engine(load_show_config())
    blender = engine.get("blender_exe")
    if not blender:
        report.note("Blender not installed — animatic blend deferred")
        return {
            "status": "deferred",
            "detail": (
                "Blender not found. Payload ready; install Blender then re-run "
                "with --write-blend"
            ),
        }

    if BLEND_OUT.exists() and not payload.get("reset"):
        report.mark("reused", "scenes/ANIMATIC_MASTER.blend")
        return {
            "status": "reused",
            "detail": "Existing blend preserved (pass --reset to rebuild proxies)",
        }

    cmd = [
        str(blender),
        "--background",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(PAYLOAD),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not BLEND_OUT.exists():
        err = (proc.stderr or proc.stdout or "")[-2000:]
        report.fail("ANIMATIC_MASTER.blend", err or f"exit {proc.returncode}")
        return {"status": "failed", "detail": err}

    report.mark("created", "scenes/ANIMATIC_MASTER.blend")
    return {"status": "created", "detail": str(BLEND_OUT)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Oino ANIMATIC_MASTER setup")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Rebuild named animatic objects (does not delete other scenes/assets)",
    )
    args = parser.parse_args()

    report = RunReport(script="setup_animatic", seed=20261210, reset=args.reset)
    cfg = load_show_config()
    shots = load_shot_list()
    report.mark("reused", "docs/animatic_shot_list.json")

    audio_markers = None
    if AUDIO_MARKERS.is_file():
        audio_markers = json.loads(AUDIO_MARKERS.read_text(encoding="utf-8"))
        report.mark("reused", "docs/audio_markers.json")

    bundle = build_marker_bundle(shots, audio_markers)
    MARKERS_OUT.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/animatic_markers.json")

    audio = cfg.get("audio") or {}
    music = _resolve(PROJECT_ROOT, audio.get("mixed_master_path") or audio.get("music_path"))
    narr = _resolve(PROJECT_ROOT, audio.get("narration_path"))
    if music is None or not music.is_file():
        report.fail("music", "Configured music/mixed master missing")
        report.write(REPORTS_DIR)
        return 1
    report.mark("reused", str(music.relative_to(PROJECT_ROOT)).replace("\\", "/"))

    engine_info = resolve_render_engine(cfg)
    title = cfg.get("title_card") or {
        "text": cfg.get("project_title"),
        "release_date": cfg.get("release_date"),
    }

    payload = {
        "fps": shots["fps"],
        "final_frame": shots["final_frame"],
        "resolution": (cfg.get("resolutions") or {}).get("hd") or [1920, 1080],
        "engine": engine_info.get("engine") or "BLENDER_EEVEE_NEXT",
        "collections": shots["collections"],
        "shots": shots["shots"],
        "story_circle_beats": shots["story_circle_beats"],
        "monologue_anchors": shots["monologue_anchors"],
        "music_cues": bundle["music_cues"],
        "structural_audio_markers": bundle["structural_audio_markers"],
        "music_path": str(music.resolve()),
        "narration_path": str(narr.resolve()) if narr and narr.is_file() else None,
        "title_card": title,
        "blend_out": str(BLEND_OUT.resolve()),
        "report_out": str(BLENDER_RUN_REPORT.resolve()),
        "reset": args.reset,
    }

    # Ensure bpy helper exists beside this script (already authored)
    if not BLENDER_SCRIPT.is_file():
        report.fail("_blender_animatic_master.py", "Helper script missing")
        report.write(REPORTS_DIR)
        return 1
    report.mark("reused", "scripts/_blender_animatic_master.py")

    blender_status = try_write_blend(payload, write=args.write_blend, report=report)
    write_status_md(cfg, shots, blender_status, report)

    report.note(
        "Priority staging: eyelines, Oino_Hand, PROP_Table, knock, changed melody — "
        "not every visual idea animated yet"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} shots={len(shots['shots'])} "
        f"blend={blender_status['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
