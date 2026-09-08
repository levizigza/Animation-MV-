"""Animate the final meal — opening mirrored; memory becomes participation.

Sister keeps her own rhythm; changed note is a real creative contribution.
Original recording ends imperfectly beside living women; living melody carries out.
Final story image: open doorway. Final film image: Prompt 22 title card.

Usage:
  python scripts/animate_final_meal.py
  python scripts/animate_final_meal.py --check-links
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, PROJECT_ROOT, REPORTS_DIR  # noqa: E402

FM_JSON = DOCS_DIR / "final_meal_animation.json"
STATUS_MD = DOCS_DIR / "final_meal_animation.md"
MARKERS_JSON = DOCS_DIR / "final_meal_markers.json"
CALL_MOTIF = DOCS_DIR / "call_to_dinner_motif.json"
ANIMATIC = DOCS_DIR / "animatic_shot_list.json"
HF_JSON = DOCS_DIR / "holy_fool_turning.json"
CANON = PROJECT_ROOT / "CANON.md"
SHOW_CONFIG = PROJECT_ROOT / "config" / "show_config.json"

REQUIRED_MIRROR_IDS = (
    "MIRROR_01_CALL",
    "MIRROR_02_DELAY",
    "MIRROR_03_BOWLS",
    "MIRROR_04_DOOR",
    "MIRROR_05_MELODY",
)

REQUIRED_ENDING_IDS = (
    "FM_OINO_DOWNSTAIRS",
    "FM_SISTER_ANGRY",
    "FM_OINO_SITS_BESIDE",
    "FM_ACCEPTS_BOWL",
    "FM_PRESENT_NO_FORGIVENESS_DEMAND",
    "FM_SISTER_TAPS_OLD",
    "FM_OINO_ANSWERS",
    "FM_SISTER_CHANGES_NOTE",
    "FM_OINO_ALMOST_CORRECTS",
    "FM_OINO_FOLLOWS",
    "FM_OPEN_DOORWAY",
    "FM_TITLE_CARD",
)

REQUIRED_OPENING_ACTIONS = (
    "sister calls Oino",
    "Oino delays",
    "two bowls wait",
    "the attic door closes",
    "the family melody is repeated exactly",
)

TITLE_TEXT = "One Of Gods Fools"
TITLE_DATE = "December 10, 2026"


def load_fm() -> dict[str, Any]:
    if not FM_JSON.is_file():
        raise FileNotFoundError(f"Missing {FM_JSON}")
    return json.loads(FM_JSON.read_text(encoding="utf-8"))


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("scene") != "SCN_09_FINAL_MEAL":
        errors.append("scene must be SCN_09_FINAL_MEAL")

    policy = data.get("policy") or {}
    if policy.get("sister_is_symbolic_child") is not False:
        errors.append("policy.sister_is_symbolic_child must be false")
    if policy.get("sister_has_own_rhythm") is not True:
        errors.append("policy.sister_has_own_rhythm must be true")
    if policy.get("changed_note_is_real_creative_contribution") is not True:
        errors.append(
            "policy.changed_note_is_real_creative_contribution must be true"
        )
    if policy.get("literal_magic_trick_ending") is not False:
        errors.append("policy.literal_magic_trick_ending must be false")
    if (policy.get("true_transformation") or "").lower() != "memory becoming participation":
        errors.append(
            "policy.true_transformation must be 'memory becoming participation'"
        )
    if (policy.get("final_story_image") or "").lower() != "open doorway":
        errors.append("policy.final_story_image must be open doorway")
    if "prompt 22" not in (policy.get("final_film_image") or "").lower():
        errors.append("policy.final_film_image must cite Prompt 22 title card")
    if policy.get("title_card_text") != TITLE_TEXT:
        errors.append(f"policy.title_card_text must be exactly '{TITLE_TEXT}'")
    if policy.get("title_card_date") != TITLE_DATE:
        errors.append(f"policy.title_card_date must be exactly '{TITLE_DATE}'")

    mirrors = data.get("composition_mirror") or []
    mids = [m.get("id") for m in mirrors]
    for req in REQUIRED_MIRROR_IDS:
        if req not in mids:
            errors.append(f"Missing composition mirror: {req}")
    for m in mirrors:
        mid = m.get("id", "?")
        if not (m.get("opening") or "").strip():
            errors.append(f"{mid}: opening required")
        if not (m.get("ending") or "").strip():
            errors.append(f"{mid}: ending required")

    opening = (data.get("opening_reference") or {}).get("beats") or []
    open_actions = [(b.get("action") or "").strip() for b in opening]
    for req in REQUIRED_OPENING_ACTIONS:
        if req not in open_actions:
            errors.append(f"opening_reference missing action: {req}")

    ending = data.get("ending_beats") or []
    eids = [b.get("id") for b in ending]
    if len(eids) != len(set(eids)):
        errors.append("ending_beats ids must be unique")
    for req in REQUIRED_ENDING_IDS:
        if req not in eids:
            errors.append(f"Missing ending beat: {req}")

    prev = -1
    story_final = 0
    film_final = 0
    by_id = {b.get("id"): b for b in ending}
    for b in ending:
        bid = b.get("id", "?")
        for key in ("marker", "who", "action", "staging"):
            if not (b.get(key) or "").strip():
                errors.append(f"{bid}: {key} required")
        frame = int(b.get("frame") or 0)
        if frame <= prev:
            errors.append(f"{bid}: frames must increase")
        prev = frame
        if b.get("final_story_image"):
            story_final += 1
        if b.get("final_film_image"):
            film_final += 1

    if story_final != 1:
        errors.append("Exactly one beat must set final_story_image (open doorway)")
    if film_final != 1:
        errors.append("Exactly one beat must set final_film_image (title card)")

    doorway = by_id.get("FM_OPEN_DOORWAY") or {}
    if not doorway.get("final_story_image"):
        errors.append("FM_OPEN_DOORWAY must be final_story_image")
    if "doorway" not in (doorway.get("action") or "").lower():
        errors.append("FM_OPEN_DOORWAY action must name the open doorway")

    title = by_id.get("FM_TITLE_CARD") or {}
    if not title.get("final_film_image"):
        errors.append("FM_TITLE_CARD must be final_film_image")
    if title.get("title_text") != TITLE_TEXT:
        errors.append(f"FM_TITLE_CARD.title_text must be '{TITLE_TEXT}'")
    if title.get("title_date") != TITLE_DATE:
        errors.append(f"FM_TITLE_CARD.title_date must be '{TITLE_DATE}'")
    if title.get("link_prompt") != "Prompt 22":
        errors.append("FM_TITLE_CARD.link_prompt must be Prompt 22")

    change = by_id.get("FM_SISTER_CHANGES_NOTE") or {}
    if change.get("creative_contribution") is not True:
        errors.append("FM_SISTER_CHANGES_NOTE must mark creative_contribution true")

    audio = data.get("audio_layering") or {}
    orig = audio.get("original_recording") or {}
    if orig.get("audible") is not True:
        errors.append("audio_layering.original_recording.audible must be true")
    layer = audio.get("layering") or {}
    if layer.get("brief_overlap") is not True:
        errors.append("audio_layering.layering.brief_overlap must be true")
    staging = (layer.get("staging") or "").lower()
    if "briefly" not in staging or "living" not in staging:
        errors.append(
            "audio layering staging must brief-overlap then let living carry final sound"
        )

    dion = data.get("dionysian_transformation") or {}
    if dion.get("subtle") is not True:
        errors.append("dionysian_transformation.subtle must be true")
    if dion.get("literal_magic_trick") is not False:
        errors.append("dionysian_transformation.literal_magic_trick must be false")
    if (dion.get("true_transformation") or "").lower() != "memory becoming participation":
        errors.append(
            "dionysian_transformation.true_transformation must be memory becoming participation"
        )
    for medium in ("water", "juice", "light"):
        if medium not in (dion.get("may_briefly_resemble_wine") or []):
            errors.append(
                f"dionysian_transformation.may_briefly_resemble_wine must include {medium}"
            )

    must_not = " ".join(data.get("must_not") or []).lower()
    for term in ("symbolic child", "magic", "forgiveness", "title card"):
        if term not in must_not:
            errors.append(f"must_not should address '{term}'")

    return errors


def check_links(data: dict[str, Any], report: RunReport) -> None:
    if CALL_MOTIF.is_file():
        motif = json.loads(CALL_MOTIF.read_text(encoding="utf-8"))
        ids = {a.get("id") for a in (motif.get("appearances") or [])}
        for need in ("CALL_01_SISTER_DOWNSTAIRS", "CALL_06_TABLE_TAP_NEW_MELODY"):
            if need not in ids:
                report.fail("link", f"call motif missing {need}")
        call06 = next(
            (
                a
                for a in (motif.get("appearances") or [])
                if a.get("id") == "CALL_06_TABLE_TAP_NEW_MELODY"
            ),
            None,
        )
        avoid = ((call06 or {}).get("visual_form") or {}).get("avoid") or ""
        if "moral prop" not in avoid.lower():
            report.note("CALL_06 avoid text should keep sister from moral-prop staging")
        else:
            report.note("call motif CALL_01 / CALL_06 linked")
    else:
        report.note("call_to_dinner_motif.json missing — skip motif links")

    if ANIMATIC.is_file():
        anim = json.loads(ANIMATIC.read_text(encoding="utf-8"))
        shots = {s.get("id") for s in (anim.get("shots") or [])}
        for need in data.get("approx_animatic_shots") or []:
            if need not in shots:
                report.fail("link", f"animatic shot missing: {need}")
            else:
                report.note(f"animatic {need} linked")
    else:
        report.note("animatic_shot_list.json missing — skip animatic links")

    if HF_JSON.is_file():
        hf = json.loads(HF_JSON.read_text(encoding="utf-8"))
        last_hf = max(
            (int(b.get("frame") or 0) for b in (hf.get("beats") or [])),
            default=0,
        )
        first_fm = min(
            (int(b.get("frame") or 0) for b in (data.get("ending_beats") or [])),
            default=0,
        )
        if first_fm <= last_hf:
            report.fail(
                "link",
                f"final meal start f{first_fm} must follow holy-fool (last f{last_hf})",
            )
        else:
            report.note(f"final meal f{first_fm} follows holy-fool (last f{last_hf})")
    else:
        report.note("holy_fool_turning.json missing — skip order link")

    if CANON.is_file():
        text = CANON.read_text(encoding="utf-8")
        if TITLE_TEXT not in text or "2026" not in text:
            report.fail("link", "CANON.md missing exact title card lock")
        else:
            report.note("CANON title card lock present")
    else:
        report.note("CANON.md missing — title text still enforced in brief")

    if SHOW_CONFIG.is_file():
        cfg = json.loads(SHOW_CONFIG.read_text(encoding="utf-8"))
        card = cfg.get("title_card") or {}
        # show_config may use apostrophe variant; craft lock follows CANON exact string
        if card.get("release_date") not in ("2026-12-10", TITLE_DATE):
            report.fail("link", f"show_config title_card date unexpected: {card}")
        else:
            report.note(
                "show_config release date ok; film card text locked to CANON "
                f"'{TITLE_TEXT}'"
            )


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers: list[dict[str, Any]] = []
    for b in data.get("ending_beats") or []:
        markers.append(
            {
                "name": b["marker"],
                "frame": b["frame"],
                "who": b.get("who"),
                "action": b.get("action"),
                "note": b.get("staging"),
                "final_story_image": bool(b.get("final_story_image")),
                "final_film_image": bool(b.get("final_film_image")),
                "creative_contribution": bool(b.get("creative_contribution")),
            }
        )
    audio = (data.get("audio_layering") or {}).get("layering") or {}
    am = audio.get("markers") or {}
    for key, name_key, frame_key in (
        ("overlap", "overlap_start", "overlap_start_frame"),
        ("living", "living_carries", "living_carries_frame"),
        ("recording", "recording_imperfect_end", "recording_imperfect_end_frame"),
    ):
        name = am.get(name_key)
        frame = am.get(frame_key)
        if name and frame is not None:
            markers.append(
                {
                    "name": name,
                    "frame": frame,
                    "kind": "audio_layer",
                    "note": key,
                }
            )
    out = {
        "schema_version": 1,
        "scene": data["scene"],
        "editable": True,
        "final_story_image": "open doorway",
        "final_film_image": {
            "text": TITLE_TEXT,
            "date": TITLE_DATE,
            "prompt": "Prompt 22",
        },
        "true_transformation": "memory becoming participation",
        "markers": sorted(markers, key=lambda m: int(m["frame"])),
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/final_meal_markers.json")
    return MARKERS_JSON


def write_status(data: dict[str, Any], report: RunReport) -> Path:
    policy = data["policy"]
    dion = data["dionysian_transformation"]
    audio = data["audio_layering"]
    lines = [
        "# Final meal — SCN_09_FINAL_MEAL",
        "",
        f"**Throughline:** {data.get('throughline')}  ",
        f"**Animatic:** "
        + ", ".join(f"`{s}`" for s in (data.get("approx_animatic_shots") or [])),
        "",
        f"**True transformation:** {policy.get('true_transformation')}  ",
        f"**Final story image:** {policy.get('final_story_image')}  ",
        f"**Final film image:** {policy.get('final_film_image')} — "
        f"**{policy.get('title_card_text')}** / **{policy.get('title_card_date')}**",
        "",
        "## Hard rules",
        "",
        f"- Sister is symbolic child: `{policy.get('sister_is_symbolic_child')}`",
        f"- Sister has own rhythm: `{policy.get('sister_has_own_rhythm')}`",
        f"- Changed note is real creative contribution: "
        f"`{policy.get('changed_note_is_real_creative_contribution')}`",
        f"- Literal magic-trick ending: `{policy.get('literal_magic_trick_ending')}`",
        "",
        "## Composition mirror (opening → ending)",
        "",
        "| Opening | Ending |",
        "|---------|--------|",
    ]
    for m in data.get("composition_mirror") or []:
        lines.append(f"| {m['opening']} | {m['ending']} |")
    lines += ["", "## Ending beats", "", "| Frame | Marker | Who | Action |", "|-------|--------|-----|--------|"]
    for b in data.get("ending_beats") or []:
        tag = ""
        if b.get("final_story_image"):
            tag = " (story final)"
        elif b.get("final_film_image"):
            tag = " (film final)"
        elif b.get("creative_contribution"):
            tag = " (creative)"
        lines.append(
            f"| {b['frame']} | `{b['marker']}`{tag} | {b['who']} | {b['action']} |"
        )
    lines += [
        "",
        "## Audio layering",
        "",
        f"- Original recording audible to imperfect end: "
        f"`{(audio.get('original_recording') or {}).get('audible')}`",
        f"- {(audio.get('layering') or {}).get('staging')}",
        "",
        "## Dionysian transformation (subtle)",
        "",
        f"- True transformation: {dion.get('true_transformation')}",
        f"- Literal magic trick: `{dion.get('literal_magic_trick')}`",
        f"- May briefly resemble wine: "
        + ", ".join(dion.get("may_briefly_resemble_wine") or []),
        f"- Staging: {dion.get('staging')}",
        "",
        "## Must preserve",
        "",
    ]
    for item in data.get("must_preserve") or []:
        lines.append(f"- {item}")
    lines += ["", "## Must not", ""]
    for item in data.get("must_not") or []:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Rebuild",
        "",
        "```text",
        "python scripts/animate_final_meal.py",
        "python scripts/animate_final_meal.py --check-links",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/final_meal_animation.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Animate final meal / ending")
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Cross-check call motif, animatic, holy-fool order, CANON title card",
    )
    args = parser.parse_args()

    report = RunReport(script="animate_final_meal", seed=20261210)
    try:
        data = load_fm()
        report.mark("reused", "docs/final_meal_animation.json")
    except Exception as exc:  # noqa: BLE001
        report.fail("brief", exc)
        report.write(REPORTS_DIR)
        return 1

    errors = validate(data)
    for e in errors:
        report.fail("validate", e)
    if errors:
        report.write(REPORTS_DIR)
        return 1

    write_markers(data, report)
    write_status(data, report)
    if args.check_links:
        check_links(data, report)

    report.note(
        "Final meal mirrors opening; sister owns changed note; "
        "doorway=story final; Prompt 22 title card=film final"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} scene={data['scene']} "
        f"mirrors={len(data['composition_mirror'])} "
        f"ending_beats={len(data['ending_beats'])} "
        f"title={data['policy']['title_card_text']}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
