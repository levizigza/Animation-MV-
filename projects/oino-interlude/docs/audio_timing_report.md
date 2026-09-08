# Audio timing report — Oino (Interlude)

**Generated:** 2026-09-08T01:09:44.495828+00:00  
**Film:** Oino (Interlude) · **Album:** One Of God's Fools  
**Scene:** `AUDIO_MASTER` · **VSE:** `AUDIO_TIMELINE`

## Detection summary

| Field | Value |
|-------|-------|
| Music path | `audio/master.wav` |
| Sample rate | 48000 Hz |
| Channel count | 2 |
| Duration | 131.134979 s |
| FPS | 24 |
| Duration → frames | 3148 (FINAL_FRAME) |
| Music start | 0.000 s · frame 1 |
| Music end | 131.134979 s · frame 3148 |
| Narration mode | **embedded** |
| Narration path | `null` (no separate stem in show_config) |
| Narration start/end | See markers (embedded estimate — editable) |

## Narration vs music

Narration is treated as **embedded** in the mixed master (`narration_path` is null; `monologue_unchanged` remains true). `NARRATION_START` / `NARRATION_END` are **editable estimates**, not stem cuts.

## Structural markers

| Name | Time (s) | Frame | Note |
|------|----------|-------|------|
| `AUDIO_START` | 0.000 | 1 | First sample of mixed timeline |
| `NARRATION_START` | 0.000 | 1 | Start of archive monologue (embedded estimate — edit if stem arrives) |
| `NARRATION_END` | 31.092 | 746 | End of primary narration span (editable; not auto-locked to beats) |
| `MUSIC_END` | 131.135 | 3148 | Last frame of music / mixed master |
| `FINAL_FRAME` | 131.135 | 3148 | Picture end = ceil(duration*fps) alignment |
| `TITLE_CARD_START` | 127.135 | 3051 | One Of God's Fools card begins (default last 4s — editable) |
| `TITLE_CARD_END` | 131.135 | 3148 | Title card holds through FINAL_FRAME |

## Broad dramatic cues (not per-beat)

Policy: **do not** cut animation automatically to every transient or beat.

| Name | Time (s) | Frame | Note |
|------|----------|-------|------|
| `CUE_ENTRANCE` | 0.000 | 1 | World / archive entrance — music breathes in |
| `CUE_FIRST_MELODY` | 14.280 | 343 | First clear melodic statement (broad) |
| `CUE_HARMONIC_CHANGE` | 31.092 | 746 | First major section / harmonic turn |
| `CUE_KNOCK` | 12.780 | 307 | Sister's call-to-dinner knock (emotional trigger) |
| `CUE_LOOP` | 47.113 | 1131 | Memorial / repeating chorus loop character |
| `CUE_REST` | 101.053 | 2425 | Breath / bridge rest — do not fill with busy cuts |
| `CUE_RELEASE` | 114.312 | 2743 | Release toward sister / holy-fool letting go |
| `CUE_FINAL_PHRASE` | 120.723 | 2897 | Last living phrase before title card |

## Dionysus leitmotif

- Cue id: `DIONYSUS_LEITMOTIF`
- Status: **MUSIC_REVIEW_REQUIRED**
- `MUSIC_REVIEW_REQUIRED`: `True`
- Source file: `None`

### Placeholder proposal (not locked)

- Pitches: E3, G3, A3, E4
- MIDI: [52, 55, 57, 64]
- Shape: m3 ↑ · M2 ↑ · P5 ↑ (open, nourishing leap)
- Hint: E minor / modal — review against father's unfinished melody

### Required appearance modes

- **human family melody:** Singable / hummable contour in domestic register
- **loom or work rhythm:** Even pulse, shuttle-like repeats of the interval cells
- **dance rhythm:** Accent shift; same pitches, livelier subdivision
- **distorted digital pattern:** Bit-crushed / time-stretched echo of the contour
- **too perfect memorial loop:** Quantized, airless loop — shadow of control
- **living variation at end:** Breathing rubato / sister's altered note kinship

## Blender scene

- Target blend: `scenes/AUDIO_MASTER.blend`
- Status: created
- Detail: C:\Users\levyz\OneDrive\Microsoft Copilot Chat Files\Documents\Music Video Maker\projects\oino-interlude\scenes\AUDIO_MASTER.blend

## Editable source

Hand-edit markers in [`audio_markers.json`](audio_markers.json). Set `"hand_edited": true` after intentional changes so `setup_audio.py --reset-markers` will not overwrite without `--force`.

