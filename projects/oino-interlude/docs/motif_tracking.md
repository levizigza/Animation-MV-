# Motif tracking — Oino (Interlude)

**System:** `OINO_MOTIF_SYSTEM`  
**Film:** Oino (Interlude)  
**Allow new symbols:** `False`  
**Readability:** readable_pending_review — No new symbols until every locked motif has first_appearance, at least one transformation, and final_meaning, and explicit_untransformed is empty or resolved.

## Policy

- Track first appearance → transformation → final meaning. Orphan symbols (appear once, never transform) must be flagged.
- Required arc per motif: `first_appearance`, `transformation`, `final_meaning`
- **Do not add new symbols until this system is readable.**

## Untransformed flags

None. Every locked motif has first appearance, transformation(s), and final meaning.

## Motifs (summary)

| Motif | First | Transformations | Final |
|-------|-------|-----------------|-------|
| **RECORDING** | protected fragment | ancestral evidence; substitute for presence | memory shared with the living |
| **HAND** | closes the attic door | touches the archive; helps or fails to help; rewinds and grips the control; releases the control; accepts the bowl | follows the sister's rhythm |
| **DOORWAY** | excludes the sister | becomes a factory gate; becomes the Zone threshold; becomes the route home | remains open at the end |
| **BOWL AND TABLE** | waiting | nourishment; Oino's absence; reflected consequence | shared participation |
| **VINE AND WATER** | inherited Oino lineage | life growing through machines; transformation; nourishment | release from rigid structures |
| **MASK AND THEATRE** | people performing futures | artificial versions of the self; Dionysian presence | the father as a person rather than a perfect performance |
| **MELODY AND CALL TO DINNER** | invitation refused | archive opened; industrial rhythm; memorial loop; interruption | living variation |

## Motif detail

### RECORDING

**Id:** `MOTIF_RECORDING`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | protected fragment | `SH020_ATTIC_ARCHIVE` | `MOTIF_REC_PROTECTED_FRAGMENT` |
| `transformation` | ancestral evidence | `SH030_ARCHIVE_DISCOVERY` | `MOTIF_REC_ANCESTRAL_EVIDENCE` |
| `transformation` | substitute for presence | `SH090_REWIND_ENCOUNTER` | `MOTIF_REC_SUBSTITUTE_PRESENCE` |
| `final_meaning` | memory shared with the living | `SH120_CHANGED_NOTE` | `MOTIF_REC_MEMORY_SHARED` |

#### protected fragment

- **Staging:** Attic / archive: a protected fragment of the unfinished melody.
- **Links:** `PROP_PlaybackDevice`, `audio/master.wav`

#### ancestral evidence

- **Staging:** Recording as proof of the ancestor's world — evidence, not yet presence.
- **Links:** `CALL_02_ARCHIVE_ANCESTOR`, `CLIP_ANC_CAMERA_DINNER`

#### substitute for presence

- **Staging:** Loop and rewind make the recording stand in for the living father.
- **Links:** `BLOCK_P3_RESET_MERCY`, `PROP_PlaybackControl`

#### memory shared with the living

- **Staging:** Carried downstairs; audible to imperfect end beside living women — shared, not controlled.
- **Links:** `HF_CARRY_RECORDING_OUT`, `FM_AUDIO_RECORDING_IMPERFECT_END`

### HAND

**Id:** `MOTIF_HAND`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | closes the attic door | `SH010_CALL_TO_DINNER` | `MOTIF_HAND_CLOSES_ATTIC` |
| `transformation` | touches the archive | `SH030_ARCHIVE_DISCOVERY` | `MOTIF_HAND_TOUCHES_ARCHIVE` |
| `transformation` | helps or fails to help | `SH040_MELODY_OPENS_HISTORY` | `MOTIF_HAND_HELPS_OR_FAILS` |
| `transformation` | rewinds and grips the control | `SH090_REWIND_ENCOUNTER` | `MOTIF_HAND_REWINDS_GRIPS` |
| `transformation` | releases the control | `SH110_RELEASE` | `MOTIF_HAND_RELEASES_CONTROL` |
| `transformation` | accepts the bowl | `SH120_CHANGED_NOTE` | `MOTIF_HAND_ACCEPTS_BOWL` |
| `final_meaning` | follows the sister's rhythm | `SH120_CHANGED_NOTE` | `MOTIF_HAND_FOLLOWS_SISTER` |

