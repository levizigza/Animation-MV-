# Atmosphere — Oino (Interlude)

**System:** `OINO_ATMOSPHERE`  
**Master seed:** `20261214`  
**Dionysian role:** life breaking through rigid systems

## Hard rules

- Cover weak staging with fog: `False`
- Glitches / CA / flares / constant particles: `False` / `False` / `False` / `False`
- Switchable per scene / shot: `True` / `True`
- Seeded randomness: `True`

## Versions

- **preview** (`ATM_PREVIEW`): density×0.55, budget `low`, grain 0.25 — Readable atmosphere for animatic / layout approval
- **final** (`ATM_FINAL`): density×1.0, budget `crafted`, grain 0.4 — Full craft pass — still sparse; never constant particle rain

## Effects

| Id | Label | Default | Preview dens. | Final dens. | Dionysian |
|----|-------|---------|---------------|-------------|-----------|
| `ATM_ATTIC_DUST` | attic dust | on (resolved **on**) | 0.2 | 0.35 | no |
| `ATM_STEAM_HAZE` | steam haze | on (resolved **on**) | 0.25 | 0.45 | no |
| `ATM_ELECTRICAL_SMOKE` | electrical smoke | off (resolved **off**) | 0.15 | 0.3 | no |
| `ATM_SCREEN_GLOW` | screen glow | on (resolved **on**) | 0.3 | 0.5 | no |
| `ATM_SHALLOW_WATER` | shallow water | on (resolved **on**) | 0.4 | 0.7 | no |
| `ATM_CONDENSATION` | condensation | off (resolved **off**) | 0.2 | 0.4 | no |
| `ATM_RESTRAINED_RAIN` | restrained rain | off (resolved **off**) | 0.1 | 0.22 | no |
| `ATM_FILM_GRAIN` | film grain | on (resolved **on**) | 0.2 | 0.4 | no |
| `ATM_GATE_WEAVE` | gate weave | on (resolved **on**) | 0.25 | 0.45 | no |
| `ATM_VINE_GROWTH` | vine growth | on (resolved **on**) | 0.3 | 0.55 | yes |
| `ATM_WHITE_BIRD_RELEASE` | white bird or dove-like release forms | off (resolved **off**) | 0.35 | 0.6 | yes |

## Transitions

### dust to steam

- **Id:** `TR_DUST_TO_STEAM`
- **From → to:** `ATM_ATTIC_DUST` → `ATM_STEAM_HAZE`
- **Shots:** `SH030_ARCHIVE_DISCOVERY`, `SH040_MELODY_OPENS_HISTORY`
- **Staging:** Archive air thickens into labour steam — same world changing.

### steam to electric glow

- **Id:** `TR_STEAM_TO_ELECTRIC`
- **From → to:** `ATM_STEAM_HAZE` → `ATM_ELECTRICAL_SMOKE`
- **Shots:** `SH050_CHANGING_WORLD`, `SH051_ELECTRIC_HOUSEHOLD_TIME`
- **Staging:** Warm soot yields to tungsten / porcelain light; smoke thinner, cleaner.

### electric glow to screen reflection

- **Id:** `TR_ELECTRIC_TO_SCREEN`
- **From → to:** `ATM_ELECTRICAL_SMOKE` → `ATM_SCREEN_GLOW`
- **Shots:** `SH060_CARE_AND_HARM`, `SH061_OINO_SEES_OWN_RECORDING`
- **Staging:** Practical glow flattens into glass; Oino can watch herself.

### screen reflection to water

- **Id:** `TR_SCREEN_TO_WATER`
- **From → to:** `ATM_SCREEN_GLOW` → `ATM_SHALLOW_WATER`
- **Shots:** `SH070_ZONE_PASSAGE`
- **Staging:** Hard reflection softens into shallow water — Zone unresolved.

### water reflection to table surface

- **Id:** `TR_WATER_TO_TABLE`
- **From → to:** `ATM_SHALLOW_WATER` → `table_surface`
- **Shots:** `SH070_TABLE_GLIMPSE`, `SH080_WARM_TWO_SHOT`
- **Staging:** Ripple becomes worn wood / bowl reflection; warmth replaces passage chill.

### table surface to title-card black

- **Id:** `TR_TABLE_TO_TITLE_BLACK`
- **From → to:** `table_surface` → `title_card_black`
- **Shots:** `SH122_OPEN_DOORWAY`, `SH130_TITLE_CARD`
- **Staging:** Open doorway hold settles; fade to quiet near-black — no flare, no glitch.

## Dionysian — life through rigid systems

- a vine through iron (`DION_ATM_VINE_THROUGH_IRON`) → `ATM_VINE_GROWTH`
- a human laugh inside a machine rhythm (`DION_ATM_LAUGH_IN_MACHINE`)
- a body moving against synchronization (`DION_ATM_BODY_AGAINST_SYNC`)
- a flock briefly released from an industrial ceiling (`DION_ATM_FLOCK_RELEASE`) → `ATM_WHITE_BIRD_RELEASE`

## Scene defaults

- `SCN_02_OINO_ARCHIVE`: `ATM_ATTIC_DUST`, `ATM_FILM_GRAIN`
- `SCN_MODULAR_INDUSTRIAL_WORLD`: `ATM_STEAM_HAZE`, `ATM_GATE_WEAVE`, `ATM_VINE_GROWTH`
- `SCN_07_ZONE`: `ATM_SHALLOW_WATER`, `ATM_CONDENSATION`, `ATM_VINE_GROWTH`
- `SCN_08_TABLE_ROOM`: `ATM_CONDENSATION`, `ATM_VINE_GROWTH`
- `SCN_09_FINAL_MEAL`: —
- `SCN_13_TITLE_CARD`: `ATM_FILM_GRAIN`

## Switches

Editable: [`atmosphere_switches.json`](atmosphere_switches.json)  
Precedence: per_shot > per_scene > global > default_enabled

```text
python scripts/build_atmosphere.py
python scripts/build_atmosphere.py --enable ATM_WHITE_BIRD_RELEASE
python scripts/build_atmosphere.py --shot SH110_RELEASE_CONTROL --enable ATM_WHITE_BIRD_RELEASE
python scripts/build_atmosphere.py --scene SCN_07_ZONE --disable ATM_RESTRAINED_RAIN
```

