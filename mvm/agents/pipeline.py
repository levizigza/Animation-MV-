"""Creative agents — AutoMV-shaped, craft-first (no generative video)."""

from __future__ import annotations

import re
from typing import Any

from mvm.cel.masters import (
    exposure_for_mode,
    load_style_pack,
    pick_cel_mode,
)
from mvm.cel.xsheet import build_xsheet_for_shot
from mvm.schemas.models import (
    ApprovalState,
    Beatmap,
    CelPolicy,
    Character,
    Shot,
    ShotIntent,
    Story,
    XSheet,
)


def _tokenize_prompt(prompt: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-']+", prompt.lower())
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "with", "for",
        "from", "into", "like", "as", "by", "at", "is", "are", "be", "this",
    }
    return [w for w in words if w not in stop and len(w) > 2]


def music_analyst(prompt: str, beatmap: Beatmap, style_pack: str) -> dict[str, Any]:
    tokens = _tokenize_prompt(prompt)
    avg_energy = (
        sum(s.energy for s in beatmap.sections) / max(1, len(beatmap.sections))
    )
    if avg_energy > 0.7:
        temp = "ferocious"
    elif avg_energy > 0.45:
        temp = "warm_kinetic"
    else:
        temp = "quiet_luminous"

    moods = []
    mood_map = {
        "love": "tender",
        "night": "nocturne",
        "city": "urban",
        "rain": "melancholy",
        "fire": "volatile",
        "dream": "surreal",
        "war": "brutal",
        "ocean": "tidal",
        "space": "cosmic",
    }
    for t, m in mood_map.items():
        if t in tokens:
            moods.append(m)
    if not moods:
        moods = ["cinematic"]

    return {
        "visual_temperature": temp,
        "moods": moods,
        "bpm": beatmap.bpm,
        "duration": beatmap.duration,
        "motif_seeds": tokens[:8],
        "style_pack": style_pack,
        "section_energies": {s.name: s.energy for s in beatmap.sections},
    }


def screenwriter(prompt: str, analysis: dict[str, Any], style_pack: str) -> Story:
    seeds = analysis.get("motif_seeds", [])
    title_bits = [s.title() for s in seeds[:3]] or ["Untitled Pulse"]
    title = " ".join(title_bits)

    protagonist = Character(
        id="lead",
        name="Lead",
        description=f"Central figure shaped by: {prompt[:160]}",
        color_keys=["#1a1a1a", "#f2e9e0", "#c45c26"],
        line_weight="medium",
        model_sheet_notes="Clear silhouette; consistent head-to-body ratio across shots.",
    )
    shadow = Character(
        id="shadow",
        name="Shadow Self",
        description="Motivic double — appears on bridges and low-energy holds.",
        color_keys=["#0d0d12", "#4a5568"],
        line_weight="thin",
        model_sheet_notes="More graphic; fewer midtones.",
    )

    arc = []
    for sec, energy in analysis.get("section_energies", {}).items():
        if sec == "intro":
            arc.append("Establish world and silence before the pulse.")
        elif sec == "verse":
            arc.append("Character walks the motif; small gestures carry story.")
        elif sec == "prechorus":
            arc.append("Tension coils; anticipation poses.")
        elif sec == "chorus":
            arc.append("Full emotional release; bold keys and smears.")
        elif sec == "bridge":
            arc.append("Interior turn; held atmosphere and shadow motif.")
        else:
            arc.append("Resolve or dissolve; lingering hold.")

    return Story(
        title=title,
        prompt=prompt,
        logline=f"A {analysis['visual_temperature']} visual poem: {prompt[:120]}",
        themes=analysis.get("moods", []) + seeds[:4],
        visual_temperature=analysis["visual_temperature"],
        narrative_arc=arc,
        characters=[protagonist, shadow],
        motif_recurrence=seeds[:5],
        style_pack=style_pack,
        approval=ApprovalState.PENDING_REVIEW,
    )


def director(story: Story, beatmap: Beatmap, style_pack: str) -> list[Shot]:
    pack = load_style_pack(style_pack)
    shots: list[Shot] = []
    for i, section in enumerate(beatmap.sections):
        duration = max(0.5, section.end - section.start)
        mode = pick_cel_mode(section.name, section.energy, pack)
        exposure = exposure_for_mode(mode, pack)
        smear = pack.smear_bias * (0.4 + 0.6 * section.energy)

        cam = {
            "type": pack.camera_grammar.get("move_style", "motivated"),
            "start": {"loc": [0, -6, 1.6], "rot_deg": [75, 0, 0]},
            "end": {"loc": [0, -5.2, 1.7], "rot_deg": [78, 0, 0]},
        }
        if section.name == "chorus":
            cam["type"] = "push_in"
            cam["end"]["loc"] = [0, -4.0, 1.5]
        elif section.name in ("bridge", "outro"):
            cam["type"] = "slow_pull"
            cam["end"]["loc"] = [0, -7.0, 1.8]

        desc = _shot_description(story, section.name)
        priority = {
            "full": "impact",
            "limited": "performance",
            "held_atmosphere": "atmosphere",
        }.get(mode, "performance")
        shot = Shot(
            id=f"shot_{i+1:03d}_{section.name}",
            index=i + 1,
            section=section.name,
            start=section.start,
            end=section.end,
            duration=duration,
            intent=ShotIntent(
                purpose=desc,
                emotional_beat=section.name,
                staging_goal="Lead staged center; Shadow motif on periphery for bridge.",
                animation_priority=priority,  # type: ignore[arg-type]
                hold_for_lyric=section.name in ("verse", "bridge"),
                notes=f"Heuristic director; energy={section.energy:.2f}",
            ),
            description=desc,
            camera=cam,
            blocking="Lead staged center; Shadow motif on periphery for bridge.",
            lens_mm=24.0 if section.name == "intro" else (50.0 if section.name == "chorus" else 35.0),
            cel=CelPolicy(
                mode=mode,  # type: ignore[arg-type]
                exposure=exposure,  # type: ignore[arg-type]
                hold_on_lyrics=True,
                smear_on_accents=smear > 0.3,
                smear_density=min(1.0, smear),
                masters_pack=pack.id,
                key_on_beats=True,
                fx_vocab=["smear", "impact"] if section.name == "chorus" else ["smear"],
            ),
            characters=["lead"] + (["shadow"] if section.name in ("bridge", "outro") else []),
            color_script=pack.color_guidance.get("palette", "ink_and_paint"),
            approval=ApprovalState.PENDING_REVIEW,
            notes=f"Energy={section.energy:.2f}; pack={pack.id}",
        )
        shots.append(shot)
    return shots


