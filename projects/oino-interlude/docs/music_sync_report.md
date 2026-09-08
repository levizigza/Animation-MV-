# Music sync report — Oino (Interlude)

**Updated:** 2026-09-07T23:16:26.650495+00:00  
**Preview:** `renders/preview/music_sync_preview.mp4` (created)

## Policy

- Cut to every beat: `False`
- Drive facial performance from amplitude: `False`
- Drive Oino decisions from amplitude: `False`
- Drive every camera cut from amplitude: `False`
- Audio-reactive secondary only: `True`
- Characters must listen: `True`

## Approval counts (movements)

- Automatic: **13**
- Manually approved: **0**
- Pending manual: **9**

## Cues

| Frame | Cue | Kind | Source | Approval |
|-------|-----|------|--------|----------|
| 1 | CUE_ENTRANCE | broad_cue | `docs/audio_markers.json` | **automatic** |
| 1 | AUDIO_START | structural | `docs/audio_markers.json` | **automatic** |
| 1 | NARRATION_START | structural | `docs/audio_markers.json` | **automatic** |
| 180 | watcher and singularity | narration | `frame_hint:180|anchor:NARRATION_START` | **pending_manual** |
| 307 | CUE_KNOCK | broad_cue | `docs/audio_markers.json` | **automatic** |
| 307 | room tone and distant call | music | `CUE_KNOCK` | **automatic** |
| 343 | CUE_FIRST_MELODY | broad_cue | `docs/audio_markers.json` | **automatic** |
| 343 | father's unfinished phrase | music | `CUE_FIRST_MELODY` | **automatic** |
| 391 | first Dionysus leitmotif | music | `CUE_FIRST_MELODY+DIONYSUS_LEITMOTIF` | **pending_manual** |
| 520 | archive discovery | narration | `frame_hint:520|anchor:CUE_ENTRANCE` | **pending_manual** |
| 746 | CUE_HARMONIC_CHANGE | broad_cue | `docs/audio_markers.json` | **automatic** |
| 746 | steam and labour pulse | music | `CUE_HARMONIC_CHANGE` | **automatic** |
| 746 | ascent and anticipation | narration | `frame_hint:746|anchor:CUE_HARMONIC_CHANGE` | **pending_manual** |
| 746 | NARRATION_END | structural | `docs/audio_markers.json` | **automatic** |
| 946 | electric release and dance | music | `CUE_HARMONIC_CHANGE` | **automatic** |
| 1131 | CUE_LOOP | broad_cue | `docs/audio_markers.json` | **automatic** |
| 1131 | future voice and memorial presence | music | `CUE_LOOP` | **automatic** |
| 1131 | Babel and Icarus | narration | `frame_hint:1131|anchor:CUE_LOOP` | **pending_manual** |
| 1531 | digital quantization | music | `CUE_LOOP` | **automatic** |
| 1600 | chaos and self-projection | narration | `frame_hint:1600|anchor:CUE_LOOP` | **pending_manual** |
| 2000 | labyrinth and ancestor failure | narration | `frame_hint:2000|anchor:CUE_REST` | **pending_manual** |
| 2225 | Zone suspension | music | `CUE_REST` | **automatic** |
| 2425 | CUE_REST | broad_cue | `docs/audio_markers.json` | **automatic** |
| 2425 | table warmth | music | `CUE_REST` | **automatic** |
| 2600 | rewind loop | music | `CUE_REST` | **automatic** |
| 2600 | descent and captivity | narration | `frame_hint:2600|anchor:CUE_REST` | **pending_manual** |
| 2723 | irregular knock | music | `CUE_RELEASE` | **automatic** |
| 2743 | CUE_RELEASE | broad_cue | `docs/audio_markers.json` | **automatic** |
| 2743 | release | music | `CUE_RELEASE` | **automatic** |
| 2743 | cautionary tale and threshold | narration | `frame_hint:2743|anchor:CUE_RELEASE` | **pending_manual** |
| 2897 | CUE_FINAL_PHRASE | broad_cue | `docs/audio_markers.json` | **automatic** |
| 2897 | sister's changed melody | music | `CUE_FINAL_PHRASE` | **automatic** |
| 3051 | title-card resolve | music | `TITLE_CARD_START` | **automatic** |
| 3051 | TITLE_CARD_START | structural | `docs/audio_markers.json` | **automatic** |
| 3148 | FINAL_FRAME | structural | `docs/audio_markers.json` | **automatic** |
| 3148 | MUSIC_END | structural | `docs/audio_markers.json` | **automatic** |
| 3148 | TITLE_CARD_END | structural | `docs/audio_markers.json` | **automatic** |

## Secondary reactive controls

- **steam vibration** (`RX_STEAM_VIBRATION`) — band `low_mid`, max 0.25 → machinery / steam volume proxies
- **cable sway** (`RX_CABLE_SWAY`) — band `low`, max 0.2 → cable / vine-through-machine proxies
- **screen brightness** (`RX_SCREEN_BRIGHTNESS`) — band `high`, max 0.35 → monitor / black-glass emission
- **water ripples** (`RX_WATER_RIPPLES`) — band `mid`, max 0.3 → ZONE_ShallowWater / table reflection
- **dust density** (`RX_DUST_DENSITY`) — band `low`, max 0.2 → attic / archive volume density
- **faint table resonance** (`RX_TABLE_RESONANCE`) — band `low_mid`, max 0.15 → TABLE_WornSurface micro-vibrate

## Forbidden amplitude targets

- `facial_performance`
- `oino_decision_beats`
- `primary_camera_cuts`

## Approve pending cues

```text
python scripts/music_sync.py --approve MUS_TABLE_WARMTH NAR_ARCHIVE_DISCOVERY
python scripts/music_sync.py --preview
```

