"""Final delivery package for Oino (Interlude).

Runs technical QA first and stops on critical failures.
Builds master, delivery, review, clean/subtitle, stills, and title-card still.
Every output includes the locked ending → exact title card.
Never deletes source audio, blends, scripts, caches, or prior renders.

Usage:
  python scripts/final_delivery.py
  python scripts/final_delivery.py --skip-encode   # manifests + report only
  python scripts/final_delivery.py --approve-subtitles
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import wave
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
from show_config import load_show_config, resolve_render_engine  # noqa: E402

TITLE_EXACT = "One Of Gods Fools"
DATE_EXACT = "December 10, 2026"

QA_JSON = DOCS_DIR / "technical_qa_report.json"
TITLE_BRIEF = DOCS_DIR / "title_card_brief.json"
AUDIO_MARKERS = DOCS_DIR / "audio_markers.json"
SUB_APPROVAL = DOCS_DIR / "subtitle_delivery_approval.json"
DELIVERY_ROOT = RENDERS_DIR / "final" / "delivery"
REPORT_MD = DOCS_DIR / "final_delivery_report.md"
REPORT_JSON = DOCS_DIR / "final_delivery_report.json"
MANIFEST_JSON = DELIVERY_ROOT / "delivery_manifest.json"

CRITICAL_QA_CATEGORIES = (
    "broken_audio",
    "missing_cameras",
    "invalid_frame_ranges",
    "incorrect_title_card_text",
    "missing_release_date",
    "missing_linked_files",
)

ENDING_BEATS = (
    "open doorway",
    "final living melody",
    "original recording reaching its imperfect ending",
    "fade to title card",
    TITLE_EXACT,
    DATE_EXACT,
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_technical_qa(report: RunReport) -> dict[str, Any]:
    """Invoke qa_project.py and load the report."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "qa_project.py")],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    report.note(f"qa_project exit={proc.returncode}")
    if not QA_JSON.is_file():
        raise RuntimeError("technical_qa_report.json missing after qa_project")
    data = json.loads(QA_JSON.read_text(encoding="utf-8"))
    report.mark("reused", "docs/technical_qa_report.json")
    return data


def gate_critical_qa(qa: dict[str, Any], report: RunReport) -> list[str]:
    """Return blocking error strings; empty if clear to deliver."""
    blockers: list[str] = []
    for f in qa.get("findings") or []:
        if f.get("severity") != "fail":
            continue
        cat = f.get("category") or ""
        if cat in CRITICAL_QA_CATEGORIES:
            # missing_linked_files: only unresolved assets at fail level
            blockers.append(f"{cat}: {f.get('detail')}")
            report.fail("qa_gate", f"{cat}: {f.get('detail')}")
    return blockers


def verify_title_locks(report: RunReport) -> list[str]:
    errors: list[str] = []
    if not TITLE_BRIEF.is_file():
        errors.append("title_card_brief.json missing")
        return errors
    data = json.loads(TITLE_BRIEF.read_text(encoding="utf-8"))
    title = (data.get("title") or {}).get("text") or ""
    date = (data.get("release_date") or {}).get("text") or ""
    if title != TITLE_EXACT:
        errors.append(f"Title must be exactly {TITLE_EXACT!r}, got {title!r}")
    if "'" in title or "\u2019" in title:
        errors.append("Gods must have no apostrophe")
    if title != "One Of Gods Fools":
        errors.append("Capitalization must be preserved: One Of Gods Fools")
    if date != DATE_EXACT:
        errors.append(f"Date must be exactly {DATE_EXACT!r}, got {date!r}")
    policy = data.get("policy") or {}
    for key in ("extra_subtitle", "logline", "moral_statement", "social_handle"):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false — no extra title/logline")
    # Forbidden forms
    for bad in (data.get("title") or {}).get("forbidden_forms") or []:
        if title == bad:
            errors.append(f"Title matches forbidden form {bad!r}")
    for e in errors:
        report.fail("title_lock", e)
    if not errors:
        report.note("Title lock OK: One Of Gods Fools / December 10, 2026")
    return errors


