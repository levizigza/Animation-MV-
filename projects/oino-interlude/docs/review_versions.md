# Review versions — Oino (Interlude)

**Emotional QA is not part of the film.** See [`emotional_qa.md`](emotional_qa.md).

**Title card lock:** `One Of Gods Fools` / `December 10, 2026`

| Version | Purpose | Output | Status |
|---------|---------|--------|--------|
| `ANIMATIC_REVIEW` | Proxy staging, rhythm, broad cues — not detail modelling | `renders/review/ANIMATIC_REVIEW` | paths_ready |
| `PERFORMANCE_REVIEW` | Eyes, hands, breath, table performance, holy-fool release | `renders/review/PERFORMANCE_REVIEW` | paths_ready |
| `WORLD_REVIEW` | Modular industrial world, eras benefit/cost, Zone, atmosphere | `renders/review/WORLD_REVIEW` | paths_ready |
| `COLOUR_REVIEW` | Lighting presets, Dionysian interruption, AgX, no every-shot-red | `renders/review/COLOUR_REVIEW` | paths_ready |
| `TITLE_CARD_REVIEW` | Exact card text/date, still frame, controls, TITLE_CARD_FINAL | `renders/review/TITLE_CARD_REVIEW` | paths_ready |
| `FINAL_REVIEW` | Full emotional + technical lock pass before delivery | `renders/review/FINAL_REVIEW` | paths_ready |

## Rebuild

```text
python scripts/render_review_versions.py
python scripts/render_review_versions.py --write-slate
python scripts/qa_project.py
```

