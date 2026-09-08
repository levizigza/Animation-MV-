"""Coordinate broad emotional music/narration sync for Oino (Interlude).

Uses actual docs/audio_markers.json. Amplitude drives secondary motion only —
not faces, Oino's decisions, or every camera cut.

Usage:
  python scripts/music_sync.py
  python scripts/music_sync.py --preview
  python scripts/music_sync.py --approve MUS_TABLE_WARMTH NAR_ARCHIVE_DISCOVERY
"""

from __future__ import annotations

import argparse
import json
import math
import struct
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
    RENDERS_PREVIEW,
    REPORTS_DIR,
    require_file,
)
from show_config import load_show_config  # noqa: E402

SYNC_JSON = DOCS_DIR / "music_sync.json"
APPROVALS_JSON = DOCS_DIR / "music_sync_approvals.json"
MARKERS_JSON = DOCS_DIR / "audio_markers.json"
LEITMOTIF_JSON = DOCS_DIR / "dionysus_leitmotif.json"
REPORT_MD = DOCS_DIR / "music_sync_report.md"
REPORT_JSON = DOCS_DIR / "music_sync_report.json"
REACTIVE_JSON = DOCS_DIR / "music_sync_reactive_envelopes.json"
SRT_PATH = PROJECT_ROOT / "cache" / "music_sync_cues.srt"
PREVIEW_MP4 = RENDERS_PREVIEW / "music_sync_preview.mp4"

REQUIRED_NARRATION = (
    "archive discovery",
    "watcher and singularity",
    "ascent and anticipation",
    "Babel and Icarus",
    "chaos and self-projection",
    "labyrinth and ancestor failure",
    "descent and captivity",
    "cautionary tale and threshold",
)

REQUIRED_MUSIC = (
    "room tone and distant call",
    "father's unfinished phrase",
    "first Dionysus leitmotif",
    "steam and labour pulse",
    "electric release and dance",
    "digital quantization",
    "future voice and memorial presence",
    "Zone suspension",
    "table warmth",
    "rewind loop",
    "irregular knock",
    "release",
    "sister's changed melody",
    "title-card resolve",
)

