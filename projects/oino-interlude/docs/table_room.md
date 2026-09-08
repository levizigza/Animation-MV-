# Table Room - SCN_08_TABLE_ROOM

**Role:** centre of the film — familiar family table inside impossible architecture from old industrial frames  
**Register:** warm, pleasurable, funny, safe enough that the audience understands why Oino stays  
**Oino receives:** what she came for — genuine comfort with the father before the shadow

## Hard rules

- Villain: `False`
- Father as monster: `False`
- Father life beyond Oino's desire: `True`
- First scene must feel safe: `True`
- Explain Dionysian uncertainty: `False`
- Dionysian uncertainty optional: `True`

## Elements

- **worn_table_surface:** `TABLE_WornSurface`
- **father_habitual_chair:** `CHAIR_Father_Habitual`
- **oino_chair:** `CHAIR_Oino`
- **window_or_opening:** `TABLE_WindowOpening`
- **playback_device:** `PROP_PlaybackDevice`
- **bowl_or_cup:** `PROP_Bowl`, `PROP_Cup`
- **machinery_as_quiet_architecture:** `ARCH_IndustrialFrame_A`, `ARCH_IndustrialFrame_B`, `ARCH_BeamQuiet`, `ARCH_ColumnRepurposed`
- **warm_human_light:** `LIGHT_WarmHuman`
- **colder_surrounding_space:** `LIGHT_ColdSurround`
- **vine_growth_one_table_leg:** `TABLE_VineLeg`
- **reflective_surface_sister_downstairs:** `PROP_ReflectiveSurface_Sister`

## Father life beats

| Id | Beat | Frame |
|----|------|-------|
| `FATHER_MUSICAL_MISTAKE` | the familiar musical mistake | 72 |
| `FATHER_LAUGH` | a laugh | 120 |
| `FATHER_NOTE_DISAGREEMENT` | a disagreement about a note | 168 |
| `FATHER_GLANCE_WINDOW` | a glance toward the window | 216 |
| `FATHER_PHYSICAL_HABIT` | a small physical habit | 264 |
| `FATHER_ORDINARY_PAUSE` | an ordinary pause | 312 |

## Saved cameras

- `CAM_TABLE_ARRIVAL` — arrival: Oino enters; warm table centre; industrial frames read as quiet architecture
- `CAM_TABLE_TWO_SHOT` — two-shot: Father and Oino share the table; safety and pleasure readable
- `CAM_TABLE_FATHER_HANDS` — father's hands: Musical mistake, habit, cup — life in the hands
- `CAM_TABLE_OINO_CONTROL` — Oino's hand on the control: Playback / control under her hand — gift received; shadow not yet
- `CAM_TABLE_REFLECTION` — table reflection: Reflective surface can show sister downstairs; ordinary world below
- `CAM_TABLE_FATHER_LEAVING` — father leaving: His motion toward window or door; life beyond her hold
- `CAM_TABLE_DOORWAY_LOOKBACK` — doorway looking back: Looking back at the table after warmth — patient; empty space allowed

## Dionysian uncertainty (optional)

- Default choice: vine-like shadow
- Object: `EDGE_DionysianUncertainty`
- Explain: `False`
- Staging: Visible only at frame edge; never centred; never labelled; may be omitted in a pass.

## Events

- `TABLE_ARRIVAL` f1: Oino arrives; warm human light vs colder space
- `TABLE_WARMTH_ESTABLISHED` f48: Register: warm, funny, safe — why she stays
- `TABLE_SISTER_REFLECTION_AVAILABLE` f192: Reflective surface capable of showing sister downstairs
- `TABLE_DIONYSUS_EDGE_OPTIONAL` f288: Optional Dionysian uncertainty at edge only; do not explain
- `TABLE_FATHER_EXIT_BEGIN` f360: Father begins to leave; Oino has received what she came for
- `TABLE_LOOKBACK` f420: Doorway looking back; table remains centre

## Blender

- Target: `scenes/SCN_08_TABLE_ROOM.blend`
- Status: **deferred**
- Detail: Install Blender, then re-run with --write-blend

```text
python scripts/build_table_room.py --write-blend
```

