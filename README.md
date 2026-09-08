# Cel Music Video Studio

Blender-primary music video pipeline that **crafts cel animation**—pose-to-pose keys, breakdowns, holds, smears, and exposure sheets—synced to music analysis. You approve the plan before any craft render. Not diffusion video; not one-click slop.

## What it takes from the ecosystem

| Source | What we use |
|--------|-------------|
| **Blender** | Hybrid 3D layout + Grease Pencil cel performance |
| **Remotion** | Editorial overlays (titles, lyric punches) |
| **FFmpeg + librosa** | Mux + BPM / beats / sections / energy |
| **AutoMV-shaped agents** | Screenwriter → Director → Animation Director → Verifier |

## Architecture

```
prompt + audio → MIR beatmap → creative agents → story / shots / X-sheets
        → Studio review (you approve) → Blender cel craft → FFmpeg mux → Remotion overlays
```

Style packs encode masters' *thinking* (Miyazaki atmosphere, Akira intensity, limited TV economy, classic cel)—as operational rules for timing and camera, not scraped frames.

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) on `PATH`
- [Blender 4.x](https://www.blender.org/) optional but recommended (`BLENDER_PATH` if not on PATH)
- Node 18+ for Studio UI / Remotion stub

## Install

```bash
cd "Music Video Maker"
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -e ".[studio]"
pip install pillow
```

## CLI workflow

```bash
mvm init path\to\song.mp3 -t "Neon Harbor" -p "Rider through rain; chorus explodes chrome" -s akira_chrome
mvm analyze neon-harbor
mvm plan neon-harbor
# Review in Studio, or:
mvm approve-plan neon-harbor
mvm craft neon-harbor --shot shot_004_chorus
mvm assemble neon-harbor --shot shot_004_chorus
```

Commands: `mvm styles` · `mvm list` · `mvm review-export <slug>`

## Studio (cinema craft stage)

```bash
# terminal 1
uvicorn mvm.studio_api:app --reload --port 8787
# terminal 2
cd studio && npm install && npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173 — **cinema layout**: full-bleed craft stage, shot timeline, frame strip, live build feed.

1. Open or create a project  
2. **Approve plan**  
3. **Craft shot** — watch cel frames stream onto the stage (SSE)  
4. Scrub the **frame strip** to verify keys/smears against the X-sheet  
5. Play MP4 preview when encoded, or play the PNG sequence as video  

Media API (proxied via Vite `/api`):

- `GET /api/projects/{slug}/shots/{id}/preview` — `shot_preview.mp4`
- `GET /api/projects/{slug}/shots/{id}/frames` — frame manifest + key/smear flags
- `GET /api/projects/{slug}/shots/{id}/frames/{name}` — single PNG
- `GET /api/projects/{slug}/shots/{id}/craft-status`
- `POST /api/projects/{slug}/craft/{id}/stream` — SSE craft progress

Craft remains Blender / X-sheet fallback — not diffusion.
## Project tree

```
projects/<slug>/
  audio/master.*
  beatmap.json
  story.json
  shots/*.json
  xsheets/*.json
  previews/   # craft previews
  renders/
  final/      # muxed plates + remotion_props.json
```

## Documentation

- [README](README.md) — install and workflow
- [Craft engine audit](docs/CRAFT_ENGINE_AUDIT.md) — architecture map, gaps, preserve/redesign, smallest vertical slice
- [Domain model](docs/DOMAIN_MODEL.md) — Project/Sequence/Shot intent, timing, revision, provenance
- [Neuro-symbolic craft](docs/NEURO_SYMBOLIC.md) — soft proposals grounded by hard craft rules
- [Oino Interlude canon](docs/OINO_INTERLUDE_CANON.md) — locked story/creative rules for first MV

## Style packs

- `classic_cel` — pose-to-pose discipline
- `ghibli_atmosphere` — held air, soft staging
- `akira_chrome` — dense action, crash camera grammar
- `limited_tv` — economy keys + long holds

## Phase map

- **Phase 0** (this repo): MIR, agents, X-sheets, Studio gate, craft preview, FFmpeg mux, Remotion stub
- **Phase 1**: richer hybrid templates + masters packs (included as data)
- **Phase 2+**: character bank, batch queue, Resolve export, Whisper/Demucs optional

## License

Project code: MIT-intended for your studio use. Respect Blender GPL when distributing Blender-linked binaries; do not ship copyrighted model sheets from existing films.
