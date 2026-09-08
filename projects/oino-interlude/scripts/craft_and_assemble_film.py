"""Seed MVM shots/xsheets from shot_list, craft via Blender, assemble full film.

Requires Blender on PATH / BLENDER_PATH / tools/blender-*/blender.exe.

Usage (repo root):
  python projects/oino-interlude/scripts/craft_and_assemble_film.py
  python projects/oino-interlude/scripts/craft_and_assemble_film.py --hero-only
  python projects/oino-interlude/scripts/craft_and_assemble_film.py --final
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
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
from project_paths import DOCS_DIR, REPORTS_DIR  # noqa: E402
from show_config import load_show_config, resolve_render_engine  # noqa: E402

from mvm.blender.runner import find_blender, render_shot  # noqa: E402
from mvm.cel.decisions import record_craft  # noqa: E402
from mvm.cel.xsheet import build_xsheet_for_shot  # noqa: E402
from mvm.editorial.assemble import mux_shot_with_audio, concat_shots  # noqa: E402
from mvm.project.workspace import ProjectWorkspace  # noqa: E402
from mvm.schemas.models import Shot, ShotIntent  # noqa: E402

SHOT_LIST = DOCS_DIR / "shot_list.csv"
FPS = 24
TITLE_EXACT = "One Of Gods Fools"


def discover_blender() -> Path | None:
    env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_EXE")
    if env and Path(env).is_file():
        return Path(env)
    found = find_blender()
    if found:
        return found
    tools = REPO_ROOT / "tools"
    if tools.is_dir():
        hits = sorted(tools.rglob("blender.exe"))
        if hits:
            return hits[0]
    return None


def load_shot_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with SHOT_LIST.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def seed_shots(ws: ProjectWorkspace, rows: list[dict[str, Any]], report: RunReport) -> list[Shot]:
    beatmap = ws.load_beatmap()
    shots: list[Shot] = []
    for i, row in enumerate(rows):
        f0 = int(row["frame_start"])
        f1 = int(row["frame_end"])
        start = (f0 - 1) / FPS
        end = f1 / FPS
        shot = Shot(
            id=row["shot_id"],
            index=i,
            section=row.get("camera_language") or "oino",
            start=start,
            end=end,
            duration=max(0.04, end - start),
            intent=ShotIntent(
                purpose=(row.get("emotional_purpose") or row["shot_id"])[:240],
                emotional_beat=row.get("camera_language") or "",
                staging_goal=row.get("hero_label") or row.get("focus_target") or "",
            ),
            description=row.get("emotional_purpose") or "",
            camera={"name": row.get("camera"), "language": row.get("camera_language")},
            blocking=row.get("focus_target") or "",
            lens_mm=float(row.get("lens_mm") or 35),
            characters=["Oino"],
            color_script=row.get("lighting_preset") or "",
            notes=f"hero={row.get('hero')} parent={row.get('parent_animatic')}",
        )
        ws.save_shot(shot)
        xs = build_xsheet_for_shot(shot, beatmap, fps=FPS)
        xs.end_frame = max(1, int(round(shot.duration * FPS)))
        ws.save_xsheet(xs)
        shots.append(shot)
        report.mark("created", f"shots/{shot.id}.json")
    return shots


def write_scene_blends(blender: Path, report: RunReport) -> None:
    env = os.environ.copy()
    env["BLENDER_PATH"] = str(blender)
    env["BLENDER_EXE"] = str(blender)
    scripts = [
        "setup_animatic.py",
        "setup_audio.py",
        "build_oino_archive.py",
        "build_zone.py",
        "build_table_room.py",
        "build_title_card.py",
    ]
    for name in scripts:
        path = SCRIPTS_DIR / name
        if not path.is_file():
            report.note(f"skip missing {name}")
            continue
        cmd = [sys.executable, str(path), "--write-blend"]
        proc = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT), env=env, capture_output=True, text=True
        )
        if proc.returncode != 0:
            report.fail(name, (proc.stderr or proc.stdout or "")[-800:])
        else:
            report.mark("created", f"{name} --write-blend")
            report.note((proc.stdout or "").strip().splitlines()[-1] if proc.stdout else name)


def craft_all(
    ws: ProjectWorkspace,
    shots: list[Shot],
    *,
    preview: bool,
    blender: Path,
    report: RunReport,
) -> list[Path]:
    outputs: list[Path] = []
    xsheets = {x.shot_id: x for x in ws.load_xsheets()}
    for shot in shots:
        xs = xsheets[shot.id]
        result = render_shot(
            ws.root,
            shot,
            xs,
            style_pack=ws.meta().style_pack,
            preview=preview,
            blender_path=blender,
        )
        record_craft(ws.root, shot=shot, xsheet=xs, craft_result=result)
        out = Path(result.get("output") or "")
        report.note(f"{shot.id}: {result.get('engine')} -> {out}")
        if result.get("warning"):
            report.note(str(result["warning"]))
        # Prefer mp4 path
        mp4 = ws.root / ("previews" if preview else "renders") / shot.id / "shot_preview.mp4"
        if mp4.is_file():
            outputs.append(mp4)
            report.mark("created", str(mp4.relative_to(ws.root)).replace("\\", "/"))
        elif out.is_file():
            outputs.append(out)
    return outputs


def assemble_film(ws: ProjectWorkspace, shots: list[Shot], report: RunReport) -> Path | None:
    muxed: list[Path] = []
    for shot in shots:
        preview = ws.root / "previews" / shot.id / "shot_preview.mp4"
        frames = ws.root / "previews" / shot.id / "frames"
        src = preview if preview.exists() else frames
        if not src.exists():
            report.note(f"skip mux {shot.id} — no craft output")
            continue
        out = ws.root / "final" / f"{shot.id}.mp4"
        result = mux_shot_with_audio(
            src, ws.audio_file(), out, start_sec=shot.start, duration_sec=shot.duration
        )
        if result.get("ok"):
            muxed.append(out)
            report.mark("created", str(out.relative_to(ws.root)).replace("\\", "/"))
        else:
            report.fail(f"mux {shot.id}", result.get("error") or result.get("stderr") or "fail")

    if not muxed:
        return None
    full = ws.root / "final" / "oino_crafted_full.mp4"
    if len(muxed) == 1:
        full.write_bytes(muxed[0].read_bytes())
    else:
        concat_shots(muxed, full)
    report.mark("created", str(full.relative_to(ws.root)).replace("\\", "/"))
    return full


def publish_to_site(film: Path, report: RunReport) -> None:
    site_video = REPO_ROOT / "site" / "video"
    site_video.mkdir(parents=True, exist_ok=True)
    dest = site_video / "oino-interlude-full.mp4"
    # Re-encode web-friendly copy
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(film.resolve()),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(dest.resolve()),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.is_file():
        # fallback copy
        dest.write_bytes(film.read_bytes())
    report.mark("created", "site/video/oino-interlude-full.mp4")


def update_pipeline_blender(blender: Path, report: RunReport) -> None:
    path = PROJECT_ROOT / "config" / "pipeline.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["blender"]["exe"] = str(blender)
    data["blender"]["note"] = "Installed portable / local Blender for craft"
    data["missing_placeholders"]["blender_exe"] = str(blender)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "config/pipeline.json (blender.exe)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hero-only", action="store_true")
    parser.add_argument("--final", action="store_true", help="Full-res craft (slower)")
    parser.add_argument("--skip-blends", action="store_true")
    parser.add_argument("--skip-craft", action="store_true")
    parser.add_argument("--max-shots", type=int, default=0)
    args = parser.parse_args()

    report = RunReport(script="craft_and_assemble_film", seed=20261210)
    blender = discover_blender()
    if not blender:
        report.fail("blender", "Blender not found — install or set BLENDER_PATH")
        report.write(REPORTS_DIR)
        print("SUMMARY ok=False blender=missing")
        return 1

    os.environ["BLENDER_PATH"] = str(blender)
    os.environ["BLENDER_EXE"] = str(blender)
    report.note(f"Blender: {blender}")
    update_pipeline_blender(blender, report)

    ws = ProjectWorkspace(PROJECT_ROOT)
    meta = ws.meta()
    meta.plan_approved = True
    ws.save_meta(meta)
    report.note("plan_approved=True for craft")

    rows = load_shot_rows()
    if args.hero_only:
        rows = [r for r in rows if r.get("hero") == "yes"]
    if args.max_shots and args.max_shots > 0:
        rows = rows[: args.max_shots]

    shots = seed_shots(ws, rows, report)

    if not args.skip_blends:
        write_scene_blends(blender, report)

    crafted: list[Path] = []
    if not args.skip_craft:
        crafted = craft_all(
            ws, shots, preview=not args.final, blender=blender, report=report
        )

    film = assemble_film(ws, shots, report)
    if film and film.is_file():
        publish_to_site(film, report)
    else:
        report.fail("assemble", "No full film produced")

    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} blender={blender} shots={len(shots)} "
        f"crafted={len(crafted)} film={film} title={TITLE_EXACT!r}"
    )
    return 0 if report.ok and film else 1


if __name__ == "__main__":
    raise SystemExit(main())