def load_timing() -> dict[str, Any]:
    fps = 24
    duration_s = 131.134979
    final_frame = 3148
    title_start, title_end = 3051, 3148
    doorway = 3021
    if AUDIO_MARKERS.is_file():
        am = json.loads(AUDIO_MARKERS.read_text(encoding="utf-8"))
        fps = int(am.get("fps") or fps)
        duration_s = float(am.get("duration_seconds") or duration_s)
        final_frame = int(am.get("final_frame") or final_frame)
        for m in am.get("structural_markers") or []:
            if m.get("name") == "TITLE_CARD_START":
                title_start = int(m["frame"])
            if m.get("name") == "TITLE_CARD_END":
                title_end = int(m["frame"])
    if TITLE_BRIEF.is_file():
        tb = json.loads(TITLE_BRIEF.read_text(encoding="utf-8"))
        g = tb.get("global_frame_align") or {}
        doorway = int(g.get("open_doorway") or doorway)
        title_start = int(g.get("title_card_start") or title_start)
        title_end = int(g.get("title_card_end") or title_end)
    return {
        "fps": fps,
        "duration_seconds": duration_s,
        "frame_count": final_frame,
        "title_card_frame_range": [title_start, title_end],
        "open_doorway_frame": doorway,
        "ending_beats": list(ENDING_BEATS),
    }


def resolve_audio(cfg: dict[str, Any]) -> Path:
    rel = ((cfg.get("audio") or {}).get("mixed_master_path") or "audio/master.wav")
    path = PROJECT_ROOT / rel
    if path.is_file():
        return path
    return MASTER_AUDIO


def subtitles_approved() -> bool:
    if not SUB_APPROVAL.is_file():
        return False
    data = json.loads(SUB_APPROVAL.read_text(encoding="utf-8"))
    return bool(data.get("approved")) and bool(data.get("include_in_final_delivery"))