#### closes the attic door

- **Staging:** Hand refuses the invitation — door closes on the sister.
- **Links:** `CALL_01_SISTER_DOWNSTAIRS`

#### touches the archive

- **Staging:** Fingers on reels, plates, documents — preservation as contact.
- **Links:** `SCN_02_OINO_ARCHIVE`

#### helps or fails to help

- **Staging:** Ancestor/worker hands: care possible; also the choice to follow melody instead.
- **Links:** `ANC_02_MENDS_SLEEVE`, `ANC_05_FOLLOWS_MELODY`

#### rewinds and grips the control

- **Staging:** Shadow hand — grip that removes spontaneity.
- **Links:** `BLOCK_P3_FINDS_CONTROL`, `KNOCK_OINO_HAND_REMAINS`

#### releases the control

- **Staging:** Holy-fool hinge: fingers lift while wanting remains.
- **Links:** `HF_RELEASE_CONTROL`

#### accepts the bowl

- **Staging:** Receives nourishment beside the sister.
- **Links:** `FM_ACCEPTS_BOWL`

#### follows the sister's rhythm

- **Staging:** Hand/tap joins living variation — participation, not archive correction.
- **Links:** `FM_OINO_FOLLOWS`, `CALL_06_TABLE_TAP_NEW_MELODY`

### DOORWAY

**Id:** `MOTIF_DOORWAY`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | excludes the sister | `SH010_CALL_TO_DINNER` | `MOTIF_DOOR_EXCLUDES_SISTER` |
| `transformation` | becomes a factory gate | `SH050_CHANGING_WORLD` | `MOTIF_DOOR_FACTORY_GATE` |
| `transformation` | becomes the Zone threshold | `SH070_ZONE_PASSAGE` | `MOTIF_DOOR_ZONE_THRESHOLD` |
| `transformation` | becomes the route home | `SH110_RELEASE` | `MOTIF_DOOR_ROUTE_HOME` |
| `final_meaning` | remains open at the end | `SH120_CHANGED_NOTE` | `MOTIF_DOOR_REMAINS_OPEN` |

#### excludes the sister

- **Staging:** Attic door shut — ordinary invitation kept out.
- **Links:** `CALL_01_SISTER_DOWNSTAIRS`

#### becomes a factory gate

- **Staging:** Industrial threshold — labour world as another kind of closed gate.
- **Links:** `CALL_03_FACTORY_ALARM`, `ARCH_IndustrialFrame_A`

#### becomes the Zone threshold

- **Staging:** Uncertain destination doors; ancestor at exit with no guarantee of return.
- **Links:** `ZONE_Door_A`, `ANC_08_ZONE_EXIT_NO_CERTAINTY`, `THR_01_MAP_MISMATCH`

#### becomes the route home

- **Staging:** Look back without commanding return — doorway as path toward sister.
- **Links:** `HF_LOOK_BACK_THRESHOLD`, `CAM_TABLE_DOORWAY_LOOKBACK`

#### remains open at the end

- **Staging:** Final story image: open doorway — invitation kept open.
- **Links:** `FM_OPEN_DOORWAY`

### BOWL AND TABLE

**Id:** `MOTIF_BOWL_TABLE`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | waiting | `SH010_CALL_TO_DINNER` | `MOTIF_BOWL_WAITING` |
| `transformation` | nourishment | `SH080_TABLE_ARRIVAL` | `MOTIF_BOWL_NOURISHMENT` |
| `transformation` | Oino's absence | `SH100_SISTER_REFLECTION` | `MOTIF_BOWL_OINO_ABSENCE` |
| `transformation` | reflected consequence | `SH100_SISTER_REFLECTION` | `MOTIF_BOWL_REFLECTED_CONSEQUENCE` |
| `final_meaning` | shared participation | `SH120_CHANGED_NOTE` | `MOTIF_BOWL_SHARED_PARTICIPATION` |

