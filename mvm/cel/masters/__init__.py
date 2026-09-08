"""Masters rule packs — operational animation thinking, not scraped frames."""

from __future__ import annotations

import json
from pathlib import Path

from mvm.schemas.models import StylePack

STYLES_DIR = Path(__file__).resolve().parents[3] / "styles"
MASTERS_DIR = Path(__file__).resolve().parent


def load_style_pack(pack_id: str) -> StylePack:
    path = STYLES_DIR / f"{pack_id}.json"
    if not path.exists():
        path = STYLES_DIR / "classic_cel.json"
    return StylePack.model_validate_json(path.read_text(encoding="utf-8"))


def list_style_packs() -> list[str]:
    if not STYLES_DIR.exists():
        return []
    return sorted(p.stem for p in STYLES_DIR.glob("*.json"))


def load_masters_rules(pack_id: str) -> dict:
    path = MASTERS_DIR / f"{pack_id}.json"
    if not path.exists():
        path = MASTERS_DIR / "classic_cel.json"
    return json.loads(path.read_text(encoding="utf-8"))


def pick_cel_mode(section_name: str, energy: float, pack: StylePack) -> str:
    rules = load_masters_rules(pack.id)
    section_modes = rules.get("section_modes", {})
    if section_name in section_modes:
        return section_modes[section_name]
    if energy >= rules.get("full_energy_threshold", 0.8):
        return "full"
    if energy <= rules.get("hold_energy_threshold", 0.35):
        return "held_atmosphere"
    return rules.get("default_mode", "limited")


def exposure_for_mode(mode: str, pack: StylePack) -> str:
    rules = load_masters_rules(pack.id)
    return rules.get("exposure_by_mode", {}).get(mode, pack.default_exposure)
