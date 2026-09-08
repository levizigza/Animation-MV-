# Knock animation — SCN_08_TABLE_ROOM

**Throughline:** An irregular knock breaks the controlled table loop. Source stays uncertain until the reflection shows the sister already eating alone. Oino hears, sees her failure, and still keeps her hand on the control.

## Hard rules

- Jump scare: `False`
- Source certain before reflection: `False`
- Cost already exists: `True`
- Hypothetical later warning: `False`
- Breaks artificial rhythm: `True`

## Knock

- Marker: `KNOCK_INTERRUPT` @ f452
- Pattern: off-grid, incomplete call contour — breaks the exact-frame laugh loop
- Avoid: jump-scare door slam; horror sting; sudden creature at the door

## Possible sources (uncertain until reflection)

- `SRC_SISTER_TAP_DOWNSTAIRS` — the sister tapping downstairs
- `SRC_ATTIC_DOOR` — the attic door
- `SRC_BOWL_TABLE` — a bowl touching the table
- `SRC_MACHINE_MELODY` — a machine responding to the melody
- `SRC_ZONE_FORCE` — an unexplained force in the Zone

**Reveal:** reflection_reveals_sister → `SRC_SISTER_TAP_DOWNSTAIRS`

## Reflection

- Surface: `PROP_ReflectiveSurface_Sister`  
- Camera: `CAM_TABLE_REFLECTION`  
- Frames: 460–500

| Frame | Marker | Image |
|-------|--------|-------|
| 460 | `KNOCK_REFL_SISTER_WAITING` | the sister waiting |
| 472 | `KNOCK_REFL_TWO_BOWLS` | two bowls |
| 484 | `KNOCK_REFL_UNTOUCHED_PLACE` | one untouched place |
| 496 | `KNOCK_REFL_SISTER_EATS_ALONE` | the sister beginning to eat alone |

## Oino — three stages

### 1. She hears the interruption and tries to ignore it.

- Marker: `KNOCK_OINO_TRIES_IGNORE` @ f454
- Staging: No whip-pan to source. Head may tick toward sound then return. Desire protects the loop.
- Cost: Ignoring is already a choice against a living interrupt — not preparation for a later lesson.

### 2. She sees the sister and understands that she has repeated the ancestor's failure.

- Marker: `KNOCK_OINO_SEES_SISTER_FAILURE` @ f488
- Staging: Camera can favor CAM_TABLE_REFLECTION then Oino's eyes. Ancestor's implicated watching becomes her own control. Sister is a living person, not a moral prop.
- Cost: The failure is present-tense: sister already alone downstairs while Oino loops the father.

### 3. Her hand remains on the control because she still wants her father to stay.

- Marker: `KNOCK_OINO_HAND_REMAINS` @ f508
- Staging: Hold on hand + eyeline. Merciful control becomes known cost. Do not force release in this beat — wanting him to stay is honest.
- Cost: Cost already exists (sister eating alone); her hand staying proves desire outweighs return — now, not later.

## Must preserve

- Knock breaks artificial rhythm without jump scare
- Source uncertain until reflection reveals sister
- Reflection shows waiting, two bowls, untouched place, sister eating alone
- Three Oino stages: ignore → ancestor failure recognized → hand remains
- Cost already exists — not a hypothetical warning

## Must not

- Jump scare knock
- Confirm source before reflection
- Turn sister into a moral prop only
- Frame the loneliness as something that might happen later
- Horror sting or monster at the door

## Rebuild

```text
python scripts/animate_knock.py
python scripts/animate_knock.py --check-links
```

