# Domain model (craft-first)

Typed authoring schema for Project / Sequence / Shot / intent / timing / review.

- [`mvm/schemas/domain.py`](../mvm/schemas/domain.py) — Project, Sequence, ShotCraft, ShotIntent, StoryboardPanel, Layout, KeyPose, TimingPlan, ExposureHold, AudioCue, Reference, Review, Revision, ProvenanceRecord
- [`mvm/schemas/compat.py`](../mvm/schemas/compat.py) — legacy Shot/XSheet → domain upgrades
- [`mvm/schemas/models.py`](../mvm/schemas/models.py) — `Shot.intent` required (backfilled for old JSON)

## Timing (craft sheet)

Inspectable timing lives in `timing/` (versioned). Key poses stay in `key_poses/`.
Spacing is explicit (`linear` / `stepped` / `slow_in` / `slow_out` / `slow_in_out` / `custom`
piecewise-linear). `allow_auto_smooth` is always `false` — engines must not silently ease.

CLI: `mvm timing create|hold|annotate|timeline|version|compare|export|import-bundle`

Authored vs generated: every exposure/slot/curve carries `source` (`authored`|`generated`).
Generated spacing slots are reversible via revision snapshot or drop-generated.

## Key-pose-first workflow

Keys carry `action` / `intention` and a `PoseArc` (anticipation / follow-through; `None` = unset).
In-between suggestions live in `suggestions/` as non-destructive previews until
accept / partial-accept / reject. Missing information is listed instead of guessed.
Approved key poses cannot be rewritten automatically.

CLI: `mvm keypose mark|action|arc|approve|suggest|preview|accept|partial-accept|reject-suggestion`

## Creator-intent notation

Explicit marks (`motion_path`, `source_object`, `target_object`, `force_direction`,
`timing_emphasis`, `contact_point`, `anticipation`, `overshoot`, `settle`,
`intended_stillness`) live in `notation/`. Translation yields a `MotionRequest` in
`motion_requests/` with `applied_as_final=False` always.

Ambiguous notation returns 2–3 interpretations; the human choice is recorded in
provenance. Freehand refs are links only — never auto-baked into finals.

CLI: `mvm notation create|analyze|translate|choose`

## Reference notebooks

Project- or character-scoped notebooks in `notebooks/` hold reference images/videos,
observational notes, preserve/exaggerate/omit, acting observations, movement vocabulary,
recurring behaviors, transformation notes, and required source attribution.

Assistance uses `AssistanceMetadata` (`influence_mode=explicit_metadata`) only —
`opaque_style_imitation` is always false. Revisions fork versions while persisting media
and attribution.

CLI: `mvm notebook create|attach|notes|revise|assist`

## Structured craft reviews

Multi-category critiques live in `critiques/` (separate from gate `reviews/` approve/reject).
Categories: intent clarity, staging, silhouette/readability, pose, timing, spacing, weight,
acting, emotional transition, continuity, sound relationship, originality/authorship.

Each item has notes, frame/time range, severity, reviewer (on the session), revision status,
and resolved/unresolved state. **No aggregate quality score** — comparison views are
per-category deltas between current and previous revision reviews.

CLI: `mvm critique create|add|resolve|compare|show`

## Sequence-aware analysis

Evaluator inspects preceding / current / following shots plus character state, camera/spatial
continuity, pacing contrast, emotional progression, and repeated framing/gesture patterns.
It **identifies possible issues with explanations** and never auto-fixes shot data
(`auto_fix_applied=False`).

CLI: `mvm sequence evaluate`

## Sound-aware planning

`sound_plans/` holds dialogue / phoneme / emphasis / impact / breath / music beat /
silence / environmental cues plus optional sound→motion relationships
(`move|hold|silence|non_reaction|unassigned`). Cues overlay the timing timeline for
editing. **`force_every_cue_to_motion` is always false** — silence and non-reaction
are valid authored choices; links never auto-apply.

CLI: `mvm sound create|cue|link|import-beats|timeline`

## Provenance

Every meaningful change should leave a `ProvenanceRecord` (creator, timestamp, source
references, operation, input parameters, generated alternatives, acceptance state,
human edits after generation, final approval). Generated work is visibly labeled.
Guardrails refuse hidden full-shot replacement, silent smoothing, overwriting approved
work, untraceable asset swaps, and living-artist names as style controls. Users can
export/import provenance bundles and restore prior revisions.

