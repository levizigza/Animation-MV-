# Project status — Oino (Interlude)

**Film:** Oino (Interlude) · **Album:** One Of Gods Fools · **Release:** 2026-12-10  
**Resumed:** 2026-09-07 · **Phase:** Docs + review packages authored; **no Blender `.blend` on disk**

---

## Resume snapshot (current)

| Gate | Status |
|------|--------|
| Blender installed / on PATH | **No** — all `.blend` writes deferred |
| Music + narration timing approved | **No** — 0 manual music approvals; 9 pending; all monologue markers `REVIEW_REQUIRED` |
| Table performance passed review | **No** — blocked in docs only; `PERFORMANCE_REVIEW` has paths, no picture |
| Title card present + correct (docs/still) | **Yes** — `One Of Gods Fools` / `December 10, 2026`; no apostrophe |
| Title card Blender scene | **Deferred** — `scenes/SCN_13_TITLE_CARD.blend` not written |
| `docs/story_music_map.json` | **Assembled** from shot list + music sync + monologue |

### Latest versioned inspectable output

- **Scene:** `SCN_13_TITLE_CARD`
- **Shot:** `SH130_TITLE_CARD`
- **Frames:** `3051`–`3148`
- **Output:** see `renders/review/TITLE_CARD_REVIEW/LATEST_VERSION.json`

---

## Complete (authored / locked — not picture)

- Canon + creative bible; show/config/audio markers (~131.13 s, 3148 frames @ 24)
- Shot list (22 rows); camera / lighting / materials / motifs / atmosphere systems
- Scene packages as JSON/docs: archive, call-to-dinner, industrial world, Zone, table room, knock, holy fool, final meal, title card
- Table performance **block** (4 phases) — craft plan only
- Music sync map + preview slate; monologue text + provisional timing
- Review version folders (manifests); technical QA last run: **ok**, 3 warns (Blender deferred, missing textures, no blends)
- Final delivery scaffold under `renders/final/delivery/` (proxy picture + locked ending still)

## Broken / blocked

- No Blender executable → no craft renders, no `.blend` scene files
- Review movies listed in manifests **not** filled with Blender performance/world picture
- `project_status.md` previously described “foundation only” — superseded by this resume section
- Album title in `show_config.json` still uses apostrophe form for project/album fields; **on-screen card** lock remains without apostrophe

## Missing

- Character rigs, table env meshes, Zone lookdev, narration stem, melody stems
- Human approvals in `docs/music_sync_approvals.json` (empty)
- `PERFORMANCE_REVIEW` / `ANIMATIC_REVIEW` picture locks
- Blender install + `BLENDER_PATH`

## Version history (recent)

| When (UTC) | Script / package |
|------------|------------------|
| 2026-09-07T23:49 | `final_delivery` |
| 2026-09-07T23:42 | `qa_project` |
| 2026-09-07T23:23 | `render_review_versions` |
| 2026-09-07T23:16 | `music_sync` |
| 2026-09-07T23:12 | `build_title_card` |
| 2026-09-07T22:56 | `block_table_performance` |
| Latest title cut | `export_title_card_review_cut` → `TITLE_CARD_REVIEW/LATEST_VERSION.json` |

## Next smallest reviewable step (after this title cut)

Human approve music/narration against `renders/preview/music_sync_preview.mp4` + `docs/story_music_map.md`, **or** install Blender and write `SCN_08_TABLE_ROOM` Phase 2 (`SH080_WARM_TWO_SHOT`, frames 2440–2550) into `PERFORMANCE_REVIEW`.

Do not treat script exit codes as picture success.