#### waiting

- **Staging:** Two bowls wait downstairs while Oino delays.
- **Links:** `OPEN_TWO_BOWLS`

#### nourishment

- **Staging:** Table centre: food, warmth, gift toward care.
- **Links:** `PROP_Bowl`, `TABLE_WornSurface`, `LIGHT_WarmHuman`

#### Oino's absence

- **Staging:** Untouched place downstairs — cost already present.
- **Links:** `KNOCK_REFL_UNTOUCHED_PLACE`

#### reflected consequence

- **Staging:** Sister beginning to eat alone in the table reflection.
- **Links:** `KNOCK_REFL_SISTER_EATS_ALONE`, `PROP_ReflectiveSurface_Sister`

#### shared participation

- **Staging:** Bowl accepted; melody shared — memory becomes participation.
- **Links:** `FM_ACCEPTS_BOWL`, `FM_OINO_FOLLOWS`

### VINE AND WATER

**Id:** `MOTIF_VINE_WATER`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | inherited Oino lineage | `SH020_ATTIC_ARCHIVE` | `MOTIF_VINE_INHERITED_LINEAGE` |
| `transformation` | life growing through machines | `SH050_CHANGING_WORLD` | `MOTIF_VINE_THROUGH_MACHINES` |
| `transformation` | transformation | `SH060_CARE_AND_HARM` | `MOTIF_VINE_TRANSFORMATION` |
| `transformation` | nourishment | `SH080_TABLE_ARRIVAL` | `MOTIF_VINE_NOURISHMENT` |
| `final_meaning` | release from rigid structures | `SH110_RELEASE` | `MOTIF_VINE_RELEASE_RIGID` |

#### inherited Oino lineage

- **Staging:** Vine / water / cup as inheritance — nourishment lineage, not lecture.
- **Links:** `ECHO_IVY_THROUGH_MACHINE`, `ECHO_WINE_LIGHT`

#### life growing through machines

- **Staging:** Roots and vines integrated with machinery / quiet architecture.
- **Links:** `ZONE_VineThroughPipe`, `TABLE_VineLeg`, `organic_growth`

#### transformation

- **Staging:** Gift as change of material and relation — toward nourishment.
- **Links:** `oino_transformation_language.json`

#### nourishment

- **Staging:** Water / juice / wine-coloured light at the meal — subtle.
- **Links:** `PROP_Cup`, `LIGHT_WarmHuman`

#### release from rigid structures

- **Staging:** Optional vine loosen / birds / breath — release from loop and machine grip.
- **Links:** `REL_VINE_LOOSENS`, `REL_DUST_TO_WHITE_BIRDS`, `HF_RELEASE_CONTROL`

### MASK AND THEATRE

**Id:** `MOTIF_MASK_THEATRE`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | people performing futures | `SH050_CHANGING_WORLD` | `MOTIF_MASK_PERFORMING_FUTURES` |
| `transformation` | artificial versions of the self | `SH090_REWIND_ENCOUNTER` | `MOTIF_MASK_ARTIFICIAL_SELF` |
| `transformation` | Dionysian presence | `SH070_ZONE_PASSAGE` | `MOTIF_MASK_DIONYSIAN_PRESENCE` |
| `final_meaning` | the father as a person rather than a perfect performance | `SH110_RELEASE` | `MOTIF_MASK_FATHER_AS_PERSON` |

#### people performing futures

- **Staging:** Crowds / labour / possible futures staged as performance without era labels.
- **Links:** `ECHO_RED_GARMENT`, `revolution_passes`

#### artificial versions of the self

