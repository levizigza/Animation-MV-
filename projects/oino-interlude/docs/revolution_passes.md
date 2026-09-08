# Revolution passes - four movements + possible futures

**Scene:** `SCN_MODULAR_INDUSTRIAL_WORLD`  
**On-screen era labels:** forbidden  
**History carried by:** energy_systems, materials, interfaces, labour, food, music, relationships

One modular world. Not four unrelated cities.

## Movement 1 - Water, steam, and hands (`MOV_01_WATER_STEAM_HANDS`)

**Internal only** - no slate text on screen.

- **Controls:** era_blend=0.2, future_branch=0.0, organic_growth=0.15, dionysus_presence=0.25
- **Collections:** `WORLD_WATER_AND_REFLECTIONS`, `WORLD_STEAM`, `WORLD_STRUCTURE`
- **Palette:** waterwheel, loom, steam, damp stone, timber, hand labour

| Axis | Content |
|------|---------|
| Benefit | Shared power of water and steam multiplies what hands alone can feed and warm. |
| Cost | Judgment systems and machines rank bodies; injury and exhaustion stay visible. |
| Gesture of care | Ancestor repairs a stranger's sleeve; stranger frees the caught coat. |
| Temptation toward control | Coloured blocks/monitors that score workers instead of seeing them. |
| Dionysian echo | Children singing the family contour as loom/work rhythm (life-force in labour song). |

### Staging beats

- `M1_SCHOOLROOM_SINGING`: A schoolroom with children singing
- `M1_JUDGING_BLOCKS`: Coloured blocks or monitors judging workers
- `M1_SLEEVE_REPAIR`: The ancestor repairs a stranger's sleeve
- `M1_COAT_FREED`: The stranger frees the ancestor when his coat catches
- `M1_INJURED_ASKS`: An injured worker asks for help while the melody draws Oino onward

## Movement 2 - Electricity, light, and time (`MOV_02_ELECTRICITY_LIGHT_TIME`)

**Internal only** - no slate text on screen.

- **Controls:** era_blend=0.5, future_branch=0.05, organic_growth=0.1, dionysus_presence=0.3
- **Collections:** `WORLD_ELECTRIC`, `WORLD_STRUCTURE`, `WORLD_STEAM`
- **Palette:** electric light, domestic interiors, poles and lamps, alarm as gathering rhythm

| Axis | Content |
|------|---------|
| Benefit | Light and machines return hours of life — a woman can dance. |
| Cost | Another home keeps an empty chair; relief is unevenly distributed. |
| Gesture of care | Neighbors organize to the alarm rhythm — mutual aid, not panic. |
| Temptation toward control | Schedule every returned hour so nothing is wasted or free. |
| Dionysian echo | Dance rhythm of the family melody under electric lamps (joy without erasing the empty chair). |

### Staging beats

- `M2_LIGHT_RELIEVES`: Electric light genuinely relieves domestic labour
- `M2_WOMAN_DANCES`: A woman dances because a machine returns time to her
- `M2_EMPTY_CHAIR`: Another household waits beside an empty chair
- `M2_ALARM_GATHERS`: An alarm becomes the rhythm of people gathering and organizing
- `M2_BENEFIT_AND_ABSENCE`: Show benefit and absence in the same visual movement

## Movement 3 - Computing, screens, and confession (`MOV_03_COMPUTING_SCREENS_CONFESSION`)

**Internal only** - no slate text on screen.

- **Controls:** era_blend=0.72, future_branch=0.25, organic_growth=0.2, dionysus_presence=0.35
- **Collections:** `WORLD_DIGITAL`, `WORLD_ELECTRIC`, `WORLD_STRUCTURE`
- **Palette:** terminals, monitors, network faces, corridors of cleaner lost voices

| Axis | Content |
|------|---------|
| Benefit | Confession and kinship can travel distance; the lonely can be answered. |
| Cost | Self and dead voices become editable loops; presence without presence. |
| Gesture of care | A relative stays on the line until the admission is finished. |
| Temptation toward control | Play Oino's recording without her — perfect, interruptible, owned. |
| Dionysian echo | Too-perfect memorial loop of the melody in the corridor; slight timing errors as living tremor. |

### Staging beats

- `M3_PRIVATE_ADMISSION`: A person types a private admission into a terminal
- `M3_DISTANT_RELATIVE`: A distant relative appears through a network
- `M3_FACES_OFFSET`: Faces repeat with slight timing differences
- `M3_OINO_WITHOUT_HER`: Oino sees her own recording playing without her
- `M3_CLEANER_VOICE`: Every corridor offers a cleaner version of a lost voice

## Movement 4 - Assistance, memorial presence, and possible futures (`MOV_04_ASSISTANCE_MEMORIAL_FUTURES`)

**Internal only** - no slate text on screen.

- **Controls:** era_blend=0.88, future_branch=0.7, organic_growth=0.4, dionysus_presence=0.45
- **Collections:** `WORLD_POSSIBLE_FUTURES`, `WORLD_DIGITAL`, `WORLD_ORGANIC_GROWTH`, `WORLD_STRUCTURE`
- **Palette:** assistive devices, synthetic voice panels, re-framed factory structure, central ordinary table

| Axis | Content |
|------|---------|
| Benefit | Assistive voice returns agency to the living speaker. |
| Cost | Reconstructed dead speech can sell comfort as ownership of the lost. |
| Gesture of care | Hands set bowls on the ordinary table for whoever still arrives. |
| Temptation toward control | Prefer the reconstructed voice to the living person's slower assistive speech. |
| Dionysian echo | Wine-coloured light on the table; melody as nourishment, not spectacle. |

### Staging beats

- `M4_LIVING_ASSISTIVE`: A living person speaks through an assistive synthetic voice
- `M4_DECEASED_RECONSTRUCTED`: A deceased person's voice is reconstructed
- `M4_FACTORY_NOT_CITY`: Old factory frames become structures that do not resemble cities
- `M4_TABLE_CENTRE`: An ordinary table appears at the centre

## Possible futures (`PASS_FUTURES`)

- **Controls:** era_blend=0.92, future_branch=0.85, organic_growth=0.35, dionysus_presence=0.4

| Axis | Content |
|------|---------|
| Benefit | Speech and presence restored for the living who need assistive tools. |
| Cost | Memorial reconstruction can replace grief with a controllable ghost. |
| Gesture of care | Someone adjusts a device so another person can finish a sentence. |
| Temptation toward control | Loop the reconstructed voice until it cannot surprise. |
| Dionysian echo | Living variation of the family melody against a too-perfect memorial loop. |

### Staging

- assistive synthetic voice used by a living person
- reconstructed voice of a deceased person (clearly not the same ethical class)
- old factory frames become non-city structures
- ordinary table (ANCHOR) at the centre

## Sources

- [`revolution_passes.json`](revolution_passes.json)
- [`revolution_pass_presets.json`](revolution_pass_presets.json)
- [`revolution_pass_markers.json`](revolution_pass_markers.json)
- World: [`modular_industrial_world.json`](modular_industrial_world.json)

```text
python scripts/build_revolution_passes.py --pass MOV_01_WATER_STEAM_HANDS --write-world
```

