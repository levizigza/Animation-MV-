# Table performance block — SCN_08_TABLE_ROOM

**Throughline:** Warm reunion becomes shadow through merciful reset, then missing life — not horror announcement.  
**Dread from:** repetition and missing life

## Hard rules

- Horror music: `False`
- Red warning light: `False`
- Monster reveal: `False`
- First pass must feel safe: `True`
- Shadow is: rewind / edit / control until the encounter cannot surprise her

## Animation priorities

- **eyes and eyelines** (`eyes_eyelines`): Track who looks at whom; father's glance to window vs locked look at Oino after control.
- **breathing** (`breathing`): Alive irregular breath in Phases 1–2; Phase 4 breath locks to loop length.
- **fingers and hand contact** (`fingers_hand_contact`): Cup rim, table edge, playback keys; Oino's hand on control as the moral hinge.
- **weight shifts** (`weight_shifts`): Chair settles, lean toward laugh, rise to leave; Phase 4 weight no longer drifts.
- **Oino trying to conceal the reset** (`conceal_reset`): Body shields the control; eyes stay soft; mercy mask — not villain staging.
- **the father's independent attention** (`father_independent_attention`): Window, note preference, pause — life beyond her desire until she removes it.
- **the instant Oino recognizes that her own hand is creating the loss** (`recognition_own_hand`): Eyeline from father's identical laugh down to her fingers still on the control; no sting.

## Phases

### Phase 1 — ARRIVAL

**Frames:** 1–96  
**Register:** cautious hope; recognition without scare  
**Cameras:** `CAM_TABLE_ARRIVAL`, `CAM_TABLE_FATHER_HANDS`

| Frame | Marker | Who | Action |
|-------|--------|-----|--------|
| 1 | `BLOCK_P1_OINO_ENTERS` | Oino | enters cautiously |
| 48 | `BLOCK_P1_FATHER_MID_MELODY` | Father | halfway through the unfinished melody |
| 72 | `BLOCK_P1_FAMILIAR_MISTAKE` | Father | makes the mistake she remembers |

**Must preserve**

- Father is already living before she enters
- Mistake is remembered and loved

**Must not**

- Announce danger
- Lock father's attention only on Oino

### Phase 2 — PLEASURE

**Frames:** 97–312  
**Register:** warm, pleasurable, funny, safe — why she stays  
**Cameras:** `CAM_TABLE_TWO_SHOT`, `CAM_TABLE_FATHER_HANDS`, `CAM_TABLE_REFLECTION`

| Frame | Marker | Who | Action |
|-------|--------|-----|--------|
| 120 | `BLOCK_P2_FATHER_LAUGHS` | Father | laughs |
| 132 | `BLOCK_P2_OINO_SITS` | Oino | sits |
| 168 | `BLOCK_P2_PREFERENCE_DISAGREEMENT` | Father | has a preference, distraction, or small disagreement |
| 216 | `BLOCK_P2_ORDINARY_COMPANY` | Both | she enjoys his ordinary company; his attention can leave her |

**Must preserve**

- Audience understands why she stays
- Father has life beyond Oino's desire
- Tenderness is specific, not generic

**Must not**

- Foreshadow with red light or horror cue
- Make father a monster under a digital face

### Phase 3 — THE FIRST RESET

**Frames:** 313–400  
**Register:** merciful control; second pass a fraction too precise  
**Cameras:** `CAM_TABLE_FATHER_LEAVING`, `CAM_TABLE_OINO_CONTROL`, `CAM_TABLE_TWO_SHOT`

| Frame | Marker | Who | Action |
|-------|--------|-----|--------|
| 320 | `BLOCK_P3_FATHER_BEGINS_LEAVE` | Father | begins to leave |
| 348 | `BLOCK_P3_FINDS_CONTROL` | Oino | finds the playback control |
| 360 | `BLOCK_P3_RESET_MERCY` | Oino | resets the scene; it feels merciful |
| 384 | `BLOCK_P3_SECOND_TOO_PRECISE` | Both | second version plays a fraction too precise |

**Must preserve**

- Reset feels merciful first
- Shadow enters through behaviour, not scare design

**Must not**

- Horror music sting on reset
- Red warning light
- Monster reveal

### Phase 4 — THE LOSS OF SPONTANEITY

**Frames:** 401–480  
**Register:** dread from repetition and missing life  
**Cameras:** `CAM_TABLE_OINO_CONTROL`, `CAM_TABLE_TWO_SHOT`, `CAM_TABLE_DOORWAY_LOOKBACK`

| Frame | Marker | Who | Action |
|-------|--------|-----|--------|
| 408 | `BLOCK_P4_REMOVE_PAUSES` | Oino | removes pauses |
| 420 | `BLOCK_P4_REMOVE_DISAGREEMENTS` | Oino | removes disagreements |
| 432 | `BLOCK_P4_REMOVE_GLANCES` | Oino | removes glances |
| 444 | `BLOCK_P4_REMOVE_DEPARTURES` | Oino | removes departures |
| 456 | `BLOCK_P4_LAUGH_SAME_FRAME` | Father | laughter occurs on exactly the same frame |
| 468 | `BLOCK_P4_ATTENTION_NO_INDEPENDENCE` | Father | his attention no longer moves independently |
| 476 | `BLOCK_P4_RECOGNITION_OWN_HAND` | Oino | recognizes that her own hand is creating the loss |

**Must preserve**

- Dread from repetition and missing life
- Recognition lands on Oino's hand, not a villain reveal

**Must not**

- Horror music
- Red warning light
- Monster reveal to announce the shadow

## Pass versions

- **pass_a_living:** Phases 1–2 only as full life reference; keep mistakes, laughs, disagreements, glances, pauses, departure.
- **pass_b_first_reset:** Phase 3 — merciful; fraction too precise.
- **pass_c_loss:** Phase 4 — strip spontaneity; lock laugh to exact frame; freeze independent attention.

## Rebuild

```text
python scripts/block_table_performance.py
python scripts/block_table_performance.py --check-table-room
```