REQUIRED_REACTIVE = (
    "steam vibration",
    "cable sway",
    "screen brightness",
    "water ripples",
    "dust density",
    "faint table resonance",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_sync() -> dict[str, Any]:
    if not SYNC_JSON.is_file():
        raise FileNotFoundError(f"Missing {SYNC_JSON}")
    return json.loads(SYNC_JSON.read_text(encoding="utf-8"))


def load_audio_markers() -> dict[str, Any]:
    if not MARKERS_JSON.is_file():
        raise FileNotFoundError(
            f"Missing {MARKERS_JSON}. Run scripts/setup_audio.py first."
        )
    return json.loads(MARKERS_JSON.read_text(encoding="utf-8"))


def load_approvals() -> dict[str, Any]:
    if APPROVALS_JSON.is_file():
        return json.loads(APPROVALS_JSON.read_text(encoding="utf-8"))
    return {"schema_version": 1, "approvals": {}}


def save_approvals(data: dict[str, Any]) -> None:
    APPROVALS_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def marker_index(markers: dict[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for m in markers.get("structural_markers") or []:
        idx[m["name"]] = {**m, "kind": "structural"}
    for m in markers.get("broad_cues") or []:
        idx[m["name"]] = {**m, "kind": "broad_cue"}
    return idx


def validate(sync: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = sync.get("policy") or {}
    for key in (
        "cut_to_every_beat",
        "drive_facial_performance_from_amplitude",
        "drive_oino_decisions_from_amplitude",
        "drive_every_camera_cut_from_amplitude",
    ):
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    if policy.get("audio_reactive_secondary_only") is not True:
        errors.append("policy.audio_reactive_secondary_only must be true")
    if policy.get("characters_must_listen") is not True:
        errors.append("policy.characters_must_listen must be true")

    nar = [(m.get("label") or "").strip() for m in (sync.get("narration_movements") or [])]
    mus = [(m.get("label") or "").strip() for m in (sync.get("music_movements") or [])]
    rx = [(m.get("label") or "").strip() for m in (sync.get("reactive_controls") or [])]
    for req in REQUIRED_NARRATION:
        if req not in nar:
            errors.append(f"Missing narration movement: {req}")
    for req in REQUIRED_MUSIC:
        if req not in mus:
            errors.append(f"Missing music movement: {req}")
    for req in REQUIRED_REACTIVE:
        if req not in rx:
            errors.append(f"Missing reactive control: {req}")

    forbidden = set(sync.get("forbidden_reactive_targets") or [])
    for need in ("facial_performance", "oino_decision_beats", "primary_camera_cuts"):
        if need not in forbidden:
            errors.append(f"forbidden_reactive_targets must include {need}")

    for m in sync.get("reactive_controls") or []:
        drives = m.get("drives") or []
        if drives != ["secondary_motion"]:
            errors.append(f"{m.get('id')}: drives must be secondary_motion only")

    return errors


def resolve_frame(
    movement: dict[str, Any],
    idx: dict[str, dict[str, Any]],
    *,
    fps: float,
    final_frame: int,
) -> tuple[int, str, str]:
    """Return (frame, source_marker_or_hint, resolve_method).

    Prefer explicit frame_hint for story placement (narration beats), else
    anchor audio markers + optional frame_offset for music movements.
    """
    offset = int(movement.get("frame_offset") or 0)
    hint = movement.get("frame_hint")
    cue = movement.get("anchor_cue")

    if hint is not None:
        frame = max(1, min(final_frame, int(hint) + offset))
        src = f"frame_hint:{hint}"
        if cue:
            src = f"{src}|anchor:{cue}"
        return frame, src, "frame_hint"

    if cue and cue in idx:
        frame = int(idx[cue]["frame"]) + offset
        frame = max(1, min(final_frame, frame))
        return frame, cue, "audio_marker"
    fb = movement.get("fallback_cue")
    if fb and fb in idx:
        frame = int(idx[fb]["frame"]) + offset
        frame = max(1, min(final_frame, frame))
        return frame, fb, "audio_marker_fallback"
    return 1, "none", "unresolved"


def approval_status(
    movement_id: str,
    resolve_method: str,
    approvals: dict[str, Any],
    marker_meta: dict[str, Any] | None,
) -> str:
    appr = (approvals.get("approvals") or {}).get(movement_id) or {}
    if appr.get("status") == "manually_approved":
        return "manually_approved"
    if appr.get("status") == "rejected":
        return "rejected"
    # Direct audio marker with no offset proposal → automatic from analysis
    if resolve_method == "audio_marker" and not appr.get("requires_review"):
        if marker_meta and marker_meta.get("editable") is False:
            return "automatic"
        # editable cues still automatic until human stamps approval file
        return "automatic"
    if resolve_method in ("frame_hint", "audio_marker_fallback") or (
        resolve_method == "audio_marker" and appr.get("requires_review")
    ):
        return "pending_manual"
    return "pending_manual"


def build_cue_rows(
    sync: dict[str, Any],
    markers: dict[str, Any],
    approvals: dict[str, Any],
) -> list[dict[str, Any]]:
    idx = marker_index(markers)
    fps = float(markers.get("fps") or 24)
    final_frame = int(markers.get("final_frame") or 3148)
    rows: list[dict[str, Any]] = []

    def add_movement(kind: str, movement: dict[str, Any]) -> None:
        frame, source, method = resolve_frame(
            movement, idx, fps=fps, final_frame=final_frame
        )
        mid = movement["id"]
        cue_name = movement.get("anchor_cue")
        meta = idx.get(cue_name) if cue_name else None
        status = approval_status(mid, method, approvals, meta)
        if movement.get("leitmotif_status") == "MUSIC_REVIEW_REQUIRED":
            status = "pending_manual"
            source = f"{source}+DIONYSUS_LEITMOTIF"
        t = (frame - 1) / fps
        rows.append(
            {
                "cue": movement["label"],
                "id": mid,
                "kind": kind,
                "frame": frame,
                "time_seconds": round(t, 6),
                "source": source,
                "resolve_method": method,
                "approval": status,
                "link_shots": movement.get("link_shots") or [],
                "note": movement.get("note"),
            }
        )

    for m in sync.get("narration_movements") or []:
        add_movement("narration", m)
    for m in sync.get("music_movements") or []:
        add_movement("music", m)

    # Also list structural + broad cues as coordination anchors
    for name, meta in sorted(idx.items(), key=lambda kv: int(kv[1].get("frame") or 0)):
        rows.append(
            {
                "cue": name,
                "id": name,
                "kind": meta.get("kind") or "marker",
                "frame": int(meta["frame"]),
                "time_seconds": float(meta.get("time_seconds") or 0),
                "source": "docs/audio_markers.json",
                "resolve_method": "audio_marker",
                "approval": "automatic"
                if meta.get("editable") is False
                else "automatic",
                "link_shots": [],
                "note": meta.get("note"),
            }
        )

    rows.sort(key=lambda r: (int(r["frame"]), r["kind"], r["id"]))
    return rows


def read_wav_mono_rms(path: Path, window_sec: float = 0.05) -> list[tuple[float, float]]:
    """Return list of (time_sec, rms) envelopes."""
    require_file(path, "audio")
    with wave.open(str(path), "rb") as w:
        nch = w.getnchannels()
        sw = w.getsampwidth()
        rate = w.getframerate()
        nframes = w.getnframes()
        raw = w.readframes(nframes)
    if sw == 3:
        # 24-bit packed — convert roughly
        samples = []
        for i in range(0, len(raw), 3 * nch):
            # take first channel
            b = raw[i : i + 3]
            if len(b) < 3:
                break
            val = int.from_bytes(b, "little", signed=True)
            samples.append(val / 8388608.0)
    elif sw == 2:
        fmt = "<" + "h" * (len(raw) // 2)
        packed = struct.unpack(fmt, raw)
        samples = [packed[i] / 32768.0 for i in range(0, len(packed), nch)]
    else:
        # fallback silence
        return [(0.0, 0.0)]

    win = max(1, int(rate * window_sec))
    out: list[tuple[float, float]] = []
    for start in range(0, len(samples), win):
        chunk = samples[start : start + win]
        if not chunk:
            break
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
        t = start / float(rate)
        out.append((t, rms))
    return out


def build_reactive_envelopes(
    sync: dict[str, Any], rms: list[tuple[float, float]], fps: float
) -> dict[str, Any]:
    if not rms:
        rms = [(0.0, 0.0)]
    peak = max((v for _, v in rms), default=1.0) or 1.0
    envelopes = {}
    for ctrl in sync.get("reactive_controls") or []:
        cid = ctrl["id"]
        max_inf = float(ctrl.get("max_influence") or 0.2)
        # Simple band weighting (placeholder — secondary only)
        band = ctrl.get("band") or "mid"
        series = []
        for t, v in rms[:: max(1, len(rms) // 500) or 1]:  # downsample ~500 pts
            norm = min(1.0, v / peak)
            if band == "high":
                w = norm**0.7
            elif band == "low":
                w = norm**1.4
            else:
                w = norm
            series.append(
                {
                    "t": round(t, 4),
                    "frame": int(t * fps) + 1,
                    "value": round(w * max_inf, 5),
                }
            )
        envelopes[cid] = {
            "label": ctrl.get("label"),
            "band": band,
            "max_influence": max_inf,
            "target": ctrl.get("target"),
            "drives": ctrl.get("drives"),
            "samples": series,
        }
    return {
        "schema_version": 1,
        "policy": "secondary_motion_only",
        "forbidden": sync.get("forbidden_reactive_targets"),
        "envelopes": envelopes,
        "updated_at": _utc(),
    }


def write_srt(rows: list[dict[str, Any]], fps: float, duration_s: float, path: Path) -> None:
    # Movement rows only for readable burn-in
    moves = [r for r in rows if r["kind"] in ("narration", "music")]
    moves = sorted(moves, key=lambda r: int(r["frame"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i, r in enumerate(moves):
        start = (int(r["frame"]) - 1) / fps
        if i + 1 < len(moves):
            end = (int(moves[i + 1]["frame"]) - 1) / fps
        else:
            end = duration_s
        if end <= start:
            end = min(duration_s, start + 1.5)

        def ts(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int(round((sec - int(sec)) * 1000))
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        label = f"[{r['kind']}] {r['cue']} | f{r['frame']} | {r['approval']}"
        lines += [str(i + 1), f"{ts(start)} --> {ts(end)}", label, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(
    sync: dict[str, Any],
    rows: list[dict[str, Any]],
    preview: dict[str, Any],
    report: RunReport,
) -> tuple[Path, Path]:
    policy = sync["policy"]
    moves = [r for r in rows if r["kind"] in ("narration", "music")]
    auto_n = sum(1 for r in moves if r["approval"] == "automatic")
    man_n = sum(1 for r in moves if r["approval"] == "manually_approved")
    pend_n = sum(1 for r in moves if r["approval"] == "pending_manual")

    payload = {
        "schema_version": 1,
        "updated_at": _utc(),
        "policy": policy,
        "preview": preview,
        "counts": {
            "cues_total": len(rows),
            "movements": len(moves),
            "automatic": auto_n,
            "manually_approved": man_n,
            "pending_manual": pend_n,
        },
        "cues": rows,
        "reactive_controls": [c["label"] for c in sync.get("reactive_controls") or []],
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/music_sync_report.json")

    lines = [
        "# Music sync report — Oino (Interlude)",
        "",
        f"**Updated:** {payload['updated_at']}  ",
        f"**Preview:** `{preview.get('path', '—')}` ({preview.get('status')})",
        "",
        "## Policy",
        "",
        f"- Cut to every beat: `{policy.get('cut_to_every_beat')}`",
        f"- Drive facial performance from amplitude: "
        f"`{policy.get('drive_facial_performance_from_amplitude')}`",
        f"- Drive Oino decisions from amplitude: "
        f"`{policy.get('drive_oino_decisions_from_amplitude')}`",
        f"- Drive every camera cut from amplitude: "
        f"`{policy.get('drive_every_camera_cut_from_amplitude')}`",
        f"- Audio-reactive secondary only: `{policy.get('audio_reactive_secondary_only')}`",
        f"- Characters must listen: `{policy.get('characters_must_listen')}`",
        "",
        "## Approval counts (movements)",
        "",
        f"- Automatic: **{auto_n}**",
        f"- Manually approved: **{man_n}**",
        f"- Pending manual: **{pend_n}**",
        "",
        "## Cues",
        "",
        "| Frame | Cue | Kind | Source | Approval |",
        "|-------|-----|------|--------|----------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['frame']} | {r['cue']} | {r['kind']} | `{r['source']}` | "
            f"**{r['approval']}** |"
        )
    lines += [
        "",
        "## Secondary reactive controls",
        "",
    ]
    for c in sync.get("reactive_controls") or []:
        lines.append(
            f"- **{c['label']}** (`{c['id']}`) — band `{c.get('band')}`, "
            f"max {c.get('max_influence')} → {c.get('target')}"
        )
    lines += [
        "",
        "## Forbidden amplitude targets",
        "",
    ]
    for f in sync.get("forbidden_reactive_targets") or []:
        lines.append(f"- `{f}`")
    lines += [
        "",
        "## Approve pending cues",
        "",
        "```text",
        "python scripts/music_sync.py --approve MUS_TABLE_WARMTH NAR_ARCHIVE_DISCOVERY",
        "python scripts/music_sync.py --preview",
        "```",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/music_sync_report.md")
    return REPORT_MD, REPORT_JSON


def make_preview(
    audio_path: Path,
    srt_path: Path,
    duration_s: float,
    report: RunReport,
) -> dict[str, Any]:
    RENDERS_PREVIEW.mkdir(parents=True, exist_ok=True)
    cfg = load_show_config()
    res = (cfg.get("resolutions") or {}).get("preview") or [960, 540]
    w, h = int(res[0]), int(res[1])

    # Escape path for ffmpeg subtitles filter (Windows)
    srt_esc = srt_path.resolve().as_posix().replace(":", "\\:")
    vf = (
        f"drawtext=text='OINO MUSIC SYNC PREVIEW':x=24:y=24:"
        f"fontsize=22:fontcolor=0xE8E4DC:"
        f"font=Sans,subtitles='{srt_esc}':force_style="
        f"'FontName=Sans,FontSize=16,PrimaryColour=&H00DCE4E8&,OutlineColour=&H00000000&,"
        f"BorderStyle=1,Outline=1,Shadow=0,MarginV=40'"
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
        str(PREVIEW_MP4.resolve()),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        report.fail("preview", "ffmpeg not found on PATH")
        return {"status": "failed", "path": None, "detail": "ffmpeg missing"}

    if proc.returncode != 0 or not PREVIEW_MP4.is_file():
        # Retry without drawtext (font issues) — subtitles + color only
        vf2 = f"subtitles='{srt_esc}'"
        cmd2 = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x0A0A0A:s={w}x{h}:d={duration_s:.6f}:r=24",
            "-i",
            str(audio_path.resolve()),
            "-vf",
            vf2,
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
            str(PREVIEW_MP4.resolve()),
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        if proc2.returncode != 0 or not PREVIEW_MP4.is_file():
            # Last resort: mux audio with black video, no subs
            cmd3 = [
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
                str(PREVIEW_MP4.resolve()),
            ]
            proc3 = subprocess.run(cmd3, capture_output=True, text=True)
            if proc3.returncode != 0 or not PREVIEW_MP4.is_file():
                err = (proc3.stderr or proc.stderr or "")[-2000:]
                report.fail("preview", err or "ffmpeg failed")
                return {"status": "failed", "path": None, "detail": err}
            report.note("Preview written without subtitle burn-in (ffmpeg filter limited)")
            report.mark("created", "renders/preview/music_sync_preview.mp4")
            return {
                "status": "created_no_subs",
                "path": str(PREVIEW_MP4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "audio": "full",
            }

    report.mark("created", "renders/preview/music_sync_preview.mp4")
    return {
        "status": "created",
        "path": str(PREVIEW_MP4.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "audio": "full",
        "resolution": [w, h],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Oino music sync — broad emotional cues")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Write renders/preview/music_sync_preview.mp4 with full audio",
    )
    parser.add_argument(
        "--approve",
        nargs="+",
        default=[],
        help="Mark movement ids as manually_approved",
    )
    args = parser.parse_args()

    report = RunReport(script="music_sync", seed=20261210)
    try:
        sync = load_sync()
        report.mark("reused", "docs/music_sync.json")
        markers = load_audio_markers()
        report.mark("reused", "docs/audio_markers.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("load", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(sync)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    approvals = load_approvals()
    if args.approve:
        for mid in args.approve:
            approvals.setdefault("approvals", {})[mid] = {
                "status": "manually_approved",
                "approved_at": _utc(),
            }
        save_approvals(approvals)
        report.mark("created", "docs/music_sync_approvals.json")
        report.note(f"Approved: {', '.join(args.approve)}")
    elif not APPROVALS_JSON.is_file():
        save_approvals(approvals)
        report.mark("created", "docs/music_sync_approvals.json")

    # Leitmotif review flag
    if LEITMOTIF_JSON.is_file():
        lm = json.loads(LEITMOTIF_JSON.read_text(encoding="utf-8"))
        if lm.get("MUSIC_REVIEW_REQUIRED"):
            report.note("Dionysus leitmotif still MUSIC_REVIEW_REQUIRED")

    rows = build_cue_rows(sync, markers, approvals)
    fps = float(markers.get("fps") or 24)
    duration_s = float(markers.get("duration_seconds") or 131.13)

    # Reactive envelopes from master wav
    audio_path = MASTER_AUDIO
    cfg = load_show_config()
    music_rel = ((cfg.get("audio") or {}).get("mixed_master_path") or "audio/master.wav")
    cand = PROJECT_ROOT / music_rel
    if cand.is_file():
        audio_path = cand
    try:
        rms = read_wav_mono_rms(audio_path)
        reactive = build_reactive_envelopes(sync, rms, fps)
        REACTIVE_JSON.write_text(json.dumps(reactive, indent=2) + "\n", encoding="utf-8")
        report.mark("created", "docs/music_sync_reactive_envelopes.json")
    except Exception as exc:  # noqa: BLE001
        report.note(f"Reactive envelopes skipped: {exc}")

    write_srt(rows, fps, duration_s, SRT_PATH)
    report.mark("created", "cache/music_sync_cues.srt")

    preview_info: dict[str, Any] = {"status": "skipped", "path": None}
    if args.preview:
        preview_info = make_preview(audio_path, SRT_PATH, duration_s, report)
    else:
        report.note("Pass --preview to write full-audio preview movie")

    write_report(sync, rows, preview_info, report)
    report.note(
        "Broad cues only; reactive=secondary; faces/decisions/cuts not amplitude-driven"
    )
    report.write(REPORTS_DIR)

    moves = [r for r in rows if r["kind"] in ("narration", "music")]
    print(
        f"SUMMARY ok={report.ok} movements={len(moves)} "
        f"cues={len(rows)} preview={preview_info.get('status')}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
