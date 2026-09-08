# Monologue timing — Oino (Interlude)

**Source text:** [`monologue.txt`](monologue.txt) (exact — do not rewrite)  
**Timing mode:** `provisional_no_stem`  
**Narration stem:** `not available`  
**Window:** f1–f746 @ 24 fps

## Policy

- Do **not** cut solely from punctuation.
- Use **breath, emphasis, silence, the music, and the movement of attention**.
- Protect the **young woman's voice**.
- Provisional timings are labeled **`REVIEW_REQUIRED`**.

## Subtitle / burn-in protection

- Faces — keep captions off facial performance / eyeline band
- Hands — do not cover door, tape, control, bowl, or sister's tap
- Reflections — keep sister / self reflection readable
- Title-safe — margins + never collide with `TITLE_CARD_FINAL`

Detail: [`monologue_subtitle_safe.json`](monologue_subtitle_safe.json)

## Markers

| Marker | Frame | Status | Phrase |
|--------|-------|--------|--------|
| `AMONG_THE_DUST` | 4 | **REVIEW_REQUIRED** | Among the dust |
| `HE_WAS_A_WATCHER` | 62 | **REVIEW_REQUIRED** | He was a watcher |
| `FINAL_DAYS` | 131 | **REVIEW_REQUIRED** | final days |
| `AIR_THICK_WITH_ANTICIPATION` | 179 | **REVIEW_REQUIRED** | air thick with anticipation |
| `WINDS_WHISPERED` | 227 | **REVIEW_REQUIRED** | winds whispered |
| `TOWER_OF_BABEL` | 276 | **REVIEW_REQUIRED** | Tower of Babel |
| `ICARUS` | 326 | **REVIEW_REQUIRED** | Icarus |
| `REFLECTION_OF_CHAOS` | 385 | **REVIEW_REQUIRED** | reflection of chaos |
| `DETHRONED_GODS` | 442 | **REVIEW_REQUIRED** | dethroned gods |
| `LABYRINTH` | 534 | **REVIEW_REQUIRED** | labyrinth |
| `THROUGH_HIS_LENS` | 556 | **REVIEW_REQUIRED** | Through his lens |
| `SLAVES_TO_VISIONS` | 599 | **REVIEW_REQUIRED** | slaves to the twisted visions |
| `CAUTIONARY_TALES` | 668 | **REVIEW_REQUIRED** | cautionary tales |
| `THRESHOLD_OF_ETERNITY` | 706 | **REVIEW_REQUIRED** | threshold of eternity |

## Paragraph provisional map

1. f4 — Among the dust and echoes of an old attic, I found them — videos left by…
2. f179 — He spoke of an air thick with anticipation, a world on the cusp of an un…
3. f385 — In his eyes, a reflection of chaos — a society mesmerized by its fantasi…
4. f556 — Through his lens, I saw their descent, captivated yet fearful, as they b…

## Rebuild

```text
python scripts/build_monologue_timing.py
python scripts/build_monologue_timing.py --check-audio
```

When a reviewed stem alignment exists, re-run and clear `REVIEW_REQUIRED` only after human approval.

