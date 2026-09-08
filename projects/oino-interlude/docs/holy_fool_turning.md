# Holy-fool turning — SCN_08_TABLE_ROOM

**Throughline:** Ancestor at the exit offers no map. Oino looks, releases the control, lets the father finish and leave, carries the recording out, and looks back once without commanding return. Ordinary and costly — no cosmic reward.  
**Animatic:** `SH110_RELEASE`  
**Holy-fool action:** allowing the father to leave while she still wants him to stay  
**Quality:** ordinary and costly

## Hard rules

- Cosmic reward: `False`
- Explosion: `False`
- Proof world saved: `False`
- Ancestor as oracle: `False`
- Guarantee of return: `False`

## Ancestor at exit

- `HF_ANCESTOR_AT_EXIT` @ f520: stands near the exit
- Explanation: `False`
- Guarantee Oino can return: `False`
- Link: `ANC_08_ZONE_EXIT_NO_CERTAINTY`
- Staging: Near doorway / Zone-table threshold; incomplete warning presence; loving, fallible, implicated — not a supernatural judge or oracle.

## Beats

| Frame | Marker | Who | Action |
|-------|--------|-----|--------|
| 528 | `HF_LOOK_ANCESTOR_TO_FATHER` | Oino | looking from the ancestor to her father |
| 540 | `HF_FATHER_TENDER_PERSONAL` | Father | the father remaining tender and personal |
| 552 | `HF_ANCESTOR_NOT_ORACLE` | Ancestor | the ancestor refusing to become an oracle |
| 564 | `HF_RELEASE_CONTROL` (hinge) | Oino | Oino releasing the playback control |
| 576 | `HF_SEQUENCE_FORWARD` | Scene | the sequence moving forward |
| 588 | `HF_FATHER_FINISHES_MELODY` | Father | the father finishing the melody |
| 612 | `HF_FATHER_STANDS_LEAVES` | Father | the father standing and leaving |
| 636 | `HF_LISTEN_SOUND_AND_SILENCE` | Oino | Oino listening through the final sound and the silence after it |
| 660 | `HF_CARRY_RECORDING_OUT` | Oino | Oino carrying the recording out |
| 684 | `HF_LOOK_BACK_THRESHOLD` | Oino | one look back at the threshold without commanding a return |

_Hinge = releasing the playback control._

## Optional Dionysian release

- Max images in final shot: `1`
- Additional only if: animatic proves that additional imagery helps
- Default: `REL_DUST_TO_WHITE_BIRDS` → dust or film perforations become white birds
- Explain: `False`

Options:

- `REL_VINE_LOOSENS` — a vine loosens from a machine
- `REL_DUST_TO_WHITE_BIRDS` — dust or film perforations become white birds
- `REL_RED_REFLECTION_BREAKS` — a red reflection breaks into moving light
- `REL_RHYTHM_BECOMES_BREATH` — a rhythm becomes breath

## Must preserve

- Ancestor offers no explanation and no guarantee of return
- Father stays tender and personal through the leave
- Holy-fool action is ordinary and costly — she releases what she still wants
- One look back without commanding return
- At most one optional Dionysian release image unless animatic proves more helps

## Must not

- Cosmic reward
- Explosion
- Proof that the world has been saved
- Ancestor as oracle
- Father as monster under a digital face
- Stack multiple Dionysian release images in the final shot by default

## Rebuild

```text
python scripts/animate_holy_fool_turning.py
python scripts/animate_holy_fool_turning.py --check-links
```

