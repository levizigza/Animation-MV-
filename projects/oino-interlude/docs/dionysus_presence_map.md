# Dionysus presence map - Oino (Interlude)

**Album role:** major character in One Of God's Fools.  
**This film:** recurring presence — not a narrator who explains mythology.  
**Literal cameo default:** `False`

## Hard rules

- Glowing horned god giving instructions: `False`
- Voice saying he is Dionysus: `False`
- Every red object a symbol: `False`
- Explain mythology on screen: `False`

Echoes are **optional and individually switchable**. Disabled = must not appear.

## Evolution (no on-screen phase titles)

| Phase | Presence |
|-------|----------|
| **EARLY** | *hidden in family objects* - Vine, water, cup, and melody — inheritance as nourishment, not announcement. |
| **MIDDLE** | *visible in labour and theatre* - Labour, dance, theatre, masks, laughter, and the breakdown of rigid categories. |
| **ZONE** | *ambiguous and beautiful* - Impossible to classify — do not resolve as god, glitch, or ghost. |
| **TABLE** | *ordinary meal becomes sacred* - Sacred without becoming a religious ceremony. |
| **RELEASE** | *transformation outward* - Movement, breath, birds, or changed music — not a cameo bow. |

## Echo map

| Echo | On? | First phase | Appears | Does | Meaning now | Changes later? |
|------|-----|-------------|---------|------|-------------|----------------|
| `ECHO_RED_GARMENT` (Red garment in a crowd) | **no** | MIDDLE | A single red garment moves through a labour or gathering crowd — not every red prop. | Pulls the eye once; then is absorbed by the crowd again. | Life-force flash inside industrial anonymity. | TABLE: If recalled, only as warmth of cloth at the meal — never as costume ID of the god. |
| `ECHO_LAUGH_BEFORE_SOURCE` (Laugh that arrives before the visible source) | **no** | MIDDLE | A laugh is heard a beat before any mouth or body that could own it. | Breaks rigid sync between sound and picture; invites loss of self / joy tension. | Theatre and labour categories blur — who is laughing for whom. | ZONE: May return with no source at all; still do not caption it as Dionysus. |
| `ECHO_MASK_BLACK_GLASS` (Mask reflected in black glass) | **no** | MIDDLE | A mask appears only as reflection in dark glass/monitor — not worn as god cosplay. | Suggests theatre / loss of face without explaining cult. | Persona and machine glass share one surface. | ZONE: Reflection may fail to match any foreground face — still unclassified. |
| `ECHO_IVY_THROUGH_MACHINE` (Ivy or vine growing through a machine) | **yes** | EARLY | Vine/ivy threads a loom, pipe, or cable bundle — worn growth, not CGI miracle. | Links WORLD_ORGANIC_GROWTH to labour machines; nourishment through technology's gaps. | Hidden in family/world objects — vine as lineage without lecture. | MIDDLE: Growth thickens where categories break (dance floor / factory edge). |
| `ECHO_BROKEN_STAFF_GROWTH` (Broken staff or tool with organic growth) | **no** | EARLY | Archive/world tool that only resembles a broken thyrsus — mechanical + organic, not costume prop. | Sits among family objects; invites touch without naming. | Inherited principle as worn tool — transformation toward nourishment. | RELEASE: May be left behind; growth continues without becoming a relic worshipped on screen. |
| `ECHO_WINE_LIGHT` (Wine-coloured light) | **yes** | EARLY | Wine-coloured light (#5C1A2E family) on cup, stain, or lamp — only when motivated. | Conditions water-stain / table warmth; not a continuous god gel. | Hidden in cup/water/melody adjacency. | TABLE: Same light makes the ordinary meal feel sacred without altar staging. |
| `ECHO_HAND_PERCUSSION_DANCE` (Hand percussion or dance impulse in a mechanical rhythm) | **no** | MIDDLE | A body adds off-grid clap/step inside factory or electric pulse. | Breaks rigid category of machine time vs living time. | Labour becoming dance without abandoning work. | RELEASE: Kin to sister's table tap / changed melody — living variation, not memorial loop. |
| `ECHO_ARCHIVE_FRAME_FIGURE` (Figure in one damaged archive frame) | **no** | EARLY | One damaged ancestor or reconstructed plate holds an unidentifiable figure for a few frames. | Creates doubt — watcher, guest, stain, or theatre — then gone. | Presence inside family memory without genealogy lecture. | ZONE: If echoed, still refuse classification; never label the frame Dionysus. |
| `ECHO_ZONE_EXIT_SILHOUETTE` (Silhouette near the Zone exit) | **no** | ZONE | A silhouette at the passage edge — beautiful, brief, unreadable. | Holds ambiguity: guide, threat, reflection, or nothing. | ZONE presence — impossible to classify. | TABLE: Does not reappear as the same silhouette at dinner; sacredness shifts to the meal. |
| `ECHO_WHITE_BIRDS_RELEASE` (White birds or dove-like forms during release) | **yes** | RELEASE | White bird / dove-like release image as Oino lets the father leave. | Transforms presence into movement and breath — holy-fool letting go. | RELEASE — transformation into changed music / freedom, not a god exit. | no (terminal image) |

## Per-echo detail

### `ECHO_RED_GARMENT` - Red garment in a crowd [disabled]

- **Marker:** `DION_ECHO_RED_GARMENT` · shot `SH050_CHANGING_WORLD` · f1400
- **First phase:** MIDDLE
- **Appears:** A single red garment moves through a labour or gathering crowd — not every red prop.
- **Does:** Pulls the eye once; then is absorbed by the crowd again.
- **Meaning at appearance:** Life-force flash inside industrial anonymity.
- **Later change (TABLE):** If recalled, only as warmth of cloth at the meal — never as costume ID of the god.
- **Forbid:** horns; name caption; tracking shot that proves identity

### `ECHO_LAUGH_BEFORE_SOURCE` - Laugh that arrives before the visible source [disabled]

- **Marker:** `DION_ECHO_LAUGH_BEFORE_SOURCE` · shot `SH050_CHANGING_WORLD` · f1550
- **First phase:** MIDDLE
- **Appears:** A laugh is heard a beat before any mouth or body that could own it.
- **Does:** Breaks rigid sync between sound and picture; invites loss of self / joy tension.
- **Meaning at appearance:** Theatre and labour categories blur — who is laughing for whom.
- **Later change (ZONE):** May return with no source at all; still do not caption it as Dionysus.
- **Forbid:** voice saying I am Dionysus; laugh as jump scare

### `ECHO_MASK_BLACK_GLASS` - Mask reflected in black glass [disabled]

- **Marker:** `DION_ECHO_MASK_BLACK_GLASS` · shot `SH060_CARE_AND_HARM` · f1800
- **First phase:** MIDDLE
- **Appears:** A mask appears only as reflection in dark glass/monitor — not worn as god cosplay.
- **Does:** Suggests theatre / loss of face without explaining cult.
- **Meaning at appearance:** Persona and machine glass share one surface.
- **Later change (ZONE):** Reflection may fail to match any foreground face — still unclassified.
- **Forbid:** putting the mask on a glowing god body

### `ECHO_IVY_THROUGH_MACHINE` - Ivy or vine growing through a machine [ENABLED]

- **Marker:** `DION_ECHO_IVY_THROUGH_MACHINE` · shot `SH040_MELODY_OPENS_HISTORY` · f900
- **First phase:** EARLY
- **Appears:** Vine/ivy threads a loom, pipe, or cable bundle — worn growth, not CGI miracle.
- **Does:** Links WORLD_ORGANIC_GROWTH to labour machines; nourishment through technology's gaps.
- **Meaning at appearance:** Hidden in family/world objects — vine as lineage without lecture.
- **Later change (MIDDLE):** Growth thickens where categories break (dance floor / factory edge).
- **Forbid:** vine spelling DIONYSUS; instant full coverage growth gag

### `ECHO_BROKEN_STAFF_GROWTH` - Broken staff or tool with organic growth [disabled]

- **Marker:** `DION_ECHO_BROKEN_STAFF_GROWTH` · shot `SH030_ARCHIVE_DISCOVERY` · f650
- **First phase:** EARLY
- **Appears:** Archive/world tool that only resembles a broken thyrsus — mechanical + organic, not costume prop.
- **Does:** Sits among family objects; invites touch without naming.
- **Meaning at appearance:** Inherited principle as worn tool — transformation toward nourishment.
- **Later change (RELEASE):** May be left behind; growth continues without becoming a relic worshipped on screen.
- **Forbid:** intact ceremonial thyrsus; god handing the staff to Oino

### `ECHO_WINE_LIGHT` - Wine-coloured light [ENABLED]

- **Marker:** `DION_ECHO_WINE_LIGHT` · shot `SH030_ARCHIVE_DISCOVERY` · f700
- **First phase:** EARLY
- **Appears:** Wine-coloured light (#5C1A2E family) on cup, stain, or lamp — only when motivated.
- **Does:** Conditions water-stain / table warmth; not a continuous god gel.
- **Meaning at appearance:** Hidden in cup/water/melody adjacency.
- **Later change (TABLE):** Same light makes the ordinary meal feel sacred without altar staging.
- **Forbid:** every red practical as wine gel; spotlight that follows a horned figure

### `ECHO_HAND_PERCUSSION_DANCE` - Hand percussion or dance impulse in a mechanical rhythm [disabled]

- **Marker:** `DION_ECHO_HAND_PERCUSSION_DANCE` · shot `SH050_CHANGING_WORLD` · f1250
- **First phase:** MIDDLE
- **Appears:** A body adds off-grid clap/step inside factory or electric pulse.
- **Does:** Breaks rigid category of machine time vs living time.
- **Meaning at appearance:** Labour becoming dance without abandoning work.
- **Later change (RELEASE):** Kin to sister's table tap / changed melody — living variation, not memorial loop.
- **Forbid:** bacchanal crowd takeover of the whole frame

### `ECHO_ARCHIVE_FRAME_FIGURE` - Figure in one damaged archive frame [disabled]

- **Marker:** `DION_ECHO_ARCHIVE_FRAME_FIGURE` · shot `SH030_ARCHIVE_DISCOVERY` · f580
- **First phase:** EARLY
- **Appears:** One damaged ancestor or reconstructed plate holds an unidentifiable figure for a few frames.
- **Does:** Creates doubt — watcher, guest, stain, or theatre — then gone.
- **Meaning at appearance:** Presence inside family memory without genealogy lecture.
- **Later change (ZONE):** If echoed, still refuse classification; never label the frame Dionysus.
- **Forbid:** subtitle This is Dionysus; clear god portrait in HD

### `ECHO_ZONE_EXIT_SILHOUETTE` - Silhouette near the Zone exit [disabled]

- **Marker:** `DION_ECHO_ZONE_EXIT_SILHOUETTE` · shot `SH070_ZONE_PASSAGE` · f2350
- **First phase:** ZONE
- **Appears:** A silhouette at the passage edge — beautiful, brief, unreadable.
- **Does:** Holds ambiguity: guide, threat, reflection, or nothing.
- **Meaning at appearance:** ZONE presence — impossible to classify.
- **Later change (TABLE):** Does not reappear as the same silhouette at dinner; sacredness shifts to the meal.
- **Forbid:** silhouette sprouting horns; voice-over explanation

### `ECHO_WHITE_BIRDS_RELEASE` - White birds or dove-like forms during release [ENABLED]

- **Marker:** `DION_ECHO_WHITE_BIRDS_RELEASE` · shot `SH110_RELEASE` · f2820
- **First phase:** RELEASE
- **Appears:** White bird / dove-like release image as Oino lets the father leave.
- **Does:** Transforms presence into movement and breath — holy-fool letting go.
- **Meaning at appearance:** RELEASE — transformation into changed music / freedom, not a god exit.
- **Later change:** none mapped
- **Forbid:** birds forming a face; caption Dionysus departs

## Continuity checks

- [ ] No glowing horned instructor.
- [ ] No self-naming Dionysus voice.
- [ ] Not every red practical is an echo.
- [ ] EARLY stays hidden in objects/melody; RELEASE becomes birds/breath/changed music.
- [ ] TABLE sacredness is meal/relationship, not ceremony.

## Sources

- [`dionysus_presence.json`](dionysus_presence.json)
- [`dionysus_presence_switches.json`](dionysus_presence_switches.json)
- [`dionysus_presence_markers.json`](dionysus_presence_markers.json)
- Leitmotif proposal: [`dionysus_leitmotif.json`](dionysus_leitmotif.json)

```text
python scripts/build_dionysus_presence.py --enable ECHO_WINE_LIGHT ECHO_WHITE_BIRDS_RELEASE
```

