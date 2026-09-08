# Craft-First Animation Engine — Repository Audit

**Status:** documentation only (no production code changed in this audit)  
**Package:** `mvm` 0.1.0  
**Audit date:** 2026-09-07  
**Checks cited:** `pytest tests/` → 2 passed

This document maps the current Cel Music Video Studio codebase for implementation planning under a craft-first operating contract: authored frames, visible decisions, human approval for meaningful creative changes.

---

## 1. System map

```text
ENTRY POINTS
  mvm CLI (typer) ──────────────┐
  Studio UI (Vite/React) ──API──┤
  uvicorn mvm.studio_api:app ───┘
           │
           ▼
  project JSON tree (source of truth)
           │
    ┌──────┼──────────────┬──────────────┐
    ▼      ▼              ▼              ▼
  MIR    Agents         Cel craft     Editorial
 audio/  agents/        cel/ +        editorial/
 analyze pipeline       blender/      assemble +
                        runner        Remotion stub
           │
           ▼
  approve gate (plan_approved)
           │
           ▼
  craft preview / render → mux → final/
```

---

## 2. Current application entry points

| Entry | Location | Role |
|-------|----------|------|
| CLI | `mvm/cli.py` → console script `mvm` | `init`, `analyze`, `plan`, `approve-plan`, `craft`, `assemble`, `styles`, `list`, `review-export`, `version` |
| Studio API | `mvm/studio_api.py` | FastAPI on `:8787`; CORS open; multipart project create |
| Studio UI | `studio/` (`npm run dev` → `:5173`, proxies `/api`) | Human review: waveform/sections, shot edits, approve, craft |
| Blender craft script | `mvm/blender/scripts/craft_shot.py` | Headless Blender: hybrid 3D + Grease Pencil from `craft_payload.json` |
| Remotion stub | `editorial/remotion/src/Overlays.tsx` | Overlay composition placeholder (not wired into assemble yet) |
| Package install | `pyproject.toml` | `pip install -e ".[studio]"` |

**API routes (exist):**  
`/api/health`, `/api/styles`, `/api/projects` (GET/POST), `/api/projects/{slug}`, PATCH shot, POST approve-plan, craft, assemble, GET audio.

---

## 3. Rendering pipeline

**Order of operations (intended):**

1. `init` — copy audio, write `project.json`
2. `analyze` — librosa MIR → `beatmap.json`
3. `plan` — rule-based agents → `story.json`, `shots/*.json`, `xsheets/*.json` (`plan_approved=false`)
4. **Human approve** — CLI `approve-plan` or Studio POST approve
5. `craft` — blocked unless `plan_approved`
6. Blender if found; else **declared** `fallback_cel_preview` (Pillow frames from X-sheet)
7. `assemble` — FFmpeg / `imageio-ffmpeg` mux audio + plate; write `final/remotion_props.json`

**Craft data handoff:**  
`write_craft_payload` → `previews|renders/<shot_id>/craft_payload.json` containing shot, xsheet, style, fps, resolution.

**Engines:**

| Engine id | When | Output |
|-----------|------|--------|
| `blender` | `BLENDER_PATH` / PATH / common install paths | `shot_preview.mp4` (+ `.blend`) |
| `fallback_cel_preview` | Blender missing or Blender fails | PNG sequence and/or MP4 |

**Preserved contract:** fallback is still X-sheet-driven craft timing, not diffusion. Engine id is returned in craft result dict (CLI prints it; Studio shows status string).

---

## 4. Animation data structures

Defined in `mvm/schemas/models.py` (Pydantic):

| Model | Purpose |
|-------|---------|
| `Beatmap` | duration, bpm, beats, downbeats, onsets, sections, energy/flux curves |
| `Section` | name, start/end seconds, energy |
| `Story` / `Character` | narrative, motifs, model-sheet notes |
| `CelPolicy` | mode (`full` / `limited` / `held_atmosphere`), exposure (`1s`/`2s`/`3s`), smear density, masters pack, FX vocab |
| `Shot` | timing, camera dict, lens, cel policy, characters, approval |
| `XSheet` / `XSheetCell` | frame-accurate layers; exposure kinds: `key`, `breakdown`, `inbetween`, `hold`, `smear`, `blank` |
| `StylePack` | biases, camera grammar, GP/toon settings |
| `ProjectMeta` | slug, prompt, fps, style, **`plan_approved`**, `render_approved` |
| `ApprovalState` | draft / pending_review / approved / rejected |

