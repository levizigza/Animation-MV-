"""Set up AUDIO_MASTER / AUDIO_TIMELINE and editable audio markers for Oino.

Idempotent. Does not cut animation to every beat/transient.

Usage:
  python scripts/setup_audio.py
  python scripts/setup_audio.py --write-blend
  python scripts/setup_audio.py --reset-markers   # regenerate JSON from analysis
                                                 # (refuses to wipe hand-edited
                                                 #  markers unless --force)
"""

from __future__ import annotations

import argparse
import json
import math
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
    BEATMAP_JSON,
    DOCS_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    SCENES_DIR,
    require_file,
)
from show_config import (  # noqa: E402
    load_show_config,
    measure_wav_duration,
    resolve_render_engine,
)

MARKERS_JSON = DOCS_DIR / "audio_markers.json"
TIMING_REPORT = DOCS_DIR / "audio_timing_report.md"
BLEND_PATH = SCENES_DIR / "AUDIO_MASTER.blend"
BLENDER_SETUP_SCRIPT = SCRIPTS_DIR / "_blender_audio_master.py"

# Required structural markers (frames set from audio)
STRUCTURAL_MARKER_NAMES = (
    "AUDIO_START",
    "NARRATION_START",
    "NARRATION_END",
    "MUSIC_END",
    "FINAL_FRAME",
    "TITLE_CARD_START",
    "TITLE_CARD_END",
)