def _shot_description(story: Story, section: str) -> str:
    motifs = ", ".join(story.motif_recurrence[:3]) or "the pulse"
    mapping = {
        "intro": f"Wide establish; world breathes before {motifs}.",
        "verse": f"Lead carries {motifs} through understated performance.",
        "prechorus": f"Coiling anticipation; eyes and hands lead into release.",
        "chorus": f"Full cel intensity on {motifs}; smear accents on hits.",
        "bridge": "Interior quiet; Shadow Self and held atmosphere.",
        "outro": "Dissolve to hold; lingering silhouette.",
    }
    return mapping.get(section, f"Section {section}: develop {motifs}.")


def animation_director(shots: list[Shot], beatmap: Beatmap, fps: int) -> list[XSheet]:
    return [build_xsheet_for_shot(shot, beatmap, fps=fps) for shot in shots]


def verifier(
    story: Story,
    shots: list[Shot],
    xsheets: list[XSheet],
    beatmap: Beatmap,
) -> dict[str, Any]:
    issues: list[str] = []
    if not story.characters:
        issues.append("No characters in story.")
    if not shots:
        issues.append("No shots planned.")

    for shot in shots:
        if shot.end <= shot.start:
            issues.append(f"{shot.id}: invalid time range.")
        if abs((shot.end - shot.start) - shot.duration) > 0.05:
            issues.append(f"{shot.id}: duration mismatch.")

    xs_by_id = {x.shot_id: x for x in xsheets}
    for shot in shots:
        xs = xs_by_id.get(shot.id)
        if not xs:
            issues.append(f"{shot.id}: missing X-sheet.")
            continue
        keys = [c for c in xs.cells if c.layer == "character" and c.exposure == "key"]
        if len(keys) < 2:
            issues.append(f"{shot.id}: fewer than 2 character keys.")
        # Beat alignment: at least one key near a beat in shot
        beat_in = [t for t in beatmap.beat_times if shot.start <= t < shot.end]
        if beat_in and shot.cel.key_on_beats and len(keys) < 2:
            issues.append(f"{shot.id}: weak beat-keyed craft.")

    ok = len(issues) == 0
    return {"ok": ok, "issues": issues, "shot_count": len(shots), "xsheet_count": len(xsheets)}


def run_planning_pipeline(
    prompt: str,
    beatmap: Beatmap,
    style_pack: str = "classic_cel",
    fps: int = 24,
) -> dict[str, Any]:
    analysis = music_analyst(prompt, beatmap, style_pack)
    story = screenwriter(prompt, analysis, style_pack)
    shots = director(story, beatmap, style_pack)
    xsheets = animation_director(shots, beatmap, fps)
    report = verifier(story, shots, xsheets, beatmap)
    # MIR soft proposals grounded symbolically (suggestions only; not auto-applied)
    from mvm.neurosymbolic.bridge import proposals_from_music_analysis
    from mvm.neurosymbolic.grounding import ground_proposal
    from mvm.neurosymbolic.schemas import GroundingStatus
    from mvm.neurosymbolic.symbolic import build_symbolic_state

    mir_proposals = proposals_from_music_analysis(
        beatmap=beatmap, shots=shots, style_pack=style_pack
    )
    energy_by_section = {s.name: s.energy for s in beatmap.sections}
    ns_decisions: list[dict[str, Any]] = []
    for prop in mir_proposals:
        sid = str(prop.payload.get("shot_id") or "")
        shot = next((s for s in shots if s.id == sid), None)
        if shot is None:
            continue
        state = build_symbolic_state(
            shot=shot,
            style_pack=style_pack,
            section_energy=energy_by_section.get(shot.section),
        )
        grounding = ground_proposal(state, prop)
        ns_decisions.append(
            {
                "proposal": prop.model_dump(mode="json"),
                "grounding": grounding.model_dump(mode="json"),
                "applied": False,
                "layers": {
                    "neuro": prop.source.value,
                    "symbolic": grounding.status.value,
                },
            }
        )
    return {
        "analysis": analysis,
        "story": story,
        "shots": shots,
        "xsheets": xsheets,
        "verification": report,
        "neurosymbolic": {
            "decisions": ns_decisions,
            "summary": {
                "total": len(ns_decisions),
                "accepted": sum(
                    1
                    for d in ns_decisions
                    if d["grounding"]["status"] == GroundingStatus.ACCEPTED.value
                ),
                "blocked": sum(
                    1
                    for d in ns_decisions
                    if d["grounding"]["status"] == GroundingStatus.BLOCKED.value
                ),
                "needs_human": sum(
                    1
                    for d in ns_decisions
                    if d["grounding"]["status"] == GroundingStatus.NEEDS_HUMAN.value
                ),
                "applied": False,
                "layers": {"neuro": "proposal", "symbolic": "grounding"},
            },
        },
    }