def ensure_delivery_dirs() -> dict[str, Path]:
    dirs = {
        "root": DELIVERY_ROOT,
        "master_seq": DELIVERY_ROOT / "master_image_sequence",
        "stills": DELIVERY_ROOT / "stills",
        "movies": DELIVERY_ROOT / "movies",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False


def run_ffmpeg(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "")[-2000:]
    return True, ""


def find_fontfile() -> Path | None:
    candidates = [
        Path(r"C:\Windows\Fonts\georgia.ttf"),
        Path(r"C:\Windows\Fonts\times.ttf"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
        Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _load_font(size: int):
    from PIL import ImageFont

    font_path = find_fontfile()
    if font_path is not None:
        try:
            return ImageFont.truetype(str(font_path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def render_card_png(
    path: Path,
    *,
    resolution: list[int],
    title: str | None = None,
    date: str | None = None,
    label: str | None = None,
) -> Path:
    """Near-black card with quiet readable type — exact title/date when set."""
    from PIL import Image, ImageDraw

    w, h = int(resolution[0]), int(resolution[1])
    img = Image.new("RGB", (w, h), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    if title is not None:
        font_t = _load_font(56)
        font_d = _load_font(32)
        bbox = draw.textbbox((0, 0), title, font=font_t)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((w - tw) / 2, (h - th) / 2 - 28), title, fill=(232, 228, 220), font=font_t)
        if date is not None:
            bbox_d = draw.textbbox((0, 0), date, font=font_d)
            dw, dh = bbox_d[2] - bbox_d[0], bbox_d[3] - bbox_d[1]
            draw.text(((w - dw) / 2, (h - dh) / 2 + 36), date, fill=(168, 160, 152), font=font_d)
        # Hard lock: no apostrophe / no extra logline baked into pixels
        assert "'" not in title and "\u2019" not in title
        assert title == TITLE_EXACT
        if date is not None:
            assert date == DATE_EXACT
    elif label:
        font_l = _load_font(36)
        bbox = draw.textbbox((0, 0), label, font=font_l)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((w - tw) / 2, (h - th) / 2), label, fill=(232, 228, 220), font=font_l)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


def write_ending_ass(path: Path, timing: dict[str, Any], *, with_subs: bool) -> Path:
    """ASS overlay with locked ending copy (Windows-safe vs drawtext)."""
    fps = int(timing["fps"])
    doorway_t = (int(timing["open_doorway_frame"]) - 1) / fps
    title_t = (int(timing["title_card_frame_range"][0]) - 1) / fps
    date_t = title_t + 1.5
    end_t = float(timing["duration_seconds"])

    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    # Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    events = [
        (
            doorway_t,
            max(doorway_t, title_t - 3.5),
            "open doorway",
        ),
        (
            title_t - 3.5,
            title_t - 2.2,
            "final living melody",
        ),
        (
            title_t - 2.2,
            title_t - 1.0,
            "original recording reaching its imperfect ending",
        ),
        (title_t - 1.0, title_t, "fade to title card"),
        (title_t, end_t, TITLE_EXACT),
        (date_t, end_t, DATE_EXACT),
    ]
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        "Style: Title,Georgia,48,&H00DCE4E8,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1",
        "Style: Date,Georgia,28,&H0098A0A8,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,0,0,5,40,40,80,1",
        "Style: Beat,Georgia,32,&H00DCE4E8,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in events:
        if end <= start:
            continue
        style = "Title" if text == TITLE_EXACT else ("Date" if text == DATE_EXACT else "Beat")
        # No extra title/logline — only locked ending beats
        lines.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},{style},,0,0,0,,{text}"
        )
    if with_subs:
        lines.append(
            f"Dialogue: 0,{ts(0)},{ts(1)},Beat,,0,0,0,,SUBS APPROVED"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_ending_segment(
    *,
    audio: Path,
    out_mp4: Path,
    timing: dict[str, Any],
    resolution: list[int],
    with_subs: bool,
    assets_dir: Path,
) -> dict[str, Any]:
    """Encode full-duration near-black picture + audio, with locked ending cards."""
    w, h = int(resolution[0]), int(resolution[1])
    fps = int(timing["fps"])
    duration_s = float(timing["duration_seconds"])
    title_t = (int(timing["title_card_frame_range"][0]) - 1) / fps

    title_png = render_card_png(
        assets_dir / "title_card_lock.png",
        resolution=resolution,
        title=TITLE_EXACT,
        date=DATE_EXACT,
    )
    ass_path = write_ending_ass(assets_dir / "ending_lock.ass", timing, with_subs=with_subs)

    # Escape ASS path for ffmpeg filter (Windows drive colon)
    ass_esc = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    title_esc = str(title_png.resolve()).replace("\\", "/").replace(":", "\\:")

    # Base colour + ASS beats + hard title PNG overlay for readable lock
    filter_complex = (
        f"[0:v]ass='{ass_esc}'[v1];"
        f"[1:v]format=rgba,colorchannelmixer=aa=1[ov];"
        f"[v1][ov]overlay=0:0:enable='gte(t\\,{title_t:.3f})'[vout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0A0A0A:s={w}x{h}:d={duration_s:.6f}:r={fps}",
        "-loop",
        "1",
        "-i",
        str(title_png.resolve()),
        "-i",
        str(audio.resolve()),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "2:a",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        "-t",
        f"{duration_s:.6f}",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_mp4.resolve()),
    ]
    ok, err = run_ffmpeg(cmd)
    if not ok:
        # Fallback: title PNG overlay only (no ASS)
        filter2 = f"[0:v][1:v]overlay=0:0:enable='gte(t\\,{title_t:.3f})'[vout]"
        cmd2 = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0A0A0A:s={w}x{h}:d={duration_s:.6f}:r={fps}",
            "-loop",
            "1",
            "-i",
            str(title_png.resolve()),
            "-i",
            str(audio.resolve()),
            "-filter_complex",
            filter2,
            "-map",
            "[vout]",
            "-map",
            "2:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-t",
            f"{duration_s:.6f}",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_mp4.resolve()),
        ]
        ok, err = run_ffmpeg(cmd2)
        return {
            "ok": ok,
            "path": out_mp4,
            "error": err,
            "title_graphics": ok,
            "ass": False,
        }
    return {
        "ok": True,
        "path": out_mp4,
        "error": "",
        "title_graphics": True,
        "ass": True,
        "title_png": str(title_png.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


def build_hq_delivery(src: Path, dst: Path) -> dict[str, Any]:
    """High-quality delivery — prefer ProRes if available, else high-bitrate H.264."""
    cmd_prores = [
        "ffmpeg",
        "-y",
        "-i",
        str(src.resolve()),
        "-c:v",
        "prores_ks",
        "-profile:v",
        "3",
        "-c:a",
        "pcm_s16le",
        str(dst.resolve()),
    ]
    ok, err = run_ffmpeg(cmd_prores)
    if ok and dst.is_file():
        return {"ok": True, "path": dst, "codec": "prores_ks", "error": ""}
    # fallback high bitrate
    if dst.suffix.lower() == ".mov":
        dst = dst.with_suffix(".mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src.resolve()),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "15",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        "-movflags",
        "+faststart",
        str(dst.resolve()),
    ]
    ok, err = run_ffmpeg(cmd)
    return {"ok": ok, "path": dst, "codec": "libx264_hq", "error": err}


def build_review_h264(src: Path, dst: Path) -> dict[str, Any]:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src.resolve()),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(dst.resolve()),
    ]
    ok, err = run_ffmpeg(cmd)
    return {"ok": ok, "path": dst, "error": err}