- **Staging:** Quantized laugh / locked attention — self as perfect playback.
- **Links:** `BLOCK_P4_LAUGH_SAME_FRAME`, `ECHO_MASK_BLACK_GLASS`

#### Dionysian presence

- **Staging:** Optional edge figure / damaged frame — presence without explanation.
- **Links:** `EDGE_DionysianUncertainty`, `ZONE_DamagedFrame_PossibleDionysus`

#### the father as a person rather than a perfect performance

- **Staging:** Tender, personal, allowed to finish and leave — not a flawless loop.
- **Links:** `HF_FATHER_TENDER_PERSONAL`, `HF_FATHER_FINISHES_MELODY`

### MELODY AND CALL TO DINNER

**Id:** `MOTIF_MELODY_CALL`

| Role | Meaning | Shot | Marker |
|------|---------|------|--------|
| `first_appearance` | invitation refused | `SH010_CALL_TO_DINNER` | `MOTIF_MELODY_INVITATION_REFUSED` |
| `transformation` | archive opened | `SH030_ARCHIVE_DISCOVERY` | `MOTIF_MELODY_ARCHIVE_OPENED` |
| `transformation` | industrial rhythm | `SH050_CHANGING_WORLD` | `MOTIF_MELODY_INDUSTRIAL_RHYTHM` |
| `transformation` | memorial loop | `SH090_REWIND_ENCOUNTER` | `MOTIF_MELODY_MEMORIAL_LOOP` |
| `transformation` | interruption | `SH100_SISTER_REFLECTION` | `MOTIF_MELODY_INTERRUPTION` |
| `final_meaning` | living variation | `SH120_CHANGED_NOTE` | `MOTIF_MELODY_LIVING_VARIATION` |

#### invitation refused

- **Staging:** Sister calls; Oino does not come.
- **Links:** `CALL_01_SISTER_DOWNSTAIRS`

#### archive opened

- **Staging:** Call returns as ancestral / archive recording.
- **Links:** `CALL_02_ARCHIVE_ANCESTOR`

#### industrial rhythm

- **Staging:** Factory / terminal echoes of the dinner call.
- **Links:** `CALL_03_FACTORY_ALARM`, `CALL_04_TERMINAL_NOTIFICATION`

#### memorial loop

- **Staging:** Exact repetition / locked laugh — melody as memorial control.
- **Links:** `BLOCK_P4_LAUGH_SAME_FRAME`, `OPEN_MELODY_EXACT`

#### interruption

- **Staging:** Irregular knock breaks artificial rhythm — not a jump scare.
- **Links:** `KNOCK_INTERRUPT`, `CALL_05_ZONE_KNOCK`

#### living variation

- **Staging:** Sister changes the note; Oino follows; living melody carries the final sound.
- **Links:** `FM_SISTER_CHANGES_NOTE`, `CALL_06_TABLE_TAP_NEW_MELODY`, `FM_AUDIO_LIVING_CARRIES`

## Continuity checklist

- [ ] Recording ends as memory shared with the living (not only a loop).
- [ ] Hand arc: close door → grip control → release → accept bowl → follow sister.
- [ ] Doorway ends open (story final), answering the closed attic.
- [ ] Bowl/table: waiting → absence/reflection → shared participation.
- [ ] Vine/water: lineage through machines toward release from rigid structures.
- [ ] Mask/theatre: futures and artificial selves resolve toward father as person.
- [ ] Melody/call: refused invitation → living variation (CALL_01 → CALL_06).
- [ ] No new symbols added while `allow_new_symbols` is false.
- [ ] Untransformed flags list is empty or explicitly resolved.

## Sources

- Machine-readable: [`motif_system.json`](motif_system.json)
- Markers: [`motif_system_markers.json`](motif_system_markers.json)
- Related: [`call_to_dinner_tracking.md`](call_to_dinner_tracking.md), [`final_meal_animation.md`](final_meal_animation.md), [`holy_fool_turning.md`](holy_fool_turning.md)

```text
python scripts/build_motif_system.py
python scripts/build_motif_system.py --check-links
```

