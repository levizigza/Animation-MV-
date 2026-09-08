"""Build monologue timing markers from locked narration text.

Uses docs/monologue.txt (exact). Prefer a real narration stem when present.
If timing is unavailable, write provisional paragraph/phrase markers labeled
REVIEW_REQUIRED.

Does not cut solely from punctuation. Protects faces, hands, reflections,
and title-safe area when subtitles are used. Protects the young woman's voice.

Usage:
  python scripts/build_monologue_timing.py
  python scripts/build_monologue_timing.py --check-audio
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import wave
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR  # noqa: E402
from show_config import load_show_config  # noqa: E402

MONOLOGUE_TXT = DOCS_DIR / "monologue.txt"
AUDIO_MARKERS = DOCS_DIR / "audio_markers.json"
TIMING_JSON = DOCS_DIR / "monologue_timing.json"
MARKERS_JSON = DOCS_DIR / "monologue_timing_markers.json"
STATUS_MD = DOCS_DIR / "monologue_timing.md"
SUBSAFE_JSON = DOCS_DIR / "monologue_subtitle_safe.json"

REQUIRED_MARKERS = (
    "AMONG_THE_DUST",
    "HE_WAS_A_WATCHER",
    "FINAL_DAYS",
    "AIR_THICK_WITH_ANTICIPATION",
    "WINDS_WHISPERED",
    "TOWER_OF_BABEL",
    "ICARUS",
    "REFLECTION_OF_CHAOS",
    "DETHRONED_GODS",
    "LABYRINTH",
    "THROUGH_HIS_LENS",
    "SLAVES_TO_VISIONS",
    "CAUTIONARY_TALES",
    "THRESHOLD_OF_ETERNITY",
)

# Cue phrase must appear in monologue.txt (case-insensitive substring)
CUE_PHRASES: tuple[tuple[str, str], ...] = (
    ("AMONG_THE_DUST", "Among the dust"),
    ("HE_WAS_A_WATCHER", "He was a watcher"),
    ("FINAL_DAYS", "final days"),
    ("AIR_THICK_WITH_ANTICIPATION", "air thick with anticipation"),
    ("WINDS_WHISPERED", "winds whispered"),
    ("TOWER_OF_BABEL", "Tower of Babel"),
    ("ICARUS", "Icarus"),
    ("REFLECTION_OF_CHAOS", "reflection of chaos"),
    ("DETHRONED_GODS", "dethroned gods"),
    ("LABYRINTH", "labyrinth"),
    ("THROUGH_HIS_LENS", "Through his lens"),
    ("SLAVES_TO_VISIONS", "slaves to the twisted visions"),
    ("CAUTIONARY_TALES", "cautionary tales"),
    ("THRESHOLD_OF_ETERNITY", "threshold of eternity"),
)


def load_monologue() -> str:
    if not MONOLOGUE_TXT.is_file():
        raise FileNotFoundError(f"Missing {MONOLOGUE_TXT}")
    return MONOLOGUE_TXT.read_text(encoding="utf-8")


def paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return parts


def resolve_narration_path(cfg: dict[str, Any]) -> Path | None:
    audio = cfg.get("audio") or {}
    candidates: list[Path] = []
    for key in ("narration_path", "narration_path_expected"):
        rel = audio.get(key)
        if rel:
            p = Path(rel)
            candidates.append(p if p.is_absolute() else PROJECT_ROOT / p)
    candidates += [
        PROJECT_ROOT / "audio" / "narration.wav",
        PROJECT_ROOT / "audio" / "monologue.wav",
        PROJECT_ROOT / "audio" / "voice.wav",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def load_narration_window(fps: int) -> tuple[int, int, float]:
    """Return (start_frame, end_frame, duration_seconds) for narration span."""
    start_f, end_f = 1, 746
    if AUDIO_MARKERS.is_file():
        data = json.loads(AUDIO_MARKERS.read_text(encoding="utf-8"))
        fps = int(data.get("fps") or fps)
        for m in data.get("structural_markers") or []:
            if m.get("name") == "NARRATION_START":
                start_f = int(m["frame"])
            if m.get("name") == "NARRATION_END":
                end_f = int(m["frame"])
    if end_f < start_f:
        end_f = start_f
    duration_s = (end_f - start_f) / float(fps)
    return start_f, end_f, duration_s


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate() or 1)


def char_weight(s: str) -> int:
    # Prefer spoken substance over punctuation for provisional spacing
    return max(1, len(re.sub(r"[^\w\s]", "", s, flags=re.UNICODE)))


def place_provisional(
    text: str,
    start_f: int,
    end_f: int,
    fps: int,
) -> list[dict[str, Any]]:
    """Distribute cues by character weight inside the narration window.

    Not punctuation-driven cuts — weights approximate breath/attention spans
    until a stem + review locks timing.
    """
    paras = paragraphs(text)
    if not paras:
        raise ValueError("monologue.txt has no paragraphs")

    para_weights = [char_weight(p) for p in paras]
    total_pw = sum(para_weights) or 1
    span = max(1, end_f - start_f)

    # Paragraph windows
    para_windows: list[tuple[int, int]] = []
    cursor = start_f
    for i, w in enumerate(para_weights):
        length = max(1, int(round(span * (w / total_pw))))
        p_end = cursor + length
        if i == len(para_weights) - 1:
            p_end = end_f
        para_windows.append((cursor, min(p_end, end_f)))
        cursor = min(p_end, end_f)

    lower = text
    markers: list[dict[str, Any]] = []
    for name, phrase in CUE_PHRASES:
        idx = lower.lower().find(phrase.lower())
        if idx < 0:
            raise ValueError(f"Phrase for {name} not found in monologue: {phrase!r}")
        # Which paragraph?
        running = 0
        para_i = 0
        for i, p in enumerate(paras):
            # account for blank line separators roughly
            plen = len(p) + (2 if i < len(paras) - 1 else 0)
            if idx < running + len(p):
                para_i = i
                local = idx - running
                break
            running += plen
        else:
            para_i = len(paras) - 1
            local = 0

        p_start, p_end = para_windows[para_i]
        para = paras[para_i]
        # Position by weight before the cue inside the paragraph (attention),
        # not by comma/period count.
        before = para[: max(0, local)]
        frac = char_weight(before) / float(char_weight(para))
        frac = min(0.92, max(0.02, frac))
        frame = p_start + int(round((p_end - p_start) * frac))
        frame = max(start_f, min(end_f, frame))
        t = (frame - 1) / float(fps)
        markers.append(
            {
                "name": name,
                "phrase": phrase,
                "paragraph_index": para_i + 1,
                "frame": frame,
                "time_seconds": round(t, 6),
                "status": "REVIEW_REQUIRED",
                "timing_source": "provisional_weight_in_narration_window",
            }
        )
    return markers


def place_from_narration_wav(
    text: str,
    narr_path: Path,
    fps: int,
) -> list[dict[str, Any]]:
    """When a stem exists, map the full wav duration; still REVIEW until aligned."""
    dur = wav_duration(narr_path)
    end_f = max(1, int(round(dur * fps)) + 1)
    # Stem-local frames 1..end; also store global if window known
    start_f, window_end, _ = load_narration_window(fps)
    local = place_provisional(text, 1, end_f, fps)
    # Remap into global narration window by normalized position
    for m in local:
        norm = (int(m["frame"]) - 1) / float(max(1, end_f - 1))
        g = start_f + int(round((win_end - start_f) * norm))
        m["frame_local"] = m["frame"]
        m["frame"] = max(start_f, min(win_end, g))
        m["time_seconds"] = round((m["frame"] - 1) / float(fps), 6)
        m["timing_source"] = "narration_wav_duration_provisional"
        m["status"] = "REVIEW_REQUIRED"
        m["narration_file"] = str(narr_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return local


def subtitle_safe_spec() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "subtitles_optional": True,
        "protect": {
            "faces": {
                "rule": "Keep lower-third and side captions clear of facial performance.",
                "safe_avoid": ["center_face_roi", "eyeline_band"],
            },
            "hands": {
                "rule": "Do not cover hand contact on door, tape, control, bowl, or sister's tap.",
                "safe_avoid": ["hand_prop_contact_zone"],
            },
            "reflections": {
                "rule": "Keep sister / self reflection readable — no caption over glass story.",
                "safe_avoid": ["PROP_ReflectiveSurface_Sister", "screen_self_reflection"],
            },
            "title_safe": {
                "rule": "Respect title-safe margins; never collide with TITLE_CARD_FINAL typography.",
                "margin_percent": {"top": 10, "bottom": 12, "left": 8, "right": 8},
                "avoid_during": ["TITLE_CARD_FINAL", "SH130_TITLE_CARD"],
            },
        },
        "preferred_subtitle_lane": "lower_third_outside_title_safe_bottom_pad",
        "note": "Protect the young woman's voice — captions support, never replace or drown her.",
    }


def validate_text_cues(text: str) -> list[str]:
    errors: list[str] = []
    lower = text.lower()
    for name, phrase in CUE_PHRASES:
        if phrase.lower() not in lower:
            errors.append(f"monologue.txt missing phrase for {name}: {phrase!r}")
    names = [n for n, _ in CUE_PHRASES]
    if tuple(names) != REQUIRED_MARKERS:
        errors.append("CUE_PHRASES order/ids must match REQUIRED_MARKERS")
    return errors


def write_outputs(
    text: str,
    markers: list[dict[str, Any]],
    *,
    timing_mode: str,
    narr_path: Path | None,
    start_f: int,
    end_f: int,
    fps: int,
    report: RunReport,
) -> None:
    all_review = all(m.get("status") == "REVIEW_REQUIRED" for m in markers)
    payload = {
        "schema_version": 1,
        "monologue_file": "docs/monologue.txt",
        "monologue_unchanged": True,
        "fps": fps,
        "timing_mode": timing_mode,
        "narration_stem": (
            str(narr_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if narr_path
            else None
        ),
        "narration_window": {
            "frame_start": start_f,
            "frame_end": end_f,
            "source": "docs/audio_markers.json NARRATION_START/END"
            if AUDIO_MARKERS.is_file()
            else "default_1_746",
        },
        "policy": {
            "cut_solely_from_punctuation": False,
            "use_breath_emphasis_silence_music_attention": True,
            "protect_young_woman_voice": True,
            "rewrite_monologue": False,
            "provisional_label": "REVIEW_REQUIRED",
            "note": (
                "Do not cut solely from punctuation. Use breath, emphasis, silence, "
                "the music, and the movement of attention. Protect the young woman's voice."
            ),
        },
        "paragraph_count": len(paragraphs(text)),
        "all_markers_review_required": all_review,
        "markers": markers,
    }
    TIMING_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/monologue_timing.json")

    out_markers = {
        "schema_version": 1,
        "editable": True,
        "timing_mode": timing_mode,
        "REVIEW_REQUIRED": all_review,
        "markers": [
            {
                "name": m["name"],
                "frame": m["frame"],
                "time_seconds": m["time_seconds"],
                "status": m["status"],
                "phrase": m["phrase"],
                "source": m.get("timing_source"),
                "paragraph_index": m.get("paragraph_index"),
            }
            for m in markers
        ],
    }
    MARKERS_JSON.write_text(json.dumps(out_markers, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/monologue_timing_markers.json")

    safe = subtitle_safe_spec()
    SUBSAFE_JSON.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/monologue_subtitle_safe.json")

    lines = [
        "# Monologue timing — Oino (Interlude)",
        "",
        f"**Source text:** [`monologue.txt`](monologue.txt) (exact — do not rewrite)  ",
        f"**Timing mode:** `{timing_mode}`  ",
        f"**Narration stem:** `{payload['narration_stem'] or 'not available'}`  ",
        f"**Window:** f{start_f}–f{end_f} @ {fps} fps",
        "",
        "## Policy",
        "",
        "- Do **not** cut solely from punctuation.",
        "- Use **breath, emphasis, silence, the music, and the movement of attention**.",
        "- Protect the **young woman's voice**.",
        "- Provisional timings are labeled **`REVIEW_REQUIRED`**.",
        "",
        "## Subtitle / burn-in protection",
        "",
        "- Faces — keep captions off facial performance / eyeline band",
        "- Hands — do not cover door, tape, control, bowl, or sister's tap",
        "- Reflections — keep sister / self reflection readable",
        "- Title-safe — margins + never collide with `TITLE_CARD_FINAL`",
        "",
        f"Detail: [`monologue_subtitle_safe.json`](monologue_subtitle_safe.json)",
        "",
        "## Markers",
        "",
        "| Marker | Frame | Status | Phrase |",
        "|--------|-------|--------|--------|",
    ]
    for m in markers:
        lines.append(
            f"| `{m['name']}` | {m['frame']} | **{m['status']}** | {m['phrase']} |"
        )
    lines += [
        "",
        "## Paragraph provisional map",
        "",
    ]
    for i, p in enumerate(paragraphs(text), start=1):
        first = next(
            (m for m in markers if m.get("paragraph_index") == i),
            None,
        )
        preview = p[:72] + ("…" if len(p) > 72 else "")
        lines.append(
            f"{i}. f{(first or {}).get('frame', '?')} — {preview}"
        )
    lines += [
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/build_monologue_timing.py",
        "python scripts/build_monologue_timing.py --check-audio",
        "```",
        "",
        "When a reviewed stem alignment exists, re-run and clear `REVIEW_REQUIRED` "
        "only after human approval.",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/monologue_timing.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build monologue timing markers")
    parser.add_argument(
        "--check-audio",
        action="store_true",
        help="Report narration stem / master presence",
    )
    args = parser.parse_args()

    report = RunReport(script="build_monologue_timing", seed=20261210)
    cfg = load_show_config()
    fps = int((cfg.get("timing") or {}).get("fps") or 24)

    try:
        text = load_monologue()
        report.mark("reused", "docs/monologue.txt")
    except Exception as exc:  # noqa: BLE001
        report.fail("monologue", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate_text_cues(text)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    narr_path = resolve_narration_path(cfg)
    start_f, end_f, _ = load_narration_window(fps)

    if narr_path:
        report.note(f"Narration stem found: {narr_path.name} — provisional map still REVIEW_REQUIRED until aligned")
        markers = place_from_narration_wav(text, narr_path, fps)
        timing_mode = "narration_stem_present_provisional"
        report.mark("reused", str(narr_path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
    else:
        report.note(
            "Narration stem not available — provisional paragraph markers REVIEW_REQUIRED"
        )
        markers = place_provisional(text, start_f, end_f, fps)
        timing_mode = "provisional_no_stem"

    # Ensure required set
    have = {m["name"] for m in markers}
    for req in REQUIRED_MARKERS:
        if req not in have:
            report.fail("markers", f"Missing {req}")
    if not report.ok:
        report.write(REPORTS_DIR)
        return 1

    write_outputs(
        text,
        markers,
        timing_mode=timing_mode,
        narr_path=narr_path,
        start_f=start_f,
        end_f=end_f,
        fps=fps,
        report=report,
    )

    if args.check_audio:
        master = PROJECT_ROOT / ((cfg.get("audio") or {}).get("mixed_master_path") or "audio/master.wav")
        report.note(f"master.wav present={master.is_file()}")
        report.note(f"narration stem present={narr_path is not None}")
        report.note(f"NARRATION window f{start_f}-{end_f}")

    report.note(
        "14 cues; no punctuation-only cuts; voice protected; "
        f"status=REVIEW_REQUIRED mode={timing_mode}"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} markers={len(markers)} "
        f"mode={timing_mode} review_required=True"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
