"""Single source of truth loader + validator for Oino (Interlude).

Usage:
  python scripts/show_config.py
  python scripts/show_config.py --inspect-audio
  python scripts/show_config.py --inspect-audio --write-duration
  python scripts/show_config.py --json-summary

Duration stays null in the config until ``--inspect-audio --write-duration``
is explicitly run after the mixed master (or music) file is available.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import wave
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROJECT_ROOT, REPORTS_DIR  # noqa: E402
from logging_utils import RunReport  # noqa: E402

SHOW_CONFIG_PATH = PROJECT_ROOT / "config" / "show_config.json"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ENGINE_ALLOWED = frozenset({"BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"})


class ShowConfigError(ValueError):
    """Invalid show configuration."""


def load_show_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or SHOW_CONFIG_PATH
    if not cfg_path.is_file():
        raise FileNotFoundError(
            f"Missing show config (source of truth): {cfg_path}"
        )
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ShowConfigError("show_config.json must be a JSON object")
    return data


def _resolve(project_root: Path, rel: str | None) -> Path | None:
    if rel is None or rel == "":
        return None
    p = Path(rel)
    if p.is_absolute():
        return p
    return project_root / p


def _validate_date(label: str, value: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not DATE_RE.match(value):
        errors.append(f"{label} must be YYYY-MM-DD, got {value!r}")
        return
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        errors.append(f"{label} invalid calendar date: {exc}")


def _validate_rgba(label: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) != 4:
        errors.append(f"{label} must be RGBA list of 4 numbers")
        return
    for i, c in enumerate(value):
        if not isinstance(c, (int, float)):
            errors.append(f"{label}[{i}] must be numeric")
        elif not 0.0 <= float(c) <= 1.0:
            errors.append(f"{label}[{i}] must be in [0, 1], got {c}")


def _validate_resolution(label: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) != 2:
        errors.append(f"{label} must be [width, height]")
        return
    w, h = value
    if not isinstance(w, int) or not isinstance(h, int) or w < 16 or h < 16:
        errors.append(f"{label} dimensions must be integers >= 16, got {value}")


def _validate_hex(label: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, str) or not HEX_RE.match(value):
        errors.append(f"{label} must be #RRGGBB, got {value!r}")


def measure_wav_duration(path: Path) -> float:
    """Return duration in seconds from a WAV header (no hardcoded film length)."""
    if not path.is_file():
        raise FileNotFoundError(f"Cannot inspect audio; file missing: {path}")
    with wave.open(str(path), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
    if rate <= 0:
        raise ShowConfigError(f"Invalid sample rate in {path}")
    return frames / float(rate)


def resolve_render_engine(cfg: dict[str, Any]) -> dict[str, Any]:
    """Pick an engine compatible with installed Blender (or config default)."""
    render = dict(cfg.get("render") or {})
    preferred = render.get("engine", "BLENDER_EEVEE_NEXT")
    fallback = render.get("engine_fallback", "BLENDER_EEVEE")
    exe = render.get("blender_exe")
    env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_EXE")
    if env:
        exe = env

    # Prefer repo finder when available
    blender_path = None
    try:
        repo_root = PROJECT_ROOT.parents[1]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from mvm.blender.runner import find_blender

        blender_path = find_blender()
    except Exception:
        blender_path = Path(exe) if exe else None

    version_str = None
    engine = preferred
    if blender_path and Path(blender_path).exists():
        # Blender 4.2+ → EEVEE_NEXT; older → EEVEE
        name = str(blender_path)
        m = re.search(r"Blender\s*([0-9]+)\.([0-9]+)", name, re.I)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            version_str = f"{major}.{minor}"
            if (major, minor) >= (4, 2):
                engine = preferred if preferred in ENGINE_ALLOWED else "BLENDER_EEVEE_NEXT"
            else:
                engine = fallback
        else:
            engine = preferred
    else:
        # Not installed: keep config engine for 4.2+ target; record absence
        engine = preferred if preferred in ENGINE_ALLOWED else "BLENDER_EEVEE_NEXT"

    return {
        "engine": engine,
        "blender_exe": str(blender_path) if blender_path else None,
        "blender_version_guess": version_str,
        "installed": bool(blender_path and Path(blender_path).exists()),
    }


def validate_show_config(
    cfg: dict[str, Any],
    *,
    project_root: Path | None = None,
    require_optional_audio: bool = False,
) -> list[str]:
    """Return a list of validation errors (empty = ok)."""
    root = project_root or PROJECT_ROOT
    errors: list[str] = []

    for key in (
        "project_title",
        "film_title",
        "working_subtitle",
        "release_date",
        "protagonist",
        "narrator",
    ):
        if not cfg.get(key) or not isinstance(cfg[key], str):
            errors.append(f"Missing or non-string field: {key}")

    _validate_date("release_date", str(cfg.get("release_date", "")), errors)

    title_card = cfg.get("title_card") or {}
    if not isinstance(title_card, dict):
        errors.append("title_card must be an object")
    else:
        if not title_card.get("text"):
            errors.append("title_card.text is required")
        _validate_date(
            "title_card.release_date",
            str(title_card.get("release_date", "")),
            errors,
        )

    audio = cfg.get("audio") or {}
    if not isinstance(audio, dict):
        errors.append("audio must be an object")
        audio = {}

    for field, required_flag in (
        ("music_path", audio.get("music_required", True)),
        ("mixed_master_path", audio.get("mixed_master_required", True)),
        ("narration_path", audio.get("narration_required", False) or require_optional_audio),
    ):
        rel = audio.get(field)
        if rel is None:
            if required_flag:
                errors.append(f"audio.{field} is required but null")
            continue
        if not isinstance(rel, str):
            errors.append(f"audio.{field} must be a string path or null")
            continue
        path = _resolve(root, rel)
        assert path is not None
        if required_flag and not path.is_file():
            errors.append(f"Required audio file missing: {field} → {path}")
        elif not required_flag and not path.is_file():
            # Optional: warn via soft error channel — collect as note-level by prefix
            errors.append(f"WARN optional audio missing: {field} → {path}")

    timing = cfg.get("timing") or {}
    if not isinstance(timing, dict):
        errors.append("timing must be an object")
    else:
        fps = timing.get("fps")
        if not isinstance(fps, int) or fps <= 0:
            errors.append(f"timing.fps must be a positive int, got {fps!r}")
        dur = timing.get("duration_seconds")
        if dur is not None:
            if not isinstance(dur, (int, float)) or float(dur) <= 0:
                errors.append(
                    f"timing.duration_seconds must be null or > 0, got {dur!r}"
                )
        dframes = timing.get("duration_frames")
        if dframes is not None and (
            not isinstance(dframes, int) or dframes <= 0
        ):
            errors.append(
                f"timing.duration_frames must be null or positive int, got {dframes!r}"
            )

    resolutions = cfg.get("resolutions") or {}
    if not isinstance(resolutions, dict):
        errors.append("resolutions must be an object")
    else:
        for name in ("preview", "hd", "final"):
            _validate_resolution(f"resolutions.{name}", resolutions.get(name), errors)

    cm = cfg.get("colour_management") or {}
    if not isinstance(cm, dict):
        errors.append("colour_management must be an object")
    else:
        for rgba_key in ("wine_light_rgba", "ink_line_rgba", "paper_rgba"):
            if rgba_key in cm:
                _validate_rgba(f"colour_management.{rgba_key}", cm[rgba_key], errors)
        if "wine_light_hex" in cm:
            _validate_hex("colour_management.wine_light_hex", cm["wine_light_hex"], errors)
        for num_key in ("exposure", "gamma"):
            if num_key in cm and not isinstance(cm[num_key], (int, float)):
                errors.append(f"colour_management.{num_key} must be numeric")

    render = cfg.get("render") or {}
    if not isinstance(render, dict):
        errors.append("render must be an object")
    else:
        eng = render.get("engine")
        if eng not in ENGINE_ALLOWED:
            errors.append(f"render.engine must be one of {sorted(ENGINE_ALLOWED)}")
        fb = render.get("engine_fallback")
        if fb is not None and fb not in ENGINE_ALLOWED:
            errors.append(
                f"render.engine_fallback must be one of {sorted(ENGINE_ALLOWED)}"
            )

    outputs = cfg.get("outputs") or {}
    if not isinstance(outputs, dict):
        errors.append("outputs must be an object")
    else:
        for key, rel in outputs.items():
            if not isinstance(rel, str) or not rel.strip():
                errors.append(f"outputs.{key} must be a non-empty relative path")
                continue
            # Directories may be created later — validate path shape only
            if Path(rel).is_absolute():
                errors.append(f"outputs.{key} must be project-relative, got {rel}")

    seeds = cfg.get("seeds") or {}
    if not isinstance(seeds, dict) or not seeds:
        errors.append("seeds must be a non-empty object")
    else:
        for name, val in seeds.items():
            if not isinstance(val, int):
                errors.append(f"seeds.{name} must be an int, got {val!r}")

    mythic = cfg.get("mythic_canon")
    if not isinstance(mythic, dict):
        errors.append("mythic_canon must be an object")
    else:
        for key in (
            "inherited_name",
            "family_line",
            "inherited_principle",
            "dionysus_presence_mode",
            "zone_explanation",
        ):
            if not mythic.get(key):
                errors.append(f"mythic_canon.{key} is required")
        if "literal_dionysus_cameo" not in mythic:
            errors.append("mythic_canon.literal_dionysus_cameo is required")
        elif not isinstance(mythic["literal_dionysus_cameo"], bool):
            errors.append("mythic_canon.literal_dionysus_cameo must be boolean")

    motifs = cfg.get("visual_motifs")
    if not isinstance(motifs, dict) or not motifs:
        errors.append("visual_motifs must be a non-empty object")
    else:
        motif_ids: list[str] = []
        for name, body in motifs.items():
            if not isinstance(body, dict):
                errors.append(f"visual_motifs.{name} must be an object")
                continue
            mid = body.get("id")
            if not mid or not isinstance(mid, str):
                errors.append(f"visual_motifs.{name}.id is required")
            else:
                motif_ids.append(mid)
            if "colour_hex" in body:
                _validate_hex(f"visual_motifs.{name}.colour_hex", body["colour_hex"], errors)
        if len(motif_ids) != len(set(motif_ids)):
            errors.append("visual_motifs ids must be unique")

    scenes = cfg.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty list")
    else:
        ids: list[str] = []
        for i, sc in enumerate(scenes):
            if not isinstance(sc, dict):
                errors.append(f"scenes[{i}] must be an object")
                continue
            sid = sc.get("id")
            if not sid or not isinstance(sid, str):
                errors.append(f"scenes[{i}].id is required")
            else:
                ids.append(sid)
        if len(ids) != len(set(ids)):
            dupes = sorted({x for x in ids if ids.count(x) > 1})
            errors.append(f"scene ids must be unique; duplicates: {dupes}")

    return errors


def write_duration_from_audio(
    cfg: dict[str, Any],
    *,
    project_root: Path | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Inspect mixed master (or music) and set timing fields. Does not invent duration."""
    root = project_root or PROJECT_ROOT
    audio = cfg.get("audio") or {}
    rel = audio.get("mixed_master_path") or audio.get("music_path")
    wav = _resolve(root, rel) if rel else None
    if wav is None or not wav.is_file():
        raise FileNotFoundError(
            "Cannot write duration: mixed_master_path / music_path missing on disk"
        )
    seconds = measure_wav_duration(wav)
    fps = int((cfg.get("timing") or {}).get("fps") or 24)
    cfg = dict(cfg)
    timing = dict(cfg.get("timing") or {})
    timing["duration_seconds"] = round(seconds, 6)
    timing["duration_frames"] = int(round(seconds * fps))
    timing["duration_inspected_at"] = datetime.now(timezone.utc).isoformat()
    timing["duration_source"] = str(wav.relative_to(root)).replace("\\", "/")
    cfg["timing"] = timing
    return cfg