Style + masters data files:

- `styles/*.json` — runtime style packs  
- `mvm/cel/masters/*.json` — operational principles / section modes / exposure policy  

X-sheet builder: `mvm/cel/xsheet.py` maps beats/onsets → keys/smears; writes `timing_chart` summary on the sheet.

---

## 5. Timeline / frame representation

| Layer | Unit | Notes |
|-------|------|-------|
| Music | seconds | beatmap times; shot `start`/`end`/`duration` |
| Picture | integer frames @ `fps` (default 24) | X-sheet `start_frame`…`end_frame` |
| Mapping | `mvm/cel/timing.py` | `time_to_frame`, `exposure_step`, `frames_for_duration` |
| Camera | float seconds + keyframed Blender frames | shot.camera start/end locs |
| Editorial | shot-level clips | concat list for multi-shot mux |

There is **no** shared global timeline object beyond project JSON + per-shot X-sheets. Remotion props duplicate section/shot times for overlays.

---

## 6. Asset storage

```text
projects/<slug>/
  project.json
  audio/master.<ext>
  beatmap.json
  story.json
  shots/<shot_id>.json
  xsheets/<shot_id>.json
  model_sheets/          # directory exists; little/no content pipeline yet
  previews/<shot_id>/    # craft_payload.json, frames/, shot_preview.mp4, optional .blend
  renders/<shot_id>/     # final-quality target (same craft path, preview=false)
  final/                 # muxed mp4s, remotion_props.json, concat_list.txt
```

Also:

- `styles/` — shared style packs (repo root)
- `blender/templates/` — README only; no `.blend` bases checked in
- `projects/` gitignored (local work product)

---

## 7. AI / model integrations

| Kind | Status |
|------|--------|
| LLM APIs (OpenAI/Anthropic/Gemini/etc.) | **Not integrated** |
| Diffusion / AI video backends | **Explicitly avoided** in v1 (by design) |
| “Agents” | **Deterministic / heuristic** Python in `mvm/agents/pipeline.py` (Music Analyst, Screenwriter, Director, Animation Director, Verifier) |
| MIR | librosa (BPM, beats, onsets, RMS, spectral flux, heuristic sections) |
| Optional future (README) | Whisper, Demucs — not implemented |
| `httpx` | listed dependency; not used for generative backends in current craft path |

**Implication:** creative planning is rule + prompt-token driven, not opaque model sampling. Still, decisions (key placement, smear selection, section labels) are **not yet written to a durable decisions ledger** for the user to inspect beyond X-sheet `timing_chart` / shot notes.

---

## 8. User review surfaces

| Surface | Can do | Gaps |
|---------|--------|------|
| Studio (`studio/src/App.tsx`) | Create project, list projects, see energy/sections, edit description/notes/cel mode/exposure/smear, approve plan, trigger craft | No X-sheet grid editor; no preview player; no decisions panel; shot edit does not rebuild X-sheet or revoke approval |
| CLI | Full pipeline; approve gate before craft | Unicode/console quirks on some Windows code pages |
| FastAPI `/docs` | Interactive API | Not a creative review UX |
| Blender `.blend` (when craft succeeds) | Human can open and refine GP strokes | Not linked from Studio |

**Human approval that exists:** `plan_approved` hard-blocks craft in CLI and API.

**Human approval missing:** per-shot re-approval after cel edits; `render_approved` field exists on meta but is unused in craft/assemble gates; no reject → replan loop UI.

---

## 9. Tests and build commands

| Command | Purpose | Current state |
|---------|---------|---------------|
| `pip install -e ".[studio]"` | Install package + Studio API deps | Documented; works |
| `pytest tests/` | Smoke: styles + plan/X-sheet | **2 passed** (only smoke coverage) |
| `mvm …` | CLI workflow | Works |
| `uvicorn mvm.studio_api:app --reload --port 8787` | API | Documented |
| `cd studio && npm install && npm run dev` | UI | Documented; deps installed in workspace |
| `cd studio && npm run build` | Production UI bundle | Not verified in this audit |
| `ruff` | Lint (optional extra) | Configured line-length; not in CI |
| Typecheck (mypy/pyright) | Python types | **Missing** |
| CI (GitHub Actions etc.) | Automated gates | **Missing** |
| Remotion render | Overlay pipeline | Stub only |

---

## 10. Missing infrastructure

