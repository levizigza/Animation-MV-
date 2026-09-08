# Ancestor arc - watcher to incomplete warning

**Starts as:** watcher  
**Ends as:** incomplete warning  
**Qualities:** perceptive, loving, fallible, implicated in the failure he describes

## Hard rules

- Omniscient prophet: `False`
- Supernatural judge: `False`
- Simple anti-ambition sermon: `False`

He did not only warn against humanity's ambition; he participated in the desire to preserve everything. Show implication, not omniscience.

## Visual language

- reflections
- partial faces
- damaged film
- documents
- reconstructed images
- out-of-focus movement

## Beats

| # | Id | Action | Mode | Implication |
|---|----|--------|------|-------------|
| 1 | `ANC_01_NOTICES_CHANGE` | He notices the beauty and danger of early industrial change. | observing | Beauty draws him closer as danger begins. |
| 2 | `ANC_02_MENDS_SLEEVE` | He helps mend a stranger's sleeve. | participating_care | He can still choose a small repair over spectacle. |
| 3 | `ANC_03_COAT_CATCHES` | He receives help when his own coat catches on a nail. | receiving_care | He needs others; the archive later forgets this mutuality. |
| 4 | `ANC_04_WATCHES_ASK` | He watches a worker ask for assistance. | watching_without_solving | Witness is not yet warning; the ask hangs. |
| 5 | `ANC_05_FOLLOWS_MELODY` | He follows the melody instead of stopping. | choosing_preservation_pull | Desire to follow the music outweighs stopping for need — early implication. |
| 6 | `ANC_06_PRESERVES_THROUGH_CALL` | He preserves voices and images while someone calls him to dinner. | preserving_instead_of_returning | Ordinary life ignored while preservation continues — he is already inside the pattern Oino inherits. |
| 7 | `ANC_07_CANNOT_TELL_TRUE` | He becomes unable to tell Oino which recording is true. | incomplete_authority | Archive excess breaks certainty; he cannot judge truth for her. |
| 8 | `ANC_08_ZONE_EXIT_NO_CERTAINTY` | He stands at the Zone exit and offers no certainty. | incomplete_warning | Ends as warning without map — loving, fallible, implicated. |

## Per-beat staging

### 1. `ANC_01_NOTICES_CHANGE` - Notices beauty and danger

- **Shot / frame:** `SH040_MELODY_OPENS_HISTORY` / f780
- **Marker:** `ANC_01_NOTICES_CHANGE`
- **Staging:** Steam and damp timber through a reflection; partial face at frame edge; no captioned judgment.

### 2. `ANC_02_MENDS_SLEEVE` - Mends a stranger's sleeve

- **Shot / frame:** `SH040_MELODY_OPENS_HISTORY` / f860
- **Marker:** `ANC_02_MENDS_SLEEVE`
- **Staging:** Hands and cloth in focus; faces soft or cropped; care as ordinary labour.

### 3. `ANC_03_COAT_CATCHES` - Receives help with the coat

- **Shot / frame:** `SH040_MELODY_OPENS_HISTORY` / f920
- **Marker:** `ANC_03_COAT_CATCHES`
- **Staging:** Nail, snagged fabric, stranger's hands; slightly awkward body; not heroic rescue.

### 4. `ANC_04_WATCHES_ASK` - Watches a worker ask for help

- **Shot / frame:** `SH050_CHANGING_WORLD` / f1280
- **Marker:** `ANC_04_WATCHES_ASK`
- **Staging:** Out-of-focus movement of the ask; ancestor's eye-line sharp; he does not become the answer.

### 5. `ANC_05_FOLLOWS_MELODY` - Follows the melody instead of stopping

- **Shot / frame:** `SH050_CHANGING_WORLD` / f1380
- **Marker:** `ANC_05_FOLLOWS_MELODY`
- **Staging:** Camera/body drift toward unfinished melody; injured ask falls behind in soft focus.

### 6. `ANC_06_PRESERVES_THROUGH_CALL` - Preserves while dinner calls

- **Shot / frame:** `SH030_ARCHIVE_DISCOVERY` / f600
- **Marker:** `ANC_06_PRESERVES_THROUGH_CALL`
- **Staging:** See CLIP_ANC_CAMERA_DINNER — ordinary, slightly embarrassing unedited take.

### 7. `ANC_07_CANNOT_TELL_TRUE` - Cannot tell which recording is true

- **Shot / frame:** `SH060_CARE_AND_HARM` / f1900
- **Marker:** `ANC_07_CANNOT_TELL_TRUE`
- **Staging:** Damaged film / reconstructed plates side by side; partial faces; no omniscient answer.

### 8. `ANC_08_ZONE_EXIT_NO_CERTAINTY` - Zone exit — no certainty

- **Shot / frame:** `SH070_ZONE_PASSAGE` / f2380
- **Marker:** `ANC_08_ZONE_EXIT_NO_CERTAINTY`
- **Staging:** Silhouette or reflection at threshold; incomplete warning; not a supernatural judge.

## Key clip

See [`ancestor_dinner_camera_clip.md`](ancestor_dinner_camera_clip.md) (`CLIP_ANC_CAMERA_DINNER`).

## Continuity checklist

- [ ] Beauty and danger noticed without prophetic voice-over.
- [ ] Sleeve mend and coat catch stay mutual, ordinary, slightly awkward.
- [ ] Melody pull leaves the asking worker unanswered.
- [ ] Dinner-call camera clip is embarrassing, not sermonizing.
- [ ] He cannot name the true recording; Zone exit offers no certainty.
- [ ] Ancestor-origin vs reconstructed footage stay visually distinct.

## Sources

- [`ancestor_arc.json`](ancestor_arc.json)
- [`ancestor_arc_markers.json`](ancestor_arc_markers.json)

```text
python scripts/build_ancestor_arc.py
```