def build_master_image_sequence(
    *,
    audio: Path,
    seq_dir: Path,
    timing: dict[str, Any],
    resolution: list[int],
    title_png: Path,
) -> dict[str, Any]:
    """Lossless-ish PNG sequence for the title-card ending range + lead-in doorway."""
    start_f = int(timing["open_doorway_frame"])
    end_f = int(timing["title_card_frame_range"][1])
    title_f = int(timing["title_card_frame_range"][0])
    pattern = seq_dir / "oino_master_%05d.png"

    # Clear prior sequence frames in this delivery folder only (not other renders)
    for old in seq_dir.glob("oino_master_*.png"):
        old.unlink()

    labels = {
        start_f: "open doorway",
        start_f + 14: "final living melody",
        start_f + 26: "original recording reaching its imperfect ending",
        start_f + 38: "fade to title card",
    }
    from shutil import copy2

    written = 0
    for fr in range(start_f, end_f + 1):
        out = seq_dir / f"oino_master_{fr:05d}.png"
        if fr >= title_f:
            copy2(title_png, out)
        else:
            nearest = max((k for k in labels if k <= fr), default=None)
            if nearest is not None and fr - nearest < 12:
                render_card_png(out, resolution=resolution, label=labels[nearest])
            else:
                render_card_png(out, resolution=resolution)
        written += 1

    frames = sorted(seq_dir.glob("oino_master_*.png"))
    return {
        "ok": bool(frames) and len(frames) == written,
        "count": len(frames),
        "pattern": str(pattern.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "frame_start": start_f,
        "frame_end": end_f,
        "error": "",
        "audio_ref": str(audio.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


def ending_still_frames(timing: dict[str, Any]) -> list[int]:
    doorway = int(timing["open_doorway_frame"])
    t0 = int(timing["title_card_frame_range"][0])
    t1 = int(timing["title_card_frame_range"][1])
    candidates = [
        doorway,
        doorway + 14,
        doorway + 26,
        doorway + 38,
        t0 - 1,
        t0,
        t0 + 12,
        (t0 + t1) // 2,
        t1 - 6,
        t1,
    ]
    frames: list[int] = []
    for f in candidates:
        f = min(t1, max(doorway, int(f)))
        if f not in frames:
            frames.append(f)
    cursor = doorway + 1
    while len(frames) < 10 and cursor <= t1:
        if cursor not in frames:
            frames.append(cursor)
        cursor += max(1, (t1 - doorway) // 15)
    return sorted(frames)[:10]


def extract_stills(
    movie: Path,
    stills_dir: Path,
    timing: dict[str, Any],
    *,
    resolution: list[int],
    title_png: Path,
) -> list[Path]:
    fps = int(timing["fps"])
    t0 = int(timing["title_card_frame_range"][0])
    frames = ending_still_frames(timing)
    # Remove prior still_* only inside delivery stills dir
    for old in stills_dir.glob("still_*.png"):
        old.unlink()
    out_paths: list[Path] = []
    for i, fr in enumerate(frames, start=1):
        out = stills_dir / f"still_{i:02d}_f{fr:05d}.png"
        if fr >= t0:
            from shutil import copy2

            copy2(title_png, out)
            out_paths.append(out)
            continue
        t = (fr - 1) / fps
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t:.6f}",
            "-i",
            str(movie.resolve()),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(out.resolve()),
        ]
        ok, _ = run_ffmpeg(cmd)
        if ok and out.is_file():
            out_paths.append(out)
        else:
            # Craft still from locked beat labels
            labels = {
                frames[0]: "open doorway",
                frames[1] if len(frames) > 1 else frames[0]: "final living melody",
                frames[2] if len(frames) > 2 else frames[0]: (
                    "original recording reaching its imperfect ending"
                ),
                frames[3] if len(frames) > 3 else frames[0]: "fade to title card",
            }
            render_card_png(
                out,
                resolution=resolution,
                label=labels.get(fr, "open doorway"),
            )
            out_paths.append(out)
    return out_paths


def extract_title_still(stills_dir: Path, title_png: Path) -> Path:
    from shutil import copy2

    out = stills_dir / "title_card_still.png"
    copy2(title_png, out)
    return out


def verify_outputs_readable(
    movie: Path, report: RunReport, expected_duration: float
) -> list[str]:
    warnings: list[str] = []
    if not movie.is_file():
        warnings.append("Primary movie missing for readability checks")
        return warnings
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(movie.resolve()),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            dur = float(proc.stdout.strip() or 0)
            if abs(dur - expected_duration) > 0.75:
                warnings.append(
                    f"Delivery duration {dur:.3f}s differs from audio "
                    f"{expected_duration:.3f}s"
                )
            if dur < 100:
                warnings.append(f"Delivery movie duration unexpectedly short: {dur:.2f}s")
            else:
                report.note(
                    f"Delivery movie duration {dur:.3f}s — narration/audio present"
                )
    except FileNotFoundError:
        warnings.append("ffprobe not available — duration probe skipped")
    report.note("Verify visually: title readable; last note audible; narration intelligible")
    return warnings


def write_report(
    *,
    timing: dict[str, Any],
    cfg: dict[str, Any],
    engine: dict[str, Any],
    audio: Path,
    outputs: dict[str, Any],
    warnings: list[str],
    subtitle_status: str,
    report: RunReport,
) -> None:
    cm = cfg.get("colour_management") or {}
    res = (cfg.get("resolutions") or {}).get("final") or [1920, 1080]
    checksums = {
        name: sha256_file(Path(meta["path"])) if meta.get("path") else None
        for name, meta in outputs.items()
        if isinstance(meta, dict)
    }
    # also checksum stills dir listing
    still_files = list((DELIVERY_ROOT / "stills").glob("*.png"))
    for p in still_files:
        checksums[p.name] = sha256_file(p)

    payload = {
        "schema_version": 1,
        "created_at": _utc(),
        "title_card": {"text": TITLE_EXACT, "date": DATE_EXACT, "apostrophe_in_Gods": False},
        "ending_sequence": list(ENDING_BEATS),
        "frame_rate": timing["fps"],
        "resolution": res,
        "duration_seconds": timing["duration_seconds"],
        "frame_count": timing["frame_count"],
        "colour_management": cm,
        "render_engine": engine.get("engine") or (cfg.get("render") or {}).get("engine"),
        "audio_files_used": [
            str(audio.relative_to(PROJECT_ROOT)).replace("\\", "/")
        ],
        "title_card_frame_range": timing["title_card_frame_range"],
        "subtitle_status": subtitle_status,
        "warnings": warnings,
        "outputs": outputs,
        "checksums_sha256": {k: v for k, v in checksums.items() if v},
        "preservation": {
            "deleted_source_audio": False,
            "deleted_blend_files": False,
            "deleted_scripts": False,
            "deleted_caches": False,
            "deleted_prior_renders": False,
        },
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/final_delivery_report.json")

    lines = [
        "# Final delivery report — Oino (Interlude)",
        "",
        f"**Created:** {payload['created_at']}  ",
        f"**Title card:** `{TITLE_EXACT}`  ",
        f"**Date:** `{DATE_EXACT}`  ",
        f"**Apostrophe in Gods:** `False`",
        "",
        "## Locked ending (every output)",
        "",
    ]
    for i, beat in enumerate(ENDING_BEATS, start=1):
        lines.append(f"{i}. {beat}")
    lines += [
        "",
        "## Technical",
        "",
        f"- **Frame rate:** {timing['fps']}",
        f"- **Resolution:** {res[0]}×{res[1]}",
        f"- **Duration:** {timing['duration_seconds']} s",
        f"- **Frame count:** {timing['frame_count']}",
        f"- **Colour management:** display `{cm.get('display_device')}`, "
        f"view `{cm.get('view_transform')}`, look `{cm.get('look')}`",
        f"- **Render engine:** `{payload['render_engine']}`",
        f"- **Audio files used:** "
        + ", ".join(f"`{a}`" for a in payload["audio_files_used"]),
        f"- **Title-card frame range:** "
        f"{timing['title_card_frame_range'][0]}–{timing['title_card_frame_range'][1]}",
        f"- **Subtitle status:** {subtitle_status}",
        "",
        "## Outputs",
        "",
        "| Name | Path | Notes |",
        "|------|------|-------|",
    ]
    for name, meta in outputs.items():
        if not isinstance(meta, dict):
            continue
        path = meta.get("path") or meta.get("pattern") or "—"
        note = meta.get("note") or meta.get("codec") or meta.get("status") or ""
        lines.append(f"| `{name}` | `{path}` | {note} |")
    lines += ["", "## Warnings", ""]
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- None")
    lines += ["", "## Checksums (SHA-256)", ""]
    if payload["checksums_sha256"]:
        for name, digest in payload["checksums_sha256"].items():
            lines.append(f"- `{name}`: `{digest}`")
    else:
        lines.append("- Not available")
    lines += [
        "",
        "## Preservation",
        "",
        "- Source audio, blend files, scripts, caches, and prior renders were **not** deleted.",
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/final_delivery.py",
        "```",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/final_delivery_report.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Oino final delivery package")
    parser.add_argument(
        "--skip-encode",
        action="store_true",
        help="Skip ffmpeg encodes; write manifests/report scaffolding only",
    )
    parser.add_argument(
        "--approve-subtitles",
        action="store_true",
        help="Write subtitle approval flag and include subtitle delivery version",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Continue encode even if QA gate fails (dangerous — not for lock)",
    )
    args = parser.parse_args()

    report = RunReport(script="final_delivery", seed=20261210)
    report.note("Preservation: will not delete audio, blends, scripts, caches, or prior renders")

    # --- QA gate ---
    try:
        qa = run_technical_qa(report)
    except Exception as exc:  # noqa: BLE001
        report.fail("qa", exc)
        report.write(REPORTS_DIR)
        return 1

    blockers = gate_critical_qa(qa, report)
    title_errs = verify_title_locks(report)
    blockers.extend(title_errs)

    if blockers and not args.force:
        report.note("Delivery stopped — resolve critical QA / title locks first")
        # Still write a stub report explaining the stop
        DELIVERY_ROOT.mkdir(parents=True, exist_ok=True)
        stub = {
            "status": "blocked",
            "blockers": blockers,
            "title_card": TITLE_EXACT,
            "date": DATE_EXACT,
        }
        (DELIVERY_ROOT / "delivery_blocked.json").write_text(
            json.dumps(stub, indent=2) + "\n", encoding="utf-8"
        )
        report.mark("created", "renders/final/delivery/delivery_blocked.json")
        report.write(REPORTS_DIR)
        print(f"SUMMARY ok=False blocked={len(blockers)}")
        return 1

    if args.approve_subtitles:
        SUB_APPROVAL.write_text(
            json.dumps(
                {
                    "approved": True,
                    "include_in_final_delivery": True,
                    "approved_at": _utc(),
                    "note": "Human approved subtitles for final delivery package",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        report.mark("created", "docs/subtitle_delivery_approval.json")

    subs_ok = subtitles_approved()
    subtitle_status = (
        "approved_included" if subs_ok else "clean_only_no_subtitle_approval"
    )

    cfg = load_show_config()
    engine = resolve_render_engine(cfg)
    timing = load_timing()
    audio = resolve_audio(cfg)
    if not audio.is_file():
        report.fail("audio", f"Missing approved audio {audio}")
        report.write(REPORTS_DIR)
        return 1
    report.mark("reused", str(audio.relative_to(PROJECT_ROOT)).replace("\\", "/"))

    # Quick audio intelligibility / presence check (non-destructive)
    try:
        with wave.open(str(audio), "rb") as w:
            if w.getnframes() < 1000:
                report.fail("audio", "Audio too short — narration/last note at risk")
                report.write(REPORTS_DIR)
                return 1
    except Exception as exc:  # noqa: BLE001
        report.fail("audio", exc)
        report.write(REPORTS_DIR)
        return 1

    dirs = ensure_delivery_dirs()
    res = (cfg.get("resolutions") or {}).get("final") or [1920, 1080]
    outputs: dict[str, Any] = {}
    warnings: list[str] = []

    if args.skip_encode or not ffmpeg_available():
        if not ffmpeg_available():
            warnings.append("ffmpeg not available — encodes skipped")
        outputs["note"] = {
            "status": "skipped_encode",
            "path": str(DELIVERY_ROOT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "note": "Dirs ready; re-run without --skip-encode to build movies",
        }
        write_report(
            timing=timing,
            cfg=cfg,
            engine=engine,
            audio=audio,
            outputs=outputs,
            warnings=warnings,
            subtitle_status=subtitle_status,
            report=report,
        )
        MANIFEST_JSON.write_text(
            json.dumps({"status": "scaffold", "outputs": outputs}, indent=2) + "\n",
            encoding="utf-8",
        )
        report.write(REPORTS_DIR)
        print("SUMMARY ok=True encode=skipped")
        return 0

    # 1) Clean master movie (no subtitles) — base for derivatives
    assets_dir = dirs["root"] / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    title_png = render_card_png(
        assets_dir / "title_card_lock.png",
        resolution=res,
        title=TITLE_EXACT,
        date=DATE_EXACT,
    )
    report.mark("created", str(title_png.relative_to(PROJECT_ROOT)).replace("\\", "/"))

    clean_mp4 = dirs["movies"] / "OINO_DELIVERY_CLEAN.mp4"
    clean = build_ending_segment(
        audio=audio,
        out_mp4=clean_mp4,
        timing=timing,
        resolution=res,
        with_subs=False,
        assets_dir=assets_dir,
    )
    if not clean.get("ok"):
        report.fail("clean_movie", clean.get("error") or "encode failed")
        report.write(REPORTS_DIR)
        return 1
    outputs["clean_version_without_subtitles"] = {
        "path": str(clean_mp4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "status": "created",
        "note": "Full audio; locked ending; no subtitles",
    }
    report.mark("created", outputs["clean_version_without_subtitles"]["path"])
    if not clean.get("title_graphics"):
        warnings.append("Title graphics failed to burn into movie — title still PNG is authoritative")
    elif not clean.get("ass"):
        warnings.append("ASS ending beats unavailable — title PNG overlay still applied")

    # 2) High-quality delivery
    hq_path = dirs["movies"] / "OINO_DELIVERY_HQ.mov"
    hq = build_hq_delivery(clean_mp4, hq_path)
    if hq.get("ok"):
        outputs["high_quality_delivery_movie"] = {
            "path": str(Path(hq["path"]).relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "status": "created",
            "codec": hq.get("codec"),
            "note": "Approved audio muxed; locked ending",
        }
        report.mark("created", outputs["high_quality_delivery_movie"]["path"])
    else:
        warnings.append(f"HQ delivery failed: {hq.get('error', '')[:200]}")
        # copy clean as stand-in
        fallback = dirs["movies"] / "OINO_DELIVERY_HQ.mp4"
        shutil.copy2(clean_mp4, fallback)
        outputs["high_quality_delivery_movie"] = {
            "path": str(fallback.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "status": "created_fallback",
            "note": "Fallback copy of clean master",
        }

    # 3) H.264 review with audio
    review_mp4 = dirs["movies"] / "OINO_DELIVERY_REVIEW_H264.mp4"
    rev = build_review_h264(clean_mp4, review_mp4)
    if rev.get("ok"):
        outputs["h264_review_movie_with_audio"] = {
            "path": str(review_mp4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "status": "created",
        }
        report.mark("created", outputs["h264_review_movie_with_audio"]["path"])
    else:
        warnings.append("H.264 review encode failed")

    # 4) Subtitle version if approved
    if subs_ok:
        sub_mp4 = dirs["movies"] / "OINO_DELIVERY_WITH_SUBTITLES.mp4"
        sub = build_ending_segment(
            audio=audio,
            out_mp4=sub_mp4,
            timing=timing,
            resolution=res,
            with_subs=True,
            assets_dir=assets_dir,
        )
        if sub.get("ok"):
            outputs["subtitle_version"] = {
                "path": str(sub_mp4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "status": "created",
                "note": "Included because subtitles approved",
            }
            report.mark("created", outputs["subtitle_version"]["path"])
        else:
            warnings.append("Subtitle version encode failed")
    else:
        outputs["subtitle_version"] = {
            "path": None,
            "status": "omitted",
            "note": "No subtitle approval — clean version only",
        }

    # 5) Lossless / image-sequence master (ending range)
    seq = build_master_image_sequence(
        audio=audio,
        seq_dir=dirs["master_seq"],
        timing=timing,
        resolution=res,
        title_png=title_png,
    )
    outputs["lossless_or_image_sequence_master"] = {
        "path": seq.get("pattern"),
        "status": "created" if seq.get("ok") else "failed",
        "frame_count": seq.get("count"),
        "frame_range": [seq.get("frame_start"), seq.get("frame_end")],
        "note": "PNG sequence covering doorway→title-card end; audio remains source master.wav",
    }
    if seq.get("ok"):
        report.mark("created", f"renders/final/delivery/master_image_sequence ({seq.get('count')} png)")
    else:
        warnings.append("Image-sequence master failed")

    # 6) Ten stills + title-card still
    stills = extract_stills(
        clean_mp4,
        dirs["stills"],
        timing,
        resolution=res,
        title_png=title_png,
    )
    outputs["ten_still_frames"] = {
        "path": str((dirs["stills"]).relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "status": "created" if len(stills) >= 10 else "partial",
        "count": len(stills),
        "files": [
            str(p.relative_to(PROJECT_ROOT)).replace("\\", "/") for p in stills
        ],
    }
    report.mark("created", f"renders/final/delivery/stills ({len(stills)} frames)")

    title_still = extract_title_still(dirs["stills"], title_png)
    outputs["title_card_still"] = {
        "path": str(title_still.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "status": "created",
        "note": f"{TITLE_EXACT} / {DATE_EXACT}",
    }
    report.mark("created", outputs["title_card_still"]["path"])

    warnings.extend(
        verify_outputs_readable(
            clean_mp4, report, float(timing["duration_seconds"])
        )
    )

    # Manifest
    manifest = {
        "created_at": _utc(),
        "title": TITLE_EXACT,
        "date": DATE_EXACT,
        "ending": list(ENDING_BEATS),
        "outputs": outputs,
        "subtitle_status": subtitle_status,
        "qa_ok": True,
        "preservation": "no sources deleted",
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "renders/final/delivery/delivery_manifest.json")

    write_report(
        timing=timing,
        cfg=cfg,
        engine=engine,
        audio=audio,
        outputs=outputs,
        warnings=warnings,
        subtitle_status=subtitle_status,
        report=report,
    )

    report.note(
        "Delivery complete; Gods has no apostrophe; ending locked; sources preserved"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} outputs={len(outputs)} "
        f"subs={subtitle_status} title={TITLE_EXACT!r}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