# Broad dramatic cues — NOT per-beat
BROAD_CUE_NAMES = (
    "CUE_ENTRANCE",
    "CUE_REST",
    "CUE_HARMONIC_CHANGE",
    "CUE_FIRST_MELODY",
    "CUE_LOOP",
    "CUE_KNOCK",
    "CUE_RELEASE",
    "CUE_FINAL_PHRASE",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve(root: Path, rel: str | None) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    return p if p.is_absolute() else root / p


def inspect_wav(path: Path) -> dict[str, Any]:
    require_file(path, "audio")
    with wave.open(str(path), "rb") as w:
        channels = w.getnchannels()
        sample_rate = w.getframerate()
        sample_width = w.getsampwidth()
        frames = w.getnframes()
    duration = frames / float(sample_rate) if sample_rate else 0.0
    return {
        "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frames": frames,
        "duration_seconds": round(duration, 6),
    }


def load_beatmap() -> dict[str, Any] | None:
    if not BEATMAP_JSON.is_file():
        return None
    return json.loads(BEATMAP_JSON.read_text(encoding="utf-8"))


def sec_to_frame(seconds: float, fps: int) -> int:
    return max(1, int(math.floor(seconds * fps + 1e-9)) + (0 if seconds <= 0 else 0) or 1)


def frame_from_time(t: float, fps: int) -> int:
    """Frame index at time t (1-based Blender-style)."""
    if t <= 0:
        return 1
    return int(round(t * fps)) + 1


def search_dionysus_motif(report: RunReport) -> dict[str, Any]:
    """Search project for an existing Dionysus audio/MIDI motif. None found → proposal."""
    roots = [
        PROJECT_ROOT / "audio",
        PROJECT_ROOT / "assets",
        PROJECT_ROOT.parents[1] / "assets",
    ]
    patterns = ("*dionys*", "*leitmotif*", "*leitmotiv*", "*bacch*")
    found: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            for p in root.rglob(pat):
                if p.suffix.lower() in {".wav", ".mp3", ".ogg", ".flac", ".mid", ".midi", ".aiff"}:
                    found.append(str(p))

    # Textual canon references only — not a musical source
    text_hits = [
        "CANON.md (textual lineage)",
        "config/show_config.json mythic_canon",
        "docs/creative_bible.md",
    ]
    report.note("Dionysus search: no dedicated audio/MIDI leitmotif source file found")
    for h in text_hits:
        report.note(f"textual_reference:{h}")

    if found:
        src = found[0]
        report.mark("reused", f"dionysus_source:{src}")
        return {
            "cue_id": "DIONYSUS_LEITMOTIF",
            "status": "SOURCE_FOUND",
            "source_file": src,
            "MUSIC_REVIEW_REQUIRED": False,
            "proposal_notes": None,
            "appearances": _leitmotif_appearances(),
        }

    # Placeholder 4-note proposal only — not locked music
    proposal = {
        "cue_id": "DIONYSUS_LEITMOTIF",
        "status": "MUSIC_REVIEW_REQUIRED",
        "MUSIC_REVIEW_REQUIRED": True,
        "source_file": None,
        "proposal": {
            "kind": "placeholder_four_note_motif",
            "pitch_names": ["E3", "G3", "A3", "E4"],
            "midi_notes": [52, 55, 57, 64],
            "interval_shape": "m3 ↑ · M2 ↑ · P5 ↑ (open, nourishing leap)",
            "suggested_durations_beats": [1.0, 1.0, 1.0, 2.0],
            "tonal_centre_hint": "E minor / modal — review against father's unfinished melody",
            "not_final": True,
        },
        "appearances": _leitmotif_appearances(),
        "search_notes": (
            "No Dionysus theme audio/MIDI located in oino-interlude or repo assets. "
            "Textual mythic presence only. This cue is a reusable placeholder for music review."
        ),
    }
    report.mark("created", "DIONYSUS_LEITMOTIF (placeholder proposal)")
    return proposal


def _leitmotif_appearances() -> dict[str, str]:
    return {
        "human_family_melody": "Singable / hummable contour in domestic register",
        "loom_or_work_rhythm": "Even pulse, shuttle-like repeats of the interval cells",
        "dance_rhythm": "Accent shift; same pitches, livelier subdivision",
        "distorted_digital_pattern": "Bit-crushed / time-stretched echo of the contour",
        "too_perfect_memorial_loop": "Quantized, airless loop — shadow of control",
        "living_variation_at_end": "Breathing rubato / sister's altered note kinship",
    }


def build_markers(
    *,
    fps: int,
    duration_s: float,
    beatmap: dict[str, Any] | None,
    narration_separate: bool,
    narration_info: dict[str, Any] | None,
) -> dict[str, Any]:
    final_frame = max(1, int(math.ceil(duration_s * fps)))
    # Title card: last ~4.0s of picture (editable)
    title_len_s = 4.0
    title_start_s = max(0.0, duration_s - title_len_s)

    # Narration window: if separate, use that file; if embedded, editable guess = intro→early verse
    if narration_separate and narration_info:
        narr_start_s = 0.0
        narr_end_s = float(narration_info["duration_seconds"])
    else:
        # Embedded / absent stem — broad editable defaults from MIR sections
        narr_start_s = 0.0
        narr_end_s = 14.28  # end of intro section from beatmap default
        if beatmap and beatmap.get("sections"):
            # Prefer first two sections as archive-narration span (editable)
            secs = beatmap["sections"]
            narr_end_s = float(secs[min(1, len(secs) - 1)]["end"])

    music_start_s = 0.0
    music_end_s = duration_s

    def mk(name: str, t: float, note: str, editable: bool = True) -> dict[str, Any]:
        if name in ("MUSIC_END", "FINAL_FRAME", "TITLE_CARD_END") or t >= duration_s - 1e-6:
            fr = final_frame
            t_out = duration_s
        elif t <= 0 or name == "AUDIO_START":
            fr = 1
            t_out = 0.0
        else:
            fr = max(1, min(final_frame, int(round(t * fps))))
            t_out = t
        return {
            "name": name,
            "time_seconds": round(t_out, 6),
            "frame": fr,
            "editable": editable,
            "note": note,
        }

    structural = [
        mk("AUDIO_START", 0.0, "First sample of mixed timeline", editable=False),
        mk(
            "NARRATION_START",
            narr_start_s,
            "Start of archive monologue (embedded estimate — edit if stem arrives)",
        ),
        mk(
            "NARRATION_END",
            narr_end_s,
            "End of primary narration span (editable; not auto-locked to beats)",
        ),
        mk("MUSIC_END", music_end_s, "Last frame of music / mixed master"),
        mk("FINAL_FRAME", duration_s, "Picture end = ceil(duration*fps) alignment"),
        mk(
            "TITLE_CARD_START",
            title_start_s,
            "One Of God's Fools card begins (default last 4s — editable)",
        ),
        mk("TITLE_CARD_END", duration_s, "Title card holds through FINAL_FRAME"),
    ]
    # Fix FINAL_FRAME / MUSIC_END / TITLE_CARD_END frames explicitly
    for m in structural:
        if m["name"] in ("MUSIC_END", "FINAL_FRAME", "TITLE_CARD_END"):
            m["frame"] = final_frame
            m["time_seconds"] = round(duration_s, 6)

    # Broad cues from MIR sections — sparse, story-facing
    sections = (beatmap or {}).get("sections") or []
    energy = (beatmap or {}).get("energy_curve") or []

    def section_time(name_substr: str, which: str = "start") -> float | None:
        hits = [s for s in sections if name_substr in s.get("name", "")]
        if not hits:
            return None
        s = hits[0] if which == "start" else hits[-1]
        return float(s["start"] if which == "start" else s["end"])

    intro_end = float(sections[0]["end"]) if sections else 14.0
    first_chorus = next((s for s in sections if s.get("name") == "chorus"), None)
    bridge = next((s for s in sections if s.get("name") == "bridge"), None)
    outro = next((s for s in sections if s.get("name") == "outro"), None)

    # Harmonic / section change: first chorus entrance
    harmonic_t = float(first_chorus["start"]) if first_chorus else intro_end
    # First melody: early verse after intro (not every onset)
    first_melody_t = float(sections[1]["start"]) if len(sections) > 1 else 8.0
    # Loop: start of repeated chorus block (2nd chorus if present)
    choruses = [s for s in sections if s.get("name") == "chorus"]
    loop_t = float(choruses[1]["start"]) if len(choruses) > 1 else harmonic_t
    # Knock: sister call — slightly before intro→verse join (editable; distinct from first melody)
    knock_t = max(0.0, intro_end - 1.5)
    # Rest: bridge low energy
    rest_t = float(bridge["start"]) if bridge else duration_s * 0.75
    # Release: holy-fool / energy drop into outro
    release_t = float(outro["start"]) if outro else duration_s * 0.87
    # Final phrase: mid-outro before title
    final_phrase_t = (release_t + title_start_s) / 2.0

    broad = [
        mk("CUE_ENTRANCE", 0.0, "World / archive entrance — music breathes in"),
        mk("CUE_FIRST_MELODY", first_melody_t, "First clear melodic statement (broad)"),
        mk("CUE_HARMONIC_CHANGE", harmonic_t, "First major section / harmonic turn"),
        mk("CUE_KNOCK", knock_t, "Sister's call-to-dinner knock (emotional trigger)"),
        mk("CUE_LOOP", loop_t, "Memorial / repeating chorus loop character"),
        mk("CUE_REST", rest_t, "Breath / bridge rest — do not fill with busy cuts"),
        mk("CUE_RELEASE", release_t, "Release toward sister / holy-fool letting go"),
        mk("CUE_FINAL_PHRASE", final_phrase_t, "Last living phrase before title card"),
    ]

    return {
        "schema_version": 1,
        "editable": True,
        "fps": fps,
        "duration_seconds": round(duration_s, 6),
        "final_frame": final_frame,
        "policy": {
            "cut_to_every_beat": False,
            "cut_to_every_transient": False,
            "use_broad_cues_only": True,
            "note": (
                "Do not synchronize every edit to every beat. "
                "Markers are broad dramatic cues; refine by hand."
            ),
        },
        "structural_markers": structural,
        "broad_cues": broad,
        "updated_at": _utc(),
    }


def write_markers_json(
    data: dict[str, Any],
    *,
    reset: bool,
    force: bool,
    report: RunReport,
) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if MARKERS_JSON.exists() and not reset:
        report.mark("reused", "docs/audio_markers.json")
        return MARKERS_JSON
    if MARKERS_JSON.exists() and reset and not force:
        existing = json.loads(MARKERS_JSON.read_text(encoding="utf-8"))
        if existing.get("hand_edited"):
            report.mark(
                "skipped",
                "docs/audio_markers.json (hand_edited=true; pass --force to overwrite)",
            )
            return MARKERS_JSON
    existed = MARKERS_JSON.exists()
    MARKERS_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report.mark("reused" if existed else "created", "docs/audio_markers.json")
    return MARKERS_JSON


def write_timing_report(
    *,
    cfg: dict[str, Any],
    music: dict[str, Any],
    narration: dict[str, Any] | None,
    narration_mode: str,
    markers: dict[str, Any],
    leitmotif: dict[str, Any],
    blender_result: dict[str, Any],
    report: RunReport,
) -> Path:
    fps = markers["fps"]
    lines = [
        "# Audio timing report — Oino (Interlude)",
        "",
        f"**Generated:** { _utc() }  ",
        f"**Film:** {cfg.get('film_title')} · **Album:** {cfg.get('project_title')}  ",
        f"**Scene:** `AUDIO_MASTER` · **VSE:** `AUDIO_TIMELINE`",
        "",
        "## Detection summary",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Music path | `{music['path']}` |",
        f"| Sample rate | {music['sample_rate']} Hz |",
        f"| Channel count | {music['channels']} |",
        f"| Duration | {music['duration_seconds']:.6f} s |",
        f"| FPS | {fps} |",
        f"| Duration → frames | {markers['final_frame']} (FINAL_FRAME) |",
        f"| Music start | 0.000 s · frame 1 |",
        f"| Music end | {music['duration_seconds']:.6f} s · frame {markers['final_frame']} |",
        f"| Narration mode | **{narration_mode}** |",
    ]
    if narration:
        lines += [
            f"| Narration path | `{narration['path']}` |",
            f"| Narration duration | {narration['duration_seconds']:.6f} s |",
            f"| Narration SR / ch | {narration['sample_rate']} Hz / {narration['channels']} ch |",
        ]
    else:
        lines += [
            "| Narration path | `null` (no separate stem in show_config) |",
            "| Narration start/end | See markers (embedded estimate — editable) |",
        ]

    lines += [
        "",
        "## Narration vs music",
        "",
    ]
    if narration_mode == "separate":
        lines.append(
            "Narration is a **separate** file from music. Both are laid on `AUDIO_TIMELINE`."
        )
    elif narration_mode == "embedded":
        lines.append(
            "Narration is treated as **embedded** in the mixed master "
            "(`narration_path` is null; `monologue_unchanged` remains true). "
            "`NARRATION_START` / `NARRATION_END` are **editable estimates**, not stem cuts."
        )
    else:
        lines.append("Narration status unresolved — check `show_config.json` audio block.")

    lines += [
        "",
        "## Structural markers",
        "",
        "| Name | Time (s) | Frame | Note |",
        "|------|----------|-------|------|",
    ]
    for m in markers["structural_markers"]:
        lines.append(
            f"| `{m['name']}` | {m['time_seconds']:.3f} | {m['frame']} | {m['note']} |"
        )

    lines += [
        "",
        "## Broad dramatic cues (not per-beat)",
        "",
        "Policy: **do not** cut animation automatically to every transient or beat.",
        "",
        "| Name | Time (s) | Frame | Note |",
        "|------|----------|-------|------|",
    ]
    for m in markers["broad_cues"]:
        lines.append(
            f"| `{m['name']}` | {m['time_seconds']:.3f} | {m['frame']} | {m['note']} |"
        )

    lines += [
        "",
        "## Dionysus leitmotif",
        "",
        f"- Cue id: `{leitmotif['cue_id']}`",
        f"- Status: **{leitmotif['status']}**",
        f"- `MUSIC_REVIEW_REQUIRED`: `{leitmotif.get('MUSIC_REVIEW_REQUIRED')}`",
        f"- Source file: `{leitmotif.get('source_file')}`",
        "",
    ]
    if leitmotif.get("proposal"):
        p = leitmotif["proposal"]
        lines += [
            "### Placeholder proposal (not locked)",
            "",
            f"- Pitches: {', '.join(p['pitch_names'])}",
            f"- MIDI: {p['midi_notes']}",
            f"- Shape: {p['interval_shape']}",
            f"- Hint: {p['tonal_centre_hint']}",
            "",
        ]
    lines += [
        "### Required appearance modes",
        "",
    ]
    for k, v in (leitmotif.get("appearances") or {}).items():
        lines.append(f"- **{k.replace('_', ' ')}:** {v}")

    lines += [
        "",
        "## Blender scene",
        "",
        f"- Target blend: `{BLEND_PATH.relative_to(PROJECT_ROOT).as_posix()}`",
        f"- Status: {blender_result.get('status')}",
        f"- Detail: {blender_result.get('detail')}",
        "",
        "## Editable source",
        "",
        f"Hand-edit markers in [`audio_markers.json`](audio_markers.json). "
        f"Set `\"hand_edited\": true` after intentional changes so "
        f"`setup_audio.py --reset-markers` will not overwrite without `--force`.",
        "",
    ]
    TIMING_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/audio_timing_report.md")
    return TIMING_REPORT


def write_blender_helper_script() -> Path:
    """Write a bpy script invoked by Blender — creates AUDIO_MASTER + VSE strips."""
    code = r'''
# Auto-generated helper — invoked by setup_audio.py
import json
import sys
from pathlib import Path

payload_path = Path(sys.argv[sys.argv.index("--") + 1])
data = json.loads(payload_path.read_text(encoding="utf-8"))

import bpy

# Preserve user work: only rebuild named scene if missing or reset flag
reset = data.get("reset", False)
scene_name = "AUDIO_MASTER"
vse_name = "AUDIO_TIMELINE"

if scene_name in bpy.data.scenes and not reset:
    scene = bpy.data.scenes[scene_name]
else:
    if scene_name in bpy.data.scenes and reset:
        bpy.data.scenes.remove(bpy.data.scenes[scene_name])
    scene = bpy.data.scenes.new(scene_name)

bpy.context.window.scene = scene
fps = int(data["fps"])
scene.render.fps = fps
scene.frame_start = 1
scene.frame_end = int(data["final_frame"])
scene.render.resolution_x = int(data["resolution"][0])
scene.render.resolution_y = int(data["resolution"][1])

if not scene.sequence_editor:
    scene.sequence_editor_create()
sed = scene.sequence_editor
# Clear only strips we own on reset
if reset:
    for s in list(sed.sequences_all):
        sed.sequences.remove(s)

def ensure_sound(name, path, channel, frame_start):
    existing = sed.sequences.get(name)
    if existing and not reset:
        return existing
    if existing and reset:
        sed.sequences.remove(existing)
    return sed.sequences.new_sound(name=name, filepath=path, channel=channel, frame_start=frame_start)

music = data["music_path"]
ensure_sound("MUSIC_MASTER", music, channel=1, frame_start=1)
if data.get("narration_path"):
    ensure_sound("NARRATION", data["narration_path"], channel=2, frame_start=1)

# Timeline markers
for m in data["markers"]:
    name = m["name"]
    frame = int(m["frame"])
    if name in scene.timeline_markers:
        if not reset:
            continue
        scene.timeline_markers.remove(scene.timeline_markers[name])
    marker = scene.timeline_markers.new(name, frame=frame)
    marker.name = name

# Store VSE logical name as custom property
scene["vse_timeline_name"] = vse_name
scene["oino_audio_setup"] = True

out = Path(data["blend_out"])
out.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print(f"OINO_AUDIO_MASTER_OK {out}")
'''
    BLENDER_SETUP_SCRIPT.write_text(code.lstrip("\n"), encoding="utf-8")
    return BLENDER_SETUP_SCRIPT


def try_build_blend(
    *,
    cfg: dict[str, Any],
    music_path: Path,
    narration_path: Path | None,
    markers: dict[str, Any],
    reset: bool,
    write_blend: bool,
    report: RunReport,
) -> dict[str, Any]:
    if not write_blend:
        return {
            "status": "skipped",
            "detail": "Pass --write-blend to create scenes/AUDIO_MASTER.blend when Blender is available",
        }

    engine = resolve_render_engine(cfg)
    blender = engine.get("blender_exe")
    if not blender:
        # Still write helper + payload for later
        write_blender_helper_script()
        payload = _blend_payload(cfg, music_path, narration_path, markers, reset)
        payload_path = PROJECT_ROOT / "cache" / "audio_master_payload.json"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        report.mark("created", "cache/audio_master_payload.json")
        report.mark("created", "scripts/_blender_audio_master.py")
        report.note("Blender not installed — blend creation deferred")
        return {
            "status": "deferred",
            "detail": (
                "Blender not found. Payload + bpy helper written; "
                "re-run with Blender on PATH / BLENDER_PATH and --write-blend"
            ),
        }

    if BLEND_PATH.exists() and not reset:
        report.mark("reused", "scenes/AUDIO_MASTER.blend")
        return {
            "status": "reused",
            "detail": f"Existing {BLEND_PATH.name} preserved (pass --reset to rebuild)",
        }

    write_blender_helper_script()
    payload = _blend_payload(cfg, music_path, narration_path, markers, reset)
    payload_path = PROJECT_ROOT / "cache" / "audio_master_payload.json"
    payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    cmd = [
        str(blender),
        "--background",
        "--python",
        str(BLENDER_SETUP_SCRIPT),
        "--",
        str(payload_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not BLEND_PATH.exists():
        report.fail(
            "AUDIO_MASTER.blend",
            proc.stderr[-1500:] or proc.stdout[-1500:] or f"exit {proc.returncode}",
        )
        return {"status": "failed", "detail": "Blender subprocess failed"}
    report.mark("created", "scenes/AUDIO_MASTER.blend")
    return {"status": "created", "detail": str(BLEND_PATH)}


def _blend_payload(
    cfg: dict[str, Any],
    music_path: Path,
    narration_path: Path | None,
    markers: dict[str, Any],
    reset: bool,
) -> dict[str, Any]:
    res = (cfg.get("resolutions") or {}).get("hd") or [1920, 1080]
    all_markers = markers["structural_markers"] + markers["broad_cues"]
    return {
        "fps": markers["fps"],
        "final_frame": markers["final_frame"],
        "resolution": res,
        "music_path": str(music_path.resolve()),
        "narration_path": str(narration_path.resolve()) if narration_path else None,
        "markers": all_markers,
        "blend_out": str(BLEND_PATH.resolve()),
        "reset": reset,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Oino AUDIO_MASTER setup")
    parser.add_argument("--write-blend", action="store_true")
    parser.add_argument(
        "--reset-markers",
        action="store_true",
        help="Regenerate audio_markers.json from analysis",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting hand_edited markers / rebuild blend",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Rebuild Blender scene strips/markers (preserves other .blends)",
    )
    args = parser.parse_args()

    report = RunReport(script="setup_audio", seed=None, reset=args.reset)
    cfg = load_show_config()
    fps = int((cfg.get("timing") or {}).get("fps") or 24)
    audio = cfg.get("audio") or {}

    music_rel = audio.get("mixed_master_path") or audio.get("music_path")
    music_path = _resolve(PROJECT_ROOT, music_rel)
    if music_path is None or not music_path.is_file():
        report.fail("music", f"Missing music/mixed master: {music_rel}")
        report.write(REPORTS_DIR)
        return 1

    music = inspect_wav(music_path)
    report.mark("reused", music["path"])

    narr_rel = audio.get("narration_path")
    narr_path = _resolve(PROJECT_ROOT, narr_rel) if narr_rel else None
    narration = None
    if narr_path and narr_path.is_file():
        narration = inspect_wav(narr_path)
        narration_mode = "separate"
        report.mark("reused", narration["path"])
    elif narr_rel:
        report.fail("narration", f"Configured narration_path missing: {narr_path}")
        narration_mode = "missing_configured_stem"
    else:
        narration_mode = "embedded"
        report.note("narration_path=null -> embedded in mixed master (or absent stem)")

    duration_s = float(music["duration_seconds"])
    beatmap = load_beatmap()
    if beatmap:
        report.mark("reused", "beatmap.json")

    markers = build_markers(
        fps=fps,
        duration_s=duration_s,
        beatmap=beatmap,
        narration_separate=(narration_mode == "separate"),
        narration_info=narration,
    )
    markers["audio_detection"] = {
        "music": music,
        "narration": narration,
        "narration_mode": narration_mode,
        "fps": fps,
        "seconds_per_frame": round(1.0 / fps, 8),
        "frames_from_duration": markers["final_frame"],
    }

    leitmotif = search_dionysus_motif(report)
    markers["dionysus_leitmotif"] = leitmotif

    # Persist markers
    if MARKERS_JSON.exists() and not args.reset_markers:
        # Keep hand edits; still refresh report from current file + detection
        on_disk = json.loads(MARKERS_JSON.read_text(encoding="utf-8"))
        report.mark("reused", "docs/audio_markers.json")
        # Merge detection metadata into report source of truth file lightly
        on_disk["audio_detection"] = markers["audio_detection"]
        on_disk["dionysus_leitmotif"] = leitmotif
        if not on_disk.get("hand_edited"):
            # Update structural frames if duration changed and not hand-edited
            on_disk["structural_markers"] = markers["structural_markers"]
            on_disk["broad_cues"] = markers["broad_cues"]
            on_disk["duration_seconds"] = markers["duration_seconds"]
            on_disk["final_frame"] = markers["final_frame"]
            on_disk["fps"] = fps
            on_disk["updated_at"] = _utc()
            MARKERS_JSON.write_text(json.dumps(on_disk, indent=2) + "\n", encoding="utf-8")
            report.note("Refreshed marker times from audio (file not hand_edited)")
        markers_out = on_disk
    else:
        write_markers_json(
            markers, reset=args.reset_markers, force=args.force, report=report
        )
        markers_out = markers

    blender_result = try_build_blend(
        cfg=cfg,
        music_path=music_path,
        narration_path=narr_path if narration else None,
        markers=markers_out if "structural_markers" in markers_out else markers,
        reset=args.reset or args.force,
        write_blend=args.write_blend,
        report=report,
    )

    write_timing_report(
        cfg=cfg,
        music=music,
        narration=narration,
        narration_mode=narration_mode,
        markers=markers_out if "structural_markers" in markers_out else markers,
        leitmotif=leitmotif,
        blender_result=blender_result,
        report=report,
    )

    # Side-copy leitmotif proposal for music review
    motif_path = DOCS_DIR / "dionysus_leitmotif.json"
    motif_path.write_text(json.dumps(leitmotif, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/dionysus_leitmotif.json")

    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} narration_mode={narration_mode} "
        f"duration_s={duration_s:.3f} final_frame={markers['final_frame']} "
        f"leitmotif={leitmotif['status']} blend={blender_result['status']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