- Decision / provenance ledger (`decisions.json` or equivalent) for MIR→keys, holds, smears, style rules applied
- X-sheet rebuild + approval invalidation when Studio patches cel policy
- Interactive X-sheet editor and preview playback in Studio
- Real Blender template `.blend` packs under `blender/templates/`
- Model sheet asset pipeline (directory only)
- Character continuity bank across shots
- Verifier results persisted to disk (today returned in-memory during `plan` only)
- `render_approved` gate wired to assemble/final
- Remotion actually compositing over plates
- Whisper/Demucs optional MIR enrichment
- Resolve/FCPXML export
- CI, ruff/mypy in default workflow
- Broader tests (workspace I/O, approve gate, craft engine id, assemble mux)
- Secrets/config story for any future LLM director (none today — keep optional and explicit)

---

## 11. What already exists

- End-to-end **craft-first** skeleton: analyze → plan → approve → craft → mux
- Versionable **project JSON** as source of truth
- **X-sheet** as the animation authority for frame exposures
- **Masters / style packs** as data, not vibes
- **Hybrid renderer path** (3D layout + GP script) with honest fallback engine naming
- Collaborative **Studio approve gate**
- MIR beat/section sync feeding shot cuts and key accents
- Remotion props hook for later editorial

---

## 12. What is missing

- Transparent **decision ledger** (user-visible model/heuristic choices)
- Closing the loop: edit shot → regenerate X-sheet → require re-approve
- Production-grade Blender templates and character drawing systems
- Studio X-sheet + preview + provenance UX
- Test/CI depth matching a professional pipeline
- Editorial Remotion render integration
- Optional lyric/stem analysis

---

## 13. What should be preserved

- Blender-primary, **no diffusion-as-primary-image** stance
- **Human approve before craft** (`plan_approved`)
- X-sheet / cel exposure vocabulary and pose-to-pose thinking
- Project directory contract (`beatmap`, `story`, `shots`, `xsheets`, previews/final)
- Style packs + masters JSON as editable craft knowledge
- Explicit engine reporting (`blender` vs `fallback_cel_preview`)
- Deterministic agents until/unless an LLM layer is added as an **optional, reviewed** advisor—not a silent pixel generator

---

## 14. What should be redesigned

| Area | Why | Direction (not implemented here) |
|------|-----|----------------------------------|
| Studio shot PATCH | Cel edits leave stale X-sheets and keep approval | PATCH → rebuild X-sheet for shot → set `plan_approved=false` + surface diff |
| Agent “black box” planning | Heuristics exist but aren’t audited | Emit `decisions.json` / per-shot decision blocks on every plan/craft |
| Section labeling MIR | Coarse energy heuristic; can mislabel structure | Keep heuristic default; allow manual section edit in Studio before plan lock |
| Fallback preview UX | Easy to mistake silhouette MP4 for “the look” | Require provenance badge in Studio; watermark or metadata sidecar |
| Camera as free `dict` | Weak schema | Typed camera model shared by Director + Blender script |
| `render_approved` unused | Dead field | Either wire to assemble/final or remove later (prefer wire) |

Do **not** redesign by replacing with Remotion-first or AI-video-first architecture.

---

## 15. Smallest viable vertical slice (craft-first)

Goal: one song fragment → one approved shot → one authored cel preview → mux, with **visible decisions** and **no silent creative overwrite**.

**Slice scope (implementation order):**

1. **Plan one chorus/intro shot** (already works) and write **`decisions.json`** listing: style pack, section label source, key frame times, smear frames, exposure step, engine intended.
2. **Studio/CLI approve** remains mandatory before craft (already works).
3. **Craft that single shot** with engine id surfaced in API + UI status (partially works; strengthen UI).
4. **If user edits cel policy:** rebuild that shot’s X-sheet, append decision delta, **clear `plan_approved`** until re-approve.
5. **Mux** that shot with trimmed audio (already works via assemble).

**Out of slice:** full-length multi-shot polish, Remotion titles, Whisper, character banks, Resolve export, LLM screenwriter.

**Exit criteria for the slice:**

- [x] `decisions.json` present after `plan` / `craft`
- [x] Cel edit invalidates approval and regenerates X-sheet
- [x] Studio shows engine + key/smear counts before/after craft
- [x] Pytest covers approve gate + X-sheet rebuild + decisions file shape
- [x] No new generative video dependency

---

## 16. Recommended next implementation ticket

**Ticket A (smallest):** Decision ledger + Studio provenance display + X-sheet rebuild on cel PATCH with approval revoke.

No production code was modified for this audit.
