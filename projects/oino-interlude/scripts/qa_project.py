"""Technical QA for Oino (Interlude) production tree.

Checks linked files, audio, cameras, frame ranges, shot IDs, markers,
materials, title card text/date, and output paths.

Usage:
  python scripts/qa_project.py
  python scripts/qa_project.py --strict
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import wave
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import (  # noqa: E402
    CANON_PATH,
    DOCS_DIR,
    MASTER_AUDIO,
    PROJECT_ROOT,
    RENDERS_DIR,
    REPORTS_DIR,
    SCENES_DIR,
)
from show_config import load_show_config  # noqa: E402

QA_MD = DOCS_DIR / "technical_qa_report.md"
QA_JSON = DOCS_DIR / "technical_qa_report.json"
EMOTIONAL_QA = DOCS_DIR / "emotional_qa.md"

TITLE_EXACT = "One Of Gods Fools"
DATE_EXACT = "December 10, 2026"
DATE_ISO = "2026-12-10"

REQUIRED_REVIEW_DIRS = (
    "ANIMATIC_REVIEW",
    "PERFORMANCE_REVIEW",
    "WORLD_REVIEW",
    "COLOUR_REVIEW",
    "TITLE_CARD_REVIEW",
    "FINAL_REVIEW",
)

REQUIRED_CAMERA_LANG = (
    "attic",
    "archive",
    "steam",
    "electric",
    "digital",
    "zone",
    "table",
    "return",
    "title_card",
)

REQUIRED_MONO_MARKERS = (
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


def add(
    findings: list[dict[str, Any]],
    *,
    category: str,
    severity: str,
    detail: str,
    path: str | None = None,
) -> None:
    findings.append(
        {
            "category": category,
            "severity": severity,
            "detail": detail,
            "path": path,
        }
    )


def check_audio(findings: list[dict[str, Any]], cfg: dict[str, Any]) -> None:
    music = ((cfg.get("audio") or {}).get("mixed_master_path") or "audio/master.wav")
    path = PROJECT_ROOT / music
    if not path.is_file():
        path = MASTER_AUDIO
    if not path.is_file():
        add(
            findings,
            category="broken_audio",
            severity="fail",
            detail="Mixed master / master.wav missing",
            path=str(music),
        )
        return
    try:
        with wave.open(str(path), "rb") as w:
            if w.getnframes() <= 0 or w.getframerate() <= 0:
                add(
                    findings,
                    category="broken_audio",
                    severity="fail",
                    detail="Audio has zero frames or invalid rate",
                    path=str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                )
            else:
                add(
                    findings,
                    category="broken_audio",
                    severity="pass",
                    detail=(
                        f"Audio OK {w.getnchannels()}ch {w.getframerate()}Hz "
                        f"{w.getnframes()} frames"
                    ),
                    path=str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                )
    except Exception as exc:  # noqa: BLE001
        add(
            findings,
            category="broken_audio",
            severity="fail",
            detail=f"Cannot read audio: {exc}",
            path=str(path),
        )


def check_title_card(findings: list[dict[str, Any]]) -> None:
    # CANON
    if CANON_PATH.is_file():
        text = CANON_PATH.read_text(encoding="utf-8")
        if TITLE_EXACT not in text:
            add(
                findings,
                category="incorrect_title_card_text",
                severity="fail",
                detail=f"CANON.md missing exact '{TITLE_EXACT}'",
                path="CANON.md",
            )
        else:
            add(
                findings,
                category="incorrect_title_card_text",
                severity="pass",
                detail="CANON contains exact title",
                path="CANON.md",
            )
        if DATE_EXACT not in text and DATE_ISO not in text:
            add(
                findings,
                category="missing_release_date",
                severity="fail",
                detail=f"CANON.md missing '{DATE_EXACT}'",
                path="CANON.md",
            )
        else:
            add(
                findings,
                category="missing_release_date",
                severity="pass",
                detail="CANON contains release date",
                path="CANON.md",
            )
    else:
        add(
            findings,
            category="incorrect_title_card_text",
            severity="fail",
            detail="CANON.md missing",
            path="CANON.md",
        )

    brief = DOCS_DIR / "title_card_brief.json"
    if brief.is_file():
        data = json.loads(brief.read_text(encoding="utf-8"))
        title = (data.get("title") or {}).get("text")
        date = (data.get("release_date") or {}).get("text")
        if title != TITLE_EXACT:
            add(
                findings,
                category="incorrect_title_card_text",
                severity="fail",
                detail=f"title_card_brief text is {title!r}",
                path="docs/title_card_brief.json",
            )
        else:
            add(
                findings,
                category="incorrect_title_card_text",
                severity="pass",
                detail="title_card_brief text exact",
                path="docs/title_card_brief.json",
            )
        if date != DATE_EXACT:
            add(
                findings,
                category="missing_release_date",
                severity="fail",
                detail=f"title_card_brief date is {date!r}",
                path="docs/title_card_brief.json",
            )
        else:
            add(
                findings,
                category="missing_release_date",
                severity="pass",
                detail="title_card_brief date exact",
                path="docs/title_card_brief.json",
            )
        if "'" in (title or "") or "\u2019" in (title or ""):
            add(
                findings,
                category="incorrect_title_card_text",
                severity="fail",
                detail="Apostrophe found in Gods — forbidden",
                path="docs/title_card_brief.json",
            )


def check_cameras_and_shots(findings: list[dict[str, Any]]) -> None:
    cam_path = DOCS_DIR / "camera_system.json"
    csv_path = DOCS_DIR / "shot_list.csv"
    anim_path = DOCS_DIR / "animatic_shot_list.json"

    if not cam_path.is_file():
        add(
            findings,
            category="missing_cameras",
            severity="fail",
            detail="camera_system.json missing",
            path="docs/camera_system.json",
        )
    else:
        cam = json.loads(cam_path.read_text(encoding="utf-8"))
        langs = cam.get("camera_language") or {}
        for req in REQUIRED_CAMERA_LANG:
            if req not in langs:
                add(
                    findings,
                    category="missing_cameras",
                    severity="fail",
                    detail=f"Missing camera language: {req}",
                )
        shots = cam.get("shots") or []
        ids = [s.get("id") for s in shots]
        if len(ids) != len(set(ids)):
            add(
                findings,
                category="duplicate_shot_ids",
                severity="fail",
                detail="Duplicate shot ids in camera_system.json",
            )
        else:
            add(
                findings,
                category="duplicate_shot_ids",
                severity="pass",
                detail="camera_system shot ids unique",
            )
        cameras = {s.get("camera") for s in shots if s.get("camera")}
        if len(cameras) < 1:
            add(
                findings,
                category="missing_cameras",
                severity="fail",
                detail="No camera names on shots",
            )
        else:
            add(
                findings,
                category="missing_cameras",
                severity="pass",
                detail=f"{len(cameras)} camera names present",
            )
        for s in shots:
            sid = s.get("id", "?")
            a, b = int(s.get("frame_start") or 0), int(s.get("frame_end") or -1)
            if b < a:
                add(
                    findings,
                    category="invalid_frame_ranges",
                    severity="fail",
                    detail=f"{sid}: frame_end < frame_start",
                )

    if csv_path.is_file():
        with csv_path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        ids = [r.get("shot_id") for r in rows]
        if len(ids) != len(set(ids)):
            add(
                findings,
                category="duplicate_shot_ids",
                severity="fail",
                detail="Duplicate shot_id in shot_list.csv",
                path="docs/shot_list.csv",
            )
        for r in rows:
            try:
                a, b = int(r["frame_start"]), int(r["frame_end"])
            except (KeyError, ValueError):
                add(
                    findings,
                    category="invalid_frame_ranges",
                    severity="fail",
                    detail=f"Bad frames on {r.get('shot_id')}",
                    path="docs/shot_list.csv",
                )
                continue
            if b < a:
                add(
                    findings,
                    category="invalid_frame_ranges",
                    severity="fail",
                    detail=f"{r.get('shot_id')}: invalid range {a}-{b}",
                    path="docs/shot_list.csv",
                )
        add(
            findings,
            category="invalid_frame_ranges",
            severity="pass",
            detail=f"shot_list.csv ranges checked ({len(rows)} shots)",
            path="docs/shot_list.csv",
        )
    else:
        add(
            findings,
            category="invalid_frame_ranges",
            severity="fail",
            detail="shot_list.csv missing",
            path="docs/shot_list.csv",
        )

    if anim_path.is_file():
        anim = json.loads(anim_path.read_text(encoding="utf-8"))
        ids = [s.get("id") for s in (anim.get("shots") or [])]
        if len(ids) != len(set(ids)):
            add(
                findings,
                category="duplicate_shot_ids",
                severity="fail",
                detail="Duplicate ids in animatic_shot_list.json",
            )


def check_markers(findings: list[dict[str, Any]]) -> None:
    required_files = {
        "docs/audio_markers.json": (
            "AUDIO_START",
            "NARRATION_START",
            "NARRATION_END",
            "TITLE_CARD_START",
            "TITLE_CARD_END",
            "CUE_KNOCK",
            "CUE_RELEASE",
            "CUE_FINAL_PHRASE",
        ),
        "docs/monologue_timing_markers.json": REQUIRED_MONO_MARKERS,
        "docs/title_card_markers.json": ("TITLE_CARD_FINAL",),
    }
    for rel, names in required_files.items():
        path = PROJECT_ROOT / rel
        if not path.is_file():
            add(
                findings,
                category="missing_markers",
                severity="fail",
                detail=f"Missing marker file",
                path=rel,
            )
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if "structural_markers" in data or "broad_cues" in data:
            have = {m["name"] for m in (data.get("structural_markers") or [])}
            have |= {m["name"] for m in (data.get("broad_cues") or [])}
        else:
            have = {m.get("name") for m in (data.get("markers") or [])}
        missing = [n for n in names if n not in have]
        if missing:
            add(
                findings,
                category="missing_markers",
                severity="fail",
                detail=f"Missing markers: {', '.join(missing)}",
                path=rel,
            )
        else:
            add(
                findings,
                category="missing_markers",
                severity="pass",
                detail=f"Required markers present ({len(names)})",
                path=rel,
            )


def check_materials(findings: list[dict[str, Any]]) -> None:
    audit = DOCS_DIR / "material_audit_report.json"
    lib = DOCS_DIR / "material_library.json"
    if audit.is_file():
        data = json.loads(audit.read_text(encoding="utf-8"))
        pink = data.get("pink_textures") or []
        if pink:
            add(
                findings,
                category="pink_or_disconnected_materials",
                severity="fail",
                detail=f"Pink texture flags: {len(pink)}",
                path="docs/material_audit_report.json",
            )
        else:
            add(
                findings,
                category="pink_or_disconnected_materials",
                severity="pass",
                detail="No pink texture flags in filesystem audit",
                path="docs/material_audit_report.json",
            )
        # Disconnected / unsupported need blend audit
        blend = data.get("blend_audit")
        if not blend or blend.get("status") in (None, "deferred", "not run"):
            add(
                findings,
                category="unsupported_nodes_or_modifiers",
                severity="warn",
                detail="Blend node audit not run (Blender deferred)",
                path="docs/material_audit_report.json",
            )
        else:
            fails = [
                f
                for f in (blend.get("findings") or [])
                if f.get("severity") == "fail"
                and f.get("category")
                in ("unsupported_nodes", "disconnected_shaders", "pink_textures")
            ]
            if fails:
                add(
                    findings,
                    category="unsupported_nodes_or_modifiers",
                    severity="fail",
                    detail=f"{len(fails)} blend material failures",
                )
            else:
                add(
                    findings,
                    category="unsupported_nodes_or_modifiers",
                    severity="pass",
                    detail="Blend material audit clean of fail-level node issues",
                )
    elif lib.is_file():
        add(
            findings,
            category="pink_or_disconnected_materials",
            severity="warn",
            detail="material_library present but audit report missing — run build_material_library.py",
        )
    else:
        add(
            findings,
            category="pink_or_disconnected_materials",
            severity="warn",
            detail="No material audit yet",
        )

    # Missing linked texture files
    if lib.is_file():
        data = json.loads(lib.read_text(encoding="utf-8"))
        missing = []
        for m in data.get("materials") or []:
            for rel in m.get("expected_images") or []:
                if not (PROJECT_ROOT / rel).is_file():
                    missing.append(rel)
        if missing:
            add(
                findings,
                category="missing_linked_files",
                severity="warn",
                detail=f"{len(missing)} expected material images not on disk (placeholders OK until authored)",
            )
        else:
            add(
                findings,
                category="missing_linked_files",
                severity="pass",
                detail="All declared material images present",
            )


def check_cost(findings: list[dict[str, Any]]) -> None:
    atmo = DOCS_DIR / "atmosphere.json"
    if not atmo.is_file():
        add(
            findings,
            category="excessive_particle_or_geometry_cost",
            severity="warn",
            detail="atmosphere.json missing",
        )
        return
    data = json.loads(atmo.read_text(encoding="utf-8"))
    preview = (data.get("versions") or {}).get("preview") or {}
    final = (data.get("versions") or {}).get("final") or {}
    if preview.get("particle_budget") not in ("low", "crafted"):
        add(
            findings,
            category="excessive_particle_or_geometry_cost",
            severity="warn",
            detail=f"Unexpected preview particle_budget={preview.get('particle_budget')}",
        )
    # Flag any effect with final density > 0.85 as cost watch
    heavy = [
        e["id"]
        for e in (data.get("effects") or [])
        if float((e.get("final") or {}).get("density") or 0) > 0.85
    ]
    if heavy:
        add(
            findings,
            category="excessive_particle_or_geometry_cost",
            severity="warn",
            detail=f"High final density effects: {', '.join(heavy)}",
        )
    else:
        add(
            findings,
            category="excessive_particle_or_geometry_cost",
            severity="pass",
            detail=(
                f"Atmosphere budgets preview={preview.get('particle_budget')} "
                f"final={final.get('particle_budget')}; no extreme densities"
            ),
        )
    crutches = data.get("forbidden_crutches") or []
    if "constant_particle_fields" not in crutches:
        add(
            findings,
            category="excessive_particle_or_geometry_cost",
            severity="fail",
            detail="Atmosphere must forbid constant_particle_fields",
        )


def check_output_paths(findings: list[dict[str, Any]]) -> None:
    review_root = RENDERS_DIR / "review"
    if not review_root.is_dir():
        add(
            findings,
            category="output_path_errors",
            severity="warn",
            detail="renders/review missing — run render_review_versions.py",
            path="renders/review",
        )
        return
    for name in REQUIRED_REVIEW_DIRS:
        d = review_root / name
        if not d.is_dir():
            add(
                findings,
                category="output_path_errors",
                severity="fail",
                detail=f"Missing review output dir {name}",
                path=f"renders/review/{name}",
            )
            continue
        man = d / "manifest.json"
        if not man.is_file():
            add(
                findings,
                category="output_path_errors",
                severity="fail",
                detail=f"Missing manifest in {name}",
                path=f"renders/review/{name}",
            )
            continue
        data = json.loads(man.read_text(encoding="utf-8"))
        if data.get("emotional_qa_on_screen") is not False:
            add(
                findings,
                category="output_path_errors",
                severity="fail",
                detail=f"{name} manifest allows emotional QA on screen",
            )
        out_movie = data.get("output_movie")
        if not out_movie or ".." in str(out_movie):
            add(
                findings,
                category="output_path_errors",
                severity="fail",
                detail=f"{name} invalid output_movie path",
            )
        else:
            add(
                findings,
                category="output_path_errors",
                severity="pass",
                detail=f"{name} output path OK",
                path=out_movie,
            )


def check_emotional_qa_doc(findings: list[dict[str, Any]]) -> None:
    if not EMOTIONAL_QA.is_file():
        add(
            findings,
            category="missing_markers",
            severity="fail",
            detail="emotional_qa.md missing",
            path="docs/emotional_qa.md",
        )
        return
    text = EMOTIONAL_QA.read_text(encoding="utf-8")
    if "Do not place these questions inside the film" not in text and "never on screen" not in text.lower():
        add(
            findings,
            category="output_path_errors",
            severity="fail",
            detail="emotional_qa.md must state questions are not for the film",
        )
    required_snippets = [
        "Oino is the protagonist",
        "Dionysus felt without becoming exposition",
        "holy fool",
        "One Of Gods Fools",
        "December 10, 2026",
        "Zone ambiguous",
    ]
    missing = [s for s in required_snippets if s.lower() not in text.lower() and s not in text]
    # holy fool / Zone checks with flexible match
    if "protagonist" not in text.lower():
        missing.append("protagonist")
    if "One Of Gods Fools" not in text:
        missing.append("One Of Gods Fools")
    if "December 10, 2026" not in text:
        missing.append("December 10, 2026")
    if missing:
        # filter duplicates from flexible checks
        miss = []
        if "Oino is the protagonist" not in text:
            miss.append("protagonist question")
        if "One Of Gods Fools" not in text:
            miss.append("title exact")
        if "December 10, 2026" not in text:
            miss.append("date exact")
        if "exposition" not in text.lower():
            miss.append("Dionysus exposition")
        if "holy fool" not in text.lower():
            miss.append("holy fool")
        if "zone" not in text.lower():
            miss.append("Zone")
        if miss:
            add(
                findings,
                category="missing_markers",
                severity="fail",
                detail=f"emotional_qa.md incomplete: {', '.join(miss)}",
            )
        else:
            add(
                findings,
                category="missing_markers",
                severity="pass",
                detail="emotional_qa.md present with key locks",
                path="docs/emotional_qa.md",
            )
    else:
        add(
            findings,
            category="missing_markers",
            severity="pass",
            detail="emotional_qa.md present with key locks",
            path="docs/emotional_qa.md",
        )


def write_reports(findings: list[dict[str, Any]], report: RunReport) -> None:
    counts: dict[str, int] = {"fail": 0, "warn": 0, "pass": 0, "info": 0}
    for f in findings:
        counts[f.get("severity", "info")] = counts.get(f.get("severity", "info"), 0) + 1

    payload = {
        "schema_version": 1,
        "title_card_exact": TITLE_EXACT,
        "release_date_exact": DATE_EXACT,
        "counts": counts,
        "ok": counts.get("fail", 0) == 0,
        "findings": findings,
        "emotional_qa": "docs/emotional_qa.md",
        "emotional_qa_on_screen": False,
    }
    QA_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/technical_qa_report.json")

    lines = [
        "# Technical QA report — Oino (Interlude)",
        "",
        f"**OK:** `{payload['ok']}`  ",
        f"**Fail / warn / pass:** {counts.get('fail', 0)} / {counts.get('warn', 0)} / {counts.get('pass', 0)}",
        "",
        f"**Title lock:** `{TITLE_EXACT}`  ",
        f"**Date lock:** `{DATE_EXACT}`  ",
        "",
        "Emotional questions: [`emotional_qa.md`](emotional_qa.md) (not for on-screen use).",
        "",
        "| Severity | Category | Detail | Path |",
        "|----------|----------|--------|------|",
    ]
    for f in findings:
        lines.append(
            f"| `{f['severity']}` | `{f['category']}` | {f['detail']} | "
            f"`{f.get('path') or '—'}` |"
        )
    lines += [
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/qa_project.py",
        "python scripts/qa_project.py --strict",
        "python scripts/render_review_versions.py",
        "```",
        "",
    ]
    QA_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/technical_qa_report.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Technical QA for Oino project")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures for exit code",
    )
    args = parser.parse_args()

    report = RunReport(script="qa_project", seed=20261210)
    cfg = load_show_config()
    findings: list[dict[str, Any]] = []

    check_audio(findings, cfg)
    check_title_card(findings)
    check_cameras_and_shots(findings)
    check_markers(findings)
    check_materials(findings)
    check_cost(findings)
    check_output_paths(findings)
    check_emotional_qa_doc(findings)

    # Linked blend scenes — note deferred
    blends = list(SCENES_DIR.glob("*.blend")) if SCENES_DIR.is_dir() else []
    if not blends:
        add(
            findings,
            category="missing_linked_files",
            severity="warn",
            detail="No .blend files yet (Blender deferred) — scene packages pending",
            path="scenes/",
        )
    else:
        add(
            findings,
            category="missing_linked_files",
            severity="pass",
            detail=f"{len(blends)} blend file(s) present",
            path="scenes/",
        )

    write_reports(findings, report)

    fails = sum(1 for f in findings if f["severity"] == "fail")
    warns = sum(1 for f in findings if f["severity"] == "warn")
    for f in findings:
        if f["severity"] == "fail":
            report.fail(f["category"], f["detail"])
        elif f["severity"] == "warn":
            report.note(f"WARN {f['category']}: {f['detail']}")

    report.note(
        "Emotional QA is docs-only — never place those questions inside the film"
    )
    report.write(REPORTS_DIR)

    ok = fails == 0 and (not args.strict or warns == 0)
    print(
        f"SUMMARY ok={ok} fail={fails} warn={warns} "
        f"findings={len(findings)} title={TITLE_EXACT!r}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
