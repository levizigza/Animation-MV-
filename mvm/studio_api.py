"""FastAPI Studio backend — collaborative review gate + cinema craft media."""

from __future__ import annotations

import json
import queue
import shutil
import threading
from pathlib import Path
from typing import Any, Generator, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from mvm.agents.pipeline import run_planning_pipeline
from mvm.audio.analyze import analyze_audio
from mvm.blender.runner import find_blender, render_shot, write_craft_payload
from mvm.cel.decisions import record_cel_edit, record_craft, record_plan
from mvm.cel.masters import list_style_packs
from mvm.cel.xsheet import build_xsheet_for_shot
from mvm.editorial.assemble import mux_shot_with_audio, write_remotion_props
from mvm.project.workspace import PROJECTS_DIR, ProjectWorkspace, create_project
from mvm.schemas.models import ApprovalState, Shot
from mvm.studio_media import (
    craft_status,
    frames_manifest,
    preview_mp4_path,
    safe_frame_path,
)

app = FastAPI(title="Cel Music Video Studio", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveBody(BaseModel):
    approved: bool = True
    comment: str = "Plan approved for craft preview"
    restore_revision_id: Optional[str] = None


class ShotUpdate(BaseModel):
    description: Optional[str] = None
    notes: Optional[str] = None
    lens_mm: Optional[float] = None
    approval: Optional[ApprovalState] = None
    cel_mode: Optional[str] = None
    cel_exposure: Optional[str] = None
    smear_density: Optional[float] = None


def _ws(slug: str) -> ProjectWorkspace:
    path = PROJECTS_DIR / slug
    if not path.exists():
        raise HTTPException(404, "Project not found")
    return ProjectWorkspace(path)


def _shot_xsheet(ws: ProjectWorkspace, shot_id: str):
    shot = next((s for s in ws.load_shots() if s.id == shot_id), None)
    if not shot:
        raise HTTPException(404, "Shot not found")
    xs = next((x for x in ws.load_xsheets() if x.shot_id == shot_id), None)
    return shot, xs


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/styles")
def styles() -> list[str]:
    return list_style_packs()


@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if (p / "project.json").exists():
            ws = ProjectWorkspace(p)
            meta = ws.meta()
            out.append(
                {
                    "slug": meta.slug,
                    "title": meta.title,
                    "plan_approved": meta.plan_approved,
                    "style_pack": meta.style_pack,
                }
            )
    return out


@app.get("/api/projects/{slug}")
def get_project(slug: str) -> dict[str, Any]:
    return _ws(slug).to_dict()


@app.post("/api/projects")
async def create(
    title: str = Form(...),
    prompt: str = Form(...),
    style: str = Form("classic_cel"),
    audio: UploadFile = File(...),
) -> dict[str, Any]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = PROJECTS_DIR / "_upload_tmp"
    tmp.mkdir(exist_ok=True)
    suffix = Path(audio.filename or "track.wav").suffix or ".wav"
    dest = tmp / f"upload{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(audio.file, f)
    ws = create_project(title=title, prompt=prompt, audio_path=dest, style_pack=style)
    dest.unlink(missing_ok=True)
    beatmap = analyze_audio(ws.audio_file())
    ws.save_beatmap(beatmap)
    result = run_planning_pipeline(prompt, beatmap, style_pack=style, fps=ws.meta().fps)
    ws.save_story(result["story"])
    ws.save_shots(result["shots"])
    ws.save_xsheets(result["xsheets"])
    from mvm.neurosymbolic.bridge import ground_planning_mir, summarize_decisions

    ns_persisted = ground_planning_mir(
        ws.root, beatmap=beatmap, shots=result["shots"], style_pack=style
    )
    ns_summary = {
        **(result.get("neurosymbolic") or {}).get("summary", {}),
        **summarize_decisions(ns_persisted),
        "persisted": len(ns_persisted),
    }
    record_plan(
        ws.root,
        prompt=prompt,
        style_pack=style,
        beatmap=beatmap,
        shots=result["shots"],
        xsheets=result["xsheets"],
        analysis=result["analysis"],
        verification=result["verification"],
        neurosymbolic=ns_summary,
    )
    ws.persist_plan_domain(result["shots"], result["xsheets"])
    meta = ws.meta()
    meta.plan_approved = False
    ws.save_meta(meta)
    return ws.to_dict()


@app.patch("/api/projects/{slug}/shots/{shot_id}")
def update_shot(slug: str, shot_id: str, body: ShotUpdate) -> dict[str, Any]:
    ws = _ws(slug)
    shots = ws.load_shots()
    target: Shot | None = next((s for s in shots if s.id == shot_id), None)
    if not target:
        raise HTTPException(404, "Shot not found")
    if body.description is not None:
        target.description = body.description
    if body.notes is not None:
        target.notes = body.notes
    if body.lens_mm is not None:
        target.lens_mm = body.lens_mm
    if body.approval is not None:
        target.approval = body.approval

    cel_changed: list[str] = []
    if body.cel_mode is not None and body.cel_mode != target.cel.mode:
        target.cel.mode = body.cel_mode  # type: ignore[assignment]
        cel_changed.append("cel_mode")
    if body.cel_exposure is not None and body.cel_exposure != target.cel.exposure:
        target.cel.exposure = body.cel_exposure  # type: ignore[assignment]
        cel_changed.append("cel_exposure")
    if body.smear_density is not None and body.smear_density != target.cel.smear_density:
        target.cel.smear_density = body.smear_density
        cel_changed.append("smear_density")

    ws.save_shot(target)
    response: dict[str, Any] = {"shot": target.model_dump(mode="json")}

    if cel_changed:
        if not (ws.root / "beatmap.json").exists():
            raise HTTPException(400, "beatmap.json required to rebuild X-sheet after cel edit")
        beatmap = ws.load_beatmap()
        meta = ws.meta()
        xsheet = build_xsheet_for_shot(target, beatmap, fps=meta.fps)
        xsheet.approval = ApprovalState.PENDING_REVIEW
        target.approval = ApprovalState.PENDING_REVIEW
        ws.save_shot(target)
        ws.save_xsheet(xsheet)
        ws.set_plan_approved(False)
        record_cel_edit(
            ws.root,
            shot=target,
            xsheet=xsheet,
            changed_fields=cel_changed,
            approval_revoked=True,
        )
        parent_rev = None
        if (ws.root / "domain_project.json").exists():
            parent_rev = json.loads(
                (ws.root / "domain_project.json").read_text(encoding="utf-8")
            ).get("active_revision_id")
        domain = ws.persist_timing_rebuild(
            target,
            xsheet,
            cel_changed,
            parent_revision_id=parent_rev,
        )
        response["shot"] = domain["shot"].model_dump(mode="json")
        response["xsheet"] = xsheet.model_dump(mode="json")
        response["timing_plan"] = domain["timing_plan"].model_dump(mode="json")
        response["revision"] = domain["revision"].model_dump(mode="json")
        response["provenance"] = domain["provenance"].model_dump(mode="json")
        response["plan_approved"] = False
        response["approval_revoked"] = True
        response["changed_fields"] = cel_changed
        response["note"] = (
            "Cel policy changed: X-sheet + TimingPlan rebuilt. "
            "Revision/provenance recorded. Plan approval revoked — re-approve before craft."
        )
    return response


@app.post("/api/projects/{slug}/approve-plan")
def approve_plan(slug: str, body: ApproveBody) -> dict[str, Any]:
    from mvm.project.reviews import approve_plan as do_approve
    from mvm.project.reviews import reject_plan as do_reject

    ws = _ws(slug)
    if body.approved:
        result = do_approve(
            ws.root, ws.load_shots(), comment=body.comment or "Plan approved for craft preview"
        )
        for xs in ws.load_xsheets():
            xs.approval = ApprovalState.APPROVED
            ws.save_xsheet(xs)
        story = ws.load_story()
        story.approval = ApprovalState.APPROVED
        ws.save_story(story)
        ws.set_plan_approved(True)
        return {
            "plan_approved": True,
            **result,
        }

    if not (body.comment or "").strip():
        raise HTTPException(400, "Rejecting a plan requires a comment explaining why.")
    result = do_reject(
        ws.root,
        ws.load_shots(),
        comment=body.comment,
        restore_revision_id=body.restore_revision_id,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("reason", "Reject failed"))
    ws.set_plan_approved(False)
    return {"plan_approved": False, **result}


@app.get("/api/projects/{slug}/shots/{shot_id}/craft-status")
def get_craft_status(slug: str, shot_id: str) -> dict[str, Any]:
    ws = _ws(slug)
    shot, xs = _shot_xsheet(ws, shot_id)
    status = craft_status(ws.root, shot_id, xs)
    status["preview_url"] = (
        f"/api/projects/{slug}/shots/{shot_id}/preview" if status["has_mp4"] else None
    )
    status["frames_manifest_url"] = f"/api/projects/{slug}/shots/{shot_id}/frames"
    status["shot"] = shot.model_dump(mode="json")
    return status


@app.get("/api/projects/{slug}/shots/{shot_id}/preview")
def get_shot_preview(slug: str, shot_id: str) -> FileResponse:
    ws = _ws(slug)
    _shot_xsheet(ws, shot_id)
    mp4 = preview_mp4_path(ws.root, shot_id)
    if not mp4.is_file():
        raise HTTPException(
            404,
            "No shot_preview.mp4 yet — craft the shot or use /frames for PNG sequence playback.",
        )
    return FileResponse(mp4, media_type="video/mp4", filename="shot_preview.mp4")


@app.get("/api/projects/{slug}/shots/{shot_id}/frames")
def get_frames_manifest(slug: str, shot_id: str) -> dict[str, Any]:
    ws = _ws(slug)
    _, xs = _shot_xsheet(ws, shot_id)
    return frames_manifest(ws.root, shot_id, slug, xs)


@app.get("/api/projects/{slug}/shots/{shot_id}/frames/{name}")
def get_frame_file(slug: str, shot_id: str, name: str) -> FileResponse:
    ws = _ws(slug)
    _shot_xsheet(ws, shot_id)
    path = safe_frame_path(ws.root, shot_id, name)
    if path is None:
        raise HTTPException(404, "Frame not found")
    media = "image/png" if path.suffix.lower() == ".png" else "application/octet-stream"
    return FileResponse(path, media_type=media, filename=name)


@app.post("/api/projects/{slug}/craft/{shot_id}")
def craft_shot(slug: str, shot_id: str) -> dict[str, Any]:
    ws = _ws(slug)
    if not ws.meta().plan_approved:
        raise HTTPException(400, "Plan not approved — collaborative gate blocked craft.")
    shot, xs = _shot_xsheet(ws, shot_id)
    if not xs:
        raise HTTPException(404, "X-sheet not found")
    result = render_shot(ws.root, shot, xs, style_pack=ws.meta().style_pack, preview=True)
    record_craft(ws.root, shot=shot, xsheet=xs, craft_result=result)
    result["decisions_path"] = str(ws.root / "decisions.json")
    result["craft_status"] = craft_status(ws.root, shot_id, xs)
    result["frames"] = frames_manifest(ws.root, shot_id, slug, xs)
    return result


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/api/projects/{slug}/craft/{shot_id}/stream")
def craft_shot_stream(slug: str, shot_id: str) -> StreamingResponse:
    """SSE craft progress — frames appear as they are authored."""
    ws = _ws(slug)
    if not ws.meta().plan_approved:
        raise HTTPException(400, "Plan not approved — collaborative gate blocked craft.")
    shot, xs = _shot_xsheet(ws, shot_id)
    if not xs:
        raise HTTPException(404, "X-sheet not found")

    events: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def on_frame(index: int, total: int, path: Path) -> None:
        events.put(
            {
                "type": "frame",
                "frame": index,
                "total": total,
                "name": path.name,
                "url": f"/api/projects/{slug}/shots/{shot_id}/frames/{path.name}",
                "progress": round(index / max(total, 1), 4),
            }
        )

    def worker() -> None:
        try:
            events.put(
                {
                    "type": "started",
                    "shot_id": shot_id,
                    "expected_frames": xs.end_frame,
                    "fps": xs.fps,
                }
            )
            out_dir = ws.root / "previews" / shot_id
            write_craft_payload(ws.root, shot, xs, ws.meta().style_pack, out_dir)
            events.put({"type": "payload_written", "dir": str(out_dir)})
            blender = find_blender()
            engine = "blender" if blender else "fallback_cel_preview"
            events.put({"type": "engine_selected", "engine": engine})
            result = render_shot(
                ws.root,
                shot,
                xs,
                style_pack=ws.meta().style_pack,
                preview=True,
                on_frame=on_frame,
            )
            record_craft(ws.root, shot=shot, xsheet=xs, craft_result=result)
            mp4 = preview_mp4_path(ws.root, shot_id)
            if mp4.is_file():
                events.put(
                    {
                        "type": "mp4_ready",
                        "url": f"/api/projects/{slug}/shots/{shot_id}/preview",
                    }
                )
            events.put(
                {
                    "type": "done",
                    "ok": result.get("ok", True),
                    "engine": result.get("engine"),
                    "output": result.get("output"),
                    "warning": result.get("warning"),
                    "frames": frames_manifest(ws.root, shot_id, slug, xs),
                    "craft_status": craft_status(ws.root, shot_id, xs),
                }
            )
        except Exception as exc:  # noqa: BLE001 — surface to SSE client
            events.put({"type": "error", "message": str(exc)})
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def gen() -> Generator[str, None, None]:
        while True:
            item = events.get()
            if item is None:
                break
            yield _sse(item)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/projects/{slug}/assemble/{shot_id}")
def assemble_shot(slug: str, shot_id: str) -> dict[str, Any]:
    ws = _ws(slug)
    shot = next((s for s in ws.load_shots() if s.id == shot_id), None)
    if not shot:
        raise HTTPException(404, "Shot not found")
    write_remotion_props(
        ws.root,
        [s.model_dump(mode="json") for s in ws.load_shots()],
        ws.load_beatmap().model_dump(mode="json"),
    )
    preview = ws.root / "previews" / shot.id / "shot_preview.mp4"
    frames = ws.root / "previews" / shot.id / "frames"
    src = preview if preview.exists() else frames
    if not src.exists():
        raise HTTPException(400, "Craft preview missing")
    out = ws.root / "final" / f"{shot.id}.mp4"
    return mux_shot_with_audio(
        src, ws.audio_file(), out, start_sec=shot.start, duration_sec=shot.duration
    )


@app.get("/api/projects/{slug}/audio")
def get_audio(slug: str) -> FileResponse:
    ws = _ws(slug)
    return FileResponse(ws.audio_file())


def run() -> None:
    import uvicorn

    uvicorn.run("mvm.studio_api:app", host="127.0.0.1", port=8787, reload=True)


if __name__ == "__main__":
    run()
