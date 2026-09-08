# Creative bible — Oino (Interlude)

Album: **One Of Gods Fools** · Release: **December 10, 2026**  
Authoritative lock: [`../CANON.md`](../CANON.md)  
Film project root: `projects/oino-interlude/`

This bible guides Blender / animatic / continuity work. It does not replace CANON; if they diverge, **CANON wins**.

---

## Logline spine

A young woman (Oino) narrates her great-great-grandfather's archive. Her sister's call to dinner triggers a journey through memory, technology, and unfinished music toward an ordinary table that can still be sacred. Reunion with the father comforts her; her shadow is control (rewind/edit). Her holy-fool act is letting him leave. She returns to her sister's anger and altered note. Final card: **One Of Gods Fools** / **December 10, 2026**.

## Cast (named collections)

| Role | Collection name (config) | Continuity notes |
|------|--------------------------|------------------|
| Oino | `CHAR_Oino` | Young woman; no generic magic; myth via choices & material |
| Sister | `CHAR_Sister` | Living person — rhythm, anger, creativity |
| Father | `CHAR_Father` | Temptation stays beautiful; unfinished melody |
| Watcher (GGG) | `CHAR_GreatGreatGrandfather` | Perceptive, loving, fallible, implicated |
| Dionysus | *(presence, not required as literal character)* | Life-force ↔ loss of self; not tech-villain |

## Mythic lineage (artistic adaptation)

Dionysus → Staphylus → Rhoeo → Anius → **Oino** → later descendants.

Gift: **transformation toward nourishment** (music, memory, food, care, change).

## Story objects

1. **Monologue** — original text unchanged; archive narration.
2. **Sister's call to dinner** — emotional + mythic trigger.
3. **Father's unfinished melody** — primary musical object.
4. **Industrial eras** — tools/landscapes change; human needs recur; each era **benefit + cost**.
5. **The table** — mythic destination (ordinary / intimate / sacred).
6. **The Zone** — do not explain (memory / simulation / spiritual / beyond).
7. **Shadow** — Oino rewinds, edits, controls until surprise dies.
8. **Holy-fool action** — allow father to leave while wanting him to stay.
9. **Ending behaviour** — return to sister, accept anger, follow altered note.
10. **Title card** — exact: *One Of Gods Fools* · December 10, 2026.

## Continuity supervisor checklist

Before approving a shot or layout:

- [ ] Who is **waiting**?
- [ ] Who is **leaving**?
- [ ] Who is **listening**?
- [ ] Who is **choosing**?
- [ ] Is the father reunion still comforting *before* the shadow?
- [ ] Is the sister more than a moral prop in this beat?
- [ ] Does tech show both relief and cost?
- [ ] Are we over-literalizing Babel / Icarus / Orpheus / Inanna / Midas / Dionysus?
- [ ] Are we syncing every cut to every beat? (Prefer breath + irregularity.)

## Look & craft (pipeline)

- Primary image source: **Blender + Grease Pencil / X-sheet craft** (repo MVM engine). No diffusion as primary path.
- Style pack default: `classic_cel` (repo `styles/classic_cel.json`) — placeholder until Oino lookdev lock.
- FPS 24 · 1920×1080 · seed `20261210` (`config/pipeline.json`).
- Soft MIR/heuristic suggestions must pass symbolic grounding; human approve before apply.

## Audio

- Master: `audio/master.wav`
- Source name preserved: `audio/Oino (Interlude)-Final.wav`
- Monologue stem: **PLACEHOLDER** (do not alter monologue text).
- Father melody / sister altered-note stems: **PLACEHOLDER** in `config/pipeline.json` → `missing_placeholders`.