def save_show_config(cfg: dict[str, Any], path: Path | None = None) -> Path:
    out = path or SHOW_CONFIG_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Oino show_config.json")
    parser.add_argument(
        "--inspect-audio",
        action="store_true",
        help="Measure WAV duration (does not write unless --write-duration)",
    )
    parser.add_argument(
        "--write-duration",
        action="store_true",
        help="Persist inspected duration into show_config.json",
    )
    parser.add_argument(
        "--require-narration",
        action="store_true",
        help="Fail if narration_path is missing",
    )
    parser.add_argument("--json-summary", action="store_true")
    args = parser.parse_args()

    report = RunReport(script="show_config", seed=None)
    try:
        cfg = load_show_config()
        report.mark("reused", "config/show_config.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("config/show_config.json", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate_show_config(
        cfg, require_optional_audio=args.require_narration
    )
    hard = [e for e in errors if not e.startswith("WARN ")]
    warns = [e[5:] for e in errors if e.startswith("WARN ")]
    for w in warns:
        report.note(f"WARN {w}")
    for e in hard:
        report.fail("validate", e)

    engine_info = resolve_render_engine(cfg)
    report.note(
        f"render_engine={engine_info['engine']} "
        f"blender_installed={engine_info['installed']} "
        f"exe={engine_info['blender_exe']}"
    )

    measured = None
    if args.inspect_audio:
        try:
            audio = cfg.get("audio") or {}
            rel = audio.get("mixed_master_path") or audio.get("music_path")
            wav = _resolve(PROJECT_ROOT, rel)
            if wav is None:
                raise FileNotFoundError("No music/mixed master path in config")
            measured = measure_wav_duration(wav)
            fps = int((cfg.get("timing") or {}).get("fps") or 24)
            report.note(
                f"inspected_duration_seconds={measured:.6f} "
                f"frames_at_{fps}fps={int(round(measured * fps))} "
                f"source={wav.name}"
            )
            if args.write_duration:
                cfg = write_duration_from_audio(cfg)
                # Re-validate after write
                post = validate_show_config(cfg)
                post_hard = [e for e in post if not e.startswith("WARN ")]
                if post_hard:
                    for e in post_hard:
                        report.fail("post_write_validate", e)
                else:
                    save_show_config(cfg)
                    report.mark("created", "timing.duration_seconds (from audio inspect)")
            elif (cfg.get("timing") or {}).get("duration_seconds") is None:
                report.note(
                    "duration remains null in config "
                    "(pass --write-duration to persist after inspect)"
                )
        except Exception as exc:  # noqa: BLE001
            report.fail("inspect_audio", exc)

    if args.json_summary:
        summary = {
            "project_title": cfg.get("project_title"),
            "film_title": cfg.get("film_title"),
            "working_subtitle": cfg.get("working_subtitle"),
            "release_date": cfg.get("release_date"),
            "duration_seconds": (cfg.get("timing") or {}).get("duration_seconds"),
            "measured_seconds": measured,
            "render": engine_info,
            "errors": hard,
            "warnings": warns,
            "ok": report.ok and not hard,
        }
        print(json.dumps(summary, indent=2))

    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok and not hard} "
        f"errors={len(hard)} warnings={len(warns)}"
    )
    return 0 if report.ok and not hard else 1


if __name__ == "__main__":
    raise SystemExit(main())