CLI: `mvm provenance record|inspect|accept|reject|edit|approve|export|import-bundle|restore`

## Narrow assistants

Scoped suggestion-only assistants (not one general animation agent):
storyboard, timing, pose, continuity, sound, critique, provenance.

Each states input assumptions, stays in assigned scope, returns labeled suggestions
with confidence/uncertainty/reasons, and writes provenance — not silent craft edits.
A domain fence blocks cross-domain mutation during suggest.

CLI: `mvm assistant run`

## Neuro-symbolic craft

Soft MIR / heuristic / assistant proposals become `NeuralProposal` objects and must
pass `ground_proposal` against `SymbolicCraftState` before they are ledgered.
Symbolic rules can veto illegal craft moves; accepted items remain suggestions
(`applied=False`). Decisions live in `neurosymbolic_decisions/` with neuro vs
symbolic provenance. See [`NEURO_SYMBOLIC.md`](NEURO_SYMBOLIC.md).

CLI: `mvm neurosym inspect|ground`

## Evaluation harness

Three fixed craft scenes under `eval_scenes/`:
dialogue (readable acting), physical action (weight/timing), quiet (stillness/subtext).

Each session evaluates separate dimensions — intent clarity, pose readability, timing,
spacing, stillness, sequence context, sound relationship, revision quality, and
human reviewer preference — with automatic *observations* (signals + confidence) and
a required human review form. Results live in `eval_sessions/` and `eval_forms/`.
**No aggregate quality score**; automatic metrics never substitute for human preference.

CLI: `mvm eval scenes|seed|run|run-all|form|submit|show`

## Short-sequence pilot

`mvm pilot run` exercises one short sequence through intent → storyboard → layout →
animatic → key poses → timing → in-betweens → sound → review → revision → approval.
It records confusion/assumption/suggestion/revision/intent measurements and writes a
prioritized P0/P1/P2 findings report (no aggregate score; no features added mid-pilot).

## External craft references (public-apis)

Curated APIs that improve decision conditions — not auto-animation:
Free Dictionary, Art Institute of Chicago, Met, MusicBrainz, Colormind, Lyrics.ovh.
Stored in `external_refs/` with attribution; `applied_as_final=False`; human accept before notebook attach.

CLI: `mvm refs catalog|dictionary|art|music|palette|lyrics|accept|list` · `mvm approve-shot`

**Invariants:** every shot has explicit intent; key poses ≠ in-between slots; timing plans store no render paths; AI suggestions attach to Revision via ProvenanceRecord; Review reject can restore a prior revision.

## Storyboard / animatic

First-class animatic artifacts live in `animatics/` (versioned). Panel artwork stays in `panels/`.
Duration and order are owned by the animatic version so timing edits never rewrite artwork JSON.

CLI: `mvm storyboard create-shot|add-panel|animatic|reorder|set-duration|version|compare`

States: `intent` → `storyboard` → `layout` → `animatic` → `key_poses` → `timing_review` → `inbetween_review` → `sound_edit_review` → `final_review` → `approved`

Rules (see `mvm/schemas/lifecycle.py`):
- No detailed animation (`key_poses`+) without explicit intent
- No `final_review` without `animatic_approved`
- Animatic approve sets `animatic_approved` (and `Animatic.approved`); it does **not** set
  `shot.approval=approved` — that is reserved for `final_review` → `approved`
- Generated in-betweens cannot overwrite approved key poses
- Rejected revisions stay recoverable via `recover_rejected_revision`
- Blocked transitions always return an explanatory `reason` / `blockers`

## On-disk layout (after `plan`)

```text
projects/<slug>/
  domain_project.json
  sequences/*.json
  timing/*.json
  key_poses/*.json
  layouts/*.json
  panels/*.json
  revisions/*.json
  provenance/*.json
  neurosymbolic_decisions/*.json
  decisions.json          # human-readable ledger (parallel)
  shots/*.json            # includes intent + timing_plan_id links
  xsheets/*.json          # legacy exposure sheet (still used by craft)
```

Written by `mvm.project.domain_store.persist_plan_domain` / `persist_timing_rebuild`.
