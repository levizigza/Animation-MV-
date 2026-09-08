# Technical QA report — Oino (Interlude)

**OK:** `True`  
**Fail / warn / pass:** 0 / 3 / 20

**Title lock:** `One Of Gods Fools`  
**Date lock:** `December 10, 2026`  

Emotional questions: [`emotional_qa.md`](emotional_qa.md) (not for on-screen use).

| Severity | Category | Detail | Path |
|----------|----------|--------|------|
| `pass` | `broken_audio` | Audio OK 2ch 48000Hz 6294479 frames | `audio/master.wav` |
| `pass` | `incorrect_title_card_text` | CANON contains exact title | `CANON.md` |
| `pass` | `missing_release_date` | CANON contains release date | `CANON.md` |
| `pass` | `incorrect_title_card_text` | title_card_brief text exact | `docs/title_card_brief.json` |
| `pass` | `missing_release_date` | title_card_brief date exact | `docs/title_card_brief.json` |
| `pass` | `duplicate_shot_ids` | camera_system shot ids unique | `—` |
| `pass` | `missing_cameras` | 21 camera names present | `—` |
| `pass` | `invalid_frame_ranges` | shot_list.csv ranges checked (22 shots) | `docs/shot_list.csv` |
| `pass` | `missing_markers` | Required markers present (8) | `docs/audio_markers.json` |
| `pass` | `missing_markers` | Required markers present (14) | `docs/monologue_timing_markers.json` |
| `pass` | `missing_markers` | Required markers present (1) | `docs/title_card_markers.json` |
| `pass` | `pink_or_disconnected_materials` | No pink texture flags in filesystem audit | `docs/material_audit_report.json` |
| `warn` | `unsupported_nodes_or_modifiers` | Blend node audit not run (Blender deferred) | `docs/material_audit_report.json` |
| `warn` | `missing_linked_files` | 33 expected material images not on disk (placeholders OK until authored) | `—` |
| `pass` | `excessive_particle_or_geometry_cost` | Atmosphere budgets preview=low final=crafted; no extreme densities | `—` |
| `pass` | `output_path_errors` | ANIMATIC_REVIEW output path OK | `renders/review/ANIMATIC_REVIEW/ANIMATIC_REVIEW.mp4` |
| `pass` | `output_path_errors` | PERFORMANCE_REVIEW output path OK | `renders/review/PERFORMANCE_REVIEW/PERFORMANCE_REVIEW.mp4` |
| `pass` | `output_path_errors` | WORLD_REVIEW output path OK | `renders/review/WORLD_REVIEW/WORLD_REVIEW.mp4` |
| `pass` | `output_path_errors` | COLOUR_REVIEW output path OK | `renders/review/COLOUR_REVIEW/COLOUR_REVIEW.mp4` |
| `pass` | `output_path_errors` | TITLE_CARD_REVIEW output path OK | `renders/review/TITLE_CARD_REVIEW/TITLE_CARD_REVIEW.mp4` |
| `pass` | `output_path_errors` | FINAL_REVIEW output path OK | `renders/review/FINAL_REVIEW/FINAL_REVIEW.mp4` |
| `pass` | `missing_markers` | emotional_qa.md present with key locks | `docs/emotional_qa.md` |
| `warn` | `missing_linked_files` | No .blend files yet (Blender deferred) — scene packages pending | `scenes/` |

## Rebuild

```text
python scripts/qa_project.py
python scripts/qa_project.py --strict
python scripts/render_review_versions.py
```

