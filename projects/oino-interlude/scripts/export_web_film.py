"""Build a full-length web-watchable Oino cut for GitHub Pages.

Proxy / animatic picture (shot boards) + approved master audio + locked title card.
Not Blender cel picture lock.

Usage (from repo root or oino-interlude):
  python projects/oino-interlude/scripts/export_web_film.py
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = PROJECT_ROOT.parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, MASTER_AUDIO, REPORTS_DIR  # noqa: E402

TITLE_EXACT = "One Of Gods Fools"
DATE_EXACT = "December 10, 2026"
FPS = 24
W, H = 1280, 720
SHOT_LIST = DOCS_DIR / "shot_list.csv"
AUDIO_MARKERS = DOCS_DIR / "audio_markers.json"
TITLE_STILL = (
    PROJECT_ROOT
    / "renders"
    / "final"
    / "delivery"
    / "stills"
    / "title_card_still.png"
)
OUT_DIR = REPO_ROOT / "site" / "video"
OUT_MP4 = OUT_DIR / "oino-interlude-full.mp4"
ASS_PATH = OUT_DIR / "web_film_shots.ass"


def load_duration() -> float:
    if AUDIO_MARKERS.is_file():
        data = json.loads(AUDIO_MARKERS.read_text(encoding="utf-8"))
        return float(data.get("duration_seconds") or 131.134979)
    return 131.134979


def load_shots() -> list[dict]:
    rows = []
    with SHOT_LIST.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                {
                    "id": row["shot_id"],
                    "start": int(row["frame_start"]),
                    "end": int(row["frame_end"]),
                    "purpose": (row.get("emotional_purpose") or "")[:90],
                    "lang": row.get("camera_language") or "",
                }
            )
    return rows


def ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(shots: list[dict], duration_s: float, title_start_f: int) -> None:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {W}",
        f"PlayResY: {H}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Shot,Georgia,36,&H00DCE4E8,&H000000FF,&H00000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,0,0,8,40,40,80,1",
        "Style: Meta,Georgia,22,&H0098A0A8,&H000000FF,&H00000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,0,0,2,40,40,40,1",
        "Style: Note,Georgia,20,&H00B0AAA0,&H000000FF,&H00000000,&H64000000,"
        "0,0,0,0,100,100,0,0,1,0,0,2,40,40,100,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 0,{ts(0)},{ts(duration_s)},Meta,,0,0,0,,Oino (Interlude) — full review cut",
    ]
    title_t = (title_start_f - 1) / FPS
    for sh in shots:
        t0 = (sh["start"] - 1) / FPS
        t1 = min(duration_s, sh["end"] / FPS)
        if t1 <= t0:
            continue
        # Hide board text once title card holds
        if t0 >= title_t:
            continue
        end = min(t1, title_t)
        label = sh["id"].replace("_", " ")
        lines.append(
            f"Dialogue: 0,{ts(t0)},{ts(end)},Shot,,0,0,0,,{label}"
        )
        if sh["purpose"]:
            purpose = sh["purpose"].replace(",", " ")
            lines.append(
                f"Dialogue: 0,{ts(t0)},{ts(end)},Note,,0,0,0,,{purpose}"
            )
        if sh["lang"]:
            lines.append(
                f"Dialogue: 0,{ts(t0)},{ts(end)},Meta,,0,0,0,,camera · {sh['lang']}"
            )
    ASS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ffmpeg(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stderr or "")[-2000:]


def main() -> int:
    report = RunReport(script="export_web_film", seed=20261210)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MASTER_AUDIO.is_file():
        report.fail("audio", MASTER_AUDIO)
        report.write(REPORTS_DIR)
        return 1
    if not TITLE_STILL.is_file():
        report.fail("still", TITLE_STILL)
        report.write(REPORTS_DIR)
        return 1

    duration_s = load_duration()
    shots = load_shots()
    title_start = 3051
    write_ass(shots, duration_s, title_start)
    report.mark("created", str(ASS_PATH.relative_to(REPO_ROOT)).replace("\\", "/"))

    title_t = (title_start - 1) / FPS
    ass_esc = str(ASS_PATH.resolve()).replace("\\", "/").replace(":", "\\:")
    title_esc = str(TITLE_STILL.resolve()).replace("\\", "/").replace(":", "\\:")

    # Scale title still to canvas then overlay from title card start
    fc = (
        f"[0:v]ass='{ass_esc}'[v1];"
        f"[1:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0A0A0A[ov];"
        f"[v1][ov]overlay=0:0:enable='gte(t\\,{title_t:.3f})'[vout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0A0A0A:s={W}x{H}:d={duration_s:.6f}:r={FPS}",
        "-loop",
        "1",
        "-i",
        str(TITLE_STILL.resolve()),
        "-i",
        str(MASTER_AUDIO.resolve()),
        "-filter_complex",
        fc,
        "-map",
        "[vout]",
        "-map",
        "2:a",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "23",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-t",
        f"{duration_s:.6f}",
        "-movflags",
        "+faststart",
        str(OUT_MP4.resolve()),
    ]
    ok, err = run_ffmpeg(cmd)
    if not ok:
        # Fallback without ASS
        fc2 = (
            f"[1:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0A0A0A[ov];"
            f"[0:v][ov]overlay=0:0:enable='gte(t\\,{title_t:.3f})'[vout]"
        )
        cmd2 = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0A0A0A:s={W}x{H}:d={duration_s:.6f}:r={FPS}",
            "-loop",
            "1",
            "-i",
            str(TITLE_STILL.resolve()),
            "-i",
            str(MASTER_AUDIO.resolve()),
            "-filter_complex",
            fc2,
            "-map",
            "[vout]",
            "-map",
            "2:a",
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
            "-t",
            f"{duration_s:.6f}",
            "-movflags",
            "+faststart",
            str(OUT_MP4.resolve()),
        ]
        ok, err = run_ffmpeg(cmd2)
        if not ok:
            report.fail("ffmpeg", err)
            report.write(REPORTS_DIR)
            return 1
        report.note("ASS unavailable — title card + audio only")

    mb = OUT_MP4.stat().st_size / (1024 * 1024)
    report.mark("created", f"site/video/oino-interlude-full.mp4 ({mb:.1f} MB)")
    report.note(f"Full cut {duration_s:.3f}s · {TITLE_EXACT} / {DATE_EXACT}")
    report.write(REPORTS_DIR)
    print(f"SUMMARY ok=True out=site/video/oino-interlude-full.mp4 mb={mb:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
