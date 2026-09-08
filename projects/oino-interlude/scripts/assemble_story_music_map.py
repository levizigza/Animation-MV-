"""Assemble docs/story_music_map.json from current locked sources.

Does not re-run music sync, monologue timing, or shot-list generation.
Reads only existing docs and writes the missing map + a short MD twin.

Usage:
  python scripts/assemble_story_music_map.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, REPORTS_DIR  # noqa: E402

OUT_JSON = DOCS_DIR / "story_music_map.json"
OUT_MD = DOCS_DIR / "story_music_map.md"
SHOT_LIST = DOCS_DIR / "shot_list.csv"
MUSIC_SYNC = DOCS_DIR / "music_sync_report.json"
MONO = DOCS_DIR / "monologue_timing.json"
AUDIO_MARKERS = DOCS_DIR / "audio_markers.json"
APPROVALS = DOCS_DIR / "music_sync_approvals.json"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_shots() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with SHOT_LIST.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                {
                    "shot_id": row["shot_id"],
                    "hero": row.get("hero") == "yes",
                    "camera": row.get("camera"),
                    "frame_start": int(row["frame_start"]),
                    "frame_end": int(row["frame_end"]),
                    "camera_language": row.get("camera_language"),
                    "emotional_purpose": row.get("emotional_purpose"),
                    "parent_animatic": row.get("parent_animatic"),
                    "lighting_preset": row.get("lighting_preset"),
                }
            )
    return rows


def overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    return not (a1 < b0 or b1 < a0)


def main() -> int:
    report = RunReport(script="assemble_story_music_map", seed=20261210)
    missing = [p for p in (SHOT_LIST, MUSIC_SYNC, MONO, AUDIO_MARKERS) if not p.is_file()]
    if missing:
        for p in missing:
            report.fail("source", f"Missing {p}")
        report.write(REPORTS_DIR)
        return 1

    shots = load_shots()
    sync = json.loads(MUSIC_SYNC.read_text(encoding="utf-8"))
    mono = json.loads(MONO.read_text(encoding="utf-8"))
    audio = json.loads(AUDIO_MARKERS.read_text(encoding="utf-8"))
    approvals = {}
    if APPROVALS.is_file():
        approvals = json.loads(APPROVALS.read_text(encoding="utf-8"))

    cues = sync.get("cues") or []
    phrases = mono.get("markers") or mono.get("phrases") or []
    if isinstance(phrases, dict):
        phrases = list(phrases.values())

    mapped: list[dict[str, Any]] = []
    for shot in shots:
        s0, s1 = shot["frame_start"], shot["frame_end"]
        shot_cues = [
            {
                "id": c.get("id") or c.get("cue"),
                "kind": c.get("kind"),
                "frame": c.get("frame"),
                "approval": c.get("approval"),
                "note": c.get("note") or c.get("cue"),
            }
            for c in cues
            if isinstance(c.get("frame"), int) and s0 <= int(c["frame"]) <= s1
        ]
        shot_phrases = []
        for p in phrases:
            pf = p.get("frame") or p.get("frame_start")
            if pf is None:
                continue
            pf = int(pf)
            pe = int(p.get("frame_end") or pf)
            if overlaps(s0, s1, pf, pe):
                shot_phrases.append(
                    {
                        "id": p.get("id") or p.get("marker") or p.get("name"),
                        "frame": pf,
                        "status": p.get("status") or "REVIEW_REQUIRED",
                        "text_excerpt": (p.get("phrase") or p.get("text") or p.get("label") or "")[
                            :80
                        ],
                    }
                )
        mapped.append(
            {
                **shot,
                "music_cues_in_range": shot_cues,
                "narration_phrases_in_range": shot_phrases,
                "timing_gate": (
                    "blocked"
                    if any(c.get("approval") == "pending_manual" for c in shot_cues)
                    or any(
                        (p.get("status") or "").upper() == "REVIEW_REQUIRED"
                        for p in shot_phrases
                    )
                    else "ok_for_layout"
                ),
            }
        )

    counts = sync.get("counts") or {}
    payload = {
        "schema_version": 1,
        "assembled_at": _utc(),
        "film": "Oino (Interlude)",
        "sources": {
            "shot_list": "docs/shot_list.csv",
            "music_sync_report": "docs/music_sync_report.json",
            "monologue_timing": "docs/monologue_timing.json",
            "audio_markers": "docs/audio_markers.json",
            "music_sync_approvals": "docs/music_sync_approvals.json",
        },
        "policy_note": (
            "Map only. Do not cut to every beat. Characters listen; "
            "amplitude does not puppeteer faces, decisions, or every cut."
        ),
        "audio": {
            "duration_seconds": audio.get("duration_seconds"),
            "fps": audio.get("fps") or 24,
            "final_frame": audio.get("final_frame"),
            "narration_mode": "embedded",
            "narration_path": None,
        },
        "approval_summary": {
            "music_manually_approved": counts.get("manually_approved", 0),
            "music_pending_manual": counts.get("pending_manual", 0),
            "music_automatic": counts.get("automatic", 0),
            "music_sync_approvals_file": approvals.get("approvals") or {},
            "monologue_all_review_required": all(
                (p.get("status") or "").upper() == "REVIEW_REQUIRED" for p in phrases
            )
            if phrases
            else True,
            "timing_approved": False,
            "note": "Timing is NOT approved until pending_manual = 0 and monologue REVIEW_REQUIRED cleared by human.",
        },
        "shots": mapped,
    }

    if OUT_JSON.is_file():
        report.mark("reused", "docs/story_music_map.json (will overwrite with assemble)")
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/story_music_map.json")

    blocked = sum(1 for s in mapped if s["timing_gate"] == "blocked")
    lines = [
        "# Story ↔ music map — Oino (Interlude)",
        "",
        f"**Assembled:** {payload['assembled_at']}  ",
        f"**Timing approved:** `False`  ",
        f"**Music pending manual:** {counts.get('pending_manual', 0)}  ",
        f"**Shots with timing gate blocked:** {blocked}/{len(mapped)}",
        "",
        "## Policy",
        "",
        payload["policy_note"],
        "",
        "## Shots",
        "",
        "| Shot | Frames | Gate | Cues | Narration phrases |",
        "|------|--------|------|------|-------------------|",
    ]
    for s in mapped:
        lines.append(
            f"| `{s['shot_id']}` | {s['frame_start']}–{s['frame_end']} | "
            f"**{s['timing_gate']}** | {len(s['music_cues_in_range'])} | "
            f"{len(s['narration_phrases_in_range'])} |"
        )
    lines += [
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/assemble_story_music_map.py",
        "```",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/story_music_map.md")
    report.note(f"shots={len(mapped)} timing_gate_blocked={blocked}")
    report.write(REPORTS_DIR)
    print(f"SUMMARY ok={report.ok} shots={len(mapped)} blocked={blocked}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
