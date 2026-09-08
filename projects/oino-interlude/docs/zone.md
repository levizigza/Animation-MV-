# Zone - SCN_07_ZONE

**Nature:** passage between archive, memory, simulation, spiritual encounter, and physical space  
**Resolved:** `False`  
**Oino's goal:** follow the unfinished melody

## Hard rules

- Villain: `False`
- Technical explanation: `False`
- Wish-room diagram: `False`
- Final answer what the Zone is: `False`
- Patient camera / empty hold after exit: `True` / `True`

## Elements

- **shallow_water:** `ZONE_ShallowWater`
- **industrial_debris:** `ZONE_Debris_A`, `ZONE_Debris_B`, `ZONE_Debris_C`
- **abandoned_tools:** `ZONE_Tool_Abandoned_A`, `ZONE_Tool_Abandoned_B`
- **doors_uncertain:** `ZONE_Door_A`, `ZONE_Door_B`, `ZONE_Door_C`
- **roots_vines_machinery:** `ZONE_VineThroughPipe`, `ZONE_RootMachine`
- **sound_reflections_wrong:** `ZONE_AUDIO_WrongReflection`
- **irregular_knock:** `ZONE_AUDIO_IrregularKnock`
- **unsourced_red_amber_light:** `ZONE_LIGHT_AmberUnsourced`
- **table_glimpse:** `ZONE_TableGlimpse`
- **distant_laugh:** `ZONE_AUDIO_DistantLaugh`
- **damaged_frame_dionysus_echo:** `ZONE_DamagedFrame_PossibleDionysus`

## Thresholds (certainty removed)

| Id | Certainty removed | Frame |
|----|-------------------|-------|
| `THR_01_MAP_MISMATCH` | the map no longer matches the corridor | 48 |
| `THR_02_PHOTO_UNPROVEN` | a photograph no longer proves where it was taken | 96 |
| `THR_03_VOICE_UNCLASSIFIED` | the voice may be living or reconstructed | 144 |
| `THR_04_REFLECTION_LATE` | her reflection responds a fraction late | 192 |
| `THR_05_ANCESTOR_INCOMPLETE` | the ancestor's guidance becomes incomplete | 240 |

## Events

- `ZONE_IRREGULAR_KNOCK` f120: Irregular knock — call-to-dinner cousin; not a scare sting
- `ZONE_DISTANT_LAUGH` f168: One distant laugh; may arrive before any visible source
- `ZONE_TABLE_GLIMPSE` f216: Table glimpsed before Oino reaches it — ordinary destination ahead
- `ZONE_DAMAGED_DIONYSUS_FRAME` f264: One damaged frame; possible Dionysus echo — do not label
- `ZONE_EMPTY_AFTER_OINO` f320: Oino leaves frame; camera holds empty space

## Blender

- Target: `scenes/SCN_07_ZONE.blend`
- Status: **deferred**
- Detail: Install Blender, then re-run with --write-blend

```text
python scripts/build_zone.py --write-blend
```

