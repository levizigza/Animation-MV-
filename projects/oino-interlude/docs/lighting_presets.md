# Lighting presets — Oino (Interlude)

**System:** `OINO_LIGHTING_PRESETS`  
**Dionysian role:** living interruption inside systems of grey, black, and industrial blue  
**Every shot red:** `False`

## Palette families

### attic

| Swatch | Hex |
|--------|-----|
| paper cream | `#E8DFD0` |
| dust grey | `#9A9590` |
| oxidized brown | `#6B4E3D` |
| muted blue | `#5A6B7A` |

### steam

| Swatch | Hex |
|--------|-----|
| soot | `#1A1A1A` |
| iron | `#4A4E52` |
| rust | `#8B4513` |
| amber fire | `#C87820` |
| dirty green | `#4A5C3A` |

### electricity

| Swatch | Hex |
|--------|-----|
| tungsten gold | `#E8B060` |
| deep blue | `#1A2A5C` |
| pale porcelain | `#F2EDE6` |
| warning red | `#C03030` |

### digital

| Swatch | Hex |
|--------|-----|
| black glass | `#0A0C0E` |
| monitor green | `#33FF66` |
| cold cyan | `#40C8D8` |
| bruised violet | `#5C3A6E` |

### dionysus

| Swatch | Hex |
|--------|-----|
| restrained wine red | `#5C1A2E` |
| pomegranate | `#8B1E3D` |
| amber | `#C4903A` |
| skin warmth | `#D4A574` |
| deep shadow | `#1A1218` |

### table

| Swatch | Hex |
|--------|-----|
| worn wood | `#6B4A32` |
| cloth | `#C4B8A8` |
| human skin | `#D4A574` |
| warm practical light | `#FFD9A0` |

### title_card

| Swatch | Hex |
|--------|-----|
| near black | `#0A0A0A` |
| quiet off white | `#E8E4DC` |
| warm grey type | `#A8A098` |

## Presets

| Id | Family | Key energy | Motif links |
|----|--------|------------|-------------|
| `ATTIC_DUST` | attic | 40 | `MOTIF_HAND`, `MOTIF_RECORDING` |
| `OINO_ARCHIVE` | attic | 55 | `MOTIF_RECORDING`, `MOTIF_HAND` |
| `STEAM_SOOT` | steam | 90 | `MOTIF_DOORWAY`, `MOTIF_VINE_WATER` |
| `ELECTRIC_WARMTH` | electricity | 120 | `MOTIF_MELODY_CALL`, `MOTIF_MASK_THEATRE` |
| `DIGITAL_COLD` | digital | 35 | `MOTIF_RECORDING`, `MOTIF_MASK_THEATRE` |
| `DIONYSUS_AMBER_RED` | dionysus | 45 | `MOTIF_VINE_WATER`, `MOTIF_MASK_THEATRE` |
| `ZONE_REFLECTION` | digital | 30 | `MOTIF_DOORWAY`, `MOTIF_BOWL_TABLE` |
| `TABLE_WARMTH` | table | 180 | `MOTIF_BOWL_TABLE`, `MOTIF_HAND` |
| `OPEN_DOOR_DAWN` | attic | 2.5 | `MOTIF_DOORWAY` |
| `TITLE_CARD_BLACK` | title_card | 0 | — |

## Preset detail

### `ATTIC_DUST`

- **Family:** attic
- **World:** strength 0.15 / color `dust_grey`
- **Key / fill / rim:** 40 / 12 / 8
- **Volume:** thin dust motes — low density
- **Shots:** `SH010_CALL_TO_DINNER`, `SH020_ATTIC_ARCHIVE`
- **Must not:** saturated red wash; clean studio white

### `OINO_ARCHIVE`

- **Family:** attic
- **World:** strength 0.08 / color `oxidized_brown`
- **Key / fill / rim:** 55 / 10 / 15
- **Volume:** none — paper and grain read in surface
- **Shots:** `SH030_ARCHIVE_DISCOVERY`
- **Must not:** monitor green dominance; Dionysian wash on every plate

### `STEAM_SOOT`

- **Family:** steam
- **World:** strength 0.2 / color `soot`
- **Key / fill / rim:** 90 / 18 / 25
- **Volume:** steam / soot — mid density, warm scatter
- **Shots:** `SH040_MELODY_OPENS_HISTORY`, `SH050_CHANGING_WORLD`
- **Must not:** clean cyan digital look; title-card black void

### `ELECTRIC_WARMTH`

- **Family:** electricity
- **World:** strength 0.12 / color `deep_blue`
- **Key / fill / rim:** 120 / 20 / 8
- **Volume:** subtle haze only
- **Shots:** `SH050_CHANGING_WORLD`
- **Must not:** warning red as full-frame gel; horror sting red
- **Note:** Warning red is accent only — not a scare announce.

### `DIGITAL_COLD`

- **Family:** digital
- **World:** strength 0.05 / color `black_glass`
- **Key / fill / rim:** 35 / 8 / 12
- **Volume:** none
- **Shots:** `SH060_CARE_AND_HARM`, `SH090_REWIND_ENCOUNTER`
- **Must not:** warm table tungsten as key; wine red full wash

### `DIONYSUS_AMBER_RED`

- **Family:** dionysus
- **World:** strength 0.1 / color `deep_shadow`
- **Key / fill / rim:** 45 / 14 / 22
- **Volume:** none — colour lives in cup, stain, edge light
- **Shots:** `SH070_ZONE_PASSAGE`, `SH080_TABLE_ARRIVAL`, `SH110_RELEASE`
- **Must not:** every shot red; glowing god gel; literal magic-trick wine flood
- **Usage:** Living interruption inside grey / black / industrial blue systems. Switchable; omit freely.

### `ZONE_REFLECTION`

- **Family:** digital
- **World:** strength 0.18 / color `bruised_violet`
- **Key / fill / rim:** 30 / 16 / 20
- **Volume:** shallow water scatter — soft
- **Shots:** `SH070_ZONE_PASSAGE`
- **Must not:** resolved explanation light cue; jump-scare flash
- **Note:** Slightly wrong reflections — cool, unresolved.

### `TABLE_WARMTH`

- **Family:** table
- **World:** strength 0.1 / color `cloth`
- **Key / fill / rim:** 180 / 40 / 25
- **Volume:** none
- **Shots:** `SH080_TABLE_ARRIVAL`, `SH100_SISTER_REFLECTION`, `SH120_CHANGED_NOTE`
- **Must not:** red warning light for shadow; horror music-linked gel
- **Note:** Warm human light surrounded by colder space — LIGHT_WarmHuman / LIGHT_ColdSurround.

### `OPEN_DOOR_DAWN`

- **Family:** attic
- **World:** strength 0.35 / color `paper_cream`
- **Key / fill / rim:** 2.5 / 30 / 18
- **Volume:** soft exterior air into doorway
- **Shots:** `SH120_CHANGED_NOTE`
- **Must not:** closed attic blackout; title card prematurely
- **Note:** Final story image light — open doorway; invitation kept open.

### `TITLE_CARD_BLACK`

- **Family:** title_card
- **World:** strength 0.0 / color `near_black`
- **Key / fill / rim:** 0 / 0 / 0
- **Volume:** none
- **Shots:** `SH130_TITLE_CARD`
- **Must not:** coloured gel behind type; Dionysian red title wash
- **Note:** Near-black field; quiet off-white or warm grey type. Exact card: One Of Gods Fools / December 10, 2026.

## Rebuild

```text
python scripts/build_lighting_presets.py
```

