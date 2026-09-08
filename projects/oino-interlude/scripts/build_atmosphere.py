"""Build Oino atmosphere effects — preview/final, switchable, seeded.

Effects stay sparse. Dionysian atmosphere = life breaking through rigid systems.
Do not cover weak staging with fog, glitches, CA, flares, or constant particles.

Usage:
  python scripts/build_atmosphere.py
  python scripts/build_atmosphere.py --enable ATM_WHITE_BIRD_RELEASE
  python scripts/build_atmosphere.py --disable ATM_RESTRAINED_RAIN
  python scripts/build_atmosphere.py --shot SH080_WARM_TWO_SHOT --enable ATM_CONDENSATION
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import RunReport  # noqa: E402
from project_paths import DOCS_DIR, REPORTS_DIR  # noqa: E402
from show_config import load_show_config  # noqa: E402

ATMO_JSON = DOCS_DIR / "atmosphere.json"
SWITCHES_JSON = DOCS_DIR / "atmosphere_switches.json"
MARKERS_JSON = DOCS_DIR / "atmosphere_markers.json"
STATUS_MD = DOCS_DIR / "atmosphere.md"
SEED_TABLE_JSON = DOCS_DIR / "atmosphere_seed_table.json"

REQUIRED_EFFECT_LABELS = (
    "attic dust",
    "steam haze",
    "electrical smoke",
    "screen glow",
    "shallow water",
    "condensation",
    "restrained rain",
    "film grain",
    "gate weave",
    "vine growth",
    "white bird or dove-like release forms",
)

REQUIRED_TRANSITION_LABELS = (
    "dust to steam",
    "steam to electric glow",
    "electric glow to screen reflection",
    "screen reflection to water",
    "water reflection to table surface",
    "table surface to title-card black",
)

FORBIDDEN_POLICY = (
    "cover_weak_staging_with_fog",
    "cover_with_glitches",
    "cover_with_chromatic_aberration",
    "cover_with_lens_flares",
    "cover_with_constant_particles",
)


def load() -> dict[str, Any]:
    if not ATMO_JSON.is_file():
        raise FileNotFoundError(f"Missing {ATMO_JSON}")
    return json.loads(ATMO_JSON.read_text(encoding="utf-8"))


def load_switches() -> dict[str, Any]:
    if SWITCHES_JSON.is_file():
        return json.loads(SWITCHES_JSON.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "global": {},
        "per_scene": {},
        "per_shot": {},
    }


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = data.get("policy") or {}
    for key in FORBIDDEN_POLICY:
        if policy.get(key) is not False:
            errors.append(f"policy.{key} must be false")
    if policy.get("switchable_per_scene") is not True:
        errors.append("policy.switchable_per_scene must be true")
    if policy.get("switchable_per_shot") is not True:
        errors.append("policy.switchable_per_shot must be true")
    if policy.get("seeded_randomness") is not True:
        errors.append("policy.seeded_randomness must be true")
    role = (policy.get("dionysian_role") or "").lower()
    if "life" not in role or "rigid" not in role:
        errors.append("policy.dionysian_role must describe life breaking through rigid systems")

    versions = data.get("versions") or {}
    for ver in ("preview", "final"):
        if ver not in versions:
            errors.append(f"versions.{ver} required")

    effects = data.get("effects") or []
    labels = [(e.get("label") or "").strip() for e in effects]
    ids = [e.get("id") for e in effects]
    if len(ids) != len(set(ids)):
        errors.append("effect ids must be unique")
    for req in REQUIRED_EFFECT_LABELS:
        if req not in labels:
            errors.append(f"Missing effect: {req}")
    if len(effects) != len(REQUIRED_EFFECT_LABELS):
        errors.append(
            f"Expected exactly {len(REQUIRED_EFFECT_LABELS)} effects, found {len(effects)}"
        )

    for e in effects:
        eid = e.get("id", "?")
        if e.get("switchable") is not True:
            errors.append(f"{eid}: switchable must be true")
        if "seed_channel" not in e:
            errors.append(f"{eid}: seed_channel required")
        for ver in ("preview", "final"):
            block = e.get(ver) or {}
            if "density" not in block:
                errors.append(f"{eid}.{ver}.density required")
        if not e.get("must_not"):
            errors.append(f"{eid}: must_not required")

    transitions = data.get("transitions") or []
    tlabels = [(t.get("label") or "").strip() for t in transitions]
    for req in REQUIRED_TRANSITION_LABELS:
        if req not in tlabels:
            errors.append(f"Missing transition: {req}")
    if len(transitions) != len(REQUIRED_TRANSITION_LABELS):
        errors.append(
            f"Expected exactly {len(REQUIRED_TRANSITION_LABELS)} transitions, "
            f"found {len(transitions)}"
        )
    effect_ids = set(ids)
    for t in transitions:
        tid = t.get("id", "?")
        for key in ("from_effect", "to_effect"):
            val = t.get(key)
            if val is not None and val not in effect_ids:
                # allow null when using surfaces
                if val:
                    errors.append(f"{tid}: unknown {key} {val}")
        if not (t.get("staging") or "").strip():
            errors.append(f"{tid}: staging required")

    crutches = data.get("forbidden_crutches") or []
    for need in (
        "fog_to_hide_blocking",
        "glitch_overlay_as_drama",
        "chromatic_aberration_as_style_default",
        "lens_flare_spectacle",
        "constant_particle_fields",
    ):
        if need not in crutches:
            errors.append(f"forbidden_crutches must include {need}")

    dion = data.get("dionysian_breaking_through") or []
    if len(dion) < 4:
        errors.append("Need at least four Dionysian breaking-through images")
    blob = " ".join(
        (d.get("image") or "") for d in dion
    ).lower()
    for needle in ("vine", "laugh", "synchron", "flock"):
        if needle not in blob:
            errors.append(f"dionysian_breaking_through should include '{needle}'")

    return errors


def resolve_seed(data: dict[str, Any]) -> int:
    cfg = load_show_config()
    seeds = cfg.get("seeds") or {}
    if "fx" in seeds:
        return int(seeds["fx"])
    return int(data.get("seed") or 20261214)


def build_seed_table(data: dict[str, Any], master_seed: int) -> dict[str, Any]:
    table: dict[str, Any] = {"master_seed": master_seed, "effects": {}, "transitions": {}}
    for e in data.get("effects") or []:
        ch = int(e["seed_channel"])
        rng = random.Random(master_seed + ch * 9973)
        table["effects"][e["id"]] = {
            "seed": master_seed + ch * 9973,
            "jitter": round(rng.random() * 0.08, 5),
            "phase": round(rng.random(), 5),
        }
    for t in data.get("transitions") or []:
        ch = int(t["seed_channel"])
        rng = random.Random(master_seed + ch * 9973)
        table["transitions"][t["id"]] = {
            "seed": master_seed + ch * 9973,
            "blend_curve": round(0.35 + rng.random() * 0.3, 5),
        }
    return table


def apply_cli_switches(
    switches: dict[str, Any],
    *,
    enable: list[str],
    disable: list[str],
    scene: str | None,
    shot: str | None,
) -> dict[str, Any]:
    if scene and shot:
        raise ValueError("Pass only one of --scene or --shot")
    target: dict[str, Any]
    if shot:
        target = switches.setdefault("per_shot", {}).setdefault(shot, {})
    elif scene:
        target = switches.setdefault("per_scene", {}).setdefault(scene, {})
    else:
        target = switches.setdefault("global", {})
    for eid in enable:
        target[eid] = True
    for eid in disable:
        target[eid] = False
    return switches


def effect_enabled(
    effect: dict[str, Any],
    switches: dict[str, Any],
    *,
    scene: str | None = None,
    shot: str | None = None,
) -> bool:
    eid = effect["id"]
    # Precedence: shot > scene > global > default_enabled
    if shot:
        shot_map = (switches.get("per_shot") or {}).get(shot) or {}
        if eid in shot_map:
            return bool(shot_map[eid])
    if scene:
        scene_map = (switches.get("per_scene") or {}).get(scene) or {}
        if eid in scene_map:
            return bool(scene_map[eid])
        # Also check scene_defaults membership as soft default when no override
    glob = switches.get("global") or {}
    if eid in glob:
        return bool(glob[eid])
    return bool(effect.get("default_enabled"))


def write_switches(switches: dict[str, Any], report: RunReport) -> Path:
    switches["schema_version"] = 1
    switches["editable"] = True
    switches["precedence"] = ["per_shot", "per_scene", "global", "default_enabled"]
    SWITCHES_JSON.write_text(json.dumps(switches, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/atmosphere_switches.json")
    return SWITCHES_JSON


def write_markers(data: dict[str, Any], report: RunReport) -> Path:
    markers = []
    for e in data.get("effects") or []:
        markers.append(
            {
                "name": e["id"],
                "label": e["label"],
                "category": e.get("category"),
                "dionysian": bool(e.get("dionysian")),
                "default_enabled": bool(e.get("default_enabled")),
                "shots": e.get("shots") or [],
                "scenes": e.get("scenes") or [],
            }
        )
    for t in data.get("transitions") or []:
        markers.append(
            {
                "name": t["id"],
                "label": t["label"],
                "kind": "transition",
                "from_effect": t.get("from_effect"),
                "to_effect": t.get("to_effect"),
                "approx_shots": t.get("approx_shots") or [],
            }
        )
    out = {
        "schema_version": 1,
        "system_id": data.get("system_id"),
        "seed": data.get("seed"),
        "markers": markers,
    }
    MARKERS_JSON.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/atmosphere_markers.json")
    return MARKERS_JSON


def write_status(
    data: dict[str, Any],
    switches: dict[str, Any],
    seed_table: dict[str, Any],
    report: RunReport,
) -> Path:
    policy = data["policy"]
    lines = [
        "# Atmosphere — Oino (Interlude)",
        "",
        f"**System:** `{data.get('system_id')}`  ",
        f"**Master seed:** `{seed_table.get('master_seed')}`  ",
        f"**Dionysian role:** {policy.get('dionysian_role')}",
        "",
        "## Hard rules",
        "",
        f"- Cover weak staging with fog: `{policy.get('cover_weak_staging_with_fog')}`",
        f"- Glitches / CA / flares / constant particles: "
        f"`{policy.get('cover_with_glitches')}` / "
        f"`{policy.get('cover_with_chromatic_aberration')}` / "
        f"`{policy.get('cover_with_lens_flares')}` / "
        f"`{policy.get('cover_with_constant_particles')}`",
        f"- Switchable per scene / shot: `{policy.get('switchable_per_scene')}` / "
        f"`{policy.get('switchable_per_shot')}`",
        f"- Seeded randomness: `{policy.get('seeded_randomness')}`",
        "",
        "## Versions",
        "",
    ]
    for ver, block in (data.get("versions") or {}).items():
        lines.append(
            f"- **{ver}** (`{block.get('id')}`): density×{block.get('density_scale')}, "
            f"budget `{block.get('particle_budget')}`, grain {block.get('grain_strength')} — "
            f"{block.get('note')}"
        )
    lines += ["", "## Effects", "", "| Id | Label | Default | Preview dens. | Final dens. | Dionysian |", "|----|-------|---------|---------------|-------------|-----------|"]
    for e in data.get("effects") or []:
        en = effect_enabled(e, switches)
        lines.append(
            f"| `{e['id']}` | {e['label']} | "
            f"{'on' if e.get('default_enabled') else 'off'} "
            f"(resolved **{'on' if en else 'off'}**) | "
            f"{(e.get('preview') or {}).get('density')} | "
            f"{(e.get('final') or {}).get('density')} | "
            f"{'yes' if e.get('dionysian') else 'no'} |"
        )
    lines += ["", "## Transitions", ""]
    for t in data.get("transitions") or []:
        lines += [
            f"### {t['label']}",
            "",
            f"- **Id:** `{t['id']}`",
            f"- **From → to:** `{t.get('from_effect') or t.get('from_surface')}` → "
            f"`{t.get('to_effect') or t.get('to_surface')}`",
            f"- **Shots:** " + ", ".join(f"`{s}`" for s in (t.get("approx_shots") or [])),
            f"- **Staging:** {t.get('staging')}",
            "",
        ]
    lines += ["## Dionysian — life through rigid systems", ""]
    for d in data.get("dionysian_breaking_through") or []:
        lines.append(
            f"- {d.get('image')} (`{d.get('id')}`)"
            + (f" → `{d.get('link_effect')}`" if d.get("link_effect") else "")
        )
    lines += [
        "",
        "## Scene defaults",
        "",
    ]
    for scene, fx in (data.get("scene_defaults") or {}).items():
        lines.append(f"- `{scene}`: " + (", ".join(f"`{x}`" for x in fx) if fx else "—"))
    lines += [
        "",
        "## Switches",
        "",
        f"Editable: [`atmosphere_switches.json`](atmosphere_switches.json)  ",
        "Precedence: per_shot > per_scene > global > default_enabled",
        "",
        "```text",
        "python scripts/build_atmosphere.py",
        "python scripts/build_atmosphere.py --enable ATM_WHITE_BIRD_RELEASE",
        "python scripts/build_atmosphere.py --shot SH110_RELEASE_CONTROL --enable ATM_WHITE_BIRD_RELEASE",
        "python scripts/build_atmosphere.py --scene SCN_07_ZONE --disable ATM_RESTRAINED_RAIN",
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.mark("created", "docs/atmosphere.md")
    return STATUS_MD


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Oino atmosphere system")
    parser.add_argument("--enable", nargs="*", default=[], help="Enable effect ids")
    parser.add_argument("--disable", nargs="*", default=[], help="Disable effect ids")
    parser.add_argument("--scene", type=str, default=None, help="Scope enable/disable to scene")
    parser.add_argument("--shot", type=str, default=None, help="Scope enable/disable to shot")
    args = parser.parse_args()

    report = RunReport(script="build_atmosphere", seed=20261214)
    try:
        data = load()
        report.mark("reused", "docs/atmosphere.json")
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

    master_seed = resolve_seed(data)
    data["seed"] = master_seed
    report.note(f"atmosphere seed={master_seed}")

    switches = load_switches()
    known = {e["id"] for e in data["effects"]}
    for eid in list(args.enable) + list(args.disable):
        if eid not in known:
            report.fail("switch", f"Unknown effect id: {eid}")
    if not report.ok:
        report.write(REPORTS_DIR)
        return 1

    if args.enable or args.disable:
        try:
            switches = apply_cli_switches(
                switches,
                enable=list(args.enable or []),
                disable=list(args.disable or []),
                scene=args.scene,
                shot=args.shot,
            )
        except ValueError as exc:
            report.fail("switch", exc)
            report.write(REPORTS_DIR)
            return 1

    seed_table = build_seed_table(data, master_seed)
    SEED_TABLE_JSON.write_text(json.dumps(seed_table, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/atmosphere_seed_table.json")

    write_switches(switches, report)
    write_markers(data, report)
    write_status(data, switches, seed_table, report)

    # Persist seed onto atmosphere.json if changed from show_config
    ATMO_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    report.mark("created", "docs/atmosphere.json")

    report.note(
        "11 effects × preview/final; 6 transitions; switchable; "
        "no fog/glitch/CA/flare/constant-particle crutches"
    )
    report.write(REPORTS_DIR)
    print(
        f"SUMMARY ok={report.ok} effects={len(data['effects'])} "
        f"transitions={len(data['transitions'])} seed={master_seed}"
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
