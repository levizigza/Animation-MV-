# Title card — SCN_13_TITLE_CARD

**Emotional ending (before card):** Oino follows the sister's changed melody  
**Title:** **One Of Gods Fools**  
**Date:** **December 10, 2026**  
**Apostrophe in Gods:** `False`

## Sequence after emotional ending

1. `TC_HOLD_OPEN_DOORWAY` f1: Hold on the open doorway.
2. `TC_LIVING_NOTE_SETTLES` f16: Let the last living note settle.
3. `TC_RECORDING_IMPERFECT_END` f28: Allow the original recording to reach its imperfect end.
4. `TC_FADE_NEAR_BLACK` f40: Fade to a quiet near-black frame.
5. `TC_TITLE_FADE_IN` f52: Fade in the exact album title: One Of Gods Fools
6. `TC_DATE_FADE_IN` f70: Fade in the exact release date: December 10, 2026

## Hard rules

- Extra subtitle: `False`
- Logline: `False`
- Moral statement: `False`
- Social handle: `False`
- Unapproved production credit: `False`
- Trailer animation / metallic / glow / fast move: `False` / `False` / `False` / `False`
- Typography: legible, quiet, tactile, and slightly archaeological

## Exposed controls

- title fade in: `12` frames
- date fade in: `10` frames
- title hold duration: `72` frames
- date hold duration: `54` frames
- background colour: `#0A0A0A` (near_black)
- type colour: `#E8E4DC` (quiet_off_white)
- letter spacing: `0.08`
- final fade out: enabled=`False` (default off unless delivery requires it)

## TITLE_CARD_FINAL

- Local range: f52–f148
- Global align: f3051–f3148
- Note: Final title-card frame range — title and date hold on near-black

## Blender

- Target: `scenes/SCN_13_TITLE_CARD.blend`
- Status: **deferred**
- Detail: Install Blender, then re-run with --write-blend

```text
python scripts/build_title_card.py --write-blend
```

