# Oino transformation language

**Mythic source:** Oenotropae as *visual and emotional language only* — not generic superhero power set for Oino.
**Inherited principle:** transformation toward nourishment

## Hard rules

- Generic superhero powers: `False`
- Destroy the gift: `False`
- Force reunion forever: `False`
- **Answer:** Change how the gift is used. Carry memory home and share it rather than forcing it to repeat forever.

## Subtle transformation chain

| Id | From -> To | Nourishment link | Emotional read |
|----|------------|------------------|----------------|
| `XF_WATER_TO_STEAM` | clear water -> steam | water | life made usable as power without claiming dominion over it |
| `XF_STEAM_TO_ELECTRIC_HAZE` | steam -> electric haze | time returned by machines | heat becomes light-time — hours returned to bodies |
| `XF_HAZE_TO_SCREEN_GLOW` | electric haze -> screen glow | memory preserved through recording | atmosphere becomes interface — connection and capture arrive together |
| `XF_SCREEN_TO_AMBER` | screen glow -> reflected amber light | food | digital cold turns toward table warmth without ceremony |
| `XF_DRY_BOWL_TO_MEAL` | a dry bowl -> a shared meal | food | vessel waits, then feeds relation — gift used as sharing |
| `XF_MECH_TO_HUMAN_MELODY` | a mechanical rhythm -> a human melody | music changed by another person | grid softens into sister's living contour |
| `XF_PRESERVED_TO_LIVING` | a preserved image -> a living variation | memory preserved through recording | archive yields to change instead of endless identical playback |
| `XF_CABLE_TO_VINE` | a red cable -> a vine | water | tech line becomes growing line — connection as life, not only extraction |
| `XF_VINE_TO_PATH` | a vine -> a line of movement through the world | time returned by machines | growth becomes path — pilgrimage, not power display |

## Nourishment tracks

### food (`NTR_FOOD`)

- **Throughline:** Dry bowl / untouched bowls -> shared meal at the table; gift feeds relation.
- **Forced-production risk:** Treat people as endless providers of comfort.
- **Markers:** `XF_DRY_BOWL_TO_MEAL`, `XF_SCREEN_TO_AMBER`

### water (`NTR_WATER`)

- **Throughline:** Clear water -> steam -> haze; stain that only reads as wine under amber.
- **Forced-production risk:** Divert every flow into output; leave nothing to drink.
- **Markers:** `XF_WATER_TO_STEAM`, `XF_CABLE_TO_VINE`

### time returned by machines (`NTR_TIME`)

- **Throughline:** Electric relief returns hours — dance possible; empty chair shows uneven return.
- **Forced-production risk:** Schedule every returned hour so nothing is free.
- **Markers:** `XF_STEAM_TO_ELECTRIC_HAZE`, `XF_VINE_TO_PATH`

### speech restored through assistance (`NTR_SPEECH`)

- **Throughline:** Assistive synthetic voice for the living; distinct from harvested/reconstructed dead speech.
- **Forced-production risk:** Prefer controllable reconstructed voice over living assisted speech.
- **Markers:** `XF_HAZE_TO_SCREEN_GLOW`

### memory preserved through recording (`NTR_MEMORY`)

- **Throughline:** Archive preserves; shadow begins when preservation becomes forced identical replay.
- **Forced-production risk:** Harvest voices; loop the father until he cannot surprise.
- **Markers:** `XF_HAZE_TO_SCREEN_GLOW`, `XF_PRESERVED_TO_LIVING`

### music changed by another person (`NTR_MUSIC`)

- **Throughline:** Father's unfinished melody -> sister's altered note; living variation at the end.
- **Forced-production risk:** Quantize the family melody into a too-perfect memorial loop.
- **Markers:** `XF_MECH_TO_HUMAN_MELODY`, `XF_PRESERVED_TO_LIVING`

## Danger of forced production (visual parallels)

| Parallel | Image | Echoes |
|----------|-------|--------|
| `FP_WORKERS_MEASURED` | workers being measured | Judging blocks/monitors score bodies instead of seeing needs. (cf. Oenotropae treated as resource) |
| `FP_OENOTROPAE_RESOURCE` | Oenotropae being treated as a resource | Mythic gift imagined as endless yield — artistic warning, not literal superpower. (cf. workers being measured) |
| `FP_VOICES_HARVESTED` | voices being harvested | Cleaner corridor voices; reconstructed dead speech sold as comfort. (cf. Oino extracting the same reunion) |
| `FP_OINO_EXTRACTS_REUNION` | Oino repeatedly extracting the same reunion from her father | Shadow: rewind/edit until the encounter cannot surprise her. (cf. voices being harvested) |

## Resolution

- **Not:** destruction of the gift
- **Is:** changing how the gift is used
- **Action:** Oino carries memory home and shares it rather than forcing it to repeat forever

### Beats

- Release the father (holy-fool action)
- Return to sister; accept anger
- Follow the changed note
- Dry bowls become shared meal
- Preserved image yields to living variation

## Continuity checklist

- [ ] No laser hands / generic magic powers for Oino.
- [ ] Water/steam/haze/screen/amber read as one changing world.
- [ ] Dry bowl becomes shared meal; sister changes the music.
- [ ] Workers measured // gift-as-resource // harvested voices // Oino's rewind are visibly parallel.
- [ ] Ending shares memory home — does not smash the archive or loop the father forever.

## Sources

- [`oino_transformation_language.json`](oino_transformation_language.json)
- [`oino_transformation_markers.json`](oino_transformation_markers.json)

```text
python scripts/build_oino_transformation_language.py
```

